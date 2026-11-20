---
description: Scan a source into the catalog (CDGC), link glossary terms, and show lineage
argument-hint: "<source system or connection> [glossary or report]"
---

Use the idmc-mp and idmc-governance skills. On Windows, use `python` (or `py`) where these steps say `python3`.
Source: $ARGUMENTS

1. Prove the org, then check CDGC access (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_cdgc.py" --help`; auth in
   `${CLAUDE_PLUGIN_ROOT}/knowledge/09-catalog-lineage/01-cdgc-apis-auth.md`).
2. List existing catalog sources first; reuse one if it already covers the system.
3. Create the catalog source by cloning a working definition, then scan and poll
   (`02-catalog-sources-create-scan-update-purge.md`). Ask before running a scan.
4. Glossary: create or reuse domains and terms and link them to assets (`03-glossary-links-classification.md`).
5. Show what was found: asset counts by type, the lineage path the user asked for, and links made, with ids.
   Before saying something cannot be done, read `05-cdgc-gaps-gotchas.md` and work the ladder.
