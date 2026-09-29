"""Small offline DSP toolkit for our own synthesised audio (AUDIO, WP A1). Copied as-is from
apps/matchfactory/tools/audio/dsp.py (05424db); only this docstring changed (design/REUSE.md).

Everything here is generated from maths and fixed random seeds. Nothing reads a recording: the reference captures in
research/sound-refs are for listening and comparing only, never an input (GAMEPROMPT §7.2 "Audio", the copying line).

Conventions
- Mono signals are 1-D float64 arrays at SR; stereo signals are (n, 2).
- Times in seconds, frequencies in Hz, levels in dB.
- `tau` is an exponential decay time constant: amplitude = exp(-t / tau) (-30 dB after about 3.45 tau).
"""
from __future__ import annotations

import math
import wave

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 44100
TWO_PI = 2.0 * math.pi


# ----------------------------------------------------------------------------------------------------------------------
# basics

def n_of(dur: float) -> int:
    return int(round(dur * SR))


def t_axis(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def db2a(db: float) -> float:
    return 10.0 ** (db / 20.0)


def a2db(a: float) -> float:
    return 20.0 * math.log10(max(a, 1e-12))


def rng_for(*key) -> np.random.Generator:
    """A deterministic generator per (cue, part, variant, ...) key: renders are bit-reproducible."""
    h = 1469598103934665603
    for part in key:
        for ch in str(part).encode():
            h = ((h ^ ch) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return np.random.default_rng(h)


def place(dst: np.ndarray, src: np.ndarray, at: float | int, gain: float = 1.0, wrap: bool = False) -> None:
    """Adds src into dst starting at time `at` (float seconds) or sample index (int). wrap=True folds around (loops)."""
    start = at if isinstance(at, (int, np.integer)) else n_of(at)
    n = len(dst)
    if wrap:
        start %= n
        pos = 0
        while pos < len(src):
            s = (start + pos) % n
            take = min(len(src) - pos, n - s)
            dst[s:s + take] += gain * src[pos:pos + take]
            pos += take
        return
    if start >= n:
        return
    s0 = max(start, 0)
    k0 = s0 - start
    take = min(len(src) - k0, n - s0)
    if take > 0:
        dst[s0:s0 + take] += gain * src[k0:k0 + take]


def pad_to(x: np.ndarray, n: int) -> np.ndarray:
    if len(x) >= n:
        return x[:n]
    out = np.zeros((n,) + x.shape[1:])
    out[:len(x)] = x
    return out


# ----------------------------------------------------------------------------------------------------------------------
# envelopes

def env_exp(n: int, attack: float = 0.002, tau: float = 0.1, hold: float = 0.0, delay: float = 0.0) -> np.ndarray:
    """Linear attack, optional hold at 1, then exp decay with time constant tau."""
    t = t_axis(n) - delay
    e = np.zeros(n)
    a = max(attack, 1e-5)
    on = t >= 0
    e[on] = np.where(t[on] < a, t[on] / a,
                     np.where(t[on] < a + hold, 1.0, np.exp(-(t[on] - a - hold) / max(tau, 1e-6))))
    return e


def env_ahr(n: int, attack: float, hold: float, release: float, delay: float = 0.0, curve: str = "lin") -> np.ndarray:
    """Attack (linear or sine), hold, release (linear, sine or exponential-looking cosine)."""
    t = t_axis(n) - delay
    e = np.zeros(n)
    a = max(attack, 1e-5)
    r = max(release, 1e-5)
    up = (t >= 0) & (t < a)
    hd = (t >= a) & (t < a + hold)
    dn = (t >= a + hold) & (t < a + hold + r)
    if curve == "sine":
        e[up] = np.sin(0.5 * math.pi * t[up] / a) ** 2
        e[dn] = np.cos(0.5 * math.pi * (t[dn] - a - hold) / r) ** 2
    else:
        e[up] = t[up] / a
        e[dn] = 1.0 - (t[dn] - a - hold) / r
    e[hd] = 1.0
    return e


def env_points(n: int, points: list[tuple[float, float]], curve: str = "lin") -> np.ndarray:
    """Piecewise envelope through (time, value) points; 'exp' interpolates in the log domain (values > 0)."""
    t = t_axis(n)
    ts = np.array([p[0] for p in points])
    vs = np.array([p[1] for p in points], dtype=np.float64)
    if curve == "exp":
        return np.exp(np.interp(t, ts, np.log(np.maximum(vs, 1e-6))))
    return np.interp(t, ts, vs)


def fade(x: np.ndarray, fin: float = 0.001, fout: float = 0.005) -> np.ndarray:
    """Short raised-cosine fades so a file starts and ends at exactly zero (no clicks)."""
    y = x.copy()
    ni, no = max(n_of(fin), 1), max(n_of(fout), 1)
    wi = np.sin(0.5 * math.pi * np.arange(ni) / ni) ** 2
    wo = np.cos(0.5 * math.pi * (np.arange(no) + 1) / no) ** 2
    if y.ndim == 1:
        y[:ni] *= wi
        y[-no:] *= wo
    else:
        y[:ni] *= wi[:, None]
        y[-no:] *= wo[:, None]
    return y


# ----------------------------------------------------------------------------------------------------------------------
# frequency curves

def glide_exp(f0: float, f1: float, dur: float, n: int, delay: float = 0.0) -> np.ndarray:
    """Exponential glide f0 -> f1 over `dur` seconds (starting after `delay`), then held."""
    t = np.clip((t_axis(n) - delay) / max(dur, 1e-6), 0.0, 1.0)
    return f0 * (f1 / f0) ** t


def glide_lin(f0: float, f1: float, dur: float, n: int, delay: float = 0.0) -> np.ndarray:
    t = np.clip((t_axis(n) - delay) / max(dur, 1e-6), 0.0, 1.0)
    return f0 + (f1 - f0) * t


def vibrato(freq, n: int, rate: float, depth_hz: float = 0.0, depth_cents: float = 0.0, onset: float = 0.0,
            ramp: float = 0.0, phase: float = 0.0) -> np.ndarray:
    t = t_axis(n)
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,)).copy()
    depth = np.ones(n)
    if onset > 0 or ramp > 0:
        depth = np.clip((t - onset) / max(ramp, 1e-6), 0.0, 1.0)
    lfo = np.sin(TWO_PI * rate * t + phase) * depth
    if depth_cents:
        f *= 2.0 ** (depth_cents * lfo / 1200.0)
    if depth_hz:
        f += depth_hz * lfo
    return f


