"""Our own synthesised instrument patches, used by the jingles (sfx.py) and the loops (music.py). Each function returns
a mono note or hit as a float array starting at its onset; `vel` is linear gain. All randomness comes from
dsp.rng_for(key...) so every render is bit-identical. Copied as-is from apps/matchfactory/tools/audio/instruments.py
(05424db; the patches were designed for Match Factory's SPEC-motion-audio §21.1 and are generic: pluck bass, marimba,
kalimba, glock, toy EP, whistle, brass stab, saw pad, woodblock, shaker, kick, clap, hat, tambourine, snare, crash,
firework pop). Only this docstring changed (design/REUSE.md).
"""
from __future__ import annotations

import math

import numpy as np

import dsp
from dsp import SR, db2a, n_of

# ----------------------------------------------------------------------------------------------------------------------
# pitched


def pluck_bass(f: float, dur: float, vel: float = 1.0, key=("pb",)) -> np.ndarray:
    """Pluck bass: sin + tri (-6 dB), A 3 ms, tau 0.18 s, LP(1.2 kHz); 5 ms noise thump LP(300 Hz).
    Our touches: a faint octave and gentle saturation so the line still reads on a phone speaker."""
    ln = min(dur + 0.08, 0.9)
    n = n_of(ln)
    env = dsp.env_exp(n, 0.003, 0.18) * dsp.env_ahr(n, 0.0, ln - 0.03, 0.03)
    tone = dsp.osc_sin(f, n) + db2a(-6) * dsp.osc_tri(f, n, 0.25) + db2a(-16) * dsp.osc_sin(2 * f, n, 0.1)
    tone = dsp.softclip(tone * env * 1.3, 1.2)
    tone = dsp.lp(tone, 1200.0)
    rng = dsp.rng_for(*key, "thump")
    th = dsp.lp(dsp.white(n_of(0.005), rng), 300.0) * np.hanning(n_of(0.005))
    th = dsp.pad_to(th, n) * 2.0
    return vel * (tone + db2a(-10) * th)


def marimba(f: float, vel: float = 1.0, key=("mar",), length: float = 1.1) -> np.ndarray:
    """Marimba: modal partials x1 (tau 0.45 s), x3.93 (-10 dB, tau 0.10 s), x9.2 (-20 dB, tau 0.03 s);
    mallet click BP(3 kHz) 4 ms (-18 dB). Higher notes decay a little faster, like the bars do."""
    n = n_of(length)
    scale = (523.25 / f) ** 0.25
    y = dsp.additive(f, n, [(1.0, 0.0, 0.45 * scale), (3.93, -10.0, 0.10 * scale), (9.2, -20.0, 0.03)],
                     attack=0.0015)
    rng = dsp.rng_for(*key, "click")
    c = dsp.bp(dsp.white(n_of(0.004), rng), 3000.0, 1.2) * np.hanning(n_of(0.004))
    y += db2a(-18) * 3.0 * dsp.pad_to(c, n)
    return vel * dsp.fade(y, 0.0005, 0.03)


def kalimba(f: float, vel: float = 1.0, key=("kal",), length: float = 0.9) -> np.ndarray:
    """Kalimba pluck: sin + x2 (-8 dB), tau 0.25 s; our touch: a faint inharmonic tine partial and a soft thumb."""
    n = n_of(length)
    y = dsp.additive(f, n, [(1.0, 0.0, 0.25), (2.0, -8.0, 0.16), (5.95, -26.0, 0.04)], attack=0.002)
    rng = dsp.rng_for(*key, "thumb")
    th = dsp.lp(dsp.white(n_of(0.006), rng), 900.0) * np.hanning(n_of(0.006))
    y += db2a(-22) * 3.0 * dsp.pad_to(th, n)
    return vel * dsp.fade(y, 0.0005, 0.03)


