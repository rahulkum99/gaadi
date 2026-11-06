#!/bin/sh
# Pull Track360, persist GPS points, and raise alerts every 5 minutes.
# Failures must not stop the loop.

INTERVAL="${LIVE_INGEST_INTERVAL_SECONDS:-300}"

echo "Starting live ingest every ${INTERVAL}s"
while true; do
  python manage.py pull_live_fleet || echo "live ingest failed; retrying in ${INTERVAL}s"
  sleep "${INTERVAL}"
done
