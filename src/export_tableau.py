"""Export flat CSVs for Tableau Public (free tier has no live BigQuery
connector — it reads files: CSV/Excel/Google Sheets/spatial only).

Each export is shaped for a specific chart, not a raw table dump:
  - country_gmv_map.csv        -> filled/symbol map (country-level GMV & users)
  - rfm_user_detail.csv        -> RFM quadrant scatter (frequency x monetary)
  - cohort_retention.csv       -> cohort highlight table (triangular heatmap)
  - category_affinity_matrix.csv -> category x category lift heatmap

Run: python -m src.export_tableau
"""
import pandas as pd

from src.bq_client import REPO_ROOT, get_client
from src.data import load_table

OUT_DIR = REPO_ROOT / "tableau" / "data"

# This synthetic dataset represents the same country two ways in places
# (Portuguese "Brasil" vs "Brazil", German "Deutschland" vs "Germany").
# Tableau's built-in geocoding needs the standard English name to plot a map,
# so both spellings are merged under one canonical name here.
COUNTRY_STD = {"Brasil": "Brazil", "Deutschland": "Germany"}


def export_country_map() -> None:
    country = load_table("country_distribution", use_cache=False)
    country["country_std"] = country["country"].replace(COUNTRY_STD)
    out = country.groupby("country_std", as_index=False)[["users", "gmv"]].sum()
    out = out.rename(columns={"country_std": "country"}).sort_values("users", ascending=False)
    out.to_csv(OUT_DIR / "country_gmv_map.csv", index=False)
    print(f"country_gmv_map.csv: {len(out)} countries")


def export_rfm_detail() -> None:
    """Includes `country` (normalized the same way as the map export) so a
    Tableau dashboard action can link the country map to this scatter plot —
    the two shared no field before this, which made cross-filtering between
    them impossible."""
    rfm = load_table("rfm_user_features", use_cache=False)
    client = get_client()
    country = client.query(
        "SELECT id AS user_id, country FROM `bigquery-public-data.thelook_ecommerce.users`"
    ).result().to_dataframe()
    country["country"] = country["country"].replace(COUNTRY_STD)

    rfm = rfm.merge(country, on="user_id", how="left")
    cols = ["user_id", "country", "frequency", "monetary", "recency_days", "tenure_days", "return_rate", "user_segment"]
    rfm[cols].to_csv(OUT_DIR / "rfm_user_detail.csv", index=False)
    print(f"rfm_user_detail.csv: {len(rfm)} users")


def export_cohort_retention() -> None:
    cohort = load_table("cohort_retention", use_cache=False)
    cohort.to_csv(OUT_DIR / "cohort_retention.csv", index=False)
    print(f"cohort_retention.csv: {len(cohort)} rows")


def export_category_affinity() -> None:
    """Category x category lift, computed from order-level category membership
    (lift = P(A,B) / (P(A) * P(B)); >1 means the pair co-occurs more than chance)."""
    baskets = load_table("order_category_baskets", use_cache=False)
    total_orders = baskets["order_id"].nunique()
    order_counts = baskets.groupby("category")["order_id"].nunique()

    pairs = load_table("category_pairs", use_cache=False)
    pairs = pairs.merge(order_counts.rename("orders_a"), left_on="category_a", right_index=True)
    pairs = pairs.merge(order_counts.rename("orders_b"), left_on="category_b", right_index=True)
    pairs["lift"] = (pairs["co_purchase_orders"] / total_orders) / (
        (pairs["orders_a"] / total_orders) * (pairs["orders_b"] / total_orders)
    )

    # Mirror into a full symmetric matrix (A,B) and (B,A) so Tableau can put
    # category on both rows and columns without needing a calculated field.
    mirrored = pairs.rename(columns={"category_a": "category_b", "category_b": "category_a"})
    full = pd.concat([pairs, mirrored], ignore_index=True)[["category_a", "category_b", "co_purchase_orders", "lift"]]
    full.to_csv(OUT_DIR / "category_affinity_matrix.csv", index=False)
    print(f"category_affinity_matrix.csv: {len(full)} pairs")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_country_map()
    export_rfm_detail()
    export_cohort_retention()
    export_category_affinity()


if __name__ == "__main__":
    main()
