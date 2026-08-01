"""Shared coarse/fine parameter search grids.

粗搜：模块级 ``range(start, stop + 1, step)``。
精搜：在粗搜最优值附近，对该变量 ± 粗搜步长；精搜步长默认为 1。
甲板/平直段长度精搜：仅向更短方向搜索 ``[best - coarse_step, best)``，因更长甲板不会更优。
"""


def grid_step(grid) -> int:
    """Return step size of a coarse ``range`` or sorted sequence."""
    if isinstance(grid, range):
        return grid.step or 1
    vals = list(grid)
    if len(vals) < 2:
        return 1
    return vals[1] - vals[0]


def fine_range_symmetric(best, coarse_step, fine_step=1, min_val=None, max_val=None):
    """Fine search grid: best ± coarse_step (inclusive endpoints)."""
    lo = int(best) - coarse_step
    hi = int(best) + coarse_step
    if min_val is not None:
        lo = max(lo, min_val)
    if max_val is not None:
        hi = min(hi, max_val)
    return range(lo, hi + 1, fine_step)


def fine_range_deck(best, coarse_step, fine_step=1, min_val=0):
    """Fine search for deck/runway length: only lengths shorter than *best*."""
    lo = max(int(best) - coarse_step, min_val)
    hi = int(best)
    if lo >= hi:
        return range(0)
    return range(lo, hi, fine_step)
