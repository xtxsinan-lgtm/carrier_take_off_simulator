const config = require('./config.js');
const { getWindowMetrics } = require('./utils/responsive.js');

App({
  globalData: {
    config,
    /** 系统窗口与安全区信息，供各页面做 Canvas 尺寸计算 */
    systemInfo: null,
  },

  onLaunch() {
    try {
      this.globalData.systemInfo = getWindowMetrics();
    } catch (e) {
      console.warn('获取系统信息失败', e);
    }
  },
});
