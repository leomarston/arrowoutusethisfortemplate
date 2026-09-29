#!/usr/bin/env python3
"""tools/feelstrip.py — ours-vs-v552 frame strips at the measured beats, plus the numbers (PLAN-P T10; gates A2 / G3).

For a named moment (a preset in tools/feelstrip.json: the Pause punch, the tab push-slide, the HUD drop, the unlock dismiss,
the Sky Jump claim staging, the win-logo beats, the home badge loops, the V2 band punch) it
  1. finds the anchor in the v552 reference clip (research/video) and in OUR recording (auto: the dim's first frame, the
     first moving frame...; or --anchor-ours T),
  2. draws a two-row strip (v552 on top, ours below) of the frames nearest to anchor + each beat,
  3. measures the SAME quantity on both with the SAME code (panel scale fitted to its settled frame, page / HUD offset
     fitted to the settled frame, the dim ramp, per-region onsets, the event time, badge activity windows), and
  4. judges ours against v552 beat by beat with the preset's tolerance (±0.005 scale, ±2 pt, ±1 frame, ...).
The documented catalog numbers (motion-catalog.md, REFERENCE.md, hud_intro_L48) are used only by `selftest`, to prove the
measurement reproduces them on v552. Ours is never judged against a hand-typed table.

usage:
  feelstrip.py list
  feelstrip.py strip PRESET --ours OURS.mov|DIR|.npz [--anchor-ours T | --ours-window S E] [--pages N]
               [--out STRIP.png] [--json RESULT.json]
  feelstrip.py selftest [PRESET ...] [--json OUT]
        per preset: the auto anchor lands on the documented v552 anchor (±1 frame), the measurement reproduces the
        catalog, v552-vs-itself PASSES, and a negative control (the motion replaced by a hard cut) FAILS.
Exit: strip 0 = within tolerance (or look-only preset), 1 = out of tolerance, 2 = input error; selftest 0 = all pass.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blipscan  # noqa: E402  (frame reader: tools/vstream.swift)

ROOT = os.path.abspath(os.path.join(HERE, ".."))
PRESETS = os.path.join(HERE, "feelstrip.json")
W_PT = 393
FRAME = 1 / 60.0


def load_presets():
    with open(PRESETS) as f:
        return json.load(f)["presets"]


def frames_of(path, window=None, seek=False, width=W_PT):
    if seek:
        os.environ["VSTREAM_SEEK"] = "1"
    try:
        s, e = (window or (None, None))
        return list(blipscan.read_frames(path, width, s, e))
    finally:
        os.environ.pop("VSTREAM_SEEK", None)


def crop(img, rect):
    """rect in pt; the frame may be decoded at any width (px per pt = width / 393)."""
    k = img.shape[1] / float(W_PT)
    x, y, w, h = [int(round(v * k)) for v in rect]
    return img[max(0, y):y + h, max(0, x):x + w]


def lum(img):
    return img.astype(np.float32).mean(axis=2)


def nearest(frames, t):
    """The frame ON SCREEN at time t: the last frame shown at or before t (+4 ms jitter). Screen recorders (simctl, the
    phone) emit a frame only when the picture changes, so a missing sample means the previous frame is still showing."""
    ts = np.array([f[0] for f in frames])
    k = int(np.searchsorted(ts, t + 0.004, side="right")) - 1
    k = min(max(k, 0), len(frames) - 1)
    return k, frames[k]


# ------------------------------------------------------------------------------------------------------------ anchors
def detect_anchor(frames, spec):
    kind = spec.get("kind", "manual")
    if kind == "manual" or len(frames) < 3:
        return None
    rect = spec.get("rect", [0, 0, W_PT, 852])
    L = np.array([crop(f[1], rect).astype(np.float32).mean() for f in frames])
    if kind == "lum_drop":
        d = L[1:] - L[:-1]
        k = int(np.argmin(d)) + 1
        return frames[k][0] if d[k - 1] < -3 else None
    if kind == "motion_start":
        act = np.array([np.abs(crop(frames[i][1], rect).astype(np.int16) - crop(frames[i - 1][1], rect).astype(np.int16)).mean()
                        for i in range(1, len(frames))])
        on = np.nonzero(act > max(1.0, 0.1 * act.max()))[0]
        return frames[int(on[0]) + 1][0] if len(on) else None
    raise SystemExit(f"feelstrip: unknown anchor kind {kind}")


# ------------------------------------------------------------------------------------------------------------ measures
def fit_scale(img, ref, rect, center):
    """Scale s of img's content vs the settled ref about `center`: img(x) ~ ref(c + (x - c) / s), coarse-to-fine SAD."""
    k = img.shape[1] / float(W_PT)
    x, y, w, h = [int(round(v * k)) for v in rect]
    F = lum(img)[y:y + h, x:x + w]
    R = lum(ref)
    cx, cy = center[0] * k, center[1] * k
    yy, xx = np.mgrid[y:y + h, x:x + w].astype(np.float32)
    m = 6

    def err(s):
        src = np.stack([cy + (yy - cy) / s, cx + (xx - cx) / s])
        Rs = ndimage.map_coordinates(R, src, order=1, mode="nearest")
        return float(np.abs(F - Rs)[m:-m, m:-m].mean())
    grid = np.arange(0.90, 1.1001, 0.004)
    e = [err(s) for s in grid]
    s0 = grid[int(np.argmin(e))]
    fine = np.arange(s0 - 0.004, s0 + 0.00401, 0.0005)
    e = [err(s) for s in fine]
    k = int(np.argmin(e))
    if 0 < k < len(fine) - 1:          # parabola through the three best
        a, b, c = e[k - 1], e[k], e[k + 1]
        den = a - 2 * b + c
        return float(fine[k] + (0.5 * (a - c) / den * 0.0005 if den > 0 else 0))
    return float(fine[k])


