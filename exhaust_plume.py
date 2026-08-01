"""Shared STOVL main-engine exhaust plume safety-distance model."""
from dataclasses import dataclass

import numpy as np

# F-35B default exhaust parameters
EXHAUST_MDOT_KG_S = 147.0
EXHAUST_U0_MPS = 666.0
EXHAUST_D0_M = 1.04
EXHAUST_HEIGHT_M = 1.74
EXHAUST_USAFE_MPS = 25.0
EXHAUST_WALL_ETA = 0.70
EXHAUST_WALL_CW = 6.0
HORIZONTAL_JET_THETA_DEG = 5.0


@dataclass(frozen=True)
class ExhaustPlumeParams:
    mdot_kg_s: float = EXHAUST_MDOT_KG_S
    u0_mps: float = EXHAUST_U0_MPS
    d0_m: float = EXHAUST_D0_M
    height_m: float = EXHAUST_HEIGHT_M
    usafe_mps: float = EXHAUST_USAFE_MPS
    wall_eta: float = EXHAUST_WALL_ETA
    wall_cw: float = EXHAUST_WALL_CW
    horizontal_jet_theta_deg: float = HORIZONTAL_JET_THETA_DEG


def calc_exhaust_safe_distance_m(theta_deg, u_wind_mps, rho,
                                 params: ExhaustPlumeParams = ExhaustPlumeParams()):
    """
    尾流衰减至安全阈值所需的水平向后距离，m（两段模型：自由射流 + 撞地壁面射流）。

    θ：喷流中心线与水平面夹角（自水平量起，向后下方为正），°
    u_wind_mps：甲板风，与尾流同向分量（顶风放飞时为正），m/s
    """
    a0 = np.pi / 4 * params.d0_m ** 2
    rho0 = params.mdot_kg_s / (a0 * params.u0_mps)
    k = 6.2 * np.sqrt(rho0 / rho) * params.d0_m

    d_u0 = max(params.u0_mps - u_wind_mps, 0.0)
    if u_wind_mps >= params.usafe_mps:
        return np.inf

    target_plume = params.usafe_mps - u_wind_mps
    if target_plume >= d_u0:
        return 0.0

    x_baseline = k * d_u0 / target_plume
    if theta_deg < params.horizontal_jet_theta_deg:
        return x_baseline

    theta_rad = np.radians(min(theta_deg, 89.9))
    l_impinge = params.height_m / np.sin(theta_rad)
    horiz_offset = params.height_m / np.tan(theta_rad)

    d_ui = min(d_u0, d_u0 * k / max(l_impinge, 0.01))
    f_wall = params.wall_eta * params.mdot_kg_s * d_u0 * np.cos(theta_rad)
    wall_coeff = params.wall_cw * np.sqrt(max(f_wall, 0.0) / rho)

    r_safe = 0.0
    if target_plume < d_ui:
        r_safe = max(0.0, wall_coeff / target_plume - params.d0_m)

    return horiz_offset + r_safe


def calc_exhaust_theta_deg_for_safe_distance_m(max_safe_m, u_wind_mps, rho,
                                             params: ExhaustPlumeParams = ExhaustPlumeParams()):
    """
    calc_exhaust_safe_distance_m 的反函数：给定允许的最大安全距离，求最小喷流角 θ（°）。

    即满足 safe(θ) ≤ max_safe_m 的最小 θ。
    """
    if u_wind_mps >= params.usafe_mps or max_safe_m <= 0:
        return 89.9

    d_u0 = max(params.u0_mps - u_wind_mps, 0.0)
    target_plume = params.usafe_mps - u_wind_mps
    if target_plume >= d_u0:
        return params.horizontal_jet_theta_deg

    a0 = np.pi / 4 * params.d0_m ** 2
    rho0 = params.mdot_kg_s / (a0 * params.u0_mps)
    k = 6.2 * np.sqrt(rho0 / rho) * params.d0_m
    x_baseline = k * d_u0 / target_plume

    if max_safe_m >= x_baseline:
        return params.horizontal_jet_theta_deg

    lo, hi = params.horizontal_jet_theta_deg, 89.9
    while hi - lo > 0.05:
        mid = (lo + hi) / 2.0
        if calc_exhaust_safe_distance_m(mid, u_wind_mps, rho, params) > max_safe_m:
            lo = mid
        else:
            hi = mid
    return hi


def calc_min_nozzle_deg_for_plume(x_m, min_safe_distance_m, u_wind_mps, deck_angle_deg,
                                  rho, params: ExhaustPlumeParams = ExhaustPlumeParams()):
    """位置 x 处满足尾流约束的最小喷口偏转角（°）；deck_angle_deg 为当前甲板切线角。"""
    max_safe_m = x_m - min_safe_distance_m
    theta_total = calc_exhaust_theta_deg_for_safe_distance_m(max_safe_m, u_wind_mps, rho, params)
    return max(0.0, theta_total - deck_angle_deg)


def update_min_plume_trailing_edge_m(x_m, theta_deg, u_wind_mps, current_min_m, rho,
                                     params: ExhaustPlumeParams = ExhaustPlumeParams()):
    """
    更新甲板上受影响最后缘位置，m：滑跑全程 min(x − 安全距离)。

    即尾流后缘在甲板上到达的最靠后（x 最小）位置。
    """
    safe_m = calc_exhaust_safe_distance_m(theta_deg, u_wind_mps, rho, params)
    if np.isinf(safe_m):
        return current_min_m
    edge_m = x_m - safe_m
    if current_min_m is None:
        return edge_m
    return min(current_min_m, edge_m)
