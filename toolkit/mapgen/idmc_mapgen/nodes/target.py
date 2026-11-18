"""Target: write to a table through the connection's adapter (BigQuery write disposition, PG/JDBC paths, SaaS upserts).

BigQuery targets poll their load job every second by default: oprRuntimeAttributes jobPollInterval = pollInterval = "1"
and runtimeAttributes "Job Poll Interval In Seconds" = "1" (the writer's own default is 10 s per target; the same mapping
ran 127 s -> 56 s, L-CDI-200). An attribute of the same name given in extra_opr / oprAttrs / extra_rt / rtAttrs /
writerAttrs wins, and its value is the interval of the names the spec does not set (one interval, never a 5 / 1 mix);
"poll": <whole seconds> sets the interval of the names the spec does not set, "poll": false leaves them out (the target
then polls at whatever the spec sets itself, else every 10 s: lint BQ_TGT_POLL), "poll": null is the default.

Option values (idmc_mapgen/values.py): truncate / createTarget are booleans (true / false, "true" / "false" in any
case, 0 / 1; "poll" takes "true" / "false" too, while a number there is seconds); object, disposition, op,
pre_sql / post_sql, updateStrategy, updateColumns and the attribute names and values are text (a number becomes its
text, true / false / a list / an object is refused); the fields are field tuples (imf.field_tuple). ``options(nd)``
and ``field_tuples(nd)`` read them all, for the build and its lint hook (``lint_problems``) alike.
"""
from .. import values
from ..imf import adapter_fields, field_tuple, tx_fields
from ..registry import node

# (oprRuntimeAttributes names, runtimeAttributes names) of the BigQuery writer's job poll interval
POLL_ATTRS = (("jobPollInterval", "pollInterval"), ("Job Poll Interval In Seconds",))
_POLL_KEYS = (("extra_opr", "oprAttrs", "opr"), ("extra_rt", "rtAttrs", "rt"))   # (pair list, dict, writerAttrs key)
_ATTR = "an attribute value"


def _first_text(nd, keys, what):
    """The first of ``keys`` that the node gives (not null), as text; "" when none."""
    for k in keys:
        if nd.get(k) is not None:
            return values.text(nd, k, what=what)
    return ""


def sql_text(nd):
    """(pre SQL, post SQL) of a target: pre_sql (else preSQL) and post_sql (else postSQL), as text ("" = none)."""
    return _first_text(nd, ("pre_sql", "preSQL"), "SQL"), _first_text(nd, ("post_sql", "postSQL"), "SQL")


def writer_attrs(nd):
    """{"opr": [(name, value)], "rt": [(name, value)]} of a target's "writerAttrs" (target_ops writes them; the poll
    default reads them): objects {name: value} of texts."""
    wa = nd.get("writerAttrs")
    if wa is None:
        return {"opr": [], "rt": []}
    if not isinstance(wa, dict):
        from ..spec import SpecError
        raise SpecError("%s must be an object {\"opr\": {name: value}, \"rt\": {name: value}}, got %s"
                        % (values.where(nd, "writerAttrs"), values.brief(wa)))
    out = {}
    for side in ("opr", "rt"):
        sub = wa.get(side)
        if sub is not None and not isinstance(sub, dict):
            from ..spec import SpecError
            raise SpecError("%s must be an object {name: value}, got %s" % (values.where(nd, "writerAttrs." + side), values.brief(sub)))
        out[side] = [(k, values.as_text(v, values.where(nd, "writerAttrs.%s %r" % (side, k)), what=_ATTR)) for k, v in (sub or {}).items()]
    return out


def options(nd):
    """A target's options as the build reads them (SpecError naming the target and the option for a value it refuses).
    "object" is checked when given (the build needs it: a missing one is its "missing or unknown key")."""
    truncate = values.flag(nd, "truncate")
    pre, post = sql_text(nd)
    return {"truncate": truncate, "createTarget": values.flag(nd, "createTarget"),
            "object": values.text(nd, "object", default="", what="an object path"),
            "disposition": values.text(nd, "disposition", "Write truncate" if truncate else "Write append", what="a write disposition"),
            "op": values.text(nd, "op", "Insert", what="a write operation"),
            "updateColumns": values.text_list(nd, "updateColumns"), "pre": pre, "post": post,
            "updateStrategy": values.text(nd, "updateStrategy", "", what="an update strategy expression"),
            "extra_opr": values.text_pairs(nd, "extra_opr", _ATTR), "extra_rt": values.text_pairs(nd, "extra_rt", _ATTR),
            "oprAttrs": values.text_map(nd, "oprAttrs", _ATTR), "rtAttrs": values.text_map(nd, "rtAttrs", _ATTR),
            "writerAttrs": writer_attrs(nd)}


