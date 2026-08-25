"""Predict next-90-day spend (CLV regression) from pre-cutoff RFM-style features.

Reports both a plain regression baseline (GradientBoostingRegressor) and, for
comparison, a probabilistic BG/NBD + Gamma-Gamma model (the `lifetimes`
package) fit on the same pre-cutoff transaction history — a standard approach
in CLV literature that models purchase frequency and monetary value as
separate stochastic processes rather than one black-box regressor.
"""
import joblib
import numpy as np
import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.bq_client import REPO_ROOT
from src.data import load_table
from src.train_churn_model import CATEGORICAL_FEATURES, NUMERIC_FEATURES

TARGET = "clv_next_90d"


def fit_regressor(df: pd.DataFrame) -> None:
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    preprocessor = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES)],
        remainder="passthrough",
    )
    pipeline = Pipeline([("preprocess", preprocessor), ("model", GradientBoostingRegressor(random_state=42))])
    pipeline.fit(X_train, y_train)

    pred = pipeline.predict(X_test)
    print("GradientBoostingRegressor")
    print(f"  MAE: {mean_absolute_error(y_test, pred):.2f}")
    print(f"  R2:  {r2_score(y_test, pred):.3f}")

    out_path = REPO_ROOT / "models" / "clv_regressor.joblib"
    out_path.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, out_path)
    print(f"Saved model to {out_path}")


def fit_bgnbd_gamma_gamma(df: pd.DataFrame) -> None:
    # BG/NBD naming differs from the RFM naming used in the feature table:
    #   frequency = repeat purchases only (our `frequency` counts the first order too, so subtract 1)
    #   recency   = time from FIRST to LAST purchase (our `tenure_days`)
    #   T         = time from FIRST purchase to the observation cutoff
    #             = our `recency_days` (cutoff - last purchase) + `tenure_days` (last - first purchase)
    lt = df[["frequency", "recency_days", "tenure_days", "avg_order_value"]].copy()
    lt["T"] = lt["recency_days"] + lt["tenure_days"]
    lt = lt.rename(columns={"tenure_days": "recency"})
    lt["frequency"] = (lt["frequency"] - 1).clip(lower=0)
    lt = lt[lt["avg_order_value"] > 0]

    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(lt["frequency"], lt["recency"], lt["T"])

    repeat_buyers = lt[lt["frequency"] > 0]
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(repeat_buyers["frequency"], repeat_buyers["avg_order_value"])

    pred_clv = ggf.customer_lifetime_value(
        bgf,
        lt["frequency"],
        lt["recency"],
        lt["T"],
        lt["avg_order_value"],
        time=3,  # months
        freq="D",
        discount_rate=0.01,
    )
    # Negative predictions are a known artifact of extrapolating from a customer base
    # that is overwhelmingly one-time buyers (repeat purchase probability near zero) —
    # not a bug. CLV can't be negative in business terms, so clip at 0.
    pred_clv = pred_clv.clip(lower=0)
    print("\nBG/NBD + Gamma-Gamma (probabilistic CLV, 3-month horizon, clipped at 0)")
    print(pred_clv.describe())
    print(
        f"\n{(pred_clv == 0).mean():.1%} of users get a $0 probabilistic CLV — "
        "consistent with the low repeat-purchase rate in this dataset."
    )


def main() -> None:
    df = load_table("ml_churn_clv_features")
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES)

    fit_regressor(df)
    fit_bgnbd_gamma_gamma(df)


if __name__ == "__main__":
    main()
