"""饱和打击 CSV 预设单元测试。"""
from __future__ import annotations

from utils.saturation_presets import (
    AEW_PRESETS,
    ASM_PRESETS,
    SAM_PRESETS,
    SHIP_PRESETS,
    build_saturation_presets_payload,
    filter_presets_by_nation,
    get_preset_by_id,
    load_presets,
    nations_sorted,
)
from utils.paths import SATURATION_MISSILE_CSV, SATURATION_RADAR_CSV


def test_get_preset_by_id_found():
    """能按 id 找到反舰导弹预设。"""
    p = get_preset_by_id(ASM_PRESETS, 'yj12')
    assert p is not None
    assert p['vm'] == 3.5
    assert p['traj'] == 'high'


def test_get_preset_by_id_missing():
    """未知 id 返回 None。"""
    assert get_preset_by_id(ASM_PRESETS, 'no-such') is None


def test_build_saturation_presets_payload_keys():
    """目录载荷含四类预设且与 CSV 一致。"""
    payload = build_saturation_presets_payload()
    assert set(payload) == {'asm', 'aew', 'ship', 'sam'}
    assert len(payload['asm']) == len(ASM_PRESETS)
    assert len(payload['aew']) == len(AEW_PRESETS)
    assert len(payload['ship']) == len(SHIP_PRESETS)
    assert len(payload['sam']) == len(SAM_PRESETS)
    assert all('id' in x and 'name' in x for x in payload['sam'])


def test_load_presets_from_csv_path():
    """显式双库路径加载与默认路径一致。"""
    a = load_presets(SATURATION_MISSILE_CSV, SATURATION_RADAR_CSV)
    b = load_presets()
    assert [x['id'] for x in a['asm']] == [x['id'] for x in b['asm']]
    assert [x['id'] for x in a['aew']] == [x['id'] for x in b['aew']]


def test_load_presets_missing_file_returns_empty():
    """任一 CSV 不存在时返回空分组（Pyodide 等环境）。"""
    empty = load_presets('/tmp/no-such-missile.csv', '/tmp/no-such-radar.csv')
    assert empty == {'asm': [], 'aew': [], 'ship': [], 'sam': []}
    half = load_presets('/tmp/no-such-missile.csv', SATURATION_RADAR_CSV)
    assert half == {'asm': [], 'aew': [], 'ship': [], 'sam': []}


def test_nations_sorted_dedups_by_first_appearance():
    """国别按首次出现顺序去重，忽略空白与缺失。"""
    presets = [
        {'id': 'a', 'nation': '中国'},
        {'id': 'b', 'nation': '美国'},
        {'id': 'c', 'nation': '中国'},
        {'id': 'd', 'nation': ' '},
        {'id': 'e'},
    ]
    assert nations_sorted(presets) == ['中国', '美国']


def test_nations_sorted_on_real_presets():
    """真实预设的国别列表非空且不含空串。"""
    for presets in (ASM_PRESETS, SAM_PRESETS, SHIP_PRESETS, AEW_PRESETS):
        nations = nations_sorted(presets)
        assert nations
        assert all(n.strip() for n in nations)
    assert '中国' in nations_sorted(ASM_PRESETS)
    assert '美国' in nations_sorted(SHIP_PRESETS)


def test_filter_presets_by_nation():
    """按国别过滤只返回该国别型号。"""
    china = filter_presets_by_nation(ASM_PRESETS, '中国')
    assert china
    assert all(x['nation'] == '中国' for x in china)
    assert 'yj12' in [x['id'] for x in china]
    assert 'harpoon' not in [x['id'] for x in china]


def test_filter_presets_by_nation_empty_returns_all():
    """国别为空视为不限国别，返回全部型号。"""
    assert len(filter_presets_by_nation(SAM_PRESETS, '')) == len(SAM_PRESETS)
    assert filter_presets_by_nation(SAM_PRESETS, '  ') == list(SAM_PRESETS)
    assert filter_presets_by_nation(SAM_PRESETS, '不存在的国别') == []


def test_payload_presets_carry_nation():
    """目录载荷四类预设均带国别，供前端两级选择。"""
    payload = build_saturation_presets_payload()
    for cat in ('asm', 'sam', 'ship', 'aew'):
        assert all(x.get('nation') for x in payload[cat]), f'{cat} 存在无国别预设'
