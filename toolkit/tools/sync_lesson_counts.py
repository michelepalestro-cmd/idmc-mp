#!/usr/bin/env python3
"""sync_lesson_counts.py - rebuild every lesson count from knowledge/lessons/lessons.jsonl, so the numbers never drift.

    python3 toolkit/tools/sync_lesson_counts.py           # rewrite the counts in place
    python3 toolkit/tools/sync_lesson_counts.py --check   # exit 1 (and list the files) if any count is stale

Rewrites: the summary line of each job folder's lessons file (knowledge/<job>/lessons*.md), the summary, the files
table, the kinds table and the id-prefix table of knowledge/lessons/README.md, and the lesson total in the root README.md.
lessons.jsonl is the source of truth; each lessons file is matched to its lessons by the `### L-...` headings it holds. Standard library only, offline.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LESSONS = ROOT / "knowledge" / "lessons"
KNOWLEDGE = ROOT / "knowledge"


def lesson_files():
    return sorted(KNOWLEDGE.glob("*/lessons*.md"))
KIND_MEANING = {
    "GOTCHA": "a trap: something that looks like one thing and is another",
    "RECIPE": "a proven multi-step procedure",
    "ROUTE": "an exact verb, host, path, headers and body with the success signal and read-back",
    "PROCESS": "an end-to-end way of working",
    "WALL": "something that is not headless, dated (many walls are superseded)",
    "LAW": "a rule that holds across orgs and changes outcomes",
    "OVERTURNED": "the newer lesson that replaced an older belief; its partner is a superseded lesson",
    "FACT": "a fact worth knowing, with its source",
    "PATTERN": "a reusable way to do something",
    "ERROR": "an error signature and what it really means",
    "PERF": "a measured performance fact",
    "SECURITY": "a rule about secrets, access or exposure",
    "DECISION": "a choice made, with its reasons",
    "WORKAROUND": "a way around a wall",
}


def n(x):
    return f"{x:,}"


def load():
    rows = [json.loads(l) for l in (LESSONS / "lessons.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    by_file, general = {}, collections.Counter()
    for p in lesson_files():
        t = p.read_text(encoding="utf-8")
        key = str(p.relative_to(KNOWLEDGE))
        by_file[key] = re.findall(r"^### (L-[A-Z]+-\d+)\s", t, re.M)
        g = re.split(r"^## Other general lessons.*$", t, flags=re.M)
        if len(g) > 1:
            general[key] = len(re.findall(r"^### L-", re.split(r"^## ", g[1], flags=re.M)[0], re.M))
    return rows, by_file, general


def stats(rows, ids):
    sel = [r for r in rows if r["id"] in set(ids)]
    st = collections.Counter(r["status"] for r in sel)
    dates = sorted(r["date"] for r in sel if r.get("date"))
    pfx = collections.Counter(r["id"].split("-")[1] for r in sel)
    return {"total": len(sel), "current": st["current"], "superseded": st["superseded"], "disputed": st["disputed"],
            "first": dates[0] if dates else "", "last": dates[-1] if dates else "", "prefixes": pfx,
            "domains": sorted({r["domain"] for r in sel})}


def summary_line(s, g):
    gen = f" ({g} of the current ones are general, not IDMC-specific)" if g else ""
    return (f"{n(s['total'])} lessons: {n(s['current'])} current{gen}, {s['disputed']} disputed, "
            f"{s['superseded']} superseded; evidence dated {s['first']} to {s['last']}.")


def sync_by_domain(rows, by_file, general):
    out = {}
    for name, ids in by_file.items():
        p = KNOWLEDGE / name
        t = p.read_text(encoding="utf-8")
        new = summary_line(stats(rows, ids), general.get(name))
        # the summary is the first sentence after the title that states the counts, up to its evidence date range
        t2, c = re.subn(r"^(?:\d[\d,]* (?:current )?lessons[:\s,].*?\d{4}-\d{2}-\d{2}\.)", lambda m: new, t, count=1,
                        flags=re.M)
        if c == 0:
            t2 = re.sub(r"^(# .*\n)", lambda m: m.group(1) + new + "\n", t, count=1)
        out[p] = t2
    return out


def sync_readme(rows, by_file, general):
    p = LESSONS / "README.md"
    t = p.read_text(encoding="utf-8")
    allst = stats(rows, [r["id"] for r in rows])
    t = re.sub(r"\*\*[\d,]+ lessons\*\* in \d+ domain files", f"**{n(allst['total'])} lessons** in {len(by_file)} domain files", t)
    t = re.sub(r"text\. [\d,]+ are current, [\d,]+ are superseded", f"text. {n(allst['current'])} are current, "
               f"{n(allst['superseded'])} are superseded", t)
    t = re.sub(r"and [\d,]+ are disputed\.", f"and {allst['disputed']} are disputed.", t)
    t = re.sub(r"\(evidence dates [\d-]+ to [\d-]+ across all files\)",
               f"(evidence dates {allst['first']} to {allst['last']} across all files)", t)
    t = re.sub(r"\([\d,]+ lines, the same ids as the headings\)", f"({n(allst['total'])} lines, the same ids as the headings)", t)
    # files table
    lines = ["| File | Id prefixes | Lessons | Current | Superseded | Disputed | Evidence dates |",
             "|---|---|---|---|---|---|---|"]
    for name, ids in by_file.items():
        s = stats(rows, ids)
        title = re.search(r"^# Lessons: (.+)$", (KNOWLEDGE / name).read_text(encoding="utf-8"), re.M)
        label = f"{name[:2]} {title.group(1).strip() if title else name}"
        pf = s["prefixes"]
        pref = ", ".join(f"`{k}` ({pf[k]})" for k in sorted(pf)) if len(pf) > 1 else ", ".join(f"`{k}`" for k in pf)
        cur = n(s["current"]) + (f" ({general[name]} general)" if general.get(name) else "")
        lines.append(f"| [{label}](../{name}) | {pref} | {n(s['total'])} | {cur} | {s['superseded']} | "
                     f"{s['disputed']} | {s['first']} to {s['last']} |")
    lines.append(f"| **Total** | {len(allst['prefixes'])} prefixes | **{n(allst['total'])}** | **{n(allst['current'])}** | "
                 f"**{allst['superseded']}** | **{allst['disputed']}** | {allst['first']} to {allst['last']} |")
    t = re.sub(r"\| File \| Id prefixes \|.*?\n(?:\|.*\n)+", "\n".join(lines) + "\n", t, count=1)
    # kinds table
    kc = collections.Counter(r["kind"] for r in rows)
    main = [k for k in KIND_MEANING if kc.get(k)]
    rest = sorted((k for k in kc if k not in KIND_MEANING), key=lambda k: (-kc[k], k))
    kl = ["| Kind | Means | Count |", "|---|---|---|"] + [f"| `{k}` | {KIND_MEANING[k]} | {n(kc[k])} |" for k in main]
    if rest:
        kl.append("| " + ", ".join(f"`{k}`" for k in rest) + " | rarer kinds | " + ", ".join(str(kc[k]) for k in rest) + " |")
    t = re.sub(r"\| Kind \| Means \| Count \|.*?\n(?:\|.*\n)+", "\n".join(kl) + "\n", t, count=1)
    # id-prefix table
    pl = ["| Prefix | Domain key | File |", "|---|---|---|"]
    for name, ids in by_file.items():
        s = stats(rows, ids)
        pl.append("| " + ", ".join(f"`{k}`" for k in sorted(s["prefixes"])) + " | " +
                  ", ".join(f"`{d}`" for d in s["domains"]) + f" | [{name}](../{name}) |")
    t = re.sub(r"\| Prefix \| Domain key \| File \|.*?\n(?:\|.*\n)+", "\n".join(pl) + "\n", t, count=1)
    out = {p: t}
    rp = ROOT / "README.md"
    rt = rp.read_text(encoding="utf-8")
    out[rp] = re.sub(r"carries \*\*[\d,]+ field lessons\*\*", f"carries **{n(allst['total'])} field lessons**", rt)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report stale files; exit 1 if any")
    a = ap.parse_args()
    rows, by_file, general = load()
    missing = {r["id"] for r in rows} - {i for ids in by_file.values() for i in ids}
    if missing:
        print("lessons.jsonl ids with no heading in any knowledge/<job>/lessons*.md file: " + ", ".join(sorted(missing)[:10]))
        return 1
    new = {**sync_by_domain(rows, by_file, general), **sync_readme(rows, by_file, general)}
    stale = [p for p, t in new.items() if p.read_text(encoding="utf-8") != t]
    if a.check:
        for p in stale:
            print("stale counts: " + str(p.relative_to(ROOT)))
        print("counts up to date" if not stale else f"{len(stale)} file(s) stale: run without --check")
        return 1 if stale else 0
    for p in stale:
        p.write_text(new[p], encoding="utf-8")
        print("updated " + str(p.relative_to(ROOT)))
    print(f"{len(rows):,} lessons; {len(stale)} file(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
