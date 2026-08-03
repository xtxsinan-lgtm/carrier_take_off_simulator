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
    """分别估算舰载/预警机雷达探测距离，并据此推算最终交战距离（公里）。

    两路探测独立估算：

    - 舰载雷达探测距离 ``ship_detect_km = min(舰载雷达功率探测距离 ship_power,
      地球曲率雷达视距 ship_horizon)``（即 ``ship_search``）。
    - 预警机雷达探测距离 ``awacs_detect_km``：``has_awacs=True`` 时为
      ``预警机前出距离 standoff_km + min(预警机雷达功率探测距离 awacs_power,
      预警机地球曲率雷达视距 awacs_horizon)``（即 ``awacs_total``）；
      ``has_awacs=False``（无预警机）时记为 0（同时不再计入预警机前出距离）。

    交战距离取两路探测中「更远」的一路（哪路先发现即以其为准，代表更好的态势提示/引导），
    再与拦截弹射程取较小值：

    ``engage_dist = min(max(awacs_detect_km, ship_detect_km), sam_range_km)``

    注：原「舰载火控锁定距离」``ship_lock = ship_detect_km * LOCK_FRACTION``
    仍会计算并在返回值中提供，仅供界面展示/诊断参考，不再参与 ``engage_dist`` 的计算。
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
    ship_detect_km = ship_search
    # 仅供展示/诊断，不参与 engage_dist 计算
    ship_lock = ship_search * LOCK_FRACTION

    if has_awacs:
        # 预警机：参考 8 m² 天线对 5 m² RCS 探测 400 km（示意）
        awacs_power = power_range_km(400.0, awacs_area, 8.0, awacs_type, rcs, 5.0)
        awacs_horizon = radar_horizon_km(H_AWACS, h_target)
        awacs_detect = min(awacs_power, awacs_horizon)
        awacs_total = standoff_km + awacs_detect
        awacs_detect_km = awacs_total
    else:
        # 无预警机：不使用预警机前出+探测（awacs_* 置零便于诊断/前端展示）
        awacs_power = 0.0
        awacs_horizon = 0.0
        awacs_detect = 0.0
        awacs_total = 0.0
        awacs_detect_km = 0.0
        standoff_km = 0.0

    # 交战距离＝两路探测取更远者（更好的态势提示），再与拦截弹射程取较小值
    detect_max_km = max(awacs_detect_km, ship_detect_km)
    engage_dist = min(detect_max_km, sam_range_km)

    return {
        'awacs_power': awacs_power,
        'awacs_horizon': awacs_horizon,
        'awacs_detect': awacs_detect,
        'awacs_total': awacs_total,
        'awacs_detect_km': awacs_detect_km,
        'ship_power': ship_power,
        'ship_horizon': ship_horizon,
        'ship_search': ship_search,
        'ship_detect_km': ship_detect_km,
        'ship_lock': ship_lock,
        'detect_max_km': detect_max_km,
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

    新公式下 ``engage_dist = min(max(awacs_detect_km, ship_detect_km), sam_range_km)``，
    判定顺序为：先看是否被拦截弹射程封顶；否则看两路探测中较远的一路 —— 若为预警机
    雷达探测距离（且预警机确实是更远的一路）则归为预警机，否则归为舰载雷达探测距离；
    用 ``math.isclose`` 做浮点近似比较，避免 ``==`` 在极端参数下因浮点误差误判。
    """
    engage = result['engage_dist']
    sam_range = result['sam_range']
    has_awacs = bool(result.get('has_awacs', True))
    awacs_detect_km = result.get('awacs_detect_km', result.get('awacs_total', 0.0))
    ship_detect_km = result.get('ship_detect_km', result.get('ship_search', 0.0))

    if math.isclose(engage, sam_range, rel_tol=0, abs_tol=1e-9):
        return '拦截弹射程'
    awacs_is_farther = has_awacs and awacs_detect_km >= ship_detect_km
    if awacs_is_farther and math.isclose(engage, awacs_detect_km, rel_tol=0, abs_tol=1e-9):
        return '预警机雷达探测距离'
    if math.isclose(engage, ship_detect_km, rel_tol=0, abs_tol=1e-9):
        return '舰载雷达探测距离'
    return '拦截弹射程'
