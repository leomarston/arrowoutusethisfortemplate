#!/usr/bin/env python3
"""reveal_backfill.py — reconstruct what the DOORS hide on the recorded door levels (SPEC-gameplay §3.5, LEVELS.md §3).

The phone start JSONs (research/levels/Lnnn.json) hold only what is visible at the start: arrows under a locked door are
not in them. The phone bot won every door level and photographed the board before every round (research/bot/tmp/
Lnnn-<run>-rNN.png). This tool re-reads those round shots with the bot's own reader (research/bot/bot.py, read only) and
tracks, round by round, in the START json's cell frame (the shift comes from `origin_pt` exactly as bot.dump_level does):

  * door cells that vanish between two clean reads  -> one door rectangle each, in OPENING order;
  * arrows that appear and are not start arrows      -> hidden arrows, assigned to the door whose rectangle holds them;
  * keys (gold key blobs) and the arrow they hang on -> start keys and keys hidden under doors;
  * pink tapes that appear                           -> bundles hidden under doors.

Cross-check: every unit the bot TAPPED in the same run (research/bot/log.jsonl, cells in the read frame of its round) is
mapped to the start frame by the best integer shift and must equal a start or a revealed arrow; every start/revealed
arrow must have been tapped. Output: design/tools/work/reveals/Lnnn.json + a summary table on stdout.

Usage:  python3 design/tools/reveal_backfill.py [33 34 ... 58 62 63 65 66 69 83]   (default: all door levels; L62+ =
        phone session 2, backfill_s2)
Only clean reads (bot.guard ok, 0 anomalies) are used; the tool never touches research/.
"""
import glob
import json
import os
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
RESEARCH = os.path.join(APP, 'research')
sys.path.insert(0, os.path.join(RESEARCH, 'bot'))
warnings.filterwarnings('ignore')

import numpy as np            # noqa: E402
from PIL import Image         # noqa: E402
import bot                    # noqa: E402  (research/bot/bot.py — read-only reuse)

OUT = os.path.join(HERE, 'work', 'reveals')
# The attempt that WON, per level (run ids = the 6-digit stamp in the round-shot names; ledger: research/levels.md).
# L46 and L53 were resumed after a bot stop, so two runs make one attempt.
RUNS = {33: ['011032'], 34: ['011816'], 37: ['013748'], 41: ['015654'], 43: ['020428'], 46: ['022335', '022702'],
        47: ['024742'], 49: ['030011'], 53: ['033000', '033214'], 54: ['033648'], 58: ['040440']}


def rect_split(cells):
    """Union of door cells -> rectangles (per 4-connected component, column bands with identical vertical runs)."""
    cells = set(cells)
    comps = []
    while cells:
        s = min(cells)
        comp, stack = {s}, [s]
        cells.discard(s)
        while stack:
            c = stack.pop()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in cells:
                    cells.discard(n)
                    comp.add(n)
                    stack.append(n)
        comps.append(comp)
    rects = []
    for comp in comps:
        cs = sorted({c for c, _ in comp})
        rs = [r for _, r in comp]
        r0, r1 = min(rs), max(rs)

        def runs(c):
            out, start = [], None
            for r in range(r0, r1 + 2):
                inside = r <= r1 and (c, r) in comp
                if inside and start is None:
                    start = r
                if not inside and start is not None:
                    out.append((start, r - 1))
                    start = None
            return tuple(out)
        band_start, band_runs = cs[0], runs(cs[0])
        for c in list(range(cs[0] + 1, cs[-1] + 2)):
            nxt = runs(c) if c <= cs[-1] else ()
            if c > cs[-1] or nxt != band_runs:
                for (a, b) in band_runs:
                    rects.append(sorted((cc, rr) for cc in range(band_start, c) for rr in range(a, b + 1)))
                band_start, band_runs = c, nxt
    return rects


def bbox(cells):
    cs = [c for c, _ in cells]
    rs = [r for _, r in cells]
    return [min(cs), min(rs), max(cs), max(rs)]


def is_rect(cells):
    b = bbox(cells)
    return len(set(cells)) == (b[2] - b[0] + 1) * (b[3] - b[1] + 1)


