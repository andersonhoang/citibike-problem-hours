"""
analysis/07_bootstrap_errors_figures.py
Tasks: "Bootstrap confidence intervals; per-week and per-group results" (Marcuz),
       "Error analysis and failure cases" (Anderson),
       "Final figures and tables from code" (Joanna).

Works on a predictions file. Before the freeze it runs as a DRY RUN on validation week 6;
after the single test run it runs on the test predictions:
    python analysis/07_bootstrap_errors_figures.py valid     (dry run, allowed now)
    python analysis/07_bootstrap_errors_figures.py test      (only after 06_run_test_once.py)
Bootstrap resamples WHOLE DAYS (hours within a day are related), 2,000 repeats.
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
from src.config import RESULTS, FIGURES, ALERT_BUDGET, RANDOM_STATE
from src.metrics import all_metrics, pr_auc

LABELS = {"b1_last_week": "Baseline 1: same hour last week", "b2_hist_rate": "Baseline 2: historical rate",
          "lasso_no_weather": "Lasso (no weather)", "lasso_weather": "Lasso (+ weather)",
          "rf_no_weather": "Random forest (no weather)", "rf_weather": "Random forest (+ weather)"}


def bootstrap_days(preds, method, n_boot=2000, seed=RANDOM_STATE):
    """95% percentile CIs for all 4 fixed metrics by resampling whole days with replacement."""
    rng = np.random.default_rng(seed)
    preds = preds.assign(day=preds.hour_start.dt.date)
    by_day = {d: g for d, g in preds.groupby("day")}
    days = list(by_day)
    sc_col, pr_col = f"{method}_score", f"{method}_prob"
    keys = ["pr_auc", f"precision_at_{ALERT_BUDGET}", f"recall_at_{ALERT_BUDGET}", "brier"]
    vals = {k: [] for k in keys}
    for _ in range(n_boot):
        pick = rng.choice(len(days), len(days), replace=True)
        # Give each drawn day a distinct slot id so duplicate days do not merge hour_start groups in at_budget().
        sample = pd.concat([by_day[days[i]].assign(_bhour=slot * 24 + by_day[days[i]]["hour"]) for slot, i in enumerate(pick)], ignore_index=True)
        if sample.y.sum() > 0:
            r = all_metrics(sample, sc_col, pr_col, k=ALERT_BUDGET, time_col="_bhour")
            for k in keys:
                vals[k].append(r[k])
    out = {}
    for k in keys:
        out[f"{k}_ci_low"] = float(np.percentile(vals[k], 2.5))
        out[f"{k}_ci_high"] = float(np.percentile(vals[k], 97.5))
    return out


def bootstrap_diff(preds, m1, m2, n_boot=2000, seed=RANDOM_STATE):
    """95% CI for PR-AUC(m1) - PR-AUC(m2), same resampled days for both (paired)."""
    rng = np.random.default_rng(seed)
    preds = preds.assign(day=preds.hour_start.dt.date)
    by_day = {d: g for d, g in preds.groupby("day")}
    days = list(by_day)
    diffs = []
    for _ in range(n_boot):
        s = pd.concat([by_day[days[i]] for i in rng.choice(len(days), len(days), replace=True)])
        diffs.append(pr_auc(s.y, s[f"{m1}_score"]) - pr_auc(s.y, s[f"{m2}_score"]))
    return float(np.mean(diffs)), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def main(which):
    src = {"valid": RESULTS / "validation_week6_predictions.parquet", "test": RESULTS / "test_predictions.parquet"}[which]
    if not src.exists():
        sys.exit(f"STOP: {src.name} not found. (Test predictions exist only after the single test run.)")
    preds = pd.read_parquet(src)
    methods = [m for m in LABELS if f"{m}_score" in preds.columns]
    tag = which

    # 1) Overall metrics + bootstrap CIs.
    n_boot = 1000 if which == "valid" else 2000
    rows = []
    for m in methods:
        r = all_metrics(preds, f"{m}_score", f"{m}_prob", k=ALERT_BUDGET)
        cis = bootstrap_days(preds, m, n_boot=n_boot)
        rows.append({"method": m, "label": LABELS[m], **r, **cis})
    overall = pd.DataFrame(rows).sort_values("pr_auc", ascending=False)
    overall.to_csv(RESULTS / f"{tag}_metrics_with_ci.csv", index=False)

    # 2) Per week and per demand group.
    preds["week"] = ((preds.hour_start - pd.Timestamp("2025-09-01")).dt.days // 7 + 1)
    per = []
    for col in ["week", "demand_group"]:
        for key, g in preds.groupby(col):
            for m in methods:
                per.append({"by": col, "group": key, "method": m, "pr_auc": pr_auc(g.y, g[f"{m}_score"]),
                            "problem_rate": g.y.mean()})
    per = pd.DataFrame(per)
    per.to_csv(RESULTS / f"{tag}_metrics_by_week_group.csv", index=False)

    # 3) Weather comparison (paired bootstrap of the PR-AUC difference).
    wx = {}
    for fam in ["lasso", "rf"]:
        if f"{fam}_weather_score" in preds:
            wx[fam] = dict(zip(["mean_diff", "ci_low", "ci_high"],
                               bootstrap_diff(preds, f"{fam}_weather", f"{fam}_no_weather", n_boot=n_boot)))
    best = overall.iloc[0].method
    best_base = overall[overall.method.str.startswith("b")].iloc[0].method
    vs_base = dict(zip(["mean_diff", "ci_low", "ci_high"], bootstrap_diff(preds, best, best_base, n_boot=n_boot)))
    json.dump({"weather_minus_no_weather": wx, "best_model": best, "best_baseline": best_base,
               "best_minus_best_baseline": vs_base},
              open(RESULTS / f"{tag}_paired_differences.json", "w"), indent=2)

    # 4) Error analysis: where does the best model miss? (alerts = top-20 per hour)
    s = preds.sort_values(["hour_start", f"{best}_score"], ascending=[True, False], kind="mergesort")
    s["alert"] = s.groupby("hour_start").cumcount() < ALERT_BUDGET
    s["outcome"] = np.select([s.alert & (s.y == 1), s.alert & (s.y == 0), ~s.alert & (s.y == 1)],
                             ["hit", "false alarm", "missed"], "quiet")
    by_hour = s.groupby("hour").agg(problems=("y", "sum"), caught=("outcome", lambda o: (o == "hit").sum()))
    by_hour["recall"] = by_hour.caught / by_hour.problems.replace(0, np.nan)
    missed_st = (s[s.outcome == "missed"].groupby(["station_id", "station_name"]).size()
                 .sort_values(ascending=False).head(10).rename("missed_problem_hours").reset_index())
    missed_st.to_csv(RESULTS / f"{tag}_top_missed_stations.csv", index=False)
    by_hour.to_csv(RESULTS / f"{tag}_recall_by_hour.csv")
    # Biggest single misses (largest |net flow| not alerted).
    big = s[s.outcome == "missed"].nlargest(10, "abs_net_flow")[
        ["station_name", "hour_start", "net_flow", f"{best}_score"]]
    big.to_csv(RESULTS / f"{tag}_biggest_misses.csv", index=False)

    # ---------------- Figures
    FIGURES.mkdir(exist_ok=True)
    # Fig 5: PR-AUC with CIs.
    o = overall.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#999999" if m.startswith("b") else "#2b6cb0" for m in o.method]
    ax.barh(o.label, o.pr_auc, xerr=[o.pr_auc - o.pr_auc_ci_low, o.pr_auc_ci_high - o.pr_auc], color=colors, capsize=3)
    ax.axvline(preds.y.mean(), color="crimson", ls="--", label=f"Random guess ≈ {preds.y.mean():.3f}")
    ax.set(xlabel="PR-AUC (higher is better), 95% CI from resampling whole days",
           title=f"Who finds problem hours best? ({'validation week 6' if which == 'valid' else 'test weeks 7-8'})")
    ax.legend(loc="lower right"); fig.tight_layout()
    fig.savefig(FIGURES / f"fig5_{tag}_pr_auc.png", dpi=150); plt.close(fig)

    # Fig 6: precision at budget.
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(o.label, o[f"precision_at_{ALERT_BUDGET}"], color=colors)
    for i, v in enumerate(o[f"precision_at_{ALERT_BUDGET}"]):
        ax.text(v + 0.005, i, f"{v:.0%}", va="center")
    ax.set(xlabel=f"Share of the top-{ALERT_BUDGET} alerts per hour that were real problem hours",
           title="Precision at a fixed alert budget"); fig.tight_layout()
    fig.savefig(FIGURES / f"fig6_{tag}_precision_at_budget.png", dpi=150); plt.close(fig)

    # Fig 7: failure case: recall of the best model by hour of day.
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(by_hour.index, by_hour.problems, color="#dddddd", label="Real problem hours")
    ax.bar(by_hour.index, by_hour.caught, color="#2b6cb0", label=f"Caught in top-{ALERT_BUDGET} alerts")
    ax.set(xlabel="Hour of day", ylabel="Station-hours",
           title=f"Where {LABELS[best]} fails: problem hours caught vs missed by hour")
    ax.legend(); fig.tight_layout()
    fig.savefig(FIGURES / f"fig7_{tag}_failure_by_hour.png", dpi=150); plt.close(fig)

    print(overall.drop(columns=["label"]).round(4).to_string(index=False))
    print(json.dumps({"weather": wx, "best_vs_baseline": vs_base}, indent=2))
    print("Top missed stations:\n", missed_st.to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "valid")
