"""Mapplets: build a reusable mapplet (DMAPPLET) from a spec, and call one from a mapping.

1. A mapplet spec is a normal spec with "documentType": "DMAPPLET", an "input" node and an "output" node:

    {"name": "mplt_clean_names", "documentType": "DMAPPLET", "connections": {},
     "nodes": [
       {"type": "input",  "name": "Input",  "fields": [["in_name", "STRING", 256], ["in_city", "STRING", 256]]},
       {"type": "expression", "name": "EXP_CLEAN", "fields": [{"name": "clean_name", "type": "STRING", "prec": 256,
                                                                "expr": "UPPER(LTRIM(RTRIM(in_name)))"}]},
       {"type": "output", "name": "Output", "fields": [["clean_name", "STRING", 256]]}],
     "links": [["Input", "EXP_CLEAN"], ["EXP_CLEAN", "Output"]]}

   Compile it with compile.build (the template hook below sets documentType) and package it with package.package /
   package.package_bytes, which hand a DMAPPLET spec to ``mapplet_package_bytes`` (a <name>.DMAPPLET.zip package; IDMC
   accepts documentType "DMAPPLET", not "MAPPLET"); mapgen.py build / deploy and compile_file do this. The package
   lists the spec's connections; it carries no "assets", no projectJson / folderJson files and no packageOverrides
   (PACKAGE_IGNORES): a spec that sets them gets lint WARN MPLT_PKG_IGNORED, and mapgen.py build / deploy and
   python -m idmc_mapgen.compile print the same warning.

2. A mapping calls it with a "mapplet" node, and lists it under "assets" so the package declares the dependency:

    {"type": "mapplet", "name": "MPL_CLEAN", "mappletGuid": "<frs id of the imported mapplet>",
     "inputs": [["in_name", "STRING", 256], ["in_city", "STRING", 256]],
     "outputs": [["clean_name", "STRING", 256]],
     "map": {"in_name": "customer_name", "in_city": "city"}}          # mapplet input -> incoming field
    "assets": [{"guid": "<same id>", "name": "mplt_clean_names", "type": "DMAPPLET", "path": "/Explore/<project>/<folder>"}]

   package.py writes every asset as a reference with refType "frsDocument" (an asset's own "refType" key is not read):
   that is how m_probe_mapplet imported and ran live. UI exports write refType "mappletTemplate" for a mapplet;
   that form is not proven with a generated package.
   Link into "MPL_CLEAN" and out of "MPL_CLEAN". Only the mapplet's outputs leave it (like a passive transformation
   with no pass-through), so carry other fields around it with a Joiner, or add them as mapplet inputs/outputs.

Option values (idmc_mapgen/values.py): a mapplet node's "active" and a DMAPPLET spec's own "active" are booleans (true /
false, "true" / "false" in any case, 0 / 1; default false); mappletGuid, inputGroup / outputGroup and the map values
are text (a number becomes its text); fields / inputs / outputs are field tuples (imf.field_tuple). lint reports what
the build refuses in them (``lint_problems``, ``spec_problems``: values.lint_hook), in the build's words.
"""
import io
import json
import zipfile

from .. import values
from ..imf import field_tuple, imf_bytes
from ..registry import node, template_hook
from ..spec import SpecError
from ..types import typeinfo

NS_IN = "com.informatica.metadata.template.tx.tmplinput."
NS_OUT = "com.informatica.metadata.template.tx.tmploutput."
NS_MPL = "com.informatica.metadata.template.tx.tmplmapplet."
MAPPLET_ADAPTER = "com.informatica.metadata.template.ext.da.cloud.common.MappletAdapter"


