"""F-35B 短距起飞仿真（平直甲板，策略 A/B/C 喷口偏转对比）。

策略说明
--------
策略 A — 延迟偏转喷口
    滑跑初期主喷口保持水平（0°），仅升力风扇提供垂直推力；当地速达到
    转换阈值 v_trans 后，以 NOZZLE_RATE_DEG_S 的速率偏转至目标角 nozzle_deg。
    搜索变量：目标喷口角、转换地速。

策略 B — 全程固定喷口
    自滑跑起点起主喷口即固定在某一角度，不再变化。
    搜索变量：固定喷口角。

策略 C — 尾流安全约束下的最优偏转
    给定 MIN_SAFE_DISTANCE_M（负值，如 −60），要求滑跑全程
    min(x − 安全距离) ≥ MIN_SAFE_DISTANCE_M，即尾流后缘不得侵入该 x 以左区域。
    利用 calc_exhaust_safe_distance_m 的反函数，在 x=0 处倒推起始喷口角；
    此后每个时间步根据当前 x 计算最小允许喷口角，并在「保持」与
    「减小 dt×NOZZLE_RATE_DEG_S」之间做动态规划，求最短离地距离。
    搜索变量：MIN_SAFE_DISTANCE_M（用户设定）。
"""
import numpy as np

# ---------------------------------------------------------------------------
# 大气与温度（推力在 T_THRUST_REF_C 海平面标定）
# ---------------------------------------------------------------------------
AMBIENT_TEMP_C = 15.0           # 环境温度，°C
T_THRUST_REF_C = 15.0           # 推力标定参考温度（ISA 海平面），°C
RHO_ISA_KG_M3 = 1.225           # ISA 海平面标准密度，kg/m³
THRUST_TEMP_EXPONENT = 0.85     # 涡扇海平面静态推力温度修正指数（含 FADEC 部分补偿）


def calc_sea_level_density_kg_m3(ambient_temp_c, reference_temp_c=T_THRUST_REF_C):
    """海平面空气密度，kg/m³；同压强下 ρ ∝ 1/T。"""
    t_ref_k = reference_temp_c + 273.15
    t_amb_k = ambient_temp_c + 273.15
    return RHO_ISA_KG_M3 * t_ref_k / t_amb_k


def calc_thrust_temp_factor(ambient_temp_c, reference_temp_c=T_THRUST_REF_C,
                            exponent=THRUST_TEMP_EXPONENT):
    """
    相对 reference_temp_c 标定推力的温度衰减系数。

    主喷管、升力风扇、滚转喷管假设相同衰减比例。
    """
    t_ref_k = reference_temp_c + 273.15
    t_amb_k = ambient_temp_c + 273.15
    return (t_ref_k / t_amb_k) ** exponent


RHO = calc_sea_level_density_kg_m3(AMBIENT_TEMP_C)
THRUST_TEMP_FACTOR = calc_thrust_temp_factor(AMBIENT_TEMP_C)

# ---------------------------------------------------------------------------
# 物理常数
# ---------------------------------------------------------------------------
G = 9.81                        # 重力加速度，m/s²
KT_TO_MPS = 0.514444            # 节 → m/s
M_TO_FT = 3.28084               # m → ft
MPS_TO_KT = 1.94384             # m/s → kt

# ---------------------------------------------------------------------------
# 飞机与推力参数（F-35B）
# ---------------------------------------------------------------------------
MASS_KG = 21620                 # 满内油 + 4 枚中距弹，kg
WEIGHT_N = MASS_KG * G          # 重力，N
S_REF_M2 = 42.7                 # 机翼参考面积，m²
WINGSPAN_M = 10.7               # 翼展，m
WING_HEIGHT_M = 1.96            # 机翼平均离地高度，m
ASPECT_RATIO = WINGSPAN_M ** 2 / S_REF_M2  # 展弦比 AR = b²/S

NOZZLE_RATE_DEG_S = 95 / 2.5    # 3BSM 主喷管偏转速率，°/s（95° 需 2.5 s）
T_MAIN_STOVL_SL_N = 83260       # STOVL 模式主喷管推力（T_THRUST_REF_C 标定），N
ROLLPOST_EFFICIENCY = 0.9       # 滚转喷管效率（关闭时功率回收给主喷管）
T_LIFTFAN_SL_N = 83260          # 升力风扇推力（T_THRUST_REF_C 标定），N
T_ROLLPOSTS_SL_N = 14600        # 滚转喷管总推力（T_THRUST_REF_C 标定），N
T_MAIN_STOVL_N = T_MAIN_STOVL_SL_N * THRUST_TEMP_FACTOR
T_LIFTFAN_N = T_LIFTFAN_SL_N * THRUST_TEMP_FACTOR
T_ROLLPOSTS_N = T_ROLLPOSTS_SL_N * THRUST_TEMP_FACTOR
T_MAIN_GROUND_N = T_MAIN_STOVL_N + T_ROLLPOSTS_N / ROLLPOST_EFFICIENCY  # 地面主喷管等效推力
CD0 = 0.039                     # 零升阻力系数（襟翼放下、起落架未收）
MU = 0.02                       # 甲板滚动摩擦系数

