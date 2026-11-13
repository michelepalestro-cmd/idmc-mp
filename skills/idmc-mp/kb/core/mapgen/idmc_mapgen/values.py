"""Node option values: one coercion rule for every node builder (lint can apply the same rules).

Boolean options (``flag`` / ``as_flag``): true / false, the strings "true" / "false" in any case, and 0 / 1; null
or absent = the option's default. Anything else is a SpecError naming the node and the option. (Builders used to
test options for truthiness, so any non-empty string counted as true: "truncate": "false" truncated the table.)

Text slots (``text`` / ``as_text``: an expression, a condition, SQL, an object path, an attribute or property value,
a field or group name): a string is used as it is; a number becomes its text in JSON spelling (0 -> "0",
1.5 -> "1.5"), the way the IMF holds it; true / false, a list, an object or any other value is a SpecError naming
the node and the option. (A literal number used to go into the IMF as a JSON number, true as a JSON boolean.)
null = the option's default where it has one; a slot without a default refuses it.

Whole numbers (``as_whole``: a precision, a scale, a count, an offset): a JSON integer, at least the option's lower
bound; null = the option's default. A fraction or a whole float (5.0), a numeric string ("5"), true / false or a
number below the bound is a SpecError naming the node and the option. (An isinstance(int) test or int() let them
through: ["x", "NUMERIC", 5.0] was written as precision 5.0 with scale 9, "occurs": 2.5 as 2.)

Precision / scale (``precision_scale``, every field list of every builder): whole numbers, the precision >= 1 and the
scale >= 0; null = the type's default. A scale larger than the precision is a SpecError, also when the scale is the
type's default: a NUMERIC (or TIMESTAMP / DATE) field with a precision below 9 and no scale of its own would get the
default scale 9 (["amt", "NUMERIC", 5] was decimal(5,9)); give its scale. That is all the rule enforces: scale <=
precision. The generator does not guess a scale for the field (SQL reads NUMERIC(5) as scale 0, min(9, 5) would give
decimal(5,5)), and a precision of 9 or more without a scale keeps the type's default scale 9, as it always did: valid,
but it leaves precision - 9 integer digits (decimal(9,9) holds no value of 1 or more, decimal(12,9) none of 1000 or
more), so give the scale whenever the column holds larger values. nodes/masking.py applies the same rule to its
entries.

Lint (``refusals``, ``named``, ``lint_hook``): a node module's ``lint_problems(spec, nd, analysis, conns)`` hook runs
the build's own readers through ``refusals``, so it reports exactly the SpecErrors the build raises for those values,
in the build's words; ``lint_hook`` registers it with lint's per-node check registry (lint.check), so lint reports
them. lint.py's own rules read text slots and flags by the same rules (lint._text, lint._flag: "expr": 1000 is
"1000", "truncate": "false" is false). Where one of them still crashes on a value of the wrong kind (a field name that
is a number, "keys": [1]), lint reports that crash: also an ERROR, worded by lint.py.
"""
import json
import math

from .spec import SpecError
from .types import TYPES, typeinfo

REQUIRED = object()          # "no default": null is refused (as_text / text)
_TRUE, _FALSE = "true", "false"


def brief(v, n=60):
    """A value as it reads in the spec (JSON), shortened for messages."""
    try:
        s = json.dumps(v, ensure_ascii=False)
    except (TypeError, ValueError):
        s = repr(v)
    return s if len(s) <= n else s[:n - 3] + "..."


def where(nd, option):
    """'<type> <name>: <option>', the start of a message about one option of node ``nd``."""
    nd = nd if isinstance(nd, dict) else {}
    return "%s %r: %s" % (nd.get("type") or "node", nd.get("name"), option)


def _whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def named(nd, msg):
    """``msg`` worded as the build reports a problem of node ``nd`` (compile._named): "node '<name>' (<type>): <msg>",
    unless the message names the node already."""
    nd = nd if isinstance(nd, dict) else {}
    if repr(nd.get("name")) in msg:
        return msg
    return "node %r (%s): %s" % (nd.get("name"), nd.get("type"), msg)


