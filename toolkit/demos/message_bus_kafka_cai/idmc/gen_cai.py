#!/usr/bin/env python3
"""gen_cai.py - generate the CAI import package of the Message Bus Replacement demo (offline; no IDMC call).

    python idmc/gen_cai.py [--consumers off|on] [--config config.json] [--offline-frs] [--out build/cai]

Writes build/cai/mbr_cai.zip (v3 import package) + mbr_cai.json (manifest: GUIDs, asset paths, publish order) and,
with --dump, every asset XML under build/cai/xml/ for review.

--consumers off (default, first build): every Kafka / AMQP consumer is authored enabled="false", so publishing a
connection starts no listener before its process exists (L-CAI-119). After the processes are published, rebuild
with --consumers on and republish ONLY the three listener connections (BUILD.md step 7).
--offline-frs: use placeholder Project / Folder records (dry run on a PC with no org; the zip is NOT importable).

Assets (project 'Message Bus Replacement'):
  1 Connections        mbr_ledger_api / mbr_merch_api / mbr_wh_api / mbr_store_api (REST service connectors)
                       mbr_ledger / mbr_merch / mbr_wh / mbr_store (REST app connections, PostgREST stand-ins)
                       mbr-kafka (consumers item-sub, po-sub, perf-sub; producers item-pub, po-pub, dlq-pub)
                       mbr-kafka-store (consumer store-price-sub: its own connection, so it can be stopped alone)
                       mbr-jms (AMQP 1.0 to the legacy JMS broker: consumers items-legacy, pos-legacy)
  2 Bridge JMS to Kafka mbr_jms_bridge_items, mbr_jms_bridge_pos
  3 Subscribers        mbr_item_subscriber + mbr_item_handle, mbr_po_subscriber + mbr_po_handle,
                       mbr_store_price_subscriber + mbr_store_price_handle, mbr_perf_subscriber
  4 Error Queue and Replay  mbr_deliver (retry + backoff), mbr_error_queue_replay, mbr_hospital_retry
PROVEN in an earlier form (same step grammar, same listener / handler / delivery split, same connection options);
ADAPTED here: names, the stand-in REST contract (PostgREST functions instead of a stand-in service), DLQ to a
Kafka topic, the hospital replay processes.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import mbr_cai as C  # noqa: E402
import mbr_config as CFG  # noqa: E402
import mbr_flow as W  # noqa: E402

LEDGER, MERCH, WH, STORE = "mbr_ledger", "mbr_merch", "mbr_wh", "mbr_store"
KAF, KSTORE, JMS = "mbr-kafka", "mbr-kafka-store", "mbr-jms"
DELIVER_OUT = ["status", "http_status", "error", "reason", "attempts", "body"]
HANDLER_IN = ["body", "msg_id", "rev", "key", "source", "topic"]
G: C.Guids = None  # set in main()
CONF: dict = {}


def gc(name):
    return G.guid("AI_CONNECTION:" + name)


def gp(name):
    return G.guid("PROCESS:" + name)


def J(pairs):
    return W.jobj(pairs)


setv = W.setv


# ------------------------------------------------------------------ XQuery helpers
def H(n):
    """value of a Kafka / AMQP event header (headers arrive as repeated <headers><name/><value/></headers>, L-CAI-118)"""
    return f"string(($input.event/headers[name = '{n}']/value)[1])"


def ENV(tag, src):
    """a field of the message envelope by string search: never faults, works on a broken payload"""
    return f"substring-before(substring-after({src}, '<{tag}>'), '</{tag}>')"


def X(f):
    """a field of the parsed inner payload; faults on malformed XML (caught by the listener)"""
    return f"string((util:parseXML($temp.inner)/descendant-or-self::*:{f})[1])"


def OR(*exprs):
    e = exprs[-1]
    for x in reversed(exprs[:-1]):
        e = f"(let $v := {x} return if ($v != '') then $v else {e})"
    return e


def track(proc, stage, target, status="'ok'", detail="''", ms="''", mid="$input.msg_id", rev="$input.rev"):
    return W.service(f"track {stage}", LEDGER, gc(LEDGER), "track", inputs=[("payload", "formula", J([
        ("msg_id", mid), ("rev", rev), ("stage", f"'{stage}'"), ("target", target), ("status", status), ("detail", detail),
        ("ms", ms), ("process", f"'{proc}'"), ("instance_id", "util:getProcessId()")]))])


DLQ_REF = None  # the temp field <mbr-kafka>:KafkaMessage every process with an error path carries


def dlq_ref():
    return C.ref_field("dlqmsg", f"{KAF}:KafkaMessage", gc(KAF))


def dlq(proc, code, text, target, http="''", step="''", attempts="'1'", mid="$input.msg_id", rev="$input.rev",
        body="$input.body", topic="$input.topic", biz="$input.key", fam="''", typ="''"):
    """The error path, three connector calls inside the SAME run (no extra CAI API call):
    1 the hospital entry (ledger /rpc/dlq: reason, retryable per reason code, next retry time),
    2 a copy to the Kafka dead-letter topic (native producer dlq-pub, key = business id, reason in the headers),
    3 a timeline event."""
    hdr = lambda n, v: f"<headers><name>{n}</name><value>{{string({v})}}</value></headers>"  # noqa: E731
    headers = "(" + ", ".join([hdr("mbr-msg-id", mid), hdr("mbr-rev", rev), hdr("mbr-reason", code),
                               hdr("mbr-source-topic", topic), hdr("mbr-failed-step", step)]) + ")"
    return [W.service("to the hospital (error queue)", LEDGER, gc(LEDGER), "dlq", inputs=[("payload", "formula", J([
        ("msg_id", mid), ("rev", rev), ("topic", topic), ("biz_id", biz), ("family", fam), ("type", typ),
        ("reason_code", code), ("reason_text", f"substring({text}, 1, 1500)"), ("target", target), ("http_status", http),
        ("payload", body), ("failed_step", step), ("attempts", attempts)]))],
        outputs=[("temp.dlq_id", "id")]),
            W.assign("dead-letter record", [W.op("temp.dlqmsg/messageKey", biz), W.op("temp.dlqmsg/body", body),
                                            W.op("temp.dlqmsg/headers", headers)]),
            W.service("copy to the dead-letter topic", KAF, gc(KAF), "dlq-pub", inputs=[("event", "field", "temp.dlqmsg")]),
            track(proc, "error_queue", target, code, f"substring({text}, 1, 600)", mid=mid, rev=rev)]


# ------------------------------------------------------------------ service connectors (REST, the PostgREST stand-ins)
def S(n, kind="property", prop=None):
    return (n, kind, prop)


STD = [S("http_status", "status"), S("body", "entire"), S("result"), S("error"), S("reason")]


def connectors():
    A = C.action
    to = int(CONF["ledger_api"].get("request_timeout_s", 10))
    AS = lambda *a, **k: C.action(*a, timeout=to, **k)  # noqa: E731  stand-in targets: a timeout -> HTTP 500 -> retry
    ledger = [A("track", "POST", "{$base_url}/rpc/track", ["payload"], "{$payload}", STD),
              A("dlq", "POST", "{$base_url}/rpc/dlq", ["payload"], "{$payload}", STD + [S("id"), S("retryable")]),
              A("config", "GET", "{$base_url}/rpc/config", [], None,
                STD + [S("retry_max"), S("backoff_base_s"), S("backoff_mult"), S("backoff_max_s"), S("departments"), S("dc_map")]),
              A("eq_due", "POST", "{$base_url}/rpc/eq_due", [], "{}", STD + [S("ids"), S("count")]),
              A("eq_get", "GET", "{$base_url}/rpc/eq_get?id={$id}", ["id"], None,
                STD + [S("id"), S("msg_id"), S("rev"), S("topic"), S("biz_id"), S("family"), S("type"), S("payload"),
                       S("status"), S("replays"), S("reason_code")]),
              A("eq_mark", "POST", "{$base_url}/rpc/eq_mark", ["payload"], "{$payload}", STD + [S("status")])]
    merch = [AS("items", "POST", "{$base_url}/rpc/merch_items", ["payload"], "{$payload}", STD),
             AS("items_present", "POST", "{$base_url}/rpc/merch_items_present", ["payload"], "{$payload}",
                STD + [S("all_present"), S("missing"), S("missing_count")]),
             AS("pos", "POST", "{$base_url}/rpc/merch_pos", ["payload"], "{$payload}", STD + [S("version")]),
             AS("po_version", "GET", "{$base_url}/rpc/po_version?po={$po}", ["po"], None, STD + [S("version"), S("status")]),
             AS("cancel", "POST", "{$base_url}/rpc/merch_po_cancel", ["payload"], "{$payload}", STD)]
    wh = [AS("items", "POST", "{$base_url}/rpc/wh_items", ["payload"], "{$payload}", STD),
          AS("pos", "POST", "{$base_url}/rpc/wh_pos", ["payload"], "{$payload}", STD)]
    store = [AS("prices", "POST", "{$base_url}/rpc/store_prices", ["payload"], "{$payload}", STD + [S("stores")])]
    return [("mbr_ledger_api", LEDGER, "Ops ledger + hospital (error queue) API", ledger),
            ("mbr_merch_api", MERCH, "SIMULATED merchandising system (items, POs, PO versions, cancel = compensation)", merch),
            ("mbr_wh_api", WH, "SIMULATED warehouse system (items with masked vendor contact, POs per DC)", wh),
            ("mbr_store_api", STORE, "SIMULATED store point of sale (price per store)", store)]


# ------------------------------------------------------------------ listener connections
def kafka_conns(enabled):
    k, t, gr = CONF["kafka"], CONF["kafka"]["topics"], CONF["kafka"]["groups"]
    agent = CONF["agent"]["name"]
    o, op, pp = k["consumer_options"], k["perf_consumer_options"], k["producer_options"]
    main = C.kafka_connection(
        G, KAF, "Kafka: item, PO and load-test subscribers; producers for the JMS bridge, the hospital replay and the DLQ",
        agent, k["host"], k["port"], additional=k.get("additional_brokers", ""), ssl=k.get("use_ssl"), sasl=k.get("use_sasl"),
        consumers=[("item-sub", t["item"]["name"], gr["item"], o, enabled),
                   ("po-sub", t["po"]["name"], gr["po"], o, enabled),
                   ("perf-sub", t["perf"]["name"], gr["perf"], op, enabled)],
        producers=[("item-pub", t["item"]["name"], pp), ("po-pub", t["po"]["name"], pp), ("dlq-pub", t["dlq"]["name"], pp)])
    store = C.kafka_connection(
        G, KSTORE, "Kafka: the store-price subscriber on its own connection (its own group; stop / start it alone)",
        agent, k["host"], k["port"], additional=k.get("additional_brokers", ""), ssl=k.get("use_ssl"), sasl=k.get("use_sasl"),
        consumers=[("store-price-sub", t["item"]["name"], gr["store_price"], o, enabled)])
    return main, store


def jms_conn(enabled):
    a = CONF["artemis"]
    q = a["queues"]
    return C.amqp_connection(
        G, JMS, "Legacy JMS broker over AMQP 1.0 (cutover only): the legacy queues bridged to Kafka",
        CONF["agent"]["name"], a["host"], a["amqp_port"], CFG.env_value("MBR_ARTEMIS_USER") or "set-by-deploy_cai-set-secret",
        consumers=[("items-legacy", q["items"], q["dlq"], "", enabled), ("pos-legacy", q["pos"], q["dlq"], "", enabled)],
        query=a.get("query_parameters", "jms.validatePropertyNames=false"))


# ------------------------------------------------------------------ mbr_deliver: one delivery with retry + backoff
DELIVER_TARGETS = [("merch_items", MERCH, "items"), ("merch_items_present", MERCH, "items_present"), ("merch_pos", MERCH, "pos"),
                   ("wh_items", WH, "items"), ("wh_pos", WH, "pos"), ("store_prices", STORE, "prices"),
                   ("merch_po_cancel", MERCH, "cancel")]


def p_deliver():
    P = "mbr_deliver"
    outs = [("temp.hs", "http_status"), ("temp.he", "error"), ("temp.hr", "reason"), ("temp.hres", "result"), ("temp.hb", "body")]
    branches = [(f"$input.target = '{t}'", [W.service(t, conn, gc(conn), act, inputs=[("payload", "field", "input.payload")],
                                                      outputs=outs)]) for t, conn, act in DELIVER_TARGETS]
    branches.append((None, [W.assign("unknown target", setv(hs="'0'", he="'UNKNOWN_TARGET'", hr="concat('no such target ', $input.target)"))]))
    attempt = W.assign("attempt", setv(n="string(xs:integer(if ($temp.n castable as xs:integer) then $temp.n else 0) + 1)",
                                      hs="''", he="''", hr="''", hres="''", hb="''"))
    maxr = "(if ($input.retry_max castable as xs:integer) then xs:integer($input.retry_max) else 5)"
    nextw = ("(let $b := (if ($input.backoff_base_s castable as xs:decimal) then xs:decimal($input.backoff_base_s) else 2), "
             "$m := (if ($input.backoff_mult castable as xs:decimal) then xs:decimal($input.backoff_mult) else 2), "
             "$mx := (if ($input.backoff_max_s castable as xs:decimal) then xs:decimal($input.backoff_max_s) else 60) "
             "return string(if ($temp.wait_s castable as xs:decimal) then min(($mx, xs:decimal($temp.wait_s) * $m)) else min(($mx, $b))))")
    retry_track = track(P, "retry", "$input.target", "$temp.hs",
                        "concat('attempt ', $temp.n, ' of ', string(" + maxr + "), ' failed: HTTP ', $temp.hs, ' ', $temp.he, ' ', "
                        "$temp.hr, '; next try in ', $temp.wait_s, ' s')", ms="string(xs:decimal($temp.wait_s) * 1000)")
    classify = W.decision("classify the answer", [
        ("starts-with($temp.hs, '2')", [W.assign("delivered", setv(st="if ($temp.hres = 'duplicate') then 'duplicate' else 'delivered'"))]),
        ("$temp.hs = '409'", [W.assign("stale", setv(st="'stale'"))]),
        ("starts-with($temp.hs, '4')", [W.assign("rejected (no retry)", setv(st="'rejected'"))]),
        (f"xs:integer($temp.n) lt {maxr}", [W.assign("backoff", setv(wait_s=nextw)), retry_track,
                                            W.wait("backoff wait", expr="$temp.wait_s"), W.jump(attempt.sid)]),
        (None, [W.assign("retries exhausted", setv(st="'failed'"))])])
    steps = [W.assign("init", setv(n="'0'", wait_s="''")), attempt, W.decision("route to the target", branches), classify,
             W.assign("outputs", [W.op("output.status", "$temp.st"), W.op("output.http_status", "$temp.hs"),
                                  W.op("output.error", "$temp.he"), W.op("output.reason", "$temp.hr"),
                                  W.op("output.attempts", "$temp.n"), W.op("output.body", "$temp.hb")]),
             W.end()]
    return C.process(G, P, "Delivers one JSON payload to a target with retries: 5xx and timeouts retry with exponential backoff "
                           "(retry_max, backoff_base_s, backoff_mult, backoff_max_s from the ledger config); 2xx = delivered "
                           "(duplicate on an idempotent replay), 409 = stale, other 4xx = rejected (no retry). Private subprocess.",
                     W.flow(steps), CONF["agent"]["name"],
                     inputs=["target", "payload", "msg_id", "rev", "retry_max", "backoff_base_s", "backoff_mult", "backoff_max_s"],
                     outputs=DELIVER_OUT, temps=["n", "wait_s", "hs", "he", "hr", "hres", "hb", "st"], rest=True, anonymous=False)


def deliver(title, target, payload_field, prefix):
    ins = [("target", "const", target), ("payload", "field", payload_field), ("msg_id", "field", "input.msg_id"),
           ("rev", "field", "input.rev"), ("retry_max", "field", "temp.cfg_retry"), ("backoff_base_s", "field", "temp.cfg_base"),
           ("backoff_mult", "field", "temp.cfg_mult"), ("backoff_max_s", "field", "temp.cfg_max")]
    return W.subflow(title, "mbr_deliver", gp("mbr_deliver"), inputs=ins, out_fields=DELIVER_OUT,
                     out_map=[(f"temp.{prefix}_{o}", o) for o in DELIVER_OUT])


def get_config():
    return W.service("read retry + validation settings", LEDGER, gc(LEDGER), "config",
                     outputs=[("temp.cfg_retry", "retry_max"), ("temp.cfg_base", "backoff_base_s"), ("temp.cfg_mult", "backoff_mult"),
                              ("temp.cfg_max", "backoff_max_s"), ("temp.cfg_depts", "departments"), ("temp.cfg_dc_map", "dc_map")])


CFG_TEMPS = ["cfg_retry", "cfg_base", "cfg_mult", "cfg_max", "cfg_depts", "cfg_dc_map"]


def pref_temps(*prefixes):
    return [f"{p}_{o}" for p in prefixes for o in DELIVER_OUT]


# ------------------------------------------------------------------ items: validate, transform, deliver
ITEM_FIELDS = [("item", "item"), ("item_desc", "item_desc"), ("short_desc", "short_desc"), ("dept", "dept"), ("class", "class"),
               ("subclass", "subclass"), ("unit_retail", "unit_retail"), ("compare_at", "compare_at_price"), ("upc", "upc"),
               ("supplier", "supplier"), ("status", "status"), ("email", "vendor_contact_email")]


def item_parse_ops():
    ops = [W.op("temp.inner", "string((util:parseXML($input.body)//*:messageData)[1])")]
    ops += [W.op(f"temp.{t}", X(f)) for t, f in ITEM_FIELDS]
    ops.append(W.op("temp.masked", "(let $e := $temp.email return if (contains($e, '@')) then concat(substring($e, 1, 1), '***@', "
                                   "substring-after($e, '@')) else '')"))
    return ops


UPC_RULE = ("(let $u := $temp.upc return if (not(matches($u, '^[0-9]{12}$'))) then 'UPC_CHECK_DIGIT' else "
            "(let $d := for $i in 1 to 12 return xs:integer(substring($u, $i, 1)), "
            "$s := 3 * ($d[1] + $d[3] + $d[5] + $d[7] + $d[9] + $d[11]) + ($d[2] + $d[4] + $d[6] + $d[8] + $d[10]) "
            "return if ((10 - $s mod 10) mod 10 = $d[12]) then () else 'UPC_CHECK_DIGIT'))")
PRICE_RULE = ("(if ($temp.unit_retail castable as xs:decimal) then (if (xs:decimal($temp.unit_retail) gt 0) then () else "
              "'UNIT_RETAIL_POSITIVE') else 'UNIT_RETAIL_POSITIVE')")
CMP_RULE = ("(if (($temp.compare_at castable as xs:decimal) and ($temp.unit_retail castable as xs:decimal)) then "
            "(if (xs:decimal($temp.compare_at) ge xs:decimal($temp.unit_retail)) then () else 'COMPARE_AT_GE_RETAIL') else ())")
DEPT_RULE = "(if ($temp.dept = tokenize($temp.cfg_depts, ',')) then () else 'DEPT_VALID')"
REQ_RULE = ("(if ($temp.item != '' and $temp.item_desc != '' and $temp.supplier != '' and $temp.upc != '') then () "
            "else 'REQUIRED_FIELDS')")
DQ_FLAGS = f"string-join(({UPC_RULE}, {PRICE_RULE}, {CMP_RULE}, {DEPT_RULE}, {REQ_RULE}), ',')"
ITEM_TEMPS = [t for t, _ in ITEM_FIELDS] + ["inner", "masked", "dq_flags", "valid", "merch_json", "wh_json", "store_json", "res",
                                            "dlq_id"]
OKS = "('delivered', 'duplicate')"


def p_item_handle():
    P = "mbr_item_handle"
    merch_json = J([("msg_id", "$input.msg_id"), ("rev", "$input.rev"), ("item", "$temp.item"), ("item_desc", "$temp.item_desc"),
                    ("dept", "$temp.dept"), ("class", "$temp.class"), ("subclass", "$temp.subclass"), ("unit_retail", "$temp.unit_retail"),
                    ("compare_at", "$temp.compare_at"), ("upc", "$temp.upc"), ("supplier", "$temp.supplier"), ("status", "$temp.status")])
    wh_json = J([("msg_id", "$input.msg_id"), ("rev", "$input.rev"), ("item", "$temp.item"), ("item_desc", "$temp.item_desc"),
                 ("dept", "$temp.dept"), ("upc", "$temp.upc"), ("vendor_contact", "$temp.masked")])
    ok = f"($temp.m_status = {OKS} and $temp.w_status = {OKS})"
    m_bad = f"not($temp.m_status = {OKS})"
    fail_code = (f"(if ({m_bad}) then (if ($temp.m_error != '') then $temp.m_error else 'MERCH_UNAVAILABLE') "
                 "else (if ($temp.w_error != '') then $temp.w_error else 'WAREHOUSE_UNAVAILABLE'))")
    fail_text = ("concat('merch: ', $temp.m_status, ' HTTP ', $temp.m_http_status, ' ', $temp.m_reason, ' after ', $temp.m_attempts, "
                 "' attempt(s); warehouse: ', $temp.w_status, ' HTTP ', $temp.w_http_status, ' ', $temp.w_reason, ' after ', "
                 "$temp.w_attempts, ' attempt(s)')")
    fail_target = f"(if ({m_bad}) then 'merch' else 'warehouse')"
    fail_http = f"(if ({m_bad}) then $temp.m_http_status else $temp.w_http_status)"
    fail_att = f"(if ({m_bad}) then $temp.m_attempts else $temp.w_attempts)"
    deliver_both = [
        W.parallel("deliver to merchandising and warehouse in parallel", [
            [deliver("merchandising item", "merch_items", "temp.merch_json", "m")],
            [deliver("warehouse item (vendor contact masked)", "wh_items", "temp.wh_json", "w")]]),
        W.decision("both delivered?", [
            (ok, [track(P, "delivered", "'all'", "'ok'", "concat('merch ', $temp.m_status, ' / warehouse ', $temp.w_status)"),
                  W.assign("delivered", setv(res="'delivered'"))]),
            (None, [*dlq(P, fail_code, fail_text, fail_target, fail_http, "concat('deliver ', " + fail_target + ")", fail_att,
                        fam="'Items'"), W.assign("error queue", setv(res="'error_queue'"))])])]
    invalid = [*dlq(P, "'VALIDATION_FAILED'", "concat('item ', $temp.item, ' failed validation: ', $temp.dq_flags)", "'validation'",
                   step="'validate'", fam="'Items'"), W.assign("error queue", setv(res="'error_queue'"))]
    steps = [
        get_config(),
        W.assign("parse the envelope + item (util:parseXML)", item_parse_ops()),
        W.assign("validate (UPC check digit, prices, department, required)", setv(dq_flags=DQ_FLAGS)
                 + setv(valid="if ($temp.dq_flags = '') then 'Y' else 'N'")),
        W.assign("transform XML to JSON per target (warehouse gets a masked contact)", setv(merch_json=merch_json, wh_json=wh_json)),
        track(P, "validated", "'cai'", "if ($temp.valid = 'Y') then 'ok' else 'failed'",
              "concat('item ', $temp.item, ' dept ', $temp.dept, if ($temp.dq_flags = '') then ' all rules passed' else concat(' failed: ', $temp.dq_flags))"),
        W.decision("valid?", [("$temp.valid = 'N'", invalid), (None, deliver_both)]),
        W.assign("outcome", [W.op("output.outcome", "$temp.res"), W.op("output.detail", "$temp.dq_flags")]),
        W.end()]
    return C.process(G, P, "Item handler: parse, validate, transform to JSON, deliver merchandising + warehouse in parallel with "
                           "retry; failures go to the hospital (error queue) and the dead-letter topic. Private subprocess.",
                     W.flow(steps), CONF["agent"]["name"], inputs=HANDLER_IN, outputs=["outcome", "detail"],
                     temps=ITEM_TEMPS + CFG_TEMPS + pref_temps("m", "w"), temp_xml=dlq_ref(), rest=True, anonymous=False)


# ------------------------------------------------------------------ listeners (Kafka): thin, every fault caught
def capture_ops(fam_default):
    return setv(body="string($input.event/body)",
                msg_id=OR(H("mbr-msg-id"), ENV("messageID", "string($input.event/body)"), "concat('unknown-', util:generateUUID())"),
                rev=OR(H("mbr-rev"), "'1'"), key=OR(H("mbr-key"), f"substring-after({ENV('id', 'string($input.event/body)')}, ':')"),
                source=H("mbr-source"), topic="string($input.event/topic)", part="string($input.event/partitionId)",
                family=OR(H("mbr-family"), f"'{fam_default}'"), mtype=OR(H("mbr-type"), ENV("type", "string($input.event/body)")))


LISTENER_TEMPS = ["body", "msg_id", "rev", "key", "source", "topic", "part", "family", "mtype", "outcome", "dlq_id", "fcode"]
FAULT_CODE = ("(let $r := concat(string($output.faultInfo[1]/code), ' ', string($output.faultInfo[1]/reason)) return "
              "if (contains($r, 'xmlStringToElement') or contains($r, 'SAXParse')) then 'MALFORMED_XML' else 'CAI_FAULT')")


def listener(name, desc, conn, es, handler, fam, poison_to_queue=True):
    fault_text = ("concat('CAI fault in " + handler + ": ', string($output.faultInfo[1]/code), ' ', "
                  "string($output.faultInfo[1]/reason))")
    call = W.subflow(f"handle ({handler})", handler, gp(handler),
                     inputs=[(n, "field", f"temp.{n}") for n in HANDLER_IN],
                     out_fields=["outcome", "detail"], out_map=[("temp.outcome", "outcome")])
    to_queue = dlq(name, "$temp.fcode", fault_text, "'cai'", step=f"'{handler}'", mid="$temp.msg_id", rev="$temp.rev",
                   body="$temp.body", topic="$temp.topic", biz="$temp.key", fam="$temp.family", typ="$temp.mtype")
    if poison_to_queue:
        on_fault = [W.assign("classify the fault", setv(fcode=FAULT_CODE)), *to_queue]
    else:   # a second subscriber of the same topic: the first one already queued a poison message
        on_fault = [W.assign("classify the fault", setv(fcode=FAULT_CODE)),
                    W.decision("malformed?", [
                        ("$temp.fcode = 'MALFORMED_XML'", [track(name, "skipped", "'store'", "'skipped'",
                                                                 "'malformed payload: the item subscriber queued it'",
                                                                 mid="$temp.msg_id", rev="$temp.rev")]),
                        (None, to_queue)])]
    steps = [W.assign("capture the record + mbr-* headers", capture_ops(fam)),
             track(name, "consumed", "$temp.topic", "'ok'", "concat('partition ', $temp.part, ' key ', $temp.key, ' source ', $temp.source)",
                   mid="$temp.msg_id", rev="$temp.rev"),
             W.catching(call, ok_steps=[W.assign("handled", setv(fcode="''"))], fault_steps=on_fault),
             W.end()]
    ev = C.ref_field("event", f"{conn}:KafkaMessage", gc(conn), tag="parameter", required=True)
    return C.process(G, name, desc, W.flow(steps), CONF["agent"]["name"], rest=False, event_source=f"{conn}:{es}", input_xml=ev,
                     temps=LISTENER_TEMPS, temp_xml=dlq_ref())


# ------------------------------------------------------------------ purchase orders: validate, route, deliver, compensate
PO_FIELDS = [("po", "order_no"), ("version", "version"), ("supplier", "supplier"), ("dept", "dept"), ("location", "location"),
             ("total_cost", "total_cost"), ("line_count", "line_count"), ("not_before", "not_before_date"),
             ("not_after", "not_after_date"), ("order_type", "order_type")]
LINES = "util:parseXML($temp.inner)/descendant-or-self::*:PODtl"
DEC = lambda e: f"(if (string({e}) castable as xs:decimal) then xs:decimal(string({e})) else 0)"  # noqa: E731
LINES_JSON = ("concat('[', string-join(for $l at $i in " + LINES + " return concat('{\"line_no\":\"', string($i), '\",\"item\":', "
              + W.js("$l/*:item") + ", ',\"location\":', " + W.js("$l/*:location") + ", ',\"loc_type\":', " + W.js("$l/*:loc_type")
              + ", ',\"unit_cost\":', " + W.js("$l/*:unit_cost") + ", ',\"qty_ordered\":', " + W.js("$l/*:qty_ordered") + ", '}'), ','), ']')")
DC_ROUTE = ("(let $m := tokenize($temp.cfg_dc_map, ','), $f := substring($temp.location, 1, 1) "
            "return substring-after(($m[starts-with(., concat($f, ':'))])[1], ':'))")
PO_TEMPS = [t for t, _ in PO_FIELDS] + ["inner", "n_lines", "lines_total", "items_csv", "lines_json", "hdr_ok", "applied", "stale",
                                        "dc", "all_present", "missing", "merch_json", "wh_json", "ip_json", "cancel_json", "res", "dlq_id"]


def p_po_handle():
    P = "mbr_po_handle"
    parse = ([W.op("temp.inner", "string((util:parseXML($input.body)//*:messageData)[1])")]
             + [W.op(f"temp.{t}", X(f)) for t, f in PO_FIELDS]
             + setv(n_lines=f"string(count({LINES}))",
                    lines_total=f"string(round-half-to-even(sum(for $l in {LINES} return {DEC('$l/*:unit_cost')} * {DEC('$l/*:qty_ordered')}), 2))",
                    items_csv=f"string-join(distinct-values(for $l in {LINES} return string($l/*:item)), ',')",
                    lines_json=LINES_JSON))
    checks = setv(hdr_ok="(if (not($temp.line_count castable as xs:integer) or not($temp.total_cost castable as xs:decimal)) then 'N' "
                         "else if (xs:integer($temp.line_count) != xs:integer($temp.n_lines)) then 'N' "
                         "else if (abs(xs:decimal($temp.total_cost) - xs:decimal($temp.lines_total)) gt 0.005) then 'N' else 'Y')",
                  dc=DC_ROUTE)
    head = [("msg_id", "$input.msg_id"), ("rev", "$input.rev"), ("po", "$temp.po"), ("version", "$temp.version")]
    merch_json = J(head + [("supplier", "$temp.supplier"), ("dept", "$temp.dept"), ("location", "$temp.location"), ("dc", "$temp.dc"),
                           ("total_cost", "$temp.total_cost"), ("line_count", "$temp.line_count"), ("not_before", "$temp.not_before"),
                           ("not_after", "$temp.not_after"), ("order_type", "$temp.order_type"), ("lines_json", "$temp.lines_json", "raw")])
    wh_json = J(head + [("dc", "$temp.dc"), ("location", "$temp.location"), ("line_count", "$temp.line_count"),
                        ("lines_json", "$temp.lines_json", "raw")])
    stale = ("(if (($temp.version castable as xs:integer) and ($temp.applied castable as xs:integer)) then "
             "(if (xs:integer($temp.applied) gt 0 and xs:integer($temp.version) le xs:integer($temp.applied)) then 'Y' else 'N') else 'N')")
    out = lambda v: W.assign(v, [W.op("output.outcome", f"'{v}'")])  # noqa: E731
    steps = [
        get_config(),
        W.assign("parse the envelope + PO header and lines", parse),
        W.assign("header = lines check; route to a distribution center", checks),
        W.assign("transform XML to JSON per target", setv(merch_json=merch_json, wh_json=wh_json,
                                                         ip_json=J([("items", "$temp.items_csv"), ("msg_id", "$input.msg_id")]))),
        W.service("version already applied (ask the system of record)", MERCH, gc(MERCH), "po_version",
                  inputs=[("po", "field", "temp.po")], outputs=[("temp.applied", "version")]),
        W.assign("stale?", setv(stale=stale)),
        track(P, "validated", "'cai'", "if ($temp.hdr_ok = 'Y') then 'ok' else 'failed'",
              "concat('PO ', $temp.po, ' v', $temp.version, ' (applied v', $temp.applied, '), ', $temp.n_lines, ' lines, total ', "
              "$temp.total_cost, ', DC ', $temp.dc)"),
        W.decision("filter: stale, incomplete or unroutable?", [
            ("$temp.stale = 'Y'", [track(P, "skipped_stale", "'merch'", "'skipped'",
                                         "concat('PO ', $temp.po, ' v', $temp.version, ' is not newer than v', $temp.applied)"),
                                   out("skipped_stale"), W.end()]),
            ("$temp.hdr_ok = 'N'", [*dlq(P, "'PO_INCOMPLETE'", "concat('PO ', $temp.po, ': header says ', $temp.line_count, ' lines / ', "
                                        "$temp.total_cost, ' but ', $temp.n_lines, ' lines / ', $temp.lines_total, ' arrived')",
                                        "'validation'", step="'header = lines check'", fam="'Order'"), out("error_queue"), W.end()]),
            ("$temp.dc = ''", [*dlq(P, "'NO_DC'", "concat('PO ', $temp.po, ': no distribution center for location ', $temp.location)",
                                    "'routing'", step="'route'", fam="'Order'"), out("error_queue"), W.end()]),
            (None, [W.assign("go on", setv(res="''"))])]),
        deliver("items present in merchandising?", "merch_items_present", "temp.ip_json", "ip"),
        W.assign("read the answer", setv(
            all_present="if ($temp.ip_body != '') then string((util:parseXML($temp.ip_body)//*:all_present)[1]) else ''",
            missing="if ($temp.ip_body != '') then string((util:parseXML($temp.ip_body)//*:missing)[1]) else ''")),
        W.decision("all items present?", [
            (f"not($temp.ip_status = {OKS})", [*dlq(P, "'MERCH_UNAVAILABLE'", "concat('items check failed: HTTP ', $temp.ip_http_status, "
                                                   "' ', $temp.ip_reason, ' after ', $temp.ip_attempts, ' attempt(s)')", "'merch'",
                                                   "$temp.ip_http_status", "'items present?'", "$temp.ip_attempts", fam="'Order'"),
                                               out("error_queue"), W.end()]),
            ("$temp.all_present != 'true'", [*dlq(P, "'ITEMS_MISSING'", "concat('PO ', $temp.po, ' waits for items ', $temp.missing)",
                                                  "'merch'", step="'items present?'", fam="'Order'"),
                                             out("waiting_for_items"), W.end()]),
            (None, [W.assign("go on", setv(res="''"))])]),
        deliver("merchandising PO", "merch_pos", "temp.merch_json", "m"),
        W.decision("merchandising answer", [
            ("$temp.m_status = 'stale'", [track(P, "skipped_stale", "'merch'", "'skipped'", "concat('merch: ', $temp.m_reason)"),
                                          out("skipped_stale"), W.end()]),
            (f"not($temp.m_status = {OKS})", [*dlq(P, "if ($temp.m_error != '') then $temp.m_error else 'MERCH_UNAVAILABLE'",
                                                  "concat('merch ', $temp.m_status, ' HTTP ', $temp.m_http_status, ': ', $temp.m_reason, "
                                                  "' (after ', $temp.m_attempts, ' attempt(s))')", "'merch'", "$temp.m_http_status",
                                                  "'deliver merch'", "$temp.m_attempts", fam="'Order'"), out("error_queue"), W.end()]),
            (None, [W.assign("go on", setv(res="''"))])]),
        deliver("warehouse PO (routed DC)", "wh_pos", "temp.wh_json", "w"),
        W.decision("warehouse answer", [
            (f"$temp.w_status = {OKS}", [track(P, "delivered", "'all'", "'ok'", "concat('merch ', $temp.m_status, ' / warehouse ', "
                                                                               "$temp.w_status, ' at ', $temp.dc)"),
                                         W.assign("delivered", setv(res="'delivered'"))]),
            (None, [W.assign("compensation payload", setv(cancel_json=J([("msg_id", "$input.msg_id"), ("rev", "$input.rev"), ("po", "$temp.po"),
                                                                         ("reason", "concat('warehouse refused PO ', $temp.po, ': ', $temp.w_reason)")]))),
                    deliver("cancel the merchandising PO (compensation)", "merch_po_cancel", "temp.cancel_json", "c"),
                    *dlq(P, "if ($temp.w_error != '') then $temp.w_error else 'WAREHOUSE_UNAVAILABLE'",
                        "concat('warehouse ', $temp.w_status, ' HTTP ', $temp.w_http_status, ': ', $temp.w_reason, '; merch PO cancelled (', "
                        "$temp.c_status, ')')", "'warehouse'", "$temp.w_http_status", "'deliver warehouse'", "$temp.w_attempts", fam="'Order'"),
                    track(P, "compensated", "'merch'", "$temp.c_status", "concat('merch PO ', $temp.po, ' cancelled: the warehouse refused it')"),
                    W.assign("compensated", setv(res="'compensated'"))])]),
        W.assign("outcome", [W.op("output.outcome", "$temp.res")]),
        W.end()]
    return C.process(G, P, "PO handler: parse header + lines, header = lines check, skip stale versions (asks merchandising), route "
                           "to a DC, wait for missing items in the hospital (ITEMS_MISSING, retried), deliver merchandising then "
                           "warehouse with retry; a warehouse refusal cancels the merchandising PO (compensation). Private subprocess.",
                     W.flow(steps), CONF["agent"]["name"], inputs=HANDLER_IN, outputs=["outcome", "detail"],
                     temps=PO_TEMPS + CFG_TEMPS + pref_temps("ip", "m", "w", "c"), temp_xml=dlq_ref(), rest=True, anonymous=False)


# ------------------------------------------------------------------ store prices (a second subscriber of the item topic)
def p_store_handle():
    P = "mbr_store_price_handle"
    store_json = J([("msg_id", "$input.msg_id"), ("rev", "$input.rev"), ("item", "$temp.item"), ("unit_retail", "$temp.unit_retail"),
                    ("compare_at", "$temp.compare_at")])
    steps = [get_config(),
             W.assign("parse item prices", item_parse_ops()),
             W.assign("validate", setv(dq_flags=DQ_FLAGS) + setv(valid="if ($temp.dq_flags = '') then 'Y' else 'N'", store_json=store_json)),
             W.decision("filter: valid?", [
                 ("$temp.valid = 'N'", [track(P, "skipped", "'store'", "'skipped'", "concat('invalid item, not priced in stores: ', $temp.dq_flags)"),
                                        W.assign("skipped", setv(res="'skipped'"))]),
                 (None, [deliver("store prices (every store)", "store_prices", "temp.store_json", "p"),
                         W.decision("store answer", [
                             (f"$temp.p_status = {OKS}", [track(P, "delivered", "'store'", "'ok'",
                                                                "concat('price ', $temp.unit_retail, ' sent to the stores')"),
                                                          W.assign("ok", setv(res="'delivered'"))]),
                             (None, [*dlq(P, "if ($temp.p_error != '') then $temp.p_error else 'STORE_UNAVAILABLE'",
                                         "concat('store ', $temp.p_status, ' HTTP ', $temp.p_http_status, ': ', $temp.p_reason)", "'store'",
                                         "$temp.p_http_status", "'deliver store'", "$temp.p_attempts", fam="'Items'"),
                                     W.assign("error queue", setv(res="'error_queue'"))])])])]),
             W.assign("outcome", [W.op("output.outcome", "$temp.res")]), W.end()]
    return C.process(G, P, "Store-price handler: item price -> every store's POS; invalid items are skipped (the item subscriber "
                           "queues them). Private subprocess.", W.flow(steps), CONF["agent"]["name"], inputs=HANDLER_IN,
                     outputs=["outcome", "detail"], temps=ITEM_TEMPS + CFG_TEMPS + pref_temps("p"), temp_xml=dlq_ref(),
                     rest=True, anonymous=False)


def p_perf_listener():
    P = "mbr_perf_subscriber"
    inner = "util:parseXML(string((util:parseXML(string($input.event/body))//*:messageData)[1]))"
    payload = J([("msg_id", "$temp.msg_id"), ("rev", "$temp.rev"), ("stage", "'delivered'"), ("target", "'perf'"), ("status", "'ok'"),
                 ("detail", f"(let $p := {inner} return concat('perf seq ', string(($p/descendant-or-self::*:seq)[1]), ' run ', "
                            "string(($p/descendant-or-self::*:run)[1]), ' partition ', $temp.part))"),
                 ("process", f"'{P}'"), ("instance_id", "util:getProcessId()")])
    send = W.service("parse the ping + track delivered", LEDGER, gc(LEDGER), "track", inputs=[("payload", "formula", payload)])
    steps = [W.assign("capture", setv(msg_id=OR(H("mbr-msg-id"), "concat('unknown-', util:generateUUID())"), rev=OR(H("mbr-rev"), "'1'"),
                                      part="string($input.event/partitionId)", body="string($input.event/body)",
                                      topic="string($input.event/topic)", key=H("mbr-key"))),
             W.catching(send, ok_steps=[W.assign("ok", setv(fcode="''"))],
                        fault_steps=[*dlq(P, "'MALFORMED_XML'", "concat('ping not parsed: ', string($output.faultInfo[1]/reason))", "'cai'",
                                         step="'parse'", mid="$temp.msg_id", rev="$temp.rev", body="$temp.body", topic="$temp.topic",
                                         biz="$temp.key", fam="'Perf'", typ="'Ping'")]),
             W.end()]
    ev = C.ref_field("event", f"{KAF}:KafkaMessage", gc(KAF), tag="parameter", required=True)
    return C.process(G, P, "Kafka listener mbr-kafka:perf-sub (load test): parse the ping + one ledger write = 1 CAI run a message",
                     W.flow(steps), CONF["agent"]["name"], rest=False, event_source=f"{KAF}:perf-sub", input_xml=ev,
                     temps=LISTENER_TEMPS, temp_xml=dlq_ref())


# ------------------------------------------------------------------ JMS -> Kafka bridge (cutover)
def AH(n):
    return f"string(($input.event/headers[name = '{n}']/value)[1])"


def p_bridge(name, es, pub, family, topic):
    B = "$temp.body"
    hdr = lambda n, v: f"<headers><name>{n}</name><value>{{string({v})}}</value></headers>"  # noqa: E731
    headers = "(" + ", ".join([hdr("mbr-msg-id", "$temp.msg_id"), hdr("mbr-rev", "$temp.rev"), hdr("mbr-key", "$temp.key"),
                               hdr("mbr-family", "$temp.family"), hdr("mbr-type", "$temp.mtype"), hdr("mbr-sent-at", "$temp.sent_at"),
                               hdr("mbr-source", "$temp.source"), hdr("mbr-bridge", "'cai-jms-bridge'"),
                               hdr("mbr-jms-queue", "$temp.queue")]) + ")"
    # JMS properties with hyphens arrive only with jms.validatePropertyNames=false on the connection (L-CAI-123);
    # identifier-style names (mbr_msg_id) and the envelope stay as fallbacks
    cap = setv(body="string($input.event/body)")
    cap += setv(msg_id=OR(AH("mbr-msg-id"), AH("mbr_msg_id"), ENV("messageID", B), "concat('unknown-', util:generateUUID())"),
                key=OR(AH("mbr-key"), AH("mbr_key"), f"substring-after({ENV('id', B)}, ':')"),
                family=OR(AH("mbr-family"), AH("mbr_family"), ENV("family", B), f"'{family}'"),
                mtype=OR(AH("mbr-type"), AH("mbr_type"), ENV("type", B)),
                rev=OR(AH("mbr-rev"), AH("mbr_rev"), "'1'"),
                sent_at=OR(AH("mbr-sent-at"), AH("mbr_sent_at"), AH("JMSTimestamp")),
                source=OR(AH("mbr-source"), AH("mbr_source"), "'legacy-jms'"),
                queue=OR(AH("JMSDestination"), f"'{es}'"))
    cap += [W.op("temp.kmsg/messageKey", "$temp.key"), W.op("temp.kmsg/body", "$temp.body"), W.op("temp.kmsg/headers", headers)]
    produce = W.service(f"publish to Kafka {topic} (key = business id)", KAF, gc(KAF), pub, inputs=[("event", "field", "temp.kmsg")])
    steps = [W.assign("JMS TextMessage + properties -> Kafka record", cap),
             W.catching(produce,
                        ok_steps=[track(name, "bridged", f"'{topic}'", "'ok'", f"concat($temp.queue, ' -> {topic} key ', $temp.key)",
                                        mid="$temp.msg_id", rev="$temp.rev")],
                        fault_steps=[*dlq(name, "'KAFKA_PUBLISH_FAILED'", "concat('bridge could not publish to " + topic + ": ', "
                                          "string($output.faultInfo[1]/reason))", "'kafka'", step="'bridge'", mid="$temp.msg_id",
                                          rev="$temp.rev", body="$temp.body", topic="$temp.queue", biz="$temp.key", fam="$temp.family",
                                          typ="$temp.mtype")]),
             W.end()]
    ev = C.ref_field("event", f"{JMS}:AMQPMessage", gc(JMS), tag="parameter", required=True)
    kref = C.ref_field("kmsg", f"{KAF}:KafkaMessage", gc(KAF)) + dlq_ref()
    return C.process(G, name, f"JMS -> Kafka bridge for the cutover: legacy TextMessages from queue {es} are republished to Kafka "
                              f"{topic} with record key = business id and the mbr-* headers (native CAI Kafka producer).",
                     W.flow(steps), CONF["agent"]["name"], rest=False, event_source=f"{JMS}:{es}", input_xml=ev, temp_xml=kref,
                     temps=["body", "msg_id", "key", "family", "mtype", "rev", "sent_at", "source", "queue", "dlq_id"])


# ------------------------------------------------------------------ hospital: replay one entry, sweep the due ones
def p_replay():
    P = "mbr_error_queue_replay"
    hdr = lambda n, v: f"<headers><name>{n}</name><value>{{string({v})}}</value></headers>"  # noqa: E731
    headers = "(" + ", ".join([hdr("mbr-msg-id", "$temp.e_msg_id"), hdr("mbr-rev", "$temp.e_rev"), hdr("mbr-key", "$temp.e_biz"),
                               hdr("mbr-family", "$temp.e_family"), hdr("mbr-type", "$temp.e_type"), hdr("mbr-source", "'hospital'"),
                               hdr("mbr-replay", "string(xs:integer(if ($temp.e_replays castable as xs:integer) then $temp.e_replays else 0) + 1)")]) + ")"
    res = lambda v: [W.assign(v, [W.op("output.result", f"'{v}'")]), W.end()]  # noqa: E731
    produce = lambda pub: W.catching(  # noqa: E731
        W.service(f"republish ({pub})", KAF, gc(KAF), pub, inputs=[("event", "field", "temp.kmsg")]),
        ok_steps=[W.assign("published", setv(pub_ok="'Y'"))], fault_steps=[W.assign("publish failed", setv(pub_ok="'N'"))])
    steps = [
        W.service("read the hospital entry", LEDGER, gc(LEDGER), "eq_get", inputs=[("id", "field", "input.id")],
                  outputs=[("temp.e_result", "result"), ("temp.e_msg_id", "msg_id"), ("temp.e_rev", "rev"), ("temp.e_topic", "topic"),
                           ("temp.e_biz", "biz_id"), ("temp.e_family", "family"), ("temp.e_type", "type"),
                           ("temp.e_payload", "payload"), ("temp.e_status", "status"), ("temp.e_replays", "replays")]),
        W.decision("replayable?", [
            ("$temp.e_result != 'ok'", res("not_found")),
            ("not($temp.e_status = ('open', 'dead'))", res("not_replayable")),
            (None, [W.assign("rebuild the Kafka record", [W.op("temp.kmsg/messageKey", "$temp.e_biz"), W.op("temp.kmsg/body", "$temp.e_payload"),
                                                          W.op("temp.kmsg/headers", headers)])])]),
        W.decision("which topic?", [
            ("$temp.e_family = 'Items'", [produce("item-pub")]),
            ("$temp.e_family = 'Order'", [produce("po-pub")]),
            (None, res("unknown_family"))]),
        W.decision("published?", [
            ("$temp.pub_ok != 'Y'", res("publish_failed")),
            (None, [W.service("mark replayed", LEDGER, gc(LEDGER), "eq_mark", inputs=[("payload", "formula", J([
                ("id", "$input.id"), ("status", "'replayed'"), ("actor", "if ($input.actor != '') then $input.actor else 'operator'")]))]),
                track(P, "replayed", "$temp.e_family", "'ok'", "concat('hospital entry ', $input.id, ' replayed by ', $input.actor)",
                      mid="$temp.e_msg_id", rev="$temp.e_rev")])]),
        W.assign("result", [W.op("output.result", "'replayed'")]),
        W.end()]
    kref = C.ref_field("kmsg", f"{KAF}:KafkaMessage", gc(KAF))
    return C.process(G, P, "Replays one hospital (error queue) entry: republishes the original message to its Kafka topic with the "
                           "same message id (targets answer 'duplicate' for parts already applied) and marks the entry replayed. "
                           "Anonymous on the agent's own endpoint (operator console, drills, the hospital sweep).",
                     W.flow(steps), CONF["agent"]["name"], inputs=["id", "actor"], outputs=["result"],
                     temps=["e_result", "e_msg_id", "e_rev", "e_topic", "e_biz", "e_family", "e_type", "e_payload", "e_status",
                            "e_replays", "pub_ok"], temp_xml=kref, rest=True, anonymous=True)


def p_hospital():
    P = "mbr_hospital_retry"
    inc = W.assign("next entry", setv(i="string(xs:integer(if ($temp.i castable as xs:integer) then $temp.i else 0) + 1)"))
    call = W.subflow("replay it", "mbr_error_queue_replay", gp("mbr_error_queue_replay"),
                     inputs=[("id", "formula", "tokenize($temp.ids, ',')[xs:integer($temp.i)]"), ("actor", "const", "hospital")],
                     out_fields=["result"], out_map=[("temp.r", "result")])
    steps = [W.service("due entries", LEDGER, gc(LEDGER), "eq_due", outputs=[("temp.ids", "ids"), ("temp.n", "count")]),
             W.assign("loop start", setv(i="'0'", done="'0'")),
             inc,
             W.decision("another due entry?", [
                 ("($temp.n castable as xs:integer) and xs:integer($temp.i) le xs:integer($temp.n)",
                  [call, W.assign("count", setv(done="string(xs:integer($temp.done) + (if ($temp.r = 'replayed') then 1 else 0))")),
                   W.jump(inc.sid)]),
                 (None, [W.assign("done", setv(i="$temp.i"))])]),
             W.assign("result", [W.op("output.replayed", "$temp.done"), W.op("output.due", "$temp.n")]),
             W.end()]
    return C.process(G, P, "Hospital sweep (the legacy Hospital Retry adapter): replays every retryable entry whose next retry time "
                           "has come (backoff per entry, dead after the replay limit). Started every minute by the mbr-timer "
                           "container (the CAI scheduler does not start agent-run processes, L-CAI-142).",
                     W.flow(steps), CONF["agent"]["name"], inputs=["actor"], outputs=["replayed", "due"],
                     temps=["ids", "n", "i", "r", "done"], rest=True, anonymous=True)


# ------------------------------------------------------------------ package
PUBLISH_ORDER = (
    ["mbr_ledger_api.AI_SERVICE_CONNECTOR.xml", "mbr_merch_api.AI_SERVICE_CONNECTOR.xml", "mbr_wh_api.AI_SERVICE_CONNECTOR.xml",
     "mbr_store_api.AI_SERVICE_CONNECTOR.xml",
     "mbr_ledger.AI_CONNECTION.xml", "mbr_merch.AI_CONNECTION.xml", "mbr_wh.AI_CONNECTION.xml", "mbr_store.AI_CONNECTION.xml",
     "mbr-kafka.AI_CONNECTION.xml", "mbr-kafka-store.AI_CONNECTION.xml", "mbr-jms.AI_CONNECTION.xml",
     "mbr_deliver.PROCESS.xml", "mbr_item_handle.PROCESS.xml", "mbr_po_handle.PROCESS.xml", "mbr_store_price_handle.PROCESS.xml",
     "mbr_error_queue_replay.PROCESS.xml", "mbr_hospital_retry.PROCESS.xml",
     "mbr_item_subscriber.PROCESS.xml", "mbr_po_subscriber.PROCESS.xml", "mbr_store_price_subscriber.PROCESS.xml",
     "mbr_perf_subscriber.PROCESS.xml", "mbr_jms_bridge_items.PROCESS.xml", "mbr_jms_bridge_pos.PROCESS.xml"])
LISTENER_CONNECTIONS = ["mbr-kafka.AI_CONNECTION.xml", "mbr-kafka-store.AI_CONNECTION.xml", "mbr-jms.AI_CONNECTION.xml"]


def assets(consumers_on):
    f = CONF["project"]["folders"]
    F1, F2, F3, F4 = f["connections"], f["bridge"], f["subscribers"], f["errors"]
    tag = "Message Bus Replacement"
    A = []
    base = CONF["ledger_api"]["base_url"]
    for sc, conn, desc, acts in connectors():
        A.append((F1, sc, "AI_SERVICE_CONNECTOR", f"{tag}: {desc}", C.service_connector(G, sc, desc, acts, base), []))
    for sc, conn, desc, _ in connectors():
        A.append((F1, conn, "AI_CONNECTION", f"{tag}: {desc}", C.rest_connection(G, conn, sc, f"{desc}: {base} (agent host loopback)",
                                                                                  base, CONF["agent"]["name"]),
                  [G.guid("AI_SERVICE_CONNECTOR:" + sc)]))
    kmain, kstore = kafka_conns(consumers_on)
    A.append((F1, KAF, "AI_CONNECTION", f"{tag}: Kafka", kmain, []))
    A.append((F1, KSTORE, "AI_CONNECTION", f"{tag}: Kafka (store prices)", kstore, []))
    A.append((F1, JMS, "AI_CONNECTION", f"{tag}: legacy JMS over AMQP", jms_conn(consumers_on), []))
    rest = [gc(c) for c in (LEDGER, MERCH, WH, STORE)]
    t = CONF["kafka"]["topics"]
    q = CONF["artemis"]["queues"]
    A.append((F4, "mbr_deliver", "PROCESS", f"{tag}: delivery with retry + backoff", p_deliver(), rest))
    A.append((F3, "mbr_item_handle", "PROCESS", f"{tag}: item handler", p_item_handle(), rest + [gc(KAF), gp("mbr_deliver")]))
    A.append((F3, "mbr_po_handle", "PROCESS", f"{tag}: PO handler", p_po_handle(), rest + [gc(KAF), gp("mbr_deliver")]))
    A.append((F3, "mbr_store_price_handle", "PROCESS", f"{tag}: store-price handler", p_store_handle(), rest + [gc(KAF), gp("mbr_deliver")]))
    A.append((F4, "mbr_error_queue_replay", "PROCESS", f"{tag}: replay one hospital entry", p_replay(), [gc(LEDGER), gc(KAF)]))
    A.append((F4, "mbr_hospital_retry", "PROCESS", f"{tag}: hospital sweep", p_hospital(), [gc(LEDGER), gp("mbr_error_queue_replay")]))
    A.append((F3, "mbr_item_subscriber", "PROCESS", f"{tag}: item subscriber", listener(
        "mbr_item_subscriber", f"Kafka listener {KAF}:item-sub (topic {t['item']['name']}, key = item): thin; every fault is caught "
                               "and sent to the hospital + the dead-letter topic.", KAF, "item-sub", "mbr_item_handle", "Items"),
              [gc(KAF), gc(LEDGER), gp("mbr_item_handle")]))
    A.append((F3, "mbr_po_subscriber", "PROCESS", f"{tag}: PO subscriber", listener(
        "mbr_po_subscriber", f"Kafka listener {KAF}:po-sub (topic {t['po']['name']}, key = PO): thin; every fault is caught and sent "
                             "to the hospital + the dead-letter topic.", KAF, "po-sub", "mbr_po_handle", "Order"),
              [gc(KAF), gc(LEDGER), gp("mbr_po_handle")]))
    A.append((F3, "mbr_store_price_subscriber", "PROCESS", f"{tag}: store-price subscriber", listener(
        "mbr_store_price_subscriber", f"Kafka listener {KSTORE}:store-price-sub (its own group on {t['item']['name']}): store prices",
        KSTORE, "store-price-sub", "mbr_store_price_handle", "Items", poison_to_queue=False),
              [gc(KSTORE), gc(KAF), gc(LEDGER), gp("mbr_store_price_handle")]))
    A.append((F3, "mbr_perf_subscriber", "PROCESS", f"{tag}: load-test subscriber", p_perf_listener(), [gc(KAF), gc(LEDGER)]))
    A.append((F2, "mbr_jms_bridge_items", "PROCESS", f"{tag}: JMS bridge items",
              p_bridge("mbr_jms_bridge_items", "items-legacy", "item-pub", "Items", t["item"]["name"]), [gc(JMS), gc(KAF), gc(LEDGER)]))
    A.append((F2, "mbr_jms_bridge_pos", "PROCESS", f"{tag}: JMS bridge POs",
              p_bridge("mbr_jms_bridge_pos", "pos-legacy", "po-pub", "Order", t["po"]["name"]), [gc(JMS), gc(KAF), gc(LEDGER)]))
    assert q  # queues are named in the AMQP connection (jms_conn)
    return A


def offline_frs(cfg):
    rec = lambda i, n, d, kind, parents: {  # noqa: E731
        "id": i, "name": n, "description": d, "owner": "OFFLINE", "createdBy": "OFFLINE", "lastUpdatedBy": "OFFLINE",
        "lastAccessedBy": "OFFLINE", "createdTime": "2026-01-01T00:00:00Z", "lastUpdatedTime": "2026-01-01T00:00:00Z",
        "lastAccessedTime": "2026-01-01T00:00:00Z", "expiresBy": "2038-01-18T00:00:00Z", "documentType": kind,
        "contentType": "Binary", "documentState": "COMPLETE", "aclRule": "org", "subcontainerCount": 0, "parentInfo": parents}
    p = cfg["project"]
    proj = rec("OFFLINEPROJECTPLACEHOLD", p["name"], p["description"], "Project",
               [{"parentId": "OFFLINESPACE", "parentName": "OFFLINE", "parentType": "Space"}])
    folders = {n: rec(f"OFFLINEFOLDER{i:02d}PLACEHO"[:22], n, n, "Folder",
                      [{"parentId": proj["id"], "parentName": p["name"], "parentType": "Project"}])
               for i, n in enumerate(p["folders"].values())}
    return {"project": proj, "folders": folders}


def main():
    global G, CONF
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--consumers", choices=["off", "on"], default="off", help="author the listener consumers enabled (on) or not")
    ap.add_argument("--config", help="config file (default: config.json next to README.md)")
    ap.add_argument("--offline-frs", action="store_true", help="placeholder Project/Folder records (dry run; not importable)")
    ap.add_argument("--out", help="output folder (default build/cai)")
    ap.add_argument("--dump", action="store_true", help="also write every asset XML to <out>/xml/ for review")
    a = ap.parse_args()
    CONF = CFG.load(a.config, example_ok=a.offline_frs)
    out = Path(a.out) if a.out else CFG.BUILD / "cai"
    G = C.Guids(str((out / "guids.offline.json") if a.offline_frs else (CFG.STATE / "guids.json")))
    frs = offline_frs(CONF) if a.offline_frs else CFG.state_get("frs.json")
    if not frs:
        sys.exit("state/frs.json missing: run `python idmc/deploy_cai.py ensure-project` first (or --offline-frs for a dry run)")
    if not a.offline_frs:
        miss = CFG.placeholders(CONF, ["org.org_id_v3", "agent.name"])
        if miss:
            sys.exit("fill in config.json first: " + ", ".join(miss))
    A = assets(a.consumers == "on")
    man = C.package(G, "mbr_cai", CONF["project"]["name"], frs, A, CONF["org"].get("org_id_v3", ""), CONF["org"].get("org_name", ""),
                    str(out), publish_order=PUBLISH_ORDER)
    man["listener_connections"] = [man["by_name"][s] for s in LISTENER_CONNECTIONS]
    man["consumers"] = a.consumers
    import json
    (out / "mbr_cai.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    if a.dump:
        xd = out / "xml"
        xd.mkdir(parents=True, exist_ok=True)
        for folder, name, typ, desc, entry, refs in A:
            (xd / f"{name}.{typ}.xml").write_text(C.item(name, typ, desc, G.guid(f"{typ}:{name}"), entry), encoding="utf-8")
    kinds = {}
    for _, _, typ, *_ in A:
        kinds[typ] = kinds.get(typ, 0) + 1
    print(f"wrote {out / 'mbr_cai.zip'} ({os.path.getsize(out / 'mbr_cai.zip'):,} bytes): {len(A)} assets {kinds}; "
          f"consumers {a.consumers}; publish order {len(man['publish'])} paths")
    if a.offline_frs:
        print("NOTE: --offline-frs placeholders: this zip is for review only, not for import")


if __name__ == "__main__":
    main()
