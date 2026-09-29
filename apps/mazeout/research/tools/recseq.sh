#!/bin/sh
# usage: recseq.sh NAME SECONDS "phone-args" ["sleep S" | "phone-args"]...   (PH-0 2026-09-28)
# Like recact.sh, but runs SEVERAL steps once frames flow: each step is either "sleep S" or the arguments of one phone command.
# Records research/video/NAME.mov; PRE/TAIL as recact (RECACT_PRE / RECACT_TAIL). Host times of each step go to NAME.mov.marks.
P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; R=/Users/yago/Downloads/app-factory/apps/mazeout/research
N=$1; S=$2; shift 2
PRE=${RECACT_PRE:-2.5}; TAIL=${RECACT_TAIL:-3}
TOTAL=$(python3 -c "print(round($S + $PRE + $TAIL, 2))")
O=$R/video/$N.mov; rm -f $O $O.log $O.marks; ($P rec $O $TOTAL >/dev/null 2>&1 &)
for i in $(seq 1 60); do grep -q RECORDING $O.log 2>/dev/null && break; sleep 0.25; done
sleep $PRE
for step in "$@"; do
  case "$step" in
    sleep*) sleep ${step#sleep } ;;
    *) python3 -c "import time,sys; print('STEP', sys.argv[1], time.time())" "$step" >> $O.marks; $P $step ;;
  esac
done
python3 -c "import time; print('DONE', time.time())" >> $O.marks
for i in $(seq 1 160); do grep -qE 'SAVED|ERROR' $O.log 2>/dev/null && break; sleep 0.25; done
tail -1 $O.log
