"""Rank: top/bottom N rows per group by one field; adds RANKINDEX.

top is a boolean (true / false, "true" / "false" in any case, 0 / 1; default true); by, n and groupBy are text (a
number becomes its text: the IMF holds n as "3"; true / false, a list or an object is a SpecError). ``options`` reads
them for the build and its lint hook (``lint_problems``) alike.
"""
from .. import values
from ..registry import node


def options(nd):
    """(top, by, n, groupBy) of a rank node, as the build reads them."""
    top, by = values.flag(nd, "top", True), values.text(nd, "by", what="a field name")
    return top, by, values.text(nd, "n", "1", what="a row count"), values.text_list(nd, "groupBy")


@node("rank", doc="by: rank field; top: true|false; n: rows per group; groupBy: [col, ...]. Adds RANKINDEX.")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    top, by, n, group_by = options(nd)
    g = b.group("DefaultGroup", True, True)
    tx = b.new("TmplRank", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal"), ("Case Sensitive String Comparison", "true"), ("Rank Data Cache Size", "Auto"),
                                         ("Rank Index Cache Size", "Auto")]),
               groups=[g], isTop=values.imf_bool(top), rankField=by, numOfRows=n,
               groupByFieldsList=b.new("TmplRankGroupByFields", fields=[b.new("TmplRankGroupByField", fieldName=k) for k in group_by]))
    ctx.out(name, g); ctx.inp(name, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this rank's values (``options``)."""
    return values.refusals(nd, lambda: options(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['by', 'top', 'n', 'groupBy'])

values.lint_hook("rank", lint_problems)      # lint reports what the build refuses (values.lint_hook)
