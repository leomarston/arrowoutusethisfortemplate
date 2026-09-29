#!/usr/bin/env python3
"""build_levels.py — assembles design/levels.json (SPEC-gameplay §14, design/LEVELS.md).

Steps (each can run alone; artefacts in design/tools/work/):
  curve     fit the generator curve to the recorded levels (work/imported.json) -> work/curve.json
  designed  run gen_levels for L106..L150 + the stand-ins of repeated slots      -> work/designed.json, substitutes.json
  assemble  L1..L105 (imported in our order, repeats -> V2 boards / stand-ins, unlock cards) + L106..L150 (designed) +
            sessions, unlocks, tutorials, curve -> design/levels.json, then the validator (validate_levels.py) must pass.

  python3 design/tools/build_levels.py curve
  python3 design/tools/build_levels.py designed [--from 62 --to 150]
  python3 design/tools/build_levels.py assemble
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import arrowcore as ac  # noqa: E402
from pathrandom import fnv1a64  # noqa: E402

WORK = os.path.join(HERE, 'work')
LEVELS_JSON = os.path.join(DESIGN, 'levels.json')
AUTHORED_END = 150
SALT = fnv1a64('arrow-out/levels/v1')            # = curve.salt; changing it changes every designed/endless board

# SPEC.md §5 item 19 (orchestrator ruling 08:35 on research/video-levels.md): v552 moved four of the video build's boards
# to later numbers (phone L35 = video L21, L45 = L26, L51 = L12, L52 = L14, cell for cell). The video keeps its slots
# (L1-L31 in video order); the four PHONE slots take, in order, the video build's authored boards v552 does not have
# (research/levels/video/V2-L032..L035), keeping the slot's v552 timer and tag. The spares V2-L036..L038 open the
# designed range at L62-L64 (V2-L037, the biggest, takes the Hard slot L64: DECISION, LEVELS.md §2.4).
SUBSTITUTES = {35: ('V2-L032', 21), 45: ('V2-L033', 26), 51: ('V2-L034', 12), 52: ('V2-L035', 14)}
RECORDED_END = 105                  # phone sessions 1 + 2 + 3 recorded v552 L32-L105 (research/levels)
# Phone session 2 (research/levels.md): v552 REPEATS five boards 20 levels later, cell for cell and head for head
# (build/recast/duplicates.txt): L72 = L52 (= video L14), L75 = L55, L77 = L57, L81 = L61, L83 = L63. SPEC.md §5 item 19's rule
# for duplicates applies (the phone slot is substituted, keeping its v552 timer and tag): the older build's unused authored
# boards first, IN ORDER OF THE SLOTS, matched by kind (V2-L036 plain -> L72, plain; V2-L038 pipes -> L75; V2-L037 boxes ->
# L77, whose repeat had boxes), then generated boards built to the repeated board's own size / units / waves / free arrows /
# timer / obstacle kinds (gen_levels.generate with a target override) for the slots left (L81, L83). DECISION (recast
# 2026-09-25): the spares go to the duplicate slots rather than after L83 (the brief's placement) because ORCH 19 rules
# duplicates exactly this way and the slots after L83 will be re-recorded (phone session 3). SPEC.md §5 item 26 accepted it.
# CONTENT RECAST 2 (phone session 3, v552 L84-L105) + the orchestrator's DEDUP RULE (SPEC.md §5 item 28): no board may appear
# twice in L1-L150; the FIRST occurrence in OUR order wins; every later duplicate slot gets a GENERATED stand-in built to the
# repeated board's size, units, waves, free arrows, timer, tag and obstacle kinds. plan_slots() finds the repeats in our order
# (repeats.py: offset-free, rotations and mirrors included, visible or full layer) and stops when they are not these:
#   ORCH 19 (video/phone): 35 = 21, 45 = 26, 51 = 12, 52 = 14            -> V2-L032..V2-L035 (SUBSTITUTES)
#   ORCH 26 (v552 repeats itself): 72 = 14, 75 = 55, 77 = 57            -> spares V2-L036 / V2-L038 / V2-L037 (SPARE_SLOTS)
#                                  81 = 61, 83 = 63                      -> generated stand-ins
#   recast 2 (session 3): 86 = 66, 100 = 31 (V2-L031 = the video L31), 101 = 35 (V2-L032, shipped at L35 by ORCH 19),
#                         103 = 45 (V2-L033, shipped at L45)             -> generated stand-ins
EXPECTED_REPEATS = {35: 21, 45: 26, 51: 12, 52: 14, 72: 14, 75: 55, 77: 57, 81: 61, 83: 63, 86: 66, 100: 31, 101: 35, 103: 45}
DUPLICATES = {n: d for n, d in EXPECTED_REPEATS.items() if n not in SUBSTITUTES}   # the phone's self-repeats (stand-in slots)
SPARE_SLOTS = {72: 'V2-L036', 75: 'V2-L038', 77: 'V2-L037'}     # ORCH 26 (accepted; "not after L83")

# First appearance of each obstacle in OUR level list -> the unlock card (tutorials.md §6; v552 texts; door = ours).
FEATURES = {
    'tape': dict(feature='linked', title='Linked Arrows!', card='LINKED ARROWS move together!', caps='LINKED ARROWS',
                 icon='unlockIconLinked'),
    'box': dict(feature='box', title='Box!', card='Clear required amount of arrows to break the BOX!', caps='BOX',
                icon='unlockIconBox'),
    'pipe': dict(feature='pipe', title='Pipe!', card='Pass arrows through the PIPE to break it!', caps='PIPE',
                 icon='unlockIconPipe'),
    'elevator': dict(feature='elevator', title='Elevator!', card='Clear all arrows on the ELEVATOR to activate it!',
                     caps='ELEVATOR', icon='unlockIconElevator'),
    'door': dict(feature='door', title='Door!', card='Collect the KEY to open the DOOR!', caps='DOOR',
                 icon='unlockIconDoor'),                       # SPEC.md §5 item 19 (our wording; v552 showed no card)
    'corner': dict(feature='corner', title='Corner!', card='Arrows turn when they hit the CORNER!', caps='CORNER',
                   icon='unlockIconCorner'),
}
FEATURE_KINDS = ('tape', 'box', 'pipe', 'elevator', 'door', 'corner')   # a key belongs to its door


def recorded_lengths(levels):
    h = {}
    for l in levels:
        if l['level'] < 32 or l['level'] > RECORDED_END or l['source'] != 'recorded':
            continue
        for a in l['arrows']:
            n = len(a['cells'])
            h[n] = h.get(n, 0) + 1
    return {str(k): v for k, v in sorted(h.items())}


FIT_FROM = 40                       # the obstacle mix is fitted on v552 L40-L105 (past the unlock run of L32-L39)
TEMPLATE_DECADES = [3, 4, 5, 6, 7, 8, 9]   # templates = the recorded L30-L99 (slot k = decade 3 + k; L30/L31 = the videos;
                                           # recast 2: + L80-L99 from phone sessions 2/3; L100-L105 is a partial decade)
GROWTH_FROM = 100                   # growth starts after the last template decade (was 80 with templates L30-L79)
FIRST_LEVEL = dict(tape=7, box=11, pipe=21, elevator=31, door=33, corner=70)   # first appearance in OUR order


def level_kinds(l):
    return {('box' if o['kind'] == 'curtain' else o['kind']) for o in l['obstacles'] if o['kind'] in FEATURE_KINDS}


def fit_obstacles(imported):
    """Obstacle mix of the recorded phone boards: each kind's share of the levels since its unlock in our order (window
    L40-L105, from its first level on) and the number of kinds per level. Recast 2: the elevator is fitted like the others
    now that v552 shows it (L100-L103; it was held at 6 % while it was video-only; the fit gives 6 % again)."""
    rec = [l for l in imported if FIT_FROM <= l['level'] <= RECORDED_END and l['source'] == 'recorded']
    weights = {}
    for k in ('door', 'pipe', 'box', 'tape', 'corner', 'elevator'):
        win = [l for l in rec if l['level'] >= FIRST_LEVEL[k]]
        weights[k] = int(round(100.0 * sum(1 for l in win if k in level_kinds(l)) / len(win)))
    counts = [0, 0, 0]
    for l in rec:
        counts[min(2, len(level_kinds(l)))] += 1
    return dict(firstLevel=dict(FIRST_LEVEL), kindOrder=['door', 'pipe', 'box', 'tape', 'elevator', 'corner'],
                kindWeights=weights, countWeights=[int(round(100.0 * c / len(rec))) for c in counts])


def fit_timers(imported):
    rec = [l for l in imported if 32 <= l['level'] <= RECORDED_END and l['source'] == 'recorded']

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2]
    normals = [l['timer_s'] for l in rec if l['tag'] == 'normal']
    return dict(fromTemplate=True,       # every designed level takes its template's v552 timer (1:40 ... 3:30)
                hard=med([l['timer_s'] for l in rec if l['tag'] == 'hard']),
                superHard=med([l['timer_s'] for l in rec if l['tag'] == 'superHard']),
                normal=180, short=150, pShort=round(sum(1 for t in normals if t == 150) / float(len(normals)), 2),
                maxWorkShareShort=0.40)


def make_curve(imported):
    by = {l['level']: l for l in imported}
    templates = []
    for slot, dec in enumerate(TEMPLATE_DECADES):
        for p in range(10):
            n = 10 * dec + p
            l = by[n]
            m = ac.metrics(l)
            templates.append(dict(slot=slot, pos=p, level=n, cols=l['cols'], rows=l['rows'], units=m['_units'],
                                  rounds=m['rounds'], free=m['free_at_start'], timer=l['timer_s'], tag=l['tag']))
    return dict(
        schema=1,
        _about='Generator curve (SPEC-gameplay §14.3). Fitted to L30-L105 by design/tools/build_levels.py '
               '(templates L30-L99 in 7 decade slots; timers from the templates; obstacle mix of L40-L105 incl. '
               'corners and elevators; growth from L100); the designed L106-L150 and every endless level past the '
               'authored end come from it (gen_levels.py = the reference algorithm C4 ports).',
        salt=SALT,
        authoredEnd=AUTHORED_END,
        cycle=10,
        slots=len(TEMPLATE_DECADES),
        tagByPosition={'4': 'hard', '9': 'superHard'},
        templates=templates,
        growth=dict(**{'from': GROWTH_FROM}, perDecade=0.02, cap=1.25),
        maxCols=26, maxRows=36,
        timers=fit_timers(imported),
        lengths=recorded_lengths(imported),
        straight=0.82,
        maxLength=60,
        mergeFactor=80,
        flipSteps=3000,
        silhouette=dict(p=0.25, shapes=['oval', 'octagon', 'notch', 'blocks', 'cross', 'heart', 'diamond', 'arch']),
        obstacles=fit_obstacles(imported),
        attempts=10,
        goodEnough=0.25,
    )


def cmd_curve():
    imported = json.load(open(os.path.join(WORK, 'imported.json')))
    curve = make_curve(imported)
    ac.dump(curve, os.path.join(WORK, 'curve.json'))
    print('curve: %d templates, salt %s' % (len(curve['templates']), curve['salt']))


def feature_first_levels(levels):
    first = {}
    for l in levels:
        for o in l['obstacles']:
            k = o['kind']
            if k in FEATURE_KINDS and k not in first:
                first[k] = l['level']
    return first


SESSIONS = [dict(id='L1-4', levels=[1, 2, 3, 4], hud_label='Levels 1-4', panel_label='Level 1-4', reward=80,
                 stage_gap_s=0.7, hearts='carry')]
TUTORIALS = [dict(id='tapToMove', level=1, stage=0, trigger='stageReady', caption='Tap to move!',
                  hand=dict(arrow=1, at=[0.89, 1.06]), dismiss='anyTap', holdTimer=False)]


def plan_slots(imported, extra):
    """OUR order L1..RECORDED_END with every repeat resolved (SPEC.md §5 items 19, 26, 28). Slot by slot, the research board
    of the slot (the video for L1-L31, v552 after) is placed unless it repeats a board ALREADY PLACED (repeats.py: offset-free,
    rotations and mirrors, the start-visible arrows or every layer); a repeating slot takes its V2 substitute (ORCH 19), its
    spare (ORCH 26) or a generated stand-in (None here; cmd_designed makes it). Returns (placed {n: level or None},
    repeats {n: (first level, key, symmetry)})."""
    import repeats as rp
    placed, keys, reps = {}, {}, {}
    for n in range(1, RECORDED_END + 1):
        raw = imported[n]
        k = rp.keys(raw)
        hit = next((m for m in sorted(keys) if rp.relation(keys[m], k)[0] == 'repeat'), None)
        if hit is None:
            placed[n], keys[n] = raw, k
            continue
        which = rp.relation(keys[hit], k)[1]
        reps[n] = (hit, which, rp.sym_between(placed[hit], raw, which))
        name = SUBSTITUTES[n][0] if n in SUBSTITUTES else SPARE_SLOTS.get(n)
        if name:
            l = json.loads(json.dumps(extra[name]))
            l['level'] = n
            l['timer_s'] = raw['timer_s']
            l['tag'] = raw['tag']
            placed[n], keys[n] = l, rp.keys(l)
        else:
            placed[n] = None
    return placed, reps


def research_order():
    """repeats.py --order: our order before the stand-ins (a stand-in slot keeps its raw phone board, to be seen repeating)."""
    imported = {l['level']: l for l in json.load(open(os.path.join(WORK, 'imported.json')))}
    extra = json.load(open(os.path.join(WORK, 'imported_extra.json')))
    placed, _ = plan_slots(imported, extra)
    out = []
    for n in range(1, RECORDED_END + 1):
        l = placed[n] or imported[n]
        l = dict(l, _board=('%s at' % SUBSTITUTES[n][0] if n in SUBSTITUTES else '%s at' % SPARE_SLOTS[n]
                            if n in SPARE_SLOTS else 'raw') + ' ' + l['source'])
        out.append(l)
    return out


def substitute_target(n, phone):
    """gen_levels target for a generated stand-in: the repeated board's own size, units, waves, free (the phone slot's own
    read of it, = the first occurrence cell for cell), and the slot's v552 timer and tag."""
    m = ac.metrics(phone)
    return dict(n=n, pos=n % 10, tag=phone['tag'], template=n, units=m['_units'], rounds=m['rounds'],
                free=m['free_at_start'], cols=phone['cols'], rows=phone['rows'], template_timer=phone['timer_s'])


