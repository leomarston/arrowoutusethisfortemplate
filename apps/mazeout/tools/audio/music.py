#!/usr/bin/env python3
"""Renders the music loops to App/Resources/Music/<id>.wav (stereo, 44.1 kHz, 16-bit).

Adapted from apps/matchfactory/tools/audio/music.py (05424db): the `Song` loop engine and `parse_line` are verbatim;
Match Factory's two compositions ("Workbench Bounce", "Factory Floor") are NOT copied. The audio agent (A1) composes our
own loops in the tempo, key centre, density and loudness the analyst measured (never a melody derived from the
original), writes one `render_<id>()` per MusicID and registers it in RENDER. MF's compositions are a technique
reference only: `git show 05424db:apps/matchfactory/tools/audio/music.py`. design/REUSE.md lists the changes.

Loops are rendered CIRCULARLY: one period long, every note tail, chorus and reverb wraps around the end onto the
start, and the master dynamics run warmed up on the loop's own tail. The file is therefore exactly one period of the
steady-state performance, so looping [0, N) is sample-seamless (check.py verifies the seam).

    python3 tools/audio/music.py [--out DIR] [id ...]
"""
from __future__ import annotations

import argparse
import math  # noqa: F401  (compositions use it)
import os
import sys
from typing import Callable

import numpy as np

import dsp
import instruments as ins  # noqa: F401  (compositions use the shared patches)
import specs
from dsp import SR, db2a

# ----------------------------------------------------------------------------------------------------------------------
# the loop engine (verbatim from MF)

class Song:
    def __init__(self, name: str):
        bpm, bars, samples, rms, tp = specs.MUSIC[name]
        self.name, self.bpm, self.bars, self.N = name, bpm, bars, samples
        self.beat = 60.0 / bpm
        self.rms_target, self.tp_ceiling = rms, tp
        self.mix = np.zeros((samples, 2))
        self.send = np.zeros(samples)

    def pos(self, bar: int, beat: float, jitter_key=None, jitter_ms: float = 0.0) -> int:
        """Sample index of (bar 1-based, beat 0-based within the bar); wraps into [0, N)."""
        s = ((bar - 1) * 4 + beat) * self.beat * SR
        if jitter_key is not None and jitter_ms:
            s += dsp.rng_for("jit", self.name, *jitter_key).uniform(-1, 1) * jitter_ms / 1000.0 * SR
        return int(round(s)) % self.N

    def sec(self, beats: float) -> float:
        return beats * self.beat

    def track(self) -> np.ndarray:
        return np.zeros(self.N)

    def add(self, track: np.ndarray, gain_db: float, pan: float, send: float, hp_hz: float = 0.0,
            eq: list[tuple[str, float, float, float]] | None = None) -> None:
        """Mixes a finished mono track in: optional HP and EQ (circular), constant-power pan, reverb send."""
        t = track
        if hp_hz or eq:
            t3 = np.concatenate([t[-SR:], t])
            if hp_hz:
                t3 = dsp.hp(t3, hp_hz)
            for kind, f, q, g in eq or []:
                t3 = dsp.filt(t3, kind, f, q, g)
            t = t3[SR:]
        g = db2a(gain_db)
        self.mix += dsp.pan(t * g, pan)
        self.send += t * g * send

    def finish(self, ir_rt: float = 0.7, wet: float = 0.12, comp: tuple[float, float] | None = None,
               tilt_db: float = 0.0) -> np.ndarray:
        """Reverb return (circular), glue compression, level to the RMS target, true-peak limiting (all loop-safe)."""
        ir = dsp.make_ir(rt60=ir_rt, predelay=0.015, seed="musicroom", stereo=True)
        wetsig = dsp.convolve(self.send, ir, circular=True)
        # the "12 % wet" of §21.1: dry at 0.88, the unit-energy room at 0.12 of the dry send's scale x 3 (a plucky,
        # sparse source spreads its energy over the 0.7 s tail, so the return needs this make-up to be audible)
        out = (1.0 - wet) * self.mix + wet * 3.0 * wetsig
        out -= out.mean(axis=0)
        if tilt_db:
            out = np.stack([dsp.filt(np.concatenate([out[-SR:, c], out[:, c]]), "highshelf", 4000.0, 0.7,
                                     tilt_db)[SR:] for c in range(2)], axis=1)
        if comp:
            thr, ratio = comp
            rms_now = dsp.rms_db(out)
            out = dsp.compressor(out, rms_now + thr, ratio, 12.0, 180.0, circular=True)
        # iterate: set the RMS, limit the true peak, repeat until both hold
        for _ in range(6):
            out *= db2a(self.rms_target - dsp.rms_db(out))
            if dsp.a2db(dsp.true_peak(out)) <= self.tp_ceiling - 0.15:
                break
            out = dsp.limiter(out, self.tp_ceiling - 0.3, lookahead_ms=2.0, release_ms=90.0, circular=True)
        out *= db2a(self.rms_target - dsp.rms_db(out))
        if dsp.a2db(dsp.true_peak(out)) > self.tp_ceiling - 0.1:
            out = dsp.limiter(out, self.tp_ceiling - 0.25, lookahead_ms=2.0, release_ms=90.0, circular=True)
        return out


def parse_line(s: str) -> list[tuple[float, str, float]]:
    """'0:D5:.5 .5:F#5:.5' -> [(beat, note, dur_beats), ...]"""
    out = []
    for tok in s.split():
        b, n, d = tok.split(":")
        out.append((float(b), n, float(d)))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# compositions: one render_<id>() -> (N, 2) float64 per MusicID. NONE: Arrow Out has no music (SPEC-motion-audio MA2,
# §11.5); a composition is written only if a later phone check finds a loop and audio.json turns music.enabled on.
# Pattern (MF):
#     s = Song("<id>"); t = s.track(); dsp.place(t, ins.marimba(dsp.hz("D5"), 0.9, key=("m", 1)), s.pos(1, 0), wrap=True)
#     s.add(t, gain_db=-2.0, pan=-0.15, send=1.0, hp_hz=120.0); return s.finish(ir_rt=0.7, wet=0.12, comp=(4.0, 1.6))

RENDER: dict[str, Callable[[], np.ndarray]] = {}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=specs.MUSIC_DIR)
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args(argv)
    if not specs.music_enabled():
        # SPEC-motion-audio MA2 / §11.5: no music exists in v552 (inert Music button); the contract's MusicIDs stay, but
        # nothing is composed or rendered while Tuning/audio.json music.enabled is false (check.py then treats any
        # Music/*.wav as a stray).
        print("music.py: music.enabled is false in Tuning/audio.json (SPEC-motion-audio §11.5): no music to render")
        return 0
    music = specs.active_music_ids()
    missing = [m for m in music if m not in RENDER]
    if missing:
        raise SystemExit(f"no composition for MusicID(s): {missing}")
    os.makedirs(a.out, exist_ok=True)
    for mid in music:
        if a.ids and mid not in a.ids:
            continue
        x = RENDER[mid]()
        path = os.path.join(a.out, f"{mid}.wav")
        dsp.write_wav(path, x, dither_seed=f"music-{mid}")
        print(f"music.py: {path}  {len(x)} samples  RMS {dsp.rms_db(x):.2f} dBFS  TP {dsp.a2db(dsp.true_peak(x)):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
