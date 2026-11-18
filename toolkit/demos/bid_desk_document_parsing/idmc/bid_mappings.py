#!/usr/bin/env python3
"""bid_mappings.py - the eight Bid Desk mappings: build six of them headless with the toolkit's generator (toolkit/mapgen),
import them, then wrap each imported mapping in a mapping task (runtime, pre-processing command, folder).

    python bid_mappings.py crm-ids --doc-ids <id1>,<id2>   # the CRM ContentDocumentIds (from infra/sf_files.py ids) -> state
    python bid_mappings.py render                         # templates/mappings/*.json -> state/specs/*.json, every ${...} filled
    python bid_mappings.py build --offline                # lint + compile + package 1, 1b, 3a, 3b, 4, 5 (placeholder ids)
    python bid_mappings.py build                          # the same with your org's ids (resolves the missing ones read-only)
    python bid_mappings.py import [--mode REUSE|OVERWRITE] [--only 3a] [--execute --expect-org <orgIdV3>]
    python bid_mappings.py list                           # the mappings and tasks in the project (read-only)
    python bid_mappings.py tasks [--execute --expect-org <orgIdV3>]   # one mapping task per imported mapping

How the mappings get into IDMC (KB CDI 02 "How Claude Builds Mappings Headless", route 5):
  * 1, 1b, 3a, 3b, 4, 5: each template is a toolkit/mapgen spec (nodes, fields, expressions, lookups, rule specs, links in
    order) plus the blueprint's own keys ("task", "status", "notes", "soqlFilters"). build renders it for your org, lints it
    (an ERROR stops that mapping), compiles it to IMF JSON and packages it as a DTEMPLATE zip under state/packages/.
    The profile comes from config.json + state/ids.json: org, project + the spec's stage folder, connection guids (the
    FRS federatedId a mapping binds as saas:@<guid>) + v2 ids, the rule specs' FRS ids as package assets.
    import uploads a package with the core idmc_export_import (REUSE the first time, OVERWRITE to rebuild under the SAME
    guid: build keeps each mapping's guid in state/ids.json mapping_guids). Dry run unless --execute --expect-org.
    ADAPTED: the generator is PROVEN elsewhere (BigQuery / PostgreSQL / Salesforce mappings); these specs have not yet been
    imported in this form, and Snowflake + SharePoint adapters ride its generic connector path (KB L-CONN-093).
  * Adapter details the generator does not write are applied by a template hook that build registers (mapgen's extension
    point; toolkit/mapgen is unchanged): Salesforce sources (mapping 1) get the proven source shape of KB L-CONN-108, data-
    object attributes owner / resource and readOptions.filterCondition = the spec's soqlFilters entry (typeSystem
    'Salesforce' comes from the profile); Snowflake targets get objectType 'table' + tableType = TABLE (KB L-CONN-093).
  * 2a, 2b (Structure Parser): UI once. The generator has no Structure Parser node; the proven path was a designer-built
    mapping, then package-cloned (the parser keeps "@<v3 model id>" + a copy of the model). Their specs document the shape.
Mapping tasks (PROVEN): POST /api/v2/mttask {"@type":"mtTask","name","mappingId","runtimeEnvironmentId"} -> it lands in
Default; move it with FRS POST /frs/api/v1/MoveEntities {"xferSpec":{"targetLocationId":<folder>,"sourceSpecArr":
[{"sourceEntityId":<frs id>,"mergeTags":""}]}}; the pre-processing command is "preProcessingCmd" on the full v2 task body
(POST /api/v2/mttask/<id>, the GET body minus audit fields), then read back.
Gotchas: the Snowflake writer's full reload needs the runtime attribute 'presql' (the truncate flag and the transformation's
Pre SQL are ignored, L-CONN-106: the specs set it in writerAttrs); the CRM Files filter must be a plain ContentDocumentId
list (L-CONN-114 + the catalog cannot parse a sub-query filter); a v2 MTT list has no frsGuid and its 'valid' is always
false: read each task. A mapping of the same name that the designer built has another guid: import REUSE keeps it.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

sys.path.insert(0, str(C.TOOLKIT / "mapgen"))     # the toolkit's shared mapping generator (stdlib only)

SPECS = C.TEMPLATES / "mappings"
OUT = C.STATE_DIR / "specs"
PKG_DIR = C.STATE_DIR / "packages"
AUDIT = ("createTime", "updateTime", "createdBy", "updatedBy")
BUILDABLE = ("1", "1b", "3a", "3b", "4", "5")              # 2a / 2b: Structure Parser, UI once
BLUEPRINT_KEYS = ("task", "status", "notes")               # the blueprint's own spec keys (mapgen does not read them)
# connection alias -> (config / state key, mapgen kind, adapter typeSystem). Snowflake and SharePoint use the generator's
# generic connector path (no BigQuery / PostgreSQL writer defaults, object path as written: KB L-CONN-093)
CONNS = {"CRM": ("crm", "SF", "Salesforce"), "WH": ("warehouse", "SNOWFLAKE", None), "SP": ("sharepoint", "SHAREPOINT", None)}
ACCEPTED = {"CONN_KIND": "Snowflake and SharePoint are not kinds mapgen knows; they take its generic connector path"}
PH = {"org": "OFFLINEorgGuid00000001", "project": "OFFLINEprojectGuid0001", "folder": "OFFLINEfolderGuid00001",
      "crm": "OFFLINEconnGuidCRM001", "warehouse": "OFFLINEconnGuidWH0001", "sharepoint": "OFFLINEconnGuidSP0001"}
RULE_REF = re.compile(r"^\$\{state:rulespecs\.([^}]+)\}$")


def code(stem):
    """m_bid_3a_bid_lines_dq -> 3a"""
    return stem.split("_")[2]


def specs(cfg, st):
    out = {}
    for p in sorted(SPECS.glob("m_bid_*.json")):
        out[p.stem] = C.render(json.loads(p.read_text(encoding="utf-8")), cfg, st)
    return out


def open_refs(spec, st):
    """what a rendered spec still waits for: '<state:... not built yet>' markers and rule specs not in state"""
    text = json.dumps(spec)
    left = sorted(set(x for x in text.split('"') if "not built yet" in x))
    rules = sorted(set(m for m in re.findall(r"\$\{state:rulespecs\.([^}]+)\}", text) if m not in (st.get("rulespecs") or {})))
    return left + ["rule spec %r" % r for r in rules]


def selected(a, all_specs, buildable_only=True):
    want = set(a.only or [])
    out = []
    for stem, s in all_specs.items():
        if buildable_only and code(stem) not in BUILDABLE:
            continue
        if want and not ({stem, code(stem)} & want):
            continue
        out.append((stem, s))
    if want and not out:
        C.H.die("--only %s matches none of: %s" % (sorted(want), ", ".join(code(k) for k in all_specs)))
    return out


# ------------------------------------------------------------------ mapgen profile + spec
def placeholder(prefix, n):
    return ("OFFLINE%s%d" % (prefix, n)).ljust(22, "0")[:22]


def profile(cfg, st, spec, offline):
    """the mapgen profile of one spec: org, project + the spec's stage folder, runtime, the three connections"""
    mg = st.get("mapgen") or {}
    org, guids, v2 = mg.get("org") or {}, mg.get("conn_guid") or {}, st.get("conn") or {}
    fk, rk = spec["task"]["folder"], spec["task"]["runtime"]
    need = [k for k, v in (("org guid", org.get("guid")), ("project id", st.get("project")),
                           ("folder %s id" % fk, (st.get("folders") or {}).get(fk))) if not v]
    need += ["connection %s ids" % k for k, _, _ in CONNS.values() if not (guids.get(k) and v2.get(k))]
    if need and not offline:
        C.H.die("missing in state/ids.json: %s (run bid_project.py and bid_connections.py, then build without --offline "
                "with IDMC credentials; or use --offline)" % ", ".join(need))
    conns = {}
    for alias, (key, kind, ts) in CONNS.items():
        c = {"guid": guids.get(key) or PH[key], "name": cfg["connections"][key], "repoHandle": v2.get(key) or "OFFLINE_" + key,
             "kind": kind}
        if ts:
            c["typeSystem"] = ts
        conns[alias] = c
    rt_name = cfg["idmc"]["runtime_environment_crm" if rk == "crm" else "runtime_environment"]
    return {"org": {"v2Id": org.get("v2Id") or "OFFLINE", "guid": org.get("guid") or PH["org"], "name": org.get("name") or "offline"},
            "runtimeEnvironment": {"id": (st.get("runtime") or {}).get(rk) or "OFFLINE_RE", "name": rt_name},
            "folder": {"project": cfg["idmc"]["project"], "projectGuid": st.get("project") or PH["project"],
                       "name": cfg["idmc"]["folders"][fk], "guid": (st.get("folders") or {}).get(fk) or PH["folder"]},
            "connections": conns}


