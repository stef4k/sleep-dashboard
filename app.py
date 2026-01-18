import streamlit as st
from src.data import load_sleep_csv
from src.charts import funnel_trapezoid, sleep_bar_last_7_days, sleep_target_band, plotly_parallel_coords
from src.charts import (
    funnel_trapezoid,
    sleep_bar_last_7_days,
    sleep_target_band,
    plotly_parallel_coords,
    calendar_heatmap_month,
    sleep_rhythm_last_30_days,
    start_time_vs_efficiency,
    deep_pct_vs_bedtime,
)
from src.charts import rhr_over_time_weekly, rhr_vs_score, bad_sleep_pareto
import pandas as pd
import sys

#sys.modules.pop("src.charts", None)
def apply_plotly_dark(fig):
    """Make Plotly charts transparent/dark-friendly for a dark dashboard."""
    # Parallel coords special-case
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",  # outside the plot
        plot_bgcolor="rgba(0,0,0,0)",   # inside the axes
        font=dict(color="rgba(255,255,255,0.88)"),
        margin=dict(l=30, r=20, t=50, b=35),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.12)",
            borderwidth=0,
            font=dict(color="rgba(255,255,255,0.75)"),
        ),
        title=dict(font=dict(color="rgba(255,255,255,0.92)")),
    )

    # If the figure has cartesian axes, soften grids/ticks
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        linecolor="rgba(255,255,255,0.18)",
        tickcolor="rgba(255,255,255,0.25)",
        title_font=dict(color="rgba(255,255,255,0.70)"),
        tickfont=dict(color="rgba(255,255,255,0.70)"),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        linecolor="rgba(255,255,255,0.18)",
        tickcolor="rgba(255,255,255,0.25)",
        title_font=dict(color="rgba(255,255,255,0.70)"),
        tickfont=dict(color="rgba(255,255,255,0.70)"),
    )
    if fig.data and fig.data[0].type == "parcoords":
      fig.update_traces(
          labelfont=dict(color="rgba(255,255,255,0.75)"),
          tickfont=dict(color="rgba(255,255,255,0.60)"),
      )
    return fig

# Page config + global styles
st.set_page_config(page_title="Sleep Compass", layout="wide")

