"""Lookup. Default = UNCONNECTED: no links; call it from an expression as :LKP.<NAME>(arg, ...).
"connected": true delegates to nodes/lookup_connected.py.

The lookup object is resolved like a source's: on PostgreSQL / JDBC connections "<schema>/<table>" becomes
"<schema>/TABLE/<table>" ("objkind": "VIEW" -> "<schema>/VIEW/<view>"); the connector rejects the one-segment
"<schema>/<table>" path at run time (SDK_APP_COM_20000, L-CDI-162). The adapter type system is the connection's
(``typeSystem``, default TOOLKIT). Flat-file lookups are not supported (they need the CSV file adapter shape).
"""
from .. import values
from ..imf import adapter_fields, read_options, tx_fields
from ..registry import node

OBJKINDS = ("TABLE", "VIEW")
POLICIES = ("Use First Value", "Use Last Value", "Use Any Value", "Report Error")   # one value back: no "Use All Values"
_NEEDS_CONNECTED = "lookup %r is 'connected', which needs idmc_mapgen/nodes/lookup_connected.py (%s)"


def _unconnected_cond(nd):
    """[(lookup_col, IN_arg)] of an unconnected lookup (equality only; the operator form is for connected lookups)."""
    from ..spec import SpecError
    out = []
    for c in nd["cond"]:
        if not (isinstance(c, (list, tuple)) and len(c) == 2 and all(isinstance(x, str) and x for x in c)):
            raise SpecError("lookup %r: an unconnected lookup's cond entries are [lookup_col, IN_arg] (got %r; [col, op, arg] "
                            "needs \"connected\": true)" % (nd["name"], c))
        out.append((c[0], c[1]))
    return out


def _kind_and_objkind(conn, nd):
    """(connection kind, objkind) of a lookup; SpecError for a flat file connection or an unknown objkind."""
    from ..spec import SpecError
    kind = conn.get("kind", "BQ")
    if kind == "FF":
        raise SpecError("lookup %r: a flat file lookup is not supported (conn %r is a flat file connection); land the file "
                        "in a table first, or join it with a joiner" % (nd["name"], nd.get("conn")))
    objkind = nd.get("objkind", "TABLE")
    if objkind not in OBJKINDS:
        raise SpecError("lookup %r: objkind %r not in %s" % (nd["name"], objkind, ", ".join(OBJKINDS)))
    return kind, objkind


def _policy(nd):
    """The multiple-match policy of an unconnected lookup (SpecError for one it cannot have)."""
    policy = nd.get("policy", "Use Any Value")
    if policy not in POLICIES:
        from ..spec import SpecError
        raise SpecError("lookup %r: policy %r not in %s" % (nd["name"], policy, ", ".join(POLICIES)))
    return policy


def lookup_object(conn, nd):
    """The DataObject path of a lookup (``nd["object"]``) as the connector needs it."""
    from ..spec import SpecError
    obj = values.text(nd, "object", "", what="an object path")
    kind, objkind = _kind_and_objkind(conn, nd)
    if kind in ("PG", "JDBC") and obj and "/TABLE/" not in obj and "/VIEW/" not in obj:
        parts = obj.split("/")
        if len(parts) != 2 or not all(parts):
            raise SpecError("lookup %r: object %r on a %s connection must be <schema>/<table> (or <schema>/TABLE/<table>, "
                            "<schema>/VIEW/<view>)" % (nd["name"], obj, kind))
        obj = "%s/%s/%s" % (parts[0], objkind, parts[1])
    return obj


@node("lookup", doc="Unconnected lookup: conn, object | query, fields, cond: [[lookup_col, IN_arg]], ret, policy, "
                    "objkind (PG/JDBC: TABLE|VIEW). connected: true -> connected lookup (separate module).")
