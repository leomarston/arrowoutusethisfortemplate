#!/bin/sh
# PLAY_UDID=<udid> tools/play-watch.sh [A|B]: keeps the latest build of slot A or B (default B) running on a separate
# "Play" simulator for the owner. Installs the first good build at once and later builds at most every 8 minutes, so
# play is not interrupted constantly; a build is taken only after its binary has been quiet for 25 s and passes
# `codesign -v`, and it is staged in build/play-stage first (a later build never swaps files under the running app).
# PLAY_UDID is required and must be a simulator the orchestrator created for this purpose (it is neither slot's UDID:
# never share a simulator between agents). Loops forever: start it with run_in_background and stop it at the end.
# Generalised from tools/gameprompt/snippets/play-watch.sh (05424db; the Arrows copy with its UDID, paths and a stale
# scratchpad hard-coded); see design/REUSE.md.
[ -n "$PLAY_UDID" ] || { echo "play-watch.sh: set PLAY_UDID to the Play simulator's UDID" >&2; exit 64; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-B}"
case "$SRC" in A|B) ;; *) echo "play-watch.sh: slot must be A or B" >&2; exit 64 ;; esac
if grep -q "UDID=$PLAY_UDID;" "$ROOT/tools/slot.sh"; then
  echo "play-watch.sh: PLAY_UDID is a slot simulator (tools/slot.sh); use a separate one" >&2; exit 64
fi
APP="$ROOT/build/dd-$SRC/Build/Products/Debug-iphonesimulator/ArrowOut.app"
BUNDLE_ID=com.manycode.arrowout
STAGE="$ROOT/build/play-stage"
last=""; lastInstall=0
while true; do
  if [ -f "$APP/ArrowOut" ]; then
    m=$(stat -f %m "$APP/ArrowOut"); now=$(date +%s)
    if [ "$m" != "$last" ] && [ $((now - m)) -ge 25 ] && { [ $lastInstall -eq 0 ] || [ $((now - lastInstall)) -ge 480 ]; }; then
      if codesign -v "$APP" 2>/dev/null; then
        rm -rf "$STAGE"; mkdir -p "$STAGE"; cp -R "$APP" "$STAGE/"
        xcrun simctl terminate "$PLAY_UDID" "$BUNDLE_ID" >/dev/null 2>&1
        if xcrun simctl install "$PLAY_UDID" "$STAGE/ArrowOut.app" && xcrun simctl launch "$PLAY_UDID" "$BUNDLE_ID" >/dev/null; then
          last=$m; lastInstall=$now; echo "$(date '+%H:%M:%S') installed + launched the build from $(date -r "$m" '+%H:%M:%S')"
        fi
      fi
    fi
  fi
  sleep 20
done
