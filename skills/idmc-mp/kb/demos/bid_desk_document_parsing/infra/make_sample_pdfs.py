#!/usr/bin/env python3
"""make_sample_pdfs.py - the four SYNTHETIC solicitation PDFs of the Bid Desk demo (fictional agencies, stdlib only).

    python make_sample_pdfs.py [--out DIR]     # default: infra/sample_docs (+ whatif/)
    python make_sample_pdfs.py --check         # rebuild in memory and compare with the shipped files (no write)

What it writes (text PDFs with real columns, so CLAIRE's PDF learner sees key/value fields and a table):
  ECPC-2031-07 Janitorial Bid Packet.pdf                      3 pages: invitation + terms, Bid Proposal Page (blank
                                                              fields), bid form (8 lines, unpriced). Two product numbers
                                                              are printed broken across a line ("ACME BH- 24548") on
                                                              purpose: the 'Product number on one line' rule catches them
  EUSD-31-RFQ-04 - EXHIBIT A - SIGNATURE PAGE.pdf             1 page: the required vendor form, every field blank
  whatif/... Bid Packet (completed).pdf                       every line priced, with two slips the DQ rules catch:
                                                              one price with 3 decimals, one line without a brand
  whatif/... SIGNATURE PAGE (completed).pdf                   every vendor field filled in and signed
Every value is fictional. Agencies: "Example County Purchasing Cooperative", "Example Unified School District".
Every completed page is stamped SAMPLE.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "sample_docs"
BLANK = "_" * 28

LINES = [  # item no, description, unit, qty, current product (as printed), notes
    ("50101", "Trash can liners, 40-45 gal, black", "CASE", "120", "ACME BH- 24548", "ACME brand preferred"),
    ("50102", "Paper towels, roll, 2-ply", "CASE", "80", "NORTHFIELD NF-1180", ""),
    ("50103", "Toilet tissue, 2-ply, 500 sheets", "CASE", "150", "NORTHFIELD NF-2202", ""),
    ("50104", "Glass cleaner, 32 oz spray", "EACH", "60", "BRIGHTWAY BW-3301", ""),
    ("50105", "Floor finish, 5 gal", "EACH", "12", "BRIGHTWAY BW- 4410", "low odor"),
    ("50106", "Hand soap refill, 1000 ml", "CASE", "40", "PUREHAND PH-5102", ""),
    ("50107", "Microfiber cloths, 16 in", "5-PK", "90", "ACME AC-6120", ""),
    ("50108", "Disinfectant wipes, 80 ct", "2-PK", "70", "PUREHAND PH-7215", "PUREHAND brand preferred"),
]
PRICES = ["24.85", "31.20", "38.75", "3.10", "6.345", "22.40", "9.95", "7.60"]          # line 5: three decimals (a slip)
BRANDS = ["ACME BH-24548", "NORTHFIELD NF-1180", "NORTHFIELD NF-2202", "BRIGHTWAY BW-3301", "BRIGHTWAY BW-4410",
          "PUREHAND PH-5102", "", "PUREHAND PH-7215"]                                    # line 7: no brand (a slip)
PROPOSAL = [("Company / Bidder", "Sample Office Supply Co. (SAMPLE)"), ("Bid Contact", "Jordan Sample"),
            ("Bid Contact Email", "jordan.sample@example.com"), ("Bid Contact Phone", "555-0100"),
            ("Sales Contact", "Riley Example"), ("Customer Service Contact", "Casey Placeholder"),
            ("Time to Deliver", "5 business days"), ("Signature of Company Official", "/s/ Jordan Sample")]
EXHIBIT = [("Company Name (include dba if applicable)", "Sample Office Supply Co. (SAMPLE)"),
           ("Address", "100 Example Way"), ("City", "Sampleton"), ("State", "EX"), ("Zip Code", "00000"),
           ("Phone", "555-0100"), ("Company E-Mail Address", "bids@example.com"),
           ("Delivery will be completed in (days after receipt of order)", "5"), ("Payment Terms: NET (days)", "30"),
           ("Authorized Representative (Print Name)", "Jordan Sample"),
           ("Authorized Representative Direct Email", "jordan.sample@example.com"),
           ("AUTHORIZED REPRESENTATIVE SIGNATURE", "/s/ Jordan Sample (certified e-signature)")]


# ------------------------------------------------------------------ a tiny PDF writer
def esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class Page:
    def __init__(self):
        self.ops = []

    def text(self, x, y, s, size=10, bold=False):
        self.ops.append("BT /%s %d Tf %d %d Td (%s) Tj ET" % ("F2" if bold else "F1", size, x, y, esc(s)))

    def line(self, x1, y1, x2, y2):
        self.ops.append("%d %d m %d %d l S" % (x1, y1, x2, y2))

    def stamp(self):
        self.text(430, 770, "SAMPLE - fictional values", 9, True)


def pdf(pages, title):
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
            "<< /Title (%s) /Producer (Bid Desk blueprint sample generator) >>" % esc(title)]
    kids = []
    for p in pages:
        stream = "\n".join(["0.5 w"] + p.ops).encode("latin-1")
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
                    "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>" % len(objs))
        kids.append(len(objs))
    objs[1] = "<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join("%d 0 R" % k for k in kids), len(kids))
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        body = o if isinstance(o, bytes) else o.encode("latin-1")
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 5 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    return bytes(out)


# ------------------------------------------------------------------ the documents
def bid_packet(completed):
    p1, p2, p3 = Page(), Page(), Page()
    for p in (p1, p2, p3):
        p.text(50, 750, "Example County Purchasing Cooperative", 14, True)
        p.text(50, 734, "Purchasing Department - 1 Sample Plaza, Example City, EX 00000", 9)
        if completed:
            p.stamp()
    p1.text(50, 700, "INVITATION TO BID", 13, True)
    rows = ["Bid #ECPC-2031-07 Janitorial Supplies Bid Proposal Page",
            "Bid & Samples Due: 03/14/31 at 10:00 AM",
            "Bid Opening: 03/14/31 at 2:00 PM",
            "Contract term: from January 1, 2032 to December 31, 2032",
            "Payment Terms: Net 30",
            "All prices are to be F.O.B. Cooperative Warehouse, Example City",
            "Only TWO decimal places will be counted. Longer prices are rounded up.",
            "Delivery will be expected within 30 days of the purchase order.",
            "The Cooperative is exempt from all State Sales Tax.",
            "Required attachments: W-9, three references for a new vendor, the signed Bid Proposal Page.",
            "Questions: Email: purchasing@example.org"]
    for i, r in enumerate(rows):
        p1.text(50, 670 - 22 * i, r, 10)
    p2.text(50, 700, "BID PROPOSAL PAGE", 13, True)
    for i, (k, v) in enumerate(PROPOSAL):
        y = 660 - 34 * i
        p2.text(50, y, k + ":", 10, True)
        p2.text(250, y, v if completed else BLANK, 10)
    p3.text(50, 700, "BID FORM", 13, True)
    cols = [(40, "Item No"), (90, "Description"), (250, "Unit"), (290, "Qty Needed"), (350, "Unit Price"),
            (410, "Brand Bid"), (500, "Current Product")]
    for x, h in cols:
        p3.text(x, 670, h, 8, True)
    p3.line(36, 664, 590, 664)
    for i, (no, desc, unit, qty, cur, note) in enumerate(LINES):
        y = 646 - 30 * i
        vals = [no, desc, unit, qty, PRICES[i] if completed else "", BRANDS[i] if completed else "", cur]
        for (x, _), v in zip(cols, vals):
            if v:
                p3.text(x, y, v, 8)
        if note:
            p3.text(500, y - 10, note, 7)
        p3.line(36, y - 14, 590, y - 14)
    p3.text(50, 380, "Bidder: " + ("Sample Office Supply Co. (SAMPLE)" if completed else BLANK), 10)
    return pdf([p1, p2, p3], "ECPC-2031-07 Janitorial Bid Packet")


def signature_page(completed):
    p = Page()
    p.text(50, 750, "Example Unified School District", 14, True)
    p.text(50, 734, "Procurement Services - 200 Sample Avenue, Example City, EX 00000", 9)
    if completed:
        p.stamp()
    p.text(50, 705, "EXHIBIT A - SIGNATURE PAGE (REQUIRED FORM)", 12, True)
    p.text(50, 685, "SOLICITATION TITLE: Classroom Paper Supplies SOLICITATION #: EUSD-31-RFQ-04", 10)
    for i, (k, v) in enumerate(EXHIBIT):
        y = 650 - 38 * i
        p.text(50, y, k + ":", 9, True)
        p.text(330, y, v if completed else BLANK, 9)
    p.text(50, 180, "Unsigned forms will result in automatic rejection.", 9)
    p.text(50, 166, "Certified electronic digital signatures are acceptable.", 9)
    p.text(50, 152, "Form revised 01/2031", 8)
    return pdf([p], "EUSD-31-RFQ-04 Exhibit A Signature Page")


def build():
    return {
        "ECPC-2031-07 Janitorial Bid Packet.pdf": bid_packet(False),
        "EUSD-31-RFQ-04 - EXHIBIT A - SIGNATURE PAGE.pdf": signature_page(False),
        "whatif/ECPC-2031-07 Janitorial Bid Packet (completed).pdf": bid_packet(True),
        "whatif/EUSD-31-RFQ-04 - EXHIBIT A - SIGNATURE PAGE (completed).pdf": signature_page(True),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check", action="store_true", help="compare with the shipped files, write nothing")
    a = ap.parse_args()
    out, bad = Path(a.out), 0
    for rel, data in build().items():
        p = out / rel
        if a.check:
            same = p.exists() and p.read_bytes() == data
            bad += not same
            print("%-4s %s (%d bytes)" % ("OK" if same else "DIFF", rel, len(data)))
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        print("wrote %s (%d bytes)" % (rel, len(data)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
