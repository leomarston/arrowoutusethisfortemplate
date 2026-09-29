"""Maze Out reference crops -> sub-pixel ink maps (rewritten from apps/arrows crop_refs.py for outlined game text).

Two kinds of sample:
  plain  : one text colour on a background (possibly a gradient).  ink = projection of each pixel on the LOCAL
           background -> LOCAL text colour axis (local = colour of the nearest 'pure' pixel of that class, found with a
           distance transform, so gradients in either colour do not bias the edge).
  outl   : a light FACE inside a dark OUTLINE (plus drop shadow) on a background.  Every pixel is unmixed against the
           two segments that can occur at an anti-aliased edge: background<->outline and outline<->face (the face never
           touches the background).  face = coverage of the face colour, outer = coverage of face+outline+shadow.
Only connected ink components that do not touch the crop border and are at least 25 % of the tallest component's
height are kept (removes pill edges, icons), unless the spec lists keep='all'.
Writes crops/<name>.png (colour), <name>_ink.npy (face / text coverage 0..1), <name>_outer.npy (outl only),
<name>_ink.png, and crops/measure.json (box, colours, ink bbox)."""
import json, os, sys, numpy as np
from PIL import Image
from scipy import ndimage
HERE=os.path.dirname(os.path.abspath(__file__))
FC=os.path.dirname(HERE)+'/'
O=FC+'crops/'; os.makedirs(O,exist_ok=True)
RS='/Users/yago/Downloads/app-factory/apps/mazeout/research/'
PH=RS+'shots/'; ST=RS+'store/'
# name: (file, box x0,y0,x1,y1 in source px, text, mode)
S={
 # --- phone runner shots, 1178x2556, pt = px*393/1178 ---
 'haptic':     (PH+'007-L32-pause.png',(325,1205,595,1310),'Haptic','plain'),
 'sound':      (PH+'007-L32-pause.png',(335,985,590,1085),'Sound','plain'),
 'full':       (PH+'002-home-L32.png',(795,170,920,250),'Full','plain'),
 'coins_home': (PH+'002-home-L32.png',(425,170,580,250),'2240','plain'),
 'coins_hud':  (PH+'003-L32-start.png',(150,95,300,155),'2240','plain'),
 'paused':     (PH+'007-L32-pause.png',(320,610,860,770),'Paused','outl'),
 'on_sound':   (PH+'007-L32-pause.png',(645,995,775,1080),'ON','outl'),
 'on_haptic':  (PH+'007-L32-pause.png',(645,1216,775,1301),'ON','outl'),
 'resume':     (PH+'007-L32-pause.png',(205,1535,535,1650),'Resume','outl'),
 'quit':       (PH+'007-L32-pause.png',(695,1535,920,1650),'Quit','outl'),
 'level_tab':  (PH+'003-L32-start.png',(462,171,716,219),'Level 32','outl'),
 'timer':      (PH+'003-L32-start.png',(372,244,545,328),'3:00','outl',{'lum':1}),
 'play':       (PH+'002-home-L32.png',(425,1925,750,2115),'Play','outl'),
 'LEVEL':      (PH+'002-home-L32.png',(515,1561,660,1601),'LEVEL','outl'),
 'num32':      (PH+'002-home-L32.png',(520,1608,660,1710),'32','outl'),
 'home':       (PH+'002-home-L32.png',(510,2450,670,2520),'Home','outl'),
 'loading':    (RS+'kickoff/state.png',(395,2300,730,2410),'Loading','outl'),
 # --- store screenshots, 1320x2868 marketing composites (in-game renders inside) ---
 's_kate':     (ST+'iphone-6.png',(370,1750,570,1855),'Kate','plain'),
 's_max':      (ST+'iphone-6.png',(370,1990,545,2095),'Max','plain',{'bg':'border'}),
 's_james':    (ST+'iphone-6.png',(370,2228,630,2335),'James','plain',{'bg':'border'}),
 's_x1':       (ST+'iphone-6.png',(105,1385,240,1480),'x1','plain'),
 's_x5':       (ST+'iphone-6.png',(345,1385,480,1480),'x5','plain'),
 's_x25':      (ST+'iphone-6.png',(835,1385,1000,1480),'x25','plain'),
 's_x100':     (ST+'iphone-6.png',(1042,1385,1262,1480),'x100','plain'),
 's_2355':     (ST+'iphone-6.png',(620,1572,760,1642),'23:55','plain'),
 's_2356':     (ST+'iphone-7.png',(480,235,665,325),'2356','plain'),
 's_2346':     (ST+'iphone-7.png',(882,235,1085,325),'23:46','plain'),
 's_beat':     (ST+'iphone-6.png',(70,1232,1250,1312),'Beat levels without fail to get more rewards!','outl'),
 's_x10':      (ST+'iphone-6.png',(575,1368,750,1488),'x10','outl'),
 's_16':       (ST+'iphone-6.png',(1140,1755,1260,1850),'16','outl',{'lum':1}),
 's_hard':     (ST+'iphone-2.png',(530,172,795,248),'Hard Level','outl',{'lum':1}),
 's_045':      (ST+'iphone-2.png',(425,264,612,358),'0:45','outl',{'lum':1}),
 's_1000':     (ST+'iphone-7.png',(545,1805,775,1905),'1000','outl',{'lum':1}),
}
def lum(c): return c@np.array([0.299,0.587,0.114])
def nearest(mask):
    """indices of the nearest True pixel for every pixel"""
    _,(iy,ix)=ndimage.distance_transform_edt(~mask, return_indices=True); return iy,ix