def substitute_kinds(phone):
    order = ['door', 'elevator', 'box', 'pipe', 'tape', 'corner']
    return sorted(level_kinds(phone), key=order.index)


def cmd_assemble():
    imported = {l['level']: l for l in json.load(open(os.path.join(WORK, 'imported.json')))}
    extra = json.load(open(os.path.join(WORK, 'imported_extra.json')))
    designed = json.load(open(os.path.join(WORK, 'designed.json')))['levels']
    subs = {l['level']: l for l in json.load(open(os.path.join(WORK, 'substitutes.json')))['levels']}
    curve = json.load(open(os.path.join(WORK, 'curve.json')))
    placed, reps = plan_slots(imported, extra)
    found = {n: r[0] for n, r in reps.items()}
    if found != EXPECTED_REPEATS:
        raise SystemExit('repeats in our order changed: found %s, expected %s' % (found, EXPECTED_REPEATS))
    levels = []
    for n in range(1, RECORDED_END + 1):
        phone = imported[n]
        first, which, sym = reps.get(n, (None, None, None))
        how = '' if sym in (None, 'identical') else ' (%s)' % sym
        if n in SUBSTITUTES:
            name, dup = SUBSTITUTES[n]
            l = placed[n]
            l['_from'] = ('%s (the video build\'s L%s) substitutes a duplicate of L%03d: the phone\'s L%d (%s) is the '
                          'same board as video L%d, which ships at L%d' % (name, name[-2:], dup, n, phone['capture'],
                                                                          dup, dup))
        elif n in SPARE_SLOTS:
            spare = SPARE_SLOTS[n]
            l = placed[n]
            l['_from'] = ('%s (the video build\'s L%s, not in v552) substitutes a duplicate of L%03d: the phone\'s '
                          'L%d (%s) repeats its L%d cell for cell' % (spare, spare[-2:], DUPLICATES[n], n,
                                                                     phone['capture'], DUPLICATES[n]))
        elif n in reps:
            l = json.loads(json.dumps(subs[n]))
            is_v2 = phone.get('_is')
            l['_from'] = ('designed stand-in for a repeat of L%03d: the phone\'s L%d (%s)%s repeats L%d%s (the first '
                          'occurrence in our order); generated to that board\'s size, units, waves, free arrows, timer, '
                          'tag and obstacle kinds' % (first, n, phone['capture'],
                                                      ' = the older build\'s %s' % is_v2 if is_v2 else '', first, how))
        else:
            l = json.loads(json.dumps(placed[n]))
            l.pop('_is', None)
        levels.append(l)
    nxt = RECORDED_END + 1
    for l in designed:
        if nxt <= l['level'] <= AUTHORED_END:
            levels.append(l)
    levels.sort(key=lambda l: l['level'])
    first = feature_first_levels(levels)
    unlocks = []
    for kind, n in sorted(first.items(), key=lambda x: x[1]):
        card = dict(FEATURES[kind])
        card['level'] = n
        unlocks.append(dict(feature=card['feature'], level=n, title=card['title'], card=card['card'],
                            caps=card['caps'], icon=card['icon']))
        levels[n - 1]['unlock'] = card['feature']
    for l in levels:
        m = ac.metrics(l)
        l['metrics'] = ac.bundle_metrics(m)
        l['schema'] = 1
    doc = dict(schema=1,
               _about=('Arrow Out level content (SPEC-gameplay §14, design/LEVELS.md). Built by design/tools/build_levels.py '
                       'from research/levels (L1-31 video, L32-105 phone v552 + the door and elevator reveals; a slot '
                       'whose board repeats an earlier one holds a V2 board or a generated stand-in) and gen_levels.py '
                       '(L106-150). CONTENT runs `pclevels bundle design/levels.json App/Resources/Levels` to write '
                       'level_NNNN.json, sessions.json, unlocks.json, tutorials.json and curve.json. Keys starting with '
                       '"_" are comments.'),
               authoredEnd=AUTHORED_END,
               sessions=SESSIONS, unlocks=unlocks, tutorials=TUTORIALS, curve=curve,
               levels=levels)
    # PUBLISH item 12 (SPEC.md rulings 37e/39): the level order of design/level-order.json, when one is planned. No plan ->
    # the research order above, byte for byte; a plan made on other content -> refused before anything is written.
    import reorder_levels
    doc = reorder_levels.apply_planned(doc)
    write_doc(doc, LEVELS_JSON)
    print('design/levels.json: %d levels, unlocks %s' % (len(levels), [(u['feature'], u['level']) for u in unlocks]))


