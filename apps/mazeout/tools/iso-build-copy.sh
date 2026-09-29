#!/bin/sh
# tools/iso-build-copy.sh <role> <A|B> [build|test|build-for-testing|test-without-building] [xcodebuild args...]
# Builds a SCRATCH COPY of the app while other owners are mid-edit in the shared tree (GAMEPROMPT §8.2 rule 3):
#   build/iso-<role>/tree   App/ rsynced from the real tree (a snapshot), project.yml copied; Packages, art, design,
#                           Tests, UITests and tools symlinked to the real tree;
#   build/iso-<role>/dd     its own DerivedData (never the slot's build/dd-<slot>).
# Copy-only fixes for someone else's half-written file go in build/iso-<role>/patch.py (optional): it is run with the
# copy's App/ directory as its argument after every rsync, must print what it changed, and must assert that its target
# text still exists. Never patch the real tree to get your build green: append `file:line error — owner` to
# build/blocked.md instead (GAMEPROMPT §8.2 rule 4).
# Generalised from tools/gameprompt/snippets/iso-build-copy.sh (05424db; MF G1's copy with its BoardEngine patch baked
# in); see design/REUSE.md.
set -e
ROLE="$1"
[ -n "$ROLE" ] || { echo "usage: iso-build-copy.sh <role> <A|B> [action] [xcodebuild args...]" >&2; exit 64; }
shift
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/slot.sh"
shift
ACTION="${1:-build}"
[ $# -gt 0 ] && shift
BASE="$ROOT/build/iso-$ROLE"
ISO="$BASE/tree"
ISODD="$BASE/dd"
XCODEGEN="${XCODEGEN:-$(command -v xcodegen || echo "$HOME/.local/bin/xcodegen")}"
mkdir -p "$ISO"
rsync -a --delete "$ROOT/App/" "$ISO/App/"
for d in Packages art design Tests UITests tools; do
  if [ -e "$ROOT/$d" ]; then ln -sfn "$ROOT/$d" "$ISO/$d"; fi
done
cp "$ROOT/project.yml" "$ISO/project.yml"
if [ -f "$BASE/patch.py" ]; then python3 "$BASE/patch.py" "$ISO/App"; fi
(cd "$ISO" && "$XCODEGEN" generate --quiet --spec project.yml)
wait_for_memory iso-build-copy.sh
xcodebuild -project "$ISO/ArrowOut.xcodeproj" -scheme "$SCHEME" -configuration "$CONFIG" -destination "id=$UDID" \
  -derivedDataPath "$ISODD" -jobs 4 -quiet "$@" "$ACTION"
echo "iso-build-copy.sh: $ACTION ok ($ISODD)"
