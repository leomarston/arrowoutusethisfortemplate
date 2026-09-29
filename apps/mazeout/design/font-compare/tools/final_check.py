"""Final check of the SHIPPED font file at the spec (point size + tracking per crop from results/final_spec_fit.json):
renders design/fonts/PCDisplay-Black.ttf at exactly that size (pt -> px of the reference shot) and tracking, puts the
baseline where the crop's sizing glyph sits, scores line IoU / ink / width, and writes a sheet
reference | shipped font | overlay (red = reference only, blue = font only, dark = both).
usage: final_check.py OUT.png [crops|plain|face]"""
import json, os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import compare, fine
SS=compare.SS; FC=compare.FC
FONT=FC.rstrip('/').rsplit('/',1)[0]+'/fonts/PCDisplay-Black.ttf'   # design/fonts/
spec=json.load(open(FC+'results/final_spec_fit.json'))
out=sys.argv[1]
crops=sum([compare.GROUPS[x] if x in compare.GROUPS else [x] for x in (sys.argv[2] if len(sys.argv)>2 else 'plain,face').split(',')],[])
# size of the font when the sizing glyph is rendered at CAP0 (ctrender sizes by 'H'): measure once per char
chars=sorted(set(compare.SIZING[k][1] for k in crops))
sz=compare.sizing(FONT,None,None,chars)
probe=compare.render([dict(id='p',font=FONT,ps=None,axes=None,cap=compare.CAP0*SS,text='H',H=400,base=300,x=10)],'p')['p'][1]
size0=probe['size']          # render-px font size at cap=CAP0*SS
rows=[]; report=json.load(open(FC+'results/final_check.json')) if os.path.exists(FC+'results/final_check.json') else {}
for k in crops:
    sp=spec[k]; ppt=fine.px_per_pt(k)
    size_px=sp['size_pt']*ppt*SS; s=size_px/size0; ch=compare.SIZING[k][1]; g=compare.REFG[k]
    job=dict(id='fc_'+k,font=FONT,ps=None,axes=None,cap=compare.CAP0*SS*s,text=compare.M[k]['text'],H=compare.REF[k].shape[0]*SS,
             base=g['bottom']*SS-sz[ch]['off']*s,x=6*SS,track=sp['track_pt']*ppt*SS)
    r,m=compare.render([job],'fc')['fc_'+k]
    sc,B=compare.score(compare.REF[k],r)
    report[k]=dict(size_pt=sp['size_pt'],track_pt=sp['track_pt'],ps=m['ps'],line_iou=sc['iou'],ink=sc['mass'],width=sc['wratio'])
    print(f"{k:11s} {sp['size_pt']:6.2f}pt trk {sp['track_pt']:+.2f}  IoU {sc['iou']:.3f} ink x{sc['mass']:.2f} width x{sc['wratio']:.3f}  ({m['ps']})", flush=True)
    rows.append((k,sp,compare.REF[k],B,sc))
print('mean line IoU (this run)', round(float(np.mean([report[k]['line_iou'] for k in crops])),4), '| all crops in file', round(float(np.mean([v['line_iou'] for v in report.values()])),4), len(report))
json.dump(report,open(FC+'results/final_check.json','w'),indent=1)
lab=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',16)
tiles=[]
for k,sp,ref,B,sc in rows:
    h=ref.shape[0]; W=max(ref.shape[1],B.shape[1])
    R=np.zeros((h,W)); R[:,:ref.shape[1]]=ref; Bp=np.zeros((h,W)); Bp[:,:min(W,B.shape[1])]=B[:h,:W]
    ink=lambda a: Image.fromarray((255*(1-a)).astype(np.uint8)).convert('RGB')
    rgb=np.ones((h,W,3))*255; rgb[...,0]-=255*Bp; rgb[...,1]-=255*np.maximum(R,Bp)*0.85; rgb[...,2]-=255*R
    t=Image.new('RGB',(3*W+60,h+26),(255,255,255)); d=ImageDraw.Draw(t)
    d.text((4,2),f"{k}: {sp['size_pt']:.2f} pt, tracking {sp['track_pt']:+.2f} pt   line IoU {sc['iou']:.3f}  ink x{sc['mass']:.2f}  width x{sc['wratio']:.3f}",fill=(0,0,0),font=lab)
    t.paste(ink(R),(0,24)); t.paste(ink(Bp),(W+30,24)); t.paste(Image.fromarray(np.clip(rgb,0,255).astype(np.uint8)),(2*W+60,24)); tiles.append(t)
Wt=max(t.width for t in tiles); Ht=sum(t.height+6 for t in tiles)+30
S=Image.new('RGB',(Wt,Ht),(255,255,255)); d=ImageDraw.Draw(S)
d.text((4,6),"reference | PCDisplay-Black (shipped file) | overlay: red = reference only, blue = font only, dark = both",fill=(120,0,0),font=lab); y=30
for t in tiles: S.paste(t,(0,y)); y+=t.height+6
sc=float(os.environ.get('SCALE','1'))
if sc!=1: S=S.resize((int(S.width*sc),int(S.height*sc)),Image.LANCZOS)
S.save(out); print(out,S.size)
