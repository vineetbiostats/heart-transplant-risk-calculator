import math
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Heart Transplant Risk Calculator", page_icon="♥", layout="wide")
ROOT = Path(__file__).resolve().parent
CSV = ROOT / "HeartScore_Risk_Calculator_95CI.csv"
if not CSV.exists():
    CSV = ROOT / "data" / "HeartScore_Risk_Calculator_95CI.csv"
if not CSV.exists():
    st.error("Risk table not found. Upload HeartScore_Risk_Calculator_95CI.csv beside app.py or inside data/.")
    st.stop()
DATA = pd.read_csv(CSV)
BASE = {1: 0.96748726, 5: 0.92018142, 10: 0.84173748, 15: 0.72456804}
BETA = 0.03843341
RULES = {
    "Length of hospital stay (days)": [("<1", 36), ("1–7", 4), ("8–23", 0), ("24–53", 5), ("≥54", 16)],
    "Recipient age (years)": [("<27", 4), ("27–42", 0), ("43–60", 3), ("61–65", 8), ("≥66", 10)],
    "Donor age (years)": [("<19", 0), ("19–41", 2), ("42–51", 7), ("≥52", 10)],
    "Recipient ethnicity": [("Black", 8), ("Hispanic/Other", 0), ("White", 1)],
    "Recipient diabetes status": [("No", 0), ("Unknown/not reported", 2), ("Yes", 6)],
    "eGFR (mL/min/1.73 m²)": [("<28", 8), ("28–<44.4", 5), ("44.4–<88", 1), ("88–<109", 0), ("≥109", 1), ("Unknown/not reported", 3)],
    "Total bilirubin (mg/dL)": [("<0.3", 2), ("0.3–<0.5", 0), ("0.5–<3.2", 1), ("≥3.2", 3), ("Unknown/not reported", 0)],
    "Source of payment": [("Government", 4), ("Other/not reported", 3), ("Private", 0)],
    "Recipient cigarette use": [("No", 0), ("Not reported", 8), ("Yes", 5)],
    "Primary diagnosis": [("Congenital heart disease", 2), ("Dilated cardiomyopathy", 2), ("Ischemic cardiomyopathy", 8), ("Retransplantation/graft failure/valvular heart disease/other or rare diagnoses", 5), ("Restrictive/hypertrophic cardiomyopathy", 0)],
}

def predicted_risk(score, horizon):
    return -math.expm1(math.log(BASE[horizon]) * math.exp(BETA * score))

st.title("Heart Transplant Risk Calculator")
left, center, right = st.columns([1.15, 1.2, 1.65], gap="large")

with left:
    st.subheader("Patient characteristics")
    mode = st.radio("Input", ["Individual predictors", "Total score"], horizontal=True, label_visibility="collapsed")
    selected = []
    if mode == "Individual predictors":
        for name, options in RULES.items():
            labels = [f"{category} ({points} points)" for category, points in options]
            choice = st.selectbox(name, labels, index=None, placeholder="Select…", key=name)
            if choice is not None:
                index = labels.index(choice)
                selected.append((name, options[index][0], options[index][1]))
        score = sum(item[2] for item in selected) if len(selected) == len(RULES) else None
    else:
        score = st.number_input("Total Heart Score", min_value=0, max_value=101, value=None, step=1, placeholder="Enter score")

with center:
    st.subheader("Score and predictions")
    if score is None:
        st.info("Select all 10 predictors or enter a total score.")
    else:
        score = int(score)
        st.metric("Total Heart Score", score)
        st.caption(f"Linear predictor: {BETA * score:.5f}")
        rows = []
        for horizon in BASE:
            match = DATA.loc[(DATA.heart_score == score) & (DATA.horizon == horizon)]
            ci = "Not available"
            if not match.empty:
                item = match.iloc[0]
                ci = f"{100 * item.lower95:.2f}–{100 * item.upper95:.2f}%"
            rows.append({"Horizon": f"{horizon} year" + ("s" if horizon > 1 else ""),
                         "Risk": f"{100 * predicted_risk(score, horizon):.2f}%", "95% CI": ci})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        if score > 100:
            st.warning("Bootstrap 95% CIs are unavailable for score 101.")
        if selected:
            st.markdown("**Scoring breakdown**")
            st.dataframe(pd.DataFrame(selected, columns=["Predictor", "Category", "Points"]), hide_index=True, use_container_width=True)

with right:
    st.subheader("Predicted risk by Heart Score")
    curves = DATA.copy()
    curves["Risk (%)"] = curves["risk"] * 100
    curves["Horizon"] = curves["horizon"].map(lambda t: f"{t} year" + ("s" if t > 1 else ""))
    order = ["1 year", "5 years", "10 years", "15 years"]
    enc = dict(
        x=alt.X("heart_score:Q", title="Total Heart Score", scale=alt.Scale(domain=[0, 101])),
        y=alt.Y("Risk (%):Q", title="Event risk (%)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("Horizon:N", sort=order),
        tooltip=[alt.Tooltip("heart_score:Q", title="Score"), "Horizon:N", alt.Tooltip("Risk (%):Q", format=".2f")],
    )
    chart = alt.Chart(curves).mark_line(strokeWidth=2.5).encode(**enc)
    if score is not None and score <= 100:
        dots = alt.Chart(curves.loc[curves.heart_score == score]).mark_circle(size=125, filled=True).encode(**enc)
        chart = chart + dots
    st.altair_chart(chart.properties(height=420), use_container_width=True)

st.divider()
with st.expander("About the model and technical details"):
    st.markdown("**Outcome:** Death or retransplantation after a first heart transplant (verify against final event coding).")
    st.markdown("**Model:** Fully updated Cox model; 1-, 5-, 10- and 15-year event probabilities measured from transplantation.")
    st.markdown("**95% CIs:** Percentile intervals from 1,000 bootstrap recalibration replicates, conditional on the original score.")
    st.markdown("**Limitations:** Research use only; not prospectively independently validated. Length of hospital stay is post-transplant information, so a complete score cannot be calculated before it is known. Confirm baseline survival centering, valid score range, and event definition before clinical use.")
    st.markdown(f"**Updated coefficient per point:** {BETA:.8f}")
    st.dataframe(pd.DataFrame([{"Years": t, "Baseline survival": s} for t, s in BASE.items()]), hide_index=True)
    st.latex(r"P(t\mid S)=1-S_0(t)^{\exp(0.03843341S)}")