SWEEP_LE_DEG = 35  # F-35B 35°，歼-35 38°，歼-15 42°
FLAP_DEFLECTION_DEG = 20
FLAP_EFFICIENCY = 0.5
WING_INCIDENCE_DEG = 2
ROTATION_AOA_DEG = 12.5         # F-35B 起飞拉杆攻角，°

# ---------------------------------------------------------------------------
# 主喷口尾流参数（F-35B；随机型调整）
# ---------------------------------------------------------------------------
EXHAUST_MDOT_KG_S = 147.0       # 排气流量 ṁ，kg/s
EXHAUST_U0_MPS = 666.0          # 喷口排气速度 U₀，m/s
EXHAUST_D0_M = 1.04             # 喷口直径 D₀，m
EXHAUST_HEIGHT_M = 1.74         # 喷口离地高度 h，m
EXHAUST_USAFE_MPS = 25.0        # 安全速度阈值，m/s
EXHAUST_WALL_ETA = 0.70         # 壁面射流转向动量保留率 η
EXHAUST_WALL_CW = 6.0           # 壁面射流衰减常数 C_w
HORIZONTAL_JET_THETA_DEG = 5.0  # 低于此 θ 按水平自由射流处理

WIND_KT = 22
V_WIND_MPS = WIND_KT * KT_TO_MPS  # 甲板逆风，m/s

# 策略 C：尾流约束（必须为负，表示该 x 以左的甲板须全程安全）
MIN_SAFE_DISTANCE_M = -60.0

# 全项目俯仰角硬上限（°）；舰基起飞操纵/结构限制，搜索与仿真均不得超过
PITCH_MAX_DEG = 20


def check_pitch_deg(pitch_deg):
    """校验俯仰角不超过 PITCH_MAX_DEG；超限则抛出 ValueError。"""
    if pitch_deg > PITCH_MAX_DEG:
        raise ValueError(f"俯仰角 {pitch_deg}° 超过硬上限 {PITCH_MAX_DEG}°")
    return pitch_deg

# 搜索范围
NOZZLE_FINAL_DEG_START = 20
NOZZLE_FINAL_DEG_END = 90
NOZZLE_FINAL_DEG_STEP = 5
NOZZLE_FINE_RADIUS_DEG = 10
NOZZLE_FINE_STEP_DEG = 1
V_TRANS_START_MPS = 0
V_TRANS_END_MPS = 45
V_TRANS_STEP_MPS = 5
V_TRANS_FINE_RADIUS_MPS = 10
V_TRANS_FINE_STEP_MPS = 1

DT_DEFAULT = 0.01
MAX_SIM_TIME_S = 60.0
MAX_RUNWAY_M = 3000.0

def calc_exhaust_safe_distance_m(theta_deg, u_wind_mps):
    """
    尾流衰减至安全阈值所需的水平向后距离，m（两段模型：自由射流 + 撞地壁面射流）。

    θ：喷流中心线与水平面夹角（自水平量起，向后下方为正），°
    u_wind_mps：甲板风，与尾流同向分量（顶风放飞时为正），m/s
    """
    a0 = np.pi / 4 * EXHAUST_D0_M ** 2
    rho0 = EXHAUST_MDOT_KG_S / (a0 * EXHAUST_U0_MPS)
    k = 6.2 * np.sqrt(rho0 / RHO) * EXHAUST_D0_M

    d_u0 = max(EXHAUST_U0_MPS - u_wind_mps, 0.0)
    if u_wind_mps >= EXHAUST_USAFE_MPS:
        return np.inf

    target_plume = EXHAUST_USAFE_MPS - u_wind_mps
    if target_plume >= d_u0:
        return 0.0

    x_baseline = k * d_u0 / target_plume
    if theta_deg < HORIZONTAL_JET_THETA_DEG:
        return x_baseline

    theta_rad = np.radians(min(theta_deg, 89.9))
    l_impinge = EXHAUST_HEIGHT_M / np.sin(theta_rad)
    horiz_offset = EXHAUST_HEIGHT_M / np.tan(theta_rad)

    d_ui = min(d_u0, d_u0 * k / max(l_impinge, 0.01))
    f_wall = EXHAUST_WALL_ETA * EXHAUST_MDOT_KG_S * d_u0 * np.cos(theta_rad)
    wall_coeff = EXHAUST_WALL_CW * np.sqrt(max(f_wall, 0.0) / RHO)

    r_safe = 0.0
    if target_plume < d_ui:
        r_safe = max(0.0, wall_coeff / target_plume - EXHAUST_D0_M)

    return horiz_offset + r_safe


