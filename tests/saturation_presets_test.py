"""饱和打击 CSV 预设单元测试。"""
from __future__ import annotations

from utils.saturation_presets import (
    AEW_PRESETS,
    ASM_PRESETS,
    SAM_PRESETS,
    SHIP_PRESETS,
    build_saturation_presets_payload,
    get_preset_by_id,
    load_presets,
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
