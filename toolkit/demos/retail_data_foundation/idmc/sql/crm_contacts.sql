-- Reverse ETL to the CRM: DQ-valid golden records only (clean-only gate), test identities excluded, plus a count gate:
-- when the share of valid golden records falls below CRM_COUNT_GATE the query returns 0 rows and nothing is pushed,
-- so a bad load never overwrites good CRM data. Column aliases are the Salesforce API field names.
WITH g AS (SELECT * FROM `${WH_PROJECT}.${DS_GOLD}.customer_golden`),
gate AS (SELECT COUNTIF(dq_valid = 1) / GREATEST(COUNT(*), 1) AS valid_share FROM g)
SELECT
  CAST(g.customer_id AS STRING) AS ${SF_CONTACT_EXT},
  IFNULL(NULLIF(REGEXP_EXTRACT(g.full_name, r'^(.*) [^ ]+$'), ''), '') AS FirstName,
  IFNULL(NULLIF(ARRAY_REVERSE(SPLIT(g.full_name, ' '))[SAFE_OFFSET(0)], ''), 'Unknown') AS LastName,
  g.email AS Email,
  g.phone_e164 AS Phone,
  g.address AS MailingStreet,
  g.city AS MailingCity,
  g.state AS MailingState,
  g.zip AS MailingPostalCode,
  g.tier AS Rdf_Tier__c,
  g.home_store_code AS Rdf_Home_Store__c,
  g.signup_channel AS Rdf_Signup_Channel__c,
  g.dq_score AS Rdf_DQ_Score__c
FROM g CROSS JOIN gate
WHERE g.dq_valid = 1
  AND gate.valid_share >= ${CRM_COUNT_GATE}
  AND NOT REGEXP_CONTAINS(g.email, r'${TEST_ID_REGEX}')
