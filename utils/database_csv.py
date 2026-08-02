"""舰载机 / 航母参数库 CSV 导入导出（UTF-8 BOM，便于 Excel 打开中文）。"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from utils.specs import AircraftSpec, CarrierSpec

AIRCRAFT_CSV_COLUMNS = (
    'id', 'name', 'type_label', 'mtow_kg', 'empty_kg', 'internal_fuel_kg',
    'bvr_missile', 'missile_mass_kg', 'sweep_le_deg', 'wingspan_m', 'wing_area_m2',
    'wing_height_m', 'cd0', 't_max_sl_n', 't_main_stovl_sl_n', 't_liftfan_sl_n',
    't_rollposts_sl_n', 'exhaust_mdot_kg_s', 'exhaust_d0_m', 'exhaust_height_m', 'notes',
)

CARRIERS_CSV_COLUMNS = (
    'id', 'name', 'nation', 'max_speed_kt', 'ski_jump', 'total_deck_length_m',
    'ski_jump_angle_deg', 'ski_jump_height_m', 'f35b_capable', 'deck_length_source', 'notes',
)


def _cell_str(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return '1' if value else '0'
    return str(value)


def _parse_bool(raw: str) -> bool:
    text = raw.strip().lower()
    if text in ('1', 'true', 'yes', 'y', '是'):
        return True
    if text in ('0', 'false', 'no', 'n', '否', ''):
        return False
    raise ValueError(f'无法解析布尔值: {raw!r}')


def _parse_optional_float(raw: str) -> float | None:
    text = raw.strip()
    if not text:
        return None
    return float(text)


def _parse_float(raw: str, field: str) -> float:
    text = raw.strip()
    if not text:
        raise ValueError(f'缺少必填数值字段 {field}')
    return float(text)


def export_aircraft_csv(path: str | Path, aircraft: dict[str, 'AircraftSpec']) -> None:
    path = Path(path)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=AIRCRAFT_CSV_COLUMNS)
        writer.writeheader()
        for ac in aircraft.values():
            writer.writerow({col: _cell_str(getattr(ac, col)) for col in AIRCRAFT_CSV_COLUMNS})


def export_carriers_csv(path: str | Path, carriers: list['CarrierSpec']) -> None:
    path = Path(path)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CARRIERS_CSV_COLUMNS)
        writer.writeheader()
        for c in carriers:
            writer.writerow({col: _cell_str(getattr(c, col)) for col in CARRIERS_CSV_COLUMNS})


def load_aircraft_csv(path: str | Path) -> dict[str, 'AircraftSpec']:
    from utils.specs import AircraftSpec

    path = Path(path)
    rows: list[dict[str, str]] = []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f'{path} 缺少表头')
        missing = [c for c in AIRCRAFT_CSV_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f'{path} 缺少列: {missing}')
        rows.extend(reader)

    aircraft: dict[str, AircraftSpec] = {}
    for row in rows:
        if not row.get('id', '').strip():
            continue
        ac_id = row['id'].strip()
        aircraft[ac_id] = AircraftSpec(
            id=ac_id,
            name=row['name'].strip(),
            type_label=row['type_label'].strip(),
            mtow_kg=_parse_float(row['mtow_kg'], 'mtow_kg'),
            empty_kg=_parse_float(row['empty_kg'], 'empty_kg'),
            internal_fuel_kg=_parse_float(row['internal_fuel_kg'], 'internal_fuel_kg'),
            bvr_missile=row['bvr_missile'].strip(),
            missile_mass_kg=_parse_float(row['missile_mass_kg'], 'missile_mass_kg'),
            sweep_le_deg=_parse_float(row['sweep_le_deg'], 'sweep_le_deg'),
            wingspan_m=_parse_float(row['wingspan_m'], 'wingspan_m'),
            wing_area_m2=_parse_float(row['wing_area_m2'], 'wing_area_m2'),
            wing_height_m=_parse_float(row['wing_height_m'], 'wing_height_m'),
            cd0=_parse_float(row['cd0'], 'cd0'),
            t_max_sl_n=_parse_optional_float(row['t_max_sl_n']),
            t_main_stovl_sl_n=_parse_optional_float(row['t_main_stovl_sl_n']),
            t_liftfan_sl_n=_parse_optional_float(row['t_liftfan_sl_n']),
            t_rollposts_sl_n=_parse_optional_float(row['t_rollposts_sl_n']),
            exhaust_mdot_kg_s=_parse_optional_float(row.get('exhaust_mdot_kg_s', '')),
            exhaust_d0_m=_parse_optional_float(row.get('exhaust_d0_m', '')),
            exhaust_height_m=_parse_optional_float(row.get('exhaust_height_m', '')),
            notes=row.get('notes', '').strip(),
        )
    if not aircraft:
        raise ValueError(f'{path} 未读到有效舰载机记录')
    return aircraft


def load_carriers_csv(path: str | Path) -> list['CarrierSpec']:
    from utils.specs import CarrierSpec

    path = Path(path)
    carriers: list[CarrierSpec] = []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f'{path} 缺少表头')
        missing = [c for c in CARRIERS_CSV_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f'{path} 缺少列: {missing}')
        for row in reader:
            if not row.get('id', '').strip():
                continue
            carriers.append(CarrierSpec(
                id=row['id'].strip(),
                name=row['name'].strip(),
                nation=row['nation'].strip(),
                max_speed_kt=_parse_float(row['max_speed_kt'], 'max_speed_kt'),
                ski_jump=_parse_bool(row['ski_jump']),
                total_deck_length_m=_parse_float(row['total_deck_length_m'], 'total_deck_length_m'),
                ski_jump_angle_deg=_parse_float(row.get('ski_jump_angle_deg') or '0', 'ski_jump_angle_deg'),
                ski_jump_height_m=_parse_optional_float(row.get('ski_jump_height_m', '')),
                f35b_capable=_parse_bool(row['f35b_capable']),
                deck_length_source=row.get('deck_length_source', '').strip(),
                notes=row.get('notes', '').strip(),
            ))
    if not carriers:
        raise ValueError(f'{path} 未读到有效航母记录')
    return carriers
