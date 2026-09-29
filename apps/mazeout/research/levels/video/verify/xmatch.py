#!/usr/bin/env python3
"""Every video board (L1-L31 finals, V2 L32-L38) x every phone board (research/levels/L032..L061 + open variants), 8 symmetries,
best integer shift (voting over same-shaped arrows) -> verify/xmatch.json + a printed summary. Verifier's own code (lvldiff.py)."""
import json, os, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lvldiff

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
vid = {}
for n in range(1, 32):
    vid[n] = os.path.join(R, 'levels', f'L{n:03d}.json')
for n in range(32, 39):
    vid[n] = os.path.join(R, 'levels', 'video', f'V2-L{n:03d}.json')
phone = sorted(glob.glob(os.path.join(R, 'levels', 'L0[3-6][0-9]*.json')))
phone = [p for p in phone if 32 <= int(os.path.basename(p)[1:4]) <= 61]


def arrows_of(p, all_layers=False):
    d = json.load(open(p))
    return d, [a for a in d['arrows'] if all_layers or a.get('layer', 1) == 1]


out = {'phone_files': [os.path.basename(p) for p in phone], 'rows': []}
for n, vp in vid.items():
    dv, A = arrows_of(vp, all_layers=True)
    best = None
    for pp in phone:
        dp, B = arrows_of(pp)
        c = lvldiff.compare(A, B, sym=True, WA=dv['cols'], HA=dv['rows'])
        frac = c['identical'] / max(1, min(len(A), len(B)))
        row = (c['identical'], frac, os.path.basename(pp), c['sym'], c['shift'], len(A), len(B))
        if best is None or row[:2] > best[:2]:
            best = row
    out['rows'].append({'video_level': n, 'video_arrows': len(A), 'best_phone': best[2], 'identical': best[0],
                        'phone_arrows': best[6], 'frac_of_smaller': round(best[1], 3), 'sym': best[3], 'shift': best[4]})
    print(f'video L{n:02d} ({len(A)} arrows incl. hidden) best {best[2]} ({best[6]} arrows): {best[0]} identical '
          f'({best[1]:.2f} of the smaller) sym {best[3]} shift {best[4]}', flush=True)
json.dump(out, open(os.path.join(R, 'levels', 'video', 'verify', 'xmatch.json'), 'w'), indent=1)
