"""simulator_api 单元测试（小程序 / iOS 统一后端）。"""
from __future__ import annotations

import json

from apps.simulator_api import build_data_payload, handle_request


def test_get_api_data_returns_aircraft_and_carriers():
    status, headers, body = handle_request('GET', '/api/data', None)
    assert status == 200
    assert 'application/json' in headers['Content-Type']
    data = json.loads(body.decode())
    assert 'aircraft' in data and len(data['aircraft']) >= 1
    assert 'carriers' in data and len(data['carriers']) >= 1
    assert data['modes']['ski_jump'] == '滑跃起飞'


def test_options_returns_cors():
    status, headers, body = handle_request('OPTIONS', '/api/simulate', None)
    assert status == 204
    assert headers['Access-Control-Allow-Origin'] == '*'
    assert body == b''


def test_post_simulate_ski_jump_success():
    data = build_data_payload()
    carrier = next(c for c in data['carriers'] if c['id'] == 'SHANDONG')
    aircraft = next(a for a in data['aircraft'] if a['id'] == 'J-15')
    payload = {
        'mode': 'ski_jump',
        'aircraft': aircraft,
        'carrier': carrier,
        'mass_kg': 28000,
        'temp_c': 30,
        'wind_kt': carrier['max_speed_kt'],
        'total_deck_length_m': carrier['total_deck_length_m'],
        'ski_jump_angle_deg': carrier['ski_jump_angle_deg'],
    }
    status, _, body = handle_request('POST', '/api/simulate', json.dumps(payload).encode())
    assert status == 200
    result = json.loads(body.decode())
    assert 'success' in result
    assert 'output' in result


def test_unknown_route_404():
    status, _, body = handle_request('GET', '/unknown', None)
    assert status == 404
    assert json.loads(body.decode())['error'] == 'Not Found'


def test_post_simulate_invalid_payload_returns_json_not_500():
    """缺字段时不应抛未捕获异常（真机侧会显示 HTTP 500）。"""
    status, _, body = handle_request('POST', '/api/simulate', b'{}')
    assert status == 200
    result = json.loads(body.decode())
    assert result['success'] is False
    assert 'error' in result


def test_legacy_miniprogram_api_shim_reexports():
    """旧模块名仍可 import，与 simulator_api 为同一实现。"""
    from apps import miniprogram_api, simulator_api

    assert miniprogram_api.handle_request is simulator_api.handle_request
    assert miniprogram_api.build_data_payload is simulator_api.build_data_payload
