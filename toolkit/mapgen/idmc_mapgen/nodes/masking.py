"""Data Masking (TmplDmo): one masking entry per field; every incoming field leaves as out_<field> (format-preserving).

    {"type": "masking", "name": "DM", "entries": [{"field": "email", "type": "Email address", "prec": 64},
                                                 {"field": "dob", "type": "Random", "pc": "date/time"}],
     "passthrough": true}

Entries: ``{field, type, pc?, prec?, scale?, data?}``, one per field (the designer gives a port one masking rule).
- ``type``: a technique of the Mapping Designer's rule catalogue (MASKING_TYPES). "Email Advanced" is the advanced
  e-mail rule (stored as maskingType "Email address" with isEmailAdvanced TRUE).
- ``pc``: the rule's data type = the masked field's platform type (string, date/time, decimal, bigint, integer,
  double, ...). The designer takes it from the field, and so does the generator: leave it out and it is the platform
  type of the field as it arrives (STRING -> string, TIMESTAMP/DATE -> date/time, NUMERIC -> decimal, INTEGER ->
  bigint, INT32 -> integer, FLOAT -> double), string when that type cannot be derived. A pc that contradicts the
  field's known type is a SpecError (a string rule on a bigint port). It picks the rule variant (Key and Random have
  string, date and numeric variants) and the default precision/scale of the rule: string 256/0 (as the legacy
  generators wrote), date/time 29/9, decimal 28/9, bigint 19/0, integer 10/0, double 15/0. (The designer copies the
  masked field's own precision/scale; give them when the field's differ, e.g. a STRING longer than 256 or a NUMERIC
  with scale 0.) ``prec`` / ``scale`` (whole numbers; null = the default) override them; a scale above the precision
  is a SpecError (decimal with prec 5 needs a scale).
- ``data``: {param: value} on top of the rule's defaults (parameters the rule does not know are appended). What data
  leaves open follows the dialog's couplings: isSeeded follows repeatableOutput and replaceCardIssuer is the opposite
  of keepCardIssuer (DERIVED), turning useRange on turns useBlurring off and vice versa (EXCLUSIVE), and a parameter
  whose activation condition is not met is written empty (a BOOL one "FALSE"), as the designer writes it. A mandatory
  parameter without a default must be given (custom "Substitution": dicName, outputPort; "Dependent":
  dependentPortName, dependentOutputPort; "Email Advanced": firstNameColumn, lastNameColumn). An unknown type is a
  SpecError.

``passthrough``: the Data Masking transformation itself only emits out_<field>, and the designer has no pass-through
setting (an all-fields rule on its output group is ignored at run time: TE_7002 "invalid symbol reference" for the
original name). "passthrough": true adds, right after it, an Expression ``<name>_passthrough`` that maps every
out_<field> back to <field> -- what designer-built mappings do by hand (m_003_mask_customers exp_Anchor_Output,
m_load_and_cleanse_customer_data exp_prepare_output) -- so downstream nodes see every incoming field under its own
name as well: unmasked fields unchanged, masked fields carrying the MASKED value (the clear value never leaves the
masking). Links from the masking node leave from that Expression. The incoming fields come from the spec's field flow;
``"passthrough": [name | [name, TYPE, prec?, scale?], ...]`` restores only these, and is required when an upstream
node's fields cannot be derived (a generic node, an unknown type); there a typed entry also gives a masked field's
rule its data type. A restored port carries its own type's precision/scale: the rule's for a masked field of that
type, else the declared or the type's default (a declared prec / scale is a whole number, null = the default, as in
an entry; a scale above the precision is a SpecError).

``passthrough`` is true / false ("true" / "false" in any case, 0 / 1, null = false) or a field list (``passthrough_value``);
``data`` values are text (a number becomes its text, "seedValue": 190 is "190"; null = the rule's default; true /
false, a list or an object is a SpecError: the designer writes "TRUE" / "FALSE").

lint (``lint_problems``) runs these same rules, so it reports exactly the entries (MSK_TYPE) and passthrough values
(MSK_FIELD) that the build refuses.
"""
import weakref

from .. import values
from ..registry import node, template_hook
from ..types import TYPES, typeinfo

