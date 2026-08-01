"""Shared atmosphere, aero, units, and flight-limit helpers for carrier takeoff simulators."""
import numpy as np

# ---------------------------------------------------------------------------
# Atmosphere / thrust temperature reference
# ---------------------------------------------------------------------------
T_THRUST_REF_C = 15.0
RHO_ISA_KG_M3 = 1.225
THRUST_TEMP_EXPONENT = 0.85

# ---------------------------------------------------------------------------
# Physical units
# ---------------------------------------------------------------------------
G = 9.81
KT_TO_MPS = 0.514444
M_TO_FT = 3.28084
MPS_TO_KT = 1.94384

# ---------------------------------------------------------------------------
# Flap / incidence defaults (STOVL & conventional)
# ---------------------------------------------------------------------------
FLAP_DEFLECTION_DEG = 20
FLAP_EFFICIENCY = 0.5
WING_INCIDENCE_DEG = 2

# ---------------------------------------------------------------------------
# Flight limits
# ---------------------------------------------------------------------------
PITCH_MAX_DEG = 20


def calc_sea_level_density_kg_m3(ambient_temp_c, reference_temp_c=T_THRUST_REF_C):
    """海平面空气密度，kg/m³；同压强下 ρ ∝ 1/T。"""
    t_ref_k = reference_temp_c + 273.15
    t_amb_k = ambient_temp_c + 273.15
    return RHO_ISA_KG_M3 * t_ref_k / t_amb_k


def calc_thrust_temp_factor(ambient_temp_c, reference_temp_c=T_THRUST_REF_C,
                            exponent=THRUST_TEMP_EXPONENT):
    """相对 reference_temp_c 标定推力的温度衰减系数。"""
    t_ref_k = reference_temp_c + 273.15
    t_amb_k = ambient_temp_c + 273.15
    return (t_ref_k / t_amb_k) ** exponent


def calc_oswald_e(aspect_ratio, sweep_le_deg):
    """η = 4.61(1 - 0.045·AR^0.68)(cos Λ)^0.15 - 3.1"""
    sweep_rad = np.radians(sweep_le_deg)
    return 4.61 * (1 - 0.045 * aspect_ratio ** 0.68) * (np.cos(sweep_rad) ** 0.15) - 3.1


def calc_cl_alpha(aspect_ratio, oswald_e, sweep_le_deg):
    """C_Lα = 2π·AR / (2 + √(4 + (AR²/η²)(1 + tan²Λ)))，单位 /rad"""
    sweep_rad = np.radians(sweep_le_deg)
    denom = 2 + np.sqrt(4 + (aspect_ratio ** 2 / oswald_e ** 2) * (1 + np.tan(sweep_rad) ** 2))
    return 2 * np.pi * aspect_ratio / denom


def calc_cl_from_alpha_deg(alpha_deg, cl_alpha):
    return np.radians(alpha_deg) * cl_alpha


def calc_ground_effect_phi(wing_height_m, wingspan_m):
    """Torenbeek 地面效应修正因子 φ。"""
    x = 16 * wing_height_m / wingspan_m
    return x * x / (1 + x * x)


def taxi_alpha_deg(fldef_deg=FLAP_DEFLECTION_DEG, flap_efficiency=FLAP_EFFICIENCY,
                   wing_incidence_deg=WING_INCIDENCE_DEG):
    """滑行等效迎角，°。"""
    return fldef_deg * flap_efficiency + wing_incidence_deg


def dynamic_pressure(rho, airspeed_mps):
    """动压 q = ½·ρ·V²，Pa"""
    return 0.5 * rho * airspeed_mps * airspeed_mps


def drag_coefficient(cd0, k_ind, cl, phi_ground):
    """阻力系数 Cd = Cd0 + k·Cl²·φ（含地面效应修正）"""
    return cd0 + k_ind * cl * cl * phi_ground


def check_pitch_deg(pitch_deg, pitch_max_deg=PITCH_MAX_DEG):
    """校验俯仰角不超过硬上限；超限则抛出 ValueError。"""
    if pitch_deg > pitch_max_deg:
        raise ValueError(f"俯仰角 {pitch_deg}° 超过硬上限 {pitch_max_deg}°")
    return pitch_deg


def wind_knots_to_mps(wind_kt, kt_to_mps=KT_TO_MPS):
    return wind_kt * kt_to_mps
