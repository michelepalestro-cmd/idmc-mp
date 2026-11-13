#!/usr/bin/env python3
"""idmc_frs_delete.py - headless deletes with a dependency check, KEEP guards, leaf-first rounds, per-item result
codes and a read-back. Dry-run by default; --execute needs --expect-org <orgIdV3> (the live org is proven first).

  python idmc_frs_delete.py deps <frsGuid> ... [--ids-file f]           (read-only: who uses it, what it uses)
  python idmc_frs_delete.py delete (<frsGuid> ... | --ids-file f) [--keep-file k] [--allow-inbound] [--log f.jsonl]
  python idmc_frs_delete.py v2-delete mttask|mapping|connection|agent|runtimeEnvironment|schedule|workflow <id>

Routes (host https://<pod>.<domain>.informaticacloud.com, header IDS-SESSION-ID with the v2 id; PROVEN 2026-09 in a
production org cleanup of 80+ objects):
  POST /frs/v1/GetInboundDocRefs  {"artifactIds":[..]} -> value[]{docId, docRefArray[]}      (who references each)
  POST /frs/v1/GetAllDependencies {"artifactIds":[..]} -> value[]{docId, docRefInfos[]}      (what each depends on)
  POST /frs/v1/DeleteEntities     {"artifactIds":[..]} -> value[]{guid, code, message}: FRS_200 deleted,
       FRS_082 still published or out of date (unpublish CAI first), FRS_087 project not empty
  GET  /frs/v1/BaseEntities('<id>') -> 200 still there, 404 / FRS_070 gone (the read-back)
  DELETE /api/v2/<resource>/<id> (icSessionId) -> 200; read-back 403/404 = gone; a deleted SCHEDULE's GET is an
       empty 200 shell, so it is checked in the list instead. A mapping deletes only when its tasks[] is empty.
Order that worked (whole-app removal, both orgs): back up first (idmc_export_import.py export, keep the zip outside
  the KB) -> CAI unpublish (processes -> app connections -> connectors) -> FRS delete CAI assets -> tasks (v2 id via
  frsGuid, never by name) -> mappings -> DQ assets / profiles (FRS) -> connections (after a used-by check) ->
  agents / runtime environments -> schedules -> empty folders and projects. Undo = re-import the backup with REUSE,
  then republish CAI. Never delete while another session imports; tell the migration lead before each batch.
KEEP by default (refused here): Add-On Bundles content (system content; FRS reports delete:false), the Default
  project, anything in --keep-file (ids or path prefixes), published CAI assets. Also keep the org's
  CAI_Anonymous_<orgIdV3> user if apps call anonymous CAI URLs (users are not deleted by this script).
A rejected or interrupted run may already have deleted objects server-side: re-run 'deps' or the read-back.
"""
from __future__ import annotations

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_objects import list_objects  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

SYSTEM_PREFIXES = ("Add-On Bundles",)
V2_RES = ("mttask", "mapping", "connection", "agent", "runtimeEnvironment", "schedule", "workflow")


def ref_ids(v, key):
    return [x if isinstance(x, str) else (x.get("id") or x.get("docId")) for x in v.get(key) or []]


def frs_batch(S, action, ids, key, size=50):
    out = {}
    for i in range(0, len(ids), size):
        r = S.call("frs", "POST", f"/frs/v1/{action}", body={"artifactIds": ids[i:i + size]})
        if not r.ok:
            raise RuntimeError(f"{action} HTTP {r.status} {r.head(200)}")
        for v in (r.json({}) or {}).get("value") or []:
            out.setdefault(v.get("docId"), []).extend(ref_ids(v, key))
    return out


def load_ids(a):
    ids = list(a.ids or [])
    if getattr(a, "ids_file", None):
        ids += [ln.strip() for ln in open(a.ids_file, encoding="utf-8") if ln.strip() and not ln.startswith("#")]
    return list(dict.fromkeys(ids))


def describe(objs, i):
    o = objs.get(i) or {}
    return f"{o.get('type', '?'):22} {o.get('path', '(not in the v3 object list)')}"


def guards(objs, ids, keep):
    bad = []
    for i in ids:
        o = objs.get(i) or {}
        path = o.get("path") or ""
        if path.split("/")[0] in SYSTEM_PREFIXES or (o.get("type") in ("Project", "PROJECT") and path == "Default"):
            bad.append((i, "system content"))
        elif i in keep or any(path == k or path.startswith(k.rstrip("/") + "/") for k in keep):
            bad.append((i, "in --keep-file"))
        elif ((o.get("customAttributes") or {}).get("publicationStatus")) == "published":
            bad.append((i, "published: unpublish first (FRS_082)"))
    return bad


def leaves(S, remaining, objs):
    inbound = frs_batch(S, "GetInboundDocRefs", remaining, "docRefArray")
    rem = set(remaining)
    free = [i for i in remaining if not any(x in rem for x in inbound.get(i, []))]
    content = [i for i in free if (objs.get(i) or {}).get("type") not in ("Folder", "Project", "FOLDER", "PROJECT")]
    return content or free


