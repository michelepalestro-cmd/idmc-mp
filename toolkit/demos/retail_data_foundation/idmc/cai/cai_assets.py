"""CAI asset XML for the real-time CRM sync (generic; adapted from processes that ran in production in 2026-09).

Three asset kinds, published in this order (unpublish in reverse):
  AI_SERVICE_CONNECTOR  <sc>        REST actions: Get_Token (OAuth 2.0 client credentials, form-encoded BODY, not URL),
                                    Upsert_Contact (PATCH /sobjects/Contact/<ExtId>/<id>: create-or-update, idempotent),
                                    Upsert_Record (PATCH any sObject by external id, JSON payload built in CAI)
  AI_CONNECTION         <conn>      Cloud Server connection holding the token URL, client id / secret, API version
  PROCESS               processes   REST processes restricted to allowed IDMC users / groups (Basic Authentication on
                                    /active-bpel/rt/<process>); anonymous only as an explicit test opt-in
                                    (config cai.anonymous). token -> upsert; outputs sfdc_id / sfdc_created / sfdc_status
Why a custom service connector instead of the built-in Salesforce connector: the built-in one needs the
ModifyMetadata permission, which breaks least privilege for an integration user.
"""
import html
from xml.sax.saxutils import escape

MA = '<mutualAuth enabled="false"><keyStore mode="file"/><keyStorePassword/></mutualAuth>'


def e(s):
    return html.escape(str(s), quote=True)


def item(name, mime, desc, guid, entry):
    """The repository wrapper every CAI asset file in an export package uses."""
    return f"""<aetgt:getResponse xmlns:aetgt="http://schemas.active-endpoints.com/appmodules/repository/2010/10/avrepository.xsd"
 xmlns:types1="http://schemas.active-endpoints.com/appmodules/repository/2010/10/avrepository.xsd">
<types1:Item><types1:Name>{name}</types1:Name><types1:MimeType>{mime}</types1:MimeType>
<types1:Description>{e(desc)}</types1:Description><types1:AppliesTo/><types1:Tags/><types1:VersionLabel>1.0</types1:VersionLabel>
<types1:State>CURRENT</types1:State><types1:ProcessGroup/>
<types1:Entry>{entry}</types1:Entry><types1:GUID>{guid}</types1:GUID><types1:DisplayName>{name}</types1:DisplayName></types1:Item>
</aetgt:getResponse>
"""


def _ca(name, masked, test=""):
    return (f'<connectionAttribute description="" label="{name}" masked="{str(masked).lower()}" name="{name}" required="true" '
            f'testWith="{e(test)}" type="string"/>')


