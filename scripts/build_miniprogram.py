#!/usr/bin/env python3
"""构建微信小程序静态数据：data.json + data.js（小程序 require 用）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MINIPROGRAM_DATA = ROOT / 'miniprogram' / 'data'

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_miniprogram_data() -> dict:
    """从 CSV 生成小程序用数据目录结构。"""
    from scripts.frontend_catalog import build_catalog_payload
    from utils.database_csv import load_aircraft_csv, load_carriers_csv
    from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV

    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    carriers = load_carriers_csv(CARRIERS_CSV)
    return build_catalog_payload(aircraft, carriers)


def render_data_js(data: dict) -> str:
    """生成可供小程序 require 的 CommonJS 模块（勿手改产物）。"""
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return (
        '/**\n'
        ' * 航母/战斗机目录数据 — 由 scripts/build_miniprogram.py 自动生成。\n'
        ' * 请勿手改；修改 CSV 后运行 python3 scripts/build_all.py。\n'
        ' */\n'
        f'module.exports = {payload};\n'
    )


def main() -> None:
    MINIPROGRAM_DATA.mkdir(parents=True, exist_ok=True)
    data = build_miniprogram_data()

    json_path = MINIPROGRAM_DATA / 'data.json'
    js_path = MINIPROGRAM_DATA / 'data.js'
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    js_path.write_text(render_data_js(data), encoding='utf-8')
    print(f'Wrote {json_path}')
    print(f'Wrote {js_path}')


if __name__ == '__main__':
    main()
