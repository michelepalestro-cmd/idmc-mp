#!/usr/bin/env python3
"""Seed the stand-in retail database with synthetic, deliberately dirty data (stdlib only, deterministic).

  python infra/seed.py --out seed.sql                 # write the SQL only (offline)
  python infra/seed.py --apply                        # pipe it into the docker compose Postgres (see pgexec.py)
  python infra/seed.py --customers 2000 --seed 7 --apply

What it creates: 5 stores, 24 products, N customers (about 8 % with messy names / e-mails / phones / tiers, about 4 %
near-duplicate people: same person typed differently), memberships for about 40 %, orders with 1-4 lines, payments
(a few with missing status or processor, for the DQ rules) and store visits. All names, streets and domains are
invented; e-mail domains are example.com / example.org style test domains.
"""
import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pgexec import q, run_sql  # noqa: E402

FIRST = ["Ava", "Liam", "Mia", "Noah", "Zoe", "Ethan", "Ivy", "Lucas", "Nora", "Owen", "Ruby", "Eli", "Maya", "Leo",
         "Iris", "Jude", "Cleo", "Finn", "Tess", "Omar", "Lena", "Ravi", "Sofia", "Hugo", "Anya", "Theo"]
LAST = ["Rivera", "Chen", "Patel", "Okafor", "Novak", "Haddad", "Larsen", "Moreau", "Silva", "Kowalski", "Tanaka",
        "Brennan", "Duarte", "Fischer", "Ibrahim", "Jansen", "Kim", "Lopez", "Murphy", "Nakamura", "O'Neill", "Price"]
STREETS = ["Maple Ave", "Oak St", "Cedar Ln", "Birch Rd", "Elm Ct", "Willow Way", "Harbor Blvd", "Summit Dr"]
STORES = [("ST01", "Riverside", "Springfield", "IL"), ("ST02", "Lakeshore", "Fairview", "TX"),
          ("ST03", "Hillcrest", "Madison", "WI"), ("ST04", "Downtown", "Franklin", "TN"),
          ("ST05", "Harborview", "Clinton", "FL")]
CATS = {"Apparel": (12, 80), "Footwear": (40, 140), "Home": (8, 120), "Snacks": (2, 9), "Electronics": (25, 400),
        "Beauty": (6, 60)}
TIERS = [("Bronze", 19.0), ("Silver", 39.0), ("Gold", 79.0)]
DOMAINS = ["example.com", "example.org", "mail.example.com"]


def dirty_name(n, rnd):
    return rnd.choice([n.lower(), n.upper(), "  " + n + "  ", n.replace(" ", "   ")])


def dirty_email(e, rnd):
    return rnd.choice([e.upper(), " " + e + " ", e.replace("@", "@@"), e.replace(".", "", 1)])


def dirty_phone(p, rnd):
    return rnd.choice([p[:3] + "-" + p[3:6] + "-" + p[6:], "(" + p[:3] + ") " + p[3:6] + " " + p[6:], "1" + p,
                       p[:7], ""])


