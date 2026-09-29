#!/usr/bin/env python3
"""gen_levels.py — the level generator (SPEC-gameplay §14.3, design/LEVELS.md §4).

One algorithm for both jobs:
  * DESIGNED levels L62..L150 (written into design/levels.json by build_levels.py, source "designed");
  * the ENDLESS levels past the authored end (C4's runtime port in `Generator`/`LevelProvider`, seeded by the level).

Deterministic: every random number comes from `pathrandom.PathRandom` (bit-exact with PathCore's PathRandom), seeded
by `level_seed(n, curve.salt)`. The only floating-point maths is `unit()` comparisons and the heart silhouette's
products (correctly rounded IEEE operations, no transcendental functions), so a Swift port can reproduce the boards.

Per level n (curve = levels.json "curve", fitted to the recorded L30-L61 by build_levels.py):
  1. TARGET  cycle position p = n mod 10 (p 4 = Hard, p 9 = Super Hard: the phone's cadence 34/44/54 and 39/49/59);
             template = the recorded level at the same position of a recorded decade (L3p, L4p, L5p in rotation);
             targets = its units / waves / free-at-start / size, grown by `growth(n)`; obstacle kinds from the fitted
             frequency table; a silhouette with probability `silhouette.p` (obstacle-free or tape-only levels).
  2. REGIONS doors (rectangles in opening order), an elevator platform, boxes, pipes (tube paths) and tape bundles are
             laid out without overlap; the remaining cells are tiled with snakes (lengths from the recorded
             histogram, straightness 0.64), each door rectangle and the platform (both layers) separately.
  3. HEADS   a plain peel + head-flip local search on the dependency DAG gives every snake a PREFERRED head (depth and
             free-at-start toward the targets).
  4. PEEL    a forward removal simulation under the full rules chooses each snake's head (the preferred one when its
             ray is clear), picks the key riders (a door opens right after its rider leaves), breaks a box or a pipe
             exactly when nothing else can move (its counter = the removals / passages so far), and splits a snake
             when the board is stuck. The removal order is a witness: the level is solvable by construction.
  5. CHECK   arrowcore's greedy solver must solve the final level; the bot at 0.6 s per tap must keep >= 20 % of the
             timer. `curve.attempts` candidates (seed forks "a0", "a1", ...); the one closest to the targets wins.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arrowcore as ac  # noqa: E402
from pathrandom import PathRandom, level_seed  # noqa: E402

DIRL = ['up', 'down', 'left', 'right']
TAG_BY_POS = {4: 'hard', 9: 'superHard'}


class Fail(Exception):
    pass


# ============================================================================================== helpers
def lens_sampler(curve):
    table = sorted((int(k), v) for k, v in curve['lengths'].items())
    total = sum(v for _, v in table)

    def sample(rng):
        x = rng.below(total)
        for k, v in table:
            if x < v:
                return k
            x -= v
        return 2
    return sample


def in_grid(c, W, H):
    return 0 <= c[0] < W and 0 <= c[1] < H


def ray_iter(head, d, W, H):
    q = ac.step(head, d)
    while 0 <= q[0] < W and 0 <= q[1] < H:
        yield q
        q = ac.step(q, d)


def orient(cells):
    return (list(cells), ac.dir_between(cells[-2], cells[-1]))


def rect(c0, r0, c1, r1):
    return {(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}


# ============================================================================================== silhouettes
def mask_for(shape, W, H):
    """Integer-exact silhouettes (set of playable cells); None = the full rectangle."""
    out = set()
    for r in range(H):
        for c in range(W):
            dx, dy = 2 * c - (W - 1), 2 * r - (H - 1)          # doubled offsets from the centre
            if shape == 'oval':
                ok = dx * dx * H * H + dy * dy * W * W <= W * W * H * H
            elif shape == 'octagon':
                ok = abs(dx) + abs(dy) <= ((W + H) * 5) // 6
            elif shape == 'diamond':
                ok = abs(dx) * H + abs(dy) * W <= (W * H * 4) // 3
            elif shape == 'notch':                               # a "C": a notch cut from the right middle (L60)
                ok = not (c >= W // 2 and abs(dy) < H // 3)
            elif shape == 'blocks':                              # a wide block on top, two blocks below (L55)
                top = r < (H * 2) // 5
                ok = top or (r != (H * 2) // 5 and abs(dx) > 1)
            elif shape == 'cross':
                ok = abs(dx) <= (W * 2) // 3 or abs(dy) <= (H * 2) // 3
            elif shape == 'heart':                               # the spike's heart curve (L6 is a heart)
                x = (c + 0.5) / W * 2.44 - 1.22
                y = 1.28 - (r + 0.5) / H * 2.36
                a = x * x + y * y - 1
                ok = a * a * a - x * x * y * y * y <= 0
            elif shape == 'arch':                                # rounded top, flat bottom
                ok = dy >= 0 or dx * dx * H * H + dy * dy * W * W <= W * W * H * H
            else:
                ok = True
            if ok:
                out.add((c, r))
    return out


# ============================================================================================== tiling
def tile(cells, rng, sample_len, straight):
    """Cover `cells` (a set) with snakes (paths of >= 2 cells); leftovers of 1 cell join a neighbour's end or stay empty."""
    free = set(cells)
    order = sorted(cells, key=lambda c: (c[1], c[0]))
    rng.shuffle(order)
    snakes = []
    for s in order:
        if s not in free:
            continue
        target = sample_len(rng)
        path = [s]
        free.discard(s)
        d = DIRL[rng.below(4)]
        for end in (0, 1):
            while len(path) < target:
                cur = path[-1] if end == 0 else path[0]
                if len(path) >= 2:
                    d = ac.dir_between(path[-2], path[-1]) if end == 0 else ac.dir_between(path[1], path[0])
                turn = ['left', 'right'] if d in ('up', 'down') else ['up', 'down']
                if rng.below(2):
                    turn.reverse()
                opts = ([d] + turn) if rng.chance(straight) else (turn + [d])
                nxt = None
                for o in opts:
                    q = ac.step(cur, o)
                    if q in free:
                        nxt = (q, o)
                        break
                if nxt is None:
                    break
                free.discard(nxt[0])
                if end == 0:
                    path.append(nxt[0])
                else:
                    path.insert(0, nxt[0])
                d = nxt[1]
        snakes.append(path)
    idx = {}
    for i, p in enumerate(snakes):
        for c in p:
            idx[c] = i
    for i, p in enumerate(snakes):
        if len(p) != 1:
            continue
        c = p[0]
        for d in DIRL:
            q = ac.step(c, d)
            j = idx.get(q)
            if j is None or j == i or len(snakes[j]) < 2:
                continue
            if snakes[j][0] == q:
                snakes[j].insert(0, c)
            elif snakes[j][-1] == q:
                snakes[j].append(c)
            else:
                continue
            idx[c] = j
            p.clear()
            break
    return [p for p in snakes if len(p) >= 2]


