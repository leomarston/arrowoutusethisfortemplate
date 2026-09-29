# Maze Out — sounds (analyst passes 1 + 2, 2026-09-25, no phone)

Copying line: the files in `research/sound-refs/` are references to LISTEN to and compare against only. Nothing in
`App/Resources` may derive from them: every cue below gets OUR OWN synthesis from the recipe column. VERIFIED / INFERRED as in
motion.md. Later analysts: extend the tables in place and log your pass in §7.

## 0. Sources
| source | audio | notes |
|---|---|---|
| **PHONE** (v552) runner `rec` clips | **the recorder captures app audio** (pass 2 correction): `S1-L48-play-intro` and `S1-L49-play-intro-superhard` hold the Play-button click (identical copies, corr 1.000); `S1-L50-win-seq-2-continue` holds the whole home-return sequence (0.16–4.71 s, then the clip's edit-list cut). Every other clip is **digital zero** — and since the capture path works, that silence is the game's own. | 48 kHz mono, movie time = video time (`mfx audio` applies the edit list). Snippets: `sound-refs/phone_*.wav` (gitignored). Numbers: `motion-tools/out/phone_audio.txt`, `phone_xcorr.txt`, `phone_cues.txt`; spectrogram `motion-frames/spec_phone_S1-L50-win-seq-2-continue.png`. |
| phone settings (owner state, meta-029) | **Sound ON, Music OFF, Haptic ON**, Notifications ON | so no clip can say anything about music; everything else is audible |
| **YT-A** (owner video L1–L20; v552 look) | 44.1 kHz → `sound-refs/YT1-L01-20-full.wav` | 37 non-silent segments in 505 s, exact digital silence between cues. Settings never shown. |
| **YT-B** (owner video L11–L38; older build) | → `sound-refs/YT2-L11-38-full.wav` | 98 segments; Settings seen: Sound ON, Music OFF, Haptic ON. |
Pass-1 per-cue snippets: `cue_click_YTA_27.12.wav`, `cue_coin_YTA_94.52.wav`, `cue_coin_YTB_108.21.wav`, `cue_win_YTB_102.05.wav`,
`cue_unlock_YTB_75.80.wav`, `bump_silence_YTB_1249.0.wav`; `out/sound_inv_{A,B}.txt`, `out/cues.txt`, `out/bandtrace.txt`.

## 1. Verdict: in-level play is silent — now VERIFIED on v552
| silent event (v552 clip, audio digital zero) | where |
|---|---|
| arrow tap / ripple, exit slide, sparkle stars, dots, combo colours (blue, blue, violet) | S1-L47-headtap-long-exit, S1-L52-three-exits, S1-P01, S1-P02, S1-L33, S1-L35 |
| bump: slide, red arrow, ✖ badge, red vignette, heart break | S1-L47-bump-1, S1-L48-bump-2 |
| box break, key → door, pipe pass + shatter | S1-L50-box-break, S1-L33-key-first, S1-L35-pipe-break |
| level intro after the Play click (zoom-out, draw-in, HUD, big timer, hearts) | S1-L48-play-intro 0.38–3.8, S1-L49 |
| **win celebration** (wave, MAZE OUT! sign, confetti, fireworks), the win panel, the Streak strip on it | S1-L50-win-seq-1 (9.95 s, unskipped) |
| "Out of Time!" popup (9.5 s idle) | S1-L52-short-exit-win |
| bulb hint (pan + green blinks), hourglass booster (flight, icing, frost vignette), Weekly Contest tutorial overlay, home idle 2 s, tap on the scientist, the Out of Time popup after a real timeout | META-L062-bulb-hint, META-L062-hourglass-freeze, S1-weekly-contest-open, S1-home-idle-L48, META-home-tap-scientist, META-L062-timeout-0s |
YT-A (v552 look) agrees on all of these (pass 1). Reviews (web-research §11: "pretty weird playing in complete silence") agree.

What sounds on v552: **the UI click, and the meta/home cues after a win** (Claw token, multiplier merge, Claw bar count-up,
Streak strip pops, coin collect). The feature-unlock chime (YT-A/B) was not met on the phone yet (no unlock in the recorded
clips) but is the same build family → keep it.

## 2. Cue inventory
### 2.1 Summary table
| # | cue | evidence | trigger | onset vs visual | length | level | character | bus |
|---|---|---|---|---|---|---|---|---|
| 1 | **UI click** | **v552 VERIFIED** (Play, 2 clips) = YT-A click (corr **0.993** after alignment) | every UI button **on release** (Play, shop tabs, settings, pause, resume, X, unlock dismiss, tap-to-skip the win); **not** on the win panel's Continue (VERIFIED v552 + YT-A) | release; the next screen cuts in +0.06–0.08 s later | 20 ms above −20 dB, ≈ 60 ms to silence | −7.6 dBFS peak (phone and YT-A captures identical) | soft low "tock": body 215–430 Hz (strongest ≈ 345–352 Hz), transient centroid ≈ 2.3–2.5 kHz | SFX |
| 2 | **Claw token appears** | v552 VERIFIED (1 instance) | the purple hex token "+1" popping at the capsule machine right after the home cut | home cut ≈ 0.17 → onset **0.225** (token full ≈ 0.30) | ≈ 0.42 s above −20 dB, tail to 0.75 | −1.6 dBFS | sparkly shimmer (centroid 5.9 kHz, partials 4.3 / 9.8 kHz) over a sustained **C6 ≈ 1049 Hz** bell; ends on low 330–430 Hz body | SFX |
| 3 | **multiplier merge** | v552 VERIFIED (1) | the orange x25 badge merging into the token (white burst ≈ 0.85) | **0.805** | 95 ms above −20 dB, decays to ≈ 1.2 s | −2.9 dBFS | low thump (C#4 ≈ 275 Hz, B3/A3 below) then a bell tinkle C#6 ≈ 1090 + F6 ≈ 1371 Hz + ≈ 4.1 kHz | SFX |
| 4 | **Claw bar count-up ticks** | v552 VERIFIED (1 run of 7) | the Claw bar counting 156 → 181 after the token reaches the bar icon (1.997) | first tick **1.910**, then every **57 ms** (1.910 1.955 2.020 2.085 2.125 2.170 2.250) | ≈ 30 ms per tick, 0.36 s run | −2.5 dBFS | buzzy harmonic tick, fundamental ≈ **700 Hz (F5)** with partials 680–850 Hz, steady pitch | SFX |
| 5 | **bar-complete thunk** | v552 VERIFIED (1) | end of the count-up | **2.270** | 0.12 s above −20 dB | −5.6 dBFS | short tone **F#4 ≈ 369 Hz**, slight downward glide | SFX |
| 6 | **Streak strip pops ×3** | v552 VERIFIED (1 run) | the chip strip lighting x100 (≈ 3.0–3.08) and the badge flash (3.48) | **3.050, 3.200, 3.420** | 0.13–0.16 s each | −1.9 / −1.8 / −4.9 dBFS | round "bloop": D5 ≈ 586 Hz over F#4 ≈ 369 Hz; the 2nd/3rd carry a 6.5–10 kHz sparkle | SFX |
| 7 | **coin collect** | **v552 VERIFIED** = YT-A cue 2 (swell NCC 0.55, clinks at the same 3.15 + 9.3 kHz partials) | coins flying from the capsule machine to the coin pill after the Claw/Streak beats | swell **3.18**; clinks **4.300 4.365 4.450 4.535 4.620** (≈ 80 ms apart) = the 5 coin landings (counter +4 each at 4.29 … 4.69) | ≈ 2.9 s (YT-A; the phone clip is cut at 4.71) | clinks 0 dBFS (clipping, 2 samples), swell −7 dB | glittery swell 6.5–6.9 kHz, then metallic clinks (**3152 Hz G7 + 9.3 kHz D9**), bell tail (YT-A 1.5 s) | SFX |
| 8 | unlock chime | YT-A + YT-B (5 copies, pass 1); not met on the phone yet | the feature-unlock overlay appearing | with the dark overlay, ≈ 0.2 s before the icon pops | 2.0–2.25 s | −2.4 to −6.5 dBFS | low C2 thump then a sustained Cmaj7 bell/pad shimmer (C6 E6 G6 B6 E7) | SFX |
| 9 | win fanfare (older) | YT-B only | the last arrow leaving | with the wave | 4.7 s | 0 dBFS | brassy C-major stabs + cheer + firework pops | SFX — **not in v552** (VERIFIED silent win) |
| — | coin collect (older) | YT-B only | — | — | 1.4–1.7 s | — | clinks only | not v552 |

v552 home-return order (S1-L50-win-seq-2-continue; visual beats in motion.md §6.5): Continue (no click) → cut 0.17 → cue 2
(0.225) → cue 3 (0.805) → [dim lifts, token flies to the bar] → cue 4 ticks (1.91–2.25) → cue 5 (2.27) → [Streak strip] → cue 6
pops (3.05, 3.20, 3.42) → cue 7 swell (3.18) → clinks (4.30–4.62). Relative loudness in the same capture: the home cues peak
≈ 6 dB above the click.

### 2.2 Click (cue 1) — detail and recipe
- v552 Play click: 59.9 ms from first to last non-zero sample, peak −7.6 dBFS, strongest partials 352 / 316 / 387 / 422 Hz
  (F4 ≈ 352), centroid 2.3–2.5 kHz. YT-A median of 60 copies: 20 ms above −20 dB, silent after 25 ms; 258–431 Hz.
- **Recipe (ours):** sine 380 Hz gliding to 300 Hz over 15 ms, attack 1 ms / exponential decay τ = 6 ms, plus a 3 ms noise
  burst band-passed 1.8–3 kHz at −10 dB under the tone; total 30 ms; −6 dBFS peak; 44.1 kHz mono 16-bit; zero-crossing ends.
  One sample for all buttons. Fire on RELEASE, same frame as the button's action.

### 2.3 Coin collect (cue 7) — detail and recipe (pass 1, now v552-confirmed)
| time from onset | layer | bands |
|---|---|---|
| 0 → 0.15 s | swell attack | 6–7.2 kHz glitter rises from −67 to −26 dB |
| 0.15 → 0.55 s | sparkle + soft bells | glitter steady; a bell pair ≈ 3.14 kHz (G7) + ≈ 9.3 kHz (D9) ≈ 12 dB under the later clinks |
| 0.55 → 1.0 s | glitter only | 6–7 kHz steady (−30 dB) |
| 1.05–1.45 s (YT-A) / 1.12–1.44 s (v552) | **clinks** — one per coin landing on the pill | 3.15 kHz + 9.3 kHz (+ ≈ 5.2 kHz) strikes, loudest part |
| → 2.9 s | tail | 3.14 kHz bell rings down ≈ 32 dB/s; glitter fades by 2.7 s |
**Recipe (ours):** (a) glitter: 30 sine grains/s, random 5.5–7.5 kHz, 25 ms Hann each, 0.15 s attack / 0.85 s sustain /
1.5 s release, −28 dB; (b) clink: inharmonic partials f1 = 3150 Hz, f2 = 2.96·f1, f3 = 1.65·f1 (amps 1, 0.6, 0.25), attack 2 ms,
decay τ 0.25 s (f2, f3 0.08 s); (c) **drive the clinks from our coin-fly animation** (one per coin landing, ≈ 80 ms apart on
v552, 5 coins for +20) and start the glitter ≈ 1.1 s before the first landing. Peak −3 dBFS.

### 2.4 New v552 home cues (2–6) — recipes (ours)
| cue | recipe |
|---|---|
| 2 token appears | 0.45 s: noise shimmer band-passed 4–10 kHz (attack 30 ms, decay τ 0.15 s, −12 dB) + a bell on C6 1047 Hz (sine + 2.76× partial at −14 dB, attack 5 ms, decay τ 0.25 s) + a soft 330–430 Hz body under the tail (−18 dB); peak −3 dBFS |
| 3 merge | 70 ms sine thump 290 → 210 Hz (attack 2 ms, τ 25 ms) + two bells C#6 1109 Hz and F6 1397 Hz starting 15 ms later (τ 0.15 s, −6 dB) + a 4.1 kHz ping (τ 60 ms, −12 dB); total ≈ 0.4 s |
| 4 count-up tick | 28 ms tick: square-ish wave at 700 Hz (odd harmonics 1, 1/3, 1/5 …, low-passed 6 kHz), attack 1 ms, decay τ 10 ms; **one tick per displayed counter step**, 57 ms apart on v552; peak −4 dBFS |
| 5 thunk | 120 ms sine 380 → 355 Hz, attack 3 ms, τ 40 ms, + 1 ms click; −6 dBFS |
| 6 streak pop | 140 ms "bloop": sine 600 → 370 Hz exponential glide over 60 ms, τ 50 ms; 2nd and 3rd add a 6.5–10 kHz noise sparkle (τ 80 ms, −10 dB); fire on each chip-light / badge-flash event |

### 2.5 Unlock chime (cue 8, pass 1)
0–0.1 s low thump (C2/F2), then from 0.1 s a sustained C6 (1055 Hz) with E6 1313, G6 1572, B6 1981, E7 2627 Hz shimmering in, −16 dB
plateau, release by 2.0–2.25 s. Recipe (ours): 4-voice FM bell (ratio 3.5, index 1.2 → 0.3) on C6, E6 (+0.5 s), G6 and B6
(+1.1 s), 1.8 s decay each, over a 65 Hz sine thump (5 ms attack, τ 0.3 s); peak −4 dBFS; 2.2 s.

### 2.6 Win fanfare (cue 9, YT-B only) — keep only behind a deviation flag
0–0.4 s swoosh/thump (F2–A3), 0.4–2.0 s brassy C-major stabs + melody (C2 bass; E5 F5 G5 B5 C6 E6 G6 C7), 1.5–2.3 s noisy
cheer, 2.5–3.6 s 6–8 firework pops, tail to 4.7 s (+14 cents sharp). v552 plays **nothing** at the win.

## 3. Music
| question | answer | source |
|---|---|---|
| does a Music toggle exist | yes, home Settings: Sound / Music / Haptic (the in-level Pause panel has only Sound + Haptic) | meta-029, shots/007 |
| owner's state | **Music OFF** (Sound ON, Haptic ON) | meta-029 |
| any music heard | none — but with Music OFF on the phone and in YT-B, and unknown in YT-A, **the existence of a music loop is still unknown** | — |
| BPM / key / instruments / loop length | unknown | clips-needed #4 (turn Music ON, record, turn it back OFF) |

## 4. Haptics
Haptic toggles exist (pause panel + settings), owner state ON. Video cannot record them. INFERRED from the genre: a light impact
on a successful tap, a heavier one on a bump. Only by feel on the phone (clips-needed #4).

## 5. What our build should do (for the spec writers; the owner decides)
1. **Default = v552:** the click (cue 1) on every UI button release (not on the win panel's Continue); the home-return cues 2–7
   locked to their animation beats (token, merge, count-up ticks per step, thunk, streak pops, coin glitter + one clink per
   landing coin); the unlock chime (cue 8) with every feature-unlock overlay; **everything in a level and the win celebration
   silent**.
2. The SFX bus follows the Sound toggle; a Music bus exists behind the Music toggle but plays nothing until a phone check with
   Music ON finds a loop.
3. Optional, flagged as a deviation from v552: our own win fanfare (cue 9 recipe).
4. The checker (GAMEPROMPT §7) should assert: click 25–35 ms, peak −6 dBFS ±1.5, fired on release; coin cue ≈ 2.9 s with one
   clink per coin 70–100 ms apart, first clink 1.05–1.15 s after the glitter onset; count-up ticks = number of counter steps,
   57 ± 10 ms apart; chime 2.2 s ±0.1 with C6 present from 0.1 s; zero output during a level and during the celebration.

## 7. Pass log
- 2026-09-25 03:55 — pass 1: PHONE audio read as unusable (all clips then were silent moments); inventory built from the owner's
  two videos. The unlock chime found hiding inside the YT-A coin segment.
- 2026-09-25 05:25 — pass 2: the part-2 PHONE clips prove the recorder captures app audio (Play click, home-return cues) →
  the silence of taps, exits, bumps, obstacles, the intro and the whole win is v552's own (VERIFIED). v552 click = YT-A click;
  v552 coin cue = YT-A cue 2; five new v552 home cues (token, merge, count-up ticks, thunk, streak pops) with recipes. Owner
  state Sound ON / Music OFF / Haptic ON (meta-029) → music still unknown.

## Meta explorer additions (2026-09-25 04:27–07:40, owner settings Sound ON / Music OFF / Haptic ON)
- All 11 `video/META-*.mov` tracks are digital zero → more VERIFIED-silent v552 moments: home idle 15 s (META-home-idle-12s), tapping the
  scientist, a tape-bundle bump (META-L062-tape-blocked-bump: tap + bump + red flash inside the clip), the timer's last 7 s + the "Out of
  Time!" popup entrance (META-L062-timer-last-seconds: no tick, no alarm, no popup sting), the hourglass flight/frost and the bulb pan/blink
  (both clips start after the booster tap, so the booster's own click is not covered).
- The Settings **Music** button is inert on v552 (4 attempts left it OFF; Sound toggles fine) → no music can be enabled (meta.md §4).
