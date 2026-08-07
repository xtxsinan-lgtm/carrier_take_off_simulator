"""滑跃甲板圆弧几何：入口切线水平，出口切线角 = 资料给定滑跃角。

仅需出口切线角（°）；可选跳台唇口高度 h（m）确定圆弧半径 R = h / (1 − cos α)。
未给高度时用参考半径 SKI_JUMP_REF_RADIUS_M，弧长/水平投影/高度均由 R 与 α 导出。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from utils.takeoff_config import physics_config

# 仅给定滑跃角、无唇口高度时的参考圆弧半径，m（典型 STOBAR 量级）
SKI_JUMP_REF_RADIUS_M = float(physics_config()['ski_jump_ref_radius_m'])


@dataclass(frozen=True)
class SkiJumpArc:
    angle_deg: float
    angle_rad: float
    radius_m: float
    arc_length_m: float
    horizontal_m: float
    lip_height_m: float

    @property
    def cos_exit(self) -> float:
        return math.cos(self.angle_rad)

    @property
    def sin_exit(self) -> float:
        return math.sin(self.angle_rad)


def compute_ski_jump_arc(angle_deg: float, lip_height_m: float | None = None,
                         radius_m: float | None = None) -> SkiJumpArc:
    """
    计算圆弧滑跃段几何。

    优先级：显式 radius_m > lip_height_m > 参考半径。
    """
    if angle_deg <= 0:
        raise ValueError('滑跃角必须为正')
    angle_rad = math.radians(angle_deg)
    if radius_m is not None and radius_m > 0:
        r = radius_m
        h = r * (1.0 - math.cos(angle_rad))
    elif lip_height_m is not None and lip_height_m > 0:
        h = lip_height_m
        r = h / (1.0 - math.cos(angle_rad))
    else:
        r = SKI_JUMP_REF_RADIUS_M
        h = r * (1.0 - math.cos(angle_rad))
    arc_length = r * angle_rad
    horizontal = r * math.sin(angle_rad)
    return SkiJumpArc(
        angle_deg=angle_deg,
        angle_rad=angle_rad,
        radius_m=r,
        arc_length_m=arc_length,
        horizontal_m=horizontal,
        lip_height_m=h,
    )


def deck_angle_rad_at_s(s_m: float, arc: SkiJumpArc) -> float:
    """沿弧长 s 处甲板切线与水平面夹角（rad），0 → 出口角。"""
    if s_m <= 0:
        return 0.0
    return min(s_m / arc.radius_m, arc.angle_rad)


def deck_angle_deg_at_s(s_m: float, arc: SkiJumpArc) -> float:
    return math.degrees(deck_angle_rad_at_s(s_m, arc))


def deck_cos_sin_at_s(s_m: float, arc: SkiJumpArc) -> tuple[float, float]:
    phi = deck_angle_rad_at_s(s_m, arc)
    return math.cos(phi), math.sin(phi)


def horizontal_at_s(s_m: float, arc: SkiJumpArc) -> float:
    """自滑跃入口起累计水平距离，m。"""
    phi = deck_angle_rad_at_s(s_m, arc)
    return arc.radius_m * math.sin(phi)


def deck_height_at_s(s_m: float, arc: SkiJumpArc) -> float:
    """沿弧长 s 处甲板表面相对平甲板的高度，m。"""
    phi = deck_angle_rad_at_s(s_m, arc)
    return arc.radius_m * (1.0 - math.cos(phi))
