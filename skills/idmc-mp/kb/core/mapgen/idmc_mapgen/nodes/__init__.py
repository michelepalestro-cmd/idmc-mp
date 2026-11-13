"""Transformation builders. Importing this package registers every node type.

The core types are imported explicitly (an error there is a bug and must surface). Any other module dropped into
this directory (new transformation types, delegates such as lookup_connected / expression_window, template hooks)
is discovered and imported automatically. A module that fails to import is never silently ignored:
- whatever it registered before failing is rolled back (no half-imported node types or template hooks), also when
  the module that imported it handled the ImportError (an optional dependency); a core hook or builder it removed
  before failing is put back (unless a module that imported fine during its import may have removed it);
- the failure is kept in IMPORT_ERRORS, and what the module's source declares in FAILED_SCOPE;
- compile.build refuses every spec that may need the module: a spec using a node type it declares, and any spec
  when it adds template hooks (a hook acts on every build), uses the registry in a way that hides what it registers
  (NODES or TEMPLATE_HOOKS named directly, node() or the registry module assigned to a variable or passed around --
  getattr(registry, name) included --, a node type name computed at run time, getattr with a registry name written
  as a literal), reaches modules or code at run time (import_module, reload, exec_module, load_module,
  spec_from_file_location, run_path or run_module as an attribute or an imported name, sys.modules, and the
  built-ins __import__, exec and eval used by those plain names), imports a module of this package whose functions
  register (a kit's install(): the module may have called it) or code outside this package and the standard
  library (an installed kit: not read), or its source cannot be analysed. A spec that cannot need it still builds,
  so a half-written new node type does not block unrelated work. The analysis reads the source: a registration it
  cannot see is not found, e.g. one through a registry function fetched with getattr under a name built at run time
  from the package (getattr(idmc_mapgen.registry, "no" + "de")), or through a built-in reached as an attribute
  (builtins.__import__, importlib.__import__, builtins.exec).
Registrations made by code an extension runs in a namespace of its own (exec, runpy.run_path) belong to that
extension's import: they are kept when it imports fine (registry.importing_module).
Registering a type that already exists (e.g. a new joiner) needs ``@node("joiner", override=True)``; without it
the module fails to import with DuplicateNodeType, and specs using that type are refused.
"""
import ast
import importlib
import importlib.machinery
import os
import pkgutil
import sys

from .. import registry
from . import (aggregator, cleanse, dedup, expression, filter, generic, joiner, lookup, masking, rank,  # noqa: F401
               router, rulespec, sequence, sorter, source, target, union)

CORE = {"aggregator", "cleanse", "dedup", "expression", "filter", "generic", "joiner", "lookup", "masking", "rank",
        "router", "rulespec", "sequence", "sorter", "source", "target", "union"}
IMPORT_ERRORS = {}   # module name -> "ExcType: message"
FAILED_SCOPE = {}    # module name -> (node types it declares, reason it may act on every spec or None)
EXTENSIONS = []      # extension modules imported successfully

_TOP = __name__.rpartition(".")[0]                       # the package this one belongs to (idmc_mapgen)
# this loader, the registry and the package's lazy __init__: not registration helpers
_INFRA = frozenset([__name__, _TOP + ".registry", _TOP])
_MUTATORS = frozenset(["append", "insert", "extend", "remove", "pop", "popitem", "clear", "update", "setdefault",
                       "__setitem__", "__delitem__", "__iadd__"])
_REGISTRY_NAMES = frozenset(["node", "template_hook", "NODES", "TEMPLATE_HOOKS"])
# names that import a module or run code chosen at run time (what that code registers cannot be read)
_DYNAMIC_FUNCS = frozenset(["__import__", "exec", "eval"])
_DYNAMIC_ATTRS = frozenset(["import_module", "exec_module", "load_module", "spec_from_file_location", "run_path",
                            "run_module", "reload"])


