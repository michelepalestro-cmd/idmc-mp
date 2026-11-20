#!/usr/bin/env python3
"""ops.py - a small operator console on the command line (reads the ledger; replays through CAI).

  python verify/ops.py status                 target row counts, hospital by reason/status, consumer-group lag
  python verify/ops.py hospital [--all]       open (or all) hospital entries
  python verify/ops.py replay <id>            replay one entry through the CAI process mbr_error_queue_replay (agent host)
  python verify/ops.py discard <id>           mark an entry discarded (an operator decision; nothing is sent)
  python verify/ops.py trace <msg_id>         the ledger timeline of one message
  python verify/ops.py reset --yes            empty the ledger, the hospital and the stand-in targets (a clean baseline)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mbr_msgs as M  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("cmd", choices=["status", "hospital", "replay", "discard", "trace", "reset"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = M.CFG.load(a.config)
    if a.cmd == "status":
        print("targets:", M.api(cfg, "/targets")[1])
        print("hospital:", M.api(cfg, "/dash_error_queue")[1])
        for g in cfg["kafka"]["groups"].values():
            lg = M.group_lag(cfg, g)
            print(f"group {g}: lag {lg['lag']}, members {lg['members']}")
    elif a.cmd == "hospital":
        q = "/error_queue?order=id.desc&limit=50" + ("" if a.all else "&status=eq.open")
        for e in M.api(cfg, q)[1] or []:
            print(f"{e['id']:>6} {e['status']:9} {e['reason_code']:22} retry={str(e['retryable']):5} replays={e['replays']} "
                  f"{e['family']:6} {e['biz_id']:12} {str(e['reason_text'])[:80]}")
    elif a.cmd == "replay":
        st, txt = M.agent_post(cfg, "mbr_error_queue_replay", {"id": a.arg, "actor": "operator"})
        print(f"HTTP {st} {txt[:300]}")
    elif a.cmd == "discard":
        print(M.api(cfg, "/rpc/eq_mark", {"id": a.arg, "status": "discarded", "actor": "operator"}))
    elif a.cmd == "trace":
        M.show(M.events(cfg, a.arg))
        for e in M.error_queue(cfg, a.arg):
            print("  hospital:", {k: e[k] for k in ("id", "reason_code", "status", "replays", "retryable")})
    else:
        if not a.yes:
            sys.exit("reset empties the ledger and the stand-in targets: add --yes")
        print(M.api(cfg, "/rpc/reset_demo", {}))


if __name__ == "__main__":
    main()
