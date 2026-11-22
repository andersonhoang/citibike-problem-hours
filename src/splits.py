"""
src/splits.py
Task: "Fix split dates and holiday flags in one small file" (Joanna).
Labels every study date as train / valid / test, numbers the weeks and flags the two holidays,
all from src/config.py. Writes data_processed/split_dates.csv for anyone who wants to look at it.
Self-test and write the file (from the repository root):  python -m src.splits
"""
import csv
from datetime import date, timedelta

from src.config import HOLIDAYS, SPLIT_DATES_CSV, TEST, TRAIN, VALID


def split_of(d: date) -> str:
    """Return 'train', 'valid', 'test' or 'outside' for one calendar date."""
    for name, (first, last) in (("train", TRAIN), ("valid", VALID), ("test", TEST)):
        if first <= d <= last:
            return name
    return "outside"


def week_of(d: date) -> int:
    """Study week 1-8; week 1 starts on the first training day (Monday 1 Sep 2025)."""
    return (d - TRAIN[0]).days // 7 + 1


def split_table() -> list[dict]:
    """One row per study day: date, week, split, weekday and holiday name (blank if none)."""
    n_days = (TEST[1] - TRAIN[0]).days + 1
    days = [TRAIN[0] + timedelta(days=i) for i in range(n_days)]
    return [{"date": d.isoformat(), "week": week_of(d), "split": split_of(d),
             "weekday": d.strftime("%a"), "holiday": HOLIDAYS.get(d, "")} for d in days]


def self_test(rows: list[dict]) -> None:
    """Known answers from the Notion task's 'Done when'."""
    count = lambda s: sum(r["split"] == s for r in rows)
    assert len(rows) == 56 and rows[-1]["week"] == 8, "56 days in 8 weeks"
    assert (count("train"), count("valid"), count("test")) == (35, 7, 14), "35 / 7 / 14 days"
    assert count("outside") == 0, "no day outside the three splits"
    by_date = {r["date"]: r for r in rows}
    assert by_date["2025-09-01"]["split"] == "train" and by_date["2025-09-01"]["holiday"] == "Labor Day"
    assert by_date["2025-10-13"]["split"] == "test" and by_date["2025-10-13"]["holiday"] == "Columbus Day"
    assert sum(bool(r["holiday"]) for r in rows) == 2, "exactly two holidays"
    assert all(r["weekday"] == "Mon" for r in rows[::7]) and rows[-1]["weekday"] == "Sun", "weeks run Mon-Sun"
    # The three splits touch with no gap and no overlap.
    assert VALID[0] - TRAIN[1] == timedelta(days=1) and TEST[0] - VALID[1] == timedelta(days=1)


if __name__ == "__main__":
    table = split_table()
    self_test(table)
    SPLIT_DATES_CSV.parent.mkdir(exist_ok=True)
    with open(SPLIT_DATES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "week", "split", "weekday", "holiday"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(table)
    print("Self-test passed: 56 days, 35 train / 7 valid / 14 test, Mon-Sun weeks, 2 holidays flagged.")
    print(f"Saved {SPLIT_DATES_CSV.relative_to(SPLIT_DATES_CSV.parents[1]).as_posix()}")
