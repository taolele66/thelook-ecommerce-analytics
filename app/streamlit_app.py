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
import plotly.graph_objects as go
import streamlit as st

from src.bq_client import REPO_ROOT
from src.data import load_table
from src.train_churn_model import CATEGORICAL_FEATURES, NUMERIC_FEATURES

st.set_page_config(page_title="TheLook E-commerce Analytics", layout="wide")

# ---------------------------------------------------------------------------
# Theme: Wong (2011, Nature Methods) colorblind-safe palette. Order is fixed
# (never re-cycled per filter) and validated with the data-viz skill's
# validate_palette.js — all checks pass in this order for 5 categorical
# slots. Blue/vermillion double as an implicit healthy/at-risk pairing.
# ---------------------------------------------------------------------------
BLUE, TEAL, ORANGE, PURPLE, VERMILLION = "#0072B2", "#009E73", "#E69F00", "#CC79A7", "#D55E00"
SEGMENT_ORDER = ["高价值活跃用户", "新用户/潜力用户", "一般用户", "沉睡/低价值用户", "高价值流失预警"]
SEGMENT_COLORS = dict(zip(SEGMENT_ORDER, [BLUE, TEAL, ORANGE, PURPLE, VERMILLION]))

INK_PRIMARY, INK_SECONDARY, INK_MUTED = "#0b0b0b", "#52514e", "#898781"
GRIDLINE, SURFACE = "#e1e0d9", "#fcfcfb"
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

st.markdown(
    f"""
    <style>
    .stat-row {{ display: flex; gap: 14px; margin-bottom: 6px; }}
    .stat-card {{
        flex: 1; background: {SURFACE}; border: 1px solid rgba(11,11,11,0.10);
        border-radius: 10px; padding: 14px 18px 16px 18px;
    }}
    .stat-card .accent {{ height: 3px; width: 28px; border-radius: 2px; margin-bottom: 10px; }}
    .stat-card .label {{ color: {INK_SECONDARY}; font-size: 0.82rem; margin-bottom: 2px; }}
    .stat-card .value {{ color: {INK_PRIMARY}; font-size: 1.65rem; font-weight: 600; line-height: 1.2; }}
    .stat-card .sub {{ color: {INK_MUTED}; font-size: 0.78rem; margin-top: 2px; }}
    .insight-box {{
        background: {SURFACE}; border-left: 3px solid {BLUE}; border-radius: 6px;
        padding: 14px 18px; color: {INK_SECONDARY}; font-size: 0.92rem; line-height: 1.55;
    }}
    .insight-box b {{ color: {INK_PRIMARY}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("TheLook E-commerce — Analytics Deep Dive")

tab_overview, tab_cohort, tab_funnel, tab_basket, tab_predict = st.tabs(
    ["Overview", "Cohort Retention", "Purchase Funnel", "Basket Analysis", "Churn / CLV Prediction"]
)


def style_fig(fig, *, title, legend=False, height=340):
    """Shared chrome: system font, hairline recessive gridlines, no chart border."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK_PRIMARY, family=FONT), x=0),
        font=dict(family=FONT, color=INK_SECONDARY, size=12),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        height=height,
        margin=dict(l=10, r=20, t=44, b=10),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11)) if legend else None,
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRIDLINE, gridwidth=1, zeroline=False, color=INK_MUTED)
    fig.update_yaxes(showgrid=False, zeroline=False, color=INK_MUTED)
    return fig


def top_n_plus_other(df: pd.DataFrame, dim: str, value: str, n: int = 9) -> pd.DataFrame:
    df = df.sort_values(value, ascending=False)
    top, rest = df.head(n), df.iloc[n:]
    out = top[[dim, value]].copy()
    if len(rest):
        out = pd.concat([out, pd.DataFrame({dim: ["其他"], value: [rest[value].sum()]})], ignore_index=True)
    return out


