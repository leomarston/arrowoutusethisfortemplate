#!/usr/bin/env python3
"""Cell-by-cell diff of two level JSONs (phone schema or verify/myread.py output), written for the verifier.

usage: lvldiff.py A.json B.json [--sym] [--json OUT]
- start-frame arrows only (arrows with "layer": 2 are hidden elevator layers and are compared separately);
- an arrow = (ordered cells tail->head, dir); best integer shift (and with --sym the best of 8 symmetries) by voting;
- obstacles compared by kind + cell set (+ pipe ends, + counter when both have one).
"""
import json, sys, argparse
from collections import Counter

SYMS = [(lambda c, r, W, H: (c, r)), (lambda c, r, W, H: (W - 1 - c, r)), (lambda c, r, W, H: (c, H - 1 - r)),
        (lambda c, r, W, H: (W - 1 - c, H - 1 - r)), (lambda c, r, W, H: (r, c)), (lambda c, r, W, H: (H - 1 - r, c)),
        (lambda c, r, W, H: (r, W - 1 - c)), (lambda c, r, W, H: (H - 1 - r, W - 1 - c))]


def load(p):
    d = json.load(open(p))
    arr = [a for a in d['arrows'] if a.get('layer', 1) == 1]
    hid = [a for a in d['arrows'] if a.get('layer', 1) != 1]
    return d, arr, hid


def key(a):
    return tuple(tuple(c) for c in a['cells'])


def dir_of(cells):
    (c1, r1), (c2, r2) = cells[-2], cells[-1]
    return {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}[(c2 - c1, r2 - r1)]


def transform(arrows, f, W, H):
    out = []
    for a in arrows:
        cells = [f(c[0], c[1], W, H) for c in a['cells']]
        out.append({'id': a.get('id'), 'cells': [list(c) for c in cells], 'dir': dir_of(cells)})
    return out


def best_shift(A, B):
    # vote shifts between arrows of the same shape (same relative cells)
    def shape(a):
        c0 = a['cells'][0]
        return tuple((c[0] - c0[0], c[1] - c0[1]) for c in a['cells'])
    bs = {}
    for b in B:
        bs.setdefault(shape(b), []).append(b)
    votes = Counter()
    for a in A:
        for b in bs.get(shape(a), []):
            votes[(b['cells'][0][0] - a['cells'][0][0], b['cells'][0][1] - a['cells'][0][1])] += 1
    if not votes:
        return (0, 0), 0
    s, n = votes.most_common(1)[0]
    return s, n


def compare(A, B, Aob=(), Bob=(), sym=False, WA=None, HA=None):
    best = None
    fs = SYMS if sym else SYMS[:1]
    for k, f in enumerate(fs):
        At = transform(A, f, WA, HA)
        s, n = best_shift(At, B)
        if best is None or n > best[0]:
            best = (n, k, s, At)
    n, k, s, At = best
    Aset = {tuple((c[0] + s[0], c[1] + s[1]) for c in a['cells']): a for a in At}
    Bset = {key(b): b for b in B}
    same = [x for x in Aset if x in Bset]
    onlyA = [Aset[x] for x in Aset if x not in Bset]
    onlyB = [Bset[x] for x in Bset if x not in Aset]
    # obstacles (only for the identity symmetry)
    ob = None
    if k == 0:
        def norm(o, sh):
            cells = frozenset((c[0] + sh[0], c[1] + sh[1]) for c in o['cells'])
            ends = None
            if o.get('ends'):
                ends = frozenset(((e['cell'][0] + sh[0], e['cell'][1] + sh[1]), e['out']) for e in o['ends'])
            return ({'curtain': 'box'}.get(o['kind'], o['kind']), cells, ends)
        Ao = [norm(o, s) + (o.get('counter', o.get('counter_eye', o.get('counter_ocr'))),) for o in Aob]
        Bo = [norm(o, (0, 0)) + (o.get('counter'),) for o in Bob]
        ob = {'A': len(Ao), 'B': len(Bo), 'same_cells': 0, 'same_counter': 0, 'diffs': []}
        used = set()
        for a in Ao:
            m = [j for j, b in enumerate(Bo) if j not in used and b[0] == a[0] and b[1] == a[1]]
            if m:
                j = m[0]
                used.add(j)
                ob['same_cells'] += 1
                b = Bo[j]
                if a[2] != b[2] and a[2] is not None and b[2] is not None:
                    ob['diffs'].append({'kind': a[0], 'ends_A': sorted(a[2]), 'ends_B': sorted(b[2])})
                if a[3] is not None and b[3] is not None:
                    if a[3] == b[3]:
                        ob['same_counter'] += 1
                    else:
                        ob['diffs'].append({'kind': a[0], 'counter_A': a[3], 'counter_B': b[3]})
            else:
                ob['diffs'].append({'onlyA': a[0], 'cells': sorted(a[1])})
        for j, b in enumerate(Bo):
            if j not in used:
                ob['diffs'].append({'onlyB': b[0], 'cells': sorted(b[1])})
    return {'sym': k, 'shift': s, 'nA': len(A), 'nB': len(B), 'identical': len(same),
            'onlyA': [{'id': a['id'], 'cells': a['cells'], 'dir': a['dir']} for a in onlyA],
            'onlyB': [{'id': b.get('id'), 'cells': b['cells'], 'dir': b['dir']} for b in onlyB], 'obstacles': ob}


def compare_elevators(da, db, shift):
    EA = [o for o in da.get('obstacles', []) if o['kind'] == 'elevator']
    EB = db.get('elevators', []) or [o for o in db.get('obstacles', []) if o['kind'] == 'elevator']
    out = []
    for eb in EB:
        cb = set(tuple(c) for c in eb['cells'])
        best = (0, None)
        for ea in EA:
            ca = set((c[0] + shift[0], c[1] + shift[1]) for c in ea['cells'])
            j = len(ca & cb) / max(1, len(ca | cb))
            if j > best[0]:
                best = (j, len(ca))
        out.append({'cells_B': len(cb), 'cells_A': best[1], 'jaccard': round(best[0], 3)})
    return {'A': len(EA), 'B': len(EB), 'match': out}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--sym', action='store_true')
    ap.add_argument('--json')
    x = ap.parse_args()
    da, A, hA = load(x.a)
    db, B, hB = load(x.b)
    obA = [o for o in da.get('obstacles', []) if o['kind'] not in ('elevator',)]
    obB = [o for o in db.get('obstacles', []) if o['kind'] not in ('elevator',)]
    # pipes: prefer the `pipes` list (has ends) when present
    def pipes_of(d):
        return [dict(kind='pipe', cells=p['cells'], ends=p.get('ends'), counter=p.get('counter')) for p in d.get('pipes', [])]
    if da.get('pipes'):
        obA = [o for o in obA if o['kind'] != 'pipe'] + pipes_of(da)
    if db.get('pipes'):
        obB = [o for o in obB if o['kind'] != 'pipe'] + pipes_of(db)
    res = compare(A, B, obA, obB, x.sym, da.get('cols'), da.get('rows'))
    res['elevators'] = compare_elevators(da, db, res['shift']) if res['sym'] == 0 else None
    res['files'] = [x.a, x.b]
    res['dims'] = [[da.get('cols'), da.get('rows')], [db.get('cols'), db.get('rows')]]
    if x.json:
        json.dump(res, open(x.json, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('onlyA', 'onlyB')}))
    for a in res['onlyA']:
        print('  only A:', a)
    for b in res['onlyB']:
        print('  only B:', b)
