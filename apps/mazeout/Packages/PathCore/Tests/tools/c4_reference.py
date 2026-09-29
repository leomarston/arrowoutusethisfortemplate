#!/usr/bin/env python3
"""c4_reference.py — C4's fixtures from the Python reference tools (design/tools, read-only; nothing is written there).

  python3 Tests/tools/c4_reference.py runtime [--from 151 --to 650] [--jsonl a.jsonl ...]
      Fixtures/c4_runtime_reference.json: for every level past the authored end, gen_levels.generate(curve, n) (curve =
      design/levels.json "curve") as the SHA-256 of its canonical line (json.dumps(sort_keys, compact); no "schema"), its
      byte count, the winning attempt, the rejected reasons, and validate_levels.check_level's errors and warnings on it.
      Slow (the Python generator: ~0.3-3 s per level); `--jsonl` merges the output of earlier runs of this script's
      `rows` mode instead of regenerating.
  python3 Tests/tools/c4_reference.py rows <from> <to> <out.jsonl>
      the same rows as JSON lines (run several ranges in parallel, then `runtime --jsonl …`).
  python3 Tests/tools/c4_reference.py negatives
      Fixtures/c4_negative_controls.json: design/tools/validator_selftest.py's 20 mutations of design/levels.json, each with
      the Python validator's error list (validate_levels.check_level on the mutated level + the document checks).
  python3 Tests/tools/c4_reference.py extras
      Fixtures/c4_reference_extras.json: gen_levels.mask_for for every silhouette at four sizes; Python round()/repr() of
      sample floats; level_seed values.
"""
import copy
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))          # apps/mazeout
TOOLS = os.path.join(APP, 'design', 'tools')
FIX = os.path.abspath(os.path.join(HERE, '..', 'Fixtures'))
sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True                                           # design/ stays untouched
import arrowcore as ac  # noqa: E402
import gen_levels  # noqa: E402
import pathrandom  # noqa: E402
import validate_levels as vl  # noqa: E402
import level_order  # noqa: E402  (PUBLISH item 12: boards by research slot, not by position)

# the pinned content (Tests/Fixtures/content, design/tools/pin_fixtures.py); = design/levels.json when the pins are current
LEVELS = os.path.join(FIX, 'content', 'levels.json')


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def row(curve, n):
    t = time.time()
    try:
        lvl, info = gen_levels.generate(curve, n)
    except Exception as e:                                               # noqa: BLE001 (recorded, not hidden)
        return dict(level=n, error=repr(e))
    dt = time.time() - t
    line = canon(lvl)
    errs, warns = [], []
    l2 = json.loads(line)
    l2['schema'] = 1
    vl.check_level(l2, errs, warns)
    return dict(level=n, sha256=hashlib.sha256(line.encode()).hexdigest(), bytes=len(line.encode()),
                attempt=info['attempt'], rejected=info['rejected'], kinds=info['kinds'], tag=info['target']['tag'],
                errors=errs, warnings=warns, python_gen_s=round(dt, 3))


def cmd_rows(a, b, out):
    curve = json.load(open(LEVELS))['curve']
    with open(out, 'w') as f:
        for n in range(a, b + 1):
            f.write(json.dumps(row(curve, n)) + '\n')
            f.flush()


def cmd_runtime(a, b, jsonl):
    rows = {}
    for p in jsonl:
        for line in open(p):
            r = json.loads(line)
            if 'line' in r:                                              # the scratch runner's format: hash it here
                r = dict(level=r['level'], sha256=hashlib.sha256(r['line'].encode()).hexdigest(),
                         bytes=len(r['line'].encode()), attempt=json.loads(r['info'])['attempt'],
                         rejected=json.loads(r['info'])['rejected'], kinds=json.loads(r['info'])['kinds'],
                         tag=json.loads(r['info'])['target']['tag'], errors=r['errors'], warnings=r['warnings'],
                         python_gen_s=r.get('gen_s'))
            rows[r['level']] = r
    curve = json.load(open(LEVELS))['curve']
    for n in range(a, b + 1):
        if n not in rows:
            rows[n] = row(curve, n)
    out = dict(_about='C4 runtime-level reference (Tests/tools/c4_reference.py): design/tools/gen_levels.py + '
                      'validate_levels.check_level on L%d-L%d, curve = design/levels.json "curve". sha256 = the canonical '
                      'line json.dumps(level, sort_keys=True, separators=(",", ":")), no "schema" key.' % (a, b),
               curve_sha256=hashlib.sha256(canon(curve).encode()).hexdigest(),
               levels=[rows[n] for n in range(a, b + 1)])
    with open(os.path.join(FIX, 'c4_runtime_reference.json'), 'w') as f:
        json.dump(out, f, indent=0, sort_keys=True)
        f.write('\n')
    print('c4_runtime_reference.json: %d levels, %d with python errors' % (
        len(out['levels']), sum(1 for r in out['levels'] if r.get('errors') or r.get('error'))))