def fit_shift(img, ref, rect, axis, rng):
    """Offset (pt) of img's content in rect vs ref: img(p) ~ ref(p - s) along axis; the ref is sampled from the whole frame."""
    k = img.shape[1] / float(W_PT)
    x, y, w, h = [int(round(v * k)) for v in rect]
    F = lum(img)[y:y + h, x:x + w]
    R = lum(ref)
    H, W = R.shape
    best = []
    for s in range(int(np.floor(rng[0] * k)), int(np.ceil(rng[1] * k)) + 1):
        # F(p) ~ R(p - s): p must lie in the rect and p - s inside the frame
        if axis == "x":
            x0, x1 = max(x, s), min(x + w, W + s)
            if x1 - x0 < max(20, 0.15 * w):
                continue
            a = F[:, x0 - x:x1 - x]
            b = R[y:y + h, x0 - s:x1 - s]
        else:
            y0, y1 = max(y, s), min(y + h, H + s)
            if y1 - y0 < max(10, 0.15 * h):
                continue
            a = F[y0 - y:y1 - y, :]
            b = R[y0 - s:y1 - s, x:x + w]
        best.append((float(np.abs(a - b).mean()), s))
    if not best:
        return None, None
    best.sort()
    e0, s0 = best[0]
    d = {s: e for e, s in best}
    if s0 - 1 in d and s0 + 1 in d:
        a, b, c = d[s0 - 1], e0, d[s0 + 1]
        den = a - 2 * b + c
        if den > 0:
            return (s0 + 0.5 * (a - c) / den) / k, e0
    return float(s0) / k, e0


def rgb_mean(img, rect):
    return float(crop(img, rect).astype(np.float32).mean())


