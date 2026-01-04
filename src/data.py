import pandas as pd

REQUIRED_COLS = [
    "date","week_day","is_night_sleep",
    "start_time","end_time",
    "duration_min","minutes_asleep","minutes_awake","efficiency",
    "deep_minutes","light_minutes","rem_minutes",
    "overall_score","resting_heart_rate"
]

def load_sleep_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Parse dates/times
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])

    # Ensure bool
    df["is_night_sleep"] = df["is_night_sleep"].astype(bool)

    # Derived features for visuals
    df["start_hour"] = df["start_time"].dt.hour + df["start_time"].dt.minute/60.0
    df["end_hour"] = df["end_time"].dt.hour + df["end_time"].dt.minute/60.0

    # If sleep ends after midnight, end_hour is fine; for plotting rhythms you may want wrap logic later.
    df["deep_pct"] = df["deep_minutes"] / df["minutes_asleep"].replace(0, pd.NA)
    df["rem_pct"]  = df["rem_minutes"]  / df["minutes_asleep"].replace(0, pd.NA)
    df["awake_pct"] = df["minutes_awake"] / df["duration_min"].replace(0, pd.NA)

    # Convenience columns
    df["sleep_hours"] = df["minutes_asleep"] / 60.0
    df["duration_hours"] = df["duration_min"] / 60.0

    # Sort
    df = df.sort_values("start_time").reset_index(drop=True)

    return df
