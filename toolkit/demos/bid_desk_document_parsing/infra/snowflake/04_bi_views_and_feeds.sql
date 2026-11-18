-- Bid Desk 04: the governance feed tables (catalog lineage + glossary, filled by bid_lineage.py feed / bid_glossary.py feed)
-- and one BI view per Tableau sheet (BID_V_BI_*). Tableau reads only these views. Idempotent.
USE SCHEMA ${snowflake.database}.${snowflake.schema};

CREATE TABLE IF NOT EXISTS BID_LINEAGE (
  READ_AT TIMESTAMP_NTZ, VIEW_NAME VARCHAR(100), HOP NUMBER(4, 0), FROM_NAME VARCHAR(300), FROM_TYPE VARCHAR(60), FROM_SYSTEM VARCHAR(60),
  TO_NAME VARCHAR(300), TO_TYPE VARCHAR(60), TO_SYSTEM VARCHAR(60))
  COMMENT = 'Bid Desk: the catalog (CDGC) lineage of every Tableau view, hop by hop, as the catalog shows it';

CREATE TABLE IF NOT EXISTS BID_GLOSSARY (
  READ_AT TIMESTAMP_NTZ, DOMAIN VARCHAR(100), TERM VARCHAR(100), DEFINITION VARCHAR(2000), LIFECYCLE VARCHAR(40), LINKED_ASSET VARCHAR(300))
  COMMENT = 'Bid Desk: the glossary terms (CDGC) and the Snowflake columns each is linked to';

-- tab 1 Bid Desk: one card per solicitation
CREATE OR REPLACE VIEW BID_V_BI_DECISIONS AS
SELECT G.SORT_ORDER, G.AGENCY, G.SOLICITATION_NO, G.DOC_TYPE, G.SOLICITATION_TITLE, G.BID_DUE, G.DECISION, G.DETAIL, G.DQ_SCORE,
       G.LINES, G.LINES_PRICED, G.LINES_TO_PRICE, G.LINES_TO_FIX, G.REQUIRED_FIELDS, G.FIELDS_BLANK, G.FIELDS_INVALID, G.BID_VALUE,
       S.PAYMENT_TERMS, S.FOB, S.PRICE_RULE, S.SIGNATURE_RULE, S.E_SIGNATURE_RULE, G.VERSION_NUMBER AS CRM_FILE_VERSION, G.LOADED_AT
FROM BID_GLD_READINESS G LEFT JOIN BID_V_SOLICITATIONS S ON S.CONTENT_VERSION_ID = G.CONTENT_VERSION_ID;

CREATE OR REPLACE VIEW BID_V_BI_BID_LINES AS
SELECT SOLICITATION_NO, ITEM_NO, ITEM_DESCRIPTION, UNIT, QTY_NEEDED, CURRENT_PRODUCT, BRAND_PREFERRED, UNIT_PRICE_TEXT, BRAND_BID,
       LINE_VALUE, LINE_STATUS, LINE_ISSUE, DQ_PRODUCT_ONE_LINE, DQ_PRICE_FILLED, DQ_PRICE_DECIMALS, DQ_BRAND_FILLED
FROM BID_SLV_BID_LINES;

CREATE OR REPLACE VIEW BID_V_BI_FIELDS AS
SELECT SOLICITATION_NO, FORM_NAME, FIELD_NO, FIELD_NAME, IFF(FIELD_STATUS = 'BLANK', '(blank)', FIELD_VALUE) AS FIELD_VALUE,
       FIELD_STATUS, DQ_FILLED, DQ_EMAIL_FORMAT
FROM BID_SLV_REQUIRED_FIELDS;

-- tab 2 Data Quality: the Data Profiling scorecard (latest read per profile) + the in-pipeline checks per rule
CREATE OR REPLACE VIEW BID_V_BI_DQ AS
SELECT 'Data Profiling' AS CHECKED_BY, SOURCE AS LAYER, PROFILE_NAME, TABLE_NAME, COLUMN_NAME, RULE_SPEC, DIMENSION, CHECKED, PASSED,
       FAILED, SCORE_PCT, READ_AT
FROM BID_DQ_SCORECARD QUALIFY READ_AT = MAX(READ_AT) OVER (PARTITION BY PROFILE_NAME)
UNION ALL
SELECT 'Mapping 3a', 'Silver', NULL, 'BID_SLV_BID_LINES', R.COL, R.RULE, R.DIM, COUNT(*), SUM(IFF(R.V = 'VALID', 1, 0)),
       SUM(IFF(R.V = 'VALID', 0, 1)), ROUND(100 * SUM(IFF(R.V = 'VALID', 1, 0)) / NULLIF(COUNT(*), 0), 1), MAX(L.LOADED_AT)
