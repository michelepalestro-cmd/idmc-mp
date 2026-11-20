"""Load a mapping spec: profile merge, ${VAR} substitution, structural validation with clear messages.

    spec = load_spec("examples/m_orders.json", profile="local/profile.local.json")

Profile (JSON; every key optional):
    {"org": {"v2Id": "...", "guid": "<22-char org guid>", "name": "<org name>"},
     "runtimeEnvironment": {"id": "...", "name": "..."},
     "folder": {"project": "...", "projectGuid": "...", "name": "...", "guid": "..."},
     "connections": {"WH": {"guid": "...", "name": "...", "repoHandle": "<v2 connection id>", "kind": "BQ"}},
     "vars": {"WH_PROJECT": "my-project", "DS": "my_dataset"}}

Which profile (the same answer for load_spec, compile, lint, deploy and mapgen.py):
- the ``profile`` argument (CLI --profile) when it is a path or a non-empty dict (None, {} and "" mean "not given");
  a relative path resolves against the current directory;
- else the spec's own "profile" key: a path relative to the spec file's folder (never the cwd; for a dict spec, its
  "baseDir" when it is a non-empty string, else the cwd) or an inline object (an inline object holding "auth" is
  refused with a SpecError: a spec never decides where credentials go);
- else ``default_profile`` (mapgen.py passes its fallbacks: $MAPGEN_PROFILE, ./profile.json, local/profile.local.json);
- else none.

Merge rules (the spec always wins; the merge sees the spec after ${VAR} substitution, so a node's "conn", a
"connections" key or the whole "nodes" list may come from a var):
- orgGuid <- org.guid, orgName <- org.name, runtimeEnvironment <- runtimeEnvironment;
- folder: the profile folder, overridden key by key by the spec's folder;
- connections: only the aliases the spec uses (a node's "conn") or names itself; each alias = the profile entry
  overridden key by key by the spec's entry. Unused profile connections are NOT added (each one becomes a
  package dependency the target org must resolve). The ${VAR}s of the profile values that are kept are substituted
  too; those of unused or overridden profile values are not looked at (an inline "profile" object as well: the
  loaded spec keeps it as written).
- vars: profile vars, then the spec's own "vars", then the ``vars`` argument. A var's value may use other vars.
Substitution, in every string and dict key (lists, tuples and objects are walked):
- ``${NAME}`` is replaced from vars (unknown name = error). A string that is exactly one ``${NAME}`` takes the
  var's value with its JSON type (false stays false, 5 stays 5, a list stays a list) -- except in a text slot (see
  _TEXT_SPEC / _TEXT_NODE: an expression, a condition, SQL, an object path, an advanced / runtime attribute value,
  a name...), where a number or true / false is text in JSON spelling ("1000", "1.5", "true"), as the IMF holds it;
  in a raw IMF property ("set", a generic node's "props" / "objs" / field "extra") true / false is text and a number
  stays a number only under the IMF's numeric keys (_IMF_NUMBER_KEYS: precision, scale, batchSize, ...). null stays
  null everywhere, as if null were written there. Inside a longer string a number, true, false or null is written
  in JSON spelling, and a list or object is an error. A value JSON has no type for (a Python caller's date or
  Decimal) is its str() text, whole or inside a longer string.
  (substitute() alone knows no slots: there every whole value keeps its JSON type.)
- ``$${`` is a literal ``${`` (``$${NAME}`` gives ``${NAME}``). Any other ``${`` (``${ X }``, ``${A-B}``, an unclosed
  ``${``) and three or more ``$`` before ``{`` are errors, so nothing that looks like ``${...}`` is left over.
- Informatica's own ``$$PARAM`` / ``$PMCacheDir`` (no braces) are left alone.
The loaded spec's "vars" holds the effective value of every var it declares; a spec loaded from a file gets
"baseDir" = its folder, against which package.py resolves relative projectJson / folderJson. A spec file's own
"baseDir" is read as its "profile" key is: a leading '~' is the home folder (os.path.expanduser), an absolute one is
kept, a relative one is resolved against the spec file's folder; an empty or null one means that folder. A dict
spec's "baseDir" is kept as it is.
Spec and profile files are UTF-8 with or without a BOM. load_spec reports every problem at once in one SpecError,
including what the packager would refuse without reading a file (validate(..., for_package=True)).
Load a spec once: loading consumes the $${ escapes (and fills every var), so a loaded spec given to load_spec, prepare,
lint, compile_file or deploy again is substituted a second time ("$${X}" loads as "${X}", which a second load replaces
with X's value, or refuses as undefined when X is not defined for that load: the loaded spec's "vars" keeps the vars
it declares, not the caller's vars argument or an explicit profile's). Give those entry points the spec file or the
dict as written; build() and the package functions take the loaded spec and substitute nothing (deploy.deploy lints
the raw spec for this reason).
"""
import copy
import json
import os
import re


class SpecError(ValueError):
    """A spec (or profile) problem the author must fix. str() lists every problem found."""

    def __init__(self, problems):
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__(self.problems[0] if len(self.problems) == 1 else
                         "%d spec problems:\n  - %s" % (len(self.problems), "\n  - ".join(self.problems)))


_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_VAR = re.compile(r"\$(\$?)\{(%s)\}" % _NAME)       # ${NAME} / $${NAME} (kept for importers; the parser is _parse)
_DOLLARS_BRACE = re.compile(r"\$+\{")
_REF_TAIL = re.compile(r"(%s)\}" % _NAME)
_FOLDER_KEYS = ("project", "projectGuid", "name", "guid")
_CONN_STR_KEYS = ("guid", "name", "repoHandle", "kind", "typeSystem")
_ASSET_KEYS = ("guid", "name", "type", "path")
_NAME_MSG = "'name' must be a non-empty string"
_NODES_MSG = "'nodes' must be a non-empty list"
_LINKS_MSG = "'links' must be a list"
_SELECTION_MSG = "links[%d]: the field selection must be a list, a {in: out} map or {\"exclude\": [...]}"
_CONNS_MSG = "'connections' must be an object {alias: {guid, name, repoHandle, kind?}}"


