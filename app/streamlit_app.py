"""Interactive companion to the Looker Studio dashboard.

Looker Studio covers the business-facing KPIs; this app is the technical
deep dive: cohort retention, funnel drop-off, basket rules, and live
churn/CLV predictions from the trained models in models/.

Run: streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

from src.bq_client import REPO_ROOT
from src.data import load_table
from src.train_churn_model import CATEGORICAL_FEATURES, NUMERIC_FEATURES

st.set_page_config(page_title="TheLook E-commerce Analytics", layout="wide")
st.title("TheLook E-commerce — Analytics Deep Dive")

tab_overview, tab_cohort, tab_funnel, tab_basket, tab_predict = st.tabs(
    ["Overview", "Cohort Retention", "Purchase Funnel", "Basket Analysis", "Churn / CLV Prediction"]
)

with tab_overview:
    rfm = load_table("rfm_user_features")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Users", f"{rfm['user_id'].nunique():,}")
    col2.metric("Total Monetary (window)", f"${rfm['monetary'].sum():,.0f}")
    col3.metric("Avg Frequency", f"{rfm['frequency'].mean():.2f}")
    col4.metric("Avg Return Rate", f"{rfm['return_rate'].mean():.1%}")

    seg_counts = rfm["user_segment"].value_counts().reset_index()
    seg_counts.columns = ["user_segment", "users"]
    st.plotly_chart(px.pie(seg_counts, names="user_segment", values="users", title="User Segments"), width="stretch")

with tab_cohort:
    cohort = load_table("cohort_retention")
    pivot = cohort.pivot(index="cohort_month", columns="months_since_signup", values="retention_rate")
    st.plotly_chart(
        px.imshow(pivot, color_continuous_scale="Blues", aspect="auto", title="Monthly Cohort Retention"),
        width="stretch",
    )

with tab_funnel:
    funnel = load_table("purchase_funnel")
    top_source = funnel.groupby("traffic_source")[["sessions", "sessions_viewed_product", "sessions_added_to_cart", "sessions_purchased"]].sum()
    stages = pd.DataFrame(
        {
            "stage": ["Sessions", "Viewed Product", "Added to Cart", "Purchased"],
            "count": [
                top_source["sessions"].sum(),
                top_source["sessions_viewed_product"].sum(),
                top_source["sessions_added_to_cart"].sum(),
                top_source["sessions_purchased"].sum(),
            ],
        }
    )
    st.plotly_chart(px.funnel(stages, x="count", y="stage", title="Overall Purchase Funnel"), width="stretch")
    st.dataframe(funnel.sort_values("sessions", ascending=False).head(20))

with tab_basket:
    rules_path = REPO_ROOT / "data" / "basket_rules.csv"
    if rules_path.exists():
        rules = pd.read_csv(rules_path)
        st.dataframe(rules.sort_values("lift", ascending=False).head(30))
    else:
        st.info("Run `python -m src.basket_analysis` first to generate basket_rules.csv")

with tab_predict:
    st.subheader("Live churn risk / next-90-day spend prediction")
    churn_model_path = REPO_ROOT / "models" / "churn_model.joblib"
    clv_model_path = REPO_ROOT / "models" / "clv_regressor.joblib"

    if not (churn_model_path.exists() and clv_model_path.exists()):
        st.info("Run `python -m src.train_churn_model` and `python -m src.train_clv_model` first.")
    else:
        churn_model = joblib.load(churn_model_path)
        clv_model = joblib.load(clv_model_path)
        features = load_table("ml_churn_clv_features")

        user_id = st.selectbox("Pick a user_id", features["user_id"].sample(50, random_state=1).sort_values())
        row = features[features["user_id"] == user_id][NUMERIC_FEATURES + CATEGORICAL_FEATURES]

        churn_proba = churn_model.predict_proba(row)[0, 1]
        clv_pred = clv_model.predict(row)[0]

        c1, c2 = st.columns(2)
        c1.metric("Predicted churn probability (next 90d)", f"{churn_proba:.1%}")
        c2.metric("Predicted spend (next 90d)", f"${clv_pred:,.2f}")
        st.dataframe(row.T.rename(columns={row.index[0]: "value"}).astype(str))
