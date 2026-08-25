-- Session-level purchase funnel from the clickstream `events` table:
-- product view -> cart -> purchase. Breaks out by traffic_source and device
-- (browser) so drop-off can be compared across acquisition channels.

CREATE OR REPLACE TABLE `{project}.thelook_marts.purchase_funnel` AS
WITH session_flags AS (
  SELECT
    session_id,
    traffic_source,
    browser,
    LOGICAL_OR(event_type = 'product')  AS viewed_product,
    LOGICAL_OR(event_type = 'cart')     AS added_to_cart,
    LOGICAL_OR(event_type = 'purchase') AS purchased
  FROM `bigquery-public-data.thelook_ecommerce.events`
  GROUP BY session_id, traffic_source, browser
)
SELECT
  traffic_source,
  browser,
  COUNT(*)                                   AS sessions,
  COUNTIF(viewed_product)                    AS sessions_viewed_product,
  COUNTIF(added_to_cart)                     AS sessions_added_to_cart,
  COUNTIF(purchased)                         AS sessions_purchased,
  SAFE_DIVIDE(COUNTIF(added_to_cart), COUNTIF(viewed_product)) AS view_to_cart_rate,
  SAFE_DIVIDE(COUNTIF(purchased), COUNTIF(added_to_cart))      AS cart_to_purchase_rate,
  SAFE_DIVIDE(COUNTIF(purchased), COUNT(*))                    AS overall_conversion_rate
FROM session_flags
GROUP BY traffic_source, browser
ORDER BY sessions DESC;
