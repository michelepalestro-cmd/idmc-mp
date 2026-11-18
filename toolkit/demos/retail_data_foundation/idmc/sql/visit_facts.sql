-- Store visits with dwell minutes (an open visit counts up to now).
SELECT
  v.visit_id, v.customer_id, UPPER(v.store_code) AS store_code, v.check_in_at, v.check_out_at,
  CAST(TIMESTAMP_DIFF(IFNULL(v.check_out_at, CURRENT_TIMESTAMP()), v.check_in_at, MINUTE) AS INT64) AS minutes,
  v.status
FROM `${WH_PROJECT}.${DS_LAND}.visits` v
