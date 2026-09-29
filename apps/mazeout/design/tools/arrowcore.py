#!/usr/bin/env python3
"""arrowcore.py — the Python mirror of Arrow Out's board rules (design/SPEC-gameplay.md §2–§4).

One module, used by every design/tools script (import, reveal backfill, generator, validator). PathCore (Swift) is the
authority in the app; this file is the executable statement of the SAME rules for content work, so a level that this
module solves is solvable in the game. If the two ever disagree, the spec text decides and the loser is fixed.

Level dicts use the BUNDLE schema (SPEC-architecture §4.3, `LevelJSON.swift`):
  level, source, capture?, cols, rows, mask?, timer_s, hearts, tag, arrows[{id, cells:[[c,r]…] tail→head, dir, layer?, hidden_by?}],
  obstacles[{id, kind, cells, arrows?, ends?[{cell,out}], counter?, counter_at?, order?, opens?, turn?, reveals?, sprite?}],
  unlock?, seed?, metrics?

Rules implemented (SPEC-gameplay §3):
  * ray walk from the head's next cell to the grid edge; the first live arrow cell, locked door cell, unbroken box cell,
    pipe tube cell (not entered through a mouth) or corner side blocks;
  * pipes: a ray entering a mouth against its `out` direction continues from the other mouth in that mouth's `out`;
    each passage −1 at the tap; 0 → the pipe breaks (its cells empty);
  * tape bundle: one unit; exits iff every member's ray is clear (members ignore each other); else the bundle bumps;
  * box/curtain: every arrow cleared anywhere lowers every unbroken counter by 1 (per member); 0 → breaks, reveals live;
  * door + key: a key arrow's exit sends the key to `opens` (else the lowest-order locked door not yet targeted); the door
    blocks until it opens (solver: it opens before the next tap — opening is monotone, see §3.6), then `reveals` go live;
  * elevator: layer-2 arrows are inert (never block, never tappable) until every platform arrow has left; then they go
    live at once; empty platform cells never block;
  * corner: a wedge turns the ray 90° (`turn` = incoming→outgoing; the reverse pair is implied); other sides block
    (VERIFIED phone v552 L70/L71, SPEC-gameplay §3.9: research facing s -> turn, import_research.FACING_TURN);
  * an obstacle lying wholly inside a door (v552 L69: pipes under doors) is UNDER it: the locked door blocks first, the
    obstacle acts from the burst on (the walk checks a locked door before a pipe/corner/box).
"""
from __future__ import annotations

import json
import math
import statistics

DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
OPP = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
# CornerTurn: "XY" = a ray travelling X leaves travelling Y; the implied reverse pair is opp(Y) -> opp(X).
CORNER = {
    'upRight': {'up': 'right', 'left': 'down'},
    'upLeft': {'up': 'left', 'right': 'down'},
    'downRight': {'down': 'right', 'left': 'up'},
    'downLeft': {'down': 'left', 'right': 'up'},
}
TAP_SECONDS = 0.6          # HeadlessDriver human pace (SPEC-architecture §4.15)
DOOR_SECONDS = 1.14        # key tap -> door burst (VERIFIED motion §5.2)
MAX_HOPS = 16              # pipe/corner loop guard (rules.json pipe.maxHops)


def step(c, d):
    return (c[0] + DIRS[d][0], c[1] + DIRS[d][1])


