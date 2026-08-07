"""饱和打击雷达估算单元测试。"""
from __future__ import annotations

import math

import pytest

from utils.missile_interception.missile_interception_radar import (
    H_TARGET,
    TECH_MULT,
    binding_limit_label,
    clamp,
    default_maneuver_class,
    dive_angle_deg,
    dive_entry_horizontal_km,
    estimate_engagement_distance,
    estimate_pk,
    maneuver_pk_factor,
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
    assert r['ship_detect_km'] == r['ship_search']
    assert r['awacs_detect_km'] == r['awacs_total']
    assert r['detect_max_km'] == max(r['awacs_detect_km'], r['ship_detect_km'])
    assert r['engage_dist'] == 40
    assert binding_limit_label(r) == '拦截弹射程'


def test_estimate_engagement_distance_with_awacs_uses_max_then_sam():
    """有预警机时：交战距离 = min(max(预警机总探测, 舰载探测), 拦截弹射程)。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='high', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=1000,
    )
    assert r['engage_dist'] == pytest.approx(
        min(max(r['awacs_total'], r['ship_search']), r['sam_range'])
    )


def test_engage_dist_uses_max_of_sensors_awacs_farther():
    """预警机总探测 > 舰载探测且二者均小于射程时：交战距离取预警机一路。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='high', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=1000,
    )
    assert r['awacs_total'] > r['ship_search']
    assert r['engage_dist'] == pytest.approx(r['awacs_total'])
    assert binding_limit_label(r) == '预警机雷达探测距离'


def test_engage_dist_uses_max_of_sensors_ship_farther():
    """舰载探测 > 预警机总探测且二者均小于射程时：交战距离取舰载一路（而非二者取小）。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='high', awacs_area=0.5, awacs_type='mechanical',
        standoff_km=0, ship_area=1000, ship_type='gan_aesa', sam_range_km=5000,
    )
    assert r['ship_search'] > r['awacs_total']
    assert r['engage_dist'] == pytest.approx(r['ship_search'])
    assert binding_limit_label(r) == '舰载雷达探测距离'


def test_target_altitude_m():
    """target_altitude_m 按弹道类型返回高度估计，未知类型回退高空值。"""
    assert target_altitude_m('sea') == H_TARGET['sea'] == 10.0
    assert target_altitude_m('high') == H_TARGET['high'] == 12000.0
    assert target_altitude_m('glide') == H_TARGET['glide'] == 45000.0
    assert target_altitude_m('ballistic') == H_TARGET['ballistic'] == 80000.0
    assert target_altitude_m('unknown_traj') == H_TARGET['high']


def test_estimate_no_awacs_uses_ship_search_and_horizon():
    """无预警机时：交战距离 = min(舰载探测, 拦截弹射程)，且不使用预警机探测。"""
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
    assert r['awacs_detect_km'] == 0.0
    assert r['detect_max_km'] == r['ship_detect_km'] == r['ship_search']
    assert binding_limit_label(r) != '预警机雷达探测距离'


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


def test_dive_entry_horizontal_km_geometry():
    """俯冲角 + 最大射高几何：45°、35km 射高、45km 巡航 → 10km 水平进入距离。"""
    entry = dive_entry_horizontal_km(45000.0, 35.0, 45.0)
    assert entry == pytest.approx(10.0)
    entry80 = dive_entry_horizontal_km(80000.0, 35.0, 45.0)
    assert entry80 == pytest.approx(45.0)
    assert dive_entry_horizontal_km(30000.0, 35.0, 45.0) is None


def test_dive_angle_from_traj():
    """弹道类型对应默认俯冲角。"""
    assert dive_angle_deg('ballistic') == 45.0
    assert dive_angle_deg('glide') == 25.0


def test_high_traj_skips_dive_geometry_when_within_sam_envelope():
    """常规高空导弹巡航高度已在射高包线内：不计算俯冲进入距离。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='high', awacs_area=8, awacs_type='aesa',
        standoff_km=150, ship_area=12, ship_type='aesa', sam_range_km=1000,
        sam_max_alt_km=33.0,
    )
    assert r['h_target_m'] == 12000.0
    assert r['h_engage_m'] == 12000.0
    assert r['dive_entry_km'] is None
    assert r['dive_angle_deg'] is None
    assert r['engage_dist'] == pytest.approx(
        min(max(r['awacs_total'], r['ship_search']), r['sam_range'])
    )
    assert binding_limit_label(r) != '俯冲进入射高包线'


def test_sea_traj_skips_dive_geometry():
    """掠海导弹同样在射高包线内，不涉及俯冲几何。"""
    r = estimate_engagement_distance(
        rcs=0.5, traj='sea', awacs_area=8, awacs_type='aesa',
        standoff_km=0, ship_area=12, ship_type='aesa', sam_range_km=500,
        has_awacs=False, sam_max_alt_km=33.0,
    )
    assert r['dive_entry_km'] is None
    assert r['dive_angle_deg'] is None


