# raw frame crop with cell centre dots + labels (normalized coords): grid.py N x y w h scale out [json]
import sys, json
from PIL import Image, ImageDraw
n=int(sys.argv[1]); x,y,w,h=[int(v) for v in sys.argv[2:6]]; sc=float(sys.argv[6]); out=sys.argv[7]
jp=sys.argv[8] if len(sys.argv)>8 else '/Users/yago/Downloads/app-factory/apps/mazeout/research/video-frames/work/levelsC/V2-L%03d.json'%n
js=json.load(open(jp)); fp=js['fit_px']; p=fp['pitch']
fr = sys.argv[9] if len(sys.argv)>9 else '/Users/yago/Downloads/app-factory/apps/mazeout/'+js['frame']
im=Image.open(fr).convert('RGB').crop((x,y,x+w,y+h))
im=im.resize((int(w*sc),int(h*sc)),Image.LANCZOS); dr=ImageDraw.Draw(im)
for c in range(-2, js['cols']+2):
  for r in range(-2, js['rows']+2):
    px=fp['x0']+(c+fp['c0'])*p; py=fp['y0']+(r+fp['r0'])*p
    if x<=px<x+w and y<=py<y+h:
      X=(px-x)*sc; Y=(py-y)*sc
      dr.ellipse([X-2,Y-2,X+2,Y+2],fill=(255,0,0))
      if r%1==0: dr.text((X+3,Y+2),'%d,%d'%(c,r),fill=(200,0,0))
im.save(out); print(im.size)
