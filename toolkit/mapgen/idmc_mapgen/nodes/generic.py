"""Generic node: build any IMF transformation class from raw properties (for probing classes nobody has wrapped yet).

    {"type": "generic", "name": "X", "cls": "<fully qualified class>",
     "groups": [[name, is_input, is_output], ...],          # TmplGroups ("rules" = all-fields rule on input groups)
     "groupCls": {group: "<FQ class>"},                     # re-class a group (e.g. a union input group)
     "groupProps": {"inputGroups": [group, ...]},           # put these groups in that property instead of "groups"
     "keepInGroups": false,                                 # ...or in both
     "props": {prop: value},                                # plain properties (they win over the defaults below)
     "objs": {prop: [["<FQ class>", {props}], ...]},        # nested objects (a list; "objlist": {prop: false} = single)
     "fields": [{name, type, prec?, scale?, extra: {...}}], "fieldCls": "<FQ class>", "fieldsProp": "fields",
     "adv": [[name, value], ...],                           # advanced properties (default Tracing Level = Normal)
     "in": {".Group": group},                               # link keys "<NAME>.Group" -> group ("" = "<NAME>")
     "out": {"Group": group}}                               # link sources "<NAME>.Group" ("" = "<NAME>")

Defaults: without "in", the first input group is the link target "<NAME>"; without "out", the first output group
is the link source "<NAME>". A node with no input group (a source) or no output group (a sink) simply has none,
and "in": {} / "out": {} mean none. Link keys may be written with or without the leading dot; two keys that are the
same link key ("In" and ".In") are refused. Group names must be unique and the flags true/false. ``ports(nd)`` gives
the link keys exactly as build registers them; lint's field-flow rule for generic nodes uses it (``_flow``), so lint
and build accept the same links. Every link group must stay in the transformation, so props/objs/fields that
replace "groups" while it holds a link group are refused (the links would point at groups that are not there).
Classes are fully qualified Java names; a short name is accepted only when this build already knows it (types.CLS,
or a class an earlier node registered). Each class keeps its own $$classInfo entry, so a probe class never
re-points a core class that has the same simple name (tmpltarget.FieldMapping next to common.field.FieldMapping).
"keepInGroups" and the "objlist" values are booleans (true / false, "true" / "false" in any case, 0 / 1; the group
flags stay JSON booleans); "adv" names and values and field names are text (a number becomes its text); a field's
prec / scale are whole numbers (null = the type's default), and the scale may not exceed the precision. "props" /
"objs" / field "extra" are raw IMF properties, written as given. (lint runs this builder itself: _build_refusals.)
"""
from .. import values
from ..imf import FQ_CLASS
from ..registry import node
from ..spec import SpecError

ADV_DEFAULT = [("Tracing Level", "Normal")]

TX_FIELD = "com.informatica.metadata.template.common.field.TxField"
RESERVED = ("$$ID", "$$class", "name")   # props/objs/fields cannot replace these


def _first(groups, col):
    return next((g[0] for g in groups if len(g) > col and g[col]), None)


def _groups(nd):
    """The node's "groups" as [(name, is_input, is_output)]: non-empty unique names, true/false flags."""
    name, groups = nd.get("name"), nd.get("groups")
    if not isinstance(groups, (list, tuple)):
        raise SpecError("generic %r: 'groups' must be a list of [name, is_input, is_output], got %r" % (name, groups))
    out, seen = [], set()
    for i, g in enumerate(groups):
        if not (isinstance(g, (list, tuple)) and len(g) == 3 and isinstance(g[0], str) and g[0]):
            raise SpecError("generic %r: groups[%d] must be [name, is_input, is_output] with a non-empty name, got %r"
                            % (name, i, g))
        if not (isinstance(g[1], bool) and isinstance(g[2], bool)):
            raise SpecError("generic %r: groups[%d] %r: is_input and is_output must be true or false (JSON booleans; a "
                            "string such as \"false\" would count as true), got %r and %r" % (name, i, g[0], g[1], g[2]))
        if g[0] in seen:
            raise SpecError("generic %r: group %r is listed twice in 'groups'" % (name, g[0]))
        seen.add(g[0])
        out.append(tuple(g))
    return out


def _link_keys(nd, key, norm, link):
    """nd[key] ("in" / "out") with its keys in link-suffix form; two keys that are the same link key are refused."""
    name, v = nd.get("name"), nd[key]
    if not isinstance(v, dict):
        raise SpecError("generic %r: %r must be an object {link key: group name}, got %r" % (name, key, v))
    out, first = {}, {}
    for k, g in v.items():
        if not isinstance(k, str):
            raise SpecError("generic %r: %r key %r must be a string" % (name, key, k))
        s = norm(k)
        if s in first:
            raise SpecError("generic %r: %r keys %r and %r are the same link key %r; keep one"
                            % (name, key, first[s], k, link(str(name), s)))
        first[s] = k
        out[s] = g
    return out


