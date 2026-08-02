"""Unit tests for database_csv.py."""
import pytest

from utils.database_csv import load_aircraft_csv, load_carriers_csv
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV


def test_load_aircraft_csv_count():
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    assert len(aircraft) >= 8
    assert 'F-35B' in aircraft
    assert 'AV-8B' in aircraft
    assert 'J-15' in aircraft


def test_load_carriers_csv_count():
    carriers = load_carriers_csv(CARRIERS_CSV)
    assert len(carriers) >= 9
    ids = {c.id for c in carriers}
    assert 'SHANDONG' in ids
    assert 'WASP' in ids


def test_aircraft_a2a_mass_via_specs():
    from utils.specs import A2A_MISSILE_COUNT, PILOT_LOAD_KG

    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    j15 = aircraft['J-15']
    assert j15.a2a_mass_kg == pytest.approx(
        j15.empty_kg + j15.internal_fuel_kg + A2A_MISSILE_COUNT * j15.missile_mass_kg + PILOT_LOAD_KG
    )
