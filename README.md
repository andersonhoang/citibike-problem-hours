# Citi Bike station-hour prediction (42.510 Statistical Learning for Data Science, SUTD)

Group project: Anderson Hoang, Joanna Chen, Marcuz Duong. Python only.

This repo builds the station-hour table: 300 busiest NYC Citi Bike stations x 24 hours x 56 days (1 Sep to 26 Oct 2025) = 403,200 rows, with departures, arrivals and net flow (arrivals minus departures).

## Raw data: licence warning

The Citi Bike trip files are licensed. **Never commit, upload or share them** (no shared Drive, no repo). They live in a git-ignored folder on your own laptop. Only the aggregated tables in `data_processed/` are in the repo (team decision, 16 Nov 2026).

## Set up

1. Python 3.10 or newer (built and tested with 3.14).
2. `pip install -r requirements.txt` (polars; tested with 2.1.0).
3. Optional: if your raw files are not in `data_raw/` next to the scripts, create `local_settings.py` next to `get_data.py` with these two lines. Create it in an editor such as Notepad or VS Code. It is git-ignored.

```python
from pathlib import Path
DATA_DIR = Path(r"C:\your\raw\folder")
```

## Run, in this order

```
python get_data.py          # downloads the 3 zips (about 3 GB), unzips, checks columns, cleans station fields
python station_hour.py test # self-test on a tiny made-up file
python station_hour.py      # builds data_processed/station_hour.csv and excluded_stations.csv (a few minutes)
python check_code.py        # code and git-safety checks: expect 5 of 5
python check_outputs.py     # data checks, recounted from the raw trips: expect 17 of 17 (a few minutes)
```

Fingerprint of the table (PowerShell):

```
Get-FileHash data_processed\station_hour.csv -Algorithm SHA256
```

Expected: `fad529850ef096b3ee3d6a7bc414362b9cb5fadfd8cb1b0c145eaa2a12f04114`. A match means your table equals the team's, row for row. If it differs, compare the row count and totals: 403,200 rows, 4,337,394 arrivals, 4,376,848 departures.

`git status` may show the two CSVs in `data_processed/` as modified after a rebuild. The content is identical; it is only Windows line-ending handling. Do not commit those.

## Files

| File | What it does |
|---|---|
| `get_data.py` | Download, unzip, column check, station cleaning rules (shared functions) |
| `station_hour.py` | Picks the 300 stations (training weeks only) and builds the table |
| `check_code.py` | Code rules and repo-safety checks |
| `check_outputs.py` | Table checks plus an independent recount from the raw trips |
| `check_stations.py` | Diagnostic: names and IDs that do not match across months |
| `data_processed/station_hour.csv` | The table: 403,200 rows |
| `data_processed/excluded_stations.csv` | 341 stations left out by the 35-day rule, with the reason |

## Data facts (verified on a fresh download, 20 Nov 2026)

| File | Size | Trips |
|---|---|---|
| `202508-citibike-tripdata.zip` | 953.9 MB | 5,121,533 |
| `202509-citibike-tripdata.zip` | 984.6 MB | 5,287,447 |
| `202510-citibike-tripdata.zip` | 881.3 MB | 4,731,900 |

Total 15,140,880 trips in 17 CSV files, 13 columns each. Files with a "JC-" prefix (Jersey City) are not used.

## Team rules (agreed 16 Nov 2026)

1. Station IDs: remove a trailing `_` or `_old`.
2. Station names: trim leading and trailing spaces.
3. Blank station IDs are dropped before the 300 busiest are picked.
4. A station is kept only if it is active on all 35 training days (1 Sep to 5 Oct 2025). Renamed, added or removed stations are excluded.
5. Trip volume = trips starting plus trips ending at the station in the training weeks. The 300 busiest are chosen from training weeks only.
6. A trip that crosses midnight is counted as an arrival at its end hour.
7. `data_processed/` CSV files may be in the repo. Raw data never.

Do not change the question, split, metrics or methods without the team.
