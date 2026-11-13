"""In-out parameters (mapping variables): values that a mapping reads as $$NAME and can update per run.

    "inOutParameters": [
      {"name": "p_min_qty", "type": "INTEGER", "default": "2"},
      {"name": "p_last_ts", "type": "STRING", "prec": 32, "default": "1970-01-01 00:00:00",
       "aggregation": "MAX", "retention": "ON_SUCCESS_OR_WARNING", "description": "high-water mark"}]

Use them as $$p_min_qty in filter conditions, expressions and source queries. Update them from an Expression
with SETVARIABLE($$p_last_ts, value) / SETMAXVARIABLE / SETMINVARIABLE / SETCOUNTVARIABLE; the value that IDMC
keeps after a run follows ``retention`` (ON_SUCCESS_OR_WARNING | ON_SUCCESS | ON_WARNING | NEVER) and
``aggregation`` (MAX | MIN | COUNT). The mapping task can override the starting value.
Stored in the IMF as Template.variables (SessionVariable objects).

name, type, default, description, retention and aggregation are text: a number becomes its text ("default": 2 is
"2"), null is the default ("" for default and description); true / false, a list or an object is a SpecError (the
default used to be written as "True" / "None"). prec / scale are whole numbers (null = the type's default; STRING:
100), and the scale may not exceed the precision (a NUMERIC with a precision below 9 needs its "scale").
``parameters(spec)`` reads them all, for the build and for lint (``lint_problems(spec)``) alike.
"""
from .. import values
from ..registry import template_hook

RETENTION = {"ON_SUCCESS_OR_WARNING", "ON_SUCCESS", "ON_WARNING", "NEVER"}
AGGREGATION = {"MAX", "MIN", "COUNT"}
SESSION_VARIABLE = "com.informatica.metadata.template.common.SessionVariable"


def parameters(spec):
    """The spec's in-out parameters as the build writes them: [{name, type, prec, scale, retention, aggregation,
    default, description}] (texts and whole numbers as described above); SpecError for a value the build refuses
    (a name, a duplicate, a retention / aggregation outside its set too)."""
    from ..spec import SpecError
    out, seen = [], set()
    for i, p in enumerate(spec.get("inOutParameters") or []):
        name = values.as_text(p.get("name"), "inOutParameters[%d] name" % i, "", what="a parameter name")
        if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
            raise SpecError("inOutParameters: invalid name %r (letters, digits, _; not starting with a digit; no $$)" % name)
        if name.lower() in seen:
            raise SpecError("inOutParameters: duplicate name %r" % name)
        seen.add(name.lower())
        at = "inOutParameters %r:" % name

        def txt(key, default, what):
            return values.as_text(p.get(key), "%s %s" % (at, key), default, what=what)
        t = txt("type", "STRING", "a field type")
        prec = p.get("prec")
        prec, sc = values.precision_scale(t, 100 if prec is None and t == "STRING" else prec, p.get("scale"), at[:-1], '"scale"',
                                          names=("prec", "scale"))
        ret, agg = txt("retention", "ON_SUCCESS_OR_WARNING", "a retention policy"), txt("aggregation", "MAX", "MAX, MIN or COUNT")
        if ret not in RETENTION:
            raise SpecError("inOutParameters %r: retention %r not in %s" % (name, ret, sorted(RETENTION)))
        if agg not in AGGREGATION:
            raise SpecError("inOutParameters %r: aggregation %r not in %s" % (name, agg, sorted(AGGREGATION)))
        out.append({"name": name, "type": t, "prec": prec, "scale": sc, "retention": ret, "aggregation": agg,
                    "default": txt("default", "", "a default value"), "description": txt("description", "", "a description")})
    return out


@template_hook
def apply_in_out_parameters(ctx, content):
    params = parameters(ctx.spec)
    if not params:
        return
    b = ctx.b
    short = b.register(SESSION_VARIABLE)
    content["variables"] = [b.new(short, aggregationType=p["aggregation"], expressionVariable="false", name=p["name"],
                                  platformType=b.ptype(p["type"]), precision=p["prec"], retentionPolicy=p["retention"],
                                  scale=p["scale"], defaultValue=p["default"], description=p["description"]) for p in params]


def lint_problems(spec):
    """[(lint code, message)]: what the build refuses in the spec's inOutParameters (``parameters``), in the build's
    words. Registered below as a spec-level lint check (node None)."""
    from ..spec import SpecError
    try:
        parameters(spec)
    except SpecError as e:
        return [("NODE_MALFORMED", p if isinstance(p, str) else str(p)) for p in e.problems]
    except Exception:       # noqa: BLE001 -- a shape the build reports as the hook's exception (inOutParameters not a list of objects)
        return []
    return []


# a spec-level check: on the nodes every mapping (source, target) and every mapplet (input, output) has, raised once
values.lint_hook(("source", "target", "input", "output"), lambda spec, nd, analysis, conns: lint_problems(spec), spec_level=True)
