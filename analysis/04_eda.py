"""
analysis/04_eda.py
Task: "EDA: 4 figures from code" (Joanna). TRAINING WEEKS ONLY.
  fig1_netflow_distribution.png   - distribution of net flow, with the 5% threshold
  fig2_problem_share_hour_weekday.png - problem-hour share by hour x weekday
  fig3_demand_groups.png          - problem-hour rate by station-demand group
  fig4_data_quality.png           - total trips per day and share of zero-trip station-hours
Run:  python analysis/04_eda.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import FEATURES_PARQUET, FIGURES, THRESHOLD_JSON


def main():
    FIGURES.mkdir(exist_ok=True)
    df = pd.read_parquet(FEATURES_PARQUET)
    tr = df[df.split == "train"].copy()
    thr = json.loads(THRESHOLD_JSON.read_text())["q0.95"]["threshold"]

    # Figure 1: net-flow distribution (clipped to +-40 for readability).
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(tr["net_flow"].clip(-40, 40), bins=81, color="#3b7dd8")
    for s in (-thr, thr):
        ax.axvline(s, color="crimson", ls="--")
    ax.set_yscale("log")
    ax.set(title=f"Net flow per station-hour (training weeks); problem if |net flow| >= {thr:g}",
           xlabel="Arrivals minus departures (bikes per hour, clipped at ±40)", ylabel="Station-hours (log scale)")
    fig.tight_layout(); fig.savefig(FIGURES / "fig1_netflow_distribution.png", dpi=150); plt.close(fig)

    # Figure 2: problem share heatmap, hour x weekday.
    pivot = tr.pivot_table(index="weekday", columns="hour", values="y", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(10, 3.6))
    im = ax.imshow(pivot.values * 100, aspect="auto", cmap="Reds")
    ax.set_yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    ax.set_xticks(range(24), range(24))
    ax.set(title="Share of station-hours that are problem hours (%), training weeks", xlabel="Hour of day")
    fig.colorbar(im, ax=ax, label="%")
    fig.tight_layout(); fig.savefig(FIGURES / "fig2_problem_share_hour_weekday.png", dpi=150); plt.close(fig)

    # Figure 3: demand groups.
    grp = tr.groupby("demand_group")["y"].mean().reindex(["low", "mid", "high"]) * 100
    fig, ax = plt.subplots(figsize=(5, 3.6))
    ax.bar(grp.index, grp.values, color=["#9ecae1", "#4292c6", "#08519c"])
    for i, v in enumerate(grp.values):
        ax.text(i, v + 0.1, f"{v:.1f}%", ha="center")
    ax.set(title="Problem-hour rate by station-demand group\n(terciles of training trip volume)",
           ylabel="% of station-hours", xlabel="Demand group (100 stations each)")
    fig.tight_layout(); fig.savefig(FIGURES / "fig3_demand_groups.png", dpi=150); plt.close(fig)

    # Figure 4: data quality: daily trips and share of zero-activity station-hours.
    daily = tr.groupby(tr.hour_start.dt.date).agg(trips=("departures", "sum"),
                                                   zero_share=("abs_net_flow", lambda s: np.nan))
    act = tr.departures + tr.arrivals
    daily["zero_share"] = (act == 0).groupby(tr.hour_start.dt.date).mean() * 100
    fig, ax1 = plt.subplots(figsize=(9, 3.6))
    ax1.bar(daily.index, daily["trips"], color="#bbbbbb", label="Departures from the 300 stations")
    ax1.set_ylabel("Departures per day")
    ax2 = ax1.twinx()
    ax2.plot(daily.index, daily["zero_share"], color="crimson", marker="o", ms=3, label="% station-hours with no trips")
    ax2.set_ylabel("% zero-trip station-hours", color="crimson")
    ax1.set_title("Data-quality view (training weeks): daily volume and empty station-hours")
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(FIGURES / "fig4_data_quality.png", dpi=150); plt.close(fig)

    # Numbers quoted in the report.
    summary = {
        "threshold": thr,
        "train_problem_rate": float(tr.y.mean()),
        "peak_cell": {"weekday": int(pivot.stack().idxmax()[0]), "hour": int(pivot.stack().idxmax()[1]),
                      "share": float(pivot.stack().max())},
        "group_rates": grp.round(3).to_dict(),
        "net_flow_sd": float(tr.net_flow.std()),
        "min_daily_departures": int(daily.trips.min()), "max_daily_departures": int(daily.trips.max()),
    }
    (Path(FIGURES).parent / "results" / "eda_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
