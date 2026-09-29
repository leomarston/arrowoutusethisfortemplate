"""Per-glyph shape score + spacing error (adapted from apps/arrows glyphscore.py).
Reference and candidate lines are split into glyph blobs (connected components; dots merged into the blob they
overlap).  Blob i of the candidate is compared with blob i of the reference after its own best 1/4-px alignment:
glyph IoU = sum(min)/sum(max).  Spacing error = RMS of blob-centroid x differences after removing the mean offset.
Crops whose blob counts differ are skipped (touching glyphs).
usage: glyphscore.py OUT.json "Fam:wPlain:wFace,..." [crops|plain|face]"""
import json, os, sys, numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
from candidates import C, instances
import compare
SS=compare.SS
def glyph_iou(refg, candg):
    """best IoU of two single-glyph images (same height) over x shifts in 1/4 px and y shifts of +-1/4 px"""
    h=refg.shape[0]; best=0
    for q in (-1,0,1):
        for p in range(SS):
            im=compare.reduce(np.pad(candg,((0,0),(p,0))),0,q)
            for dx in range(-3,4):
                W=max(refg.shape[1], im.shape[1]+abs(dx))+8
                A=np.zeros((h,W)); A[:, 4:4+refg.shape[1]]=refg
                B=np.zeros((h,W)); x0=4+dx
                if x0<0: continue
                B[:min(h,im.shape[0]), x0:x0+im.shape[1]]=im[:h]
                iou=np.minimum(A,B).sum()/np.maximum(A,B).sum()
                if iou>best: best=iou
    return best
def run_one(fam, w, k):
    c=[x for x in C if x['family']==fam][0]; _,f,ps,ax,opr=list(instances(c,5,[w]))[0]
    sz=compare.sizing(f,ps,ax,[compare.SIZING[k][1]])
    j,s=compare.crop_job('gs',f,ps,ax,k,sz); R4,m=compare.render([j],'gs')['gs']
    ref=compare.REF[k]; im=compare.reduce(R4,0,0)
    rb=compare.blobs(ref); cb=compare.blobs(im)
    if len(rb)!=len(cb): return dict(skip=f'{len(rb)} vs {len(cb)} blobs')
    text=[ch for ch in compare.M[k]['text'] if ch!=' ']
    labR,_=ndimage.label(ref>0.02); labC,_=ndimage.label(R4>0.02)
    ious=[];wts=[];rc=[];cc=[]
    for (a,b,y0,y1),(ca,cb_,cy0,cy1) in zip(rb,cb):
        # isolate: reference blob = its own connected ink (neighbours removed); candidate likewise in SS space
        idsR=set(np.unique(labR[:, a:b][ref[:, a:b]>0.5]))-{0}; mR=np.isin(labR,list(idsR))
        refg=(ref*mR)[:, max(a-2,0):b+2]
        idsC=set(np.unique(labC[:, ca*SS:cb_*SS][R4[:, ca*SS:cb_*SS]>0.5]))-{0}; mC=np.isin(labC,list(idsC))
        candg=(R4*mC)[:, max(ca-2,0)*SS:(cb_+2)*SS]
        # coarse shift so the candidate starts where the reference starts
        ious.append(glyph_iou(refg, candg)); wts.append(ref[:,a:b].sum())
        rc.append((ref[:,a:b].sum(0)*np.arange(a,b)).sum()/ref[:,a:b].sum())
        cc.append((im[:,ca:cb_].sum(0)*np.arange(ca,cb_)).sum()/max(im[:,ca:cb_].sum(),1e-6))
    d=np.array(cc)-np.array(rc); d-=d.mean()
    lab=text if len(text)==len(ious) else ['?']*len(ious)
    return dict(gIoU=round(float(np.average(ious,weights=wts)),4), spacing_rms_px=round(float(np.sqrt((d**2).mean())),2),
                per_glyph={f'{i}:{l}':round(float(x),3) for i,(l,x) in enumerate(zip(lab,ious))}, n=len(rb))
if __name__=='__main__':
    out=sys.argv[1]; specs=[x.split(':') for x in sys.argv[2].split(',')]
    crops=sum([compare.GROUPS[x] if x in compare.GROUPS else [x] for x in (sys.argv[3] if len(sys.argv)>3 else 'plain,face').split(',')],[])
    res=json.load(open(out)) if os.path.exists(out) else {}
    for sp in specs:
        fam=sp[0]; wp=int(sp[1]); wf=int(sp[2]) if len(sp)>2 else wp
        r={}
        for k in crops:
            w=wp if compare.GROUP_OF[k]=='plain' else wf
            r[k]=run_one(fam,w,k); r[k]['w']=w
        res[fam]=r
        ok=[v for v in r.values() if 'gIoU' in v]
        pg=[r[k]['gIoU'] for k in compare.GROUPS['plain'] if k in r and 'gIoU' in r[k]]
        fg=[r[k]['gIoU'] for k in compare.GROUPS['face'] if k in r and 'gIoU' in r[k]]
        print(f"{fam:30s} gIoU all {np.mean([v['gIoU'] for v in ok]):.4f}  plain {np.mean(pg) if pg else 0:.4f} ({len(pg)})  face {np.mean(fg) if fg else 0:.4f} ({len(fg)})  spacing {np.mean([v['spacing_rms_px'] for v in ok]):.2f}px  skipped {[k for k,v in r.items() if 'skip' in v]}", flush=True)
        json.dump(res,open(out,'w'),indent=1)
