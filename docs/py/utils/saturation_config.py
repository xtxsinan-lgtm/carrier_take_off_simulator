"""饱和打击 / 反导拦截仿真默认参数 — 从 data/saturation_config.json 加载。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.paths import SATURATION_CONFIG_JSON

_INJECTED: dict[str, Any] | None = None


def inject_saturation_config(cfg: dict[str, Any]) -> None:
    """注入配置（Pyodide / 测试用）；优先于磁盘文件。"""
    global _INJECTED
    _INJECTED = dict(cfg)
    load_saturation_config.cache_clear()


@lru_cache(maxsize=1)
def load_saturation_config(path: str | Path | None = None) -> dict[str, Any]:
    """加载饱和打击配置 JSON；路径缺省为 data/saturation_config.json。"""
    if _INJECTED is not None:
        return dict(_INJECTED)
    p = Path(path) if path is not None else SATURATION_CONFIG_JSON
    return json.loads(p.read_text(encoding='utf-8'))


def physics_config() -> dict[str, Any]:
    return dict(load_saturation_config()['physics'])


def ui_config() -> dict[str, Any]:
    return dict(load_saturation_config()['ui'])


def simulation_config() -> dict[str, Any]:
    return dict(load_saturation_config()['simulation'])


def estimate_defaults() -> dict[str, Any]:
    return dict(load_saturation_config()['estimate_defaults'])


def traj_types() -> dict[str, str]:
    """弹道类型 id → 界面显示名。"""
    return dict(load_saturation_config().get('traj_types', {}))


def valid_traj_ids() -> frozenset[str]:
    """CSV / API 允许的 asm traj 取值。"""
    types = traj_types()
    if types:
        return frozenset(types)
    return frozenset({'high', 'sea', 'glide', 'ballistic'})


def build_saturation_config_payload() -> dict[str, Any]:
    """构建前端/小程序/iOS 共用的饱和打击配置片段。"""
    cfg = load_saturation_config()
    return {
        'version': cfg.get('version', 1),
        'physics': dict(cfg['physics']),
        'traj_types': dict(cfg.get('traj_types', {})),
        'ui': dict(cfg['ui']),
        'simulation': dict(cfg['simulation']),
        'estimate_defaults': dict(cfg['estimate_defaults']),
    }
