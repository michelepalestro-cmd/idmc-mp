"""Rule Specification: a Data Quality asset that already exists in the org (list it in the spec's "assets").

asset, field names and the map's incoming names are text (a number becomes its text; true / false, a list or an
object is a SpecError); a precision is a whole number >= 1 (null = the type's default; the scale is 0). ``options``
reads them for the build and its lint hook (``lint_problems``) alike.
"""
from .. import values
from ..registry import node


def defs(nd, key, default=None):
    """[(name, TYPE, precision, scale)] of a DQ node's field list ``key`` ([[name, TYPE, prec?, scale?], ...]; ``default``:
    the list when the key is absent, None = required). The scale defaults to 0; give it when the rule specification's
    field has one (a decimal 18,4 input), or the Mapping Designer marks the mapping Invalid."""
    out = []
    for i, fd in enumerate(nd[key] if default is None else nd.get(key, default)):
        fname = values.as_text(fd[0], values.where(nd, "%s[%d] name" % (key, i)), what="a field name")
        at = values.where(nd, "%s %r" % (key, fname))
        prec = values.field_type(fd[1], at)[1]
        out.append((fname, fd[1], values.as_whole(fd[2] if len(fd) > 2 else None, at + " precision", 1, prec, "the type's default"),
                    values.as_whole(fd[3] if len(fd) > 3 else None, at + " scale", 0, 0, "0")))
    return out


def options(nd):
    """(asset, map, inputs, outputs) of a rulespec node, as the build reads them."""
    asset, mp = values.text(nd, "asset", what="an asset id"), values.text_map(nd, "map")
    return asset, mp, defs(nd, "inputs"), defs(nd, "outputs", [["Output", "STRING", 50]])


@node("rulespec", doc="asset: <frs id>; inputs: [[name, TYPE, prec?, scale?]]; map: {rule_input: incoming_field}; outputs: [[name, TYPE, prec?]].")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    asset, mp, ins, outs = options(nd)
    gi = b.group("Input group:", True, False); go = b.group("MappletOutputTx_Output", False, True, rule=False)

    def rsf(fields):
        return [b.new("TxField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                      name=fname, platformType=b.ptype(t), precision=prec, scale=sc) for fname, t, prec, sc in fields]
    fin = rsf(ins); fout = rsf(outs)
    fm = b.new("FieldMapping", fields=[b.new("TxFieldMapping", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                                              name=mp.get(f["name"], f["name"]), precision=0, scale=0, txField=b.ref(f)) for f in fin])
    tx = b.new("TmplRuleSpecification", augmented="false", createTime=ctx.now, name=name, advancedProperties=b.adv([("version", "R37")]),
               groups=[gi, go], documentId="@" + asset, ruleId="@" + asset,
               inputGroups=[b.new("TmplRuleSpecificationGroup", name="Input group:", fieldMappingMode="MANUAL", fieldMapping=fm)],
               inputFields=b.new("RuleSpecificationFields", fieldList=fin), outputFields=b.new("RuleSpecificationFields", fieldList=fout))
    ctx.out(name, go); ctx.inp(name, gi)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this rulespec's values (``options``)."""
    return values.refusals(nd, lambda: options(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['asset', 'inputs', 'map', 'outputs'])

values.lint_hook("rulespec", lint_problems)      # lint reports what the build refuses (values.lint_hook)
