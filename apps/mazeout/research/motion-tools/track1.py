"""Track a straight exit along x or y. usage: track1.py CLIP T0 T1 AXIS BAND_LO BAND_HI [x0 x1]
AXIS=x: band is a y range (pt) and the scan runs along x (full screen width); AXIS=y: band is an x range.
Prints per real frame: t, blue extent (min,max) in pt, dark(ink) extent in the band, mean colour of blue pixels."""
import sys
from mf import *
clip=sys.argv[1]; t0=float(sys.argv[2]); t1=float(sys.argv[3]); ax=sys.argv[4]; lo=float(sys.argv[5]); hi=float(sys.argv[6])
W=393*2  # 2 px per pt
if ax=='x': crop=(0,lo,393,hi-lo)
else: crop=(lo,0,hi-lo,852)
t,px=raw(clip,t0,t1,W if ax=='x' else int((hi-lo)*2),crop=crop)
for i in range(len(t)):
    f=px[i].astype(int); R,G,B=f[...,0],f[...,1],f[...,2]
    blue=(B>140)&(B-R>70)&(G>60)
    navy=(B-R>35)&(B<200)&(R<90)
    ink=(R<70)&(G<70)&(B<70)
    prof_b=blue.any(axis=0 if ax=='x' else 1)
    prof_n=navy.any(axis=0 if ax=='x' else 1)
    prof_k=ink.sum(axis=0 if ax=='x' else 1)
    sc=0.5
    off=0 if ax=='x' else 0
    def ext(p):
        w=np.where(p)[0]
        return (round(w.min()*sc,1),round(w.max()*sc,1),int(len(w))) if len(w) else None
    mc=tuple(int(v) for v in f[blue].mean(0)) if blue.sum()>20 else None
    print(f"{t[i]:.3f} blue {ext(prof_b)} navy {ext(prof_n)} ink {ext(prof_k>0)} col {mc}")
