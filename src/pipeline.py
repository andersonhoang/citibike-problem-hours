"""
src/pipeline.py
Fits every method (2 baselines, lasso, random forest; models with and without weather)
on one block of weeks and scores another block. Used by BOTH the validation run (week 6)
and the single test run (weeks 7-8), so the two runs are exactly the same code.
"""
import json
import time

import pandas as pd

from src.config import ALERT_BUDGET, THRESHOLD_JSON, TUNE_FIT, TUNE_EVAL
from src.features import feature_lists
from src.metrics import all_metrics
from src import models as M


def between(df, period):
    d = df["hour_start"].dt.date
    return df[(d >= period[0]) & (d <= period[1])]


def run_all(df, fit_mask, score_mask, y_col="y", thr_key="q0.95", log=print, rf=True, lasso_C=None):
    """
    df          : full feature table
    fit_mask    : rows used to fit (must have full history)
    score_mask  : rows to score
    lasso_C     : dict {"no_weather": C, "weather": C}; if None, C is tuned on weeks 1-4 -> week 5.
    Returns (metrics table, predictions table, extra info dict).
    """
    thr = json.loads(THRESHOLD_JSON.read_text())[thr_key]["threshold"]
    base, with_wx = feature_lists(df)
    fit = df[fit_mask & df.has_history]
    sc = df[score_mask].copy()
    assert sc.has_history.all(), "scored rows must have full history"
    preds = sc[["station_id", "station_name", "hour_start", "hour", "weekday", "demand_group",
                "net_flow", "abs_net_flow", y_col]].rename(columns={y_col: "y"}).copy()
    info = {"threshold": thr, "fit_rows": int(len(fit)), "score_rows": int(len(sc)), "lasso": {}}

    # Baselines (need no fitting beyond rates from the fit rows).
    s, p = M.baseline_last_week(sc, thr)
    preds["b1_last_week_score"], preds["b1_last_week_prob"] = s, p
    rate = M.fit_baseline_rate(df[fit_mask], y_col)          # all fit-period rows, history not needed
    s, p = M.predict_baseline_rate(rate, sc)
    preds["b2_hist_rate_score"], preds["b2_hist_rate_prob"] = s, p

    for tag, feats in [("no_weather", base), ("weather", with_wx)]:
        # Lasso: tune C with a time-ordered split inside the training weeks only.
        t0 = time.time()
        if lasso_C is None:
            tf, te = between(df[df.has_history], TUNE_FIT), between(df[df.has_history], TUNE_EVAL)
            C, tab = M.tune_lasso(tf, te, feats, y_col=y_col)
            info["lasso"][tag] = {"best_C": C, "tuning": tab.to_dict("records")}
        else:
            C = lasso_C[tag]
            info["lasso"][tag] = {"best_C": C, "tuning": "fixed from validation run"}
        lm = M.make_lasso(feats, C).fit(fit[feats], fit[y_col])
        p = lm.predict_proba(sc[feats])[:, 1]
        preds[f"lasso_{tag}_score"] = preds[f"lasso_{tag}_prob"] = p
        info["lasso"][tag]["coefficients"] = M.lasso_coefficients(lm).head(15).to_dict("records")
        info["lasso"][tag]["nonzero"] = int((lm.named_steps["clf"].coef_ != 0).sum())
        log(f"  lasso {tag}: C={C}, {time.time() - t0:.0f}s")

        if rf:
            t0 = time.time()
            m = M.make_rf().fit(fit[feats], fit[y_col])
            p = m.predict_proba(sc[feats])[:, 1]
            preds[f"rf_{tag}_score"] = preds[f"rf_{tag}_prob"] = p
            imp = pd.Series(m.feature_importances_, index=feats).sort_values(ascending=False)
            info.setdefault("rf", {})[tag] = {"importance_top10": imp.head(10).round(4).to_dict()}
            log(f"  random forest {tag}: {time.time() - t0:.0f}s")

    methods = sorted({c.rsplit("_", 1)[0] for c in preds.columns if c.endswith("_score")})
    rows = []
    for mth in methods:
        r = all_metrics(preds, f"{mth}_score", f"{mth}_prob", k=ALERT_BUDGET)
        rows.append({"method": mth, **r})
    table = pd.DataFrame(rows).sort_values("pr_auc", ascending=False)
    return table, preds, info
