#!/usr/bin/env python3
"""secret_scan.py - run before you share or commit the informatica-idmc-headless plugin: fails on anything that looks like a
credential, an org-specific id you added, or a local path.

    python3 toolkit/tools/secret_scan.py                  # scans the repository root
    python3 toolkit/tools/secret_scan.py <folder> --explain
    python3 toolkit/tools/secret_scan.py --files a b ...  # only these files (the pre-commit hook: the staged files)

A filled-in IDMC_LOGIN.txt always fails the scan: empty its IDMC_USER / IDMC_PASS lines before you share.
Add your own org's ids, hosts and names to toolkit/tools/secret_scan_extra.txt (one regex per line; that file is
itself skipped by the scan) so they are caught too. A hit is printed as rule, file:line and a masked preview (the
first 3 characters + ***), never the matched value itself, so CI logs and scrollback do not repeat a secret.
"""
import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent              # toolkit/tools
ROOT = HERE.parents[1]                               # the repository root
RULES = [
    ("private-key", r"BEGIN\s+(?:RSA|OPENSSH|EC|DSA)?\s*PRIVATE KEY-----\s*[A-Za-z0-9+/]{20,}"),
    ("gcp-sa-key", r"\"private_key_id\"\s*:\s*\"[a-f0-9]{20,}"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),
    ("token", r"glpat-[A-Za-z0-9_.-]{10,}|xox[bpa]-[A-Za-z0-9-]{10,}|gh[opusr]_[A-Za-z0-9]{30,}|sk_live_[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}"),
    ("payment-key", r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,}|\bwhsec_[A-Za-z0-9]{8,}|\bacct_[A-Za-z0-9]{12,}"),
    ("assigned-secret", r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|client[_-]?secret)[\"']?\s*[:=]\s*[\"']?(?!<|\$|\.\.\.|\{|changeme|CHANGE_ME|example)[^\"'\s<>]{8,}"),
    ("sas-or-sig", r"(?i)[?&]sig=[A-Za-z0-9%+/=]{20,}"),
    ("ipv4", r"\b(?!0\.0\.0\.0\b)(?!127\.)(?!10\.)(?!192\.168\.)(?!172\.(?:1[6-9]|2\d|3[01])\.)(?:\d{1,3}\.){3}\d{1,3}\b"),
    ("local-path", r"(?i)[A-Z]:\\+Users\\+[^\\\s]+|/c/Use[r]s/[^/\s]+|/home/(?!infa/|user/|<)[a-z][a-z0-9_-]+/"),
    ("email", r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]
TEXT = {".md", ".txt", ".json", ".csv", ".yml", ".yaml", ".py", ".sh", ".sql", ".xml", ".js", ".ps1", ".ini",
        ".cfg", ".toml", ".bat", ".cmd", ".env", ".example", ".html", ".twb", ".tds", ".jsonl"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "_source"}
SKIP_FILES = {"secret_scan.py", "secret_scan_extra.txt"}
PROSE_VALUE = re.compile(r"[:=]\s*[\"']?[a-z][a-z-]*[a-z][.,;:)]*$")  # "password: rotation" is prose, not a value
ALLOW_EMAIL_DOMAINS = re.compile(r"@(?:informatica\.com|salesforce\.com|apache\.org|python\.org)$", re.I)
MAINTAINER_EMAILS = set()   # published contact addresses allowed by the scan (none)


def mask(text):
    return text[:3] + "***"


def scan_file(p, shown, rules, explain):
    """Hits in one file; prints each as rule, path:line and a masked preview."""
    hits = 0
    f = p.name
    if f == "IDMC_LOGIN.txt":
        filled = [ln.split("=", 1)[0].strip() for ln in p.read_text(encoding="utf-8-sig").splitlines()
                  if re.match(r"\s*IDMC_(?:USER|PASS)\s*=\s*\S", ln)]
        if filled:
            print(f"filled-in-login  {shown}  {', '.join(filled)} set: empty them before sharing")
            return 1
        return 0
    if f in SKIP_FILES or (p.suffix.lower() not in TEXT and not f.startswith(".env")):
        return 0
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for label, pat in rules:
            for m in re.finditer(pat, line):
                if label == "email" and (ALLOW_EMAIL_DOMAINS.search(m.group(0)) or m.group(0).lower() in MAINTAINER_EMAILS):
                    continue
                if label == "assigned-secret" and PROSE_VALUE.search(m.group(0)):
                    continue
                hits += 1
                if explain or hits <= 40:
                    print(f"{label:15s} {shown}:{i}  {mask(m.group(0))}")
    return hits


def git_files(root):
    """Files git would commit under root (tracked and untracked, minus ignored), or None outside a git work tree."""
    import subprocess
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return [x for x in r.stdout.split("\0") if x]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=str(ROOT))
    ap.add_argument("--files", nargs="+", metavar="FILE", help="scan only these files (paths as given)")
    ap.add_argument("--explain", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="scan every file under root, including git-ignored ones (use before zipping a folder to share)")
    a = ap.parse_args()
    rules = list(RULES)
    extra = HERE / "secret_scan_extra.txt"
    if extra.is_file():
        rules += [("custom", ln.strip()) for ln in extra.read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.startswith("#")]
    hits = 0
    if a.files:
        for name in a.files:
            p = Path(name)
            if p.is_file():
                hits += scan_file(p, name, rules, a.explain)
    elif not a.all and git_files(a.root) is not None:
        for rel in git_files(a.root):            # what git would commit: tracked + untracked, minus .gitignore
            p = Path(a.root) / rel
            if p.is_file() and not any(part in SKIP_DIRS for part in Path(rel).parts):
                hits += scan_file(p, Path(rel), rules, a.explain)
    else:
        for dp, dn, fn in os.walk(a.root):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                p = Path(dp) / f
                hits += scan_file(p, p.relative_to(a.root), rules, a.explain)
    print("CLEAN" if not hits else f"{hits} hit(s): fix them before sharing")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
