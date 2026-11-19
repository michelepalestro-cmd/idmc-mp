# .env keys used by toolkit/demos/retail_data_foundation

Section header for toolkit/setup/.env.example: `# [retail_data_foundation]`. Values live only in the toolkit .env (outside the
toolkit folder), never in this blueprint.

- IDMC_USER - (goes in IDMC_LOGIN.txt, not the .env) IDMC user name with Designer + Operator + Admin rights in the target org - IDMC Administrator > Users (core key)
- IDMC_PASS - (IDMC_LOGIN.txt) that user's login secret - set by your IDMC admin (core key)
- IDMC_LOGIN_HOST - (IDMC_LOGIN.txt) the domain login host, e.g. dm-us.informaticacloud.com, never a pod host - the URL you log in at (core key)
- PG_HOST - host name or address the Secure Agent uses to reach the stand-in Postgres - 127.0.0.1 (the stand-in listens on loopback only; any other host gets TLS with certificate validation)
- PG_PORT - Postgres port as seen from the agent (default 5432) - infra/docker-compose.yml port mapping
- PG_DB - source database name (default rdf_retail) - infra/docker-compose.yml POSTGRES_DB
- PG_USER - application/owner role of the source database (default rdf_app) - infra/docker-compose.yml POSTGRES_USER
- PG_PASS - login secret of PG_USER - you choose it before `docker compose up`
- PG_CDC_USER - least-privilege replication role for Database Ingestion CDC (default rdf_cdc) - created by infra/sql/02_cdc_prereqs.sql
- PG_CDC_PASS - login secret of PG_CDC_USER - you choose it; psql reads it from its environment (\getenv in 02_cdc_prereqs.sql), never from the command line
- BQ_PROJECT - Google Cloud project id that holds the warehouse datasets - Google Cloud console project picker
- BQ_KEY_FILE - path (outside the toolkit) to the service-account JSON key used by the BigQuery V2 connections - IAM > Service accounts > Keys
- GCS_STAGING_BUCKET - bucket name (no gs://) for BigQuery bulk loads and CDC staging - Cloud Storage > Buckets
- SF_LOGIN_URL - Salesforce My Domain base URL, https://<my-domain>.my.salesforce.com - Salesforce Setup > My Domain
- SF_CLIENT_ID - consumer key of the Connected App (client-credentials flow) used by CAI - Setup > App Manager > your Connected App
- SF_CLIENT_SECRET - consumer secret of that Connected App - same page (Manage Consumer Details)
- SF_USERNAME - API-only integration user for the CDI Salesforce connection - Setup > Users
- SF_PASSWORD - that user's login secret - set when you create the user
- SF_SECURITY_TOKEN - that user's security token (may be empty from a trusted IP range) - Salesforce personal settings > Reset Security Token
- CAI_RT_BASE - optional: CAI runtime base URL of your org, https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/rt (the /active-bpel/public/rt/<orgIdV3> form only with the test-only cai.anonymous) - printed by idmc/05_cai.py url after publish
- RDF_CAI_USER - optional: native IDMC user that calls the CAI processes (Basic Authentication); list it in config.json cai.allowedUsers - IDMC Administrator > Users
- RDF_CAI_PASS - that user's login secret - set when you create the user
