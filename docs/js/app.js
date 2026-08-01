import {
  a2aMassKg,
  computeAircraftAero,
  computeSkiJumpArc,
  filterAircraftForMode,
  filterCarriersForMode,
  fmtInt,
  fmtNum,
  maxPayloadKg,
  resolveCarrierSkiJump,
} from './physics.js';

const PYODIDE_VERSION = '0.26.4';
const APP_VERSION = 4;

let data = null;
let pyodide = null;
let pyReady = false;
let currentMode = 'ski_jump';
let skiGeom = null;

const els = {};

function $(id) {
  return document.getElementById(id);
}

async function loadData() {
  const resp = await fetch(`data.json?v=${APP_VERSION}`);
  if (!resp.ok) throw new Error(`无法加载 data.json (${resp.status})`);
  data = await resp.json();
  if (!data.py_sources) {
    throw new Error('data.json 缺少 py_sources，请运行 python3 scripts/build_docs.py');
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

  for (const name of data.py_load_order) {
    const code = data.py_sources[name];
    if (!code) throw new Error(`缺少 Python 模块: ${name}`);
    pyodide.FS.writeFile(`/py/${name}`, code);
  }

  pyodide.globals.set(
    '_py_order',
    data.py_load_order.map((n) => n.replace(/\.py$/, ''))
  );
  await pyodide.runPythonAsync(`
import importlib.util
import sys

for _name in _py_order:
    _path = f'/py/{_name}.py'
    _spec = importlib.util.spec_from_file_location(_name, _path)
    if _spec is None or _spec.loader is None:
        raise ImportError(f'无法加载模块 {_name} from {_path}')
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _mod
    _spec.loader.exec_module(_mod)
`);
}

function setStatus(text, cls = '') {
  els.status.textContent = text;
  els.status.className = cls;
}

function modeNeedsSkiJump(mode) {
  return mode === 'ski_jump' || mode === 'short_ski_jump';
}

function refreshModeButtons() {
  els.modeBtns.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.mode === currentMode);
  });
  els.skiJumpSection.classList.toggle('hidden', !modeNeedsSkiJump(currentMode));
}

function populateCarriers() {
  const list = filterCarriersForMode(currentMode, data.carriers);
  els.carrierSelect.innerHTML =
    list.length === 0
      ? '<option value="">（无可用航母）</option>'
      : list.map((c) => `<option value="${c.id}">${c.name}（${c.nation}）</option>`).join('');
  updateCarrierInfo();
}

function populateAircraft() {
  const list = filterAircraftForMode(currentMode, data.aircraft);
  els.aircraftSelect.innerHTML =
    list.length === 0
      ? '<option value="">（无可用战斗机）</option>'
      : list.map((a) => `<option value="${a.id}">${a.name}</option>`).join('');
  updateAircraftInfo();
}

function getSelectedCarrier() {
  const id = els.carrierSelect.value;
  return data.carriers.find((c) => c.id === id) || null;
}

function getSelectedAircraft() {
  const id = els.aircraftSelect.value;
  return data.aircraft.find((a) => a.id === id) || null;
}

function updateSkiJumpFromInputs() {
  const carrier = getSelectedCarrier();
  if (!carrier || !carrier.ski_jump) {
    skiGeom = null;
    return;
  }
  const angle = parseFloat(els.skiAngle.value);
  const arcLen = parseFloat(els.skiArcLength.value);
  if (Number.isNaN(angle) || angle <= 0) return;
  try {
    skiGeom = computeSkiJumpArc(
      angle,
      null,
      Number.isNaN(arcLen) || arcLen <= 0 ? null : arcLen
    );
    els.skiHeight.value = skiGeom.lip_height_m.toFixed(2);
    els.skiHorizontal.textContent = fmtNum(skiGeom.horizontal_m, 1);
  } catch (e) {
    skiGeom = null;
  }
}

function updateCarrierInfo() {
  const c = getSelectedCarrier();
  if (!c) {
    els.carrierSpecs.innerHTML = '<tr><td colspan="2">请选择航母</td></tr>';
    return;
  }

  if (c.ski_jump) {
    const base = resolveCarrierSkiJump(c);
    els.skiAngle.value = base.angle_deg;
    els.skiArcLength.value = base.arc_length_m.toFixed(1);
    updateSkiJumpFromInputs();
  }

  els.carrierSpecs.innerHTML = `
    <tr><th>最大航速</th><td>${fmtInt(c.max_speed_kt)} kt</td></tr>
    <tr><th>甲板总长度</th><td>${fmtNum(c.total_deck_length_m, 1)} m</td></tr>
    ${c.ski_jump ? '<tr><th>滑跃甲板</th><td>是 <span class="badge">参数可编辑</span></td></tr>' : '<tr><th>滑跃甲板</th><td>否（平直甲板）</td></tr>'}
  `;

  els.skiJumpSection.classList.toggle(
    'hidden',
    !modeNeedsSkiJump(currentMode) || !c.ski_jump
  );

  if (c.ski_jump && !els.windInput.dataset.userEdited) {
    els.windInput.value = c.max_speed_kt;
  }
}

