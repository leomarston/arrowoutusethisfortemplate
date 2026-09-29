"""Fine fit of one family: for every crop, scan weight x tracking (CoreText kern = SwiftUI .tracking, in pt) and keep
line IoU / ink ratio / width ratio / font size.  Sizing as in compare.py (the crop's sizing glyph).
pt conversion: phone runner shots 1178 px = 393 pt (px*393/1178); store shots 1320 px = 440 pt (px/3).
usage: fine.py OUT.json FAMILY w1,w2,.. t0:t1:step [crops|plain|face]"""
import json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from candidates import C, instances
import compare
SS=compare.SS
def px_per_pt(k): return 1178/393 if compare.M[k]['file'].startswith('shots/') or compare.M[k]['file'].startswith('kickoff/') else 3.0
if __name__=='__main__':
    out,fam=sys.argv[1],sys.argv[2]; ws=[int(x) for x in sys.argv[3].split(',')]
    t0,t1,ts=[float(x) for x in sys.argv[4].split(':')]; tracks=np.round(np.arange(t0,t1+1e-9,ts),3)
    crops=sum([compare.GROUPS[x] if x in compare.GROUPS else [x] for x in (sys.argv[5] if len(sys.argv)>5 else 'plain,face').split(',')],[])
    c=[x for x in C if x['family']==fam][0]
    res=json.load(open(out)) if os.path.exists(out) else {}
    for w in ws:
        _,f,ps,ax,opr=list(instances(c,5,[w]))[0]
        sz=compare.sizing(f,ps,ax,sorted(set(compare.SIZING[k][1] for k in crops)))
        for k in crops:
            ppt=px_per_pt(k); jobs=[]
            for t in tracks:
                j,s=compare.crop_job(f'f_{k}_{t}',f,ps,ax,k,sz); j['track']=float(t)*ppt*SS; jobs.append(j)
            rr=compare.render(jobs,'fine')
            for t in tracks:
                r,m=rr[f'f_{k}_{t}']; sc,B=compare.score(compare.REF[k],r)
                size_px=m['size']/SS
                res.setdefault(k,{}).setdefault(str(w),{})[str(t)]=dict(iou=sc['iou'],mass=sc['mass'],wratio=sc['wratio'],
                    size_px=round(size_px,3), size_pt=round(size_px/ppt,3))
            best=max(res[k][str(w)].items(), key=lambda kv: kv[1]['iou'])
            print(f"{fam} w{w} {k:11s} best track {best[0]:>6s}pt IoU {best[1]['iou']:.3f} ink x{best[1]['mass']:.2f} width x{best[1]['wratio']:.3f} size {best[1]['size_pt']:.2f}pt", flush=True)
        json.dump(res,open(out,'w'),indent=0)
