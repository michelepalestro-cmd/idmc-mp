# CAI Event Listeners: Kafka & AMQP (JMS)

**Answers:** How to build event-driven CAI headless: Kafka and AMQP (JMS) listener connections, event-bound processes and the
native Kafka producer, authored in an import package and published over REST; how to start one safely, stop and start it on a
schedule, and keep messages from being lost or applied twice; how the listener dispatches, what it costs in throughput, and which
settings break silently.

**Read when:** before you put CAI between a message broker and the systems behind it (a JMS-to-Kafka bridge, a subscriber per
target, a windowed or late subscriber), and whenever a listener consumes nothing, consumes twice or lags.

**Key rules:**
- Kafka and AMQP connections, event-bound processes and catch handlers author headless in an import package; nothing here needs
  the designer (L-CAI-116, L-CAI-118).
- Publish a new consumer disabled, publish its processes, then enable and republish the connection (L-CAI-119).
- One process at a time per consumer: keep Kafka-started processes short and make holds and approvals hand-offs (L-CAI-120).
- A stop resumes from the last offset auto-commit: make targets idempotent and set `autoCommitIntervalMs=1000` (L-CAI-121).
- Start and stop event sources with restadmin `eventconnection` and the `IDS-SESSION-ID` header (L-CAI-122).
- Over AMQP, JMS property names with hyphens or dots vanish unless `jms.validatePropertyNames=false` (L-CAI-123).
- After every connection publish read the agent's catalina log: a route can fail while the publish says SUCCESS (L-CAI-125).

**Related:** [CAI Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md) ·
[CAI Runtime](02-cai-runtime-invoke-urls-control.md) · [CAI Connections & Connectors](03-cai-connections-connectors-e.g.-salesforce-oauth.md) ·
[Process Server on a Secure Agent](04-process-server-on-a-secure-agent.md) · [CAI Troubleshooting](05-cai-troubleshooting-stuck-assets.md) ·
[Lessons: CAI](../../lessons/by-domain/05-application-integration-cai.md)

**Last verified:** 2026-10-09

> **Summary.** CAI listens to Kafka and to AMQP 1.0 brokers (a JMS broker such as ActiveMQ Artemis) through Camel-based
> connections that run only on a Secure Agent's Process Server. Everything is authored as repository-item XML in a v3 import
> package and published with `asset/v1/publish`, like any other CAI asset. The listener runs one process at a time per consumer
> thread and commits offsets on a timer, so the design rules are: thin listeners that hand each message to a handler subprocess
> inside a catch, idempotent targets, hand-offs instead of waits, and one connection per subscriber you want to control on its own.
> Measured on one agent: about 30 msg/s with 3 consumers and 47 msg/s with 6, 4 MB messages in about 5 s, nothing lost across
> stops, restarts and outages.

---

## 1. The pieces

| Asset | What it holds | Lesson |
|---|---|---|
| AI_CONNECTION, Kafka | brokers, the event sources (consumers: topic, consumer group, content format, Camel options) and the event targets (producers) | L-CAI-116 |
| AI_CONNECTION, AMQP | broker host and port, SASL user and password, Query Parameters, the event sources (queue, payload format, dead-letter queue) | L-CAI-116, L-CAI-123 |
| Listener process | `<event eventSource="<conn>:<eventSource>"/>` in its deployment, input `event` typed `<conn>:KafkaMessage` or `<conn>:AMQPMessage` | L-CAI-118 |
| Handler subprocess | no access configuration: no URL, callable only as a subprocess | L-CAI-130 |
| Producer call | a Service step on `<conn>:<eventTarget>` with a KafkaMessage (key, value, headers) | L-CAI-124 |

Both connection types run only on a Secure Agent (`agentOnly="true"`, `<agent><agent name></agent>`); the Process Server must
be running there ([Process Server on a Secure Agent](04-process-server-on-a-secure-agent.md)).

## 2. Authoring the connection (L-CAI-116)

Kafka, inside the AI_CONNECTION entry of a hand-built package ([CAI Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md) §2.3):

