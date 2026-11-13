"""Filter: keep the rows where cond is TRUE (pair it with a reject path, or prefer a router).

cond is text: a number becomes its text ("cond": 1 is "1"); true / false, a list or an object is a SpecError.
The lint hook ``lint_problems`` runs the same reader.
"""
from .. import values
from ..registry import node


def _cond(nd):
    return values.text(nd, "cond", what="a condition")


@node("filter", doc="Keep rows matching cond (an IDMC expression).")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    cond = _cond(nd)
    g = b.group("DefaultGroup", True, True)
    tx = b.new("TmplFilter", augmented="false", createTime=ctx.now, name=name, groups=[g], advancedFilterCondition=cond)
    ctx.out(name, g); ctx.inp(name, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this filter's cond (a value that is not text)."""
    return values.refusals(nd, lambda: _cond(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['cond'])

values.lint_hook("filter", lint_problems)      # lint reports what the build refuses (values.lint_hook)