def read(path, start):
    im = np.array(Image.open(path).convert('RGB')).astype(np.int16)
    ok, why, _ = bot.guard(im)
    if not ok:
        return None, 'guard: ' + why
    try:
        b = bot.read_board(im)
    except Exception as e:           # a board mid-animation can defeat the grid fit
        return None, 'read: %s' % e
    if b['anomalies']:
        return None, 'anomalies %d' % len(b['anomalies'])
    fit = b['fit']
    c0 = int(round((start['origin_pt'][0] * bot.SCALE - fit['x0']) / fit['pitch']))
    r0 = int(round((start['origin_pt'][1] * bot.SCALE - fit['y0']) / fit['pitch']))

    def m(cells):
        return [(c - c0, r - r0) for c, r in cells]
    arrows = [dict(cells=m(a['cells']), dir=a['dir']) for a in b['arrows']]
    obst = [dict(kind=o['kind'], cells=m(o['cells'])) for o in b['obstacles']]
    return dict(arrows=arrows, obstacles=obst, shift=(c0, r0), pitch=fit['pitch']), None


def log_units(level, t_from, t_to):
    out = []
    with open(os.path.join(RESEARCH, 'bot', 'log.jsonl')) as f:
        for line in f:
            r = json.loads(line)
            if r.get('level') != level or r.get('result') != 'tapped':
                continue
            if not (t_from - 5 <= r['t'] <= t_to + 60):
                continue
            out.append(r)
    return out


def best_shift(cells_list, known_sets):
    """Integer shift (dx, dy) that maps the most logged units onto known arrow cell sets."""
    best, bs = (0, 0), -1
    for dx in range(-40, 41):
        for dy in range(-40, 41):
            n = 0
            for cs in cells_list:
                if frozenset((c + dx, r + dy) for c, r in cs) in known_sets:
                    n += 1
            if n > bs:
                best, bs = (dx, dy), n
    return best, bs


