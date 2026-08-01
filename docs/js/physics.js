/** 与 takeoff_physics.py 一致的气动与滑跃几何计算（浏览器端即时显示用） */
const SKI_JUMP_REF_RADIUS_M = 200;
const FLAP_DEFLECTION_DEG = 20;
const FLAP_EFFICIENCY = 0.5;
const WING_INCIDENCE_DEG = 2;
const PILOT_LOAD_KG = 100;
const A2A_MISSILE_COUNT = 4;

export function computeSkiJumpArc(angleDeg, lipHeightM = null, arcLengthM = null) {
  if (angleDeg <= 0) throw new Error('滑跃角必须为正');
  const angleRad = (angleDeg * Math.PI) / 180;
  let r, h;
  if (arcLengthM != null && arcLengthM > 0) {
    r = arcLengthM / angleRad;
    h = r * (1 - Math.cos(angleRad));
  } else if (lipHeightM != null && lipHeightM > 0) {
    h = lipHeightM;
    r = h / (1 - Math.cos(angleRad));
  } else {
    r = SKI_JUMP_REF_RADIUS_M;
    h = r * (1 - Math.cos(angleRad));
  }
  return {
    angle_deg: angleDeg,
    radius_m: r,
    arc_length_m: r * angleRad,
    horizontal_m: r * Math.sin(angleRad),
    lip_height_m: h,
  };
}

export function resolveCarrierSkiJump(carrier) {
  if (!carrier.ski_jump) return null;
  const angle = carrier.ski_jump_angle_deg || 0;
  let height = carrier.ski_jump_height_m;
  if (height == null || height === '') {
    return computeSkiJumpArc(angle);
  }
  height = Number(height);
  if (height > 0) {
    return computeSkiJumpArc(angle, height, null);
  }
  return computeSkiJumpArc(angle);
}

export function calcOswaldE(aspectRatio, sweepLeDeg) {
  const sweepRad = (sweepLeDeg * Math.PI) / 180;
  return 4.61 * (1 - 0.045 * aspectRatio ** 0.68) * Math.cos(sweepRad) ** 0.15 - 3.1;
}

export function calcClAlpha(aspectRatio, oswaldE, sweepLeDeg) {
  const sweepRad = (sweepLeDeg * Math.PI) / 180;
  const denom =
    2 + Math.sqrt(4 + ((aspectRatio ** 2) / oswaldE ** 2) * (1 + Math.tan(sweepRad) ** 2));
  return (2 * Math.PI * aspectRatio) / denom;
}

export function calcClFromAlphaDeg(alphaDeg, clAlpha) {
  return ((alphaDeg * Math.PI) / 180) * clAlpha;
}

export function taxiAlphaDeg() {
  return FLAP_DEFLECTION_DEG * FLAP_EFFICIENCY + WING_INCIDENCE_DEG;
}

export function computeAircraftAero(ac) {
  const ar = (ac.wingspan_m ** 2) / ac.wing_area_m2;
  const eta = calcOswaldE(ar, ac.sweep_le_deg);
  const clAlpha = calcClAlpha(ar, eta, ac.sweep_le_deg);
  const alphaTaxi = taxiAlphaDeg();
  return {
    aspect_ratio: ar,
    oswald_e: eta,
    cl_alpha_per_rad: clAlpha,
    taxi_alpha_deg: alphaTaxi,
    cl_taxi: calcClFromAlphaDeg(alphaTaxi, clAlpha),
    cl_20deg: calcClFromAlphaDeg(20, clAlpha),
    cd0: ac.cd0,
  };
}

export function a2aMassKg(ac) {
  return (
    ac.empty_kg +
    ac.internal_fuel_kg +
    A2A_MISSILE_COUNT * ac.missile_mass_kg +
    PILOT_LOAD_KG
  );
}

export function maxPayloadKg(ac) {
  return ac.mtow_kg - ac.empty_kg - ac.internal_fuel_kg - PILOT_LOAD_KG;
}

export function filterCarriersForMode(mode, carriers) {
  if (mode === 'ski_jump') return carriers.filter((c) => c.ski_jump);
  if (mode === 'short_takeoff') return carriers.filter((c) => c.f35b_capable && !c.ski_jump);
  if (mode === 'short_ski_jump') return carriers.filter((c) => c.f35b_capable && c.ski_jump);
  return [];
}

export function filterAircraftForMode(mode, aircraft) {
  if (mode === 'ski_jump') return aircraft.filter((a) => a.type_label !== 'v/stol');
  if (mode === 'short_takeoff' || mode === 'short_ski_jump') {
    return aircraft.filter((a) => a.type_label === 'v/stol');
  }
  return [];
}

export function fmtNum(v, digits = 1) {
  if (v == null || v === '' || Number.isNaN(v)) return '—';
  return Number(v).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtInt(v) {
  if (v == null || v === '') return '—';
  return Math.round(Number(v)).toLocaleString('zh-CN');
}
