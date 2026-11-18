-- Bid Desk 03: the views the IDMC mappings 3a / 3b / 4 read, and the Silver / Gold tables they write. Idempotent.
-- Regex patterns are dollar-quoted ($$...$$) so a backslash means what it means in a regex. The label patterns match the
-- synthetic sample PDFs (infra/make_sample_pdfs.py); adapt them when you parse other documents.
USE SCHEMA ${snowflake.database}.${snowflake.schema};

-- the newest CLAIRE reading of each document in play
CREATE OR REPLACE VIEW BID_V_BID_PACKET_LATEST AS
SELECT B.* FROM BID_BRZ_BID_PACKET B
WHERE B.CONTENT_VERSION_ID IN (SELECT CONTENT_VERSION_ID FROM BID_V_DOCUMENTS)
QUALIFY B.IDMC_RUN_ID = MAX(B.IDMC_RUN_ID) OVER (PARTITION BY B.CONTENT_VERSION_ID);

CREATE OR REPLACE VIEW BID_V_SIGNATURE_PAGE_LATEST AS
SELECT S.* FROM BID_BRZ_SIGNATURE_PAGE S
WHERE S.CONTENT_VERSION_ID IN (SELECT CONTENT_VERSION_ID FROM BID_V_DOCUMENTS)
QUALIFY S.IDMC_RUN_ID = MAX(S.IDMC_RUN_ID) OVER (PARTITION BY S.CONTENT_VERSION_ID);

-- all text CLAIRE exported for each document, one line break between blocks (the field extraction below reads it)
CREATE OR REPLACE VIEW BID_V_DOCUMENT_TEXT AS
SELECT CONTENT_VERSION_ID, 'Bid packet' AS DOC_TYPE,
       MAX(ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(TEXT_01, TEXT_02, TEXT_03, TEXT_04, TEXT_05, TEXT_06, TEXT_07, TEXT_08, TEXT_09,
           TEXT_10, TEXT_11, TEXT_12, TEXT_13, TEXT_14, TEXT_15, TEXT_16, TEXT_17, TEXT_18, TEXT_19, TEXT_20), CHAR(10))) AS ALL_TEXT
FROM BID_V_BID_PACKET_LATEST GROUP BY 1
UNION ALL
SELECT CONTENT_VERSION_ID, 'Signature page',
       ARRAY_TO_STRING(ARRAY_CONSTRUCT_COMPACT(TEXT_01, TEXT_02, TEXT_03, TEXT_04, TEXT_05, TEXT_06, TEXT_07, TEXT_08, TEXT_09,
           TEXT_10), CHAR(10)) || CHAR(10)
FROM BID_V_SIGNATURE_PAGE_LATEST;

