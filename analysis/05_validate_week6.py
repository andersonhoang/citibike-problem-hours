"""
analysis/05_validate_week6.py
Tasks: "Score both baselines on week 6", "Lasso logistic regression with time-ordered tuning",
       "Random forest first run (default settings)", and the input for
       "CHECKPOINT (Sun 22 Nov): do the models beat the baselines on validation? Go or fallback".
Fit on training weeks 1-5 -> score validation week 6. The test weeks are NOT touched.
Also runs the 3% / 10% threshold sensitivity on week 6 (dry run of the sensitivity code).
Run:  python analysis/05_validate_week6.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import FEATURES_PARQUET, RESULTS, TRAIN, VALID
from src.pipeline import run_all, between


def main():
    # Never load test-week rows at all during validation (enforced at parquet read time).
    df = pd.read_parquet(FEATURES_PARQUET, filters=[("split", "!=", "test")])
    assert "test" not in set(df["split"]), "STOP: test rows must never be loaded during validation"
    d = df.hour_start.dt.date
    fit_mask = (d >= TRAIN[0]) & (d <= TRAIN[1])
    val_mask = (d >= VALID[0]) & (d <= VALID[1])

    print("Fitting on weeks 1-5, scoring week 6 ...")
    table, preds, info = run_all(df, fit_mask, val_mask)
    table.to_csv(RESULTS / "validation_week6_metrics.csv", index=False)
    preds.to_parquet(RESULTS / "validation_week6_predictions.parquet", index=False)
    (RESULTS / "validation_week6_info.json").write_text(json.dumps(info, indent=2, default=str))
    print(table.round(4).to_string(index=False))

    # Checkpoint rule: GO if the best model beats the best baseline on week-6 PR-AUC.
    best_base = table[table.method.str.startswith("b")].pr_auc.max()
    best_model = table[~table.method.str.startswith("b")].pr_auc.max()
    decision = "GO" if best_model > best_base else "FALLBACK (net-flow MAE)"
    chk = {"best_baseline_pr_auc": best_base, "best_model_pr_auc": best_model, "decision": decision,
           "lasso_C": {k: v["best_C"] for k, v in info["lasso"].items()}}
    (RESULTS / "checkpoint_decision.json").write_text(json.dumps(chk, indent=2))
    print("CHECKPOINT:", json.dumps(chk))

    # Sensitivity dry run on week 6: 3% and 10% problem-hour definitions (lasso + baselines + RF).
    sens = []
    for y_col, key, label in [("y_3pct", "q0.97", "3%"), ("y_10pct", "q0.90", "10%")]:
        print(f"Sensitivity {label} ...")
        t, _, _ = run_all(df, fit_mask, val_mask, y_col=y_col, thr_key=key, lasso_C=chk["lasso_C"])
        sens.append(t.assign(threshold=label))
    sens.append(table.assign(threshold="5%"))
    pd.concat(sens).to_csv(RESULTS / "validation_week6_sensitivity.csv", index=False)
    print(pd.concat(sens).pivot(index="method", columns="threshold", values="pr_auc").round(4).to_string())


if __name__ == "__main__":
    main()
