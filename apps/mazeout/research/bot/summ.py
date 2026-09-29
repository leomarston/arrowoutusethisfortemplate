#!/usr/bin/env python3
"""summ.py LEVEL "free text lines..." → appends a levels.md entry built from levels/Lnnn.json + bot/log.jsonl + the text."""
import json, sys, collections, os
R = '/Users/yago/Downloads/app-factory/apps/mazeout/research'
L = int(sys.argv[1]); text = sys.argv[2] if len(sys.argv) > 2 else ''
jp = f'{R}/levels/L{L:03d}.json'
d = json.load(open(jp))
if '--timer' in sys.argv: d['timer_s'] = int(sys.argv[sys.argv.index('--timer') + 1])
if '--tag' in sys.argv: d['tag'] = sys.argv[sys.argv.index('--tag') + 1]
json.dump(d, open(jp, 'w'), indent=1)
ts = '%d:%02d' % (d['timer_s'] // 60, d['timer_s'] % 60) if d.get('timer_s') else '?'
ob = collections.Counter(o['kind'] for o in d['obstacles'])
dirs = collections.Counter(a['dir'] for a in d['arrows'])
lens = [len(a['cells']) for a in d['arrows']]
taps = [json.loads(l) for l in open(f'{R}/bot/log.jsonl') if f'"level": {L},' in l]
ntap = sum(1 for t in taps if t.get('result') == 'tapped')
rounds = len({t.get('round') for t in taps if t.get('result') == 'tapped'})
out = [f'\n## L{L}',
       f'- Tag: {d.get("tag") or "none"}. Timer {ts}. Hearts {d["hearts"]}. Board {d["cols"]}x{d["rows"]} cells '
       f'(bounding box of arrow+obstacle cells), pitch {d["pitch_pt"]} pt at {d["zoom"]} zoom (stroke {d["stroke_pt"]} pt).',
       f'- Arrows at start (visible): {len(d["arrows"])} (dirs {dict(dirs)}; length min/median/max {min(lens)}/{sorted(lens)[len(lens)//2]}/{max(lens)} cells).',
       f'- Obstacles: {dict(ob) if ob else "none"}' + (f'; door cells {sum(len(o["cells"]) for o in d["obstacles"] if o["kind"]=="door")}' if ob.get('door') else ''),
       f'- JSON: research/levels/L{L:03d}.json (shot {d["shot"]}). Bot: {ntap} tap entries over {rounds} rounds (bot/log.jsonl).']
out += ['- ' + t for t in text.split('\n') if t.strip()]
open(f'{R}/levels.md', 'a').write('\n'.join(out) + '\n')
print('\n'.join(out))
