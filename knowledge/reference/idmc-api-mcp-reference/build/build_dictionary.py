#!/usr/bin/env python3
"""
build_dictionary.py — generate the endpoint dictionary from content/*.json.

A lookup view of the same truth the master document carries. The master is organised
by product, for reading. This is organised by path, for answering "I have this
endpoint / this verb — what is it, what can it do, where do I call it?"

READ-ONLY over content/. Writes the dictionary, and with --csv the same data as
spreadsheets, both inside this reference folder:
    claude-idmc-how-to/idmc-endpoint-dictionary.md
    claude-idmc-how-to/csv-every-endpoint/*.csv          (--csv)

It does NOT write the master .docx and does not edit any section file, so it is safe to run
while another agent holds a section (AGENTS.md rules 1-3).

Everything below is derived. The two distinctions the whole knowledge base exists to
preserve are carried through verbatim and never merged:

  verified verb   a live status code was seen          -> "Works"
  [doc] verb      Informatica documents it, unproven   -> "Documented"
  rejected verb   explicitly refused, with the code    -> "Rejected"
  untested verb   nobody probed it. UNKNOWN.           -> "Untested"

Usage:
    python build/build_dictionary.py
    python build/build_dictionary.py --check     # verify, write nothing
    python build/build_dictionary.py --csv       # also write the CSV set
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(ROOT, "content")
# The reader-facing folder IS the output location, not a copy of it. Copies of a
# generated file drift silently, which is the failure AGENTS.md exists to prevent.
HOWTO = os.path.join(ROOT, "claude-idmc-how-to")
OUT = os.path.join(HOWTO, "idmc-endpoint-dictionary.md")
CSVDIR = os.path.join(HOWTO, "csv-every-endpoint")

VERBS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
SERVICE_RANGE = re.compile(r"^(1\d|2\d)-")

# the one-line reading of each verb, for the summary sheet.
VERB_VERDICT = {
    "GET": "The platform's real surface. Nearly everything readable is readable.",
    "POST": "Every write, every run, and on the v2 plane every UPDATE. POST to /{id} IS the update.",
    "PUT": "Rare. None proven in the July 2026 census; proven since on runtime-environment selections, "
           "catalog sources and profiles (L-AUTH-016). Other documented PUTs stay unproven.",
    "PATCH": "Rare. None proven in the July 2026 census; proven since on v3 folders and projects "
             "(L-MIG-105) and data360 content assets (L-CDGC-053). Other documented PATCHes stay unproven.",
    "DELETE": "Rare and clustered - admin, connections, catalog sources, CDQ dictionaries. "
              "It is half of the sanctioned update pattern (DELETE then re-POST).",
}

# the only MCP action that writes anything. Everything else is a read.
MCP_WRITES = {"checkout_data_order"}

# ─────────────────────────────────────────────────────────────────────────────
# Newer evidence from the lessons log (knowledge/lessons/lessons.jsonl).
# content/*.json is the July 2026 probe corpus and is not re-seeded (AGENTS.md
# rule 9). Where a later CURRENT lesson proves an entry wrong or incomplete, the
# note goes here, keyed by the exact endpoint string, so every rebuild carries it.
# The entry's own Works/Rejected line is left as probed; the note says what holds now.
# ─────────────────────────────────────────────────────────────────────────────
LATER_LESSONS = [
    ("/data360/lineage/v1/*", "L-CDGC-181", "2026-10-08",
     "The graph routes are still not found, but lineage IS readable over REST: "
     "`GET /data360/search/v1/assets/<identity>?scheme=internal&segments=all` returns a "
     "`lineage` segment of inbound and outbound data-flow hops (walk it asset by asset) and a "
     "`neighborhood` segment with table- and column-level data-flow edges (L-CDGC-156). "
     "MCP get_asset_details is no longer the only lineage read. Supersedes L-CDGC-085."),
    ("/data360/search/v1/assets", "L-CDGC-181", "2026-10-08",
     "The single-asset form works: `GET /data360/search/v1/assets/<identity>?scheme=internal"
     "&segments=all` reads lineage and neighborhood segments, and `segments=dataQuality` reads "
     "the asset's catalog DQ scores (L-CDGC-266). Use `search/api/v1/search` for queries."),
    ("/data360/glossary/v1/terms", "L-CDGC-051", "2026-09-29",
     "This path stays 404, but glossary authoring is headless: create domains and terms with "
     "`POST /data360/content/v1/assets` (L-CDGC-050, L-CDGC-051) and rename or redefine them with "
     "`PATCH /data360/content/v1/assets/<externalId>?scheme=external` (L-CDGC-053)."),
    ("/data360/businessDataset/v1 (RuleOccurrence)", "L-CDGC-243", "2026-11-19",
     "This path stays 404, but catalog rule occurrences are written through the contentv2 publish, "
     "and their scores are pushed with `PATCH /ccgf-ruleautomation/api/v1/dataQuality/publishScore` "
     "(L-CDGC-243) and read with `segments=dataQuality` (L-CDGC-266)."),
    ("/quality/public/v2/scorecards", "L-DQ-123", "2026-11-02",
     "The CDQ scorecard path stays 404, but per-rule pass rates ARE readable headless: each "
     "bound rule is an `Output` column in the metric store, and "
     "`Profiles('<id>')/Columns('<columnId>')/ValueFrequencies` gives VALID/INVALID counts. "
     "Keep only entries whose totalRows equals the column's current totalRows (L-DQ-151). "
     "Supersedes L-DQ-031."),
    ("/metric-store/api/v1/odata/Profiles('{uuid}')/Columns", "L-DQ-123", "2026-11-02",
     "Bound rule specifications appear here as `Output` columns (columnKey from 40000 up); "
     "`Columns('<columnId>')/ValueFrequencies` returns each rule's VALID/INVALID frequency, i.e. "
     "its pass rate. Page with $top/$skip (20 per page by default). After a re-run, filter value "
     "entries to the current totalRows (L-DQ-151)."),
    ("/metric-store/.../Profiles('{uuid}')/Insights | Patterns | ValueFrequencies", "L-DQ-123",
     "2026-11-02",
     "The profile-level `Profiles('<id>')/ValueFrequencies?$filter=...` form answers 400 "
     "METRIC_STORE_00022; use the column-level `Columns('<columnId>')/ValueFrequencies`."),
    ("/profiling-service/api/v1/profile", "L-DQ-019", "2026-10-03",
     "POST is proven: profiles are created over REST with a body cloned from a known-good "
     "profile, run with `POST /profile/<id>/execute` and polled at `GET /job/<profileJobId>`."),
    ("/profiling-service/api/v1/profile/{uuid}", "L-DQ-019", "2026-10-03",
     "PUT is proven: `PUT /profile/<id>` updates a profile."),
    ("/public/core/v3/license/metering/ExportMeteringData", "L-IPU-021", "2026-10-03",
     "The full cycle works: POST (dates in full ISO-8601 with a zone), poll "
     "`GET .../ExportMeteringData/<jobId>` until SUCCESS, then `GET .../<jobId>/download` for a "
     "ZIP with one CSV per org. `toolkit/lib/idmc_metering.py` wraps it. Job-level metering is "
     "a separate export, `ExportServiceJobLevelMeteringData` (L-IPU-065)."),
    ("/public/core/v3/license/metering/MeteringUsageSummary", "L-IPU-022", "2026-07-26",
     "Still 404; it does not mean metering is not entitled. Use the async export "
     "(`toolkit/lib/idmc_metering.py`)."),
    ("/active-bpel/opsanalytics-das/metrics?query={processJobReport(...)}", "L-CAI-159",
     "2026-11-01",
     "GET is proven: it returns 200 and `data.processJobReport[]` with the header "
     "`IDS-SESSION-ID: <session>`; the documented `Authorization: Bearer <session>` gets 401."),
    ("/public/core/v3/users/{id}", "L-AUTH-058", "2026-09-28",
     "DELETE is proven: `DELETE /public/core/v3/users/<userId>` returns 204 and removes the user. "
     "Edit in place is still not available."),
]

# section-level notes, keyed by the content/ section id
LATER_SECTION_NOTES = {
    "15-cdgc": [
        "Newer evidence (L-CDGC-181, 2026-10-08): the MCP table's 'MCP ONLY for lineage. Every "
        "REST lineage path returns 404' no longer holds. Lineage hops are readable over REST "
        "through the asset read's `lineage` and `neighborhood` segments (L-CDGC-156)."],
}

# global notes, rendered before the Postman section
LATER_GLOBAL = [
    ("PUT and PATCH", "L-AUTH-016, L-METHOD-032, L-MIG-105, L-CDGC-053",
     "The verb counts below are the July 2026 census. Later lessons proved PUT (runtime-"
     "environment selections, catalog sources, profiles) and PATCH (v3 folders and projects, "
     "204; data360 content assets for glossary terms and descriptions; FRS documents). Treat "
     "any other documented PUT or PATCH as unproven until a live call succeeds."),
    ("Lineage", "L-CDGC-181",
     "Readable over REST hop by hop through the asset read's `lineage` segment; the "
     "`/data360/lineage/*` graph routes are still 404."),
    ("Per-rule DQ pass rates", "L-DQ-123",
     "Readable over REST from the metric store's rule `Output` column ValueFrequencies "
     "(supersedes L-DQ-031)."),
    ("MCP catalog", "L-MCP-132, L-MCP-001",
     "The vendor's public MCP registry (`/mcp-registry/v0.1/servers`, no login) listed 23 "
     "managed servers as of the October 2026 release, and an org's managed registry is read at "
     "`/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED`. The 'five managed servers' "
     "count in the MCP dictionary below is the April 2026 catalog."),
    ("IPU metering", "L-IPU-021",
     "The async `ExportMeteringData` job works end to end (start, poll, download); "
     "`toolkit/lib/idmc_metering.py` wraps it."),
]

# the MCP dictionary predates the full registry
LATER_MCP_NOTE = (
    "Newer evidence (L-MCP-132, 2026-11-19; L-MCP-001): the tables below are the April 2026 "
    "catalog. The public registry listed 23 managed servers as of the October 2026 release, "
    "and lists `get_asset_lineage` on the catalog discovery server (registry-only, not called "
    "here; L-MCP-148 reports that server's neighborhood read excludes lineage); the org registry "
    "at `/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED` says what your org exposes "
    "(`/public/core/v3/mcpServers` is not the registry). Asset lineage is no longer an MCP-only "
    "read (L-CDGC-181). Mark each server as called live or registry-only (L-MCP-131).")

# ─────────────────────────────────────────────────────────────────────────────
# which auth plane and host a path lives on.  First match wins, so order matters:
# the more specific prefix must come first.
# ─────────────────────────────────────────────────────────────────────────────
PLANES = [
    (r"^/active-bpel/public/rt/",   "Anonymous CAI",     "<pod>-cai.dm-us.informaticacloud.com",       "no header at all"),
    (r"^/active-bpel/local/",       "CAI runtime",       "<pod>-cai.dm-us.informaticacloud.com",       "INFA-SESSION-ID"),
    (r"^/active-bpel/",             "CAI runtime",       "<pod>-cai.dm-us.informaticacloud.com",       "INFA-SESSION-ID (+ vnd.api+json to publish)"),
    (r"^/process-engine/",          "Secure Agent",      "<agent-host>:<httpPort>",                    "agent-local"),
    (r"^/business-entity/",         "MDM runtime",       "<pod>-mdm.dm-us.informaticacloud.com",       "Bearer + IDS-SESSION-ID + X-INFA-ORG-ID"),
    (r"^/rdm-service/",             "MDM runtime",       "<pod>-mdm.dm-us.informaticacloud.com",       "Bearer + IDS-SESSION-ID + X-INFA-ORG-ID"),
    (r"^/quality/public/",          "CDQ dictionaries",  "<pod>-dqcloud-api.dm-us.informaticacloud.com", "Bearer JWT or IDS-SESSION-ID"),
    (r"^/dataquality/",             "CDQ dictionaries",  "<pod>-dqcloud-api.dm-us.informaticacloud.com", "Bearer JWT or IDS-SESSION-ID"),
    (r"^/profiling-service/",       "Data Profiling",    "<pod>-dqprofile.dm-us.informaticacloud.com", "IDS-SESSION-ID (SPA-injected)"),
    (r"^/metric-store/",            "Data Profiling",    "<pod>-dqprofile.dm-us.informaticacloud.com", "IDS-SESSION-ID (SPA-injected)"),
    (r"^/(ccgf-|cdmp-marketplace/)","CDGC write plane",  "cdgc-api.dm-us.informaticacloud.com",        "Bearer + IDS-SESSION-ID + X-INFA-ORG-ID"),
    (r"^/data360/",                 "Identity / CDGC",   "idmc-api.dm-us.informaticacloud.com",        "Bearer + IDS-SESSION-ID + X-INFA-ORG-ID"),
    (r"^/identity-service/",        "Identity",          "<pod>.dm-us.informaticacloud.com",           "body auth, then IDS-SESSION-ID"),
    (r"^/mcp-servers/",             "MCP servers",       "a2e-prod-<pod>-mcp.dm-us.informaticacloud.com", "IDS-SESSION-ID | Bearer JWT | OAuth2"),
    (r"^/(saas/)?public/core/v3/",  "v3 platform",       "<pod>.dm-us.informaticacloud.com/saas",      "INFA-SESSION-ID"),
    (r"^/public/(apim|api)/",       "v3 platform",       "<pod>.dm-us.informaticacloud.com/saas",      "INFA-SESSION-ID"),
    (r"^/public/(mi|appint|cdgc)/", "v3 platform",       "<pod>.dm-us.informaticacloud.com/saas",      "INFA-SESSION-ID"),
    (r"^/ma/api/v2/",               "v2 platform",       "<pod>.dm-us.informaticacloud.com",           "issues icSessionId"),
    (r"^/api/v2/",                  "v2 platform",       "<pod>.dm-us.informaticacloud.com/saas",      "icSessionId"),
    (r"^/frs/v1/",                  "v3 platform",       "<pod>.dm-us.informaticacloud.com/saas",      "INFA-SESSION-ID"),
    # DBMI has its OWN host. Mapping it to the platform plane is what made every
    # dbmi path look like a 404: proven live 2026-07-26 that <pod>-ing serves real
    # DBMI handlers while the pod/saas host returns a bare 404 for the same path.
    (r"^/(dbmi|mi)/",               "Ingestion (DBMI)",  "<pod>-ing.dm-us.informaticacloud.com",       "Bearer + IDS-SESSION-ID"),
    (r"^/apim/",                    "API Manager",       "<pod>-apigw.dm-us.informaticacloud.com",     "Bearer JWT"),
    (r"^/cdam-policy-api",          "Identity / CDGC",   "idmc-api.dm-us.informaticacloud.com",        "Bearer + IDS-SESSION-ID + X-INFA-ORG-ID"),
    # bare `objects?q=…` is shorthand for the v3 design-object census
    (r"^objects\?",                 "v3 platform",       "<pod>.dm-us.informaticacloud.com/saas",      "INFA-SESSION-ID"),
    # probed on the v3 platform host; every variant 404s, so the plane is where it
    # was looked for, not where it lives
    (r"^/(dataprep|prep)/",         "v3 platform (probed)", "<pod>.dm-us.informaticacloud.com/saas",   "INFA-SESSION-ID"),
]

# 50-limits Service column -> the section files those caps apply to
CAP_SCOPE = {
    "CAI": ("13-cai", "14-cai-runtime"),
    "CDQ": ("16-cdq",),
    "Address Verification": ("16-cdq",),
    "Operational Insights": ("21-operational-insights",),
    "MDM SaaS": ("20-mdm",),
    "Data Profiling": ("17-profiling",),
    "Platform": ("10-admin-core",),
    "MCP": (),
}


def plane_for(path: str):
    for rx, plane, host, hdr in PLANES:
        if re.match(rx, path):
            return plane, host, hdr
    return None, None, None


def is_path(ep: str) -> bool:
    """A real endpoint, as opposed to a capability described in prose."""
    e = ep.strip()
    return e.startswith("/") or e.startswith("<") or e.startswith("objects?")


# ─────────────────────────────────────────────────────────────────────────────
# parsing the two authored columns
# ─────────────────────────────────────────────────────────────────────────────
RE_REJECTED = re.compile(r"rejected:\s*([^;—]+)", re.I)
RE_UNTESTED = re.compile(r"untested:\s*([^;—]+)", re.I)
RE_ALLFIVE = re.compile(r"all five verbs untested", re.I)


def parse_verbs(cell: str):
    """'GET, POST  ·  PUT [doc]' -> (['GET','POST'], ['PUT'], flags)."""
    works, documented, flags = [], [], []
    for tok in re.split(r"[,·]", cell or ""):
        t = tok.strip()
        if not t:
            continue
        low = t.lower()
        if low in ("ui only", "none proven"):
            flags.append(low)
            continue
        m = re.match(r"^(GET|POST|PUT|PATCH|DELETE)\s*(\[doc\])?$", t, re.I)
        if not m:
            flags.append(t)
            continue
        v = m.group(1).upper()
        (documented if m.group(2) else works).append(v)
    return works, documented, flags


def parse_notes(cell: str):
    """Pull rejected/untested verb clauses out, leaving the evidence prose."""
    note = cell or ""
    rejected: "OrderedDict[str, str]" = OrderedDict()
    untested: list[str] = []

    for clause in RE_REJECTED.findall(note):
        for part in clause.split(","):
            m = re.match(r"\s*(GET|POST|PUT|PATCH|DELETE)\s*(\d{3})?", part, re.I)
            if m:
                v = m.group(1).upper()
                if v not in rejected or (m.group(2) and not rejected[v]):
                    rejected[v] = m.group(2) or ""
    for clause in RE_UNTESTED.findall(note):
        for part in clause.split(","):
            m = re.match(r"\s*(GET|POST|PUT|PATCH|DELETE)\s*$", part.strip(), re.I)
            if m and m.group(1).upper() not in untested:
                untested.append(m.group(1).upper())
    if RE_ALLFIVE.search(note):
        untested = list(VERBS)

    ev = RE_REJECTED.sub("", note)
    ev = RE_UNTESTED.sub("", ev)
    ev = RE_ALLFIVE.sub("", ev)
    seen, out = set(), []
    for frag in re.split(r"\s*;\s*|\s{2,}—\s{2,}", ev):
        f = frag.strip(" —·;")
        if f and f.lower() not in seen:
            seen.add(f.lower())
            out.append(f)
    return out, rejected, untested


# A verb column sometimes names the verb that was TRIED while the evidence records that it
# failed — "/api/v2/auditlog | GET | 404 superseded by v3 securityLog". Reporting that as a
# working verb is the false-positive class this whole knowledge base exists to prevent, so
# when every evidence fragment is a bare failure code the verb is demoted to rejected.
FAIL_EV = re.compile(r"^(400|403|404|405|415|500|503)\b")


def demote_failed(rec: dict) -> None:
    ev = [e for e in rec["ev"] if e]
    if not ev or not rec["works"]:
        return
    if not all(FAIL_EV.match(e) for e in ev):
        return
    code = FAIL_EV.match(ev[0]).group(1)
    for v in rec["works"]:
        rec["rejected"].setdefault(v, code)
    rec["demoted"] = True
    rec["works"] = []


def dedupe_prose(text: str) -> str:
    """The restructure concatenated rows, so 'X; X' happens. Collapse it."""
    seen, out = set(), []
    for frag in re.split(r"\s*;\s*", text or ""):
        f = frag.strip()
        if f and f.lower() not in seen:
            seen.add(f.lower())
            out.append(f)
    return "; ".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# load
# ─────────────────────────────────────────────────────────────────────────────
def load():
    services, mcp_rows, cross = OrderedDict(), [], {}
    for f in sorted(glob.glob(os.path.join(CONTENT, "*.json"))):
        sid = os.path.basename(f)[:-5]
        d = json.load(open(f, encoding="utf-8"))
        if not SERVICE_RANGE.match(sid):
            cross[sid] = d
            continue
        entry = {"id": sid, "title": d["title"], "rows": [], "mcp": [],
                 "mcp_note": None, "notes": d.get("notes", []),
                 "open": d.get("open_questions", []),
                 "verified": d.get("last_verified")}
        for b in d.get("blocks", []):
            if b.get("type") == "table" and b["header"][0] == "Endpoint":
                entry["rows"] += b["rows"]
            elif b.get("type") == "table" and b["header"][0] == "MCP action":
                for r in b["rows"]:
                    entry["mcp"].append(r)
                    mcp_rows.append([sid] + r)
            elif b.get("type") == "callout" and "MCP coverage" in (b.get("label") or ""):
                entry["mcp_note"] = b.get("text")
        services[sid] = entry
    return services, mcp_rows, cross


def build_entries(services):
    """One record per endpoint, merging a path that appears in two sections."""
    by_path: "OrderedDict[str, dict]" = OrderedDict()
    caps: "list[dict]" = []
    for sid, svc in services.items():
        for ep, verbs, does, notes in svc["rows"]:
            ep = ep.strip()
            works, documented, flags = parse_verbs(verbs)
            ev, rejected, untested = parse_notes(notes)
            rec = {"ep": ep, "works": works, "doc": documented, "flags": flags,
                   "does": does.strip(), "ev": ev, "rejected": rejected,
                   "untested": untested, "svc": [sid], "title": svc["title"]}
            if not is_path(ep):
                caps.append(rec)
                continue
            if ep in by_path:
                p = by_path[ep]
                for v in works:
                    if v not in p["works"]:
                        p["works"].append(v)
                for v in documented:
                    if v not in p["doc"]:
                        p["doc"].append(v)
                for v, c in rejected.items():
                    p["rejected"].setdefault(v, c)
                for v in untested:
                    if v not in p["untested"]:
                        p["untested"].append(v)
                p["does"] = dedupe_prose(p["does"] + "; " + does.strip())
                for e in ev:
                    if e.lower() not in {x.lower() for x in p["ev"]}:
                        p["ev"].append(e)
                if sid not in p["svc"]:
                    p["svc"].append(sid)
            else:
                by_path[ep] = rec

    # a verb that is proven or documented is not untested; proven beats rejected
    for r in by_path.values():
        # proven wins over documented: a verb we have SEEN work is not "doc only".
        r["doc"] = [v for v in r["doc"] if v not in r["works"]]
        known = set(r["works"]) | set(r["doc"])
        r["untested"] = [v for v in r["untested"] if v not in known]
        for v in list(r["rejected"]):
            if v in r["works"]:
                del r["rejected"][v]
        r["does"] = dedupe_prose(r["does"])
        demote_failed(r)
        # A verb nobody said ANYTHING about is untested, not absent. Making that
        # explicit is the difference between "we did not check" and "it does not
        # work" -- the one conflation this whole document exists to prevent. Do
        # this last so demote_failed() has already moved failures to rejected.
        accounted = set(r["works"]) | set(r["doc"]) | set(r["rejected"]) | set(r["untested"])
        if "ui only" not in r["flags"]:
            r["untested"] += [v for v in VERBS if v not in accounted]
        r["plane"], r["host"], r["hdr"] = plane_for(r["ep"])
    for r in caps:
        r["does"] = dedupe_prose(r["does"])
    return by_path, caps


# ─────────────────────────────────────────────────────────────────────────────
# render
# ─────────────────────────────────────────────────────────────────────────────
def vlist(vs):
    return ", ".join(v for v in VERBS if v in vs) or "—"


def rejlist(d):
    return ", ".join(f"{v} {c}".strip() for v, c in
                     sorted(d.items(), key=lambda kv: VERBS.index(kv[0]))) or "—"


def cap_status(c) -> str:
    """Status of an operation that has no endpoint. Documented-but-unexercised must say
    so; falling through to a dash reads as 'nothing known', which is a different claim."""
    if "ui only" in c["flags"]:
        return "UI only"
    if c["works"]:
        return "Works: " + vlist(c["works"])
    if c["doc"]:
        return "Documented only: " + vlist(c["doc"])
    return "none proven"


def md_escape(s: str) -> str:
    """Escape pipes for a Markdown cell. Always AFTER short(), never before, or the
    ellipsis can cut a backslash off its pipe and break the table."""
    return (s or "").replace("|", "\\|")


def cell(s, n: int = 120) -> str:
    return md_escape(short(s, n))


def render(services, by_path, caps, mcp_rows, cross):
    L: list[str] = []
    A = L.append

    paths = [r for r in by_path.values()]
    verified = [r for r in paths if r["works"]]
    n_ui = sum(1 for r in caps + paths if "ui only" in r["flags"])
    # two different questions: "declared none proven" vs "nothing works on it today"
    n_declared_none = sum(1 for r in paths if "none proven" in r["flags"])
    n_no_verb = sum(1 for r in paths if not r["works"])
    n_doc_only = sum(1 for r in paths if not r["works"] and r["doc"])
    n_demoted = sum(1 for r in paths if r.get("demoted"))

    per_verb_work = {v: sum(1 for r in paths if v in r["works"]) for v in VERBS}
    per_verb_doc = {v: sum(1 for r in paths if v in r["doc"]) for v in VERBS}
    per_verb_rej = {v: sum(1 for r in paths if v in r["rejected"]) for v in VERBS}
    per_verb_unt = {v: sum(1 for r in paths if v in r["untested"]) for v in VERBS}

    A("# IDMC Endpoint Dictionary")
    A("")
    A("Every endpoint in this knowledge base, in one place, answering *what is this path, "
      "which verbs actually work on it, and where do I call it*.")
    A("")
    A("**Generated** by `build/build_dictionary.py` from `content/*.json` — the same source as "
      "the master document that `build/build_master.py` renders (not shipped). Do not edit this "
      "file by hand; edit the section JSON and rebuild. The master document is organised by "
      "product, for reading. This is organised by path, for lookup.")
    A("")
    A(f"**{len(paths)} endpoints** across {len(services)} services, "
      f"**{len(mcp_rows)} MCP actions**, "
      f"plus {len(caps)} operations that have no endpoint at all.")
    A("")
    A("## How to read an entry")
    A("")
    A("Four states, never merged, because conflating them is the mistake this whole document "
      "exists to prevent:")
    A("")
    A("| Label | Means |")
    A("|---|---|")
    A("| **Works** | A live status code was observed on this verb. Trust it. |")
    A("| **Documented** | Informatica documents the verb; nobody exercised it here. Plausible, unproven. |")
    A("| **Rejected** | The verb was explicitly refused, with the code. A `405` is a *finding*: the resource is read-only at any permission level. |")
    A("| **Untested** | Nobody probed it. **Unknown, not unsupported.** Do not quote this as a limitation. |")
    A("")
    A("A `404` with an empty body is a genuine UI-only wall. A `404` *with* a body is usually the "
      "wrong path or wrong host — keep hunting. Full decoder in the appendix.")
    A("")

    # ── newer evidence from the lessons log ───────────────────────────────
    A("## Newer evidence: what later lessons changed")
    A("")
    A("The entries below are the July 2026 probe corpus. These later current lessons in "
      "`knowledge/lessons/lessons.jsonl` change what holds; each affected entry also carries a "
      "*Newer evidence* note. Where a note and an entry disagree, the note wins.")
    A("")
    A("| Topic | What holds now | Lessons |")
    A("|---|---|---|")
    for topic, ids, text in LATER_GLOBAL:
        A(f"| {topic} | {text} | {ids} |")
    A("")
    later = {}
    for ep, lid, date, text in LATER_LESSONS:
        later.setdefault(ep, []).append((lid, date, text))
    missing = [ep for ep in later if ep not in by_path]
    if missing:
        print(f"WARN LATER_LESSONS keys with no endpoint: {missing}")

    # ── the Postman answer ────────────────────────────────────────────────
    A("## The Postman question, answered")
    A("")
    A(f"Across {len(paths)} endpoints:")
    A("")
    A("| Verb | Works | Documented only | Rejected | Untested |")
    A("|---|---:|---:|---:|---:|")
    for v in VERBS:
        A(f"| `{v}` | {per_verb_work[v]} | {per_verb_doc[v]} | {per_verb_rej[v]} | {per_verb_unt[v]} |")
    A("")
    A("What that table means in practice (July 2026 census; see *Newer evidence* above for "
      "the PUT and PATCH routes proven since):")
    A("")
    A(f"- **`GET` and `POST` are the platform.** {per_verb_work['GET']} endpoints read, "
      f"{per_verb_work['POST']} write or run. Everything else is a rounding error.")
    A(f"- **`PUT` is nearly absent and `PATCH` effectively does not exist** — "
      f"{per_verb_work['PUT']} and {per_verb_work['PATCH']} proven respectively. IDMC has almost no "
      "in-place edit. The sanctioned update pattern is `DELETE` then re-`POST` "
      "(`/public/core/v3/users/{id}` is canonical: `PUT` and `PATCH` both 405), or, on the v2 "
      "plane, **`POST` to the `/{id}` path — that *is* the update**.")
    A(f"- **`DELETE` is rare** ({per_verb_work['DELETE']} proven) and clustered in admin, "
      "connections, catalog sources and CDQ dictionaries.")
    A("- **`HEAD` and `OPTIONS` appear nowhere** in any guide or probe. There is no preflight "
      "discovery: to test whether a write verb exists, `POST` an empty body — **400 / 415 / 422 "
      "means the verb is there**, 405 means it is not.")
    A(f"- **{n_no_verb} of the {len(paths)} endpoints have no working verb** — {n_doc_only} "
      f"documented but never exercised, {n_declared_none} explicitly marked *none proven*, and "
      f"{n_demoted} whose source row names a verb but whose only evidence is a failure code, so "
      "this dictionary reports the verb as **Rejected** rather than Works. Separately, "
      f"{n_ui} operations are **UI-only with no endpoint at all**. That gap — read and run over "
      "REST, author and publish in the browser — is the single most important shape of this "
      "platform.")
    A("")

    # ── per-service index ─────────────────────────────────────────────────
    A("## Services")
    A("")
    A("| Service | Endpoints | With a working verb | MCP actions |")
    A("|---|---:|---:|---:|")
    for sid, svc in services.items():
        eps = [r for r in paths if sid in r["svc"]]
        A(f"| [{md_escape(svc['title'])}](#{anchor(svc['title'])}) | {len(eps)} | "
          f"{sum(1 for r in eps if r['works'])} | {len(svc['mcp']) or '—'} |")
    A("")

    # ── alphabetical index ────────────────────────────────────────────────
    A("## Index — every endpoint, alphabetical")
    A("")
    A("| Endpoint | Works | What it does |")
    A("|---|---|---|")
    for r in sorted(paths, key=lambda x: x["ep"].lower()):
        w = vlist(r["works"])
        if w == "—":
            w = "*none proven*" if "none proven" in r["flags"] else "*doc only*" if r["doc"] else "—"
        A(f"| `{md_escape(r['ep'])}` | {w} | {cell(r['does'])} |")
    A("")

    # ── the entries ───────────────────────────────────────────────────────
    A("---")
    A("")
    A("# Entries by service")
    A("")
    for sid, svc in services.items():
        A(f"## {svc['title']}")
        A("")
        if svc["verified"]:
            A(f"*Last verified {svc['verified']}.*")
            A("")
        eps = [r for r in sorted(paths, key=lambda x: x["ep"].lower()) if sid in r["svc"]]
        for r in eps:
            A(f"### `{r['ep']}`")
            A("")
            A(f"{r['does'] or '—'}")
            A("")
            bits = []
            if r["works"]:
                bits.append(f"**Works:** {vlist(r['works'])}")
            elif "ui only" in r["flags"]:
                bits.append("**Works:** none — *UI only*")
            elif r.get("demoted"):
                bits.append("**Works:** none *(the verb below was refused)*")
            else:
                bits.append("**Works:** none proven")
            if r["doc"]:
                bits.append(f"**Documented:** {vlist(r['doc'])}")
            if r["rejected"]:
                bits.append(f"**Rejected:** {rejlist(r['rejected'])}")
            if r["untested"]:
                bits.append(f"**Untested:** {vlist(r['untested'])}")
            A(" · ".join(bits))
            A("")
            if r["plane"]:
                A(f"*Plane:* {r['plane']} — `{r['host']}` · header `{r['hdr']}`")
                A("")
            if r["ev"]:
                A(f"*Evidence:* {'; '.join(r['ev'])}")
                A("")
            if len(r["svc"]) > 1:
                A(f"*Also documented under:* {', '.join(x for x in r['svc'] if x != sid)}")
                A("")
            for lid, date, text in later.get(r["ep"], []):
                A(f"> **Newer evidence ({lid}, {date}):** {text}")
                A("")

        own_caps = [c for c in caps if sid in c["svc"]]
        if own_caps:
            A("#### No endpoint exists for these")
            A("")
            A("| Operation | Status | What it does | Where it happens |")
            A("|---|---|---|---|")
            for c in own_caps:
                st = cap_status(c)
                A(f"| {md_escape(c['ep'])} | {st} | {cell(c['does'])} | "
                  f"{cell('; '.join(c['ev']) or '—')} |")
            A("")

        if svc["mcp"]:
            A("#### MCP coverage")
            A("")
            A("| Action | Verb | Server | What it does | REST equivalent |")
            A("|---|---|---|---|---|")
            for m in svc["mcp"]:
                A("| " + " | ".join(cell(c, 150) for c in m) + " |")
            A("")
        elif svc["mcp_note"]:
            A(f"**MCP coverage:** {svc['mcp_note']}")
            A("")

        caps_here = [c for s, c in cap_rows(cross) if sid in CAP_SCOPE.get(s, ())]
        if caps_here:
            A("#### Caps that bite here")
            A("")
            for what, limit, src in caps_here:
                A(f"- **{what}** — {limit} *({src})*")
            A("")
        for n in svc["notes"]:
            A(f"> **{n.get('label','')}** {n.get('text','')}")
            A("")
        for q in svc["open"]:
            A(f"> ⚠️ **Open question.** {q}")
            A("")
        for n in LATER_SECTION_NOTES.get(sid, []):
            A(f"> {n}")
            A("")

    # ── MCP dictionary ────────────────────────────────────────────────────
    A("---")
    A("")
    A("# MCP dictionary")
    A("")
    A(f"> {LATER_MCP_NOTE}")
    A("")
    mcp = cross.get("30-mcp-servers")
    if mcp:
        if mcp.get("intro"):
            A(mcp["intro"])
            A("")
        for b in mcp.get("blocks", []):
            if b.get("type") == "table":
                A(f"### {b.get('title') or 'Actions'}")
                A("")
                A("| " + " | ".join(b["header"]) + " |")
                A("|" + "---|" * len(b["header"]))
                for row in b["rows"]:
                    A("| " + " | ".join(cell(c, 200) for c in row) + " |")
                A("")
        for n in mcp.get("notes", []):
            A(f"> **{n.get('label','')}** {n.get('text','')}")
            A("")

    delta = cross.get("31-api-vs-mcp")
    if delta:
        A("### REST or MCP — which to reach for")
        A("")
        for b in delta.get("blocks", []):
            if b.get("type") == "table":
                A("| " + " | ".join(b["header"]) + " |")
                A("|" + "---|" * len(b["header"]))
                for row in b["rows"]:
                    A("| " + " | ".join(cell(c, 200) for c in row) + " |")
                A("")

    # ── appendices ────────────────────────────────────────────────────────
    A("---")
    A("")
    A("# Appendix — everything you need to actually make a call")
    A("")
    for sid, head in [("02-authentication", "Authentication planes"),
                      ("03-status-codes", "Status-code decoder"),
                      ("51-ui-only-walls", "The UI-only walls"),
                      ("50-limits", "Documented caps")]:
        d = cross.get(sid)
        if not d:
            continue
        A(f"## {head}")
        A("")
        for b in d.get("blocks", []):
            if b.get("type") != "table":
                continue
            if b.get("title"):
                A(f"**{b['title']}**")
                A("")
            A("| " + " | ".join(b["header"]) + " |")
            A("|" + "---|" * len(b["header"]))
            for row in b["rows"]:
                A("| " + " | ".join(cell(c, 200) for c in row) + " |")
            A("")

    A("---")
    A("")
    A(f"*Generated from `content/*.json` by `build/build_dictionary.py`. "
      f"{len(paths)} endpoints · {len(mcp_rows)} MCP actions · {len(caps)} endpointless operations.*")
    return "\n".join(L) + "\n"


def cap_rows(cross):
    d = cross.get("50-limits")
    if not d:
        return []
    out = []
    for b in d.get("blocks", []):
        if b.get("type") == "table" and b["header"][0] == "Service":
            for svc, what, limit, src in b["rows"]:
                out.append((svc, (what, limit, src)))
    return out


def short(s: str, n: int = 120) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def anchor(title: str) -> str:
    a = title.lower()
    a = re.sub(r"[^a-z0-9 \-]", "", a)
    return a.replace(" ", "-")


# ─────────────────────────────────────────────────────────────────────────────
# CSV — the same records, at two grains
# ─────────────────────────────────────────────────────────────────────────────
def _w(name, header, rows):
    """UTF-8 with BOM so Excel opens it directly; LF line ends to match .gitattributes (eol=lf)."""
    p = os.path.join(CSVDIR, name)
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(header)
        wr.writerows(rows)
    print(f"  {name:<34} {len(rows):>4} rows")
    return p


def state_of(rec, verb):
    """The one question this whole corpus answers, for one endpoint and one verb."""
    if verb in rec["works"]:
        return "WORKS", ""
    if verb in rec["doc"]:
        return "DOCUMENTED", ""
    if verb in rec["rejected"]:
        return "REJECTED", rec["rejected"][verb]
    if verb in rec["untested"]:
        return "UNTESTED", ""
    if "ui only" in rec["flags"]:
        return "UI-ONLY", ""
    return "UNTESTED", ""


def write_csvs(services, by_path, caps, mcp_rows, cross):
    os.makedirs(CSVDIR, exist_ok=True)
    paths = list(by_path.values())
    title = {sid: s["title"] for sid, s in services.items()}
    print("\nCSV set:")

    # 01 — one row per endpoint. The wide sheet you read.
    rows = []
    for r in sorted(paths, key=lambda x: (title[x["svc"][0]], x["ep"].lower())):
        rows.append([
            title[r["svc"][0]], r["ep"], r["does"],
            vlist(r["works"]) if r["works"] else "",
            vlist(r["doc"]) if r["doc"] else "",
            rejlist(r["rejected"]) if r["rejected"] else "",
            vlist(r["untested"]) if r["untested"] else "",
            "YES" if r["works"] else "NO",
            "YES" if r.get("demoted") else "",
            r["plane"], r["host"], r["hdr"],
            "; ".join(r["ev"]),
            "; ".join(title.get(s, s) for s in r["svc"][1:]),
            r["svc"][0],
        ])
    _w("01_endpoints.csv",
       ["Service", "Endpoint", "What it does", "Works (proven)", "Documented only",
        "Rejected (verb + code)", "Untested", "Any working verb?",
        "Demoted (verb named but evidence is a failure)", "Auth plane", "Host",
        "Header", "Evidence", "Also under", "Section id"], rows)

    # 02 — one row per endpoint x verb. The sheet you pivot and filter.
    rows = []
    for r in sorted(paths, key=lambda x: x["ep"].lower()):
        for v in VERBS:
            st, code = state_of(r, v)
            rows.append([
                r["ep"], v, st, code,
                "YES" if st == "WORKS" else "NO",
                "YES" if st in ("WORKS", "DOCUMENTED") else "NO",
                title[r["svc"][0]], r["plane"], r["host"], r["hdr"],
                r["does"], "; ".join(r["ev"]),
            ])
    _w("02_endpoint_verb_matrix.csv",
       ["Endpoint", "Verb", "State", "Rejection code", "Safe to script today?",
        "Believed supported?", "Service", "Auth plane", "Host", "Header",
        "What it does", "Evidence"], rows)

    # 03 — the Postman answer, per verb.
    rows = []
    for v in VERBS:
        w = sum(1 for r in paths if v in r["works"])
        d = sum(1 for r in paths if v in r["doc"])
        j = sum(1 for r in paths if v in r["rejected"])
        u = sum(1 for r in paths if v in r["untested"])
        rows.append([v, w, d, j, u, len(paths),
                     f"{100.0 * w / len(paths):.1f}%", VERB_VERDICT.get(v, "")])
    for v in ("HEAD", "OPTIONS"):
        rows.append([v, 0, 0, 0, 0, len(paths), "0.0%",
                     "Appears in no guide and no probe. There is no preflight discovery in IDMC: "
                     "to test a write verb, POST an empty body - 400/415/422 means the verb exists, "
                     "405 means it does not."])
    _w("03_postman_verb_summary.csv",
       ["Verb", "Works (proven)", "Documented only", "Rejected", "Untested",
        "Endpoints total", "% proven", "What this means in IDMC"], rows)

    # 04 — per service.
    rows = []
    for sid, svc in services.items():
        eps = [r for r in paths if sid in r["svc"]]
        rows.append([
            svc["title"], len(eps),
            sum(1 for r in eps if r["works"]),
            sum(1 for r in eps if not r["works"] and r["doc"]),
            sum(1 for r in eps if not r["works"] and not r["doc"]),
            *[sum(1 for r in eps if v in r["works"]) for v in VERBS],
            len(svc["mcp"]), len([c for c in caps if sid in c["svc"]]),
            svc["verified"] or "", sid,
        ])
    _w("04_service_rollup.csv",
       ["Service", "Endpoints", "With a working verb", "Documented only", "None proven",
        *[f"{v} proven" for v in VERBS], "MCP actions", "Endpointless operations",
        "Last verified", "Section id"], rows)

    # 05 — MCP. Every action, its server, and the REST it wraps.
    rows = []
    for row in mcp_rows:
        sid, action, verb, server, does, rest = (row + [""] * 6)[:6]
        # the REST-equivalent cell is prose, so read its verdict rather than parse a path.
        low = (rest or "").lower()
        if not rest.strip() or "mcp only" in low or "no rest" in low:
            reach = "NO - MCP only"
        elif "disputed" in low:
            reach = "DISPUTED"
        else:
            reach = "YES"
        rows.append([action, verb or "POST", server, title.get(sid, sid), does, rest,
                     "WRITE" if action in MCP_WRITES else "READ", reach])
    _w("05_mcp_actions.csv",
       ["MCP action", "Verb", "MCP server", "Backing IDMC service", "What it does",
        "REST equivalent", "Read or write", "Reachable over REST too?"], rows)

    # 06 — operations with no endpoint at all. The UI-only wall.
    rows = []
    for c in sorted(caps, key=lambda x: (title.get(x["svc"][0], ""), x["ep"].lower())):
        rows.append([title.get(c["svc"][0], c["svc"][0]), c["ep"], c["does"],
                     cap_status(c), "; ".join(c["ev"])])
    _w("06_no_endpoint_ui_only.csv",
       ["Service", "Operation", "What it does", "Status", "Evidence"], rows)

    # 07 — auth planes, deduped off the live records.
    seen, rows = set(), []
    for r in paths:
        k = (r["plane"], r["host"], r["hdr"])
        if r["plane"] and k not in seen:
            seen.add(k)
            rows.append([r["plane"], r["host"], r["hdr"],
                         sum(1 for x in paths if (x["plane"], x["host"], x["hdr"]) == k)])
    rows.sort(key=lambda x: -x[3])
    _w("07_auth_planes.csv",
       ["Auth plane", "Host pattern", "Header(s) to send", "Endpoints on this plane"], rows)

    # 08-10 — the cross-cutting reference tables, passed through verbatim.
    for sid, fname in [("03-status-codes", "08_status_code_decoder.csv"),
                       ("50-limits", "09_limits_and_caps.csv"),
                       ("51-ui-only-walls", "10_ui_only_walls.csv")]:
        d = cross.get(sid)
        if not d:
            continue
        hdr, out = None, []
        for b in d.get("blocks", []):
            if b.get("type") != "table":
                continue
            if hdr is None:
                hdr = b["header"]
            if b["header"] == hdr:
                out += [list(x) for x in b["rows"]]
        if hdr:
            _w(fname, hdr, out)
    return CSVDIR


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="render but write nothing")
    ap.add_argument("--csv", action="store_true", help="also write claude-idmc-how-to/csv-every-endpoint/*.csv")
    args = ap.parse_args()

    services, mcp_rows, cross = load()
    by_path, caps = build_entries(services)
    text = render(services, by_path, caps, mcp_rows, cross)

    paths = list(by_path.values())
    print(f"services       : {len(services)}")
    print(f"endpoints      : {len(paths)}")
    print(f"  working verb : {sum(1 for r in paths if r['works'])}")
    print(f"  doc only     : {sum(1 for r in paths if not r['works'] and r['doc'])}")
    print(f"  none proven  : {sum(1 for r in paths if not r['works'] and not r['doc'])}")
    print(f"endpointless   : {len(caps)}")
    print(f"MCP actions    : {len(mcp_rows)}")
    unplaned = [r["ep"] for r in paths if not r["plane"]]
    if unplaned:
        print(f"WARN no plane mapped ({len(unplaned)}): {unplaned}")
    for v in VERBS:
        print(f"  {v:<7} works {sum(1 for r in paths if v in r['works']):>3}"
              f"  doc {sum(1 for r in paths if v in r['doc']):>3}"
              f"  rejected {sum(1 for r in paths if v in r['rejected']):>3}"
              f"  untested {sum(1 for r in paths if v in r['untested']):>3}")
    if args.check:
        print("\n--check: nothing written")
        return 0
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"\nwrote {OUT}  ({len(text):,} bytes, {text.count(chr(10)):,} lines)")
    if args.csv:
        print(f"wrote {write_csvs(services, by_path, caps, mcp_rows, cross)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
