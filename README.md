# Heart Transplant Risk Calculator

A Streamlit application adapted from the supplied previous calculator design, with 10 predictor categories, point breakdown, four cumulative event-risk horizons, bootstrap percentile 95% confidence intervals, and score–risk curves.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publish

Deploy as a Streamlit app (e.g., Streamlit Community Cloud), or port the scoring and CSV lookup to R Shiny if the original hosting service is preferred. Keep `app.py`, `requirements.txt`, and `data/HeartScore_Risk_Calculator_95CI.csv` together.

## Pre-publication verification

1. Confirm endpoint coding (`label_status==1`) represents death or retransplantation.
2. Confirm baseline survival values are referenced to score zero and match the Cox fitting and bootstrap convention.
3. Verify bootstrap risk table against final point-estimate equations, including exact ties/rounding.
4. Verify observed score range and whether score 101 needs a bootstrap interval.
5. Verify score category mapping, particularly diagnosis, diabetes, missing data and hospital stay.
6. Obtain appropriate institutional approval and label validation status.

No clinical identifiers are collected by the application.
