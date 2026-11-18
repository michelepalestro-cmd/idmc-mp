"""Compile a spec into IMF JSON (the content of a mapping's bin/@2.bin).

    from idmc_mapgen.compile import build
    imf = build(spec)                      # {"content": Template, "metadata": {"$$classInfo": {...}}}

CLI (legacy-compatible; writes <name>.imf.json and the package into the current directory):
    python -m idmc_mapgen.compile spec.json [--out pkg.zip] [--profile profile.json]

Every problem is a SpecError: an error raised while building a node names the node and its type; one raised by a
template hook names the hook. An extension module in idmc_mapgen/nodes/ that failed to import stops every build
that may need it (see nodes/__init__.py); allow_broken_extensions=True, or the environment variable
MAPGEN_ALLOW_BROKEN_EXTENSIONS=1, builds without it anyway (with a RuntimeWarning).
"""
import json
import os
import sys
import time
import warnings

from . import nodes  # noqa: F401  (registers every node type)
from .imf import B, epoch_ms, imf_bytes, now_iso  # noqa: F401  (imf_bytes re-exported)
from .registry import NODES, TEMPLATE_HOOKS, Ctx
from .spec import SpecError, validate

ALLOW_BROKEN_ENV = "MAPGEN_ALLOW_BROKEN_EXTENSIONS"


def _flow_order(ctx, content):
    """Target load order: spec "flowOrder": [[[source names], [target names]], ...] -> Template.flowOrderEntries."""
    fo = ctx.spec.get("flowOrder")
    if fo:
        content["flowOrderEntries"] = [ctx.b.new("TmplFlowOrderEntry", sources=list(fs), sourceTypes=["Source"] * len(fs),
                                                 targets=list(ft), targetTypes=["Target"] * len(ft)) for fs, ft in fo]


# flowOrder is the legacy template-level step: keep it the first hook whatever registers later.
if _flow_order not in TEMPLATE_HOOKS:
    TEMPLATE_HOOKS.insert(0, _flow_order)


def _unknown_type(t):
    msg = "node type %r is not implemented (known: %s)" % (t, ", ".join(sorted(NODES)))
    if nodes.IMPORT_ERRORS:
        msg += "; extension modules that failed to import: " + "; ".join("%s (%s)" % kv for kv in sorted(nodes.IMPORT_ERRORS.items()))
    return SpecError(msg)


def allow_broken(flag):
    """True when a build goes on without the extension modules that failed to import (with a RuntimeWarning) instead of
    refusing the spec: ``flag`` (build's ``allow_broken_extensions``), or, when it is None, the environment variable
    MAPGEN_ALLOW_BROKEN_EXTENSIONS set to 1 / true / yes / on (any case). lint uses it to choose ERROR or WARN for
    EXTENSION_BROKEN, so the two always agree."""
    if flag is None:
        flag = os.environ.get(ALLOW_BROKEN_ENV, "").strip().lower() in ("1", "true", "yes", "on")
    return bool(flag)


_allow_broken = allow_broken      # the earlier private name (kept stable for importers)


def broken_extensions(spec):
    """The extension modules that failed to import and that this spec may need, with the reason: exactly what build
    refuses. lint reports each entry as EXTENSION_BROKEN (lint._extension_issues: an ERROR, a WARN when allow_broken()
    says build goes on without them). Any spec shape."""
    nodes_ = spec.get("nodes") if isinstance(spec, dict) else None
    used = {nd.get("type") for nd in (nodes_ if isinstance(nodes_, list) else [])
            if isinstance(nd, dict) and isinstance(nd.get("type"), str)}
    out = []
    for mod, err in sorted(nodes.IMPORT_ERRORS.items()):
        types, why = nodes.FAILED_SCOPE.get(mod, (frozenset(), "nothing is known about what it adds"))
        if why:
            out.append("nodes/%s.py (%s) may act on every spec: %s" % (mod, err, why))
        elif types & used:
            out.append("nodes/%s.py (%s) declares node type(s) %s, used by this spec"
                       % (mod, err, ", ".join(repr(t) for t in sorted(types & used))))
    return out


_broken_extensions = broken_extensions


def _check_extensions(spec, allow_broken_extensions):
    broken = broken_extensions(spec)
    if not broken:
        return
    msg = ("extension module(s) in idmc_mapgen/nodes/ failed to import, so this build would silently lack what they "
           "add: " + "; ".join(broken))
    if allow_broken(allow_broken_extensions):
        warnings.warn("building %r without them: %s" % (spec["name"], msg), RuntimeWarning, stacklevel=3)
        return
    raise SpecError(msg + ". Fix or remove the module(s), or build without them with allow_broken_extensions=True "
                    "(environment: %s=1)." % ALLOW_BROKEN_ENV)


