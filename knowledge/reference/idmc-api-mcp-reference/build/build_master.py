#!/usr/bin/env python3
"""
build_master.py -- builds THE single master document.

    python build/build_master.py

Reads every content/*.json in filename order and renders one .docx:
    idmc-api-mcp-master-reference.docx   (generated on demand; not shipped in the repo)

Needs the third-party package python-docx (pip install python-docx). Python 3.10+.

This is the ONLY script that writes the .docx. Never hand-edit the .docx --
edits there are destroyed on the next build. Edit content/*.json instead.

Design notes for agents:
  * One JSON file per section = parallel edits never collide.
  * Filename prefix sets document order. 00-09 front, 10-29 services,
    30-39 MCP, 40-49 matrices, 50-59 cross-cutting, 60+ multi-org, 90+ back.
  * Block types: table | paras | bullets | callout | code
  * Status/verb cells are colour-coded automatically from their text.
"""
import glob
import json
import os
import sys
from datetime import datetime

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "idmc-api-mcp-master-reference.docx")

NAVY = RGBColor(0x00, 0x27, 0x75)
BRIGHT = RGBColor(0x00, 0xB3, 0xFF)
BLUE = RGBColor(0x02, 0x2A, 0xC0)
TEAL = RGBColor(0x04, 0xE1, 0xCB)
GREY = RGBColor(0x59, 0x59, 0x59)
BLACK = RGBColor(0x00, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FAINT = RGBColor(0xB0, 0xB0, 0xB0)

HDR_BG = "002775"
ALT_BG = "F2F5FA"
CELL_BG = "E8EEF7"

GREEN = RGBColor(0x1E, 0x7B, 0x1E)
ORANGE = RGBColor(0xB3, 0x62, 0x0A)
RED = RGBColor(0xA1, 0x1B, 0x1B)
MIDGREY = RGBColor(0x6B, 0x6B, 0x6B)
PURPLE = RGBColor(0x4A, 0x4A, 0x8A)

# Any cell whose full text matches one of these gets coloured + centred.
TOKENS = {
    "YES": (GREEN, True), "WRITE": (GREEN, True), "REAL": (GREEN, True),
    "DOC": (BLUE, True), "RUN": (RGBColor(0x0B, 0x6E, 0x9E), True),
    "READ": (PURPLE, True),
    "UI": (ORANGE, True), "UI-ONLY": (ORANGE, True),
    "PARTIAL": (ORANGE, True), "DISPUTED": (ORANGE, True), "CONTESTED": (ORANGE, True),
    "NO": (RED, True), "GAP": (RED, True), "BLOCKED": (RED, True),
    "EMPTY-200": (RED, True),
    "--": (FAINT, False), "-": (FAINT, False), "": (BLACK, False),
}


def token_style(val):
    v = str(val).strip()
    if v in TOKENS:
        return TOKENS[v]
    if v and v[0] in "45" and len(v) <= 3 and v.isdigit():
        return RED, False
    return None


def set_bg(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def put(cell, text, size=7.5, bold=False, color=BLACK, mono=False, center=False):
    cell.text = ""
    p = cell.paragraphs[0]
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run(str(text))
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Consolas" if mono else "Arial"


def looks_mono(header_cell, col_values):
    """Endpoint/path-ish columns render monospaced."""
    h = str(header_cell).lower()
    if any(k in h for k in ("endpoint", "path", "action", "url", "code", "resource",
                            "tool", "verb", "cell")):
        return True
    hits = sum(1 for v in col_values[:8] if str(v).strip().startswith(("/", "GET ", "POST ")))
    return hits >= 3


def add_table(doc, header, rows, usable=9.9):
    ncol = len(header)
    t = doc.add_table(rows=1, cols=ncol)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    cols = [[(r[i] if i < len(r) else "") for r in rows] for i in range(ncol)]
    token_cols = set()
    for i in range(ncol):
        vals = [str(v).strip() for v in cols[i] if str(v).strip()]
        if vals and sum(1 for v in vals if token_style(v) is not None) >= max(2, len(vals) * 0.6):
            token_cols.add(i)
    mono_cols = {i for i in range(ncol)
                 if i not in token_cols and looks_mono(header[i], cols[i])}

    # A verb-list column needs enough width to hold "GET, POST, DELETE" on one line,
    # so it gets a fixed generous width rather than being sized by mean length.
    verb_cols = {i for i in range(ncol)
                 if str(header[i]).strip().lower() in
                 ("verbs supported", "verbs proven", "verbs")}
    VERB_W = 1.15

    weights = []
    for i in range(ncol):
        if i in token_cols or i in verb_cols:
            weights.append(0.0)
            continue
        lens = [len(str(header[i]))] + [len(str(v)) for v in cols[i]]
        weights.append(max(8, min(90, sum(lens) / max(1, len(lens)))))
    fixed = (sum(0.62 for i in range(ncol) if i in token_cols)
             + sum(VERB_W for i in range(ncol) if i in verb_cols))
    avail = max(1.0, usable - fixed)
    wsum = sum(weights) or 1
    widths = []
    for i in range(ncol):
        if i in token_cols:
            widths.append(0.62)
        elif i in verb_cols:
            widths.append(VERB_W)
        else:
            widths.append(max(0.62, avail * weights[i] / wsum))

    fs = 7.5 if ncol <= 5 else 7.0

    hdr = t.rows[0]
    for i, h in enumerate(header):
        set_bg(hdr.cells[i], HDR_BG)
        put(hdr.cells[i], h, size=fs, bold=True, color=WHITE, center=(i in token_cols))
    repeat_header(hdr)

    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci in range(ncol):
            val = row[ci] if ci < len(row) else ""
            st = token_style(val) if ci in token_cols else None
            if st:
                col, bold = st
                put(cells[ci], val, size=fs, bold=bold, color=col, center=True)
                if str(val).strip() not in ("--", "-", ""):
                    set_bg(cells[ci], CELL_BG)
            else:
                put(cells[ci], val, size=fs, mono=(ci in mono_cols))
                if ri % 2 == 1:
                    set_bg(cells[ci], ALT_BG)
    for r in t.rows:
        for i, w in enumerate(widths):
            if i < len(r.cells):
                r.cells[i].width = Inches(w)
    return t


def h1(doc, text, pagebreak=True):
    if pagebreak:
        doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(text)
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = NAVY
    r.font.name = "Arial"
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), "12")
    b.set(qn("w:color"), "00B3FF")
    pbdr.append(b)
    pPr.append(pbdr)
    return p


