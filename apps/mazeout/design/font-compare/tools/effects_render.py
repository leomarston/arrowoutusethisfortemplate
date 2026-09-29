"""Rebuild outlined titles from the SPEC (shipped font + measured effects) and put them next to the reference colour
crop, to check the effect numbers by eye.  Layers, back to front (all at 4x, then box-downsampled):
  shadow  : the outline shape moved down by `drop` px, outline colour
  outline : glyph dilated by `w` px (Euclidean distance, anti-aliased), outline colour
  band    : (optional) the glyph moved down by `band` px, band colour (the 'Paused' title's peach inner step)
  face    : the glyph, vertical gradient face_top -> face_bottom
px are reference-shot px (1178-wide phone shots; pt = px*393/1178).
usage: effects_render.py OUT.png"""
import json, os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
import compare, fine
SS=compare.SS; FC=compare.FC
FONT=FC.rstrip('/').rsplit('/',1)[0]+'/fonts/PCDisplay-Black.ttf'
spec=json.load(open(FC+'results/final_spec_fit.json'))
H=lambda s: np.array([int(s[i:i+2],16) for i in (1,3,5)],float)
FX={ # measured in results/effects.json + tools/profile.py runs (see fonts.md §5)
 'paused':   dict(face=('#FFFFFF','#FFFFFF'), outline='#7B1D01', w=5.6, drop=9.45, band=('#FFD699',4.5)),
 'play':     dict(face=('#F1FFF2','#F1FFF2'), outline='#066A01', w=6.6, drop=6.6),
 'resume':   dict(face=('#FFFCED','#FDF4DD'), outline='#066A01', w=4.0, drop=3.2),
 'quit':     dict(face=('#FFFCED','#FDF4DC'), outline='#650000', w=4.4, drop=4.2),
 'on_sound': dict(face=('#FFFCED','#FDF3DC'), outline='#066A01', w=3.0, drop=3.0),
 'level_tab':dict(face=('#FFF9EF','#FFEDCB'), outline='#002985', w=1.9, drop=2.2),
 'timer':    dict(face=('#F7F7F9','#E2E3EA'), outline='#081E5E', w=2.0, drop=3.4),
 'LEVEL':    dict(face=('#FFFFFF','#FFFFFF'), outline='#093198', w=2.45, drop=2.3),
 'num32':    dict(face=('#FFFFFF','#FFFFFF'), outline='#066A01', w=6.4, drop=1.5),
 'home':     dict(face=('#FFFFFF','#FFFFFF'), outline='#16388C', w=2.95, drop=1.75),
 'loading':  dict(face=('#CCCCCC','#CCCCCC'), outline='#681E1A', w=2.6, drop=1.2),
}
sz=compare.sizing(FONT,None,None,sorted(set(compare.SIZING[k][1] for k in FX)))
size0=compare.render([dict(id='p',font=FONT,ps=None,axes=None,cap=compare.CAP0*SS,text='H',H=400,base=300,x=10)],'p')['p'][1]['size']
tiles=[]; lab=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',15)
for k,fx in FX.items():
    sp=spec[k]; ppt=fine.px_per_pt(k); s=sp['size_pt']*ppt*SS/size0; ch=compare.SIZING[k][1]; g=compare.REFG[k]
    ref=compare.REF[k]; hh,ww=ref.shape; pad=14
    job=dict(id='e_'+k,font=FONT,ps=None,axes=None,cap=compare.CAP0*SS*s,text=compare.M[k]['text'],H=hh*SS,
             base=g['bottom']*SS-sz[ch]['off']*s,x=6*SS,track=sp['track_pt']*ppt*SS)
    r,m=compare.render([job],'ef')['e_'+k]
    sc,_=compare.score(ref,r)
    # place the 4x glyph exactly where score() aligned it
    dx=int(round(sc['dx']*SS)); dy=int(round(sc['dy']*SS))
    G=np.zeros(((hh+2*pad)*SS,(max(ww,r.shape[1]//SS)+2*pad)*SS))
    y0=pad*SS+dy; x0=pad*SS+dx; G[y0:y0+r.shape[0], x0:x0+r.shape[1]]=r[:G.shape[0]-y0, :G.shape[1]-x0]
    dout=ndimage.distance_transform_edt(G<0.5)/SS
    outl=np.clip(fx['w']-dout+0.5,0,1)
    shift=lambda a,px: np.pad(a,((int(round(px*SS)),0),(0,0)))[:a.shape[0]]
    shadow=shift(outl,fx['drop'])
    col=lambda c: H(c)[None,None,:]
    bgc=H(compare.M[k]['colours']['bg'])
    img=np.ones(G.shape+(3,))*bgc
    for a,c in ((shadow,col(fx['outline'])),(outl,col(fx['outline']))):
        img=img*(1-a[...,None])+c*a[...,None]
    if 'band' in fx:
        b=shift(G,fx['band'][1]); img=img*(1-b[...,None])+col(fx['band'][0])*b[...,None]
    rows=np.where(G.max(1)>0.5)[0]; t=np.clip((np.arange(G.shape[0])-rows[0])/max(rows[-1]-rows[0],1),0,1)[:,None,None]
    facec=H(fx['face'][0])[None,None,:]*(1-t)+H(fx['face'][1])[None,None,:]*t
    img=img*(1-G[...,None])+facec*G[...,None]
    h2=img.shape[0]//SS*SS; w2=img.shape[1]//SS*SS
    img=img[:h2,:w2].reshape(h2//SS,SS,w2//SS,SS,3).mean((1,3))
    ours=Image.fromarray(np.clip(img,0,255).astype(np.uint8))
    refc=Image.open(FC+'crops/'+k+'.png').convert('RGB')
    rb=Image.new('RGB',ours.size,tuple(int(v) for v in bgc)); rb.paste(refc,(pad,pad))
    sc2=2
    rb=rb.resize((rb.width*sc2,rb.height*sc2),Image.LANCZOS); ours=ours.resize((ours.width*sc2,ours.height*sc2),Image.LANCZOS)
    tile=Image.new('RGB',(rb.width+ours.width+30, rb.height+22),(255,255,255)); d=ImageDraw.Draw(tile)
    d.text((4,2),f"{k}: reference (left) | spec rebuild (right): {sp['size_pt']:.1f} pt, trk {sp['track_pt']:+.2f}, outline {fx['outline']} {fx['w']/ppt:.2f} pt, drop {fx['drop']/ppt:.2f} pt",fill=(0,0,0),font=lab)
    tile.paste(rb,(0,22)); tile.paste(ours,(rb.width+30,22)); tiles.append(tile)
W=max(t.width for t in tiles); S=Image.new('RGB',(W,sum(t.height+8 for t in tiles)),(255,255,255)); y=0
for t in tiles: S.paste(t,(0,y)); y+=t.height+8
sc=float(os.environ.get('SCALE','1'))
if sc!=1: S=S.resize((int(S.width*sc),int(S.height*sc)),Image.LANCZOS)
S.save(sys.argv[1]); print(sys.argv[1],S.size)
