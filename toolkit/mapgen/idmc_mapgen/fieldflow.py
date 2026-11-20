"""Field flow over a mapping spec: which fields leave every node, so lint can check every name before import.

One rule per node type:

    from idmc_mapgen.fieldflow import flow, F

    @flow("normalizer", ports=lambda nd: ([""], [""]))
    def _normalizer(nd, inputs):
        rows = inputs.get(nd["name"], [])
        return {"": list(rows) + [F("GCID_x", "INTEGER", nd["name"])]}

``inputs`` maps each input link key ("NAME", "NAME.Master", "NAME.Input1") to the fields arriving there,
after the link's field rule. The rule returns {output suffix: [Field]}; "" is the default output, router
groups use their group name. ``ports(nd)`` returns (input suffixes, output suffixes) and is what makes a link
endpoint valid ("" = the bare node name). A node type with no rule is "unchecked": its outputs are unknown, so
nothing downstream of it is reported as missing. A connected lookup uses the rule registered as
"lookup:connected" (a default one is below; register yours with override=True).
"""
from collections import OrderedDict, namedtuple, defaultdict


class Field(namedtuple("Field", "name type origin flags")):
    """A port: name, warehouse type (STRING, INTEGER, ... or None), the node that created it, flags."""
    __slots__ = ()

    def __new__(cls, name, type=None, origin=None, flags=()):
        return super().__new__(cls, name, type, origin, frozenset(flags))


F = Field


class Fields(list):
    """A list of Field. ``unchecked`` = something upstream had no rule, so the list may be incomplete."""
    unchecked = False

    def names(self):
        return [f.name for f in self]

    def find(self, name):
        """Exact match first, then case-insensitive (Informatica port names are case-insensitive)."""
        for f in self:
            if f.name == name:
                return f
        low = name.lower()
        for f in self:
            if f.name.lower() == low:
                return f
        return None


def fields(items=(), unchecked=False):
    out = Fields(items)
    out.unchecked = unchecked
    return out


FLOWS = {}   # type -> fn(nd, inputs) -> {suffix: [Field]}
PORTS = {}   # type -> fn(nd) -> ([input suffixes], [output suffixes])


def default_ports(nd):
    return [""], [""]


def flow(type_name, ports=None, override=False):
    """Register the field rule (and optionally the port shape) of a node type."""
    def deco(fn):
        if type_name in FLOWS and FLOWS[type_name] is not fn and not override:
            raise ValueError("flow rule registered twice: " + type_name)
        FLOWS[type_name] = fn
        PORTS[type_name] = ports or PORTS.get(type_name) or default_ports
        return fn
    return deco


def rule_key(nd):
    t = nd.get("type")
    if t == "lookup" and nd.get("connected"):
        from . import values      # "connected": "false" is false (as the build reads it); a refused value counts as true
        if not values.is_flag(nd.get("connected")) or values.as_flag(nd.get("connected"), ""):
            return "lookup:connected"
    return t


def ports_of(nd):
    """(input suffixes, output suffixes) or None when the type has no rule (any link key accepted)."""
    k = rule_key(nd)
    if k in PORTS:
        try:
            return PORTS[k](nd)
        except Exception:      # malformed node: lint reports the shape problem itself
            return None
    return None


# ----------------------------------------------------------------------------------------- helpers
def _decl(fd, origin, flags=()):
    """A field from a legacy tuple [name, TYPE, prec?, ...] or a dict {"name", "type"}."""
    if isinstance(fd, dict):
        return F(fd.get("name"), fd.get("type"), origin, flags)
    if isinstance(fd, (list, tuple)) and fd:
        return F(fd[0], fd[1] if len(fd) > 1 else None, origin, flags)
    return F(str(fd), None, origin, flags)


def _one(inputs, nd):
    """The single input of a one-group node (merged if several links feed it)."""
    got = inputs.get(nd["name"])
    if got is None:
        return fields()
    return got


def _add(base, extra):
    """base + extra; an extra field replaces a base field with the same name (case-insensitive)."""
    names = {f.name.lower() for f in extra}
    out = fields([f for f in base if f.name.lower() not in names] + list(extra), getattr(base, "unchecked", False))
    return out


def _passthrough(nd, inputs):
    return {"": _one(inputs, nd)}


# ----------------------------------------------------------------------------------------- rules
@flow("source", ports=lambda nd: ([], [""]))
def _source(nd, inputs):
    return {"": fields(_decl(fd, nd["name"]) for fd in nd.get("fields") or [])}


