#!/usr/bin/env python3
"""构建 GitHub Pages 静态资源：data.json + 打包 Python 仿真模块。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
PY_DEST = DOCS / 'py'

# Pyodide 按依赖顺序加载（路径相对项目根）
PY_LOAD_ORDER = [
    'utils/__init__.py',
    'utils/takeoff_physics.py',
    'utils/ski_jump_geometry.py',
    'utils/trajectory.py',
    'utils/sim_config.py',
    'utils/search_utils.py',
    'utils/deck_config.py',
    'utils/exhaust_plume.py',
    'utils/specs.py',
    'simulators/__init__.py',
    'simulators/short_take_off.py',
    'simulators/short_ski_jump_take_off.py',
    'simulators/ski_jump_take_off.py',
    'apps/__init__.py',
    'apps/web_simulator.py',
]

PY_IMPORT_ORDER = [
    'utils.takeoff_physics',
    'utils.ski_jump_geometry',
    'utils.trajectory',
    'utils.sim_config',
    'utils.search_utils',
    'utils.deck_config',
    'utils.exhaust_plume',
    'utils.specs',
    'simulators.short_take_off',
    'simulators.short_ski_jump_take_off',
    'simulators.ski_jump_take_off',
    'apps.web_simulator',
]


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


def main() -> None:
    import sys
    sys.path.insert(0, str(ROOT))
    from utils.database_csv import load_aircraft_csv, load_carriers_csv
    from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV

    DOCS.mkdir(exist_ok=True)
    PY_DEST.mkdir(parents=True, exist_ok=True)

    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    carriers = load_carriers_csv(CARRIERS_CSV)

    py_sources = {}
    for rel in PY_LOAD_ORDER:
        src = ROOT / rel
        if not src.is_file():
            raise FileNotFoundError(src)
        py_sources[rel] = src.read_text(encoding='utf-8')
        dest = PY_DEST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(py_sources[rel], encoding='utf-8')

    data = {
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
        'py_load_order': PY_LOAD_ORDER,
        'py_import_order': PY_IMPORT_ORDER,
        'py_sources': py_sources,
    }
    (DOCS / 'data.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Wrote {DOCS / "data.json"}')
    print(f'Copied {len(PY_LOAD_ORDER)} Python modules under {PY_DEST}/')


if __name__ == '__main__':
    main()
