#!/usr/bin/env python3
"""Live-traffic stand-in for the retail front ends (web, mobile, store tills are OUT OF SCOPE): writes sign-ups,
memberships, orders + payments and store visits into the stand-in Postgres, so CDC, the batch lanes and the CRM sync
have something to move. Optionally it also calls the CAI real-time processes the way an application would.

  python infra/traffic.py --dry-run --count 5            # print the SQL of 5 events, touch nothing
  python infra/traffic.py --count 20 --interval 3        # 20 events, one every 3 s
  python infra/traffic.py --forever --interval 10        # until Ctrl-C
  python infra/traffic.py --count 1 --kind signup --cai  # one sign-up, then POST it to rdf_cai_customer_to_crm

--cai needs CAI_RT_BASE in the toolkit .env (the runtime base printed by idmc/05_cai.py url) and, for the default
authenticated processes, RDF_CAI_USER / RDF_CAI_PASS (an IDMC user listed in config.json cai.allowedUsers), sent with
Basic Authentication over https only. Calls fail open with a 6 s timeout, like the original application did: the
database write is never blocked by CAI.
"""
import argparse
import base64
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
from pgexec import q, run_sql  # noqa: E402
import rdf_common as C  # noqa: E402

FIRST = ["Ada", "Ben", "Cara", "Dev", "Esme", "Femi", "Gia", "Hal", "Isla", "Jon", "Kai", "Lia"]
LAST = ["Quinn", "Ross", "Shah", "Ueda", "Vance", "Wolfe", "Young", "Zeller", "Abbott", "Byrne"]
STORES = ["ST01", "ST02", "ST03", "ST04", "ST05"]


def signup(rnd, tag):
    f, l = rnd.choice(FIRST), rnd.choice(LAST)
    full = f"{f} {l}"
    if rnd.random() < 0.25:
        full = rnd.choice([full.lower(), "  " + full.upper() + " "])
    email = f"{f}.{l}.{tag}@example.com".lower()
    phone = "%03d%03d%04d" % (rnd.randint(201, 989), rnd.randint(200, 999), rnd.randint(0, 9999))
    store = rnd.choice(STORES)
    rec = {"full_name": full, "email": email, "phone": phone, "tier": rnd.choice(["Bronze", "silver ", "GOLD", ""]),
           "channel": rnd.choice(["web", "mobile", "store"]), "store": store,
           "address": f"{rnd.randint(1, 999)} Example St", "city": "Springfield", "state": "IL", "zip": "62701"}
    sql = ("INSERT INTO public.customers (full_name, email, phone, address, city, state, zip, tier, signup_channel, "  # nosec B608  # synthetic values quoted by q()
           f"home_store_code) VALUES ({q(rec['full_name'])}, {q(email)}, {q(phone)}, {q(rec['address'])}, "
           f"{q(rec['city'])}, {q(rec['state'])}, {q(rec['zip'])}, {q(rec['tier'])}, {q(rec['channel'])}, {q(store)}) "
           "RETURNING customer_id;")
    return sql, rec


def order(rnd):
    amt = round(rnd.uniform(5, 220), 2)
    store = rnd.choice(STORES)
    return ("WITH c AS (SELECT customer_id FROM public.customers ORDER BY random() LIMIT 1), "  # nosec B608  # synthetic values quoted by q()
            "p AS (SELECT product_id, unit_price FROM public.products ORDER BY random() LIMIT 1), "
            "o AS (INSERT INTO public.orders (customer_id, store_code, channel, status, list_amount, discount, amount) "
            f"SELECT c.customer_id, {q(store)}, 'store', 'paid', {amt}, 0, {amt} FROM c RETURNING order_id, customer_id), "
            "l AS (INSERT INTO public.order_lines (order_id, product_id, qty, unit_price, line_amount) "
            f"SELECT o.order_id, p.product_id, 1, {amt}, {amt} FROM o, p RETURNING order_id) "
            "INSERT INTO public.payments (customer_id, order_id, kind, amount, status, processor) "
            f"SELECT o.customer_id, o.order_id, 'order', {amt}, 'settled', {q(rnd.choice(['card', 'wallet']))} FROM o "
            "RETURNING order_id;")