def lint_hook(type_names, hook, spec_level=False):
    """Run ``hook(spec, nd, analysis, conns) -> [(code, message)]`` (a node module's ``lint_problems``) as lint's extra
    check of node types ``type_names`` (lint.check, its per-node check registry), so lint reports the build's own
    refusals. ``spec_level``: the issues are the spec's (node None), raised once (lint drops the same issue raised
    again from another node). Also registered in the copy of lint that ``python -m idmc_mapgen.lint`` runs as
    __main__ (as nodes/mapplet.py does). Silently skipped when lint cannot be imported: a build never needs it."""
    import sys
    try:
        from . import lint
    except Exception:           # noqa: BLE001 -- lint is optional here, as fieldflow is for the field rules
        return

    def check(ctx, nd):
        for code, msg in hook(ctx.spec, nd, ctx.an, ctx.conns) or []:
            ctx.issue(code, None if spec_level else nd.get("name"), msg)
    check.__qualname__ = "lint_hook(%s)" % getattr(hook, "__module__", "?")
    mods = [lint]
    main = sys.modules.get("__main__")
    if main is not None and main is not lint and getattr(getattr(main, "__spec__", None), "name", None) == lint.__name__:
        mods.append(main)
    for mod in mods:
        for t in ([type_names] if isinstance(type_names, str) else type_names):
            mod.check(t)(check)


def lint_reads_type(fd):
    """False for a field declaration (a tuple or a field object) whose TYPE is given but is not a known type: lint's
    own TYPE_UNKNOWN / TYPE_JSON report that field, so a hook skips it for the field lists lint.py checks itself
    (source, target, expression, aggregator, union fields: one ERROR per problem)."""
    t = fd[1] if isinstance(fd, (list, tuple)) and len(fd) > 1 else fd.get("type") if isinstance(fd, dict) else None
    return t is None or (isinstance(t, str) and t in TYPES)


def refusals(nd, *readers, code="NODE_MALFORMED"):
    """[(code, message)] for a node module's ``lint_problems`` hook: the SpecError problems that the build's own option
    readers raise for node ``nd`` (each reader is called in turn, so one bad option does not hide another), worded as
    the build words them (``named``). A reader's other exceptions (a missing key, a list where an object belongs) are
    not reported here: the build calls them "missing or unknown key" or names the exception, and lint's own rules
    report those shapes."""
    out = []
    for fn in readers:
        try:
            fn()
        except SpecError as e:
            out += [(code, named(nd, p if isinstance(p, str) else str(p))) for p in e.problems]
        except Exception:       # noqa: BLE001 -- a shape lint's own rules report (and the build refuses)
            pass
    return out


# ---------------------------------------------------------------------------------------------- whole numbers
def as_whole(v, where_, low=0, default=None, what=None):
    """A whole-number option's value (a precision, a scale, a count, an offset): a JSON integer >= ``low`` (None: no
    lower bound); None = ``default``. SpecError (``where_`` names the node and the option; ``what``: what null means,
    for the message) for a fraction or a whole float (5.0), a numeric string ("5"), true / false, a list... or a
    number below ``low``."""
    if v is None:
        return default
    if _whole(v) and (low is None or v >= low):
        return v
    raise SpecError("%s must be a whole number%s%s, got %s" % (where_, "" if low is None else " >= %d" % low,
                                                                " (null = %s)" % what if what else "", brief(v)))


# ---------------------------------------------------------------------------------------------- booleans
def is_flag(v):
    """True when ``v`` is a value a boolean option accepts (null included: the default)."""
    return (v is None or isinstance(v, bool) or (_whole(v) and v in (0, 1))
            or (isinstance(v, str) and v.lower() in (_TRUE, _FALSE)))


def as_flag(v, where_, default=False):
    """A boolean option's value: true / false, "true" / "false" (any case), 0 / 1; None = ``default``.
    SpecError (``where_`` names the node and the option) for anything else."""
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if _whole(v) and v in (0, 1):
        return v == 1
    if isinstance(v, str) and v.lower() in (_TRUE, _FALSE):
        return v.lower() == _TRUE
    raise SpecError("%s must be true or false (also \"true\" / \"false\" in any case, or 0 / 1), got %s" % (where_, brief(v)))


def flag(nd, key, default=False):
    """Boolean option ``key`` of node ``nd`` (absent or null = ``default``)."""
    return as_flag(nd.get(key), where(nd, key), default)


def imf_bool(v):
    """The IMF spelling of a boolean: "true" / "false"."""
    return _TRUE if v else _FALSE


# ---------------------------------------------------------------------------------------------- text
def as_text(v, where_, default=REQUIRED, what=None):
    """A text slot's value: a string as is; a whole or finite number as its JSON text (0 -> "0", 1.5 -> "1.5");
    None = ``default`` (REQUIRED: refused). SpecError (``where_`` names the node and the option; ``what`` says what
    the text is, e.g. "an expression") for true / false, a list, an object or any other value."""
    if isinstance(v, str):
        return v
    if v is None and default is not REQUIRED:
        return default
    if _whole(v):
        return str(v)
    if isinstance(v, float) and math.isfinite(v):
        return json.dumps(v)
    if isinstance(v, bool):
        kind = " (true / false are not text: write the text you mean as a string, e.g. \"TRUE\")"
    elif isinstance(v, (list, tuple)):
        kind = " (a list)"
    elif isinstance(v, dict):
        kind = " (an object)"
    else:
        kind = ""
    raise SpecError("%s must be text%s, got %s%s" % (where_, " (%s)" % what if what else "", brief(v), kind))


