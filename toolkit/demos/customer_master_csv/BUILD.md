# BUILD: customer mastering from a CSV, live in your org

Every step says how to prove it worked. Fill in the timing log at the end: it is the user story's measurement.
Writes are dry runs until `--execute --expect-org <orgIdV3>`. Paths are relative to the plugin root; Windows: `py`
instead of `python3`.

**You need:** an IDMC org and a native IDMC user (see the root README), a Linux x86-64 machine for the Secure Agent
(4 vCPU and 16 GB is comfortable; macOS cannot run an agent), and the plugin connected: `/informatica-idmc-headless:connect` prints your
org id. Write that id down as `<orgIdV3>`.

## 1. Install and register the Secure Agent (target: 15-25 min)

Ask Claude: *"install a Secure Agent on this Linux machine and register it to my org"*, or follow the
[Secure Agent cheat sheet](../../../knowledge/02-secure-agent/README.md) and
[guide §3](../../../knowledge/02-secure-agent/01-secure-agent-install-run-tune.md):

1. Installer URL and an org-scoped install token: `python3 toolkit/lib/idmc_session.py get v2 /api/v2/agent/installerInfo/linux64 --save-to ~/.idmc_toolkit/agent_installer.json` (printing hides the token; the file is readable only by you)
   (use the token within 24 hours, L-AGENT-001).
2. As a non-root OS user: download, verify the published SHA-256, `./agent64_install_ng_ext.<build>.bin -i silent`.
3. Start the daemon first, then register: `./infaagent startup`, then `./consoleAgentManager.sh configureToken <user> '<token>'`
   (L-AGENT-002). Never put your IDMC password on the command line.
4. Enable only **Data Integration** on the runtime environment (`toolkit/lib/idmc_runtime_selections.py`): selecting
   every service downloaded about 18 GB in about 8 minutes and overloaded a 4-vCPU host (L-AGENT-041).

**Proof:** `/informatica-idmc-headless:health-check` shows the agent and its Data Integration engine RUNNING with `subState` 0. Engines
can take 6-10 minutes after a start (L-AGENT-125).

## 2. A flat-file connection and the input file (target: 3-5 min)

1. Make a folder on the agent host that the agent's OS user can read and write, for example
   `/home/<agentuser>/customer_data` (L-CONN-067).
2. Create the connection (Claude: *"create a CSV flat-file connection called FF_CUSTOMERS on my agent's runtime pointing
   at /home/<agentuser>/customer_data"*): `POST /api/v2/connection` with `"type": "CSVFile"`, the runtime environment
   id and the directory in the top-level `database` field (L-CONN-065).
3. Test it: `GET /api/v2/connection/test/<connId>` must succeed (free, no IPU).
4. Make the input and copy it into that folder: `python3 toolkit/demos/customer_master_csv/check.py --out ~/customer_master`
   (it also builds the package and the expected output), then copy `~/customer_master/data/customers_raw.csv` to the
   agent folder (or use your own CSV with the same
   header).

**Proof:** the test passes and the file is in the folder, readable by the agent user.

## 3. Deploy the mapping and its task (target: 2-5 min)

1. Make a profile from `toolkit/mapgen/profile.example.json`: keep only a connection alias `FF` with
   `"name": "FF_CUSTOMERS"` and `"kind": "FF"`, set your runtime environment name and a project/folder, and save it
   outside the plugin (for example `~/.idmc_toolkit/customer_master_profile.json`).
2. Fill every id from the names: `python3 toolkit/mapgen/mapgen.py --profile <profile> resolve --write`.
3. Dry run: `python3 toolkit/mapgen/mapgen.py --profile <profile> deploy toolkit/demos/customer_master_csv/mapping/m_customer_master_csv.json`
4. Deploy: the same command with `--execute --expect-org <orgIdV3>`. It imports the mapping and creates the mapping
   task `mt_customer_master_csv`.

**Proof:** the deploy prints the mapping and task ids; the mapping opens as valid in the designer.

## 4. Run it (target: 1-3 min)

`python3 toolkit/mapgen/mapgen.py --profile <profile> run mt_customer_master_csv --folder "<project>/<folder>" --execute --expect-org <orgIdV3>`

A run is a job and counts against your job budget and IPUs. Expect 20 s to 3 minutes of fixed cost per job on an
agent, plus a few seconds for a few thousand rows.

**Proof:** the run ends SUCCESS with source rows = your record count, `customer_xref.csv` rows = the same count and
`customers_golden.csv` rows = the number of customers.

## 5. Compare with the twin (target: 1 min)

Copy `customers_golden.csv` and `customer_xref.csv` from the agent folder to a local folder, then:

`python3 toolkit/demos/customer_master_csv/check.py --compare <that folder>`

**Proof:** "live run matches the twin" and ALL CHECKS PASSED. A difference names the record and the column: fix the
expression or the twin, re-deploy, re-run.

## Traps

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| `FR_3085` null character | a CSV source with empty fields | put `(blank)` in empty cells (the sample does; the mapping reads `(blank)` as empty) | L-CONN-066 |
| Connection test fails although the path exists | the agent's OS user cannot read or write the folder | own it by the agent user (mode 2775 for a shared group) | L-CONN-067 |
| Engines stay starting | `subState` is still -1 or 2 | wait; Process Server alone can take up to 20 minutes | L-AGENT-125 |
| The task create fails `APP_13500` | parentheses in the task name | letters, digits, spaces and hyphens only | L-CDI-280 |

## Timing log (fill in)

| Step | Target | Your time | Notes |
|---|---|---|---|
| 1. Secure Agent installed, registered, Data Integration RUNNING | 15-25 min | | |
| 2. Connection created and tested, file in place | 3-5 min | | |
| 3. Mapping and task deployed | 2-5 min | | |
| 4. Run finished | 1-3 min | | |
| 5. Compared with the twin | 1 min | | |
| **Total, first time** | **about 20-40 min** | | |

Share what you measured (and anything that went wrong) with `/informatica-idmc-headless:save-lesson`, and send it upstream with the
"Share a lesson" issue form.
