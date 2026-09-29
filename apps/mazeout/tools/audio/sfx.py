#!/usr/bin/env python3
"""Renders every SoundID to App/Resources/Sounds/<id>.wav (mono, 44.1 kHz, 16-bit), from our own recipes.

T9 AUDIO-2 (owner item 6, 2026-09-28: "sounds are bad ... use the kit ... most sounds feel cheap"). The 9 cues are
rebuilt on the FULL kit the way apps/matchfactory's own cues are built (05424db sfx.py: layered pop + blip + fwip + air,
FM-bell doublets at +-4 cents, upper-partial rings, fluttered shimmer, small rooms and a plate): every cue is now a
transient (contact) + a body (tuned, with its own modal partials, each decaying on its own) + where the event rings, a
struck modal bell with detuned doublets, then a small room. Gentle saturation gives the low bodies harmonics a phone
speaker can reproduce. The beats, pitches, lengths and levels are unchanged: research/sounds.md §2 and SPEC-motion-audio
§11.2/§11.3 (the numbers only), so no contract, timeline or manifest change (SoundIDs, lengths, peaks, the 5 baked coin
landings are the same). Staged in tools/audio-t9 during the Wave-0 fence; A4 copies this folder's changed files over
tools/audio (sfx.py, specs.py, check.py, check_selftest.py) together with the WAVs.

Earlier history: adapted from apps/matchfactory/tools/audio/sfx.py (05424db): the helpers, the renderer (variants, sized
renders) and the manifest writer are kept verbatim; MF's cue recipes are not copied (they are its cues, not ours).

Inputs: none but maths and fixed seeds. Nothing is read from recordings (GAMEPROMPT §7.2: nothing may derive from the
original's sounds; check.py enforces it).

    python3 tools/audio/sfx.py                 # all sounds into App/Resources/Sounds (+ tools/audio/manifest.json)
    python3 tools/audio/sfx.py --out DIR tap   # one sound somewhere else
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Callable

import numpy as np

import dsp
import instruments as ins  # noqa: F401  (recipes use the shared patches: ins.marimba, ins.glock, ...)
import specs
from dsp import SR, db2a, n_of

# ----------------------------------------------------------------------------------------------------------------------
# helpers (verbatim from MF)


def buf(sid: str, length: float | None = None) -> np.ndarray:
    return np.zeros(n_of(length if length is not None else specs.SFX[sid][1]))


def nrm(x: np.ndarray, rms: float = 0.3) -> np.ndarray:
    """Normalises a noise component to a fixed RMS so the recipe's relative dB levels mean the same thing."""
    r = math.sqrt(float(np.mean(x * x)))
    return x * (rms / r) if r > 0 else x


def noise_sweep(n: int, rng, f0: float, f1: float, dur: float, q: float, kind: str = "pink", delay: float = 0.0,
                exp: bool = True) -> np.ndarray:
    src = dsp.pink(n, rng) if kind == "pink" else dsp.white(n, rng)
    fc = dsp.glide_exp(f0, f1, dur, n, delay) if exp else dsp.glide_lin(f0, f1, dur, n, delay)
    return nrm(dsp.svf(src, fc, q, "bp"))


def pentatonic_hz(lo: float, hi: float, root: str = "D") -> list[float]:
    """Major-pentatonic pitches in [lo, hi]: random 'pings' drawn from a scale sound like sparkle, not static."""
    r = dsp.midi(root + "0")
    out = []
    for m in range(r, 136):
        if (m - r) % 12 in (0, 2, 4, 7, 9):
            f = dsp.hz(m)
            if lo <= f <= hi:
                out.append(f)
    return out


def tail(x: np.ndarray, frac: float = 0.25) -> np.ndarray:
    """A short event's buffer must end at zero: fade its last `frac` (no truncated ring = no click)."""
    return dsp.fade(x, 0.0, max(frac * len(x) / SR, 0.002))


def ping(f: float, dur: float, attack: float, tau: float, harm: float = -18.0) -> np.ndarray:
    n = n_of(dur)
    y = dsp.osc_sin(f, n) + db2a(harm) * dsp.osc_sin(2.0 * f, n, 0.3)
    return tail(y * dsp.env_exp(n, attack, tau))


def crackle(n: int, rng, count: int, t0: float, t1: float, width: float = 0.002, hp_hz: float = 3000.0) -> np.ndarray:
    """Sparse crackle: `count` tiny white-noise bursts (so they carry real high-frequency energy), high-passed."""
    y = np.zeros(n)
    w = max(4, n_of(width))
    for at in rng.uniform(t0, t1, count):
        k = n_of(float(at))
        if k + w < n:
            y[k:k + w] += rng.uniform(0.3, 1.0) * dsp.white(w, rng) * np.hanning(w)
    return dsp.hp(y, hp_hz, order=2)