def ports(nd):
    """({input suffix: group}, {output suffix: group}) of a generic node, as build registers them. Suffixes follow the
    link syntax: link "NAME.G" -> input suffix ".G" and output suffix "G"; "" = the bare "NAME"."""
    groups = nd.get("groups") or []
    if nd.get("in") is None:
        ins = {"": _first(groups, 1)} if _first(groups, 1) is not None else {}
    else:
        ins = _link_keys(nd, "in", lambda k: k if not k or k.startswith(".") else "." + k, lambda n, s: n + s)
    if nd.get("out") is None:
        outs = {"": _first(groups, 2)} if _first(groups, 2) is not None else {}
    else:
        outs = _link_keys(nd, "out", lambda k: k[1:] if k.startswith(".") else k, lambda n, s: n + "." + s if s else n)
    return ins, outs


@node("generic", doc="Any IMF class from raw props (probing). See module docstring.")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]

    def cls_key(what, k):
        """A class key for b.new()/b.c(): a fully qualified name, or a short name this build already knows."""
        if isinstance(k, str) and "." not in k and k in b.fq:
            return k
        if not isinstance(k, str) or not FQ_CLASS.match(k):
            raise SpecError("generic %r: %s %r must be a fully qualified IMF class name (e.g. %s)"
                            % (name, what, k, b.fq["TmplFilter"]))
        return k

    def group(what, g):
        if g not in gs:
            raise SpecError("generic %r: %s names group %r, which is not one of its groups (%s)"
                            % (name, what, g, ", ".join(gs) or "none"))
        return gs[g]

    short = cls_key("cls", nd["cls"])
    objlist = nd.get("objlist") or {}
    if not isinstance(objlist, dict):
        raise SpecError("%s must be an object {prop: true | false}, got %s" % (values.where(nd, "objlist"), values.brief(objlist)))
    single = {k: not values.as_flag(objlist.get(k), values.where(nd, "objlist %r" % k), True) for k in objlist}
    keep, adv = values.flag(nd, "keepInGroups"), (values.text_pairs(nd, "adv") if nd.get("adv") is not None else ADV_DEFAULT)
    gs = {gn: b.group(gn, i, o, rule=bool(i)) for gn, i, o in _groups(nd)}
    for gn, gcls in nd.get("groupCls", {}).items():
        group("groupCls", gn)["$$class"] = b.c(cls_key("groupCls[%r]" % gn, gcls))
    kw = dict(nd.get("props", {}))
    for k, spec_ in nd.get("objs", {}).items():
        out_ = []
        for cfq, pr in spec_:
            out_.append(b.new(cls_key("objs[%r]" % k, cfq), **pr))
        kw[k] = out_[0] if single.get(k) else out_
    if nd.get("fields"):
        fl = []
        fshort = cls_key("fieldCls", nd.get("fieldCls", TX_FIELD))
        for i, f in enumerate(nd["fields"]):
            fname = values.as_text(f["name"], values.where(nd, "fields[%d] name" % i), what="a field name")
            prec, sc = values.precision_scale(f["type"], f.get("prec"), f.get("scale"), values.where(nd, "field %r" % fname), '"scale"',
                                              names=("prec", "scale"))
            d = dict(defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                     name=fname, platformType=b.ptype(f["type"]), precision=prec, scale=sc)
            d.update(f.get("extra", {})); fl.append(b.new(fshort, **d))
        kw[nd.get("fieldsProp", "fields")] = fl
    sep = nd.get("groupProps", {})
    moved = {g for v in sep.values() for g in v}
    for k, v in sep.items():
        kw[k] = [group("groupProps[%r]" % k, g) for g in v]
    bad = [k for k in RESERVED if k in kw]
    if bad:
        raise SpecError("generic %r: props/objs/fields cannot set %s (the builder owns the object id and class, and "
                        "the transformation name is the node name)" % (name, ", ".join(bad)))
    props = dict(augmented="false", createTime=ctx.now, name=name,
                 advancedProperties=b.adv(adv),
                 groups=[g for n_, g in gs.items() if n_ not in moved or keep])
    props.update(kw)
    tx = b.new(short, **props)
    held = {id(o) for v in tx.values() for o in (v if isinstance(v, list) else [v]) if isinstance(o, dict)}

    def port(what, k, v):
        """A link group; it must still be in the transformation, or every link to it would dangle."""
        g = group("%s[%r]" % (what, k), v)
        if id(g) not in held:
            raise SpecError("generic %r: %s[%r] is group %r, which is no longer in the transformation: props/objs/fields "
                            "replaced the property that held it (set the groups with \"groups\" / \"groupProps\")"
                            % (name, what, k, v))
        return g

    ins, outs = ports(nd)
    for k, v in outs.items():
        ctx.out(name, port("out", k, v), k)
    for k, v in ins.items():
        ctx.inp(name + k, port("in", k, v))
    return tx


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['cls', 'groups', 'groupCls', 'groupProps', 'keepInGroups', 'props', 'objs', 'objlist', 'fields', 'fieldCls', 'fieldsProp', 'adv', 'in', 'out'])


def _flow():
    """lint's field-flow rule for generic nodes, with the link keys exactly as build registers them (``ports``)."""
    try:
        from ..fieldflow import _decl, fields, flow
    except ImportError:
        return

    def _ports(nd):
        ins, outs = ports(nd)
        return list(ins), list(outs)

    @flow("generic", ports=_ports, override=True)
    def _generic(nd, inputs):
        """Declared fields only, and always unchecked: whether a class passes its inputs through is unknown."""
        decl = [_decl(fd, nd["name"]) for fd in nd.get("fields") or []]
        return {sfx: fields(decl, True) for sfx in ports(nd)[1]}


_flow()
