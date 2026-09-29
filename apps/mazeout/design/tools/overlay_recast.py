#!/usr/bin/env python3
"""overlay_recast.py — the L1 overlay proof (tools/levels/render.py, read-only) for the recast bundles (L62-L83, L84-L105).

render.py draws every bundled "recorded"/"video" level over its capture and scores the ink (recorded tol1 >= 0.99, video
>= 0.97), and with --reveals proves what every door hides on the round shot where it is first open. This wrapper only
updates what the recast changed: the substitute map (ORCH 19 + the repeats of phone session 2) and two exclusions the
session-2 boards need (the obstacle art is never scored): the CORNER art (red plate + blue spring, ±0.8 cell) and the
cells of a hidden arrow that poke out of its door (L62's humps, drawn by the game only once the door opens).

  python3 design/tools/overlay_recast.py --levels 62,63,... --out build/recast/overlay [--reveals] [--negative] [--sheet]
  python3 design/tools/overlay_recast.py --elevators --levels 102 --out build/recast2/overlay [--negative]
      (content recast 2) WHAT A v552 ELEVATOR HIDES: its layer-2 arrows drawn over the round shot the bot dumped right after
      the platform opened (research/levels/Lnnn-open1.json "shot"); inside the platform ± 0.5 cell ALL ink must be those
      arrows (every platform arrow has left by then; start-visible arrows around the platform are masked as for doors).
Since the level re-order (PUBLISH item 12) the research files are found by the board's RESEARCH slot (level_order.py: its
provenance in design/levels.json, which the bundle must match), not by the level it ships at; --levels takes shipped levels.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(APP, 'tools', 'levels'))
import render as R  # noqa: E402
sys.path.insert(0, HERE)
import level_order as LO  # noqa: E402

# The V2 board a level ships (research/levels/video/V2-L0nn.json) and every other research file come from the board's
# provenance (was the slot map {35: 32, 45: 33, 51: 34, 52: 35, 72: 36, 75: 38, 77: 37}, which the re-order invalidates).
R.SUBST = {}


def research_file(b):
    return LO.research_json(b if '_rslot' in b else LO.with_provenance(b))


R.research_file = research_file
_exclusion = R.exclusion


def exclusion(b, rj, geo, shape):
    ex = _exclusion(b, rj, geo, shape)
    p = geo.p

    def rect(cells, m):
        xs, ys = zip(*[geo.xy(*c) for c in cells])
        xa, xb = int(min(xs) - m * p), int(math.ceil(max(xs) + m * p))
        ya, yb = int(min(ys) - m * p), int(math.ceil(max(ys) + m * p))
        ex[max(0, ya):max(0, yb + 1), max(0, xa):max(0, xb + 1)] = True
    doors = {o['id']: {tuple(c) for c in o['cells']} for o in b['obstacles'] if o['kind'] == 'door'}
    for o in b['obstacles']:
        if o['kind'] == 'corner':
            rect(o['cells'], 0.8)
    for a in b['arrows']:
        d = doors.get(a.get('hidden_by'))
        if d:
            for c in a['cells']:
                if tuple(c) not in d:
                    rect([c], 0.62)
    return ex


R.exclusion = exclusion


def prove_elevators(argv):
    import json
    out = argv[argv.index('--out') + 1] if '--out' in argv else os.path.join(APP, 'build', 'recast2', 'overlay')
    only = {int(x) for x in argv[argv.index('--levels') + 1].split(',')} if '--levels' in argv else None
    os.makedirs(out, exist_ok=True)
    rows = []
    for name in sorted(os.listdir(R.LEVELS)):
        if not name.startswith('level_'):
            continue
        b = LO.with_provenance(json.load(open(os.path.join(R.LEVELS, name))))
        if b['source'] != 'recorded' or (only and b['level'] not in only):
            continue
        for e in [o for o in b['obstacles'] if o['kind'] == 'elevator']:
            rj = json.load(open(R.research_file(b)))
            op = json.load(open(os.path.join(R.RESEARCH, 'L%03d-open1.json' % b['_rslot'])))
            shot = os.path.join(APP, op['shot'])
            hidden = [a for a in b['arrows'] if a.get('hidden_by') == e['id']]
            plat = set(e.get('arrows', []))
            b2 = dict(b, arrows=[a for a in b['arrows'] if a['id'] not in plat])   # gone by the open shot: not masked
            region = R.reveal_region(b2, e, None)
            res, vis = R.prove(b, rj, shot, arrows_override=hidden, region=region)
            res.update(elevator=e['id'], hidden_arrows=len(hidden), shot=os.path.relpath(shot, APP))
            if b['_rslot'] != b['level']:
                res['board'] = LO.label(b)
            R.overlay_png(b, res, vis, os.path.join(out, 'L%03d-%s-elevator-overlay.png' % (b['level'], e['id'])))
            if '--negative' in argv and len(hidden) >= 2:
                res['negative_controls'] = []
                flat = [dict(a, hidden_by=None, layer=1) for a in hidden]
                for mname, arrows in R.mutations(dict(b, arrows=flat, obstacles=[])):
                    mres, _ = R.prove(b, rj, shot, arrows_override=arrows, region=region)
                    res['negative_controls'].append(dict(mutation=mname, tol1=mres['tol1'],
                                                         caught_by_iou_gate=mres['tol1'] < res['gate'],
                                                         caught_by_local_check=not (mres['depth_ok'] and mres['coverage_ok'])))
            rows.append(res)
            print('L%03d elevator %s %2d hidden arrows on %s: IoU %.4f tol1 %.4f %s | depth %.1f/%.1f cov %.3f%s' % (
                b['level'], e['id'], len(hidden), os.path.basename(shot), res['iou'], res['tol1'],
                'PASS' if res['pass'] else 'FAIL', res['max_missed_depth_px'], res['max_extra_depth_px'],
                res['worst_arrow_coverage'], '' if res['depth_ok'] and res['coverage_ok'] else '  LOCAL-FLAG'), flush=True)
            for nc in res.get('negative_controls', []):
                print('      negative: %-40s tol1 %.4f -> %s' % (nc['mutation'], nc['tol1'], 'CAUGHT (%s)' % ', '.join(
                    x for x, y in (('IoU', nc['caught_by_iou_gate']), ('local', nc['caught_by_local_check'])) if y)
                    if nc['caught_by_iou_gate'] or nc['caught_by_local_check'] else 'MISSED'), flush=True)
    json.dump(dict(elevators=len(rows), passed=sum(r['pass'] for r in rows), table=rows),
              open(os.path.join(out, 'elevators-report.json'), 'w'), indent=1, default=str)
    print('render --elevators: %d elevators, %d pass' % (len(rows), sum(r['pass'] for r in rows)))
    return 0 if rows and all(r['pass'] for r in rows) else 1


if __name__ == '__main__':
    if '--elevators' in sys.argv[1:]:
        sys.exit(prove_elevators(sys.argv[1:]))
    sys.exit(R.main(sys.argv[1:]))
