"""
analysis/06_run_test_once.py
Task: "Run the untouched test weeks ONCE" (Marcuz). CRITICAL PATH.

SAFETY LOCKS (hard rule from the Notion plan):
  1. Refuses to run before the plan freeze date (Wed 25 Nov 2026).
  2. Refuses to run unless FREEZE.md exists in the repo root (the frozen plan, committed).
  3. Refuses to run a second time if results/test_predictions.parquet already exists.

Final models: lasso C values are taken from the validation run (no re-tuning). Models are refitted
on weeks 1-6 (train + validation) and score weeks 7-8. The 5% threshold stays the one fixed from
weeks 1-5. (Refit-on-weeks-1-6 is a PROPOSED freeze item: confirm in FREEZE.md.)
Run (on/after 26 Nov, once):  python analysis/06_run_test_once.py
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import FEATURES_PARQUET, RESULTS, ROOT, TRAIN, VALID, TEST, FREEZE_DATE
from src.pipeline import run_all

OUT = RESULTS / "test_predictions.parquet"


def main(today=None):
    today = today or date.today()
    if today <= FREEZE_DATE:
        sys.exit(f"STOP: test weeks may only be scored after the plan freeze ({FREEZE_DATE}). Today is {today}.")
    if not ((ROOT / "FREEZE.md").exists() or (ROOT / "analysis" / "ANALYSIS_PLAN.md").exists()):
        sys.exit("STOP: FREEZE.md (or analysis/ANALYSIS_PLAN.md) not found. Write, commit, and tag `plan-frozen` first.")
    if OUT.exists():
        sys.exit("STOP: the test weeks were already scored. No second run (no re-tuning).")

    df = pd.read_parquet(FEATURES_PARQUET)
    C = json.loads((RESULTS / "checkpoint_decision.json").read_text())["lasso_C"]
    d = df.hour_start.dt.date
    fit_mask = (d >= TRAIN[0]) & (d <= VALID[1])
    test_mask = (d >= TEST[0]) & (d <= TEST[1])

    tables, all_preds = [], None
    for y_col, key, label in [("y", "q0.95", "5%"), ("y_3pct", "q0.97", "3%"), ("y_10pct", "q0.90", "10%")]:
        t, p, info = run_all(df, fit_mask, test_mask, y_col=y_col, thr_key=key, lasso_C=C)
        tables.append(t.assign(threshold=label))
        if label == "5%":
            all_preds, main_info = p, info
    all_preds.to_parquet(OUT, index=False)
    pd.concat(tables).to_csv(RESULTS / "test_metrics_all_thresholds.csv", index=False)
    tables[0].to_csv(RESULTS / "test_metrics.csv", index=False)
    (RESULTS / "test_info.json").write_text(json.dumps(main_info, indent=2, default=str))
    (RESULTS / "TEST_RUN_STAMP.txt").write_text(f"Test weeks scored once on {today}.\n")
    print(tables[0].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