def _txf(b, fd, i=0, **extra):
    name, t, prec, sc, _, _ = field_tuple(fd, i)      # whole precision / scale, the scale not above the precision
    return b.new("TxField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                 name=name, platformType=b.ptype(t), precision=prec, scale=sc, **extra)


@node("input", doc="Mapplet Input: fields [[name, TYPE, prec?], ...] (only in a DMAPPLET spec).")
def build_input(ctx, nd):
    b = ctx.b; name = nd["name"]
    b.register(NS_IN + "TmplInput")
    g = b.group("DefaultGroup", False, True, rule=False)
    tx = b.new("TmplInput", augmented="false", createTime=ctx.now, name=name, groups=[g],
               fields=[_txf(b, fd, i) for i, fd in enumerate(nd["fields"])])
    ctx.out(name, g)
    return tx


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build_input.options = frozenset(['fields'])


@node("output", doc="Mapplet Output: fields [[name, TYPE, prec?], ...], map {output field: incoming field} (default same name).")
def build_output(ctx, nd):
    b = ctx.b; name = nd["name"]
    for c in ("TmplOutput", "OutputFieldMappings", "OutputFieldMapping"):
        b.register(NS_OUT + c)
    g = b.group("DefaultGroup", True, False)
    outs = [_txf(b, fd, i) for i, fd in enumerate(nd["fields"])]
    mp = values.text_map(nd, "map")
    tx = b.new("TmplOutput", augmented="false", createTime=ctx.now, name=name, groups=[g], fields=outs, fieldMappingMode="MANUAL",
               showLabels="true",
               manualMappings=b.new("OutputFieldMappings", mappingList=[
                   b.new("OutputFieldMapping", fromFieldName=mp.get(f["name"], f["name"]), toField=b.ref(f)) for f in outs]))
    ctx.inp(name, g)
    return tx


build_output.options = frozenset(['fields', 'map'])


@template_hook
def set_document_type(ctx, content):
    if ctx.spec.get("documentType") == "DMAPPLET":
        content["documentType"] = "DMAPPLET"


def _adapter_field(b, fd, i=0):
    name, t, prec, sc, _, _ = field_tuple(fd, i)      # the TxField's precision / scale (the scale was always the default)
    pt = typeinfo(t)[0]
    return b.new("BaseAdapterField", name=name, annotations=[b.new("Description", body="")], createable="true", externalId="false",
                 fieldStatus="UNDEFINED", fieldType="UNDEFINED", filterable="true", foreignKey="false", generated="false", javaType="",
                 key="false", label=name, nativeName="", nativeType="string" if pt == "string" else pt, newField="false", nullable="true",
                 original="false", passthroughPort="false", precision=prec, scale=sc, sfIdLookup="false", unique="false", updateable="true")


@node("mapplet", doc="Call a mapplet: mappletGuid, inputs, outputs, map {mapplet input: incoming field}, active.")
def build_mapplet(ctx, nd):
    b = ctx.b; name = nd["name"]
    for c in ("TmplMapplet", "TxFieldGroup"):
        b.register(NS_MPL + c)
    b.register(MAPPLET_ADAPTER)
    active, guid = values.flag(nd, "active"), values.text(nd, "mappletGuid", what="a mapplet id")
    gi = b.group(values.text(nd, "inputGroup", "Input", what="a group name"), True, False)
    go = b.group(values.text(nd, "outputGroup", "Output", what="a group name"), False, True, rule=False)
    in_txf = [_txf(b, fd, i) for i, fd in enumerate(nd["inputs"])]
    out_txf = [_txf(b, fd, i) for i, fd in enumerate(nd["outputs"])]
    in_af = [_adapter_field(b, fd, i) for i, fd in enumerate(nd["inputs"])]
    out_af = [_adapter_field(b, fd, i) for i, fd in enumerate(nd["outputs"])]
    mp = values.text_map(nd, "map")
    fm = b.new("FieldMapping", fields=[
        b.new("TxField", adapterField=b.ref(af), defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
              isDefaultValueUpdated="false", name=mp.get(af["name"], af["name"]), precision=0, scale=0) for af in in_af])
    tx = b.new("TmplMapplet", augmented="false", createTime=ctx.now, name=name, groups=[gi, go],
               active=values.imf_bool(active), fieldMappingMode="MANUAL", hasFixedReferences="false",
               saasMappletId="@" + guid, type="NATIVE",
               inputGroups=[b.new("TxFieldGroup", name=gi["name"], fields=in_txf)],
               outputGroups=[b.new("TxFieldGroup", name=go["name"], fields=out_txf)],
               validForEngines=["CDI"],
               dataAdapter=b.new("MappletAdapter", name="", inputFields=in_af, outputFields=out_af),
               fieldMapping=fm)
    ctx.inp(name, gi); ctx.out(name, go)
    return tx


build_mapplet.options = frozenset(['mappletGuid', 'inputs', 'outputs', 'map', 'active', 'inputGroup', 'outputGroup'])

PACKAGE_IGNORES = ("assets", "projectJson", "folderJson", "packageOverrides")


def package_ignored(spec):
    """The keys of PACKAGE_IGNORES a DMAPPLET spec sets (to anything but null or empty) -> [key]: its package lists
    only the spec's connections, so mapplet_package_bytes writes no asset reference, no projectJson / folderJson file
    (it does not even read it) and no packageOverrides. [] for any other spec."""
    if not isinstance(spec, dict) or spec.get("documentType") != "DMAPPLET":
        return []
    return [k for k in PACKAGE_IGNORES if spec.get(k) is not None and spec.get(k) not in ("", [], {}, ())]


def package_ignored_message(spec):
    """One line saying which keys of a DMAPPLET spec its package ignores (package_ignored), or None."""
    keys = package_ignored(spec)
    if not keys:
        return None
    return ("this DMAPPLET spec sets %s, which a mapplet package does not carry: it lists only the connections (no "
            "asset reference, no projectJson / folderJson file -- not even read -- and no packageOverrides), so %s "
            "no effect" % (" and ".join(", ".join(keys).rsplit(", ", 1)), "it has" if len(keys) == 1 else "they have"))


def mapplet_package_bytes(spec, imf, guid=None, now_ms=None):
    """A DMAPPLET import package (outer zip bytes) for a compiled mapplet spec. Sets spec["guid"].

    Same package rules as package.py: the name checks, ONE reference / objectRef / Connection entry per connection
    guid, exportPackage.chksum written by package.checksum_text (keys escaped as Properties.store writes them), every
    SpecError before spec["guid"] is set, and ``now_ms`` fixes every timestamp (deployTime, attachTime, the checksum
    header and every zip entry), so the same inputs give the same bytes; a pinned ``now_ms`` outside 1980-2107 local
    time (the years a ZIP entry date can hold) is a SpecError, as for package.package_bytes. The keys of
    PACKAGE_IGNORES are not packaged (package_ignored; lint warns MPLT_PKG_IGNORED)."""
    from ..package import _dependencies, _name_problems, _package_time, _zip_put, checksum_text, new_guid
    conns, _, dep_errs = _dependencies(spec, assets=False)
    ms, dt, time_errs = _package_time(now_ms)      # dates the entries as package.package_files does
    errs = _name_problems(spec) + dep_errs + time_errs
    if errs:
        raise SpecError(errs)
    name = spec["name"]; F = spec["folder"]
    g = guid or spec.get("guid") or new_guid(); spec["guid"] = g
    binb = imf_bytes(imf)
    mt = [{"@type": "mappletTemplate", "id": "@1", "name": name, "description": spec.get("description", ""), "autoExpireObject": False,
           "bundleVersion": "0", "assetFrsGuid": g, "templateId": "@2", "deployTime": ms, "hasParameters": False, "valid": True,
           "fixedConnection": True, "hasParametersDeployed": False, "fixedConnectionDeployed": True, "isSchemaValidationEnabled": False,
           "tasks": 0, "documentType": "DMAPPLET", "validForEngines": ["CDI"],
           "active": values.as_flag(spec.get("active"), "mapplet spec %r: active" % name),
           "hasFixedReferences": False, "allowMaxFieldLength": False, "specialCharacterSupport": False,
           "references": [{"@type": "reference", "refObjectId": "@" + c["guid"], "refType": "connection"} for c in conns]}]
    fr = [{"@type": "fileRecord", "id": "@2", "name": name, "type": "IMFOBJECT", "size": len(binb), "attachTime": ms,
           "additionalInfo": "com.informatica.metadata.template.common.Template"}]
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED) as z:
        _zip_put(z, "mappletTemplate.json", json.dumps(mt, separators=(",", ":")), dt)
        _zip_put(z, "fileRecord.json", json.dumps(fr, separators=(",", ":")), dt)
        _zip_put(z, "bin/@2.bin", binb, dt)
        _zip_put(z, "metadata.meta", json.dumps([{"@type": "objectRef", "id": "@1", "type": "mappletTemplate"}]), dt)
    mv = {"major": 0, "minor": 0}
    eo = [{"objectGuid": g, "objectName": name, "objectType": "DMAPPLET", "path": "/Explore/%s/%s" % (F["project"], F["name"]), "providerName": None,
           "metadata": {"modelVersion": mv, "repoInfo": None, "objectRefs": [c["guid"] for c in conns], "contextAttributes": [{"name": "id", "value": "@1"}],
                        "additionalInfo": {"description": spec.get("description", ""), "contentType": "JSON", "documentState": "VALID"}}},
          {"objectGuid": F["projectGuid"], "objectName": F["project"], "objectType": "Project", "path": "/Explore", "providerName": None,
           "metadata": {"modelVersion": mv, "repoInfo": None, "objectRefs": [], "contextAttributes": [],
                        "additionalInfo": {"description": "", "contentType": "Binary", "documentState": "COMPLETE"}}},
          {"objectGuid": F["guid"], "objectName": F["name"], "objectType": "Folder", "path": "/Explore/" + F["project"], "providerName": None,
           "metadata": {"modelVersion": mv, "repoInfo": None, "objectRefs": [], "contextAttributes": [],
                        "additionalInfo": {"description": "", "contentType": "Binary", "documentState": "COMPLETE"}}}]
    for c in conns:
        eo.append({"objectGuid": c["guid"], "objectName": c["name"], "objectType": "Connection", "path": "/SYS", "providerName": None,
                   "metadata": {"modelVersion": mv, "repoInfo": {"repoHandle": c["repoHandle"]}, "objectRefs": [], "contextAttributes": None,
                                "additionalInfo": {"description": None, "contentType": "JSON", "documentState": "COMPLETE"}}})
    em = json.dumps({"name": "gen_" + name, "sourceOrgId": spec["orgGuid"], "sourceOrgName": spec.get("orgName", "data"), "exportedObjects": eo}).encode()
    files = {"Explore/%s/%s/%s.DMAPPLET.zip" % (F["project"], F["name"], name): inner.getvalue(), "exportMetadata.v2.json": em}
    ck = checksum_text(files, ms)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p, bb in files.items():
            _zip_put(z, p, bb, dt)
        _zip_put(z, "exportPackage.chksum", ck, dt)
    return out.getvalue()


