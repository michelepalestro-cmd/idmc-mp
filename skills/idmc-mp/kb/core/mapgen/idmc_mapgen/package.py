"""Package IMF JSON as an IDMC import package (a from-scratch "export" zip of one DTEMPLATE mapping or DMAPPLET mapplet).

Outer zip:  Explore/<project>/<folder>/<name>.DTEMPLATE.zip, exportMetadata.v2.json, exportPackage.chksum
Inner zip:  mappingTemplate.json, fileRecord.json, bin/@2.bin (the IMF JSON), metadata.meta
A spec with "documentType": "DMAPPLET" is a mapplet: package() and package_bytes() hand it to
nodes.mapplet.mapplet_package_bytes (<name>.DMAPPLET.zip holding mappletTemplate.json), so mapgen.py build,
compile_file and python -m idmc_mapgen.compile write the package deploy imports. package_files() builds the
DTEMPLATE layout only and refuses a DMAPPLET spec.
exportPackage.chksum: a java.util.Properties file, one "<path>=<SHA256 upper hex>" line per file, each path
escaped as Properties.store writes a key (see checksum_key: "\\ " for a space, "\\:" "\\=" "\\#" "\\!", "\\uXXXX"
for non-ASCII). IDMC reads it back with Properties.load; a key it cannot match to its zip entry fails the upload
with 400 MigrationSvc_073 "Import package has been modified" (proven live for ':', '=' and 'e-acute' in a mapping
name and for ':' and 'e-acute' in a DMAPPLET name; with these escapes the same packages upload checksumValid).
Project, folder and mapping names are non-empty strings without '/', '\\', a control character or a lone
surrogate, and a project or folder is never '.' or '..' (each would move or break the package path).
A connection guid or an asset guid is ONE package dependency, however many aliases or entries name it.
projectJson / folderJson ([package path, local file]): the package path is a plain relative zip path ('\\' is
written as '/'); a relative local file resolves against spec["baseDir"], which must then be an absolute folder
(load_spec(path) records the spec file's folder and resolves the file's own relative, empty or null baseDir
against it; in a dict spec a null, empty or relative baseDir is an error), or against the current directory when
the spec has no "baseDir" key.
The name, dependency and projectJson / folderJson checks raise SpecError before spec["guid"] is written, and
static_problems() runs the ones that need no file for spec.validate(spec, for_package=True): load_spec, lint and
deploy's lint gate refuse what the packager refuses. So does a pinned now_ms outside 1980-2107 local time (the
years a ZIP entry date can hold). The DMAPPLET packager uses the same name checks, per-guid connection
dependencies, package time check (_package_time) and checksum_text.
safe_file_name(name): the local file name the CLIs use for <name>.pkg.zip / <name>.imf.json (Windows-safe).

    from idmc_mapgen.package import package, package_bytes
    package(spec, imf, "m_x.pkg.zip")          # sets spec["guid"] if it has none
    data = package_bytes(spec, imf, now_ms=1790000000000)   # deterministic bytes (tests, reproducible builds)
"""
import hashlib
import io
import json
import os
import random
import string
import time
import unicodedata
import zipfile

from .imf import imf_bytes
from .spec import SpecError

_CTRL_ESC = {"\t": "\\t", "\n": "\\n", "\r": "\\r", "\f": "\\f"}


def checksum_key(path):
    r"""``path`` written as java.util.Properties.store writes a key (saveConvert, escapeSpace and escapeUnicode on).

    backslash -> \\, space -> "\ ", tab/LF/CR/FF -> \t \n \r \f, = : # ! get a backslash, and every other
    character outside U+0020..U+007E becomes \uXXXX (upper-case hex, one per UTF-16 unit). The result is pure
    ASCII; an ASCII path without \ = : # ! only gets "\ " for its spaces, exactly as before.
    """
    out = []
    for ch in path:
        o = ord(ch)
        if 61 < o < 127:
            out.append("\\\\" if ch == "\\" else ch)
        elif ch == " ":
            out.append("\\ ")
        elif ch in _CTRL_ESC:
            out.append(_CTRL_ESC[ch])
        elif ch in "=:#!":
            out.append("\\" + ch)
        elif o < 0x20 or o > 0x7E:
            u = ch.encode("utf-16-be", "surrogatepass")
            out.append("".join("\\u%04X" % int.from_bytes(u[i:i + 2], "big") for i in range(0, len(u), 2)))
        else:
            out.append(ch)
    return "".join(out)


