"""Contact sheet of the reference crops: colour crop | face/text ink | outer ink (outlined samples), each x2.
usage: contact.py OUT.png [names...]"""
import json, os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); O=os.path.dirname(HERE)+'/crops/'
M=json.load(open(O+'measure.json'))
names=sys.argv[2:] or list(M)
lab=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',16)
rows=[]
for n in names:
    if n not in M: continue
    ims=[Image.open(O+n+'.png').convert('RGB')]
    for suf in ('_ink.png','_outer.png'):
        if os.path.exists(O+n+suf): ims.append(Image.open(O+n+suf).convert('RGB').point(lambda v:255-v))
    ims=[i.resize((i.width*2,i.height*2),Image.NEAREST) for i in ims]
    W=sum(i.width+8 for i in ims)+200; H=max(i.height for i in ims)+6
    r=Image.new('RGB',(W,H),(255,255,255)); d=ImageDraw.Draw(r); d.text((4,4),n,fill=(150,0,0),font=lab)
    d.text((4,24),M[n]['mode'],fill=(90,90,90),font=lab); x=200
    for i in ims: r.paste(i,(x,3)); x+=i.width+8
    rows.append(r)
W=max(r.width for r in rows); H=sum(r.height+4 for r in rows)
S=Image.new('RGB',(W,H),(200,200,200)); y=0
for r in rows: S.paste(r,(0,y)); y+=r.height+4
S.save(sys.argv[1]); print(sys.argv[1],S.size)
