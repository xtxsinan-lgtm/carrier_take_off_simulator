# ============================================================
# 短距滑跃起飞仿真 （起飞后喷口偏转版）
# ============================================================
import numpy as np
# ============================================================
# 初始化参数
# ============================================================
# 常数
g = 9.81                                          # 重力加速度，单位 m/s²
lbf_to_N = 4.44822                                # 磅力(lbf)到牛顿(N)的转换系数
pi = 3.1416                                       # 圆周率近似值
rho = 1.225                                       # 海平面标准大气密度，单位 kg/m³

# 垂起飞机参数
W_kg_mtow = 27200                                 # 短距起飞最大起飞重量(MTOW)，单位 kg。F-35B 约 27200，歼-35 约 28500
W_kg_A2A_load = 21620                             # 满内油+4枚中距弹时的起飞重量，单位 kg。F-35B 约 21620
W_kg = W_kg_A2A_load                                  # 当前仿真使用的起飞重量，这里取 MTOW
W = W_kg * g                                      # 飞机重力，单位 N（牛顿）
m = W_kg                                          # 飞机质量，单位 kg（质量=重量/重力加速度，这里直接用 kg 数值）

S_m2 = 42.7                                       # 机翼参考面积，单位 m²。F-35B 约 42.7 m²
b_m = 10.7                                        # 翼展，单位 m。F-35B 约 10.7 m
AR = b_m * b_m / S_m2                             # 机翼展弦比(Aspect Ratio) = 翼展² / 翼面积

nozzle_transition_speed = 95/2.5                  # 主喷管旋转角速度，单位 度/秒。3BSM 喷管 95° 旋转需 2.5 秒
T_main_stovl = 83260                              # STOVL 模式下主喷管可用推力，单位 N。F-35B 约 83260 N (≈18718 lbf)
efficiency_rollposts = 0.9                        # 滚转喷管效率。用于估算滚转喷管关闭时回收给主喷管的功率
                                                  # 若滚转喷管与主喷管排气速度一致（总效率最高），主喷管推力增量 ≈ T_rollposts / efficiency_rollposts
T_liftfan = 83260                                 # 升力风扇最大推力，单位 N。F-35B 约 83260 N
T_rollposts = 14600                               # 滚转喷管总推力，单位 N。F-35B 约 14600 N

e = 0.98                                          # Oswald 效率因子，描述机翼升阻效率，后掠翼典型值 0.8~0.9
Cl_taxi =0.604                                     # 地面滑行时的升力系数（襟翼放下，2度机翼安装角）
Cd0 = 0.039                                       # 地面滑行时的零升阻力系数（起落架、襟翼放下）
k = 1 / (pi * AR * e)                             # 诱导阻力因子，公式 k = 1/(π·AR·e)。AR 为展弦比，e 为 Oswald 效率
h = 1.96                                           # 机翼离地高度
phi_flat = (16 * h / b_m)**2 / (1 + (16 * h / b_m)**2)  # 地面效应修正因子，Torenbeek 模型。
                                                        # h=1.5m 为机翼离地高度，b_m 为翼展。值<1 表示地面效应减弱诱导阻力
lift_slope = 2.885                                  # 升力线斜率 dCl/dα，单位 /rad。典型后掠翼约 2.5~3.0 /rad

# 航母参数
SKI_JUMP_LENGTH = 37.0                            # 滑跃甲板长度，单位 m。如英国伊丽莎白女王级为 37m
SKI_JUMP_ANGLE = np.radians(12.5)                 # 滑跃甲板倾角，单位 弧度。12.5° 转换为弧度
mu = 0.03                                         # 地面滚动摩擦系数。航母甲板钢制表面约 0.02（低于铺装跑道 0.04）
V_wind_kt = 25
V_wind = V_wind_kt * 0.514444                            # 甲板风（逆风），单位 m/s。25 节 × 0.514444 = 12.86 m/s

# 预计算候选值（用于搜索）
THETA_NOZZLE_TAKEOFF_LIST_A = range(5, 71, 5)      # 起飞时主喷管偏转角度候选列表，单位 度。
FLAT_LENGTH_LIST_A = range(30, 201, 20)             # 平直段从 40m 到 200m，步长 20m
V_TRANS_LIST_A = range(5, 76, 10)                   # 喷口开始偏转时地速 15m/s 到 75m/s，步长 10m/s

