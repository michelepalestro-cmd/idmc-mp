"""mbr_msgs.py - stand-in traffic + read-back helpers for verify/ (standard library only; offline tooling, never runtime).

- Messages: a legacy-bus style envelope (family, type, id, messageID, messageData = the escaped business XML) around
  an item (ItemDesc) or a purchase order (PODesc with PODtl lines). Synthetic data only.
- Kafka: sent with the broker's own console producer inside the mbr-kafka container (`docker exec -i`), with the record
  key and the mbr-* headers (the CAI listener reads headers and value; the key picks the partition).
- Legacy JMS: sent as a STOMP frame to ActiveMQ Artemis with the mbr-* headers as message properties. No content-length
  header: with one, Artemis makes a BytesMessage and the CAI AMQP consumer (Payload Format Text) would not get text.
- Read-back: the ledger API (PostgREST) on 127.0.0.1:18080: /events, /error_queue, /targets, /po_status, /rpc/*.
Run these scripts on the Docker host (or point DOCKER_HOST at it); credentials come from the toolkit .env by key name.
"""
from __future__ import annotations

import html
import json
import random
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import mbr_config as CFG  # noqa: E402

E = lambda s: html.escape(str(s), quote=False)  # noqa: E731
HDR_DELIM, KEY_SEP = "|H|", "|K|"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"


def new_id(prefix="m"):
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


# ------------------------------------------------------------------ business payloads
def upc(seed=None):
    """A 12-digit UPC-A with a valid check digit (the CAI validation recomputes it)."""
    r = random.Random(seed)
    d = [r.randint(0, 9) for _ in range(11)]
    s = 3 * sum(d[0::2]) + sum(d[1::2])
    return "".join(map(str, d)) + str((10 - s % 10) % 10)


def item_xml(item, dept="110", unit_retail="19.99", compare_at="29.99", good_upc=True, email="buyer@example.com"):
    u = upc(item) if good_upc else upc(item)[:11] + str((int(upc(item)[11]) + 1) % 10)
    return ("<ItemDesc>" + "".join(f"<{k}>{E(v)}</{k}>" for k, v in [
        ("item", item), ("item_desc", f"Demo item {item}"), ("short_desc", f"Item {item}"), ("dept", dept), ("class", "10"),
        ("subclass", "1"), ("unit_retail", unit_retail), ("compare_at_price", compare_at), ("upc", u), ("supplier", "SUP001"),
        ("status", "A"), ("vendor_contact_email", email)]) + "</ItemDesc>")


def po_xml(po, items, lines=3, version=1, location="1001", break_totals=False):
    """A PO whose header totals match its lines (break_totals=True makes the header lie)."""
    dtl, total = [], 0.0
    for i in range(lines):
        it = items[i % len(items)]
        cost, qty = 5.25 + (i % 7), 1 + (i % 12)
        total += cost * qty
        dtl.append(f"<PODtl><item>{E(it)}</item><location>{location}</location><loc_type>W</loc_type>"
                   f"<unit_cost>{cost:.2f}</unit_cost><qty_ordered>{qty}</qty_ordered></PODtl>")
    total = round(total, 2) + (100 if break_totals else 0)
    head = "".join(f"<{k}>{E(v)}</{k}>" for k, v in [
        ("order_no", po), ("version", version), ("supplier", "SUP001"), ("dept", "110"), ("location", location),
        ("total_cost", f"{total:.2f}"), ("line_count", lines), ("not_before_date", "2026-11-01"),
        ("not_after_date", "2026-11-30"), ("order_type", "N")])
    return f"<PODesc>{head}{''.join(dtl)}</PODesc>"


def envelope(family, mtype, biz_id, msg_id, inner_xml, kind):
    """One line, no newline: the console producer reads one record per line."""
    return (f"<Messages><message><family>{family}</family><type>{mtype}</type><id>{kind}:{E(biz_id)}</id>"
            f"<messageID>{msg_id}</messageID><messageData>{E(inner_xml)}</messageData></message></Messages>")


def headers_for(msg_id, key, family, mtype, rev="1", source="verify"):
    return {"mbr-msg-id": msg_id, "mbr-rev": rev, "mbr-key": key, "mbr-family": family, "mbr-type": mtype,
            "mbr-source": source, "mbr-sent-at": now_iso()}


# ------------------------------------------------------------------ Kafka (console producer in the broker container)
def kafka_cmd(cfg, topic):
    k = cfg["kafka"]
    return ["docker", "exec", "-i", k.get("container", "mbr-kafka"), "/opt/kafka/bin/kafka-console-producer.sh",
            "--bootstrap-server", "localhost:9092", "--topic", topic,
            "--producer-property", "max.request.size=5242880", "--producer-property", "acks=all",
            "--property", "parse.key=true", "--property", f"key.separator={KEY_SEP}",
            "--property", "parse.headers=true", "--property", f"headers.delimiter={HDR_DELIM}",
            "--property", "headers.separator=,", "--property", "headers.key.separator=:"]


def kafka_line(key, headers, value):
    for v in list(headers.values()) + [key]:
        if "," in str(v) or HDR_DELIM in str(v) or KEY_SEP in str(v):
            raise ValueError(f"header/key value may not contain ',' or the delimiters: {v!r}")
    if "\n" in value or HDR_DELIM in value or KEY_SEP in value:
        raise ValueError("value must be one line without the delimiters")
    return ",".join(f"{k}:{v}" for k, v in headers.items()) + HDR_DELIM + key + KEY_SEP + value


