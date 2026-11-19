#!/bin/sh
# First start only (docker-entrypoint-initdb.d). Creates the login roles with passwords from the environment.
# The values never reach a command line (argv is visible in the process list): psql reads them from its own
# environment with \getenv (psql 15+; the image is postgres:16) and quotes them with format(%L). Nothing is echoed.
set -eu
: "${MBR_PGRST_AUTH_PASSWORD:?set MBR_PGRST_AUTH_PASSWORD}"
: "${MBR_CDI_PG_PASSWORD:?set MBR_CDI_PG_PASSWORD}"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d mbr <<'SQL'
\getenv api_pw MBR_PGRST_AUTH_PASSWORD
\getenv cdi_pw MBR_CDI_PG_PASSWORD
CREATE ROLE mbr_api_anon NOLOGIN;
SELECT format('CREATE ROLE mbr_api_login LOGIN NOINHERIT PASSWORD %L', :'api_pw') \gexec
GRANT mbr_api_anon TO mbr_api_login;
-- read-only role for the IDMC PostgreSQL connection (nightly batch; add REPLICATION for the optional CDC)
SELECT format('CREATE ROLE mbr_batch_reader LOGIN PASSWORD %L', :'cdi_pw') \gexec
SQL
echo "roles created: mbr_api_anon, mbr_api_login, mbr_batch_reader"
