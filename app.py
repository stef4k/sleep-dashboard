import streamlit as st
from src.data import load_sleep_csv
from src.charts import funnel_trapezoid, sleep_bar_last_n_days, sleep_target_band, plotly_parallel_coords
from src.charts import (
    funnel_trapezoid,
    sleep_bar_last_n_days,
    sleep_target_band,
    plotly_parallel_coords,
    calendar_heatmap_month,
    sleep_rhythm_last_30_days,
    start_time_vs_efficiency,
    deep_pct_vs_bedtime,
)
from src.charts import rhr_over_time_weekly, rhr_vs_score, bad_sleep_pareto
import pandas as pd
import math
from contextlib import contextmanager
import datetime as dt
import hashlib
import requests
import html
import textwrap
import json
from pathlib import Path
from urllib.parse import quote_plus


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


PHILO_BASE = "https://philosophersapi.com"
PHILO_QUOTES_INDEX = f"{PHILO_BASE}/api/quotes"
PHILO_CACHE_PATH = Path("data/philo_quotes_cache.json")
ALLOWED_SCHOOLS = {
    "Aristotelianism",
    "Cynicism",
    "Platonism",
    "Pre-Socratic",
    "Pythagoreanism",
    "Stoicism",
    "Neo-Platonism",
    "Neoplatonism",
    "Classical Greek",
}


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_quotes_index():
    r = requests.get(PHILO_QUOTES_INDEX, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Unexpected quotes index payload")
    return data


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_quote_detail(qid: str):
    r = requests.get(f"{PHILO_BASE}/api/quotes/{qid}", timeout=10)
    r.raise_for_status()
    return r.json()


def _stable_daily_index(n: int, date_: dt.date, seed: str = "sleep-compass") -> int:
    key = f"{seed}|{date_.isoformat()}".encode("utf-8")
    h = hashlib.sha256(key).hexdigest()
    return int(h[:8], 16) % n


def _get_id(obj: dict):
    return obj.get("id") or obj.get("_id") or obj.get("quoteID") or obj.get("quoteId")


def render_explanation():
    st.title("Design Rationale")
    st.caption("Why the dashboard looks and behaves the way it does")

    intro = (
        "This page explains the main design choices behind the dashboard. "
        "The focus is on making trends easy to scan, comparisons easy to trust, "
        "and decisions easy to act on."
    )
    st.markdown(intro)

    left, right = st.columns(2, gap="large")

    with left:
        with st.container(border=True):
            st.markdown("### Data")
            st.markdown(
                """
                - The dataset contains ~6 months of personal sleep data recorded with a Fitbit Versa 2.
                - It is tabular with 176 rows and 14 columns; each row is a sleep session.
                - The date refers to the day the session ended, to avoid ambiguity.
                - Core attributes include start/end time, duration, minutes asleep/awake, efficiency (0-1), sleep stages (deep, light, REM), overall score (0-100), and resting heart rate.
                - I built the dataset by merging Fitbit export data with the Fitbit Web API sleep logs,
                  then keeping relevant fields and converting time columns to minutes.
                - I parsed the dates and dropped invalid rows to keep comparisons reliable.
                """
            )

        with st.container(border=True):
            st.markdown("### Structure")
            st.markdown(
                """
                - The narrative flows from checking *last night* overview, to recommendations for today, then *short-term*, *mid-term*, and *long-term* sections. I consider each of those a section of the dashboard. The mentioned flow follows the western human tendency to process information from top right to bottom left.
                - Each section keeps a consistent card layout, which makes it easy to navigate and always know in which section we are.
                - I also added time-window filters next to some section headers to reinforce context and easily expand my analysis for a particular time-frame.
                - I added a daily quote because I am into philosophy (especially Ancient Greek philosophy). It is not directly tied to sleep, but it adds a small moment of motivation and reflection that fits the dashboard’s recovery mindset.
                 """
            )

        with st.container(border=True):
            st.markdown("### Visual Representations")
            st.markdown(
                """
                - I use a funnel chart (**Efficiency funnel**) to summarize last night in one glance (sleep-stage composition + efficiency). It is an effective way to visualize and understand quickly how the night was structured and the stages of the night sleep.
                - I use a timeline bar chart (**Sleep timeline**) to compare nights and naps across a short window and spot irregular days quickly. Since I rarely sleep before midnight, I find it more intuitive to have each row start from midnight so that the date of sleep is clear.
                - I use a linechart (**Total sleep vs target**) and a green zone to show whether I hit my 7.5h goal and how far off I am when I miss it in the short-term.
                - I use a parallel coordinate plot (**Sleep composition & quality**) to compare the time spent in each sleep stage without switching between separate charts. By drawing a line on any axis, the plot filter and intensifies the lines that matches that value, which makes it easy to query and identify patterns in the short-term, e.g. night where I was awake the most in the last 30 days.
                - I use a heatmap (**Calendar heatmap**) to show long sequences and month-to-month variation, and to make outliers and gaps obvious. After identifying an outlier night, I can scroll back to the top and use the date input to jump to that night and investigate it in detail.
                - I use a time-series line chart (**Sleep rhythm**) chart to show bedtime/wake-time consistency and medians because regularity matters as much as duration. This plot also helps identify trends in bedtime/wake-time, and outlier nights.
                - I use scatter plots (**Bedtime vs efficiency, bedtime vs deep %**) to test hypotheses about bedtime, e.g. is going to bed early correlated with more deep sleep?, is going to bed late correlated to better efficiency but at what cost?
                - I use a linechart (**Resting heart rate evolution**) and scatterplot (**Resting heart rate vs sleep score**) for resting-heart-rate trends/relationships to connect sleep quality with potential health issues and connect stress related periods with elevated heart-rate.
                - I use a Pareto chart (**Bad sleep signals**) of bad-sleep signals to prioritize the few patterns that explain most low sleep score nights. This helps me to focus and take action on the most impactful factors that lead to bad sleep. Each x-axis category is a simple hypothesis (evaluated on nights with **score ≤ 75**):
                  - **Fixed thresholds:** Late bedtime (≥ 03:00), Short sleep (< 7h), Low efficiency (< 0.80) and Low deep sleep (deep% < 12%).
                  - **Percentile-based ("relative") thresholds:** High RHR (≥ 75th percentile of RHR over the selected window) and "Woke up a lot" (minutes awake ≥ 75th percentile over the selected window).
                """
            )

    with right:
        with st.container(border=True):
            st.markdown("### Page Layout")
            st.markdown(
                """
                - A wide layout supports side-by-side comparison without excessive scrolling.
                - The idea is that I can quickly scan the top of the dashboard for a check-in (which I do everyday). Then, if I am curious and have some time I can scroll down and dive into the sections of mid-term and long-term visuals. Those sections barely change day-to-day, so it does not make sense to constantly evaluate them. Probably, the optimal time to check them is once per week for the mid-term and once per month for the long-term.
                - The header block anchors the page with a daily context and motivation.
                - Cards and captions follow logical order: title, purpose, then chart.
                - The optimal zoom for the browser window is around 80% to balance readability with overview.
                """
            )

        with st.container(border=True):
            st.markdown("### Screen Space Use")
            st.markdown(
                """
                - I set the page to a wide layout so I can place charts in two columns and compare them side by side.
                - I keep the daily controls (dashboard date + weekday/weekend filter) near the top so the context stays obvious.
                - I reserve the top of the page for the daily check-in (overview + recommendations) because I review it every day.
                - I organize the short-term and mid-term visuals in 2x2 grids so I can read a whole section faster.
                - Axis ticks are adapted to the charts avoiding overlapping and easing reading.
                - I use consistent card padding and spacing so the layout feels structured.
                """
            )

        with st.container(border=True):
            st.markdown("### Interaction")
            st.markdown(
                """
                - The date input enables time-travel views so insights can be replayed as of any night.
                - The weekday/weekend filter lets me compare routine days against weekend behavior and see if there are any differences.
                - Each section has its own time window slider (short-term 1-30 days, mid-term 30-90, long-term 90-365), so I can explore ranges independently as I want.
                - Most charts have extra hover information which provides detail without cluttering the main view.
                """
            )

        with st.container(border=True):
            st.markdown("### Meta Data")
            st.markdown(
                """
                - I fetched some philosophical quotes from the [philosophers API](https://philosophersapi.com/), filtering only the schools of philosophy that I am interested. I saved those quotes in a separate JSON file for easy access.
                - I store the quotes locally in `data/philo_quotes_cache.json` so the dashboard still works even if the API is slow or unavailable.
                - I pick the daily quote deterministically from the selected date so it does not shuffle on refresh, and I cache API requests so the header stays fast.                
                - The images of the philosophers are fetched on the fly from the API since I found that the image URLs were quite stable and I wanted to avoid caching too many images locally.
                - I build separate windowed datasets per section (short/mid/long) from the same filtered data so each section stays independent but consistent.
                """
            )

    with st.container(border=True):
        st.markdown("### Color Use")
        st.markdown(
            """
            - I chose a dark, blue-toned gradient background to evoke night.
            - I define a small set of CSS variables for text, muted text, card backgrounds, and borders, and I reuse them across the page for consistency.
            - I keep titles and key numbers high-contrast and I push secondary text to muted grays so the hierarchy stays clear.
            - I use subtle borders and shadows to separate cards without bright outlines.
            - I keep color meanings stable across charts:
              - **Orange** highlights *Wake-up* / waking-related markers.
              - **Purple** highlights *Bedtime* / falling-asleep timing.
              - **Teal** encodes *Naps* (so it does not compete with waking-up orange).
              - **Green** encodes “good” sleep in **Total sleep vs target** (target zone) and the **Calendar heatmap** (higher total sleep).
              - **Red** encodes “bad” sleep in the **Calendar heatmap** (lower total sleep).
            - For some scatter plots, I encode **sleep score** as color using a continuous **dark blue -> white** palette, so higher score reads as darker.
            - In the parallel coordinate plot, I use 7 separable colors that are also distinguishable from the dark blue background.
            - I do not use rainbow palettes to avoid re-learning a new legend in every chart.
            """
        )

def _norm_url(u: str):
    if not u:
        return ""
    u = str(u).strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("//"):
        return "https:" + u
    if not u.startswith("/"):
        u = "/" + u
    return PHILO_BASE + u


def _extract_image_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("url", "src", "path", "image", "imageUrl", "imageURL", "imagePath"):
            if key in value:
                return value.get(key)
    if isinstance(value, list):
        for item in value:
            found = _extract_image_value(item)
            if found:
                return found
    return ""


def _pick_image_from_images(images: dict) -> str:
    if not isinstance(images, dict):
        return ""
    preferred_keys = [
        "full1200x1600",
        "full840x1120",
        "full600x800",
        "ill750x750",
        "ill500x500",
        "ill250x250",
        "thumbnailIll150x150",
        "thumbnailIll50x50",
    ]
    for key in preferred_keys:
        if key in images:
            found = _extract_image_value(images.get(key))
            if found:
                return found
    for _, value in images.items():
        found = _extract_image_value(value)
        if found:
            return found
    return ""


def _pick_image_from_philosopher_images(images: dict) -> str:
    if not isinstance(images, dict):
        return ""
    group_order = [
        ("faceImages", ["face500x500", "face250x250", "face750x750"]),
        ("fullImages", ["full1200x1600", "full840x1120", "full1260x1680", "full600x800", "full420x560"]),
        ("illustrations", ["ill750x750", "ill500x500", "ill250x250"]),
        ("thumbnailIllustrations", ["thumbnailIll150x150", "thumbnailIll100x100", "thumbnailIll50x50"]),
    ]
    for group, keys in group_order:
        group_obj = images.get(group)
        if isinstance(group_obj, dict):
            for key in keys:
                if key in group_obj:
                    found = _extract_image_value(group_obj.get(key))
                    if found:
                        return found
            for _, value in group_obj.items():
                found = _extract_image_value(value)
                if found:
                    return found
    return _pick_image_from_images(images)


def _extract_philosopher_identifiers(detail: dict) -> tuple[str, str]:
    ph = detail.get("philosopher") or detail.get("author") or {}
    name = ph.get("name") or ph.get("fullName") or detail.get("philosopherName") or ""
    ph_id = (
        ph.get("id")
        or ph.get("_id")
        or ph.get("uuid")
        or ph.get("philosopherId")
        or detail.get("philosopherId")
        or detail.get("philosopherID")
        or detail.get("philosopherUuid")
    )
    return str(ph_id).strip() if ph_id else "", str(name).strip()


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def fetch_philosopher_by_id(philosopher_id: str) -> dict:
    r = requests.get(f"{PHILO_BASE}/api/philosophers/{philosopher_id}", timeout=10)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def fetch_philosopher_by_name(name: str) -> dict:
    safe_name = quote_plus(name.strip())
    r = requests.get(f"{PHILO_BASE}/api/philosophers/name/{safe_name}", timeout=10)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, dict) else {}


