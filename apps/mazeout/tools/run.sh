#!/bin/sh
# tools/run.sh <A|B> [launch args...]: boot (if needed) -> terminate -> install -> launch. Always terminates first and
# launches with --terminate-running-process: simctl launch silently DROPS the arguments when the app is already running
# (GAMEPROMPT §3.3). Launch args use the -pc. prefix (`-pc.level 32 -pc.go level`).
# Console output (stdout + stderr, every `[PC]` log line) goes to the simulator's own data/tmp/pc-run-<slot>.log and is
# linked from build/run-<slot>.log. It must NOT be written under ~/Downloads directly: the host sandbox denies
# xpcproxy_sim access there, and every launch then fails with "The request was denied by service delegate
# (SBMainWorkspace)". Adapted from apps/matchfactory/tools/run.sh (05424db); see design/REUSE.md.
set -e
. "$(dirname "$0")/slot.sh"
shift
[ -d "$APP" ] || { echo "run.sh: $APP missing; run tools/build.sh $SLOT first" >&2; exit 1; }
sim_boot
xcrun simctl terminate "$UDID" "$BUNDLE_ID" 2>/dev/null || true
xcrun simctl install "$UDID" "$APP"
mkdir -p "$(dirname "$SIMLOG")" "$ROOT/build"
: > "$SIMLOG"
LOG="$ROOT/build/run-$SLOT.log"
ln -sfn "$SIMLOG" "$LOG"
xcrun simctl launch --terminate-running-process --stdout="$SIMLOG" --stderr="$SIMLOG" "$UDID" "$BUNDLE_ID" "$@"
echo "run.sh: launched on $SIM_NAME; log $LOG -> $SIMLOG"
