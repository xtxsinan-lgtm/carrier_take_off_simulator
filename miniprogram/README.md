# 微信小程序 — 航母舰载机起飞仿真

基于腾讯微信小程序原生框架，面向手机端使用，采用 **rpx + 安全区** 自适应不同屏幕尺寸。

## 目录结构

```
miniprogram/
  app.js / app.json / app.wxss   # 全局入口与深色主题
  config.js                      # API 地址配置
  data/data.json                 # 内置航母/战斗机数据（由脚本生成）
  pages/index/                   # 主仿真页
  components/                    # 模式选择、参数列表、轨迹 Canvas
  utils/                         # 物理预览、API、屏幕适配、轨迹绘制
```

## 快速开始

### 1. 一键构建（推荐）

```bash
python3 scripts/build_all.py
```

会生成：`physics.js`（Web + 小程序）、`docs/data.json`、`miniprogram/data/data.json`。

### 2. 启动仿真 API（小程序无法运行 Pyodide，需后端）

```bash
python3 apps/miniprogram_api.py
# 默认 http://127.0.0.1:8765
```

### 3. 配置 API 地址

编辑 `miniprogram/config.js`：

```js
module.exports = {
  apiBaseUrl: 'http://127.0.0.1:8765',  // 本地调试
};
```

### 4. 用微信开发者工具打开

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 导入项目，目录选择本仓库的 `miniprogram/`
3. **详情 → 本地设置 → 勾选「不校验合法域名、web-view…」**（本地 HTTP 调试必需）
4. 编译预览

正式发布前：

- 将 `apiBaseUrl` 改为 **HTTPS 已备案域名**
- 在微信公众平台配置 **request 合法域名**
- 在 `project.config.json` 中填写真实 `appid`

## 与 Web / Python 的同步

- **仿真数值**：小程序 API 与网页 Pyodide 均调用同一 `apps/web_simulator.run_simulation_json`
- **机库数据**：来自 `data/*.csv`，由 `build_all.py` 写入两端 `data.json`
- **参数预览物理**：由 `generate_frontend_physics.py` 从 Python 常量生成，**禁止手改** `utils/physics.js`

详见仓库根目录构建脚本与 `tests/frontend_build_sync_test.py`。

## 屏幕适配说明

| 机制 | 用途 |
|------|------|
| `rpx` | 以 750 设计宽等比缩放，全页面布局 |
| `env(safe-area-inset-bottom)` | 底部安全区（全面屏/Home 条） |
| `trajectoryCanvasHeightRpx()` | 按屏宽动态调整轨迹图高度 |
| `@media (min-width: …)` | 模式按钮、表单列数随屏宽变化 |
| Canvas 2D + `pixelRatio` | 轨迹图高清绘制 |

## 与 Web 版差异

| 项目 | Web (GitHub Pages) | 微信小程序 |
|------|-------------------|-----------|
| 仿真引擎 | 浏览器 Pyodide | 后端 `miniprogram_api.py` |
| 数据 | `docs/data.json` | `miniprogram/data/data.json` |
| 参数预览 | `physics.js` | 同逻辑移植至 `utils/physics.js` |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data` | 航母/战斗机数据库 |
| POST | `/api/simulate` | 运行仿真，body 同 Web 版 payload |
