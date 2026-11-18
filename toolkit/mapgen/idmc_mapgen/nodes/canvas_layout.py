"""Canvas layout: where each transformation sits on the Mapping Designer canvas, so that no two boxes overlap.

The designer keeps the positions in one Template annotation, ``LayoutAnnotation``, whose ``jsonBlob`` is
``{"<transformation name>": {"x": 100, "y": 120}, ...}`` (pixels at 100 % zoom, origin top left; read from a mapping
saved in the designer). A mapping imported without it opens with every transformation of a column stacked on one
spot: the boxes overlap and the links hide behind them.

Opt-in per spec (absent = the IMF is unchanged, byte for byte):

    "layout": "auto"
    "layout": {"auto": true, "dx": 200, "dy": 100, "x0": 40, "y0": 40, "targets": "next", "sources": "first",
               "pin": {"TGT_A": [900, 40]}}
    "layout": {"SRC_A": [40, 40], "EXP_A": [240, 40], ...}            # every position given (no "auto")

auto: a left-to-right layered layout. Each transformation's column = the longest chain of links before it (sources in
column 0); with ``"targets": "last"`` every target sits in the last column, so the data lands in one column
on the right; ``"targets": "next"`` puts each target just right of what feeds it, so no link has to run behind
another box. ``"sources": "late"`` puts each source just left of its first consumer. Rows: a column's boxes are stacked ``dy`` apart in the order of their neighbours' rows (barycentre,
forward/backward sweeps ending forward, snapped to half rows), so straight chains stay on one line and a router's branches fan out below it. ``pin`` fixes boxes;
transformations with no link (an unconnected lookup) go on a row under the flow. A box is about 140 x 60 px: keep
``dx`` >= 180 and ``dy`` >= 80. A transformation the spec does not name (a builder's helper) is placed after the
last column.
"""
import json

from ..registry import template_hook

LAYOUT_ANNOTATION = "com.informatica.metadata.template.common.layout.LayoutAnnotation"
DEFAULTS = {"dx": 200, "dy": 100, "x0": 40, "y0": 40, "targets": "next", "sources": "first"}
BOX_W, BOX_H = 140, 60


def _opts(spec):
    lay = spec.get("layout")
    if lay in (None, False, "", {}):
        return None
    from ..spec import SpecError
    if lay is True or lay == "auto":
        return dict(DEFAULTS, auto=True, pin={})
    if not isinstance(lay, dict):
        raise SpecError("'layout' must be \"auto\", an object of options or an object of positions, got %r" % (lay,))
    keys = set(DEFAULTS) | {"auto", "pin"}
    if lay.get("auto") or set(lay) <= keys:
        o = dict(DEFAULTS, auto=True, pin={})
        for k, v in lay.items():
            if k not in keys:
                raise SpecError("layout: unknown option %r (options: %s)" % (k, ", ".join(sorted(keys))))
            o[k] = v
        for k in ("dx", "dy", "x0", "y0"):
            if not isinstance(o[k], int) or isinstance(o[k], bool) or o[k] < 0:
                raise SpecError("layout: %s must be a whole number of pixels, got %r" % (k, o[k]))
        if o["targets"] not in ("last", "next"):
            raise SpecError("layout: targets must be \"last\" or \"next\", got %r" % (o["targets"],))
        if o["sources"] not in ("first", "late"):
            raise SpecError("layout: sources must be \"first\" or \"late\", got %r" % (o["sources"],))
        o["pin"] = _positions(o.get("pin") or {}, "layout.pin")
        return o
    return {"auto": False, "pin": _positions(lay, "layout")}


def _positions(d, where):
    from ..spec import SpecError
    if not isinstance(d, dict):
        raise SpecError("%s must be an object {name: [x, y]}" % where)
    out = {}
    for k, v in d.items():
        if (not isinstance(v, (list, tuple)) or len(v) != 2
                or not all(isinstance(c, int) and not isinstance(c, bool) and c >= 0 for c in v)):
            raise SpecError("%s[%r] must be [x, y], two whole numbers >= 0, got %r" % (where, k, v))
        out[k] = (v[0], v[1])
    return out


