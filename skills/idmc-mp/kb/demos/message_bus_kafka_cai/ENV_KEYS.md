# [message_bus_kafka_cai] keys for setup/.env.example

IDMC_USER - (goes in IDMC_LOGIN.txt, not the .env) IDMC login name (Designer + Operator + Admin privileges in the target org) - your IDMC administrator
IDMC_PASS - (IDMC_LOGIN.txt) that login's password - your IDMC administrator (one rejected login writes a block file)
IDMC_LOGIN_HOST - (IDMC_LOGIN.txt) the domain login host, e.g. dm-us.informaticacloud.com - the URL you sign in at, without the pod label
MBR_PG_USER - Postgres superuser name for the stand-in ops ledger container (mbr-pg) - you choose it before `docker compose up`
MBR_PG_PASSWORD - that Postgres user's password - you choose it (generate a long random string)
MBR_PGRST_AUTH_PASSWORD - password of the login role `mbr_api_login` that PostgREST uses (created by infra/postgres SQL) - you choose it
MBR_CDI_PG_PASSWORD - password of the read-only role `mbr_batch_reader` that the IDMC PostgreSQL connection uses - you choose it
MBR_ARTEMIS_USER - ActiveMQ Artemis user for the legacy JMS stand-in and the CAI AMQP connection - you choose it
MBR_ARTEMIS_PASSWORD - that Artemis user's password (set into CAI with asset/v1/update, never in a package) - you choose it
MBR_ORACLE_PASSWORD - SYS/SYSTEM password of the Oracle Free container (mbr-oracle) - you choose it
MBR_ORACLE_BATCH_PASSWORD - password of the Oracle schema user MBR_BATCH (the nightly CDI target) - you choose it
MBR_KAFKA_CLUSTER_ID - KRaft cluster id (22-char base64 UUID) - generate once: `docker run --rm apache/kafka:4.3.1 /opt/kafka/bin/kafka-storage.sh random-uuid`
