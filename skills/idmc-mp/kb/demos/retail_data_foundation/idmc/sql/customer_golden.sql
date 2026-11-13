-- Golden record: one survivor per person_key. Survivorship = has_address desc, dq_score desc, created_at asc,
-- customer_id. merged_count = how many source records collapsed into the survivor; first_signed_up_at = the person's
-- earliest sign-up across the merged records.
WITH stg AS (
{{include stg_customers_scored.sql}}
),
ranked AS (
  SELECT
    stg.*,
    ROW_NUMBER() OVER (PARTITION BY person_key
                       ORDER BY has_address DESC, dq_score DESC, created_at ASC, customer_id) AS rn,
    COUNT(*) OVER (PARTITION BY person_key) AS merged_count,
    MIN(created_at) OVER (PARTITION BY person_key) AS first_signed_up_at
  FROM stg
)
SELECT customer_id, full_name, email, phone_e164, address, city, state, zip, tier, signup_channel, home_store_code,
       dq_score, dq_valid, merged_count, first_signed_up_at
FROM ranked
WHERE rn = 1
