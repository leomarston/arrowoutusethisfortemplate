#!/bin/sh
# heartbeat.sh MINUTES wf_ids... : wakes the orchestrator after MINUTES, or early on disk < 6 GB or a stalled agent (idle > 45 min)
M=$1; shift
for i in $(seq 1 $M); do
  f=$(df -g / | awk 'NR==2{print $4}'); [ "$f" -lt ${HB_DISK_MIN:-6} ] && { echo "ALARM disk ${f}G $(date +%H:%M)"; exit 1; }
  if [ $((i % 10)) -eq 0 ]; then s=$(python3 "$(dirname "$0")/stallcheck.py" 45 "$@" | grep STALL); [ -n "$s" ] && { echo "ALARM $s"; exit 1; }; fi
  sleep 60
done
echo "heartbeat $(date +%H:%M) disk $(df -h / | awk 'NR==2{print $4}')"
