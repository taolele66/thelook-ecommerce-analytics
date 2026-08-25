-- Monthly acquisition cohorts and retention curves.
-- Output grain: one row per (cohort_month, months_since_signup) with active user count
-- and retention_rate relative to the cohort's initial size. Feeds a Looker Studio
-- retention heatmap and the Streamlit cohort tab.

CREATE OR REPLACE TABLE `{project}.thelook_marts.cohort_retention` AS
WITH first_order AS (
  SELECT
    user_id,
    DATE_TRUNC(DATE(MIN(order_created_at)), MONTH) AS cohort_month
  FROM `{project}.thelook_marts.stg_order_items`
  WHERE order_item_status NOT IN ('Cancelled')
  GROUP BY user_id
),
monthly_activity AS (
  SELECT DISTINCT
    user_id,
    DATE_TRUNC(DATE(order_created_at), MONTH) AS activity_month
  FROM `{project}.thelook_marts.stg_order_items`
  WHERE order_item_status NOT IN ('Cancelled')
),
cohort_activity AS (
  SELECT
    f.cohort_month,
    a.activity_month,
    DATE_DIFF(a.activity_month, f.cohort_month, MONTH) AS months_since_signup,
    COUNT(DISTINCT a.user_id) AS active_users
  FROM monthly_activity a
  JOIN first_order f USING (user_id)
  WHERE a.activity_month >= f.cohort_month
  GROUP BY 1, 2, 3
),
cohort_size AS (
  SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_users
  FROM first_order
  GROUP BY cohort_month
)
SELECT
  ca.cohort_month,
  ca.months_since_signup,
  ca.active_users,
  cs.cohort_users,
  SAFE_DIVIDE(ca.active_users, cs.cohort_users) AS retention_rate
FROM cohort_activity ca
JOIN cohort_size cs USING (cohort_month)
ORDER BY cohort_month, months_since_signup;
