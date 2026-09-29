"""Lighting-rig calibration: render the palette spheres, report lit / mid / dark values."""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import preview as P


def scene(name, key, ibl, fill=0.0, key_dir=(0.42, -1, 0.55)):
    s = P.base_scene(f'{P.PREV}/calib_{name}.png', 1100, 260, P.top_camera(2.4, 1100 / 260))
    s['floor']['unlit'] = False
    s['lights'] = [dict(type='directional', direction=list(key_dir), intensity=key, color=[1, 1, 1], shadow=True, shadowScale=8)]
    if fill:
        s['lights'].append(dict(type='directional', direction=[-0.5, -0.6, -0.4], intensity=fill, shadow=False))
    s['ibl']['exponent'] = ibl
    s['items'] = [dict(usdz=f'{P.OUT}/_calib.usdz', position=[0, 0.2, 0])]
    return s


def measure(name):
    a = np.asarray(Image.open(f'{P.PREV}/calib_{name}.png').convert('RGB')).astype(int)
    H, W, _ = a.shape
    res = []
    for i in range(5):
        cx = int(W / 2 + (-0.9 + 0.45 * i) * W / 2.4); cy = H // 2
        r = int(0.2 * W / 2.4 * 0.95)
        yy, xx = np.mgrid[-r:r, -r:r]
        m = xx ** 2 + yy ** 2 < r * r
        patch = a[cy - r:cy + r, cx - r:cx + r][m]
        lum = patch @ np.array([0.3, 0.59, 0.11])
        o = np.argsort(lum)
        res.append(dict(lit=tuple(patch[o[-len(o) // 50:]].mean(0).astype(int)), mid=tuple(patch[o[len(o) // 2]]),
                        dark=tuple(patch[o[len(o) // 20]])))
    floor = tuple(a[8, W // 2])
    return res, floor


if __name__ == '__main__':
    P.make_rig_assets()
    runs = [('k1000', 1000, -20), ('k3000', 3000, -20), ('i0', 0.001, 0), ('i1', 0.001, 1)]
    P.run_job([scene(*r) for r in runs], 'calib')
    for n, *_ in runs:
        res, fl = measure(n)
        print(n, 'floor', fl)
        for i, r in enumerate(res):
            print('   ', ['grey', 'blue', 'cream', 'yellow', 'red'][i], r)