def doc_text(doc):
    """Readable top, one compact line per level (diff-friendly, ~2 MB). The exact text write_doc writes."""
    head = {k: v for k, v in doc.items() if k != 'levels'}
    out = ['{\n']
    for k in sorted(head):
        out.append('  %s: %s,\n' % (json.dumps(k), json.dumps(head[k], sort_keys=True, separators=(',', ':'))))
    out.append('  "levels": [\n')
    for i, l in enumerate(doc['levels']):
        out.append('    ' + json.dumps(l, sort_keys=True, separators=(',', ':')) + (',' if i < len(doc['levels']) - 1
                                                                                    else '') + '\n')
    out.append('  ]\n}\n')
    return ''.join(out)


def write_doc(doc, path):
    """Readable top, one compact line per level (diff-friendly, ~2 MB)."""
    with open(path, 'w') as f:
        f.write(doc_text(doc))


def cmd_designed(a=RECORDED_END + 1, b=AUTHORED_END):
    """The designed levels (the reference algorithm, what C4's Generator reproduces byte for byte) -> work/designed.json,
    and the generated substitutes of repeated phone boards (target overrides; not reproducible from the level number
    alone, so kept apart) -> work/substitutes.json."""
    import gen_levels
    import validate_levels
    curve = json.load(open(os.path.join(WORK, 'curve.json')))

    def gate(lvl):
        errs, warns = [], []
        validate_levels.check_level(dict(lvl, source='generated', schema=1), errs, warns)
        return errs[0].split(': ', 1)[1] if errs else None
    out, infos = [], []
    for n in range(a, b + 1):
        lvl, info = gen_levels.generate(curve, n, gate=gate)
        out.append(lvl)
        infos.append(info)
        print('designed L%d %s %s' % (n, lvl['tag'], '+'.join(info['kinds']) or '-'), flush=True)
    ac.dump(dict(levels=out, infos=infos), os.path.join(WORK, 'designed.json'))
    imported = {l['level']: l for l in json.load(open(os.path.join(WORK, 'imported.json')))}
    sout, sinfos = [], []
    for n in sorted(DUPLICATES):
        if n in SPARE_SLOTS:
            continue
        lvl, info = gen_levels.generate(curve, n, target=substitute_target(n, imported[n]),
                                        kinds=substitute_kinds(imported[n]), gate=gate)
        sout.append(lvl)
        sinfos.append(info)
        print('substitute L%d %s' % (n, '+'.join(info['kinds'])), flush=True)
    ac.dump(dict(levels=sout, infos=sinfos), os.path.join(WORK, 'substitutes.json'))
    print('designed L%d-L%d + substitutes %s' % (a, b, [l['level'] for l in sout]))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'assemble'
    if cmd == 'curve':
        cmd_curve()
    elif cmd == 'designed':
        cmd_designed()
    elif cmd == 'assemble':
        cmd_assemble()
    else:
        raise SystemExit('unknown step %s' % cmd)
