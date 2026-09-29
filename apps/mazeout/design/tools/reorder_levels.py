#!/usr/bin/env python3
"""reorder_levels.py — the level re-order (PUBLISH item 12; SPEC.md rulings 37e + 39 OD8; design/publish/level-reorder.md).

The build-phase form of design/publish/tools/level_reorder/reorder_ref.py (same algorithm, same constants, same PathRandom
draws: `plan` reproduces its candidate order byte for byte). The order is DATA (design/level-order.json); the runtime never
runs this.

  python3 design/tools/reorder_levels.py plan  [--levels design/levels.json] [--plan design/level-order.json]
      the search (~25 s, one core, numpy + scipy) on the RESEARCH order -> the plan: parameters, the order {slot: research
      slot}, the curve deviations, and the sha256 of the levels.json it was computed on (input) and of the one it produces
      (output). Given an already re-ordered levels.json, the research order is rebuilt from the boards' provenance first.
  python3 design/tools/reorder_levels.py apply [--levels IN] [--out OUT] [--plan design/level-order.json]
      SHA GUARD: IN must be the plan's input (-> permuted, re-checked, and the result must hash to the plan's output) or its
      output (-> "already applied", nothing changes). Anything else is a STALE levels.json: exit 2, nothing written — the
      content changed after the plan, so re-run `plan` and review the new order. No numpy/scipy needed.
  python3 design/tools/reorder_levels.py check [--levels ...] [--plan ...] [--quick]
      re-runs the search and demands the plan file byte for byte (skipped with --quick), then asserts H1-H10 on the
      re-ordered list (level-reorder.md §4): same boards, frozen slots byte-identical, tags per slot, first appearances,
      teaching order, practice slots, timers, anti-copy, bounded moves, look-alike gaps, runs, curve tolerance.
build_levels.py assemble calls apply_planned() on the document it assembled, so a later assemble can never silently put the
research order back, and refuses when the plan is stale.
"""
import copy
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import build_levels as BL  # noqa: E402
import level_order as LO  # noqa: E402
from pathrandom import PathRandom, fnv1a64  # noqa: E402

LEVELS_JSON = BL.LEVELS_JSON
PLAN_JSON = LO.PLAN_JSON
ALGORITHM = 'reorder_levels v1 (= design/publish/tools/level_reorder/reorder_ref.py v1)'

# ------------------------------------------------------------------------------------------------ constants (reorder_ref v1)
FREEZE_TO = 33
ZONE_END = 105
ANCHORS = {70}
FIRST = dict(tape=7, box=11, pipe=21, elevator=31, door=33, corner=70)
PRACTICE = {34: 'door', 71: 'corner'}
DMAX = dict(normal=10, hard=20, superHard=20)
DMIN_V552 = 3
LOOKALIKE_GAP = 10
TWIN_GAP = 10
RUN_MAX = 3
SHORT_TIMER, SHORT_GAP = 120, 5
NOISE = 0.3
ATTEMPTS = 64
ROUNDS = 12
MAX_PASSES = 20
SALT = fnv1a64('arrow-out/reorder/v1')
BIG = 1e6
WIN = 9
W_FREE = 0.05
W_KINDMIX = 0.02
KINDS = ('door', 'pipe', 'box', 'tape', 'elevator', 'corner')
TOL = dict(units=0.12, waves=0.12, pressure=0.035, units_mean=0.056, waves_mean=0.063, pressure_mean=0.013, timer=0.10,
           free_abs=3.5, decade=0.08, kinds=2)
KIND = dict(tape='tape', door='door', pipe='pipe', box='box', curtain='box', elevator='elevator', corner='corner')


# ------------------------------------------------------------------------------------------------ features (= feat.py)
def research_number(l):
    """The number this board had in the ORIGINAL game's order, when it is known (VERIFIED from the capture path / _from)."""
    cap = l.get('capture') or ''
    m = re.search(r'[/-]L0*(\d+)-', cap)
    if l['source'] == 'recorded' and m:
        return ('v552', int(m.group(1)))
    if l['source'] == 'video':
        m2 = re.search(r'/(V[12])/L0*(\d+)-start', cap)
        if l.get('_from', '').startswith('V2-L'):
            return ('older-build', int(re.match(r'V2-L0*(\d+)', l['_from']).group(1)))
        if m2:
            return ('older-build', int(m2.group(2)))
    return None


