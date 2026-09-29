#!/bin/sh
# tools/core.sh [swift test args]: builds and tests Packages/PathCore on macOS, no simulator (GAMEPROMPT §8.1 "Core").
# -j 2 keeps it light next to the art and audio lanes (GAMEPROMPT §3.4). Adapted from apps/matchfactory/tools/core.sh
# (05424db): MFCore -> PathCore; see design/REUSE.md.
# WP0 amendment (SPEC-architecture §2.4, §2.5 item 3): before building, every `import` in Sources/PathCore must be
# Foundation or CoreGraphics (D1). UIKit, SwiftUI, QuartzCore, AVFoundation (or anything else) there fails the run.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/Packages/PathCore"
[ -f "$PKG/Package.swift" ] || { echo "core.sh: $PKG/Package.swift missing (WP0 creates the package)" >&2; exit 1; }
cd "$PKG"
BAD=$(grep -rnE '^[[:space:]]*(@_?[A-Za-z]+[[:space:]]+)*import[[:space:]]+' Sources/PathCore --include='*.swift' \
      | grep -vE 'import[[:space:]]+(Foundation|CoreGraphics)([[:space:]]*(//.*)?)?$' || true)
if [ -n "$BAD" ]; then
  echo "core.sh: PathCore may import only Foundation and CoreGraphics (SPEC-architecture §2.4, D1):" >&2
  echo "$BAD" >&2
  exit 1
fi
echo "core.sh: import check ok (Sources/PathCore: Foundation + CoreGraphics only)"
swift build -j 2
swift test -j 2 "$@"
