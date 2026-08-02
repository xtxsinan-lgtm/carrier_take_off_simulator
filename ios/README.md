# 航母舰载机起飞仿真 — iOS App

SwiftUI 原生界面，布局与交互对齐微信小程序 / Web 版（深色主题、6 段卡片、轨迹图）。

## 架构

```
iPhone App (SwiftUI)
  ├─ Bundle data.json（机库目录，由 build_all 生成）
  ├─ Physics.swift（预览气动/滑跃，由 Python 生成）
  └─ HTTP → apps/simulator_api.py（与小程序同一仿真 API）
```

## 快速开始

### 1. 构建数据与物理

```bash
python3 scripts/build_all.py
```

### 2. 启动仿真 API

```bash
# 模拟器可用 127.0.0.1；真机需局域网
python3 apps/simulator_api.py --host 0.0.0.0
```

### 3. 配置 API 地址

编辑 `CarrierTakeOff/Config.swift`：

- 模拟器：`http://127.0.0.1:8765`
- 真机：`http://<Mac局域网IP>:8765`

### 4. 打开 Xcode 工程

需要安装完整版 [Xcode](https://developer.apple.com/xcode/)（仅 Command Line Tools 无法跑模拟器）。

```bash
# 若尚未生成工程：
python3 scripts/generate_ios_xcodeproj.py
# 或一键：python3 scripts/build_all.py

open ios/CarrierTakeOff.xcodeproj
```

选择 iPhone 模拟器或真机 → Run。

也可用 XcodeGen（可选）：`cd ios && xcodegen generate`。

## 与其他通道同步

| 项目 | 来源 |
|------|------|
| 模式 / 策略 / 机库 | `scripts/frontend_catalog.py` → `Resources/data.json` |
| 预览物理常量 | `generate_frontend_physics.py` → `Physics.swift` |
| 仿真数值 | `simulator_api` → `web_simulator.run_simulation_json` |

**禁止手改** `Physics.swift`、`Resources/data.json`（与 JS 产物一样由 build 生成）。

## 界面结构（与小程序一致）

1. 起飞模式（+ 策略）
2. 航母（含可编辑滑跃参数）
3. 战斗机
4. 仿真条件 → 开始仿真
5. 仿真输出
6. 起飞轨迹（滑跃 / 短距滑跃成功后）
