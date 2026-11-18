#!/usr/bin/env python3
"""Render infra/sql/03_bigquery_ddl.sql for your project and (optionally) run it with the Google Cloud `bq` CLI.

  python infra/bq_setup.py                 # dry run: render to state/rendered/bigquery_ddl.sql and print the plan
  python infra/bq_setup.py --offline       # same, with placeholders for unset .env values (no credentials needed)
  python infra/bq_setup.py --execute       # run each statement with: bq query --use_legacy_sql=false --project_id=<BQ_PROJECT>

Needs (only with --execute): the `bq` CLI on PATH, authenticated as an account that may create datasets
(for a service account: gcloud auth activate-service-account --key-file "$BQ_KEY_FILE"). Values come from the
toolkit .env (BQ_PROJECT) and config.json; nothing secret is printed.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import rdf_common as C  # noqa: E402


def statements(sql):
    out, buf = [], []
    for line in sql.splitlines():
        if line.strip().startswith("--") or not line.strip():
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            out.append("\n".join(buf).rstrip().rstrip(";"))
            buf = []
    if buf:
        out.append("\n".join(buf))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--offline", action="store_true", help="render with placeholders for unset .env values")
    ap.add_argument("--execute", action="store_true", help="run the statements with the bq CLI")
    a = ap.parse_args()
    cfg = C.load_config(a.config)
    v = C.template_vars(cfg, offline=a.offline or not a.execute)
    sql = C.render((Path(__file__).parent / "sql" / "03_bigquery_ddl.sql").read_text(encoding="utf-8"), v, "03_bigquery_ddl.sql")
    p = C.write_rendered("bigquery_ddl.sql", sql)
    st = statements(sql)
    print(f"rendered {len(st)} statement(s) -> {p.relative_to(C.BLUEPRINT)}")
    if not a.execute:
        for s in st:
            print("  [DRY-RUN] " + s.splitlines()[0][:110])
        print("dry run: nothing sent (add --execute to run them with the bq CLI)")
        return 0
    if not shutil.which("bq"):
        C.die("the bq CLI is not on PATH (install the Google Cloud SDK)")
    proj = C.env("BQ_PROJECT", required=True)
    bad = 0
    for s in st:
        r = subprocess.run(["bq", "query", "--use_legacy_sql=false", f"--project_id={proj}", "--quiet", s],
                           capture_output=True, text=True)
        print(("  OK   " if r.returncode == 0 else "  FAIL ") + s.splitlines()[0][:100])
        if r.returncode:
            bad += 1
            print("       " + (r.stderr or r.stdout).strip()[:400])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
