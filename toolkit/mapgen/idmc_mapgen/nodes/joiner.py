"""Joiner: Master and Detail input groups, equality conditions, normal/outer join types.

cond operands and join are text (a number becomes its text; true / false, a list or an object is a SpecError);
sorted is a boolean (true / false, "true" / "false" in any case, 0 / 1). ``options`` reads them for the build and its lint
hook (``lint_problems``) alike.
"""
from .. import values
from ..registry import node
from ..spec import SpecError

JOIN_TYPES = {"NORMAL": "Normal Join", "MASTER_OUTER": "Master Outer Join", "DETAIL_OUTER": "Detail Outer Join", "FULL_OUTER": "Full Outer Join"}


def _cond(nd):
    """[(master field, detail field)] of a joiner's "cond" [[master_col, detail_col], ...], as text."""
    out = []
    for i, (l, r) in enumerate(nd["cond"]):
        out.append(tuple(values.as_text(x, values.where(nd, "cond[%d] %s field" % (i, side)), what="a field name")
                         for x, side in ((l, "master"), (r, "detail"))))
    return out


def options(nd):
    """(join, sorted, cond) of a joiner node, as the build reads them (the join type's validity is the build's next
    check, and lint's JNR_TYPE)."""
    return values.text(nd, "join", "NORMAL", what="a join type"), values.flag(nd, "sorted"), _cond(nd)


@node("joiner", doc="Link into \"JNR.Master\" / \"JNR.Detail\". cond: [[master_col, detail_col], ...]; "
                    "join: NORMAL|MASTER_OUTER|DETAIL_OUTER|FULL_OUTER; sorted: true for same-pipeline branches.")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    gm = b.group("Master", True, False); gd = b.group("Detail", True, False); go = b.group("OutputGroup", False, True, rule=False)
    join, sorted_input, cond = options(nd)
    if join not in JOIN_TYPES:
        raise SpecError("joiner %r: join %r is not one of %s" % (name, join, ", ".join(JOIN_TYPES)))
    tx = b.new("TmplJoiner", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal"), ("Joiner Data Cache Size", "AUTO"), ("Master Sort Order", "AUTO")] +
                                        ([("Sorted Input", "true")] if sorted_input else [])),
               groups=[gm, gd, go], advancedJoinCondition="", joinType=JOIN_TYPES[join],
               joinConditions=[b.new("JoinCondition", leftOperand=l, operator="=", rightOperand=r) for l, r in cond])
    ctx.out(name, go); ctx.inp(name + ".Master", gm); ctx.inp(name + ".Detail", gd)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this joiner's values (``options``)."""
    return values.refusals(nd, lambda: options(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['master', 'detail', 'cond', 'join', 'sorted'])

values.lint_hook("joiner", lint_problems)      # lint reports what the build refuses (values.lint_hook)
