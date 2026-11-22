# 📋 All 38 tasks from Notion: status and where the work is

Pulled from the Notion **Tasks** database (42.510 Mission Control) on **22 Nov 2026**.
Legend: ✅ done in this folder · 🟡 done as a dry run on validation (rerun on test after the freeze) · 🔒 locked until a date or a team action · 👥 needs a human (meeting, laptop, submission)

> [!IMPORTANT]
> Two rules from the Notion plan shape this list. **(1) The test weeks (13 to 26 Oct) are scored once, after the plan freeze on Wed 25 Nov.** I wrote the test script, but it refuses to run before 26 Nov. **(2) Frozen decisions were not changed.** Two "proposed" settings are used and must be confirmed: the H-3 cut-off rule and the top-20 alert budget.

## Week 1 (15 to 17 Nov): Setup and data

| # | Task | Owner | Status | Where / what was done |
|---|---|---|---|---|
| 1 | KICK-OFF: plan, Python, open questions | All | ✅ (Notion: Done) | Meeting already held |
| 2 | Create repository with folders + start AI_USE.md | Marcuz | ✅ | Team repo cloned; added `src/`, `analysis/`, `figures/`, `results/`, `report/`, `slides/`, [AI_USE.md](../AI_USE.md) |
| 3 | Python environment: pinned versions | Marcuz | ✅ (this laptop) 👥 | [requirements.txt](../requirements.txt) pinned. 👥 Anderson and Joanna must install it on their laptops |
| 4 | Metric functions with toy tests | Marcuz | ✅ | [src/metrics.py](../src/metrics.py): self-test passes (hand-computed answers; a constant model's PR-AUC equals the problem rate) |
| 5 | Fix split dates and holiday flags | Joanna | ✅ | [src/splits.py](../src/splits.py) → `data_processed/split_dates.csv` |
| 6 | Write get_data.py | Anderson | ✅ (Anderson's code in the repo) | `get_data.py` |
| 7 | Build the station-hour table | Anderson | ✅ (Notion: Done) | `data_processed/station_hour.csv`, SHA-256 matches the README |
| 8 | Weather snapshot (Open-Meteo) | Joanna | ✅ | [analysis/01_weather_snapshot.py](../analysis/01_weather_snapshot.py) → `weather_hourly.csv` + `weather_provenance.json` (1,512 hours, no gaps) |

## Week 2 (18 to 22 Nov): Features, EDA, first models

| # | Task | Owner | Status | Where / what was done |
|---|---|---|---|---|
| 9 | Rebuild the station-hour table on a second laptop | Joanna | 👥 | Needs the raw files (about 3 GB) on Joanna's laptop: `python get_data.py`, then `python station_hour.py`, then compare the hash |
| 10 | Lag features (2-hour rule) + leakage test | Anderson | ✅ | [src/features.py](../src/features.py): the leakage test passes |
| 11 | 5% threshold from training weeks | Joanna | ✅ | [analysis/02_threshold.py](../analysis/02_threshold.py) → `results/threshold.json` (**15 bikes/hour**) |
| 12 | Lasso logistic regression, time-ordered tuning | Marcuz | ✅ | [src/models.py](../src/models.py), [src/pipeline.py](../src/pipeline.py): C tuned on weeks 1–4 → week 5 |
| 13 | EDA: 4 figures | Joanna | ✅ | [analysis/04_eda.py](../analysis/04_eda.py) → `figures/fig1`–`fig4` |
| 14 | Join weather (latest observed only) | Joanna | ✅ | `add_weather()` in `src/features.py` uses the reading from H-3 |
| 15 | Score both baselines on week 6 | Joanna | ✅ | `results/validation_week6_metrics.csv` |
| 16 | Random forest first run (defaults) | Marcuz | ✅ | Same file, with and without weather |
| 17 | CHECKPOINT: go or fallback | All | ✅ evidence · 👥 decision | `results/checkpoint_decision.json`. 👥 Record the decision in the Notion Decision log |

## Week 3 (23 to 29 Nov): Freeze, test, results

| # | Task | Owner | Status | Where / what was done |
|---|---|---|---|---|
| 18 | Report skeleton + Data section | Anderson | ✅ draft | [report/REPORT_DRAFT.md](../report/REPORT_DRAFT.md) (8 required sections) |
| 19 | FREEZE the analysis plan (Wed 25 Nov) | All | 🔒 👥 | Draft ready: [FREEZE_DRAFT.md](../FREEZE_DRAFT.md). The team reviews it, renames it to `FREEZE.md` and commits |
| 20 | Draft Methods and validation | Joanna | ✅ draft | Report §4 |
| 21 | Run the untouched test weeks ONCE | Marcuz | 🔒 | [analysis/06_run_test_once.py](../analysis/06_run_test_once.py): runs only after 25 Nov, only if `FREEZE.md` exists, and only once |
| 22 | Final figures and tables | Joanna | 🟡 | [analysis/07_bootstrap_errors_figures.py](../analysis/07_bootstrap_errors_figures.py) (`valid` now, `test` later) |
| 23 | Bootstrap CIs; per-week, per-group | Marcuz | 🟡 | Same script (resamples whole days) |
| 24 | Sensitivity: 3%/10%; with vs without weather | Joanna | 🟡 | `results/validation_week6_sensitivity.csv`; the test version runs inside script 06 |
| 25 | Draft Results section | Marcuz | 🟡 | Report §5 uses validation numbers. Swap in test numbers after the test run |
| 26 | Error analysis and failure cases | Anderson | 🟡 | Script 07 → `*_top_missed_stations.csv`, `fig7` |
| 27 | Draft Abstract, Problem, Discussion, Contributions | All | ✅ draft | Report §1, §2, §6, §7 |

## Week 4 (30 Nov to 6 Dec): Edit, rerun, submit

| # | Task | Owner | Status | Where / what was done |
|---|---|---|---|---|
| 28 | Edit to one voice and 6 pages | Joanna | 👥 | After the test numbers are in |
| 29 | Clean-clone rerun | Marcuz | ✅ helper · 👥 run | [run_all.ps1](../run_all.ps1) runs every step in order |
| 30 | AI_USE.md final + references verified | Anderson | ✅ draft · 👥 verify | [AI_USE.md](../AI_USE.md) |
| 31 | Slides: first version | All | ✅ draft | [slides/CitiBike_Problem_Hours.pptx](../slides/CitiBike_Problem_Hours.pptx) (with speaker notes) |
| 32 | README.md and licence notes | Marcuz | ✅ | [README.md](../README.md) |
| 33 | Pre-submission checklist (Sat 5 Dec) | All | 👥 | Checklist in [00_START_HERE.md](../00_START_HERE.md) |
| 34 | SUBMIT (Sun 6 Dec, before 12:00) | Anderson | 👥 | |

## Week 5 (7 to 13 Dec): Present

| # | Task | Owner | Status | Where |
|---|---|---|---|---|
| 35 | Timed rehearsal 1 | All | 👥 | Script: [presentation/PRESENTATION_GUIDE.md](../presentation/PRESENTATION_GUIDE.md) |
| 36 | Rehearsal 2 + Q&A drill from the Decision log | All | 👥 | [presentation/DEFENCE_QA.md](../presentation/DEFENCE_QA.md) |
| 37 | Finalise slides one day before | Joanna | 👥 | |
| 38 | PRESENT AND DEFEND | All | 👥 | |
