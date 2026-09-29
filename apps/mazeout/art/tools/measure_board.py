#!/usr/bin/env python3
"""Measure the board look (family A: arrows, heads, vacated dots) on the untinted runner shots.

    python3 art/tools/measure_board.py            # prints the numbers STYLE.md §A quotes

Captures are 1178 x 2556 px lossless sRGB from the iPhone 15 (393 x 852 pt): pt = px * 393 / 1178.
Looked at only; nothing is copied out of them.
"""
import os
import numpy as np
from PIL import Image

APP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHOTS = os.path.join(APP, "research", "shots")
PT = 393 / 1178


def load(n):
    return np.asarray(Image.open(os.path.join(SHOTS, n)).convert("RGB")).astype(np.float64)


def runs(mask1d):
    """(start, length) of True runs."""
    m = np.concatenate([[False], mask1d, [False]])
    d = np.diff(m.astype(int))
    s = np.nonzero(d == 1)[0]
    e = np.nonzero(d == -1)[0]
    return list(zip(s, e - s))


def main():
    im = load("003-L32-start.png")
    lum = im.mean(2)
    sat = im.max(2) - im.min(2)
    cover = np.clip((255 - lum) / 255, 0, 1) * (sat < 20)      # ink coverage (neutral pixels only)
    y0, y1, x0, x1 = 760, 1880, 40, 1140                         # the board box on 003
    ink = cover > 0.5
    # --- stroke width: coverage summed across horizontal strokes (vertical profiles), and vice versa
    widths_h, cy = [], []
    for x in range(x0, x1, 3):
        for s, L in runs(ink[y0:y1, x]):
            if 8 <= L <= 16:
                a, b = y0 + s - 2, y0 + s + L + 2
                widths_h.append(cover[a:b, x].sum())
                cy.append(((np.arange(a, b)) * cover[a:b, x]).sum() / cover[a:b, x].sum())
    widths_v, cx = [], []
    for y in range(y0, y1, 3):
        for s, L in runs(ink[y, x0:x1]):
            if 8 <= L <= 16:
                a, b = x0 + s - 2, x0 + s + L + 2
                widths_v.append(cover[y, a:b].sum())
                cx.append(((np.arange(a, b)) * cover[y, a:b]).sum() / cover[y, a:b].sum())
    wh, wv = np.median(widths_h), np.median(widths_v)
    print(f"stroke width: horizontal strokes {wh:.2f} px, vertical strokes {wv:.2f} px -> {PT * (wh + wv) / 2:.2f} pt "
          f"(p10-p90 {np.percentile(widths_h + widths_v, 10):.2f}-{np.percentile(widths_h + widths_v, 90):.2f} px)")
    # --- lattice: histogram of stroke centres, peaks = grid lines
    def lattice(c, name):
        c = np.asarray(c)
        h, e = np.histogram(c, bins=np.arange(c.min() - 1, c.max() + 2, 1.0))
        peaks = []
        for i in range(1, len(h) - 1):
            if h[i] >= max(h[i - 1], h[i + 1]) and h[i] > 12:
                if peaks and e[i] - peaks[-1][0] < 20:
                    if h[i] > peaks[-1][1]:
                        peaks[-1] = (e[i] + 0.5, h[i])
                    continue
                peaks.append((e[i] + 0.5, h[i]))
        pos = np.array([p for p, _ in peaks])
        # refine each peak with the mean of centres within +-3 px
        pos = np.array([c[np.abs(c - p) < 3].mean() for p in pos])
        d = np.diff(pos)
        pitch = np.median(d[(d > 30) & (d < 80)])
        k = np.round((pos - pos[0]) / pitch)
        A = np.stack([k, np.ones_like(k)], 1)
        (p_fit, o_fit), res, *_ = np.linalg.lstsq(A, pos, rcond=None)
        err = np.abs(A @ [p_fit, o_fit] - pos).max()
        print(f"{name}: {len(pos)} line positions, pitch {p_fit:.3f} px = {p_fit * PT:.3f} pt, first {o_fit:.1f} px, "
              f"cells {int(k.max()) + 1}, max residual {err:.2f} px")
        return p_fit, o_fit, int(k.max()) + 1
    py, oy, ny = lattice(cy, "rows (horizontal strokes, y)")
    px_, ox, nx = lattice(cx, "cols (vertical strokes, x)")
    print(f"board span: x {ox:.1f}..{ox + (nx - 1) * px_:.1f} px, y {oy:.1f}..{oy + (ny - 1) * py:.1f} px "
          f"(centre x {(2 * ox + (nx - 1) * px_) / 2 * PT:.1f} pt, y {(2 * oy + (ny - 1) * py) / 2 * PT:.1f} pt)")
    # --- head: the right-pointing heads of the 4 taped arrows at the top-left (rows 1-4)
    heads = []
    for r in range(4):
        yc = oy + r * py
        band = cover[int(yc - py / 2):int(yc + py / 2), 150:300]
        col_extent = (band > 0.5).sum(0)                      # ink height per column
        base = np.nonzero(col_extent > 1.6 * wh)[0]
        if len(base):
            xs = 150 + base
            tip = 150 + np.nonzero(col_extent > 0)[0].max()
            heads.append((col_extent.max(), tip - xs.min() + 1, xs.min(), tip))
    for hw, hl, a, b in heads:
        print(f"head (right): width {hw} px = {hw * PT:.2f} pt, length {hl} px = {hl * PT:.2f} pt (x {a}..{b})")
    # tip position relative to the lattice: how far past the last cell centre the tip reaches
    tips = [b for *_, b in heads]
    print("head tips x px:", tips, " nearest col centre", [round(ox + round((t - ox) / px_) * px_, 1) for t in tips])
    # --- end cap: rounded? coverage at the tail end of the top-left arrow (row 0)
    yc = int(round(oy))
    tail = cover[yc - 8:yc + 9, 60:90]
    first = [np.nonzero(tail[i] > 0.5)[0].min() if (tail[i] > 0.5).any() else -1 for i in range(tail.shape[0])]
    print("tail end profile (first ink col per row, row0 tail):", first)
    # --- colours
    core = ink & (cover > 0.99)
    print("ink core colour (mean sRGB):", im[y0:y1, x0:x1][core[y0:y1, x0:x1]].mean(0).round(1))
    bg = (lum > 250)[y0:y1, x0:x1]
    print("board ground colour:", im[y0:y1, x0:x1][bg].mean(0).round(1), " screen top", im[400, 600], " bottom", im[2100, 600])
    # --- vacated dots (004): light blue discs where the arrow was
    im4 = load("004-L32-after-first.png")
    b = im4[..., 2] - im4[..., 0]
    dots = (b > 20) & (im4[..., 2] > 230)
    ys, xs = np.nonzero(dots[1500:1700, 40:400])
    from scipy import ndimage
    lab, n = ndimage.label(dots[1500:1700, 40:400])
    cs = ndimage.center_of_mass(dots[1500:1700, 40:400], lab, range(1, n + 1))
    sizes = ndimage.sum(dots[1500:1700, 40:400], lab, range(1, n + 1))
    good = [(c, s) for c, s in zip(cs, sizes) if s > 30]
    print(f"vacated dots: {len(good)}; centres y px", [round(1500 + c[0], 1) for c, _ in good][:6],
          "x px", [round(40 + c[1], 1) for c, _ in good][:6])
    dia = [2 * np.sqrt(s / np.pi) for _, s in good]
    print(f"  diameter ~{np.median(dia):.1f} px = {np.median(dia) * PT:.2f} pt (area-equivalent, core only)")
    cols = im4[1500:1700, 40:400][lab > 0]
    print("  dot colour core (max-blue pixels):", cols[cols[:, 2] >= 250].mean(0).round(1) if len(cols) else None,
          " darkest:", cols[np.argmin(cols.sum(1))])
    xs_d = sorted(40 + c[1] for c, _ in good)
    print("  dot spacing px:", np.diff(xs_d).round(1))


if __name__ == "__main__":
    main()
