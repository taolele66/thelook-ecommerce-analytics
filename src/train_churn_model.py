"""Train a churn classifier: will this user place zero orders in the next 90 days?

Features and label come from sql/06_ml_features/churn_and_clv_features.sql, which
already enforces a time-based split (features built strictly before the cutoff,
label observed strictly after) to avoid leakage.
"""
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, balanced_accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.bq_client import REPO_ROOT
from src.data import load_table

NUMERIC_FEATURES = [
    "frequency",
    "monetary",
    "avg_order_value",
    "recency_days",
    "tenure_days",
    "avg_categories_per_order",
    "return_rate",
    "age",
]
CATEGORICAL_FEATURES = ["country", "gender", "traffic_source"]
TARGET = "churned_next_90d"


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="passthrough",
    )
    model = HistGradientBoostingClassifier(class_weight="balanced", random_state=42)
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def main() -> None:
    df = load_table("ml_churn_clv_features")
    df = df.dropna(subset=NUMERIC_FEATURES + CATEGORICAL_FEATURES)

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    print(f"Class balance in test set:\n{y_test.value_counts(normalize=True)}\n")
    print(classification_report(y_test, y_pred))
    print(f"ROC AUC: {roc_auc_score(y_test, y_proba):.3f}")
    print(f"Balanced accuracy: {balanced_accuracy_score(y_test, y_pred):.3f}")
    print(f"Average precision (PR AUC): {average_precision_score(y_test, y_proba):.3f}")

    out_path = REPO_ROOT / "models" / "churn_model.joblib"
    out_path.parent.mkdir(exist_ok=True)
    joblib.dump(pipeline, out_path)
    print(f"Saved model to {out_path}")


if __name__ == "__main__":
    main()
