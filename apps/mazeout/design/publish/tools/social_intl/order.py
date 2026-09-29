import os, sys
sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/Packages/PathCore/Tests/tools')
import soc_model as M; M.use('v552')
from socialsim import population as Pp, data as D
from datetime import datetime, timezone
T = int(datetime(2026, 9, 28, 18, tzinfo=timezone.utc).timestamp())
W = Pp.World(); W.extend_to(T + 40 * 86400)
for iso in ('HU', 'PE', 'NL', 'TR', 'FR', 'US'):
    orders = []
    for dd in (0, 1, 7, 30):
        t = T + dd * 86400
        top = W.top(t, 50, iso)
        orders.append([g for (_, g, c, j) in top])
    same = [orders[0] == o for o in orders[1:]]
    swaps = [sum(1 for a, b in zip(orders[0], o) if a != b) for o in orders[1:]]
    lv0 = [W.level(c, j, T) for (_, _, c, j) in W.top(T, 5, iso)]
    lv30 = [W.level(c, j, T + 30 * 86400) for (_, _, c, j) in W.top(T + 30 * 86400, 5, iso)]
    arch = sorted({Pp.ARCH[c.a]['key'] for (_, _, c, j) in W.top(T, 50, iso)})
    print(iso, 'top50 order identical after +1d/+7d/+30d:', same, 'positions changed:', swaps, '| top5 L now', lv0, '+30d', lv30, arch)
