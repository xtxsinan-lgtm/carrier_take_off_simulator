"""饱和打击用简化雷达方程估算（探测距离 / 火控锁定 / 单发 Pk）。

仅为演示用启发式模型，不对应任何真实型号实测参数。
"""
from __future__ import annotations

import math
from typing import Any

# 雷达体制灵敏度倍率（相对机械扫描）
TECH_MULT: dict[str, float] = {
    'mechanical': 1.0,
    'pesa': 1.43,
    'aesa': 2.10,
    'gan_aesa': 3.74,
}

# 假设高度（米）
H_AWACS = 9000.0  # 预警机/预警直升机典型巡航高度
H_SHIP_RADAR = 25.0  # 舰载对空搜索雷达天线典型高度
H_TARGET: dict[str, float] = {
    'sea': 10.0,       # 掠海反舰导弹合理估计掠海高度
    'high': 12000.0,   # 高空巡航反舰导弹合理估计高度（原 15000 调整为更贴近实际的 12000）
}

# 火控锁定距离占搜索探测距离的比例
LOCK_FRACTION = 0.65

# Pk 基线（相对中等 RCS、无机动目标）
PK0 = 0.75


def clamp(x: float, lo: float, hi: float) -> float:
    """将数值限制在 [lo, hi]。"""
    return max(lo, min(hi, x))


def radar_horizon_km(h1: float, h2: float) -> float:
    """地球曲率雷达视距（公里）；h1/h2 为天线与目标高度（米）。"""
    return 4.12 * (math.sqrt(h1) + math.sqrt(h2))


def power_range_km(
    ref_range_km: float,
    area: float,
    ref_area: float,
    radar_type: str,
    rcs: float,
    ref_rcs: float,
) -> float:
    """功率受限探测距离（公里），按雷达方程比例关系缩放。"""
    mult = TECH_MULT.get(radar_type, 1.0)
    return ref_range_km * math.sqrt(area / ref_area) * (rcs / ref_rcs) ** 0.25 * mult


def target_altitude_m(traj: str) -> float:
    """按弹道类型返回目标高度估计（米）；未知弹道类型按高空弹道回退。"""
    return H_TARGET.get(traj, H_TARGET['high'])


def radar_gain_factor(area: float, radar_type: str, ref_area: float) -> float:
    """天线面积 + 体制的增益系数，归一到参考面积附近约 1.0。"""
    mult = TECH_MULT.get(radar_type, 1.0)
    g = math.sqrt(area / ref_area) * mult
    return clamp(0.55 + 0.45 * min(g, 1.6), 0.55, 1.25)


def estimate_engagement_distance(
    rcs: float,
    traj: str,
    awacs_area: float,
    awacs_type: str,
    standoff_km: float,
    ship_area: float,
    ship_type: str,
    sam_range_km: float,
    has_awacs: bool = True,
) -> dict[str, Any]:
    """估算预警机探测、舰载火控锁定与最终交战距离（公里）。

    - ``has_awacs=True``（默认，有预警机）：交战距离取
      ``min(预警机总探测距离, 舰载火控锁定距离, 拦截弹射程)``。
    - ``has_awacs=False``（无预警机）：不再有预警机前出探测，发现/交战距离仅由
      舰载雷达决定 —— 先取 ``ship_search = min(舰载雷达功率探测距离, 地球曲率雷达视距)``，
      再取 ``engage_dist = min(ship_search, 拦截弹射程)``（不再乘火控锁定折损系数，
      因为此时「发现」与「交战」都受限于同一部舰载雷达，直接取探测距离与射程的较小值）。
    """
    rcs = max(0.001, float(rcs))
    h_target = target_altitude_m(traj)
    awacs_area = max(0.1, float(awacs_area))
    standoff_km = max(0.0, float(standoff_km))
    ship_area = max(0.1, float(ship_area))
    sam_range_km = max(0.1, float(sam_range_km))
    has_awacs = bool(has_awacs)

    # 舰载雷达：参考 10 m² 天线对 5 m² RCS 探测 200 km（示意）
    ship_power = power_range_km(200.0, ship_area, 10.0, ship_type, rcs, 5.0)
    ship_horizon = radar_horizon_km(H_SHIP_RADAR, h_target)
    ship_search = min(ship_power, ship_horizon)
    ship_lock = ship_search * LOCK_FRACTION

    if has_awacs:
        # 预警机：参考 8 m² 天线对 5 m² RCS 探测 400 km（示意）
        awacs_power = power_range_km(400.0, awacs_area, 8.0, awacs_type, rcs, 5.0)
        awacs_horizon = radar_horizon_km(H_AWACS, h_target)
        awacs_detect = min(awacs_power, awacs_horizon)
        awacs_total = standoff_km + awacs_detect
        engage_dist = min(awacs_total, ship_lock, sam_range_km)
    else:
        # 无预警机：不使用预警机前出+探测（awacs_* 置零便于诊断/前端展示），
        # 交战距离直接取「舰载雷达探测」与「拦截弹射程」的最小值。
        awacs_power = 0.0
        awacs_horizon = 0.0
        awacs_detect = 0.0
        awacs_total = 0.0
        standoff_km = 0.0
        engage_dist = min(ship_search, sam_range_km)

    return {
        'awacs_power': awacs_power,
        'awacs_horizon': awacs_horizon,
        'awacs_detect': awacs_detect,
        'awacs_total': awacs_total,
        'ship_power': ship_power,
        'ship_horizon': ship_horizon,
        'ship_search': ship_search,
        'ship_lock': ship_lock,
        'sam_range': sam_range_km,
        'engage_dist': engage_dist,
        'standoff': standoff_km,
        'has_awacs': has_awacs,
        'h_target_m': h_target,
    }


