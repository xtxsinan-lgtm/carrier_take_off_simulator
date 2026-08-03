"""项目根目录与数据文件路径。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'output'

AIRCRAFT_CSV = DATA_DIR / 'aircraft_database.csv'
CARRIERS_CSV = DATA_DIR / 'carriers_database.csv'
# 饱和打击：导弹库（反舰弹 / 防空弹）与雷达库（预警机 / 舰载雷达）分表
SATURATION_MISSILE_CSV = DATA_DIR / 'saturation_missile_database.csv'
SATURATION_RADAR_CSV = DATA_DIR / 'saturation_radar_database.csv'
BASELINE_JSON = DATA_DIR / 'baseline_before.json'
SURVEY_RESULTS_TXT = OUTPUT_DIR / 'carrier_takeoff_survey_results.txt'
