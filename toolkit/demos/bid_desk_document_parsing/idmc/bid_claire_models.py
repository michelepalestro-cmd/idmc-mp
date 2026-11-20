#!/usr/bin/env python3
"""bid_claire_models.py - the two CLAIRE intelligent structure models (bid packet, signature page), headless.

    python bid_claire_models.py show                        # the models in the project (read-only)
    python bid_claire_models.py discover <bid|sig>          # CLAIRE discovers the structure of the sample (saves nothing in IDMC)
    python bid_claire_models.py create <bid|sig> [--execute --expect-org <orgIdV3>]   # discover + save in folder 2
    python bid_claire_models.py update <bid|sig> [--execute ...]   # re-learn, store under the SAME id (mappings keep their binding)
    python bid_claire_models.py fields <bid|sig>            # the model's output fields + a proposed map onto the Bronze columns
    ... --sample <pdf>                                      # learn from another file (default: claire.<key>.train_on in config)

The six calls (KB CDI 02 section 10, L-CDI-223/224; PROVEN 2026-10-06 and 2026-10-13), all on https://<pod>.<domain>...:
  1 GET  /saas/api/v2/intelligentstructure/getAtlanticWidget      header icSessionId -> icsUUID
  2 POST /structurediscovery-service/atlweb/api/v3.0/validateWidget   empty body; cookie USER_SESSION=<v2 session> AND header
       IDS-SESSION-ID: <v2 session> (the cookie alone answers 200 {"valid": false}: a refusal dressed as success)
       -> {"valid": true} + service cookies (JSESSIONID, XSRF-TOKEN...). Then GET /structurediscovery-service/getVersion.
  3 POST /structurediscovery-service/upload?<resumable params>    multipart (the same params as form fields + part 'file');
       headers X-CSRF-TOKEN = the XSRF-TOKEN cookie, X-CSRF-PARAM: _csrf, X-Ajax-call: true on EVERY later POST
       (without it Tomcat answers 404, not 403) -> inputText + learnerUsed (PdfToModel for a PDF)
  4 POST .../RunDataPreview   form runData={fileName, text: inputText, key, learnerUse, treeType: horizontal, ...} -> aModelString
  5 POST .../getStructure     form formData={name, description, learnerUse, fileName, aModelString (TUNED, below), ...}
  6 POST /saas/api/v2/intelligentstructure/create?containerId=<v3 folder id>
       {"orgId": <orgIdV3>, "@type": "structureDefinition", "id", "name", "modelName", "description", "amodel": <step 5 JSON as text>}
  update = POST /saas/api/v2/intelligentstructure/<v2 id> with the same body shape (the editor's Save); read back after.
Tuning (step 5 input): every value CLAIRE typed (number, date, phone...) becomes text, so Bronze keeps exactly what the PDF
says (01702 stays 01702; Silver types it); every text block CLAIRE kept to itself (isExport 0) is exported, so no line of the
document is lost; projectToSeparateGroup 0 keeps ONE output group, the document's fields on every row (L-CDI-229).
Train on the COMPLETED sample (config claire.<key>.train_on = whatif) so every field exists even where the original is blank.
Do not follow the unauthenticated 302 (it points at plain http and times out behind a proxy).
"""
from __future__ import annotations

import base64
import http.client
import json
import mimetypes
import re
import ssl
import sys
import time
import urllib.parse
import uuid
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

SD = "/structurediscovery-service"
TYPED = ("number", "date", "time", "city", "state", "phone", "text")
CANON = {
    "bid": ["COMPANY_BIDDER", "BID_CONTACT", "BID_CONTACT_EMAIL", "BID_CONTACT_PHONE", "SALES_CONTACT", "SERVICE_CONTACT",
            "TIME_TO_DELIVER", "SIGNATURE", "PAYMENT_TERMS", "BIDDER", "ITEM_NO", "ITEM_DESCRIPTION", "UNIT", "QTY_NEEDED",
            "UNIT_PRICE", "BRAND_BID", "CURRENT_PRODUCT", "BID_NOTES"],
    "sig": ["COMPANY_NAME", "ADDRESS", "CITY", "STATE", "ZIP_CODE", "PHONE", "COMPANY_EMAIL", "DELIVERY_DAYS", "PAYMENT_NET_DAYS",
            "REP_NAME", "REP_EMAIL", "SIGNATURE", "REVISED_DATE"]}