def compute(spec, o=None):
    """{node name: (x, y)} for the spec's nodes (the auto layout plus pins); o = the parsed options (None = defaults).
    Separate flows of one mapping (pipelines that share no link) get their own band of rows, one empty row apart, in the
    order of the spec, so two pipelines never read as one."""
    o = o or dict(DEFAULTS, auto=True, pin={})
    names = [n["name"] for n in spec["nodes"]]
    adj = {n: set() for n in names}
    for lk in spec.get("links") or []:
        a, b = lk[0].split(".")[0], lk[1].split(".")[0]
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
    comps, seen = [], set()
    for n in names:
        if n in seen or not adj[n]:
            continue
        stack, comp = [n], []
        while stack:
            m = stack.pop()
            if m in seen:
                continue
            seen.add(m)
            comp.append(m)
            stack.extend(adj[m] - seen)
        comps.append(set(comp))
    depth = {}

    def d(n, seen=()):
        if n not in depth:
            ps = [lk[0].split(".")[0] for lk in spec.get("links") or [] if lk[1].split(".")[0] == n]
            depth[n] = 0 if not ps or n in seen else 1 + max(d(q, seen + (n,)) for q in ps)
        return depth[n]
    last_all = max([d(n) for n in names if adj[n]] or [0])        # targets "last": one column for every flow
    pos, top = {}, o["y0"]
    for comp in comps:
        sub = {"nodes": [nd for nd in spec["nodes"] if nd["name"] in comp],
               "links": [lk for lk in spec.get("links") or [] if lk[0].split(".")[0] in comp]}
        p = _compute_one(sub, dict(o, y0=top, pin={}, _last=last_all))
        pos.update(p)
        top = max(v[1] for v in p.values()) + 2 * o["dy"]
    rest = [n for n in names if n not in pos]          # transformations with no link: a row under the flows
    for i, n in enumerate(rest):
        pos[n] = (o["x0"] + i * o["dx"], top)
    pos.update({n: xy for n, xy in o["pin"].items()})
    return pos


def _compute_one(spec, o):
    """the layered layout of one connected flow (compute() bands the flows)"""
    names = [n["name"] for n in spec["nodes"]]
    order = {n: i for i, n in enumerate(names)}
    kind = {n["name"]: n.get("type") for n in spec["nodes"]}
    succ, pred = {n: [] for n in names}, {n: [] for n in names}
    for lk in spec.get("links") or []:
        a, b = lk[0].split(".")[0], lk[1].split(".")[0]
        if a in succ and b in pred:
            if b not in succ[a]:
                succ[a].append(b)
            if a not in pred[b]:
                pred[b].append(a)
    linked = [n for n in names if succ[n] or pred[n]]
    col = {}

    def column(n, seen=()):
        if n not in col:
            if n in seen:          # a cycle cannot happen in a valid mapping; place it rather than recurse forever
                return 0
            col[n] = 0 if not pred[n] else 1 + max(column(p, seen + (n,)) for p in pred[n])
        return col[n]
    for n in linked:
        column(n)
    last = max(col.values()) if col else 0
    if o.get("sources", "first") == "late":      # a source sits just left of its first consumer (no long link)
        for n in linked:
            if not pred[n] and succ[n]:
                col[n] = max(0, min(col[s] for s in succ[n]) - 1)
    if o.get("targets", "next") == "last":
        last = max(last, o.get("_last", last))
        for n in linked:
            if kind[n] == "target" and not succ[n]:
                col[n] = last
    cols = {}
    for n in linked:
        cols.setdefault(col[n], []).append(n)
    y = {}

    def place(c, want):
        """stack column c in the order of the wanted rows, dy apart, as close to the wanted rows as possible"""
        ns = sorted(cols[c], key=lambda n: (want.get(n, 0.0), order[n]))
        prev = None
        for n in ns:
            v = want.get(n, 0.0)
            y[n] = v if prev is None else max(v, prev + o["dy"])
            prev = y[n]
    first = sorted(cols.get(0, []), key=lambda n: order[n])
    place(0, {n: i * o["dy"] for i, n in enumerate(first)})

    def mean(ns):
        vs = [y[n] for n in ns if n in y]
        return sum(vs) / len(vs) if vs else None
    def forward(skip_first):
        for c in sorted(cols):
            if c == 0 and skip_first:
                continue
            want = {}
            for n in cols[c]:
                m = mean(pred[n]) if c > 0 else None
                want[n] = m if m is not None else y.get(n, 0.0)
            place(c, want)

    def backward():
        for c in sorted(cols, reverse=True):
            if c == last:
                continue
            want = {}
            for n in cols[c]:
                m = mean(succ[n])
                want[n] = (m + (mean(pred[n]) if pred[n] else m)) / 2 if m is not None else y.get(n, 0.0)
            place(c, want)
    forward(True)
    for _sweep in range(2):
        backward()
        forward(False)
    half = o["dy"] / 2.0 or 1.0          # snap to half rows, then restack (a chain keeps one line)
    for c in sorted(cols):
        place(c, {n: round(y[n] / half) * half for n in cols[c]})
    top = min(y.values()) if y else 0
    pos = {n: (o["x0"] + col[n] * o["dx"], int(round(o["y0"] + y[n] - top))) for n in linked}
    bottom = max([p[1] for p in pos.values()] or [o["y0"] - o["dy"]])
    for i, n in enumerate([n for n in names if n not in pos]):
        pos[n] = (o["x0"] + i * o["dx"], bottom + o["dy"])
    pos.update({n: xy for n, xy in o["pin"].items()})
    return pos