def glock(f: float, vel: float = 1.0, key=("gl",), length: float = 1.6) -> np.ndarray:
    """Glockenspiel: partials x1 (tau 1.2 s), x2.76 (-12 dB, tau 0.4 s), x5.4 (-20 dB, tau 0.15 s) + strike tick."""
    n = n_of(length)
    y = dsp.additive(f, n, [(1.0, 0.0, 1.2), (2.76, -12.0, 0.4), (5.4, -20.0, 0.15)], attack=0.0008)
    rng = dsp.rng_for(*key, "tick")
    tk = dsp.hp(dsp.white(n_of(0.002), rng), 5000.0) * np.hanning(n_of(0.002))
    y += db2a(-24) * 3.0 * dsp.pad_to(tk, n)
    return vel * dsp.fade(y, 0.0003, 0.05)


def toy_ep(f: float, dur: float, vel: float = 1.0, key=("ep",), tau: float = 0.6) -> np.ndarray:
    """Toy EP: FM 1:1, index 1.4 -> 0.3 (tau 0.3 s) + tine partial x14 (-26 dB, tau 0.05 s); A 3 ms, tau 0.6 s.
    The note is damped 60 ms after its written length."""
    ln = dur + 0.12
    n = n_of(ln)
    t = dsp.t_axis(n)
    ph = dsp.phase_of(f, n)
    idx = 0.3 + 1.1 * np.exp(-t / 0.3)
    y = np.sin(2 * math.pi * ph + idx * np.sin(2 * math.pi * ph))
    if 14 * f < 0.45 * SR:
        y += db2a(-26) * np.sin(2 * math.pi * 14 * ph) * np.exp(-t / 0.05)
    env = dsp.env_exp(n, 0.003, tau) * dsp.env_ahr(n, 0.0, dur, 0.1, curve="sine")
    return vel * y * env


def round_bass(f: float, dur: float, vel: float = 1.0) -> np.ndarray:
    """Round synth bass: saw + sine sub, LP 600 Hz with a +400 Hz envelope (tau 0.1 s), A 5 ms."""
    ln = dur + 0.04
    n = n_of(ln)
    t = dsp.t_axis(n)
    raw = 0.55 * dsp.osc_saw(f, n) + 0.9 * dsp.osc_sin(f, n, 0.25)
    fc = 600.0 + 400.0 * np.exp(-t / 0.1)
    y = dsp.svf(raw, fc, 0.9, "lp")
    env = dsp.env_ahr(n, 0.005, max(dur - 0.03, 0.01), 0.06, curve="sine")
    return vel * dsp.softclip(y * env, 1.1)


