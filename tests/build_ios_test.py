"""build_ios 脚本单元测试。"""
from __future__ import annotations

from scripts.build_ios import build_ios_data


def test_build_ios_data_has_required_keys():
    """iOS 目录数据必须含 modes / carriers / aircraft / py_sources。"""
    data = build_ios_data()
    assert 'modes' in data and data['modes']
    assert 'carriers' in data and len(data['carriers']) >= 1
    assert 'aircraft' in data and len(data['aircraft']) >= 1
    assert 'stovl_strategies' in data
    assert 'tiltrotor_strategies' in data
    assert 'py_sources' in data and len(data['py_sources']) >= 1
    assert 'py_load_order' in data


def test_build_ios_data_modes_match_miniprogram_keys():
    """iOS 与小程序模式键集合一致（忽略 iOS 额外的 py_* 字段）。"""
    from scripts.build_miniprogram import build_miniprogram_data

    ios = build_ios_data()
    mini = build_miniprogram_data()
    assert set(ios['modes']) == set(mini['modes'])
    assert ios['carriers'] == mini['carriers']
    assert ios['aircraft'] == mini['aircraft']
