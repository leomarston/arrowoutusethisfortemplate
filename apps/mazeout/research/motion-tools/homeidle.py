"""Home idle: per real frame, Play-button green bbox, left/right worker yellow bbox, monster purple bbox (F01 clip)."""
from mf import *
from scipy import ndimage
t,px=raw('F01-notif-dismiss.mov',0,8,393)
S=1.0
def bbox(m):
    ys,xs=np.where(m)
    return (xs.min(),ys.min(),xs.max(),ys.max(),len(ys)) if len(ys) else None
for i in range(len(t)):
    f=px[i].astype(int); R,G,B=f[...,0],f[...,1],f[...,2]
    green=(G>180)&(R<120)&(B<110)
    play=green[630:710,90:300]; pb=bbox(play)
    yellow=(R>220)&(G>150)&(G<215)&(B<90)
    lw=yellow[480:640,0:120]; rw=yellow[480:640,270:393]
    purple=(R>120)&(R<200)&(B>190)&(G<120)
    mon=purple[150:420,110:290]
    lb=bbox(lw); rb=bbox(rw); mb=bbox(mon)
    print(f"{t[i]:.3f} play {pb and (pb[0]+90,pb[1]+630,pb[2]+90,pb[3]+630)} w={pb and pb[2]-pb[0]} | Lw {lb and (lb[0],lb[1]+480,lb[2],lb[3]+480,lb[4])} | Rw {rb and (rb[0]+270,rb[1]+480,rb[2]+270,rb[3]+480,rb[4])} | mon {mb and (mb[0]+110,mb[1]+150,mb[2]+110,mb[3]+150,mb[4])}")
