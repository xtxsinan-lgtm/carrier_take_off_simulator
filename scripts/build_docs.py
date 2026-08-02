#!/usr/bin/env python3
"""构建 GitHub Pages 静态资源：data.json + 打包 Python 仿真模块。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
PY_DEST = DOCS / 'py'

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    'utils/propeller_thrust.py',
    'utils/specs.py',
    'simulators/__init__.py',
    'simulators/short_take_off.py',
    'simulators/short_ski_jump_take_off.py',
    'simulators/ski_jump_take_off.py',
    'simulators/tiltrotor_short_take_off.py',
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
    'utils.propeller_thrust',
    'utils.specs',
    'simulators.short_take_off',
    'simulators.short_ski_jump_take_off',
    'simulators.ski_jump_take_off',
    'simulators.tiltrotor_short_take_off',
    'apps.web_simulator',
]


def main() -> None:
    from scripts.frontend_catalog import build_catalog_payload
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

    data = build_catalog_payload(aircraft, carriers)
    data['py_load_order'] = PY_LOAD_ORDER
    data['py_import_order'] = PY_IMPORT_ORDER
    data['py_sources'] = py_sources

    (DOCS / 'data.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Wrote {DOCS / "data.json"}')
    print(f'Copied {len(PY_LOAD_ORDER)} Python modules under {PY_DEST}/')


if __name__ == '__main__':
    main()
