"""Targets for every sound file, shared by sfx.py / music.py (render) and check.py (verify).

Adapted from apps/matchfactory/tools/audio/specs.py (05424db): the paths and the machinery are kept; Match Factory's
cue tables were emptied, and A1 filled them from our own SPEC-motion-audio §11.3 (the cue list, lengths and levels of
Arrow Out; design/REUSE.md). Match Factory's tables remain a format example only:
`git show 05424db:apps/matchfactory/tools/audio/specs.py`.

Conventions (unchanged from MF):
- Peaks are SAMPLE peaks of the rendered 16-bit file in dBFS; true peak (4x oversampled) may exceed the target by at most
  PEAK_TOL_DB. `spec` names the SPEC-motion-audio cue; `tag` says where the number comes from (VERIFIED / DECISION).
- Sounds are mono, music stereo, 44.1 kHz 16-bit PCM (GAMEPROMPT §7.2 "Audio").
- The frozen audio contract (a Swift file with `enum SoundID` and `enum MusicID`) is the source of truth for WHICH files
  exist; this module parses it rather than copying the list. Its path is CONTRACT below (proposal; the architecture spec
  confirms it, and PC_AUDIO_CONTRACT overrides it).
"""
from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, "..", ".."))
# PC_SOUNDS_DIR / PC_MUSIC_DIR (T9 AUDIO-2, additive): render, check and mutation-test a staged set somewhere else (e.g.
# build/p/T9/wav) without touching App/. Unset = the shipped folders, exactly as before.
SOUNDS_DIR = os.environ.get("PC_SOUNDS_DIR") or os.path.join(APP, "App", "Resources", "Sounds")
MUSIC_DIR = os.environ.get("PC_MUSIC_DIR") or os.path.join(APP, "App", "Resources", "Music")
CONTRACT = os.environ.get("PC_AUDIO_CONTRACT") or os.path.join(APP, "App", "Contracts", "AudioContract.swift")

PEAK_TOL_DB = 1.5          # GAMEPROMPT §7.2: peaks within +-1.5 dB of the targets
LEN_TOL = 0.05             # +-5 % (or 10 ms) of the spec length

# id: (spec cue, length s, peak dBFS, tag)      -- SPEC-motion-audio §11.3 (A1). The 9 SoundIDs of the contract (§11.2).
# Levels are the measured v552 sample peaks clamped to <= -1.5 dBFS (the capture of the coin clinks clipped at 0 dBFS).
SFX: dict[str, tuple[str, float, float, str]] = {
    "uiClick":      ("SPEC-motion-audio §11.2 uiClick",      0.035, -7.5, "VERIFIED level/length (v552 Play click -7.6 dBFS, 20 ms > -20 dB)"),
    "unlockChime":  ("SPEC-motion-audio §11.2 unlockChime",  2.20,  -3.0, "VERIFIED V1/V2 shape; level DECISION"),
    "clawToken":    ("SPEC-motion-audio §11.2 clawToken",    0.75,  -2.0, "VERIFIED v552 (-1.6 dBFS, 0.42 s > -20 dB, tail 0.75)"),
    "clawMerge":    ("SPEC-motion-audio §11.2 clawMerge",    1.20,  -3.0, "VERIFIED v552 (-2.9 dBFS, decays to ~1.2 s)"),
    "clawTick":     ("SPEC-motion-audio §11.2 clawTick",     0.040, -3.0, "VERIFIED v552 (-2.5 dBFS, ~30 ms)"),
    "clawComplete": ("SPEC-motion-audio §11.2 clawComplete", 0.16,  -5.5, "VERIFIED v552 (-5.6 dBFS, 0.12 s > -20 dB)"),
    "streakPop":    ("SPEC-motion-audio §11.2 streakPop",    0.18,  -2.0, "VERIFIED v552 (-1.9/-1.8/-4.9 dBFS, 0.13-0.16 s)"),
    "coinCollect":  ("SPEC-motion-audio §11.2 coinCollect",  2.90,  -1.5, "VERIFIED v552=V1 (clinks clip 0 dBFS -> -1.5)"),
    "tapTick":      ("SPEC-motion-audio §11.2 tapTick",      0.030, -12.0, "DECISION (owner option, unmapped)"),
}

# coinCollect's 5 baked clinks, seconds from the cue start (= C0 - 0.35): the §8.3 C4 landings C0 + 0.77 + 0.085 k.
COIN_CLINKS_S = [1.120, 1.205, 1.290, 1.375, 1.460]

