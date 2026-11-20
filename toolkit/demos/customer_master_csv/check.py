#!/usr/bin/env python3
"""check.py - prove the customer-mastering user story offline, and time each step.

    python3 check.py                              # sample -> lint + build the IDMC package -> twin -> checks -> score
    python3 check.py --customers 2000             # a bigger sample
    python3 check.py --compare <folder>           # also compare a live run's customers_golden.csv + customer_xref.csv
    python3 check.py --out <folder>               # where data/, build/ and expected/ go (default: a new temp folder)
    python3 check.py --out .                      # write next to this demo instead (git ignores those folders)

By default nothing is written inside the plugin folder (it is replaced on every update).

No login and no network. The package it builds carries PLACEHOLDER ids (OFFLINE...): to import it into a real org,
use BUILD.md (mapgen resolve + deploy with --execute --expect-org). Standard library only.
"""
import argparse
import copy
import csv
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAPGEN = HERE.parents[1] / "mapgen"
sys.path.insert(0, str(MAPGEN))
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import make_sample  # noqa: E402

PROFILE = {
    "org": {"v2Id": "OFFLINE", "guid": "OFFLINEorgGuid00000001", "name": "offline"},
    "runtimeEnvironment": {"id": "OFFLINE_RE", "name": "<your Secure Agent group>"},
    "folder": {"project": "Customer_Master", "projectGuid": "OFFLINEprojectGuid0001", "name": "csv",
               "guid": "OFFLINEfolderGuid00001"},
    "connections": {"FF": {"guid": "OFFLINEconnGuidFF0001", "name": "FF_CUSTOMERS", "repoHandle": "OFFLINE_FF",
                           "kind": "FF"}},
    "vars": {},
}
TIMES = []


def step(label, fn):
    t = time.perf_counter()
    out = fn()
    TIMES.append((label, time.perf_counter() - t))
    return out


def build_package(root):
    from idmc_mapgen import lint as L
    from idmc_mapgen.spec import load_spec
    from idmc_mapgen.compile import build
    from idmc_mapgen.package import package_bytes
    raw = json.loads((HERE / "mapping" / "m_customer_master_csv.json").read_text(encoding="utf-8"))
    issues = L.lint(copy.deepcopy(raw), profile=PROFILE, allow_live=True)
    sev = lambda i: getattr(i, "severity", None) or (i[1] if isinstance(i, tuple) else "")
    errs = [i for i in issues if sev(i) == "ERROR"]
    for i in issues:
        print(f"  lint {sev(i)}: {getattr(i, 'code', i[0] if isinstance(i, tuple) else i)} "
              f"{getattr(i, 'message', '') or (i[3] if isinstance(i, tuple) and len(i) > 3 else '')}"[:200])
    if errs:
        raise SystemExit("lint errors: fix the spec")
    spec = load_spec(raw, profile=PROFILE)
    imf = build(spec)
    pkg = package_bytes(spec, imf)
    out = root / "build"
    out.mkdir(parents=True, exist_ok=True)
    (out / "m_customer_master_csv.pkg.zip").write_bytes(pkg)
    (out / "m_customer_master_csv.imf.json").write_text(json.dumps(imf, indent=1), encoding="utf-8")
    return len(imf["content"]["transformations"]), len(imf["content"]["links"]), len(pkg)


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify(expected, raw_csv):
    golden, xref, raw = read(expected / "customers_golden.csv"), read(expected / "customer_xref.csv"), \
        read(raw_csv)
    ids = [g["customer_id"] for g in golden]
    problems = []
    if len(xref) != len(raw):
        problems.append(f"xref has {len(xref)} rows for {len(raw)} source records")
    if {x["source_id"] for x in xref} != {r["source_id"] for r in raw}:
        problems.append("xref does not cover every source record exactly once")
    if len(set(ids)) != len(ids) or ids != [f"CUST-{n:06d}" for n in range(1, len(ids) + 1)]:
        problems.append("customer ids are not unique and sequential")
    if {x["customer_id"] for x in xref} != set(ids):
        problems.append("xref customer ids differ from the golden ids")
    if any(not g["customer_name"] for g in golden):
        problems.append("a golden record has no name")
    if any(g["customer_email"] and g["customer_email"] != g["customer_email"].lower() for g in golden):
        problems.append("an e-mail is not lower case")
    return problems, len(golden), len(raw)


def compare(expected, live):
    diffs = []
    for name in ("customers_golden.csv", "customer_xref.csv"):
        e, l = read(expected / name), read(live / name)
        key = "customer_id" if name.startswith("customers") else "source_id"
        ed, ld = {r[key]: r for r in e}, {r[key]: r for r in l}
        if set(ed) != set(ld):
            diffs.append(f"{name}: keys differ ({len(set(ed) ^ set(ld))} not in both)")
        for k in sorted(set(ed) & set(ld)):
            for col, v in ed[k].items():
                if (ld[k].get(col) or "") != v:
                    diffs.append(f"{name} {k} {col}: expected {v!r}, IDMC wrote {ld[k].get(col)!r}")
    return diffs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--customers", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--compare", metavar="FOLDER", help="folder holding the two CSVs a live IDMC run wrote")
    ap.add_argument("--out", metavar="FOLDER",
                    help="where data/, build/ and expected/ are written (default: a new temp folder; '.' = this demo)")
    a = ap.parse_args()
    root = (HERE if a.out == "." else Path(a.out).resolve()) if a.out else Path(tempfile.mkdtemp(prefix="customer_master_"))
    print(f"output folder: {root}")
    t0 = time.perf_counter()
    step("1. make a messy customer CSV", lambda: make_sample.generate(a.customers, a.seed, root / "data"))
    ntx, nlinks, size = step("2. lint + build the IDMC mapping package", lambda: build_package(root))
    sys.path.insert(0, str(HERE))
    import reference as R
    rows = step("3. run the Python twin (expected output)", lambda: R.run(root / "data" / "customers_raw.csv",
                                                                        root / "expected"))
    problems, ngold, nraw = step("4. check the outputs",
                                 lambda: verify(root / "expected", root / "data" / "customers_raw.csv"))
    quality = step("5. score the match against the answer key", lambda: R.score(rows, root / "data" / "truth.csv"))
    print(f"mapping: {ntx} transformations, {nlinks} links, package {size:,} bytes -> "
          f"{root / 'build' / 'm_customer_master_csv.pkg.zip'}")
    print(f"result: {nraw} messy records -> {ngold} golden customers (CUST-000001 ...), "
          f"cross-reference for every record")
    print("match quality:", json.dumps(quality))
    for label, s in TIMES:
        print(f"  {s * 1000:8.1f} ms  {label}")
    print(f"  {(time.perf_counter() - t0) * 1000:8.1f} ms  total")
    if a.compare:
        d = compare(root / "expected", Path(a.compare))
        print("live run matches the twin" if not d else f"{len(d)} difference(s):\n  " + "\n  ".join(d[:30]))
        problems += d
    if problems:
        print("FAILED:\n  " + "\n  ".join(problems))
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