FROM BID_SLV_BID_LINES L, LATERAL (SELECT * FROM VALUES
     ('UNIT_PRICE_TEXT', 'Required value filled in', 'COMPLETENESS', L.DQ_PRICE_FILLED),
     ('UNIT_PRICE_TEXT', 'Price with at most two decimals', 'CONFORMITY', L.DQ_PRICE_DECIMALS),
     ('BRAND_BID', 'Required value filled in', 'COMPLETENESS', L.DQ_BRAND_FILLED)) R(COL, RULE, DIM, V)
GROUP BY R.COL, R.RULE, R.DIM;

-- tab 3 Lineage: every hop the catalog shows (fed by bid_lineage.py feed)
CREATE OR REPLACE VIEW BID_V_BI_LINEAGE AS
SELECT VIEW_NAME, HOP, FROM_SYSTEM, FROM_TYPE, FROM_NAME, TO_SYSTEM, TO_TYPE, TO_NAME, READ_AT
FROM BID_LINEAGE QUALIFY READ_AT = MAX(READ_AT) OVER ();

-- tab 4 Glossary and Governance
CREATE OR REPLACE VIEW BID_V_BI_GLOSSARY AS
SELECT DOMAIN, TERM, DEFINITION, LIFECYCLE, LINKED_ASSET, READ_AT FROM BID_GLOSSARY QUALIFY READ_AT = MAX(READ_AT) OVER ();

-- tab 5 Mapping: the pipeline step by step (what each IDMC object does), with the rows of the latest run
CREATE OR REPLACE VIEW BID_V_BI_PIPELINE AS
SELECT * FROM VALUES
  (1, '1 CRM Bid Documents', 'Mapping (CDI)', 'Salesforce Account + Files (every new version, bytes included)', 'BID_BRZ_SF_AGENCY, BID_BRZ_SF_DOCUMENT', 'Bronze'),
  (2, '1b Transfer to SharePoint', 'Mapping (CDI)', 'new documents -> one SharePoint folder per solicitation', 'SharePoint library + BID_BRZ_SP_TRANSFER', 'Bronze'),
  (3, '2a Read the Bid Packet', 'Mapping + CLAIRE model', 'PDF bytes -> Structure Parser (Bid packet model)', 'BID_BRZ_BID_PACKET', 'Bronze'),
  (4, '2b Read the Signature Page', 'Mapping + CLAIRE model', 'PDF bytes -> Structure Parser (Signature page model)', 'BID_BRZ_SIGNATURE_PAGE', 'Bronze'),
  (5, '3a Bid Lines Data Quality', 'Mapping + rule specifications', 'standardize, then price / decimals / brand rules', 'BID_SLV_BID_LINES', 'Silver'),
  (6, '3b Required Fields Data Quality', 'Mapping + rule specifications', 'filled in, e-mail format', 'BID_SLV_REQUIRED_FIELDS', 'Silver'),
  (7, '4 Bid Readiness', 'Mapping (CDI)', 'counts per document -> one decision', 'BID_GLD_READINESS', 'Gold'),
  (8, 'Run / Reset', 'Taskflows', 'the nightly batch, on demand; Reset puts the originals back first', 'all of the above', 'Orchestration')
  AS P(STEP, IDMC_OBJECT, KIND, WHAT_IT_DOES, WRITES, LAYER);

-- tab 6 Parsing: what CLAIRE read from each document in play
CREATE OR REPLACE VIEW BID_V_BI_PARSING AS
SELECT D.AGENCY, D.SOLICITATION_NO, D.DOC_TYPE, D.TITLE, D.VERSION_NUMBER, D.CONTENT_SIZE AS PDF_BYTES,
       IFF(D.DOC_TYPE = 'Bid packet', (SELECT COUNT(*) FROM BID_V_BID_PACKET_LATEST B WHERE B.CONTENT_VERSION_ID = D.CONTENT_VERSION_ID
                                        AND NULLIF(TRIM(B.ITEM_NO), '') IS NOT NULL),
           (SELECT COUNT(*) FROM BID_V_SIGNATURE_PAGE_LATEST S WHERE S.CONTENT_VERSION_ID = D.CONTENT_VERSION_ID)) AS ROWS_READ,
       IFF(D.DOC_TYPE = 'Bid packet', 'one row per bid-form line', 'one row: every vendor field') AS SHAPE,
       (SELECT COUNT(*) FROM BID_V_REQUIRED_FIELDS_SRC F WHERE F.CONTENT_VERSION_ID = D.CONTENT_VERSION_ID) AS REQUIRED_FIELDS_FOUND,
       D.LOADED_AT AS READ_FROM_CRM_AT
FROM BID_V_DOCUMENTS D;
