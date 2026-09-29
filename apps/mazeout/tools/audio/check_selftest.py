"""Self-test of tools/audio/check.py: broken copies of the shipped files (in a temp dir) must each be CAUGHT, and an
unchanged copy must pass (GAMEPROMPT §7.2 "Its self-test injects mutations and must catch all of them").

    python3 tools/audio/check_selftest.py

Generalised from apps/matchfactory/tools/audio/check_selftest.py (05424db), whose mutations named MF files (pick.wav,
vacuumHum.wav, level.wav ...). Here each mutation picks its target from specs.py: a plain one-shot, a loop, an intro ->
loop chain, a music loop. A mutation whose kind of target does not exist in our specs is reported "n/a" and is not
counted; every APPLICABLE mutation must be caught. MF's 11 mutations are all kept; 4 were added (start click, DC offset,
10 % too long, 3 dB too quiet). Exit 2 = nothing shipped yet (no Sounds/ files): the self-test cannot run.

A1 (Arrow Out) added the mutations of SPEC-motion-audio §11.6 and §11.5: uiClick / clawTick / streakPop lengths that
the generic +-10 ms tolerance lets through; coinCollect with the draft's interfering clinks, a late landing, a missing
landing, a late or missing glitter swell; unlockChime without its 1047 Hz partial or started late; a stray music file
while music is disabled; music enabled with nothing composed; a contract SoundID without a spec; a tool that names a
recording; a shipped file that is not our render (--reproduce). Every mutation also names the failure it must produce:
it only counts as CAUGHT when check.py fails FOR THAT REASON (not because of some side effect of the edit).

T9 AUDIO-2 (the kit rebuild) added 7 mutations for the new "onset" and "pitch" assertions (the same beats and pitches as
research/sounds.md §2): clawToken a semitone sharp, the clawMerge tinkle retuned +30 cents to equal temperament,
clawComplete a whole tone flat, streakPop without its F#4 under-tone, uiClick 12 ms late, clawTick 8 ms late, the coin
clinks a semitone sharp. PC_SOUNDS_DIR (specs.py) points the whole self-test at a staged set (build/p/T9/wav).
"""
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dsp  # noqa: E402
import specs  # noqa: E402
import sfx  # noqa: E402


def run(sounds, music, args=(), env=None):
    e = dict(os.environ)
    e.update(env or {})
    r = subprocess.run([sys.executable, os.path.join(HERE, "check.py"), "--sounds", sounds, "--music", music, *args],
                       capture_output=True, text=True, env=e)
    return r.returncode, [l.strip()[2:] for l in r.stdout.splitlines() if l.startswith("  - ")]


def mutate(name, fn, expect):
    """fn(sounds_dir, music_dir, tmp) edits the copy; it may return {"args": [...], "env": {...}} for check.py."""
    tmp = tempfile.mkdtemp(prefix="pc-mut-")
    s, m = os.path.join(tmp, "Sounds"), os.path.join(tmp, "Music")
    shutil.copytree(specs.SOUNDS_DIR, s)
    if os.path.isdir(specs.MUSIC_DIR):
        shutil.copytree(specs.MUSIC_DIR, m)
    else:
        os.makedirs(m)
    try:
        extra = fn(s, m, tmp)
        extra = extra if isinstance(extra, dict) else {}
        code, fails = run(s, m, extra.get("args", ()), extra.get("env"))
    finally:
        shutil.rmtree(tmp)
    hit = code != 0 and (expect is None or any(expect in f for f in fails))
    why = [f for f in fails if expect and expect in f] or fails
    verdict = ("passes" if code == 0 else "FAILS") if name.startswith("baseline") else ("CAUGHT" if hit else "missed")
    print(f"{name:62} exit {code}  {verdict}  -> {why[:2]}")
    return code, hit


def edit(path, f):
    x, _, _ = dsp.read_wav(path)
    dsp.write_wav(path, f(x))


def band_stop(x, lo, hi):
    """Removes a band (FFT mask), then re-fades the edges so the edit leaves no edge click of its own."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / dsp.SR)
    X[(f >= lo) & (f <= hi)] = 0.0
    return dsp.fade(np.fft.irfft(X, len(x)), 0.001, 0.001)


def delay(x, secs):
    k = dsp.n_of(secs)
    return dsp.fade(np.concatenate([np.zeros(k), x[:-k]]), 0.0005, 0.005)


@contextlib.contextmanager
def patched(obj, attr, value):
    old = getattr(obj, attr)
    setattr(obj, attr, value)
    try:
        yield
    finally:
        setattr(obj, attr, old)


def rerender(path, sid, **patches):
    """Writes sid rendered by our own recipe with module attributes patched (e.g. other landing times)."""
    with contextlib.ExitStack() as st:
        for key, value in patches.items():
            mod, attr = key.split(".")
            st.enter_context(patched({"specs": specs, "sfx": sfx}[mod], attr, value))
        dsp.write_wav(path, sfx.RECIPES[sid](sid, 1))


def summed_copies(freq, n, strikes, attack, tau):
    """The §11.3 draft's clinks: one independent copy per landing, summed (they interfere 85 ms apart)."""
    y = np.zeros(n)
    k = dsp.n_of(1.4)
    for s0 in strikes:
        dsp.place(y, dsp.osc_sin(freq, k) * dsp.env_exp(k, attack, tau), s0)
    return y


