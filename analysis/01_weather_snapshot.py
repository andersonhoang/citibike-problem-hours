"""
analysis/01_weather_snapshot.py
Task: "Save hourly weather snapshot from Open-Meteo (NYC, 25 Aug to 26 Oct 2025)" (Joanna).

Downloads ONE citywide hourly weather series for New York City and saves the data PLUS its
provenance (query, parameters, retrieval time, response metadata). Licence: CC BY 4.0, cite Open-Meteo.
Run once from the repository root:  python analysis/01_weather_snapshot.py
The snapshot is then kept: do not re-run it unless the team decides to take a new snapshot.

Time zone: the API is asked for UTC and the times are converted to New York local time here.
With timezone=America/New_York the archive API returns a FIXED GMT-5 clock, but Sep-Oct 2025
is daylight time (GMT-4), so every reading would be labelled one hour too early compared
with the Citi Bike timestamps.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_processed"
WEATHER_CSV = DATA / "weather_hourly.csv"
PROVENANCE_JSON = DATA / "weather_provenance.json"

# Step 1: the exact query (kept in the provenance file).
URL = "https://archive-api.open-meteo.com/v1/archive"
PARAMS = {
    "latitude": 40.78,                # Central Park area; the API uses its nearest grid cell
    "longitude": -73.97,
    "start_date": "2025-08-25",       # August days give the lagged weather for the first study week
    "end_date": "2025-10-27",         # one extra UTC day: 26 Oct 20:00-23:00 EDT falls on 27 Oct UTC
    "hourly": "temperature_2m,precipitation,wind_speed_10m",
    "timezone": "GMT",
}
LOCAL_TZ = "America/New_York"         # same local clock (with daylight saving) as the Citi Bike timestamps
FIRST_HOUR = pd.Timestamp("2025-08-25 00:00")
LAST_HOUR = pd.Timestamp("2025-10-26 23:00")


def to_table(body: dict) -> pd.DataFrame:
    """Turn the API's hourly arrays into a table in New York local time, trimmed to the study window."""
    assert body.get("utc_offset_seconds") == 0, "expected a UTC response"
    h = body["hourly"]
    utc = pd.to_datetime(h["time"]).tz_localize("UTC")
    wx = pd.DataFrame({
        "hour_start": utc.tz_convert(LOCAL_TZ).tz_localize(None),
        "temp_c": h["temperature_2m"],
        "precip_mm": h["precipitation"],
        "wind_kmh": h["wind_speed_10m"],
    })
    keep = (wx["hour_start"] >= FIRST_HOUR) & (wx["hour_start"] <= LAST_HOUR)
    return wx[keep].reset_index(drop=True)


def check(wx: pd.DataFrame) -> None:
    """Known answers: 63 days x 24 hours = 1,512 rows, no gaps, no missing values."""
    assert len(wx) == 63 * 24, len(wx)
    assert wx["hour_start"].iloc[0] == FIRST_HOUR and wx["hour_start"].iloc[-1] == LAST_HOUR
    assert wx["hour_start"].diff().dropna().eq(pd.Timedelta("1h")).all(), "gap in hourly series"
    assert wx.notna().all().all(), "missing weather values"


def main():
    # Step 2: download.
    resp = requests.get(URL, params=PARAMS, timeout=60)
    resp.raise_for_status()
    body = resp.json()

    # Step 3: build the table and check it.
    wx = to_table(body)
    check(wx)

    # Step 4: save the snapshot and its provenance.
    DATA.mkdir(exist_ok=True)
    wx.to_csv(WEATHER_CSV, index=False)
    provenance = {
        "url": URL,
        "params": PARAMS,
        "full_request": resp.url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "response_metadata": {k: v for k, v in body.items() if k != "hourly"},
        "time_handling": f"requested in UTC, converted to {LOCAL_TZ} (EDT, UTC-4, throughout "
                         "25 Aug-26 Oct 2025), trimmed to 25 Aug 00:00-26 Oct 23:00 local",
        "licence": "Open-Meteo data, CC BY 4.0 (https://open-meteo.com/en/licence)",
        "rows": len(wx),
    }
    PROVENANCE_JSON.write_text(json.dumps(provenance, indent=2))
    print(f"Saved {WEATHER_CSV.name}: {len(wx):,} hourly rows, {wx.hour_start.min()} to {wx.hour_start.max()}")
    print(wx.describe().round(2).to_string())


if __name__ == "__main__":
    # Self-test of the time-zone conversion on a made-up response, before any download.
    fake = {"utc_offset_seconds": 0, "hourly": {
        "time": ["2025-09-10T04:00", "2025-09-10T05:00"],
        "temperature_2m": [16.7, 16.6], "precipitation": [0.0, 0.0], "wind_speed_10m": [7.7, 8.8]}}
    t = to_table(fake)
    assert str(t["hour_start"].iloc[0]) == "2025-09-10 00:00:00", t   # 04:00 UTC = 00:00 EDT
    main()
