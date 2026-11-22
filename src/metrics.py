"""
src/metrics.py
Task: "Metric functions with toy tests (PR-AUC, precision and recall at budget, Brier)" (Marcuz).
Self-test:  python -m src.metrics
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def pr_auc(y, score) -> float:
    """PR-AUC = average precision. A random score gets about the share of 1s in y."""
    return float(average_precision_score(y, score))


def brier(y, prob) -> float:
    """Average squared gap between predicted probability and what happened (lower is better)."""
    y, prob = np.asarray(y, float), np.asarray(prob, float)
    return float(np.mean((prob - y) ** 2))


def at_budget(df: pd.DataFrame, score_col: str, y_col: str = "y", time_col: str = "hour_start", k: int = 20):
    """
    Precision and recall at a fixed alert budget.
    In every hour, planners look at the k station-hours with the highest score.
    precision = real problem hours among all alerts / all alerts
    recall    = real problem hours caught / all real problem hours
    Ties are broken at random with a fixed seed (deterministic). Breaking them by row order would
    favour stations that sort first by ID, which matters for the baselines (many tied scores).
    """
    tie = np.random.default_rng(42).random(len(df))
    ranked = df.assign(_tie=tie).sort_values([time_col, score_col, "_tie"], ascending=[True, False, True],
                                             kind="mergesort")
    ranked = ranked.assign(_rank=ranked.groupby(time_col).cumcount())
    alerts = ranked[ranked["_rank"] < k]
    caught = alerts[y_col].sum()
    precision = caught / len(alerts) if len(alerts) else np.nan
    recall = caught / df[y_col].sum() if df[y_col].sum() else np.nan
    return float(precision), float(recall)


def all_metrics(df: pd.DataFrame, score_col: str, prob_col: str, k: int = 20, y_col: str = "y", time_col: str = "hour_start") -> dict:
    """Every fixed metric for one model in one table."""
    p, r = at_budget(df, score_col, y_col, time_col=time_col, k=k)
    return {
        "pr_auc": pr_auc(df[y_col], df[score_col]),
        f"precision_at_{k}": p,
        f"recall_at_{k}": r,
        "brier": brier(df[y_col], df[prob_col]),
        "problem_rate": float(df[y_col].mean()),
        "n_rows": int(len(df)),
    }


if __name__ == "__main__":
    # Toy table: 2 hours x 3 stations, with answers worked out by hand.
    toy = pd.DataFrame({
        "hour_start": [1, 1, 1, 2, 2, 2],
        "y":          [1, 0, 0, 0, 1, 1],
        "s":          [0.9, 0.2, 0.1, 0.8, 0.7, 0.1],
    })
    # Budget k=1: hour 1 picks the 0.9 row (a hit); hour 2 picks the 0.8 row (a miss).
    p, r = at_budget(toy, "s", k=1)
    assert p == 0.5 and abs(r - 1 / 3) < 1e-12, (p, r)
    # Brier by hand: perfect probabilities -> 0; always 0.5 -> 0.25.
    assert brier([1, 0], [1, 0]) == 0.0 and brier([1, 0], [0.5, 0.5]) == 0.25
    # PR-AUC by hand: scores ranked 0.9(1) 0.8(0) 0.7(1) 0.2(0) 0.1(0) 0.1(1)
    # AP = mean precision at each hit = (1/1 + 2/3 + 3/6)/3 ... with the 0.1 tie sklearn counts both 0.1 rows -> 3/6.
    assert abs(pr_auc(toy["y"], toy["s"]) - (1 + 2 / 3 + 3 / 6) / 3) < 1e-12
    # An always-no (constant) model: PR-AUC equals the problem-hour rate.
    rng = np.random.default_rng(0)
    y = (rng.random(10_000) < 0.05).astype(int)
    assert abs(pr_auc(y, np.zeros_like(y)) - y.mean()) < 1e-12
    print("Self-test passed: budget precision/recall, Brier and PR-AUC match hand answers;")
    print(f"constant model PR-AUC = problem rate ({y.mean():.4f}).")
