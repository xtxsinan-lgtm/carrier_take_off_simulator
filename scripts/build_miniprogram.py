#!/usr/bin/env python3
"""构建微信小程序静态数据：miniprogram/data/data.json（不含 Python 源码）。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MINIPROGRAM_DATA = ROOT / 'miniprogram' / 'data'


def _carrier_dict(c) -> dict:
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


def _aircraft_dict(ac) -> dict:
    d = asdict(ac) if hasattr(ac, '__dataclass_fields__') else dict(ac)
    return {k: v for k, v in d.items() if k in (
        'id', 'name', 'type_label', 'mtow_kg', 'empty_kg', 'internal_fuel_kg',
        'bvr_missile', 'missile_mass_kg', 'sweep_le_deg', 'wingspan_m', 'wing_area_m2',
        'wing_height_m', 'cd0', 't_max_sl_n', 't_main_stovl_sl_n', 't_liftfan_sl_n',
        't_rollposts_sl_n', 'exhaust_mdot_kg_s', 'exhaust_d0_m', 'exhaust_height_m', 'notes',
    )}


def build_miniprogram_data() -> dict:
    """从 CSV 生成小程序用 data.json 结构。"""
    import sys
    sys.path.insert(0, str(ROOT))
    from utils.database_csv import load_aircraft_csv, load_carriers_csv
    from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV

    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    carriers = load_carriers_csv(CARRIERS_CSV)
    return {
        'version': 8,
        'pilot_load_kg': 100.0,
        'a2a_missile_count': 4,
        'pitch_max_deg': 20,
        'modes': {
            'ski_jump': '滑跃起飞',
            'short_takeoff': '短距起飞',
            'short_ski_jump': '短距滑跃起飞',
        },
        'aircraft': [_aircraft_dict(ac) for ac in aircraft.values()],
        'carriers': [_carrier_dict(c) for c in carriers],
    }


def main() -> None:
    MINIPROGRAM_DATA.mkdir(parents=True, exist_ok=True)
    data = build_miniprogram_data()
    out = MINIPROGRAM_DATA / 'data.json'
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
