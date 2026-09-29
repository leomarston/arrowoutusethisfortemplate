#!/bin/sh
# socialsnap.sh NNN [noturkeytop] — from HOME: Leaderboard Weekly (player view + top/bottom), World top 2 pages, Turkey player row
# (+ top unless noturkeytop), back to HOME. Shots shots/NNN-social-HHMMSS-*.png; OCR rows appended to build/phone2/social-ocr.txt.
R=/Users/yago/Downloads/app-factory/apps/mazeout/research; P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone
O=/Users/yago/Downloads/app-factory/apps/mazeout/build/phone2/social-ocr.txt
t() { perl -e 'alarm shift; exec @ARGV' 40 $P "$@" >/dev/null; }
s() { F=$($R/tools/snap.sh $N "$1" | tail -1); echo "== $F" >> $O; python3 $R/tools/lbrows.py $F ${2:-150} 800 >> $O; echo $F; }
N=$1
t tap 325 805; sleep 1.8; t tap 72 146; sleep 1.8; s weekly-player 330
t swipe 196 540 196 760 0.5; sleep 1.2; s weekly-top 330
t swipe 196 760 196 420 0.5; sleep 1.2; s weekly-bottom 330
t tap 196 146; sleep 2.0; s world-p1 190
t swipe 196 700 196 250 0.6; sleep 1.5; s world-p2 190
t tap 317 146; sleep 2.0; s turkey-player 190
if [ "$2" != noturkeytop ]; then
  for i in $(seq 1 24); do t swipe 196 260 196 760 0.1; done; sleep 1.5; s turkey-top 190
fi
t tap 196 805; sleep 1.5
