#!/usr/bin/env python3
"""lbrows.py SHOT [y0 y1] — OCR a leaderboard/race list into rows: 'y | rank | name | numbers...' (uses tools/ocr)."""
import subprocess, sys, re
f = sys.argv[1]; y0, y1 = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ('470', '852')
out = subprocess.run(['/Users/yago/Downloads/app-factory/apps/mazeout/research/tools/ocr', f, '0', y0, '393', y1], capture_output=True, text=True).stdout
items = []
for line in out.splitlines():
    m = re.match(r'\s*(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+) \| (.*)', line)
    if m:
        x, y, w, h = map(int, m.groups()[:4]); items.append((x, y + h / 2, m.group(5)))
items.sort(key=lambda t: t[1])
rows = []
for it in items:
    if rows and abs(it[1] - rows[-1][0]) < 22:
        rows[-1][1].append(it)
    else:
        rows.append([it[1], [it]])
for y, its in rows:
    its.sort()
    print('%4.0f | ' % y + ' | '.join('%s@%d' % (t[2], t[0]) for t in its))