```
attributes: kafkaHost, kafkaPort, additionalBrokers, otherAttributesCommon, Use SSL, Use SASL
<consumers>
  <consumer name="<eventSource>" typeName="KafkaConsumer" enabled="false|true">
     loadBalance, topic, groupId, contentFormat (TEXT | XML | JSON), simplifyContent,
     otherAttributesProducerConsumer = autoOffsetReset=earliest&consumersCount=3&maxPollRecords=5&autoCommitIntervalMs=1000
  </consumer>
</consumers>
<producers>
  <producer name="<eventTarget>" typeName="KafkaProducer">
     topic, groupId, contentFormat,
     otherAttributesProducerConsumer = requestRequiredAcks=all&enableIdempotence=true&retries=10&maxInFlightRequest=5
  </producer>
</producers>
<javaConnector xmlns="http://schemas.informatica.com/appmodules/screenflow/2014/04/avosConnectors.xsd"
               plugin="Camel" type="KAFKA" uuid="c5d3f9bc-95ba-48e6-99df-5bca133b44b3" name="KAFKA" agentOnly="true"/>
```

AMQP 1.0: `type="AMQP"`, `uuid="59b13626-0180-4d48-a749-38f8f33f7b18"`; attributes `User Name`, `Password`, `Virtual Host`,
`Host`, `Port`, `Use SSL`, `Query Parameters`; consumer `typeName="AMQP Source"` with `Destination Type` (queue), `Destination`,
`Payload Format` (Xml, Json, Text, Binary), `Objectlist Field Name`, `Dead Letter Queue Name`, `Custom Message ID`,
`Enable Load Balancing`, `Other Attributes`. The connector uses the agent's bundled Qpid JMS client: SASL PLAIN worked with no
extra jars and no agent restart.

- **Other Attributes** take Camel endpoint option names joined with `&` (the list above). Read the ProducerConfig and
  ConsumerConfig dumps in the agent's catalina log to see what the route really got.
- **Secrets:** author the password `encrypted="true"` with an empty value and set it after the import with
  `asset/v1/update` (L-CAI-132); a value authored `encrypted="false"` is stored and exported in plaintext (L-CAI-060).
- **One connection per independently controlled subscriber:** republishing a connection restarts all of its event sources
  (L-CAI-119).
- Kafka was proven over PLAINTEXT; Kafka SSL and SASL are untested.

## 3. The listener process (L-CAI-118, L-CAI-137)

```
<deployment><targetLocation><agent name></targetLocation><event eventSource="<conn>:<eventSource>"/></deployment>
input: <parameter name="event" type="reference">  options referenceTo=<conn>:KafkaMessage, required, isCopy, guid=<connection GUID>
```

- A Kafka event carries `body` (a string for TEXT), `headers` as `<headers><name/><value/></headers>` elements, `topic` and
  `partitionId`. `messageKey` is empty on consume: carry the business key and the message id as headers, and read one with
  `string(($input.event/headers[name = '<header>']/value)[1])`.
- Keep the listener thin: capture the body and headers, record a tracking event with `util:getProcessId()` (L-CAI-131), and call
  the handler subprocess inside an eventContainer (catch). On a fault, send the message to an error queue and a dead-letter
  topic yourself, then end normally (L-CAI-137, L-CAI-129).
- Handlers have no access configuration, so they are not APIs (L-CAI-130); subprocess outputs need an explicit output mapping
  (L-CAI-137).
- REST targets: `failOnError="false"` returns the status as data so the process can retry 5xx and reject 4xx (L-CAI-129);
  `requestTimeout` is in seconds (L-CAI-128).

## 4. Starting, stopping and catching up

| Step | How | Lesson |
|---|---|---|
| First start | publish the connection with `enabled="false"`, publish the processes, re-import with `enabled="true"` and republish; check 'Starting route' and 'Subscribed to topic(s)' in catalina and the group STABLE with members | L-CAI-119 |
| A subscriber added later | a new consumer group with `autoOffsetReset=earliest` processes everything still retained in the topic | L-CAI-119 |
| Stop or start one event source | `POST .../active-bpel/local/restadmin/eventconnection/stop` or `/start?agentName=<agent>` with `IDS-SESSION-ID`; the route path is `project:/rt.connection/<conn>/$public/<conn>:<eventSource>` | L-CAI-122 |
| Windowed subscriber | stop at the end of its window, start at the beginning; while stopped the group is EMPTY and lag grows | L-CAI-122 |
| Stop one listener of a connection with several consumers | stop its `<conn>:<eventSource>` route; the connection's other event sources keep consuming (one connection can hold one listener per site) | L-CAI-147 |
| After any connection republish | republish the dependent processes last, listeners stopped meanwhile, or they read out-of-date | L-CAI-133 |