def _pairs(nd, key, what):
    """'advanced' / 'set' as [(name, value)]: a {name: value} object or a list of [name, value] pairs."""
    v = nd.get(key)
    if not v:
        return []
    items = list(v.items()) if isinstance(v, dict) else v
    if not isinstance(items, (list, tuple)) or not all(
            isinstance(p, (list, tuple)) and len(p) == 2 and isinstance(p[0], str) and p[0] for p in items):
        raise SpecError("node %r (%s): %r must be %s; got %r" % (nd["name"], nd["type"], key, what, v))
    return items


def _apply_escape_hatches(b, nd, tx):
    """'advanced' ({name: value} or [[name, value]]) overrides/appends advanced properties; 'set' ({prop: value})
    is merged last."""
    from . import values
    for k, v in _pairs(nd, "advanced", "{name: value} or [[name, value], ...]"):
        v = values.as_text(v, "node %r (%s): advanced %r" % (nd["name"], nd["type"], k), what="an advanced property value")
        props = tx.setdefault("advancedProperties", [])
        for p in props:
            if p.get("name") == k:
                p["value"] = v
                break
        else:
            props.append(b.new("TxAdvancedProperty", name=k, value=v))
    st = _pairs(nd, "set", "an object {property: value}")
    if st:
        tx.update(st)


def _named(nd, e):
    """SpecError e with every problem naming the node (most builder messages already do)."""
    probs = [p if isinstance(p, str) else str(p) for p in e.problems]   # a problem that is not a str must not crash here
    if probs == e.problems and all(repr(nd["name"]) in p for p in probs):
        return e
    tag = "node %r (%s): " % (nd["name"], nd["type"])
    return SpecError([p if repr(nd["name"]) in p else tag + p for p in probs])


def _is_obj(o):
    return isinstance(o, dict) and "$$ID" in o and "$$class" in o


def build_node(fn, ctx, nd):
    """Run node builder ``fn`` on node ``nd`` exactly as build() runs it -> the transformation object: the builder must
    return an IMF object with a name and register IMF groups, the escape hatches ("advanced", "set") are applied, and
    every problem is a SpecError naming the node (a KeyError is a "missing or unknown key", any other exception keeps
    its type and message). lint runs the generic nodes' builders through it (lint._build_refusals), so it reports the
    build's own refusals in the build's words."""
    try:
        ins_before = set(ctx.ing)
        tx = fn(ctx, nd)
        where = "builder %s.%s" % (getattr(fn, "__module__", "?"), getattr(fn, "__qualname__", "?"))
        if not (_is_obj(tx) and "name" in tx):
            raise SpecError("node %r (%s): %s returned %s, not the transformation object (a missing 'return tx'?)"
                            % (nd["name"], nd["type"], where, type(tx).__name__))
        # the link loop references these groups: one that is not an IMF object would fail there, far from its cause
        ports = [("link source", nd["name"] + ("." + s if s else ""), g) for s, g in (ctx.outg.get(nd["name"]) or {}).items()]
        ports += [("link target", k, ctx.ing[k]) for k in ctx.ing if k not in ins_before]
        bad = ["%s %r is %s" % (what, key, type(g).__name__) for what, key, g in ports if not _is_obj(g)]
        if bad:
            raise SpecError("node %r (%s): %s registered a group that is not an IMF object (ctx.out / ctx.inp take the "
                            "group object): %s" % (nd["name"], nd["type"], where, "; ".join(bad)))
        _apply_escape_hatches(ctx.b, nd, tx)
        return tx
    except SpecError as e:
        n = _named(nd, e)
        if n is e:
            raise
        raise n from None
    except KeyError as e:
        raise SpecError("node %r (%s): missing or unknown key %s" % (nd["name"], nd["type"], e)) from None
    except Exception as e:   # a malformed option or a builder bug: name the node, keep the message and the cause
        raise SpecError("node %r (%s): %s: %s" % (nd["name"], nd["type"], type(e).__name__, e)) from e


_build_node = build_node          # the earlier private name (kept stable for importers)


def _run_hook(hook, ctx, content):
    try:
        hook(ctx, content)
    except SpecError:
        raise
    except Exception as e:
        raise SpecError("template hook %s.%s: %s: %s" % (getattr(hook, "__module__", "?"), getattr(hook, "__qualname__", "?"),
                                                         type(e).__name__, e)) from e


