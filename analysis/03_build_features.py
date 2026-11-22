"""
analysis/03_build_features.py
Builds the modelling table: lag features (H-3 rule) + calendar + latest observed weather + outcome.
Reads the fixed threshold from results/threshold.json (computed on training weeks only).
Run:  python analysis/03_build_features.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import STATION_HOUR_CSV, WEATHER_CSV, FEATURES_PARQUET, THRESHOLD_JSON
from src.features import build_features, feature_lists
from src.splits import split_of


def main():
    sh = pd.read_csv(STATION_HOUR_CSV, dtype={"station_id": str})
    sh["hour_start"] = pd.to_datetime(sh["date"]) + pd.to_timedelta(sh["hour"], unit="h")
    sh = sh.sort_values(["station_id", "hour_start"]).reset_index(drop=True)
    wx = pd.read_csv(WEATHER_CSV, parse_dates=["hour_start"])

    # Check: the table is a complete grid (needed for "shift k rows = k hours back").
    assert len(sh) == sh["station_id"].nunique() * 56 * 24

    df = build_features(sh, wx)
    thr = json.loads(THRESHOLD_JSON.read_text())
    for key, name in [("q0.95", "y"), ("q0.97", "y_3pct"), ("q0.90", "y_10pct")]:
        df[name] = (df["abs_net_flow"] >= thr[key]["threshold"]).astype(int)
    df["split"] = [split_of(d) for d in df["hour_start"].dt.date]

    base, with_wx = feature_lists(df)
    # Rows whose 7-day history is not available (first week, because August is not in the
    # aggregated table) are flagged; models are fitted only on rows with full history.
    df["has_history"] = df[with_wx].notna().all(axis=1)
    # Station-demand group (terciles of training trip volume) for per-group results.
    vol = df[df.split == "train"].groupby("station_id")[["departures", "arrivals"]].sum().sum(axis=1)
    groups = pd.qcut(vol.rank(method="first"), 3, labels=["low", "mid", "high"])
    df["demand_group"] = df["station_id"].map(groups).astype(str)

    df.to_parquet(FEATURES_PARQUET, index=False)
    print(f"Saved {FEATURES_PARQUET.name}: {len(df):,} rows, {len(with_wx)} features (+weather).")
    print(df[df.split != "test"].groupby("split").agg(rows=("y", "size"), problem_rate=("y", "mean"),
                                  with_history=("has_history", "mean")).round(4).to_string())


if __name__ == "__main__":
    main()
