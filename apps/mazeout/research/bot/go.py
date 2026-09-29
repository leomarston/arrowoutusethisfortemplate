#!/usr/bin/env python3
"""go.py LEVEL NNN [--no-play] — from HOME: Play → start shot shots/NNN-L<lvl>-start.png → guard/read (stop on anything odd) →
dump levels/Lnnn.json → play2 → shot of the end popup shots/(NNN+1)-L<lvl>-end.png. Prints a one-line verdict per step."""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot
import numpy as np
from PIL import Image
L = int(sys.argv[1]); N = int(sys.argv[2]); noplay = '--no-play' in sys.argv; here = '--here' in sys.argv
retry = '--retry' in sys.argv          # entry tap = 'Try Again' (196,558); keep the first start JSON
entry = ('196', '558') if retry else ('196', '668')
R = bot.ROOT
start = f'{R}/shots/{N:03d}-L{L:03d}-' + ('retry-start.png' if retry else 'start.png')
if here and os.path.exists(start):
    im = np.array(Image.open(start).convert('RGB')).astype(np.int16)
else:
    subprocess.run([bot.PHONE, 'tap', entry[0], entry[1]], capture_output=True)
    time.sleep(1.6)
    im = bot.shot(start)
ok, why, info = bot.guard(im)
prev = '/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad/prev.png'
Image.open(start).resize((393, 852)).save(prev)
if not ok:
    print('GUARD', why, info, '→ look at', prev); sys.exit(2)
b = bot.apply_overrides(im, bot.read_board(im), L)
ov = f'{bot.OVL}/L{L:03d}-start.png'
bot.overlay(im, b, ov)
a = Image.open(start).resize((393, 852)); o = Image.open(ov).resize((393, 852))
W = Image.new('RGB', (796, 852), 'white'); W.paste(a, (0, 0)); W.paste(o, (403, 0)); W.save(prev)
unk = [x for x in b['obstacles'] if x['kind'] == 'unknown']
kinds = sorted({x['kind'] for x in b['obstacles']})
print('READ arrows', len(b['arrows']), 'pitch_pt %.2f' % (b['fit']['pitch'] / bot.SCALE), 'obstacles', kinds, 'anomalies', b['anomalies'], 'unknown', [(x['bbox_px'], x['mean_rgb']) for x in unk])
if b['anomalies'] or unk:
    print('STOP before first tap (timer not running) → look at', prev); sys.exit(3)
if not (retry and os.path.exists(f'{bot.LEVELS}/L{L:03d}.json')):
    bot.dump_level(b, L, start, zoom='fit')
else:
    print('retry: kept existing JSON; arrows now', len(b['arrows']), 'json', len(__import__('json').load(open(f'{bot.LEVELS}/L{L:03d}.json'))['arrows']))
if noplay or not bot.plan(b):
    print('NO PLAY (noplay or no free unit) → look at', prev); sys.exit(4)
res = bot.play2(L, 230)
print('PLAY', res)
S = 1178 / 393
def is_win(path):
    a = np.array(Image.open(path).convert('RGB')).astype(int)
    q = a[int(425 * S):int(475 * S), int(215 * S):int(290 * S)].reshape(-1, 3)
    return ((q[:, 0] > 235) & (q[:, 1] > 235) & (q[:, 2] > 235)).mean() > 0.25
shots = [start]
if '--next' in sys.argv:            # number end shots from --next K (so a resumed run does not overwrite earlier shots)
    N = int(sys.argv[sys.argv.index('--next') + 1]) - 1
if res == 'guard':
    c1 = f'{R}/shots/{N + 1:03d}-L{L:03d}-end-a.png'; bot.shot(c1)
    time.sleep(2.3)
    c2 = f'{R}/shots/{N + 2:03d}-L{L:03d}-end-popup.png'; bot.shot(c2); shots.append(c2)
    if is_win(c2):
        print('WIN popup detected → Continue')
        subprocess.run([bot.PHONE, 'tap', '196', '538'], capture_output=True)
        time.sleep(3.6)
        c3 = f'{R}/shots/{N + 3:03d}-after-L{L:03d}.png'; bot.shot(c3); shots.append(c3)
        def is_home(path):
            a = np.array(Image.open(path).convert('RGB')).astype(int)
            g = a[int(800 * S):int(845 * S), int(5 * S):int(30 * S)].reshape(-1, 3)
            return ((g[:, 2] > 180) & (g[:, 0] < 90) & (g[:, 1] > 60)).mean() > 0.6
        for k in range(2):
            if is_home(c3):
                break
            print('after-Continue screen is not home (event progress?) → tap (196,785)')
            subprocess.run([bot.PHONE, 'tap', '196', '785'], capture_output=True)
            time.sleep(2.4)
            c3 = f'{R}/shots/{N + 3:03d}-after-L{L:03d}-home{k + 1}.png'; bot.shot(c3); shots.append(c3)
        print('NEXT free shot number', N + 4, 'home' if is_home(c3) else 'NOT HOME')
    else:
        print('NOT a win popup — look; NEXT free shot number', N + 3)
else:
    c1 = f'{R}/shots/{N + 1:03d}-L{L:03d}-stopped.png'; bot.shot(c1); shots.append(c1)
    print('NEXT free shot number', N + 2)
W = Image.new('RGB', (262 * len(shots) + 6 * len(shots), 568), 'white')
for i, sp in enumerate(shots):
    W.paste(Image.open(sp).resize((262, 568)), (i * 268, 0))
W.save(prev)
print('montage →', prev)
