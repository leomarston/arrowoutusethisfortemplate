#!/usr/bin/env python3
"""model vs video obstacle timeline: removal events from the replay report, pipe passes / box counters by the Model, video readings
from the obst timeline.   corr.py N [--replay R] [--json J]"""
import json, os, sys
MZ = '/Users/yago/Downloads/app-factory/apps/mazeout'
sys.path.insert(0, MZ + '/research/video-tools')
import vextract as vx
WORK = MZ + '/research/video-frames/work'
a = sys.argv[1:]
n = int(a[0])
def opt(k, d=None):
    return a[a.index(k) + 1] if k in a else d
jp = opt('--json', WORK + '/levelsC/V2-L%03d.json' % n)
rp = opt('--replay', WORK + '/levelsC/V2-L%03d-replay.json' % n)
if not os.path.exists(rp):
    rp = WORK + '/extract/V2-L%03d-replay.json' % n
js = json.load(open(jp)); rep = json.load(open(rp))
ob = json.load(open(WORK + '/levelsC/V2-L%03d-obst.json' % n)) if os.path.exists(WORK + '/levelsC/V2-L%03d-obst.json' % n) else None
m = vx.Model(js)
pipe_k_of_obst = {}
pk = 0
for k, o in enumerate(js['obstacles']):
    if o['kind'] == 'pipe':
        pipe_k_of_obst[pk] = k; pk += 1
box_k_of_obst = {}
bk = 0
for k, o in enumerate(js['obstacles']):
    if o['kind'] in ('box', 'curtain'):
        box_k_of_obst[bk] = k; bk += 1
events = []
removed = 0
for e in rep['log']:
    ids = None
    if e.get('event') == 'tap' and e.get('video') == 'exit':
        ids = e['group']
    elif e.get('event') == 'gone_without_tap':
        ids = [e['arrow']]
    if not ids:
        continue
    ids = [i for i in ids if i in m.alive]
    if not ids:
        continue
    passes = []
    for i in ids:
        info = {}
        m.ray(i, info)
        passes += [m.pipes[kk]['k'] for kk in info.get('pipes', [])]
    before = [(pp['k'], pp['counter']) for pp in m.pipes]
    m.remove(ids)
    removed += len(ids)
    after_p = {pp['k']: pp['counter'] for pp in m.pipes}
    boxes = [(bi, b['counter'], b['broken']) for bi, b in enumerate(m.blockers)]
    events.append(dict(t=e['t'], ids=ids, tapped=e.get('event') == 'tap', removed=removed, pipe_passes=passes,
                       pipes_after={k: after_p.get(k, 0) for k, _ in before}, boxes_after=boxes))
print('removal events:', len(events), 'arrows removed', removed, 'of', len([x for x in js['arrows'] if x.get('layer', 1) == 1]))
for ev in events:
    if ev['pipe_passes']:
        print('  PIPE PASS t=%.3f arrows %s passes pipe %s -> counters %s' % (ev['t'], ev['ids'], ev['pipe_passes'], ev['pipes_after']))
    for bi, c, br in ev['boxes_after']:
        if c == 0 and not any(x for x in events[:-1] if False):
            pass
# box: time model counter hits 0
for bi, b in enumerate(m.blockers):
    t_zero = next((ev['t'] for ev in events if ev['boxes_after'][bi][1] <= 0), None)
    print('  BOX %d (obstacle %d) counter %s: model zero at t=%s (removal #%s)' % (bi, box_k_of_obst[bi], b['counter0'], t_zero,
          next((ev['removed'] for ev in events if ev['boxes_after'][bi][1] <= 0), None)))
if ob:
    for o in ob['obstacles']:
        print('  VIDEO obstacle %d %s counter0 %s break %s readings %s' % (o['k'], o['kind'], o['counter0'], o['t_break'], o['readings_collapsed']))
# box counters: model counter after each removal vs video reading at that time
if ob:
    for o in ob['obstacles']:
        if o['kind'] not in ('box', 'curtain'):
            continue
        bi = [b for b, k in box_k_of_obst.items() if k == o['k']][0]
        mism = []
        for t, v in o['readings_collapsed']:
            if v is None:
                continue
            # model counter at video time t (removals up to t - 0.05)
            prior = [ev for ev in events if ev['t'] <= t]
            mc = prior[-1]['boxes_after'][bi][1] if prior else m.blockers[bi]['counter0']
            if mc != v:
                mism.append((t, v, mc))
        print('  box obstacle %d: %d readings, %d differ from the model counter at that time (video, model): %s' % (
            o['k'], len(o['readings_collapsed']), len(mism), mism[:12]))
json.dump(events, open(WORK + '/levelsC/V2-L%03d-events.json' % n, 'w'), indent=0, default=str)
