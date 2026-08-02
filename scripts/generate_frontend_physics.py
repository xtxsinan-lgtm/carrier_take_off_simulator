#!/usr/bin/env python3
"""从 Python 物理常量生成前端 physics.js（Web ESM + 小程序 CommonJS）。

算法与 utils/takeoff_physics.py、utils/ski_jump_geometry.py、utils/specs.py 对齐；
常量在生成时注入。请勿手改 docs/js/physics.js 或 miniprogram/utils/physics.js。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_PHYSICS = ROOT / 'docs' / 'js' / 'physics.js'
MINI_PHYSICS = ROOT / 'miniprogram' / 'utils' / 'physics.js'

# 导出符号列表（ESM / CJS 共用）
_EXPORT_NAMES = (
    'computeSkiJumpArc',
    'resolveCarrierSkiJump',
    'calcOswaldE',
    'calcClAlpha',
    'calcClFromAlphaDeg',
    'taxiAlphaDeg',
    'computeAircraftAero',
    'a2aMassKg',
    'maxPayloadKg',
    'filterCarriersForMode',
    'filterAircraftForMode',
    'fmtNum',
    'fmtInt',
    'modeNeedsSkiJump',
    'modeHasTrajectory',
    'defaultDeckWindKt',
)


def _load_constants() -> dict:
    """从 Python 源读取前端预览所需常量。"""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from utils.ski_jump_geometry import SKI_JUMP_REF_RADIUS_M
    from utils.specs import A2A_MISSILE_COUNT, PILOT_LOAD_KG
    from utils.takeoff_physics import (
        FLAP_DEFLECTION_DEG,
        FLAP_EFFICIENCY,
        PITCH_MAX_DEG,
        WING_INCIDENCE_DEG,
    )
    return {
        'SKI_JUMP_REF_RADIUS_M': float(SKI_JUMP_REF_RADIUS_M),
        'FLAP_DEFLECTION_DEG': float(FLAP_DEFLECTION_DEG),
        'FLAP_EFFICIENCY': float(FLAP_EFFICIENCY),
        'WING_INCIDENCE_DEG': float(WING_INCIDENCE_DEG),
        'PILOT_LOAD_KG': float(PILOT_LOAD_KG),
        'A2A_MISSILE_COUNT': int(A2A_MISSILE_COUNT),
        'PITCH_MAX_DEG': float(PITCH_MAX_DEG),
    }


def render_physics_body(constants: dict | None = None) -> str:
    """生成 physics 函数体（无 export / module.exports）。"""
    c = constants or _load_constants()
    return f'''/**
 * 前端气动与滑跃几何预览 — 由 scripts/generate_frontend_physics.py 自动生成。
 * 请勿手改；修改物理请改 Python（utils/）后运行 python3 scripts/build_all.py。
 */
const SKI_JUMP_REF_RADIUS_M = {c['SKI_JUMP_REF_RADIUS_M']};
const FLAP_DEFLECTION_DEG = {c['FLAP_DEFLECTION_DEG']};
const FLAP_EFFICIENCY = {c['FLAP_EFFICIENCY']};
const WING_INCIDENCE_DEG = {c['WING_INCIDENCE_DEG']};
const PILOT_LOAD_KG = {c['PILOT_LOAD_KG']};
const A2A_MISSILE_COUNT = {c['A2A_MISSILE_COUNT']};
const PITCH_MAX_DEG = {c['PITCH_MAX_DEG']};

function computeSkiJumpArc(angleDeg, lipHeightM = null, arcLengthM = null) {{
  if (angleDeg <= 0) throw new Error('滑跃角必须为正');
  const angleRad = (angleDeg * Math.PI) / 180;
  let r;
  let h;
  if (arcLengthM != null && arcLengthM > 0) {{
    r = arcLengthM / angleRad;
    h = r * (1 - Math.cos(angleRad));
  }} else if (lipHeightM != null && lipHeightM > 0) {{
    h = lipHeightM;
    r = h / (1 - Math.cos(angleRad));
  }} else {{
    r = SKI_JUMP_REF_RADIUS_M;
    h = r * (1 - Math.cos(angleRad));
  }}
  return {{
    angle_deg: angleDeg,
    radius_m: r,
    arc_length_m: r * angleRad,
    horizontal_m: r * Math.sin(angleRad),
    lip_height_m: h,
  }};
}}

function resolveCarrierSkiJump(carrier) {{
  if (!carrier.ski_jump) return null;
  const angle = carrier.ski_jump_angle_deg || 0;
  let height = carrier.ski_jump_height_m;
  if (height == null || height === '') {{
    return computeSkiJumpArc(angle);
  }}
  height = Number(height);
  if (height > 0) {{
    return computeSkiJumpArc(angle, height, null);
  }}
  return computeSkiJumpArc(angle);
}}

function calcOswaldE(aspectRatio, sweepLeDeg) {{
  const sweepRad = (sweepLeDeg * Math.PI) / 180;
  return 4.61 * (1 - 0.045 * aspectRatio ** 0.68) * Math.cos(sweepRad) ** 0.15 - 3.1;
}}

function calcClAlpha(aspectRatio, oswaldE, sweepLeDeg) {{
  const sweepRad = (sweepLeDeg * Math.PI) / 180;
  const denom =
    2 + Math.sqrt(4 + ((aspectRatio ** 2) / oswaldE ** 2) * (1 + Math.tan(sweepRad) ** 2));
  return (2 * Math.PI * aspectRatio) / denom;
}}

function calcClFromAlphaDeg(alphaDeg, clAlpha) {{
  return ((alphaDeg * Math.PI) / 180) * clAlpha;
}}

function taxiAlphaDeg() {{
  return FLAP_DEFLECTION_DEG * FLAP_EFFICIENCY + WING_INCIDENCE_DEG;
}}

function computeAircraftAero(ac) {{
  const ar = (ac.wingspan_m ** 2) / ac.wing_area_m2;
  const eta = calcOswaldE(ar, ac.sweep_le_deg);
  const clAlpha = calcClAlpha(ar, eta, ac.sweep_le_deg);
  const alphaTaxi = taxiAlphaDeg();
  return {{
    aspect_ratio: ar,
    oswald_e: eta,
    cl_alpha_per_rad: clAlpha,
    taxi_alpha_deg: alphaTaxi,
    cl_taxi: calcClFromAlphaDeg(alphaTaxi, clAlpha),
    cl_20deg: calcClFromAlphaDeg(PITCH_MAX_DEG, clAlpha),
    cd0: ac.cd0,
  }};
}}

function a2aMassKg(ac) {{
  return (
    ac.empty_kg +
    ac.internal_fuel_kg +
    A2A_MISSILE_COUNT * ac.missile_mass_kg +
    PILOT_LOAD_KG
  );
}}

function maxPayloadKg(ac) {{
  return Number(ac.max_payload_kg);
}}

function filterCarriersForMode(mode, carriers) {{
  if (mode === 'ski_jump') return carriers.filter((c) => c.ski_jump);
  if (mode === 'short_takeoff' || mode === 'tiltrotor_short_takeoff') {{
    return carriers.filter((c) => c.f35b_capable && !c.ski_jump);
  }}
  if (mode === 'short_ski_jump') return carriers.filter((c) => c.f35b_capable && c.ski_jump);
  return [];
}}

function filterAircraftForMode(mode, aircraft) {{
  if (mode === 'ski_jump') return aircraft.filter((a) => a.type_label === 'conventional');
  if (mode === 'short_takeoff' || mode === 'short_ski_jump') {{
    return aircraft.filter((a) => a.type_label === 'v/stol');
  }}
  if (mode === 'tiltrotor_short_takeoff') {{
    return aircraft.filter((a) => a.type_label === 'tiltrotor');
  }}
  return [];
}}

function fmtNum(v, digits = 1) {{
  if (v == null || v === '' || Number.isNaN(v)) return '—';
  return Number(v).toLocaleString('zh-CN', {{
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }});
}}

function fmtInt(v) {{
  if (v == null || v === '') return '—';
  return Math.round(Number(v)).toLocaleString('zh-CN');
}}

function modeNeedsSkiJump(mode) {{
  return mode === 'ski_jump' || mode === 'short_ski_jump';
}}

function modeHasTrajectory(mode) {{
  return mode === 'ski_jump' || mode === 'short_ski_jump';
}}

/** 默认甲板风 = 航母最大航速 (kt) */
function defaultDeckWindKt(carrier) {{
  if (!carrier || carrier.max_speed_kt == null || carrier.max_speed_kt === '') return null;
  return Number(carrier.max_speed_kt);
}}
'''


def render_esm(constants: dict | None = None) -> str:
    """生成 Web 用 ESM physics.js 全文。"""
    body = render_physics_body(constants)
    names = ',\n  '.join(_EXPORT_NAMES)
    return body + f'\nexport {{\n  {names},\n}};\n'


def render_cjs(constants: dict | None = None) -> str:
    """生成小程序用 CommonJS physics.js 全文。"""
    body = render_physics_body(constants)
    lines = ',\n  '.join(_EXPORT_NAMES)
    return body + f'\nmodule.exports = {{\n  {lines},\n}};\n'


def write_physics_files(constants: dict | None = None) -> tuple[Path, Path]:
    """写入 docs 与 miniprogram 两份 physics.js。"""
    c = constants or _load_constants()
    DOCS_PHYSICS.parent.mkdir(parents=True, exist_ok=True)
    MINI_PHYSICS.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PHYSICS.write_text(render_esm(c), encoding='utf-8')
    MINI_PHYSICS.write_text(render_cjs(c), encoding='utf-8')
    return DOCS_PHYSICS, MINI_PHYSICS


def main() -> None:
    docs_path, mini_path = write_physics_files()
    print(f'Wrote {docs_path}')
    print(f'Wrote {mini_path}')


if __name__ == '__main__':
    main()