-- one row per solicitation in play: what the agency requires, read from its own document
CREATE OR REPLACE VIEW BID_V_SOLICITATIONS AS
SELECT D.CONTENT_VERSION_ID, D.CONTENT_DOCUMENT_ID, D.VERSION_NUMBER, D.AGENCY, D.DOC_TYPE, D.SOLICITATION_NO, D.FILE_NAME, D.SP_FOLDER,
       D.SP_FILE_NAME, D.LOADED_AT AS READ_FROM_CRM_AT,
       IFF(D.DOC_TYPE = 'Bid packet',
           TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$Bid #[A-Z0-9-]+ (.*) Bid Proposal Page$$, 1, 1, 'e', 1)),
           TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$SOLICITATION TITLE:[ ]*(.*)[ ]+SOLICITATION #$$, 1, 1, 'e', 1))) AS SOLICITATION_TITLE,
       TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$Bid & Samples Due:[ ]*([0-9/]+ (at |by )?[0-9:]+ [AP]M)$$, 1, 1, 'e', 1)) AS BID_DUE,
       TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$Bid Opening:[ ]*([0-9/]+ (at )?[0-9:]+ [AP]M)$$, 1, 1, 'e', 1)) AS BID_OPENING,
       TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$Contract term:[ ]*(from [^\n]*)$$, 1, 1, 'e', 1)) AS CONTRACT_TERM,
       COALESCE((SELECT MAX(NULLIF(TRIM(B.PAYMENT_TERMS), '')) FROM BID_V_BID_PACKET_LATEST B WHERE B.CONTENT_VERSION_ID = D.CONTENT_VERSION_ID),
                TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$Payment Terms:[ ]*(Net [0-9]+)$$, 1, 1, 'e', 1)),
                IFF(D.DOC_TYPE = 'Signature page', 'NET (days) - the vendor fills it in', NULL)) AS PAYMENT_TERMS,
       TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$All prices are to be (F\.O\.B\. [^\n]*)$$, 1, 1, 'e', 1)) AS FOB,
       IFF(REGEXP_INSTR(T.ALL_TEXT, $$exempt from all State Sales Tax$$) > 0, 'Tax exempt: no state sales tax', NULL) AS TAX,
       IFF(REGEXP_INSTR(T.ALL_TEXT, $$Only TWO decimal places will be counted$$) > 0, 'Two decimals only: longer prices are rounded up', NULL) AS PRICE_RULE,
       IFF(REGEXP_INSTR(T.ALL_TEXT, $$Delivery will be expected within 30 days$$) > 0, 'Delivery within 30 days of the purchase order', NULL) AS DELIVERY_RULE,
       IFF(REGEXP_INSTR(T.ALL_TEXT, $$automatic rejection$$) > 0, 'Must be signed: an unsigned form is automatically rejected', NULL) AS SIGNATURE_RULE,
       IFF(REGEXP_INSTR(T.ALL_TEXT, $$Certified electronic digital signatures are acceptable$$) > 0, 'Certified electronic signatures only', NULL) AS E_SIGNATURE_RULE,
       IFF(REGEXP_INSTR(T.ALL_TEXT, $$W-9$$) > 0, 'W-9; 3 references for a new vendor; signed Bid Proposal Page', NULL) AS REQUIRED_ATTACHMENTS,
       TRIM(REGEXP_SUBSTR(T.ALL_TEXT, $$Email:[ ]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)$$, 1, 1, 'e', 1)) AS AGENCY_EMAIL
FROM BID_V_DOCUMENTS D JOIN BID_V_DOCUMENT_TEXT T ON T.CONTENT_VERSION_ID = D.CONTENT_VERSION_ID;

-- the response fields each solicitation requires, one row per field (mapping 3b checks them). A model field wins; the
-- label regex on the document text is the fallback when the model put that field into a text block.
CREATE OR REPLACE VIEW BID_V_REQUIRED_FIELDS_SRC AS
WITH S AS (
  SELECT S.*, D.SOLICITATION_NO AS SOL, T.ALL_TEXT AS X
  FROM BID_V_SIGNATURE_PAGE_LATEST S JOIN BID_V_DOCUMENTS D ON D.CONTENT_VERSION_ID = S.CONTENT_VERSION_ID
  JOIN BID_V_DOCUMENT_TEXT T ON T.CONTENT_VERSION_ID = S.CONTENT_VERSION_ID),
