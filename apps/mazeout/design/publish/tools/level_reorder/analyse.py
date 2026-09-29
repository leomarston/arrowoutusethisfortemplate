"""level_reorder/analyse.py — the numbers of design/publish/level-reorder.md: a candidate order vs today's order.
  python3 design/publish/tools/level_reorder/analyse.py [level_order_candidate.json]"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from feat import load  # noqa: E402
import reorder_ref as R2  # noqa: E402
from reorder_ref import rolling, FREEZE_TO  # noqa: E402

doc, F = load()
by = {f['n']: f for f in F}
O = json.load(open(os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else 'level_order_candidate.json')))
order = {int(s): o for s, o in O['order'].items()}
N = len(F)
moved = [s for s in order if order[s] != s]
disp = [abs(s - order[s]) for s in moved]
print('moved %d boards; |move| mean %.1f median %s max %d; by tag: %s' % (
    len(moved), statistics.mean(disp), statistics.median(disp), max(disp),
    {t: len([s for s in moved if by[order[s]]['tag'] == t]) for t in ('normal', 'hard', 'superHard')}))
# copy metrics
def at_own_number(order):
    out = []
    for s, o in order.items():
        f = by[o]
        if f['origin'] and f['origin'][0] == 'v552' and f['origin'][1] == s:
            out.append(s)
    return out
ident = {s: s for s in range(1, N + 1)}
print('v552 boards at their v552 number: before %d, after %d %s' % (len(at_own_number(ident)), len(at_own_number(order)),
                                                                  at_own_number(order)))
def v552_adj(order):
    n = 0
    lst = []
    for s in range(1, N):
        a, b = by[order[s]], by[order[s + 1]]
        if a['origin'] and b['origin'] and a['origin'][0] == b['origin'][0] == 'v552' and b['origin'][1] == a['origin'][1] + 1:
            n += 1
            lst.append(s)
    return n, lst
print('consecutive v552 pairs kept consecutive: before %d, after %s' % (v552_adj(ident)[0], v552_adj(order)))
P = R2.Problem(F)
print('pairwise violations:', P.pair_violations(order), 'forbidden cells used:', [s for s in order if order[s] != s and P.forbidden(order[s], s)])
J, out = P.devs(order)
print('deviations:', {k: round(v, 3) for k, v in out.items()}, 'within TOL:', P.within(out))
# decade table
def dec_rows(order, lo, hi):
    fs = [by[order[s]] for s in range(lo, hi + 1)]
    kinds = {}
    for f in fs:
        for k in f['kinds']:
            kinds[k] = kinds.get(k, 0) + 1
    return dict(units=statistics.mean(f['units'] for f in fs), waves=statistics.mean(f['waves'] for f in fs),
                pressure=statistics.mean(f['pressure'] for f in fs), timer=statistics.mean(f['timer'] for f in fs),
                free=statistics.mean(f['free'] for f in fs),
                maxu=max(f['units'] for f in fs), kinds=kinds,
                tags=''.join({'normal': '.', 'hard': 'H', 'superHard': 'S'}[f['tag']] for f in fs))
print()
print('| slots | units old → new | waves old → new | pressure old → new | timer s old → new | obstacle levels old → new (door/pipe/box/tape/elev/corner) |')
for lo in list(range(30, 110, 10)) + [110]:
    hi = min(lo + 9, 150) if lo < 110 else 150
    a, b = dec_rows(ident, lo, hi), dec_rows(order, lo, hi)
    ks = ['door', 'pipe', 'box', 'tape', 'elevator', 'corner']
    print('| L%d-L%d | %.1f → %.1f | %.1f → %.1f | %.3f → %.3f | %.0f → %.0f | %s → %s |' % (
        lo, hi, a['units'], b['units'], a['waves'], b['waves'], a['pressure'], b['pressure'], a['timer'], b['timer'],
        '/'.join(str(a['kinds'].get(k, 0)) for k in ks), '/'.join(str(b['kinds'].get(k, 0)) for k in ks)))
# rolling curve sample
old = [by[n] for n in range(1, N + 1)]
new = [by[order[n]] for n in range(1, N + 1)]
ru_o, ru_n = rolling([f['units'] for f in old]), rolling([f['units'] for f in new])
rw_o, rw_n = rolling([f['waves'] for f in old]), rolling([f['waves'] for f in new])
rp_o, rp_n = rolling([f['pressure'] for f in old]), rolling([f['pressure'] for f in new])
print()
print('rolling-9 at every 5th slot (units / waves / pressure; old → new):')
for s in range(35, 106, 5):
    i = s - 1
    print('  L%d  %.1f → %.1f   %.1f → %.1f   %.3f → %.3f' % (s, ru_o[i], ru_n[i], rw_o[i], rw_n[i], rp_o[i], rp_n[i]))
# worst spots
worst = sorted(range(29, 105), key=lambda i: -abs(ru_n[i] - ru_o[i]) / ru_o[i])[:3]
print('worst units spots:', [(i + 1, round(ru_o[i], 1), round(ru_n[i], 1)) for i in worst])
# the permutation table
print()
print('slot <- board (origin, tag, timer, kinds, units/waves)')
for s in range(FREEZE_TO + 1, O['zone_end'] + 1):
    f = by[order[s]]
    print('  L%d <- L%d %s %s %d %s %d/%d%s' % (s, order[s], f['origin'], f['tag'], f['timer'], '+'.join(sorted(f['kinds'])) or '-',
                                           f['units'], f['waves'], '' if order[s] != s else '   (anchor/fixed)'))
