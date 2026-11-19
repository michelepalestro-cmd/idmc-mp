#!/usr/bin/env python3
"""
build_pdf.py — render the generated master KB (Markdown) to a clean, customer-facing PDF.

Pipeline:
  1. read  iics-to-ipus-knowledge-base.md  (the single-file KB built by build_kb.py; run that first)
  2. convert Markdown -> HTML (tables, fenced code, GitHub-style heading anchors so the
     in-document Contents links resolve)
  3. wrap in a print stylesheet (Arial, Informatica blue, zebra tables, per-section page breaks)
  4. render HTML -> PDF via Playwright (msedge channel), with footer page numbers

Shareability: this renders ONLY the generated deliverable, which is built from sections/ (no
prices, no discount schedules). Do not point it at any other file.

Requires:  Python 3.10+, pip install markdown pymdown-extensions playwright, and the msedge
           browser channel (Windows; on other systems change channel= to a browser you have).
Run:       python3 build/build_kb.py && python3 build/build_pdf.py
Output:    iics-to-ipus-knowledge-base.pdf at the KB root (generated; not shipped in the repo).
"""

import os
import pathlib
import re
import datetime
import markdown
from markdown.extensions.toc import TocExtension
from playwright.sync_api import sync_playwright

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
KB_ROOT = os.path.dirname(BUILD_DIR)
SRC_MD = os.path.join(KB_ROOT, "iics-to-ipus-knowledge-base.md")
OUT_HTML = os.path.join(BUILD_DIR, "_kb_render.html")   # intermediate (scratch; git-ignored)
OUT_PDF = os.path.join(KB_ROOT, "iics-to-ipus-knowledge-base.pdf")


def github_slugify(value, separator):
    """Match build_kb.py's github_slug so the doc's #anchors resolve in the PDF."""
    v = value.strip().lower()
    v = re.sub(r"[^\w\s-]", "", v)
    v = re.sub(r"\s+", separator, v)
    return v


CSS = """
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
  font-size: 10.5pt; line-height: 1.5; color: #1f2733; margin: 0;
}
/* ---- headings (Informatica blue, no orange) ---- */
h1 { font-size: 26pt; color: #0b3d91; margin: 0 0 6pt; line-height: 1.15; }
h2 { font-size: 17pt; color: #0b4f9e; margin: 22pt 0 8pt;
     padding-bottom: 4pt; border-bottom: 2px solid #0b4f9e; break-after: avoid; }
h3 { font-size: 13pt; color: #14568c; margin: 16pt 0 6pt; break-after: avoid; }
h4 { font-size: 11.5pt; color: #2a3f5f; margin: 12pt 0 4pt; break-after: avoid; }
/* start each top-level section on a fresh page (H2), but not the very first block */
h2 { break-before: page; }
h2.no-break { break-before: auto; }
p { margin: 0 0 8pt; }
a { color: #0b4f9e; text-decoration: none; }
strong { color: #14283f; }
ul, ol { margin: 0 0 8pt; padding-left: 20pt; }
li { margin: 2pt 0; }
hr { border: 0; border-top: 1px solid #d7dee8; margin: 14pt 0; }
/* ---- tables ---- */
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt;
        font-size: 9pt; break-inside: auto; }
th, td { border: 1px solid #c6d2e1; padding: 5pt 7pt; text-align: left;
         vertical-align: top; word-break: normal; overflow-wrap: anywhere; }
th { background: #e9f1fb; color: #0b3d91; font-weight: bold; }
tr { break-inside: avoid; }
tbody tr:nth-child(even) { background: #f5f8fc; }
/* ---- blockquotes / callouts ---- */
blockquote { margin: 10pt 0; padding: 8pt 12pt; background: #f2f7fd;
             border-left: 4px solid #0b4f9e; color: #26374f; }
blockquote p { margin: 0 0 5pt; }
blockquote p:last-child { margin-bottom: 0; }
/* ---- code ---- */
code { font-family: "Consolas", "Courier New", monospace; font-size: 9pt;
       background: #eef1f5; padding: 1pt 4pt; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #e1e6ec; border-radius: 4px;
      padding: 8pt 10pt; overflow-x: auto; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.5pt; }
/* ---- cover ---- */
.cover { border-bottom: 3px solid #0b3d91; padding-bottom: 12pt; margin-bottom: 4pt; }
.cover .sub { color: #4a5a72; font-size: 11pt; margin-top: 2pt; }
.cover .meta { color: #6b7a90; font-size: 9pt; margin-top: 8pt; }
img { max-width: 100%; }
"""

HTML_TMPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>{css}</style></head>
<body>{body}</body></html>"""


def main():
    with open(SRC_MD, encoding="utf-8") as f:
        md_text = f.read()

    html_body = markdown.markdown(
        md_text,
        extensions=["extra", "sane_lists",
                    TocExtension(slugify=github_slugify, separator="-", toc_depth="2-3")],
        output_format="html5",
    )
    # let the title (first H1) and the Contents heading share the cover page
    html_body = html_body.replace("<h2", "<h2 class=\"no-break\"", 1)

    html = HTML_TMPL.format(css=CSS, body=html_body)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    footer = ('<div style="width:100%;font-family:Arial;font-size:8pt;color:#8a97a8;'
              'padding:0 14mm;display:flex;justify-content:space-between;">'
              '<span>IICS to IPUs — Knowledge Base · customer-facing</span>'
              '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
              '</div>')
    header = '<span></span>'

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page()
        pg.goto(pathlib.Path(OUT_HTML).as_uri())
        pg.emulate_media(media="print")
        pg.pdf(
            path=OUT_PDF, format="Letter", print_background=True,
            display_header_footer=True, header_template=header, footer_template=footer,
            margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
        )
        b.close()

    size_kb = os.path.getsize(OUT_PDF) / 1024
    print("Built PDF -> %s" % OUT_PDF)
    print("Source: %s (%d chars)" % (os.path.basename(SRC_MD), len(md_text)))
    print("PDF size: %.0f KB" % size_kb)
    print("Rendered: %s" % datetime.date.today().isoformat())


if __name__ == "__main__":
    main()
