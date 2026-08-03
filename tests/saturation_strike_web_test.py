"""饱和打击 Web JSON API 单元测试。"""
from __future__ import annotations

import json

from apps.saturation_strike_web import run_saturation, run_saturation_json


def test_run_saturation_presets():
    """presets action 返回四类预设。"""
    r = run_saturation('presets')
    assert r['success'] is True
    assert 'asm' in r['presets']


def test_run_saturation_estimate_distance():
    """estimate_distance action。"""
    r = run_saturation('estimate_distance', {
        'rcs': 0.5, 'traj': 'high', 'awacs_area': 8, 'awacs_type': 'aesa',
        'standoff': 150, 'ship_area': 12, 'ship_type': 'aesa', 'sam_range': 40,
    })
    assert r['success'] is True
    assert r['engage_dist'] == 40


def test_run_saturation_estimate_pk():
    """estimate_pk action（忽略遗留 ecm 字段）。"""
    r = run_saturation('estimate_pk', {
        'vm': 2.6, 'vi': 3.8, 'rcs': 0.5, 'traj': 'high',
        'ship_area': 12, 'ship_type': 'aesa', 'interceptor_dia': 0.35,
        'seeker_type': 'active_aesa',
    })
    assert r['success'] is True
    assert 'pk' in r
    assert 'ecm_factor' not in r
    # 遗留 ecm 入参不得改变结果
    r2 = run_saturation('estimate_pk', {
        'vm': 2.6, 'vi': 3.8, 'rcs': 0.5, 'ecm': 5, 'traj': 'high',
        'ship_area': 12, 'ship_type': 'aesa', 'interceptor_dia': 0.35,
        'seeker_type': 'active_aesa',
    })
    assert r2['pk'] == r['pk']


def test_run_saturation_simulate_flat_payload():
    """扁平载荷可直接仿真。"""
    r = run_saturation_json({
        'nm': 24, 'vm': 2.6, 'D': 120, 'ni': 16, 'vi': 3.8,
        'pk': 0.7, 'tlock': 6, 'minr': 3, 'fast': True,
    })
    assert r['success'] is True
    assert r['n_rounds'] >= 1


def test_run_saturation_json_string():
    """JSON 字符串载荷可解析。"""
    payload = json.dumps({
        'action': 'simulate',
        'params': {
            'nm': 12, 'vm': 2.0, 'D': 100, 'ni': 8, 'vi': 3.5,
            'pk': 0.6, 'tlock': 5, 'minr': 3, 'fast': True,
        },
    })
    r = run_saturation_json(payload)
    assert r['success'] is True


def test_run_saturation_unknown_action():
    """未知 action 返回错误。"""
    r = run_saturation('nope')
    assert r['success'] is False
    assert '未知' in r['error']


def test_run_saturation_json_invalid():
    """非法 JSON 返回错误。"""
    r = run_saturation_json('{not json')
    assert r['success'] is False