def _brief(v, n=60):
    try:
        s = json.dumps(v, ensure_ascii=False, default=repr)
    except (TypeError, ValueError):
        s = repr(v)
    return s if len(s) <= n else s[:n - 3] + "..."


def _dedupe(items):
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _is_path(x):
    return isinstance(x, (str, bytes, os.PathLike))


def _given(x):
    """An explicit profile: a non-empty path or a non-empty dict (None, {} and "" mean "not given")."""
    if x is None:
        return False
    if isinstance(x, dict) or _is_path(x):
        return bool(x if isinstance(x, dict) else os.fspath(x))
    return True                      # any other type is "given" and refused by _open_profile


def _read_json(p, what):
    """A JSON file (UTF-8, BOM allowed) -> object. Raises SpecError naming the file."""
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SpecError("%s not found: %s" % (what, p)) from None
    except ValueError as e:          # JSONDecodeError, UnicodeDecodeError
        raise SpecError("%s is not valid JSON (%s): %s" % (what, e, p)) from None
    except OSError as e:
        raise SpecError("%s cannot be read (%s): %s" % (what, e.strerror or e, p)) from None


# ---------------------------------------------------------------- profile
def _open_profile(src, base_dir, label):
    """(profile dict, absolute path or None). A relative path resolves against base_dir (None = the cwd) only."""
    if isinstance(src, dict):
        return copy.deepcopy(src), None
    if not _is_path(src):
        raise SpecError("%s must be a profile path or an object, got %s" % (label, _brief(src)))
    p = os.path.expanduser(os.fsdecode(os.fspath(src)))
    full = os.path.abspath(p if os.path.isabs(p) else os.path.join(base_dir or os.getcwd(), p))
    if not os.path.exists(full):
        rel = "" if os.path.isabs(p) else ", relative to %s" % ("the spec file's folder" if base_dir else "the current directory")
        raise SpecError("profile not found: %s (%s %r%s)" % (full, label, p, rel))
    prof = _read_json(full, "profile")
    if not isinstance(prof, dict):
        raise SpecError("profile must be a JSON object, got %s: %s" % (_brief(prof), full))
    return prof, full


def _var_name_problems(d, where):
    """Var names that no ${NAME} can use (a key such as "${X}" would also stay unexpanded in the loaded spec)."""
    return ["%s: %r is not a variable name (letters, digits and _, not starting with a digit), so no ${...} can use it"
            % (where, k) for k in d if not (isinstance(k, str) and re.fullmatch(_NAME, k))]


def _conn_problems(alias, c, label="connection"):
    if not isinstance(c, dict):
        return ["%s %r must be an object" % (label, alias)]
    return ["%s %r: %r must be a string, got %s" % (label, alias, k, _brief(c[k]))
            for k in _CONN_STR_KEYS if c.get(k) is not None and not isinstance(c[k], str)]


_PROFILE_OBJECTS = (("org", "{v2Id, guid, name}"), ("auth", "{...}"), ("runtimeEnvironment", "{id, name}"),
                    ("folder", "{project, projectGuid, name, guid}"), ("folders", "{key: folder}"),
                    ("connections", "{alias: {guid, name, repoHandle, kind?}}"), ("vars", "{NAME: value}"),
                    ("guards", "{protectedFolders, protectedTargets, busyTaskPrefixes}"), ("sourceControl", "{enabled, checkinNew}"))


def profile_problems(prof, where=None):
    """Type problems of a profile: a section that is not an object, a connection that is not one, bad guards."""
    w = "profile %s" % where if where else "profile"
    if not isinstance(prof, dict):
        return ["%s must be a JSON object, got %s" % (w, _brief(prof))]
    errs = []
    for k, shape in _PROFILE_OBJECTS:
        v = prof.get(k)
        if v is not None and not isinstance(v, dict):
            errs.append("%s: %r must be an object %s, got %s" % (w, k, shape, _brief(v)))
    if isinstance(prof.get("connections"), dict):
        for a, c in prof["connections"].items():
            errs += _conn_problems(a, c, w + ": connection")
    if isinstance(prof.get("vars"), dict):
        errs += _var_name_problems(prof["vars"], w + ": vars")
    if isinstance(prof.get("folder"), dict):
        errs += ["%s: folder.%s must be a string, got %s" % (w, k, _brief(prof["folder"][k]))
                 for k in _FOLDER_KEYS if prof["folder"].get(k) is not None and not isinstance(prof["folder"][k], str)]
    if isinstance(prof.get("folders"), dict):
        errs += ["%s: folders.%s must be an object {project, projectGuid, name, guid}" % (w, k)
                 for k, v in prof["folders"].items() if not isinstance(v, dict)]
    guards = prof.get("guards")
    if isinstance(guards, dict):
        for k in ("protectedFolders", "protectedTargets", "busyTaskPrefixes"):
            v = guards.get(k)
            if v is None:
                continue
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                errs.append("%s: guards.%s must be a list of strings, got %s" % (w, k, _brief(v)))
                continue
            for x in v if k != "busyTaskPrefixes" else ():
                try:
                    re.compile(x)
                except re.error as e:
                    errs.append("%s: guards.%s pattern %r is not a valid regular expression (%s)" % (w, k, x, e))
    if prof.get("workDir") is not None and not isinstance(prof["workDir"], str):
        errs.append("%s: 'workDir' must be a path string, got %s" % (w, _brief(prof["workDir"])))
    return errs


