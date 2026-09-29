#!/bin/sh
# level.sh LEVEL NNN — from HOME: tap Play, shot the start (shots/NNN-L<level>-start.png), read + overlay, print summary,
# write a side-by-side preview to the scratchpad (prev.png). The timer does not run until the first tap.
R=/Users/yago/Downloads/app-factory/apps/mazeout/research; P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone
L=$1; N=$2; LL=$(printf %03d $L); S=$R/shots/$N-L$LL-start.png
$P tap 196 668 >/dev/null; sleep 1.6; $P shot $S >/dev/null
cd /Users/yago/Downloads/app-factory/apps/mazeout
python3 research/bot/bot.py read $S --level $L --tag start | grep -v '^obstacles'
python3 -c "
from PIL import Image
a=Image.open('$S').resize((393,852)); b=Image.open('research/bot/overlay/L$LL-start.png').resize((393,852))
W=Image.new('RGB',(796,852),'white'); W.paste(a,(0,0)); W.paste(b,(403,0)); W.save('/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad/prev.png')"
