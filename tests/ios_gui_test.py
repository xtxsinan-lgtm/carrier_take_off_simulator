"""iOS GUI 通道相关单元测试（源码结构与本地引擎契约）。"""
from __future__ import annotations

from utils.paths import ROOT

IOS_ROOT = ROOT / 'ios' / 'CarrierTakeOff'


def test_ios_swift_sources_exist():
    """主界面与本地引擎模块文件必须存在。"""
    required = [
        'CarrierTakeOffApp.swift',
        'ContentView.swift',
        'SimulatorViewModel.swift',
        'CatalogStore.swift',
        'LocalSimulatorEngine.swift',
        'Models.swift',
        'Physics.swift',
        'Config.swift',
        'Theme.swift',
        'Info.plist',
        'Components/ModeSelector.swift',
        'Components/SpecList.swift',
        'Components/TrajectoryChart.swift',
        'Resources/engine.html',
        'Resources/engine.js',
    ]
    for rel in required:
        path = IOS_ROOT / rel
        assert path.is_file(), f'缺少 iOS 源文件: {rel}'


def test_ios_content_view_has_six_sections():
    """主界面文案须覆盖与小程序相同的 1–6 段卡片标题。"""
    text = (IOS_ROOT / 'ContentView.swift').read_text(encoding='utf-8')
    for title in (
        '1. 起飞模式',
        '2. 航母',
        '3. 战斗机',
        '4. 仿真条件',
        '5. 仿真输出',
        '6. 起飞轨迹',
    ):
        assert title in text, f'ContentView 缺少卡片: {title}'


def test_ios_uses_local_engine_not_http_api():
    """iOS 仿真应走 LocalSimulatorEngine，而非 HTTP API。"""
    vm = (IOS_ROOT / 'SimulatorViewModel.swift').read_text(encoding='utf-8')
    assert 'LocalSimulatorEngine' in vm
    assert 'apiBaseUrl' not in vm
    assert 'APIClient' not in vm
    engine_js = (IOS_ROOT / 'Resources' / 'engine.js').read_text(encoding='utf-8')
    assert 'run_simulation_json' in engine_js
    assert 'loadPyodide' in engine_js
    assert '__BUNDLED_CATALOG__' in engine_js
    engine_swift = (IOS_ROOT / 'LocalSimulatorEngine.swift').read_text(encoding='utf-8')
    assert '__BUNDLED_CATALOG__' in engine_swift


def test_ios_project_yml_exists():
    """XcodeGen 工程描述须存在，便于生成 .xcodeproj。"""
    assert (ROOT / 'ios' / 'project.yml').is_file()