def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = BLUE
    r.font.name = "Arial"
    return p


def para(doc, text, size=9, italic=False, color=BLACK, bold=False, after=5):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.italic = italic
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Arial"
    return p


def bullet(doc, text, size=9):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = "Arial"
    return p


def callout(doc, label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.left_indent = Inches(0.12)
    if label:
        r = p.add_run(label.rstrip() + "  ")
        r.font.size = Pt(9)
        r.font.bold = True
        r.font.color.rgb = NAVY
        r.font.name = "Arial"
    r2 = p.add_run(text)
    r2.font.size = Pt(9)
    r2.font.name = "Arial"
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:color"), "00B3FF")
    left.set(qn("w:space"), "6")
    pbdr.append(left)
    pPr.append(pbdr)
    return p


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    r.font.size = Pt(8)
    r.font.name = "Consolas"
    return p


def load_sections():
    out = []
    for f in sorted(glob.glob(os.path.join(CONTENT, "*.json"))):
        try:
            out.append((os.path.basename(f), json.load(open(f, encoding="utf-8"))))
        except Exception as e:
            print("  !! SKIPPED %s -- invalid JSON: %s" % (os.path.basename(f), e))
    return out


def render_block(doc, b):
    bt = b.get("type", "paras")
    if bt == "table":
        if b.get("title"):
            h2(doc, b["title"])
        if b.get("intro"):
            para(doc, b["intro"], size=9, italic=True, color=GREY, after=4)
        rows = b.get("rows") or []
        if rows:
            add_table(doc, b["header"], rows)
        else:
            para(doc, "(no rows yet)", size=8.5, italic=True, color=GREY)
    elif bt == "paras":
        if b.get("title"):
            h2(doc, b["title"])
        for t in b.get("text", []):
            para(doc, t, size=b.get("size", 9))
    elif bt == "bullets":
        if b.get("title"):
            h2(doc, b["title"])
        for t in b.get("items", []):
            bullet(doc, t)
    elif bt == "callout":
        callout(doc, b.get("label", ""), b.get("text", ""))
    elif bt == "code":
        if b.get("title"):
            h2(doc, b["title"])
        code(doc, b.get("text", ""))


def build():
    sections = load_sections()
    doc = Document()
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(9)
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Inches(11), Inches(8.5)
    for s in doc.sections:
        s.top_margin = Inches(0.45)
        s.bottom_margin = Inches(0.45)
        s.left_margin = Inches(0.5)
        s.right_margin = Inches(0.5)
        p = s.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("IDMC API & MCP Master Reference   ·   generated from content/*.json   ·   "
                      "do not hand-edit this file")
        r.font.size = Pt(7)
        r.font.color.rgb = GREY
        r.font.name = "Arial"

    nrows = sum(len(b.get("rows", [])) for _, s in sections
                for b in s.get("blocks", []) if b.get("type") == "table")
    ntab = sum(1 for _, s in sections for b in s.get("blocks", [])
               if b.get("type") == "table" and b.get("rows"))

    # ---- cover ----
    for _ in range(3):
        doc.add_paragraph()
    for txt, col in [("IDMC API & MCP", NAVY), ("Master Reference", BRIGHT)]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(txt)
        r.font.size = Pt(38)
        r.font.bold = True
        r.font.color.rgb = col
        r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(16)
    r = p.add_run("Every IDMC API surface and every MCP action — what each one can do,\n"
                  "which HTTP verbs it accepts, and how far it has actually been proven")
    r.font.size = Pt(12.5)
    r.font.color.rgb = GREY
    r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(30)
    r = p.add_run("THE single master document for this knowledge base")
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = BLUE
    r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("%d sections · %d tables · %d data rows" % (len(sections), ntab, nrows))
    r.font.size = Pt(10.5)
    r.font.color.rgb = TEAL
    r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(34)
    r = p.add_run("Generated " + datetime.now().strftime("%d %B %Y, %H:%M"))
    r.font.size = Pt(10)
    r.font.color.rgb = GREY
    r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Generated file — edit content/*.json and re-run build/build_master.py")
    r.font.size = Pt(8.5)
    r.font.italic = True
    r.font.color.rgb = GREY
    r.font.name = "Arial"

    # ---- contents + freshness ----
    h1(doc, "Contents & section freshness")
    para(doc, "One row per section. The owner and last-verified columns are maintained by whoever "
              "edits that section, so this table doubles as the work register: a section with an old "
              "verified date or a draft status is the next thing to pick up.",
         size=9.5)
    toc_rows = []
    for fn, s in sections:
        nb = sum(len(b.get("rows", [])) for b in s.get("blocks", [])
                 if b.get("type") == "table")
        toc_rows.append([
            s.get("title", fn),
            fn,
            s.get("owner") or "unassigned",
            s.get("last_verified") or "-",
            s.get("status") or "-",
            str(nb) if nb else "-",
        ])
    add_table(doc, ["Section", "Content file", "Owner", "Last verified", "Status", "Rows"], toc_rows)

    oq = [(s.get("title"), q) for _, s in sections for q in s.get("open_questions", [])]
    if oq:
        h2(doc, "Open questions across all sections")
        para(doc, "Collected automatically from every section's open_questions list. These are the "
                  "known-unknowns; do not present any of them to a customer as settled.",
             size=9, italic=True, color=GREY)
        add_table(doc, ["Section", "Open question"], [[a, b] for a, b in oq])

    # ---- sections ----
    for fn, s in sections:
        h1(doc, s.get("title", fn))
        meta = []
        if s.get("owner"):
            meta.append("owner: " + s["owner"])
        if s.get("last_verified"):
            meta.append("last verified: " + s["last_verified"])
        if s.get("status"):
            meta.append("status: " + s["status"])
        if meta:
            para(doc, "   ·   ".join(meta), size=8, italic=True, color=GREY, after=4)
        if s.get("intro"):
            para(doc, s["intro"], size=9.5)
        for b in s.get("blocks", []):
            render_block(doc, b)
        for n in s.get("notes", []):
            if isinstance(n, dict):
                callout(doc, n.get("label", ""), n.get("text", ""))
            else:
                callout(doc, "", str(n))
        if s.get("open_questions"):
            h2(doc, "Open questions in this section")
            for q in s["open_questions"]:
                bullet(doc, q)

    doc.save(OUT)
    print("WROTE:", OUT)
    print("sections: %d   tables: %d   rows: %d" % (len(sections), ntab, nrows))
    return OUT


if __name__ == "__main__":
    build()
