"""Side-by-side sheet: for each crop the reference ink, then each candidate (given weight, sized on the crop's sizing
glyph, best 1/4-px alignment) with a red/blue overlay (red = reference only, blue = candidate only, dark = both).
usage: sheet.py OUT.png "Fam1:w,Fam2:w,..." crop1,crop2,...|plain|face"""
import json, sys, os, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import compare
from candidates import C, instances
SP=compare.SP; SS=compare.SS
out=sys.argv[1]
fams=[(x.rsplit(':',1)[0], int(x.rsplit(':',1)[1])) for x in sys.argv[2].split(',')]
crops=sum([compare.GROUPS[x] if x in compare.GROUPS else [x] for x in sys.argv[3].split(',')],[])
lab=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18)
def cand(fam,w,k):
    c=[x for x in C if x['family']==fam][0]; _,f,ps,ax,opr=list(instances(c,5,[w]))[0]
    sz=compare.sizing(f,ps,ax,[compare.SIZING[k][1]])
    j,s=compare.crop_job('sh',f,ps,ax,k,sz); r,m=compare.render([j],'sh')['sh']
    sc,B=compare.score2(compare.REF[k],r); return sc,B
blocks=[]
for k in crops:
    ref=compare.REF[k]; h=ref.shape[0]
    rows=[('REFERENCE  '+k,ref,None)]
    for fam,w in fams:
        sc,B=cand(fam,w,k); rows.append((f"{fam} {w}  IoU {sc['iou']:.3f} wfit {sc['iou_wfit']:.3f} ink x{sc['mass']:.2f} width x{sc['wratio']:.3f}",B,sc))
    Wimg=max(r[1].shape[1] for r in rows)
    ims=[]
    for name,B,sc in rows:
        Bp=np.zeros((h,Wimg)); Bp[:,:min(Wimg,B.shape[1])]=B[:h,:Wimg]; Rp=np.zeros((h,Wimg)); Rp[:,:ref.shape[1]]=ref
        g=Image.fromarray((255*(1-Bp)).astype(np.uint8)).convert('RGB')
        rgb=np.ones(Bp.shape+(3,))*255; rgb[...,0]-=255*Bp; rgb[...,1]-=255*np.maximum(Rp,Bp)*0.85; rgb[...,2]-=255*Rp
        o=Image.fromarray(np.clip(rgb,0,255).astype(np.uint8))
        cv=Image.new('RGB',(2*Wimg+30, h+28),(255,255,255)); d=ImageDraw.Draw(cv); d.text((6,3),name,fill=(0,0,0),font=lab)
        cv.paste(g,(5,26)); cv.paste(o,(Wimg+25,26)); ims.append(cv)
    Wb=max(i.width for i in ims); Hb=sum(i.height for i in ims)+8
    b=Image.new('RGB',(Wb,Hb),(235,235,235)); y=0
    for i in ims: b.paste(i,(0,y)); y+=i.height
    blocks.append(b)
W=max(b.width for b in blocks); H=sum(b.height+10 for b in blocks)
S=Image.new('RGB',(W,H),(190,190,190)); y=0
for b in blocks: S.paste(b,(0,y)); y+=b.height+10
sc=float(os.environ.get('SCALE','1'))
if sc!=1: S=S.resize((int(S.width*sc),int(S.height*sc)),Image.LANCZOS)
S.save(out); print(out,S.size)
