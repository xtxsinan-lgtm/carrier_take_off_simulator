"""饱和打击仿真的公开资料预设（反舰弹 / 预警机 / 舰载雷达 / 防空弹）。

型号列表以 data/saturation_equipment_database.csv 为唯一数据源；
前端经 build_all → data.json 的 saturation_presets 自动同步。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.database_csv import load_saturation_equipment_csv
from utils.paths import SATURATION_EQUIPMENT_CSV


def load_presets(path: str | Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """从 CSV 加载四类预设；文件不存在时返回空分组（如 Pyodide 环境）。"""
    csv_path = Path(path) if path is not None else SATURATION_EQUIPMENT_CSV
    if not csv_path.is_file():
        return {'asm': [], 'aew': [], 'ship': [], 'sam': []}
    return load_saturation_equipment_csv(csv_path)


def get_preset_by_id(presets: list[dict[str, Any]], preset_id: str) -> dict[str, Any] | None:
    """按 id 查找预设；找不到返回 None。"""
    for item in presets:
        if item['id'] == preset_id:
            return item
    return None


def build_saturation_presets_payload(path: str | Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """构建前端/小程序/iOS 共用的饱和打击预设目录（源自 CSV）。"""
    data = load_presets(path)
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
