#!/usr/bin/env python3
"""playabove.py LEVEL YMAX_PT [ROUNDS] — corner levels (v552 L70+): the session-1 bot knows no CORNER obstacle, so play only the arrows
whose every cell lies above YMAX_PT (the maze part, unaffected by the corners) with the bot's greedy planner; unknown blobs (the corners)
are dropped from the obstacle list. Round shots: bot/tmp/L<lvl>-above-<HHMMSS>-rNN.png. Stops when no maze arrow is left."""
import sys, time
lvl, ymax = int(sys.argv[1]), float(sys.argv[2]); R = int(sys.argv[3]) if len(sys.argv) > 3 else 12
sys.argv = ['x', '--ignore-anomalies']; sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/research/bot')
import bot
run = time.strftime('%H%M%S'); fit = None
for rnd in range(1, R + 1):
    im = bot.shot(bot.TMP + '/L%03d-above-%s-r%02d.png' % (lvl, run, rnd))
    ok, why, info = bot.guard(im)
    if not ok: print('guard', why); break
    try:
        b = bot.read_board(im, fit=None)
        if len(b['arrows']) >= 4: fit = b['fit']
    except (RuntimeError, ValueError):
        if fit is None: print('read failed'); break
        b = bot.read_board(im, fit=fit)
    b = bot.apply_overrides(im, b, lvl)
    b['obstacles'] = [o for o in b['obstacles'] if o['kind'] != 'unknown']
    f = b['fit']
    def y_pt(c): return (f['y0'] + c[1] * f['pitch']) / bot.SCALE
    maze = [a for a in b['arrows'] if all(y_pt(c) < ymax for c in a['cells'])]
    print('round', rnd, 'arrows', len(b['arrows']), 'above', len(maze), flush=True)
    if not maze: break
    taps = [(u, c, xy) for u, c, xy in bot.plan(b) if all(y_pt(cc) < ymax for cc in u['cells'])]
    if not taps: print('no taps above'); break
    spec = ';'.join('%.1f,%.1f' % xy for _, _, xy in taps)
    print(' tapping', len(taps), flush=True)
    bot.sh([bot.PHONE, 'taps', spec, '0.05'], timeout=200)
    time.sleep(0.5)
