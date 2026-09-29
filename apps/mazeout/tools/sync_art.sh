#!/bin/sh
# Build phase (postCompile, idempotent; project.yml wires it, SPEC-architecture §2.2):
#   art/ui/out -> <app bundle>/UI    UI rasters <case>@3x.png (SVG route B2 and UI-3D route B3; art/PIPELINE.md)
#   art/out    -> <app bundle>/Art   3D-route renders <case>@3x.png (characters, the home scene, 3D arrows), plus the
#                                    puppets' `<id>_rig/rig.json` and the `char_*.json` placement sidecars (WP0
#                                    amendment, §2.5 item 2: the home puppets need them, §6.4)
# Files starting with "_" are pipeline scratch, never shipped. Only PNGs (and those JSON sidecars) are copied: nothing
# from research/ can reach the bundle through this script (the copying line). A missing folder is skipped, so an early
# build still works.
# Adapted from apps/matchfactory/tools/sync_art.sh (05424db): MF's USDZ items/sidecars/rig are gone (Maze Out's board
# is vector code; no RealityKit); see design/REUSE.md.
# FIX-2 lane B (A4-r2 / A4-r6): what never ships is decided by ONE rule in tools/uiart_gen.py (manifest status 'not-shipped'
# or notes starting 'NOT SHIPPED', plus the ids of tools/art_build_only.txt); `uiart_gen.py --exclude-list ui|art` prints
# those files (+ art/out sidecars, rig folders) as rsync excludes, applied BEFORE the includes. --delete-excluded also drops
# them from a bundle an earlier build filled (plain --delete protects excluded names on the receiver).
set -e
APP="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH"
[ -n "$TARGET_BUILD_DIR" ] || { echo "sync_art.sh: run from an Xcode build phase (TARGET_BUILD_DIR unset)" >&2; exit 1; }
mkdir -p "$APP/UI" "$APP/Art"
EXCL="${TMPDIR:-/tmp}/pc-sync-art.$$"; mkdir -p "$EXCL"; trap 'rm -rf "$EXCL"' EXIT
python3 "$SRCROOT/tools/uiart_gen.py" --exclude-list ui > "$EXCL/ui.txt"
python3 "$SRCROOT/tools/uiart_gen.py" --exclude-list art > "$EXCL/art.txt"
if [ -d "$SRCROOT/art/ui/out" ]; then
  rsync -a --delete --delete-excluded --exclude='_*' --exclude-from="$EXCL/ui.txt" --include='*/' --include='*.png' \
    --exclude='*' "$SRCROOT/art/ui/out/" "$APP/UI/"
fi
if [ -d "$SRCROOT/art/out" ]; then
  rsync -a -m --delete --delete-excluded --exclude='_*' --exclude-from="$EXCL/art.txt" --include='*/' --include='*.png' \
    --include='/*_rig/rig.json' --include='/char_*.json' --exclude='*' "$SRCROOT/art/out/" "$APP/Art/"
fi
# F3-B (2026-09-29): the copied JSON loses its NON-RUNTIME keys here, at sync time: the art pipeline's notes ("note",
# "notes", "baked", "proof", and char_loading_layout.json's "replaces" = the retired figure ids, which name the reference's
# characters), "_" comments and capture-provenance keys (the rule: tools/strip_bundle_json.py). art/out keeps its notes; the
# .app does not. release_gates.sh gate 7 fails a Release bundle that still carries one. (rsync re-copies a stripped file on
# the next build — its size differs from the source — and this line strips it again: idempotent.)
python3 "$SRCROOT/tools/strip_bundle_json.py" strip "$APP/Art" "$APP/UI"
