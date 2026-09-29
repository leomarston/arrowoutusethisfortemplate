"""Re-measures the numbers of design/publish/motion-catalog.md (desk only: no phone, no simulator, no rendering).

Run: ~/.venvs/mf3d/bin/python design/publish/tools/motion_catalog_measure.py [pause|slide|v2slide|shopcards|badges|claim|unlock|all]
Uses research/motion-tools/mf.py (phone .mov, presentation times) and yt.py (the owner's mp4s, MFX_SEEK). Light: small widths,
short windows. Prints plain tables; nothing is written.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'research', 'motion-tools'))
import mf  # noqa: E402
import yt  # noqa: E402


def bbox_w(frame, cond, y0=150, y1=700):
    f = frame.astype(int)
    m = cond(f[..., 0], f[..., 1], f[..., 2])
    m[:y0] = False
    m[y1:] = False
    ys, xs = np.nonzero(m)
    return (xs.max() - xs.min()) if len(xs) > 50 else None


BLUE = lambda R, G, B: (B > 170) & (R < 90) & (G > 60) & (G < 200)   # noqa: E731
YELLOW = lambda R, G, B: (R > 200) & (G > 140) & (B < 90)             # noqa: E731


def pause():
    """v552 Paused panel: scale punch on open (1 pt/px at width 393)."""
    t, px = mf.raw("S3-L092-pause-open-close.mov", 1.49, 1.70, width=393)
    rest = None
    rows = [(t[i], bbox_w(px[i], BLUE), bbox_w(px[i], YELLOW)) for i in range(len(t))]
    rest = rows[-1]
    print("v552 pause   t     blue-w  scale   title-w scale")
    for tt, b, y in rows:
        if b and y:
            print(f"  {tt:.3f}  {b:4d}  {b / rest[1]:.3f}   {y:4d}  {y / rest[2]:.3f}")
    t, px = yt.raw('B', 80.58, 80.76, width=393)
    rows = [(t[i], bbox_w(px[i], BLUE)) for i in range(len(t))]
    rest = rows[-1][1]
    print("V2 quit      " + "  ".join(f"{tt:.3f}:{(b or 0) / rest:.3f}" for tt, b in rows))


def shift_series(t, px, ref, band, rng=(-100, 300)):
    R = ref[band].astype(float).mean(axis=2)
    out = []
    for i in range(len(t)):
        F = px[i][band].astype(float).mean(axis=2)
        best = None
        for s in range(*rng):
            a, b = (F[:, s:], R[:, :R.shape[1] - s]) if s >= 0 else (F[:, :F.shape[1] + s], R[:, -s:])
            if a.shape[1] < 60:
                continue
            e = np.abs(a - b).mean()
            if best is None or e < best[0]:
                best = (e, s)
        out.append((t[i], best[1], best[0]))
    return out


def slide():
    """v552 tab slide tail (home -> Leaderboard, forced Weekly step)."""
    t, px = mf.raw("S1-weekly-contest-open.mov", 0, 0.24, width=393)
    for tt, s, e in shift_series(t, px, px[-1], slice(30, 70)):
        print(f"  v552 {tt:.3f} page offset {s:+4d} pt (err {e:.1f})")


def v2slide():
    """V2 (older build) Shop -> Leaderboard, one page, full curve; fit 1-(1-u)^n."""
    t, px = yt.raw('B', 28.40, 28.92, width=393)
    for tt, s, e in shift_series(t, px, px[0], slice(100, 600), rng=(-393, 60)):
        print(f"  V2 {tt:.3f} old page offset {s:+4d} pt (err {e:.1f})")


def shopcards():
    """V2 closable Shop: each card row slides in from the right with an overshoot."""
    t, px = yt.raw('B', 71.14, 71.75, width=393)
    for name, (a, b) in {"special": (160, 250), "epic": (490, 530), "elite": (690, 730)}.items():
        ser = shift_series(t, px, px[-1], slice(a, b), rng=(-60, 394))
        print(name, " ".join(f"{tt:.3f}:{s:+d}" for tt, s, _ in ser))


def badges():
    """v552 idle home: the left event badges animate (flags wave, rocket lift-off, sky drum hop)."""
    t, px = mf.raw("META-home-idle-12s.mov", 0, 16, width=393, fps=30)
    f = px.astype(int)
    for name, (x0, y0, x1, y1) in {"streak": (15, 200, 85, 275), "rocket": (15, 295, 85, 370), "sky": (15, 390, 85, 465)}.items():
        r = f[:, y0:y1, x0:x1]
        d = np.abs(np.diff(r, axis=0)).mean(axis=(1, 2, 3))
        print(f"{name:7s}", "".join("#" if x > 2 else "+" if x > 0.8 else "." if x > 0.3 else " " for x in d[::2]))
    print("(1 char = 1/15 s)")


def claim():
    """v552 Sky Jump stage win claim: title letters, island, 'You win!', coin count-up."""
    t, px = mf.raw("S3-skyjump3-win-claim.mov", 1.20, 3.80, width=393)
    for i in range(0, len(t), 3):
        f = px[i].astype(int)
        y = YELLOW(f[..., 0], f[..., 1], f[..., 2])
        ys, xs = np.nonzero(y[80:190])
        print(f"  {t[i]:.3f} title right edge {xs.max() if len(xs) else -1}")


def unlock():
    """v552 unlock card dismiss fade (two clips)."""
    for clip, s, e in (("S3-L100-elevator-unlock-dismiss.mov", 1.10, 1.45), ("S2-L070-corner-unlock-dismiss.mov", 1.35, 1.70)):
        t, px = mf.raw(clip, s, e, width=131)
        lum = px.mean(axis=(1, 2, 3))
        print(clip, " ".join(f"{t[i]:.3f}:{lum[i]:.0f}" for i in range(len(t))))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for name in ('pause', 'slide', 'v2slide', 'shopcards', 'badges', 'claim', 'unlock'):
        if what in (name, 'all'):
            print('==', name)
            globals()[name]()
