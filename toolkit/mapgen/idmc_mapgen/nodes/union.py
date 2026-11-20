"""Union: N input groups mapped onto one output field list (UNION ALL).

fields: [[name, TYPE, prec?, null, scale?], ...] (the field tuple of section 4 of docs/SPEC_REFERENCE.md; a union
field has no native type, so the 4th item must be null): prec 0 / null = the type's default precision, scale null =
the type's default scale; otherwise both are whole numbers (values.precision_scale), and the scale may not exceed the
precision (a NUMERIC with a precision below 9 needs its scale: ["amt", "NUMERIC", 5, null, 2]). Input group names,
field names and the map's incoming names are text (a number becomes its text; true / false, a list or an object is a
SpecError). ``options`` reads them all, for the build and its lint hook (``lint_problems``) alike.
"""
from .. import values
from ..registry import node

_HOW = "[name, TYPE, precision, null, scale]"


def _fields(nd, lint=False):
    """[(name, TYPE, precision, scale)] of a union's "fields" (``lint``: without the fields of an unknown TYPE, which
    lint's own TYPE_UNKNOWN / TYPE_JSON report)."""
    from ..spec import SpecError
    out = []
    for i, fd in enumerate(nd["fields"]):
        if lint and not values.lint_reads_type(fd):
            continue
        name = values.as_text(fd[0], values.where(nd, "fields[%d] name" % i), what="a field name")
        at = values.where(nd, "field %r" % name)
        if len(fd) > 3 and fd[3] is not None:
            raise SpecError("%s: a union field has no native type: the 4th item of %s must be null (fields are %s)"
                            % (at, values.brief(fd), _HOW))
        prec = fd[2] if len(fd) > 2 else None
        if isinstance(prec, int) and not isinstance(prec, bool) and prec == 0:
            prec = None                 # 0: the legacy spelling of "the type's default precision" (false, "" are not)
        prec, scale = values.precision_scale(fd[1], prec, fd[4] if len(fd) > 4 else None, at, _HOW)
        out.append((name, fd[1], prec, scale))
    return out


def options(nd, lint=False):
    """(inputs, fields, {group: {output field: incoming field}}) of a union node, as the build reads them."""
    inputs, fields = values.text_list(nd, "inputs", values.REQUIRED, item="input group name"), _fields(nd, lint)
    group_maps = nd.get("map") or {}
    if not isinstance(group_maps, dict):
        from ..spec import SpecError
        raise SpecError("%s must be an object {GROUP: {output_field: incoming_field}}, got %s"
                        % (values.where(nd, "map"), values.brief(group_maps)))
    return inputs, fields, {gn: values.as_text_map(group_maps.get(gn), values.where(nd, "map %r" % gn)) for gn in inputs}


@node("union", doc="inputs: [GROUP, ...] (link into 'UNI.GROUP'); fields: [[name, TYPE, prec?, null, scale?], ...]; "
                   "map: {GROUP: {output_field: incoming_field}} (default: same name).")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    inputs, fields, maps = options(nd)
    gin = {gn: b.group(gn, True, False) for gn in inputs}
    go = b.group("OutputGroup", False, True, rule=False)
    fl = []
    for fname, t, prec, sc in fields:
        fl.append(b.new("TxField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                        name=fname, platformType=b.ptype(t), precision=prec, scale=sc))
    ugs = []
    for gn in inputs:
        mp = maps[gn]
        fm = b.new("FieldMapping", fields=[b.new("TxFieldMapping", defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                                                  isDefaultValueUpdated="false", name=mp.get(f["name"], f["name"]), precision=0, scale=0,
                                                  txField=b.ref(f)) for f in fl])
        ugs.append(b.new("TmplUnionGroup", name=gn, fieldMapping=fm))
    tx = b.new("TmplUnion", augmented="false", createTime=ctx.now, name=name, advancedProperties=b.adv([("Tracing Level", "Normal")]),
               groups=list(gin.values()) + [go], fields=fl, inputGroups=ugs)
    ctx.out(name, go)
    for gn, g in gin.items():
        ctx.inp(name + "." + gn, g)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this union's values (``options``: input group names, the field
    tuples -- names, a 4th item that is not null, precision / scale -- and the map)."""
    return values.refusals(nd, lambda: options(nd, lint=True))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['inputs', 'fields', 'map'])

values.lint_hook("union", lint_problems)      # lint reports what the build refuses (values.lint_hook)
