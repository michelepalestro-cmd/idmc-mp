#!/usr/bin/env python3
"""idmc_runtime_selections.py - which services and connectors a runtime environment's Secure Agent runs:
show, change a few flags with a diff preview and a "never select all" guard, restore from a backup.

  python idmc_runtime_selections.py show <reId> [--section services|connectors|additionalServices] [--enabled-only] [--grep x]
  python idmc_runtime_selections.py set <reId> [--enable "Data Integration,connectors:PostgreSQL"] [--disable "..."]
         [--max-enable 5] [--backup-dir DIR]                         (dry-run; --execute --expect-org <orgIdV3>)
  python idmc_runtime_selections.py restore <reId> <backup.json>      (dry-run; --execute --expect-org <orgIdV3>)
Names match 'name' case-insensitively; prefix 'section:' when a name exists in two sections.

Route (PROVEN 2026-09, production; the first proven PUT recorded for IDMC):
  GET/PUT https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui
  header IDS-SESSION-ID: <v2 icSessionId> (INFA-SESSION-ID returns the login HTML). Body: {"services": {"selections":
  [{name, internalName, mandatory, enabled, visible, ...}]}, "connectors": {...}, "additionalServices": {...}}.
  GET, edit only the 'enabled' flags, PUT the whole document back, GET again to confirm. This is what the
  Administrator 'Enable or Disable Services' dialog calls.
Why the guards (measured on a shared 4-vCPU agent host): selecting every service pulled ~18 GB of packages in
  ~8 minutes, drove the load average to ~189 and exhausted swap. Every PUT, even a deselect, also rolls Data
  Integration Server, Mass Ingestion and Connector Service to their newest builds, and jobs queue ~5 min behind
  it: batch changes, never during a timed run or demo. Metadata/catalog scanner services are heavy: switch them on
  only for a scan window (deselecting them freed ~3.7 GB RAM). A backup of the GET body is written before any PUT
  (the undo). After a change, poll /api/v2/agent/details/<agentId> until the engines report RUNNING.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

SECTIONS = ("services", "connectors", "additionalServices")


def path(re_id):
    return f"/runtime/api/v2/runtimeEnvironment/{re_id}/selections/ui"


def fetch(S, re_id):
    r = S.get("runtime", path(re_id))
    if not r.ok or r.is_html:
        H.die(f"GET selections -> HTTP {r.status} {r.verdict()} {r.head(160)}")
    return r.json({}) or {}


def items(doc):
    for sec in SECTIONS:
        for x in (doc.get(sec) or {}).get("selections") or []:
            yield sec, x


def enabled_map(doc):
    return {(sec, x.get("name")): bool(x.get("enabled")) for sec, x in items(doc)}


def find(doc, spec):
    sec, _, name = spec.rpartition(":") if ":" in spec else ("", "", spec)
    hits = [(s, x) for s, x in items(doc) if x.get("name", "").lower() == name.strip().lower() and (not sec or s == sec)]
    if len(hits) != 1:
        H.die(f"'{spec}' matches {len(hits)} selection(s); use the exact name (see 'show'), or 'section:name'")
    return hits[0]


def check_and_diff(before, after, max_enable):
    b, a = enabled_map(before), enabled_map(after)
    changes = [(k, b.get(k), a.get(k)) for k in a if b.get(k) != a.get(k)]
    for (sec, name), old, new in changes:
        print(f"  {sec:18} {name:45} {'on ' if old else 'off'} -> {'ON' if new else 'OFF'}")
    turned_on = [k for k, old, new in changes if new and not old]
    if len(turned_on) > max_enable:
        H.die(f"{len(turned_on)} selections would be switched ON (> --max-enable {max_enable}): enable only what the "
              "workload needs (selecting everything pulled ~18 GB and overloaded a shared host)")
    for sec in ("services", "connectors"):
        sel = (after.get(sec) or {}).get("selections") or []
        if sel and all(x.get("enabled") for x in sel) and not all(x.get("enabled") for x in (before.get(sec) or {}).get("selections") or []):
            H.die(f"this change would enable EVERY item in '{sec}': refused (never select all)")
    for sec, x in items(after):
        if x.get("mandatory") and not x.get("enabled"):
            H.die(f"'{x.get('name')}' is mandatory and cannot be disabled")
    return changes


def put_and_confirm(S, gate, re_id, before, after, changes, backup_dir):
    if not changes:
        print("  nothing to change")
        return
    bk = os.path.join(backup_dir, f"selections_{re_id}_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    print("  backup of the current selections (the undo):", H.save_json(bk, before))
    print(f"  {len(changes)} change(s); the PUT also rolls DIS / Mass Ingestion / Connector Service to the newest build")
    r = gate.send("PUT selections", "runtime", "PUT", path(re_id), body=after, timeout=180)
    if r is None:
        return
    if not r.ok:
        H.die(f"PUT failed HTTP {r.status} {r.head(300)}")
    time.sleep(5)
    now = enabled_map(fetch(S, re_id))
    missed = [(k, new) for k, old, new in changes if now.get(k) != new]
    print(f"  read-back: {len(changes) - len(missed)}/{len(changes)} applied" + (f"; NOT applied: {missed}" if missed else ""))
    H.jlog(gate.logfile, op="selections", re=re_id, changes=[(f"{s}:{n}", v) for (s, n), _, v in changes], missed=missed)


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="runtime environment service/connector selections")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sh = sub.add_parser("show")
    sh.add_argument("re")
    sh.add_argument("--section", choices=SECTIONS)
    sh.add_argument("--enabled-only", action="store_true")
    sh.add_argument("--grep")
    st = H.add_gate_args(sub.add_parser("set"))
    st.add_argument("re")
    st.add_argument("--enable", default="")
    st.add_argument("--disable", default="")
    st.add_argument("--max-enable", type=int, default=5)
    st.add_argument("--backup-dir", default=".")
    rs = H.add_gate_args(sub.add_parser("restore"))
    rs.add_argument("re")
    rs.add_argument("backup")
    rs.add_argument("--max-enable", type=int, default=25)
    rs.add_argument("--backup-dir", default=".")
    a = ap.parse_args()
    try:
        S = Session()
        doc = fetch(S, a.re)
        if a.cmd == "show":
            n = 0
            for sec, x in items(doc):
                if (a.section and sec != a.section) or (a.enabled_only and not x.get("enabled")):
                    continue
                if a.grep and a.grep.lower() not in x.get("name", "").lower():
                    continue
                n += 1
                print(f"  {sec:18} {'ON ' if x.get('enabled') else 'off'} {'M' if x.get('mandatory') else ' '} {x.get('name')}")
            tot = {sec: sum(1 for s, x in items(doc) if s == sec and x.get("enabled")) for sec in SECTIONS}
            print(f"{n} row(s) shown; enabled per section: {tot}")
            return
        gate = H.WriteGate(a, S)
        gate.guard()
        if a.cmd == "set":
            after = copy.deepcopy(doc)
            for spec in filter(None, (s.strip() for s in a.enable.split(","))):
                find(after, spec)[1]["enabled"] = True
            for spec in filter(None, (s.strip() for s in a.disable.split(","))):
                find(after, spec)[1]["enabled"] = False
        else:
            after = json.load(open(a.backup, encoding="utf-8"))
            if set(enabled_map(after)) != set(enabled_map(doc)):
                print("  note: the backup's selection list differs from the live one (new or removed items)")
        changes = check_and_diff(doc, after, a.max_enable)
        put_and_confirm(S, gate, a.re, doc, after, changes, a.backup_dir)
    except (LoginError, RuntimeError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
