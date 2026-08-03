"""饱和打击雷达估算单元测试。"""
from __future__ import annotations

import math

from utils.saturation_radar import (
    H_TARGET,
    TECH_MULT,
    binding_limit_label,
    clamp,
    estimate_engagement_distance,
    estimate_pk,
    power_range_km,
    radar_gain_factor,
    radar_horizon_km,
    target_altitude_m,
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
    """短程拦截弹时交战距离受射程限制（默认 has_awacs=True 仍成立）。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='high', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=40,
    )
    assert r['has_awacs'] is True
    assert r['engage_dist'] == 40
    assert binding_limit_label(r) == '拦截弹射程'


def test_target_altitude_m():
    """target_altitude_m 按弹道类型返回高度估计，未知类型回退高空值。"""
    assert target_altitude_m('sea') == H_TARGET['sea'] == 10.0
    assert target_altitude_m('high') == H_TARGET['high'] == 12000.0
    assert target_altitude_m('unknown_traj') == H_TARGET['high']


def test_estimate_no_awacs_uses_ship_search_and_horizon():
    """无预警机时：交战距离 = min(舰载探测, 拦截弹射程)，且不使用预警机总探测。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='sea', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=200,
        has_awacs=False,
    )
    assert r['has_awacs'] is False
    assert r['ship_search'] == min(r['ship_power'], r['ship_horizon'])
    assert r['engage_dist'] == min(r['ship_search'], r['sam_range'])
    assert r['awacs_power'] == 0.0
    assert r['awacs_horizon'] == 0.0
    assert r['awacs_detect'] == 0.0
    assert r['awacs_total'] == 0.0
    assert binding_limit_label(r) != '预警机总探测距离'


def test_estimate_no_awacs_sea_shorter_horizon_than_high():
    """同一舰载雷达下，掠海目标的地球曲率视距应短于高空目标。"""
    sea = estimate_engagement_distance(
        rcs=0.5, traj='sea', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=500,
        has_awacs=False,
    )
    high = estimate_engagement_distance(
        rcs=0.5, traj='high', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=500,
        has_awacs=False,
    )
    assert sea['ship_horizon'] < high['ship_horizon']


def test_estimate_pk_range():
    """Pk 估算落在 [0.03, 0.97]。"""
    r = estimate_pk(
        vm_ma=2.6, vi_ma=3.8, rcs=0.5, traj='high',
        ship_area=12, ship_type='aesa', interceptor_dia_m=0.35,
        seeker_type='active_aesa',
    )
    assert 0.03 <= r['pk'] <= 0.97
    assert 'speed_factor' in r
    assert 'ecm_factor' not in r


def test_estimate_pk_ignores_legacy_ecm_concept():
    """Pk 不再受抗干扰档数影响：相同其余参数时结果唯一。"""
    a = estimate_pk(2.6, 3.8, 0.5, 'high', 12, 'aesa', 0.35, 'active_aesa')
    b = estimate_pk(2.6, 3.8, 0.5, 'high', 12, 'aesa', 0.35, 'active_aesa')
    assert a['pk'] == b['pk']
    assert set(a.keys()) == {
        'pk', 'speed_factor', 'ship_radar_factor', 'seeker_factor', 'rcs_factor', 'traj_factor',
    }


def test_estimate_pk_sea_skimming_harder():
    """掠海弹道 traj_factor 更低；在未顶满上限时 Pk 亦更低。"""
    high = estimate_pk(3.0, 3.0, 0.05, 'high', 6, 'mechanical', 0.2, 'active_mech')
    sea = estimate_pk(3.0, 3.0, 0.05, 'sea', 6, 'mechanical', 0.2, 'active_mech')
    assert sea['traj_factor'] < high['traj_factor']
    assert sea['pk'] <= high['pk']
    if high['pk'] < 0.97:
        assert sea['pk'] < high['pk']