ALIAS = {"DESCRIPTION": "ITEM_DESCRIPTION", "COMPANY_E_MAIL_ADDRESS": "COMPANY_EMAIL", "COMPANY_BIDDER": "COMPANY_BIDDER",
         "AUTHORIZED_REPRESENTATIVE_PRINT_NAME": "REP_NAME", "AUTHORIZED_REPRESENTATIVE_DIRECT_EMAIL": "REP_EMAIL",
         "AUTHORIZED_REPRESENTATIVE_SIGNATURE": "SIGNATURE", "SIGNATURE_OF_COMPANY_OFFICIAL": "SIGNATURE",
         "CUSTOMER_SERVICE_CONTACT": "SERVICE_CONTACT", "PAYMENT_TERMS_NET_DAYS": "PAYMENT_NET_DAYS"}
PASS = {"CONTENT_VERSION_ID": "CONTENT_VERSION_ID", "AGENCY": "AGENCY", "TITLE": "TITLE", "SOLICITATION_NO": "SOLICITATION_NO",
        "VERSION_NUMBER": "VERSION_NUMBER", "FILE_NAME": "FILE_NAME", "x_ism": "ISM_NAME", "x_run": "IDMC_RUN_ID", "x_ts": "LOADED_AT"}
TEXT_SLOTS = {"bid": 20, "sig": 10}


def tune(ams):
    head, b64 = ams.split("|", 1)
    m = json.loads(zlib.decompress(base64.b64decode(b64)))
    changed = []

    def walk(stmt):
        for c in stmt.get("statementChildren", []):
            if c.get("statementType") == "STRING" and c.get("type") in TYPED:
                c.pop("typeFormat", None)
                c["type"] = "token"
                c["precision"] = str(max(int(c.get("precision") or 0), 255))
                changed.append(c["name"])
            if str(c.get("isExport")) == "0":
                c["isExport"] = 1
                changed.append(c["name"] + " (exported)")
            if str(c.get("projectToSeparateGroup")) == "1":
                c["projectToSeparateGroup"] = 0
            walk(c)
    walk(m["rmodel"]["script"])

    def node(mt):
        tag = mt.group(0)
        if not re.search(r'\stype="(%s)"' % "|".join(TYPED), tag):
            return tag
        tag = re.sub(r'\s(type|typeFormat|scale)="[^"]*"', "", tag)
        tag = re.sub(r'\sbasicType="[^"]*"', ' basicType="STRING"', tag)
        tag = re.sub(r'\sprecision="[^"]*"', "", tag)
        return tag.replace(' basicType="STRING"', ' basicType="STRING" precision="255"', 1)
    m["rmodel"]["serializedTree"] = re.sub(r"<Node\b[^>]*/>", node, m["rmodel"]["serializedTree"])
    print("  tuned:", changed)
    return head + "|" + base64.b64encode(zlib.compress(json.dumps(m, separators=(",", ":")).encode())).decode()


class SDClient:
    """the Structure Discovery service: session as cookie AND header, then X-CSRF-TOKEN on every POST"""

    def __init__(self, ctx):
        self.sid = ctx.S.v2()["sid"]
        self.host = urllib.parse.urlparse(ctx.S.hosts()["pod"]).netloc
        self.jar = {"USER_SESSION": self.sid}
        self.extra = {}
        r = ctx.read("v2", "/api/v2/intelligentstructure/getAtlanticWidget")
        if not C.ok(r):
            C.H.die("getAtlanticWidget HTTP %s" % (r.status if r else "?"))
        st, d = self.req("POST", SD + "/atlweb/api/v3.0/validateWidget", b"",
                         headers={"IDS-SESSION-ID": self.sid, "X-Requested-With": "XMLHttpRequest", "Origin": "https://" + self.host})
        if st != 200 or json.loads(d or b"{}").get("valid") is not True:
            C.H.die("validateWidget not valid (HTTP %s): the session must be BOTH cookie and header" % st)
        self.extra = {"X-Ajax-call": "true", "X-CSRF-PARAM": "_csrf", "X-CSRF-TOKEN": self.jar.get("XSRF-TOKEN", "")}
        self.req("GET", SD + "/getVersion", ctype="application/x-www-form-urlencoded; charset=utf-8")

    def req(self, method, path, body=None, ctype=None, headers=None, timeout=300):
        h = {"Accept": "application/json, text/plain, */*", "Cookie": "; ".join("%s=%s" % kv for kv in self.jar.items())}
        if ctype:
            h["Content-Type"] = ctype
        if "XSRF-TOKEN" in self.jar and self.extra:
            self.extra["X-CSRF-TOKEN"] = self.jar["XSRF-TOKEN"]
        h.update(self.extra)
        h.update(headers or {})
        # certificate and hostname verification on (system CA store)
        c = http.client.HTTPSConnection(self.host, timeout=timeout, context=ssl.create_default_context())  # nosemgrep: python.lang.security.audit.httpsconnection-detected.httpsconnection-detected
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        data = r.read()
        for k, v in r.getheaders():
            if k.lower() == "set-cookie":
                n, val = v.split(";", 1)[0].split("=", 1)
                self.jar[n.strip()] = val.strip()
        return r.status, data

    def form(self, path, fields):
        return self.req("POST", SD + path, urllib.parse.urlencode(fields).encode(), "application/x-www-form-urlencoded; charset=UTF-8")

    def upload(self, fname, data, mime):
        n, dg = len(data), str(uuid.uuid4())
        ident = "%d-%s" % (n, "".join(ch for ch in fname if ch.isalnum() or ch == "-"))
        q = [("resumableChunkNumber", 1), ("resumableChunkSize", 1048576), ("resumableCurrentChunkSize", n), ("resumableTotalSize", n),
             ("resumableType", mime), ("resumableIdentifier", ident), ("resumableFilename", fname), ("resumableTotalChunks", 1),
             ("withCredentials", "true"), ("useXDomain", "true"), ("flowChunkNumber", 1), ("flowChunkSize", n),
             ("flowCurrentChunkSize", n), ("flowTotalSize", n), ("flowIdentifier", "%d_%s" % (n, fname)), ("flowFilename", fname),
             ("flowRelativePath", fname), ("flowTotalChunks", 1), ("isExport", "false"), ("isUpdateSample", "false"),
             ("isUpdateXmlSample", "false"), ("dataGuid", dg), ("learnMethods", ""), ("isExternalModel", "false"),
             ("learnFromEntireInput", "false"), ("resumableRelativePath", "undefined")]
        b = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
        parts = [("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode() for k, v in q]
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                      % (b, fname, mime)).encode() + data + b"\r\n")
        parts.append(("--%s--\r\n" % b).encode())
        return self.req("POST", SD + "/upload?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote), b"".join(parts),
                        "multipart/form-data; boundary=" + b)


