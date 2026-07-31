# ============================================================
# 短距起飞仿真
# ============================================================
import numpy as np

# ============================================================
# 参数初始化
# ============================================================

# 常数
g = 9.81
lbf_to_N = 4.44822

pi = 3.1416
mu = 0.02 # 地面滚动摩擦系数
rho = 1.225 # 空气密度

# 垂起飞机参数
W_kg_mtow = 27200  # 短距起飞最大起飞重量 F35B 27200 F135歼35 28500 混动歼35 28500
W_kg_A2A_load = 21620  # 满内油4枚中距弹时起飞重量 F35B 21620 F135歼35 21250 混动歼35 22280
W_kg = W_kg_A2A_load # 自行选择要计算的重量
W = W_kg * g  # 重力
m = W_kg  # kg

S_m2 = 42.7 # 翼面积
b_m = 10.7 # 翼展
h = 1.96 # 翼高
AR = b_m * b_m / S_m2 # 展弦比

nozzle_transition_speed = 95/2.5 #主喷管旋转95度需要2.5秒
T_main_stovl = 83260  # STOVL 模式下主喷管可用推力 F35B 83260 F35B早期设计 80000 F135歼35 83260 混动歼35 145400
efficiency_rollposts = 0.9 # 滚转喷管效率，用于倒推主喷管抽功，在主喷管和滚转喷管排气速度一致（此时总效率最高），可以近似认为滚转喷管不使用时，主喷管推力的增加值为 T_rollposts / efficiency_rollposts
T_liftfan = 83260 #  F35B 83260 F35B早期设计 89000 F135歼35 83260 混动歼35 96900
T_rollposts = 14600 #  F35B 14600 F35B早期设计 17000 F135歼35 14600

e = 0.85 # Oswald 效率，后掠翼战斗机典型值 0.8~0.9
Cl_to = 0.604 # 滑行升力系数
Cl_takeoff = 1.234 # 拉杆抬前轮时升力系数
Cd0 = 0.039 # 地面滑行时零升阻力系数
k = 1 / (pi * AR *e)  # 诱导阻力因子
phi = (16 * h / b_m)**2 / (1 + (16 * h / b_m)**2) # 地面效应修正因子，公式来自 Torenbeek 地面效应模型

# 搜索参数
final_deg_search_start = 20 # 最终喷口偏转角度搜索下界
final_deg_search_end = 90 # 最终喷口偏转角度搜索上界
deg_search_step = 5 # 最终喷口偏转角度搜索步长
deg_fine_tune_radius = 10 # 最终喷口偏转角度精细搜索半径
deg_fine_tune_step = 1 # 最终喷口偏转角度精细搜索步长
v_trans_search_start = 15  # 喷口开始偏转地速搜索下界
v_trans_search_end = 70 # 喷口开始偏转地速搜索上界
v_trans_search_step = 5 # 喷口开始偏转地速搜索步长
v_trans_fine_tune_radius = 10 # 喷口开始偏转地速精细搜索半径
v_trans_fine_tune_step = 1 # 喷口开始偏转地速精细搜索步长

# 甲板风
V_wind_kt = 22  # 节
V_wind = V_wind_kt * 0.514444  # m/s


print(f"起飞重量: {W_kg:,} kg")
print(f"展弦比: {AR:.3f} ")
print(f"甲板风: {V_wind_kt} kt = {V_wind:.2f} m/s")
print(f"地面效应因子 φ = {phi:.3f}")
print(f"诱导阻力因子 k = {k:.3f}")
# ============================================================
# 策略A仿真（主喷管滑跑开始时平直向后，在起飞前再偏转至最优角度）
# ============================================================

