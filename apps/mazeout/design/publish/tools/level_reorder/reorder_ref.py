#!/usr/bin/env python3
"""reorder_ref.py — the REFERENCE prototype of the level re-order (owner item 12 / SPEC.md ruling 37e), specified in
design/publish/level-reorder.md. Reads design/levels.json (read-only); writes level_order_candidate.json next to itself.
  python3 design/publish/tools/level_reorder/reorder_ref.py            (ATTEMPTS=64 default; ~25 s, one core)

  stage 1  per tag class, a min-cost assignment (scipy linear_sum_assignment) of the zone's boards to the zone's slots:
           cost = difficulty distance to the board the slot holds today + seeded noise; forbidden cells = BIG
  stage 2  deterministic first-improvement swap search inside each tag class (candidate pairs in a seeded order) that
           lowers the curve objective J while every hard rule still holds; stops at a local minimum or MAX_PASSES
  choose   K attempts (PathRandom(salt).fork('a<k>')); the attempt inside TOL with the lowest J wins (ties: lower k)
"""
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', 'tools')))   # design/tools (pathrandom)
from feat import load  # noqa: E402
from pathrandom import PathRandom, fnv1a64  # noqa: E402

E = os.environ.get
FREEZE_TO = int(E('FREEZE_TO', 33))
ZONE_END = int(E('ZONE_END', 105))
ANCHORS = {70}
FIRST = dict(tape=7, box=11, pipe=21, elevator=31, door=33, corner=70)
PRACTICE = {34: 'door', 71: 'corner'}
DMAX = dict(normal=int(E('DMAX_N', 10)), hard=20, superHard=20)
DMIN_V552 = int(E('DMIN', 3))              # a v552 board moves at least this far (normal class; tagged move by 10s)
LOOKALIKE_GAP = 10
TWIN_GAP = 10
RUN_MAX = int(E('RUN_MAX', 3))
SHORT_TIMER, SHORT_GAP = 120, 5
NOISE = float(E('NOISE', 0.3))
ATTEMPTS = int(E('ATTEMPTS', 64))
ROUNDS = 12
MAX_PASSES = 20
SALT = fnv1a64('arrow-out/reorder/v1')
BIG = 1e6
WIN = 9
W_FREE = float(E('W_FREE', 0.05))
W_KINDMIX = float(E('W_KINDMIX', 0.02))
KINDS = ('door', 'pipe', 'box', 'tape', 'elevator', 'corner')
# tolerance = the ORIGINAL curve's own one-level change (rolling-9, L34-L105: units max 0.181 / mean 0.056, waves 0.188 /
# 0.063, pressure 0.047 / 0.013) and its decade-to-decade change (units: mean 7 %, max 14 %)
TOL = dict(units=0.12, waves=0.12, pressure=0.035, units_mean=0.056, waves_mean=0.063, pressure_mean=0.013, timer=0.10, free_abs=float(E('TOL_F', 3.5)),
           decade=0.08, kinds=2)


def alike(a, b):
    return ((a['cols'], a['rows']) == (b['cols'], b['rows']) and a['kinds'] == b['kinds']
            and abs(a['units'] - b['units']) <= 0.2 * max(a['units'], b['units']))


def dist(b, o):
    ku = len(b['kinds'] | o['kinds'])
    jac = (1.0 - len(b['kinds'] & o['kinds']) / float(ku)) if ku else 0.0
    return (abs(math.log(b['units'] / o['units'])) + abs(math.log(b['waves'] / o['waves']))
            + 4.0 * abs(b['pressure'] - o['pressure'])
            + 0.5 * abs(math.log(b['cols'] * b['rows'] / float(o['cols'] * o['rows'])))
            + 0.15 * abs(b['timer'] - o['timer']) / 30.0 + 0.6 * jac + 0.025 * abs(b['free'] - o['free'])
            + (0.4 if b['tag'] != 'normal' and abs(b['n'] - o['n']) > 10 else 0.0))