def mutations(src):
    """validator_selftest.py's 20 mutations. Targets name BOARDS by their research slot (design/tools/level_order.py), so after
    the level re-order the same boards are mutated; `levels` lists the SLOTS they ship at (what the Swift test swaps)."""
    board, slot = level_order.resolver(src)

    def lv(doc, n):
        return board(doc, n)

    def at(name, n):
        return name if slot(n) == n else '%s [ships at L%d]' % (name, slot(n))
    muts = []

    def m1(d):
        for o in lv(d, 13)['obstacles']:
            if o['kind'] == 'box' and o['counter'] == 28:
                o['counter'] = 29
    muts.append((at('L13 box counter 28 -> 29 (tight)', 13), [slot(13)], m1))

    def m2(d):
        a = next(a for a in lv(d, 29)['arrows'] if a['id'] == 67)
        a['cells'] = a['cells'][::-1]
        a['dir'] = ac.dir_between(tuple(a['cells'][-2]), tuple(a['cells'][-1]))
    muts.append((at('L29 arrow 67 reversed', 29), [slot(29)], m2))

    def m3(d):
        lv(d, 7).pop('unlock')
    muts.append((at('L7 unlock card removed', 7), [slot(7)], m3))

    def m4(d):
        for o in lv(d, 21)['obstacles']:
            if o['kind'] == 'pipe':
                o['counter'] = 0
    muts.append((at('L21 pipe counter 0', 21), [slot(21)], m4))

    def m5(d):
        for o in lv(d, 33)['obstacles']:
            if o['kind'] == 'door':
                o['reveals'] = o.get('reveals', [])[1:]
                break
    muts.append((at('L33 door reveals one arrow short', 33), [slot(33)], m5))

    def m6(d):
        l = lv(d, 47)
        l['obstacles'] = [o for o in l['obstacles'] if not (o['kind'] == 'key' and o['id'] == 'k1')]
    muts.append((at('L47 hidden key removed', 47), [slot(47)], m6))

    def m7(d):
        t = next(o for o in lv(d, 32)['obstacles'] if o['kind'] == 'tape')
        t['cells'][0] = [t['cells'][0][0], t['cells'][0][1] + 1]
    muts.append((at('L32 tape tie moved off the cell behind the head', 32), [slot(32)], m7))

    def m8(d):
        twin = json.loads(json.dumps(lv(src, 21)))
        for k in ('arrows', 'obstacles', 'cols', 'rows'):
            lv(d, 35)[k] = twin[k]
        lv(d, 35).pop('metrics', None)
    muts.append((at('L35 back to the phone board = video L21 (repeat)', 35), [slot(35)], m8))

    def m9(d):                                        # recast 2026-09-25: L64 is v552's plain Hard board now
        for o in lv(d, 62)['obstacles']:
            if o['kind'] == 'box':
                o['counter'] = len(lv(d, 62)['arrows'])
    muts.append((at('L62 box counter = arrows (never breaks)', 62), [slot(62)], m9))

    def m10(d):
        for o in lv(d, 31)['obstacles']:
            if o['kind'] == 'elevator':
                o['arrows'] = o['arrows'][1:]
    muts.append((at('L31 elevator platform list short', 31), [slot(31)], m10))

    # phone session 2 (validator_selftest.py m11-m15)
    def m11(d):
        for o in lv(d, 70)['obstacles']:
            if o['kind'] == 'corner':
                o['turn'] = {'downRight': 'upLeft', 'upLeft': 'downRight', 'downLeft': 'upRight', 'upRight': 'downLeft'}[o['turn']]
    muts.append((at('L70 corners turned the other way (the plate faces away)', 70), [slot(70)], m11))

    def m12(d):
        p = next(o for o in lv(d, 69)['obstacles'] if o['kind'] == 'pipe' and o['cells'][0][1] >= 26)
        for c in p['cells']:
            c[1] -= 3
        for e in p['ends']:
            e['cell'][1] -= 3
        if p.get('counter_at'):
            p['counter_at'][1] -= 3
    muts.append((at('L69 a pipe under a door moved half out of it', 69), [slot(69)], m12))

    def m13(d):
        l = lv(d, 62)
        stub = next(a for a in l['arrows'] if a.get('hidden_by') and any(c[1] == 20 for c in a['cells']))
        stub.pop('hidden_by')
        for o in l['obstacles']:
            if o.get('reveals') and stub['id'] in o['reveals']:
                o['reveals'].remove(stub['id'])
    muts.append((at('L62 the key arrow under the door made visible (covered by the door)', 62), [slot(62)], m13))

    def m14(d):
        twin = json.loads(json.dumps(lv(src, 14)))
        for k in ('arrows', 'obstacles', 'cols', 'rows'):
            lv(d, 72)[k] = twin[k]
        lv(d, 72).pop('metrics', None)
    muts.append((at('L72 back to the phone board = L14 (v552 repeats it)', 72), [slot(72)], m14))

    def m15(d):
        lv(d, 70).pop('unlock')
    muts.append((at('L70 corner unlock card removed', 70), [slot(70)], m15))

    # content recast 2 (validator_selftest.py m16-m20: phone session 3, SPEC.md §5 item 28 dedup incl. rotations/mirrors)
    imp = {l['level']: l for l in json.load(open(os.path.join(TOOLS, 'work', 'imported.json')))}

    def phone_board(d, n):
        for k in ('arrows', 'obstacles', 'cols', 'rows'):
            lv(d, n)[k] = json.loads(json.dumps(imp[n][k]))
        lv(d, n).pop('metrics', None)

    def m16(d):
        phone_board(d, 86)
    muts.append((at('L86 back to the phone board = L66 (v552 repeats it)', 86), [slot(86)], m16))

    def m17(d):
        src_ = lv(d, 94)
        l = lv(d, 134)
        W = src_['cols']
        flip = {'left': 'right', 'right': 'left', 'up': 'up', 'down': 'down'}
        l['arrows'] = [dict(id=a['id'], cells=[[W - 1 - c[0], c[1]] for c in a['cells']], dir=flip[a['dir']])
                       for a in src_['arrows']]
        l['obstacles'] = []
        l['cols'] = W
        l['rows'] = src_['rows']
        l.pop('metrics', None)
    muts.append((at('L134 = L94 mirrored left-right (a mirrored repeat)', 134), [slot(134)], m17))

    def m18(d):
        phone_board(d, 101)
    muts.append((at('L101 back to the phone board = V2-L032 (ships at L35)', 101), [slot(101)], m18))

    def m19(d):
        l = lv(d, 93)
        l['obstacles'] = [o for o in l['obstacles'] if not (o['kind'] == 'key' and o['id'] == 'k1')]
    muts.append((at('L93 the key hidden under the first door removed', 93), [slot(93)], m19))

    def m20(d):
        for o in lv(d, 102)['obstacles']:
            if o['kind'] == 'elevator':
                o['arrows'] = o['arrows'][1:]
    muts.append((at('L102 elevator platform list short', 102), [slot(102)], m20))
    return muts


