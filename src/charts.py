import altair as alt
import pandas as pd

def calendar_heatmap(df: pd.DataFrame, value_col: str = "minutes_asleep"):
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["dow"] = d["date"].dt.day_name()
    d["week"] = d["date"].dt.isocalendar().week.astype(int)
    d["year"] = d["date"].dt.year

    # One year view (latest year in data)
    latest_year = d["year"].max()
    d = d[d["year"] == latest_year]

    chart = (
        alt.Chart(d)
        .mark_rect()
        .encode(
            x=alt.X("week:O", title="ISO week"),
            y=alt.Y("dow:O", sort=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"], title="Day"),
            tooltip=["date:T", value_col],
            color=alt.Color(f"{value_col}:Q", title=value_col),
        )
        .properties(height=220)
    )
    return chart

def rhythm_chart(df: pd.DataFrame):
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])

    # start_hour & end_hour expected from your loader
    if "start_hour" not in d.columns:
        d["start_hour"] = d["start_time"].dt.hour + d["start_time"].dt.minute/60.0
    if "end_hour" not in d.columns:
        d["end_hour"] = d["end_time"].dt.hour + d["end_time"].dt.minute/60.0

    start = (
        alt.Chart(d)
        .mark_circle()
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("start_hour:Q", title="Bedtime hour", scale=alt.Scale(domain=[0, 24])),
            tooltip=["date:T", "start_time:T", "start_hour:Q"]
        )
    )

    end = (
        alt.Chart(d)
        .mark_circle()
        .encode(
            x="date:T",
            y=alt.Y("end_hour:Q", title="Wake hour", scale=alt.Scale(domain=[0, 24])),
            tooltip=["date:T", "end_time:T", "end_hour:Q"]
        )
    )

    return (start + end).properties(height=260).resolve_scale(y="independent")

def bedtime_vs_score(df: pd.DataFrame):
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])

    chart = (
        alt.Chart(d)
        .mark_circle()
        .encode(
            x=alt.X("start_hour:Q", title="Bedtime (hour)", scale=alt.Scale(domain=[0, 24])),
            y=alt.Y("overall_score:Q", title="Overall score"),
            tooltip=["date:T", "start_time:T", "overall_score:Q", "efficiency:Q"]
        )
        .properties(height=260)
    )
    return chart
