"""Verifier: a Data Quality address-verifier asset that already exists in the org (list it in the spec's "assets").

Shape harvested from a designer-built mapping (TmplVerifier, version R37): input group "Input group:" with a MANUAL
field mapping (incoming field -> the asset's input port), output group "MappletOutputTx_Output" carrying the asset's
output ports; incoming fields pass through. Options:
  asset    the verifier asset's frs id
  inputs   [[port, precision], ...]  the asset's input ports in the asset's order (e.g. Address_Lines_1, 128)
  outputs  [[port, precision], ...]  the asset's output ports (e.g. Verification_Status_Code, 4)
  map      {asset input port: incoming field}; ports left out of the map receive nothing
Added 2026-11-01 (property-master address verification; KB L-CDI-266).
"""
from .. import values
from ..registry import node
from ..types import CLS

CLS.setdefault("TmplVerifier", "com.informatica.metadata.template.tx.tmplverifier.TmplVerifier")
CLS.setdefault("TmplVerifierGroup", "com.informatica.metadata.template.tx.tmplverifier.TmplVerifierGroup")
CLS.setdefault("VerifierFields", "com.informatica.metadata.template.tx.tmplverifier.VerifierFields")


def _ports(nd, key):
    out = []
    for i, p in enumerate(nd.get(key) or []):
        at = values.where(nd, "%s[%d]" % (key, i))
        nm = values.as_text(p[0], at + " name", what="a port name")
        prec = values.as_whole(p[1] if len(p) > 1 else None, at + " precision", 1, 128, "128")
        out.append((nm, prec))
    return out


def options(nd):
    asset = values.text(nd, "asset", what="an asset id")
    ins, outs = _ports(nd, "inputs"), _ports(nd, "outputs")
    mp = nd.get("map") or {}
    known = {n for n, _ in ins}
    for k in mp:
        if k not in known:
            from ..spec import SpecError
            raise SpecError("verifier %r: map key %r is not one of its inputs %s" % (nd.get("name"), k, sorted(known)))
    return asset, ins, outs, {k: values.as_text(v, values.where(nd, "map " + k), what="a field name") for k, v in mp.items()}


@node("verifier", doc="asset: <frs id>; inputs/outputs: [[port, prec]]; map: {port: incoming field}; incoming fields pass through.")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    asset, ins, outs, mp = options(nd)
    gi = b.group("Input group:", True, False)
    go = b.group("MappletOutputTx_Output", False, True, rule=False)

    def tf(n, p):
        return b.new("TxField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false",
                     name=n, platformType=b.ptype("STRING"), precision=p, scale=0)
    infl = [tf(n, p) for n, p in ins]
    outfl = [tf(n, p) for n, p in outs]
    by_port = {f["name"]: f for f in infl}
    fm = b.new("FieldMapping", fields=[b.new("TxFieldMapping", defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                                              isDefaultValueUpdated="false", name=src, precision=0, scale=0, txField=b.ref(by_port[port]))
                                       for port, src in mp.items()])
    tx = b.new("TmplVerifier", augmented="false", createTime=ctx.now, name=name, advancedProperties=b.adv([("version", "R37")]),
               groups=[gi, go], active="false", verifierAssetDocumentId="", verifierAssetId="@" + asset,
               inputGroups=[b.new("TmplVerifierGroup", name="Input group:", fieldMappingMode="MANUAL", fieldMapping=fm)],
               inputFields=b.new("VerifierFields", fieldList=infl), outputFields=b.new("VerifierFields", fieldList=outfl))
    ctx.out(name, go); ctx.inp(name, gi)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    return values.refusals(nd, lambda: options(nd))


build.options = frozenset(['asset', 'inputs', 'outputs', 'map'])

values.lint_hook("verifier", lint_problems)
