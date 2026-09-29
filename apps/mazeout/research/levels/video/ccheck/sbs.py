# side-by-side: start frame | overlay, optional crop (x y w h in px), scale
import sys
from PIL import Image
R='/Users/yago/Downloads/app-factory/apps/mazeout/research/'
n=int(sys.argv[1]); out=sys.argv[2]
crop=None; scale=1.0
if len(sys.argv)>3: crop=tuple(int(v) for v in sys.argv[3:7])
if len(sys.argv)>7: scale=float(sys.argv[7])
a=Image.open(R+'video-frames/V2/L%03d-start.png'%n).convert('RGB')
ovp = sys.argv[8] if len(sys.argv)>8 else R+'video-frames/work/extract/V2-L%03d-overlay.png'%n
b=Image.open(ovp).convert('RGB')
if crop:
    x,y,w,h=crop; a=a.crop((x,y,x+w,y+h)); b=b.crop((x,y,x+w,y+h))
W,H=a.size
im=Image.new('RGB',(W*2+6,H),(255,255,255)); im.paste(a,(0,0)); im.paste(b,(W+6,0))
if scale!=1.0: im=im.resize((int(im.width*scale),int(im.height*scale)),Image.LANCZOS)
im.save(out)
print(im.size)
