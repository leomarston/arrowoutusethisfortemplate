#!/usr/bin/env python3
"""c2_reads.py [--jobs N] [--levels 32-61] — C2 evidence cache (SPEC-architecture §4.17 GoldenRoundsTests, HeadlessTests).

Reads every recorded level's START shot and every per-round shot the phone bot kept (research/bot/tmp/L0NN-<run>-rNN.png)
with the research's own board reader (research/bot/bot.py `read_board` + `apply_overrides`, imported READ-ONLY: nothing
is written under research/) and caches what each shot shows in Tests/Fixtures/c2_reads.json:

  {"levels": {"47": {"start": READ, "rounds": [{"file": "L047-024742-r06.png", "run": "024742", "round": 6, "read": READ}]}}}
  READ = {"ok": bool, "why": str, "fit": {...}, "shift": [c0, r0], "arrows": [{"cells", "dir"}], "blobs": [{"kind", "cells"}],
          "pipes": [{"cells", "ends": [{"cell", "out"}]}], "anomalies": [...]}

Cells are in the READ frame; `shift` maps them to the level's START json frame (bot.dump_level's origin formula:
start = read - shift). The golden-rounds and level-completion tools consume this cache, so numpy/scipy are needed only
here (run once; the fixture is the evidence).
"""
import json, os, re, sys, glob
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))          # apps/mazeout
RESEARCH = os.path.join(APP, 'research')
BOTDIR = os.path.join(RESEARCH, 'bot')
OUT = os.path.join(HERE, '..', 'Fixtures', 'c2_reads.json')
DIRNAME = {(0, -1): 'up', (0, 1): 'down', (-1, 0): 'left', (1, 0): 'right'}


def _bot():
    sys.path.insert(0, BOTDIR)
    import bot  # noqa: E402  (read-only use of the reader)
    return bot


def read_one(args):
    path, level = args
    bot = _bot()
    import numpy as np
    from PIL import Image
    start = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % level)))
    im = np.array(Image.open(path).convert('RGB')).astype(np.int16)
    ok, why, info = bot.guard(im)
    out = dict(ok=bool(ok), why=why)
    if not ok:
        return path, out
    try:
        b = bot.apply_overrides(im, bot.read_board(im), level)
    except Exception as e:  # a read during a transition: recorded as not ok
        out.update(ok=False, why='read failed: %s' % e)
        return path, out
    fit = b['fit']
    c0 = int(round((start['origin_pt'][0] * bot.SCALE - fit['x0']) / fit['pitch']))
    r0 = int(round((start['origin_pt'][1] * bot.SCALE - fit['y0']) / fit['pitch']))
    out['fit'] = {k: round(float(v), 3) for k, v in fit.items()}
    out['shift'] = [c0, r0]
    out['arrows'] = [dict(cells=[list(map(int, c)) for c in a['cells']], dir=a['dir']) for a in b['arrows']]
    out['blobs'] = [dict(kind=o['kind'], cells=[list(map(int, c)) for c in o['cells']]) for o in b['obstacles']]
    out['pipes'] = [dict(cells=sorted([list(map(int, c)) for c in p['cells']]),
                         ends=[dict(cell=[int(c[0]), int(c[1])], out=DIRNAME[tuple(d)]) for c, d in sorted(p['ends'].items())])
                    for p in b['pipes']]
    out['anomalies'] = [str(a) for a in b['anomalies']]
    return path, out


def main():
    jobs = 2
    if '--jobs' in sys.argv:
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1])
    lo, hi = 32, 61
    if '--levels' in sys.argv:
        lo, hi = map(int, sys.argv[sys.argv.index('--levels') + 1].split('-'))
    work = []
    meta = {}
    for L in range(lo, hi + 1):
        st = json.load(open(os.path.join(RESEARCH, 'levels', 'L%03d.json' % L)))
        shot = os.path.join(APP, st['shot'])
        work.append((shot, L))
        meta[shot] = (L, 'start', None, None)
        for f in sorted(glob.glob(os.path.join(BOTDIR, 'tmp', 'L%03d-*r[0-9][0-9].png' % L))):
            m = re.search(r'L\d{3}-(?:(\d{6})-)?r(\d{2})\.png$', f)
            if not m:
                continue
            work.append((f, L))
            meta[f] = (L, 'round', m.group(1) or '', int(m.group(2)))
    res = {}
    if os.path.exists(OUT):
        res = json.load(open(OUT)).get('levels', {})
    done = set()
    for L, d in res.items():
        if d.get('start'):
            done.add(d['start'].get('_file'))
        for r in d.get('rounds', []):
            done.add(r['file'])
    todo = [w for w in work if os.path.basename(w[0]) not in done]
    print('reads: %d total, %d cached, %d to do' % (len(work), len(work) - len(todo), len(todo)), flush=True)
    n = 0
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for path, read in ex.map(read_one, todo, chunksize=2):
            L, what, run, rnd = meta[path]
            d = res.setdefault(str(L), {'start': None, 'rounds': []})
            if what == 'start':
                read['_file'] = os.path.basename(path)
                d['start'] = read
            else:
                d['rounds'].append(dict(file=os.path.basename(path), run=run, round=rnd, read=read))
            n += 1
            if n % 20 == 0:
                print('  %d/%d' % (n, len(todo)), flush=True)
                json.dump({'levels': res}, open(OUT, 'w'), separators=(',', ':'), sort_keys=True)
    for d in res.values():
        d['rounds'].sort(key=lambda r: (r['run'], r['round']))
    json.dump({'schema': 1, 'tool': 'Tests/tools/c2_reads.py', 'reader': 'research/bot/bot.py read_board + apply_overrides',
               'levels': res}, open(OUT, 'w'), separators=(',', ':'), sort_keys=True)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