def service_connector(sc, sc_uuid, token_url_example, api_version, contact_ext, tag, contact_fields):
    params = "".join(f'<parameter name="{f}" required="false" type="string"/>' for f in contact_fields)
    return f"""<businessConnector xmlns="http://schemas.informatica.com/socrates/data-services/2014/05/business-connector-model.xsd"
 agentOnly="false" debug="false" displayName="{sc}" label="" name="{sc}" uuid="{sc_uuid}">
<description>[{tag}] Salesforce REST (OAuth client credentials, least privilege)</description><tags/>
<connectionAttributes xmlns="http://schemas.informatica.com/appmodules/screenflow/2014/04/avosConnectors.xsd">
{_ca("SF_TOKEN_URL", False, token_url_example)}{_ca("SF_CLIENT_ID", True)}{_ca("SF_CLIENT_SECRET", True)}{_ca("SF_API_VERSION", False, api_version)}
</connectionAttributes>
<actions>
<action category="" failOnError="true" forSearch="false" label="Get_Token" maxRedirects="100" name="Get_Token" preemptiveAuth="true" responseEncoding="">
<description>OAuth 2.0 client-credentials token from the Connected App</description><input/>
<binding><restSimpleBinding multiUsing="semicolonSeparated" url="{{$SF_TOKEN_URL}}" verb="POST">{MA}
<httpHeaders><header name="Content-Type">application/x-www-form-urlencoded</header><header name="Accept">application/json</header></httpHeaders>
<body>grant_type=client_credentials&amp;amp;client_id={{$SF_CLIENT_ID}}&amp;amp;client_secret={{$SF_CLIENT_SECRET}}</body>
</restSimpleBinding></binding>
<output><field description="" name="access_token" property="access_token" type="string"/>
<field description="" name="instance_url" property="instance_url" type="string"/></output>
</action>
<action category="" failOnError="true" forSearch="false" label="Upsert_Contact" maxRedirects="100" name="Upsert_Contact" preemptiveAuth="true" responseEncoding="">
<description>Create-or-update Contact by external id {contact_ext}</description>
<input>
<parameter name="instance_url" nogen="true" required="true" type="string"/>
<parameter name="access_token" nogen="true" required="true" type="string"/>
<parameter name="customer_id" nogen="true" required="true" type="string"/>
{params}
</input>
<binding><restSimpleBinding multiUsing="semicolonSeparated" url="{{$instance_url}}/services/data/v{{$SF_API_VERSION}}/sobjects/Contact/{contact_ext}/{{$customer_id}}" verb="PATCH">{MA}
<httpHeaders><header name="Authorization">Bearer {{$access_token}}</header><header name="Content-Type">application/json</header><header name="Accept">application/json</header></httpHeaders>
<body generateUsing="JSON" preserveJsonStringFormatting="true"/>
</restSimpleBinding></binding>
<output><field description="" name="id" property="id" type="string"/><field description="" name="created" property="created" type="string"/>
<field description="" name="success" property="success" type="string"/></output>
</action>
<action category="" failOnError="true" forSearch="false" label="Upsert_Record" maxRedirects="100" name="Upsert_Record" preemptiveAuth="true" responseEncoding="">
<description>Create-or-update ANY sObject by external id; the JSON payload is built in the process (parents via Parent__r external ids)</description>
<input>
<parameter name="instance_url" nogen="true" required="true" type="string"/>
<parameter name="access_token" nogen="true" required="true" type="string"/>
<parameter name="sobject" nogen="true" required="true" type="string"/>
<parameter name="ext_field" nogen="true" required="true" type="string"/>
<parameter name="ext_id" nogen="true" required="true" type="string"/>
<parameter name="payload" nogen="true" required="true" type="string"/>
</input>
<binding><restSimpleBinding multiUsing="semicolonSeparated" url="{{$instance_url}}/services/data/v{{$SF_API_VERSION}}/sobjects/{{$sobject}}/{{$ext_field}}/{{$ext_id}}" verb="PATCH">{MA}
<httpHeaders><header name="Authorization">Bearer {{$access_token}}</header><header name="Content-Type">application/json</header><header name="Accept">application/json</header></httpHeaders>
<body>{{$payload}}</body>
</restSimpleBinding></binding>
<output><field description="" name="id" property="id" type="string"/><field description="" name="created" property="created" type="string"/></output>
</action>
</actions><objects/></businessConnector>"""


def app_connection(conn, sc, sc_guid, sc_uuid, tag, token_url, api_version):
    """The Connected App client id / secret are authored encrypted="true" with an EMPTY value (the shape IDMC exports
    for a sensitive attribute, L-CAI-198), so the package never holds them. 05_cai.py set-secret then stores them
    encrypted with PUT /active-bpel/asset/v1/update (L-CAI-132); an attribute authored encrypted="false" would be
    stored and exported in plain text."""
    return f"""<connection xmlns="http://schemas.informatica.com/socrates/data-services/2014/04/avosConnections.xsd" displayName="{conn}" label="{conn}" name="{conn}">
<description>[{tag}] Salesforce REST (Cloud Server, OAuth client credentials)</description><tags/><agent/>
<attributes>
<attribute name="SF_TOKEN_URL" value="{e(token_url)}"/><attribute encrypted="true" name="SF_CLIENT_ID" value=""/>
<attribute encrypted="true" name="SF_CLIENT_SECRET" value=""/><attribute name="SF_API_VERSION" value="{e(api_version)}"/>
</attributes>
<businessConnector xmlns="http://schemas.informatica.com/appmodules/screenflow/2014/04/avosConnectors.xsd" agentOnly="false"
 connectorPath="project:/rt.connector/{sc}/{sc}_svcDef.xml" guid="{sc_guid}" name="{sc}" supportsConnectionTest="false" uuid="{sc_uuid}">
<description>[{tag}] Salesforce REST</description></businessConnector>
</connection>"""


def fld(n, tag="field"):
    return f'<{tag} description="" name="{n}" type="string"><options><option name="required">false</option></options></{tag}>'


def _deploy(anonymous=False, users=(), groups=()):
    """REST access of a process (L-CAI-181). Default: only the listed IDMC users / groups may call it, with Basic
    Authentication on https://<pod>-cai.<domain>/active-bpel/rt/<process>. With neither listed the endpoint answers
    403 to everyone (fails closed). anonymous=True is a test-only opt-in: anyone with the URL can call it."""
    if anonymous:
        acc = "<allowAnonymousAccess/>"
    else:
        acc = ("<allowedGroups>" + "".join(f"<group>{e(g)}</group>" for g in groups) + "</allowedGroups>" if groups else "") + \
              ("<allowedUsers>" + "".join(f"<user>{e(u)}</user>" for u in users) + "</allowedUsers>" if users else "")
    return f'<deployment suspendOnFault="false" tracingLevel="none"><rest>{acc}</rest></deployment>'