def cmd_delete(S, gate, a, objs):
    ids = load_ids(a)
    keep = [ln.strip() for ln in open(a.keep_file, encoding="utf-8") if ln.strip()] if a.keep_file else []
    if not ids:
        H.die("no ids given")
    bad = guards(objs, ids, keep)
    for i, why in bad:
        print(f"  REFUSED {i}  {describe(objs, i)}  ({why})")
    if bad:
        H.die(f"{len(bad)} protected object(s) in the delete list: remove them and re-run")
    inbound = frs_batch(S, "GetInboundDocRefs", ids, "docRefArray")
    outside = {i: [x for x in refs if x not in ids] for i, refs in inbound.items() if any(x not in ids for x in refs)}
    for i, refs in outside.items():
        print(f"  USED BY OUTSIDE {i} {describe(objs, i)} <- {[describe(objs, x) for x in refs[:4]]}")
    if outside and not a.allow_inbound:
        H.die(f"{len(outside)} object(s) are referenced from outside the delete set: move them to KEEP, add their "
              "users to the set, or pass --allow-inbound after checking")
    print(f"delete plan: {len(ids)} object(s) {dict(collections.Counter((objs.get(i) or {}).get('type') for i in ids))}")
    for i in ids:
        print(f"   {i}  {describe(objs, i)}")
    if not gate.execute:
        print("DRY-RUN: nothing deleted. Back up first, then --execute --expect-org <orgIdV3>.")
        return
    gate.guard()
    remaining, stuck = list(ids), {}
    for rnd in range(1, a.rounds + 1):
        leaf = leaves(S, remaining, objs)
        print(f"round {rnd}: {len(remaining)} left, {len(leaf)} deletable now")
        done = set()
        for k in range(0, len(leaf), 25):
            r = gate.send(f"DeleteEntities x{len(leaf[k:k + 25])}", "frs", "POST", "/frs/v1/DeleteEntities",
                          body={"artifactIds": leaf[k:k + 25]})
            for v in (r.json({}) or {}).get("value") or [] if r is not None and r.ok else []:
                if v.get("code") == "FRS_200":
                    done.add(v.get("guid"))
                else:
                    stuck[v.get("guid")] = f"{v.get('code')} {str(v.get('message'))[:160]}"
        for i in done:
            rb = S.get("frs", f"/frs/v1/BaseEntities('{i}')")
            H.jlog(gate.logfile, op="frs_delete", id=i, what=describe(objs, i), readback=rb.status)
            if rb.ok:
                stuck[i] = f"FRS_200 but still readable (HTTP {rb.status})"
        remaining = [i for i in remaining if i not in done]
        if not remaining or not done:
            break
    print(f"deleted {len(ids) - len(remaining)}/{len(ids)}; left {len(remaining)}")
    for i in remaining:
        print(f"   LEFT {i} {describe(objs, i)} {stuck.get(i, '')}")


def cmd_v2(S, gate, res, oid):
    cur = S.get("v2", f"/api/v2/{res}/{oid}")
    j = cur.json({}) or {}
    if not cur.ok:
        H.die(f"GET {res}/{oid} -> HTTP {cur.status} {cur.head(160)}")
    print(f"  {res} {oid} '{j.get('name')}'")
    if res == "mapping" and j.get("tasks"):
        H.die(f"mapping still has {len(j['tasks'])} task(s): delete those first")
    r = gate.send(f"delete {res} {oid}", "v2", "DELETE", f"/api/v2/{res}/{oid}")
    if r is None:
        return
    if res == "schedule":
        gone = oid not in {s.get("id") for s in S.get("v2", "/api/v2/schedule").json([]) or []}
    else:
        gone = S.get("v2", f"/api/v2/{res}/{oid}").status in (403, 404)
    print(f"  read-back: {'GONE' if gone else 'STILL PRESENT'} (delete HTTP {r.status}; REPO_52013 = still bound to a "
          "schedule, REPO_10242 = a mapping still uses the connection)")
    H.jlog(gate.logfile, op="v2_delete", res=res, id=oid, name=j.get("name"), status=r.status, gone=gone)


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="guarded headless deletes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    dp = sub.add_parser("deps")
    dp.add_argument("ids", nargs="*")
    dp.add_argument("--ids-file")
    dl = H.add_gate_args(sub.add_parser("delete"))
    dl.add_argument("ids", nargs="*")
    dl.add_argument("--ids-file")
    dl.add_argument("--keep-file")
    dl.add_argument("--allow-inbound", action="store_true")
    dl.add_argument("--rounds", type=int, default=15)
    v2 = H.add_gate_args(sub.add_parser("v2-delete"))
    v2.add_argument("resource", choices=V2_RES)
    v2.add_argument("id")
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "v2-delete":
            gate = H.WriteGate(a, S)
            gate.guard()
            return cmd_v2(S, gate, a.resource, a.id)
        objs = {o["id"]: o for o in list_objects(S)}
        if a.cmd == "deps":
            ids = load_ids(a)
            inbound = frs_batch(S, "GetInboundDocRefs", ids, "docRefArray")
            deps = frs_batch(S, "GetAllDependencies", ids, "docRefInfos")
            for i in ids:
                print(f"{i}  {describe(objs, i)}")
                for x in inbound.get(i, []):
                    print(f"   used by  {x}  {describe(objs, x)}")
                for x in deps.get(i, []):
                    print(f"   uses     {x}  {describe(objs, x)}")
            return
        gate = H.WriteGate(a, S)
        gate.guard()
        cmd_delete(S, gate, a, objs)
    except (LoginError, RuntimeError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
