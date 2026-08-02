const { loadSimulatorData, runSimulation, modesToList } = require('../../utils/api.js');
const {
  computeSkiJumpArc,
  resolveCarrierSkiJump,
  computeAircraftAero,
  a2aMassKg,
  maxPayloadKg,
  filterCarriersForMode,
  filterAircraftForMode,
  fmtNum,
  fmtInt,
  modeNeedsSkiJump,
  modeHasTrajectory,
  defaultDeckWindKt,
} = require('../../utils/physics.js');
const { trajectoryCanvasHeightRpx } = require('../../utils/responsive.js');
const config = require('../../config.js');

Page({
  data: {
    modeList: [],
    strategyList: [],
    currentMode: 'ski_jump',
    currentStrategy: 'A',
    showStrategy: false,
    strategyTitle: '喷口策略',
    carriers: [],
    aircraft: [],
    carrierNames: [],
    aircraftNames: [],
    carrierIndex: 0,
    aircraftIndex: 0,
    carrierLabel: '',
    aircraftLabel: '',
    carrierSpecs: [],
    aircraftSpecs: [],
    showSkiJump: false,
    skiAngle: '',
    skiArcLength: '',
    skiHeight: '',
    skiHorizontal: '—',
    windKt: '',
    tempC: '30',
    massKg: '',
    statusText: '',
    statusClass: '',
    outputText: '选择参数后点击「开始仿真」，结果将显示在此处。',
    outputEmpty: true,
    running: false,
    simResult: null,
    showTrajectory: false,
    trajHeightRpx: 380,
    hasApi: false,
  },

  /** 页面级缓存：完整数据库与滑跃几何 */
  _data: null,
  _skiGeom: null,
  _windUserEdited: false,
  _massUserEdited: false,

  onLoad() {
    this.setData({
      trajHeightRpx: trajectoryCanvasHeightRpx(),
      hasApi: Boolean(config.apiBaseUrl),
    });
    this.bootstrap();
  },

  async bootstrap() {
    this.setStatus('正在加载数据…', 'loading');
    try {
      const data = await loadSimulatorData();
      if (!data || !Array.isArray(data.carriers) || !Array.isArray(data.aircraft)) {
        throw new Error('数据格式无效：缺少 carriers / aircraft');
      }
      this._data = data;
      this._stovlStrategies = data.stovl_strategies || {
        A: '策略 A — 延迟偏转喷口',
        B: '策略 B — 全程固定喷口',
        C: '策略 C — 尾流约束最优偏转',
      };
      this._tiltrotorStrategies = data.tiltrotor_strategies || {
        A: '策略 A — 延迟倾转短舱',
        B: '策略 B — 全程固定短舱角',
      };
      this.setData({
        modeList: modesToList(data.modes),
        strategyList: modesToList(this._stovlStrategies),
      });
      this.applyMode('ski_jump');
      const hint = config.apiBaseUrl
        ? '本地数据已加载。仿真将请求后端 API。'
        : '数据已加载。仿真需配置 config.js 中的 apiBaseUrl 并启动 python3 apps/miniprogram_api.py';
      this.setStatus(hint, 'ok');
    } catch (e) {
      this.setStatus(e.message || '加载失败', 'error');
    }
  },

  setStatus(text, cls = '') {
    this.setData({ statusText: text, statusClass: cls });
  },

  applyMode(mode) {
    if (!this._data) return;
    const carriers = filterCarriersForMode(mode, this._data.carriers);
    const aircraft = filterAircraftForMode(mode, this._data.aircraft);
    const showStrategy =
      mode === 'short_takeoff' ||
      mode === 'short_ski_jump' ||
      mode === 'tiltrotor_short_takeoff';
    const isTilt = mode === 'tiltrotor_short_takeoff';
    const strategyMap = isTilt ? this._tiltrotorStrategies : this._stovlStrategies;
    let currentStrategy = this.data.currentStrategy;
    if (isTilt && currentStrategy === 'C') currentStrategy = 'A';
    this._windUserEdited = false;
    this._massUserEdited = false;
    this.setData({
      currentMode: mode,
      showStrategy,
      strategyTitle: isTilt ? '短舱倾转策略' : '喷口策略',
      strategyList: modesToList(strategyMap || {}),
      currentStrategy,
      carriers,
      aircraft,
      carrierNames: carriers.map((c) => `${c.name}（${c.nation}）`),
      aircraftNames: aircraft.map((a) => a.name),
      carrierIndex: 0,
      aircraftIndex: 0,
      showTrajectory: false,
      simResult: null,
    });
    this.refreshSelections();
  },

  getSelectedCarrier() {
    const list = this.data.carriers;
    const idx = this.data.carrierIndex;
    return list[idx] || null;
  },

  getSelectedAircraft() {
    const list = this.data.aircraft;
    const idx = this.data.aircraftIndex;
    return list[idx] || null;
  },

  refreshSelections() {
    this.updateCarrierInfo();
    this.updateAircraftInfo();
  },

  updateSkiJumpFromInputs() {
    const carrier = this.getSelectedCarrier();
    if (!carrier || !carrier.ski_jump) {
      this._skiGeom = null;
      return;
    }
    const angle = parseFloat(this.data.skiAngle);
    const arcLen = parseFloat(this.data.skiArcLength);
    if (Number.isNaN(angle) || angle <= 0) return;
    try {
      this._skiGeom = computeSkiJumpArc(
        angle,
        null,
        Number.isNaN(arcLen) || arcLen <= 0 ? null : arcLen
      );
      this.setData({
        skiHeight: this._skiGeom.lip_height_m.toFixed(2),
        skiHorizontal: fmtNum(this._skiGeom.horizontal_m, 1),
      });
    } catch (e) {
      this._skiGeom = null;
    }
  },

  updateCarrierInfo() {
    const c = this.getSelectedCarrier();
    if (!c) {
      this.setData({
        carrierLabel: '（无可用航母）',
        carrierSpecs: [],
        showSkiJump: false,
      });
      return;
    }

    let skiPatch = {};
    if (c.ski_jump) {
      const base = resolveCarrierSkiJump(c);
      skiPatch = {
        skiAngle: String(base.angle_deg),
        skiArcLength: base.arc_length_m.toFixed(1),
      };
    }

    const specs = [
      { label: '最大航速', value: `${fmtInt(c.max_speed_kt)} kt` },
      { label: '甲板总长度', value: `${fmtNum(c.total_deck_length_m, 1)} m` },
      {
        label: '滑跃甲板',
        value: c.ski_jump ? '是（参数可编辑）' : '否（平直甲板）',
      },
    ];

    const showSki = modeNeedsSkiJump(this.data.currentMode) && c.ski_jump;
    const patch = {
      carrierLabel: `${c.name}（${c.nation}）`,
      carrierSpecs: specs,
      showSkiJump: showSki,
      ...skiPatch,
    };

    if (!this._windUserEdited) {
      const wind = defaultDeckWindKt(c);
      if (wind != null) patch.windKt = String(wind);
    }

    this.setData(patch, () => {
      if (c.ski_jump) this.updateSkiJumpFromInputs();
    });
  },

  updateAircraftInfo() {
    const ac = this.getSelectedAircraft();
    if (!ac) {
      this.setData({
        aircraftLabel: '（无可用战斗机）',
        aircraftSpecs: [],
      });
      return;
    }

    const aero = computeAircraftAero(ac);
    const isVtol = ac.type_label === 'v/stol';
    const isTilt = ac.type_label === 'tiltrotor';
    const specs = [
      { label: '最大起飞重量 (MTOW)', value: `${fmtInt(ac.mtow_kg)} kg` },
      { label: '最大内油', value: `${fmtInt(ac.internal_fuel_kg)} kg` },
      { label: '中距弹型号', value: ac.bvr_missile },
      { label: '中距弹重量', value: `${fmtNum(ac.missile_mass_kg, 1)} kg/枚` },
      { label: '最大载弹量', value: `${fmtInt(maxPayloadKg(ac))} kg` },
      {
        label: isTilt ? '默认起飞重量（空重+内油+机组）' : '4枚中距弹满内油空战起飞重量',
        value: `${fmtInt(a2aMassKg(ac))} kg`,
      },
      { label: '翼展', value: `${fmtNum(ac.wingspan_m, 2)} m` },
      { label: '翼面积', value: `${fmtNum(ac.wing_area_m2, 2)} m²` },
    ];

    if (isVtol) {
      specs.push(
        { label: '主喷管推力 (15°C SL)', value: `${fmtNum(ac.t_main_stovl_sl_n / 1000, 1)} kN` },
        { label: '升力风扇推力', value: `${fmtNum(ac.t_liftfan_sl_n / 1000, 1)} kN` },
        { label: '滚转喷管推力', value: `${fmtNum(ac.t_rollposts_sl_n / 1000, 1)} kN` }
      );
    } else if (isTilt) {
      specs.push(
        { label: '总轴功率 (15°C SL)', value: `${fmtNum(ac.shaft_power_sl_w / 1e6, 2)} MW` },
        { label: '桨盘直径', value: `${fmtNum(ac.prop_diameter_m, 2)} m` },
        {
          label: '短舱遮挡比',
          value: `${fmtNum((ac.nacelle_blockage_frac ?? 0.1) * 100, 0)} %`,
        }
      );
    } else {
      specs.push({
        label: '最大加力推力 (15°C SL)',
        value: `${fmtNum(ac.t_max_sl_n / 1000, 1)} kN`,
      });
    }

    specs.push(
      { label: '前缘后掠角', value: `${fmtNum(ac.sweep_le_deg, 1)}°` },
      { label: '展弦比', value: fmtNum(aero.aspect_ratio, 3) },
      { label: '升力线斜率 C_Lα', value: `${fmtNum(aero.cl_alpha_per_rad, 4)} /rad` },
      {
        label: '滑行升力系数 Cl_taxi',
        value: `${fmtNum(aero.cl_taxi, 4)}（迎角 ${fmtNum(aero.taxi_alpha_deg, 1)}°）`,
      },
      { label: '20° 攻角升力系数', value: fmtNum(aero.cl_20deg, 4) },
      { label: '零升阻力系数 Cd0', value: fmtNum(aero.cd0, 4) }
    );

    const patch = {
      aircraftLabel: ac.name,
      aircraftSpecs: specs,
    };
    if (!this._massUserEdited) {
      patch.massKg = String(Math.round(a2aMassKg(ac)));
    }
    this.setData(patch);
  },

  onModeChange(e) {
    this.applyMode(e.detail.mode);
  },

  onStrategyChange(e) {
    const strategy = e.detail.mode;
    if (strategy) this.setData({ currentStrategy: strategy });
  },

  onCarrierChange(e) {
    this._windUserEdited = false;
    this.setData({ carrierIndex: Number(e.detail.value) }, () => this.updateCarrierInfo());
  },

  onAircraftChange(e) {
    this._massUserEdited = false;
    this.setData({ aircraftIndex: Number(e.detail.value) }, () => this.updateAircraftInfo());
  },

  onSkiAngleInput(e) {
    this.setData({ skiAngle: e.detail.value }, () => this.updateSkiJumpFromInputs());
  },

  onSkiArcInput(e) {
    this.setData({ skiArcLength: e.detail.value }, () => this.updateSkiJumpFromInputs());
  },

  onWindInput(e) {
    this._windUserEdited = true;
    this.setData({ windKt: e.detail.value });
  },

  onTempInput(e) {
    this.setData({ tempC: e.detail.value });
  },

  onMassInput(e) {
    this._massUserEdited = true;
    this.setData({ massKg: e.detail.value });
  },

  async onRunSimulation() {
    const carrier = this.getSelectedCarrier();
    const aircraft = this.getSelectedAircraft();
    if (!carrier || !aircraft) {
      this.setStatus('请选择航母和战斗机', 'error');
      return;
    }

    const mass = parseFloat(this.data.massKg);
    const temp = parseFloat(this.data.tempC);
    const wind = parseFloat(this.data.windKt);
    if ([mass, temp, wind].some((v) => Number.isNaN(v))) {
      this.setStatus('请填写有效的重量、温度和甲板风', 'error');
      return;
    }

    this.setData({
      running: true,
      outputEmpty: false,
      outputText: '计算中…',
      showTrajectory: false,
      simResult: null,
    });
    this.setStatus('仿真计算中（可能需要数秒至数十秒）…', 'loading');

    const payload = {
      mode: this.data.currentMode,
      aircraft,
      carrier,
      mass_kg: mass,
      temp_c: temp,
      wind_kt: wind,
      total_deck_length_m: carrier.total_deck_length_m,
    };

    if (this.data.showStrategy) {
      payload.strategy = this.data.currentStrategy;
    }

    if (modeNeedsSkiJump(this.data.currentMode) && carrier.ski_jump) {
      this.updateSkiJumpFromInputs();
      payload.ski_jump_angle_deg = parseFloat(this.data.skiAngle);
      payload.ski_jump_arc_length_m = parseFloat(this.data.skiArcLength);
      payload.ski_jump_height_m = parseFloat(this.data.skiHeight);
    }

    try {
      const result = await runSimulation(payload);
      const showTraj =
        modeHasTrajectory(this.data.currentMode) &&
        result.success &&
        result.trajectory &&
        result.trajectory.length &&
        result.deck_profile;

      this.setData({
        outputText: result.output || '(无输出)',
        simResult: showTraj ? result : null,
        showTrajectory: Boolean(showTraj),
      });

      if (result.success) {
        const trajNote =
          showTraj && result.trajectory ? ` · 轨迹 ${result.trajectory.length} 点` : '';
        const msg = result.deck_launch_ok
          ? `仿真完成 — 甲板可用（余量 ${fmtNum(result.deck_margin_m, 1)} m）${trajNote}`
          : `仿真完成 — 甲板不足（超出 ${fmtNum(-result.deck_margin_m, 1)} m）${trajNote}`;
        this.setStatus(msg, result.deck_launch_ok ? 'ok' : 'error');
      } else {
        this.setStatus(result.error || '仿真失败', 'error');
      }
    } catch (e) {
      this.setData({
        outputText: String(e.message || e),
        showTrajectory: false,
        simResult: null,
      });
      this.setStatus(`仿真出错: ${e.message}`, 'error');
    } finally {
      this.setData({ running: false });
    }
  },
});
