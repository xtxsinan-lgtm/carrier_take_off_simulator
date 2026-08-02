"""iOS 本地引擎通道端到端：build 产物含 py_sources 与桥接页。"""
from __future__ import annotations

import json

import pytest

from scripts.build_docs import PY_LOAD_ORDER
from scripts.build_ios import build_ios_data, main as build_ios_main
from scripts.generate_frontend_physics import render_swift, write_physics_files
from utils.paths import ROOT


@pytest.mark.e2e
def test_ios_local_engine_build_pipeline_e2e():
    """运行 build_ios 后，本地引擎所需资源齐全且与 Web py 列表一致。"""
    write_physics_files()
    build_ios_main()

    data_path = ROOT / 'ios' / 'CarrierTakeOff' / 'Resources' / 'data.json'
    physics_path = ROOT / 'ios' / 'CarrierTakeOff' / 'Physics.swift'
    engine_js = ROOT / 'ios' / 'CarrierTakeOff' / 'Resources' / 'engine.js'
    assert data_path.is_file()
    assert engine_js.is_file()
    assert physics_path.read_text(encoding='utf-8') == render_swift()

    on_disk = json.loads(data_path.read_text(encoding='utf-8'))
    expected = build_ios_data()
    assert on_disk['modes'] == expected['modes']
    assert on_disk['py_load_order'] == list(PY_LOAD_ORDER)
    assert set(on_disk['py_sources']) == set(expected['py_sources'])
    assert 'run_simulation_json' in engine_js.read_text(encoding='utf-8')