def _unwritable(s):
    """The characters of ``s`` no zip entry name can hold: control characters (they break the entry; zipfile cuts
    a name at NUL) and lone surrogates (not text: UTF-8 cannot encode them, so zipfile cannot write the name)."""
    return sorted({c for c in s if unicodedata.category(c) in ("Cc", "Cs")})


_FILE_NAME_BAD = frozenset('<>:"/\\|?*')
_DOS_DEVICES = frozenset(["CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"] +
                         [d + c for d in ("COM", "LPT") for c in "0123456789¹²³"])


def safe_file_name(name):
    """``name`` (a mapping or mapplet name) as a local file name that is safe on Windows, for the files the CLIs name
    after the mapping (<name>.pkg.zip, <name>.imf.json, deploy's run records). Each of < > : " / \\ | ? *, every
    control character and a lone surrogate becomes '_' (with a ':' NTFS writes 'm_a:b.pkg.zip' into the alternate
    data stream 'b.pkg.zip' of a 0-byte file 'm_a'; the others fail with OSError), and a DOS device name (CON, NUL,
    COM1 ..., also before a '.') gets a leading '_'. The same on every OS, so a build names its files alike
    everywhere; the package itself keeps the real name."""
    s = "".join("_" if c in _FILE_NAME_BAD or unicodedata.category(c) in ("Cc", "Cs") else c for c in str(name))
    if s.partition(".")[0].rstrip(" ").upper() in _DOS_DEVICES:
        s = "_" + s
    return s or "_"


def _name_problem(what, v):
    """The problem with ``v``, a non-empty project, folder or mapping name (``what``), or None."""
    bad = sorted(set(_unwritable(v)) | {c for c in v if c in "/\\"})
    if bad:
        return ("%s %r contains %s: a project, folder or asset name cannot hold '/', '\\', a control character "
                "or a lone surrogate (IDMC does not allow them, and the package path would break)"
                % (what, v, ", ".join(repr(c) for c in bad)))
    if what != "name" and v in (".", ".."):
        return "%s %r is a path step, not a name: the package entry Explore/<project>/<folder>/... would move" % (what, v)
    return None


def _name_problems(spec, given_only=False):
    """Project, folder and mapping names become package paths (Explore/<project>/<folder>/<name>.<TYPE>.zip), so each
    must be a non-empty string without '/' or '\\' (they would move the entry), a control character or a lone
    surrogate; IDMC allows none of them in a project, folder or asset name. A project or folder cannot be '.' or
    '..' either: that is a path step, so the entry would move too. -> [problem]
    ``given_only``: judge only the names that are non-empty strings (validate() reports a missing one itself)."""
    F = spec.get("folder")
    errs, names = [], [("name", spec.get("name"))]
    if isinstance(F, dict):
        names += [("folder.project", F.get("project")), ("folder.name", F.get("name"))]
    elif not given_only:
        errs.append("'folder' must be an object {project, projectGuid, name, guid}, got %r" % (F,))
    for what, v in names:
        if not isinstance(v, str) or not v:
            if not given_only:
                errs.append("%s must be a non-empty string, got %r" % (what, v))
            continue
        p = _name_problem(what, v)
        if p:
            errs.append(p)
    return errs


def _usable(e):
    return isinstance(e, dict) and isinstance(e.get("guid"), str) and e.get("guid") != ""


def _unique(entries, keys, what):
    """[(label, entry)] -> (entries, one per guid (first wins); problems). The same guid with a different ``keys``
    value is a problem (one guid is one object), and so is an entry that is not an object with a guid."""
    first, out, errs = {}, [], []
    for label, e in entries:
        if not _usable(e):
            errs.append("%s %s must be an object with a guid (a non-empty string), got %r" % (what, label, e))
            continue
        g = e["guid"]
        if g not in first:
            first[g] = (label, e)
            out.append(e)
            continue
        l0, e0 = first[g]
        frs = len(g) == 22 and g.isascii() and g.isalnum()
        for k in keys:
            if e.get(k) != e0.get(k):
                errs.append("%s %s and %s share guid %s but differ in %s (%r vs %r): one guid is one object%s"
                            % (what, l0, label, g, k, e0.get(k), e.get(k), "" if frs else
                               " (%r is not a 22-character FRS guid: is the profile resolved? "
                               "python mapgen.py resolve --write)" % (g,)))
    return out, errs


