#!/usr/bin/env python3
"""tools/flat_check.py <png> [max_fraction=0.97]: exits 3 (and renames the file to <name>.rejected.png) when one flat
colour covers more than max_fraction of the screen below the 52 pt status band. Colours are compared at 5 bits per
channel, so a gradient or antialiasing never counts as flat. Used by tools/capture-shot.sh (GAMEPROMPT §8.3 step 4)."""
import os
import sys

from PIL import Image


def flat_fraction(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    top = int(round(h * 52 / 852))                       # the Dynamic Island band is never compared
    im = im.crop((0, top, w, h)).point(lambda v: v & 0xF8)
    colors = im.getcolors(maxcolors=w * h)
    count, rgb = max(colors)
    return count / float(im.size[0] * im.size[1]), rgb


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 64
    path = argv[0]
    limit = float(argv[1]) if len(argv) > 1 else 0.97
    frac, rgb = flat_fraction(path)
    tag = "#%02X%02X%02X" % rgb
    if frac > limit:
        bad = os.path.splitext(path)[0] + ".rejected.png"
        os.replace(path, bad)
        print(f"flat_check: REJECTED {path}: {frac:.3f} of the frame is {tag} (> {limit}); kept as {bad}", file=sys.stderr)
        return 3
    print(f"flat_check: ok {os.path.basename(path)}: most common colour {tag} covers {frac:.3f} (<= {limit})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
