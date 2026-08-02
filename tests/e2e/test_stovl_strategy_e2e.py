"""STOVL 策略 A/B/C 端到端：短距起飞可选策略并返回结果。"""
from __future__ import annotations

import pytest

from apps.web_simulator import run_simulation
from utils.database_csv import load_aircraft_csv, load_carriers_csv
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV


@pytest.mark.e2e
def test_short_takeoff_strategies_abc_succeed():
    """平直甲板短距起飞：策略 A/B/C 均可找到可行解。"""
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)['F-35B']
    carrier = next(c for c in load_carriers_csv(CARRIERS_CSV) if c.id == 'WASP')
    for strategy in ('A', 'B', 'C'):
        result = run_simulation(
            'short_takeoff',
            aircraft,
            carrier,
            aircraft.a2a_mass_kg,
            30.0,
            carrier.max_speed_kt,
            strategy=strategy,
        )
        assert result['success'] is True, strategy
        assert result['strategy'] == strategy
        assert result['distance_m'] is not None and result['distance_m'] > 0
        assert f'策略 {strategy}' in result['output']


@pytest.mark.e2e
def test_short_ski_jump_strategy_b_succeeds():
    """短距滑跃策略 B 可找到可行解（相对 A 较快校验）。"""
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)['F-35B']
    carrier = next(c for c in load_carriers_csv(CARRIERS_CSV) if c.id == 'QE')
    result = run_simulation(
        'short_ski_jump',
        aircraft,
        carrier,
        aircraft.a2a_mass_kg,
        30.0,
        carrier.max_speed_kt,
        ski_jump_angle_deg=carrier.ski_jump_angle_deg,
        strategy='B',
    )
    assert result['success'] is True
    assert result['strategy'] == 'B'
    assert result['distance_m'] > 0
    assert '策略 B' in result['output']