def seg_fit(c, a, b):
    """fit c = a + t (b-a); returns t (clipped) and residual distance"""
    d=b-a; dd=(d*d).sum(-1)+1e-9; t=((c-a)*d).sum(-1)/dd; tc=np.clip(t,0,1)
    r=np.sqrt(((c-(a+tc[...,None]*d))**2).sum(-1)); return tc, r
def keep_components(ink, thr=0.5, minfrac=0.25):
    lab,n=ndimage.label(ink>thr); objs=ndimage.find_objects(lab); H,W=ink.shape
    hs=[(s[0].stop-s[0].start) for s in objs]; hmax=max(hs) if hs else 0
    keep=np.zeros(n+1,bool)
    for i,s in enumerate(objs):
        touches = s[0].start==0 or s[1].start==0 or s[0].stop==H or s[1].stop==W
        if not touches and hs[i]>=minfrac*hmax: keep[i+1]=True
        # dots (i, j, :) are small: keep if they sit above/inside a kept blob's column range (handled below)
    km=keep[lab]
    # re-admit small components (dots, colons) lying within the vertical band of kept ink and not touching the border
    if km.any():
        ys=np.where(km.any(1))[0]; y0,y1=ys[0],ys[-1]
        for i,s in enumerate(objs):
            touches = s[0].start==0 or s[1].start==0 or s[0].stop==H or s[1].stop==W
            if not keep[i+1] and not touches and s[0].start>=y0-0.35*(y1-y0) and s[0].stop<=y1+2: keep[i+1]=True
    km=keep[lab]
    # drop components whose vertical centre lies outside the band of the tallest component (stray button edges)
    big=[objs[i] for i in range(n) if keep[i+1] and hs[i]>=0.5*hmax]
    if big:
        b0=min(s[0].start for s in big); b1=max(s[0].stop for s in big)
        for i,s in enumerate(objs):
            cy=(s[0].start+s[0].stop)/2
            if keep[i+1] and not (b0<=cy<=b1): keep[i+1]=False
        km=keep[lab]
    grow=ndimage.binary_dilation(km, iterations=3)   # keep the anti-aliased fringe
    return grow
