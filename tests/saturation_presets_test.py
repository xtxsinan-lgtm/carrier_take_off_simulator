"""饱和打击预设单元测试。"""
from __future__ import annotations

from utils.saturation_presets import (
    AEW_PRESETS,
    ASM_PRESETS,
    SAM_PRESETS,
    SHIP_PRESETS,
    build_saturation_presets_payload,
    get_preset_by_id,
)


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
    """目录载荷含四类预设且非空。"""
    payload = build_saturation_presets_payload()
    assert set(payload) == {'asm', 'aew', 'ship', 'sam'}
    assert len(payload['asm']) == len(ASM_PRESETS)
    assert len(payload['aew']) == len(AEW_PRESETS)
    assert len(payload['ship']) == len(SHIP_PRESETS)
    assert len(payload['sam']) == len(SAM_PRESETS)
    assert all('id' in x and 'name' in x for x in payload['sam'])
