#!/usr/bin/env python3
"""Collects the per-level facts for research/video-levels.md (levels 1-38) -> verify/consolidated.json + markdown rows on stdout."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate

R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
idx = json.load(open(os.path.join(R, 'video-index.json')))
IX = {(x['video'], x['level']): x for x in idx['levels']}
third = json.load(open(os.path.join(R, 'levels', 'video', 'verify', 'thirdreader.json')))
rer = json.load(open(os.path.join(R, 'levels', 'video', 'verify', 'replay-rerun.json')))
xm = {r['video_level']: r for r in json.load(open(os.path.join(R, 'levels', 'video', 'verify', 'xmatch.json')))['rows']}
PHONE_SAME = {12: 51, 14: 52, 21: 35, 26: 45}


def obst_summary(d):
    parts = []
    boxes = [o for o in d['obstacles'] if o['kind'] in ('box', 'curtain')]
    if boxes:
        parts.append('box ' + '/'.join(str(o['counter']) for o in boxes))
    ties = [o for o in d['obstacles'] if o['kind'] == 'tape_pink']
    if ties:
        sizes = sorted({len(o['cells']) for o in ties})
        parts.append(f'{len(ties)} tie' + ('s' if len(ties) > 1 else '') + ' x' + '/'.join(map(str, sizes)))
    if d.get('pipes'):
        parts.append('pipe ' + '/'.join(str(p['counter']) for p in d['pipes']))
    if d.get('elevators'):
        parts.append('elevator ' + '+'.join(f"{len(e['cells'])}c/{len(e.get('hidden_arrow_ids', []))}h" for e in d['elevators']))
    return ', '.join(parts) or '-'


rows = []
out = {}
for n in range(1, 39):
    f = os.path.join(R, 'levels', f'L{n:03d}.json') if n <= 31 else os.path.join(R, 'levels', 'video', f'V2-L{n:03d}.json')
    d = json.load(open(f))
    vid = 'V1' if n <= 10 else 'V2'
    ix = IX.get((vid, n), {})
    start = [a for a in d['arrows'] if a.get('layer', 1) == 1]
    hid = [a for a in d['arrows'] if a.get('layer', 1) != 1]
    cells = sum(len(a['cells']) for a in start)
    sol = validate.solve_rounds(d)
    t3 = third.get(f'{vid}-L{n:03d}', {})
    t3alt = third.get(f'V1-L{n:03d}') if 11 <= n <= 20 else None
    rr = rer.get(f'{vid}-L{n:03d}', {}).get('stats', {})
    rr1 = rer.get(f'V1-L{n:03d}', {}).get('stats', {}) if 11 <= n <= 20 else None
    popups = [b for b in (ix.get('before') or []) if b.get('kind') == 'unlock']
    unlock = popups[0]['text'][0] if popups else ''
    tag = d.get('tag') or ''
    rec = {
        'level': n, 'file': os.path.relpath(f, R), 'source': d.get('source'), 'video': vid, 't_start': d.get('t'),
        'grid': f"{d['cols']}x{d['rows']}", 'cols': d['cols'], 'rows': d['rows'], 'pitch_pt': d['pitch_pt'],
        'arrows': len(start), 'hidden': len(hid), 'cells': cells, 'obstacles': obst_summary(d), 'tag': tag,
        'timer_s': d.get('timer_s'), 'hearts': d.get('hearts'), 'reward': ix.get('reward'), 'time_left': ix.get('timer_at_clear'),
        'play_s': round(ix['t_clear'] - ix['t_first_tap'], 1) if ix.get('t_clear') and ix.get('t_first_tap') else None,
        'taps': ix.get('n_taps'), 'hearts_end': ix.get('hearts_end'), 'unlock_popup': unlock,
        'captions': ix.get('captions'), 'rounds': sol['rounds'], 'free_at_start': sol.get('free_at_start'), 'moves': sol['moves'],
        'third_reader': f"{t3.get('identical')}/{t3.get('nB')}" + (f" (V1 {t3alt.get('identical')}/{t3alt.get('nB')})" if t3alt else ''),
        'replay_rerun_inconsistent': rr.get('inconsistent'), 'replay_rerun_V1_inconsistent': rr1.get('inconsistent') if rr1 else None,
        'phone_same': PHONE_SAME.get(n), 'best_other_phone_overlap': f"{xm[n]['identical']}/{xm[n]['video_arrows']} ({xm[n]['best_phone']})",
    }
    out[n] = rec
    ph = f"= phone L{PHONE_SAME[n]}" if n in PHONE_SAME else ('-' if n < 32 else 'no (phone L%d differs)' % n)
    rows.append(f"| {n} | {vid} {d.get('t')} | {rec['grid']} | {rec['arrows']}" + (f" (+{rec['hidden']})" if rec['hidden'] else '') +
                f" | {rec['obstacles']} | {tag or '-'} | {rec['timer_s'] // 60}:{rec['timer_s'] % 60:02d} | {rec['reward']} | {rec['time_left']} | "
                f"{rec['rounds']} | {unlock or '-'} | {ph} | {rec['third_reader']} | {rec['replay_rerun_inconsistent']}" +
                (f"/{rec['replay_rerun_V1_inconsistent']}" if rr1 else '') + ' |')
json.dump(out, open(os.path.join(R, 'levels', 'video', 'verify', 'consolidated.json'), 'w'), indent=1)
print('\n'.join(rows))
