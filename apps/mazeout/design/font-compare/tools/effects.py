"""Measure the text effects of the outlined samples: face colour (top / middle / bottom of the face = gradient),
outline colour at the top vs the bottom band (a darker bottom band = a separate drop shadow), outline width per side
(face edge -> outer edge, per column / row, sub-pixel threshold crossings), and the extra depth at the bottom.
px are source px (phone shots 1178 wide: pt = px*393/1178; store shots 1320 wide: pt = px/3 on a 440-pt canvas).
usage: effects.py [names...] -> results/effects.json"""
import json, os, sys, numpy as np
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__)); FC=os.path.dirname(HERE)+'/'; O=FC+'crops/'
M=json.load(open(O+'measure.json'))
def cross(v, thr=0.5, rev=False):
    """sub-pixel position of the first crossing of thr (from the start, or from the end if rev)"""
    if rev: v=v[::-1]
    idx=np.where(v>=thr)[0]
    if len(idx)==0: return None
    i=idx[0]
    if i==0: pos=0.0
    else:
        a,b=v[i-1],v[i]; pos=(i-1)+(thr-a)/(b-a)+0.5
    return (len(v)-pos) if rev else pos
def hexc(c): return '#%02X%02X%02X'%tuple(int(round(x)) for x in c)
res={}
names=sys.argv[1:] or [k for k,v in M.items() if v['mode']=='outl']
for k in names:
    if not os.path.exists(O+k+'_outer.npy'): continue
    f=np.load(O+k+'_ink.npy'); o=np.load(O+k+'_outer.npy'); c=np.asarray(Image.open(O+k+'.png').convert('RGB')).astype(float)
    tops=[];bots=[];lefts=[];rights=[]
    for x in range(f.shape[1]):
        if f[:,x].max()<0.99: continue
        a=cross(f[:,x]); b=cross(o[:,x]); a2=cross(f[:,x],rev=True); b2=cross(o[:,x],rev=True)
        if None in (a,b,a2,b2): continue
        tops.append(a-b); bots.append(b2-a2)
    for y in range(f.shape[0]):
        if f[y].max()<0.99: continue
        a=cross(f[y]); b=cross(o[y]); a2=cross(f[y],rev=True); b2=cross(o[y],rev=True)
        if None in (a,b,a2,b2): continue
        lefts.append(a-b); rights.append(b2-a2)
    fy=np.where(f.max(1)>0.99)[0]; y0,y1=fy[0],fy[-1]; hh=y1-y0
    full=f>0.99
    def band(m, a, b):
        rows=np.zeros_like(m); rows[int(a):int(b)+1]=True; sel=m&rows
        return hexc(np.median(c[sel],0)) if sel.any() else None
    ring=(o>0.99)&(f<0.01)
    res[k]=dict(text=M[k]['text'],
        face_top=band(full,y0,y0+0.2*hh), face_mid=band(full,y0+0.4*hh,y0+0.6*hh), face_bottom=band(full,y1-0.2*hh,y1),
        outline_top=band(ring,0,y0+0.25*hh), outline_bottom=band(ring,y1+1,f.shape[0]),
        width_top_px=round(float(np.median(tops)),2) if tops else None,
        width_bottom_px=round(float(np.median(bots)),2) if bots else None,
        width_left_px=round(float(np.median(lefts)),2) if lefts else None,
        width_right_px=round(float(np.median(rights)),2) if rights else None,
        n=[len(tops),len(lefts)])
    r=res[k]
    if r['width_top_px'] is not None:
        r['side_mean_px']=round(float(np.mean([r['width_left_px'],r['width_right_px'],r['width_top_px']])),2)
        r['bottom_extra_px']=round(r['width_bottom_px']-r['side_mean_px'],2)
    print(k, r)
json.dump(res,open(FC+'results/effects.json','w'),indent=1)
