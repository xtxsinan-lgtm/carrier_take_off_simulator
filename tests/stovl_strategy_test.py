"""STOVL 策略选择单元测试。"""
from __future__ import annotations

import pytest

from apps.web_simulator import (
    STOVL_STRATEGIES,
    normalize_stovl_strategy,
    run_stovl_strategy_search,
)
import simulators.short_take_off as flat


def test_normalize_stovl_strategy_default_and_case():
    assert normalize_stovl_strategy(None) == 'A'
    assert normalize_stovl_strategy('') == 'A'
    assert normalize_stovl_strategy('b') == 'B'
    assert normalize_stovl_strategy('C') == 'C'


def test_normalize_stovl_strategy_rejects_unknown():
    with pytest.raises(ValueError, match='未知 STOVL 策略'):
        normalize_stovl_strategy('Z')


def test_stovl_strategies_labels_cover_abc():
    assert set(STOVL_STRATEGIES) == {'A', 'B', 'C'}


def test_run_stovl_strategy_search_dispatches_b():
    result = run_stovl_strategy_search(flat, 'B')
    assert result is not None
    assert result['x_m'] > 0
