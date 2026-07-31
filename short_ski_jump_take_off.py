"""F-35B 短距滑跃起飞仿真（平直段 + 滑跃段，策略 A/B/C 喷口偏转对比）。

策略说明
--------
策略 A — 延迟偏转喷口
    平直段滑跑初期主喷口保持水平（0°）；当地速达到转换阈值 v_trans 后，
    以 NOZZLE_RATE_DEG_S 的速率偏转至目标角 nozzle_deg，随后经滑跃段离舰。
    搜索变量：平直段长度、目标喷口角、转换地速、俯仰角（及可选的离舰后喷口角）。

策略 B — 全程固定喷口
    自滑跑起点起主喷口即固定在某一角度，平直段与滑跃段均不变。
    搜索变量：平直段长度、固定喷口角、俯仰角（及可选的离舰后喷口角）。

策略 C — 尾流安全约束下的最优偏转
    给定 MIN_SAFE_DISTANCE_M（负值，如 −60），要求滑跑全程
    min(x − 安全距离) ≥ MIN_SAFE_DISTANCE_M，即尾流后缘不得侵入该 x 以左区域。
    利用 calc_exhaust_safe_distance_m 的反函数，在 x=0 处倒推起始喷口角；
    此后每个时间步根据当前 x 计算最小允许喷口角（滑跃段 θ 含滑跃角），
    并在「保持」与「减小 dt×NOZZLE_RATE_DEG_S」之间做动态规划，
    再经空中段判定，求最短起飞总距离（平直段 + 滑跃段水平投影）。
    搜索变量：MIN_SAFE_DISTANCE_M（用户设定）、平直段长度、俯仰角。

ALLOW_AIR_NOZZLE_VECTORING 为 True 时，策略 A/B 还可搜索离舰后主喷口继续偏转的角度。
"""
import numpy as np

# ---------------------------------------------------------------------------
# 仿真模式开关
# ---------------------------------------------------------------------------
ALLOW_AIR_NOZZLE_VECTORING = False
# True：离甲板后主喷口可继续偏转；此时 NOZZLE_AIR_DEG_LIST 参与参数搜索
# False：离甲板后喷口固定为滑跑结束角；NOZZLE_AIR_DEG_LIST 被忽略

# ---------------------------------------------------------------------------
# 大气与温度（推力在 T_THRUST_REF_C 海平面标定）
# ---------------------------------------------------------------------------
AMBIENT_TEMP_C = 30.0           # 环境温度，°C
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

# ---------------------------------------------------------------------------
# 飞机与推力参数（F-35B）
# ---------------------------------------------------------------------------
MASS_KG_MTOW = 27200            # 最大起飞重量 MTOW，kg
MASS_KG_A2A = 21620             # 满内油 + 4 枚中距弹，kg
MASS_KG = MASS_KG_A2A
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
T_MAIN_GROUND_N = T_MAIN_STOVL_N + T_ROLLPOSTS_N / ROLLPOST_EFFICIENCY

CD0 = 0.039                     # 零升阻力系数（襟翼放下、起落架未收）

SWEEP_LE_DEG = 35  # F-35B 35°，歼-35 38°，歼-15 42°
FLAP_DEFLECTION_DEG = 20
FLAP_EFFICIENCY = 0.5
WING_INCIDENCE_DEG = 2

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


# ---------------------------------------------------------------------------
# 航母甲板参数
# ---------------------------------------------------------------------------
SKI_JUMP_LENGTH_M = 37.0
SKI_JUMP_ANGLE_DEG = 12.5
SKI_JUMP_ANGLE_RAD = np.radians(SKI_JUMP_ANGLE_DEG)
SKI_JUMP_COS = np.cos(SKI_JUMP_ANGLE_RAD)
SKI_JUMP_SIN = np.sin(SKI_JUMP_ANGLE_RAD)
SKI_JUMP_HORIZONTAL_M = SKI_JUMP_LENGTH_M * SKI_JUMP_COS
MU = 0.03
WIND_KT = 25
V_WIND_MPS = WIND_KT * KT_TO_MPS

# 策略 C：尾流约束（必须为负，表示该 x 以左的甲板须全程安全）
MIN_SAFE_DISTANCE_M = -60.0

# 全项目俯仰角硬上限（°）；舰基起飞操纵/结构限制，搜索与仿真均不得超过
PITCH_MAX_DEG = 20


def check_pitch_deg(pitch_deg):
    """校验俯仰角不超过 PITCH_MAX_DEG；超限则抛出 ValueError。"""
    if pitch_deg > PITCH_MAX_DEG:
        raise ValueError(f"俯仰角 {pitch_deg}° 超过硬上限 {PITCH_MAX_DEG}°")
    return pitch_deg

# 策略 C 搜索范围
FLAT_LENGTH_M_LIST_C = range(50, 501, 10) if not ALLOW_AIR_NOZZLE_VECTORING else range(30, 501, 20)
PITCH_DEG_LIST_C = range(20, PITCH_MAX_DEG + 1, 1) if not ALLOW_AIR_NOZZLE_VECTORING else range(10, PITCH_MAX_DEG + 1, 2)

# ---------------------------------------------------------------------------
# 参数搜索范围（随 ALLOW_AIR_NOZZLE_VECTORING 切换，保持与原两文件一致）
# ---------------------------------------------------------------------------
if ALLOW_AIR_NOZZLE_VECTORING:
    NOZZLE_TAKEOFF_DEG_LIST_A = range(5, 71, 5)
    FLAT_LENGTH_M_LIST_A = range(30, 201, 20)
    V_TRANS_MPS_LIST_A = range(5, 76, 10)
    NOZZLE_TAKEOFF_DEG_LIST_B = range(5, 31, 5)
    FLAT_LENGTH_M_LIST_B = range(50, 501, 20)
    PITCH_DEG_LIST = range(10, PITCH_MAX_DEG + 1, 2)
    NOZZLE_AIR_DEG_LIST = range(0, 31, 5)  # 仅 ALLOW_AIR_NOZZLE_VECTORING=True 时参与搜索
