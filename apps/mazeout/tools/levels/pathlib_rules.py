#!/usr/bin/env python3
"""pathlib_rules.py — CONTENT's Python mirror of the board rules (SPEC-architecture §3.2 tools/levels/**; L1 acceptance:
"the Python mirror agrees with PathCore on the free set of every level's start state").

The rule code below (DIRS … class Board) is a copy of design/tools/arrowcore.py lines 32-356 (the gameplay spec's executable
rules, SPEC-gameplay §2-§4), taken 2026-09-25 so tools/levels does not depend on a design/ work file; `--pin` checks the
copy still equals its source. PathCore (Swift, C2) is the authority in the app; this mirror exists so content work in
Python and the app agree, and the comparison below is the proof.

  python3 tools/levels/pathlib_rules.py compare build/l1/freeset-swift.json App/Resources/Levels [--report F]
      For every bundled level: the free units of the START state, then along C2's greedy trajectory (from lvtool
      freeset) the free units at the start of every round, replaying the removals Swift made. Any difference = exit 1.
  python3 tools/levels/pathlib_rules.py --pin
      The rule code equals design/tools/arrowcore.py lines 32-356 (exit 1 when the source moved on).

Rules the mirror implements (the SHIPPED rules.json agrees: tape.blockedPolicy bundleBumps, box.countAt tap / every member
counts, pipe passes consumed at the tap, elevator empty cells never block, doors block until the burst):
see the Board docstring and SPEC-gameplay §3.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

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



# -------------------------------------------------------------------- CONTENT's comparison with PathCore (C2)
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..'))
PIN = (32, 356)


def units_key(units):
    return sorted(sorted(u) for u in units)


def compare(swift_path, levels_dir, report=None):
    sw = json.load(open(swift_path))['levels']
    rows, bad, states = [], [], 0
    files = sorted(glob.glob(os.path.join(levels_dir, 'level_*.json')))
    for f in files:
        lvl = json.load(open(f))
        n = str(lvl['level'])
        if n not in sw:
            bad.append('L%s: no Swift record' % n)
            continue
        s = sw[n]
        b = Board(lvl)
        py_start = units_key(u for u, _ in b.free_units())
        diff = []
        if py_start != units_key(s['start']):
            diff.append('start: python %s vs swift %s' % (py_start, units_key(s['start'])))
        states += 1
        # replay C2's greedy trajectory round by round
        for k, rnd in enumerate(s['rounds']):
            while True:
                fu = b.free_units()
                if fu or not b.pending_doors:
                    break
                b.open_pending_doors()
            py = units_key(u for u, _ in b.free_units())
            if py != units_key(rnd['free']):
                diff.append('round %d: python %s vs swift %s' % (k + 1, py, units_key(rnd['free'])))
                break
            states += 1
            for u in rnd['removed']:
                r = b.resolve(u[0])
                if r[0] != 'exit' or sorted(r[1]) != sorted(u):
                    diff.append('round %d: python cannot exit %s (%s)' % (k + 1, u, r[0]))
                    break
                b.commit_exit(r[1], r[2])
            if diff:
                break
            b.open_pending_doors()
        if not diff and s.get('cleared') and not b.cleared():
            diff.append('python board not cleared after the trajectory (%d left)' % len(b.alive))
        rows.append(dict(level=int(n), start_free_units=len(py_start), rounds=len(s['rounds']), equal=not diff,
                         diff=diff[:3]))
        bad += ['L%s: %s' % (n, d) for d in diff]
    rep = dict(levels=len(rows), states_compared=states, equal=sum(r['equal'] for r in rows), errors=bad, table=rows)
    if report:
        with open(report, 'w') as fh:
            json.dump(rep, fh, indent=1, sort_keys=True)
            fh.write('\n')
    print('pathlib_rules compare: %d levels, %d round-start states (start + every greedy round); %d/%d levels agree with '
          'PathCore; %d difference(s)' % (len(rows), states, rep['equal'], len(rows), len(bad)))
    for x in bad[:30]:
        print('DIFF', x)
    return 0 if not bad and len(rows) == len(sw) else 1


def pin():
    src = os.path.join(APP, 'design', 'tools', 'arrowcore.py')
    lines = open(src).read().split('\n')
    want = '\n'.join(lines[PIN[0] - 1:PIN[1]])
    me = open(os.path.abspath(__file__)).read()
    ok = want in me
    print('pathlib_rules --pin: the rule code %s design/tools/arrowcore.py lines %d-%d (sha1 %s)' % (
        'EQUALS' if ok else 'NO LONGER EQUALS', PIN[0], PIN[1], hashlib.sha1(want.encode()).hexdigest()[:12]))
    return 0 if ok else 1


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--pin']:
        sys.exit(pin())
    if a[:1] == ['compare'] and len(a) >= 3:
        rp = a[a.index('--report') + 1] if '--report' in a else None
        sys.exit(compare(a[1], a[2], rp))
    print(__doc__)
    sys.exit(64)
