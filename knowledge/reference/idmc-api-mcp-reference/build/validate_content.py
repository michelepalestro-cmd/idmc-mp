#!/usr/bin/env python3
"""
validate_content.py -- run this BEFORE build_master.py, and before you hand back
a section you edited.

    python build/validate_content.py            # check everything
    python build/validate_content.py 12-cdi     # check one section

Exit code 0 = clean, 1 = errors found. Warnings do not fail the run.

What it enforces:
  * valid JSON, required keys present
  * every table row has exactly as many cells as its header
  * status/verb cells use the agreed vocabulary (typos are the #1 real defect)
  * last_verified is a real ISO date and not in the future
  * no duplicate endpoint+section rows (the #1 merge artefact)
  * flags rows whose evidence column is empty -- an unsourced claim
"""
import glob
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(ROOT, "content")

REQUIRED = ["id", "title", "blocks"]
BLOCK_TYPES = {"table", "paras", "bullets", "callout", "code"}

STATUS_VOCAB = {
    # legacy capability words -- still valid in the cross-cutting sections
    "WRITE", "RUN", "READ", "UI-ONLY", "GAP", "DOC",
    "YES", "NO", "UI", "PARTIAL", "DISPUTED", "CONTESTED",
    "REAL", "BLOCKED", "EMPTY-200",
    "--", "-", "",
}
STATUS_HEADERS = {"status", "get", "post", "put", "patch", "delete",
                  "rest api", "mcp", "same?", "headless?", "over rest", "over mcp"}

