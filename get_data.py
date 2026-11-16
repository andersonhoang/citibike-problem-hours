"""
get_data.py
42.510 Citi Bike project: download, check and clean the NYC trip files.

What it does, in order:
  1. Downloads the three NYC zip files (no "JC-" prefix) into data_raw/.
  2. Unzips them into data_raw/.
  3. Checks that every CSV has the 13 expected columns.
  4. Prints the row count of each CSV.
  5. Cleans the station fields (team-approved rules) and prints the station counts.

Raw files stay in data_raw/ on your own laptop. Never commit or share them.
Run the self-test first with:  python get_data.py test
"""

# Step 1: import the tools we need.
import sys                      # reads the command-line word "test"
import tempfile                 # makes a temporary folder for the self-test
import urllib.request           # downloads files from the internet
import zipfile                  # opens .zip files
from pathlib import Path        # handles file paths on any computer
import polars as pl             # fast table library, works on large CSV files

# Step 2: settings.
# The three NYC zip links from the Citi Bike system-data page (no "JC-" prefix).
ZIP_URLS = [
    "https://s3.amazonaws.com/tripdata/202508-citibike-tripdata.zip",
    "https://s3.amazonaws.com/tripdata/202509-citibike-tripdata.zip",
    "https://s3.amazonaws.com/tripdata/202510-citibike-tripdata.zip",
]

# Folder for the raw files. By default it is a folder called data_raw next to this script.
# This folder is git-ignored and must never be committed or shared.
# To use another folder on your laptop, create a file called local_settings.py next to this script
# (local_settings.py is git-ignored) with one line, for example:
#   DATA_DIR = Path(r"C:\Users\yourname\Documents\SUTD\your-folder")
try:
    from local_settings import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).resolve().parent / "data_raw"

EXPECTED_COLUMNS = [
    "ride_id", "rideable_type", "started_at", "ended_at",
    "start_station_name", "start_station_id", "end_station_name", "end_station_id",
    "start_lat", "start_lng", "end_lat", "end_lng", "member_casual",
]


def download_zips(urls):
    """Download each zip, but skip any zip that is already in data_raw/."""
    DATA_DIR.mkdir(exist_ok=True)               # create the folder if it is missing
    for url in urls:
        target = DATA_DIR / Path(url).name      # keep the file name from the link
        if target.exists():
            print(f"Already there, skipping: {target.name}")
            continue
        print(f"Downloading: {target.name} (this is about 1 GB, it takes a while)")
        urllib.request.urlretrieve(url, target)


def unzip_all():
    """Unzip every zip in data_raw/ into the same folder."""
    for zip_path in sorted(DATA_DIR.glob("*.zip")):
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(DATA_DIR)             # writes the CSV files next to the zip
        print(f"Unzipped: {zip_path.name}")


def list_trip_csvs():
    """Return the NYC CSV files only. Files with 'JC-' in the name are Jersey City and are skipped."""
    return sorted(p for p in DATA_DIR.glob("*.csv") if "JC-" not in p.name)


def check_columns(csv_path):
    """Stop with an error if any of the 13 expected columns is missing."""
    header = pl.read_csv(csv_path, n_rows=0).columns   # read only the header row
    missing = [c for c in EXPECTED_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"{csv_path.name} is missing columns: {missing}")


def scan_csv(csv_path):
    """Open a CSV without loading it all into memory. Every column is read as text."""
    return pl.scan_csv(csv_path, infer_schema_length=0)


def has_real_id(column):
    """True where a station ID is present: not missing (null) and not only spaces.
    A blank ID is not a station, so the project drops these rows before counting stations."""
    return pl.col(column).is_not_null() & (pl.col(column).str.strip_chars() != "")


def clean(lf):
    """Apply the team-approved rules. Takes a lazy table, returns a lazy table."""
    return lf.with_columns(
        # Rule 1: remove a trailing "_" or "_old" from station IDs (for example 5303.06_ or 5348.06_old becomes 5348.06).
        pl.col("start_station_id").str.replace(r"_(old)?$", ""),
        pl.col("end_station_id").str.replace(r"_(old)?$", ""),
        # Rule 2: remove leading and trailing spaces from station names.
        pl.col("start_station_name").str.strip_chars(),
        pl.col("end_station_name").str.strip_chars(),
        # Turn the two time columns into real date-time values.
        pl.col("started_at").str.to_datetime(strict=False),
        pl.col("ended_at").str.to_datetime(strict=False),
    )


def run_self_test():
    """Run the cleaning on a tiny made-up file where we know the answers."""
    rows = [
        "start_station_id,start_station_name,end_station_id,end_station_name,started_at,ended_at",
        "5303.06,Clinton St & Grand St ,6000.1,A,2025-08-05 12:38:34.768,2025-08-05 12:47:13.228",
        "5303.06_,Clinton St & Grand St,6000.1_,A,2025-08-05 13:00:00.000,2025-08-05 13:10:00.000",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tiny.csv"
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        df = clean(scan_csv(path)).collect()
    # Known answers: 2 trips, 1 start ID, 1 start name, 1 end ID.
    assert df.height == 2, "expected 2 trips"
    assert df["start_station_id"].n_unique() == 1, "expected 1 start station ID"
    assert df["start_station_name"].n_unique() == 1, "expected 1 start station name"
    assert df["end_station_id"].n_unique() == 1, "expected 1 end station ID"
    print("Self-test passed: 2 trips, 1 start ID, 1 start name, 1 end ID.")


def main():

    download_zips(ZIP_URLS)
    unzip_all()

    csv_files = list_trip_csvs()
    if not csv_files:
        raise SystemExit("No NYC CSV files found in data_raw/. Check the downloads.")

    # Check columns and count rows, one file at a time.
    total_rows = 0
    for csv_path in csv_files:
        check_columns(csv_path)
        rows = scan_csv(csv_path).select(pl.len()).collect().item()
        total_rows += rows
        print(f"{csv_path.name}: {rows:,} rows")
    print(f"Total rows: {total_rows:,}")

    # Clean all files together and count the stations.
    all_trips = clean(pl.concat([scan_csv(p) for p in csv_files]))
    counts = all_trips.select(
        # Count distinct REAL IDs only. A blank ID is not a station.
        pl.col("start_station_id").filter(has_real_id("start_station_id")).n_unique().alias("start_station_ids"),
        pl.col("start_station_name").filter(has_real_id("start_station_id")).n_unique().alias("start_station_names"),
        (~has_real_id("start_station_id")).sum().alias("trips_with_blank_start_id"),
    ).collect()
    print(counts.to_dicts())
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_self_test()
    else:
        main()
