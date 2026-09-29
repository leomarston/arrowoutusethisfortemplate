#!/usr/bin/env python3
"""repeats.py — the repeat detector (SPEC.md §5 items 19, 26, 28: no board may appear twice in L1-L150; the FIRST occurrence in
our order wins, every later duplicate slot gets a generated stand-in).

A board's identity is taken offset-free AND under the 8 symmetries of the square (4 rotations x mirror): every cell and every
head direction is mapped by the symmetry, then the board is shifted to its top-left cell, and the smallest of the 8 images is
the canonical key. Three keys per level:
  visible   the arrows visible at the start (no door/elevator hides them): what the player sees        -> a REPEAT
  full      every arrow of every layer (hidden ones included)                                         -> a REPEAT
  cells     the visible arrows' cells without their heads (the same drawing with other heads)          -> reported (near)
Two levels repeat when their visible keys or their full keys are equal. Obstacles are not in the key (a board with the same
arrows and another obstacle skin is still the same maze to the player).

  python3 design/tools/repeats.py                      # design/levels.json (L1-L150) -> build/recast2/repeats.txt
  python3 design/tools/repeats.py --order              # the research corpus in OUR order, before any stand-in
                                                       # (build_levels.research_order): what the dedup rule acts on
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

VEC = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
DIR_OF = {v: k for k, v in VEC.items()}
# the dihedral group D4 acting on (x, y): (a, b, c, d) -> (a*x + b*y, c*x + d*y)
SYMS = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0),       # rotations 0, 90, 180, 270
        (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0)]       # mirrors: x, y, main and anti diagonal
SYM_NAMES = ['identical', 'rotated 90', 'rotated 180', 'rotated 270', 'mirrored left-right', 'mirrored top-bottom',
             'mirrored on the diagonal', 'mirrored on the anti-diagonal']


def _img(arrows, s, heads=True):
    a, b, c, d = s
    pts = []
    for cells, dr in arrows:
        cs = [(a * x + b * y, c * x + d * y) for x, y in cells]
        v = VEC[dr]
        pts.append((cs, DIR_OF[(a * v[0] + b * v[1], c * v[0] + d * v[1])] if heads else None))
    if not pts:
        return ()
    x0 = min(x for cs, _ in pts for x, _ in cs)
    y0 = min(y for cs, _ in pts for _, y in cs)
    return tuple(sorted((tuple(sorted((x - x0, y - y0) for x, y in cs)), dr or '') for cs, dr in pts))


def canonical(arrows, heads=True):
    """(key, index of the symmetry that gives it) — key = the smallest of the 8 images."""
    imgs = [(_img(arrows, s, heads), i) for i, s in enumerate(SYMS)]
    return min(imgs)


def arrows_of(l, visible_only):
    out = []
    for a in l['arrows']:
        if visible_only and (a.get('hidden_by') or (a.get('layer') or 1) > 1):
            continue
        out.append(([tuple(c) for c in a['cells']], a['dir']))
    return out


def keys(l):
    return dict(visible=canonical(arrows_of(l, True)), full=canonical(arrows_of(l, False)),
                cells=canonical(arrows_of(l, True), heads=False))


def relation(ka, kb):
    """How board b repeats board a ('' = not at all)."""
    for k in ('visible', 'full'):
        if ka[k][0] == kb[k][0]:
            return 'repeat', k
    if ka['cells'][0] == kb['cells'][0]:
        return 'near', 'cells'
    return '', ''


def sym_between(la, lb, which='visible'):
    """The symmetry that maps board a onto board b (name), from their canonical images."""
    A = arrows_of(la, which == 'visible')
    B = arrows_of(lb, which == 'visible')
    for i, s in enumerate(SYMS):
        if _img(A, s) == _img(B, SYMS[0]):
            return SYM_NAMES[i]
    return '?'


def scan(levels, label=lambda l: 'L%d' % l['level']):
    """levels in OUR order -> (repeats, nears): repeats = [(later, first, key, symmetry)], the first occurrence wins."""
    ks = [(l, keys(l)) for l in levels]
    reps, nears = [], []
    first_of = {}
    for i, (l, k) in enumerate(ks):
        hit = None
        for j in range(i):
            lj, kj = ks[j]
            rel, which = relation(kj, k)
            if rel == 'repeat' and j not in first_of:
                hit = (j, which)
                break
            if rel == 'near':
                nears.append((label(l), label(lj)))
        if hit:
            j, which = hit
            first_of[i] = j
            reps.append((label(l), label(ks[j][0]), which, sym_between(ks[j][0], l, which)))
    return reps, nears


def main():
    out = []
    if '--order' in sys.argv[1:]:
        import build_levels
        levels = build_levels.research_order()
        reps, nears = scan(levels, label=lambda l: 'L%d (%s)' % (l['level'], l.get('_board', l['source'])))
        out.append('research corpus in our order (before stand-ins): %d boards' % len(levels))
    else:
        path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(APP, 'design', 'levels.json')
        levels = json.load(open(path))['levels']
        reps, nears = scan(levels)
        out.append('%s: %d levels' % (os.path.relpath(path, APP), len(levels)))
    for later, first, which, sym in reps:
        out.append('REPEAT %s = %s (%s key, %s)' % (later, first, which, sym))
    for a, b in nears:
        out.append('near %s: the same arrow cells as %s with other heads' % (a, b))
    out.append('%d repeat(s), %d near repeat(s) (rotations and mirrors included)' % (len(reps), len(nears)))
    print('\n'.join(out))
    return 1 if reps and '--order' not in sys.argv[1:] else 0


if __name__ == '__main__':
    sys.exit(main())
