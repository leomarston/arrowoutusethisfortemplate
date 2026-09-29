#!/bin/sh
# usage: recact2.sh NAME SECONDS -- phone-args...   like recact.sh, but writes host epoch-ms marks to video/NAME.mov.marks
P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; R=/Users/yago/Downloads/app-factory/apps/mazeout/research
N=$1; S=$2; shift 2; [ "$1" = "--" ] && shift
ms() { perl -MTime::HiRes=time -e 'printf "%d\n", time*1000'; }
O=$R/video/$N.mov; M=$O.marks; rm -f $O $O.log $M; echo "rec_cmd $(ms)" > $M; ($P rec $O $S >/dev/null 2>&1 &)
for i in $(seq 1 80); do grep -q RECORDING $O.log 2>/dev/null && break; sleep 0.05; done
echo "recording_seen $(ms)" >> $M
[ -n "$DELAY" ] && sleep $DELAY; if [ $# -gt 0 ]; then echo "action_start $(ms) $*" >> $M; $P "$@" >> $M 2>&1; echo "action_end $(ms)" >> $M; fi
sleep $S; sleep 1.5; tail -1 $O.log; cat $M
