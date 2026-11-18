"""Sorter: order rows by keys ("-col" = descending); distinct drops duplicate rows.

keys are field names (text); distinct is a boolean (true / false, "true" / "false" in any case, 0 / 1). ``options``
reads them for the build and its lint hook (``lint_problems``) alike.
"""
from .. import values
from ..registry import node


def options(nd):
    """(keys, distinct) of a sorter node, as the build reads them."""
    return values.text_list(nd, "keys", values.REQUIRED), values.flag(nd, "distinct")


@node("sorter", doc="keys: [col, \"-col\" (descending)]; distinct: bool.")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    keys, distinct = options(nd)
    g = b.group("DefaultGroup", True, True)
    tx = b.new("TmplSorter", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal"), ("Case Sensitive", "true"), ("Distinct", values.imf_bool(distinct))]),
               groups=[g], advancedSort="", sorterMode="SIMPLE",
               sortEntries=[b.new("SortEntry", ascending="false" if k.startswith("-") else "true", fieldName=k.lstrip("-")) for k in keys])
    ctx.out(name, g); ctx.inp(name, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this sorter's values (``options``)."""
    return values.refusals(nd, lambda: options(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['keys', 'distinct'])

values.lint_hook("sorter", lint_problems)      # lint reports what the build refuses (values.lint_hook)
