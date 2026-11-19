---
name: idmc-claire-mcp
description: Use for Informatica IDMC CLAIRE GPT and managed MCP servers: list and call the org's MCP servers, MCP OAuth clients, agent-style async orchestration and custom shims, CLAIRE prompting patterns, and choosing MCP vs REST.
---

# IDMC co-pilot: CLAIRE and MCP servers

Part of the **idmc-mp** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `idmc-mp` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/lessons/lessons.jsonl"` (this area: `"domain": "claire-mcp"`),
  then `knowledge/11-mcp-claire/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

## What users ask for
- Connect Claude to the org's managed MCP servers and call them.
- Decide whether a task should go through MCP or REST.
- "Is there an official plugin, MCP server or CLI for IDMC?" and "is this community tool safe to use?"
- Use CLAIRE GPT well.

## How to work
1. For the vendor's current catalog, read the public registry (no login, doc 01 §1a); then list the org's MCP registry
   and auth (docs 01-02) with `toolkit/lib/idmc_mcp.py`.
2. Pick MCP or REST per doc 05; MCP never replaces the Secure Agent.
3. Long-running work: the async orchestration pattern (doc 04).

## Read (in this order when unsure)
| Need | File |
|---|---|
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/11-mcp-claire/README.md` |
| Managed MCP servers: catalog and access | `knowledge/11-mcp-claire/01-managed-mcp-servers-catalog-access.md` |
| MCP auth and OAuth clients | `knowledge/11-mcp-claire/02-mcp-auth-oauth-clients.md` |
| CLAIRE GPT prompting | `knowledge/11-mcp-claire/03-claire-gpt-prompting-rules-patterns.md` |
| Agent-style MCP and shims | `knowledge/11-mcp-claire/04-agent-style-mcp-async-orchestration-custom-shims.md` |
| MCP vs REST | `knowledge/11-mcp-claire/05-mcp-vs-rest-when-to-use-which.md` |
| Vendor Claude plugin, MCP registries, community CLIs and MCP servers | `knowledge/11-mcp-claire/07-ecosystem-plugins-registries-community-tools.md` |
| Someone else's public code for a route or pattern | `knowledge/reference/community-code-index.md` |
| MCP servers, actions and calls | `knowledge/reference/playbook/10-mcp.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_mcp.py`: managed MCP servers: registry, tools, calls

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/idmc-mp:save-lesson`. Never write inside the plugin folder.