def contact_process(name, guid, conn, conn_guid, tag, anonymous=False, users=(), groups=()):
    """Sign-up -> Contact. The light cleanse runs in CAI (XQuery): trimmed lower-case e-mail, digits-only phone,
    first / last name split at the last space (the batch golden record refines it on the next lane run).
    Every writer of a field must apply the same rule, or the batch undoes the real-time result."""
    n = lambda f: f"normalize-space(string($input.{f}))"  # noqa: E731
    formulas = {
        "temp.first_name": f"(let $n := {n('full_name')} return if (contains($n, ' ')) then replace($n, '^(.*) [^ ]+$', '$1') else '')",
        "temp.last_name": f"(let $n := {n('full_name')} return if (contains($n, ' ')) then replace($n, '^.* ([^ ]+)$', '$1') else if ($n != '') then $n else 'Unknown')",
        "temp.email": f"lower-case({n('email')})",
        "temp.phone": f"replace({n('phone')}, '[^0-9]', '')",
    }
    ops = "".join(f'<operation source="formula" to="{k}"><expression language="XQuery">{e(v)}</expression></operation>'
                  for k, v in formulas.items())
    ins = ["customer_id", "email", "full_name", "phone", "tier", "channel"]
    temps = ["access_token", "instance_url", "first_name", "last_name", "email", "phone"]
    upsert_in = "".join([
        '<parameter name="instance_url" source="field">temp.instance_url</parameter>',
        '<parameter name="access_token" source="field">temp.access_token</parameter>',
        '<parameter name="customer_id" source="field">input.customer_id</parameter>',
        '<parameter name="FirstName" source="field">temp.first_name</parameter>',
        '<parameter name="LastName" source="field">temp.last_name</parameter>',
        '<parameter name="Email" source="field">temp.email</parameter>',
        '<parameter name="Phone" source="field">temp.phone</parameter>',
        '<parameter name="Rdf_Tier__c" source="field">input.tier</parameter>',
        '<parameter name="Rdf_Signup_Channel__c" source="field">input.channel</parameter>'])
    return f"""<process xmlns="http://schemas.active-endpoints.com/appmodules/screenflow/2010/10/avosScreenflow.xsd" xmlns:list="urn:activevos:spi:list:functions"
 GUID="{guid}" displayName="{name}" name="{name}">
<appliesTo/><description>[{tag}] Real time: sign-up -> CRM Contact (upsert on the external id). The batch golden record enriches it on the next lane run.</description>
<tags>{'.anonymous' if anonymous else ''}</tags><generator>Informatica Process Designer 11</generator>
<input>{''.join(fld(x, 'parameter') for x in ins)}</input><output>{''.join(fld(x) for x in ('sfdc_id', 'sfdc_created', 'sfdc_status'))}</output>
<tempFields>{''.join(fld(x) for x in temps)}</tempFields><notes/>
{_deploy(anonymous, users, groups)}
<flow id="a"><start id="b"><link id="l1" targetId="c"/></start>
<assignment id="c"><title>Cleanse</title>{ops}<link id="l2" targetId="d"/></assignment>
<service id="d"><title>Get token</title><serviceName>{conn}:Get_Token</serviceName><serviceGUID>{conn_guid}</serviceGUID><serviceInput/>
<serviceOutput><operation source="field" to="temp.access_token">access_token</operation><operation source="field" to="temp.instance_url">instance_url</operation></serviceOutput>
<link id="l3" targetId="f"/></service>
<service id="f"><title>Upsert Contact</title><serviceName>{conn}:Upsert_Contact</serviceName><serviceGUID>{conn_guid}</serviceGUID>
<serviceInput>{upsert_in}</serviceInput>
<serviceOutput><operation source="field" to="output.sfdc_id">id</operation><operation source="field" to="output.sfdc_created">created</operation></serviceOutput>
<link id="l4" targetId="g"/></service>
<assignment id="g"><title>Status</title><operation source="constant" to="output.sfdc_status">upserted</operation><link id="l5" targetId="h"/></assignment>
<end id="h"/></flow></process>"""


# ------------------------------------------------------------- event processes (one record each, JSON built in CAI)
def _v(f):
    return f"normalize-space(string($input.{f}))"