function updateAircraftInfo() {
  const ac = getSelectedAircraft();
  if (!ac) {
    els.aircraftSpecs.innerHTML = '<tr><td colspan="2">请选择战斗机</td></tr>';
    return;
  }

  const aero = computeAircraftAero(ac);
  const isVtol = ac.type_label === 'v/stol';

  let thrustRows = '';
  if (isVtol) {
    thrustRows = `
      <tr><th>主喷管推力 (15°C SL)</th><td>${fmtNum(ac.t_main_stovl_sl_n / 1000, 1)} kN</td></tr>
      <tr><th>升力风扇推力</th><td>${fmtNum(ac.t_liftfan_sl_n / 1000, 1)} kN</td></tr>
      <tr><th>滚转喷管推力</th><td>${fmtNum(ac.t_rollposts_sl_n / 1000, 1)} kN</td></tr>
    `;
  } else {
    thrustRows = `<tr><th>最大加力推力 (15°C SL)</th><td>${fmtNum(ac.t_max_sl_n / 1000, 1)} kN</td></tr>`;
  }

  els.aircraftSpecs.innerHTML = `
    <tr><th>最大起飞重量 (MTOW)</th><td>${fmtInt(ac.mtow_kg)} kg</td></tr>
    <tr><th>最大内油</th><td>${fmtInt(ac.internal_fuel_kg)} kg</td></tr>
    <tr><th>中距弹型号</th><td>${ac.bvr_missile}</td></tr>
    <tr><th>中距弹重量</th><td>${fmtNum(ac.missile_mass_kg, 1)} kg/枚</td></tr>
    <tr><th>最大载弹量</th><td>${fmtInt(maxPayloadKg(ac))} kg</td></tr>
    <tr><th>4枚中距弹满内油空战起飞重量</th><td>${fmtInt(a2aMassKg(ac))} kg</td></tr>
    <tr><th>翼展</th><td>${fmtNum(ac.wingspan_m, 2)} m</td></tr>
    <tr><th>翼面积</th><td>${fmtNum(ac.wing_area_m2, 2)} m²</td></tr>
    ${thrustRows}
    <tr><th>前缘后掠角</th><td>${fmtNum(ac.sweep_le_deg, 1)}°</td></tr>
    <tr><th>展弦比</th><td>${fmtNum(aero.aspect_ratio, 3)}</td></tr>
    <tr><th>升力线斜率 C_Lα</th><td>${fmtNum(aero.cl_alpha_per_rad, 4)} /rad</td></tr>
    <tr><th>滑行升力系数 Cl_taxi</th><td>${fmtNum(aero.cl_taxi, 4)}（迎角 ${fmtNum(aero.taxi_alpha_deg, 1)}°）</td></tr>
    <tr><th>20° 攻角升力系数</th><td>${fmtNum(aero.cl_20deg, 4)}</td></tr>
    <tr><th>零升阻力系数 Cd0</th><td>${fmtNum(aero.cd0, 4)}</td></tr>
  `;

  if (!els.massInput.dataset.userEdited) {
    els.massInput.value = Math.round(a2aMassKg(ac));
  }
}

async function initPyodide() {
  if (pyReady) return;
  setStatus('正在加载 Python 仿真引擎（首次约需 20–40 秒）…', 'loading');
  els.runBtn.disabled = true;

  const { loadPyodide } = await import(
    `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.mjs`
  );
  pyodide = await loadPyodide();
  await pyodide.loadPackage('numpy');

  try {
    await loadPythonModules();
  } catch (e) {
    throw new Error(`Python 模块加载失败: ${e.message}`);
  }

  pyReady = true;
  els.runBtn.disabled = false;
  setStatus('仿真引擎已就绪', 'ok');
}