def plain(c, bgmode='mode'):
    if bgmode=='border': bg=np.median(np.concatenate([c[0],c[-1],c[:,0],c[:,-1]]),0)
    else:
        q=(c//8).astype(int); key=q[...,0]*1024+q[...,1]*32+q[...,2]
        mode_key=np.bincount(key.ravel()).argmax(); bg=np.median(c[key==mode_key],0)   # most common colour = background
    d=np.sqrt(((c-bg)**2).sum(-1)); fg=np.median(c[d>0.85*d.max()],0); span=np.sqrt(((fg-bg)**2).sum())
    t0,_=seg_fit(c,bg,fg)
    pf=t0>0.9; pb=t0<0.08
    fy,fx=nearest(pf); by,bx=nearest(pb)
    lf=c[fy,fx]; lb=c[by,bx]
    ink,_=seg_fit(c,lb,lf)
    return ink, None, dict(bg=bg, fg=fg)
def outl_lum(c):
    """face by luminance only (for faces whose colour is close to the background, e.g. the HUD timer):
    inside a 2-px band around the face core only face and outline colours occur (the outline is >= 3 px wide)."""
    L=lum(c); border=np.concatenate([c[0],c[-1],c[:,0],c[:,-1]]); bg=np.median(border,0)
    Lf=np.percentile(L,99); Lo=np.percentile(L,1)
    core=L>(Lf+Lo)/2
    lab,n=ndimage.label(core); objs=ndimage.find_objects(lab); H,W=L.shape
    keep=np.zeros(n+1,bool)
    for i,sl in enumerate(objs):
        if not (sl[0].start==0 or sl[1].start==0 or sl[0].stop==H or sl[1].stop==W): keep[i+1]=True
    core=keep[lab]
    R=ndimage.binary_dilation(core, iterations=2)
    fc=np.median(c[L>=Lf-3],0); oc=np.median(c[L<=Lo+3],0)
    pF=core & (L>Lf-0.25*(Lf-Lo)); fy,fx=nearest(pF); lF=c[fy,fx]      # local face colour (vertical gradient)
    t,r=seg_fit(c,oc,lF)
    face=t*R*((r<22)|(t>0.95))     # pixels off the outline->face segment (background seen in small counters) are not face
    return face, None, dict(bg=bg, face=fc, outline=oc)
def outl(c):
    border=np.concatenate([c[0],c[-1],c[:,0],c[:,-1]]); bg=np.median(border,0)
    d=np.sqrt(((c-bg)**2).sum(-1)); textish=d>0.2*d.max()
    L=lum(c)
    lt=L[textish]
    face=np.median(c[textish & (L>=np.percentile(lt,85))],0)
    out=np.median(c[textish & (L<=np.percentile(lt,10))],0)
    # pure classes (loose thresholds so gradients stay 'pure')
    sp_fo=np.sqrt(((face-out)**2).sum()); sp_bo=np.sqrt(((bg-out)**2).sum())
    df=np.sqrt(((c-face)**2).sum(-1)); do=np.sqrt(((c-out)**2).sum(-1)); db=d
    pF=df<0.25*sp_fo; pO=(do<0.25*min(sp_fo,sp_bo)); pB=db<0.25*sp_bo
    fy,fx=nearest(pF); oy,ox=nearest(pO); by,bx=nearest(pB)
    lF=c[fy,fx]; lO=c[oy,ox]; lB=c[by,bx]
    t1,r1=seg_fit(c,lB,lO)     # background -> outline
    t2,r2=seg_fit(c,lO,lF)     # outline -> face
    # the face never touches the background: a pixel is on the outline/face segment only if it is inside the outer region
    use2=(r2<r1)
    outer=np.where(use2,1.0,t1); facec=np.where(use2,t2,0.0)
    # the outline/face fit may also claim bg pixels whose colour happens to lie on that segment: require an outline neighbour
    outer_core=ndimage.binary_dilation(outer>0.5, iterations=1)
    facec=facec*ndimage.binary_erosion(outer>0.5, iterations=1)
    return facec, outer, dict(bg=bg, face=face, outline=out)
if __name__=='__main__':
    only=sys.argv[1:] or list(S)
    meas=json.load(open(O+'measure.json')) if os.path.exists(O+'measure.json') else {}
    for name in only:
        f,box,text,mode=S[name][:4]; opt=S[name][4] if len(S[name])>4 else {}
        im=np.asarray(Image.open(f).convert('RGB')).astype(float)
        x0,y0,x1,y1=box; c=im[y0:y1,x0:x1]
        ink,outer,cols=plain(c, opt.get('bg','mode')) if mode=='plain' else (outl_lum(c) if opt.get('lum') else outl(c))
        km=keep_components(ink)          # the face never touches the crop border (the outline may: pill edges)
        ink=ink*km
        if outer is not None: outer=outer*ndimage.binary_dilation(km, iterations=14)
        m=(outer if outer is not None else ink)>0.5
        if not m.any(): print('NO INK KEPT', name); continue
        ys,xs=np.where(m); ty0,ty1,tx0,tx1=ys.min(),ys.max(),xs.min(),xs.max()
        p=6
        cy0,cy1,cx0,cx1=max(ty0-p,0),min(ty1+p+1,c.shape[0]),max(tx0-p,0),min(tx1+p+1,c.shape[1])
        fi=np.where(ink>0.5);
        meas[name]=dict(file=os.path.relpath(f,RS),box=list(box),text=text,mode=mode,
            colours={k:'#%02X%02X%02X'%tuple(int(round(v)) for v in val) for k,val in cols.items()},
            crop_origin_px=[int(x0+cx0),int(y0+cy0)],
            face_bbox_px=[int(x0+fi[1].min()),int(y0+fi[0].min()),int(x0+fi[1].max()),int(y0+fi[0].max())],
            outer_bbox_px=[int(x0+tx0),int(y0+ty0),int(x0+tx1),int(y0+ty1)])
        sl=(slice(cy0,cy1),slice(cx0,cx1))
        Image.fromarray(c[sl].astype(np.uint8)).save(O+name+'.png')
        np.save(O+name+'_ink.npy',ink[sl]); Image.fromarray((ink[sl]*255).astype(np.uint8)).save(O+name+'_ink.png')
        if outer is not None:
            np.save(O+name+'_outer.npy',outer[sl]); Image.fromarray((outer[sl]*255).astype(np.uint8)).save(O+name+'_outer.png')
        print(name, meas[name]['colours'], 'crop', c[sl].shape[:2])
    json.dump(meas,open(O+'measure.json','w'),indent=1)
