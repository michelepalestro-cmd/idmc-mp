"""SQL transformation (EXPERIMENTAL: imports, but runs fail - see docs/PROBES.md; needs "allowUnsupported": true).

Runs a query (or stored procedure) against a database for every row that passes.

    {"type": "sql", "name": "SQL_STOCK", "conn": "PG",
     "query": "SELECT on_hand FROM inv.stock WHERE sku = ?sku? AND store_id = ?store_id?",
     "inputs":  [["sku", "STRING", 64, "character_varying", 0], ["store_id", "STRING", 16, "character_varying", 0]],
     "outputs": [["on_hand", "INTEGER", 19, "bigint", 0]],
     "map": {"sku": "sku", "store_id": "store_id"},
     "sqlType": "ENTERED_QUERY"}

- ``?field?`` binds an input field as a query parameter; ``~field~`` substitutes its text into the query.
- ``inputs`` / ``outputs`` use the field tuple of sources and targets ([name, TYPE, prec, nativeType, scale]).
- ``map``: SQL input field -> incoming field (default: the same name).
- ``passthrough``: incoming fields to carry through (declared like inputs; they become pass-through ports).
  Passive: one output row per input row (the first result row). A generated ``SQLError`` port carries the
  database error text of a failed row.
- ``sqlType``: ENTERED_QUERY (default) | STORED_PROCEDURE | STORED_FUNCTION (then ``query`` is the procedure name).
- ``allowUnsupported`` / ``continueOnError`` (default true) are booleans (true / false, "true" / "false" in any case,
  0 / 1: "allowUnsupported": "false" used to build); query, sqlType, errorNativeType, field names and native types
  and the map's incoming names are text (a number becomes its text; true / false, a list or an object is a
  SpecError). A field's null precision / nativeType / scale is the default, precision and scale are whole numbers,
  and the scale may not exceed the precision (a NUMERIC with a precision below 9 needs its scale).
- ``options`` reads them all (and refuses the node without allowUnsupported), for the build and its lint hook
  (``lint_problems``) alike.
"""
from .. import values
from ..registry import node
from ..types import typeinfo

NS = "com.informatica.metadata.template.tx.tmplsql."
_TUPLE_HOW = "[name, TYPE, precision, nativeType, scale]"


def _adapter_field(b, name, t, prec, native, scale, generated=False):
    pt, dprec, dsc, jt = typeinfo(t)
    return b.new("BaseAdapterField", name=name, createable="false", externalId="false", fieldStatus="UNDEFINED",
                 fieldType="UNDEFINED", filterable="false" if generated else "true", foreignKey="false",
                 generated="true" if generated else "false", javaType=jt, key="false", label=name, nativeName="" if generated else name,
                 nativeType=native, newField="false", nullable="true", original="false", passthroughPort="false",
                 precision=prec, scale=scale, sfIdLookup="false", unique="false", updateable="false")


def _sql_field(b, af, name, t, prec, scale, direction):
    return b.new("SqlField", adapterField=b.ref(af), defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                 isDefaultValueUpdated="false", name=name, platformType=b.ptype(t), precision=prec, scale=scale, fieldType=direction)


def _tuple(nd, key, i, fd):
    name = values.as_text(fd[0], values.where(nd, "%s[%d] name" % (key, i)), what="a field name")
    at = values.where(nd, "%s %r" % (key, name))
    t = fd[1]
    prec, sc = values.precision_scale(t, fd[2] if len(fd) > 2 else None, fd[4] if len(fd) > 4 else None, at, _TUPLE_HOW)
    native = values.as_text(fd[3] if len(fd) > 3 else None, at + " nativeType", t.lower(), what="a native type name")
    return name, t, prec, native, sc


def _tuples(nd, key):
    return [_tuple(nd, key, i, fd) for i, fd in enumerate(nd.get(key, []))]