def backfill(L):
    start = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    files = []
    for run in RUNS[L]:
        files += sorted(glob.glob(os.path.join(RESEARCH, 'bot', 'tmp', 'L%03d-%s-r*.png' % (L, run))))
    known = {}                     # frozenset(cells) -> id
    arrows = {}
    for a in start['arrows']:
        k = frozenset(map(tuple, a['cells']))
        known[k] = a['id']
        arrows[a['id']] = dict(id=a['id'], cells=[tuple(c) for c in a['cells']], dir=a['dir'], start=True, round=0)
    next_id = max(arrows) + 1
    start_doors = set()
    for o in start['obstacles']:
        if o['kind'] == 'door':
            start_doors |= set(map(tuple, o['cells']))
    start_doors |= set(map(tuple, start.get('door_cells') or []))
    keys_start = [sorted(map(tuple, o['cells'])) for o in start['obstacles'] if o['kind'] == 'key']
    tapes_start = [sorted(map(tuple, o['cells'])) for o in start['obstacles'] if o['kind'] == 'tape_pink']

    rounds = []
    skipped = []
    prev_doors = set(start_doors)
    events = []                    # (round index, removed door cells)
    key_seen = {}                  # frozenset(key cells) -> first round
    tape_seen = {}
    for i, f in enumerate(files):
        r, why = read(f, start)
        name = os.path.basename(f)
        if r is None:
            skipped.append((name, why))
            continue
        doors = set()
        for o in r['obstacles']:
            if o['kind'] == 'door':
                doors |= set(o['cells'])
        new = []
        for a in r['arrows']:
            k = frozenset(a['cells'])
            if k in known:
                continue
            aid = next_id
            next_id += 1
            known[k] = aid
            arrows[aid] = dict(id=aid, cells=a['cells'], dir=a['dir'], start=False, round=len(rounds), shot=name)
            new.append(aid)
        removed = prev_doors - doors
        if removed:
            events.append(dict(round=len(rounds), shot=name, cells=sorted(removed)))
        prev_doors = doors if doors <= prev_doors else prev_doors & doors
        for o in r['obstacles']:
            if o['kind'] == 'key' and 1 <= len(o['cells']) <= 2:
                k = frozenset(o['cells'])
                key_seen.setdefault(k, dict(first=len(rounds), last=len(rounds), shot=name))
                key_seen[k]['last'] = len(rounds)
            if o['kind'] == 'tape_pink' and o['cells']:
                k = frozenset(o['cells'])
                tape_seen.setdefault(k, dict(first=len(rounds), shot=name))
        rounds.append(dict(shot=name, arrows=len(r['arrows']), door_cells=len(doors), new=new))

    # doors: each removal event -> rectangles; any start door cells never removed are reported
    doors = []
    for ev in events:
        for rc in rect_split(ev['cells']):
            doors.append(dict(cells=rc, rect=bbox(rc), opened_round=ev['round'], shot=ev['shot']))
    problems = []
    left = start_doors - {c for d in doors for c in d['cells']}
    if left:
        problems.append('%d start door cell(s) never seen removed (board read ended?): %s' % (len(left), bbox(left)))
        for rc in rect_split(left):
            doors.append(dict(cells=rc, rect=bbox(rc), opened_round=None, shot=None, note='never seen open'))
    for d in doors:
        if not is_rect(d['cells']):
            problems.append('door %s not a rectangle' % d['rect'])
    for k, d in enumerate(doors):
        d['order'] = k

    # hidden arrows -> door
    for aid, a in arrows.items():
        if a['start']:
            continue
        cs = set(a['cells'])
        best, bn = None, 0
        for d in doors:
            n = len(cs & set(d['cells']))
            if n > bn:
                best, bn = d['order'], n
        a['door'] = best
        if best is None or bn < len(cs):
            problems.append('revealed arrow %d: %d/%d cells inside door %s' % (aid, bn, len(cs), best))

    # keys -> rider (the arrow whose cells hold the key's cells)
    def rider(kcells):
        votes = {}
        for aid, a in arrows.items():
            n = len(set(kcells) & set(a['cells']))
            if n:
                votes[aid] = n
        return max(votes, key=lambda x: (votes[x], -x)) if votes else None
    keys = []
    for kc in keys_start:
        keys.append(dict(cells=kc, rider=rider(kc), start=True))
    for k, s in key_seen.items():
        kc = sorted(k)
        if any(set(kc) & set(x['cells']) for x in keys):
            continue
        rd = rider(kc)
        if rd is None:
            problems.append('key %s rides no arrow' % kc)
        keys.append(dict(cells=kc, rider=rd, start=False, first_round=s['first'], shot=s['shot']))
    tapes = []
    for k, s in tape_seen.items():
        tc = sorted(k)
        if any(set(tc) & set(t) for t in tapes_start):
            continue
        members = sorted(aid for aid, a in arrows.items() if set(tc) & set(a['cells']))
        tapes.append(dict(cells=tc, members=members, first_round=s['first'], shot=s['shot']))

    # log cross-check (the run's time window)
    ts = [os.path.getmtime(f) for f in files]
    logs = log_units(L, min(ts), max(ts)) if ts else []
    known_sets = set(known)
    matched, unmatched = set(), []
    # one shift per logged tap batch: batches share a read -> group by 'round' + time
    batches = {}
    for r in logs:
        batches.setdefault((r.get('round'), int(r['t'])), []).append(r)
    for key, recs in batches.items():
        cl = [[tuple(c) for c in r['cells']] for r in recs]
        (dx, dy), n = best_shift(cl, known_sets)
        for cs in cl:
            k = frozenset((c + dx, r + dy) for c, r in cs)
            if k in known:
                matched.add(known[k])
            else:
                unmatched.append(sorted(k)[:3])
    never = sorted(set(arrows) - matched)
    return dict(level=L, runs=RUNS[L], shots=len(files), clean_reads=len(rounds), skipped=skipped, rounds=rounds,
                doors=doors, hidden=[dict(id=a['id'], cells=a['cells'], dir=a['dir'], door=a['door'], round=a['round'],
                                          shot=a.get('shot')) for a in arrows.values() if not a['start']],
                keys=keys, tapes=tapes, start_arrows=len(start['arrows']),
                log=dict(tapped_units=len(logs), matched=len(matched), unmatched=unmatched[:10],
                         unmatched_count=len(unmatched), never_tapped=never),
                problems=problems)