def merge(snakes, rng, target_units, max_len):
    snakes = [list(p) for p in snakes]
    while len(snakes) > target_units:
        ends = {}
        for i, p in enumerate(snakes):
            ends.setdefault(p[0], []).append((i, 0))
            ends.setdefault(p[-1], []).append((i, 1))
        pairs = []
        for i, p in enumerate(snakes):
            for side, c in ((0, p[0]), (1, p[-1])):
                for dd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (c[0] + dd[0], c[1] + dd[1])
                    for j, sj in ends.get(q, []):
                        if j > i and len(p) + len(snakes[j]) <= max_len:
                            pairs.append((i, side, j, sj))
        if not pairs:
            break
        i, si, j, sj = pairs[rng.below(len(pairs))]
        a = snakes[i] if si == 1 else snakes[i][::-1]
        b = snakes[j] if sj == 0 else snakes[j][::-1]
        snakes[i] = a + b
        snakes.pop(j)
    return snakes


# ============================================================================================== preferred heads (plain board)
def plain_peel(W, H, snakes, rng):
    snakes = [list(p) for p in snakes]
    owner = {}
    for i, p in enumerate(snakes):
        for c in p:
            owner[c] = i
    alive = set(range(len(snakes)))

    def clear(cells, d, me, extra=()):
        own = set(cells)
        for q in ray_iter(cells[-1], d, W, H):
            if q in own or q in extra:
                return False
            o = owner.get(q)
            if o is not None and o in alive and o != me:
                return False
        return True

    order = []
    while alive:
        cands = []
        for i in sorted(alive):
            p = snakes[i]
            for cells in (p, p[::-1]):
                d = ac.dir_between(cells[-2], cells[-1])
                if clear(cells, d, i):
                    cands.append((i, cells, d))
        if not cands:
            best = []
            for i in sorted(alive):
                p = snakes[i]
                for k in range(2, len(p) - 1):
                    a, b = p[:k], p[k:]
                    for piece, other in ((a, b), (a[::-1], b), (b, a), (b[::-1], a)):
                        if clear(piece, ac.dir_between(piece[-2], piece[-1]), i, extra=set(other)):
                            best.append((i, k))
                            break
            if not best:
                return None
            i, k = best[rng.below(len(best))]
            p = snakes[i]
            j = len(snakes)
            snakes[i] = p[:k]
            snakes.append(p[k:])
            for c in snakes[j]:
                owner[c] = j
            alive.add(j)
            continue
        i, cells, d = cands[rng.below(len(cands))]
        alive.discard(i)
        order.append((list(cells), d))
    return order


class Dag:
    """Dependency DAG of a plain board: an arrow depends on every arrow on its ray."""

    def __init__(self, arrows, W, H):
        self.A = [dict(cells=[tuple(c) for c in a[0]], dir=a[1]) for a in arrows]
        self.W, self.H = W, H
        self.owner = {}
        for i, a in enumerate(self.A):
            for c in a['cells']:
                self.owner[c] = i
        self.deps = [self._deps(i) for i in range(len(self.A))]

    def _deps(self, i):
        a = self.A[i]
        return {self.owner[q] for q in ray_iter(a['cells'][-1], a['dir'], self.W, self.H)
                if q in self.owner and self.owner[q] != i}

    def evaluate(self):
        n = len(self.A)
        depth = [0] * n
        state = [0] * n
        for s in range(n):
            if state[s]:
                continue
            stack = [(s, iter(sorted(self.deps[s])))]
            state[s] = 1
            while stack:
                v, it = stack[-1]
                nxt = next(it, None)
                if nxt is None:
                    depth[v] = 1 + max((depth[w] for w in self.deps[v]), default=0)
                    state[v] = 2
                    stack.pop()
                elif state[nxt] == 1:
                    return None
                elif state[nxt] == 0:
                    state[nxt] = 1
                    stack.append((nxt, iter(sorted(self.deps[nxt]))))
        return (max(depth) if depth else 0), sum(1 for d in self.deps if not d)

    def flip(self, i):
        a = self.A[i]
        cells = a['cells'][::-1]
        d = ac.dir_between(cells[-2], cells[-1])
        if any(q in set(cells) for q in ray_iter(cells[-1], d, self.W, self.H)):
            return False
        self.A[i] = dict(cells=cells, dir=d)
        self.deps[i] = self._deps(i)
        return True


def optimise(dag, rng, R, F, steps):
    cur = dag.evaluate()
    if cur is None:
        return None

    def cost(e):
        return abs(e[0] - R) / max(1.0, R) + abs(e[1] - F) / max(3.0, F)
    best = cost(cur)
    n = len(dag.A)
    for _ in range(steps):
        if best < 0.04 or n == 0:
            break
        i = rng.below(n)
        saved = (dag.A[i], dag.deps[i])
        if not dag.flip(i):
            continue
        e = dag.evaluate()
        if e is not None and cost(e) <= best:
            best, cur = cost(e), e
        else:
            dag.A[i], dag.deps[i] = saved
    return cur


