"""mbr_cai.py - offline generator for hand-built CAI import packages (generic; standard library only).

Builds repository-item XML for service connectors (REST), app connections (REST, Kafka, AMQP 1.0 / JMS) and processes,
and wraps them in a v3 import package:
    Explore/<project>.Project.json, Explore/<project>/<folder>.Folder.json,
    Explore/<project>/<folder>/<name>.<TYPE>.xml, exportMetadata.v2.json, exportPackage.chksum, a contents CSV.
PROVEN in an earlier form (2026-10: 21 production CAI assets imported OVERWRITE and published from packages built this
way); ADAPTED here: names, config-driven values, and the FRS Project/Folder JSON is built from the target org's own
FRS records (state/frs.json written by deploy_cai.py) instead of a copied template.

No secrets: the AMQP password is authored encrypted="true" with an EMPTY value and set afterwards with
PUT /active-bpel/asset/v1/update (deploy_cai.py set-secret, L-CAI-132).
GUIDs persist in state/guids.json so every rebuild OVERWRITEs the same objects (an import never changes identity).
"""
from __future__ import annotations

import datetime
import hashlib
import html
import io
import json
import os
import secrets
import string
import uuid
import zipfile
from xml.dom import minidom  # nosec B408  # parses only safe_xml_bytes-checked XML  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml

E = lambda s: html.escape(str(s), quote=True)  # noqa: E731

MIME = {"AI_SERVICE_CONNECTOR": "application/xml+businesssconnector", "AI_CONNECTION": "application/xml+connection",
        "PROCESS": "application/xml+process"}
NS_SF = "http://schemas.active-endpoints.com/appmodules/screenflow/2010/10/avosScreenflow.xsd"
NS_CONN = "http://schemas.informatica.com/socrates/data-services/2014/04/avosConnections.xsd"
NS_CTR = "http://schemas.informatica.com/appmodules/screenflow/2014/04/avosConnectors.xsd"
NS_BC = "http://schemas.informatica.com/socrates/data-services/2014/05/business-connector-model.xsd"
NS_REPO = "http://schemas.active-endpoints.com/appmodules/repository/2010/10/avrepository.xsd"
# vendor connector type ids (the same in every org; from genuine exports, KB L-CAI-116)
KAFKA_UUID = "c5d3f9bc-95ba-48e6-99df-5bca133b44b3"
AMQP_UUID = "59b13626-0180-4d48-a749-38f8f33f7b18"


def safe_xml_bytes(data):
    """Refuse XML that declares a DTD or entities (XXE / entity expansion); returns the bytes unchanged."""
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    low = raw.lower()
    if b"<!doctype" in low or b"<!entity" in low:
        raise ValueError("XML with a DTD or entity declaration is refused")
    return raw


# ------------------------------------------------------------------ GUID store
class Guids:
    """22-char object GUIDs and service-connector UUIDs, persisted so rebuilds keep identity."""

    def __init__(self, path):
        self.path = path
        self.d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.d, f, indent=1, sort_keys=True)

    def guid(self, key):
        if key not in self.d:
            a = string.ascii_letters + string.digits
            self.d[key] = "".join(secrets.choice(a) for _ in range(22))
            self._save()
        return self.d[key]

    def sc_uuid(self, key):
        k = "uuid:" + key
        if k not in self.d:
            self.d[k] = str(uuid.uuid4())
            self._save()
        return self.d[k]


# ------------------------------------------------------------------ repository item wrapper
def item(name, typ, desc, gid, entry):
    return (f'<aetgt:getResponse xmlns:aetgt="{NS_REPO}" xmlns:types1="{NS_REPO}">'
            f"<types1:Item><types1:Name>{E(name)}</types1:Name><types1:MimeType>{MIME[typ]}</types1:MimeType>"
            f"<types1:Description>{E(desc)}</types1:Description><types1:AppliesTo/><types1:Tags/>"
            f"<types1:VersionLabel>1.0</types1:VersionLabel><types1:State>CURRENT</types1:State><types1:ProcessGroup/>"
            f"<types1:Entry>{entry}</types1:Entry><types1:GUID>{gid}</types1:GUID>"
            f"<types1:DisplayName>{E(name)}</types1:DisplayName></types1:Item></aetgt:getResponse>\n")


# ------------------------------------------------------------------ REST service connector
MA = '<mutualAuth enabled="false"><keyStore mode="file"/><keyStorePassword/></mutualAuth>'


