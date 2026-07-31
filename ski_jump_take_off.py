"""固定翼舰载机滑跃起飞仿真（以歼-15 为气动参考）。"""
import numpy as np

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
MPS_TO_KT = 1.94384             # m/s → kt

# ---------------------------------------------------------------------------
# 飞机参数（当前几何仍取 F-35B 量级，Λ 取歼-15）
# ---------------------------------------------------------------------------
MASS_KG = 27200                 # 典型舰基起飞重量，kg
WEIGHT_N = MASS_KG * G          # 重力，N
S_REF_M2 = 42.74                # 机翼参考面积，m² ；歼-15/15T 68.84m2,歼-35 68.9m2 
WINGSPAN_M = 10.7               # 翼展，m；歼-15/15T 14.7m,歼-35 13.6m
WING_HEIGHT_M = 1.96            # 机翼平均离地高度，m，歼-15/15T 2.55m,歼-35 1.96m
ASPECT_RATIO = WINGSPAN_M ** 2 / S_REF_M2  # 展弦比 AR = b²/S
T_MAX_SL_N = 182000             # 最大加力推力（T_THRUST_REF_C 标定），N；歼-15 ~251 kN，歼-15T 264kN,歼-35 ~186 kN
T_MAX_N = T_MAX_SL_N * THRUST_TEMP_FACTOR
CD0 = 0.039                     # 零升阻力系数（襟翼放下、起落架未收） 歼35为0.039， 歼15为0.0475

SWEEP_LE_DEG = 42  # F-35B 35°，歼-35 38°，歼-15 42°
FLAP_DEFLECTION_DEG = 20
FLAP_EFFICIENCY = 0.5
WING_INCIDENCE_DEG = 2

# ---------------------------------------------------------------------------
# 航母甲板参数
# ---------------------------------------------------------------------------
SKI_JUMP_LENGTH_M = 37.0        # 滑跃段弧长，m，库兹涅佐夫级为50米
SKI_JUMP_ANGLE_DEG = 12.5 # 滑跃段角度，库兹涅佐夫级为14度
SKI_JUMP_ANGLE_RAD = np.radians(SKI_JUMP_ANGLE_DEG)
SKI_JUMP_COS = np.cos(SKI_JUMP_ANGLE_RAD)   # 预计算，避免循环内重复三角函数
SKI_JUMP_SIN = np.sin(SKI_JUMP_ANGLE_RAD)
SKI_JUMP_HORIZONTAL_M = SKI_JUMP_LENGTH_M * SKI_JUMP_COS  # 滑跃段水平投影
MU = 0.03                       # 甲板滚动摩擦系数
WIND_KT = 25
V_WIND_MPS = WIND_KT * KT_TO_MPS  # 甲板逆风，m/s

PITCH_MAX_DEG = 20  # 全项目俯仰角硬上限（°）；舰基起飞操纵/结构限制，搜索与仿真均不得超过


def check_pitch_deg(pitch_deg):
    """校验俯仰角不超过 PITCH_MAX_DEG；超限则抛出 ValueError。"""
    if pitch_deg > PITCH_MAX_DEG:
        raise ValueError(f"俯仰角 {pitch_deg}° 超过硬上限 {PITCH_MAX_DEG}°")
    return pitch_deg

PITCH_SEARCH_MIN = 10
PITCH_SEARCH_MAX = PITCH_MAX_DEG
PITCH_SEARCH_STEP = 1
FLAT_SEARCH_MAX_M = 280   # 粗搜平直段上限，m
FLAT_SEARCH_STEP_M = 20
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
    global AMBIENT_TEMP_C, RHO, THRUST_TEMP_FACTOR, T_MAX_N
    AMBIENT_TEMP_C = ambient_temp_c
    RHO = calc_sea_level_density_kg_m3(ambient_temp_c)
    THRUST_TEMP_FACTOR = calc_thrust_temp_factor(ambient_temp_c)
    T_MAX_N = T_MAX_SL_N * THRUST_TEMP_FACTOR


def apply_wind_knots(wind_kt):
    global WIND_KT, V_WIND_MPS
    WIND_KT = wind_kt
    V_WIND_MPS = wind_kt * KT_TO_MPS


