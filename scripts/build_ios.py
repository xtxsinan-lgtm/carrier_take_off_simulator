#!/usr/bin/env python3
"""构建 iOS App 静态数据：将 catalog 写入 ios/CarrierTakeOff/Resources/data.json。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IOS_RESOURCES = ROOT / 'ios' / 'CarrierTakeOff' / 'Resources'

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_ios_data() -> dict:
    """从 CSV 生成与小程序同源的目录数据。"""
    from scripts.frontend_catalog import build_catalog_payload
    from utils.database_csv import load_aircraft_csv, load_carriers_csv
    from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV

    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    carriers = load_carriers_csv(CARRIERS_CSV)
    return build_catalog_payload(aircraft, carriers)


def main() -> None:
    """写入 iOS Bundle 用 data.json。"""
    IOS_RESOURCES.mkdir(parents=True, exist_ok=True)
    data = build_ios_data()
    path = IOS_RESOURCES / 'data.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {path}')


if __name__ == '__main__':
    main()
