"""Fit the level-intro HUD slide-in (S1-L32-intro): pause-button top y (top HUD) and left-booster left x (bottom boosters).
Models: (a) easeOutBack over T with overshoot s; (b) damped spring from rest. Start position, t0 free; end fixed."""
import numpy as np
from scipy.optimize import least_squares
hud=[(0.266,2.0),(0.283,26.5),(0.316,64.5),(0.333,79.5),(0.349,89.5),(0.399,97.5),(0.416,105.5),(0.433,104.5),(0.483,88.5),(0.499,81.5),(0.532,68.0),(0.566,67.5),(0.599,67.5)]
boo=[(0.333,-39.0),(0.349,-15.5),(0.399,6.5),(0.416,37.0),(0.433,36.5),(0.483,26.0),(0.499,22.0),(0.532,18.5),(0.566,18.5)]
def eob(u,s):
    u=np.clip(u,0,1); u=u-1; return 1+(s+1)*u**3+s*u**2
def spring(tau,z,w):
    tau=np.maximum(tau,0); wd=w*np.sqrt(max(1-z*z,1e-6))
    return 1-np.exp(-z*w*tau)*(np.cos(wd*tau)+z*w/wd*np.sin(wd*tau))
def res(p,model,data,end):
    y0,t0=p[0],p[1]
    t=np.array([a for a,b in data]); y=np.array([b for a,b in data])
    if model=='eob': T,s=p[2],p[3]; f=eob((t-t0)/T,s)
    else: z,w=p[2],p[3]; f=spring(t-t0,z,w)
    return y0+(end-y0)*f-y
for name,data,end,y0g in (('top HUD (pause-button top y, pt)',hud,67.5,-40.0),('left booster (left edge x, pt)',boo,18.5,-60.0)):
    for model,g,lb,ub in (('eob',[0.3,2.0],[0.05,0],[1.5,20]),('spring',[0.5,20],[0.05,2],[0.99,80])):
        r=least_squares(res,[y0g,0.24]+g,bounds=([-400,0.0]+lb,[end-1,0.4]+ub),args=(model,data,end))
        rr=res(r.x,model,data,end)
        extra=''
        if model=='spring':
            z,w=r.x[2],r.x[3]; extra=f'  -> SwiftUI .spring(response {2*np.pi/w:.3f}, dampingFraction {z:.2f})'
        print(f"{name:36s} {model:6s} start {r.x[0]:7.1f} t0 {r.x[1]:.3f} p3 {r.x[2]:.3f} p4 {r.x[3]:.3f}  RMS {np.sqrt((rr**2).mean()):.1f} pt max {abs(rr).max():.1f}{extra}")
