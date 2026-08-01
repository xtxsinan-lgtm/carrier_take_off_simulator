#!/usr/bin/env python3
"""构建 GitHub Pages 静态资源：data.json + 复制 Python 仿真模块到 docs/py/。"""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
PY_DEST = DOCS / 'py'

PY_FILES = (
    'takeoff_physics.py',
    'ski_jump_geometry.py',
    'sim_config.py',
    'search_utils.py',
    'deck_config.py',
    'exhaust_plume.py',
    'short_take_off.py',
    'short_ski_jump_take_off.py',
    'ski_jump_take_off.py',
    'web_simulator.py',
)

LOAD_ORDER = list(PY_FILES)


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
        't_rollposts_sl_n', 'notes',
    )}


def main() -> None:
    import sys
    sys.path.insert(0, str(ROOT))
    from database_csv import load_aircraft_csv, load_carriers_csv

    DOCS.mkdir(exist_ok=True)
    PY_DEST.mkdir(exist_ok=True)

    aircraft = load_aircraft_csv(ROOT / 'aircraft_database.csv')
    carriers = load_carriers_csv(ROOT / 'carriers_database.csv')

    py_sources = {
        name: (ROOT / name).read_text(encoding='utf-8')
        for name in PY_FILES
    }

    data = {
        'version': 4,
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
        'py_load_order': LOAD_ORDER,
        'py_sources': py_sources,
    }
    (DOCS / 'data.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    for name in PY_FILES:
        src = ROOT / name
        if not src.is_file():
            raise FileNotFoundError(src)
        shutil.copy2(src, PY_DEST / name)

    print(f'Wrote {DOCS / "data.json"}')
    print(f'Copied {len(PY_FILES)} Python modules to {PY_DEST}/')


if __name__ == '__main__':
    main()
