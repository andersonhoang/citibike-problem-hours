"""
src/config.py
Task: "Fix split dates and holiday flags in one small file" (Joanna).
The ONE place for the study dates. Every later script imports these instead of typing dates itself.
Values from the Decision log (row 17: time-ordered split) and the project proposal.
"""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_processed"
SPLIT_DATES_CSV = DATA / "split_dates.csv"

# Time-ordered split, 8 weeks Monday to Sunday. Both dates inclusive.
TRAIN = (date(2025, 9, 1), date(2025, 10, 5))     # weeks 1-5
VALID = (date(2025, 10, 6), date(2025, 10, 12))   # week 6
TEST = (date(2025, 10, 13), date(2025, 10, 26))   # weeks 7-8, scored ONCE after the plan freeze

# Lag history: the 7 days before the study period (both dates inclusive). It only fills the lags of the
# first study week (for example "same hour last week"); these days are never rows to predict.
HISTORY = (date(2025, 8, 25), date(2025, 8, 31))

# Public holidays in the study period: one in training, one in test.
HOLIDAYS = {date(2025, 9, 1): "Labor Day", date(2025, 10, 13): "Columbus Day"}
