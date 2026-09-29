"""Rank families from compare.py output(s): per group (plain text / outlined faces) the weight with the best mean
metric, then the overall mean over all crops (each crop counted once).
usage: rank.py METRIC(iou|iou_wfit) OUT.tsv IN1.json [IN2.json ...]"""
import json, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from compare import GROUPS
from candidates import C
metric=sys.argv[1]; out=sys.argv[2]; d={}
for f in sys.argv[3:]:
    for fam,ws in json.load(open(f)).items(): d.setdefault(fam,{}).update(ws)
lic={c['family']:c['lic'] for c in C}
rows=[]
for fam,ws in d.items():
    r={'family':fam}; tot=[]
    for g,cr in GROUPS.items():
        best=None
        for w,cs in ws.items():
            if not all(c in cs for c in cr): continue
            m=np.mean([cs[c][metric] for c in cr]); raw=np.mean([cs[c]['iou'] for c in cr]); wf=np.mean([cs[c]['iou_wfit'] for c in cr])
            wr=np.mean([cs[c]['wratio'] for c in cr]); ms=np.mean([cs[c]['mass'] for c in cr])
            if best is None or m>best[0]: best=(m,w,raw,wf,wr,ms)
        if best is None: break
        r[g]=best; tot+=[best[0]]*len(cr)
    else:
        r['all']=float(np.mean(tot)); rows.append(r)
rows.sort(key=lambda r:-r['all'])
hdr=f"{'#':>2s} {'family':30s} {'licence':12s} {'ALL':>6s} | plain: w  {metric:>6s} iou   wfit  width  ink | face: w  {metric:>6s} iou   wfit  width  ink"
lines=[hdr]
for i,r in enumerate(rows):
    p=r['plain'];f=r['face']
    lines.append(f"{i+1:2d} {r['family']:30s} {lic.get(r['family'],'?'):12s} {r['all']:.4f} | {p[1]:>4s} {p[0]:.4f} {p[2]:.3f} {p[3]:.3f} {p[4]:.3f} {p[5]:.2f} | {f[1]:>4s} {f[0]:.4f} {f[2]:.3f} {f[3]:.3f} {f[4]:.3f} {f[5]:.2f}")
print('\n'.join(lines))
with open(out,'w') as fo:
    fo.write('rank\tfamily\tlicence\tall\tplain_w\tplain_'+metric+'\tplain_iou\tplain_wfit\tplain_width\tplain_ink\tface_w\tface_'+metric+'\tface_iou\tface_wfit\tface_width\tface_ink\n')
    for i,r in enumerate(rows):
        p=r['plain'];f=r['face']
        fo.write('\t'.join(map(str,[i+1,r['family'],lic.get(r['family'],'?'),round(r['all'],4),p[1],round(p[0],4),round(p[2],4),round(p[3],4),round(p[4],4),round(p[5],3),f[1],round(f[0],4),round(f[2],4),round(f[3],4),round(f[4],4),round(f[5],3)]))+'\n')