def simulate_strategy_A_wind(W_test, m_test, V_wind, V_trans, theta_deg=45, dt=0.01, max_t=60):
    """
    策略A仿真，考虑甲板风
    V_wind: 逆风速度 (m/s)
    V_trans: 喷口开始偏转时地速 (m/s)
    """
    transition_dur=theta_deg / nozzle_transition_speed
    theta_final = np.radians(theta_deg)
    V_g = 0.0  # 地速
    x = 0.0    # 地速积分得到的距离
    t = 0.0
    airborne = False
    transitioned = False
    in_transition = False
    trans_start = 0
    
    # 记录
    history = {'t': [], 'x': [], 'V_g': [], 'V_a': [], 'N': [], 'a': [], 'T_h': [], 'T_v': [], 'phase': []}
    
    while t < max_t and x < 3000:
        V_a = V_g + V_wind  # 空速 = 地速 + 风速（逆风）
        
        # 阶段判断
        if not airborne and not transitioned and V_g >= V_trans and not in_transition:
            in_transition = True
            trans_start = t
        
        # 推力计算，注意达到起飞条件前，滚转喷管都不开启，用于驱动滚转喷管的空气流量/功率全部留在主喷管喷气
        if in_transition:
            elapsed = t - trans_start
            if elapsed >= transition_dur:
                ratio = 1.0
                in_transition = False
                transitioned = True
            else:
                ratio = elapsed / transition_dur
            theta_cur = theta_final * ratio
            T_main_eff = T_main_stovl + T_rollposts / efficiency_rollposts
            T_h = T_main_eff * np.cos(theta_cur)
            T_v = T_main_eff * np.sin(theta_cur) + T_liftfan
        elif transitioned:
            T_h = (T_main_stovl + T_rollposts / efficiency_rollposts) * np.cos(theta_final)
            T_v = T_main_stovl * np.sin(theta_final) + T_liftfan 
        else:
            T_h = T_main_stovl + T_rollposts / efficiency_rollposts
            T_v = T_liftfan 
        
        if airborne:
            T_h = T_main_stovl
            T_v = T_liftfan  + T_rollposts
        
        # 气动力（基于空速）
        q = 0.5 * rho * V_a**2
        L = q * S_m2 * Cl_to + T_v
        Cd = Cd0 + k * Cl_to**2 * phi
        D = q * S_m2 * Cd
        
        # 地面正压力
        N = W_test - L
        # 达到起飞状态的地面压力
        L_potential = q * S_m2 * Cl_takeoff + T_v + T_rollposts
        N_potential = W_test - L_potential
        if N_potential < 0: #如果速度达到起飞条件，则让滚转喷管立即启动，假定这个过程极快
            N = 0
            if not airborne:
                airborne = True
        
        F_f = mu * N if not airborne else 0
        a = (T_h - D - F_f) / m_test
        
        # 记录
        history['t'].append(t)
        history['x'].append(x)
        history['V_g'].append(V_g)
        history['V_a'].append(V_a)
        history['N'].append(N)
        history['a'].append(a)
        history['T_h'].append(T_h)
        history['T_v'].append(T_v)
        history['phase'].append(1 if not (in_transition or transitioned) else (2 if in_transition else 3))
        
        V_g += a * dt
        if V_g < 0:
            V_g = 0
        x += V_g * dt
        t += dt
    
    for key in history:
        history[key] = np.array(history[key])
    
    return history, airborne, x, V_g

# 1. 扫描最优转换速度
print("\n" + "=" * 60)
print(f"策略A：起飞前偏转主喷口（{V_wind_kt}节甲板风）")
print("=" * 60)

best_dist = float('inf')
best_Vtrans = 0
best_hist = None

print(f"扫描喷口开始偏转时地速:")
for theta_deg in range (final_deg_search_start, final_deg_search_end + deg_search_step, deg_search_step):
    for V_trans in range(v_trans_search_start, v_trans_search_end + v_trans_search_step, v_trans_search_step):
        hist, airborne, x_final, V_g_final = simulate_strategy_A_wind(W, m, V_wind, V_trans, theta_deg)
        
        # 找到离地时刻
        lift_off_idx = np.where(np.diff(np.sign(hist['N'])) < 0)[0]
        if len(lift_off_idx) > 0:
            lo_idx = lift_off_idx[0]
            x_lo = hist['x'][lo_idx]
            V_g_lo = hist['V_g'][lo_idx]
            V_a_lo = hist['V_a'][lo_idx]
            t_lo = hist['t'][lo_idx]
            
            if x_lo < best_dist:
                best_dist = x_lo
                best_Vtrans = V_trans
                best_hist = hist
                best_lo_idx = lo_idx
                best_theta_deg = theta_deg
            
            # if V_trans % 10 == 0:
            #     print(f"最终角度 {theta_deg:2d} 度  转换地速 {V_trans:2d} m/s ({V_trans*1.94384:.0f} kt): 离地距离 = {x_lo:6.1f} m, 离地地速 = {V_g_lo:.1f} m/s, 离地空速 = {V_a_lo:.1f} m/s")

print(f"\n{'=' * 60}")
print(f"最优结果:")
print(f"  最优最终角度: {best_theta_deg} 度)")
print(f"  最优喷口开始偏转时地速: {best_Vtrans} m/s ({best_Vtrans*1.94384:.0f} kt)")
print(f"  最短离地距离: {best_dist:.1f} m ({best_dist*3.28084:.0f} ft)")
print(f"  离地时地速: {best_hist['V_g'][best_lo_idx]:.1f} m/s ({best_hist['V_g'][best_lo_idx]*1.94384:.0f} kt)")
print(f"  离地时空速: {best_hist['V_a'][best_lo_idx]:.1f} m/s ({best_hist['V_a'][best_lo_idx]*1.94384:.0f} kt)")
print(f"  离地时间: {best_hist['t'][best_lo_idx]:.2f} s")
print(f"{'=' * 60}")

# 2. 精细扫描最优转换速度
print("精细扫描最优转换地速）：")
print("-" * 60)