# ------------------------------------------------------------------------------------------------ phone session 2 (L62+)
# The session-2 door levels. Their start reads merge touching doors (and doors touching boxes) into one blob, so the door
# RECTANGLES are curated here (start frame, c0, r0, c1, r1; measured on the start shot, the blob cell counts agree) and each
# door's opening is detected on the round shots as "its rectangle holds no door/box ink any more". Everything else is the
# same idea as backfill(): new arrows that lie wholly inside an opened door are the arrows it hid; keys and tapes that appear
# inside it ride them; session 2 adds PIPES found inside a door (L69: a pipe under a door, revealed by its burst).
# Reads apply research/bot/overrides (arrows under keys that the reader cannot trace, verified by eye in session 2).
RUNS_S2 = {62: ['111843'], 63: ['112956'], 65: ['122221'], 66: ['122659'], 69: ['124510', '124847'], 83: ['141306']}
DOOR_RECTS_S2 = {
    62: [(0, 0, 16, 10), (9, 21, 25, 33)],                          # top-left, bottom-right (start blobs 187 + 221 cells)
    63: [(13, 0, 21, 27)],                                          # the right column (252)
    65: [(0, 0, 12, 33), (13, 7, 25, 16)],                          # left column 13x34 + right middle 13x10 (shots/421; the
                                                                    # 767-cell blob = these + box 22 (13x7) + box 52 (13x8))
    66: [(0, 6, 19, 13)],                                           # 20x8 (160; the blob's 161st cell is the key)
    69: [(5, 0, 20, 6), (0, 26, 7, 33), (8, 26, 17, 33), (18, 26, 25, 33)],   # top + three side by side at the bottom
                                                                    # (frame x at 7.5 / 17.5 cells on shots/450)
    83: [(13, 0, 21, 27)],
}


def read_s2(path, start, L):
    im = np.array(Image.open(path).convert('RGB')).astype(np.int16)
    ok, why, _ = bot.guard(im)
    if not ok:
        return None, 'guard: ' + why
    try:
        b = bot.read_board(im)
        b = bot.apply_overrides(im, b, L)
    except Exception as e:
        return None, 'read: %s' % e
    fit = b['fit']
    c0 = int(round((start['origin_pt'][0] * bot.SCALE - fit['x0']) / fit['pitch']))
    r0 = int(round((start['origin_pt'][1] * bot.SCALE - fit['y0']) / fit['pitch']))

    def m(cells):
        return [(c - c0, r - r0) for c, r in cells]
    arrows = [dict(cells=m(a['cells']), dir=a['dir']) for a in b['arrows']]
    obst = [dict(kind=o['kind'], cells=m(o['cells'])) for o in b['obstacles']]
    # anomalies (a stroke the reader could not resolve: mid-animation, a key or badge touching it) do not drop the read in
    # session 2 (most reads have one): the unresolved strokes are not in `arrows`; what the read adds is cross-checked
    # (no overlaps, the overlay proof of every door: tools/levels/render.py --reveals via design/tools/overlay_recast.py)
    return dict(arrows=arrows, obstacles=obst, shift=(c0, r0), pitch=fit['pitch'], anomalies=len(b['anomalies'])), None


# Arrows that run under a door but poke out of it (start frame cells that are visible at the start as head-less stubs):
# L62's 53-cell key arrow humps twice over the bottom door's top frame at row 20 (shots meta-058 / 111843-r04, by eye).
STUBS_S2 = {62: {(12, 20), (13, 20), (14, 20), (15, 20)}}


