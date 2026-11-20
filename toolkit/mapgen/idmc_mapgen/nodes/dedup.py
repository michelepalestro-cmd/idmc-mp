"""Deduplicate: a Data Quality dedupe asset that already exists in the org (list it in the spec's "assets").

The input/output port layout is the one of a customer dedupe asset (GroupKey + Person_Name mandatory);
``map`` binds the asset's inputs to incoming fields. asset and the map's incoming names are text (a number becomes its
text; true / false, a list or an object is a SpecError). ``options`` reads them for the build and its lint hook
(``lint_problems``) alike.
"""
from .. import values
from ..registry import node

INS = [("SequenceId", "INTEGER", 19, "OPTIONAL"), ("GroupKey", "STRING", 30, "MANDATORY"), ("Address_Part1", "STRING", 80, "OPTIONAL"),
       ("Date", "TIMESTAMP", 29, "OPTIONAL"), ("Person_Name", "STRING", 80, "MANDATORY"), ("Address_Part2", "STRING", 80, "OPTIONAL"),
       ("Postal_Area", "STRING", 80, "OPTIONAL"), ("Telephone_Number", "STRING", 80, "OPTIONAL"), ("Id", "STRING", 80, "OPTIONAL"),
       ("Attribute1", "STRING", 80, "OPTIONAL"), ("Attribute2", "STRING", 80, "OPTIONAL"), ("Code", "STRING", 80, "OPTIONAL"), ("Geocode", "STRING", 80, "OPTIONAL")]
OUTS = [("Out_ClusterId", "STRING", 30), ("Out_ClusterSize", "INT32", 10), ("Out_RowId", "STRING", 25), ("Out_DriverId", "STRING", 25),
        ("Out_DriverScore", "FLOAT", 15), ("Out_LinkId", "STRING", 25), ("Out_LinkScore", "FLOAT", 15)] + \
       [("Out_" + n, "TIMESTAMP" if n == "Date" else "STRING", 29 if n == "Date" else 80) for n, _, _, _ in INS[2:]] + [("Out_IsSurvivor", "STRING", 80)]


def options(nd):
    """(asset, {asset input: incoming field}) of a dedup node, as the build reads them."""
    return values.text(nd, "asset", what="an asset id"), values.as_text_map(nd["map"], values.where(nd, "map"))


@node("dedup", doc="asset: <frs id>; map: {asset_input (GroupKey, Person_Name, ...): incoming_field}. Outputs Out_ClusterId, Out_IsSurvivor, ...")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    asset, mp = options(nd)
    gi = b.group("Input group:", True, False); go = b.group("MappletOutputTx_Output", False, True, rule=False)
    fin = [b.new("DedupField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false", name=n,
                 platformType=b.ptype(ty), precision=pr, scale=0, fieldConstraint=c) for n, ty, pr, c in INS]
    fout = [b.new("TxField", defaultValue="", ignoreComparison="false", ignoreNullInputs="false", isDefaultValueUpdated="false", name=n,
                  platformType=b.ptype(ty), precision=pr, scale=0) for n, ty, pr in OUTS]
    byname = {f["name"]: f for f in fin}
    fm = b.new("FieldMapping", fields=[b.new("TxFieldMapping", defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                                              isDefaultValueUpdated="false", name=src_, precision=0, scale=0, txField=b.ref(byname[dst_]))
                                        for dst_, src_ in mp.items()])
    tx = b.new("TmplDedup", augmented="false", createTime=ctx.now, name=name, advancedProperties=b.adv([("version", "R37")]), groups=[gi, go],
               assetDocumentId="", assetId="@" + asset,
               inputGroups=[b.new("TmplDQGroup", name="Input group:", fieldMappingMode="MANUAL", fieldMapping=fm)],
               inputFields=b.new("DQFields", fieldList=fin), outputFields=b.new("DQFields", fieldList=fout))
    ctx.out(name, go); ctx.inp(name, gi)
    return tx


def lint_problems(spec, nd, analysis=None, conns=None):
    """[(lint code, message)]: what the build refuses in this dedup's values (``options``; the map's asset inputs are
    lint's DDP_MAP)."""
    return values.refusals(nd, lambda: options(nd))


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['asset', 'map'])

values.lint_hook("dedup", lint_problems)      # lint reports what the build refuses (values.lint_hook)
