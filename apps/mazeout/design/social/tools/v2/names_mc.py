#!/usr/bin/env python3
"""names_mc.py — how often does a board of REAL people pass the "top first name <= 4 %" guard? (evidence for T6)

For every culture with Wikidata counts, the real first-name frequencies (adults born 1950-2008, men and women weighted
equally, tools/v2/build_name_data_v2.py) are sampled: ROWS first-name rows (a Country top 200 carries 60-90 of them),
TRIALS times. Reported: the empirical share of the most common name / top 10 / top 50, the share of samples whose most
repeated name exceeds 4 % of the rows, and the 99th percentile of that repeat count. The same for the v2 draw (M7) over
the culture's shipped list. Deterministic (seeded).
    python3 design/social/tools/v2/names_mc.py [OUT.json] [--rows 70] [--trials 4000]
"""
import os, sys, json, math, random, bisect, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..')))
import build_name_data_v2 as B                                                  # noqa: E402
from socialsim import v2 as V2                                                  # noqa: E402

ROWS = int(sys.argv[sys.argv.index('--rows') + 1]) if '--rows' in sys.argv else 70
TRIALS = int(sys.argv[sys.argv.index('--trials') + 1]) if '--trials' in sys.argv else 4000
OUT = next((a for a in sys.argv[1:] if a.endswith('.json')), None)


def model_probs(n, Dw):
    H = max(1, min(Dw['headN'], n // 6))
    hp = Dw['headP'] * min(n, 300) // 300 / 100.0
    tu = Dw['tailUniformP'] / 100.0
    p = [0.0] * n
    for i in range(H):
        p[i] += hp / H
    for i in range(n):
        p[i] += (1 - hp) * (tu / n + (1 - tu) * (math.sqrt((i + 1) / n) - math.sqrt(i / n)))
    return p


def mc(p, rng):
    cum = []
    a = 0.0
    for x in p:
        a += x
        cum.append(a)
    over = 0
    maxes = []
    for _ in range(TRIALS):
        c = collections.Counter(bisect.bisect_left(cum, rng.random() * a) for _ in range(ROWS))
        m = max(c.values())
        maxes.append(m)
        over += m / ROWS > 0.04
    maxes.sort()
    return dict(fail4pct=round(over / TRIALS, 3), maxCountP50=maxes[TRIALS // 2], maxCountP99=maxes[int(TRIALS * 0.99)],
                maxCountMax=maxes[-1])


def main():
    rng = random.Random(20260928)
    d = json.load(open(B.OUT, encoding='utf-8'))
    res = dict(rows=ROWS, trials=TRIALS, draw=V2.DRAW, cultures={})
    for cu in B.ORDER:
        if cu in ('en', 'easteu', 'sea', 'th') or not d['cultures'].get(cu):
            continue
        score, raw, persons, nd = B.load_counts(cu)
        top = sorted(score.values(), reverse=True)[:len(d['cultures'][cu])]
        if not top:
            continue
        tot = sum(top)
        emp = [x / tot for x in top]
        mp = model_probs(len(d['cultures'][cu]), V2.DRAW)
        res['cultures'][cu] = dict(listSize=len(d['cultures'][cu]),
                                   real=dict(top1=round(emp[0], 4), top10=round(sum(emp[:10]), 3), top50=round(sum(emp[:50]), 3), **mc(emp, rng)),
                                   model=dict(top1=round(mp[0], 4), top10=round(sum(mp[:10]), 3), top50=round(sum(mp[:50]), 3), **mc(mp, rng)))
        print(cu, res['cultures'][cu], flush=True)
    if OUT:
        with open(OUT, 'w') as f:
            json.dump(res, f, indent=1)


if __name__ == '__main__':
    main()