# ----------------------------------------------------------------------------------------------------------------------
# oscillators (freq may be a scalar or a per-sample array)

def phase_of(freq, n: int, phase0: float = 0.0) -> np.ndarray:
    """Phase in cycles. A scalar frequency uses f*n/SR directly, so a loop whose f*period is an integer is sample-exact."""
    if np.ndim(freq) == 0:
        return float(freq) * np.arange(n) / SR + phase0
    f = np.asarray(freq, dtype=np.float64)
    ph = np.empty(n)
    ph[0] = 0.0
    np.cumsum(f[:-1] / SR, out=ph[1:])
    return ph + phase0


def osc_sin(freq, n: int, phase0: float = 0.0) -> np.ndarray:
    return np.sin(TWO_PI * phase_of(freq, n, phase0))


def _polyblep(t: np.ndarray, dt: np.ndarray) -> np.ndarray:
    out = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m2 = t > 1.0 - dt
    x = (t[m2] - 1.0) / dt[m2]
    out[m2] = x * x + x + x + 1.0
    return out


def osc_saw(freq, n: int, phase0: float = 0.0) -> np.ndarray:
    """Band-limited (PolyBLEP) sawtooth, range -1..1."""
    ph = phase_of(freq, n, phase0) % 1.0
    dt = np.broadcast_to(np.abs(np.asarray(freq, dtype=np.float64)) / SR, (n,))
    return 2.0 * ph - 1.0 - _polyblep(ph, dt)


