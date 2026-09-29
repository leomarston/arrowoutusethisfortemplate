"""Exit colour vs tap cadence on the phone (v552): classifies every bot round shot (research/bot/tmp/Lnnn-HHMMSS-rNN.png,
lossless runner shots) as showing a BLUE exit (#1DA7ED-like), a RAINBOW exit (saturated green present on the board), both or
none, and joins it with the bot log (taps per round). out/exitcolour.txt"""
import os, re, json, glob, datetime, collections
import numpy as np
from PIL import Image
B = '/Users/yago/Downloads/app-factory/apps/mazeout/research/bot'
L = [json.loads(l) for l in open(os.path.join(B, 'log.jsonl'))]
def hms(t): return datetime.datetime.fromtimestamp(t).strftime('%H%M%S')
rows = []
shots = sorted(glob.glob(os.path.join(B, 'tmp', 'L0[0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]-r[0-9][0-9].png')))
sessions = collections.defaultdict(list)
for p in shots:
    m = re.match(r'L0(\d\d)-(\d{6})-r(\d\d)\.png', os.path.basename(p)); sessions[int(m.group(1))].append(m.group(2))
for p in shots:
    m = re.match(r'L0(\d\d)-(\d{6})-r(\d\d)\.png', os.path.basename(p))
    lev, ses, rnd = int(m.group(1)), m.group(2), int(m.group(3))
    sess = sorted(set(sessions[lev])); nxt = [s for s in sess if s > ses]; end = nxt[0] if nxt else '999999'
    ent = [e for e in L if e.get('level') == lev and e.get('round') == rnd and ses <= hms(e['t']) < end]
    ntap = len(ent)
    ms = None
    if ent and ent[0].get('out'):
        try: ms = json.loads(ent[0]['out']).get('ms')
        except Exception: ms = None
    im = np.asarray(Image.open(p).convert('RGB')).astype(int)
    H, W = im.shape[:2]; s = W / 393.0
    reg = im[int(130 * s):int(740 * s)]
    R, G, Bb = reg[..., 0], reg[..., 1], reg[..., 2]
    mx = reg.max(-1); mn = reg.min(-1)
    blue = (abs(R - 25) < 25) & (abs(G - 165) < 22) & (abs(Bb - 237) < 18)
    # green hue, saturated: rainbow bands (no obstacle is green)
    green = (G > 150) & (G - R > 60) & (G - Bb > 40)
    yellowgreen = (G > 180) & (R > 150) & (Bb < 90) & (R < 235)
    nb, ng = int(blue.sum() / s / s), int((green | yellowgreen).sum() / s / s)
    cls = ('rainbow' if ng > 8 else '') + ('+' if ng > 8 and nb > 30 else '') + ('blue' if nb > 30 else '')
    rows.append((os.path.basename(p), lev, rnd, ntap, ms, nb, ng, cls or 'none'))
out = []
for r in rows:
    out.append(f"{r[0]:22s} taps {r[3]:3d} ms {str(r[4]):40s} blue_pt2 {r[5]:5d} green_pt2 {r[6]:4d} -> {r[7]}")
agg = collections.Counter((min(r[3], 3), r[7]) for r in rows if r[7] != 'none')
out.append('SUMMARY (taps-in-round capped at 3, class): ' + str(sorted(agg.items())))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'exitcolour.txt'), 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
