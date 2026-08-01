"""单次起飞仿真 Web API（供 Pyodide / 本地 CLI 调用）。"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any

import short_ski_jump_take_off as ski_stovl
import short_take_off as flat_stovl
import ski_jump_take_off as ski_conv
from ski_jump_geometry import SKI_JUMP_REF_RADIUS_M, compute_ski_jump_arc
from takeoff_physics import (
    FLAP_DEFLECTION_DEG,
    FLAP_EFFICIENCY,
    PITCH_MAX_DEG,
    WING_INCIDENCE_DEG,
    calc_cl_alpha,
    calc_cl_from_alpha_deg,
    calc_oswald_e,
    taxi_alpha_deg,
)

PILOT_LOAD_KG = 100.0
A2A_MISSILE_COUNT = 4

MODES = {
    'ski_jump': '滑跃起飞',
    'short_takeoff': '短距起飞',
    'short_ski_jump': '短距滑跃起飞',
}


@dataclass(frozen=True)
class AircraftSpec:
    id: str
    name: str
    type_label: str
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

    @property
    def max_payload_kg(self) -> float:
        return self.mtow_kg - self.empty_kg - self.internal_fuel_kg - PILOT_LOAD_KG


@dataclass(frozen=True)
class CarrierSpec:
    id: str
    name: str
    nation: str
    max_speed_kt: float
    ski_jump: bool
    total_deck_length_m: float
    ski_jump_angle_deg: float = 0.0
    ski_jump_height_m: float | None = None
    f35b_capable: bool = False
    notes: str = ''
    deck_length_source: str = ''


def aircraft_from_dict(d: dict[str, Any]) -> AircraftSpec:
    return AircraftSpec(
        id=d['id'],
        name=d['name'],
        type_label=d['type_label'],
        mtow_kg=float(d['mtow_kg']),
        empty_kg=float(d['empty_kg']),
        internal_fuel_kg=float(d['internal_fuel_kg']),
        bvr_missile=d['bvr_missile'],
        missile_mass_kg=float(d['missile_mass_kg']),
        sweep_le_deg=float(d['sweep_le_deg']),
        wingspan_m=float(d['wingspan_m']),
        wing_area_m2=float(d['wing_area_m2']),
        wing_height_m=float(d['wing_height_m']),
        cd0=float(d.get('cd0', 0.039)),
        t_max_sl_n=_opt_float(d.get('t_max_sl_n')),
        t_main_stovl_sl_n=_opt_float(d.get('t_main_stovl_sl_n')),
        t_liftfan_sl_n=_opt_float(d.get('t_liftfan_sl_n')),
        t_rollposts_sl_n=_opt_float(d.get('t_rollposts_sl_n')),
        notes=d.get('notes', ''),
    )


def carrier_from_dict(d: dict[str, Any]) -> CarrierSpec:
    return CarrierSpec(
        id=d['id'],
        name=d['name'],
        nation=d['nation'],
        max_speed_kt=float(d['max_speed_kt']),
        ski_jump=bool(d['ski_jump']),
        total_deck_length_m=float(d['total_deck_length_m']),
        ski_jump_angle_deg=float(d.get('ski_jump_angle_deg') or 0),
        ski_jump_height_m=_opt_float(d.get('ski_jump_height_m')),
        f35b_capable=bool(d.get('f35b_capable')),
        notes=d.get('notes', ''),
        deck_length_source=d.get('deck_length_source', ''),
    )


def _opt_float(v: Any) -> float | None:
    if v is None or v == '':
        return None
    return float(v)


def resolve_ski_jump_geom(
    angle_deg: float,
    height_m: float | None = None,
    arc_length_m: float | None = None,
) -> dict[str, float]:
    """根据角度及可选高度/弧长，补全滑跃几何（缺失项用计算值）。"""
    angle_rad = angle_deg * 3.141592653589793 / 180.0
    if angle_deg <= 0:
        raise ValueError('滑跃角必须为正')

    if arc_length_m is not None and arc_length_m > 0:
        radius_m = arc_length_m / angle_rad
        lip_height_m = radius_m * (1.0 - __import__('math').cos(angle_rad))
        arc = compute_ski_jump_arc(angle_deg, radius_m=radius_m)
    elif height_m is not None and height_m > 0:
        arc = compute_ski_jump_arc(angle_deg, lip_height_m=height_m)
    else:
        arc = compute_ski_jump_arc(angle_deg)

    return {
        'angle_deg': arc.angle_deg,
        'radius_m': arc.radius_m,
        'arc_length_m': arc.arc_length_m,
        'horizontal_m': arc.horizontal_m,
        'lip_height_m': arc.lip_height_m,
        'ref_radius_m': SKI_JUMP_REF_RADIUS_M,
    }


def compute_aircraft_aero(ac: AircraftSpec) -> dict[str, float]:
    ar = ac.wingspan_m ** 2 / ac.wing_area_m2
    eta = calc_oswald_e(ar, ac.sweep_le_deg)
    cl_alpha = calc_cl_alpha(ar, eta, ac.sweep_le_deg)
    alpha_taxi = taxi_alpha_deg(FLAP_DEFLECTION_DEG, FLAP_EFFICIENCY, WING_INCIDENCE_DEG)
    return {
        'aspect_ratio': ar,
        'oswald_e': eta,
        'cl_alpha_per_rad': cl_alpha,
        'taxi_alpha_deg': alpha_taxi,
        'cl_taxi': calc_cl_from_alpha_deg(alpha_taxi, cl_alpha),
        'cl_20deg': calc_cl_from_alpha_deg(20.0, cl_alpha),
        'cd0': ac.cd0,
    }


def filter_carriers_for_mode(mode: str, carriers: list[CarrierSpec]) -> list[CarrierSpec]:
    if mode == 'ski_jump':
        return [c for c in carriers if c.ski_jump]
    if mode == 'short_takeoff':
        return [c for c in carriers if c.f35b_capable and not c.ski_jump]
    if mode == 'short_ski_jump':
        return [c for c in carriers if c.f35b_capable and c.ski_jump]
    raise ValueError(f'未知模式: {mode}')


def filter_aircraft_for_mode(mode: str, aircraft: list[AircraftSpec]) -> list[AircraftSpec]:
    if mode == 'ski_jump':
        return [a for a in aircraft if a.type_label != 'v/stol']
    if mode in ('short_takeoff', 'short_ski_jump'):
        return [a for a in aircraft if a.type_label == 'v/stol']
    raise ValueError(f'未知模式: {mode}')


def _deck_launch_label(success: bool, distance_m: float | None, deck_length_m: float) -> str:
    if not success or distance_m is None:
        return '仿真失败'
    margin = deck_length_m - distance_m
    if margin >= 0:
        return f'甲板可用（余量 {margin:.1f} m）'
    return f'甲板不足（超出 {-margin:.1f} m）'


def _configure_flat_stovl(ac: AircraftSpec, mass_kg: float, temp_c: float, wind_kt: float):
    geom = dict(mass_kg=mass_kg, s_ref_m2=ac.wing_area_m2, wingspan_m=ac.wingspan_m,
                wing_height_m=ac.wing_height_m, sweep_le_deg=ac.sweep_le_deg)
    thrust = dict(t_main_sl_n=ac.t_main_stovl_sl_n, t_liftfan_sl_n=ac.t_liftfan_sl_n,
                  t_rollposts_sl_n=ac.t_rollposts_sl_n)
    flat_stovl.apply_thrust_temperature(temp_c)
    flat_stovl.apply_stovl_thrust_sl(**thrust)
    flat_stovl.apply_wind_knots(wind_kt)
    flat_stovl.apply_aircraft_geometry(**geom)
    return flat_stovl


def _configure_ski_stovl(ac: AircraftSpec, mass_kg: float, temp_c: float, wind_kt: float,
                         ski_angle: float, lip_height_m: float | None):
    geom = dict(mass_kg=mass_kg, s_ref_m2=ac.wing_area_m2, wingspan_m=ac.wingspan_m,
                wing_height_m=ac.wing_height_m, sweep_le_deg=ac.sweep_le_deg)
    thrust = dict(t_main_sl_n=ac.t_main_stovl_sl_n, t_liftfan_sl_n=ac.t_liftfan_sl_n,
                  t_rollposts_sl_n=ac.t_rollposts_sl_n)
    ski_stovl.apply_thrust_temperature(temp_c)
    ski_stovl.apply_stovl_thrust_sl(**thrust)
    ski_stovl.apply_wind_knots(wind_kt)
    ski_stovl.apply_aircraft_geometry(**geom)
    ski_stovl.apply_ski_jump_deck(ski_angle, lip_height_m)
    return ski_stovl


def _configure_ski_conv(ac: AircraftSpec, mass_kg: float, temp_c: float, wind_kt: float,
                        ski_angle: float, lip_height_m: float | None):
    ski_conv.apply_thrust_temperature(temp_c)
    ski_conv.apply_wind_knots(wind_kt)
    ski_conv.apply_ski_jump_deck(ski_angle, lip_height_m)
    ski_conv.apply_aircraft_geometry(
        mass_kg=mass_kg, s_ref_m2=ac.wing_area_m2, wingspan_m=ac.wingspan_m,
        wing_height_m=ac.wing_height_m, sweep_le_deg=ac.sweep_le_deg,
        cd0=ac.cd0, t_max_sl_n=ac.t_max_sl_n)
    return ski_conv


def _format_f35b_output(result: dict, deck_length_m: float, mode_label: str) -> list[str]:
    pitch = '—' if result.get('pitch_deg') is None else f"{result['pitch_deg']}°"
    dist = result.get('distance_m') or result.get('total_m')
    flat_m = result.get('flat_m', result.get('x_m'))
    lines = [
        f'模式: {mode_label}',
        f"  重量:             {result.get('mass_kg', '—')} kg",
        f"  最小总距离:       {dist:.1f} m" if dist is not None else '  最小总距离:       —',
        f"  飞行甲板总长:     {deck_length_m:.0f} m",
        f"  甲板起飞:         {_deck_launch_label(True, dist, deck_length_m)}",
        f"  平直段:           {flat_m:.0f} m" if flat_m is not None else '  平直段:           —',
        f"  喷管最终角:       {result.get('nozzle_deg')}°",
        f"  开始偏转地速:     {result.get('v_trans_mps')} m/s",
    ]
    plume = result.get('min_plume_trailing_edge_m')
    if plume is not None:
        lines.append(f"  甲板受影响最后缘: {plume:.1f} m")
    v_deck = result.get('v_deck_mps') or result.get('v_gs_mps')
    t_deck = result.get('t_deck_s') or result.get('t_s')
    lines += [
        f"  俯仰角:           {pitch}",
        f"  离舰速度:         {v_deck:.1f} m/s" if v_deck else '  离舰速度:         —',
        f"  离舰用时:         {t_deck:.2f} s" if t_deck else '  离舰用时:         —',
    ]
    return lines


def _format_conv_output(result: dict, deck_length_m: float) -> list[str]:
    dist = result['total_m']
    return [
        '模式: 滑跃起飞',
        f"  重量:             {result.get('mass_kg', '—')} kg",
        f"  最小总距离:       {dist:.1f} m",
        f"  飞行甲板总长:     {deck_length_m:.0f} m",
        f"  甲板起飞:         {_deck_launch_label(True, dist, deck_length_m)}",
        f"  平直段:           {result['flat_m']:.0f} m",
        f"  俯仰角:           {result['pitch_deg']}°",
        f"  离舰速度:         {result['v_deck_mps']:.1f} m/s",
        f"  离舰用时:         {result['t_deck_s']:.2f} s",
    ]


def run_simulation(
    mode: str,
    aircraft: AircraftSpec | dict[str, Any],
    carrier: CarrierSpec | dict[str, Any],
    mass_kg: float,
    temp_c: float,
    wind_kt: float,
    ski_jump_angle_deg: float | None = None,
    ski_jump_arc_length_m: float | None = None,
    ski_jump_height_m: float | None = None,
    total_deck_length_m: float | None = None,
) -> dict[str, Any]:
    """运行单次仿真，返回结构化结果与文本输出。"""
    if isinstance(aircraft, dict):
        aircraft = aircraft_from_dict(aircraft)
    if isinstance(carrier, dict):
        carrier = carrier_from_dict(carrier)

    deck_length = total_deck_length_m if total_deck_length_m is not None else carrier.total_deck_length_m
    buf = io.StringIO()

    try:
        with redirect_stdout(buf):
            if mode == 'short_takeoff':
                if aircraft.type_label != 'v/stol':
                    raise ValueError('短距起飞仅适用于 STOVL 飞机')
                if carrier.ski_jump:
                    raise ValueError('短距起飞需要平直甲板航母')
                mod = _configure_flat_stovl(aircraft, mass_kg, temp_c, wind_kt)
                mod.print_config_summary()
                print()
                result = mod.run_strategy_a_search()
                if result is None:
                    return _fail('未能找到可行解', buf.getvalue(), mode)
                result['mass_kg'] = mass_kg
                result['distance_m'] = float(result['x_m'])
                lines = _format_f35b_output(result, deck_length, MODES[mode])

            elif mode == 'short_ski_jump':
                if aircraft.type_label != 'v/stol':
                    raise ValueError('短距滑跃起飞仅适用于 STOVL 飞机')
                if not carrier.ski_jump:
                    raise ValueError('短距滑跃起飞需要滑跃甲板')
                angle = ski_jump_angle_deg if ski_jump_angle_deg is not None else carrier.ski_jump_angle_deg
                geom = resolve_ski_jump_geom(angle, ski_jump_height_m, ski_jump_arc_length_m)
                mod = _configure_ski_stovl(
                    aircraft, mass_kg, temp_c, wind_kt, geom['angle_deg'], geom['lip_height_m'])
                mod.print_config_summary()
                print()
                result = mod.run_strategy_a_search()
                if result is None:
                    return _fail('未能找到可行解', buf.getvalue(), mode)
                if result['pitch_deg'] > PITCH_MAX_DEG:
                    raise ValueError(f"俯仰角 {result['pitch_deg']}° 超过硬上限 {PITCH_MAX_DEG}°")
                result['mass_kg'] = mass_kg
                result['distance_m'] = float(result['total_m'])
                lines = _format_f35b_output(result, deck_length, MODES[mode])

            elif mode == 'ski_jump':
                if not carrier.ski_jump:
                    raise ValueError('滑跃起飞需要滑跃甲板航母')
                if aircraft.type_label == 'v/stol':
                    raise ValueError('滑跃起飞模式请选择常规固定翼舰载机')
                angle = ski_jump_angle_deg if ski_jump_angle_deg is not None else carrier.ski_jump_angle_deg
                geom = resolve_ski_jump_geom(angle, ski_jump_height_m, ski_jump_arc_length_m)
                mod = _configure_ski_conv(
                    aircraft, mass_kg, temp_c, wind_kt, geom['angle_deg'], geom['lip_height_m'])
                mod.print_config_summary()
                print()
                result = mod.run_min_takeoff_search()
                if result is None:
                    return _fail('未能找到可行解', buf.getvalue(), mode)
                if result['pitch_deg'] > PITCH_MAX_DEG:
                    raise ValueError(f"俯仰角 {result['pitch_deg']}° 超过硬上限 {PITCH_MAX_DEG}°")
                result['mass_kg'] = mass_kg
                lines = _format_conv_output(result, deck_length)

            else:
                raise ValueError(f'未知模式: {mode}')

        config_text = buf.getvalue()
        output_lines = [
            '=' * 60,
            '仿真配置',
            '=' * 60,
            config_text.rstrip(),
            '',
            '=' * 60,
            '优化结果',
            '=' * 60,
        ] + lines

        distance_m = result.get('distance_m') or result.get('total_m')
        if distance_m is not None:
            distance_m = float(distance_m)

        return {
            'success': True,
            'mode': mode,
            'output': '\n'.join(output_lines),
            'distance_m': distance_m,
            'deck_launch_ok': distance_m is not None and distance_m <= deck_length,
            'deck_margin_m': deck_length - distance_m if distance_m is not None else None,
            'result': _json_safe(result),
        }
    except Exception as exc:
        config_text = buf.getvalue()
        msg = f'仿真错误: {exc}'
        output = config_text + ('\n' if config_text else '') + msg
        return {'success': False, 'mode': mode, 'output': output, 'error': str(exc)}


def _json_safe(obj: Any) -> Any:
    """将 numpy 标量等转为 JSON 可序列化类型。"""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if str(k).startswith('_') or k == 'history':
                continue
            out[k] = _json_safe(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    if hasattr(obj, 'item'):
        try:
            return obj.item()
        except ValueError:
            return obj.tolist()
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


def _fail(msg: str, config_text: str, mode: str) -> dict[str, Any]:
    output = (
        (config_text + '\n' if config_text else '')
        + f'✗ {msg}'
    )
    return {'success': False, 'mode': mode, 'output': output, 'error': msg}


def run_simulation_json(payload: dict[str, Any] | str) -> dict[str, Any]:
    """Pyodide 入口：接收 JSON dict 或 JSON 字符串，返回 JSON-serializable dict。"""
    if isinstance(payload, str):
        import json
        payload = json.loads(payload)
    elif hasattr(payload, 'to_py'):
        payload = payload.to_py()
    ac = payload['aircraft']
    carrier = payload['carrier']
    return run_simulation(
        mode=payload['mode'],
        aircraft=ac,
        carrier=carrier,
        mass_kg=float(payload['mass_kg']),
        temp_c=float(payload['temp_c']),
        wind_kt=float(payload['wind_kt']),
        ski_jump_angle_deg=_opt_float(payload.get('ski_jump_angle_deg')),
        ski_jump_arc_length_m=_opt_float(payload.get('ski_jump_arc_length_m')),
        ski_jump_height_m=_opt_float(payload.get('ski_jump_height_m')),
        total_deck_length_m=_opt_float(payload.get('total_deck_length_m')),
    )


if __name__ == '__main__':
    from database_csv import load_aircraft_csv, load_carriers_csv
    from pathlib import Path

    root = Path(__file__).resolve().parent
    ac_map = load_aircraft_csv(root / 'aircraft_database.csv')
    carriers = load_carriers_csv(root / 'carriers_database.csv')
    carrier = next(c for c in carriers if c.id == 'SHANDONG')
    ac = ac_map['J-15']
    r = run_simulation('ski_jump', ac, carrier, ac.a2a_mass_kg, 30.0, carrier.max_speed_kt)
    print(r['output'])
    sys.exit(0 if r['success'] else 1)