def mapgen_spec(stem, spec, cfg, st, offline):
    """a rendered template -> the spec mapgen loads: blueprint keys dropped, rule specs bound to their FRS ids (listed as
    package assets), the mapping's own guid kept for an OVERWRITE rebuild"""
    sp = {k: copy.deepcopy(v) for k, v in spec.items() if k not in BLUEPRINT_KEYS}
    rules, assets, ph = st.get("rulespecs") or {}, {}, {}
    folder3 = "/Explore/%s/%s" % (cfg["idmc"]["project"], cfg["idmc"]["folders"]["f3"])
    for nd in sp["nodes"]:
        if nd.get("type") != "rulespec":
            continue
        m = RULE_REF.match(nd.get("asset") or "")
        if not m:
            C.H.die("%s: rulespec %s: asset must be ${state:rulespecs.<rule name in dq.json>}" % (stem, nd["name"]))
        rule = m.group(1)
        frs = rules.get(rule) or (ph.setdefault(rule, placeholder("rule", len(ph) + 1)) if offline else None)
        if not frs:
            C.H.die("%s: rule spec %r has no id in state/ids.json: run bid_dq.py build first (or use --offline)" % (stem, rule))
        nd["asset"] = frs
        assets.setdefault(frs, {"guid": frs, "name": "%s - %s" % (cfg["idmc"]["project"], rule), "type": "RULE_SPECIFICATION",
                                "path": folder3})
    if assets:
        sp["assets"] = list(assets.values())
    left = [x for x in open_refs(sp, st) if not x.startswith("rule spec")]
    if left and not offline:
        C.H.die("%s still waits for: %s" % (stem, "; ".join(left)))
    g = (st.get("mapping_guids") or {}).get(stem)
    if g:
        sp["guid"] = g                      # rebuild under the SAME guid (import OVERWRITE)
    return sp


