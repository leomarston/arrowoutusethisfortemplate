#!/usr/bin/env python3
"""reveal.py LEVEL [RUN] — post-hoc: walk the bot's per-round shots bot/tmp/L<lvl>-<run>-rNN.png of a (won) run, and dump the
first clean read after each door opening as levels/L<lvl>-open<k>.json (cells in the START json frame) + an overlay."""
import sys, os, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot
import numpy as np
from PIL import Image
L = int(sys.argv[1])
fs = sorted(glob.glob(f'{bot.TMP}/L{L:03d}-*-r*.png'))
runs = sorted({re.search(r'-(\d{6})-r', f).group(1) for f in fs})
run = sys.argv[2] if len(sys.argv) > 2 else runs[-1]
fs = [f for f in fs if f'-{run}-r' in f]
prev = None
for f in fs:
    im = np.array(Image.open(f).convert('RGB')).astype(np.int16)
    ok, why, info = bot.guard(im)
    if not ok:
        continue
    try:
        b = bot.apply_overrides(im, bot.read_board(im), L)
    except Exception as e:
        continue
    nd = sum(1 for o in b['obstacles'] if o['kind'] in ('door', 'box'))
    if prev is None:
        prev = nd; print(os.path.basename(f), 'doors', nd); continue
    if nd < prev and not b['anomalies']:
        k = 1 if prev is None else 0
        k = (json_start_doors if 'json_start_doors' in dir() else None)
        import json
        st = json.load(open(f'{bot.LEVELS}/L{L:03d}.json'))
        k = sum(1 for o in st['obstacles'] if o['kind'] in ('door', 'box')) - nd
        p = bot.dump_level(b, L, f, suffix='-open%d' % k, extra=dict(note='state after %d door(s) opened (arrows revealed); cells in the START json frame; post-hoc from %s' % (k, os.path.basename(f))))
        bot.overlay(im, b, f'{bot.OVL}/L{L:03d}-open{k}.png', note=f'after {k} door(s) opened')
        print(os.path.basename(f), 'doors', nd, '→', p, 'arrows', len(b['arrows']))
        prev = nd
    elif nd < prev:
        print(os.path.basename(f), 'doors', nd, 'anomalies (skip)', b['anomalies'][:1])
