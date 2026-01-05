import altair as alt
import pandas as pd
import plotly.graph_objects as go
import math


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


def nice_ticks(series: pd.Series, n: int = 4, unit: str = "min"):
    smin = float(series.min())
    smax = float(series.max())
    if smin == smax:
        # Give it a small artificial range so you still see ticks
        pad = 1.0 if unit == "score" else 10.0
        smin, smax = smin - pad, smax + pad

    span = smax - smin

    # Choose a "nice" step
    if unit == "score":
        candidates = [1, 2, 5, 10]
    else:
        candidates = [5, 10, 15, 30, 45, 60, 90, 120]

    # Target step so we get ~n ticks
    raw_step = span / max(n - 1, 1)
    step = min(candidates, key=lambda c: abs(c - raw_step))

    start = math.floor(smin / step) * step
    end = math.ceil(smax / step) * step

    tickvals = list(range(int(start), int(end + step), int(step)))

    # Trim if too many ticks
    if len(tickvals) > 6:
        tickvals = tickvals[::2]

    if unit == "score":
        ticktext = [f"{v}" for v in tickvals]
    else:
        ticktext = [f"{v}m" for v in tickvals]

    return tickvals, ticktext, [start, end]


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

def sleep_bar_last_7_days(df: pd.DataFrame):
    if df is None or len(df) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    d = df.copy()
    d["start_time"] = pd.to_datetime(d["start_time"])
    d["end_time"] = pd.to_datetime(d["end_time"])

    # If is_night_sleep exists, we can label type; otherwise treat all as Night sleep
    if "is_night_sleep" not in d.columns:
        d["is_night_sleep"] = True

    # Define last 7 calendar days ending at latest end_time date (intuitive)
    max_day = d["end_time"].dt.date.max()
    last7 = [(pd.to_datetime(max_day) - pd.Timedelta(days=i)).date() for i in range(6, -1, -1)]  # chronological

    def hour_float(ts):
        return ts.hour + ts.minute / 60.0 + ts.second / 3600.0

    segments = []
    for _, r in d.iterrows():
        start_h = hour_float(r["start_time"])
        end_h = hour_float(r["end_time"])
        start_day = r["start_time"].date()
        end_day = r["end_time"].date()

        sleep_type = "Night sleep" if bool(r["is_night_sleep"]) else "Nap"

        # Split across days if crosses midnight OR dates differ
        if end_h < start_h or end_day != start_day:
            segments.append({"display_date": start_day, "x1": start_h, "x2": 24.0, "type": sleep_type})
            segments.append({"display_date": end_day,   "x1": 0.0,     "x2": end_h, "type": sleep_type})
        else:
            segments.append({"display_date": start_day, "x1": start_h, "x2": end_h, "type": sleep_type})

    seg = pd.DataFrame(segments)

    # Keep only the last 7 days window
    seg = seg[seg["display_date"].isin(last7)]

    # Force y-axis labels for all 7 days
    axis_df = pd.DataFrame({"display_date": last7})
    axis_df["date_str"] = pd.to_datetime(axis_df["display_date"]).dt.strftime("%a %d %b")
    order = list(axis_df["date_str"])

    if len(seg) == 0:
        empty = axis_df.copy()
        empty["x1"] = 0.0
        empty["x2"] = 0.0
        return (
            alt.Chart(empty)
            .mark_bar(opacity=0)
            .encode(
                y=alt.Y("date_str:N", sort=order, title=None),
                x=alt.X("x1:Q", scale=alt.Scale(domain=[0, 24]),
                        axis=alt.Axis(title="Hour of day", tickCount=13)),
                x2="x2:Q",
            )
            .properties(height=260)
        )

    seg["date_str"] = pd.to_datetime(seg["display_date"]).dt.strftime("%a %d %b")

    def hhmm_from_hour(h: float) -> str:
        total_min = int(round(h * 60)) % (24 * 60)
        hh = total_min // 60
        mm = total_min % 60
        return f"{hh:02d}:{mm:02d}"

    seg["start_str"] = seg["x1"].apply(hhmm_from_hour)
    seg["end_str"] = seg["x2"].apply(hhmm_from_hour)

    # Color scheme: Night sleep = blue, Nap = orange
    color_scale = alt.Scale(
        domain=["Night sleep", "Nap"],
        range=["#1f77b4", "#ff7f0e"]  # classic, readable, colorblind-friendlier than random picks
    )

    bars = (
        alt.Chart(seg)
        .mark_bar(cornerRadius=6)
        .encode(
            y=alt.Y("date_str:N", sort=order, title=None),
            x=alt.X("x1:Q", scale=alt.Scale(domain=[0, 24]),
                    axis=alt.Axis(title="Hour of day", tickCount=13)),
            x2="x2:Q",
            color=alt.Color("type:N", scale=color_scale, title="Sleep type"),
            tooltip=[
                alt.Tooltip("type:N", title="Type"),
                alt.Tooltip("date_str:N", title="Day"),
                alt.Tooltip("start_str:N", title="Start"),
                alt.Tooltip("end_str:N", title="End"),
            ],
        )
    )

    # Invisible layer to force y-axis categories
    axis_layer = (
        alt.Chart(axis_df)
        .mark_point(opacity=0)
        .encode(y=alt.Y("date_str:N", sort=order))
    )

    return (bars + axis_layer).properties(height=260)

