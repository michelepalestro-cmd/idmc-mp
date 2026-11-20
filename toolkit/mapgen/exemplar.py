#!/usr/bin/env python3
"""exemplar.py - read an EXPORTED mapping and print how its sources, targets and lookups are built, so a connector the
generator has no template for can be generated from that shape. Offline, standard library only, read-only.

    python toolkit/mapgen/exemplar.py <package.zip>            # a v3 export package, or one <name>.DTEMPLATE.zip inside it
    python toolkit/mapgen/exemplar.py <package.zip> --all      # every field, not only the first 25
    python toolkit/mapgen/exemplar.py <package.zip> --json     # the same, as JSON

Use it when IDMC supports a source or target that the generator has no template for (no row in the Mapping Fast Path
section 2): find a mapping in the org that already reads or writes that connector, or have one made once in the
Mapping Designer (one source, one target, saved; it does not need to run), export it
(`python "toolkit/lib/idmc_export_import.py" export --id <frsGuid> --out x.zip`),
then run this on the zip. For each adapter it prints the connection reference, typeSystem, objectType, the object
path, the read / write options and runtime attributes that differ from the defaults, any connector-specific attribute
objects (for example FlatFileAttrs), and the fields as spec tuples [name, TYPE, precision, nativeType, scale], plus a
starter spec node and profile entry. Values whose names look like secrets are never printed.
Keep exported packages out of shared folders: they hold your org's ids.
"""
import argparse
import io
import json
import re
import sys
import zipfile

try:                                                          # the classes the generator already builds
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    from idmc_mapgen.types import CLS as _CLS
    KNOWN_CLASSES = tuple(_CLS.values())
except Exception:                                             # run standalone: skip the "not templated" check
    KNOWN_CLASSES = ()
SENSITIVE_NAME = re.compile(r"(?i)pass(word|wd)?|secret|token|credential|private|api[_-]?key|access[_-]?key")
# IDMC platform type -> the generator's spec type label (labels only: every connector uses them with its own nativeType)
SPEC_TYPE = {"string": "STRING", "bigint": "INTEGER", "decimal": "NUMERIC", "double": "FLOAT",
             "date/time": "TIMESTAMP", "integer": "INT32"}
def is_default(v):
    """An empty / off value that adds nothing to a spec ('', 'false', 0, None, NONE, empty list or dict)."""
    return v is None or v is False or v == 0 or (isinstance(v, str) and v in ("", "false", "0", "NONE")) \
        or (isinstance(v, (list, dict)) and not v)


def short(cls):
    return (cls or "").rsplit(".", 1)[-1]


