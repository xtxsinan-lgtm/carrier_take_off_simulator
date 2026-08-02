#!/usr/bin/env python3
"""一键构建全部前端产物：physics.js + Web data.json + 小程序 data.json。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    """按依赖顺序构建：物理 JS → GitHub Pages → 小程序数据。"""
    from scripts.generate_frontend_physics import write_physics_files
    from scripts import build_docs, build_miniprogram

    print('=== 1/3 生成前端 physics.js（常量来自 Python）===')
    write_physics_files()

    print('=== 2/3 构建 Web（docs/data.json + docs/py）===')
    build_docs.main()

    print('=== 3/3 构建小程序（miniprogram/data/data.json）===')
    build_miniprogram.main()

    print('全部构建完成。')


if __name__ == '__main__':
    main()
