# Rebuild check: station-hour table on a second laptop (Joanna)

Notion task: **Rebuild the station-hour table from the script on a second laptop** (owner Joanna, reviewer Anderson).
Done when: identical row counts and totals to Anderson's table.

**Result: identical.** The table rebuilt from the raw trips on Joanna's laptop is byte-for-byte the same as `data_processed/station_hour.csv` on `main`.

## Set-up

| Item | Value |
|---|---|
| Date | 27 Nov 2026 |
| Repository | `main` at `8439783` (after PRs #3, #4, #5, #7) |
| Python / polars | 3.14.4 / 2.1.0 (pinned `requirements.txt`; `analysis/00_check_env.py`: 11/11 OK) |
| Raw data | Downloaded fresh by `get_data.py` from `s3.amazonaws.com/tripdata/` into the git-ignored `data_raw/` (not shared, per the licence) |

| Zip file | Size (bytes) |
|---|---|
| `202508-citibike-tripdata.zip` | 1,000,258,641 |
| `202509-citibike-tripdata.zip` | 1,032,411,368 |
| `202510-citibike-tripdata.zip` | 924,115,389 |

17 NYC CSV files, 13 columns each, **15,140,880 trips** (same as the README's data facts).

## Steps run (README order)

1. `python get_data.py test`: self-test passed.
2. `python get_data.py`: download, unzip, column check, station cleaning.
3. `python station_hour.py test`: both self-tests passed (midnight trip, blank IDs dropped).
4. `python station_hour.py`: 403,200 rows, 300 stations, 341 stations excluded.
5. `python check_code.py`: 5 of 5 passed.
6. `python check_outputs.py`: 17 of 17 passed, including the independent recount from the raw trips.

## Comparison with the team's table

| Check | Team table (`main`) | Rebuild on Joanna's laptop |
|---|---|---|
| SHA-256 `station_hour.csv` | `fad529850ef096b3ee3d6a7bc414362b9cb5fadfd8cb1b0c145eaa2a12f04114` | `fad529850ef096b3ee3d6a7bc414362b9cb5fadfd8cb1b0c145eaa2a12f04114` |
| SHA-256 `excluded_stations.csv` | `0e42ad1777d0b6ff3bb8cac194bf350b87e152df2e29ae87bfa8de02fafdf909` | `0e42ad1777d0b6ff3bb8cac194bf350b87e152df2e29ae87bfa8de02fafdf909` |
| Rows | 403,200 | 403,200 |
| Stations x days x hours | 300 x 56 x 24 | 300 x 56 x 24 |
| Arrivals | 4,337,394 | 4,337,394 |
| Departures | 4,376,848 | 4,376,848 |
| Excluded stations | 341 | 341 |

`git status` after the rebuild showed no change to any tracked file, so the rebuilt CSVs are not part of this pull request: they are already on `main`.