def _dependencies(spec, assets=True, given_only=False):
    """(connections, assets, problems): what the package lists as dependencies, one entry per guid, spec order.
    ``assets``: False for a DMAPPLET package (it lists connections only). ``given_only``: skip the entries that are not
    objects with a string guid (validate() reports those itself)."""
    errs = []
    cd = spec.get("connections")
    if cd is None:
        cd = {}
    if not isinstance(cd, dict):
        if not given_only:
            errs.append("'connections' must be an object {alias: {guid, name, repoHandle}}, got %r" % (cd,))
        cd = {}
    al = (spec.get("assets") or []) if assets else []
    if not isinstance(al, (list, tuple)):
        if not given_only:
            errs.append("'assets' must be a list of {guid, name, type, path}, got %r" % (al,))
        al = []
    centries = [("alias %r" % (a,), c) for a, c in cd.items()]
    aentries = [("entry %r" % (a.get("name") if isinstance(a, dict) else a,), a) for a in al]
    if given_only:
        centries = [x for x in centries if _usable(x[1])]
        aentries = [x for x in aentries if _usable(x[1])]
    conns, e1 = _unique(centries, ("name", "repoHandle"), "connection")
    alist, e2 = _unique(aentries, ("name", "type", "path"), "asset")
    errs += e1 + e2
    both = {c["guid"] for c in conns} & {a["guid"] for a in alist}
    if both:
        errs.append("guid %s is both a connection and an asset: one guid is one object" % ", ".join(sorted(both)))
    return conns, alist, errs


def _generated_entries(spec):
    """The entries a DTEMPLATE package writes itself (projectJson / folderJson cannot replace them)."""
    F = spec.get("folder")
    if not isinstance(F, dict):
        return ("exportMetadata.v2.json",)
    return ("Explore/%s/%s/%s.DTEMPLATE.zip" % (F.get("project"), F.get("name"), spec.get("name")), "exportMetadata.v2.json")


def _cwd():
    """The current directory, for a message. Never raises: on POSIX os.getcwd() fails once the current directory has
    been deleted, and validate() (which runs _extra_plan) must raise nothing but SpecError."""
    try:
        return os.getcwd()
    except OSError as e:
        return "<unreadable: %s>" % (e.strerror or e)