def visit(rnd):
    return ("WITH c AS (SELECT customer_id FROM public.customers ORDER BY random() LIMIT 1) "  # nosec B608  # synthetic values quoted by q()
            f"INSERT INTO public.visits (customer_id, store_code) SELECT customer_id, {q(rnd.choice(STORES))} FROM c "
            "RETURNING visit_id;"
            " UPDATE public.visits SET check_out_at = now(), status = 'closed' "
            "WHERE status = 'open' AND check_in_at < now() - interval '30 minutes';")


def membership(rnd):
    tier, price = rnd.choice([("Bronze", 19), ("Silver", 39), ("Gold", 79)])
    return ("WITH c AS (SELECT customer_id FROM public.customers c WHERE NOT EXISTS (SELECT 1 FROM public.memberships m "  # nosec B608  # synthetic values quoted by q()
            "WHERE m.customer_id = c.customer_id) ORDER BY random() LIMIT 1), "
            "m AS (INSERT INTO public.memberships (customer_id, tier, status, monthly_price, started_at) "
            f"SELECT customer_id, {q(tier)}, 'active', {price}, now() FROM c RETURNING membership_id, customer_id, monthly_price) "
            "INSERT INTO public.payments (customer_id, membership_id, kind, amount, status, processor) "
            "SELECT customer_id, membership_id, 'membership', monthly_price, 'settled', 'card' FROM m RETURNING membership_id;")


def call_cai(process, payload, timeout=6):
    base = C.env("CAI_RT_BASE")
    if not base:
        print("   (CAI skipped: CAI_RT_BASE not set)")
        return None
    u = urllib.parse.urlsplit(base)
    if u.scheme != "https" or not (u.hostname or "").endswith(".informaticacloud.com"):
        print("   (CAI skipped: CAI_RT_BASE must be https://<pod>-cai.<domain>.informaticacloud.com/...)")
        return None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if "/public/rt/" not in u.path:          # authenticated endpoint (the default): Basic Authentication
        user, pw = C.env("RDF_CAI_USER"), C.env("RDF_CAI_PASS")
        if not (user and pw):
            print("   (CAI skipped: RDF_CAI_USER / RDF_CAI_PASS not set; the processes need Basic Authentication)")
            return None
        headers["Authorization"] = "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(base.rstrip("/") + "/" + process, data=json.dumps(payload).encode(), method="POST",
                                 headers=headers)
    t0 = time.time()
    try:
        with C.urlopen(req, timeout=timeout) as r:
            body = r.read().decode(errors="replace")
            print(f"   CAI {process}: HTTP {r.status} in {time.time() - t0:.2f}s {body[:200]}")
            return body
    except Exception as e:  # fail open: the app keeps working when CAI is slow or down
        print(f"   CAI {process}: failed open after {time.time() - t0:.2f}s ({type(e).__name__})")
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--forever", action="store_true")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--kind", choices=["mix", "signup", "order", "visit", "membership"], default="mix")
    ap.add_argument("--cai", action="store_true", help="also POST sign-ups to the CAI process rdf_cai_customer_to_crm")
    ap.add_argument("--dry-run", action="store_true", help="print the SQL, touch nothing")
    ap.add_argument("--psql", help="psql command to use instead of docker compose exec")
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    rnd = random.Random(a.seed)  # nosec B311  # seeded synthetic test data, not crypto
    n = 0
    try:
        while a.forever or n < a.count:
            n += 1
            kind = a.kind if a.kind != "mix" else rnd.choices(["signup", "order", "visit", "membership"], [3, 5, 3, 1])[0]
            tag = "%d%03d" % (int(time.time()), n)
            rec = None
            if kind == "signup":
                sql, rec = signup(rnd, tag)
            else:
                sql = {"order": order, "visit": visit, "membership": membership}[kind](rnd)
            if a.dry_run:
                print(f"[{n}] {kind}: {sql[:300]}")
            else:
                ids = run_sql(sql, a.psql)
                print(f"[{n}] {kind}: id {ids[0] if ids else '?'}")
                if kind == "signup" and a.cai and ids:
                    call_cai("rdf_cai_customer_to_crm", {"customer_id": ids[0], "email": rec["email"],
                                                         "full_name": rec["full_name"], "phone": rec["phone"],
                                                         "tier": rec["tier"], "channel": rec["channel"]})
            if a.forever or n < a.count:
                time.sleep(a.interval)
    except KeyboardInterrupt:
        print("stopped")
    print(f"{n} event(s)")


if __name__ == "__main__":
    main()