def osc_square(freq, n: int, phase0: float = 0.0, pw: float = 0.5) -> np.ndarray:
    """Band-limited (PolyBLEP) pulse wave."""
    ph = phase_of(freq, n, phase0) % 1.0
    dt = np.broadcast_to(np.abs(np.asarray(freq, dtype=np.float64)) / SR, (n,))
    y = np.where(ph < pw, 1.0, -1.0)
    y += _polyblep(ph, dt)
    y -= _polyblep((ph + 1.0 - pw) % 1.0, dt)
    return y


def osc_tri(freq, n: int, phase0: float = 0.0, max_harm: int = 31) -> np.ndarray:
    """Band-limited triangle by additive synthesis (odd harmonics, 1/k^2), kept under 0.45*SR."""
    ph = TWO_PI * phase_of(freq, n, phase0)
    fmax = float(np.max(freq)) if np.ndim(freq) else float(freq)
    y = np.zeros(n)
    sign = 1.0
    for k in range(1, max_harm + 1, 2):
        if k * fmax > 0.45 * SR:
            break
        y += sign * np.sin(k * ph) / (k * k)
        sign = -sign
    return y * (8.0 / math.pi ** 2)


def additive(freq, n: int, partials: list[tuple[float, float, float]], attack: float = 0.002,
             phase_seed: int | None = None) -> np.ndarray:
    """Modal/additive tone: partials = [(ratio, gain_db, tau), ...]; each partial decays on its own."""
    ph = phase_of(freq, n)
    rng = np.random.default_rng(phase_seed) if phase_seed is not None else None
    y = np.zeros(n)
    fmax = float(np.max(freq)) if np.ndim(freq) else float(freq)
    for ratio, gdb, tau in partials:
        if ratio * fmax > 0.45 * SR:
            continue
        p0 = rng.random() if rng is not None else 0.0
        y += db2a(gdb) * np.sin(TWO_PI * (ratio * ph + p0)) * env_exp(n, attack, tau)
    return y


def fm_bell(freq, n: int, ratio: float = 3.5, index0: float = 2.5, index1: float = 0.0, index_tau: float = 0.12,
            attack: float = 0.003, tau: float = 0.13) -> np.ndarray:
    """Two-operator FM bell: carrier f, modulator ratio*f, index gliding index0 -> index1 with index_tau."""
    ph = phase_of(freq, n)
    t = t_axis(n)
    idx = index1 + (index0 - index1) * np.exp(-t / index_tau)
    mod = np.sin(TWO_PI * ratio * ph)
    return np.sin(TWO_PI * ph + idx * mod) * env_exp(n, attack, tau)


# ----------------------------------------------------------------------------------------------------------------------
# noise

