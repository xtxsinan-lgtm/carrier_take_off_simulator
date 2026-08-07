"""Unit tests for sim_config.py."""
from utils.takeoff.sim_config import apply_wind_knots_globals
from utils.takeoff.takeoff_physics import KT_TO_MPS


def test_apply_wind_knots_globals():
    g = {}
    apply_wind_knots_globals(30.0, g)
    assert g['WIND_KT'] == 30.0
    assert g['V_WIND_MPS'] == 30.0 * KT_TO_MPS