_HOOKED = []


def _set_attrs(b, dobj, pairs):
    """a data object's objectAttributes = [Option name=value, ...], reusing the generator's Option objects"""
    attrs = dobj.get("objectAttributes") or []
    for i, (k, v) in enumerate(pairs):
        if i < len(attrs):
            attrs[i].update(name=k, value=v)
        else:
            attrs.append(b.new("Option", name=k, value=v))
    dobj["objectAttributes"] = attrs[:len(pairs)]


def register_adapter_hook():
    """the adapter details the generator does not write, as a mapgen template hook (its extension point; toolkit/mapgen is
    unchanged). Salesforce sources (typeSystem Salesforce, KB L-CONN-108): data-object attributes owner = '' and
    resource = '' instead of tableType, and readOptions.filterCondition = the spec's soqlFilters[<source name>] (SOQL, a
    plain literal list). Snowflake targets (kind SNOWFLAKE, KB L-CONN-093): data object objectType 'table' with the
    attribute tableType = TABLE, the shape of a designer-built Snowflake target that a generated mapping ran with."""
    if _HOOKED:
        return
    from idmc_mapgen.registry import template_hook
    from idmc_mapgen.spec import SpecError

    @template_hook
    def bid_adapter_shapes(ctx, content):
        filters = ctx.spec.get("soqlFilters") or {}
        by_name = {t["name"]: t for t in ctx.txs}
        seen = set()
        for nd in ctx.spec["nodes"]:
            conn = ctx.conns.get(nd.get("conn")) or {}
            if nd.get("type") == "source" and conn.get("typeSystem") == "Salesforce":
                seen.add(nd["name"])
                da = by_name[nd["name"]]["dataAdapter"]
                _set_attrs(ctx.b, da["object"], [("owner", ""), ("resource", "")])
                da["readOptions"]["filterCondition"] = filters.get(nd["name"], "")
            elif nd.get("type") == "target" and conn.get("kind") == "SNOWFLAKE":
                dobj = by_name[nd["name"]]["dataAdapter"]["object"]
                dobj["objectType"] = "table"
                _set_attrs(ctx.b, dobj, [("tableType", "TABLE")])
        stray = sorted(set(filters) - seen)
        if stray:
            raise SpecError("soqlFilters names %s, not Salesforce sources of this spec" % stray)
    _HOOKED.append(bid_adapter_shapes)