def load_profile(profile, base_dir=None):
    """A profile dict (copied) or the path of a profile JSON -> dict; None, {} and "" give {}.

    A relative path resolves against ``base_dir`` when it is given (a spec's own "profile" key: the spec file's
    folder), else against the current directory -- never one and then the other. Raises SpecError when the file is
    missing, is not JSON, is not an object, or a section has the wrong type (see profile_problems)."""
    if not _given(profile):
        return {}
    prof, path = _open_profile(profile, base_dir, "profile")
    probs = profile_problems(prof, path)
    if probs:
        raise SpecError(probs)
    return prof


def resolve_profile(spec, profile=None, base_dir=None, default=None):
    """The profile a spec loads with -> (profile dict, absolute path or None); see "Which profile" above.

    ``base_dir``: the folder the spec's own "profile" key is relative to (the spec file's folder; None = the cwd).
    Raises SpecError when the chosen profile cannot be read or is not a JSON object."""
    if _given(profile):
        return _open_profile(profile, None, "the profile argument")
    own = spec.get("profile") if isinstance(spec, dict) else None
    if _given(own):
        if not (isinstance(own, dict) or _is_path(own)):
            return {}, None                      # shape_problems() reports the bad "profile" value
        if isinstance(own, dict) and own.get("auth") is not None:
            # a spec may come from anyone: it must never say where (or with which variables) credentials are sent
            raise SpecError("the spec's inline \"profile\" object may not hold \"auth\": login settings come only from "
                            "a profile file (--profile, $MAPGEN_PROFILE, ./profile.json, local/profile.local.json, or "
                            "a profile file the spec names) and the login file ~/.idmc_toolkit/IDMC_LOGIN.txt")
        return _open_profile(own, base_dir, "the spec's \"profile\" key")
    if _given(default):
        return _open_profile(default, None, "the default profile")
    return {}, None


# ---------------------------------------------------------------- ${VAR} substitution
def _snippet(s, start):
    end = s.find("}", start)
    if 0 <= end < start + 48:
        return s[start:end + 1]
    return s[start:start + 24] + ("..." if len(s) > start + 24 else "")


def _parse(s):
    """Split s into literal text and ("ref", NAME) pieces -> (pieces, problems)."""
    pieces, probs, pos = [], [], 0
    for m in _DOLLARS_BRACE.finditer(s):
        if m.start() < pos:
            continue
        n = m.end() - m.start() - 1                      # how many '$' before the '{'
        if n == 1:
            t = _REF_TAIL.match(s, m.end())
            if t:
                pieces += [s[pos:m.start()], ("ref", t.group(1))]
                pos = t.end()
            else:
                probs.append("%r is not a ${NAME} placeholder (NAME = letters, digits and _, not starting with a digit; "
                             "write $${ for a literal ${)" % _snippet(s, m.start()))
        elif n == 2:
            pieces.append(s[pos:m.start()] + "${")      # the escape: a literal ${
            pos = m.end()
        else:
            probs.append("%r: %d '$' before '{' is ambiguous (${NAME} is a variable, $${...} a literal ${...}; "
                         "put any other '$' into a var)" % (_snippet(s, m.start()), n))
    pieces.append(s[pos:])
    return [p for p in pieces if p != ""], probs


class _Typed:
    """A number or true / false that a whole-value ${NAME} put somewhere. _finish() turns it into text in a text slot
    and into the plain JSON value anywhere else (where it lands is only known once the spec is merged)."""
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __deepcopy__(self, memo):
        return self                              # immutable

    def __repr__(self):
        return "_Typed(%r)" % (self.value,)


# Text slots: the places that the IMF (or the package) holds as text. A path inside the spec ("*" = any key or list
# index); _TEXT_NODE paths are inside one node (any type), _TEXT_NODE_TYPE ones inside a node of that type only (a
# generic node's "groups" carry booleans where a router's carry conditions). A _Typed number or true / false in a text
# slot becomes text in JSON spelling; everywhere else (truncate, createTarget, poll, precision, prec / scale,
# passthrough, packageOverrides, vars, ...) it keeps its JSON type, like a literal written there. Raw IMF properties
# ("set", generic "props" / "objs" / field "extra") follow the IMF's types instead: see _IMF_NUMBER_KEYS.
_TEXT_SPEC = tuple([(k,) for k in ("name", "description", "orgGuid", "orgName", "guid", "taskName", "documentType", "baseDir")] +
                   [("folder", "*"), ("runtimeEnvironment", "*"), ("connections", "*", "*"), ("assets", "*", "*"),
                    ("links", "*", 0), ("links", "*", 1), ("links", "*", 2, "*"), ("links", "*", 2, "exclude", "*"),
                    ("flowOrder", "*", "*", "*"), ("projectJson", "*"), ("folderJson", "*")] +
                   [("inOutParameters", "*", k) for k in ("name", "type", "default", "description", "retention", "aggregation")])
_TEXT_NODE = tuple(
    [(k,) for k in ("type", "name", "conn", "object", "query", "objkind", "cond", "pre_sql", "preSQL", "post_sql", "postSQL",
                    "op", "disposition", "updateStrategy", "by", "ret", "policy", "join", "master", "detail", "asset",
                    "mappletGuid", "inputGroup", "outputGroup", "sqlType", "errorNativeType")] +
    [(k, "*") for k in ("advanced", "cond", "updateColumns", "keys", "groupBy", "oprAttrs", "rtAttrs", "inputs", "map",
                        "passthrough")] +
    [(k, "*", "*") for k in ("advanced", "cond", "extra_opr", "extra_rt", "writerAttrs", "map")] +
    [(k, "*", i) for k in ("fields", "inputs", "outputs") for i in (0, 1, 3)] +       # field tuples: name, TYPE, nativeType
    [("fields", "*", 5, "*")] +                                                          # field tuple flags ("true" / "false")
    [("fields", "*", k) for k in ("name", "type", "expr", "kind")] +                     # field objects
    [("passthrough", "*", 0), ("passthrough", "*", 1),
     ("entries", "*", "field"), ("entries", "*", "type"), ("entries", "*", "pc"), ("entries", "*", "data", "*"),
     ("window", "partitionBy", "*"), ("window", "orderBy", "*")])
