-- Category-pair co-purchase counts (self-join order_items on order_id).
-- Feeds the market-basket / association-rule mining step in
-- src/basket_analysis.py (support/confidence/lift computed there).

CREATE OR REPLACE TABLE `{project}.thelook_marts.category_pairs` AS
SELECT
  a.category AS category_a,
  b.category AS category_b,
  COUNT(DISTINCT a.order_id) AS co_purchase_orders
FROM `{project}.thelook_marts.stg_order_items` a
JOIN `{project}.thelook_marts.stg_order_items` b
  ON a.order_id = b.order_id
  AND a.category < b.category  -- unordered pair, avoid self-pairs and duplicates
WHERE a.order_item_status NOT IN ('Cancelled')
  AND b.order_item_status NOT IN ('Cancelled')
GROUP BY category_a, category_b
ORDER BY co_purchase_orders DESC;

-- Raw basket export (one row per order_id + category) for mlxtend apriori in Python:
CREATE OR REPLACE TABLE `{project}.thelook_marts.order_category_baskets` AS
SELECT DISTINCT
  order_id,
  category
FROM `{project}.thelook_marts.stg_order_items`
WHERE order_item_status NOT IN ('Cancelled');