def room(x: np.ndarray, wet: float, rt: float = 0.5, seed: str = "sfxroom") -> np.ndarray:
    ir = dsp.make_ir(rt60=rt, predelay=0.010, seed=seed, stereo=False)
    return dsp.reverb(x, ir, wet)


def finish(sid: str, x: np.ndarray, fout: float = 0.008, fin: float = 0.0005, dc: bool = True,
           length: float | None = None) -> np.ndarray:
    """Pads/cuts to the spec length, removes DC, fades both edges (no clicks) and sets the spec's sample peak."""
    if length is None:
        length = specs.SFX[sid][1] if sid in specs.SFX else len(x) / SR
    y = dsp.pad_to(x, n_of(length))
    if dc:
        y = dsp.dc_block(y, 18.0)
    y = dsp.fade(y, fin, fout)
    return dsp.normalize_peak(y, specs.SFX[sid][2] if sid in specs.SFX else -12.0)


# ----------------------------------------------------------------------------------------------------------------------
# T9 building blocks (our own; the techniques of MF's kit: modal partials that each decay on their own, detuned doublets,
# contact transients, fluttered shimmer, small rooms)


def modal(f, n: int, modes: list[tuple[float, float, float]], rng, attack: float = 0.001, doublet_cents: float = 0.0,
          doublet_db: float = -9.0, delay: float = 0.0, hold: float = 0.0) -> np.ndarray:
    """A struck modal body: modes = [(ratio, gain dB, tau s)], each partial decaying on its own with a random start
    phase (a real bar/bell never starts all partials in phase). `f` may be a per-sample glide. doublet_cents > 0 adds,
    for every mode, a second copy detuned by that many cents at doublet_db: the slow beating of a real bell's split
    modes (the 'shimmer' of MF's +-4-cent FM-bell pairs), shallow enough that it never nulls the note. `hold` keeps the
    FIRST mode (the body) at full level that long before it decays (a key that bottoms out and stays down a moment);
    the upper modes decay at once."""
    y = np.zeros(n)
    fmax = float(np.max(f)) if np.ndim(f) else float(f)
    env_cache: dict[tuple[float, float, float], np.ndarray] = {}
    for ratio, gdb, tau in modes:
        if ratio * fmax > 0.45 * SR:
            continue
        h = hold if ratio == modes[0][0] else 0.0
        key = (attack, tau, h)
        if key not in env_cache:
            env_cache[key] = dsp.env_exp(n, attack, tau, hold=h, delay=delay)
        e = env_cache[key]
        y += db2a(gdb) * dsp.osc_sin(np.asarray(f) * ratio if np.ndim(f) else f * ratio, n, rng.random()) * e
        if doublet_cents > 0.0:
            fd = (np.asarray(f) if np.ndim(f) else f) * ratio * 2.0 ** (doublet_cents / 1200.0)
            y += db2a(gdb + doublet_db) * dsp.osc_sin(fd, n, rng.random()) * e
    return y


def contact(n: int, rng, centre: float, q: float, dur: float, gain_db: float = 0.0, at: float = 0.0,
            hp: float | None = None) -> np.ndarray:
    """The contact transient of a strike (finger on a key, a coin on a pill): a band-passed white-noise burst of `dur`
    seconds with a 0.1 ms rise and a fast exponential fall. Placed at `at` into a buffer of n samples."""
    k = max(n_of(0.004), n_of(dur * 6.0))
    b = dsp.bp(dsp.white(k, rng), centre, q) * dsp.env_exp(k, 0.0001, dur)
    if hp:
        b = dsp.hp(b, hp, order=2)
    y = np.zeros(n)
    dsp.place(y, db2a(gain_db) * nrm(tail(b, 0.3), 0.6), at)
    return y


def sheen(n: int, rng, lo: float, hi: float, flutter_hz: float, depth: float = 0.45) -> np.ndarray:
    """Air shimmer: band noise (soft spectral edges) with an amplitude flutter, like MF's mergeChime shimmer."""
    t = dsp.t_axis(n)
    x = nrm(dsp.spectral_band(n, rng, lo, hi, edge_oct=0.3), 0.3)
    return x * ((1.0 - depth) + depth * (0.5 + 0.5 * np.sin(2 * math.pi * flutter_hz * t + rng.random() * 6.28)))


def sat(x: np.ndarray, drive: float) -> np.ndarray:
    """Gentle tanh saturation, level-matched at the peak: a low body gains the harmonics a phone speaker can play."""
    p = float(np.max(np.abs(x))) or 1.0
    return dsp.softclip(x / p, drive) * p / (math.tanh(drive) / drive)


