import numpy as np
import pandas as pd

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def _fmt_ts(ts: pd.Timestamp) -> str:
    # Match format: 2025-04-16T02:21:30.000
    return ts.strftime("%Y-%m-%dT%H:%M:%S.000")

def generate_sleep_data(
    start_date="2025-04-01",
    end_date="2025-06-30",
    seed=42,
    nap_prob=0.18,                 # probability of a nap per day
    weekend_nap_boost=0.07,         # extra nap probability on Sat/Sun
):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start_date, end_date, freq="D")

    rows = []

    for d in dates:
        week_day = d.strftime("%A")
        is_weekend = week_day in ["Saturday", "Sunday"]

        # --- NIGHT SLEEP (one per day) ---
        # Start time distribution: later on weekends
        if is_weekend:
            start_hour = rng.normal(2.9, 0.6)   # around ~02:54
            duration = rng.normal(520, 45)      # longer on weekends
        else:
            start_hour = rng.normal(2.4, 0.55)  # around ~02:24
            duration = rng.normal(485, 40)

        start_hour = _clamp(start_hour, 0.3, 4.2)
        duration = int(_clamp(duration, 360, 620))  # 6h to ~10h20

        # Efficiency baseline with noise - compute asleep from it
        eff = rng.normal(0.87, 0.04)
        eff = _clamp(eff, 0.75, 0.94)

        minutes_asleep = int(round(duration * eff))
        minutes_asleep = _clamp(minutes_asleep, 240, duration)  # never > duration
        minutes_awake = int(duration - minutes_asleep)
        efficiency = minutes_asleep / duration if duration > 0 else np.nan

        # Sleep stages only for night sleep, must sum to minutes_asleep
        # Deep: ~10–25%, REM: ~15–30%, Light: remainder
        deep_frac = _clamp(rng.normal(0.17, 0.04), 0.10, 0.25)
        rem_frac  = _clamp(rng.normal(0.22, 0.05), 0.15, 0.30)

        deep_minutes = int(round(minutes_asleep * deep_frac))
        rem_minutes  = int(round(minutes_asleep * rem_frac))
        light_minutes = int(minutes_asleep - deep_minutes - rem_minutes)
        # Fix any rounding issues (rare)
        if light_minutes < 0:
            light_minutes = 0
            # take from rem then deep if needed
            overflow = (deep_minutes + rem_minutes) - minutes_asleep
            take = min(overflow, rem_minutes); rem_minutes -= take; overflow -= take
            take = min(overflow, deep_minutes); deep_minutes -= take

        # Resting HR: slightly lower with better sleep, plus noise
        rhr = 60 - 7*(efficiency - 0.85) - 0.01*(minutes_asleep - 420) + rng.normal(0, 1.8)
        rhr = round(_clamp(rhr, 45, 75), 1)

        # Overall score: correlated with efficiency + amount + deep/rem, penalize high rhr
        score = (
            25
            + 55*efficiency
            + 0.03*minutes_asleep
            + 0.04*deep_minutes
            + 0.02*rem_minutes
            - 0.7*max(0, rhr - 56)
            + rng.normal(0, 4.0)
        )
        score = round(_clamp(score, 0, 100), 1)

        # Create timestamp
        start_minute = int(_clamp(rng.normal(15, 20), 0, 59))
        start_second = int(rng.integers(0, 60))
        start_time = pd.Timestamp(d.date()) + pd.Timedelta(hours=float(start_hour)) \
                     + pd.Timedelta(minutes=start_minute, seconds=start_second)
        end_time = start_time + pd.Timedelta(minutes=duration)

        rows.append({
            "date": d.strftime("%Y-%m-%d"),
            "week_day": week_day,
            "is_night_sleep": True,
            "start_time": _fmt_ts(start_time),
            "end_time": _fmt_ts(end_time),
            "duration_min": int(duration),
            "minutes_asleep": int(minutes_asleep),
            "minutes_awake": int(minutes_awake),
            "efficiency": round(efficiency, 2),
            "deep_minutes": int(deep_minutes),
            "light_minutes": int(light_minutes),
            "rem_minutes": int(rem_minutes),
            "overall_score": float(score),
            "resting_heart_rate": float(rhr),
        })

        # OPTIONAL NAP (sometimes) 
        p_nap = nap_prob + (weekend_nap_boost if is_weekend else 0.0)
        if rng.random() < p_nap:
            # Nap start: afternoon/evening; duration: 20–120
            nap_start_hour = rng.normal(16.8, 2.0)
            nap_start_hour = _clamp(nap_start_hour, 12.5, 21.5)

            nap_duration = int(_clamp(rng.normal(55, 20), 20, 120))
            nap_eff = _clamp(rng.normal(0.90, 0.05), 0.75, 0.98)
            nap_asleep = int(round(nap_duration * nap_eff))
            nap_awake = nap_duration - nap_asleep
            nap_efficiency = nap_asleep / nap_duration

            nap_minute = int(rng.integers(0, 60))
            nap_second = int(rng.integers(0, 60))
            nap_start = pd.Timestamp(d.date()) + pd.Timedelta(hours=float(nap_start_hour),
                                                              minutes=nap_minute,
                                                              seconds=nap_second)
            nap_end = nap_start + pd.Timedelta(minutes=nap_duration)

            # Naps have 0 stage minutes + missing overall_score
            rows.append({
                "date": d.strftime("%Y-%m-%d"),
                "week_day": week_day,
                "is_night_sleep": False,
                "start_time": _fmt_ts(nap_start),
                "end_time": _fmt_ts(nap_end),
                "duration_min": int(nap_duration),
                "minutes_asleep": int(nap_asleep),
                "minutes_awake": int(nap_awake),
                "efficiency": round(nap_efficiency, 2),
                "deep_minutes": 0,
                "light_minutes": 0,
                "rem_minutes": 0,
                "overall_score": np.nan,  
                "resting_heart_rate": float(rhr), 
            })

    df = pd.DataFrame(rows)

    # Sort by date then start_time
    df["start_time_sort"] = pd.to_datetime(df["start_time"].str.replace(".000", "", regex=False))
    df = df.sort_values(["date", "start_time_sort"]).drop(columns=["start_time_sort"]).reset_index(drop=True)

    return df


if __name__ == "__main__":
    df = generate_sleep_data("2025-04-16", "2025-10-10", seed=7, nap_prob=0.15)
    print(df.head(12).to_csv(index=False))

    df.to_csv("data/synthetic.csv", index=False)
    print("\nSaved -> data/synthetic.csv")
