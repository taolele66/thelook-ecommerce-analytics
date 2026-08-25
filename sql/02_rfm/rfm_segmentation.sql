-- RFM (Recency / Frequency / Monetary) scoring and rule-based segmentation.
-- Anchors "today" to the max order date in the data so the model stays valid
-- as the public dataset is periodically refreshed with new synthetic dates.

CREATE OR REPLACE TABLE `{project}.thelook_marts.rfm_user_features` AS
WITH last_date AS (
  SELECT MAX(order_created_at) AS max_date
  FROM `{project}.thelook_marts.stg_order_items`
  WHERE order_item_status NOT IN ('Cancelled')
),
user_orders AS (
  SELECT
    user_id,
    order_id,
    MIN(order_created_at) AS order_date,
    SUM(sale_price)       AS order_value,
    LOGICAL_OR(returned_at IS NOT NULL) AS order_has_return
  FROM `{project}.thelook_marts.stg_order_items`
  WHERE order_item_status NOT IN ('Cancelled')
  GROUP BY user_id, order_id
),
user_agg AS (
  SELECT
    user_id,
    COUNT(DISTINCT order_id)                              AS frequency,
    SUM(order_value)                                      AS monetary,
    DATE_DIFF(DATE((SELECT max_date FROM last_date)), DATE(MAX(order_date)), DAY) AS recency_days,
    DATE_DIFF(DATE(MAX(order_date)), DATE(MIN(order_date)), DAY)                  AS tenure_days,
    COUNTIF(order_has_return) / COUNT(DISTINCT order_id)  AS return_rate
  FROM user_orders
  GROUP BY user_id
),
scored AS (
  SELECT
    *,
    NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,  -- lower recency_days = more recent = higher score
    NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
    NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
  FROM user_agg
)
SELECT
  *,
  r_score + f_score + m_score AS rfm_total,
  CASE
    WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '高价值活跃用户'
    WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN '高价值流失预警'
    WHEN r_score >= 4 AND f_score <= 2                  THEN '新用户/潜力用户'
    WHEN r_score <= 2 AND f_score <= 2                  THEN '沉睡/低价值用户'
    ELSE '一般用户'
  END AS user_segment
FROM scored;
