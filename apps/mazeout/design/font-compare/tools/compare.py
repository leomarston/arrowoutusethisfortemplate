"""Score candidates against the reference crops (adapted from apps/arrows compare.py, commit 8e77f85).

Sizing: every crop names one isolated reference glyph (blob index + character).  Its height and bottom edge are measured
in the reference ink with the ink-sum edge estimator (exact for flat edges); the candidate renders that character alone,
is measured with the SAME estimator, and is then scaled / placed so the glyph matches.  This makes the comparison
independent of each font's cap-height / overshoot conventions (a round '3' or 'S' is compared like with like).
Rendering: CoreText (ctrender, same engine as iOS), 4x supersampled, box-downsampled.
Scores: soft line IoU = sum(min)/sum(max) with a 1/4-px x/y alignment search; width-fit IoU (render stretched to the
reference ink width: pure shape); ink-mass ratio (weight proxy) and ink-width ratio (proportion/spacing proxy).
usage: compare.py OUT.json [--step N] [--families a,b] [--weights 500,550] [--crops c1,c2] [--keep]"""
import json, os, subprocess, sys, argparse, numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
from candidates import C, instances, WORK
FC=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
SP=WORK; REN=SP+'ctrender'; SS=4
M=json.load(open(FC+'crops/measure.json'))
# crop -> (sizing blob index, its character)
SIZING={
 'haptic':(0,'H'),'sound':(4,'d'),'full':(0,'F'),'coins_home':(2,'4'),'coins_hud':(2,'4'),
 's_kate':(0,'K'),'s_max':(0,'M'),'s_james':(0,'J'),'s_x1':(1,'1'),'s_x5':(1,'5'),'s_x25':(1,'2'),'s_x100':(1,'1'),
 's_2355':(0,'2'),'s_2356':(0,'2'),'s_2346':(3,'4'),
 'paused':(0,'P'),'on_sound':(1,'N'),'on_haptic':(1,'N'),'resume':(0,'R'),'quit':(3,'t'),'level_tab':(0,'L'),
 'timer':(0,'3'),'play':(0,'P'),'LEVEL':(0,'L'),'num32':(0,'3'),'home':(0,'H'),'loading':(0,'L'),
 's_beat':(0,'B'),'s_x10':(1,'0'),'s_16':(0,'1'),'s_hard':(0,'H'),'s_045':(2,'4'),'s_1000':(0,'1'),
}
GROUPS={
 'plain':['haptic','sound','full','coins_home','coins_hud','s_kate','s_max','s_james','s_x1','s_x5','s_x25','s_x100','s_2355','s_2356','s_2346'],
 'face':['paused','on_sound','on_haptic','resume','quit','level_tab','timer','play','LEVEL','num32','home','loading','s_beat','s_x10','s_16','s_hard','s_045','s_1000'],
}
GROUP_OF={c:g for g,cs in GROUPS.items() for c in cs}
def blobs(img, thr=0.5):
    """glyph blobs: connected components, with dots/accents merged into the blob they overlap horizontally"""
    lab,n=ndimage.label(img>thr); objs=ndimage.find_objects(lab)
    area=ndimage.sum(np.ones_like(img), lab, range(1,n+1))
    bx=sorted([[s[1].start,s[1].stop,s[0].start,s[0].stop] for s,a in zip(objs,area) if a>=12])   # drop specks
    merged=[]
    for b in bx:
        if merged:
            m=merged[-1]; ov=min(m[1],b[1])-max(m[0],b[0])
            if ov>0.5*min(m[1]-m[0],b[1]-b[0]):
                m[0]=min(m[0],b[0]);m[1]=max(m[1],b[1]);m[2]=min(m[2],b[2]);m[3]=max(m[3],b[3]); continue
        merged.append(list(b))
    return merged
