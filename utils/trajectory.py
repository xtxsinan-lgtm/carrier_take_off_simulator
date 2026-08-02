"""起飞轨迹采样辅助模块。"""
from __future__ import annotations

TRAJECTORY_SAMPLE_DT = 0.08


class TrajectoryRecorder:
    """按时间间隔向列表写入 (x, y, t, phase) 点。"""

    def __init__(self, trajectory: list[dict] | None, sample_dt: float = TRAJECTORY_SAMPLE_DT):
        self.trajectory = trajectory
        self.sample_dt = sample_dt
        self._last_t = -1e9

    def record(self, x: float, y: float, t: float, phase: str, *, force: bool = False) -> None:
        if self.trajectory is None:
            return
        if force or not self.trajectory or t - self._last_t >= self.sample_dt:
            self.trajectory.append({
                'x': round(float(x), 3),
                'y': round(float(y), 3),
                't': round(float(t), 3),
                'phase': phase,
            })
            self._last_t = t


def build_flat_deck_profile(total_deck_length_m: float) -> dict:
    """平直甲板折线（无滑跃段），供短距 STOVL 轨迹绘制。"""
    length = float(total_deck_length_m)
    return {
        'flat_length_m': length,
        'ski_jump_angle_deg': 0.0,
        'lip_height_m': 0.0,
        'horizontal_m': 0.0,
        'arc_length_m': 0.0,
        'radius_m': 0.0,
        'points': [[0.0, 0.0], [round(length, 3), 0.0]],
    }


def build_deck_profile(flat_length_m: float, arc) -> dict:
    """生成甲板折线（水平 x、高度 y），供前端绘制。"""
    from utils.ski_jump_geometry import deck_height_at_s, horizontal_at_s

    points: list[list[float]] = [[0.0, 0.0], [float(flat_length_m), 0.0]]
    n = max(24, int(arc.arc_length_m / 2))
    for i in range(1, n + 1):
        s = arc.arc_length_m * i / n
        points.append([
            round(flat_length_m + horizontal_at_s(s, arc), 3),
            round(deck_height_at_s(s, arc), 3),
        ])
    return {
        'flat_length_m': float(flat_length_m),
        'ski_jump_angle_deg': arc.angle_deg,
        'lip_height_m': arc.lip_height_m,
        'horizontal_m': arc.horizontal_m,
        'arc_length_m': arc.arc_length_m,
        'radius_m': arc.radius_m,
        'points': points,
    }