def calc_exhaust_theta_deg_for_safe_distance_m(max_safe_m, u_wind_mps):
    """
    calc_exhaust_safe_distance_m 的反函数：给定允许的最大安全距离，求最小喷流角 θ（°）。

    即满足 safe(θ) ≤ max_safe_m 的最小 θ。
    """
    if u_wind_mps >= EXHAUST_USAFE_MPS or max_safe_m <= 0:
        return 89.9

    d_u0 = max(EXHAUST_U0_MPS - u_wind_mps, 0.0)
    target_plume = EXHAUST_USAFE_MPS - u_wind_mps
    if target_plume >= d_u0:
        return HORIZONTAL_JET_THETA_DEG

    a0 = np.pi / 4 * EXHAUST_D0_M ** 2
    rho0 = EXHAUST_MDOT_KG_S / (a0 * EXHAUST_U0_MPS)
    k = 6.2 * np.sqrt(rho0 / RHO) * EXHAUST_D0_M
    x_baseline = k * d_u0 / target_plume

    if max_safe_m >= x_baseline:
        return HORIZONTAL_JET_THETA_DEG

    lo, hi = HORIZONTAL_JET_THETA_DEG, 89.9
    while hi - lo > 0.05:
        mid = (lo + hi) / 2.0
        if calc_exhaust_safe_distance_m(mid, u_wind_mps) > max_safe_m:
            lo = mid
        else:
            hi = mid
    return hi


def calc_min_nozzle_deg_for_plume(x_m, min_safe_distance_m, u_wind_mps, ski_jump_offset_deg=0.0):
    """位置 x 处满足尾流约束 x − safe(θ) ≥ min_safe_distance 的最小喷口偏转角（°）。"""
    max_safe_m = x_m - min_safe_distance_m
    theta_total = calc_exhaust_theta_deg_for_safe_distance_m(max_safe_m, u_wind_mps)
    return max(0.0, theta_total - ski_jump_offset_deg)


def update_min_plume_trailing_edge_m(x_m, theta_deg, u_wind_mps, current_min_m):
    """
    更新甲板上受影响最后缘位置，m：滑跑全程 min(x − 安全距离)。

    即尾流后缘在甲板上到达的最靠后（x 最小）位置。
    """
    safe_m = calc_exhaust_safe_distance_m(theta_deg, u_wind_mps)
    if np.isinf(safe_m):
        return current_min_m
    edge_m = x_m - safe_m
    if current_min_m is None:
        return edge_m
    return min(current_min_m, edge_m)

# ---------------------------------------------------------------------------
# 气动参数（计算值）
# ---------------------------------------------------------------------------
def calc_oswald_e(aspect_ratio, sweep_le_deg):
    """η = 4.61(1 - 0.045·AR^0.68)(cos Λ)^0.15 - 3.1"""
    sweep_rad = np.radians(sweep_le_deg)
    return 4.61 * (1 - 0.045 * aspect_ratio ** 0.68) * (np.cos(sweep_rad) ** 0.15) - 3.1


def calc_cl_alpha(aspect_ratio, oswald_e, sweep_le_deg):
    """C_Lα = 2π·AR / (2 + √(4 + (AR²/η²)(1 + tan²Λ)))，单位 /rad"""
    sweep_rad = np.radians(sweep_le_deg)
    denom = 2 + np.sqrt(4 + (aspect_ratio ** 2 / oswald_e ** 2) * (1 + np.tan(sweep_rad) ** 2))
    return 2 * np.pi * aspect_ratio / denom


def calc_cl_from_alpha_deg(alpha_deg, cl_alpha):
    return np.radians(alpha_deg) * cl_alpha


def calc_ground_effect_phi(wing_height_m, wingspan_m):
    """Torenbeek 地面效应修正因子 φ。"""
    x = 16 * wing_height_m / wingspan_m
    return x * x / (1 + x * x)