def backfill_s2(L, runs=None, rects_table=None, reader=None, stubs=None, max_anomalies=None, key_cells=(1, 2)):
    runs = RUNS_S2 if runs is None else runs
    rects_table = DOOR_RECTS_S2 if rects_table is None else rects_table
    reader = read_s2 if reader is None else reader
    stubs_table = STUBS_S2 if stubs is None else stubs
    start = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    files = []
    for run in runs[L]:
        files += sorted(glob.glob(os.path.join(RESEARCH, 'bot', 'tmp', 'L%03d-%s-r*.png' % (L, run))))
    rects = [set((c, r) for c in range(a, cc + 1) for r in range(b_, rr + 1)) for a, b_, cc, rr in rects_table[L]]
    known = {frozenset(map(tuple, a['cells'])): a['id'] for a in start['arrows']}
    arrows = {a['id']: dict(id=a['id'], cells=[tuple(c) for c in a['cells']], dir=a['dir'], start=True)
              for a in start['arrows']}
    next_id = max(arrows) + 1
    opened = [None] * len(rects)          # (read index, shot)
    rounds, skipped, problems = [], [], []
    keys_seen, tapes_seen, pipes_seen = {}, {}, {}
    for f in files:
        r, why = reader(f, start, L)
        name = os.path.basename(f)
        if r is None:
            skipped.append((name, why))
            continue
        if max_anomalies is not None and r['anomalies'] > max_anomalies:
            skipped.append((name, 'anomalies %d (mid-animation read)' % r['anomalies']))
            continue
        ri = len(rounds)
        shut = set()
        for o in r['obstacles']:
            if o['kind'] in ('door', 'box', 'box_part'):
                shut |= set(o['cells'])
        for k, R in enumerate(rects):
            if opened[k] is None and len(R & shut) < 0.5 * len(R):
                opened[k] = (ri, name)
        new = []
        for a in r['arrows']:
            k = frozenset(a['cells'])
            if k in known:
                continue
            stubs = stubs_table.get(L, set())
            host = [j for j, R in enumerate(rects) if set(a['cells']) <= R | stubs and len(set(a['cells']) & R) > 0]
            clash = [x for x in arrows.values() if not x['start'] and set(x['cells']) & set(a['cells'])]
            if clash:
                problems.append('%s: new arrow %s..%s overlaps revealed arrow %s (kept the earlier read)' % (
                    name, a['cells'][0], a['cells'][-1], [x['id'] for x in clash]))
                continue
            if not host:
                problems.append('%s: new arrow %s..%s outside every door (misread?) ignored' % (name, a['cells'][0],
                                                                                            a['cells'][-1]))
                continue
            aid = next_id
            next_id += 1
            known[k] = aid
            arrows[aid] = dict(id=aid, cells=a['cells'], dir=a['dir'], start=False, door=host[0], round=ri, shot=name)
            new.append(aid)
            if opened[host[0]] is None:
                problems.append('%s: arrow %d inside door %d before it opened' % (name, aid, host[0]))
        for o in r['obstacles']:
            k = frozenset(o['cells'])
            if o['kind'] == 'key' and key_cells[0] <= len(o['cells']) <= key_cells[1]:
                keys_seen.setdefault(k, dict(first=ri, shot=name))
            if o['kind'] == 'tape_pink' and o['cells']:
                tapes_seen.setdefault(k, dict(first=ri, shot=name))
            if o['kind'] == 'pipe' and o['cells']:
                host = [j for j, R in enumerate(rects) if set(o['cells']) <= R]
                if host:
                    pipes_seen.setdefault(k, dict(first=ri, shot=name, door=host[0]))
        rounds.append(dict(shot=name, arrows=len(r['arrows']), anomalies=r['anomalies'],
                           open=[x is not None for x in opened], new=new))
    order = sorted(range(len(rects)), key=lambda k: (opened[k][0] if opened[k] else 10 ** 6, k))
    doors = []
    for rank, k in enumerate(order):
        c0, r0, c1, r1 = rects_table[L][k]
        doors.append(dict(cells=sorted(rects[k]), rect=[c0, r0, c1, r1], order=rank, index=k,
                          opened_round=opened[k][0] if opened[k] else None, shot=opened[k][1] if opened[k] else None))
        if not opened[k]:
            problems.append('door %s never seen open' % [c0, r0, c1, r1])
    rank_of = {d['index']: d['order'] for d in doors}

    def rider(kcells):
        votes = {}
        for aid, a in arrows.items():
            n = len(set(kcells) & set(a['cells']))
            if n:
                votes[aid] = n
        return max(votes, key=lambda x: (votes[x], -x)) if votes else None
    keys = []
    for o in start['obstacles']:
        if o['kind'] == 'key':
            keys.append(dict(cells=sorted(map(tuple, o['cells'])), rider=rider([tuple(c) for c in o['cells']]), start=True))
    for k, s in sorted(keys_seen.items(), key=lambda x: x[1]['first']):
        kc = sorted(k)
        if any(set(kc) & set(x['cells']) for x in keys):
            continue
        rd = rider(kc)
        if rd is None:
            problems.append('key %s rides no arrow' % kc)
        keys.append(dict(cells=kc, rider=rd, start=arrows.get(rd, {}).get('start', False), first_round=s['first'],
                         shot=s['shot']))
    tapes_start = [set(map(tuple, o['cells'])) for o in start['obstacles'] if o['kind'] == 'tape_pink']
    tapes = []
    for k, s in tapes_seen.items():
        tc = sorted(k)
        if any(set(tc) & t for t in tapes_start):
            continue
        members = sorted(aid for aid, a in arrows.items() if set(tc) & set(a['cells']))
        if not members or any(arrows[m]['start'] for m in members):
            continue
        tapes.append(dict(cells=tc, members=members, first_round=s['first'], shot=s['shot']))
    pipes = [dict(cells=sorted(k), door=rank_of[s['door']], first_round=s['first'], shot=s['shot'])
             for k, s in pipes_seen.items()]
    hidden = [dict(id=a['id'], cells=a['cells'], dir=a['dir'], door=rank_of[a['door']], round=a['round'], shot=a['shot'])
              for a in arrows.values() if not a['start']]
    for d in doors:                         # at the first read with the door open, every arrow it hid is still there
        late = [h['id'] for h in hidden if h['door'] == d['order'] and d['opened_round'] is not None
                and h['round'] > d['opened_round']]
        if late:
            problems.append('door %d: arrows %s first read after its opening read (a skipped round?)' % (d['order'], late))
    return dict(level=L, runs=runs[L], shots=len(files), clean_reads=len(rounds), skipped=skipped, rounds=rounds,
                doors=doors, hidden=hidden, keys=keys, tapes=tapes, pipes=pipes, start_arrows=len(start['arrows']),
                problems=problems, session=2)


