"""Level-intro HUD per frame for any clip: hud_intro2.py CLIP T0 T1 (pause-button top y, boosters x, hearts)."""
from mf import *
from scipy import ndimage
import sys
t,px=raw(sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),786)
S=2
for i in range(len(t)):
    f=px[i].astype(int); R,G,B=f[...,0],f[...,1],f[...,2]
    blue=(B>200)&(R<60)&(G>80)&(G<170)
    top=blue[:150*S, 336*S:370*S]; ys=np.where(top.any(1))[0]
    pause=(ys.min()/S, ys.max()/S) if len(ys) else None
    green=(G>170)&(R<120)&(B<120)
    band=green[750*S:830*S]
    xs=np.where(band.any(0))[0]/S
    left=[x for x in xs if x<196]; right=[x for x in xs if x>=196]
    bl=(min(left),max(left)) if left else None; br=(min(right),max(right)) if right else None
    # timer digits: white text pixels inside the pill area, x 60..240, y 45..140, excluding the Level tab (y<82 and x 150..240 area is tab)
    white=(R>235)&(G>235)&(B>235)
    reg=white[45*S:140*S, 60*S:250*S].copy()
    lab,n=ndimage.label(reg)
    boxes=[]
    for k in range(1,n+1):
        yy,xx=np.where(lab==k)
        if len(yy)<12: continue
        boxes.append((xx.min()/S+60,yy.min()/S+45,xx.max()/S+60,yy.max()/S+45,len(yy)))
    # keep glyph-like blobs below the tab text (tab text is ~y 73..81)
    dig=[b for b in boxes if b[3]>84]
    db=(min(b[0] for b in dig),min(b[1] for b in dig),max(b[2] for b in dig),max(b[3] for b in dig)) if dig else None
    red=(R>200)&(G<80)&(B<80)
    lab,n=ndimage.label(red[40*S:170*S,140*S:320*S]); hs=[]
    for k in range(1,n+1):
        yy,xx=np.where(lab==k)
        if len(yy)<30: continue
        hs.append((round(xx.mean()/S+140),round((xx.max()-xx.min()+1)/S,1)))
    hs.sort()
    print(f"{t[i]:.3f} pauseY {pause} boostL x {bl} boostR x {br} timerTxt {db} hearts {hs}")
