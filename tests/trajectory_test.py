"""轨迹采样与甲板折线的单元测试。"""
import pytest

import simulators.short_ski_jump_take_off as ski_stovl
import simulators.ski_jump_take_off as ski_conv
from apps.web_simulator import _capture_trajectory, _configure_ski_conv, resolve_ski_jump_geom
from utils.ski_jump_geometry import compute_ski_jump_arc
from utils.trajectory import TrajectoryRecorder, build_deck_profile


def test_trajectory_recorder_none_trajectory():
    """trajectory=None 时不写入任何点。"""
    rec = TrajectoryRecorder(None)
    rec.record(1.0, 2.0, 0.5, 'flat', force=True)
    rec.record(3.0, 4.0, 1.0, 'arc')


def test_trajectory_recorder_sampling():
    traj: list[dict] = []
    rec = TrajectoryRecorder(traj, sample_dt=0.1)
    rec.record(0, 0, 0.0, 'flat', force=True)
    rec.record(1, 0, 0.05, 'flat')
    rec.record(2, 0, 0.12, 'flat')
    assert len(traj) == 2
    assert traj[-1]['x'] == 2.0


def test_build_deck_profile_shape():
    arc = compute_ski_jump_arc(12.0)
    profile = build_deck_profile(50.0, arc)
    assert profile['flat_length_m'] == 50.0
    pts = profile['points']
    assert pts[0] == [0.0, 0.0]
    assert pts[1] == [50.0, 0.0]
    assert pts[-1][0] > pts[1][0]
    assert pts[-1][1] == pytest.approx(arc.lip_height_m, rel=0.01)


def test_ski_jump_simulate_records_y():
    """滑跃仿真轨迹应包含 arc 段且 y 随滑跃上升。"""
    traj: list[dict] = []
    ski_conv.simulate(100.0, 15.0, trajectory=traj)
    assert len(traj) >= 3
    arc_pts = [p for p in traj if p['phase'] == 'arc']
    assert arc_pts
    assert max(p['y'] for p in arc_pts) > 0.5
    assert any(p['phase'] == 'air' for p in traj)


def test_short_ski_jump_simulate_records_y(f35b_ski_config):
    """短距滑跃仿真轨迹应含平直段与滑跃段。"""
    traj: list[dict] = []
    ok, *_ = ski_stovl.simulate(40.0, 25.0, 45.0, 'A', 12.0, trajectory=traj)
    assert ok
    phases = {p['phase'] for p in traj}
    assert 'flat' in phases
    assert 'arc' in phases
    assert 'air' in phases
    assert traj[-1]['y'] > traj[0]['y']


def test_capture_trajectory_ski_jump(aircraft, carriers):
    """_capture_trajectory 应返回轨迹点与甲板折线。"""
    carrier = next(c for c in carriers if c.id == 'SHANDONG')
    ac = aircraft['J-15']
    geom = resolve_ski_jump_geom(carrier.ski_jump_angle_deg)
    mod = _configure_ski_conv(
        ac, ac.a2a_mass_kg, 30.0, carrier.max_speed_kt,
        geom['angle_deg'], geom['lip_height_m'],
    )
    result = mod.run_min_takeoff_search()
    assert result is not None
    traj, deck = _capture_trajectory('ski_jump', mod, result, carrier.total_deck_length_m)
    assert traj
    assert len(traj) >= 5
    assert deck['total_deck_length_m'] == carrier.total_deck_length_m
    assert deck['takeoff_distance_m'] == pytest.approx(result['total_m'], rel=0.001)
    assert deck['points'][0] == [0.0, 0.0]
    assert deck['points'][-1][0] == pytest.approx(deck['takeoff_distance_m'], rel=0.01)


def test_capture_trajectory_non_ski_mode():
    """短距平直起飞不生成轨迹。"""
    traj, deck = _capture_trajectory('short_takeoff', None, {'flat_m': 50.0}, 200.0)
    assert traj is None
    assert deck is None


@pytest.fixture
def aircraft():
    from utils.database_csv import load_aircraft_csv
    from utils.paths import AIRCRAFT_CSV
    return load_aircraft_csv(AIRCRAFT_CSV)


@pytest.fixture
def carriers():
    from utils.database_csv import load_carriers_csv
    from utils.paths import CARRIERS_CSV
    return load_carriers_csv(CARRIERS_CSV)


@pytest.fixture
def f35b_ski_config():
    import simulators.short_ski_jump_take_off as mod
    from utils.database_csv import load_aircraft_csv
    from utils.paths import AIRCRAFT_CSV
    ac = load_aircraft_csv(AIRCRAFT_CSV)['F-35B']
    mod.apply_stovl_thrust_sl(
        t_main_sl_n=ac.t_main_stovl_sl_n,
        t_liftfan_sl_n=ac.t_liftfan_sl_n,
        t_rollposts_sl_n=ac.t_rollposts_sl_n,
    )
    mod.apply_aircraft_geometry(
        mass_kg=ac.a2a_mass_kg, s_ref_m2=ac.wing_area_m2, wingspan_m=ac.wingspan_m,
        wing_height_m=ac.wing_height_m, sweep_le_deg=ac.sweep_le_deg,
    )
    mod.apply_ski_jump_deck(12.0, None)
    return ac
