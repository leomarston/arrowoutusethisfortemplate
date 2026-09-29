#!/usr/bin/env python3
"""validate_levels.py — the content validator for design/levels.json (SPEC-gameplay §14.4, LEVELS.md §5).

Every level must: parse in the bundle schema; be structurally sound; carry well-formed obstacles; have legal values; be
SOLVED by the greedy solver under the rules (arrowcore = SPEC-gameplay §3); use every obstacle it has (every pipe passed,
every box broken, every door opened, the elevator activated) in that solution; leave the 0.6 s/tap bot >= 20 % of the
timer. Across levels: numbering 1..authoredEnd, unlock cards exactly at each feature's first appearance, sessions and
tutorials pointing at real content, no two boards identical (offset-free, rotations and mirrors: repeats.py).

  python3 design/tools/validate_levels.py [design/levels.json]        -> exit 0 when clean; report on stdout and in
                                                                         design/tools/work/validate_report.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arrowcore as ac  # noqa: E402

LEVEL_KEYS = {'schema', 'level', 'source', 'capture', 'cols', 'rows', 'mask', 'timer_s', 'hearts', 'tag', 'arrows',
              'obstacles', 'unlock', 'seed', 'metrics'}
ARROW_KEYS = {'id', 'cells', 'dir', 'layer', 'hidden_by'}
OBST_KEYS = {'id', 'kind', 'cells', 'arrows', 'ends', 'counter', 'counter_at', 'order', 'opens', 'turn', 'reveals',
             'sprite'}
KINDS = {'tape', 'door', 'key', 'pipe', 'box', 'curtain', 'elevator', 'corner'}
PREFIX = dict(tape='t', door='d', key='k', pipe='p', box='b', curtain='c', elevator='e', corner='x')
FEATURE_OF = dict(tape='linked', door='door', pipe='pipe', box='box', curtain='box', elevator='elevator',
                  corner='corner')


def is_rect(cells):
    cs = {tuple(c) for c in cells}
    if not cs:
        return False
    xs, ys = [c[0] for c in cs], [c[1] for c in cs]
    return len(cs) == (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)


def check_level(l, errs, warns):
    L = l.get('level')
    E = lambda m: errs.append('L%s: %s' % (L, m))   # noqa: E731
    W_ = lambda m: warns.append('L%s: %s' % (L, m))  # noqa: E731
    for k in l:
        if k not in LEVEL_KEYS and not k.startswith('_'):
            E('unknown key %s' % k)
    for k in ('level', 'source', 'cols', 'rows', 'timer_s', 'hearts', 'tag', 'arrows', 'obstacles'):
        if k not in l:
            E('missing %s' % k)
            return None
    if l['source'] not in ('recorded', 'video', 'designed', 'generated'):
        E('source %s' % l['source'])
    if l['source'] in ('recorded', 'video') and not l.get('capture'):
        E('no capture for a %s level' % l['source'])
    if not (60 <= l['timer_s'] <= 600):
        E('timer_s %s' % l['timer_s'])
    if l['hearts'] != 3:
        E('hearts %s' % l['hearts'])
    if l['tag'] not in ('normal', 'hard', 'superHard'):
        E('tag %s' % l['tag'])
    if not (2 <= l['cols'] <= 40 and 2 <= l['rows'] <= 40):
        E('grid %sx%s' % (l['cols'], l['rows']))
    if l['cols'] > 26:
        W_('cols %d > 26: fit pitch below the 14.04 pt zoom floor' % l['cols'])
    for a in l['arrows']:
        for k in a:
            if k not in ARROW_KEYS:
                E('arrow %s unknown key %s' % (a.get('id'), k))
    for p in ac.structural_problems(l):
        E(p)
    A = {a['id']: a for a in l['arrows']}
    O = {}
    for o in l['obstacles']:
        for k in o:
            if k not in OBST_KEYS:
                E('obstacle %s unknown key %s' % (o.get('id'), k))
        if o.get('kind') not in KINDS:
            E('obstacle %s kind %s' % (o.get('id'), o.get('kind')))
            continue
        if o['id'] in O:
            E('duplicate obstacle id %s' % o['id'])
        if not o['id'].startswith(PREFIX[o['kind']]):
            W_('obstacle %s id prefix vs kind %s' % (o['id'], o['kind']))
        O[o['id']] = o
    stubs = []                                  # (door, hidden arrow, its cells outside the door): v552 L62's humps
    visible_cells = {}
    for a in l['arrows']:
        if a.get('hidden_by') is None and (a.get('layer', 1) or 1) == 1:
            for c in a['cells']:
                visible_cells[tuple(c)] = a['id']
    hider_cells = {}
    door_sets = {o['id']: {tuple(c) for c in o['cells']} for o in O.values() if o['kind'] == 'door'}
    under = {}                                  # obstacle id -> the door it lies under (v552 L69: pipes under doors)
    for o in O.values():
        if o['kind'] in ('box', 'curtain', 'pipe', 'corner'):
            host = [d for d, ds in door_sets.items() if {tuple(c) for c in o['cells']} <= ds]
            if host:
                under[o['id']] = host[0]
    for o in sorted(O.values(), key=lambda o: 0 if o['kind'] == 'door' else 1):
        k = o['kind']
        cs = [tuple(c) for c in o['cells']]
        if k in ('door', 'box', 'curtain', 'pipe', 'corner', 'elevator'):
            for c in cs:
                if not (0 <= c[0] < l['cols'] and 0 <= c[1] < l['rows']):
                    E('%s %s cell %s outside the grid' % (k, o['id'], c))
                if k in ('door', 'box', 'curtain', 'pipe', 'corner') and c in visible_cells:
                    E('%s %s covers visible arrow %s at %s' % (k, o['id'], visible_cells[c], c))
                if k != 'elevator':
                    if c in hider_cells and not (under.get(o['id']) == hider_cells[c]):
                        E('%s %s overlaps %s at %s' % (k, o['id'], hider_cells[c], c))
                    if c not in hider_cells:
                        hider_cells[c] = o['id']
        if k == 'tape':
            mem = o.get('arrows', [])
            if not (2 <= len(mem) <= 4):
                E('tape %s binds %d arrows' % (o['id'], len(mem)))
            ms = [A.get(m) for m in mem]
            if None in ms:
                E('tape %s: unknown member' % o['id'])
                continue
            dirs = {m['dir'] for m in ms}
            lens = {len(m['cells']) for m in ms}
            if len(dirs) != 1 or len(lens) != 1:
                E('tape %s members differ (dirs %s, lengths %s)' % (o['id'], dirs, lens))
            for m in ms:
                cs2 = [tuple(c) for c in m['cells']]
                if any(ac.dir_between(x, y) != m['dir'] for x, y in zip(cs2, cs2[1:])):
                    E('tape %s member %s is not straight' % (o['id'], m['id']))
            if len(cs) != len(mem) or {tuple(m['cells'][len(m['cells']) - 2]) for m in ms} != set(cs):
                E('tape %s tie cells %s are not each member\'s cell behind the head' % (o['id'], cs))
            if len({m.get('hidden_by') for m in ms}) != 1:
                E('tape %s members hidden differently' % o['id'])
        elif k in ('door', 'box', 'curtain'):
            if not is_rect(cs):
                E('%s %s is not a rectangle' % (k, o['id']))
            if k == 'door' and len(cs) < 4:
                E('door %s smaller than 2x2' % o['id'])
            rv = set(o.get('reveals', []))
            hid = {a['id'] for a in l['arrows'] if a.get('hidden_by') == o['id']}
            if rv != hid:
                E('%s %s reveals %s != arrows hidden by it %s' % (k, o['id'], sorted(rv), sorted(hid)))
            for aid in hid:
                out_cells = {tuple(c) for c in A[aid]['cells']} - set(cs)
                if out_cells and k != 'door':
                    E('%s %s: hidden arrow %s sticks out' % (k, o['id'], aid))
                elif out_cells:
                    stubs.append((o['id'], aid, out_cells))
            if k in ('box', 'curtain'):
                if not isinstance(o.get('counter'), int) or o['counter'] < 1:
                    E('%s %s counter %s' % (k, o['id'], o.get('counter')))
                elif o['counter'] >= len(l['arrows']):
                    E('%s %s counter %d >= %d arrows (never breaks)' % (k, o['id'], o['counter'], len(l['arrows'])))
        elif k == 'key':
            if len(o.get('arrows', [])) != 1 or o['arrows'][0] not in A:
                E('key %s rider %s' % (o['id'], o.get('arrows')))
                continue
            rc = [tuple(c) for c in A[o['arrows'][0]]['cells']]
            if len(cs) != 2 or not set(cs) <= set(rc):
                E('key %s cells %s not on its rider' % (o['id'], cs))
            if o.get('opens') and o['opens'] not in O:
                E('key %s opens unknown %s' % (o['id'], o['opens']))
        elif k == 'pipe':
            ends = o.get('ends', [])
            if len(ends) != 2:
                E('pipe %s has %d ends' % (o['id'], len(ends)))
                continue
            if any(ac.dir_between(x, y) is None for x, y in zip(cs, cs[1:])) or len(set(cs)) != len(cs):
                E('pipe %s cells are not an ordered 4-connected path' % o['id'])
            elif [tuple(ends[0]['cell']), tuple(ends[1]['cell'])] != [cs[0], cs[-1]]:
                E('pipe %s ends %s are not its extremities' % (o['id'], [e['cell'] for e in ends]))
            else:
                if ends[0]['out'] != ac.dir_between(cs[1], cs[0]) or ends[1]['out'] != ac.dir_between(cs[-2], cs[-1]):
                    E('pipe %s mouth directions do not continue the tube' % o['id'])
            if not isinstance(o.get('counter'), int) or not (1 <= o['counter'] <= 9):
                E('pipe %s counter %s' % (o['id'], o.get('counter')))
            at = o.get('counter_at')
            if not at or min(abs(at[0] - c[0]) + abs(at[1] - c[1]) for c in cs) > 1.0:
                E('pipe %s counter_at %s not on the tube' % (o['id'], at))
        elif k == 'elevator':
            if not is_rect(cs):
                E('elevator %s is not a rectangle' % o['id'])
            plat = {a['id'] for a in l['arrows'] if (a.get('layer', 1) or 1) == 1 and a.get('hidden_by') is None
                    and {tuple(c) for c in a['cells']} <= set(cs)}
            if set(o.get('arrows', [])) != plat:
                E('elevator %s platform %s != layer-1 arrows inside %s' % (o['id'], o.get('arrows'), sorted(plat)))
            l2 = {a['id'] for a in l['arrows'] if a.get('hidden_by') == o['id']}
            if set(o.get('reveals', [])) != l2:
                E('elevator %s reveals != its layer-2 arrows' % o['id'])
            for aid in l2:
                if (A[aid].get('layer') or 1) != 2:
                    E('elevator %s: hidden arrow %s not on layer 2' % (o['id'], aid))
        elif k == 'corner':
            if len(cs) != 1 or o.get('turn') not in ac.CORNER:
                E('corner %s' % o['id'])
    doors = [o for o in O.values() if o['kind'] == 'door']
    keys = [o for o in O.values() if o['kind'] == 'key']
    if len(keys) != len(doors):
        E('%d keys for %d doors' % (len(keys), len(doors)))
    if sorted(o.get('order', -1) for o in doors) != list(range(len(doors))):
        E('door orders %s' % sorted(o.get('order') for o in doors))
    for a in l['arrows']:
        hb = a.get('hidden_by')
        if hb is not None and hb not in O:
            E('arrow %s hidden by unknown %s' % (a['id'], hb))
    for d, aid, out_cells in stubs:
        # A hidden arrow may poke out of its door (drawn there at the start, as v552 L62 shows) only where no ray can
        # reach it while the door is shut: then whether a hidden cell blocks is moot (the rules keep hidden arrows inert).
        for c in out_cells:
            if c in visible_cells or c in hider_cells:
                E('door %s: hidden arrow %s pokes out onto an occupied cell %s' % (d, aid, c))
        bb = ac.Board(l)
        bb.hidden = set()
        bb.door_open = {x for x in door_sets if x != d}
        bb.box_broken = {o['id'] for o in O.values() if o['kind'] in ('box', 'curtain')}
        for a in l['arrows']:
            if a.get('hidden_by') == d:
                continue
            bb.alive = {a['id']}
            w = bb.walk(a['id'])
            hit = set(map(tuple, w['cells'])) & out_cells
            if hit:
                E('door %s: hidden arrow %s pokes out at %s, which arrow %s\'s ray can reach' % (d, aid, sorted(hit),
                                                                                             a['id']))
                break
    if errs and any(e.startswith('L%s:' % L) for e in errs):
        return None
    # full self-ray check (through pipes / corners): the walk from an empty board must never meet the arrow itself
    b0 = ac.Board(l)
    b0.hidden = set()
    for a in l['arrows']:
        others = set(A) - {a['id']}
        bb = b0.copy()
        bb.alive = {a['id']}
        bb.door_open = {o['id'] for o in doors}
        bb.box_broken = {o['id'] for o in O.values() if o['kind'] in ('box', 'curtain')}
        w = bb.walk(a['id'])
        if w['blocker'] == ('arrow', a['id']):
            E('arrow %s: its ray meets its own body (through a pipe/corner)' % a['id'])
    # no ray can loop: from an empty board (every door open, every box broken), with every pipe intact and with every pipe
    # broken, no walk may reach the pipe/corner hop guard (a corner or pipe cycle would freeze a game walk without one)
    if any(o['kind'] in ('pipe', 'corner') for o in O.values()):
        for broken in (False, True):
            bb = ac.Board(l)
            bb.hidden = set()
            bb.door_open = {o['id'] for o in doors}
            bb.box_broken = {o['id'] for o in O.values() if o['kind'] in ('box', 'curtain')}
            if broken:
                bb.pipe_broken = {o['id'] for o in O.values() if o['kind'] == 'pipe'}
            for a in l['arrows']:
                bb.alive = {a['id']}
                w = bb.walk(a['id'])
                if len(w['passages']) + len(w['corners']) >= ac.MAX_HOPS:
                    E('arrow %s: its ray loops through pipes/corners' % a['id'])
                    break
    # solvable with the greedy solver; the obstacles are all used
    g = ac.greedy(l)
    if not g['ok']:
        d = ac.dfs(l, budget=150000)
        E('greedy solver stuck with %d units left (DFS: %s)' % (len(g['stuck']), 'solvable' if d['ok'] else
                                                                  ('undecided' if d['exhausted'] else 'UNSOLVABLE')))
        return None
    b = ac.Board(l)
    used = dict(pipes={}, boxes=set(), doors=set(), elev=set(), keys=0)
    for u in g['order']:
        r = b.resolve(u[0])
        for m in r[1]:
            for p in r[2][m]['passages']:
                used['pipes'][p] = used['pipes'].get(p, 0) + 1
        ev = b.commit_exit(r[1], r[2])
        ev += b.open_pending_doors()
        for e in ev:
            if e[0] == 'boxBreak':
                used['boxes'].add(e[1])
            if e[0] == 'doorOpened':
                used['doors'].add(e[1])
            if e[0] == 'elevatorActivated':
                used['elev'].add(e[1])
            if e[0] == 'keyDispatched':
                used['keys'] += 1
    for o in O.values():
        if o['kind'] == 'pipe' and used['pipes'].get(o['id'], 0) == 0:
            E('pipe %s is never passed in the solution' % o['id'])
        if o['kind'] in ('box', 'curtain') and o['id'] not in used['boxes']:
            E('box %s never breaks in the solution' % o['id'])
        if o['kind'] == 'door' and o['id'] not in used['doors']:
            E('door %s never opens' % o['id'])
        if o['kind'] == 'elevator' and o['id'] not in used['elev']:
            E('elevator %s never activates' % o['id'])
    # no dead end: 40 seeded random play orders (any free unit, uniformly) must all clear a non-monotone board
    if any(o['kind'] in ('pipe', 'elevator', 'corner') for o in O.values()):
        from pathrandom import PathRandom
        rng = PathRandom(1000 + int(L))
        for _ in range(40):
            bb = ac.Board(l)
            while not bb.cleared():
                fu = bb.free_units()
                if not fu:
                    if bb.pending_doors:
                        bb.open_pending_doors()
                        continue
                    E('dead end: a random play order gets stuck with %d arrows left' % len(bb.alive))
                    break
                u, w = fu[rng.below(len(fu))]
                bb.commit_exit(u, w)
                bb.open_pending_doors()
            if not bb.cleared():
                break
    m = ac.metrics(l)
    if m['bot_time_left'] < 0.2 * l['timer_s']:
        E('bot at 0.6 s/tap keeps only %.0f s of %d' % (m['bot_time_left'], l['timer_s']))
    if l.get('metrics'):
        bm = ac.bundle_metrics(m)
        for k2, v in bm.items():
            if l['metrics'].get(k2) != v:
                E('metrics.%s %s != recomputed %s' % (k2, l['metrics'].get(k2), v))
                break
    return m


def board_key(l):
    """Offset-free: the arrow cells and the heads' directions, shifted to the board's top-left arrow cell (v552 repeats boards
    cell for cell 20 levels later; a repeat read in another frame must still be caught)."""
    cs = [tuple(c) for a in l['arrows'] for c in a['cells']]
    x0, y0 = min(c[0] for c in cs), min(c[1] for c in cs)
    return frozenset(((c[0] - x0, c[1] - y0), a['dir']) for a in l['arrows'] for c in a['cells'][-1:]) | \
        frozenset((c[0] - x0, c[1] - y0) for c in cs)


def repeated_boards(levels):
    """[(later level, first level)] for every board that repeats an earlier one (repeats.scan: offset-free, rotations and
    mirrors, visible or full key). Superset of board_key's offset-free identity."""
    import repeats
    reps, _ = repeats.scan(levels, label=lambda l: l['level'])
    return [(a, b) for a, b, _, _ in reps]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), 'levels.json')
    doc = json.load(open(path))
    errs, warns = [], []
    levels = doc['levels']
    nums = [l['level'] for l in levels]
    end = doc.get('authoredEnd', len(levels))
    if nums != list(range(1, end + 1)):
        errs.append('level numbers are not 1..%d' % end)
    table = []
    for l in levels:
        m = check_level(l, errs, warns)
        table.append((l['level'], m))
    # unlock cards at first appearance
    first = {}
    for l in levels:
        for o in l['obstacles']:
            f = FEATURE_OF.get(o['kind'])
            if f and f not in first:
                first[f] = l['level']
    unlocks = {u['feature']: u for u in doc.get('unlocks', [])}
    for f, n in sorted(first.items(), key=lambda x: x[1]):
        lv = levels[n - 1]
        if lv.get('unlock') != f:
            errs.append('L%d: first %s but unlock=%s' % (n, f, lv.get('unlock')))
        if f not in unlocks or unlocks[f]['level'] != n:
            errs.append('unlocks.json: %s should be at L%d (%s)' % (f, n, unlocks.get(f, {}).get('level')))
    for l in levels:
        if l.get('unlock') and first.get(l['unlock']) != l['level']:
            errs.append('L%d: unlock %s is not a first appearance' % (l['level'], l['unlock']))
    for f, u in unlocks.items():
        if f not in first:
            errs.append('unlocks.json: %s never appears' % f)
    # sessions / tutorials
    for s in doc.get('sessions', []):
        for n in s['levels']:
            if not (1 <= n <= end):
                errs.append('session %s level %d' % (s['id'], n))
    for t in doc.get('tutorials', []):
        lv = levels[t['level'] - 1]
        if t.get('hand') and t['hand']['arrow'] not in {a['id'] for a in lv['arrows']}:
            errs.append('tutorial %s points at a missing arrow' % t['id'])
    # no repeated board (SPEC.md §5 item 28): offset-free, under the 8 symmetries of the square, on the start-visible arrows
    # or on every layer (repeats.py); the first occurrence wins
    for later, first in repeated_boards(levels):
        errs.append('L%d repeats L%d' % (later, first))
    rep = dict(file=path, levels=len(levels), errors=errs, warnings=warns, first_appearance=first,
               table=[dict(level=n, rounds=m['rounds'], free=m['free_at_start'], units=m['_units'],
                           arrows=m['arrows'], bot_time_left=m['bot_time_left']) if m else dict(level=n, failed=True)
                      for n, m in table])
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    ac.dump(rep, os.path.join(HERE, 'work', 'validate_report.json'))
    print('validated %d levels: %d error(s), %d warning(s); first appearances %s' % (
        len(levels), len(errs), len(warns), first))
    for e in errs[:60]:
        print('ERROR', e)
    for w in warns[:20]:
        print('WARN', w)
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
