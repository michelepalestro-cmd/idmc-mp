#!/usr/bin/env python3
"""sf_files.py - the Bid Desk sample data in your Salesforce org, over Salesforce REST (stdlib only, self-contained).

    python sf_files.py seed   [--execute]        # the agencies (Accounts) + each sample PDF attached as a Salesforce File
    python sf_files.py status                    # the agencies and every version of their files (read-only)
    python sf_files.py ids                       # the ContentDocumentIds mapping 1 must filter on (paste into state)
    python sf_files.py whatif [bid|sig|both] [--execute]   # attach the completed copy as a NEW VERSION of the same file
    python sf_files.py reset  [--execute]        # attach the original again as a new version where the newest differs
    python sf_files.py stage --dir <folder>      # download the newest version of each file into <folder> (for 1b)

Why this script exists (the two places Python stays in the runtime path, both stated walls):
  * reset: the CDI Salesforce connector rejected a ContentVersion new-version insert (WRT_8164 REQUIRED_FIELD_MISSING
    [Title] with Title sent) while REST accepted the same five fields (KB L-CONN-115). So mapping 5's pre-processing
    command runs `sf_files.py reset` on the Secure Agent host; the mapping itself only logs the reset.
  * stage: the CDI SharePoint Online connector uploads a file's bytes from its connection's Attachment_File_Path on the
    agent; CDI cannot write a binary file there itself (KB L-CONN-107). Mapping 1b's pre-processing command runs
    `sf_files.py stage --dir <Attachment_File_Path>`; the mapping then does the transfer.
  Everything else (reading the CRM, parsing, DQ, decisions) runs in IDMC.

Nothing is ever deleted. Every file carries the description from config (salesforce.file_description).
Auth: a Connected App with the client-credentials flow: SF_INSTANCE_URL, SF_CLIENT_ID, SF_CLIENT_SECRET from the
environment or from --env-file (KEY=value lines; keep it 0600, outside the toolkit). Values are never printed.
Config: --config <config.json> (default: ../config.json, else ../config.example.json).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BP = Path(__file__).resolve().parents[1]


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Never re-send the Bearer token to another host on a 3xx, and refuse an https -> http downgrade
    (urllib's default handler copies every header to whatever Location the server names)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is None:
            return None
        o, n = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(new.full_url)
        if o.scheme == "https" and n.scheme != "https":
            raise urllib.error.HTTPError(req.full_url, code, "refused redirect from https to " + n.scheme, headers, fp)
        if (o.scheme, o.hostname, o.port) != (n.scheme, n.hostname, n.port):
            for d in (new.headers, new.unredirected_hdrs):
                for k in [k for k in d if k.lower() in ("authorization", "cookie")]:
                    del d[k]
        return new


OPENER = urllib.request.build_opener(SafeRedirect)


def load_env(path):
    out = dict(os.environ)
    if path and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out


class SF:
    def __init__(self, env, api):
        miss = [k for k in ("SF_INSTANCE_URL", "SF_CLIENT_ID", "SF_CLIENT_SECRET") if not env.get(k)]
        if miss:
            sys.exit("missing %s (environment or --env-file); values are never printed" % ", ".join(miss))
        self.base = env["SF_INSTANCE_URL"].rstrip("/")
        body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": env["SF_CLIENT_ID"],
                                       "client_secret": env["SF_CLIENT_SECRET"]}).encode()
        st, d = self._raw("POST", self.base + "/services/oauth2/token", body, "application/x-www-form-urlencoded", auth=False)
        if st != 200 or "access_token" not in d:
            sys.exit("Salesforce token: HTTP %s %s" % (st, str({k: v for k, v in d.items() if k != "access_token"})[:200]))
        self.tok, self.api = d["access_token"], "/services/data/v" + api

    def _raw(self, method, url, body=None, ctype="application/json", auth=True, binary=False):
        h = {"Accept": "application/json"}
        if body is not None:
            h["Content-Type"] = ctype
        if auth:
            h["Authorization"] = "Bearer " + self.tok
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            with OPENER.open(req, timeout=300) as r:
                data = r.read()
                return r.status, (data if binary else json.loads(data or b"{}"))
        except urllib.error.HTTPError as e:
            data = e.read()
            try:
                return e.code, json.loads(data)
            except ValueError:
                return e.code, {"raw": data[:300].decode(errors="replace")}

    def call(self, path, body=None, method=None):
        return self._raw(method or ("POST" if body is not None else "GET"), self.base + self.api + path,
                         json.dumps(body).encode() if body is not None else None)

    def query(self, soql):
        st, d = self.call("/query?q=" + urllib.parse.quote(soql))
        if st != 200:
            sys.exit("SOQL failed %s %s" % (st, str(d)[:300]))
        return d.get("records") or []

    def bytes_of(self, cv_id):
        st, d = self._raw("GET", self.base + self.api + "/sobjects/ContentVersion/%s/VersionData" % cv_id, binary=True)
        if st != 200:
            sys.exit("download %s: HTTP %s" % (cv_id, st))
        return d


def q(vals):
    """SOQL string literals: backslash first, then the single quote (SOQL escapes with a backslash)."""
    return ", ".join("'%s'" % v.replace("\\", "\\\\").replace("'", "\\'") for v in vals)


def agencies(sf, cfg):
    names = [a["name"] for a in cfg["salesforce"]["agencies"]]
    return {r["Name"]: r["Id"] for r in sf.query("SELECT Id, Name FROM Account WHERE Name IN (%s)" % q(names))}  # nosec B608  # SOQL; values escaped by q()


def documents(sf, acc_ids):
    if not acc_ids:
        return {}
    links = sf.query("SELECT ContentDocumentId, LinkedEntityId FROM ContentDocumentLink WHERE LinkedEntityId IN (%s)" % q(acc_ids))  # nosec B608  # SOQL; values escaped by q()
    docs = {l["ContentDocumentId"]: l["LinkedEntityId"] for l in links}
    if not docs:
        return {}
    vers = sf.query("SELECT Id, ContentDocumentId, Title, VersionNumber, Checksum, ContentSize, ReasonForChange, CreatedDate "
                    "FROM ContentVersion WHERE ContentDocumentId IN (%s) ORDER BY ContentDocumentId, VersionNumber" % q(list(docs)))  # nosec B608  # SOQL; values escaped by q()
    out = {}
    for v in vers:
        out.setdefault(v["ContentDocumentId"], {"account": docs[v["ContentDocumentId"]], "versions": []})["versions"].append(v)
    return out


def md5(p):
    """Salesforce ContentVersion.Checksum is an MD5 of the bytes: a change check the API dictates, not security."""
    return hashlib.md5(Path(p).read_bytes(), usedforsecurity=False).hexdigest()


def path_of(cfg, rel):
    p = Path(rel)
    return p if p.is_absolute() else BP / rel


def title_of(path):
    return Path(path).stem


def doc_for(docs, title):
    for did, d in docs.items():
        if d["versions"] and d["versions"][0]["Title"] == title:
            return did, d
    return None, None


def new_version(sf, did, path, reason, execute):
    body = {"ContentDocumentId": did, "Title": title_of(path), "PathOnClient": Path(path).name, "ReasonForChange": reason,
            "VersionData": base64.b64encode(Path(path).read_bytes()).decode()}
    if not execute:
        print("  [DRY-RUN] POST /sobjects/ContentVersion new version of %s from %s" % (did, Path(path).name))
        return
    st, r = sf.call("/sobjects/ContentVersion", body)
    print("  new version of %s: HTTP %s %s" % (did, st, r.get("id") if isinstance(r, dict) else str(r)[:200]))
    if st not in (200, 201):
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["seed", "status", "ids", "whatif", "reset", "stage"])
    ap.add_argument("which", nargs="?", default="both", choices=["bid", "sig", "both"])
    ap.add_argument("--config")
    ap.add_argument("--env-file", help="KEY=value file with SF_INSTANCE_URL / SF_CLIENT_ID / SF_CLIENT_SECRET")
    ap.add_argument("--dir", help="stage: the SharePoint connection's Attachment_File_Path on this host")
    ap.add_argument("--execute", action="store_true", help="really write to Salesforce (seed / whatif / reset)")
    ap.add_argument("--offline", action="store_true", help="print the plan only, never call Salesforce")
    a = ap.parse_args()
    cfgp = Path(a.config) if a.config else (BP / "config.json" if (BP / "config.json").exists() else BP / "config.example.json")
    cfg = json.load(open(cfgp, encoding="utf-8"))
    ags = cfg["salesforce"]["agencies"]
    pick = {"bid": ["Bid packet"], "sig": ["Signature page"], "both": ["Bid packet", "Signature page"]}[a.which]
    if a.offline:
        print("[OFFLINE] %s on %d agencies (%s); files:" % (a.cmd, len(ags), ", ".join(x["name"] for x in ags)))
        for x in ags:
            for k in ("original", "whatif"):
                p = path_of(cfg, x[k])
                print("   %-8s %s %s" % (k, "OK " if p.exists() else "MISSING", p.name))
        return
    sf = SF(load_env(a.env_file), cfg["salesforce"]["rest_api_version"])
    acc = agencies(sf, cfg)
    docs = documents(sf, list(acc.values()))
    if a.cmd == "status" or a.cmd == "ids":
        for name, aid in acc.items():
            print("agency %s (%s)" % (name, aid))
        for did, d in docs.items():
            print("  file %s: %s" % (did, ", ".join("v%s %s %s B" % (v["VersionNumber"], v["Title"], v["ContentSize"])
                                                     for v in d["versions"])))
        if a.cmd == "ids":
            print(json.dumps({"crm": {"content_document_ids": sorted(docs)}}, indent=1))
        return
    if a.cmd == "seed":
        for x in ags:
            aid = acc.get(x["name"])
            if not aid:
                if not a.execute:
                    print("[DRY-RUN] POST /sobjects/Account {Name: %s, Type: %s}" % (x["name"], cfg["salesforce"]["account_type"]))
                    continue
                st, r = sf.call("/sobjects/Account", {"Name": x["name"], "Type": cfg["salesforce"]["account_type"]})
                aid = r.get("id")
                print("account %s: HTTP %s %s" % (x["name"], st, aid))
            orig = path_of(cfg, x["original"])
            did, _ = doc_for(docs, title_of(orig))
            if did:
                print("  file %s already attached (%s)" % (orig.name, did))
                continue
            body = {"Title": title_of(orig), "PathOnClient": orig.name, "FirstPublishLocationId": aid,
                    "Description": cfg["salesforce"]["file_description"], "VersionData": base64.b64encode(orig.read_bytes()).decode()}
            if not a.execute:
                print("  [DRY-RUN] POST /sobjects/ContentVersion %s -> %s" % (orig.name, x["name"]))
                continue
            st, r = sf.call("/sobjects/ContentVersion", body)
            print("  file %s: HTTP %s %s" % (orig.name, st, r.get("id") if isinstance(r, dict) else r))
        print("next: python sf_files.py ids  (the ContentDocumentIds go into state/ids.json crm.content_document_ids)")
        return
    for x in ags:
        if x["doc_type"] not in pick and a.cmd == "whatif":
            continue
        orig = path_of(cfg, x["original"])
        did, d = doc_for(docs, title_of(orig))
        if not did:
            print("no file %s in Salesforce: run seed first" % orig.name)
            continue
        newest = d["versions"][-1]
        if a.cmd == "whatif":
            new_version(sf, did, path_of(cfg, x["whatif"]), "Bid Desk what-if: completed by the sales desk (SAMPLE)", a.execute)
        elif a.cmd == "reset":
            if newest["Checksum"] == md5(orig):
                print("  %s: newest version v%s is the original already" % (orig.name, newest["VersionNumber"]))
            else:
                new_version(sf, did, orig, "Bid Desk reset: the agency original again (was v%s)" % newest["VersionNumber"], a.execute)
        elif a.cmd == "stage":
            if not a.dir:
                sys.exit("stage needs --dir <the SharePoint connection's Attachment_File_Path>")
            n = newest["VersionNumber"]
            fn = "%s%s.pdf" % (newest["Title"], "" if str(n) == "1" else " (v%s)" % n)
            dest = Path(a.dir) / fn
            if dest.exists() and dest.stat().st_size == int(newest["ContentSize"]):
                print("  staged already: %s" % fn)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(sf.bytes_of(newest["Id"]))
            print("  staged %s (%d bytes)" % (fn, dest.stat().st_size))
    if a.cmd in ("whatif", "reset") and not a.execute:
        print("DRY-RUN: nothing written. Add --execute.")


if __name__ == "__main__":
    main()