def _own_poll(nd):
    """The values the spec itself gives the poll interval attributes (extra_* pairs, *Attrs, writerAttrs; opr first)."""
    vals, wa = [], writer_attrs(nd)
    for names, (lst, dct, wkey) in zip(POLL_ATTRS, _POLL_KEYS):
        pairs = values.text_pairs(nd, lst, _ATTR) + list(values.text_map(nd, dct, _ATTR).items()) + wa[wkey]
        vals += [v for k, v in pairs if k in names and v != ""]
    return vals


def poll_seconds(nd):
    """The interval written for the poll attributes the spec does not set itself, None for "poll": false: "poll":
    <whole seconds>, else the value of a poll attribute the spec does set, else "1". "poll" also takes the strings
    "true" / "false" (any case); a number is seconds ("1" and 0 are refused)."""
    p = nd.get("poll")
    if isinstance(p, str) and values.is_flag(p):
        p = values.as_flag(p, values.where(nd, "poll"))
    if p is None or p is True:
        own = _own_poll(nd)
        return own[0] if own else "1"
    if p is False:
        return None
    if isinstance(p, int) and p > 0:
        return str(p)
    from ..spec import SpecError
    raise SpecError("target %r: poll %r must be true, false (also \"true\" / \"false\") or a whole number of seconds > 0"
                    % (nd["name"], p))


def poll_interval(nd):
    """The job poll interval a BigQuery target ends up with: its own attribute, else what the generator writes; None =
    the writer's 10 s default ("poll": false and no poll attribute of its own)."""
    secs = poll_seconds(nd)
    own = _own_poll(nd)
    return own[0] if own else secs


