"""Normalizer: turns repeating columns into rows (one output row per occurrence).

    {"type": "normalizer", "name": "NRM_QTY",
     "fields": [{"name": "store_id", "type": "STRING", "prec": 16},              # occurs 1: copied to every row
                {"name": "qty", "type": "INTEGER", "occurs": 3}],                 # qty_1..qty_3 -> qty
     "map": {"store_id": "store_id", "qty_1": "q_jan", "qty_2": "q_feb", "qty_3": "q_mar"},
     "generatedKey": false}

- ``fields``: the normalized fields. ``occurs`` > 1 makes inputs <name>_1..<name>_n and one output <name>, plus
  GCID_<name> (which occurrence the row came from, 1..n).
- ``map``: normalizer input field -> incoming field. Default: same name.
- ``generatedKey``: true adds GK_<first multiple-occurring field> (a generated row-group key). A boolean: true /
  false, "true" / "false" in any case, 0 / 1.
- Only the normalized fields (and GCID_/GK_) leave the Normalizer; incoming fields not listed are dropped.
- Field names and the map's incoming names are text (a number becomes its text); prec / scale are whole numbers
  (null = the type's default), and the scale may not exceed the precision (a NUMERIC with a precision below 9 needs
  its "scale"); occurs is a whole number >= 1 (default 1; int() used to turn 2.5 into 2 and true into 1).
- ``options`` reads them all, for the build and its lint hook (``lint_problems``) alike.
"""
from .. import values
from ..registry import node

NS = "com.informatica.metadata.template.tx.tmplnormalizer."


def _fields(nd):
    """[(name, TYPE, precision, scale, occurs)] of a normalizer's "fields", as the build reads them."""
    from ..spec import SpecError
    if not nd.get("fields"):
        raise SpecError("normalizer %r needs fields" % nd["name"])
    out = []
    for i, f in enumerate(nd["fields"]):
        fname = values.as_text(f["name"], values.where(nd, "fields[%d] name" % i), what="a field name")
        at = values.where(nd, "field %r" % fname)
        prec, sc = values.precision_scale(f["type"], f.get("prec"), f.get("scale"), at, '"scale"', names=("prec", "scale"))
        out.append((fname, f["type"], prec, sc, values.as_whole(f.get("occurs"), at + " occurs", 1, 1, "1")))
    return out


def options(nd):
    """(generatedKey, map, fields) of a normalizer node, as the build reads them."""
    generated_key, mp = values.flag(nd, "generatedKey"), values.text_map(nd, "map")
    return generated_key, mp, _fields(nd)


def _field_kw(b, name, t, prec, scale):
    return dict(defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                name=name, platformType=b.ptype(t), precision=prec, scale=scale)


@node("normalizer", doc="Repeating columns -> rows. fields: [{name, type, prec?, scale?, occurs?}], map: {input: incoming}, generatedKey.")
def build(ctx, nd):
    from ..spec import SpecError
    b = ctx.b; name = nd["name"]
    for cls in ("TmplNormalizer", "NormalizerFields", "NormalizerField", "NormalizerTxField",
                "NormalizerFieldMappings", "NormalizerFieldMapping"):
        b.register(NS + cls)
    generated_key, mp, fields = options(nd)
    g = b.group("DefaultGroup", True, True)
    nfs, ins, outs, gcids = [], [], [], []
    multi = None
    for fname, t, prec, sc, occ in fields:
        nf = b.new("NormalizerField", name=fname, platformType=b.ptype(t), precision=prec, scale=sc, occurs=occ, level=1)
        nfs.append(nf)
        if occ > 1:
            multi = multi or nf
            for i in range(1, occ + 1):
                ins.append(b.new("NormalizerTxField", occurrence=i, referenceField=b.ref(nf),
                                 **_field_kw(b, "%s_%d" % (fname, i), t, prec, sc)))
        else:
            ins.append(b.new("NormalizerTxField", occurrence=1, referenceField=b.ref(nf), **_field_kw(b, fname, t, prec, sc)))
        outs.append(b.new("NormalizerTxField", occurrence=0, referenceField=b.ref(nf), **_field_kw(b, fname, t, prec, sc)))
        if occ > 1:
            gcids.append(b.new("NormalizerTxField", referenceField=b.ref(nf), **_field_kw(b, "GCID_" + fname, "INT32", 10, 0)))
    outs += gcids
    if generated_key and multi is not None:
        outs.append(b.new("NormalizerTxField", referenceField=b.ref(multi), **_field_kw(b, "GK_" + multi["name"], "INTEGER", 19, 0)))
    unknown = sorted(set(mp) - {x["name"] for x in ins})
    if unknown:
        raise SpecError("normalizer %r: map keys %s are not normalizer inputs (inputs: %s)" % (name, unknown, [x["name"] for x in ins]))
    mappings = [b.new("NormalizerFieldMapping", fromFieldName=mp.get(x["name"], x["name"]), toField=b.ref(x)) for x in ins]
    tx = b.new("TmplNormalizer", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal")]), groups=[g],
               fieldsMode="NOT_PARAMETERIZED",
               normalizerFields=b.new("NormalizerFields", fieldList=nfs),
               inputFields=ins, outputFields=outs,
               createGKField=values.imf_bool(generated_key),
               fieldMappingMode="MANUAL",
               manualMappings=b.new("NormalizerFieldMappings", mappingList=mappings))
    ctx.out(name, g); ctx.inp(name, g)
    return tx


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['fields', 'map', 'generatedKey'])


def _flow():
    from ..spec import SpecError
    try:
        from ..fieldflow import F, flow, fields
    except ImportError:
        return

    def _occurs(f):
        """occurs as the build reads it; 1 for a value the build refuses (lint_problems reports that)."""
        try:
            return values.as_whole(f.get("occurs"), "occurs", 1, 1)
        except SpecError:
            return 1

    @flow("normalizer", override=True)
    def _normalizer(nd, inputs):
        outs = [F(f["name"], f.get("type"), nd["name"]) for f in nd.get("fields") or []]
        outs += [F("GCID_" + f["name"], "INT32", nd["name"]) for f in nd.get("fields") or [] if _occurs(f) > 1]
        multi = [f for f in nd.get("fields") or [] if _occurs(f) > 1]
        gk = nd.get("generatedKey")
        if values.is_flag(gk) and values.as_flag(gk, "") and multi:     # as build reads it (build refuses other values)
            outs.append(F("GK_" + multi[0]["name"], "INTEGER", nd["name"]))
        return {"": fields(outs)}


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this normalizer's values (``options``: generatedKey, the map,
    the fields' names, prec / scale and occurs)."""
    return values.refusals(nd, lambda: options(nd))


_flow()

values.lint_hook("normalizer", lint_problems)      # lint reports what the build refuses (values.lint_hook)
