# Predicting Problem Hours at Busy Citi Bike Stations to Prioritise Rebalancing (NYC, Sep–Oct 2025)

**Course:** 42.510 Statistical Learning for Data Science, SUTD  
**Team:** Anderson Hoang (Data), Joanna Chen (Methods), Marcuz Duong (Results)  
**Target length:** Max 6 A4 pages (11–12 pt), excluding References and Appendix.

> **STATUS NOTE (22 Nov 2026):** Section 5 currently shows **Validation Week 6** results (`6–12 Oct 2025`). The untouched **Test Weeks 7–8** (`13–26 Oct 2025`) are locked until after the Wed 25 Nov plan freeze. After running `analysis/06_run_test_once.py` and `analysis/07_bootstrap_errors_figures.py test`, replace the `[VALIDATION]` numbers in Section 5 with the `results/test_*.csv` values.

---

## 1. Abstract

Bike-share operators face empty docks and full racks during sharp demand surges, leaving riders without a bike or a place to park. For **Citi Bike operations planners**, we test whether trip history, calendar features, and citywide weather available **2 hours ahead** can predict high-imbalance "problem hours" at the 300 busiest New York City stations from 1 Sep to 26 Oct 2025 (403,200 station-hours). Using a strict time-ordered split (Weeks 1–5 train, Week 6 validation, Weeks 7–8 untouched test) and a fixed training-set problem-hour threshold (`|net flow| >= 15` bikes/hour, top 5%), we compare two transparent operational baselines against Lasso logistic regression and Random Forest, each fitted without and with lagged weather. `[VALIDATION]` On Validation Week 6, Random Forest with weather achieves **PR-AUC 0.499** (95% day-bootstrap CI: 0.338–0.606) and Lasso reaches **0.474** (0.313–0.600), beating the best baseline (historical station-hour-weekday rate, **0.408**, CI: 0.262–0.515; paired gain **+0.088**, CI: +0.027 to +0.138). Adding lagged citywide weather changes PR-AUC by less than 0.01 (95% CIs cross zero). Results hold across 3% and 10% threshold sensitivity checks. Error analysis reveals a key operational limitation: a flat alert budget of 20 stations/hour wastes alerts overnight while capping recall at ~24% during 8 AM and 5 PM peaks. All claims are predictive only.

---

## 2. Problem and Relevance

**Primary question:** For Citi Bike operations planners, can trip history, calendar, and weather information available 2 hours before each hour help predict which station-hours will be high-imbalance problem hours at the 300 busiest New York City stations in September–October 2025?

**Audience and decision:** Operations planners deciding which stations to check and rebalance next with limited trucks. A ranked 2-hour-ahead risk list supports prioritisation. We assume 2 hours is sufficient lead time to dispatch a truck (a stated operational assumption, not an official Citi Bike figure).

**Scope:** Prediction and association only. We make no causal claims (e.g., we do not claim weather causes imbalance) and do not model truck routing.

---

## 3. Data Curation (Lead: Anderson Hoang)

**Sources and licence:**
- **Citi Bike trip histories:** Official NYC monthly zip archives (`202508`, `202509`, `202510`, excluding `JC-` Jersey City files), totalling **15,140,880 trips** across 17 CSVs (13 columns each). Licensed under the Citi Bike Data Sharing Policy (Lyft Bikes and Scooters, LLC). Raw files are never committed or redistributed; `get_data.py` reproduces the download locally. Only aggregated station-hour counts are stored in `data_processed/`.
- **Weather:** Open-Meteo Historical Weather API (CC BY 4.0, non-commercial), one citywide NYC hourly series (`lat=40.78, lon=-73.97`, timezone `America/New_York`, 25 Aug–26 Oct 2025: temperature, precipitation, wind speed; 1,512 hours, zero gaps). Query parameters and metadata are saved in `data_processed/weather_provenance.json`.

**Unit and cleaning rules (agreed 16 Nov 2026):**
- **Unit:** One station in one hour (`station-hour`). `net_flow = arrivals - departures`, where departures are counted by `started_at` at `start_station_id` and arrivals by `ended_at` at `end_station_id` (trips crossing midnight on 31 Aug are counted as 1 Sep arrivals).
- **ID and name hygiene:** `start_station_id` and `end_station_id` are read as text (`str`) so IDs like `5329.10` keep their trailing zero. Trailing `_` and `_old` suffixes are stripped; leading/trailing spaces on station names are trimmed; blank station IDs are dropped.
- **Station selection (no leakage):** Stations must be active on all 35 training days (1 Sep–5 Oct 2025); **341 stations** failing this rule are excluded and logged in `data_processed/excluded_stations.csv`. From the remaining stations, the **300 busiest** by training trip volume (starts + ends) are selected.
- **Resulting table:** `300 stations × 24 hours × 56 days = 403,200 rows` (`4,337,394` arrivals, `4,376,848` departures; SHA-256 verified). `member_casual` is excluded; no rider-level linking is attempted.

