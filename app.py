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
from contextlib import contextmanager
import base64
from pathlib import Path

def img_to_base64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")


def apply_plotly_dark(fig):
    """Make Plotly charts transparent/dark-friendly for a dark dashboard."""
    is_parcoords = bool(fig.data) and (getattr(fig.data[0], "type", "") == "parcoords")

    # Use larger margins for parcoords (it needs headroom for top labels)
    base_margin = dict(l=95, r=50, t=80, b=25) if is_parcoords else dict(l=30, r=20, t=50, b=35)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="rgba(255,255,255,0.88)"),
        margin=base_margin,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.12)",
            borderwidth=0,
            font=dict(color="rgba(255,255,255,0.75)"),
        ),
        #title=dict(font=dict(color="rgba(255,255,255,0.92)")),
    )

    # Axes styling (only applies if cartesian axes exist; harmless otherwise)
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

    if is_parcoords:
        fig.update_traces(
            labelfont=dict(color="rgba(255,255,255,0.85)", size=13),
            tickfont=dict(color="rgba(255,255,255,0.75)", size=11),
            rangefont=dict(color="rgba(255,255,255,0.75)", size=11),
        )

    return fig

# Page config + global styles
st.set_page_config(page_title="Sleep Compass", layout="wide")

st.markdown(
    """
<style>
/* =========================
   CLEAN DARK THEME (single source of truth)
   ========================= */

:root{
  --text: #ffffff;
  --muted: rgba(255,255,255,0.78);
  --muted2: rgba(255,255,255,0.62);

  --cardTop: rgba(255,255,255,0.085);
  --cardBot: rgba(255,255,255,0.045);

  /* THIS is why your borders were “invisible” */
  --border: rgba(255,255,255,0.30);
  --borderStrong: rgba(255,255,255,0.40);

  --shadow: 0 18px 45px rgba(0,0,0,0.48);
  --radius: 18px;
}

/* Page background */
html, body, [data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 700px at 20% 10%, rgba(70,130,255,0.28), transparent 55%),
    radial-gradient(900px 600px at 85% 25%, rgba(120,200,255,0.18), transparent 55%),
    radial-gradient(900px 700px at 30% 85%, rgba(90,110,255,0.18), transparent 60%),
    linear-gradient(180deg, #07162f 0%, #071b3a 45%, #05122a 100%) !important;
}

/* Make Streamlit inner layers transparent */
[data-testid="stAppViewContainer"] > .main,
[data-testid="stMainBlockContainer"]{
  background: transparent !important;
}

.main .block-container{ padding-top: 1.2rem; }

/* Global text */
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4{
  color: var(--text) !important;
}

div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li{
  color: var(--muted) !important;
}

/* Captions: force white (not gray) */
div[data-testid="stCaptionContainer"] *{
  color: var(--muted) !important;
  opacity: 1 !important;
}

/* =========================
   ONE CARD STYLE (used everywhere)
   ========================= */
.sleep-card{
  background: linear-gradient(180deg, var(--cardTop) 0%, var(--cardBot) 100%) !important;
  border: 1.6px solid var(--borderStrong) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

/* Your internal card text */
.sleep-card .title{ color: var(--text) !important; font-weight: 850; }
.sleep-card .subtitle{ color: var(--muted2) !important; }
.sleep-card .kpi .big{ color: var(--text) !important; }

/* Mini boxes inside recommendation card */
.mini{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.16) !important;
  border-radius: 14px !important;
}
.mini .label{ color: var(--muted2) !important; }
.mini .value{ color: var(--text) !important; }

/* =========================
   APPLY SAME CARD STYLE TO Streamlit containers (border=True)
   ========================= */

/* Most versions */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background: linear-gradient(180deg, var(--cardTop) 0%, var(--cardBot) 100%) !important;
  border: 1.6px solid var(--borderStrong) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 16px 18px 12px 18px !important;
  margin-bottom: 14px !important;
}

/* Some builds use stContainer */
div[data-testid="stContainer"]{
  background: linear-gradient(180deg, var(--cardTop) 0%, var(--cardBot) 100%) !important;
  border: 1.6px solid var(--borderStrong) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

/* Prevent inner layers from painting over the card */
div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stContainer"] > div{
  background: transparent !important;
  border-radius: var(--radius) !important;
}

/* Make headers inside those containers white */
div[data-testid="stVerticalBlockBorderWrapper"] h4,
div[data-testid="stContainer"] h4{
  color: var(--text) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stContainer"] p{
  color: var(--muted) !important;
}

/* =========================
   Date input (BaseWeb) — remove white slab
   ========================= */
div[data-testid="stDateInput"] label{
  color: var(--muted) !important;
  font-weight: 650 !important;
}

/* The wrapper carries the background */
div[data-testid="stDateInput"] div[data-baseweb="input"]{
  background: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.28) !important;
  border-radius: 12px !important;
}
div[data-testid="stDateInput"] div[data-baseweb="input"] input{
  background: transparent !important;
  color: #ffffff !important;
}
div[data-testid="stDateInput"] div[data-baseweb="input"] input::placeholder{
  color: rgba(255,255,255,0.55) !important;
}
div[data-testid="stDateInput"] div[data-baseweb="input"] svg{
  fill: rgba(255,255,255,0.85) !important;
}

/* Plot backgrounds transparent */
div[data-testid="stPlotlyChart"] > div{ background: transparent !important; }
.vega-embed, .vega-embed canvas, .vega-embed svg{ background: transparent !important; }

/* =========================
   RESTORE LAYOUT for the first two custom HTML cards
   (Overview / Recommendations)
   ========================= */

.sleep-card{
  padding: 18px 18px 14px 18px !important;
  margin-bottom: 14px !important;
}

/* Header row */
.sleep-card .hdr{
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
  margin-bottom: 10px !important;
}

.sleep-card .title{
  font-size: 1.05rem !important;
  font-weight: 850 !important;
  margin: 0 !important;
  color: #fff !important;
}

.sleep-card .subtitle{
  font-size: 0.85rem !important;
  margin-top: 2px !important;
  color: rgba(255,255,255,0.65) !important;
}

/* Make the card content area behave */
.sleep-card.top{
  min-height: 210px !important;
  display: flex !important;
  flex-direction: column !important;
}

.sleep-card .body{
  flex: 1 !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  padding-top: 6px !important;
}

/* KPI line */
.sleep-card .kpi{
  display: flex !important;
  align-items: baseline !important;
  gap: 12px !important;
  flex-wrap: wrap !important;
  margin-top: 8px !important;
}

.sleep-card .kpi .big{
  font-size: 2.05rem !important;
  font-weight: 900 !important;
  letter-spacing: -0.02em !important;
  line-height: 1 !important;
  color: #fff !important;
}

.sleep-card .kpi .sep{
  color: rgba(255,255,255,0.22) !important;
  font-size: 1.7rem !important;
}

/* Recommendations inner grid */
.grid2{
  display: grid !important;
  grid-template-columns: 1fr 1fr !important;
  gap: 12px !important;
  margin-top: 6px !important;
  align-items: stretch !important;
}

.mini{
  padding: 12px 14px !important;
  min-height: 110px !important;
}

.mini .label{
  font-size: 0.80rem !important;
  margin-bottom: 4px !important;
  color: rgba(255,255,255,0.60) !important;
}

.mini .value{
  font-size: 1.55rem !important;
  font-weight: 900 !important;
  line-height: 1.05 !important;
  color: #fff !important;
}

/* Badges (pills) */
.badge{
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 4px 10px !important;
  border-radius: 999px !important;
  font-size: 0.80rem !important;
  font-weight: 700 !important;
  color: #fff !important;
  border: 1px solid rgba(255,255,255,0.22) !important;
  background: rgba(255,255,255,0.08) !important;
}



/* =========================
   FORCE crisp white borders on ALL cards
   ========================= */

/* Your top custom cards */
.sleep-card{
  border: 1.5px solid rgba(255,255,255,0.75) !important;
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.22) inset,   /* inner stroke */
    0 18px 45px rgba(0,0,0,0.48) !important;
}

/* Streamlit border=True containers */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stContainer"]{
  border: 1.5px solid rgba(255,255,255,0.75) !important;
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.22) inset,
    0 18px 45px rgba(0,0,0,0.48) !important;
}

/* Make sure nothing inside paints over the edge */
div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stContainer"] > div{
  background: transparent !important;
}

:root{
  --cardBorder: rgba(255,255,255,0.55);   /* visible white */
  --cardBorder2: rgba(255,255,255,0.18);  /* inner stroke */
}

/* ---- FORCE bright borders for Streamlit bordered containers ---- */

/* Wrapper that Streamlit uses for border=True */
div[data-testid="stVerticalBlockBorderWrapper"]{
  border: 2px solid var(--cardBorder) !important;
  border-radius: 18px !important;
  box-shadow:
    0 0 0 1px var(--cardBorder2) inset,
    0 18px 45px rgba(0,0,0,0.45) !important;
}

/* Some builds actually draw the border on a fieldset inside the wrapper */
div[data-testid="stVerticalBlockBorderWrapper"] fieldset{
  border: 2px solid var(--cardBorder) !important;
  border-radius: 18px !important;
}

/* And the legend can create weird dark line effects — neutralize it */
div[data-testid="stVerticalBlockBorderWrapper"] legend{
  color: rgba(255,255,255,0.85) !important;
}

/* Safety net: any direct child that has a border, force it bright */
div[data-testid="stVerticalBlockBorderWrapper"] *[style*="border"]{
  border-color: var(--cardBorder) !important;
}

:root{
  --cardBorder: rgba(255,255,255,0.95);
  --cardBorder2: rgba(255,255,255,0.30);
}

/* Streamlit border=True containers (actual border is often on fieldset) */
div[data-testid="stVerticalBlockBorderWrapper"]{
  border: 2px solid var(--cardBorder) !important;
  border-radius: 18px !important;
  box-shadow:
    0 0 0 1px var(--cardBorder2) inset,
    0 0 0 2px rgba(255,255,255,0.35),
    0 18px 45px rgba(0,0,0,0.45) !important;
}

/* If Streamlit draws border on fieldset, FORCE it */
div[data-testid="stVerticalBlockBorderWrapper"] fieldset{
  border: 2px solid var(--cardBorder) !important;
  border-radius: 18px !important;
}

/* Kill the dark legend seam */
div[data-testid="stVerticalBlockBorderWrapper"] legend{
  color: rgba(255,255,255,0.85) !important;
  padding: 0 8px !important;
}

/* =========================
   RELIABLE WHITE BORDERS (marker + :has)
   Works regardless of Streamlit's internal border implementation
   ========================= */

.card-marker, .section-marker { display: none !important; }

/* Any Streamlit block that CONTAINS our marker becomes a card */
div[data-testid="stVerticalBlock"]:has(.card-marker),
div[data-testid="stVerticalBlock"]:has(.section-marker){
  background: linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.04) 100%) !important;

  border: 2px solid #ffffff !important;           /* PURE WHITE */
  border-radius: 18px !important;

  outline: 1px solid rgba(255,255,255,0.35) !important;
  outline-offset: -2px !important;

  padding: 16px 18px 12px 18px !important;
  margin-bottom: 14px !important;

  box-shadow:
    0 0 0 1px rgba(255,255,255,0.22) inset,
    0 18px 45px rgba(0,0,0,0.45) !important;

  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

/* Keep inner layers transparent so they don't "fill" the border */
div[data-testid="stVerticalBlock"]:has(.card-marker) > div,
div[data-testid="stVerticalBlock"]:has(.section-marker) > div{
  background: transparent !important;
}

/* ===== Header logo inside the top box ===== */
.header-marker { display: none !important; }

div[data-testid="stVerticalBlock"]:has(.header-marker){
  position: relative !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker){
  position: relative !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .sleep-logo-wrap{
  position: absolute !important;
  top: 0px !important;     /* push down */
  right: 18px !important;

  width: 175px !important;
  height: 175px !important;
  border-radius: 50% !important;
  overflow: hidden !important;

  background: rgba(255,255,255,0.03) !important; /* optional subtle */
  box-shadow: 0 10px 18px rgba(0,0,0,0.35) !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) img.sleep-logo{
  position: absolute !important;
  left: 50% !important;
  top: 50% !important;

  width: 170px !important;     /* make the image bigger than circle */
  height: auto !important;

  transform: translate(-50%, -50%) scale(1.05) !important; /* center + fit */
  transform-origin: center !important;

  display: block !important;
}


[data-testid="stElementToolbar"] { 
  display: none !important; 
}

</style>
""",
    unsafe_allow_html=True,
)

