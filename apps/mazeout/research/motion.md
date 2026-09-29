# Maze Out — motion (analyst passes 1 + 2, 2026-09-25, no phone)

Tables an engineer can type in. Every number says where it comes from:
**VERIFIED** = measured on a named clip with real presentation timestamps (mfx) or on a lossless runner shot;
**INFERRED** = reasoned from fewer / noisier observations, from another build, or from a still. Later analysts: extend each
section in place (add rows, keep the source column) and log your pass in §10.

Pass 2 (05:20) added the 12 phone clips of player part 2 (v552, mostly 60 Hz) and re-measured what pass 1 could only take
from the owner's videos. **Pass-1 statements that pass 2 corrected** are replaced in place and listed in §10.

## 0. Sources and conventions

| id | what | frame rate | audio | build / look |
|---|---|---|---|---|
| **PHONE** | `research/video/S1-*.mov`, `F00/F01`, `META-*` (runner `rec`, iPhone 15, 393×852 pt) + runner shots `research/shots/*.png`, `research/bot/tmp/L0NN-*-rNN.png` (lossless sRGB, 1178 px wide = 2.997 px/pt) | variable (≤ 60 Hz; a timestamp gap = nothing moved) | **records app audio** (pass 2: the Play click and the home-return cues are in the tracks; silent moments are genuinely silent — see sounds.md) | **v552 — the build we copy**: black arrows on white, "MAZE OUT!" win splash, 2 boosters |
| **YT-A** | owner's video `research/video/owner/V1-levels-01-20.mp4` (505 s, L1–L20 incl. the FTUE) | 25 fps constant | yes | blue arrows on pale-blue board, 4 boosters, same "MAZE OUT!" win splash + popups as the phone → the closest cousin of v552 (its win timing matches v552 within 0.05 s, §6.6) |
| **YT-B** | owner's video `research/video/owner/V2-levels-11-38.mp4` (1683 s, L11–L38) | 59.64 fps constant | yes (Music OFF) | "Well Done!" win splash, 5-tab home, Elevator obstacle → an **older / A-B cohort build**; timings only where the phone has none, never looks |

