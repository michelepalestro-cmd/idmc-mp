# CLAIRE DQ Agent: file-based profiling and cleansing

**Answers:** What can the hosted CLAIRE Data Quality agent (`dataqualityagent` MCP server) do headless? How do I upload a
file, get a profile and a generated cleansing transform back, and apply it? Which of its skills need a cataloged asset,
and what does each one persist?

**Read when:** profiling or cleansing a sample file without a catalog; calling the DQ agent's skills over MCP; an upload
returns 409 or a skill returns an empty answer; deciding whether CLAIRE-generated rules exist as console assets.

**Key rules:**
- Only `data_quality_cleansing` works on an uploaded file; the other skills need a CDGC-cataloged asset id (L-DQ-072,
  L-DQ-071).
- Upload with `curl --http1.1 -H "Expect:"`, a unique filename, and a fresh URL on every 409 (L-DQ-072).
- Two calls generate the transform: a prescriptive call naming every fix, then "Yes, proceed now" with only `prompt` and
  `conversation_id` (L-DQ-073).
- Prompts are plain ASCII prose: `<`, `>` and `->` are rejected with `-32602` (L-DQ-074).
- The MCP rule-generation skill drafts only; CLAIRE GPT's chat rule generation persists rule specs and dictionaries to
  the CLAIRE project, so audit both object types after any run (L-DQ-079, L-MCP-097).
- Uploads are egress: sample or synthesize, one dataset at a time, and keep a ledger (L-DQ-081).

**Related:** [Profiling - What Is Headless](02-profiling-what-is-headless.md) ·
[DQ Assets](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) ·
[Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md) ·
[MCP Auth & OAuth Clients](../09-claire-mcp/02-mcp-auth-oauth-clients.md) ·
[Lessons: Data Quality & Profiling](../../lessons/by-domain/06-data-quality-profiling.md)

**Last verified:** 2026-10-03

> **Summary.** The managed MCP server **`dataqualityagent`** is Informatica's hosted CLAIRE Data Quality Agent. It has
> seven tools: five prompt-driven skills plus `request_upload_url` and `get_skill_execution_updates`. The file recipe:
> authenticate (Bearer JWT + `IDS-SESSION-ID`, or an OAuth token) → `request_upload_url` → `PUT` the file → call 1 →
> call 2 → extract and run the generated Python script with a harness → review each rule. Calling conventions for the
> async loop are shared with the other agent-style servers
> ([Agent-Style MCP & Custom Shims](../09-claire-mcp/04-agent-style-mcp-async-orchestration-custom-shims.md)).

---

## 1. The server and its tools

Endpoint (read it from the MCP registry, see [Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md)):
`https://mcp.<domain>.informaticacloud.com/mcp-servers/public/dataqualityagent`

| Tool | Input | Needs a cataloged asset? | What you get | State in these sources |
|---|---|---|---|---|
| `request_upload_url` | `filename`, `size_bytes`, `content_type`, `description`, `display_name` | no | a single-use presigned PUT `url`, `required_headers`, and a `conversation_id` | proven |
| `data_quality_cleansing` | `prompt`, `name` (file name), `artifacts` ([file name]), `conversation_id` | **no**: works on the uploaded file | file-based profile, metadata inference, CDEs, issue catalog, **generated Python transformation** | **proven** on several datasets |
| `data_profiling` | `prompt`, `name`, `external_id` (asset id) | **yes** | a profile of the cataloged asset | on uncataloged assets: SUCCESS + ARTIFACT error, or a summarize-step error (L-DQ-071) |
| `data_quality_analysis` | same | **yes** | DQ metadata/score for the asset | empty `END_OF_ANSWER` when nothing is cataloged or published |
| `data_quality_rule_recommendation` | same, plus the reply `"yes"` | **yes** | recommended rules | pauses on a HUMAN_PROBE; one run returned 10 rules (4 matching already-published rules) (L-DQ-080) |
| `data_quality_rule_generation` | `prompt`,... | yes (table asset) | a rule plan | drafts only: nothing saved, bound or run (L-DQ-079) |
| `get_skill_execution_updates` | `conversation_id`, `message_id`, `cursor`, `events`, `reasoning` | n/a | the asynchronous progress and answer items | proven |

The hosted agent runs in Informatica's cloud. It cannot reach a private database directly: that is a network position
only a Secure Agent has (L-MCP-006).

---

## 2. Connect and authenticate (L-DQ-070)