def compile_specs(cfg, st, offline, only=None, out_dir=None, quiet=False):
    """lint + compile + package the buildable specs -> [(stem, transformations, links, errors, warnings, guid)].
    out_dir: write <stem>.pkg.zip + <stem>.imf.json there (None = in memory only, e.g. bid_verify offline)."""
    from idmc_mapgen import lint as L
    from idmc_mapgen.compile import build
    from idmc_mapgen.package import package_bytes
    from idmc_mapgen.spec import SpecError, load_spec
    register_adapter_hook()
    results = []
    for stem, spec in specs(cfg, st).items():
        if code(stem) not in BUILDABLE or (only and not ({stem, code(stem)} & set(only))):
            continue
        sp = mapgen_spec(stem, spec, cfg, st, offline)
        prof = profile(cfg, st, spec, offline)
        issues = L.lint(copy.deepcopy(sp), profile=prof, allow_live=True)
        errs = [i for i in issues if i.severity == "ERROR"]
        warns = [i for i in issues if i.severity == "WARN" and i.code not in ACCEPTED]
        if not quiet:
            for i in errs + warns:
                print(("  [%s] %s: %s %s %s" % (i.severity, code(stem), i.code, i.node or "", i.message))[:300])
        if errs:
            results.append((stem, 0, 0, len(errs), len(warns), None))
            continue
        try:
            loaded = load_spec(sp, profile=prof)
            imf = build(loaded)
            pkg = package_bytes(loaded, imf)
        except SpecError as e:
            print("  [ERROR] %s: %s" % (code(stem), e))
            results.append((stem, 0, 0, 1, len(warns), None))
            continue
        ntx, nlk = len(imf["content"]["transformations"]), len(imf["content"]["links"])
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / (stem + ".pkg.zip")).write_bytes(pkg)
            (out_dir / (stem + ".imf.json")).write_text(json.dumps(imf, indent=1), encoding="utf-8")
        results.append((stem, ntx, nlk, 0, len(warns), loaded["guid"]))
    return results


def resolve(ctx, cfg, st):
    """the ids a real build needs that the other steps do not store, read-only: the org (v2 id, 22-char guid, name) and
    each connection's FRS guid (federatedId of GET /api/v2/connection/<v2 id>)"""
    mg = st.setdefault("mapgen", {})
    if not (mg.get("org") or {}).get("guid"):
        d = ctx.json(ctx.read("v2", "/api/v2/org"), {}) or {}
        mg["org"] = {"v2Id": d.get("id"), "guid": d.get("orgUuid") or ctx.S.v2().get("orgUuid"), "name": d.get("name")}
        print("org: v2 %s  guid %s  %r" % (mg["org"]["v2Id"], mg["org"]["guid"], mg["org"]["name"]))
    guids = mg.setdefault("conn_guid", {})
    for key, _, _ in CONNS.values():
        cid = (st.get("conn") or {}).get(key)
        if not cid:
            C.H.die("connection %r has no id in state/ids.json: run bid_connections.py show (or build) first" % cfg["connections"][key])
        if not guids.get(key):
            d = ctx.json(ctx.read("v2", "/api/v2/connection/" + cid), {}) or {}
            guids[key] = d.get("federatedId")
            print("connection %-10s v2 %s  guid %s" % (key, cid, guids[key] or "NOT FOUND"))


