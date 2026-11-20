# Bid Desk: .env keys (names only, never values)

Section header for toolkit/setup/.env.example: `# [bid_desk_document_parsing]`

IDMC_USER - (goes in IDMC_LOGIN.txt, not the .env) IDMC login name (org admin, or Designer + Operator + Admin privileges) - your IDMC org administrator
IDMC_PASS - (IDMC_LOGIN.txt) that user's IDMC login - your IDMC org administrator
IDMC_LOGIN_HOST - (IDMC_LOGIN.txt) the DOMAIN login host of your region, e.g. dm-us.informaticacloud.com - the address bar after you sign in to IDMC (drop the pod label)
SF_USERNAME - Salesforce integration user for the IDMC Salesforce connection - Salesforce Setup > Users
SF_PASSWORD - that Salesforce user's login - Salesforce Setup > Users (reset if unknown)
SF_SECURITY_TOKEN - the user's security token; empty when the agent's IP is in the org's trusted ranges - Salesforce: avatar > Settings > Reset My Security Token
SF_INSTANCE_URL - the org's My Domain URL, e.g. https://<mydomain>.my.salesforce.com - Salesforce Setup > My Domain
SF_CLIENT_ID - consumer key of a Connected App with the client-credentials flow (file seed / what-if / reset / staging) - Salesforce Setup > App Manager > your Connected App > Manage Consumer Details
SF_CLIENT_SECRET - consumer secret of that Connected App - same page as SF_CLIENT_ID
SNOWFLAKE_USER - Snowflake service user for IDMC (key-pair auth) - Snowflake: CREATE USER (infra/snowflake/01_cost_guard_and_access.sql)
SNOWFLAKE_PAT - Snowflake programmatic access token for the SQL API (setup SQL, verify, feeds) - Snowsight > your user > Programmatic access tokens
SNOWFLAKE_BI_USER - read-only Snowflake user embedded in the Tableau data sources - Snowflake: CREATE USER with role BID_READER
SNOWFLAKE_BI_PASSWORD - that read-only user's login - set when you create the user
ENTRA_TENANT_ID - Microsoft Entra tenant id (GUID) - Entra admin center > Overview
ENTRA_CLIENT_ID - application (client) id of the Entra app registration for IDMC SharePoint - Entra admin center > App registrations > your app > Overview
ENTRA_CLIENT_SECRET - a client secret of that app - Entra admin center > App registrations > your app > Certificates & secrets
SHAREPOINT_REFRESH_TOKEN - delegated refresh token minted for the SharePoint audience (not Graph), after admin consent - infra/sharepoint_setup.py token-url, sign in once, redeem the code (BUILD step 5)
TABLEAU_PAT_NAME - Tableau personal access token name - Tableau: My Account Settings > Personal Access Tokens
TABLEAU_PAT_SECRET - Tableau personal access token secret - same page (shown once)