def _name(n):
    return n.id if isinstance(n, ast.Name) else n.attr if isinstance(n, ast.Attribute) else None


def _parse(path):
    with open(path, "rb") as f:   # bytes: ast honours a UTF-8 BOM and a coding cookie, exactly as import does
        return ast.parse(f.read(), path)


def _names(tree):
    """The registry names a source binds by import (``from ..registry import node as reg`` binds reg to node()), the
    names it binds otherwise (a ``node`` variable is not node()), and the AST facts the rules below need."""
    walk = list(ast.walk(tree))
    imported = [a for n in walk if isinstance(n, ast.ImportFrom) for a in n.names]

    def bound_as(*names):
        return set(names) | {a.asname or a.name for a in imported if a.name in names}
    bound = set()
    for n in walk:
        if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load):
            bound.add(n.id)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(n.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
    return {"node": bound_as("node"), "hook": bound_as("template_hook"), "hooks": bound_as("TEMPLATE_HOOKS"),
            "nodes": bound_as("NODES"),
            "module": bound_as("registry") | {a.asname for n in walk if isinstance(n, ast.Import) for a in n.names
                                              if a.asname and a.name.rsplit(".", 1)[-1] == "registry"},
            "dynamic": bound_as(*_DYNAMIC_ATTRS),
            "sys": {"sys"} | {a.asname for n in walk if isinstance(n, ast.Import) for a in n.names
                              if a.asname and a.name == "sys"},
            "sys_modules": {a.asname or a.name for n in walk if isinstance(n, ast.ImportFrom) and not n.level
                            and n.module == "sys" for a in n.names if a.name == "modules"},
            "bound": bound, "called": {id(n.func) for n in walk if isinstance(n, ast.Call)},
            "bases": {id(n.value) for n in walk if isinstance(n, ast.Attribute)}}


def _is_node_fn(f, nm):
    """f (what a call calls) is the registry's node(): node, its import alias, or <registry module>.node."""
    return ((isinstance(f, ast.Name) and f.id in nm["node"])
            or (isinstance(f, ast.Attribute) and f.attr == "node" and _name(f.value) in nm["module"]))


def _hidden_use(n, nm):
    """Why n hands node() or the registry module to other code (what then gets registered cannot be read), or None."""
    if not isinstance(getattr(n, "ctx", None), ast.Load) or id(n) in nm["called"]:
        return None
    if isinstance(n, ast.Name) and n.id not in nm["bound"]:
        if n.id in nm["node"]:
            return "it passes the registry's node() around, so the node types it registers cannot be read"
        if n.id in nm["module"] and id(n) not in nm["bases"]:
            return "it passes the registry module around, so what it registers cannot be read"
    if isinstance(n, ast.Attribute) and n.attr == "node" and _name(n.value) in nm["module"]:
        return "it passes the registry's node() around, so the node types it registers cannot be read"
    return None


def _dynamic_use(n, nm):
    """Why n reaches a module or runs code chosen at run time (importlib.import_module, __import__, sys.modules,
    runpy, exec, eval, a loader's exec_module; getattr of a registry name): what that registers cannot be read."""
    what = None
    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in nm["bound"]:
        if n.id in _DYNAMIC_FUNCS or n.id in nm["dynamic"] or n.id in nm["sys_modules"]:
            what = "sys.modules" if n.id in nm["sys_modules"] else n.id
    elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
        if n.attr in _DYNAMIC_ATTRS:
            what = n.attr
        elif n.attr == "modules" and _name(n.value) in nm["sys"]:
            what = "sys.modules"
    elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) > 1
          and isinstance(n.args[1], ast.Constant) and n.args[1].value in _REGISTRY_NAMES):
        what = "getattr(..., %r)" % n.args[1].value
    if what is None:
        return None
    return "it reaches modules or code at run time (%s), so what it registers cannot be read" % what


