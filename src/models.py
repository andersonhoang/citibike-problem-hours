"""
src/models.py
Baselines, lasso logistic regression and random forest, with ONE shared interface:
    fit(train_df) -> model ;  predict(model, df) -> (score, probability)
Tasks: "Score both baselines on week 6" (Joanna), "Lasso logistic regression with time-ordered
tuning" (Marcuz), "Random forest first run (default settings)" (Marcuz).
"""
import warnings
import numpy as np
# scikit-learn 1.8 warns that `penalty="l1"` will be renamed; the model is unchanged, so hide the notice.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="Inconsistent values")
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import RANDOM_STATE
from src.metrics import pr_auc


# ---------------------------------------------------------------- Baseline 1
def baseline_last_week(df: pd.DataFrame, threshold: float):
    """Same station-hour last week. Score = |net flow| 168 hours earlier (for ranking);
    probability = 1 if that hour was a problem hour, else 0 (for the Brier score)."""
    score = df["absnet_lag168"].to_numpy(float)
    prob = (score >= threshold).astype(float)
    return score, prob


# ---------------------------------------------------------------- Baseline 2
def fit_baseline_rate(train: pd.DataFrame, y_col="y"):
    """Each station's problem-hour rate by hour and weekday, from training weeks only.
    Falls back to the station's overall training rate if a cell is missing."""
    cell = train.groupby(["station_id", "hour", "weekday"])[y_col].mean().rename("rate_cell")
    station = train.groupby("station_id")[y_col].mean().rename("rate_station")
    return cell, station


def predict_baseline_rate(model, df: pd.DataFrame):
    cell, station = model
    out = df[["station_id", "hour", "weekday"]].join(cell, on=["station_id", "hour", "weekday"])
    out = out.join(station, on="station_id")
    p = out["rate_cell"].fillna(out["rate_station"]).fillna(0).to_numpy(float)
    return p, p


# ---------------------------------------------------------------- Lasso
def make_lasso(features, C):
    """Standardise numeric features, one-hot encode hour and weekday, L1-penalised logistic regression."""
    cats = [c for c in ["hour", "weekday"] if c in features]
    nums = [c for c in features if c not in cats]
    pre = ColumnTransformer([
        ("num", StandardScaler(), nums),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cats),
    ])
    clf = LogisticRegression(penalty="l1", C=C, solver="liblinear", max_iter=2000)
    return Pipeline([("pre", pre), ("clf", clf)])


def tune_lasso(fit_df, eval_df, features, grid=(0.001, 0.003, 0.01, 0.03, 0.1, 1.0), y_col="y"):
    """Time-ordered tuning: fit on weeks 1-4, score PR-AUC on week 5. Returns best C and the table."""
    rows = []
    for C in grid:
        m = make_lasso(features, C).fit(fit_df[features], fit_df[y_col])
        p = m.predict_proba(eval_df[features])[:, 1]
        n_kept = int((m.named_steps["clf"].coef_ != 0).sum())
        rows.append({"C": C, "pr_auc_week5": pr_auc(eval_df[y_col], p), "nonzero_coefs": n_kept})
    tab = pd.DataFrame(rows)
    return float(tab.loc[tab.pr_auc_week5.idxmax(), "C"]), tab


def lasso_coefficients(model) -> pd.DataFrame:
    names = model.named_steps["pre"].get_feature_names_out()
    coefs = model.named_steps["clf"].coef_.ravel()
    return (pd.DataFrame({"feature": names, "coef": coefs})
            .assign(abs=lambda d: d.coef.abs()).sort_values("abs", ascending=False).drop(columns="abs"))


# ---------------------------------------------------------------- Random forest
def make_rf(**kw):
    """scikit-learn defaults (100 trees, full depth); only n_jobs and random_state are set."""
    return RandomForestClassifier(n_jobs=-1, random_state=RANDOM_STATE, **kw)


if __name__ == "__main__":
    # Known-answer tests on tiny made-up data.
    toy = pd.DataFrame({"station_id": ["A"] * 4 + ["B"] * 4, "hour": [8, 8, 9, 9] * 2,
                        "weekday": [0] * 8, "y": [1, 1, 0, 1, 0, 0, 0, 0], "absnet_lag168": [9, 1, 0, 5] * 2})
    m = fit_baseline_rate(toy)
    p, _ = predict_baseline_rate(m, pd.DataFrame({"station_id": ["A", "A", "B", "C"], "hour": [8, 9, 8, 8], "weekday": [0, 0, 0, 0]}))
    assert list(p) == [1.0, 0.5, 0.0, 0.0], p           # C is unseen -> 0
    s, pr = baseline_last_week(toy.head(4), threshold=5)
    assert list(pr) == [1, 0, 0, 1]
    # Lasso on a separable toy problem should rank positives first.
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"x": rng.normal(size=400), "noise": rng.normal(size=400), "hour": rng.integers(0, 24, 400), "weekday": 0})
    y = (X.x > 1).astype(int)
    lm = make_lasso(["x", "noise", "hour", "weekday"], C=1.0).fit(X, y)
    assert pr_auc(y, lm.predict_proba(X)[:, 1]) > 0.95
    print("Self-test passed: baseline 2 rates, baseline 1 flags, lasso ranks a toy signal (PR-AUC > 0.95).")
