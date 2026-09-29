#!/bin/sh
# Build the RealityKit preview renderer (macOS 15+). Output stays in the gitignored build dir.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../../../build/art"
mkdir -p "$OUT"
# build to a temp file, then rename: a render already running in another lane keeps its (old) inode
xcrun swiftc -O -target arm64-apple-macos15.0 "$HERE/main.swift" -o "$OUT/mfrender.tmp.$$"
mv -f "$OUT/mfrender.tmp.$$" "$OUT/mfrender"
echo "built $OUT/mfrender"
