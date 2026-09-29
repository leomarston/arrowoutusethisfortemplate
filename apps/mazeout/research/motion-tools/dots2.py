"""Vacated-cell dots, robust: find the dots present in the last frame inside a region, then trace each dot's centre
colour back in time. Prints per dot: centre (pt), first frame the stroke is gone, first frame the dot reaches 50 % and 90 %
of its final contrast."""
import sys
from mf import *
from scipy import ndimage
clip=sys.argv[1]; t0=float(sys.argv[2]); t1=float(sys.argv[3]); x0,y0,x1,y1=[float(v) for v in sys.argv[4].split(',')]
t,px=raw(clip,t0,t1,1179,crop=(x0,y0,x1-x0,y1-y0))
S=px.shape[2]/(x1-x0)
last=px[-1].astype(int)
R,G,B=last[...,0],last[...,1],last[...,2]
dot=(B>225)&(B-R>12)&(R>150)&(R<246)
lab,n=ndimage.label(dot)
cents=[]
for k in range(1,n+1):
    yy,xx=np.where(lab==k)
    if 6<=len(yy)<=120: cents.append((yy.mean(),xx.mean(),len(yy)))
print('dots found',len(cents))
out=[]
for (cy,cx,sz) in cents:
    yi,xi=int(round(cy)),int(round(cx))
    seq=px[:,max(yi-1,0):yi+2,max(xi-1,0):xi+2].reshape(len(t),-1,3).mean(1)
    fin=seq[-1]; white=np.array([255,255,255.])
    contrast=np.linalg.norm(seq-white,axis=1)/max(np.linalg.norm(fin-white),1)
    ink=(seq.sum(1)<300)|((seq[:,2]-seq[:,0]>90))
    # last index where ink/stroke present
    li=np.where(ink)[0]
    gone=t[li[-1]+1] if len(li) and li[-1]+1<len(t) else None
    start=li[-1]+1 if len(li) else 0
    c50=next((t[i] for i in range(start,len(t)) if contrast[i]>=0.5),None)
    c90=next((t[i] for i in range(start,len(t)) if contrast[i]>=0.9),None)
    out.append((cx/S+x0,cy/S+y0,sz,gone,c50,c90,tuple(int(v) for v in fin)))
for o in sorted(out,key=lambda o:(o[3] or 0)):
    print('dot at (%.1f,%.1f) size %d px  stroke_gone %s  50%% %s  90%% %s  final %s'%(o[0],o[1],o[2],
          f"{o[3]:.3f}" if o[3] else None, f"{o[4]:.3f}" if o[4] else None, f"{o[5]:.3f}" if o[5] else None, o[6]))
