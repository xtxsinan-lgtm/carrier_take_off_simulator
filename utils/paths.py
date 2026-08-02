"""Project root and data file paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'output'

AIRCRAFT_CSV = DATA_DIR / 'aircraft_database.csv'
CARRIERS_CSV = DATA_DIR / 'carriers_database.csv'
SATURATION_EQUIPMENT_CSV = DATA_DIR / 'saturation_equipment_database.csv'
BASELINE_JSON = DATA_DIR / 'baseline_before.json'
SURVEY_RESULTS_TXT = OUTPUT_DIR / 'carrier_takeoff_survey_results.txt'