# In the service tables the verb column LISTS verbs, so it is validated differently:
# every token must be a real HTTP verb or one of the agreed qualifiers.
VERB_COL_HEADERS = {"verb", "verbs supported", "verbs proven", "verbs"}
HTTP_VERBS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
VERB_QUALIFIERS = {"none proven", "ui only", "documented, unproven", "all five verbs untested"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

errors = []
warnings = []


def err(f, msg):
    errors.append("[ERROR] %s: %s" % (f, msg))


def warn(f, msg):
    warnings.append("[warn ] %s: %s" % (f, msg))


def check_file(path):
    fn = os.path.basename(path)
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        err(fn, "invalid JSON -- %s" % e)
        return

    for k in REQUIRED:
        if k not in d:
            err(fn, "missing required key '%s'" % k)
    if "id" in d and d["id"] != fn[:-5]:
        err(fn, "id '%s' does not match filename" % d["id"])

    lv = d.get("last_verified")
    if lv:
        if not DATE_RE.match(str(lv)):
            err(fn, "last_verified '%s' is not YYYY-MM-DD" % lv)
        else:
            y, m, dd = (int(x) for x in str(lv).split("-"))
            try:
                if date(y, m, dd) > date.today():
                    err(fn, "last_verified '%s' is in the future" % lv)
            except ValueError:
                err(fn, "last_verified '%s' is not a real date" % lv)

    if not d.get("owner"):
        warn(fn, "no owner set -- set 'owner' when you claim this section")

    seen = set()
    for bi, b in enumerate(d.get("blocks", [])):
        tag = "block %d" % bi
        bt = b.get("type", "paras")
        if bt not in BLOCK_TYPES:
            err(fn, "%s has unknown type '%s' (allowed: %s)"
                % (tag, bt, ", ".join(sorted(BLOCK_TYPES))))
            continue
        if bt != "table":
            continue
        hdr = b.get("header")
        if not isinstance(hdr, list) or not hdr:
            err(fn, "%s is a table with no header list" % tag)
            continue
        ncol = len(hdr)
        lower = [str(h).strip().lower() for h in hdr]
        rows_ = [r for r in b.get("rows", []) if isinstance(r, list)]

        def is_status_col(i):
            """A column is status-vocabulary-checked only if its header LOOKS like a
            status column AND its values actually behave like tokens. Otherwise it is
            a prose column that merely shares a header word, and forcing the vocabulary
            on it produces false failures."""
            if lower[i] not in STATUS_HEADERS:
                return False
            vals = [str(r[i]).strip() for r in rows_ if i < len(r) and str(r[i]).strip()]
            if not vals:
                return False
            ok = sum(1 for v in vals
                     if v in STATUS_VOCAB or re.match(r"^\d{3}(\s*/\s*\d{3})*$", v))
            return ok >= len(vals) * 0.5

        status_cols = [i for i in range(ncol) if is_status_col(i)]
        verb_cols = [i for i, h in enumerate(lower) if h in VERB_COL_HEADERS]
        ev_cols = [i for i, h in enumerate(lower)
                   if "evidence" in h or h in ("source", "notes / evidence")]

        for ri, row in enumerate(b.get("rows", [])):
            where = "%s row %d" % (tag, ri + 1)
            if not isinstance(row, list):
                err(fn, "%s is not a list" % where)
                continue
            if len(row) != ncol:
                err(fn, "%s has %d cells, header has %d" % (where, len(row), ncol))
                continue
            for ci in status_cols:
                v = str(row[ci]).strip()
                if v in STATUS_VOCAB:
                    continue
                if v.isdigit() and len(v) == 3:
                    continue          # a bare HTTP code is legal
                if re.match(r"^\d{3}(\s*/\s*\d{3})*$", v):
                    continue          # "404 / 405"
                parts = [x.strip() for x in v.split("/")]
                if len(parts) > 1 and all(p in STATUS_VOCAB for p in parts):
                    continue          # compound, e.g. "READ / WRITE"
                err(fn, "%s col '%s' has '%s' -- not in the status vocabulary"
                    % (where, hdr[ci], v))
            # Verb-list columns: every listed token must be a real HTTP verb.
            for ci in verb_cols:
                raw = str(row[ci]).strip()
                if not raw or raw in ("--", "-"):
                    continue
                for chunk in re.split(r"[·,;]", raw):
                    tok = chunk.strip()
                    if not tok:
                        continue
                    low = tok.lower()
                    if low in VERB_QUALIFIERS:
                        continue
                    base = re.sub(r"\[.*?\]|\(.*?\)", "", tok).strip()
                    if base.upper() in HTTP_VERBS:
                        continue
                    if all(p.strip().upper() in HTTP_VERBS
                           for p in base.split("/") if p.strip()):
                        continue
                    if re.match(r"^(GET|POST|PUT|PATCH|DELETE)\s+\d{3}$", base.upper()):
                        continue
                    err(fn, "%s verb column has '%s' -- not an HTTP verb or an agreed qualifier"
                        % (where, tok))

            # Duplicate detection uses the first TWO columns, because many tables
            # legitimately repeat a grouping value (service name) in column 0.
            key = (str(row[0]).strip().lower(),
                   str(row[1]).strip().lower() if ncol > 1 else "",
                   b.get("title", ""))
            if key[0] and key in seen:
                warn(fn, "%s duplicates '%s' + '%s' within the same table"
                     % (where, row[0], row[1] if ncol > 1 else ""))
            seen.add(key)
            for ci in ev_cols:
                if not str(row[ci]).strip():
                    warn(fn, "%s has an empty evidence cell -- unsourced claim" % where)


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    files = sorted(glob.glob(os.path.join(CONTENT, "*.json")))
    if only:
        files = [f for f in files
                 if any(o in os.path.basename(f) for o in only)]
        if not files:
            print("no content files matched", only)
            return 1
    for f in files:
        check_file(f)

    for w in warnings:
        print(w)
    for e in errors:
        print(e)
    print("\nchecked %d section file(s): %d error(s), %d warning(s)"
          % (len(files), len(errors), len(warnings)))
    if errors:
        print("FAILED -- fix the errors above before building.")
        return 1
    print("OK -- safe to run build/build_master.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
