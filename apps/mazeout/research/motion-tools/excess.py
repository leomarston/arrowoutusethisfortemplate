from evavg import *
def excess_table(S,sr,pre,t_from,t_to,step=0.02,nfft=1024,hop=120,base=(-0.22,-0.05)):
    f=np.fft.rfftfreq(nfft,1/sr)
    tt=np.arange(S.shape[1])*hop/sr-pre+nfft/2/sr
    bm=(tt>base[0])&(tt<base[1])
    B=S[:,bm].mean(1)
    bands=[(80,250),(250,600),(600,1200),(1200,2500),(2500,5000),(5000,10000)]
    rows=[]
    t=t_from
    while t<t_to:
        m=(tt>=t)&(tt<t+step)
        X=S[:,m].mean(1)-B
        Xs=X.copy(); Xs[f<100]=-99
        pk=[]
        for i in np.argsort(Xs)[::-1]:
            if Xs[i]<6: break
            if all(abs(f[i]-p)>60 for p in pk): pk.append(f[i])
            if len(pk)>=4: break
        bb=[]
        for lo,hi in bands:
            mm=(f>=lo)&(f<hi); bb.append(10*np.log10((10**(S[mm][:,m]/10)).mean())-10*np.log10((10**(B[mm]/10)).mean()))
        rows.append(f'{t:+.2f} bands(+dB 80-250/250-600/600-1.2k/1.2-2.5k/2.5-5k/5-10k): '+' '.join(f'{v:5.1f}' for v in bb)+'  peaks: '+' '.join(f'{p:.0f}' for p in pk))
        t+=step
    return rows
