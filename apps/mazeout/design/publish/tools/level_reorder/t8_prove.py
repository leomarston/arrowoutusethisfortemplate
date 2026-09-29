#!/usr/bin/env python3
"""t8_prove.py — PLAN-P T8 LV-TOOLS, proven on SCRATCH copies (the real design/levels.json, bundle, fixtures and pins are
never written; B0 applies). Evidence -> build/p/T8/evidence/.

Trees under build/p/T8/scratch/ (design/, tools/levels/, Packages/PathCore/Tests/{tools,Fixtures}, App/Resources,
App/Board/LabBoards copied; research/ symlinked read-only; PYTHONDONTWRITEBYTECODE=1 everywhere):
  orig   today's content + today's tools (build/p/T8/orig: the untouched originals)
  cur    today's content + the T8 tools (design/tools as edited + the staged fenced files)
  new    cur, then the re-order applied, the fixtures re-pinned, the bundle rewritten (Python mirror of lvtool, proven
         byte-exact on today's bundle) and provenance-stripped

  python3 design/publish/tools/level_reorder/t8_prove.py setup
  python3 design/publish/tools/level_reorder/t8_prove.py fast        # order, guard, hook, check, rule controls, bundle,
                                                                    # strip, scans, c4b, c4_reference, levels_report
  python3 design/publish/tools/level_reorder/t8_prove.py slow        # validator, repeats, selftests (minutes: background)
  python3 design/publish/tools/level_reorder/t8_prove.py samples     # render / overlay / replay on moved boards
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
T8 = os.path.join(APP, 'build', 'p', 'T8')
SCR = os.path.join(T8, 'scratch')
EV = os.path.join(T8, 'evidence')
ORIG = os.path.join(T8, 'orig')
STAGED = os.path.join(HERE, 'staged')
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
RESEARCH_SHA = '63e410012fe32c3ace59f13731d11b6426b98beac7a7d6afff55a2882b13b0b4'
ORDERED_SHA = '8ace3d3a564867cf31d5e0fed51938bdbfacb539b3eda0fd3057522558f062cc'     # level-reorder.md §8 "8ace3d3a…"
NEW_TOOLS = ['design/tools/level_order.py', 'design/tools/reorder_levels.py', 'design/tools/strip_provenance.py']
CHANGED = ['design/tools/validator_selftest.py', 'design/tools/overlay_recast.py', 'design/tools/levels_report.py',
           'design/tools/build_levels.py', 'tools/levels/render.py', 'tools/levels/replay_bundle.py',
           'Packages/PathCore/Tests/tools/c4b_bot_replay.py', 'Packages/PathCore/Tests/tools/c4_reference.py']
RESULTS = {}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def run(tree, args, log=None, ok=(0,), timeout=900):
    t0 = time.time()
    r = subprocess.run(['nice', '-n', '19', sys.executable] + args, cwd=tree, env=ENV, capture_output=True, text=True,
                       timeout=timeout)
    out = r.stdout + r.stderr
    if log:
        with open(os.path.join(EV, log), 'w') as f:
            f.write('$ (cwd %s) python3 %s\n# rc %d, %.1f s\n%s' % (os.path.relpath(tree, APP), ' '.join(args), r.returncode,
                                                                 time.time() - t0, out))
    if ok is not None and r.returncode not in ok:
        raise SystemExit('FAILED rc %d: %s\n%s' % (r.returncode, ' '.join(args), out[-3000:]))
    return r.returncode, out


def record(key, passed, **info):
    RESULTS[key] = dict(passed=bool(passed), **info)
    print('%-44s %s  %s' % (key, 'PASS' if passed else 'FAIL', json.dumps(info)[:230]), flush=True)


# ------------------------------------------------------------------------------------------------ setup
def make_tree(name, tools):
    T = os.path.join(SCR, name)
    if os.path.exists(T):
        shutil.rmtree(T)
    os.makedirs(os.path.join(T, 'design', 'publish', 'tools', 'level_reorder'))
    ign = shutil.ignore_patterns('__pycache__', '*.pyc', '*.tmp-reorder')
    shutil.copytree(os.path.join(APP, 'design', 'tools'), os.path.join(T, 'design', 'tools'), ignore=ign)
    for f in ('levels.json', 'LEVELS.md'):
        shutil.copyfile(os.path.join(APP, 'design', f), os.path.join(T, 'design', f))
    shutil.copyfile(os.path.join(HERE, 'level_order_candidate.json'),
                    os.path.join(T, 'design', 'publish', 'tools', 'level_reorder', 'level_order_candidate.json'))
    shutil.copytree(os.path.join(APP, 'tools', 'levels'), os.path.join(T, 'tools', 'levels'), ignore=ign)
    for d in ('tools', 'Fixtures'):
        shutil.copytree(os.path.join(APP, 'Packages', 'PathCore', 'Tests', d), os.path.join(T, 'Packages', 'PathCore', 'Tests', d),
                        ignore=ign)
    shutil.copytree(os.path.join(APP, 'App', 'Resources'), os.path.join(T, 'App', 'Resources'))
    shutil.copytree(os.path.join(APP, 'App', 'Board', 'LabBoards'), os.path.join(T, 'App', 'Board', 'LabBoards'))
    os.symlink(os.path.join(APP, 'research'), os.path.join(T, 'research'))
    if tools == 'orig':
        for rel in CHANGED:
            shutil.copyfile(os.path.join(ORIG, rel), os.path.join(T, rel))
        for rel in NEW_TOOLS:
            os.remove(os.path.join(T, rel))
    else:
        for rel in CHANGED:
            st = os.path.join(STAGED, rel)
            if os.path.exists(st):
                shutil.copyfile(st, os.path.join(T, rel))
    return T


def cmd_setup():
    os.makedirs(EV, exist_ok=True)
    for name, tools in (('orig', 'orig'), ('cur', 'new'), ('new', 'new')):
        make_tree(name, tools)
    base = {rel: sha(os.path.join(ORIG, rel)) for rel in CHANGED}
    live = {rel: sha(os.path.join(APP, rel)) for rel in CHANGED}
    json.dump(dict(originals=base, live_now=live,
                   staged={rel: sha(os.path.join(STAGED, rel)) for rel in CHANGED if os.path.exists(os.path.join(STAGED, rel))},
                   new=[r for r in NEW_TOOLS]), open(os.path.join(EV, 'tool-shas.json'), 'w'), indent=1)
    print('trees: %s' % ', '.join(sorted(os.listdir(SCR))))


# ------------------------------------------------------------------------------------------------ fast
def cmd_fast():
    orig, cur, new = (os.path.join(SCR, n) for n in ('orig', 'cur', 'new'))
    L = 'design/levels.json'
    # hook dormant: assemble without a plan = today's bytes
    run(new, ['design/tools/build_levels.py', 'assemble'], 'hook-noplan.log')
    record('hook: assemble without a plan unchanged', sha(os.path.join(new, L)) == RESEARCH_SHA,
           sha=sha(os.path.join(new, L))[:16])
    # plan x2
    run(new, ['design/tools/reorder_levels.py', 'plan'], 'plan-1.log')
    p1 = open(os.path.join(new, 'design', 'level-order.json'), 'rb').read()
    run(new, ['design/tools/reorder_levels.py', 'plan'], 'plan-2.log')
    p2 = open(os.path.join(new, 'design', 'level-order.json'), 'rb').read()
    plan = json.loads(p2)
    cand = json.load(open(os.path.join(HERE, 'level_order_candidate.json')))
    record('order byte-identical x2', p1 == p2, plan_sha=hashlib.sha256(p2).hexdigest()[:16], bytes=len(p2))
    record('order == reorder_ref candidate', plan['order'] == cand['order'] and plan['J'] == cand['J'],
           attempt=plan['attempt'], J=plan['J'], moved=plan['moved'], search=plan['search'])
    shutil.copyfile(os.path.join(new, 'design', 'level-order.json'), os.path.join(EV, 'level-order.json'))
    # apply + guard
    run(new, ['design/tools/reorder_levels.py', 'apply'], 'apply.log')
    s1 = sha(os.path.join(new, L))
    record('apply -> the plan output (= level-reorder.md 8ace3d3a)', s1 == ORDERED_SHA == plan['output']['sha256'], sha=s1[:16])
    _, out = run(new, ['design/tools/reorder_levels.py', 'apply'], 'apply-again.log')
    record('apply again = no-op', sha(os.path.join(new, L)) == s1 and 'already' in out)
    stale = os.path.join(SCR, 'stale.json')
    t = open(os.path.join(orig, L)).read()
    i = t.index('"timer_s":180')
    open(stale, 'w').write(t[:i] + '"timer_s":181' + t[i + 13:])
    before = sha(stale)
    rc, out = run(new, ['design/tools/reorder_levels.py', 'apply', '--levels', stale, '--out', stale + '.out'],
                  'apply-stale.log', ok=None)
    record('apply refuses a stale levels.json', rc == 2 and not os.path.exists(stale + '.out') and sha(stale) == before
           and 'STALE' in out, rc=rc)
    # hook with the plan = apply's bytes; with a stale plan = refused, nothing written
    run(new, ['design/tools/build_levels.py', 'assemble'], 'hook-plan.log')
    record('hook: assemble with the plan = apply', sha(os.path.join(new, L)) == s1)
    good = open(os.path.join(new, 'design', 'level-order.json')).read()
    bad = json.loads(good)
    bad['input']['sha256'] = '0' * 64
    open(os.path.join(new, 'design', 'level-order.json'), 'w').write(json.dumps(bad, indent=1) + '\n')
    rc, out = run(new, ['design/tools/build_levels.py', 'assemble'], 'hook-stale.log', ok=None)
    record('hook: assemble refuses a stale plan', rc != 0 and sha(os.path.join(new, L)) == s1 and 'STALE' in out, rc=rc)
    open(os.path.join(new, 'design', 'level-order.json'), 'w').write(good)
    # full check (re-search + H1-H10)
    rc, out = run(new, ['design/tools/reorder_levels.py', 'check'], 'check.log', ok=None)
    record('check: search reproduces the plan, H1-H10 hold', rc == 0, line=out.strip().splitlines()[-1][:160])
    # rule negative controls on verify()
    rule_controls(new)
    # resolution: provenance == plan order; research slots of the moved boards (level-reorder.md §9 list)
    sys.path.insert(0, os.path.join(new, 'design', 'tools'))
    import level_order as LO
    doc = json.load(open(os.path.join(new, L)))
    sm = LO.slot_map(doc['levels'])
    order = {int(s): o for s, o in plan['order'].items()}
    expect9 = {34: 44, 35: 35, 39: 49, 42: 38, 44: 54, 47: 37, 48: 42, 51: 48, 54: 34, 59: 69, 62: 58, 63: 56, 64: 74,
               69: 59, 73: 82, 74: 84, 75: 68, 76: 73, 79: 89, 80: 71, 82: 76, 86: 81, 89: 99, 93: 96, 98: 88, 100: 100,
               102: 97, 103: 101}
    record('provenance lookup == plan order (150 slots)', LO.order_of(doc['levels']) == order)
    record('board -> slot list of level-reorder.md §9', all(sm[k] == v for k, v in expect9.items()),
           mismatches={k: (sm[k], v) for k, v in expect9.items() if sm[k] != v})
    # pins in scratch
    run(new, ['design/tools/pin_fixtures.py'], 'pin.log')
    run(new, ['design/tools/pin_fixtures.py', '--check'], 'pin-check.log')
    bundle_and_strip(orig, cur, new)
    c4b(orig, cur, new)
    c4ref(orig, cur, new)
    levels_report(orig, cur, new)
    dump('fast')


def rule_controls(new):
    """verify() must catch every broken order (the rules are not vacuous)."""
    sys.path.insert(0, os.path.join(new, 'design', 'tools'))
    import reorder_levels as RL
    research = json.load(open(os.path.join(SCR, 'orig', 'design', 'levels.json')))
    plan = json.load(open(os.path.join(new, 'design', 'level-order.json')))
    good = {int(s): o for s, o in plan['order'].items()}
    F = [RL.features(l) for l in research['levels']]
    P = RL.Problem(F)
    by = {f['n']: f for f in F}

    def swapped(a, b):
        o = dict(good)
        o[a], o[b] = o[b], o[a]
        return o

    corner = next(s for s in range(71, 106) if 'corner' in by[good[s]]['kinds'] and by[good[s]]['tag'] == 'normal')
    dup = dict(good)
    dup[37] = good[38]
    ctrl = [
        ('H2 L34 practice slot without a door (Hard 34 <-> 54)', swapped(34, 54)),
        ('H1 a corner board before the Corner card (L70)', swapped(60, corner)),
        ('H3 a Hard board in a Normal slot', swapped(44, 45)),
        ('H4 the 1:40 board earlier than the first short timer (Hard 54 <-> 74)', swapped(54, 74)),
        ('H5 v552 L40 back at its own number', swapped(36, 40) if good[40] != 40 else swapped(36, 41)),
        ('H6 a Normal board moved > 10', swapped(36, 60)),
        ('H10 a frozen slot changed (L20 <-> L21)', swapped(20, 21)),
        ('H10 not a permutation (a board twice)', dup),
        ('the copied order itself (identity in the zone)', {s: s for s in good}),
    ]
    rows, caught = [], 0
    for name, o in ctrl:
        try:
            applied = RL.permute(research, o)
            bad, _ = RL.verify(research, applied, o, P)
        except SystemExit as e:
            bad = ['refused: %s' % e]
        caught += bool(bad)
        rows.append(dict(control=name, caught=bool(bad), why=bad[:2]))
    json.dump(rows, open(os.path.join(EV, 'rule-controls.json'), 'w'), indent=1)
    record('re-order rule negative controls', caught == len(ctrl), caught='%d/%d' % (caught, len(ctrl)),
           missed=[r['control'] for r in rows if not r['caught']])


def bundle_and_strip(orig, cur, new):
    SP = ['design/tools/strip_provenance.py']
    rc, out = run(cur, SP + ['check-bundle', 'design/levels.json', 'App/Resources/Levels'], 'mirror-vs-today.log', ok=None)
    record('bundle mirror == today\'s App/Resources/Levels', rc == 0, line=out.strip()[:120])
    # the re-ordered bundle (what lv.sh bundle would write), then the strip in place
    run(new, SP + ['bundle', 'design/levels.json', 'App/Resources/Levels'], 'bundle-new.log')
    Ld = lambda T: os.path.join(T, 'App', 'Resources', 'Levels')  # noqa: E731
    diff = sorted(f for f in os.listdir(Ld(cur)) if f != '.gitkeep'
                  and open(os.path.join(Ld(cur), f), 'rb').read() != open(os.path.join(Ld(new), f), 'rb').read())
    lv = [f for f in diff if f.startswith('level_')]
    record('re-ordered bundle: 67 level files change, nothing else', len(lv) == 67 and len(diff) == 67, changed=len(diff),
           aux_changed=[f for f in diff if not f.startswith('level_')])
    rc, out = run(new, SP + ['strip-levels', 'App/Resources/Levels'], 'strip-levels.log')
    rc, out = run(new, SP + ['check-bundle', 'design/levels.json', 'App/Resources/Levels', '--publish'],
                  'strip-vs-publish-mirror.log', ok=None)
    record('stripped bundle == publish form of the mirror (byte)', rc == 0, line=out.strip()[:120])
    # LevelsBundleTests.testTheBundleEqualsDesignLevelsJSON in Python + the provenance join every tool uses
    sys.path.insert(0, os.path.join(new, 'design', 'tools'))
    import level_order as LO
    doc = json.load(open(os.path.join(new, 'design', 'levels.json')))
    bad = []
    for l in doc['levels']:
        b = json.load(open(os.path.join(Ld(new), 'level_%04d.json' % l['level'])))
        try:
            j = LO.with_provenance(b, os.path.join(new, 'design', 'levels.json'))
            if j['_rslot'] != (LO.rslot(l) or l['level']) or 'capture' in b or any(k.startswith('_') for k in b):
                bad.append(l['level'])
        except LO.ProvenanceError as e:
            bad.append(str(e))
    record('stripped bundle: gameplay == design, provenance joins back', not bad, bad=bad[:5])
    # the publish copy of every shipped root, scanned
    pub = os.path.join(SCR, 'publish-new')
    run(new, SP + ['publish', '--app', new, '--out', pub], 'publish-new.log')
    rc, out = run(new, SP + ['scan', pub, '--json', os.path.join(EV, 'scan-publish-new.json')], 'scan-publish-new.log', ok=None)
    rep = json.load(open(os.path.join(EV, 'scan-publish-new.json')))
    lit = [(h['file'], h['token']) for h in rep['hits'] if h['cls'] == 'phone-substring']
    record('stripped copy: 0 provenance hits', rc == 0 and rep['unallowed'] == 0, unallowed=rep['unallowed'],
           literal_regex_hits=rep['acceptance_regex_hits'], literal_hits_are=lit)
    rc, out = run(cur, SP + ['scan', os.path.join(cur, 'App', 'Resources', 'Levels'), os.path.join(cur, 'App', 'Resources', 'Tuning'),
                            os.path.join(cur, 'App', 'Resources', 'Social'), os.path.join(cur, 'App', 'Resources', 'Localizable.xcstrings'),
                            os.path.join(cur, 'App', 'Board', 'LabBoards'), '--json', os.path.join(EV, 'scan-shipped-today.json')],
                  'scan-shipped-today.log', ok=None)
    today = json.load(open(os.path.join(EV, 'scan-shipped-today.json')))
    record('scan finds today\'s provenance (before the strip)', today['unallowed'] > 300, unallowed=today['unallowed'],
           literal=today['acceptance_regex_hits'])
    # tuning: the parsed files differ only by "_" keys and worldModel
    sys.path.insert(0, os.path.join(new, 'design', 'tools'))
    import strip_provenance as SPm
    tun = []
    for f in sorted(os.listdir(os.path.join(new, 'App', 'Resources', 'Tuning'))):
        a = json.load(open(os.path.join(new, 'App', 'Resources', 'Tuning', f)))
        b = json.load(open(os.path.join(pub, 'Tuning', f)))
        want = SPm.transform(a, SPm.is_comment, SPm.tuning_rewrite(f))
        tun.append((f, b == want))
    record('tuning strip = "_" keys dropped + worldModel only', all(x[1] for x in tun), files=[x[0] for x in tun])
    scanner_controls(new, pub)


def scanner_controls(new, pub):
    """The scan must see what it is meant to see: one injected hit per provenance class in a copy of the publish copy."""
    ctl = os.path.join(SCR, 'publish-new-controls')
    if os.path.exists(ctl):
        shutil.rmtree(ctl)
    shutil.copytree(pub, ctl)
    inj = [('research-path', 'Tuning/ui.json', '"loading"', '"loading_src": "research/meta.md",\n  "loading"'),
           ('phone-word', 'Tuning/game.json', '"ftue"', '"note": "measured on the phone",\n  "ftue"'),
           ('version-tag', 'Levels/sessions.json', '"hud_label":"Levels 1-4"', '"hud_label":"Levels 1-4 v552"'),
           ('level-name', 'Levels/level_0060.json', '"level":60', '"level":60,"tag2":"L060"'),
           ('level-name', 'Levels/L042-extra.json', None, '{"x":1}\n')]
    rows = []
    for cls, rel, find, rep in inj:
        p = os.path.join(ctl, rel)
        if find is None:
            open(p, 'w').write(rep)
        else:
            t = open(p).read()
            assert find in t, (rel, find)
            open(p, 'w').write(t.replace(find, rep, 1))
    rc, out = run(new, ['design/tools/strip_provenance.py', 'scan', ctl, '--json', os.path.join(EV, 'scan-controls.json')],
                  'scan-controls.log', ok=None)
    rep = json.load(open(os.path.join(EV, 'scan-controls.json')))
    got = [(h['cls'], h['file']) for h in rep['hits'] if h['cls'] in ('research-path', 'phone-word', 'version-tag', 'level-name')]
    for cls, rel, _, _ in inj:
        rows.append(dict(control='%s in %s' % (cls, rel), caught=(cls, rel) in got))
    json.dump(rows, open(os.path.join(EV, 'scan-controls-verdicts.json'), 'w'), indent=1)
    n = sum(r['caught'] for r in rows)
    record('scan negative controls', n == len(rows) and rc == 1, caught='%d/%d' % (n, len(rows)))


def c4b(orig, cur, new):
    tool = ['Packages/PathCore/Tests/tools/c4b_bot_replay.py']
    pinned = json.load(open(os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'Fixtures', 'c4b_bot_replay.json')))
    fx = lambda T: json.load(open(os.path.join(T, 'Packages', 'PathCore', 'Tests', 'Fixtures', 'c4b_bot_replay.json')))  # noqa
    run(orig, tool, 'c4b-orig.log')
    run(cur, tool, 'c4b-cur.log')
    run(new, tool, 'c4b-new.log')
    o, c, n = fx(orig), fx(cur), fx(new)
    strip = lambda rows: [{k: v for k, v in r.items() if k != 'slot'} for r in rows]  # noqa: E731
    record('c4b: old tool on today = the pinned fixture', o['levels'] == pinned['levels'] and o['content_sha256'] == pinned['content_sha256'])
    record('c4b: new tool on today = pinned + slot (= level)', strip(c['levels']) == pinned['levels']
           and all(r['slot'] == r['level'] for r in c['levels']))
    slots = {r['level']: r['slot'] for r in n['levels']}
    record('c4b: re-ordered: same taps + verdicts, slot follows the board', strip(n['levels']) == pinned['levels']
           and slots == {69: 59, 73: 82, 76: 73, 79: 89, 80: 71, 82: 76}, slots=slots, content_sha=n['content_sha256'][:12])


def c4ref(orig, cur, new):
    tool = ['Packages/PathCore/Tests/tools/c4_reference.py', 'negatives']
    fxp = lambda T: os.path.join(T, 'Packages', 'PathCore', 'Tests', 'Fixtures', 'c4_negative_controls.json')  # noqa
    pinned = open(os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'Fixtures', 'c4_negative_controls.json'), 'rb').read()
    run(orig, tool, 'c4ref-orig.log')
    run(cur, tool, 'c4ref-cur.log')
    _, out = run(new, tool, 'c4ref-new.log')
    record('c4_reference: old tool on today = pinned fixture (byte)', open(fxp(orig), 'rb').read() == pinned)
    record('c4_reference: new tool on today = pinned fixture (byte)', open(fxp(cur), 'rb').read() == pinned)
    n = json.load(open(fxp(new)))
    caught = sum(1 for m in n['mutations'] if m['python_errors'])
    moved = {m['mutation'].split(' ')[0]: m['levels'] for m in n['mutations'] if '[ships at' in m['mutation']}
    record('c4_reference negatives re-ordered: 20/20 caught, levels = slots', caught == 20 == len(n['mutations']),
           caught='%d/%d' % (caught, len(n['mutations'])), moved_targets=moved)


def levels_report(orig, cur, new):
    tool = ['design/tools/levels_report.py']
    run(orig, tool, 'levels_report-orig.log')
    run(cur, tool, 'levels_report-cur.log')
    a = open(os.path.join(orig, 'design', 'LEVELS.md'), 'rb').read()
    b = open(os.path.join(cur, 'design', 'LEVELS.md'), 'rb').read()
    record('levels_report: new tool on today = old tool (byte)', a == b)
    md = os.path.join(new, 'design', 'LEVELS.md')
    t = open(md).read()
    if '<!-- BEGIN:order -->' not in t:
        open(md, 'w').write(t.rstrip('\n') + '\n\n## Level order (scratch marker)\n\n<!-- BEGIN:order -->\n<!-- END:order -->\n')
    run(new, tool, 'levels_report-new.log')
    t2 = open(md).read()
    sect = t2.split('<!-- BEGIN:order -->')[1].split('<!-- END:order -->')[0]
    rows = [r for r in sect.splitlines() if r.startswith('| ') and r[2].isdigit()]
    shutil.copyfile(md, os.path.join(EV, 'LEVELS-new.md'))
    same_rest = [k for k in ('curve', 'mix', 'lengths', 'pipes') if
                 t2.split('<!-- BEGIN:%s -->' % k)[1].split('<!-- END:%s -->' % k)[0] ==
                 a.decode().split('<!-- BEGIN:%s -->' % k)[1].split('<!-- END:%s -->' % k)[0]]
    record('levels_report re-ordered: order table + origin tables unchanged', len(rows) == 67 and len(same_rest) == 4,
           order_rows=len(rows), origin_tables_identical=same_rest)


# ------------------------------------------------------------------------------------------------ slow
def cmd_slow():
    orig, cur, new = (os.path.join(SCR, n) for n in ('orig', 'cur', 'new'))
    _, out = run(new, ['design/tools/validate_levels.py', 'design/levels.json'], 'validate-new.log', ok=None)
    last = [l for l in out.splitlines() if l.startswith('validated')]
    warns = [l for l in out.splitlines() if l.startswith('WARN')]
    _, base = run(orig, ['design/tools/validate_levels.py', 'design/levels.json'], 'validate-orig.log', ok=None)
    same_first = last and last[0].split('first appearances')[1] == [l for l in base.splitlines() if l.startswith('validated')][0].split('first appearances')[1]
    record('validator: 0 errors + the same L6 warning', bool(last) and ' 0 error(s), 1 warning(s)' in last[0]
           and warns == ['WARN L6: cols 27 > 26: fit pitch below the 14.04 pt zoom floor'] and same_first,
           line=last[0] if last else None, warnings=warns)
    rc, out = run(new, ['design/tools/repeats.py', 'design/levels.json'], 'repeats-new.log', ok=None)
    record('repeats: 0 repeats, 0 near repeats', rc == 0 and '0 repeat(s), 0 near repeat(s)' in out, line=out.strip().splitlines()[-1])
    _, a = run(orig, ['design/tools/validator_selftest.py'], 'selftest-orig.log', timeout=1800)
    _, b = run(cur, ['design/tools/validator_selftest.py'], 'selftest-cur.log', timeout=1800)
    record('selftest: new tool on today = old tool (stdout byte)', a == b, last=b.strip().splitlines()[-1])
    _, c = run(new, ['design/tools/validator_selftest.py'], 'selftest-new.log', timeout=1800)
    lines = c.strip().splitlines()
    record('negative controls re-ordered 20/20 CAUGHT', lines[-1] == '20/20 caught' and sum(l.startswith('CAUGHT') for l in lines) == 20,
           last=lines[-1], ships=[l[:90] for l in lines if 'ships at' in l])
    dump('slow')


# ------------------------------------------------------------------------------------------------ samples
def cmd_samples():
    orig, cur, new = (os.path.join(SCR, n) for n in ('orig', 'cur', 'new'))
    out = os.path.join(SCR, 'samples')
    os.makedirs(out, exist_ok=True)

    def rep(p):
        return json.load(open(p))['table'][0]
    # render: v552 L69 (pipes under doors) ships at L59; v552 L80 (corners) ships at L71. (No video board: every
    # research/video-frames capture is absent from disk today — VERIFIED — so no video overlay runs with either tool.)
    for board, old_l, new_l in (('v552 L69', 69, 59), ('v552 L80', 80, 71)):
        run(orig, ['tools/levels/render.py', '--levels', str(old_l), '--out', os.path.join(out, 'render-orig-%d' % old_l)],
            'render-orig-%d.log' % old_l, ok=None)
        run(new, ['tools/levels/render.py', '--levels', str(new_l), '--out', os.path.join(out, 'render-new-%d' % new_l)],
            'render-new-%d.log' % new_l, ok=None)
        a = rep(os.path.join(out, 'render-orig-%d' % old_l, 'report-partial.json'))
        b = rep(os.path.join(out, 'render-new-%d' % new_l, 'report-partial.json'))
        keys = ('iou', 'tol1', 'capture', 'registration', 'pass')
        record('render %s: L%d (today) == L%d (re-ordered, stripped)' % (board, old_l, new_l),
               all(a[k] == b[k] for k in keys) and b.get('board') == board, tol1=(a['tol1'], b['tol1']))
    # reveals: v552 L47 (door + tape) ships at L37
    run(orig, ['design/tools/overlay_recast.py', '--reveals', '--levels', '47', '--out', os.path.join(out, 'rev-orig')],
        'reveals-orig-47.log', ok=None)
    run(new, ['design/tools/overlay_recast.py', '--reveals', '--levels', '37', '--out', os.path.join(out, 'rev-new')],
        'reveals-new-37.log', ok=None)
    a = json.load(open(os.path.join(out, 'rev-orig', 'reveals-report-partial.json')))
    b = json.load(open(os.path.join(out, 'rev-new', 'reveals-report-partial.json')))
    record('reveals v552 L47: L47 (today) == L37 (re-ordered)', [(r['door'], r['tol1']) for r in a['table']] ==
           [(r['door'], r['tol1']) for r in b['table']] and a['doors'] > 0, doors=a['doors'], tol1=[r['tol1'] for r in b['table']])
    # elevator: v552 L102 ships at L97
    run(orig, ['design/tools/overlay_recast.py', '--elevators', '--levels', '102', '--out', os.path.join(out, 'el-orig')],
        'elev-orig-102.log', ok=None)
    run(new, ['design/tools/overlay_recast.py', '--elevators', '--levels', '97', '--out', os.path.join(out, 'el-new')],
        'elev-new-97.log', ok=None)
    a = json.load(open(os.path.join(out, 'el-orig', 'elevators-report.json')))
    b = json.load(open(os.path.join(out, 'el-new', 'elevators-report.json')))
    record('elevator v552 L102: L102 (today) == L97 (re-ordered)', a['elevators'] > 0 and
           [(r['elevator'], r['tol1']) for r in a['table']] == [(r['elevator'], r['tol1']) for r in b['table']],
           tol1=[r['tol1'] for r in b['table']])
    # the real tree as it stands until B0: T8's overlay_recast.py + level_order.py with TODAY's render.py (not the staged one)
    mix = os.path.join(SCR, 'mix')
    if os.path.exists(mix):
        shutil.rmtree(mix)
    shutil.copytree(orig, mix, symlinks=True)
    for rel in ('design/tools/level_order.py', 'design/tools/overlay_recast.py'):
        shutil.copyfile(os.path.join(APP, rel), os.path.join(mix, rel))
    run(mix, ['design/tools/overlay_recast.py', '--elevators', '--levels', '102', '--out', os.path.join(out, 'el-mix')],
        'elev-mix-102.log', ok=None)
    c = json.load(open(os.path.join(out, 'el-mix', 'elevators-report.json')))
    run(orig, ['design/tools/overlay_recast.py', '--levels', '62', '--out', os.path.join(out, 'ov-orig-62')], 'overlay-orig-62.log', ok=None)
    run(mix, ['design/tools/overlay_recast.py', '--levels', '62', '--out', os.path.join(out, 'ov-mix-62')], 'overlay-mix-62.log', ok=None)
    d1 = rep(os.path.join(out, 'ov-orig-62', 'report-partial.json'))
    d2 = rep(os.path.join(out, 'ov-mix-62', 'report-partial.json'))
    # every bundled board today: the new research-file lookup == overlay_recast's old slot map (V2 boards included)
    sys.path.insert(0, os.path.join(mix, 'design', 'tools'))
    import level_order as LO
    old_map = {35: 32, 45: 33, 51: 34, 52: 35, 72: 36, 75: 38, 77: 37}
    Ld = os.path.join(orig, 'App', 'Resources', 'Levels')
    diff = []
    for name in sorted(os.listdir(Ld)):
        if not name.startswith('level_'):
            continue
        b = json.load(open(os.path.join(Ld, name)))
        if b['source'] not in ('recorded', 'video'):
            continue
        old = os.path.join('research', 'levels', 'video', 'V2-L%03d.json' % old_map[b['level']]) if b['level'] in old_map \
            else os.path.join('research', 'levels', 'L%03d.json' % b['level'])
        now = os.path.relpath(LO.research_json(LO.with_provenance(b, os.path.join(orig, 'design', 'levels.json'))), mix)
        if old != now:
            diff.append((b['level'], old, now))
    record('in-place overlay_recast + today\'s render.py = before (L102 elevator, L62 overlay, every research file)',
           [(r['elevator'], r['tol1']) for r in a['table']] == [(r['elevator'], r['tol1']) for r in c['table']]
           and all(d1[k] == d2[k] for k in ('iou', 'tol1', 'capture', 'registration', 'pass')) and not diff,
           tol1_62=(d1['tol1'], d2['tol1']), lookup_diffs=diff[:5])
    # video replay: V2-L035 (today L52 -> L46)
    run(orig, ['tools/levels/replay_bundle.py', '--levels', '52', '--out', os.path.join(out, 'rp-orig')], 'replay-orig-52.log', ok=None)
    run(new, ['tools/levels/replay_bundle.py', '--levels', '46', '--out', os.path.join(out, 'rp-new')], 'replay-new-46.log', ok=None)
    a = json.load(open(os.path.join(out, 'rp-orig', 'summary.json')))
    b = json.load(open(os.path.join(out, 'rp-new', 'summary.json')))
    ka = [(r['video'], r['video_level'], r['taps'], r['consistent'], r['inconsistent']) for r in a['table']]
    kb = [(r['video'], r['video_level'], r['taps'], r['consistent'], r['inconsistent']) for r in b['table']]
    record('replay V2-L035: L52 (today) == L46 (re-ordered)', ka == kb and len(ka) > 0, today=ka, reordered=kb)
    dump('samples')


def dump(stage):
    p = os.path.join(EV, 'results-%s.json' % stage)
    json.dump(RESULTS, open(p, 'w'), indent=1)
    n = sum(r['passed'] for r in RESULTS.values())
    print('%s: %d/%d checks pass -> %s' % (stage, n, len(RESULTS), os.path.relpath(p, APP)))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    os.makedirs(EV, exist_ok=True)
    {'setup': cmd_setup, 'fast': cmd_fast, 'slow': cmd_slow, 'samples': cmd_samples}.get(cmd, lambda: print(__doc__))()