# Parameter sets per masking type, as the Mapping Designer writes them. maskingType takes the human label.
# (They are the catalogue's string rules below, with the designer's values for Credit card and Key.)
PRESET = {"Email address": {"repeatableOutput": "TRUE", "isSeeded": "TRUE", "seedValue": "190", "isEmailAdvanced": "FALSE",
                            "errorHandle": "DefaultValue", "trim": "FALSE", "isEmailStandard": "TRUE", "isMapped": "FALSE"},
          "Phone": {"overrideAllowed": "FALSE", "repeatableOutput": "TRUE", "isSeeded": "TRUE", "seedValue": "190", "errorHandle": "DefaultValue", "trim": "FALSE"},
          "SSN": {"overrideAllowed": "FALSE", "repeatableOutput": "TRUE", "isSeeded": "TRUE", "seedValue": "190", "isRandomized": "TRUE", "errorHandle": "DefaultValue", "trim": "FALSE"},
          "Credit card": {"overrideAllowed": "FALSE", "repeatableOutput": "TRUE", "isSeeded": "TRUE", "seedValue": "190", "keepCardIssuer": "TRUE",
                          "replaceCardIssuer": "FALSE", "targetIssuer": "", "errorHandle": "DefaultValue", "trim": "FALSE"},
          "Key": {"overrideAllowed": "FALSE", "repeatableOutput": "TRUE", "isSeeded": "TRUE", "seedValue": "190", "useMaskFormat": "FALSE", "maskFormat": "",
                  "useSrcFilter": "FALSE", "srcFilterOption": "", "srcFilterStr": "", "useTargetFilter": "FALSE", "targetFilterOption": "", "targetFilterStr": ""}}

# The designer's masking rule catalogue (the rules the Data Masking dialog offers; TDmoGenerator writes a rule's
# parameters in this order). maskingType -> {field class: ((param, default, activation "param=VALUE" | None,
# mandatory), ...)}. Field classes: string, date, numeric (see PC_CLASS).
_OVR = ("overrideAllowed", "FALSE", None, False)
_SEED = (("repeatableOutput", "TRUE", None, False), ("isSeeded", "TRUE", None, True), ("seedValue", "190", "repeatableOutput=TRUE", True))
_ERR = (("errorHandle", "DefaultValue", None, False), ("trim", "FALSE", None, False))
_FILTERS = (("useSrcFilter", "FALSE", None, True), ("srcFilterOption", "", "useSrcFilter=TRUE", False), ("srcFilterStr", "", "useSrcFilter=TRUE", False),
            ("useTargetFilter", "FALSE", None, True), ("targetFilterOption", "", "useTargetFilter=TRUE", False),
            ("targetFilterStr", "", "useTargetFilter=TRUE", False))
_DICT_OPTS = (("dictionaryOptimization", "FALSE", "repeatableOutput=TRUE", False), ("isMapped", "FALSE", None, False),
              ("isUnique", "FALSE", "repeatableOutput=TRUE", False), ("isRelationalSrc", "FALSE", None, False), ("isFlatFileSrc", "TRUE", None, False))


def _dictionary(dic, port):
    """A substitution rule over one of Informatica's shipped dictionaries."""
    return ((_OVR,) + _SEED + _DICT_OPTS + (("dicName", dic, None, True), ("fileEncoding", "1", None, False), ("serialNoPort", "SNO", None, False),
                                            ("outputPort", port, None, True), ("lookupInputPort", "", None, False), ("lookupOutputPort", "", None, False)))


def _range_blur(use_range, lo, hi, blur, unit, blo, bhi):
    return (_OVR, ("useRange", use_range, None, True), ("minWidth", lo, "useRange=TRUE", False), ("maxWidth", hi, "useRange=TRUE", False),
            ("useBlurring", blur, None, False), ("blurringUnit", unit, "useBlurring=TRUE", False), ("blurLow", blo, "useBlurring=TRUE", False),
            ("blurHigh", bhi, "useBlurring=TRUE", False))


