"""Node-type registry: one module per transformation under idmc_mapgen/nodes/ registers itself here.

A node builder is ``fn(ctx, nd) -> tx``: it creates the transformation object with ``ctx.b`` (the IMF builder),
registers the groups it exposes for links, and returns the tx. ``compile.build`` appends it to the template.

    from ..registry import node

    @node("expression", doc="Computed ports (OUTPUT / VARIABLE) on a pass-through row.")
    def build(ctx, nd):
        g = ctx.b.group("DefaultGroup", True, True)
        ...
        ctx.out(nd["name"], g)          # link source  "<name>"  (or ctx.out(name, g, "VALID") -> "<name>.VALID")
        ctx.inp(nd["name"], g)          # link target  "<name>"  (or ctx.inp(name + ".Master", g))
        return tx

A node that must not be linked (an unconnected lookup) simply registers no groups.
Keep the ORDER of ``ctx.b.new`` calls identical to the legacy generators: IMF ids are sequential, and the
equivalence tests compare the output byte for byte.

A type has one builder. Registering a type that already has one raises DuplicateNodeType, unless the new builder
says so explicitly: ``@node("joiner", override=True)`` replaces the existing joiner builder.

Every registration also records the module whose import made it (NODE_ORIGIN / HOOK_ORIGIN), also when it goes
through a helper function of another module, so nodes/__init__ can undo exactly what a failed import registered.
"""
import sys

NODES = {}
NODE_ORIGIN = {}     # node type -> (builder, module whose import registered it, or None)
HOOK_ORIGIN = {}     # id(hook) -> (hook, module whose import registered it, or None)


class DuplicateNodeType(ValueError):
    """A node type registered a second time without override=True."""


def importing_module():
    """The module whose import is running at the call site (the import making a registration), or None.

    That is the innermost module body on the stack that is being imported: its globals are those of the module
    sys.modules holds under its name, and it has an import spec. Code that runs in a namespace of its own (exec into
    a new module object, runpy.run_path, a module object made from a spec but never put in sys.modules) is not an
    import: what it registers belongs to the import that ran it. (Recording that namespace instead made
    nodes/__init__ undo the registrations of an extension that imported fine, since such a namespace is never in
    sys.modules afterwards, which is also how a failed import looks.)"""
    f = sys._getframe(1)
    while f is not None:
        if f.f_code.co_name == "<module>":
            g = f.f_globals
            name = g.get("__name__")
            m = sys.modules.get(name) if isinstance(name, str) else None
            if m is not None and getattr(m, "__dict__", None) is g and g.get("__spec__") is not None:
                return name
        f = f.f_back
    return None


def node(type_name, doc="", override=False):
    def deco(fn):
        old = NODES.get(type_name)
        if old is not None and old is not fn and not override:
            raise DuplicateNodeType("node type %r registered twice (already built by %s.%s); to replace that builder, "
                                    "register the new one with @node(%r, override=True)"
                                    % (type_name, getattr(old, "__module__", "?"), getattr(old, "__qualname__", "?"), type_name))
        fn.node_type = type_name
        fn.doc = doc
        NODES[type_name] = fn
        NODE_ORIGIN[type_name] = (fn, importing_module())
        return fn
    return deco


class Ctx:
    """Per-build state shared by the node builders."""

    def __init__(self, b, spec, now):
        self.b = b                       # imf.B builder
        self.spec = spec
        self.now = now                   # createTime stamp (ISO, UTC)
        self.conns = spec.get("connections", {})
        self.txs = []                    # transformations, in spec order
        self.outg = {}                   # node name -> {group suffix ("" = default): group obj}
        self.ing = {}                    # link key ("NAME" or "NAME.Group") -> input group obj

    def conn(self, alias):
        if alias not in self.conns:
            raise KeyError("connection alias %r is not in spec.connections (have: %s)" % (alias, ", ".join(sorted(self.conns))))
        return self.conns[alias]

    def kind(self, alias):
        """Connector family of a connection alias: BQ (default), PG, JDBC, FF, SF, ..."""
        return self.conn(alias).get("kind", "BQ")

    def out(self, name, group, suffix=""):
        self.outg.setdefault(name, {})[suffix] = group

    def inp(self, key, group):
        self.ing[key] = group


TEMPLATE_HOOKS = []


def template_hook(fn):
    """Register fn(ctx, content), called after the Template content is assembled, before $$classInfo."""
    if fn not in TEMPLATE_HOOKS:
        TEMPLATE_HOOKS.append(fn)
        HOOK_ORIGIN[id(fn)] = (fn, importing_module())
    return fn
