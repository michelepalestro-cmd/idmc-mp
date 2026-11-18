"""Aggregator: group-by fields plus aggregate OUTPUT ports.

Names, groupBy fields and expr are text (a number becomes its text; true / false, a list or an object is a SpecError);
prec / scale as an expression port's (nodes/expression.py ``port``). The lint hook ``lint_problems`` runs the same
readers.
"""
from .. import values
from ..registry import node
from .expression import ports


def _group_by(nd):
    return values.text_list(nd, "groupBy", values.REQUIRED)


@node("aggregator", doc="groupBy: [col, ...]; fields: [{name, type, expr (e.g. SUM(x), COUNT(x), MAX(x, cond))}].")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    g = b.group("DefaultGroup", True, True)
    fl = []
    for fname, t, prec, sc, _, expr in ports(nd, kind_default=None):
        fl.append(b.new("TmplAggregatorField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                        isDefaultValueUpdated="false", name=fname, platformType=b.ptype(t),
                        precision=prec, scale=sc, expFieldType="OUTPUT", expression=expr,
                        macroOutputPrefix="", macroOutputSuffix="", selectedMacroInput="", userPrompt=""))
    group_by = _group_by(nd)
    tx = b.new("TmplAggregator", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal"), ("Sorted Input", "false")]),
               groups=[g], additionalFields="", inputSorted="false", fields=fl,
               groupByFieldsList=b.new("TmplAggregatorGroupByFields",
                                       fields=[b.new("TmplAggregatorGroupByField", fieldName=k) for k in group_by]))
    ctx.out(name, g); ctx.inp(name, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this aggregator's values (its fields as ``port`` reads them,
    groupBy as a list of field names)."""
    return values.refusals(nd, lambda: ports(nd, kind_default=None, lint=True), lambda: _group_by(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['groupBy', 'fields'])

values.lint_hook("aggregator", lint_problems)      # lint reports what the build refuses (values.lint_hook)
