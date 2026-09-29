"""Dots via local maxima of blueness (B-R) on a smoothed frame; trace each dot's blueness over time.
usage: dots3.py CLIP T0 T1 x0,y0,x1,y1 [REFT]  -> dots that are ABSENT at REFT (default T0) and present at T1."""
import sys
from mf import *
from scipy import ndimage
clip=sys.argv[1]; t0=float(sys.argv[2]); t1=float(sys.argv[3]); x0,y0,x1,y1=[float(v) for v in sys.argv[4].split(',')]
t,px=raw(clip,t0,t1,1179,crop=(x0,y0,x1-x0,y1-y0))
S=px.shape[2]/(x1-x0)
def blu(f):
    f=f.astype(float); b=f[...,2]-f[...,0]
    b[(f.sum(-1)<400)]=0          # ignore ink
    b[(f[...,2]-f[...,0])>100]=0  # ignore exit-blue strokes
    return ndimage.gaussian_filter(b,1.2)
BL=np.array([blu(f) for f in px])
last=BL[-1]; first=BL[0]
mx=(last==ndimage.maximum_filter(last,size=int(S*5)))&(last>18)&(first<8)
ys,xs=np.where(mx)
print('new dots',len(ys))
for y,x in sorted(zip(ys,xs),key=lambda p:(p[1],p[0])):
    tr=BL[:,y,x]; fin=tr[-1]
    i50=next((i for i in range(len(t)) if tr[i]>=0.5*fin),None); i90=next((i for i in range(len(t)) if tr[i]>=0.9*fin),None)
    prev=t[i50-1] if i50 else None
    print('dot (%.1f,%.1f) final %.0f  50%% at %.3f (prev frame %.3f)  90%% at %.3f'%(x/S+x0,y/S+y0,fin,t[i50],prev if prev else -1,t[i90]))
