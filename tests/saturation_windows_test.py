"""饱和打击拦截窗口单元测试。"""
from __future__ import annotations

from utils.saturation_windows import compute_windows


def test_compute_windows_default_params():
    """默认量级参数应形成多个窗口。"""
    windows = compute_windows(
        discovery_m=120_000,
        vm_mps=2.6 * 340,
        vi_mps=3.8 * 340,
        t_lock_s=6,
        min_range_m=3000,
    )
    assert len(windows) >= 2
    assert windows[0]['round'] == 1
    assert windows[0]['dist_start_m'] == 120_000
    assert windows[0]['dist_end_m'] < windows[0]['dist_start_m']


def test_compute_windows_zero_when_too_close():
    """发现距离过近时无窗口。"""
    windows = compute_windows(
        discovery_m=5000,
        vm_mps=2.6 * 340,
        vi_mps=3.8 * 340,
        t_lock_s=6,
        min_range_m=3000,
    )
    assert windows == []


def test_compute_windows_zero_closing_speed():
    """合速度非正时返回空列表。"""
    assert compute_windows(100000, 0, 0, 6, 3000) == []