```
POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/local/restadmin/eventconnection/stop?agentName=<agent>
IDS-SESSION-ID: <session>
{"eventRoute":["project:/rt.connection/<conn>/$public/<conn>:<eventSource>"]}

POST .../active-bpel/local/restadmin/eventconnection/start?agentName=<agent>
{"routeInfo":[{"eventRoute":"project:/rt.connection/<conn>/$public/<conn>:<eventSource>"}]}
```

`INFA-SESSION-ID` answers HTTP 500 NullPointerException on both calls.

## 5. Delivery semantics

| Behaviour | Measured | Design consequence | Lesson |
|---|---|---|---|
| One process at a time per consumer | 20 s Wait = records 20.5 s apart on one partition; a retry backoff held an unrelated record about 7 s | short processes; hand-offs for holds and approvals; bounded backoff; `consumersCount` up to the partition count | L-CAI-120 |
| A stop resumes from the last auto-commit | 63 of 600 reprocessed with the 5 s default, 10 of 600 with `autoCommitIntervalMs=1000`; 0 lost | idempotent targets (message id + revision); a short commit interval | L-CAI-121 |
| Hand-off headers are lost on retries and replays | an approved message was parked again on an error-queue retry | the process asks the approval or hold store for the current decision | L-CAI-138 |
| JMS property names over AMQP | names with hyphens or dots missing | `Query Parameters` = `jms.validatePropertyNames=false` | L-CAI-123 |

## 6. Producing to Kafka (L-CAI-124, L-CAI-125)

A Service step on `<conn>:<eventTarget>` with the input `event` typed `<conn>:KafkaMessage`; set `messageKey`, `body` and
`headers` in an Assignment. For an idempotent producer set `retries` explicitly (Camel's default is 0): with
`enableIdempotence=true` alone the producer route fails to start while the publish still says SUCCESS, and callers get 'No
consumers available on endpoint: direct://<conn>_<eventTarget>'. For large messages raise `maxRequestSize` from its 1 MB default
to the broker's and topic's `message.max.bytes` (L-CAI-127).

## 7. Measured throughput and size (one Secure Agent, 8 vCPU)

| Load | Result | Lesson |
|---|---|---|
| 40 msg/s for 30 s, one REST call per message | kept up: peak lag 32, end-to-end p50 106 ms, p95 331 ms | L-CAI-126 |
| 3,000 messages at 200 msg/s | queued in Kafka; drained at about 30 msg/s with 3 consumers (101 s) and about 47 msg/s with 6 (66 s); 0 lost, 0 duplicates | L-CAI-126 |
| 2,000-line XML message (423 KB) | delivered 1.3 s after its approval | L-CAI-127 |
| 19,500-line XML message (4.1 MB) | consumed 1.9 s after publish, parsed in 3.7 s, delivered in 5.3 s; via an AMQP-to-Kafka bridge after raising `maxRequestSize`: delivered in 4.9 s | L-CAI-127 |

These numbers prove the pattern and give a per-agent floor. Scale out with partitions, consumers and agents in an agent group,
and size production in a proof of concept.

## 8. Signatures

| You see | It means | Do | Lesson |
|---|---|---|---|
| Publish SUCCESS, but callers get 'No consumers available on endpoint: direct://...' | a producer route failed to start | read catalina for 'Failed to start route'; for idempotence set `retries` | L-CAI-125 |
| HTTP 500 'NullPointerException: Cannot read the array length ...' on eventconnection start or stop | wrong header | send `IDS-SESSION-ID` | L-CAI-122 |
| Hyphenated JMS properties missing from the AMQP event headers | Qpid validates property names | `jms.validatePropertyNames=false` | L-CAI-123 |
| Records processed twice after a stop or republish | the listener resumed from the last auto-commit | idempotent targets; `autoCommitIntervalMs=1000` | L-CAI-121 |
| Processes read 'out-of-date' after a connection republish | dependent processes are flagged, the runtime is fine | republish the processes last | L-CAI-133 |
| A record of one partition waits behind another | a Wait or retry inside a Kafka-started process holds the partition | hand-offs; bounded backoff; more partitions and consumers | L-CAI-120 |

## 9. Overturned beliefs (this area)

| Old belief | Overturned by | Now |
|---|---|---|
| Kafka and JMS event sources, listener processes and fault handling can only be authored in the Process Designer (L-CAI-117) | L-CAI-116 (2026-10-08) | Author them in an import package and publish over REST; control listeners with restadmin |
