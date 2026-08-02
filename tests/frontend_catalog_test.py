"""frontend_catalog / generate_frontend_physics / build_all 单元测试。"""
from __future__ import annotations

from scripts.frontend_catalog import MODES, aircraft_to_dict, build_catalog_payload, carrier_to_dict
from scripts.generate_frontend_physics import render_cjs, render_esm, _load_constants
from utils.database_csv import load_aircraft_csv, load_carriers_csv
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV


def test_carrier_to_dict_has_ski_jump_fields():
    carriers = load_carriers_csv(CARRIERS_CSV)
    d = carrier_to_dict(carriers[0])
    assert 'ski_jump' in d and 'total_deck_length_m' in d and 'id' in d


def test_aircraft_to_dict_strips_computed_props():
    ac = next(iter(load_aircraft_csv(AIRCRAFT_CSV).values()))
    d = aircraft_to_dict(ac)
    assert 'id' in d and 'name' in d
    assert 'a2a_mass_kg' not in d


def test_build_catalog_payload_modes():
    payload = build_catalog_payload(
        load_aircraft_csv(AIRCRAFT_CSV),
        load_carriers_csv(CARRIERS_CSV),
    )
    assert payload['modes'] == MODES
    assert 'tiltrotor_short_takeoff' in payload['modes']
    assert 'tiltrotor_strategies' in payload
    assert set(payload['tiltrotor_strategies']) == {'A', 'B'}
    assert 'py_sources' not in payload
    assert any(a['id'] == 'MV-22' for a in payload['aircraft'])
    # 第二功能：饱和打击预设
    assert 'saturation_presets' in payload
    assert set(payload['saturation_presets']) == {'asm', 'aew', 'ship', 'sam'}
    assert len(payload['saturation_presets']['asm']) >= 1


def test_docs_saturation_page_exists_and_links():
    """饱和打击 HTML 页存在，并与起飞页互链。"""
    from utils.paths import ROOT

    sat = ROOT / 'docs' / 'saturation-strike.html'
    index = ROOT / 'docs' / 'index.html'
    assert sat.is_file()
    assert (ROOT / 'docs' / 'js' / 'saturation.js').is_file()
    assert (ROOT / 'docs' / 'css' / 'saturation.css').is_file()
    sat_html = sat.read_text(encoding='utf-8')
    index_html = index.read_text(encoding='utf-8')
    assert 'saturation.js' in sat_html
    assert 'index.html' in sat_html
    assert 'saturation-strike.html' in index_html
    assert 'run_saturation_json' in (ROOT / 'docs' / 'js' / 'saturation.js').read_text(encoding='utf-8')


def test_web_simulator_modes_match_frontend_catalog():
    """Web API 与前端 catalog 的模式/策略表必须一致，防止某一端漏加新模式。"""
    from apps import web_simulator as ws
    from scripts.frontend_catalog import STOVL_STRATEGIES, TILTROTOR_STRATEGIES

    assert ws.MODES == MODES
    assert ws.STOVL_STRATEGIES == STOVL_STRATEGIES
    assert ws.TILTROTOR_STRATEGIES == TILTROTOR_STRATEGIES


def test_docs_html_renders_modes_from_catalog_not_hardcoded():
    """HTML 版模式按钮须由 data.modes 动态生成，禁止在 index.html 硬编码模式 id。"""
    import re
    from utils.paths import ROOT

    html = (ROOT / 'docs' / 'index.html').read_text(encoding='utf-8')
    app_js = (ROOT / 'docs' / 'js' / 'app.js').read_text(encoding='utf-8')

    assert 'id="modeGroup"' in html
    assert 'data-mode="ski_jump"' not in html
    assert 'data-mode="tiltrotor_short_takeoff"' not in html
    assert 'function populateModeButtons' in app_js
    assert 'data.modes' in app_js

    # index.html 的 app.js?v= 须与 APP_VERSION 一致，避免 Pages/浏览器继续用旧脚本
    ver_js = re.search(r'const APP_VERSION\s*=\s*(\d+)', app_js)
    ver_html = re.search(r'app\.js\?v=(\d+)', html)
    assert ver_js and ver_html
    assert ver_js.group(1) == ver_html.group(1), (
        f'缓存版本不一致: app.js APP_VERSION={ver_js.group(1)} '
        f'vs index.html ?v={ver_html.group(1)}'
    )


def test_render_esm_and_cjs_contain_injected_constants():
    c = _load_constants()
    esm = render_esm(c)
    cjs = render_cjs(c)
    assert f"SKI_JUMP_REF_RADIUS_M = {c['SKI_JUMP_REF_RADIUS_M']}" in esm
    assert 'export {' in esm
    assert 'module.exports' in cjs
    assert '请勿手改' in esm and '请勿手改' in cjs


def test_render_includes_default_deck_wind_helper():
    from scripts.generate_frontend_physics import render_cjs

    text = render_cjs()
    assert 'function defaultDeckWindKt' in text
    assert 'max_speed_kt' in text


def test_load_constants_positive():
    c = _load_constants()
    assert c['SKI_JUMP_REF_RADIUS_M'] > 0
    assert c['A2A_MISSILE_COUNT'] >= 1
