"""VTOL/STOVL 主喷管尾流安全距离模型（utils.takeoff.exhaust_plume）。

仅适用于可偏转主喷管向下/后方的 VTOL 飞机（如 F-35B、AV-8B）。
常规固定翼舰载机（滑跃起飞）不调用本模块——其发动机尾流不作甲板波及计算。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# F-35B 默认尾流参数（15°C 海平面 STOVL 标定）
EXHAUST_MDOT_KG_S = 147.0
EXHAUST_U0_MPS = 666.0
EXHAUST_D0_M = 1.04
EXHAUST_HEIGHT_M = 1.74
EXHAUST_USAFE_MPS = 25.0
EXHAUST_WALL_ETA = 0.70
EXHAUST_WALL_CW = 6.0
HORIZONTAL_JET_THETA_DEG = 5.0

# Rolls-Royce Pegasus（AV-8B）公开进气量：432 lb/s
PEGASUS_AIRFLOW_LB_S = 432.0
LB_S_TO_KG_S = 0.45359237


def lb_s_to_kg_s(lb_s: float) -> float:
    """质量流率 lb/s → kg/s。"""
    return lb_s * LB_S_TO_KG_S


def calc_exhaust_u0_from_thrust_mdot(thrust_n: float, mdot_kg_s: float) -> float:
    """由推力与质量流率估算四喷口同速假设下的排气速度 u₀ = T / ṁ（N·s/kg ≡ m/s）。"""
    if mdot_kg_s <= 0:
        raise ValueError('质量流率必须为正')
    return thrust_n / mdot_kg_s


def calc_exhaust_d0_equiv_four_nozzles(nozzle_diameter_m: float) -> float:
    """四等径矢量喷口合并为单股射流时的等效直径 d₀ = 2·d_n。"""
    if nozzle_diameter_m <= 0:
        raise ValueError('喷口直径必须为正')
    return 2.0 * nozzle_diameter_m


def calc_exhaust_d0_from_engine_diameter(engine_diameter_m: float, nozzle_count: int = 4) -> float:
    """由发动机外径粗估四喷口等效直径（喷口直径 ≈ D_engine / √n）。"""
    if engine_diameter_m <= 0 or nozzle_count < 1:
        raise ValueError('发动机直径与喷口数量必须为正')
    nozzle_d = engine_diameter_m / math.sqrt(nozzle_count)
    return calc_exhaust_d0_equiv_four_nozzles(nozzle_d)


def estimate_rcs_rollpost_thrust_n(bleed_mdot_kg_s: float, jet_velocity_mps: float = 340.0) -> float:
    """由 RCS 引气质量流率估算姿态控制喷管等效推力（用于滚转辅助项）。"""
    return bleed_mdot_kg_s * jet_velocity_mps


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


def default_exhaust_plume_params() -> ExhaustPlumeParams:
    """F-35B 默认尾流参数。"""
    return ExhaustPlumeParams()


def exhaust_plume_params_from_stovl(
    thrust_n: float,
    mdot_kg_s: float | None = None,
    d0_m: float | None = None,
    height_m: float | None = None,
    *,
    lb_s_airflow: float | None = None,
    nozzle_diameter_m: float | None = None,
    engine_diameter_m: float | None = None,
) -> ExhaustPlumeParams:
    """
    由 STOVL 推力与进气量构造尾流参数。

    ṁ 优先用 mdot_kg_s；否则由 lb_s_airflow 换算。
    u₀ = T / ṁ；d₀ 可由喷口直径或发动机外径估算。
    """
    if mdot_kg_s is None:
        if lb_s_airflow is None:
            raise ValueError('需提供 mdot_kg_s 或 lb_s_airflow')
        mdot_kg_s = lb_s_to_kg_s(lb_s_airflow)
    u0 = calc_exhaust_u0_from_thrust_mdot(thrust_n, mdot_kg_s)
    if d0_m is None:
        if nozzle_diameter_m is not None:
            d0_m = calc_exhaust_d0_equiv_four_nozzles(nozzle_diameter_m)
        elif engine_diameter_m is not None:
            d0_m = calc_exhaust_d0_from_engine_diameter(engine_diameter_m)
        else:
            d0_m = EXHAUST_D0_M
    return ExhaustPlumeParams(
        mdot_kg_s=mdot_kg_s,
        u0_mps=u0,
        d0_m=d0_m,
        height_m=height_m if height_m is not None else EXHAUST_HEIGHT_M,
    )


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
