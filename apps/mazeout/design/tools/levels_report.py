#!/usr/bin/env python3
"""levels_report.py — regenerates the generated sections of design/LEVELS.md from design/levels.json.

Sections between `<!-- BEGIN:name -->` and `<!-- END:name -->` are replaced; everything else in LEVELS.md is prose.
  python3 design/tools/levels_report.py
Since the level re-order (PUBLISH item 12): the range tables group boards by ORIGIN (their research slot, level_order.py:
v552's number for a phone board), so "phone L32-61" still means those boards wherever they ship; the level table names a
moved board's research number; the `order` section (when LEVELS.md has its markers) lists every re-ordered slot.
"""
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import arrowcore as ac  # noqa: E402
import level_order as LO  # noqa: E402


def rs(l):
    """The board's research slot (= its level before the re-order; generated boards keep their level)."""
    r = LO.rslot(l)
    return l['level'] if r is None else r


def obst_text(l):
    parts = []
    kinds = {}
    for o in l['obstacles']:
        kinds.setdefault(o['kind'], []).append(o)
    if 'tape' in kinds:
        parts.append('tape %s' % '+'.join(str(len(o['arrows'])) for o in kinds['tape']))
    if 'door' in kinds:
        parts.append('door x%d (keys %d)' % (len(kinds['door']), len(kinds.get('key', []))))
    if 'pipe' in kinds:
        doors = [{tuple(c) for c in o['cells']} for o in kinds.get('door', [])]
        under = sum(1 for o in kinds['pipe'] if any({tuple(c) for c in o['cells']} <= d for d in doors))
        parts.append('pipe %s%s' % ('/'.join(str(o['counter']) for o in kinds['pipe']),
                                    ' (%d under doors)' % under if under else ''))
    if 'box' in kinds:
        parts.append('box %s' % '/'.join(str(o['counter']) for o in kinds['box']))
    if 'elevator' in kinds:
        parts.append('elevator x%d (+%d hidden)' % (len(kinds['elevator']), sum(len(o.get('reveals', []))
                                                                               for o in kinds['elevator'])))
    if 'corner' in kinds:
        parts.append('corner x%d' % len(kinds['corner']))
    return ', '.join(parts) or '-'


def origin(l):
    moved = rs(l) != l['level']
    return _origin(l) + ((' L%d' % rs(l)) if moved and l['source'] == 'recorded' else
                         (' for phone L%d' % rs(l)) if moved else '')


def _origin(l):
    src = l['source']
    if l.get('_from', '').startswith(('designed substitute', 'designed stand-in')):
        m = re.search(r'repeat of L0*(\d+)', l['_from'])
        return 'designed (stand-in for a repeat of L%s)' % m.group(1) if m else 'designed (stand-in)'
    if l.get('_from'):
        f = l['_from']
        m = re.match(r'(V2-L0\d\d)', f)
        return '%s (%s)' % (m.group(1) if m else 'video', 'substitute' if 'substitutes' in f else 'spare')
    if src == 'video':
        cap = l.get('capture') or ''
        return 'video %s' % ('V1' if '/V1/' in cap else 'V2')
    if src == 'recorded':
        return 'phone v552'
    return 'designed'


