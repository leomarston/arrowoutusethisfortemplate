"""Run-length colour profile down one pixel column (or along a row) of a reference shot: shows the layer stack of an
outlined title (background | outline | face | inner band | outline | shadow | background) with each run's length in px.
usage: profile.py FILE x y0 y1 [--row]   (px in the source image)"""
import sys, numpy as np
from PIL import Image
f=sys.argv[1]; x=int(sys.argv[2]); a0=int(sys.argv[3]); a1=int(sys.argv[4]); row='--row' in sys.argv
im=np.asarray(Image.open(f).convert('RGB')).astype(int)
line=im[x,a0:a1] if row else im[a0:a1,x]
runs=[]; 
for i,c in enumerate(line):
    q=tuple((c//6)*6)
    if runs and np.abs(np.array(runs[-1][2])-c).max()<=10: runs[-1][1]+=1
    else: runs.append([a0+i,1,tuple(c)])
print(' | '.join(f"{s}:{n}px #{c[0]:02X}{c[1]:02X}{c[2]:02X}" for s,n,c in runs))
