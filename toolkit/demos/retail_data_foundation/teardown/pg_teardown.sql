-- Undo infra/sql/02_cdc_prereqs.sql. STOP and UNDEPLOY both Database Ingestion jobs first (teardown.py run --only cdc),
-- or the slots are active and cannot be dropped. Never drop a slot that another task still uses: when a CDC slot
-- moves to another task or org, STOP the old job (do not undeploy) and roll back with "stop new, resume old".
--   psql -U <PG_USER> -d <PG_DB> -v cdc_user=rdf_cdc -v owner=<PG_USER> -f teardown/pg_teardown.sql

SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name IN ('rdf_cdc_hot', 'rdf_cdc_cold');
DROP PUBLICATION IF EXISTS rdf_cdc_pub_hot;
DROP PUBLICATION IF EXISTS rdf_cdc_pub_cold;
ALTER TABLE public.customers   REPLICA IDENTITY DEFAULT;
ALTER TABLE public.memberships REPLICA IDENTITY DEFAULT;
ALTER TABLE public.orders      REPLICA IDENTITY DEFAULT;
ALTER TABLE public.payments    REPLICA IDENTITY DEFAULT;
ALTER TABLE public.visits      REPLICA IDENTITY DEFAULT;
ALTER TABLE public.stores      REPLICA IDENTITY DEFAULT;
ALTER TABLE public.products    REPLICA IDENTITY DEFAULT;
ALTER TABLE public.order_lines REPLICA IDENTITY DEFAULT;
-- the persistence tables the CDC tasks created themselves (one per job)
DO $$ DECLARE t text; BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'infa_persistent_%' LOOP
    EXECUTE format('DROP TABLE IF EXISTS public.%I', t);
  END LOOP; END $$;
REASSIGN OWNED BY :"cdc_user" TO :"owner";
DROP OWNED BY :"cdc_user";
DROP ROLE IF EXISTS :"cdc_user";
