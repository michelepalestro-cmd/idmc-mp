# How to work on this knowledge base

**Read this before touching anything in this folder.** It is the contract that lets several
agents improve this document at the same time without fighting each other.

There is **exactly one master document**: `IDMC API & MCP Master Reference.docx`.
It is **generated**. Never edit it.

---

## The 30-second version

```bash
cd "<KB root>\knowledge/12-reference-library\IDMC API & MCP Reference"

python build/validate_content.py         # 1. confirm the tree is clean before you start
#    ... edit exactly ONE file in content/ ...
python build/validate_content.py 12-cdi  # 2. check just your section
python build/build_master.py             # 3. regenerate the single master doc
```

**One agent, one section file, one sitting.** That is the whole concurrency model.

---

## Why it is built this way

The .docx is a binary. Two agents editing it at once means one silently loses their work, and
appending to it produces the same content twice under different headings — both of which already
happened here. So the truth moved out of the document into `content/*.json`:

- **One JSON file per section.** Two agents editing different sections touch different files and
  cannot collide. Git-diffable, greppable, reviewable.
- **The builder is deterministic.** Same content in, same document out. Rebuild whenever; the doc
  is disposable, the content is not.
- **The validator catches the defects that actually happen** — malformed rows, invented status
  values, unsourced claims — before they reach the document.

---

## Rules

1. **Never edit the .docx.** Your edits are destroyed on the next build. Edit `content/*.json`.
2. **Claim your section first.** Set `"owner"` to your agent name and `"status": "in-progress"`
   in that file, as your first change. Check nobody else holds it.
3. **One file per agent.** If your finding spans two sections, edit one, and add a line to the
   other's `open_questions` saying what still needs doing there. Do not edit both.
4. **Validate before you finish.** `python build/validate_content.py <your-section>` must exit 0.
5. **Never delete a row to "fix" it.** If a row is wrong, correct it and say so in `notes`, or move
   it to `open_questions`. Losing a finding is worse than carrying a disputed one.
6. **Every claim carries its evidence.** A row with an empty evidence cell is an unsourced claim
   and the validator warns about it. Cite the endpoint plus the HTTP code, or the vendor guide plus
   the page.
7. **Do not upgrade a `DOC` row to `YES` without a live response.** `DOC` means Informatica
   documents it. `YES` means you saw a status code. These are different and the distinction is the
   most valuable thing in this document.
8. **Stamp `last_verified`** (YYYY-MM-DD) whenever you re-confirm a section against a live org.
9. **Do not run `build/seed_content.py` again.** It was a one-time migration and would overwrite
   everyone's work. It refuses without `--force` for that reason.
10. **Re-run `build/build_master.py` when you are done** so the master reflects your work.
11. **No skill work here.** The Claude skill once generated from this corpus is org-specific and is not
    part of this KB. Do not recreate `skill/`, `skill_src/` or `build_skill.py` in this folder.
12. **No secrets and no identities.** No tokens, cookies, private keys or passwords in `content/` or
    any script; read them from environment variables at run time. This folder is in the KB's generic
    zone, so it also carries **no** org, app, customer or person names, org IDs, agent / RE /
    connection / object IDs, IP addresses or VM host names. Use the neutral labels (**Org A** = an org on a
    dm-us pod, **Org B** = a sub-org on a dmp-us pod) and placeholders (`<pod>`, `<orgIdV2>`, `<orgIdV3>`,
    `<agentId>`, `<reId>`, `<connId>`, `<private-ip>`). Domain labels (`dm-us`, `dmp-us`) are platform
    facts and are fine; write pod names as `<pod>`. Before you finish, run the KB's share gate (kept
    outside the shared KB) over the KB root; it must report no hit in this folder.

---

## Section files

Filename prefix sets the order in the document, so leave gaps for insertions.

| Range | What lives there |
|---|---|
| `00`–`09` | Front matter, how to read, authentication, status codes |
| `10`–`29` | **One file per IDMC product** — its API table plus its MCP table |
| `30`–`39` | The consolidated MCP catalog and the API-vs-MCP comparison |
| `50`–`59` | Cross-cutting: caps, UI-only walls, corrections |
| `60`–`89` | Multi-org / per-pod validation |
| `90`+ | Provenance and back matter |

To add a section, drop in a new `NN-name.json` with the shape below. The builder and the contents
table pick it up automatically — no registration step.

### File shape

```json
{
 "id": "12-cdi",                        // MUST equal the filename without .json
 "title": "CDI - Cloud Data Integration",
 "owner": "agent-name-or-null",
 "last_verified": "2026-07-25",         // YYYY-MM-DD, not in the future
 "status": "verified | in-progress | migrated | draft",
 "intro": "One paragraph of context. Optional.",
 "blocks": [ ... ],
 "notes": [ {"label": "Short bold lead-in.", "text": "The point."} ],
 "open_questions": ["What is genuinely still unknown here."]
}
```

