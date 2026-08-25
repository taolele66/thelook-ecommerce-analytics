-- Enriched order-line grain: one row per order_item, joined to product, user, and order status.
-- Source: bigquery-public-data.thelook_ecommerce
-- Excludes cancelled orders from monetary calculations downstream (kept here, filtered in marts).

CREATE OR REPLACE VIEW `{project}.thelook_marts.stg_order_items` AS
SELECT
  oi.id                    AS order_item_id,
  oi.order_id,
  oi.user_id,
  oi.product_id,
  oi.status                AS order_item_status,
  oi.created_at             AS order_created_at,
  oi.shipped_at,
  oi.delivered_at,
  oi.returned_at,
  oi.sale_price,
  p.category,
  p.department,
  p.brand,
  p.cost                    AS product_cost,
  p.retail_price,
  u.country,
  u.state,
  u.city,
  u.age,
  u.gender,
  u.traffic_source,
  u.created_at              AS user_signup_at
FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
JOIN `bigquery-public-data.thelook_ecommerce.products` p
  ON oi.product_id = p.id
JOIN `bigquery-public-data.thelook_ecommerce.users` u
  ON oi.user_id = u.id;
