#!/usr/bin/env python3
"""import_research.py — research level JSONs (phone + video) -> bundle-schema levels L1..L105 (SPEC-gameplay §14.2, LEVELS.md §2).

Sources (read only):
  research/levels/L001..L031.json   video (V1 L1-10, V2 L11-31; batch reports research/video-levels-{A,B,C}.md)
  research/levels/L032..L105.json   phone v552 (research/levels.md; session 2 = L062..L083, with corners; session 3 =
                                    L084..L105: corner facings read from the start shots, v552 elevators)
  design/tools/work/reveals/Lnnn.json   hidden arrows, doors, keys, tapes under doors (reveal_backfill.py)
  research/shots/NNN-Lnnn-start.png  pipe counter badge positions (orange face detector below)

What this adds to the raw reads (every item is cited in CURATION and in design/LEVELS.md):
  * counters the phone JSON does not carry (pipes, boxes; research/levels.md per level);
  * pipe mouths for the phone levels whose reader wrote no pipes[] (L48, L49, L56: derived from the tube shape);
  * door rectangles, opening order, keys (start + hidden) and the arrows/tapes under doors (reveal backfill);
  * the L57 box staircase split into its four boxes (shots/179);
  * reader artifacts removed (L49: the key/counter blob glued to a pipe);
  * obstacle ids (t/d/k/p/b/e/x + index), pipe cells ordered mouth -> mouth, tape ties = one cell per member.

Usage: python3 design/tools/import_research.py  -> design/tools/work/imported.json (L1..L105, before the duplicate
decision and the unlock/curve pass, which build_levels.py applies).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
RESEARCH = os.path.join(APP, 'research')
sys.path.insert(0, HERE)
import arrowcore as ac  # noqa: E402

PHONE_PX_PER_PT = 1178.0 / 393.0

# ------------------------------------------------------------------------------------------------ curation
# Keys: pipe/box matched by ANY cell they cover. Values VERIFIED from research/levels.md unless marked.
CURATION = {
    35: dict(pipes={(6, 0): 2}),                                   # levels.md L35: counter '2' (2 -> 1 -> 0 seen)
    36: dict(pipes={(0, 4): 1, (0, 12): 1}),                       # L36: both counters '1'
    38: dict(pipes={(0, 0): 4}),                                   # L38: counter '4'
    41: dict(pipes={(0, 0): 3, (19, 18): 3}),                      # L41: counters 3 and 3
    42: dict(pipes={(2, 0): 4, (16, 0): 4, (6, 26): 3, (13, 26): 3}),  # L42: top two 4, bottom two 3
    44: dict(pipes={(0, 3): 8, (24, 0): 3}),                       # L44: LEFT half 8, RIGHT half 3
    48: dict(pipes={(0, 0): 4, (7, 0): 4, (14, 0): 4}),            # L48: counter 4 each
    # L49: top-right U 4, left U 4, right-middle U 3, left-middle U 3, bottom U 3; the left U's blob also holds the key/
    # counter-box pixels on row 11 (reader note: "the key body touches the left pipe's counter box") -> dropped.
    49: dict(pipes={(20, 8): 4, (0, 12): 4, (19, 16): 3, (1, 20): 3, (8, 35): 3},
             pipe_drop_cells=[(1, 11), (2, 11)], keys_drop_empty=True),
    50: dict(boxes={(0, 15): 10}),                                 # L50: box 10 (10 x 3)
    51: dict(boxes={(10, 12): 8, (5, 15): 16, (0, 18): 23}),       # L51: 8 / 16 / 23 (= video L12, same cells)
    53: dict(boxes={(13, 0): 39, (13, 26): 21}),                   # L53: top 39, bottom 21
    # L56: TL box 47, BR box 18; pipes (shots/174 read by eye): TR 5, left-upper 5, right-lower 4, left-lower 3
    56: dict(boxes={(0, 0): 47, (14, 23): 18}, pipes={(17, 8): 5, (3, 12): 5, (17, 16): 4, (3, 20): 3}),
    # L57: the four touching boxes read as one blob; split by eye on shots/179 (left -> right 40, 37, 26, 22)
    57: dict(box_split=[((0, 21, 4, 23), 40), ((5, 18, 9, 23), 37), ((10, 15, 14, 23), 26), ((15, 12, 19, 23), 22)]),
    # ---- phone session 2 (research/levels.md "Phone session 2"; research/phone-session2-progress.md)
    62: dict(boxes={(18, 3): 23, (9, 12): 66, (1, 21): 34}),        # counters_note: 23 top-right, 66 middle, 34 bottom-left
    63: dict(pipes={(12, 0): 3, (12, 18): 3}),                      # both badges read "3" (bot/tmp/L063-112956-r01)
    # L65: the reader's 767-cell 'door' blob = 2 doors + 2 boxes (shots/421): boxes 22 (top, 13x7) and 52 (bottom, 13x8) in
    # the right column; the doors come from the reveal backfill (DOOR_RECTS_S2)
    65: dict(box_split=[((13, 0, 25, 6), 22), ((13, 17, 25, 24), 52)]),
    # L66: the key on the long row-5 arrow (override L066.json, start frame) hangs on (6,5)-(7,5); the read kept one cell
    66: dict(key_cells={12: [(6, 5), (7, 5)]}),
    67: dict(boxes={(15, 0): 25, (10, 5): 21, (5, 10): 14, (0, 15): 9}),   # anti-diagonal, top-right -> bottom-left
    68: dict(pipes={(19, 0): 6, (19, 30): 3}),                      # counters_note: 6 top, 3 bottom
    # L69 (Super Hard): 4 doors (top + three side by side at the bottom), 3 keys at the start + 1 under the bottom-left door
    # (on the col-0 arrow, read as a 1-cell blob touching the pipe badge; by eye on bot/tmp/L069-124510-r02), and THREE PIPES
    # UNDER DOORS, revealed by the bursts (bot/tmp/L069-124510-r02, -124847-r03, -124847-r05; counters read by eye 2, 4, 3):
    69: dict(key_cells={'hidden:(0, 31)': [(0, 30), (0, 31)]},
             hidden_pipes=[([(1, 28), (1, 29), (1, 30), (2, 30), (3, 30), (4, 30), (5, 30), (6, 30), (6, 29), (6, 28)], 2),
                           ([(19, 28), (19, 29), (19, 30), (20, 30), (21, 30), (22, 30), (23, 30), (24, 30), (24, 29),
                             (24, 28)], 4),
                           ([(6, 5), (6, 4), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (11, 3), (12, 3), (13, 3), (14, 3),
                             (15, 3), (16, 3), (17, 3), (18, 3), (19, 3), (19, 4), (19, 5)], 3)]),
    73: dict(boxes={(16, 0): 46, (16, 22): 58}),                     # counters_note: 46 top-right, 58 bottom-right
    77: dict(box_split=[((0, 21, 4, 23), 40), ((5, 18, 9, 23), 37), ((10, 15, 14, 23), 26), ((15, 12, 19, 23), 22)]),  # = L57
    82: dict(pipes={(0, 0): 6, (20, 5): 6, (0, 10): 6}),            # three badges read "6" (shots/533, by eye)
    83: dict(pipes={(12, 0): 3, (12, 18): 3}),                      # = L63 (bot/tmp/L083-141306-r01)
    # ---- phone session 3 (research/levels.md "L84 (phone session 3)" ...; research/phone-session3-progress.md). Corners: the
    # start reads carry no `facing` since session 3 -> read from the start shot with research/bot/corners.py (corner_facings).
    86: dict(key_cells={12: [(6, 5), (7, 5)]}),                     # = L66 (override L086.json = L066's): the key spans 2 cells
    87: dict(boxes={(12, 0): 17, (12, 10): 34, (12, 20): 40}),      # three 6x6 boxes stacked on the right, top -> bottom
    88: dict(pipes_all=3),                                          # two long ∩ pipes, badge '3' at each right-hand mouth
    92: dict(boxes={(0, 0): 15}, pipes_all=3),                      # the 18x3 box along the top '15'; two U pipes '3'
    96: dict(pipes_all=3),                                          # one 58-cell zig-zag pipe, badge '3' at the bottom mouth
    97: dict(boxes={(9, 0): 21}),                                   # the 4x26 pillar box '21'
    105: dict(pipes_all=3),                                         # two C pipes on the left edge, '3' at each right mouth
}
# The corner's facing (research: the plate's diagonal [sx, sy], y down) -> the bundle's CornerTurn (named incoming -> outgoing,
# SPEC-gameplay §3.9). research/bot/corners.py's rule, d' = d - (d.s)s for d.s < 0, blocked otherwise, gives for s = (1, -1)
# (plate up-right): left -> up, down -> right = arrowcore 'downRight' (down -> right, left -> up); checked for all 16 pairs
# by corner_turn_selftest().
FACING_TURN = {(1, -1): 'downRight', (-1, -1): 'downLeft', (1, 1): 'upRight', (-1, 1): 'upLeft'}
# Video pipe badges noted by batch C (cell the badge sits on); others use the phone detector or the default rule.
VIDEO_BADGE = {25: {(18, 5): (18, 4), (5, 29): (4, 29)}, 29: {(0, 4): (0, 3), (6, 10): (6, 9), (12, 16): (12, 15)}}
DOOR_LEVELS = (33, 34, 37, 41, 43, 46, 47, 49, 53, 54, 58, 62, 63, 65, 66, 69, 83, 86, 89, 93, 98)
RECORDED_END = 105                  # research/levels L032..L105 (phone sessions 1, 2 and 3)
# Phone session 3's elevator levels. v552 L100 / L101 / L103 ARE the older build's V2-L031 / V2-L032 / V2-L033 in the same cell
# frame (reveal_backfill.backfill_elevator + the check in import: visible 28/28, 29/29, 36/36 with the same heads, platform cells
# equal, the hidden arrows the phone revealed 7/7, 11/11, 15/15 in the V2 layer; L103's -open1 dump holds 8 of 17, so its
# hidden layer is V2-L033's, as the session ledger says): imported from the V2 file with the phone's timer, tag and capture.
# L102 is a new board: platform = the start read's lavender cells, hidden layer = reveal_backfill's (work/reveals/L102.json).
PHONE_IS_V2 = {100: 'V2-L031', 101: 'V2-L032', 103: 'V2-L033'}
ELEVATOR_LEVELS = (102,)


def corner_turn_selftest():
    """FACING_TURN = research/bot/corners.py's reflection, for every facing and every ray direction."""
    for s_, turn in FACING_TURN.items():
        for d, v in ac.DIRS.items():
            dot = v[0] * s_[0] + v[1] * s_[1]
            want = None
            if dot < 0:
                w = (v[0] - dot * s_[0], v[1] - dot * s_[1])
                want = next(k for k, x in ac.DIRS.items() if x == w)
            got = ac.CORNER[turn].get(d)
            if got != want:
                raise SystemExit('corner facing %s turn %s: %s -> %s, corners.py says %s' % (s_, turn, d, got, want))


