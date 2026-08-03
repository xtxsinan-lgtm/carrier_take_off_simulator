/**
 * 饱和打击 Web 前端：GUI 保留战术终端风格，计算走 Pyodide Python 核心。
 */
const PYODIDE_VERSION = '0.26.4';
/** 与 saturation-strike.html 中 ?v= 同步递增 */
const APP_VERSION = 10;

/** 预警机预设中「无预警机」的特殊 value */
const AEW_NONE_VALUE = '__none__';

/** 仅加载饱和打击相关 Python 模块（无需 numpy） */
const SATURATION_PY_FILES = [
  'utils/__init__.py',
  'utils/paths.py',
  'utils/database_csv.py',
  'utils/saturation_presets.py',
  'utils/saturation_radar.py',
  'utils/saturation_windows.py',
  'utils/saturation_monte_carlo.py',
  'simulators/__init__.py',
  'simulators/saturation_strike.py',
  'apps/__init__.py',
  'apps/saturation_strike_web.py',
];

const SATURATION_IMPORTS = [
  'utils.paths',
  'utils.database_csv',
  'utils.saturation_presets',
  'utils.saturation_radar',
  'utils.saturation_windows',
  'utils.saturation_monte_carlo',
  'simulators.saturation_strike',
  'apps.saturation_strike_web',
];

let data = null;
let pyodide = null;
let pyReady = false;
let chartRef = null;
/** 防止重入；计算中再次点击则排队用最新参数再跑一轮 */
let runLock = false;
let rerunRequested = false;

function $(id) {
  return document.getElementById(id);
}

function fmt(n, d = 2) {
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: 0 });
}

function fillSelect(selectEl, presets) {
  selectEl.innerHTML =
    '<option value="">— 自定义 / 手动输入 —</option>' +
    presets.map((p) => `<option value="${p.id}">${p.name}</option>`).join('');
}

/** 在预警机预设下拉框中插入「无预警机」选项（紧跟自定义选项之后）。 */
function insertNoAewOption(selectEl) {
  const noneOpt = document.createElement('option');
  noneOpt.value = AEW_NONE_VALUE;
  noneOpt.textContent = '无预警机';
  selectEl.insertBefore(noneOpt, selectEl.options[1] || null);
}

/** 选择「无预警机」时置灰预警机相关输入，提示这些字段此时不参与计算。 */
function setAwacsFieldsDisabled(disabled) {
  ['awacsArea', 'awacsType', 'standoff'].forEach((id) => {
    const el = $(id);
    if (el) el.disabled = disabled;
  });
}

function applyPresetsFromData() {
  const presets = data.saturation_presets || {};
  fillSelect($('asmPreset'), presets.asm || []);
  fillSelect($('aewPreset'), presets.aew || []);
  insertNoAewOption($('aewPreset'));
  fillSelect($('shipPreset'), presets.ship || []);
  fillSelect($('samPreset'), presets.sam || []);

  $('asmPreset').addEventListener('change', (e) => {
    const p = (presets.asm || []).find((x) => x.id === e.target.value);
    if (!p) return;
    $('vm').value = p.vm;
    $('rcs').value = p.rcs;
    $('traj').value = p.traj;
  });
  $('aewPreset').addEventListener('change', (e) => {
    const isNone = e.target.value === AEW_NONE_VALUE;
    setAwacsFieldsDisabled(isNone);
    if (isNone) return;
    const p = (presets.aew || []).find((x) => x.id === e.target.value);
    if (!p) return;
    $('awacsArea').value = p.area;
    $('awacsType').value = p.type;
    $('standoff').value = p.standoff;
  });
  $('shipPreset').addEventListener('change', (e) => {
    const p = (presets.ship || []).find((x) => x.id === e.target.value);
    if (!p) return;
    $('shipArea').value = p.area;
    $('shipType').value = p.type;
  });
  $('samPreset').addEventListener('change', (e) => {
    const p = (presets.sam || []).find((x) => x.id === e.target.value);
    if (!p) return;
    $('vi').value = p.vi;
    $('interceptorDia').value = p.dia;
    $('seekerType').value = p.guidance;
    $('samRange').value = p.range;
  });
}

