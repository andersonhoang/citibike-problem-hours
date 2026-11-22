# PROJECT_CONTEXT.md — Master Project Facts (42.510 Citi Bike Problem Hours)

> Master copy pulled from Notion page **Project context (plain text)** (Owner: Anderson, updated 13 Nov 2026; Section 16 agreed 16 Nov 2026).  
> If this file and the Notion page ever differ, the Notion page is the master.

## 0. Rules for any AI assistant
1. Follow the decisions on this page. Do not change the question, outcome definition, split, metrics or methods. If you think one is wrong, say so and stop; the team decides.
2. Never invent data, results, numbers, citations, links or licence terms. If you have not run code, say "not run".
3. Never ask for or accept the raw Citi Bike files. Work from column names and small made-up samples only (the data is licensed and may not be redistributed).
4. Write Python. Explain every block in plain English, because every team member must be able to explain and modify every line in an oral defence.
5. Use prediction or association wording only. No causal words such as "effect", "impact" or "causes".
6. Respect the leakage rules in Section 6 in every piece of code.
7. End every answer with: what you assumed, what the team must verify, and one small test with a known answer.

## 1. Course and deadlines
- Course: 42.510 Statistical Learning for Data Science, SUTD. Instructor Assoc. Prof. Bikramjit Das; TA Dr. Darryl Teo.
- Project weight: 30 points (proposal 5, final report 10, presentation and oral defence 15).
- Final report and reproducible analysis package: due Sunday 6 Dec 2026, 23:59 (time zone assumed Singapore; to confirm). Team plan: submit Sunday 6 Dec before 12:00.
- Presentation and defence: in class, 7 to 13 Dec 2026, 12 to 15 minutes plus about 5 to 7 minutes of questions. Exact slot to confirm.
- Team availability: working adults. Weeknights ~1 hour; Saturday from 12:00 and all of Sunday for heavy tasks.

## 2. The project
- **Title:** Predicting Problem Hours at Busy Citi Bike Stations to Prioritise Rebalancing (NYC, Sep to Oct 2025). Catalog topic 2.1.
- **Primary question:** For Citi Bike operations planners, can trip history, calendar and weather information available 2 hours before each hour help predict which station-hours will be high-imbalance problem hours at the 300 busiest New York City stations in September to October 2025?
- **Audience:** bike-share operations planners deciding which stations to rebalance next.
- **Scope:** prediction only. Not causal effects. Not truck routing. 2-hour lead time is an operational assumption for truck dispatch, not a Citi Bike figure.

## 3. Team and roles
| Member | Leads | Report section |
|---|---|---|
| Anderson Hoang | Data retrieval, cleaning, station selection, lag features, error analysis, `AI_USE.md` | Data |
| Joanna Chen | EDA, baselines, threshold, split dates, weather join, sensitivity, table rebuild check, final report edit | Methods |
| Marcuz Duong | Repository, Python environment, metric functions, models, test run, bootstrap, `README.md`, clean-clone rerun | Results |

All three share question formulation, slides and defence preparation. Every member must speak and can be asked any question.

## 4. Data
### 4.1 Citi Bike trips
- Source: https://citibikenyc.com/system-data
- Files: NYC monthly zips WITHOUT `JC-` prefix: `202508`, `202509`, `202510` (~1 GB each; 15,140,880 trips across 17 CSVs).
- Licence: Citi Bike Data Sharing Policy (Lyft Bikes and Scooters, LLC). Raw CSVs must NOT be redistributed or committed; provide `get_data.py`. Aggregated station-hour counts in `data_processed/` may be kept in the repo (team decision, 16 Nov 2026). Do not link trips to riders. Do not imply endorsement.
- Columns (13): `ride_id`, `rideable_type`, `started_at`, `ended_at`, `start_station_name`, `start_station_id`, `end_station_name`, `end_station_id`, `start_lat`, `start_lng`, `end_lat`, `end_lng`, `member_casual`.
- Read `start_station_id` and `end_station_id` as TEXT. `member_casual` is not used as a rider attribute.

