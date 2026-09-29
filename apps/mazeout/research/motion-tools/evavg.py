from mf import *
import os
from spec import *
def stft(seg,sr,nfft=1024,hop=120):
    win=np.hanning(nfft); n=(len(seg)-nfft)//hop
    return np.stack([np.abs(np.fft.rfft(seg[i*hop:i*hop+nfft]*win)) for i in range(n)],1)
_cache={}
def getaudio(fn):
    if fn not in _cache:
        sr,x,p=audio(fn); os.remove(p); _cache[fn]=(sr,x)
    return _cache[fn]
def evspec(events,pre=0.25,post=0.9,nfft=1024,hop=120):
    Ss=[]
    for fn,t0 in events:
        sr,x=getaudio(fn)
        a=int((t0-pre)*sr); b=int((t0+post)*sr)
        if a<0 or b>len(x): continue
        Ss.append(20*np.log10(stft(x[a:b],sr,nfft,hop)+1e-7))
    S=np.stack(Ss)
    return sr,np.median(S,0),np.percentile(S,25,0),len(Ss)
def render(sr,S,pre,out,title,nfft=1024,hop=120,H=300,fmax=12000,marks=()):
    f=np.fft.rfftfreq(nfft,1/sr)
    fl=np.geomspace(100,fmax,H); idx=np.searchsorted(f,fl)
    img=S[idx][::-1]; img=np.clip((img-(img.max()-60))/60,0,1)
    px_per_col=3
    im=Image.fromarray((255*(1-img)).astype(np.uint8)).resize((img.shape[1]*px_per_col,H)).convert('RGB')
    d=ImageDraw.Draw(im)
    cps=sr/hop*px_per_col
    for k in range(-2,10):
        xx=int((k/10+pre)*cps); d.line([(xx,H-10),(xx,H)],fill=(0,0,255)); d.text((xx+1,H-22),f'{k/10:+.1f}',fill=(0,0,255))
    xx=int(pre*cps); d.line([(xx,0),(xx,H)],fill=(255,0,0))
    for tm,lab in marks:
        xx=int((tm+pre)*cps); d.line([(xx,0),(xx,H)],fill=(255,120,0)); d.text((xx+2,12),lab,fill=(255,120,0))
    for fr in (200,500,1000,2000,4000,8000):
        yy=H-1-int(np.searchsorted(fl,fr)); d.line([(0,yy),(10,yy)],fill=(0,150,0)); d.text((12,yy-6),str(fr),fill=(0,150,0))
    d.text((60,2),title,fill=(200,0,0))
    im.save(out); return im.size
def band_env(S,sr,nfft,lo,hi):
    f=np.fft.rfftfreq(nfft,1/sr); m=(f>=lo)&(f<hi)
    return 10*np.log10((10**(S[m]/10)).mean(0))