def _scope(tree):
    """(node types a source registers with node("<type>"), reason it may act on ANY spec, or None)."""
    nm = _names(tree)
    types = set()
    for n in ast.walk(tree):
        x = _name(n)
        if x in nm["hook"] or x in nm["hooks"]:
            return frozenset(types), "it registers template hooks"
        if x in nm["nodes"]:
            return frozenset(types), "it uses the node registry directly"
        if isinstance(n, ast.Call) and _is_node_fn(n.func, nm):
            arg = n.args[0] if n.args else next((k.value for k in n.keywords if k.arg == "type_name"), None)
            if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                return frozenset(types), "it registers node types computed at run time"
            types.add(arg.value)
            continue
        why = _hidden_use(n, nm) or _dynamic_use(n, nm)
        if why:
            return frozenset(types), why
    return frozenset(types), None


def _registers_in_functions(tree):
    """True when a function of this source registers a node type or a template hook (a helper such as a kit's
    install()): node() or template_hook used there, or a change to NODES / TEMPLATE_HOOKS (reading them does not
    count). Decorators and module-level code do not count: they run when the module is imported, as that module's
    own registrations."""
    nm = _names(tree)
    regs = nm["nodes"] | nm["hooks"]
    for f in ast.walk(tree):
        if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        for st in (f.body if isinstance(f.body, list) else [f.body]):
            for n in ast.walk(st):
                if _name(n) in nm["hook"] or (isinstance(n, ast.Call) and _is_node_fn(n.func, nm)) or _hidden_use(n, nm):
                    return True
                if isinstance(n, ast.Subscript) and not isinstance(n.ctx, ast.Load) and _name(n.value) in regs:
                    return True
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _MUTATORS
                        and _name(n.func.value) in regs):
                    return True
                if isinstance(n, ast.AugAssign) and _name(n.target) in regs:
                    return True
    return False


