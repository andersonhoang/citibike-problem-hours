"""
analysis/02_threshold.py
Task: "Compute the 5% problem-hour threshold from training weeks" (Joanna). CRITICAL PATH.

Problem hour = a station-hour whose |net flow| (|arrivals - departures|) is at or above a threshold.
The threshold is the 95th percentile of |net flow| over TRAINING station-hours only
(1 Sep - 5 Oct 2025, from src/config.py), so no validation or test hour influences it.
Also computes the 97th and 90th percentiles (3% and 10% problem hours) for the sensitivity check.
Writes results/threshold.json, which every later script reads. Fix it BEFORE any model is scored.

Run from the repository root:  python analysis/02_threshold.py
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import DATA, TRAIN  # noqa: E402  (the split dates live in one place)

STATION_HOUR_CSV = DATA / "station_hour.csv"
RESULTS = ROOT / "results"
THRESHOLD_JSON = RESULTS / "threshold.json"

MAIN_QUANTILE = 0.95                     # top 5% = problem hours (decision log row 10)
SENSITIVITY_QUANTILES = (0.97, 0.90)     # top 3% and top 10%


def threshold_from(abs_flow: pd.Series, q: float) -> float:
    """The q-th quantile of |net flow| (numpy's default linear rule). Problem hour = |net flow| >= this."""
    return float(np.quantile(abs_flow, q))


def summary_for(abs_flow: pd.Series, q: float) -> dict:
    thr = threshold_from(abs_flow, q)
    return {
        "threshold": thr,
        "train_problem_hours": int((abs_flow >= thr).sum()),
        "train_problem_rate": round(float((abs_flow >= thr).mean()), 6),
        "train_hours_exactly_at_threshold": int((abs_flow == thr).sum()),
    }


def main():
    sh = pd.read_csv(STATION_HOUR_CSV, dtype={"station_id": str}, parse_dates=["date"])
    d = sh["date"].dt.date
    train = sh[(d >= TRAIN[0]) & (d <= TRAIN[1])]

    # Guards: training weeks only, complete grid.
    assert train["date"].dt.date.min() == TRAIN[0] and train["date"].dt.date.max() == TRAIN[1]
    n_days = (TRAIN[1] - TRAIN[0]).days + 1
    assert len(train) == train["station_id"].nunique() * 24 * n_days, "training grid is not complete"

    abs_flow = train["net_flow"].abs()
    out = {
        "rule": "problem hour = 1 if |net_flow| >= threshold",
        "computed_on": f"training weeks only: {TRAIN[0]} to {TRAIN[1]} (src/config.py)",
        "n_training_station_hours": int(len(train)),
        "n_stations": int(train["station_id"].nunique()),
        "abs_net_flow_mean": round(float(abs_flow.mean()), 4),
        "net_flow_sd": round(float(train["net_flow"].std()), 4),
        "computed_date": date.today().isoformat(),
    }
    for q in (MAIN_QUANTILE, *SENSITIVITY_QUANTILES):
        out[f"q{q:.2f}"] = summary_for(abs_flow, q)
    # Direction of the main problem hours (filling up vs emptying), for the report.
    thr = out[f"q{MAIN_QUANTILE:.2f}"]["threshold"]
    out["main_problem_hours_by_direction"] = {
        "filling (net_flow >= +threshold)": int((train["net_flow"] >= thr).sum()),
        "emptying (net_flow <= -threshold)": int((train["net_flow"] <= -thr).sum()),
    }

    RESULTS.mkdir(exist_ok=True)
    THRESHOLD_JSON.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    print(f"Saved {THRESHOLD_JSON.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    # Known answers before touching the real data.
    s = pd.Series(np.arange(1, 101))                          # values 1..100
    assert abs(threshold_from(s, 0.95) - 95.05) < 1e-9         # linear rule: 95 + 0.05 * (96 - 95)
    assert (s >= threshold_from(s, 0.95)).sum() == 5           # exactly 96..100 are "problems"
    ties = pd.Series([0] * 90 + [15] * 10)                     # whole numbers with ties
    assert threshold_from(ties, 0.95) == 15 and (ties >= 15).mean() == 0.10   # ties push the rate above 5%
    main()
