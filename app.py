import math
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path

st.set_page_config(page_title='Heart Transplant Risk Calculator', page_icon='♥', layout='wide')
ROOT=Path(__file__).parent
DATA=pd.read_csv(ROOT/'HeartScore_Risk_Calculator_95CI.csv')
BASE={1:0.96748726,5:0.92018142,10:0.84173748,15:0.72456804}
BETA=0.03843341

RULES={
 'Length of hospital stay (days)': [('<1',36),('1–7',4),('8–23',0),('24–53',5),('≥54',16)],
 'Recipient age (years)': [('<27',4),('27–42',0),('43–60',3),('61–65',8),('≥66',10)],
 'Donor age (years)': [('<19',0),('19–41',2),('42–51',7),('≥52',10)],
 'Recipient ethnicity': [('Black',8),('Hispanic/Other',0),('White',1)],
 'Recipient diabetes status': [('No',0),('Unknown/not reported',2),('Yes',6)],
 'eGFR (mL/min/1.73 m²)': [('<28',8),('28–<44.4',5),('44.4–<88',1),('88–<109',0),('≥109',1),('Unknown/not reported',3)],
 'Total bilirubin (mg/dL)': [('<0.3',2),('0.3–<0.5',0),('0.5–<3.2',1),('≥3.2',3),('Unknown/not reported',0)],
 'Source of payment': [('Government',4),('Other/not reported',3),('Private',0)],
 'Recipient cigarette use': [('No',0),('Not reported',8),('Yes',5)],
 'Primary diagnosis': [('Congenital heart disease',2),('Dilated cardiomyopathy',2),('Ischemic cardiomyopathy',8),('Retransplantation/graft failure/valvular heart disease/other or rare diagnoses',5),('Restrictive/hypertrophic cardiomyopathy',0)]
}

def risk(score, horizon):
    return -math.expm1(math.log(BASE[horizon])*math.exp(BETA*score))

st.title('Heart Transplant Risk Calculator')
st.caption('Death or retransplantation after a first heart transplant · Fully updated model · Research prototype')
st.warning('Research use only. This tool is not independently validated for prospective clinical decisions. Hospital length of stay is post-transplant information; predictions are not available before that information is known. Time horizons are measured from transplantation, not discharge.')
left, center, right=st.columns([1.15,1.15,1.65],gap='large')
with left:
    st.subheader('Patient characteristics')
    mode=st.radio('Input method',['Individual predictors','Total score'],horizontal=True)
    selected=[]
    if mode=='Individual predictors':
        for name, options in RULES.items():
            selection=st.selectbox(name,[f'{category}  ({points} points)' for category,points in options],index=None,placeholder='Select category',key=name)
            if selection is not None:
                ix=[f'{category}  ({points} points)' for category,points in options].index(selection)
                selected.append((name,options[ix][0],options[ix][1]))
        score=sum(row[2] for row in selected) if len(selected)==len(RULES) else None
    else:
        score=st.number_input('Total Heart Score',min_value=0,max_value=101,value=None,step=1,placeholder='Enter score')
    with st.expander('Model calibration parameters'):
        st.write(f'Updated coefficient per point: **{BETA:.8f}**')
        st.table(pd.DataFrame([{'Horizon (years)':t,'Baseline survival':s} for t,s in BASE.items()]))
        st.latex(r'P(t|S)=1-S_0(t)^{\\exp(0.03843341 S)}')
with center:
    st.subheader('Score and predictions')
    if score is None:
        st.info('Complete all 10 predictor selections or enter the total score to see predictions.')
    else:
        st.metric('Total Heart Score',int(score))
        if score>100:
            st.error('The supplied bootstrap CI table covers scores 0–100 only. No confidence interval is available for score 101.')
        if score<1 or score>80:
            st.warning('This score is outside the previously reported observed range of 1–80; predictions may extrapolate. Verify against the final analytic dataset.')
        st.caption(f'Updated linear predictor = {BETA*score:.5f}')
        rows=[]
        for t in BASE:
            r=DATA[(DATA.heart_score==score)&(DATA.horizon==t)]
            if not r.empty:
                rec=r.iloc[0]
                rows.append({'Horizon':f'{t} year'+('s' if t>1 else ''),'Risk (%)':100*risk(score,t),'Lower 95% CI (%)':100*rec.lower95,'Upper 95% CI (%)':100*rec.upper95})
            else:
                rows.append({'Horizon':f'{t} year'+('s' if t>1 else ''),'Risk (%)':100*risk(score,t),'Lower 95% CI (%)':float('nan'),'Upper 95% CI (%)':float('nan')})
        results=pd.DataFrame(rows)
        st.dataframe(results.style.format({'Risk (%)':'{:.2f}','Lower 95% CI (%)':'{:.2f}','Upper 95% CI (%)':'{:.2f}'}),hide_index=True,use_container_width=True)
        if selected:
            st.markdown('**Patient-specific scoring table**')
            st.dataframe(pd.DataFrame(selected,columns=['Predictor','Selected category','Points']),hide_index=True,use_container_width=True)
        st.caption('95% CIs are percentile intervals from 1,000 patient-level bootstrap recalibration replicates, conditional on the original score.')
with right:
    st.subheader('Predicted risk versus total score')
    curves=DATA.copy()
    curves['Risk (%)']=curves['risk']*100
    curves['Horizon']=curves['horizon'].astype(str)+' years'
    chart=alt.Chart(curves).mark_line(strokeWidth=2.5).encode(
        x=alt.X('heart_score:Q',title='Total Heart Score',scale=alt.Scale(domain=[0,100])),
        y=alt.Y('Risk (%):Q',title='Cumulative event risk (%)',scale=alt.Scale(domain=[0,100])),
        color=alt.Color('Horizon:N',sort=['1 years','5 years','10 years','15 years']),
        tooltip=[alt.Tooltip('heart_score:Q',title='Score'),alt.Tooltip('Horizon:N'),alt.Tooltip('Risk (%):Q',format='.2f')]
    )
    if score is not None and score<=100:
        pts=curves[curves.heart_score==score]
        dots=alt.Chart(pts).mark_circle(size=125,filled=True,stroke='white',strokeWidth=1.5).encode(x='heart_score:Q',y='Risk (%):Q',color='Horizon:N',tooltip=['Horizon:N',alt.Tooltip('Risk (%):Q',format='.2f')])
        chart=chart+dots
    st.altair_chart(chart.properties(height=420),use_container_width=True)
    st.caption('Filled markers indicate the selected patient’s Heart Score. Curves show estimated cumulative event risk at 1, 5, 10 and 15 years.')
    st.markdown('**Interpretation and limitations**')
    st.write('The estimated probability is the cumulative probability of the model-defined event by each time horizon after transplantation. Confidence intervals quantify uncertainty in the estimated risk function, not an individual prediction interval. Confirm the endpoint coding, the baseline-survival reference, and the final score range before public release.')
    st.download_button('Download calculator risk table (CSV)',DATA.to_csv(index=False).encode(),file_name='HeartScore_Risk_Calculator_95CI.csv',mime='text/csv')

st.divider()
st.caption('Model version: fully updated contemporary recalibration, November 2026. Parameters and bootstrap table are supplied by the investigators. No patient identifiers are requested or stored by this app.')
