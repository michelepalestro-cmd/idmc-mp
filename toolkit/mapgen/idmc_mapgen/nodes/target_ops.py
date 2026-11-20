"""Target write operations beyond Insert, plus connector writer attributes (template hook over every target).

    {"type": "target", ..., "op": "Upsert", "updateColumns": ["order_id"]}
    {"type": "target", ..., "op": "Data Driven", "updateColumns": ["order_id"],
     "updateStrategy": "DECODE(op_flag, 'I', DD_INSERT, 'U', DD_UPDATE, 'D', DD_DELETE, DD_REJECT)"}
    {"type": "target", ..., "writerAttrs": {"opr": {"TruncateTable": "YES"}, "rt": {"Truncate target": "YES"}}}

- ``op``: Insert | Update | Upsert | Delete | Data Driven. IMF calls Data Driven "Rowbased"; both spellings work.
- ``updateColumns``: the key columns that Update / Upsert / Delete / Data Driven match on (flagged key="true").
- ``updateStrategy``: the row-level expression of a Data Driven target (DD_INSERT, DD_UPDATE, DD_DELETE,
  DD_REJECT). Giving it implies op = Data Driven. Rows flagged DD_REJECT count as failed rows (run state WARNING).
- ``writerAttrs``: extra writer attributes for ANY connector: "opr" = internal names (oprRuntimeAttributes),
  "rt" = display names (runtimeAttributes). The base target builder only writes runtime attributes for
  BigQuery; this is how PostgreSQL/JDBC targets get theirs.

Connector defaults added automatically (an explicit writerAttrs / oprAttrs / rtAttrs entry of the same name wins):
- BigQuery Upsert: UpdateMode = "Update Else Insert". Without it the BigQuery writer runs only an UPDATE, so
  new keys are silently dropped.
- BigQuery Data Driven: Enable Merge + Enable Data Driven = YES (isMergeEnabled / isDataDrivenEnabled).
  Without them the writer ignores the row flags and UPDATEs every row (a DD_DELETE row overwrites the target).
- PostgreSQL Upsert: UpdateMode = "Update Else Insert" (the writer default "Update As Update" never inserts).
Measured on a real Secure Agent; see docs/PROBES.md.

The options are read as the target builder reads them (nodes/target.py ``options``): "truncate" is a boolean
(true / false, "true" / "false" in any case, 0 / 1 -- "truncate": "false" used to add TruncateTable = YES), and
updateStrategy, pre/post SQL and the writerAttrs values are text (a number becomes its text).
"""
from ..registry import template_hook
from .target import options as target_options

OPS = {"insert": "Insert", "update": "Update", "upsert": "Upsert", "delete": "Delete",
       "data driven": "Rowbased", "datadriven": "Rowbased", "data_driven": "Rowbased", "rowbased": "Rowbased"}

# (connector kind, IMF operation) -> ([(opr name, value)], [(rt name, value)])
DEFAULT_WRITER_ATTRS = {
    ("BQ", "Upsert"): ([("UpdateMode", "Update Else Insert")], [("UpdateMode", "Update Else Insert")]),
    ("BQ", "Rowbased"): ([("isMergeEnabled", "YES"), ("isDataDrivenEnabled", "YES")],
                         [("Enable Merge", "YES"), ("Enable Data Driven", "YES")]),
    ("PG", "Upsert"): ([("UpdateMode", "Update Else Insert")], [("Update Mode", "Update Else Insert")]),
}


def write_op(nd):
    """The IMF operation for a target node (None = leave the builder's value)."""
    op = nd.get("op")
    if target_options(nd)["updateStrategy"] and (op is None or str(op).lower() in ("data driven", "datadriven", "data_driven", "rowbased")):
        return "Rowbased"
    if op is None:
        return None
    key = str(op).strip().lower()
    if key not in OPS:
        from ..spec import SpecError
        raise SpecError("target %r: op %r not in Insert, Update, Upsert, Delete, Data Driven" % (nd["name"], op))
    return OPS[key]


def _existing(container):
    return {a.get("name") for a in container.get("attributes") or []}


def _append(b, container, pairs):
    have = _existing(container)
    new = [b.new("RuntimeAttribute", name=k, value=v) for k, v in pairs if k not in have]
    if new:
        container["attributes"] = list(container.get("attributes") or []) + new


@template_hook
def apply_target_ops(ctx, content):
    from ..spec import SpecError
    b = ctx.b
    by_name = {t["name"]: t for t in ctx.txs}
    for nd in ctx.spec["nodes"]:
        if nd.get("type") != "target":
            continue
        tx = by_name[nd["name"]]
        da = tx["dataAdapter"]
        o = target_options(nd)
        op = write_op(nd)
        if op is not None:
            wo = da["writeOptions"]
            wo["operations"] = [op]
            if op == "Rowbased":
                if not o["updateStrategy"]:
                    raise SpecError("target %r: a Data Driven target needs \"updateStrategy\" (an expression returning DD_INSERT / "
                                    "DD_UPDATE / DD_DELETE / DD_REJECT)" % nd["name"])
                wo["updateStrategyExpression"] = o["updateStrategy"]
            if op != "Insert" and not o["updateColumns"]:
                raise SpecError("target %r: op %s needs \"updateColumns\" (the key columns to match on)" % (nd["name"], nd.get("op")))
        if nd.get("writerAttrs"):
            _append(b, da["oprRuntimeAttributes"], o["writerAttrs"]["opr"])
            _append(b, da["runtimeAttributes"], o["writerAttrs"]["rt"])
        kind = ctx.kind(nd["conn"])
        opr_def, rt_def = DEFAULT_WRITER_ATTRS.get((kind, op or "Insert"), ([], []))
        opr_def, rt_def = list(opr_def), list(rt_def)
        pre, post = o["pre"], o["post"]
        sql_names = {"BQ": (("preSQLWriter", "pre SQL"), ("postSQLWriter", "post SQL")),
                     "PG": (("preSQL", "Pre-SQL"), ("postSQL", "Post-SQL"))}.get(kind)
        if sql_names and (pre or post):
            # The BigQuery and PostgreSQL writers ignore the transformation-level "Pre SQL"/"Post SQL" properties
            # and run these writer attributes instead; move the SQL there so it runs exactly once.
            (pre_o, pre_r), (post_o, post_r) = sql_names
            if pre:
                opr_def.append((pre_o, pre)); rt_def.append((pre_r, pre))
            if post:
                opr_def.append((post_o, post)); rt_def.append((post_r, post))
            for p in tx.get("advancedProperties", []):
                if p.get("name") in ("Pre SQL", "Post SQL"):
                    p["value"] = ""
        if kind == "PG" and o["truncate"]:
            # The PostgreSQL writer ignores WriteOptions.truncate; it reads TruncateTable (booleans are YES/NO:
            # "true" is rejected and falls back to NO).
            opr_def.append(("TruncateTable", "YES")); rt_def.append(("Truncate target", "YES"))
        if opr_def or rt_def:
            _append(b, da["oprRuntimeAttributes"], opr_def)
            _append(b, da["runtimeAttributes"], rt_def)
