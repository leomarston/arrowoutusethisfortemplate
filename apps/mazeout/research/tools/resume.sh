#!/bin/sh
# resume.sh — tap Resume ONLY if the Paused panel is really up (else a tap at (123,530) would hit the board).
P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; T=/Users/yago/Downloads/app-factory/apps/mazeout/research/bot/tmp/resumecheck.png
$P shot $T >/dev/null
if python3 -c "
from PIL import Image; import numpy as np, sys
a=np.array(Image.open('$T').convert('RGB')).astype(int)
g=a[int(515*2.997):int(545*2.997), int(80*2.997):int(165*2.997)].reshape(-1,3)
green=((g[:,1]>150)&(g[:,0]<120)&(g[:,2]<120)).mean()
t=a[int(215*2.997):int(245*2.997), int(120*2.997):int(270*2.997)].reshape(-1,3)
orange=((t[:,0]>200)&(t[:,1]>120)&(t[:,2]<90)).mean()
print('resume_green',round(green,3),'orange',round(orange,3))
sys.exit(0 if (green>0.3 and orange>0.05) else 1)
"; then $P tap 123 530 >/dev/null; echo RESUMED; else echo NOT_PAUSED_NO_TAP; fi
