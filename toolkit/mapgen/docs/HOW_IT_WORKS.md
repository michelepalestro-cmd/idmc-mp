# How the headless mapping generator works ("Route 5")

**In one sentence:** you describe a pipeline to Claude in plain English; Claude writes a small JSON *spec*; `mapgen`
turns the spec into a real Informatica CDI mapping (the same format an IDMC export contains), imports it into your org
over the REST API, wraps it in a mapping task, runs it on your Secure Agent, and then checks the result.

---

## 1. The plain-language version

| # | Step | Where it happens | What it means |
|---|---|---|---|
| 1 | **You ask** | your laptop | "Make the names ALL CAPS by the time they land in BigQuery." |
| 2 | **Claude writes a spec** | your laptop | A short JSON file: the boxes of the mapping (source, expression, target …) and the arrows between them. |
| 3 | **`mapgen lint`** | your laptop | Checks the spec for the mistakes that would otherwise only show up when the job runs. Nothing has touched IDMC yet. |
| 4 | **`mapgen` compiles** | your laptop | Translates every box into Informatica's own internal mapping objects (IMF). |
| 5 | **`mapgen` packages** | your laptop | Packs those objects into the same zip layout an IDMC export uses, with a checksum for every file. |
| 6 | **Import** | Informatica Cloud | IDMC unpacks it and stores a **real mapping** in your project and folder: it opens on the canvas, shows lineage, and CLAIRE can read it. |
| 7 | **Mapping task** | Informatica Cloud | A small wrapper that says "run this mapping on this Secure Agent group". It holds no logic. |
| 8 | **Start a job** | Informatica Cloud | IDMC queues the run for your Secure Agent. |
| 9 | **Your Secure Agent runs it** | your Secure Agent VM | It reads the rows through the source connector, applies the transformations in memory, and writes through the target connector. |
| 10 | **Claude checks and reports** | your laptop | It reads the run status and row counts, compares the target with a reference query, and tells you what happened. |

Claude **designs and orchestrates**. The Secure Agent **moves the data**. Claude never handles your rows during a run.

## 2. Where each piece lives

| Piece | Where it runs | Talks to | How |
|---|---|---|---|
| Claude Code, `mapgen`, the spec, the profile | your laptop | Informatica Cloud | HTTPS, IDMC REST API (v2 + v3, plus FRS for folder moves) |
| Mapping, mapping task, connections, job dispatch, logs | Informatica Cloud (your org) | your laptop, your Secure Agent | answers REST calls; hands jobs to the agent |
| Secure Agent → Data Integration Server → one DTM process per job | your Secure Agent VM | Informatica Cloud, your data systems | **outbound** HTTPS (443) to Informatica Cloud (no inbound ports); connectors straight to each data system |
| Your data (BigQuery, PostgreSQL, Salesforce, files …) | your data systems | the Secure Agent | each connector's own protocol |

### What travels where

- **Your row data:** data system → agent memory → data system. It never crosses the laptop or Informatica Cloud during a run.
- **The mapping definition:** laptop → Informatica Cloud, once, as an import package.
- **Job state, logs and row counts:** agent → Informatica Cloud → laptop, read over REST.
- **Credentials:** database credentials live (encrypted) in your org's *connections* and are used by the agent; the spec only
  names a connection by its ID. The IDMC login comes from environment variables on the laptop, never from a spec or a profile.
- **Verification:** after the run Claude queries the target (row counts, two-way diffs) with a warehouse client. Those are
  small result sets, not the data set.

## 3. The technical version

### 3.1 The spec

```json
{"name": "m_names_upper",
 "connections": {"WH": {"guid": "<connection FRS guid>", "name": "BQ_WAREHOUSE", "repoHandle": "<v2 connection id>"}},
 "nodes": [
  {"type": "source", "name": "SRC_Members", "conn": "WH",
   "query": "SELECT member_id, full_name FROM raw.members",
   "fields": [["member_id", "STRING", 256], ["full_name", "STRING", 256]]},
  {"type": "expression", "name": "EXP_Upper_Name", "fields": [
   {"name": "full_name", "type": "STRING", "expr": "UPPER(LTRIM(RTRIM(r_full_name)))"}]},
  {"type": "target", "name": "TGT_Members_Upper", "conn": "WH", "object": "analytics/members_upper", "truncate": true,
   "fields": [["member_id", "STRING"], ["full_name", "STRING"]]}],
 "links": [["SRC_Members", "EXP_Upper_Name", {"member_id": "", "full_name": "r_full_name"}],
           ["EXP_Upper_Name", "TGT_Members_Upper"]]}
```

