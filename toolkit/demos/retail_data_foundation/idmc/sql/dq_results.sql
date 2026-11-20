-- One row per data-quality rule: rows checked, rows failed, and the DQ dimension it rolls up to. Each business rule
-- counts ONCE (address = street + city + state + zip all present; identity = same name AND same e-mail or phone,
-- so two different people who merely share a name are not flagged).
WITH s AS (
{{include stg_customers_scored.sql}}
),
p AS (SELECT * FROM `${WH_PROJECT}.${DS_LAND}.payments`),
m AS (SELECT * FROM `${WH_PROJECT}.${DS_LAND}.memberships`),
o AS (SELECT * FROM `${WH_PROJECT}.${DS_LAND}.orders`),
dup AS (
  SELECT COUNT(DISTINCT a.customer_id) AS n
  FROM s a JOIN s b
    ON a.customer_id < b.customer_id AND LOWER(a.full_name) = LOWER(b.full_name)
   AND (a.email = b.email OR (a.phone_digits != '' AND a.phone_digits = b.phone_digits))
),
rules AS (
  SELECT 'customer_email_valid' AS rule, 'validity' AS dimension, 'customers' AS table_name,
         COUNT(*) AS checked, COUNTIF(email_valid = 0) AS failed FROM s
  UNION ALL SELECT 'customer_phone_e164', 'validity', 'customers', COUNT(*), COUNTIF(phone_e164 = '') FROM s
  UNION ALL SELECT 'customer_address_complete', 'completeness', 'customers', COUNT(*), COUNTIF(has_address = 0) FROM s
  UNION ALL SELECT 'customer_tier_canonical', 'consistency', 'customers', COUNT(*), COUNTIF(tier_valid = 0) FROM s
  UNION ALL SELECT 'customer_duplicate_identity', 'uniqueness', 'customers', (SELECT COUNT(*) FROM s), (SELECT n FROM dup)
  UNION ALL SELECT 'payment_status_present', 'completeness', 'payments', COUNT(*),
                   COUNTIF(status IS NULL OR status = '') FROM p
  UNION ALL SELECT 'payment_processor_present', 'completeness', 'payments', COUNT(*),
                   COUNTIF(processor IS NULL OR processor = '') FROM p
  UNION ALL SELECT 'membership_has_customer', 'integrity', 'memberships', COUNT(*),
                   COUNTIF(customer_id NOT IN (SELECT customer_id FROM s)) FROM m
  UNION ALL SELECT 'order_amount_consistent', 'accuracy', 'orders', COUNT(*),
                   COUNTIF(ABS(list_amount - discount - amount) > 0.01) FROM o
)
SELECT rule, dimension, table_name, checked, failed,
       CAST(ROUND(1 - failed / GREATEST(checked, 1), 4) AS FLOAT64) AS pass_rate
FROM rules
