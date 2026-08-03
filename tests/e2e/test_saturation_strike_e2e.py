"""饱和打击端到端测试：全链路仿真与估算。"""
from __future__ import annotations

import json

import pytest

from apps.miniprogram_api import handle_request
from apps.saturation_strike_web import run_saturation_json
from simulators.saturation_strike import run_saturation_strike


@pytest.mark.e2e
def test_e2e_saturation_default_params():
    """默认参数全链路：窗口、最优方案、期望突防与策略表。"""
    result = run_saturation_strike(
        nm=24, vm_ma=2.6, discovery_km=120, ni=16, vi_ma=3.8,
        pk=0.7, t_lock_s=6, min_range_km=3,
    )
    assert result['success'] is True
    assert result['n_rounds'] == 4
    assert result['windows'][0]['dist_start_km'] == pytest.approx(120.0)
    assert result['best']['plan']
    assert sum(result['best']['plan']) == 16
    assert 0 < result['expected_leak'] < 24
    assert len(result['all_candidates']) >= 4
    assert result['final_trials'] == 6000
    assert '期望突防' in result['note'] or '突防' in result['note']


@pytest.mark.e2e
def test_e2e_saturation_zero_windows():
    """边界：无窗口时突防等于来袭。"""
    result = run_saturation_json({
        'action': 'simulate',
        'params': {
            'nm': 8, 'vm': 3, 'D': 4, 'ni': 10, 'vi': 3,
            'pk': 0.7, 'tlock': 8, 'minr': 3, 'fast': True,
        },
    })
    assert result['success'] is True
    assert result['n_rounds'] == 0
    assert result['expected_leak'] == 8


@pytest.mark.e2e
def test_e2e_saturation_estimate_paths():
    """合并估算按钮依赖的交战距离 + 拦截率（Pk）路径均可用。"""
    params = {
        'rcs': 0.5, 'traj': 'high', 'awacs_area': 8, 'awacs_type': 'aesa',
        'standoff': 150, 'ship_area': 12, 'ship_type': 'aesa', 'sam_range': 40,
        'vm': 2.6, 'vi': 3.8, 'interceptor_dia': 0.35,
        'seeker_type': 'active_aesa',
    }
    # 与三端 onEstimateDistanceAndPk / estimateDistanceAndPk 调用顺序一致
    dist = run_saturation_json({'action': 'estimate_distance', 'params': params})
    assert dist['success'] is True
    assert dist['engage_dist'] == pytest.approx(40.0)
    assert dist['binding']

    pk = run_saturation_json({'action': 'estimate_pk', 'params': params})
    assert pk['success'] is True
    assert 0.03 <= pk['pk'] <= 0.97
    assert 'ecm_factor' not in pk
    # 遗留抗干扰档数不得影响拦截率估算
    pk_hi = run_saturation_json({
        'action': 'estimate_pk',
        'params': {**params, 'ecm': 5},
    })
    assert pk_hi['pk'] == pk['pk']


@pytest.mark.e2e
def test_e2e_saturation_estimate_distance_no_awacs():
    """无预警机（has_awacs=False）交战距离估算全链路可用。"""
    params = {
        'rcs': 0.5, 'traj': 'sea', 'awacs_area': 8, 'awacs_type': 'aesa',
        'standoff': 150, 'ship_area': 12, 'ship_type': 'aesa', 'sam_range': 200,
        'vm': 2.6, 'vi': 3.8, 'interceptor_dia': 0.35,
        'seeker_type': 'active_aesa', 'has_awacs': False,
    }
    dist = run_saturation_json({'action': 'estimate_distance', 'params': params})
    assert dist['success'] is True
    assert dist['has_awacs'] is False
    assert dist['engage_dist'] == pytest.approx(min(dist['ship_search'], dist['sam_range']))
    assert dist['binding'] != '预警机总探测距离'


@pytest.mark.e2e
def test_e2e_saturation_http_api():
    """小程序 HTTP API 饱和打击路由。"""
    payload = {
        'action': 'simulate',
        'params': {
            'nm': 24, 'vm': 2.6, 'D': 120, 'ni': 16, 'vi': 3.8,
            'pk': 0.7, 'tlock': 6, 'minr': 3, 'fast': True,
        },
    }
    status, headers, body = handle_request(
        'POST', '/api/saturation/simulate', json.dumps(payload).encode(),
    )
    assert status == 200
    assert 'application/json' in headers['Content-Type']
    result = json.loads(body.decode())
    assert result['success'] is True
    assert result['n_rounds'] >= 1
    assert 'best' in result