def plate(x: np.ndarray, wet: float, rt: float, seed: str) -> np.ndarray:
    ir = dsp.make_ir(rt60=rt, predelay=0.006, seed=seed, hf=0.75, lf=0.7, early=5, stereo=False)
    return dsp.reverb(x, ir, wet)


def restruck(freq: float, n: int, strikes: list[float], attack: float, tau: float) -> np.ndarray:
    """One modal partial of a small bell that is struck again while it still rings: a single phase-continuous sine whose
    amplitude ramps linearly from its decayed value back to 1 over `attack` at every strike, then decays exp(-t/tau).
    For the first strike this is exactly osc_sin * env_exp(attack, tau). Summing independent copies instead lets a new
    strike land out of phase with the ring and cancel it (at an 85 ms spacing a 3150 Hz strike is 270 deg off the ring)."""
    t = dsp.t_axis(n)
    env = np.zeros(n)
    a0 = 0.0
    for k, s0 in enumerate(strikes):
        s1 = strikes[k + 1] if k + 1 < len(strikes) else math.inf
        m = (t >= s0) & (t < s1)
        u = t[m] - s0
        env[m] = np.where(u < attack, a0 + (1.0 - a0) * u / attack, np.exp(-(u - attack) / tau))
        if s1 < math.inf:
            a0 = math.exp(-max(s1 - s0 - attack, 0.0) / tau) if s1 - s0 >= attack else a0 + (1.0 - a0) * (s1 - s0) / attack
    return dsp.osc_sin(freq, n) * env


def ends(x: np.ndarray, fout: float = 0.020) -> np.ndarray:
    """A partial placed with a fixed-length buffer must END at zero: a 20 ms raised-cosine fade on its last samples
    (cut while still ringing, a buffer leaves a step in the middle of the file: a click the edge check cannot see)."""
    return dsp.fade(x, 0.0, fout)


# ----------------------------------------------------------------------------------------------------------------------
# recipes: one per SoundID. Signature: r_<cue>(sid, v, **sized) -> mono float64 array at SR whose length is the spec
# length; `v` is the variant number (1 = <id>.wav). Pitches/beats in the comments = research/sounds.md §2 (numbers only).

Recipe = Callable[..., np.ndarray]
RECIPES: dict[str, Recipe] = {}