E AS (
  SELECT CONTENT_VERSION_ID, VERSION_NUMBER, AGENCY, SOL AS SOLICITATION_NO, 'Exhibit A - Signature Page' AS FORM_NAME,
         F.VALUE:N::NUMBER AS FIELD_NO, F.VALUE:L::VARCHAR AS FIELD_NAME, F.VALUE:V::VARCHAR AS RAW_VALUE, F.VALUE:M::NUMBER AS IS_EMAIL
  FROM S, LATERAL FLATTEN(INPUT => ARRAY_CONSTRUCT(
    OBJECT_CONSTRUCT_KEEP_NULL('N', 1, 'L', 'Company name', 'M', 0, 'V', COALESCE(NULLIF(TRIM(COMPANY_NAME), ''), REGEXP_SUBSTR(X, $$Company Name[^:]*:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 2, 'L', 'Address', 'M', 0, 'V', COALESCE(NULLIF(TRIM(ADDRESS), ''), REGEXP_SUBSTR(X, $$(^|\n)Address:[ ]*([^\n]*)$$, 1, 1, 'e', 2))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 3, 'L', 'City', 'M', 0, 'V', COALESCE(NULLIF(TRIM(CITY), ''), REGEXP_SUBSTR(X, $$(^|\n)City:[ ]*([^\n]*)$$, 1, 1, 'e', 2))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 4, 'L', 'State', 'M', 0, 'V', COALESCE(NULLIF(TRIM(STATE), ''), REGEXP_SUBSTR(X, $$(^|\n)State:[ ]*([^\n]*)$$, 1, 1, 'e', 2))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 5, 'L', 'Zip code', 'M', 0, 'V', COALESCE(NULLIF(TRIM(ZIP_CODE), ''), REGEXP_SUBSTR(X, $$Zip Code:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 6, 'L', 'Phone', 'M', 0, 'V', COALESCE(NULLIF(TRIM(PHONE), ''), REGEXP_SUBSTR(X, $$(^|\n)Phone:[ ]*([^\n]*)$$, 1, 1, 'e', 2))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 7, 'L', 'Company e-mail', 'M', 1, 'V', COALESCE(NULLIF(TRIM(COMPANY_EMAIL), ''), REGEXP_SUBSTR(X, $$Company E-Mail Address:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 8, 'L', 'Delivery (days after order)', 'M', 0, 'V', COALESCE(NULLIF(TRIM(DELIVERY_DAYS), ''), REGEXP_SUBSTR(X, $$Delivery will be completed in[^:]*:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 9, 'L', 'Payment terms (NET days)', 'M', 0, 'V', COALESCE(NULLIF(TRIM(PAYMENT_NET_DAYS), ''), REGEXP_SUBSTR(X, $$Payment Terms: NET \(days\):[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 10, 'L', 'Authorized representative', 'M', 0, 'V', COALESCE(NULLIF(TRIM(REP_NAME), ''), REGEXP_SUBSTR(X, $$Authorized Representative \(Print Name\):[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 11, 'L', 'Representative e-mail', 'M', 1, 'V', COALESCE(NULLIF(TRIM(REP_EMAIL), ''), REGEXP_SUBSTR(X, $$Authorized Representative Direct Email:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 12, 'L', 'Signature (certified e-signature)', 'M', 0, 'V', COALESCE(NULLIF(TRIM(SIGNATURE), ''), REGEXP_SUBSTR(X, $$AUTHORIZED REPRESENTATIVE SIGNATURE:[ ]*([^\n]*)$$, 1, 1, 'e', 1)))
  )) F),
B AS (
  SELECT B.CONTENT_VERSION_ID, MAX(B.VERSION_NUMBER) VERSION_NUMBER, MAX(B.AGENCY) AGENCY, MAX(D.SOLICITATION_NO) SOLICITATION_NO,
         MAX(T.ALL_TEXT) X, MAX(B.COMPANY_BIDDER) COMPANY_BIDDER, MAX(B.BID_CONTACT) BID_CONTACT, MAX(B.BID_CONTACT_EMAIL) BID_CONTACT_EMAIL,
         MAX(B.BID_CONTACT_PHONE) BID_CONTACT_PHONE, MAX(B.SALES_CONTACT) SALES_CONTACT, MAX(B.SERVICE_CONTACT) SERVICE_CONTACT,
         MAX(B.TIME_TO_DELIVER) TIME_TO_DELIVER, MAX(B.SIGNATURE) SIGNATURE
  FROM BID_V_BID_PACKET_LATEST B JOIN BID_V_DOCUMENTS D ON D.CONTENT_VERSION_ID = B.CONTENT_VERSION_ID
  JOIN BID_V_DOCUMENT_TEXT T ON T.CONTENT_VERSION_ID = B.CONTENT_VERSION_ID GROUP BY 1),
P AS (
  SELECT CONTENT_VERSION_ID, VERSION_NUMBER, AGENCY, SOLICITATION_NO, 'Bid Proposal Page' AS FORM_NAME,
         F.VALUE:N::NUMBER AS FIELD_NO, F.VALUE:L::VARCHAR AS FIELD_NAME, F.VALUE:V::VARCHAR AS RAW_VALUE, F.VALUE:M::NUMBER AS IS_EMAIL
  FROM B, LATERAL FLATTEN(INPUT => ARRAY_CONSTRUCT(
    OBJECT_CONSTRUCT_KEEP_NULL('N', 1, 'L', 'Company / bidder', 'M', 0, 'V', COALESCE(NULLIF(TRIM(COMPANY_BIDDER), ''), REGEXP_SUBSTR(X, $$Company / Bidder:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 2, 'L', 'Bid contact', 'M', 0, 'V', COALESCE(NULLIF(TRIM(BID_CONTACT), ''), REGEXP_SUBSTR(X, $$Bid Contact:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 3, 'L', 'Bid contact e-mail', 'M', 1, 'V', COALESCE(NULLIF(TRIM(BID_CONTACT_EMAIL), ''), REGEXP_SUBSTR(X, $$Bid Contact Email:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 4, 'L', 'Bid contact phone', 'M', 0, 'V', COALESCE(NULLIF(TRIM(BID_CONTACT_PHONE), ''), REGEXP_SUBSTR(X, $$Bid Contact Phone:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 5, 'L', 'Sales contact', 'M', 0, 'V', COALESCE(NULLIF(TRIM(SALES_CONTACT), ''), REGEXP_SUBSTR(X, $$Sales Contact:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 6, 'L', 'Customer service contact', 'M', 0, 'V', COALESCE(NULLIF(TRIM(SERVICE_CONTACT), ''), REGEXP_SUBSTR(X, $$Customer Service Contact:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 7, 'L', 'Time to deliver', 'M', 0, 'V', COALESCE(NULLIF(TRIM(TIME_TO_DELIVER), ''), REGEXP_SUBSTR(X, $$Time to Deliver:[ ]*([^\n]*)$$, 1, 1, 'e', 1))),
    OBJECT_CONSTRUCT_KEEP_NULL('N', 8, 'L', 'Signature of company official', 'M', 0, 'V', COALESCE(NULLIF(TRIM(SIGNATURE), ''), REGEXP_SUBSTR(X, $$Signature of Company Official:[ ]*([^\n]*)$$, 1, 1, 'e', 1)))
  )) F)
SELECT SOLICITATION_NO, AGENCY, FORM_NAME, FIELD_NO, FIELD_NAME, TRIM(REGEXP_REPLACE(COALESCE(RAW_VALUE, ''), $$\s+$$, ' ')) AS FIELD_VALUE,
       IFF(IS_EMAIL = 1, TRIM(REGEXP_REPLACE(COALESCE(RAW_VALUE, ''), $$\s+$$, ' ')), NULL) AS EMAIL_VALUE, CONTENT_VERSION_ID, VERSION_NUMBER
FROM E
UNION ALL
SELECT SOLICITATION_NO, AGENCY, FORM_NAME, FIELD_NO, FIELD_NAME, TRIM(REGEXP_REPLACE(COALESCE(RAW_VALUE, ''), $$\s+$$, ' ')),
       IFF(IS_EMAIL = 1, TRIM(REGEXP_REPLACE(COALESCE(RAW_VALUE, ''), $$\s+$$, ' ')), NULL), CONTENT_VERSION_ID, VERSION_NUMBER
FROM P;

-- the bid-form lines as mapping 3a reads them
CREATE OR REPLACE VIEW BID_V_BID_LINES_SRC AS
SELECT D.SOLICITATION_NO, B.AGENCY, B.CONTENT_VERSION_ID, B.VERSION_NUMBER, B.ITEM_NO, B.ITEM_DESCRIPTION, B.UNIT, B.QTY_NEEDED,
       B.CURRENT_PRODUCT, B.BID_NOTES, B.UNIT_PRICE, B.BRAND_BID
FROM BID_V_BID_PACKET_LATEST B JOIN BID_V_DOCUMENTS D ON D.CONTENT_VERSION_ID = B.CONTENT_VERSION_ID
WHERE NULLIF(TRIM(B.ITEM_NO), '') IS NOT NULL;

-- Silver: every bid-form line, standardized and checked (mapping 3a, full reload via the writer's presql)
CREATE TABLE IF NOT EXISTS BID_SLV_BID_LINES (
  SOLICITATION_NO VARCHAR(40), AGENCY VARCHAR(255), CONTENT_VERSION_ID VARCHAR(18), VERSION_NUMBER VARCHAR(20), ITEM_NO VARCHAR(40),
  ITEM_DESCRIPTION VARCHAR(2000), UNIT VARCHAR(40), PACK_SIZE NUMBER(4, 0), QTY_NEEDED NUMBER(10, 0),
  CURRENT_PRODUCT_RAW VARCHAR(255), CURRENT_PRODUCT VARCHAR(255), CURRENT_BRAND VARCHAR(60), BID_NOTES VARCHAR(255),
  BRAND_PREFERRED VARCHAR(60), UNIT_PRICE_TEXT VARCHAR(40), UNIT_PRICE NUMBER(12, 2), LINE_VALUE NUMBER(14, 2), BRAND_BID VARCHAR(255),
  DQ_PRODUCT_ONE_LINE VARCHAR(10), DQ_PRICE_FILLED VARCHAR(10), DQ_PRICE_DECIMALS VARCHAR(10), DQ_BRAND_FILLED VARCHAR(10),
  LINE_STATUS VARCHAR(20), LINE_ISSUE VARCHAR(255), IDMC_RUN_ID VARCHAR(20), LOADED_AT TIMESTAMP_NTZ)
  COMMENT = 'Bid Desk Silver: the bid-form lines, product numbers standardized, the response checked by Data Quality rules';

-- Silver: every required response field, checked (mapping 3b, full reload)
CREATE TABLE IF NOT EXISTS BID_SLV_REQUIRED_FIELDS (
  SOLICITATION_NO VARCHAR(40), AGENCY VARCHAR(255), FORM_NAME VARCHAR(60), FIELD_NO NUMBER(4, 0), FIELD_NAME VARCHAR(60),
  FIELD_VALUE VARCHAR(2000), EMAIL_VALUE VARCHAR(255), DQ_FILLED VARCHAR(10), DQ_EMAIL_FORMAT VARCHAR(10), FIELD_STATUS VARCHAR(20),
  CONTENT_VERSION_ID VARCHAR(18), VERSION_NUMBER VARCHAR(20), IDMC_RUN_ID VARCHAR(20), LOADED_AT TIMESTAMP_NTZ)
  COMMENT = 'Bid Desk Silver: the response fields each solicitation requires, filled in or not, checked by Data Quality rules';

-- Gold: one bid-readiness decision per solicitation (mapping 4, full reload)
CREATE TABLE IF NOT EXISTS BID_GLD_READINESS (
  SOLICITATION_NO VARCHAR(40), AGENCY VARCHAR(255), DOC_TYPE VARCHAR(40), SOLICITATION_TITLE VARCHAR(255), BID_DUE VARCHAR(40),
  LINES NUMBER(6, 0), LINES_PRICED NUMBER(6, 0), LINES_TO_PRICE NUMBER(6, 0), LINES_TO_FIX NUMBER(6, 0), PRICES_3_DECIMALS NUMBER(6, 0),
  LINES_NO_BRAND NUMBER(6, 0), REQUIRED_FIELDS NUMBER(6, 0), FIELDS_FILLED NUMBER(6, 0), FIELDS_BLANK NUMBER(6, 0),
  FIELDS_INVALID NUMBER(6, 0), DQ_CHECKS NUMBER(8, 0), DQ_PASSED NUMBER(8, 0), DQ_SCORE NUMBER(5, 1), BID_VALUE NUMBER(14, 2),
  DECISION VARCHAR(40), DETAIL VARCHAR(400), SORT_ORDER NUMBER(4, 0), CONTENT_VERSION_ID VARCHAR(18), VERSION_NUMBER VARCHAR(20),
  IDMC_RUN_ID VARCHAR(20), LOADED_AT TIMESTAMP_NTZ)
  COMMENT = 'Bid Desk Gold: one bid-readiness decision per public-sector solicitation, for the sales desk in Tableau';

-- the Data Profiling scorecard (bid_dq.py land): one row per rule occurrence per profile run, as IDMC counted it
CREATE TABLE IF NOT EXISTS BID_DQ_SCORECARD (
  READ_AT TIMESTAMP_NTZ, SOURCE VARCHAR(20), PROFILE_NAME VARCHAR(200), RUN_REF VARCHAR(60), TABLE_NAME VARCHAR(100), COLUMN_NAME VARCHAR(100),
  RULE_SPEC VARCHAR(200), RULE_FRS_ID VARCHAR(40), DIMENSION VARCHAR(40), CHECKED NUMBER(10, 0), PASSED NUMBER(10, 0), FAILED NUMBER(10, 0),
  SCORE_PCT NUMBER(5, 1))
  COMMENT = 'Bid Desk: the IDMC Data Profiling scorecard (rule occurrences VALID / INVALID as IDMC counted them)';

-- the Silver bid lines the 'standardized' profile reads (the checked columns, as text)
CREATE OR REPLACE VIEW BID_V_BID_LINES_DQ AS
SELECT SOLICITATION_NO, CONTENT_VERSION_ID, ITEM_NO, UNIT, CURRENT_PRODUCT, UNIT_PRICE_TEXT, BRAND_BID, LINE_STATUS FROM BID_SLV_BID_LINES;
