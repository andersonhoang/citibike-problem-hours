"""
check_stations.py
Finds station names and IDs that do not match across all three months.
Uses the same two cleaning rules as get_data.py.
"""

# Step 1: import the tools.
from pathlib import Path        # handles file paths
import polars as pl             # reads the large CSV files

# Step 2: point at the folder with the raw CSV files.
from get_data import DATA_DIR as folder   # the raw-data folder, set in get_data.py (or local_settings.py)
files = [p for p in folder.glob("*.csv") if "JC-" not in p.name]   # skip Jersey City files

# Step 3: read only the two station columns, as text, and clean them.
trips = (
    pl.concat([pl.scan_csv(p, infer_schema_length=0) for p in files])
    .select("start_station_id", "start_station_name", "started_at")
    # A blank station ID is not a station: drop those rows before counting.
    .filter(pl.col("start_station_id").is_not_null() & (pl.col("start_station_id").str.strip_chars() != ""))
    .with_columns(
        pl.col("start_station_id").str.replace(r"_(old)?$", ""),   # rule 1: remove trailing "_" or "_old"
        pl.col("start_station_name").str.strip_chars(),      # rule 2: remove spaces at the ends
    )
)

# Check 1: names that are used by more than one cleaned ID.
print("Names with more than one ID:")
print(
    trips.group_by("start_station_name")
    .agg(pl.col("start_station_id").n_unique().alias("ids"))
    .filter(pl.col("ids") > 1)
    .collect()
)

# Check 2: IDs that are used with more than one name (possible rename).
print("IDs with more than one name:")
print(
    trips.group_by("start_station_id")
    .agg(pl.col("start_station_name").unique().alias("names"))
    .filter(pl.col("names").list.len() > 1)
    .collect()
)

# Check 3: for each name that has two IDs, show the trips per ID per month.
# Month = first 7 characters of started_at, for example 2025-09.
shared_names = (
    trips.group_by("start_station_name")
    .agg(pl.col("start_station_id").n_unique().alias("ids"))
    .filter(pl.col("ids") > 1)
    .collect()
    .get_column("start_station_name")
    .to_list()
)
print("Trips per ID per month for names with two IDs:")
print(
    trips.filter(pl.col("start_station_name").is_in(shared_names))
    .with_columns(pl.col("started_at").str.slice(0, 7).alias("month"))
    .group_by("start_station_name", "start_station_id", "month")
    .agg(pl.len().alias("trips"))
    .sort("start_station_name", "start_station_id", "month")
    .collect()
)