def features(l):
    obs = l['obstacles']
    tapes = [o for o in obs if o['kind'] == 'tape']
    units = len(l['arrows']) - sum(len(t['arrows']) - 1 for t in tapes)
    doors = sum(1 for o in obs if o['kind'] == 'door')
    kinds = frozenset(KIND[o['kind']] for o in obs if o['kind'] in KIND)
    m = l['metrics']
    return dict(n=l['level'], tag=l['tag'], timer=l['timer_s'], units=units, waves=m['rounds'], free=m['free_at_start'],
                arrows=m['arrows'], cells=m['cells'], cols=l['cols'], rows=l['rows'], doors=doors, kinds=kinds,
                bot_left=m['bot_time_left'], pressure=round(1 - m['bot_time_left'] / l['timer_s'], 4),
                source=l['source'], origin=research_number(l), stand_in=l.get('_from', '').startswith('designed stand-in'),
                twin_of=(int(re.search(r'repeat of L0*(\d+)', l['_from']).group(1))
                         if l.get('_from', '').startswith('designed stand-in') else None),
                unlock=l.get('unlock'))


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


def rolling(xs, w=WIN):
    h = w // 2
    return [sum(xs[max(0, i - h):i + h + 1]) / len(xs[max(0, i - h):i + h + 1]) for i in range(len(xs))]


# ------------------------------------------------------------------------------------------------ the problem (= reorder_ref)
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
        J += 20.0 * (max(0.0, out['units'] - 0.08) ** 2 + max(0.0, out['waves'] - 0.08) ** 2) + 5.0 * du ** 2
        return J, out

    def within(self, out):
        return all(out[k] <= TOL[k] for k in TOL)

    def attempt(self, k):
        import numpy as np
        from scipy.optimize import linear_sum_assignment
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


# ------------------------------------------------------------------------------------------------ documents
def doc_text(doc):
    return BL.doc_text(doc)


def sha_text(text):
    import hashlib
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def research_doc(doc):
    """The research order of `doc` (a copy): boards sorted by their research slot, numbered by it. Identity for a doc that
    is already in research order (then the text is byte-identical)."""
    by = {s: r for r, s in LO.slot_map(doc['levels']).items()}      # slot -> research slot
    out = copy.deepcopy(doc)
    lv = []
    for l in out['levels']:
        l['level'] = by[l['level']]
        lv.append(l)
    out['levels'] = sorted(lv, key=lambda l: l['level'])
    return out


def permute(research, order):
    """The research-order doc re-ordered: slot s holds research board order[s]; only `level` changes."""
    old = {l['level']: l for l in research['levels']}
    if sorted(order) != sorted(order.values()) or sorted(order) != sorted(old):
        raise SystemExit('reorder_levels: the order is not a permutation of the %d levels' % len(old))
    out = copy.deepcopy(research)
    new = []
    for s in range(1, len(old) + 1):
        l = copy.deepcopy(old[order[s]])
        l['level'] = s
        new.append(l)
    out['levels'] = new
    return out


def canon(l, drop=('level',)):
    return json.dumps({k: v for k, v in l.items() if k not in drop}, sort_keys=True, separators=(',', ':'))


def verify(research, applied, order, P=None):
    """H1-H10 (level-reorder.md §4) on the applied doc. Returns a list of failures (empty = pass) and the curve numbers."""
    bad = []
    R, A = research['levels'], applied['levels']
    if len(R) != len(A):
        return ['level count %d vs %d' % (len(R), len(A))], None
    if sorted(canon(l) for l in R) != sorted(canon(l) for l in A):
        bad.append('H10 the multiset of boards (every key but level) changed')
    for k in sorted(set(research) | set(applied)):
        if k != 'levels' and research.get(k) != applied.get(k):
            bad.append('H10 document section %s changed' % k)
    for s in range(1, len(A) + 1):
        a, r = A[s - 1], R[s - 1]
        if a['level'] != s:
            bad.append('L%d is numbered %d' % (s, a['level']))
        frozen = s <= FREEZE_TO or s in ANCHORS or s > ZONE_END
        if frozen and canon(a, ()) != canon(r, ()):
            bad.append('H10 frozen L%d changed' % s)
        if a['tag'] != r['tag']:
            bad.append('H3 L%d tag %s -> %s' % (s, r['tag'], a['tag']))
        if a.get('unlock') != r.get('unlock'):
            bad.append('H10 L%d unlock %s -> %s' % (s, r.get('unlock'), a.get('unlock')))
        if canon(a) != canon(R[order[s] - 1]):
            bad.append('L%d does not hold research board %d' % (s, order[s]))
    if BL.feature_first_levels(A) != BL.feature_first_levels(R):
        bad.append('H1 first appearances %s -> %s' % (BL.feature_first_levels(R), BL.feature_first_levels(A)))
    if LO.order_of(A) != order:
        bad.append('provenance does not resolve to the plan order')
    P = P or Problem([features(l) for l in R])
    used = [s for s in P.zone if P.forbidden(order[s], s)]      # every zone slot, moved or not (the copied order fails)
    if used:
        bad.append('H1/H2/H4/H5/H6 forbidden cells used at %s' % used)
    v = P.pair_violations(order)
    if v:
        bad.append('H4/H5/H7/H8 pairwise %s' % v[:5])
    J, out = P.devs(order)
    if not P.within(out):
        bad.append('H9 curve outside tolerance %s' % {k: round(x, 4) for k, x in out.items()})
    return bad, (J, out)


