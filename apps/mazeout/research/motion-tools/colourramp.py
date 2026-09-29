"""Black -> exit-blue colour ramp: mean colour of the arrow's stroke pixels in a small window that follows the head
(window = [head-HB, head-HA] along the axis), per real frame."""
import sys
from mf import *
def ramp(clip,t0,t1,axis,band,headfn,label):
    t,px=raw(clip,t0,t1,786)
    for i in range(len(t)):
        f=px[i].astype(int)
        h=headfn(t[i])
        if h is None: continue
        if axis=='x':
            win=f[int(band[0]*2):int(band[1]*2), int((h-14)*2):int((h-6)*2)]
        else:
            win=f[int((h+6)*2):int((h+14)*2), int(band[0]*2):int(band[1]*2)]
        w=win.reshape(-1,3); m=w.max(1)-w.min(1)
        stroke=w[(w.sum(1)<600)]
        c=stroke.mean(0).astype(int) if len(stroke) else None
        print(label,f"{t[i]:.3f}",'#%02X%02X%02X'%tuple(c) if c is not None else None, len(stroke))
import numpy as np
# P01: head x from track1 (1.964 336.5 ... ) -> interpolate
P01=[(1.947,334.5),(1.964,336.5),(1.980,338.5),(1.997,343),(2.013,347),(2.030,351.5),(2.047,357),(2.063,363),(2.080,369),(2.097,376),(2.113,383)]
f1=lambda t: float(np.interp(t,[a for a,b in P01],[b for a,b in P01])) if t<=2.113 else None
ramp('S1-P01-press2s.mov',1.93,2.12,'x',(357,361),f1,'P01')
K=[(0.516,406.5),(0.532,404),(0.566,395.5),(0.582,390.5),(0.599,384.5),(0.616,377.5),(0.632,370.5),(0.649,362.5),(0.666,353.5),(0.682,344.5),(0.699,334.5)]
fk=lambda t: float(np.interp(t,[a for a,b in K],[b for a,b in K])) if t<=0.699 else None
ramp('S1-L33-key-first.mov',0.49,0.70,'y',(80,84),fk,'L33')