THETA_NOZZLE_TAKEOFF_LIST_B = range(5, 31, 5)      # 起飞时主喷管偏转角度候选列表，单位 度。
FLAT_LENGTH_LIST_B = range(50, 501, 20)             # 平直段从 80m 到 300m，步长 20m

THETA_START_DEG = 0 # 初始喷管角度
fix_nozzle_time = 0.0 # 喷管角度固定时间
THETA_DEG_PITCH_LIST = range(10, 21, 2)   # 飞机俯仰角候选列表，单位 度。
THETA_DEG_NOZZLE_AIR_LIST = range(0, 31, 5)   # 离甲板后主喷管相对机身偏转角候选列表，单位 弧度。

# 预计算常量
T_main_ground = T_main_stovl + T_rollposts / efficiency_rollposts   # 地面滑行时主喷管可用推力。
                                                                    # 滚转喷管关闭，其功率回收给主喷管，故主喷管推力增加
ski_cos = np.cos(SKI_JUMP_ANGLE)                                    # 滑跃倾角的余弦值，预计算避免重复三角函数运算
ski_sin = np.sin(SKI_JUMP_ANGLE)                                    # 滑跃倾角的正弦值，预计算

print(f"起飞重量: {W_kg:,} kg")
print(f"展弦比: {AR:.3f} ")
print(f"甲板风: {V_wind_kt} kt = {V_wind:.2f} m/s")
print(f"地面效应因子 φ = {phi_flat:.3f}")
print(f"诱导阻力因子 k = {k:.3f}")