**Option A: the user session and a JWT.**

1. Log in with v3: `POST https://<domain>.informaticacloud.com/saas/public/core/v3/login`
   `{"username":"<user>","password":"<pw>"}` → `userInfo.sessionId`. A login failure has no `userInfo` key; handle
   that case (L-MCP-032).
2. Mint a JWT: `GET https://<domain>.informaticacloud.com/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=<fresh uuid>`
   with header `IDS-SESSION-ID: <sessionId>` → `jwt_token`. It lasts 30 minutes from grant. Refresh about 5 minutes
   early, from the still-valid session.
3. Headers on every MCP call:

```
Authorization: Bearer <jwt_token>
IDS-SESSION-ID: <sessionId>
MCP-Protocol-Version: 2025-06-18
Content-Type: application/json
Accept: application/json, text/event-stream
```

**Option B: an OAuth client** (client credentials, recommended for daemons). This token alone is the bearer. See
[MCP Auth & OAuth Clients](../09-claire-mcp/02-mcp-auth-oauth-clients.md). Through a local gateway the tools appear
with server-prefixed names, for example `dq_get_skill_execution_updates` ([04 Agent-Style MCP](../09-claire-mcp/04-agent-style-mcp-async-orchestration-custom-shims.md)).

Send an `initialize` first (`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"<client>","version":"1"}}}`).
The server is stateless enough that a small client re-initializes before each call.

---

## 3. The call envelope and the asynchronous loop

### 3.1 The doubly nested `tools/call`

The DQ agent's tools expect the tool **arguments to be a complete inner JSON-RPC `tools/call` message**:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call",
 "params":{"name":"data_quality_cleansing",
           "arguments":{"jsonrpc":"2.0","id":"<fresh uuid>","method":"tools/call",
                        "params":{"name":"data_quality_cleansing",
                                  "arguments":{"prompt":"...","conversation_id":"<id>","events":true,"reasoning":true}}}}}
```

Through a gateway that already wraps calls, a validation error on this shape means the gateway wants the **plain**
argument object. Retry once with `{"prompt":...}` (L-MCP-030).

### 3.2 Unwrap the answer

The answer's `result.content[].text` is itself a JSON-RPC message whose `result.content[].text` may be another one.
Unwrap up to three or four levels, or read `result.structuredContent`, until you reach
`{status, context, items, pagination}` (L-MCP-030).

### 3.3 Poll until done (L-MCP-044)

The first response carries `context.conversation_id` and `context.message_id` and returns immediately. Then loop:

```
tools/call get_skill_execution_updates
  {"conversation_id":"<cid>","message_id":"<mid>","cursor":"<cursor, start at 0>","events":true,"reasoning":true}
→ {"status":"IN_PROGRESS|SUCCESS|PARTIAL_SUCCESS|FAILED", "items":[...],
   "pagination":{"cursor":"<next>","has_more":true|false,"poll_interval_ms":1500}}
```

- Feed back the returned `cursor` each time, and wait `poll_interval_ms` (about 1.5 s) between polls.
- Stop when `has_more` is false and the status is terminal, or when an item of type **`HUMAN_PROBE`** arrives
  (§7.2). Allow up to ~15 minutes for a code-generation run.
- Item types: `EXECUTION_INSIGHT` (progress text in `payload.text`), `REASONING_TRACE` (`payload.thought`),
  `ARTIFACT` (`payload.summary` plus `payload.data`: the grids, reports and script), `HUMAN_PROBE`, and
  `END_OF_ANSWER`.
- `"deferred": true` on the skill call asks for this submit-then-poll behaviour explicitly (used with the rule
  recommendation skill).

---

## 4. The file-based recipe, step by step (L-DQ-072, L-DQ-073)

### 4.1 Prepare the file

- **Formats:** csv, xlsx, parquet.
- **Keep it small and synthetic or sampled.** The upload leaves your network (§9). A 2,000-row random sample of a large
  table worked well, and small reference tables went up in full.
- **Drop all-empty columns.** An entirely null column stalls the run after the preview (it stops at PARTIAL). Report
  that column's null rate from the database instead (L-DQ-077).
- **Use a unique filename per upload,** for example `<dataset>_<unix time>.csv`. Re-using a name collides with an
  earlier mint (409).
- **One dataset at a time.** Serial runs cleared transient failures that parallel runs did not.

### 4.2 Mint the upload URL

```json
tools/call request_upload_url
{"filename":"<unique>.csv","size_bytes":<bytes>,"content_type":"text/csv",
 "description":"<what the file is and which defects you expect>","display_name":"<label>"}