def test_glide_ballistic_engage_limited_by_dive_entry():
    """滑翔体 / 弹道导弹有效交战距离受俯冲进入射高包线限制。"""
    common = dict(
        rcs=0.5, awacs_area=8, awacs_type='aesa', standoff_km=150,
        ship_area=12, ship_type='aesa', sam_range_km=1000, has_awacs=True,
        sam_max_alt_km=33.0,
    )
    high = estimate_engagement_distance(traj='high', **common)
    glide = estimate_engagement_distance(traj='glide', **common)
    ballistic = estimate_engagement_distance(traj='ballistic', **common)
    assert glide['dive_entry_km'] is not None
    assert ballistic['dive_entry_km'] is not None
    assert ballistic['dive_entry_km'] > glide['dive_entry_km']
    assert glide['engage_dist'] < high['engage_dist']
    assert ballistic['engage_dist'] > glide['engage_dist']
    assert binding_limit_label(ballistic) == '俯冲进入射高包线'
    assert glide['h_engage_m'] == 33000.0
    assert glide['h_target_m'] == 45000.0


def test_maneuver_pk_factor_ordering():
    """机动性修正：滑翔体更难拦截，超燃冲压更易拦截，双锥体介于巡航与滑翔体之间。"""
    cruise = maneuver_pk_factor('cruise')
    scramjet = maneuver_pk_factor('scramjet')
    glide = maneuver_pk_factor('glide')
    dual = maneuver_pk_factor('dual_cone')
    assert glide < dual < cruise < scramjet


def test_default_maneuver_class():
    """型号 / 弹道推断机动性类别。"""
    assert default_maneuver_class('glide') == 'glide'
    assert default_maneuver_class('ballistic') == 'dual_cone'
    assert default_maneuver_class('high', 'yj12') == 'scramjet'
    assert default_maneuver_class('high', 'yj18') == 'cruise'


def test_estimate_pk_range():
    """Pk 估算落在 [0.03, 0.97]。"""
    r = estimate_pk(
        vm_ma=2.6, vi_ma=3.8, rcs=0.5, traj='high',
        ship_area=12, ship_type='aesa', interceptor_dia_m=0.35,
        seeker_type='active_aesa',
    )
    assert 0.03 <= r['pk'] <= 0.97
    assert 'speed_factor' in r
    assert 'maneuver_factor' in r
    assert 'ecm_factor' not in r


def test_estimate_pk_maneuver_class_affects_pk():
    """滑翔体 Pk 低于巡航，超燃冲压 Pk 高于巡航（其余参数相同）。"""
    common = dict(
        vm_ma=3.0, vi_ma=3.0, rcs=0.05, traj='high',
        ship_area=6, ship_type='mechanical', interceptor_dia_m=0.2,
        seeker_type='active_mech',
    )
    cruise = estimate_pk(**common, maneuver_class='cruise')
    glide = estimate_pk(**common, maneuver_class='glide')
    scramjet = estimate_pk(**common, maneuver_class='scramjet')
    assert glide['pk'] < cruise['pk']
    assert scramjet['pk'] > cruise['pk']


def test_estimate_pk_sea_skimming_harder():
    """掠海弹道 traj_factor 更低；在未顶满上限时 Pk 亦更低。"""
    high = estimate_pk(3.0, 3.0, 0.05, 'high', 6, 'mechanical', 0.2, 'active_mech')
    sea = estimate_pk(3.0, 3.0, 0.05, 'sea', 6, 'mechanical', 0.2, 'active_mech')
    assert sea['traj_factor'] < high['traj_factor']
    assert sea['pk'] <= high['pk']
    if high['pk'] < 0.97:
        assert sea['pk'] < high['pk']


def test_estimate_pk_glide_and_ballistic_harder_than_high():
    """滑翔体 / 弹道导弹弹道比常规高空弹道更难拦截（更低 traj_factor）。"""
    high = estimate_pk(8.0, 4.0, 0.1, 'high', 12, 'aesa', 0.35, 'active_aesa')
    glide = estimate_pk(8.0, 4.0, 0.1, 'glide', 12, 'aesa', 0.35, 'active_aesa')
    ballistic = estimate_pk(10.0, 4.0, 0.1, 'ballistic', 12, 'aesa', 0.35, 'active_aesa')
    assert glide['traj_factor'] < high['traj_factor']
    assert ballistic['traj_factor'] < glide['traj_factor']
    assert ballistic['pk'] <= glide['pk'] <= high['pk']
