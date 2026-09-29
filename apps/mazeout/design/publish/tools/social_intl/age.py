import sys
sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/Packages/PathCore/Tests/tools')
import soc_model as M; M.use('v552')
from socialsim import population as Pp, core as K
W = Pp.World()
for days in (1, 7, 28, 56, 90, 154, 365):
    t = K.EPOCH + days * 86400
    W.extend_to(t)
    top = W.top(t, 100)
    print('world age %3d d: players %7d  #1 L%-6d #10 L%-6d #100 L%-6d  rank of a L60 player %d' % (
        days, W.joined(t), W.level(*top[0][2:], t), W.level(*top[9][2:], t), W.level(*top[99][2:], t), W.rank_of_level(60, t)))