_TEXT_NODE_TYPE = {
    "router": (("groups", "*", 0), ("groups", "*", 1)),
    "sql": (("passthrough", "*", 3),),                   # sql passthrough = field tuples (a masking one's [3] is a scale)
    "generic": (("cls",), ("fieldCls",), ("fieldsProp",), ("adv", "*", "*"), ("groupCls", "*"), ("groupProps", "*", "*"),
                ("in", "*"), ("out", "*"), ("groups", "*", 0), ("objs", "*", "*", 0)),
}
# Raw IMF properties (the "set" escape hatch of any node; a generic node's "props", "objs" and field "extra") follow the
# IMF's own types: the 78 UI-authored mappings hold no JSON boolean at all (52,049 "true" / "false" strings) and JSON
# numbers only under these keys. There a whole-value number stays a number under these keys, anything else is text.
_IMF_NUMBER_KEYS = frozenset(("precision", "scale", "commandType", "rowLimit", "batchSize", "maxRowsPerRequest",
                              "pkChunkingSize", "startOffset", "endOffset", "firstDataRow", "headerLineNo",
                              "headerAndDataDelimiter", "rowDelimiter", "occurs", "level", "occurrence"))


def _match(path, pat):
    return len(path) == len(pat) and all(p == "*" or (p == x and type(p) is type(x)) for p, x in zip(pat, path))


def _imf_property(nd, t, rel):
    """The IMF property that a raw escape-hatch value at ``rel`` (a path inside node ``nd``) sets -- the innermost
    property name for a value nested in a raw IMF object -- or None when ``rel`` is not in a raw IMF property."""
    sub = None
    st = nd.get("set")
    if rel[0] == "set" and len(rel) >= 2:
        if isinstance(st, dict):
            sub = rel[1:]                                # "set": {prop: value}
        elif isinstance(st, list) and len(rel) >= 3 and rel[2] == 1 and isinstance(rel[1], int) and rel[1] < len(st):
            pair = st[rel[1]]                            # "set": [[prop, value], ...]
            if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], str):
                sub = (pair[0],) + rel[3:]
    elif t == "generic":
        if rel[0] == "props" and len(rel) >= 2:
            sub = rel[1:]                                # "props": {prop: value}
        elif rel[0] == "objs" and len(rel) >= 5 and rel[3] == 1:
            sub = rel[4:]                                # "objs": {prop: [["<class>", {prop: value}], ...]}
        elif rel[0] == "fields" and len(rel) >= 4 and rel[2] == "extra":
            sub = rel[3:]                                # "fields": [{..., "extra": {prop: value}}]
    names = [k for k in sub or () if isinstance(k, str)]
    return names[-1] if names else None


def _text_slot(spec, path, value=None):
    """Should the whole-value number or true / false ``value`` at ``path`` (a tuple of keys / list indexes) of
    ``spec`` be text?"""
    if len(path) >= 3 and path[0] == "nodes" and isinstance(path[1], int):
        nodes = spec.get("nodes")
        nd = nodes[path[1]] if isinstance(nodes, list) and 0 <= path[1] < len(nodes) else None
        nd = nd if isinstance(nd, dict) else {}
        t = nd.get("type")
        t = t.value if isinstance(t, _Typed) else t
        t = t if isinstance(t, str) else None
        rel = path[2:]
        prop = _imf_property(nd, t, rel)
        if prop is not None:
            return isinstance(value, bool) or prop not in _IMF_NUMBER_KEYS
        return any(_match(rel, p) for p in _TEXT_NODE + _TEXT_NODE_TYPE.get(t, ()))
    return any(_match(path, p) for p in _TEXT_SPEC)


def _finish(o, text_slot=None, path=()):
    """o with every _Typed replaced: text (JSON spelling) where text_slot(path, value) is true, else the JSON value."""
    if isinstance(o, _Typed):
        return json.dumps(o.value) if text_slot is not None and text_slot(path, o.value) else o.value
    if isinstance(o, list):
        return [_finish(x, text_slot, path + (i,)) for i, x in enumerate(o)]
    if isinstance(o, dict):
        return {k: _finish(v, text_slot, path + (k,)) for k, v in o.items()}
    return o


