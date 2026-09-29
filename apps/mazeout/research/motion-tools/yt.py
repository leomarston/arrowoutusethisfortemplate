"""Helpers for the owner's two gameplay videos (constant frame rate mp4, 592x1280, audio on).
   A = "Maze Out! - Tap Puzzle Levels 1-20 Gameplay.mp4" (25 fps, 505 s)
   B = "Maze Out! Gameplay Level 11-38.mp4"              (59.64 fps, 1683 s)
Crops are in points of a 393-pt-wide screen (592 px / 393 pt = 1.506 px/pt), like the phone clips.
Uses MFX_SEEK=1 so mfx seeks instead of decoding from 0.
CLI: yt.py sheet A|B START END STEP [WIDTH COLS x,y,w,h]  -> ../motion-frames/yt{A|B}_*.jpg"""
import os, sys, subprocess
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf

VIDS = {'A': '/Users/yago/Downloads/arrowoutproject/Maze Out! - Tap Puzzle Levels 1-20 Gameplay.mp4',
        'B': '/Users/yago/Downloads/arrowoutproject/Maze Out! Gameplay Level 11-38.mp4'}
FPS = {'A': 25.0, 'B': 59.64}
PT = 592 / 393.0


def raw(key, start, end, width=131, fps=240, crop=None):
    out = os.path.join(mf.W, f"yt{key}_{start}_{end}_{width}_{fps}_{crop}.bin".replace(' ', ''))
    cmd = [mf.MFX, 'raw', VIDS[key], out, str(fps), str(start), str(end), str(width)]
    if crop:
        cmd += [str(c) for c in crop]
    env = dict(os.environ, MFX_SEEK='1')
    subprocess.run(cmd, check=True, capture_output=True, env=env)
    d = open(out, 'rb').read()
    h = np.frombuffer(d[:16], dtype=np.int32)
    w, hh, n = int(h[1]), int(h[2]), int(h[3])
    t = np.frombuffer(d[16:16 + 8 * n], dtype=np.float64).copy()
    px = np.frombuffer(d[16 + 8 * n:], dtype=np.uint8).reshape(n, hh, w, 3)
    os.remove(out)
    return t, px


def sheet(key, s, e, step, width=90, cols=12, crop=None, out=None, label_fmt='{:.2f}'):
    fps = 240 if step <= 0 else max(1.0 / step, 0.01)
    t, px = raw(key, s, e, width, fps=240 if step <= 0 else 1.0 / step, crop=crop)
    tag = '' if crop is None else '_c' + '-'.join(str(int(c)) for c in crop)
    out = out or os.path.join(mf.SP, '..', 'motion-frames', f'yt{key}_{s}-{e}_{step}{tag}.jpg')
    mf.sheet([Image.fromarray(p) for p in px], [label_fmt.format(x) for x in t], out, cols=cols, font_size=11)
    return out, len(t)


if __name__ == '__main__':
    a = sys.argv
    if a[1] == 'sheet':
        key = a[2]; s = float(a[3]); e = float(a[4]); step = float(a[5])
        width = int(a[6]) if len(a) > 6 else 90
        cols = int(a[7]) if len(a) > 7 else 12
        crop = [float(v) for v in a[8].split(',')] if len(a) > 8 else None
        print(*sheet(key, s, e, step, width, cols, crop))
