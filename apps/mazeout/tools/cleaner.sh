#!/bin/sh
# Every 5 min: frees space the factory's own work leaves behind and nothing uses — the two mazeout simulators' dead app
# copies (containermanagerd/Dead, one per reinstall, 65-300 MB each; entries > 10 min old) and closed Instruments temp traces
# (> 30 min old). Logs what it freed to build/cleaner.log. Never touches other simulators or other apps' files.
LOG=/Users/yago/Downloads/app-factory/apps/mazeout/build/cleaner.log
T=/private/var/folders/g6/8bctrt9s4p5dbyd9y3pvh3qh0000gn/T
while true; do
  b=$(df -m / | awk 'NR==2{print $4}')
  for d in 177520B6-4889-46C2-BDD9-155813D2B175 B80EDB24-6280-4C52-A63F-E8AADD245017; do
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
