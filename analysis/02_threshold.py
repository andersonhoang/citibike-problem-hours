"""
analysis/02_threshold.py
Task: "Compute the 5% problem-hour threshold from training weeks" (Joanna). CRITICAL PATH.
Uses ONLY training rows (1 Sep - 5 Oct). Writes results/threshold.json, which every later script reads.
Also writes the 3% and 10% thresholds for the sensitivity check.
Run:  python analysis/02_threshold.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import STATION_HOUR_CSV, THRESHOLD_JSON, RESULTS, TRAIN, PROBLEM_QUANTILE, SENSITIVITY_QUANTILES


def threshold_from(abs_flow: pd.Series, q: float) -> float:
    """Problem hour = |net flow| >= this value. Computed once, then fixed."""
    return float(np.quantile(abs_flow, q))


def main():
    sh = pd.read_csv(STATION_HOUR_CSV, dtype={"station_id": str}, parse_dates=["date"])
    train = sh[(sh["date"].dt.date >= TRAIN[0]) & (sh["date"].dt.date <= TRAIN[1])]
    assert train["date"].dt.date.max() == TRAIN[1]          # no validation/test rows used
    abs_train = train["net_flow"].abs()

    out = {"rule": "problem hour = 1 if |net_flow| >= threshold", "computed_on": "training weeks 1-5 only",
           "n_training_rows": int(len(train))}
    for q in (PROBLEM_QUANTILE, *SENSITIVITY_QUANTILES):
        thr = threshold_from(abs_train, q)
        out[f"q{q:.2f}"] = {"threshold": thr, "train_problem_rate": float((abs_train >= thr).mean())}
    RESULTS.mkdir(exist_ok=True)
    THRESHOLD_JSON.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    # Known answer: values 1..100 -> 95th percentile = 95.05 and 5 values (96..100) are >= it.
    s = pd.Series(np.arange(1, 101))
    assert abs(threshold_from(s, 0.95) - 95.05) < 1e-9 and (s >= threshold_from(s, 0.95)).sum() == 5
    main()
