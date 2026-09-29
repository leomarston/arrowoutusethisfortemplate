import sys
from mf import *
name=sys.argv[1]; step=float(sys.argv[2]) if len(sys.argv)>2 else 0.5
s=float(sys.argv[3]) if len(sys.argv)>3 else 0; e=float(sys.argv[4]) if len(sys.argv)>4 else 999
t,px=raw(name,0,999,131)
idx=[]; 
for x in np.arange(max(s,t[0]),min(e,t[-1])+1e-6,step):
    i=int(np.searchsorted(t,x+1e-6)-1); i=max(i,0); idx.append(i)
out=f'w/ov_{name[:-4]}_{s}_{step}.jpg'
sheet([Image.fromarray(px[i]) for i in idx],[f'{t[i]:.2f}' for i in idx],out,cols=14)
print(out)