def vedges(img):
    """sub-pixel top and bottom edge of the ink in img (rows): ink-sum estimator on the row-max profile"""
    p=img.max(1); full=np.where(p>=0.98)[0]
    if len(full)==0: full=np.where(p>=p.max()*0.98)[0]
    r0,r1=full[0],full[-1]
    top=r0-p[:r0].sum(); bot=r1+1+p[r1+1:].sum()
    return float(top), float(bot)
def ref_glyph(k):
    ink=np.load(FC+'crops/'+k+'_ink.npy'); bi,ch=SIZING[k]; b=blobs(ink)[bi]
    sub=ink[:, b[0]:b[1]].copy()
    # other glyphs' ink inside the column range (kerning overlaps) is removed with the blob's own label mask
    lab,_=ndimage.label(ink>0.02); ids=set(np.unique(lab[b[2]:b[3], b[0]:b[1]][ink[b[2]:b[3], b[0]:b[1]]>0.5]))-{0}
    mask=np.isin(lab, list(ids))[:, b[0]:b[1]]
    top,bot=vedges(sub*mask)
    return dict(h=bot-top, top=top, bottom=bot)
REF={k:np.load(FC+'crops/'+k+'_ink.npy') for k in SIZING}
REFG={k:ref_glyph(k) for k in SIZING}
def render(jobs, tag='j'):
    tmp=SP+'renders/p%d/'%os.getpid(); os.makedirs(tmp,exist_ok=True); jf=tmp+tag+'.json'; json.dump(jobs,open(jf,'w'))   # per-process dir: parallel runs must not share render files
    o=subprocess.run([REN,jf,tmp],capture_output=True,text=True)
    if o.returncode: raise RuntimeError(o.stderr[:500])
    out={}
    for line in o.stdout.splitlines():
        m=json.loads(line); r=np.fromfile(tmp+m['id']+'.raw',dtype=np.uint8).reshape(m['H'],m['W']).astype(float)/255
        os.remove(tmp+m['id']+'.raw'); out[m['id']]=(r,m)
    return out
CAP0=100.0
def sizing(f, ps, ax, chars):
    """render each sizing char alone at CAP0 (x SS) and measure it (SS px)"""
    jobs=[dict(id='sz%d'%i,font=f,ps=ps,axes=ax,cap=CAP0*SS,text=ch,H=int(CAP0*SS*2.2),base=CAP0*SS*1.6,x=CAP0*SS*0.3) for i,ch in enumerate(chars)]
    rr=render(jobs,'sz'); res={}
    for i,ch in enumerate(chars):
        r,m=rr['sz%d'%i]; t,b=vedges(r); res[ch]=dict(h=b-t, off=b-CAP0*SS*1.6)
    return res
def crop_job(jid, f, ps, ax, k, sz, text=None):
    g=REFG[k]; bi,ch=SIZING[k]; s=g['h']*SS/sz[ch]['h']
    return dict(id=jid,font=f,ps=ps,axes=ax,cap=CAP0*SS*s,text=text or M[k]['text'],H=REF[k].shape[0]*SS,
                base=g['bottom']*SS-sz[ch]['off']*s,x=6*SS), s
def left_edge(img):
    cols=np.where(img.max(0)>0.5)[0]; return cols[0] if len(cols) else 0
def ink_w(img):
    cols=np.where(img.max(0)>0.5)[0]; return (cols[-1]-cols[0]+1) if len(cols) else 0