### 4.2 Weather
- Source: Open-Meteo Historical Weather API (https://open-meteo.com/en/docs/historical-weather-api). Licence CC BY 4.0, non-commercial use; cite in references.
- One citywide hourly series for NYC (`lat=40.78, lon=-73.97`, `America/New_York`, 25 Aug to 26 Oct 2025): temperature, precipitation, wind speed. Save query, parameters, retrieval date and metadata.

## 5. Definitions
- **Unit:** one station in one hour (`station-hour`).
- **Net flow** = arrivals minus departures.
- **Study period:** Mon 1 Sep 2025 to Sun 26 Oct 2025 = 56 days = 8 full weeks.
- **Stations:** 300 busiest by training trip volume (starts + ends), after excluding stations inactive on any of the 35 training days.
- **Sample size:** `300 × 24 × 56 = 403,200` station-hours.
- **Primary outcome:** `problem_hour = 1` if `|net_flow|` is in top 5% of TRAINING station-hours (`>= 15` bikes/hr), else 0. Fixed once from training weeks.
- **Lead time:** 2 hours ahead (proposed cut-off: use data up to end of hour `H-3`).
- **Holidays:** Labor Day (Mon 1 Sep 2025, training) and Columbus Day (Mon 13 Oct 2025, test).

## 6. Validation and leakage rules
| Split | Weeks | Dates (2025) |
|---|---|---|
| Training | 1 to 5 | 1 Sep to 5 Oct |
| Validation | 6 | 6 to 12 Oct |
| Test (untouched) | 7 to 8 | 13 to 26 Oct |

- Threshold, station list, scaling, feature selection, and tuning use training weeks only.
- Features use only data available 2 hours before target hour (`<= H-3`). Never target-hour trips or weather.
- Test weeks scored **exactly once**, after plan freeze on Wed 25 Nov 2026 (`plan-frozen` tag). No random train/test split.

## 7. Methods (fixed)
- Baseline 1: same station-hour last week (`lag 168h`).
- Baseline 2: station's historical problem-hour rate by `(station_id, hour, weekday)` from training weeks.
- Model 1: Lasso logistic regression (without and with weather).
- Model 2: Random forest (without and with weather).
- No other methods will be added.

## 8. Metrics (fixed)
- Primary: PR-AUC (average precision; random guess ≈ problem-hour rate ~0.05).
- Precision and recall at a fixed alert budget (proposed: top 20 station-hours per hour).
- Brier score.
- Per test week and by station-demand group, with bootstrap 95% CIs resampling **whole test days**.
- No accuracy. Sensitivity checks: 3% (`>=18`) and 10% (`>=10`) thresholds; with vs without weather.

## 9. Risk, fallback and limitations
- Main risk: models fail to beat baselines -> Fallback: predict net flow (MAE) and report negative result honestly. (Validation Week 6 result: **GO**.)
- Limitations: no staff rebalancing or dock inventory (net flow is proxy); 1 holiday in train and 1 in test; busy 300 stations only; 8 weeks cannot show seasonal change.

## 10–14. Software, AI rules, Deliverables, Schedule, Glossary
- Python only; layout: `README.md`, `requirements.txt`, `get_data.py`, `data_processed/`, `src/`, `analysis/`, `figures/`, `report/`, `slides/`, `AI_USE.md`.
- Final report (10 pts): max 6 A4 pages, 11–12 pt, 8 required sections.
- Presentation (15 pts): 12–15 min + 5–7 min Q&A; audience in minute 1, data story, baseline/methods/split/metrics, 2–3 decisive results, 1 important failure, direct answer.

## 15. Open items & Environment Record (updated 22 Nov 2026)
- **Pinned Python & packages (verified on Marcuz's laptop, 22 Nov 2026 — Anderson & Joanna to confirm):**
  `Python 3.12.10`, `polars==1.44.2`, `pandas==3.1.1`, `numpy==2.5.5`, `scipy==1.18.1`, `scikit-learn==1.9.1`, `matplotlib==3.11.2`, `seaborn==0.13.2`, `pyarrow==26.0.1`, `requests==2.34.2`, `python-pptx==1.0.2`, `python-docx==1.2.0`, `ipykernel==7.4.0`, `nbconvert==7.17.2`.
- **Still to confirm by team:** formal proposal approval / instructor feedback; exact presentation slot; submission platform and time zone; final sign-off on `H-3` cut-off, top-20 alert budget, and Weeks 1–6 refit in `FREEZE.md`.

## 16. Data and station decisions (agreed 16 Nov 2026)
1. Strip trailing `_` or `_old` from station IDs.
2. Trim leading/trailing spaces on station names.
3. Keep only stations active on all 35 training days (1 Sep–5 Oct) before picking top 300.
4. Rank by `starts + ends` in training weeks.
5. Aggregated station-hour counts may be kept in `data_processed/`; raw trips never committed.
