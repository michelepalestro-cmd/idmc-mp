#!/usr/bin/env python3
"""teardown.py - undo the build in reverse order. Every IDMC step is a dry run until --execute --expect-org <orgIdV3>.

  python teardown/teardown.py plan                       print every step below (no call)
  python teardown/teardown.py export --execute ...       1 back up the project (v3 export with dependencies) to state/
  python teardown/teardown.py schedule --execute ...     2 unbind the nightly schedule from the taskflow
  python teardown/teardown.py cai --execute ...          3 stop the listeners, then unpublish every CAI asset (reverse order)
  python teardown/teardown.py delete --execute ...       4 delete the project content (core idmc_frs_delete.py, leaf first)
  python teardown/teardown.py infra [--volumes]          5 docker compose down (add --volumes to drop the data too)

Steps 1-4 call the core scripts (export, taskflow/schedule, publish, FRS delete) or the blueprint's own deploy_cai.py /
listener_ctl.py. The CDI connections and tasks are removed by step 4 with the project (they live in its folder only if
you moved them there; otherwise delete them with core idmc_frs_delete.py v2-delete, see BUILD.md "Undo").
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import mbr_config as CFG  # noqa: E402

CORE = CFG.use_core()
BP = CFG.BP
PY = sys.executable


def run(cmd, really=True):
    print("  $", " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], check=False).returncode if really else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("step", choices=["plan", "export", "schedule", "cai", "delete", "infra"])
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--expect-org")
    ap.add_argument("--volumes", action="store_true")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = CFG.load(a.config, example_ok=(a.step == "plan"))
    gate = ["--execute", "--expect-org", a.expect_org] if a.execute else []
    if a.execute and not a.expect_org:
        sys.exit("--execute needs --expect-org <orgIdV3>")
    ids = CFG.state_get("ids.json", {})
    pid = ids.get("project_id", "<project id from state/ids.json>")
    steps = {
        "export": [[PY, CORE / "idmc_export_import.py", "export", "--id", pid, "--out", CFG.STATE / "mbr_backup_before_teardown.zip"]],
        "schedule": [[PY, CORE / "idmc_taskflow_schedule.py", "unbind", ids.get("taskflow_id", "<taskflow id>"), *gate]],
        "cai": [[PY, BP / "idmc" / "listener_ctl.py", "stop", "mbr-kafka:item-sub", "mbr-kafka:po-sub", "mbr-kafka:perf-sub",
                 "mbr-kafka-store:store-price-sub", "mbr-jms:items-legacy", "mbr-jms:pos-legacy", *gate],
                [PY, BP / "idmc" / "deploy_cai.py", "unpublish", *gate]],
        "delete": [[PY, CORE / "idmc_frs_delete.py", "deps", pid],
                   [PY, CORE / "idmc_frs_delete.py", "delete", "--ids-file", CFG.STATE / "delete_ids.txt", *gate]],
        "infra": [["docker", "compose", "-f", BP / "infra" / "docker-compose.yml", "down", *(["--volumes"] if a.volumes else [])]],
    }
    if a.step == "plan":
        for name in ("export", "schedule", "cai", "delete", "infra"):
            print(f"[{name}]")
            for c in steps[name]:
                run(c, really=False)
        print("delete_ids.txt: one v3 id per line (the project id from state/ids.json deletes its folders and assets "
              "leaf first); the core script refuses published CAI assets (FRS_082): unpublish first.")
        return
    if a.step == "delete" and not (CFG.STATE / "delete_ids.txt").exists():
        sys.exit("write state/delete_ids.txt first (the project id is enough; see `teardown.py plan`)")
    for c in steps[a.step]:
        run(c)


if __name__ == "__main__":
    main()