@flow("target", ports=lambda nd: ([""], []))
def _target(nd, inputs):
    return {}


@flow("expression")
def _expression(nd, inputs):
    outs = [F(f.get("name"), f.get("type"), nd["name"]) for f in nd.get("fields") or []
            if isinstance(f, dict) and str(f.get("kind", "OUTPUT")).upper() != "VARIABLE"]
    return {"": _add(_one(inputs, nd), outs)}


flow("filter")(_passthrough)
flow("sorter")(_passthrough)


def _router_ports(nd):
    return [""], [g[0] for g in nd.get("groups") or [] if g] + ["DEFAULT1"]


@flow("router", ports=_router_ports)
def _router(nd, inputs):
    inp = _one(inputs, nd)
    return {sfx: fields(inp, inp.unchecked) for sfx in _router_ports(nd)[1]}


@flow("joiner", ports=lambda nd: ([".Master", ".Detail"], [""]))
def _joiner(nd, inputs):
    m = inputs.get(nd["name"] + ".Master") or fields()
    d = inputs.get(nd["name"] + ".Detail") or fields()
    seen = {f.name.lower() for f in m}
    out = fields(list(m) + [f for f in d if f.name.lower() not in seen], m.unchecked or d.unchecked)
    return {"": out}


@flow("aggregator")
def _aggregator(nd, inputs):
    """Incoming fields pass through (CDI returns the last row's value for non-group-by fields)."""
    inp = _one(inputs, nd)
    gb = {g.lower() for g in nd.get("groupBy") or []}
    passed = fields([f if f.name.lower() in gb else f._replace(flags=f.flags | {"agg_pass:" + nd["name"]}) for f in inp],
                    inp.unchecked)
    aggs = [F(f.get("name"), f.get("type"), nd["name"]) for f in nd.get("fields") or [] if isinstance(f, dict)]
    return {"": _add(passed, aggs)}


@flow("rank")
def _rank(nd, inputs):
    return {"": _add(_one(inputs, nd), [F("RANKINDEX", "INTEGER", nd["name"])])}


@flow("sequence")
def _sequence(nd, inputs):
    return {"": _add(_one(inputs, nd), [F("NEXTVAL", "INTEGER", nd["name"]), F("CURRVAL", "INTEGER", nd["name"])])}


@flow("union", ports=lambda nd: (["." + g for g in nd.get("inputs") or []], [""]))
def _union(nd, inputs):
    return {"": fields(_decl(fd, nd["name"]) for fd in nd.get("fields") or [])}


@flow("lookup", ports=lambda nd: ([], []))
def _lookup_unconnected(nd, inputs):
    return {}


@flow("lookup:connected")
def _lookup_connected(nd, inputs):
    """Incoming fields + every declared lookup field: nodes/lookup_connected.py writes each one as a port. (A
    "returnFields" key used to narrow them here, which the builder never read: lint warns UNKNOWN_OPTION on it now.)"""
    decl = [_decl(fd, nd["name"]) for fd in nd.get("fields") or []]
    return {"": _add(_one(inputs, nd), decl)}


@flow("masking")
def _masking(nd, inputs):
    """Every incoming field leaves as out_<field> (masked if it has an entry); originals only with passthrough. A
    fallback: nodes/masking.py registers the exact rule (override=True: only the fields a passthrough list restores)."""
    from . import values      # "passthrough": "false" is false, as the build reads it
    pt = nd.get("passthrough")
    on = (values.as_flag(pt, "") if values.is_flag(pt) else bool(pt))
    inp = _one(inputs, nd)
    outs = [F("out_" + f.name, f.type, nd["name"]) for f in inp]
    base = inp if on else fields((), inp.unchecked)
    return {"": _add(base, outs)}


@flow("rulespec")
def _rulespec(nd, inputs):
    outs = [_decl(fd, nd["name"]) for fd in nd.get("outputs") or [["Output", "STRING", 50]]]
    return {"": _add(_one(inputs, nd), outs)}


@flow("cleanse")
def _cleanse(nd, inputs):
    outs = [F(_decl(fd, nd["name"]).name + "_" + nd["name"], "STRING", nd["name"]) for fd in nd.get("fields") or []]
    return {"": _add(_one(inputs, nd), outs)}


