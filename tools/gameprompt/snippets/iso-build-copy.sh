#!/bin/sh
# G1 scratch copy (build/g1/iso): the real tree's App/ + ONE patch in BOARD's BoardEngine.prepare, so the first launch of a
# fresh install can reach level 1 (the unpatched Router.bootWork -> board.prepare waits forever for the board view's first
# layout; see the G1 report). Everything else is symlinked to the real tree. Usage: build/g1/iso.sh [build|test <args>]
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ISO="$ROOT/build/g1/iso"
DD="$ROOT/build/g1/dd-iso"
UDID=FFE58FD1-0DC6-4010-895D-AA12D0327736
mkdir -p "$ISO"
rsync -a --delete "$ROOT/App/" "$ISO/App/"
for d in Packages art Tests UITests tools; do ln -sfn "$ROOT/$d" "$ISO/$d"; done
cp "$ROOT/project.yml" "$ISO/project.yml"
python3 - "$ISO/App/Board/BoardEngine.swift" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = "        await waitForLayout()\n        await WarmUp.run(self, prototypes: protos)"
new = ("        if !laidOut && arView.window == nil {   // G1 SCRATCH PATCH: never block boot on an off-window view\n"
       "            Log.info(\"board\", \"prepare: view off-window, warm-up deferred to the level (G1 scratch patch)\")\n"
       "            return\n        }\n" + old)
assert old in s, "BoardEngine.prepare changed: update the patch"
open(p, "w").write(s.replace(old, new, 1))
PY
# Other owners' files that are mid-edit and do not compile yet get the smallest fix IN THE COPY ONLY (listed here):
python3 - "$ISO/App" <<'PY'
import sys, os
root = sys.argv[1]
fixes = [("Shell/Meta/DailyBonusView.swift",
          'MFButton(id: "daily.note.\\(index)", clicks: false, enabled: !revealed,',
          'MFButton(id: "daily.note.\\(index)", enabled: !revealed, clicks: false,')]
for rel, old, new in fixes:
    p = os.path.join(root, rel)
    if os.path.exists(p):
        s = open(p).read()
        if old in s:
            open(p, "w").write(s.replace(old, new)); print("iso.sh: copy-only fix in", rel)
PY
cd "$ISO" && xcodegen generate --quiet --spec project.yml
avail=$(df -g / | awk 'NR==2 {print $4}')
if [ "${avail:-0}" -lt 3 ]; then echo "iso.sh: only ${avail} GB free" >&2; exit 1; fi
cmd="${1:-build}"; [ $# -gt 0 ] && shift
xcodebuild -project "$ISO/MatchFactory.xcodeproj" -scheme MatchFactory -configuration Debug -destination "id=$UDID" \
  -derivedDataPath "$DD" -jobs 4 -quiet "$@" "$cmd"
echo "iso.sh: $cmd ok ($DD)"
