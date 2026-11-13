#!/usr/bin/env python3
"""send.py - send one item or one purchase order through the new bus (Kafka) or the legacy bus (JMS) and follow it.

  python verify/send.py item [--via kafka|jms] [--item 100001] [--bad-upc] [--dept 999]
  python verify/send.py po   [--via kafka|jms] [--po PO100001] [--lines 3] [--version 1] [--location 1001]
                             [--items 100001,100002] [--break-totals] [--no-items]
  python verify/send.py smoke                 item + PO over Kafka, then the same over JMS (the bridge), expect delivered
  add --dry to print what would be sent; --no-wait to skip the read-back.

The PO's items must exist in the merchandising stand-in first: `po` sends its items (over the same bus) unless
--no-items is given; with --no-items the PO waits in the hospital as ITEMS_MISSING until the items arrive.
Large PO: `send.py po --lines 19500` (about 4 MB: the topic and the CAI producer allow 5 MB).
Expected read-back per message: consumed -> validated -> delivered (Kafka) or bridged -> consumed -> ... (JMS).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mbr_msgs as M  # noqa: E402

CFG = M.CFG


def send_item(cfg, via, item, dry=False, bad_upc=False, dept="110"):
    mid = M.new_id("item")
    body = M.envelope("Items", "ItemCre", item, mid, M.item_xml(item, dept=dept, good_upc=not bad_upc), "ItemDesc")
    h = M.headers_for(mid, item, "Items", "ItemCre", source=f"verify-{via}")
    if via == "kafka":
        M.kafka_send(cfg, cfg["kafka"]["topics"]["item"]["name"], [(item, h, body)], dry)
    else:
        M.jms_send(cfg, cfg["artemis"]["queues"]["items"], h, body, dry)
    print(f"sent item {item} msg {mid} via {via} ({len(body):,} bytes)")
    return mid


def send_po(cfg, via, po, items, lines, version=1, location="1001", dry=False, break_totals=False):
    mid = M.new_id("po")
    body = M.envelope("Order", "POCre", po, mid, M.po_xml(po, items, lines, version, location, break_totals), "PODesc")
    h = M.headers_for(mid, po, "Order", "POCre", source=f"verify-{via}")
    if via == "kafka":
        M.kafka_send(cfg, cfg["kafka"]["topics"]["po"]["name"], [(po, h, body)], dry)
    else:
        M.jms_send(cfg, cfg["artemis"]["queues"]["pos"], h, body, dry)
    print(f"sent PO {po} v{version} with {lines:,} lines msg {mid} via {via} ({len(body):,} bytes)")
    return mid


def follow(cfg, mid, timeout, stages=("delivered", "error_queue", "skipped_stale"), need=1):
    t0 = time.time()
    ok, ev = M.wait_stage(cfg, mid, stages, timeout, need)
    print(f"  {'OK ' if ok else 'TIMEOUT'} after {time.time() - t0:.1f} s, {len(ev)} ledger events:")
    M.show(ev)
    for e in M.error_queue(cfg, mid):
        print(f"  hospital entry {e['id']}: {e['reason_code']} retryable={e['retryable']} status={e['status']} {str(e.get('reason_text'))[:120]}")
    return ok, ev


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("what", choices=["item", "po", "smoke"])
    ap.add_argument("--via", choices=["kafka", "jms"], default="kafka")
    ap.add_argument("--item")
    ap.add_argument("--bad-upc", action="store_true")
    ap.add_argument("--dept", default="110")
    ap.add_argument("--po")
    ap.add_argument("--lines", type=int, default=3)
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--location", default="1001")
    ap.add_argument("--items")
    ap.add_argument("--break-totals", action="store_true")
    ap.add_argument("--no-items", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = CFG.load(a.config, example_ok=a.dry)
    to = int(cfg["verify"]["wait_timeout_s"])
    stamp = str(int(time.time()) % 1000000)
    if a.what == "item":
        mid = send_item(cfg, a.via, a.item or f"1{stamp}", a.dry, a.bad_upc, a.dept)
        if not (a.dry or a.no_wait):
            follow(cfg, mid, to)
    elif a.what == "po":
        items = (a.items or f"2{stamp},3{stamp}").split(",")
        if not a.no_items:
            for it in items:
                send_item(cfg, a.via, it, a.dry)
            if not a.dry:
                time.sleep(5)
        mid = send_po(cfg, a.via, a.po or f"PO{stamp}", items, a.lines, a.version, a.location, a.dry, a.break_totals)
        if not (a.dry or a.no_wait):
            follow(cfg, mid, max(to, 60 + a.lines // 200))
    else:
        results = []
        for via in ("kafka", "jms"):
            it = f"4{stamp}{0 if via == 'kafka' else 1}"
            mid = send_item(cfg, via, it, a.dry)
            ok = a.dry or follow(cfg, mid, to, need=2)[0]   # item: delivered by the item AND the store-price subscriber
            results.append((f"item via {via}", ok))
            pmid = send_po(cfg, via, f"PO{stamp}{via[0]}", [it], 3, dry=a.dry)
            ok = a.dry or follow(cfg, pmid, to)[0]
            results.append((f"PO via {via}", ok))
        print("SMOKE:", ", ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in results))
        sys.exit(0 if all(ok for _, ok in results) else 1)


if __name__ == "__main__":
    main()
