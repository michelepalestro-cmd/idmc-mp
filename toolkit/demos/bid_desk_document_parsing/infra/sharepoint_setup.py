#!/usr/bin/env python3
"""sharepoint_setup.py - the SharePoint side of the Bid Desk: Entra app consent, the delegated refresh token for the
IDMC SharePoint Online connection, the write-permission check, and the target folders. Stdlib only.

    python sharepoint_setup.py consent-url             # the admin-consent URL + click path (an Entra admin does it once)
    python sharepoint_setup.py token-url               # the sign-in URL that returns an authorization code
    python sharepoint_setup.py redeem --out <file outside the toolkit>   # paste the code at the hidden prompt -> refresh token (0600 file)
    python sharepoint_setup.py check                   # scopes the token REALLY carries + effective permissions on the site
    python sharepoint_setup.py mkdirs [--execute]      # <library>/<root_folder>/<agency> - <solicitation> folders

Facts this encodes (KB 02 Connector Notes, SharePoint Online; lessons L-CONN-100/101/107/111):
  * Mint the token for the SharePoint audience (https://<tenant>.sharepoint.com/.default offline_access), NOT Microsoft
    Graph: a Graph-scoped refresh token lets Test Connection pass and then browses 0 objects (L-CONN-100/101).
  * The token carries the CONSENTED scopes, not the ones the app registration lists. Until an admin grants consent for
    the write permissions, scp shows only the read scopes, SharePoint's EffectiveBasePermissions shows View/Open only,
    and every upload is 403 (L-CONN-111). `check` reads both, so you know before the first run.
  * The connector's INSERT into a document library needs the folder to exist: one row = ServerRelativeUrl (the folder)
    + Name (the file name); the bytes come from the connection's Attachment_File_Path on the agent (L-CONN-107).
Credentials: ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, SHAREPOINT_REFRESH_TOKEN (toolkit .env). Never printed.
"""
from __future__ import annotations

import base64
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import bid_common as C  # noqa: E402

REDIRECT = "https://login.microsoftonline.com/common/oauth2/nativeclient"


def tenant_host(cfg):
    return urllib.parse.urlparse(cfg["sharepoint"]["site_url"]).netloc


def http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with C.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def token(cfg):
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "client_id": C.env("ENTRA_CLIENT_ID"),
                                   "client_secret": C.env("ENTRA_CLIENT_SECRET"), "refresh_token": C.env("SHAREPOINT_REFRESH_TOKEN"),
                                   "scope": "https://%s/.default offline_access" % tenant_host(cfg)}).encode()
    st, d = http("POST", "https://login.microsoftonline.com/%s/oauth2/v2.0/token" % C.env("ENTRA_TENANT_ID"), body,
                 {"Content-Type": "application/x-www-form-urlencoded"})
    if st != 200:
        C.H.die("token refresh HTTP %s %s (AADSTS65001 = the scope was never consented)" % (st, d.get("error_description", "")[:200]))
    return d["access_token"]           # the rotated refresh token in d is NOT stored: the connection keeps its own


