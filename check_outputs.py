"""
check_outputs.py
42.510 Citi Bike project: data checks on the finished outputs.

Run after every build:  python check_outputs.py
It checks the saved table against fixed numbers, then recounts the arrivals and
departures straight from the raw trip files with its own code, so a bug in the
build cannot hide itself. Reading the raw files takes a few minutes.
Exit code 0 = all passed; 1 = at least one check failed.
"""

# Step 1: import the tools.
from pathlib import Path                    # file paths
import sys                                  # sets the exit code
import polars as pl                         # table library
from get_data import DATA_DIR               # the raw-data folder, set in get_data.py (or local_settings.py)

# Step 2: settings. These are the fixed numbers and paths.
FOLDER = Path(__file__).resolve().parent
TABLE = FOLDER / "data_processed" / "station_hour.csv"
RAW_DIR = DATA_DIR
EXPECTED_RAW_TRIPS = 15_140_880             # all NYC trips, Aug to Oct 2025 (agreed number)
EXPECTED_STATIONS = 300
HOURS_PER_STATION = 24 * 56                 # 1,344 hours in the 56-day study period
EXPECTED_ROWS = EXPECTED_STATIONS * HOURS_PER_STATION   # 403,200
STUDY_FIRST = "2025-09-01"                  # dates as text; ISO dates sort correctly as text
STUDY_LAST = "2025-10-26"
FAILED = []                                 # names of checks that failed


def check(name, passed, detail=""):
    """Print PASS or FAIL for one check, with a short detail."""
    suffix = f" ({detail})" if detail else ""
    print(("PASS: " if passed else "FAIL: ") + name + suffix)
    if not passed:
        FAILED.append(name)


def is_blank(column):
    """True where a value is missing (null) or only spaces."""
    return pl.col(column).is_null() | (pl.col(column).str.strip_chars() == "")


def clean_id(column):
    """The team rule for station IDs: remove a trailing _ or _old. Written again here on purpose."""
    return pl.col(column).str.replace(r"_(old)?$", "")


def check_table():
    """Check the saved table. Returns the totals and station list for the raw recount, or None."""
    print("TABLE: data_processed/station_hour.csv")
    if not TABLE.exists():
        check("table file exists", False, str(TABLE))
        return None

    # Read every column as text, then turn the counts into whole numbers.
    table = pl.read_csv(TABLE, infer_schema_length=0).with_columns(
        pl.col("departures", "arrivals", "net_flow").cast(pl.Int64),
        pl.col("hour").cast(pl.Int64),
    )

    check("table has 403,200 rows", table.height == EXPECTED_ROWS, f"{table.height:,} rows")

    blank_ids = table.filter(is_blank("station_id")).height
    check("no blank station IDs", blank_ids == 0, f"{blank_ids:,} blank rows")

    real_ids = table.filter(~is_blank("station_id")).get_column("station_id").n_unique()
    check("exactly 300 distinct real stations", real_ids == EXPECTED_STATIONS, f"{real_ids} stations")

    per_station = table.group_by("station_id").agg(pl.len().alias("rows"))
    off = per_station.filter(pl.col("rows") != HOURS_PER_STATION).height
    check("every station has 1,344 hourly rows", off == 0, f"{off} stations off")

    dates = table.select(pl.col("date").min().alias("first"), pl.col("date").max().alias("last")).to_dicts()[0]
    check("dates run 1 Sep to 26 Oct 2025", dates["first"] == STUDY_FIRST and dates["last"] == STUDY_LAST,
          f"{dates['first']} to {dates['last']}")

    days = table.get_column("date").n_unique()
    check("56 distinct days", days == 56, f"{days} days")

    hours_seen = set(table.get_column("hour").to_list())
    check("hours run 0 to 23", hours_seen == set(range(24)), f"{len(hours_seen)} distinct hours")

    duplicates = table.height - table.unique(subset=["station_id", "date", "hour"]).height
    check("no duplicate station-hour rows", duplicates == 0, f"{duplicates} duplicates")

    wrong_net = table.filter(pl.col("net_flow") != pl.col("arrivals") - pl.col("departures")).height
    check("net_flow = arrivals minus departures on every row", wrong_net == 0, f"{wrong_net} rows wrong")

    negative = table.filter((pl.col("departures") < 0) | (pl.col("arrivals") < 0)).height
    check("no negative counts", negative == 0, f"{negative} rows")

    missing = table.select(pl.col("departures", "arrivals", "net_flow").is_null().sum()).row(0)
    check("no missing counts", sum(missing) == 0, f"{sum(missing)} missing values")

    no_name = table.filter(is_blank("station_name")).height
    check("every row has a station name", no_name == 0, f"{no_name:,} rows without a name")

    totals = {
        "departures": table.get_column("departures").sum(),
        "arrivals": table.get_column("arrivals").sum(),
        "stations": table.filter(~is_blank("station_id")).get_column("station_id").unique().to_list(),
    }
    print(f"  Table totals: departures {totals['departures']:,}, arrivals {totals['arrivals']:,}")
    return totals


def check_against_raw(totals):
    """Recount from the raw trip files, with separate code, and compare with the table."""
    print("RAW TRIPS: independent recount")
    files = [p for p in RAW_DIR.glob("*.csv") if "JC-" not in p.name]
    check("NYC raw CSV files found", len(files) > 0, f"{len(files)} files")
    if not files:
        return

    # Read the four columns needed, as text, one file after another without loading everything.
    trips = pl.concat(
        [pl.scan_csv(p, infer_schema_length=0) for p in files]
    ).select(
        clean_id("start_station_id").alias("start"),
        clean_id("end_station_id").alias("end"),
        pl.col("started_at").str.slice(0, 10).alias("start_day"),
        pl.col("ended_at").str.slice(0, 10).alias("end_day"),
    )

    # One pass over the raw files: total trips, plus departures and arrivals at the table's stations in the study period.
    raw = trips.select(
        pl.len().alias("trips"),
        (pl.col("start").is_in(totals["stations"]) & pl.col("start_day").is_between(pl.lit(STUDY_FIRST), pl.lit(STUDY_LAST)))
        .sum().alias("departures"),
        (pl.col("end").is_in(totals["stations"]) & pl.col("end_day").is_between(pl.lit(STUDY_FIRST), pl.lit(STUDY_LAST)))
        .sum().alias("arrivals"),
    ).collect().to_dicts()[0]

    check("raw trips total 15,140,880", raw["trips"] == EXPECTED_RAW_TRIPS, f"{raw['trips']:,} trips")
    check("table arrivals match raw trips ending at the 300 stations",
          totals["arrivals"] == raw["arrivals"], f"table {totals['arrivals']:,} vs raw {raw['arrivals']:,}")
    check("table departures match raw trips starting at the 300 stations",
          totals["departures"] == raw["departures"], f"table {totals['departures']:,} vs raw {raw['departures']:,}")


def main():
    totals = check_table()
    print()
    if totals is not None:
        check_against_raw(totals)
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed.")
        sys.exit(1)
    print("All data checks passed.")


if __name__ == "__main__":
    main()