def r_ui_click(sid, v=1):
    """A small hollow key bottoming out: a 'tock' on F4 with a plastic 'clack' (v552: body 215-430 Hz, strongest
    ~345-352; broadband to ~8 kHz, centroid ~2.3-2.5 kHz; 20 ms above -20 dB). A tuned body with its own wood modes,
    held a moment as the key bottoms out, + a low settle + the key's plastic modes (a ~1.1 kHz clack, a ~4 kHz ring) +
    the finger contact; nothing above ~7 kHz."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v)
    f = dsp.glide_exp(368.0, 348.0, 0.012, n)                                  # the key lands, the pitch settles on F4
    body = modal(f, n, [(1.0, 0.0, 0.0042), (2.43, -11.0, 0.0028), (3.87, -18.0, 0.0017), (5.61, -25.0, 0.0010)],
                 rng, attack=0.0025, hold=0.004)
    settle = dsp.osc_sin(dsp.glide_exp(300.0, 262.0, 0.014, n), n, rng.random()) * dsp.env_exp(n, 0.0025, 0.0080,
                                                                                               delay=0.002)
    y = dsp.hp(sat(body + db2a(-12.0) * settle, 1.25), 95.0, order=2)         # harmonics for a phone speaker
    clack = nrm(dsp.lp(dsp.bp(dsp.white(n, rng), 1150.0, 1.0), 4800.0, order=3), 0.3) * dsp.env_exp(n, 0.0008, 0.0060)
    y += db2a(1.5) * clack                                                    # the plastic clack (~1.1 kHz mode)
    y += contact(n, rng, 2400.0, 1.3, 0.0007, -16.0)                           # the finger/key contact (~2.4 kHz)
    ring = nrm(dsp.bp(dsp.white(n, rng), 4000.0, 1.4), 0.3) * dsp.env_exp(n, 0.0006, 0.0030)
    y += db2a(9.5) * ring                                                      # the key's plastic ring (~4 kHz)
    return finish(sid, dsp.lp(y, 7000.0, order=2), fout=0.006)


def r_unlock_chime(sid, v=1):
    """A reveal: a low C2 'whomp' (harmonics so small speakers hear it) + a soft air swell, then a Cmaj7 that blooms:
    struck bells C6 at 0.10 s, E6 0.50 s, E7 0.60 s, G6 + B6 1.10 s (sounds.md §2.5) over a warm sustained pad of the
    same chord (G4 C5 E5 + C6 E6 G6 B6 with gently falling harmonics, chorused), on a plate."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v); y = np.zeros(n)
    fth = dsp.glide_exp(98.0, 65.4, 0.10, n)                                   # C2 thump, dropping onto C2
    thump = dsp.osc_sin(fth, n) * dsp.env_exp(n, 0.045, 0.042)
    thump += db2a(-18.0) * dsp.osc_sin(2.0 * fth, n, 0.2) * dsp.env_exp(n, 0.010, 0.035)
    y += db2a(-8.0) * sat(thump, 1.7)
    y += db2a(-25.0) * nrm(dsp.lp(dsp.white(n, rng), 420.0, order=2), 0.3) * dsp.env_exp(n, 0.008, 0.07)
    y += db2a(-30.0) * sheen(n, rng, 5000.0, 12000.0, 17.0) * dsp.env_ahr(n, 0.30, 0.50, 0.90, delay=0.08,
                                                                         curve="sine")
    # the pad: every chord tone a soft additive voice (harmonics 1..6) + a +6-cent twin, one slow bloom from 0.10 s
    harm = [(1, 0.0), (2, -9.0), (3, -14.0), (4, -19.0), (5, -23.0), (6, -27.0)]
    pad = np.zeros(n)
    for f, g in ((261.6, -10.0), (392.0, -11.0), (523.25, -8.0), (659.25, -9.0), (1046.5, 2.5), (1318.5, -0.5),
                 (1568.0, -10.0), (1975.5, -12.0)):
        for h, gh in harm:
            if f * h > 9000.0:
                continue
            for cents, gt in ((0.0, 0.0), (6.0, -4.0)):
                pad += db2a(g + gh + gt) * dsp.osc_sin(f * h * 2.0 ** (cents / 1200.0), n, rng.random())
    pad *= dsp.env_ahr(n, 0.07, 1.05, 0.40, delay=0.10, curve="sine")
    y += db2a(-22.0) * dsp.lp(pad, 5200.0)
    notes = ((1046.5, 0.10, 2.5), (1318.5, 0.50, -2.5), (2637.0, 0.60, -13.0), (1568.0, 1.10, -6.0), (1975.5, 1.10, -8.0))
    for f, at, g in notes:
        nb = n - n_of(at)
        strike = modal(f, nb, [(1.0, 0.0, 0.34), (2.76, -15.0, 0.12), (5.40, -24.0, 0.05), (8.93, -32.0, 0.025)], rng,
                       attack=0.060 if at < 0.2 else 0.003, doublet_cents=3.0, doublet_db=-6.0)
        dsp.place(y, ends(strike, 0.25), at, db2a(g - 20.0))
    y = plate(y, 0.20, 1.4, "t9-unlock")
    return finish(sid, y, fout=0.25)


