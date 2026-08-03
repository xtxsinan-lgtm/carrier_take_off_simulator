"""饱和打击「估算交战距离与拦截率」三端 UI 同步单元测试。"""
from __future__ import annotations

import re

from utils.paths import ROOT

ESTIMATE_BTN = '◈ 估算交战距离与拦截率'
# 按钮下方仅保留的两字段（文案关键词，允许各端略有后缀）
BELOW_LABELS = ('雷达发现距离', '单发拦截成功概率')
# 须移到按钮上方的字段关键词（各端文案略有差异时用元组表示任一即可）
ABOVE_KEYS = (
    ('拦截弹数量',),
    ('拦截弹飞行速度', '拦截弹速度'),
    ('拦截弹直径',),
    ('火控锁定',),
    ('最小交战距离',),
)


def _first_match_index(text: str, options: tuple[str, ...]) -> tuple[str, int]:
    """返回首个命中关键词及其下标。"""
    for key in options:
        idx = text.find(key)
        if idx >= 0:
            return key, idx
    raise AssertionError(f'未找到任一关键词: {options}')


def test_first_match_index_prefers_earlier_option():
    """_first_match_index 按选项顺序返回首个命中。"""
    key, idx = _first_match_index('拦截弹飞行速度 Ma', ('拦截弹飞行速度', '拦截弹速度'))
    assert key == '拦截弹飞行速度'
    assert idx == 0
    key2, idx2 = _first_match_index('拦截弹速度 Ma', ('拦截弹飞行速度', '拦截弹速度'))
    assert key2 == '拦截弹速度'
    assert idx2 == 0


def _assert_merged_estimate_layout(text: str, channel: str) -> None:
    """断言合并估算按钮、旧双按钮消失、下方仅两结果字段。"""
    assert ESTIMATE_BTN in text, f'{channel} 缺少合并估算按钮文案'
    assert text.count(ESTIMATE_BTN) == 1, f'{channel} 合并估算按钮应仅出现一次'
    # 旧独立按钮不得残留
    assert '估算 Pk' not in text, f'{channel} 仍含旧「估算 Pk」按钮'
    assert '估算交战距离"' not in text and "估算交战距离'" not in text
    assert '◈ 估算交战距离\n' not in text
    assert '◈ 估算交战距离<' not in text

    btn_idx = text.index(ESTIMATE_BTN)
    for options in ABOVE_KEYS:
        key, idx = _first_match_index(text, options)
        assert idx < btn_idx, f'{channel} 字段「{key}」须在估算按钮上方'

    for label in BELOW_LABELS:
        assert label in text, f'{channel} 缺少下方字段: {label}'
        assert text.index(label) > btn_idx, f'{channel} 字段「{label}」须在估算按钮下方'

    # 下方两字段相对顺序：发现距离 → 单发拦截成功概率
    assert text.index(BELOW_LABELS[0]) < text.index(BELOW_LABELS[1]), (
        f'{channel} 下方字段顺序应为雷达发现距离 → 单发拦截成功概率'
    )


def test_html_saturation_merged_estimate_ui():
    """HTML 饱和页：合并估算按钮，仅 D/Pk 在下方。"""
    html = (ROOT / 'docs' / 'saturation-strike.html').read_text(encoding='utf-8')
    js = (ROOT / 'docs' / 'js' / 'saturation.js').read_text(encoding='utf-8')
    _assert_merged_estimate_layout(html, 'HTML')
    assert 'id="estimateBtn"' in html
    assert 'id="distBtn"' not in html
    assert 'id="estBtn"' not in html
    assert 'onEstimateDistanceAndPk' in js
    assert "callPython('estimate_distance'" in js
    assert "callPython('estimate_pk'" in js
    # 缓存版本与 HTML 引用一致
    ver_js = re.search(r'const APP_VERSION\s*=\s*(\d+)', js)
    ver_html = re.search(r'saturation\.js\?v=(\d+)', html)
    assert ver_js and ver_html and ver_js.group(1) == ver_html.group(1)


def test_miniprogram_saturation_merged_estimate_ui():
    """小程序饱和页：合并估算按钮与 HTML 同构。"""
    wxml = (ROOT / 'miniprogram' / 'pages' / 'saturation' / 'saturation.wxml').read_text(
        encoding='utf-8'
    )
    js = (ROOT / 'miniprogram' / 'pages' / 'saturation' / 'saturation.js').read_text(
        encoding='utf-8'
    )
    _assert_merged_estimate_layout(wxml, '小程序')
    assert 'bindtap="onEstimateDistanceAndPk"' in wxml
    assert 'onEstimateDistanceAndPk' in js
    assert "action: 'estimate_distance'" in js
    assert "action: 'estimate_pk'" in js
    assert 'bindtap="onEstimateDistance"' not in wxml
    assert 'bindtap="onEstimatePk"' not in wxml


def test_ios_saturation_merged_estimate_ui():
    """iOS 饱和页：合并估算按钮与 HTML / 小程序同构。"""
    view = (ROOT / 'ios' / 'CarrierTakeOff' / 'SaturationStrikeView.swift').read_text(
        encoding='utf-8'
    )
    vm = (ROOT / 'ios' / 'CarrierTakeOff' / 'SaturationViewModel.swift').read_text(
        encoding='utf-8'
    )
    _assert_merged_estimate_layout(view, 'iOS')
    assert 'estimateDistanceAndPk' in view
    assert 'func estimateDistanceAndPk' in vm
    assert '"estimate_distance"' in vm
    assert '"estimate_pk"' in vm
    assert 'Button("◈ 估算交战距离")' not in view
    assert 'Button("◈ 估算 Pk")' not in view
    assert 'func estimateDistance()' not in vm
    assert 'func estimatePk()' not in vm


def test_catalog_saturation_subtitle_mentions_intercept_rate():
    """启动页副标题须反映交战距离与拦截率估算（非旧 Pk 文案）。"""
    from scripts.frontend_catalog import SIMULATORS

    sat = next(s for s in SIMULATORS if s['id'] == 'saturation')
    assert '拦截率' in sat['subtitle']
    assert 'Pk 估算' not in sat['subtitle']


def test_saturation_ui_no_ecm_fields():
    """三端 UI 与估算传参均不含抗干扰档数。"""
    html = (ROOT / 'docs' / 'saturation-strike.html').read_text(encoding='utf-8')
    web_js = (ROOT / 'docs' / 'js' / 'saturation.js').read_text(encoding='utf-8')
    wxml = (ROOT / 'miniprogram' / 'pages' / 'saturation' / 'saturation.wxml').read_text(
        encoding='utf-8'
    )
    mp_js = (ROOT / 'miniprogram' / 'pages' / 'saturation' / 'saturation.js').read_text(
        encoding='utf-8'
    )
    view = (ROOT / 'ios' / 'CarrierTakeOff' / 'SaturationStrikeView.swift').read_text(
        encoding='utf-8'
    )
    vm = (ROOT / 'ios' / 'CarrierTakeOff' / 'SaturationViewModel.swift').read_text(
        encoding='utf-8'
    )
    assert 'id="ecm"' not in html
    assert '抗干扰' not in html
    assert 'ecm:' not in web_js
    assert '抗干扰系数' not in web_js
    assert '抗干扰' not in wxml
    assert 'ecm:' not in mp_js
    assert '抗干扰' not in view
    assert '"ecm"' not in vm