TAXI_ALPHA_DEG = FLAP_DEFLECTION_DEG * FLAP_EFFICIENCY + WING_INCIDENCE_DEG  # 滑行等效迎角，°


def recompute_aero_parameters():
    """根据当前 MASS_KG / 几何参数刷新气动派生量。"""
    global ASPECT_RATIO, WEIGHT_N, OSWALD_E, K_IND, CL_ALPHA, PHI_GROUND, CL_TAXI, CL_ROTATION
    ASPECT_RATIO = WINGSPAN_M ** 2 / S_REF_M2
    WEIGHT_N = MASS_KG * G
    OSWALD_E = calc_oswald_e(ASPECT_RATIO, SWEEP_LE_DEG)
    K_IND = 1 / (np.pi * ASPECT_RATIO * OSWALD_E)
    CL_ALPHA = calc_cl_alpha(ASPECT_RATIO, OSWALD_E, SWEEP_LE_DEG)
    PHI_GROUND = calc_ground_effect_phi(WING_HEIGHT_M, WINGSPAN_M)
    CL_TAXI = calc_cl_from_alpha_deg(TAXI_ALPHA_DEG, CL_ALPHA)
    CL_ROTATION = calc_cl_from_alpha_deg(TAXI_ALPHA_DEG + ROTATION_AOA_DEG, CL_ALPHA)


def apply_thrust_temperature(ambient_temp_c):
    global AMBIENT_TEMP_C, RHO, THRUST_TEMP_FACTOR
    global T_MAIN_STOVL_N, T_LIFTFAN_N, T_ROLLPOSTS_N, T_MAIN_GROUND_N
    AMBIENT_TEMP_C = ambient_temp_c
    RHO = calc_sea_level_density_kg_m3(ambient_temp_c)
    THRUST_TEMP_FACTOR = calc_thrust_temp_factor(ambient_temp_c)
    T_MAIN_STOVL_N = T_MAIN_STOVL_SL_N * THRUST_TEMP_FACTOR
    T_LIFTFAN_N = T_LIFTFAN_SL_N * THRUST_TEMP_FACTOR
    T_ROLLPOSTS_N = T_ROLLPOSTS_SL_N * THRUST_TEMP_FACTOR
    T_MAIN_GROUND_N = T_MAIN_STOVL_N + T_ROLLPOSTS_N / ROLLPOST_EFFICIENCY


def apply_wind_knots(wind_kt):
    global WIND_KT, V_WIND_MPS
    WIND_KT = wind_kt
    V_WIND_MPS = wind_kt * KT_TO_MPS


def apply_stovl_thrust_sl(t_main_sl_n, t_liftfan_sl_n, t_rollposts_sl_n):
    global T_MAIN_STOVL_SL_N, T_LIFTFAN_SL_N, T_ROLLPOSTS_SL_N
    T_MAIN_STOVL_SL_N = t_main_sl_n
    T_LIFTFAN_SL_N = t_liftfan_sl_n
    T_ROLLPOSTS_SL_N = t_rollposts_sl_n
    apply_thrust_temperature(AMBIENT_TEMP_C)


def apply_aircraft_geometry(mass_kg, s_ref_m2, wingspan_m, wing_height_m, sweep_le_deg):
    global MASS_KG, S_REF_M2, WINGSPAN_M, WING_HEIGHT_M, SWEEP_LE_DEG
    MASS_KG = mass_kg
    S_REF_M2 = s_ref_m2
    WINGSPAN_M = wingspan_m
    WING_HEIGHT_M = wing_height_m
    SWEEP_LE_DEG = sweep_le_deg
    recompute_aero_parameters()


recompute_aero_parameters()


def print_config_summary():
    print(f"环境温度:     {AMBIENT_TEMP_C:.0f} °C (推力标定 {T_THRUST_REF_C:.0f} °C)")
    print(f"空气密度 ρ:   {RHO:.4f} kg/m³ | 推力温度系数 {THRUST_TEMP_FACTOR:.4f}")
    print(f"实际推力({AMBIENT_TEMP_C:.0f}°C SL): 主喷管 {T_MAIN_STOVL_N/1000:.1f} kN，"
          f"升力风扇 {T_LIFTFAN_N/1000:.1f} kN，滚转 {T_ROLLPOSTS_N/1000:.1f} kN"
          f"（{T_THRUST_REF_C:.0f}°C 标定 {T_MAIN_STOVL_SL_N/1000:.1f}/"
          f"{T_LIFTFAN_SL_N/1000:.1f}/{T_ROLLPOSTS_SL_N/1000:.1f} kN）")
    print(f"起飞重量:     {MASS_KG:,} kg")
    print(f"展弦比 AR:    {ASPECT_RATIO:.3f}")
    print(f"甲板风:       {WIND_KT} kt ({V_WIND_MPS:.2f} m/s)")
    print(f"地面效应 φ:   {PHI_GROUND:.3f}")
    print(f"Oswald η:     {OSWALD_E:.4f}")
    print(f"诱导因子 k:   {K_IND:.3f}")
    print(f"C_Lα:         {CL_ALPHA:.4f} /rad  (Λ={SWEEP_LE_DEG}°)")
    print(f"Cl_taxi:      {CL_TAXI:.4f}")
    print(f"Cl_rotation:  {CL_ROTATION:.4f}")