def apply_aircraft_geometry(mass_kg, s_ref_m2, wingspan_m, wing_height_m, sweep_le_deg, cd0, t_max_sl_n):
    global MASS_KG, S_REF_M2, WINGSPAN_M, WING_HEIGHT_M, SWEEP_LE_DEG, CD0, T_MAX_SL_N
    MASS_KG = mass_kg
    S_REF_M2 = s_ref_m2
    WINGSPAN_M = wingspan_m
    WING_HEIGHT_M = wing_height_m
    SWEEP_LE_DEG = sweep_le_deg
    CD0 = cd0
    T_MAX_SL_N = t_max_sl_n
    apply_thrust_temperature(AMBIENT_TEMP_C)
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
MAX_AIR_TIME_S = 5.0
CL_MAX = 1.8


def print_config_summary():
    print(f"环境温度:     {AMBIENT_TEMP_C:.0f} °C (推力标定 {T_THRUST_REF_C:.0f} °C)")
    print(f"空气密度 ρ:   {RHO:.4f} kg/m³ | 推力温度系数 {THRUST_TEMP_FACTOR:.4f}")
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


def simulate(flat_length_m, pitch_deg, dt=DT_DEFAULT, max_time_s=MAX_GROUND_TIME_S):
    """
    固定翼滑跃起飞全过程仿真。

    返回: (success, x_deck, v_deck, vy_final, min_vy, t_deck, final_lift_n)
    """
    check_pitch_deg(pitch_deg)
    v_gs, x, t = 0.0, 0.0, 0.0                  # 地速、水平位置、时间

    # ==================== 阶段 1：平直甲板滑跑 ====================
    while x < flat_length_m and t < max_time_s:
        v_air = v_gs + V_WIND_MPS                 # 空速 = 地速 + 甲板风
        q = dynamic_pressure(v_air)               # 动压
        lift = q * S_REF_M2 * CL_TAXI              # 机翼升力 L = q·S·Cl
        drag = q * S_REF_M2 * drag_coefficient(CL_TAXI, PHI_GROUND_FLAT)
        normal = max(WEIGHT_N - lift, 0.0)        # 地面正压力 N = W - L
        # 水平加速度 a = (T - D - μ·N) / m
        v_gs = max(v_gs + (T_MAX_N - drag - MU * normal) / MASS_KG * dt, 0.0)
        x += v_gs * dt
        t += dt

    # ==================== 阶段 2：滑跃甲板滑跑 ====================
    s = 0.0                                       # 沿滑跃斜面的滑行距离
    while s < SKI_JUMP_LENGTH_M and t < max_time_s:
        v_air = v_gs + V_WIND_MPS * SKI_JUMP_COS  # 沿斜面方向的空速
        q = dynamic_pressure(v_air)
        phi_s = PHI_GROUND_FLAT * (1 - s / SKI_JUMP_LENGTH_M) + s / SKI_JUMP_LENGTH_M  # 地面效应衰减
        lift = q * S_REF_M2 * CL_TAXI
        drag = q * S_REF_M2 * drag_coefficient(CL_TAXI, phi_s)
        normal = max(WEIGHT_N * SKI_JUMP_COS - lift, 0.0)  # 垂直于斜面的正压力
        # 沿斜面加速度 a = (T - D - W·sin(θ) - μ·N) / m
        v_gs = max(v_gs + (T_MAX_N - drag - WEIGHT_N * SKI_JUMP_SIN - MU * normal) / MASS_KG * dt, 0.0)
        s += v_gs * dt
        x += v_gs * SKI_JUMP_COS * dt              # 水平位置增量
        t += dt

    if s < SKI_JUMP_LENGTH_M * 0.99:
        return False, x, v_gs, 0.0, 0.0, t, 0.0

    v_deck = v_gs                                 # 离甲板速度（沿斜面）
    vx = v_gs * SKI_JUMP_COS                      # 水平速度分量
    vy = v_gs * SKI_JUMP_SIN                      # 垂直速度分量（滑跃赋予）
    x_deck, t_deck = x, t
    min_vy = vy
    if vy <= 0:
        return False, x_deck, v_deck, vy, min_vy, t_deck, 0.0

    # ==================== 阶段 3：离甲板后自由飞行 ====================
    pitch_rad = np.radians(pitch_deg)             # 固定俯仰角，rad
    t_air = 0.0
    final_lift_n = 0.0

    while t_air < MAX_AIR_TIME_S and t < max_time_s:
        v_spd = np.hypot(vx, vy)
        gamma = np.arctan2(vy, vx) if v_spd > 0.1 else 0.0  # 航迹角
        v_air = np.hypot(vx + V_WIND_MPS, vy)      # 合空速
        q = dynamic_pressure(v_air)
        alpha_eff = pitch_rad - gamma              # 有效迎角 = 俯仰角 - 航迹角
        cl = np.clip(CL_TAXI + CL_ALPHA * alpha_eff, 0.0, CL_MAX)  # Cl = Cl_taxi + C_Lα·α
        lift = q * S_REF_M2 * cl
        drag = q * S_REF_M2 * (CD0 + K_IND * cl * cl)  # 离甲板后无地面效应
        final_lift_n = lift

        sin_g, cos_g = np.sin(gamma), np.cos(gamma)
        dvx = (T_MAX_N - lift * sin_g - drag * cos_g) / MASS_KG  # 水平加速度
        dvy = (lift * cos_g - drag * sin_g - WEIGHT_N) / MASS_KG  # 垂直加速度
        vx += dvx * dt
        vy += dvy * dt
        t_air += dt
        t += dt
        min_vy = min(min_vy, vy)

        if vy <= 0:                                # 垂直速度降为 0 → 失败
            return False, x_deck, v_deck, vy, min_vy, t_deck, final_lift_n
        # 安全判据：升力接近重力且有足够爬升率
        if lift >= WEIGHT_N * 0.95 and vy > 1.0 and t_air > 0.5:
            break

    return True, x_deck, v_deck, vy, min_vy, t_deck, final_lift_n


