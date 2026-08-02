"""Unit tests for ski_jump_take_off.py core simulation."""
import pytest

import simulators.ski_jump_take_off as ski_conv


def test_simulate_100m_15deg_prefix_matches_baseline(baseline):
    sim = ski_conv.simulate(100.0, 15.0)
    assert sim[:5] == pytest.approx(tuple(baseline['ski_conv']['simulate_100_15']), rel=0, abs=1e-6)


def test_simulate_rejects_excessive_pitch():
    with pytest.raises(ValueError, match='超过硬上限'):
        ski_conv.simulate(50.0, ski_conv.PITCH_MAX_DEG + 1)


def test_total_takeoff_distance_adds_horizontal():
    flat_m = 80.0
    total = ski_conv.total_takeoff_distance_m(flat_m)
    assert total == pytest.approx(flat_m + ski_conv.SKI_JUMP_HORIZONTAL_M)
