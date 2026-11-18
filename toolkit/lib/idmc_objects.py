#!/usr/bin/env python3
"""idmc_objects.py - READ-ONLY inventory: v3 object search/list, type census, references, path lookup,
v2 detail GETs and v2 <-> v3 (frsGuid) id resolution. Importable helpers for the other scripts.

  python idmc_objects.py list [--type MTT] [--location <project>] [--tag <tag>] [--q "<raw q>"]
                              [--path-prefix <project>/<folder>] [--name-contains x] [--json out.json]
  python idmc_objects.py census                      # object count per type (whole org, paged)
  python idmc_objects.py refs <frsGuid> [--dir uses|usedBy|both]
  python idmc_objects.py lookup <project>/<folder>/<name> <TYPE>
  python idmc_objects.py v2 <resource> [<id>]        # mttask | workflow | mapping | connection | schedule |
                                                     # runtimeEnvironment | agent | agent/details | task?type=MTT
  python idmc_objects.py resolve <id>                # v2 task/workflow id -> v3 id, or v3 id -> v2 MTT id

Routes (plane v3 = <serverUrl>/public/core/v3 with INFA-SESSION-ID; v2 = <serverUrl>/api/v2 with icSessionId):
  GET  /public/core/v3/objects?limit=200&skip=N&q=...   PROVEN 2026-09 (paged; 'count' + 'objects[]')
  GET  /public/core/v3/objects/<id>/references?refType=uses|usedBy&limit=50&skip=N   PROVEN 2026-09
  POST /public/core/v3/lookup {"objects":[{"path","type"}]}   PROVEN 2026-09 (read-only despite POST)
  GET  /api/v2/<resource>[/<id>]                          PROVEN 2026-09
  GET  /api/v2/mttask/<v3 id> resolving to the v2 task    ADAPTED from a 2026-09 note; falls back to a scan
Gotchas encoded here:
  * The q filter is NOT validated: a wrong type name returns 0 objects, not an error (type=='DBMI' -> 0 while
    the real type is DBMI_TASK). census shows the real type names. Filter client-side when in doubt.
  * The v2 MTT list omits frsGuid and scheduleId: read each detail GET. v2 workflows carry no frsGuid at all:
    resolve by name among v3 WORKFLOW objects and require exactly one match.
  * The same task name can exist in unrelated folders: address tasks by id, never by name.
  * A one-off 500 'Objects Listing Failed' was seen while another session imported: retried once here.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402


def list_objects(S, q=None, limit=200, max_items=None):
    """Every v3 object matching q (server-side, unvalidated). Pages until 'count'."""
    out, skip = [], 0
    while True:
        qs = {"limit": limit, "skip": skip}
        if q:
            qs["q"] = q
        path = "/public/core/v3/objects?" + urllib.parse.urlencode(qs)
        r = S.get("v3", path)
        if r.status == 500:                       # transient listing failure during a peer's write: one retry
            time.sleep(5)
            r = S.get("v3", path)
        if not r.ok:
            raise RuntimeError(f"objects list HTTP {r.status} {r.head(200)}")
        j = r.json({}) or {}
        batch = j.get("objects") or []
        out += batch
        skip += limit
        if len(batch) < limit or skip >= (j.get("count") or 0) or (max_items and len(out) >= max_items):
            return out[:max_items] if max_items else out


def build_q(obj_type=None, location=None, tag=None, raw=None):
    parts = [p for p in (f"type=='{obj_type}'" if obj_type else None, f"location=='{location}'" if location else None,
                         f"tag=='{tag}'" if tag else None, raw) if p]
    return " and ".join(parts) or None


def references(S, oid, direction="uses"):
    out, skip = [], 0
    while True:
        r = S.get("v3", f"/public/core/v3/objects/{oid}/references?refType={direction}&limit=50&skip={skip}")
        if not r.ok:
            raise RuntimeError(f"references HTTP {r.status} {r.head(200)}")
        batch = (r.json({}) or {}).get("references") or []
        out += batch
        skip += 50
        if len(batch) < 50:
            return out


def lookup_path(S, path, obj_type):
    r = S.call("v3", "POST", "/public/core/v3/lookup", body={"objects": [{"path": path, "type": obj_type}]})
    objs = (r.json({}) or {}).get("objects") if r.ok else None
    return r, objs or []


def v2_to_v3(S, v2id):
    """v2 MTT -> frsGuid (detail GET). v2 workflow -> unique name match among v3 WORKFLOW objects."""
    r = S.get("v2", f"/api/v2/mttask/{v2id}")
    if r.ok and (r.json({}) or {}).get("frsGuid"):
        return r.json()["frsGuid"], "mttask.frsGuid"
    r = S.get("v2", f"/api/v2/workflow/{v2id}")
    name = (r.json({}) or {}).get("name") if r.ok else None
    if not name:
        return None, f"not an MTT or workflow in this org (HTTP {r.status})"
    hits = [o for o in list_objects(S, "type=='WORKFLOW'") if o.get("path", "").split("/")[-1] == name]
    if len(hits) == 1:
        return hits[0]["id"], "WORKFLOW name match"
    return None, f"workflow '{name}': {len(hits)} v3 matches (need exactly 1)"


def v3_to_v2_mtt(S, v3id, scan_limit=400):
    r = S.get("v2", f"/api/v2/mttask/{v3id}")
    j = r.json({}) if r.ok else None
    if isinstance(j, dict) and j.get("id") and j.get("frsGuid") in (v3id, None):
        return j["id"], "GET /api/v2/mttask/<v3id>"
    r = S.get("v2", "/api/v2/mttask")
    for t in (r.json([]) or [])[:scan_limit] if r.ok else []:
        d = S.get("v2", f"/api/v2/mttask/{t['id']}").json({}) or {}
        if d.get("frsGuid") == v3id:
            return t["id"], "detail scan"
    return None, "no v2 MTT carries this frsGuid (checked up to %d)" % scan_limit


def show(objs, limit=500):
    for o in objs[:limit]:
        pub = (o.get("customAttributes") or {}).get("publicationStatus") or ""
        print(f"  {o.get('id')}  {o.get('type', ''):22} {o.get('path', '')}  {(o.get('updateTime') or '')[:19]} {pub}")
    if len(objs) > limit:
        print(f"  ... {len(objs) - limit} more (use --json)")


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    for f in ("--type", "--location", "--tag", "--q", "--path-prefix", "--name-contains", "--json"):
        ls.add_argument(f)
    ls.add_argument("--max", type=int)
    sub.add_parser("census")
    rf = sub.add_parser("refs")
    rf.add_argument("id")
    rf.add_argument("--dir", default="both", choices=["uses", "usedBy", "both"])
    lk = sub.add_parser("lookup")
    lk.add_argument("path")
    lk.add_argument("type")
    v2 = sub.add_parser("v2")
    v2.add_argument("resource")
    v2.add_argument("id", nargs="?")
    v2.add_argument("--json")
    rs = sub.add_parser("resolve")
    rs.add_argument("id")
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "list":
            objs = list_objects(S, build_q(a.type, a.location, a.tag, a.q), max_items=a.max)
            if a.path_prefix:
                objs = [o for o in objs if (o.get("path") or "").startswith(a.path_prefix)]
            if a.name_contains:
                objs = [o for o in objs if a.name_contains.lower() in (o.get("path") or "").split("/")[-1].lower()]
            print(f"{len(objs)} object(s)")
            show(objs)
            if not objs and a.type:
                print("  0 hits: the q filter is not validated; run 'census' to see the real type names")
            if a.json:
                H.save_json(a.json, objs, private=False)
                print("saved", a.json)
        elif a.cmd == "census":
            c = collections.Counter(o.get("type") for o in list_objects(S))
            for t, n in c.most_common():
                print(f"  {n:>6}  {t}")
        elif a.cmd == "refs":
            for d in (["uses", "usedBy"] if a.dir == "both" else [a.dir]):
                refs = references(S, a.id, d)
                print(f"[{d}] {len(refs)}")
                for x in refs:
                    print(f"   {x.get('id')}  {x.get('documentType') or x.get('type', ''):22} {x.get('path')}")
        elif a.cmd == "lookup":
            r, objs = lookup_path(S, a.path, a.type)
            print(f"HTTP {r.status} | {len(objs)} object(s)")
            show(objs) if objs else print(" ", r.head(400))
        elif a.cmd == "v2":
            r = S.get("v2", f"/api/v2/{a.resource}" + (f"/{a.id}" if a.id else ""))
            print(f"HTTP {r.status} | {r.verdict()}")
            body = r.json()
            if a.json and body is not None:
                H.save_json(a.json, body, private=True)      # detail bodies can carry connection attributes
                print("saved", a.json)
            print(H.preview(body if body is not None else r.text, 6000))
        else:
            if len(a.id) == 22:
                v2id, how = v3_to_v2_mtt(S, a.id)
                print(f"v3 {a.id} -> v2 {v2id}  ({how})")
            else:
                v3id, how = v2_to_v3(S, a.id)
                print(f"v2 {a.id} -> v3 {v3id}  ({how})")
    except (LoginError, RuntimeError) as e:
        H.die(str(e), 3)


if __name__ == "__main__":
    main()
