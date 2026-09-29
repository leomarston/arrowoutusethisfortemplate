#!/bin/sh
# gaplevel.sh LEVEL NNN — from HOME: open the level (go2 --no-play), scan for gap-clip candidates, then WITHOUT pauses:
#  hit-tolerance taps (1/3 and 2/3 between two parallel free arrows, a lossless shot after each) and a long-gap bump clip, then the
#  corner-aware bot finishes the level. Logs to build/phone2/gap-L<level>.log
R=/Users/yago/Downloads/app-factory/apps/mazeout/research; P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone
B=/Users/yago/Downloads/app-factory/apps/mazeout/build/phone2; L=$1; N=$2; LL=$(printf %03d $L)
cd /Users/yago/Downloads/app-factory/apps/mazeout
python3 $R/bot/go2.py $L $N --no-play 2>&1 | grep -v "Warning\|return _\|ret = " | cut -c1-300
S=$R/shots/$N-L$LL-start.png; [ -f $S ] || { echo "no start shot"; exit 1; }
python3 $R/tools/gapscan.py $S $L 2>/dev/null | tail -1 > $B/gap-L$LL.json
python3 - $B/gap-L$LL.json <<'PY' > $B/gap-L$LL.sh
import json, sys
d = json.load(open(sys.argv[1])); P = '/Users/yago/Downloads/app-factory/tools/phonedriver/phone'
R = '/Users/yago/Downloads/app-factory/apps/mazeout/research'; out = []
if d['par']:
    q = d['par'][0]; a, b = q['a'], q['b']
    t1 = [round(a[0] + (b[0] - a[0]) / 3, 1), round(a[1] + (b[1] - a[1]) / 3, 1)]
    t2 = [round(a[0] + 2 * (b[0] - a[0]) / 3, 1), round(a[1] + 2 * (b[1] - a[1]) / 3, 1)]
    out.append('echo "HIT pair %s a=%s b=%s taps %s then %s"' % (q['ids'], a, b, t1, t2))
    out.append('%s tap %s %s >/dev/null; sleep 0.9; %s shot SHOTDIR-hit13.png >/dev/null' % (P, t1[0], t1[1], P))
    out.append('%s tap %s %s >/dev/null; sleep 0.9; %s shot SHOTDIR-hit23.png >/dev/null' % (P, t2[0], t2[1], P))
if d['long']:
    x = sorted(d['long'], key=lambda z: -z['gap'])[0]
    out.append('echo "LONG bump id %s dir %s gap %s tap %s"' % (x['id'], x['dir'], x['gap'], x['tap']))
    out.append('RECACT_TAIL=2 sh %s/tools/recact.sh S2-LVL-bump-gap%d 2.5 -- tap %s %s' % (R, x['gap'], x['tap'][0], x['tap'][1]))
print('\n'.join(out))
PY
sed -i '' "s#SHOTDIR#$R/shots/$N-L$LL#g; s#LVL#L$LL#g" $B/gap-L$LL.sh
cat $B/gap-L$LL.sh | grep echo
sh $B/gap-L$LL.sh
python3 $R/bot/corners.py play2 --level $L --seconds 170 2>&1 | grep -v "Warning\|return _\|ret = " | tail -3
