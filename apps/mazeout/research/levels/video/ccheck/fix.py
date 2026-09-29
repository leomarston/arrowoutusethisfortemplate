import json, sys
W='/Users/yago/Downloads/app-factory/apps/mazeout/research/video-frames/work/levelsC/'

def occ(js):
    o = {}
    for a in js['arrows']:
        for c in a['cells']:
            o[tuple(c)] = a['id']
    return o

def fix_pipe(js, k, add_cells, end_moves, note):
    pp = js['pipes'][k]
    oc = occ(js)
    for c in add_cells:
        assert tuple(c) not in oc, ('cell occupied', c, oc.get(tuple(c)))
        assert list(c) not in pp['cells']
    old_cells = [list(c) for c in pp['cells']]
    pp['cells'] = sorted(old_cells + [list(c) for c in add_cells])
    for e in pp['ends']:
        for old, new in end_moves:
            if e['cell'] == old:
                e['cell'] = new
    # the matching obstacle entry
    obs = [o for o in js['obstacles'] if o['kind'] == 'pipe' and sorted(map(list, o['cells'])) == sorted(old_cells)]
    assert len(obs) == 1, len(obs)
    obs[0]['cells'] = [list(c) for c in pp['cells']]
    obs[0]['note'] = note
    js.setdefault('fixes', []).append('pipe %d: %s' % (k, note))

def rebound(js):
    cs = [tuple(c) for a in js['arrows'] for c in a['cells']] + [tuple(c) for o in js['obstacles'] for c in o['cells']]
    assert min(c[0] for c in cs) == 0 and min(c[1] for c in cs) == 0, 'normalisation changed'
    js['cols'] = max(c[0] for c in cs) + 1; js['rows'] = max(c[1] for c in cs) + 1

# L23
js = json.load(open(W + 'V2-L023.orig.json'))
fix_pipe(js, 0, [[6, 4]], [([6, 3], [6, 4])], 'mouth ring of the right leg is at (6,4) (the reader stopped at the badge cell (6,3)); frame L023-start.png')
fix_pipe(js, 1, [[9, 17], [15, 17]], [([9, 18], [9, 17]), ([15, 18], [15, 17])], 'both mouth rings are on row 17 (the reader started the legs at row 18); frame L023-start.png')
rebound(js); json.dump(js, open(W + 'V2-L023.json', 'w'), indent=1)
# L25
js = json.load(open(W + 'V2-L025.orig.json'))
fix_pipe(js, 0, [[18, 5]], [([18, 4], [18, 5])], 'bottom mouth ring at (18,5), badge at (18,4); frame L025-start.png')
fix_pipe(js, 1, [[5, 29]], [([4, 29], [5, 29])], 'right mouth ring at (5,29); frame L025-start.png')
rebound(js); json.dump(js, open(W + 'V2-L025.json', 'w'), indent=1)
# L29
js = json.load(open(W + 'V2-L029.orig.json'))
fix_pipe(js, 0, [[0, 4], [4, 0]], [([0, 3], [0, 4]), ([3, 0], [4, 0])], 'mouth rings at (0,4) and (4,0), badge at (0,3); frame L029-start.png')
fix_pipe(js, 1, [[6, 10], [10, 6]], [([6, 9], [6, 10]), ([9, 6], [10, 6])], 'mouth rings at (6,10) and (10,6), badge at (6,9); frame L029-start.png')
fix_pipe(js, 2, [[12, 16]], [([12, 15], [12, 16])], 'bottom mouth ring at (12,16), badge at (12,15); frame L029-start.png')
new = [[4, 2], [3, 2], [3, 3], [3, 4], [2, 4], [2, 3], [2, 2], [2, 1], [3, 1], [4, 1]]
oc = occ(js)
for c in new:
    assert tuple(c) not in oc, c
    for pp in js['pipes']:
        assert c not in pp['cells'], ('in pipe', c)
nid = max(a['id'] for a in js['arrows']) + 1
js['arrows'].append(dict(id=nid, cells=new, dir='right', added_by_hand='batch C: 10-cell arrow inside pipe 0\'s L-corner (tail (4,2), head (4,1) right) missed by the reader (the pipe bbox is excluded from its ink test; it was the "0 heads" anomaly)'))
js['fixes'].append('arrow %d added by hand (missed by the reader; was anomaly %r)' % (nid, js['anomalies']))
js['anomalies'] = []
js['occlusion_inferred'] = [x for x in js['occlusion_inferred'] if x != ['partial', [5, 8], [5, 9]]]
js['fixes'].append("occlusion_inferred entry ['partial', [5, 8], [5, 9]] (raw grid) dropped: it was the reader's guess between the added arrow's head (4,1) and the pipe mouth (4,0)")
rebound(js); json.dump(js, open(W + 'V2-L029.json', 'w'), indent=1)
print('ok')
