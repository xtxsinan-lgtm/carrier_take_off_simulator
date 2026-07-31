# ============================================================
# 滑跃起飞仿真
# ============================================================
import numpy as np

# ============================================================
# 参数初始化
# ============================================================
# 常数
g = 9.81                                          # 重力加速度，单位 m/s²
rho = 1.225                                       # 海平面标准大气密度，单位 kg/m³

# 固定翼舰载机参数（以典型重型舰载战斗机为参考，如歼-15 / Su-33）
W_kg = 27200                                      # 最大起飞重量，单位 kg。
                                                  # 歼-35 29.5吨，歼-15T 35.9吨，歼-15 33吨, F-35B 27.2吨。
                                                  #满内油4枚中距弹歼-35 24.44吨，歼-15T 29.44吨, F-35B 21.52吨 
W = W_kg * g                                      # 飞机重力，单位 N
m = W_kg                                          # 飞机质量，单位 kg

S_m2 = 42.74                                       # 机翼参考面积，单位 m²。歼-15 67.84 m 歼-35 67.8 F-35B 42.74 
b_m = 10.7                                       # 翼展，单位 m。歼-15 14.7 m 歼-35 13.6 m F-35B 10.7
AR = b_m * b_m / S_m2                             # 机翼展弦比 = 翼展² / 翼面积

e = 0.98                                          # Oswald 效率因子。后掠翼战斗机典型值 0.8~0.9，歼-15T 0.86 歼-35 0.95 F-35B 0.98
k = 1 / (np.pi * AR * e)                          # 诱导阻力因子，k = 1/(π·AR·e)

T_max = 182000 * 0.94                  # 发动机最大水平推力，单位 N。歼-35 186.2kN。歼-15T 264kN。歼-15 250kN。F-35B 182kN。0.94为30度温度修正
Cl_taxi = 0.604                     # 地面滑行升力系数。小迎角、襟翼放下但尚未拉杆 歼-15 0.633 歼-35 0.596 F-35B 0.604
lift_slope = 2.885                  # 升力线斜率 dCl/dα，单位 /rad。典型后掠翼约 2.5~3.0 /rad，歼-35 2.855，歼-15 3.024，F-35B 2.885
Cd0 = 0.039                      # 零升阻力系数。含起落架、表面粗糙度。 歼-15 0.0475  歼-35 0.039 F-35B 0.039
                                    # 注意：全程使用同一 Cd0，离甲板后襟翼和起落架均不收

h = 1.96                                          # 机翼平均离地高度，单位 m 歼-15 2.55 歼-35 1.96 F-35B 1.96 
phi_flat = (16 * h / b_m)**2 / (1 + (16 * h / b_m)**2)  # 地面效应修正因子，Torenbeek 模型。
                                                        # 值 < 1 表示地面效应减弱诱导阻力

# 航母滑跃甲板参数
SKI_JUMP_LENGTH = 37                           # 滑跃甲板长度，单位 m。如伊丽莎白女王级为 37 m, 库兹涅佐夫级为 50 m
SKI_JUMP_ANGLE_DEG = 12.5                         # 滑跃甲板倾角，单位 度。 如伊丽莎白女王级为 12.5 m, 库兹涅佐夫级为 14 m
SKI_JUMP_ANGLE = np.radians(SKI_JUMP_ANGLE_DEG)   # 滑跃倾角转换为å弧度
mu = 0.03                                         # 甲板滚动摩擦系数。钢制航母甲板约 0.02
V_wind_kt = 25
V_wind = V_wind_kt * 0.514444                            # 甲板风（逆风），单位 m/s。25 节 × 0.514444 = 12.86 m/s

# 预计算三角函数，避免循环内重复计算
ski_cos = np.cos(SKI_JUMP_ANGLE)                  # 滑跃倾角余弦值
ski_sin = np.sin(SKI_JUMP_ANGLE)                  # 滑跃倾角正弦值

# 离甲板后俯仰角搜索范围（单位：度）
# 俯仰角 = 机身纵轴与水平面的夹角
# 离甲板瞬间机身沿斜面，俯仰角约 15°；
PITCH_SEARCH_MIN = 10                             # 最小搜索俯仰角，度
PITCH_SEARCH_MAX = 20                             # 最大搜索俯仰角，度
PITCH_SEARCH_STEP = 1                             # 搜索步长，度

print(f"起飞重量: {W_kg:,} kg")
print(f"展弦比: {AR:.3f} ")
print(f"甲板风: {V_wind_kt} kt = {V_wind:.2f} m/s")
print(f"地面效应因子 φ = {phi_flat:.3f}")
print(f"诱导阻力因子 k = {k:.3f}")