def dynamic_pressure(airspeed_mps):
    """动压 q = ½·ρ·V²，Pa"""
    return 0.5 * RHO * airspeed_mps * airspeed_mps


def find_liftoff_index(normal_force):
    """正压力由正变负时的索引（离地瞬间）。"""
    idx = np.where(np.diff(np.sign(normal_force)) < 0)[0]
    return int(idx[0]) if len(idx) else None


def simulate_strategy_a(v_trans_mps, nozzle_final_deg, dt=DT_DEFAULT):
    """策略 A：先水平加速，达阈值后再偏转喷口。"""
    trans_duration_s = nozzle_final_deg / NOZZLE_RATE_DEG_S
    nozzle_final_rad = np.radians(nozzle_final_deg)
    v_gs, x, t = 0.0, 0.0, 0.0
    airborne = False
    transitioned = in_trans = False
    trans_start_t = 0.0
    min_plume_trailing_edge_m = None
    history = {k: [] for k in ('t', 'x', 'v_gs', 'v_air', 'normal', 'a', 't_h', 't_v')}

    while t < MAX_SIM_TIME_S and x < MAX_RUNWAY_M:
        v_air = v_gs + V_WIND_MPS

        if not airborne and not transitioned and v_gs >= v_trans_mps and not in_trans:
            in_trans, trans_start_t = True, t

        if in_trans:
            elapsed = t - trans_start_t
            ratio = min(elapsed / trans_duration_s, 1.0) if trans_duration_s > 0 else 1.0
            if ratio >= 1.0:
                in_trans, transitioned = False, True
            nozzle_rad = nozzle_final_rad * ratio
            t_h = T_MAIN_GROUND_N * np.cos(nozzle_rad)
            t_v = T_MAIN_GROUND_N * np.sin(nozzle_rad) + T_LIFTFAN_N
        elif transitioned:
            nozzle_rad = nozzle_final_rad
            t_h = T_MAIN_GROUND_N * np.cos(nozzle_final_rad)
            t_v = T_MAIN_STOVL_N * np.sin(nozzle_final_rad) + T_LIFTFAN_N
        else:
            nozzle_rad = 0.0
            t_h = T_MAIN_GROUND_N
            t_v = T_LIFTFAN_N

        if airborne:
            nozzle_rad = nozzle_final_rad if transitioned else 0.0
            t_h, t_v = T_MAIN_STOVL_N, T_LIFTFAN_N + T_ROLLPOSTS_N

        q = dynamic_pressure(v_air)
        lift = q * S_REF_M2 * CL_TAXI + t_v        # 总升力 = 机翼升力 + 垂直推力
        drag = q * S_REF_M2 * (CD0 + K_IND * CL_TAXI ** 2 * PHI_GROUND)  # 含地面效应的阻力
        normal = WEIGHT_N - lift                   # 地面正压力 N = W - L_total
        # 拉杆后潜在升力（含滚转喷管）足以克服重力 → 判定离地
        lift_potential = q * S_REF_M2 * CL_ROTATION + t_v + T_ROLLPOSTS_N
        if WEIGHT_N - lift_potential < 0:
            normal = 0.0
            airborne = True

        friction = MU * normal if not airborne else 0.0  # 地面摩擦力 μ·N
        accel = (t_h - drag - friction) / MASS_KG   # 水平加速度 a = (T_h - D - F) / m

        history['t'].append(t)
        history['x'].append(x)
        history['v_gs'].append(v_gs)
        history['v_air'].append(v_air)
        history['normal'].append(normal)
        history['a'].append(accel)
        history['t_h'].append(t_h)
        history['t_v'].append(t_v)

        v_gs = max(v_gs + accel * dt, 0.0)
        x += v_gs * dt
        t += dt

        if not airborne:
            min_plume_trailing_edge_m = update_min_plume_trailing_edge_m(
                x, np.degrees(nozzle_rad), V_WIND_MPS, min_plume_trailing_edge_m)

    for key in history:
        history[key] = np.array(history[key])
    return history, airborne, min_plume_trailing_edge_m if min_plume_trailing_edge_m is not None else 0.0


