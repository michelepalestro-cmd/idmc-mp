#!/usr/bin/env python3
"""run_tests.py - offline tests for the idmc-mp plugin: structure, links, lessons, code, and every user story.

    python3 toolkit/tests/run_tests.py            # all tests; exit 1 on any failure
    python3 toolkit/tests/run_tests.py -k US-06   # only tests whose name contains the text
    python3 toolkit/tests/run_tests.py --list     # list the tests

Stdlib only. No IDMC login and no network: the live half of each story is the checklist in toolkit/tests/USER_STORIES.md.
Run from anywhere; it works on the plugin root (two folders above toolkit/tests/).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # toolkit/tests -> plugin root
PY = sys.executable
sys.dont_write_bytecode = True                 # the in-process tests import toolkit modules: leave no __pycache__
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
TESTS = []
SKILLS = ["idmc-mp", "idmc-secure-agent", "idmc-connections", "idmc-cdi", "idmc-cdc", "idmc-cai", "idmc-data-quality",
          "idmc-governance", "idmc-mdm", "idmc-claire-mcp", "idmc-deploy", "idmc-ipu"]
COMMANDS = ["connect", "health-check", "new-pipeline", "fix-error", "save-lesson", "tune-agent", "optimize",
            "promote", "add-dq", "catalog", "ipu-report", "clean-data", "connect-mcp"]
DOMAINS = {"auth", "agent", "connections", "cdi", "dbmi-cdc", "cai", "dq-profiling", "cdgc", "mdm", "claire-mcp",
           "migration", "org-cleanup", "ipu-licensing", "environment-ops", "claude-method", "ui-automation"}
LESSON_KEYS = {"id", "domain", "kind", "title", "text", "evidence", "status", "date", "supersedes_id"}


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def p(*parts):
    return os.path.join(ROOT, *parts)


def read(*parts):
    with open(p(*parts), encoding="utf-8") as f:
        return f.read()


# every child process gets a dead proxy, so a test that tried to reach IDMC (or anything) fails instead of connecting
NO_NET = {k: "http://127.0.0.1:9" for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY",
                                              "all_proxy")}
CRED_VARS = ("IDMC_CREDS_FILE", "IDMC_USER", "IDMC_PASS", "IDMC_LOGIN_HOST", "IDMC_LOGIN_URL", "IDMC_PROFILE",
             "MAPGEN_ENV_FILE", "MAPGEN_PROFILE", "MAPGEN_STATE_DIR", "NO_PROXY", "no_proxy")


def no_plugin_login_file():
    """login_file() falls back to a repo-root (or toolkit/) IDMC_LOGIN.txt: with one present a test could log in."""
    for f in (p("IDMC_LOGIN.txt"), p("toolkit", "IDMC_LOGIN.txt")):
        assert not os.path.exists(f), "move %s to ~/.idmc_toolkit/ before running the tests (it would be used)" % f


def run(args, cwd=ROOT, home=None):
    env = dict(ENV, **NO_NET)
    if home:
        no_plugin_login_file()
        env["HOME"] = home
        env["USERPROFILE"] = home
        for k in CRED_VARS:
            env.pop(k, None)
        env["IDMC_CACHE_DIR"] = os.path.join(home, ".idmc_session")
        env["MAPGEN_STATE_DIR"] = os.path.join(home, ".idmc_mapgen")
    r = subprocess.run([PY] + args, cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "no YAML front matter"
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def plugin_paths(text):
    """Every ${CLAUDE_PLUGIN_ROOT}/... path and every backticked knowledge/ knowledge/lessons/ toolkit/ path."""
    found = set()
    for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"']+)", text):
        found.add(m.group(1))
    for m in re.finditer(r"`((?:knowledge|lessons|toolkit|skills|commands|tests)/[^`]*)`", text):
        found.add(m.group(1).split(" ")[0])
    out = set()
    for f in found:
        f = f.rstrip(".,;:)")
        if "<" in f or "*" in f:
            continue
        out.add(f)
    return out


def lessons():
    rows = []
    with open(p("knowledge", "lessons", "lessons.jsonl"), encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                rows.append((n, json.loads(line)))
    return rows


# ---------------------------------------------------------------- structure
@test("plugin: the repo offers exactly one plugin, and its manifests agree")
def _():
    mk = json.loads(read(".claude-plugin", "marketplace.json"))
    pl = json.loads(read(".claude-plugin", "plugin.json"))
    assert len(mk["plugins"]) == 1, "marketplace lists %d plugins" % len(mk["plugins"])
    entry = mk["plugins"][0]
    assert entry["name"] == pl["name"] == mk["name"] == "idmc-mp", "names differ"
    assert entry["source"] == "./", "plugin source is not the repo root"
    assert entry["version"] == pl["version"] == mk["metadata"]["version"], "versions differ"
    others = [d for d, _, fs in os.walk(ROOT) if "plugin.json" in fs and ".git" not in d]
    assert others == [p(".claude-plugin")], "extra plugin.json files: %s" % others


@test("skills: every skill folder has a valid SKILL.md and the router names every area skill")
def _():
    have = sorted(d for d in os.listdir(p("skills")) if os.path.isdir(p("skills", d)))
    assert have == sorted(SKILLS), "skills on disk %s != expected %s" % (have, SKILLS)
    router = read("skills", "idmc-mp", "SKILL.md")
    for s in SKILLS:
        fm = frontmatter(read("skills", s, "SKILL.md"))
        assert fm.get("name") == s, "%s: name is %r" % (s, fm.get("name"))
        d = fm.get("description", "")
        assert d.startswith("Use ") and 60 < len(d) <= 1024, "%s: description must start with 'Use' and be 60-1024 chars" % s
        if s != "idmc-mp":
            assert "`%s`" % s in router, "router does not route to %s" % s


@test("commands: every command has a description and only names files that exist")
def _():
    have = sorted(f[:-3] for f in os.listdir(p("commands")) if f.endswith(".md"))
    assert have == sorted(COMMANDS), "commands on disk %s != expected %s" % (have, COMMANDS)
    for c in COMMANDS:
        t = read("commands", c + ".md")
        assert frontmatter(t).get("description"), c + ": no description"
        assert "skill" in t, c + ": does not name a skill to use"


@test("paths: every plugin path named in skills, commands and README exists")
def _():
    bad = []
    files = [("README.md",), (".github", "CONTRIBUTING.md")] + [("skills", s, "SKILL.md") for s in SKILLS] + \
            [("commands", c + ".md") for c in COMMANDS]
    names = set()
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        names.update(fs)
    for f in files:
        text = read(*f)
        for rel in plugin_paths(text):
            if not os.path.exists(p(*rel.split("/"))):
                bad.append("%s -> %s" % ("/".join(f), rel))
        for m in re.finditer(r"`(\d\d-[\w.-]+\.md)`", text):   # a bare doc name, e.g. `02-...md`
            if m.group(1) not in names:
                bad.append("%s -> %s" % ("/".join(f), m.group(1)))
    assert not bad, "missing:\n    " + "\n    ".join(bad)


@test("links: every relative markdown link in the repo resolves")
def _():
    link = re.compile(r"\]\((<[^>\n]+>|(?:[^()\s]|\([^()\s]*\))+)\)")
    bad, n = [], 0
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in fs:
            if not f.endswith(".md"):
                continue
            path = os.path.join(d, f)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for m in link.finditer(text):
                t = m.group(1).strip("<>")
                if re.match(r"^[a-z]+:", t) or t.startswith("#"):
                    continue
                target = unquote(t.split("#")[0])
                if not target:
                    continue
                n += 1
                if not os.path.exists(os.path.normpath(os.path.join(d, target))):
                    bad.append("%s -> %s" % (os.path.relpath(path, ROOT), t))
    assert n > 1000, "only %d links found" % n
    assert not bad, "%d broken:\n    " % len(bad) + "\n    ".join(bad[:20])


@test("layout: no file or folder name with spaces or symbols outside the reference sources")
def _():
    bad = []
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        rel = os.path.relpath(d, ROOT)
        if rel.startswith(os.path.join("knowledge", "reference")) or rel.startswith(os.path.join("toolkit", "demos")):
            continue
        for x in dirs + fs:
            if re.search(r"[ &(),']", x):
                bad.append(os.path.join(rel, x))
    assert not bad, "rename: " + ", ".join(bad[:10])


# ---------------------------------------------------------------- lessons
@test("lessons: lessons.jsonl is valid, ids unique, domains and statuses known")
def _():
    rows = lessons()
    assert len(rows) > 1500, "only %d lessons" % len(rows)
    ids, errs = set(), []
    for n, r in rows:
        if set(r) != LESSON_KEYS:
            errs.append("line %d keys %s" % (n, sorted(set(r) ^ LESSON_KEYS)))
        if r["id"] in ids:
            errs.append("line %d duplicate id %s" % (n, r["id"]))
        ids.add(r["id"])
        if r["domain"] not in DOMAINS:
            errs.append("line %d unknown domain %s" % (n, r["domain"]))
        if r["status"] not in ("current", "superseded", "disputed"):
            errs.append("line %d status %s" % (n, r["status"]))
    for n, r in rows:
        refs = [x.strip() for x in r["supersedes_id"].split(",") if x.strip()]
        if ";" in r["supersedes_id"]:
            errs.append("line %d supersedes_id: separate ids with ', '" % n)
        for x in refs:
            if x not in ids:
                errs.append("line %d supersedes unknown %s" % (n, x))
    assert not errs, "\n    ".join(errs[:15])


@test("lessons: every area skill's domain has current lessons and a lessons file in its job folder")
def _():
    rows = [r for _, r in lessons() if r["status"] == "current"]
    for s in SKILLS[1:]:
        t = read("skills", s, "SKILL.md")
        doms = re.findall(r'"domain": "([a-z-]+)"', t)
        assert doms, s + ": names no lesson domain"
        for d in doms:
            assert d in DOMAINS, "%s: unknown domain %s" % (s, d)
            assert sum(1 for r in rows if r["domain"] == d) >= 10, "%s: fewer than 10 current %s lessons" % (s, d)
        md = re.search(r"(knowledge/[\w.-]+/lessons[\w.-]*\.md)", t)
        assert md and os.path.exists(p(*md.group(1).split("/"))), s + ": its lessons file is missing"


@test("lessons: the error-signature index is up to date")
def _():
    rc, out = run(["toolkit/tools/build_skill_field_lessons.py", "--check"])
    assert rc == 0, out.strip()


@test("lessons: the lesson counts in the docs match lessons.jsonl")
def _():
    rc, out = run(["toolkit/tools/sync_lesson_counts.py", "--check"])
    assert rc == 0, out.strip()[-800:]


# ---------------------------------------------------------------- code and safety
@test("code: every Python file compiles")
def _():
    bad = []
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in fs:
            if f.endswith(".py"):
                path = os.path.join(d, f)
                try:
                    with open(path, encoding="utf-8") as fh:
                        compile(fh.read(), path, "exec")
                except SyntaxError as e:
                    bad.append("%s: %s" % (os.path.relpath(path, ROOT), e))
    assert not bad, "\n    ".join(bad)


@test("code: every library script answers --help without a login")
def _():
    lib = p("toolkit", "lib")
    home = tempfile.mkdtemp()
    for f in sorted(os.listdir(lib)):
        if f.startswith("idmc_") and f.endswith(".py"):
            rc, out = run([os.path.join("toolkit", "lib", f), "--help"], home=home)
            assert rc == 0, "%s --help exit %d: %s" % (f, rc, out[-300:])


@test("safety: secret scan is clean and no login file is committed")
def _():
    rc, out = run(["toolkit/tools/secret_scan.py", "."])
    assert rc == 0, out[-800:]
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        assert "IDMC_LOGIN.txt" not in fs, "IDMC_LOGIN.txt inside the plugin: " + d


@test("safety: redact() masks secret-ish keys by substring and {key, value(s)} pairs")
def _():
    sys.path.insert(0, p("toolkit", "lib"))
    import idmc_http as H
    d = {"Client Secret": "s3", "secretKey": "s4", "apiKey": "k", "api-key": "k", "Private Key Password": "z",
         "passwd": "p", "pwd": "p", "IDS-SESSION-ID": "x", "session_id": "x", "Authorization": "Bearer y",
         "Cookie": "c", "sas_token": "t", "signature": "g", "credentials": "c", "jwt": "j",
         "host": "keep", "passthrough": "keep", "isAssigned": True, "name": "keep",
         "options": [{"key": "IICS Password", "values": ["hunter2"]}, {"key": "host", "values": ["h"]},
                     {"key": {"$t": "Secret Access Key"}, "value": "v"}]}
    r = H.redact(d)
    for k in d:
        if k in ("host", "passthrough", "isAssigned", "name", "options"):
            assert r[k] == d[k] or k == "options", "%s changed: %r" % (k, r[k])
        else:
            assert str(r[k]).startswith("<redacted:"), "%s not redacted: %r" % (k, r[k])
    assert r["options"][0]["values"] == ["<redacted:7>"], r["options"][0]
    assert r["options"][1]["values"] == ["h"], r["options"][1]
    assert r["options"][2]["value"] == "<redacted:1>", r["options"][2]
    assert "hunter2" not in json.dumps(r)


@test("safety: redirects only to https on the same host; mapgen sends credentials only to *.informaticacloud.com")
def _():
    sys.path.insert(0, p("toolkit", "lib"))
    sys.path.insert(0, p("toolkit", "mapgen"))
    import urllib.request
    import idmc_http as H
    from idmc_mapgen.client import Client, LoginError
    from idmc_mapgen.spec import SpecError, resolve_profile
    h = H.SafeRedirect()
    req = urllib.request.Request("https://usw5.dm-us.informaticacloud.com/saas/api/v2/org",
                                 headers={"icSessionId": "x"})
    for bad in ("https://evil.example.com/x", "http://usw5.dm-us.informaticacloud.com/x",
                "https://usw5.dm-us.informaticacloud.com:8443/x"):
        assert h.redirect_request(req, None, 302, "Found", {}, bad) is None, bad
    ok = h.redirect_request(req, None, 302, "Found", {}, "https://usw5.dm-us.informaticacloud.com/saas/y")
    assert ok is not None and ok.full_url.endswith("/saas/y")
    for url in ("http://dm-us.informaticacloud.com", "https://evil.example.com", "https://informaticacloud.com.evil.io",
                "https://u:p" + "@dm-us.informaticacloud.com", "https://dm-us.informaticacloud.com:8443"):
        try:
            Client.login_url(url)
            raise AssertionError("login URL accepted: " + url)
        except LoginError:
            pass
    assert Client.login_url("https://usw5.dm-us.informaticacloud.com/cloudUX/home") == "https://dm-us.informaticacloud.com"
    c = Client({"auth": {"loginUrl": "https://collector.example.com"}},
               env={"IDMC_USER": "u", "IDMC_PASS": "p", "MAPGEN_ENV_FILE": os.devnull})
    try:
        c.session()
        raise AssertionError("a non-IDMC loginUrl reached the login")
    except LoginError:
        pass
    try:
        resolve_profile({"profile": {"auth": {"loginUrl": "https://x.informaticacloud.com"}}})
        raise AssertionError("a spec's inline profile auth was accepted")
    except SpecError:
        pass


@test("safety: mapgen writes are dry runs unless --execute --expect-org; --dry-run still accepted")
def _():
    home = tempfile.mkdtemp()
    pkg = os.path.join(home, "x.pkg.zip")
    import zipfile
    with zipfile.ZipFile(pkg, "w") as z:
        z.writestr("exportMetadata.v2.json", "{}")
    prof = os.path.join(home, "profile.json")
    with open(prof, "w", encoding="utf-8") as f:
        f.write("{}")
    mg = os.path.join("toolkit", "mapgen", "mapgen.py")
    for extra in ([], ["--dry-run"], ["--dry-run", "--execute"]):
        rc, out = run([mg, "--profile", prof, "import", pkg] + extra, home=home)
        assert rc == 0 and "dry run: would import" in out, out[-400:]
    rc, out = run([mg, "--profile", prof, "import", pkg, "--execute"], home=home)
    assert rc == 2 and "--expect-org" in out, out[-400:]
    for cmd in (["task", "m_x"], ["run", "mt_x"], ["deploy", "spec.json"]):
        rc, out = run([mg, "--profile", prof] + cmd + ["--execute"], home=home)
        assert rc == 2 and "--expect-org" in out, " ".join(cmd) + ": " + out[-400:]


# ---------------------------------------------------------------- user stories (offline half)
@test("US-01 install: one plugin, one marketplace, installs as idmc-mp@idmc-mp")
def _():
    readme = read("README.md")
    assert "/plugin marketplace add michelepalestro-cmd/idmc-mp-informatica-claude-plugin" in readme
    assert "/plugin install idmc-mp@idmc-mp" in readme


@test("US-02 connect: first run creates the login file in HOME (mode 600), never in the plugin, no login attempt")
def _():
    home = tempfile.mkdtemp()
    rc, out = run(["toolkit/check_login.py"], home=home)
    f = os.path.join(home, ".idmc_toolkit", "IDMC_LOGIN.txt")
    assert os.path.isfile(f), "login file not created: " + out[-300:]
    assert oct(os.stat(f).st_mode & 0o777) == "0o600", "mode is " + oct(os.stat(f).st_mode & 0o777)
    assert "Fill in" in out, out[-300:]
    assert not os.path.exists(p("toolkit", "IDMC_LOGIN.txt"))
    rc2, out2 = run(["toolkit/setup/check_setup.py"], home=home)
    assert f in out2, "check_setup does not point at the home login file"


@test("US-02b connect: example or empty login values never reach IDMC; --where and --setup without a terminal are safe")
def _():
    home = tempfile.mkdtemp()
    d = os.path.join(home, ".idmc_toolkit")
    os.makedirs(d)
    f = os.path.join(d, "IDMC_LOGIN.txt")
    cases = [("", "", ""),
             ("jane.doe@example.com", "changeme", "https://usw5.dm-us.informaticacloud.com/cloudUX/home"),
             ("svc_user", "a-real-looking-pass", "https://www.google.com/")]
    for user, pw, host in cases:
        with open(f, "w", encoding="utf-8") as out:
            out.write("IDMC_USER=%s\nIDMC_PASS=%s\nIDMC_LOGIN_HOST=%s\n" % (user, pw, host))
        rc, out = run(["toolkit/check_login.py"], home=home)
        assert rc == 2 and "No login was tried" in out and "Logging in" not in out, out[-400:]
    rc, out = run(["toolkit/check_login.py", "--where"], home=home)
    assert rc == 0 and f in out, out[-300:]
    rc, out = run(["toolkit/check_login.py", "--setup"], home=home)
    assert rc == 2 and "needs a terminal" in out, out[-300:]


@test("US-03 health-check: read-only command, uses the session tool and the lessons")
def _():
    t = read("commands", "health-check.md")
    assert "Read-only" in t and "idmc_session.py" in t and "lessons.jsonl" in t


@test("US-04 fix-error: every error the skill promises to handle has a current lesson")
def _():
    current = [r for _, r in lessons() if r["status"] == "current"]
    blob = [(r["title"] + " " + r["text"]) for r in current]
    for sig in ["APP_10519", "APP_105060", "readyToRun", "401", "403", "404", "405", "500", "zero-byte"]:
        hits = sum(1 for b in blob if sig.lower() in b.lower())
        assert hits >= 1, "no current lesson for " + sig


@test("US-05 save-lesson: the command writes the lessons.jsonl shape outside the plugin")
def _():
    t = read("commands", "save-lesson.md")
    for k in LESSON_KEYS:
        assert "`%s`" % k in t, "save-lesson does not name field " + k
    assert "~/.idmc_toolkit/lessons-local.jsonl" in t and "Never write into the plugin folder" in t


@test("US-06 new pipeline: the generator compiles real mappings offline (retail demo, 13 steps)")
def _():
    demo = p("toolkit", "demos", "retail_data_foundation")
    try:
        rc, out = run(["verify/offline_check.py"], cwd=demo, home=tempfile.mkdtemp())
        assert rc == 0 and "13/13 offline steps passed" in out, out[-600:]
    finally:
        run(["teardown/teardown.py", "clean-local"], cwd=demo)


@test("US-07 to US-16: each co-pilot area has a skill, a starting doc and a tool")
def _():
    for s in SKILLS[1:]:
        t = read("skills", s, "SKILL.md")
        assert "## How to work" in t and "## Read" in t and "## Tools" in t, s + ": missing a section"
        assert re.search(r"`knowledge/[^`]+\.md`", t), s + ": no starting doc"
        assert re.search(r"`toolkit/[^`]+\.py`", t), s + ": no tool"


@test("US-17 demos: the bid-desk blueprint verifies offline")
def _():
    rc, out = run(["verify/bid_verify.py", "offline"], cwd=p("toolkit", "demos", "bid_desk_document_parsing"),
                  home=tempfile.mkdtemp())
    assert rc == 0 and "ALL CHECKS PASSED" in out, out[-600:]


@test("US-20 customer CSV: messy CSV -> cleaned, mastered customers with ids, as a real IDMC mapping (offline)")
def _():
    rc, out = run(["check.py"], cwd=p("toolkit", "demos", "customer_master_csv"), home=tempfile.mkdtemp())
    assert rc == 0 and "ALL CHECKS PASSED" in out, out[-800:]
    q = json.loads(re.search(r"match quality: (\{.*\})", out).group(1))
    assert q["precision"] == 1.0 and q["recall"] >= 0.95, q


@test("US-18 updates keep user data: nothing tells Claude to write inside the plugin")
def _():
    for s in SKILLS:
        t = read("skills", s, "SKILL.md")
        assert "~/.idmc_toolkit" in t, s + ": does not send user data to ~/.idmc_toolkit"


# ---- the MCP bridge: Informatica's managed MCP servers as Claude Code tools (against a local stand-in, no network) ----
def _bridge(env_path, msgs):
    """Run the bridge over stdio with these JSON-RPC messages; return ({id: response}, stderr)."""
    env = dict(ENV, **NO_NET)
    env.update(NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost", IDMC_MCP_ENV_FILE=env_path)
    lines = "".join(json.dumps(m) + "\n" for m in msgs)
    r = subprocess.run([PY, p("toolkit", "lib", "idmc_mcp_bridge.py")], input=lines, env=env, capture_output=True,
                       text=True, timeout=120)
    out = {}
    for ln in r.stdout.splitlines():
        j = json.loads(ln)
        out[j.get("id")] = j
    return out, r.stderr + r.stdout


INIT = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {},
         "clientInfo": {"name": "test", "version": "1"}}}, {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]


def _call(i, name, args=None):
    return {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args or {}}}


def _mock():
    sys.path.insert(0, p("toolkit", "tests"))
    import mock_idmc_mcp
    return mock_idmc_mcp


@test("MCP bridge: the plugin starts it, and with no client file it offers only the status tool")
def _():
    man = json.loads(read(".claude-plugin", "plugin.json"))
    srv = man["mcpServers"]["idmc"]
    assert srv["args"] == ["${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_mcp_bridge.py"], srv
    out, log = _bridge(os.path.join(tempfile.mkdtemp(), "none.env"), INIT + [_call(3, "idmc_mcp_status")])
    assert out[1]["result"]["serverInfo"]["name"] == "idmc-mp", out[1]
    assert [t["name"] for t in out[2]["result"]["tools"]] == ["idmc_mcp_status"], out[2]
    assert "/idmc-mp:connect-mcp" in out[3]["result"]["content"][0]["text"], out[3]


@test("MCP bridge: read-only by default, forwards calls, renews an expired token, never prints the secret")
def _():
    m = _mock()
    srv, base, state = m.start()
    try:
        d = tempfile.mkdtemp()
        envf = os.path.join(d, "client.env")
        m.write_env(envf, base, list(m.TOOLS))
        out, log = _bridge(envf, INIT + [_call(3, "addr_verify_address", {"address": "1 Main St"}),
                                         _call(4, "conn_list_connections"), _call(5, "jobs_run_mapping_task"),
                                         _call(6, "idmc_mcp_status")])
    finally:
        srv.shutdown()
    names = [t["name"] for t in out[2]["result"]["tools"]]
    assert "addr_verify_address" in names and "jobs_get_job_status" in names, names
    assert not any(n.endswith(("run_mapping_task", "delete_connection")) for n in names), names
    assert all(len(n) <= 38 for n in names), [n for n in names if len(n) > 38]
    assert out[3]["result"]["structuredContent"]["status"] == "VERIFIED", out[3]
    assert out[4]["result"]["structuredContent"]["server"] == "connectionmanagement", out[4]      # an SSE answer
    assert out[5]["result"]["isError"], out[5]
    assert ("jobmanagement", "run_mapping_task", {}) not in state.calls, state.calls
    assert state.issued >= 2, "the first token was expired: the bridge must fetch a new one after the 401"
    assert "read-only" in out[6]["result"]["content"][0]["text"], out[6]
    assert m.CLIENT_SECRET not in log, "the client secret was printed"


@test("MCP bridge: writes appear only when the client file allows them, marked as writes")
def _():
    m = _mock()
    srv, base, state = m.start()
    try:
        envf = os.path.join(tempfile.mkdtemp(), "client.env")
        m.write_env(envf, base, ["jobmanagement"], allow_writes=True)
        out, _ = _bridge(envf, INIT)
    finally:
        srv.shutdown()
    tools = {t["name"]: t for t in out[2]["result"]["tools"]}
    assert "jobs_run_mapping_task" in tools, list(tools)
    assert tools["jobs_run_mapping_task"]["description"].startswith("WRITES to IDMC"), tools["jobs_run_mapping_task"]
    assert tools["jobs_run_mapping_task"]["annotations"]["readOnlyHint"] is False


@test("MCP bridge: refuses a client file others can read, inside the plugin, or pointing at a non-https host")
def _():
    m = _mock()
    d = tempfile.mkdtemp()
    envf = os.path.join(d, "client.env")
    m.write_env(envf, "http://example.com", ["jobmanagement"])
    out, _ = _bridge(envf, INIT + [_call(3, "idmc_mcp_status")])
    assert "https" in out[3]["result"]["content"][0]["text"], out[3]
    if os.name == "posix":
        m.write_env(envf, "http://127.0.0.1:9", ["jobmanagement"])
        os.chmod(envf, 0o644)
        out, _ = _bridge(envf, INIT + [_call(3, "idmc_mcp_status")])
        assert "chmod 600" in out[3]["result"]["content"][0]["text"], out[3]
    inside = p("toolkit", "tests", "client-test.env")
    try:
        m.write_env(inside, "http://127.0.0.1:9", ["jobmanagement"])
        out, _ = _bridge(inside, INIT + [_call(3, "idmc_mcp_status")])
        assert "outside the plugin" in out[3]["result"]["content"][0]["text"], out[3]
    finally:
        os.remove(inside)


def main():
    args = sys.argv[1:]
    if "--list" in args:
        for n, _ in TESTS:
            print(n)
        return 0
    k = args[args.index("-k") + 1] if "-k" in args else None
    fails = 0
    for n, fn in TESTS:
        if k and k not in n:
            continue
        try:
            fn()
            print("PASS  " + n)
        except AssertionError as e:
            fails += 1
            print("FAIL  " + n + "\n    " + str(e))
        except Exception as e:  # noqa: BLE001
            fails += 1
            print("ERROR " + n + "\n    %s: %s" % (type(e).__name__, e))
    print("\n%s: %d failed" % ("FAILED" if fails else "ALL PASSED", fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
