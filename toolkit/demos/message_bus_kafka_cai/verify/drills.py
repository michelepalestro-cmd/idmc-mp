#!/usr/bin/env python3
"""drills.py - the failure drills: each one breaks something on purpose and checks that nothing is lost or applied twice.

  python verify/drills.py poison        a malformed message -> hospital MALFORMED_XML (not retried) + DLQ copy -> discarded
  python verify/drills.py validation    an item with a bad UPC check digit -> hospital VALIDATION_FAILED, nothing delivered
  python verify/drills.py outage        merchandising down -> retries with backoff -> hospital MERCH_UNAVAILABLE
                                        -> merchandising back -> replay -> delivered, entry resolved
  python verify/drills.py missing-items a PO before its items -> hospital ITEMS_MISSING -> items arrive -> replay -> delivered
  python verify/drills.py compensation  the warehouse refuses a PO -> the merchandising PO is cancelled -> hospital REJECTED
  python verify/drills.py large-po      a 19,500-line PO over Kafka and over JMS (the bridge) -> delivered, lines counted
  python verify/drills.py restart --expect-org <orgIdV3>
                                        stop the item listener, send 50 items, start it: all 50 delivered, the store-price
                                        listener kept running meanwhile (uses idmc/listener_ctl.py: an IDMC write)
  python verify/drills.py all [--expect-org <orgIdV3>]   every drill above (restart only with --expect-org)

Replays go through the CAI process mbr_error_queue_replay on the agent (run this on the agent host), or wait for the
mbr-timer sweep with --wait-sweep. Every drill prints PASS / FAIL and the ledger timeline.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mbr_msgs as M  # noqa: E402
import send as SND  # noqa: E402

CFG = M.CFG
BP = Path(__file__).resolve().parents[1]


def entry(cfg, mid, code=None, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = [e for e in M.error_queue(cfg, mid) if code is None or e["reason_code"] == code]
        if rows:
            return rows[-1]
        time.sleep(2)
    return None


def replay(cfg, eid, wait_sweep):
    if wait_sweep:
        print(f"  waiting for the hospital sweep (mbr-timer) to replay entry {eid}")
        return True
    st, txt = M.agent_post(cfg, "mbr_error_queue_replay", {"id": str(eid), "actor": "drill"})
    print(f"  replay entry {eid} via the agent: HTTP {st} {txt[:160]}")
    return st == 200


def verdict(name, ok, detail=""):
    print(f"DRILL {name}: {'PASS' if ok else 'FAIL'} {detail}")
    return ok


def d_poison(cfg, a):
    mid = M.new_id("poison")
    body = "<Messages><message><family>Items</family><type>ItemCre</type><id>ItemDesc:999999</id>" \
           f"<messageID>{mid}</messageID><messageData>&lt;ItemDesc&gt;&lt;item&gt;999999&lt;/item&gt;BROKEN</messageData>"
    M.kafka_send(cfg, cfg["kafka"]["topics"]["item"]["name"], [("999999", M.headers_for(mid, "999999", "Items", "ItemCre"), body)])
    e = entry(cfg, mid, "MALFORMED_XML")
    ok = bool(e) and e["retryable"] is False
    if e:
        st, _ = M.api(cfg, "/rpc/eq_mark", {"id": str(e["id"]), "status": "discarded", "actor": "drill"})
        ok = ok and st == 200
    M.show(M.events(cfg, mid))
    return verdict("poison", ok, f"entry {e and e['id']} discarded; a copy is on topic {cfg['kafka']['topics']['dlq']['name']}")


def d_validation(cfg, a):
    mid = SND.send_item(cfg, "kafka", f"8{int(time.time()) % 100000}", bad_upc=True)
    e = entry(cfg, mid, "VALIDATION_FAILED")
    M.show(M.events(cfg, mid))
    return verdict("validation", bool(e) and not e["retryable"], "the bad item reached no target")


def d_outage(cfg, a):
    M.api(cfg, "/rpc/set_fault", {"target": "merch", "mode": "down", "seconds": 90})
    mid = SND.send_item(cfg, "kafka", f"6{int(time.time()) % 100000}")
    e = entry(cfg, mid, "MERCH_UNAVAILABLE", timeout=150)
    retries = sum(1 for x in M.events(cfg, mid) if x["stage"] == "retry")
    M.api(cfg, "/rpc/clear_faults", {})
    ok = bool(e) and e["retryable"] is True and retries >= 1
    if ok:
        ok = replay(cfg, e["id"], a.wait_sweep)
        ok = ok and SND.follow(cfg, mid, 180 if a.wait_sweep else 90, stages=("delivered",), need=2)[0]
        final = (M.error_queue(cfg, mid) or [{}])[-1]
        ok = ok and final.get("status") == "resolved"
    M.show(M.events(cfg, mid))
    return verdict("outage", ok, f"{retries} retries before the hospital; then replayed and resolved")


def d_missing(cfg, a):
    s = int(time.time()) % 100000
    items = [f"7{s}1", f"7{s}2"]
    mid = SND.send_po(cfg, "kafka", f"PO7{s}", items, 4)
    e = entry(cfg, mid, "ITEMS_MISSING")
    for it in items:
        SND.send_item(cfg, "kafka", it)
    time.sleep(8)
    ok = bool(e) and replay(cfg, e["id"], a.wait_sweep) and SND.follow(cfg, mid, 120, stages=("delivered",))[0]
    return verdict("missing-items", ok, "the PO waited in the hospital until its items existed")


def d_compensation(cfg, a):
    s = int(time.time()) % 100000
    it = f"5{s}"
    SND.send_item(cfg, "kafka", it)
    time.sleep(6)
    M.api(cfg, "/rpc/set_fault", {"target": "warehouse", "mode": "reject", "seconds": 60})
    mid = SND.send_po(cfg, "kafka", f"PO5{s}", [it], 2)
    ok, ev = M.wait_stage(cfg, mid, ("compensated",), 90)
    M.api(cfg, "/rpc/clear_faults", {})
    st, rows = M.api(cfg, f"/po_status?po=eq.PO5{s}")
    cancelled = st == 200 and rows and rows[0].get("status") == "cancelled"
    M.show(ev)
    return verdict("compensation", ok and cancelled, "merchandising PO cancelled after the warehouse refusal")


def d_large(cfg, a):
    n = int(cfg["verify"]["large_po_lines"])
    s = int(time.time()) % 100000
    it = [f"9{s}{i}" for i in range(5)]
    for x in it:
        SND.send_item(cfg, "kafka", x)
    time.sleep(8)
    oks = []
    for via in ("kafka", "jms"):
        t0 = time.time()
        mid = SND.send_po(cfg, via, f"PO9{s}{via[0]}", it, n)
        ok = SND.follow(cfg, mid, 300, stages=("delivered",))[0]
        st, rows = M.api(cfg, f"/po_status?po=eq.PO9{s}{via[0]}")
        lines = rows[0].get("merch_lines") if st == 200 and rows else None
        oks.append(ok and lines == n)
        print(f"  {via}: {n:,} lines -> merchandising {lines} lines, warehouse {rows and rows[0].get('wh_lines')}, "
              f"{time.time() - t0:.1f} s end to end")
    return verdict("large-po", all(oks), f"{n:,}-line PO over Kafka and JMS")


def d_restart(cfg, a):
    if not a.expect_org:
        return verdict("restart", False, "needs --expect-org (it stops and starts a listener in the org)")
    ctl = [sys.executable, str(BP / "idmc" / "listener_ctl.py")]
    gate = ["--execute", "--expect-org", a.expect_org]
    subprocess.run(ctl + ["stop", "mbr-kafka:item-sub"] + gate, check=False)
    s = int(time.time()) % 100000
    mids, recs = [], []
    for i in range(50):
        item = f"3{s}{i:02d}"
        mid = M.new_id("rst")
        mids.append(mid)
        recs.append((item, M.headers_for(mid, item, "Items", "ItemCre"),
                     M.envelope("Items", "ItemCre", item, mid, M.item_xml(item), "ItemDesc")))
    M.kafka_send(cfg, cfg["kafka"]["topics"]["item"]["name"], recs)
    time.sleep(10)
    lag = M.group_lag(cfg, cfg["kafka"]["groups"]["item"])
    store = M.group_lag(cfg, cfg["kafka"]["groups"]["store_price"])
    print(f"  while stopped: item group lag {lag['lag']} members {lag['members']}; store-price group lag {store['lag']}")
    subprocess.run(ctl + ["start", "mbr-kafka:item-sub"] + gate, check=False)
    t0, done = time.time(), set()
    while time.time() - t0 < 180 and len(done) < len(mids):
        for m in mids:
            if m not in done and any(e["stage"] == "delivered" and e["target"] == "all" for e in M.events(cfg, m)):
                done.add(m)
        time.sleep(3)
    twice = sum(1 for m in mids if sum(1 for e in M.events(cfg, m) if e["stage"] == "consumed" and
                                      e["process"] == "mbr_item_subscriber") > 1)
    return verdict("restart", len(done) == len(mids) and lag["lag"] > 0,
                   f"{len(done)}/{len(mids)} delivered after the start in {time.time() - t0:.1f} s; {twice} re-read after the "
                   "restart (idempotent targets answered duplicate)")


DRILLS = {"poison": d_poison, "validation": d_validation, "outage": d_outage, "missing-items": d_missing,
          "compensation": d_compensation, "large-po": d_large, "restart": d_restart}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("drill", choices=list(DRILLS) + ["all"])
    ap.add_argument("--expect-org", help="v3 org id (only the restart drill writes to IDMC)")
    ap.add_argument("--wait-sweep", action="store_true", help="let the mbr-timer sweep replay instead of calling the agent")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = CFG.load(a.config)
    names = list(DRILLS) if a.drill == "all" else [a.drill]
    if a.drill == "all" and not a.expect_org:
        names.remove("restart")
    res = {n: DRILLS[n](cfg, a) for n in names}
    print("SUMMARY:", ", ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in res.items()))
    sys.exit(0 if all(res.values()) else 1)


if __name__ == "__main__":
    main()