def sample_for(cfg, key, override=None):
    if override:
        return Path(override)
    ag = next(x for x in cfg["salesforce"]["agencies"] if x["doc_type"] == ("Bid packet" if key == "bid" else "Signature page"))
    return C.BP / ag[cfg["claire"][key].get("train_on", "whatif")]


def describe(cfg, key):
    return ("%s: CLAIRE model of the %s (synthetic sample), learned from the document itself."
            % (cfg["idmc"]["project"], "bid packet: invitation, terms, Bid Proposal Page, bid form" if key == "bid"
               else "signature page: the required vendor form"))


def discover(ctx, key, sample):
    cfg = ctx.cfg
    name, path = cfg["claire"][key]["model"], sample_for(cfg, key, sample)
    if ctx.offline:
        print("[OFFLINE] would run calls 1-5 on %s (%d bytes) for model %r" % (path.name, path.stat().st_size, name))
        return name, None
    c = SDClient(ctx)
    data, fname = path.read_bytes(), path.name
    safe = "".join(ch if (ch.isalnum() or ch in " _.()") else "_" for ch in fname)
    st, d = c.upload(safe, data, mimetypes.guess_type(fname)[0] or "application/pdf")
    up = json.loads(d or b"{}")
    if st != 200 or not up.get("inputText"):
        C.H.die("upload HTTP %s: %s" % (st, str(up)[:300]))
    run = {"fileName": safe, "text": up["inputText"], "learnFromEntireInput": False, "key": str(uuid.uuid4()),
           "learnerUse": up.get("learnerUsed") or "", "treeType": "horizontal", "dataFromExternal": up.get("dataFromExternal", ""),
           "powerCenterMode": "NONE", "fastExcelMode": False, "hiddenSheetsOn": False}
    st, d = c.form("/RunDataPreview", {"runData": json.dumps(run, separators=(",", ":"))})
    pv = json.loads(d or b"{}")
    if st != 200 or not pv.get("aModelString"):
        C.H.die("RunDataPreview gave no model: HTTP %s" % st)
    now = int(time.time() * 1000)
    form = {"name": name, "additionaSamples": [], "additionalFileNames": [], "description": describe(cfg, key),
            "learnerUse": up.get("learnerUsed") or "", "fileName": safe, "date": now, "updated": now, "text": "",
            "learnFromEntireInput": False, "aModelString": tune(pv["aModelString"]), "uniqueId": str(uuid.uuid4()),
            "treeType": "horizontal"}
    st, d = c.form("/getStructure", {"formData": json.dumps(form, separators=(",", ":")), "dataGuid": "", "fileName": safe})
    gs = json.loads(d or b"{}")
    if st != 200 or "structure" not in gs:
        C.H.die("getStructure refused: HTTP %s %s" % (st, str(gs)[:300]))
    print("%s (%s, learner %s): %d groups" % (name, fname, up.get("learnerUsed"), len(gs.get("groups", []))))
    for g in gs.get("groups", []):
        print("  group %-22s %s" % (g.get("name"), [f.get("name") for f in g.get("metaFields", [])]))
    return name, gs