# ------------------------------------------------------------------------------------------------ phone session 3 (L84+)
# CONTENT RECAST 2 (research/levels.md "L84 (phone session 3)"; research/phone-session3-progress.md). Same method as session 2
# (curated door rectangles, opening = no door ink left in the rectangle), with two session-3 differences:
#   * every round shot is read on the START shot's grid (research/bot/go3.py --fit-from: the zoom never changes inside a level;
#     a free fit drifted on L102's lavender platform), and with research/bot/corners.py's reader (L89/L93 carry corners; the
#     plain reader traces pseudo-arrows on a corner plate, and L89's top-left corner lies UNDER its left door);
#   * ELEVATORS (v552's debut at L100): the hidden layer = the arrows that appear inside the platform once it opens (the bot's
#     own `-open1` dump right after the last platform arrow left + every later round shot of the run).
RUNS_S3 = {86: ['145847'], 89: ['150741'], 93: ['152916'], 98: ['155420']}
DOOR_RECTS_S3 = {
    86: [(0, 6, 19, 13)],                                            # = L66 (the blob's 161st cell is the key), shots/626
    89: [(0, 0, 13, 12), (14, 0, 25, 12)],                           # 14x13 + 12x13 side by side (blob 338; frame x 13.5
                                                                     # cells on shots/644; a hidden U runs up col 13)
    93: [(0, 19, 6, 25), (7, 16, 13, 25), (14, 13, 20, 25)],         # rising staircase 7x7 / 7x10 / 7x13 (blob 210), shots/670
    98: [(0, 7, 11, 22), (12, 7, 23, 22)],                           # two 12x16 doors side by side (blob 384), shots/703
}
BLOB_KEY_CELLS_S3 = {86: {(7, 5)}}                                   # L86 = L66: the key's 2nd cell, read as door
ELEVATOR_RUNS_S3 = {100: ['160659'], 101: ['161636'], 102: ['162126', '162556'], 103: ['163321']}