# ------------------------------------------------------------------------------------------------ plan
def search(research):
    F = [features(l) for l in research['levels']]
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
    if not best:
        raise SystemExit('reorder_levels: no attempt satisfies the rules (%s)' % fails)
    return best, passed, fails, P


def make_plan(doc, levels_rel='design/levels.json'):
    research = research_doc(doc)
    rtext = doc_text(research)
    (J, k, order, out), passed, fails, P = search(research)
    applied = permute(research, order)
    bad, _ = verify(research, applied, order, P)
    if bad:
        raise SystemExit('reorder_levels: the search result fails its own rules: %s' % bad)
    def name(s):
        lab = LO.label(applied['levels'][s - 1])
        return lab if lab.endswith('L%d' % order[s]) else '%s (research L%d)' % (lab, order[s])
    boards = {str(s): name(s) for s in sorted(order) if order[s] != s}
    plan = dict(
        _about='The level order (PUBLISH item 12; SPEC.md rulings 37e/39 OD8; design/publish/level-reorder.md). Written by '
               'design/tools/reorder_levels.py plan; applied by `reorder_levels.py apply` and by build_levels.py assemble. '
               'order = {slot: research slot}: slot s ships the board design/levels.json holds at L<order[s]> in the '
               'research order. input/output = sha256 of that levels.json before / after the re-order: any other content '
               'is refused until the plan is recomputed.',
        algorithm=ALGORITHM, salt=SALT, attempt=k, noise=NOISE, attempts=ATTEMPTS, rounds=ROUNDS, max_passes=MAX_PASSES,
        freeze_to=FREEZE_TO, zone_end=ZONE_END, anchors=sorted(ANCHORS), practice={str(a): b for a, b in PRACTICE.items()},
        first=FIRST, dmax=DMAX, dmin_v552=DMIN_V552, lookalike_gap=LOOKALIKE_GAP, twin_gap=TWIN_GAP, run_max=RUN_MAX,
        short_timer=dict(max_s=SHORT_TIMER, gap=SHORT_GAP), tolerance=TOL,
        search=dict(inside_tolerance=passed, rejected=dict(sorted(fails.items()))),
        J=round(J, 4), deviations={x: round(y, 4) for x, y in out.items()},
        input=dict(file=levels_rel, sha256=sha_text(rtext)),
        output=dict(sha256=sha_text(doc_text(applied))),
        moved=len(boards),
        order={str(s): o for s, o in sorted(order.items())},
        boards=boards)
    return plan


def plan_text(plan):
    return json.dumps(plan, indent=1) + '\n'


# ------------------------------------------------------------------------------------------------ apply
class Stale(SystemExit):
    pass


def apply_text(text, plan):
    """(state, new_text): 'applied' (permuted), 'already' (text is the plan's output). Raises Stale otherwise."""
    sha = sha_text(text)
    if sha == plan['output']['sha256']:
        return 'already', text
    if sha != plan['input']['sha256']:
        raise Stale('reorder_levels: STALE levels.json (sha256 %s) is neither the plan\'s input (%s) nor its output (%s): '
                    'the content changed after the plan; run `design/tools/reorder_levels.py plan` and review the new order. '
                    'Nothing was written.' % (sha[:12], plan['input']['sha256'][:12], plan['output']['sha256'][:12]))
    research = json.loads(text)
    if doc_text(research) != text:
        raise Stale('reorder_levels: the levels.json is not in build_levels.write_doc form; nothing was written')
    order = {int(s): o for s, o in plan['order'].items()}
    applied = permute(research, order)
    bad, _ = verify(research, applied, order)
    if bad:
        raise SystemExit('reorder_levels: the applied order breaks its rules: %s' % bad)
    out = doc_text(applied)
    if sha_text(out) != plan['output']['sha256']:
        raise SystemExit('reorder_levels: the result hashes to %s, the plan says %s; nothing was written'
                         % (sha_text(out)[:12], plan['output']['sha256'][:12]))
    return 'applied', out