def _extra_plan(spec, taken, given_only=False):
    """The projectJson / folderJson = [package path, local file] entries, judged without reading a file ->
    (problems, [(key, package path, local file, path to read, where it was resolved)]).

    The package path is a plain relative zip path ('\\' is written as '/'). The local file is a str or an os.PathLike.
    A relative local file resolves against spec["baseDir"], which must then be an absolute folder (load_spec(path)
    records the spec file's folder; a null, empty or relative baseDir would silently mean the current directory, so it
    is an error), else, when the spec has no "baseDir" key at all, against the current directory.
    ``given_only``: no problem for a baseDir that is not a string (validate() reports it itself)."""
    wanted = [k for k in ("projectJson", "folderJson") if spec.get(k)]
    if not wanted:
        return [], []
    has_base = "baseDir" in spec    # even as null: in a dict spec null cannot mean "the current directory" either
    base = spec.get("baseDir")
    if isinstance(base, os.PathLike):
        base = os.fspath(base)
    if base is not None and not isinstance(base, str):
        return ([] if given_only else ["'baseDir' must be a folder path (a string), got %r" % (base,)]), []
    errs, plan, dests = [], [], set()
    for k in wanted:
        v = spec[k]
        if isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[1], os.PathLike):
            v = (v[0], os.fspath(v[1]))     # a pathlib.Path local file (Python callers): open() always took one
        if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, str) and x for x in v)):
            errs.append("%s must be [package path, local file] (two non-empty strings), got %r" % (k, v))
            continue
        dest, local = v
        dest = dest.replace("\\", "/")   # zip entries use '/' (zipfile rewrites '\\' on Windows only): key == entry
        bad = _unwritable(dest)
        if bad:
            errs.append("%s package path %r contains %s (a control character or a lone surrogate)"
                        % (k, dest, ", ".join(repr(c) for c in bad)))
            continue
        if any(step in ("", ".", "..") for step in dest.split("/")):
            errs.append("%s package path %r must be a relative path inside the package, like 'Explore/<project>.Project.json' "
                        "(no leading '/', and no empty, '.' or '..' step)" % (k, dest))
            continue
        if dest in taken or dest in dests or dest == "exportPackage.chksum":
            errs.append("%s package path %r is already a package entry" % (k, dest))
            continue
        dests.add(dest)
        if has_base and not os.path.isabs(local) and not (base and os.path.isabs(base)):   # a dict spec's null, "" or relative baseDir
            what = "baseDir is null" if base is None else "baseDir %r is %s" % (base, "empty" if not base else "a relative folder")
            errs.append("%s local file %r: %s, so the file would be read from the current directory %s, "
                        "not next to the spec; give baseDir as an absolute folder or leave it out (load_spec(path) sets "
                        "the spec file's folder)" % (k, local, what, _cwd()))
            continue
        p = local if os.path.isabs(local) or base is None else os.path.join(base, local)
        where = "" if os.path.isabs(local) else "; resolved against %s" % (
            "the spec folder (baseDir) %s" % base if base is not None else
            "the current directory %s (the spec has no baseDir)" % _cwd())
        plan.append((k, dest, local, p, where))
    return errs, plan


def _extra_files(spec, taken):
    """({package path: bytes} for projectJson / folderJson, problems): _extra_plan, then each local file read."""
    errs, plan = _extra_plan(spec, taken)
    out = {}
    for k, dest, local, p, where in plan:
        if os.path.isdir(p):
            errs.append("%s local file %r is a folder, not a file%s" % (k, local, where))
            continue
        try:
            with open(p, "rb") as f:
                out[dest] = f.read()
        except (OSError, ValueError) as e:      # ValueError: a NUL in the path (and on POSIX a lone surrogate)
            errs.append("%s local file %r cannot be read (%s)%s" % (k, local, getattr(e, "strerror", None) or e, where))
    return out, errs


def static_problems(spec):
    """What the packager would refuse in ``spec`` that shows without reading a file -> [problem]; never raises.

    The name rules (_name_problems), one guid = one object (_dependencies) and, for a DTEMPLATE, the projectJson /
    folderJson shapes and the baseDir rule (_extra_plan). spec.validate(spec, for_package=True) adds these, so
    load_spec, lint and deploy's lint gate report them; a value that is missing or of the wrong type is left to
    validate()'s own messages. A DMAPPLET package lists no assets and no projectJson / folderJson files (see
    nodes/mapplet.py), so they are not judged for one."""
    if not isinstance(spec, dict):
        return []
    mapplet = spec.get("documentType") == "DMAPPLET"
    errs = _name_problems(spec, given_only=True) + _dependencies(spec, assets=not mapplet, given_only=True)[2]
    if not mapplet:
        errs += _extra_plan(spec, _generated_entries(spec), given_only=True)[0]
    return errs


def new_guid():
    """A fresh 22-character FRS guid (letters and digits)."""
    a = string.ascii_letters + string.digits
    return "".join(random.choice(a) for _ in range(22))


ZIP_YEARS = (1980, 2107)    # the years a ZIP entry date can hold (DOS date: 1980 + a 7-bit year)


def _package_time(now_ms):
    """(package time in epoch ms, zip entry date or None, problems) for ``now_ms`` (None = the current time, and
    zipfile dates the entries). A pinned time dates every zip entry in local time, so it must fall in 1980-2107 local
    time, the years a ZIP entry date can hold (compile_file refuses the same): anything else (0, a negative or a huge
    number, NaN) is a problem here, never zipfile's raw ValueError, an OSError or an OverflowError."""
    if now_ms is None:
        return int(time.time() * 1000), None, []
    try:
        now = int(now_ms)
        dt = time.localtime(now / 1000.0)[:6]
    except (TypeError, ValueError, OverflowError, OSError) as e:
        return None, None, ["now_ms %r is not a usable package time (%s: %s)" % (now_ms, type(e).__name__, e)]
    if not ZIP_YEARS[0] <= dt[0] <= ZIP_YEARS[1]:
        return None, None, ["now_ms %r is %04d-%02d-%02d %02d:%02d:%02d local time: a package can only be pinned to a "
                            "time in %d-%d (local time), the years a ZIP entry date can hold"
                            % ((now_ms,) + tuple(dt) + ZIP_YEARS)]
    return now, dt, []