def _imported_modules(tree, package):
    """Fully qualified names of the modules a source (in ``package``) imports, anywhere in it (also names that may be
    a submodule: "from pkg import x" gives pkg and pkg.x)."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level:
                parts = package.split(".")
                if n.level > len(parts):
                    continue
                base = ".".join(parts[:len(parts) - n.level + 1] + ([n.module] if n.module else []))
            out.append(base)
            out += [base + "." + a.name for a in n.names if a.name != "*"]    # "from pkg import submodule"
    return [m for m in dict.fromkeys(out) if m]


def _in_package(mod):
    return mod == _TOP or mod.startswith(_TOP + ".")


def _external(mod):
    """True for a module outside this package and the standard library that exists (installed, on sys.path, or
    loaded): its code may register through the registry (a kit), and this check does not read it."""
    top = mod.partition(".")[0]
    if not top or _in_package(top) or top in sys.stdlib_module_names or top in sys.builtin_module_names:
        return False
    if top in sys.modules:
        return sys.modules[top] is not None
    try:
        return importlib.machinery.PathFinder.find_spec(top) is not None     # searched, not imported
    except (ImportError, ValueError):
        return False


def _module_source(fullname):
    """The source file of a module of this package, found without importing anything; None when there is none."""
    m = sys.modules.get(fullname)
    f = getattr(m, "__file__", None) if m is not None else None
    if f is None:
        parent = sys.modules.get(fullname.rpartition(".")[0])
        path = getattr(parent, "__path__", None)
        if path is None:
            return None
        try:
            found = importlib.machinery.PathFinder.find_spec(fullname, list(path))
        except (ImportError, ValueError):
            return None
        f = getattr(found, "origin", None)
    return f if isinstance(f, str) and f.endswith(".py") else None


def _through_helper(tree, package, seen):
    """(import chain, kind) through which a source reaches registration code it does not show: a module of this
    package whose functions register (kind "helper": the source may have called them) or whose source is too deep to
    analyse ("unreadable"), or code outside this package and the standard library (kind "external": an installed
    kit, not read); None when there is none."""
    for mod in _imported_modules(tree, package):
        if mod in seen or mod in _INFRA:
            continue
        seen.add(mod)
        if not _in_package(mod):
            if _external(mod):
                return [mod], "external"
            continue
        path = _module_source(mod)
        if path is None:
            continue
        try:
            sub = _parse(path)
        except (SyntaxError, OSError, ValueError):
            continue          # it imported (or will import) on its own; its own failure is reported for it
        except (RecursionError, MemoryError):
            return [mod], "unreadable"    # too deep to analyse: it may register
        if _registers_in_functions(sub):
            return [mod], "helper"
        found = _through_helper(sub, mod if os.path.basename(path) == "__init__.py" else mod.rpartition(".")[0], seen)
        if found:
            return [mod] + found[0], found[1]
    return None


def source_scope(path, package=__name__):
    """(node types a module source declares with @node("<type>"), reason it may act on ANY spec, or None).

    Read statically, so it also works for a module that failed before registering anything. Template hooks, direct
    registry use, node() under another name, computed type names, modules or code reached at run time, importing a
    module whose functions register or code outside this package and the standard library, and unreadable sources
    all count as "may act on any spec". ``package``: the package the module is in (for its relative imports)."""
    try:
        tree = _parse(path)
    except SyntaxError:
        return frozenset(), "its source does not parse"
    except (OSError, ValueError):
        return frozenset(), "its source cannot be read"
    except (RecursionError, MemoryError) as e:
        return frozenset(), "its source cannot be analysed (%s: too deeply nested)" % type(e).__name__
    types, why = _scope(tree)
    if why is None:
        found = _through_helper(tree, package, set())
        if found:
            chain, kind = found
            why = ({"helper": "it imports %s, whose functions register node types or template hooks (it may have "
                              "called them)",
                    "external": "it imports %s, code outside idmc_mapgen and the standard library that this check "
                                "does not read (it may register node types or template hooks)",
                    "unreadable": "it imports %s, whose source cannot be analysed (it may register node types or "
                                  "template hooks)"}[kind] % " -> ".join(chain))
    return types, why


def _registered_by(fn, record):
    """The module whose import made a registration, as the registry recorded it (registry.NODE_ORIGIN / HOOK_ORIGIN),
    or None without a record (NODES / TEMPLATE_HOOKS changed directly)."""
    return record[1] if record is not None and record[0] is fn else None


def _snapshot():
    return dict(registry.NODES), list(registry.TEMPLATE_HOOKS), set(sys.modules), dict(registry.NODE_ORIGIN)


def _uses_registry_lists(mod):
    """True when a module's source names NODES or TEMPLATE_HOOKS (it may remove registrations itself)."""
    f = getattr(mod, "__file__", None)
    if not (isinstance(f, str) and f.endswith(".py")):
        return False
    try:
        tree = _parse(f)
    except Exception:          # unreadable (or too deep to analyse): it may have
        return True
    nm = _names(tree)
    regs = nm["nodes"] | nm["hooks"]
    return any(_name(n) in regs for n in ast.walk(tree))


def _restore_removed(before):
    """Put back the node types and template hooks a failed import removed (a core builder or hook it was replacing),
    each hook in its old place; returns (node types, hooks) put back. Not when a module that imported successfully
    during that import names NODES / TEMPLATE_HOOKS: it may have removed them itself (a sibling replacing a core
    hook), and what it did is kept."""
    nodes_before, hooks_before, modules_before, origins_before = before
    gone = [t for t in nodes_before if t not in registry.NODES]
    missing = [h for h in hooks_before if h not in registry.TEMPLATE_HOOKS]
    if not (gone or missing):
        return [], []
    if any(_uses_registry_lists(sys.modules.get(m)) for m in set(sys.modules) - modules_before):
        return [], []
    for t in gone:
        registry.NODES[t] = nodes_before[t]
        if t in origins_before:
            registry.NODE_ORIGIN[t] = origins_before[t]
    cur = registry.TEMPLATE_HOOKS
    for i, h in enumerate(hooks_before):
        if h in cur:
            continue
        prev = next((p for p in reversed(hooks_before[:i]) if p in cur), None)
        nxt = next((p for p in hooks_before[i + 1:] if p in cur), None)
        cur.insert(cur.index(prev) + 1 if prev is not None else cur.index(nxt) if nxt is not None else len(cur), h)
    return gone, missing


