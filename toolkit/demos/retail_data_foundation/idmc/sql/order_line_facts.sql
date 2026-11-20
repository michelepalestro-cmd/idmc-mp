-- Line-level sales facts (order + line + product), one row per order line of a placed or paid order. order_day is a
-- TIMESTAMP at midnight UTC (a BigQuery DATE target column would need the STRING 'YYYY-MM-DD 00:00:00' instead).
SELECT
  l.order_line_id, l.order_id, o.customer_id, UPPER(o.store_code) AS store_code, o.channel, o.status AS order_status,
  TIMESTAMP_TRUNC(o.ordered_at, DAY) AS order_day,
  l.product_id, p.sku, p.category, l.qty, l.unit_price, l.line_amount
FROM `${WH_PROJECT}.${DS_LAND}.order_lines` l
JOIN `${WH_PROJECT}.${DS_LAND}.orders` o ON o.order_id = l.order_id
LEFT JOIN `${WH_PROJECT}.${DS_LAND}.products` p ON p.product_id = l.product_id
WHERE o.status IN ('placed', 'paid')
