#!/bin/sh
# tools/test.sh <A|B> [-only-testing:Target/Class ...]: xcodebuild test with the slot's destination and DerivedData.
# UI suites must pass twice in a row (GAMEPROMPT §14); run once more rather than retrying a failure away.
# Adapted from apps/matchfactory/tools/test.sh (05424db); see design/REUSE.md.
set -e
. "$(dirname "$0")/slot.sh"
shift
cd "$ROOT"
[ -d "$PROJECT" ] || "$ROOT/tools/gen.sh"
wait_for_memory test.sh
xcodebuild -project "$PROJECT" -scheme "$SCHEME" -configuration "$CONFIG" \
  -destination "id=$UDID" -derivedDataPath "$DD" -jobs 4 -quiet "$@" test