def get_philosopher_image(philosopher_id: str, name: str) -> str:
    try:
        ph_detail = {}
        if philosopher_id:
            ph_detail = fetch_philosopher_by_id(philosopher_id)
        elif name:
            ph_detail = fetch_philosopher_by_name(name)
        images = ph_detail.get("images") if isinstance(ph_detail, dict) else {}
        img = _pick_image_from_philosopher_images(images or {})
        return _norm_url(img)
    except Exception:
        return ""


def extract_card(detail: dict) -> dict:
    quote = detail.get("quote") or detail.get("text") or detail.get("content") or ""
    quote = str(quote).strip()

    ph = detail.get("philosopher") or detail.get("author") or {}
    name = ph.get("name") or ph.get("fullName") or detail.get("philosopherName") or "Philosophy"
    school = ph.get("school") or detail.get("school") or ""

    quote_date = (
        detail.get("date")
        or detail.get("quoteDate")
        or detail.get("year")
        or detail.get("spokenOn")
        or detail.get("saidOn")
        or detail.get("published")
    )
    if isinstance(quote_date, dict):
        year = quote_date.get("year") or quote_date.get("y")
        month = quote_date.get("month") or quote_date.get("m")
        day = quote_date.get("day") or quote_date.get("d")
        parts = [str(p) for p in (day, month, year) if p]
        quote_date = " ".join(parts)
    quote_date = str(quote_date).strip() if quote_date else ""

    return {
        "name": str(name).strip(),
        "quote": quote,
        "image_url": "",
        "quote_date": quote_date,
        "school": str(school).strip(),
    }


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_allowed_quote_ids() -> list[str]:
    idx = fetch_quotes_index()
    allowed_ids: list[str] = []
    for item in idx:
        qid = _get_id(item)
        if not qid:
            continue
        try:
            detail = fetch_quote_detail(str(qid))
            card = extract_card(detail)
            if card.get("school") in ALLOWED_SCHOOLS:
                allowed_ids.append(str(qid))
        except Exception:
            continue
    return allowed_ids


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_quote_cache_file() -> list[dict]:
    if not PHILO_CACHE_PATH.exists():
        return []
    try:
        data = json.loads(PHILO_CACHE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def get_daily_quote_card(date_: dt.date):
    fallback = {"name": "Daily Anchor", "quote": "Stay consistent.", "image_url": "", "quote_date": ""}
    try:
        cached_quotes = load_quote_cache_file()
        if cached_quotes:
            n = len(cached_quotes)
            pick_i = _stable_daily_index(n, date_)
            if n > 1:
                yesterday_i = _stable_daily_index(n, date_ - dt.timedelta(days=1))
                if pick_i == yesterday_i:
                    pick_i = (pick_i + 1) % n
            card = dict(cached_quotes[pick_i])
            if card.get("quote"):
                card["image_url"] = get_philosopher_image("", card.get("name", ""))
                return card

        allowed_ids = fetch_allowed_quote_ids()
        n = len(allowed_ids)
        if n == 0:
            return fallback
        pick_i = _stable_daily_index(n, date_)
        if n > 1:
            yesterday_i = _stable_daily_index(n, date_ - dt.timedelta(days=1))
            if pick_i == yesterday_i:
                pick_i = (pick_i + 1) % n
        qid = allowed_ids[pick_i]
        detail = fetch_quote_detail(str(qid))
        card = extract_card(detail)
        ph_id, ph_name = _extract_philosopher_identifiers(detail)
        card["image_url"] = get_philosopher_image(ph_id, ph_name or card.get("name", ""))
        if not card["quote"]:
            return fallback
        return card
    except Exception:
        return fallback

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

.main .block-container{ padding-top: 0.4rem; }

/* Global text */
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4{
  color: var(--text) !important;
}

/* Sidebar text: keep readable on light background (override global dark text) */
[data-testid="stSidebar"]{
  color: #0c1326 !important;
}
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] li,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] h4,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] h5,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] h6{
  color: #0c1326 !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span{
  color: #0c1326 !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{
  color: rgba(12,19,38,0.65) !important;
}