→ {"url":"<single-use presigned PUT>","required_headers":{...},"conversation_id":"<cid>",...}
```

Keep that `conversation_id`: the first cleansing call runs in it.

### 4.3 PUT the file (the 409 trap)

```bash
curl -sS --http1.1 -H "Expect:" -X PUT \
     -H "<each required_header>: <value>" \
     --data-binary @<file> "<url>" -o /dev/null -w "%{http_code}"
```

- **Force HTTP/1.1 and send an empty `Expect:` header.** With curl's default HTTP/2, or an `Expect: 100-continue`
  preflight, the preflight **consumes the single-use URL**, and the body PUT then gets **409**.
- There is also a genuine transient 409 race on a freshly minted URL. Wait ~1 s after minting, and on a 409 **mint a
  new URL** and retry. One upload took 7 x 409 before a 201. A loop of up to ~8 attempts was enough.
- Success: 200, 201 or 204.

### 4.4 Call 1: a prescriptive prompt

```json
tools/call data_quality_cleansing
{"prompt":"Profile the uploaded file <file>. For each column report the inferred type, null and blank percentage,
           distinct count and dominant patterns. Then fix these issues: trim and lowercase email; normalize phone to
           one format; map state variants to 2-letter codes; parse mixed date formats to ISO; standardize tier and
           status to fixed value lists; strip thousands separators and reject negative amounts; zero-pad zip to 5 digits;
           flag duplicate records on name plus birth date plus normalized email.",
 "name":"<file>","artifacts":["<file>"],"conversation_id":"<cid from request_upload_url>"}
```

- **Name every fix you want.** CLAIRE captures this "usage context" and proposes rules. A generic "analyze/profile
  this file" first call, plus artifacts re-sent on the second call, produced an **empty second call** (profile only).
- Write in **plain ASCII prose, with no angle brackets**. `<` and `>` are rejected with JSON-RPC `-32602` "Angle
  brackets... prohibited", so `->` arrows fail. Some shims also reject non-ASCII and HTML (L-DQ-074). The `<file>` above
  is a doc placeholder: write the real name.
- Pass as `artifacts` only the name you uploaded or that CLAIRE itself returned. Never invent an artifact name.

### 4.5 Call 2: "proceed"

```json
tools/call data_quality_cleansing
{"prompt":"Yes, proceed now. Using the usage context you captured, generate the actual cleansing and standardization
           rules for each affected column and the de-duplication key, with one before and after example each.",
 "conversation_id":"<same cid>"}
```

Send **only** `prompt` and `conversation_id`: no artifacts, no name. CLAIRE then runs its full code-generation and
self-test loop.

### 4.6 What comes back

Progress lines (`EXECUTION_INSIGHT`) walk through fixed stages:

1. analysing the metadata attributes;
2. identifying critical data elements (CDEs);
3. identifying functional dependencies among the CDEs;
4. identifying statistical DQ issues;
5. identifying standardization DQ issues;
6. generating code to fix them;
7. checking whether the code is valid, and self-correcting;
8. testing the code on sample data ("Testing got failed, retrying attempt n of 5").

The final `ARTIFACT` items include:

- **Inferred metadata per column** (GridView): data type, data kind, business entity, sensitivity, a generated description.
- **Critical data elements** with per-column reasoning, and **functional-dependency clusters** (for example
  identity/dedup anchors, geographic cross-validation groups).
- **Issue lists** (statistical and standardization), each with dimension, fix type (`fixable`, `not_fixable`, `CDGC`),
  sample rows, reason and suggested fix.
- **The transformation**: a Python script in the IDMC Python-transformation dialect, JSON-escaped under a `"Script"`
  key (PropertiesView), with Pre-Partition definitions, Main per-row code, Post-Partition DataFrame rules and an
  Output block ending in `generateRow`.

**Profile statistics cover the whole upload.** The `valueCount` equals the uploaded row count, and the "Rows: 500" line
is only the preview size (L-DQ-076).

---

## 5. Applying the generated transform locally: the generic applier (L-DQ-075)

One small harness applies any CLAIRE cleansing output with no per-dataset code:

1. Extract the longest JSON-escaped `"Script"` value from the call-2 output (a raw JSON decode starting at the quote).
2. `ast.parse` it and fail loudly if it is not valid Python.
3. Split it at the markers `# Main Python Code`, `# Post-Partition` and `# Output Code`.
4. `exec` the Pre section once.
5. For each input row, bind each column as a variable of the same name (the IDMC input-port convention, `''` → `None`)
   and `exec` the Main section.
