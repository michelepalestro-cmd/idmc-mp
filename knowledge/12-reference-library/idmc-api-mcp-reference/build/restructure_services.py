#!/usr/bin/env python3
"""
restructure_services.py -- rebuilds the per-service section files in the new shape.

New shape, as specified by the KB owner on 2026-07-25:
  * ONE big table per service (the product = the section)
  * NO READ / WRITE / RUN vocabulary anywhere. Only the Postman verbs.
  * The Verbs column LISTS every verb the endpoint accepts, comma separated.
  * Immediately after the API table, the SAME service's MCP coverage.

Joins two legacy data modules on the endpoint path:
  _build/fable_run/idmc_kb_data_fable.py      -- what each endpoint does + evidence
  _build/fable_run/idmc_verbmatrix_data.py    -- per-verb support

Run once. It overwrites the service section files only.
Do NOT re-run: its two legacy input modules (_build/fable_run/*.py) are org-specific evidence and
are not shipped with this KB.
"""
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(ROOT, "content")
LEGACY = os.path.join(ROOT, "_build", "fable_run")

VERBS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def load(modname, filename):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(LEGACY, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CAP = load("cap", "idmc_kb_data_fable.py")
VM = load("vm", "idmc_verbmatrix_data.py")


def norm(p):
    """Normalise a path for joining: strip host, params, placeholders, case.

    /saas is a base-URL prefix, not part of the resource, so it is stripped --
    otherwise /saas/public/core/v3/login and /public/core/v3/login look like two
    different endpoints and the table shows the same login twice.
    """
    s = str(p).strip().lower()
    s = s.split("?")[0]
    s = re.sub(r"\{[^}]*\}", "{}", s)
    s = re.sub(r"\s*\(.*?\)\s*", "", s)
    s = re.sub(r"^/(saas|ma)/", "/", s)
    s = s.rstrip("/ ")
    return s


def verbs_and_notes(vmrow):
    """From [path, G, P, PU, PA, D, note] -> (verb list string, rejection string)."""
    ok, doc, ui, rej, unk = [], [], [], [], []
    for i, v in enumerate(VERBS):
        cell = str(vmrow[i + 1]).strip()
        if cell == "YES":
            ok.append(v)
        elif cell == "DOC":
            doc.append(v)
        elif cell == "UI":
            ui.append(v)
        elif cell and cell[0] in "45" and cell.isdigit():
            rej.append("%s %s" % (v, cell))
        elif cell in ("--", "-", ""):
            unk.append(v)
    parts = []
    if ok:
        parts.append(", ".join(ok))
    if doc:
        parts.append(", ".join(v + " [doc]" for v in doc))
    if ui:
        parts.append("UI only")
    verbstr = "  ·  ".join(parts) if parts else "none proven"
    extra = []
    if rej:
        extra.append("rejected: " + ", ".join(rej))
    if unk and len(unk) < 5:
        extra.append("untested: " + ", ".join(unk))
    elif len(unk) == 5 and not parts:
        extra.append("all five verbs untested")
    return verbstr, "; ".join(extra)


# service id -> (title, capability list, verb-matrix list, mcp rows, mcp intro)
NO_MCP = "No MCP server covers this service. Everything here is REST-only."

MCP_JOB = [
    ["run_mapping_task", "POST", "Job Management",
     "Triggers a mapping task with runtime parameters.",
     "Wraps POST /api/v2/job. REST is equivalent."],
    ["get_job_status", "POST", "Job Management",
     "Live execution state, row counts and error logs for one job.",
     "Wraps GET /api/v2/activity/activityLog. REST returns full history, MCP one job."],
    ["stop_running_job", "POST", "Job Management",
     "Immediate termination request to the Secure Agent.",
     "Wraps the v2 Stop Job resource."],
]
MCP_CDGC = [
    ["search_metadata", "POST", "CDGC Metadata Search",
     "Natural-language catalog query returning matching asset IDs and core attributes.",
     "Wraps POST /data360/search/api/v1/search. REST is richer: raw Elasticsearch DSL."],
    ["get_asset_details", "POST", "CDGC Metadata Search",
     "Full metadata for one asset, INCLUDING lineage, profile and descriptions.",
     "MCP ONLY for lineage. Every REST lineage path returns 404."],
]
MCP_MDM = [
    ["search_master_record", "POST", "Customer Identification",
     "Fuzzy identity match returning the business ID of the best-matching master record.",
     "MCP ONLY. REST has no public MDM search or list resource."],
    ["get_master_record_details", "POST", "Customer Identification",
     "The consolidated golden record, merged across source systems.",
     "REST equivalent is the disputed GET on entity/{be}/{id}. MCP is the safer path."],
]
MCP_DMP = [
    ["list_data_collections", "POST", "Data Provisioning",
     "Lists marketplace data collections; optional name and search filters.",
     "Wraps GET /data360/marketplace/api/v1/dataCollections."],
    ["list_delivery_targets", "POST", "Data Provisioning",
     "Returns collection detail. Despite the name it does NOT return a target list.",
     "Wraps the cdmp-marketplace provisioning reads."],
    ["checkout_data_order", "POST", "Data Provisioning",
     "Raises a formal access request. Requires a business justification.",
     "The only MCP action that persists anything new. Wraps POST .../orders."],
]
MCP_CDQ = [
    ["verify_address", "POST", "Address Verification",
     "Validates, standardizes and geocodes an address. 240+ countries.",
     "Wraps POST /dataquality/addressverification/api/v1/process. REST does 1,000 per call, MCP one."],
]

PLAN = [
    ("10-admin-core", "Administration & Core platform",
     CAP.ADMIN, VM.VM_ADMIN, [], NO_MCP),
    ("11-migration", "Migration - export & import",
     CAP.MIGRATION, VM.VM_MIGR, [], NO_MCP),
    ("12-cdi", "CDI - Cloud Data Integration",
     CAP.CDI, VM.VM_CDI, MCP_JOB,
     "The Job Management MCP server covers CDI. Three actions, all thin wrappers over the v2 "
     "job plane - it can run, watch and stop a task, exactly as REST can. It cannot create a "
     "connection, author a mapping or set a schedule."),
    ("13-cai", "CAI - Cloud Application Integration (asset lifecycle)",
     CAP.CAI, VM.VM_CAI_ASSET, [], NO_MCP),
    ("14-cai-runtime", "CAI - invocation & runtime administration",
     CAP.CAI_ADMIN, VM.VM_CAI_RT, [], NO_MCP),
    ("15-cdgc", "CDGC - Cloud Data Governance & Catalog",
     CAP.CDGC, VM.VM_CDGC, MCP_CDGC,
     "The CDGC Metadata Search MCP server covers this service. Two actions. One of them is the "
     "single most important thing MCP has that REST does not: get_asset_details returns LINEAGE, "
     "which no REST endpoint on this platform will give you."),
    ("16-cdq", "CDQ - Cloud Data Quality",
     CAP.CDQ, VM.VM_CDQ, MCP_CDQ,
     "The Address Verification MCP server covers one corner of CDQ. Nothing in MCP touches "
     "dictionaries, rules or scorecards."),
    ("17-profiling", "Data Profiling",
     CAP.PROF, VM.VM_PROF, [],
     "No dedicated MCP server. Profiling statistics do reach MCP indirectly - the CDGC "
     "get_asset_details action bundles profile data into its response."),
    ("18-mass-ingestion", "Mass Ingestion - CMI, DBMI, file, application, streaming",
     CAP.CMI, VM.VM_CMI, [], NO_MCP),
    ("19-marketplace", "Data Marketplace",
     CAP.DMP, VM.VM_DMP, MCP_DMP,
     "The Data Provisioning MCP server covers Data Marketplace, and it holds the only write "
     "action in the entire MCP catalog: checkout_data_order."),
    ("20-mdm", "MDM, Customer 360, Business 360 & Reference 360",
     CAP.MDM, VM.VM_MDM, MCP_MDM,
     "The Customer Identification MCP server covers MDM. Its fuzzy-match action is the second "
     "thing MCP can do that REST cannot, because REST exposes no public search resource here."),
    ("21-operational-insights", "Operational Insights",
     CAP.OI, VM.VM_OI, [], NO_MCP),
    ("22-dam-apim-claire", "Data Access Management, API Manager & CLAIRE",
     CAP.OTHER, VM.VM_OTHER, [], NO_MCP),
]

API_HDR = ["Endpoint", "Verbs supported", "What it does", "Notes & evidence"]
MCP_HDR = ["MCP action", "Verb", "Server", "What it does", "REST equivalent"]


def build_api_rows(caps, vms):
    """One row per endpoint. Verb column lists every supported verb."""
    vindex = {}
    for r in vms:
        vindex.setdefault(norm(r[0]), r)

    rows = []
    used = set()
    seen = {}          # norm(path) -> index into rows, so one endpoint = one row
    for c in caps:
        # capability rows are [verb, path, does, status, evidence]
        # or, for OTHER, [service, path, does, status, evidence]
        path, does, evidence = c[1], c[2], c[4]
        key = norm(path)
        vm = vindex.get(key)
        if vm:
            used.add(key)
            verbstr, rej = verbs_and_notes(vm)
            note = evidence
            if rej:
                note = (note + "  —  " + rej) if note else rej
        else:
            # no verb-matrix row: fall back to the verb named in the capability row
            v = str(c[0]).strip()
            verbstr = v if v.upper() in VERBS or "/" in v else "none proven"
            if verbstr == "none proven" and "UI" in str(c[3]):
                verbstr = "UI only"
            note = evidence

        if key in seen:
            # same endpoint, another operation: merge into the existing row rather
            # than repeating the path. "What it does" becomes a semicolon list.
            i = seen[key]
            if does and does not in rows[i][2]:
                rows[i][2] = rows[i][2] + "; " + does
            if note and note not in rows[i][3]:
                rows[i][3] = rows[i][3] + "; " + note
            continue
        seen[key] = len(rows)
        rows.append([path, verbstr, does, note])

    # carry any verb-matrix endpoint the capability list never mentioned
    for r in vms:
        if norm(r[0]) in used:
            continue
        verbstr, rej = verbs_and_notes(r)
        note = r[6]
        if rej:
            note = note + "  —  " + rej
        rows.append([r[0], verbstr, r[6], note if note != r[6] else ""])
    return rows


def main():
    for sid, title, caps, vms, mcp, mcpintro in PLAN:
        path = os.path.join(CONTENT, sid + ".json")
        old = {}
        if os.path.exists(path):
            old = json.load(open(path, encoding="utf-8"))

        api_rows = build_api_rows(caps, vms)
        blocks = [{
            "type": "table",
            "title": "",
            "intro": "Every endpoint in this service, with the exact HTTP verbs it accepts. "
                     "Where an endpoint accepts more than one verb they are all listed.",
            "header": API_HDR,
            "rows": api_rows,
        }]
        if mcp:
            blocks.append({
                "type": "table",
                "title": "MCP coverage for this service",
                "intro": mcpintro,
                "header": MCP_HDR,
                "rows": mcp,
            })
        else:
            blocks.append({
                "type": "callout",
                "label": "MCP coverage for this service:",
                "text": mcpintro,
            })

        doc = {
            "id": sid,
            "title": title,
            "owner": old.get("owner"),
            "last_verified": old.get("last_verified", "2026-07-25"),
            "status": "restructured",
            "intro": old.get("intro", ""),
            "blocks": blocks,
            "notes": old.get("notes", []),
            "open_questions": old.get("open_questions", []),
        }
        json.dump(doc, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("%-26s %3d API rows   %d MCP rows" % (sid, len(api_rows), len(mcp)))


if __name__ == "__main__":
    main()
