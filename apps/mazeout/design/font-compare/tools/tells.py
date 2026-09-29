"""Quick visual filter: render a 'tells' string in every candidate (CoreText via ctrender) at one cap height,
at the heaviest weight (or the weights given), one row per family, with the reference crops on top.
usage: tells.py OUT.png [TEXT] [families-comma|all] [weight-override-json]"""
import json, os, sys, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from candidates import C, instances, heaviest, WORK
REN=WORK+'ctrender'; SS=2
out=sys.argv[1]
text=sys.argv[2] if len(sys.argv)>2 else 'Haptic 3:00 2240 Quit Play Loading 9h 42m Paused'
fams=None if len(sys.argv)<=3 or sys.argv[3]=='all' else sys.argv[3].split(',')
ovr=json.loads(sys.argv[4]) if len(sys.argv)>4 else {}
CAP=44; H=int(CAP*1.9); BASE=int(CAP*1.35)
jobs=[]; names=[]
for c in C:
    if fams and c['family'] not in fams: continue
    w=ovr.get(c['family'], heaviest(c))
    _,f,ps,ax,opr=list(instances(c,5,[w]))[0]
    jid='t%02d'%len(jobs)
    jobs.append(dict(id=jid,font=f,ps=ps,axes=ax,cap=CAP*SS,text=text,H=H*SS,base=BASE*SS,x=8*SS)); names.append(f"{c['family']} {w}")
tmp=WORK+'renders/'; os.makedirs(tmp,exist_ok=True); json.dump(jobs,open(tmp+'tells.json','w'))
o=subprocess.run([REN,tmp+'tells.json',tmp],capture_output=True,text=True)
rows=[]
for line in o.stdout.splitlines():
    m=json.loads(line); r=np.fromfile(tmp+m['id']+'.raw',dtype=np.uint8).reshape(m['H'],m['W']).astype(float)/255
    os.remove(tmp+m['id']+'.raw')
    r=r.reshape(H,SS,-1,SS).mean((1,3)) if r.shape[1]%SS==0 else r[:, :r.shape[1]//SS*SS].reshape(H,SS,-1,SS).mean((1,3))
    rows.append(r)
lab=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',16)
refs=[p for p in (os.environ.get('REFS','').split(',')) if p]
refims=[Image.open(p).convert('RGB') for p in refs]
refims=[im.resize((int(im.width*H/im.height),H)) for im in refims]
W=240+max([r.shape[1] for r in rows]+[sum(im.width+10 for im in refims)])
img=Image.new('RGB',(W,(len(rows)+ (1 if refims else 0))*H+10),(255,255,255)); d=ImageDraw.Draw(img); y=0
if refims:
    x=240; d.text((4,H//2-8),'REFERENCE crops',fill=(160,0,0),font=lab)
    for im in refims: img.paste(im,(x,0)); x+=im.width+10
    y=H
for n,r in zip(names,rows):
    if (y//H)%2==0: d.rectangle([0,y,W,y+H-1],fill=(245,245,250))
    d.text((4,y+H//2-8),n,fill=(0,0,0),font=lab)
    tile=Image.fromarray((255*(1-r)).astype(np.uint8)).convert('L')
    img.paste(Image.new('RGB',tile.size,(30,20,10)),(240,y),Image.fromarray((255*r).astype(np.uint8)))
    y+=H
img.save(out); print(out,img.size)