DEDUP_INPUTS = [("SequenceId", "INTEGER", "OPTIONAL"), ("GroupKey", "STRING", "MANDATORY"), ("Address_Part1", "STRING", "OPTIONAL"),
                ("Date", "TIMESTAMP", "OPTIONAL"), ("Person_Name", "STRING", "MANDATORY"), ("Address_Part2", "STRING", "OPTIONAL"),
                ("Postal_Area", "STRING", "OPTIONAL"), ("Telephone_Number", "STRING", "OPTIONAL"), ("Id", "STRING", "OPTIONAL"),
                ("Attribute1", "STRING", "OPTIONAL"), ("Attribute2", "STRING", "OPTIONAL"), ("Code", "STRING", "OPTIONAL"),
                ("Geocode", "STRING", "OPTIONAL")]
DEDUP_OUTPUTS = ([("Out_ClusterId", "STRING"), ("Out_ClusterSize", "INT32"), ("Out_RowId", "STRING"), ("Out_DriverId", "STRING"),
                  ("Out_DriverScore", "FLOAT"), ("Out_LinkId", "STRING"), ("Out_LinkScore", "FLOAT")] +
                 [("Out_" + n, "TIMESTAMP" if n == "Date" else "STRING") for n, _, _ in DEDUP_INPUTS[2:]] + [("Out_IsSurvivor", "STRING")])


@flow("dedup")
def _dedup(nd, inputs):
    return {"": _add(_one(inputs, nd), [F(n, t, nd["name"]) for n, t in DEDUP_OUTPUTS])}


def _generic_ports(nd):
    """A fallback: nodes/generic.py registers the generic rule with its own ports() (override=True), the link keys
    exactly as build registers them. This one is used only when that module cannot be imported, and then lint reports
    the broken compiler (EXTENSION_BROKEN) anyway."""
    groups = nd.get("groups") or []
    ins = list((nd.get("in") or {}).keys()) or ([""] if any(len(g) > 1 and g[1] for g in groups) else [])
    outs = list((nd.get("out") or {}).keys()) or ([""] if any(len(g) > 2 and g[2] for g in groups) else [])
    return ins, outs


@flow("generic", ports=_generic_ports)
def _generic(nd, inputs):
    """Declared fields only, and always unchecked: whether a class passes its inputs through is unknown."""
    decl = [_decl(fd, nd["name"]) for fd in nd.get("fields") or []]
    return {sfx: fields(decl, True) for sfx in _generic_ports(nd)[1]}


# ----------------------------------------------------------------------------------------- graph
Link = namedtuple("Link", "idx raw frm frm_node frm_suffix to to_node to_suffix rule")


def parse_link(idx, lk):
    """Same parsing as the compiler: "<node>[.<output group>]" -> "<node>[.<input group>]" [, rule]."""
    frm, to = str(lk[0]), str(lk[1])
    fn, _, fg = frm.partition(".")
    tn = to.split(".")[0]
    rule = lk[2] if len(lk) > 2 else None
    return Link(idx, lk, frm, fn, fg, to, tn, to[len(tn):], rule)


def is_exclude_rule(rule):
    """True for {"exclude": [names]} only. A rename map that merely contains a field called "exclude" is NOT one,
    even though the legacy generators read any dict holding that key as an exclude rule (lint flags it)."""
    return isinstance(rule, dict) and set(rule) == {"exclude"} and isinstance(rule["exclude"], (list, tuple))


def apply_rule(src, rule):
    """Fields after a link's field rule -> (Fields, [names the rule names that are not upstream])."""
    unchecked = getattr(src, "unchecked", False)
    if is_exclude_rule(rule):
        ex = rule.get("exclude") or []
        missing = [n for n in ex if src.find(n) is None]
        low = {n.lower() for n in ex}
        return fields([f for f in src if f.name.lower() not in low], unchecked), missing
    if rule:
        sel = rule if isinstance(rule, dict) else {k: "" for k in rule}
        out, missing = [], []
        for k, v in sel.items():
            f = src.find(k)
            if f is None:
                missing.append(k)
                continue
            out.append(f._replace(name=v) if v else f)
        return fields(out, unchecked), missing
    return fields(src, unchecked), []


