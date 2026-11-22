"""
src/splits.py
Task: "Fix split dates and holiday flags in one small file" (Joanna).
Labels every date as train / valid / test and flags the two holidays.
Self-test:  python -m src.splits
"""
from datetime import date
import pandas as pd
from src.config import TRAIN, VALID, TEST, HOLIDAYS


def split_of(d: date) -> str:
    """Return 'train', 'valid', 'test' or 'outside' for one calendar date."""
    if TRAIN[0] <= d <= TRAIN[1]:
        return "train"
    if VALID[0] <= d <= VALID[1]:
        return "valid"
    if TEST[0] <= d <= TEST[1]:
        return "test"
    return "outside"


def split_table() -> pd.DataFrame:
    """One row per study day: date, week number (1-8), split, weekday and holiday flag."""
    days = pd.date_range(TRAIN[0], TEST[1], freq="D").date
    out = pd.DataFrame({"date": days})
    out["week"] = [(d - TRAIN[0]).days // 7 + 1 for d in days]          # Mon 1 Sep starts week 1
    out["split"] = [split_of(d) for d in days]
    out["weekday"] = [d.strftime("%a") for d in days]
    out["holiday"] = [HOLIDAYS.get(d, "") for d in days]
    return out


if __name__ == "__main__":
    t = split_table()
    # Known answers: 56 days, 8 weeks, 35/7/14 days per split, two holidays in the right splits.
    assert len(t) == 56 and t["week"].max() == 8
    assert (t["split"] == "train").sum() == 35
    assert (t["split"] == "valid").sum() == 7
    assert (t["split"] == "test").sum() == 14
    assert t.loc[t["date"] == date(2025, 9, 1), "split"].item() == "train"
    assert t.loc[t["date"] == date(2025, 10, 13), "split"].item() == "test"
    assert t.iloc[0]["weekday"] == "Mon" and t.iloc[-1]["weekday"] == "Sun"
    t.to_csv("data_processed/split_dates.csv", index=False)
    print("Self-test passed: 56 days, 35 train / 7 valid / 14 test, holidays flagged.")
    print("Saved data_processed/split_dates.csv")
