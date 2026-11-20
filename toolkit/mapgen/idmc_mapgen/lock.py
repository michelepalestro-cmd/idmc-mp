"""Shared-runtime guards for anything that runs on the real Secure Agent.

The agent host is shared with production pipelines and the org has a monthly job cap, so:
- ``live_lock(owner)``: only ONE live import/run sequence at a time across every process on this machine.
- ``record_job(...)``: every IDMC job (task run) is appended to a ledger, and ``jobs_used()`` counts them,
  so a test campaign can stop itself at its job budget.

Paths come from MAPGEN_STATE_DIR (default ~/.idmc_mapgen).
"""
import contextlib, json, os, time

STATE_DIR = os.path.expanduser(os.environ.get("MAPGEN_STATE_DIR", "~/.idmc_mapgen"))
LOCK = os.path.join(STATE_DIR, "live.lock")
LEDGER = os.path.join(STATE_DIR, "jobs.jsonl")
STALE_S = 45 * 60          # a lock older than this is considered abandoned


def _ensure():
    os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)


@contextlib.contextmanager
def live_lock(owner, wait_s=3600, poll_s=15):
    """Block until this process holds the live lock (or wait_s passes -> TimeoutError)."""
    _ensure()
    t0 = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"owner": owner, "pid": os.getpid(), "t": time.time()}).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                with open(LOCK) as f:
                    info = json.load(f)
                if time.time() - info.get("t", 0) > STALE_S:
                    os.remove(LOCK)
                    continue
            except (OSError, ValueError):
                pass
            if time.time() - t0 > wait_s:
                with open(LOCK) as f:
                    raise TimeoutError("live lock held by %s" % f.read())
            time.sleep(poll_s)
    try:
        yield
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


def record_job(owner, task_id, task_name, run_id=None, state=None, rows=None, note=""):
    _ensure()
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "owner": owner, "task_id": task_id,
                            "task": task_name, "run_id": run_id, "state": state, "rows": rows, "note": note}) + "\n")


def jobs_used(since=None):
    """Number of jobs recorded (optionally since an ISO timestamp)."""
    if not os.path.exists(LEDGER):
        return 0
    n = 0
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if since is None or r.get("t", "") >= since:
                n += 1
    return n