CATALOGUE = {
    "Credit card": {"string": (_OVR, ("repeatableOutput", "FALSE", None, False)) + _SEED[1:] + (
        ("keepCardIssuer", "TRUE", None, True), ("replaceCardIssuer", "FALSE", None, False), ("targetIssuer", "", "keepCardIssuer=FALSE", False)) + _ERR},
    "Email address": {"string": _SEED + (("isEmailAdvanced", "FALSE", None, False),) + _ERR + (("isEmailStandard", "TRUE", None, False),
                                                                                              ("isMapped", "FALSE", None, False))},
    "Email Advanced": {"string": _SEED + (("isEmailAdvanced", "TRUE", None, False),) + _ERR + (
        ("isEmailStandard", "FALSE", None, False), ("isMapped", "FALSE", None, False), ("fromMapping", "TRUE", None, False),
        ("fromDictionary", "FALSE", None, False), ("firstNameColumn", "", None, True), ("firstNameLength", "10", None, False),
        ("delimiter", "", None, False), ("lastNameColumn", "", None, True), ("lastNameLength", "10", None, False),
        ("isDomainNameConstant", "TRUE", None, False), ("isDomainNameRandom", "FALSE", None, False),
        ("domainConstantValue", "company.com", None, False)) + _ERR},
    "IP address": {"string": (_OVR,) + _SEED + _ERR},
    "Key": {"string": (_OVR,) + _SEED + (("useMaskFormat", "TRUE", None, True), ("maskFormat", "R", None, True)) + _FILTERS,
            "date": (_OVR,) + _SEED + (("isMapped", "FALSE", None, False),),
            "numeric": (("overrideAllowed", "TRUE", None, False),) + _SEED + (("isMapped", "FALSE", None, False),)},
    "Phone": {"string": (_OVR,) + _SEED + _ERR},
    "Random": {"string": (_OVR, ("useRange", "FALSE", None, True), ("minWidth", "", None, False), ("maxWidth", "", None, False),
                          ("useMaskFormat", "TRUE", None, True), ("maskFormat", "R", "useMaskFormat=TRUE", True)) + _FILTERS,
               "numeric": _range_blur("FALSE", "0", "0", "TRUE", "Percent", "10", "10"),
               "date": _range_blur("TRUE", "01/01/1970 00:00:00", "01/19/2038 03:13:59", "FALSE", "Year", "0", "0")},
    "SIN": {"string": (_OVR,) + _SEED + (("startDigit", "FALSE", None, False), ("startDigitValue", "0", "startDigit=TRUE", False)) + _ERR},
    "SSN": {"string": (_OVR,) + _SEED + (("isRandomized", "TRUE", None, False),) + _ERR},
    "Substitution": {"string": (("DicConn", "", None, False), ("dicName", "", None, True), ("outputPort", "", None, True), ("sortPort", "", None, False),
                                ("lookupInputPort", "", None, False), ("lookupOutputPort", "", None, False), ("errorConstantValue", "", None, False),
                                _OVR) + _SEED + _DICT_OPTS + (("fileEncoding", "1", None, False), ("serialNoPort", "SNO", None, False))},
    "Substitution name": {"string": _dictionary("informatica_mask_first_names.dic", "FIRSTNAME")},
    "Substitution female name": {"string": _dictionary("informatica_mask_female_first_names.dic", "FIRSTNAMES")},
    "Substitution male name": {"string": _dictionary("informatica_mask_male_first_names.dic", "MALE_FIRST_NAMES")},
    "Substitution position": {"string": _dictionary("informatica_mask_job_position.dic", "JobPosition")},
    "Substitution last name": {"string": _dictionary("informatica_mask_last_names.dic", "LASTNAME")},
    "Substitution US ZIP code": {"string": _dictionary("informatica_mask_us_zipcode.dic", "US_ZIPCODE")},
    "Substitution street": {"string": _dictionary("informatica_mask_address.dic", "STREET")},
    "Substitution city": {"string": _dictionary("informatica_mask_us_towns.dic", "TOWNNAMES")},
    "Substitution state": {"string": _dictionary("informatica_mask_states.dic", "STATENAME")},
    "Substitution country": {"string": _dictionary("informatica_mask_countries.dic", "COUNTRY_NAME")},
    "Dependent": {"string": (("dependentPortName", "", None, True), ("dependentOutputPort", "", None, True))},
    "URL": {"string": (_OVR,) + _SEED + _ERR},
}
MASKING_TYPES = tuple(CATALOGUE)
IMF_TYPE = {"Email Advanced": "Email address"}      # spec type -> maskingType label written in the IMF

# The dialog's coupled parameters (ui_js TDmo rule dialog, _refreshData / _handleToggleRangeBlur), applied to what
# ``data`` leaves open: a parameter the designer derives from another one (mask_rules.json "derivationList"; the dialog
# hides it): param -> ((related param, its value, derived value), ...); the Random switches it keeps exclusive (turning
# one on turns the other off); and the BOOL parameters it writes "FALSE" (a radio group) instead of "" while their
# activation condition is not met. The defaults already agree with all three, so only data overrides change.
DERIVED = {"isSeeded": (("repeatableOutput", "TRUE", "TRUE"), ("repeatableOutput", "FALSE", "FALSE")),
           "replaceCardIssuer": (("keepCardIssuer", "TRUE", "FALSE"), ("keepCardIssuer", "FALSE", "TRUE"))}
EXCLUSIVE = (("useRange", "useBlurring"),)
INACTIVE_FALSE = frozenset(["dictionaryOptimization", "isUnique"])