def _undo(before, failed):
    """Undo what an import registered on behalf of a module whose import failed; returns (node types, hooks) undone
    (with ``failed``, also the ones it removed).

    The registry records which import made each registration, also when it ran through a helper function of a module
    that imports fine (a kit's install(), a private nodes/_kit.py). A registration whose module is no longer in
    sys.modules (its import failed: the extension itself, or a module whose ImportError the extension handled) is
    undone; one made by a module that imported successfully during its own import (a sibling's
    node("alias")(expression.build)) is kept. ``failed`` (the extension itself failed): a registration without a
    record (a direct NODES / TEMPLATE_HOOKS change) is undone too when its function belongs to a module that failed
    or that was loaded BEFORE this import (the failed code registered an existing builder or hook itself, e.g.
    node("filter", override=True)(joiner.build)), and what it removed is put back (_restore_removed)."""
    nodes_before, hooks_before, modules_before, origins_before = before

    def undo(fn, record):
        by = _registered_by(fn, record)
        if by == __name__:    # this loader's own import: code of the extension that is not an import of its own
            return failed     # (e.g. a module that replaced itself in sys.modules)
        if by:
            return by not in sys.modules
        if not failed:
            return False
        m = getattr(fn, "__module__", None)
        return m not in sys.modules or m in modules_before
    types = [t for t, fn in registry.NODES.items()
             if nodes_before.get(t) is not fn and undo(fn, registry.NODE_ORIGIN.get(t))]
    for t in types:
        if t in nodes_before:
            registry.NODES[t] = nodes_before[t]
        else:
            del registry.NODES[t]
        if t in origins_before:
            registry.NODE_ORIGIN[t] = origins_before[t]
        else:
            registry.NODE_ORIGIN.pop(t, None)
    hooks = [h for h in registry.TEMPLATE_HOOKS
             if h not in hooks_before and undo(h, registry.HOOK_ORIGIN.get(id(h)))]
    registry.TEMPLATE_HOOKS[:] = [h for h in registry.TEMPLATE_HOOKS if h not in hooks]
    for h in hooks:
        registry.HOOK_ORIGIN.pop(id(h), None)
    if failed:
        gone, missing = _restore_removed(before)
        return types + gone, hooks + missing
    return types, hooks


def _load_extension(info):
    name = info.name
    before = _snapshot()
    try:
        importlib.import_module(__name__ + "." + name)
    except Exception as e:   # keep the core usable; compile.build refuses the specs that may need this module
        IMPORT_ERRORS[name] = "%s: %s" % (type(e).__name__, e)
        types, hooks = _undo(before, failed=True)
        folder = getattr(info.module_finder, "path", None)
        if info.ispkg or not folder:
            declared, why = frozenset(), "it is a package or not a plain source file"
        else:
            try:
                declared, why = source_scope(os.path.join(folder, name + ".py"))
            except Exception as ae:   # the analysis must never break the core (e.g. RecursionError: a huge expression)
                declared, why = frozenset(), "its source could not be analysed (%s: %s)" % (type(ae).__name__, ae)
        if hooks and not why:
            why = "it adds or removes template hooks"
        FAILED_SCOPE[name] = (declared | frozenset(types), why)
        return False
    _undo(before, failed=False)   # registered by a module that failed and whose ImportError this one handled
    EXTENSIONS.append(name)
    return True


for _m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
    if _m.name in CORE or _m.name.startswith("_"):
        continue
    _load_extension(_m)