def r_claw_token(sid, v=1):
    """The purple token pops in: a bright up-blip + sparkle arpeggio at the touch, then the token's soft 'fwump' (a
    swept puff of air with a cork-pop 'thoop', peaking as the token fills, ~0.08 s), a struck C6 bell (~1049 Hz) with
    doublets under a fluttered 3-10 kHz shimmer, and a second softer puff on E4/F#4 as it settles (~0.42 s; v552: the
    cue ends on a low 330-430 Hz body). sounds.md §2.1 cue 2: peak -2 dBFS, ~0.42 s above -20 dB, tail to 0.75 s."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v); y = np.zeros(n)
    fb = dsp.glide_exp(650.0, 845.0, 0.030, n)
    y += db2a(-14.0) * (dsp.osc_tri(fb, n) + db2a(-10.0) * dsp.osc_sin(2.0 * fb, n, 0.3)) * dsp.env_exp(n, 0.0015, 0.022)
    for k, f in enumerate((4186.0, 5274.0, 6272.0, 7902.0, 9397.0)):           # C8 E8 G8 B8 D9: a 30 ms up-sparkle
        dsp.place(y, db2a(-14.0 - 1.0 * k) * ping(f, 0.10, 0.0006, 0.022, harm=-30.0), 0.004 + 0.007 * k)
    y += db2a(-13.0) * sheen(n, rng, 3000.0, 10000.0, 19.0) * dsp.env_ahr(n, 0.030, 0.06, 0.30, curve="sine")
    y += db2a(-6.0) * modal(1049.0, n, [(1.0, 0.0, 0.14), (2.76, -8.0, 0.060), (5.40, -18.0, 0.025),
                                        (8.93, -28.0, 0.012)], rng, attack=0.002, doublet_cents=4.0, doublet_db=-7.0)

    def puff(at: float, dur: float, lo: float, hi: float, thoop: tuple[float, float], gain: float) -> None:
        k = n_of(dur)
        fc = np.interp(dsp.t_axis(k), [0.0, 0.45 * dur, dur], [lo, hi, lo])
        air = nrm(dsp.svf(dsp.pink(k, rng), fc, 0.7, "bp"), 0.3) * dsp.env_ahr(k, 0.40 * dur, 0.10 * dur, 0.50 * dur,
                                                                                curve="sine")
        th = dsp.osc_sin(dsp.glide_exp(thoop[0], thoop[1], 0.5 * dur, k), k, rng.random())
        th *= dsp.env_ahr(k, 0.35 * dur, 0.05 * dur, 0.60 * dur, curve="sine")
        dsp.place(y, db2a(gain) * tail(sat(air + db2a(-16.0) * th, 1.4), 0.2), at)

    puff(0.030, 0.110, 250.0, 1500.0, (95.0, 190.0), 4.0)                     # the token fills (~0.08 s)
    puff(0.360, 0.110, 300.0, 1100.0, (165.0, 330.0), -15.0)                  # it settles (~0.42 s)
    body = (dsp.osc_tri(329.6, n, rng.random()) + db2a(-2.0) * dsp.osc_tri(370.0, n, rng.random()))
    y += db2a(-24.0) * dsp.lp(body, 1400.0) * dsp.env_ahr(n, 0.04, 0.03, 0.14, delay=0.36, curve="sine")
    return finish(sid, room(y, 0.12, 0.55, "t9-token"), fout=0.05)


def r_claw_merge(sid, v=1):
    """The x-badge merges into the token: a thump gliding C#4 -> A3 (~275 -> 217 Hz) with an air 'whump' and a rising
    'boop' onto F5 (~686 Hz), then a soft bell tinkle C#6 ~1090 + F6 ~1371 Hz (v552's are ~35 cents flat of equal
    temperament, kept) and a 4.1 kHz tine (sounds.md §2.1 cue 3: 95 ms above -20 dB, the bells decay to ~1.2 s)."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v); y = np.zeros(n)
    fth = dsp.glide_exp(298.0, 216.0, 0.100, n)
    thump = dsp.osc_sin(fth, n) * dsp.env_exp(n, 0.0015, 0.040)
    thump += db2a(-12.0) * dsp.osc_sin(2.0 * fth, n, 0.1) * dsp.env_exp(n, 0.001, 0.014)
    y += sat(thump, 1.6)
    y += db2a(2.0) * nrm(dsp.bp(dsp.white(n, rng), 1200.0, 0.5), 0.3) * dsp.env_exp(n, 0.003, 0.020)
    y += contact(n, rng, 1600.0, 1.0, 0.0008, -12.0)
    fb = dsp.glide_exp(540.0, 686.0, 0.040, n)
    y += db2a(-2.0) * (dsp.osc_sin(fb, n, 0.3) + db2a(-14.0) * dsp.osc_sin(2.0 * fb, n, 0.1)) * dsp.env_exp(n, 0.004,
                                                                                                        0.030)
    for f, g in ((1090.0, 0.0), (1371.0, -1.5)):                           # a bright strike, then a long soft ring
        b = modal(f, n_of(1.15), [(1.0, 0.0, 0.035), (2.76, -12.0, 0.020), (5.40, -22.0, 0.010)], rng, attack=0.002,
                  doublet_cents=4.0, doublet_db=-10.0)
        b += db2a(-30.0) * dsp.osc_sin(f * 2.0 ** (2.0 / 1200.0), n_of(1.15), rng.random()) * dsp.env_exp(
            n_of(1.15), 0.004, 0.42)
        dsp.place(y, ends(b), 0.015, db2a(g - 10.0))
    dsp.place(y, ends(ins.kalimba(686.0, 1.0, key=(sid, "kal", v), length=0.9)), 0.030, db2a(-26.0))
    dsp.place(y, ping(4100.0, 0.30, 0.0008, 0.045, harm=-30.0), 0.017, db2a(-15.0))
    return finish(sid, room(y, 0.035, 0.45, "t9-merge"), fout=0.2)


