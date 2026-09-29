import sys
from mf import *
def spec(name,s,e,marks,out,fmax=10000,pxs=500,H=360,logf=True):
    sr,x,_=audio(name)
    seg=x[int(s*sr):int(e*sr)]
    nfft=2048; hop=int(sr/pxs)
    win=np.hanning(nfft)
    n=(len(seg)-nfft)//hop
    S=np.stack([np.abs(np.fft.rfft(seg[i*hop:i*hop+nfft]*win)) for i in range(n)],1)
    f=np.fft.rfftfreq(nfft,1/sr)
    S=20*np.log10(S+1e-7)
    # log frequency axis 80..fmax
    fl=np.geomspace(80,fmax,H) if logf else np.linspace(0,fmax,H)
    idx=np.searchsorted(f,fl)
    img=S[idx][::-1]
    img=np.clip((img-(img.max()-75))/75,0,1)
    im=Image.fromarray((255*(1-img)).astype(np.uint8)).convert('RGB')
    d=ImageDraw.Draw(im)
    for tm,lab in marks:
        xx=int((tm-s)*pxs)
        d.line([(xx,0),(xx,H)],fill=(255,0,0)); d.text((xx+2,2),lab,fill=(255,0,0))
    for k in range(int(s*10)+1,int(e*10)+1):
        xx=int((k/10-s)*pxs); d.line([(xx,H-8),(xx,H)],fill=(0,0,255))
        if k%5==0: d.text((xx+1,H-20),f'{k/10:.1f}',fill=(0,0,255))
    for fr in (200,500,1000,2000,5000):
        yy=H-1-int(np.searchsorted(fl,fr)); d.line([(0,yy),(12,yy)],fill=(0,160,0)); d.text((14,yy-6),str(fr),fill=(0,160,0))
    # envelope strip
    tt,ee=envelope(seg,sr,5)
    E=Image.new('RGB',(im.width,80),'white'); de=ImageDraw.Draw(E)
    pts=[(int(t_*pxs),int(80-(max(v,-60)+60)/60*78)) for t_,v in zip(tt,ee)]
    de.line(pts,fill=(0,0,0))
    for tm,lab in marks:
        xx=int((tm-s)*pxs); de.line([(xx,0),(xx,80)],fill=(255,0,0))
    C=Image.new('RGB',(im.width,H+80),'white'); C.paste(im,(0,0)); C.paste(E,(0,H)); C.save(out)
    print(out,C.size)
if __name__=='__main__':
    pass