class Analysis:
    """The spec as a graph, plus the fields arriving at (inputs) and leaving (outputs) every node."""

    def __init__(self, spec):
        self.spec = spec
        self.nodes = OrderedDict()
        self.dups = []
        for nd in spec.get("nodes") or []:
            if not isinstance(nd, dict) or "name" not in nd:
                continue
            if nd["name"] in self.nodes:
                self.dups.append(nd["name"])
                continue
            self.nodes[nd["name"]] = nd
        self.links = [parse_link(i, lk) for i, lk in enumerate(spec.get("links") or [])
                      if isinstance(lk, (list, tuple)) and len(lk) >= 2]
        self.bad_links = [i for i, lk in enumerate(spec.get("links") or [])
                          if not (isinstance(lk, (list, tuple)) and len(lk) >= 2)]
        self.in_links = defaultdict(list)
        self.out_links = defaultdict(list)
        for lk in self.links:
            self.out_links[lk.frm_node].append(lk)
            self.in_links[lk.to_node].append(lk)
        self.inputs = defaultdict(dict)     # node -> {link key: Fields}
        self.outputs = {}                   # node -> {suffix: Fields}
        self.rule_missing = []              # (link, [names])
        self.cycle_nodes = []
        self._run()

    def known_link(self, lk):
        """(from ok, from group ok, to ok, to group ok) for a link."""
        fnd, tnd = self.nodes.get(lk.frm_node), self.nodes.get(lk.to_node)
        fp = ports_of(fnd) if fnd else None
        tp = ports_of(tnd) if tnd else None
        fg_ok = fnd is not None and (fp is None or lk.frm_suffix in fp[1])
        tg_ok = tnd is not None and (tp is None or lk.to_suffix in tp[0])
        return fnd is not None, fg_ok, tnd is not None, tg_ok

    def order(self):
        """Kahn topological order over node names; nodes on a cycle are left out (see cycle_nodes)."""
        indeg = {n: 0 for n in self.nodes}
        succ = defaultdict(set)
        for lk in self.links:
            if lk.frm_node in self.nodes and lk.to_node in self.nodes and lk.to_node not in succ[lk.frm_node]:
                succ[lk.frm_node].add(lk.to_node)
                indeg[lk.to_node] += 1
        ready = [n for n in self.nodes if indeg[n] == 0]
        out = []
        while ready:
            n = ready.pop(0)
            out.append(n)
            for m in sorted(succ[n], key=list(self.nodes).index):
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
        self.cycle_nodes = [n for n in self.nodes if n not in out]
        return out

    def _run(self):
        for name in self.order():
            nd = self.nodes[name]
            for lk in self.in_links.get(name, []):
                src_out = self.outputs.get(lk.frm_node)
                if src_out is None or lk.frm_suffix not in src_out:
                    up = fields((), True)
                else:
                    up = src_out[lk.frm_suffix]
                got, missing = apply_rule(up, lk.rule)
                if missing and not up.unchecked:
                    self.rule_missing.append((lk, missing))
                key = lk.to
                if key in self.inputs[name]:     # several links into one group: union of fields
                    prev = self.inputs[name][key]
                    got = fields(list(prev) + [f for f in got if prev.find(f.name) is None], prev.unchecked or got.unchecked)
                self.inputs[name][key] = got
            fn = FLOWS.get(rule_key(nd))
            if fn is None:
                outs = {sfx: fields((), True) for sfx in (ports_of(nd) or ([], [""]))[1]} if ports_of(nd) else {}
                self.outputs[name] = defaultdict(lambda: fields((), True), outs)
                continue
            try:
                res = fn(nd, self.inputs[name]) or {}
            except Exception:    # malformed node: lint reports it; downstream is unchecked
                res = None
            if res is None:
                self.outputs[name] = defaultdict(lambda: fields((), True))
                continue
            any_unchecked = any(getattr(v, "unchecked", False) for v in self.inputs[name].values())
            outs = {}
            for sfx, fl in res.items():
                fl = fl if isinstance(fl, Fields) else fields(fl)
                if any_unchecked:
                    fl.unchecked = True
                outs[sfx] = fl
            self.outputs[name] = outs
        for name in self.cycle_nodes:
            self.outputs[name] = defaultdict(lambda: fields((), True))

    def incoming(self, name, key=None):
        """Fields arriving at node ``name`` (one input key, or every key merged)."""
        if key is not None:
            return self.inputs.get(name, {}).get(key, fields())
        got = self.inputs.get(name, {})
        if not got:
            return fields()
        if len(got) == 1:
            return next(iter(got.values()))
        out = fields((), any(v.unchecked for v in got.values()))
        for v in got.values():
            out.extend(f for f in v if out.find(f.name) is None)
        return out

    def ancestors(self, name, key=None):
        """Every node upstream of ``name`` (optionally only through input key ``key``)."""
        seen, todo = set(), [lk.frm_node for lk in self.in_links.get(name, []) if key is None or lk.to == key]
        while todo:
            n = todo.pop()
            if n in seen or n not in self.nodes:
                continue
            seen.add(n)
            todo.extend(lk.frm_node for lk in self.in_links.get(n, []))
        return seen


def analyze(spec):
    return Analysis(spec)