def white(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(n)


def colored(n: int, rng: np.random.Generator, slope_db_oct: float, fmin: float = 20.0) -> np.ndarray:
    """Noise with a spectral slope (pink = -3 dB/oct, brown = -6 dB/oct), unit RMS. Circular (loop-safe)."""
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = 1.0
    shape = (np.maximum(f, fmin) / 1000.0) ** (slope_db_oct / (20.0 * math.log10(2.0)))
    shape[0] = 0.0
    y = np.fft.irfft(X * shape, n)
    return y / (np.sqrt(np.mean(y * y)) + 1e-12)


def pink(n: int, rng: np.random.Generator) -> np.ndarray:
    return colored(n, rng, -3.0)


def brown(n: int, rng: np.random.Generator) -> np.ndarray:
    return colored(n, rng, -6.0)


def spectral_band(n: int, rng: np.random.Generator, lo: float, hi: float, slope_db_oct: float = 0.0,
                  edge_oct: float = 0.25) -> np.ndarray:
    """Band-limited noise with soft (cosine) band edges built in the frequency domain; circular, unit RMS."""
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    lo2, hi2 = math.log2(lo), math.log2(hi)
    w = np.clip((lf - (lo2 - edge_oct)) / edge_oct, 0, 1) * np.clip(((hi2 + edge_oct) - lf) / edge_oct, 0, 1)
    w = np.sin(0.5 * math.pi * w) ** 2
    if slope_db_oct:
        w *= (np.maximum(f, 1.0) / 1000.0) ** (slope_db_oct / (20.0 * math.log10(2.0)))
    w[0] = 0.0
    y = np.fft.irfft(X * w, n)
    return y / (np.sqrt(np.mean(y * y)) + 1e-12)


# ----------------------------------------------------------------------------------------------------------------------
# static filters (RBJ cookbook biquads, run as SOS)

def _biquad(kind: str, f0: float, q: float = 0.7071, gain_db: float = 0.0) -> np.ndarray:
    f0 = min(max(f0, 5.0), 0.49 * SR)
    w0 = TWO_PI * f0 / SR
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2.0 * q)
    A = 10.0 ** (gain_db / 40.0)
    if kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "bp":  # constant 0 dB peak gain
        b = [alpha, 0.0, -alpha]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "lowshelf":
        sq = 2 * math.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sq), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sq)]
        a = [(A + 1) + (A - 1) * cw + sq, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sq]
    elif kind == "highshelf":
        sq = 2 * math.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sq), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sq)]
        a = [(A + 1) - (A - 1) * cw + sq, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sq]
    else:
        raise ValueError(kind)
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1.0, a[1] / a[0], a[2] / a[0]]])


def filt(x: np.ndarray, kind: str, f0: float, q: float = 0.7071, gain_db: float = 0.0, order: int = 1) -> np.ndarray:
    """Static biquad; `order` cascades the same section (steeper slopes)."""
    sos = np.vstack([_biquad(kind, f0, q, gain_db)] * order)
    return signal.sosfilt(sos, x, axis=0)


def lp(x, f0, q=0.7071, order=1):
    return filt(x, "lp", f0, q, order=order)


def hp(x, f0, q=0.7071, order=1):
    return filt(x, "hp", f0, q, order=order)


def bp(x, f0, q=1.0, order=1):
    return filt(x, "bp", f0, q, order=order)


def dc_block(x: np.ndarray, f0: float = 20.0) -> np.ndarray:
    return filt(x, "hp", f0, 0.7071)


# ----------------------------------------------------------------------------------------------------------------------
# time-varying state-variable filter (TPT / Zavalishin), cutoff per sample

def svf(x: np.ndarray, fc, q: float = 0.7071, mode: str = "lp") -> np.ndarray:
    """Modulated 2-pole SVF. mode: lp | bp (0 dB peak) | hp | notch. fc scalar or per-sample array."""
    n = len(x)
    fcv = np.broadcast_to(np.clip(np.asarray(fc, dtype=np.float64), 10.0, 0.48 * SR), (n,))
    g = np.tan(math.pi * fcv / SR)
    k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    xs = x.tolist()
    A1, A2, A3 = a1.tolist(), a2.tolist(), a3.tolist()
    ic1 = ic2 = 0.0
    out = [0.0] * n
    if mode == "lp":
        for i in range(n):
            v3 = xs[i] - ic2
            v1 = A1[i] * ic1 + A2[i] * v3
            v2 = ic2 + A2[i] * ic1 + A3[i] * v3
            ic1 = 2.0 * v1 - ic1
            ic2 = 2.0 * v2 - ic2
            out[i] = v2
    elif mode == "bp":
        for i in range(n):
            v3 = xs[i] - ic2
            v1 = A1[i] * ic1 + A2[i] * v3
            v2 = ic2 + A2[i] * ic1 + A3[i] * v3
            ic1 = 2.0 * v1 - ic1
            ic2 = 2.0 * v2 - ic2
            out[i] = k * v1
    elif mode == "hp":
        for i in range(n):
            xi = xs[i]
            v3 = xi - ic2
            v1 = A1[i] * ic1 + A2[i] * v3
            v2 = ic2 + A2[i] * ic1 + A3[i] * v3
            ic1 = 2.0 * v1 - ic1
            ic2 = 2.0 * v2 - ic2
            out[i] = xi - k * v1 - v2
    else:
        for i in range(n):
            xi = xs[i]
            v3 = xi - ic2
            v1 = A1[i] * ic1 + A2[i] * v3
            v2 = ic2 + A2[i] * ic1 + A3[i] * v3
            ic1 = 2.0 * v1 - ic1
            ic2 = 2.0 * v2 - ic2
            out[i] = xi - k * v1
    return np.asarray(out)


