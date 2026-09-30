#!/bin/sh
# Kills runaway work of THIS project only, by memory FOOTPRINT (top's MEM = resident + compressed; RSS alone misses a process
# whose pages were compressed/swapped — 22:44 a LOOK render sat at 8.6 GB footprint with a small RSS and filled the disk):
# python of apps/mazeout or the session scratchpad > 3 GB, xctest of our targets > 6 GB. Logs any other process > 5 GB.
APP="$(cd "$(dirname "$0")/.." && pwd)"          # this app folder, wherever the repo is checked out
mkdir -p "$APP/build"; LOG="$APP/build/memguard.log"
mb() { case "$1" in *G) echo "${1%G}" | awk '{printf "%d", $1*1024}';; *M) echo "${1%M}" | awk '{printf "%d", $1}';; *K) echo 0;; *) echo 0;; esac; }
while true; do
  top -l 1 -o mem -n 25 -stats pid,mem 2>/dev/null | awk 'NR>12 && $1 ~ /^[0-9]+$/ {print $1, $2}' | while read pid mem; do
    m=$(mb "$mem"); [ "$m" -gt 3072 ] || continue
    cmd=$(ps -p "$pid" -o command= 2>/dev/null)
    exe=$(ps -p "$pid" -o comm= 2>/dev/null)     # the EXECUTABLE decides the rule (09-29 13:48: an xctest whose arguments
    case "$exe" in                              # contained 'python' was killed under the python rule at 4.5 GB)
      *xctest)
        case "$cmd" in *PathCoreTests*|*ArrowOut*)
          [ "$m" -gt 6144 ] && kill "$pid" 2>/dev/null && echo "$(date '+%m-%d %H:%M:%S') killed xctest pid $pid footprint ${m} MB" >> "$LOG" ;; esac ;;
      *[Pp]ython*)
        case "$cmd" in "$APP"/*|*" $APP"/*)      # only python whose command line runs from THIS app folder
          kill "$pid" 2>/dev/null && echo "$(date '+%m-%d %H:%M:%S') killed python pid $pid footprint ${m} MB: $(echo "$cmd" | cut -c1-160)" >> "$LOG" ;; esac ;;
      *)
        [ "$m" -gt 5120 ] && { grep -q "big $pid " "$LOG" 2>/dev/null || echo "$(date '+%m-%d %H:%M:%S') big $pid ${m} MB $(echo "$cmd" | cut -c1-100)" >> "$LOG"; } ;;
    esac
  done
  df -g / | awk 'NR==2 && $4 < 1' | grep -q . && echo "$(date '+%m-%d %H:%M:%S') disk < 1 GB" >> "$LOG"
  sleep 10
done
