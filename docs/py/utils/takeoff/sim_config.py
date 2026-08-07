"""Shared simulation configuration helpers (module-global mutators)."""
from utils.takeoff.takeoff_physics import KT_TO_MPS, wind_knots_to_mps


def apply_wind_knots_globals(wind_kt, globals_dict, kt_to_mps=KT_TO_MPS):
    globals_dict['WIND_KT'] = wind_kt
    globals_dict['V_WIND_MPS'] = wind_knots_to_mps(wind_kt, kt_to_mps)