else:
    NOZZLE_TAKEOFF_DEG_LIST_A = range(5, 86, 5)
    FLAT_LENGTH_M_LIST_A = range(10, 161, 10)
    V_TRANS_MPS_LIST_A = range(0, 41, 5)
    NOZZLE_TAKEOFF_DEG_LIST_B = range(0, 31, 10)
    FLAT_LENGTH_M_LIST_B = range(100, 501, 10)
    PITCH_DEG_LIST = range(20, PITCH_MAX_DEG + 1, 1)
    NOZZLE_AIR_DEG_LIST = range(0, 31, 5)  # 开关关闭时被忽略，保留定义便于切换模式

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


def calc_min_nozzle_deg_for_plume(x_m, min_safe_distance_m, u_wind_mps, on_ski_jump=False):
    """位置 x 处满足尾流约束的最小喷口偏转角（°）；滑跃段 θ 含滑跃角。"""
    max_safe_m = x_m - min_safe_distance_m
    theta_total = calc_exhaust_theta_deg_for_safe_distance_m(max_safe_m, u_wind_mps)
    offset = SKI_JUMP_ANGLE_DEG if on_ski_jump else 0.0
    return max(0.0, theta_total - offset)


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


def _plume_edge_or_zero(value):
    return value if value is not None else 0.0

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


TAXI_ALPHA_DEG = FLAP_DEFLECTION_DEG * FLAP_EFFICIENCY + WING_INCIDENCE_DEG


def recompute_aero_parameters():
    global ASPECT_RATIO, WEIGHT_N, OSWALD_E, K_IND, CL_ALPHA, PHI_GROUND_FLAT, CL_TAXI
    ASPECT_RATIO = WINGSPAN_M ** 2 / S_REF_M2
    WEIGHT_N = MASS_KG * G
    OSWALD_E = calc_oswald_e(ASPECT_RATIO, SWEEP_LE_DEG)
    K_IND = 1 / (np.pi * ASPECT_RATIO * OSWALD_E)
    CL_ALPHA = calc_cl_alpha(ASPECT_RATIO, OSWALD_E, SWEEP_LE_DEG)
    PHI_GROUND_FLAT = calc_ground_effect_phi(WING_HEIGHT_M, WINGSPAN_M)
    CL_TAXI = calc_cl_from_alpha_deg(TAXI_ALPHA_DEG, CL_ALPHA)


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


def apply_ski_jump_deck(length_m, angle_deg):
    global SKI_JUMP_LENGTH_M, SKI_JUMP_ANGLE_DEG, SKI_JUMP_ANGLE_RAD
    global SKI_JUMP_COS, SKI_JUMP_SIN, SKI_JUMP_HORIZONTAL_M
    SKI_JUMP_LENGTH_M = length_m
    SKI_JUMP_ANGLE_DEG = angle_deg
    SKI_JUMP_ANGLE_RAD = np.radians(angle_deg)
    SKI_JUMP_COS = np.cos(SKI_JUMP_ANGLE_RAD)
    SKI_JUMP_SIN = np.sin(SKI_JUMP_ANGLE_RAD)
    SKI_JUMP_HORIZONTAL_M = SKI_JUMP_LENGTH_M * SKI_JUMP_COS


recompute_aero_parameters()

DT_DEFAULT = 0.02
MAX_GROUND_TIME_S = 30.0
MAX_AIR_TIME_S = 3.0
ALPHA_LIMIT_RAD = np.radians(20)
CL_MIN, CL_MAX = 0.2, 1.8


def print_config_summary():
    mode = "离甲板后可偏转" if ALLOW_AIR_NOZZLE_VECTORING else "离甲板后固定"
    print(f"仿真模式:     {mode}")
    print(f"环境温度:     {AMBIENT_TEMP_C:.0f} °C (推力标定 {T_THRUST_REF_C:.0f} °C)")
    print(f"空气密度 ρ:   {RHO:.4f} kg/m³ | 推力温度系数 {THRUST_TEMP_FACTOR:.4f}")
    print(f"实际推力({AMBIENT_TEMP_C:.0f}°C SL): 主喷管 {T_MAIN_STOVL_N/1000:.1f} kN，"
          f"升力风扇 {T_LIFTFAN_N/1000:.1f} kN，滚转 {T_ROLLPOSTS_N/1000:.1f} kN"
          f"（{T_THRUST_REF_C:.0f}°C 标定 {T_MAIN_STOVL_SL_N/1000:.1f}/"
          f"{T_LIFTFAN_SL_N/1000:.1f}/{T_ROLLPOSTS_SL_N/1000:.1f} kN）")
    print(f"起飞重量:     {MASS_KG:,} kg")
    print(f"展弦比 AR:    {ASPECT_RATIO:.3f}")
    print(f"甲板风:       {WIND_KT} kt ({V_WIND_MPS:.2f} m/s)")
    print(f"地面效应 φ:   {PHI_GROUND_FLAT:.3f}")
    print(f"Oswald η:     {OSWALD_E:.4f}")
    print(f"诱导因子 k:   {K_IND:.3f}")
    print(f"C_Lα:         {CL_ALPHA:.4f} /rad  (Λ={SWEEP_LE_DEG}°)")
    print(f"Cl_taxi:      {CL_TAXI:.4f}")