def reduce(r, p, q):
    if p>0: r=np.pad(r,((0,0),(p,0)))
    if q>0: r=np.pad(r,((q,0),(0,0)))[:r.shape[0]]
    elif q<0: r=np.pad(r[-q:],((0,-q),(0,0)))
    h=r.shape[0]//SS*SS; w=r.shape[1]//SS*SS
    return r[:h,:w].reshape(h//SS,SS,w//SS,SS).mean((1,3))
def score(ref, r):
    h,w=ref.shape; best=(-1,)
    base=reduce(r,0,0); d0=left_edge(ref)-left_edge(base)
    for q in (-1,0,1):
        for p in range(SS):
            im=reduce(r,p,q)
            for dx in range(d0-3,d0+4):
                Wt=max(w, im.shape[1]+abs(dx))+8
                A=np.zeros((h,Wt)); A[:,:w]=ref
                B=np.zeros((h,Wt)); hh=min(h,im.shape[0])
                if dx>=0: B[:hh,dx:dx+im.shape[1]]=im[:hh]
                else: B[:hh,:im.shape[1]+dx]=im[:hh,-dx:]
                iou=np.minimum(A,B).sum()/np.maximum(A,B).sum()
                if iou>best[0]: best=(iou, dx+p/SS, q/SS, B)
    iou,dx,dy,B=best
    return dict(iou=round(float(iou),4), dx=dx, dy=dy, mass=round(float(B.sum()/ref.sum()),4),
                wratio=round(ink_w(B)/max(ink_w(ref),1),4)), B
def score2(ref, r):
    s,B=score(ref, r)
    from PIL import Image
    f=1/max(s['wratio'],1e-3)
    r2=np.asarray(Image.fromarray(r.astype(np.float32),'F').resize((max(1,round(r.shape[1]*f)),r.shape[0]),Image.BILINEAR))
    s2,_=score(ref, r2); s['iou_wfit']=s2['iou']
    return s, B
def run(out, step=100, families=None, weights=None, crops=None, keep=False, quiet=False, minw=0):
    res=json.load(open(out)) if os.path.exists(out) else {}
    crops=crops or list(SIZING)
    for c in C:
        if families and c['family'] not in families: continue
        for w,f,ps,ax,opr in instances(c, step, weights):
            if w<minw and not (c['kind']=='static' and max(c['faces'])<minw): continue
            if str(w) in res.get(c['family'],{}) and all(k in res[c['family']][str(w)] for k in crops): continue
            chars=sorted(set(SIZING[k][1] for k in crops))
            try: sz=sizing(f,ps,ax,chars)
            except Exception as e: print('SIZE FAIL',c['family'],w,e); continue
            jobs=[]; meta={}
            for k in crops:
                jid=f"{c['family'].replace(' ','_').replace('(','').replace(')','')}__{w}__{k}"
                j,s=crop_job(jid,f,ps,ax,k,sz); jobs.append(j); meta[jid]=(k,s)
            rr=render(jobs,'cj')
            for jid,(r,m) in rr.items():
                k,s=meta[jid]
                sc,B=score2(REF[k],r); sc.update(size_px=round(m['size']/SS,3), ps=m['ps'])
                res.setdefault(c['family'],{}).setdefault(str(w),{})[k]=sc
                if keep: np.save(SP+'renders/'+jid+'.npy', B)
            if not quiet: print(c['family'], w, 'mean IoU', round(np.mean([res[c['family']][str(w)][k]['iou'] for k in crops]),4), flush=True)
            json.dump(res,open(out,'w'),indent=0)
    return res
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--step',type=int,default=100)
    ap.add_argument('--families'); ap.add_argument('--weights'); ap.add_argument('--crops'); ap.add_argument('--keep',action='store_true'); ap.add_argument('--minw',type=int,default=0); ap.add_argument('--part')
    a=ap.parse_args()
    crops=None
    if a.crops: crops=sum([GROUPS[x] if x in GROUPS else [x] for x in a.crops.split(',')],[])
    fams=a.families.split(',') if a.families else None
    if a.part:   # 'i/n': every n-th family starting at i (split a full run over 2 processes)
        i,n=map(int,a.part.split('/')); fams=[c['family'] for j,c in enumerate(C) if j%n==i and (fams is None or c['family'] in fams)]
    run(a.out, a.step, fams, [int(x) for x in a.weights.split(',')] if a.weights else None, crops, a.keep, minw=a.minw)
