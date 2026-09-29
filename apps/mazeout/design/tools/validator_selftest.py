#!/usr/bin/env python3
"""validator_selftest.py — negative controls for validate_levels.py (SPEC-gameplay §14.4, LEVELS.md §5).

Each mutation of design/levels.json must make the validator fail; prints CAUGHT/MISSED per mutation.
  python3 design/tools/validator_selftest.py        (run from anywhere)
Targets name BOARDS by their research slot (level_order.py: v552's number for a phone board), not by position, so the same
20 boards are mutated after the level re-order (PUBLISH item 12); a board that ships elsewhere is labelled "[ships at Lk]".
"""
import json, subprocess, sys, os, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
src = json.load(open('../levels.json'))
import level_order  # noqa: E402
_board, _slot = level_order.resolver(src)
def run(doc):
    os.makedirs('work', exist_ok=True)
    json.dump(doc, open('work/mut.json', 'w'))
    r = subprocess.run([sys.executable, 'validate_levels.py', 'work/mut.json'], capture_output=True, text=True)
    return r.returncode, [l for l in r.stdout.splitlines() if l.startswith('ERROR')][:2]
def lv(doc, n): return _board(doc, n)
def at(name, n): return name if _slot(n) == n else '%s [ships at L%d]' % (name, _slot(n))
muts = []
def m1(d):
    for o in lv(d, 13)['obstacles']:
        if o['kind'] == 'box' and o['counter'] == 28: o['counter'] = 29
muts.append((at('L13 box counter 28 -> 29 (tight, research/video-levels.md)', 13), m1))
def m2(d):
    a = next(a for a in lv(d, 29)['arrows'] if a['id'] == 67)
    a['cells'] = a['cells'][::-1]
    import arrowcore as ac
    a['dir'] = ac.dir_between(tuple(a['cells'][-2]), tuple(a['cells'][-1]))
muts.append((at('L29 arrow 67 reversed', 29), m2))
def m3(d): lv(d, 7).pop('unlock')
muts.append((at('L7 unlock card removed', 7), m3))
def m4(d):
    for o in lv(d, 21)['obstacles']:
        if o['kind'] == 'pipe': o['counter'] = 0
muts.append((at('L21 pipe counter 0', 21), m4))
def m5(d):
    for o in lv(d, 33)['obstacles']:
        if o['kind'] == 'door': o['reveals'] = o.get('reveals', [])[1:]; break
muts.append((at('L33 door reveals one arrow short', 33), m5))
def m6(d):
    l = lv(d, 47); l['obstacles'] = [o for o in l['obstacles'] if not (o['kind'] == 'key' and o['id'] == 'k1')]
muts.append((at('L47 hidden key removed (a door can never open)', 47), m6))
def m7(d):
    t = next(o for o in lv(d, 32)['obstacles'] if o['kind'] == 'tape'); t['cells'][0] = [t['cells'][0][0], t['cells'][0][1] + 1]
muts.append((at('L32 tape tie moved off the cell behind the head', 32), m7))
def m8(d):
    twin = json.loads(json.dumps(lv(src, 21)))
    lv(d, 35)['arrows'] = twin['arrows']; lv(d, 35)['obstacles'] = twin['obstacles']; lv(d, 35)['cols'] = twin['cols']; lv(d, 35)['rows'] = twin['rows']; lv(d, 35).pop('metrics', None)
muts.append((at('L35 back to the phone board = video L21 (repeat)', 35), m8))
def m9(d):
    for o in lv(d, 62)['obstacles']:
        if o['kind'] == 'box': o['counter'] = len(lv(d, 62)['arrows'])
muts.append((at('L62 box counter = arrows (never breaks)', 62), m9))
def m10(d):
    for o in lv(d, 31)['obstacles']:
        if o['kind'] == 'elevator': o['arrows'] = o['arrows'][1:]