def T(c):
    return (int(c[0]), int(c[1]))


def ordered_path(cells):
    """A 4-connected simple path -> cells in order from one extremity to the other."""
    cs = set(cells)

    def nb(c):
        return [n for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if n in cs]
    ends = [c for c in cs if len(nb(c)) == 1]
    if len(ends) != 2:
        raise ValueError('not a simple path: %d extremities in %s' % (len(ends), sorted(cs)[:6]))
    path, prev, cur = [min(ends)], None, min(ends)
    while True:
        nxt = [n for n in nb(cur) if n != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        path.append(cur)
    if len(path) != len(cs):
        raise ValueError('branching tube')
    return path


def pipe_from_path(path):
    e0, e1 = path[0], path[-1]
    out0 = ac.dir_between(path[1], e0)
    out1 = ac.dir_between(path[-2], e1)
    return [dict(cell=list(e0), out=out0), dict(cell=list(e1), out=out1)]


def detect_badges(shot_path, origin_pt, pitch_pt):
    """Orange counter faces of the pipe badges on a lossless phone shot -> centroids in cell units."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    im = np.array(Image.open(shot_path).convert('RGB')).astype(int)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    m = (R > 170) & (G > 40) & (G < 120) & (B < 40)
    m[:int(122 * PHONE_PX_PER_PT)] = False            # HUD band
    m[int(755 * PHONE_PX_PER_PT):] = False            # booster band
    lab, n = ndimage.label(m)
    out = []
    p = pitch_pt * PHONE_PX_PER_PT
    ox, oy = origin_pt[0] * PHONE_PX_PER_PT, origin_pt[1] * PHONE_PX_PER_PT
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 0.25 * p * p:                    # a badge face is ~1.1 x 1.1 pitch
            continue
        out.append(((xs.mean() - ox) / p, (ys.mean() - oy) / p))
    return out


def corner_facings(src):
    """Phone session 3: the corners' plate diagonals read from the start shot by research/bot/corners.py (read only), in the
    start json's cell frame (the shift from origin_pt, as bot.dump_level does). {cell: (sx, sy)}."""
    import numpy as np
    from PIL import Image
    sys.path.insert(0, os.path.join(RESEARCH, 'bot'))
    import bot
    import corners
    bot.read_board, bot.ray = corners._read, corners._ray          # corners.py patches bot on import: call it explicitly
    im = np.array(Image.open(os.path.join(APP, src['shot'].replace('apps/mazeout/', ''))).convert('RGB')).astype(np.int16)
    b = corners.read_board(im)
    f = b['fit']
    c0 = int(round((src['origin_pt'][0] * bot.SCALE - f['x0']) / f['pitch']))
    r0 = int(round((src['origin_pt'][1] * bot.SCALE - f['y0']) / f['pitch']))
    return {(c - c0, r - r0): tuple(s_) for (c, r), s_ in b['corners'].items()}


def default_badge(pipe):
    """DECISION default: the badge centred between the first mouth and its tube neighbour (phone L56 pattern)."""
    cs = pipe['cells']
    return [round((cs[0][0] + cs[1][0]) / 2.0, 2), round((cs[0][1] + cs[1][1]) / 2.0, 2)]


def rect_cells(c0, r0, c1, r1):
    return [[c, r] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]


def import_level(L, reveals=None, warn=None, src_path=None):
    src = json.load(open(src_path or os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    cur = CURATION.get(L, {}) if src_path is None else {}
    warn = warn if warn is not None else []
    arrows = []
    for a in src['arrows']:
        rec = dict(id=a['id'], cells=[list(T(c)) for c in a['cells']], dir=a['dir'])
        if (a.get('layer') or 1) > 1:
            rec['layer'] = a['layer']
        arrows.append(rec)
    by_cells = {}
    for a in arrows:
        for c in a['cells']:
            if a.get('layer', 1) == 1:
                by_cells[T(c)] = a['id']
    obst = []

    # tapes (tie = one cell per member)
    tapes = []
    for o in src['obstacles']:
        if o['kind'] != 'tape_pink':
            continue
        cs = [T(c) for c in o['cells']]
        members = sorted({by_cells[c] for c in cs if c in by_cells})
        tapes.append((cs, members))

    # pipes
    pipes = []
    if src.get('pipes'):
        for p in src['pipes']:
            path = ordered_path([T(c) for c in p['cells']])
            ends = {T(e['cell']): e['out'] for e in p['ends']}
            if set(ends) != {path[0], path[-1]}:
                warn.append('L%d pipe ends %s are not the tube extremities %s' % (L, list(ends), [path[0], path[-1]]))
            pe = [dict(cell=list(path[0]), out=ends.get(path[0])), dict(cell=list(path[-1]), out=ends.get(path[-1]))]
            pipes.append(dict(path=path, ends=pe, counter=p.get('counter')))
    else:
        for o in src['obstacles']:
            if o['kind'] != 'pipe':
                continue
            cs = [T(c) for c in o['cells'] if T(c) not in set(map(tuple, cur.get('pipe_drop_cells', [])))]
            path = ordered_path(cs)
            pipes.append(dict(path=path, ends=pipe_from_path(path), counter=o.get('counter')))
    pc = cur.get('pipes', {})
    for p in pipes:
        hit = [v for k, v in pc.items() if k in set(p['path'])]
        if hit:
            p['counter'] = hit[0]
        elif 'pipes_all' in cur:
            p['counter'] = cur['pipes_all']
        if p['counter'] is None:
            warn.append('L%d pipe at %s: NO COUNTER' % (L, p['path'][0]))
    # badge positions -> ends[0] = the mouth next to the badge
    badges = []
    if src.get('source') == 'recorded':
        shot = os.path.join(os.path.dirname(RESEARCH), src['shot']) if not os.path.isabs(src['shot']) else src['shot']
        if not os.path.exists(shot):
            shot = os.path.join(APP, src['shot'].replace('apps/mazeout/', '')) if 'apps/mazeout/' in src['shot'] else shot
        if not os.path.exists(shot):
            cand = glob.glob(os.path.join(RESEARCH, 'shots', '*-L%03d-start.png' % L))
            shot = cand[0] if cand else None
        if pipes and shot:
            badges = detect_badges(shot, src['origin_pt'], src['pitch_pt'])
    for p in pipes:
        mouths = [T(p['ends'][0]['cell']), T(p['ends'][1]['cell'])]
        at = None
        if badges:
            best = min(badges, key=lambda b: min(abs(b[0] - c[0]) + abs(b[1] - c[1]) for c in p['path']))
            dist = min(abs(best[0] - c[0]) + abs(best[1] - c[1]) for c in p['path'])
            if dist <= 1.0:
                at = [round(best[0] * 2) / 2.0, round(best[1] * 2) / 2.0]
                badges.remove(best)
        vb = VIDEO_BADGE.get(L, {})
        for m, cell in vb.items():
            if m in mouths:
                at = [float(cell[0]), float(cell[1])]
        if at is not None:
            dm = [abs(at[0] - m[0]) + abs(at[1] - m[1]) for m in mouths]
            if dm[1] < dm[0]:
                p['path'] = list(reversed(p['path']))
                p['ends'] = list(reversed(p['ends']))
        p['counter_at'] = at if at is not None else None

    # boxes
    boxes = []
    if 'box_split' in cur:
        for (c0, r0, c1, r1), n in cur['box_split']:
            boxes.append(dict(cells=rect_cells(c0, r0, c1, r1), counter=n))
    else:
        for o in src['obstacles']:
            if o['kind'] not in ('box', 'curtain'):
                continue
            cs = [T(c) for c in o['cells']]
            n = o.get('counter')
            for k, v in cur.get('boxes', {}).items():
                if k in set(cs):
                    n = v
            if n is None:
                warn.append('L%d box at %s: NO COUNTER' % (L, cs[0]))
            xs, ys = [c for c, _ in cs], [r for _, r in cs]
            rc = rect_cells(min(xs), min(ys), max(xs), max(ys))
            if len(rc) != len(set(cs)):
                warn.append('L%d box at %s is not a full rectangle (%d of %d)' % (L, cs[0], len(set(cs)), len(rc)))
            boxes.append(dict(cells=rc, counter=n))

    # corners (phone session 2: kind "corner", one cell, "facing" = the plate's diagonal; session 3: facing read from the shot)
    corners = []
    read_facing = None
    for o in src['obstacles']:
        if o['kind'] == 'corner':
            f = o.get('facing')
            if f is None:
                read_facing = read_facing if read_facing is not None else corner_facings(src)
                f = read_facing.get(T(o['cells'][0]))
                if f is None:
                    raise SystemExit('L%d corner %s: no facing on the start shot' % (L, o['cells'][0]))
            corners.append(dict(cells=[list(T(c)) for c in o['cells']], turn=FACING_TURN[tuple(f)]))

    # elevators (video; phone session 3 from the elevator reveal, L102)
    elevators = []
    if L in ELEVATOR_LEVELS and src_path is None:
        if reveals is None:
            raise SystemExit('L%d needs design/tools/work/reveals/L%03d.json (run reveal_backfill.py)' % (L, L))
        plat = sorted({T(c) for o in src['obstacles'] if o['kind'] == 'elevator' for c in o['cells']})
        nid = max(a['id'] for a in arrows) + 1
        hid = []
        for h in reveals['hidden']:
            arrows.append(dict(id=nid, cells=[list(T(c)) for c in h['cells']], dir=h['dir'], layer=2))
            hid.append(nid)
            nid += 1
        src = dict(src, elevators=[dict(cells=[list(c) for c in plat], arrow_ids=list(reveals['platform']),
                                        hidden_arrow_ids=hid)])
    for e in src.get('elevators') or []:
        elevators.append(dict(cells=[list(T(c)) for c in e['cells']], platform=sorted(e['arrow_ids']),
                              hidden=sorted(e['hidden_arrow_ids'])))

    # doors + keys (+ hidden arrows and tapes) from the reveal backfill
    doors, keys = [], []
    if L in DOOR_LEVELS and src_path is None:
        if reveals is None:
            raise SystemExit('L%d needs design/tools/work/reveals/L%03d.json (run reveal_backfill.py)' % (L, L))
        order_ids = {}
        for d in sorted(reveals['doors'], key=lambda d: d['order']):
            did = 'd%d' % len(doors)
            order_ids[d['order']] = did
            doors.append(dict(id=did, cells=[list(T(c)) for c in d['cells']], order=len(doors), reveals=[]))
        for h in reveals['hidden']:
            did = order_ids[h['door']]
            arrows.append(dict(id=h['id'], cells=[list(T(c)) for c in h['cells']], dir=h['dir'], hidden_by=did))
            next(d for d in doors if d['id'] == did)['reveals'].append(h['id'])
            for c in h['cells']:
                by_cells[T(c)] = h['id']
        for t in reveals['tapes']:
            tapes.append(([T(c) for c in t['cells']], sorted(t['members'])))
        kl = [k for k in reveals['keys'] if k['rider'] is not None]
        if cur.get('keys_drop_empty'):
            kl = [k for k in kl if k['cells']]
        for k in kl:                                                   # curated key cells (a key the reader cut short)
            kc = cur.get('key_cells', {})
            if k['rider'] in kc and k['start']:
                k['cells'] = [list(c) for c in kc[k['rider']]]
            for tag, cells in kc.items():
                if isinstance(tag, str) and not k['start'] and tag == 'hidden:%s' % (tuple(k['cells'][0]),):
                    k['cells'] = [list(c) for c in cells]
        for k in kl:
            rc = {T(c) for a in arrows if a['id'] == k['rider'] for c in a['cells']}
            if not {T(c) for c in k['cells']} <= rc or len(k['cells']) != 2:
                warn.append('L%d key %s is not 2 cells on its rider %s' % (L, k['cells'], k['rider']))
        # keys target doors in door order: the k-th key to be used opens the k-th door (research: doors open in order)
        kd = sorted(kl, key=lambda k: (0 if k['start'] else 1, k.get('first_round', 0)))
        for k in kd:
            keys.append(dict(cells=[list(T(c)) for c in k['cells']], rider=k['rider'], start=k['start']))
        if len(keys) != len(doors):
            warn.append('L%d: %d keys for %d doors' % (L, len(keys), len(doors)))
        # pipes under doors (session 2, L69): an obstacle whose cells lie inside a door is hidden by it until its burst
        for cells, n in cur.get('hidden_pipes', []):
            path = [T(c) for c in cells]
            host = [d for d in doors if set(path) <= {T(c) for c in d['cells']}]
            if len(host) != 1:
                warn.append('L%d hidden pipe at %s is not inside exactly one door' % (L, path[0]))
            at = None
            if host:                      # the badge on the round shot where that door is first open (same board geometry)
                shot = next(x['shot'] for x in reveals['doors'] if x['order'] == host[0]['order'])
                bs = detect_badges(os.path.join(RESEARCH, 'bot', 'tmp', shot), src['origin_pt'], src['pitch_pt'])
                near = [b for b in bs if min(abs(b[0] - c[0]) + abs(b[1] - c[1]) for c in path) <= 1.0]
                if near:
                    b = min(near, key=lambda b: min(abs(b[0] - c[0]) + abs(b[1] - c[1]) for c in path))
                    at = [round(b[0] * 2) / 2.0, round(b[1] * 2) / 2.0]
                else:
                    warn.append('L%d hidden pipe at %s: no badge found on %s' % (L, path[0], shot))
            if at is not None:
                dm = [abs(at[0] - m[0]) + abs(at[1] - m[1]) for m in (path[0], path[-1])]
                if dm[1] < dm[0]:
                    path = list(reversed(path))
            pipes.append(dict(path=path, ends=pipe_from_path(path), counter=n, counter_at=at, hidden=True))

    # assemble obstacles with ids
    tapes.sort(key=lambda t: (min(r for _, r in t[0]), min(c for c, _ in t[0])))
    for i, (cs, members) in enumerate(tapes):
        obst.append(dict(id='t%d' % i, kind='tape', cells=[list(c) for c in cs], arrows=members))
    for d in doors:
        rec = dict(id=d['id'], kind='door', cells=d['cells'], order=d['order'])
        if d['reveals']:
            rec['reveals'] = sorted(d['reveals'])
        obst.append(rec)
    # key -> door: assigned by simulating the level's rule (lowest-order locked door not yet targeted) — i.e. keys
    # open doors in the order their arrows leave; `opens` stays unset so the rule, not the data, decides (§3.5).
    for i, k in enumerate(keys):
        obst.append(dict(id='k%d' % i, kind='key', cells=k['cells'], arrows=[k['rider']]))
    for i, p in enumerate(pipes):
        rec = dict(id='p%d' % i, kind='pipe', cells=[list(c) for c in p['path']], ends=p['ends'], counter=p['counter'])
        if p['counter_at'] is not None:
            rec['counter_at'] = p['counter_at']
        obst.append(rec)
    for i, b in enumerate(boxes):
        obst.append(dict(id='b%d' % i, kind='box', cells=b['cells'], counter=b['counter']))
    for i, c in enumerate(corners):
        obst.append(dict(id='x%d' % i, kind='corner', cells=c['cells'], turn=c['turn']))
    for i, e in enumerate(elevators):
        eid = 'e%d' % i
        obst.append(dict(id=eid, kind='elevator', cells=e['cells'], arrows=e['platform'], reveals=e['hidden']))
        for a in arrows:
            if a['id'] in e['hidden']:
                a['hidden_by'] = eid
                a['layer'] = 2
    for p in obst:
        if p['kind'] == 'pipe' and 'counter_at' not in p:
            p['counter_at'] = default_badge(p)

    tag = {None: 'normal', 'Hard Level': 'hard', 'Super Hard': 'superHard', 'Hard': 'hard'}.get(src.get('tag'), 'normal')
    capture = src.get('shot') or src.get('frame')
    arrows.sort(key=lambda a: a['id'])
    lvl = dict(level=L, source=src['source'], capture=capture, cols=src['cols'], rows=src['rows'], mask=None,
               timer_s=src['timer_s'], hearts=src.get('hearts') or 3, tag=tag, arrows=arrows, obstacles=obst)
    fit_grid(lvl, warn)
    return lvl


def fit_grid(lvl, warn):
    """cols/rows must hold every arrow and obstacle cell (the research bbox sometimes excludes pipe mouths)."""
    xs = [c[0] for a in lvl['arrows'] for c in a['cells']] + [c[0] for o in lvl['obstacles'] for c in o['cells']]
    ys = [c[1] for a in lvl['arrows'] for c in a['cells']] + [c[1] for o in lvl['obstacles'] for c in o['cells']]
    if min(xs) < 0 or min(ys) < 0:
        warn.append('L%d: negative cell (%d, %d)' % (lvl['level'], min(xs), min(ys)))
    if max(xs) >= lvl['cols'] or max(ys) >= lvl['rows']:
        warn.append('L%d: grid %dx%d grown to %dx%d' % (lvl['level'], lvl['cols'], lvl['rows'],
                                                       max(lvl['cols'], max(xs) + 1), max(lvl['rows'], max(ys) + 1)))
        lvl['cols'] = max(lvl['cols'], max(xs) + 1)
        lvl['rows'] = max(lvl['rows'], max(ys) + 1)


# The older build's authored boards that v552 does not have (research/video-levels-D.md): SPEC.md §5 item 19 ships
# V2-L032..L035 in the phone's duplicate slots and V2-L036..L038 at L62-L64.
EXTRA = ['V2-L032', 'V2-L033', 'V2-L034', 'V2-L035', 'V2-L036', 'V2-L037', 'V2-L038']


def import_phone_v2(L, warn):
    """A v552 board that IS an older-build V2 board (PHONE_IS_V2): the V2 import (with its hidden layer), the phone's level
    number, timer, tag and capture — after checking, in the same cell frame, that the phone's start read equals the V2
    board's visible layer (cells + heads) and platform, and that every hidden arrow the phone revealed is in the V2 layer."""
    name = PHONE_IS_V2[L]
    ph = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    lvl = import_level(int(name.split('L')[-1]), None, warn, src_path=os.path.join(RESEARCH, 'levels', 'video', name + '.json'))
    vis = {frozenset(map(tuple, a['cells'])): a['dir'] for a in lvl['arrows'] if (a.get('layer') or 1) == 1}
    hid = {frozenset(map(tuple, a['cells'])): a['dir'] for a in lvl['arrows'] if (a.get('layer') or 1) > 1}
    got = {frozenset(map(tuple, a['cells'])): a['dir'] for a in ph['arrows']}
    plat = {tuple(c) for o in ph['obstacles'] if o['kind'] == 'elevator' for c in o['cells']}
    vplat = {tuple(c) for o in lvl['obstacles'] if o['kind'] == 'elevator' for c in o['cells']}
    if got != vis or plat != vplat:
        raise SystemExit('L%d is not %s: visible %d/%d equal, platform %s' % (L, name, sum(1 for k, d in got.items()
                                                                                       if vis.get(k) == d), len(vis), plat == vplat))
    rv = json.load(open(os.path.join(HERE, 'work', 'reveals', 'L%03d.json' % L)))
    miss = [h['cells'][:2] for h in rv['hidden'] if hid.get(frozenset(map(tuple, h['cells']))) != h['dir']]
    if miss:
        raise SystemExit('L%d: revealed arrows not in %s\'s hidden layer: %s' % (L, name, miss))
    lvl.update(level=L, source='recorded', capture=ph['shot'], timer_s=ph['timer_s'],
               tag={None: 'normal', 'Hard Level': 'hard', 'Super Hard': 'superHard'}.get(ph.get('tag'), 'normal'),
               _is=name)
    return lvl


def main():
    out, warn = [], []
    corner_turn_selftest()
    for L in range(1, RECORDED_END + 1):
        rv = None
        if L in DOOR_LEVELS or L in ELEVATOR_LEVELS:
            p = os.path.join(HERE, 'work', 'reveals', 'L%03d.json' % L)
            rv = json.load(open(p))
        if L in PHONE_IS_V2:
            out.append(import_phone_v2(L, warn))
            continue
        out.append(import_level(L, rv, warn))
    ac.dump(out, os.path.join(HERE, 'work', 'imported.json'))
    extra = {}
    for name in EXTRA:
        n = int(name.split('L')[-1])
        lvl = import_level(n, None, warn, src_path=os.path.join(RESEARCH, 'levels', 'video', name + '.json'))
        extra[name] = lvl
    ac.dump(extra, os.path.join(HERE, 'work', 'imported_extra.json'))
    for w in warn:
        print('WARN', w)
    print('imported %d levels + %d video extras' % (len(out), len(extra)))


if __name__ == '__main__':
    main()