/* Title size */
div[data-testid="stMarkdownContainer"] h1{
  font-size: 5rem !important;
  margin-top: 0 !important;
  margin-bottom: 0.35rem !important;
}

div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li{
  color: var(--muted) !important;
}

/* Expander chevron: make arrow visible on dark background */
[data-testid="stExpander"] summary{
  color: #ffffff !important;
}
[data-testid="stExpander"] summary svg{
  color: #ffffff !important;
  stroke: #ffffff !important;
  fill: #ffffff !important;
}
[data-testid="stExpander"] summary svg [stroke]{
  stroke: #ffffff !important;
}
[data-testid="stExpander"] summary svg [fill]{
  fill: #ffffff !important;
}

/* Captions: force white (not gray) */
div[data-testid="stCaptionContainer"] *{
  color: var(--muted) !important;
  opacity: 1 !important;
}

/* Tight caption for specific charts */
.tight-caption{
  margin-top: -6px !important;
  margin-bottom: -8px !important;
  color: var(--muted) !important;
  font-size: 0.88rem !important;
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
   Date input (BaseWeb) – remove white slab
   ========================= */
div[data-testid="stDateInput"] label{
  color: #ffffff !important;
  font-weight: 800 !important;
  font-size: 0.98rem !important;
  opacity: 1 !important;
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

/* =========================
   Radio input (Streamlit) – match date input box style
   ========================= */
div[data-testid="stRadio"] label{
  color: #ffffff !important;
  font-weight: 800 !important;
  font-size: 0.98rem !important;
  opacity: 1 !important;
}
/* Wrap the entire radio group in a "box" */
div[data-testid="stRadio"]:has([role="radiogroup"]) > div{
  background: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.28) !important;
  border-radius: 12px !important;
  padding: 8px 12px !important;
}
div[data-testid="stRadio"] [role="radiogroup"]{
  display: flex !important;
  gap: 14px !important;
}
div[data-testid="stRadio"] span{
  color: #ffffff !important;
}

/* =========================
   Slider input (Streamlit) — yellow accent + boxed like other filters
   ========================= */
div[data-testid="stSlider"] label{
  color: #ffffff !important;
  font-weight: 800 !important;
  font-size: 0.9rem !important;
  text-transform: uppercase !important;
  opacity: 1 !important;
}

div[data-testid="stSlider"]{
  background: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.28) !important;
  border-radius: 12px !important;
  padding: 6px 10px 8px 10px !important;
}

