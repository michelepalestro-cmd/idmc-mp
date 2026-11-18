#!/usr/bin/env python3
"""listener_ctl.py - stop / start ONE CAI listener (event source) on the Secure Agent, the others keep running.

  python idmc/listener_ctl.py stop  mbr-kafka:item-sub [mbr-kafka-store:store-price-sub ...]  --execute --expect-org <id>
  python idmc/listener_ctl.py start mbr-kafka:item-sub                                        --execute --expect-org <id>

Route: POST https://<pod>-cai.<domain>/active-bpel/local/restadmin/eventconnection/{stop|start}?agentName=<agent>
  stop  body {"eventRoute": ["project:/rt.connection/<conn>/$public/<conn>:<eventSource>", ...]}
  start body {"routeInfo": [{"eventRoute": "project:/rt.connection/<conn>/$public/<conn>:<eventSource>"}, ...]}
Header IDS-SESSION-ID (with INFA-SESSION-ID every body shape answered HTTP 500 NullPointerException, L-CAI-122).
The answer lists eventRouteStatus IN_ACTIVE / ACTIVE per route (about 1-7 s). A stopped Kafka event source leaves its
consumer group EMPTY while lag grows; start resumes from the last offset auto-commit (L-CAI-121), so a few records can
be processed twice: the targets are idempotent. Other event sources of the same connection keep running (L-CAI-147).
PROVEN in an earlier form (2026-10: per-consumer stop/start drills, nothing lost).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import mbr_config as CFG  # noqa: E402

CFG.use_core()
import idmc_http as H  # noqa: E402
from idmc_session import Session  # noqa: E402


def body_for(op, routes):
    paths = ["project:/rt.connection/%s/$public/%s" % (r.split(":")[0], r) for r in routes]
    return {"eventRoute": paths} if op == "stop" else {"routeInfo": [{"eventRoute": p} for p in paths]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("op", choices=["stop", "start"])
    ap.add_argument("routes", nargs="+", help="<connection>:<eventSource>, e.g. mbr-kafka:item-sub")
    ap.add_argument("--config")
    H.add_gate_args(ap)
    a = ap.parse_args()
    for r in a.routes:
        if ":" not in r:
            H.die(f"route '{r}' must be <connection>:<eventSource>")
    cfg = CFG.load(a.config)
    agent = cfg["agent"]["name"]
    body = body_for(a.op, a.routes)
    path = f"/active-bpel/local/restadmin/eventconnection/{a.op}?agentName={agent}"
    print(f"[{'EXECUTE' if a.execute and not a.dry_run else 'DRY-RUN'}] {a.op} on agent {agent}: POST cai:{path}")
    print("    body:", json.dumps(body))
    if not a.execute or a.dry_run:
        return
    S = Session()
    gate = H.WriteGate(a, S)
    gate.guard()
    url = S.hosts()["cai"] + path
    t0 = time.time()
    r = S.call("frs", "POST", url, body=body, headers={"Accept": "application/json"}, timeout=120)  # frs plane = IDS-SESSION-ID only
    print(f"    -> HTTP {r.status} in {time.time() - t0:.1f} s")
    print(json.dumps(H.redact(r.json({}) or {}), indent=1)[:3000])
    H.jlog(a.log, label=f"listener {a.op}", routes=a.routes, status=r.status)


if __name__ == "__main__":
    main()