def simulate_optimal(flat_length, V_trans, theta_deg_takeoff, strategy,
                     theta_nozzle_air_deg, theta_pitch_deg, dt=0.02):
    """
    F-35B 滑跃甲板短距起飞全过程仿真函数

    【修改说明】离甲板后喷管和俯仰角固定，不再实时网格搜索调整。
    固定角度由调用方通过 theta_nozzle_air_deg 和 theta_pitch_air_deg 指定。

    参数:
        flat_length: 平直甲板长度，单位 m
        V_trans: 策略A的转换地速（开始偏转喷管的速度阈值），单位 m/s
        theta_deg_takeoff: 主喷管最终偏转角，单位 度
        strategy: 'A'（先水平加速再偏转）或 'B'（固定角度）
        theta_nozzle_air_deg: 离甲板后主喷管相对机身的固定偏转角，单位 度
        theta_pitch_air_deg: 离甲板后飞机俯仰角的固定值，单位 度
        dt: 仿真时间步长，单位 s

    返回:
        (success, x_deck, V_deck, Vy_final, min_Vy)
        success: 是否满足离甲板后 Vy>0 的约束
        x_deck: 离甲板时的水平位置，单位 m
        V_deck: 离甲板时的速度大小，单位 m/s
        Vy_final: 仿真结束时的垂直速度，单位 m/s
        min_Vy: 离甲板后经历的最小垂直速度，单位 m/s
    """
    theta_start = np.radians(THETA_START_DEG)
    theta_final = np.radians(theta_deg_takeoff)       # 将喷管最终偏转角从度转换为弧度
    trans_dur = (theta_deg_takeoff -  THETA_START_DEG)/ nozzle_transition_speed   # 喷管从 0° 偏转到 theta_final_deg 所需时间，单位 s
    # ==================== 阶段1: 平直甲板滑跑 ====================
    V, x, t = 0.0, 0.0, 0.0                         # 初始化地速 V=0，水平位置 x=0，时间 t=0
    transitioned, in_trans, trans_start = False, False, 0.0   # 状态标志
    theta_nozzle = theta_start                              # 当前喷管偏转角（相对机身），初始为 0°（水平向后）

    # 喷管偏转过程计算
    if strategy == 'A' and not transitioned and not in_trans and V >= V_trans and t >= fix_nozzle_time:
        # 策略A：当速度达到转换阈值且未开始/完成过渡时，启动喷管偏转过渡
        in_trans = True                         # 标记进入过渡状态
        trans_start = t                         # 记录过渡开始时刻
    if in_trans:
        # 正在执行喷管偏转过渡
        if trans_dur != 0:
            ratio = (t - trans_start) / trans_dur   # 过渡进度比例，0→1
        if trans_dur == 0 or ratio >= 1.0:
            ratio = 1.0                         # 限制不超过 100%
            in_trans = False                    # 过渡结束
            transitioned = True                 # 标记已完成过渡
        theta_nozzle = theta_start + (theta_final - theta_start) * ratio      # 当前喷管角 = 最终角 × 过渡比例（线性插值）
    elif strategy == 'B' or transitioned:
        # 策略B 全程固定角度，或策略A已完成过渡后保持最终角度
        theta_nozzle = theta_final
        
    while x < flat_length and t < 30:               # 当飞机未跑出平直段且时间未超 30 秒时循环
        V_a = V + V_wind                            # 空速 = 地速 + 甲板风（逆风叠加）
        q = 0.5 * rho * V_a * V_a                   # 动压 q = ½·ρ·V²，单位 Pa (N/m²)
        T_h = T_main_ground * np.cos(theta_nozzle)  # 主喷管水平推力分量 = 总推力 × cos(喷管角)
        T_v = T_main_ground * np.sin(theta_nozzle) + T_liftfan   # 垂直向上总推力 = 主喷管垂直分量 + 升力风扇（始终全开）
        L = q * S_m2 * Cl_taxi                        # 机翼升力 = 动压 × 翼面积 × 滑行升力系数
        D = q * S_m2 * (Cd0 + k * Cl_taxi * Cl_taxi * phi_flat)      # 总阻力
        N = W - L - T_v                             # 地面正压力 = 重力 - 升力 - 垂直推力
        if N < 0: N = 0                             # 正压力不能为负
        a = (T_h - D - mu * N) / m                  # 水平加速度
        V = max(V + a * dt, 0)                      # 更新地速
        x += V * dt                                 # 更新水平位置
        t += dt                                     # 时间推进

    # ==================== 阶段2: 滑跃甲板滑跑 ====================
    s = 0.0                                         # 沿滑跃斜面滑行的距离，初始为 0
    while s < SKI_JUMP_LENGTH and t < 30:           # 当未跑完滑跃段且时间未超时
        V_a = V + V_wind * ski_cos                  # 沿斜面方向的空速分量
        q = 0.5 * rho * V_a * V_a                   # 动压计算
        phi_s = phi_flat * (1 - s/SKI_JUMP_LENGTH) + 1.0 * (s/SKI_JUMP_LENGTH)   # 地面效应随高度线性衰减
        T_s = T_main_ground * np.cos(theta_nozzle)  # 主喷管推力沿斜面方向的分量
        T_n = T_main_ground * np.sin(theta_nozzle) + T_liftfan   # 主喷管+升力风扇垂直于斜面向上的分量
        L = q * S_m2 * Cl_taxi                        # 机翼升力（垂直于斜面）
        D = q * S_m2 * (Cd0 + k * Cl_taxi * Cl_taxi * phi_s)         # 总阻力
        N = W * ski_cos - L - T_n                   # 垂直于斜面的正压力
        if N < 0: N = 0                             # 正压力下限为 0
        a = (T_s - D - W * ski_sin - mu * N) / m    # 沿斜面加速度
        V = max(V + a * dt, 0)                      # 更新沿斜面速度
        s += V * dt                                 # 沿斜面滑行距离累加
        x += V * ski_cos * dt                       # 水平位置增量
        t += dt                                     # 时间推进

    if s < SKI_JUMP_LENGTH * 0.99:
        # 如果滑跃段未走完，判定起飞失败
        return False, x, V, 0, 0

    V_deck = V                                      # 离甲板瞬间的速度大小
    Vx = V * ski_cos                                # 离甲板时水平速度分量
    Vy = V * ski_sin                                # 离甲板时垂直速度分量
    x_deck = x                                      # 离甲板时的总水平位置

    # ==================== 阶段3: 离甲板后自由飞行（固定角度控制）====================
    t_air = 0.0                                     # 离甲板后飞行时间计时器
    min_Vy = Vy                                     # 记录离甲板后经历的最小垂直速度

    if Vy < 0:
        return False, x_deck, V_deck, Vy, min_Vy

    # 固定控制角度（不再实时搜索）
    theta_p = np.radians(theta_pitch_deg)     # 离甲板后固定俯仰角（弧度）
    theta_final_air = np.radians(theta_nozzle_air_deg)                      # 转换后喷管偏转角
    trans_dur_air = (theta_nozzle_air_deg - theta_deg_takeoff) / nozzle_transition_speed   # 喷管从 theta_deg_takeoff 偏转到 theta_nozzle_air_deg 所需时间，单位 s
    # 喷管偏转过程计算
    if not transitioned and not in_trans:
        # 策略A：当速度达到转换阈值且未开始/完成过渡时，启动喷管偏转过渡
        in_trans_air = True                         # 标记进入过渡状态
        theta_nozzle_air = theta_final
    if in_trans:
        # 正在执行喷管偏转过渡
        if trans_dur_air != 0:
            ratio_air = t_air / trans_dur_air   # 过渡进度比例，0→1
        else:
            ratio_air = 1.0
        if ratio_air >= 1.0:
            ratio_air = 1.0                         # 限制不超过 100%
            in_trans_air = False                    # 过渡结束
            transitioned_air = True                 # 标记已完成过渡
        theta_nozzle_air = theta_final_air * ratio_air      # 当前喷管角 = 最终角 × 过渡比例（线性插值）
    elif transitioned:
        # 策略B 全程固定角度，或策略A已完成过渡后保持最终角度
        theta_nozzle_air = theta_final_air
        
    while t_air < 3.0:                              # 最多仿真离甲板后 3 秒
        V_spd = np.sqrt(Vx*Vx + Vy*Vy)              # 当前合速度大小
        gamma = np.arctan2(Vy, Vx) if V_spd > 0.1 else 0   # 航迹角
        V_ax = Vx + V_wind                          # 水平空速
        V_a = np.sqrt(V_ax*V_ax + Vy*Vy)            # 合空速大小
        q = 0.5 * rho * V_a * V_a                   # 动压

        # 使用固定角度计算气动力和推力
        alpha_eff = theta_p - gamma                 # 有效迎角
        if abs(alpha_eff) > 20 * np.pi / 180:
            # 固定角度导致迎角超限，判定不可行
            return False, x_deck, V_deck, Vy, min_Vy

        Cl = Cl_taxi + lift_slope * alpha_eff       # 升力系数
        if Cl > 1.8: Cl = 1.8                       # 上限
        if Cl < 0.2: Cl = 0.2                       # 下限

        Cd = Cd0 + k * Cl * Cl                      # 阻力系数（离甲板后无地面效应）
        L = q * S_m2 * Cl                           # 升力大小
        D = q * S_m2 * Cd                           # 阻力大小

        thrust_ang = theta_p + theta_nozzle_air                # 主喷管推力向量相对水平面的绝对角度
        T_mx = T_main_stovl * np.cos(thrust_ang)     # 主喷管推力水平分量
        T_my = T_main_stovl * np.sin(thrust_ang)     # 主喷管推力垂直分量
        T_vx = -(T_liftfan + T_rollposts) * np.sin(theta_p)   # 升力风扇+滚转喷管的水平分量
        T_vy = (T_liftfan + T_rollposts) * np.cos(theta_p)    # 升力风扇+滚转喷管的垂直分量

        Lx = -L * np.sin(gamma)                     # 升力的水平分量
        Ly = L * np.cos(gamma)                      # 升力的垂直分量
        Dx = -D * np.cos(gamma)                     # 阻力的水平分量
        Dy = -D * np.sin(gamma)                     # 阻力的垂直分量

        dVx = (T_mx + T_vx + Lx + Dx) / m           # 水平加速度
        dVy = (T_my + T_vy + Ly + Dy - W) / m       # 垂直加速度

        # 安全检查：如果垂直加速度极负，提前判定失败
        if dVy < -15:
            return False, x_deck, V_deck, Vy, min_Vy

        Vx += dVx * dt                              # 更新水平速度
        Vy += dVy * dt                              # 更新垂直速度
        t_air += dt                                 # 时间累加
        min_Vy = min(min_Vy, Vy)                    # 更新最小垂直速度

        if Vy <= 0:
            # 垂直速度降为 0 或负值，起飞失败
            return False, x_deck, V_deck, Vy, min_Vy
        if L + T_vy >= W and Vy > 2 and t_air > 0.3:
            # 安全判据：升力 ≥ 重力 且垂直速度 >2 m/s 且已离甲板超过 0.3 秒
            break

    return True, x_deck, V_deck, Vy, min_Vy


