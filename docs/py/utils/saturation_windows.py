"""饱和打击拦截窗口几何：由发现距离、双方速度与火控锁定时间反推轮次。"""
from __future__ import annotations

from typing import Any


def compute_windows(
    discovery_m: float,
    vm_mps: float,
    vi_mps: float,
    t_lock_s: float,
    min_range_m: float,
    max_rounds: int = 200,
) -> list[dict[str, Any]]:
    """计算拦截窗口序列。

    所有来袭弹速度相同，故轮次时序与距离与存活数无关，可确定性推演。
    每轮时长 = 锁定时间 + 拦截弹迎头飞行时间；导弹在该轮持续接近。
    当轮末剩余距离 ≤ 最小交战距离时窗口关闭。
    """
    rounds: list[dict[str, Any]] = []
    distance = float(discovery_m)
    closing = float(vm_mps) + float(vi_mps)
    if closing <= 0:
        return rounds

    guard = 0
    while guard < max_rounds:
        guard += 1
        t_fly = distance / closing
        total_t = float(t_lock_s) + t_fly
        dist_after = distance - float(vm_mps) * total_t
        if dist_after <= float(min_range_m):
            break
        rounds.append({
            'round': len(rounds) + 1,
            'dist_start_m': distance,
            't_fly_s': t_fly,
            'total_t_s': total_t,
            'dist_end_m': dist_after,
        })
        distance = dist_after
    return rounds
