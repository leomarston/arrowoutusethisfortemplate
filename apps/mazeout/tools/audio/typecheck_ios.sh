#!/bin/bash
# AUDIO (A2): type-checks App/Audio for the iOS simulator together with the LEAD's frozen contracts and support files
# (AudioContract, AppContext/AppModel, LaunchArgs, Log, PlayerStore, Tuning), without xcodebuild or a simulator. It needs an
# iOS-simulator PathCore.swiftmodule from a slot build (build/dd-A or build/dd-B, Debug). Any file of another owner that the
# contracts reference is added from the real tree (read-only). Output: build/a2/typecheck-ios.log.
# Adapted from apps/matchfactory tools/audio/typecheck_ios.sh (05424db).
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MOD=""
for d in "$ROOT/build/dd-A" "$ROOT/build/dd-B"; do
  [ -d "$d/Build/Products/Debug-iphonesimulator/PathCore.swiftmodule" ] && MOD="$d/Build/Products/Debug-iphonesimulator" && break
done
[ -n "$MOD" ] || { echo "typecheck_ios.sh: no iOS-simulator PathCore.swiftmodule under build/dd-A|B; a slot build makes one" >&2; exit 1; }
mkdir -p "$ROOT/build/a2"
SDK="$(xcrun --sdk iphonesimulator --show-sdk-path)"
cd "$ROOT"
FILES=(App/Contracts/*.swift App/Support/*.swift App/Brand.swift App/AppModel.swift App/GameApp.swift App/Audio/*.swift ${EXTRA_FILES:-})
set +e
xcrun swiftc -typecheck -sdk "$SDK" -target arm64-apple-ios18.0-simulator -swift-version 5 -strict-concurrency=minimal \
  -parse-as-library -I "$MOD" "${FILES[@]}" > "$ROOT/build/a2/typecheck-ios.log" 2>&1
STATUS=$?
set -e
W=$(grep -c "warning:" "$ROOT/build/a2/typecheck-ios.log" || true)
E=$(grep -c "error:" "$ROOT/build/a2/typecheck-ios.log" || true)
AW=$(grep "warning:" "$ROOT/build/a2/typecheck-ios.log" | grep -c "App/Audio/" || true)
AE=$(grep "error:" "$ROOT/build/a2/typecheck-ios.log" | grep -c "App/Audio/" || true)
echo "typecheck_ios.sh: exit $STATUS, $E errors ($AE in App/Audio), $W warnings ($AW in App/Audio); PathCore from $MOD; ${#FILES[@]} files" | tee -a "$ROOT/build/a2/typecheck-ios.log"
exit $STATUS