def _zip_put(z, name, data, date_time):
    """ZipFile.writestr, with a fixed timestamp when date_time is given (same entry attributes as writestr)."""
    if date_time is None:
        z.writestr(name, data)
        return
    zi = zipfile.ZipInfo(name, date_time=date_time)
    zi.external_attr = 0o600 << 16
    z.writestr(zi, data, compress_type=z.compression)


def package_files(spec, imf, now_ms=None):
    """({path: bytes} of the outer DTEMPLATE package without exportPackage.chksum, the package time in epoch ms, the
    zip entry timestamp or None). Every check runs first: one SpecError lists every problem, before spec["guid"] is
    set (a pinned ``now_ms`` outside 1980-2107 local time is one, see _package_time). A DMAPPLET spec is refused:
    package() / package_bytes() package it (nodes.mapplet.mapplet_package_bytes)."""
    if spec.get("documentType") == "DMAPPLET":
        raise SpecError("package_files builds a mapping (DTEMPLATE) package and %r is a DMAPPLET spec: package it with "
                        "package() or package_bytes(), which write the DMAPPLET layout (nodes.mapplet.mapplet_package_bytes)"
                        % (spec.get("name"),))
    errs = _name_problems(spec)
    conns, assets, dep_errs = _dependencies(spec)
    taken = _generated_entries(spec)
    extra, extra_errs = _extra_files(spec, taken)
    now, dt, time_errs = _package_time(now_ms)
    errs += dep_errs + extra_errs + time_errs
    if errs:
        raise SpecError(errs)
    name = spec["name"]; F = spec["folder"]
    dt_path = taken[0]
    g = spec.get("guid") or new_guid(); spec["guid"] = g
    binb = imf_bytes(imf)
    refs = [{"@type": "reference", "refObjectId": "@" + c["guid"], "refType": "connection"} for c in conns]
    refs += [{"@type": "reference", "refObjectId": "@" + a["guid"], "refType": "frsDocument"} for a in assets]
    mt = [{"@type": "mappingTemplate", "id": "@1", "name": name, "description": spec.get("description", ""), "autoExpireObject": False,
           "bundleVersion": "0", "assetFrsGuid": g, "templateId": "@2", "deployTime": now, "hasParameters": False, "valid": True,
           "fixedConnection": True, "hasParametersDeployed": False, "fixedConnectionDeployed": True, "isSchemaValidationEnabled": False,
           "tasks": 0, "documentType": "MAPPING", "allowMaxFieldLength": False, "specialCharacterSupport": False, "references": refs}]
    fr = [{"@type": "fileRecord", "id": "@2", "name": name, "type": "IMFOBJECT", "size": len(binb), "attachTime": now,
           "additionalInfo": "com.informatica.metadata.template.common.Template"}]
    for k, v in (spec.get("packageOverrides") or {}).items():   # e.g. {"hasParameters": true} for parameterized mappings
        mt[0][k] = v
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED) as z:
        _zip_put(z, "mappingTemplate.json", json.dumps(mt, separators=(",", ":")), dt)
        _zip_put(z, "fileRecord.json", json.dumps(fr, separators=(",", ":")), dt)
        _zip_put(z, "bin/@2.bin", binb, dt)
        _zip_put(z, "metadata.meta", json.dumps([{"@type": "objectRef", "id": "@1", "type": "mappingTemplate"}]), dt)
    innerb = inner.getvalue()
    mv = {"major": 0, "minor": 0}
    eo = [{"objectGuid": g, "objectName": name, "objectType": "DTEMPLATE", "path": "/Explore/%s/%s" % (F["project"], F["name"]), "providerName": None,
           "metadata": {"modelVersion": mv, "repoInfo": None,
                        "objectRefs": [a["guid"] for a in assets] + [c["guid"] for c in conns],
                        "contextAttributes": [{"name": "id", "value": "@1"}],
                        "additionalInfo": {"description": spec.get("description", ""), "contentType": "JSON", "documentState": "VALID"}}},
          {"objectGuid": F["projectGuid"], "objectName": F["project"], "objectType": "Project", "path": "/Explore", "providerName": None,
           "metadata": {"modelVersion": mv, "repoInfo": None, "objectRefs": [], "contextAttributes": [],
                        "additionalInfo": {"description": "", "contentType": "Binary", "documentState": "COMPLETE"}}},
          {"objectGuid": F["guid"], "objectName": F["name"], "objectType": "Folder", "path": "/Explore/" + F["project"], "providerName": None,
           "metadata": {"modelVersion": mv, "repoInfo": None, "objectRefs": [], "contextAttributes": [],
                        "additionalInfo": {"description": "", "contentType": "Binary", "documentState": "COMPLETE"}}}]
    for a in assets:   # design assets (rule specs, DQ assets ...) that already exist in the target org
        eo.append({"objectGuid": a["guid"], "objectName": a["name"], "objectType": a["type"], "path": a["path"], "providerName": None,
                   "metadata": {"modelVersion": {"major": 1, "minor": 0}, "repoInfo": {"repoHandle": a["guid"]}, "objectRefs": [], "contextAttributes": None,
                                "additionalInfo": {"description": "", "contentType": "Binary", "documentState": "VALID"}}})
    for c in conns:
        eo.append({"objectGuid": c["guid"], "objectName": c["name"], "objectType": "Connection", "path": "/SYS", "providerName": None,
                   "metadata": {"modelVersion": mv, "repoInfo": {"repoHandle": c["repoHandle"]}, "objectRefs": [], "contextAttributes": None,
                                "additionalInfo": {"description": None, "contentType": "JSON", "documentState": "COMPLETE"}}})
    em = json.dumps({"name": "gen_" + name, "sourceOrgId": spec["orgGuid"], "sourceOrgName": spec.get("orgName", "data"),
                     "exportedObjects": eo}).encode()
    files = {dt_path: innerb, "exportMetadata.v2.json": em}
    files.update(extra)
    return files, now, dt