def total_takeoff_distance_m(flat_length_m):
    return flat_length_m + SKI_JUMP_HORIZONTAL_M


def dynamic_pressure(airspeed_mps):
    """动压 q = ½·ρ·V²，Pa"""
    return 0.5 * RHO * airspeed_mps * airspeed_mps


def drag_coefficient(cl, phi_ground):
    """阻力系数 Cd = Cd0 + k·Cl²·φ（含地面效应修正）"""
    return CD0 + K_IND * cl * cl * phi_ground


def simulate(flat_length_m, v_trans_mps, nozzle_takeoff_deg, strategy, pitch_deg,
             nozzle_air_deg=0, dt=DT_DEFAULT):
    """
    滑跃短距起飞全过程仿真。

    返回: (success, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m)
    """
    check_pitch_deg(pitch_deg)
    nozzle_final_rad = np.radians(nozzle_takeoff_deg)
    trans_duration_s = nozzle_takeoff_deg / NOZZLE_RATE_DEG_S if nozzle_takeoff_deg > 0 else 0.0
    pitch_rad = np.radians(pitch_deg)
    nozzle_start_rad = 0.0
    min_plume_trailing_edge_m = None

    v_gs, x, t = 0.0, 0.0, 0.0
    transitioned, in_trans, trans_start_t = False, False, 0.0
    nozzle_rad = nozzle_start_rad

    def track_plume(on_ski_jump):
        """θ = 喷口偏转角 + 滑跃角（若在滑跃段）；更新甲板受影响最后缘。"""
        nonlocal min_plume_trailing_edge_m
        theta_deg = np.degrees(nozzle_rad) + (SKI_JUMP_ANGLE_DEG if on_ski_jump else 0.0)
        min_plume_trailing_edge_m = update_min_plume_trailing_edge_m(
            x, theta_deg, V_WIND_MPS, min_plume_trailing_edge_m)

    def step_nozzle():
        nonlocal transitioned, in_trans, trans_start_t, nozzle_rad
        if (strategy == 'A' and not transitioned and not in_trans
                and v_gs >= v_trans_mps):
            in_trans, trans_start_t = True, t
        if in_trans:
            ratio = (t - trans_start_t) / trans_duration_s if trans_duration_s > 0 else 1.0
            if ratio >= 1.0:
                ratio, in_trans, transitioned = 1.0, False, True
            nozzle_rad = nozzle_start_rad + (nozzle_final_rad - nozzle_start_rad) * ratio
        elif strategy == 'B' or transitioned:
            nozzle_rad = nozzle_final_rad

    # ==================== 阶段 1：平直甲板滑跑 ====================
    while x < flat_length_m and t < MAX_GROUND_TIME_S:
        step_nozzle()
        v_air = v_gs + V_WIND_MPS
        q = dynamic_pressure(v_air)
        t_h = T_MAIN_GROUND_N * np.cos(nozzle_rad)
        t_v = T_MAIN_GROUND_N * np.sin(nozzle_rad) + T_LIFTFAN_N
        lift = q * S_REF_M2 * CL_TAXI
        drag = q * S_REF_M2 * drag_coefficient(CL_TAXI, PHI_GROUND_FLAT)
        normal = max(WEIGHT_N - lift - t_v, 0.0)
        v_gs = max(v_gs + (t_h - drag - MU * normal) / MASS_KG * dt, 0.0)
        x += v_gs * dt
        t += dt
        track_plume(on_ski_jump=False)

    # ==================== 阶段 2：滑跃甲板滑跑 ====================
    s = 0.0
    while s < SKI_JUMP_LENGTH_M and t < MAX_GROUND_TIME_S:
        step_nozzle()
        v_air = v_gs + V_WIND_MPS * SKI_JUMP_COS
        q = dynamic_pressure(v_air)
        phi_s = PHI_GROUND_FLAT * (1 - s / SKI_JUMP_LENGTH_M) + s / SKI_JUMP_LENGTH_M
        t_s = T_MAIN_GROUND_N * np.cos(nozzle_rad)
        t_n = T_MAIN_GROUND_N * np.sin(nozzle_rad) + T_LIFTFAN_N
        lift = q * S_REF_M2 * CL_TAXI
        drag = q * S_REF_M2 * drag_coefficient(CL_TAXI, phi_s)
        normal = max(WEIGHT_N * SKI_JUMP_COS - lift - t_n, 0.0)
        v_gs = max(v_gs + (t_s - drag - WEIGHT_N * SKI_JUMP_SIN - MU * normal) / MASS_KG * dt, 0.0)
        s += v_gs * dt
        x += v_gs * SKI_JUMP_COS * dt
        t += dt
        track_plume(on_ski_jump=True)

    if s < SKI_JUMP_LENGTH_M * 0.99:
        return False, x, v_gs, t, 0.0, _plume_edge_or_zero(min_plume_trailing_edge_m)

    v_deck = v_gs
    vx = v_gs * SKI_JUMP_COS
    vy = v_gs * SKI_JUMP_SIN
    x_deck, t_deck = x, t
    min_vy = vy

    if vy < 0:
        return False, x_deck, v_deck, t_deck, min_vy, _plume_edge_or_zero(min_plume_trailing_edge_m)

    plume_trailing_edge_m = _plume_edge_or_zero(min_plume_trailing_edge_m)
    if ALLOW_AIR_NOZZLE_VECTORING:
        return _simulate_air_vectoring(
            vx, vy, pitch_rad, nozzle_final_rad, nozzle_takeoff_deg, nozzle_air_deg,
            x_deck, v_deck, t_deck, min_vy, plume_trailing_edge_m, dt)
    return _simulate_air_fixed(
        vx, vy, pitch_rad, nozzle_final_rad,
        x_deck, v_deck, t_deck, min_vy, plume_trailing_edge_m, dt)