# Platform type (entry "pc") -> rule field class, and the default precision/scale of a rule on such a field (the
# designer copies the field's own: ui_js addDataMaskingRules sets precision / scale / pcType from the port).
PC_CLASS = {"string": "string", "nstring": "string", "text": "string", "ntext": "string", "date/time": "date",
            "decimal": "numeric", "double": "numeric", "bigint": "numeric", "integer": "numeric", "real": "numeric", "small integer": "numeric"}
PC_DEFAULTS = {"string": (256, 0), "nstring": (256, 0), "text": (256, 0), "ntext": (256, 0), "date/time": (29, 9), "decimal": (28, 9),
               "double": (15, 0), "bigint": (19, 0), "integer": (10, 0), "real": (7, 0), "small integer": (5, 0)}
PC_TYPE = {"string": "STRING", "nstring": "STRING", "text": "STRING", "ntext": "STRING", "date/time": "TIMESTAMP", "decimal": "NUMERIC",
           "double": "FLOAT", "bigint": "INTEGER", "integer": "INT32"}

PASSTHROUGH_SUFFIX = "_passthrough"
_PENDING = weakref.WeakKeyDictionary()   # build ctx -> [(masking node, TmplDmo, its OutputGroup)] waiting for the hook
_ANALYSES = weakref.WeakKeyDictionary()  # build ctx -> field flow of the spec being built (the masked fields' types)


def _err(msg):
    from ..spec import SpecError
    return SpecError(msg)


def _platform(t):
    """The platform type of a spec field TYPE (TIMESTAMP -> date/time), None when the type is unknown."""
    ti = TYPES.get(t) if isinstance(t, str) else None
    return ti[0] if ti else None


def _carries(t, pc):
    """True when a port of spec TYPE ``t`` carries the precision/scale of a rule of platform type ``pc``."""
    p = _platform(t)
    return p == pc or (PC_CLASS.get(p) == "string" and PC_CLASS.get(pc) == "string")


def passthrough_value(nd):
    """The node's "passthrough": True, False, or the field list. A boolean spelling (true / false, "true" / "false" in
    any case, 0 / 1; null or absent = false) is that boolean; SpecError for anything else."""
    pt = nd.get("passthrough")
    if isinstance(pt, (list, tuple)):
        return pt
    if values.is_flag(pt):
        return values.as_flag(pt, "")
    raise _err("masking %r: passthrough must be true, false (also \"true\" / \"false\" in any case, or 0 / 1) or a list of "
               "fields (got %r)" % (nd.get("name"), pt))


def check_passthrough_value(nd):
    """SpecError unless "passthrough" is absent, a boolean (passthrough_value) or a list."""
    passthrough_value(nd)


def field_type(nd, inc, field):
    """The spec TYPE of the field a masking entry masks, None when unknown: the field flow's (``inc``: the fields arriving
    at the masking node), else a typed passthrough entry's ([name, TYPE, ...], for an upstream that cannot be derived)."""
    f = inc.find(field) if inc is not None and isinstance(field, str) else None
    if f is not None and f.type:
        return f.type
    pt = nd.get("passthrough")
    if isinstance(pt, (list, tuple)) and isinstance(field, str):
        for it in pt:
            if isinstance(it, (list, tuple)) and len(it) > 1 and isinstance(it[0], str) and it[0].lower() == field.lower():
                return it[1] if isinstance(it[1], str) else None
    return None


def entry_pc(nd, e, ftype=None):
    """The rule's data type (DmoTxField pcType): the entry's ``pc``, else the platform type of the masked field (spec TYPE
    ``ftype``; the designer takes it from the field), else string. A pc that contradicts the field's known type is
    refused: the rule and the port would disagree (a string rule of precision 256 on a bigint port)."""
    want = _platform(ftype)
    pc = e.get("pc")
    if pc is None:
        return want or "string"
    if not isinstance(pc, str) or pc not in PC_CLASS:
        raise _err("masking %r entry %r: pc %r is not a platform type (known: %s)" % (nd.get("name"), e.get("field"), pc, ", ".join(PC_CLASS)))
    if want and pc != want:
        raise _err("masking %r entry %r: pc %r, but the field arrives as %s (platform type %s), and a rule's data type is its "
                   "field's: leave pc out or give %r" % (nd.get("name"), e.get("field"), pc, ftype, want, want))
    return pc


