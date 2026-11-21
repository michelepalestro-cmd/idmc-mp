---
description: Turn your org's Informatica MCP servers into Claude Code tools (a scoped OAuth client, read-only by default), and test them
---

Use the idmc-claire-mcp skill. On Windows, use `python` (or `py`) where these steps say `python3`. Goal: the org's managed
MCP servers show up in Claude Code as `mcp__plugin_informatica-idmc-headless_idmc__*` tools, through the plugin's bridge
(`toolkit/lib/idmc_mcp_bridge.py`, started by the plugin), and one read-only call proves they work.

1. Prove the org: `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`. If it is not CONNECTED, run
   `/informatica-idmc-headless:connect` first. Never retry a rejected login. Note the org id it prints.
2. List what the org has: `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_mcp.py" servers`. An empty list or a 403
   means MCP is not switched on for this org or this user lacks the AI Agent Engineering privileges: say so, point to
   `knowledge/11-mcp-claire/01-managed-mcp-servers-catalog-access.md` §6, and stop. Do not invent servers.
3. Ask the user two things, with a recommendation:
   - **Which servers.** Recommend every server the org lists. Name any that need a product the org may not have
     (`searchcustomer` needs MDM, `policymanagement` needs Data Access Management, `ordermanagement` and
     `dataprovisioning` need Data Marketplace).
   - **Read-only or read and write.** Recommend read-only. Read and write also offers tools that run jobs, create or
     delete connections, users and policies; Claude Code still asks before each call.
4. If `~/.idmc_toolkit/mcp_client.env` already exists, a client was made before. Show
   `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_mcp.py" clients`, and with the user's yes, delete the old client
   (`client-delete <clientId> --execute --expect-org <orgIdV3>`) and move the old file aside
   (`mv ~/.idmc_toolkit/mcp_client.env ~/.idmc_toolkit/mcp_client.env.old`). Its secret cannot be read again.
5. Dry run, then create the client (the secret goes straight to a 0600 file and is never printed):
   `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_mcp.py" client-create --name claude-code-mcp --contexts <c1,c2,...>`
   then the same with `--execute --expect-org <orgIdV3>` (add `--allow-writes` only if the user chose read and write).
6. Test it before going further: `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_mcp_bridge.py" --check`. It must list
   each chosen server with its tools. A server shown as unavailable: report its message (a 401 or 403 usually means
   the user lacks that product or privilege) and continue with the rest.
7. Tell the user to restart Claude Code (or run `/mcp` and reconnect `plugin:informatica-idmc-headless:idmc`). Then call
   `idmc_mcp_status`, and make one read-only call on a server the org has: for example `logs_*` or `jobs_search_*`
   for recent jobs, `conn_list_connections`, or `addr_verify_address` on a test address. Show the answer.
8. Finish with: the org id, the servers connected, the mode (read-only or read and write), the tool count, and the
   proof call's result. Remind the user:
   - the client stores the password of the user who created it: after that password changes, run this command again;
   - tokens renew by themselves (24 h); MCP calls use the org's IPUs like any other call;
   - use MCP or REST per task (`knowledge/11-mcp-claire/05-mcp-vs-rest-when-to-use-which.md`): the toolkit's REST
     scripts are still the way to build mappings, deploy CDC, publish CAI, profile data and do bulk work.
