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


import sys
#sys.modules.pop("src.charts", None)


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
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------
# Header
# ----------------------------
st.title("Sleep Compass")
st.caption("MVP: patterns, rhythm, and one driver relationship.")

# ----------------------------
# Data loading
# ----------------------------
use_real = st.toggle("Use real data (local only)", value=False)
path = "data/sleep_data.csv" if use_real else "data/synthetic.csv"

df = load_sleep_csv(path)

# ----------------------------
# Filters
# ----------------------------
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    only_night = st.checkbox("Only night sleep", value=True)
with col2:
    days = st.selectbox("Range", [7, 30, 90, 365], index=1)
with col3:
    metric = st.selectbox("Heatmap metric", ["minutes_asleep", "overall_score", "efficiency"], index=0)

df_filtered = df.copy()
if only_night and "is_night_sleep" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["is_night_sleep"] == True]

df_recent = df_filtered.tail(days)
last_night = df_filtered.sort_values("start_time").iloc[-1] if len(df_filtered) > 0 else None

# ----------------------------
# Recommendations (placeholder logic)
# ----------------------------
def bedtime_suggestion_hour(df_for_rec):
    """
    Placeholder: median bedtime among top 25% nights by overall_score.
    (You’ll refine later.)
    """
    if df_for_rec is None or len(df_for_rec) == 0:
        return None
    top = df_for_rec[df_for_rec["overall_score"] >= df_for_rec["overall_score"].quantile(0.75)]
    base = top if len(top) >= 3 else df_for_rec
    return float(base["start_hour"].median())

def nap_recommendation(last_row):
    """
    Placeholder: if last night's sleep < 7h => Yes 25 min else No 0 min.
    """
    if last_row is None:
        return (None, None)
    sleep_min = float(last_row["minutes_asleep"])
    if sleep_min < 7 * 60:
        return ("Yes", 25)
    return ("No", 0)

bedtime_hr = bedtime_suggestion_hour(df_recent)
nap_yesno, nap_min = nap_recommendation(last_night)

# ----------------------------
# Display helpers
# ----------------------------
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

# ----------------------------
# Top bar: two cards
# ----------------------------
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

with row1_left:
    #st.markdown("**Efficiency funnel (last night)**")
    st.plotly_chart(funnel_trapezoid(last_night), use_container_width=True)


with row1_right:
    st.markdown("**Sleep timeline (last 7 days)**")
    st.altair_chart(sleep_bar_last_7_days(df_filtered.tail(30)), use_container_width=True)

with row2_left:
    st.markdown("**Total sleep vs target (7.5h)**")
    st.altair_chart(sleep_target_band(df_filtered, target_hours=7.5), use_container_width=True)

with row2_right:
    #st.markdown("**Sleep composition & quality (last 4 nights)**")
    st.plotly_chart(plotly_parallel_coords(df_filtered, n_nights=4), use_container_width=True)

# Mid term section
st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
st.subheader("Mid-term")

m1_left, m1_right = st.columns(2, gap="large")
m2_left, m2_right = st.columns(2, gap="large")

with m1_left:
    #st.markdown("**Calendar heatmap (total sleep per day)**")
    st.altair_chart(calendar_heatmap_month(df_filtered, value_col="minutes_asleep"), use_container_width=True)

with m1_right:
    #st.markdown("**Sleep rhythm (bedtime & wake-up)**")
    st.altair_chart(sleep_rhythm_last_30_days(df_filtered), use_container_width=True)

with m2_left:
    #st.markdown("**Bedtime vs efficiency**")
    st.altair_chart(start_time_vs_efficiency(df_filtered), use_container_width=True)

with m2_right:
    #st.markdown("**Deep sleep % vs bedtime**")
    st.altair_chart(deep_pct_vs_bedtime(df_filtered), use_container_width=True)


# Long term sections
st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")

with left:
    st.markdown("### Health")
    st.altair_chart(rhr_over_time_weekly(df_filtered, months=3), use_container_width=True)
    st.altair_chart(rhr_vs_score(df_filtered, n_days=90), use_container_width=True)

with right:
    st.markdown("### Bad sleep")
    st.altair_chart(bad_sleep_pareto(df_filtered, n_days=90, score_max=75.0), use_container_width=True)
