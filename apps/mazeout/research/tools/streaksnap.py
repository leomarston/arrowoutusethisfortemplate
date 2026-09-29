#!/usr/bin/env python3
"""streaksnap.py NNN — from HOME: open the Streak Race panel (badge 47,235), shoot the top, scroll with overlapping 3-row steps to the
end, OCR every page and merge the rows in order (overlap by name). Prints 'rank | name | prize | score' for all rows and the timer;
shots shots/NNN-social-HHMMSS-streak-pK.png. Leaves the panel OPEN (caller closes with tap 361 72)."""
import subprocess, sys, time, re
R = '/Users/yago/Downloads/app-factory/apps/mazeout/research'; P = '/Users/yago/Downloads/app-factory/tools/phonedriver/phone'
N = sys.argv[1]
def t(*a): subprocess.run(['perl', '-e', 'alarm shift; exec @ARGV', '40', P, *map(str, a)], capture_output=True)
def snap(name):
    return subprocess.run([R + '/tools/snap.sh', N, name], capture_output=True, text=True).stdout.strip().splitlines()[-1]
def ocr(f, y0, y1):
    out = subprocess.run([R + '/tools/ocr', f, '0', str(y0), '393', str(y1)], capture_output=True, text=True).stdout
    it = []
    for line in out.splitlines():
        m = re.match(r'\s*(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+) \| (.*)', line)
        if m:
            x, y, w, h = map(int, m.groups()[:4]); it.append((x, y + h / 2, m.group(5).strip()))
    return it
def rows(f, y0=470, y1=852):
    its = ocr(f, y0, y1); names = sorted([i for i in its if 95 <= i[0] <= 130], key=lambda i: i[1])
    res = []
    for nx, ny, nm in names:
        near = [i for i in its if abs(i[1] - ny) < 30 and i is not None]
        prize = [i[2] for i in near if 235 <= i[0] <= 275 and re.fullmatch(r'\d+', i[2]) and abs(i[1] - ny) < 22]
        score = [i[2] for i in near if i[0] >= 320 and re.fullmatch(r'\d+', i[2])]
        rank = [i[2] for i in near if i[0] < 60 and re.fullmatch(r'\d+', i[2])]
        res.append(dict(y=ny, name=nm, prize=prize[0] if prize else '', score=score[0] if score else '?', rank=rank[0] if rank else ''))
    return res
if '--open' not in sys.argv:
    t('tap', 47, 235); time.sleep(2.2)
for _ in range(4):
    t('swipe', 196, 520, 196, 840, 0.1)
time.sleep(1.5)
f = snap('streak-p0'); timer = [i[2] for i in ocr(f, 440, 485)]
allrows = rows(f, 480, 852); pages = [f]
for k in range(1, 20):
    t('swipe', 196, 780, 196, 560, 0.8); time.sleep(1.3)
    f = snap('streak-p%d' % k); pages.append(f)
    new = rows(f)
    names = [r['name'] for r in allrows]
    # align: first new row whose name is already known → append the ones after it
    j = next((i for i, r in enumerate(new) if r['name'] in names[-6:]), None)
    if j is None:
        print('WARN no overlap on page', k, [r['name'] for r in new]); allrows += new
    else:
        last = max(i for i, r in enumerate(new) if r['name'] in names[-6:])
        allrows += new[last + 1:]
    if not new or (new and new[-1]['name'] == names[-1]):
        break
print('timer', timer)
for i, r in enumerate(allrows, 1):
    print('%2d | %-4s | %-20s | %5s | %s' % (i, r['rank'], r['name'], r['prize'], r['score']))
print('pages', len(pages))
