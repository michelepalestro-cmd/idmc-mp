#!/bin/sh
# Creates the demo topics once (idempotent). Runs in the mbr-kafka-init container.
# 3 partitions = 3 lanes read in parallel, one lane always in order; the record key (business id) picks the lane.
set -eu
B="${BOOTSTRAP:-mbr-kafka:29092}"
K=/opt/kafka/bin/kafka-topics.sh
mk() {  # name partitions
  $K --bootstrap-server "$B" --create --if-not-exists --topic "$1" --partitions "$2" --replication-factor 1 \
     --config retention.ms=604800000 --config max.message.bytes=5242880
}
mk mbr.item 3     # item create / modify (key = item number)
mk mbr.po   3     # purchase orders, header + lines in one message (key = PO number)
mk mbr.perf 6     # load test pings (6 partitions = 6 consumers)
mk mbr.dlq  3     # dead-letter copies of every message that went to the error queue
$K --bootstrap-server "$B" --list
