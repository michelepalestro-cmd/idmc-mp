-- Retail Data Foundation: warehouse datasets and tables (BigQuery standard SQL). Rendered by infra/bq_setup.py
-- (${...} come from config.json + .env). The mappings write with Bulk + Write truncate into PRE-CREATED tables:
-- a column added later must also be added here (and the spec's field list refreshed), or it lands NULL silently.
-- Database Ingestion creates the ${DS_CDC} tables itself.

CREATE SCHEMA IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}` OPTIONS (location = '${BQ_LOCATION}');
CREATE SCHEMA IF NOT EXISTS `${WH_PROJECT}.${DS_STAGING}` OPTIONS (location = '${BQ_LOCATION}');
CREATE SCHEMA IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}` OPTIONS (location = '${BQ_LOCATION}');
CREATE SCHEMA IF NOT EXISTS `${WH_PROJECT}.${DS_CDC}` OPTIONS (location = '${BQ_LOCATION}');

-- landing (typed copies of the source tables, written by m_rdf_ingest_customers / m_rdf_ingest_activity)
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.stores` (
  store_id INT64, store_code STRING, name STRING, city STRING, state STRING, opened_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.products` (
  product_id INT64, sku STRING, name STRING, category STRING, unit_price NUMERIC);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.customers` (
  customer_id INT64, full_name STRING, email STRING, phone STRING, address STRING, city STRING, state STRING,
  zip STRING, tier STRING, signup_channel STRING, home_store_code STRING, crm_id STRING,
  created_at TIMESTAMP, updated_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.memberships` (
  membership_id INT64, customer_id INT64, tier STRING, status STRING, monthly_price NUMERIC,
  started_at TIMESTAMP, cancelled_at TIMESTAMP, updated_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.orders` (
  order_id INT64, customer_id INT64, store_code STRING, channel STRING, status STRING, list_amount NUMERIC,
  discount NUMERIC, amount NUMERIC, ordered_at TIMESTAMP, updated_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.order_lines` (
  order_line_id INT64, order_id INT64, product_id INT64, qty INT64, unit_price NUMERIC, line_amount NUMERIC);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.payments` (
  payment_id INT64, customer_id INT64, order_id INT64, membership_id INT64, kind STRING, amount NUMERIC,
  status STRING, processor STRING, paid_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_LAND}.visits` (
  visit_id INT64, customer_id INT64, store_code STRING, check_in_at TIMESTAMP, check_out_at TIMESTAMP, status STRING);

-- staging (m_rdf_customer_golden)
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_STAGING}.stg_customers` (
  customer_id INT64, full_name STRING, email STRING, phone_digits STRING, phone_e164 STRING, address STRING,
  city STRING, state STRING, zip STRING, tier STRING, signup_channel STRING, home_store_code STRING, crm_id STRING,
  created_at TIMESTAMP, email_valid INT64, phone_valid INT64, has_address INT64, tier_valid INT64,
  person_key STRING, dq_score FLOAT64, dq_valid INT64);

-- gold
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.customer_golden` (
  customer_id INT64, full_name STRING, email STRING, phone_e164 STRING, address STRING, city STRING, state STRING,
  zip STRING, tier STRING, signup_channel STRING, home_store_code STRING, dq_score FLOAT64, dq_valid INT64,
  merged_count INT64, first_signed_up_at TIMESTAMP, dq_status STRING, golden_built_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.customer_review` (
  customer_id INT64, full_name STRING, email STRING, phone_e164 STRING, address STRING, city STRING, state STRING,
  zip STRING, tier STRING, signup_channel STRING, home_store_code STRING, dq_score FLOAT64, dq_valid INT64,
  merged_count INT64, first_signed_up_at TIMESTAMP, dq_status STRING, golden_built_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.dq_results` (
  rule STRING, dimension STRING, table_name STRING, checked INT64, failed INT64, pass_rate FLOAT64, run_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.dq_scorecard` (
  dimension STRING, rules INT64, checked INT64, failed INT64, pass_rate FLOAT64, status STRING, run_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.order_line_facts` (
  order_line_id INT64, order_id INT64, customer_id INT64, store_code STRING, channel STRING, order_status STRING,
  order_day TIMESTAMP, product_id INT64, sku STRING, category STRING, qty INT64, unit_price NUMERIC,
  line_amount NUMERIC);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.store_daily_sales` (
  store_code STRING, order_day TIMESTAMP, lines INT64, units INT64, revenue NUMERIC);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.visit_facts` (
  visit_id INT64, customer_id INT64, store_code STRING, check_in_at TIMESTAMP, check_out_at TIMESTAMP,
  minutes INT64, status STRING);
CREATE TABLE IF NOT EXISTS `${WH_PROJECT}.${DS_GOLD}.address_verification` (
  customer_id INT64, addr_hash STRING, status STRING, checked_at TIMESTAMP, first_checked_at TIMESTAMP);

-- serving view for BI: the latest scorecard with a plain-language label
CREATE OR REPLACE VIEW `${WH_PROJECT}.${DS_GOLD}.v_dq_scorecard` AS
SELECT dimension, rules, checked, failed, pass_rate, status,
       CASE status WHEN 'green' THEN 'healthy' WHEN 'amber' THEN 'watch' ELSE 'action needed' END AS label, run_at
FROM `${WH_PROJECT}.${DS_GOLD}.dq_scorecard`;
