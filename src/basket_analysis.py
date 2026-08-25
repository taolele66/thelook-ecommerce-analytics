"""Market-basket analysis: which product categories tend to be bought together?

Pivots order_category_baskets (order_id, category) into a one-hot basket
matrix and runs apriori + association_rules (mlxtend) to get
support/confidence/lift per category pair.
"""
from mlxtend.frequent_patterns import apriori, association_rules

from src.bq_client import REPO_ROOT
from src.data import load_table


def main() -> None:
    df = load_table("order_category_baskets")

    basket = (
        df.assign(present=1)
        .pivot_table(index="order_id", columns="category", values="present", fill_value=0)
        .astype(bool)
    )

    # Most orders in this dataset touch only one product category, so
    # cross-category support is naturally low — a much lower threshold than
    # apriori's usual 1-5% default is needed to surface any itemsets at all.
    frequent_itemsets = apriori(basket, min_support=0.002, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)
    rules = rules.sort_values("lift", ascending=False)

    out_path = REPO_ROOT / "data" / "basket_rules.csv"
    out_path.parent.mkdir(exist_ok=True)
    rules.to_csv(out_path, index=False)

    print(rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(20))
    print(f"\nSaved {len(rules)} rules to {out_path}")


if __name__ == "__main__":
    main()
