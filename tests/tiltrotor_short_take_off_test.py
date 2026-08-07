"""倾转旋翼短距起飞仿真单元测试。"""
from __future__ import annotations

import pytest

import simulators.takeoff.tiltrotor_short_take_off as tilt


def test_nacelle_rate_from_wikipedia_12s_for_90deg():
    assert tilt.NACELLE_RATE_DEG_S == pytest.approx(7.5)


def test_current_prop_thrust_positive_at_hover():
    t = tilt.current_prop_thrust_n(0.0, 90.0)
    assert t > 150000  # 约 >150 kN，足以支撑中等重量


def test_simulate_strategy_b_can_liftoff():
    hist, airborne = tilt.simulate_strategy_b(45.0)
    assert airborne is True
    lo = tilt.evaluate_liftoff(hist)
    assert lo is not None
    assert lo['x_m'] > 0


def test_run_strategy_a_search_returns_feasible():
    best = tilt.run_strategy_a_search()
    assert best is not None
    assert best['x_m'] > 0
    assert 0 <= best['nozzle_deg'] <= 90


def test_run_strategy_b_search_returns_feasible():
    best = tilt.run_strategy_b_search()
    assert best is not None
    assert best['x_m'] > 0


def test_run_strategy_c_search_raises():
    with pytest.raises(ValueError, match='策略 C'):
        tilt.run_strategy_c_search()


def test_apply_propulsion_sl_updates_power():
    tilt.apply_propulsion_sl(8e6, 11.0, nacelle_blockage_frac=0.12)
    assert tilt.SHAFT_POWER_SL_W == 8e6
    assert tilt.PROP_DIAMETER_M == 11.0
    assert tilt.NACELLE_BLOCKAGE_FRAC == 0.12
    # 恢复默认，避免污染后续用例
    tilt.apply_propulsion_sl(2 * 4590e3, 11.61, nacelle_blockage_frac=0.10)