class Problem:
    def __init__(self, F):
        self.F = F
        self.by = {f['n']: f for f in F}
        self.N = len(F)
        self.zone = [s for s in range(FREEZE_TO + 1, ZONE_END + 1) if s not in ANCHORS]
        self.classes = {}
        for s in self.zone:
            self.classes.setdefault(self.by[s]['tag'], []).append(s)
        self.alike_pairs = []
        for i in range(1, self.N + 1):
            for j in range(i + 1, self.N + 1):
                fi, fj = self.by[i], self.by[j]
                twin = fi['twin_of'] == j or fj['twin_of'] == i
                if twin or alike(fi, fj):
                    self.alike_pairs.append((i, j, TWIN_GAP if twin else LOOKALIKE_GAP, 'twin' if twin else 'look-alike'))
        old = [self.by[n] for n in range(1, self.N + 1)]
        self.timer_floor, m = {}, 10 ** 9                      # the original's running minimum timer at each slot
        for f in old:
            m = min(m, f['timer'])
            self.timer_floor[f['n']] = m
        self.ro = {k: rolling([f[k] for f in old]) for k in ('units', 'waves', 'pressure', 'timer', 'free')}

    # ------------------------------------------------------------------ hard rules
    def forbidden(self, b, s):
        f = self.by[b]
        if f['origin'] and f['origin'][1] == s:
            return True                                           # its own number in the original game / older build
        d = abs(s - b)
        if d > DMAX[f['tag']]:
            return True
        if f['origin'] and f['origin'][0] == 'v552' and f['tag'] == 'normal' and d < DMIN_V552:
            return True
        if any(s <= FIRST[k] for k in f['kinds']):
            return True                                           # never before its obstacle's teaching level
        if s in PRACTICE and PRACTICE[s] not in f['kinds']:
            return True                                           # the level after a teaching card practises it
        if f['timer'] <= SHORT_TIMER and f['timer'] < self.timer_floor[s]:
            return True                                           # a short timer (<= 2:00) never earlier than originally
        return False

    def pair_violations(self, order):
        by, v = self.by, []
        for s in range(FREEZE_TO, ZONE_END + 1):                 # includes the seams 33|34 and 105|106
            a, b = order[s], order[s + 1]
            if b == a + 1 and not (a == s and b == s + 1):
                v.append((s + 1, 'adjacency %d,%d kept' % (a, b)))
        slot = {o: s for s, o in order.items()}
        for i, j, need, why in self.alike_pairs:
            gap = abs(slot[i] - slot[j])
            if gap < need and not (slot[i] == i and slot[j] == j):
                mover = j if slot[j] != j else i
                v.append((slot[mover], '%s L%d/L%d gap %d' % (why, i, j, gap)))
        for k in KINDS + (None,):
            run = 0
            for s in range(FREEZE_TO + 1, ZONE_END + 2):
                ks = by[order[s]]['kinds']
                run = run + 1 if ((k in ks) if k else not ks) else 0
                if run > RUN_MAX:
                    v.append((s, 'run of %s ending L%d' % (k or 'plain', s)))
        shorts = sorted(s for s in range(1, self.N + 1) if by[order[s]]['timer'] <= SHORT_TIMER)
        for a, b in zip(shorts, shorts[1:]):
            if b - a < SHORT_GAP:
                v.append((b, 'short timers L%d,L%d' % (a, b)))
        return v

    # ------------------------------------------------------------------ the curve
    def devs(self, order):
        by = self.by
        new = [by[order[n]] for n in range(1, self.N + 1)]
        out, J = {}, 0.0
        seg = range(29, min(self.N, ZONE_END + 5))
        for k in ('units', 'waves', 'pressure', 'timer', 'free'):
            rn, ro = rolling([f[k] for f in new]), self.ro[k]
            if k == 'pressure':
                out[k] = max(abs(rn[i] - ro[i]) for i in seg)
                out[k + '_mean'] = sum(abs(rn[i] - ro[i]) for i in seg) / len(seg)
                J += sum(((rn[i] - ro[i]) / 0.2) ** 2 for i in seg)
            elif k == 'free':
                out['free_abs'] = max(abs(rn[i] - ro[i]) for i in seg)
                J += W_FREE * sum(((rn[i] - ro[i]) / 3.0) ** 2 for i in seg)
            else:
                out[k] = max(abs(rn[i] - ro[i]) / ro[i] for i in seg)
                out[k + '_mean'] = sum(abs(rn[i] - ro[i]) / ro[i] for i in seg) / len(seg)
                if k in ('units', 'waves'):
                    J += sum(((rn[i] - ro[i]) / ro[i]) ** 2 for i in seg)
        du, dk = 0.0, 0
        for lo in range(30, ZONE_END + 1, 10):
            hi = min(lo + 9, ZONE_END)
            o = [by[s] for s in range(lo, hi + 1)]
            n = [by[order[s]] for s in range(lo, hi + 1)]
            for k in ('units', 'waves'):
                a, b = sum(f[k] for f in o) / len(o), sum(f[k] for f in n) / len(n)
                du = max(du, abs(b - a) / a)
            for k in KINDS:
                dkk = abs(sum(k in f['kinds'] for f in n) - sum(k in f['kinds'] for f in o))
                dk = max(dk, dkk)
                J += W_KINDMIX * dkk ** 2
        out['decade'], out['kinds'] = du, dk
        # the max terms enter J too, so the search pushes the worst spot down
        J += 20.0 * (max(0.0, out['units'] - 0.08) ** 2 + max(0.0, out['waves'] - 0.08) ** 2) + 5.0 * du ** 2
        return J, out

    def within(self, out):
        return all(out[k] <= TOL[k] for k in TOL)

    # ------------------------------------------------------------------ stage 1 + 2
    def attempt(self, k):
        rng = PathRandom(SALT).fork('a%d' % k)
        noise = {(b, s): rng.unit() for s in self.zone for b in self.zone}
        penalty = {}
        order = None
        for _ in range(ROUNDS):
            order = {s: s for s in range(1, self.N + 1)}
            for tag, slots in sorted(self.classes.items()):
                C = np.zeros((len(slots), len(slots)))
                for i, b in enumerate(slots):
                    for j, s in enumerate(slots):
                        C[i, j] = BIG if self.forbidden(b, s) else (dist(self.by[b], self.by[s]) + NOISE * noise[(b, s)]
                                                                    + penalty.get((b, s), 0.0))
                r, c = linear_sum_assignment(C)
                if C[r, c].sum() >= BIG:
                    return None, None, 'infeasible class %s' % tag
                for i, j in zip(r, c):
                    order[slots[j]] = slots[i]
            v = self.pair_violations(order)
            if not v:
                break
            for s, _ in v:
                penalty[(order[s], s)] = penalty.get((order[s], s), 0.0) + 2.0
        else:
            return None, None, 'pairwise rules unresolved'
        # stage 2: swaps inside a class, seeded candidate order, first improvement
        J, out = self.devs(order)
        pairs = [(a, b) for slots in self.classes.values() for i, a in enumerate(slots) for b in slots[i + 1:]]
        srng = rng.fork('swaps')
        for _ in range(MAX_PASSES):
            srng.shuffle(pairs)
            improved = False
            for s1, s2 in pairs:
                b1, b2 = order[s1], order[s2]
                if self.forbidden(b1, s2) or self.forbidden(b2, s1):
                    continue
                order[s1], order[s2] = b2, b1
                J2, out2 = self.devs(order)
                if J2 < J - 1e-9 and not self.pair_violations(order):
                    J, out, improved = J2, out2, True
                else:
                    order[s1], order[s2] = b1, b2
            if not improved:
                break
        return order, (J, out), None


