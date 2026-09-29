"""Key flight (L33): centroid, size and principal-axis angle of the gold key per real frame.
Gold = R>200, 150<G<225, B<110 and changed vs the frame before the tap (doors' static orange frames cancel out)."""
from mf import *
from scipy import ndimage
t,px=raw('S1-L33-key-first.mov',0.45,1.7,786,crop=(0,300,200,380))
S=px.shape[2]/200
ref=px[0].astype(int)
for i in range(len(t)):
    f=px[i].astype(int); R,G,B=f[...,0],f[...,1],f[...,2]
    gold=(R>200)&(G>150)&(G<228)&(B<120)
    ch=np.abs(f-ref).sum(2)>50
    m=gold&(ch|(t[i]<0.53))
    # keep the largest component
    lab,n=ndimage.label(ndimage.binary_closing(m,iterations=1))
    if n==0: print(f"{t[i]:.3f} no key"); continue
    sz=ndimage.sum(m,lab,range(1,n+1)); k=int(np.argmax(sz))+1
    yy,xx=np.where((lab==k)&m)
    if len(yy)<10: print(f"{t[i]:.3f} tiny {len(yy)}"); continue
    cx=xx.mean()/S; cy=yy.mean()/S+300
    cov=np.cov(np.vstack([xx,yy])); w,v=np.linalg.eigh(cov); ang=np.degrees(np.arctan2(v[1,1],v[0,1]))
    L=4*np.sqrt(w[1])/S
    print(f"{t[i]:.3f} key centre ({cx:6.1f},{cy:6.1f}) px {len(yy):5d} long-axis {L:5.1f}pt angle {ang:6.1f}")