def _simulate_air_fixed(vx, vy, pitch_rad, nozzle_final_rad,
                        x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m, dt):
    t_air = 0.0
    while t_air < MAX_AIR_TIME_S:
        v_spd = np.hypot(vx, vy)
        gamma = np.arctan2(vy, vx) if v_spd > 0.1 else 0.0
        v_air = np.hypot(vx + V_WIND_MPS, vy)
        q = dynamic_pressure(v_air)
        alpha_eff = pitch_rad - gamma
        if abs(alpha_eff) > ALPHA_LIMIT_RAD:
            return False, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m

        cl = np.clip(CL_TAXI + CL_ALPHA * alpha_eff, CL_MIN, CL_MAX)
        lift = q * S_REF_M2 * cl
        drag = q * S_REF_M2 * (CD0 + K_IND * cl * cl)

        thrust_ang = pitch_rad + nozzle_final_rad
        t_mx = T_MAIN_STOVL_N * np.cos(thrust_ang)
        t_my = T_MAIN_STOVL_N * np.sin(thrust_ang)
        t_vx = -(T_LIFTFAN_N + T_ROLLPOSTS_N) * np.sin(pitch_rad)
        t_vy = (T_LIFTFAN_N + T_ROLLPOSTS_N) * np.cos(pitch_rad)

        sin_g, cos_g = np.sin(gamma), np.cos(gamma)
        lx, ly = -lift * sin_g, lift * cos_g
        dx, dy = -drag * cos_g, -drag * sin_g
        dvx = (t_mx + t_vx + lx + dx) / MASS_KG
        dvy = (t_my + t_vy + ly + dy - WEIGHT_N) / MASS_KG

        if dvy < -15:
            return False, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m

        vx += dvx * dt
        vy += dvy * dt
        t_air += dt
        min_vy = min(min_vy, vy)

        if vy <= 0:
            return False, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m
        if lift + t_vy >= WEIGHT_N and vy > 2 and t_air > 0.3:
            break

    return True, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m


def _simulate_air_vectoring(vx, vy, pitch_rad, nozzle_final_rad, nozzle_takeoff_deg, nozzle_air_deg,
                            x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m, dt):
    nozzle_air_final_rad = np.radians(nozzle_air_deg)
    trans_air_duration_s = abs(nozzle_air_deg - nozzle_takeoff_deg) / NOZZLE_RATE_DEG_S
    in_trans_air, transitioned_air, trans_air_start_t = False, False, 0.0
    nozzle_air_rad = nozzle_final_rad
    t_air = 0.0

    while t_air < MAX_AIR_TIME_S:
        if nozzle_air_deg != nozzle_takeoff_deg:
            if not transitioned_air and not in_trans_air:
                in_trans_air, trans_air_start_t = True, t_air
            if in_trans_air:
                ratio = ((t_air - trans_air_start_t) / trans_air_duration_s
                         if trans_air_duration_s > 0 else 1.0)
                if ratio >= 1.0:
                    ratio, in_trans_air, transitioned_air = 1.0, False, True
                nozzle_air_rad = nozzle_final_rad + (nozzle_air_final_rad - nozzle_final_rad) * ratio
            elif transitioned_air:
                nozzle_air_rad = nozzle_air_final_rad

        v_spd = np.hypot(vx, vy)
        gamma = np.arctan2(vy, vx) if v_spd > 0.1 else 0.0
        v_air = np.hypot(vx + V_WIND_MPS, vy)
        q = dynamic_pressure(v_air)
        alpha_eff = pitch_rad - gamma
        if abs(alpha_eff) > ALPHA_LIMIT_RAD:
            return False, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m

        cl = np.clip(CL_TAXI + CL_ALPHA * alpha_eff, CL_MIN, CL_MAX)
        lift = q * S_REF_M2 * cl
        drag = q * S_REF_M2 * (CD0 + K_IND * cl * cl)

        thrust_ang = pitch_rad + nozzle_air_rad
        t_mx = T_MAIN_STOVL_N * np.cos(thrust_ang)
        t_my = T_MAIN_STOVL_N * np.sin(thrust_ang)
        t_vx = -(T_LIFTFAN_N + T_ROLLPOSTS_N) * np.sin(pitch_rad)
        t_vy = (T_LIFTFAN_N + T_ROLLPOSTS_N) * np.cos(pitch_rad)

        sin_g, cos_g = np.sin(gamma), np.cos(gamma)
        dvx = (t_mx + t_vx - lift * sin_g - drag * cos_g) / MASS_KG
        dvy = (t_my + t_vy + lift * cos_g - drag * sin_g - WEIGHT_N) / MASS_KG
        if dvy < -15:
            return False, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m

        vx += dvx * dt
        vy += dvy * dt
        t_air += dt
        min_vy = min(min_vy, vy)
        if vy <= 0:
            return False, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m
        if lift + t_vy >= WEIGHT_N and vy > 2 and t_air > 0.3:
            break

    return True, x_deck, v_deck, t_deck, min_vy, min_plume_trailing_edge_m


def _ground_step_flat_c(v_gs, x, nozzle_deg, dt):
    nozzle_rad = np.radians(nozzle_deg)
    v_air = v_gs + V_WIND_MPS
    q = dynamic_pressure(v_air)
    t_h = T_MAIN_GROUND_N * np.cos(nozzle_rad)
    t_v = T_MAIN_GROUND_N * np.sin(nozzle_rad) + T_LIFTFAN_N
    lift = q * S_REF_M2 * CL_TAXI
    drag = q * S_REF_M2 * drag_coefficient(CL_TAXI, PHI_GROUND_FLAT)
    normal = max(WEIGHT_N - lift - t_v, 0.0)
    v2 = max(v_gs + (t_h - drag - MU * normal) / MASS_KG * dt, 0.0)
    return v2, x + v2 * dt


