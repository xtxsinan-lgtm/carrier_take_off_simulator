"""微信小程序仿真 HTTP API（供 miniprogram 通过 wx.request 调用）。"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# 支持从项目根目录直接运行：python3 apps/miniprogram_api.py
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.web_simulator import run_simulation_json


def build_data_payload() -> dict[str, Any]:
    """返回航母/战斗机数据库 JSON（与 build_miniprogram 结构一致）。"""
    from scripts.build_miniprogram import build_miniprogram_data
    return build_miniprogram_data()


def handle_request(method: str, path: str, body: bytes | None) -> tuple[int, dict[str, str], bytes]:
    """
    处理单次 HTTP 请求，返回 (status_code, headers, body_bytes)。
    便于单元测试，无需启动真实服务器。
    """
    parsed = urlparse(path)
    route = parsed.path.rstrip('/') or '/'
    cors = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    if method == 'OPTIONS':
        return 204, cors, b''

    if method == 'GET' and route == '/api/data':
        payload = build_data_payload()
        body_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = {**cors, 'Content-Type': 'application/json; charset=utf-8'}
        return 200, headers, body_bytes

    if method == 'POST' and route == '/api/simulate':
        if not body:
            err = {'success': False, 'error': '请求体为空'}
            return 400, {**cors, 'Content-Type': 'application/json'}, json.dumps(err).encode()
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as exc:
            err = {'success': False, 'error': f'JSON 解析失败: {exc}'}
            return 400, {**cors, 'Content-Type': 'application/json'}, json.dumps(err).encode()
        result = run_simulation_json(payload)
        body_bytes = json.dumps(result, ensure_ascii=False).encode('utf-8')
        headers = {**cors, 'Content-Type': 'application/json; charset=utf-8'}
        return 200, headers, body_bytes

    err = {'error': 'Not Found'}
    return 404, {**cors, 'Content-Type': 'application/json'}, json.dumps(err).encode()


class _ApiHandler(BaseHTTPRequestHandler):
    """stdlib HTTP 处理器，委托 handle_request。"""

    def log_message(self, format: str, *args: Any) -> None:
        print(f'[miniprogram_api] {self.address_string()} - {format % args}')

    def _respond(self, status: int, headers: dict[str, str], body: bytes) -> None:
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        status, headers, body = handle_request('OPTIONS', self.path, None)
        self._respond(status, headers, body)

    def do_GET(self) -> None:
        status, headers, body = handle_request('GET', self.path, None)
        self._respond(status, headers, body)

    def do_POST(self) -> None:
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length) if length else b''
        status, headers, body = handle_request('POST', self.path, raw)
        self._respond(status, headers, body)


def serve(host: str = '127.0.0.1', port: int = 8765) -> None:
    """启动仿真 API 服务。"""
    try:
        server = ThreadingHTTPServer((host, port), _ApiHandler)
    except OSError as exc:
        if exc.errno == 48:
            print(f'端口 {port} 已被占用，仿真 API 可能已在运行。')
            print(f'  可直接访问: http://{host}:{port}/api/data')
            print(f'  若要重启: kill $(lsof -t -i :{port}) 后再运行本脚本')
            raise SystemExit(1) from exc
        raise
    print(f'小程序仿真 API 运行于 http://{host}:{port}')
    print('  GET  /api/data     — 航母/战斗机数据')
    print('  POST /api/simulate — 运行仿真')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
        server.server_close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='航母起飞仿真 — 小程序 HTTP API')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址（默认 127.0.0.1）')
    parser.add_argument('--port', type=int, default=8765, help='监听端口（默认 8765）')
    args = parser.parse_args()
    serve(args.host, args.port)