best_dist_fine = float('inf')
best_Vtrans_fine = 0
for theta_deg in range (best_theta_deg - deg_fine_tune_radius, best_theta_deg + deg_fine_tune_radius, deg_fine_tune_step):
    for V_trans in range(best_Vtrans - v_trans_fine_tune_radius, best_Vtrans + v_trans_fine_tune_radius, v_trans_fine_tune_step):
        hist, airborne, x_final, V_g_final = simulate_strategy_A_wind(W, m, V_wind, V_trans, best_theta_deg)
        lift_off_idx = np.where(np.diff(np.sign(hist['N'])) < 0)[0]
        if len(lift_off_idx) > 0:
            lo_idx = lift_off_idx[0]
            x_lo = hist['x'][lo_idx]
            V_g_lo = hist['V_g'][lo_idx]
            V_a_lo = hist['V_a'][lo_idx]
            t_lo = hist['t'][lo_idx]
            marker = " <-- 最优" if x_lo < best_dist_fine else ""
            if x_lo < best_dist_fine:
                best_dist_fine = x_lo
                best_Vtrans_fine = V_trans
                best_hist_fine = hist
                best_lo_idx_fine = lo_idx
                best_theta_deg_fine = theta_deg
            # print(f"  V_trans = {V_trans} m/s ({V_trans*1.94384:.0f} kt): 离地距离 = {x_lo:.1f} m, 离地地速 = {V_g_lo:.1f} m/s, 时间 = {t_lo:.2f}s{marker}")

print(f"\n★ 精细最优: 最终角度: {best_theta_deg_fine} 度，转换地速 {best_Vtrans_fine} m/s ({best_Vtrans_fine*1.94384:.0f} kt), 离地距离 {best_dist_fine:.1f} m ({best_dist_fine*3.28084:.0f} ft)")

# ============================================================
# 策略B仿真（主喷管角度固定）
# ============================================================
print("\n" + "=" * 60)
print(f"策略B对比（{V_wind_kt}节甲板风 固定偏转角度）")
print("=" * 60)


def simulate_strategy_B_wind(W_test, m_test, V_wind, angle, dt=0.01, max_t=60):
    theta_final = np.radians(angle)
    V_g = 0.0
    x = 0.0
    t = 0.0
    airborne = False
    
    history = {'t': [], 'x': [], 'V_g': [], 'V_a': [], 'N': [], 'a': [], 'T_h': [], 'T_v': []}
    
    while t < max_t and x < 3000:
        V_a = V_g + V_wind
        
        # 同样假定起飞前滚转喷管不抽功
        T_main_eff = T_main_stovl + T_rollposts / efficiency_rollposts
        T_h = T_main_eff * np.cos(theta_final)
        T_v = T_main_eff * np.sin(theta_final) + T_liftfan
        
        q = 0.5 * rho * V_a**2
        L = q * S_m2 * Cl_to + T_v
        Cd = Cd0 + k * Cl_to**2 * phi
        D = q * S_m2 * Cd
        
        N = W_test - L
        L_potential = q * S_m2 * Cl_takeoff + T_v + T_rollposts
        N_potential = W_test - L_potential
        if N_potential < 0: #如果升力只差滚转喷管，则假定瞬时启动滚转喷管
            N = 0
            if not airborne:
                airborne = True
        
        F_f = mu * N if not airborne else 0
        a = (T_h - D - F_f) / m_test
        
        history['t'].append(t)
        history['x'].append(x)
        history['V_g'].append(V_g)
        history['V_a'].append(V_a)
        history['N'].append(N)
        history['a'].append(a)
        history['T_h'].append(T_h)
        history['T_v'].append(T_v)
        
        V_g += a * dt
        if V_g < 0:
            V_g = 0
        x += V_g * dt
        t += dt
    
    for key in history:
        history[key] = np.array(history[key])
    
    return history, airborne, x, V_g

best_B_dist = float('inf')
best_B_angle = 0
for angle in range(25, 90, 1):
    hist, airborne, x_final, V_g_final = simulate_strategy_B_wind(W, m, V_wind, angle)
    lift_off_idx = np.where(np.diff(np.sign(hist['N'])) < 0)[0]
    if len(lift_off_idx) > 0:
        lo_idx = lift_off_idx[0]
        x_lo = hist['x'][lo_idx]
        V_g_lo = hist['V_g'][lo_idx]
        # print(f"  固定{angle}°: 离地距离 = {x_lo:.1f} m, 离地地速 = {V_g_lo:.1f} m/s")
        if x_lo < best_B_dist:
            best_B_dist = x_lo
            best_B_angle = angle

print(f"\n策略B最优: 固定{best_B_angle}°, 离地距离 {best_B_dist:.1f} m")
print(f"策略A最优: 喷口开始偏转时地速{best_Vtrans_fine} m/s, 离地距离 {best_dist_fine:.1f} m")
print(f"策略A比策略B短: {best_B_dist - best_dist_fine:.1f} m ({(best_B_dist - best_dist_fine)/best_B_dist*100:.1f}%)")

