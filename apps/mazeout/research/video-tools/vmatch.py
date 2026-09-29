#!/usr/bin/env python3
"""vmatch — which boards are the same level? Cross-matches every extracted video level (video-frames/work/extract/V?-L0NN.json)
against the phone's recorded levels (research/levels/L0NN.json) and V1 against V2.

  python3 vmatch.py [--min 0.5] [--out PATH]

Score = identical arrows (same cells tail->head and direction, best integer shift, and also mirrored/rotated? NO: boards are
compared as drawn) / max(arrow count). Only layer-1 (start-frame) arrows are compared (the phone JSON has no hidden layers).
Prints the best partner of every level and every pair >= --min; writes JSON (default video-frames/work/extract/matches.json)."""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
EX = os.path.join(RES, 'video-frames', 'work', 'extract')


def keyset(js, dx=0, dy=0):
    return {(tuple((c[0] + dx, c[1] + dy) for c in a['cells']), a['dir']) for a in js['arrows'] if a.get('layer', 1) == 1}


def score(A, B):
    ka = keyset(A)
    best = (0, (0, 0))
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            m = len(ka & keyset(B, dx, dy))
            if m > best[0]:
                best = (m, (dx, dy))
    na = len(ka); nb = len(keyset(B))
    return best[0] / max(1, max(na, nb)), best[0], na, nb, best[1]


def main():
    a = sys.argv[1:]
    mn = float(a[a.index('--min') + 1]) if '--min' in a else 0.5
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(EX, 'matches.json')
    vids = {}
    for p in sorted(glob.glob(os.path.join(EX, 'V?-L0??.json'))):
        vids[os.path.basename(p)[:-5]] = json.load(open(p))
    phone = {}
    for p in sorted(glob.glob(os.path.join(RES, 'levels', 'L0??.json'))):
        phone['phone-' + os.path.basename(p)[:-5]] = json.load(open(p))
    names = list(vids) + list(phone)
    alls = dict(vids, **phone)
    pairs = []
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            if x[:2] == y[:2] and not x.startswith('phone') and x[:2] == y[:2]:
                continue          # same video: skip (levels do not repeat inside one video)
            if x.startswith('phone') and y.startswith('phone'):
                continue
            s, m, na, nb, sh = score(alls[x], alls[y])
            if m:
                pairs.append(dict(a=x, b=y, score=round(s, 3), identical=m, arrows=[na, nb], shift=sh))
    pairs.sort(key=lambda r: -r['score'])
    best = {}
    for r in pairs:
        for k in ('a', 'b'):
            o = r['b' if k == 'a' else 'a']
            if r[k] not in best or r['score'] > best[r[k]]['score']:
                best[r[k]] = dict(partner=o, score=r['score'], identical=r['identical'], arrows=r['arrows'])
    res = dict(rule=__doc__.split('\n')[4].strip(), pairs=[r for r in pairs if r['score'] >= mn], best=best)
    json.dump(res, open(out, 'w'), indent=1)
    for r in res['pairs']:
        print('%-14s == %-14s  %.3f  (%d identical of %s)  shift %s' % (r['a'], r['b'], r['score'], r['identical'], r['arrows'], r['shift']))
    print('best partner below %.2f:' % mn, ', '.join('%s->%s %.2f' % (k, v['partner'], v['score']) for k, v in sorted(best.items()) if v['score'] < mn))


if __name__ == '__main__':
    main()