async function loadData() {
  const resp = await fetch(`data.json?v=${APP_VERSION}`);
  if (!resp.ok) throw new Error(`无法加载 data.json (${resp.status})`);
  data = await resp.json();
  if (!data.py_sources) {
    throw new Error('data.json 缺少 py_sources，请运行 python3 scripts/build_all.py');
  }
  if (!data.saturation_presets) {
    throw new Error('data.json 缺少 saturation_presets，请运行 python3 scripts/build_all.py');
  }
}

async function loadPythonModules() {
  pyodide.runPython(`
import sys
from pathlib import Path
Path('/py').mkdir(parents=True, exist_ok=True)
if '/py' not in sys.path:
    sys.path.insert(0, '/py')
`);

  for (const name of SATURATION_PY_FILES) {
    const code = data.py_sources[name];
    if (code === undefined || code === null) {
      throw new Error(`缺少 Python 模块: ${name}`);
    }
    const parts = name.split('/');
    if (parts.length > 1) {
      let dir = '/py';
      for (let i = 0; i < parts.length - 1; i++) {
        dir += `/${parts[i]}`;
        try {
          pyodide.FS.mkdir(dir);
        } catch {
          /* already exists */
        }
      }
    }
    pyodide.FS.writeFile(`/py/${name}`, code);
  }

  pyodide.globals.set('_py_import_order', SATURATION_IMPORTS);
  await pyodide.runPythonAsync(`
import importlib
for _name in _py_import_order:
    importlib.import_module(_name)
`);
}

async function initPyodide() {
  if (pyReady) return;
  $('statusTag').textContent = 'LOADING';
  const { loadPyodide } = await import(
    `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.mjs`
  );
  pyodide = await loadPyodide();
  await loadPythonModules();
  pyReady = true;
  $('statusTag').textContent = 'READY';
}

function callPython(action, params) {
  const payload = JSON.stringify({ action, params });
  pyodide.globals.set('_sat_payload', payload);
  const raw = pyodide.runPython(`
import json
from apps.saturation_strike_web import run_saturation_json
json.dumps(run_saturation_json(_sat_payload), ensure_ascii=False)
`);
  return JSON.parse(raw);
}

/** 异步调用 Python，便于在计算前刷新「计算中」UI */
async function callPythonAsync(action, params) {
  const payload = JSON.stringify({ action, params });
  pyodide.globals.set('_sat_payload', payload);
  const raw = await pyodide.runPythonAsync(`
import json
from apps.saturation_strike_web import run_saturation_json
json.dumps(run_saturation_json(_sat_payload), ensure_ascii=False)
`);
  return JSON.parse(raw);
}

function collectEstimateParams() {
  return {
    rcs: +$('rcs').value,
    traj: $('traj').value,
    awacs_area: +$('awacsArea').value,
    awacs_type: $('awacsType').value,
    standoff: +$('standoff').value,
    ship_area: +$('shipArea').value,
    ship_type: $('shipType').value,
    sam_range: +$('samRange').value,
    vm: +$('vm').value,
    vi: +$('vi').value,
    interceptor_dia: +$('interceptorDia').value,
    seeker_type: $('seekerType').value,
    has_awacs: $('aewPreset').value !== AEW_NONE_VALUE,
  };
}

function collectSimParams() {
  return {
    nm: +$('Nm').value,
    vm: +$('vm').value,
    D: +$('D').value,
    ni: +$('Ni').value,
    vi: +$('vi').value,
    pk: +$('pk').value,
    tlock: +$('tlock').value,
    minr: +$('minr').value,
  };
}

