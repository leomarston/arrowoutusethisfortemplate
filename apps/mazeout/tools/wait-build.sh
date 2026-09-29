#!/bin/sh
# tools/wait-build.sh <role> <A|B> [action] [xcodebuild args...]
# Waits until every other owner's Swift sources have been quiet for QUIET s (default 90) AND free swap is >= 400 MB,
# then builds the scratch copy (tools/iso-build-copy.sh); a failed build is retried after the next quiet window, up to
# 5 attempts. Each wait is capped at 60 x 5 s. The log of the last attempt: build/iso-<role>/build.log.
# The whole run can exceed the 4-minute Bash rule of GAMEPROMPT §3.4: start it with run_in_background, or with an
# explicit Bash timeout. Generalised from tools/gameprompt/snippets/wait-build.sh (05424db); see design/REUSE.md.
ROLE="$1"; SLOTARG="$2"
[ -n "$ROLE" ] && [ -n "$SLOTARG" ] || { echo "usage: wait-build.sh <role> <A|B> [action] [xcodebuild args...]" >&2; exit 64; }
shift 2
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
mkdir -p "build/iso-$ROLE"
LOG="build/iso-$ROLE/build.log"
QUIET="${QUIET:-90}"
for attempt in 1 2 3 4 5; do
  i=0
  while :; do
    now=$(date +%s)
    newest=$(find App Packages/PathCore/Sources -name '*.swift' -exec stat -f %m {} + 2>/dev/null | sort -n | tail -1)
    newest=${newest:-0}
    free=$(sysctl vm.swapusage | sed -E 's/.*free = ([0-9]+)(\.[0-9]+)?M.*/\1/')
    [ $((now - newest)) -ge "$QUIET" ] && [ "${free:-0}" -ge 400 ] && break
    i=$((i + 1)); [ $i -ge 60 ] && break
    sleep 5
  done
  echo "wait-build.sh: attempt $attempt quiet=$((now - newest))s swapfree=${free}M $(date +%H:%M:%S)"
  if "$ROOT/tools/iso-build-copy.sh" "$ROLE" "$SLOTARG" "$@" > "$LOG" 2>&1; then
    echo "wait-build.sh: BUILD OK $(date +%H:%M:%S) (log $LOG)"
    exit 0
  fi
  grep -E "error:" "$LOG" | head -5
done
echo "wait-build.sh: BUILD GAVE UP after 5 attempts (log $LOG)"
exit 1
