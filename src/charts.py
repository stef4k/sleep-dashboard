import altair as alt
import pandas as pd
import plotly.graph_objects as go
import math
import numpy as np

CHART_HEIGHT = 420

def _sleep_dark_altair_theme():
    return {
        "config": {
            "background": "transparent",
            "view": {"stroke": "transparent"},
            "axis": {
                "labelColor": "rgba(255,255,255,0.88)",
                "titleColor": "rgba(255,255,255,0.92)",
                "domainColor": "rgba(255,255,255,0.25)",
                "tickColor": "rgba(255,255,255,0.25)",
                "gridColor": "rgba(255,255,255,0.12)",
                "grid": True,
            },
            "legend": {
                "labelColor": "rgba(255,255,255,0.82)",
                "titleColor": "rgba(255,255,255,0.92)",
                "symbolStrokeColor": "rgba(255,255,255,0.35)",
                "symbolFillColor": "rgba(255,255,255,0.35)",
            },
            "title": {
                "color": "rgba(255,255,255,0.92)",
                "fontSize": 14,
                "anchor": "start",
            },
            "header": {  # for facet headers if you ever use them
                "labelColor": "rgba(255,255,255,0.88)",
                "titleColor": "rgba(255,255,255,0.92)",
            },
        }
    }

alt.themes.register("sleep_dark", _sleep_dark_altair_theme)
alt.themes.enable("sleep_dark")


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
        .properties(height=CHART_HEIGHT)
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

    return (start + end).properties(height=CHART_HEIGHT).resolve_scale(y="independent")

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
        .properties(height=CHART_HEIGHT)
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
        fig.update_layout(height=CHART_HEIGHT)
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
        height=CHART_HEIGHT,
        margin=dict(l=20, r=20, t=35, b=10),
        #title=dict(text="Efficiency funnel (last night)", x=0.0, xanchor="left"),
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
            .properties(height=CHART_HEIGHT)
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

    return (bars + axis_layer).properties(height=CHART_HEIGHT)

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

    chart = (good_zone + target_rule + stems + line + points).properties(height=CHART_HEIGHT).configure_axisX(
        labelAngle=-45,
        labelAlign="right",
        labelBaseline="middle"
    ).configure_view(
        strokeWidth=0
    )

    return chart


