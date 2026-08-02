"""Unit tests for exhaust_plume.py."""
import numpy as np
import pytest

from utils.exhaust_plume import (
    calc_exhaust_safe_distance_m,
    calc_exhaust_theta_deg_for_safe_distance_m,
    calc_min_nozzle_deg_for_plume,
    update_min_plume_trailing_edge_m,
)


RHO = 1.225
WIND = 11.317768


def test_exhaust_safe_distance_30deg_matches_baseline(baseline):
    expected = baseline['flat']['exhaust_30']
    assert calc_exhaust_safe_distance_m(30.0, WIND, RHO) == pytest.approx(expected)


def test_exhaust_theta_inverse_50m(baseline):
    expected = baseline['flat']['exhaust_theta']
    assert calc_exhaust_theta_deg_for_safe_distance_m(50.0, WIND, RHO) == pytest.approx(expected)


def test_min_nozzle_at_100m(baseline):
    expected = baseline['flat']['min_nozzle']
    assert calc_min_nozzle_deg_for_plume(100.0, -60.0, WIND, 0.0, RHO) == pytest.approx(expected)


def test_exhaust_safe_distance_infinite_when_wind_exceeds_safe():
    assert np.isinf(calc_exhaust_safe_distance_m(30.0, 30.0, RHO))


def test_update_min_plume_trailing_edge_tracks_minimum():
    edge1 = update_min_plume_trailing_edge_m(100.0, 30.0, WIND, None, RHO)
    edge2 = update_min_plume_trailing_edge_m(50.0, 30.0, WIND, edge1, RHO)
    assert edge2 <= edge1
