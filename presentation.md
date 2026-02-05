---
marp: true
paginate: true
size: 16:9
---

<!--
Export tip (VS Code):
- Install the "Marp for VS Code" extension
- Open this file and run: Marp: Export Slide Deck (PDF)
-->

# The Art of Sleeping
## Sleep Compass — a personal sleep consistency & recovery dashboard

**[Your Name]** · Visual Analytics Final Project · **[Course / University]** · **[Date]**

![bg right:45% contain](thumbnail.png)

---

# 1‑minute elevator pitch

- I built a web dashboard that turns my Fitbit sleep logs into a **daily check‑in** plus **short/mid/long‑term** patterns.
- Target user: **me** (habit building + recovery), but it generalizes to anyone with tracker data.
- Main goal: **spot what drives low‑score nights** and make next‑day decisions easier.

---

# Data + research questions

- Source: **Fitbit Versa 2** sleep sessions (Apr–Sep 2025), **162 sessions** (149 night sleeps + 13 naps)
- Key fields: bedtime/wake time, duration, stages (deep/light/REM), efficiency, overall score (0–100), resting HR

Questions I designed for:
- Am I hitting my **7.5h** target—and how often do I miss?
- Is my schedule **consistent** (bed/wake times), or drifting?
- What variables best explain **low overall score** nights?
- Do patterns differ on **weekdays vs weekends**?

---

# What the dashboard does (story + interaction)

Structure (top → bottom):
- **Daily context**: selected “as‑of” date + quick overview + quote (motivational framing)
- **Recommendations**: simple guidance for today based on recent patterns
- **Short‑term** (days): compare recent nights + naps
- **Mid‑term** (weeks): distributions + multi‑metric comparisons
- **Long‑term** (months): calendar patterns + rhythm + relationships

Interactions used in the demo:
- **Time‑travel**: pick an “as‑of” date to replay the past
- **Filter**: All / Weekdays / Weekends
- Hover tooltips + linked reading across charts (consistent color semantics)

---

# Visual encodings (and why they fit)

- **Efficiency funnel**: “last night in one glance” (composition + a single quality metric)
- **Sleep timeline**: compare nights/naps to spot irregularity quickly
- **Target band + line**: show *how far* I am from 7.5h, not just pass/fail
- **Parallel coordinates**: compare many metrics per night without flipping charts
- **Calendar heatmap + sleep rhythm**: reveal long sequences, outliers, and consistency
- **Scatter + Pareto**: test hypotheses + prioritize recurring “bad sleep” signals

---

# What I found (examples from my data)

- **Only ~26%** of night sleeps reach the **7.5h** target (median sleep: **6h 54m**)
- Overall score is strongly driven by **minutes asleep** (**r ≈ 0.71**)
- **Later bedtime** is associated with a **lower score** (**r ≈ −0.25**)
- Weekday vs weekend averages are **surprisingly similar** (score ~77 on both)

---

# Limitations + next steps

Limitations:
- Wearable sleep stages/scores are **estimates** (not ground truth)
- Correlations are **not causal**; confounders exist (stress, workload, illness)
- Missing context variables (caffeine/alcohol, exercise intensity, screen time)

Next steps:
- Add simple **annotations** (“late dinner”, “travel”, “work deadline”)
- Track a few daily habits to explain variance beyond duration
- Add “consistency score” and a clearer “weekly review” mode

---

# Live demo plan (3 minutes)

1) Start at today’s **Daily check‑in** (overview → recommendation)
2) Use **as‑of date** to jump to a “bad night” and show what changes
3) Show **short‑term** timeline (nights + naps) and explain the encoding
4) Jump to **calendar + rhythm** to show consistency/outliers
5) End on **scatter/Pareto** to explain “what drives low score nights”

**Online demo:** https://stef-sleep-app.streamlit.app/

