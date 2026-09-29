#!/usr/bin/env python3
"""replay_bundle.py — the video REPLAY CHECK on the bundled levels (CONTENT, L1 acceptance: "every video level … its vextract
replay has 0 inconsistent taps").

For every bundled level with source "video" (L1-L31, the substitutes L35/L45/L51/L52 and the spares L62-L64), the BUNDLE's
arrows, tapes, boxes (counters), pipes (mouths, counters) and elevators (platforms, layer 2) are written back into the
research geometry of that video board (fit_px, stroke, elevator times: research/levels[/video]/…json), and
research/video-tools/vextract.py's `replay` plays the owner's video against it: every tap the video shows must be an EXIT of
an arrow our model says is FREE (or a bump of a BLOCKED one), every arrow that vanishes without a detected tap must be free,
boxes / pipes must break exactly when our counters say, nothing may be left at the end. L11-L20 are replayed against BOTH
videos (V1 and V2 play the same boards). vextract is imported read-only; its frame cache is redirected to build/l1/ (research/
is read-only for build agents).

  python3 tools/levels/replay_bundle.py [--levels 1,2,35] [--out build/l1/replay]     (~10-20 min for all 48 replays)

Since the level re-order + provenance strip (PUBLISH item 12): which video board a bundled level is comes from its
design/levels.json record (design/tools/level_order.py; the bundle's gameplay must equal it), never from the level it ships at.
`--levels` and the output names use the shipped level number.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(APP, 'research', 'video-tools'))
import vextract  # noqa: E402
sys.path.insert(0, os.path.join(APP, 'design', 'tools'))
import level_order as LO  # noqa: E402  (board identity after the re-order)

LEVELS = os.path.join(APP, 'App', 'Resources', 'Levels')
RESEARCH = os.path.join(APP, 'research', 'levels')


def plays(b):
    """[(video, video level number, research geometry file)] for a bundled video level (provenance restored)."""
    if LO.is_substitute(b):                   # a V2 board in a phone slot (ORCH 19 substitutes, ORCH 26 spares)
        v, n = LO.video_board(b)
        return [(v, n, os.path.join(RESEARCH, 'video', '%s-L%03d.json' % (v, n)))]
    level = b['_rslot']                       # L1-L31: the video's own level number
    if level <= 10:
        return [('V1', level, os.path.join(RESEARCH, 'L%03d.json' % level))]
    if level <= 20:
        return [('V1', level, os.path.join(RESEARCH, 'video', 'V1-L%03d.json' % level)),
                ('V2', level, os.path.join(RESEARCH, 'L%03d.json' % level))]
    return [('V2', level, os.path.join(RESEARCH, 'L%03d.json' % level))]


def bbox_px(base, cells, pad=0.5):
    fp = base['fit_px']
    p = fp['pitch']
    xs = [fp['x0'] + (c[0] + fp['c0']) * p for c in cells]
    ys = [fp['y0'] + (c[1] + fp['r0']) * p for c in cells]
    return [int(min(xs) - pad * p), int(min(ys) - pad * p), int(max(xs) + pad * p), int(max(ys) + pad * p)]


def to_research(b, base):
    """the bundle level's content in the research (video) schema, on the research file's geometry"""
    js = json.loads(json.dumps(base))
    elevs = [o for o in b['obstacles'] if o['kind'] == 'elevator']
    eidx = {o['id']: k for k, o in enumerate(elevs)}
    arrows = []
    for a in b['arrows']:
        rec = dict(id=a['id'], cells=a['cells'], dir=a['dir'])
        if a.get('layer', 1) != 1:
            rec['layer'] = a['layer']
            rec['under_elevator'] = eidx[a['hidden_by']]
        arrows.append(rec)
    keep = [o for o in base['obstacles'] if o['kind'] not in ('tape_pink', 'box', 'curtain', 'pipe', 'elevator')]
    obst = list(keep)
    taped = []
    for o in b['obstacles']:
        if o['kind'] == 'tape':
            obst.append(dict(kind='tape_pink', cells=o['cells'], bbox_px=bbox_px(base, o['cells'])))
            taped += o['arrows']
        elif o['kind'] in ('box', 'curtain'):
            obst.append(dict(kind='box', cells=o['cells'], counter=o['counter'], bbox_px=bbox_px(base, o['cells'])))
    pipes = [dict(cells=o['cells'], ends=o['ends'], counter=o.get('counter')) for o in b['obstacles'] if o['kind'] == 'pipe']
    base_el = base.get('elevators') or []
    elevators = []
    for o in elevs:
        match = [e for e in base_el if {tuple(c) for c in e['cells']} == {tuple(c) for c in o['cells']}]
        if len(match) != 1:
            raise SystemExit('L%d: elevator %s has no unique research counterpart' % (b['level'], o['id']))
        e = dict(match[0])
        e.update(cells=o['cells'], arrow_ids=o.get('arrows', []), hidden_arrow_ids=o.get('reveals', []))
        elevators.append(e)
    js.update(arrows=arrows, obstacles=obst, pipes=pipes, elevators=elevators, taped_arrow_ids=sorted(taped),
              blocker_cells=[c for o in b['obstacles'] if o['kind'] in ('box', 'curtain') for c in o['cells']],
              _content='App/Resources/Levels/level_%04d.json (the bundle), on the geometry of %s' % (
                  b['level'], os.path.relpath(base.get('_path', ''), APP)))
    return js


def main(argv):
    out = argv[argv.index('--out') + 1] if '--out' in argv else os.path.join(APP, 'build', 'l1', 'replay')
    only = None
    if '--levels' in argv:
        only = {int(x) for x in argv[argv.index('--levels') + 1].split(',')}
    os.makedirs(out, exist_ok=True)
    vextract.WORK = os.path.join(APP, 'build', 'l1', 'vreplay-work')      # frame cache out of research/
    rows = []
    for name in sorted(os.listdir(LEVELS)):
        if not name.startswith('level_'):
            continue
        b = LO.with_provenance(json.load(open(os.path.join(LEVELS, name))))
        if b['source'] != 'video' or (only and b['level'] not in only):
            continue
        for V, n, geo in plays(b):
            base = json.load(open(geo))
            base['_path'] = geo
            js = to_research(b, base)
            jp = os.path.join(out, 'L%03d-%s-L%03d-bundle.json' % (b['level'], V, n))
            json.dump(js, open(jp, 'w'), indent=1)
            rp = os.path.join(out, 'L%03d-%s-L%03d-replay.json' % (b['level'], V, n))
            t0 = time.time()
            r = vextract.replay(V, n, js_path=jp, report=rp)
            st = r['stats']
            row = dict(level=b['level'], video=V, video_level=n, taps=st['taps'], mapped=st['mapped'],
                       consistent=st['consistent'], inconsistent=st['inconsistent'], left_at_end=len(st['left_at_end']),
                       counter_mismatch=st.get('counter_mismatch', 0), unexplained_stays=st['unexplained_stays'],
                       miss=st['miss'], late=st['late'], seconds=round(time.time() - t0, 1))
            rows.append(row)
            print('L%03d %s-L%03d taps %3d consistent %3d INCONSISTENT %d left %d counter_mismatch %d stays %d (%.0f s)' % (
                b['level'], V, n, row['taps'], row['consistent'], row['inconsistent'], row['left_at_end'],
                row['counter_mismatch'], row['unexplained_stays'], row['seconds']), flush=True)
    bad = [r for r in rows if r['inconsistent'] or r['left_at_end'] or r['counter_mismatch']]
    summ = dict(replays=len(rows), levels=len({r['level'] for r in rows}), inconsistent=sum(r['inconsistent'] for r in rows),
                left_at_end=sum(r['left_at_end'] for r in rows), counter_mismatch=sum(r['counter_mismatch'] for r in rows),
                failing=bad, table=rows)
    json.dump(summ, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
    print('replay_bundle: %d replays over %d bundled video levels: %d inconsistent event(s), %d arrow(s) left, %d counter '
          'mismatch(es)' % (len(rows), summ['levels'], summ['inconsistent'], summ['left_at_end'], summ['counter_mismatch']))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
