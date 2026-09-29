#!/usr/bin/env python3
"""Verifies the shipped audio (GAMEPROMPT §7.2 "Audio": the checker is part of the deliverable; targets in specs.py
from our SPEC-motion-audio). Adapted from apps/matchfactory/tools/audio/check.py (05424db): MF's timeTick-specific sizes
became the generic specs.SIZED, temp prefixes renamed, and an empty contract now FAILS instead of passing vacuously
(design/REUSE.md). Its self-test is check_selftest.py (every mutation must be caught).

Checks
 1. Every SoundID / MusicID case in the frozen audio contract (specs.CONTRACT) has its file (parsed, not copied).
 2. Format: Sounds mono / Music stereo, 44.1 kHz, 16-bit PCM.
 3. Length within +-5 % (or 10 ms) of the spec; music loops are exactly the spec's sample count and <= 60 s.
 4. Sample peak within +-1.5 dB of the target; true peak (4x) no more than 1.5 dB over it; music true peak <= ceiling
    and RMS within +-1 dB of the target.
 5. No clicks at the edges: one-shots start and end at zero; no DC offset; no NaN; not silent.
 6. Loops are seamless: (a) the wrap step x[-1] -> x[0] is no larger than the largest step in the 10 ms either side of
    the seam; (b) RMS of the window before the seam vs after it within +-1 dB (250 ms for SFX loops, one bar for music).
    Intro -> loop chains (specs.CHAINS) get the same two checks at the join.
 7. Provenance: no audio tool references research/ or sound-refs outside comments/docstrings, and no tool opens a
    .wav/.aif/.mov/.m4a input; with --reproduce, a fresh render in a temp dir is byte-identical to the shipped files
    (so every shipped file is the output of our synthesis code alone).
 8. SPEC-motion-audio §11.6 per-cue assertions (specs.CUE_ASSERT): uiClick 25-40 ms; clawTick <= 45 ms; streakPop
    0.18 s; coinCollect 2.9 s +-5 %, exactly 5 clink onsets at specs.COIN_CLINKS_S +-5 ms (3.15 kHz band envelope) and
    the glitter onset at 0 +-20 ms; unlockChime 2.2 +-0.1 s with a 1047 Hz partial present from 0.10 s.
 9. Music (SPEC-motion-audio MA2 / §11.5): while Tuning/audio.json music.enabled is false the contract's MusicIDs have
    no file and none is checked; any Music/*.wav is then a stray (fails).

    python3 tools/audio/check.py [--reproduce] [--report path.json] [--sounds DIR] [--music DIR] [--tools DIR]
Exit status 0 = all green.
"""
from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

import dsp
import specs

FAILS: list[str] = []
ROWS: list[dict] = []


def fail(msg: str) -> None:
    FAILS.append(msg)


def seam_metrics(a_end: np.ndarray, b_start: np.ndarray, win: int) -> dict:
    """a_end = the signal before the seam, b_start = after it (mono or stereo)."""
    A = a_end if a_end.ndim == 2 else a_end[:, None]
    B = b_start if b_start.ndim == 2 else b_start[:, None]
    local = max(8, dsp.n_of(0.010))
    step = float(np.max(np.abs(B[0] - A[-1])))
    around = np.concatenate([np.abs(np.diff(A[-local:], axis=0)).max(axis=1),
                             np.abs(np.diff(B[:local], axis=0)).max(axis=1)])
    max_local = float(np.max(around)) if around.size else 0.0
    r_a = dsp.rms_db(A[-win:])
    r_b = dsp.rms_db(B[:win])
    return {"step": step, "max_local_step": max_local, "continuous": step <= max(max_local, 2.0 / 32767),
            "rms_before_db": round(r_a, 2), "rms_after_db": round(r_b, 2), "rms_delta_db": round(r_b - r_a, 2)}


