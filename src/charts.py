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

def efficiency_funnel(last_night_row):
    """
    Funnel for last night:
    Time in bed -> Time asleep -> Light -> REM -> Deep (Deep is last)
    Displayed in HOURS.
    Expects fields:
      duration_min, minutes_asleep, light_minutes, deep_minutes, rem_minutes
    """
    if last_night_row is None:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    tib_min    = float(last_night_row["duration_min"])
    asleep_min = float(last_night_row["minutes_asleep"])
    light_min  = float(last_night_row.get("light_minutes", 0.0))
    rem_min    = float(last_night_row.get("rem_minutes", 0.0))
    deep_min   = float(last_night_row.get("deep_minutes", 0.0))

    # Convert to hours
    tib_h    = tib_min / 60.0
    asleep_h = asleep_min / 60.0
    light_h  = light_min / 60.0
    rem_h    = rem_min / 60.0
    deep_h   = deep_min / 60.0

    order = ["Time in bed", "Time asleep", "Light sleep", "REM sleep", "Deep sleep"]

    data = pd.DataFrame({
        "stage": order,
        "hours": [tib_h, asleep_h, light_h, rem_h, deep_h],
    })

    # Percent relative to time in bed
    data["pct_of_bed"] = (data["hours"] / tib_h * 100.0).round(1)

    # Label in hours + percent
    data["label"] = data.apply( lambda r: f"{fmt_hm_from_hours(r['hours'])} ({r['pct_of_bed']:.1f}%)", axis=1)
    
    bars = (
        alt.Chart(data)
        .mark_bar(cornerRadiusEnd=6)
        .encode(
            y=alt.Y("stage:N", sort=order, title=None),
            x=alt.X("hours:Q", title="Hours"),
            tooltip=["stage:N", alt.Tooltip("hours:Q", format=".2f"), "pct_of_bed:Q"]
        )
    )

    labels = (
        alt.Chart(data)
        .mark_text(align="left", dx=6)
        .encode(
            y=alt.Y("stage:N", sort=order),
            x="hours:Q",
            text="label:N"
        )
    )

    return (bars + labels).properties(height=240)

def centered_funnel(last_night_row):
    if last_night_row is None:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    tib_min    = float(last_night_row["duration_min"])
    asleep_min = float(last_night_row["minutes_asleep"])
    light_min  = float(last_night_row.get("light_minutes", 0.0))
    rem_min    = float(last_night_row.get("rem_minutes", 0.0))
    deep_min   = float(last_night_row.get("deep_minutes", 0.0))

    stages = ["Time in bed", "Time asleep", "Light sleep", "REM sleep", "Deep sleep"]
    mins   = [tib_min, asleep_min, light_min, rem_min, deep_min]

    tib_h = tib_min / 60.0
    hours = [m/60.0 for m in mins]

    def fmt_hm_from_hours(h: float) -> str:
        total_min = int(round(h * 60))
        hh = total_min // 60
        mm = total_min % 60
        return f"{hh}h {mm:02d}m"

    df = pd.DataFrame({"stage": stages, "hours": hours})
    df["pct_of_bed"] = (df["hours"] / tib_h * 100).round(1)
    df["label"] = df.apply(lambda r: f"{fmt_hm_from_hours(r['hours'])} ({r['pct_of_bed']:.1f}%)", axis=1)

    # Geometry for centered funnel
    maxw = df["hours"].max()
    df["x0"] = (maxw - df["hours"]) / 2
    df["x1"] = df["x0"] + df["hours"]
    df["y"]  = range(len(df))  # 0..n-1 from top

    # Build rectangles using rule + thickness via y offsets
    thickness = 0.75
    df["y0"] = df["y"] - thickness/2
    df["y1"] = df["y"] + thickness/2

    # For a clean top-to-bottom order
    df["stage_order"] = pd.Categorical(df["stage"], categories=stages, ordered=True)
    df = df.sort_values("stage_order").reset_index(drop=True)
    df["y"] = range(len(df))
    df["y0"] = df["y"] - thickness/2
    df["y1"] = df["y"] + thickness/2

    base = alt.Chart(df)

    funnel = base.mark_rect(cornerRadius=6).encode(
        x=alt.X("x0:Q", title=None, axis=None),
        x2="x1:Q",
        y=alt.Y("y:Q", axis=alt.Axis(values=list(range(len(df))), labelExpr="datum.value==0 ? 'Time in bed' : datum.value==1 ? 'Time asleep' : datum.value==2 ? 'Light sleep' : datum.value==3 ? 'REM sleep' : 'Deep sleep'", title=None)),
        y2="y1:Q",
        tooltip=["stage:N", alt.Tooltip("hours:Q", format=".2f"), "pct_of_bed:Q"]
    ).properties(height=260)

    # Left labels (stage)
    stage_text = base.mark_text(align="left", dx=-8).encode(
        x=alt.value(0),
        y=alt.Y("y:Q", axis=None),
        text="stage:N"
    )

    # Right labels (time + pct)
    value_text = base.mark_text(align="left", dx=8).encode(
        x="x1:Q",
        y=alt.Y("y:Q", axis=None),
        text="label:N"
    )

    # Set a consistent x-scale with some padding
    return (funnel + value_text).configure_view(strokeWidth=0).properties(title="Efficiency funnel (last night)")



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