"""饱和打击仿真的公开资料预设（反舰弹 / 预警机 / 舰载雷达 / 防空弹）。

型号列表以导弹库与雷达库 CSV 为数据源：
  data/missile_interception_missile_database.csv（asm / sam）
  data/missile_interception_radar_database.csv（aew / ship）
前端经 build_all → data.json 的 missile_interception_presets 自动同步。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.database_csv import load_missile_interception_presets_csv
from utils.paths import MISSILE_INTERCEPTION_MISSILE_CSV, MISSILE_INTERCEPTION_RADAR_CSV


def load_presets(
    missile_path: str | Path | None = None,
    radar_path: str | Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """从导弹库 + 雷达库加载四类预设；任一文件不存在时返回空分组（如 Pyodide 环境）。"""
    m_path = Path(missile_path) if missile_path is not None else MISSILE_INTERCEPTION_MISSILE_CSV
    r_path = Path(radar_path) if radar_path is not None else MISSILE_INTERCEPTION_RADAR_CSV
    if not m_path.is_file() or not r_path.is_file():
        return {'asm': [], 'aew': [], 'ship': [], 'sam': []}
    return load_missile_interception_presets_csv(m_path, r_path)


def get_preset_by_id(presets: list[dict[str, Any]], preset_id: str) -> dict[str, Any] | None:
    """按 id 查找预设；找不到返回 None。"""
    for item in presets:
        if item['id'] == preset_id:
            return item
    return None


def nations_sorted(presets: list[dict[str, Any]]) -> list[str]:
    """从预设列表提取去重国别并稳定排序（按首次出现顺序）。"""
    seen: list[str] = []
    for item in presets:
        nation = (item.get('nation') or '').strip()
        if nation and nation not in seen:
            seen.append(nation)
    return seen


def filter_presets_by_nation(
    presets: list[dict[str, Any]], nation: str
) -> list[dict[str, Any]]:
    """按国别过滤预设；国别为空时返回全部。"""
    key = (nation or '').strip()
    if not key:
        return list(presets)
    return [x for x in presets if (x.get('nation') or '').strip() == key]


def nations_union(*preset_lists: list[dict[str, Any]]) -> list[str]:
    """合并多组预设的国别，按各组内首次出现顺序去重（驱护+防空共用国别列表）。"""
    seen: list[str] = []
    for presets in preset_lists:
        for nation in nations_sorted(presets):
            if nation not in seen:
                seen.append(nation)
    return seen


def build_missile_interception_presets_payload(
    missile_path: str | Path | None = None,
    radar_path: str | Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """构建前端/小程序/iOS 共用的饱和打击预设目录（源自双 CSV）。"""
    data = load_presets(missile_path, radar_path)
    return {
        'asm': list(data['asm']),
        'aew': list(data['aew']),
        'ship': list(data['ship']),
        'sam': list(data['sam']),
    }


# 兼容旧导入名：模块加载时从 CSV 填充（CLI/测试）
_loaded = load_presets()
ASM_PRESETS: list[dict[str, Any]] = list(_loaded['asm'])
AEW_PRESETS: list[dict[str, Any]] = list(_loaded['aew'])
SHIP_PRESETS: list[dict[str, Any]] = list(_loaded['ship'])
SAM_PRESETS: list[dict[str, Any]] = list(_loaded['sam'])
