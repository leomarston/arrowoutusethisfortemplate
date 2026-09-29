import sys, collections
sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/Packages/PathCore/Tests/tools')
import soc_model as M; M.use('v552')
from socialsim import population as Pp, data as D, names as Nm, core as K
from datetime import datetime, timezone
T = int(datetime(2026, 9, 28, 18, tzinfo=timezone.utc).timestamp())
W = Pp.World(); W.extend_to(T + 86400)
d = Nm.data()
def base_token(c, j):
    st, _ = W.style_of(c, j)
    if st not in Nm.POPULAR_STYLES: return None
    key = K.h64(W.seed, 'nick', W.gid(c, j)); Dw = Nm.DRAW
    if st == 'given': ntok, nsuf = len(d['cultures'][c.culture]), 1
    elif st == 'mixed': ntok, nsuf = len(d['mixedTokens'][c.culture]), len(d['mixedSuffixes'])
    else: ntok, nsuf = len(d['cultures'][c.culture]), len(d['underscoreSuffixes'])
    if K.below(key, 'head?', 100) < Dw['headP']: t = K.below(key, 'head', min(Dw['headN'], ntok))
    else:
        u = K.u01(key, 'pop'); t = int(K.fl(ntok * u * u))
    toks = d['cultures'][c.culture] if st != 'mixed' else d['mixedTokens'][c.culture]
    tk = toks[t]
    return tk[1] if isinstance(tk, list) else tk
print('%-4s %6s %8s %s' % ('iso', 'rows', 'firstnm', 'most repeated first names in Country top 200 (count)'))
for iso in ('US', 'GB', 'DE', 'FR', 'ES', 'IT', 'BR', 'TR', 'JP', 'KR', 'PL', 'IN', 'SA', 'NL', 'SE'):
    rows = [(c, j) for (_, _, c, j) in W.top(T, 200, iso)]
    toks = [b for b in (base_token(c, j) for (c, j) in rows) if b]
    cnt = collections.Counter(toks)
    print('%-4s %6d %8d %s' % (iso, len(rows), len(toks), ', '.join('%s %d' % kv for kv in cnt.most_common(5))))
print({k: len(v) for k, v in d['cultures'].items()})
