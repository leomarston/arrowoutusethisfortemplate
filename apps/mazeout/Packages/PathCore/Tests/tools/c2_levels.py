#!/usr/bin/env python3
"""c2_levels.py — the COMPLETED recorded levels L32–L61 for C2's tests (HeadlessTests, GoldenRoundsTests).

The research JSONs (research/levels/Lnnn.json, read by research/bot/bot.py on the owner's phone) are the authority for the
ARROWS but lack obstacle data the rules need: pipe and box counters (the phone JSON carries none), pipe mouths on L48 /
L49 / L56 (no pipes[] entry), the arrows and keys under doors when no Lnnn-openK.json was dumped (L33 L34 L37 L41 L43 L46),
keys riding revealed arrows (C1's reveal merge adds arrows only), door rectangles and their opening order (the phone JSON
has only the union), and one box blob that is really four boxes (L57). design/levels.json (SPEC-gameplay) will own these
values; until it exists this tool completes them from EVIDENCE only, each value cited:

  * arrows: research/levels/Lnnn.json (ids kept) + revealed arrows seen in ANOMALY-FREE per-round reads of the bot's own
    round shots (Fixtures/c2_reads.json, Tests/tools/c2_reads.py; cells mapped to the start frame with bot.dump_level's
    origin formula);
  * doors: the rectangles and ORDER in which the door cells vanished across the anomaly-free reads of one run (each shrink
    step = one door); keys: key blobs of those reads, riding the arrow that holds their cells;
  * pipes / tapes / boxes: the start shot's read (cells, pipe mouths); counters from the EVIDENCE table below (digits read on
    the start shots at the given screen points, cross-checked with research/levels.md);
  * timer, tag, hearts, mask: the research JSON.

Writes Tests/Fixtures/c2_recorded_levels.json ({"levels": [bundle-v1 level, …], "provenance": {...}}) and prints a report.
Pure Python (no numpy): the image reads are cached by c2_reads.py.
"""
import json, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
RESEARCH = os.path.join(APP, 'research')
FIX = os.path.join(HERE, '..', 'Fixtures')
READS = os.path.join(FIX, 'c2_reads.json')
OUT = os.path.join(FIX, 'c2_recorded_levels.json')
DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}

# Counter digits read on the START shots (screen pt, 393 x 852; shot px x 393/1178) and the level notes. "at": null = every
# obstacle of that kind on the level carries the value.
EVIDENCE = {
    35: {'pipe': [(None, 2, 'levels.md L35 "counter box ... (2 here)"; shot 042')]},
    36: {'pipe': [(None, 1, 'levels.md L36 "both counters 1"; shot 047')]},
    38: {'pipe': [(None, 4, 'levels.md L38 "PIPE along the top edge with counter 4"; shot 056')]},
    41: {'pipe': [(None, 3, 'levels.md L41 "2 PIPES (counters 3 and 3)"; shot 076')]},
    42: {'pipe': [((106.8, 258.8), 4, 'shot 081 top-left "4"'), ((336.5, 258.8), 4, 'shot 081 top-right "4"'),
                  ((123.0, 653.4), 3, 'shot 081 bottom-left "3"'), ((270.3, 653.4), 3, 'shot 081 bottom-right "3"')]},
    44: {'pipe': [((21.8, 206.3), 8, 'shot 090 left pipe "8"'), ((233.2, 695.2), 3, 'shot 090 right pipe "3"')]},
    48: {'pipe': [(None, 4, 'levels.md L48 "counter 4 each"; shot 121')]},
    49: {'pipe': [((348.5, 295.5), 4, 'shot 126 top-right U "4"'), ((45.3, 355.7), 4, 'shot 126 left U "4"'),
                  ((333.1, 417.2), 3, 'shot 126 right-middle U "3"'), ((60.2, 477.4), 3, 'shot 126 left-middle U "3"'),
                  ((249.8, 666.6), 3, 'shot 126 bottom U "3"')],
         'keyRider': ([[0, 10], [0, 11], [1, 11], [2, 11], [3, 11]],
                      'research/bot/overrides/L049.json: the key arrow tail (1,21)->(4,22) RIGHT in the read frame = start '
                      'frame (0,10)->(3,11); its key blob has no arrow cells (touches the pipe counter box)')},
    50: {'box': [(None, 10, 'levels.md L50 "silver ring counter 10"; shot 135')]},
    51: {'box': [((312.6, 508.2), 8, 'shot 140 right box "8"'), ((196.4, 578.6), 16, 'shot 140 middle box "16"'),
                 ((81.1, 648.2), 23, 'shot 140 left box "23"')]},
    53: {'box': [((None, 'top'), 39, 'levels.md L53 "top counter 39"'), ((None, 'bottom'), 21, 'levels.md L53 "bottom counter 21"')]},
    56: {'pipe': [((287.4, 325.8), 5, 'shot 174 upper-right U "5"'), ((105.9, 447.1), 5, 'shot 174 left-middle U "5"'),
                  ((287.4, 447.1), 4, 'shot 174 right-middle U "4"'), ((105.9, 568.4), 3, 'shot 174 lower-left U "3"')],
         'box': [((90.5, 264.8), 47, 'shot 174 top-left box "47"'), ((302.8, 613.6), 18, 'shot 174 bottom-right box "18"')]},
    57: {'box': [((62.8, 627.7), 40, 'shot 179 box 1 "40"'), ((152.0, 600.8), 37, 'shot 179 box 2 "37"'),
                 ((241.7, 573.5), 26, 'shot 179 box 3 "26"'), ((331.0, 547.0), 22, 'shot 179 box 4 "22"')]},
}