def check_sound(path: str, sid: str, length: float, peak_db: float, loop: bool, chained_intro: bool) -> dict:
    row = {"file": os.path.relpath(path, specs.APP), "id": sid}
    if not os.path.exists(path):
        fail(f"{sid}: missing {path}")
        row["status"] = "MISSING"
        return row
    x, sr, sw = dsp.read_wav(path)
    ok = True
    if sr != dsp.SR or sw != 2 or x.ndim != 1:
        fail(f"{sid}: format {sr} Hz, {8 * sw}-bit, {'mono' if x.ndim == 1 else 'stereo'} (want mono 44.1 kHz 16-bit)")
        row["status"] = "FAIL"
        return row
    dur = len(x) / sr
    tol = max(specs.LEN_TOL * length, 0.010)
    if abs(dur - length) > tol:
        fail(f"{sid}: length {dur:.3f} s, spec {length:.3f} s (+-{tol:.3f})")
        ok = False
    pk = dsp.a2db(dsp.sample_peak(x))
    tp = dsp.a2db(dsp.true_peak(x))
    if not np.all(np.isfinite(x)) or pk < -60:
        fail(f"{sid}: silent or non-finite")
        ok = False
    if abs(pk - peak_db) > specs.PEAK_TOL_DB:
        fail(f"{sid}: peak {pk:.2f} dBFS, target {peak_db:.1f} (+-{specs.PEAK_TOL_DB})")
        ok = False
    if tp > peak_db + specs.PEAK_TOL_DB:
        fail(f"{sid}: true peak {tp:.2f} dBTP exceeds target {peak_db:.1f} + {specs.PEAK_TOL_DB}")
        ok = False
    dc = float(np.mean(x))
    if abs(dc) > 2e-3:
        fail(f"{sid}: DC offset {dc:.4f}")
        ok = False
    edge = 2.5 / 32767
    if not loop:
        if abs(x[0]) > edge:
            fail(f"{sid}: starts at {x[0]:.4f} (click)")
            ok = False
        if not chained_intro and abs(x[-1]) > edge:
            fail(f"{sid}: ends at {x[-1]:.4f} (click)")
            ok = False
    row.update({"length_s": round(dur, 4), "spec_length_s": length, "peak_dbfs": round(pk, 2),
                "target_peak_dbfs": peak_db, "true_peak_dbtp": round(tp, 2), "rms_dbfs": round(dsp.rms_db(x), 2)})
    if loop:
        m = seam_metrics(x, x, dsp.n_of(0.25))
        # context: the largest 250 ms -> 250 ms RMS change ANYWHERE in the loop (a pad's own beating motion)
        W, H = dsp.n_of(0.25), dsp.n_of(0.01)
        xx = np.concatenate([x, x, x])
        n = len(x)
        m["motion_max_db_anywhere"] = round(max(abs(dsp.rms_db(xx[n + i:n + i + W]) - dsp.rms_db(xx[n + i - W:n + i]))
                                                for i in range(0, n, H)), 2)
        row["seam"] = m
        if not m["continuous"]:
            fail(f"{sid}: loop seam step {m['step']:.5f} > local max {m['max_local_step']:.5f}")
            ok = False
        if abs(m["rms_delta_db"]) > 1.0:
            fail(f"{sid}: RMS across the loop seam differs by {m['rms_delta_db']} dB")
            ok = False
    row["status"] = "ok" if ok else "FAIL"
    return row


def check_chain(intro: str, loop: str) -> dict:
    """The intro must hand over to the loop's sample 0 as if the loop had been playing: its last 30 ms must equal the
    loop's last 30 ms (so the join IS the loop's own seam, checked above at 250 ms), and the step must be continuous."""
    a, _, _ = dsp.read_wav(os.path.join(specs.SOUNDS_DIR, intro + ".wav"))
    b, _, _ = dsp.read_wav(os.path.join(specs.SOUNDS_DIR, loop + ".wav"))
    m = seam_metrics(a, b, dsp.n_of(0.25))
    k = dsp.n_of(0.03)
    tail_err = float(np.max(np.abs(a[-k:] - b[-k:])))
    m["tail_equals_loop_tail_lsb"] = round(tail_err * 32767, 2)
    ok = m["continuous"] and tail_err <= 2.5 / 32767
    if not m["continuous"]:
        fail(f"{intro} -> {loop}: join step {m['step']:.5f} > local max {m['max_local_step']:.5f}")
    if tail_err > 2.5 / 32767:
        fail(f"{intro} -> {loop}: the intro's last 30 ms differ from the loop's last 30 ms by {tail_err * 32767:.1f} LSB")
    return {"chain": f"{intro} -> {loop}", **m, "status": "ok" if ok else "FAIL"}


