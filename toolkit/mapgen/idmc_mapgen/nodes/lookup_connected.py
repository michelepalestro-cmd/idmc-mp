"""Connected Lookup: every incoming row looks up a table or query, and the lookup's fields join the row.

Spec (a "lookup" node with "connected": true):

    {"type": "lookup", "name": "LKP_STORE", "connected": true, "conn": "WH",
     "object": "dataset/stores" | "query": "SELECT ...",
     "fields": [["lk_store_id", "STRING", 64], ["lk_region", "STRING", 8], ["store_name", "STRING", 128]],
     "cond": [["lk_store_id", "store_id"], ["lk_region", "=", "region"]],   # [lookup field, (op,) incoming field]
     "policy": "Use First Value"}

- ``fields`` are the lookup object's columns you need (condition columns and the ones you want back). All of
  them leave the lookup as ports, so give them names that do not collide with incoming fields (``lk_`` prefix).
- Operators: = != < <= > >=. ``policy``: Use First Value | Use Last Value | Use Any Value | Use All Values |
  Report Error ("Use All Values" returns one row per match).
- A row with no match keeps flowing with NULL lookup fields (default-value semantics).
- Optional: ``cache`` false = uncached lookup (one query per row), ``dynamicCache`` true (insert/update the cache
  as rows pass; adds NewLookupRow).

lint runs the same rules (``lint_problems``, merged in by nodes/lookup.py's lint hook), so it refuses exactly the
policies, cond entries and condition fields this builder refuses, with the same messages.
"""
from .. import values
from ..imf import adapter_fields, read_options, tx_fields
from ..registry import node  # noqa: F401  (registry import keeps the module self-describing)
from ..spec import SpecError

OPS = {"=", "!=", "<", "<=", ">", ">="}
POLICIES = {"Use First Value", "Use Last Value", "Use Any Value", "Use All Values", "Report Error"}


def _conds(nd):
    out = []
    for c in nd["cond"]:
        if len(c) == 2:
            l, op, r = c[0], "=", c[1]
        elif len(c) == 3:
            l, op, r = c
        else:
            raise ValueError("lookup %r: cond entries are [lookup_field, incoming_field] or [lookup_field, op, incoming_field]" % nd["name"])
        if op not in OPS:
            raise ValueError("lookup %r: operator %r not in %s" % (nd["name"], op, sorted(OPS)))
        out.append((l, op, r))
    return out


def _policy(nd):
    """The multiple-match policy (SpecError for one outside POLICIES)."""
    policy = nd.get("policy", "Use Any Value")
    if policy not in POLICIES:
        raise SpecError("lookup %r: policy %r not in %s" % (nd["name"], policy, sorted(POLICIES)))
    return policy


def _checked_conds(nd):
    """[(lookup field, op, incoming field)] of "cond"; SpecError for an entry that is not [lookup_field,
    incoming_field] / [lookup_field, op, incoming_field], or an operator outside OPS."""
    try:
        return _conds(nd)
    except ValueError as e:
        raise SpecError(str(e)) from None


def _declared(nd):
    """The names of the lookup's fields (the first item of each [name, TYPE, ...]); SpecError when "fields" is not a
    list. Entries that are not such a list are left to adapter_fields, which refuses them."""
    fields = nd.get("fields")
    if not isinstance(fields, (list, tuple)):
        raise SpecError("lookup %r: 'fields' must be the list of the lookup object's columns [[name, TYPE, ...], ...] "
                        "(its condition fields and the fields it returns), got %.60r" % (nd["name"], fields))
    return {fd[0] for fd in fields if isinstance(fd, (list, tuple)) and fd}


def _undeclared(nd, conds, declared):
    """The refusal of condition lookup fields that are not the name of one of its fields (compared exactly), or None."""
    missing = [l for l, _, _ in conds if l not in declared]
    return "lookup %r: condition fields %s are not in its fields" % (nd["name"], missing) if missing else None


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)] for what build_connected refuses in a connected lookup, with its own messages: a policy
    outside POLICIES, "fields" that is not a list, a cond entry that is not [lookup_field, (op,) incoming_field] or has
    an operator outside OPS (NODE_MALFORMED), condition fields that are not in its fields, compared exactly as the
    builder compares them (LKP_FIELD). No cond at all is lint's own NODE_MALFORMED; the connection and the object are
    lookup.py's and lint's."""
    out = values.refusals(nd, lambda: _options(nd))
    try:
        _policy(nd)
    except SpecError as e:
        out.append(("NODE_MALFORMED", str(e)))
    try:
        declared = _declared(nd)
    except SpecError as e:
        out.append(("NODE_MALFORMED", str(e)))
        declared = None
    except Exception as e:      # a field name the builder cannot read either (a list: unhashable)
        out.append(("NODE_MALFORMED", "lookup %r: fields cannot be read (%s: %s)" % (nd["name"], type(e).__name__, e)))
        declared = None
    if not nd.get("cond"):
        return out
    try:
        conds = _checked_conds(nd)
    except SpecError as e:
        return out + [("NODE_MALFORMED", str(e))]
    except Exception as e:      # a cond the builder cannot even read (not a list of lists): it fails there too
        return out + [("NODE_MALFORMED", "lookup %r: cond %.60r cannot be read (%s: %s)" % (nd["name"], nd["cond"], type(e).__name__, e))]
    problem = None if declared is None else _undeclared(nd, conds, declared)
    return out + ([("LKP_FIELD", problem)] if problem else [])


def _options(nd):
    """(query, object, cache, dynamicCache) as build_connected reads them."""
    return (values.text(nd, "query", "", what="SQL"), values.text(nd, "object", "", what="an object path"),
            values.flag(nd, "cache", True), values.flag(nd, "dynamicCache"))


def build_connected(ctx, nd):
    b = ctx.b; name = nd["name"]
    policy = _policy(nd)
    conds = _checked_conds(nd)
    problem = _undeclared(nd, conds, _declared(nd))
    if problem:
        raise SpecError(problem)
    g = b.group("DefaultGroup", True, True)
    q, obj, cache, dynamic = _options(nd)
    conn = ctx.conn(nd["conn"])
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
    cached = values.imf_bool(cache)
    adv = [("Tracing Level", "Normal"), ("Lookup caching enabled", cached), ("Lookup cache directory name", "$PMCacheDir"),
           ("Lookup cache persistent", "false"), ("Cache File Name Prefix", ""), ("Re-cache from lookup source", "false"),
           ("Lookup Data Cache Size", "AUTO"), ("Lookup Index Cache Size", "AUTO"), ("Null ordering", ""), ("Sorted Input", "false"),
           ("Lookup source is static", "false"), ("Pre-build lookup cache", "AUTO"), ("Optional", "true")]
    if dynamic:
        adv.append(("Dynamic Lookup Cache", "true"))
    tx = b.new("TmplLookup", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv(adv),
               groups=[g],
               advancedInputPortNames="", associatedFields="", lookupCondition="", multipleMatchPolicy=policy,
               returnPortName="", unconnected="false", useLabels="false", fields=tx_fields(b, nd["fields"], afs),
               inputPortNames=[],
               lookupConditions=[b.new("LookupCondition", leftOperand=l, operator=op, rightOperand=r) for l, op, r in conds],
               dataAdapter=da)
    ctx.out(name, g); ctx.inp(name, g)
    return tx