def plotly_parallel_coords(df: pd.DataFrame, n_nights: int = 4):
    """
    Plotly Parcoords for last n_nights:
    - Fix Date label clipping (range headroom + domain headroom)
    - Remove colorbar
    - Use discrete line colors (stepped colorscale)
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

    # --- Date axis (ordinal -> tick labels)
    agg["date_str"] = pd.to_datetime(agg["date"]).dt.strftime("%a %d %b")
    agg["date_ord"] = np.arange(len(agg), dtype=int)

    n = len(agg)
    date_tv = agg["date_ord"].tolist()
    date_tt = agg["date_str"].tolist()

    # Headroom so first/last date labels aren't clipped
    date_rng = [-0.6, (n - 1) + 0.6] if n > 1 else [-0.6, 0.6]

    # Ticks for minute axes (uses your global nice_ticks(series, n=..., unit=...))
    awake_tv, awake_tt, awake_rng = nice_ticks(agg["awake"], n=3, unit="min")
    light_tv, light_tt, light_rng = nice_ticks(agg["light"], n=3, unit="min")
    rem_tv, rem_tt, rem_rng       = nice_ticks(agg["rem"],   n=3, unit="min")
    deep_tv, deep_tt, deep_rng    = nice_ticks(agg["deep"],  n=3, unit="min")

    # --- Discrete line colors (muted, dark-theme friendly)
    discrete_colors = [
    "rgb(202,148,253)",
    "rgb(231,131,97)",
    "rgb(33,240,182)",
    "rgb(206,240,106)",
    ]

    # Integer id per polyline
    agg["line_id"] = np.arange(n, dtype=int)

    # Build a stepped colorscale so each integer maps to one solid color.
    # IMPORTANT: Parcoords expects a continuous scale; this makes it *look* discrete.
    if n == 1:
        colorscale = [[0.0, discrete_colors[0]], [1.0, discrete_colors[0]]]
        cmin, cmax = 0, 1
    else:
        colorscale = []
        for i in range(n):
            c = discrete_colors[i % len(discrete_colors)]
            a0 = i / (n - 1)
            a1 = (i + 1) / (n - 1)
            # Duplicate stops => hard step (no gradient)
            colorscale.append([a0, c])
            colorscale.append([min(1.0, a1 - 1e-6), c])
        cmin, cmax = 0, n - 1

    fig = go.Figure(
        go.Parcoords(
            # Add headroom so top labels don't clip
            domain=dict(x=[0.06, 1.0], y=[0.02, 0.90]),
            line=dict(
                color=agg["line_id"],
                colorscale=colorscale,
                cmin=cmin,
                cmax=cmax,
                showscale=False,  # remove the palette on the right
            ),
            dimensions=[
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
                    range=[50, 100],
                    tickvals=[50, 60, 70, 80, 90, 100],
                    ticktext=["50", "60", "70", "80", "90", "100"],
                ),
            ],
            labelfont=dict(size=14, color="rgba(255,255,255,0.88)"),
            tickfont=dict(size=12, color="rgba(255,255,255,0.75)"),
            rangefont=dict(size=12, color="rgba(255,255,255,0.75)"),
        )
    )

    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=95, r=25, t=45, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig




def _filter_last_n_days(df: pd.DataFrame, n_days: int) -> pd.DataFrame:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.date
    if len(d) == 0:
        return d
    max_date = pd.to_datetime(d["date"]).max().date()
    min_date = (pd.to_datetime(max_date) - pd.Timedelta(days=n_days - 1)).date()
    return d[(d["date"] >= min_date) & (d["date"] <= max_date)].sort_values("date")

def calendar_heatmap_month(df: pd.DataFrame, value_col: str = "minutes_asleep"):
    if df is None or len(df) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    d = df.copy()

    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]
    if len(d) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No night sleep rows"]})).mark_text(size=16).encode(text="msg:N")

    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"])

    # Make sure the value column is numeric
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce").fillna(0)

    d["date_day"] = d["date"].dt.floor("D")

    daily = (
        d.groupby("date_day", as_index=False)
         .agg(total_min=(value_col, "sum"))
         .rename(columns={"date_day": "day"})
    )
    if daily.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No daily data"]})).mark_text(size=16).encode(text="msg:N")

    latest = daily["day"].max()
    daily = daily[(daily["day"].dt.year == latest.year) & (daily["day"].dt.month == latest.month)].copy()
    if daily.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No rows in latest month"]})).mark_text(size=16).encode(text="msg:N")

    # Convert to hours
    daily["sleep_h"] = daily["total_min"] / 60.0

    # Clamp for a fixed scale (your spec)
    daily["sleep_h_clamped"] = daily["sleep_h"].clip(lower=4.5, upper=9.0)

    # Display hours as hours and minutes
    daily["sleep_hm"] = daily["total_min"].apply(fmt_hm_from_minutes)


    # Discrete bands (fixed thresholds)
    def band(h):
        if h < 6.0:
            return "4.5–6"
        elif h < 7.5:
            return "6–7.5"
        else:
            return "7.5–9"

    daily["band"] = daily["sleep_h_clamped"].apply(band)

    dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    daily["dow"] = daily["day"].dt.day_name()
    daily["dom"] = daily["day"].dt.day.astype(int)

    first = pd.Timestamp(latest.year, latest.month, 1)
    first_monday_index = first.dayofweek  # Mon=0
    daily["wom"] = ((daily["dom"] + first_monday_index - 1) // 7).astype(int)

    # Tooltip formatting
    daily["sleep_h_str"] = daily["sleep_h"].apply(lambda h: f"{h:.1f}h")
    daily["sleep_h_clamped_str"] = daily["sleep_h_clamped"].apply(lambda h: f"{h:.1f}h")

    title = f"Calendar heatmap ({latest.strftime('%B %Y')})"

    # Green / Yellow / Red palette (fixed bins)
    band_domain = ["4.5–6", "6–7.5", "7.5–9"]
    band_range = ["#d73027", "#fee08b", "#1a9850"]  # red, yellow, green

    rect = (
        alt.Chart(daily)
        .mark_rect(cornerRadius=6)
        .encode(
            x=alt.X("wom:O", title=None, axis=alt.Axis(labelAngle=0, ticks=False)),
            y=alt.Y("dow:O", sort=dow_order, title=None),
            color=alt.Color(
                "sleep_h_clamped:Q",
                title="Total sleep (hours)",
                scale=alt.Scale(
                    domain=[4.5, 7, 9.0],
                    range=["#d73027", "#fee08b", "#1a9850"],
                ),
                legend=alt.Legend(
                    values=[4.5, 6, 7.5, 9],
                    labelExpr="datum.value + ' h'"
                ),
            ),
            tooltip=[
                alt.Tooltip("day:T", title="Date"),
                alt.Tooltip("sleep_hm:N", title="Total sleep"),
            ]
        )
        .properties(height=CHART_HEIGHT, title=title)
    )

    text = (
        alt.Chart(daily)
        .mark_text(fontSize=12)
        .encode(
            x="wom:O",
            y=alt.Y("dow:O", sort=dow_order),
            text=alt.Text("dom:O"),
            tooltip=[
                alt.Tooltip("day:T", title="Date"),
                alt.Tooltip("sleep_h_str:N", title="Sleep"),
            ],
        )
    )

    return (rect + text).configure_view(strokeWidth=0)


def sleep_rhythm_last_30_days(df: pd.DataFrame):
    if df is None or len(df) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"])

    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]

    if len(d) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No night sleep rows"]})).mark_text(size=16).encode(text="msg:N")

    # Filter last 30 days based on available max date
    max_day = d["date"].dt.floor("D").max()
    min_day = max_day - pd.Timedelta(days=29)
    d = d[(d["date"].dt.floor("D") >= min_day) & (d["date"].dt.floor("D") <= max_day)].copy()

    # Ensure start/end datetime exist
    if "start_time" in d.columns:
        d["start_dt"] = pd.to_datetime(d["start_time"], errors="coerce")
    else:
        d["start_dt"] = pd.NaT

    if "end_time" in d.columns:
        d["end_dt"] = pd.to_datetime(d["end_time"], errors="coerce")
    else:
        d["end_dt"] = pd.NaT

    d = d.dropna(subset=["start_dt", "end_dt"])
    if len(d) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No valid start/end times"]})).mark_text(size=16).encode(text="msg:N")

    # Hours as floats (so minutes are preserved)
    d["bed_h_raw"] = d["start_dt"].dt.hour + d["start_dt"].dt.minute / 60.0
    d["wake_h_raw"] = d["end_dt"].dt.hour + d["end_dt"].dt.minute / 60.0

    # We want a continuous window from 18:00 → 14:00 next day.
    # So represent everything on [18, 38] where 14:00 becomes 38.
    def wrap_to_night_window(h):
        # Anything earlier than 18:00 belongs to the "next day" part of the window
        return h + 24 if h < 18 else h

    d["bed_h"] = d["bed_h_raw"].apply(wrap_to_night_window)
    d["wake_h"] = d["wake_h_raw"].apply(wrap_to_night_window)

    # Long format for Altair
    long = pd.concat(
        [
            d[["date", "bed_h"]].rename(columns={"bed_h": "hour"}).assign(event="Bedtime"),
            d[["date", "wake_h"]].rename(columns={"wake_h": "hour"}).assign(event="Wake-up"),
        ],
        ignore_index=True,
    )

    # Tooltip: human time (unwrap)
    def hour_to_hm(v: float) -> str:
        v = float(v) % 24
        h = int(v)
        m = int(round((v - h) * 60))
        if m == 60:
            h = (h + 1) % 24
            m = 0
        return f"{h:02d}:{m:02d}"

    long["time_hm"] = long["hour"].apply(hour_to_hm)

    # Axis from 18 → 38 (i.e., 14:00 next day)
    tickvals = list(range(18, 39, 2))

    y_axis = alt.Y(
        "hour:Q",
        title="Hour",
        scale=alt.Scale(domain=[18, 38]),
        axis=alt.Axis(
            values=tickvals,
            labelExpr="format(datum.value % 24, '02') + ':00'",
        ),
    )
    x_axis = alt.X(
        "date:T",
        title=None,
        axis=alt.Axis(
            labelAngle=-30,
            labelOverlap=False,
            labelFlush=False,
            tickCount=8,
        ),
    )

    # Semantically chosen colors
    color_scale = alt.Scale(
        domain=["Bedtime", "Wake-up"],
        range=["#A78BFA", "#F28E2B"],
    )

    # Dotted lines  for median bedtime and wakeuptime
    med_bed = float(np.median(d["bed_h"]))
    med_wake = float(np.median(d["wake_h"]))

    med_df = pd.DataFrame(
        {
            "event": ["Bedtime", "Wake-up"],
            "hour": [med_bed, med_wake],
        }
    )
    med_df["time_hm"] = med_df["hour"].apply(hour_to_hm)
    median_rules = (
        alt.Chart(med_df)
        .mark_rule(strokeDash=[6, 4], strokeWidth=2)
        .encode(
            y="hour:Q",
            color=alt.Color("event:N", title=None, scale=color_scale),
            tooltip=[
                alt.Tooltip("event:N", title="Median"),
                alt.Tooltip("time_hm:N", title="Time"),
            ],
        )
    )

    median_labels = (
        alt.Chart(med_df)
        .mark_text(align="left", dx=6, dy=-6)
        .encode(
            y="hour:Q",
            text=alt.Text("time_hm:N"),
            color=alt.Color("event:N", title=None, scale=color_scale),
        )
    )


    base = alt.Chart(long).encode(
        x=x_axis,
        y=y_axis,
        color=alt.Color("event:N", title=None, scale=color_scale),
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("event:N", title="Event"),
            alt.Tooltip("time_hm:N", title="Time"),
        ],
    )

    chart = (base.mark_line() + base.mark_circle(size=60) + median_rules + median_labels).properties(
        height=CHART_HEIGHT, title="Sleep rhythm (last 30 days, median shown as dotted lines)"
    ).configure_view(strokeWidth=0)
    return chart



def start_time_vs_efficiency(df: pd.DataFrame):
    """
    Scatter: bedtime (wrapped) vs efficiency, last 30 days.
    Color by score for extra context.
    """
    if df is None or len(df) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    d = _filter_last_n_days(df, 30).copy()
    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]
    if len(d) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No night sleep rows"]})).mark_text(size=16).encode(text="msg:N")

    d["date"] = pd.to_datetime(d["date"])
    d["bed_h"] = d["start_hour"].apply(lambda h: h if h >= 21 else h + 24)


    tickvals = list(range(21, 31))  # 21 → 30

    x_axis = alt.X(
        "bed_h:Q",
        title="Bedtime",
        scale=alt.Scale(domain=[21, 30]),
        axis=alt.Axis(
            values=tickvals,
            labelExpr="format(datum.value % 24, '02') + ':00'",
        ),
    )

    pts = (
        alt.Chart(d)
        .mark_circle(size=70, opacity=0.85)
        .encode(
            x=x_axis,
            y=alt.Y("efficiency:Q", title="Efficiency", scale=alt.Scale(domain=[0.6, 1.0])),
            color=alt.Color("overall_score:Q", title="Score"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("start_time:T", title="Start"),
                alt.Tooltip("efficiency:Q", title="Efficiency", format=".2f"),
                alt.Tooltip("overall_score:Q", title="Score"),
            ],
        )
    )

    trend = (
        alt.Chart(d)
        .transform_loess("bed_h", "efficiency", bandwidth=0.6)
        .mark_line()
        .encode(
            x="bed_h:Q",
            y="efficiency:Q",
        )
    )

    return (pts + trend).properties(height=CHART_HEIGHT, title="Bedtime vs efficiency (last 30 days)").configure_view(strokeWidth=0)


def deep_pct_vs_bedtime(df: pd.DataFrame):
    """
    Scatter: bedtime (wrapped) vs deep sleep percentage (night), last 30 days.
    """
    if df is None or len(df) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    d = _filter_last_n_days(df, 30).copy()
    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]
    if len(d) == 0:
        return alt.Chart(pd.DataFrame({"msg": ["No night sleep rows"]})).mark_text(size=16).encode(text="msg:N")

    d["date"] = pd.to_datetime(d["date"])
    d["bed_h"] = d["start_hour"].apply(lambda h: h if h >= 12 else h + 24)
    d["deep_pct_100"] = (d["deep_pct"] * 100).astype(float)

    
    tickvals = list(range(21, 31))  # 21 → 30

    x_axis = alt.X(
        "bed_h:Q",
        title="Bedtime",
        scale=alt.Scale(domain=[21, 30]),
        axis=alt.Axis(
            values=tickvals,
            labelExpr="format(datum.value % 24, '02') + ':00'",
        ),
    )

    pts = (
        alt.Chart(d)
        .mark_circle(size=70, opacity=0.85)
        .encode(
            x=x_axis,
            y=alt.Y("deep_pct_100:Q", title="Deep sleep (%)"),
            color=alt.Color("overall_score:Q", title="Score"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("start_time:T", title="Start"),
                alt.Tooltip("deep_pct_100:Q", title="Deep %", format=".1f"),
                alt.Tooltip("deep_minutes:Q", title="Deep (min)"),
                alt.Tooltip("overall_score:Q", title="Score"),
            ],
        )
    )

    trend = (
        alt.Chart(d)
        .transform_loess("bed_h", "deep_pct_100", bandwidth=0.6)
        .mark_line()
        .encode(
            x="bed_h:Q",
            y="deep_pct_100:Q",
        )
    )

    return (pts + trend).properties(height=CHART_HEIGHT, title="Deep % vs bedtime (last 30 days)").configure_view(strokeWidth=0)


def _last_n_days_night(df: pd.DataFrame, n_days: int = 30) -> pd.DataFrame:
    """Filter to night sleeps and last n days by date."""
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"])

    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]

    if d.empty:
        return d

    max_day = d["date"].dt.floor("D").max()
    min_day = max_day - pd.Timedelta(days=n_days - 1)
    d = d[(d["date"].dt.floor("D") >= min_day) & (d["date"].dt.floor("D") <= max_day)].copy()
    d = d.sort_values("date")
    return d


def rhr_over_time_weekly(df: pd.DataFrame, months: int = 3):
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"])

    if "is_night_sleep" in d.columns:
        d = d[d["is_night_sleep"] == True]

    if d.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    # last N months based on max date in data (not "today")
    max_day = d["date"].dt.floor("D").max()
    min_day = max_day - pd.DateOffset(months=months)
    d = d[d["date"] >= min_day].copy()

    # Week start = Monday (stable + intuitive)
    day = d["date"].dt.floor("D")
    d["week_start"] = day - pd.to_timedelta(day.dt.weekday, unit="D")

    weekly = (
        d.groupby("week_start", as_index=False)
         .agg(
            rhr=("resting_heart_rate", "mean"),
            score=("overall_score", "mean"),
            nights=("week_start", "size"),
         )
         .sort_values("week_start")
    )

    # If resting_heart_rate is missing in your data, fail gracefully
    weekly = weekly.dropna(subset=["rhr"])
    if weekly.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No RHR values available"]})).mark_text(size=16).encode(text="msg:N")

    base = alt.Chart(weekly).encode(
        x=alt.X(
            "week_start:T",
            title=None,
            axis=alt.Axis(labelAngle=-30, tickCount=8),
        ),
        y=alt.Y("rhr:Q", title="Resting heart rate (bpm)"),
        tooltip=[
            alt.Tooltip("week_start:T", title="Week of"),
            alt.Tooltip("rhr:Q", title="Avg RHR", format=".1f"),
            alt.Tooltip("score:Q", title="Avg score", format=".0f"),
            alt.Tooltip("nights:Q", title="# nights"),
        ],
    )

    line = base.mark_line()
    pts = base.mark_circle(size=60)

    return (line + pts).properties(
        height=CHART_HEIGHT,
        title=alt.TitleParams(
            text=f"Resting heart rate (weekly avg, last {months} months)",
            anchor="start",
            fontSize=14,
            dy=0,
        ),
        padding={"left": 10, "right": 10, "top": 35, "bottom": 45},  # <- THIS fixes clipping
    ).configure_view(strokeWidth=0)


def rhr_vs_score(df: pd.DataFrame, n_days: int = 90):
    d = _last_n_days_night(df, n_days)
    if d.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    # Keep needed cols + drop missing
    d = d.dropna(subset=["resting_heart_rate", "overall_score"])

    if d.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No valid rows"]})).mark_text(size=16).encode(text="msg:N")

    pts = (
        alt.Chart(d)
        .mark_circle(size=70, opacity=0.85)
        .encode(
            x=alt.X(
                "overall_score:Q",
                title="Sleep score",
                scale=alt.Scale(domain=[40, 100]),
            ),
            y=alt.Y(
                "resting_heart_rate:Q",
                title="RHR (bpm)",
                scale=alt.Scale(domain=[30, 70]),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("overall_score:Q", title="Score", format=".0f"),
                alt.Tooltip("resting_heart_rate:Q", title="RHR (bpm)", format=".0f"),
            ],
        )
    )

    trend = (
        alt.Chart(d)
        .transform_loess("overall_score", "resting_heart_rate", bandwidth=0.7)
        .mark_line()
        .encode(
            x=alt.X("overall_score:Q", scale=alt.Scale(domain=[40, 100])),
            y=alt.Y("resting_heart_rate:Q", scale=alt.Scale(domain=[30, 70])),
        )
    )

    return (pts + trend).properties(
        height=CHART_HEIGHT,
        title=f"Resting heart rate (RHR) vs sleep score (last {n_days} days)",
        padding={"bottom": 40, "left": 10, "right": 10, "top": 35},
    ).configure_view(strokeWidth=0)


def bad_sleep_pareto(df: pd.DataFrame, n_days: int = 30, score_max: float = 75.0):
    """
    Pareto chart over rule-based 'reason flags' for bad nights (score <= score_max).
    Counts can exceed #nights because one night can trigger multiple reasons.
    """
    d = _last_n_days_night(df, n_days)
    if d.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No data"]})).mark_text(size=16).encode(text="msg:N")

    # Ensure datetime
    d["start_time"] = pd.to_datetime(d["start_time"], errors="coerce")
    d = d.dropna(subset=["start_time", "overall_score"])

    # Aggregate per day (safer)
    daily = (
        d.assign(day=d["date"].dt.floor("D"))
        .groupby("day", as_index=False)
        .agg(
            start_time=("start_time", "min"),
            minutes_asleep=("minutes_asleep", "sum"),
            minutes_awake=("minutes_awake", "sum"),
            duration_min=("duration_min", "sum"),
            efficiency=("efficiency", "mean"),
            deep_pct=("deep_pct", "mean"),
            score=("overall_score", "mean"),
            rhr=("resting_heart_rate", "mean"),
        )
        .sort_values("day")
    )

    # Thresholds based on the 75th percentile over the period
    rhr_thr = float(daily["rhr"].quantile(0.75)) if daily["rhr"].notna().any() else np.nan
    awake_thr = float(daily["minutes_awake"].quantile(0.75)) if daily["minutes_awake"].notna().any() else np.nan

    # Bedtime in wrapped hours (night window), for "late bedtime"
    start_hour = daily["start_time"].dt.hour + daily["start_time"].dt.minute / 60.0
    bedtime_wrapped = start_hour.where(start_hour >= 12, start_hour + 24)  # 01:00 -> 25, 03:00 -> 27

    # Bad nights filter
    bad = daily[daily["score"] <= score_max].copy()
    if bad.empty:
        return alt.Chart(pd.DataFrame({"msg": [f"No nights with score ≤ {score_max}"]})).mark_text(size=16).encode(text="msg:N")

    # Recompute wrapped bedtime for bad subset
    start_hour_bad = bad["start_time"].dt.hour + bad["start_time"].dt.minute / 60.0
    bad["bed_wrapped"] = start_hour_bad.where(start_hour_bad >= 12, start_hour_bad + 24)

    bad["sleep_h"] = bad["minutes_asleep"] / 60.0
    bad["awake_pct"] = bad["minutes_awake"] / bad["duration_min"].replace(0, np.nan)

    # Reason flags (simple + interpretable)
    flags = pd.DataFrame({
        "Late bedtime (≥ 02:00)": bad["bed_wrapped"] >= 26.0, # 2am+
        "Short sleep (< 7h)": bad["sleep_h"] < 7.0,
        "Low efficiency (< 0.85)": bad["efficiency"] < 0.85,
        "Woke up a lot (awake high)": (bad["minutes_awake"] >= awake_thr) | (bad["awake_pct"] >= 0.15),
        "High RHR (relative)": bad["rhr"] >= rhr_thr if not np.isnan(rhr_thr) else False,
        "Low deep sleep (deep% < 12%)": bad["deep_pct"] < 0.12 if "deep_pct" in bad.columns else False,
    }, index=bad.index)
    
    # Build long list of triggered reasons
    long = []
    for idx in flags.index:
        triggered = [c for c in flags.columns if bool(flags.loc[idx, c])]
        if not triggered:
            triggered = ["Other / unclear"]
        for reason in triggered:
            long.append(reason)

    counts = pd.Series(long).value_counts().reset_index()
    counts.columns = ["reason", "count"]
    counts = counts.sort_values("count", ascending=False).reset_index(drop=True)
    counts["cum_count"] = counts["count"].cumsum()
    counts["cum_pct"] = counts["cum_count"] / counts["count"].sum()

    # Pareto: bars (count) + line (cumulative %)
    bars = (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X("reason:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-30, labelOverlap=False,
                                                        labelLimit=1000, labelPadding=10, ticks=True)),
            y=alt.Y("count:Q", title="Reason count"),
            tooltip=[
                alt.Tooltip("reason:N", title="Reason"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("cum_pct:Q", title="Cumulative", format=".0%"),
            ],
        )
    )

    line = (
        alt.Chart(counts)
        .mark_line(point=True)
        .encode(x=alt.X(
            "reason:N",
            sort="-y",
            axis=alt.Axis(
                labelAngle=0,         
                labelFontSize=10,      
                labelLimit=160,        # prevent truncation
                labelPadding=10,       # add breathing room
                title=None
            )
        ),
            y=alt.Y(
                "cum_pct:Q",
                title="Cumulative % of triggered signals",
                axis=alt.Axis(format="%", orient="right"),
                scale=alt.Scale(domain=[0, 1]),
            ),
            tooltip=[
                alt.Tooltip("reason:N", title="Reason"),
                alt.Tooltip("cum_pct:Q", title="Cumulative", format=".0%"),
            ],
        )
    )

    return alt.layer(bars, line).resolve_scale(y="independent").properties(
        height=CHART_HEIGHT,
        title=alt.TitleParams(
            text=f"Bad sleep signals (Pareto of triggered signals, score ≤ {score_max}, last {n_days} days)",
            anchor="start",
            fontSize=14,
        ),
        padding={"top": 35, "bottom": 70, "left": 10, "right": 55},
    ).configure_view(strokeWidth=0)
