"""饱和打击仿真的公开资料预设（反舰弹 / 预警机 / 舰载雷达 / 防空弹）。

速度、尺寸、射程取自维基百科等公开资料；反舰导弹 RCS 为粗略量级估计，非实测值。
"""
from __future__ import annotations

from typing import Any

# 舰载防空导弹预设
SAM_PRESETS: list[dict[str, Any]] = [
    {'id': 'sm2', 'name': 'SM-2MR 标准-2 (美国)', 'vi': 3.5, 'dia': 0.343, 'guidance': 'semi_active', 'range': 167},
    {'id': 'sm6', 'name': 'SM-6 标准-6 (美国)', 'vi': 3.5, 'dia': 0.343, 'guidance': 'active_mech', 'range': 240},
    {'id': 'aster30', 'name': 'Aster 30 (法国/欧洲)', 'vi': 4.5, 'dia': 0.18, 'guidance': 'active_mech', 'range': 120},
    {'id': 'essm', 'name': 'ESSM Block2 (北约通用)', 'vi': 4.0, 'dia': 0.254, 'guidance': 'active_mech', 'range': 50},
    {'id': 'hhq9', 'name': '海红旗-9 HHQ-9 (中国)', 'vi': 4.2, 'dia': 0.56, 'guidance': 'active_mech', 'range': 200},
    {'id': 'barak8', 'name': '巴拉克-8 Barak 8 (以色列/印度)', 'vi': 2.0, 'dia': 0.225, 'guidance': 'active_mech', 'range': 100},
    {'id': 'seaceptor', 'name': '海上拦截者 Sea Ceptor/CAMM (英国)', 'vi': 3.0, 'dia': 0.166, 'guidance': 'active_aesa', 'range': 25},
    {'id': 's300f', 'name': '里夫/48N6 S-300F (俄罗斯)', 'vi': 6.0, 'dia': 0.52, 'guidance': 'semi_active', 'range': 150},
]

# 反舰导弹预设
ASM_PRESETS: list[dict[str, Any]] = [
    {'id': 'exocet', 'name': '飞鱼 Exocet MM40 Block3 (法国)', 'vm': 0.93, 'rcs': 0.15, 'traj': 'sea'},
    {'id': 'harpoon', 'name': '鱼叉 Harpoon (美国)', 'vm': 0.85, 'rcs': 0.3, 'traj': 'sea'},
    {'id': 'yj12', 'name': '鹰击-12 YJ-12 (中国)', 'vm': 3.5, 'rcs': 0.3, 'traj': 'high'},
    {'id': 'yj18', 'name': '鹰击-18 YJ-18 (中国, 末端超音速)', 'vm': 3.0, 'rcs': 0.2, 'traj': 'sea'},
    {'id': 'kalibr', 'name': '口径 3M-54 Kalibr (俄罗斯)', 'vm': 2.9, 'rcs': 0.2, 'traj': 'sea'},
    {'id': 'brahmos', 'name': '布拉莫斯 BrahMos (印度/俄罗斯)', 'vm': 3.0, 'rcs': 0.3, 'traj': 'sea'},
    {'id': 'nsm', 'name': '海军打击导弹 NSM (挪威, 隐身外形)', 'vm': 0.93, 'rcs': 0.05, 'traj': 'sea'},
]

# 预警机/预警直升机预设
AEW_PRESETS: list[dict[str, Any]] = [
    {'id': 'e2d', 'name': 'E-2D 先进鹰眼 (美国, 固定翼舰载)', 'area': 40, 'type': 'aesa', 'standoff': 150},
    {'id': 'e2c', 'name': 'E-2C 鹰眼 (美国, 固定翼舰载, 早期型)', 'area': 40, 'type': 'mechanical', 'standoff': 150},
    {'id': 'kj600', 'name': '空警-600 KJ-600 (中国, 固定翼舰载)', 'area': 40, 'type': 'aesa', 'standoff': 150},
    {'id': 'ka31', 'name': '卡-31 Ka-31 预警直升机 (俄/中/印)', 'area': 6, 'type': 'pesa', 'standoff': 100},
]

# 驱逐舰雷达预设
SHIP_PRESETS: list[dict[str, Any]] = [
    {'id': 'burke3', 'name': '阿利·伯克 Flight III (美国, SPY-6)', 'area': 13.5, 'type': 'gan_aesa'},
    {'id': 'burke2a', 'name': '阿利·伯克 Flight IIA (美国, SPY-1D)', 'area': 12, 'type': 'pesa'},
    {'id': 'type052d', 'name': '052D (中国, Type 346A)', 'area': 14, 'type': 'aesa'},
    {'id': 'type055', 'name': '055 (中国, Type 346B)', 'area': 21, 'type': 'aesa'},
    {'id': 'type45', 'name': '45型 Type 45 (英国, SAMPSON)', 'area': 6, 'type': 'aesa'},
]


def get_preset_by_id(presets: list[dict[str, Any]], preset_id: str) -> dict[str, Any] | None:
    """按 id 查找预设；找不到返回 None。"""
    for item in presets:
        if item['id'] == preset_id:
            return item
    return None


def build_saturation_presets_payload() -> dict[str, list[dict[str, Any]]]:
    """构建前端/小程序/iOS 共用的饱和打击预设目录。"""
    return {
        'asm': list(ASM_PRESETS),
        'aew': list(AEW_PRESETS),
        'ship': list(SHIP_PRESETS),
        'sam': list(SAM_PRESETS),
    }