st.markdown(
    """
<style>
/* Tighten top spacing a bit */
.block-container { padding-top: 1.2rem; }

/* Card styling */
.sleep-card {
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(49,51,63,.10);
  border-radius: 18px;
  padding: 18px 18px 14px 18px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

/* Header row */
.sleep-card .hdr {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin-bottom: 10px;
}
.sleep-card .title {
  font-size: 1.05rem;
  font-weight: 750;
  margin:0;
}
.sleep-card .subtitle {
  color: rgba(49,51,63,.65);
  font-size: 0.85rem;
  margin-top: 2px;
}

/* KPI styling */
.sleep-card .kpi {
  display:flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.sleep-card .kpi .big {
  font-size: 2.05rem;
  font-weight: 850;
  letter-spacing: -0.02em;
  line-height: 1;
}
.sleep-card .kpi .sep {
  color: rgba(49,51,63,.22);
  font-size: 1.7rem;
}
.sleep-card.top {
  min-height: 210px;          /* adjust until it looks right */
  display: flex;
  flex-direction: column;
}

/* Make the body area expand */
.sleep-card .body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;     /* vertically center content */
}

/* Mini boxes inside recommendation card */
.grid2 {
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 6px;
  align-items: stretch;
}
.mini {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(49,51,63,.10);
  background: rgba(49,51,63,.02);
  min-height: 110px;
}
.mini .label {
  color: rgba(49,51,63,.65);
  font-size: 0.80rem;
  margin-bottom: 4px;
}
.mini .value {
  font-size: 1.55rem;
  font-weight: 850;
  line-height: 1.05;
}

/* Pills */
.badge {
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size:0.80rem;
  font-weight:650;
  border:1px solid rgba(49,51,63,.12);
  background: rgba(49,51,63,.04);
}
.badge.good { background: rgba(46, 204, 113, .13); border-color: rgba(46, 204, 113, .25); }
.badge.warn { background: rgba(241, 196, 15, .16); border-color: rgba(241, 196, 15, .30); }
.badge.bad  { background: rgba(231, 76, 60,  .13); border-color: rgba(231, 76, 60,  .25); }

/* Plot cards */
.sleep-card { margin-bottom: 14px; }
.sleep-card .body { padding-top: 6px; }

/* Reduce Streamlit default top padding for charts */
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stPlotlyChart"]) {
  margin-top: -6px;
}

/* Make section headers cleaner */
h3 { margin-top: 0.2rem; }
/* Section headers (st.subheader) */
h2 {
  font-size: 5rem;        /* default ~1.5rem */
  font-weight: 800;
  letter-spacing: -0.01em;
  margin-top: 1.8rem;
  margin-bottom: 0.6rem;
}

/* Lighter caption text */
p { color: rgba(49,51,63,.72); }


div[data-testid="stVerticalBlockBorderWrapper"]{
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(49,51,63,.10);
  border-radius: 18px;
  padding: 14px 16px 10px 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  margin-bottom: 14px;
}
/* Streamlit section headers (st.subheader) */
div[data-testid="stHeading"] h1,
div[data-testid="stHeading"] h2,
div[data-testid="stHeading"] h3 {
  font-size: 2.1rem !important;
  font-weight: 850 !important;
  letter-spacing: -0.01em;
  margin-top: 1.6rem !important;
  margin-bottom: 0.6rem !important;
  line-height: 1.15 !important;
}

/* If your st.subheader is not inside stHeading in your version, also apply globally */
h3 {
  font-size: 2.1rem !important;
  font-weight: 850 !important;
}
/* st.subheader renders as markdown, but it sits inside stMarkdown */
div[data-testid="stMarkdown"] h3 {
  font-size: 2.1rem !important;
  font-weight: 850 !important;
  letter-spacing: -0.01em;
  margin-top: 1.6rem !important;
  margin-bottom: 0.6rem !important;
  line-height: 1.15 !important;
}
/* Main page title (st.title) */
div[data-testid="stMarkdown"] h1 {
  font-size: 3.2rem !important;   /* default ~2.5rem */
  font-weight: 900 !important;
  letter-spacing: -0.015em;
  margin-bottom: 0.4rem !important;
  line-height: 1.05 !important;
}
div[data-testid="stMarkdown"] h1 {
  font-size: 3.6rem !important;
}

/* App background */
.main {
  background:
    radial-gradient(
      1200px 600px at 10% 10%,
      rgba(64, 123, 255, 0.08),
      transparent 60%
    ),
    radial-gradient(
      900px 500px at 90% 20%,
      rgba(120, 180, 255, 0.10),
      transparent 55%
    ),
    linear-gradient(
      180deg,
      #f8faff 0%,
      #f4f7fd 45%,
      #eef2fb 100%
    );
}
/* Page background (Streamlit >= 1.30-ish) */
/* === Deep blue dashboard background (Sleep-style) === */
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(
      1200px 700px at 15% 10%,
      rgba(40, 90, 200, 0.25),
      transparent 60%
    ),
    radial-gradient(
      1000px 600px at 85% 20%,
      rgba(90, 140, 255, 0.22),
      transparent 55%
    ),
    linear-gradient(
      180deg,
      #0b1a3a 0%,
      #10265c 35%,
      #173b8f 70%,
      #1e4fb3 100%
    ) !important;
}

/* Let the gradient show through */
[data-testid="stAppViewContainer"] > .main {
  background: transparent !important;
}

[data-testid="stMainBlockContainer"] {
  background: transparent !important;
}

/* Optional: soften sidebar */
section[data-testid="stSidebar"] > div {
  background: rgba(20, 40, 90, 0.55) !important;
  backdrop-filter: blur(12px);
}
/* Make the internal content layer transparent so the background shows */
[data-testid="stAppViewContainer"] > .main {
  background: transparent !important;
}

[data-testid="stMainBlockContainer"] {
  background: transparent !important;
}

/* Optional: sidebar also transparent so it doesn't look like a white slab */
section[data-testid="stSidebar"] > div {
  background: rgba(255,255,255,0.75) !important;
  backdrop-filter: blur(10px);
}
/* =========================
   Dark gradient background (page)
   ========================= */
html, body, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1200px 700px at 20% 10%, rgba(70,130,255,0.28), transparent 55%),
    radial-gradient(900px 600px at 85% 25%, rgba(120,200,255,0.18), transparent 55%),
    radial-gradient(900px 700px at 30% 85%, rgba(90,110,255,0.18), transparent 60%),
    linear-gradient(180deg, #07162f 0%, #071b3a 45%, #05122a 100%) !important;
}

.main .block-container { padding-top: 1.2rem; }

/* =========================
   Global typography on dark bg
   ========================= */
:root{
  --text: rgba(255,255,255,0.92);
  --muted: rgba(255,255,255,0.65);
  --muted2: rgba(255,255,255,0.50);
  --card: rgba(255,255,255,0.07);
  --card2: rgba(255,255,255,0.05);
  --border: rgba(255,255,255,0.12);
  --border2: rgba(255,255,255,0.18);
  --shadow: 0 10px 30px rgba(0,0,0,0.35);
}

div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li,
div[data-testid="stCaptionContainer"] {
  color: var(--muted) !important;
}

div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4 {
  color: var(--text) !important;
}

/* Bigger main title */
div[data-testid="stMarkdown"] h1 {
  font-size: 3.4rem !important;
  font-weight: 900 !important;
  letter-spacing: -0.02em !important;
  margin-bottom: 0.35rem !important;
}

/* Bigger section headers (Short-term / Mid-term) */
div[data-testid="stMarkdown"] h3 {
  font-size: 2.2rem !important;
  font-weight: 900 !important;
  letter-spacing: -0.015em !important;
  margin-top: 1.7rem !important;
  margin-bottom: 0.6rem !important;
}

/* =========================
   “Glass” cards (your HTML cards)
   ========================= */
.sleep-card{
  background: linear-gradient(180deg, var(--card) 0%, var(--card2) 100%) !important;
  border: 1px solid var(--border) !important;
  border-radius: 18px;
  padding: 18px 18px 14px 18px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.sleep-card .title{
  color: var(--text) !important;
  font-weight: 850;
}

.sleep-card .subtitle{
  color: var(--muted2) !important;
}

.sleep-card .kpi .big{
  color: var(--text) !important;
}

/* Mini boxes inside recommendation card */
.mini{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
}
.mini .label{ color: var(--muted2) !important; }
.mini .value{ color: var(--text) !important; }

/* Badges on dark bg */
.badge{
  color: var(--text) !important;
  border: 1px solid rgba(255,255,255,0.16) !important;
  background: rgba(255,255,255,0.06) !important;
}
.badge.good { background: rgba(46, 204, 113, .18) !important; border-color: rgba(46, 204, 113, .35) !important; }
.badge.warn { background: rgba(241, 196, 15, .20) !important; border-color: rgba(241, 196, 15, .40) !important; }
.badge.bad  { background: rgba(231, 76, 60,  .18) !important; border-color: rgba(231, 76, 60,  .38) !important; }

/* =========================
   Streamlit bordered containers (your plot cards)
   ========================= */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background: linear-gradient(180deg, var(--card) 0%, var(--card2) 100%) !important;
  border: 1px solid var(--border) !important;
  border-radius: 18px !important;
  padding: 14px 16px 10px 16px !important;
  box-shadow: var(--shadow) !important;
  backdrop-filter: blur(10px);
}

/* Make headers/captions inside plot cards readable */
div[data-testid="stVerticalBlockBorderWrapper"] h4,
div[data-testid="stVerticalBlockBorderWrapper"] h3,
div[data-testid="stVerticalBlockBorderWrapper"] strong{
  color: var(--text) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] p{
  color: var(--muted2) !important;
}

/* =========================
   Inputs (date picker) on dark bg
   ========================= */
div[data-testid="stDateInput"] label {
  color: var(--muted) !important;
  font-weight: 650 !important;
}

div[data-testid="stDateInput"] input {
  background: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  color: var(--text) !important;
}

/* =========================
   Plot backgrounds (so charts don’t sit on white)
   ========================= */
div[data-testid="stPlotlyChart"] > div {
  background: transparent !important;
}
.vega-embed, .vega-embed canvas, .vega-embed svg {
  background: transparent !important;
}

/* FORCE st.caption text to white-ish */
div[data-testid="stCaptionContainer"] * {
  color: rgba(255,255,255,0.85) !important;
}

/* In some Streamlit versions, caption is rendered as <p> in markdown container */
div[data-testid="stMarkdownContainer"] p {
  color: rgba(255,255,255,0.85) !important;
}

/* =========================
   FIX st.date_input (BaseWeb) white background
   Put this LAST in your CSS
   ========================= */

/* The BaseWeb input wrapper */
div[data-testid="stDateInput"] div[data-baseweb="input"]{
  background-color: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.28) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}

/* Some versions put the background on an inner div */
div[data-testid="stDateInput"] div[data-baseweb="input"] > div{
  background-color: transparent !important;
}

/* The actual text field should be transparent (so wrapper bg shows) + white text */
div[data-testid="stDateInput"] div[data-baseweb="input"] input{
  background: transparent !important;
  color: rgba(255,255,255,0.95) !important;
  caret-color: rgba(255,255,255,0.95) !important;
}

/* Placeholder color */
div[data-testid="stDateInput"] div[data-baseweb="input"] input::placeholder{
  color: rgba(255,255,255,0.55) !important;
}

/* Calendar icon color (SVG) */
div[data-testid="stDateInput"] div[data-baseweb="input"] svg{
  fill: rgba(255,255,255,0.85) !important;
}

/* Focus state */
div[data-testid="stDateInput"] div[data-baseweb="input"]:focus-within{
  border-color: rgba(140,190,255,0.75) !important;
  box-shadow: 0 0 0 3px rgba(120,170,255,0.18) !important;
}

</style>
""",
    unsafe_allow_html=True,
)