# ----------------------------------------------------------------------------------------------------------------------
# effects

def softclip(x: np.ndarray, drive: float = 1.0) -> np.ndarray:
    """tanh saturation normalised so small signals keep unity gain."""
    if drive <= 0:
        return x
    return np.tanh(drive * x) / drive


def make_ir(rt60: float = 0.7, predelay: float = 0.015, seed: str = "room", hf: float = 0.45, lf: float = 1.1,
            early: int = 10, stereo: bool = True, length: float | None = None) -> np.ndarray:
    """A synthetic room/plate impulse response: early reflections + a diffuse tail whose decay is frequency dependent
    (rt60 at mids, lf*rt60 below 250 Hz, hf*rt60 above 6 kHz). Unit energy per channel. Returns (n, 2) or (n,)."""
    total = length if length is not None else predelay + 1.15 * rt60
    n = n_of(total)
    chans = []
    for ch in range(2 if stereo else 1):
        rng = rng_for("ir", seed, ch)
        ir = np.zeros(n)
        t = t_axis(n)
        bands = [(20.0, 250.0, lf), (250.0, 2000.0, 1.0), (2000.0, 6000.0, 0.5 * (1.0 + hf)), (6000.0, 20000.0, hf)]
        tail_start = predelay + 0.004
        for lo, hi, ratio in bands:
            noise = spectral_band(n, rng, lo, hi, edge_oct=0.5)
            rt = max(rt60 * ratio, 0.05)
            env = np.where(t >= tail_start, np.exp(-6.91 * (t - tail_start) / rt), 0.0)
            onset = 1.0 - np.exp(-np.maximum(t - tail_start, 0.0) / 0.006)
            ir += noise * env * onset
        ir *= 0.5
        # early reflections: sparse, decreasing, slightly low-passed taps
        er = np.zeros(n)
        for i in range(early):
            d = predelay * 0.35 + rng.uniform(0.002, 0.045)
            g = rng.uniform(0.35, 0.8) * math.exp(-d / 0.03) * (1 if rng.random() < 0.6 else -1)
            k = n_of(d)
            if k < n:
                er[k] += g
        er = lp(er, 7000.0)
        ir += er * 2.0
        ir /= math.sqrt(np.sum(ir * ir)) + 1e-12
        chans.append(ir)
    return np.stack(chans, axis=1) if stereo else chans[0]


def convolve(x: np.ndarray, ir: np.ndarray, circular: bool = False) -> np.ndarray:
    """Mono x through a mono or stereo IR. circular=True folds the tail onto the start (loops)."""
    irs = ir if ir.ndim == 2 else ir[:, None]
    n = len(x)
    outs = []
    for c in range(irs.shape[1]):
        y = signal.oaconvolve(x, irs[:, c])
        if circular:
            base = y[:n].copy()
            tail = y[n:]
            pos = 0
            while pos < len(tail):
                take = min(len(tail) - pos, n)
                base[:take] += tail[pos:pos + take]
                pos += take
            outs.append(base)
        else:
            outs.append(y[:n])
    out = np.stack(outs, axis=1)
    return out if ir.ndim == 2 else out[:, 0]


def reverb(x: np.ndarray, ir: np.ndarray, wet: float, circular: bool = False, keep_len: bool = True) -> np.ndarray:
    """Mix `wet` of reverb into x (mono in -> same shape as the IR's channel layout)."""
    y = convolve(x, ir, circular=circular)
    if y.ndim == 2 and x.ndim == 1:
        return (1.0 - wet) * x[:, None] + wet * y
    return (1.0 - wet) * x + wet * y


