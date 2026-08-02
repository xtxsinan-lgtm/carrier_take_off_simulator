"""饱和打击蒙特卡洛与计划优化单元测试。"""
from __future__ import annotations

from utils.saturation_monte_carlo import (
    fix_sum,
    generate_candidate_plans,
    mulberry32,
    optimize_plan,
    plan_key,
    simulate_plan,
)


def test_mulberry32_deterministic():
    """同一种子产生相同序列。"""
    a = mulberry32(12345)
    b = mulberry32(12345)
    assert [a() for _ in range(5)] == [b() for _ in range(5)]
    vals = [mulberry32(999)() for _ in range(3)]
    assert all(0 <= v < 1 for v in vals)


def test_plan_key():
    """计划键为逗号连接。"""
    assert plan_key([7, 4, 3, 2]) == '7,4,3,2'


def test_fix_sum():
    """修正后总和等于目标。"""
    p = [1, 1, 1]
    fix_sum(p, 10)
    assert sum(p) == 10
    assert all(x >= 0 for x in p)


def test_generate_candidate_plans_empty_rounds():
    """零轮次无候选。"""
    assert generate_candidate_plans(16, 0) == []


def test_generate_candidate_plans_includes_equal_split():
    """候选含均分且总和为 Ni。"""
    plans = generate_candidate_plans(16, 4)
    names = [c['name'] for c in plans]
    assert '逐轮均分' in names
    assert '全部第一轮打光' in names
    for c in plans:
        assert sum(c['plan']) == 16


def test_simulate_plan_leak_between_zero_and_nm():
    """期望突防落在 [0, Nm]。"""
    rng = mulberry32(1)
    res = simulate_plan(24, 16, 0.7, [8, 4, 2, 2], trials=200, rng=rng)
    assert 0 <= res['expected_leak'] <= 24
    assert len(res['avg_survivors']) == 5


def test_optimize_plan_returns_best():
    """优化返回最优方案与候选列表。"""
    opt = optimize_plan(24, 16, 0.7, 4, search_trials=100, final_trials=200)
    assert opt['best']['plan']
    assert sum(opt['best']['plan']) == 16
    assert opt['all_candidates']
    assert opt['final_res']['expected_leak'] <= opt['all_candidates'][-1]['expected_leak']


def test_optimize_plan_zero_rounds():
    """零轮次返回空计划。"""
    opt = optimize_plan(24, 16, 0.7, 0)
    assert opt['best']['plan'] == []
    assert opt['final_res']['expected_leak'] == 24
