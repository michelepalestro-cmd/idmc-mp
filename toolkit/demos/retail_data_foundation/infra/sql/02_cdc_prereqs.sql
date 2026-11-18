-- Retail Data Foundation: PostgreSQL prerequisites for IDMC Database Ingestion CDC (pgoutput), hot + cold tasks.
-- PROVEN pattern (a production demo, 2026-09): two CDC tasks, each with its OWN slot and publication.
-- Run as the database owner, passing the CDC role's login secret as a psql variable (never type it into this file):
--   psql -U <PG_USER> -d <PG_DB> -v cdc_user=rdf_cdc -v cdc_pw="$PG_CDC_PASS" -v owner=<PG_USER> -f 02_cdc_prereqs.sql
--
-- Rules learned the hard way (each failed a job until fixed):
--   1. the task CREATEs public.infa_persistent_<job> itself        -> the CDC role needs CREATE on schema public
--   2. that persistence table must NOT be in any publication       -> never create a FOR ALL TABLES publication
--   3. every captured table must be REPLICA IDENTITY FULL           -> ALTER TABLE ... REPLICA IDENTITY FULL
--   4. create each slot AFTER its publication (pgoutput decodes with the historic catalog)
--   5. two CDC tasks can never share a slot; an idle slot retains WAL (max_slot_wal_keep_size caps it)
--   6. the role needs REPLICATION + SELECT only (no DML)
-- pg_hba.conf (in the data directory): allow  host replication <cdc_user> <agent network> scram-sha-256
--   and     host <db> <cdc_user> <agent network> scram-sha-256

CREATE ROLE :"cdc_user" LOGIN REPLICATION;
-- the login secret comes in as a psql variable and is quoted by format(), so this file holds no secret
-- (switch off log_statement = all / ddl while running it if your server logs DDL)
SELECT format('ALTER ROLE %I PASSWORD %L', :'cdc_user', :'cdc_pw') \gexec
GRANT CONNECT ON DATABASE :"DBNAME" TO :"cdc_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"cdc_user";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"cdc_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT SELECT ON TABLES TO :"cdc_user";

-- HOT task: high-churn tables, apply cycle 5 s, flush 2 s
CREATE PUBLICATION rdf_cdc_pub_hot FOR TABLE
  public.customers, public.memberships, public.orders, public.payments, public.visits;
-- COLD task: reference / low-churn tables, apply cycle 10 s, flush 5 s
CREATE PUBLICATION rdf_cdc_pub_cold FOR TABLE
  public.stores, public.products, public.order_lines;

ALTER TABLE public.customers   REPLICA IDENTITY FULL;
ALTER TABLE public.memberships REPLICA IDENTITY FULL;
ALTER TABLE public.orders      REPLICA IDENTITY FULL;
ALTER TABLE public.payments    REPLICA IDENTITY FULL;
ALTER TABLE public.visits      REPLICA IDENTITY FULL;
ALTER TABLE public.stores      REPLICA IDENTITY FULL;
ALTER TABLE public.products    REPLICA IDENTITY FULL;
ALTER TABLE public.order_lines REPLICA IDENTITY FULL;

SELECT pg_create_logical_replication_slot('rdf_cdc_hot', 'pgoutput');
SELECT pg_create_logical_replication_slot('rdf_cdc_cold', 'pgoutput');

-- Check:  SELECT slot_name, active, restart_lsn FROM pg_replication_slots;   (a polling job shows active=f between cycles)
-- ROLLBACK is teardown/pg_teardown.sql (stop + undeploy both DBMI jobs FIRST, or the slots are busy).
