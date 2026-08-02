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
    assert 'py_sources' not in payload


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
