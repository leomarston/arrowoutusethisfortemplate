#!/bin/sh
# timer.sh N GAP  -> N shots (scratch) with local time + OCR'd timer text (+ heart count proxy)
P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; R=/Users/yago/Downloads/app-factory/apps/mazeout/research
V=/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad
for i in $(seq 1 $1); do
  T=$(python3 -c 'import time;print("%.2f"%time.time())'); $P shot $V/tm.png >/dev/null 2>&1
  O=$($R/video-tools/vocr --crop 370 245 190 85 --scale 2 $V/tm.png 2>/dev/null | python3 -c 'import sys,json;print(" ".join(json.loads(sys.stdin.readline())["lines"]))' 2>/dev/null)
  echo "$(date -r ${T%.*} +%H:%M:%S).${T#*.} timer=[$O]"
  sleep $2
done