def is_exclude_rule(sel):
    """{"exclude": [...]} and nothing else. A rename map that merely has a field called "exclude" is a rename map
    (the legacy generators turned {"exclude": "exclude", ...} into "all fields except e,x,c,l,u,d,e")."""
    return isinstance(sel, dict) and set(sel) == {"exclude"} and isinstance(sel["exclude"], (list, tuple))


def _link_rules(b, tg, sel):
    """Field selection on the receiving group: list = include only; {in: out} = include + rename; {"exclude": [...]} = all but."""
    if is_exclude_rule(sel):
        tg["rules"] = [b.new("TmplAllRule", bulkRename="false", include="true"),
                       b.new("TmplNameRule", bulkRename="false", include="false", fieldNamesStr="",
                             names=[b.new("TmplNameRuleEntry", inputName=k, outputName="") for k in sel["exclude"]])]
    else:
        sel = sel if isinstance(sel, dict) else {k: "" for k in sel}
        tg["rules"] = [b.new("TmplNameRule", bulkRename="false", include="true", fieldNamesStr="",
                             names=[b.new("TmplNameRuleEntry", inputName=k, outputName=v) for k, v in sel.items()])]


def build(spec, now=None, allow_broken_extensions=None):
    """spec dict -> IMF dict. ``now``: createTime (None = current UTC, epoch seconds, or an ISO string).

    ``allow_broken_extensions``: build even when an extension module this spec may need failed to import (None =
    the MAPGEN_ALLOW_BROKEN_EXTENSIONS environment variable decides; default refuse)."""
    validate(spec)
    for i, nd in enumerate(spec["nodes"]):
        if not isinstance(nd["type"], str):
            raise SpecError("nodes[%d] (%s): 'type' must be a string, got %r" % (i, nd["name"], nd["type"]))
    _check_extensions(spec, allow_broken_extensions)
    b = B()
    ctx = Ctx(b, spec, now_iso(now))
    for nd in spec["nodes"]:
        fn = NODES.get(nd["type"])
        if fn is None:
            raise _unknown_type(nd["type"])
        ctx.txs.append(build_node(fn, ctx, nd))
    links = []
    T = {t["name"]: t for t in ctx.txs}
    for i, lk in enumerate(spec["links"]):
        frm, to = lk[0], lk[1]
        fn, _, fg = frm.partition(".")
        tn = to.split(".")[0]
        if fg not in ctx.outg.get(fn, {}):
            raise SpecError("links[%d] %s -> %s: %r has no output %s (link sources: %s)"
                            % (i, frm, to, fn, "group %r" % fg if fg else "default group",
                               ", ".join(sorted((fn + "." + s) if s else fn for s in ctx.outg.get(fn, {}))) or "none - it cannot be linked from"))
        if to not in ctx.ing:
            raise SpecError("links[%d] %s -> %s: %r is not a link target (targets of %s: %s)"
                            % (i, frm, to, to, tn, ", ".join(sorted(k for k in ctx.ing if k.split(".")[0] == tn)) or "none"))
        tg = ctx.ing[to]
        for nn in (fn, tn):
            if nn not in T:
                raise SpecError("links[%d] %s -> %s: node %r has no transformation named %r (its 'set' or its builder "
                                "renamed it); links find a transformation by its node name" % (i, frm, to, nn, nn))
        if len(lk) > 2 and lk[2]:
            _link_rules(b, tg, lk[2])
        links.append(b.new("TmplLink", name=fn + ".Edge", fromGroup=b.ref(ctx.outg[fn][fg]), fromTransformation=b.ref(T[fn]),
                           toGroup=b.ref(tg), toTransformation=b.ref(T[tn])))
    ann = [b.new("GenericAnnotation", source="TEMPLATE_SETTINGS", nameValuePairs=[
              b.new("NameValuePair", name="UNIQUIFY_MAPPLET_TX_NAMES_OPTIONS", value={"$$class": b.c("StringValue"), "valueLiteral": "{\"nonNativeMappletTx\":true}"}),
              b.new("NameValuePair", name="UNIQUIFY_MAPPLET_TX_NAMES", value={"$$class": b.c("BooleanValue"), "value": "true"})]),
           b.new("Description", body=spec.get("description", ""))]
    content = {"$$IID": "stringIdentity:@2", "$$class": b.c("Template"), "annotations": ann, "allowMaxFieldLength": "false",
               "bigIntConvertType": "ONLY_BIGINT", "documentType": "MAPPING", "ecoSystem": "", "name": spec["name"],
               "specialCharacterSupport": "false", "templateOrigin": "", "links": links, "transformations": ctx.txs}
    for hook in list(TEMPLATE_HOOKS):
        _run_hook(hook, ctx, content)
    return {"content": content, "metadata": {"$$classInfo": b.class_info()}}


