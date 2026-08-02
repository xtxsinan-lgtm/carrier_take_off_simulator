/**
 * 小程序运行时配置。
 * 正式发布前请将 apiBaseUrl 改为已备案 HTTPS 域名，并在微信公众平台配置 request 合法域名。
 * 本地调试：开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名」。
 */
module.exports = {
  /**
   * 仿真 API 根地址，末尾不要斜杠。
   * - 开发者工具模拟器：http://127.0.0.1:8765
   * - 真机调试/预览：改为 Mac 局域网 IP，如 http://192.168.1.90:8765
   *   （API 需 python3 apps/simulator_api.py --host 0.0.0.0）
   */
  apiBaseUrl: 'http://127.0.0.1:8765',
  /** 内置数据版本（与 data/data.json 中 version 对应） */
  dataVersion: 11,
};
