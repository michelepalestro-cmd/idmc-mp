#!/usr/bin/env python3
"""Step 1: create or update the five connections, then test them. Dry run by default.

  python idmc/01_connections.py plan --offline                  # render the bodies (secrets shown as key names only)
  python idmc/01_connections.py apply [--only pg,bq] --execute --expect-org <orgIdV3>
  python idmc/01_connections.py test  [--only pg]               # GET /api/v2/connection/test/<id> (read-only)
  python idmc/01_connections.py apply --only bq_dbmi --key-format pem --execute --expect-org <orgIdV3>

Connections (names from config.json "connections"):
  pg       native PostgreSQL (CCI): type TOOLKIT_CCI + instanceName PostgreSQL; connParams userName (NOT user),
           authenticationType UserIdPassword, encryptionMethod noEncryption       PROVEN 2026-09
  pg_cdc   the same with the replication role, used only by Database Ingestion  PROVEN 2026-09
  bq       Google BigQuery V2 (CCI), Simple mode, staging bucket, standard SQL for custom queries   PROVEN 2026-09
  bq_dbmi  a second BigQuery V2 connection for Database Ingestion: the private-key form it accepts differs from CDI's
           on some pods, so keep one connection per consumer                    PROVEN 2026-09
  sf       Salesforce (v2 native type): username / password / securityToken at the TOP level, not connParams  ADAPTED
Secrets are read from the toolkit .env at send time and never printed or written to disk.
Update = POST /api/v2/connection/<id> with the full body (there is no PUT); every update must carry the secret again
because GET masks it. If a create answers 403 APP_10519 or "no connector with type", the org has never had a
connection of that type: create one in Administrator > Connections once (UI wall), then this script manages it.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import rdf_common as C  # noqa: E402

TPL = C.BLUEPRINT / "idmc" / "templates" / "connections"
KEYS = ["pg", "pg_cdc", "bq", "bq_dbmi", "sf"]
CFG_KEY = {"pg": "pg", "pg_cdc": "pgCdc", "bq": "bq", "bq_dbmi": "bqDbmi", "sf": "sf"}
SECRETS = {"pg": ["PG_PASS"], "pg_cdc": ["PG_CDC_PASS"], "bq": ["BQ_KEY_FILE"], "bq_dbmi": ["BQ_KEY_FILE"],
           "sf": ["SF_USERNAME", "SF_PASSWORD", "SF_SECURITY_TOKEN"]}


def key_material(fmt):
    """(client_email, private key in the requested form) from BQ_KEY_FILE. Never printed."""
    kf = C.env("BQ_KEY_FILE", required=True)
    j = json.loads(Path(kf).expanduser().read_text(encoding="utf-8"))
    pem = j["private_key"]
    body = "".join(ln for ln in pem.splitlines() if ln and "PRIVATE KEY" not in ln)
    forms = {"stripped": body, "noheader": "\n".join(ln for ln in pem.splitlines() if "PRIVATE KEY" not in ln).strip(),
             "pem": pem, "escaped": pem.replace("\n", "\\n")}
    v = forms[fmt]
    if fmt != "pem" and "\n" in v and fmt != "noheader":
        v = v.replace("\n", "")
    return j["client_email"], v


def body_for(key, cfg, st, offline, key_format):
    v = C.template_vars(cfg, offline=offline)
    v["RE_ID"] = (st.get("runtimeEnvironment") or {}).get("id") or "<runtime environment id: run 00_resolve.py>"
    login = C.env("SF_LOGIN_URL") or ("https://login.salesforce.com" if offline else C.env("SF_LOGIN_URL", required=True))
    v["SF_SOAP_URL"] = login.rstrip("/") + f"/services/Soap/u/{cfg['crm']['apiVersion']}"
    b = C.render_json(TPL / f"{key}.json", v)
    shown = json.loads(json.dumps(b))
    if offline:
        if key in ("pg", "pg_cdc"):
            shown["connParams"]["password"] = "<from " + SECRETS[key][0] + ">"
        elif key in ("bq", "bq_dbmi"):
            shown["connParams"]["clientEmail"] = "<client_email from BQ_KEY_FILE>"
            shown["connParams"]["privateKey"] = f"<private_key from BQ_KEY_FILE, form '{key_format}'>"
        else:
            shown.update(username="<SF_USERNAME>", password="<SF_PASSWORD>", securityToken="<SF_SECURITY_TOKEN>")
        return None, shown
    if key in ("pg", "pg_cdc"):
        b["connParams"]["password"] = C.env(SECRETS[key][0], required=True)
        shown["connParams"]["password"] = "***"
    elif key in ("bq", "bq_dbmi"):
        email, pk = key_material(key_format)
        b["connParams"].update(clientEmail=email, privateKey=pk)
        shown["connParams"].update(clientEmail="***", privateKey="***")
    else:
        b.update(username=C.env("SF_USERNAME", required=True), password=C.env("SF_PASSWORD", required=True),
                 securityToken=C.env("SF_SECURITY_TOKEN") or "")
        shown.update(username="***", password="***", securityToken="***")
    return b, shown


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["plan", "apply", "test"])
    ap.add_argument("--only", help="comma list of " + ",".join(KEYS))
    ap.add_argument("--offline", action="store_true", help="plan without the .env or a login")
    ap.add_argument("--key-format", choices=["noheader", "stripped", "pem", "escaped"],
                    help="BigQuery private-key form (default: noheader for bq, pem for bq_dbmi; see Gotchas)")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    keys = a.only.split(",") if a.only else KEYS
    if a.cmd == "plan" or a.offline:
        for k in keys:
            fmt = a.key_format or ("pem" if k == "bq_dbmi" else "noheader")
            _, shown = body_for(k, cfg, st, True, fmt)
            print(f"--- {k}: POST /api/v2/connection (or /api/v2/connection/<id> when it exists)")
            print(json.dumps(shown, indent=1))
        print("needs:", ", ".join(f"{n}={s}" for k in keys for n, s in C.env_status(SECRETS[k])))
        return 0
    C.offline_session_guard(a)
    from idmc_session import Session
    import idmc_http as H
    S = Session()
    gate = H.WriteGate(a, S)
    existing = {c.get("name"): c for c in S.get("v2", "/api/v2/connection").json([]) or []}
    st.setdefault("connections", {})
    bad = 0
    for k in keys:
        name = cfg["connections"][CFG_KEY[k]]
        cur = existing.get(name)
        if a.cmd == "test":
            if not cur:
                print(f"{k}: '{name}' not found")
                bad += 1
                continue
            r = S.get("v2", f"/api/v2/connection/test/{cur['id']}")
            if r.status == 400:
                r = S.get("v2", f"/api/v2/connection/test/{cur['id']}?type=TOOLKIT_CCI")
            ok = r.ok and "fail" not in r.text.lower()
            print(f"{k}: test HTTP {r.status} {'OK' if ok else 'FAILED'} {r.head(240)}")
            bad += 0 if ok else 1
            continue
        fmt = a.key_format or ("pem" if k == "bq_dbmi" else "noheader")
        body, shown = body_for(k, cfg, st, False, fmt)
        if cur:
            body["id"] = cur["id"]
            r = gate.send(f"update connection {name}", "v2", "POST", f"/api/v2/connection/{cur['id']}", body=body)
        else:
            r = gate.send(f"create connection {name}", "v2", "POST", "/api/v2/connection", body=body)
        if r is None:
            print("    (dry run) body with secrets masked:", json.dumps(shown)[:400])
            continue
        if not r.ok:
            bad += 1
            hint = " -> create the first connection of this type in the UI once (APP_10519 / no connector)" \
                if "APP_10519" in r.text or "no connector" in r.text.lower() else ""
            print(f"    FAILED HTTP {r.status} {r.head(300)}{hint}")
            continue
        j = r.json({}) or {}
        back = S.get("v2", f"/api/v2/connection/{j.get('id') or (cur or {}).get('id')}").json({}) or {}
        st["connections"][CFG_KEY[k]] = {"id": back.get("id"), "guid": back.get("federatedId"), "name": name}
        print(f"    read-back id={back.get('id')} guid={back.get('federatedId')} host/project="
              f"{(back.get('connParams') or {}).get('hostName') or (back.get('connParams') or {}).get('projectId')}")
    if a.cmd == "apply" and gate.execute:
        C.save_state(st)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