# SPEC-motion-audio §11.6: the per-cue assertions check.py makes ON TOP of the generic ones (format, spec length +-5 % /
# 10 ms, peak +-1.5 dB, edges, DC, provenance, contract coverage, reproduction).
#   length: (min s, max s) of the file.
#   onsets: the rises of a band's envelope (analytic signal of a raised-cosine band mask, `edge` Hz transitions) whose
#           peak is within `within_db` of the band's maximum; there must be exactly len(at) of them, each at at[k] +- tol
#           (onset = the half-way point of the rise), and each must raise the band by >= min_rise_db over its level
#           just before (so every landing is heard). coinCollect: one clink per landing coin.
#   first:  the first time a band's envelope comes within `rel_db` of its own maximum must be at `at` +- tol, and the
#           band's maximum must be at least `min_db` re the file's peak (the layer exists and starts on time).
#   hold:   that band stays within `rel_db` of its maximum from `start` to `end` s (the partial is PRESENT).
#   onset:  (T9) the first sample within `rel_db` of the file's peak comes no later than `max_s` (the cue fires on its
#           visual beat: no leading silence may delay it).
#   pitch:  (T9) the SAME PITCHES as research-measured in sounds.md §2 (the numbers, never the files): for each entry, the
#           strongest spectral peak inside `band` over the window `t` (Hann, zero-padded, parabolic interpolation) is within
#           `cents` of `f`, and that peak is at least `min_db` re the window's strongest peak anywhere (the partial is a
#           real part of the cue, not leakage).
_ON = {"rel_db": -30.0, "max_s": 0.005}


def _p(name: str, f: float, band: tuple[float, float], t: tuple[float, float], cents: float = 50.0,
       min_db: float = -24.0) -> dict:
    return {"name": name, "f": f, "band": band, "t": t, "cents": cents, "min_db": min_db}


CUE_ASSERT: dict[str, dict] = {
    "uiClick":     {"length": (0.025, 0.040), "onset": _ON,
                    "pitch": [_p("tock body ~F4 352 Hz", 352.0, (250.0, 480.0), (0.0, 0.025), cents=60.0)]},
    "clawTick":    {"length": (0.0, 0.045), "onset": _ON,
                    "pitch": [_p("tick ~F5 700 Hz", 700.0, (560.0, 860.0), (0.0, 0.030), cents=40.0)]},
    "streakPop":   {"length": (0.175, 0.185), "onset": _ON,
                    "pitch": [_p("bloop D5 586 Hz", 586.0, (520.0, 660.0), (0.03, 0.16), cents=30.0),
                              _p("under-tone F#4 369 Hz", 369.0, (320.0, 420.0), (0.03, 0.16), cents=30.0)]},
    "clawToken":   {"onset": _ON,
                    "pitch": [_p("bell C6 1049 Hz", 1049.0, (950.0, 1150.0), (0.05, 0.45), cents=25.0, min_db=-12.0)]},
    "clawMerge":   {"onset": _ON,
                    "pitch": [_p("tinkle C#6 1090 Hz", 1090.0, (1030.0, 1200.0), (0.05, 0.60), cents=25.0),
                              _p("tinkle F6 1371 Hz", 1371.0, (1290.0, 1480.0), (0.05, 0.60), cents=25.0),
                              _p("thump C#4 275 Hz", 275.0, (200.0, 340.0), (0.0, 0.05), cents=100.0)]},
    "clawComplete": {"onset": _ON,
                     "pitch": [_p("thunk F#4 369 Hz", 369.0, (300.0, 440.0), (0.0, 0.12), cents=50.0, min_db=-6.0)]},
    "tapTick":     {"onset": _ON},
    "coinCollect": {"length": (2.90 * 0.95, 2.90 * 1.05),
                    "pitch": [_p("clink G7 3152 Hz", 3152.0, (2900.0, 3400.0), (1.10, 2.00), cents=20.0, min_db=-12.0)],
                    "onsets": {"band": (2900.0, 3400.0), "edge": 200.0, "at": COIN_CLINKS_S, "tol": 0.005,
                               "within_db": 6.0, "min_rise_db": 2.0, "name": "clink (3.15 kHz band)"},
                    "first": {"band": (5500.0, 8000.0), "edge": 150.0, "at": 0.0, "tol": 0.020, "rel_db": -40.0,
                              "min_db": -30.0, "name": "glitter (5.5-8 kHz band)"}},
    "unlockChime": {"length": (2.10, 2.30), "onset": _ON,
                    "pitch": [_p("C6 1047 Hz", 1046.5, (1000.0, 1100.0), (0.12, 1.00), cents=20.0, min_db=-24.0),
                              _p("E6 1319 Hz", 1318.5, (1260.0, 1380.0), (0.55, 1.40), cents=20.0, min_db=-30.0),
                              _p("G6 1568 Hz", 1568.0, (1500.0, 1640.0), (1.15, 1.90), cents=20.0, min_db=-30.0),
                              _p("B6 1976 Hz", 1975.5, (1890.0, 2060.0), (1.15, 1.90), cents=20.0, min_db=-30.0)],
                    "first": {"band": (1020.0, 1075.0), "edge": 30.0, "at": 0.10, "tol": 0.020, "rel_db": -20.0,
                              "min_db": -30.0, "name": "1047 Hz partial"},
                    "hold": {"band": (1020.0, 1075.0), "edge": 30.0, "start": 0.12, "end": 1.00, "rel_db": -30.0,
                             "name": "1047 Hz partial"}},
}