# Header
st.title("Sleep Compass")
st.caption("A personal decision-making dashboard that turns your sleep logs into actionable, data-driven guidance—spotting patterns, tracking rhythm, and highlighting the behaviors most linked to better nights.")



# Data loading
path = "data/sleep_data.csv" #if use_real else "data/synthetic.csv"

df = load_sleep_csv(path)

# --- Time travel: pick an "as-of" date and filter everything accordingly ---
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"])

min_date = df["date"].dt.date.min()
max_date = df["date"].dt.date.max()

c1, c2 = st.columns([1, 3])  # adjust ratio as you like
with c1:
    as_of_date = st.date_input(
        "View dashboard as of:",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

# Use end-of-day timestamp so the whole selected day is included
as_of_ts = pd.Timestamp(as_of_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

def window_by_days(dfx: pd.DataFrame, end_ts: pd.Timestamp, days: int) -> pd.DataFrame:
    start_ts = (end_ts.floor("D") - pd.Timedelta(days=days - 1))
    return dfx[(dfx["date"] >= start_ts) & (dfx["date"] <= end_ts)].copy()



# Filter everything up to "as_of"
df_all = df[df["date"] <= as_of_ts].copy()

df_night = df_all.copy()
if "is_night_sleep" in df_night.columns:
    df_night = df_night[df_night["is_night_sleep"] == True]

# Rolling windows ending at as_of
df_7_all   = window_by_days(df_all,   as_of_ts, 7)    # includes naps
df_30_night = window_by_days(df_night, as_of_ts, 30)  # night only
df_90_night = window_by_days(df_night, as_of_ts, 90)  # night only

# Overview night = latest night up to as_of
if len(df_night) > 0 and "start_time" in df_night.columns:
    df_night["start_time"] = pd.to_datetime(df_night["start_time"], errors="coerce")
    df_night = df_night.dropna(subset=["start_time"])
    last_night = df_night.sort_values("start_time").iloc[-1] if len(df_night) > 0 else None
else:
    last_night = df_night.iloc[-1] if len(df_night) > 0 else None


def bedtime_suggestion_hour(last_row, target_h=1 + 15/60, max_shift_min=30):
    """
    Bedtime suggestion:
    - Target is 01:15
    - If last bedtime was later than target, shift earlier by at most 30 minutes
    - If last bedtime was earlier than target, keep it (don't push later)

    Returns: suggested bedtime as float hour in [0, 24)
    """
    if last_row is None:
        return None

    # Get last bedtime as float hour
    if "start_hour" in last_row:
        last_h = float(last_row["start_hour"])
    else:
        st_dt = pd.to_datetime(last_row.get("start_time", None), errors="coerce")
        if pd.isna(st_dt):
            return None
        last_h = st_dt.hour + st_dt.minute / 60.0

    # Wrap into a night-continuous timeline (e.g., 01:15 -> 25.25)
    def wrap_night(h):
        return h if h >= 12 else h + 24

    target_wrapped = wrap_night(target_h)          # 01:15 -> 25.25
    last_wrapped = wrap_night(last_h)

    # If already earlier than target, keep it
    if last_wrapped <= target_wrapped:
        suggested_wrapped = last_wrapped
    else:
        # Shift earlier by max 45 min, but never earlier than target
        suggested_wrapped = max(last_wrapped - (max_shift_min / 60.0), target_wrapped)

    # Convert back to normal 0-24 range
    return float(suggested_wrapped % 24)


def nap_recommendation(last_row):
    """
    Nap rules:
    - Nap only if (total sleep < 7.5h) OR (score < 75)
    - If score < 60 OR sleep < 6h   -> 45 min
    - Elif score < 70 OR sleep < 6.5h -> 35 min
    - Else -> 23 min
    """
    if last_row is None:
        return (None, None)

    sleep_min = float(last_row.get("minutes_asleep", 0))
    score = float(last_row.get("overall_score", 0))

    sleep_h = sleep_min / 60.0

    # Gate: only recommend a nap if you actually need it
    if not (sleep_h < 7.5 or score < 75):
        return ("No", 0)

    # Duration tiers (highest priority first)
    if score < 60 or sleep_h < 6.0:
        return ("Yes", 45)

    if score < 70 or sleep_h < 6.5:
        return ("Yes", 35)

    return ("Yes", 23)

bedtime_hr = bedtime_suggestion_hour(last_night)
nap_yesno, nap_min = nap_recommendation(last_night)

# Display helpers
def score_badge(score: float):
    if score >= 85:
        return ("😄 Great", "good")
    if score >= 75:
        return ("🙂 Good", "good")
    if score >= 65:
        return ("😐 OK", "warn")
    return ("😴 Poor", "bad")

def fmt_hm(minutes):
    m = int(minutes)
    return f"{m//60}h {m%60:02d}m"

def render_html(html: str):
    # Remove blank lines + leading spaces so Markdown never switches out of HTML mode
    html = "\n".join(line.strip() for line in html.splitlines() if line.strip())
    st.markdown(html, unsafe_allow_html=True)
  
def card_open(title: str, subtitle: str = ""):
    sub = f'<div class="subtitle">{subtitle}</div>' if subtitle else ""
    render_html(f"""
    <div class="sleep-card">
      <div class="hdr">
        <div>
          <div class="title">{title}</div>
          {sub}
        </div>
      </div>
      <div class="body">
    """)

def card_close():
    render_html("</div></div>")

def fmt_time_from_hour(h):
    hh = int(h) % 24
    mm = int(round((h - int(h)) * 60)) % 60
    return f"{hh:02d}:{mm:02d}"

# Build Overview strings
if last_night is not None:
    sleep_str = fmt_hm(last_night["minutes_asleep"])
    score_val = float(last_night["overall_score"])
    badge_txt, badge_cls = score_badge(score_val)
    score_str = f"{score_val:.0f}/100"
else:
    sleep_str, score_str, badge_txt, badge_cls = "—", "—", "❔ Unknown", "warn"

# Build Recommendation strings (sanitize)
bedtime_str = fmt_time_from_hour(bedtime_hr) if bedtime_hr is not None else "—"
nap_yesno_safe = nap_yesno if nap_yesno in ("Yes", "No") else "—"
nap_min_safe = int(nap_min) if isinstance(nap_min, (int, float)) else 0
nap_badge_cls = "good" if nap_yesno_safe == "No" else "warn"
nap_detail = f"{nap_min_safe} min" if nap_yesno_safe == "Yes" else "0 min"

# Top bar: two cards
left, right = st.columns([1.15, 1.0], gap="large")
with left:
    render_html(f"""
<div class="sleep-card top">
  <div class="hdr">
    <div>
      <div class="title">Overview</div>
      <div class="subtitle">Last night summary</div>
    </div>
  </div>

  <div class="body">
    <div class="kpi">
      <span class="badge {badge_cls}">{badge_txt}</span>
      <div class="sep">|</div>
      <div class="big">{sleep_str}</div>
      <div class="sep">|</div>
      <div class="big">Score {score_str}</div>
    </div>
  </div>
</div>
""")
with right:
    render_html(f"""
<div class="sleep-card top">
  <div class="hdr">
    <div>
      <div class="title">Recommendations</div>
      <div class="subtitle">For tonight</div>
    </div>
  </div>

  <div class="body">
    <div class="grid2">
      <div class="mini">
        <div class="label">Bedtime suggestion</div>
        <div class="value">{bedtime_str}</div>
      </div>

      <div class="mini">
        <div class="label">Nap recommendation</div>
        <div class="value">
          {nap_yesno_safe}
          <span style="margin:0 8px; color: rgba(49,51,63,.22);">|</span>
          <span class="badge {nap_badge_cls}">⏱ {nap_detail}</span>
        </div>
      </div>
    </div>
  </div>
</div>
""")


st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

# Short term section
st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
st.subheader("Short-term")

row1_left, row1_right = st.columns(2, gap="large")
row2_left, row2_right = st.columns(2, gap="large")

#st.caption("Last night and the past week—quick feedback loops.")

with row1_left:
    with st.container(border=True):
        st.markdown("#### Efficiency funnel")
        st.caption("How last night’s sleep stages add up")

        fig = funnel_trapezoid(last_night)
        fig = apply_plotly_dark(fig)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with row1_right:
    with st.container(border=True):
        st.markdown("#### Sleep timeline (7 days)")
        st.caption("Nights + naps in context")
        st.altair_chart(sleep_bar_last_7_days(df_7_all), use_container_width=True)

with row2_left:
    with st.container(border=True):
        st.markdown("#### Total sleep vs target")
        st.caption("Progress toward 7.5h each night")
        st.altair_chart(sleep_target_band(df_night, target_hours=7.5), use_container_width=True)
with row2_right:
    with st.container(border=True):
        st.markdown("#### Sleep composition & quality")
        st.caption("Stage balance and sleep score (last 4 nights)")

        fig = plotly_parallel_coords(df_night, n_nights=4)
        fig = apply_plotly_dark(fig)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# Mid term section
st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
st.subheader("Mid-term")

m1_left, m1_right = st.columns(2, gap="large")
m2_left, m2_right = st.columns(2, gap="large")

with m1_left:
    with st.container(border=True):
        st.markdown("#### Calendar heatmap")
        st.caption("Daily total sleep across the month")
        st.altair_chart(calendar_heatmap_month(df_30_night, value_col="minutes_asleep"), use_container_width=True)

with m1_right:
    with st.container(border=True):
        st.markdown("#### Sleep rhythm (30 days)")
        st.caption("Bedtime and wake-up consistency + medians")
        st.altair_chart(sleep_rhythm_last_30_days(df_30_night), use_container_width=True)

with m2_left:
    with st.container(border=True):
        st.markdown("#### Bedtime vs sleep efficiency")
        st.caption("How timing relates to quality (trend line is descriptive)")
        st.altair_chart(start_time_vs_efficiency(df_30_night), use_container_width=True)

with m2_right:
    with st.container(border=True):
        st.markdown("#### Deep sleep % vs bedtime")
        st.caption("Timing vs recovery signal (trend line is descriptive)")
        st.altair_chart(deep_pct_vs_bedtime(df_30_night), use_container_width=True)


# Long term sections
st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")

with left:
    st.markdown("### Health")

    with st.container(border=True):
        st.markdown("#### Resting heart rate (weekly)")
        st.caption("3-month trend (weekly averages)")
        st.altair_chart(rhr_over_time_weekly(df_90_night, months=3), use_container_width=True)

    with st.container(border=True):
        st.markdown("#### RHR vs sleep score")
        st.caption("90-day relationship")
        st.altair_chart(rhr_vs_score(df_90_night, n_days=90), use_container_width=True)

with right:
    st.markdown("### Bad sleep")

    with st.container(border=True):
        st.markdown("#### Bad sleep signals (Pareto)")
        st.caption("Triggered signals when score ≤ 75 (last 90 days)")
        st.altair_chart(bad_sleep_pareto(df_90_night, n_days=90, score_max=75.0), use_container_width=True)

        with st.expander("How to read this"):
            st.markdown(
                """
                This **Pareto chart** shows how often *different bad sleep signals* were triggered
                across nights with a sleep score ≤ 75.

                Each bar counts **triggered signals**, not nights.
                A single night can contribute to multiple bars
                (e.g. short sleep *and* late bedtime).

                The cumulative line answers:
                *“Which factors account for most of the problems when sleep is bad?”*

                This helps prioritize behaviors to fix first,
                rather than explaining 100% of bad nights.
                """
            )