def measure(frames, anchor, spec, pages=1, full=False):
    """Returns {"values": [(beat, value)], ...} for the measure kinds that have per-beat values, or a dict of named times.
    full=True (tab slide, our recording): the whole model window instead of the reference's partial beats."""
    kind = spec["kind"]
    if kind in ("scale", "shift_x", "shift_y", "ramp"):
        beats, settle, rng = spec["beats"], spec.get("settle", 0.3), spec.get("range")
        if full and spec.get("model"):
            T = spec["model"]["T"]
            beats = [round(i * FRAME, 4) for i in range(int((T + 0.05) / FRAME) + 1)]
            settle = T + 0.12
            rng = [rng[0] * pages, rng[1] * pages]
        _, (ts, ref) = nearest(frames, anchor + settle)
        pre = None
        if full and spec.get("model"):
            # the page that LEAVES, measured against the last frame before the slide: exact while the arriving page is
            # still mostly off screen (early u); the per-frame estimate with the lower match error wins
            kp, _ = nearest(frames, anchor)
            pre = frames[max(0, kp - 1)][1]
        out = []
        for b in beats:
            k, (t, img) = nearest(frames, anchor + b)
            if t < anchor - 0.004 and b >= 0:
                out.append((b, None))
                continue
            if kind == "scale":
                v = fit_scale(img, ref, spec["rect"], spec["center"])
            elif kind == "ramp":
                v = rgb_mean(img, spec["rect"])
            else:
                v, e = fit_shift(img, ref, spec["rect"], kind[-1], rng)
                if pre is not None:
                    v2, e2 = fit_shift(img, pre, spec["rect"], kind[-1], rng)
                    if v2 is not None and abs(v2) > 0.5 and (e is None or e2 < e):
                        v = v2 - np.sign(v2) * W_PT * pages
            out.append((b, None if v is None else round(v, 4)))
        res = {"values": out, "settled_t": ts}
        if kind == "ramp":
            vals = [v for _, v in out if v is not None]
            if vals:
                L0, L1 = vals[0], rgb_mean(ref, spec["rect"])
                res["fraction"] = [(b, None if v is None else round((v - L0) / (L1 - L0), 3) if L1 != L0 else None)
                                   for b, v in out]
                end = [b for b, f in res["fraction"] if f is not None and f >= 0.97]
                res["end"] = end[0] if end else None
        if kind == "shift_x" and spec.get("model"):
            res["model"] = model_fit(out, spec["model"], pages)
        return res
    if kind == "onsets":
        a_k, (ta, fa) = nearest(frames, anchor)
        res = {}
        for name, rect in spec["regions"].items():
            A = crop(fa, rect).astype(np.int16)
            on, settle, prev = None, None, A
            for t, img in frames:
                if t <= ta or t > ta + spec["horizon"]:
                    continue
                C = crop(img, rect).astype(np.int16)
                if on is None and np.abs(C - A).mean() > spec["thr"]:
                    on = round(t - ta, 4)
                if np.abs(C - prev).mean() > spec["thr"] / 4:
                    settle = round(t - ta, 4)
                prev = C
            res[f"{name}.onset"] = on
            res[f"{name}.settle"] = settle
        return {"times": res}
    if kind == "event":
        ev = []
        prev = None
        for t, img in frames:
            if t < anchor + spec["after"]:
                prev = img
                continue
            if prev is not None:
                d = np.abs(crop(img, spec["rect"]).astype(np.int16) - crop(prev, spec["rect"]).astype(np.int16)).mean()
                if d > spec["thr"]:
                    ev.append((round(t - anchor, 4), round(float(d), 1)))
            prev = img
            if len(ev) >= 3:
                break
        return {"events": ev, "times": {"panel": ev[1][0] if len(ev) > 1 else (ev[0][0] if ev else None),
                                        "removal": ev[0][0] if ev else None}}
    if kind == "activity":
        res = {}
        for name, rect in spec["regions"].items():
            act = []
            for i in range(1, len(frames)):
                d = np.abs(crop(frames[i][1], rect).astype(np.int16) - crop(frames[i - 1][1], rect).astype(np.int16)).mean()
                act.append((frames[i][0], d))
            wins, cur = [], None
            for t, d in act:
                if d > spec["thr"]:
                    if cur and t - cur[1] <= 0.3:
                        cur[1] = t
                    else:
                        cur = [t, t]
                        wins.append(cur)
            res[name] = [[round(a - anchor, 2), round(b - anchor, 2)] for a, b in wins if b - a >= 0.1]
        return {"windows": res}
    raise SystemExit(f"feelstrip: unknown measure {kind}")


def model_fit(values, model, pages):
    """Tab slide: fit x(t) = D (1 - (t - t0)/T)^e with D = ±393·pages, t0 free; residuals at the check points of u."""
    pts = [(b, v) for b, v in values if v is not None]
    if len(pts) < 3:
        return None
    T, e = model["T"], model["exp"]
    D = W_PT * pages * (1 if pts[0][1] >= 0 else -1)

    def x(t, t0):
        u = np.clip((t - t0) / T, 0, 1)
        return D * (1 - u) ** e
    best = None
    for t0 in np.arange(-0.6, 0.2, 0.001):
        r = [v - x(b, t0) for b, v in pts]
        err = float(np.sqrt(np.mean(np.square(r))))
        if best is None or err < best[0]:
            best = (err, t0)
    err, t0 = best
    checks = []
    for u in model["check_u"]:
        t = t0 + u * T
        near = [(abs(b - t), b, v) for b, v in pts if abs(b - t) <= 0.6 * FRAME]
        if near:
            _, b, v = min(near)
            checks.append((u, round(v - x(b, t0), 2)))
    return {"t0": round(float(t0), 4), "D": D, "rms": round(err, 2), "residual_at_u": checks}


