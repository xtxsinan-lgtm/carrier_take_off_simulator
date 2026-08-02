"""饱和打击仿真 Web/JSON API（供 Pyodide / 小程序 / iOS 调用）。"""
from __future__ import annotations

import json
from typing import Any

from simulators.saturation_strike import (
    run_estimate_distance_from_params,
    run_estimate_pk_from_params,
    run_saturation_strike,
)
from utils.saturation_presets import build_saturation_presets_payload


def _opt_float(v: Any, default: float) -> float:
    """解析可选浮点，空值用默认。"""
    if v is None or v == '':
        return default
    return float(v)


def _opt_int(v: Any, default: int) -> int:
    """解析可选整数，空值用默认。"""
    if v is None or v == '':
        return default
    return int(round(float(v)))


def run_saturation(
    action: str = 'simulate',
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """统一入口：simulate / estimate_distance / estimate_pk / presets。"""
    params = params or {}
    if action == 'presets':
        return {'success': True, 'presets': build_saturation_presets_payload()}
    if action == 'estimate_distance':
        try:
            result = run_estimate_distance_from_params(params)
            return {'success': True, **result}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}
    if action == 'estimate_pk':
        try:
            result = run_estimate_pk_from_params(params)
            return {'success': True, **result}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}
    if action != 'simulate':
        return {'success': False, 'error': f'未知 action: {action}'}

    try:
        fast = bool(params.get('fast', False))
        search_trials = _opt_int(params.get('search_trials'), 200 if fast else 900)
        final_trials = _opt_int(params.get('final_trials'), 800 if fast else 6000)
        result = run_saturation_strike(
            nm=_opt_int(params.get('nm'), 24),
            vm_ma=_opt_float(params.get('vm'), 2.6),
            discovery_km=_opt_float(params.get('D', params.get('discovery_km')), 120.0),
            ni=_opt_int(params.get('ni'), 16),
            vi_ma=_opt_float(params.get('vi'), 3.8),
            pk=_opt_float(params.get('pk'), 0.7),
            t_lock_s=_opt_float(params.get('tlock', params.get('t_lock_s')), 6.0),
            min_range_km=_opt_float(params.get('minr', params.get('min_range_km')), 3.0),
            search_trials=search_trials,
            final_trials=final_trials,
        )
        return result
    except Exception as exc:
        return {'success': False, 'error': str(exc)}


def run_saturation_json(payload: dict[str, Any] | str) -> dict[str, Any]:
    """解析 JSON/dict 载荷并运行饱和打击 API。"""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            return {'success': False, 'error': f'JSON 解析失败: {exc}'}
    if not isinstance(payload, dict):
        return {'success': False, 'error': '载荷必须为对象'}
    action = str(payload.get('action', 'simulate'))
    params = payload.get('params')
    if params is None:
        # 允许扁平载荷（字段直接在根上）
        params = {k: v for k, v in payload.items() if k != 'action'}
    return run_saturation(action=action, params=params)
