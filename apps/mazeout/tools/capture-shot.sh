#!/bin/sh
# tools/capture-shot.sh <A|B> <name> [launch args...]: one capture that waits for a READY FILE, never a fixed sleep
# (GAMEPROMPT §8.3 "Captures wait for a ready file"):
#   1. remove Documents/<READY> in the app container, launch through tools/run.sh with CAPTURE_ARGS + the given args;
#   2. wait until the app writes Documents/<READY> (<= TIMEOUT s), then SHOT_DELAY s for entrances to finish;
#   3. `simctl io <udid> screenshot --type=png --mask=ignored`, converted to sRGB with sips;
#   4. reject a frame whose most common colour covers more than FLAT_MAX of the screen below the 52 pt status band
#      (a blank launch/placeholder frame; memory screenshots-verify-content-not-count). Every frame must still be LOOKED at.
# Output: $OUT/<name>.png (sRGB) + <name>.json (the ready file) + <name>.log (the [PC] console log).
# Environment (defaults):
#   OUT=build/shots  READY=capture-ready.json (a lab: lab-ready.json)  TIMEOUT=40  SHOT_DELAY=0.6
#   CAPTURE_ARGS="-pc.capture 1"  FLAT_MAX=0.97
# FLAT_MAX is 0.97, not the 0.88 of GAMEPROMPT §8.3: a white Maze Out board late in a level (5 arrows left) is ~92 %
# white by arithmetic (design/REUSE.md), so 0.88 would reject real frames; a blank frame is ~100 % one tone.
# Generalised from tools/gameprompt/snippets/capture-shot.sh (05424db, MF BoardLab on slot A); see design/REUSE.md.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/slot.sh"
NAME="$2"
[ -n "$NAME" ] || { echo "usage: capture-shot.sh <A|B> <name> [launch args...]" >&2; exit 64; }
shift 2
OUT="${OUT:-$ROOT/build/shots}"
READY="${READY:-capture-ready.json}"
TIMEOUT="${TIMEOUT:-40}"
CAPTURE_ARGS="${CAPTURE_ARGS--pc.capture 1}"
mkdir -p "$OUT"
DATA=$(xcrun simctl get_app_container "$UDID" "$BUNDLE_ID" data 2>/dev/null || true)
[ -n "$DATA" ] && rm -f "$DATA/Documents/$READY"
# shellcheck disable=SC2086  # CAPTURE_ARGS is a word list on purpose
"$ROOT/tools/run.sh" "$SLOT" $CAPTURE_ARGS "$@" >/dev/null
DATA=$(xcrun simctl get_app_container "$UDID" "$BUNDLE_ID" data)
i=0
limit=$((TIMEOUT * 5))
while [ ! -f "$DATA/Documents/$READY" ]; do
  i=$((i + 1))
  if [ "$i" -gt "$limit" ]; then
    echo "capture-shot.sh: no Documents/$READY after $TIMEOUT s; log tail:" >&2
    tail -20 "$SIMLOG" >&2 || true
    xcrun simctl io "$UDID" screenshot --type=png --mask=ignored "$OUT/$NAME-timeout.png" >/dev/null 2>&1 || true
    exit 1
  fi
  sleep 0.2
done
sleep "${SHOT_DELAY:-0.6}"
xcrun simctl io "$UDID" screenshot --type=png --mask=ignored "$OUT/$NAME.raw.png" >/dev/null 2>&1
sips -m "/System/Library/ColorSync/Profiles/sRGB Profile.icc" "$OUT/$NAME.raw.png" --out "$OUT/$NAME.png" >/dev/null
rm -f "$OUT/$NAME.raw.png"
cp "$DATA/Documents/$READY" "$OUT/$NAME.json"
cp "$SIMLOG" "$OUT/$NAME.log" 2>/dev/null || true
python3 "$HERE/flat_check.py" "$OUT/$NAME.png" "${FLAT_MAX:-0.97}"
echo "$OUT/$NAME.png"