def rolling(xs, w=WIN):
    h = w // 2
    return [sum(xs[max(0, i - h):i + h + 1]) / len(xs[max(0, i - h):i + h + 1]) for i in range(len(xs))]


def main():
    doc, F = load()
    P = Problem(F)
    best, fails, passed = None, {}, 0
    for k in range(ATTEMPTS):
        order, res, why = P.attempt(k)
        if order is None:
            fails[why] = fails.get(why, 0) + 1
            continue
        J, out = res
        if not P.within(out):
            fails['outside tolerance'] = fails.get('outside tolerance', 0) + 1
            continue
        passed += 1
        if best is None or J < best[0]:
            best = (J, k, order, out)
    print('attempts %d, inside tolerance %d, rejected %s' % (ATTEMPTS, passed, fails))
    if not best:
        raise SystemExit('no valid attempt')
    J, k, order, out = best
    print('best a%d J %.3f %s' % (k, J, {x: round(y, 3) for x, y in out.items()}))
    json.dump(dict(algorithm='reorder_ref v1', salt=SALT, attempt=k, noise=NOISE, attempts=ATTEMPTS, freeze_to=FREEZE_TO,
                   zone_end=ZONE_END, anchors=sorted(ANCHORS), practice={str(a): b for a, b in PRACTICE.items()},
                   dmax=DMAX, dmin_v552=DMIN_V552, tolerance=TOL, J=round(J, 4),
                   deviations={x: round(y, 4) for x, y in out.items()},
                   order={str(s): o for s, o in sorted(order.items())}),
              open(os.path.join(HERE, E('OUT', 'level_order_candidate.json')), 'w'), indent=1)


if __name__ == '__main__':
    main()