def url_amp(url):
    """A restSimpleBinding url is evaluated as an XQuery template: between query parameters it needs '&amp;' AFTER
    XML parsing, i.e. '&amp;amp;' in the file (L-CAI-145). E() escapes once more, so pre-escape here."""
    return url.replace("&", "&amp;")


def action(name, verb, url, params=(), body=None, outputs=(), fail_on_error=False, desc="", timeout=None, headers=None):
    """One REST action. params: input names used as {$name} in url/body; body: literal template or None;
    outputs: [(name, kind, prop)] with kind property | status | entire;
    timeout: requestTimeout in SECONDS (L-CAI-128); fail_on_error False returns the HTTP status as data (L-CAI-129)."""
    ins = "".join(f'<parameter name="{p}" nogen="true" required="false" type="string"/>' for p in params)
    hdr = '<header name="Accept">application/json</header>'
    for k, v in (headers or {}).items():
        hdr += f'<header name="{E(k)}">{E(v)}</header>'
    b = ""
    if body is not None:
        hdr = '<header name="Content-Type">application/json</header>' + hdr
        b = f"<body>{E(body)}</body>"
    outs = []
    for n, kind, prop in outputs:
        if kind == "status":
            outs.append(f'<field description="" name="{n}" responseStatusCode="true" type="string"/>')
        elif kind == "entire":
            outs.append(f'<field description="" entireResponse="true" name="{n}" type="string"/>')
        else:
            outs.append(f'<field description="" name="{n}" property="{prop or n}" type="string"/>')
    to = f' requestTimeout="{int(timeout)}"' if timeout else ""
    return (f'<action category="" failOnError="{str(fail_on_error).lower()}" forSearch="false" label="{name}" maxRedirects="100" '
            f'name="{name}" preemptiveAuth="true" responseEncoding=""{to}><description>{E(desc)}</description>'
            f"<input>{ins}</input><binding><restSimpleBinding multiUsing=\"semicolonSeparated\" url=\"{E(url_amp(url))}\" verb=\"{verb}\">"
            f"{MA}<httpHeaders>{hdr}</httpHeaders>{b}</restSimpleBinding></binding>"
            f"<output>{''.join(outs)}</output></action>")


def service_connector(g: Guids, name, desc, actions, base_test):
    return (f'<businessConnector xmlns="{NS_BC}" agentOnly="false" debug="false" displayName="{name}" label="" name="{name}" '
            f'uuid="{g.sc_uuid(name)}"><description>{E(desc)}</description><tags/>'
            f'<connectionAttributes xmlns="{NS_CTR}"><connectionAttribute description="base URL" label="base_url" masked="false" '
            f'name="base_url" required="true" testWith="{E(base_test)}" type="string"/></connectionAttributes>'
            f"<actions>{''.join(actions)}</actions><objects/></businessConnector>")


# ------------------------------------------------------------------ app connections
def _attrs(d):
    return "".join(f'<attribute name="{E(k)}" value="{E(v)}"/>' for k, v in d.items())


def rest_connection(g: Guids, name, sc_name, desc, base_url, agent):
    ag = f"<agent>{E(agent)}</agent>" if agent else "<agent/>"
    return (f'<connection xmlns="{NS_CONN}" GUID="{g.guid("AI_CONNECTION:" + name)}" displayName="{name}" label="{name}" name="{name}">'
            f"<description>{E(desc)}</description><tags/>{ag}"
            f'<attributes><attribute name="base_url" value="{E(base_url)}"/></attributes>'
            f'<businessConnector xmlns="{NS_CTR}" agentOnly="false" connectorPath="project:/rt.connector/{sc_name}/{sc_name}_svcDef.xml" '
            f'guid="{g.guid("AI_SERVICE_CONNECTOR:" + sc_name)}" name="{sc_name}" supportsConnectionTest="false" uuid="{g.sc_uuid(sc_name)}">'
            f"<description>{E(desc)}</description></businessConnector></connection>")


