"""IMF object builder: sequential $$ID objects, class ids, references, groups and adapter/tx field lists.

IMF ("Informatica Metadata Framework") JSON is what a mapping's ``bin/@2.bin`` holds. Every object is a dict with
``$$ID`` (unique, sequential) and ``$$class`` (a small integer resolved through ``metadata.$$classInfo``);
references to another object are ``{"##ID": <id>, "$$class": <class>}``.
"""
import calendar
import datetime
import json
import re
import time

from .types import CLS, PLATFORM_TYPE_SID, typeinfo

FQ_CLASS = re.compile(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+\Z")   # a fully qualified Java class name


def _spec_error(msg):
    from .spec import SpecError
    return SpecError(msg)


class B:
    """One builder per mapping.

    Class ids ($$class) are given out per FULLY QUALIFIED class, in order of first use, so two classes with the same
    simple name (common.field.FieldMapping and tmpltarget.FieldMapping) can both appear in one mapping.
    ``fq`` maps the short names the builders use to their class: a copy of types.CLS plus what register() adds.
    A short name never changes meaning within a build. c() / new() also take any fully qualified name directly.
    """

    def __init__(self):
        self.n = 0
        self.cls = {}          # fully qualified class -> class id
        self.fq = dict(CLS)    # short name -> fully qualified class

    def fqn(self, k):
        """The fully qualified class of a short name or of a fully qualified name (returned as is)."""
        if "." in k:
            return k
        if k not in self.fq:
            raise _spec_error("IMF class %r has no fully qualified name (add it to types.CLS or use a generic node)" % k)
        return self.fq[k]

    def c(self, k):
        f = self.fqn(k)
        if f not in self.cls:
            self.cls[f] = len(self.cls) + 1
        return self.cls[f]

    def register(self, fq_name):
        """Make a fully qualified class usable by its short name; returns the short name.

        Raises SpecError when that short name already means another class in this build (a core class or one
        registered earlier): the short name keeps its meaning, so use the fully qualified name with new() / c()."""
        if not isinstance(fq_name, str) or not FQ_CLASS.match(fq_name):
            raise _spec_error("IMF class %r is not a fully qualified Java class name (e.g. %s)" % (fq_name, CLS["TmplFilter"]))
        short = fq_name.rsplit(".", 1)[1]
        have = self.fq.setdefault(short, fq_name)
        if have != fq_name:
            raise _spec_error("IMF class %s: its short name %r already means %s in this mapping; use the fully "
                              "qualified name with new()/c() instead of registering it" % (fq_name, short, have))
        return short

    def new(self, k, **kw):
        self.n += 1
        d = {"$$ID": self.n, "$$class": self.c(k)}
        d.update(kw)
        return d

    def ref(self, o):
        return {"##ID": o["$$ID"], "$$class": o["$$class"]}

    def ptype(self, t):
        return {"##SID": PLATFORM_TYPE_SID + typeinfo(t)[0], "$$class": self.c("DataType")}

    def adv(self, pairs):
        return [self.new("TxAdvancedProperty", name=k, value=v) for k, v in pairs]

    def group(self, name, inp, out, rule=True):
        g = self.new("TmplGroup", input=str(inp).lower(), name=name, output=str(out).lower())
        if rule and inp:
            g["rules"] = [self.new("TmplAllRule", bulkRename="false", include="true")]
        return g

    def class_info(self):
        return {str(v): k for k, v in self.cls.items()}


def now_iso(now=None):
    """createTime stamp: None = current UTC time, a number = epoch seconds, a string = used verbatim."""
    if isinstance(now, str):
        return now
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime() if now is None else time.gmtime(now))


def epoch_ms(now=None):
    """The package timestamp (epoch milliseconds) for the same ``now`` that build() takes: None = None (the packager
    uses the current time), a number = epoch seconds, a string = an ISO timestamp like createTime
    ("2026-10-03T00:00:00.000Z"; no zone = UTC)."""
    if now is None:
        return None
    if not isinstance(now, str):
        return int(now * 1000)
    s = now.strip()
    try:
        dt = datetime.datetime.fromisoformat(s[:-1] + "+00:00" if s[-1:] in ("Z", "z") else s)
    except ValueError:
        raise _spec_error("now %r is not epoch seconds or an ISO timestamp (YYYY-MM-DDTHH:MM:SS[.fff]Z)" % now) from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return calendar.timegm(dt.utctimetuple()) * 1000 + dt.microsecond // 1000


# connector flags of an adapter field tuple (fd[5]) and their defaults
FIELD_FLAGS = (("createable", False), ("externalId", False), ("nullable", True), ("sfIdLookup", False), ("unique", False),
               ("updateable", True))