def s3_reader(L):
    """read(path, start, L) for session 3: corners.py's reader on the start shot's grid, overrides applied."""
    import corners                                  # research/bot/corners.py patches bot.read_board/bot.ray on import:
    bot.read_board, bot.ray = corners._read, corners._ray      # undo that globally, call its reader explicitly
    start = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    im0 = np.array(Image.open(os.path.join(APP, start['shot'].replace('apps/mazeout/', ''))).convert('RGB')).astype(np.int16)
    fit0 = corners.read_board(im0)['fit']

    def read_s3(path, start_, L_):
        im = np.array(Image.open(path).convert('RGB')).astype(np.int16)
        ok, why, _ = bot.guard(im)
        if not ok:
            return None, 'guard: ' + why
        try:
            b = corners.read_board(im, fit=fit0)
            b = bot.apply_overrides(im, b, L_)
        except Exception as e:
            return None, 'read: %s' % e
        fit = b['fit']
        c0 = int(round((start_['origin_pt'][0] * bot.SCALE - fit['x0']) / fit['pitch']))
        r0 = int(round((start_['origin_pt'][1] * bot.SCALE - fit['y0']) / fit['pitch']))

        def m(cells):
            return [(c - c0, r - r0) for c, r in cells]
        return dict(arrows=[dict(cells=m(a['cells']), dir=a['dir']) for a in b['arrows']],
                    obstacles=[dict(kind=o['kind'], cells=m(o['cells'])) for o in b['obstacles']],
                    shift=(c0, r0), pitch=fit['pitch'], anomalies=len(b['anomalies'])), None
    return read_s3


def backfill_s3(L):
    """Session-3 door levels: backfill_s2's method with the session-3 reader; the curated rectangles must tile the start
    read's door blob (its extra cells may only be key cells)."""
    start = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    blob = {tuple(c) for o in start['obstacles'] if o['kind'] == 'door' for c in o['cells']}
    keyc = {tuple(c) for o in start['obstacles'] if o['kind'] == 'key' for c in o['cells']}
    rects = [(c, r) for a, b_, cc, rr in DOOR_RECTS_S3[L] for c in range(a, cc + 1) for r in range(b_, rr + 1)]
    res = backfill_s2(L, runs=RUNS_S3, rects_table=DOOR_RECTS_S3, reader=s3_reader(L), stubs={}, max_anomalies=3,
                      key_cells=(2, 2))     # a key spans 2 cells; 1-cell 'keys' are door-burst debris
    if len(rects) != len(set(rects)):
        res['problems'].append('curated door rectangles overlap')
    keyc |= BLOB_KEY_CELLS_S3.get(L, set())
    if not set(rects) <= blob or not (blob - set(rects)) <= keyc:
        res['problems'].append('curated rectangles (%d cells) do not tile the start door blob (%d cells; %d outside, '
                               '%d uncovered non-key)' % (len(rects), len(blob), len(set(rects) - blob),
                                                          len(blob - set(rects) - keyc)))
    res['session'] = 3
    return res


def backfill_elevator(L):
    """v552 elevator levels (session 3): the platform = the start read's lavender 'elevator' cells; its layer-1 arrows =
    the start arrows wholly on it; the hidden layer = the arrows that appear wholly on it in the `-open1` dump (taken by
    research/bot/go3.py --elevator right after the platform's last arrow left) or on any later round shot of the run."""
    start = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
    plat = {tuple(c) for o in start['obstacles'] if o['kind'] == 'elevator' for c in o['cells']}
    known = {frozenset(map(tuple, a['cells'])): a['id'] for a in start['arrows']}
    platform = sorted(a['id'] for a in start['arrows'] if set(map(tuple, a['cells'])) <= plat)
    problems, hidden, seen = [], [], {}
    op = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d-open1.json' % L)))
    sources = [('L%03d-open1.json' % L, [dict(cells=[tuple(c) for c in a['cells']], dir=a['dir']) for a in op['arrows']])]
    reader = s3_reader(L)
    files = []
    for run in ELEVATOR_RUNS_S3[L]:
        files += sorted(glob.glob(os.path.join(RESEARCH, 'bot', 'tmp', 'L%03d-%s-r*.png' % (L, run))))
    for f in files:
        r, why = reader(f, start, L)
        if r is not None:
            sources.append((os.path.basename(f), r['arrows']))
    first_open = None
    for name, arrows in sources:
        for a in arrows:
            k = frozenset(a['cells'])
            if k in known or k in seen:
                continue
            if not set(a['cells']) <= plat:
                continue                                  # a read of the maze around it (the start read holds those)
            clash = [h for h in hidden if set(h['cells']) & set(a['cells'])]
            if clash:
                problems.append('%s: %s..%s overlaps hidden %s (kept the earlier read)' % (
                    name, a['cells'][0], a['cells'][-1], [h['id'] for h in clash]))
                continue
            seen[k] = len(hidden)
            hidden.append(dict(id=len(hidden), cells=list(a['cells']), dir=a['dir'], source=name))
            first_open = first_open or name
    late = sorted({h['source'] for h in hidden if h['source'] != sources[0][0]})
    if late:
        problems.append('hidden arrows first read on round shots after the open dump: %s' % late)
    return dict(level=L, kind='elevator', runs=ELEVATOR_RUNS_S3[L], shots=len(files), platform_cells=len(plat),
                platform=platform, hidden=hidden, problems=problems, session=3)


