#!/usr/bin/env python3
"""pin_fixtures.py — pins the content the PathCore content tests read into Packages/PathCore/Tests/Fixtures/content/
(hermetic, like C1's Fixtures/research): the tests never read design/ or the gitignored design/tools/work/ again.

  python3 design/tools/pin_fixtures.py           # copy + write MANIFEST.txt (sha256 of each pinned file and of its source)
  python3 design/tools/pin_fixtures.py --check   # exit 1 when a pin differs from its source (content changed, not re-pinned)

Pinned:  levels.json   = design/levels.json                 (C4Fixtures.doc: GeneratorTests, ValidatorTests, SolverTests,
                                                             LevelLibraryTests; c4_reference.py negatives/runtime read it)
         designed.json = design/tools/work/designed.json    (the reference generator's L106-L150 levels + infos; GeneratorTests)
Re-pin after every content change (build_levels.py assemble), then regenerate the derived C4 fixtures:
  python3 Packages/PathCore/Tests/tools/c4_reference.py negatives
  python3 Packages/PathCore/Tests/tools/c4_reference.py runtime --from 151 --to 650 [--jsonl ...]
  python3 Packages/PathCore/Tests/tools/c4b_bot_replay.py      (BotReplayTests: pins the content's sha256)
"""
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
DST = os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'Fixtures', 'content')
PINS = [('levels.json', os.path.join(APP, 'design', 'levels.json')),
        ('designed.json', os.path.join(HERE, 'work', 'designed.json'))]


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    check = '--check' in sys.argv[1:]
    bad = []
    if not check:
        os.makedirs(DST, exist_ok=True)
    lines = ['# Tests/Fixtures/content — the content the PathCore content tests read (hermetic; design/tools/pin_fixtures.py).',
             '# Verify: cd Packages/PathCore/Tests/Fixtures/content && shasum -a 256 -c MANIFEST.txt',
             '# Sources: levels.json = design/levels.json; designed.json = design/tools/work/designed.json (gitignored there).',
             '# Pinned by content recast 2 (phone sessions 1-3: v552 L32-L105 recorded, repeats -> V2 boards / stand-ins;'
             ' designed L106-L150; 2026-09-25).',
             '# Re-ordered by PUBLISH B0 (2026-09-28): L34-L105 permuted per design/level-order.json (reorder_levels.py;'
             ' L1-L33 + L70 frozen); the curve "_about" text neutralised (numbers unchanged).', '#']
    for name, src in PINS:
        dst = os.path.join(DST, name)
        if check:
            if not os.path.exists(dst) or sha(dst) != sha(src):
                bad.append(name)
            continue
        shutil.copyfile(src, dst)
        lines.append('%s  %s' % (sha(dst), name))
    if check:
        print('pins: %s' % ('current' if not bad else 'STALE ' + ', '.join(bad)))
        return 1 if bad else 0
    open(os.path.join(DST, 'MANIFEST.txt'), 'w').write('\n'.join(lines) + '\n')
    print('pinned %s -> %s' % (', '.join(n for n, _ in PINS), os.path.relpath(DST, APP)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