class _Subst:
    """${NAME} substitution over a JSON-like object, with vars resolved transitively (see the module docstring).
    A whole-value number or true / false comes out as a _Typed (see _finish)."""

    def __init__(self, vars_, origin=None):
        self.raw = vars_
        self.origin = origin or {}               # name -> where it is defined (messages)
        self.memo, self.stack = {}, []
        self.undefined = {}                      # name -> [paths where it is used]
        self.problems = []                       # every other problem
        self.typed = False                       # a _Typed was made: the result needs _finish()
        self._cycles = set()

    def value(self, name, path):
        """(True, the var's fully substituted value) or (False, None) when it is undefined or cyclic (recorded)."""
        if name not in self.raw:
            where = self.undefined.setdefault(name, [])
            if path not in where:
                where.append(path)
            return False, None
        if name in self.memo:
            return True, self.memo[name]
        if name in self.stack:
            cyc = self.stack[self.stack.index(name):] + [name]
            if frozenset(cyc) not in self._cycles:
                self._cycles.add(frozenset(cyc))
                self.problems.append("variable cycle %s: a var's value cannot use the var itself"
                                     % " -> ".join("${%s}" % c for c in cyc))
            return False, None
        self.stack.append(name)
        try:
            v = self.walk(self.raw[name], "%s.%s" % (self.origin.get(name, "vars"), name))
        finally:
            self.stack.pop()
        self.memo[name] = v
        return True, v

    def text(self, s, path, key=False):
        if "$" not in s:
            return s
        pieces, probs = _parse(s)
        if probs:
            self.problems += ["%s: %s" % (path or "(top level)", p) for p in probs]
            return s
        refs = [p for p in pieces if isinstance(p, tuple)]
        if not refs:
            return "".join(pieces)
        if len(pieces) == 1 and not key:         # exactly "${NAME}": the var's value, JSON type kept
            ok, v = self.value(refs[0][1], path)
            if not ok:
                return s
            if isinstance(v, (bool, int, float)):   # text or not depends on where it lands: _finish decides
                self.typed = True
                return _Typed(v)
            if v is not None and not isinstance(v, (str, list, tuple, dict, _Typed)):
                return str(v)                    # a Python caller's date, Decimal...: no JSON type to keep, so its
                                                 # text, as inside a longer string (the packager cannot write it)
            return copy.deepcopy(v)              # a string, null, a list / object (a _Typed inside stays one), a _Typed
        out = []
        for p in pieces:
            if not isinstance(p, tuple):
                out.append(p)
                continue
            ok, v = self.value(p[1], path)
            if isinstance(v, _Typed):
                v = v.value
            if not ok:
                out.append("${%s}" % p[1])
            elif isinstance(v, str):
                out.append(v)
            elif isinstance(v, (list, tuple, dict)):
                self.problems.append("%s: ${%s} is %s; a list or object can only be a whole value (\"${%s}\" alone), "
                                     "not part of the text %s" % (path or "(top level)", p[1],
                                                                 "an object" if isinstance(v, dict) else "a list", p[1], _brief(s)))
                out.append("${%s}" % p[1])
            elif v is None or isinstance(v, (bool, int, float)):
                out.append(json.dumps(v))        # true / false / null / 5 / 1.5
            else:
                out.append(str(v))
        return "".join(out)

    def key(self, k, path):
        return self.text(k, "%s (key %s)" % (path or "(top level)", _brief(k)), key=True) if isinstance(k, str) else k

    def walk(self, o, path=""):
        if isinstance(o, str):
            return self.text(o, path)
        if isinstance(o, (list, tuple)):
            return [self.walk(x, "%s[%d]" % (path, i)) for i, x in enumerate(o)]
        if isinstance(o, dict):
            return self._dict(o, path)
        return copy.deepcopy(o)

    def walk_spec(self, spec):
        """walk() of a whole spec, except that its "vars" becomes the effective value of every var it declares and
        its "profile" stays as written (a profile, inline or a file, is read as it is and merged: only the values the
        merge keeps are substituted)."""
        return self._dict(spec, "", top=True)

    def _dict(self, o, path, top=False):
        out, src = {}, {}
        for k, v in o.items():
            nk = self.key(k, path)
            if nk in out:
                self.problems.append("%s: keys %s and %s are both %s after ${...} substitution"
                                     % (path or "(top level)", _brief(src[nk]), _brief(k), _brief(nk)))
                continue
            src[nk] = k
            if top and k == "vars" and isinstance(v, dict):
                out[nk] = {n: copy.deepcopy(self.value(n, "vars")[1]) for n in v}
            elif top and k == "profile":
                out[nk] = copy.deepcopy(v)
            else:
                out[nk] = self.walk(v, "%s.%s" % (path, k) if path else str(k))
        return out

    def messages(self, where="spec"):
        msgs = []
        if self.undefined:
            def at(paths):
                return ", ".join(p or "(top level)" for p in paths[:3]) + (" and %d more" % (len(paths) - 3) if len(paths) > 3 else "")
            msgs.append("%s uses undefined ${...} variable(s): %s (defined: %s)"
                        % (where, "; ".join("%s at %s" % (n, at(self.undefined[n])) for n in sorted(self.undefined)),
                           ", ".join(sorted(map(str, self.raw))) or "none"))
        return msgs + self.problems


def substitute(obj, vars_, where="spec"):
    """Replace ${NAME} in every string and dict key of obj (recursively; see the module docstring). Returns a new
    object; raises SpecError listing every undefined name and malformed placeholder."""
    if vars_ is None:
        vars_ = {}
    if not isinstance(vars_, dict):
        raise SpecError("vars must be a dict {NAME: value}, got %s" % _brief(vars_))
    eng = _Subst(vars_)
    out = eng.walk(obj)
    msgs = eng.messages(where)
    if msgs:
        raise SpecError(msgs)
    return _finish(out) if eng.typed else out       # no text slots here: every whole value keeps its JSON type


# ---------------------------------------------------------------- merge + load
def _copy(value, path):
    return copy.deepcopy(value)


def _over(theirs, mine, sub, path):
    """{**theirs, **mine} (a profile entry overridden key by key by the spec's own), in that key order; only the
    profile keys and values that are kept go through ``sub``."""
    out = {}
    for k, v in theirs.items():
        if k in mine:
            out[k] = None                                # keeps the profile's key order; the spec's value is set below
        else:
            out.update(sub({k: v}, path))
    out.update(mine)
    return out