def entry_precision(e, pc=None, node=None):
    """(precision, scale) of a masking entry: its prec/scale (null = not given), else the defaults the designer copies
    from a field of platform type ``pc`` (default: the entry's pc). Whole numbers, the scale not above the precision."""
    pc = pc if pc is not None else e.get("pc") or "string"
    where = ("masking %r entry %r" % (node, e.get("field"))) if node else ("masking entry %r" % (e.get("field"),))
    if not isinstance(pc, str) or pc not in PC_DEFAULTS:
        raise _err("%s: pc %r is not a platform type (known: %s)" % (where, pc, ", ".join(PC_DEFAULTS)))
    dp, ds = PC_DEFAULTS[pc]
    prec = values.as_whole(e.get("prec"), "%s: prec" % where, 1, dp, "the rule's default")     # the rule of every
    scale = values.as_whole(e.get("scale"), "%s: scale" % where, 0, ds, "the rule's default")  # field list (values.py)
    if scale > prec:
        raise _err("%s: scale %d is larger than the precision %d%s" % (where, scale, prec, "" if e.get("scale") is not None else
                                                                        " (%d is the default scale of a %s field: give \"scale\")" % (ds, pc)))
    return prec, scale


def entry_params(nd, e, pc=None):
    """(maskingType label, [(param, value)]) of one entry, as the designer writes it (``pc``: the rule's data type,
    default the entry's)."""
    t, pc = e["type"], (pc if pc is not None else e.get("pc", "string"))
    # parameter values are text (the designer writes "TRUE", "190"): a number becomes its text, null = the default
    data = {k: values.as_text(v, "masking %r entry %r: data %r" % (nd["name"], e["field"], k), what="a parameter value")
            for k, v in (e.get("data") or {}).items() if v is not None}
    cls = PC_CLASS.get(pc)
    if cls is None:
        raise _err("masking %r entry %r: pc %r is not a platform type (known: %s)" % (nd["name"], e["field"], pc, ", ".join(PC_CLASS)))
    if t == "Email address" and str(data.get("isEmailAdvanced", "")).upper() == "TRUE":
        t = "Email Advanced"
    rules = CATALOGUE.get(t)
    if rules is None:
        raise _err("masking %r entry %r: unknown masking type %r (known: %s)" % (nd["name"], e["field"], e["type"], ", ".join(MASKING_TYPES)))
    params = rules.get(cls)
    if params is None:
        raise _err("masking %r entry %r: type %r does not apply to %s fields (pc %r); it applies to %s fields"
                   % (nd["name"], e["field"], e["type"], cls, pc, " / ".join(sorted(rules))))
    preset = PRESET.get(t, {}) if cls == "string" else {}  # the designer's values for the five preset types
    known = {p for p, _, _, _ in params}
    value = {p: data.get(p, preset.get(p, d)) for p, d, _, _ in params}
    for a, b in EXCLUSIVE:          # data turns one switch on or off: the dialog sets the other to the opposite
        for one, other in ((a, b), (b, a)):
            if one in data and other not in data and other in value:
                value[other] = "FALSE" if str(data[one]).upper() == "TRUE" else "TRUE"
    for p, rel in DERIVED.items():  # a derived parameter follows its related one (unless data gives it)
        if p in value and p not in data:
            for rp, rv, dv in rel:
                if rp in value and str(value[rp]).upper() == rv:
                    value[p] = dv
                    break
    out, missing = [], []
    for p, d, act, mand in params:
        v = value[p]
        active = True
        if act:
            # case-insensitive, like the isEmailAdvanced switch above: data {"repeatableOutput": "true"} keeps the
            # seed (blanking it would leave a repeatable rule without a seed if the runtime reads "true" as TRUE)
            ap, av = act.split("=")
            active = str(value.get(ap, "")).upper() == av.upper()
        if not active and p not in data:
            v = "FALSE" if p in INACTIVE_FALSE else ""      # the designer writes inactive parameters empty (BOOL: FALSE)
        if mand and d == "" and active and v == "" and p not in missing:
            missing.append(p)
        out.append((p, v))
    if missing:
        raise _err("masking %r entry %r: type %r needs data %s (mandatory, no default)" % (nd["name"], e["field"], e["type"],
                                                                                         ", ".join(missing)))
    out += [(k, v) for k, v in data.items() if k not in known]
    return IMF_TYPE.get(t, t), out


