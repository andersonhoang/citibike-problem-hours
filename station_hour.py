"""
station_hour.py
42.510 Citi Bike project: build the station-hour table.

For the 300 busiest stations (chosen from the training weeks only), it counts
departures and arrivals for every hour from 1 Sep to 26 Oct 2025, then works out net flow.
Output: data_processed/station_hour.csv (aggregated counts, not raw trips).

Run the self-test first:  python station_hour.py test
Then build the table:     python station_hour.py
"""

# Step 1: import the tools we need.
import sys                                          # reads the command-line word "test"
from datetime import datetime, timedelta           # date-times and time steps
from pathlib import Path                            # file paths
import polars as pl                                 # table library
from get_data import DATA_DIR, clean, has_real_id, list_trip_csvs, scan_csv   # reuse the functions from get_data.py
from src.config import TEST, TRAIN                  # the one place for the study dates

# Step 2: settings. The dates come from src/config.py, so they cannot drift apart.
TRAIN_FIRST, TRAIN_LAST = TRAIN                     # training weeks 1 to 5 (1 Sep to 5 Oct 2025)
TRAINING_DAYS = (TRAIN_LAST - TRAIN_FIRST).days + 1                 # 35 days, inclusive
STUDY_FIRST, STUDY_LAST = TRAIN_FIRST, TEST[1]      # the study period, 1 Sep to 26 Oct 2025
STUDY_DAYS = (STUDY_LAST - STUDY_FIRST).days + 1                    # 56 days, inclusive
TOP_N = 300                        # number of busiest stations
OUTPUT_DIR = Path(__file__).resolve().parent / "data_processed"


def load_trips():
    """Read all trip files (Aug to Oct) and clean them. Nothing is loaded into memory yet."""
    trips = clean(pl.concat([scan_csv(p) for p in list_trip_csvs()]))
    return trips.select("started_at", "ended_at", "start_station_id", "end_station_id", "start_station_name")


def hourly_counts(trips):
    """Count departures and arrivals for each station and hour that had at least one trip."""
    # Departures: count trips by the hour they started, at their start station.
    departures = (
        trips.select(
            pl.col("start_station_id").alias("station_id"),
            pl.col("started_at").dt.truncate("1h").cast(pl.Datetime("us")).alias("hour_start"),
        )
        .group_by("station_id", "hour_start")
        .agg(pl.len().alias("departures"))
    )
    # Arrivals: count trips by the hour they ended, at their end station.
    # A trip that starts on 31 Aug and ends on 1 Sep is counted as an arrival on 1 Sep.
    arrivals = (
        trips.select(
            pl.col("end_station_id").alias("station_id"),
            pl.col("ended_at").dt.truncate("1h").cast(pl.Datetime("us")).alias("hour_start"),
        )
        .group_by("station_id", "hour_start")
        .agg(pl.len().alias("arrivals"))
    )
    # Join the two counts. A station-hour with only departures (or only arrivals) gets 0 for the other.
    return (
        departures.join(arrivals, on=["station_id", "hour_start"], how="full", coalesce=True)
        .with_columns(pl.col("departures", "arrivals").fill_null(0))
    )


def pick_top_stations(trips):
    """Choose the busiest stations using the training weeks only."""
    # One row per trip start and one row per trip end, each with its station and day.
    events = (
        pl.concat([
            trips.select(pl.col("start_station_id").alias("station_id"), pl.col("started_at").dt.date().alias("day")),
            trips.select(pl.col("end_station_id").alias("station_id"), pl.col("ended_at").dt.date().alias("day")),
        ])
        # A blank station ID is not a station. Drop those rows first, or the blank group can rank in the top 300.
        .filter(has_real_id("station_id"))
        .filter(pl.col("day").is_between(TRAIN_FIRST, TRAIN_LAST))
    )

    # For each station: total trip volume (starts plus ends) and how many training days it was active.
    stats = events.group_by("station_id").agg(
        pl.len().alias("trip_volume"),
        pl.col("day").n_unique().alias("days_present"),
    )

    # Exclude stations not active on every training day (renamed, added or removed).
    # Team rule, confirmed 16 Nov 2026.
    eligible = stats.filter(pl.col("days_present") == TRAINING_DAYS)

    # Keep the TOP_N stations with the most trips.
    return eligible.sort("trip_volume", descending=True).head(TOP_N).select("station_id")