def claims(jwt):
    part = jwt.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["consent-url", "token-url", "redeem", "check", "mkdirs"])
    # the authorization code is never a command-line argument (shell history, process list): it is read from the
    # environment (SHAREPOINT_AUTH_CODE) or typed at a hidden prompt
    ap.add_argument("--out", help="redeem: write the refresh token here (outside the toolkit, 0600)")
    a = ap.parse_args()
    C.H.safe_console()
    cfg = C.load_config(a.config)
    sp = cfg["sharepoint"]
    if a.cmd == "consent-url":
        print("An Entra admin opens (replace the two ids):")
        print("  https://login.microsoftonline.com/<ENTRA_TENANT_ID>/adminconsent?client_id=<ENTRA_CLIENT_ID>")
        print("or clicks: Entra admin center > Identity > Applications > App registrations > <your app> > API permissions >")
        print("  Add: SharePoint > Delegated > AllSites.Write (or Sites.ReadWrite.All) + MyFiles.Write; then 'Grant admin consent'.")
        print("Then mint a NEW refresh token (token-url, redeem): an old one keeps its old scopes.")
        return
    if a.cmd == "token-url":
        print("Sign in once as the user IDMC will act as, then copy the 'code' parameter from the address bar:")
        print("  https://login.microsoftonline.com/<ENTRA_TENANT_ID>/oauth2/v2.0/authorize?client_id=<ENTRA_CLIENT_ID>"
              "&response_type=code&redirect_uri=" + urllib.parse.quote(REDIRECT, safe="") +
              "&scope=" + urllib.parse.quote("https://%s/.default offline_access" % tenant_host(cfg), safe="") + "&prompt=consent")
        return
    if a.cmd == "redeem":
        if not a.out:
            C.H.die("redeem needs --out <file outside the toolkit>")
        if Path(a.out).resolve().is_relative_to(C.TOOLKIT.resolve()):
            C.H.die("--out must be outside the toolkit")
        code = os.environ.get("SHAREPOINT_AUTH_CODE") or ""
        if not code:
            if not sys.stdin.isatty():
                code = sys.stdin.readline()
            else:
                code = getpass.getpass("authorization code (the 'code' parameter, not shown): ")
        code = code.strip()
        if not code:
            C.H.die("no authorization code: paste it at the prompt, pipe it on stdin, or set SHAREPOINT_AUTH_CODE")
        body = urllib.parse.urlencode({"grant_type": "authorization_code", "client_id": C.env("ENTRA_CLIENT_ID"),
                                       "client_secret": C.env("ENTRA_CLIENT_SECRET"), "code": code, "redirect_uri": REDIRECT,
                                       "scope": "https://%s/.default offline_access" % tenant_host(cfg)}).encode()
        st, d = http("POST", "https://login.microsoftonline.com/%s/oauth2/v2.0/token" % C.env("ENTRA_TENANT_ID"), body,
                     {"Content-Type": "application/x-www-form-urlencoded"})
        if st != 200 or "refresh_token" not in d:
            C.H.die("redeem HTTP %s %s" % (st, d.get("error_description", "")[:200]))
        fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("SHAREPOINT_REFRESH_TOKEN=" + d["refresh_token"] + "\n")
        print("refresh token written to the file you named (0600); scopes:", claims(d["access_token"]).get("scp"))
        return
    if a.offline or (a.cmd == "mkdirs" and not a.execute):
        print("[OFFLINE / DRY-RUN] would refresh the SharePoint token and %s" % ("read scp + EffectiveBasePermissions" if a.cmd == "check"
                                                                      else "create the folders"))
        for ag in cfg["salesforce"]["agencies"]:
            print("   folder %s/%s/%s - %s" % (sp["library"], sp["root_folder"], ag["name"], ag["solicitation"]))
        return
    tok = token(cfg)
    h = {"Authorization": "Bearer " + tok, "Accept": "application/json;odata=nometadata"}
    if a.cmd == "check":
        scp = claims(tok).get("scp", "")
        print("scopes in the token:", scp)
        st, d = http("GET", sp["site_url"].rstrip("/") + "/_api/web/EffectiveBasePermissions", headers=h)
        low = int((d or {}).get("Low", 0)) if st == 200 else 0
        print("EffectiveBasePermissions HTTP %s: AddListItems=%s" % (st, bool(low & 0x2)))
        if "Write" not in scp and "FullControl" not in scp:
            print("NOT WRITABLE: grant admin consent for the write scope, then mint a new refresh token (consent-url)")
            sys.exit(1)
        return
    for ag in cfg["salesforce"]["agencies"]:
        for rel in (sp["root_folder"], "%s/%s - %s" % (sp["root_folder"], ag["name"], ag["solicitation"])):
            url = "%s/%s/%s" % (sp["site_relative"].rstrip("/"), sp["library"], rel)
            call = sp["site_url"].rstrip("/") + "/_api/web/folders/add('%s')" % urllib.parse.quote(url)
            if not a.execute:
                print("[DRY-RUN] POST %s" % call)
                continue
            st, d = http("POST", call, b"", h)
            print("folder %s: HTTP %s" % (url, st))


if __name__ == "__main__":
    main()
