#!/usr/bin/env python3
"""Verifier's validator + solver for level JSONs (own implementation; does not import bot.py / vextract / bcheck / ccheck / dcheck).

usage: validate.py FILE.json ... [--random N] [--json OUT]
Checks
  schema: every key of the phone schema (research/levels/L032.json) present, with the phone's types;
  invariants: ids 0..n-1, cells in [0,cols)x[0,rows), 4-adjacent steps, no self-overlap, no two start-layer arrows share a cell,
    dir = last step, cols/rows tight, arrows not on box/pipe cells, hidden arrows inside their platform, ties: one cell per bound
    arrow, on cell index len-2, bound arrows straight/parallel/equal length/same dir;
  solver (rules as measured in the videos): ray from the head; blocked by any live arrow cell, an unbroken box, a live pipe cell
    unless it enters a mouth against the mouth's out direction (then it continues from the other mouth in that mouth's out
    direction; one pass per arrow); boxes break when removed arrows >= counter (every bundle member counts); a pipe breaks after
    `counter` passes; empty elevator platform cells never block; a platform's hidden layer goes live when its last platform arrow
    leaves; a Linked bundle leaves only if every member is free. Greedy rounds (all free units per round) -> solvable + depth;
    --random N random free-move orders -> dead ends.
"""
import json, sys, random, argparse, os

PHONE_REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'L032.json')
D = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
OPP = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}


def schema_check(d, ref):
    errs = []
    for k, v in ref.items():
        if k not in d:
            errs.append(f'missing key {k}')
            continue
        if v is not None and d[k] is not None and type(v) != type(d[k]) and not (isinstance(v, (int, float)) and isinstance(d[k], (int, float))):
            errs.append(f'type of {k}: {type(d[k]).__name__} vs phone {type(v).__name__}')
    for a in d.get('arrows', []):
        for k in ('id', 'cells', 'dir'):
            if k not in a:
                errs.append(f'arrow missing {k}')
    return errs