def _ground_step_ski_c(v_gs, x, s, nozzle_deg, dt):
    nozzle_rad = np.radians(nozzle_deg)
    v_air = v_gs + V_WIND_MPS * SKI_JUMP_COS
    q = dynamic_pressure(v_air)
    phi_s = PHI_GROUND_FLAT * (1 - s / SKI_JUMP_LENGTH_M) + s / SKI_JUMP_LENGTH_M
    t_s = T_MAIN_GROUND_N * np.cos(nozzle_rad)
    t_n = T_MAIN_GROUND_N * np.sin(nozzle_rad) + T_LIFTFAN_N
    lift = q * S_REF_M2 * CL_TAXI
    drag = q * S_REF_M2 * drag_coefficient(CL_TAXI, phi_s)
    normal = max(WEIGHT_N * SKI_JUMP_COS - lift - t_n, 0.0)
    v2 = max(v_gs + (t_s - drag - WEIGHT_N * SKI_JUMP_SIN - MU * normal) / MASS_KG * dt, 0.0)
    s2 = s + v2 * dt
    return v2, x + v2 * SKI_JUMP_COS * dt, s2


def simulate_strategy_c(flat_length_m, pitch_deg, min_safe_distance_m, dt=DT_DEFAULT):
    """
    策略 C：尾流约束下 DP 优化喷口减小 schedule，再经空中段判定能否成功离舰。
    """
    check_pitch_deg(pitch_deg)
    if min_safe_distance_m >= 0:
        raise ValueError("min_safe_distance_m 必须为负值")

    rate_step = NOZZLE_RATE_DEG_S * dt
    init_nozzle = calc_min_nozzle_deg_for_plume(0.0, min_safe_distance_m, V_WIND_MPS, on_ski_jump=False)
    states = {round(init_nozzle, 2): (0.0, 0.0, 0.0, 0.0, False)}
    min_plume_trailing_edge_m = None
    completed = []

    for _ in range(int(MAX_GROUND_TIME_S / dt) * 3):
        if not states:
            break
        new_states = {}
        for nozzle_deg, (v_gs, x, t, s, on_ski) in states.items():
            if on_ski and s >= SKI_JUMP_LENGTH_M:
                completed.append((nozzle_deg, v_gs, x, t, s))
                continue

            nozzle_min = calc_min_nozzle_deg_for_plume(
                x, min_safe_distance_m, V_WIND_MPS, on_ski_jump=on_ski)
            nozzle_deg = max(nozzle_deg, nozzle_min)

            for decrease in (False, True):
                n2 = nozzle_deg - rate_step if decrease else nozzle_deg
                if decrease and n2 < nozzle_min - 1e-9:
                    continue
                n2 = max(n2, nozzle_min)

                if on_ski:
                    v2, x2, s2 = _ground_step_ski_c(v_gs, x, s, n2, dt)
                    on_ski2 = True
                    theta_deg = n2 + SKI_JUMP_ANGLE_DEG
                else:
                    v2, x2 = _ground_step_flat_c(v_gs, x, n2, dt)
                    on_ski2 = x2 >= flat_length_m
                    s2 = 0.0
                    theta_deg = n2

                t2 = t + dt
                min_plume_trailing_edge_m = update_min_plume_trailing_edge_m(
                    x2, theta_deg, V_WIND_MPS, min_plume_trailing_edge_m)

                if on_ski2 and s2 >= SKI_JUMP_LENGTH_M:
                    completed.append((n2, v2, x2, t2, s2))
                    continue

                key = round(n2, 2)
                val = (v2, x2, t2, s2, on_ski2)
                if key not in new_states or v2 > new_states[key][0]:
                    new_states[key] = val
        states = new_states

    pitch_rad = np.radians(pitch_deg)
    plume_val = _plume_edge_or_zero(min_plume_trailing_edge_m)
    best = None
    total_m = total_takeoff_distance_m(flat_length_m)

    for nozzle_deg, v_deck, x_deck, t_deck, s in completed:
        if s < SKI_JUMP_LENGTH_M * 0.99:
            continue
        vy = v_deck * SKI_JUMP_SIN
        if vy < 0:
            continue
        vx = v_deck * SKI_JUMP_COS
        nozzle_rad = np.radians(nozzle_deg)
        ok, _, _, _, min_vy, _ = _simulate_air_fixed(
            vx, vy, pitch_rad, nozzle_rad, x_deck, v_deck, t_deck, vy, plume_val, dt)
        if not ok:
            continue
        candidate = dict(
            total_m=total_m, flat_m=flat_length_m, pitch_deg=pitch_deg,
            nozzle_deg=nozzle_deg, v_deck_mps=v_deck, t_deck_s=t_deck,
            min_vy_mps=min_vy, min_plume_trailing_edge_m=plume_val,
        )
        if best is None or v_deck > best['v_deck_mps']:
            best = candidate

    return best


def search_strategy_c(min_safe_distance_m):
    best = None
    for flat_m in FLAT_LENGTH_M_LIST_C:
        for pitch_deg in PITCH_DEG_LIST_C:
            result = simulate_strategy_c(flat_m, pitch_deg, min_safe_distance_m)
            if result and (best is None or result['total_m'] < best['total_m']):
                best = result
    return best