def r_claw_tick(sid, v=1):
    """One Claw-bar count-up step: a buzzy harmonic tick on ~F5 700 Hz (v552 per-tick 668-709 Hz) - a DC-free pulse +
    triangle through a low-pass that snaps shut (a mechanical counter, not a beep) + a ratchet contact."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v)
    f, pw = 700.0, 0.32
    raw = 0.55 * (dsp.osc_square(f, n, 0.0, pw=pw) - (2.0 * pw - 1.0)) + 0.45 * dsp.osc_tri(f, n)
    tone = dsp.svf(raw, dsp.glide_exp(6000.0, 1700.0, 0.014, n), 1.1, "lp") * dsp.env_exp(n, 0.0005, 0.011)
    y = sat(tone, 1.2)
    y += db2a(-15.0) * dsp.osc_sin(2.31 * f, n, rng.random()) * dsp.env_exp(n, 0.0003, 0.0030)
    y += db2a(-14.0) * dsp.osc_sin(350.0, n, rng.random()) * dsp.env_exp(n, 0.0008, 0.006)   # the counter's body
    y += contact(n, rng, 3200.0, 1.6, 0.0006, -16.0)
    return finish(sid, y, fout=0.006)


def r_claw_complete(sid, v=1):
    """The bar is full: a round 'thunk-bong' on F#4 ~369 Hz, falling slightly (v552: 369 Hz with a fast ~900 Hz attack
    partial, 0.12 s above -20 dB) - a tuned wood/ceramic modal body, a soft low thud, a contact click, a small room."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v)
    f = dsp.glide_exp(382.0, 364.0, 0.10, n)
    body = modal(f, n, [(1.0, 0.0, 0.040), (2.44, -5.0, 0.013), (2.10, -14.0, 0.030), (4.60, -22.0, 0.005)], rng,
                 attack=0.0015)
    thud = dsp.osc_sin(dsp.glide_exp(200.0, 182.0, 0.05, n), n, 0.1) * dsp.env_exp(n, 0.002, 0.022)
    y = sat(body + db2a(-11.0) * thud, 1.3)
    y += contact(n, rng, 1800.0, 1.2, 0.0006, -11.0)
    return finish(sid, room(y, 0.08, 0.30, "t9-complete"), fout=0.03)


