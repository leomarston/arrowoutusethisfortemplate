#!/bin/sh
# tools/gen.sh: regenerates ArrowOut.xcodeproj from project.yml under a mutex (build/.gen.lock), so two agents never
# write the project at once (GAMEPROMPT §3.3: concurrent xcodegen runs corrupt the project). Every agent that ADDS,
# REMOVES or RENAMES a file (a new .metal file included) runs it. Adapted from apps/matchfactory/tools/gen.sh
# (05424db); see design/REUSE.md.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/build/.gen.lock"
XCODEGEN="${XCODEGEN:-$(command -v xcodegen || echo "$HOME/.local/bin/xcodegen")}"
[ -x "$XCODEGEN" ] || { echo "gen.sh: xcodegen not found (looked for \$XCODEGEN, PATH, ~/.local/bin)" >&2; exit 1; }
[ -f "$ROOT/project.yml" ] || { echo "gen.sh: $ROOT/project.yml missing (WP0 writes it)" >&2; exit 1; }
mkdir -p "$ROOT/build"
i=0
until mkdir "$LOCK" 2>/dev/null; do
  i=$((i + 1))
  if [ "$i" -ge 60 ]; then
    echo "gen.sh: $LOCK held for 60 s; if no xcodegen is running (pgrep -fl xcodegen), rmdir it and retry" >&2
    exit 1
  fi
  sleep 1
done
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM
cd "$ROOT"
"$XCODEGEN" generate --quiet --spec project.yml
echo "gen.sh: ArrowOut.xcodeproj generated"