The third element of the first link is a field rule: `member_id` passes through unchanged and `full_name` arrives in
the expression as `r_full_name`. That rename matters. An Expression passes every incoming field through, so a new port
called `full_name` next to an incoming `full_name` would put two fields with one name in the same transformation, which
IDMC rejects. `mapgen lint` reports it as `EXPR_PORT_CONFLICT`, and it caught exactly this mistake in the first
hand-written draft of this example. The target maps fields by name, so it receives `member_id` and the new `full_name`.

The org, folder and connection IDs usually come from a **profile** file instead of the spec, and `${NAME}` placeholders in
the spec are filled from `vars` (usually the profile's), so the same spec works in another org. Every node type and option,
and the exact profile and variable rules, are in [`SPEC_REFERENCE.md`](SPEC_REFERENCE.md).

### 3.2 Compile: spec → IMF

IMF is the object model IDMC itself stores mappings in. Each spec node becomes its IMF transformation class
(`TmplSource`, `TmplTarget`, `TmplExpression`, `TmplFilter`, `TmplRouter`, `TmplJoiner`, `TmplAggregator`, `TmplSorter`,
`TmplUnion`, `TmplLookup`, `TmplRank`, `TmplGenerator`, `TmplDmo`, `TmplRuleSpecification`, `TmplCleanse`, `TmplDedup` …),
with its groups, ports and data types. Sources and targets carry a `BaseAdapter` bound to a connection
(`connectionId: "saas:@<connection guid>"`). Links become `TmplLink` objects, and the receiving group gets a field rule:
`TmplAllRule` (all fields) or `TmplNameRule` (pick, rename or exclude fields).

Every object carries `$$ID` and `$$class`. References look like `{"##ID": 12, "$$class": 7}`, and `$$classInfo` maps each
class number to its Java class name. Warehouse types map to platform types: STRING → string(4000), INTEGER → bigint(19),
NUMERIC → decimal(28,9), FLOAT → double(15), TIMESTAMP and DATE → date/time(29,9).

The example's expression port becomes one `TmplExpressionField`:

```json
{"$$ID": 23, "$$class": 9, "name": "full_name", "expFieldType": "OUTPUT",
 "expression": "UPPER(LTRIM(RTRIM(r_full_name)))",
 "platformType": {"##SID": "smd:com.informatica.metadata.seed.platform.Platform.typesystem/string"},
 "precision": 4000, "scale": 0}
```

### 3.3 Package

```
m_names_upper.pkg.zip
├─ Explore/<project>/<folder>/m_names_upper.DTEMPLATE.zip
│   ├─ mappingTemplate.json   name, asset GUID, references to its connections
│   ├─ fileRecord.json        points the template at the IMF file
│   ├─ bin/@2.bin             the IMF JSON (the mapping itself)
│   └─ metadata.meta
├─ exportMetadata.v2.json     the mapping, its project, folder and connections
└─ exportPackage.chksum       path=SHA-256 for every file; IDMC rejects a package that does not match
```

### 3.4 Import, task, run, verify (the REST calls, in order)

| # | Call | Purpose |
|---|---|---|
| 1 | `POST /ma/api/v2/user/login` | a session, valid for about 30 minutes (mapgen signs in again after 24) |
| 2 | `GET /api/v2/org` | confirm the org before any write |
| 3 | `POST /public/core/v3/import/package` (multipart, field `package`) | upload → `jobId` |
| 4 | `POST /public/core/v3/import/{jobId}` | start it: `REUSE` for a new mapping, `OVERWRITE` to rebuild one under the same GUID |
| 5 | `GET /public/core/v3/import/{jobId}` | poll until `SUCCESSFUL`; read the import log |
| 6 | `GET /api/v2/mapping` | the new mapping's id (matched by name **and** folder) |
| 7 | `POST /api/v2/mttask` `{mappingId, runtimeEnvironmentId}` | create the mapping task, or reuse it |
| 8 | `POST /frs/v1/MoveEntities` | new tasks are born in `Default`; move it into the folder |
| 9 | `POST /api/v2/job` `{taskId, taskType: "MTT"}` | start the run → `runId` |
| 10 | `GET /api/v2/activity/activityLog?taskId=…` | poll until the entry's `runId` matches and it has an end time; state 1 = success, 2 = warning, 3 = failed; success/failed rows (per target for multi-target mappings) |
| 11 | `GET /api/v2/activity/activityLog/{id}/sessionLog` | the agent's detailed log, when something failed |

Then Claude runs the verification SQL: row counts plus a two-way `EXCEPT DISTINCT` against a reference query, expecting 0
differences, and for a rebuild a second run compared with the first.

## 4. Guardrails

**`mapgen lint`, before anything touches IDMC.** Each rule came from a real failure:

| Trap | What goes wrong | Lint |
|---|---|---|
| An Expression port reuses an incoming field's name | two fields with one name; IDMC rejects it | error `EXPR_PORT_CONFLICT`; rename the input on the link |
| An Expression OUTPUT port uses another OUTPUT port | the expression is invalid | error; make the helper a VARIABLE port |
| One source feeds both the master and the detail of a Joiner | the run hangs with no error | error unless the joiner has sorted input and Sorters |
| More than 4–5 warehouse readers in one mapping | the agent's Java heap runs out | warning at 5, error above; split the mapping |
| A DATE column | with the Java type the earlier generators wrote (`java.sql.Date`) every run fails: "Unknown native type" | built in: mapgen writes `java.sql.Timestamp`, as designer-built mappings do, so DATE columns read and write natively |
| A JSON-typed field | fails in the warehouse connection's Simple mode | declare it STRING |
| BigQuery write settings | appends on every run; a 10 s poll per target | warning for an append nobody asked for; mapgen writes the disposition as a runtime attribute and a 1 s poll by default |
| A target field nobody upstream produces | silently loads NULL | error, naming the field |
| An unknown field in an expression or condition | import or run failure | error before import |
| A target that is a protected live table | overwrites production | refused unless explicitly allowed |

**Run safety, on the live system.** Check the org before every write. Build in a scratch folder and a scratch dataset
first. One live run at a time, because the agent host is shared. Keep a job budget, because every run counts toward the
org's monthly job cap. Read back every write, because an HTTP 200 can be a silent no-op. Promote only after parity. Change
a mapping by rebuilding it under the same GUID (OVERWRITE); new targets POSTed to its task are silently ignored.

## 5. FAQ

**Is the mapping real?**
Yes. It is stored in your org exactly like a mapping built in the designer: it opens on the canvas with every
transformation visible, you can edit and validate it there, it appears in lineage, and CLAIRE can read it. The only
difference is how it got there (an import package instead of mouse clicks).

**Where does the code run?**
`mapgen` runs on your laptop (Python 3, standard library only). It only builds files and makes REST calls. The mapping
itself runs on your Secure Agent, inside the DTM process the agent starts for each job.

**Where does my data go?**
From your source system into the Secure Agent's memory and out to your target system. It never passes through Claude,
the laptop or Informatica Cloud during a run. Informatica Cloud sees the mapping definition, job states, logs and row
counts. After a run, Claude's verification queries return counts and differences, not the data set.

**What does Claude do, and what does the Secure Agent do?**
Claude turns your request into a spec, runs `mapgen` (lint, build, package, import, task, run), reads the results and
checks them. The Secure Agent does all the data work: it connects to your systems with the connection credentials stored
in your org, reads, transforms and writes the rows.

**What can't it do yet?**
- BigQuery full pushdown cannot be switched on headless yet, so warehouse-to-warehouse mappings run in agent mode (the rows
  stream through the agent). Heavy warehouse-internal logic can stay in query sources until then.
- Changing a mapping's connector type means regenerating it, not editing the package.
- Data-quality transformations (rule specification, cleanse, deduplicate) need those assets to exist in your org.
- Window functions (LAG / LEAD) do not run in standard mappings: they import as valid and fail at run start. The
  generator refuses them by default; use a Sorter plus VARIABLE ports for running totals and previous-row values.
- The SQL transformation imports but fails at run start (one UI-authored exemplar would show the missing shape), and
  Transaction Control, Java and Hierarchy Parser/Builder are not covered yet. The poster's "Proven vs not yet" table is
  the current list.
- A decimal keeps at most 28 significant digits (19 before the point at scale 9): wider NUMERIC values overflow.
- Each mapping task pays roughly 20 s of fixed start-up time, so fewer, richer mappings beat many small ones.

**Why not a Mapping Designer API?**
IDMC has no public REST call that creates a mapping: `POST /api/v2/mapping` is not a create surface, and the v3 objects
endpoint is read-only. The import API is the documented write path that accepts a complete mapping definition, so
`mapgen` builds what an export would contain and imports it. Building the package yourself is not a path Informatica
documents, so treat generated mappings like any other change: scratch first, review on the canvas, parity before
promotion. If Informatica ships a mapping-design API, the spec stays the same and only the last step changes.

**What do I need to use it?**
Python 3, an IDMC user that can import objects and create and run mapping tasks, a Secure Agent with the connectors you
need, the connections already defined in your org, and a profile file with your org, folder, connection and runtime
environment (`mapgen resolve` can look those IDs up by name).

**How do I change a mapping later?**
Edit the spec and rebuild it under the same mapping GUID with `OVERWRITE`. The mapping keeps its identity, its task and its
history. Re-run the parity check before anything downstream reads the new output.
