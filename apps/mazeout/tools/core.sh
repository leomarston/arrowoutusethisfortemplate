#!/bin/sh
# tools/core.sh [swift test args]: builds and tests Packages/PathCore on macOS, no simulator (GAMEPROMPT §8.1 "Core").
# -j 2 keeps it light next to the art and audio lanes (GAMEPROMPT §3.4). Adapted from apps/matchfactory/tools/core.sh
# (05424db): MFCore -> PathCore; see design/REUSE.md.
# WP0 amendment (SPEC-architecture §2.4, §2.5 item 3): before building, every `import` in the core's sources must be
# Foundation or CoreGraphics (D1) (+ GameCore in ArrowEscape, template phase 1). UIKit, SwiftUI, QuartzCore, AVFoundation
# (or anything else) there fails the run. Template phase 5: SortPuzzle (the second module) may import only Foundation and
# GameCore; `swift test` runs its SortPuzzleTests next to PathCoreTests.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$ROOT/Packages/PathCore"
[ -f "$PKG/Package.swift" ] || { echo "core.sh: $PKG/Package.swift missing (WP0 creates the package)" >&2; exit 1; }
cd "$PKG"
# Template phase 1: the core is three targets. GameCore (genre-agnostic) may import only Foundation and CoreGraphics;
# ArrowEscape (the puzzle) may import those and GameCore; PathCore is the umbrella and only re-exports the two.
IMPORT_RE='^[[:space:]]*(@_?[A-Za-z]+[[:space:]]+)*import[[:space:]]+'
for d in Sources/GameCore Sources/ArrowEscape Sources/PathCore Sources/SortPuzzle; do
  [ -d "$d" ] || { echo "core.sh: $PKG/$d missing" >&2; exit 1; }
done
check_imports() {  # <dir> <allowed module alternation>
  grep -rnE "$IMPORT_RE" "$1" --include='*.swift' \
    | grep -vE "import[[:space:]]+($2)([[:space:]]*(//.*)?)?\$" || true
}
BAD="$(check_imports Sources/GameCore 'Foundation|CoreGraphics'; check_imports Sources/ArrowEscape 'Foundation|CoreGraphics|GameCore'; check_imports Sources/PathCore 'GameCore|ArrowEscape'; check_imports Sources/SortPuzzle 'Foundation|GameCore')"
if [ -n "$BAD" ]; then
  echo "core.sh: GameCore may import only Foundation and CoreGraphics, ArrowEscape also GameCore, PathCore only the two, SortPuzzle only Foundation and GameCore (SPEC-architecture §2.4, D1):" >&2
  echo "$BAD" >&2
  exit 1
fi
# ArrowEscape -> GameCore only: GameCore must never import the puzzle (checked above: its allow-list has no ArrowEscape).
echo "core.sh: import check ok (GameCore: Foundation + CoreGraphics; ArrowEscape: + GameCore; PathCore: umbrella; SortPuzzle: Foundation + GameCore)"
swift build -j 2
swift test -j 2 "$@"