def stat_card(col, label: str, value: str, sub: str = "", accent: str = BLUE) -> None:
    col.markdown(
        f"""<div class="stat-card">
                <div class="accent" style="background:{accent};"></div>
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                <div class="sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )


with tab_overview:
    rfm = load_table("rfm_user_features")
    country_dist = load_table("country_distribution")
    category_dist = load_table("category_distribution")
    mau = load_table("monthly_active_users")
    churn_feat = load_table("ml_churn_clv_features")

    n_users = rfm["user_id"].nunique()
    total_gmv = rfm["monetary"].sum()
    aov = rfm["monetary"].sum() / rfm["frequency"].sum()

    c1, c2, c3, c4 = st.columns(4)
    stat_card(c1, "Users", f"{n_users:,}", accent=BLUE)
    stat_card(c2, "Total GMV (window)", f"${total_gmv / 1e6:,.2f}M", accent=TEAL)
    stat_card(c3, "Avg order value", f"${aov:,.2f}", accent=ORANGE)
    stat_card(c4, "Avg return rate", f"{rfm['return_rate'].mean():.1%}", accent=VERMILLION)
    st.write("")

    # --- Segments: donut + monetary bar, same color per segment throughout ---
    seg = (
        rfm.groupby("user_segment")
        .agg(users=("user_id", "nunique"), monetary=("monetary", "sum"), return_rate=("return_rate", "mean"))
        .reindex(SEGMENT_ORDER)
        .reset_index()
    )

    left, right = st.columns([1, 1.2])
    with left:
        fig = px.pie(
            seg, names="user_segment", values="users", hole=0.58,
            color="user_segment", color_discrete_map=SEGMENT_COLORS,
            category_orders={"user_segment": SEGMENT_ORDER},
        )
        fig.update_traces(textposition="outside", textinfo="label+percent", textfont=dict(size=11))
        fig.add_annotation(text=f"{n_users:,}<br><span style='font-size:11px'>users</span>",
                            showarrow=False, font=dict(size=18, color=INK_PRIMARY, family=FONT))
        st.plotly_chart(style_fig(fig, title="User Segments", height=360), width="stretch")

    with right:
        fig = px.bar(
            seg.sort_values("monetary"), x="monetary", y="user_segment", orientation="h",
            color="user_segment", color_discrete_map=SEGMENT_COLORS, text="monetary",
        )
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False, width=0.62)
        fig.update_yaxes(title="")
        fig.update_xaxes(title="GMV ($)")
        st.plotly_chart(style_fig(fig, title="GMV by Segment", height=360), width="stretch")

    # --- Return rate by segment + retention behavior (two single-axis charts, not dual-axis) ---
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            seg.sort_values("return_rate"), x="return_rate", y="user_segment", orientation="h",
            color="user_segment", color_discrete_map=SEGMENT_COLORS, text="return_rate",
        )
        fig.update_traces(texttemplate="%{text:.1%}", textposition="outside", cliponaxis=False, width=0.62)
        fig.update_yaxes(title="")
        fig.update_xaxes(title="Return rate", tickformat=".0%")
        st.plotly_chart(style_fig(fig, title="Return Rate by Segment", height=300), width="stretch")

    with right:
        ret = (
            churn_feat.assign(group=churn_feat["churned_next_90d"].map({0: "Retained", 1: "Churned"}))
            .groupby("group")[["frequency", "monetary"]].mean().reindex(["Retained", "Churned"]).reset_index()
        )
        fig = px.bar(
            ret, x="group", y="frequency", color="group",
            color_discrete_map={"Retained": BLUE, "Churned": VERMILLION}, text="frequency",
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False, width=0.5)
        fig.update_xaxes(title="")
        fig.update_yaxes(title="Avg pre-cutoff order frequency")
        st.plotly_chart(style_fig(fig, title="Order Frequency: Retained vs. Churned", height=300), width="stretch")

    # --- Where users are / what they buy ---
    left, right = st.columns(2)
    with left:
        d = top_n_plus_other(country_dist, "country", "users")
        fig = px.bar(d.sort_values("users"), x="users", y="country", orientation="h", text="users")
        fig.update_traces(marker_color=BLUE, texttemplate="%{text:,}", textposition="outside",
                           cliponaxis=False, width=0.62)
        fig.update_yaxes(title="")
        fig.update_xaxes(title="Users")
        st.plotly_chart(style_fig(fig, title="Users by Country (top 9 + other)", height=340), width="stretch")

    with right:
        d = top_n_plus_other(category_dist, "category", "users")
        fig = px.bar(d.sort_values("users"), x="users", y="category", orientation="h", text="users")
        fig.update_traces(marker_color=BLUE, texttemplate="%{text:,}", textposition="outside",
                           cliponaxis=False, width=0.62)
        fig.update_yaxes(title="")
        fig.update_xaxes(title="Users")
        st.plotly_chart(style_fig(fig, title="Users by Category (top 9 + other)", height=340), width="stretch")

    # --- Monthly active users trend ---
    fig = go.Figure(
        go.Scatter(
            x=mau["month"], y=mau["active_users"], mode="lines",
            line=dict(color=BLUE, width=2), fill="tozeroy", fillcolor="rgba(0,114,178,0.10)",
        )
    )
    fig.update_yaxes(title="Active users")
    st.plotly_chart(style_fig(fig, title="Monthly Active Users", height=280), width="stretch")

    # --- Insight callout, mirrors README § Key findings ---
    churn_rate = churn_feat["churned_next_90d"].mean()
    top_country = country_dist.sort_values("users", ascending=False).iloc[0]
    st.markdown(
        f"""<div class="insight-box">
        <b>留存与流失用户</b>在下单频率、消费金额上存在方向一致但幅度温和的差异；
        退货率在各分群间集中在 <b>{seg['return_rate'].min():.1%}–{seg['return_rate'].max():.1%}</b> 区间，
        区分度有限，说明退货体验并非流失的主要驱动因素。<b>{churn_rate:.0%}</b> 的用户在观察窗口后 90 天内
        零下单——这与该数据集里 <b>71% 的订单只涉及单一品类、平均下单频率仅 {rfm['frequency'].mean():.2f}</b> 的特征一致：
        用户流失更多由购买行为本身（复购频率、消费能力）决定，而非退货体验。
        最大的用户来源国是 <b>{top_country['country']}</b>（{top_country['users']:,} 用户）。
        </div>""",
        unsafe_allow_html=True,
    )

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
