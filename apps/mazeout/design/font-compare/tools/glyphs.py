"""Glyph 'tells' sheet: reference glyphs cut from the crops (blob i of a crop) vs the same glyph cut from each
candidate's render of the same line (sized on the crop's sizing glyph, so every glyph is at the reference scale).
Rows = fonts (reference first, red), columns = glyphs.  Cells show '-' when the candidate's blob count differs.
usage: glyphs.py OUT.png "Fam:w,Fam:w,..." [set]   set = plain | face | digits (default plain)"""
import json, os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from candidates import C, instances
import compare
SS=compare.SS
SETS={
 'plain':[('haptic',0),('haptic',1),('haptic',2),('haptic',3),('haptic',5),('sound',0),('sound',4),('full',0),('full',1),
          ('s_kate',0),('s_kate',1),('s_kate',3),('s_max',0),('s_max',2),('s_james',0),('s_james',2),('s_james',4)],
 'digits':[('coins_home',0),('coins_home',2),('coins_home',3),('s_x1',0),('s_x1',1),('s_x5',1),('s_2356',1),('s_2356',3),('s_2355',2),
           ('timer',0),('num32',0),('s_045',2),('s_16',1)],
 'face':[('paused',0),('paused',1),('paused',3),('paused',5),('quit',0),('resume',0),('resume',4),('level_tab',0),('level_tab',2),
         ('loading',6),('home',0),('s_beat',0),('LEVEL',2),('on_sound',0)],
}
out=sys.argv[1]; fams=[(x.rsplit(':',1)[0], int(x.rsplit(':',1)[1])) for x in sys.argv[2].split(',')]
GL=SETS[sys.argv[3] if len(sys.argv)>3 else 'plain']
def cut(img, b, pad=2):
    a0,a1,y0,y1=b; return img[:, max(a0-pad,0):a1+pad]
def label(k,i):
    t=[c for c in compare.M[k]['text'] if c!=' ']; return t[i] if i<len(t) else '?'
refrow={}
for j,(k,i) in enumerate(GL):
    rb=compare.blobs(compare.REF[k]); refrow[j]=cut(compare.REF[k], rb[i])
rows=[('REFERENCE',refrow)]
for fam,w in fams:
    c=[x for x in C if x['family']==fam][0]; _,f,ps,ax,opr=list(instances(c,5,[w]))[0]
    crops=sorted(set(k for k,_ in GL)); sz=compare.sizing(f,ps,ax,sorted(set(compare.SIZING[k][1] for k in crops)))
    jobs=[];
    for k in crops:
        j,s=compare.crop_job('g_'+k,f,ps,ax,k,sz); jobs.append(j)
    rr=compare.render(jobs,'gl'); cells={}
    for j,(k,i) in enumerate(GL):
        im=compare.reduce(rr['g_'+k][0],0,0); cb=compare.blobs(im)
        cells[j]=cut(im,cb[i]) if len(cb)==len(compare.blobs(compare.REF[k])) else None
    rows.append((f'{fam} {w}',cells))
colw=[max((r[1][i].shape[1] if r[1][i] is not None else 20) for r in rows)+10 for i in range(len(GL))]
Hc=max(max(r[1][i].shape[0] for r in rows if r[1][i] is not None) for i in range(len(GL)))+6
lab=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',16)
W=230+sum(colw); img=Image.new('RGB',(W,Hc*len(rows)+26),(255,255,255)); d=ImageDraw.Draw(img)
x=230
for i,(k,bi) in enumerate(GL): d.text((x+4,4),label(k,bi),fill=(150,0,0),font=lab); x+=colw[i]
for ri,(name,gs) in enumerate(rows):
    y=26+ri*Hc
    if ri%2==0: d.rectangle([0,y,W,y+Hc-1],fill=(244,244,250))
    d.text((4,y+Hc//2-8),name,fill=(0,0,0),font=lab); x=230
    for i in range(len(GL)):
        g=gs[i]
        if g is None: d.text((x+6,y+Hc//2-8),'-',fill=(120,120,120),font=lab)
        else:
            m=Image.fromarray((np.clip(g,0,1)*255).astype(np.uint8))
            img.paste(Image.new('RGB',m.size,(170,20,20) if ri==0 else (20,20,40)),(x+5,y+(Hc-g.shape[0])//2),m)
        x+=colw[i]
sc=float(os.environ.get('SCALE','1'))
if sc!=1: img=img.resize((int(img.width*sc),int(img.height*sc)),Image.LANCZOS)
img.save(out); print(out,img.size)
