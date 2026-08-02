"""api / modesToList 与数据加载相关单元测试。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_miniprogram_data_json_has_carriers_and_modes():
    """内置 data.json 必须含 modes / carriers / aircraft，供本地界面渲染。"""
    path = ROOT / 'miniprogram' / 'data' / 'data.json'
    assert path.is_file(), '缺少 miniprogram/data/data.json，请运行 build_miniprogram.py'
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['modes']['ski_jump'] == '滑跃起飞'
    assert len(data['carriers']) >= 1
    assert any(c.get('ski_jump') for c in data['carriers'])
    assert len(data['aircraft']) >= 1


def test_modes_to_list_shape_matches_miniprogram_contract():
    """modes 对象转为 [{id,label}]，与小程序 mode-selector 约定一致。"""
    modes = {
        'ski_jump': '滑跃起飞',
        'short_takeoff': '短距起飞',
        'short_ski_jump': '短距滑跃起飞',
    }
    # 与 miniprogram/utils/api.js modesToList 同逻辑（Python 侧校验契约）
    mode_list = [{'id': k, 'label': v} for k, v in modes.items()]
    assert len(mode_list) == 3
    assert mode_list[0] == {'id': 'ski_jump', 'label': '滑跃起飞'}


def test_trajectory_chart_is_inline_below_sim_output():
    """轨迹图须跟在仿真输出卡片后进入文档流，不得用底部固定坞（traj-dock）。"""
    wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')
    wxss = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxss').read_text(encoding='utf-8')
    assert 'traj-dock' not in wxml
    assert 'traj-dock' not in wxss
    assert 'page-root' not in wxml
    assert '5. 仿真输出' in wxml
    assert '6. 起飞轨迹' in wxml
    assert 'trajectory-chart' in wxml
    # 轨迹区块须出现在仿真输出之后，保证滚动时随内容离开视口
    assert wxml.index('5. 仿真输出') < wxml.index('6. 起飞轨迹')
    assert wxml.index('6. 起飞轨迹') < wxml.index('page-footer')