def print_strategy_c_result(title, r):
    print(f"★ {title}: 总距 {r['total_m']:.1f} m ({r['total_m'] * M_TO_FT:.0f} ft)")
    print(f"    平直段 {r['flat_m']:.0f} m | 俯仰角 {r['pitch_deg']}°")
    print(f"    离甲板喷管角 {r['nozzle_deg']:.1f}° | 离甲板 {r['v_deck_mps']:.1f} m/s @ {r['t_deck_s']:.1f} s")
    print(f"    最小 Vy {r['min_vy_mps']:.2f} m/s")
    print(f"    离甲板总时间 {r['t_deck_s']:.2f} s | 甲板受影响最后缘 {r['min_plume_trailing_edge_m']:.1f} m")


def _pack_result_a_fixed(total_m, flat_m, v_trans, nozzle_deg, pitch_deg, v_deck, t_deck, min_vy,
                         plume_trailing_edge_m):
    return dict(total_m=total_m, flat_m=flat_m, v_trans_mps=v_trans, nozzle_deg=nozzle_deg,
                pitch_deg=pitch_deg, v_deck_mps=v_deck, t_deck_s=t_deck, min_vy_mps=min_vy,
                min_plume_trailing_edge_m=plume_trailing_edge_m)


def _pack_result_a_vectoring(total_m, flat_m, v_trans, nozzle_deg, nozzle_air_deg, pitch_deg,
                             v_deck, t_deck, min_vy, plume_trailing_edge_m):
    return dict(total_m=total_m, flat_m=flat_m, v_trans_mps=v_trans, nozzle_deg=nozzle_deg,
                nozzle_air_deg=nozzle_air_deg, pitch_deg=pitch_deg, v_deck_mps=v_deck,
                t_deck_s=t_deck, min_vy_mps=min_vy, min_plume_trailing_edge_m=plume_trailing_edge_m)


def _pack_result_b_fixed(total_m, flat_m, nozzle_deg, pitch_deg, v_deck, t_deck, min_vy, plume_trailing_edge_m):
    return dict(total_m=total_m, flat_m=flat_m, nozzle_deg=nozzle_deg, pitch_deg=pitch_deg,
                v_deck_mps=v_deck, t_deck_s=t_deck, min_vy_mps=min_vy, min_plume_trailing_edge_m=plume_trailing_edge_m)


def _pack_result_b_vectoring(total_m, flat_m, nozzle_deg, nozzle_air_deg, pitch_deg, v_deck,
                             t_deck, plume_trailing_edge_m):
    return dict(total_m=total_m, flat_m=flat_m, nozzle_deg=nozzle_deg,
                nozzle_air_deg=nozzle_air_deg, pitch_deg=pitch_deg, v_deck_mps=v_deck,
                t_deck_s=t_deck, min_plume_trailing_edge_m=plume_trailing_edge_m)


def print_strategy_a_result(title, r):
    print(f"★ {title}: 总距 {r['total_m']:.1f} m ({r['total_m'] * M_TO_FT:.0f} ft)")
    if ALLOW_AIR_NOZZLE_VECTORING:
        print(f"    平直段 {r['flat_m']:.0f} m | 转换地速 {r['v_trans_mps']} m/s | 滑跑喷管角 {r['nozzle_deg']}°")
        print(f"    离甲板喷管角 {r['nozzle_air_deg']}° | 俯仰角 {r['pitch_deg']}° | 离甲板速度 {r['v_deck_mps']:.1f} m/s")
    else:
        print(f"    平直段 {r['flat_m']:.0f} m | 转换地速 {r['v_trans_mps']} m/s | 喷管角 {r['nozzle_deg']}°")
        print(f"    俯仰角 {r['pitch_deg']}° | 离甲板 {r['v_deck_mps']:.1f} m/s @ {r['t_deck_s']:.1f} s")
    print(f"    最小 Vy {r['min_vy_mps']:.2f} m/s")
    print(f"    离甲板总时间 {r['t_deck_s']:.2f} s | 甲板受影响最后缘 {r['min_plume_trailing_edge_m']:.1f} m")


def print_strategy_b_result(title, r):
    print(f"★ {title}: 总距 {r['total_m']:.1f} m ({r['total_m'] * M_TO_FT:.0f} ft)")
    if ALLOW_AIR_NOZZLE_VECTORING:
        print(f"    平直段 {r['flat_m']:.0f} m | 固定喷管角 {r['nozzle_deg']}°")
        print(f"    离甲板喷管角 {r['nozzle_air_deg']}° | 俯仰角 {r['pitch_deg']}° | 离甲板速度 {r['v_deck_mps']:.1f} m/s")
    else:
        print(f"    平直段 {r['flat_m']:.0f} m | 固定喷管角 {r['nozzle_deg']}° | 俯仰角 {r['pitch_deg']}°")
        print(f"    离甲板 {r['v_deck_mps']:.1f} m/s @ {r['t_deck_s']:.1f} s")
    print(f"    离甲板总时间 {r['t_deck_s']:.2f} s | 甲板受影响最后缘 {r['min_plume_trailing_edge_m']:.1f} m")


