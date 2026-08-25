-- Supporting breakdowns for the Streamlit Overview tab: where users are
-- (country), what they buy (category), and how the active base trends over
-- time. Kept separate from rfm_user_features (one row per user) since these
-- are one-row-per-dimension-value aggregates.

CREATE OR REPLACE TABLE `{project}.thelook_marts.country_distribution` AS
SELECT
  country,
  COUNT(DISTINCT user_id) AS users,
  SUM(sale_price)         AS gmv
FROM `{project}.thelook_marts.stg_order_items`
WHERE order_item_status NOT IN ('Cancelled')
GROUP BY country
ORDER BY users DESC;

CREATE OR REPLACE TABLE `{project}.thelook_marts.category_distribution` AS
SELECT
  category,
  COUNT(DISTINCT user_id) AS users,
  SUM(sale_price)         AS gmv
FROM `{project}.thelook_marts.stg_order_items`
WHERE order_item_status NOT IN ('Cancelled')
GROUP BY category
ORDER BY users DESC;

CREATE OR REPLACE TABLE `{project}.thelook_marts.monthly_active_users` AS
SELECT
  DATE_TRUNC(DATE(order_created_at), MONTH) AS month,
  COUNT(DISTINCT user_id)                   AS active_users
FROM `{project}.thelook_marts.stg_order_items`
WHERE order_item_status NOT IN ('Cancelled')
GROUP BY month
ORDER BY month;