def shifted(cells, s):
    return [(c - s[0], r - s[1]) for c, r in cells]


def rect_ok(cells):
    cs = [c for c, _ in cells]; rs = [r for _, r in cells]
    return len(cells) == (max(cs) - min(cs) + 1) * (max(rs) - min(rs) + 1)


def components(cells):
    left = set(cells); out = []
    while left:
        seed = min(left, key=lambda c: (c[1], c[0])); comp = {seed}; stack = [seed]; left.discard(seed)
        while stack:
            c, r = stack.pop()
            for dc, dr in DIRS.values():
                n = (c + dc, r + dr)
                if n in left:
                    left.discard(n); comp.add(n); stack.append(n)
        out.append(comp)
    return out


def column_bands(area):
    """Consecutive columns with identical vertical runs form one rectangle (C1's splitIntoRectangles)."""
    rects = []
    for comp in components(area):
        c0 = min(c for c, _ in comp); c1 = max(c for c, _ in comp); r0 = min(r for _, r in comp); r1 = max(r for _, r in comp)
        def runs(c):
            out = []; start = None
            for r in range(r0, r1 + 2):
                inside = r <= r1 and (c, r) in comp
                if inside and start is None: start = r
                if not inside and start is not None: out.append((start, r - 1)); start = None
            return out
        band0 = c0; brun = runs(c0)
        for c in range(c0 + 1, c1 + 2):
            nxt = runs(c) if c <= c1 else []
            if c > c1 or nxt != brun:
                for a, b in brun:
                    rects.append({(cc, rr) for rr in range(a, b + 1) for cc in range(band0, c)})
                band0 = c; brun = nxt
    return rects


def pt_to_cell(pt, st):
    ox, oy = st['origin_pt']; p = st['pitch_pt']
    return (round((pt[0] - ox) / p), round((pt[1] - oy) / p))


