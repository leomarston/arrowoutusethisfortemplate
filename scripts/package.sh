#!/bin/bash
# Portable bundle: zips the whole project INCLUDING secrets (.env + keys/) and
# the .git history, so it works on any Mac after unzip — no reconfiguring.
#
# ⚠️  The zip contains live credentials (App Store Connect .p8, Distribution
#     signing key, RevenueCat secret). KEEP IT PRIVATE — AirDrop/USB/private cloud
#     only, never a public upload.
#
# How it works: it rsyncs the repo into a temp staging dir while PRUNING the
# heavy, regenerable build caches (build/, DerivedData/, *.xcodeproj/, SwiftPM
# checkouts). rsync never descends into an excluded dir, so this stays fast even
# though the untouched repo can carry multiple GB of Xcode caches. Everything
# needed to *rebuild* (source, fastlane, metadata, keys, .env, PROJECT_LOG.md,
# .claude skill, .git) travels; anything Xcode regenerates does not.
#
# Usage:  bash scripts/package.sh  [output.zip]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$(basename "$ROOT")"
PARENT="$(dirname "$ROOT")"
OUT="${1:-$PARENT/${NAME}-portable.zip}"
# zip runs inside the staging dir (deleted on exit), so a relative OUT must be made absolute first,
# or the zip is written into the temp dir and silently lost.
case "$OUT" in /*) ;; *) OUT="$(pwd)/$OUT" ;; esac
echo "⚠️  $OUT will contain live secrets (.env, keys/). Keep it private."

# Filter rules (rsync applies them in order, first match wins).
# NOTE: '.git/***' MUST come first — branch refs live at paths like
# .git/refs/heads/build/reco, and the bare 'build/' exclude below would
# otherwise prune that directory and corrupt the repo (no commits on the
# current branch after unzip). Protecting .git wholesale keeps every branch.
EXCLUDES=(
  --include '.git/***'                # protect git internals + all branch refs
  --exclude 'build/'
  --exclude 'DerivedData/'
  --exclude '*.xcodeproj/'
  --exclude '.build/'                 # SwiftPM
  --exclude 'SourcePackages/'         # resolved SPM checkouts
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.DS_Store'
)

STAGE_ROOT="$(mktemp -d)"
STAGE="$STAGE_ROOT/$NAME"
trap 'rm -rf "$STAGE_ROOT"' EXIT
mkdir -p "$STAGE"

echo "Staging a clean copy (pruning build caches)…"
rsync -a "${EXCLUDES[@]}" "$ROOT/" "$STAGE/"

rm -f "$OUT"
( cd "$STAGE_ROOT" && zip -r -q -X "$OUT" "$NAME" )

echo "Wrote: $OUT  ($(du -h "$OUT" | cut -f1))"
echo "Includes .env + keys/ + .git (live credentials) — keep this file PRIVATE."
