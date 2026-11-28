"""
analysis/07_baselines.py
Task: "Score both baselines on week 6" (Joanna; reviewer Marcuz).

Two simple rules any planner could use today. A model is only useful if it beats them.
  Baseline 1, last week:       risk = problem-hour flag of the same station, same hour, 7 days (168 h) earlier (0 or 1).
  Baseline 2, historical rate: probability = share of problem hours for that station, hour of day and day type
                               (weekday / weekend-or-holiday) in the TRAINING weeks; fallback = the station's
                               overall training rate.
Both are scored on VALIDATION week 6 (6-12 Oct 2025) with Marcuz's functions in src/metrics.py:
PR-AUC, precision and recall at the alert budget, Brier score.
Rows are written to the shared table data_processed/validation_scores.csv (re-running replaces these two rows).

Run from the repository root (after analysis/02_threshold.py):  python analysis/07_baselines.py
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import DATA, HOLIDAYS, TRAIN, VALID  # noqa: E402
from src.metrics import brier, pr_auc, precision_at_budget, recall_at_budget  # noqa: E402

SCORES_CSV = DATA / "validation_scores.csv"
THRESHOLD_JSON = ROOT / "results" / "threshold.json"

# Alert budget: planners act on the top K station-hours in each clock hour.
# PROPOSED value from the project context (top 20 per hour); to be confirmed at the plan freeze.
ALERT_BUDGET_PER_HOUR = 20
TIE_SEED = 42510   # rows are shuffled once with this seed so tied scores are not ordered by station ID


def load_table() -> tuple[pd.DataFrame, float]:
    """Station-hour table with a timestamp, day type and the fixed problem-hour flag."""
    thr = json.loads(THRESHOLD_JSON.read_text())["q0.95"]["threshold"]
    sh = pd.read_csv(DATA / "station_hour.csv", dtype={"station_id": str}, parse_dates=["date"])
    sh["hour_start"] = sh["date"] + pd.to_timedelta(sh["hour"], unit="h")
    sh["day"] = sh["date"].dt.date
    sh["day_type"] = np.where((sh["date"].dt.day_of_week >= 5) | sh["day"].isin(HOLIDAYS),
                              "weekend_or_holiday", "weekday")
    sh["y_true"] = (sh["net_flow"].abs() >= thr).astype(int)
    return sh, thr


def baseline_last_week(sh: pd.DataFrame, rows: pd.DataFrame) -> pd.Series:
    """Problem flag of the same station 168 hours earlier (known long before the 2-hour cut-off)."""
    past = sh[["station_id", "hour_start", "y_true"]].copy()
    past["hour_start"] = past["hour_start"] + pd.Timedelta(hours=168)
    merged = rows[["station_id", "hour_start"]].merge(past, on=["station_id", "hour_start"], how="left")
    assert merged["y_true"].notna().all(), "every validation hour needs its value from 7 days earlier"
    return merged["y_true"].astype(float).set_axis(rows.index)


def fit_historical_rate(train: pd.DataFrame):
    """Training-week problem shares by station x hour x day type, and by station (fallback)."""
    assert train["day"].min() == TRAIN[0] and train["day"].max() == TRAIN[1], "rates must use training weeks only"
    cell = train.groupby(["station_id", "hour", "day_type"])["y_true"].mean().rename("rate_cell")
    station = train.groupby("station_id")["y_true"].mean().rename("rate_station")
    return cell, station


def baseline_historical_rate(model, rows: pd.DataFrame) -> tuple[pd.Series, int]:
    cell, station = model
    out = rows[["station_id", "hour", "day_type"]].join(cell, on=["station_id", "hour", "day_type"])
    out = out.join(station, on="station_id")
    n_fallback = int(out["rate_cell"].isna().sum())
    prob = out["rate_cell"].fillna(out["rate_station"])
    assert prob.notna().all(), "every validation station must have training rows"
    return prob.astype(float), n_fallback


def score(name: str, rows: pd.DataFrame, prob: pd.Series, thr: float, note: str) -> dict:
    """All fixed metrics via src/metrics.py. Budget is per clock hour, so group by the timestamp, not hour of day."""
    df = rows.assign(y_prob=prob.values)
    df = df.sample(frac=1.0, random_state=TIE_SEED)          # neutral, repeatable order for tied scores
    k = ALERT_BUDGET_PER_HOUR
    return {
        "model": name,
        "split": "validation (week 6)",
        "threshold_abs_net_flow": thr,
        "pr_auc": round(pr_auc(df["y_true"], df["y_prob"]), 6),
        "precision_at_budget": round(precision_at_budget(df, k, hour_col="hour_start"), 6),
        "recall_at_budget": round(recall_at_budget(df, k, hour_col="hour_start"), 6),
        "brier": round(brier(df["y_true"], df["y_prob"]), 6),
        "alert_budget_per_hour": k,
        "n_rows": int(len(df)),
        "n_problem_hours": int(df["y_true"].sum()),
        "problem_rate": round(float(df["y_true"].mean()), 6),
        "random_guess_pr_auc": round(float(df["y_true"].mean()), 6),
        "note": note,
        "script": "analysis/07_baselines.py",
        "run_date": date.today().isoformat(),
    }


def write_scores(new_rows: list[dict]) -> pd.DataFrame:
    """Add these rows to the shared validation table, replacing earlier rows from this script."""
    new = pd.DataFrame(new_rows)
    if SCORES_CSV.exists():
        old = pd.read_csv(SCORES_CSV)
        old = old[old["script"] != "analysis/07_baselines.py"]
        new = pd.concat([old, new], ignore_index=True)
    new.to_csv(SCORES_CSV, index=False, lineterminator="\n")
    return new


def main():
    sh, thr = load_table()
    train = sh[(sh["day"] >= TRAIN[0]) & (sh["day"] <= TRAIN[1])]
    valid = sh[(sh["day"] >= VALID[0]) & (sh["day"] <= VALID[1])].copy()
    assert valid["day"].nunique() == 7 and len(valid) == 300 * 24 * 7, "week 6 must be complete"

    b1 = baseline_last_week(sh, valid)
    rate_model = fit_historical_rate(train)
    b2, n_fallback = baseline_historical_rate(rate_model, valid)

    rows = [
        score("Baseline 1: same station-hour last week", valid, b1, thr,
              "risk is the 0/1 problem flag 168 h earlier"),
        score("Baseline 2: historical rate (station x hour x day type)", valid, b2, thr,
              f"training-week rates; {n_fallback} validation rows used the station fallback"),
    ]
    table = write_scores(rows)
    show = ["model", "pr_auc", "precision_at_budget", "recall_at_budget", "brier", "n_problem_hours", "problem_rate"]
    print(pd.DataFrame(rows)[show].to_string(index=False))
    print(f"\nRandom guess PR-AUC = problem rate = {rows[0]['problem_rate']:.4f}. "
          f"Station fallback used for {n_fallback} rows.")
    print(f"Saved {SCORES_CSV.relative_to(ROOT).as_posix()} ({len(table)} rows)")


if __name__ == "__main__":
    # Known-answer test on a tiny made-up table before touching the real data.
    toy = pd.DataFrame({"station_id": ["A"] * 4 + ["B"] * 2, "hour": [8, 8, 9, 9, 8, 8],
                        "day_type": ["weekday"] * 6, "y_true": [1, 0, 1, 1, 0, 0],
                        "day": [TRAIN[0]] * 3 + [TRAIN[1]] * 3})
    cell, station = fit_historical_rate(toy)
    q = pd.DataFrame({"station_id": ["A", "A", "B", "A"], "hour": [8, 9, 8, 8],
                      "day_type": ["weekday", "weekday", "weekday", "weekend_or_holiday"]})
    p, nf = baseline_historical_rate((cell, station), q)
    assert list(p) == [0.5, 1.0, 0.0, 0.75] and nf == 1, (list(p), nf)   # last row falls back to A's rate 3/4
    main()