# ------------------------------------------------------------------------------------------------------------ compare
def compare(spec, m_ref, m_ours):
    kind, tol = spec["kind"], spec.get("tol")
    rows, ok = [], True
    if kind == "shift_x" and spec.get("model"):
        # judged by the VERIFIED curve (V2 RMS 1.26 pt, v552 tail RMS 1.1 pt), not beat by beat: v552 only shows the tail
        mo = m_ours.get("model") or {"residual_at_u": []}
        for u, r in mo["residual_at_u"]:
            rows.append({"beat": f"u={u}", "v552": 0.0, "ours": r, "delta": r, "pass": abs(r) <= tol})
        ok = len(mo["residual_at_u"]) >= 3 and all(abs(r) <= tol for _, r in mo["residual_at_u"])
        return {"rows": rows, "pass": bool(ok), "model": m_ours.get("model")}
    if kind in ("scale", "shift_x", "shift_y"):
        for (b, v), (_, o) in zip(m_ref["values"], m_ours["values"]):
            d = None if v is None or o is None else round(o - v, 4)
            good = d is not None and abs(d) <= tol
            ok &= good if v is not None else True
            rows.append({"beat": b, "v552": v, "ours": o, "delta": d, "pass": good if v is not None else None})
    elif kind == "ramp":
        for (b, v), (_, o) in zip(m_ref["fraction"], m_ours["fraction"]):
            d = None if v is None or o is None else round(o - v, 3)
            good = d is not None and abs(d) <= tol
            ok &= good if v is not None else True
            rows.append({"beat": b, "v552": v, "ours": o, "delta": d, "pass": good if v is not None else None})
        ends = (m_ref.get("end"), m_ours.get("end"))
        good = None not in ends and abs(ends[1] - ends[0]) <= spec["end_tol"]
        ok &= good
        rows.append({"beat": "ramp end", "v552": ends[0], "ours": ends[1], "pass": good})
    elif kind in ("onsets", "event"):
        for k, v in m_ref["times"].items():
            o = m_ours["times"].get(k)
            d = None if v is None or o is None else round(o - v, 4)
            good = (v is None and o is None) or (d is not None and abs(d) <= tol)
            ok &= good
            rows.append({"beat": k, "v552": v, "ours": o, "delta": d, "pass": good})
    else:
        return {"rows": [], "pass": None, "note": "look-only preset"}
    return {"rows": rows, "pass": bool(ok)}


# ------------------------------------------------------------------------------------------------------------ strip
def draw_strip(preset, ref_frames, ref_anchor, ours_frames, ours_anchor, out, labels=("v552", "ours")):
    st = preset["strip"]
    sc = st.get("scale", 0.5)
    rows = []
    for frames, anchor in ((ref_frames, ref_anchor), (ours_frames, ours_anchor)):
        cells = []
        for b in st["beats"]:
            if frames and anchor is not None:
                _, (t, img) = nearest(frames, anchor + b)
                c = Image.fromarray(np.ascontiguousarray(crop(img, st["rect"]))).resize(
                    (int(st["rect"][2]), int(st["rect"][3])), Image.BILINEAR)
                lab = f"+{b:.3f} (frame {t - anchor:+.3f})"
            else:
                c = Image.new("RGB", (int(st["rect"][2]), int(st["rect"][3])), (230, 230, 230))
                lab = f"+{b:.3f}  n/a"
            cells.append((c.resize((max(1, int(c.size[0] * sc)), max(1, int(c.size[1] * sc))), Image.LANCZOS), lab))
        rows.append(cells)
    cw = max(c.size[0] for r in rows for c, _ in r)
    ch = max(c.size[1] for r in rows for c, _ in r)
    lab_w, lab_h, pad = 44, 14, 4
    S = Image.new("RGB", (lab_w + len(st["beats"]) * (cw + pad), 2 * (ch + lab_h + pad)), (255, 255, 255))
    d = ImageDraw.Draw(S)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 10)
    except Exception:
        font = ImageFont.load_default()
    for r, (cells, name) in enumerate(zip(rows, labels)):
        y = r * (ch + lab_h + pad)
        d.text((2, y + lab_h + 4), name, fill=(0, 0, 0), font=font)
        for k, (c, lab) in enumerate(cells):
            x = lab_w + k * (cw + pad)
            d.text((x, y + 1), lab, fill=(200, 0, 0), font=font)
            S.paste(c, (x, y + lab_h))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    S.save(out)
    return out


