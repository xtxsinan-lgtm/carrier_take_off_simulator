const config = require('../config.js');

/** 加载航母/战斗机数据库 */
function loadSimulatorData() {
  const base = config.apiBaseUrl;
  if (base) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${base}/api/data`,
        method: 'GET',
        success(res) {
          if (res.statusCode >= 200 && res.statusCode < 300 && res.data) {
            resolve(res.data);
          } else {
            reject(new Error(`加载数据失败 (${res.statusCode})`));
          }
        },
        fail(err) {
          reject(new Error(err.errMsg || '网络请求失败'));
        },
      });
    });
  }
  return new Promise((resolve, reject) => {
    try {
      const data = require('../data/data.json');
      resolve(data);
    } catch (e) {
      reject(new Error('缺少 data/data.json，请运行 python3 scripts/build_miniprogram.py'));
    }
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

module.exports = {
  loadSimulatorData,
  runSimulation,
};
