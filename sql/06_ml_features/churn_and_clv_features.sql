-- Model-ready feature table for churn classification + CLV regression.
-- Uses a time-based split to avoid label leakage:
--   observation_cutoff = max(order_date) - 90 days
--   features            = built only from activity BEFORE observation_cutoff
--   churn label         = 1 if the user placed NO order in the 90 days AFTER the cutoff
--   clv_next_90d        = actual $ spent in the 90 days AFTER the cutoff (regression target)
-- This mirrors how the model would be used in production: predict future behavior
-- from past behavior only.

CREATE OR REPLACE TABLE `{project}.thelook_marts.ml_churn_clv_features` AS
WITH bounds AS (
  SELECT
    MAX(order_created_at) AS max_date,
    DATE_SUB(DATE(MAX(order_created_at)), INTERVAL 90 DAY) AS cutoff
  FROM `{project}.thelook_marts.stg_order_items`
  WHERE order_item_status NOT IN ('Cancelled')
),
orders_before AS (
  SELECT o.*
  FROM `{project}.thelook_marts.stg_order_items` o, bounds b
  WHERE o.order_item_status NOT IN ('Cancelled')
    AND DATE(o.order_created_at) < b.cutoff
),
orders_after AS (
  SELECT o.*
  FROM `{project}.thelook_marts.stg_order_items` o, bounds b
  WHERE o.order_item_status NOT IN ('Cancelled')
    AND DATE(o.order_created_at) >= b.cutoff
),
user_orders_before AS (
  SELECT
    user_id,
    order_id,
    MIN(order_created_at) AS order_date,
    SUM(sale_price)       AS order_value,
    LOGICAL_OR(returned_at IS NOT NULL) AS order_has_return,
    COUNT(DISTINCT category) AS categories_in_order
  FROM orders_before
  GROUP BY user_id, order_id
),
features AS (
  SELECT
    uob.user_id,
    ANY_VALUE(o.country)        AS country,
    ANY_VALUE(o.gender)         AS gender,
    ANY_VALUE(o.age)            AS age,
    ANY_VALUE(o.traffic_source) AS traffic_source,
    COUNT(DISTINCT uob.order_id)                                   AS frequency,
    SUM(uob.order_value)                                           AS monetary,
    AVG(uob.order_value)                                           AS avg_order_value,
    DATE_DIFF(b.cutoff, DATE(MAX(uob.order_date)), DAY)            AS recency_days,
    DATE_DIFF(DATE(MAX(uob.order_date)), DATE(MIN(uob.order_date)), DAY) AS tenure_days,
    AVG(uob.categories_in_order)                                   AS avg_categories_per_order,
    COUNTIF(uob.order_has_return) / COUNT(DISTINCT uob.order_id)   AS return_rate
  FROM user_orders_before uob
  JOIN orders_before o ON o.user_id = uob.user_id
  CROSS JOIN bounds b
  GROUP BY uob.user_id, b.cutoff
),
future_spend AS (
  SELECT user_id, SUM(sale_price) AS clv_next_90d
  FROM orders_after
  GROUP BY user_id
)
SELECT
  f.*,
  COALESCE(fs.clv_next_90d, 0) AS clv_next_90d,
  CASE WHEN fs.user_id IS NULL THEN 1 ELSE 0 END AS churned_next_90d
FROM features f
LEFT JOIN future_spend fs USING (user_id)
-- keep only users with enough history to make the label meaningful
WHERE f.frequency >= 1;