# ------------------------------------------------------------------------------------------------------------ commands
def ref_frames_of(preset):
    ref = preset["ref"]
    return frames_of(ref["clip"], ref["window"], ref.get("seek", False), preset.get("width", W_PT))[::preset.get("every", 1)]


def run_strip(name, preset, ours_frames, anchor_ours=None, pages=1, out=None, ref_cache=None):
    ref = preset["ref"]
    rf = ref_cache if ref_cache is not None else ref_frames_of(preset)
    ra = ref["anchor"] if ref.get("anchor") is not None else detect_anchor(rf, preset["anchor"])
    oa = anchor_ours if anchor_ours is not None else detect_anchor(ours_frames, preset["anchor"])
    res = {"preset": name, "ref_clip": ref["clip"], "ref_anchor": ra, "ours_anchor": oa}
    if oa is None:
        res["error"] = "no anchor in our recording (pass --anchor-ours T or --ours-window S E)"
        return res
    mr = measure(rf, ra, preset["measure"], 1)
    mo = measure(ours_frames, oa, preset["measure"], pages, full=True)
    res.update({"v552": mr, "ours": mo, "judge": compare(preset["measure"], mr, mo)})
    if out:
        res["strip"] = draw_strip(preset, rf, ra, ours_frames, oa, out)
    return res


def print_result(res):
    print(f"== {res['preset']}  v552 {res['ref_clip']} anchor {res['ref_anchor']}  ours anchor {res['ours_anchor']}")
    if res.get("error"):
        print("   ERROR", res["error"])
        return
    for r in res["judge"]["rows"]:
        print(f"   {str(r['beat']):>16s}  v552 {r['v552']}  ours {r['ours']}  Δ {r.get('delta')}  "
              f"{'ok' if r['pass'] else ('--' if r['pass'] is None else 'OUT')}")
    if res["ours"].get("model"):
        print(f"   model fit (ours): {res['ours']['model']}")
    if res["ours"].get("windows"):
        print(f"   windows v552 {res['v552']['windows']}\n   windows ours {res['ours']['windows']}")
    j = res["judge"]["pass"]
    print(f"   -> {'PASS' if j else ('LOOK' if j is None else 'FAIL')}" + (f"  strip {res['strip']}" if res.get("strip") else ""))


def cmd_strip(args):
    presets = load_presets()
    if args.preset not in presets:
        print(f"feelstrip: unknown preset {args.preset}; `feelstrip.py list`", file=sys.stderr)
        return 2
    p = presets[args.preset]
    if not os.path.exists(blipscan.resolve(args.ours)):
        print(f"feelstrip: missing {args.ours}", file=sys.stderr)
        return 2
    of = frames_of(args.ours, args.ours_window, width=p.get("width", W_PT))[::p.get("every", 1)]
    out = args.out or os.path.join(ROOT, "build", "p", "feelstrip", f"{args.preset}.png")
    res = run_strip(args.preset, p, of, args.anchor_ours, args.pages, out)
    print_result(res)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=1, default=str)
    if res.get("error"):
        return 2
    return 0 if res["judge"]["pass"] in (True, None) else 1


def hard_cut(frames, anchor, settle):
    """Negative control: every frame from the anchor to anchor + settle is replaced by the settled frame (no motion)."""
    _, (ts, ref) = nearest(frames, anchor + settle)
    return [(t, ref if anchor - 1e-6 <= t <= ts else img) for t, img in frames]