def whistle_line(notes: list[tuple[float, float, float, float]], total: int, circular: bool = False,
                 key=("wh",)) -> np.ndarray:
    """Monophonic whistle / ocarina lead: sin + x2 (-18 dB) + x3 (-24 dB); vibrato 5.5 Hz +-15 cents after 0.15 s;
    breath noise BP(2 kHz) -24 dB; A 30 ms, release 80 ms; 30 ms portamento on legato.
    notes = [(start_s, dur_s, freq_hz, vel)], rendered as ONE voice so legato joins glide instead of re-attacking.
    circular=True: `total` is a loop period and everything wraps (seamless loops)."""
    n = total
    t = np.arange(n) / SR
    freq = np.full(n, notes[0][2])
    amp = np.zeros(n)
    vib_depth = np.zeros(n)
    assigned = np.zeros(n, dtype=bool)
    notes = sorted(notes)
    for i, (s, d, f, v) in enumerate(notes):
        prev = notes[i - 1] if i > 0 else (notes[-1] if circular else None)
        legato = False
        if prev is not None:
            pend = prev[0] + prev[1]
            if circular and i == 0:
                pend -= n / SR
            legato = abs(pend - s) < 0.03 and abs(prev[2] - f) > 0.5  # a repeated pitch is re-tongued
        s0, s1 = n_of(s), n_of(s + d)
        idx = np.arange(s0, s1 + n_of(0.08))
        seg_t = (idx - s0) / SR
        # pitch: portamento from the previous pitch on legato joins
        pf = np.full(len(idx), f)
        if legato:
            g = np.clip(seg_t / 0.03, 0, 1)
            pf = prev[2] * (f / prev[2]) ** g
        # amplitude: attack (none on legato), hold, 80 ms release after the written end
        if legato:
            a = np.minimum(1.0, 0.8 + 0.2 * seg_t / 0.03)  # a light tongued dip between slurred notes
        else:
            a = np.minimum(1.0, seg_t / 0.03)
        rel = np.clip(1.0 - (seg_t - d) / 0.08, 0.0, 1.0)
        a = np.minimum(a, rel)
        # a gentle swell on long notes
        a *= 0.92 + 0.08 * np.clip(seg_t / 0.35, 0, 1)
        vd = np.clip((seg_t - 0.15) / 0.12, 0, 1)
        j = idx % n if circular else idx
        keep = j < n
        j, pf, a, vd = j[keep], pf[keep], a[keep], vd[keep]
        body = seg_t[keep] < d
        freq[j[body]] = pf[body]
        assigned[j[body]] = True
        amp[j] = np.maximum(amp[j], v * a)
        vib_depth[j[body]] = vd[body]
    # hold the last pitch (and vibrato depth) through releases and rests: forward fill, wrapping for loops
    where = np.where(assigned)[0]
    ff = np.maximum.accumulate(np.where(assigned, np.arange(n), -1))
    ff[ff < 0] = where[-1] if circular else where[0]
    freq = freq[ff]
    vib_depth = vib_depth[ff]
    # vibrato
    lfo = np.sin(2 * math.pi * 5.5 * t)
    fvib = freq * 2.0 ** (15.0 * vib_depth * lfo / 1200.0)
    ph = dsp.phase_of(fvib, n)
    if circular:
        # make the phase periodic: spread the residual over the loop (inaudible, < 1 cycle over the period)
        total_cycles = ph[-1] + fvib[-1] / SR
        ph = ph - (total_cycles - round(total_cycles)) * (np.arange(n) / n)
    y = np.sin(2 * math.pi * ph) + db2a(-18) * np.sin(4 * math.pi * ph) + db2a(-24) * np.sin(6 * math.pi * ph)
    rng = dsp.rng_for(*key, "breath")
    breath = dsp.spectral_band(n, rng, 1400.0, 2800.0, edge_oct=0.5)
    y = y * amp + db2a(-24) * breath * amp
    return y


def brass_stab(freqs: list[float], dur: float, vel: float = 1.0, key=("br",), bright: float = 1.0) -> np.ndarray:
    """Brass stab: 3 saws +-8 cents per note, LP envelope 800 Hz -> 3.5 kHz -> 1.5 kHz (A 20 ms), amp A 10 ms,
    release 80 ms. Our touches: a 25 ms pitch scoop into each note and light saturation (brassy bite)."""
    ln = dur + 0.1
    n = n_of(ln)
    t = dsp.t_axis(n)
    rng = dsp.rng_for(*key)
    raw = np.zeros(n)
    scoop = 2.0 ** (-35.0 * np.exp(-t / 0.012) / 1200.0)
    for f in freqs:
        for c in (-8.0, 0.0, 8.0):
            ff = f * 2 ** (c / 1200.0) * scoop
            raw += dsp.osc_saw(ff, n, rng.random())
    raw /= max(1.0, math.sqrt(len(freqs) * 3))
    fc = np.interp(t, [0.0, 0.02, 0.02 + 0.12 * dur + 0.05, ln], [800.0, 3500.0 * bright, 1500.0 * bright,
                                                                    1200.0 * bright])
    y = dsp.svf(raw, fc, 0.8, "lp")
    env = dsp.env_ahr(n, 0.010, max(dur - 0.01, 0.0), 0.08, curve="sine")
    y = dsp.softclip(y * env * 1.4, 1.3)
    return vel * y


