# 航母舰载机起飞仿真 — iOS App

SwiftUI 原生界面，布局与小程序对齐。**数据与仿真均在设备本地完成**（Bundle `data.json` + Pyodide 跑同一套 Python），不依赖 HTTP 后端。

## 架构

```
iPhone App (SwiftUI)
  ├─ Bundle data.json（机库目录 + py_sources，由 build_all 生成）
  ├─ Physics.swift（参数预览，由 Python 生成）
  └─ LocalSimulatorEngine（隐藏 WKWebView + Pyodide）
         └─ apps.web_simulator.run_simulation_json（与 Web 同源）
```

微信小程序仍使用 `python3 apps/miniprogram_api.py`；iOS **不需要**该服务。

## 快速开始

### 1. 构建数据与物理

```bash
python3 scripts/build_all.py
```

### 2. 打开 Xcode 工程

需要完整版 Xcode：

```bash
python3 scripts/generate_ios_xcodeproj.py   # 若尚未生成
open ios/CarrierTakeOff.xcodeproj
```

选模拟器或真机 → Run。首次启动会从 CDN 拉取 Pyodide/numpy（仅引擎运行时）；仿真计算在本机完成。

若模拟器仍报 *Your team has no devices…*：确认目标是 **iOS Simulators** 下的设备（名称旁有模拟器图标），然后 **Product → Clean Build Folder** 再 Run。工程已对 `iphonesimulator` SDK 关闭强制签名。

## 与其他通道同步

| 项目 | 来源 |
|------|------|
| 模式 / 策略 / 机库 | `scripts/frontend_catalog.py` → `Resources/data.json` |
| 预览物理常量 | `generate_frontend_physics.py` → `Physics.swift` |
| 仿真数值 | Bundle 内 `py_sources` → 本地 Pyodide → `web_simulator` |

**禁止手改** `Physics.swift`、`Resources/data.json`（由 build 生成）。

## 界面结构（与小程序一致）

1. 起飞模式（+ 策略）
2. 航母（含可编辑滑跃参数）
3. 战斗机
4. 仿真条件 → 开始仿真
5. 仿真输出
6. 起飞轨迹（滑跃 / 短距滑跃成功后）
