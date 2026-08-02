"""舰载机 / 航母 / 饱和打击装备 CSV 导入导出单元测试。"""
import pytest

from utils.database_csv import (
    list_model_ids_from_saturation_csv,
    load_aircraft_csv,
    load_carriers_csv,
    load_saturation_equipment_csv,
)
from utils.paths import AIRCRAFT_CSV, CARRIERS_CSV, SATURATION_EQUIPMENT_CSV


def test_load_aircraft_csv_count():
    """起飞仿真：CSV 中的舰载机型号应全部可加载。"""
    aircraft = load_aircraft_csv(AIRCRAFT_CSV)
    assert len(aircraft) >= 11
    assert 'F-35B' in aircraft
    assert 'AV-8B' in aircraft
    assert 'J-15' in aircraft
    assert 'F-14' in aircraft
    assert 'FA-18C' in aircraft
    assert 'MV-22' in aircraft


def test_load_carriers_csv_count():
    """起飞仿真：CSV 中的航母型号应全部可加载。"""
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
    f14 = aircraft['F-14']
    assert f14.wingspan_m == pytest.approx(19.54)
    assert f14.t_max_sl_n == pytest.approx(250900)
    hornet = aircraft['FA-18C']
    assert hornet.wing_area_m2 == pytest.approx(38.0)
    assert hornet.t_max_sl_n == pytest.approx(156600)


def test_load_saturation_equipment_csv_groups():
    """饱和打击：四类装备均可从 CSV 识别。"""
    data = load_saturation_equipment_csv(SATURATION_EQUIPMENT_CSV)
    assert set(data) == {'asm', 'aew', 'ship', 'sam'}
    assert len(data['asm']) >= 7
    assert len(data['sam']) >= 8
    assert data['asm'][0]['id'] == 'exocet'
    assert 'vm' in data['asm'][0]
    assert 'area' in data['aew'][0]
    assert 'guidance' in data['sam'][0]


def test_list_model_ids_from_saturation_csv():
    """列出 CSV 型号 id，供前端自动同步断言。"""
    ids = list_model_ids_from_saturation_csv(SATURATION_EQUIPMENT_CSV)
    assert 'yj12' in ids['asm']
    assert 'e2d' in ids['aew']
    assert 'type055' in ids['ship']
    assert 'hhq9' in ids['sam']