def simulate_strategy_b(nozzle_fixed_deg, dt=DT_DEFAULT):
    """策略 B：全程固定喷口偏转角。"""
    nozzle_rad = np.radians(nozzle_fixed_deg)
    v_gs, x, t = 0.0, 0.0, 0.0
    airborne = False
    min_plume_trailing_edge_m = None
    history = {k: [] for k in ('t', 'x', 'v_gs', 'v_air', 'normal', 'a', 't_h', 't_v')}

    while t < MAX_SIM_TIME_S and x < MAX_RUNWAY_M:
        v_air = v_gs + V_WIND_MPS
        t_h = T_MAIN_GROUND_N * np.cos(nozzle_rad)
        t_v = T_MAIN_GROUND_N * np.sin(nozzle_rad) + T_LIFTFAN_N
        q = dynamic_pressure(v_air)
        lift = q * S_REF_M2 * CL_TAXI + t_v
        drag = q * S_REF_M2 * (CD0 + K_IND * CL_TAXI ** 2 * PHI_GROUND)
        normal = WEIGHT_N - lift
        lift_potential = q * S_REF_M2 * CL_ROTATION + t_v + T_ROLLPOSTS_N
        if WEIGHT_N - lift_potential < 0:
            normal = 0.0
            airborne = True

        friction = MU * normal if not airborne else 0.0
        accel = (t_h - drag - friction) / MASS_KG

        history['t'].append(t)
        history['x'].append(x)
        history['v_gs'].append(v_gs)
        history['v_air'].append(v_air)
        history['normal'].append(normal)
        history['a'].append(accel)
        history['t_h'].append(t_h)
        history['t_v'].append(t_v)

        v_gs = max(v_gs + accel * dt, 0.0)
        x += v_gs * dt
        t += dt

        if not airborne:
            min_plume_trailing_edge_m = update_min_plume_trailing_edge_m(
                x, nozzle_fixed_deg, V_WIND_MPS, min_plume_trailing_edge_m)

    for key in history:
        history[key] = np.array(history[key])
    return history, airborne, min_plume_trailing_edge_m if min_plume_trailing_edge_m is not None else 0.0


def _ground_forces_flat(v_gs, nozzle_deg):
    """平直甲板单步前力与离地判定（策略 C 共用）。"""
    v_air = v_gs + V_WIND_MPS
    nozzle_rad = np.radians(nozzle_deg)
    t_h = T_MAIN_GROUND_N * np.cos(nozzle_rad)
    t_v = T_MAIN_GROUND_N * np.sin(nozzle_rad) + T_LIFTFAN_N
    q = dynamic_pressure(v_air)
    lift = q * S_REF_M2 * CL_TAXI + t_v
    drag = q * S_REF_M2 * (CD0 + K_IND * CL_TAXI ** 2 * PHI_GROUND)
    normal = WEIGHT_N - lift
    lift_potential = q * S_REF_M2 * CL_ROTATION + t_v + T_ROLLPOSTS_N
    airborne = WEIGHT_N - lift_potential < 0
    if airborne:
        normal = 0.0
    friction = MU * normal if not airborne else 0.0
    accel = (t_h - drag - friction) / MASS_KG
    return accel, airborne


