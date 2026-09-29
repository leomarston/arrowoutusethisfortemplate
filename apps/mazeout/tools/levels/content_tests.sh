#!/bin/sh
# tools/levels/content_tests.sh [OUT]  — CONTENT's content tests in one run (L1 + L2). No simulator.
# Every step must pass; the logs land in OUT (default build/l2/tests). SPEC.md §6: the caller checks
# `sysctl vm.swapusage` first; swift builds run with -j 2 (lvtool into build/l1/lvtool, pclevels into build/l2/pc).
#   1  lvtool bundle --check   App/Resources/Levels = design/levels.json byte for byte (150 levels, sessions, unlocks,
#                              tutorials, curve.json) and LevelLibrary reads the bundled curve; --publish (PUBLISH B0,
#                              ruling 39 OD8): the shipped form, every capture / "_" note stripped
#   2  lvtool check            the SPEC-gameplay §14.4 list on L1-L150 with C2's rules + the shipped rules.json
#   3  pclevels validate       C4's validator with the art catalogue (--sprites art/ui/out) + pclevels bot
#   4  lvtool consistency      unlock cards / tutorial / session / tags / timers / strings / art of L1-L150 vs the specs
#   5  lvtool endless          1000 served endless levels: solvable, curve-fitted, no repeats, renderable, deterministic
#   6  endless_py.py           the Python validator's independent verdict on the same 1000 levels
#   7  lvtool l2selftest       negative controls of 4 and 5 (every mutation CAUGHT)
#   8  strings                 build.py --check, coverage.py --strict-code, tr_review.py (TR review + fit)
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
OUT="${1:-build/l2/tests}"
mkdir -p "$OUT"
fail=0
step() {                       # step <name> <command…>
  name="$1"; shift
  if "$@" >"$OUT/$name.txt" 2>&1; then echo "PASS $name"; else echo "FAIL $name (see $OUT/$name.txt)"; fail=1; fi
}
swift build -j 2 -c release --package-path tools/levels/lvtool --scratch-path build/l1/lvtool >"$OUT/build-lvtool.txt" 2>&1 || { echo "FAIL build lvtool"; exit 1; }
swift build -j 2 -c release --package-path Packages/PathCore --scratch-path build/l2/pc --product pclevels >"$OUT/build-pclevels.txt" 2>&1 || { echo "FAIL build pclevels"; exit 1; }
LV=build/l1/lvtool/release/lvtool
PC=build/l2/pc/release/pclevels
step 1-bundle "$LV" bundle design/levels.json App/Resources/Levels --publish --check
step 1-bundle-python python3 -B tools/levels/bundle_check.py design/levels.json App/Resources/Levels --publish
step 2-check "$LV" check App/Resources/Levels --publish --report "$OUT/2-check.json"
step 3-validate "$PC" validate App/Resources/Levels --publish --sprites art/ui/out
step 3-bot "$PC" bot App/Resources/Levels
step 4-consistency "$LV" consistency --report "$OUT/4-consistency.json"
step 5-endless "$LV" endless --from 151 --count "${ENDLESS_COUNT:-1000}" --jobs 3 --report "$OUT/5-endless.json" --out "$OUT/5-endless-levels.jsonl"
step 6-endless-python python3 -B tools/levels/endless_py.py "$OUT/5-endless-levels.jsonl" --jobs 3
step 7-l2selftest "$LV" l2selftest
step 8-strings-build python3 -B tools/strings/build.py --check
step 8-strings-coverage python3 -B tools/strings/coverage.py --strict-code
step 8-strings-tr-review python3 -B tools/strings/tr_review.py
[ "$fail" = 0 ] && echo "content tests: all passed" || echo "content tests: FAILED"
exit "$fail"
