#!/usr/bin/env python3
"""bid_tableau.py - ONE Tableau workbook for the Bid Desk, one tab (dashboard) per topic, built from the Snowflake BI views and
published over the Tableau REST API. Stdlib only.

    python bid_tableau.py build                 # writes dashboards/out/<workbook>.twb (live Snowflake connection, no extract)
    python bid_tableau.py publish [--execute]   # build + sign in (PAT) + find/create the project + publish (overwrite) + list views
    python bid_tableau.py status                # the workbook on the server and its views (read-only)

Tabs (one dashboard each, every sheet a text table of one BI view; never a blank section: each view returns rows once the
pipeline has run and the feeds were loaded):
  Bid Desk             BID_V_BI_DECISIONS (one card row per solicitation) + BID_V_BI_BID_LINES + BID_V_BI_FIELDS
  Data Quality         BID_V_BI_DQ (Data Profiling scorecard + the in-pipeline checks)
  Lineage              BID_V_BI_LINEAGE (the catalog's hops, fed by idmc/bid_catalog.py feed)
  Glossary and Governance  BID_V_BI_GLOSSARY (fed by idmc/bid_glossary.py feed)
  Mapping              BID_V_BI_PIPELINE (each IDMC step, what it reads and writes)
  Parsing              BID_V_BI_PARSING (what CLAIRE read from each document)
REST (Tableau Server 2021.4+ / Cloud; API version in config tableau.api_version):
  POST /api/<v>/auth/signin {"credentials":{"personalAccessTokenName","personalAccessTokenSecret","site":{"contentUrl"}}}
  GET  /api/<v>/sites/<site>/projects?filter=name:eq:<name>   (POST .../projects to create it)
  POST /api/<v>/sites/<site>/workbooks?overwrite=true   multipart/MIXED: part request_payload (text/xml) with
       <workbook name showTabs="true"><connections><connection serverAddress serverPort="443"><connectionCredentials name
       password embed="true"/></connection></connections><project id/></workbook> + part tableau_workbook (the .twb)
  GET  /api/<v>/sites/<site>/workbooks/<id>/views
Credentials: TABLEAU_PAT_NAME / TABLEAU_PAT_SECRET (sign-in), SNOWFLAKE_BI_USER / SNOWFLAKE_BI_PASSWORD (embedded, read-only
role BID_READER). Status: ADAPTED. The source demo published a .twbx with Hyper extracts; this live-connection .twb is new
and was not opened in Tableau in this form. If the server rejects it, open the .twb in Tableau Desktop, save, and publish.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from xml.sax.saxutils import quoteattr  # nosec B406  # escaping only, no parsing  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import bid_common as C  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
S, I, R = "string", "integer", "real"
TABS = [
    ("Bid Desk", [("Decisions", "BID_V_BI_DECISIONS", [("AGENCY", S), ("SOLICITATION_NO", S), ("DECISION", S), ("DETAIL", S),
                                                        ("BID_DUE", S), ("DQ_SCORE", R)]),
                  ("Bid Form", "BID_V_BI_BID_LINES", [("SOLICITATION_NO", S), ("ITEM_NO", S), ("ITEM_DESCRIPTION", S), ("UNIT", S),
                                                      ("UNIT_PRICE_TEXT", S), ("BRAND_BID", S), ("LINE_STATUS", S), ("LINE_ISSUE", S)]),
                  ("Required Forms", "BID_V_BI_FIELDS", [("SOLICITATION_NO", S), ("FORM_NAME", S), ("FIELD_NAME", S),
                                                         ("FIELD_VALUE", S), ("FIELD_STATUS", S)])]),
    ("Data Quality", [("Scorecard", "BID_V_BI_DQ", [("CHECKED_BY", S), ("LAYER", S), ("TABLE_NAME", S), ("COLUMN_NAME", S),
                                                    ("RULE_SPEC", S), ("DIMENSION", S), ("CHECKED", I), ("PASSED", I), ("SCORE_PCT", R)])]),
    ("Lineage", [("Lineage hops", "BID_V_BI_LINEAGE", [("VIEW_NAME", S), ("HOP", I), ("FROM_SYSTEM", S), ("FROM_TYPE", S),
                                                       ("FROM_NAME", S), ("TO_TYPE", S), ("TO_NAME", S)])]),
    ("Glossary and Governance", [("Glossary", "BID_V_BI_GLOSSARY", [("DOMAIN", S), ("TERM", S), ("DEFINITION", S), ("LINKED_ASSET", S)])]),
    ("Mapping", [("Pipeline steps", "BID_V_BI_PIPELINE", [("STEP", I), ("IDMC_OBJECT", S), ("KIND", S), ("WHAT_IT_DOES", S),
                                                          ("WRITES", S), ("LAYER", S)])]),
    ("Parsing", [("What CLAIRE read", "BID_V_BI_PARSING", [("AGENCY", S), ("SOLICITATION_NO", S), ("DOC_TYPE", S), ("VERSION_NUMBER", S),
                                                           ("ROWS_READ", I), ("SHAPE", S), ("REQUIRED_FIELDS_FOUND", I)])]),
]


def a(v):
    return quoteattr(str(v))


def twb(cfg, bi_user="<SNOWFLAKE_BI_USER>"):
    sf = cfg["snowflake"]
    server = "%s.snowflakecomputing.com" % sf["account"]
    ds, ws, db, win = [], [], [], []
    for tab, sheets in TABS:
        zones = []
        for i, (title, view, cols) in enumerate(sheets):
            dsn = "federated.%s" % view.lower()
            ds.append(
                "<datasource caption=%s inline='true' name=%s version='18.1'><connection class='federated'><named-connections>"
                "<named-connection caption=%s name='snowflake.bid'><connection authentication='Username Password' class='snowflake' "
                "dbname=%s schema=%s server=%s username=%s warehouse=%s service='' one-time-sql='' /></named-connection>"
                "</named-connections><relation connection='snowflake.bid' name=%s table=%s type='table' /></connection>%s</datasource>"
                % (a(title), a(dsn), a(server), a(sf["database"]), a(sf["schema"]), a(server), a(bi_user), a(sf["warehouse"]),
                   a(view), a("[%s].[%s]" % (sf["schema"], view)),
                   "".join("<column datatype=%s name=%s role='dimension' type=%s />" % (a(t), a("[%s]" % c), a("nominal" if t == S else "ordinal"))
                           for c, t in cols)))
            deps = "".join("<column datatype=%s name=%s role='dimension' type=%s /><column-instance column=%s derivation='None' "
                           "name=%s pivot='key' type=%s />" % (a(t), a("[%s]" % c), a("nominal" if t == S else "ordinal"), a("[%s]" % c),
                                                                a("[none:%s:%s]" % (c, "nk" if t == S else "ok")),
                                                                a("nominal" if t == S else "ordinal")) for c, t in cols)
            rows = " / ".join("[%s].[none:%s:%s]" % (dsn, c, "nk" if t == S else "ok") for c, t in cols)
            name = "%s - %s" % (tab, title)
            ws.append("<worksheet name=%s><table><view><datasources><datasource caption=%s name=%s /></datasources>"
                      "<datasource-dependencies datasource=%s>%s</datasource-dependencies><aggregation value='true' /></view><style />"
                      "<panes><pane><view><breakdown value='auto' /></view><mark class='Automatic' /></pane></panes>"
                      "<rows>%s</rows><cols /></table></worksheet>" % (a(name), a(title), a(dsn), a(dsn), deps, rows))
            h = 100000 // len(sheets)
            zones.append("<zone h=%s id=%s name=%s w='100000' x='0' y=%s />" % (a(h), a(i + 3), a(name), a(i * h)))
        db.append("<dashboard name=%s><style /><size maxheight='1400' maxwidth='1600' minheight='900' minwidth='1200' />"
                  "<zones><zone h='100000' id='1' type='layout-basic' w='100000' x='0' y='0'>%s</zone></zones></dashboard>"
                  % (a(tab), "".join(zones)))
        win.append("<window class='dashboard' name=%s />" % a(tab))
    return ("<?xml version='1.0' encoding='utf-8' ?>\n<workbook source-build='2021.4.0' source-platform='win' version='18.1' "
            "xmlns:user='http://www.tableausoftware.com/xml/user'><preferences /><datasources>%s</datasources><worksheets>%s"
            "</worksheets><dashboards>%s</dashboards><windows>%s</windows></workbook>\n"
            % ("".join(ds), "".join(ws), "".join(db), "".join(win)))


class Tab:
    def __init__(self, cfg):
        t = cfg["tableau"]
        self.server, self.v = t["server"].rstrip("/"), t["api_version"]
        st, d = self.req("POST", "/api/%s/auth/signin" % self.v, json.dumps({"credentials": {
            "personalAccessTokenName": C.env("TABLEAU_PAT_NAME"), "personalAccessTokenSecret": C.env("TABLEAU_PAT_SECRET"),
            "site": {"contentUrl": t.get("site", "")}}}).encode(), "application/json")
        if st != 200:
            C.H.die("Tableau sign-in HTTP %s" % st)
        c = d["credentials"]
        self.tok, self.site = c["token"], c["site"]["id"]
        self.base = "/api/%s/sites/%s" % (self.v, self.site)

    def req(self, method, path, body=None, ctype=None):
        h = {"Accept": "application/json"}
        if ctype:
            h["Content-Type"] = ctype
        if getattr(self, "tok", None):
            h["X-Tableau-Auth"] = self.tok
        rq = urllib.request.Request(self.server + path, data=body, method=method, headers=h)
        try:
            with C.urlopen(rq, timeout=180) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"raw": raw[:300].decode(errors="replace")}

    def project(self, name):
        st, d = self.req("GET", self.base + "/projects?filter=" + urllib.parse.quote("name:eq:" + name))
        ps = ((d.get("projects") or {}).get("project") or []) if st == 200 else []
        if ps:
            return ps[0]["id"]
        st, d = self.req("POST", self.base + "/projects", json.dumps({"project": {"name": name, "description": "Bid Desk demo"}}).encode(),
                         "application/json")
        return d["project"]["id"]

    def publish(self, cfg, name, pid, data):
        sf = cfg["snowflake"]
        payload = ("<tsRequest><workbook name=%s showTabs='true'><connections><connection serverAddress=%s serverPort='443'>"
                   "<connectionCredentials name=%s password=%s embed='true' /></connection></connections><project id=%s /></workbook>"
                   "</tsRequest>" % (a(name), a("%s.snowflakecomputing.com" % sf["account"]), a(C.env("SNOWFLAKE_BI_USER")),
                                     a(C.env("SNOWFLAKE_BI_PASSWORD")), a(pid)))
        b = uuid.uuid4().hex
        body = ("--%s\r\nContent-Disposition: name=\"request_payload\"\r\nContent-Type: text/xml\r\n\r\n%s\r\n--%s\r\n"
                "Content-Disposition: name=\"tableau_workbook\"; filename=\"bid_desk.twb\"\r\nContent-Type: application/octet-stream\r\n\r\n"
                % (b, payload, b)).encode() + data + ("\r\n--%s--\r\n" % b).encode()
        return self.req("POST", self.base + "/workbooks?overwrite=true", body, "multipart/mixed; boundary=%s" % b)


def main():
    ap = C.argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__,
                                   formatter_class=C.argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "publish", "status"])
    ap.add_argument("--config")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a_ = ap.parse_args()
    C.H.safe_console()
    cfg = C.load_config(a_.config)
    name = cfg["tableau"]["workbook"]
    if a_.cmd in ("build", "publish"):
        OUT.mkdir(exist_ok=True)
        user = C.env("SNOWFLAKE_BI_USER", required=False) if a_.execute else None
        p = OUT / (name.replace(" ", "_") + ".twb")
        p.write_text(twb(cfg, user or "<SNOWFLAKE_BI_USER>"), encoding="utf-8")
        print("built %s: %d tabs, %d sheets" % (p.relative_to(C.BP), len(TABS), sum(len(s) for _, s in TABS)))
        if a_.cmd == "build":
            return
        if not a_.execute or a_.offline:
            print("[DRY-RUN] would sign in to %s, ensure project %r, publish %r (overwrite), list its views"
                  % ("<tableau.server>", cfg["tableau"]["project"], name))
            return
        t = Tab(cfg)
        pid = t.project(cfg["tableau"]["project"])
        st, d = t.publish(cfg, name, pid, p.read_bytes())
        print("publish HTTP %s %s" % (st, (d.get("workbook") or {}).get("id") or str(d)[:300]))
        if st in (200, 201):
            wid = d["workbook"]["id"]
            st, v = t.req("GET", t.base + "/workbooks/%s/views" % wid)
            for x in ((v.get("views") or {}).get("view") or []):
                print("  view", x.get("name"))
        return
    if a_.offline:
        print("[OFFLINE] would list the workbook %r and its views" % name)
        return
    t = Tab(cfg)
    st, d = t.req("GET", t.base + "/workbooks?filter=" + urllib.parse.quote("name:eq:" + name))
    for w in ((d.get("workbooks") or {}).get("workbook") or []):
        print(w.get("name"), w.get("id"), w.get("updatedAt"))


if __name__ == "__main__":
    main()