def invariants(d):
    errs, notes = [], []
    arrows = d['arrows']
    ids = [a['id'] for a in arrows]
    if sorted(ids) != list(range(len(arrows))):
        errs.append('ids are not 0..n-1')
    cols, rows = d['cols'], d['rows']
    occ = {}
    boxes = [o for o in d['obstacles'] if o['kind'] in ('box', 'curtain')]
    boxcells = {tuple(c) for o in boxes for c in o['cells']}
    pipecells = {tuple(c) for p in d.get('pipes', []) for c in p['cells']}
    elevs = d.get('elevators') or []
    allcells = set()
    for a in arrows:
        cs = [tuple(c) for c in a['cells']]
        if len(cs) < 2:
            errs.append(f'arrow {a["id"]} has {len(cs)} cell')
            continue
        if len(set(cs)) != len(cs):
            errs.append(f'arrow {a["id"]} overlaps itself')
        for (c1, r1), (c2, r2) in zip(cs, cs[1:]):
            if abs(c1 - c2) + abs(r1 - r2) != 1:
                errs.append(f'arrow {a["id"]} step {(c1, r1)}->{(c2, r2)} not adjacent')
        for c in cs:
            if not (0 <= c[0] < cols and 0 <= c[1] < rows):
                errs.append(f'arrow {a["id"]} cell {c} out of bounds')
            allcells.add(c)
        last = (cs[-1][0] - cs[-2][0], cs[-1][1] - cs[-2][1])
        if D.get(a['dir']) != last:
            errs.append(f'arrow {a["id"]} dir {a["dir"]} != last step {last}')
        if a.get('layer', 1) == 1:
            for c in cs:
                if c in occ:
                    errs.append(f'arrows {occ[c]} and {a["id"]} share {c}')
                occ[c] = a['id']
                if c in boxcells:
                    errs.append(f'arrow {a["id"]} on a box cell {c}')
                if c in pipecells:
                    errs.append(f'arrow {a["id"]} on a pipe cell {c}')
        # ray through its own body
        dx, dy = D[a['dir']]
        x, y = cs[-1]
        own = set(cs[:-1])
        for _ in range(max(cols, rows) + 2):
            x, y = x + dx, y + dy
            if (x, y) in own:
                errs.append(f'arrow {a["id"]} ray crosses its own body')
                break
    # hidden layers: inside their platform, no overlap among themselves
    for k, e in enumerate(elevs):
        ec = {tuple(c) for c in e['cells']}
        hid = [a for a in arrows if a.get('layer', 1) != 1 and a.get('under_elevator') == k]
        if sorted(a['id'] for a in hid) != sorted(e.get('hidden_arrow_ids', [])):
            errs.append(f'elevator {k}: hidden_arrow_ids != layer-2 arrows')
        seen = {}
        for a in hid:
            for c in map(tuple, a['cells']):
                if c not in ec:
                    errs.append(f'hidden arrow {a["id"]} cell {c} outside platform {k}')
                if c in seen:
                    errs.append(f'hidden arrows {seen[c]} and {a["id"]} share {c}')
                seen[c] = a['id']
        plat = [a['id'] for a in arrows if a.get('layer', 1) == 1 and set(map(tuple, a['cells'])) & ec]
        if sorted(plat) != sorted(e.get('arrow_ids', [])):
            notes.append(f'elevator {k}: arrows touching the platform {sorted(plat)} vs arrow_ids {sorted(e.get("arrow_ids", []))}')
        inside = [a['id'] for a in arrows if a.get('layer', 1) == 1 and set(map(tuple, a['cells'])) <= ec]
        if sorted(inside) != sorted(e.get('arrow_ids', [])):
            notes.append(f'elevator {k}: arrows wholly inside {sorted(inside)} vs arrow_ids {sorted(e.get("arrow_ids", []))}')
    # tightness
    obcells = {tuple(c) for o in d['obstacles'] for c in o['cells']}
    everything = allcells | obcells | pipecells
    if everything:
        mc, mr = max(c[0] for c in everything), max(c[1] for c in everything)
        nc, nr = min(c[0] for c in everything), min(c[1] for c in everything)
        if (nc, nr) != (0, 0) or (mc + 1, mr + 1) != (cols, rows):
            errs.append(f'cols/rows not tight: cells span ({nc},{nr})-({mc},{mr}) vs {cols}x{rows}')
    # boxes: full rectangles with an integer counter
    for o in boxes:
        cs = {tuple(c) for c in o['cells']}
        xs = [c[0] for c in cs]; ys = [c[1] for c in cs]
        if len(cs) != (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1):
            errs.append(f'box not a full rectangle ({len(cs)} cells)')
        if not isinstance(o.get('counter'), int):
            errs.append(f'box without integer counter')
    for p in d.get('pipes', []):
        if not isinstance(p.get('counter'), int):
            errs.append('pipe without integer counter')
        cs = [tuple(c) for c in p['cells']]
        s = set(cs)
        ends = [tuple(e['cell']) for e in p.get('ends', [])]
        deg = {c: sum((c[0] + dx, c[1] + dy) in s for dx, dy in D.values()) for c in cs}
        if sorted(c for c in cs if deg[c] == 1) != sorted(ends) or len(ends) != 2:
            errs.append(f'pipe ends {ends} are not its degree-1 cells')
        for e in p.get('ends', []):
            c = tuple(e['cell'])
            nb = [(c[0] + dx, c[1] + dy) for dx, dy in D.values() if (c[0] + dx, c[1] + dy) in s]
            if nb:
                n = nb[0]
                if D[e['out']] != (c[0] - n[0], c[1] - n[1]):
                    errs.append(f'pipe end {c} out {e["out"]} does not point away from the tube')
    # ties
    ties = [o for o in d['obstacles'] if o['kind'] == 'tape_pink']
    taped = set()
    for t in ties:
        tc = {tuple(c) for c in t['cells']}
        bound = [a for a in arrows if tc & set(map(tuple, a['cells']))]
        taped |= {a['id'] for a in bound}
        for a in bound:
            cs = [tuple(c) for c in a['cells']]
            hit = [i for i, c in enumerate(cs) if c in tc]
            if len(hit) != 1:
                errs.append(f'tie covers {len(hit)} cells of arrow {a["id"]}')
            elif hit[0] != len(cs) - 2:
                notes.append(f'tie on cell index {hit[0]} of arrow {a["id"]} (len {len(cs)}), not len-2')
            if len({c[0] for c in cs}) != 1 and len({c[1] for c in cs}) != 1:
                errs.append(f'taped arrow {a["id"]} is not straight')
        if len({a['dir'] for a in bound}) != 1 or len({len(a['cells']) for a in bound}) != 1:
            errs.append(f'tie binds arrows of different dir/length {[a["id"] for a in bound]}')
        if len(bound) != len(tc):
            errs.append(f'tie with {len(tc)} cells binds {len(bound)} arrows')
    if sorted(taped) != sorted(d.get('taped_arrow_ids', [])):
        errs.append(f'taped_arrow_ids {sorted(d.get("taped_arrow_ids", []))} != arrows under ties {sorted(taped)}')
    return errs, notes


