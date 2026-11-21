---
name: idmc-cai
description: Use for Informatica IDMC Cloud Application Integration: author, publish, unpublish and invoke CAI processes, service and app connections (e.g. Salesforce OAuth), Process Server on a Secure Agent, Kafka/AMQP/JMS event listeners, and stuck or failing CAI assets. Also for APIs, webhooks, real-time or event-driven integration in Informatica.
---

# IDMC co-pilot: Application Integration (CAI): processes, connectors, events

Part of the **informatica-idmc-headless** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `informatica-idmc-headless` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (this area: `"domain": "cai"`),
  then `knowledge/07-app-integration/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

## What users ask for
- Publish a process that does X when an event or API call arrives.
- Wire CAI to Kafka, AMQP/JMS or a SaaS app.
- Unstick an asset that will not publish or unpublish.

## How to work
1. Authoring is mostly package-based: clone a working asset or import a package (doc 01).
2. Publish with `toolkit/lib/idmc_cai_publish.py`; invoke and check the run (doc 02).
3. Connections and OAuth (doc 03); Process Server on the agent if the process must run there (doc 04).
4. Events: listeners per doc 06. Stuck assets: doc 05.

## Read (in this order when unsure)
| Need | File |
|---|---|
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/07-app-integration/README.md` |
| Asset lifecycle | `knowledge/07-app-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md` |
| Runtime: invoke, URLs, control | `knowledge/07-app-integration/02-cai-runtime-invoke-urls-control.md` |
| Connections and connectors | `knowledge/07-app-integration/03-cai-connections-connectors-salesforce-oauth.md` |
| Process Server on a Secure Agent | `knowledge/07-app-integration/04-process-server-on-a-secure-agent.md` |
| Troubleshooting and stuck assets | `knowledge/07-app-integration/05-cai-troubleshooting-stuck-assets.md` |
| Event listeners: Kafka, AMQP, JMS | `knowledge/07-app-integration/06-cai-event-listeners-kafka-amqp-jms.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_cai_publish.py`: publish / unpublish CAI assets
- `toolkit/lib/idmc_export_import.py`: export and import packages (authoring by package)

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `knowledge/lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/informatica-idmc-headless:save-lesson`. Never write inside the plugin folder.
