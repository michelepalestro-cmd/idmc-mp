"""Run SQL against the stand-in Postgres without a Python driver (stdlib only).

Default transport: `docker compose -p rdf exec -T postgres psql -U <PG_USER> -d <PG_DB> -v ON_ERROR_STOP=1 -At`
(override with --psql "<command>", e.g. a local `psql -h localhost -U rdf_app -d rdf_retail`). The database login
secret is never on a command line: inside the container psql uses the local socket; for a remote psql set PGPASSWORD
in your shell or use a ~/.pgpass file.
"""
import os
import shlex
import subprocess
import sys
from pathlib import Path

INFRA = Path(__file__).resolve().parent


def default_cmd():
    user = os.environ.get("PG_USER", "rdf_app")
    db = os.environ.get("PG_DB", "rdf_retail")
    return ["docker", "compose", "-p", "rdf", "-f", str(INFRA / "docker-compose.yml"), "exec", "-T", "postgres",
            "psql", "-U", user, "-d", db]


def psql_cmd(override=None):
    base = shlex.split(override, posix=(os.name != "nt")) if override else default_cmd()
    return base + ["-v", "ON_ERROR_STOP=1", "-At", "-F", "\t"]


def run_sql(sql, override=None, check=True):
    """Feed SQL on stdin; return stdout lines."""
    r = subprocess.run(psql_cmd(override), input=sql, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit(f"psql failed (exit {r.returncode})")
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def q(s):
    """SQL literal (NULL for None)."""
    if s is None:
        return "NULL"
    if isinstance(s, (int, float)):
        return repr(s)
    return "'" + str(s).replace("'", "''") + "'"