def build(ctx, nd):
    conn = ctx.conn(nd["conn"])
    obj = lookup_object(conn, nd)
    if values.flag(nd, "connected"):
        try:
            from .lookup_connected import build_connected
        except ImportError as e:
            from ..spec import SpecError
            raise SpecError(_NEEDS_CONNECTED % (nd["name"], e)) from None
        return build_connected(ctx, dict(nd, object=obj) if "object" in nd else nd)
    b = ctx.b; name = nd["name"]
    q, ret = values.text(nd, "query", "", what="SQL"), values.text(nd, "ret", what="a field name")
    cond = _unconnected_cond(nd)
    policy = _policy(nd)
    afs = adapter_fields(b, nd["fields"], "CUSTOM_TABLE" if q else obj.split("/")[-1])
    dobj = b.new("DataObject", name=obj, customQuery=q, dbSchema="", label=obj, objectName=obj.split("/")[-1] if obj else "",
                 objectType="" if q else "TABLE", parentPath="", path=obj, retainMetadata="false", fields=afs)
    if not q:
        dobj["objectAttributes"] = [b.new("Option", name="tableType", value="TABLE")]
    da = b.new("BaseAdapter", name="", codePage="", compatibleEngine="", connectionId="saas:@" + conn["guid"],
               connectionSelectionType="", excludeDynamicFileNameField="false", fwConfigId="", multipleObject="false",
               objectType="QUERY" if q else "SINGLE", typeSystem=conn.get("typeSystem", "TOOLKIT"), useDynamicFileName="false", object=dobj,
               oprRuntimeAttributes=b.new("RuntimeAttributes"),
               readOptions=read_options(b),
               runtimeAttributes=b.new("RuntimeAttributes"))
    tx = b.new("TmplLookup", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal"), ("Lookup caching enabled", "true"), ("Lookup cache directory name", "$PMCacheDir"),
                                         ("Lookup cache persistent", "false"), ("Cache File Name Prefix", ""), ("Re-cache from lookup source", "false"),
                                         ("Lookup Data Cache Size", "AUTO"), ("Lookup Index Cache Size", "AUTO"), ("Null ordering", ""), ("Sorted Input", "false"),
                                         ("Lookup source is static", "false"), ("Pre-build lookup cache", "AUTO"), ("Optional", "true")]),
               advancedInputPortNames="", associatedFields="", lookupCondition="", multipleMatchPolicy=policy,
               returnPortName=ret, unconnected="true", useLabels="false", fields=tx_fields(b, nd["fields"], afs),
               inputPortNames=[r for l, r in cond],
               lookupConditions=[b.new("LookupCondition", leftOperand=l, operator="=", rightOperand=r) for l, r in cond],
               dataAdapter=da)
    return tx   # unconnected: exposes no link groups


def _connected_problems(spec, nd, analysis, conns):
    """lookup_connected.lint_problems: build_connected's own refusals (policy, cond entries, condition fields), or the
    refusal build gives when that module cannot be imported."""
    try:
        from .lookup_connected import lint_problems as connected_problems
    except ImportError as e:     # build's own refusal of every connected lookup then
        return [("NODE_MALFORMED", _NEEDS_CONNECTED % (nd["name"], e))]
    except Exception as e:       # the module fails while importing: build fails there too
        return [("NODE_MALFORMED", _NEEDS_CONNECTED % (nd["name"], "%s: %s" % (type(e).__name__, e)))]
    return list(connected_problems(spec, nd, analysis, conns))


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)] for what build() refuses in a lookup's options, besides the object path shape that lint
    checks itself (PG_OBJECT_PATH): a flat file connection, an unknown objkind, and the lookup's cond entries and policy
    (an unconnected lookup: [lookup_col, IN_arg] and its four policies; a connected one: lookup_connected.lint_problems,
    build_connected's own rules, also for its condition fields)."""
    from ..spec import SpecError
    conn = (conns if conns is not None else spec.get("connections") or {}).get(nd.get("conn"))
    checks = [lambda: values.flag(nd, "connected"), lambda: values.text(nd, "object", "", what="an object path")]
    checks += [] if conn is None else [lambda: _kind_and_objkind(conn, nd)]      # an unknown conn: lint's CONN_UNKNOWN
    connected = values.as_flag(nd.get("connected"), "") if values.is_flag(nd.get("connected")) else True
    if not connected:
        checks += [lambda: values.text(nd, "query", "", what="SQL"), lambda: values.text(nd, "ret", what="a field name"),
                   lambda: _unconnected_cond(nd) if nd.get("cond") else None, lambda: _policy(nd)]
    out = []
    for fn in checks:
        try:
            fn()
        except SpecError as e:
            out.append(("NODE_MALFORMED", str(e)))
        except KeyError:          # "ret" missing: lint's LKP_FIELD
            pass
    if connected:
        out += _connected_problems(spec, nd, analysis, conns)
    return out


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
# (cache and dynamicCache are read by nodes/lookup_connected.py, for a connected lookup)
build.options = frozenset(['conn', 'object', 'query', 'fields', 'cond', 'ret', 'policy', 'connected', 'objkind', 'cache', 'dynamicCache'])
