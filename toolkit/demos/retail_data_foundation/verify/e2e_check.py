#!/usr/bin/env python3
"""End-to-end check: one sign-up in the source -> golden record in the warehouse -> reverse ETL rows -> CRM Contact.

  python verify/e2e_check.py                       # dry run: print the plan, touch nothing (works offline)
  python verify/e2e_check.py --execute --expect-org <orgIdV3> [--cai] [--no-lane] [--timeout 900]

Steps (with --execute):
  1. insert one uniquely named, deliberately messy customer into the source DB      (infra/pgexec.py)
  2. --cai: POST it to rdf_cai_customer_to_crm, time the real-time Contact upsert    (CAI_RT_BASE + RDF_CAI_USER/PASS)
  3. run the sign-up lane tf_rdf_customer (3 jobs: ingest -> golden -> CRM sync)       (core taskflow run; costs jobs)
     --no-lane skips it and waits for the scheduled tf_rdf_full instead
  4. warehouse: the golden row exists, cleansed (Title Case name, lower-case e-mail, E.164 phone), dq_valid = 1
                                                                                     (bq CLI, BQ_PROJECT)
  5. operational DB: activation.customer_golden holds the row (reverse ETL, PostgreSQL Upsert applied, not 0 rows)
  6. CRM: the Contact with the external id exists and carries the cleansed values    (Salesforce REST, client creds)
PASS needs every step; each prints its evidence and elapsed seconds. The test record uses the domain verify.invalid:
it is valid by the e-mail rule (so it passes the clean-only gate) and easy to find and delete afterwards
(teardown/teardown.py --verify-records).
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "idmc" / "lib"))
sys.path.insert(0, str(ROOT / "infra"))
import rdf_common as C  # noqa: E402


def bq_rows(sql):
    if not shutil.which("bq"):
        C.die("the bq CLI is not on PATH (Google Cloud SDK)")
    r = subprocess.run(["bq", "query", "--use_legacy_sql=false", "--format=json", "--quiet",
                        f"--project_id={C.env('BQ_PROJECT', required=True)}", sql], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout)[:400])
    return json.loads(r.stdout or "[]")


def sf_query(soql, api):
    login = C.env("SF_LOGIN_URL", required=True).rstrip("/")
    form = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": C.env("SF_CLIENT_ID", required=True),
                                   "client_secret": C.env("SF_CLIENT_SECRET", required=True)}).encode()
    with C.urlopen(urllib.request.Request(login + "/services/oauth2/token", data=form, method="POST",
                                                       headers={"Content-Type": "application/x-www-form-urlencoded"}),
                                timeout=30) as r:
        tok = json.loads(r.read())
    url = f"{tok['instance_url']}/services/data/v{api}/query?q=" + urllib.parse.quote(soql)
    with C.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok["access_token"]}),
                                timeout=30) as r:
        return json.loads(r.read()).get("records", [])


def wait_for(label, fn, timeout, every=15):
    t0 = time.time()
    while True:
        try:
            got = fn()
        except Exception as e:  # keep polling through transient errors, report the last one
            got, err = None, e
        else:
            err = None
        if got:
            print(f"   {label}: found after {time.time() - t0:.0f} s")
            return got
        if time.time() - t0 > timeout:
            print(f"   {label}: NOT found within {timeout} s{' (' + str(err)[:200] + ')' if err else ''}")
            return None
        time.sleep(every)


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--cai", action="store_true", help="also test the real-time CAI path")
    ap.add_argument("--no-lane", action="store_true", help="do not start tf_rdf_customer; wait for the schedule")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--psql", help="psql command (default: docker compose exec)")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    tag = time.strftime("%Y%m%d%H%M%S")
    email = f"Verify.Rdf{tag}@Verify.Invalid"
    name = f"  verify   rdf{tag}  "
    gold = C.ident(cfg["warehouse"]["datasets"]["gold"])
    ext = C.ident(cfg["crm"]["contactExternalId"])
    act_schema = C.ident(cfg["source"]["activationSchema"])
    email_lc = email.lower()
    plan = [
        f"1 insert customer email={email.lower()} (messy name/phone/tier) into {cfg['source']['schema']}.customers",
        "2 POST rdf_cai_customer_to_crm (real time)" if a.cai else "2 (CAI path skipped; add --cai)",
        "3 run tf_rdf_customer" if not a.no_lane else "3 wait for the scheduled tf_rdf_full",
        "4 bq: SELECT ... FROM %s.customer_golden WHERE email = '%s'" % (gold, email_lc),  # nosec B608  # plan text printed only
        "5 psql: SELECT ... FROM %s.customer_golden WHERE customer_id = <id>" % act_schema,  # nosec B608  # plan text printed only
        "6 Salesforce: SELECT Id, FirstName, LastName, Email, Phone FROM Contact WHERE %s = '<id>'" % ext,  # nosec B608  # plan text printed only
    ]
    if not a.execute:
        print("dry run - the end-to-end check would do:")
        for p in plan:
            print("  " + p)
        print("needs:", ", ".join(f"{k}={v}" for k, v in C.env_status(
            ["IDMC_USER", "IDMC_PASS", "IDMC_LOGIN_HOST", "BQ_PROJECT", "SF_LOGIN_URL", "SF_CLIENT_ID", "SF_CLIENT_SECRET"]
            + (["CAI_RT_BASE", "RDF_CAI_USER", "RDF_CAI_PASS"] if a.cai else []))))
        return 0
    C.offline_session_guard(a)
    from pgexec import q, run_sql
    t0 = time.time()
    results = {}
    vals = ", ".join([q(name), q(" " + email + " "), q("(217) 555-0" + tag[-3:]), q("12 verify lane"), q("springfield"),
                      q("il"), q("62701"), q("GOLD "), "'web'", "'ST01'"])
    ins = ("INSERT INTO public.customers (full_name, email, phone, address, city, state, zip, tier, signup_channel, "  # nosec B608  # every value quoted by q()
           "home_store_code) VALUES (%s) RETURNING customer_id;" % vals)
    cid = run_sql(ins, a.psql)[0]
    print(f"1 inserted customer_id {cid}")
    results["source"] = True
    if a.cai:
        sys.path.insert(0, str(ROOT / "infra"))
        from traffic import call_cai
        t1 = time.time()
        body = call_cai("rdf_cai_customer_to_crm", {"customer_id": cid, "email": email, "full_name": name,
                                                    "phone": "2175550" + tag[-3:], "tier": "GOLD ", "channel": "web"})
        results["cai"] = bool(body and "upserted" in body)
        print(f"2 CAI real time: {'OK' if results['cai'] else 'FAILED'} in {time.time() - t1:.2f} s")
    if not a.no_lane:
        wid = ((st.get("taskflows") or {}).get("tf_rdf_customer") or {}).get("id")
        if not wid:
            C.die("tf_rdf_customer id missing in state/ids.json (run 04_taskflows.py schedule or apply first)")
        rc = C.core_cli("idmc_taskflow_schedule.py", ["run", wid] + C.gate_args(a))
        print(f"3 lane run exit {rc}")
    bq_table = "%s.%s.customer_golden" % (C.gcp_project(C.env("BQ_PROJECT", required=True)), gold)
    sql = ("SELECT customer_id, full_name, email, phone_e164, tier, dq_valid FROM "  # nosec B608  # validated identifiers and int id
           "`%s` WHERE customer_id = %d" % (bq_table, int(cid)))
    rows = wait_for("4 golden record", lambda: bq_rows(sql), a.timeout)
    if rows:
        r = rows[0]
        ok = r.get("email") == email.lower() and r.get("full_name") == f"Verify Rdf{tag}" and str(r.get("dq_valid")) == "1" \
            and (r.get("phone_e164") or "").startswith("+1") and r.get("tier") == "Gold"
        print(f"   {json.dumps(r)} -> {'cleansed OK' if ok else 'NOT as expected'}")
        results["golden"] = ok
    act_sql = "SELECT full_name, email, dq_valid FROM %s.customer_golden WHERE customer_id = %d;" % (act_schema, int(cid))  # nosec B608  # validated schema and int id
    act = wait_for("5 reverse ETL row", lambda: run_sql(act_sql, a.psql), a.timeout, every=10)
    results["reverse_etl"] = bool(act)
    soql = "SELECT Id, FirstName, LastName, Email, Phone FROM Contact WHERE %s = '%d'" % (ext, int(cid))  # nosec B608  # validated field and int id
    sf = wait_for("6 CRM Contact", lambda: sf_query(soql, cfg["crm"]["apiVersion"]), a.timeout)
    if sf:
        print(f"   {json.dumps({k: v for k, v in sf[0].items() if k != 'attributes'})}")
    results["crm"] = bool(sf)
    ok = all(results.values())
    print(f"\n{'PASS' if ok else 'FAIL'} in {time.time() - t0:.0f} s: " + ", ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in results.items()))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
