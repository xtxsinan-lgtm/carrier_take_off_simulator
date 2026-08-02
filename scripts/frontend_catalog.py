"""前端机库/舰库 JSON 的共享序列化（Web 与小程序共用）。"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from utils.specs import A2A_MISSILE_COUNT, PILOT_LOAD_KG
from utils.takeoff_physics import PITCH_MAX_DEG

MODES = {
    'ski_jump': '滑跃起飞',
    'short_takeoff': '短距起飞',
    'short_ski_jump': '短距滑跃起飞',
    'tiltrotor_short_takeoff': '倾转短距起飞',
}

STOVL_STRATEGIES = {
    'A': '策略 A — 延迟偏转喷口',
    'B': '策略 B — 全程固定喷口',
    'C': '策略 C — 尾流约束最优偏转',
}

TILTROTOR_STRATEGIES = {
    'A': '策略 A — 延迟倾转短舱',
    'B': '策略 B — 全程固定短舱角',
}

# data.json 结构版本；字段变更时递增
DATA_VERSION = 11

_AIRCRAFT_KEYS = (
    'id', 'name', 'type_label', 'mtow_kg', 'empty_kg', 'internal_fuel_kg', 'max_payload_kg',
    'bvr_missile', 'missile_mass_kg', 'sweep_le_deg', 'wingspan_m', 'wing_area_m2',
    'wing_height_m', 'cd0', 't_max_sl_n', 't_main_stovl_sl_n', 't_liftfan_sl_n',
    't_rollposts_sl_n', 'exhaust_mdot_kg_s', 'exhaust_d0_m', 'exhaust_height_m',
    'shaft_power_sl_w', 'prop_diameter_m', 'nacelle_blockage_frac', 'notes',
)


def carrier_to_dict(c: Any) -> dict:
    """航母规格 → 前端 JSON 字段。"""
    return {
        'id': c.id,
        'name': c.name,
        'nation': c.nation,
        'max_speed_kt': c.max_speed_kt,
        'ski_jump': c.ski_jump,
        'total_deck_length_m': c.total_deck_length_m,
        'ski_jump_angle_deg': c.ski_jump_angle_deg,
        'ski_jump_height_m': c.ski_jump_height_m,
        'f35b_capable': c.f35b_capable,
        'deck_length_source': c.deck_length_source,
        'notes': c.notes,
    }


def aircraft_to_dict(ac: Any) -> dict:
    """战斗机规格 → 前端 JSON 字段。"""
    d = asdict(ac) if hasattr(ac, '__dataclass_fields__') else dict(ac)
    return {k: v for k, v in d.items() if k in _AIRCRAFT_KEYS}


def build_catalog_payload(aircraft: dict, carriers: list) -> dict:
    """构建不含 py_sources 的共享目录数据（小程序 / API / Web 公共部分）。"""
    return {
        'version': DATA_VERSION,
        'pilot_load_kg': float(PILOT_LOAD_KG),
        'a2a_missile_count': int(A2A_MISSILE_COUNT),
        'pitch_max_deg': float(PITCH_MAX_DEG),
        'modes': dict(MODES),
        'stovl_strategies': dict(STOVL_STRATEGIES),
        'tiltrotor_strategies': dict(TILTROTOR_STRATEGIES),
        'aircraft': [aircraft_to_dict(ac) for ac in aircraft.values()],
        'carriers': [carrier_to_dict(c) for c in carriers],
    }
