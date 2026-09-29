"""Vacated-cell dots: per path cell, the colour at the cell centre per real frame (P02-A, L32 arrow at 0.786x zoom)."""
from mf import *
cells=[(17,10),(17,9),(17,8),(18,8),(18,9),(18,10),(18,11),(17,11),(17,12),(18,12),(19,12),(19,11),(19,10),(19,9),(19,8),(19,7),(19,6),(18,6),(17,6),(16,6),(15,6),(14,6),(14,5),(14,4),(14,3),(14,2)]
P=14.04; X0=259.3; Y0=332.0
t,px=raw('S1-P02-queued-tap-250ms.mov',0.45,1.30,1179)  # 3 px/pt
S=3
def state(c):
    r,g,b=c
    if r+g+b<250: return 'K'          # black ink
    if b>200 and r<120: return 'B'    # exit blue stroke
    if r>245 and g>245 and b>245: return '.'  # white
    if b>235 and 170<r<235: return 'o'  # pale dot (#C5E1FF)
    return '?'
rows=[]
for k,(c,r) in enumerate(cells):
    x=X0+(c-14)*P; y=Y0+(r-2)*P
    seq=[]
    for i in range(len(t)):
        f=px[i][int(y*S)-1:int(y*S)+2, int(x*S)-1:int(x*S)+2].reshape(-1,3).mean(0)
        seq.append((t[i],state(f),tuple(int(v) for v in f)))
    # first frame not ink/blue after being blue, first frame 'o'
    left=next((tt for tt,s,_ in seq if tt>0.5 and s not in 'KB'),None)
    dot=next((tt for tt,s,_ in seq if s=='o'),None)
    cols=[f"{tt:.3f}{s}" for tt,s,_ in seq]
    fin=seq[-1][2]
    print(f"cell#{k:2d} {c,r} path_s_from_tail={k}  stroke_gone {left}  dot_first {dot}  final {fin}")
    rows.append((k,left,dot))
print(' '.join(s for _,s,_ in seq))