def kafka_connection(g: Guids, name, desc, agent, host, port, consumers=(), producers=(), additional="", common="",
                     ssl=False, sasl=False):
    """consumers: [(event_source, topic, group, other_attrs, enabled)]; producers: [(event_target, topic, other_attrs)].
    A consumer authored enabled=false starts no route on publish (safe first start, L-CAI-119)."""
    cons = "".join(
        f'<consumer enabled="{str(en).lower()}" name="{n}" typeName="KafkaConsumer"><description/><attributes>'
        + _attrs({"loadBalance": "false", "topic": t, "groupId": grp, "contentFormat": "TEXT", "simplifyContent": "false",
                  "otherAttributesProducerConsumer": o}) + "</attributes></consumer>"
        for n, t, grp, o, en in consumers)
    prods = "".join(
        f'<producer enabled="true" name="{n}" typeName="KafkaProducer"><description/><attributes>'
        + _attrs({"topic": t, "groupId": "unused", "contentFormat": "TEXT", "otherAttributesProducerConsumer": o})
        + "</attributes></producer>" for n, t, o in producers)
    return (f'<connection xmlns="{NS_CONN}" GUID="{g.guid("AI_CONNECTION:" + name)}" displayName="{name}" label="{name}" name="{name}">'
            f"<description>{E(desc)}</description><tags/><agent>{E(agent)}</agent><attributes>"
            + _attrs({"kafkaHost": host, "kafkaPort": str(port), "additionalBrokers": additional, "otherAttributesCommon": common,
                      "Use SSL": str(bool(ssl)).lower(), "Use SASL": str(bool(sasl)).lower()})
            + "</attributes>"
            + (f"<consumers>{cons}</consumers>" if cons else "") + (f"<producers>{prods}</producers>" if prods else "")
            + f'<javaConnector xmlns="{NS_CTR}" agentOnly="true" name="KAFKA" plugin="Camel" type="KAFKA" uuid="{KAFKA_UUID}">'
            f"<description>Connects to a Kafka stream to read data from or write data to a topic.</description></javaConnector></connection>")


def amqp_connection(g: Guids, name, desc, agent, host, port, user, consumers=(), query=""):
    """AMQP 1.0 (a JMS broker such as ActiveMQ Artemis). consumers: [(event_source, queue, dlq, other, enabled)].
    query = 'Query Parameters', appended to the Qpid JMS URI: jms.validatePropertyNames=false keeps JMS property names
    with hyphens (L-CAI-123). The password is authored encrypted with an EMPTY value (set later, L-CAI-132)."""
    cons = "".join(
        f'<consumer enabled="{str(en).lower()}" name="{n}" typeName="AMQP Source"><description/><attributes>'
        + _attrs({"Enable Load Balancing": "false", "Custom Message ID": "", "Destination Type": "queue", "Destination": q,
                  "Payload Format": "Text", "Objectlist Field Name": "object", "Dead Letter Queue Name": dlq,
                  "Other Attributes": o}) + "</attributes></consumer>"
        for n, q, dlq, o, en in consumers)
    return (f'<connection xmlns="{NS_CONN}" GUID="{g.guid("AI_CONNECTION:" + name)}" displayName="{name}" label="{name}" name="{name}">'
            f"<description>{E(desc)}</description><tags/><agent>{E(agent)}</agent><attributes>"
            f'<attribute name="User Name" value="{E(user)}"/><attribute encrypted="true" name="Password" value=""/>'
            + _attrs({"Virtual Host": "", "Host": host, "Port": str(port), "Use SSL": "false", "Query Parameters": query})
            + "</attributes>" + (f"<consumers>{cons}</consumers>" if cons else "")
            + f'<javaConnector xmlns="{NS_CTR}" agentOnly="true" name="AMQP" plugin="Camel" type="AMQP" uuid="{AMQP_UUID}">'
            f"<description>Connects to an AMQP stream to send messages to a queue or delete messages from a queue.</description>"
            f"</javaConnector></connection>")


# ------------------------------------------------------------------ processes
def fld(n, tag="field", typ="string", initial=None):
    opt = '<option name="required">false</option>'
    if initial is not None:
        opt += f'<option name="initialvalue">{E(initial)}</option>'
    return f'<{tag} description="" name="{n}" type="{typ}"><options>{opt}</options></{tag}>'


def ref_field(n, ref_to, conn_guid, tag="field", required=False):
    """A reference-typed field, e.g. the listener input 'event' = <conn>:KafkaMessage | <conn>:AMQPMessage (L-CAI-118),
    or a temp field <conn>:KafkaMessage for the native producer (L-CAI-124)."""
    return (f'<{tag} description="" name="{n}" type="reference"><options><option name="referenceTo">{ref_to}</option>'
            f'<option name="required">{str(required).lower()}</option><option name="isCopy">true</option>'
            f'<option name="guid">{conn_guid}</option></options></{tag}>')