def simulate_fixed_wing_ski_jump(flat_length, theta_pitch_deg, dt=0.02, max_t=30):
    """
    固定翼飞机滑跃甲板起飞全过程仿真

    参数:
        flat_length: 平直甲板长度，单位 m
        theta_pitch_deg: 离甲板后固定俯仰角，单位 度。
                        俯仰角 = 机身纵轴与水平面的夹角。
                        离甲板后飞行员保持此俯仰角不变，通过改变迎角来调节升力。
        dt: 仿真时间步长，单位 s
        max_t: 最大仿真时间，单位 s

    返回:
        (success, x_deck, V_deck, Vy_final, min_Vy, t_deck, final_L)
        success: 是否满足离甲板后 Vy>0 且最终升力≥重力的约束
        x_deck: 离甲板时的水平位置，单位 m
        V_deck: 离甲板时的速度大小，单位 m/s
        Vy_final: 仿真结束时的垂直速度，单位 m/s
        min_Vy: 离甲板后经历的最小垂直速度，单位 m/s
        t_deck: 离甲板时刻，单位 s
        final_L: 仿真结束时的升力值，单位 N
    """

    # ==================== 阶段1: 平直甲板滑跑 ====================
    # 机身水平（俯仰角 ≈ 0°），速度水平，迎角 ≈ 0，使用 Cl_taxi
    V = 0.0                                         # 地速（沿甲板方向），初始为 0
    x = 0.0                                         # 水平位置，初始为 0
    t = 0.0                                         # 仿真时间，初始为 0

    while x < flat_length and t < max_t:
        V_a = V + V_wind                            # 空速 = 地速 + 甲板风（逆风叠加）
        q = 0.5 * rho * V_a * V_a                   # 动压 q = ½·ρ·V²，单位 Pa

        L = q * S_m2 * Cl_taxi                      # 机翼升力 = 动压 × 翼面积 × 滑行升力系数
        # 阻力 = 动压 × 翼面积 × (零升阻力 + 诱导阻力 × 地面效应修正)
        D = q * S_m2 * (Cd0 + k * Cl_taxi * Cl_taxi * phi_flat)

        N = W - L                                   # 地面正压力 = 重力 - 升力（无垂直推力辅助）
        if N < 0: 
            N = 0                                   # 正压力下限为 0（已离地）

        # 水平加速度 = (发动机推力 - 气动阻力 - 轮子的滚动摩擦阻力) / 质量
        a = (T_max - D - mu * N) / m

        V = max(V + a * dt, 0)                      # 更新地速，限制不小于 0（防止倒退）
        x += V * dt                                 # 更新水平位置
        t += dt                                     # 时间推进

    # ==================== 阶段2: 滑跃甲板滑跑 ====================
    # 机身沿斜面（俯仰角 = 滑跃角 ≈ 12.5°），速度沿斜面，迎角仍 ≈ 0，继续使用 Cl_taxi
    s = 0.0                                         # 沿滑跃斜面滑行的距离，初始为 0

    while s < SKI_JUMP_LENGTH and t < max_t:
        # 沿斜面方向的空速 = 地速 + 风速在斜面方向的投影
        V_a = V + V_wind * ski_cos
        q = 0.5 * rho * V_a * V_a                   # 动压

        # 地面效应随高度线性衰减：s=0 时全地面效应，s=L 时无地面效应
        phi_s = phi_flat * (1 - s / SKI_JUMP_LENGTH) + 1.0 * (s / SKI_JUMP_LENGTH)

        L = q * S_m2 * Cl_taxi                      # 升力（垂直于斜面）
        # 阻力（沿斜面向后），Cd0 全程不变
        D = q * S_m2 * (Cd0 + k * Cl_taxi * Cl_taxi * phi_s)

        # 垂直于斜面的正压力 = 重力垂直分量 - 升力（无垂直推力）
        N = W * ski_cos - L
        if N < 0: 
            N = 0

        # 沿斜面加速度 = (推力 - 阻力 - 重力沿斜面向下分量 - 摩擦阻力) / 质量
        # 发动机推力始终水平向后。沿斜面方向的分量 = T_max（假设机身轴线与斜面平行）
        a = (T_max - D - W * ski_sin - mu * N) / m

        V = max(V + a * dt, 0)                      # 更新沿斜面速度
        s += V * dt                                 # 沿斜面距离累加
        x += V * ski_cos * dt                       # 水平位置增量 = 斜面速度 × cos(倾角) × dt
        t += dt                                     # 时间推进

    # 检查是否成功跑完滑跃段（速度未在斜面上耗尽）
    if s < SKI_JUMP_LENGTH * 0.99:
        return False, x, V, 0, 0, t, 0

    # 记录离甲板瞬间状态
    V_deck = V                                      # 离甲板速度大小（沿斜面方向）
    Vx = V * ski_cos                                # 水平速度分量
    Vy = V * ski_sin                                # 垂直速度分量（滑跃甲板赋予的初始上抛速度）
    x_deck = x                                      # 离甲板水平位置
    t_deck = t

    # ==================== 阶段3: 离甲板后自由飞行 ====================
    # 离甲板后，飞行员将俯仰角固定为 theta_pitch_deg，保持不变。
    # 升力系数由有效迎角决定：Cl = Cl_taxi + lift_slope * α_eff
    # 其中有效迎角 α_eff = 俯仰角 - 航迹角
    theta_pitch = np.radians(theta_pitch_deg)       # 固定俯仰角，弧度
    t_air = 0.0                                     # 离甲板后飞行时间计时器
    min_Vy = Vy                                     # 记录最小垂直速度

    # 安全检查：离甲板时必须有正的垂直速度
    if Vy <= 0:
        return False, x_deck, V_deck, Vy, min_Vy, t_deck, 0

    final_L = 0                                     # 记录最终升力值

    while t_air < 5.0 and t < max_t:                # 最多仿真离甲板后 5 秒
        V_spd = np.sqrt(Vx * Vx + Vy * Vy)          # 当前合速度大小
        gamma = np.arctan2(Vy, Vx) if V_spd > 0.1 else 0  # 航迹角（速度向量与水平面夹角）

        V_ax = Vx + V_wind                          # 水平空速 = 水平地速 + 甲板风
        V_a = np.sqrt(V_ax * V_ax + Vy * Vy)        # 合空速大小
        q = 0.5 * rho * V_a * V_a                   # 动压

        # 有效迎角 = 固定俯仰角 - 当前航迹角
        # 俯仰角是机身纵轴与水平面的夹角，航迹角是速度向量与水平面的夹角
        # 两者之差即为机翼实际迎角
        alpha_eff = theta_pitch - gamma

        # 升力系数 = 基准滑行升力系数 + 升力线斜率 × 有效迎角
        Cl = Cl_taxi + lift_slope * alpha_eff
        if Cl > 1.8: 
            Cl = 1.8                                # 升力系数上限（失速边界）
        if Cl < 0.0: 
            Cl = 0.0                                # 升力系数下限（负迎角时升力为0或负）

        # 阻力系数 = 零升阻力 + 诱导阻力（Cd0 全程不变，起落架和襟翼均不收回）
        Cd = Cd0 + k * Cl * Cl

        L = q * S_m2 * Cl                           # 升力大小（垂直于空速方向）
        D = q * S_m2 * Cd                           # 阻力大小（与空速方向相反）
        final_L = L                                 # 记录当前升力

        # 升力分解：垂直于空速，向上偏前
        Lx = -L * np.sin(gamma)                     # 升力水平分量（向后，当 γ>0 时 sin(γ)>0，故加负号）
        Ly = L * np.cos(gamma)                      # 升力垂直分量（向上）

        # 阻力分解：与空速方向相反
        Dx = -D * np.cos(gamma)                     # 阻力水平分量（向后）
        Dy = -D * np.sin(gamma)                     # 阻力垂直分量（向下）

        # 运动方程（推力纯水平向后，不随俯仰角变化）
        dVx = (T_max + Lx + Dx) / m                 # 水平加速度
        dVy = (Ly + Dy - W) / m                     # 垂直加速度 = (升力垂直分量 - 阻力垂直分量 - 重力) / 质量

        Vx += dVx * dt                              # 更新水平速度
        Vy += dVy * dt                              # 更新垂直速度
        t_air += dt                                 # 离甲板后时间累加
        t += dt

        min_Vy = min(min_Vy, Vy)                    # 更新最小垂直速度记录

        # 约束检查1：垂直速度不能降为 0（否则飞机会下坠触海）
        if Vy <= 0:
            return False, x_deck, V_deck, Vy, min_Vy, t_deck, final_L

        # 约束检查2：升力必须足够大以维持飞行
        # 当升力 ≥ 95% 重力且仍有正的爬升率时，认为已安全建立飞行姿态
        if L >= W * 0.95 and Vy > 1.0 and t_air > 0.5:
            break

    return True, x_deck, V_deck, Vy, min_Vy, t_deck, final_L