def build(n_customers, seed):
    rnd = random.Random(seed)  # nosec B311  # seeded synthetic test data, not crypto
    now = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=rnd.randint(0, 200))
    out = ["BEGIN;"]
    for code, name, city, st in STORES:
        out.append(f"INSERT INTO public.stores (store_code, name, city, state, opened_at) VALUES "  # nosec B608  # synthetic values quoted by q()
                   f"({q(code)}, {q(name + ' Store')}, {q(city)}, {q(st)}, {q((now - timedelta(days=900)).isoformat())});")
    pid = 0
    prices = {}
    for cat, (lo, hi) in CATS.items():
        for i in range(4):
            pid += 1
            price = round(rnd.uniform(lo, hi), 2)
            prices[pid] = price
            out.append(f"INSERT INTO public.products (sku, name, category, unit_price) VALUES "  # nosec B608  # synthetic values quoted by q()
                       f"({q('SKU-%04d' % pid)}, {q(cat + ' item ' + str(i + 1))}, {q(cat)}, {price});")
    cid = mid = oid = 0
    people = []
    for i in range(n_customers):
        f, l = rnd.choice(FIRST), rnd.choice(LAST)
        num = rnd.randint(10, 9999)
        email = f"{f}.{l}{rnd.randint(1, 99)}@{rnd.choice(DOMAINS)}".lower().replace("'", "")
        phone = "%03d%03d%04d" % (rnd.randint(201, 989), rnd.randint(200, 999), rnd.randint(0, 9999))
        store = rnd.choice(STORES)
        addr = f"{num} {rnd.choice(STREETS)}"
        tier = rnd.choice(["Bronze", "Silver", "Gold", ""])
        full = f"{f} {l}"
        created = now - timedelta(days=rnd.randint(0, 365), minutes=rnd.randint(0, 1440))
        rec = dict(full=full, email=email, phone=phone, addr=addr, city=store[2], state=store[3],
                   zip="%05d" % rnd.randint(10000, 99999), tier=tier, ch=rnd.choice(["web", "mobile", "store"]),
                   store=store[0], created=created)
        if rnd.random() < 0.08:            # messy record
            rec.update(full=dirty_name(full, rnd), email=dirty_email(email, rnd), phone=dirty_phone(phone, rnd),
                       tier=rnd.choice(["GOLD ", "gld", "silver ", "brz", "platinum"]), state=rec["state"].lower(),
                       addr=rnd.choice([addr.lower(), "  " + addr + " ", ""]))
        people.append(rec)
        if rnd.random() < 0.04:            # the same person signs up again, typed differently
            dup = dict(rec)
            dup.update(full=dirty_name(full, rnd), phone=dirty_phone(phone, rnd), created=created + timedelta(days=3),
                       zip="" if rnd.random() < 0.5 else rec["zip"])
            people.append(dup)
    for rec in people:
        cid += 1
        out.append("INSERT INTO public.customers (full_name, email, phone, address, city, state, zip, tier, signup_channel, "  # nosec B608  # synthetic values quoted by q()
                   "home_store_code, created_at, updated_at) VALUES "
                   f"({q(rec['full'])}, {q(rec['email'])}, {q(rec['phone'])}, {q(rec['addr'])}, {q(rec['city'])}, "
                   f"{q(rec['state'])}, {q(rec['zip'])}, {q(rec['tier'])}, {q(rec['ch'])}, {q(rec['store'])}, "
                   f"{q(rec['created'].isoformat())}, {q(rec['created'].isoformat())});")
        tier_pick = None
        if rnd.random() < 0.4:
            mid += 1
            tier_pick, price = rnd.choice(TIERS)
            status = rnd.choice(["active", "active", "active", "cancelled"])
            started = rec["created"] + timedelta(days=1)
            out.append("INSERT INTO public.memberships (customer_id, tier, status, monthly_price, started_at, cancelled_at) "  # nosec B608  # synthetic values quoted by q()
                       f"VALUES ({cid}, {q(tier_pick)}, {q(status)}, {price}, {q(started.isoformat())}, "
                       f"{q((started + timedelta(days=60)).isoformat()) if status == 'cancelled' else 'NULL'});")
            out.append("INSERT INTO public.payments (customer_id, membership_id, kind, amount, status, processor, paid_at) "  # nosec B608  # synthetic values quoted by q()
                       f"VALUES ({cid}, {mid}, 'membership', {price}, 'settled', 'card', {q(started.isoformat())});")
        for _ in range(rnd.randint(0, 5)):
            oid += 1
            store = rnd.choice(STORES)[0] if rnd.random() < 0.3 else rec["store"]
            ts = rec["created"] + timedelta(days=rnd.randint(1, 120), minutes=rnd.randint(0, 900))
            lines = [(rnd.randint(1, pid), rnd.randint(1, 3)) for _ in range(rnd.randint(1, 4))]
            list_amt = round(sum(prices[p] * qn for p, qn in lines), 2)
            disc = round(list_amt * {"Bronze": 0.05, "Silver": 0.10, "Gold": 0.20}.get(tier_pick, 0), 2)
            status = rnd.choice(["paid", "paid", "paid", "placed", "refunded"])
            out.append("INSERT INTO public.orders (customer_id, store_code, channel, status, list_amount, discount, amount, "  # nosec B608  # synthetic values quoted by q()
                       f"ordered_at) VALUES ({cid}, {q(store)}, {q(rnd.choice(['web', 'mobile', 'store']))}, {q(status)}, "
                       f"{list_amt}, {disc}, {round(list_amt - disc, 2)}, {q(ts.isoformat())});")
            for p, qn in lines:
                out.append("INSERT INTO public.order_lines (order_id, product_id, qty, unit_price, line_amount) VALUES "  # nosec B608  # synthetic values quoted by q()
                           f"({oid}, {p}, {qn}, {prices[p]}, {round(prices[p] * qn, 2)});")
            pst = None if rnd.random() < 0.02 else ("refunded" if status == "refunded" else "settled")
            proc = None if rnd.random() < 0.02 else rnd.choice(["card", "wallet", "cash"])
            out.append("INSERT INTO public.payments (customer_id, order_id, kind, amount, status, processor, paid_at) VALUES "  # nosec B608  # synthetic values quoted by q()
                       f"({cid}, {oid}, 'order', {round(list_amt - disc, 2)}, {q(pst)}, {q(proc)}, {q(ts.isoformat())});")
            if rnd.random() < 0.6:
                out.append("INSERT INTO public.visits (customer_id, store_code, check_in_at, check_out_at, status) VALUES "  # nosec B608  # synthetic values quoted by q()
                           f"({cid}, {q(store)}, {q(ts.isoformat())}, {q((ts + timedelta(minutes=rnd.randint(5, 140))).isoformat())}, 'closed');")
    out.append("COMMIT;")
    return "\n".join(out) + "\n", {"customers": cid, "memberships": mid, "orders": oid}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--customers", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", help="write the SQL to this file")
    ap.add_argument("--apply", action="store_true", help="run it against the stand-in Postgres")
    ap.add_argument("--psql", help="psql command to use instead of docker compose exec")
    a = ap.parse_args()
    sql, counts = build(a.customers, a.seed)
    print(f"generated: {counts} ({len(sql.splitlines())} statements)")
    if a.out:
        Path(a.out).write_text(sql, encoding="utf-8")
        print("wrote", a.out)
    if a.apply:
        run_sql(sql, a.psql)
        print("applied")
    if not a.out and not a.apply:
        print("nothing written (use --out FILE and/or --apply)")


if __name__ == "__main__":
    main()