def _flow():
    try:
        from ..fieldflow import F, flow, fields
    except ImportError:
        return

    def _decl(nd, key):
        return [F(fd[0], fd[1] if len(fd) > 1 else None, nd["name"]) for fd in nd.get(key) or []]

    @flow("input", ports=lambda nd: ([], [""]), override=True)
    def _input(nd, inputs):
        return {"": fields(_decl(nd, "fields"))}

    @flow("output", ports=lambda nd: ([""], []), override=True)
    def _output(nd, inputs):
        return {}

    @flow("mapplet", ports=lambda nd: ([""], [""]), override=True)
    def _mapplet(nd, inputs):
        return {"": fields(_decl(nd, "outputs"))}


_flow()

# ---------------------------------------------------------------------------------------------- lint
_REQUIRED = {"input": ("fields",), "output": ("fields",), "mapplet": ("mappletGuid", "inputs", "outputs")}


def _field_tuples(nd, key):
    return [field_tuple(fd, i) for i, fd in enumerate(nd[key])]


def _readers(nd):
    """The option readers that build_input / build_output / build_mapplet apply to node ``nd``."""
    t = nd.get("type")
    if t == "input":
        return [lambda: _field_tuples(nd, "fields")]
    if t == "output":
        return [lambda: _field_tuples(nd, "fields"), lambda: values.text_map(nd, "map")]
    return [lambda: values.flag(nd, "active"), lambda: values.text(nd, "mappletGuid", what="a mapplet id"),
            lambda: values.text(nd, "inputGroup", "Input", what="a group name"),
            lambda: values.text(nd, "outputGroup", "Output", what="a group name"),
            lambda: _field_tuples(nd, "inputs"), lambda: _field_tuples(nd, "outputs"), lambda: values.text_map(nd, "map")]


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in an input, output or mapplet node, in the build's words
    (compile.build_node): a required key it lacks ("missing or unknown key"), a value its readers refuse (an "active"
    that is not a boolean, a mappletGuid / group name / map value that is not text, a field tuple's precision / scale /
    native type / flags, an unknown TYPE), or a field list it cannot read. lint has no rules of its own for these node
    types, so every refusal is reported here (NODE_MALFORMED)."""
    out = [("NODE_MALFORMED", values.named(nd, "missing or unknown key %r" % k))
           for k in _REQUIRED.get(nd.get("type"), ()) if k not in nd]
    for fn in _readers(nd):
        try:
            fn()
        except SpecError as e:
            out += [("NODE_MALFORMED", values.named(nd, p if isinstance(p, str) else str(p))) for p in e.problems]
        except KeyError:            # a required key: reported above
            pass
        except Exception as e:      # noqa: BLE001 -- a field list the build cannot read: it names the exception too
            out.append(("NODE_MALFORMED", values.named(nd, "%s: %s" % (type(e).__name__, e))))
    return out


def spec_problems(spec):
    """[(lint code, message)] of a DMAPPLET spec as a whole: its "active" as mapplet_package_bytes reads it (a boolean)
    and the keys its package ignores (MPLT_PKG_IGNORED, a WARN: package_ignored_message, which mapgen.py build / deploy
    and python -m idmc_mapgen.compile print too). [] for any other spec."""
    if not isinstance(spec, dict) or spec.get("documentType") != "DMAPPLET":
        return []
    out = []
    try:
        values.as_flag(spec.get("active"), "mapplet spec %r: active" % spec.get("name"))
    except SpecError as e:
        out.append(("NODE_MALFORMED", str(e)))
    msg = package_ignored_message(spec)
    return out + ([("MPLT_PKG_IGNORED", msg)] if msg else [])


values.lint_hook(("input", "output", "mapplet"), lint_problems)      # lint reports what the build refuses
# a spec-level check on the nodes every mapplet spec has (input, output), raised once (node None)
values.lint_hook(("input", "output"), lambda spec, nd, analysis, conns: spec_problems(spec), spec_level=True)
