#!/usr/bin/env python3
"""bid_teardown.py - remove the Bid Desk, in reverse build order. Prints the plan; each step runs only with --execute.

    python bid_teardown.py plan                                  # the ordered undo list with the exact commands (no login)
    python bid_teardown.py export [--execute --expect-org <id>]  # FIRST: a v3 export of the whole project (your restore point)
    python bid_teardown.py idmc [--execute --expect-org <id>]    # steps 2-8 below, each through the core library's guarded tools

Order (each step undoes one BUILD step; never delete what you cannot restore):
  1  export the project (toolkit/lib/idmc_export_import.py export --id <projectId> --out <file outside the toolkit>)
  2  detach the schedule            idmc/bid_taskflows.py detach --execute ...       (then disable/delete the schedule)
  3  access limit undo (if used)    idmc/bid_access.py undo --execute ...
  4  glossary undo                  idmc/bid_glossary.py undo --execute ...
  5  lineage MERGEs undo            the registry in state/ids.json "merges": same body with operationType=SPLIT
  6  catalog sources                REST DELETE only PURGES a source's metadata; the definition is removed in Metadata Command
                                    Center > Catalog Sources > <source> > Delete (UI)
  7  taskflows, tasks, mappings, CLAIRE models, rule specs, profiles, folders, project:
                                    toolkit/lib/idmc_frs_delete.py delete --ids-file state/delete_ids.txt (leaf-first, batches of
                                    25, reads back FRS_070 = gone; refuses Default / Add-On Bundles / inbound references)
                                    then toolkit/lib/idmc_frs_delete.py v2-delete for v2-only leftovers (mttask, workflow, schedule)
  8  connections                    toolkit/lib/idmc_frs_delete.py v2-delete connection <id> (after every task is gone)
  9  Snowflake                      teardown/99_snowflake_drop.sql (drops the BID_* objects; the monitor and warehouse last)
 10  Salesforce                     the two Accounts and their Files (Setup or Data Loader; this blueprint never deletes CRM data)
 11  SharePoint                     the <root_folder> folder in the library (by hand)
 12  Tableau                        the workbook (Tableau > Explore > <project> > workbook > Delete)
Gotchas: a task bound to a schedule cannot be deleted (REPO_52013): detach first; published CAI assets need unpublish (not
used here); a rejected or interrupted delete may already have removed objects: read back before you report.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import bid_common as C  # noqa: E402

CORE = C.CORE


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["plan", "export", "idmc"])
    ap.add_argument("--out", help="export: the package file, OUTSIDE the toolkit")
    a = ap.parse_args()
    C.H.safe_console()
    st = C.state()
    if a.cmd == "plan":
        print(__doc__.split("Order")[1])
        return
    ctx = C.Ctx(a)
    pid = st.get("project", "<projectId>")
    if a.cmd == "export":
        print("run:  python \"%s\" export --id %s --out %s" % (CORE / "idmc_export_import.py", pid, a.out or "<file outside the toolkit>"))
        return
    ids = []
    for k in ("tasks",):
        ids += list((st.get(k) or {}).values())
    for m in (st.get("claire") or {}).values():
        ids.append(m.get("v3"))
    ids += list((st.get("rulespecs") or {}).values())
    ids += list((st.get("folders") or {}).values()) + [pid]
    ids = [i for i in ids if i]
    out = C.STATE_DIR / "delete_ids.txt"
    if not ctx.offline:
        C.STATE_DIR.mkdir(exist_ok=True)
        out.write_text("\n".join(ids) + "\n", encoding="utf-8")
    print("%d FRS ids (tasks, models, rule specs, folders, project) -> %s" % (len(ids), out.relative_to(C.BP)))
    print("1. python idmc/bid_taskflows.py detach %s" % ("--execute --expect-org " + (a.expect_org or "<orgIdV3>")))
    print("2. python \"%s\" delete --ids-file \"%s\" %s" % (CORE / "idmc_frs_delete.py", out, "--execute --expect-org " + (a.expect_org or "<orgIdV3>")))
    print("   (taskflows and profiles: list their ids with idmc/bid_taskflows.py show / idmc/bid_dq.py profiles and add them first)")
    for k, cid in (st.get("conn") or {}).items():
        print("3. python \"%s\" v2-delete connection %s --execute --expect-org %s" % (CORE / "idmc_frs_delete.py", cid,
                                                                                                 a.expect_org or "<orgIdV3>"))
    print("This script never deletes by itself: run each printed command after you checked the export.")


if __name__ == "__main__":
    main()
