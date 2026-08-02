const config = require('../config.js');

/** 读取内置航母/战斗机数据库（不依赖网络） */
function loadLocalData() {
  try {
    return require('../data/data.json');
  } catch (e) {
    throw new Error('缺少 data/data.json，请运行 python3 scripts/build_miniprogram.py');
  }
}

/**
 * 加载仿真数据：优先使用本地 data.json，保证界面可选；
 * 若配置了 apiBaseUrl，再尝试用远端数据覆盖（失败则保留本地）。
 */
function loadSimulatorData() {
  const local = loadLocalData();
  const base = config.apiBaseUrl;
  if (!base) {
    return Promise.resolve(local);
  }
  return new Promise((resolve) => {
    wx.request({
      url: `${base}/api/data`,
      method: 'GET',
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data && res.data.carriers) {
          resolve(res.data);
        } else {
          resolve(local);
        }
      },
      fail() {
        // 本地调试网络不通时仍可用内置数据选参数
        resolve(local);
      },
    });
  });
}

/** 调用后端 Python 仿真 API */
function runSimulation(payload) {
  const base = config.apiBaseUrl;
  if (!base) {
    return Promise.reject(
      new Error('未配置 apiBaseUrl。请在 config.js 填写后端地址，或运行 python3 apps/miniprogram_api.py')
    );
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${base}/api/simulate`,
      method: 'POST',
      header: { 'content-type': 'application/json' },
      data: payload,
      timeout: 120000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data) {
          resolve(res.data);
        } else {
          const msg = (res.data && res.data.error) || `仿真请求失败 (${res.statusCode})`;
          reject(new Error(msg));
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || '仿真网络请求失败'));
      },
    });
  });
}

/** 将 modes 对象转为 [{id, label}]，供小程序可靠渲染 */
function modesToList(modes) {
  const src = modes || {};
  return Object.keys(src).map((id) => ({ id, label: src[id] }));
}

module.exports = {
  loadLocalData,
  loadSimulatorData,
  runSimulation,
  modesToList,
};