# ============================================================
# 扫描策略A：寻找最优参数组合（含离甲板后固定角度）
# ============================================================
print("=" * 60)
print("扫描策略A 起飞前偏转喷口")
print("=" * 60)



def search_a():
    best_A = None                                     # 存储策略A的最优结果元组
    results_A = []                                    # 存储策略A所有成功结果
    for flat in FLAT_LENGTH_LIST_A:                 # 平直段长度 
        for theta_deg in THETA_NOZZLE_TAKEOFF_LIST_A:       # 起飞喷管最终偏转角
            for Vt in V_TRANS_LIST_A:                       # 转换地速
                for theta_n_air_deg in THETA_DEG_NOZZLE_AIR_LIST:    # 离甲板后固定喷管角（粗搜 0°~90°，步长10°）
                    for theta_p_deg in THETA_DEG_PITCH_LIST:   # 离甲板后固定俯仰角（粗搜 0°~20°，步长5°）
                        s, xd, vd, vyd, mvy = simulate_optimal(
                            flat, Vt, theta_deg, 'A', theta_n_air_deg, theta_p_deg)
                        if s:
                            total = flat + SKI_JUMP_LENGTH * ski_cos
                            results_A.append((total, flat, Vt, theta_deg,
                                              theta_n_air_deg, theta_p_deg, vd, vyd, mvy))
                            if best_A is None or total < best_A[0]:
                                return (total, flat, Vt, theta_deg, theta_n_air_deg, theta_p_deg, vd, vyd, mvy)
    return None

