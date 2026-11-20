#!/usr/bin/env python3
"""
build_kb.py — assemble the readable master KB from the modular sections/ files.

This is the "Integrator" role from AGENTS.md, made reproducible. It:
  1. reads sections/00-executive-summary.md .. 12-glossary.md in order,
  2. strips each file's trailing "## Sources" block (citations live in sources/SOURCES.md),
  3. demotes every heading one level (so the master has a single H1),
  4. rewrites cross-references like (./04-....md) into in-document #anchors,
  5. prepends a title, provenance line, and an auto-generated table of contents,
  6. writes iics-to-ipus-knowledge-base.md at the KB root.

The output is generated on demand and is not shipped in the repo (sections/ is the
source of truth). Run it when you want the single-file version:
    python3 build/build_kb.py

Python 3.10+, standard library only. Safe to re-run (idempotent).
"""

import os
import re
import datetime

# --- locate the KB root (parent of this build/ dir) ---
BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
KB_ROOT = os.path.dirname(BUILD_DIR)
SECTIONS_DIR = os.path.join(KB_ROOT, "sections")
OUTPUT = os.path.join(KB_ROOT, "iics-to-ipus-knowledge-base.md")

# --- ordered section files (numeric prefix -> filename) ---
SECTION_FILES = [
    "00-executive-summary.md",
    "01-history-iics-to-idmc.md",
    "02-legacy-licensing-model.md",
    "03-ipu-consumption-model.md",
    "04-ipu-metering-by-service.md",
    "05-what-iics-locks-out.md",
    "06-what-ipus-unlock.md",
    "07-side-by-side-matrix.md",
    "08-migration-and-conversion.md",
    "09-commercial-model.md",
    "10-why-move-why-stay.md",
    "11-faq-objections.md",
    "12-glossary.md",
]


def github_slug(text: str) -> str:
    """Replicate GitHub's heading-anchor algorithm (no collapsing of repeats)."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)   # drop punctuation; keep word chars, spaces, hyphens
    s = s.replace(" ", "-")
    return s


def first_h1(lines):
    for ln in lines:
        m = re.match(r"^#\s+(.*)$", ln)
        if m:
            return m.group(1).strip()
    return None


def strip_sources(lines):
    """Truncate the file at its trailing '# Sources' / '## Sources' heading."""
    for i, ln in enumerate(lines):
        if re.match(r"^#+\s*Sources\b.*$", ln.strip()):
            # also drop a preceding '---' horizontal rule if present
            j = i
            while j - 1 >= 0 and lines[j - 1].strip() in ("", "---"):
                j -= 1
            return lines[:j]
    return lines


def demote_headings(lines):
    out = []
    for ln in lines:
        m = re.match(r"^(#{1,6})(\s)", ln)
        if m:
            hashes = m.group(1)
            if len(hashes) < 6:
                ln = "#" + ln
        out.append(ln)
    return out


def build_anchor_map():
    """filename numeric prefix -> in-doc anchor (from the file's H1 title)."""
    amap = {}
    titles = {}
    for fname in SECTION_FILES:
        num = fname[:2]
        with open(os.path.join(SECTIONS_DIR, fname), encoding="utf-8") as f:
            title = first_h1(f.read().splitlines())
        titles[num] = title
        amap[num] = github_slug(title) if title else num
    return amap, titles


def rewrite_links(text, anchor_map):
    """(NN-anything.md), (./NN-anything.md) and either with #frag -> (#section-anchor)."""
    def repl(m):
        num = m.group(1)
        anchor = anchor_map.get(num)
        return "(#%s)" % anchor if anchor else m.group(0)
    return re.sub(r"\((?:\.\/)?(\d\d)-[^)/]+\.md(?:#[^)]*)?\)", repl, text)


def main():
    anchor_map, titles = build_anchor_map()

    today = datetime.date.today().isoformat()
    header = []
    header.append("# IICS to IPUs — Knowledge Base")
    header.append("")
    header.append(
        "*Customer-facing • Built from the modular `sections/` files • "
        "Published consumption rates dated to **CPDS v39.1 (effective June 5, 2026)** • "
        "Last built: %s*" % today
    )
    header.append("")
    header.append(
        "> **Do not hand-edit this file.** It is generated from `sections/00…12` by "
        "`build/build_kb.py`. Edit the section files, then re-run the build. "
        "See [`AGENTS.md`](./AGENTS.md) and [`README.md`](./README.md). "
        "All citations live in [`sources/SOURCES.md`](./sources/SOURCES.md)."
    )
    header.append("")

    # table of contents (leading blank line separates it from the header blockquote)
    toc = ["", "## Contents", ""]
    for fname in SECTION_FILES:
        num = fname[:2]
        title = titles[num]
        toc.append("- [%s](#%s)" % (title, anchor_map[num]))
    toc.append("")

    body = []
    for fname in SECTION_FILES:
        with open(os.path.join(SECTIONS_DIR, fname), encoding="utf-8") as f:
            lines = f.read().splitlines()
        lines = strip_sources(lines)
        lines = demote_headings(lines)
        text = "\n".join(lines).rstrip()
        text = rewrite_links(text, anchor_map)
        body.append("\n---\n\n" + text + "\n")

    footer = []
    footer.append("\n---\n")
    footer.append("## Sources & References")
    footer.append("")
    footer.append(
        "Every non-obvious claim in this knowledge base traces to the canonical, "
        "de-duplicated citation registry: [`sources/SOURCES.md`](./sources/SOURCES.md). "
        "Published IPU consumption rates are quoted from the **Informatica Cloud & Product "
        "Description Schedule (CPDS) v39.1, effective June 5, 2026**; items marked "
        "`[verify]` are gated or unconfirmed and are tracked at the bottom of "
        "`sources/SOURCES.md` for the next fact-checking pass."
    )
    footer.append("")

    out = "\n".join(header) + "\n".join(toc) + "".join(body) + "\n".join(footer)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(out)

    n_verify = out.count("[verify]")
    print("Built: %s" % OUTPUT)
    print("Sections integrated: %d" % len(SECTION_FILES))
    print("Output size: %d lines, %d chars" % (out.count("\n") + 1, len(out)))
    print("[verify] markers carried through: %d" % n_verify)


if __name__ == "__main__":
    main()
