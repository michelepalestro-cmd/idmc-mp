#!/usr/bin/env python3
"""reference.py - the Python twin of mapping/m_customer_master_csv.json.

    python3 reference.py                       # data/customers_raw.csv -> expected/customers_golden.csv + customer_xref.csv
    python3 reference.py --in <raw.csv> --out <folder>

It applies the same rules, in the same order, with the same IDMC function behaviour (INITCAP, REG_REPLACE, SUBSTR,
LPAD, both sorters, the cluster and survivor passes), so a live IDMC run can be compared file for file
(`check.py --compare <folder with the two CSVs the run wrote>`). Standard library only.
"""
import argparse
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / "mapping" / "m_customer_master_csv.json"


def initcap(s):
    """IDMC INITCAP: first letter of each word upper, the rest lower; words split by spaces and non-alphanumerics."""
    out, start = [], True
    for ch in s:
        out.append(ch.upper() if start else ch.lower())
        start = not ch.isalnum()
    return "".join(out)


def state_codes():
    """The state DECODE of the mapping spec, read from the spec itself so the two can never drift."""
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    std = next(n for n in spec["nodes"] if n["name"] == "EXP_STANDARDIZE")
    expr = next(f["expr"] for f in std["fields"] if f["name"] == "customer_state")
    pairs = re.findall(r"'([A-Z ]+)', '([A-Z]{2})'", expr)
    return dict(pairs)


BLANK = "(blank)"                      # placeholder for an empty cell (an empty CSV field can fail an IDMC source, L-CONN-066)
EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")


def standardize(r, states):
    nz = lambda k: "" if (r.get(k) or "").strip() == BLANK else (r.get(k) or "")
    sp = re.sub(r"\s+", " ", nz("full_name")).strip()
    comma = sp.find(",") + 1                                       # INSTR is 1-based, 0 = absent
    name = (sp[comma:].strip() + " " + sp[:comma - 1].strip()).strip() if comma > 0 else sp
    name_key = re.sub(r"[^A-Za-z]", "", name).upper()
    email = nz("email").strip().lower()
    email_ok = 1 if EMAIL_RE.match(email) else 0
    digits = re.sub(r"[^0-9]", "", nz("phone"))
    phone = digits[1:11] if len(digits) == 11 and digits[0] == "1" else digits
    phone_ok = 1 if len(phone) == 10 else 0
    addr = re.sub(r"\s+", " ", nz("address")).strip().upper()
    for pat, rep in [(r"\.$", ""), (" STREET$", " ST"), (" AVENUE$", " AVE"), (" ROAD$", " RD")]:
        addr = re.sub(pat, rep, addr)
    state = nz("state").strip().upper()
    zipd = re.sub(r"[^0-9]", "", nz("zip"))
    zip5 = zipd[:5] if len(zipd) >= 5 else ("0" + zipd if len(zipd) == 4 else ("00" + zipd if len(zipd) == 3 else ""))
    return {
        "source_id": r["source_id"],
        "customer_name": initcap(name),
        "customer_email": email if email_ok else "",
        "customer_phone": f"({phone[:3]}) {phone[3:6]}-{phone[6:10]}" if phone_ok else "",
        "customer_address": addr,
        "customer_city": initcap(nz("city").strip()),
        "customer_state": states.get(state, state),
        "customer_zip": zip5,
        "last_updated": nz("updated_at").strip(),
        "block_key": name_key + "|" + zip5,
        "email_missing": 0 if email_ok else 1,
        "phone_digits": phone if phone_ok else "",
        "phone_missing": 0 if phone_ok else 1,
        "completeness": email_ok + phone_ok + (1 if addr else 0) + (1 if len(zip5) == 5 else 0),
    }


def master(rows):
    """SRT_BY_BLOCK -> EXP_CLUSTER -> SRT_BY_CUSTOMER -> EXP_SURVIVOR, exactly as the mapping runs them."""
    rows = sorted(rows, key=lambda x: (x["block_key"], x["email_missing"], x["customer_email"], x["phone_missing"],
                                       x["phone_digits"], x["source_id"]))
    prev_block, grp, cl_email, cl_phone = "", 0, "", ""
    for x in rows:
        em, ph = x["customer_email"], x["phone_digits"]
        new = 1 if (x["block_key"] != prev_block or (em and cl_email and em != cl_email)
                    or (ph and cl_phone and ph != cl_phone)) else 0
        rule = "FIRST" if new else ("EMAIL" if em and em == cl_email else ("PHONE" if ph and ph == cl_phone
                                                                            else "NAME+ZIP"))
        grp += new
        cl_email = em if new else (cl_email or em)
        cl_phone = ph if new else (cl_phone or ph)
        prev_block = x["block_key"]
        x["customer_id"], x["match_rule"] = f"CUST-{grp:06d}", rule
    rows = sorted(rows, key=lambda x: x["source_id"])
    rows = sorted(rows, key=lambda x: x["last_updated"], reverse=True)
    rows = sorted(rows, key=lambda x: x["completeness"], reverse=True)
    rows = sorted(rows, key=lambda x: x["customer_id"])
    prev = ""
    for x in rows:
        x["is_survivor"] = 0 if x["customer_id"] == prev else 1
        prev = x["customer_id"]
    return rows


GOLDEN = ["customer_id", "customer_name", "customer_email", "customer_phone", "customer_address", "customer_city",
          "customer_state", "customer_zip", "last_updated"]
XREF = ["source_id", "customer_id", "match_rule", "is_survivor"]


def run(raw, out):
    states = state_codes()
    with open(raw, newline="", encoding="utf-8") as f:
        rows = [standardize(r, states) for r in csv.DictReader(f)]
    rows = master(rows)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "customers_golden.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(GOLDEN)
        for x in rows:
            if x["is_survivor"]:
                w.writerow([x[k] for k in GOLDEN])
    with open(out / "customer_xref.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(XREF)
        for x in rows:
            w.writerow([x[k] for k in XREF])
    return rows


def score(rows, truth_csv):
    """Pairwise precision and recall of the match against the answer key."""
    with open(truth_csv, newline="", encoding="utf-8") as f:
        truth = {r["source_id"]: r["person_id"] for r in csv.DictReader(f)}
    by_cust, by_person = {}, {}
    for x in rows:
        by_cust.setdefault(x["customer_id"], []).append(x["source_id"])
        by_person.setdefault(truth[x["source_id"]], []).append(x["source_id"])
    pairs = lambda groups: {(a, b) for g in groups.values() for i, a in enumerate(sorted(g)) for b in sorted(g)[i + 1:]}
    found, real = pairs(by_cust), pairs(by_person)
    tp = len(found & real)
    return {"source_records": len(rows), "real_people": len(by_person), "customers_found": len(by_cust),
            "precision": round(tp / len(found), 4) if found else 1.0, "recall": round(tp / len(real), 4) if real else 1.0}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="raw", default=str(HERE / "data" / "customers_raw.csv"))
    ap.add_argument("--out", default=str(HERE / "expected"))
    ap.add_argument("--truth", default=str(HERE / "data" / "truth.csv"))
    a = ap.parse_args()
    rows = run(Path(a.raw), Path(a.out))
    print(f"expected output -> {a.out}: {sum(x['is_survivor'] for x in rows)} golden customers from {len(rows)} records")
    if Path(a.truth).is_file():
        print("match quality vs the answer key:", json.dumps(score(rows, a.truth)))


if __name__ == "__main__":
    main()
