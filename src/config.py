"""
src/config.py
One place for every fixed setting of the project, so no script hard-codes its own copy.
Values come from the Notion page "Project context (plain text)" and the Decision log.
"""
from datetime import date
from pathlib import Path

# Folders (all relative to the repository root, so the project runs on any laptop).
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_processed"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
STATION_HOUR_CSV = DATA / "station_hour.csv"
WEATHER_CSV = DATA / "weather_hourly.csv"
FEATURES_PARQUET = DATA / "features.parquet"
THRESHOLD_JSON = RESULTS / "threshold.json"

# Time-ordered split (Section 6 of the project context). Dates are inclusive.
TRAIN = (date(2025, 9, 1), date(2025, 10, 5))     # weeks 1-5
VALID = (date(2025, 10, 6), date(2025, 10, 12))   # week 6
TEST = (date(2025, 10, 13), date(2025, 10, 26))   # weeks 7-8, scored ONCE after the freeze

# Inner tuning split INSIDE the training weeks (so tuning never sees week 6 or the test weeks).
TUNE_FIT = (date(2025, 9, 1), date(2025, 9, 28))  # weeks 1-4
TUNE_EVAL = (date(2025, 9, 29), date(2025, 10, 5))  # week 5

HOLIDAYS = {date(2025, 9, 1): "Labor Day", date(2025, 10, 13): "Columbus Day"}

# Lead-time rule (PROPOSED in the project context; confirm with the team):
# to predict hour H we use only data up to the END of hour H-3, i.e. the newest lag is 3 hours.
MIN_LAG = 3

# Primary outcome: top 5% of |net flow| in training station-hours.
PROBLEM_QUANTILE = 0.95
SENSITIVITY_QUANTILES = (0.97, 0.90)  # 3% and 10% problem-hour rates

# Alert budget (PROPOSED example in the project context; confirm with the team):
# planners can act on the top 20 station-hours in each hour.
ALERT_BUDGET = 20

# Plan freeze: test weeks may be scored only on or after this date.
FREEZE_DATE = date(2026, 11, 25)

RANDOM_STATE = 42
