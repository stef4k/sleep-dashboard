import streamlit as st
from src.data import load_sleep_csv
from src.charts import calendar_heatmap, rhythm_chart, bedtime_vs_score

st.set_page_config(page_title="Sleep Compass", layout="wide")

st.title("Sleep Compass")
st.caption("MVP: patterns, rhythm, and one driver relationship.")

use_real = st.toggle("Use real data (local only)", value=False)
path = "data/sleep_data.csv" if use_real else "data/synthetic.csv"

df = load_sleep_csv(path)

# Filters
col1, col2, col3 = st.columns([1,1,1])
with col1:
    only_night = st.checkbox("Only night sleep", value=True)
with col2:
    days = st.selectbox("Range", [7, 30, 90, 365], index=1)
with col3:
    metric = st.selectbox("Heatmap metric", ["minutes_asleep", "overall_score", "efficiency"], index=0)

if only_night:
    df = df[df["is_night_sleep"] == True]

df_recent = df.tail(days)

# KPI row
st.subheader("Quick stats")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Avg score", f"{df_recent['overall_score'].mean():.1f}")
k2.metric("Avg sleep (h)", f"{df_recent['sleep_hours'].mean():.2f}")
k3.metric("Avg efficiency", f"{df_recent['efficiency'].mean():.2f}")
k4.metric("Avg deep %", f"{(df_recent['deep_pct'].mean()*100):.1f}%")
k5.metric("Avg RHR", f"{df_recent['resting_heart_rate'].mean():.1f}")

# Charts
st.subheader("Overview")
st.altair_chart(calendar_heatmap(df_recent, value_col=metric), use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Sleep rhythm (bed/wake)")
    st.altair_chart(rhythm_chart(df_recent), use_container_width=True)
with c2:
    st.subheader("Bedtime vs score")
    st.altair_chart(bedtime_vs_score(df_recent), use_container_width=True)

with st.expander("Data preview"):
    st.dataframe(df_recent.tail(50), use_container_width=True)