def simulate_strategy_c(min_safe_distance_m, dt=DT_DEFAULT):
    """
    策略 C：全程满足 min(x − 安全距离) ≥ min_safe_distance_m；
    每步可选减小喷口或保持，DP 求最短离地距离。
    """
    if min_safe_distance_m >= 0:
        raise ValueError("min_safe_distance_m 必须为负值")

    rate_step = NOZZLE_RATE_DEG_S * dt
    init_nozzle = calc_min_nozzle_deg_for_plume(0.0, min_safe_distance_m, V_WIND_MPS)
    states = {round(init_nozzle, 2): (0.0, 0.0, 0.0)}
    best = None
    min_plume_trailing_edge_m = None

    for _ in range(int(MAX_SIM_TIME_S / dt)):
        if not states:
            break
        new_states = {}
        for nozzle_deg, (v_gs, x, t) in states.items():
            if x >= MAX_RUNWAY_M:
                continue

            nozzle_min = calc_min_nozzle_deg_for_plume(x, min_safe_distance_m, V_WIND_MPS)
            nozzle_deg = max(nozzle_deg, nozzle_min)

            _, airborne_now = _ground_forces_flat(v_gs, nozzle_deg)
            if airborne_now:
                candidate = dict(
                    x_m=x, v_gs_mps=v_gs, v_air_mps=v_gs + V_WIND_MPS, t_s=t,
                    nozzle_deg=nozzle_deg,
                    min_plume_trailing_edge_m=min_plume_trailing_edge_m if min_plume_trailing_edge_m is not None else 0.0,
                )
                if best is None or x < best['x_m']:
                    best = candidate
                continue

            for decrease in (False, True):
                n2 = nozzle_deg - rate_step if decrease else nozzle_deg
                if decrease and n2 < nozzle_min - 1e-9:
                    continue
                n2 = max(n2, nozzle_min)

                accel, airborne = _ground_forces_flat(v_gs, n2)
                v2 = max(v_gs + accel * dt, 0.0)
                x2 = x + v2 * dt
                t2 = t + dt

                if not airborne:
                    min_plume_trailing_edge_m = update_min_plume_trailing_edge_m(
                        x2, n2, V_WIND_MPS, min_plume_trailing_edge_m)

                if airborne:
                    candidate = dict(
                        x_m=x2, v_gs_mps=v2, v_air_mps=v2 + V_WIND_MPS, t_s=t2,
                        nozzle_deg=n2,
                        min_plume_trailing_edge_m=min_plume_trailing_edge_m if min_plume_trailing_edge_m is not None else 0.0,
                    )
                    if best is None or x2 < best['x_m']:
                        best = candidate
                else:
                    key = round(n2, 2)
                    if key not in new_states or v2 > new_states[key][0]:
                        new_states[key] = (v2, x2, t2)
        states = new_states

    return best


def evaluate_liftoff(history, min_plume_trailing_edge_m):
    """从仿真历史提取离地指标，无法离地则返回 None。"""
    idx = find_liftoff_index(history['normal'])
    if idx is None:
        return None
    return dict(
        x_m=history['x'][idx],
        v_gs_mps=history['v_gs'][idx],
        v_air_mps=history['v_air'][idx],
        t_s=history['t'][idx],
        min_plume_trailing_edge_m=min_plume_trailing_edge_m,
        idx=idx,
        history=history,
    )


def search_strategy_a():
    best = None
    for nozzle_deg in range(NOZZLE_FINAL_DEG_START, NOZZLE_FINAL_DEG_END + 1, NOZZLE_FINAL_DEG_STEP):
        for v_trans in range(V_TRANS_START_MPS, V_TRANS_END_MPS + 1, V_TRANS_STEP_MPS):
            hist, _, max_plume_m = simulate_strategy_a(v_trans, nozzle_deg)
            lo = evaluate_liftoff(hist, max_plume_m)
            if lo and (best is None or lo['x_m'] < best['x_m']):
                best = dict(nozzle_deg=nozzle_deg, v_trans_mps=v_trans, **lo)
    return best


def fine_tune_strategy_a(coarse_best):
    best = coarse_best.copy()
    for nozzle_deg in range(coarse_best['nozzle_deg'] - NOZZLE_FINE_RADIUS_DEG,
                            coarse_best['nozzle_deg'] + NOZZLE_FINE_RADIUS_DEG + 1,
                            NOZZLE_FINE_STEP_DEG):
        for v_trans in range(coarse_best['v_trans_mps'] - V_TRANS_FINE_RADIUS_MPS,
                             coarse_best['v_trans_mps'] + V_TRANS_FINE_RADIUS_MPS + 1,
                             V_TRANS_FINE_STEP_MPS):
            hist, _, max_plume_m = simulate_strategy_a(v_trans, nozzle_deg)
            lo = evaluate_liftoff(hist, max_plume_m)
            if lo and lo['x_m'] < best['x_m']:
                best = dict(nozzle_deg=nozzle_deg, v_trans_mps=v_trans, **lo)
    return best


def search_strategy_b():
    best = None
    for nozzle_deg in range(25, 90):
        hist, _, max_plume_m = simulate_strategy_b(nozzle_deg)
        lo = evaluate_liftoff(hist, max_plume_m)
        if lo and (best is None or lo['x_m'] < best['x_m']):
            best = dict(nozzle_deg=nozzle_deg, **lo)
    return best


def run_strategy_a_search():
    """策略 A 粗搜索 + 细化，返回最优结果 dict 或 None。"""
    best = search_strategy_a()
    if best:
        best = fine_tune_strategy_a(best)
    return best