class Game:
    def __init__(self, d):
        self.cols, self.rows = d['cols'], d['rows']
        self.arrows = {a['id']: a for a in d['arrows']}
        self.live = {a['id'] for a in d['arrows'] if a.get('layer', 1) == 1}
        self.pending = {}  # elevator k -> hidden ids
        self.plat = {}
        for k, e in enumerate(d.get('elevators') or []):
            self.pending[k] = set(e.get('hidden_arrow_ids', []))
            self.plat[k] = set(e.get('arrow_ids', []))
        self.boxes = [{'cells': {tuple(c) for c in o['cells']}, 'counter': o['counter'], 'alive': True}
                      for o in d['obstacles'] if o['kind'] in ('box', 'curtain')]
        self.pipes = [{'cells': {tuple(c) for c in p['cells']}, 'ends': [(tuple(e['cell']), e['out']) for e in p['ends']],
                       'left': p['counter'], 'alive': True} for p in d.get('pipes', [])]
        ties = [o for o in d['obstacles'] if o['kind'] == 'tape_pink']
        self.bundle = {}
        for t in ties:
            tc = {tuple(c) for c in t['cells']}
            ids = frozenset(a['id'] for a in d['arrows'] if tc & set(map(tuple, a['cells'])))
            for i in ids:
                self.bundle[i] = ids
        self.removed = 0
        self.cellmap()

    def cellmap(self):
        self.occ = {}
        for i in self.live:
            for c in self.arrows[i]['cells']:
                self.occ[tuple(c)] = i

    def ray(self, i):
        """returns (free, pipes_passed)"""
        a = self.arrows[i]
        x, y = a['cells'][-1]
        dname = a['dir']
        passed = []
        steps = 0
        while True:
            dx, dy = D[dname]
            x, y = x + dx, y + dy
            steps += 1
            if steps > 4 * (self.cols + self.rows) + 50:
                return False, passed  # loop guard
            if not (-1 <= x <= self.cols and -1 <= y <= self.rows):
                return True, passed
            if not (0 <= x < self.cols and 0 <= y < self.rows):
                continue
            c = (x, y)
            o = self.occ.get(c)
            if o is not None and o != i:
                return False, passed
            if o == i:
                return False, passed
            if any(b['alive'] and c in b['cells'] for b in self.boxes):
                return False, passed
            hit = None
            for k, p in enumerate(self.pipes):
                if p['alive'] and c in p['cells']:
                    hit = k
            if hit is not None:
                p = self.pipes[hit]
                ends = dict(p['ends'])
                if c in ends and OPP[ends[c]] == dname:
                    other = [e for e in p['ends'] if e[0] != c][0]
                    passed.append(hit)
                    (x, y), dname = other[0], other[1]
                    continue
                return False, passed

    def unit(self, i):
        return sorted(self.bundle.get(i, {i}))

    def free_units(self):
        seen, out = set(), []
        for i in sorted(self.live):
            if i in seen:
                continue
            u = self.unit(i)
            seen |= set(u)
            if all(j in self.live for j in u) and all(self.ray(j)[0] for j in u):
                out.append(u)
        return out

    def remove(self, u):
        passes = []
        for j in u:
            passes += self.ray(j)[1]
        for j in u:
            self.live.discard(j)
        self.removed += len(u)
        for b in self.boxes:
            if b['alive'] and self.removed >= b['counter']:
                b['alive'] = False
        for k in passes:
            p = self.pipes[k]
            p['left'] -= 1
            if p['left'] <= 0:
                p['alive'] = False
        for k in list(self.pending):
            if self.pending[k] and not (self.plat[k] & self.live):
                self.live |= self.pending[k]
                self.pending[k] = set()
        self.cellmap()

    def done(self):
        return not self.live and not any(self.pending.values())