### Block types

```json
{"type": "table",   "title": "...", "intro": "...",
 "header": ["Endpoint", "Verbs supported", "What it does", "Notes & evidence"],
 "rows":   [["/api/v2/connection", "GET, POST", "Connection list; create a connection",
             "200 - 10 connections; 201 on create - untested: PUT, PATCH, DELETE"]]}

{"type": "paras",   "title": "...", "text": ["Paragraph one.", "Paragraph two."]}
{"type": "bullets", "title": "...", "items": ["First point.", "Second point."]}
{"type": "callout", "label": "The thing to notice.", "text": "Why it matters."}
{"type": "code",    "title": "...", "text": "POST /identity-service/api/v1/Login"}
```

Every row must have exactly as many cells as the header. The validator enforces it.

---

## The service tables -- the shape to follow

Each IDMC product is one section, containing **one big table** of every endpoint in that service,
then that service's **MCP coverage** immediately underneath. Do not split a service across tables.

API table header, exactly:

```json
["Endpoint", "Verbs supported", "What it does", "Notes & evidence"]
```

MCP table header, exactly:

```json
["MCP action", "Verb", "Server", "What it does", "REST equivalent"]
```

If a service has no MCP server, use a `callout` block instead, labelled
`"MCP coverage for this service:"`.

### The Verbs supported column

**List every verb the endpoint accepts, comma separated.** There is no READ/WRITE/RUN
vocabulary in the service tables any more -- only the Postman verbs.

| Write this | When |
|---|---|
| `GET, POST, DELETE` | All three verified working against a live org. List them all. |
| `PUT [doc]` | Informatica documents that verb; it was not exercised. Suffix `[doc]`. |
| `UI only` | The operation exists but no verb reaches it. |
| `none proven` | No verb has been shown to work. Explain in the notes. |

Rejections and untested verbs go in the **notes** column, not the verb column:

- `rejected: PUT 405` -- that verb was explicitly refused with that code.
- `untested: PUT, PATCH` -- nobody probed them. **UNKNOWN, not unsupported.**

> **`untested` and `rejected` are never merged.** Untested is an admission of ignorance; a 405 is a
> finding (the resource is read-only at any permission level). Conflating them produced every wrong
> conclusion this project has had to walk back. Never write `none proven` where you mean untested.

The validator enforces that every token in a verb column is a real HTTP verb or one of the
qualifiers above.

### One endpoint = one row

If a path supports several operations, they go in **one** row with all verbs listed and the
operations joined by a semicolon in "What it does". Do not repeat the path.

### Cross-cutting sections

The non-service sections (status codes, caps, UI-only walls, corrections, multi-org) still use the
older capability words where they genuinely apply: `WRITE` `RUN` `READ` `UI-ONLY` `GAP` `DOC`, plus
`YES` `NO` `PARTIAL` `DISPUTED` `CONTESTED` `--`. Those are validated too.

## Where to find evidence

- The Informatica guides at https://docs.informatica.com (not bundled). Cite guide plus page for any `DOC` row.
- The recorded probe results and the extraction record (`_extracted_all_tables.json`, every table from
  the two superseded documents) are org-specific and are not part of this KB.
- `probe_idmc_surface.py`, the live probe harness, is not shipped either, because it reads a local
  credential file. It is GET-only by default; `--allow-write` adds a create-and-delete round trip.
  **Reproduce its calls against your own org to re-date a live row** (method in `content/90-provenance.json`).

## Superseded documents

`IDMC API & MCP Capability Reference.docx` and `IDMC Verb Matrix - API vs MCP.docx` were merged
into the master on 2026-07-25 and retired. All 633 of their
data rows are in `content/`. Do not resurrect them; add to the master instead.

---

## Good first tasks

Anything in the contents table with `status: migrated` and no owner needs a pass. In priority order:

1. **`90-provenance.json` is empty** — it needs the sources and re-verification method written up.
2. **Re-probe the four open questions** listed in the master's own open-questions table. Each is a
   live-verifiable fact currently carried as disputed.
3. **Probe the untested verbs** — every `untested:` entry in a service table's notes is a verb nobody
   sent. A live probe (see "Where to find evidence") turns it into a proven verb or a `rejected:` code.
   This is the highest-value grind in the whole document.
4. **Cite the `DOC` rows** — several name a vendor guide but not a page. Add page numbers from
   the guide at https://docs.informatica.com.
5. **Add the MCP table to a service that has none** if a new Informatica server ships covering it.
6. **Split any section that has grown past ~60 rows** into two files at the next free prefix.