div[data-testid="stSlider"] [data-baseweb="slider"]{
  padding-top: 4px !important;
}

div[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBar"]{
  background: rgba(255,255,255,0.18) !important;
}

div[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBar"] *{
  color: rgba(255,255,255,0.65) !important;
  opacity: 1 !important;
}

/* Ensure min/max edge labels are visible */
div[data-testid="stSlider"] [data-baseweb="slider"]{
  color: rgba(255,255,255,0.65) !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"] span,
div[data-testid="stSlider"] [data-baseweb="slider"] div{
  color: rgba(255,255,255,0.65) !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stThumbValue"]{
  color: #ff4d3a !important;
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

/* ===== Header quote block inside the top box ===== */
.header-marker { display: none !important; }

div[data-testid="stVerticalBlock"]:has(.header-marker){
  position: relative !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker){
  position: relative !important;
  padding-top: 6px !important;   /* bring title closer to top border */
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .motivation-wrap{
  position: absolute !important;
  top: 8px !important;
  right: 18px !important;
  width: 520px !important;
  display: flex !important;
  gap: 16px !important;
  align-items: flex-start !important;
  justify-content: flex-end !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .motivation-img{
  width: 152px !important;
  height: 152px !important;
  border-radius: 50% !important;
  overflow: hidden !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  background: rgba(255,255,255,0.04) !important;
  flex: 0 0 auto !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .motivation-img img{
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .motivation-text{
  max-width: 360px !important;
  text-align: right !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .motivation-name{
  font-weight: 850 !important;
  color: rgba(255,255,255,0.92) !important;
  font-size: 1.2rem !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .motivation-date{
  color: rgba(255,255,255,0.62) !important;
  font-size: 0.9rem !important;
  margin-top: 4px !important;
}

div[data-testid="stVerticalBlock"]:has(.header-marker) .motivation-quote{
  color: rgba(255,255,255,0.78) !important;
  font-size: 1.05rem !important;
  line-height: 1.45 !important;
  margin-top: 8px !important;
  white-space: normal !important;
}


[data-testid="stElementToolbar"] { 
  display: none !important; 
}

</style>
""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "PAGE",
    ["Dashboard", "Explanation"],
    index=0,
)
if page == "Explanation":
    render_explanation()
    st.stop()

header_slot = st.empty()

# Header
st.title("The Art of Sleeping")
st.caption("My nightly scorecard for better recovery and performance")



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
        "DASHBOARD DATE",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )
with c2:
    day_filter = st.radio(
        "FILTER DAYS",
        ["All", "Weekdays", "Weekends"],
        horizontal=True,
    )

# ===== Top header box (title + date input + overview/reco + quote) =====
with header_slot.container():
    # marker so CSS knows "this is the header block"
    st.markdown('<span class="header-marker"></span>', unsafe_allow_html=True)

    card = get_daily_quote_card(as_of_date)
    safe_name = html.escape(card["name"])
    safe_quote = html.escape(card["quote"])
    safe_date = html.escape(card.get("quote_date", ""))
    img_html = ""
    if card["image_url"]:
        img_html = f'<div class="motivation-img"><img src="{card["image_url"]}" /></div>'
    else:
        initials = "".join([p[0] for p in safe_name.split()[:2]]).upper()
        img_html = (
            '<div class="motivation-img" '
            'style="display:flex;align-items:center;justify-content:center;'
            'color:rgba(255,255,255,0.75);font-weight:800;">'
            f"{initials}</div>"
        )

    date_label = safe_date
    date_html = f'<div class="motivation-date">{date_label}</div>' if date_label else ""
    header_html = (
        f'<div class="motivation-wrap">{img_html}'
        f'<div class="motivation-text">'
        f'<div class="motivation-name">{safe_name}</div>'
        f'{date_html}'
        f'<div class="motivation-quote">&ldquo;{safe_quote}&rdquo;</div>'
        f"</div></div>"
    )
    st.markdown(header_html, unsafe_allow_html=True)

# Use end-of-day timestamp so the whole selected day is included
as_of_ts = pd.Timestamp(as_of_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

def window_by_days(dfx: pd.DataFrame, end_ts: pd.Timestamp, days: int) -> pd.DataFrame:
    start_ts = (end_ts.floor("D") - pd.Timedelta(days=days - 1))
    return dfx[(dfx["date"] >= start_ts) & (dfx["date"] <= end_ts)].copy()

def apply_daytype_filter(dfx: pd.DataFrame, mode: str) -> pd.DataFrame:
    if dfx is None or len(dfx) == 0 or mode == "All":
        return dfx
    dow = dfx["date"].dt.dayofweek
    if mode == "Weekdays":
        return dfx[dow < 5].copy()
    return dfx[dow >= 5].copy()


# Filter everything up to "as_of"
df_all_unfiltered = df[df["date"] <= as_of_ts].copy()
df_all = apply_daytype_filter(df_all_unfiltered, day_filter)

# Night sleeps for plots (respects day filter)
df_night = df_all.copy()
if "is_night_sleep" in df_night.columns:
    df_night = df_night[df_night["is_night_sleep"] == True]

# Night sleeps for overview/recommendations/funnel (ignores day filter)
df_night_all = df_all_unfiltered.copy()
if "is_night_sleep" in df_night_all.columns:
    df_night_all = df_night_all[df_night_all["is_night_sleep"] == True]

# Rolling windows ending at as_of
df_30_night = window_by_days(df_night, as_of_ts, 30)  # night only
df_90_night = window_by_days(df_night, as_of_ts, 90)  # night only

# Overview night = latest night up to as_of
if len(df_night_all) > 0 and "start_time" in df_night_all.columns:
    df_night_all["start_time"] = pd.to_datetime(df_night_all["start_time"], errors="coerce")
    df_night_all = df_night_all.dropna(subset=["start_time"])
    last_night = df_night_all.sort_values("start_time").iloc[-1] if len(df_night_all) > 0 else None
else:
    last_night = df_night_all.iloc[-1] if len(df_night_all) > 0 else None


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

with st.container():
    st.markdown('<span class="section-marker"></span>', unsafe_allow_html=True)
    short_term_header_left, short_term_header_right = st.columns([3, 1], gap="large")
    with short_term_header_left:
        st.markdown("## Short-term")
    with short_term_header_right:
        short_term_days = st.slider(
            "SHORT-TERM DAYS",
            min_value=1,
            max_value=30,
            value=7,
        )

    df_short_all = window_by_days(df_all, as_of_ts, short_term_days)
    df_short_night = window_by_days(df_night, as_of_ts, short_term_days)

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
        st.markdown(f"#### Sleep timeline ")
        st.caption(f"Nights + naps in context ({short_term_days} days)")
        st.altair_chart(
            sleep_bar_last_n_days(df_short_all, n_days=short_term_days),
            use_container_width=True,
            theme=None,
        )

    with row2_left:
        #with chart_card("Total sleep vs target", "Progress toward 7.5h each night"):
        st.markdown("#### Total sleep vs target")
        st.caption("Progress toward 7.5h target each night")
        st.altair_chart(
            sleep_target_band(df_short_night, target_hours=7.5, n_days=short_term_days),
            use_container_width=True,
        )

    with row2_right:
        #with chart_card("Sleep composition & quality", "Stage balance and sleep score (last 4 nights)"):
        st.markdown("#### Sleep composition & quality")
        st.caption(f"Stage balance and sleep score using parallel coordinates last {short_term_days} nights")
        fig = apply_plotly_dark(plotly_parallel_coords(df_short_night, n_nights=short_term_days))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------
# Mid-term section (FULL)
# ---------------------------
with st.container():
    st.markdown('<span class="section-marker"></span>', unsafe_allow_html=True)
    mid_term_header_left, mid_term_header_right = st.columns([3, 1], gap="large")
    with mid_term_header_left:
        st.markdown("## Mid-term")
    with mid_term_header_right:
        mid_term_days = st.slider(
            "MID-TERM DAYS",
            min_value=30,
            max_value=90,
            value=30,
        )

    df_mid_night = window_by_days(df_night, as_of_ts, mid_term_days)
    calendar_anchor = df_mid_night["date"].max() if len(df_mid_night) > 0 else None

    m1_left, m1_right = st.columns(2, gap="large")
    m2_left, m2_right = st.columns(2, gap="large")

    with m1_left:
        with st.container(border=True):
            st.markdown("#### Calendar heatmap")
            st.caption("Daily total sleep across months")
            st.altair_chart(
                calendar_heatmap_month(
                    df_night,
                    value_col="minutes_asleep",
                    anchor_date=calendar_anchor,
                    n_days=mid_term_days,
                ),
                use_container_width=True
            )

    with m1_right:
        with st.container(border=True):
            st.markdown(f"#### Sleep rhythm ")
            st.caption(f"Bedtime and wake-up consistency + medians ({mid_term_days} days)")
            st.altair_chart(
                sleep_rhythm_last_30_days(df_mid_night, n_days=mid_term_days),
                use_container_width=True
            )

    with m2_left:
        with st.container(border=True):
            st.markdown("#### Bedtime vs sleep efficiency")
            st.caption("How timing relates to quality")
            st.altair_chart(
                start_time_vs_efficiency(df_mid_night, n_days=mid_term_days),
                use_container_width=True
            )

    with m2_right:
        with st.container(border=True):
            st.markdown("#### Bedtime vs deep sleep %")
            st.caption("Timing vs recovery signal")
            st.altair_chart(
                deep_pct_vs_bedtime(df_mid_night, n_days=mid_term_days),
                use_container_width=True
            )

# ---------------------------
# Long-term sections (FULL: Health + Bad sleep)
# ---------------------------
with st.container():
    st.markdown('<span class="section-marker"></span>', unsafe_allow_html=True)
    health_header_left, health_header_right = st.columns([3, 1], gap="large")
    with health_header_left:
        st.markdown("## Health & Patterns")
    with health_header_right:
        health_days = st.slider(
            "HEALTH & PATTERNS DAYS",
            min_value=90,
            max_value=365,
            value=180,
        )

    df_health_night = window_by_days(df_night, as_of_ts, health_days)
    health_months = max(1, int(math.ceil(health_days / 30)))

    left, right = st.columns(2, gap="large")

    with left:
        with st.container(border=True):
            st.markdown("#### Resting heart rate evolution")
            st.caption(f"{health_months}-month trend (weekly averages)")
            st.altair_chart(
                rhr_over_time_weekly(df_health_night, months=health_months),
                use_container_width=True
            )

        with st.container(border=True):
            st.markdown("#### Resting heart rate vs sleep score")
            st.caption(f"{health_days}-day relationship")
            st.altair_chart(
                rhr_vs_score(df_health_night, n_days=health_days),
                use_container_width=True
            )

    with right:
        with st.container(border=True):
            st.markdown("#### Bad sleep signals - Pareto")
            pareto_daily = df_health_night.copy()
            pareto_daily["date"] = pd.to_datetime(pareto_daily["date"], errors="coerce")
            pareto_daily = pareto_daily.dropna(subset=["date", "overall_score"])
            pareto_daily = (
                pareto_daily.assign(day=pareto_daily["date"].dt.floor("D"))
                .groupby("day", as_index=False)
                .agg(score=("overall_score", "mean"))
            )
            total_nights = int(len(pareto_daily))
            bad_nights = int((pareto_daily["score"] <= 75.0).sum()) if total_nights else 0
            st.caption(
                f"Triggered signals when score ≤ 75. In detail, {bad_nights} bad nights out of the {total_nights} recorded nights in the last {health_days} days"
            )
            st.altair_chart(
                bad_sleep_pareto(df_health_night, n_days=health_days, score_max=75.0),
                use_container_width=True
            )

            with st.expander("How to read this"):
                st.markdown(
                    """
                    This **Pareto chart** shows how often *different bad sleep signals* were triggered
                    across nights with a sleep score equal or less than 75.

                    Each bar counts **triggered signals**, not nights.
                    A single night can contribute to multiple bars
                    (e.g. short sleep *and* late bedtime).

                    The cumulative line answers:
                    *Which factors account for most of the problems when sleep is bad?*

                    This helps prioritize behaviors to fix first,
                    rather than explaining 100% of bad nights.
                    """
                )