def _main():
    print_config_summary()

    print("\n" + "=" * 60)
    print(f"策略 A：起飞前偏转喷口（{WIND_KT} kt 甲板风）")
    print("=" * 60)

    best_a = search_strategy_a()
    if best_a:
        print(f"\n粗搜索最优:")
        print(f"  喷管最终角:   {best_a['nozzle_deg']}°")
        print(f"  开始偏转地速: {best_a['v_trans_mps']} m/s ({best_a['v_trans_mps'] * MPS_TO_KT:.0f} kt)")
        print(f"  离地距离:     {best_a['x_m']:.1f} m ({best_a['x_m'] * M_TO_FT:.0f} ft)")
        print(f"  离地地速:     {best_a['v_gs_mps']:.1f} m/s ({best_a['v_gs_mps'] * MPS_TO_KT:.0f} kt)")
        print(f"  离地空速:     {best_a['v_air_mps']:.1f} m/s ({best_a['v_air_mps'] * MPS_TO_KT:.0f} kt)")
        print(f"  离地时间:     {best_a['t_s']:.2f} s")
        print(f"  甲板受影响最后缘: {best_a['min_plume_trailing_edge_m']:.1f} m")

        print("\n细化搜索 …")
        best_a = fine_tune_strategy_a(best_a)
        print(f"\n★ 细化最优: 喷管角 {best_a['nozzle_deg']}°，转换地速 {best_a['v_trans_mps']} m/s "
              f"({best_a['v_trans_mps'] * MPS_TO_KT:.0f} kt)")
        print(f"  离地距离: {best_a['x_m']:.1f} m ({best_a['x_m'] * M_TO_FT:.0f} ft)")
        print(f"  离地总时间: {best_a['t_s']:.2f} s | 甲板受影响最后缘 {best_a['min_plume_trailing_edge_m']:.1f} m")

    print("\n" + "=" * 60)
    print(f"策略 B：全程固定喷口（{WIND_KT} kt 甲板风）")
    print("=" * 60)

    best_b = search_strategy_b()
    if best_a and best_b:
        diff_m = best_b['x_m'] - best_a['x_m']
        print(f"\n策略 B 最优: 固定 {best_b['nozzle_deg']}°，离地 {best_b['x_m']:.1f} m")
        print(f"  离地总时间 {best_b['t_s']:.2f} s | 甲板受影响最后缘 {best_b['min_plume_trailing_edge_m']:.1f} m")
        print(f"策略 A 最优: 转换地速 {best_a['v_trans_mps']} m/s，离地 {best_a['x_m']:.1f} m")
        print(f"  离地总时间 {best_a['t_s']:.2f} s | 甲板受影响最后缘 {best_a['min_plume_trailing_edge_m']:.1f} m")
        print(f"策略 A 比 B 短: {diff_m:.1f} m ({diff_m / best_b['x_m'] * 100:.1f}%)")

    print("\n" + "=" * 60)
    print(f"策略 C：尾流约束 min(x−安全距离) ≥ {MIN_SAFE_DISTANCE_M:.0f} m（{WIND_KT} kt 甲板风）")
    print("=" * 60)

    init_nozzle_c = calc_min_nozzle_deg_for_plume(0.0, MIN_SAFE_DISTANCE_M, V_WIND_MPS)
    print(f"起始喷管角（x=0 反推）: {init_nozzle_c:.1f}°")

    best_c = simulate_strategy_c(MIN_SAFE_DISTANCE_M)
    if best_c:
        print(f"\n★ 策略 C 最优: 离地 {best_c['x_m']:.1f} m ({best_c['x_m'] * M_TO_FT:.0f} ft)")
        print(f"  离地喷管角:   {best_c['nozzle_deg']:.1f}°")
        print(f"  离地地速:     {best_c['v_gs_mps']:.1f} m/s ({best_c['v_gs_mps'] * MPS_TO_KT:.0f} kt)")
        print(f"  离地空速:     {best_c['v_air_mps']:.1f} m/s ({best_c['v_air_mps'] * MPS_TO_KT:.0f} kt)")
        print(f"  离地总时间:   {best_c['t_s']:.2f} s")
        print(f"  甲板受影响最后缘: {best_c['min_plume_trailing_edge_m']:.1f} m")
        if best_a and best_b:
            print(f"  比策略 A 长: {best_c['x_m'] - best_a['x_m']:.1f} m | 比策略 B 长: {best_c['x_m'] - best_b['x_m']:.1f} m")
    else:
        print("\n策略 C 未能离地")


if __name__ == "__main__":
    _main()