def cmd_build(a, ctx, cfg, st):
    offline = ctx.offline
    for o in a.only or []:
        if o not in BUILDABLE and not (o.startswith("m_bid_") and code(o) in BUILDABLE):
            print("%s: not built by the generator (2a / 2b: UI once, BUILD.md step 9; build takes %s)" % (o, ", ".join(BUILDABLE)))
    if not offline:
        resolve(ctx, cfg, st)
        C.save_state(st)
    res = compile_specs(cfg, st, offline, a.only, PKG_DIR)
    bad = 0
    for stem, ntx, nlk, ne, nw, guid in res:
        if ne:
            bad += 1
            print("FAIL %-3s %s: %d lint/compile error(s)" % (code(stem), stem, ne))
            continue
        print("OK   %-3s %-30s %2d transformations, %2d links, guid %s%s -> %s"
              % (code(stem), stem, ntx, nlk, guid, ", %d warning(s)" % nw if nw else "",
                 (PKG_DIR / (stem + ".pkg.zip")).relative_to(C.BP)))
        if not offline:
            st.setdefault("mapping_guids", {})[stem] = guid
    print("accepted lint warnings: " + "; ".join("%s (%s)" % kv for kv in ACCEPTED.items()))
    print("2a, 2b (Structure Parser): UI once, see BUILD.md step 9")
    if offline:
        print("offline build: packages carry PLACEHOLDER ids - rebuild without --offline before importing")
    else:
        C.save_state(st)
    sys.exit(1 if bad else 0)


def offline_package(zbytes):
    """True when a package (or the DTEMPLATE zip inside it) carries a placeholder id of an --offline build"""
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        for n in z.namelist():
            data = z.read(n)
            if b"OFFLINE" in data or (n.endswith(".zip") and offline_package(data)):
                return True
    return False