def search_strategy_a():
    best = None
    if ALLOW_AIR_NOZZLE_VECTORING:
        for flat_m in FLAT_LENGTH_M_LIST_A:
            for nozzle_deg in NOZZLE_TAKEOFF_DEG_LIST_A:
                for v_trans in V_TRANS_MPS_LIST_A:
                    for nozzle_air_deg in NOZZLE_AIR_DEG_LIST:
                        for pitch_deg in PITCH_DEG_LIST:
                            ok, _, v_deck, t_deck, min_vy, plume_trailing_edge_m = simulate(
                                flat_m, v_trans, nozzle_deg, 'A', pitch_deg, nozzle_air_deg)
                            if not ok:
                                continue
                            total_m = total_takeoff_distance_m(flat_m)
                            candidate = _pack_result_a_vectoring(
                                total_m, flat_m, v_trans, nozzle_deg, nozzle_air_deg, pitch_deg,
                                v_deck, t_deck, min_vy, plume_trailing_edge_m)
                            if best is None or candidate['total_m'] < best['total_m']:
                                best = candidate
    else:
        for flat_m in FLAT_LENGTH_M_LIST_A:
            for nozzle_deg in NOZZLE_TAKEOFF_DEG_LIST_A:
                for v_trans in V_TRANS_MPS_LIST_A:
                    for pitch_deg in PITCH_DEG_LIST:
                        ok, _, v_deck, t_deck, min_vy, plume_trailing_edge_m = simulate(
                            flat_m, v_trans, nozzle_deg, 'A', pitch_deg)
                        if not ok:
                            continue
                        total_m = total_takeoff_distance_m(flat_m)
                        candidate = _pack_result_a_fixed(
                            total_m, flat_m, v_trans, nozzle_deg, pitch_deg,
                            v_deck, t_deck, min_vy, plume_trailing_edge_m)
                        if best is None or candidate['total_m'] < best['total_m']:
                            best = candidate
    return best


def fine_tune_strategy_a(initial):
    best = initial
    if ALLOW_AIR_NOZZLE_VECTORING:
        for flat_m in range(max(int(initial['flat_m']) - 20, 0), int(initial['flat_m']), 2):
            for v_trans in range(initial['v_trans_mps'] - 10, initial['v_trans_mps'] + 10, 2):
                for nozzle_deg in range(max(initial['nozzle_deg'] - 5, 1), initial['nozzle_deg'] + 6, 2):
                    if nozzle_deg > 90:
                        continue
                    for nozzle_air_deg in range(max(initial['nozzle_air_deg'] - 5, 0),
                                                min(initial['nozzle_air_deg'] + 6, 91), 2):
                        for pitch_deg in range(max(initial['pitch_deg'] - 5, 0),
                                               min(initial['pitch_deg'] + 6, PITCH_MAX_DEG + 1), 1):
                            ok, _, v_deck, t_deck, min_vy, plume_trailing_edge_m = simulate(
                                flat_m, v_trans, nozzle_deg, 'A', pitch_deg, nozzle_air_deg)
                            if not ok:
                                continue
                            total_m = total_takeoff_distance_m(flat_m)
                            if total_m < best['total_m']:
                                best = _pack_result_a_vectoring(
                                    total_m, flat_m, v_trans, nozzle_deg, nozzle_air_deg, pitch_deg,
                                    v_deck, t_deck, min_vy, plume_trailing_edge_m)
    else:
        for flat_m in range(max(int(initial['flat_m']) - 20, 0), int(initial['flat_m']), 1):
            for v_trans in range(initial['v_trans_mps'] - 10, initial['v_trans_mps'] + 11, 1):
                for nozzle_deg in range(max(initial['nozzle_deg'] - 5, 1), initial['nozzle_deg'] + 6, 1):
                    if nozzle_deg > 90:
                        continue
                    for pitch_deg in range(max(initial['pitch_deg'], 0), min(initial['pitch_deg'] + 3, PITCH_MAX_DEG + 1), 1):
                        ok, _, v_deck, t_deck, min_vy, plume_trailing_edge_m = simulate(
                            flat_m, v_trans, nozzle_deg, 'A', pitch_deg)
                        if not ok:
                            continue
                        total_m = total_takeoff_distance_m(flat_m)
                        if total_m < best['total_m']:
                            best = _pack_result_a_fixed(
                                total_m, flat_m, v_trans, nozzle_deg, pitch_deg,
                                v_deck, t_deck, min_vy, plume_trailing_edge_m)
    return best if best['total_m'] < initial['total_m'] else None


def search_strategy_b():
    best = None
    if ALLOW_AIR_NOZZLE_VECTORING:
        for nozzle_deg in NOZZLE_TAKEOFF_DEG_LIST_B:
            for flat_m in FLAT_LENGTH_M_LIST_B:
                for nozzle_air_deg in NOZZLE_AIR_DEG_LIST:
                    for pitch_deg in PITCH_DEG_LIST:
                        ok, _, v_deck, t_deck, _, plume_trailing_edge_m = simulate(
                            flat_m, 0, nozzle_deg, 'B', pitch_deg, nozzle_air_deg)
                        if not ok:
                            continue
                        total_m = total_takeoff_distance_m(flat_m)
                        candidate = _pack_result_b_vectoring(
                            total_m, flat_m, nozzle_deg, nozzle_air_deg, pitch_deg, v_deck,
                            t_deck, plume_trailing_edge_m)
                        if best is None or candidate['total_m'] < best['total_m']:
                            best = candidate
    else:
        for flat_m in FLAT_LENGTH_M_LIST_B:
            for nozzle_deg in NOZZLE_TAKEOFF_DEG_LIST_B:
                for pitch_deg in PITCH_DEG_LIST:
                    ok, _, v_deck, t_deck, min_vy, plume_trailing_edge_m = simulate(
                        flat_m, 0, nozzle_deg, 'B', pitch_deg)
                    if not ok:
                        continue
                    total_m = total_takeoff_distance_m(flat_m)
                    candidate = _pack_result_b_fixed(
                        total_m, flat_m, nozzle_deg, pitch_deg, v_deck, t_deck, min_vy, plume_trailing_edge_m)
                    if best is None or candidate['total_m'] < best['total_m']:
                        best = candidate
    return best


