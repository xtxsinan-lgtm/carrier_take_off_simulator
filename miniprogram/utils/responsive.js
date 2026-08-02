/**
 * 屏幕适配：基于微信 750rpx 设计稿与安全区。
 */

/** 获取窗口与安全区度量 */
function getWindowMetrics() {
  const sys = wx.getSystemInfoSync();
  const safeBottom = Math.max(0, sys.screenHeight - (sys.safeArea ? sys.safeArea.bottom : sys.screenHeight));
  return {
    windowWidth: sys.windowWidth,
    windowHeight: sys.windowHeight,
    screenWidth: sys.screenWidth,
    screenHeight: sys.screenHeight,
    pixelRatio: sys.pixelRatio || 2,
    safeArea: sys.safeArea || { top: 0, bottom: sys.screenHeight, left: 0, right: sys.windowWidth },
    safeBottom,
    /** 1rpx 对应的 px */
    rpxRatio: sys.windowWidth / 750,
  };
}

/** rpx 转 px（用于 Canvas 物理像素计算） */
function rpxToPx(rpx) {
  const { windowWidth } = wx.getSystemInfoSync();
  return (rpx * windowWidth) / 750;
}

/** 根据屏幕宽度返回轨迹图 Canvas 高度（rpx） */
function trajectoryCanvasHeightRpx() {
  const { windowWidth } = wx.getSystemInfoSync();
  if (windowWidth >= 414) return 420;
  if (windowWidth >= 375) return 380;
  return 340;
}

module.exports = {
  getWindowMetrics,
  rpxToPx,
  trajectoryCanvasHeightRpx,
};
