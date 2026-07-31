"""
舰载机 × 航母最小起飞距离遍历（30°C，甲板风 = 航母最大航速）。

F-35B：策略 A（short_take_off / short_ski_jump_take_off）
常规型：ski_jump_take_off 最小总距搜索（仅 STOBAR 航母，不含 F-35B 适用舰）
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

import short_ski_jump_take_off as ski_stovl
import short_take_off as flat_stovl
import ski_jump_take_off as ski_conv

SURVEY_TEMP_C = 30.0
PILOT_LOAD_KG = 100.0
A2A_MISSILE_COUNT = 4
# 与仿真模块一致：俯仰角硬上限（°）
PITCH_MAX_DEG = ski_conv.PITCH_MAX_DEG

# 保存搜索范围默认值，便于多次运行前恢复
_SEARCH_DEFAULTS = {
    'flat_stovl': dict(
        NOZZLE_FINAL_DEG_START=flat_stovl.NOZZLE_FINAL_DEG_START,
        NOZZLE_FINAL_DEG_END=flat_stovl.NOZZLE_FINAL_DEG_END,
        V_TRANS_START_MPS=flat_stovl.V_TRANS_START_MPS,
        V_TRANS_END_MPS=flat_stovl.V_TRANS_END_MPS,
    ),
    'ski_stovl': dict(
        FLAT_LENGTH_M_LIST_A=list(ski_stovl.FLAT_LENGTH_M_LIST_A),
        NOZZLE_TAKEOFF_DEG_LIST_A=list(ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A),
        V_TRANS_MPS_LIST_A=list(ski_stovl.V_TRANS_MPS_LIST_A),
    ),
    'ski_conv': dict(
        PITCH_SEARCH_MIN=ski_conv.PITCH_SEARCH_MIN,
        PITCH_SEARCH_MAX=ski_conv.PITCH_SEARCH_MAX,
        FLAT_SEARCH_MAX_M=ski_conv.FLAT_SEARCH_MAX_M,
    ),
}
PILOT_LOAD_KG = 100.0
A2A_MISSILE_COUNT = 4

# 记录搜索边界是否被最优解触及，用于事后收紧未使用的边界
BOUNDARY_HITS: dict[str, set[str]] = {
    'flat_stovl': set(),
    'ski_stovl': set(),
    'ski_conv': set(),
}


@dataclass(frozen=True)
class AircraftSpec:
    id: str
    name: str
    type_label: str  # 'conventional' | 'v/stol'
    mtow_kg: float
    empty_kg: float
    internal_fuel_kg: float
    bvr_missile: str
    missile_mass_kg: float
    sweep_le_deg: float
    wingspan_m: float
    wing_area_m2: float
    wing_height_m: float
    cd0: float = 0.039
    t_max_sl_n: float | None = None
    t_main_stovl_sl_n: float | None = None
    t_liftfan_sl_n: float | None = None
    t_rollposts_sl_n: float | None = None
    notes: str = ''

    @property
    def a2a_mass_kg(self) -> float:
        return (self.empty_kg + self.internal_fuel_kg
                + A2A_MISSILE_COUNT * self.missile_mass_kg + PILOT_LOAD_KG)


@dataclass(frozen=True)
class CarrierSpec:
    id: str
    name: str
    nation: str
    max_speed_kt: float
    ski_jump: bool
    ski_jump_angle_deg: float = 0.0
    ski_jump_length_m: float = 0.0
    ski_jump_height_m: float | None = None
    f35b_capable: bool = False
    notes: str = ''

    def deck_wind_kt(self) -> float:
        return self.max_speed_kt

    def ski_jump_arc_m(self) -> float:
        if not self.ski_jump:
            return 0.0
        if self.ski_jump_length_m > 0:
            return self.ski_jump_length_m
        if self.ski_jump_height_m:
            return self.ski_jump_height_m / math.sin(math.radians(self.ski_jump_angle_deg))
        return 35.0


def _estimate_arc(angle_deg: float, height_m: float | None, documented_m: float | None) -> float:
    if documented_m:
        return documented_m
    if height_m:
        return height_m / math.sin(math.radians(angle_deg))
    return 35.0


AIRCRAFT: dict[str, AircraftSpec] = {
    'F-35B': AircraftSpec(
        id='F-35B', name='F-35B Lightning II', type_label='v/stol',
        mtow_kg=27200, empty_kg=14651, internal_fuel_kg=6400,
        bvr_missile='AIM-120C AMRAAM', missile_mass_kg=152.0,
        sweep_le_deg=35, wingspan_m=10.7, wing_area_m2=42.7, wing_height_m=1.96,
        cd0=0.039,
        t_main_stovl_sl_n=83260, t_liftfan_sl_n=83260, t_rollposts_sl_n=14600,
        notes='STOVL 推力为垂起模式海平面标定值（15°C）',
    ),
    'J-15': AircraftSpec(
        id='J-15', name='歼-15', type_label='conventional',
        mtow_kg=33000, empty_kg=17500, internal_fuel_kg=9800,
        bvr_missile='PL-12', missile_mass_kg=199.0,
        sweep_le_deg=42, wingspan_m=14.7, wing_area_m2=67.84, wing_height_m=2.55,
        cd0=0.0475, t_max_sl_n=251000,
        notes='WS-10H/AL-31 双发最大加力约 251 kN（15°C 标定）',
    ),
    'J-15T': AircraftSpec(
        id='J-15T', name='歼-15T', type_label='conventional',
        mtow_kg=35900, empty_kg=17800, internal_fuel_kg=10000,
        bvr_missile='PL-15', missile_mass_kg=210.0,
        sweep_le_deg=42, wingspan_m=14.7, wing_area_m2=67.84, wing_height_m=2.55,
        cd0=0.0475, t_max_sl_n=264000,
        notes='弹射型，滑跃舰上仍按 STOBAR 仿真；加力约 264 kN',
    ),
    'J-35': AircraftSpec(
        id='J-35', name='歼-35', type_label='conventional',
        mtow_kg=29500, empty_kg=15500, internal_fuel_kg=8000,
        bvr_missile='PL-15', missile_mass_kg=210.0,
        sweep_le_deg=38, wingspan_m=13.6, wing_area_m2=66.9, wing_height_m=1.96,
        cd0=0.039, t_max_sl_n=186000,
        notes='WS-21 级双发加力约 186 kN（公开估算）',
    ),
    'MiG-29K': AircraftSpec(
        id='MiG-29K', name='MiG-29K', type_label='conventional',
        mtow_kg=24500, empty_kg=12000, internal_fuel_kg=4560,
        bvr_missile='RVV-AE (R-77)', missile_mass_kg=175.0,
        sweep_le_deg=40, wingspan_m=11.99, wing_area_m2=34.5, wing_height_m=1.89,
        cd0=0.042, t_max_sl_n=176380,
        notes='2×RD-33MK 加力各 88.3 kN；翼展/面积/翼高为公开数据估算',
    ),
    'Rafale-M': AircraftSpec(
        id='Rafale-M', name='阵风 M', type_label='conventional',
        mtow_kg=24500, empty_kg=10600, internal_fuel_kg=4700,
        bvr_missile='MBDA Meteor', missile_mass_kg=190.0,
        sweep_le_deg=48, wingspan_m=10.80, wing_area_m2=45.7, wing_height_m=1.90,
        cd0=0.036, t_max_sl_n=150000,
        notes='2×M88-2/E4 加力各 75 kN（15°C SL）；空重/内油/翼面积取自 Dassault/法军公开数据',
    ),
    'FA-18E': AircraftSpec(
        id='FA-18E', name='F/A-18E Super Hornet', type_label='conventional',
        mtow_kg=29937, empty_kg=14552, internal_fuel_kg=6667,
        bvr_missile='AIM-120C AMRAAM', missile_mass_kg=152.0,
        sweep_le_deg=20, wingspan_m=13.62, wing_area_m2=46.5, wing_height_m=1.55,
        cd0=0.042, t_max_sl_n=195800,
        notes='2×F414-GE-400 加力各 97.9 kN（15°C SL）；NAVAIR/DefenceDB 公开数据',
    ),
}

CARRIERS: list[CarrierSpec] = [
    CarrierSpec(
        id='QE', name='伊丽莎白女王级', nation='英国',
        max_speed_kt=25, ski_jump=True, ski_jump_angle_deg=13.0,
        ski_jump_height_m=6.0, f35b_capable=True,
        notes='公开数据：>25 kn，13° ski-jump，跳台高约 6 m',
    ),
    CarrierSpec(
        id='IZUMO', name='出云级', nation='日本',
        max_speed_kt=30, ski_jump=False, f35b_capable=True,
        notes='改装后无 ski-jump，F-35B 短距滑跑起飞',
    ),
    CarrierSpec(
        id='CAVOUR', name='加富尔级', nation='意大利',
        max_speed_kt=29, ski_jump=True, ski_jump_angle_deg=12.0,
        ski_jump_length_m=35.0, f35b_capable=True,
        notes='29 kn，12° ski-jump；弧长约 35 m（估算）',
    ),
    CarrierSpec(
        id='TRIESTE', name='的里雅斯特级', nation='意大利',
        max_speed_kt=25, ski_jump=True, ski_jump_angle_deg=12.0,
        ski_jump_length_m=35.0, f35b_capable=True,
        notes='LHD Trieste，25 kn，12° ski-jump',
    ),
    CarrierSpec(
        id='WASP', name='黄蜂级', nation='美国',
        max_speed_kt=22, ski_jump=False, f35b_capable=True,
        notes='LHD/LHA，22 kn，平直甲板 STOVL',
    ),
    CarrierSpec(
        id='KUZNETSOV', name='库兹涅佐夫级', nation='中/俄',
        max_speed_kt=30, ski_jump=True, ski_jump_angle_deg=14.0,
        ski_jump_length_m=50.0, f35b_capable=False,
        notes='辽宁/山东/库兹涅佐夫；29 kn，14°，弧长约 50 m',
    ),
    CarrierSpec(
        id='VIKRAMADITYA', name='超日王号', nation='印度',
        max_speed_kt=29, ski_jump=True, ski_jump_angle_deg=14.3,
        ski_jump_length_m=45.0, f35b_capable=False,
        notes='改装自戈尔什科夫号；29 kn，14.3°',
    ),
    CarrierSpec(
        id='VIKRANT', name='维克兰特号', nation='印度',
        max_speed_kt=28, ski_jump=True, ski_jump_angle_deg=14.0,
        ski_jump_length_m=45.0, f35b_capable=False,
        notes='国产 STOBAR；28 kn，14°',
    ),
]


def _carrier_deck_desc(c: CarrierSpec) -> str:
    if c.ski_jump:
        return (f"滑跃 {c.ski_jump_arc_m():.0f} m / {c.ski_jump_angle_deg:.1f}°，"
                f"最大航速 {c.max_speed_kt:.0f} kt（甲板风）")
    return f"平直甲板，最大航速 {c.max_speed_kt:.0f} kt（甲板风）"


def _configure_f35b(ac: AircraftSpec, carrier: CarrierSpec, mass_kg: float):
    geom = dict(mass_kg=mass_kg, s_ref_m2=ac.wing_area_m2, wingspan_m=ac.wingspan_m,
                wing_height_m=ac.wing_height_m, sweep_le_deg=ac.sweep_le_deg)
    thrust = dict(t_main_sl_n=ac.t_main_stovl_sl_n, t_liftfan_sl_n=ac.t_liftfan_sl_n,
                  t_rollposts_sl_n=ac.t_rollposts_sl_n)
    wind_kt = carrier.deck_wind_kt()
    if carrier.ski_jump:
        ski_stovl.apply_thrust_temperature(SURVEY_TEMP_C)
        ski_stovl.apply_stovl_thrust_sl(**thrust)
        ski_stovl.apply_wind_knots(wind_kt)
        ski_stovl.apply_aircraft_geometry(**geom)
        ski_stovl.apply_ski_jump_deck(carrier.ski_jump_arc_m(), carrier.ski_jump_angle_deg)
        return ski_stovl
    flat_stovl.apply_thrust_temperature(SURVEY_TEMP_C)
    flat_stovl.apply_stovl_thrust_sl(**thrust)
    flat_stovl.apply_wind_knots(wind_kt)
    flat_stovl.apply_aircraft_geometry(**geom)
    return flat_stovl


def _configure_conventional(ac: AircraftSpec, carrier: CarrierSpec, mass_kg: float):
    ski_conv.apply_thrust_temperature(SURVEY_TEMP_C)
    ski_conv.apply_wind_knots(carrier.deck_wind_kt())
    ski_conv.apply_ski_jump_deck(carrier.ski_jump_arc_m(), carrier.ski_jump_angle_deg)
    ski_conv.apply_aircraft_geometry(
        mass_kg=mass_kg, s_ref_m2=ac.wing_area_m2, wingspan_m=ac.wingspan_m,
        wing_height_m=ac.wing_height_m, sweep_le_deg=ac.sweep_le_deg,
        cd0=ac.cd0, t_max_sl_n=ac.t_max_sl_n)
    return ski_conv


def _check_flat_stovl_boundaries(mod, result: dict) -> set[str]:
    hits = set()
    if result['nozzle_deg'] <= mod.NOZZLE_FINAL_DEG_START + 1:
        hits.add('nozzle_low')
    if result['nozzle_deg'] >= mod.NOZZLE_FINAL_DEG_END - 1:
        hits.add('nozzle_high')
    if result['v_trans_mps'] <= mod.V_TRANS_START_MPS + 1:
        hits.add('vtrans_low')
    if result['v_trans_mps'] >= mod.V_TRANS_END_MPS - 1:
        hits.add('vtrans_high')
    return hits


def _assert_pitch_within_limit(pitch_deg: float):
    if pitch_deg > PITCH_MAX_DEG:
        raise ValueError(f"俯仰角 {pitch_deg}° 超过硬上限 {PITCH_MAX_DEG}°")


def _check_ski_stovl_boundaries(mod, result: dict) -> set[str]:
    hits = set()
    flats = list(mod.FLAT_LENGTH_M_LIST_A)
    nozzles = list(mod.NOZZLE_TAKEOFF_DEG_LIST_A)
    vtrans = list(mod.V_TRANS_MPS_LIST_A)
    pitches = list(mod.PITCH_DEG_LIST)
    if result['flat_m'] <= min(flats) + 5:
        hits.add('flat_low')
    if result['flat_m'] >= max(flats) - 5:
        hits.add('flat_high')
    if result['nozzle_deg'] <= min(nozzles) + 2:
        hits.add('nozzle_low')
    if result['nozzle_deg'] >= max(nozzles) - 2:
        hits.add('nozzle_high')
    if result['v_trans_mps'] <= min(vtrans) + 2:
        hits.add('vtrans_low')
    if result['v_trans_mps'] >= max(vtrans) - 2:
        hits.add('vtrans_high')
    if result['pitch_deg'] <= min(pitches):
        hits.add('pitch_low')
    if result['pitch_deg'] >= max(pitches):
        hits.add('pitch_high')
    return hits


def _capture_search_defaults():
    """从当前仿真模块读取搜索范围，供多次运行前恢复。"""
    _SEARCH_DEFAULTS['flat_stovl'] = dict(
        NOZZLE_FINAL_DEG_START=flat_stovl.NOZZLE_FINAL_DEG_START,
        NOZZLE_FINAL_DEG_END=flat_stovl.NOZZLE_FINAL_DEG_END,
        V_TRANS_START_MPS=flat_stovl.V_TRANS_START_MPS,
        V_TRANS_END_MPS=flat_stovl.V_TRANS_END_MPS,
    )
    _SEARCH_DEFAULTS['ski_stovl'] = dict(
        FLAT_LENGTH_M_LIST_A=list(ski_stovl.FLAT_LENGTH_M_LIST_A),
        NOZZLE_TAKEOFF_DEG_LIST_A=list(ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A),
        V_TRANS_MPS_LIST_A=list(ski_stovl.V_TRANS_MPS_LIST_A),
    )
    _SEARCH_DEFAULTS['ski_conv'] = dict(
        PITCH_SEARCH_MIN=ski_conv.PITCH_SEARCH_MIN,
        PITCH_SEARCH_MAX=ski_conv.PITCH_SEARCH_MAX,
        FLAT_SEARCH_MAX_M=ski_conv.FLAT_SEARCH_MAX_M,
    )


def _check_ski_conv_boundaries(mod, result: dict) -> set[str]:
    hits = set()
    if result['flat_m'] <= 5:
        hits.add('flat_low')
    if result['flat_m'] >= mod.FLAT_SEARCH_MAX_M - 5:
        hits.add('flat_high')
    if result['pitch_deg'] <= mod.PITCH_SEARCH_MIN + 1:
        hits.add('pitch_low')
    if result['pitch_deg'] >= mod.PITCH_SEARCH_MAX - 1:
        hits.add('pitch_high')
    return hits


def _record_hits(category: str, hits: set[str]):
    BOUNDARY_HITS[category].update(hits)


def _expand_flat_stovl_bounds(hits: set[str]):
    if 'nozzle_low' in hits:
        flat_stovl.NOZZLE_FINAL_DEG_START = max(5, flat_stovl.NOZZLE_FINAL_DEG_START - 10)
    if 'nozzle_high' in hits:
        flat_stovl.NOZZLE_FINAL_DEG_END = min(95, flat_stovl.NOZZLE_FINAL_DEG_END + 5)
    if 'vtrans_low' in hits:
        flat_stovl.V_TRANS_START_MPS = max(0, flat_stovl.V_TRANS_START_MPS - 10)
    if 'vtrans_high' in hits:
        flat_stovl.V_TRANS_END_MPS = min(90, flat_stovl.V_TRANS_END_MPS + 10)


def _expand_ski_stovl_bounds(hits: set[str]):
    if 'flat_low' in hits:
        lo = min(ski_stovl.FLAT_LENGTH_M_LIST_A)
        extra = list(range(max(10, lo - 40), lo, 5))
        merged = sorted(set(extra + list(ski_stovl.FLAT_LENGTH_M_LIST_A)))
        ski_stovl.FLAT_LENGTH_M_LIST_A = merged
    if 'flat_high' in hits:
        hi = max(ski_stovl.FLAT_LENGTH_M_LIST_A)
        extra = list(range(hi + 10, hi + 80, 10))
        merged = sorted(set(list(ski_stovl.FLAT_LENGTH_M_LIST_A) + extra))
        ski_stovl.FLAT_LENGTH_M_LIST_A = merged
    if 'nozzle_low' in hits:
        lo = min(ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A)
        extra = list(range(max(0, lo - 20), lo, 5))
        ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A = sorted(set(extra + list(ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A)))
    if 'nozzle_high' in hits:
        hi = max(ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A)
        extra = list(range(hi + 5, min(95, hi + 30), 5))
        ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A = sorted(set(list(ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A) + extra))
    if 'vtrans_low' in hits:
        lo = min(ski_stovl.V_TRANS_MPS_LIST_A)
        extra = list(range(max(0, lo - 15), lo, 5))
        ski_stovl.V_TRANS_MPS_LIST_A = sorted(set(extra + list(ski_stovl.V_TRANS_MPS_LIST_A)))
    if 'vtrans_high' in hits:
        hi = max(ski_stovl.V_TRANS_MPS_LIST_A)
        extra = list(range(hi + 5, hi + 30, 5))
        ski_stovl.V_TRANS_MPS_LIST_A = sorted(set(list(ski_stovl.V_TRANS_MPS_LIST_A) + extra))


def _expand_ski_conv_bounds(hits: set[str]):
    if 'flat_low' in hits:
        pass  # 粗搜索已从 0 开始
    if 'flat_high' in hits:
        ski_conv.FLAT_SEARCH_MAX_M = min(400, ski_conv.FLAT_SEARCH_MAX_M + 60)
    if 'pitch_low' in hits:
        ski_conv.PITCH_SEARCH_MIN = max(5, ski_conv.PITCH_SEARCH_MIN - 3)
    if 'pitch_high' in hits:
        ski_conv.PITCH_SEARCH_MAX = min(PITCH_MAX_DEG, ski_conv.PITCH_SEARCH_MAX + 3)


def run_f35b_case(ac: AircraftSpec, carrier: CarrierSpec, load_label: str, mass_kg: float) -> dict[str, Any]:
    mod = _configure_f35b(ac, carrier, mass_kg)
    for attempt in range(3):
        if carrier.ski_jump:
            result = mod.run_strategy_a_search()
            if result is None:
                return dict(success=False, aircraft=ac.id, carrier=carrier.id, load=load_label)
            _assert_pitch_within_limit(result['pitch_deg'])
            hits = _check_ski_stovl_boundaries(mod, result)
            _record_hits('ski_stovl', hits)
            if hits and attempt < 2:
                _expand_ski_stovl_bounds(hits)
                _configure_f35b(ac, carrier, mass_kg)
                continue
            dist = result['total_m']
            detail = (f"平直段 {result['flat_m']:.0f} m，喷管 {result['nozzle_deg']}°，"
                      f"转换 {result['v_trans_mps']} m/s，俯仰 {result['pitch_deg']}°")
        else:
            result = mod.run_strategy_a_search()
            if result is None:
                return dict(success=False, aircraft=ac.id, carrier=carrier.id, load=load_label)
            hits = _check_flat_stovl_boundaries(mod, result)
            _record_hits('flat_stovl', hits)
            if hits and attempt < 2:
                _expand_flat_stovl_bounds(hits)
                _configure_f35b(ac, carrier, mass_kg)
                continue
            dist = result['x_m']
            detail = (f"喷管 {result['nozzle_deg']}°，转换 {result['v_trans_mps']} m/s，"
                      f"离地 {result['v_gs_mps']:.1f} m/s")
        return dict(
            success=True, aircraft=ac.id, carrier=carrier.id, load=load_label,
            mass_kg=mass_kg, distance_m=dist, detail=detail,
            carrier_desc=_carrier_deck_desc(carrier),
            wind_kt=carrier.deck_wind_kt(), temp_c=SURVEY_TEMP_C,
        )
    return dict(success=False, aircraft=ac.id, carrier=carrier.id, load=load_label)


def run_conventional_case(ac: AircraftSpec, carrier: CarrierSpec, load_label: str, mass_kg: float) -> dict[str, Any]:
    if not carrier.ski_jump:
        return dict(success=False, aircraft=ac.id, carrier=carrier.id, load=load_label,
                    note='该舰无滑跃甲板')
    mod = _configure_conventional(ac, carrier, mass_kg)
    for attempt in range(2):
        result = mod.run_min_takeoff_search()
        if result is None:
            return dict(success=False, aircraft=ac.id, carrier=carrier.id, load=load_label)
        _assert_pitch_within_limit(result['pitch_deg'])
        hits = _check_ski_conv_boundaries(mod, result)
        _record_hits('ski_conv', hits)
        if hits & {'pitch_low', 'pitch_high'} and attempt == 0:
            _expand_ski_conv_bounds(hits)
            _configure_conventional(ac, carrier, mass_kg)
            continue
        detail = (f"平直段 {result['flat_m']:.0f} m，俯仰 {result['pitch_deg']}°，"
                  f"离板 {result['v_deck_mps']:.1f} m/s")
        return dict(
            success=True, aircraft=ac.id, carrier=carrier.id, load=load_label,
            mass_kg=mass_kg, distance_m=result['total_m'], detail=detail,
            carrier_desc=_carrier_deck_desc(carrier),
            wind_kt=carrier.deck_wind_kt(), temp_c=SURVEY_TEMP_C,
        )
    return dict(success=False, aircraft=ac.id, carrier=carrier.id, load=load_label)


def print_aircraft_database():
    print('=' * 88)
    print('舰载机参数库')
    print('=' * 88)
    for ac in AIRCRAFT.values():
        print(f"\n【{ac.name}】 ({ac.type_label})")
        print(f"  MTOW: {ac.mtow_kg:.0f} kg | 空重: {ac.empty_kg:.0f} kg | 内油: {ac.internal_fuel_kg:.0f} kg")
        print(f"  中距弹: {ac.bvr_missile} ×{A2A_MISSILE_COUNT}（{ac.missile_mass_kg:.0f} kg/枚）")
        print(f"  空战挂载: {ac.a2a_mass_kg:.0f} kg（含飞行员相关 {PILOT_LOAD_KG:.0f} kg）")
        print(f"  后掠角 {ac.sweep_le_deg}° | 翼展 {ac.wingspan_m} m | 面积 {ac.wing_area_m2} m² | 翼高 {ac.wing_height_m} m")
        if ac.type_label == 'v/stol':
            print(f"  垂起推力(15°C SL): 主喷管 {ac.t_main_stovl_sl_n/1000:.1f} kN，"
                  f"升力风扇 {ac.t_liftfan_sl_n/1000:.1f} kN，滚转 {ac.t_rollposts_sl_n/1000:.1f} kN")
        else:
            print(f"  最大加力(15°C SL): {ac.t_max_sl_n/1000:.1f} kN | Cd0={ac.cd0}")
        if ac.notes:
            print(f"  备注: {ac.notes}")


def print_carrier_database():
    print('\n' + '=' * 88)
    print('航母参数库')
    print('=' * 88)
    for c in CARRIERS:
        cap = 'F-35B 适用' if c.f35b_capable else '常规滑跃机适用'
        print(f"\n【{c.name}】 ({c.nation}) — {cap}")
        print(f"  {_carrier_deck_desc(c)}")
        if c.notes:
            print(f"  备注: {c.notes}")


def _print_result_row(r: dict[str, Any]):
    if not r.get('success'):
        print(f"  ✗ {r['aircraft']} @ {r['carrier']} [{r['load']}] — 未能找到可行解")
        return
    print(f"  ✓ {r['aircraft']} @ {r['carrier']} [{r['load']}]  {r['mass_kg']:.0f} kg")
    print(f"      航母: {r['carrier_desc']}")
    print(f"      最小起飞总距离: {r['distance_m']:.1f} m  |  {r['detail']}")


def _reset_search_ranges():
    d = _SEARCH_DEFAULTS['flat_stovl']
    flat_stovl.NOZZLE_FINAL_DEG_START = d['NOZZLE_FINAL_DEG_START']
    flat_stovl.NOZZLE_FINAL_DEG_END = d['NOZZLE_FINAL_DEG_END']
    flat_stovl.V_TRANS_START_MPS = d['V_TRANS_START_MPS']
    flat_stovl.V_TRANS_END_MPS = d['V_TRANS_END_MPS']
    d = _SEARCH_DEFAULTS['ski_stovl']
    ski_stovl.FLAT_LENGTH_M_LIST_A = list(d['FLAT_LENGTH_M_LIST_A'])
    ski_stovl.NOZZLE_TAKEOFF_DEG_LIST_A = list(d['NOZZLE_TAKEOFF_DEG_LIST_A'])
    ski_stovl.V_TRANS_MPS_LIST_A = list(d['V_TRANS_MPS_LIST_A'])
    d = _SEARCH_DEFAULTS['ski_conv']
    ski_conv.PITCH_SEARCH_MIN = d['PITCH_SEARCH_MIN']
    ski_conv.PITCH_SEARCH_MAX = d['PITCH_SEARCH_MAX']
    ski_conv.FLAT_SEARCH_MAX_M = d['FLAT_SEARCH_MAX_M']


def run_conv_survey_subset(aircraft_ids: tuple[str, ...]):
    """仅对指定常规机型 × STOBAR 航母运行滑跃起飞搜索（不重复已有组合）。"""
    _capture_search_defaults()
    _reset_search_ranges()
    BOUNDARY_HITS['ski_conv'].clear()

    conv_carriers = [c for c in CARRIERS if c.ski_jump and not c.f35b_capable]
    missing = [aid for aid in aircraft_ids if aid not in AIRCRAFT]
    if missing:
        raise KeyError(f'未知机型: {missing}')

    print('=' * 88)
    print(f'常规舰载机增量遍历（{SURVEY_TEMP_C:.0f}°C，STOBAR 航母：'
          f'{", ".join(c.name for c in conv_carriers)}）')
    print('=' * 88)
    for aid in aircraft_ids:
        ac = AIRCRAFT[aid]
        print(f"\n【{ac.name}】 MTOW {ac.mtow_kg:.0f} kg | 空战 {ac.a2a_mass_kg:.0f} kg | "
              f"加力 {ac.t_max_sl_n/1000:.1f} kN")

    results = []
    for aid in aircraft_ids:
        ac = AIRCRAFT[aid]
        for carrier in conv_carriers:
            for load_label, mass in (('空战挂载', ac.a2a_mass_kg), ('MTOW', ac.mtow_kg)):
                print(f"\n--- {ac.name} | {carrier.name} | {load_label} ---")
                r = run_conventional_case(ac, carrier, load_label, mass)
                results.append(r)
                _print_result_row(r)

    print('\n' + '=' * 88)
    print('增量汇总表')
    print('=' * 88)
    print(f"\n{'机型':<10} {'航母':<14} {'挂载':<8} {'重量kg':>8} {'总距m':>8}  甲板条件")
    print('-' * 88)
    for r in results:
        if not r.get('success'):
            print(f"{r['aircraft']:<10} {r['carrier']:<14} {r['load']:<8} {'—':>8} {'失败':>8}")
            continue
        print(f"{r['aircraft']:<10} {r['carrier']:<14} {r['load']:<8} {r['mass_kg']:>8.0f} "
              f"{r['distance_m']:>8.1f}  {r['carrier_desc']}")
    return results


def run_survey():
    _capture_search_defaults()
    _reset_search_ranges()
    BOUNDARY_HITS['flat_stovl'].clear()
    BOUNDARY_HITS['ski_stovl'].clear()
    BOUNDARY_HITS['ski_conv'].clear()
    print_aircraft_database()
    print_carrier_database()

    f35b = AIRCRAFT['F-35B']
    f35b_carriers = [c for c in CARRIERS if c.f35b_capable]
    conv_ac = [AIRCRAFT[k] for k in ('J-15', 'J-15T', 'J-35', 'MiG-29K', 'Rafale-M', 'FA-18E')]
    # 常规滑跃机仅在 STOBAR 航母上计算，跳过 F-35B 适用舰（QE/加富尔/的里雅斯特等）
    conv_carriers = [c for c in CARRIERS if c.ski_jump and not c.f35b_capable]

    print('\n' + '=' * 88)
    print(f'F-35B 策略 A 遍历（{SURVEY_TEMP_C:.0f}°C，甲板风 = 航母最大航速）')
    print('=' * 88)
    f35b_results = []
    for carrier in f35b_carriers:
        for load_label, mass in (('空战挂载', f35b.a2a_mass_kg), ('MTOW', f35b.mtow_kg)):
            print(f"\n--- {f35b.name} | {carrier.name} | {load_label} ---")
            r = run_f35b_case(f35b, carrier, load_label, mass)
            f35b_results.append(r)
            _print_result_row(r)

    print('\n' + '=' * 88)
    print(f'常规舰载机滑跃起飞遍历（{SURVEY_TEMP_C:.0f}°C，甲板风 = 航母最大航速，仅 STOBAR 航母）')
    print('=' * 88)
    conv_results = []
    for ac in conv_ac:
        for carrier in conv_carriers:
            for load_label, mass in (('空战挂载', ac.a2a_mass_kg), ('MTOW', ac.mtow_kg)):
                print(f"\n--- {ac.name} | {carrier.name} | {load_label} ---")
                r = run_conventional_case(ac, carrier, load_label, mass)
                conv_results.append(r)
                _print_result_row(r)

    print('\n' + '=' * 88)
    print('汇总表')
    print('=' * 88)
    print(f"\n{'机型':<10} {'航母':<14} {'挂载':<8} {'重量kg':>8} {'总距m':>8}  甲板条件")
    print('-' * 88)
    for r in f35b_results + conv_results:
        if not r.get('success'):
            print(f"{r['aircraft']:<10} {r['carrier']:<14} {r['load']:<8} {'—':>8} {'失败':>8}")
            continue
        print(f"{r['aircraft']:<10} {r['carrier']:<14} {r['load']:<8} {r['mass_kg']:>8.0f} "
              f"{r['distance_m']:>8.1f}  {r['carrier_desc']}")

    print('\n边界触及记录（供搜索范围调整参考）:')
    for key, hits in BOUNDARY_HITS.items():
        print(f"  {key}: {sorted(hits) if hits else '无'}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--conv-only':
        ids = tuple(sys.argv[2:]) if len(sys.argv) > 2 else ('Rafale-M', 'FA-18E')
        run_conv_survey_subset(ids)
    else:
        run_survey()