def fine_tune_strategy_b(initial):
    best = initial
    if ALLOW_AIR_NOZZLE_VECTORING:
        for flat_m in range(max(int(initial['flat_m']) - 20, 0), int(initial['flat_m']), 1):
            for nozzle_deg in range(initial['nozzle_deg'] - 5, initial['nozzle_deg'] + 6, 1):
                if nozzle_deg > 90:
                    continue
                for nozzle_air_deg in range(max(initial['nozzle_air_deg'] - 5, 0),
                                            min(initial['nozzle_air_deg'] + 6, 91), 1):
                    for pitch_deg in range(max(initial['pitch_deg'] - 5, 0),
                                           min(initial['pitch_deg'] + 6, PITCH_MAX_DEG + 1), 1):
                        ok, _, v_deck, t_deck, _, plume_trailing_edge_m = simulate(
                            flat_m, 0, nozzle_deg, 'B', pitch_deg, nozzle_air_deg)
                        if not ok:
                            continue
                        total_m = total_takeoff_distance_m(flat_m)
                        if total_m < best['total_m']:
                            best = _pack_result_b_vectoring(
                                total_m, flat_m, nozzle_deg, nozzle_air_deg, pitch_deg, v_deck,
                                t_deck, plume_trailing_edge_m)
    else:
        for flat_m in range(max(int(initial['flat_m']) - 20, 0), int(initial['flat_m']), 1):
            for nozzle_deg in range(max(initial['nozzle_deg'] - 10, 0), initial['nozzle_deg'] + 11, 1):
                if nozzle_deg > 90:
                    continue
                for pitch_deg in range(max(initial['pitch_deg'], 0), min(initial['pitch_deg'] + 3, PITCH_MAX_DEG + 1), 1):
                    ok, _, v_deck, t_deck, min_vy, plume_trailing_edge_m = simulate(
                        flat_m, 0, nozzle_deg, 'B', pitch_deg)
                    if not ok:
                        continue
                    total_m = total_takeoff_distance_m(flat_m)
                    if total_m < best['total_m']:
                        best = _pack_result_b_fixed(
                            total_m, flat_m, nozzle_deg, pitch_deg, v_deck, t_deck, min_vy, plume_trailing_edge_m)
    return best if best['total_m'] < initial['total_m'] else None


def run_strategy_a_search():
    """策略 A 粗搜索 + 细化，返回最优结果 dict 或 None。"""
    best = search_strategy_a()
    if not best:
        return None
    refined = fine_tune_strategy_a(best)
    return refined if refined else best


def _main():
    print_config_summary()

    print("\n" + "=" * 60)
    print("策略 A：滑跑中延迟偏转喷口（自 0° 转换）")
    print("=" * 60)

    best_a = search_strategy_a()
    if best_a:
        print_strategy_a_result("粗搜索最优", best_a)
        print("细化搜索 …")
        refined_a = fine_tune_strategy_a(best_a)
        if refined_a:
            best_a = refined_a
        print_strategy_a_result("细化最优", best_a)

    print("\n" + "=" * 60)
    print("策略 B：滑跑全程固定喷口")
    print("=" * 60)

    best_b = search_strategy_b()
    if best_b:
        print_strategy_b_result("粗搜索最优", best_b)
        print("细化搜索 …")
        refined_b = fine_tune_strategy_b(best_b)
        if refined_b:
            best_b = refined_b
        print_strategy_b_result("细化最优", best_b)

    print("\n" + "=" * 60)
    print(f"策略 C：尾流约束 min(x−安全距离) ≥ {MIN_SAFE_DISTANCE_M:.0f} m")
    print("=" * 60)

    init_nozzle_c = calc_min_nozzle_deg_for_plume(0.0, MIN_SAFE_DISTANCE_M, V_WIND_MPS, on_ski_jump=False)
    print(f"起始喷管角（x=0 反推）: {init_nozzle_c:.1f}°")

    best_c = search_strategy_c(MIN_SAFE_DISTANCE_M)
    if best_c:
        print_strategy_c_result("最优", best_c)

    print("\n" + "=" * 60)
    print("对比总结")
    print("=" * 60)
    if best_a and best_b:
        diff_m = best_b['total_m'] - best_a['total_m']
        print(f"策略 A: {best_a['total_m']:.1f} m ({best_a['total_m'] * M_TO_FT:.0f} ft)")
        if ALLOW_AIR_NOZZLE_VECTORING:
            print(f"        平直段 {best_a['flat_m']:.0f} m，转换地速 {best_a['v_trans_mps']} m/s")
            print(f"        滑跑喷管角 {best_a['nozzle_deg']}°，离甲板喷管角 {best_a['nozzle_air_deg']}°")
        else:
            print(f"        平直段 {best_a['flat_m']:.0f} m，转换地速 {best_a['v_trans_mps']} m/s，喷管角 {best_a['nozzle_deg']}°")
        print(f"策略 B: {best_b['total_m']:.1f} m ({best_b['total_m'] * M_TO_FT:.0f} ft)")
        print(f"        平直段 {best_b['flat_m']:.0f} m，固定喷管角 {best_b['nozzle_deg']}°")
        print(f"策略 A 比 B 短 {diff_m:.1f} m ({diff_m / best_b['total_m'] * 100:.1f}%)")
        if best_c:
            print(f"策略 C: {best_c['total_m']:.1f} m ({best_c['total_m'] * M_TO_FT:.0f} ft)")
            print(f"        平直段 {best_c['flat_m']:.0f} m，离甲板喷管角 {best_c['nozzle_deg']:.1f}°")
            print(f"        比策略 A {'短' if best_c['total_m'] < best_a['total_m'] else '长'} "
                  f"{abs(best_c['total_m'] - best_a['total_m']):.1f} m")


if __name__ == "__main__":
    _main()
