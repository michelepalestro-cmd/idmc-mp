---
description: Connect Claude to your IDMC org (login file outside the plugin) and prove which org it is
---

Use the idmc-mp skill. On Windows, use `python` (or `py`) where these steps say `python3`. Goal: the user is connected to their IDMC org and the org is proven.

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` once.
2. If it just created `~/.idmc_toolkit/IDMC_LOGIN.txt`, tell the user to fill in `IDMC_USER` and `IDMC_PASS` of a
   **native** IDMC user (SSO-only users cannot log in over REST) and `IDMC_LOGIN_HOST` (the browser address after they
   sign in), then stop. If they give you the values, write them only to that file and confirm with key names and a
   masked password, never the value.
3. If it logged in, report org name, org id, pod and base URL in one short block.
4. If the login was rejected, do NOT retry: repeated attempts lock the user. Check the login host first (a wrong
   domain label gives IDS_085, which looks like a bad password), then the file, and tell the user what to fix.