def imf_docs(z):
    """The IMF documents (JSON with a 'content' key) among a mapping zip's bin/*.bin files; other bins (for example a
    parsing model's binary) are skipped."""
    for b in [m for m in z.namelist() if m.startswith("bin/") and m.endswith(".bin")]:
        try:
            d = json.loads(z.read(b).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(d, dict) and "content" in d:
            yield d


def mappings_in(path):
    """Yield (name, imf dict) for every mapping in a package zip or a single DTEMPLATE zip."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if any(n.startswith("bin/") for n in names):         # a single <name>.DTEMPLATE.zip
            for d in imf_docs(z):
                yield path.replace("\\", "/").rsplit("/", 1)[-1], d
            return
        inner = [n for n in names if n.endswith(".DTEMPLATE.zip") or n.endswith(".DMAPPLET.zip")]
        if not inner:
            sys.exit("no mapping found in %s (expected <name>.DTEMPLATE.zip entries or bin/*.bin)" % path)
        for n in inner:
            with zipfile.ZipFile(io.BytesIO(z.read(n))) as iz:
                for d in imf_docs(iz):
                    yield n.rsplit("/", 1)[-1], d


def scalars(d, ci):
    """Non-default scalar properties of an IMF object (secrets redacted)."""
    out = {}
    for k, v in (d or {}).items():
        if k.startswith("$$") or isinstance(v, (dict, list)):
            continue
        if is_default(v):
            continue
        out[k] = "<redacted>" if SENSITIVE_NAME.search(k) else v
    return out


def attrs(ra):
    """RuntimeAttributes {attributes: [{name, value}]} -> {name: value} (secrets redacted)."""
    out = {}
    for a in (ra or {}).get("attributes") or []:
        n = a.get("name")
        if n is None:
            continue
        v = a.get("value")
        out[n] = "<redacted>" if SENSITIVE_NAME.search(str(n)) else v
    return out


def spec_type(platform):
    sid = (platform or {}).get("##SID") or ""
    p = sid.rsplit("/", 1)[-1]
    return SPEC_TYPE.get(p, p.upper() or "?")


def read_adapter(t, ci, all_fields):
    da = t.get("dataAdapter") or {}
    role = short(ci.get(str(t.get("$$class"))))
    obj = da.get("object") or {}
    ofields = {f.get("name"): f for f in obj.get("fields") or []}
    fields = []
    for f in t.get("fields") or []:
        of = ofields.get(f.get("name")) or {}
        fields.append([f.get("name"), spec_type(f.get("platformType")), f.get("precision"), of.get("nativeType"), f.get("scale")])
    extra = {}
    for k, v in da.items():
        if k in ("object", "oprRuntimeAttributes", "runtimeAttributes", "readOptions", "writeOptions", "bulkOptions") or k.startswith("$$"):
            continue
        if isinstance(v, dict) and "$$class" in v:
            s = scalars(v, ci)
            if s:
                extra["%s (%s)" % (k, short(ci.get(str(v["$$class"]))))] = s
    return {
        "transformation": t.get("name"), "role": role,
        "connectionRef": da.get("connectionId"), "typeSystem": da.get("typeSystem"), "adapterObjectType": da.get("objectType"),
        "object": dict({k: obj.get(k) for k in ("objectName", "objectType", "path", "parentPath", "dbSchema") if obj.get(k)}, **({"customQuery": (obj["customQuery"][:300] + (" ..." if len(obj["customQuery"]) > 300 else ""))} if obj.get("customQuery") else {})),
        "readOptions": scalars(da.get("readOptions"), ci), "writeOptions": scalars(da.get("writeOptions"), ci),
        "bulkOptions": scalars(da.get("bulkOptions"), ci),
        "oprRuntimeAttributes": attrs(da.get("oprRuntimeAttributes")), "runtimeAttributes": attrs(da.get("runtimeAttributes")),
        "adapterExtras": extra, "fieldCount": len(fields), "fields": fields if all_fields else fields[:25],
        "advanced": {p.get("name"): p.get("value") for p in t.get("advancedProperties") or [] if not is_default(p.get("value"))},
    }


def starter(a):
    """A starter spec node + profile hint for one adapter (the user's own names replace the placeholders)."""
    kind = "source" if "Source" in a["role"] else "target" if "Target" in a["role"] else "lookup"
    obj = a["object"].get("path") or a["object"].get("objectName") or "<object>"
    node = {"type": kind, "name": a["transformation"], "conn": "<ALIAS>", "object": obj, "fields": a["fields"][:3] + (["..."] if a["fieldCount"] > 3 else [])}
    if kind == "target" and (a["oprRuntimeAttributes"] or a["runtimeAttributes"]):
        node["writerAttrs"] = {"opr": a["oprRuntimeAttributes"], "rt": a["runtimeAttributes"]}
    prof = {"<ALIAS>": {"name": "<connection name>", "kind": "<any label>"}}
    if a["typeSystem"] and a["typeSystem"] != "TOOLKIT":
        prof["<ALIAS>"]["typeSystem"] = a["typeSystem"]
    return node, prof


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("package")
    ap.add_argument("--all", action="store_true", help="print every field")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    known = set(KNOWN_CLASSES)
    result = []
    for name, imf in mappings_in(a.package):
        ci = (imf.get("metadata") or {}).get("$$classInfo") or {}
        c = imf.get("content") or {}
        txs = c.get("transformations") or []
        ad = [t for t in txs if (t.get("dataAdapter") or {}).get("connectionId")
              or any(r in short(ci.get(str(t.get("$$class")))) for r in ("Source", "Target", "Lookup"))]
        m = {"mapping": c.get("name") or name, "transformations": [[t.get("name"), short(ci.get(str(t.get("$$class"))))] for t in txs],
             "adapters": [read_adapter(t, ci, a.all) for t in ad],
             "notTemplated": sorted({ci.get(str(t.get("$$class"))) for t in txs
                                     if known and ci.get(str(t.get("$$class"))) not in known})}
        result.append(m)
    if a.json:
        print(json.dumps(result, indent=1, ensure_ascii=False, default=str))
        return 0
    for m in result:
        print("=" * 100)
        print("mapping:", m["mapping"])
        print("transformations:", ", ".join("%s (%s)" % (n, k) for n, k in m["transformations"]))
        for cls in m["notTemplated"]:
            print("  not templated in the generator yet: %s -> a `generic` node with this cls and the exemplar's "
                  "properties (SPEC_REFERENCE 5.6), or package-clone this mapping" % cls)
        for ad in m["adapters"]:
            print("-" * 100)
            print("%s  [%s]" % (ad["transformation"], ad["role"]))
            print("  connection ref : %s   (match it to GET /api/v2/connection -> federatedId)" % ad["connectionRef"])
            print("  typeSystem     : %s   adapter objectType: %s" % (ad["typeSystem"], ad["adapterObjectType"]))
            print("  object         : %s" % json.dumps(ad["object"]))
            for k in ("readOptions", "writeOptions", "bulkOptions", "oprRuntimeAttributes", "runtimeAttributes", "advanced"):
                if ad[k]:
                    print("  %-15s: %s" % (k, json.dumps(ad[k], default=str)))
            for k, v in ad["adapterExtras"].items():
                print("  extra %-9s: %s" % (k, json.dumps(v, default=str)))
            print("  fields (%d)%s:" % (ad["fieldCount"], "" if a.all or ad["fieldCount"] <= 25 else ", first 25; --all for every one"))
            for f in ad["fields"]:
                print("    ", json.dumps(f))
            node, prof = starter(ad)
            print("  starter spec node :", json.dumps(node, default=str))
            print("  starter profile   :", json.dumps(prof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