def doc_errors(doc):
    """validate_levels.main's document checks without re-validating every level."""
    errs = []
    levels = doc['levels']
    first = {}
    for l in levels:
        for o in l['obstacles']:
            f = vl.FEATURE_OF.get(o['kind'])
            if f and f not in first:
                first[f] = l['level']
    unlocks = {u['feature']: u for u in doc.get('unlocks', [])}
    for f, n in sorted(first.items(), key=lambda x: x[1]):
        lv = levels[n - 1]
        if lv.get('unlock') != f:
            errs.append('L%d: first %s but unlock=%s' % (n, f, lv.get('unlock')))
        if f not in unlocks or unlocks[f]['level'] != n:
            errs.append('unlocks.json: %s should be at L%d (%s)' % (f, n, unlocks.get(f, {}).get('level')))
    for l in levels:
        if l.get('unlock') and first.get(l['unlock']) != l['level']:
            errs.append('L%d: unlock %s is not a first appearance' % (l['level'], l['unlock']))
    for later, first in vl.repeated_boards(levels):                     # content recast 2: rotations and mirrors too
        errs.append('L%d repeats L%d' % (later, first))
    return errs


def cmd_negatives():
    src = json.load(open(LEVELS))
    rows = []
    for name, touched, f in mutations(src):
        d = copy.deepcopy(src)
        f(d)
        errs, warns = [], []
        for n in touched:
            vl.check_level(d['levels'][n - 1], errs, warns)
        errs += doc_errors(d)
        rows.append(dict(mutation=name, levels=touched, level_json={str(n): d['levels'][n - 1] for n in touched},
                         python_errors=errs))
        print('CAUGHT' if errs else 'MISSED', name, errs[:1])
    with open(os.path.join(FIX, 'c4_negative_controls.json'), 'w') as fo:
        json.dump(dict(_about='design/tools/validator_selftest.py mutations; python_errors = validate_levels.check_level '
                              'on the mutated level(s) + the document checks (Tests/tools/c4_reference.py negatives)',
                       mutations=rows), fo, indent=0, sort_keys=True)
        fo.write('\n')


