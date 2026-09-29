#!/bin/sh
# tools/bench.sh <A|B> <lab|launch|level|soak> [options] [-- extra launch args]      (GAMEPROMPT §8.3, V3)
# tools/bench.sh report <soak dir> | heapdiff <before> <after>
# Host-side performance bench: footprint of the simulator app process, the app's own log marks, and the in-app debug
# HUD read back from screenshots with Vision OCR (tools/bench/hudocr.swift). Output: build/bench/ (gitignored).
# Performance on this loaded Mac needs an idle baseline; the verdict is taken on the phone (D1).
# See tools/bench/bench.py for the subcommands. Adapted from apps/matchfactory/tools/bench.sh (05424db).
exec python3 "$(dirname "$0")/bench/bench.py" "$@"