def process(g: Guids, name, desc, flow, agent, inputs=(), outputs=(), temps=(), rest=True, anonymous=False,
            event_source=None, input_xml=None, temp_xml="", output_xml="", suspend=False, tracing="none", roles=None):
    """rest + anonymous: anonymous REST endpoint on the agent (http://<agent>:7080/process-engine/public/rt/<name>);
    rest + roles: authenticated endpoint; rest with neither: no service URL, callable only as a subprocess (L-CAI-130);
    event_source '<conn>:<eventSource>': a listener process (rest=False)."""
    ins = input_xml if input_xml is not None else "".join(fld(n, "parameter") for n in inputs)
    outs = "".join(fld(n) for n in outputs) + output_xml
    tmps = "".join(fld(n) if isinstance(n, str) else fld(n[0], initial=n[1]) for n in temps) + temp_xml
    dep = f'<deployment suspendOnFault="{str(suspend).lower()}" tracingLevel="{tracing}">'
    if agent:
        dep += f"<targetLocation>{E(agent)}</targetLocation>"
    if rest:
        acc = "<allowAnonymousAccess/>" if anonymous else ""
        if roles and not anonymous:
            acc = "<allowedRoles>" + "".join(f"<role>{E(r)}</role>" for r in roles) + "</allowedRoles>"
        dep += "<rest>" + acc + "</rest>"
    if event_source:
        dep += f'<event eventSource="{E(event_source)}"/>'
    dep += "</deployment>"
    tags = ".anonymous" if (rest and anonymous) else ""
    return (f'<process xmlns="{NS_SF}" xmlns:list="urn:activevos:spi:list:functions" GUID="{g.guid("PROCESS:" + name)}" '
            f'displayName="{name}" name="{name}"><appliesTo/><description>{E(desc)}</description><tags>{tags}</tags>'
            f"<generator>Informatica Process Designer 11</generator><input>{ins}</input><output>{outs}</output>"
            f"<tempFields>{tmps}</tempFields><notes/>{dep}{flow}</process>")


# ------------------------------------------------------------------ FRS Project / Folder JSON (OData shape)
_PRIM = {"null": False, "primitive": True, "enum": False, "collection": False, "geospatial": False, "complex": False}
_NULL_COMPLEX = {"null": True, "primitive": False, "enum": False, "collection": False, "geospatial": False, "complex": True}
_ORDER = ["id", "name", "description", "owner", "createdBy", "lastUpdatedBy", "lastAccessedBy", "createdTime",
          "lastUpdatedTime", "lastAccessedTime", "expiresBy", "documentType", "contentType", "documentState", "aclRule",
          "subcontainerCount"]


def _prim(name, value):
    return {"annotations": [], "valueType": "PRIMITIVE", "value": value, "type": None, "name": name, "operations": [], **_PRIM}


def _ts(v):
    v = str(v or "")
    return v.replace("Z", ".000Z") if v.endswith("Z") and "." not in v else v


def frs_json(kind, rec):
    """Genuine-shaped FRS Folder / Project JSON from a flat FRS record (id, name, description, owner, createdBy, ...,
    parentInfo [{parentId, parentName, parentType}]) as read from the TARGET org by deploy_cai.py frs-read."""
    props = []
    for n in _ORDER:
        v = rec.get(n)
        if n.endswith("Time") or n == "expiresBy":
            v = _ts(v)
        if n == "subcontainerCount":
            v = int(v or 0)
        props.append(_prim(n, v))
    props.append({"annotations": [], "valueType": "COMPLEX", "value": None, "type": None, "name": "customAttributes",
                  "operations": [], **_NULL_COMPLEX})
    props.append({"annotations": [], "valueType": "COMPLEX", "value": None, "type": None, "name": "repoInfo",
                  "operations": [], **_NULL_COMPLEX})
    parents = []
    for p in rec.get("parentInfo") or []:
        parents.append({"annotations": [], "baseURI": None, "id": None, "title": None, "associationLinks": [],
                        "navigationLinks": [], "value": [_prim(k, p.get(k)) for k in ("parentId", "parentName", "parentType")]})
    props.append({"annotations": [], "valueType": "COLLECTION_COMPLEX", "value": parents, "type": None, "name": "parentInfo",
                  "operations": [], "null": False, "primitive": False, "enum": False, "collection": True,
                  "geospatial": False, "complex": True})
    return json.dumps({"annotations": [], "baseURI": None, "id": ("Folders(%s)" if kind == "Folder" else "Projects(%s)") % rec["id"],
                       "title": None, "associationLinks": [], "navigationLinks": [], "type": f"OData.frs.{kind}",
                       "editLink": None, "mediaEditLinks": [], "operations": [], "properties": props},
                      separators=(",", ":")).encode()


