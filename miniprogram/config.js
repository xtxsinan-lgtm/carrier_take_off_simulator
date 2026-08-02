/**
 * 小程序运行时配置。
 * 正式发布前请将 apiBaseUrl 改为已备案 HTTPS 域名，并在微信公众平台配置 request 合法域名。
 * 本地调试：开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名」。
 */
module.exports = {
  /** 仿真 API 根地址，末尾不要斜杠。空字符串表示使用本地 data/data.json + 需配置后端 */
  apiBaseUrl: 'http://127.0.0.1:8765',
  /** 内置数据版本（与 data/data.json 中 version 对应） */
  dataVersion: 10,
};
