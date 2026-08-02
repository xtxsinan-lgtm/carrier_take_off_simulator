"""轨迹 JSON 序列化与采样契约单元测试。"""
from __future__ import annotations

import json

from apps.web_simulator import _json_safe, run_simulation
from utils.database_csv import load_aircraft_csv, load_carriers_csv
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV


def test_json_safe_trajectory_payload_is_strict_json():
    """轨迹与甲板折线经 _json_safe 后可被标准 json.dumps 序列化。"""
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)['J-15']
    carrier = next(c for c in load_carriers_csv(CARRIERS_CSV) if c.id == 'SHANDONG')
    result = run_simulation(
        'ski_jump',
        aircraft,
        carrier,
        aircraft.a2a_mass_kg,
        30.0,
        carrier.max_speed_kt,
        ski_jump_angle_deg=carrier.ski_jump_angle_deg,
        ski_jump_height_m=carrier.ski_jump_height_m,
    )
    assert result['success'] is True
    assert result['trajectory']
    assert result['deck_profile']['points']

    payload = {
        'trajectory': _json_safe(result['trajectory']),
        'deck_profile': _json_safe(result['deck_profile']),
        'distance_m': result['distance_m'],
    }
    text = json.dumps(payload, ensure_ascii=False)
    loaded = json.loads(text)
    assert len(loaded['trajectory']) == len(result['trajectory'])
    assert loaded['trajectory'][0]['phase'] == 'flat'
    assert loaded['deck_profile']['takeoff_distance_m'] == result['distance_m']
