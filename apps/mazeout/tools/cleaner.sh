#!/bin/sh
# Every 5 min: frees space the factory's own work leaves behind and nothing uses — the two slot simulators' dead app
# copies (containermanagerd/Dead, one per reinstall, 65-300 MB each; entries > 10 min old) and closed Instruments temp traces
# (> 30 min old). Logs what it freed to build/cleaner.log. Never touches other simulators or other apps' files.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MACHINE_FROM="$ROOT" . "$ROOT/../../tools/machine.sh"; machine_require SIM_A_UDID SIM_B_UDID
mkdir -p "$ROOT/build"; LOG="$ROOT/build/cleaner.log"
T="$(getconf DARWIN_USER_TEMP_DIR 2>/dev/null || echo "${TMPDIR:-/tmp}")"   # this user's Instruments temp folder
while true; do
  b=$(df -m / | awk 'NR==2{print $4}')
  for d in "$SIM_A_UDID" "$SIM_B_UDID"; do
    D=$HOME/Library/Developer/CoreSimulator/Devices/$d/data/Library/Caches/com.apple.containermanagerd/Dead
    [ -d "$D" ] && find "$D" -mindepth 1 -maxdepth 1 -mmin +10 -exec rm -rf {} + 2>/dev/null
  done
  for f in "$T"/instruments*.ktrace; do
    [ -e "$f" ] || continue
    lsof "$f" >/dev/null 2>&1 && continue
    find "$f" -mmin +30 -delete 2>/dev/null
  done
  a=$(df -m / | awk 'NR==2{print $4}')
  [ $((a-b)) -gt 50 ] && echo "$(date '+%m-%d %H:%M') freed $((a-b)) MB -> $a MB free" >> "$LOG"
  sleep 300
done
