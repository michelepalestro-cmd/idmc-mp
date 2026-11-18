#!/usr/bin/env python3
"""snowflake_sql.py - run the Bid Desk Snowflake SQL files (or one query) through the Snowflake SQL API, stdlib only.

    python snowflake_sql.py render infra/snowflake/02_bronze.sql          # print the SQL with config values filled in
    python snowflake_sql.py apply infra/snowflake/0*.sql [--execute]      # run every statement in order (dry run: print)
    python snowflake_sql.py query "SELECT * FROM BID_GLD_READINESS"       # read-only: print the rows
    python snowflake_sql.py guard                                         # the resource monitor: quota, used, level

Auth: SNOWFLAKE_PAT (a programmatic access token) as a Bearer token with
X-Snowflake-Authorization-Token-Type: PROGRAMMATIC_ACCESS_TOKEN. Account, warehouse, database, schema, role come from
config.json (snowflake.*). 01_cost_guard_and_access.sql needs ACCOUNTADMIN: run that file in a Snowsight worksheet if your
token's role cannot create monitors and roles (render prints it ready to paste).

Error 090073 'Warehouse cannot be resumed because resource monitor has exceeded its quota' means the cost guard
stopped the warehouse: every IDMC task, catalog profiling and Tableau refresh on it fails the same way until an account
admin raises the quota (ALTER RESOURCE MONITOR <monitor> SET CREDIT_QUOTA = <n>) or the month resets (KB L-ENV-096).
"""
from __future__ import annotations

import glob
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import bid_common as C  # noqa: E402


def endpoint(cfg):
    acct = cfg["snowflake"]["account"]
    return f"https://{acct}.snowflakecomputing.com/api/v2/statements"


def split_sql(text):
    out, cur = [], []
    for line in text.splitlines():
        if (line.strip().startswith("--") or not line.strip()) and not cur:
            continue
        cur.append(line)
        if line.rstrip().endswith(";"):
            stmt = "\n".join(cur).strip().rstrip(";").strip()
            if stmt and not all(l.strip().startswith("--") or not l.strip() for l in stmt.splitlines()):
                out.append(stmt)
            cur = []
    tail = "\n".join(cur).strip()
    if tail and not all(l.strip().startswith("--") or not l.strip() for l in tail.splitlines()):
        out.append(tail)
    return out


def run(cfg, statement, timeout=300):
    """one statement -> (status, json). Never prints the token."""
    sf = cfg["snowflake"]
    body = {"statement": statement, "timeout": timeout, "warehouse": sf["warehouse"], "database": sf["database"],
            "schema": sf["schema"], "role": sf["role"], "parameters": {"QUERY_TAG": "bid_desk_blueprint"}}
    req = urllib.request.Request(endpoint(cfg) + "?requestId=" + str(uuid.uuid4()), data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + C.env("SNOWFLAKE_PAT"),
                                          "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
                                          "Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "bid-desk-blueprint/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout + 30) as r:
            st, d = r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        st, d = e.code, json.loads(e.read() or b"{}") if e.headers.get("Content-Type", "").startswith("application/json") else {}
    while st == 202 and d.get("statementHandle"):                    # still running: poll the handle
        time.sleep(2)
        req = urllib.request.Request(endpoint(cfg) + "/" + d["statementHandle"],
                                     headers={"Authorization": "Bearer " + C.env("SNOWFLAKE_PAT"),
                                              "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
                                              "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            st, d = r.status, json.loads(r.read() or b"{}")
    if str(d.get("code")) == "090073":
        C.H.die("Snowflake 090073: the resource monitor stopped the warehouse (quota reached). Raise it: "
                f"ALTER RESOURCE MONITOR {cfg['snowflake']['monitor']} SET CREDIT_QUOTA = <n>;  (KB L-ENV-096)")
    return st, d


def rows(cfg, statement):
    st, d = run(cfg, statement)
    if st != 200:
        C.H.die(f"Snowflake {st} {d.get('code')} {str(d.get('message'))[:300]}")
    cols = [c["name"] for c in (d.get("resultSetMetaData") or {}).get("rowType") or []]
    return [dict(zip(cols, r)) for r in d.get("data") or []]


def main():
    ap = C.argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__,
                                   formatter_class=C.argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["render", "apply", "query", "guard"])
    ap.add_argument("args", nargs="*", help="SQL files (render/apply) or one statement (query)")
    ap.add_argument("--config")
    ap.add_argument("--execute", action="store_true", help="apply: really run the statements")
    a = ap.parse_args()
    C.H.safe_console()
    cfg = C.load_config(a.config)
    if a.cmd in ("render", "apply"):
        files = [f for pat in a.args for f in sorted(glob.glob(str(C.BP / pat)) or glob.glob(pat))]
        if not files:
            C.H.die("no SQL files matched")
        for f in files:
            text = C.render(Path(f).read_text(encoding="utf-8"), cfg)
            stmts = split_sql(text)
            print(f"-- {Path(f).name}: {len(stmts)} statements")
            for i, s in enumerate(stmts, 1):
                if a.cmd == "render" or not a.execute:
                    print((s if a.cmd == "render" else f"[DRY-RUN] {i}: " + s.splitlines()[0][:110]) + (";" if a.cmd == "render" else ""))
                    continue
                st, d = run(cfg, s)
                print(f"  {i:>3} {st} {(d.get('message') or '')[:120]}  | {s.splitlines()[0][:80]}")
                if st != 200:
                    C.H.die(f"stopped at statement {i} of {Path(f).name}: {d.get('code')} {str(d.get('message'))[:300]}")
        if a.cmd == "apply" and not a.execute:
            print("DRY-RUN: nothing sent. Add --execute (needs SNOWFLAKE_PAT).")
    elif a.cmd == "query":
        for r in rows(cfg, " ".join(a.args)):
            print(json.dumps(r, default=str))
    else:
        for r in rows(cfg, f"SHOW RESOURCE MONITORS LIKE '{cfg['snowflake']['monitor']}'"):
            print({k: r.get(k) for k in ("name", "credit_quota", "used_credits", "remaining_credits", "level", "frequency")})


if __name__ == "__main__":
    main()