def cmd_selftest(args):
    presets = load_presets()
    names = args.presets or list(presets)
    report, all_ok = {}, True
    for name in names:
        p = presets[name]
        ref = p["ref"]
        if not os.path.exists(blipscan.resolve(ref["clip"])):
            print(f"SKIP {name}: missing {ref['clip']} (research/video is local-only)")
            all_ok = False
            continue
        rf = ref_frames_of(p)
        m = p["measure"]
        checks = {}
        det = detect_anchor(rf, p["anchor"])
        doc = ref.get("anchor")
        if p["anchor"].get("kind") != "manual" and doc is not None and not ref.get("partial"):
            checks["anchor"] = det is not None and abs(det - doc) <= 1.2 * FRAME
        anchor = doc if doc is not None else det
        mr = measure(rf, anchor, m)
        cat = m.get("catalog")
        # 1. the measurement reproduces the documented catalog on v552
        if m["kind"] in ("scale", "shift_x", "shift_y"):
            diffs = [None if v is None else round(v - c, 4) for (_, v), c in zip(mr["values"], cat)]
            checks["catalog"] = all(d is not None and abs(d) <= m["tol"] for d in diffs)
            mr["catalog_delta"] = diffs
        elif m["kind"] == "ramp":
            diffs = [None if v is None else round(v - c, 1) for (_, v), c in zip(mr["values"], cat)]
            checks["catalog"] = all(d is not None and abs(d) <= 6 for d in diffs)       # ±6/255 mean-RGB levels
            mr["catalog_delta"] = diffs
        elif m["kind"] in ("onsets", "event"):
            diffs = {k: (None if mr["times"].get(k) is None else round(mr["times"][k] - v, 3)) for k, v in cat.items()}
            mr["catalog_delta"] = diffs
            # different region definitions from the catalog's hand reading: informative within ±0.1 s, not a gate
            checks["catalog(±0.1 s, informative)"] = all(d is not None and abs(d) <= 0.1 for d in diffs.values())
        elif m["kind"] == "activity":
            mr["catalog"] = cat
        # 2. v552 vs itself passes; 3. a hard cut instead of the motion fails
        if m["kind"] != "activity":
            same = compare(m, mr, measure(rf, anchor, m))
            checks["identity passes"] = bool(same["pass"])
            settle = m.get("settle", m.get("horizon", m.get("after", 0.3) + 0.4))
            cut = hard_cut(rf, anchor, settle)
            mc = measure(cut, anchor, m)
            neg = compare(m, mr, mc)
            checks["hard-cut control fails"] = neg["pass"] is False
        ok = all(v for k, v in checks.items() if "informative" not in k)
        all_ok &= ok
        report[name] = {"anchor_doc": doc, "anchor_detected": det, "measured": mr, "checks": checks, "ok": ok}
        print(f"== {name}: {'OK' if ok else 'FAIL'}  anchor doc {doc} detected {det}  checks {checks}")
        if "catalog_delta" in mr:
            print(f"   v552 measured - catalog: {mr['catalog_delta']}")
        if m["kind"] == "activity":
            print(f"   windows {mr['windows']}\n   catalog {cat}")
        if m["kind"] in ("onsets", "event"):
            print(f"   measured times {mr['times']}")
    print("feelstrip selftest:", "PASS" if all_ok else "FAIL")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=1, default=str)
    return 0 if all_ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    s = sub.add_parser("strip")
    s.add_argument("preset")
    s.add_argument("--ours", required=True)
    s.add_argument("--anchor-ours", dest="anchor_ours", type=float)
    s.add_argument("--ours-window", dest="ours_window", type=float, nargs=2)
    s.add_argument("--pages", type=int, default=1, help="tab-slide: pages travelled (1 = adjacent tab, 2 = Shop <-> Leaderboard)")
    s.add_argument("--out")
    s.add_argument("--json")
    t = sub.add_parser("selftest")
    t.add_argument("presets", nargs="*")
    t.add_argument("--json")
    args = ap.parse_args(argv)
    if args.cmd == "list":
        for k, v in load_presets().items():
            print(f"{k:16s} {v['about']}\n{'':16s} ref {v['ref']['clip']}  measure {v['measure']['kind']}  source: {v['source']}")
        return 0
    if args.cmd == "strip":
        return cmd_strip(args)
    if args.cmd == "selftest":
        return cmd_selftest(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