_TUPLE_HOW = "[name, TYPE, precision, nativeType, scale]; nativeType null = TYPE"


def field_tuple(fd, i=0):
    """(name, TYPE, precision, scale, nativeType, {flag: bool}) of an adapter field tuple
    [name, TYPE, precision?, nativeType?, scale?, {connector flags}?]: null precision / nativeType / scale / flags = the
    default (the type's; nativeType = TYPE; no flags). The name and nativeType are text, precision and scale whole
    numbers (values.precision_scale: the scale may not exceed the precision, so a NUMERIC precision below 9 needs its
    scale), the flags an object of FIELD_FLAGS booleans (values.as_flag). SpecError otherwise (a tuple without a TYPE
    stays the IndexError the build reports with the node's name)."""
    from . import values
    name = values.as_text(fd[0], "field #%d name" % (i + 1), what="a field name")
    where = "field %r" % name
    t = fd[1]
    prec, sc = values.precision_scale(t, fd[2] if len(fd) > 2 else None, fd[4] if len(fd) > 4 else None, where, _TUPLE_HOW)
    nt = values.as_text(fd[3] if len(fd) > 3 else None, where + " nativeType", t, what="a native type name")
    fx = fd[5] if len(fd) > 5 and fd[5] is not None else {}
    known = [k for k, _ in FIELD_FLAGS]
    if not isinstance(fx, dict) or any(k not in known for k in fx):
        raise _spec_error("%s: the 6th item (connector flags) must be an object {flag: true | false} of %s, got %s"
                          % (where, ", ".join(known), values.brief(fx)))     # (any other value was ignored silently)
    flags = {k: values.as_flag(fx.get(k), "%s flag %s" % (where, k), dflt) for k, dflt in FIELD_FLAGS}
    return name, t, prec, sc, nt, flags


def adapter_fields(b, fields, parent, keys=()):
    """BaseAdapterField list for a source/target/lookup data object.

    Field tuple: [name, TYPE, precision?, nativeType?, scale?, {connector flags}?] (see field_tuple).
    flags (Salesforce and other SaaS targets): createable, externalId, nullable, sfIdLookup, unique, updateable
    (true / false, "true" / "false" in any case, 0 / 1; written "true" / "false").
    ``keys``: field names flagged key="true" (a target's updateColumns).
    """
    from .values import imf_bool
    out = []
    for i, fd in enumerate(fields):
        name, t, prec, sc, nt, fx = field_tuple(fd, i)
        jt = typeinfo(t)[3]
        out.append(b.new("BaseAdapterField", name=name, annotations=[b.new("Description", body="")], createable=imf_bool(fx["createable"]),
                         externalId=imf_bool(fx["externalId"]), fieldStatus="ORIGINAL", fieldType="CONNECTOR", filterable="true", foreignKey="false",
                         generated="false", javaType=jt, key="true" if name in keys else "false", label=name, nativeName=name, nativeType=nt, newField="false",
                         nullable=imf_bool(fx["nullable"]), original="false", passthroughPort="false", precision=prec, scale=sc, sfIdLookup=imf_bool(fx["sfIdLookup"]),
                         unique=imf_bool(fx["unique"]), updateable=imf_bool(fx["updateable"]),
                         metaExtensions=[b.new("Option", name="isPartitionKey", value="false")],
                         properties=[b.new("Option", name="parentObject", value=parent), b.new("Option", name="parentObjectLabel", value="")]))
    return out


def tx_fields(b, fields, afs):
    """TxField list bound one-to-one to the adapter fields."""
    out = []
    for i, (fd, af) in enumerate(zip(fields, afs)):
        name, t, prec, sc, _, _ = field_tuple(fd, i)
        out.append(b.new("TxField", adapterField=b.ref(af), defaultValue="", ignoreComparison="false", ignoreNullInputs="false",
                         isDefaultValueUpdated="false", name=name, platformType=b.ptype(t), precision=prec, scale=sc))
    return out


def read_options(b, filter_condition=""):
    """``filter_condition``: the source's own filter (Salesforce: a SOQL WHERE condition such as IsLatest = true)."""
    return b.new("ReadOptions", commandType=0, descending="false", filterCondition=filter_condition, flatFileCommand="",
                 queryAll="false", rowLimit=0, selectDistinct="false", userDefinedJoin="",
                 advancedFilterCondition="", requestXml="", sortFieldValues="")


def imf_bytes(imf):
    """The exact bytes stored as bin/@2.bin (compact JSON, ASCII)."""
    return json.dumps(imf, separators=(",", ":")).encode()