def apply_planned(doc, plan_path=None):
    """build_levels.py assemble's hook: no plan file -> doc unchanged (the research order); a plan -> the re-ordered doc
    (sha-guarded; a stale plan stops assemble before it writes)."""
    plan = LO.load_plan(plan_path)
    if plan is None:
        return doc
    state, text = apply_text(doc_text(doc), plan)
    print('reorder_levels: %s by %s (%d boards moved)' % ('re-ordered' if state == 'applied' else 'already in plan order',
                                                         os.path.relpath(plan_path or PLAN_JSON, APP), plan['moved']))
    return json.loads(text)


def write_atomic(path, text):
    tmp = path + '.tmp-reorder'
    with open(tmp, 'w') as f:
        f.write(text)
    os.replace(tmp, path)


# ------------------------------------------------------------------------------------------------ cli
def arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv):
    if not argv or argv[0] not in ('plan', 'apply', 'check'):
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    levels = os.path.abspath(arg(rest, '--levels', LEVELS_JSON))
    plan_path = os.path.abspath(arg(rest, '--plan', PLAN_JSON))
    if cmd == 'plan':
        doc = json.load(open(levels))
        rel = os.path.relpath(levels, APP)
        plan = make_plan(doc, rel if not rel.startswith('..') else levels)
        write_atomic(plan_path, plan_text(plan))
        print('plan: attempt a%d J %.4f, %d inside tolerance %s, %d boards moved -> %s (input %s, output %s)' % (
            plan['attempt'], plan['J'], plan['search']['inside_tolerance'], plan['search']['rejected'], plan['moved'],
            os.path.relpath(plan_path, APP), plan['input']['sha256'][:12], plan['output']['sha256'][:12]))
        return 0
    plan = LO.load_plan(plan_path)
    if plan is None:
        print('reorder_levels: no plan at %s' % plan_path)
        return 2
    text = open(levels).read()
    if cmd == 'apply':
        out = os.path.abspath(arg(rest, '--out', levels))
        try:
            state, new = apply_text(text, plan)
        except Stale as e:
            print(e.code if isinstance(e.code, str) else e)
            return 2
        if state == 'already':
            if out != levels:
                write_atomic(out, new)
            print('apply: %s is already in plan order (sha256 %s): nothing to do' % (os.path.relpath(levels, APP),
                                                                                    plan['output']['sha256'][:12]))
            return 0
        write_atomic(out, new)
        print('apply: %d boards moved; %s -> %s (sha256 %s = the plan\'s output)' % (
            plan['moved'], os.path.relpath(levels, APP), os.path.relpath(out, APP), sha_text(new)[:12]))
        return 0
    # check
    sha = sha_text(text)
    if sha not in (plan['input']['sha256'], plan['output']['sha256']):
        print('check: STALE levels.json (sha256 %s): neither the plan\'s input nor its output' % sha[:12])
        return 1
    doc = json.loads(text)
    research = research_doc(doc)
    if sha_text(doc_text(research)) != plan['input']['sha256']:
        print('check: the research order rebuilt from provenance does not hash to the plan\'s input')
        return 1
    order = {int(s): o for s, o in plan['order'].items()}
    applied = permute(research, order)
    bad, (J, out) = verify(research, applied, order)
    if sha_text(doc_text(applied)) != plan['output']['sha256']:
        bad.append('the applied order does not hash to the plan\'s output')
    if '--quick' not in rest:
        again = plan_text(make_plan(doc, plan['input']['file']))
        if again != open(plan_path).read():
            bad.append('the search no longer reproduces %s byte for byte' % os.path.relpath(plan_path, APP))
    print('check: %s is the plan\'s %s; H1-H10 %s; curve %s%s' % (
        os.path.relpath(levels, APP), 'input (research order)' if sha == plan['input']['sha256'] else 'output (re-ordered)',
        'hold' if not bad else 'FAIL', {k: round(v, 3) for k, v in out.items()},
        '' if '--quick' in rest else '; the search reproduces the plan byte for byte' if not bad else ''))
    for b in bad:
        print('FAIL', b)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