# ============================================================
# 扫描最小平直段长度（对每个平直段长度搜索最优俯仰角）
# ============================================================
print("=" * 70)
print("扫描最小平直段长度（同时搜索最优俯仰角）")
print("=" * 70)

best_overall = None                               # 全局最优结果

# 粗扫描：平直段从 0 m 到 400 m，步长 20 m
for flat in range(0, 401, 20):
    best_for_this_flat = None                     # 当前平直段长度下的最优俯仰角结果
    best_min_Vy = -1e9                            # 当前平直段下的最大最小Vy（安全性指标）

    # 对该平直段长度，搜索最优固定俯仰角
    for pitch_deg in range(PITCH_SEARCH_MIN, PITCH_SEARCH_MAX + 1, PITCH_SEARCH_STEP):
        s, xd, vd, vyd, mvy, td, fL = simulate_fixed_wing_ski_jump(flat, pitch_deg)
        if s:
            # 选择使最小Vy最大的俯仰角（最安全）
            if mvy > best_min_Vy:
                best_min_Vy = mvy
                best_for_this_flat = (pitch_deg, xd, vd, vyd, mvy, td, fL)

    total_dist = flat + SKI_JUMP_LENGTH * ski_cos   # 总起飞距离 = 平直段 + 滑跃段水平投影

    if best_for_this_flat:
        p_deg, xd, vd, vyd, mvy, td, fL = best_for_this_flat
        status = f"✓ 成功 | 最优俯仰角={p_deg}° | 最小Vy={mvy:.2f} m/s"
        if best_overall is None or total_dist < best_overall[0]:
            best_overall = (total_dist, flat, p_deg, vd, vyd, mvy, td, fL)
    else:
        status = "✗ 失败（无合适俯仰角）"

    print(f"  平直段 {flat:3d} m | 总距 {total_dist:6.1f} m | {status}")