def saw_pad(freqs: list[float], n: int, detune_cents: float = 10.0, lp_hz: float = 1800.0, quant_hz: float = 0.5,
            shifts: list[float] | None = None, gains: list[float] | None = None) -> np.ndarray:
    """Sting pad core: 4 saws +-10 cents per note through LP(1.8 kHz). Every oscillator frequency is rounded to a
    multiple of `quant_hz`, so a period of 1/quant_hz seconds loops sample-exactly (length n, circular).
    shifts[i] starts note i's four saws as if its time were shifted by that many seconds: staggering the notes'
    slow detune beats in time keeps the chord's loudness steady instead of swelling all at once."""
    y = np.zeros(n)
    for i, f in enumerate(freqs):
        sh = shifts[i] if shifts else 0.0
        g = gains[i] if gains else 1.0
        for c in (-detune_cents, -detune_cents / 3, detune_cents / 3, detune_cents):
            ff = round(f * 2 ** (c / 1200.0) / quant_hz) * quant_hz
            y += g * dsp.osc_saw(ff, n, (ff * sh) % 1.0)
    y /= math.sqrt(4 * len(freqs))
    # circular LP: filter three periods and keep the middle one
    y3 = dsp.lp(np.concatenate([y, y, y]), lp_hz, 0.6, order=2)
    return y3[n:2 * n]


# ----------------------------------------------------------------------------------------------------------------------
# percussion


def woodblock(vel: float = 1.0, key=("wb",), f: float = 900.0) -> np.ndarray:
    """Woodblock: noise BP(1.8 kHz, Q 8) tau 25 ms + sin 900 Hz tau 15 ms."""
    n = n_of(0.16)
    rng = dsp.rng_for(*key)
    nz = dsp.bp(dsp.white(n, rng), 2.0 * f, 8.0) * dsp.env_exp(n, 0.0005, 0.025) * 2.2
    tone = dsp.osc_sin(f * (1 + 0.04 * np.exp(-dsp.t_axis(n) / 0.004)), n) * dsp.env_exp(n, 0.0005, 0.015)
    return vel * dsp.fade(nz + tone, 0.0002, 0.02)


def shaker(vel: float = 1.0, key=("sh",)) -> np.ndarray:
    """Shaker: white noise HP(6 kHz), A 8 ms, tau 35 ms."""
    n = n_of(0.16)
    rng = dsp.rng_for(*key)
    nz = dsp.hp(dsp.white(n, rng), 6000.0, order=2)
    return vel * dsp.fade(nz * dsp.env_exp(n, 0.008, 0.035), 0.0, 0.02)


def soft_kick(vel: float = 1.0, key=("kick",)) -> np.ndarray:
    """Soft kick: sin 110 -> 48 Hz over 0.12 s, tau 0.15 s, 2 ms click."""
    n = n_of(0.45)
    f = dsp.glide_exp(110.0, 48.0, 0.12, n)
    body = dsp.osc_sin(f, n) * dsp.env_exp(n, 0.001, 0.15)
    rng = dsp.rng_for(*key)
    click = dsp.lp(dsp.white(n_of(0.002), rng), 3000.0) * np.hanning(n_of(0.002))
    y = body + 0.35 * dsp.pad_to(click, n)
    return vel * dsp.fade(dsp.softclip(y, 1.2), 0.0002, 0.05)


def clap(vel: float = 1.0, key=("clap",)) -> np.ndarray:
    """Clap: 3 noise bursts BP(1.5 kHz) 8 ms apart, the last one with tau 60 ms; plus a short room of its own."""
    n = n_of(0.35)
    rng = dsp.rng_for(*key)
    src = dsp.white(n, rng)
    env = np.zeros(n)
    t = dsp.t_axis(n)
    for k, d in enumerate((0.0, 0.008, 0.016)):
        tau = 0.006 if k < 2 else 0.06
        e = np.where(t >= d, np.exp(-(t - d) / tau), 0.0) * np.minimum(1.0, np.maximum(t - d, 0) / 0.0008)
        env = np.maximum(env, e)
    y = dsp.bp(src, 1500.0, 1.1) * env * 2.0
    y += 0.35 * dsp.bp(src, 3200.0, 1.5) * env
    return vel * dsp.fade(y, 0.0002, 0.04)