def main():
    levels = [int(x) for x in sys.argv[1:]] or sorted(RUNS) + sorted(RUNS_S2) + sorted(RUNS_S3) + sorted(ELEVATOR_RUNS_S3)
    os.makedirs(OUT, exist_ok=True)
    for L in [x for x in levels if x in RUNS_S3]:
        res = backfill_s3(L)
        with open(os.path.join(OUT, 'L%03d.json' % L), 'w') as f:
            json.dump(res, f, indent=1, default=list)
        print('S3 L%d: %d shots, %d clean; start %d, hidden %d; doors %s; keys %d (%d hidden); tapes %d; pipes %d' % (
            L, res['shots'], res['clean_reads'], res['start_arrows'], len(res['hidden']),
            [(d['rect'], d['opened_round']) for d in res['doors']], len(res['keys']),
            sum(1 for k in res['keys'] if not k['start']), len(res['tapes']), len(res['pipes'])))
        for p in res['problems']:
            print('   problem:', p)
    for L in [x for x in levels if x in ELEVATOR_RUNS_S3 and x not in RUNS_S3]:
        res = backfill_elevator(L)
        with open(os.path.join(OUT, 'L%03d.json' % L), 'w') as f:
            json.dump(res, f, indent=1, default=list)
        print('S3 L%d elevator: platform %d cells, %d platform arrows, %d hidden arrows (%d shots)' % (
            L, res['platform_cells'], len(res['platform']), len(res['hidden']), res['shots']))
        for p in res['problems']:
            print('   problem:', p)
    levels = [L for L in levels if L not in RUNS_S3 and L not in ELEVATOR_RUNS_S3]
    s2 = [L for L in levels if L in RUNS_S2]
    levels = [L for L in levels if L not in RUNS_S2]
    for L in s2:
        res = backfill_s2(L)
        with open(os.path.join(OUT, 'L%03d.json' % L), 'w') as f:
            json.dump(res, f, indent=1, default=list)
        print('S2 L%d: %d shots, %d clean; start %d, hidden %d; doors %s; keys %d (%d hidden); tapes %d; pipes %d' % (
            L, res['shots'], res['clean_reads'], res['start_arrows'], len(res['hidden']),
            [(d['rect'], d['opened_round']) for d in res['doors']], len(res['keys']),
            sum(1 for k in res['keys'] if not k['start']), len(res['tapes']), len(res['pipes'])))
        for p in res['problems']:
            print('   problem:', p)
    if not levels:
        return
    print('%-4s %6s %6s %6s %6s %5s %5s %8s %9s %s' % ('L', 'shots', 'clean', 'start', 'hidden', 'doors', 'keys',
                                                        'log ok', 'untapped', 'problems'))
    for L in levels:
        res = backfill(L)
        with open(os.path.join(OUT, 'L%03d.json' % L), 'w') as f:
            json.dump(res, f, indent=1, default=list)
        print('%-4d %6d %6d %6d %6d %5d %5d %8s %9d %s' % (
            L, res['shots'], res['clean_reads'], res['start_arrows'], len(res['hidden']), len(res['doors']),
            len(res['keys']), '%d/%d' % (res['log']['matched'], res['log']['tapped_units']),
            len(res['log']['never_tapped']), '; '.join(res['problems'])[:160]))


if __name__ == '__main__':
    main()