def sleep_target_band(df: pd.DataFrame, target_hours: float = 7.5):
    """
    Last 7 days total sleep (hours) with:
    - shaded "good zone" from target_hours upward
    - horizontal target rule at target_hours (neutral grey dashed)
    - vertical dashed stems per day from 0 to the sleep value (neutral grey)
    - tooltip shows sleep as "7h 40m"
    - rotated x labels for readability
    - neutral gridlines
    Expects: date, minutes_asleep, is_night_sleep (optional)
    """
    if df is None or len(df) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.date

    # night only if available
    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]

    # aggregate per day (sum in case duplicates exist)
    d = (
        d.groupby("date", as_index=False)["minutes_asleep"]
        .sum()
        .sort_values("date")
        .tail(7)
    )

    if len(d) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No night sleep rows"]})).mark_text(size=16).encode(text="msg:N")

    d["sleep_hours"] = d["minutes_asleep"] / 60.0
    d["date_str"] = pd.to_datetime(d["date"]).dt.strftime("%a %d %b")
    d["zero"] = 0.0  # for vertical stems

    # Format hover as "7h 40m"
    def fmt_hm(mins: float) -> str:
        mins = int(round(mins))
        hh = mins // 60
        mm = mins % 60
        return f"{hh}h {mm:02d}m"

    d["sleep_hm"] = d["minutes_asleep"].apply(fmt_hm)

    order = list(d["date_str"].unique())

    # y max for nice headroom
    y_max = max(float(d["sleep_hours"].max()), target_hours) + 0.75

    zone_df = pd.DataFrame({
        "date_str": order,
        "lower": [target_hours] * len(order),
        "upper": [y_max] * len(order),
    })

    # GOOD ZONE (>= target) - light green
    good_zone = (
        alt.Chart(zone_df)
        .mark_area(opacity=0.18, color="#2ca02c")
        .encode(
            x=alt.X("date_str:N", sort=order, title=None),
            y=alt.Y("lower:Q", title="Total sleep (hours)", scale=alt.Scale(domain=[0, y_max])),
            y2="upper:Q",
        )
    )

    # Horizontal target rule at 7.5h (neutral grey dashed)
    target_rule = (
        alt.Chart(pd.DataFrame({"target": [target_hours]}))
        .mark_rule(strokeDash=[6, 6], strokeWidth=2, color="#197222")
        .encode(y="target:Q")
    )

    # Vertical dashed stems per day from 0 to sleep_hours (neutral grey dashed)
    stems = (
        alt.Chart(d)
        .mark_rule(strokeDash=[4, 4], strokeWidth=1.5, color="#9aa0a6")
        .encode(
            x=alt.X("date_str:N", sort=order, title=None),
            y=alt.Y("zero:Q"),
            y2=alt.Y2("sleep_hours:Q"),
        )
    )

    # Actual sleep line + points
    line = (
        alt.Chart(d)
        .mark_line()
        .encode(
            x=alt.X("date_str:N", sort=order, title=None),
            y=alt.Y("sleep_hours:Q", title="Total sleep (hours)", scale=alt.Scale(domain=[0, y_max])),
            tooltip=[
                alt.Tooltip("date_str:N", title="Day"),
                alt.Tooltip("sleep_hm:N", title="Sleep"),
            ],
        )
    )

    points = (
        alt.Chart(d)
        .mark_circle(size=70)
        .encode(
            x=alt.X("date_str:N", sort=order),
            y="sleep_hours:Q",
            tooltip=[
                alt.Tooltip("date_str:N", title="Day"),
                alt.Tooltip("sleep_hm:N", title="Sleep"),
            ],
        )
    )

    chart = (good_zone + target_rule + stems + line + points).properties(height=260).configure_axis(
        grid=True,
        gridColor="#e6e6e6",
        tickColor="#bdbdbd",
        domainColor="#bdbdbd",
        labelColor="#6b7280",
        titleColor="#6b7280",
    ).configure_axisX(
        labelAngle=-45,
        labelAlign="right",
        labelBaseline="middle"
    ).configure_view(
        strokeWidth=0
    )

    return chart


