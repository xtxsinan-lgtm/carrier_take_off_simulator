"""Unit tests for short_take_off.py core simulation."""
import pytest

import simulators.takeoff.short_take_off as flat


def test_module_defaults_rho_and_thrust(baseline):
    assert flat.RHO == pytest.approx(baseline['flat']['rho'])
    assert flat.THRUST_TEMP_FACTOR == pytest.approx(baseline['flat']['thrust_factor'])


def test_simulate_strategy_c_matches_baseline(baseline):
    r = flat.simulate_strategy_c(flat.MIN_SAFE_DISTANCE_M)
    expected = baseline['flat']['strategy_c']
    assert r is not None
    assert r['x_m'] == pytest.approx(expected['x_m'])
    assert r['v_gs_mps'] == pytest.approx(expected['v_gs_mps'])
    assert r['nozzle_deg'] == pytest.approx(expected['nozzle_deg'], abs=0.01)


def test_run_strategy_a_search_returns_feasible_solution():
    best = flat.run_strategy_a_search()
    assert best is not None
    assert best['x_m'] > 0
    assert best['v_gs_mps'] > 0
    assert 0 <= best['nozzle_deg'] <= 90


def test_run_strategy_b_search_returns_feasible_solution():
    best = flat.run_strategy_b_search()
    assert best is not None
    assert best['x_m'] > 0
    assert 0 <= best['nozzle_deg'] <= 90


def test_run_strategy_c_search_returns_feasible_solution():
    best = flat.run_strategy_c_search()
    assert best is not None
    assert best['x_m'] > 0