def r_streak_pop(sid, v=1):
    """A round bubble 'bloop' (v552: an onset falling from ~720 Hz onto D5 586 Hz over F#4 369 Hz, 0.13-0.16 s, with a
    bright broadband tick at the burst). One file for the 3 pops. No long sparkle: the 6.5-10 kHz sparkle on v552's
    pops 2-3 coincides with the coin cue's glitter starting between pops 1 and 2 (INFERRED from the timing), and our
    coinCollect starts at the same place."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v)
    f1 = dsp.glide_exp(760.0, 587.0, 0.032, n)                                 # "bl-": the drop onto D5
    top = dsp.osc_sin(f1, n, 0.0) * dsp.env_exp(n, 0.0015, 0.050)
    top += db2a(-10.0) * dsp.osc_sin(2.0 * f1, n, 0.25) * dsp.env_exp(n, 0.0010, 0.028)
    top += db2a(-17.0) * dsp.osc_sin(3.0 * f1, n, 0.6) * dsp.env_exp(n, 0.0010, 0.018)
    f2 = dsp.glide_exp(410.0, 369.5, 0.040, n)                                 # "-oop": F#4 under it
    low = dsp.osc_sin(f2, n, 0.5) * dsp.env_exp(n, 0.004, 0.055)
    y = sat(top + db2a(-2.5) * low, 1.35)
    wet = noise_sweep(n, rng, 1100.0, 2600.0, 0.012, 2.2, kind="white") * dsp.env_exp(n, 0.0004, 0.0045)
    y += db2a(-14.0) * wet                                                     # the wet "p" of the bubble
    y += contact(n, rng, 7800.0, 1.8, 0.0012, -2.0, hp=4500.0)                 # the bright burst tick
    return finish(sid, dsp.lp(room(y, 0.07, 0.25, "t9-pop"), 11000.0, order=2), fout=0.03)


COIN_VEL = [0.84, 0.92, 1.0, 0.94, 0.88]      # each coin lands with its own force (the 3rd hardest)
# the clinks' G7 (~3152 Hz) partial: (strike gain, strike tau s, ring gain, ring tau s). The strike part dies before the
# next landing (85 ms), so even summed copies could not cancel a landing; the ring is the ~32 dB/s tail. check_selftest
# sets (0, -, 0.40, 0.25) = the §11.3 draft's single slow partial to prove the checker still catches a silent landing.
COIN_G7 = (0.38, 0.035, 0.075, 0.27)


def struck(freq: float, n: int, strikes: list[float], attack: float, tau: float, vel: list[float]) -> np.ndarray:
    """restruck() with a velocity per strike: the ring is re-excited to vel[k] (never below what still rings)."""
    t = dsp.t_axis(n)
    env = np.zeros(n)
    a0 = 0.0
    for k, s0 in enumerate(strikes):
        s1 = strikes[k + 1] if k + 1 < len(strikes) else math.inf
        m = (t >= s0) & (t < s1)
        u = t[m] - s0
        top = max(vel[k], a0)
        env[m] = np.where(u < attack, a0 + (top - a0) * u / attack, top * np.exp(-(u - attack) / tau))
        if s1 < math.inf:
            a0 = top * math.exp(-max(s1 - s0 - attack, 0.0) / tau)
    return dsp.osc_sin(freq, n) * env


def r_coin_collect(sid, v=1):
    """The coins' glitter swell (6.5-6.9 kHz, from the cue start), a soft early bell pair G7 ~3.14 kHz + D9 ~9.3 kHz
    at 0.15 s, then ONE clink per landing coin at specs.COIN_CLINKS_S. A clink (sounds.md §2.3, v552 phone): a bright
    strike whose ~9.3 kHz partial leads (+ 5.2 kHz, a contact tick and air), over the G7 ~3152 Hz ring that is struck
    again at every landing and rings down ~32 dB/s after the last. Small room."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v); y = np.zeros(n)
    # (a) glitter: tuned grains (tiny two-partial tines, 5.9-7.5 kHz, densest around 6.6-6.9 kHz) + a fluttered sheen
    g = np.zeros(n)
    at = 0.0
    while at < 2.55:
        f = float(np.clip(rng.normal(6700.0, 380.0), 5700.0, 7600.0))
        k = n_of(0.030)
        grain = (dsp.osc_sin(f, k, rng.random()) + db2a(-14.0) * dsp.osc_sin(1.5 * f, k, rng.random()))
        dsp.place(g, grain * dsp.env_exp(k, 0.0015, 0.007), at, 0.65 * rng.uniform(0.45, 1.0))
        at += rng.exponential(1.0 / 110.0) if at > 0.0 else 0.0005
    glitter = g + 0.8 * sheen(n, rng, 6000.0, 7400.0, 23.0, depth=0.6) + 0.60 * sheen(n, rng, 9000.0, 15000.0, 29.0)
    y += db2a(-11.0) * glitter * dsp.env_points(n, [(0.0, 0.06), (0.12, 0.22), (0.26, 0.58), (0.43, 1.0), (1.0, 1.0),
                                                    (2.5, 0.0), (3.0, 0.0)], curve="exp")
    # (b) the soft early bell pair (a G7 bell with a D9 twelfth), struck once at 0.15 s
    for f, gdb in ((3140.0, -10.0), (9300.0, 2.0)):                          # ~12 dB under the clinks' own partials
        b = modal(f, n_of(0.62), [(1.0, 0.0, 0.15)], rng, attack=0.004, doublet_cents=5.0, doublet_db=-8.0)
        dsp.place(y, ends(b), 0.15, db2a(gdb - 12.0))
    # (c) the clinks: every mode ONE partial re-struck at each landing (restruck/struck: phase-continuous, so a landing
    # never cancels the ring); the bright 9.3 kHz strike leads, the G7 strike part dies within a landing, and a quiet
    # long G7 ring (~14 dB under the G7 strike) carries the tail
    f1 = 3150.0
    gs, ts, gr, tr = COIN_G7
    if gs > 0.0:
        y += gs * restruck(f1, n, specs.COIN_CLINKS_S, 0.002, ts)           # the strike's own G7 (fast)
    y += gr * restruck(f1, n, specs.COIN_CLINKS_S, 0.002, tr)               # the ring: ~32 dB/s after the last
    y += (1.00 * struck(2.96 * f1, n, specs.COIN_CLINKS_S, 0.0015, 0.055, COIN_VEL)
          + 0.20 * struck(1.65 * f1, n, specs.COIN_CLINKS_S, 0.0015, 0.030, COIN_VEL))
    tinks = pentatonic_hz(10000.0, 13500.0, "G")
    for j, s in enumerate(specs.COIN_CLINKS_S):
        y += COIN_VEL[j] * dsp.lp(contact(n, rng, 8000.0, 0.6, 0.0012, -9.0, at=s, hp=4500.0), 12000.0)
        dsp.place(y, ping(tinks[j % len(tinks)], 0.08, 0.0005, 0.018, harm=-40.0), s + 0.001, COIN_VEL[j] * db2a(-11.0))
    return finish(sid, room(y, 0.09, 0.60, "t9-coins"), fout=0.2)