async function runSimulation() {
  const carrier = getSelectedCarrier();
  const aircraft = getSelectedAircraft();
  if (!carrier || !aircraft) {
    setStatus('请选择航母和战斗机', 'error');
    return;
  }

  const mass = parseFloat(els.massInput.value);
  const temp = parseFloat(els.tempInput.value);
  const wind = parseFloat(els.windInput.value);
  if ([mass, temp, wind].some((v) => Number.isNaN(v))) {
    setStatus('请填写有效的重量、温度和甲板风', 'error');
    return;
  }

  try {
    if (!pyReady) await initPyodide();
  } catch (e) {
    setStatus(`引擎加载失败: ${e.message}`, 'error');
    return;
  }

  els.runBtn.disabled = true;
  setStatus('仿真计算中（可能需要数秒至数十秒）…', 'loading');
  els.output.classList.remove('empty');
  els.output.textContent = '计算中…';

  const payload = {
    mode: currentMode,
    aircraft,
    carrier,
    mass_kg: mass,
    temp_c: temp,
    wind_kt: wind,
    total_deck_length_m: carrier.total_deck_length_m,
  };

  if (modeNeedsSkiJump(currentMode) && carrier.ski_jump) {
    updateSkiJumpFromInputs();
    payload.ski_jump_angle_deg = parseFloat(els.skiAngle.value);
    payload.ski_jump_arc_length_m = parseFloat(els.skiArcLength.value);
    payload.ski_jump_height_m = parseFloat(els.skiHeight.value);
  }

  try {
    pyodide.globals.set('_payload_json', JSON.stringify(payload));
    const raw = pyodide.runPython(`
import json
from web_simulator import run_simulation_json
json.dumps(run_simulation_json(_payload_json), ensure_ascii=False)
`);
    const result = JSON.parse(raw);
    els.output.textContent = result.output || '(无输出)';
    if (result.success) {
      setStatus(
        result.deck_launch_ok
          ? `仿真完成 — 甲板可用（余量 ${fmtNum(result.deck_margin_m, 1)} m）`
          : `仿真完成 — 甲板不足（超出 ${fmtNum(-result.deck_margin_m, 1)} m）`,
        result.deck_launch_ok ? 'ok' : 'error'
      );
    } else {
      setStatus(result.error || '仿真失败', 'error');
    }
  } catch (e) {
    els.output.textContent = String(e);
    setStatus(`仿真出错: ${e.message}`, 'error');
  } finally {
    els.runBtn.disabled = false;
  }
}

function bindEvents() {
  els.modeBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      currentMode = btn.dataset.mode;
      refreshModeButtons();
      populateCarriers();
      populateAircraft();
      els.massInput.dataset.userEdited = '';
      els.windInput.dataset.userEdited = '';
    });
  });

  els.carrierSelect.addEventListener('change', () => {
    els.windInput.dataset.userEdited = '';
    updateCarrierInfo();
  });

  els.aircraftSelect.addEventListener('change', () => {
    els.massInput.dataset.userEdited = '';
    updateAircraftInfo();
  });

  els.skiAngle.addEventListener('input', updateSkiJumpFromInputs);
  els.skiArcLength.addEventListener('input', updateSkiJumpFromInputs);

  els.windInput.addEventListener('input', () => {
    els.windInput.dataset.userEdited = '1';
  });
  els.massInput.addEventListener('input', () => {
    els.massInput.dataset.userEdited = '1';
  });

  els.runBtn.addEventListener('click', runSimulation);

  els.preloadBtn.addEventListener('click', () => initPyodide().catch((e) => setStatus(e.message, 'error')));
}

async function main() {
  els.modeBtns = [...document.querySelectorAll('.mode-btn')];
  els.carrierSelect = $('carrierSelect');
  els.aircraftSelect = $('aircraftSelect');
  els.carrierSpecs = $('carrierSpecs');
  els.aircraftSpecs = $('aircraftSpecs');
  els.skiJumpSection = $('skiJumpSection');
  els.skiAngle = $('skiAngle');
  els.skiArcLength = $('skiArcLength');
  els.skiHeight = $('skiHeight');
  els.skiHorizontal = $('skiHorizontal');
  els.windInput = $('windInput');
  els.tempInput = $('tempInput');
  els.massInput = $('massInput');
  els.runBtn = $('runBtn');
  els.preloadBtn = $('preloadBtn');
  els.output = $('output');
  els.status = $('status');

  try {
    await loadData();
  } catch (e) {
    setStatus(e.message, 'error');
    return;
  }

  refreshModeButtons();
  populateCarriers();
  populateAircraft();
  bindEvents();

  els.tempInput.value = 30;
  setStatus('页面已加载。点击「预加载引擎」或「开始仿真」时将加载 Python 引擎。', '');
}

main();