function renderResults(r) {
  $('placeholder').style.display = 'none';
  $('resultsBody').style.display = 'block';
  $('statusTag').textContent = 'DONE';

  const windows = r.windows || [];
  const nRounds = r.n_rounds || 0;
  const theadW = document.querySelector('#windowTable thead');
  const tbodyW = document.querySelector('#windowTable tbody');
  theadW.innerHTML =
    '<tr><th>窗口</th><th>轮次起始距离 (km)</th><th>拦截弹飞行时间 (s)</th><th>本轮耗时 (s)</th><th>轮末剩余距离 (km)</th></tr>';
  tbodyW.innerHTML =
    windows
      .map(
        (w) => `<tr>
      <td>#${w.round}</td><td>${fmt(w.dist_start_km, 2)}</td><td>${fmt(w.t_fly_s, 1)}</td>
      <td>${fmt(w.total_t_s, 1)}</td><td>${fmt(w.dist_end_km, 2)}</td>
    </tr>`
      )
      .join('') ||
    '<tr><td colspan="5">发现距离不足以形成任何拦截窗口 — 检查参数（发现距离/速度/锁定时间）</td></tr>';

  if (nRounds === 0) {
    $('statRounds').textContent = '0';
    $('statLeak').textContent = r.nm;
    $('statRate').textContent = '0%';
    $('statRoundsSub').textContent = '';
    $('statLeakSub').textContent = '';
    $('statRateSub').textContent = '';
    $('finalNote').textContent = r.note || '';
    document.querySelector('#planTable thead').innerHTML = '';
    document.querySelector('#planTable tbody').innerHTML = '';
    document.querySelector('#strategyTable thead').innerHTML = '';
    document.querySelector('#strategyTable tbody').innerHTML = '';
    if (chartRef) chartRef.destroy();
    $('mcN').textContent = r.final_trials || '–';
    return;
  }

  const best = r.best;
  const avgSurvivors = r.avg_survivors || [];
  const allCandidates = r.all_candidates || [];
  const expectedLeak = r.expected_leak;
  const interceptRate = r.intercept_rate;
  const pk = r.pk;
  const ni = r.ni;
  const nm = r.nm;
  const tlock = r.t_lock_s;

  $('mcN').textContent = r.final_trials;
  $('statRounds').textContent = nRounds;
  $('statRoundsSub').textContent = `火控锁定 ${tlock}s / 轮`;
  $('statLeak').textContent = fmt(expectedLeak, 2);
  $('statLeakSub').textContent = `/ 共 ${nm} 枚来袭`;
  $('statRate').textContent = fmt(interceptRate * 100, 1) + '%';
  $('statRateSub').textContent = `弹药消耗 ≤ ${ni} 枚`;

  const theadP = document.querySelector('#planTable thead');
  const tbodyP = document.querySelector('#planTable tbody');
  theadP.innerHTML =
    '<tr><th>窗口</th><th>本轮弹药预算</th><th>预期存活目标数(轮初)</th><th>每目标约分配</th><th>单目标本轮杀伤概率</th></tr>';
  let maxPer = 1;
  for (let i = 0; i < nRounds; i++) {
    const surv = avgSurvivors[i];
    if (surv > 0) maxPer = Math.max(maxPer, best.plan[i] / surv);
  }
  let rows = '';
  for (let ri = 0; ri < nRounds; ri++) {
    const survBefore = avgSurvivors[ri];
    const perTarget = survBefore > 0 ? best.plan[ri] / survBefore : 0;
    const kFloor = Math.floor(perTarget);
    const pkill = kFloor > 0 ? 1 - Math.pow(1 - pk, kFloor) : 0;
    rows += `<tr>
      <td>#${ri + 1}</td>
      <td>${best.plan[ri]} 枚</td>
      <td>${fmt(survBefore, 2)}</td>
      <td>≈${fmt(perTarget, 2)} 枚/目标
        <div class="bar-wrap"><div class="bar-bg"><div class="bar-fill i" style="width:${Math.min(100, (perTarget / maxPer) * 100)}%"></div></div></div>
      </td>
      <td>${fmt(pkill * 100, 1)}%</td>
    </tr>`;
  }
  tbodyP.innerHTML = rows;

  const canvas = $('survivorChart');
  if (chartRef) {
    chartRef.destroy();
    chartRef = null;
  }
  if (canvas && typeof Chart !== 'undefined' && avgSurvivors.length) {
    const ctx = canvas.getContext('2d');
    const labels = ['发现'].concat(windows.map((w) => '窗口#' + w.round + '后'));
    chartRef = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: '预期剩余来袭导弹数',
            data: avgSurvivors,
            borderColor: '#ff4d4f',
            backgroundColor: 'rgba(255,77,79,0.12)',
            fill: true,
            tension: 0.25,
            pointRadius: 3,
            pointBackgroundColor: '#ff4d4f',
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#7b8e92', font: { family: 'monospace', size: 10 } } } },
        scales: {
          x: { ticks: { color: '#7b8e92', font: { family: 'monospace', size: 9 } }, grid: { color: '#1c2b30' } },
          y: {
            beginAtZero: true,
            ticks: { color: '#7b8e92', font: { family: 'monospace', size: 9 } },
            grid: { color: '#1c2b30' },
          },
        },
      },
    });
  }

  const theadS = document.querySelector('#strategyTable thead');
  const tbodyS = document.querySelector('#strategyTable tbody');
  theadS.innerHTML = '<tr><th>策略</th><th>各轮弹药分配</th><th>期望突防导弹数</th><th>相对最优方案</th></tr>';
  if (!allCandidates.length) {
    tbodyS.innerHTML = '';
  } else {
    const minScore = allCandidates[0].expected_leak;
    const bestKey = best.plan.join(',');
    tbodyS.innerHTML = allCandidates
      .map((c) => {
        const isBest = c.name === best.name && c.plan.join(',') === bestKey;
        return `<tr class="${isBest ? 'best' : ''}">
        <td>${isBest ? '★ ' : ''}${c.name}</td>
        <td>[${c.plan.join(', ')}]</td>
        <td>${fmt(c.expected_leak, 2)}</td>
        <td>${isBest ? '—' : '+' + fmt(c.expected_leak - minScore, 2)}</td>
      </tr>`;
      })
      .join('');
  }

  $('finalNote').textContent = r.note || '';
}