def existing(ctx):
    prefix = ctx.cfg["idmc"]["project"] + "/"
    return {o["path"].rsplit("/", 1)[-1]: o for o in C.v3_objects(ctx, "SAAS_STRUCTURE_DISCOVERY", prefix)}


def norm(n):
    return re.sub(r"_+", "_", re.sub(r"[^A-Z0-9]", "_", str(n).upper())).strip("_")


def field_map(key, fields):
    canon, out, used, slot = CANON[key], dict(PASS), set(), 0
    for f in fields:
        n = norm(f)
        tgt = ALIAS.get(n) or (n if n in canon else None)
        if tgt and tgt not in used:
            out[f] = tgt
            used.add(tgt)
        elif slot < TEXT_SLOTS[key]:
            slot += 1
            out[f] = "TEXT_%02d" % slot
    return out


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["show", "discover", "create", "update", "fields"])
    ap.add_argument("key", nargs="?", choices=["bid", "sig"])
    ap.add_argument("--sample")
    a = ap.parse_args()
    ctx = C.Ctx(a)
    cfg, st = ctx.cfg, C.state()
    if a.cmd != "show" and not a.key:
        C.H.die("name the model: bid or sig")
    if a.cmd == "show":
        for n, o in sorted(existing(ctx).items()):
            print(n, o["id"])
        return
    if a.cmd == "discover":
        discover(ctx, a.key, a.sample)
        return
    model = st.get("claire", {}).get(a.key, {})
    if a.cmd == "fields":
        if not model.get("v2"):
            print("[%s] model not built yet; the map will use the fields of the model once created" % a.key)
            return
        r = ctx.read("v2", "/api/v2/intelligentstructure/" + model["v2"])
        out = [f.get("name") for f in (r.json({}) or {}).get("outputFields") or []] if r is not None else []
        fm = field_map(a.key, out)
        print(json.dumps(fm, indent=1))
        unmapped = sorted(set(CANON[a.key]) - set(fm.values()))
        print("canonical columns with no model field (the SQL label regex fills them):", unmapped)
        if not ctx.offline:
            st.setdefault("claire_field_map", {})[a.key] = fm
            C.save_state(st)
        return
    have = existing(ctx)
    name = cfg["claire"][a.key]["model"]
    folder = st.get("folders", {}).get("f2", "<folder f2 id>")
    if a.cmd == "create":
        if name in have:
            print("exists:", name, have[name]["id"], "(use update to re-learn)")
            return
        name, gs = discover(ctx, a.key, a.sample)
        body = {"orgId": "<orgIdV3>" if ctx.offline else ctx.S.v2().get("orgUuid"), "@type": "structureDefinition",
                "id": uuid.uuid4().hex[:10], "modelName": name, "name": name, "description": describe(cfg, a.key),
                "amodel": json.dumps(gs, separators=(",", ":")) if gs else "<getStructure JSON as text>"}
        r = ctx.write("create CLAIRE model", "v2", "POST", "/api/v2/intelligentstructure/create?containerId=%s" % folder, body=body)
        if C.ok(r):
            d = r.json({}) or {}
            have = existing(ctx)
            st.setdefault("claire", {})[a.key] = {"v2": d.get("id"), "v3": (have.get(name) or {}).get("id"), "name": name}
            C.save_state(st)
            print("  output fields:", len(d.get("outputFields") or []), "-> next: bid_claire_models.py fields", a.key)
        return
    if not model.get("v2") and not ctx.offline:
        C.H.die("no model id in state for %s: create it first" % a.key)
    v2id = model.get("v2", "<v2 model id>")
    cur = ctx.read("v2", "/api/v2/intelligentstructure/" + v2id)
    m = cur.json({}) if cur is not None else {"@type": "structureDefinition", "id": v2id, "name": name, "modelName": name}
    name, gs = discover(ctx, a.key, a.sample)
    body = {k: m[k] for k in ("@type", "id", "orgId", "name", "description", "modelName") if k in m}
    body["amodel"] = json.dumps(gs, separators=(",", ":")) if gs else "<getStructure JSON as text>"
    r = ctx.write("update CLAIRE model (same id)", "v2", "POST", "/api/v2/intelligentstructure/" + v2id, body=body)
    if C.ok(r):
        back = ctx.read("v2", "/api/v2/intelligentstructure/" + v2id).json({})
        print("read back: %d output fields. Open each parse mapping and Synchronize the Structure Parser (it keeps a copy)"
              % len(back.get("outputFields") or []))


if __name__ == "__main__":
    main()
