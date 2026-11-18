"""Cleanse: a Data Quality cleanse asset that already exists in the org (list it in the spec's "assets").

asset and field names are text (a number becomes its text; true / false, a list or an object is a SpecError); a
precision is a whole number >= 1 (null = the type's default; the scale is 0). ``options`` reads them for build and
lint (``lint_problems``) alike.
"""
from .. import values
from ..registry import node


def options(nd):
    """(asset, [(name, TYPE, precision)]) of a cleanse node, as the build reads them."""
    asset = values.text(nd, "asset", what="an asset id")
    defs = []
    for i, fd in enumerate(nd["fields"]):
        fname = values.as_text(fd[0], values.where(nd, "fields[%d] name" % i), what="a field name")
        at = values.where(nd, "field %r" % fname)
        prec = values.field_type(fd[1], at)[1]
        defs.append((fname, fd[1], values.as_whole(fd[2] if len(fd) > 2 else None, at + " precision", 1, prec, "the type's default")))
    return asset, defs


@node("cleanse", doc="asset: <frs id>; fields: [[name, TYPE, prec?]] -> outputs <field>_<NODE NAME> (inputs mapped BY_NAME).")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    asset, defs = options(nd)
    gi = b.group("Input group:", True, False); go = b.group("MappletOutputTx_Output", False, True, rule=False)

    def dqf(suffix=""):
        return [b.new("TxField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                      name=fname + suffix, platformType=b.ptype(t), precision=prec, scale=0) for fname, t, prec in defs]
    tx = b.new("TmplCleanse", augmented="false", createTime=ctx.now, name=name, advancedProperties=b.adv([("version", "R37")]), groups=[gi, go],
               assetDocumentId="", assetId="@" + asset,
               inputGroups=[b.new("TmplDQGroup", name="Input group:", fieldMappingMode="BY_NAME")],
               inputFields=b.new("DQFields", fieldList=dqf()), outputFields=b.new("DQFields", fieldList=dqf("_" + name)))
    ctx.out(name, go); ctx.inp(name, gi)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this cleanse's values (``options``)."""
    return values.refusals(nd, lambda: options(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['asset', 'fields'])

values.lint_hook("cleanse", lint_problems)      # lint reports what the build refuses (values.lint_hook)
