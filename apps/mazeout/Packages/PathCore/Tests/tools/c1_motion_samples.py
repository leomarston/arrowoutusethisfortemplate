#!/usr/bin/env python3
"""C1 (SPEC-architecture §4.16): the measured sample points every Motion curve is tested against.

Reads the motion analyst's raw outputs (research/motion-tools/out/*.txt, read-only) plus the tables quoted from
research/motion.md / research/tutorials.md, and writes Packages/PathCore/Tests/Fixtures/c1_motion_samples.json:
    {"<curve>": [{"t": .., "v": .., "tol": .., "src": ".."}, ...], ...}
With --tracks it also prints the averaged key tracks that are embedded in Sources/PathCore/Motion/Curves*.swift, so every
number there is reproducible from the raw files (python3 Packages/PathCore/Tests/tools/c1_motion_samples.py --tracks).
Standard library only.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))          # apps/mazeout
OUT = os.path.join(ROOT, "research", "motion-tools", "out")
FIX = os.path.join(HERE, "..", "Fixtures", "c1_motion_samples.json")
F = 1.0 / 60.0


def lines(name):
    with open(os.path.join(OUT, name)) as f:
        return f.read().splitlines()


def ripple(name, onset, lum_col):
    """(t since the first ripple frame, edge radius pt, disc luminance) while the ripple is visible."""
    out = []
    for ln in lines(name):
        m = re.match(r"\s*([\d.]+) edge_r ([\d.]+)\s+L\(r=0,3,6..\): \[([^\]]+)\]", ln)
        if not m:
            continue
        t, r = float(m.group(1)), float(m.group(2))
        lum = [int(x) for x in m.group(3).split(",")]
        if t + 1e-6 < onset or r < 5:
            continue
        out.append((round(t - onset, 3), r, lum[lum_col]))
    return out


def blocker_flash():
    """S1-L47-bump-1, contact 0.449: blocker red channel / 237 and the ✖ badge opacity from its centre pixel."""
    flash, badge = [], []
    for ln in lines("blockerflash_L47.txt")[1:]:
        m = re.match(r"([\d.]+) \((\d+), \d+, \d+\) \((\d+), (\d+), (\d+)\)", ln)
        if not m:
            continue
        t = float(m.group(1)) - 0.449
        if t < -1e-6:
            continue
        flash.append((round(t, 3), int(m.group(2)) / 237.0))
        g = int(m.group(4))
        badge.append((round(t, 3), g))
    return flash, badge


def vignette_edge():
    """S1-L47-bump-1 left edge row-mean at x = 0.2 pt: overlay alpha = 1 − G/254 (red over white)."""
    out = []
    started = False
    for ln in lines("bumpfx_v552.txt"):
        m = re.match(r"\s+([\d.]+)\s+\((\d+),(\d+),(\d+)\)", ln)
        if not m:
            if started:
                break
            continue
        t = float(m.group(1))
        if t + 1e-6 < 0.449:
            continue
        started = True
        out.append((round(t - 0.449, 3), round(1 - int(m.group(3)) / 254.0, 4)))
    return out


def hud_intro():
    rows = {}
    for ln in lines("hudfit_L48.txt"):
        if ln.startswith("data HUD:"):
            rows["hud"] = [(float(a), float(b)) for a, b in (p.split(":") for p in ln.split(":", 1)[1].split())]
        if ln.startswith("data booster:"):
            rows["booster"] = [(float(a), float(b)) for a, b in (p.split(":") for p in ln.split(":", 1)[1].split())]
    return rows


def hearts():
    """Heart widths (pt) after each heart's first frame (S1-L48-play-intro); settled width 26.5 pt."""
    seen = {}
    for ln in lines("hud_intro_L48.txt"):
        t = float(ln.split()[0])
        m = re.search(r"hearts \[(.*)\]$", ln)
        if not m or not m.group(1).strip():
            continue
        for x, w in re.findall(r"\((\d+), np\.float64\(([\d.]+)\)\)", m.group(1)):
            key = round(int(x) / 36.0)                                   # 216/251/287 → slots 6/7/8
            seen.setdefault(key, []).append((t, float(w)))
    out = []
    for k in sorted(seen):
        t0 = seen[k][0][0]
        out.append([(round(t - t0, 3), round(w / 26.5, 4)) for t, w in seen[k] if t - t0 <= 0.40])
    return out


