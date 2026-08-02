"""build_miniprogram 脚本单元测试。"""
from __future__ import annotations

from scripts.build_miniprogram import build_miniprogram_data, render_data_js


def test_build_miniprogram_data_has_required_keys():
    data = build_miniprogram_data()
    assert data['version'] >= 1
    assert 'modes' in data
    assert 'aircraft' in data and len(data['aircraft']) >= 1
    assert 'carriers' in data and len(data['carriers']) >= 1
    assert 'py_sources' not in data


def test_render_data_js_is_commonjs_module():
    text = render_data_js(build_miniprogram_data())
    assert text.startswith('/**')
    assert 'module.exports =' in text
    assert '"ski_jump"' in text