def plotly_parallel_coords(df: pd.DataFrame, n_nights: int = 4):
    """
    Plotly Parcoords (unnormalized) for last n_nights.
    Adds a Date axis so the hovered line clearly corresponds to a specific night.
    Score axis + colorbar fixed to 50–100.
    """
    if df is None or len(df) == 0:
        return None

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.date
    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]

    agg = (
        d.groupby("date", as_index=False)
        .agg(
            awake=("minutes_awake", "sum"),
            light=("light_minutes", "sum"),
            rem=("rem_minutes", "sum"),
            deep=("deep_minutes", "sum"),
            score=("overall_score", "mean"),
        )
        .sort_values("date")
        .tail(n_nights)
        .reset_index(drop=True)
    )
    if agg.empty:
        return None

    # ----------------------------
    # Add Date axis (for hover / identification)
    # ----------------------------
    agg["date_str"] = pd.to_datetime(agg["date"]).dt.strftime("%a %d %b")
    agg["date_ord"] = list(range(len(agg)))  # 0..n-1

    date_rng = [0, max(0, len(agg) - 1)]
    date_tv = agg["date_ord"].tolist()
    date_tt = agg["date_str"].tolist()

    # ----------------------------
    # Nice ticks helper
    # ----------------------------
    def nice_ticks(series: pd.Series, unit: str, n: int = 3):
        smin = float(series.min())
        smax = float(series.max())
        if smin == smax:
            pad = 1.0 if unit == "score" else 20.0
            smin, smax = smin - pad, smax + pad

        span = smax - smin
        candidates = [1, 2, 5, 10] if unit == "score" else [10, 20, 30, 45, 60, 90, 120]
        raw_step = span / max(n - 1, 1)
        step = min(candidates, key=lambda c: abs(c - raw_step))

        start = math.floor(smin / step) * step
        end = math.ceil(smax / step) * step

        tickvals = list(range(int(start), int(end + step), int(step)))
        while len(tickvals) > 4:
            tickvals = tickvals[::2]

        # Keep tick labels short (units already in axis label)
        ticktext = [f"{v:.0f}" for v in tickvals]
        return tickvals, ticktext, [start, end]

    awake_tv, awake_tt, awake_rng = nice_ticks(agg["awake"], unit="min", n=3)
    light_tv, light_tt, light_rng = nice_ticks(agg["light"], unit="min", n=3)
    rem_tv, rem_tt, rem_rng       = nice_ticks(agg["rem"],   unit="min", n=3)
    deep_tv, deep_tt, deep_rng    = nice_ticks(agg["deep"],  unit="min", n=3)

    # ----------------------------
    # Fixed score axis range (50–100) + fixed color scale (50–100)
    # ----------------------------
    score_rng = [50, 100]
    score_tv  = [50, 60, 70, 80, 90, 100]
    score_tt  = [str(v) for v in score_tv]

    fig = go.Figure(
        go.Parcoords(
            # Add left padding so first axis ("Date"/"Awake") doesn't clip
            domain=dict(x=[0.05, 1.0], y=[0.0, 0.92]),
            line=dict(
                color=agg["score"],
                colorscale="Blues",
                showscale=True,
                cmin=50,
                cmax=100,
                colorbar=dict(title="Sleep Score"),
            ),
            dimensions=[
                # Date axis so each polyline is clearly identifiable
                dict(
                    label="Date",
                    values=agg["date_ord"],
                    range=date_rng,
                    tickvals=date_tv,
                    ticktext=date_tt,
                ),
                dict(
                    label="Awake (min)",
                    values=agg["awake"],
                    range=awake_rng,
                    tickvals=awake_tv,
                    ticktext=awake_tt,
                ),
                dict(
                    label="Light (min)",
                    values=agg["light"],
                    range=light_rng,
                    tickvals=light_tv,
                    ticktext=light_tt,
                ),
                dict(
                    label="REM (min)",
                    values=agg["rem"],
                    range=rem_rng,
                    tickvals=rem_tv,
                    ticktext=rem_tt,
                ),
                dict(
                    label="Deep (min)",
                    values=agg["deep"],
                    range=deep_rng,
                    tickvals=deep_tv,
                    ticktext=deep_tt,
                ),
                dict(
                    label="Score (/100)",
                    values=agg["score"],
                    range=score_rng,
                    tickvals=score_tv,
                    ticktext=score_tt,
                ),
            ],
            labelfont=dict(size=14, color="#111827"),
            tickfont=dict(size=12, color="#111827"),
            rangefont=dict(size=12, color="#111827"),
        )
    )

    fig.update_layout(
        height=520,
        margin=dict(l=95, r=25, t=85, b=25),
        title=dict(
            text=f"Sleep composition & quality (parallel coordinates, last {n_nights} nights)",
            x=0.0,
            xanchor="left",
            y=0.98,
        ),
    )

    return fig
