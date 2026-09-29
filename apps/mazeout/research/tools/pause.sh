#!/bin/sh
# pause.sh — tap the in-level pause button and VERIFY the Paused panel is up (dimmed HUD); retry up to 3x.
P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; T=/Users/yago/Downloads/app-factory/apps/mazeout/research/bot/tmp/pausecheck.png
for i in 1 2 3; do
  $P tap 352 88 >/dev/null; sleep 0.35; $P shot $T >/dev/null
  if python3 -c "
from PIL import Image; import numpy as np, sys
a=np.array(Image.open('$T').convert('RGB')).astype(int)
p=a[int(76*2.997):int(100*2.997), int(340*2.997):int(364*2.997)].reshape(-1,3)
blue=((p[:,2]>110)&(p[:,2]>p[:,0]+60)).mean()
# Paused panel: big orange 'Paused' title around y 230 pt, and dim board
t=a[int(215*2.997):int(245*2.997), int(120*2.997):int(270*2.997)].reshape(-1,3)
orange=((t[:,0]>200)&(t[:,1]>120)&(t[:,2]<90)).mean()
print('pause_blue',round(blue,3),'orange',round(orange,3))
sys.exit(0 if (blue<0.25 and orange>0.05) else 1)
"; then echo PAUSED; exit 0; fi
  sleep 0.3
done
echo PAUSE_FAILED; exit 1
