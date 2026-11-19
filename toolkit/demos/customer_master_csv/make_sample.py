#!/usr/bin/env python3
"""make_sample.py - write a messy customer CSV (and its answer key) for the customer-mastering user story.

    python3 make_sample.py                      # 150 customers -> data/customers_raw.csv + data/truth.csv
    python3 make_sample.py --customers 1000 --seed 7

Every value is fictional: names from short lists, e-mails @example.com, phones 555-01xx. The same seed always gives
the same files. Empty cells are written as (blank) (an empty field can fail an IDMC CSV source, L-CONN-066).
data/truth.csv maps each source_id to the real person it describes, so the match can be scored.
Standard library only.
"""
import argparse
import csv
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLANK = "(blank)"   # empty cells are written as (blank): an empty field can fail an IDMC flat-file source (L-CONN-066)
FIRST = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
         "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
         "Daniel", "Nancy", "Matthew", "Lisa", "Anthony", "Betty", "Mark", "Sandra", "Paul", "Ashley", "Mary-Jane",
         "Sean", "Aoife", "Luis", "Ana", "Wei", "Mei", "Omar", "Fatima", "Ivan"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Perez", "Thompson", "White", "Harris", "O'Brien", "Clark", "Lewis", "Robinson", "Walker", "Young",
        "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green"]
STREETS = ["Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "Washington", "Lake", "Hill", "Park"]
KINDS = [("Street", "St"), ("Avenue", "Ave"), ("Road", "Rd")]
CITIES = [("Springfield", "IL", "62701"), ("Riverton", "WY", "82501"), ("Fairview", "OR", "97024"),
          ("Madison", "WI", "53703"), ("Georgetown", "TX", "78626"), ("Salem", "MA", "01970"),
          ("Franklin", "TN", "37064"), ("Clinton", "IA", "52732")]
STATE_NAMES = {"IL": "Illinois", "WY": "Wyoming", "OR": "Oregon", "WI": "Wisconsin", "TX": "Texas",
               "MA": "Massachusetts", "TN": "Tennessee", "IA": "Iowa"}


def person(i, rnd):
    first, last = rnd.choice(FIRST), rnd.choice(LAST)
    street, kind = rnd.choice(STREETS), rnd.choice(KINDS)
    city, state, zip5 = rnd.choice(CITIES)
    return {"first": first, "last": last,
            "email": f"{first}.{last}{i}@example.com".lower().replace("'", ""),
            "phone": f"{rnd.choice(['217', '307', '503', '608', '512', '978', '615', '563'])}55501{rnd.randint(0, 99):02d}",
            "num": rnd.randint(1, 9999), "street": street, "kind": kind,
            "city": city, "state": state, "zip": zip5}


def messy_record(p, rnd):
    """One source record of person p, with the kinds of mess real customer files have."""
    name = f"{p['first']} {p['last']}"
    r = rnd.random()
    if r < 0.2:
        name = f"{p['last']}, {p['first']}"                      # "Last, First"
    elif r < 0.35:
        name = name.upper()
    elif r < 0.45:
        name = name.lower()
    if rnd.random() < 0.3:
        name = "  " + name.replace(" ", "   ") + " "              # stray spaces
    email = p["email"]
    if rnd.random() < 0.3:
        email = email.upper()
    if rnd.random() < 0.2:
        email = " " + email + "  "
    if rnd.random() < 0.12:
        email = ""                                                  # missing
    d = p["phone"]
    phone = rnd.choice([f"({d[:3]}) {d[3:6]}-{d[6:]}", f"{d[:3]}.{d[3:6]}.{d[6:]}", f"+1 {d[:3]} {d[3:6]} {d[6:]}",
                        d, f"1-{d[:3]}-{d[3:6]}-{d[6:]}"])
    if rnd.random() < 0.08:
        phone = ""
    long_kind, short_kind = p["kind"]
    address = f"{p['num']} {p['street']} {rnd.choice([long_kind, short_kind, short_kind + '.'])}"
    if rnd.random() < 0.3:
        address = address.lower()
    city = p["city"] if rnd.random() < 0.7 else p["city"].upper()
    state = rnd.choice([p["state"], p["state"].lower(), STATE_NAMES[p["state"]]]) if rnd.random() < 0.3 else p["state"]
    zip_ = rnd.choice([p["zip"], p["zip"] + "-" + f"{rnd.randint(0, 9999):04d}", p["zip"].lstrip("0")])
    day = f"2026-{rnd.randint(1, 10):02d}-{rnd.randint(1, 28):02d}"
    return {"full_name": name, "email": email, "phone": phone, "address": address, "city": city,
            "state": state, "zip": zip_, "updated_at": day}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--customers", type=int, default=150, help="real people to generate (default 150)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(HERE / "data"), help="output folder (default data/)")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, truth = [], []
    for i in range(1, a.customers + 1):
        p = person(i, rnd)
        for _ in range(rnd.choices([1, 2, 3, 4], weights=[45, 30, 17, 8])[0]):
            rows.append(messy_record(p, rnd))
            truth.append(f"P{i:05d}")
    order = list(range(len(rows)))
    rnd.shuffle(order)
    fields = ["source_id", "full_name", "email", "phone", "address", "city", "state", "zip", "updated_at"]
    with open(out / "customers_raw.csv", "w", newline="", encoding="utf-8") as f, \
            open(out / "truth.csv", "w", newline="", encoding="utf-8") as g:
        w, t = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL), csv.writer(g)   # quoted, like IDMC's own CSVs
        w.writeheader()
        t.writerow(["source_id", "person_id"])
        for n, k in enumerate(order, 1):
            sid = f"S{n:06d}"
            w.writerow({"source_id": sid, **{c: (v if v != "" else BLANK) for c, v in rows[k].items()}})
            t.writerow([sid, truth[k]])
    print(f"wrote {len(rows)} records of {a.customers} people -> {out / 'customers_raw.csv'} (+ truth.csv)")


if __name__ == "__main__":
    main()