# ------------------------------------------------------------------ package
def package(g: Guids, pkg_name, project, frs, assets, org_id_v3, org_name, out_dir, publish_order=()):
    """assets: [(folder, name, TYPE, desc, entry_xml, refs[guids])]. frs = {"project": rec, "folders": {name: rec}}.
    Writes <out_dir>/<pkg_name>.zip + .json (manifest: guids, paths, publish order). Returns the manifest.
    Every connection / connector a process names must be IN the package (L-CAI-136); objectRefs to objects outside
    the package are dropped (they give MigrationSvc_031)."""
    os.makedirs(out_dir, exist_ok=True)
    proj = frs["project"]
    files, objs, csv = {}, [], ["objectPath,objectName,objectType,id"]

    def container(kind, rec, path):
        objs.append({"objectGuid": rec["id"], "objectName": rec["name"], "objectType": kind, "path": path, "providerName": None,
                     "metadata": {"modelVersion": {"major": 0, "minor": 0}, "repoInfo": None, "objectRefs": [],
                                  "contextAttributes": [],
                                  "additionalInfo": {"description": rec.get("description", ""), "contentType": "Binary",
                                                     "documentState": "COMPLETE"}}})
        csv.append(f"{path},{rec['name']},{kind},{rec['id']}")

    files[f"Explore/{project}.Project.json"] = frs_json("Project", proj)
    container("Project", proj, "/Explore")
    for folder in dict.fromkeys(a[0] for a in assets):
        rec = frs["folders"][folder]
        files[f"Explore/{project}/{folder}.Folder.json"] = frs_json("Folder", rec)
        container("Folder", rec, f"/Explore/{project}")
    inpkg = {g.guid(f"{typ}:{name}") for _, name, typ, *_ in assets}
    guids, paths, by_suffix = [], [], {}
    for folder, name, typ, desc, entry, refs in assets:
        gid = g.guid(f"{typ}:{name}")
        body = item(name, typ, desc, gid, entry).encode("utf-8")
        # well-formed or raise; guarded by safe_xml_bytes: no DTD or entities
        minidom.parseString(safe_xml_bytes(body))  # nosec B318
        if b"\x08" in body:                        # a shell heredoc once turned \b into a backspace byte
            raise SystemExit(f"control byte 0x08 in {name}")
        base = f"Explore/{project}/{folder}"
        p = f"{base}/{name}.{typ}.xml"
        files[p] = body
        objs.append({"objectGuid": gid, "objectName": name, "objectType": typ, "path": f"/{base}", "providerName": None,
                     "metadata": {"modelVersion": {"major": 1, "minor": 0}, "repoInfo": None,
                                  "objectRefs": [r for r in refs if r in inpkg], "contextAttributes": None,
                                  "additionalInfo": {"description": desc, "contentType": "application/json; charset=utf-8",
                                                     "documentState": "VALID"}}})
        csv.append(f"/{base},{name},{typ},{gid}")
        guids.append(gid)
        paths.append(p)
        by_suffix[f"{name}.{typ}.xml"] = p
    files["exportMetadata.v2.json"] = json.dumps({"name": pkg_name, "sourceOrgId": org_id_v3, "sourceOrgName": org_name,
                                                  "exportedObjects": objs}, indent=2).encode()
    # checksum lines: path with spaces escaped as '\ ', upper-case SHA256 hex (Java properties style)
    chk = "#\n#" + datetime.datetime.now(datetime.timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y") + "\n" + "".join(
        "%s=%s\n" % (p.replace(" ", "\\ "), hashlib.sha256(b).hexdigest().upper()) for p, b in files.items())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p, b in files.items():
            z.writestr(p, b)
        z.writestr("exportPackage.chksum", chk)
        z.writestr(f"ContentsofExportPackage_{pkg_name}.csv", "\n".join(csv) + "\n")
    with open(os.path.join(out_dir, pkg_name + ".zip"), "wb") as f:
        f.write(buf.getvalue())
    man = {"name": pkg_name, "guids": guids, "paths": paths,
           "publish": [by_suffix[s] for s in publish_order if s in by_suffix],
           "by_name": {s: by_suffix[s] for s in by_suffix}}
    with open(os.path.join(out_dir, pkg_name + ".json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1)
    return man
