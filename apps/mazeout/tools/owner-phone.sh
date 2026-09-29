#!/bin/sh
# (Committed copy of build/owner-phone.sh, 2026-09-30, so it survives in git and the template repo; paths are absolute, run from anywhere.)
# Owner's phone build: snapshot the tree (other owners are mid-edit), build for the iPhone 15, install fresh.
# F3-A (SPEC.md ruling 52(a), 2026-09-29): the build is the MEASURE configuration by default = Release's settings (-O, whole
# module, the same bundle) + the Swift condition PC_MEASURE, which compiles in the measurement harness the store build leaves
# out: `-pc.glitchRun <plan>` (App/Shell/GlitchRun.swift), `-pc.frameWatch 1` (App/FX/FrameWatch.swift), `-pc.tabLoop N`.
# That is the PH-2 / PH-3 (D1b) phone test build:   build/owner-phone.sh            -> dd/Build/Products/Measure-iphoneos
# A store-identical build (no harness; what TestFlight / App Store get):   PHONE_CONFIG=Release (or CONFIG=Release) build/owner-phone.sh
#                                                                          -> dd/Build/Products/Release-iphoneos
# Install the app the last line prints (APP=...); the two configurations land in different product folders.
# RFIX 2026-09-29 (VERIFY F6): tools/slot.sh EXPORTS CONFIG=Debug, so a shell that sourced it silently built a DEBUG app for
# the phone. Now PHONE_CONFIG wins; an inherited CONFIG=Release / Measure is still honoured (the documented
# `CONFIG=Release build/owner-phone.sh` keeps working), but an inherited CONFIG=Debug is IGNORED (said out loud) — Debug only
# by name: PHONE_CONFIG=Debug.
# RFIX 2026-09-29 (VERIFY F1): the snapshot's tools/meta_token.py finds the FACTORY .env (PC_FACTORY_ENV below, and its own
# walk-up to the folder holding .env + apps/), so a Release / Measure phone build carries the Meta client token; the token is
# never copied into the snapshot. Only the three ASC key variables are read from the .env (it used to be sourced whole, which
# put every secret in it — the Meta token too — into xcodebuild's environment, where Xcode turns variables into build settings).
set -e
if [ -n "${PHONE_CONFIG:-}" ]; then
  CONFIG="$PHONE_CONFIG"
elif [ "${CONFIG:-}" = "Debug" ]; then
  echo "owner-phone: ignoring the inherited CONFIG=Debug (tools/slot.sh's default export): building Measure; PHONE_CONFIG=Debug for a Debug phone build"
  CONFIG=Measure
else
  CONFIG="${CONFIG:-Measure}"
fi
case "$CONFIG" in Measure|Release|Debug) ;; *) echo "owner-phone: PHONE_CONFIG must be Measure, Release or Debug (got $CONFIG)"; exit 2;; esac
M=/Users/yago/Downloads/app-factory/apps/mazeout; O=$M/build/owner-phone; T=$O/tree
mkdir -p $T/art/ui $T/Packages
rsync -a --delete $M/App/ $T/App/
cp $M/project.yml $T/
rsync -a --delete --exclude __pycache__ $M/tools/ $T/tools/
rsync -a --delete $M/art/out/ $T/art/out/
cp $M/art/MANIFEST.json $T/art/MANIFEST.json   # the art sync reads it (never-ships rule, FIX2-B)
rsync -a --delete $M/art/ui/out/ $T/art/ui/out/
rsync -a --delete $M/art/ui/code/ $T/art/ui/code/
rsync -a --delete --exclude .build --exclude .swiftpm $M/Packages/PathCore/ $T/Packages/PathCore/
for d in Tests UITests; do ln -sfn "$M/$d" "$T/$d"; done
XG=$(command -v xcodegen || echo $HOME/.local/bin/xcodegen)
(cd $T && $XG generate --quiet --spec project.yml)
echo "snapshot $(date '+%H:%M:%S') on $(git -C $M log -1 --format=%h build/mazeout)" > $O/snapshot.txt
cd /Users/yago/Downloads/app-factory
envval() { /usr/bin/python3 - "$1" <<'PY'
import re, sys
key = sys.argv[1]
val = ""
for line in open(".env", encoding="utf-8"):
    s = line.strip()
    if s.startswith("export "):
        s = s[7:].lstrip()
    if s.startswith(key + "="):
        v = re.sub(r"\s+#.*$", "", s[len(key) + 1:]).strip()     # a trailing comment, as the shell drops it
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        val = v
print(val)
PY
}
ASC_KEY_PATH="$(envval ASC_KEY_PATH)"; ASC_KEY_ID="$(envval ASC_KEY_ID)"; ASC_ISSUER_ID="$(envval ASC_ISSUER_ID)"
export PC_FACTORY_ENV="$PWD/.env"
/usr/bin/python3 $T/tools/meta_token.py status || true      # present / absent / malformed, never the value
KP="$ASC_KEY_PATH"; case "$KP" in /*) ;; *) KP="$PWD/$KP";; esac
xcodebuild -project $T/ArrowOut.xcodeproj -scheme ArrowOut -configuration "$CONFIG" \
  -destination id=00008120-000964E426440032 -derivedDataPath $O/dd -jobs 4 -quiet \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
  -authenticationKeyPath "$KP" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID" build
echo "BUILD_EXIT=$?"
echo "APP=$O/dd/Build/Products/$CONFIG-iphoneos/ArrowOut.app ($CONFIG)"
