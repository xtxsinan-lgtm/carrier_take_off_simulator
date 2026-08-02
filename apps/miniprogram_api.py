"""兼容旧入口：请改用 python3 apps/simulator_api.py。

本模块仅转发到 apps.simulator_api，便于旧文档/脚本继续工作。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.simulator_api import (  # noqa: F401
    build_data_payload,
    handle_request,
    serve,
)

if __name__ == '__main__':
    import argparse

    print(
        '提示: apps/miniprogram_api.py 已更名为 apps/simulator_api.py（小程序与 iOS 共用）。',
        file=sys.stderr,
    )
    parser = argparse.ArgumentParser(description='[已弃用入口] 请改用 apps/simulator_api.py')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    serve(args.host, args.port)
