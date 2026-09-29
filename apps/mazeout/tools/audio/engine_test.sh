#!/bin/bash
# AUDIO (A2): offline tests of the App/Audio engine on macOS, with no simulator and no xcodebuild (SPEC-architecture §12.2 A2).
# The platform-neutral part of App/Audio (AudioCore, AudioGraph, AudioTicker in AudioEngine.swift; SoundBank; MusicPlayer;
# AudioCues) runs under AVAudioEngine's manual (offline) rendering against the real App/Resources/Sounds and Tuning/audio.json.
# The iOS-only parts (the AudioEngine contract wrapper, Haptics) are covered by tools/audio/typecheck_ios.sh.
# Output: build/a2/engine-test.log, build/a2/cue-latency.json. Exit 0 = every check passed.
# Adapted from apps/matchfactory tools/audio/engine_test.sh (05424db).
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/build/a2/enginetest"
mkdir -p "$OUT"
# The contract's enums only (AudioPlaying / HapticPlaying need PathCore + the app): AudioBus, SoundID, MusicID, Haptic.
{ echo "import Foundation"
  awk '/^enum AudioBus/{p=1} /^@MainActor protocol AudioPlaying/{p=0} p' "$ROOT/App/Contracts/AudioContract.swift"
  grep -E '^enum Haptic' "$ROOT/App/Contracts/AudioContract.swift"; } > "$OUT/ContractSubset.swift"
xcrun swiftc -O -swift-version 5 -strict-concurrency=minimal -target arm64-apple-macos15 -module-name AudioEngineTest \
  -o "$OUT/audiotest" "$ROOT/tools/audio/enginetest/main.swift" "$OUT/ContractSubset.swift" "$ROOT/App/Support/Log.swift" \
  "$ROOT/App/Audio/AudioCues.swift" "$ROOT/App/Audio/SoundBank.swift" "$ROOT/App/Audio/MusicPlayer.swift" \
  "$ROOT/App/Audio/AudioEngine.swift" "$ROOT/App/Audio/Haptics.swift" 2>&1 | tee "$OUT/compile.log"
set +e
"$OUT/audiotest" "$ROOT" > "$ROOT/build/a2/engine-test.log" 2>&1
STATUS=$?
set -e
grep -E '^(PASS|FAIL)|passed$|^worst' "$ROOT/build/a2/engine-test.log"
exit $STATUS
