#!/usr/bin/env python3
"""fit_tr.py — fit Turkey's weight and archetype tilt (M11) to the phone's Turkey board under the v2 world.

The phone guards on Turkey (SocialCalibrationTests, calib_v2.phone_guards), measured at the phone's world age (v2's world
is 19 weeks younger than the original's, so every phone moment is shifted by +19 weeks):
  rank at L62 at 04:31 TRT = 455 +- 15 %            (T6 acceptance)
  Turkey #2..#7 within 40 % of 3323 3193 2575 2401 1604 1349
  the ranks at L62..L84 through the day within 15 % of 455 448 438 412 396 386 375, slope 2.7 .. 4.6 places per level
Grid over the tilt (low = dabbler and casual, high = regular, returner and enthusiast; grinders and tourists keep 1), and for
each tilt the TR weight by secant iterations to rank 455. Prints one line per grid point, numbers only.
    python3 design/social/tools/v2/fit_tr.py [OUT.json] [--low 1,1.5,2] [--high 1,0.5,0.3]
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..')))
sys.path.insert(0, HERE)
from socialsim import v2 as V2                                                   # noqa: E402
V2.apply(['M11'])                                     # the tilt is set here, per grid point
from socialsim import population as Pp, data as D                                # noqa: E402
import calib_v2 as C                                                             # noqa: E402

ARGS = sys.argv[1:]
OUT = next((a for a in ARGS if a.endswith('.json')), None)
LOW = [float(x) for x in ARGS[ARGS.index('--low') + 1].split(',')] if '--low' in ARGS else [1.0, 1.3, 1.6, 2.0]
HIGH = [float(x) for x in ARGS[ARGS.index('--high') + 1].split(',')] if '--high' in ARGS else [1.0, 0.6, 0.4, 0.3, 0.2]
T0 = time.time()


def set_tr(w, low, high):
    for r in D.COUNTRY_ROWS:
        if r.iso == 'TR':
            r.weight = w
    Pp.ROW_TILT = {'TR': dict(dabbler=low, casual=low, regular=high, returner=high, enthusiast=high)}
    Pp.refresh_tables()


def measure(w, low, high, full=False):
    set_tr(w, low, high)
    W = Pp.World()
    W.extend_to(C.PHONE_T + 86400)
    rk = W.rank_of_level(62, C.PHONE_T, 'TR')
    if not full:
        return rk, None
    return rk, C.phone_guards(W)


def fit(low, high, w0):
    hist = []
    w = w0
    rk, _ = measure(w, low, high)
    hist.append((w, rk))
    for _ in range(5):
        if abs(rk - 455) / 455 <= 0.02:
            break
        if len(hist) == 1:
            w2 = w * 455.0 / rk
        else:
            (wa, ra), (wb, rb) = hist[-2], hist[-1]
            w2 = wb + (455 - rb) * (wb - wa) / (rb - ra) if rb != ra else wb * 455.0 / rb
        w2 = max(0.02, min(3.0, w2))
        w = round(w2, 4)
        rk, _ = measure(w, low, high)
        hist.append((w, rk))
    best = min(hist, key=lambda x: abs(x[1] - 455))
    return best[0], hist


def main():
    res = []
    w0 = 0.36
    for high in HIGH:
        for low in LOW:
            w, hist = fit(low, high, w0)
            rk, g = measure(w, low, high, full=True)
            tr = g['turkey']
            sl = g['turkeySlope']
            top = tr['top7']
            rel = [round((top[k] - tr['phoneTop7'][k]) / tr['phoneTop7'][k], 2) for k in range(1, 7)] if len(top) == 7 else None
            ok = tr['ok'] and tr['top2to7_within40'] and sl['ok'] and g['world']['ok']
            row = dict(low=low, high=high, w=w, rank=rk, top7=top, rel2to7=rel, ranks=sl['ranks'], slope=sl['slope'],
                       slopeOk=sl['ok'], top40=tr['top2to7_within40'], world=g['world']['ok'], joined=tr['joined'], ok=ok,
                       iters=len(hist))
            res.append(row)
            print('[%4.0fs] low %.2f high %.2f w %.4f rank %d slope %.2f %s top2-7 %s %s world %s joined %d -> %s' % (
                time.time() - T0, low, high, w, rk, sl['slope'], 'ok' if sl['ok'] else 'no', rel,
                'ok' if tr['top2to7_within40'] else 'no', g['world']['ok'], tr['joined'], 'OK' if ok else '-'), flush=True)
            w0 = w
            if OUT:
                with open(OUT, 'w') as f:
                    json.dump(res, f, indent=1)


if __name__ == '__main__':
    main()
