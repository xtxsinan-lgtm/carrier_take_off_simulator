"""ski_jump_take_off.py 核心仿真单元测试。"""
import pytest

import simulators.ski_jump_take_off as ski_conv


def _restore_ski_conv_defaults():
    """恢复模块默认参数，避免其他测试的 apply_* 污染基线对比。"""
    ski_conv.apply_aircraft_geometry(
        mass_kg=29500,
        s_ref_m2=68.9,
        wingspan_m=13.6,
        wing_height_m=1.96,
        sweep_le_deg=38,
        cd0=0.039,
        t_max_sl_n=186000,
    )
    ski_conv.apply_thrust_temperature(30.0)
    ski_conv.apply_wind_knots(30.0)
    ski_conv.apply_ski_jump_deck(14.0)


def test_simulate_100m_15deg_prefix_matches_baseline(baseline):
    _restore_ski_conv_defaults()
    sim = ski_conv.simulate(100.0, 15.0)
    assert sim[:5] == pytest.approx(tuple(baseline['ski_conv']['simulate_100_15']), rel=0, abs=1e-6)


def test_simulate_rejects_excessive_pitch():
    with pytest.raises(ValueError, match='超过硬上限'):
        ski_conv.simulate(50.0, ski_conv.PITCH_MAX_DEG + 1)


def test_total_takeoff_distance_adds_horizontal():
    _restore_ski_conv_defaults()
    flat_m = 80.0
    total = ski_conv.total_takeoff_distance_m(flat_m)
    assert total == pytest.approx(flat_m + ski_conv.SKI_JUMP_HORIZONTAL_M)