async function ensureEngine() {
  if (!pyReady) await initPyodide();
}

/** 一次估算交战距离与单发拦截成功概率（拦截率输入），填入按钮下方两字段。 */
async function onEstimateDistanceAndPk() {
  const btn = $('estimateBtn');
  btn.disabled = true;
  try {
    await ensureEngine();
    const params = collectEstimateParams();
    const dist = callPython('estimate_distance', params);
    if (!dist.success) throw new Error(dist.error || '交战距离估算失败');
    $('awacsDetectKm').value = dist.has_awacs ? Number(dist.awacs_detect_km).toFixed(1) : '0';
    $('shipDetectKm').value = Number(dist.ship_detect_km).toFixed(1);
    $('D').value = Number(dist.engage_dist).toFixed(1);
    $('distBreakdown').textContent = dist.has_awacs
      ? `预警机雷达探测: ${dist.awacs_detect.toFixed(0)}km(功率限${dist.awacs_power.toFixed(0)}/视距限${dist.awacs_horizon.toFixed(0)}) + 前出${dist.standoff.toFixed(0)}km = ${dist.awacs_detect_km.toFixed(0)}km ｜ 舰载雷达探测: ${dist.ship_detect_km.toFixed(0)}km(功率限${dist.ship_power.toFixed(0)}/视距限${dist.ship_horizon.toFixed(0)}) ｜ 拦截弹射程: ${dist.sam_range.toFixed(0)}km → 交战距离＝min(max(预警机探测,舰载探测), 拦截弹射程)＝${dist.engage_dist.toFixed(1)}km（受限于：${dist.binding}）— 已填入下方「预警机/舰载雷达探测距离」与「交战距离」，可手动修改。`
      : `无预警机：假设目标高度 ${dist.h_target_m.toFixed(0)}m ｜ 舰载雷达探测＝min(功率限${dist.ship_power.toFixed(0)}km, 视距限${dist.ship_horizon.toFixed(0)}km)＝${dist.ship_detect_km.toFixed(0)}km ｜ 拦截弹射程: ${dist.sam_range.toFixed(0)}km → 交战距离＝min(max(0,舰载探测), 拦截弹射程)＝${dist.engage_dist.toFixed(1)}km（受限于：${dist.binding}）— 已填入下方「舰载雷达探测距离」与「交战距离」，可手动修改。`;

    const pkR = callPython('estimate_pk', params);
    if (!pkR.success) throw new Error(pkR.error || '拦截率估算失败');
    $('pk').value = Number(pkR.pk).toFixed(2);
    $('pkEstBreakdown').textContent =
      `估算拦截率（单发）= ${pkR.pk.toFixed(2)}（基线0.75 × 速度系数${pkR.speed_factor.toFixed(2)} × 舰载雷达增益${pkR.ship_radar_factor.toFixed(2)} × 导引头增益${pkR.seeker_factor.toFixed(2)} × RCS系数${pkR.rcs_factor.toFixed(2)} × 弹道系数${pkR.traj_factor.toFixed(2)}）— 已填入下方「单发拦截成功概率」，可手动修改。`;
  } catch (e) {
    const msg = String(e.message || e);
    $('distBreakdown').textContent = msg;
    $('pkEstBreakdown').textContent = '';
    $('statusTag').textContent = 'ERROR';
  } finally {
    btn.disabled = false;
  }
}