def merge_profile(spec, prof, sub=None):
    """Spec + profile -> spec (spec wins). See the module docstring for the rules. Parts of the wrong type are left
    as they are, for validate() to report. ``sub(value, path)`` is applied to every value taken from the profile
    (load_spec passes its ${VAR} substitution; the default copies)."""
    sub = sub or _copy
    s = copy.deepcopy(spec)
    if not isinstance(s, dict) or not isinstance(prof, dict):
        return s
    org = prof.get("org") if isinstance(prof.get("org"), dict) else {}
    if "orgGuid" not in s and org.get("guid"):
        s["orgGuid"] = sub(org["guid"], "orgGuid")
    if "orgName" not in s and org.get("name"):
        s["orgName"] = sub(org["name"], "orgName")
    if "runtimeEnvironment" not in s and isinstance(prof.get("runtimeEnvironment"), dict) and prof["runtimeEnvironment"]:
        s["runtimeEnvironment"] = sub(prof["runtimeEnvironment"], "runtimeEnvironment")
    pf, sf = prof.get("folder"), s.get("folder")
    if pf and isinstance(pf, dict) and (sf is None or isinstance(sf, dict)):
        s["folder"] = _over(pf, sf or {}, sub, "folder")
    sc = s.get("connections")
    if sc is not None and not isinstance(sc, dict):
        return s
    sc = sc or {}
    pc = prof.get("connections") if isinstance(prof.get("connections"), dict) else {}
    used = []
    for nd in s.get("nodes") if isinstance(s.get("nodes"), list) else []:
        a = nd.get("conn") if isinstance(nd, dict) else None
        if isinstance(a, str) and a and a not in used:
            used.append(a)
    conns = {}
    for a in list(sc) + [a for a in used if a not in sc]:
        mine, theirs = sc.get(a), pc.get(a)
        if a in sc and not isinstance(mine, dict):
            conns[a] = mine                              # malformed: validate() reports it
        elif a in sc or a in pc:
            conns[a] = _over(theirs if isinstance(theirs, dict) else {}, mine or {}, sub, "connections.%s" % a)
    s["connections"] = conns
    return s


def read_spec(path_or_dict, base_dir=None):
    """-> (spec object, the folder its "profile" key is relative to). A path is read as UTF-8 (BOM allowed) and gives
    its own folder; anything else is deep-copied and keeps ``base_dir`` (None = the cwd). SpecError: unreadable file."""
    if _is_path(path_or_dict):
        p = os.path.abspath(os.fsdecode(os.fspath(path_or_dict)))
        return _read_json(p, "spec"), os.path.dirname(p)
    return copy.deepcopy(path_or_dict), base_dir


class Prepared:
    """A spec as load_spec sees it before validate(): merged with its profile, ${VARS} substituted, problems listed.

    spec, profile (the dict in effect, {} = none), profile_path (None for a dict), profile_problems (the profile's
    and the vars argument's types), shape_problems (the spec's types: see shape_problems), undefined ({var: [paths]}),
    var_problems (every other substitution problem)."""

    def __init__(self, spec, profile, profile_path, profile_problems_, shape, eng):
        self.spec, self.profile, self.profile_path = spec, profile, profile_path
        self.profile_problems, self.shape_problems = profile_problems_, shape
        self.undefined, self.var_problems = eng.undefined, eng.problems
        self._var_messages = eng.messages("spec")

    def problems(self):
        return _dedupe(self.profile_problems + self._var_messages + self.shape_problems)


def prepare(path_or_dict, profile=None, vars=None, default_profile=None, base_dir=None):
    """Read a spec, pick its profile, merge, substitute -> Prepared. Every spec problem is collected, not raised;
    SpecError only when the spec or the profile cannot be read (missing, not JSON, not an object).
    ``base_dir``: for a dict spec, the folder its "profile" key is relative to (default: its "baseDir", else the cwd).
    The spec file's folder (a path's own folder, else ``base_dir``) becomes the loaded spec's "baseDir" unless the spec
    sets an absolute one: a relative "baseDir" is resolved against that folder, an empty or null one is that folder,
    and a leading '~' is the home folder (os.path.expanduser), as for the "profile" key."""
    raw, base_dir = read_spec(path_or_dict, base_dir)
    if not isinstance(raw, dict):
        raise SpecError("a spec must be a JSON object, got %s" % _brief(raw))
    spec_dir = base_dir                 # the spec file's folder (None: a dict spec, no folder known)
    if base_dir is None and isinstance(raw.get("baseDir"), str) and raw["baseDir"]:
        base_dir = raw["baseDir"]       # a dict that records its folder: its "profile" key is relative to it (a loaded
                                        # spec has one too, but load a spec once: its $${ escapes are consumed)
    prof, prof_path = resolve_profile(raw, profile, base_dir, default_profile)
    pprobs = profile_problems(prof, prof_path)
    vv, origin = {}, {}
    for label, d in (("profile vars", prof.get("vars")), ("vars", raw.get("vars")), ("vars argument", vars)):
        if isinstance(d, dict):
            vv.update(d)
            origin.update(dict.fromkeys(d, label))
            if label == "vars argument":
                pprobs += _var_name_problems(d, "the vars argument")
        elif d is not None and label == "vars argument":
            pprobs.append("the vars argument must be a dict {NAME: value}, got %s" % _brief(d))
    eng = _Subst(vv, origin)
    out = eng.walk_spec(raw)            # first the spec's own text, so the merge sees the aliases it really uses
    for step in (0, 1):
        if eng.typed:                   # whole-value numbers / booleans: text in text slots (before and after the merge)
            out = _finish(out, lambda path, value, _s=out: _text_slot(_s, path, value))
        if prof and step == 0:
            out = merge_profile(out, prof, eng.walk)     # the profile values it keeps are substituted on the way in
    if spec_dir:                         # the spec's folder: package.py resolves relative projectJson / folderJson files here
        own = out.get("baseDir")
        if own is None or own == "":     # no "baseDir" key, or an empty or null one: the spec file's folder
            out["baseDir"] = spec_dir
        elif isinstance(own, str):       # as the "profile" key is read: '~' is the home folder, then relative to the
            exp = os.path.expanduser(own)    # spec file (an absolute baseDir is kept as written)
            if exp != own or not os.path.isabs(own):
                out["baseDir"] = os.path.abspath(os.path.join(spec_dir, exp))
    return Prepared(out, prof, prof_path, pprobs, shape_problems(out), eng)


