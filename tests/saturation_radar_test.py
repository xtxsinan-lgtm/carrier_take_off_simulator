"""饱和打击雷达估算单元测试。"""
from __future__ import annotations

import math

from utils.saturation_radar import (
    TECH_MULT,
    binding_limit_label,
    clamp,
    estimate_engagement_distance,
    estimate_pk,
    power_range_km,
    radar_gain_factor,
    radar_horizon_km,
)


def test_clamp_bounds():
    """clamp 限制上下界。"""
    assert clamp(5, 1, 3) == 3
    assert clamp(-1, 0, 2) == 0
    assert clamp(1.5, 0, 2) == 1.5


def test_radar_horizon_km():
    """视距随高度平方根增长。"""
    h = radar_horizon_km(9000, 10)
    assert h == 4.12 * (math.sqrt(9000) + math.sqrt(10))


def test_tech_mult_values():
    """雷达体制增益倍率：机械扫描 / PESA / AESA / 氮化镓 AESA。"""
    assert TECH_MULT['mechanical'] == 1.0
    assert TECH_MULT['pesa'] == 1.43
    assert TECH_MULT['aesa'] == 2.10
    assert TECH_MULT['gan_aesa'] == 3.74


def test_power_range_km_scales_with_area_and_rcs():
    """探测距离随天线面积与 RCS 按雷达方程比例变化。"""
    base = power_range_km(400, 8, 8, 'aesa', 5, 5)
    bigger = power_range_km(400, 32, 8, 'aesa', 5, 5)
    assert bigger == base * 2
    assert TECH_MULT['aesa'] == 2.10


def test_radar_gain_factor_bounded():
    """增益系数落在 [0.55, 1.25]。"""
    g = radar_gain_factor(10, 'aesa', 10)
    assert 0.55 <= g <= 1.25


def test_estimate_engagement_distance_sam_limited():
    """短程拦截弹时交战距离受射程限制。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='high', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=40,
    )
    assert r['engage_dist'] == 40
    assert binding_limit_label(r) == '拦截弹射程'


def test_estimate_pk_range():
    """Pk 估算落在 [0.03, 0.97]。"""
    r = estimate_pk(
        vm_ma=2.6, vi_ma=3.8, rcs=0.5, ecm=2, traj='high',
        ship_area=12, ship_type='aesa', interceptor_dia_m=0.35,
        seeker_type='active_aesa',
    )
    assert 0.03 <= r['pk'] <= 0.97
    assert 'speed_factor' in r


def test_estimate_pk_sea_skimming_harder():
    """掠海弹道 traj_factor 更低；在未顶满上限时 Pk 亦更低。"""
    high = estimate_pk(3.0, 3.0, 0.05, 4, 'high', 6, 'mechanical', 0.2, 'active_mech')
    sea = estimate_pk(3.0, 3.0, 0.05, 4, 'sea', 6, 'mechanical', 0.2, 'active_mech')
    assert sea['traj_factor'] < high['traj_factor']
    assert sea['pk'] <= high['pk']
    if high['pk'] < 0.97:
        assert sea['pk'] < high['pk']
