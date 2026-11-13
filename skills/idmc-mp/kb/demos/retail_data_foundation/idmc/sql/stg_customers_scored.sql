-- stg_customers.sql plus the scores. dq_score = mean of 4 core rules; dq_valid = valid e-mail AND valid phone
-- (the clean-only gate that every activation path checks).
SELECT
  s.*,
  CAST((s.email_valid + s.phone_valid + s.has_address + s.tier_valid) / 4.0 AS FLOAT64) AS dq_score,
  IF(s.email_valid = 1 AND s.phone_valid = 1, 1, 0) AS dq_valid
FROM (
{{include stg_customers.sql}}
) s
