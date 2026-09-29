#!/bin/sh
# usage: recact.sh NAME SECONDS -- phone-args...   (records research/video/NAME.mov, runs one phone action once frames are flowing)
# Measured 05:30: PhoneCapture's first frame lands ~0.95 s after the RECORDING log line, and the last 1-2 s of a clip are often
# missing (variable frame rate + writer tail). So: wait PRE s after RECORDING before acting, and record TAIL s longer than asked.
# Override with RECACT_PRE / RECACT_TAIL. Check a clip with: research/motion-tools/mfx pts OUT.mov
P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; R=/Users/yago/Downloads/app-factory/apps/mazeout/research
N=$1; S=$2; shift 2; [ "$1" = "--" ] && shift
PRE=${RECACT_PRE:-1.5}; TAIL=${RECACT_TAIL:-3}
TOTAL=$(python3 -c "print(round($S + $PRE + $TAIL, 2))")
O=$R/video/$N.mov; rm -f $O $O.log; ($P rec $O $TOTAL >/dev/null 2>&1 &)
for i in $(seq 1 60); do grep -q RECORDING $O.log 2>/dev/null && break; sleep 0.25; done
sleep $PRE
python3 -c "import time; print('ACT host_time', time.time())" > $O.marks
[ $# -gt 0 ] && $P "$@"
python3 -c "import time; print('ACT_DONE host_time', time.time())" >> $O.marks
for i in $(seq 1 120); do grep -qE 'SAVED|ERROR' $O.log 2>/dev/null && break; sleep 0.25; done
tail -1 $O.log