# 细化搜索
def fine_tune_a():
    for flat in range(max(int(best_A[1]) - 20, 0), int(best_A[1]), 2):
        for Vt in range(best_A[2] - 10, best_A[2] + 10, 2):
            for th in range(best_A[3] - 5, best_A[3] + 6, 2):
                if th > 90: continue
                for theta_n_air_deg in range(max(best_A[4] - 5, 0), min(best_A[4] + 6, 91), 2):
                    for theta_p_deg in range(max(best_A[5] - 5, 0), min(best_A[5] + 6, 21), 1):
                        s, xd, vd, vyd, mvy = simulate_optimal(
                            flat, Vt, th, 'A', theta_n_air_deg, theta_p_deg)
                        if s:
                            total = flat + SKI_JUMP_LENGTH * ski_cos
                            if total < best_A[0]:
                                return (total, flat, Vt, th,
                                          theta_n_air_deg, theta_p_deg, vd, vyd, mvy)
    return None

best_A = search_a()

if best_A:
    print(f"起始喷管角度={THETA_START_DEG}, 固定喷管时间={fix_nozzle_time}")
    print(f"★ 最优: 总距={best_A[0]:.1f}m ({best_A[0]*3.28084:.0f}ft)")
    print(f"        平直段={best_A[1]:.0f}m 开始偏转地速={best_A[2]}m/s 起飞时喷管偏转角度={best_A[3]}°")
    print(f"        离甲板后最终喷管偏转角度={best_A[4]}° 固定俯仰角={best_A[5]}°")
    print(f"        离甲板速度={best_A[6]:.1f}m/s")
    print("细化搜索")
    best_A = fine_tune_a()
    print(f"★ 最优: 总距={best_A[0]:.1f}m ({best_A[0]*3.28084:.0f}ft)")
    print(f"        平直段={best_A[1]:.0f}m 开始偏转地速={best_A[2]}m/s 起飞时喷管偏转角度={best_A[3]}°")
    print(f"        离甲板后最终喷管偏转角度={best_A[4]}° 固定俯仰角={best_A[5]}°")
    print(f"        离甲板速度={best_A[6]:.1f}m/s")