def excluded_stations(trips):
    """List real stations seen in the study period that fail the rule 'active on all 35 training days', with the reason."""
    events = (
        pl.concat([
            trips.select(pl.col("start_station_id").alias("station_id"), pl.col("started_at").dt.date().alias("day")),
            trips.select(pl.col("end_station_id").alias("station_id"), pl.col("ended_at").dt.date().alias("day")),
        ])
        .filter(has_real_id("station_id"))
        .filter(pl.col("day").is_between(STUDY_FIRST, STUDY_LAST))
    )
    # Training-week activity per station (0 days if the station only appears after 5 Oct).
    in_training = pl.col("day") <= TRAIN_LAST
    stats = events.group_by("station_id").agg(
        pl.col("day").filter(in_training).n_unique().alias("training_days_active"),
        pl.col("day").filter(in_training).len().alias("training_trip_volume"),
    )
    names = (
        trips.group_by("start_station_id")
        .agg(pl.col("start_station_name").first().alias("station_name"))
        .rename({"start_station_id": "station_id"})
    )
    return (
        stats.filter(pl.col("training_days_active") < TRAINING_DAYS)
        .join(names, on="station_id", how="left")
        .with_columns(
            pl.concat_str([
                pl.lit("active on "),
                pl.col("training_days_active").cast(pl.Utf8),
                pl.lit(f" of {TRAINING_DAYS} training days "
                       f"({TRAIN_FIRST.day} {TRAIN_FIRST:%b} to {TRAIN_LAST.day} {TRAIN_LAST:%b})"),
            ]).alias("reason")
        )
        .select("station_id", "station_name", "training_days_active", "training_trip_volume", "reason")
        .sort("training_trip_volume", "station_id", descending=[True, False])
    )


def build_table(top, flows, trips):
    """Make one row for every chosen station and every hour in the study period, then add the counts."""
    # All hours from 1 Sep 00:00 to 26 Oct 23:00 (56 days x 24 hours = 1,344 hours).
    hours = (
        pl.datetime_range(
            datetime.combine(STUDY_FIRST, datetime.min.time()),                              # 00:00 on the first day
            datetime.combine(STUDY_LAST, datetime.min.time()) + timedelta(hours=23),         # 23:00 on the last day
            interval="1h", eager=True)
        .cast(pl.Datetime("us"))
        .alias("hour_start")
        .to_frame()
        .lazy()
    )
    # Station names: one name per station ID.
    names = (
        trips.group_by("start_station_id")
        .agg(pl.col("start_station_name").first().alias("station_name"))
        .rename({"start_station_id": "station_id"})
    )
    # Every chosen station combined with every hour (cross join).
    # Then add the counts. Hours with no trips get 0.
    return (
        top.join(hours, how="cross")
        .join(flows, on=["station_id", "hour_start"], how="left")
        .with_columns(pl.col("departures", "arrivals").fill_null(0))
        .join(names, on="station_id", how="left")
        .with_columns(
            # Net flow = arrivals minus departures. Counts are unsigned in polars, so cast to a signed type first,
            # or a negative result wraps around to a huge positive number (found 16 Nov 2026).
            (pl.col("arrivals").cast(pl.Int64) - pl.col("departures").cast(pl.Int64)).alias("net_flow"),
            pl.col("hour_start").dt.date().alias("date"),
            pl.col("hour_start").dt.hour().alias("hour"),
        )
        .select("station_id", "station_name", "date", "hour", "departures", "arrivals", "net_flow")
        .sort("station_id", "date", "hour")
    )