def mod_delay(x: np.ndarray, delay_s: np.ndarray, circular: bool = False) -> np.ndarray:
    """Reads x at (n - delay) with linear interpolation (chorus / flanger / doppler)."""
    n = len(x)
    idx = np.arange(n) - delay_s * SR
    if circular:
        idx = np.mod(idx, n)
        xp = np.concatenate([x, x[:1]])
        i0 = np.floor(idx).astype(np.int64)
        fr = idx - i0
        return xp[i0] * (1 - fr) + xp[i0 + 1] * fr
    return np.interp(idx, np.arange(n), x, left=0.0, right=0.0)


def chorus_stereo(x: np.ndarray, rate: float, base_ms: float = 12.0, depth_ms: float = 3.0, mix: float = 0.5,
                  circular: bool = False) -> np.ndarray:
    """Mono -> stereo chorus (two LFO phases). For loops pick `rate` with an integer number of cycles per period."""
    n = len(x)
    t = t_axis(n)
    outs = []
    for ph in (0.0, 0.5 * math.pi):
        d = (base_ms + depth_ms * np.sin(TWO_PI * rate * t + ph)) / 1000.0
        outs.append(x + mix * mod_delay(x, d, circular=circular))
    return np.stack(outs, axis=1) / (1.0 + 0.5 * mix)


def pan(x: np.ndarray, p: float) -> np.ndarray:
    """Constant-power pan, p in [-1, 1]."""
    a = (p + 1.0) * 0.25 * math.pi
    return np.stack([x * math.cos(a), x * math.sin(a)], axis=1) * math.sqrt(2.0)


# ----------------------------------------------------------------------------------------------------------------------
# dynamics and measurement

def true_peak(x: np.ndarray) -> float:
    """4x oversampled peak (linear), per BS.1770 in spirit."""
    xs = x if x.ndim == 2 else x[:, None]
    m = 0.0
    for c in range(xs.shape[1]):
        m = max(m, float(np.max(np.abs(signal.resample_poly(xs[:, c], 4, 1)))))
    return m


def sample_peak(x: np.ndarray) -> float:
    return float(np.max(np.abs(x)))


def rms_db(x: np.ndarray) -> float:
    return a2db(math.sqrt(float(np.mean(np.square(x)))))


def _tp_envelope(x: np.ndarray) -> np.ndarray:
    xs = x if x.ndim == 2 else x[:, None]
    env = np.zeros(len(xs))
    for c in range(xs.shape[1]):
        up = np.abs(signal.resample_poly(xs[:, c], 4, 1))[:4 * len(xs)]
        up = pad_to(up, 4 * len(xs))
        env = np.maximum(env, up.reshape(-1, 4).max(axis=1))
    return env


def limiter(x: np.ndarray, ceiling_db: float, lookahead_ms: float = 2.0, release_ms: float = 80.0,
            circular: bool = False) -> np.ndarray:
    """Zero-overshoot look-ahead (offline) true-peak limiter. circular=True treats x as one loop period."""
    n = len(x)
    ext = 0
    if circular:
        ext = min(n, n_of(1.0))
        x_in = np.concatenate([x[-ext:], x], axis=0)
    else:
        x_in = x
    thr = db2a(ceiling_db)
    env = _tp_envelope(x_in)
    g_req = np.minimum(1.0, thr / np.maximum(env, 1e-12))
    la = max(1, n_of(lookahead_ms / 1000.0))
    g1 = minimum_filter1d(g_req, size=2 * la + 1, mode="nearest")
    g2 = uniform_filter1d(g1, size=la | 1, mode="nearest")
    # release: at a 32-sample control rate, the gain may only recover exponentially
    blk = 32
    m = (len(g2) + blk - 1) // blk
    gb = pad_to(g2, m * blk)
    gb[len(g2):] = 1.0
    ctrl = gb.reshape(m, blk).min(axis=1)
    coef = math.exp(-blk / (release_ms / 1000.0 * SR))
    out = np.empty(m)
    g = 1.0
    cl = ctrl.tolist()
    for i in range(m):
        c = cl[i]
        g = c if c < g else c + (g - c) * coef
        out[i] = g
    gs = np.interp(np.arange(len(g2)), np.arange(m) * blk + blk / 2, out)
    gfin = np.minimum(gs, g2)
    y = x_in * (gfin[:, None] if x_in.ndim == 2 else gfin)
    return y[ext:] if circular else y


