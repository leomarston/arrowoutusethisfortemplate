"""Tap ripple: radial luminance profile around the tap point per real frame (white-background pixels only)."""
import sys
from mf import *
clip=sys.argv[1]; cx=float(sys.argv[2]); cy=float(sys.argv[3]); t0=float(sys.argv[4]); t1=float(sys.argv[5])
R=40
t,px=raw(clip,t0,t1,786,crop=(cx-R,cy-R,2*R,2*R))
S=px.shape[2]/(2*R)
yy,xx=np.mgrid[0:px.shape[1],0:px.shape[2]]
rr=np.hypot(xx/S-R,yy/S-R)
ref=px[0].astype(int)
bgmask=(ref.min(2)>235)   # white background in the reference (before the tap)
for i in range(len(t)):
    f=px[i].astype(int); L=f.mean(2)
    neutral=(np.abs(f[...,0]-f[...,2])<14)
    m=bgmask&neutral
    prof=[]
    for r in range(0,R,3):
        a=m&(rr>=r)&(rr<r+3)
        prof.append(int(L[a].mean()) if a.sum()>5 else -1)
    # radius where luminance < 250 (disc edge), searching outward
    edge=None
    for r in np.arange(0,R,0.5):
        a=m&(rr>=r)&(rr<r+0.5)
        if a.sum()>3 and L[a].mean()>251: edge=r; break
    print(f"{t[i]:.3f} edge_r {edge}  L(r=0,3,6..): {prof}")
