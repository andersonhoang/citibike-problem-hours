"""
analysis/00_test_metrics.py
Task (Marcuz, W1): hand-verified 10-row toy tests for src/metrics.py.

Run from the repository root:
    python analysis/00_test_metrics.py

Every expected answer below is worked out by hand first so any team member can verify the code.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.metrics import brier, pr_auc, precision_at_budget, recall_at_budget


def main() -> None:
    """Verify all four metrics against hand-computed answers and an always-zero sanity check."""
    # 10-row toy table: 2 hours (hour 8 and hour 9) x 5 stations, 4 problem hours total (40% rate).
    # All 10 probabilities are distinct so the ranking order has no ties.
    toy = pd.DataFrame({
        "hour":   [8,   8,   8,   8,   8,   9,   9,   9,   9,   9],
        "y_true": [1,   0,   1,   0,   0,   1,   1,   0,   0,   0],
        "y_prob": [0.9, 0.7, 0.4, 0.2, 0.1, 0.8, 0.6, 0.5, 0.3, 0.0],
    })

    # 1. Precision & recall at budget k = 2 per hour (4 alerts total):
    #    Hour 8 top 2: 0.9 (hit), 0.7 (miss) -> 1 hit
    #    Hour 9 top 2: 0.8 (hit), 0.6 (hit)  -> 2 hits
    #    Precision@2 = 3 / 4 = 0.75 ; Recall@2 = 3 / 4 = 0.75
    p2 = precision_at_budget(toy, k=2)
    r2 = recall_at_budget(toy, k=2)
    assert abs(p2 - 0.75) < 1e-12, f"Expected precision@2 = 0.75, got {p2}"
    assert abs(r2 - 0.75) < 1e-12, f"Expected recall@2 = 0.75, got {r2}"

    # 2. Precision & recall at budget k = 1 per hour (2 alerts total):
    #    Hour 8 top 1: 0.9 (hit) ; Hour 9 top 1: 0.8 (hit)
    #    Precision@1 = 2 / 2 = 1.00 ; Recall@1 = 2 / 4 = 0.50
    p1 = precision_at_budget(toy, k=1)
    r1 = recall_at_budget(toy, k=1)
    assert abs(p1 - 1.00) < 1e-12, f"Expected precision@1 = 1.00, got {p1}"
    assert abs(r1 - 0.50) < 1e-12, f"Expected recall@1 = 0.50, got {r1}"

    # 3. PR-AUC (average precision) sorted descending across all 10 rows:
    #    Rank 1: 0.9 (y=1) -> P=1/1 ; Rank 2: 0.8 (y=1) -> P=2/2 ; Rank 3: 0.7 (y=0)
    #    Rank 4: 0.6 (y=1) -> P=3/4 ; Rank 5: 0.5 (y=0) ; Rank 6: 0.4 (y=1) -> P=4/6
    #    AP = (1/1 + 2/2 + 3/4 + 4/6) / 4 = 41 / 48
    expected_ap = (1 / 1 + 2 / 2 + 3 / 4 + 4 / 6) / 4
    got_ap = pr_auc(toy["y_true"], toy["y_prob"])
    assert abs(got_ap - expected_ap) < 1e-12, f"Expected PR-AUC = {expected_ap}, got {got_ap}"

    # 4. Brier score:
    #    Hour 8 squared errors: 0.01 + 0.49 + 0.36 + 0.04 + 0.01 = 0.91
    #    Hour 9 squared errors: 0.04 + 0.16 + 0.25 + 0.09 + 0.00 = 0.54
    #    Brier = (0.91 + 0.54) / 10 = 0.145
    got_brier = brier(toy["y_true"], toy["y_prob"])
    assert abs(got_brier - 0.145) < 1e-12, f"Expected Brier = 0.145, got {got_brier}"

    # 5. Sanity check: an always-zero model scores PR-AUC equal to the positive rate.
    zero_toy_ap = pr_auc(toy["y_true"], np.zeros(len(toy)))
    assert abs(zero_toy_ap - 0.40) < 1e-12, f"Expected always-zero PR-AUC = 0.40, got {zero_toy_ap}"

    rng = np.random.default_rng(42)
    y_5pct = (rng.random(10_000) < 0.05).astype(int)
    zero_5pct_ap = pr_auc(y_5pct, np.zeros_like(y_5pct))
    assert abs(zero_5pct_ap - y_5pct.mean()) < 1e-12, (zero_5pct_ap, y_5pct.mean())

    print("All metric tests PASSED:")
    print(f"  10-row toy PR-AUC        = {got_ap:.6f} (hand: 41/48 = {expected_ap:.6f})")
    print(f"  10-row toy Brier         = {got_brier:.6f} (hand: 0.145000)")
    print(f"  10-row toy P@2 / R@2     = {p2:.2f} / {r2:.2f} (hand: 0.75 / 0.75)")
    print(f"  10-row toy P@1 / R@1     = {p1:.2f} / {r1:.2f} (hand: 1.00 / 0.50)")
    print(f"  Always-zero PR-AUC (5%)  = {zero_5pct_ap:.4f} (positive rate: {y_5pct.mean():.4f})")


if __name__ == "__main__":
    main()
