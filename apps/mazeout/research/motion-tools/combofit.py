"""Which rule decides the exit colour? Reads out/exitscan_*.txt; for combo windows W, tabulates the colour class by the
combo index c (c = 1 at a tap whose gap to the previous tap exceeds W, else c+1). out/combofit.txt"""
import sys, os, re, collections, glob
SP = os.path.dirname(os.path.abspath(__file__))
files = sys.argv[1:] or sorted(glob.glob(os.path.join(SP, 'out', 'exitscan_*.txt')))
taps = []
for f in files:
    for l in open(f):
        m = re.match(r'\s*([\d.]+) tap .* gap\s+([-\d.]+)s .*-> (\S+)', l)
        if m: taps.append((f, float(m.group(1)), float(m.group(2)), m.group(3)))
out = []
for W in (0.5, 0.7, 0.9, 1.1, 1.3, 1.6, 2.0, 2.5):
    tab = collections.defaultdict(collections.Counter)
    c = 0; pf = None
    for (f, t, g, k) in taps:
        if f != pf or g < 0 or g > W: c = 1
        else: c += 1
        pf = f
        if k in ('?', 'warm', 'magenta') : k2 = 'other'
        else: k2 = k
        tab[min(c, 8)][k2] += 1
    # score: best threshold split cyan(c<=k) vs rainbow(c>k)
    best = None
    for kth in range(1, 8):
        good = sum(tab[c]['cyan'] for c in tab if c <= kth) + sum(tab[c]['rainbow'] for c in tab if c > kth)
        bad = sum(tab[c]['rainbow'] for c in tab if c <= kth) + sum(tab[c]['cyan'] for c in tab if c > kth)
        if best is None or good / (good + bad) > best[0]: best = (good / (good + bad), kth, good, bad)
    out.append(f"W={W:.1f}s  best split: cyan for c<={best[1]}, rainbow after: {best[0]*100:.1f}% ({best[2]} ok / {best[3]} wrong)")
    for c in sorted(tab):
        out.append(f"   c={c}{'+' if c == 8 else ' '} " + ' '.join(f"{k}:{tab[c][k]}" for k in ('cyan', 'violet', 'rainbow', 'green', 'other')))
open(os.path.join(SP, 'out', 'combofit.txt'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))

# 3-class ladder check (cyan c<=2, violet c==3, rainbow c>=4) on a fine W grid, per file and pooled
def ladder(W, subset):
    ok = n = 0; c = 0; pf = None
    for (f, t, g, k) in subset:
        if f != pf or g < 0 or g > W: c = 1
        else: c += 1
        pf = f
        if k not in ('cyan', 'violet', 'rainbow'): continue
        pred = 'cyan' if c <= 2 else 'violet' if c == 3 else 'rainbow'
        n += 1; ok += (pred == k) or (c == 3 and k in ('cyan', 'rainbow'))  # c=3 is the transition frame
    return ok, n
lines = ['LADDER (cyan c<=2 / violet c=3 (cyan or rainbow also accepted) / rainbow c>=4):']
for W in [x / 20 for x in range(16, 41)]:
    parts = []
    for name in sorted(set(f for f, *_ in taps)):
        ok, n = ladder(W, [x for x in taps if x[0] == name]); parts.append(f"{os.path.basename(name)} {ok}/{n}={ok/n*100:.1f}%")
    ok, n = ladder(W, taps)
    lines.append(f"  W={W:.2f}s pooled {ok}/{n}={ok/n*100:.1f}%  | " + ' | '.join(parts))
open(os.path.join(SP, 'out', 'combofit.txt'), 'a').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
