#!/bin/sh
# Every event folder runs the same app; the folder name picks the event's data.
# Edit bandon-2026/index.html, then run this to copy it to the other events.
set -e
cd "$(dirname "$0")/.."
for ev in redtail bandon-crossings; do
  cp bandon-2026/index.html "$ev/index.html"
done