def resolve_entry(nd, e, ftype=None):
    """One masking entry as build() writes it: (maskingType label, pc, precision, scale, [(param, value)]). ``ftype``: the
    spec TYPE of the masked field (field_type). SpecError for an entry the designer could not have built."""
    if not (isinstance(e, dict) and isinstance(e.get("field"), str) and e["field"] and isinstance(e.get("type"), str)
            and isinstance(e.get("data") or {}, dict)):
        raise _err("masking %r: an entry is {\"field\": name, \"type\": technique, \"pc\"?, \"prec\"?, \"scale\"?, \"data\"?: "
                   "{param: value}} (got %r)" % (nd.get("name"), e))
    pc = entry_pc(nd, e, ftype)
    prec, scale = entry_precision(e, pc, nd.get("name"))
    label, params = entry_params(nd, e, pc)
    return label, pc, prec, scale, params


def check_one_entry_per_field(nd):
    """SpecError when two entries mask the same field (any case): the designer gives a port one masking rule."""
    seen = set()
    for e in nd.get("entries") or []:
        f = e.get("field") if isinstance(e, dict) else None
        if isinstance(f, str) and f:
            if f.lower() in seen:
                raise _err("masking %r: field %r has two entries (a field takes one masking rule)" % (nd.get("name"), f))
            seen.add(f.lower())


def _incoming(ctx, name):
    """The fields arriving at node ``name`` in the spec being built (one field flow per build), None if not derivable."""
    try:
        an = _ANALYSES.get(ctx)
        if an is None:
            from .. import fieldflow
            an = _ANALYSES[ctx] = fieldflow.Analysis(ctx.spec)
        return an.incoming(name)
    except Exception:       # a spec the field flow cannot follow: the entries keep their own pc (or string)
        return None


@node("masking", doc="entries: [{field, type (a catalogue technique: 'Email address', 'Phone', 'SSN', 'Credit card', 'Key', "
                     "'Random', 'Substitution name', ...), pc? (the rule's data type, default the field's platform type), "
                     "prec?, scale?, data: {param: value}}]; outputs out_<field> for every incoming field; passthrough: true "
                     "(or a field list) also delivers the incoming fields under their own names (masked ones masked) "
                     "through an added <name>_passthrough expression.")
def build(ctx, nd):
    b = ctx.b; name = nd["name"]
    gi = b.group("InputGroup", True, False); go = b.group("OutputGroup", False, True, rule=False)
    pt = passthrough_value(nd)
    check_one_entry_per_field(nd)
    inc = _incoming(ctx, name)
    ents = []
    for e in nd["entries"]:
        mtype, pc, prec, scale, md = resolve_entry(nd, e, field_type(nd, inc, e.get("field") if isinstance(e, dict) else None))
        ents.append(b.new("DmoTxField", label="", maskingType=mtype, pcType=pc, precision=str(prec),
                          referenceField=e["field"], scale=str(scale), maskingData=[b.new("MaskingData", data=v, param=k) for k, v in md]))
    tx = b.new("TmplDmo", augmented="false", createTime=ctx.now, name=name, groups=[gi, go], dmoMode="SIMPLE", locale="en_US", parameterized="",
               maskingEntries=ents)
    ctx.out(name, go); ctx.inp(name, gi)
    if pt:
        _PENDING.setdefault(ctx, []).append((nd, tx, go))
    return tx


# --------------------------------------------------------------------------------------------- passthrough
def _declared(nodes, f):
    """(precision, scale) where field ``f`` was declared (its origin node, same name), None for unknown parts."""
    nd = nodes.get(f.origin) or {}
    for fd in nd.get("fields") or []:
        if isinstance(fd, (list, tuple)) and fd and str(fd[0]).lower() == f.name.lower():
            return (fd[2] if len(fd) > 2 else None), (fd[4] if len(fd) > 4 else None)
        if isinstance(fd, dict) and str(fd.get("name", "")).lower() == f.name.lower():
            return fd.get("prec"), fd.get("scale")
    return None, None


