#!/bin/sh
# socialsnap.sh NNN [noturkeytop] — from HOME: Leaderboard Weekly (player view + top/bottom), World top 2 pages, Turkey player row
# (+ top unless noturkeytop), back to HOME. Shots shots/NNN-social-HHMMSS-*.png; OCR rows appended to build/phone3/social-ocr.txt.
R=/Users/yago/Downloads/app-factory/apps/mazeout/research; P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone
O=/Users/yago/Downloads/app-factory/apps/mazeout/build/phone3/social-ocr.txt
t() { perl -e 'alarm shift; exec @ARGV' 40 $P "$@" >/dev/null; }
s() { F=$($R/tools/snap.sh $N "$1" | tail -1); echo "== $F" >> $O; python3 $R/tools/lbrows.py $F ${2:-150} 800 >> $O; echo $F; }
N=$1
$P shot /Users/yago/Downloads/app-factory/apps/mazeout/build/phone3/ss3-home.png >/dev/null; python3 -c "
from PIL import Image; import numpy as np, sys
a=np.array(Image.open('/Users/yago/Downloads/app-factory/apps/mazeout/build/phone3/ss3-home.png').convert('RGB')).astype(int); S=1178/393
g=a[int(800*S):int(845*S), int(5*S):int(30*S)].reshape(-1,3); sys.exit(0 if ((g[:,2]>180)&(g[:,0]<90)&(g[:,1]>60)).mean()>0.6 else 1)" || { echo NOT_HOME; exit 3; }
t tap 325 805; sleep 1.8; t tap 72 146; sleep 1.8; s weekly-player 330
t swipe 196 540 196 760 0.5; sleep 1.2; s weekly-top 330
t swipe 196 760 196 420 0.5; sleep 1.2; s weekly-bottom 330
t tap 196 146; sleep 2.0; for i in 1 2 3 4 5 6 7 8; do t swipe 196 260 196 760 0.1; done; sleep 1.5; s world-p1 190
t swipe 196 700 196 250 0.6; sleep 1.5; s world-p2 190
t swipe 196 700 196 250 0.6; sleep 1.5; s world-p3 190
t tap 317 146; sleep 2.0; s turkey-player 190
if [ "$2" != noturkeytop ]; then
  for i in $(seq 1 24); do t swipe 196 260 196 760 0.1; done; sleep 1.5; s turkey-top 190
fi
t tap 196 805; sleep 1.5