def check_table(table, top, trips):
    """Stop with an error if the table is not the right size, or its arrivals do not match the raw trips."""
    # Check 1: 300 stations x 24 hours x 56 days = 403,200 rows.
    rows = table.select(pl.len()).collect().item()
    expected = TOP_N * 24 * STUDY_DAYS
    assert rows == expected, f"expected {expected:,} rows, got {rows:,}"

    # Check 2: total arrivals in the table = trips ending at the chosen stations in the study period.
    top_ids = top.collect()["station_id"].to_list()
    table_arrivals = table.select(pl.col("arrivals").sum()).collect().item()
    direct_arrivals = (
        trips.filter(
            pl.col("ended_at").dt.date().is_between(STUDY_FIRST, STUDY_LAST)
            & pl.col("end_station_id").is_in(top_ids)
        )
        .select(pl.len())
        .collect()
        .item()
    )
    assert table_arrivals == direct_arrivals, f"arrivals {table_arrivals:,} != trips {direct_arrivals:,}"
    # Check 3: no blank station IDs in the table, and exactly TOP_N distinct stations.
    blank_rows = table.filter(~has_real_id("station_id")).select(pl.len()).collect().item()
    assert blank_rows == 0, f"{blank_rows:,} table rows have a blank station ID"
    distinct = table.select(pl.col("station_id").n_unique()).collect().item()
    assert distinct == TOP_N, f"expected {TOP_N} distinct stations, got {distinct}"

    # Check 4: no blank IDs among the chosen stations.
    blank_top = top.filter(~has_real_id("station_id")).select(pl.len()).collect().item()
    assert blank_top == 0, f"{blank_top} chosen stations have a blank ID"

    # Check 5: net flow is arrivals minus departures on every row. A wrapped-around value fails here.
    wrong_net = table.filter(
        pl.col("net_flow").cast(pl.Int64)
        != pl.col("arrivals").cast(pl.Int64) - pl.col("departures").cast(pl.Int64)
    ).select(pl.len()).collect().item()
    assert wrong_net == 0, f"{wrong_net:,} rows have a wrong net_flow"

    print(f"Checks passed: {rows:,} rows, {table_arrivals:,} arrivals, {distinct} stations.")


def run_self_test():
    """Known answers on a tiny made-up file, including a trip that crosses midnight."""
    import tempfile
    rows = [
        "start_station_id,start_station_name,end_station_id,end_station_name,started_at,ended_at",
        "A,Alpha,B,Beta,2025-09-01 08:10:00.000,2025-09-01 08:40:00.000",
        "A,Alpha,B,Beta,2025-08-31 23:50:00.000,2025-09-01 00:10:00.000",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tiny.csv"
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        flows = hourly_counts(clean(scan_csv(path))).collect()

    def value(station, when, column):
        """Return the count for one station and hour (0 if there is no row)."""
        found = flows.filter((pl.col("station_id") == station) & (pl.col("hour_start") == when))
        return found[column].sum() if found.height else 0

    # Known answers.
    assert value("A", datetime(2025, 9, 1, 8), "departures") == 1, "A should depart once at 08:00"
    assert value("B", datetime(2025, 9, 1, 8), "arrivals") == 1, "B should arrive once at 08:00"
    assert value("A", datetime(2025, 8, 31, 23), "departures") == 1, "A should depart once at 23:00 on 31 Aug"
    assert value("B", datetime(2025, 9, 1, 0), "arrivals") == 1, "B should arrive once at 00:00 on 1 Sep"
    # Known answer: a trip with a blank start station ID is dropped, so it cannot be picked as a station.
    rows_blank = [
        "start_station_id,start_station_name,end_station_id,end_station_name,started_at,ended_at",
        "A,Alpha,B,Beta,2025-09-01 08:10:00.000,2025-09-01 08:40:00.000",
        ",,B,Beta,2025-09-01 09:10:00.000,2025-09-01 09:40:00.000",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "blank.csv"
        path.write_text("\n".join(rows_blank) + "\n", encoding="utf-8")
        kept = clean(scan_csv(path)).filter(has_real_id("start_station_id")).collect()
    assert kept.height == 1, "the blank-ID trip should be dropped"

    print("Self-test passed: departures and arrivals are in the right hours, including the midnight trip.")
    print("Self-test passed: trips with a blank station ID are dropped.")


def main():
    trips = load_trips()
    top = pick_top_stations(trips)
    flows = hourly_counts(trips)
    table = build_table(top, flows, trips)
    check_table(table, top, trips)

    OUTPUT_DIR.mkdir(exist_ok=True)                 # create data_processed/ if it is missing
    out_path = OUTPUT_DIR / "station_hour.csv"
    table.collect().write_csv(out_path)
    print(f"Saved: {out_path}")

    # Save the stations left out by the 35-day rule, with the reason for each.
    excluded = excluded_stations(trips).collect()
    excluded_path = OUTPUT_DIR / "excluded_stations.csv"
    excluded.write_csv(excluded_path)
    print(f"Saved: {excluded_path} ({excluded.height:,} stations excluded)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_self_test()
    else:
        main()
