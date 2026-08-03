"""舰载机 / 航母 / 饱和打击导弹与雷达 CSV 导入导出单元测试。"""
import pytest

from utils.database_csv import (
    list_model_ids_from_saturation_csv,
    load_aircraft_csv,
    load_carriers_csv,
    load_saturation_missile_csv,
    load_saturation_presets_csv,
    load_saturation_radar_csv,
)
from utils.paths import (
    AIRCRAFT_CSV,
    CARRIERS_CSV,
    SATURATION_MISSILE_CSV,
    SATURATION_RADAR_CSV,
)


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


def test_load_saturation_missile_csv_groups():
    """饱和打击：导弹库含反舰弹与防空弹。"""
    data = load_saturation_missile_csv(SATURATION_MISSILE_CSV)
    assert set(data) == {'asm', 'sam'}
    assert len(data['asm']) >= 7
    assert len(data['sam']) >= 8
    assert data['asm'][0]['id'] == 'exocet'
    assert 'vm' in data['asm'][0]
    assert 'guidance' in data['sam'][0]


def test_load_saturation_radar_csv_groups():
    """饱和打击：雷达库含预警机与舰载雷达。"""
    data = load_saturation_radar_csv(SATURATION_RADAR_CSV)
    assert set(data) == {'aew', 'ship'}
    assert len(data['aew']) >= 4
    assert len(data['ship']) >= 5
    assert 'area' in data['aew'][0]
    assert 'standoff' in data['aew'][0]
    assert 'area' in data['ship'][0]
    assert 'standoff' not in data['ship'][0]


def test_load_saturation_presets_csv_merges():
    """合并双库后应得到四类预设。"""
    data = load_saturation_presets_csv()
    assert set(data) == {'asm', 'aew', 'ship', 'sam'}
    assert data['asm'][0]['id'] == 'exocet'
    assert data['aew'][0]['id'] == 'e2d'


def test_list_model_ids_from_saturation_csv():
    """列出双库型号 id，供前端自动同步断言。"""
    ids = list_model_ids_from_saturation_csv()
    assert 'yj12' in ids['asm']
    assert 'e2d' in ids['aew']
    assert 'type055' in ids['ship']
    assert 'hhq9' in ids['sam']