**Training-week EDA (`figures/fig1`–`fig4`):**
- Training `net_flow` has SD **7.23** bikes/hour; the top-5% problem-hour threshold is **`|net_flow| >= 15`** bikes/hour (training problem rate **5.15%** due to integer ties).
- Problem hours concentrate sharply in weekday commute peaks, reaching **33.5%** of stations on Tuesday at 08:00 (`fig2`).
- By training-volume tercile (`fig3`), problem-hour rates rise from **3.8%** (low) to **4.6%** (mid) to **7.0%** (high).
- Daily departures across the 300 stations range from **51,777** to **96,108** (`fig4`).

---

## 4. Methods and Validation (Lead: Joanna Chen)

**Time-ordered split and leakage controls:**
- **Training:** Weeks 1–5 (1 Sep–5 Oct 2025, 252,000 rows). Because 7-day lag features require 7 prior days and August is not in the aggregated table, Week 1 is excluded from model fitting (`201,600` fitted rows).
- **Validation:** Week 6 (6–12 Oct 2025, 50,400 rows).
- **Test (untouched):** Weeks 7–8 (13–26 Oct 2025, 100,800 rows), locked in code (`analysis/06_run_test_once.py`) until after the Wed 25 Nov plan freeze and scored **once**.
- **2-hour lead-time rule (`MIN_LAG = 3`):** To predict hour `H`, every count and weather feature uses data up to the end of hour `H-3` (recent lags `H-3, H-4, H-5`; 6-hour activity `H-3..H-8`; same-hour lags `24h, 48h, 168h` and 7-day same-hour means; calendar `hour`, `weekday`, `is_weekend`, `is_holiday`; weather at `H-3`). An automated leakage test (`src/features.py`) mutates all data from `H-2` onwards and asserts all 27 features at `H` remain identical.

**Models (fixed in advance):**
1. **Baseline 1 (`b1_last_week`):** Same station-hour 168 hours ago (`|net_flow|` as ranking score; problem flag as probability).
2. **Baseline 2 (`b2_hist_rate`):** Training-set problem-hour rate per `(station_id, hour, weekday)`.
3. **Lasso Logistic Regression:** Standardised numeric features + one-hot `hour`/`weekday` + L1 logistic regression (`liblinear`). Regularisation `C ∈ {0.001, 0.003, 0.01, 0.03, 0.1, 1.0}` is tuned strictly inside training (fit Weeks 1–4, score PR-AUC on Week 5).
4. **Random Forest:** `RandomForestClassifier` (100 trees, default depth, `random_state=42`) to capture nonlinear interactions.
Each model is fitted **without** and **with** lagged weather.

**Metrics and uncertainty:**
- **Primary:** PR-AUC (average precision; random guess ≈ problem-hour rate ~0.04–0.05). Accuracy is excluded because always predicting "no" yields ~95% accuracy.
- **Operational:** Precision and recall at a fixed alert budget of **top 20 station-hours per hour** (`k=20`).
- **Calibration:** Brier score (lower is better).
- **Uncertainty:** Day-block bootstrap (resampling whole days with replacement, 1,000 repeats on validation / 2,000 on test) because hours within a day are correlated.
- **Sensitivity:** 3% (`|net_flow| >= 18`) and 10% (`|net_flow| >= 10`) thresholds; with vs without weather.

---

## 5. Results (Lead: Marcuz Duong) — `[VALIDATION WEEK 6 — SWAP WITH TEST AFTER 26 NOV]`

### 5.1 Main comparison (5% threshold, `|net_flow| >= 15`)

| Method | PR-AUC (95% Day-Bootstrap CI) | Precision@20 | Recall@20 | Brier |
|---|---|---|---|---|
| **Random Forest (+ weather)** | **0.4988** (0.3378–0.6056) | 19.7% | 33.6% | 0.0275 |
| Random Forest (no weather) | 0.4874 (0.3249–0.6044) | **20.0%** | **34.1%** | **0.0270** |
| Lasso (+ weather), `C=0.03` | 0.4737 (0.3133–0.6001) | 19.5% | 33.3% | 0.0271 |
| Lasso (no weather), `C=0.1` | 0.4731 (0.3122–0.5995) | 19.6% | 33.4% | 0.0271 |
| Baseline 2: historical rate | 0.4079 (0.2619–0.5151) | 19.0% | 32.5% | 0.0302 |
| Baseline 1: same hour last week | 0.3812 (0.2481–0.4831) | 17.6% | 30.0% | 0.0527 |

*(Random baseline ≈ 0.0391 on Week 6, `n = 50,400` rows. See `figures/fig5_valid_pr_auc.png` and `figures/fig6_valid_precision_at_budget.png`.)*

