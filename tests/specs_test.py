"""Unit tests for specs.py."""
from utils.database_csv import load_aircraft_csv
from utils.paths import AIRCRAFT_CSV
from utils.specs import (
    A2A_MISSILE_COUNT,
    PILOT_LOAD_KG,
    is_vtol_aircraft,
    simulation_uses_plume_model,
)


def test_a2a_mass_and_payload():
    ac = load_aircraft_csv(AIRCRAFT_CSV)['J-15']
    assert ac.a2a_mass_kg == ac.empty_kg + ac.internal_fuel_kg + A2A_MISSILE_COUNT * ac.missile_mass_kg + PILOT_LOAD_KG
    assert ac.max_payload_kg == ac.mtow_kg - ac.empty_kg - ac.internal_fuel_kg - PILOT_LOAD_KG


def test_carrier_ski_jump_geom():
    from utils.database_csv import load_carriers_csv
    from utils.paths import CARRIERS_CSV

    carrier = next(c for c in load_carriers_csv(CARRIERS_CSV) if c.id == 'SHANDONG')
    geom = carrier.ski_jump_geom()
    assert geom is not None
    assert carrier.ski_jump_horizontal_m() == geom.horizontal_m


def test_is_vtol_aircraft():
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    assert aircraft['F-35B'].is_vtol is True
    assert is_vtol_aircraft(aircraft['J-15']) is False


def test_simulation_uses_plume_model_only_vtol_short_modes():
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    f35b = aircraft['F-35B']
    j15 = aircraft['J-15']
    assert simulation_uses_plume_model('short_takeoff', f35b) is True
    assert simulation_uses_plume_model('short_ski_jump', f35b) is True
    assert simulation_uses_plume_model('ski_jump', j15) is False
    assert simulation_uses_plume_model('short_takeoff', j15) is False