def field_tuples(nd, lint=False):
    """The target's field tuples as the build reads them (imf.field_tuple: name, TYPE, precision, scale, nativeType,
    connector flags). ``lint``: without the fields of an unknown TYPE (lint's own TYPE_UNKNOWN / TYPE_JSON)."""
    return [field_tuple(fd, i) for i, fd in enumerate(nd["fields"]) if not lint or values.lint_reads_type(fd)]


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)] for what this builder decides about a target: a value the build refuses, in the build's
    words -- an option (``options``: a boolean that is not one, text that is true / a list...) or a field tuple
    (``field_tuples``: a precision / scale that is not a whole number or a scale above the precision, a nativeType
    that is not text, connector flags that are not an object of booleans; an unknown TYPE is lint's TYPE_UNKNOWN) --,
    an invalid "poll" on a BigQuery target (the build refuses it) and a BigQuery target left at the writer's 10 s job
    poll (BQ_TGT_POLL). lint runs it for every target (values.lint_hook below); lint.py's _check_target also runs it
    for BigQuery targets, and lint drops the issues raised twice."""
    from ..spec import SpecError
    out = values.refusals(nd, lambda: options(nd), lambda: field_tuples(nd, lint=True))
    if out:
        return out
    conn = (conns if conns is not None else spec.get("connections") or {}).get(nd.get("conn")) or {}
    if conn.get("kind", "BQ") != "BQ":
        return []                       # the poll attributes are BigQuery's ("poll" elsewhere: TGT_ATTRS_IGNORED)
    try:
        secs = poll_interval(nd)
    except SpecError as e:
        return [("NODE_MALFORMED", str(e))]
    if secs is None:
        return [("BQ_TGT_POLL", "target %r: \"poll\": false and no poll attribute of its own: the writer polls every 10 s"
                 % nd.get("name"))]
    return []


def _runtime_attrs(b, nd, kind, disp, names, pairs, writer, poll_names):
    """BigQuery runtime attributes: disposition (omitted when "NONE"), mode Bulk, the extra pairs (``pairs``: the
    extra_* list, then the *Attrs object), then the poll interval attributes the spec does not set itself (``writer``:
    the writerAttrs pairs of this container count as set); empty for other kinds.

    The attribute objects are created before their RuntimeAttributes container (same id order as the legacy code).
    """
    if kind != "BQ":
        return b.new("RuntimeAttributes")
    disp_name, mode_name = names
    attrs = ([] if disp == "NONE" else [b.new("RuntimeAttribute", name=disp_name, value=disp)]) + \
        [b.new("RuntimeAttribute", name=mode_name, value="Bulk")] + \
        [b.new("RuntimeAttribute", name=k, value=v) for k, v in pairs]
    secs = poll_seconds(nd)
    if secs:
        have = {a["name"] for a in attrs} | {k for k, _ in writer}
        attrs += [b.new("RuntimeAttribute", name=k, value=secs) for k in poll_names if k not in have]
    return b.new("RuntimeAttributes", attributes=attrs)


@node("target", doc="Write to a target object (a table, a file, a SaaS object; any connector, see the Fast Path 7.0 for one with no template). Options: conn, object, fields, truncate, disposition (Write truncate|Write append|NONE), "
                    "op (Insert|Update|Upsert|Delete|Data Driven), updateColumns, createTarget, pre_sql/preSQL, post_sql/postSQL, "
                    "extra_opr/oprAttrs, extra_rt/rtAttrs, poll (BigQuery job poll interval: default 1 s, or the value of a poll "
                    "attribute the spec sets; whole seconds; false = only the spec's own attributes, else the writer's 10 s).")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    o = options(nd)
    g = b.group("DefaultGroup", True, False)
    obj = values.text(nd, "object", what="an object path")
    conn = ctx.conn(nd["conn"]); kind = conn.get("kind", "BQ")
    if kind in ("PG", "JDBC") and "/TABLE/" not in obj:
        parts = obj.split("/")
        if len(parts) != 2 or not all(parts):
            from ..spec import SpecError
            raise SpecError("target %r: object %r on a %s connection must be <schema>/<table> (or <schema>/TABLE/<table>)"
                            % (name, obj, kind))
        obj = "%s/TABLE/%s" % tuple(parts)
    afs = adapter_fields(b, nd["fields"], obj.split("/")[-1], o["updateColumns"])
    dobj = b.new("DataObject", name=obj, customQuery="", dbSchema="", label=obj, objectName=obj.split("/")[-1], objectType="TABLE",
                 parentPath="", path=obj, retainMetadata="false", fields=afs,
                 objectAttributes=[b.new("Option", name="owner", value=""), b.new("Option", name="resource", value="")])
    disp = o["disposition"]
    da = b.new("BaseAdapter", name="", codePage="", compatibleEngine="", connectionId="saas:@" + conn["guid"],
               connectionSelectionType="", excludeDynamicFileNameField="false", fwConfigId="", multipleObject="false",
               objectType="SINGLE", typeSystem=conn.get("typeSystem", "TOOLKIT"), useDynamicFileName="false",
               bulkOptions=b.new("BulkOptions", hardDelete="false", maxRowsPerRequest=0, monitorBulk="false", monitorBulkV2="false",
                                 pkChunkingEnabled="false", pkChunkingSize=0, pkChunkingStartRowId="", serialMode="false",
                                 useBulkApi="false", useBulkApiV2="false"),
               object=dobj,
               oprRuntimeAttributes=_runtime_attrs(b, nd, kind, disp, ("writeDisposition", "writeMode"),
                                                   o["extra_opr"] + list(o["oprAttrs"].items()), o["writerAttrs"]["opr"], POLL_ATTRS[0]),
               runtimeAttributes=_runtime_attrs(b, nd, kind, disp, ("Write Disposition", "Write Mode"),
                                                o["extra_rt"] + list(o["rtAttrs"].items()), o["writerAttrs"]["rt"], POLL_ATTRS[1]),
               writeOptions=b.new("WriteOptions", batchSize=values.as_whole(nd.get("batchSize"), name + " batchSize", 0, 0, "0 (the writer default)"), bulkApi="false", errorFileDirectory="", errorFilePrefix="",
                                  handleDecimalRoundOff="false", handleSpecialChars="false", operations=[o["op"]],
                                  setFieldsToNull="false", successFileDirectory="", successFilePrefix="",
                                  truncate=values.imf_bool(o["truncate"]), updateStrategyExpression="",
                                  useErrorFile="false", useExactSrcNames="false", useSuccessFile="false"))
    tx = b.new("TmplTarget", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Forward Rejected Rows", "true"), ("Pre SQL", o["pre"]), ("Post SQL", o["post"]),
                                         ("Update Override", "")]),
               groups=[g], createTarget=values.imf_bool(o["createTarget"]), fieldMappingMode="BY_NAME", inputSorted="false",
               schemaProviderType="SELECTED_OBJECT", targetFieldsOrdered="false", updateColumns=o["updateColumns"],
               useLabels="false", useSequenceFields="false",
               fields=tx_fields(b, nd["fields"], afs), dataAdapter=da, manualMappings=b.new("FieldMappings"))
    ctx.inp(name, g)
    return tx


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
# (updateStrategy and writerAttrs are read by ``options`` and written by nodes/target_ops.py's template hook)
build.options = frozenset(['conn', 'object', 'fields', 'truncate', 'disposition', 'op', 'updateColumns', 'createTarget', 'pre_sql', 'preSQL', 'post_sql', 'postSQL', 'extra_opr', 'oprAttrs', 'extra_rt', 'rtAttrs', 'poll', 'updateStrategy', 'writerAttrs', 'batchSize'])

values.lint_hook("target", lint_problems)      # lint reports what the build refuses (values.lint_hook)