LOGO_PATH = "images/logo.png"
logo_b64 = img_to_base64(LOGO_PATH)
# ===== Top header box (title + date input + overview/reco + logo) =====
with st.container():
    # marker so CSS knows "this is the header block"
    st.markdown('<span class="header-marker"></span>', unsafe_allow_html=True)

    # the logo (top-right inside this container)
    st.markdown(
    f"""
    <div class="sleep-logo-wrap">
      <img class="sleep-logo" src="data:image/png;base64,{logo_b64}" />
    </div>
    """,
    unsafe_allow_html=True
    )

# Header
st.title("Sleep Compass")
st.caption("Turn sleep logs into smarter nights - track your rhythm and habits that matter.")



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

from contextlib import contextmanager

@contextmanager
def chart_card(title: str, subtitle: str = ""):
    box = st.container()  # NOT border=True
    with box:
        st.markdown('<span class="card-marker"></span>', unsafe_allow_html=True)
        st.markdown(f"#### {title}")
        if subtitle:
            st.caption(subtitle)
        yield

@contextmanager
def section_card(title: str, subtitle: str = ""):
    box = st.container()  # NOT border=True
    with box:
        st.markdown('<span class="section-marker"></span>', unsafe_allow_html=True)
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)
        yield

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

with section_card("Short-term"):
    row1_left, row1_right = st.columns(2, gap="large")
    row2_left, row2_right = st.columns(2, gap="large")

    with row1_left:
        #with chart_card("Efficiency funnel", "How last night’s sleep stages add up"):
        st.markdown("#### Efficiency funnel")
        st.caption("How last night’s sleep stages add up")
        fig = apply_plotly_dark(funnel_trapezoid(last_night))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with row1_right:
        #with chart_card("Sleep timeline (7 days)", "Nights + naps in context"):
        st.markdown("#### Sleep timeline (7 days)")
        st.caption("Nights + naps in context")
        st.altair_chart(sleep_bar_last_7_days(df_7_all), use_container_width=True, theme=None)

    with row2_left:
        #with chart_card("Total sleep vs target", "Progress toward 7.5h each night"):
        st.markdown("#### Total sleep vs target")
        st.caption("Progress toward 7.5h each night")
        st.altair_chart(sleep_target_band(df_night, target_hours=7.5), use_container_width=True)

    with row2_right:
        #with chart_card("Sleep composition & quality", "Stage balance and sleep score (last 4 nights)"):
        st.markdown("#### Sleep composition & quality")
        st.caption("Stage balance and sleep score (last 4 nights)")
        fig = apply_plotly_dark(plotly_parallel_coords(df_night, n_nights=4))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------
