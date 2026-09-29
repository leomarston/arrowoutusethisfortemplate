#!/usr/bin/env python3
"""c4b_corner_layouts.py — reference outputs of gen_levels.corner_layout for GeneratorTests (the corner port, unit level).

Each case: a PathRandom seed, a board W x H and a set of used cells (empty; a full band on one side; a door-like block
touching a margin; scattered cells; tiny boards whose lines are too short) -> the reference's (sides, margin, corners) and
the NEXT value the stream gives afterwards (so the number of draws is pinned too).

  python3 Packages/PathCore/Tests/tools/c4b_corner_layouts.py          # writes Tests/Fixtures/c4b_corner_layouts.json
  python3 Packages/PathCore/Tests/tools/c4b_corner_layouts.py --check
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
APP = os.path.dirname(os.path.dirname(PKG))
sys.path.insert(0, os.path.join(APP, 'design', 'tools'))
import gen_levels as gl  # noqa: E402
from pathrandom import PathRandom  # noqa: E402

OUT = os.path.join(PKG, 'Tests', 'Fixtures', 'c4b_corner_layouts.json')


def used_sets(W, H, k):
    """A few deterministic used-cell sets for a W x H board."""
    yield 'empty', set()
    yield 'topBand', {(c, r) for r in range(max(1, H // 3)) for c in range(W)}
    yield 'rightBlock', {(c, r) for r in range(H // 4, H // 2 + 1) for c in range(W - 3, W)}
    yield 'bottomRow', {(c, H - 1) for c in range(W)}
    yield 'scatter', {((7 * i + k) % W, (5 * i + 3 * k) % H) for i in range(max(1, (W * H) // 9))}
    yield 'leftAndTop', {(0, r) for r in range(H)} | {(c, 0) for c in range(W)}


def build():
    cases = []
    sizes = [(3, 3), (4, 3), (3, 5), (5, 5), (10, 12), (16, 16), (17, 18), (20, 26), (24, 30), (26, 36), (13, 16), (22, 28)]
    k = 0
    for W, H in sizes:
        for name, used in used_sets(W, H, k):
            for s in range(4):
                seed = 1000003 * k + 7919 * s + W * 131 + H
                rng = PathRandom(seed)
                sides, margin, corners = gl.corner_layout(rng, W, H, set(used))
                cases.append(dict(seed=seed, cols=W, rows=H, used_name=name, used=sorted([list(c) for c in used]),
                                  sides=sides, margin=sorted([list(c) for c in margin]),
                                  corners=[dict(cell=list(c), turn=t) for c, t in corners],
                                  next=rng.below(1 << 30)))
            k += 1
    return dict(_about='gen_levels.corner_layout reference outputs (Tests/tools/c4b_corner_layouts.py): seed, board, used '
                       'cells -> sides, margin cells, corners (placement order) and the next stream value.',
                cases=cases)


def main():
    text = json.dumps(build(), sort_keys=True, separators=(',', ':')) + '\n'
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT).read() == text
        print('c4b_corner_layouts.json is %s' % ('current' if same else 'STALE'))
        return 0 if same else 1
    open(OUT, 'w').write(text)
    d = json.loads(text)
    n = len(d['cases'])
    none = sum(1 for c in d['cases'] if not c['corners'])
    two = sum(1 for c in d['cases'] if len(c['sides']) == 2)
    print('%d cases: %d without a corner (corner layout fails), %d with two sides, %d corners in all' % (
        n, none, two, sum(len(c['corners']) for c in d['cases'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