def r_tap_tick(sid, v=1):
    """The owner's optional arrow-tap sound (MA3; rendered, unmapped by default): a tiny woody tick on ~D6, crisp
    enough to read under a finger, short enough to never smear a fast tap run."""
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "t9", v)
    f = dsp.glide_exp(1250.0, 1175.0, 0.006, n)
    body = modal(f, n, [(1.0, 0.0, 0.0045), (2.61, -12.0, 0.0018), (4.1, -22.0, 0.0010)], rng, attack=0.0004)
    y = sat(body, 1.15) + contact(n, rng, 4200.0, 1.2, 0.0004, -7.0)
    return finish(sid, y, fout=0.004)


RECIPES.update({"uiClick": r_ui_click, "unlockChime": r_unlock_chime, "clawToken": r_claw_token, "clawMerge": r_claw_merge,
                "clawTick": r_claw_tick, "clawComplete": r_claw_complete, "streakPop": r_streak_pop,
                "coinCollect": r_coin_collect, "tapTick": r_tap_tick})

# specs.SIZED: which keyword of the base recipe carries the size (e.g. {"timeTick": "D"}).
SIZED_KEYWORD: dict[str, str] = {}


def render_all(out_dir: str, only: list[str] | None = None) -> list[str]:
    ids, _ = specs.contract_ids()
    missing = [i for i in ids if i not in RECIPES]
    if missing:
        raise SystemExit(f"no recipe for SoundID(s): {missing}")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for sid in ids:
        if only and sid not in only and not any(o.startswith(sid) for o in only):
            continue
        path = os.path.join(out_dir, f"{sid}.wav")
        dsp.write_wav(path, RECIPES[sid](sid, 1))
        written.append(path)
        for vi in range(2, specs.VARIANTS.get(sid, 1) + 1):
            pv = os.path.join(out_dir, f"{sid}_v{vi}.wav")
            dsp.write_wav(pv, RECIPES[sid](sid, vi))
            written.append(pv)
        for name, size in specs.SIZED.get(sid, {}).items():
            pv = os.path.join(out_dir, f"{name}.wav")
            dsp.write_wav(pv, RECIPES[sid](sid, 1, **{SIZED_KEYWORD[sid]: size}))
            written.append(pv)
    return written


def write_manifest(path: str) -> None:
    """tools/audio/manifest.json: what the engine (A2) needs to know about the files, beyond the contract."""
    ids, _ = specs.contract_ids()
    mbus = specs.music_bus_ids()
    sounds = {}
    for sid in ids:
        cue, length, peak, tag = specs.SFX[sid]
        e = {"file": f"Sounds/{sid}.wav", "bus": "music" if sid in mbus else "sfx", "spec": cue,
             "length_s": length, "peak_dbfs": peak, "tag": tag}
        if sid in specs.LOOPS:
            e["loop"] = True
        if sid in specs.CHAINS:
            e["continues_into"] = specs.CHAINS[sid]
        if specs.VARIANTS.get(sid, 1) > 1:
            e["variants"] = [f"Sounds/{sid}.wav"] + [f"Sounds/{sid}_v{i}.wav" for i in
                                                      range(2, specs.VARIANTS[sid] + 1)]
        if sid in specs.SIZED:
            e["sized"] = {f"{size:.2f}": f"Sounds/{name}.wav" for name, size in specs.SIZED[sid].items()}
        if sid == "coinCollect":
            e["clinks_s"] = list(specs.COIN_CLINKS_S)   # the baked landings: schedule the cue so they meet the coins
        sounds[sid] = e
    mus = {}
    for mid in specs.active_music_ids():
        bpm, bars, samples, rms, tp = specs.MUSIC[mid]
        mus[mid] = {"file": f"Music/{mid}.wav", "bpm": bpm, "bars": bars, "loop_samples": samples,
                    "loop": [0, samples], "rms_dbfs": rms, "true_peak_ceiling_dbtp": tp}
    doc = {
        "generated_by": "tools/audio/sfx.py + tools/audio/music.py (our own synthesis; no recorded input)",
        "format": {"sounds": "mono 44.1 kHz 16-bit PCM", "music": "stereo 44.1 kHz 16-bit PCM"},
        "notes": [
            "continues_into: schedule the loop on the same player node right after the intro (sample-exact join).",
            "variants: pick one at random per trigger.",
            "sized: pick the file whose size matches the event (e.g. a count-up duration).",
        ],
        "sounds": sounds,
        "music_enabled": specs.music_enabled(),
        "music": mus,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, sort_keys=False)
        f.write("\n")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=specs.SOUNDS_DIR)
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args(argv)
    written = render_all(a.out, a.ids or None)
    if not a.no_manifest and not a.ids and os.path.abspath(a.out) == os.path.abspath(specs.SOUNDS_DIR):
        write_manifest(os.path.join(specs.HERE, "manifest.json"))
    print(f"sfx.py: wrote {len(written)} files to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