def cmd_extras():
    masks = []
    for shape in ['oval', 'octagon', 'notch', 'blocks', 'cross', 'heart', 'diamond', 'arch']:
        for W, H in ((12, 12), (15, 19), (20, 26), (26, 36)):
            m = gen_levels.mask_for(shape, W, H)
            masks.append(dict(shape=shape, cols=W, rows=H, count=len(m),
                              rows_text=[''.join('#' if (c, r) in m else '.' for c in range(W)) for r in range(H)]))
    samples = [0.0625, 2.675, 8.4, 156.0, 0.1 + 0.2, 1e-05, 1e16, 123456.789, 7.0 / 3.0, 1.0 / 3.0, 0.5, 2.5, 0.0005,
               12.3456789, 59.95, 1234.5678, 0.001, 9.999999, 100.0 / 7.0]
    for k in range(1, 60):
        samples.append(k * 0.6 + (k % 7) * 1.14)
        samples.append(180 - (k * 0.6 + (k % 3) * 1.14))
        samples.append(k / 7.0)
    rounds = [dict(x=repr(x), r1=repr(round(x, 1)), r3=repr(round(x, 3)), repr=repr(x)) for x in samples]
    seeds = [dict(level=n, seed=pathrandom.level_seed(n, 15177990143040770677)) for n in (62, 65, 150, 151, 1000, 99999)]
    with open(os.path.join(FIX, 'c4_reference_extras.json'), 'w') as f:
        json.dump(dict(_about='gen_levels.mask_for, Python round()/repr(), pathrandom.level_seed (c4_reference.py extras)',
                       masks=masks, rounds=rounds, level_seeds=seeds), f, indent=0, sort_keys=True)
        f.write('\n')
    print('extras: %d masks, %d floats' % (len(masks), len(rounds)))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'rows':
        cmd_rows(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif cmd == 'runtime':
        args = sys.argv[2:]
        a = int(args[args.index('--from') + 1]) if '--from' in args else 151
        b = int(args[args.index('--to') + 1]) if '--to' in args else 650
        js = [x for x in args if x.endswith('.jsonl')]
        cmd_runtime(a, b, js)
    elif cmd == 'negatives':
        cmd_negatives()
    elif cmd == 'extras':
        cmd_extras()
    else:
        raise SystemExit(__doc__)
