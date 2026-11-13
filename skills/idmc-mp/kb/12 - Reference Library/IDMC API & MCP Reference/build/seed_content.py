#!/usr/bin/env python3
"""
seed_content.py -- ONE-TIME migration.

Reads _evidence/_extracted_all_tables.json (every table from the two superseded
.docx deliverables) and writes the per-section JSON content files that are now
the single source of truth for the master document.

After this has run, DO NOT run it again -- it would overwrite agent edits.
It refuses to overwrite unless --force is passed.
Its input (_evidence/_extracted_all_tables.json) is org-specific evidence and is not shipped with
this KB.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(ROOT, "content")
SRC = os.path.join(ROOT, "_evidence", "_extracted_all_tables.json")

# section-id -> (title, owner-hint, [table indexes from the extract])
# 'capref' tables are 0..39, 'verbmatrix' tables are 40..56 in the merged list.
PLAN = [
    ("00-frontmatter",       "Front matter, how to read, status vocabulary", [0]),
    ("01-executive-summary", "Executive summary - every service at a glance", [1]),
    ("02-authentication",    "Authentication - the planes and the token flow", [2, 3]),
    ("03-status-codes",      "Reading the response - status codes and error fingerprints", [4, 27]),
    ("10-admin-core",        "Administration & Core platform", [5]),
    ("11-migration",         "Migration API - export & import", [6]),
    ("12-cdi",               "CDI - Cloud Data Integration", [7]),
    ("13-cai",               "CAI - Cloud Application Integration", [8]),
    ("14-cai-runtime",       "CAI - runtime administration", [9, 28]),
    ("15-cdgc",              "CDGC - Cloud Data Governance & Catalog", [10]),
    ("16-cdq",               "CDQ - Cloud Data Quality", [11]),
    ("17-profiling",         "Data Profiling", [12, 29]),
    ("18-mass-ingestion",    "Mass Ingestion - CMI, DBMI, file, app, streaming", [13]),
    ("19-marketplace",       "Data Marketplace", [14]),
    ("20-mdm",               "MDM, Customer 360, Business 360 & Reference 360", [15, 16]),
    ("21-operational-insights", "Operational Insights", [17]),
    ("22-dam-apim-claire",   "Data Access Management, API Manager & CLAIRE", [18]),
    ("30-mcp-servers",       "Informatica MCP servers", [19, 20, 33, 34, 35, 36]),
    ("31-api-vs-mcp",        "API vs MCP - the comparison", [37]),
    ("40-verb-matrix",       "The verb matrix - GET/POST/PUT/PATCH/DELETE per endpoint",
     list(range(40, 57))),
    ("50-limits",            "Documented caps, throttles and timeouts", [21, 38]),
    ("51-ui-only-walls",     "The UI-only walls, consolidated", [22]),
    ("52-corrections",       "Corrections - documentation versus testing", [23, 39]),
    ("60-multi-org",         "Multi-org validation - per-pod differences", [24, 25, 26, 30, 31, 32]),
    ("90-provenance",        "Sources, provenance and how to re-verify", []),
]


def main():
    force = "--force" in sys.argv
    data = json.load(open(SRC, encoding="utf-8"))
    tables = data["tables"]
    os.makedirs(CONTENT, exist_ok=True)

    written = 0
    for sid, title, idxs in PLAN:
        path = os.path.join(CONTENT, sid + ".json")
        if os.path.exists(path) and not force:
            print("SKIP (exists):", sid)
            continue
        blocks = []
        for i in idxs:
            if i >= len(tables):
                continue
            t = tables[i]
            blocks.append({
                "type": "table",
                "title": t.get("section") or "",
                "header": t["header"],
                "rows": t["rows"],
                "_migrated_from": t["src"] + "#" + str(t["idx"]),
            })
        doc = {
            "id": sid,
            "title": title,
            "owner": None,
            "last_verified": "2026-07-25",
            "status": "migrated",
            "intro": "",
            "blocks": blocks,
            "notes": [],
            "open_questions": [],
        }
        json.dump(doc, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        written += 1
        print("wrote", sid, "-", len(blocks), "table block(s)")
    print("\n%d section files written to content/" % written)


if __name__ == "__main__":
    main()
