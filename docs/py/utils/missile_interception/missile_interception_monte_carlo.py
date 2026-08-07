"""饱和打击弹药分配：蒙特卡洛评估与局部爬山优化。"""
from __future__ import annotations

from typing import Any, Callable


def _to_i32(x: int) -> int:
    """转为有符号 32 位整数（对齐 JS `|0`）。"""
    x &= 0xFFFFFFFF
    if x >= 0x80000000:
        x -= 0x100000000
    return x


def _imul(a: int, b: int) -> int:
    """对齐 JS Math.imul 的 32 位有符号乘法。"""
    return _to_i32(_to_i32(a) * _to_i32(b))


def mulberry32(seed: int) -> Callable[[], float]:
    """确定性 PRNG（与前端 JS mulberry32 对齐），返回 [0,1) 浮点。"""
    state = _to_i32(seed)

    def rng() -> float:
        nonlocal state
        state = _to_i32(state + 0x6D2B79F5)
        t = _imul(state ^ ((state & 0xFFFFFFFF) >> 15), 1 | state)
        t = _to_i32(t + _imul(t ^ ((t & 0xFFFFFFFF) >> 7), 61 | t)) ^ t
        t = _to_i32(t)
        return ((_to_i32(t ^ ((t & 0xFFFFFFFF) >> 14)) & 0xFFFFFFFF) / 4294967296.0)

    return rng


def plan_key(plan: list[int]) -> str:
    """将弹药计划转为可比较的键。"""
    return ','.join(str(x) for x in plan)


def fix_sum(plan: list[int], target: int) -> None:
    """原地修正 plan 各元素之和等于 target（轮转增减）。"""
    s = sum(plan)
    i = 0
    while s != target:
        idx = i % len(plan)
        if s < target:
            plan[idx] += 1
            s += 1
        else:
            if plan[idx] > 0:
                plan[idx] -= 1
                s -= 1
        i += 1
        if i > 10000:
            break


def generate_candidate_plans(ni: int, n_rounds: int) -> list[dict[str, Any]]:
    """生成种子候选弹药分配方案。"""
    plans: list[dict[str, Any]] = []
    if n_rounds == 0:
        return plans
    r = n_rounds

    p0 = [0] * r
    p0[0] = ni
    plans.append({'name': '全部第一轮打光', 'plan': p0})

    p_eq = [0] * r
    base = ni // r
    rem = ni - base * r
    for i in range(r):
        p_eq[i] = base + (1 if i < rem else 0)
    plans.append({'name': '逐轮均分', 'plan': p_eq})

    weights = [1.6 ** (r - 1 - i) for i in range(r)]
    wsum = sum(weights)
    p_front = [round(ni * w / wsum) for w in weights]
    fix_sum(p_front, ni)
    plans.append({'name': '前重后轻', 'plan': p_front})

    weights_b = [1.6 ** i for i in range(r)]
    wsum_b = sum(weights_b)
    p_back = [round(ni * w / wsum_b) for w in weights_b]
    fix_sum(p_back, ni)
    plans.append({'name': '预留后重', 'plan': p_back})

    if r >= 3:
        mid = r // 2
        weights_m = [1.0 / (1.0 + abs(i - mid)) for i in range(r)]
        wsum_m = sum(weights_m)
        p_mid = [round(ni * w / wsum_m) for w in weights_m]
        fix_sum(p_mid, ni)
        plans.append({'name': '中段集中', 'plan': p_mid})

    return plans


def simulate_plan(
    nm: int,
    ni: int,
    pk: float,
    plan: list[int],
    trials: int,
    rng: Callable[[], float],
) -> dict[str, Any]:
    """蒙特卡洛评估逐轮弹药预算计划。

    plan[r] 为第 r 轮拦截弹预算（对该轮所有存活目标合计）。
    轮内预算尽量均分到各存活目标；未用完不自动滚存。
    """
    n_rounds = len(plan)
    leak_sum = 0.0
    survivors_by_round = [0.0] * (n_rounds + 1)

    for _ in range(trials):
        missiles = nm
        interceptors_left = ni
        survivors_by_round[0] += missiles
        for r in range(n_rounds):
            if missiles <= 0 or interceptors_left <= 0:
                survivors_by_round[r + 1] += missiles
                continue
            budget = min(plan[r], interceptors_left)
            base = budget // missiles
            extra = budget - base * missiles
            killed = 0
            used = 0
            for i in range(missiles):
                k = base + (1 if i < extra else 0)
                if k <= 0:
                    continue
                used += k
                p_kill = 1.0 - (1.0 - pk) ** k
                if rng() < p_kill:
                    killed += 1
            interceptors_left -= used
            missiles -= killed
            survivors_by_round[r + 1] += missiles
        leak_sum += missiles

    avg_survivors = [s / trials for s in survivors_by_round]
    return {
        'expected_leak': leak_sum / trials,
        'avg_survivors': avg_survivors,
    }


def optimize_plan(
    nm: int,
    ni: int,
    pk: float,
    n_rounds: int,
    search_trials: int = 900,
    final_trials: int = 6000,
    search_seed: int = 12345,
    final_seed: int = 999,
) -> dict[str, Any]:
    """在种子方案上爬山优化，再以高试验次数公平终评。"""
    search_rng = mulberry32(search_seed)
    candidates = generate_candidate_plans(ni, n_rounds)
    if not candidates:
        return {
            'best': {'name': '', 'plan': []},
            'final_res': {'expected_leak': float(nm), 'avg_survivors': [float(nm)]},
            'all_candidates': [],
            'final_trials': final_trials,
        }

    scored = []
    for c in candidates:
        score = simulate_plan(nm, ni, pk, c['plan'], search_trials, search_rng)['expected_leak']
        scored.append({'name': c['name'], 'plan': list(c['plan']), 'score': score})
    scored.sort(key=lambda x: x['score'])
    hill_plan = list(scored[0]['plan'])
    hill_score = scored[0]['score']

    improved = True
    iters = 0
    while improved and iters < 40 and n_rounds > 1:
        improved = False
        iters += 1
        for i in range(n_rounds):
            for j in range(n_rounds):
                if i == j or hill_plan[i] <= 0:
                    continue
                trial = list(hill_plan)
                trial[i] -= 1
                trial[j] += 1
                s = simulate_plan(nm, ni, pk, trial, search_trials, search_rng)['expected_leak']
                if s < hill_score - 1e-9:
                    hill_score = s
                    hill_plan = trial
                    improved = True

    final_rng = mulberry32(final_seed)
    pool = [{'name': c['name'], 'plan': list(c['plan'])} for c in candidates]
    if not any(plan_key(c['plan']) == plan_key(hill_plan) for c in pool):
        pool.append({'name': '优化方案(爬山搜索)', 'plan': list(hill_plan)})

    final_scored = []
    for c in pool:
        res = simulate_plan(nm, ni, pk, c['plan'], final_trials, final_rng)
        final_scored.append({
            'name': c['name'],
            'plan': c['plan'],
            'expected_leak': res['expected_leak'],
            'avg_survivors': res['avg_survivors'],
        })
    final_scored.sort(key=lambda x: x['expected_leak'])
    best = {'name': final_scored[0]['name'], 'plan': final_scored[0]['plan']}
    final_res = {
        'expected_leak': final_scored[0]['expected_leak'],
        'avg_survivors': final_scored[0]['avg_survivors'],
    }
    return {
        'best': best,
        'final_res': final_res,
        'all_candidates': final_scored,
        'final_trials': final_trials,
    }
