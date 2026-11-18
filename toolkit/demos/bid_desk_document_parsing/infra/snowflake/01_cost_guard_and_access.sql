-- Bid Desk 01: warehouse, cost guard (resource monitor), database, schema, roles, users. Run as ACCOUNTADMIN, once.
-- The dollar-brace placeholders are filled from config.json by infra/snowflake_sql.py (or replace them by hand in a worksheet).
-- Why the guard matters: when the monitor hits its quota with SUSPEND, EVERY client of the warehouse fails at once with
-- 090073 "Warehouse cannot be resumed because resource monitor has exceeded its quota" (IDMC tasks, catalog profiling,
-- Tableau extract refreshes, the SQL API). Size the quota for builds + a catalog scan with profiling (KB L-ENV-096).
-- Raise it later with: ALTER RESOURCE MONITOR ${snowflake.monitor} SET CREDIT_QUOTA = <n>;

CREATE RESOURCE MONITOR IF NOT EXISTS ${snowflake.monitor}
  WITH CREDIT_QUOTA = ${snowflake.monthly_credit_quota} FREQUENCY = MONTHLY START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75 PERCENT DO NOTIFY ON 90 PERCENT DO NOTIFY ON 100 PERCENT DO SUSPEND;

CREATE WAREHOUSE IF NOT EXISTS ${snowflake.warehouse}
  WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
ALTER WAREHOUSE ${snowflake.warehouse} SET RESOURCE_MONITOR = ${snowflake.monitor};

CREATE DATABASE IF NOT EXISTS ${snowflake.database};
CREATE SCHEMA IF NOT EXISTS ${snowflake.database}.${snowflake.schema};

-- the IDMC role (writes Bronze / Silver / Gold) and a read-only role for Tableau and the catalog's profiling
CREATE ROLE IF NOT EXISTS ${snowflake.role};
CREATE ROLE IF NOT EXISTS BID_READER;
GRANT USAGE ON WAREHOUSE ${snowflake.warehouse} TO ROLE ${snowflake.role};
GRANT USAGE ON WAREHOUSE ${snowflake.warehouse} TO ROLE BID_READER;
GRANT USAGE ON DATABASE ${snowflake.database} TO ROLE ${snowflake.role};
GRANT USAGE ON DATABASE ${snowflake.database} TO ROLE BID_READER;
GRANT ALL ON SCHEMA ${snowflake.database}.${snowflake.schema} TO ROLE ${snowflake.role};
GRANT USAGE ON SCHEMA ${snowflake.database}.${snowflake.schema} TO ROLE BID_READER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA ${snowflake.database}.${snowflake.schema} TO ROLE BID_READER;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA ${snowflake.database}.${snowflake.schema} TO ROLE BID_READER;
-- MONITOR lets the build user SEE the guard (a role without it gets no rows from SHOW RESOURCE MONITORS)
GRANT MONITOR ON RESOURCE MONITOR ${snowflake.monitor} TO ROLE ${snowflake.role};

-- users: create them yourself so no secret lands in this file.
--   IDMC service user (key pair; put the PUBLIC key here, the private key file on the Secure Agent host):
--     CREATE USER IF NOT EXISTS <SNOWFLAKE_USER> DEFAULT_ROLE = ${snowflake.role} DEFAULT_WAREHOUSE = ${snowflake.warehouse}
--       RSA_PUBLIC_KEY = '<public key body>';
--     GRANT ROLE ${snowflake.role} TO USER <SNOWFLAKE_USER>;
--   Tableau read-only user: CREATE USER <SNOWFLAKE_BI_USER> ... DEFAULT_ROLE = BID_READER; GRANT ROLE BID_READER TO USER ...;
--   SQL API token for the build scripts: Snowsight > your user > Programmatic access tokens (role ${snowflake.role}).

SHOW RESOURCE MONITORS LIKE '${snowflake.monitor}';