def estimate_pk(
    vm_ma: float,
    vi_ma: float,
    rcs: float,
    traj: str,
    ship_area: float,
    ship_type: str,
    interceptor_dia_m: float,
    seeker_type: str,
) -> dict[str, Any]:
    """估算单发拦截成功概率 Pk 及各因子分解（不含抗干扰/干扰能力）。"""
    vm_ma = max(0.1, float(vm_ma))
    vi_ma = max(0.1, float(vi_ma))
    rcs = max(0.001, float(rcs))
    ship_area = max(0.1, float(ship_area))
    dia = max(0.05, float(interceptor_dia_m))

    # 速度比：来袭越快相对拦截弹越难末端修正
    ratio = vi_ma / vm_ma
    speed_factor = clamp(0.55 + 0.5 * min(ratio / 1.3, 1.2), 0.5, 1.1)

    ship_radar_factor = radar_gain_factor(ship_area, ship_type, 10.0)

    if seeker_type == 'semi_active':
        # 半主动依赖舰载照射，多目标能力通常弱于主动雷达
        seeker_factor = ship_radar_factor * 0.9
    else:
        seeker_area = math.pi * (dia / 2.0) ** 2
        seeker_tech = 'aesa' if seeker_type == 'active_aesa' else 'mechanical'
        # 参考：约 20 cm 口径导引头孔径
        seeker_factor = radar_gain_factor(seeker_area, seeker_tech, 0.03)

    rcs_factor = clamp(1.0 + 0.15 * math.log10(rcs / 0.5), 0.55, 1.15)
    traj_factor = 0.85 if traj == 'sea' else 1.0

    pk = clamp(
        PK0 * speed_factor * ship_radar_factor * seeker_factor * rcs_factor * traj_factor,
        0.03,
        0.97,
    )
    return {
        'pk': pk,
        'speed_factor': speed_factor,
        'ship_radar_factor': ship_radar_factor,
        'seeker_factor': seeker_factor,
        'rcs_factor': rcs_factor,
        'traj_factor': traj_factor,
    }


def binding_limit_label(result: dict[str, Any]) -> str:
    """返回交战距离受限于哪一项（中文标签）。

    用 ``math.isclose`` 做浮点近似比较，避免 ``==`` 在极端参数下因浮点误差误判；
    优先按 ``has_awacs`` 区分有/无预警机两条路径的判定顺序。
    """
    engage = result['engage_dist']
    has_awacs = bool(result.get('has_awacs', True))
    if has_awacs and math.isclose(engage, result['awacs_total'], rel_tol=0, abs_tol=1e-9):
        return '预警机总探测距离'
    if (not has_awacs) and math.isclose(engage, result['ship_search'], rel_tol=0, abs_tol=1e-9):
        return '舰载雷达探测距离（功率/视距）'
    if math.isclose(engage, result['ship_lock'], rel_tol=0, abs_tol=1e-9):
        return '舰载火控锁定距离'
    return '拦截弹射程'
