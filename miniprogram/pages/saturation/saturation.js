const api = require('../../utils/api.js');

const RADAR_TYPES = ['mechanical', 'pesa', 'aesa', 'gan_aesa'];
const RADAR_TYPE_NAMES = ['机械扫描', 'PESA', 'AESA', 'GaN AESA'];
const TRAJ = ['high', 'sea'];
const TRAJ_NAMES = ['高空 / 常规', '掠海'];
const SEEKERS = ['active_aesa', 'active_mech', 'semi_active'];
const SEEKER_NAMES = ['主动 AESA', '主动机械', '半主动'];

function num(v, d) {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function fmt(n, d) {
  return Number(n).toFixed(d);
}

Page({
  data: {
    asmList: [], aewList: [], shipList: [], samList: [],
    asmNames: ['— 自定义 —'], aewNames: ['— 自定义 —'],
    shipNames: ['— 自定义 —'], samNames: ['— 自定义 —'],
    asmIndex: 0, aewIndex: 0, shipIndex: 0, samIndex: 0,
    trajNames: TRAJ_NAMES, trajIndex: 0,
    radarTypeNames: RADAR_TYPE_NAMES,
    awacsTypeIndex: 2, shipTypeIndex: 2, seekerIndex: 0,
    seekerNames: SEEKER_NAMES,
    nm: '24', vm: '2.6', rcs: '0.5', ecm: '2',
    awacsArea: '8', standoff: '150',
    shipArea: '12', samRange: '40',
    discoveryKm: '120', ni: '16', vi: '3.8',
    interceptorDia: '0.35', pk: '0.7', tlock: '6', minr: '3',
    distNote: '', pkNote: '', statusText: '', statusTag: 'STANDBY',
    running: false, hasResult: false,
    windows: [], planRows: [], strategies: [],
    statRounds: '–', statLeak: '–', statRate: '–',
    statRoundsSub: '', statLeakSub: '', statRateSub: '',
    finalNote: '', avgSurvivors: [],
  },

  onLoad() {
    api.loadSimulatorData().then((data) => {
      const p = data.saturation_presets || {};
      const asmList = p.asm || [];
      const aewList = p.aew || [];
      const shipList = p.ship || [];
      const samList = p.sam || [];
      this.setData({
        asmList, aewList, shipList, samList,
        asmNames: ['— 自定义 —'].concat(asmList.map((x) => x.name)),
        aewNames: ['— 自定义 —'].concat(aewList.map((x) => x.name)),
        shipNames: ['— 自定义 —'].concat(shipList.map((x) => x.name)),
        samNames: ['— 自定义 —'].concat(samList.map((x) => x.name)),
        statusText: '预设已加载。请配置后端 apiBaseUrl 后运行仿真。',
      });
    }).catch((e) => {
      this.setData({ statusText: String(e.message || e) });
    });
  },

  onField(e) {
    const key = e.currentTarget.dataset.key;
    this.setData({ [key]: e.detail.value });
  },

  onTraj(e) { this.setData({ trajIndex: Number(e.detail.value) }); },
  onAwacsType(e) { this.setData({ awacsTypeIndex: Number(e.detail.value) }); },
  onShipType(e) { this.setData({ shipTypeIndex: Number(e.detail.value) }); },
  onSeeker(e) { this.setData({ seekerIndex: Number(e.detail.value) }); },

  onAsmPreset(e) {
    const idx = Number(e.detail.value);
    this.setData({ asmIndex: idx });
    if (idx <= 0) return;
    const p = this.data.asmList[idx - 1];
    this.setData({
      vm: String(p.vm), rcs: String(p.rcs),
      trajIndex: Math.max(0, TRAJ.indexOf(p.traj)),
    });
  },
  onAewPreset(e) {
    const idx = Number(e.detail.value);
    this.setData({ aewIndex: idx });
    if (idx <= 0) return;
    const p = this.data.aewList[idx - 1];
    this.setData({
      awacsArea: String(p.area), standoff: String(p.standoff),
      awacsTypeIndex: Math.max(0, RADAR_TYPES.indexOf(p.type)),
    });
  },
  onShipPreset(e) {
    const idx = Number(e.detail.value);
    this.setData({ shipIndex: idx });
    if (idx <= 0) return;
    const p = this.data.shipList[idx - 1];
    this.setData({
      shipArea: String(p.area),
      shipTypeIndex: Math.max(0, RADAR_TYPES.indexOf(p.type)),
    });
  },
  onSamPreset(e) {
    const idx = Number(e.detail.value);
    this.setData({ samIndex: idx });
    if (idx <= 0) return;
    const p = this.data.samList[idx - 1];
    this.setData({
      vi: String(p.vi), interceptorDia: String(p.dia), samRange: String(p.range),
      seekerIndex: Math.max(0, SEEKERS.indexOf(p.guidance)),
    });
  },

  estimateParams() {
    const d = this.data;
    return {
      rcs: num(d.rcs, 0.5),
      traj: TRAJ[d.trajIndex] || 'high',
      awacs_area: num(d.awacsArea, 8),
      awacs_type: RADAR_TYPES[d.awacsTypeIndex] || 'aesa',
      standoff: num(d.standoff, 150),
      ship_area: num(d.shipArea, 12),
      ship_type: RADAR_TYPES[d.shipTypeIndex] || 'aesa',
      sam_range: num(d.samRange, 40),
      vm: num(d.vm, 2.6),
      vi: num(d.vi, 3.8),
      ecm: num(d.ecm, 2),
      interceptor_dia: num(d.interceptorDia, 0.35),
      seeker_type: SEEKERS[d.seekerIndex] || 'active_aesa',
    };
  },

  /** 一次估算交战距离与单发拦截成功概率，填入按钮下方两字段。 */
  onEstimateDistanceAndPk() {
    const params = this.estimateParams();
    api.runSaturationSimulation({ action: 'estimate_distance', params })
      .then((dist) => {
        if (!dist.success) throw new Error(dist.error || '交战距离估算失败');
        return api.runSaturationSimulation({ action: 'estimate_pk', params }).then((pkR) => {
          if (!pkR.success) throw new Error(pkR.error || '拦截率估算失败');
          this.setData({
            discoveryKm: fmt(dist.engage_dist, 1),
            distNote: `交战距离 ${fmt(dist.engage_dist, 1)} km（受限于：${dist.binding}）`,
            pk: fmt(pkR.pk, 2),
            pkNote: `估算拦截率（单发）= ${fmt(pkR.pk, 2)}`,
          });
        });
      })
      .catch((e) => this.setData({ distNote: String(e.message || e), pkNote: '' }));
  },

  onRun() {
    if (this.data.running) {
      this._rerunRequested = true;
      this.setData({ statusTag: 'QUEUED', statusText: '已排队，当前轮结束后用新参数重算…' });
      return;
    }
    this._rerunRequested = false;
    const d = this.data;
    this.setData({ running: true, statusText: '计算中…', statusTag: 'COMPUTING' });
    const payload = {
      action: 'simulate',
      params: {
        nm: num(d.nm, 24),
        vm: num(d.vm, 2.6),
        D: num(d.discoveryKm, 120),
        ni: num(d.ni, 16),
        vi: num(d.vi, 3.8),
        pk: num(d.pk, 0.7),
        tlock: num(d.tlock, 6),
        minr: num(d.minr, 3),
      },
    };
    api.runSaturationSimulation(payload)
      .then((r) => {
        if (!r.success) throw new Error(r.error || '仿真失败');
        this.applyResult(r);
        if (this._rerunRequested) {
          this._rerunRequested = false;
          this.onRun();
        }
      })
      .catch((e) => {
        this.setData({
          running: false,
          statusTag: 'ERROR',
          statusText: String(e.message || e),
          hasResult: false,
        });
        if (this._rerunRequested) {
          this._rerunRequested = false;
          this.onRun();
        }
      });
  },

  applyResult(r) {
    const windows = (r.windows || []).map((w) => ({
      round: w.round,
      dist_start_km: fmt(w.dist_start_km, 1),
      t_fly_s: fmt(w.t_fly_s, 1),
      total_t_s: fmt(w.total_t_s, 1),
      dist_end_km: fmt(w.dist_end_km, 1),
    }));
    const avg = r.avg_survivors || [];
    const plan = (r.best && r.best.plan) || [];
    const planRows = plan.map((budget, i) => {
      const surv = avg[i] || 0;
      const per = surv > 0 ? budget / surv : 0;
      return {
        round: i + 1,
        budget: `${budget} 枚`,
        surv: fmt(surv, 2),
        per: `≈${fmt(per, 2)}`,
      };
    });
    const bestKey = plan.join(',');
    const strategies = (r.all_candidates || []).map((c) => ({
      name: c.name,
      plan: `[${(c.plan || []).join(', ')}]`,
      leak: fmt(c.expected_leak, 2),
      best: c.name === (r.best && r.best.name) && (c.plan || []).join(',') === bestKey,
    }));
    this.setData({
      running: false,
      hasResult: true,
      statusTag: 'DONE',
      statusText: `MC N=${r.final_trials}`,
      windows,
      planRows,
      strategies,
      avgSurvivors: avg,
      statRounds: String(r.n_rounds),
      statRoundsSub: `锁定 ${r.t_lock_s}s/轮`,
      statLeak: fmt(r.expected_leak, 2),
      statLeakSub: `/ 共 ${r.nm} 枚`,
      statRate: `${fmt((r.intercept_rate || 0) * 100, 1)}%`,
      statRateSub: `弹药 ≤ ${r.ni}`,
      finalNote: r.note || '',
    }, () => this.drawChart(avg));
  },

  drawChart(avgSurvivors) {
    const query = wx.createSelectorQuery();
    query.select('#survivorCanvas').fields({ node: true, size: true }).exec((res) => {
      if (!res || !res[0] || !res[0].node) return;
      const canvas = res[0].node;
      const width = res[0].width;
      const height = res[0].height;
      const ctx = canvas.getContext('2d');
      const dpr = wx.getSystemInfoSync().pixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
      ctx.fillStyle = '#0e161b';
      ctx.fillRect(0, 0, width, height);
      const pts = avgSurvivors || [];
      if (pts.length < 2) return;
      const maxY = Math.max(...pts, 1);
      const pad = 16;
      ctx.strokeStyle = '#1c2b30';
      ctx.beginPath();
      ctx.moveTo(pad, pad);
      ctx.lineTo(pad, height - pad);
      ctx.lineTo(width - pad, height - pad);
      ctx.stroke();
      ctx.strokeStyle = '#ff4d4f';
      ctx.lineWidth = 2;
      ctx.beginPath();
      pts.forEach((y, i) => {
        const x = pad + (i / (pts.length - 1)) * (width - 2 * pad);
        const yy = height - pad - (y / maxY) * (height - 2 * pad);
        if (i === 0) ctx.moveTo(x, yy);
        else ctx.lineTo(x, yy);
      });
      ctx.stroke();
    });
  },
});