# ============================================================================================== region planning
def door_layout(rng, W, H, n_hint):
    """Door rectangles in OPENING order, after the recorded layouts (LEVELS.md §3.3)."""
    styles = ['bottomBand', 'topBand', 'middleBand'] if n_hint == 1 else \
        ['stackedBottom', 'leftHalf2', 'quadrants2', 'ring4', 'staircase', 'twoBottomOneTop', 'bottomBand', 'topBand']
    style = styles[rng.below(len(styles))]
    h = max(4, (H * (30 + rng.below(20))) // 100)
    if style == 'bottomBand':
        return style, [rect(0, H - h, W - 1, H - 1)]
    if style == 'topBand':
        return style, [rect(0, 0, W - 1, h - 1)]
    if style == 'middleBand':
        r0 = (H - h) // 2
        return style, [rect(0, r0, W - 1, r0 + h - 1)]
    if style == 'stackedBottom':
        h2 = max(4, h // 2 + 1)
        return style, [rect(0, H - h2, W - 1, H - 1), rect(0, H - 2 * h2, W - 1, H - h2 - 1)]
    if style == 'leftHalf2':
        w = max(4, W // 2)
        return style, [rect(0, 0, w - 1, H // 2 - 1), rect(0, H // 2, w - 1, H - 1)]
    if style == 'quadrants2':
        return style, [rect(0, 0, W // 2 - 1, H // 2 - 1), rect(W // 2, H // 2, W - 1, H - 1)]
    if style == 'ring4':
        t = 4
        return style, [rect(t + 1, H - t, W - t - 2, H - 1), rect(0, t + 2, t, H - t - 3),
                       rect(W - t - 1, t + 2, W - 1, H - t - 3), rect(t + 1, 0, W - t - 2, t - 1)]
    if style == 'staircase':
        k = 3 + rng.below(3)
        w = max(4, W // k)
        out = []
        for i in range(k):
            c0 = i * w
            if c0 + 3 >= W:
                break
            c1 = W - 1 if i == k - 1 else min(W - 1, (i + 1) * w - 1)
            hh = max(4, (H * (i + 1)) // (k + 1))
            out.append(rect(c0, H - hh, c1, H - 1))
        return style, out
    half = H // 2                                         # twoBottomOneTop (L37)
    return style, [rect(0, half, W // 2 - 1, H - 1), rect(W // 2, half, W - 1, H - 1), rect(0, 0, W - 1, half - 1)]


def box_layout(rng, W, H):
    style = ['corner', 'bottomBar', 'pairCorners', 'staircase', 'side'][rng.below(5)]
    if style == 'corner':
        w, h = 3 + rng.below(6), 3 + rng.below(6)
        c0 = 0 if rng.below(2) else W - w
        r0 = 0 if rng.below(2) else H - h
        return style, [rect(c0, r0, c0 + w - 1, r0 + h - 1)]
    if style == 'bottomBar':
        return style, [rect(0, H - 3, W - 1, H - 1)]
    if style == 'pairCorners':
        w, h = 3 + rng.below(5), 3 + rng.below(5)
        return style, [rect(0, 0, w - 1, h - 1), rect(W - w, H - h, W - 1, H - 1)]
    if style == 'staircase':
        k = 3 + rng.below(2)
        w = max(3, W // (k + 1))
        return style, [rect(W - (k - i) * w, H - 3 * (i + 1), W - (k - i) * w + w - 1, H - 1) for i in range(k)]
    w, h = 3, 3 + rng.below(4)
    c0 = 0 if rng.below(2) else W - w
    r0 = (H - h) // 2
    return style, [rect(c0, r0, c0 + w - 1, r0 + h - 1)]


def pipe_shape(rng, W, H):
    """A tube path listed mouth -> mouth, after the recorded shapes (∩ caps L48, ⊏/⊐ L49/L56, ∪ L42, ┐ L35)."""
    kind = ['capTop', 'uSide', 'uBottom', 'lCorner'][rng.below(4)]
    if kind == 'capTop':
        w, h = 4 + rng.below(3), 4 + rng.below(2)
        c0 = rng.below(max(1, W - w))
        return kind, [(c0, r) for r in range(h - 1, -1, -1)] + [(c, 0) for c in range(c0 + 1, c0 + w)] + \
            [(c0 + w - 1, r) for r in range(1, h)]
    if kind == 'uSide':
        w, h = 4, 5
        left = rng.below(2) == 0
        c0 = 0 if left else W - w
        r0 = 1 + rng.below(max(1, H - h - 1))
        if left:
            return kind, [(c0 + w - 1 - i, r0) for i in range(w)] + [(c0, r0 + i) for i in range(1, h)] + \
                [(c0 + i, r0 + h - 1) for i in range(1, w)]
        return kind, [(c0 + i, r0) for i in range(w)] + [(c0 + w - 1, r0 + i) for i in range(1, h)] + \
            [(c0 + w - 1 - i, r0 + h - 1) for i in range(1, w)]
    if kind == 'uBottom':
        w, h = 3 + rng.below(4), 4
        c0 = rng.below(max(1, W - w))
        r1 = H - 1
        return kind, [(c0, r1 - h + 1 + i) for i in range(h)] + [(c, r1) for c in range(c0 + 1, c0 + w)] + \
            [(c0 + w - 1, r1 - i) for i in range(1, h)]
    w, h = 5 + rng.below(4), 6 + rng.below(5)
    return kind, [(W - w + i, 0) for i in range(w)] + [(W - 1, r) for r in range(1, h)]


# CornerTurn of a corner whose plate faces the diagonal (sx, sy) (y down) = import_research.FACING_TURN (v552 L70-L82).
FACING_TURN = {(1, -1): 'downRight', (-1, -1): 'downLeft', (1, 1): 'upRight', (-1, 1): 'upLeft'}
CORNER_SIDES = ['right', 'left', 'bottom', 'top']
OPPOSITE = dict(right='left', left='right', bottom='top', top='bottom')


def corner_layout(rng, W, H, used):
    """Corners on an EMPTY margin line of the board, facing it (v552 L76/L79/L80/L82: 1-3 corners per side beside the
    arrow block; a ray leaving the block there turns along the margin, and a second corner can send it back in)."""
    n_sides = 1 if rng.chance(0.6) else 2
    order = list(CORNER_SIDES)
    rng.shuffle(order)
    margin, corners, sides = set(), [], []
    for side in order:
        if len(sides) >= n_sides:
            break
        if sides and OPPOSITE[side] == sides[0]:
            continue                  # two sides are ADJACENT: a ray can never come back round, so no corner loop exists
        if side in ('right', 'left'):
            x = W - 1 if side == 'right' else 0
            line = [(x, r) for r in range(1, H - 1)]
            facings = [(-1, -1), (-1, 1)] if side == 'right' else [(1, -1), (1, 1)]
        else:
            y = H - 1 if side == 'bottom' else 0
            line = [(c, y) for c in range(1, W - 1)]
            facings = [(-1, -1), (1, -1)] if side == 'bottom' else [(-1, 1), (1, 1)]
        if len(line) < 3 or any(c in used or c in margin for c in line):
            continue
        k = 1 + rng.below(3)
        picks = []
        for _ in range(4 * k):
            if len(picks) >= k:
                break
            i = rng.below(len(line))
            if i not in picks:
                picks.append(i)
        for i in sorted(picks):
            corners.append((line[i], FACING_TURN[facings[rng.below(2)]]))
        margin |= set(line)
        sides.append(side)
    return sides, margin, corners


def plan_regions(rng, W, H, kinds):
    used = set()
    plan = dict(doors=[], door_style=None, boxes=[], box_style=None, pipes=[], tapes=[], elevator=None, corners=[],
                corner_sides=None)

    def fits(cells):
        return all(in_grid(c, W, H) for c in cells) and not (set(cells) & used)
    for k in kinds:
        if k == 'door':
            n_hint = 1 if rng.chance(0.4) else 2
            ok = False
            for _ in range(4):
                style, rects = door_layout(rng, W, H, n_hint)
                rects = [r for r in rects if len(r) >= 16]
                if rects and all(fits(r) for r in rects) and not any(a & b for i, a in enumerate(rects)
                                                                     for b in rects[i + 1:]):
                    plan['doors'] = rects
                    plan['door_style'] = style
                    for r in rects:
                        used |= r
                    ok = True
                    break
            if not ok:
                raise Fail('door layout')
        elif k == 'elevator':
            ok = False
            for _ in range(8):
                w = min(W - 2, 6 + rng.below(7))
                h = min(H - 2, 4 + rng.below(4))
                c0 = 1 + rng.below(max(1, W - w - 1))
                r0 = 1 + rng.below(max(1, H - h - 1))
                R = rect(c0, r0, c0 + w - 1, r0 + h - 1)
                if fits(R):
                    plan['elevator'] = R
                    used |= R
                    ok = True
                    break
            if not ok:
                raise Fail('elevator layout')
        elif k == 'box':
            ok = False
            for _ in range(6):
                style, rects = box_layout(rng, W, H)
                if rects and all(fits(r) for r in rects) and not any(a & b for i, a in enumerate(rects)
                                                                     for b in rects[i + 1:]):
                    plan['boxes'] = rects
                    plan['box_style'] = style
                    for r in rects:
                        used |= r
                    ok = True
                    break
            if not ok:
                raise Fail('box layout')
        elif k == 'pipe':
            want = 1 + (1 if rng.chance(0.4) else 0) + (1 if rng.chance(0.15) else 0)
            for _ in range(10 * want):
                if len(plan['pipes']) >= want:
                    break
                kind, path = pipe_shape(rng, W, H)
                if len(set(path)) != len(path) or not fits(path):
                    continue
                # the mouths must face a board cell that is free for arrows
                okm = True
                for m, prev in ((path[0], path[1]), (path[-1], path[-2])):
                    out = ac.dir_between(prev, m)
                    q = ac.step(m, out)
                    if not in_grid(q, W, H) or q in used:
                        okm = False
                if not okm:
                    continue
                # FEEDERS: straight arrows lined up in front of ONE mouth, pointing into it (the recorded pattern: L35's
                # two arrows aimed at the mouth, L48's columns under their caps). The other mouth's lane stays free:
                # that is where the passing arrows leave. Target passes 2-5 (recorded counters: median 3-4).
                entry = rng.below(2)
                m, prev = (path[0], path[1]) if entry == 0 else (path[-1], path[-2])
                out = ac.dir_between(prev, m)
                want_pass = [2, 3, 3, 4, 4, 5][rng.below(6)]
                lane = []
                q = ac.step(m, out)
                while in_grid(q, W, H) and q not in used and q not in set(path):
                    lane.append(q)
                    q = ac.step(q, out)
                feeders, k = [], 0
                while len(feeders) < want_pass:
                    L = 2 + rng.below(3)
                    if k + L > len(lane):
                        break
                    seg = lane[k:k + L]                 # nearest the mouth first
                    feeders.append((list(reversed(seg)), ac.OPP[out]))   # tail far, head next to the mouth
                    k += L
                if not feeders:
                    continue
                plan['pipes'].append(path)
                plan.setdefault('feeders', []).extend(feeders)
                used |= set(path)
                for cells, _ in feeders:
                    used |= set(cells)
            if not plan['pipes']:
                raise Fail('pipe layout')
        elif k == 'tape':
            want = 1 + rng.below(4)
            for _ in range(8 * want):
                if len(plan['tapes']) >= want:
                    break
                lanes = 2 + rng.below(3)
                L = 4 if rng.chance(0.75) else 3
                d = DIRL[rng.below(4)]
                horiz = d in ('left', 'right')
                bw, bh = (L, lanes) if horiz else (lanes, L)
                if bw > W or bh > H:
                    continue
                c0 = rng.below(W - bw + 1)
                r0 = rng.below(H - bh + 1)
                R = rect(c0, r0, c0 + bw - 1, r0 + bh - 1)
                if not fits(R):
                    continue
                members = []
                for lane in range(lanes):
                    if horiz:
                        cells = [(c0 + i, r0 + lane) for i in range(L)]
                        cells = cells[::-1] if d == 'left' else cells
                    else:
                        cells = [(c0 + lane, r0 + i) for i in range(L)]
                        cells = cells[::-1] if d == 'up' else cells
                    members.append((cells, d))
                plan['tapes'].append(members)
                used |= R
            if not plan['tapes']:
                raise Fail('tape layout')
        elif k == 'corner':
            sides, margin, corners = corner_layout(rng, W, H, used)
            if not corners:
                raise Fail('corner layout')
            plan['corners'] = corners
            plan['corner_sides'] = sides
            used |= margin
    plan['used'] = used
    return plan


# ============================================================================================== the obstacle-aware peel
class Peel:
    """Forward removal simulation under the full rules, choosing heads, key riders and counters as it goes."""

    def __init__(self, W, H, units, plan, rng, prefs, total_visible):
        self.W, self.H, self.rng, self.plan = W, H, rng, plan
        self.U = units                                    # id -> dict(kind, cells|members, region, layer)
        self.prefs = prefs                                # frozenset(cells) -> preferred oriented cells
        self.alive = set(units)
        self.nd = len(plan['doors'])
        self.door_open = [False] * self.nd
        self.riders = [None] * self.nd
        self.door_cell = {}
        for k, R in enumerate(plan['doors']):
            for c in R:
                self.door_cell[c] = k
        self.box_cell = {}
        for j, R in enumerate(plan['boxes']):
            for c in R:
                self.box_cell[c] = j
        self.box_broken = [False] * len(plan['boxes'])
        self.box_C = [None] * len(plan['boxes'])
        self.pipe_cell, self.pipe_end, self.pipe_other = {}, {}, {}
        for p, path in enumerate(plan['pipes']):
            for c in path:
                self.pipe_cell[c] = p
            e0, e1 = (path[0], ac.dir_between(path[1], path[0])), (path[-1], ac.dir_between(path[-2], path[-1]))
            self.pipe_end[e0[0]] = (p, e0[1])
            self.pipe_end[e1[0]] = (p, e1[1])
            self.pipe_other[(p, e0[0])] = e1
            self.pipe_other[(p, e1[0])] = e0
        self.pipe_broken = [False] * len(plan['pipes'])
        self.corner = {c: t for c, t in plan.get('corners', [])}
        self.pipe_pass = [0] * len(plan['pipes'])
        self.pipe_C = [None] * len(plan['pipes'])
        self.elev_active = False
        self.occ = {1: {}, 2: {}}
        for i, u in units.items():
            for c in self.cells(u):
                self.occ[u['layer']][c] = i
        self.count = 0
        self.total_visible = total_visible
        self.orient = {}
        self.witness = []
        self.next_id = max(units) + 1 if units else 0

    @staticmethod
    def cells(u):
        if u['kind'] in ('bundle', 'fixed'):
            return [c for m in u['members'] for c in m[0]]
        return u['cells']

    def visible(self, i):
        r = self.U[i]['region']
        if r[0] == 'door':
            return self.door_open[r[1]]
        if r[0] == 'l2':
            return self.elev_active
        return True

    def blocked(self, q, me):
        k = self.door_cell.get(q)
        if k is not None and not self.door_open[k]:
            return True
        j = self.box_cell.get(q)
        if j is not None and not self.box_broken[j]:
            return True
        o = self.occ[1].get(q)
        if o is not None and o != me and o in self.alive:
            return True
        o = self.occ[2].get(q)
        if o is not None and o != me and o in self.alive and self.elev_active:
            return True
        return False

    def ray(self, cells, d, me):
        """(clear?, passages)."""
        own = set(cells)
        c = cells[-1]
        passages = []
        hops = 0
        while True:
            q = ac.step(c, d)
            if not in_grid(q, self.W, self.H):
                return True, passages
            p = self.pipe_cell.get(q)
            if p is not None and not self.pipe_broken[p]:
                e = self.pipe_end.get(q)
                if e is not None and e[0] == p and e[1] == ac.OPP[d] and hops < ac.MAX_HOPS:
                    hops += 1
                    passages.append(p)
                    c, d = self.pipe_other[(p, q)]
                    continue
                return False, passages
            t = self.corner.get(q)
            if t is not None:                         # arrowcore.walk: a corner turns the ray or blocks it
                nd = ac.CORNER[t].get(d)
                if nd is None or hops >= ac.MAX_HOPS:
                    return False, passages
                hops += 1
                c, d = q, nd
                continue
            if q in own or self.blocked(q, me):
                return False, passages
            c = q

    def options(self, i):
        u = self.U[i]
        if u['kind'] in ('bundle', 'fixed'):
            passes = []
            for cells, d in u['members']:
                ok, ps = self.ray(cells, d, i)
                if not ok:
                    return []
                passes += ps
            return [(None, passes)]
        out = []
        for cells in (u['cells'], u['cells'][::-1]):
            cells, d = orient(cells)
            ok, ps = self.ray(cells, d, i)
            if ok:
                out.append(((cells, d), ps))
        return out

    def candidates(self):
        res = []
        for i in sorted(self.alive):
            if not self.visible(i):
                continue
            opts = self.options(i)
            if opts:
                res.append((i, opts))
        return res

    def remove(self, i, opt):
        o, passes = opt
        u = self.U[i]
        if o is not None:
            self.orient[i] = o
        self.alive.discard(i)
        self.witness.append(i)
        self.count += len(u['members']) if u['kind'] in ('bundle', 'fixed') else 1
        for p in passes:
            self.pipe_pass[p] += 1
        for k in range(self.nd):
            if self.riders[k] == i:
                self.door_open[k] = True
        plat = [x for x, v in self.U.items() if v['region'][0] == 'plat']
        if plat and not self.elev_active and not any(x in self.alive for x in plat):
            self.elev_active = True

    def split(self):
        best = []
        for i in sorted(self.alive):
            u = self.U[i]
            if u['kind'] != 'snake' or not self.visible(i):
                continue
            p = u['cells']
            for k in range(2, len(p) - 1):
                a, b = p[:k], p[k:]
                for piece, other in ((a, b), (a[::-1], b), (b, a), (b[::-1], a)):
                    cells, d = orient(piece)
                    saved = dict(self.occ[u['layer']])
                    for c in other:
                        self.occ[u['layer']][c] = -1      # the other half stays: it blocks
                    self.alive.add(-1)
                    ok, _ = self.ray(cells, d, i)
                    self.alive.discard(-1)
                    self.occ[u['layer']] = saved
                    if ok:
                        best.append((i, k))
                        break
        if not best:
            return False
        i, k = best[self.rng.below(len(best))]
        u = self.U[i]
        p = u['cells']
        j = self.next_id
        self.next_id += 1
        self.U[j] = dict(kind='snake', cells=p[k:], region=u['region'], layer=u['layer'])
        u['cells'] = p[:k]
        for c in self.U[j]['cells']:
            self.occ[u['layer']][c] = j
        self.alive.add(j)
        return True

    def try_break(self):
        """Nothing can move: break the box or pipe whose break frees something (counter = the count so far)."""
        for j in range(len(self.box_broken)):
            if self.box_broken[j] or self.count < 1:
                continue
            self.box_broken[j] = True
            if self.candidates():
                self.box_C[j] = self.count
                return True
            self.box_broken[j] = False
        for p in range(len(self.pipe_broken)):
            if self.pipe_broken[p] or self.pipe_pass[p] < 1:
                continue
            self.pipe_broken[p] = True
            if self.candidates():
                self.pipe_C[p] = self.pipe_pass[p]
                return True
            self.pipe_broken[p] = False
        return False

    def run(self):
        rng = self.rng
        guard = 0
        while self.alive:
            guard += 1
            if guard > 6000:
                raise Fail('peel guard')
            cands = self.candidates()
            if not cands:
                if self.try_break():
                    continue
                if self.split():
                    continue
                raise Fail('peel stuck')
            # moves that keep a snake's PREFERRED head (the DAG search's orientation) come first; on a plain board
            # they are a topological order of that acyclic DAG, so the fallback is only needed around obstacles
            pref = []
            for i, opts in cands:
                u = self.U[i]
                if u['kind'] in ('bundle', 'fixed'):
                    pref.append((i, opts))
                    continue
                pc = self.prefs.get(frozenset(u['cells']))
                po = [o for o in opts if pc is not None and o[0][0] == pc]
                if po or pc is None:
                    pref.append((i, po or opts))
            if pref:
                cands = pref
            # a key rider for the next locked door: early (the recorded doors open in the first rounds), chained
            nxt = next((k for k in range(self.nd) if self.riders[k] is None), None)
            if nxt is not None:
                thr = (self.total_visible * (5 + 18 * nxt)) // 100
                snakes = [c for c in cands if self.U[c[0]]['kind'] == 'snake']
                if snakes and (self.count >= thr or len(cands) <= 2):
                    pool = snakes
                    if nxt > 0 and rng.chance(0.5):
                        prev = [c for c in snakes if self.U[c[0]]['region'] == ('door', nxt - 1)]
                        pool = prev or snakes
                    i, opts = pool[rng.below(len(pool))]
                    self.riders[nxt] = i
                    self.remove(i, self.pick_option(i, opts))
                    continue
            piped = [c for c in cands if any(ps for _, ps in c[1])]
            if piped and rng.chance(0.6):
                i, opts = piped[rng.below(len(piped))]
                opts = [o for o in opts if o[1]] or opts
            else:
                i, opts = cands[rng.below(len(cands))]
            self.remove(i, self.pick_option(i, opts))
        return self

    def pick_option(self, i, opts):
        if len(opts) == 1:
            return opts[0]
        u = self.U[i]
        pref = self.prefs.get(frozenset(u['cells'])) if u['kind'] == 'snake' else None
        if pref is not None:
            for o in opts:
                if o[0][0] == pref:
                    return o
        return opts[self.rng.below(len(opts))]


# ============================================================================================== targets
def growth(curve, n):
    g = curve['growth']
    steps = max(0, (n - g['from']) // 10)
    return min(g['cap'], 1.0 + g['perDecade'] * steps)


def target_for(curve, n):
    p = n % 10
    tag = TAG_BY_POS.get(p, 'normal')
    slot = (n // 10) % curve.get('slots', 3)
    tpl = next(t for t in curve['templates'] if t['pos'] == p and t['slot'] == slot)
    gr = growth(curve, n)
    return dict(n=n, pos=p, tag=tag, template=tpl['level'],
                units=int(tpl['units'] * gr + 0.5),
                rounds=int(tpl['rounds'] * (1 + (gr - 1) / 2) + 0.5),
                free=tpl['free'],
                cols=min(curve['maxCols'], max(10, int(tpl['cols'] * (1 + (gr - 1) / 2) + 0.5))),
                rows=min(curve['maxRows'], max(12, int(tpl['rows'] * (1 + (gr - 1) / 2) + 0.5))),
                template_timer=tpl['timer'])


def obstacle_plan(curve, n, rng):
    ob = curve['obstacles']
    unlocked = [k for k, lvl in ob['firstLevel'].items() if lvl <= n]
    cw = ob['countWeights']
    x = rng.below(sum(cw))
    count = 0
    while x >= cw[count]:
        x -= cw[count]
        count += 1
    kinds = []
    pool = [k for k in ob['kindOrder'] if k in unlocked]
    for _ in range(count):
        opts = [k for k in pool if k not in kinds]
        if not opts:
            break
        ws = [ob['kindWeights'][k] for k in opts]
        y = rng.below(sum(ws))
        for k, w in zip(opts, ws):
            if y < w:
                kinds.append(k)
                break
            y -= w
    order = ['door', 'elevator', 'box', 'pipe', 'tape', 'corner']   # layout order: big regions first, margins last
    return sorted(kinds, key=order.index)


def timer_for(curve, tag, units, doors, rng, template_timer=None):
    t = curve['timers']
    if t.get('fromTemplate') and template_timer is not None:
        return template_timer                       # the phone's timer at the template's position (1:40 ... 3:30)
    if tag == 'hard':
        return t['hard']
    if tag == 'superHard':
        return t['superHard']
    work = units * ac.TAP_SECONDS + doors * ac.DOOR_SECONDS
    if work <= t['short'] * t['maxWorkShareShort'] and rng.chance(t['pShort']):
        return t['short']
    return t['normal']


# ============================================================================================== one candidate
def build_candidate(curve, tgt, kinds, rng):
    W, H = tgt['cols'], tgt['rows']
    sample_len = lens_sampler(curve)
    straight = curve['straight']
    shape = None
    if set(kinds) <= {'tape'} and rng.chance(curve['silhouette']['p']):
        shapes = curve['silhouette']['shapes']
        shape = shapes[rng.below(len(shapes))]
    mask = mask_for(shape, W, H) if shape else None
    if mask is not None and len(mask) < (W * H * 45) // 100:
        mask, shape = None, None
    plan = plan_regions(rng, W, H, kinds)
    if mask is not None:
        for m in plan['tapes']:
            if any(c not in mask for cells, _ in m for c in cells):
                raise Fail('tape outside the silhouette')
    allc = mask if mask is not None else rect(0, 0, W - 1, H - 1)
    out_cells = allc - plan['used']
    # unit budget per region, proportional to area (the peel's splits add ~20 %)
    tiled_area = len(out_cells) + sum(len(r) for r in plan['doors']) + (2 * len(plan['elevator']) if plan['elevator'] else 0)
    budget = max(6, (tgt['units'] * curve['mergeFactor']) // 100 - sum(1 for _ in plan['tapes']))

    def share(area):
        return max(1, (budget * area) // max(1, tiled_area))
    units = {}
    uid = 0

    def add_snakes(cells, region, layer):
        nonlocal uid
        sn = merge(tile(cells, rng, sample_len, straight), rng, share(len(cells)), curve['maxLength'])
        for p in sn:
            units[uid] = dict(kind='snake', cells=p, region=region, layer=layer)
            uid += 1
        return sn
    out_snakes = add_snakes(out_cells, ('out',), 1)
    for k, R in enumerate(plan['doors']):
        add_snakes(R, ('door', k), 1)
    if plan['elevator']:
        plat = add_snakes(plan['elevator'], ('plat',), 1)
        if len(plat) < 2:
            raise Fail('platform too small')
        add_snakes(plan['elevator'], ('l2',), 2)
    for members in plan['tapes']:
        units[uid] = dict(kind='bundle', members=members, region=('out',), layer=1)
        uid += 1
    for cells, d in plan.get('feeders', []):
        units[uid] = dict(kind='fixed', members=[(cells, d)], region=('out',), layer=1)
        uid += 1
    # preferred heads: plain peel + DAG search over the layer-1 snakes that are visible at the start
    prefs = {}
    base = [u['cells'] for u in units.values() if u['kind'] == 'snake' and u['region'] == ('out',)]
    order = plain_peel(W, H, base, rng)
    if order:
        dag = Dag(order, W, H)
        optimise(dag, rng, tgt['rounds'], tgt['free'], curve['flipSteps'])
        # the plain peel may have split snakes: the visible units become the DAG's pieces, with their heads preferred
        for i in [i for i, u in units.items() if u['kind'] == 'snake' and u['region'] == ('out',)]:
            del units[i]
        for a in dag.A:
            cells = [tuple(c) for c in a['cells']]
            units[uid] = dict(kind='snake', cells=cells, region=('out',), layer=1)
            uid += 1
            prefs[frozenset(cells)] = cells
    total_visible = sum(1 for u in units.values() if u['region'] == ('out',))
    peel = Peel(W, H, units, plan, rng, prefs, total_visible).run()
    return assemble(peel, plan, tgt, curve, rng, shape)


def key_cells(cells):
    """Two consecutive cells on a straight run of the rider, nearest its tail (the key hangs there)."""
    for i in range(len(cells) - 1):
        if i == 0 or ac.dir_between(cells[i - 1], cells[i]) == ac.dir_between(cells[i], cells[i + 1]):
            return [list(cells[i]), list(cells[i + 1])]
    return [list(cells[0]), list(cells[1])]


def assemble(peel, plan, tgt, curve, rng, shape):
    arrows, obst = [], []
    ids = {}
    nid = 0
    tapes = []
    platform, l2 = [], []
    door_reveals = {k: [] for k in range(peel.nd)}
    for i in peel.witness:
        u = peel.U[i]
        if u['kind'] == 'fixed':
            cells, d = u['members'][0]
            arrows.append(dict(id=nid, cells=[list(c) for c in cells], dir=d))
            ids[i] = nid
            nid += 1
            continue
        if u['kind'] == 'bundle':
            mids = []
            for cells, d in u['members']:
                arrows.append(dict(id=nid, cells=[list(c) for c in cells], dir=d))
                mids.append(nid)
                nid += 1
            tapes.append(dict(cells=[list(cells[len(cells) - 2]) for cells, _ in u['members']], arrows=mids))
            continue
        cells, d = peel.orient[i]
        rec = dict(id=nid, cells=[list(c) for c in cells], dir=d)
        r = u['region']
        if r[0] == 'door':
            rec['hidden_by'] = 'd%d' % r[1]
            door_reveals[r[1]].append(nid)
        elif r[0] == 'l2':
            rec['hidden_by'] = 'e0'
            rec['layer'] = 2
            l2.append(nid)
        elif r[0] == 'plat':
            platform.append(nid)
        ids[i] = nid
        arrows.append(rec)
        nid += 1
    for t, tp in enumerate(tapes):
        obst.append(dict(id='t%d' % t, kind='tape', cells=tp['cells'], arrows=tp['arrows']))
    for k, R in enumerate(plan['doors']):
        rec = dict(id='d%d' % k, kind='door', cells=sorted([list(c) for c in R]), order=k)
        if door_reveals[k]:
            rec['reveals'] = sorted(door_reveals[k])
        obst.append(rec)
    for k in range(peel.nd):
        rider = ids[peel.riders[k]]
        rc = next(a for a in arrows if a['id'] == rider)['cells']
        obst.append(dict(id='k%d' % k, kind='key', cells=key_cells([tuple(c) for c in rc]), arrows=[rider]))
    for p, path in enumerate(plan['pipes']):
        if peel.pipe_pass[p] < 1:
            raise Fail('unused pipe')
        C = peel.pipe_C[p] if peel.pipe_C[p] is not None else peel.pipe_pass[p]
        if C > 9:
            raise Fail('pipe counter %d' % C)
        ends = [dict(cell=list(path[0]), out=ac.dir_between(path[1], path[0])),
                dict(cell=list(path[-1]), out=ac.dir_between(path[-2], path[-1]))]
        obst.append(dict(id='p%d' % p, kind='pipe', cells=[list(c) for c in path], ends=ends, counter=C,
                         counter_at=[(path[0][0] + path[1][0]) / 2.0, (path[0][1] + path[1][1]) / 2.0]))
    total = len(arrows)
    for j, R in enumerate(plan['boxes']):
        C = peel.box_C[j]
        if C is None:                                     # never needed: breaks late (55-95 % of the level)
            C = max(1, (total * (55 + rng.below(41))) // 100)
            C = min(C, total - 1)
        obst.append(dict(id='b%d' % j, kind='box', cells=sorted([list(c) for c in R]), counter=C))
    if plan['elevator']:
        obst.append(dict(id='e0', kind='elevator', cells=sorted([list(c) for c in plan['elevator']]),
                         arrows=sorted(platform), reveals=sorted(l2)))
    for i, (c, t) in enumerate(plan.get('corners', [])):
        obst.append(dict(id='x%d' % i, kind='corner', cells=[list(c)], turn=t))
    lvl = dict(level=tgt['n'], source='designed', capture=None, cols=peel.W, rows=peel.H, mask=None, timer_s=180,
               hearts=3, tag=tgt['tag'], arrows=arrows, obstacles=obst)
    lvl = renumber(crop(lvl))
    probs = ac.structural_problems(lvl)
    if probs:
        raise Fail('structure: ' + probs[0])
    g = ac.greedy(lvl)
    if not g['ok']:
        raise Fail('greedy stuck')
    doors = peel.nd
    m = ac.metrics(lvl)
    lvl['timer_s'] = timer_for(curve, tgt['tag'], m['_units'], doors, rng, tgt.get('template_timer'))
    m = ac.metrics(lvl)
    if m['bot_time_left'] < 0.2 * lvl['timer_s']:
        raise Fail('time')
    notes = dict(shape=shape, door_style=plan['door_style'], box_style=plan['box_style'])
    if plan.get('corner_sides'):
        notes['corner_sides'] = plan['corner_sides']
    return lvl, m, notes


def crop(lvl):
    xs = [c[0] for a in lvl['arrows'] for c in a['cells']] + [c[0] for o in lvl['obstacles'] for c in o['cells']]
    ys = [c[1] for a in lvl['arrows'] for c in a['cells']] + [c[1] for o in lvl['obstacles'] for c in o['cells']]
    c0, r0 = min(xs), min(ys)

    def sh(c):
        return [c[0] - c0, c[1] - r0]
    for a in lvl['arrows']:
        a['cells'] = [sh(c) for c in a['cells']]
    for o in lvl['obstacles']:
        o['cells'] = [sh(c) for c in o['cells']]
        for e in o.get('ends', []):
            e['cell'] = sh(e['cell'])
        if o.get('counter_at'):
            o['counter_at'] = [o['counter_at'][0] - c0, o['counter_at'][1] - r0]
    lvl['cols'] = max(xs) - c0 + 1
    lvl['rows'] = max(ys) - r0 + 1
    return lvl


def renumber(lvl):
    """Arrow ids 0..n-1: visible arrows in reading order of their heads, then the hidden ones by hider."""
    def key(a):
        h = a['cells'][-1]
        return (1 if a.get('hidden_by') else 0, a.get('hidden_by') or '', h[1], h[0])
    order = sorted(lvl['arrows'], key=key)
    m = {a['id']: i for i, a in enumerate(order)}
    for a in order:
        a['id'] = m[a['id']]
    for o in lvl['obstacles']:
        if o.get('arrows'):
            o['arrows'] = sorted(m[x] for x in o['arrows'])
        if o.get('reveals'):
            o['reveals'] = sorted(m[x] for x in o['reveals'])
    lvl['arrows'] = sorted(order, key=lambda a: a['id'])
    return lvl


def score(tgt, m):
    return (abs(m['_units'] - tgt['units']) / max(1.0, tgt['units']) +
            abs(m['rounds'] - tgt['rounds']) / max(1.0, tgt['rounds']) +
            0.5 * abs(m['free_at_start'] - tgt['free']) / max(3.0, tgt['free']))


def generate(curve, n, target=None, kinds=None, gate=None):
    """Level n from the curve. `target` / `kinds` override the curve's (build_levels: a substitute for a repeated phone
    board is generated to that board's own size, units, waves, free arrows, timer and obstacle kinds; ORCH 19).
    `gate(level) -> None | reason` = C4's validator gate (LevelProvider / Generator.generate(gate:)): it runs on a candidate
    only when it would become the best so far; a refused candidate is rejected like a failed one ("gate: <reason>") and
    the attempt loop goes on (a refused candidate does not end the phase early). build_levels gates the designed levels
    with validate_levels.check_level, so an authored level is what the game's gated generator serves."""
    rng0 = PathRandom(level_seed(n, int(curve['salt'])))
    tgt = target if target is not None else target_for(curve, n)
    plan_kinds = obstacle_plan(curve, n, rng0.fork('plan'))
    kinds = plan_kinds if kinds is None else list(kinds)
    best, reasons = None, []
    tried_kinds = kinds
    for phase in range(len(kinds) + 1):
        tried_kinds = kinds[:len(kinds) - phase]
        for a in range(curve['attempts']):
            rng = rng0.fork('a%d.%d' % (phase, a))
            try:
                lvl, m, notes = build_candidate(curve, tgt, tried_kinds, rng)
            except Fail as e:
                reasons.append(str(e))
                continue
            s = score(tgt, m)
            if best is None or s < best[0]:
                if gate is not None:
                    cand = json.loads(json.dumps(lvl))
                    cand['seed'] = level_seed(n, int(curve['salt']))
                    cand['metrics'] = ac.bundle_metrics(m)
                    why = gate(cand)
                    if why:
                        reasons.append('gate: ' + why)
                        continue
                best = (s, lvl, m, notes, '%d.%d' % (phase, a))
            if s < curve['goodEnough']:
                break
        if best is not None:
            break
    if best is None:
        raise RuntimeError('L%d: no candidate (%s)' % (n, reasons[:8]))
    s, lvl, m, notes, a = best
    lvl['seed'] = level_seed(n, int(curve['salt']))
    lvl['metrics'] = ac.bundle_metrics(m)
    info = dict(level=n, target=tgt, planned=kinds, kinds=tried_kinds,
                got=dict(units=m['_units'], rounds=m['rounds'], free=m['free_at_start'], arrows=m['arrows'],
                         cols=lvl['cols'], rows=lvl['rows'], mean_length=m['mean_length'], max_length=m['_max_length'],
                         timer=lvl['timer_s'], bot_left=m['bot_time_left'], density=m['_density']),
                score=round(s, 3), attempt=a, notes=notes, rejected=reasons)
    return lvl, info


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--curve', default=os.path.join(HERE, 'work', 'curve.json'))
    ap.add_argument('--from', dest='a', type=int, default=62)
    ap.add_argument('--to', dest='b', type=int, default=150)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    curve = json.load(open(args.curve))
    out, infos = [], []
    for n in range(args.a, args.b + 1):
        lvl, info = generate(curve, n)
        out.append(lvl)
        infos.append(info)
        g, t = info['got'], info['target']
        print('L%-4d %-9s %-20s units %3d/%-3d rounds %2d/%-2d free %2d/%-2d %2dx%-2d t%d len %4.1f bot %3.0f %-8s a%s rej %d' % (
            n, t['tag'], '+'.join(info['kinds']) or '-', g['units'], t['units'], g['rounds'], t['rounds'], g['free'],
            t['free'], g['cols'], g['rows'], g['timer'], g['mean_length'], g['bot_left'],
            info['notes'].get('shape') or '', info['attempt'], len(info['rejected'])), flush=True)
    if args.out:
        ac.dump(dict(levels=out, infos=infos), args.out)


if __name__ == '__main__':
    main()