def level_table(doc):
    rows = ['| L | origin | tag | timer | grid | arrows (+hidden) | units | obstacles (counters) | unlock | waves | free | bot s left |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for l in doc['levels']:
        m = ac.metrics(l)
        hidden = sum(1 for a in l['arrows'] if a.get('hidden_by'))
        t = l['timer_s']
        rows.append('| %d | %s | %s | %d:%02d | %dx%d | %d%s | %d | %s | %s | %d | %d | %.0f |' % (
            l['level'], origin(l), {'normal': '-', 'hard': 'Hard', 'superHard': 'Super Hard'}[l['tag']], t // 60, t % 60,
            l['cols'], l['rows'], m['arrows'] - hidden, (' (+%d)' % hidden) if hidden else '', m['_units'], obst_text(l),
            l.get('unlock') or '', m['rounds'], m['free_at_start'], m['bot_time_left']))
    return '\n'.join(rows)


def band(vals):
    if not vals:
        return '-'
    q = sorted(vals)
    return '%s-%s (median %s)' % (q[0], q[-1], q[len(q) // 2])


def curve_table(doc):
    groups = [('video L1-31', lambda l: 1 <= rs(l) <= 31),
              ('phone+substitutes L32-61', lambda l: 32 <= rs(l) <= 61),
              ('phone+substitutes L62-83', lambda l: 62 <= rs(l) <= 83),
              ('phone+stand-ins L84-105', lambda l: 84 <= rs(l) <= 105),
              ('designed L106-150', lambda l: 106 <= rs(l) <= 150)]
    rows = ['| range | tag | levels | units | waves | free at start | arrows | mean length | grid cols | grid rows | timers |',
            '|---|---|---|---|---|---|---|---|---|---|---|']
    for name, pred in groups:
        for tag in ('normal', 'hard', 'superHard'):
            ls = [l for l in doc['levels'] if pred(l) and l['tag'] == tag]
            if not ls:
                continue
            ms = [ac.metrics(l) for l in ls]
            tm = {}
            for l in ls:
                tm[l['timer_s']] = tm.get(l['timer_s'], 0) + 1
            rows.append('| %s | %s | %d | %s | %s | %s | %s | %.1f | %s | %s | %s |' % (
                name, tag, len(ls), band([m['_units'] for m in ms]), band([m['rounds'] for m in ms]),
                band([m['free_at_start'] for m in ms]), band([m['arrows'] for m in ms]),
                statistics.mean(m['mean_length'] for m in ms), band([l['cols'] for l in ls]),
                band([l['rows'] for l in ls]),
                ', '.join('%d:%02d x%d' % (k // 60, k % 60, v) for k, v in sorted(tm.items(), reverse=True))))
    return '\n'.join(rows)


def obstacle_mix(doc):
    rows = ['| range | levels | none | tape | door | pipe | box | elevator | corner | two kinds |',
            '|---|---|---|---|---|---|---|---|---|---|']
    for name, a, b in (('video L1-31', 1, 31), ('L32-61 (as shipped)', 32, 61), ('L62-83 (as shipped)', 62, 83),
                       ('L84-105 (as shipped)', 84, 105), ('L70-105 (as shipped, corners unlocked)', 70, 105),
                       ('designed L106-150', 106, 150)):
        ls = [l for l in doc['levels'] if a <= rs(l) <= b]
        cnt = dict(none=0, tape=0, door=0, pipe=0, box=0, elevator=0, corner=0, two=0)
        for l in ls:
            ks = {o['kind'] for o in l['obstacles']} - {'key'}
            if not ks:
                cnt['none'] += 1
            for k in ks:
                cnt[k] = cnt.get(k, 0) + 1
            if len(ks) >= 2:
                cnt['two'] += 1
        n = len(ls)
        rows.append('| %s | %d | %s |' % (name, n, ' | '.join('%d (%d %%)' % (cnt[k], round(100.0 * cnt[k] / n))
                                                               for k in ('none', 'tape', 'door', 'pipe', 'box', 'elevator',
                                                                         'corner', 'two'))))
    return '\n'.join(rows)


def length_table(doc):
    rows = ['| range | arrows | mean | p10 | p25 | p50 | p75 | p90 | p99 | max | turns per interior cell |',
            '|---|---|---|---|---|---|---|---|---|---|---|']
    for name, a, b in (('phone L32-105 (recorded only)', 32, 105), ('designed L106-150', 106, 150)):
        lens, turns, inner = [], 0, 0
        for l in doc['levels']:
            if not (a <= rs(l) <= b) or (name.startswith('phone') and l['source'] != 'recorded'):
                continue
            for x in l['arrows']:
                cs = [tuple(c) for c in x['cells']]
                lens.append(len(cs))
                for i in range(1, len(cs) - 1):
                    inner += 1
                    turns += ac.dir_between(cs[i - 1], cs[i]) != ac.dir_between(cs[i], cs[i + 1])
        q = sorted(lens)
        p = lambda f: q[min(len(q) - 1, int(len(q) * f))]   # noqa: E731
        rows.append('| %s | %d | %.1f | %d | %d | %d | %d | %d | %d | %d | %.2f |' % (
            name, len(q), statistics.mean(q), p(0.1), p(0.25), p(0.5), p(0.75), p(0.9), p(0.99), q[-1], turns / inner))
    return '\n'.join(rows)


def ships(doc, n):
    """' (ships at Lk)' for a research level n that ships elsewhere; '' otherwise (and without a doc)."""
    if doc is None:
        return ''
    k = LO.slot_map(doc['levels']).get(n, n)
    return '' if k == n else ' (ships at L%d)' % k


def reveal_table(doc=None):
    rows = ['| L | round shots (clean reads) | start arrows | hidden arrows | doors (opening order: rect c0,r0-c1,r1) | keys (start + hidden) | tapes under doors | bot-log check |',
            '|---|---|---|---|---|---|---|---|']
    for p in sorted(os.listdir(os.path.join(HERE, 'work', 'reveals'))):
        r = json.load(open(os.path.join(HERE, 'work', 'reveals', p)))
        if r.get('kind') == 'elevator':
            continue
        doors = '; '.join('%d,%d-%d,%d' % tuple(d['rect']) for d in r['doors'])
        ks = [k for k in r['keys'] if k['rider'] is not None and k['cells']]
        if 'log' in r:
            check = '%d/%d taps matched; never tapped: %s' % (r['log']['matched'], r['log']['tapped_units'],
                                                             ', '.join(map(str, r['log']['never_tapped'])) or 'none')
        else:
            check = 'session %d: replay_log.py (every logged tap exits)' % r.get('session', 2)
        rows.append('| %d%s | %d (%d) | %d | %d | %s | %d + %d | %d | %s |' % (
            r['level'], ships(doc, r['level']), r['shots'], r['clean_reads'], r['start_arrows'], len(r['hidden']), doors,
            sum(1 for k in ks if k['start']), sum(1 for k in ks if not k['start']), len(r['tapes']), check))
    return '\n'.join(rows)


def elevator_table(doc=None):
    rows = ['| L | platform cells | platform arrows (start) | hidden arrows | read from | problems |', '|---|---|---|---|---|---|']
    for p in sorted(os.listdir(os.path.join(HERE, 'work', 'reveals'))):
        r = json.load(open(os.path.join(HERE, 'work', 'reveals', p)))
        if r.get('kind') != 'elevator':
            continue
        srcs = sorted({h['source'] for h in r['hidden']})
        rows.append('| %d%s | %d | %d | %d | %s | %s |' % (r['level'], ships(doc, r['level']), r['platform_cells'], len(r['platform']), len(r['hidden']),
                                                        ', '.join(srcs), '; '.join(r['problems']) or 'none'))
    return '\n'.join(rows)


def art_needs(doc):
    def size(o):
        xs = [c[0] for c in o['cells']]
        ys = [c[1] for c in o['cells']]
        return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
    need = {}
    for l in doc['levels']:
        for o in l['obstacles']:
            k = o['kind']
            if k in ('door', 'box', 'elevator'):
                need.setdefault(k, {}).setdefault('W%dH%d' % size(o), []).append(l['level'])
            elif k == 'corner':
                need.setdefault('corner', {}).setdefault('cornerWedge (%s)' % o['turn'], []).append(l['level'])
            elif k == 'tape':
                a = next(x for x in l['arrows'] if x['id'] == o['arrows'][0])
                orient = 'V' if a['dir'] in ('left', 'right') else 'H'   # the band runs across the lanes
                need.setdefault('tape', {}).setdefault('tape%s%d' % (orient, len(o['arrows'])), []).append(l['level'])
    rows = ['| kind | sizes (cells W x H or sprite id): levels |', '|---|---|']
    for k in ('door', 'box', 'elevator', 'tape', 'corner'):
        items = sorted(need.get(k, {}).items(), key=lambda kv: (len(kv[1]) * -1, kv[0]))
        rows.append('| %s (%d sizes) | %s |' % (k, len(items), '; '.join('%s: %s' % (sz, ','.join(map(str, sorted(set(ls)))))
                                                                         for sz, ls in items)))
    return '\n'.join(rows)


def pipe_counters(doc):
    import collections
    rows = ['| range | pipes | counters (value x count) |', '|---|---|---|']
    for name, a, b in (('video L1-31', 1, 31), ('L32-61 (as shipped)', 32, 61), ('L62-83 (as shipped)', 62, 83),
                       ('L84-105 (as shipped)', 84, 105), ('designed L106-150', 106, 150)):
        c = collections.Counter(o['counter'] for l in doc['levels'] if a <= rs(l) <= b for o in l['obstacles']
                                if o['kind'] == 'pipe')
        rows.append('| %s | %d | %s |' % (name, sum(c.values()), ', '.join('%d x%d' % kv for kv in sorted(c.items()))))
    return '\n'.join(rows)


def order_table(doc):
    """Every slot whose board moved in the re-order (design/level-order.json; level-reorder.md §6): what it ships."""
    rows = ['| L | tag | board (origin) | timer | obstacles | units/waves | from |', '|---|---|---|---|---|---|---|']
    moved = [l for l in doc['levels'] if rs(l) != l['level']]
    for l in moved:
        tapes = [o for o in l['obstacles'] if o['kind'] == 'tape']
        units = len(l['arrows']) - sum(len(t['arrows']) - 1 for t in tapes)
        kinds = sorted({{'curtain': 'box'}.get(o['kind'], o['kind']) for o in l['obstacles']} - {'key'})
        t = l['timer_s']
        rows.append('| %d | %s | %s | %d:%02d | %s | %d/%d | %+d |' % (
            l['level'], {'normal': '', 'hard': 'H', 'superHard': 'SH'}[l['tag']], LO.label(l), t // 60, t % 60,
            '+'.join(kinds) or '-', units, l['metrics']['rounds'], rs(l) - l['level']))
    rows.append('')
    rows.append('%d boards moved; the other %d levels hold the board of their research slot.' % (
        len(moved), len(doc['levels']) - len(moved)))
    return '\n'.join(rows)


def main():
    doc = json.load(open(os.path.join(DESIGN, 'levels.json')))
    path = os.path.join(DESIGN, 'LEVELS.md')
    text = open(path).read()
    sections = dict(levels=level_table(doc), curve=curve_table(doc), mix=obstacle_mix(doc), lengths=length_table(doc),
                    reveals=reveal_table(doc), elevators=elevator_table(doc), art=art_needs(doc), pipes=pipe_counters(doc))
    if '<!-- BEGIN:order -->' in text:
        sections['order'] = order_table(doc)
    for k, v in sections.items():
        text = re.sub(r'(<!-- BEGIN:%s -->\n)(?:.*?\n)?(<!-- END:%s -->)' % (k, k),
                      lambda m: m.group(1) + v + '\n' + m.group(2), text, flags=re.S)
    open(path, 'w').write(text)
    print('LEVELS.md sections updated: %s' % ', '.join(sections))


if __name__ == '__main__':
    main()
