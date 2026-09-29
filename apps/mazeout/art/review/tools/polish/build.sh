#!/bin/sh
# Polish lane r3: render the SHELL's popup chrome (App/Shell/Popups/PopupChrome.swift, copied read-only) next to the
# polish proposal (chrome_polish.swift) at 007's ui.json frames -> build/ui-art/polish/pause_{shell,polish}.png.
# Run from apps/mazeout. swiftc only (no xcodebuild), ~15 s.
set -e
P=build/ui-art/polish
mkdir -p $P/swift
sed -n '1,181p;205,289p;363,425p' App/Shell/Popups/PopupChrome.swift > $P/swift/chrome_shell.swift
xcrun swiftc -O -parse-as-library -target arm64-apple-macos15.0 -o $P/chromerender art/ui/code/GlossyChrome.swift \
    art/review/tools/polish/stubs.swift $P/swift/chrome_shell.swift art/review/tools/polish/chrome_polish.swift \
    art/review/tools/polish/main.swift
$P/chromerender $P