def options(nd):
    """The SQL node's options as the build reads them: (query, sqlType, errorNativeType, outputs, passthrough, inputs,
    map, continueOnError); SpecError for a value it refuses, and for a node without allowUnsupported."""
    from ..spec import SpecError
    if not values.flag(nd, "allowUnsupported"):
        raise SpecError("sql %r: the SQL transformation imports but its runs fail on a Secure Agent (the incoming fields "
                        "never link into it; see docs/PROBES.md). Set \"allowUnsupported\": true to build it anyway, or use a "
                        "connected lookup with a query (per-row lookups) or target pre/post SQL (set-based statements)." % nd["name"])
    query, sql_type = values.text(nd, "query", what="SQL"), values.text(nd, "sqlType", "ENTERED_QUERY", what="a SQL type")
    err_native = values.text(nd, "errorNativeType", "character_varying", what="a native type name")
    outputs, passthrough, inputs = _tuples(nd, "outputs"), _tuples(nd, "passthrough"), _tuples(nd, "inputs")
    return (query, sql_type, err_native, outputs, passthrough, inputs, values.text_map(nd, "map"),
            values.flag(nd, "continueOnError", True))


@node("sql", doc="SQL transformation: conn, query (?field? binds), inputs, outputs, map, sqlType.")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    query, sql_type, err_native, outputs, passthrough, inputs, mp, continue_on_error = options(nd)
    for cls in ("TmplSql", "SqlAdapter", "SqlField"):
        b.register(NS + cls)
    conn = ctx.conn(nd["conn"])
    g = b.group("DefaultGroup", True, True)
    afs, sfs = [], []
    err = _adapter_field(b, "SQLError", "STRING", 255, err_native, 0, generated=True)
    afs.append(err); sfs.append(_sql_field(b, err, "SQLError", "STRING", 255, 0, "OUT"))
    for n, t, prec, native, sc in outputs:
        af = _adapter_field(b, n, t, prec, native, sc); afs.append(af); sfs.append(_sql_field(b, af, n, t, prec, sc, "OUT"))
    for n, t, prec, native, sc in passthrough:   # incoming fields carried through the SQL transformation
        af = _adapter_field(b, n, t, prec, native, sc); af["passthroughPort"] = "true"
        afs.append(af); sfs.append(_sql_field(b, af, n, t, prec, sc, "INOUT"))
    ins = []
    for n, t, prec, native, sc in inputs:
        af = _adapter_field(b, n, t, prec, native, sc); afs.append(af); sfs.append(_sql_field(b, af, n, t, prec, sc, "IN"))
        ins.append((n, af))
    da = b.new("SqlAdapter", name="", connectionId="saas:@" + conn["guid"], nativeName="", sql=query, sqlDescription="",
               sqlMetadataEdited="true", sqlType=sql_type, typeSystem=conn.get("typeSystem", "TOOLKIT"),
               fields=afs, oprRuntimeAttributes=b.new("RuntimeAttributes"))
    kw = {}
    if ins:
        kw["fieldMapping"] = b.new("FieldMapping", fields=[
            b.new("TxField", adapterField=b.ref(af), defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                  isDefaultValueUpdated="false", name=mp.get(n, n), precision=0, scale=0) for n, af in ins])
    tx = b.new("TmplSql", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Is Active", "false"), ("Is_Continue_On_Error_Selected", values.imf_bool(continue_on_error)),
                                         ("Auto_Commit", "false"), ("Max_Out_Row_Count", "6000"), ("Tracing Level", "Normal"),
                                         ("Transformation Scope", "Row")]),
               groups=[g], fieldMappingMode="MANUAL", numRowsAffected="false", unconnected="false", fields=sfs, dataAdapter=da, **kw)
    ctx.out(name, g); ctx.inp(name, g)
    return tx


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['conn', 'query', 'inputs', 'outputs', 'passthrough', 'map', 'sqlType', 'allowUnsupported',
                           'continueOnError', 'errorNativeType'])


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this SQL node (``options``: no allowUnsupported, a value that
    is not a boolean / text, a field tuple's precision / scale)."""
    return values.refusals(nd, lambda: options(nd))


def _flow():
    try:
        from ..fieldflow import F, flow, fields
    except ImportError:
        return

    @flow("sql", override=True)
    def _sql(nd, inputs):
        got = inputs.get(nd["name"]) or fields()
        outs = [F("SQLError", "STRING", nd["name"])] + [F(fd[0], fd[1], nd["name"]) for fd in nd.get("outputs", [])]
        names = {f.name.lower() for f in outs}
        return {"": fields([f for f in got if f.name.lower() not in names] + outs, getattr(got, "unchecked", False))}


_flow()

values.lint_hook("sql", lint_problems)      # lint reports what the build refuses (values.lint_hook)
