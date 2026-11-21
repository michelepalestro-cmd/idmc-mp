# Quick Start: your first hour with IDMC and Claude

**Answers:** What do I do in my first hour, what do I ask Claude, and which lessons trip up almost every new user?

**Read when:** right after installing the plugin and connecting (see [Setup and login](11-setup-and-login.md)).

For anyone who has just installed the skill or plugin and wants IDMC working. It covers what to do, what to ask
Claude, and the lessons that trip up almost every new user. Everything deeper is linked: the
[End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) (13 stages, deploy to day 2),
[New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md) and
[Error Triage](04-error-triage.md).

## 1. Before you start (5 minutes)

| You need | Why |
|---|---|
| An IDMC org you may write to | everything is built in your org; a trial org works but has a monthly job limit (L-IPU-041) |
| A **native** IDMC user and password | SSO-only users cannot log in over REST (L-AUTH-045). Create one automation user and use it for every session |
| The browser address you see after signing in to IDMC | it names your login host; the domain label (`dm-us`, `dmp-us`, ...) cannot be guessed (L-AUTH-004) |
| Python 3.10+ | the helper scripts are standard-library only |
| A Secure Agent, or the Hosted Agent | IDMC runs jobs on a runtime; on-premises or VPC sources need a Secure Agent (playbook stage 2) |

## 2. Connect and prove the org (10 minutes)

