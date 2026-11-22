"""
src/metrics.py
Task (Marcuz, W1): "Metric functions with toy tests (PR-AUC, precision and recall at budget, Brier)".

Fixed evaluation metrics from Section 8 of PROJECT_CONTEXT.md.
Accuracy is intentionally excluded because only ~5% of station-hours are problem hours.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def pr_auc(y_true, y_prob) -> float:
    """Return PR-AUC (average precision); a constant always-zero model scores the positive rate."""
    return float(average_precision_score(y_true, y_prob))


def brier(y_true, y_prob) -> float:
    """Return the Brier score (mean squared probability error; lower is better)."""
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_prob, dtype=float)
    return float(np.mean((p - y) ** 2))


def _top_k_alerts(
    df: pd.DataFrame,
    k: int,
    hour_col: str = "hour",
    prob_col: str = "y_prob",
) -> pd.DataFrame:
    """Return the top k rows by predicted risk within each hour (stable sort for deterministic ties)."""
    ranked = df.sort_values([hour_col, prob_col], ascending=[True, False], kind="mergesort")
    rank_in_hour = ranked.groupby(hour_col, sort=False).cumcount()
    return ranked[rank_in_hour < k]


def precision_at_budget(
    df: pd.DataFrame,
    k: int,
    hour_col: str = "hour",
    y_col: str = "y_true",
    prob_col: str = "y_prob",
) -> float:
    """Return the share of top-k alerts per hour that are real problem hours."""
    alerts = _top_k_alerts(df, k, hour_col=hour_col, prob_col=prob_col)
    if len(alerts) == 0:
        return float("nan")
    return float(alerts[y_col].sum() / len(alerts))


def recall_at_budget(
    df: pd.DataFrame,
    k: int,
    hour_col: str = "hour",
    y_col: str = "y_true",
    prob_col: str = "y_prob",
) -> float:
    """Return the share of all real problem hours caught inside the top-k alerts per hour."""
    total_pos = float(df[y_col].sum())
    if total_pos == 0:
        return float("nan")
    alerts = _top_k_alerts(df, k, hour_col=hour_col, prob_col=prob_col)
    return float(alerts[y_col].sum() / total_pos)