def check_music(mid: str) -> dict:
    bpm, bars, samples, rms_t, tp_ceiling = specs.MUSIC[mid]
    path = os.path.join(specs.MUSIC_DIR, mid + ".wav")
    row = {"file": os.path.relpath(path, specs.APP), "id": mid}
    if not os.path.exists(path):
        fail(f"music {mid}: missing {path}")
        row["status"] = "MISSING"
        return row
    x, sr, sw = dsp.read_wav(path)
    ok = True
    if sr != dsp.SR or sw != 2 or x.ndim != 2 or x.shape[1] != 2:
        fail(f"music {mid}: want stereo 44.1 kHz 16-bit")
        ok = False
    if len(x) != samples:
        fail(f"music {mid}: {len(x)} samples, spec loop {samples}")
        ok = False
    if len(x) / sr > 60.0:
        fail(f"music {mid}: longer than 60 s")
        ok = False
    rms = dsp.rms_db(x)
    tp = dsp.a2db(dsp.true_peak(x))
    if abs(rms - rms_t) > specs.MUSIC_RMS_TOL_DB:
        fail(f"music {mid}: RMS {rms:.2f} dBFS, target {rms_t} (+-{specs.MUSIC_RMS_TOL_DB})")
        ok = False
    if tp > tp_ceiling + 0.05:
        fail(f"music {mid}: true peak {tp:.2f} dBTP > {tp_ceiling}")
        ok = False
    bar = int(round(4 * 60.0 / bpm * sr))
    m = seam_metrics(x, x, bar)
    beat = seam_metrics(x, x, bar // 4)
    if not m["continuous"]:
        fail(f"music {mid}: seam step {m['step']:.5f} > local max {m['max_local_step']:.5f}")
        ok = False
    if abs(m["rms_delta_db"]) > 1.0:
        fail(f"music {mid}: RMS of the last bar vs the first bar differs by {m['rms_delta_db']} dB")
        ok = False
    per_bar = [round(dsp.rms_db(x[i * samples // bars:(i + 1) * samples // bars]), 2) for i in range(bars)]
    steps = np.abs(np.diff(per_bar + per_bar[:1]))
    row.update({"samples": len(x), "seconds": round(len(x) / sr, 4), "rms_dbfs": round(rms, 2),
                "target_rms_dbfs": rms_t, "true_peak_dbtp": round(tp, 2), "tp_ceiling_dbtp": tp_ceiling,
                "seam_bar": m, "seam_beat": beat, "per_bar_rms_dbfs": per_bar,
                "bar_to_bar_rms_step_db": {"seam": round(float(steps[-1]), 2), "max_inside": round(
                    float(np.max(steps[:-1])), 2), "median_inside": round(float(np.median(steps[:-1])), 2)},
                "status": "ok" if ok else "FAIL"})
    return row


def provenance(tools_dir: str) -> dict:
    bad = []
    for py in sorted(glob.glob(os.path.join(tools_dir, "*.py"))):
        if os.path.basename(py) == "check.py":
            continue  # the verifier holds the needles; it only reads Sounds/ and Music/
        tree = ast.parse(open(py, encoding="utf-8").read())
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    docs.add(id(first.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                s = node.value.lower()
                if "sound-refs" in s or "research" in s or any(s.endswith(e) for e in (".mov", ".m4a", ".aif")):
                    bad.append(f"{os.path.basename(py)}:{node.lineno}: {node.value!r}")
    for b in bad:
        fail(f"provenance: {b}")
    return {"tools_scanned": sorted(os.path.basename(p) for p in glob.glob(os.path.join(tools_dir, "*.py"))),
            "references_to_research": bad}


def band_env(x: np.ndarray, lo: float, hi: float, edge: float) -> np.ndarray:
    """Amplitude envelope of one band: a raised-cosine band mask in the frequency domain (edges `edge` Hz wide, so the
    envelope does not ring), then the analytic-signal magnitude."""
    n = len(x)
    X = np.fft.fft(x)
    f = np.abs(np.fft.fftfreq(n, 1.0 / dsp.SR))
    w = np.clip((f - (lo - edge)) / edge, 0.0, 1.0) * np.clip(((hi + edge) - f) / edge, 0.0, 1.0)
    w = np.sin(0.5 * math.pi * w) ** 2
    pos = np.fft.fftfreq(n, 1.0 / dsp.SR) > 0
    return np.abs(np.fft.ifft(X * w * np.where(pos, 2.0, 0.0)))        # one-sided spectrum = analytic signal


def band_onsets(e: np.ndarray, within_db: float) -> list[tuple[float, float]]:
    """Rises of an envelope whose peak comes within `within_db` of its maximum: [(onset s, rise dB)]. Onset = half-way
    up the rise from the preceding minimum; rise = the peak over the level 3 ms BEFORE that minimum (a strike that lands
    out of phase with a ring dips it and then recovers: a rise from the dip, but no louder than before). Small wiggles
    (prominence < 10 % of the maximum) are not rises."""
    from scipy.signal import find_peaks
    top = float(np.max(e))
    peaks, _ = find_peaks(e, height=top * dsp.db2a(-within_db), prominence=0.10 * top)
    out, prev = [], 0
    for p in peaks:
        m = prev + int(np.argmin(e[prev:p + 1]))
        half = 0.5 * (e[m] + e[p])
        k = m + int(np.argmax(e[m:p + 1] >= half))
        pre = float(e[max(m - dsp.n_of(0.003), 0)])
        out.append((float(k / dsp.SR), dsp.a2db(float(e[p]) / pre) if pre > 0 else 999.0))
        prev = p
    return out


def partial_peak(x: np.ndarray, band: tuple[float, float], t: tuple[float, float]) -> tuple[float, float]:
    """(T9) The strongest spectral peak inside `band` over the window t = (t0, t1) s: Hann window, zero-padded to >= 1 s
    (1 Hz bins), parabolic interpolation on the log magnitude. Returns (Hz, dB of that peak re the window's strongest
    peak at any frequency above 40 Hz)."""
    a, b = dsp.n_of(t[0]), min(len(x), dsp.n_of(t[1]))
    seg = x[a:b]
    if len(seg) < 16:
        return 0.0, -999.0
    nfft = 1 << max(16, int(math.ceil(math.log2(len(seg) * 4))))
    mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), nfft))
    f = np.fft.rfftfreq(nfft, 1.0 / dsp.SR)
    m = (f >= band[0]) & (f <= band[1])
    if not np.any(m) or np.max(mag[f > 40.0]) <= 0:
        return 0.0, -999.0
    idx = np.nonzero(m)[0]
    k = int(idx[np.argmax(mag[idx])])
    lm = np.log(mag[k - 1:k + 2] + 1e-20)
    den = lm[0] - 2 * lm[1] + lm[2]
    d = 0.5 * (lm[0] - lm[2]) / den if den != 0 else 0.0
    rel = dsp.a2db(float(mag[k]) / float(np.max(mag[f > 40.0])))
    return float((k + d) * dsp.SR / nfft), rel


def cue_assertions(sid: str, path: str) -> dict:
    """SPEC-motion-audio §11.6 on top of the generic checks (specs.CUE_ASSERT). Returns the measured values."""
    rules = specs.CUE_ASSERT.get(sid)
    if not rules or not os.path.exists(path):
        return {}
    x, sr, _ = dsp.read_wav(path)
    if x.ndim != 1 or sr != dsp.SR:
        return {}                                   # the generic check already failed the format
    got: dict = {}
    dur = len(x) / sr
    if "length" in rules:
        lo, hi = rules["length"]
        got["length_s"] = round(dur, 4)
        if not (lo - 1e-9 <= dur <= hi + 1e-9):
            fail(f"{sid}: length {dur * 1000:.1f} ms outside §11.6 {lo * 1000:.0f}-{hi * 1000:.0f} ms")
    peak = dsp.sample_peak(x)
    if "onsets" in rules:
        r = rules["onsets"]
        found = band_onsets(band_env(x, *r["band"], r["edge"]), r["within_db"])
        on = [t for t, _ in found]
        got["onsets_s"] = [round(t, 4) for t in on]
        got["rises_db"] = [round(min(d, 99.0), 2) for _, d in found]
        for t, d in found:
            if d < r["min_rise_db"]:
                fail(f"{sid}: the {r['name']} onset at {t:.4f} s raises the band only {d:+.2f} dB over the ring before "
                     f"it (a landing that does not sound; >= {r['min_rise_db']:.1f} dB)")
        want = list(r["at"])
        if len(on) != len(want):
            fail(f"{sid}: {len(on)} {r['name']} onsets at {got['onsets_s']}, §11.6 wants exactly {len(want)} at {want}")
        else:
            errs = [t - w for t, w in zip(on, want)]
            got["onset_errors_ms"] = [round(1000 * d, 2) for d in errs]
            for t, w, d in zip(on, want, errs):
                if abs(d) > r["tol"]:
                    fail(f"{sid}: {r['name']} onset at {t:.4f} s, §11.6 wants {w:.3f} +-{r['tol'] * 1000:.0f} ms")
    if "first" in rules:
        r = rules["first"]
        e = band_env(x, *r["band"], r["edge"])
        top = float(np.max(e))
        lvl = dsp.a2db(top / peak) if peak > 0 else -999.0
        t0 = int(np.argmax(e >= top * dsp.db2a(r["rel_db"]))) / sr
        got[r["name"]] = {"band_max_db_re_peak": round(lvl, 2), "first_s": round(t0, 4)}
        if lvl < r["min_db"]:
            fail(f"{sid}: {r['name']} is {lvl:.1f} dB re the file peak (absent; §11.6 needs >= {r['min_db']:.0f} dB)")
        elif abs(t0 - r["at"]) > r["tol"]:
            fail(f"{sid}: {r['name']} starts at {t0:.4f} s, §11.6 wants {r['at']:.2f} +-{r['tol'] * 1000:.0f} ms")
    if "onset" in rules:
        r = rules["onset"]
        k = int(np.argmax(np.abs(x) >= peak * dsp.db2a(r["rel_db"])))
        got["onset_s"] = round(k / sr, 4)
        if k / sr > r["max_s"] + 1e-9:
            fail(f"{sid}: onset at {k / sr * 1000:.1f} ms (first sample within {r['rel_db']:.0f} dB of the peak); the cue "
                 f"must sound on its beat, <= {r['max_s'] * 1000:.0f} ms")
    for r in rules.get("pitch", []):
        f_est, rel = partial_peak(x, r["band"], r["t"])
        cents = 1200.0 * math.log2(f_est / r["f"]) if f_est > 0 else 9999.0
        got["pitch " + r["name"]] = {"hz": round(f_est, 1), "cents": round(cents, 1), "db_re_strongest": round(rel, 1)}
        if rel < r["min_db"]:
            fail(f"{sid}: pitch {r['name']}: the strongest peak in {r['band'][0]:.0f}-{r['band'][1]:.0f} Hz is {rel:.1f} dB "
                 f"re the window's strongest (absent; needs >= {r['min_db']:.0f} dB)")
        elif abs(cents) > r["cents"]:
            fail(f"{sid}: pitch {r['name']}: measured {f_est:.1f} Hz = {cents:+.0f} cents off {r['f']:.1f} Hz "
                 f"(+-{r['cents']:.0f} cents)")
    if "hold" in rules:
        r = rules["hold"]
        e = band_env(x, *r["band"], r["edge"])
        seg = e[dsp.n_of(r["start"]):dsp.n_of(r["end"])]
        low = dsp.a2db(float(np.min(seg)) / float(np.max(e))) if np.max(e) > 0 else -999.0
        got[r["name"] + " min over hold"] = round(low, 2)
        if low < r["rel_db"]:
            fail(f"{sid}: {r['name']} drops to {low:.1f} dB of its maximum between {r['start']:.2f} and {r['end']:.2f} s "
                 f"(§11.6: present, >= {r['rel_db']:.0f} dB)")
    return got


def sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def reproduce() -> dict:
    tmp = tempfile.mkdtemp(prefix="pc-audio-repro-")
    try:
        env = dict(os.environ)
        subprocess.run([sys.executable, os.path.join(specs.HERE, "sfx.py"), "--out", os.path.join(tmp, "Sounds"),
                        "--no-manifest"], check=True, env=env, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, os.path.join(specs.HERE, "music.py"), "--out", os.path.join(tmp, "Music")],
                       check=True, env=env, stdout=subprocess.DEVNULL)
        shipped = sorted(glob.glob(os.path.join(specs.SOUNDS_DIR, "*.wav")) +
                         glob.glob(os.path.join(specs.MUSIC_DIR, "*.wav")))
        diffs = []
        for p in shipped:
            # map by role, not by the folder's own name (T9: a staged set may live in e.g. build/p/T9/wav)
            role = "Sounds" if os.path.dirname(os.path.abspath(p)) == os.path.abspath(specs.SOUNDS_DIR) else "Music"
            q = os.path.join(tmp, role, os.path.basename(p))
            if not os.path.exists(q) or sha(p) != sha(q):
                diffs.append(os.path.relpath(p, specs.APP))
        for d in diffs:
            fail(f"reproduce: {d} differs from a fresh render")
        return {"files": len(shipped), "identical": len(shipped) - len(diffs), "different": diffs}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reproduce", action="store_true")
    ap.add_argument("--report")
    ap.add_argument("--sounds", help="check another Sounds dir (mutation tests)")
    ap.add_argument("--music", help="check another Music dir (mutation tests)")
    ap.add_argument("--tools", help="scan another copy of tools/audio for provenance (mutation tests)")
    a = ap.parse_args(argv)
    if a.sounds:
        specs.SOUNDS_DIR = os.path.abspath(a.sounds)
    if a.music:
        specs.MUSIC_DIR = os.path.abspath(a.music)
    ids, contract_music = specs.contract_ids()
    if not ids and not contract_music:
        fail(f"the audio contract {specs.CONTRACT} declares no SoundID and no MusicID: nothing would be checked")
    music = specs.active_music_ids()          # [] while Tuning/audio.json music.enabled is false (§11.5)
    for mid in music:
        if mid not in specs.MUSIC:
            fail(f"music {mid}: music.enabled is true but the MusicID has no target in specs.py")
    music = [m for m in music if m in specs.MUSIC]
    for sid in ids:
        if sid not in specs.SFX:
            fail(f"{sid}: SoundID has no target in specs.py")
            continue
        _, length, peak, _ = specs.SFX[sid]
        loop = sid in specs.LOOPS
        chained = sid in specs.CHAINS
        ROWS.append(check_sound(os.path.join(specs.SOUNDS_DIR, sid + ".wav"), sid, length, peak, loop, chained))
        before = len(FAILS)
        cue = cue_assertions(sid, os.path.join(specs.SOUNDS_DIR, sid + ".wav"))
        if cue:
            ROWS[-1]["spec_11_6"] = cue
            if len(FAILS) > before:
                ROWS[-1]["status"] = "FAIL"
        for vi in range(2, specs.VARIANTS.get(sid, 1) + 1):
            ROWS.append(check_sound(os.path.join(specs.SOUNDS_DIR, f"{sid}_v{vi}.wav"), f"{sid}_v{vi}", length,
                                    peak, loop, chained))
    for sid, sizes in specs.SIZED.items():
        if sid not in specs.SFX:
            fail(f"{sid}: SIZED names a SoundID with no target in specs.py")
            continue
        for name, size in sizes.items():
            ROWS.append(check_sound(os.path.join(specs.SOUNDS_DIR, name + ".wav"), name, specs.SIZED_LENGTH(size),
                                    specs.SFX[sid][2], False, False))
    chains = [check_chain(i, l) for i, l in specs.CHAINS.items()]
    mus = [check_music(m) for m in music]
    known = {r["file"] for r in ROWS} | {m["file"] for m in mus}
    strays = [os.path.relpath(p, specs.APP) for p in glob.glob(os.path.join(specs.SOUNDS_DIR, "*.wav")) +
              glob.glob(os.path.join(specs.MUSIC_DIR, "*.wav")) if os.path.relpath(p, specs.APP) not in known]
    for s in strays:
        fail(f"stray file not in the contract/specs: {s}")
    prov = provenance(os.path.abspath(a.tools) if a.tools else specs.HERE)
    repro = reproduce() if a.reproduce else None

    # --- print
    print(f"{'id':22} {'len s':>6} {'spec':>6} {'peak':>7} {'tgt':>6} {'TP':>7}  status")
    for r in ROWS:
        if "length_s" in r:
            extra = ""
            if "seam" in r:
                s = r["seam"]
                extra = (f"  seam step {s['step']:.5f}/{s['max_local_step']:.5f} rms {s['rms_delta_db']:+.2f} dB"
                         f" (motion anywhere <= {s['motion_max_db_anywhere']} dB)")
            print(f"{r['id']:22} {r['length_s']:6.3f} {r['spec_length_s']:6.3f} {r['peak_dbfs']:7.2f} "
                  f"{r['target_peak_dbfs']:6.1f} {r['true_peak_dbtp']:7.2f}  {r['status']}{extra}")
        else:
            print(f"{r['id']:22} {r['status']}")
        if "spec_11_6" in r:
            print(f"{'':22} §11.6 {json.dumps(r['spec_11_6'], ensure_ascii=False)}")
    for c in chains:
        print(f"chain {c['chain']:34} step {c['step']:.5f}/{c['max_local_step']:.5f}  intro tail = loop tail within "
              f"{c['tail_equals_loop_tail_lsb']} LSB  {c['status']}")
    for m in mus:
        if "rms_dbfs" in m:
            s = m["seam_bar"]
            print(f"music {m['id']:6} {m['samples']} samples {m['seconds']} s  RMS {m['rms_dbfs']} (target "
                  f"{m['target_rms_dbfs']})  TP {m['true_peak_dbtp']} (<= {m['tp_ceiling_dbtp']})  seam step "
                  f"{s['step']:.5f}/{s['max_local_step']:.5f}  bar RMS {s['rms_before_db']} -> {s['rms_after_db']} "
                  f"({s['rms_delta_db']:+.2f} dB)  {m['status']}")
        else:
            print(f"music {m['id']} {m['status']}")
    if not specs.music_enabled():
        print(f"music: disabled (Tuning/audio.json music.enabled false, §11.5): MusicIDs {contract_music} have no file")
    print(f"provenance: {len(prov['tools_scanned'])} tools scanned, {len(prov['references_to_research'])} references "
          f"to research/")
    if repro:
        print(f"reproduce: {repro['identical']}/{repro['files']} shipped files byte-identical to a fresh render")
    if a.report:
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump({"sounds": ROWS, "chains": chains, "music": mus, "provenance": prov, "reproduce": repro,
                       "fails": FAILS}, f, indent=1)
    if FAILS:
        print(f"\ncheck.py: {len(FAILS)} FAIL(S)")
        for m in FAILS:
            print("  - " + m)
        return 1
    print(f"\ncheck.py: all green ({len(ROWS)} sound files, {len(mus)} music loops, {len(chains)} chains)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
