#!/usr/bin/env python3
"""load_test.py - steady load or a burst on the load-test topic, then measure what the CAI listener drained.

  python verify/load_test.py [--rate 40] [--seconds 30]        paced: rate msg/s for N seconds
  python verify/load_test.py --burst 3000                      as fast as the producer goes, then watch the lag drain

The pings go to the load-test topic (6 partitions); the listener mbr_perf_subscriber (consumersCount=6) makes ONE CAI run
and one ledger write per ping, so this measures the listener itself. Results: sent, delivered, end-to-end p50 / p95
(ledger time minus the sent-at header), and the drain rate. Measured in the source build on one Secure Agent (8 vCPU):
about 30 msg/s with 3 consumers, about 47 msg/s with 6, 40 msg/s steady kept up (p95 331 ms) (KB L-CAI-126).
A load test makes thousands of CAI runs: ask the org owner before you run it.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mbr_msgs as M  # noqa: E402

CFG = M.CFG


def ping(run, seq):
    mid = f"perf-{run}-{seq}"
    inner = f"<Ping><run>{run}</run><seq>{seq}</seq></Ping>"
    body = M.envelope("Perf", "Ping", str(seq), mid, inner, "Ping")
    return str(seq), {"mbr-msg-id": mid, "mbr-rev": "1", "mbr-key": str(seq), "mbr-sent-at": M.now_iso()}, body


def ts(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--rate", type=float)
    ap.add_argument("--seconds", type=int)
    ap.add_argument("--burst", type=int)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = CFG.load(a.config)
    run = uuid.uuid4().hex[:8]
    topic = cfg["kafka"]["topics"]["perf"]["name"]
    sent_at = {}
    t0 = time.time()
    if a.burst:
        recs = [ping(run, i) for i in range(a.burst)]
        for k, h, _ in recs:
            sent_at[h["mbr-msg-id"]] = h["mbr-sent-at"]
        M.kafka_send(cfg, topic, recs)
    else:
        rate = a.rate or float(cfg["verify"]["load_rate_per_s"])
        secs = a.seconds or int(cfg["verify"]["load_seconds"])
        p = M.kafka_stream(cfg, topic)
        n = int(rate * secs)
        for i in range(n):
            k, h, v = ping(run, i)
            sent_at[h["mbr-msg-id"]] = h["mbr-sent-at"]
            p.stdin.write((M.kafka_line(k, h, v) + "\n").encode())
            p.stdin.flush()
            delay = t0 + (i + 1) / rate - time.time()
            if delay > 0:
                time.sleep(delay)
        p.stdin.close()
        p.wait()
    sent = len(sent_at)
    print(f"run {run}: sent {sent} pings to {topic} in {time.time() - t0:.1f} s")
    like = urllib.parse.quote(f"perf-{run}-*")
    t1, got = time.time(), []
    while time.time() - t1 < a.timeout:
        st, rows = M.api(cfg, f"/events?msg_id=like.{like}&stage=eq.delivered&select=msg_id,at")
        got = rows if st == 200 and isinstance(rows, list) else []
        lag = M.group_lag(cfg, cfg["kafka"]["groups"]["perf"])["lag"]
        print(f"  t+{time.time() - t0:5.0f} s delivered {len(got)}/{sent}, group lag {lag}")
        if len(got) >= sent:
            break
        time.sleep(5)
    lat = sorted((ts(r["at"]) - ts(sent_at[r["msg_id"]])).total_seconds() * 1000 for r in got if r["msg_id"] in sent_at)
    if lat:
        first = min(ts(r["at"]) for r in got)
        last = max(ts(r["at"]) for r in got)
        span = max((last - first).total_seconds(), 0.001)
        p95 = lat[int(0.95 * (len(lat) - 1))]
        print(f"RESULT delivered {len(got)}/{sent}; end-to-end p50 {statistics.median(lat):.0f} ms, p95 {p95:.0f} ms; "
              f"drain {len(got) / span:.1f} msg/s")
    sys.exit(0 if len(got) >= sent else 1)


if __name__ == "__main__":
    main()
