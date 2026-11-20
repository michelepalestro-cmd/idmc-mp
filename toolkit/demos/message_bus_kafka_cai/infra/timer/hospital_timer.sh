#!/bin/sh
# Hospital sweep timer: POST to the agent's anonymous endpoint of mbr_hospital_retry every N seconds.
# Pause it: docker stop mbr-timer. One run at a time (curl waits for the answer; --max-time bounds it).
set -u
URL="${MBR_SWEEP_URL:?}"
EVERY="${MBR_SWEEP_EVERY_S:-60}"
while true; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 120 -X POST -H 'Content-Type: application/json' \
         -d '{"actor":"timer"}' "$URL" || echo 000)
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) sweep HTTP $code"
  sleep "$EVERY"
done