- Times: `t` = presentation time in that clip (**movie time**: `mf.raw()` and `mfx audio` both apply the edit list, so video
  and audio of one clip share one clock; t = 0 at the clip's first frame). YT: seconds into the video.
- Distances in **pt** of the 393-pt-wide screen or in **cells** (board pitch). Colours only from lossless shots; video colours
  are marked "(video)".
- Tools: `research/motion-tools/` (README there). Raw numbers: `research/motion-tools/out/*.txt`. Frame sheets:
  `research/motion-frames/` (gitignored). Pass 2 scripts: `bumptrack.py`, `bumpfx.py`, `exittrack.py`, `exitfit2.py`,
  `introzoom.py`, `introdraw.py`, `introfit.py`, `introdraw2.py`, `hud_intro2.py`, `winscan_v552.py`, `geom.py`, `pitchest.py`,
  `phone_audio.py`, `phone_xcorr.py`, `phone_cues.py`.
- Capture facts: part-2 `rec` clips hold 2.8–10 s (the recorder improved); `S1-L50-win-seq-2-continue` has an **edit-list
  cut at movie t = 4.709** (≈ 2 s of wall time missing; its audio after the cut is zero-filled).

## 1. Quick sheet (the numbers most code needs)

| thing | value | source |
|---|---|---|
| board fit | `pitch = clamp(393 / (cols + 2), 393/28, 393/14)` pt → one empty cell of margin each side; board centred at **(196.5, 439.2) pt** | VERIFIED 30 recorded levels, max error 0.02 pt (§2.1) |
| zoom limits | pitch **14.04 … 28.07 pt absolute** (not relative to fit): a 12-col board opens at max zoom, a 26-col board cannot zoom out | VERIFIED shots 005/006, meta-060…063, L50 (§6.7) |
| stroke | **0.22 × pitch** (4.0 pt at 17.87), black #000000, round tail cap, outer corners rounded (centre-line fillet ≈ 0.125 pitch), inner corners ≈ sharp | VERIFIED 8 start shots, 6 pitches (§2.2) |
| arrowhead | isosceles triangle, base **0.61 pitch** wide at −0.22 pitch, tip at **+0.39 pitch** (from the head cell centre) | VERIFIED 8 start shots (§2.2) |
| cell dots | #C5E1FF discs, **⌀ 0.192 pitch**, drawn under every arrow cell from the start (a never-occupied cell has none) | VERIFIED shots 136/141/043 + 003 (§2.3) |
| input | fires on **release**; press does nothing; buttons scale to **0.95** on touch-down (instant) | VERIFIED P01, shots 009/010; Play + Continue clips (§6.3) |
| exit start latency | ≤ 1 frame after release | VERIFIED 11 exits |
| exit kinematics (cells) | `s(τ) = 73.86·τ − 23.37·(1 − e^(−τ/0.353))` cells; `v(τ) = 73.86 − 66.19·e^(−τ/0.353)` c/s | VERIFIED **11 exits, 203 samples, 4 pitches (14.0, 17.9, 26.2, 28.1 pt), RMS 0.082 cells** (§3.3) |
| exit T(d) | head travels d cells in `T ≈ 0.114 + 0.0189·d` s (2–45 c, RMS 21 ms); exact table §3.3 | VERIFIED (same data) |
| exit colour | black → **#10A2EF** linear cross-fade 0.09–0.10 s; streak ladder: taps 1–2 blue, 3rd violet, 4th+ rainbow (window ≈ 1.25 s); violet/rainbow = a colour **field fixed in space**, not carried by the body | colour VERIFIED; ladder VERIFIED v552 (3-tap clip) + INFERRED W from 1630 video taps (§3.4) |
| bump | slides along its own path at **constant speed** to the blocker, `T_out ≈ 0.075 + 0.025·gap_cells` s, back easeOutQuad **0.14 s**; turns **#EE0912** (stays red); blocker flashes red; ✖ badge; heart **breaks in two**; red edge vignette 0.33 s; **silent** | VERIFIED 2 v552 clips (§4) |
| level intro | Play click → hard cut +0.06 s → board **zoom 1.49 → 1.0, easeOutCubic 1.35 s** while arrows draw tail→head (0.32 s + 21.6 ms/cell) → HUD drop at cut +1.02 s (easeOutBack 0.33 s) → boosters +0.08 s → hearts pop from +0.38 s | VERIFIED S1-L48-play-intro 60 Hz (§6.1) |
| win | last tail leaves its cell → rainbow dot wave 0.5 s → sign flies in (+0.40) → MAZE / arrow / OUT! → dim 0.33 s → confetti + fireworks → panel **instant at wave + 3.94 s**; silent | VERIFIED S1-L50-win-seq-1 60 Hz (§6.6) |
| popups | appear / disappear instantly (no scale spring); tutorial overlays: instant dim then staggered pops | VERIFIED v552 + YT-B (§6.3) |

## 2. Board geometry (NEW in pass 2)

### 2.1 Fit, margins, centring
| item | value | source |
|---|---|---|
| fit pitch | `393 / (cols + 2)` pt: the board plus **one empty cell each side** spans the 393-pt width (20 cols → 17.864; 25 → 14.556; 13 → 26.200) | VERIFIED 30 levels L32–L61, all within 0.02 pt (`levels/*.json` pitch_pt vs the formula) |
| clamps | ≥ **14.036 pt** (= 393/28, a 26-col board) and ≤ **28.071 pt** (= 393/14, a 12-col board); L50 (10 cols) opens at 28.07 and is centred (56 pt margins) | VERIFIED L50, L54, L59 (26 cols → 14.04) |
| centre | board centre (middle of the cell grid) at **x 196.5, y 439.2 pt** on every level (screen centre + 13.2 pt down) | VERIFIED 30 levels (spread ±0.2 pt) |
| height | no height clamp seen: the tallest boards (36 rows × 15.13 = 545 pt, y 167–711; 32 rows × 17.87 = 572 pt, y 153–725) keep the width rule | VERIFIED L43, L44, L49; a board that would hit the HUD (> ~34 rows at 17.87) was never seen → INFERRED width-only |
| background | plain white #FFFFFF, no grid lines | VERIFIED shots |

### 2.2 The arrow (lossless start shots of 8 levels at pitches 14.04–28.09; `out/geom.txt`)
| item | value (× pitch unless pt) | per-level spread | source |
|---|---|---|---|
| stroke width | **0.221** (L32 4.00 pt, L59 3.00, L50 6.30); drawn in whole device pixels, so the rendered width is 0.221·pitch rounded to 1/3 pt | 0.210–0.226 | VERIFIED integrated darkness across 40–407 straight segments per level |
| colour | pure black #000000, anti-aliased edges | — | VERIFIED |
| path | polyline through the cell centres, head cell last | — | VERIFIED (JSON overlay coverage 0.99–1.00) |
| tail end | **round cap**; the stroke ends **0.14 pitch** beyond the tail cell centre (= half-width + 0.03 pitch); the width profile over the last 2.5 pt matches a semicircle | 0.132–0.151 | VERIFIED 2–16 free tails per level |
| corners | outer side rounded: the centre line is filleted with **R ≈ 0.125 pitch** (outer edge radius ≈ R + w/2 ≈ 0.235 pitch); inner corner ≈ sharp (R − w/2 ≈ 0) | R 0.121–0.144 | VERIFIED 31–237 corners per level (50 %-edge positions along the corner diagonal) |
| head | isosceles **triangle**, filled black; base edge at **−0.22 pitch** (behind the head cell centre), tip at **+0.39 pitch**, base width **0.61 pitch** (length base→tip 0.61 pitch); the stroke runs into the base; base corners very slightly rounded (width reaches its max ≈ 0.07 pitch in front of the base edge), tip sharp | base −0.210…−0.236, tip +0.369…+0.395, width 0.600–0.616 | VERIFIED 15–85 heads per level |
| hit area | a tap ≥ 15 pt off an isolated stroke still sends it; tapping the head triangle works; midpoint between two parallel free arrows sent the right-hand one (1 obs.) | — | VERIFIED player part 2 (shots 107–109, 146) |

### 2.3 Cell dots
| item | value | source |
|---|---|---|
| colour | **#C5E1FF** (197,225,255), flat | VERIFIED shots 136, 141, 043 (core pixels) |
| size | **⌀ 0.192 pitch** (5.39 pt at 28.07, 4.44 at 23.12, 2.70 at 14.04) | VERIFIED effective-area measure, 85 + 79 + 3 clean dots |
| where | a dot exists at **every cell an arrow occupies at level start**, drawn *under* the arrow: it is hidden by the stroke and only peeks out as a bluish fringe at rounded outer corners (shot 003: 73 bluish blobs within 1–1.5 pt of cell centres, all at corners). A cell no arrow ever occupied has **no** dot (L32 cell (1,8)). So "a dot appears when the tail leaves the cell" (pass 1) = the arrow uncovering it. | VERIFIED shot 003 + P02 (pass 1: the dot shows the frame the tail passes) |
| during the intro | before the arrows are drawn in, the dots of all arrow cells are visible (grey-blue grid of dots on the white board) | VERIFIED S1-L48-play-intro 0.383–0.9 |
| at the win | the dots light up in the radial rainbow wave (§6.6) | VERIFIED |
| obstacles | box cells become ordinary dotted cells once the box breaks (player part 2) | VERIFIED shots 137 |

## 3. The EXIT

### 3.1 Input model
| observation | result | source |
|---|---|---|
| press 5.0 s on a free arrow | arrow stays put the whole hold; leaves 0.23 s after lift-off | VERIFIED PHONE shots 009 (grab during hold), 010 |
| press 2.0 s (S1-P01-press2s) | first arrow change at t = 1.964; fitted release 1.942 | VERIFIED |
| tap ripple onset | same frame as the first arrow change (pass 1: P02-A 0.499, L33 0.532, L35 0.266; pass 2: bump-1 0.300, bump-2 0.283) → drawn on release | VERIFIED |
| tap ripple look | grey disc at the touch point: r 11 → 22.5 pt, luminance 180 → 250 (on white) in ≈ 0.25 s, then gone | VERIFIED PHONE (3 clips, `out/ripple_*.txt`) |
| where you can tap | any cell of the arrow (tail taps, head-triangle taps) + ≥ 15 pt tolerance (§2.2) | VERIFIED |
| swipe | never triggers an arrow; it pans the board and the pan persists | VERIFIED player part 2 (shot 111) |
| queued tap (S1-P02) | tap B released 0.77 s after A, its ray blocked only by A's still-moving tail → **accepted, no bump**: an arrow leaves the blocking grid when it is tapped | VERIFIED (1 case) |
| obstacle bookkeeping at the tap | the L50 box (counter 1) shattered on the **same frame** as the tapped arrow's first motion (0.433) → counters/boxes update at the tap, not when the arrow leaves | VERIFIED S1-L50-box-break |
| host `.marks` | runner latency 0.43–2.3 s from `action_start` to the visible tap → anchor on the ripple frame | VERIFIED |

### 3.2 Look while exiting
| item | value | source |
|---|---|---|
| colour ramp | black → #10A2EF, ≈ linear per channel over **0.09–0.10 s** from release (L50-box head (5,51,76) +0.023 s → (10,119,174) +0.04 → (14,150,218) +0.07 → (16,163,240) +0.09 s) | VERIFIED 60 Hz S1-L50-box-break, -win-seq-1 (+ pass-1 P01, L33) |
| final exit colour (blue) | **#10A2EF** solid along the body | VERIFIED runner shot L038-013934-r07 (17 samples) |
| body | slides along its own polyline (snake): head leads, every body point follows the same path, corners keep their rounding, length constant | VERIFIED 11 exits |
| head off screen | the head keeps going straight along its ray past the board edge; the arrow is drawn until its **tail** passes the **screen** edge; it passes **under** the HUD panel, coin pill and boosters (they are drawn on top) and **above** idle arrows / obstacles | VERIFIED shots L038-013934-r07, L048-025348-r17 |
| sparkle stars | small 5-point **stars** spawned behind the tail as it moves: ≈ 2.4 stars per cell of path, size ≈ 0.3 pitch (8 pt at 26.2), jitter ±0.25 cell sideways, random rotation, two shades of the exit hue (blue exit: deep blue ≈ #1E88F5 + light cyan ≈ #7FD8FF (video)); each lives ≈ 0.25–0.4 s: full size ≈ 0.1 s, then fades + shrinks | VERIFIED look + timing S1-L52-three-exits 0.68–1.25 (sheet `ov_S1-L52-three-exits_0.62-1.25_0.0_c0-235-130-70.jpg`); per-star life INFERRED (±0.05 s) |
| pipes | an arrow in a pipe is drawn inside the translucent tube (lighter) and keeps the same s(τ) | VERIFIED PHONE S1-L35-pipe-break (pass 1) |
| a second exit meanwhile | independent: a second tap starts its own exit while the first still moves; both follow their own s(τ) | VERIFIED P02, three-exits |

### 3.3 Kinematics (fit: `exitfit2.py` → `out/exitfit2.txt`; tracks `exittrack.py` → `out/exittrack_*.txt`)
Distances along the arrow's own path in **cells**: the motion scales with zoom (fit in pt fails, pass 1: RMS 45 pt).
Model `s(τ) = vmax·τ − (vmax − v0)·T·(1 − e^(−τ/T))`, per-exit release t0 bounded by the last-still / first-moved frames,
robust soft-L1 fit.

| exit (clip) | pitch pt | samples | d_max cells | RMS cells |
|---|---|---|---|---|
| P02-A, L32 at 0.786× zoom, 26-cell snake, up | 14.04 | 33 | 37.8 | 0.066 |
| P02-B, L32 0.786×, 2nd tap, right | 14.04 | 14 | 9.8 | 0.070 |
| P01, L32 0.786×, 4-cell, right | 14.04 | 11 | 4.0 | 0.021 |
| L33 key arrow, fit, up | 17.857 | 25 | 16.3 | 0.024 |
| L35 pipe arrow, fit, right → pipe → down | 28.092 | 20 | 17.9 | 0.158 |
| **L47 44-cell snake, head tap, right** (tail tracked) | 17.87 | 47 | 40.3 | 0.073 |
| **L52 2-cell, left** (1st of 3 taps) | 26.199 | 4 | 1.0 | 0.022 |
| **L52 5-cell, left** (2nd tap +0.58 s) | 26.199 | 7 | 2.1 | 0.020 |
| **L52 42-cell, down** (3rd tap, violet) | 26.199 | 18 | 8.7 | 0.013 |
| **L50 6-cell, right** (box breaks at the tap) | 28.07 | 12 | 4.9 | 0.053 |
| **L50 11-cell, right** (last arrow of the level) | 28.07 | 12 | 4.7 | 0.169 |

**Fit (11 exits, 203 samples): v0 = 7.67 c/s, vmax = 73.86 c/s, T = 0.353 s, RMS 0.082 cells.** Pass 1's 5-exit
parameters (5.54 / 71.4 / 0.323) predict the 6 new exits with RMS 0.02–0.17 cells → the law is stable; T(d) differs ≤ 7 ms.

| d (cells) | 0.5 | 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 | 15 | 20 | 25 | 30 | 40 | 50 | 60 | 80 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T (s) after release | 0.043 | 0.072 | 0.115 | 0.150 | 0.181 | 0.209 | 0.235 | 0.283 | 0.326 | 0.367 | 0.424 | 0.513 | 0.596 | 0.676 | 0.827 | 0.973* | 1.115* | 1.393* |

Velocity (c/s): 0 s 7.7 · 0.05 s 16.4 · 0.1 s 24.0 · 0.2 s 36.3 · 0.3 s 45.6 · 0.5 s 57.8 · 0.7 s 64.8 · 1.0 s 70.0 · 1.5 s 72.9.
(* beyond the measured 40 cells / 1.0 s.)

Linear stand-ins, least squares over all (distance, time-since-release) pairs of the 11 exits: `T = 0.080 + 0.0205·d`
(0–45 c, n = 203, RMS 34.5 ms); **`T = 0.114 + 0.0189·d` (2–45 c, n = 145, RMS 21.0 ms)**; `T = 0.146 + 0.0176·d` (5–45 c,
n = 96, RMS 12.0 ms); `T = 0.066 + 0.0266·d` (1–12 c, n = 114, RMS 9.6 ms). Use the exp model (time residual ≈ 3 ms).
Total exit duration = the time for the **tail** to pass the screen edge = s(τ) reaching (path length to the edge + arrow length).
Honest count: 203 (distance, time) pairs but **11 independent exits** (4 pitches); clips-needed #9 asks for more long exits.

### 3.4 Exit colour ladder — the "combo"
Rule (pass 1, INFERRED from 1630 video taps, best agreement 84 % at W = 1.20–1.25 s): a tap within **W ≈ 1.25 s** of the
previous tap continues a streak; streak index c: **1–2 blue #10A2EF, 3 violet, ≥ 4 rainbow** (`out/combofit.txt`).
v552 check (pass 2, S1-L52-three-exits, taps 0.58 s and 0.75 s apart): exit 1 blue, exit 2 blue, exit 3 **violet** → VERIFIED.

| look | value | source |
|---|---|---|
| blue | solid #10A2EF + blue stars | VERIFIED |
| violet (c = 3) | the body shows a **cyan ↔ blue ↔ violet/magenta gradient** (hue ≈ 190° ↔ 290°, video (57,114,255) (123,60,252) (185,8,254) (1,172,253)), period ≈ 3.5–4 cells along the path | VERIFIED look (video colours) S1-L52-three-exits 1.40–1.75 |
| rainbow (c ≥ 4) | full hue wheel along the body: #FF6500 · #FFCE01 · #9DE600 · #37E500 · #00E100 · #00D3AF · #00C1FF · #4079FF · #8D5FFF · #BC4BF3 · #FF2FC6 · #FF5A85 (S ≈ 1, V ≈ 1), rainbow stars | VERIFIED lossless runner shots L036-013329-r06, L042-015921-r02 (pass 1) |
| where the colours live (NEW) | the violet/rainbow colours form a **field fixed in space**, sampled by the moving body: at a fixed screen point on the path the hue drifts only ≈ 50–150°/s while the body slides past at ≈ 1000 pt/s. Implement as colour = palette(path-or-world coordinate / period + slow drift), not as a gradient attached to the body | VERIFIED 1 violet exit (`out/violetfield_L52.txt`); rainbow anchoring INFERRED (same mechanism) |
| unknowns | does a bump or an obstacle tap break the streak? does the ladder cap at rainbow? lossless violet colours | clips-needed #10 |

## 4. The BUMP (wrong tap) — v552 (`out/bumptrack_v552.txt`, `out/bumpfx_v552.txt`, `out/bumpfit_v552.txt`)
Two v552 clips, 60 Hz, pitch 17.87: **bump-1** S1-L47-bump-1 (3-cell ← arrow, gap to the blocker's stroke 64.0 pt =
3.58 cells, ripple 0.300, contact 0.439–0.449) and **bump-2** S1-L48-bump-2 (8-cell → arrow, gap 24.25 pt = 1.36 cells,
ripple 0.283, contact ≈ 0.390–0.400). τ = time since contact.

| beat | value | source |
|---|---|---|
| out | the whole arrow **slides along its own path** (snake: the tail follows the body) at **constant speed** from the release: bump-1 389 pt/s = 21.8 c/s (RMS 0.75 pt), bump-2 226 pt/s = 12.6 c/s (RMS 0.12 pt) → **T_out = 0.165 s / 0.107 s**; the head stops when its tip touches the blocker's stroke edge (travel = the gap, not a fixed nudge). Law across both + YT-B (0.41 c in 0.084 s): **T_out ≈ 0.075 + 0.025·gap_cells** | VERIFIED speeds/durations; law INFERRED (3 points, one from the older build) |
| hold | none (≤ 1 frame at contact) | VERIFIED |
| back | eases back to rest: easeOutQuad **0.144 s** (bump-1, RMS 0.87 pt; easeOutCubic 0.18 s fits equally) and ≈ 0.137 s (bump-2) → ≈ 0.14 s independent of the gap | VERIFIED bump-1, INFERRED bump-2 (tail end only) |
| tapped arrow colour | black → **#EE0912** (238,9,18) during the return: starts ≈ τ 0.017, S-shaped, done at τ ≈ 0.12 (R: 13, 30, 93, 140, 190, 221, 235, 237 per 1/60 s); **stays red** for the rest of the level (still tappable; leaves normally later) | colour VERIFIED lossless shot 110; timing VERIFIED both clips |
| blocker | the whole blocking arrow **flashes red** — the same red as the bumped arrow (video (237,8,17)): black → red over τ 0.02 → 0.12 (R 12, 48, 92, 142, 187, 222, 237 per 1/60 s), then straight back to black by **τ ≈ 0.33** (≈ linear 0.2 s fade, R 234 → 209 → 160 → 102 → 45 → 0); no hold | VERIFIED bump-1, sampled on the blocker line 15–35 pt away from the badge (`out/blockerflash_L47.txt`); bump-2 sheet agrees |
| ✖ badge | red ✖ (video ≈ (246,38,49)) with a dark-red outline and lighter bevel, ≈ 18 pt (≈ 1 pitch) across, centred on the contact point (the blocker's near edge on the ray): appears at τ 0.017 **large (~1.4×) and transparent**, shrinks to 1.0 and becomes opaque by τ ≈ 0.12; holds to τ ≈ 0.33; then shrinks (→ ~0.5) and fades out by τ ≈ 0.43 | VERIFIED bump-1 (sheet `ov_S1-L47-bump-1_0.43-0.92_0.0_c222-322-36-32.jpg`), bump-2 same |
| red vignette | all four screen edges tint red: overlay ≈ #FF0000 with alpha **0.42·e^(−d/27 pt)** (d = distance from the edge: 0.42 at 0, 0.37 at 5 pt, 0.31 at 10, 0.22 at 20, 0.16 at 30, 0.08 at 45); full on the contact frame, holds ≈ 0.035 s, fades ≈ linearly to 0 at **τ = 0.33 s** (alpha 0.40 at 0.05, 0.33 at 0.10, 0.21 at 0.167, 0.09 at 0.233, 0 at 0.333) | VERIFIED both clips, identical |
| heart | the **rightmost red heart breaks**: τ 0 a jagged crack line appears; τ 0–0.12 the heart rises 7 pt (v0 ≈ −115 pt/s) while the two halves separate and tilt outward (±20–30°); from τ 0.12 the halves fall with **g ≈ 960 pt/s²**, spreading to ±15 pt; they fade out between τ 0.30 and 0.40. Under it the **empty heart slot** (#6C94DC, the pill's recess colour) is revealed from τ ≈ 0.05 | VERIFIED both clips (identical timeline); colour VERIFIED lossless shot 110 |
| shake | none (HUD and board static) | VERIFIED |
| sound | **none** (both clips' audio is digital zero while the recorder does capture app audio) | VERIFIED (sounds.md) |
| haptic | not recordable; Haptic is ON on the phone | — (clips-needed #4, by feel) |
| win panel | still says "Perfect!" with a heart lost | VERIFIED player part 2 |

YT-B (older blue skin, 2 bumps) differs: the bumped arrow turns black not red, no ✖ badge and the heart cross-fades instead
of breaking; its vignette (0.33 s) and forward law agree. Build the v552 row.

## 5. Obstacles

### 5.1 Tape (linked arrows)
| item | value | source |
|---|---|---|
| one tap on any member | all members leave together with the same kinematics; the pink tape travels **with** the bundle and leaves the screen with it | VERIFIED PHONE shots 018/019 (L32) + YT-A 81.08–81.48 (25 fps) |
| member start sync, blocked member | no v552 clip (the S1 tape rec failed) | clips-needed #5 |

### 5.2 Key → door (PHONE S1-L33-key-first, tap release ≈ 0.52; `out/keytrack_L33.txt`, `out/door_burst_L33.txt`)
| beat | t | value | source |
|---|---|---|---|
| key arrow tapped | 0.532 | the arrow turns blue and slides out through the key; the purple ring vanishes at once; the key stays where it hung | VERIFIED |
| detach + sag | 0.749 → 0.832 | key drops 8.6 pt, wobbles ±15° | VERIFIED |
| float up | 0.832 → 1.048 | rises 41 pt in 0.22 s (ease-in-out), apex ≈ 1.07 | VERIFIED |
| dive to the lock | 1.074 → 1.298 | falls 160 pt into the target door's keyhole, strong ease-in (parabola g ≈ 7650 pt/s², RMS 2 pt) | VERIFIED (1 key; far-door path: clips-needed #14) |
| insert | 1.298 → 1.448 | key shrinks and rotates to point into the keyhole (≈ 0.15 s) | VERIFIED |
| turn | 1.531 → 1.631 | key turns ≈ 45–90° in the lock (0.1 s) | VERIFIED |
| burst | 1.664 | white flash on the lock (peaks 1.681, gone 1.88) + the door breaks into pieces | VERIFIED |
| debris | 1.664 → 2.55 | ≈ 60 pieces: purple (inner frame + lock), orange (outer frame), blue (slats); small upward pop (≈ 14 pt), then fall with g ≈ 1000 pt/s² off the screen bottom (life ≈ 0.9 s), fading near the end | VERIFIED counts/timing; g INFERRED |
| door order | the next locked door is the leftmost/lowest (L33 staircase opened left → right) | VERIFIED PHONE bot rounds |
| totals | tap → burst **1.14 s**; tap → debris gone ≈ 2.0 s; arrows under the door visible as soon as it breaks | VERIFIED |

### 5.3 Pipe (PHONE S1-L35-pipe-first / pipe-break; `out/pipe_break_L35.txt`)
| beat | t (pipe-break clip) | value | source |
|---|---|---|---|
| tap | 0.266 (ripple) | arrow → blue, slides into the mouth | VERIFIED |
| inside | 0.499 → 0.732 | drawn inside the tube (lighter blue through the translucent tube); same s(τ) | VERIFIED |
| out of the far mouth | 0.732 | continues off-screen in the tube's exit direction | VERIFIED |
| counter | per passage | −1; the number-change animation not yet seen at 60 fps | clips-needed #17 |
| break (last use) | 0.782 (≈ 0.05 s after the head leaves the far mouth, tail still inside) | tube shatters into cyan shards, the orange counter box splits in 2 tumbling halves, both gold rims drop and tumble | VERIFIED |
| debris | 0.782 → ≈ 2.2 | 22–55 blobs (cyan + orange), fall with g ≈ 1000 pt/s², fade | VERIFIED timing; g INFERRED |

### 5.4 Box (v552 from L50; PHONE S1-L50-box-break, `out/boxbreak_L50.txt`) — NEW
| beat | t | value | source |
|---|---|---|---|
| counter | any arrow cleared anywhere | −1 per clearing tap, all boxes together (player: 10/10) | VERIFIED player part 2 |
| break | **0.433** = the tapped arrow's first-motion frame (release ≈ 0.41) | on the tap that takes the counter to 0 the box is replaced in one frame by ≈ 140 small purple shards laid out over the box area, plus the silver counter ring broken into a few chunks; no flash, no pre-shake | VERIFIED |
| shards | 0.433 → 1.10 | spread sideways ≈ 180 pt/s at first (bbox x 53–340 → 0–393 by 0.77), fall from rest with **g ≈ 1250–1300 pt/s²** (centroid +2.5 pt at +0.067 s, +18 at +0.167, +44 at +0.267, +67 at +0.333), fade/leave from 0.78; gone by **1.10** (life ≈ 0.67 s) | VERIFIED |
| after | the box cells are ordinary empty cells (dots only where arrows had been; none on L50/L51) | VERIFIED shots 137, 141 |
| sound | none | VERIFIED (audio zero) |

### 5.5 Elevator / Corner (older builds only)
YT-B shows Elevator (1235.06: the emptied platform darkens, panels merge, a new arrow layer fades in over ≈ 0.25 s). Not in
v552 so far (L32–L62). Measure on the PHONE if met.

## 6. HUD, level flow, popups

### 6.1 Level intro — v552, from the Play tap (S1-L48-play-intro 60 Hz; `out/introfit_L48.txt`, `out/introdraw2_L48.txt`, `out/hudfit_L48.txt`)
t = clip time; **cut = 0.375** (last home frame 0.366, first level frame 0.383).

| beat | t | value | source |
|---|---|---|---|
| Play touch-down | 0.266 | the Play button scales to **0.95** in one frame (197.5 × 69.5 → 187.5 × 66 pt), stays pressed | VERIFIED |
| release + click | 0.319 (audio) | the UI click (sounds.md cue 1) on release | VERIFIED |
| hard cut | 0.375 | home → level with no transition, **+0.06 s after the click** (L49: click 0.350 → cut 0.425, +0.08 s) | VERIFIED 2 clips |
| board zoom-out | 0.375 → 1.725 | the board starts at **1.49×** its fit scale about the board centre and zooms to 1.0 with **easeOutCubic over 1.35 s** (fit RMS 0.29 pt on the pipes' top edge over 56 frames; s = 1.33 at 0.55, 1.19 at 0.75, 1.11 at 0.90, 1.05 at 1.07, 1.01 at 1.36) | VERIFIED (exponential RMS 2.0 pt and critically-damped spring 1.1 pt fit worse) |
| arrow draw-in | from the cut | every arrow draws itself **tail → head** at the same time; each arrow's duration ≈ **0.32 s + 21.6 ms/cell** (98 % drawn; 3-cell ≈ 0.39 s, 10-cell ≈ 0.54 s, 38-cell ≈ 1.14 s; 50 % at ≈ 0.13 s + 10.8 ms/cell); the head triangle appears when the stroke reaches it; the cell dots show under not-yet-drawn parts | VERIFIED 24 arrows fully on screen; the linear law INFERRED (±0.05 s) |
| pipes / obstacles | drawn complete from the first level frame (they only zoom) | VERIFIED |
| HUD drop | 1.398 (cut + 1.023) → 1.681 | top HUD slides down from ≈ 118 pt above: **easeOutBack 0.334 s, overshoot s = 3.4** (pause-button top −50 → 106 at 1.564 → 68.5 at 1.681, then dead still: no undershoot, which rules out a spring) | VERIFIED 60 Hz (RMS 2.2 pt); pass-1's spring (0.43 s, ζ 0.47) fits the L32 clip too but predicts an undershoot the L48 data does not show |
| boosters | 1.481 → 1.681 | both slide in from the screen sides: **easeOutBack 0.209 s, s = 2.6** (left booster right edge −22 → 85.5 at 1.564 → 67.0) | VERIFIED (RMS 1.2 pt) |
| big timer | 1.714 → ≈ 1.90 | the big "2:30" pops in large over the pill (HUD start + 0.32 s) and shrinks into the slot by 1.85 (≈ 0.13 s) with a slight undershoot, settled ≈ 1.90 (pass-1 L32 at 25–60 Hz: ≈ 3.5× first frame, 0.8× undershoot, ≈ 0.25 s) | VERIFIED L48 white-pixel trace (pass 2) + L32 `out/bigtimer_L32.txt` (pass 1) |
| hearts | 1.781 / 1.880 / 1.997 (timer pop + 0.07) | each pops in at **1.58×** (42 vs 26.5 pt), shrinks to 0.89× at +0.10–0.13 s, settles 1.0× at +0.20 s; stagger 0.10–0.12 s | VERIFIED 60 Hz (`out/hud_intro_L48.txt`) |
| intro done | ≈ 2.20 (cut + 1.83 s) | — | VERIFIED |
| timer | starts at the **first tap**, not at the intro; a pinch does not start it | VERIFIED PHONE (levels.md, player part 2) |

### 6.2 Timer
- m:ss in the pill, ticks once per second; pause freezes it (VERIFIED). Behaviour near 0 (colour, pulse, sound): NOT observed
  → clips-needed #3.
- "Out of Time!" popup (+30 sec / Add Time 900): fully **static and silent** for 9.5 s (no idle animation, frames identical)
  — VERIFIED S1-L52-short-exit-win (which holds only this popup, not a win). Its entrance was not recorded.

### 6.3 Popups, buttons, transitions
| item | entrance | exit | source |
|---|---|---|---|
| button press | **scale 0.95 on touch-down, instant** (no animation), held until release; the action fires on release (Play 0.95 × 0.95; Continue 284.5 → 270 wide, 0.949) | release: the next screen replaces it | VERIFIED S1-L48-play-intro 0.266, S1-L50-win-seq-2-continue 0.067 |
| Win panel | **instant**: one black frame (4.693, the celebration layer cleared) then the full panel (4.727); no scale spring | Continue → hard cut to home ≈ 0.10 s after touch-down (0.067 press → 0.17–0.18 cut; the release is not visible) | VERIFIED v552 60 Hz |
| win-panel Streak strip | slides up from the bottom 4.743 → 4.876 (0.13 s) with the previous multiplier lit (x25); ≈ 0.25 s later the green chip slides x25 → x100 (5.13 → 5.44, 0.31 s, ease-in-out) and gets an orange ring | — | VERIFIED S1-L50-win-seq-1 |
| Paused / Quit Level? | full size on the first frame, background dims ≈ instantly | instant | VERIFIED YT-B 60 fps (pass 1) |
| Feature unlock ("Pipe!", "Box!") | dark overlay instantly; staggered pops with overshoot: icon +0.24 s, title +0.52, "Unlocked!" +0.60, card +0.76; sparkles loop | tap: overlay fades 0.25 s | VERIFIED YT-A (pass 1) |
| Weekly Contest tutorial (v552) | dim to ≈ 10 % brightness in **one frame** (mean luminance 133 → 14), then staggered pops (times after the dim frame): title +0.18 s (grows ≈ 0.1 s), maze icon +0.35, "Beat Levels!" +0.58, pointer +0.72, podium +0.88 (grows ≈ 0.25 s) | — | VERIFIED S1-weekly-contest-open (30–60 Hz) |
| fail flow (Continue? ×2, Level Failed) | not recorded (shots only); expected instant | — | clips-needed #2 |

### 6.4 FTUE tutorial hand (YT-A L1-4 stage 1, 25 fps — pass 1)
| beat | t | value |
|---|---|---|
| loading → board | 0.40 → 0.56 | cross-fade (0.16 s) from the loading art to the board (3 parallel vertical arrows, the middle ↑ is the free one) |
| caption "Tap to move!" | 0.80 → 0.88 | pops in above the arrows (small → full ≈ 0.08 s) |
| hand appears | 0.80 → 1.04 | yellow pointing hand, fingertip pinned on the free arrow, scales about the fingertip 0.25× → 1.0× (≈ 0.24 s, ease-out) |
| press loop | hold 1.04–1.36 → shrink to 0.54× 1.36–1.84 (0.48 s) → back to 1.0× 1.84–2.24 (0.40 s) → hold ≥ 1.24 s | period ≥ 2.4 s (one cycle seen) |
| on the player's tap | 3.52 → 3.60 | hand and caption vanish in ≈ 0.08 s; the arrow exits |
Source: VERIFIED YT-A (`out/hand_YTA.txt`). v552's FTUE expected to match — INFERRED.

### 6.5 Home
| item | value | source |
|---|---|---|
| Play button | static: no pulse/bounce | VERIFIED F01 (7.3 s) |
| characters | the two workers animate continuously (sway/gesture), the scientist slowly (≈ 3 s cycle, weak), the capsule arrows churn | INFERRED F01, META-home-tap-scientist (no reaction to a tap on the scientist) |
| **home return after a win (NEW, v552)** — t = S1-L50-win-seq-2-continue movie time | 0.067 Continue press → **0.17–0.18 hard cut** to home → 0.20–0.35 the home **dims** (≈ 50 %) and a purple hex **Claw token "+1"** pops at the capsule machine (small → full ≈ 0.1 s) → 0.40 flash on the token; the orange **x25 multiplier badge** appears at its right and merges into it 0.40 → 0.85 (white burst 0.85) → 1.05 "+25" → 1.5–1.7 the dim lifts and the token flies up to the Claw bar's left icon (1.6 → 1.9, arc) → 1.997 flash at the icon; the bar **counts up 156 → 181** in 4 visible steps to 2.28 → 2.28–2.5 the **Streak Race chip strip** (x1 x5 x10 x25 x100) slides out under the Claw bar with x25 lit, a green "+25" flag flies to the Streak badge (2.3 → 3.0) → ≈ 3.0–3.08 the lit chip moves to **x100**, 3.48 flash on the left x100 badge → 3.6–4.0 the strip retracts → **coins** fly up from the machine to the coin pill (first at 4.08, arrivals 4.29 … 4.69) and the counter steps **+4 per coin**, 5 coins, ≈ 0.1 s apart (3854 → 3858 → 3862 → 3866 → 3870 → 3874) | VERIFIED 60 Hz sheets `ov_S1-L50-win-seq-2-continue_*` + audio (sounds.md §2) |
| pass-1 YT-A coin fly | ≈ 1.0 s after the home cut a few coins fly to the pill (≈ 0.35 s each), a star sparkle pops on the pill, the counter counts up +20 over ≈ 0.45 s | VERIFIED YT-A 25 fps (no Claw/Streak events in that build) |

### 6.6 Win sequence — v552 (S1-L50-win-seq-1, unskipped, 60/30 Hz; `out/winscan_v552.txt`)
t = clip time. The last arrow (11 cells) was released at 0.450; **wave start W = 0.79**.

| beat | t | t − W | value |
|---|---|---|---|
| last release | 0.450 | −0.34 | the last arrow exits normally (its tail leaves the screen at ≈ 0.88) |
| **win trigger** | ≈ 0.79 | 0 | ≈ the frame the last arrow's **tail leaves its last cell** (T(10.5 cells) = 0.336 s after release → 0.786) — INFERRED (1 level); the exit keeps animating |
| rainbow dot wave | 0.79 → 1.30 | 0 → +0.51 | the cell dots flash colour in a ring expanding from the board centre (centre dots warm/yellow at 0.85, the outer ring violet at 1.2), then settle back to #C5E1FF |
| blue sign | 1.198 → ≈ 1.43 | +0.41 → +0.64 | a blank blue banner enters at the bottom-left corner and swoops up (arc) to the top centre, tilted, and settles |
| "MAZE" letters | 1.38 → 1.52 | +0.59 | yellow letters pop onto the sign one after another |
| purple arrow sign | 1.43 → 1.66 | +0.64 | rises from the bottom-left and settles under MAZE |
| "OUT!" | 1.73 → 2.43 | +0.94 | appears small/pale in the purple sign (1.73), **grows huge** (> screen width by 1.86), holds, then shrinks back into the purple sign 2.26 → 2.43 |
| dim | 2.03 → 2.37 | +1.24 → +1.58 | background luminance 255 → ≈ 40 **linearly over 0.33 s** (black at ≈ 0.85) |
| confetti | from 2.26 | +1.47 | coloured confetti bursts up from the bottom, then rains; count peaks ≈ 3.1 |
| fireworks | from 2.43 | +1.64 | white rocket trails rise; bursts flash the background (luminance bumps 2.48, 2.53, 2.70, 2.95, 4.23) |
| logo settle | ≈ 2.43 | +1.64 | whole logo ends a bit smaller at the top centre |
| layer cleared | 4.693 | +3.90 | one frame with only confetti / black |
| **win panel** | **4.727** | **+3.94** | instant (§6.3); dim complete → panel = **2.36 s** |
| streak strip | 4.743 → 5.44 | — | §6.3 |
| sound | — | — | **none** (the whole clip is digital zero) |
Agreement with YT-A (pass 1: panel at sign-crossing + 3.36 s, 2.32–2.36 s after the dim completes): v552 sign crossing ≈ 1.30
→ panel +3.43 s; dim complete → panel 2.36 s → **same timing**. Skip: any tap during the celebration shows the panel at once
(YT-A, 13 of 17 wins skipped; VERIFIED there, not re-tested on v552).
Brand note: the sign reads "MAZE OUT!" — our build keeps the motion with our own "ARROW OUT!" logo.

### 6.7 Zoom and pan
| item | value | source |
|---|---|---|
| max zoom | pitch **28.07 pt absolute** (L32 pinch 2.0 → 28.07/28.09; L062 pinch ×4 → 28.04; L50 opens there) | VERIFIED shots 005, meta-060/061, 135 (`pitchest.py`) |
| min zoom | pitch **14.04 pt absolute**: L32/L47 (fit 17.87) pinch-out → 14.04/14.0; L062 (fit 14.0) pinch 0.2 → stays 14.0 | VERIFIED shots 006, meta-062/063, player part 2 |
| double-tap | does not reset zoom; each new level and each Try Again opens at fit | VERIFIED |
| pan | a swipe pans; the pan persists | VERIFIED player part 2 |
| deceleration, pan limits, snap-back | not measured | clips-needed #13 |
| bulb hint camera | see §7 | VERIFIED |

## 7. Boosters (NEW)
### 7.1 Bulb (hint) — META-L062-bulb-hint (`out/bulbhint_L62.txt`), board at max zoom
| beat | t | value | source |
|---|---|---|---|
| camera | 0.0 → ≈ 0.80 | the board **pans** (no zoom change) to bring the hinted arrow into view: ink centroid x 198 → 289 pt, fast then slowing (≈ 6 pt/frame at 0.1–0.4 s, ≈ 1 pt/frame at 0.6–0.8 s) — an ease-out pan ≈ 0.8 s | VERIFIED (clip starts mid-pan; tap time unknown) |
| hint | 0.98 → | the hinted arrow turns **green #00DA00** (lossless shot meta-064): fade-in 0.98 → 1.18 (0.2 s), hold 0.13 s, fade back to black 1.31 → 1.48 (0.17 s), black 0.38 s, fade-in 1.86 → 2.05, then **stays green** (to ≥ 3.96 s) → two blinks (period ≈ 0.88 s) then steady | VERIFIED |
| sound | none | VERIFIED (audio zero) |
### 7.2 Left booster = HOURGLASS (time freeze) — META-L062-hourglass-freeze (2.06 s, `out/hourglass_L62.txt`)
| beat | t | value | source |
|---|---|---|---|
| rule | — | the timer freezes at once for **10 s** (+ ≈ 1.5 s of flight), then resumes; boosters do not start the timer | VERIFIED meta ledger 05:09 (clock readings) |
| hourglass appears | ≤ 0.0 | a large icy hourglass (≈ 90 × 100 pt) at the lower centre of the board (≈ (190, 617) pt) — the tap itself is before the clip | VERIFIED (position), tap time unknown |
| float up | 0.017 → 0.85 | rises ≈ 220 pt, decelerating (y 607 → 486 at 0.10 → 431 at 0.33 → 406 at 0.80), rocking slightly | VERIFIED |
| fly to the stopwatch | 0.90 → ≈ 1.30 | accelerates up-left along an arc to the timer pill's stopwatch (y 393 at 0.90 → 242 at 1.215), shrinking | VERIFIED (tracked to 1.215; landing from the sheet) |
| icing | ≈ 1.33 → 1.56 | the stopwatch icon turns icy | VERIFIED sheet |
| frost vignette | 1.58 → ≈ 1.75 | a frosty white-cyan border on all screen edges fades in (edge luminance 255 → 190 in ≈ 0.15 s) and stays for the freeze; a small "10" countdown + blue bar appear under the timer pill (meta-065 shows "6") | VERIFIED clip + shot meta-065 |
| sound | — | none in the recorded 2.06 s | VERIFIED (audio zero) |
| end of freeze (frost fade-out, bar), tap → spawn | not recorded | clips-needed #20 |

## 8. Not yet measured (all on clips-needed.md)
Timer near 0 + Out of Time entrance · fail flows (hearts out, Continue? ×2) · tape bundle timing · pipe counter change ·
key to a far door · combo edge cases + lossless violet · more long exits · zoom/pan deceleration · home idle loops (long) ·
music (the phone's Music toggle is OFF) · hourglass tap → spawn and freeze end · haptics (by feel) · skip-tap on the v552 win.

## 9. Owner-video level timeline (for the content / level team; start = hearts filled, end = win) — pass 1
Starts from `out/hearts_scan_{A,B}.txt`, ends from `out/winscan_A.txt` and the YT-B win-jingle onsets.

| YT-A level | start → end (s) | | YT-B level | start → end (s) | | YT-B level | start → end (s) |
|---|---|---|---|---|---|---|---|
| L1-4 (FTUE, 4 stages) | 0.5 → 25.3 | | L11 (Box unlock 76.0) | 79.3 → 102.1 | | L25 Hard | 711.5 → 792.6 |
| L5 | 29.0 → 42.8 | | L12 | 110.8 → 132.8 | | L26 | 800.5 → 831.3 |
| L6 (heart shape) | 45.5 → 71.0 | | L13 | 142.0 → 184.8 | | L27 | 839.0 → 894.3 |
| L7 (Linked Arrows unlock 76.4) | 80.3 → 92.5 | | L14 | 194.5 → 211.1 | | L28 | 902.0 → 971.4 |
| L8 | 97.8 → 111.2 | | L15 | 220.0 → 273.7 | | L29 Super Hard | 979.0 → 1143.4 |
| L9 | 119.0 → 137.5 | | L16 | 283.5 → 301.1 | | L30 | 1152.3 → 1172.9 |
| L10 | 142.8 → 178.2 | | L17 | 316.3 → 380.9 | | L31 (Elevator unlock 1182) | 1183.3 → 1207.8 |
| L11 (Curtain unlock 183.3) | 186.0 → 198.5 | | L18 | 389.5 → 409.3 | | L32 (2 bumps) | 1215.8 → 1251.3 |
| L12 | 202.5 → 220.1 | | L19 Hard | 416.8 → 489.6 | | L33 | 1259.3 → 1318.9 |
| L13 | 226.0 → 251.8 | | L20 | 499.3 → 518.2 | | L34 | 1327.3 → 1364.2 |
| L14 | 261.5 → 273.8 | | L21 (Pipe unlock 526) | 529.0 → 547.3 | | L35 Hard | 1375.0 → 1496.8 |
| L15 | 279.0 → 315.5 | | L22 | 554.8 → 588.3 | | L36 | 1504.5 → 1539.4 |
| L16 | 319.3 → 334.8 | | L23 | 596.3 → 642.5 | | L37 | 1547.0 → 1620.0 |
| L17 | 339.8 → 382.7 | | L24 | 652.3 → 703.9 | | L38 | 1627.5 → 1671.2 |
| L18 | 390.0 → 405.9 | | | | | | |
| L19 Hard (red HUD) | 412.3 → 465.1 | | | | | | |
| L20 | 474.5 → 492.3 | | | | | | |

## 10. Pass log
- 2026-09-25 03:50 — pass 1 (desk, no phone): PHONE clips S1-*, F00/F01 + runner shots through L054; owner videos YT-A/YT-B.
  New then: combo colour ladder, bump (YT-B), popups instant, win beat table (YT-A), board build-in (YT-B), tutorial hand,
  key/door/pipe beats, layering under the HUD.
- 2026-09-25 05:20 — pass 2 (desk, no phone): the 12 part-2 clips (S1-L47…L52, home-idle, weekly-contest, META bulb) + lossless
  start shots of 30 levels. New: board geometry (§2: fit rule, stroke, caps, corners, head, dots), v552 bump (§4), 11-exit
  kinematics (§3.3), violet exit + colour-field anchoring (§3.4), sparkle stars (§3.2), box break (§5.4), v552 intro chain with
  zoom law and draw-in (§6.1), button press scale (§6.3), v552 win (§6.6), home-return sequence (§6.5), absolute zoom limits
  (§6.7), bulb hint and hourglass freeze (§7). **Corrections to pass 1:** (1) dots are ⌀ 0.192 pitch, not 0.1, and exist under every arrow cell from
  the start (not "no dots before a cell is vacated"); (2) the v552 bump is red + ✖ + a breaking heart, not YT-B's black arrow and
  cross-fading heart, and its forward motion is constant-speed along the path, not accelerating; (3) the HUD drop is better
  described as easeOutBack (no undershoot) than as a spring; (4) a button press shows a 0.95 scale on touch-down (pass 1 saw
  none in the videos); (5) the Box obstacle IS in v552 (L50+); (6) the level intro on v552 is a zoom-out + draw-in, pass 1 had
  only YT-B's draw-in; (7) the phone recorder does capture app audio (pass 1 read its silence as a capture failure).
  Violet anchoring probe (hue at fixed screen points on the column x = 351 pt, L52 exit c): e.g. y = 330: 192° → 243° over
  1.415 → 1.747 s; y = 402: 290° → 230°; the body moved ≈ 300 pt in that time.
