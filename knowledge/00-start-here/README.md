# Start here: what do you want to do?

Pick the job, open its cheat sheet, and you have what works, what does not, the fastest safe path and the traps that
cost other people days. Every cheat sheet cites its lessons (`L-<AREA>-###`); a lesson marked **(reported)** came from
someone else's public code and has not been proven live yet.

**Before anything else:** connect once with `/idmc-mp:connect` (setup in the root [README](../../README.md)), then run
`/idmc-mp:health-check` to see what your org has. Every write is a dry run until `--execute --expect-org <orgIdV3>`.

## I want to...

| I want to... | Command | Cheat sheet | Main tool |
|---|---|---|---|
| Log in, prove which org I am in, manage users and roles | `/idmc-mp:connect` | [01 Login & orgs](../01-login-and-orgs/README.md) | `toolkit/check_login.py` |
| Install, run or tune a Secure Agent; pick its services | `/idmc-mp:tune-agent` | [02 Secure Agent](../02-secure-agent/README.md) | `toolkit/lib/idmc_runtime_selections.py` |
| Connect to a database, warehouse, file store or app | | [03 Connections](../03-connections/README.md) | `toolkit/lib/idmc_session.py` |
| Build a mapping and its task, and run it | `/idmc-mp:new-pipeline` | [04 Mappings](../04-mappings/README.md) | `toolkit/mapgen/mapgen.py` |
| Chain tasks into a taskflow or put them on a schedule | | [05 Taskflows & schedules](../05-taskflows-schedules/README.md) | `toolkit/lib/idmc_taskflow_schedule.py` |
| Replicate a database or capture changes (CDC), ingest files | | [06 CDC & ingestion](../06-cdc-ingestion/README.md) | `toolkit/lib/idmc_dbmi.py` |
| Publish a CAI process, an API or an event listener | | [07 Application integration](../07-app-integration/README.md) | `toolkit/lib/idmc_cai_publish.py` |
| Profile data, add data quality rules, clean a dataset | `/idmc-mp:add-dq`, `/idmc-mp:clean-data` | [08 Data quality](../08-data-quality/README.md) | `toolkit/lib/idmc_objects.py` |
| Scan into the catalog; glossary, classification, lineage | `/idmc-mp:catalog` | [09 Catalog & lineage](../09-catalog-lineage/README.md) | `toolkit/lib/idmc_cdgc.py` |
| Master records into golden records (MDM) | | [10 MDM](../10-mdm/README.md) | `toolkit/lib/idmc_session.py` |
| Clean a messy customer CSV, dedupe it, give customer ids (no DQ or MDM licence) | | [Customer CSV blueprint](../../toolkit/demos/customer_master_csv/README.md) | `toolkit/demos/customer_master_csv/check.py` |
| Use Informatica's MCP servers or CLAIRE GPT | | [11 MCP & CLAIRE](../11-mcp-claire/README.md) | `toolkit/lib/idmc_mcp.py` |
| Promote dev to prod, migrate between orgs, clean up | `/idmc-mp:promote` | [12 Deploy & migrate](../12-deploy-migrate/README.md) | `toolkit/lib/idmc_export_import.py` |
| See and cut IPU cost, job caps | `/idmc-mp:ipu-report`, `/idmc-mp:optimize` | [13 IPU & cost](../13-ipu-cost/README.md) | `toolkit/lib/idmc_session.py` |
| Work safely and fast with Claude on IDMC | | [14 Working with Claude](../14-working-with-claude/README.md) | |
| Understand an error | `/idmc-mp:fix-error` | [Error triage](04-error-triage.md) | `knowledge/reference/playbook/06-lessons-field.md` |

## Whole journeys

- **First hour:** [Quick start](10-quick-start-your-first-hour-with-idmc-and-claude.md).
- **A new pipeline, any source to any target:** [New pipeline milestones](08-new-pipeline-milestones-any-source-any-target.md)
  (agent -> connections -> folder -> mapping -> task -> run and proof -> DQ -> orchestration -> governance).
- **Deploy and operate IDMC end to end:** [End-to-end playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md).
- **Taking over a live or inherited build:** [What went wrong in a production deployment](09-what-went-wrong-production-deployment-post-mortem.md).

## Always true

- [The laws of headless IDMC](02-the-laws-of-headless-idmc.md): a 200 can be fake, logins are scarce, read back every write.
- [Capability map](03-capability-map.md): can I do X without the UI, and how.
- [Glossary](05-glossary.md) and [how to use this knowledge base](01-how-to-use-this-kb.md).
- Search everything at once: `grep -i "<error or thing>" lessons/lessons.jsonl`.