def compressor(x: np.ndarray, threshold_db: float, ratio: float, attack_ms: float = 10.0, release_ms: float = 150.0,
               circular: bool = False, knee_db: float = 6.0) -> np.ndarray:
    """Feed-forward RMS glue compressor at a 64-sample control rate."""
    n = len(x)
    ext = min(n, n_of(1.5)) if circular else 0
    x_in = np.concatenate([x[-ext:], x], axis=0) if circular else x
    mono = np.mean(x_in, axis=1) if x_in.ndim == 2 else x_in
    blk = 64
    m = (len(mono) + blk - 1) // blk
    pw = pad_to(mono * mono, m * blk).reshape(m, blk).mean(axis=1)
    lvl = 10.0 * np.log10(pw + 1e-12)
    over = lvl - threshold_db
    gr_target = np.where(over <= -knee_db / 2, 0.0,
                         np.where(over >= knee_db / 2, over * (1 - 1 / ratio),
                                  (1 - 1 / ratio) * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    ca = math.exp(-blk / (attack_ms / 1000.0 * SR))
    cr = math.exp(-blk / (release_ms / 1000.0 * SR))
    gr = 0.0
    out = np.empty(m)
    for i, tgt in enumerate(gr_target.tolist()):
        c = ca if tgt > gr else cr
        gr = tgt + (gr - tgt) * c
        out[i] = gr
    gain = 10.0 ** (-np.interp(np.arange(len(mono)), np.arange(m) * blk + blk / 2, out) / 20.0)
    y = x_in * (gain[:, None] if x_in.ndim == 2 else gain)
    return y[ext:] if circular else y


def normalize_peak(x: np.ndarray, peak_db: float) -> np.ndarray:
    p = sample_peak(x)
    return x * (db2a(peak_db) / p) if p > 0 else x


# ----------------------------------------------------------------------------------------------------------------------
# WAV I/O (16-bit PCM)

def to_int16(x: np.ndarray, dither_seed: str | None = None) -> np.ndarray:
    y = np.asarray(x, dtype=np.float64) * 32767.0
    if dither_seed is not None:
        rng = rng_for("dither", dither_seed)
        y = y + (rng.random(y.shape) - rng.random(y.shape))  # TPDF, +-1 LSB
    return np.clip(np.round(y), -32768, 32767).astype("<i2")


def write_wav(path: str, x: np.ndarray, dither_seed: str | None = None) -> None:
    data = to_int16(x, dither_seed)
    ch = 1 if data.ndim == 1 else data.shape[1]
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def read_wav(path: str) -> tuple[np.ndarray, int, int]:
    """Returns (float signal (n,) or (n, ch), sample rate, sample width in bytes)."""
    with wave.open(path, "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: {8 * sw}-bit, expected 16-bit")
    data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32767.0
    if ch > 1:
        data = data.reshape(-1, ch)
    return data, sr, sw


# ----------------------------------------------------------------------------------------------------------------------
# pitch helpers

NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name: str) -> int:
    """'C4' -> 60, 'F#5' -> 78, 'Bb3' -> 58."""
    name = name.strip()
    base = NOTE_INDEX[name[0].upper()]
    i = 1
    while i < len(name) and name[i] in "#b":
        base += 1 if name[i] == "#" else -1
        i += 1
    return base + 12 * (int(name[i:]) + 1)


def hz(note) -> float:
    m = midi(note) if isinstance(note, str) else note
    return 440.0 * 2.0 ** ((m - 69) / 12.0)