def kafka_send(cfg, topic, records, dry=False):
    """records: [(key, headers, value)]; one docker exec for the whole batch."""
    lines = "\n".join(kafka_line(*r) for r in records) + "\n"
    if dry:
        print(f"[dry] {len(records)} record(s) -> {topic} ({len(lines):,} bytes)")
        return 0
    p = subprocess.run(kafka_cmd(cfg, topic), input=lines.encode("utf-8"), capture_output=True)
    if p.returncode != 0:
        sys.exit(f"kafka-console-producer failed ({p.returncode}): {p.stderr.decode(errors='replace')[:600]}")
    return len(records)


def kafka_stream(cfg, topic):
    """An open console producer for paced sends (load test): write kafka_line()+'\\n' to .stdin, then close()."""
    return subprocess.Popen(kafka_cmd(cfg, topic), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def group_lag(cfg, group):
    k = cfg["kafka"]
    p = subprocess.run(["docker", "exec", k.get("container", "mbr-kafka"), "/opt/kafka/bin/kafka-consumer-groups.sh",
                        "--bootstrap-server", "localhost:9092", "--describe", "--group", group], capture_output=True)
    out = p.stdout.decode(errors="replace")
    lag, members = 0, set()
    for line in out.splitlines()[1:]:
        f = line.split()
        if len(f) >= 7 and f[5].isdigit():
            lag += int(f[5])
            members.add(f[6])
    return {"group": group, "lag": lag, "members": len(members - {"-"}), "raw": out.strip()[-800:]}


# ------------------------------------------------------------------ legacy JMS (STOMP 1.2 to Artemis)
def _esc(v):
    return str(v).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace(":", "\\c")


def jms_send(cfg, queue, headers, body, dry=False):
    a = cfg["artemis"]
    user, pw = CFG.env_value("MBR_ARTEMIS_USER"), CFG.env_value("MBR_ARTEMIS_PASSWORD")
    if dry:
        print(f"[dry] STOMP SEND -> {queue} ({len(body):,} bytes, {len(headers)} properties)")
        return
    if not user or not pw:
        sys.exit("MBR_ARTEMIS_USER / MBR_ARTEMIS_PASSWORD not in the environment or the toolkit .env")
    if "\x00" in body:
        sys.exit("a STOMP text body may not contain NUL")
    s = socket.create_connection((a["host"], int(a.get("stomp_port", 61616))), timeout=30)
    try:
        s.sendall(f"CONNECT\naccept-version:1.2\nhost:localhost\nlogin:{_esc(user)}\npasscode:{_esc(pw)}\n\n\x00".encode())
        if not _read_frame(s).startswith("CONNECTED"):
            sys.exit("STOMP CONNECT refused (check the Artemis user / password)")
        rid = uuid.uuid4().hex[:8]
        hdr = "".join(f"{_esc(k)}:{_esc(v)}\n" for k, v in headers.items())
        frame = (f"SEND\ndestination:{queue}\ndestination-type:ANYCAST\ncontent-type:text/plain\npersistent:true\n"
                 f"receipt:{rid}\n{hdr}\n").encode() + body.encode("utf-8") + b"\x00"
        s.sendall(frame)
        f = _read_frame(s)
        if not f.startswith("RECEIPT"):
            sys.exit("STOMP SEND not confirmed: " + f[:300])
        s.sendall(b"DISCONNECT\n\n\x00")
    finally:
        s.close()


def _read_frame(s):
    buf = b""
    while b"\x00" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    return buf.split(b"\x00")[0].decode(errors="replace").lstrip("\n")


# ------------------------------------------------------------------ ledger API (PostgREST)
def api(cfg, path, body=None, method=None):
    url = cfg["ledger_api"]["base_url"].rstrip("/") + path
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data is not None else "GET"),
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"null")
        except ValueError:
            return e.code, raw.decode(errors="replace")


def events(cfg, msg_id):
    st, rows = api(cfg, "/events?msg_id=eq." + urllib.parse.quote(msg_id) + "&order=id")
    return rows if st == 200 and isinstance(rows, list) else []


def wait_stage(cfg, msg_id, stages, timeout=120, need=1):
    """Wait until `need` events of msg_id are in one of `stages`; returns (ok, events)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        ev = events(cfg, msg_id)
        if sum(1 for e in ev if e.get("stage") in stages) >= need:
            return True, ev
        time.sleep(2)
    return False, events(cfg, msg_id)


def error_queue(cfg, msg_id):
    st, rows = api(cfg, "/error_queue?msg_id=eq." + urllib.parse.quote(msg_id) + "&order=id")
    return rows if st == 200 and isinstance(rows, list) else []


def show(ev):
    for e in ev:
        print(f"    {str(e.get('at'))[11:23]} {e.get('process', ''):28} {e.get('stage', ''):14} {e.get('target', ''):10} "
              f"{e.get('status', ''):10} {str(e.get('detail', ''))[:90]}")


def agent_post(cfg, process, body, timeout=120):
    """POST to an anonymous process on the agent (run this on the agent host: the engine port is local)."""
    url = cfg["agent"]["process_engine_url"].rstrip("/") + "/" + process
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except OSError as e:
        return 0, str(e)