def passthrough_fields(spec, nd, analysis=None):
    """[(name, TYPE, precision, scale)] the passthrough expression of masking node ``nd`` restores."""
    from .. import fieldflow
    pt = passthrough_value(nd)
    name = nd["name"]
    an = analysis or fieldflow.Analysis(spec)
    inc = an.incoming(name)
    nodes = {n.get("name"): n for n in spec.get("nodes") or [] if isinstance(n, dict)}
    masked = {e["field"].lower(): e for e in nd.get("entries") or [] if isinstance(e, dict) and isinstance(e.get("field"), str)}
    if pt is False:
        return []
    if pt is True:
        if inc.unchecked:
            raise _err("masking %r: passthrough needs the incoming fields, and an upstream node's fields cannot be derived; list "
                       "them: \"passthrough\": [[name, TYPE, prec?, scale?], ...]" % name)
        items = [(f.name, None) for f in inc]
    else:
        items = []
        for it in pt:
            if isinstance(it, str) and it:
                items.append((it, None))
            elif isinstance(it, (list, tuple)) and it and isinstance(it[0], str) and it[0]:
                items.append((it[0], list(it[1:]) or None))
            else:
                raise _err("masking %r: passthrough entries are a field name or [name, TYPE, prec?, scale?] (got %r)" % (name, it))
    out = []
    for fname, decl in items:
        f = inc.find(fname)
        e = masked.get(fname.lower())
        pc = entry_pc(nd, e, field_type(nd, inc, e["field"])) if e is not None else None   # the masked field's rule type
        if decl:
            if f is None and not inc.unchecked:
                # the incoming fields are known and this one is not among them: the Data Masking emits no out_<field>
                # for it, so <field> = out_<field> would be an invalid symbol reference at run time (TE_7002). A type
                # only stands in for fields that cannot be derived (a generic node upstream).
                raise _err("masking %r: passthrough field %r does not arrive (incoming: %s)" % (name, fname, ", ".join(inc.names()) or "none"))
            t = decl[0]
            typeinfo(t)
            prec, scale = (decl[1] if len(decl) > 1 else None), (decl[2] if len(decl) > 2 else None)
            at = "masking %r: passthrough field %r" % (name, fname)              # as a masking entry's prec / scale
            prec = values.as_whole(prec, at + ": precision", 1, None, "the default")
            scale = values.as_whole(scale, at + ": scale", 0, None, "the default")
            if e is not None and _carries(t, pc):           # a masked field: its out_ port has the entry's precision
                ep, es = entry_precision(e, pc, name)       # (a declared type of another kind keeps its own default)
                prec, scale = (ep if prec is None else prec), (es if scale is None else scale)
            if f is not None:
                fname = f.name                              # the incoming spelling (port names are case-insensitive)
        else:
            if f is None:
                if inc.unchecked:
                    raise _err("masking %r: passthrough field %r: the incoming fields cannot be derived; give its type: "
                               "[%r, TYPE, prec?]" % (name, fname, fname))
                raise _err("masking %r: passthrough field %r does not arrive (incoming: %s)" % (name, fname, ", ".join(inc.names()) or "none"))
            t = f.type or (PC_TYPE.get(pc) if e is not None else None)
            if not t:
                raise _err("masking %r: passthrough field %r has no known type; give it: [%r, TYPE, prec?]" % (name, f.name, f.name))
            typeinfo(t)
            if e is not None:
                prec, scale = entry_precision(e, pc, name) if _carries(t, pc) else (None, None)
            else:
                prec, scale = _declared(nodes, f)
            fname = f.name
        _, dprec, dscale, _ = TYPES[t]
        given_scale = scale is not None
        prec, scale = (dprec if prec is None else prec), (dscale if scale is None else scale)
        if decl and scale > prec:
            raise _err("masking %r: passthrough field %r: scale %d is larger than the precision %d%s" % (
                name, fname, scale, prec, "" if given_scale else " (%d is the default scale of %s: give the scale)" % (dscale, t)))
        out.append((fname, t, prec, scale))
    seen, dups = set(), []
    for n, _, _, _ in out:
        if n.lower() in seen:
            dups.append(n)
        seen.add(n.lower())
    if dups:
        raise _err("masking %r: passthrough lists %s twice" % (name, ", ".join(dups)))
    outs = {"out_" + n.lower() for n in seen | {f.name.lower() for f in inc}}
    clash = [n for n, _, _, _ in out if n.lower() in outs]
    if clash:
        raise _err("masking %r: passthrough would restore %s, which is also the name of a masking output (out_<field>); rename "
                   "the incoming field(s) or list the passthrough fields without them" % (name, ", ".join(clash)))
    return out