def checksum_text(files, now_ms):
    """exportPackage.chksum as Properties.store writes it: "#", "#<date> UTC", then one checksum_key=SHA line per file."""
    return "#\n#%s\n" % time.strftime("%a %b %d %H:%M:%S UTC %Y", time.gmtime(now_ms / 1000.0)) + "".join(
        "%s=%s\n" % (checksum_key(p), hashlib.sha256(b).hexdigest().upper()) for p, b in files.items())


def _write(target, spec, imf, now_ms):
    """Write the package of ``spec`` to ``target`` (a path or a binary file object). Every SpecError comes before
    anything is written."""
    if spec.get("documentType") == "DMAPPLET":         # a mapplet: <name>.DMAPPLET.zip holding mappletTemplate.json
        from .nodes.mapplet import mapplet_package_bytes
        data = mapplet_package_bytes(spec, imf, now_ms=now_ms)
        if hasattr(target, "write"):
            target.write(data)
        else:
            with open(target, "wb") as f:
                f.write(data)
        return
    files, now, dt = package_files(spec, imf, now_ms)
    ck = checksum_text(files, now)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p, bb in files.items():
            _zip_put(z, p, bb, dt)
        _zip_put(z, "exportPackage.chksum", ck, dt)


def package_bytes(spec, imf, now_ms=None):
    """The package as bytes: DTEMPLATE, or DMAPPLET for a spec with "documentType": "DMAPPLET". now_ms fixes every
    timestamp (deployTime, attachTime, checksum header, zip entries); it must fall in 1980-2107 local time (SpecError)."""
    buf = io.BytesIO()
    _write(buf, spec, imf, now_ms)
    return buf.getvalue()


def package(spec, imf, out, now_ms=None):
    """Write the package (see package_bytes) to ``out`` (a path or a binary file object); returns out. Sets
    spec["guid"] when the spec has none."""
    _write(out, spec, imf, now_ms)
    return out
