-- Undo of infra/postgres (run by hand with psql; kept outside the init folder on purpose).
-- psql -U <MBR_PG_USER> -d mbr -v confirm=yes -f teardown/pg_undo.sql
\if :{?confirm}
DROP SCHEMA IF EXISTS mbr_api CASCADE;
DROP SCHEMA IF EXISTS mbr CASCADE;
DROP ROLE IF EXISTS mbr_api_login;
DROP ROLE IF EXISTS mbr_api_anon;
DROP ROLE IF EXISTS mbr_batch_reader;
\else
\echo 'skipped: pass -v confirm=yes to drop the mbr schemas and roles'
\endif