def best_pitch_for_flat(flat_m, pitch_values):
    """给定平直段长度，返回 (pitch_deg, min_vy, sim_result) 或 None。"""
    best = None
    for pitch_deg in pitch_values:
        if pitch_deg > PITCH_MAX_DEG:
            continue
        ok, x_deck, v_deck, vy_final, min_vy, t_deck, final_lift = simulate(flat_m, pitch_deg)
        if ok and (best is None or min_vy > best[1]):
            best = (pitch_deg, min_vy, (ok, x_deck, v_deck, vy_final, min_vy, t_deck, final_lift))
    return best


def search_flat_length():
    best_overall = None
    print("=" * 70)
    print("扫描最小平直段（同步搜索最优俯仰角）")
    print("=" * 70)

    for flat_m in range(0, FLAT_SEARCH_MAX_M + 1, FLAT_SEARCH_STEP_M):
        result = best_pitch_for_flat(flat_m, range(PITCH_SEARCH_MIN, PITCH_SEARCH_MAX + 1, PITCH_SEARCH_STEP))
        total_m = total_takeoff_distance_m(flat_m)
        if result:
            pitch_deg, min_vy, sim = result
            _, _, _, _, _, t_deck, _ = sim
            status = f"✓ 成功 | 俯仰角 {pitch_deg}° | 最小 Vy {min_vy:.2f} m/s"
            if best_overall is None or total_m < best_overall['total_m']:
                best_overall = dict(total_m=total_m, flat_m=flat_m, pitch_deg=pitch_deg,
                                    min_vy_mps=min_vy, t_deck_s=t_deck)
        else:
            status = "✗ 失败"
        print(f"  平直段 {flat_m:3d} m | 总距 {total_m:6.1f} m | {status}")

    if best_overall:
        print(f"\n  粗搜索最优: 平直段 {best_overall['flat_m']} m，"
              f"总距 {best_overall['total_m']:.1f} m，俯仰角 {best_overall['pitch_deg']}°")
        print("  细化搜索 …")
        for flat_m in range(max(int(best_overall['flat_m']) - 20, 0),
                            int(best_overall['flat_m']) + 21, 2):
            pitch_range = range(max(best_overall['pitch_deg'] - 3, PITCH_SEARCH_MIN),
                                min(best_overall['pitch_deg'] + 4, PITCH_SEARCH_MAX + 1), 1)
            result = best_pitch_for_flat(flat_m, pitch_range)
            if not result:
                continue
            pitch_deg, min_vy, sim = result
            _, _, _, _, _, t_deck, _ = sim
            total_m = total_takeoff_distance_m(flat_m)
            if total_m < best_overall['total_m']:
                best_overall = dict(total_m=total_m, flat_m=flat_m, pitch_deg=pitch_deg,
                                    min_vy_mps=min_vy, t_deck_s=t_deck, sim=sim)
    return best_overall