def through_boxes(spec, pos, w=BOX_W, h=BOX_H):
    """[(link, box)] links whose straight line from the output port to the input port crosses a third box (it then reads
    as if that box fed the target). The designer draws links port to port: right edge middle -> left edge middle."""
    out = []
    for lk in spec.get("links") or []:
        a, b = lk[0].split(".")[0], lk[1].split(".")[0]
        if a not in pos or b not in pos:
            continue
        x1, y1 = pos[a][0] + w, pos[a][1] + h / 2.0
        x2, y2 = pos[b][0], pos[b][1] + h / 2.0
        for n, (bx, by) in pos.items():
            if n in (a, b) or bx + w <= min(x1, x2) or bx >= max(x1, x2):
                continue
            for t in (0.0, 0.25, 0.5, 0.75, 1.0):     # sample the segment where it is inside the box's x range
                xa, xb = max(min(x1, x2), bx), min(max(x1, x2), bx + w)
                x = xa + (xb - xa) * t
                yy = y1 + (y2 - y1) * ((x - x1) / (x2 - x1) if x2 != x1 else 0)
                if by - 4 <= yy <= by + h + 4:
                    out.append(("%s -> %s" % (lk[0], lk[1]), n))
                    break
    return out


def overlaps(pos, w=BOX_W, h=BOX_H):
    """[(a, b)] pairs of boxes that overlap (the check a layout must pass)."""
    items = sorted(pos.items())
    out = []
    for i, (a, (ax, ay)) in enumerate(items):
        for b, (bx, by) in items[i + 1:]:
            if abs(ax - bx) < w and abs(ay - by) < h:
                out.append((a, b))
    return out


@template_hook
def apply_canvas_layout(ctx, content):
    o = _opts(ctx.spec)
    if o is None:
        return
    from ..spec import SpecError
    if o["auto"]:
        pos = compute(ctx.spec, o)
    else:
        pos = dict(o["pin"])
        missing = [n["name"] for n in ctx.spec["nodes"] if n["name"] not in pos]
        if missing:
            raise SpecError("layout gives no position for %s (or use \"auto\": true with \"pin\")" % ", ".join(missing))
    txs = [t["name"] for t in content.get("transformations") or []]
    spec_to_tx = {nd["name"]: t for nd, t in zip(ctx.spec["nodes"], ctx.txs)}
    lay = {}
    for n, (x, y) in pos.items():
        t = spec_to_tx.get(n)
        lay[t["name"] if t else n] = {"x": x, "y": y}
    extra = [t for t in txs if t not in lay]
    if extra:
        x_end = max([v["x"] for v in lay.values()] or [DEFAULTS["x0"]]) + o.get("dx", DEFAULTS["dx"])
        for i, t in enumerate(extra):
            lay[t] = {"x": x_end, "y": DEFAULTS["y0"] + i * o.get("dy", DEFAULTS["dy"])}
    unknown = [k for k in lay if k not in txs]
    if unknown:
        raise SpecError("layout names %s, which is not a transformation of this mapping" % ", ".join(sorted(unknown)))
    blob = json.dumps({t: lay[t] for t in txs}, separators=(",", ":"))
    content.setdefault("annotations", []).insert(0, ctx.b.new(LAYOUT_ANNOTATION, jsonBlob=blob, templateId=""))