def cmd_import(a, ctx, cfg, st):
    import idmc_export_import as X
    all_specs = specs(cfg, st)
    for stem, spec in selected(a, all_specs):
        p = PKG_DIR / (stem + ".pkg.zip")
        if not p.exists():
            C.H.die("%s missing: run build first" % p.relative_to(C.BP))
        if offline_package(p.read_bytes()):
            C.H.die("%s was built --offline (placeholder ids): rebuild without --offline" % p.name)
        if ctx.offline:
            print("[OFFLINE] would import %s, mode %s (the preview needs a login)" % (p.name, a.mode))
            continue
        gate = C.H.WriteGate(ctx.args, ctx.S)
        gate.guard()
        X.cmd_import(ctx.S, argparse.Namespace(package=str(p), mode=a.mode, include=None, name="bid_" + stem), gate)
        if gate.execute:                     # read back: the mapping by name, and that it kept the guid of the build
            maps = [m for m in (ctx.json(ctx.read("v2", "/api/v2/mapping"), []) or []) if m.get("name") == spec["name"]]
            want = (st.get("mapping_guids") or {}).get(stem)
            for m in maps:
                full = ctx.json(ctx.read("v2", "/api/v2/mapping/" + m["id"]), {}) or {}
                g = full.get("assetFrsGuid")
                print("   read back %s: v2 %s guid %s %s" % (spec["name"], m["id"], g, "OK" if g == want else "(build guid %s)" % want))
            if not maps:
                print("   read back %s: NOT FOUND" % spec["name"])


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["crm-ids", "render", "build", "import", "list", "tasks"])
    ap.add_argument("--doc-ids", help="crm-ids: comma-separated ContentDocumentIds")
    ap.add_argument("--only", action="append", help="build / import: one mapping (1, 1b, 3a, ... or the template name); repeatable")
    ap.add_argument("--mode", choices=["REUSE", "OVERWRITE"], default="REUSE", help="import: REUSE first, OVERWRITE to rebuild")
    a = ap.parse_args()
    ctx = C.Ctx(a)
    cfg, st = ctx.cfg, C.state()
    if a.cmd == "crm-ids":
        ids = [x.strip() for x in (a.doc_ids or "").split(",") if x.strip()]
        if not ids:
            C.H.die("--doc-ids <id1>,<id2>")
        st["crm"] = {"content_document_ids": ids, "content_document_id_list": ", ".join("'%s'" % i for i in ids),
                     "agency_name_list": ", ".join("'%s'" % x["name"].replace("'", "''") for x in cfg["salesforce"]["agencies"])}
        C.save_state(st)
        return
    st.setdefault("crm", {}).setdefault("agency_name_list",
                                        ", ".join("'%s'" % x["name"].replace("'", "''") for x in cfg["salesforce"]["agencies"]))
    if a.cmd == "render":
        OUT.mkdir(parents=True, exist_ok=True)
        for k, s in specs(cfg, st).items():
            (OUT / (k + ".json")).write_text(json.dumps(s, indent=1), encoding="utf-8")
            open_ = open_refs(s, st)
            print("%-32s %-46s %s" % (k, s["name"], "OK" if not open_ else "waits for: " + "; ".join(open_)[:120]))
        print("-> %s" % OUT.relative_to(C.BP))
        return
    if a.cmd == "build":
        return cmd_build(a, ctx, cfg, st)
    if a.cmd == "import":
        return cmd_import(a, ctx, cfg, st)
    r = ctx.read("v2", "/api/v2/mapping")
    maps = {m.get("name"): m for m in (r.json([]) if r is not None else []) if isinstance(m, dict)}
    r = ctx.read("v2", "/api/v2/mttask")
    tasks = {t.get("name"): t for t in (r.json([]) if r is not None else []) if isinstance(t, dict)}
    defaults = {o.get("path"): o["id"] for o in C.v3_objects(ctx, "MTT") if (o.get("path") or "").startswith("Default/")}
    reg = st.setdefault("tasks", {})
    for k, spec in specs(cfg, st).items():
        mname, tname, task = spec["name"], spec["name"] + " - task", spec["task"]
        m, t = maps.get(mname), tasks.get(tname)
        print("%-46s mapping %-24s task %s" % (mname, (m or {}).get("id", "MISSING"), (t or {}).get("id", "MISSING")))
        if t:
            reg[k] = t["id"]
        if a.cmd != "tasks" or t:
            continue
        if not m and not ctx.offline:
            print("   import the mapping first (build + import, or the designer for 2a / 2b)")
            continue
        rt = (st.get("runtime") or {}).get(task["runtime"], "<runtime id>")
        body = {"@type": "mtTask", "name": tname, "description": "[bid_desk] " + spec["description"][:900],
                "mappingId": (m or {}).get("id", "<v2 mapping id>"), "runtimeEnvironmentId": rt}
        r = ctx.write("create mapping task", "v2", "POST", "/api/v2/mttask", body=body)
        tid = (r.json({}) or {}).get("id") if C.ok(r) else None
        if task.get("pre_processing"):
            full = ctx.read("v2", "/api/v2/mttask/" + (tid or "<taskId>"))
            fb = {k2: v for k2, v in (full.json({}) if full is not None else {}).items() if k2 not in AUDIT}
            fb.update(preProcessingCmd=task["pre_processing"], runtimeEnvironmentId=rt)
            ctx.write("set pre-processing command", "v2", "POST", "/api/v2/mttask/" + (tid or "<taskId>"),
                      body=fb if fb.get("@type") else {"preProcessingCmd": task["pre_processing"], "...": "the full GET body"})
            back = ctx.read("v2", "/api/v2/mttask/" + (tid or "<taskId>"))
            if back is not None:
                print("   read back preProcessingCmd:", (back.json({}) or {}).get("preProcessingCmd"))
        if tid:
            reg[k] = tid
        frs = defaults.get("Default/" + tname, "<frs id of the new task in Default>")
        if ctx.execute and frs.startswith("<"):
            again = {o.get("path"): o["id"] for o in C.v3_objects(ctx, "MTT") if (o.get("path") or "").startswith("Default/")}
            frs = again.get("Default/" + tname, frs)
        folder = (st.get("folders") or {}).get(task["folder"], "<folder id>")
        ctx.write("move task into its folder", "frs", "POST", "/frs/api/v1/MoveEntities",
                  body={"xferSpec": {"targetLocationId": folder, "sourceSpecArr": [{"sourceEntityId": frs, "mergeTags": ""}]}})
    if not ctx.offline:
        C.save_state(st)


if __name__ == "__main__":
    main()