def run_min_takeoff_search():
    """最小起飞总距离搜索（粗搜 + 细化），无控制台输出。"""
    best_overall = None
    for flat_m in range(0, FLAT_SEARCH_MAX_M + 1, FLAT_SEARCH_STEP_M):
        result = best_pitch_for_flat(flat_m, range(PITCH_SEARCH_MIN, PITCH_SEARCH_MAX + 1, PITCH_SEARCH_STEP))
        if not result:
            continue
        pitch_deg, min_vy, sim = result
        _, x_deck, v_deck, _, _, t_deck, _ = sim
        total_m = total_takeoff_distance_m(flat_m)
        if best_overall is None or total_m < best_overall['total_m']:
            best_overall = dict(total_m=total_m, flat_m=flat_m, pitch_deg=pitch_deg,
                                min_vy_mps=min_vy, t_deck_s=t_deck, v_deck_mps=v_deck,
                                x_deck_m=x_deck, sim=sim)

    if not best_overall:
        return None

    for flat_m in range(max(int(best_overall['flat_m']) - 20, 0),
                        int(best_overall['flat_m']) + 21, 2):
        pitch_range = range(max(best_overall['pitch_deg'] - 3, PITCH_SEARCH_MIN),
                            min(best_overall['pitch_deg'] + 4, PITCH_SEARCH_MAX + 1), 1)
        result = best_pitch_for_flat(flat_m, pitch_range)
        if not result:
            continue
        pitch_deg, min_vy, sim = result
        _, x_deck, v_deck, _, _, t_deck, _ = sim
        total_m = total_takeoff_distance_m(flat_m)
        if total_m < best_overall['total_m']:
            best_overall = dict(total_m=total_m, flat_m=flat_m, pitch_deg=pitch_deg,
                                min_vy_mps=min_vy, t_deck_s=t_deck, v_deck_mps=v_deck,
                                x_deck_m=x_deck, sim=sim)
    return best_overall


def print_best_result(best):
    if not best:
        print("  未找到可行解。")
        return
    sim = best.get('sim')
    if sim:
        _, x_deck, v_deck, _, min_vy, t_deck, final_lift = sim
    else:
        ok, x_deck, v_deck, _, min_vy, t_deck, final_lift = simulate(best['flat_m'], best['pitch_deg'])
        if not ok:
            print("  未找到可行解。")
            return

    print("\n" + "=" * 70)
    print("最优结果")
    print("=" * 70)
    print(f"  最小平直段:     {best['flat_m']:.0f} m")
    print(f"  总起飞距离:     {best['total_m']:.1f} m ({best['total_m'] * M_TO_FT:.0f} ft)")
    print(f"  最优俯仰角:     {best['pitch_deg']}°")
    print(f"  离甲板速度:     {v_deck:.1f} m/s ({v_deck * MPS_TO_KT:.0f} kt)")
    print(f"  离甲板 Vy:      {v_deck * SKI_JUMP_SIN:.1f} m/s")
    print(f"  最小 Vy:        {min_vy:.2f} m/s")
    print(f"  离甲板总时间:   {t_deck:.2f} s")
    print(f"  最终升力:       {final_lift / 1000:.1f} kN  (W = {WEIGHT_N / 1000:.1f} kN, L/W = {final_lift / WEIGHT_N:.2f})")
    v_stall = np.sqrt(2 * WEIGHT_N / (RHO * S_REF_M2 * 1.4))  # 失速速度 V_s = √(2W/(ρ·S·Cl_max))
    print(f"\n  参考失速速度:   {v_stall:.1f} m/s ({v_stall * MPS_TO_KT:.0f} kt, Cl=1.4)")
    print(f"  V_deck / V_stall: {v_deck / v_stall:.2f}")


def print_pitch_sensitivity(flat_m):
    print("\n" + "=" * 70)
    print(f"俯仰角敏感性（平直段 {flat_m} m）")
    print("=" * 70)
    print(f"  {'俯仰角':>6} | {'结果':>4} | {'V_deck':>10} | {'最小Vy':>8} | {'L/W':>8}")
    print("  " + "-" * 52)
    for pitch_deg in range(5, PITCH_MAX_DEG + 1, 2):
        ok, _, v_deck, _, min_vy, _, final_lift = simulate(flat_m, pitch_deg)
        result = "成功" if ok else "失败"
        lw = final_lift / WEIGHT_N if final_lift > 0 else 0.0
        print(f"  {pitch_deg:>5}° | {result:>4} | {v_deck:>8.1f} m/s | {min_vy:>8.2f} | {lw:>8.2f}")


def _main():
    print_config_summary()
    best = search_flat_length()
    print_best_result(best)
    if best:
        print_pitch_sensitivity(best['flat_m'])


if __name__ == "__main__":
    _main()
