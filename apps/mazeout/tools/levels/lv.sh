#!/bin/sh
# tools/levels/lv.sh <command> [args]: builds tools/levels/lvtool (SwiftPM, -j 2, release) into build/l1/lvtool and runs
# it from apps/mazeout (every path argument is relative to apps/mazeout). CONTENT (L1). SPEC.md §6: swift build -j 2;
# the caller checks `sysctl vm.swapusage` first. LV_NOBUILD=1 skips the build step.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
SCRATCH="$ROOT/build/l1/lvtool"
if [ -z "$LV_NOBUILD" ]; then
  swift build -j 2 -c release --package-path tools/levels/lvtool --scratch-path "$SCRATCH" >"$ROOT/build/l1/lvtool-build.log" 2>&1 || {
    tail -40 "$ROOT/build/l1/lvtool-build.log" >&2
    echo "lv.sh: build failed (log: build/l1/lvtool-build.log)" >&2
    exit 1
  }
fi
exec "$SCRATCH/release/lvtool" "$@"