# Mid-term section (FULL)
# ---------------------------
with section_card("Mid-term"):
    m1_left, m1_right = st.columns(2, gap="large")
    m2_left, m2_right = st.columns(2, gap="large")

    with m1_left:
        with st.container(border=True):
            st.markdown("#### Calendar heatmap")
            st.caption("Daily total sleep across the month")
            st.altair_chart(
                calendar_heatmap_month(df_30_night, value_col="minutes_asleep"),
                use_container_width=True
            )

    with m1_right:
        with st.container(border=True):
            st.markdown("#### Sleep rhythm (30 days)")
            st.caption("Bedtime and wake-up consistency + medians")
            st.altair_chart(
                sleep_rhythm_last_30_days(df_30_night),
                use_container_width=True
            )

    with m2_left:
        with st.container(border=True):
            st.markdown("#### Bedtime vs sleep efficiency")
            st.caption("How timing relates to quality")
            st.altair_chart(
                start_time_vs_efficiency(df_30_night),
                use_container_width=True
            )

    with m2_right:
        with st.container(border=True):
            st.markdown("#### Deep sleep % vs bedtime")
            st.caption("Timing vs recovery signal")
            st.altair_chart(
                deep_pct_vs_bedtime(df_30_night),
                use_container_width=True
            )

# ---------------------------
# Long-term sections (FULL: Health + Bad sleep)
# ---------------------------
with section_card("Health & Patterns"):
  left, right = st.columns(2, gap="large")

  with left:
      #with section_card("Health"):
          with st.container(border=True):
              st.markdown("#### Resting heart rate (weekly)")
              st.caption("3-month trend (weekly averages)")
              st.altair_chart(
                  rhr_over_time_weekly(df_90_night, months=3),
                  use_container_width=True
              )

          with st.container(border=True):
              st.markdown("#### RHR vs sleep score")
              st.caption("90-day relationship")
              st.altair_chart(
                  rhr_vs_score(df_90_night, n_days=90),
                  use_container_width=True
              )

  with right:
      #with section_card("Bad sleep"):
          with st.container(border=True):
              st.markdown("#### Bad sleep signals (Pareto)")
              st.caption("Triggered signals when score ≤ 75 (last 90 days)")
              st.altair_chart(
                  bad_sleep_pareto(df_90_night, n_days=90, score_max=75.0),
                  use_container_width=True
              )

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