def text(nd, key, default=REQUIRED, what=None):
    """Text option ``key`` of node ``nd``: absent or null = ``default``; with no default an absent key is a KeyError
    (the build's "missing or unknown key") and null a SpecError."""
    if key not in nd and default is REQUIRED:
        raise KeyError(key)
    return as_text(nd.get(key), where(nd, key), default, what)


def text_list(nd, key, default=(), item="field name"):
    """Option ``key`` of node ``nd`` as a list of texts (absent or null = ``default``; REQUIRED: absent is a
    KeyError, the build's "missing or unknown key", and null is refused); SpecError for anything but a list, or for an
    item ``as_text`` refuses."""
    if default is REQUIRED and key not in nd:
        raise KeyError(key)
    v = nd.get(key)
    if v is None and default is not REQUIRED:
        return list(default)
    if not isinstance(v, (list, tuple)):
        raise SpecError("%s must be a list of %ss, got %s" % (where(nd, key), item, brief(v)))
    what = ("an " if item[:1] in "aeiou" else "a ") + item
    return [as_text(x, where(nd, "%s[%d]" % (key, i)), what=what) for i, x in enumerate(v)]


def text_pairs(nd, key, what="an attribute value"):
    """Option ``key`` of node ``nd`` as [(name, value)]: a list of [name, value] pairs or an object {name: value}
    (absent or null = none). Names and values are texts (``as_text``)."""
    v = nd.get(key)
    if v is None:
        return []
    items = list(v.items()) if isinstance(v, dict) else v
    if not isinstance(items, (list, tuple)):
        raise SpecError("%s must be [[name, value], ...] or {name: value}, got %s" % (where(nd, key), brief(v)))
    out = []
    for i, p in enumerate(items):
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            raise SpecError("%s must be [[name, value], ...] or {name: value}; item %d is %s"
                            % (where(nd, key), i, brief(p)))
        k = as_text(p[0], where(nd, "%s[%d] name" % (key, i)), what="a name")
        out.append((k, as_text(p[1], where(nd, "%s %r" % (key, k)), what=what)))
    return out


def as_text_map(v, where_, what="a field name"):
    """``v`` as {name: text} (null = {}); SpecError for anything but an object, or a value ``as_text`` refuses (keys
    are JSON strings already)."""
    if v is None:
        return {}
    if not isinstance(v, dict):
        raise SpecError("%s must be an object {name: %s}, got %s" % (where_, what, brief(v)))
    return {k: as_text(x, "%s %r" % (where_, k), what=what) for k, x in v.items()}


def text_map(nd, key, what="a field name"):
    """Option ``key`` of node ``nd`` as {name: text} (absent or null = {}): see as_text_map."""
    return as_text_map(nd.get(key), where(nd, key), what)


# ---------------------------------------------------------------------------------------------- fields
def field_type(t, where_):
    """typeinfo(t) with the field named in the error: (platform type, precision, scale, javaType)."""
    if not isinstance(t, str) or t not in TYPES:
        raise SpecError("%s: unknown field type %r (known: %s)" % (where_, t, ", ".join(TYPES)))
    return typeinfo(t)


def precision_scale(t, prec=None, scale=None, where_="field", how=None, names=("precision", "scale")):
    """(precision, scale) of a field of spec TYPE ``t``: ``prec`` / ``scale`` as given (None = the type's default),
    whole numbers (``as_whole``: the precision >= 1, the scale >= 0; ``names``: the options as the spec spells them,
    e.g. ("prec", "scale") for a field object). SpecError for any other value, and when the scale is larger than the
    precision; for a default scale (a NUMERIC precision below 9) the message says how to give one (``how``, e.g.
    '"scale"')."""
    _, dprec, dscale, _ = field_type(t, where_)
    p = as_whole(prec, "%s: %s" % (where_, names[0]), 1, dprec, "the type's default")
    s = as_whole(scale, "%s: %s" % (where_, names[1]), 0, dscale, "the type's default")
    if s > p:
        if scale is None:
            raise SpecError("%s: %s precision %d is below the default scale %d of %s, and a scale cannot be larger than the "
                            "precision: give the scale%s" % (where_, t, p, dscale, t, " (%s)" % how if how else ""))
        raise SpecError("%s: scale %d is larger than the precision %d" % (where_, s, p))
    return p, s
