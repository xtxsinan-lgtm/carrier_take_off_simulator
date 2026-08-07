"""Unit tests for short_ski_jump_take_off.py core simulation."""
import pytest

import simulators.takeoff.short_ski_jump_take_off as ski_stovl


def test_total_takeoff_distance_includes_arc(baseline):
    assert ski_stovl.total_takeoff_distance_m(100.0) == pytest.approx(baseline['ski_stovl']['total_dist'])


def test_simulate_strategy_a_tuple_matches_baseline(baseline):
    result = ski_stovl.simulate(80.0, 20.0, 45.0, 'A', 20.0)
    assert list(result) == pytest.approx(baseline['ski_stovl']['simulate_ab'], rel=0, abs=1e-6)


def test_search_strategy_c_matches_baseline(baseline):
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        r = ski_stovl.search_strategy_c(ski_stovl.MIN_SAFE_DISTANCE_M)
    expected = baseline['ski_stovl']['strategy_c']
    assert r is not None
    assert r['total_m'] == pytest.approx(expected['total_m'])
    assert r['flat_m'] == expected['flat_m']
    assert r['pitch_deg'] == expected['pitch_deg']


def test_run_strategy_b_search_returns_feasible_solution():
    best = ski_stovl.run_strategy_b_search()
    assert best is not None
    assert best['total_m'] > 0
    assert 0 <= best['nozzle_deg'] <= 90


def test_run_strategy_c_search_returns_feasible_solution():
    best = ski_stovl.run_strategy_c_search()
    assert best is not None
    assert best['total_m'] > 0