ZIP_YEARS = (1980, 2107)    # the years a ZIP entry date can hold (the packager dates the entries in local time)


def _package_ms(now):
    """The package timestamp of compile_file's ``now`` (epoch ms, None = the current time). SpecError when it is no
    usable time, or when a ZIP entry cannot be dated with it (zipfile would fail with a raw ValueError)."""
    try:
        ms = epoch_ms(now)
        year = None if ms is None else time.localtime(ms / 1000.0).tm_year
    except SpecError:
        raise
    except (TypeError, ValueError, OverflowError, OSError) as e:
        raise SpecError("now %r is not a usable time (%s: %s)" % (now, type(e).__name__, e)) from None
    if year is not None and not ZIP_YEARS[0] <= year <= ZIP_YEARS[1]:
        raise SpecError("now %r: a package can only be pinned to a time in %d-%d (local time), the years a ZIP entry "
                        "date can hold" % (now, ZIP_YEARS[0], ZIP_YEARS[1]))
    return ms


def compile_file(path_or_spec, profile=None, out=None, now=None, vars=None, allow_broken_extensions=None):
    """load_spec -> build -> package in one call. Returns {"spec", "imf", "package"} (package = out path, or bytes).

    ``now`` (epoch seconds or an ISO string such as "2026-10-03T00:00:00.000Z") pins createTime AND every package
    timestamp, so the same inputs give the same bytes. It must fall in 1980-2107 (ZIP entry dates)."""
    from .package import package, package_bytes
    from .spec import load_spec
    if isinstance(now, str):
        now = now.strip()             # createTime gets the same text the package times were read from
    now_ms = _package_ms(now)
    spec = load_spec(path_or_spec, profile=profile, vars=vars)
    imf = build(spec, now=now, allow_broken_extensions=allow_broken_extensions)
    pkg = package(spec, imf, out, now_ms=now_ms) if out else package_bytes(spec, imf, now_ms=now_ms)
    return {"spec": spec, "imf": imf, "package": pkg}


USAGE = "usage: python -m idmc_mapgen.compile spec.json [--out pkg.zip] [--profile profile.json]"


def _cli_args(argv):
    """(spec path, --out value, --profile value) of the command line (options before or after the path); ValueError
    when an option has no value or no spec path is given."""
    opts, rest, i = {"--out": None, "--profile": None}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in opts:
            if i + 1 >= len(argv) or argv[i + 1] in opts:
                raise ValueError("%s needs a value" % a)
            opts[a] = argv[i + 1]
            i += 2
        else:
            rest.append(a)
            i += 1
    if not rest:
        raise ValueError("no spec file given")
    return rest[0], opts["--out"], opts["--profile"]


def main(argv=None):
    """The legacy-compatible CLI: <name>.pkg.zip (or --out) and <name>.imf.json in the current directory, <name> being
    package.safe_file_name of the mapping name; prints the package path written. Exit 2 on a usage or spec problem
    (a SpecError from load_spec, build or the packager: nothing is written then)."""
    from .package import package, safe_file_name
    from .spec import load_spec
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    try:
        path, out, prof = _cli_args(argv)
    except ValueError as e:
        print("ERROR: %s (%s)" % (e, USAGE), file=sys.stderr)
        return 2
    try:
        spec = load_spec(path, profile=prof)
        stem = safe_file_name(spec["name"])   # 'm_a:b.pkg.zip' would land in an NTFS alternate data stream
        out = out or stem + ".pkg.zip"
        imf = build(spec)
        package(spec, imf, out)          # the packager refuses some specs too (an unreadable folderJson file ...)
    except SpecError as e:
        print("SPEC ERROR: %s" % e, file=sys.stderr)
        return 2
    with open(stem + ".imf.json", "w") as f:
        json.dump(imf, f, indent=1)
    if spec.get("documentType") == "DMAPPLET":      # keys its package ignores (lint: MPLT_PKG_IGNORED)
        from .nodes.mapplet import package_ignored_message
        warn = package_ignored_message(spec)
        if warn:
            print("WARN: %s" % warn, file=sys.stderr)
    print("package", out, "guid", spec["guid"], "transformations", len(imf["content"]["transformations"]), "links", len(imf["content"]["links"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