def repitch(x, semitones):
    """Resamples to shift every pitch by `semitones` (and time by the same ratio), then pads/cuts back to the length."""
    r = 2.0 ** (semitones / 12.0)
    src = np.arange(0.0, len(x) - 1, r)
    y = np.interp(src, np.arange(len(x)), x)
    y = np.concatenate([y, np.zeros(max(0, len(x) - len(y)))])[:len(x)]
    return dsp.fade(y, 0.0005, 0.005)


def sharp_restruck(freq, n, strikes, attack, tau):
    """The coin's G7 ring struck a semitone sharp (every restruck partial retuned)."""
    return sfx.__dict__["_orig_restruck"](freq * 2.0 ** (1.0 / 12.0), n, strikes, attack, tau)


sfx.__dict__.setdefault("_orig_restruck", sfx.restruck)


def pick_targets():
    ids, music = specs.contract_ids()
    ids = [i for i in ids if i in specs.SFX]
    plain = [i for i in ids if i not in specs.LOOPS and i not in specs.CHAINS and i not in specs.CHAINS.values()]
    # a one-shot whose target leaves 3 dB of headroom, so "+3 dB" is a level error, not only a clipped file
    hot = next((i for i in plain if specs.SFX[i][2] <= -4.0), plain[0] if plain else None)
    return {
        "oneshot": plain[0] if plain else None,
        "hot": hot,
        "other": plain[1] if len(plain) > 1 else None,
        "loop": next((i for i in ids if i in specs.LOOPS and i not in specs.CHAINS.values()), None)
                or next((i for i in ids if i in specs.LOOPS), None),
        "chain": next(iter(specs.CHAINS.items()), None),
        "music": next((m for m in specs.active_music_ids() if m in specs.MUSIC), None),
    }