# 细化搜索：在最优平直段附近 ±20 m 范围，步长 2 m；俯仰角 ±3° 范围，步长 1°
if best_overall:
    print(f"\n  粗扫描最优: 平直段={best_overall[1]} m, 总距={best_overall[0]:.1f} m, 俯仰角={best_overall[2]}°")
    print("  细化扫描中...")

    for flat in range(max(int(best_overall[1]) - 20, 0), int(best_overall[1]) + 21, 2):
        best_for_this_flat = None
        best_min_Vy = -1e9

        for pitch_deg in range(max(best_overall[2] - 3, PITCH_SEARCH_MIN), 
                                min(best_overall[2] + 4, PITCH_SEARCH_MAX + 1), 1):
            s, xd, vd, vyd, mvy, td, fL = simulate_fixed_wing_ski_jump(flat, pitch_deg)
            if s and mvy > best_min_Vy:
                best_min_Vy = mvy
                best_for_this_flat = (pitch_deg, xd, vd, vyd, mvy, td, fL)

        if best_for_this_flat:
            total_dist = flat + SKI_JUMP_LENGTH * ski_cos
            if total_dist < best_overall[0]:
                p_deg, xd, vd, vyd, mvy, td, fL = best_for_this_flat
                best_overall = (total_dist, flat, p_deg, vd, vyd, mvy, td, fL)

# ============================================================
# 输出最优结果
# ============================================================
print("\n" + "=" * 70)
print("最优结果")
print("=" * 70)

if best_overall:
    total, flat, p_deg, vd, vyd, mvy, td, fL = best_overall
    print(f"  最小平直段长度: {flat:.0f} m")
    print(f"  总起飞距离:     {total:.1f} m ({total * 3.28084:.0f} ft)")
    print(f"  最优固定俯仰角: {p_deg}°")
    print(f"  离甲板速度:     {vd:.1f} m/s ({vd * 1.94384:.0f} kt)")
    print(f"  离甲板垂直速度: {vd * ski_sin:.1f} m/s")
    print(f"  离甲板后最小Vy: {mvy:.2f} m/s")
    print(f"  离甲板时间:     {td:.2f} s")
    print(f"  最终升力:       {fL/1000:.1f} kN (重力 {W/1000:.1f} kN, 比值 {fL/W:.2f})")

    # 计算失速速度参考值
    V_stall = np.sqrt(2 * W / (rho * S_m2 * 1.4))
    print(f"\n  参考失速速度(Cl=1.4): {V_stall:.1f} m/s ({V_stall * 1.94384:.0f} kt)")
    print(f"  离甲板速度 / 失速速度: {vd / V_stall:.2f}")
else:
    print("  未找到可行解（推力不足或甲板太短）")

# ============================================================
# 俯仰角敏感性分析：展示不同俯仰角对安全性的影响
# ============================================================
print("\n" + "=" * 70)
print("俯仰角敏感性分析（固定平直段长度 = {} m）".format(best_overall[1] if best_overall else 200))
print("=" * 70)

test_flat = best_overall[1] if best_overall else 200
print(f"  平直段长度: {test_flat} m")
print(f"  {'俯仰角':>8} | {'结果':>6} | {'离甲板速度':>10} | {'最小Vy':>8} | {'最终升力/重力':>12}")
print("  " + "-" * 60)

for pitch_deg in range(5, 36, 2):
    s, xd, vd, vyd, mvy, td, fL = simulate_fixed_wing_ski_jump(test_flat, pitch_deg)
    result = "成功" if s else "失败"
    L_ratio = fL / W if fL > 0 else 0
    print(f"  {pitch_deg:>6}° | {result:>6} | {vd:>8.1f} m/s | {mvy:>8.2f} | {L_ratio:>12.2f}")