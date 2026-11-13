"""Sequence Generator (TmplGenerator, mid-stream): adds NEXTVAL and CURRVAL.

reset is a boolean (true / false, "true" / "false" in any case, 0 / 1; default true); start and inc are written as
text (a number becomes its text; true / false, a list or an object is a SpecError). ``options`` reads them for build
and lint (``lint_problems``) alike.
"""
from .. import values
from ..registry import node


def options(nd):
    """(start, inc, reset) of a sequence node, as the build reads them."""
    start, inc = values.text(nd, "start", "1", what="a number"), values.text(nd, "inc", "1", what="a number")
    return start, inc, values.flag(nd, "reset", True)


@node("sequence", doc="start, inc, reset (default true). Adds NEXTVAL (+ CURRVAL). Observed: the start value is not honoured at run time (starts at 1).")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    start, inc, reset = options(nd)
    g = b.group("DefaultGroup", True, True)
    st_ = b.new("GeneratorState", startValue=start, incrementBy=inc, endValue="9223372036854775807",
                currentValue=start, cycle="false", numberOfCachedValues="0", reset=values.imf_bool(reset))
    tx = b.new("TmplGenerator", augmented="false", createTime=ctx.now, name=name, advancedProperties=b.adv([("Tracing Level", "Normal")]),
               groups=[g], midstream="true", state=st_)
    ctx.out(name, g); ctx.inp(name, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this sequence's values (``options``)."""
    return values.refusals(nd, lambda: options(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['start', 'inc', 'reset'])

values.lint_hook("sequence", lint_problems)      # lint reports what the build refuses (values.lint_hook)
