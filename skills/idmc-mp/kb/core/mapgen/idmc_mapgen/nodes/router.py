"""Router: one input group, one output group per condition plus DEFAULT1 (rows that match no condition).

Group names and conditions are text: a number becomes its text; true / false, a list or an object is a SpecError.
The lint hook ``lint_problems`` runs the same reader.
"""
from .. import values
from ..registry import node


def _groups(nd):
    """[(group name, condition)] of a router's "groups" [[GROUP_NAME, condition], ...], as text."""
    out = []
    for i, (gn, c) in enumerate(nd["groups"]):
        gn = values.as_text(gn, values.where(nd, "groups[%d] name" % i), what="a group name")
        out.append((gn, values.as_text(c, values.where(nd, "groups[%d] %r condition" % (i, gn)), what="a condition")))
    return out


@node("router", doc="groups: [[GROUP_NAME, condition], ...]; link from \"RTR.GROUP_NAME\" or \"RTR.DEFAULT1\".")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    groups = _groups(nd)
    gi = b.group("INPUT", True, False)
    gs = {gn: b.group(gn, False, True, rule=False) for gn, _ in groups}
    gd = b.group("DEFAULT1", False, True, rule=False)
    tx = b.new("TmplRouter", augmented="false", createTime=ctx.now, name=name, groups=[gi, gd] + list(gs.values()),
               groupFilterConditions=[b.new("GroupFilterCondition", advancedFilterCondition=c, name=gn) for gn, c in groups])
    for gn, g in gs.items():
        ctx.out(name, g, gn)
    ctx.out(name, gd, "DEFAULT1")
    ctx.inp(name, gi)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this router's group names and conditions (values that are
    not text; the groups' shape is lint's RTR_GROUPS)."""
    return values.refusals(nd, lambda: _groups(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['groups'])

values.lint_hook("router", lint_problems)      # lint reports what the build refuses (values.lint_hook)
