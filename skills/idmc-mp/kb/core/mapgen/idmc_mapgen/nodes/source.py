"""Source: a table/view/file object or a custom query, read through the connection's adapter.

query, object and objkind are text (a number becomes its text; true / false, a list or an object is a SpecError); the
fields are field tuples (imf.field_tuple). ``options`` reads them for the build and its lint hook (``lint_problems``)
alike.
"""
from .. import values
from ..imf import adapter_fields, field_tuple, read_options, tx_fields
from ..registry import node


def options(nd, kind):
    """(query, object, objkind) of a source on a connection of ``kind``, as the build reads them. objkind is None
    unless the object needs it (a PG / JDBC object without /TABLE/ or /VIEW/: <schema>/<table> becomes
    <schema>/<objkind>/<table>, and only there is objkind read)."""
    q = values.text(nd, "query", "", what="SQL"); obj = values.text(nd, "object", "", what="an object path")
    needs = kind in ("PG", "JDBC") and obj and "/TABLE/" not in obj and "/VIEW/" not in obj
    return q, obj, (values.text(nd, "objkind", "TABLE", what="TABLE or VIEW") if needs else None)


@node("source", doc="Read a table, view, flat file or custom query. Options: conn, object | query, fields, objkind (PG/JDBC: TABLE|VIEW), "
                    "filter (the source's own filter condition, e.g. a Salesforce SOQL WHERE condition), sfObject (true: Salesforce object "
                    "attributes owner/resource as IDMC exports them).")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    g = b.group("DefaultGroup", False, True, rule=False)
    conn = ctx.conn(nd["conn"]); kind = conn.get("kind", "BQ")
    q, obj, objkind = options(nd, kind)
    if objkind is not None:
        parts = obj.split("/")
        if len(parts) != 2 or not all(parts):
            from ..spec import SpecError
            raise SpecError("source %r: object %r on a %s connection must be <schema>/<table> (or <schema>/TABLE/<table>, "
                            "<schema>/VIEW/<view>)" % (name, obj, kind))
        obj = "%s/%s/%s" % (parts[0], objkind, parts[1])
    afs = adapter_fields(b, nd["fields"], "CUSTOM_TABLE" if q else obj.split("/")[-1])
    dobj = b.new("DataObject", name=obj, customQuery=q, dbSchema="", label=obj, objectName=obj.split("/")[-1] if obj else "",
                 objectType="" if q else "TABLE", parentPath="", path=obj, retainMetadata="false", fields=afs)
    if not q and kind == "SF" and values.imf_bool(nd.get("sfObject", False)) == "true":
        # opt-in: the object attributes IDMC itself writes for a Salesforce object (an exported Salesforce source)
        dobj["objectAttributes"] = [b.new("Option", name="owner", value=""), b.new("Option", name="resource", value="")]
    elif not q:
        dobj["objectAttributes"] = [b.new("Option", name="tableType", value="TABLE")]
    if kind == "FF":   # CSV flat file through the native CSVFile adapter
        for af in afs:
            af["nativeType"] = "nstring"; af["javaType"] = ""; af["fieldStatus"] = "MODIFIED"; af.pop("metaExtensions", None)
        dobj = b.new("DataObject", name=obj, customQuery="", dbSchema="", label=obj, objectName="", objectType="", parentPath="", path=obj,
                     retainMetadata="false", fields=afs,
                     fileAttrs=b.new("FlatFileAttrs", consecutiveDelimiter="false", customRowDelimiter="", delimiter=",", escapeChar="",
                                     firstDataRow=2, firstDataRowAsHeader="false", headerAndDataDelimiter=0, headerLineNo=1,
                                     multiDelimitersAsAnd="true", rowDelimiter=0, textQualifier='"'))
    da = b.new("BaseAdapter", name="", codePage="", compatibleEngine="", connectionId="saas:@" + conn["guid"],
               connectionSelectionType="", excludeDynamicFileNameField="false", fwConfigId="", multipleObject="false",
               objectType="QUERY" if q else "SINGLE", typeSystem=conn.get("typeSystem", "CSVFile" if kind == "FF" else "TOOLKIT"),
               useDynamicFileName="false", object=dobj,
               oprRuntimeAttributes=b.new("RuntimeAttributes"),
               readOptions=read_options(b, values.text(nd, "filter", "", what="a filter condition")),
               runtimeAttributes=b.new("RuntimeAttributes"))
    tx = b.new("TmplSource", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal"), ("Pre SQL", ""), ("Post SQL", ""), ("Sql Override", ""),
                                         ("Output is deterministic", "false"), ("Output is repeatable", "")] +
                                        ([("Thousand Separator", "None"), ("Decimal Separator", "."), ("Datetime Format", "")] if kind == "FF" else [])),
               groups=[g], generateFilenamePort="false", useLabels="false", useSequenceFields="false",
               fields=tx_fields(b, nd["fields"], afs), dataAdapter=da)
    ctx.out(name, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this source's values (``options``, on the node's connection;
    an unknown connection is lint's CONN_UNKNOWN, the object path's shape its PG_OBJECT_PATH) and its field tuples
    (imf.field_tuple; an unknown TYPE is lint's TYPE_UNKNOWN / TYPE_JSON)."""
    conn = (conns if conns is not None else spec.get("connections") or {}).get(nd.get("conn"))
    readers = [lambda: [field_tuple(fd, i) for i, fd in enumerate(nd["fields"]) if values.lint_reads_type(fd)]]
    if isinstance(conn, dict):
        readers.insert(0, lambda: options(nd, conn.get("kind", "BQ")))
    return values.refusals(nd, *readers)


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['conn', 'object', 'query', 'fields', 'objkind', 'filter', 'sfObject'])

values.lint_hook("source", lint_problems)      # lint reports what the build refuses (values.lint_hook)