muts.append((at('L31 elevator platform list short', 31), m10))
# phone session 2 (L62-L83): corners, pipes under doors, a hidden arrow poking out of its door, the repeated boards
def m11(d):
    for o in lv(d, 70)['obstacles']:
        if o['kind'] == 'corner': o['turn'] = {'downRight': 'upLeft', 'upLeft': 'downRight', 'downLeft': 'upRight',
                                               'upRight': 'downLeft'}[o['turn']]
muts.append((at('L70 corners turned the other way (the plate faces away)', 70), m11))
def m12(d):
    p = next(o for o in lv(d, 69)['obstacles'] if o['kind'] == 'pipe' and o['cells'][0][1] >= 26)
    for c in p['cells']: c[1] -= 3
    for e in p['ends']: e['cell'][1] -= 3
    if p.get('counter_at'): p['counter_at'][1] -= 3
muts.append((at('L69 a pipe under a door moved half out of it', 69), m12))
def m13(d):
    l = lv(d, 62)
    stub = next(a for a in l['arrows'] if a.get('hidden_by') and any(c[1] == 20 for c in a['cells']))
    stub.pop('hidden_by')
    for o in l['obstacles']:
        if o.get('reveals') and stub['id'] in o['reveals']: o['reveals'].remove(stub['id'])
muts.append((at('L62 the key arrow under the door made visible (covered by the door)', 62), m13))
def m14(d):
    twin = json.loads(json.dumps(lv(src, 14)))
    for k in ('arrows', 'obstacles', 'cols', 'rows'): lv(d, 72)[k] = twin[k]
    lv(d, 72).pop('metrics', None)
muts.append((at('L72 back to the phone board = L14 (v552 repeats it)', 72), m14))
def m15(d): lv(d, 70).pop('unlock')
muts.append((at('L70 corner unlock card removed', 70), m15))
# content recast 2 (phone session 3, L84-L105; SPEC.md §5 item 28 dedup incl. rotations and mirrors)
imp = {l['level']: l for l in json.load(open('work/imported.json'))}
def phone_board(d, n):
    for k in ('arrows', 'obstacles', 'cols', 'rows'): lv(d, n)[k] = json.loads(json.dumps(imp[n][k]))
    lv(d, n).pop('metrics', None)
def m16(d): phone_board(d, 86)
muts.append((at('L86 back to the phone board = L66 (v552 repeats it)', 86), m16))
def m17(d):
    src_ = lv(d, 94); l = lv(d, 134); W = src_['cols']
    flip = {'left': 'right', 'right': 'left', 'up': 'up', 'down': 'down'}
    l['arrows'] = [dict(id=a['id'], cells=[[W - 1 - c[0], c[1]] for c in a['cells']], dir=flip[a['dir']]) for a in src_['arrows']]
    l['obstacles'] = []; l['cols'] = W; l['rows'] = src_['rows']; l.pop('metrics', None)
muts.append((at('L134 = L94 mirrored left-right (a mirrored repeat)', 134), m17))
def m18(d): phone_board(d, 101)
muts.append((at('L101 back to the phone board = V2-L032 (ships at L35)', 101), m18))
def m19(d):
    l = lv(d, 93); l['obstacles'] = [o for o in l['obstacles'] if not (o['kind'] == 'key' and o['id'] == 'k1')]
muts.append((at('L93 the key hidden under the first door removed (the staircase stops)', 93), m19))
def m20(d):
    for o in lv(d, 102)['obstacles']:
        if o['kind'] == 'elevator': o['arrows'] = o['arrows'][1:]
muts.append((at('L102 elevator platform list short (v552 elevator + corners)', 102), m20))
ok = 0
for name, f in muts:
    d = copy.deepcopy(src); f(d)
    rc, errs = run(d)
    print('CAUGHT' if rc else 'MISSED', name, errs[:1])
    ok += rc != 0
os.remove('work/mut.json')
print('%d/%d caught' % (ok, len(muts)))
