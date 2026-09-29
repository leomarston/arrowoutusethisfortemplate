import sys
from mf import *
from scipy import ndimage
name=sys.argv[1]; s=float(sys.argv[2]); e=float(sys.argv[3])
t,px=raw(name,s,e,393)
f=px.astype(int)
yel=(f[...,0]>190)&(f[...,1]>225)&(f[...,2]<70)
yel[:,:195]=False; yel[:,665:]=False
slots=[]
for k in range(7):
    cx=int(36.5+53*k)
    slots.append(f[:,695:705,cx-18:cx+18].mean(axis=(1,2,3)))
slots=np.array(slots)
prev_y=0
for i in range(1,len(t)):
    n=yel[i].sum()
    if n>40 and prev_y<=40:
        ys,xs=np.where(yel[i]); print(f'{t[i]:.3f} OUTLINE on at ({xs.mean():.0f},{ys.mean():.0f}) n={n}')
    prev_y=n
    for k in range(7):
        if slots[k,i]-slots[k,i-1]>35: print(f'{t[i]:.3f} FLASH slot{k+1} {slots[k,i-1]:.0f}->{slots[k,i]:.0f}')