def cases(t):
    S = lambda s, sid: os.path.join(s, sid + ".wav")          # noqa: E731
    one, hot, other, loop, chain, mus = t["oneshot"], t["hot"], t["other"], t["loop"], t["chain"], t["music"]
    ids = set(specs.contract_ids()[0])
    has = lambda sid: sid if sid in ids and sid in specs.SFX else None   # noqa: E731
    # name: (target or None = n/a, fn(s, m, tmp), the failure text it must produce)
    c = {"baseline (unchanged copy)": (True, lambda s, m, tmp: None, None)}
    c[f"missing {one}.wav"] = (one, lambda s, m, tmp: os.remove(S(s, one)), "missing")
    c[f"{hot} +3 dB too hot"] = (hot, lambda s, m, tmp: edit(S(s, hot), lambda x: x * 10 ** (3 / 20)), "peak")
    c[f"{other or one} 3 dB too quiet"] = (other or one, lambda s, m, tmp: edit(S(s, other or one),
                                                                               lambda x: x * 10 ** (-3 / 20)), "peak")
    c[f"{one} ends on a click"] = (one, lambda s, m, tmp: edit(S(s, one), lambda x: np.concatenate([x[:-1], [0.05]])),
                                   "ends at")
    c[f"{one} starts on a click"] = (one, lambda s, m, tmp: edit(S(s, one), lambda x: np.concatenate([[0.05], x[1:]])),
                                     "starts at")
    c[f"{one} stereo"] = (one, lambda s, m, tmp: edit(S(s, one), lambda x: np.stack([x, x], 1)), "format")
    c[f"{one} DC offset"] = (one, lambda s, m, tmp: edit(S(s, one), lambda x: x + 0.01), "DC offset")
    c[f"{one} 10 % too long (silence appended)"] = (one, lambda s, m, tmp: edit(
        S(s, one), lambda x: np.concatenate([x, np.zeros(max(int(len(x) * 0.10), dsp.n_of(0.02)))])), "length")
    c[f"{loop} loop cut short (seam jump)"] = (loop, lambda s, m, tmp: edit(S(s, loop), lambda x: x[:-37]), "seam")
    c[f"{loop} fades out at the end"] = (loop, lambda s, m, tmp: edit(S(s, loop), lambda x: dsp.fade(x, 0, 0.3)),
                                         "seam")
    if chain:
        intro = chain[0]
        c[f"{intro} not phase-aligned to {chain[1]}"] = (intro, lambda s, m, tmp: edit(S(s, intro),
                                                                                      lambda x: np.roll(x, 50)), "->")
    else:
        c["chain intro not phase-aligned"] = (None, None, None)
    c[f"music {mus} one sample short"] = (mus, lambda s, m, tmp: edit(S(m, mus), lambda x: x[:-1]), "samples")
    c[f"music {mus} 3 dB too loud"] = (mus, lambda s, m, tmp: edit(S(m, mus), lambda x: x * 10 ** (3 / 20)), "RMS")
    c[f"music {mus} linear render (no wrapped tails)"] = (mus, lambda s, m, tmp: edit(
        S(m, mus), lambda x: np.concatenate([np.zeros((dsp.n_of(0.4), 2)), x[dsp.n_of(0.4):]])), "seam")
    c["stray extra file"] = (one, lambda s, m, tmp: shutil.copy(S(s, one), os.path.join(s, f"{one}_old.wav")), "stray")

    # --- SPEC-motion-audio §11.6 (each passes the generic checks and fails only the §11.6 assertion)
    pad = lambda secs: (lambda x: np.concatenate([x, np.zeros(dsp.n_of(secs))]))   # noqa: E731
    ui, tick, pop, coin, chime = has("uiClick"), has("clawTick"), has("streakPop"), has("coinCollect"), has("unlockChime")
    c["uiClick 43 ms (generic +-10 ms passes; §11.6 25-40 ms)"] = (
        ui, lambda s, m, tmp: edit(S(s, ui), pad(0.008)), "uiClick: length")
    c["clawTick 48 ms (generic passes; §11.6 <= 45 ms)"] = (
        tick, lambda s, m, tmp: edit(S(s, tick), pad(0.008)), "clawTick: length")
    c["streakPop 188 ms (generic passes; §11.6 0.18 s)"] = (
        pop, lambda s, m, tmp: edit(S(s, pop), pad(0.008)), "streakPop: length")
    c["coinCollect clinks as summed copies of one slow G7 partial (the §11.3 draft)"] = (
        coin, lambda s, m, tmp: rerender(S(s, coin), coin, **{"sfx.restruck": summed_copies,
                                                              "sfx.COIN_G7": (0.0, 0.035, 0.40, 0.25)}),
        "raises the band only")
    late = list(specs.COIN_CLINKS_S)
    late[2] += 0.012
    c["coinCollect 3rd landing 12 ms late"] = (
        coin, lambda s, m, tmp: rerender(S(s, coin), coin, **{"specs.COIN_CLINKS_S": late}), "wants 1.290")
    c["coinCollect one landing missing (4 clinks)"] = (
        coin, lambda s, m, tmp: rerender(S(s, coin), coin, **{"specs.COIN_CLINKS_S": specs.COIN_CLINKS_S[:4]}),
        "wants exactly 5")
    c["coinCollect glitter starts 60 ms late"] = (
        coin, lambda s, m, tmp: edit(S(s, coin), lambda x: np.concatenate(
            [np.zeros(dsp.n_of(0.06)), dsp.fade(x[dsp.n_of(0.06):], 0.005, 0.0001)])), "glitter")
    c["coinCollect without its glitter swell"] = (
        coin, lambda s, m, tmp: edit(S(s, coin), lambda x: band_stop(x, 5400.0, 8100.0)), "glitter")
    c["unlockChime without its 1047 Hz partial"] = (
        chime, lambda s, m, tmp: edit(S(s, chime), lambda x: band_stop(x, 1000.0, 1100.0)), "1047 Hz")
    c["unlockChime started 50 ms late"] = (
        chime, lambda s, m, tmp: edit(S(s, chime), lambda x: delay(x, 0.05)), "1047 Hz")

    # --- T9 AUDIO-2: the same beats and pitches (specs.CUE_ASSERT "onset" / "pitch"), each passing every older check
    token, merge, done = has("clawToken"), has("clawMerge"), has("clawComplete")
    c["clawToken a semitone sharp (resampled; same length)"] = (
        token, lambda s, m, tmp: edit(S(s, token), lambda x: repitch(x, 1.0)), "clawToken: pitch bell C6")
    c["clawMerge tinkle retuned to equal temperament (+30 cents)"] = (
        merge, lambda s, m, tmp: edit(S(s, merge), lambda x: repitch(x, 0.30)), "clawMerge: pitch tinkle")
    c["clawComplete a whole tone flat (resampled)"] = (
        done, lambda s, m, tmp: edit(S(s, done), lambda x: repitch(x, -2.0)), "clawComplete: pitch thunk")
    c["streakPop without its F#4 under-tone"] = (
        pop, lambda s, m, tmp: edit(S(s, pop), lambda x: band_stop(x, 300.0, 440.0)), "streakPop: pitch under-tone")
    c["uiClick 12 ms of leading silence (late on its beat)"] = (
        ui, lambda s, m, tmp: edit(S(s, ui), lambda x: np.concatenate([np.zeros(dsp.n_of(0.012)),
                                                                        x[:len(x) - dsp.n_of(0.012)]])),
        "uiClick: onset")
    c["clawTick 8 ms late (onset)"] = (
        tick, lambda s, m, tmp: edit(S(s, tick), lambda x: np.concatenate([np.zeros(dsp.n_of(0.008)),
                                                                            x[:len(x) - dsp.n_of(0.008)]])),
        "clawTick: onset")
    c["coinCollect clinks retuned a semitone up (G#7)"] = (
        coin, lambda s, m, tmp: rerender(S(s, coin), coin, **{"sfx.restruck": sharp_restruck}),
        "coinCollect: pitch clink")

    # --- §11.5 music switch, the contract, provenance, reproduction
    def stray_music(s, m, tmp):
        shutil.copy(S(s, one), os.path.join(m, "home.wav"))

    def music_on(s, m, tmp):
        doc = json.load(open(specs.AUDIO_TUNING, encoding="utf-8"))
        doc.setdefault("music", {})["enabled"] = True
        p = os.path.join(tmp, "audio.json")
        json.dump(doc, open(p, "w", encoding="utf-8"))
        return {"env": {"PC_AUDIO_TUNING": p}}

    def contract_plus(s, m, tmp):
        src = open(specs.CONTRACT, encoding="utf-8").read()
        new = src.replace("case uiClick,", "case uiClick, levelWin,", 1)
        assert new != src, "the contract's SoundID case line moved; update this mutation"
        p = os.path.join(tmp, "AudioContract.swift")
        open(p, "w", encoding="utf-8").write(new)
        return {"env": {"PC_AUDIO_CONTRACT": p}}

    def tool_names_recording(s, m, tmp):
        d = os.path.join(tmp, "tools")
        os.makedirs(d)
        for f in os.listdir(HERE):
            if f.endswith(".py"):
                shutil.copy(os.path.join(HERE, f), d)
        # built from fragments: check.py scans THIS file too, and no literal here may contain its needles
        ref = "/".join(["rese" + "arch", "sound" + "-refs", "phone_click.wav"])
        with open(os.path.join(d, "sfx.py"), "a", encoding="utf-8") as fh:
            fh.write('\n_REF = "' + ref + '"\n')
        return {"args": ["--tools", d]}

    def one_lsb(s, m, tmp):
        edit(S(s, one), lambda x: np.concatenate([x[:len(x) // 2], [x[len(x) // 2] + 1.0 / 32767], x[len(x) // 2 + 1:]]))
        return {"args": ["--reproduce"]}

    music_off = not specs.music_enabled()
    c["stray Music/home.wav while music is disabled (§11.5)"] = (one if music_off else None, stray_music, "stray")
    c["audio.json music.enabled true with nothing composed"] = (one if music_off else None, music_on,
                                                                "music.enabled is true")
    c["contract gains a SoundID with no spec/file"] = (one, contract_plus, "levelWin")
    c["a tool names a recording (provenance)"] = (one, tool_names_recording, "provenance")
    c[f"{one} 1 LSB off our render (--reproduce)"] = (one, one_lsb, "reproduce")
    return c


def main():
    if not os.path.isdir(specs.SOUNDS_DIR) or not any(f.endswith(".wav") for f in os.listdir(specs.SOUNDS_DIR)):
        print(f"check_selftest: no shipped sounds in {specs.SOUNDS_DIR} yet; nothing to mutate")
        return 2
    t = pick_targets()
    if t["oneshot"] is None:
        print("check_selftest: specs.py has no one-shot SoundID with a target; nothing to mutate")
        return 2
    print("targets:", {k: v for k, v in t.items()})
    caught = applicable = 0
    missed = []
    for name, (target, fn, expect) in cases(t).items():
        if target is None or fn is None:
            print(f"{name:62} n/a (no such target in specs.py)")
            continue
        code, hit = mutate(name, fn, expect)
        if name.startswith("baseline"):
            if code != 0:
                print("check_selftest: the UNCHANGED copy fails check.py; fix the audio before testing the checker")
                return 1
            continue
        applicable += 1
        caught += hit
        if not hit:
            missed.append(name)
    print(f"caught {caught}/{applicable} applicable mutations" + (f"; MISSED: {missed}" if missed else ""))
    return 0 if caught == applicable else 1


if __name__ == "__main__":
    sys.exit(main())
