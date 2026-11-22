# Run the whole pipeline in order (clean-clone rerun helper).
# Usage (PowerShell, from the repo root):  .\run_all.ps1
# Step 0 (only if rebuilding the station-hour table from raw data): python get_data.py ; python station_hour.py
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\python -m pip install -r requirements.txt }
$py = ".\.venv\Scripts\python"
Write-Host "== Self-tests ==";              & $py -m src.splits; & $py -m src.metrics; & $py -m src.features; & $py -m src.models
# The weather snapshot is downloaded ONCE and then kept (its retrieval date is part of the provenance).
# Delete data_processed\weather_hourly.csv only if you deliberately want a new snapshot.
if (Test-Path data_processed\weather_hourly.csv) { Write-Host "== 1 Weather snapshot: kept existing file ==" }
else { Write-Host "== 1 Weather snapshot =="; & $py analysis/01_weather_snapshot.py }
Write-Host "== 2 Threshold ==";             & $py analysis/02_threshold.py
Write-Host "== 3 Features ==";              & $py analysis/03_build_features.py
Write-Host "== 4 EDA figures ==";           & $py analysis/04_eda.py
Write-Host "== 5 Validation (week 6) ==";   & $py analysis/05_validate_week6.py
Write-Host "== 7 Bootstrap/errors (valid) =="; & $py analysis/07_bootstrap_errors_figures.py valid
Write-Host "Done. Test weeks: run analysis/06_run_test_once.py ONCE after the freeze, then 07 with 'test'."