def intro_zoom():
    out = []
    for ln in lines("introfit_L48.txt"):
        m = re.match(r"\s+([\d.]+)\s+([\d.]+)$", ln)
        if m:
            out.append((round(float(m.group(1)) - 0.375, 3), float(m.group(2))))
    return out


def hand():
    out = []
    for ln in lines("hand_YTA.txt"):
        m = re.match(r"([\d.]+) hand x [\d-]+ y [\d-]+ h (\d+)", ln)
        if m:
            out.append((round(float(m.group(1)) - 0.80, 3), int(m.group(2)) / 98.0))
    return out


def key_track():
    """L33 key flight, relative to the tap release 0.52 (motion.md §5.2) and to the resting key centre (74.2, 448.6)."""
    out = []
    for ln in lines("keytrack_L33.txt"):
        m = re.match(r"([\d.]+) key centre \(\s*([\d.]+),\s*([\d.]+)\) px\s+(\d+)", ln)
        if m:
            out.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), int(m.group(4))))
    return out


def box_shards():
    out = []
    for ln in lines("boxbreak_L50.txt")[1:]:
        m = re.match(r"([\d.]+)\s+[\d.]+ c=\(([\d.]+),([\d.]+)\)", ln)
        if m:
            out.append((float(m.group(1)), float(m.group(3))))
    return out


def win_dim():
    out = []
    for ln in lines("winscan_v552.txt")[1:]:
        p = ln.split()
        if len(p) > 2:
            try:
                out.append((float(p[0]), float(p[1])))
            except ValueError:
                pass
    return out


