#!/usr/bin/env python3
"""构建微信小程序静态数据：miniprogram/data/data.json（不含 Python 源码）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MINIPROGRAM_DATA = ROOT / 'miniprogram' / 'data'

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_miniprogram_data() -> dict:
    """从 CSV 生成小程序用 data.json 结构。"""
    from scripts.frontend_catalog import build_catalog_payload
    from utils.database_csv import load_aircraft_csv, load_carriers_csv
    from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV

    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    carriers = load_carriers_csv(CARRIERS_CSV)
    return build_catalog_payload(aircraft, carriers)


def main() -> None:
    MINIPROGRAM_DATA.mkdir(parents=True, exist_ok=True)
    data = build_miniprogram_data()
    out = MINIPROGRAM_DATA / 'data.json'
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
