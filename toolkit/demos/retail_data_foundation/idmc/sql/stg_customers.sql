-- Cleanse + score every customer record (the CDQ-style "standardize" step) as BigQuery SQL inside the mapping's source
-- query: the work runs in the warehouse (ELT), the Secure Agent only streams result rows to the targets.
--   name   -> trim, collapse whitespace, Title Case
--   email  -> trim + lower; validity by regex
--   phone  -> digits only; E.164 (+1 and 10 digits) when it can be built
--   tier   -> canonical Bronze / Silver / Gold, else Unknown (tolerates 'GOLD ', 'gld', 'silver ')
--   person_key -> surname | first initial | leading street number | e-mail; a blank street number never merges two
--                 people on surname alone (it falls back to surname | initial | e-mail)
-- Comments and non-ASCII are stripped by the build (the BigQuery reader fails on them).
SELECT
  c.customer_id,
  INITCAP(TRIM(REGEXP_REPLACE(IFNULL(c.full_name, ''), r'\s+', ' '))) AS full_name,
  LOWER(TRIM(IFNULL(c.email, ''))) AS email,
  REGEXP_REPLACE(IFNULL(c.phone, ''), r'[^0-9]', '') AS phone_digits,
  CASE
    WHEN LENGTH(REGEXP_REPLACE(IFNULL(c.phone, ''), r'[^0-9]', '')) = 10
      THEN CONCAT('+1', REGEXP_REPLACE(c.phone, r'[^0-9]', ''))
    WHEN LENGTH(REGEXP_REPLACE(IFNULL(c.phone, ''), r'[^0-9]', '')) = 11
         AND STARTS_WITH(REGEXP_REPLACE(c.phone, r'[^0-9]', ''), '1')
      THEN CONCAT('+', REGEXP_REPLACE(c.phone, r'[^0-9]', ''))
    ELSE ''
  END AS phone_e164,
  IF(LOWER(IFNULL(c.address, '')) = IFNULL(c.address, ''),
     INITCAP(TRIM(REGEXP_REPLACE(IFNULL(c.address, ''), r'\s+', ' '))),
     TRIM(REGEXP_REPLACE(IFNULL(c.address, ''), r'\s+', ' '))) AS address,
  IF(LOWER(IFNULL(c.city, '')) = IFNULL(c.city, ''),
     INITCAP(TRIM(REGEXP_REPLACE(IFNULL(c.city, ''), r'\s+', ' '))),
     TRIM(REGEXP_REPLACE(IFNULL(c.city, ''), r'\s+', ' '))) AS city,
  UPPER(TRIM(IFNULL(c.state, ''))) AS state,
  TRIM(IFNULL(c.zip, '')) AS zip,
  CASE
    WHEN LOWER(TRIM(IFNULL(c.tier, ''))) IN ('gold', 'gld', 'g') THEN 'Gold'
    WHEN LOWER(TRIM(IFNULL(c.tier, ''))) IN ('silver', 'slv', 's') THEN 'Silver'
    WHEN LOWER(TRIM(IFNULL(c.tier, ''))) IN ('bronze', 'brz', 'b') THEN 'Bronze'
    ELSE 'Unknown'
  END AS tier,
  LOWER(TRIM(IFNULL(c.signup_channel, ''))) AS signup_channel,
  UPPER(TRIM(IFNULL(c.home_store_code, ''))) AS home_store_code,
  IFNULL(c.crm_id, '') AS crm_id,
  c.created_at,
  IF(REGEXP_CONTAINS(LOWER(TRIM(IFNULL(c.email, ''))), r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$'), 1, 0) AS email_valid,
  IF(LENGTH(REGEXP_REPLACE(IFNULL(c.phone, ''), r'[^0-9]', '')) IN (10, 11), 1, 0) AS phone_valid,
  IF(TRIM(IFNULL(c.address, '')) != '' AND TRIM(IFNULL(c.city, '')) != '' AND TRIM(IFNULL(c.state, '')) != ''
     AND TRIM(IFNULL(c.zip, '')) != '', 1, 0) AS has_address,
  IF(LOWER(TRIM(IFNULL(c.tier, ''))) IN ('gold', 'gld', 'g', 'silver', 'slv', 's', 'bronze', 'brz', 'b'), 1, 0) AS tier_valid,
  CASE
    WHEN IFNULL(REGEXP_EXTRACT(c.address, r'^\s*([0-9]+)'), '') != '' THEN
      CONCAT(LOWER(ARRAY_REVERSE(SPLIT(TRIM(IFNULL(c.full_name, '')), ' '))[SAFE_OFFSET(0)]), '|',
             SUBSTR(LOWER(TRIM(IFNULL(c.full_name, ''))), 1, 1), '|',
             REGEXP_EXTRACT(c.address, r'^\s*([0-9]+)'), '|', LOWER(TRIM(IFNULL(c.email, ''))))
    ELSE
      CONCAT(LOWER(ARRAY_REVERSE(SPLIT(TRIM(IFNULL(c.full_name, '')), ' '))[SAFE_OFFSET(0)]), '|',
             SUBSTR(LOWER(TRIM(IFNULL(c.full_name, ''))), 1, 1), '|', LOWER(TRIM(IFNULL(c.email, ''))))
  END AS person_key
FROM `${WH_PROJECT}.${DS_LAND}.customers` c
