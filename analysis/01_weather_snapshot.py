"""
analysis/01_weather_snapshot.py
Task: "Save hourly weather snapshot from Open-Meteo (NYC, 25 Aug to 26 Oct 2025)" (Joanna).
Downloads one citywide hourly series and saves the data PLUS the query, parameters,
retrieval date and response metadata (provenance). Licence: CC BY 4.0 (cite Open-Meteo).
Run:  python analysis/01_weather_snapshot.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import DATA, WEATHER_CSV

# Step 1: the exact query (kept in the provenance file).
URL = "https://archive-api.open-meteo.com/v1/archive"
PARAMS = {
    "latitude": 40.78,
    "longitude": -73.97,
    "start_date": "2025-08-25",
    "end_date": "2025-10-26",
    "hourly": "temperature_2m,precipitation,wind_speed_10m",
    "timezone": "America/New_York",   # same local clock as the Citi Bike timestamps
}


def main():
    # Step 2: download.
    resp = requests.get(URL, params=PARAMS, timeout=60)
    resp.raise_for_status()
    body = resp.json()

    # Step 3: turn the hourly arrays into a table.
    h = body["hourly"]
    wx = pd.DataFrame({
        "hour_start": pd.to_datetime(h["time"]),
        "temp_c": h["temperature_2m"],
        "precip_mm": h["precipitation"],
        "wind_kmh": h["wind_speed_10m"],
    })

    # Step 4: checks with known answers. 63 days x 24 hours = 1,512 rows; no gaps; no missing values.
    assert len(wx) == 63 * 24, len(wx)
    assert wx["hour_start"].diff().dropna().eq(pd.Timedelta("1h")).all(), "gap in hourly series"
    assert wx.notna().all().all(), "missing weather values"

    # Step 5: save the snapshot and its provenance.
    DATA.mkdir(exist_ok=True)
    wx.to_csv(WEATHER_CSV, index=False)
    meta = {k: v for k, v in body.items() if k != "hourly"}
    provenance = {
        "url": URL,
        "params": PARAMS,
        "full_request": resp.url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "response_metadata": meta,
        "licence": "Open-Meteo data, CC BY 4.0 (https://open-meteo.com/en/licence)",
        "rows": len(wx),
    }
    (DATA / "weather_provenance.json").write_text(json.dumps(provenance, indent=2))
    print(f"Saved {WEATHER_CSV.name}: {len(wx):,} hourly rows, {wx.hour_start.min()} to {wx.hour_start.max()}")
    print(wx.describe().round(2).to_string())


if __name__ == "__main__":
    main()
