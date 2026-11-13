# Message Bus Replacement: Kafka + Informatica CAI (`mbr_`)

**What it shows.** A retail integration bus of the Oracle Retail Integration Bus (RIB) pattern (JMS topics, one
subscriber adapter per receiving system, a transform / filter / route adapter, hospital tables with a retry adapter)
replaced by **Apache Kafka** for the topics and **Informatica Cloud Application Integration (CAI)** for everything
around them. Items and purchase orders flow to simulated merchandising, warehouse and store systems; failures go to a
hospital (error queue) with timed retry, a dead-letter topic and replay; during the cutover a CAI bridge carries the
legacy JMS queues onto Kafka; a nightly CDI batch loads the day's data into Oracle.

Rebuild time: about 2-3 hours from an empty org with a Secure Agent host ready (most of it waiting for images, the
agent's Process Server and publish jobs). Start with [BUILD.md](BUILD.md).

## 1. Architecture (one picture)

```
 SENDERS (simulated)            THE BUS                 READERS = CAI on the Secure Agent           TARGETS (simulated)
 ------------------             -------                 ---------------------------------           -------------------
 verify/send.py --via kafka --> Kafka topic mbr.item --> mbr_item_subscriber --> mbr_item_handle ---> merchandising (items)
   (record key = business id,   (3 partitions, 7 days)   (group mbr-cai-item)    validate, transform +-> warehouse (items, masked contact)
    mbr-* headers)                                  \--> mbr_store_price_subscriber -> _handle ----> store POS (price per store)
                                                         (group mbr-cai-store-price, own connection)
                                Kafka topic mbr.po ----> mbr_po_subscriber --> mbr_po_handle ------> merchandising (PO header+lines)
                                                         (group mbr-cai-po)    header=lines, stale?,  -> warehouse (PO, routed DC)
                                                                               route DC, items there?   (refusal -> cancel the
                                                                                                         merchandising PO)
 LEGACY (cutover only)
 verify/send.py --via jms ----> Artemis queues --------> mbr_jms_bridge_items / _pos --(native Kafka producer)--> the topics above
   (JMS TextMessage + props)    mbr.items.legacy / mbr.pos.legacy (AMQP 1.0)

 EVERY delivery goes through mbr_deliver: retry 5xx / timeouts with exponential backoff (2, 4, 8, 16 s), 409 = stale,
 4xx = rejected. Every failure: hospital entry (reason, retryable?) + a copy on Kafka topic mbr.dlq + a ledger event.
 HOSPITAL: mbr_hospital_retry (every minute, from the mbr-timer container) replays due entries through
 mbr_error_queue_replay (republish to the original topic, same message id); operators replay or discard by id.

 OPS LEDGER + HOSPITAL + SIMULATED TARGETS = Postgres (schema mbr) behind PostgREST (SQL functions, no program code)
 NIGHTLY: CDI taskflow tf_mbr_nightly_batch (3 Copy Data tasks) Postgres -> Oracle Free (schema MBR_BATCH), 02:30.
 IDMC (cloud): design, publish, monitor. The Secure Agent (your network) runs every CAI process and CDI task.
```

What replaces what (the legacy pattern on the left):

| Legacy bus piece | Here | Shown by |
|---|---|---|
| JMS topics | Kafka topics `mbr.item`, `mbr.po` (key = business id: per-key order on one partition) | every message |
| Subscriber (SUB) adapter per system | one CAI Kafka listener per receiving system, each with its own consumer group | item reaches 3 systems through 2 groups |
| Transform / filter / route adapter | the handler subprocesses: validate, XML to JSON per target, mask, filter stale / invalid, route a PO to its distribution center | `drills.py validation`, `send.py po` |
| Hospital tables + hospital retry adapter | `mbr.error_queue` with reason codes (retryable or not), `mbr_hospital_retry` sweep with backoff, dead after 3 replays; `mbr.dlq` topic | `drills.py outage`, `missing-items`, `poison` |
| Reprocess / replay | `mbr_error_queue_replay` (operator or sweep), Kafka retention 7 days for a re-read | `ops.py replay <id>` |
| Publisher (PUB) adapter onto JMS during cutover | `mbr_jms_bridge_*`: Artemis (AMQP 1.0) to Kafka with key + headers | `send.py --via jms` |
| Adapter manager (start / stop a subscriber) | CAI restadmin `eventconnection` stop / start per event source | `drills.py restart` |
| Overnight batch into the database | CDI Copy Data tasks + taskflow + schedule into Oracle | `cdi_batch.py run` |

## 2. IDMC services used

- **Application Integration (CAI)** with the **Process Server on a Secure Agent** (Kafka and AMQP listeners run only on
  an agent): 4 REST service connectors, 7 app connections, 12 processes, all generated as XML by
  [idmc/gen_cai.py](idmc/gen_cai.py) and imported headless.
- **Data Integration (CDI)**: 2 connections (PostgreSQL, Oracle), 3 mapping tasks over the Add-On Bundle template
  `dsst__copy_data_new_tgt`, 1 taskflow, 1 schedule ([idmc/cdi_batch.py](idmc/cdi_batch.py)).
- Platform REST: v3 import / objects, FRS, v2 connections / tasks / schedules, CAI `asset/v1` publish and update,
  CAI restadmin. All through the core library (`14 - Claude Working Methods & Tooling/Script Library/`).

## 3. Real vs stand-in

| Piece | Real or stand-in | Where it runs |
|---|---|---|
| Kafka 4.3 (KRaft, 1 node = broker + controller) | real product, demo-sized (production: 3+ brokers, replication 3) | container `mbr-kafka` |
| Legacy JMS broker | stand-in: ActiveMQ Artemis (AMQP 1.0 + STOMP) | container `mbr-artemis` |
| All integration logic | real: CAI processes | the Secure Agent's Process Server |
| Merchandising, warehouse, store POS | SIMULATED: tables + SQL functions behind PostgREST, idempotent, with fault injection (down / slow / reject) | containers `mbr-pg` + `mbr-api` |
| Ops ledger + hospital | demo store: Postgres tables, written by CAI over REST | `mbr-pg` + `mbr-api` |
| Senders (legacy system, apps) | SIMULATED by `verify/` scripts (Python: traffic generation only) | the Docker host |
| Nightly batch target | real product, free edition: Oracle Database Free 23 | container `mbr-oracle` |
| Hospital sweep timer | curl in a loop (the CAI scheduler does not start agent-run processes, KB L-CAI-142) | container `mbr-timer` |

**No Python in the runtime path.** Every message is moved, checked, transformed, routed, retried and replayed by CAI.
The stand-in systems are SQL (PostgREST serves SQL functions; no application code of ours). Python only builds,
deploys, sends test traffic and reads results. A variant where the stand-ins are CAI processes themselves (a labelled
"stand-ins" folder writing through a JDBC / Data Access Service connector) was designed in the source work but not
deployed, because that connector would not publish in one org (KB L-CAI-139); PostgREST avoids the dependency.

## 4. Message flow, step by step (one item)

1. A sender publishes the item XML to `mbr.item` with key = item number and headers `mbr-msg-id`, `mbr-rev`,
   `mbr-key`, `mbr-family`, `mbr-type`, `mbr-source`, `mbr-sent-at` (a CAI listener reads headers and value; the key
   only picks the partition, and `messageKey` arrives empty on consume, KB L-CAI-118).
2. `mbr_item_subscriber` (group `mbr-cai-item`) captures the record, writes `consumed`, calls `mbr_item_handle`
   inside a catch: any fault (for example malformed XML) becomes a hospital entry + a dead-letter copy.
3. The handler reads the settings (retry, departments), parses with `util:parseXML`, runs the rules (UPC-A check digit,
   price > 0, compare-at >= price, department list, required fields), builds one JSON per target (the warehouse gets
   the vendor contact masked) and delivers to merchandising and warehouse **in parallel**, each through `mbr_deliver`.
4. `mbr_deliver` retries a 5xx or a timeout (the action's `requestTimeout` is in seconds: 10) with backoff from the
   ledger config; a 2xx `duplicate` means an idempotent target had it already.
5. Both delivered: `delivered`. Otherwise: a hospital entry with the target's reason code; retryable codes are replayed
   by the sweep with a growing backoff.
6. Independently, `mbr_store_price_subscriber` (its own group and connection) prices the item in every store.

A purchase order follows the same shape in `mbr_po_handle`: header = lines check (count and total), skip a version
that is not newer than the one merchandising has applied (asked from merchandising, the system of record, each time),
route to a distribution center from the ship-to location (`dc_map` setting), check that all its items exist (if not:
hospital `ITEMS_MISSING`, replayed when they arrive), deliver merchandising then warehouse; a warehouse refusal cancels
the merchandising PO (compensation) and opens a hospital entry.

## 5. Measured in the source build (the demo this blueprint generalizes; same CAI patterns, one Secure Agent, 8 vCPU)

- 40 msg/s steady kept up (p95 331 ms end to end); bursts of 200 msg/s drained about 30 msg/s with 3 consumers and
  about 47 msg/s with 6 (KB L-CAI-126).
- A 2,000-line PO (423 KB) and a 19,500-line PO (4.1 MB) delivered over Kafka and over the JMS bridge in 1.3-5.3 s
  (KB L-CAI-127).
- Listener stop / start mid-stream: nothing lost; with `autoCommitIntervalMs=1000` about 10 of 600 records were read
  twice and answered `duplicate` (KB L-CAI-121). One event source stopped while the others kept consuming (L-CAI-147).
- Target outage cleared 6-7 s after the target came back, no operator.
These numbers are from the source build, not from this generic form: re-measure with `verify/` in your org.

## 6. CAI API calls per message, and how to read them on the CAI Monitor

**The unit.** One CAI API call = one run of a process or subprocess on the Process Server. The connector calls inside a
run (REST, a Kafka produce, a ledger write) add none (KB L-CAI-096). Runs of stand-ins would not count as the
customer's calls; in this blueprint the stand-ins are SQL, so every CAI run you see is solution logic.

**The rule** (KB L-CAI-148): calls per message = **S x (1 + h) + d + b + r**
- S = the subscribers (consumer groups) that receive the message,
- h = 1 when each listener calls a separate handler subprocess (0 when the logic sits in the listener),
- d = the runs of the delivery subprocess (one per call to a target, when every target call goes through it),
- b = 1 when the JMS-to-Kafka bridge carried it (cutover only),
- r = the re-runs it needed (a hospital replay re-runs the whole path for every subscriber of that topic, plus 1 for
  `mbr_error_queue_replay`).

| Message (this blueprint's design) | S | h | d | b | calls |
|---|---|---|---|---|---|
| Item over Kafka | 2 (item, store price) | 1 | 3 (merchandising, warehouse, store) | 0 | **7** |
| Item over JMS (bridge) | 2 | 1 | 3 | 1 | **8** |
| PO over Kafka | 1 | 1 | 3 (items check, merchandising, warehouse) | 0 | **5** |
| PO over JMS | 1 | 1 | 3 | 1 | **6** |
| PO refused by the warehouse | 1 | 1 | 4 (+ the cancel) | 0 | **6** |
| Load-test ping | 1 | 0 | 0 | 0 | **1** |
| Hospital sweep | per minute, not per message: 1 run (+ 1 per replayed entry, + that message's path) | | | | 1,440 a day idle |

Retries inside `mbr_deliver` are Wait steps in the same run: they add no call. The source build, whose PO path had an
extra routing stage (per-distribution-center topics, a DC listener and a warehouse handler), measured PO 9 (10 over
JMS) and item 7 (8) on the CAI Monitor. The cheapest production pattern keeps the target calls and retries inside the
listener: 1 call per subscriber (h = 0, d = 0), at the cost of holding the partition during waits (KB L-CAI-120).

**Read it on the Monitor, not from a ledger.** A count from ledger events misses every run that writes no event
(delivery subprocesses, pass-through listeners) and read 2-5 calls a message where the Monitor showed 7-10.
1. `python verify/ops.py reset --yes`, stop the timer (`docker stop mbr-timer`), note the time.
2. Send a known number of messages, e.g. 10 items: `for i in 1..10: python verify/send.py item --no-wait`.
3. In IDMC: **Monitor** > **Application Integration** (the process run list; on some pods "Process Instances"), filter
   the time window and the project's processes (`mbr_`), and count the runs per process name.
4. calls per message = total runs / messages; per process it shows which term (S, h, d, b) each run is.

## 7. Folder map

| Path | What |
|---|---|
| [BUILD.md](BUILD.md) | the numbered rebuild, gotchas, UI-only walls, undo |
| [config.example.json](config.example.json) | every name and setting; copy to `config.json` |
| [ENV_KEYS.md](ENV_KEYS.md) | the toolkit `.env` keys this blueprint needs |
| [infra/](infra/) | docker-compose (Kafka, Artemis, Postgres, PostgREST, Oracle Free, timer), SQL, topic script |
| [idmc/](idmc/) | `gen_cai.py` (package generator), `deploy_cai.py`, `listener_ctl.py`, `cdi_batch.py`, `lib/`, `templates/` |
| [verify/](verify/) | `send.py` (item, PO, 19,500-line PO, smoke), `drills.py`, `load_test.py`, `ops.py` (operator console) |
| [dashboards/](dashboards/) | `export_views.py`: the ledger views as CSV for any BI tool (optional) |
| [teardown/](teardown/) | `teardown.py` (reverse order), `pg_undo.sql` |

## 8. Credentials needed

All live in the toolkit `.env` (outside this folder; see `setup/.env.example`), read by key name, never printed.

| Key | What it is | Where to get it |
|---|---|---|
| `IDMC_USER` | IDMC login with Designer + Operator + Admin privileges in the target org | your IDMC administrator |
| `IDMC_PASS` | that login's password | your IDMC administrator (one rejected login writes a block file) |
| `IDMC_LOGIN_HOST` | the domain login host, e.g. `dm-us.informaticacloud.com` | the URL you sign in at, without the pod label |
| `MBR_PG_USER` | Postgres superuser of the `mbr-pg` container | you choose it |
| `MBR_PG_PASSWORD` | its password | you choose it (long, random) |
| `MBR_PGRST_AUTH_PASSWORD` | password of the role `mbr_api_login` that PostgREST uses (URL-safe characters: it sits in a URI) | you choose it |
| `MBR_CDI_PG_PASSWORD` | password of the read-only role `mbr_batch_reader` (IDMC PostgreSQL connection) | you choose it |
| `MBR_ARTEMIS_USER` | Artemis user (legacy JMS stand-in and the CAI AMQP connection) | you choose it |
| `MBR_ARTEMIS_PASSWORD` | its password (set into CAI with `asset/v1/update`, never in a package) | you choose it |
| `MBR_ORACLE_PASSWORD` | SYS / SYSTEM password of the Oracle Free container | you choose it |
| `MBR_ORACLE_BATCH_PASSWORD` | password of the Oracle schema user `MBR_BATCH` (nightly batch target) | you choose it |
| `MBR_KAFKA_CLUSTER_ID` | the KRaft cluster id | `docker run --rm apache/kafka:4.3.1 /opt/kafka/bin/kafka-storage.sh random-uuid` |

Non-secret ids (org id, agent name, runtime environment id, template task id) go in `config.json`; ids the build
creates go to `state/ids.json`. Do not share `config.json`, `state/` or `build/`.

## 9. Optional extras (not scripted here)

The source build also ran these on the same ledger; each has a KB topic and core script:
CDC (Database Ingestion) from the Postgres ledger to a warehouse (`Script Library/idmc_dbmi.py`; Postgres already runs with
`wal_level=logical`; KB `04 - Mass Ingestion & CDC`), a bronze / silver / gold medallion with pushdown (KB
`03 - Data Integration (CDI)`), Data Quality rules and profiling (KB `06`), catalog lineage and a glossary
(`Script Library/idmc_cdgc.py`, KB `07`). If the target is used for analytics, run quality and lineage on it directly; if
it is operational, copy it with CDC first.
