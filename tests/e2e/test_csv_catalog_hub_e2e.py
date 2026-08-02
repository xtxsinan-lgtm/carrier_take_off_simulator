"""CSV 型号自动进入三端 catalog 的端到端测试。"""
from __future__ import annotations

import json

import pytest

from apps.miniprogram_api import handle_request
from scripts.frontend_catalog import SIMULATORS, build_catalog_payload
from utils.database_csv import (
    load_aircraft_csv,
    load_carriers_csv,
    load_saturation_equipment_csv,
)
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV, ROOT, SATURATION_EQUIPMENT_CSV


@pytest.mark.e2e
def test_e2e_catalog_auto_detects_csv_models():
    """起飞与饱和 CSV 中的型号须全部出现在 catalog / API data。"""
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    carriers = load_carriers_csv(CARRIERS_CSV)
    sat = load_saturation_equipment_csv(SATURATION_EQUIPMENT_CSV)
    payload = build_catalog_payload(aircraft, carriers)

    assert {a['id'] for a in payload['aircraft']} == set(aircraft)
    assert {c['id'] for c in payload['carriers']} == {c.id for c in carriers}
    for cat in ('asm', 'aew', 'ship', 'sam'):
        assert [x['id'] for x in payload['saturation_presets'][cat]] == [
            x['id'] for x in sat[cat]
        ]
    assert payload['simulators'] == SIMULATORS

    status, _, body = handle_request('GET', '/api/data', None)
    assert status == 200
    api = json.loads(body.decode())
    assert api['simulators'] == SIMULATORS
    assert len(api['saturation_presets']['sam']) == len(sat['sam'])


@pytest.mark.e2e
def test_e2e_docs_hub_and_takeoff_pages():
    """启动页与起飞页文件齐全，启动页从 simulators 渲染。"""
    hub = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
    hub_js = (ROOT / 'docs' / 'js' / 'hub.js').read_text(encoding='utf-8')
    assert 'hub.js' in hub
    assert 'data.simulators' in hub_js or 'simulators' in hub_js
    assert (ROOT / 'docs' / 'takeoff.html').is_file()
    assert (ROOT / 'docs' / 'saturation-strike.html').is_file()