def main():
    fx = {}

    # ExitKinematics: motion.md §3.3 table (pass 2, 11 exits) and the architecture's pass-1 table (§4.16).
    fx["exit_T_pass2"] = [{"t": d, "v": T, "tol": 0.003, "src": "motion.md §3.3 T(d)"} for d, T in
                          [(0.5, .043), (1, .072), (2, .115), (3, .150), (4, .181), (5, .209), (6, .235), (8, .283),
                           (10, .326), (12, .367), (15, .424), (20, .513), (25, .596), (30, .676), (40, .827),
                           (50, .973), (60, 1.115), (80, 1.393)]]
    fx["exit_v_pass2"] = [{"t": t, "v": v, "tol": 0.06, "src": "motion.md §3.3 velocity row"} for t, v in
                          [(0, 7.7), (.05, 16.4), (.1, 24.0), (.2, 36.3), (.3, 45.6), (.5, 57.8), (.7, 64.8), (1.0, 70.0),
                           (1.5, 72.9)]]
    fx["exit_T_pass1"] = [{"t": d, "v": T, "tol": 0.003, "src": "SPEC-architecture §4.16 (motion pass 1)"} for d, T in
                          [(1, .078), (5, .215), (10, .331), (20, .518), (40, .836)]]

    # Exit colour ramp (colourramp.txt P01, fitted release 1.942; G channel fraction of #10A2EF) + motion.md §3.2 L50.
    p01 = [(1.964, 0x41), (1.980, 0x62), (1.997, 0x80), (2.013, 0x95), (2.030, 0xA2), (2.047, 0xA7), (2.080, 0xA8)]
    fx["exit_colour"] = [{"t": round(t - 1.942, 3), "v": round((g - 0x0F) / (0xA7 - 0x0F), 3), "tol": 0.05,
                          "src": "colourramp.txt P01"} for t, g in p01]
    fx["exit_colour"] += [{"t": t, "v": v, "tol": 0.11, "src": "motion.md §3.2 L50 (release ±1 frame)"} for t, v in
                          [(.023, .31), (.04, .70), (.07, .90), (.09, 1.0)]]

    # Ripple: three clips, t from the first ripple frame.
    rip = {"L33": ripple("ripple_L33.txt", 0.532, 0), "P02A": ripple("ripple_P02A.txt", 0.499, 0),
           "L35": ripple("ripple_L35.txt", 0.266, 1)}
    fx["ripple_radius"] = [{"t": t, "v": r, "tol": 1.1, "src": "ripple_%s.txt" % k} for k, s in rip.items() for t, r, _ in s]
    fx["ripple_lum"] = [{"t": t, "v": l, "tol": 5.0, "src": "ripple_%s.txt" % k} for k, s in rip.items() for t, _, l in s]

    # Bump (v552): the out-duration law's three observations, the return, the colours, the badge, the vignette.
    fx["bump_out"] = [{"t": 3.58, "v": 0.165, "tol": 0.004, "src": "bumpfit_v552 bump-1"},
                      {"t": 1.36, "v": 0.107, "tol": 0.004, "src": "bumpfit_v552 bump-2"},
                      {"t": 0.41, "v": 0.084, "tol": 0.004, "src": "motion.md §4 YT-B"}]
    fx["bump_mark"] = [{"t": round(k * F, 4), "v": round(r / 238.0, 4), "tol": 0.02, "src": "motion.md §4 marked R per 1/60 s"}
                       for k, r in enumerate([0, 13, 30, 93, 140, 190, 221, 235, 237])]
    flash, badge = blocker_flash()
    fx["bump_blocker"] = [{"t": t, "v": round(v, 4), "tol": 0.03, "src": "blockerflash_L47.txt"} for t, v in flash if t <= 0.40]
    fx["bump_badge_alpha"] = [{"t": t, "v": round(min(1.0, max(0.0, (254 - g) / (254.0 - 38.0))), 3), "tol": 0.06,
                               "src": "blockerflash_L47.txt badge centre G"} for t, g in badge if 0.03 <= t <= 0.45]
    fx["vignette_edge"] = [{"t": t, "v": a, "tol": 0.012, "src": "bumpfx_v552 S1-L47 left edge x=0.2pt"} for t, a in vignette_edge()]
    fx["vignette_depth"] = [{"t": d, "v": a, "tol": 0.012, "src": "motion.md §4 vignette row"} for d, a in
                            [(0, .42), (5, .37), (10, .31), (20, .22), (30, .16), (45, .08)]]
    fx["heart_break_dy"] = [{"t": round(t - 0.449, 3), "v": round(y - 92.1, 2), "tol": 1.2, "src": "bumpfx_v552 heart 3 centroid"}
                            for t, y in [(0.466, 90.5), (0.483, 88.9), (0.499, 87.6), (0.516, 86.6), (0.532, 85.8),
                                         (0.549, 85.3), (0.566, 85.1), (0.582, 85.1), (0.616, 86.1), (0.632, 86.9),
                                         (0.649, 88.1), (0.666, 89.5), (0.682, 91.2), (0.699, 93.3)]]

    # HUD intro (S1-L48-play-intro): pause-button top y and left booster right x, clip time; the cut is 0.375.
    hi = hud_intro()
    fx["hud_drop"] = [{"t": round(t - 0.375, 3), "v": y, "tol": 5.5, "src": "hudfit_L48 HUD"} for t, y in hi["hud"] if t >= 1.414]
    fx["booster_slide"] = [{"t": round(t - 0.375, 3), "v": x, "tol": 2.6, "src": "hudfit_L48 booster"} for t, x in hi["booster"]]
    hs = hearts()
    fx["heart_pop"] = [{"t": t, "v": v, "tol": 0.075, "src": "hud_intro_L48 heart %d" % (i + 1)} for i, h in enumerate(hs) for t, v in h]
    fx["heart_stagger"] = [{"t": i, "v": v, "tol": 0.017, "src": "hud_intro_L48"} for i, v in enumerate([0.0, 0.099, 0.216])]
    fx["big_timer"] = [{"t": t, "v": v, "tol": 0.001, "src": "SPEC-architecture §4.16 (motion pass 1, L32)"} for t, v in
                       zip([0, .0415, .083, .1245, .166, .2075, .249], [3.5, 2.65, 2.2, 1.6, 1.12, 0.8, 1.0])]
    fx["intro_zoom"] = [{"t": t, "v": s, "tol": 0.004, "src": "introfit_L48.txt"} for t, s in intro_zoom()]
    fx["build_in_t50"] = [{"t": n, "v": v, "tol": 0.05, "src": "introdraw2_L48 summary (median n)"} for n, v in
                          [(3, 0.541 - 0.375), (6, 0.582 - 0.375), (10, 0.624 - 0.375)]]
    fx["build_in_t98"] = [{"t": n, "v": v, "tol": 0.05, "src": "introdraw2_L48 summary (median n)"} for n, v in
                          [(3, 0.765 - 0.375), (6, 0.849 - 0.375), (10, 0.949 - 0.375)]]

    # Tutorial hand + caption (YT-A 25 fps; tutorials.md §3): t from the hand's first frame 0.80.
    fx["hand"] = [{"t": t, "v": round(v, 4), "tol": 0.03, "src": "hand_YTA.txt"} for t, v in hand() if t <= 2.70]
    fx["caption_in"] = [{"t": t, "v": v, "tol": 0.02, "src": "tutorials.md §3"} for t, v in
                        [(0, .7), (.04, .98), (.08, 1.10), (.12, 1.05), (.16, 1.0), (.20, 1.0)]]

    # Unlock overlay (tutorials.md §6, V1 L7, t from the Play tap).
    fx["unlock_icon"] = [{"t": t, "v": v, "tol": 0.02, "src": "tutorials.md §6"} for t, v in [(.42, 1.3), (.54, 1.0), (1.0, 1.0)]]

    # Key flight (keytrack_L33, release 0.52): key centre offset from its resting spot (74.2, 448.6).
    kt = key_track()
    fx["key_flight_y"] = [{"t": round(t - 0.52, 3), "v": round(y - 448.6, 1), "tol": 3.0 if t < 1.07 else 8.0,
                           "src": "keytrack_L33.txt"} for t, x, y, px in kt if 0.749 <= t <= 1.298 and px > 2000]
    fx["key_burst"] = [{"t": 0, "v": 1.14, "tol": 0.017, "src": "motion.md §5.2 tap → burst"}]

    # Debris: box shards centroid from rest (boxbreak_L50, break frame 0.433).
    bs = box_shards()
    b0 = [y for t, y in bs if abs(t - 0.433) < 1e-3][0]
    fx["box_shards_dy"] = [{"t": round(t - 0.433, 3), "v": round(y - b0, 1), "tol": 4.0, "src": "boxbreak_L50.txt"}
                           for t, y in bs if 0.466 <= t <= 0.766]

    # Win: the dim (winscan_v552 bgLum, W = 0.79) as black-overlay alpha.
    fx["win_dim"] = [{"t": round(t - 0.79, 3), "v": round(1 - l / 255.0, 4), "tol": 0.03, "src": "winscan_v552.txt"}
                     for t, l in win_dim() if 1.9 <= t <= 2.37]
    fx["win_panel"] = [{"t": 0, "v": 3.94, "tol": 0.001, "src": "motion.md §6.6"}]

    os.makedirs(os.path.dirname(FIX), exist_ok=True)
    with open(FIX, "w") as f:
        json.dump(fx, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", os.path.relpath(FIX, ROOT), {k: len(v) for k, v in fx.items()})

    if "--tracks" in sys.argv:
        # Mean of the three ripple clips on the 1/60 s grid (the embedded RippleCurve keys).
        grid = sorted({round(round(t / F) * F, 4) for s in rip.values() for t, _, _ in s})
        print("ripple (t, radius, lum):")
        for g in grid:
            rs = [r for s in rip.values() for t, r, _ in s if abs(t - g) < 0.009]
            ls = [l for s in rip.values() for t, _, l in s if abs(t - g) < 0.009]
            print("  (%.4f, %.2f, %.1f)" % (g, sum(rs) / len(rs), sum(ls) / len(ls)))
        print("vignette edge:", vignette_edge())
        print("blocker:", [(t, round(v, 3)) for t, v in flash if t <= 0.35])
        print("badge G:", [(t, g) for t, g in badge if t <= 0.45])
        print("hearts:", hs)
        grid = sorted({t for h in hs for t, _ in h})
        print("heart mean:")
        for g in grid:
            vs = [v for h in hs for t, v in h if abs(t - g) < 0.009]
            print("  (%.3f, %.4f)" % (g, sum(vs) / len(vs)))
        print("hand:", hand())


if __name__ == "__main__":
    main()