# ids in SFX that are seamless loops (the file's [0, N) is the loop region)
LOOPS: set[str] = set()

# Intro -> loop pairs: the loop's sample 0 continues the intro's last sample (schedule the loop on the same player,
# right after the intro, for a sample-exact join).
CHAINS: dict[str, str] = {}

# Baked alternates: Sounds/<id>_v2.wav, _v3.wav ...; the engine picks one at random per trigger; <id>.wav is variant 1.
VARIANTS: dict[str, int] = {}

# Extra renders of one recipe at another size, e.g. a count-up tick sized by its duration D:
#   {"timeTick": {"timeTick_d025": 0.25, "timeTick_d070": 0.70}}  -> Sounds/timeTick_d025.wav ... (length = D + tail)
# check.py checks each with the base cue's peak and length SIZED_LENGTH(D).
SIZED: dict[str, dict[str, float]] = {}
SIZED_TAIL_S = 0.25


def SIZED_LENGTH(d: float) -> float:
    return d + SIZED_TAIL_S


# Music loops:  id: (bpm, bars, loop samples, RMS dBFS, true-peak ceiling dBTP)
# loop samples = round(bars * 4 * 60 / bpm * 44100) for 4/4 music.
# SPEC-motion-audio MA2 / §11.5: NO music (v552's Music button is inert; no loop was ever heard). The contract keeps its
# MusicID cases (home, level), but while Tuning/audio.json `music.enabled` is false nothing is composed, rendered or
# checked for them, and any Music/*.wav is a stray (music_enabled() below; music.py and check.py both obey it).
MUSIC: dict[str, tuple[float, int, int, float, float]] = {}
MUSIC_RMS_TOL_DB = 1.0

# AUDIO's tuning file (A2 owns its content; A1 only reads `music.enabled`). PC_AUDIO_TUNING overrides the path (self-test).
AUDIO_TUNING = os.environ.get("PC_AUDIO_TUNING") or os.path.join(APP, "App", "Resources", "Tuning", "audio.json")


def music_enabled() -> bool:
    """Tuning/audio.json `music.enabled` (SPEC-motion-audio §11.5, §13.3). A missing file or key means false (MA2)."""
    import json
    try:
        doc = json.load(open(AUDIO_TUNING, encoding="utf-8"))
    except FileNotFoundError:
        return False
    v = (doc.get("music") or {}).get("enabled", False)
    if not isinstance(v, bool):
        raise SystemExit(f"{AUDIO_TUNING}: music.enabled must be true or false, found {v!r}")
    return v


def active_music_ids() -> list[str]:
    """The MusicIDs that must have a file: all of the contract's while music is enabled, none otherwise."""
    _, music = contract_ids()
    return music if music_enabled() else []


def _enum_cases(src: str, enum: str) -> list[str]:
    m = re.search(r"enum\s+" + enum + r"\s*:[^{]*\{", src)
    if not m:
        raise SystemExit(f"cannot find enum {enum} in {CONTRACT}")
    depth, i = 1, m.end()
    while depth and i < len(src):
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        i += 1
    body = src[m.end():i - 1]
    body = re.split(r"\n\s*(?:var|func|static|init)\b", body)[0]
    out: list[str] = []
    for line in body.splitlines():
        line = line.split("//")[0]
        mm = re.match(r"\s*case\s+(.+)", line)
        if mm:
            out += [c.strip() for c in mm.group(1).split(",") if c.strip()]
    return out


def contract_ids() -> tuple[list[str], list[str]]:
    """SoundID and MusicID cases of the frozen audio contract (the source of truth for which files exist)."""
    if not os.path.exists(CONTRACT):
        raise SystemExit(f"audio contract {CONTRACT} not found (WP0 writes it; PC_AUDIO_CONTRACT overrides the path)")
    src = open(CONTRACT, encoding="utf-8").read()
    return _enum_cases(src, "SoundID"), _enum_cases(src, "MusicID")


def music_bus_ids() -> set[str]:
    """SoundIDs routed to the music bus (jingles, stings, pads): `case .a, .b: return .music` inside `var bus`."""
    if not os.path.exists(CONTRACT):
        return set()
    src = open(CONTRACT, encoding="utf-8").read()
    m = re.search(r"var bus: AudioBus \{.*?case (.*?):\s*\n\s*return \.music", src, re.S)
    return {c.strip().lstrip(".") for c in m.group(1).split(",")} if m else set()


def loop_samples(bpm: float, bars: int, beats_per_bar: int = 4, sr: int = 44100) -> int:
    return int(round(bars * beats_per_bar * 60.0 / bpm * sr))