def load_spec_and_profile(path_or_dict, profile=None, vars=None, default_profile=None):
    """load_spec() plus the profile it used -> (spec, profile dict). deploy builds its client from that profile."""
    p = prepare(path_or_dict, profile, vars, default_profile)
    problems = p.problems()
    try:
        validate(p.spec, for_package=True)
    except SpecError as e:
        problems += e.problems
    problems = _dedupe(problems)
    if problems:
        raise SpecError(problems)
    return p.spec, p.profile


def load_spec(path_or_dict, profile=None, vars=None, default_profile=None):
    """Load, merge and validate a spec for packaging. ``profile`` (path or non-empty dict) overrides the spec's own
    "profile" key; ``default_profile`` is used when neither names one. Raises SpecError listing every problem."""
    return load_spec_and_profile(path_or_dict, profile, vars, default_profile)[0]


# ---------------------------------------------------------------- validation
def _link_ok(lk):
    return isinstance(lk, list) and len(lk) in (2, 3) and all(isinstance(x, str) for x in lk[:2])


def _flow_entry_ok(e):
    return (isinstance(e, (list, tuple)) and len(e) == 2 and
            all(isinstance(side, (list, tuple)) and side and all(isinstance(x, str) and x for x in side) for side in e))


def _selection_problems(i, sel):
    """Problems inside one link's field selection (a list, a rename map or {"exclude": [...]})."""
    w = "links[%d]" % i

    def field(x):
        return isinstance(x, str) and x != ""
    if isinstance(sel, list):
        return ["%s: field selection item %s must be a field name (a non-empty string)" % (w, _brief(x)) for x in sel if not field(x)]
    if set(sel) == {"exclude"}:
        ex = sel["exclude"]
        if not isinstance(ex, (list, tuple)):
            return ['%s: {"exclude": %s}: the excluded fields must be a list, e.g. {"exclude": [%s]} (a one-entry rename '
                    'of a field called "exclude" would be ambiguous)' % (w, _brief(ex), _brief(ex))]
        return ["%s: excluded field %s must be a field name (a non-empty string)" % (w, _brief(x)) for x in ex if not field(x)]
    errs = []
    for k, v in sel.items():
        if not field(k):
            errs.append("%s: rename map key %s must be a field name (a non-empty string)" % (w, _brief(k)))
        if not isinstance(v, str):
            errs.append('%s: rename map %s -> %s: the new name must be a string ("" keeps the name)%s'
                        % (w, _brief(k), _brief(v), ' (an exclude rule is {"exclude": [...]} alone; it cannot be mixed with '
                                                    'renames)' if k == "exclude" else ""))
    return errs


_STR_KEYS = ("description", "orgGuid", "orgName", "guid", "taskName", "documentType", "baseDir")
DOCUMENT_TYPES = ("MAPPING", "DMAPPLET")     # "documentType": absent / null / "MAPPING" = a mapping, "DMAPPLET" = a mapplet
_OBJ_KEYS = (("folder", "{project, projectGuid, name, guid}"), ("vars", "{NAME: value}"), ("runtimeEnvironment", "{id, name}"),
             ("packageOverrides", "{key: value}"))


def shape_problems(spec):
    """Values of the wrong type (what would crash the merge, the compiler, the packager or lint) -> [message].
    validate() reports these plus the content problems; lint stops at these. Never raises."""
    if not isinstance(spec, dict):
        return ["a spec must be a JSON object, got %s" % _brief(spec)]
    errs = []
    if spec.get("name") is not None and not isinstance(spec["name"], str):
        errs.append(_NAME_MSG)
    for k in _STR_KEYS:
        if spec.get(k) is not None and not isinstance(spec[k], str):
            errs.append("'%s' must be a string, got %s" % (k, _brief(spec[k])))
    for k, shape in _OBJ_KEYS:
        if spec.get(k) is not None and not isinstance(spec[k], dict):
            errs.append("'%s' must be an object %s, got %s" % (k, shape, _brief(spec[k])))
    if isinstance(spec.get("folder"), dict):
        errs += ["folder.%s must be a string, got %s" % (k, _brief(spec["folder"][k]))
                 for k in _FOLDER_KEYS if spec["folder"].get(k) is not None and not isinstance(spec["folder"][k], str)]
    if isinstance(spec.get("vars"), dict):
        errs += _var_name_problems(spec["vars"], "vars")
    pr = spec.get("profile")
    if pr is not None and not isinstance(pr, (str, dict, os.PathLike)):
        errs.append("'profile' must be a profile path or an object, got %s" % _brief(pr))
    conns = spec.get("connections")
    if conns is not None and not isinstance(conns, dict):
        errs.append(_CONNS_MSG)
    elif isinstance(conns, dict):
        for a, c in conns.items():
            errs += _conn_problems(a, c)
    if "assets" in spec:
        assets = spec["assets"]
        if not isinstance(assets, list):
            errs.append("'assets' must be a list of {guid, name, type, path}, got %s" % _brief(assets))
        else:
            for i, a in enumerate(assets):
                if not isinstance(a, dict):
                    errs.append("assets[%d] must be an object {guid, name, type, path}, got %s" % (i, _brief(a)))
                    continue
                errs += ["assets[%d].%s must be a string, got %s" % (i, k, _brief(a[k]))
                         for k in _ASSET_KEYS if a.get(k) is not None and not isinstance(a[k], str)]
    nodes = spec.get("nodes")
    if nodes is not None and not isinstance(nodes, list):
        errs.append(_NODES_MSG)
    for i, nd in enumerate(nodes if isinstance(nodes, list) else []):
        if not isinstance(nd, dict):
            errs.append("nodes[%d] must be an object" % i)
            continue
        label = nd["name"] if isinstance(nd.get("name"), str) else "?"
        for k, what in (("type", "the node type"), ("name", "the node name"), ("conn", "a connection alias")):
            if nd.get(k) is not None and not isinstance(nd[k], str):
                errs.append("nodes[%d] (%s): '%s' must be a string (%s), got %s" % (i, label, k, what, _brief(nd[k])))
    if "links" not in spec:
        errs.append("'links' is missing: a list of [from, to] or [from, to, fields] ([] when there are none)")
    elif not isinstance(spec["links"], list):
        errs.append(_LINKS_MSG)
    else:
        for i, lk in enumerate(spec["links"]):
            if not (_link_ok(lk) and len(lk) == 3 and lk[2]):
                continue
            if isinstance(lk[2], (list, dict)):
                errs += _selection_problems(i, lk[2])
            else:                       # here, not only in validate(): lint's rules crash on a non-iterable selection
                errs.append(_SELECTION_MSG % i)
    fo = spec.get("flowOrder")
    if fo is not None:
        if not isinstance(fo, (list, tuple)):
            errs.append("'flowOrder' must be a list of [[source names], [target names]] entries, got %s" % _brief(fo))
        else:
            errs += ["flowOrder[%d] must be [[source names], [target names]] (two non-empty lists of node names), got %s"
                     % (i, _brief(e)) for i, e in enumerate(fo) if not _flow_entry_ok(e)]
    return errs