6. `exec` the Post section; it builds a DataFrame `df`.
7. Write the columns whose names end in `_out` (suffix stripped) as the cleansed file. Rows with a non-empty
   `rule_name` form the rule-hit report; tally rule frequencies from it.

The same unmodified code ran on three datasets in the proof:

- 45 rows in, 43 out (two duplicates removed), with 33 rows touched by at least one rule;
- a 2,000-row sample with 439 rows cleansed;
- a 595-row table deduplicated to 594.

**Treat the generated code as untrusted.** It is machine-written code that you `exec`. Read it first, and run it
in an isolated environment with no credentials in scope. This step is local, so it is **not** an IDMC run. To
execute cleansing *in* IDMC, the logic must live in a mapping ([DQ Assets](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) §2).
Running this Python inside an IDMC Python transformation is untested here.

---

## 6. Review checklist before you trust or apply the rules (L-DQ-078)

- [ ] **Code vs issue catalog.** Generated code can contradict CLAIRE's own findings. In the proof, it zero-padded a
      4-digit ZIP that the issue list classed `not_fixable`, which a steward should see instead.
- [ ] **`not_fixable` values pass through.** Invalid e-mails, for example, are trimmed and lowercased but not
      corrected. That is correct behaviour; route them to stewardship.
- [ ] **Type coercion at ingest.** CLAIRE's loader coerced numeric-looking strings (ZIP codes, phone numbers) to floats
      (`94107.0`), so its profile flags "float format" that a plain CSV read does not have.
- [ ] **SUCCESS does not mean the self-tests passed.** One run logged "Testing got failed... attempt 5 of 5" and still
      returned STATUS SUCCESS with a script. Validate the script yourself (the `ast.parse` plus a run on the sample).
- [ ] **Representation changes can go unflagged.** `2,300.00` became `2300.0` without a `rule_name` entry, because the
      violation mask compares numeric equality.
- [ ] **Cross-check with an independent engine** where one exists. SQL cleansing rules and the CLAIRE code agreed on
      every destructive fix in the proof (negative amounts and impossible dates → null).

---

## 7. The catalog-keyed skills

### 7.1 They need a cataloged asset (L-DQ-071)

`data_profiling`, `data_quality_analysis`, `data_quality_rule_recommendation` and (for table assets)
`data_quality_rule_generation` work only on **CDGC-cataloged** assets, keyed by the catalog asset id (a "pivot" UUID,
passed as `external_id` along with `name`). Symptoms on a raw connection or an uncataloged table:

- STATUS SUCCESS with `{"type":"END_OF_ANSWER"}` and no content;
- the answer asks you for the asset id;
- `data_profiling` returns SUCCESS with an ARTIFACT error, or fails at the summarize step with "An error occurred while
  processing data profile request".

Fixes: catalog the source first (a CDGC scan, see [Catalog & Governance (CDGC)](../07-catalog-governance-cdgc/)),
or use the file-based `data_quality_cleansing`. The classic Data Profiling service needs no catalog at all
([02](02-profiling-what-is-headless.md)). DQ *scores* from the catalog also need rule occurrences defined, run and
published in CDGC. Without them, analysis is empty and CLAIRE GPT answers "No Data Quality information".

### 7.2 Rule recommendation asks a human (L-DQ-080)

Through MCP the recommendation flow pauses with a **`HUMAN_PROBE`** item. Answer it in the same conversation by calling
the same skill with `{"prompt":"yes","conversation_id":"<cid>","deferred":true,"events":true,"reasoning":true}`, then
poll again. Catalog asset ids can change after rescans or renames, so **resolve the asset id again** (search the
catalog by name) before each run.

Recommendation only pairs the named columns with rules **already in the repository**; a column with no matching rule
comes back as "No matching data quality rules were found". For a new control (a positive amount, a value list, no future
dates), use rule generation instead, then bind the rule (L-MCP-098).

### 7.3 Rule generation drafts, nothing more (L-DQ-079)

`data_quality_rule_generation` over MCP extracts and plans rules, then stops. In the observed runs nothing was saved as
a console asset, bound or executed, so no scorecard or pass rate appeared. To make rules executable, author the rule spec
(UI, or clone, see [DQ Assets](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) §3) and put it in a
profile or a mapping.

