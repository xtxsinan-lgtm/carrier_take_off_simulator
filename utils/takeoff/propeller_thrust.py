"""涡桨 / 倾转旋翼：由轴功率与桨盘面积估算推力（含短舱遮挡）。"""
from __future__ import annotations

import math

# 默认桨盘品质因数（倾转旋翼悬停量级估计）
DEFAULT_FIGURE_OF_MERIT = 0.78
# 默认短舱/桨毂对桨盘的遮挡面积比（推力等效折减）
DEFAULT_NACELLE_BLOCKAGE_FRAC = 0.10


def calc_prop_disk_area_m2(diameter_m: float, n_rotors: int = 2) -> float:
    """由桨盘直径与旋翼数量计算总桨盘面积，m²。"""
    if diameter_m <= 0:
        raise ValueError('桨盘直径必须为正')
    if n_rotors < 1:
        raise ValueError('旋翼数量至少为 1')
    r = diameter_m / 2.0
    return n_rotors * math.pi * r * r


def calc_effective_disk_area_m2(
    disk_area_m2: float,
    nacelle_blockage_frac: float = DEFAULT_NACELLE_BLOCKAGE_FRAC,
) -> float:
    """扣除短舱遮挡后的有效桨盘面积，m²。"""
    if disk_area_m2 <= 0:
        raise ValueError('桨盘面积必须为正')
    frac = min(max(float(nacelle_blockage_frac), 0.0), 0.5)
    return disk_area_m2 * (1.0 - frac)


def calc_ideal_static_thrust_n(power_w: float, rho: float, disk_area_m2: float) -> float:
    """动量理论静推力：T = (P² · 2ρA)^(1/3)。"""
    if power_w <= 0 or rho <= 0 or disk_area_m2 <= 0:
        return 0.0
    return (power_w * power_w * 2.0 * rho * disk_area_m2) ** (1.0 / 3.0)


def calc_ideal_thrust_with_axial_speed_n(
    power_w: float,
    rho: float,
    disk_area_m2: float,
    v_axial_mps: float,
) -> float:
    """
    轴向来流下的理想推力（动量理论）。

    功率关系：P = T · (V/2 + sqrt((V/2)² + T/(2ρA)))。
    V=0 时退化为静推力闭式解；V>0 时用牛顿迭代求 T。
    """
    if power_w <= 0 or rho <= 0 or disk_area_m2 <= 0:
        return 0.0
    v = max(float(v_axial_mps), 0.0)
    if v < 1e-9:
        return calc_ideal_static_thrust_n(power_w, rho, disk_area_m2)

    kappa = 2.0 * rho * disk_area_m2
    # 初值：静推力与功率受限推力的较小者量级
    t = min(calc_ideal_static_thrust_n(power_w, rho, disk_area_m2), power_w / max(v, 1e-3))
    t = max(t, 1.0)

    for _ in range(40):
        u = 0.5 * v
        root = math.sqrt(u * u + t / kappa)
        f = t * (u + root) - power_w
        # d/dt [t*(u+sqrt(u²+t/κ))] = u + root + t/(2κ·root)
        df = u + root + t / (2.0 * kappa * root)
        if abs(df) < 1e-12:
            break
        t_new = t - f / df
        if t_new <= 0:
            t_new = 0.5 * t
        if abs(t_new - t) < 1e-3:
            return t_new
        t = t_new
    return max(t, 0.0)


def calc_propeller_thrust_n(
    power_w: float,
    rho: float,
    disk_area_m2: float,
    v_axial_mps: float = 0.0,
    figure_of_merit: float = DEFAULT_FIGURE_OF_MERIT,
    nacelle_blockage_frac: float = DEFAULT_NACELLE_BLOCKAGE_FRAC,
) -> float:
    """
    实际可用推力：理想动量推力 × 品质因数，桨盘面积先扣除短舱遮挡。

    figure_of_merit 综合桨叶型阻、非理想诱导等损失（典型倾转旋翼 0.75–0.82）。
    """
    a_eff = calc_effective_disk_area_m2(disk_area_m2, nacelle_blockage_frac)
    t_ideal = calc_ideal_thrust_with_axial_speed_n(power_w, rho, a_eff, v_axial_mps)
    fm = min(max(float(figure_of_merit), 0.1), 1.0)
    return fm * t_ideal