def closed_hat(vel: float = 1.0, key=("hat",), tau: float = 0.03) -> np.ndarray:
    """Closed hat: white noise HP(8 kHz), tau 30 ms, with a faint metallic square cluster for sheen."""
    n = n_of(0.14)
    rng = dsp.rng_for(*key)
    nz = dsp.hp(dsp.white(n, rng), 8000.0, order=2)
    metal = np.zeros(n)
    for f in (317.0, 431.0, 529.0, 681.0, 797.0, 941.0):
        metal += dsp.osc_square(f * 4.1, n, rng.random())
    metal = dsp.hp(metal, 7000.0, order=2) * 0.08
    return vel * dsp.fade((nz + metal) * dsp.env_exp(n, 0.0008, tau), 0.0001, 0.02)


def tambourine(vel: float = 1.0, key=("tam",)) -> np.ndarray:
    """Tambourine: HP(7 kHz) noise + jingles sin 6.2 / 7.9 kHz, tau 60 ms."""
    n = n_of(0.22)
    rng = dsp.rng_for(*key)
    nz = dsp.hp(dsp.white(n, rng), 7000.0, order=2) * dsp.env_exp(n, 0.002, 0.04)
    j = (dsp.osc_sin(6200.0 * (1 + 0.01 * rng.standard_normal()), n) +
         0.8 * dsp.osc_sin(7900.0 * (1 + 0.01 * rng.standard_normal()), n)) * dsp.env_exp(n, 0.001, 0.06)
    j *= 1.0 + 0.5 * np.sin(2 * math.pi * 55.0 * dsp.t_axis(n))  # jingles rattle against each other
    return vel * dsp.fade(0.8 * nz + 0.35 * j, 0.0001, 0.03)


def snare(vel: float = 1.0, key=("sn",)) -> np.ndarray:
    """Bright pop snare for the fanfare: tone body 190 Hz + noise BP 2.5 kHz / HP 5 kHz."""
    n = n_of(0.3)
    rng = dsp.rng_for(*key)
    t = dsp.t_axis(n)
    body = dsp.osc_sin(190.0 * (1 + 0.3 * np.exp(-t / 0.01)), n) * dsp.env_exp(n, 0.0008, 0.05)
    nz = dsp.white(n, rng)
    wires = (0.9 * dsp.bp(nz, 2500.0, 0.8) + 0.5 * dsp.hp(nz, 5000.0)) * dsp.env_exp(n, 0.0008, 0.08)
    return vel * dsp.fade(0.8 * body + wires, 0.0001, 0.04)


def crash(vel: float = 1.0, key=("cr",), length: float = 1.4) -> np.ndarray:
    """Crash cymbal: HP noise with a dense inharmonic partial wash, tau 0.5 s."""
    n = n_of(length)
    rng = dsp.rng_for(*key)
    nz = dsp.hp(dsp.white(n, rng), 3500.0, order=2)
    metal = np.zeros(n)
    for _ in range(24):
        metal += dsp.osc_sin(rng.uniform(3000.0, 11000.0), n, rng.random())
    metal = metal / math.sqrt(24)
    env = dsp.env_exp(n, 0.002, 0.5)
    y = (nz + 0.5 * metal) * env + dsp.hp(nz, 8000.0) * dsp.env_exp(n, 0.001, 0.05) * 0.8
    return vel * dsp.fade(y, 0.0001, 0.2)


def firework_pop(vel: float = 1.0, key=("fwp",)) -> np.ndarray:
    """Distant firework pop for the fanfare: 20 ms noise pop + 0.2 s crackle in 8-12 kHz."""
    n = n_of(0.26)
    rng = dsp.rng_for(*key)
    pop = dsp.lp(dsp.white(n, rng), 3500.0) * dsp.env_exp(n, 0.0005, 0.007) * 1.5
    crack = np.zeros(n)
    w = n_of(0.0015)
    for _ in range(14):
        k = n_of(rng.uniform(0.02, 0.22))
        if k + w < n:
            crack[k:k + w] += rng.uniform(0.3, 1.0) * dsp.white(w, rng) * np.hanning(w)
    crack = dsp.bp(crack, 10000.0, 0.9) * 2.5
    return vel * dsp.fade(pop + crack, 0.0001, 0.02)