**Rule generation is not side-effect-free everywhere.** In the CLAIRE GPT chat, rule generation runs a plan that creates
any reference **dictionary** in the CLAIRE project and folder before the Publish prompt, and **Publish Rules** (or any
free text typed while that prompt shows) saves the **rule specification** there too (L-MCP-097, L-MCP-096). That is
the documented "what CLAIRE GPT persists" list: DQ rule specifications with their dictionaries, and catalog rule
occurrences when you accept recommendations; it never runs a rule or writes data
([CLAIRE GPT - Prompting Rules & Patterns](../09-claire-mcp/03-claire-gpt-prompting-rules-patterns.md),
L-MCP-089). The one MCP run that reported rules "persisted to project CLAIRE" is consistent with that
mechanism. After any rule-generation run, list `RULE_SPECIFICATION` and `DICTIONARY` objects by `updateTime`
(`GET /public/core/v3/objects?q=type=='DICTIONARY'`) and delete or reuse strays.

---

## 8. Prompt rules for the DQ agent

- Plain ASCII prose. No `<`, `>`, `->`, HTML or smart quotes.
- Name the dataset (the uploaded file name, or the cataloged table name) and the action.
- For cleansing, list each fix (§4.4). Vague prompts come back as a `HUMAN_PROBE` or an empty answer.
- Keep one conversation per dataset. **Omit `conversation_id` to start fresh.** A stale or unknown id returns "No
  conversation found for the provided conversation id. Please pass a valid conversation id or omit it to create a new
  conversation." (L-DQ-082). After `request_upload_url`, reuse the conversation id it returned.
- Pass `events:true` and `reasoning:true` to see what ran and why.

---

## 9. Egress and logging (L-DQ-081)

File-based CLAIRE profiling sends the file to Informatica's cloud. Before any upload:

- Use synthetic data, or a sample with **no real PII**. Keep samples small.
- Send one dataset at a time.
- Keep an **egress ledger**: date, dataset, rows, columns, bytes, retries (409s included), conversation id and purpose.
  One project logged about 1.6 MB of samples in total.
- The **apply** step (§5) is local, with 0 egress.

---

## 10. Failure triage

| Symptom | Cause | Fix |
|---|---|---|
| PUT → 409 on every attempt | HTTP/2 or `Expect: 100-continue` preflight consumed the single-use URL; or a reused filename | `curl --http1.1 -H "Expect:"`, unique filename, re-mint on each 409 |
| PUT → 409 once, then 201 on a re-mint | transient race on a fresh URL | wait ~1 s after minting; retry with a new URL |
| `-32602` "Angle brackets... prohibited" | `<`, `>` or `->` in the prompt | plain ASCII prose |
| Run stops after the preview (PARTIAL) | an all-empty column | drop the column and re-run |
| Second call returns only the profile | generic first prompt and/or artifacts re-sent | prescriptive call 1; call 2 with only `prompt` + `conversation_id` |
| SUCCESS + `END_OF_ANSWER`, empty | catalog-keyed skill on an uncataloged asset | catalog it first, or use the file path |
| "An error occurred while processing data profile request" | `data_profiling` summarize step failing (seen on several days) | use `data_quality_cleansing` on a sample |
| "No conversation found for the provided conversation id" | stale conversation id | omit it to start a new conversation |
| `KeyError 'userInfo'` inside a local shim | the shim's login failed (wrong host or org, stale password) | surface the login status; see L-MCP-032 |
| Nothing in the IDMC console afterwards | expected: the agent saves no console asset | author the asset (UI/clone) or keep results in your tables |

---

## 11. What this path is and is not

- **It is** genuine Informatica output: server-side profiling statistics and CLAIRE-generated rules, fully headless,
  with no catalog needed.
- **It is not** an IDMC job. Nothing appears in the activity log, and the local apply step is your own code execution.
- **It is not** a saved DQ asset. For a reusable, schedulable scorecard use Data Profiling profiles
  ([02](02-profiling-what-is-headless.md), [04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)).

---

## 12. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "The DQ agent upload PUT fails with a permanent 409 (a per-user preview upload cap)". It survived a fresh JWT, a 15-minute wait and files under 1 MB. | 2026-09-04 | HTTP/1.1 without `Expect`, unique filenames and re-mint on 409 | L-DQ-090 → L-DQ-072 |
