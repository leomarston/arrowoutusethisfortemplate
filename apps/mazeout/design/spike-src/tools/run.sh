#!/bin/zsh
setopt nullglob
# usage: run.sh <label> <readytag> <timeout_s> [launch args...]
U=177520B6-4889-46C2-BDD9-155813D2B175
B=com.manycode.mazeout.spike
OUT=/Users/yago/Downloads/app-factory/apps/mazeout/design/spike-shots
RES=${RES:-/tmp/pathspike-results}
mkdir -p $RES
label=$1; tag=$2; to=$3; shift 3
D=$(xcrun simctl get_app_container $U $B data)
rm -f $D/tmp/ready-*.txt $D/tmp/spike-*.json
xcrun simctl launch --terminate-running-process $U $B "$@" >/dev/null
i=0
while [ ! -f $D/tmp/ready-$tag.txt ] && [ $i -lt $((to*5)) ]; do sleep 0.2; i=$((i+1)); done
if [ -f $D/tmp/ready-$tag.txt ]; then
  xcrun simctl io $U screenshot --type=png $OUT/$label.png >/dev/null 2>&1
  cp $D/tmp/spike-*.json $RES/$label.json 2>/dev/null
  echo "OK $label"
else
  echo "TIMEOUT $label"; xcrun simctl io $U screenshot --type=png $OUT/$label-timeout.png >/dev/null 2>&1
fi
