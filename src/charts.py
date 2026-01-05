import altair as alt
import pandas as pd
import plotly.graph_objects as go

# Helper to format hours as "Xh YYm"
def fmt_hm_from_hours(h: float) -> str:
    total_min = int(round(h * 60))
    hh = total_min // 60
    mm = total_min % 60
    return f"{hh}h {mm:02d}m"

def fmt_hm_from_minutes(m: float) -> str:
    m = int(round(m))
    hh = m // 60
    mm = m % 60
    return f"{hh}h {mm:02d}m"

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

# Plotly version of funnel chart since altair lacks a specific funnel chart type
def funnel_trapezoid(last_night_row):
    """
    Trapezoid funnel like the example image using Plotly.
    Order ends with Deep sleep.
    """
    if last_night_row is None:
        fig = go.Figure()
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=260)
        return fig

    stages = ["Time in bed", "Time asleep", "Light sleep", "REM sleep", "Deep sleep"]
    mins = [
        float(last_night_row["duration_min"]),
        float(last_night_row["minutes_asleep"]),
        float(last_night_row.get("light_minutes", 0.0)),
        float(last_night_row.get("rem_minutes", 0.0)),
        float(last_night_row.get("deep_minutes", 0.0)),
    ]

    tib = mins[0] if mins[0] > 0 else 1.0
    pcts = [round(v / tib * 100.0, 1) for v in mins]

    # Inside text: "7h 39m (85.0%)"
    text = [f"{fmt_hm_from_minutes(v)} ({p}%)" for v, p in zip(mins, pcts)]

    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=mins,
            orientation="h",
            text=text,
            textposition="inside",
            textinfo="text", 
            hovertemplate="%{y}<br>%{text}<extra></extra>",
        )
    )

    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=35, b=10),
        title=dict(text="Efficiency funnel (last night)", x=0.0, xanchor="left"),
    )
    return fig