1. Type `/informatica-idmc-headless:connect` (or ask **"connect to my IDMC org"**). The first time, it creates your login file in
   `~/.idmc_toolkit/` and shows a `--setup` command: run that in a terminal window and answer three questions (the IDMC
   address from your browser, your user name, your password, which stays hidden). Then type `/informatica-idmc-headless:connect` again.
   It checks the file on your computer first and makes one login attempt at most; the
   [Setup and login](11-setup-and-login.md#if-the-login-doesnt-work) explains every login message in plain words.
2. Ask: **"prove which org we are in"**. Claude runs the three-call preflight (login, `GET /api/v2/org`,
   `GET /api/v2/agent`) and prints org name, id, pod and base URL (L-AUTH-018, L-AUTH-046).
3. Ask: **"health-check my org"**. That lists runtimes and agent health, connections, projects and which services the
   org can really run.

**One login per run.** Repeated failed logins lock the user, so a failed login means *check the host and the file*,
never "try again" (L-AUTH-041, L-AUTH-035). The helper scripts enforce this with a block file.

## 3. What to ask Claude, by task

Name your own systems. Claude builds with the source, target and connectors you name, and the KB's examples are not
recommendations.

| You want to | Ask Claude | Where it works from |
|---|---|---|
| Load a table from A to B | "build a mapping from my `<source>` `<table>` to `<target>`, run it and show me the row counts" | [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md), `toolkit/mapgen/` |
| A whole pipeline | "plan and build a pipeline from `<sources>` to `<target>`; tell me each milestone as you finish it" | [New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md) |
| Schedule it | "put these mapping tasks in a taskflow and schedule it daily at 02:00 my time" | [Taskflows & Schedules](../05-taskflows-schedules/01-taskflows-schedules.md) |
| Keep a target in sync (CDC) | "set up CDC from my `<database>` to `<target>`" | [knowledge/06-cdc-ingestion](../06-cdc-ingestion) |
| A connection | "create a `<type>` connection on my Secure Agent and test it with a real query" | [knowledge/03-connections](../03-connections/README.md) |
| Real-time / API | "publish a CAI process that `<does X>` when `<event>` and show me its endpoint" | [knowledge/07-app-integration](../07-app-integration) |
| Data quality | "profile `<table>`, suggest DQ rules, and add them to the pipeline" | [knowledge/08-data-quality](../08-data-quality) |
| Catalog and lineage | "scan `<source>` into the catalog and show lineage from source to report" | [knowledge/09-catalog-lineage](../09-catalog-lineage) |
| Golden records | "match and merge `<entity>` across `<sources>` and show me the golden records" | [knowledge/10-mdm](../10-mdm) |
| Use IDMC from Claude over MCP | `/informatica-idmc-headless:connect-mcp`, or "connect Claude to IDMC's MCP servers" (read-only tools by default) | [knowledge/11-mcp-claire](../11-mcp-claire) |
| Move assets between orgs | "export project `<name>` and import it into my other org" | [knowledge/12-deploy-migrate](../12-deploy-migrate) |
| Know the cost | "how many IPUs did we use this month, and by what" | [knowledge/13-ipu-cost](../13-ipu-cost) |
| Fix an error | paste the error: "why does this fail: `<message>`" | [Error Triage](04-error-triage.md), `knowledge/lessons/` |
| See it end to end first | "deploy the `<demo>` blueprint into my org" | `toolkit/demos/` (start at `BLUEPRINT_CONVENTIONS.md`) |

## 4. The lessons that save the most time

Each one cost a real project hours or days. The id leads to the full lesson in `knowledge/lessons/`.

**Reading answers**
- A 200 can be fake. A zero-byte 200, or a 200 carrying login HTML, is gateway routing, not success (L-METHOD-025, L-AUTH-006).
- A 404 means wrong path or host until proven otherwise; a 405 proves the route exists (L-AUTH-012, L-AUTH-008).
- Never decide what the org can run from `products[]` or a 404: read deployed engines, privileges and selections (L-METHOD-033, L-AUTH-071).
- Read back after every write. A 200 whose value reverts is a silent rejection (L-METHOD-030, L-CDI-149).

**Hosts and login**
- Take every service host from the login's base URL; never hand-build or string-replace a pod name (L-AUTH-003, L-CAI-040).
- `IDS_085` on the wrong domain label looks like a bad password but is not one (L-AUTH-004, L-AUTH-035).

**Runtime and connections**
- Fix in order: host, then engine, then adapter, then driver. Only after that, request bodies and credentials (Law 20).
- `403 APP_105060` is a family: read the message to know which gate failed. On every hosted connection at once, it is a Hosted Agent outage (L-CONN-018, L-AGENT-117).
- A passing connection test is not proof: some tests pass with a wrong password; prove a connection with a real data query (L-CONN-117, L-MCP-127).
- Each runtime service you enable costs memory and rolls the engines. Enable only what you need (L-AGENT-040, L-AGENT-042).

**Building and running**
- The CDI chain is mapping, then mapping task, then taskflow, then schedule (L-CDI-001).
- An import creates design objects only: deploy, publish and bind them separately (L-MIG-024).
- One writer per org. Two Claude sessions writing to the same org will overwrite each other (L-CDI-149).
- Run long orchestrations on a server, not in a laptop shell that can be reaped (L-METHOD-148).

**Limits and cost**
- A monthly job limit can stop every Data Integration job, and no API shows it: ask Informatica for yours (L-IPU-041, L-IPU-044).
- Read IPU use with the async metering export; a meter that cannot read the log reports 0 instead of failing (L-IPU-021, L-IPU-025).

**Before anyone says "IDMC can't"**
- Work the workaround ladder in your org first: lessons, re-probe, another plane, clone a UI-made object, capture the
  UI's own call, another IDMC component, a Python bridge, one residual click
  ([New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md)).

## 5. When something goes wrong

1. Paste the exact error to Claude. It greps the lessons for that signature first.
2. If it is not in the lessons, Claude runs the five checks in [Error Triage](04-error-triage.md).
3. If you learn something new, ask Claude to **"save this as a lesson"**. It writes it, in generic form, to your local
   lessons file, which it searches next time. Share it with everyone through an issue or pull request on the repo.

## 6. Going further

- Deploy to production and run day 2: [End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md).
- What went wrong in a real production deployment, and how to avoid it: [What Went Wrong](09-what-went-wrong-production-deployment-post-mortem.md).
- The laws behind every answer: [The Laws of Headless IDMC](02-the-laws-of-headless-idmc.md).
- Every endpoint and verb: `knowledge/reference/`.
- Keep it running after go-live: [Run it in production](12-run-it-in-production.md).
