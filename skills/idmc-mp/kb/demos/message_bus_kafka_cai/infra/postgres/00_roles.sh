#!/bin/sh
# First start only (docker-entrypoint-initdb.d). Creates the login roles with passwords from the environment;
# the values are passed as psql variables and never echoed.
set -eu
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d mbr \
     -v api_pw="$MBR_PGRST_AUTH_PASSWORD" -v cdi_pw="$MBR_CDI_PG_PASSWORD" <<'SQL'
CREATE ROLE mbr_api_anon NOLOGIN;
SELECT format('CREATE ROLE mbr_api_login LOGIN NOINHERIT PASSWORD %L', :'api_pw') \gexec
GRANT mbr_api_anon TO mbr_api_login;
-- read-only role for the IDMC PostgreSQL connection (nightly batch; add REPLICATION for the optional CDC)
SELECT format('CREATE ROLE mbr_batch_reader LOGIN PASSWORD %L', :'cdi_pw') \gexec
SQL
echo "roles created: mbr_api_anon, mbr_api_login, mbr_batch_reader"
