#!/bin/sh
# apps/mazeout/tools/watchdog.sh — exits on an alarm (wakes the orchestrator)
A="$(cd "$(dirname "$0")/.." && pwd)"; R="$(cd "$A/../.." && pwd)"; idle=0; touch /tmp/mazeout-wd; mkdir -p $A/build
while :; do
  free=$(df -g / | awk 'NR==2{print $4}')
  echo "$(date +%H:%M) disk ${free}G $(sysctl vm.swapusage | cut -c1-70)" >> $A/build/health.log
  if [ -n "$(find $A -newer /tmp/mazeout-wd -type f ! -name health.log 2>/dev/null | head -1)" ]; then idle=0; else idle=$((idle+5)); fi
  touch /tmp/mazeout-wd
  [ "$free" -lt 2 ] && { echo "ALARM disk ${free} GB"; exit 1; }
  pgrep -qf "caffeinate -dimsu -t" || { echo "ALARM caffeinate ended"; exit 1; }
  [ -f /tmp/mazeout-runner-expected ] && [ -f /tmp/phonedriver.lock/owner ] && grep -q "mazeout" /tmp/phonedriver.lock/owner && \
    ! "$R/tools/phonedriver/phone" status >/dev/null 2>&1 && { echo "ALARM phone runner down"; exit 1; }
  [ $idle -ge 45 ] && { echo "ALARM nothing written for 45 min (stall?)"; exit 1; }
  sleep 300
done
