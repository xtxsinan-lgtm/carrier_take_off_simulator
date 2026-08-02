"""倾转短距起飞端到端测试。"""
from __future__ import annotations

import pytest

from apps.web_simulator import (
    TILTROTOR_STRATEGIES,
    filter_aircraft_for_mode,
    normalize_tiltrotor_strategy,
    run_simulation,
)
from utils.database_csv import load_aircraft_csv, load_carriers_csv
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV


def test_normalize_tiltrotor_strategy_rejects_c():
    with pytest.raises(ValueError, match='A/B'):
        normalize_tiltrotor_strategy('C')


def test_filter_aircraft_tiltrotor_mode_only_mv22():
    aircraft = list(load_aircraft_csv(AIRCRAFT_CSV).values())
    ids = {a.id for a in filter_aircraft_for_mode('tiltrotor_short_takeoff', aircraft)}
    assert ids == {'MV-22'}


@pytest.mark.e2e
def test_tiltrotor_short_takeoff_strategies_ab():
    """MV-22 在平直甲板上策略 A/B 均可找到可行解。"""
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)['MV-22']
    carrier = next(c for c in load_carriers_csv(CARRIERS_CSV) if c.id == 'WASP')
    for strategy in ('A', 'B'):
        result = run_simulation(
            'tiltrotor_short_takeoff',
            aircraft,
            carrier,
            aircraft.a2a_mass_kg,
            30.0,
            carrier.max_speed_kt,
            strategy=strategy,
        )
        assert result['success'] is True, strategy
        assert result['strategy'] == strategy
        assert result['distance_m'] > 0
        assert result['trajectory'] is None
        assert result['plume_applicable'] is False
        assert f'策略 {strategy}' in result['output']
        assert TILTROTOR_STRATEGIES[strategy] in result['output']
