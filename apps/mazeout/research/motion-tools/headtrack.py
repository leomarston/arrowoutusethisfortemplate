"""Head/tail tracker for exits: 'new blue' = exit-blue pixels absent in a reference frame (kills the static HUD blue).
usage: headtrack.py CLIP T0 T1 TREF AXIS(x|y) BAND_LO BAND_HI [DIR(+|-)]
AXIS=y: scan the column band x in [LO,HI] pt; AXIS=x: scan the row band y in [LO,HI] pt. Prints extents (pt) of new blue."""
import sys
from mf import *
clip=sys.argv[1]; t0=float(sys.argv[2]); t1=float(sys.argv[3]); tref=float(sys.argv[4]); ax=sys.argv[5]; lo=float(sys.argv[6]); hi=float(sys.argv[7])
t,px=raw(clip,min(t0,tref)-0.02,t1,786)
def cls(f):
    f=f.astype(int); R,G,B=f[...,0],f[...,1],f[...,2]
    return (B>120)&(B-R>60)&(G>50), (B-R>30)&(R<100)&(B>50)
r=int(np.argmin(abs(t-tref))); refb,refn=cls(px[r]); ref=refb|refn
from scipy import ndimage
ref=ndimage.binary_dilation(ref,iterations=2)
out=[]
for i in range(len(t)):
    if t[i]<t0-1e-6: continue
    b,n=cls(px[i]); m=(b|n)&~ref
    if ax=='y': prof=m[:,int(lo*2):int(hi*2)].any(1)
    else: prof=m[int(lo*2):int(hi*2),:].any(0)
    w=np.where(prof)[0]/2
    nb=int((b&~ref).sum()); nn=int((n&~b&~ref).sum())
    print(f"{t[i]:.3f} ext {('%.1f..%.1f'%(w.min(),w.max())) if len(w) else '-':>14} len {len(w)/1:6.1f}  newblue {nb:6d} newnavy {nn:5d}")