async function onRun() {
  const btn = $('runBtn');
  // 计算进行中再次点击：排队，结束后用最新表单参数再跑
  if (runLock) {
    rerunRequested = true;
    $('statusTag').textContent = 'QUEUED';
    btn.textContent = '▶ 已排队，稍后重算…';
    return;
  }
  runLock = true;
  rerunRequested = false;
  btn.disabled = true;
  try {
    if (!pyReady) {
      btn.textContent = '▶ 加载引擎中…';
      $('statusTag').textContent = 'LOADING';
      await ensureEngine();
    }
    btn.textContent = '▶ 计算中…';
    $('statusTag').textContent = 'COMPUTING';
    // 让浏览器先绘制按钮/状态，再进入阻塞式蒙特卡洛
    await new Promise((r) => setTimeout(r, 40));
    const r = await callPythonAsync('simulate', collectSimParams());
    if (!r.success) throw new Error(r.error || '仿真失败');
    renderResults(r);
  } catch (e) {
    $('statusTag').textContent = 'ERROR';
    $('placeholder').style.display = 'block';
    $('placeholder').textContent = String(e.message || e);
    $('resultsBody').style.display = 'none';
  } finally {
    runLock = false;
    btn.disabled = false;
    btn.textContent = '▶ 运行仿真 / RUN';
    if (rerunRequested) {
      rerunRequested = false;
      // 用用户改过的最新参数再跑一轮
      setTimeout(() => onRun(), 0);
    }
  }
}

function tickClock() {
  const d = new Date();
  $('clock').textContent = d.toTimeString().slice(0, 8) + ' · SIM CLOCK';
}

async function main() {
  setInterval(tickClock, 1000);
  tickClock();
  try {
    await loadData();
    applyPresetsFromData();
  } catch (e) {
    $('statusTag').textContent = 'ERROR';
    $('placeholder').textContent = String(e.message || e);
    return;
  }
  $('estimateBtn').addEventListener('click', onEstimateDistanceAndPk);
  $('runBtn').addEventListener('click', onRun);
  // 预加载引擎后自动跑一次默认参数
  onRun();
}

main();
