"""Expression: OUTPUT / VARIABLE ports computed per row; incoming fields pass through.

A port's name, kind and expr are text (a number becomes its text: "expr": 0 is "0"; true / false, a list or an object
is a SpecError); prec / scale are whole numbers (null = the type's default), and the scale may not exceed the precision
(a NUMERIC with a precision below 9 needs its "scale"). The lint hook ``lint_problems`` runs the same readers
(``port``, and the window's ``window_options``).
"""
from .. import values
from ..registry import node


def port(nd, f, i, kind_default="OUTPUT"):
    """(name, TYPE, precision, scale, kind, expr) of field object ``f`` (the i-th of node ``nd``'s "fields"), as the
    builders write them (``kind_default`` None: the kind is not read, None); SpecError naming the node and the field
    for a value they refuse."""
    name = values.as_text(f["name"], values.where(nd, "fields[%d] name" % i), what="a field name")
    at = values.where(nd, "field %r" % name)
    prec, sc = values.precision_scale(f["type"], f.get("prec"), f.get("scale"), at, '"scale"', names=("prec", "scale"))
    kind = None if kind_default is None else values.as_text(f.get("kind"), at + " kind", kind_default, what="OUTPUT or VARIABLE")
    return name, f["type"], prec, sc, kind, values.as_text(f["expr"], at + " expr", what="an expression")


def ports(nd, kind_default="OUTPUT", lint=False):
    """``port`` of every field object of node ``nd`` (what build and lint_problems read; ``lint``: without the fields
    of an unknown TYPE, which lint's own TYPE_UNKNOWN / TYPE_JSON report)."""
    return [port(nd, f, i, kind_default) for i, f in enumerate(nd["fields"]) if not lint or values.lint_reads_type(f)]


def expression_fields(b, fields, nd=None):
    nd = nd if nd is not None else {"type": "expression"}
    fl = []
    for i, f in enumerate(fields):
        name, t, prec, sc, kind, expr = port(nd, f, i)
        fl.append(b.new("TmplExpressionField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                        isDefaultValueUpdated="false", name=name, platformType=b.ptype(t),
                        precision=prec, scale=sc, expFieldType=kind,
                        expression=expr, macroOutputPrefix="", macroOutputSuffix="", selectedMacroInput="",
                        userPrompt="", variable="false"))
    return fl


@node("expression", doc="Computed ports. fields: [{name, type, expr, kind: OUTPUT|VARIABLE, prec?, scale?}]; window: {...} (window functions).")
def build(ctx, nd):
    if nd.get("window"):
        try:
            from .expression_window import build_window
        except ImportError as e:
            from ..spec import SpecError
            raise SpecError("expression %r uses \"window\", which needs idmc_mapgen/nodes/expression_window.py (%s)" % (nd["name"], e)) from None
        return build_window(ctx, nd)
    b = ctx.b; name = nd["name"]
    g = b.group("DefaultGroup", True, True)
    fl = expression_fields(b, nd["fields"], nd)
    tx = b.new("TmplExpression", augmented="false", createTime=ctx.now, name=name,
               advancedProperties=b.adv([("Tracing Level", "Normal")]), groups=[g], additionalFields="",
               windowConfigurationEnabled="false", fields=fl,
               windowSpec=b.new("TmplExpressionWindowSpec", allRowsFollowing="false", allRowsPreceding="false",
                                endOffset=0, startOffset=0, partitionKeys=[]))
    ctx.out(name, g); ctx.inp(name, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this expression's values -- a port's name / kind / expr that is
    not text, a prec / scale that is not a whole number or a scale above the precision, and with "window" the
    window's options (expression_window.window_options, which also refuses window functions unless allowUnsupported)."""
    readers = [lambda: ports(nd, lint=True)]
    if nd.get("window"):
        try:
            from .expression_window import window_options
        except ImportError:          # build refuses every window expression then; lint reports the broken extension
            window_options = None
        if window_options is not None:
            readers.insert(0, lambda: window_options(nd))
    return values.refusals(nd, *readers)


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['fields', 'window'])

values.lint_hook("expression", lint_problems)      # lint reports what the build refuses (values.lint_hook)
