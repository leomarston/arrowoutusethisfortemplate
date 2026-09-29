#!/bin/sh
# B1 capture: shot.sh <name> [launch args...] -> build/b1/shots/<name>.png (sRGB) + <name>.json (lab-ready.json)
# Launches BoardLab on slot A, waits for Documents/lab-ready.json (<= 40 s), screenshots, converts to sRGB.
set -e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
UDID=FFE58FD1-0DC6-4010-895D-AA12D0327736
NAME="$1"; shift
OUT="$ROOT/build/b1/shots"; mkdir -p "$OUT"
DATA=$(xcrun simctl get_app_container $UDID com.manycode.matchfactory data 2>/dev/null || true)
[ -n "$DATA" ] && rm -f "$DATA/Documents/snapshot.png" "$DATA/Documents/lab-ready.json" "$DATA/Documents/lab-perf.json" "$DATA/Documents/lab-r5.json" "$DATA/Documents/r1-scene.json"
"$ROOT/tools/run.sh" A -mf.go boardlab "$@" >/dev/null
DATA=$(xcrun simctl get_app_container $UDID com.manycode.matchfactory data)
i=0
while [ ! -f "$DATA/Documents/lab-ready.json" ]; do
  i=$((i+1)); [ $i -gt 200 ] && { echo "shot.sh: no lab-ready.json after 40 s" >&2; tail -20 "$ROOT/build/run-A.log" >&2; exit 1; }
  sleep 0.2
done
sleep ${SHOT_DELAY:-0.3}
xcrun simctl io $UDID screenshot --type=png --mask=ignored "$OUT/$NAME.raw.png" >/dev/null 2>&1
sips -m "/System/Library/ColorSync/Profiles/sRGB Profile.icc" "$OUT/$NAME.raw.png" --out "$OUT/$NAME.png" >/dev/null
rm -f "$OUT/$NAME.raw.png"
cp "$DATA/Documents/lab-ready.json" "$OUT/$NAME.json"
for f in lab-perf.json lab-r5.json r1-scene.json snapshot.png; do [ -f "$DATA/Documents/$f" ] && cp "$DATA/Documents/$f" "$OUT/$NAME.$f"; done
cat "$ROOT/build/run-A.log" > "$OUT/$NAME.log" 2>/dev/null || true
echo "$OUT/$NAME.png"
