"""
src/features.py
Task: "Lag features (2-hour rule) plus leakage test" (Anderson) and
      "Join weather to the station-hour table (latest observed weather only)" (Joanna).

Rule (MIN_LAG = 3): to predict hour H we use only data up to the END of hour H-3.
So every count feature uses lags >= 3 hours, and weather is taken from hour H-3.

Self-test (leakage test):  python -m src.features
"""
import numpy as np
import pandas as pd

from src.config import MIN_LAG, HOLIDAYS

# Short recent lags (hours back) and "same hour on previous days" lags.
RECENT_LAGS = [MIN_LAG, MIN_LAG + 1, MIN_LAG + 2]          # H-3, H-4, H-5
DAILY_LAGS = [24, 48, 168]                                 # same hour yesterday, 2 days ago, last week
WEATHER_COLS = ["temp_c", "precip_mm", "wind_kmh"]


def load_station_hour(path) -> pd.DataFrame:
    """Read the table, keep station IDs as text, and add one timestamp column."""
    sh = pd.read_csv(path, dtype={"station_id": str})
    sh["hour_start"] = pd.to_datetime(sh["date"]) + pd.to_timedelta(sh["hour"], unit="h")
    return sh.sort_values(["station_id", "hour_start"]).reset_index(drop=True)


def add_lag_features(sh: pd.DataFrame) -> pd.DataFrame:
    """
    Add lagged counts per station. The table is a complete grid (every station x every hour),
    so shifting by k rows inside a station = going back exactly k hours.
    """
    df = sh.copy()
    df["abs_net_flow"] = df["net_flow"].abs()
    g = df.groupby("station_id", sort=False)
    for k in RECENT_LAGS:
        df[f"dep_lag{k}"] = g["departures"].shift(k)
        df[f"arr_lag{k}"] = g["arrivals"].shift(k)
        df[f"net_lag{k}"] = g["net_flow"].shift(k)
    # Busy-ness over the 6 hours H-3 .. H-8 (sum of trips in and out).
    activity = df["departures"] + df["arrivals"]
    df["_act"] = activity
    df["activity_6h"] = df.groupby("station_id", sort=False)["_act"].transform(
        lambda s: s.shift(MIN_LAG).rolling(6, min_periods=6).sum())
    for k in DAILY_LAGS:
        df[f"net_lag{k}"] = g["net_flow"].shift(k)
        df[f"absnet_lag{k}"] = g["abs_net_flow"].shift(k)
    # Average |net flow| at this same hour over the previous 7 days (lags 24, 48, ..., 168).
    df["absnet_samehour_7d"] = sum(g["abs_net_flow"].shift(24 * d) for d in range(1, 8)) / 7
    df["net_samehour_7d"] = sum(g["net_flow"].shift(24 * d) for d in range(1, 8)) / 7
    return df.drop(columns="_act")


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Hour of day, weekday, weekend and holiday flag: all known in advance."""
    df = df.copy()
    df["weekday"] = df["hour_start"].dt.day_of_week          # 0 = Monday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    df["is_holiday"] = df["hour_start"].dt.date.isin(HOLIDAYS.keys()).astype(int)
    # Smooth hour-of-day encoding (useful for the linear model).
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    return df


def add_weather(df: pd.DataFrame, wx: pd.DataFrame) -> pd.DataFrame:
    """Join the LATEST OBSERVED weather: the reading from hour H-3, never hour H."""
    w = wx.copy()
    w["hour_start"] = pd.to_datetime(w["hour_start"]) + pd.Timedelta(hours=MIN_LAG)   # reading at H-3 is used for H
    w = w.rename(columns={c: f"{c}_lag{MIN_LAG}" for c in WEATHER_COLS})
    return df.merge(w, on="hour_start", how="left")


def feature_lists(df: pd.DataFrame):
    """Return (features without weather, features with weather)."""
    base = [c for c in df.columns if ("_lag" in c and not any(w in c for w in WEATHER_COLS))]
    base += ["activity_6h", "absnet_samehour_7d", "net_samehour_7d",
             "hour", "hour_sin", "hour_cos", "weekday", "is_weekend", "is_holiday"]
    wxf = [f"{c}_lag{MIN_LAG}" for c in WEATHER_COLS]
    return base, base + wxf


def build_features(sh: pd.DataFrame, wx: pd.DataFrame) -> pd.DataFrame:
    return add_weather(add_calendar(add_lag_features(sh)), wx)


# ---------------------------------------------------------------- leakage test
def _toy_grid(n_hours=24 * 9):
    """Tiny made-up table: 2 stations, 9 days of hours, random counts."""
    rng = np.random.default_rng(1)
    hrs = pd.date_range("2025-09-01", periods=n_hours, freq="h")
    rows = []
    for st in ["A", "B"]:
        dep = rng.integers(0, 10, n_hours)
        arr = rng.integers(0, 10, n_hours)
        rows.append(pd.DataFrame({"station_id": st, "hour_start": hrs, "hour": hrs.hour,
                                  "departures": dep, "arrivals": arr, "net_flow": arr - dep}))
    sh = pd.concat(rows, ignore_index=True)
    wx = pd.DataFrame({"hour_start": hrs, "temp_c": rng.normal(20, 3, n_hours),
                       "precip_mm": rng.random(n_hours), "wind_kmh": rng.random(n_hours) * 20})
    return sh, wx


if __name__ == "__main__":
    sh, wx = _toy_grid()
    f1 = build_features(sh, wx)
    _, cols = feature_lists(f1)
    target = pd.Timestamp("2025-09-09 12:00")

    # Leakage test: change EVERY row (trips and weather) from H-2 onwards; features at H must not change.
    sh2, wx2 = sh.copy(), wx.copy()
    late = sh2["hour_start"] >= target - pd.Timedelta(hours=MIN_LAG - 1)
    sh2.loc[late, ["departures", "arrivals"]] += 99
    sh2["net_flow"] = sh2["arrivals"] - sh2["departures"] + np.where(late, 7, 0)
    wx2.loc[wx2["hour_start"] >= target - pd.Timedelta(hours=MIN_LAG - 1), ["temp_c", "precip_mm", "wind_kmh"]] += 50
    f2 = build_features(sh2, wx2)
    a = f1[f1.hour_start == target][cols].reset_index(drop=True)
    b = f2[f2.hour_start == target][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)

    # Known answer: dep_lag3 at H equals departures at H-3 for station A.
    row = f1[(f1.station_id == "A") & (f1.hour_start == target)].iloc[0]
    src = sh[(sh.station_id == "A") & (sh.hour_start == target - pd.Timedelta(hours=3))].iloc[0]
    assert row["dep_lag3"] == src["departures"]
    # And changing H-3 itself DOES change the features (the test is not trivially passing).
    sh3 = sh.copy()
    sh3.loc[sh3["hour_start"] == target - pd.Timedelta(hours=3), "departures"] += 5
    f3 = build_features(sh3, wx)
    assert f3[(f3.station_id == "A") & (f3.hour_start == target)]["dep_lag3"].item() == src["departures"] + 5
    print(f"Leakage test passed: changing all data from H-{MIN_LAG - 1} onwards leaves the {len(cols)} features at H unchanged;")
    print(f"changing hour H-{MIN_LAG} does change them (dep_lag3 known answer = {src['departures']}).")
