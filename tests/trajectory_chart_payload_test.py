"""小程序轨迹面板数据裁剪约定测试。"""
from __future__ import annotations

from apps.web_simulator import run_simulation
from utils.database_csv import load_aircraft_csv, load_carriers_csv
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV


def test_ski_jump_chart_payload_fields_sufficient():
    """前端轨迹组件只需 trajectory / deck_profile / distance_m。"""
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
    chart = {
        'trajectory': result['trajectory'],
        'deck_profile': result['deck_profile'],
        'distance_m': result['distance_m'],
    }
    assert chart['trajectory'] and chart['deck_profile']['points']
    assert all(k in chart['trajectory'][0] for k in ('x', 'y', 't', 'phase'))
    # 完整结果应远大于裁剪后的绘图包（含长文本 output）
    assert len(result.get('output') or '') > 100