- **Models beat baselines (Checkpoint = GO):** Paired day-bootstrap PR-AUC gain of `rf_weather` over `b2_hist_rate` is **+0.0878** (95% CI: **+0.0267 to +0.1379**). Both models also achieve lower Brier scores (~0.027 vs 0.030–0.053).
- **Weather adds little or no gain:** Paired PR-AUC difference (`weather - no_weather`) is **+0.0006** for Lasso (95% CI: **-0.0019 to +0.0030**) and **+0.0093** for Random Forest (95% CI: **-0.0056 to +0.0241**); both CIs cross zero.
- **Top signals:** In both Lasso and Random Forest, the strongest predictors are 7-day same-hour imbalance (`absnet_samehour_7d`, `net_samehour_7d`), last week's same hour (`absnet_lag168`), and morning/evening commute hours (`hour_7, hour_8, hour_9, hour_17, hour_18`).

### 5.2 Demand groups and threshold sensitivity

- **By station-demand group (Week 6 PR-AUC, `rf_weather` vs `b2_hist_rate`):** Low-demand 0.462 vs 0.364; Mid-demand 0.524 vs 0.419; High-demand 0.503 vs 0.426.
- **Threshold sensitivity (Week 6 PR-AUC):**

| Method | 3% (`>=18`) | 5% (`>=15`) | 10% (`>=10`) |
|---|---|---|---|
| Random Forest (+ weather) | **0.4931** | **0.4988** | 0.4953 |
| Random Forest (no weather) | 0.4802 | 0.4874 | **0.4963** |
| Lasso (+ weather) | 0.4684 | 0.4737 | 0.4739 |
| Baseline 2: historical rate | 0.3983 | 0.4079 | 0.4158 |
| Baseline 1: same hour last week | 0.3785 | 0.3812 | 0.3888 |

Model ordering is stable across all three definitions.

### 5.3 Error analysis and failure case (`figures/fig7_valid_failure_by_hour.png`)

At a fixed alert budget of 20 stations/hour, recall collapses during peak commute hours:
- At **08:00**, 345 problem hours occurred across Week 6, and `rf_weather` caught **82 (23.8% recall)** — even though a flat cap of `20 × 7 = 140` alerts makes >41% recall mathematically impossible. High-risk events like `E 40 St & Park Ave` (Tue 08:00, `net_flow = +50`, predicted score **0.86**) were still missed because 20 other stations scored higher.
- At **17:00**, 339 problem hours occurred and **81 (23.9%)** were caught (e.g., `9 Ave & W 33 St`, Mon 17:00, `net_flow = -78`, score 0.65).
- Meanwhile, at **02:00–04:00**, only 0–1 problem hours occurred all week, wasting nearly 100% of overnight alerts.

---

## 6. Discussion and Limitations

1. **Net flow is a proxy:** Public trip logs exclude staff rebalancing trips and real-time dock inventory, so `|net_flow|` measures rider-driven pressure rather than confirmed empty/full status.
2. **Busy stations only:** Results apply to the 300 busiest stable NYC stations, not low-volume outer stations or newly added/renamed docks.
3. **Short seasonal window:** Eight autumn weeks (Sep–Oct 2025) cannot capture winter snow or summer tourism shifts; only one holiday falls in training (Labor Day) and one in test (Columbus Day).
4. **Wide confidence intervals:** Resampling 7 validation days (or 14 test days) produces wide CIs, which we report transparently.
5. **Operational recommendation:** Pair 2-hour-ahead risk scores with live GBFS dock-inventory feeds, and replace a flat hourly alert budget with a time-varying budget (more trucks at 07:00–09:00 and 16:00–19:00, minimal overnight).

---

## 7. Reproducibility and Contributions

- **Environment:** Python 3.12 with pinned packages in `requirements.txt` (`polars`, `pandas`, `scikit-learn`, `matplotlib`, `pyarrow`, `requests`).
- **One-command reproduction:** `python get_data.py` -> `python station_hour.py` -> `.\run_all.ps1` (regenerates weather snapshot, thresholds, features, EDA figures, validation tables, and self-tests). Test weeks run once via `analysis/06_run_test_once.py` after `FREEZE.md` is committed.
- **Contributions:** Anderson Hoang (data retrieval, cleaning, station selection, lag features, error analysis, Data section); Joanna Chen (EDA, thresholds, split dates, weather join, baselines, sensitivity, Methods section, final edit); Marcuz Duong (repo/env, metrics, Lasso & RF models, test run, bootstrap CIs, README, Results section).

---

## 8. References and AI-Use Disclosure

- Lyft Bikes and Scooters, LLC. *Citi Bike System Data* (Aug–Oct 2025). https://citibikenyc.com/system-data
- Open-Meteo. *Historical Weather API* (CC BY 4.0). https://open-meteo.com/en/docs/historical-weather-api
- **AI-use disclosure:** Full log of tools, dates, prompts, and independent team verification is recorded in `AI_USE.md`. No raw Citi Bike files were uploaded to any AI tool.