def dir_between(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    for k, v in DIRS.items():
        if v == (dx, dy):
            return k
    return None


def cells_of(x):
    return [tuple(c) for c in x]


class RuleError(Exception):
    pass


class Board:
    """Mutable board state for one stage. `copy()` is cheap (state only; the static tables are shared)."""

    def __init__(self, lvl, box_counts_members=True, _static=None):
        if _static is not None:
            self.S = _static
            return
        S = self.S = {}
        S['cols'], S['rows'] = lvl['cols'], lvl['rows']
        A = S['A'] = {}
        for a in lvl['arrows']:
            A[a['id']] = dict(cells=cells_of(a['cells']), dir=a['dir'], layer=a.get('layer', 1) or 1,
                              hidden_by=a.get('hidden_by'))
        O = S['O'] = {o['id']: o for o in lvl.get('obstacles', [])}
        S['tape_of'] = {}
        S['keys_on'] = {}
        S['door_cells'] = {}
        S['box_cells'] = {}
        S['pipe_cells'] = {}
        S['pipe_ends'] = {}      # cell -> (oid, out)
        S['pipe_other'] = {}     # (oid, cell) -> (cell, out)
        S['corner'] = {}         # cell -> (oid, turn)
        S['elev_platform'] = {}  # oid -> set(arrow ids)
        for oid, o in O.items():
            k = o['kind']
            cs = cells_of(o.get('cells', []))
            if k == 'tape':
                for a in o.get('arrows', []):
                    S['tape_of'][a] = oid
            elif k == 'key':
                for a in o.get('arrows', []):
                    S['keys_on'].setdefault(a, []).append(oid)
            elif k == 'door':
                for c in cs:
                    S['door_cells'][c] = oid
            elif k in ('box', 'curtain'):
                for c in cs:
                    S['box_cells'][c] = oid
            elif k == 'pipe':
                ends = o.get('ends', [])
                if len(ends) != 2:
                    raise RuleError(f'pipe {oid} has {len(ends)} ends')
                for c in cs:
                    S['pipe_cells'][c] = oid
                e0, e1 = (tuple(ends[0]['cell']), ends[0]['out']), (tuple(ends[1]['cell']), ends[1]['out'])
                S['pipe_ends'][e0[0]] = (oid, e0[1])
                S['pipe_ends'][e1[0]] = (oid, e1[1])
                S['pipe_other'][(oid, e0[0])] = e1
                S['pipe_other'][(oid, e1[0])] = e0
            elif k == 'elevator':
                S['elev_platform'][oid] = set(o.get('arrows', []))
            elif k == 'corner':
                for c in cs:
                    S['corner'][c] = (oid, o['turn'])
        S['occ'] = {1: {}, 2: {}}
        for aid, a in A.items():
            for c in a['cells']:
                S['occ'][a['layer']][c] = aid
        S['box_counts_members'] = box_counts_members
        # dynamic state
        self.alive = set(A)
        self.hidden = {aid for aid, a in A.items() if a['hidden_by'] is not None}
        self.door_open = set()
        self.door_targeted = set()
        self.pending_doors = []
        self.pipe_ctr = {oid: O[oid].get('counter') for oid in O if O[oid]['kind'] == 'pipe'}
        self.pipe_broken = set()
        self.box_ctr = {oid: O[oid].get('counter') for oid in O if O[oid]['kind'] in ('box', 'curtain')}
        self.box_broken = set()
        self.elev_active = set()
        self.tapes_gone = set()
        self.marked = set()

    def copy(self):
        b = Board(None, _static=self.S)
        b.alive = set(self.alive)
        b.hidden = set(self.hidden)
        b.door_open = set(self.door_open)
        b.door_targeted = set(self.door_targeted)
        b.pending_doors = list(self.pending_doors)
        b.pipe_ctr = dict(self.pipe_ctr)
        b.pipe_broken = set(self.pipe_broken)
        b.box_ctr = dict(self.box_ctr)
        b.box_broken = set(self.box_broken)
        b.elev_active = set(self.elev_active)
        b.tapes_gone = set(self.tapes_gone)
        b.marked = set(self.marked)
        return b

    # ---------------------------------------------------------------- queries
    def live(self, aid):
        return aid in self.alive and aid not in self.hidden

    def unit(self, aid):
        t = self.S['tape_of'].get(aid)
        if t is None:
            return [aid]
        return sorted(a for a in self.S['O'][t]['arrows'] if a in self.alive)

    def units(self):
        seen, out = set(), []
        for aid in sorted(self.alive):
            if aid in seen or aid in self.hidden:
                continue
            u = self.unit(aid)
            seen.update(u)
            out.append(u)
        return out

    def in_grid(self, c):
        return 0 <= c[0] < self.S['cols'] and 0 <= c[1] < self.S['rows']

    def static_blocker(self, c):
        S = self.S
        d = S['door_cells'].get(c)
        if d is not None and d not in self.door_open:
            return ('obstacle', d)
        b = S['box_cells'].get(c)
        if b is not None and b not in self.box_broken:
            return ('obstacle', b)
        return None

    def arrow_at(self, c, ignore=()):
        for layer in (1, 2):
            a = self.S['occ'][layer].get(c)
            if a is not None and a not in ignore and self.live(a):
                return a
        return None

    def walk(self, aid, ignore=()):
        """The head's ray. Returns dict(blocker=None|('arrow',id)|('obstacle',oid), passages=[pipe oids], corners=[...],
        cells=[cells the head passes, in order, until the grid edge or the blocker (excluded)], hops)."""
        S = self.S
        a = S['A'][aid]
        own = set(a['cells'])
        c, d = a['cells'][-1], a['dir']
        cells, passages, corners = [], [], []
        hops = 0
        while True:
            n = step(c, d)
            if not self.in_grid(n):
                return dict(blocker=None, passages=passages, corners=corners, cells=cells)
            dr = S['door_cells'].get(n)
            if dr is not None and dr not in self.door_open:
                # a locked door blocks first: an obstacle UNDER it (session 2: L69's pipes) is inert until the burst
                return dict(blocker=('obstacle', dr), passages=passages, corners=corners, cells=cells)
            p = S['pipe_cells'].get(n)
            if p is not None and p not in self.pipe_broken:
                e = S['pipe_ends'].get(n)
                if e is not None and e[0] == p and e[1] == OPP[d]:
                    hops += 1
                    if hops > MAX_HOPS:
                        return dict(blocker=('obstacle', p), passages=passages, corners=corners, cells=cells)
                    passages.append(p)
                    oc, oout = S['pipe_other'][(p, n)]
                    cells.append(n)
                    cells.append(oc)
                    c, d = oc, oout
                    continue
                return dict(blocker=('obstacle', p), passages=passages, corners=corners, cells=cells)
            k = S['corner'].get(n)
            if k is not None:
                nd = CORNER[k[1]].get(d)
                if nd is None:
                    return dict(blocker=('obstacle', k[0]), passages=passages, corners=corners, cells=cells)
                hops += 1
                if hops > MAX_HOPS:
                    return dict(blocker=('obstacle', k[0]), passages=passages, corners=corners, cells=cells)
                corners.append(k[0])
                cells.append(n)
                c, d = n, nd
                continue
            sb = self.static_blocker(n)
            if sb is not None:
                return dict(blocker=sb, passages=passages, corners=corners, cells=cells)
            b = self.arrow_at(n, ignore)
            if b is not None:
                return dict(blocker=('arrow', b), passages=passages, corners=corners, cells=cells)
            if n in own:
                # validator forbids it; treat as blocked by itself (never happens in valid content)
                return dict(blocker=('arrow', aid), passages=passages, corners=corners, cells=cells)
            cells.append(n)
            c = n

    def resolve(self, aid):
        """('exit', unit, walks) or ('bump', unit, blocker) or ('ignored', reason)."""
        if aid not in self.alive:
            return ('ignored', 'noArrow')
        if aid in self.hidden:
            return ('ignored', 'hidden')
        u = self.unit(aid)
        walks = {}
        for m in u:
            w = self.walk(m, ignore=set(u))
            if w['blocker'] is not None:
                return ('bump', u, w['blocker'])
            walks[m] = w
        return ('exit', u, walks)

    def free_units(self):
        out = []
        for u in self.units():
            r = self.resolve(u[0])
            if r[0] == 'exit':
                out.append((u, r[2]))
        return out

    # ---------------------------------------------------------------- mutation
    def commit_exit(self, u, walks):
        """Apply an exit at the tap. Returns event list (for the solver's bookkeeping)."""
        S = self.S
        ev = []
        for m in u:
            self.alive.discard(m)
        t = S['tape_of'].get(u[0])
        if t is not None:
            self.tapes_gone.add(t)
        # pipes: one passage = -1, in walk order
        for m in u:
            for p in walks[m]['passages']:
                if p in self.pipe_broken:
                    continue
                c = self.pipe_ctr.get(p)
                if c is None:
                    continue          # unlimited (missingCounterIsUnlimited)
                c -= 1
                self.pipe_ctr[p] = c
                ev.append(('pipeCount', p, c))
                if c <= 0:
                    self.pipe_broken.add(p)
                    ev.append(('pipeBreak', p))
        # boxes: every arrow cleared anywhere (tape members one each)
        n = len(u) if S['box_counts_members'] else 1
        for b, c in list(self.box_ctr.items()):
            if b in self.box_broken or c is None:
                continue
            c -= n
            self.box_ctr[b] = c
            ev.append(('counter', b, max(c, 0)))
            if c <= 0:
                self.box_broken.add(b)
                self._reveal(b)
                ev.append(('boxBreak', b))
        # keys
        for m in u:
            for k in S['keys_on'].get(m, []):
                d = self._key_target(k)
                if d is not None:
                    self.door_targeted.add(d)
                    self.pending_doors.append(d)
                    ev.append(('keyDispatched', k, d))
        # elevators: activation when every platform arrow has left
        for e, plat in S['elev_platform'].items():
            if e in self.elev_active:
                continue
            if plat and not (plat & self.alive):
                self.elev_active.add(e)
                self._reveal(e)
                ev.append(('elevatorActivated', e))
        return ev

    def _key_target(self, k):
        S = self.S
        o = S['O'][k]
        if o.get('opens'):
            d = o['opens']
            return d if d not in self.door_open and d not in self.door_targeted else None
        doors = [x for x in S['O'].values() if x['kind'] == 'door' and x['id'] not in self.door_open
                 and x['id'] not in self.door_targeted]
        if not doors:
            return None
        doors.sort(key=lambda x: (x.get('order', 0), x['id']))
        return doors[0]['id']

    def _reveal(self, oid):
        for a in self.S['O'][oid].get('reveals', []):
            self.hidden.discard(a)

    def open_pending_doors(self):
        ev = []
        for d in self.pending_doors:
            if d not in self.door_open:
                self.door_open.add(d)
                self._reveal(d)
                ev.append(('doorOpened', d))
        self.pending_doors = []
        return ev

    def cleared(self):
        return not self.alive

    def state_key(self):
        return (frozenset(self.alive), tuple(sorted((k, v) for k, v in self.pipe_ctr.items())),
                frozenset(self.door_open | set(self.pending_doors)), frozenset(self.elev_active))


# -------------------------------------------------------------------- solvers
def _nonmonotone(board, u, walks):
    """1 if tapping u would break a pipe or activate an elevator (the two non-monotone events), else 0."""
    b = board.copy()
    ev = b.commit_exit(u, walks)
    return 1 if any(e[0] in ('pipeBreak', 'elevatorActivated') for e in ev) else 0


def greedy(lvl, prefer_monotone=True):
    """Sequential greedy: tap one free unit at a time (monotone taps first, then the lowest id), doors open before the
    next tap. Returns dict(ok, order=[unit], stuck=[unit], taps, doors)."""
    b = Board(lvl)
    order, doors = [], 0
    while not b.cleared():
        fu = b.free_units()
        if not fu:
            if b.pending_doors:
                doors += len(b.open_pending_doors())
                continue
            return dict(ok=False, order=order, stuck=b.units(), taps=len(order), doors=doors)
        if prefer_monotone and len(fu) > 1:
            fu.sort(key=lambda x: (_nonmonotone(b, x[0], x[1]), x[0][0]))
        u, walks = fu[0]
        b.commit_exit(u, walks)
        doors += len(b.open_pending_doors())
        order.append(u)
    return dict(ok=True, order=order, stuck=[], taps=len(order), doors=doors)


def dfs(lvl, budget=200000):
    """Exact search with memo over the full state; returns dict(ok, order, nodes, exhausted)."""
    b0 = Board(lvl)
    seen = set()
    nodes = [0]
    path = []

    def rec(b):
        if b.cleared():
            return True
        nodes[0] += 1
        if nodes[0] > budget:
            raise TimeoutError
        k = b.state_key()
        if k in seen:
            return False
        seen.add(k)
        fu = b.free_units()
        if not fu and b.pending_doors:
            b2 = b.copy()
            b2.open_pending_doors()
            return rec(b2)
        fu.sort(key=lambda x: (_nonmonotone(b, x[0], x[1]), x[0][0]))
        for u, walks in fu:
            b2 = b.copy()
            b2.commit_exit(u, walks)
            b2.open_pending_doors()
            path.append(u)
            if rec(b2):
                return True
            path.pop()
        return False

    try:
        ok = rec(b0)
        return dict(ok=ok, order=list(path) if ok else [], nodes=nodes[0], exhausted=False)
    except TimeoutError:
        return dict(ok=False, order=[], nodes=nodes[0], exhausted=True)


def waves(lvl):
    """Dependency depth: each wave taps every unit free at the wave's start (skipping any that a non-monotone event of
    the same wave re-blocked); doors dispatched in a wave open at its end. Returns (waves, [units per wave], ok)."""
    b = Board(lvl)
    per = []
    guard = 0
    while not b.cleared():
        guard += 1
        if guard > 5000:
            return len(per), per, False
        fu = b.free_units()
        if not fu:
            if b.pending_doors:
                b.open_pending_doors()
                continue
            return len(per), per, False
        n = 0
        for u, _ in fu:
            r = b.resolve(u[0])
            if r[0] != 'exit':
                continue
            b.commit_exit(r[1], r[2])
            n += 1
        b.open_pending_doors()
        per.append(n)
    return len(per), per, True


def metrics(lvl, solve=None):
    arrows = lvl['arrows']
    lens = [len(a['cells']) for a in arrows]
    b = Board(lvl)
    units0 = b.units()
    free0 = len(b.free_units())
    tapes = [o for o in lvl.get('obstacles', []) if o['kind'] == 'tape']
    n_units = len(arrows) - sum(len(t['arrows']) - 1 for t in tapes)
    w, per, ok = waves(lvl)
    doors = sum(1 for o in lvl.get('obstacles', []) if o['kind'] == 'door')
    occupied = set()
    for a in arrows:
        for c in a['cells']:
            occupied.add((a.get('layer', 1), tuple(c)))
    cells = len(occupied)
    bot_left = lvl['timer_s'] - (n_units * TAP_SECONDS + doors * DOOR_SECONDS)
    return dict(rounds=w, free_at_start=free0, arrows=len(arrows), cells=cells,
                mean_length=round(sum(lens) / max(1, len(lens)), 3), bot_time_left=round(bot_left, 1),
                # extras (not in the bundle's LevelMetrics; used by the curve fit)
                _units=n_units, _visible_units=len(units0), _max_length=max(lens) if lens else 0,
                _median_length=statistics.median(lens) if lens else 0,
                _density=round(cells / float(lvl['cols'] * lvl['rows']), 3), _waves=per, _waves_ok=ok)


def bundle_metrics(m):
    """The LevelMetrics subset the bundle schema carries (LevelJSON.swift metricsKeys)."""
    return dict(rounds=m['rounds'], free_at_start=m['free_at_start'], arrows=m['arrows'], cells=m['cells'],
                mean_length=m['mean_length'], bot_time_left=m['bot_time_left'])


# -------------------------------------------------------------------- structure checks (validator core)
def structural_problems(lvl):
    out = []
    cols, rows = lvl['cols'], lvl['rows']
    ids = set()
    occ = {1: {}, 2: {}}
    for a in lvl['arrows']:
        cs = cells_of(a['cells'])
        aid = a['id']
        if aid in ids:
            out.append(f'arrow {aid}: duplicate id')
        ids.add(aid)
        if len(cs) < 2:
            out.append(f'arrow {aid}: {len(cs)} cell(s)')
        for x, y in zip(cs, cs[1:]):
            if dir_between(x, y) is None:
                out.append(f'arrow {aid}: step {x}->{y} not orthogonal')
        if len(set(cs)) != len(cs):
            out.append(f'arrow {aid}: crosses itself')
        if len(cs) >= 2 and dir_between(cs[-2], cs[-1]) != a['dir']:
            out.append(f'arrow {aid}: dir {a["dir"]} but last step {dir_between(cs[-2], cs[-1])}')
        layer = a.get('layer', 1) or 1
        for c in cs:
            if not (0 <= c[0] < cols and 0 <= c[1] < rows):
                out.append(f'arrow {aid}: {c} outside {cols}x{rows}')
            if c in occ[layer]:
                out.append(f'arrow {aid} shares {c} with {occ[layer][c]} (layer {layer})')
            occ[layer][c] = aid
        # straight-line self ray (pipes/corners handled by the full walk in validate)
        own = set(cs)
        p = step(cs[-1], a['dir'])
        while 0 <= p[0] < cols and 0 <= p[1] < rows:
            if p in own:
                out.append(f'arrow {aid}: ray crosses its own body at {p}')
                break
            p = step(p, a['dir'])
    return out


def load(path):
    with open(path) as f:
        return json.load(f)


def dump(obj, path, compact=False):
    with open(path, 'w') as f:
        if compact:
            json.dump(obj, f, separators=(',', ':'), sort_keys=True)
        else:
            json.dump(obj, f, indent=1, sort_keys=True)
        f.write('\n')
