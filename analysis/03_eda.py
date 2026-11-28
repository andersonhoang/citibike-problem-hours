"""
analysis/03_eda.py
Task: "EDA: 4 figures from code" (Joanna; reviewer Marcuz).

Four figures from the station-hour table, TRAINING WEEKS ONLY (1 Sep - 5 Oct 2025, src/config.py),
so nothing is learned from the validation or test weeks. Problem hour = |net_flow| >= the threshold
in results/threshold.json (run analysis/02_threshold.py first).

  figures/eda1_net_flow_distribution.png  how rare the extreme hours are
  figures/eda2_problem_share_by_hour.png  when: share of problem hours by hour, weekday vs weekend/holiday
  figures/eda3_demand_groups.png          where: problem-hour share for low / medium / high demand stations
  figures/eda4_data_quality.png           data quality: zero-trip station-hours per day, holiday marked

Also writes results/eda_summary.json with the numbers behind the figures.
Run from the repository root:  python analysis/03_eda.py
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")                       # draw to files, no window
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import DATA, HOLIDAYS, TRAIN  # noqa: E402

FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

# Colours: reference palette (blue, orange = categorical slots 1 and 2; blue ramp for ordered groups).
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"
BLUE_STEPS = ["#86b6ef", "#2a78d6", "#184f95"]       # low, medium, high demand (light -> dark)

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 13, "axes.titlesize": 16, "axes.labelsize": 13, "legend.fontsize": 12,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def load_training() -> tuple[pd.DataFrame, float]:
    """Training rows of the station-hour table, with the problem-hour flag from the fixed threshold."""
    thr = json.loads((RESULTS / "threshold.json").read_text())["q0.95"]["threshold"]
    sh = pd.read_csv(DATA / "station_hour.csv", dtype={"station_id": str}, parse_dates=["date"])
    d = sh["date"].dt.date
    train = sh[(d >= TRAIN[0]) & (d <= TRAIN[1])].copy()
    assert train["date"].dt.date.min() == TRAIN[0] and train["date"].dt.date.max() == TRAIN[1]
    train["problem"] = (train["net_flow"].abs() >= thr).astype(int)
    train["weekday"] = train["date"].dt.day_of_week               # 0 = Monday
    train["holiday"] = train["date"].dt.date.isin(HOLIDAYS)
    train["day_type"] = np.where((train["weekday"] >= 5) | train["holiday"], "Weekend or holiday", "Weekday")
    return train, thr


def fig1_distribution(train, thr, path):
    """Histogram of net flow (1-bike bins), log count axis, threshold lines at +/- thr."""
    nf = train["net_flow"]
    bins = np.arange(nf.min() - 0.5, nf.max() + 1.5)
    share = (nf.abs() >= thr).mean() * 100
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.hist(nf, bins=bins, color=BLUE, edgecolor=SURFACE, linewidth=0.3)
    ax.set_yscale("log")
    for x in (-thr, thr):
        ax.axvline(x, color=INK2, linestyle="--", linewidth=1.5)
    ax.text(thr + 1, ax.get_ylim()[1] * 0.4, f"+{thr:g}", color=INK2, fontsize=12)
    ax.text(-thr - 1, ax.get_ylim()[1] * 0.4, f"−{thr:g}", color=INK2, fontsize=12, ha="right")
    ax.set_title(f"Net flow per station-hour, training weeks\n"
                 f"Problem hours (|net flow| ≥ {thr:g}, dashed lines) = {share:.2f}% of station-hours",
                 loc="left")
    ax.set_xlabel("Net flow (arrivals − departures), bikes per hour")
    ax.set_ylabel("Station-hours (log scale)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig2_by_hour(train, thr, path):
    """Problem-hour share (%) by hour of day, weekday vs weekend/holiday."""
    share = train.groupby(["day_type", "hour"])["problem"].mean().unstack(0) * 100
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for col, colour, marker in [("Weekday", BLUE, "o"), ("Weekend or holiday", ORANGE, "s")]:
        ax.plot(share.index, share[col], color=colour, linewidth=2, marker=marker, markersize=6, label=col)
        peak = share[col].idxmax()
        # Label the peak; place it to the left when the peak is late in the day so it stays inside the plot.
        dx, ha = (-10, "right") if peak > 15 else (10, "left")
        ax.annotate(f"peak {share[col].max():.1f}% at {peak:02d}:00", (peak, share[col].max()),
                    xytext=(dx, 8), textcoords="offset points", ha=ha, color=INK, fontsize=11)
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)], rotation=45)
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(0, None)
    ax.set_title(f"Share of station-hours that are problem hours (|net flow| ≥ {thr:g}), "
                 "by hour of day\nTraining weeks; Labor Day counted with weekends", loc="left")
    ax.set_xlabel("Hour of day (New York time, start of hour)")
    ax.set_ylabel("Problem hours (% of station-hours)")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return share


def fig3_demand_groups(train, thr, path):
    """Stations sorted by training trips (departures + arrivals), cut into thirds; problem share per group."""
    trips = (train["departures"] + train["arrivals"]).groupby(train["station_id"]).sum().sort_values()
    labels = ["Low demand", "Medium demand", "High demand"]
    group = pd.qcut(trips.rank(method="first"), 3, labels=labels)
    t = train.assign(group=train["station_id"].map(group))
    stats = t.groupby("group", observed=True).agg(problem_share=("problem", "mean"),
                                                  station_hours=("problem", "size"))
    stats["stations"] = group.value_counts().reindex(labels)
    stats["trips_min"] = trips.groupby(group, observed=True).min()
    stats["trips_max"] = trips.groupby(group, observed=True).max()
    stats["problem_share"] *= 100
    fig, ax = plt.subplots(figsize=(10, 5.6))
    xt = [f"{g}\n{int(stats.loc[g, 'stations'])} stations\n"
          f"{int(stats.loc[g, 'trips_min']):,}–{int(stats.loc[g, 'trips_max']):,} trips" for g in labels]
    bars = ax.bar(xt, stats["problem_share"], color=BLUE_STEPS, width=0.6, edgecolor=SURFACE, linewidth=2)
    for b, v in zip(bars, stats["problem_share"]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}%", ha="center", va="bottom",
                fontsize=13, color=INK, fontweight="bold")
    ax.set_title(f"Problem-hour share by station demand group (|net flow| ≥ {thr:g})\n"
                 "Groups = thirds of the 300 stations by training trips (departures + arrivals)", loc="left")
    ax.set_xlabel("Station demand group (trips per station over the 35 training days)")
    ax.set_ylabel("Problem hours (% of station-hours)")
    ax.set_ylim(0, stats["problem_share"].max() * 1.2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return stats


def fig4_data_quality(train, path):
    """Station-hours with zero trips (no departure and no arrival) per training day; holidays marked."""
    zero = (train["departures"] + train["arrivals"] == 0).groupby(train["date"]).sum()
    total = train.groupby("date").size()
    assert total.nunique() == 1, "every training day should have the same number of station-hours"
    weekend = zero.index.day_of_week >= 5
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.bar(zero.index, zero.values, color=np.where(weekend, ORANGE, BLUE), width=0.8,
           edgecolor=SURFACE, linewidth=1)
    for day, name in HOLIDAYS.items():
        ts = pd.Timestamp(day)
        if ts in zero.index:
            ax.annotate(name, (ts, zero[ts]), xytext=(0, 18), textcoords="offset points", ha="center",
                        fontsize=12, color=INK, arrowprops=dict(arrowstyle="-", color=INK2))
    ax.legend(handles=[Patch(color=BLUE, label="Weekday"), Patch(color=ORANGE, label="Saturday or Sunday")],
              loc="upper right", frameon=False)
    ax.set_title(f"Station-hours with zero trips per day, training weeks (out of {int(total.iloc[0]):,} per day)\n"
                 "Columbus Day (13 Oct) falls in the test weeks, so it is not shown", loc="left")
    ax.set_xlabel("Date (2025)")
    ax.set_ylabel("Zero-trip station-hours (count per day)")
    ax.set_ylim(0, zero.max() * 1.18)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(matplotlib.dates.WeekdayLocator(byweekday=0))   # Mondays
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return zero, total


def main():
    train, thr = load_training()
    FIGURES.mkdir(exist_ok=True)
    fig1_distribution(train, thr, FIGURES / "eda1_net_flow_distribution.png")
    share = fig2_by_hour(train, thr, FIGURES / "eda2_problem_share_by_hour.png")
    stats = fig3_demand_groups(train, thr, FIGURES / "eda3_demand_groups.png")
    zero, total = fig4_data_quality(train, FIGURES / "eda4_data_quality.png")

    summary = {
        "computed_on": f"training weeks only: {TRAIN[0]} to {TRAIN[1]}",
        "threshold": thr,
        "training_station_hours": int(len(train)),
        "fig1_problem_share_pct": round(float(train["problem"].mean() * 100), 3),
        "fig1_net_flow_min_max": [int(train["net_flow"].min()), int(train["net_flow"].max())],
        "fig2_peak_share_pct": {c: {"hour": int(share[c].idxmax()), "share": round(float(share[c].max()), 2)}
                                for c in share.columns},
        "fig2_overnight_share_pct_0_to_5h": {c: round(float(share[c].loc[0:5].mean()), 2) for c in share.columns},
        "fig3_groups": {g: {"stations": int(r.stations), "trips_range": [int(r.trips_min), int(r.trips_max)],
                            "problem_share_pct": round(float(r.problem_share), 2)} for g, r in stats.iterrows()},
        "fig4_zero_trip_station_hours_per_day": {"of_total_per_day": int(total.iloc[0]),
                                                 "min": int(zero.min()), "max": int(zero.max()),
                                                 "mean": round(float(zero.mean()), 1),
                                                 "max_day": str(zero.idxmax().date()),
                                                 "labor_day": int(zero.get(pd.Timestamp("2025-09-01"), -1))},
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "eda_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print("Saved 4 figures to figures/ and results/eda_summary.json")


if __name__ == "__main__":
    main()
