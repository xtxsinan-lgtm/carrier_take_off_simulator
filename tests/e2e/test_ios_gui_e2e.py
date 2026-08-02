"""iOS 通道端到端：build 产物与小程序 catalog 一致。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_ios import build_ios_data, main as build_ios_main
from scripts.generate_frontend_physics import render_swift, write_physics_files
from utils.paths import ROOT


@pytest.mark.e2e
def test_ios_build_pipeline_e2e(tmp_path, monkeypatch):
    """运行 build_ios + physics 写入后，产物可读且与 catalog 一致。"""
    # 写入真实路径（与生产构建相同）
    write_physics_files()
    build_ios_main()

    data_path = ROOT / 'ios' / 'CarrierTakeOff' / 'Resources' / 'data.json'
    physics_path = ROOT / 'ios' / 'CarrierTakeOff' / 'Physics.swift'
    assert data_path.is_file()
    assert physics_path.read_text(encoding='utf-8') == render_swift()

    on_disk = json.loads(data_path.read_text(encoding='utf-8'))
    assert on_disk == build_ios_data()
    assert 'ski_jump' in on_disk['modes']
    assert any(c.get('ski_jump') for c in on_disk['carriers'])