@template_hook
def add_passthrough_expressions(ctx, content):
    """After the links exist: put the name-restoring Expression after each passthrough masking node and move the
    masking node's outgoing links onto it."""
    pending = _PENDING.pop(ctx, None)
    if not pending:
        return
    from .expression import build as build_expression
    b = ctx.b
    links, txl = content["links"], content["transformations"]
    names = {t.get("name") for t in txl} | {n.get("name") for n in ctx.spec.get("nodes") or [] if isinstance(n, dict)}
    analysis = None
    for nd, dmo, go in pending:
        leaving = [lk for lk in links if lk["fromGroup"]["##ID"] == go["$$ID"]]
        if not leaving:
            continue                                        # nothing downstream needs the names
        aname = nd["name"] + PASSTHROUGH_SUFFIX
        if aname in names:
            raise _err("masking %r: passthrough adds an expression named %r, which is already a node name" % (nd["name"], aname))
        if analysis is None:
            from .. import fieldflow
            analysis = fieldflow.Analysis(ctx.spec)
        restored = passthrough_fields(ctx.spec, nd, analysis)
        if not restored:
            continue
        anchor = build_expression(ctx, {"type": "expression", "name": aname,
                                        "fields": [{"name": n, "type": t, "expr": "out_" + n, "kind": "OUTPUT", "prec": p, "scale": s}
                                                   for n, t, p, s in restored]})
        names.add(aname)
        ag = anchor["groups"][0]
        txl.insert(txl.index(dmo) + 1, anchor)
        first = links.index(leaving[0])
        for lk in leaving:
            lk["name"] = aname + ".Edge"
            lk["fromGroup"] = b.ref(ag)
            lk["fromTransformation"] = b.ref(anchor)
        links.insert(first, b.new("TmplLink", name=nd["name"] + ".Edge", fromGroup=b.ref(go), fromTransformation=b.ref(dmo),
                                  toGroup=b.ref(ag), toTransformation=b.ref(anchor)))


# --------------------------------------------------------------------------------------------- lint
def lint_problems(spec, nd, analysis, conns=None):
    """[(lint code, message)] for what the build refuses in this masking node, found by running the build's own rules
    (so lint and the compiler cannot disagree): an entry (MSK_TYPE: unknown technique, a pc the field contradicts or the
    technique does not apply to, a bad precision/scale, mandatory data missing) and a passthrough value (MSK_FIELD)."""
    from ..spec import SpecError
    name = nd.get("name")
    inc = analysis.incoming(name)
    out = []
    for e in nd.get("entries") or []:
        try:
            resolve_entry(nd, e, field_type(nd, inc, e.get("field") if isinstance(e, dict) else None))
        except SpecError as err:
            out.append(("MSK_TYPE", str(err)))
    try:
        check_one_entry_per_field(nd)
    except SpecError as err:
        out.append(("MSK_TYPE", str(err)))
    try:
        if passthrough_value(nd) and analysis.out_links.get(name) and not out:     # what the hook does when links leave
            aname = name + PASSTHROUGH_SUFFIX
            if aname in analysis.nodes:
                raise _err("masking %r: passthrough adds an expression named %r, which is already a node name" % (name, aname))
            passthrough_fields(spec, nd, analysis)
    except SpecError as err:
        out.append(("MSK_FIELD", str(err)))
    return out


# --------------------------------------------------------------------------------------------- field flow (lint)
def _flow():
    """The field rule lint uses, matching what build() delivers: out_<field> for every incoming field, plus the fields
    the passthrough expression restores -- every incoming field for "passthrough": true, only the listed ones for a
    list. (The generic rule in fieldflow.py lets every original through for any passthrough value, so a downstream use
    of a field the list does not restore linted clean and failed at run time with TE_7002.)"""
    try:
        from ..fieldflow import F, fields, flow
    except ImportError:
        return

    @flow("masking", override=True)
    def _masking(nd, inputs):
        inp = inputs.get(nd["name"])
        unchecked = bool(getattr(inp, "unchecked", False))
        inp = fields(inp or (), unchecked)
        outs = [F("out_" + f.name, f.type, nd["name"]) for f in inp]
        pt = nd.get("passthrough")
        if values.is_flag(pt):
            pt = values.as_flag(pt, "")     # "true" / 1 ... as build reads them (build refuses other values: MSK_FIELD)
        base = []
        if pt is True:
            base = list(inp)
        elif isinstance(pt, (list, tuple)):
            for it in pt:
                name = it if isinstance(it, str) else (it[0] if isinstance(it, (list, tuple)) and it and isinstance(it[0], str) else None)
                if not name:
                    continue                                # build() refuses the entry
                typ = it[1] if isinstance(it, (list, tuple)) and len(it) > 1 else None
                f = inp.find(name)
                if f is not None:
                    base.append(F(f.name, typ or f.type, f.origin, f.flags))
                elif unchecked:                             # the upstream fields are unknown: it may arrive
                    base.append(F(name, typ, nd["name"]))   # (a known upstream without it: build() refuses the entry)
        low = {f.name.lower() for f in outs}
        return {"": fields([f for f in base if f.name.lower() not in low] + outs, unchecked)}


_flow()


# Every node key this builder reads besides type/name/set/advanced (lint warns UNKNOWN_OPTION on any other key).
build.options = frozenset(['entries', 'passthrough'])
