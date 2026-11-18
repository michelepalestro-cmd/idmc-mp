#!/usr/bin/env python3
"""Offline smoke check of the whole blueprint (no network, no credentials): every template renders, every mapping
compiles + lints + packages, the CAI package builds and its XML parses, the CDC and catalog bodies render, the seed
generator runs. Run it after any edit and before sharing.

  python verify/offline_check.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ["infra/seed.py", "--customers", "50", "--out", "state/rendered/seed_sample.sql"],
    ["infra/traffic.py", "--dry-run", "--count", "3", "--seed", "1", "--interval", "0"],
    ["infra/bq_setup.py", "--offline"],
    ["idmc/00_resolve.py", "--offline"],
    ["idmc/01_connections.py", "plan", "--offline"],
    ["idmc/02_cdc.py", "render", "--offline"],
    ["idmc/03_mappings.py", "build", "--offline"],
    ["idmc/04_taskflows.py", "plan"],
    ["idmc/05_cai.py", "build", "--offline"],
    ["idmc/06_dq.py", "plan"],
    ["idmc/07_catalog.py", "render", "--offline"],
    ["verify/e2e_check.py"],
    ["teardown/teardown.py", "plan"],
]


def main():
    import argparse
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    (ROOT / "state" / "rendered").mkdir(parents=True, exist_ok=True)
    bad = 0
    for s in STEPS:
        r = subprocess.run([sys.executable, str(ROOT / s[0])] + s[1:], cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or [""])[-1][:110]
        print(f"{'OK  ' if r.returncode == 0 else 'FAIL'} {' '.join(s)[:60]:60} {tail}")
        if r.returncode:
            bad += 1
            print("     " + (r.stderr or r.stdout)[-600:].replace("\n", "\n     "))
    print(f"\n{len(STEPS) - bad}/{len(STEPS)} offline steps passed")
    print("note: state/ now holds offline renders and placeholder packages; delete state/packages and state/rendered "
          "before sharing (teardown/teardown.py clean-local)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