def solve_rounds(d):
    g = Game(d)
    rounds = []
    moves = 0
    while not g.done():
        fu = g.free_units()
        if not fu:
            return {'solved': False, 'rounds': len(rounds), 'moves': moves, 'left': sorted(g.live),
                    'pending_hidden': sum(len(v) for v in g.pending.values())}
        n = 0
        for u in fu:
            if all(j in g.live for j in u) and all(g.ray(j)[0] for j in u):
                g.remove(u)
                n += 1
                moves += 1
        rounds.append(n)
    return {'solved': True, 'rounds': len(rounds), 'per_round': rounds, 'moves': moves,
            'free_at_start': len(Game(d).free_units())}


def random_orders(d, n, seed=7):
    rng = random.Random(seed)
    dead = 0
    for _ in range(n):
        g = Game(d)
        while not g.done():
            fu = g.free_units()
            if not fu:
                dead += 1
                break
            g.remove(rng.choice(fu))
    return dead


def counterfactual(d):
    """largest solvable counter per box (others as given) and 'never breaks' for boxes and pipes."""
    out = {}
    boxes = [k for k, o in enumerate(d['obstacles']) if o['kind'] in ('box', 'curtain')]
    for k in boxes:
        base = d['obstacles'][k]['counter']
        best = None
        for c in range(base, base + 30):
            dd = json.loads(json.dumps(d))
            dd['obstacles'][k]['counter'] = c
            if solve_rounds(dd)['solved']:
                best = c
            else:
                break
        dd = json.loads(json.dumps(d))
        dd['obstacles'][k]['counter'] = 10 ** 6
        out[f'box{k}'] = {'counter': base, 'max_solvable': best, 'never_breaks_solvable': solve_rounds(dd)['solved']}
    for k, p in enumerate(d.get('pipes', [])):
        dd = json.loads(json.dumps(d))
        dd['pipes'][k]['counter'] = 10 ** 6
        out[f'pipe{k}'] = {'counter': p['counter'], 'never_breaks_solvable': solve_rounds(dd)['solved']}
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--random', type=int, default=0)
    ap.add_argument('--cf', action='store_true')
    ap.add_argument('--json')
    x = ap.parse_args()
    ref = json.load(open(PHONE_REF))
    allres = {}
    for f in x.files:
        d = json.load(open(f))
        r = {'schema': schema_check(d, ref)}
        r['invariants'], r['notes'] = invariants(d)
        r['solver'] = solve_rounds(d)
        if x.random:
            r['random_dead_ends'] = f'{random_orders(d, x.random)}/{x.random}'
        if x.cf:
            r['counterfactual'] = counterfactual(d)
        allres[os.path.basename(f)] = r
        s = r['solver']
        print(f"{os.path.basename(f)}: schema {len(r['schema'])} err, invariants {len(r['invariants'])} err, notes {len(r['notes'])}, "
              f"solved {s['solved']} rounds {s['rounds']} moves {s['moves']}"
              + (f", random dead ends {r['random_dead_ends']}" if x.random else '')
              + (f", cf {r['counterfactual']}" if x.cf else ''), flush=True)
        for e in r['schema'] + r['invariants']:
            print('   ERR', e)
        for e in r['notes']:
            print('   note', e)
    if x.json:
        json.dump(allres, open(x.json, 'w'), indent=1)
