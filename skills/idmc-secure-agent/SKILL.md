---
name: idmc-secure-agent
description: Use for Informatica IDMC Secure Agent and runtime environment work: install or register an agent headless, run it as a service, size and tune it (memory, heap, DTM pool, two agents on a host), pick the services and connectors a runtime environment needs, and fix agent or engine errors. For creating or fixing connections use idmc-connections. Also for setting up the agent that runs Informatica jobs on a server or VM.
---

# IDMC co-pilot: Secure Agent and runtime environments

Part of the **informatica-idmc-headless** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `informatica-idmc-headless` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (this area: `"domain": "agent"`),
  then `knowledge/02-secure-agent/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

## What users ask for
- Stand up a Secure Agent on a VM and register it to the right org, headless.
- Make it survive reboots and restarts (service unit, orphan reaping, port guards).
- Tune it: memory, heap, disk, DTM pool and concurrency, or split work across two agents.
- Turn on only the services and connectors the pipelines need.

## How to work
1. Prove the org; list runtime environments and agents read-only (`/informatica-idmc-headless:health-check` does this).
2. Install/register: installer URL and org-scoped token from the v2 route (save it with `idmc_session.py get ... --save-to`,
   since printing hides it), then the host steps in doc 01 section 3.
3. Run as a service (doc 01 section 4); check the post-boot checklist after any resize or reboot.
4. Select services and connectors with `toolkit/lib/idmc_runtime_selections.py`
   (`02-runtime-environments-services-connectors.md`): only what is needed.
5. Connections: hand over to the `idmc-connections` skill.
6. Tuning: measure first (DTM pool, memory, heap per doc 01 sections 5-6 and `04-mappings/06-performance-concurrency-job-caps.md`
   section 6.1), change one thing, re-measure. Change settings in the UI first, `agent.do` last (doc 01 §6.1).
7. Errors: walk the four gates in order (`03-connections/03-troubleshooting-the-four-gates.md`): host, engine, adapter, driver.

## Read (in this order when unsure)
| Need | File |
|---|---|
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/02-secure-agent/README.md` |
| Install, service, tuning, two agents, memory | `knowledge/02-secure-agent/01-secure-agent-install-run-tune.md` |
| Services and connectors on a runtime environment | `knowledge/02-secure-agent/02-runtime-environments-services-connectors.md` |
| Troubleshooting: the four gates, zero to a running job (HOST -> ENGINE -> ADAPTER -> DRIVER) | `knowledge/03-connections/03-troubleshooting-the-four-gates.md` |
| Concurrency and the DTM pool | `knowledge/04-mappings/06-performance-concurrency-job-caps.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_session.py`: org-aware session, read-only from the command line: `whoami`, `hosts`, `get <plane> <path>`
  (`--save-to <file>` keeps a secret such as the install token out of the output)
- `toolkit/lib/idmc_runtime_selections.py`: services and connectors of a runtime environment
- `toolkit/lib/idmc_probe.py`: route discovery that cannot fool itself (bogus-twin check)
- MCP tools, when `/informatica-idmc-headless:connect-mcp` has connected the org's servers (`mcp__plugin_informatica-idmc-headless_idmc__*`): `agent_*` (agents,
  runtime environments; selection changes only when the client allows writes), `trouble_*` (agent health)

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `knowledge/lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/informatica-idmc-headless:save-lesson`. Never write inside the plugin folder.