def build(L, reads, notes):
    st = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    ev = EVIDENCE.get(L, {})
    d = reads[str(L)]
    start = d['start']
    s0 = start['shift']
    prov = collections.OrderedDict()
    prov['arrows'] = 'research/levels/L%03d.json (%d)' % (L, len(st['arrows']))
    # --- arrows
    arrows = [dict(id=a['id'], cells=[list(c) for c in a['cells']], dir=a['dir']) for a in st['arrows']]
    known = {frozenset(map(tuple, a['cells'])): a['id'] for a in arrows}
    start_read = {frozenset(shifted(a['cells'], s0)) for a in start['arrows']}
    if start_read != set(known):
        notes.append('L%d: the start shot read differs from the research JSON (%d vs %d arrows)' % (L, len(start_read), len(known)))
    clean = [r for r in d['rounds'] if r['read']['ok'] and not r['read']['anomalies']]
    nid = max(known.values()) + 1
    revealed = collections.OrderedDict()
    for r in clean:
        rd = r['read']
        for a in rd['arrows']:
            cs = shifted(a['cells'], rd['shift'])
            k = frozenset(cs)
            if k in known or k in revealed:
                continue
            if any(k & x for x in list(known) + list(revealed)):
                notes.append('L%d: %s arrow %s overlaps a known arrow → skipped' % (L, r['file'], sorted(k)[:3]))
                continue
            revealed[k] = dict(id=nid, cells=[list(c) for c in cs], dir=a['dir'], src=r['file'])
            nid += 1
    # --- doors: shrink steps of the anomaly-free reads of the run with the most complete history
    door_start = set()
    for b in start['blobs']:
        if b['kind'] == 'door':
            door_start |= set(shifted(b['cells'], s0))
    doors = []
    if door_start:
        best = None
        for run in sorted({r['run'] for r in clean}):
            seq = [('start', door_start)]
            for r in clean:
                if r['run'] != run:
                    continue
                cur = set()
                for b in r['read']['blobs']:
                    if b['kind'] == 'door':
                        cur |= set(shifted(b['cells'], r['read']['shift']))
                seq.append((r['file'], cur))
            steps = []
            prev = door_start
            okrun = True
            for f, cur in seq[1:]:
                if not cur <= prev:
                    okrun = False; break
                if cur != prev:
                    steps.append((f, prev - cur)); prev = cur
            if okrun and not prev and steps and (best is None or len(steps) >= len(best[1])):
                best = (run, steps)
        if best is None:
            for i, rect in enumerate(sorted(column_bands(door_start), key=lambda r: (min(c for c, _ in r), -max(rr for _, rr in r)))):
                doors.append(dict(cells=sorted(rect, key=lambda c: (c[1], c[0])), src='column bands of the start door cells (no complete read history)'))
            notes.append('L%d: door order from column bands (no complete read history)' % L)
        else:
            for f, gone in best[1]:
                parts = [gone] if rect_ok(gone) else column_bands(gone)
                if len(parts) > 1:
                    notes.append('L%d: %d doors opened between two reads (%s): ordered left → right' % (L, len(parts), f))
                for part in sorted(parts, key=lambda r: (min(c for c, _ in r), min(rr for _, rr in r))):
                    doors.append(dict(cells=sorted(part, key=lambda c: (c[1], c[0])),
                                      src='run %s: gone by %s (anomaly-free reads)' % (best[0], f)))
        prov['doors'] = ['d%d %dx%d %s' % (i, len({c for c, _ in x['cells']}), len({r for _, r in x['cells']}), x['src'])
                         for i, x in enumerate(doors)]
    # hiddenBy for revealed arrows
    all_arrows = arrows + list(revealed.values())
    door_sets = [set(map(tuple, x['cells'])) for x in doors]
    box_blobs = [set(shifted(b['cells'], s0)) for b in start['blobs'] if b['kind'] == 'box']
    for a in revealed.values():
        cs = set(map(tuple, a['cells']))
        hits = [(len(cs & ds), i) for i, ds in enumerate(door_sets)]
        n, i = max(hits) if hits else (0, -1)
        if n == 0:
            notes.append('L%d: revealed arrow %d (%s) lies under no door' % (L, a['id'], a['src']))
            continue
        if n < len(cs):
            notes.append('L%d: revealed arrow %d lies %d/%d inside d%d' % (L, a['id'], n, len(cs), i))
        a['hidden_by'] = 'd%d' % i
    if revealed:
        prov['revealed'] = '%d arrows from anomaly-free round reads (%s)' % (
            len(revealed), ', '.join(sorted({a['src'].split('-r')[0] for a in revealed.values()})))
    # --- keys
    by_cells = {frozenset(map(tuple, a['cells'])): a['id'] for a in all_arrows}
    riders = collections.OrderedDict()
    reads_for_keys = [('start', start)] + [(r['file'], r['read']) for r in clean]
    for f, rd in reads_for_keys:
        rarrows = [set(shifted(a['cells'], rd['shift'])) for a in rd['arrows']]
        for b in rd['blobs']:
            if b['kind'] != 'key' or not b['cells']:
                continue
            kc = set(shifted(b['cells'], rd['shift']))
            best = max(((len(kc & ra), i) for i, ra in enumerate(rarrows)), default=(0, -1))
            if best[0] == 0:
                continue
            rid = by_cells.get(frozenset(rarrows[best[1]]))
            if rid is None:
                notes.append('L%d: key %s rides an arrow not in the level (%s)' % (L, sorted(kc), f))
                continue
            if rid not in riders:
                riders[rid] = dict(cells=sorted(kc), src=f)
    if 'keyRider' in ev:
        cells, why = ev['keyRider']
        rid = by_cells[frozenset(map(tuple, cells))]
        riders.setdefault(rid, dict(cells=[tuple(c) for c in cells[1:3]], src=why))
    if riders:
        prov['keys'] = ['k%d on arrow %d (%s)' % (i, rid, k['src']) for i, (rid, k) in enumerate(riders.items())]
    if doors and len(riders) != len(doors):
        notes.append('L%d: %d keys for %d doors' % (L, len(riders), len(doors)))
    # --- tapes: the start shot's bands, then bands on revealed arrows seen in the anomaly-free reads (L47)
    obstacles = []
    tapes = collections.OrderedDict()
    for f, rd in reads_for_keys:
        rarrows = [set(shifted(a['cells'], rd['shift'])) for a in rd['arrows']]
        for b in rd['blobs']:
            if b['kind'] != 'tape_pink' or not b['cells']:
                continue
            band = set(shifted(b['cells'], rd['shift']))
            members = []
            for ra in rarrows:
                if band & ra and frozenset(ra) in by_cells:
                    members.append(by_cells[frozenset(ra)])
            key = tuple(sorted(members))
            if len(key) >= 2 and key not in tapes and not any(set(key) & set(k) for k in tapes):
                tapes[key] = (band, f)
    for i, (members, (band, f)) in enumerate(tapes.items()):
        obstacles.append(dict(id='t%d' % i, kind='tape', cells=[list(c) for c in sorted(band, key=lambda c: (c[1], c[0]))],
                              arrows=list(members)))
    if tapes:
        prov['tapes'] = ['t%d members %s (%s)' % (i, list(m), f) for i, (m, (_, f)) in enumerate(tapes.items())]
    for i, x in enumerate(doors):
        rev = sorted(a['id'] for a in revealed.values() if a.get('hidden_by') == 'd%d' % i)
        o = dict(id='d%d' % i, kind='door', cells=[list(c) for c in x['cells']], order=i)
        if rev: o['reveals'] = rev
        obstacles.append(o)
    for i, (rid, k) in enumerate(riders.items()):
        obstacles.append(dict(id='k%d' % i, kind='key', cells=[list(c) for c in k['cells']], arrows=[rid]))
    # --- pipes
    pipes = [dict(cells=shifted(p['cells'], s0), ends=[dict(cell=list(shifted([e['cell']], s0)[0]), out=e['out']) for e in p['ends']])
             for p in start['pipes']]
    pev = ev.get('pipe', [])
    pc = [None] * len(pipes); psrc = [None] * len(pipes)
    for at, n, why in pev:
        if at is None:
            pc = [n] * len(pipes); psrc = [why] * len(pipes); continue
        cc = pt_to_cell(at, st)
        k = min(range(len(pipes)), key=lambda j: min(abs(c - cc[0]) + abs(r - cc[1]) for c, r in pipes[j]['cells']))
        if pc[k] is not None:
            notes.append('L%d: two counters for pipe p%d' % (L, k))
        pc[k] = n; psrc[k] = '%s → cell %s' % (why, cc)
    for i, p in enumerate(pipes):
        o = dict(id='p%d' % i, kind='pipe', cells=[list(c) for c in sorted(p['cells'], key=lambda c: (c[1], c[0]))], ends=p['ends'])
        if pc[i] is not None: o['counter'] = pc[i]
        else: notes.append('L%d: pipe p%d has no counter evidence' % (L, i))
        obstacles.append(o)
    if pipes:
        prov['pipes'] = ['p%d counter %s: %s; mouths from the start shot read' % (i, pc[i], psrc[i]) for i in range(len(pipes))]
    # --- boxes (split a blob when several counters sit in it)
    bev = ev.get('box', [])
    boxes = []
    for blob in box_blobs:
        pts = []
        for at, n, why in bev:
            if at is None:
                pts.append((None, n, why)); continue
            if at[0] is None:
                pts.append((at, n, why)); continue
            cc = pt_to_cell(at, st)
            if cc in blob: pts.append((cc, n, why))
        if len([p for p in pts if p[0] is not None and p[0][0] is not None]) > 1:
            for rect in column_bands(blob):
                hit = [p for p in pts if p[0] is not None and p[0][0] is not None and p[0] in rect]
                boxes.append((rect, hit[0][1] if hit else None, '%s → cell %s; split by column bands' % (hit[0][2], hit[0][0]) if hit else 'no counter'))
        else:
            boxes.append((blob, None, None))
    # counters for unsplit boxes: "all", position hits, or top/bottom
    for bi, (rect, n, why) in enumerate(boxes):
        if n is not None:
            continue
        for at, v, w in bev:
            if at is None:
                boxes[bi] = (rect, v, w)
            elif at[0] is None:
                ys = sorted(((min(r for _, r in b[0]), j) for j, b in enumerate(boxes)))
                j = ys[0][1] if at[1] == 'top' else ys[-1][1]
                if j == bi: boxes[bi] = (rect, v, w + ' (by position)')
            else:
                cc = pt_to_cell(at, st)
                if cc in rect: boxes[bi] = (rect, v, '%s → cell %s' % (w, cc))
    for i, (rect, n, why) in enumerate(boxes):
        o = dict(id='b%d' % i, kind='box', cells=[list(c) for c in sorted(rect, key=lambda c: (c[1], c[0]))])
        if n is not None: o['counter'] = n
        else: notes.append('L%d: box b%d has no counter evidence' % (L, i))
        obstacles.append(o)
    if boxes:
        prov['boxes'] = ['b%d %d cells counter %s: %s' % (i, len(b[0]), b[1], b[2]) for i, b in enumerate(boxes)]
    out_arrows = [dict(id=a['id'], cells=a['cells'], dir=a['dir'], **({'hidden_by': a['hidden_by']} if a.get('hidden_by') else {}))
                  for a in all_arrows]
    level = dict(schema=1, level=L, source='recorded', capture=st['shot'], cols=st['cols'], rows=st['rows'],
                 timer_s=st['timer_s'], hearts=st.get('hearts', 3), tag=tag_of(st.get('tag')), arrows=out_arrows,
                 obstacles=obstacles)
    if st.get('mask'):
        level['mask'] = st['mask']
    return level, prov


def tag_of(t):
    if not t: return 'normal'
    k = t.lower().replace(' ', '')
    return {'hardlevel': 'hard', 'hard': 'hard', 'superhard': 'superHard'}.get(k, 'normal')


def main():
    reads = json.load(open(READS))['levels']
    notes = []
    levels = []; prov = {}
    for L in range(32, 62):
        lv, p = build(L, reads, notes)
        levels.append(lv); prov[str(L)] = p
    json.dump({'schema': 1, 'tool': 'Tests/tools/c2_levels.py', 'levels': levels, 'provenance': prov, 'notes': notes},
              open(OUT, 'w'), indent=None, separators=(',', ':'), sort_keys=True)
    for L in range(32, 62):
        lv = levels[L - 32]
        kinds = collections.Counter(o['kind'] for o in lv['obstacles'])
        print('L%d arrows %d (hidden %d) obstacles %s' % (L, len(lv['arrows']), sum(1 for a in lv['arrows'] if a.get('hidden_by')),
                                                          dict(kinds)))
    print('\nnotes:\n  ' + '\n  '.join(notes) if notes else '\nnotes: none')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
