#!/usr/bin/env python3
"""
build_verbmatrix.py — "IDMC Verb Matrix - API vs MCP"

Companion to the Capability Reference. Two questions, answered directly:
  1. For every endpoint, per service: which of GET/POST/PUT/PATCH/DELETE work?
  2. What is available via REST API vs via MCP?
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import idmc_verbmatrix_data as V

OUT_DIR = os.path.dirname(os.path.abspath(__file__))  # write next to this script, never to a user-profile path
OUT = os.path.join(OUT_DIR, "IDMC Verb Matrix - API vs MCP.docx")
BUILD_DATE = "25 July 2026"

NAVY = RGBColor(0x00, 0x27, 0x75)
BRIGHT = RGBColor(0x00, 0xB3, 0xFF)
BLUE = RGBColor(0x02, 0x2A, 0xC0)
TEAL = RGBColor(0x04, 0xE1, 0xCB)
GREY = RGBColor(0x59, 0x59, 0x59)
BLACK = RGBColor(0x00, 0x00, 0x00)
HDR_BG = "002775"
ALT_BG = "F2F5FA"
VERB_BG = "E8EEF7"

GREEN = RGBColor(0x1E, 0x7B, 0x1E)
ORANGE = RGBColor(0xB3, 0x62, 0x0A)
RED = RGBColor(0xA1, 0x1B, 0x1B)
MID = RGBColor(0x6B, 0x6B, 0x6B)

VERBS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def cellcolor(val):
    v = str(val).strip()
    if v == "YES":
        return GREEN, True
    if v == "DOC":
        return BLUE, True
    if v == "UI":
        return ORANGE, True
    if v == "--":
        return RGBColor(0xB0, 0xB0, 0xB0), False
    if v and v[0] in "45":
        return RED, False
    if v in ("NO",):
        return RED, True
    if v in ("PARTIAL", "DISPUTED"):
        return ORANGE, True
    return BLACK, False


def set_cell_bg(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def cell_text(cell, text, size=7.5, bold=False, color=BLACK, mono=False, center=False):
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


def verb_table(doc, rows, path_w=3.05, note_w=3.05):
    """rows: [path, GET, POST, PUT, PATCH, DELETE, note]"""
    headers = ["Endpoint"] + VERBS + ["Notes"]
    t = doc.add_table(rows=1, cols=7)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0]
    for i, h in enumerate(headers):
        set_cell_bg(hdr.cells[i], HDR_BG)
        cell_text(hdr.cells[i], h, size=7.5, bold=True,
                  color=RGBColor(0xFF, 0xFF, 0xFF), center=(0 < i < 6))
    set_repeat_header(hdr)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        cell_text(cells[0], row[0], size=7, mono=True)
        for vi in range(1, 6):
            col, bold = cellcolor(row[vi])
            cell_text(cells[vi], row[vi], size=7, bold=bold, color=col, center=True)
            if str(row[vi]).strip() not in ("--",):
                set_cell_bg(cells[vi], VERB_BG)
        cell_text(cells[6], row[6], size=7)
        if ri % 2 == 1:
            set_cell_bg(cells[0], ALT_BG)
            set_cell_bg(cells[6], ALT_BG)
    widths = [path_w, 0.52, 0.55, 0.5, 0.58, 0.62, note_w]
    for r in t.rows:
        for i, w in enumerate(widths):
            r.cells[i].width = Inches(w)
    return t


def plain_table(doc, headers, rows, widths, mono_cols=(), color_cols=(), fontsize=7.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0]
    for i, h in enumerate(headers):
        set_cell_bg(hdr.cells[i], HDR_BG)
        cell_text(hdr.cells[i], h, size=fontsize, bold=True,
                  color=RGBColor(0xFF, 0xFF, 0xFF), center=(i in color_cols))
    set_repeat_header(hdr)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, val in enumerate(row):
            if ci in color_cols:
                col, bold = cellcolor(val)
                cell_text(cells[ci], val, size=fontsize, bold=bold, color=col, center=True)
                set_cell_bg(cells[ci], VERB_BG)
            else:
                cell_text(cells[ci], val, size=fontsize, mono=(ci in mono_cols))
                if ri % 2 == 1:
                    set_cell_bg(cells[ci], ALT_BG)
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
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:color"), "00B3FF")
    pbdr.append(bottom)
    pPr.append(pbdr)


def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = BLUE
    r.font.name = "Arial"


def body(doc, text, size=9, italic=False, color=BLACK, bold=False, space_after=5):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.italic = italic
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = "Arial"


def bullet(doc, text, size=9):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = "Arial"


def callout(doc, label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.left_indent = Inches(0.12)
    r = p.add_run(label + "  ")
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


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.space_before = Pt(3)
    r = p.add_run(text)
    r.font.size = Pt(8)
    r.font.name = "Consolas"


def svc(doc, title, sub, rows, notes=None, path_w=3.05, note_w=3.05):
    h1(doc, title)
    if sub:
        body(doc, sub, size=9, italic=True, color=GREY, space_after=6)
    verb_table(doc, rows, path_w=path_w, note_w=note_w)
    for lab, txt in (notes or []):
        callout(doc, lab, txt)


def build():
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
        r = p.add_run("IDMC Verb Matrix - API vs MCP   ·   built " + BUILD_DATE
                      + "   ·   companion to the IDMC API & MCP Capability Reference")
        r.font.size = Pt(7)
        r.font.color.rgb = GREY
        r.font.name = "Arial"

    # ---------- COVER ----------
    for _ in range(3):
        doc.add_paragraph()
    for txt, sz, col in [("IDMC Verb Matrix", 38, NAVY), ("API vs MCP", 38, BRIGHT)]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(txt)
        r.font.size = Pt(sz)
        r.font.bold = True
        r.font.color.rgb = col
        r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(16)
    r = p.add_run("Which of GET / POST / PUT / PATCH / DELETE works on every endpoint,\n"
                  "and what you can do through the API versus through MCP")
    r.font.size = Pt(12.5)
    r.font.color.rgb = GREY
    r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(34)
    r = p.add_run("Part 1  —  the verb matrix, endpoint by endpoint, per service\n"
                  "Part 2  —  API vs MCP, capability by capability")
    r.font.size = Pt(11.5)
    r.font.bold = True
    r.font.color.rgb = BLUE
    r.font.name = "Arial"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(38)
    r = p.add_run("Built " + BUILD_DATE)
    r.font.size = Pt(10)
    r.font.color.rgb = GREY
    r.font.name = "Arial"

    # ---------- HOW TO READ ----------
    h1(doc, "How to read the verb matrix")
    body(doc, "Every service section below is one table. The rows are endpoints; the five middle "
              "columns are the HTTP verbs. Read across a row to see what that endpoint accepts.", size=9.5)

    h2(doc, "What the five verbs mean")
    for v, t in [
        ("GET", "Retrieves data from the server without changing anything."),
        ("POST", "Sends new data to create a new resource."),
        ("PUT", "Replaces an existing resource entirely with the data you send."),
        ("PATCH", "Applies a partial update to an existing resource."),
        ("DELETE", "Removes a specific resource from the server."),
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(v + "   ")
        r.font.size = Pt(9)
        r.font.bold = True
        r.font.name = "Consolas"
        r.font.color.rgb = NAVY
        r2 = p.add_run(t)
        r2.font.size = Pt(9)
        r2.font.name = "Arial"

    h2(doc, "What each cell means")
    plain_table(doc,
                ["Cell", "Meaning"],
                [["YES", "Verified working against a live IDMC org. This verb is supported here."],
                 ["DOC", "Informatica documents this verb, but it was not exercised in testing. Unproven."],
                 ["UI", "The operation exists but only in the user interface. No verb reaches it."],
                 ["405", "Explicitly rejected as method-not-allowed. The resource is read-only. A definite no."],
                 ["404 / 403 / 400 / 500", "Explicitly rejected with that code. See the note for what it means."],
                 ["--", "Not documented and not observed. This means UNKNOWN, not 'absent'."]],
                [0.95, 8.95], color_cols=(0,), fontsize=8.5)

    callout(doc, "The distinction that matters most in this document.",
            "A blank cell (--) is not evidence of anything. It means nobody has probed that verb on that "
            "path and Informatica has not published it. A 405, by contrast, is a hard no from the server. "
            "Do not read an empty cell as 'unsupported' — read it as 'untested'. That is the honest state "
            "of a great deal of the IDMC surface, and pretending otherwise is how the earlier wrong "
            "conclusions in this project got made.")

    h2(doc, "Two IDMC quirks that will confuse you if nobody says them out loud")
    bullet(doc, "The v2 platform plane barely uses PUT or PATCH. To update a v2 resource you POST to "
                "the path with the resource id in it — POST /api/v2/connection/{id} IS the update call. "
                "So an empty PUT column on a v2 row is usually correct behaviour, not a gap.")
    bullet(doc, "PATCH is rare across the whole platform. It appears meaningfully only in MDM (documented "
                "for entity and entity-xref) and in a handful of v3 resources where it returns 405 anyway. "
                "If you are used to REST APIs where PATCH is standard, adjust your expectations.")

    # ================= PART 1 =================
    h1(doc, "Part 1  —  the verb matrix, per service")
    body(doc, "Thirteen tables, one per service area, covering roughly 130 endpoints. Where an endpoint "
              "family was probed across many path variants, the row shows the family and the note gives "
              "the count.", size=9.5, italic=True, color=GREY)
    h2(doc, "Which services appear")
    body(doc, "Administration and Core · Migration (export/import) · CDI · CAI asset lifecycle · CAI "
              "invocation and runtime administration · CDGC · CDQ · Data Profiling · Mass Ingestion · "
              "Data Marketplace · MDM, C360, B360 and Reference 360 · Operational Insights · Data Access "
              "Management, API Manager and CLAIRE.", size=9.5)

    svc(doc, "Administration & Core  —  platform v2 and v3",
        "Users, groups, roles, privileges, schedules, licensing, audit. The most reliably writeable "
        "part of IDMC.",
        V.VM_ADMIN,
        notes=[("The one row to internalise.",
                "/public/core/v3/objects answers GET for any asset type in the org and returns 405 for "
                "POST. It is the fastest inventory tool available and it is completely read-only — there "
                "is no generic create-any-object endpoint. Note also that user edit is 405 on both PUT "
                "and PATCH: to change a user you delete and recreate.")])

    svc(doc, "Migration  —  export & import",
        "The only headless authoring backdoor. It clones an existing asset; it does not author new logic.",
        V.VM_MIGR,
        notes=[("Note the verb asymmetry on /export.",
                "GET /export returns 405 while POST /export works — the resource is a job factory, not a "
                "collection. You then GET the specific job and its package. This pattern (POST to start, "
                "GET to poll) repeats across every async operation in IDMC: metering export, catalog "
                "scans, CAI publish.")])

    svc(doc, "CDI  —  Cloud Data Integration",
        "Connections, mapping tasks, jobs, schedules, monitoring. Fully operational over REST; the "
        "design canvas is not.",
        V.VM_CDI,
        notes=[("This table is the clearest illustration of the v2 update pattern.",
                "Connection, mapping task and several others show POST in two rows — once on the "
                "collection to create, once on /{id} to update. There is no PUT anywhere in CDI, and "
                "PATCH returns 405 where it is defined at all. If you are writing a client, do not look "
                "for PUT; it is not coming."),
               ("The single row that defines the CDI ceiling.",
                "POST /api/v2/mapping returns a 400 carrying an HTML 'Internal error' page. That is the "
                "whole story of CDI automation: you can create the connection, wrap an existing mapping "
                "in a task, run it, schedule it and monitor it — but you cannot author the mapping. "
                "Informatica's product team confirmed design-time asset creation was never exposed, with "
                "API mapping design previewed for late 2026.")])

    svc(doc, "CAI  —  asset lifecycle (publish, unpublish, update)",
        "On the dedicated -cai host. This is where the publish capability lives that was long believed "
        "to be UI-only.",
        V.VM_CAI_ASSET,
        notes=[("The verb detail that resolved a months-old misconception.",
                "GET on /active-bpel/asset/v1/publish returns 405 — the resource is POST-only. Probing it "
                "with a GET therefore looks like a dead end when it is actually a working endpoint being "
                "asked the wrong question. Add the wrong host and the missing /v1/ segment and you get "
                "the 403 that was recorded as a wall for months."),
               ("Publish needs an unusual content type.",
                "Both publish and unpublish require Accept and Content-Type of application/vnd.api+json "
                "(JSON:API style) plus INFA-SESSION-ID. Body is data.attributes.assetPaths[], an array of "
                "Explore/<path>/<name>.PROCESS.xml entries, dependencies first: service connector, then "
                "app connection, then process. Maximum 199 assets per call."),
               ("PUT appears here and nowhere else in CAI.",
                "The asset/v1/update resource is genuinely PUT-based, for changing allowed users and "
                "groups, anonymous access and tracing level. Note the vendor's own caveat: after a REST "
                "update to an app connection you must republish it in the UI for the change to take "
                "effect. A REST write that needs a UI follow-up is worth knowing about before you build "
                "on it.")])

    svc(doc, "CAI  —  invocation & runtime administration",
        "Process invocation plus the restadmin plane: schedules, URN mappings and live control of "
        "running instances.",
        V.VM_CAI_RT,
        notes=[("Process invocation is the one place where all five verbs are genuinely in play.",
                "A published CAI process can be exposed on GET, POST, PUT, PATCH or DELETE — the verb is "
                "part of how you design the process, not a property of the platform. Append ?swagger to "
                "the /rt/ URL to read which verbs a given process actually accepts. This is the only "
                "endpoint family in IDMC where the answer is 'whatever you built'."),
               ("The restadmin plane is the richest runtime-control surface in the platform.",
                "Suspend, resume and terminate a running process; full schedule CRUD; start and stop "
                "listener-based event sources. Writes return 204. Note the shape: schedules use "
                "GET/POST/PUT/DELETE with no PATCH, and URN mappings use PUT for both add and update "
                "with no POST at all. Every path here has a Secure Agent twin under "
                "/process-engine/restadmin/ on the agent host and port."),
               ("One genuine no-verb-at-all row.",
                "Activating or deactivating a published API is a Console click. The vendor documents it "
                "only as a UI path, and adds that republishing a process does NOT activate its API — you "
                "must activate it from the APIs page. There is no endpoint to probe.")])

    svc(doc, "CDGC  —  Cloud Data Governance & Catalog",
        "Fully scriptable for scanning and searching. The most UI-bound service for governance content.",
        V.VM_CDGC,
        notes=[("Both principal CDGC endpoints are POST-only, and GET returns 405 on each.",
                "The scan trigger and the search endpoint both reject GET. For search that surprises "
                "people, because it reads data — but the query is an Elasticsearch DSL document, so it "
                "goes in a POST body. Search also needs a fourth header, X-INFA-SEARCH-LANGUAGE: "
                "elasticsearch, or you get 400 MissingRequestHeaderException."),
               ("The bottom four rows are the governance content wall.",
                "Glossary, classification accept, lineage and stewardship return 404 across every verb "
                "and across dozens of path variants — and critically, with empty response bodies, which "
                "means the route is not mounted rather than mistyped. Classification accept is the "
                "starkest: there is no Accept control at all, not over REST and not in the UI, which "
                "offers only Dismiss."),
               ("There is no cancel verb for a running scan.",
                "This matters operationally. Re-firing a scan while one runs returns 406 (a lock, not an "
                "error), and a stuck scan holds that lock indefinitely with no headless way to clear it. "
                "Cancelling is an MCC UI action.")])

    svc(doc, "CDQ  —  Cloud Data Quality",
        "Dictionaries have real CRUD on their own -dqcloud-api host. Everything else in CDQ does not.",
        V.VM_CDQ,
        notes=[("The dictionary API uses four verbs and is still write-only.",
                "POST creates, POST adds rows, PUT replaces all rows, DELETE clears them or removes the "
                "dictionary. What it does not have is GET — there is no read verb anywhere in the CDQ API "
                "Reference, so you cannot list dictionaries or fetch rows, and you cannot even obtain a "
                "dictionaryId from the API. Informatica tells you to read the id out of the dictionary's "
                "URL in the UI."),
               ("A UI switch gates whether your calls are accepted at all.",
                "A dictionary cannot take UI edits and API edits at the same time. Someone must click "
                "Convert to API in the interface first, and Convert to UI to hand it back. That toggle is "
                "itself UI-only, so a fully headless dictionary workflow is not possible from a cold start."),
               ("Address Verification is the cleanest documented single-verb endpoint in IDMC.",
                "POST is supported and the vendor explicitly documents 405 for every other method. The six "
                "modes — batch, certified, interactive, QuickCapture, geocode, address-code lookup — are "
                "not separate paths; they are a Mode field in the request body.")])

    svc(doc, "Data Profiling",
        "A rich read surface on the -dqprofile host. The write verbs are documented but their paths are "
        "not published locally.",
        V.VM_PROF,
        notes=[("Why this table is mostly GET and DOC.",
                "Informatica states plainly that the Data Profiling REST API can create, delete and update "
                "queries and profiles. But the endpoint paths live in a separate guide, Getting Started "
                "with Cloud Data Profiling REST API, which is not held locally — so the write verbs are "
                "marked DOC and the row says so. This is documented-but-unmapped, which is a different "
                "thing from absent."),
               ("Watch for the 200 that is really an HTML login page.",
                "These hosts need a SPA-injected IDS-SESSION-ID. Called with a plain INFA-SESSION-ID they "
                "return HTTP 200 with the identity-service login page as the body. Any tooling that "
                "classifies on status code alone will record that as a success. Always check the content "
                "type.")])

    svc(doc, "Mass Ingestion  —  CMI, DBMI, file, application, streaming",
        "The clearest example in IDMC of a service that is entitled, deployed, running — and still not "
        "authorable over REST.",
        V.VM_CMI,
        notes=[("Every verb, every path, 404 — and it is still not an entitlement problem.",
                "Informatica documents POST /dbmi/public/api/v2/task/create returning 201. On the probed "
                "org that path 404s, along with every v2 name variant, every v3 name variant and the "
                "micro-service bases. Yet GET /api/v2/agent/details shows the Database Ingestion and Mass "
                "Ingestion Runtime engines RUNNING on both Secure Agents, with create and execute "
                "privileges present. The correct conclusion is wizard-only authoring on this org, and a "
                "documented endpoint worth re-probing on another."),
               ("The clone backdoor does not help here either.",
                "Migration cloning needs an existing asset of the same type to copy. Nothing to clone "
                "means the first task must be built in the wizard before any headless work is possible.")])

    svc(doc, "Data Marketplace",
        "The strongest multi-verb write surface in the governance family, spread across three planes.",
        V.VM_DMP,
        notes=[("This is the one governance service where PUT is documented.",
                "The CAI Design guide's Data Marketplace section states the API supports GET, POST and PUT "
                "on dataAssets and dataElements. Combined with the verified creates on collections, "
                "categories, orders, terms of use and delivery targets, marketplace has the broadest verb "
                "coverage of anything in the data360 family."),
               ("Mind which of the three planes you are on.",
                "Marketplace spans api/v1 and api/v2 on the idmc-api host, plus a provisioning API on the "
                "cdgc-api host. Looking for delivery templates on the v2 plane returns 400 or 405 and "
                "reads as a wall, when the templates are simply on the third plane. Creating a template, "
                "however, is genuinely UI-only — 405 on every verb.")])

    svc(doc, "MDM, Customer 360, Business 360 & Reference 360",
        "The only service where PATCH is meaningfully documented — and the service with the hardest "
        "deploy wall.",
        V.VM_MDM,
        notes=[("MDM is where PUT and PATCH actually matter.",
                "The documented resource model gives entity and entity-xref both a full replace (PUT) and "
                "a partial update (PATCH). This is the only part of IDMC where the PATCH column earns its "
                "place. Note that the shipped Customer 360 documentation contains no REST reference at "
                "all — the resource model here comes from an Informatica solution-architect deck, so "
                "treat it as indicative and confirm against the Business 360 REST API Reference."),
               ("The routing rule that prevents data corruption.",
                "Updates arriving from a source system must go to entity-xref, NOT to the golden-record "
                "entity resource. Writing source data straight onto the master record bypasses "
                "survivorship. Also: the base URL mutates — after login, add -mdm to the pod label and "
                "strip the trailing /saas."),
               ("The deploy wall, and the one disputed row.",
                "Business-entity deploy returns 404 across roughly 20 candidate paths and every verb; "
                "until an entity is deployed the runtime cannot resolve it, which is why so many MDM "
                "paths look broken. Separately, GET on the record-by-id endpoint is genuinely contested — "
                "early testing recorded 200s, a later review concluded every runtime path 404s under "
                "correct auth and the earlier 200s were login HTML. Verify live before relying on it.")])

    svc(doc, "Operational Insights",
        "Documented, but GraphQL rather than REST — which is why REST-shaped probes found nothing.",
        V.VM_OI, path_w=3.9, note_w=2.2,
        notes=[("Only GET, and only two resources.",
                "Both resources are GET with the GraphQL query in the querystring. Headers are "
                "Authorization: Bearer <session_id>, Content-Type application/json, and Accept text/csv "
                "(omit for JSON). One documentation defect to expect: the guide says GET but both worked "
                "examples show a JSON request body containing the query, and one printed example is "
                "invalid JSON as shown."),
               ("Three governors to design around.",
                "13 months of history for processJobReport and one month for other resources; data "
                "retained 13 months; and only ONE active request at a time per organization. There is no "
                "pagination at all, so narrowing start, end, env and status is the only lever on a large "
                "result. The full schema is withheld and lives in Informatica KB article 000259754.")])

    svc(doc, "Data Access Management, API Manager & CLAIRE",
        "Engines deployed, REST planes absent. Plus the genuine entitlement questions.",
        V.VM_OTHER, path_w=3.0, note_w=3.1,
        notes=[("Uniform 404 across all verbs is itself the finding.",
                "DAM and API Manager both run engines on both Secure Agents with privileges present, yet "
                "roughly 40 DAM policy paths and every API Manager path return 404 on every verb. Record "
                "these as UI-only with the engine ready, not as purchases. The API Developer Portal is "
                "the cleanest candidate for a real entitlement gap, and CLAIRE GPT plus AI Agent "
                "Engineering remain contested: no agentic engine in either agent's stack and every path "
                "404s, but the licence console reportedly shows both entitled.")])

    # ================= PART 2 =================
    h1(doc, "Part 2  —  API vs MCP")
    body(doc, "This is the question the first document did not answer cleanly enough: what is available "
              "through the REST API, what is available through MCP, and where do they differ. The short "
              "answer is that MCP is a small, curated, mostly-read subset of REST — with two genuine "
              "exceptions where MCP can do something REST cannot.", size=9.5)

    h2(doc, "They are not the same kind of thing")
    body(doc, "Before comparing capabilities it is worth being precise about the structural difference, "
              "because it changes how you think about verbs entirely.", size=9.5)
    plain_table(doc, ["Dimension", "REST API", "MCP"], V.API_VS_MCP_SHAPE,
                [2.1, 3.9, 3.9], fontsize=8.5)

    callout(doc, "The verb question does not apply to MCP.",
            "This is the single most important thing to understand about the comparison. MCP has no "
            "GET/POST/PUT/PATCH/DELETE surface of its own — every MCP call is an HTTP POST to a single "
            "server endpoint, carrying a JSON-RPC body that names an action. The read-or-write intent "
            "lives in the action name, not in a verb. So Part 1's verb matrix is a REST concept; for MCP "
            "the equivalent question is 'which actions exist, and does each one read or write'. That is "
            "the table below.")

    h2(doc, "All 11 MCP actions, and their REST equivalent")
    body(doc, "Five Informatica-managed servers expose eleven actions between them. Eight read, one "
              "creates, two execute.", size=9.5, italic=True, color=GREY)
    plain_table(doc,
                ["MCP server", "Action", "Intent", "REST equivalent", "Same?", "Which is better, and why"],
                V.MCP_TO_REST,
                [1.4, 1.65, 0.72, 2.35, 0.72, 3.06],
                mono_cols=(1, 3), color_cols=(4,), fontsize=7.5)

    callout(doc, "Read that Same? column carefully — it is the whole answer.",
            "Seven of eleven MCP actions are thin wrappers over a REST endpoint you could call directly, "
            "and in several cases REST is strictly more capable: Elasticsearch DSL instead of one search "
            "string, 1,000 addresses per call instead of one, full job history instead of a single job. "
            "Two actions have no REST equivalent at all and are the real reason to use MCP. One is "
            "disputed, and one is partial.")

    h2(doc, "The two things MCP can do that REST cannot")
    bullet(doc, "Read asset lineage. get_asset_details returns lineage, profile and full descriptions in "
                "one call. On the REST side every lineage path — 25-plus variants across data360, graph, "
                "relationship and knowledgegraph — returns 404. If you need lineage programmatically, MCP "
                "is currently the only way to get it.")
    bullet(doc, "Fuzzy-match a customer identity. search_master_record uses MDM's matching algorithms to "
                "find a record despite typos or nicknames — the vendor's own example is finding 'Jon "
                "Smyth' when searching 'John Smith'. REST has no public search or list resource on MDM at "
                "all, so this capability simply is not available over REST.")
    body(doc, "Both exceptions are in the same family: they are read operations over governed metadata "
              "where the REST surface is genuinely missing. That is consistent with what Informatica's "
              "product team said — catalog and MDM have richer API coverage than integration, and MCP is "
              "where the newer surface is landing first.", size=9.5)

    h2(doc, "Capability by capability — API, MCP, or neither")
    body(doc, "Thirty-one capabilities. The last nine rows are the ones worth reading first: they are "
              "available through neither, which means a human in a browser.", size=9.5, italic=True,
         color=GREY)
    plain_table(doc,
                ["Capability", "REST API", "MCP", "Notes"],
                V.CAP_COMPARE,
                [3.0, 0.85, 0.72, 5.28],
                color_cols=(1, 2), fontsize=7.5)

    callout(doc, "The shape of the answer.",
            "REST can do far more than MCP — connections, scans, publishing, scheduling, process control, "
            "record ingest, dictionary CRUD, all REST-only. MCP wins on exactly two things, lineage and "
            "fuzzy identity match, plus it is the safer path for reading an MDM golden record while the "
            "REST GET stays contested. And there is a third category that neither reaches: authoring a "
            "mapping, accepting a classification, writing a glossary term, assigning a steward, deploying "
            "a business entity, authoring an ingestion task. Those are UI work regardless of which "
            "interface you prefer.")

    h2(doc, "So which should you use?")
    bullet(doc, "Building a pipeline, an integration or any unattended automation — use REST. It has the "
                "verbs, the write surface and twenty years of coverage.")
    bullet(doc, "Building an agent that needs to reason about the catalog — use MCP for discovery and "
                "lineage, then hand off to REST for anything that acts. The two compose well.")
    bullet(doc, "Needing lineage or fuzzy identity resolution programmatically — MCP is the only option "
                "today.")
    bullet(doc, "Needing to author a design-time asset — neither will help. That is the platform "
                "boundary, and Informatica has said API mapping design is previewed for late 2026 with "
                "GA around 2027.")

    h2(doc, "Practical notes on the MCP side")
    bullet(doc, "Protocol 2025-06-18, streamable HTTP transport. Informatica calls the tools 'actions'.")
    bullet(doc, "Three auth methods, all documented: IDS-SESSION-ID header, Bearer JWT, or OAuth2 client "
                "credentials. The OAuth client lifecycle — create, regenerate secret, disable — is "
                "entirely UI work in AI Agent Engineering.")
    bullet(doc, "MCP is not separately metered during the AI Agent Engineering preview, but the servers "
                "call IDMC service APIs underneath and that consumption incurs IPUs at your normal rate "
                "card. Budget it as the underlying service.")
    bullet(doc, "Server availability is per-org. Of the five published servers, a live sweep of one lab "
                "tenant found only two exposed. The documented catalog is the ceiling, not a guarantee.")
    bullet(doc, "Privileges: the asset privileges MCP Server and Deployed MCP Server, plus the feature "
                "privileges Execute Managed MCP Servers and View Managed MCP Servers. Granted by default "
                "to Admin and Designer; Operator can run but not create.")

    # ---------- PROVENANCE ----------
    h1(doc, "Provenance & how to re-verify")
    body(doc, "Every YES traces to a recorded HTTP response from a live IDMC org. Every DOC traces to a "
              "named Informatica April-2026 guide, listed in the companion document's sources section. "
              "Every blank is an honest gap.", size=9.5)
    h2(doc, "The two evidence classes, kept separate")
    bullet(doc, "Vendor documentation — official Informatica guides. Durable; will not change when a pod "
                "is reconfigured.")
    bullet(doc, "Live testing — roughly 250 verb-and-path combinations against a trial org (Org A, on a "
                "dm-us pod) between 28 June and 25 July 2026, plus a second org on a different pod. A "
                "dated snapshot: verdicts in this corpus flipped on a three-to-five-day cadence.")
    callout(doc, "Before you put any specific row in front of a customer.",
            "Re-probe it. Endpoint availability genuinely varies by pod, org and entitlement — that is "
            "not a hedge, it is the single most repeated lesson in this project. The probe harness in "
            "the archived corpus evidence (probe_idmc_surface.py) is GET-only by default and re-dates any live row.")
    h2(doc, "Companion document")
    body(doc, "This document answers 'which verbs, and API or MCP'. The IDMC API & MCP Capability "
              "Reference in the same folder covers the wider context: authentication planes, the status-code "
              "decoder ring, documented caps and throttles, the consolidated UI-only walls, and the nine "
              "corrections where earlier beliefs turned out to be wrong. Read that one for the why; use "
              "this one at the keyboard.", size=9.5)

    os.makedirs(OUT_DIR, exist_ok=True)
    doc.save(OUT)
    print("WROTE:", OUT)
    print("size:", os.path.getsize(OUT))
    d2 = Document(OUT)
    print("tables:", len(d2.tables), "rows:", sum(len(t.rows) - 1 for t in d2.tables))


if __name__ == "__main__":
    build()