# ============================================================
# 扫描策略B：固定喷口角度的最优参数（含离甲板后固定角度）
# ============================================================
print("\n" + "=" * 60)
print("扫描策略B 滑跑时固定喷口角度")
print("=" * 60)

def search_b():
    best_B = None
    for theta_deg in THETA_NOZZLE_TAKEOFF_LIST_B:
        for flat in FLAT_LENGTH_LIST_B:
            for theta_n_air_deg in THETA_DEG_NOZZLE_AIR_LIST:
                for theta_p_deg in THETA_DEG_PITCH_LIST:
                    s, xd, vd, vyd, mvy = simulate_optimal(
                        flat, 0, theta_deg, 'B', theta_n_air_deg, theta_p_deg)
                    if s:
                        total = flat + SKI_JUMP_LENGTH * ski_cos
                        if best_B is None or total < best_B[0]:
                            return (total, flat, theta_deg, theta_n_air_deg, theta_p_deg, vd, vyd, mvy)
    return None

best_B = search_b()
# 细化搜索
def fine_tune_b():
    for flat in range(max(int(best_B[1])-20, 0), int(best_B[1]), 1):
        for th in range(best_B[2] - 5, best_B[2] + 6, 1):
            if th > 90: continue
            for theta_n_air_deg in range(max(best_B[3] - 5, 0), min(best_B[3] + 6, 91), 1):
                for theta_p_deg in range(max(best_B[4] - 5, 0), min(best_B[4] + 6, 21), 1):
                    s, xd, vd, vyd, mvy = simulate_optimal(
                        flat, 0, th, 'B', theta_p_deg, theta_p_deg)
                    if s:
                        total = flat + SKI_JUMP_LENGTH * ski_cos
                        if total < best_B[0]:
                            return (total, flat, th, theta_n_air_deg, theta_p_deg, vd, vyd, mvy)
    return none

if best_B:
    print(f"★ 最优: 总距={best_B[0]:.1f}m ({best_B[0]*3.28084:.0f}ft)")
    print(f"        平直段={best_B[1]:.0f}m 喷管固定偏转角度={best_B[2]}°")
    print(f"        离甲板后最终喷管偏转角度={best_B[3]}° 固定俯仰角={best_B[4]}°")
    print(f"        离甲板速度={best_B[5]:.1f}m/s")
    print("细化搜索")
    best_B = fine_tune_b()
    print(f"★ 最优: 总距={best_B[0]:.1f}m ({best_B[0]*3.28084:.0f}ft)")
    print(f"        平直段={best_B[1]:.0f}m 喷管固定偏转角度={best_B[2]}°")
    print(f"        离甲板后最终喷管偏转角度={best_B[3]}° 固定俯仰角={best_B[4]}°")
    print(f"        离甲板速度={best_B[5]:.1f}m/s")

# ============================================================
# 对比总结
# ============================================================
print("\n" + "=" * 60)
print("对比总结")
print("=" * 60)
if best_A and best_B:
    diff = best_B[0] - best_A[0]
    print(f"策略A: {best_A[0]:.1f} m ({best_A[0]*3.28084:.0f} ft)")
    print(f"       平直段={best_A[1]:.0f}m, 开始偏转地速={best_A[2]}m/s, 起飞时喷管偏转角度={best_A[3]}°")
    print(f"       离甲板后最终喷管偏转角度={best_A[4]}°, 固定俯仰角={best_A[5]}°")
    print(f"策略B: {best_B[0]:.1f} m ({best_B[0]*3.28084:.0f} ft)")
    print(f"       平直段={best_B[1]:.0f}m, 喷管固定偏转角度={best_B[2]}°")
    print(f"       离甲板后最终喷管偏转角度={best_B[3]}°, 固定俯仰角={best_B[4]}°")
    print(f"策略A 比策略B 短: {diff:.1f} m ({diff/best_B[0]*100:.1f}%)")