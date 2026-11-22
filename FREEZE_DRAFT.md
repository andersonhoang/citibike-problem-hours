# FREEZE DRAFT: analysis plan (to be confirmed by Anderson, Joanna and Marcuz on Wed 25 Nov 2026)

> When all three agree: rename this file to `FREEZE.md` (or `analysis/ANALYSIS_PLAN.md`), fill in the sign-off, commit it, and tag the commit `plan-frozen` (`git tag plan-frozen && git push origin main --tags`).
> `analysis/06_run_test_once.py` will not run until the freeze file exists and the date is after 25 Nov 2026.

## Fixed earlier (Decision log, locked)
- Question, unit (station-hour), 300 busiest stations (training weeks only), period 1 Sep to 26 Oct 2025.
- Split: weeks 1–5 train, week 6 validation, weeks 7–8 test (scored once).
- Methods: 2 baselines, lasso logistic regression, random forest; each model without and with weather.
- Metrics: PR-AUC (primary), precision/recall at the alert budget, Brier; bootstrap over whole test days.

## Items fixed by this freeze (computed or proposed; please confirm)
| Item | Value | Source |
|---|---|---|
| Problem-hour threshold (5%) | \|net flow\| ≥ **15** bikes/hour (training rate 5.15%) | `results/threshold.json` |
| Sensitivity thresholds | 3% → ≥ 18; 10% → ≥ 10 | same file |
| Cut-off rule ("2 hours ahead") | **PROPOSED:** to predict hour H, use data up to the end of hour H-3 | project context §5 |
| Alert budget | **PROPOSED:** top 20 station-hours per hour | project context §8 |
| Features (27 + 3 weather) | `src/features.py` → `feature_lists()` | code |
| Lasso tuning grid | C ∈ {0.001, 0.003, 0.01, 0.03, 0.1, 1}, fit weeks 1–4, choose by PR-AUC on week 5 | `src/models.py` |
| Chosen lasso C | see `results/checkpoint_decision.json` | validation run |
| Random forest | scikit-learn defaults (100 trees), random_state = 42 | `src/models.py` |
| Final fit for the test run | **PROPOSED:** refit on weeks 1–6 with the C values above; threshold unchanged | `analysis/06_run_test_once.py` |
| First week (1–7 Sep) | not used for fitting (no 7-day history, because August is not in the aggregated table) | `has_history` flag |
| Station list | the 300 stations in `data_processed/station_hour.csv` | Anderson |
| Checkpoint decision | see `results/checkpoint_decision.json` | validation run |

## Sign-off
- Anderson: ______ date ______
- Joanna: ______ date ______
- Marcuz: ______ date ______
