"""build_miniprogram 脚本单元测试。"""
from __future__ import annotations

from scripts.build_miniprogram import build_miniprogram_data


def test_build_miniprogram_data_has_required_keys():
    data = build_miniprogram_data()
    assert data['version'] >= 1
    assert 'modes' in data
    assert 'aircraft' in data and len(data['aircraft']) >= 1
    assert 'carriers' in data and len(data['carriers']) >= 1
    assert 'py_sources' not in data