def validate(spec, for_package=False):
    """Structural checks: types, the documentType (DOCUMENT_TYPES), node names, aliases, links, flowOrder.
    for_package=True also requires the identity keys a package needs, and adds what the packager would refuse without
    reading a file (package.static_problems: the project / folder / mapping name rules, one guid = one object, the
    projectJson / folderJson shapes and the baseDir rule), so load_spec and lint refuse it before any package is
    written. Raises SpecError listing every problem -- never another exception, whatever the input."""
    errs = shape_problems(spec)
    if not isinstance(spec, dict):
        raise SpecError(errs)
    if not isinstance(spec.get("name"), str) or not spec.get("name"):
        errs.append(_NAME_MSG)
    dt = spec.get("documentType")
    if isinstance(dt, str) and dt not in DOCUMENT_TYPES:     # (any other value was built and packaged as a mapping)
        errs.append("'documentType' %s is not one this generator builds: leave it out (or \"MAPPING\") for a mapping, "
                    "\"DMAPPLET\" for a mapplet (IDMC rejects \"MAPPLET\")" % _brief(dt))
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errs.append(_NODES_MSG)
        nodes = nodes if isinstance(nodes, list) else []
    links = spec["links"] if isinstance(spec.get("links"), list) else []
    conns = spec.get("connections")
    if not isinstance(conns, dict):
        errs.append(_CONNS_MSG)
        conns = {}
    names, types = {}, {}
    for i, nd in enumerate(nodes):
        if not isinstance(nd, dict):
            continue                                     # shape_problems: nodes[i] must be an object
        if not nd.get("type"):
            errs.append("nodes[%d] (%s) has no 'type'" % (i, nd.get("name", "?")))
        n = nd.get("name")
        if n is None or n == "":
            errs.append("nodes[%d] has no 'name'" % i)
            continue
        if not isinstance(n, str):
            continue                                     # shape_problems
        if "." in n:
            errs.append("node name %r must not contain '.' (it separates the group in link keys)" % n)
        if n in names:
            errs.append("node name %r is used twice (nodes[%d] and nodes[%d])" % (n, names[n], i))
        names[n], types[n] = i, nd.get("type")
        c = nd.get("conn")
        if isinstance(c, str) and c not in conns:
            errs.append("node %r uses connection alias %r, not defined in 'connections' (have: %s)"
                        % (n, c, ", ".join(sorted(map(str, conns))) or "none"))
    named = isinstance(spec.get("nodes"), list)          # else every name check below would only echo that problem
    for i, lk in enumerate(links):
        if not _link_ok(lk):
            errs.append("links[%d] must be [from, to] or [from, to, fields]; got %r" % (i, lk))
            continue
        for end in lk[:2] if named else ():
            if end.split(".")[0] not in names:
                errs.append("links[%d] %r -> %r: node %r does not exist" % (i, lk[0], lk[1], end.split(".")[0]))
    fo = spec.get("flowOrder")
    for i, e in enumerate(fo if isinstance(fo, (list, tuple)) and named else []):
        if not _flow_entry_ok(e):
            continue                                     # shape_problems
        for side, want in ((e[0], "source"), (e[1], "target")):
            for x in side:
                if x not in names:
                    errs.append("flowOrder[%d]: %s %r is not a node" % (i, want, x))
                elif types.get(x) != want:
                    errs.append("flowOrder[%d]: %r is not a %s node (its type is %r)" % (i, x, want, types.get(x)))
    if for_package:
        if spec.get("orgGuid") is None or spec.get("orgGuid") == "":
            errs.append("'orgGuid' is missing (set it in the spec or the profile's org.guid)")
        f = spec.get("folder")
        if f is None:
            errs.append("'folder' {project, projectGuid, name, guid} is missing (spec or profile)")
        elif isinstance(f, dict):
            errs += ["folder.%s is missing" % k for k in _FOLDER_KEYS if f.get(k) is None or f.get(k) == ""]
        for a, c in conns.items():
            if isinstance(c, dict):
                errs += ["connection %r has no %r" % (a, k) for k in ("guid", "name", "repoHandle") if c.get(k) is None or c.get(k) == ""]
        assets = spec.get("assets")
        for a in assets if isinstance(assets, list) else []:
            if isinstance(a, dict):
                for k in _ASSET_KEYS:
                    if a.get(k) is None or a.get(k) == "":
                        errs.append("assets entry %r needs %s" % (a, k))
                        break
        from . import package as _package     # here, not at the top: package.py imports this module
        errs += _package.static_problems(spec)
    if errs:
        raise SpecError(_dedupe(errs))
    return spec