def _js(f):   # JSON string literal (escaped), or null
    v = _v(f)
    return (f"(if ({v} = '') then 'null' else concat('\"', replace(replace({v}, '\\\\', '\\\\\\\\'), '\"', '\\\\\"'), '\"'))")


def _jn(f):
    v = _v(f)
    return f"(if ({v} castable as xs:decimal) then string(xs:decimal({v})) else 'null')"


def _jb(f):
    v = _v(f)
    return f"(if (lower-case({v}) = ('true', 't', '1', 'yes')) then 'true' else 'false')"


def payload_expr(ev):
    parts = []
    for sf, key, inp in ev["rels"]:   # omit the relationship entirely when the parent key is empty
        parts.append(f"(if ({_v(inp)} = '') then '' else concat('\"{sf}\":{{\"{key}\":', {_js(inp)}, '}}'))")
    for sf, inp, kind in ev["fields"]:
        val = {"s": _js, "t": _js, "n": _jn, "b": _jb}[kind](inp)
        parts.append(f"concat('\"{sf}\":', {val})")
    return f"concat('{{', string-join(({', '.join(parts)})[. != ''], ','), '}}')"


def event_inputs(ev):
    names = [ev["ext_input"]] + [r[2] for r in ev["rels"]] + [f[1] for f in ev["fields"]]
    return list(dict.fromkeys(names))


def event_process(name, ev, guid, conn, conn_guid, tag, anonymous=False, users=(), groups=()):
    ins = "".join(fld(n, "parameter") for n in event_inputs(ev))
    outs = "".join(fld(n) for n in ("sfdc_id", "sfdc_created", "sfdc_status"))
    temps = "".join(fld(n) for n in ("access_token", "instance_url", "payload"))
    return f"""<process xmlns="http://schemas.active-endpoints.com/appmodules/screenflow/2010/10/avosScreenflow.xsd" xmlns:list="urn:activevos:spi:list:functions"
 GUID="{guid}" displayName="{name}" name="{name}">
<appliesTo/><description>[{tag}] Real time: upsert {ev['sobject']} on {ev['ext_field']} (parent links by external id).</description>
<tags>{'.anonymous' if anonymous else ''}</tags><generator>Informatica Process Designer 11</generator>
<input>{ins}</input><output>{outs}</output><tempFields>{temps}</tempFields><notes/>
{_deploy(anonymous, users, groups)}
<flow id="a"><start id="b"><link id="l1" targetId="c"/></start>
<assignment id="c"><title>Build JSON</title><operation source="formula" to="temp.payload"><expression language="XQuery">{escape(payload_expr(ev))}</expression></operation><link id="l2" targetId="d"/></assignment>
<service id="d"><title>Get token</title><serviceName>{conn}:Get_Token</serviceName><serviceGUID>{conn_guid}</serviceGUID><serviceInput/>
<serviceOutput><operation source="field" to="temp.access_token">access_token</operation><operation source="field" to="temp.instance_url">instance_url</operation></serviceOutput>
<link id="l3" targetId="f"/></service>
<service id="f"><title>Upsert {ev['sobject']}</title><serviceName>{conn}:Upsert_Record</serviceName><serviceGUID>{conn_guid}</serviceGUID>
<serviceInput><parameter name="instance_url" source="field">temp.instance_url</parameter><parameter name="access_token" source="field">temp.access_token</parameter>
<parameter name="sobject" source="constant">{ev['sobject']}</parameter><parameter name="ext_field" source="constant">{ev['ext_field']}</parameter>
<parameter name="ext_id" source="field">input.{ev['ext_input']}</parameter><parameter name="payload" source="field">temp.payload</parameter></serviceInput>
<serviceOutput><operation source="field" to="output.sfdc_id">id</operation><operation source="field" to="output.sfdc_created">created</operation></serviceOutput>
<link id="l4" targetId="g"/></service>
<assignment id="g"><title>Status</title><operation source="constant" to="output.sfdc_status">upserted</operation><link id="l5" targetId="h"/></assignment>
<end id="h"/></flow></process>"""


def membership_event(cfg):
    c = cfg["crm"]
    return {"sobject": c["membershipObject"], "ext_field": c["membershipExternalId"], "ext_input": "membership_id",
            "rels": [("Contact__r", c["contactExternalId"], "customer_id")],
            "fields": [("Tier__c", "tier", "s"), ("Status__c", "status", "s"), ("Monthly_Price__c", "monthly_price", "n"),
                       ("Started_At__c", "started_at", "t"), ("Cancelled_At__c", "cancelled_at", "t")]}
