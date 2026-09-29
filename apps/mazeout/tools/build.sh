#!/bin/sh
# tools/build.sh <A|B> [extra xcodebuild args]: $CONFIG (default Debug) build for that slot's simulator into build/dd-<slot> (each slot
# has its own DerivedData, so two agents never contend for one build database). One xcodebuild per agent, -jobs 4
# -quiet (GAMEPROMPT §3.4). Waits for >= 400 MB free swap first (tools/slot.sh wait_for_memory).
# Adapted from apps/matchfactory/tools/build.sh (05424db); see design/REUSE.md.
set -e
. "$(dirname "$0")/slot.sh"
shift
cd "$ROOT"
[ -d "$PROJECT" ] || "$ROOT/tools/gen.sh"
wait_for_memory build.sh
echo "build.sh: slot $SLOT ($SIM_NAME), $CONFIG, swap free $(swap_free_mb) MB, booted: $(xcrun simctl list devices booted | grep -c Booted)" >&2
xcodebuild -project "$PROJECT" -scheme "$SCHEME" -configuration "$CONFIG" \
  -destination "id=$UDID" -derivedDataPath "$DD" -jobs 4 -quiet "$@" build
echo "build.sh: $APP"
