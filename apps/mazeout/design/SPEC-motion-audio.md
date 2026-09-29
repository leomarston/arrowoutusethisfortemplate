# Arrow Out: motion, particles, audio and haptics (V1)

Motion-audio writer, 2026-09-25 (+03). The content spec that owns **every timing, curve, particle, sound, music and haptic value**
of **Arrow Out**, our 1:1 copy of "Maze Out! - Tap Puzzle" (Grand Games, v552 on the owner's iPhone 15). It closes every
`PENDING-motion-audio` item of `design/SPEC-architecture.md` §14 (index in §14 below) and names every value by the Tuning key the
build reads, so the build agents apply this spec as DATA (`Tuning/*.json`) plus the few code changes listed in §15.

The owner's sentence (verbatim, PLAN.md): *"Read GAMEPROMPT.md and make Maze Out on my phone. ultracode ultrathink"*.
The owner on feel (03:00, verbatim): *"I want to feel the flawless gaming experience that we have in this maze out game, like no
computer lag it has, and very well optimized … acutally flawless perfectly, and that click feeling, that this game makes, make sure
you do it very good as well."*

**Precedence.** SPEC.md §3 applies: the app-factory rules are suspended for this job; EN + TR only; iPhone only; offline game; every
asset is ours (our code, our SVG/3D art, our synthesised audio). **Nothing in `App/Resources` may derive from `research/sound-refs/`,
`research/video*`, `research/shots` or `research/store` pixels or samples** — recordings were only LOOKED at and LISTENED to.
Which document wins (SPEC.md §4): for timings, curves, particles, sounds, music and haptics **this file wins**; SPEC-architecture wins
for code structure and engine behaviour; the phone (v552) wins over the owner's videos, which win over web footage.

---

## 0 Read this first

### 0.1 Tags and sources
- **VERIFIED** (source): measured on the named phone clip / lossless shot (v552), or on the owner's video where v552 has no evidence.
- **INFERRED**: reasoned from fewer or indirect observations; the reasoning is given.
- **DECISION**: our choice (unobservable, e.g. haptics; or an engineering matter); the reason is given.

Source shorthands (as in SPEC-architecture §0.2): `motion` `sounds` `boosters` `fail` `meta` `tutorials` `vflows` `flows` `obstacles`
`levels` = `research/<name>.md`; `out/<f>` = `research/motion-tools/out/<f>` (raw measurements); `uim` = `design/ui-measure.md`;
`arch` = `design/SPEC-architecture.md`; `social` = `design/SPEC-social.md`; `shot NNN` = `research/shots/NNN-*.png`;
`bot Lnnn-…` = `research/bot/tmp/Lnnn-….png` (lossless runner shots); phone clips `research/video/S1-*.mov`, `META-*.mov`, `F00/F01`;
`V1`/`V2` = the owner's videos (= `YT-A`/`YT-B` in motion.md); `vlev-B/C/D` = `research/video-levels-{B,C,D}.md` (frame-by-frame obstacle timings). New measurements made for this spec (pass 3, 2026-09-25 ~08:30, no
phone) are marked **[P3]** with the method.

### 0.2 Units, anchors, notation
- Screen **pt** on the 393 × 852 reference (iPhone 15). Board lengths in **cells** (`p` = pitch in pt). Times in **seconds**.
- **Time anchors** (every table says which one its `start` column uses):
  | anchor | the frame on which … |
  |---|---|
  | `R` | the finger lifts on an arrow (touch-up timestamp; the release handler runs; = the first motion frame, arch §8.2) |
  | `C` | a bumping arrow's head touches its blocker (`BoardBeat.bumpContact`) |
  | `W` | the last arrow of a stage/level: its **tail leaves its last grid cell** (`BoardBeat.lastExitLeftBoard`; board.json `exit.leftBoardAt = "lastCell"`) |
  | `K` | the level screen replaces home on Play (the hard cut) |
  | `H` | home replaces the win panel on Continue (the hard cut) |
  | `S` | a popup/overlay is shown (its first frame) |
  | `B` | a booster button is released |
  | `L` | the Loading screen's first frame |
- **Curves.** `lin` = linear. `cb(x1,y1,x2,y2)` = a cubic-Bézier timing function (`CAMediaTimingFunction(controlPoints:)` and SwiftUI
  `.timingCurve(…)`; y values outside 0…1 are allowed and used for overshoots). Exact identities used below (a cubic polynomial with
  `f(0)=0, f(1)=1` is exactly `cb(1/3, f'(0)/3, 2/3, 1 − f'(1)/3)`):
  | name | formula (u = normalised time) | exact cb |
  |---|---|---|
  | `easeOutQuad` | 1 − (1−u)² | `cb(0.333, 0.667, 0.667, 1)` |
  | `easeInQuad` | u² | `cb(0.333, 0, 0.667, 0.333)` |
  | `easeOutCubic` | 1 − (1−u)³ | `cb(0.333, 1, 0.667, 1)` |
  | `easeInCubic` | u³ | `cb(0.333, 0, 0.667, 0)` |
  | `easeOutBack(s)` | 1 + (s+1)(u−1)³ + s(u−1)² | `cb(0.333, (s+3)/3, 0.667, 1)`: s 3.42 → `cb(0.333, 2.14, 0.667, 1)`; s 2.57 → `cb(0.333, 1.857, 0.667, 1)`; s 1.70158 → `cb(0.333, 1.567, 0.667, 1)` |
  | `easeInOut` | smooth S (≈ cubic in-out) | `cb(0.42, 0, 0.58, 1)` (≈) |
  | `easeInOutSine` | −(cos πu − 1)/2 | `cb(0.37, 0, 0.63, 1)` (≈) |
  | `ease` (CSS/UIKit default) | fast start, long settle | `cb(0.25, 0.1, 0.25, 1)` |
  | `kf[...]` | keyframes `t:value`, linear between them unless marked | `CAKeyframeAnimation(calculationMode: .linear)` |
  `spring(response, damping)` = SwiftUI `.spring(response:dampingFraction:)`; only used where a spring was the better fit.
- **Layer names** are arch §5.1 (`dotsRoot`, `restRoot`, `obstacleRoot`, `tapeRoot`, `moverRoot`, `tubeRoot`, `fxRoot`,
  `ScreenFXView`) and §6.5 (HUD, TutorialLayer, FXOverlay, PopupHost).
- **Cue column**: `♪ id` = a sound (`SoundID`, §11), `◉ id` = a haptic (`Haptic`, §12), `—` = silent and no haptic (VERIFIED silent
  unless marked).

### 0.3 What changed against SPEC-architecture §4.16 / §5 / §6 / §7 (this spec wins; §15 lists who applies what)
| topic | arch said (pass-1 research) | this spec (pass-2 phone data + P3) |
|---|---|---|
| exit kinematics | s = 71.4τ − 21.29(1 − e^(−τ/0.323)) | **s = 73.86τ − 23.37(1 − e^(−τ/0.353))** (v0 7.67, vmax 73.86, T 0.353; 11 exits, 4 pitches) |
| colour ramp | 0.08 s | **0.09 s** linear |
| dots | revealed as the tail leaves each cell | **drawn at stage load under every arrow cell** (visible fringe at outer corners; the arrow uncovers them) |
| violet painter | solid ≈ #9A50F5 | **a gradient field** #01ACFD ↔ #3972FF ↔ #7B3CFC ↔ #B908FE, period 3.75 cells |
| rainbow period | 5.6 (spike) vs 3.8 (store) | **4.2 cells** ([P3] 3.66 and 4.74 cells on two lossless phone shots) |
| bump | YT-B accelerating 0.09 s / hold 0.10 / back 0.10 | **constant speed, T_out = 0.075 + 0.025·c, no hold, back easeOutQuad 0.14 s** (v552) |
| hearts on a bump | dim cross-fade | **the heart breaks in two halves** (v552) |
| level intro | draw-in only (YT-B) | **zoom 1.49 → 1.0 easeOutCubic 1.35 s + draw-in 0.32 s + 21.6 ms/cell** (v552) |
| HUD drop | spring 0.429 / 0.47 | **easeOutBack s 3.42, 0.334 s** (no undershoot, v552 60 Hz) |
| clear wave | 0.45 s | **0.50 s** |
| win panel | sign crossing + 3.36 s | **W + 3.94 s** (same beat, re-anchored on W) |
| cue list | uiClick, coinCollect, unlockChime | + the v552 home-return cues (§11.2); music **none** |
| haptic map | light tap … | §12 |

---

## 1 Decisions at a glance

| # | Decision | Tag / why |
|---|---|---|
| MA1 | Every in-level event is **silent** (tap, exit, stars, combo, bump, heart, obstacles, intro, timer, time-out, boosters, win celebration). Sound exists only for UI buttons (on release), the unlock overlay, and the home-return event/coin sequence. | VERIFIED sounds §1 (+ meta explorer: all 11 META tracks digital zero while the recorder captures app audio) |
| MA2 | **No music.** v552's Settings "Music" button is inert and stays OFF (4 attempts, meta §4); no loop was ever heard on any device. Our Music button copies that (shows OFF, press scale + click, no state change). The music bus exists and stays empty. | VERIFIED meta §4; DECISION to copy the inert button rather than fake a toggle for music that does not exist |
| MA3 | **No tap sound** by default (1:1). The owner's "click feeling" is delivered by: fire on release, ripple + first motion on the next vsync, and a crisp **`.rigid` haptic tick on the release frame**. `tapTick` stays rendered but unmapped (`cues.arrowTap = ""`); one data change turns it on if the owner asks. | VERIFIED no tap sound (≈1630 taps); SPEC.md §5 item 4; DECISION haptic (§12) |
| MA4 | The exit colour ladder: combo index 1–2 **blue #10A2EF**, 3 **violet field**, ≥ 4 **rainbow field**; window 1.25 s tap-to-tap; a bump breaks the streak; ignored taps neither count nor break. | VERIFIED blue/blue/violet (S1-L52-three-exits); window INFERRED (84 % of 1630 video taps); bump rule DECISION |
| MA5 | Violet and rainbow colours are a **field fixed on the exit path** (arc coordinate), sampled by the moving body, never a gradient carried by the body. | VERIFIED motion §3.4 (violetfield_L52) |
| MA6 | All shards/debris are simulated in **screen pt** (gravity is the same at every zoom); board-anchored effects (key flight, tape, stars, badge) are in board content space. | INFERRED: measured g ≈ 1000–1300 pt/s² at pitches 17.9 and 28.1 alike |
| MA7 | Popups, panels and overlays appear and disappear **instantly** (dim in the same frame). Only first-time overlays (unlock, tutorials) stagger their content. | VERIFIED motion §6.3, fail §2 ("complete in a single frame") |
| MA8 | Buttons: **scale 0.95 on touch-down, instant**, held; action + click + haptic on **release**; back to 1.0 instantly. | VERIFIED motion §6.3 (Play, Continue) |
| MA9 | The level intro acks `introFinished` at **K + 1.02 s** (the HUD starts to drop), not at the end of the HUD pops: the board is legible and the player may tap. | DECISION (unobservable; owner's feel: no dead input) |
| MA10 | Level start and home return hard-cut **≤ 50 ms after release** (the original takes 56–100 ms). | VERIFIED original 0.06–0.08 s (Play) / ≈ 0.10 s (Continue); DECISION "ours ≤ theirs" (arch §10.2) |
| MA11 | The home-return sequence after a win is ONE queue of segments (Claw token → Streak strip → coin payout), each with the measured internal timing; a segment is skipped when its event is not active. | VERIFIED S1-L50-win-seq-2-continue (60 Hz + audio); queue rule DECISION |
| MA12 | Home characters loop at the measured periods: scientist **3.16 s**, right worker **10.2 s**, left worker **17.3 s** (> 15 s, no repeat seen). Poses are ours on those periods. | VERIFIED periods meta §8; poses DECISION |
| MA13 | Haptics: **`.rigid` 0.70** tap tick, **notification `.error`** on a heart loss (the contact frame), `.heavy` 0.85 bump without a heart, `.warning` on a fail offer, `.medium` 0.80 board clear, **`.success`** at the OUT! slam, `.medium` 0.65 bursts, `.light` 0.50 UI buttons, `.medium` 0.60 booster use, `.soft` 0.45 per landing coin. One haptic per frame, priority order §12.2. | DECISION (vibration cannot be recorded; justification §12.1) |
| MA14 | The frozen `AudioContract.swift` needs 5 more `SoundID` cases and 4 more `Haptic` cases (request §15.1). Until the orchestrator applies it, the fallback map in §15.1 keeps the build complete. | request |

---

## 2 Curve and timing catalogue (C1 `Motion/Curves.swift` + `Timing.swift`; SHELL mirrors the SwiftUI ones)

Each row is a named function the code calls; the section that uses it gives the numbers again with its anchor.

| name | definition | tag |
|---|---|---|
| `ExitKinematics.s(τ)` | `s = vmax·τ − (vmax − v0)·T·(1 − e^(−τ/T))` cells; v0 **7.67** c/s, vmax **73.86** c/s, T **0.353** s. `v(τ) = vmax − (vmax − v0)·e^(−τ/T)` | VERIFIED motion §3.3 (11 exits, 203 samples, RMS 0.082 cells) |
| `ExitKinematics.time(toTravel: d)` | inverse of s (bisection, 40 steps); table: d 0.5 → 0.043, 1 → 0.072, 2 → 0.115, 3 → 0.150, 5 → 0.209, 10 → 0.326, 20 → 0.513, 40 → 0.828 s | VERIFIED (the table is the unit test, ±0.003 s) |
| `Timing.exitColourRamp` | 0.09 s linear | VERIFIED motion §3.2 |
| `Curves.ripple` | kf over 0.233 s: radius 11 → 14.5 → 18 → 20.5 → 22 → 22.5 pt at 0, .05, .10, .15, .20, .233; core luminance 180 → 250 | VERIFIED out/ripple_* (board.json `ripple.*` already holds it) |
| `Curves.bumpOut(c)` | constant speed, duration `0.075 + 0.025·c` (c = contact travel, cells) | VERIFIED 2 v552 clips + INFERRED law |
| `Curves.bumpBack` | 0.14 s `easeOutQuad` | VERIFIED |
| `Curves.vignette` | alpha(d) = profile §3.4.4; opacity kf[0:1, 0.035:1, 0.333:0] | VERIFIED |
| `Curves.heartBreak` | halves: y = −115τ + 480τ² pt; x = ±37.5τ pt; rot ±(25°·min(τ/0.12,1) + 54°·max(τ−0.12,0)); alpha kf[0.30:1, 0.40:0] | VERIFIED motion §4 (two clips) |
| `Curves.introZoom` | scale 1.49 → 1.0, 1.35 s, `easeOutCubic` | VERIFIED out/introfit_L48 (RMS 0.29 pt) |
| `Curves.introDraw(n)` | strokeEnd: `f0 = 0.10 + 0.30/n` on the first frame, linear to 1.0 at `D(n) = 0.32 + 0.0216·n` s | VERIFIED 98 % times (24 arrows); f0 INFERRED fit of out/introdraw2_L48 |
| `Curves.hudDrop` | y offset −118.4 pt → 0, 0.334 s, `easeOutBack(3.42)` = `cb(0.333, 2.14, 0.667, 1)` | VERIFIED out/hudfit_L48 (RMS 2.2 pt) |
| `Curves.boosterSlide` | x offset ∓88.8 pt → 0, 0.209 s, `easeOutBack(2.57)` = `cb(0.333, 1.857, 0.667, 1)` | VERIFIED (RMS 1.2 pt) |
| `Curves.bigTimer` | scale kf[0:3.5, 0.067:1.42, 0.083:1.31, 0.10:1.17, 0.133:0.95, 0.167:0.88, 0.20:0.96, 0.25:1.0] | VERIFIED to 0.10 (out/bigtimer_L32 + L48 trace); the undershoot INFERRED |
| `Curves.heartPop` | scale kf[0:1.58, 0.05:1.36, 0.10:0.93, 0.133:0.89, 0.167:0.96, 0.20:1.04, 0.25:1.02, 0.30:1.0] | VERIFIED out/hud_intro_L48 (heart sizes 42 → 23.5 → 27.5 → 26.5 pt) |
| `Curves.pop(d, over)` | scale kf[0:0.2, 0.55·d:over, d:1.0], `easeOut` segments; the generic overshoot pop of overlays | VERIFIED shape (tutorials §6); `over` per element |
| `Curves.captionPop` | scale kf[0:0.7, 0.04:0.98, 0.08:1.10, 0.12:1.05, 0.16:1.0] (0.20 s total, last 0.04 hold) | VERIFIED tutorials §3 (25 fps) |
| `Curves.handIn` | scale 0.24 → 1.0 about the fingertip, 0.28 s `easeOutCubic` | VERIFIED |
| `Curves.handLoop` | period 2.10 s: hold 1.0 for 1.26 s → press 1.0 → 0.53 in 0.48 s `easeInOut` → release 0.53 → 1.0 in 0.36 s `easeOutQuad` | VERIFIED one cycle; period INFERRED |
| `Curves.keyFlight` | §3.5.2 | VERIFIED (one key) |
| `Curves.clearWave` | ring front r(t) = r_max·t/0.45; each dot: colour envelope kf[0:0, 0.05:1, 0.15:1, 0.40:0] after the front passes | VERIFIED duration 0.50 s; envelope INFERRED |
| `Curves.win` | §5 beat table (W-anchored) | VERIFIED S1-L50-win-seq-1 |
| `Curves.coinFly` | §8.3 segment C (5 coins, 0.22 s each, stagger 0.085 s, `easeInQuad`) | VERIFIED |
| `Timing.stageGap` | 0.70 s (W → next board's first frame) | VERIFIED tutorials §2 |
| `Timing.outOfTimeHold` | 1.61 s ("0:00" shown, then the popup) | VERIFIED fail §2 (META-L062-timer-last-seconds) |

---

## 3 The board

### 3.1 Tap ripple (B1 `RippleLayer`, ScreenFXView)
| # | start | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | R | 0.233 | pooled ripple disc at the release point (screen pt, not zoomed) · radius | 11 → 22.5 pt | kf (§2 `Curves.ripple`) | ◉ tap (if an arrow was accepted) | VERIFIED 3 clips |
| 2 | R | 0.233 | same · core luminance on white (black at alpha `(255 − L)/255`) | 180 → 250 (alpha 0.294 → 0.02) | kf `ripple.coreLum` | — | VERIFIED |
| 3 | R + 0.233 | 1 frame | same · hidden, back to the pool (6 layers) | — | — | — | VERIFIED "then gone" |
- Drawn on EVERY release inside the play rect, hit or miss (miss = DECISION, arch §5.3). Same transaction as the mover (arch P1).
  No ripple on HUD/booster buttons (they press-scale instead). No sound (VERIFIED).

### 3.2 Exit (B1 `ExitMover` + B2 painters, `StarTrail`, `DotsPainter`)

**3.2.1 Kinematics and look** (every exit, every painter)
| # | start | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | R (first frame = next vsync) | until the tail passes the screen edge | trimmed body stroke + head along the `ExitPath` · head travel s | 0 → path to the screen edge + arrow length | `ExitKinematics.s(τ)` sampled every 1/60 s, `calculationMode .linear` (arch §5.5) | ◉ tap on R | VERIFIED |
| 2 | R | 0.09 | black copy of the trimmed stroke + head on top of the painter · opacity | 1 → 0 (so the colour goes from the arrow's colour — black, or red if marked, or green if hinted — to the painter's) | lin | — | VERIFIED motion §3.2 (per-channel linear) |
| 3 | R | same as #1 | head rotation | steps at corners and tube turns (no tween; the path is a polyline with corner fillet 0.125 p) | discrete | — | VERIFIED |
| 4 | R | — | resting layers · hidden | same transaction | — | — | arch P1 |
| 5 | end of #1 | 1 frame | mover layers removed, `exitFinished` | — | — | — | arch §5.5 |
- **Layering**: above idle arrows/obstacles, under the HUD and boosters (VERIFIED shots L038-r07, L048-r17). A pipe passage draws inside
  the translucent tube (VERIFIED).
- `exitLeftBoard(a)` fires when the tail leaves its last grid cell (`exit.leftBoardAt = "lastCell"`, INFERRED from the win timing).
- Queued taps: an arrow leaves the blocking grid AT THE TAP (VERIFIED P02); two exits run independently.

**3.2.2 Painters (the combo ladder, §3.3)** — `board.json combo.ladder = ["solid","solid","violet","rainbow"]`, last repeats.
| painter | colour recipe | stars (§3.2.3) | tag |
|---|---|---|---|
| `solid` | body + head **#10A2EF** | 50 % #1E88F5, 50 % #7FD8FF | colour VERIFIED lossless (17 samples); star shades INFERRED (video) |
| `violet` | field along the path arc coordinate σ (cells from the path start): stops **#01ACFD · #3972FF · #7B3CFC · #B908FE · #7B3CFC · #3972FF** evenly over one period, **period 3.75 cells**, cyclic; phase offset = `fx` RNG × period per exit | the 4 distinct stops, picked by the spawn σ | VERIFIED look + hue range 190°–290° (video colours; lossless sample still open, clips-needed #10); period VERIFIED 3.5–4 cells |
| `rainbow` | field along σ: the 12 stops **#FF6500 · #FFCE01 · #9DE600 · #37E500 · #00E100 · #00D3AF · #00C1FF · #4079FF · #8D5FFF · #BC4BF3 · #FF2FC6 · #FF5A85** evenly over one period, **period 4.2 cells**, cyclic; the head takes the colour at its σ; random phase per exit | the palette colour at the spawn σ | palette VERIFIED lossless (bot L036-r06, L042-r02); period **[P3]**: hue along the stroke in the same two shots → 4.74 cells (L36, pitch 21.84) and 3.66 cells (L42, pitch 16.38); 4.2 = mid, DECISION |
- **Field fixed on the path** (MA5): colour(σ) with σ fixed to the path, so a screen point on the path keeps its hue while the body slides
  over it (VERIFIED: hue at a fixed point drifts only 50–150°/s while the body moves ≈ 1000 pt/s). No drift animation in V1
  (`rainbow.driftDegPerS = 0`, DECISION: imperceptible, and it would cost a per-frame `locations` animation on every run).
- Implementation: arch §5.5 painter A (one `CAGradientLayer` per straight run with stops at every palette step, fixed on the path,
  masked by the trimmed stroke + moving head). The `violet` painter is the same code with its 6-stop palette.

**3.2.3 Trail stars (B2 `StarTrail`)**
| property | value | tag |
|---|---|---|
| sprite | `boardTrailStar` (5-point rounded star, white, tinted per particle; MANIFEST B2) | VERIFIED look |
| where | spawned at the arrow's **tail** position as it moves (they line the path the tail has vacated, corners included); emission stops when the tail leaves the content rect (grid + 1-cell margin) | VERIFIED bot L036-r06 (stars follow the U-turn), L042-r02 |
| rate | **2.4 stars per cell** of tail travel → `CAEmitterLayer.birthRate` keyframed = 2.4 × v_tail(τ) (c/s) along with `emitterPosition` | VERIFIED ≈ 2.4 / cell |
| position jitter | uniform in a disc of radius **0.25 p** around the tail point (`emitterShape .circle`, `emitterMode .volume`) | VERIFIED ±0.25 cell |
| size | **0.30 p** ± 0.08 p (`scaleRange`) | VERIFIED 5–8 pt at p 21.8–26.2 |
| rotation | random 0–72°; spin ±90°/s (`spinRange`) | rotation VERIFIED random; spin DECISION |
| velocity | 0 (stars stay where born) | VERIFIED (no visible drift) |
| lifetime | **0.40 s**; alpha 1 → 0 linear over life (`alphaSpeed −2.5`), scale 1 → 0.4 over life (`scaleSpeed`) | VERIFIED life 0.25–0.4 s (L42 shot: the oldest visible stars ≈ 0.36 s old); linear fade = DECISION (emitter cells have no keyframes) |
| colour | per painter (table above) | — |
| per-exit emitter | 1 `CAEmitterLayer` per exit in `fxRoot`, `beginTime = convertTime(now)` (arch P2), `seed` from the `fx` stream (deterministic captures) | arch |
| budget | ≤ 5 × (0.4 s × 2.4 × 74 c/s) ≈ 360 live stars in the soak | arch §10 |

**3.2.4 Dots (B1 `DotsPainter`)** — CHANGED from arch §5.5 item 5:
- ONE `CAShapeLayer` in `dotsRoot` holding a disc (⌀ **0.192 p**, **#C5E1FF**) at **every cell occupied by an arrow at stage load**
  (hidden arrows included; their door/box sprite covers them), built with the stage, under `restRoot`. The departing arrow simply
  uncovers its dots; nothing animates. A cell no arrow ever occupied has no dot. VERIFIED motion §2.3 (shot 003: bluish fringe at
  outer corners; L32 cell (1,8) has none; the intro shows the dots before the arrows draw in).
- Cells of a broken box/pipe show dots only where arrows had been (VERIFIED shots 137, 141). The clear wave (§3.8) recolours this layer.

### 3.3 Combo ladder (C2 `ComboTracker`, `rules.json combo.*`)
- Index c of an accepted exit tap = c(previous) + 1 if `R − R_previous_accepted ≤ combo.window` (**1.25 s**), else 1. A tape bundle = one
  tap, one index for all members. VERIFIED ladder (1–2 blue, 3 violet, 4+ rainbow; S1-L52 taps 0.58 s and 0.75 s apart); window INFERRED
  (best fit 1.20–1.25 s over 1630 video taps).
- `combo.bumpBreaks = true`: a bump resets (the next exit is c = 1). DECISION (a mistake ends a streak; unverified, clips-needed #10).
- Ignored taps (`IgnoreReason`) neither count nor reset. Obstacle exits (key, pipe, tape) count like any exit. The ladder caps at
  rainbow (last entry repeats). DECISION.

### 3.4 Bump (B1 `BumpMover`, `ScreenFX`; HUD heart in S2)
Anchors: R (release), C = R + T_out (contact). c = contact travel in cells (the core's `BumpPlan.contactCells`: the head apex reaches
the blocker's stroke edge; `rules.json bump.arrowEdgeInset 0.11`, `obstacleEdgeInset 0.5`).

**3.4.1 The bumped arrow**
| # | start | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | R | T_out = 0.075 + 0.025·c | whole arrow snakes along its own path (tail follows) · head travel | 0 → c cells | **lin** (constant speed; bump-1 21.8 c/s, bump-2 12.6 c/s) | ◉ tap at R | VERIFIED speed + stop at the stroke edge; law INFERRED (3 points) |
| 2 | C | 0 | hold | — | — | ◉ heartLost at C (or ◉ bumpContact when no heart is lost) | VERIFIED none (≤ 1 frame) |
| 3 | C | 0.14 | same · head travel | c → 0 | `easeOutQuad` `cb(0.333,0.667,0.667,1)` | — | VERIFIED 0.144 s (bump-1), ≈ 0.137 (bump-2) |
| 4 | C + 0.017 | 0.103 | arrow stroke + head colour | black → **#EE0A13** (stays red for the level) | `easeInOut` `cb(0.42,0,0.58,1)` (S-shaped: R 13, 30, 93, 140, 190, 221, 235, 237 per 1/60 s) | — | VERIFIED lossless shot 110 + both clips |
| 5 | C + T_back | 1 frame | `bumpFinished` | — | — | — | arch |
- `bump.hold = 0` (was 0.10 in Tuning.swift's compiled default: board.json already overrides it). No shake of board or HUD. Silent.
- Board.json keys (already present, keep): `bump.outBase 0.075`, `bump.outPerCell 0.025`, `bump.hold 0`, `bump.back 0.14`,
  `bump.redFrom 0.017`, `bump.redTo 0.12`.

**3.4.2 The blocker flash**
| # | start | dur | property | from → to | easing | tag |
|---|---|---|---|---|---|---|
| 1 | C + 0.02 | 0.10 | the WHOLE blocking arrow's colour (a red copy on top, opacity) | black → #EE0A13 | `easeInOut` | VERIFIED bump-1 (R 12 → 237 over 0.10 s) |
| 2 | C + 0.13 | 0.20 | same | red → back to its own colour (black, or red if it was marked) | lin (R 234 → 0) | VERIFIED ("straight back to black by τ ≈ 0.33") |
- Blocker = an obstacle (door, box, pipe tube, platform): the same timing on a red tint overlay (the sprite as mask), peak alpha 0.6.
  DECISION (never observed).
- Keys: `bump.blockerRedFrom 0.02`, `bump.blockerRedTo 0.12`, `bump.blockerBlackAt 0.33` (present).

**3.4.3 The ✖ badge** (fxRoot, board content space; code-drawn: two rounded bars at ±45°, fill **#F62631**, outline **#7A0A10**
0.08 p, a lighter bevel line on the upper edge #FF7A80; size **1.0 p** across; centred on `BumpPlan.contactPoint`)
| # | start | dur | property | from → to | easing | tag |
|---|---|---|---|---|---|---|
| 1 | C + 0.017 | 0.103 | scale · opacity | 1.4 → 1.0 · 0 → 1 | `easeOutQuad` | VERIFIED |
| 2 | C + 0.12 | 0.21 | hold | — | — | VERIFIED |
| 3 | C + 0.33 | 0.10 | scale · opacity | 1.0 → 0.5 · 1 → 0 | `easeInQuad` | VERIFIED (gone by τ 0.43) |
- Keys present: `bump.badge*`.

**3.4.4 The red screen-edge tint** (ScreenFXView, 4 edge `CAGradientLayer`s, colour #FF0000)
- Alpha by distance d from the edge (stops): **d 0 → 0.42 · 5 pt → 0.37 · 10 → 0.31 · 20 → 0.22 · 30 → 0.16 · 45 → 0.08 · 70 → 0.02 ·
  90 → 0**; the corners add both edges. VERIFIED both v552 clips (≈ 0.42·e^(−d/27 pt)); the tape clip's edge pixel (254,155,155) = 0.39 ✓.
| # | start | dur | property | from → to | easing | tag |
|---|---|---|---|---|---|---|
| 1 | C | 1 frame | layer opacity | 0 → 1 (full on the contact frame) | — | VERIFIED |
| 2 | C | 0.035 | hold | 1 | — | VERIFIED |
| 3 | C + 0.035 | 0.298 | opacity | 1 → 0 | lin | VERIFIED (0 at τ 0.333) |
- Keys present: `vignette.alpha 0.42`, `vignette.decayPt 27`, `vignette.hold 0.035`, `vignette.total 0.33`. A second bump restarts it.

**3.4.5 The heart fade (HUD, S2 `HeartsRow`)** — the **rightmost full** heart breaks (v552), on the contact frame C:
| # | start | dur | layer · property | from → to | easing | tag |
|---|---|---|---|---|---|---|
| 1 | C | 1 frame | full heart → hidden; the 2 halves (`heartHUDHalves`, MANIFEST) appear at its place with a jagged crack | — | — | VERIFIED |
| 2 | C | 0.40 | each half · y | 0 → −6.9 pt (τ 0.12, apex) → +30.8 pt (τ 0.40): `y = −115τ + 480τ²` (v0 −115 pt/s, g 960 pt/s²) | physics | VERIFIED (rise 7 pt by 0.12, then g ≈ 960) |
| 3 | C | 0.40 | left half · x, rotation | 0 → −15 pt (`x = −37.5τ`) · 0 → −25° at τ 0.12 → −40° at τ 0.40 | lin | VERIFIED spread ±15 pt, tilt ±20–30° |
| 4 | C | 0.40 | right half | mirrored (+x, +rotation) | lin | VERIFIED |
| 5 | C + 0.30 | 0.10 | halves · opacity | 1 → 0 | lin | VERIFIED (fade 0.30–0.40) |
| 6 | C | — | the empty slot under it (recess **#6C94DC**, `heartHUDLost`) | visible as the halves leave (from τ ≈ 0.05) | — | VERIFIED |
- Must start ON the contact frame: drive it with a CA layer or a `TimelineView` on `MotionClock` started by the `.heartLost` event
  (the HUD's ≤ 10 Hz throttle does not apply to this one-shot animation). No pop, no shake. Silent.

**3.4.6 Tape bundle bump** (VERIFIED META-L062-tape-blocked-bump, 60 Hz): the whole bundle + its tape translate rigidly along the common
direction by the **smallest** member contact travel with the same law (§3.4.1: ≈ 0.5 cell in ≈ 0.065 s), then back (0.14 s
`easeOutQuad`); **every member turns red**; ONE ✖ at the first contact point; every blocked member's blocker flashes; ONE heart; one
vignette; the bump also starts the timer (VERIFIED fail §3).

### 3.5 Obstacles (B2)

**3.5.1 Tape carry.** On one tap every member exits with the same `s(τ)` (straight parallel members), the tape sprite translates with
them (`s(τ)·p` along the direction) and leaves the screen with them; each member has its own stars; the painter is the tap's combo
painter for all members. VERIFIED shots 018/019 (L32), V1 81.08–81.48. Member start sync: same frame (DECISION; clips-needed #5 still open).

**3.5.2 Key flight + door burst** (anchor R = the key arrow's release; VERIFIED S1-L33-key-first, tap release ≈ 0.52; out/keytrack_L33,
out/door_burst_L33). Key motion in board content space, measured at p = 17.86: lengths below are also given in cells.
| # | start | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | R | 1 frame | the purple ring (the key's hanger) · hidden; the key stays where it hung while the arrow exits through it | — | — | ◉ tap | VERIFIED |
| 2 | R + 0.23 | 0.08 | key · y · rotation | +8.6 pt (0.48 p) sag · wobble −15° → +15° → 0 | `easeOutQuad` / kf | — | VERIFIED |
| 3 | R + 0.31 | 0.22 | key · y | −41 pt (2.3 p) float up (apex at ≈ R + 0.55) | `easeInOut` | — | VERIFIED |
| 4 | R + 0.55 | T_dive (0.224 for the measured 160 pt) | key · position | apex → the target lock's keyhole: y parabola with **g ≈ 7650 pt/s² at p 17.86 = 428 p/s²** (content space, starts at rest), x linear; for another geometry T_dive = clamp(√(2·D/428), 0.16, 0.40) with D = straight distance in cells, plus a lift `0.25·D·sin(πu)` toward screen-up when the lock is above the apex | physics / `easeInQuad` on x | — | VERIFIED 1 key (dive 160 pt, RMS 2 pt); far doors INFERRED (clips-needed #14) |
| 5 | dive end (R + 0.78 measured) | 0.15 | key · scale · rotation | 1.0 → 0.7 · to point into the keyhole | `easeOutQuad` | — | VERIFIED "insert ≈ 0.15 s" (1.298 → 1.448) |
| 6 | insert end + 0.08 (R + 1.01) | 0.10 | key · rotation | +45° → +90° (turn in the lock) | `easeInOut` | — | VERIFIED (1.531 → 1.631) |
| 7 | burst = turn end + 0.03 (R + 1.14 for the measured geometry) | 1 frame | door sprite + lock + key · hidden; revealed arrows' layers added (dots already under them); `doorBurst` ack | — | — | ◉ burst | VERIFIED tap → burst 1.14 s |
| 8 | burst | 0.20 | white flash on the lock (disc r 0.9 p, white) · opacity | 0 → 1 (burst + 0.017) → 0 (+0.216) | kf | — | VERIFIED (peak 1.681, gone 1.88) |
| 9 | burst | 0.9 | ≈ **60 door shards** (§10 particle table) | pop + fall | physics | — | VERIFIED counts/timing, g INFERRED |
- Door opening order and the `opens` rule are C2's. Several keys fly concurrently. Silent (VERIFIED).

**3.5.3 Pipe passage + counter + shatter** (VERIFIED S1-L35-pipe-break at p 28.09; out/pipe_break_L35; counter timing V2 L23)
| # | start | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | R | … | the arrow runs with the same `s(τ)` through the tube (drawn under/inside the translucent tube: it reads lighter blue) and out of the far mouth in that mouth's direction | — | kinematics | ◉ tap | VERIFIED |
| 2 | at `leaveTube` (the head comes out of the far mouth) | 1 frame | counter digits (non-final pass) | n → n − 1 (instant glyph swap, no pop) | — | — | timing VERIFIED video-levels-D ("counts down when the passing arrow comes out of the far mouth", L35/L38; ~0.42–0.6 s after the tap); no-pop INFERRED |
| 3 | leaveTube + **0.05** (final pass; tail still inside) | 1 frame | tube, mouths, counter box · hidden; `pipeBroken` ack; the tube's cells now show their dots | — | — | ◉ burst | VERIFIED 0.782 − 0.732 |
| 4 | same | 1.4 | **pipe shards** (cyan glass) + the counter box split in 2 tumbling halves + both gold rims dropping and tumbling (§10) | — | physics | — | VERIFIED |
- `rules.json pipe.countAt = "leave"` (the visible `pipeCount` beat; the LOGICAL decrement stays at the tap, arch §4.4). Silent.

**3.5.4 Box (v552) and Curtain (videos; drawn with the phone's box skin, SPEC.md §5 item 11)** (VERIFIED S1-L50-box-break, out/boxbreak_L50)
| # | start | dur | property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | R of EVERY accepted exit (a tape bundle lowers it by its member count) | 1 frame | every box's counter digits | n → n − k (instant; all boxes together; "0" is never drawn) | — | — | VERIFIED (counter reads the new value on the disc frame) |
| 2 | R of the exit that takes it to 0 | 1 frame | box sprite + ring · hidden; `counterBroken` ack; revealed arrows live and visible; cells show dots where arrows had been | — | — | ◉ burst (replaces ◉ tap on that frame, §12.2) | VERIFIED "same frame as the first motion" |
| 3 | same | 0.67 | ≈ **140 box shards** + 4 ring chunks (§10) | — | physics | — | VERIFIED |
- No flash, no pre-shake (VERIFIED). `rules.json box.countAt = "tap"` (present). Silent.

**3.5.5 Elevator** (videos only, drawn in the phone palette). VERIFIED `research/video-levels-D.md` (V2 L31–L35, 5 platforms: L32
`L032-doors-fine`, L33 `L033-arrow7`). The platform is a rounded lavender slab with a hatched rim and a vertical centre divider (two
closed doors); arrows stand on it. Anchor O = the frame the LAST platform arrow's tail clears the platform cells (0.15–0.55 s after
its tap, depending on its length).
| # | start | dur | property | from → to | easing | tag |
|---|---|---|---|---|---|---|
| 1 | O + 0.02 | 0.30 | the two door halves (`elevatorPlatform`, code: two masked halves) · x offset | 0 → ±half-width (part from the centre divider outward, clipped by the platform frame) | `easeInOut` | VERIFIED (doors start 0.02 s after the clear) |
| 2 | O + 0.02 | 0.30 | hidden layer (its arrows + dots) · a dark tint over it (black overlay, opacity) | shown under the doors with tint 0.55 → 0 | lin | VERIFIED ("under a dark tint, then at full colour"; full by ≈ O + 0.35) |
| 3 | O + 0.30 | 0.15 | platform frame + hatched rim · opacity | 1 → 0 | lin | VERIFIED (frame gone by ≈ O + 0.45) |
- The hidden layer BLOCKS from the start of row 1, before it is visible (VERIFIED L32 1235.10 bump). Whether it is already live
  between the last platform tap and O is unobserved: the rules owner decides (`rules.json elevator.activateAt`, "tap" today per
  arch §4.4; "clear" is equally consistent with all 5 elevators). Empty platform cells do not block rays (VERIFIED). Silent.
- `board.json elevator.*`: `doorsAt 0.02`, `doorsDur 0.30`, `tintFrom 0.55`, `frameFadeAt 0.30`, `frameFadeDur 0.15`.

**3.5.6 Corner** (older builds only; INFERRED web §3). The exit path bends 90° at the wedge (head rotation steps, like a tube turn); on
the frame the head reaches the wedge cell centre the wedge sprite pops scale 1.0 → 1.15 → 1.0 in 0.15 s (`easeOutQuad` up 0.05 s,
`easeInOut` down 0.10 s). The pop is DECISION. Silent.

**3.5.7 Obstacle build-in**: obstacles are drawn complete on the first frame of a level and only take part in the intro zoom (no fade).
VERIFIED motion §6.1 ("pipes/obstacles drawn complete from the first level frame"). Closes arch §5.7 "obstacle sprites fade in (PENDING)".

### 3.6 Level intro (from home Play, win-panel Continue into the FTUE chain, and Try Again) — anchor K
VERIFIED S1-L48-play-intro (60 Hz; cut = 0.375 → K) + S1-L49; out/introfit_L48, introdraw2_L48, hudfit_L48, hud_intro_L48.
| # | start | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 0 | Play touch-down | until release | Play button · scale | 1.0 → 0.95 (one frame) | instant | — | VERIFIED |
| 0b | Play release (P) | — | click | — | — | ♪ uiClick, ◉ button | VERIFIED click on release |
| 1 | K ≤ P + 0.05 | 1 frame | home → level hard cut (no transition) | — | — | — | VERIFIED cut (original +0.06–0.08 s); ≤ 0.05 DECISION MA10 |
| 2 | K | 1.35 | board `stage` layer transform · scale about the board centre (screen (196.5, 439.2) at fit) | **1.49 → 1.0** | `easeOutCubic` `cb(0.333,1,0.667,1)` | — | VERIFIED (RMS 0.29 pt; exp and spring fit worse) |
| 3 | K | 1 frame | dots layer (all arrow cells) + obstacle sprites · visible | — | — | — | VERIFIED |
| 4 | K | D(n) = 0.32 + 0.0216·n | each arrow body · strokeEnd (all arrows at once, n = its cells) | `0.10 + 0.30/n` → 1.0 | lin | — | VERIFIED 98 % times; start fraction INFERRED |
| 5 | when #4 reaches 1.0 | 1 frame | that arrow's head · opacity | 0 → 1 | — | — | VERIFIED "head appears when reached" |
| 6 | **K + 1.015** | 0.334 | HUD top row (coin group, back, panel + "Level N" tab + timer pill + hearts row, pause) · y offset | −118.4 pt → 0 | `easeOutBack(3.42)` `cb(0.333,2.14,0.667,1)` (peak +37 pt past rest at +0.16) | — | VERIFIED pause top −49.9 → 106 → 68.5; coin group + tab riding along = DECISION (the tab is part of the v552 panel) |
| 6b | K + 1.015 | — | `introFinished` ack → `.ready` (input opens, timer frozen at its limit) | — | — | — | DECISION MA9 |
| 7 | K + 1.092 | 0.209 | left booster (tray + button + badge) · x offset; right booster mirrored | −88.8 → 0 / +88.8 → 0 pt | `easeOutBack(2.57)` `cb(0.333,1.857,0.667,1)` | — | VERIFIED |
| 8 | K + 1.015 → K + 1.339 | — | timer pill shows an EMPTY bar (no digits); heart slots show the empty recess #6C94DC | — | — | — | VERIFIED V1; INFERRED v552 |
| 9 | **K + 1.339** | 0.25 | the timer text ("3:00", "2:30", …) · scale about the text centre | kf `Curves.bigTimer` (3.5 → 1.42 → … → 1.0) | kf | — | VERIFIED to 0.10 s; undershoot INFERRED |
| 10 | K + 1.406, 1.505, 1.622 | 0.30 each | heart 1, 2, 3 · scale (red heart appears in its slot) | kf `Curves.heartPop` (1.58 → 0.89 → 1.04 → 1.0) | kf | — | VERIFIED (stagger 0.099 / 0.117) |
| 11 | K + 1.92 | — | intro visually complete | — | — | — | VERIFIED ≈ cut + 1.83 |
- Everything silent after the click (VERIFIED). Zoom and pan reset to fit/centre on every level start and Try Again (VERIFIED boosters §4).
- Taps during #2's last 0.33 s land on a board still at s ≤ 1.01: the hit test converts the touch through the `stage` layer's
  PRESENTATION transform (B1).
- **FTUE first board** (`IntroStyle.growFromTailsNoHUD`, L1-4 stage 1): Loading cross-fades into the level (§7) with the HUD already
  in place; rows #3–#5 only (no zoom, no HUD drop). `introFinished` at the first board frame + 0.36 s (when the "Tap to move!" hint
  appears, §6.4). VERIFIED V1 (no HUD intro, no zoom visible); draw timing = the phone law (DECISION: phone wins on feel).
- `board.json`: `intro.zoomFrom 1.49`, `intro.zoomDuration 1.35`, `intro.drawBase 0.32`, `intro.drawPerCell 0.0216` (present) + NEW
  `intro.drawStartFraction [0.10, 0.30]` (f0 = a + b/n), `intro.ackAt 1.015`. `ui.json` NEW `hudIntro.*` (§13.2).

### 3.7 Stage transitions ("Levels 1-4", any multi-board session) — anchor W of the stage's last arrow
VERIFIED V1 L1-4 (25 fps: last arrow gone ≈ 5.08, dots recoloured 5.12, fading 5.20–5.76, stage 2 builds at 5.80, complete ≈ 6.24).
| # | start | dur | property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | W | 0.50 | clear wave through the dots (§3.8) | — | — | ◉ clear | VERIFIED |
| 2 | W + 0.12 | 0.56 | dots layer · opacity | 1 → 0 | lin | — | VERIFIED 5.20–5.76 |
| 3 | W + 0.70 | 1 frame | old stage cleared; new stage's dots + obstacles visible; the timer pill re-arms to the new stage's limit (text swap, no pop); hearts carry (no animation) | — | — | — | VERIFIED gap 0.7 s |
| 4 | W + 0.70 | D(n) | new arrows draw tail → head (§3.6 #4–#5); NO zoom, NO HUD intro | — | lin | — | VERIFIED V1 (0.44 s for its small boards; D(8) = 0.49) |
| 5 | end of the longest draw | — | `stageTransitionDone` ack → `.ready` | — | — | — | DECISION |
- `board.json stageGap 0.7` (present), NEW `stage.dotsFadeFrom 0.12`, `stage.dotsFade 0.56`. Silent.

### 3.8 Board-clear wave (before the win; also inside stage transitions) — anchor W
VERIFIED S1-L50-win-seq-1 (60/30 Hz; P3 re-read of the sheet `ov_S1-L50-win-seq-1_0.85-2.6`): the dots flash colour in a ring
expanding from the board centre, warm (orange/yellow) at the centre at W + 0.06, green/cyan mid-way, blue/violet/pink at the rim by
W + 0.46; back to #C5E1FF by ≈ W + 0.6.
| property | value | tag |
|---|---|---|
| geometry | centre = the grid centre (content space); r_max = distance to the farthest dot | VERIFIED |
| front | r(t) = r_max · t / 0.45 (t from W) | VERIFIED (outermost ring at ≈ W + 0.46) |
| hue by radius | the rainbow palette indexed by r/r_max: index 0 **#FF6500** at the centre … index 10 **#FF2FC6** at r_max (evenly) | VERIFIED order (orange → yellow → green → cyan → blue → violet → pink) |
| per-dot envelope | after the front passes the dot: colour weight kf[0:0, 0.05:1, 0.15:1, 0.40:0] over #C5E1FF | INFERRED (0.1 s sampling) |
| dot size | unchanged (⌀ 0.192 p) | VERIFIED |
| implementation | container masked by the dots path (built once at the clear, ≤ 1 ms) → a static radial rainbow `CAGradientLayer` (the palette by radius) → masked by a radial ring alpha gradient whose `locations` animate outward (0.45 s, lin) with a 0.15·r_max soft trailing edge | arch §5.7 (adapted: colour by radius, ring = alpha) |
| end | `clearWaveFinished` at W + 0.50 — NOT a gate for the celebration, which runs on its own W clock (§5) | DECISION (the sign enters at W + 0.41, before the wave ends) |
Silent (VERIFIED). ◉ clear at W.

### 3.9 Zoom, pan, limits, inertia (B1 `BoardScrollView`)
| item | value | tag |
|---|---|---|
| zoom range | pitch **14.036 … 28.07 pt absolute** (`zoom.minPitch 14.036`, `zoom.maxPitch 28.07`); a board that opens at 14.0 cannot zoom out, one that opens at 28.07 cannot zoom in | VERIFIED motion §6.7, boosters §4 |
| pinch beyond a limit | rubber-band, then snaps back to the limit: UIScrollView `bouncesZoom = true` (native ≈ 0.25–0.35 s spring) | DECISION (shots cannot see a snap-back) |
| pan limit | **the play-rect centre (196.5, 438.5) may reach, but not pass, the grid's outer edge** (a grid edge can be dragged to the viewport centre and no further, ± ½ cell), at every zoom incl. fit; implement with `contentInset` = (playRect/2 − 1 cell margin·zoom) per side, recomputed in `scrollViewDidZoom` | VERIFIED meta-116…123 (edges measured 182/205–211 pt horizontally, 418/443 vertically) |
| pan beyond the limit | rubber-band + snap back (`bounces = true`, native) | DECISION (not clip-verified) |
| inertia | native `decelerationRate = .normal` (0.998/ms) | DECISION (clips-needed #13 open) |
| tracking | 1:1 after the pan recogniser begins (slop 10 pt) | DECISION |
| slop | **10 pt** (`input.slopPt`): a release moved ≤ 10 pt fires; farther = a pan, no tap | DECISION (spike value = iOS pan hysteresis; a 52 pt swipe on an arrow panned without firing, VERIFIED) |
| pinch-out from a panned state | returns to the fit SCALE but keeps the pan offset | VERIFIED meta-124/125 |
| double tap | nothing | VERIFIED |
| reset | fit + centred on every level start / Try Again | VERIFIED |
- board.json: replace `pan.slackPt` by NEW `pan.limit = "centreInGrid"` (`pan.slackPt` ignored when set), `pan.bounces true`,
  NEW `zoom.bounces true`, `pan.deceleration "normal"`.

### 3.10 Booster effects on the board and HUD (G2 `BoosterDirector`, B2 camera/highlight, S2 HUD bits) — anchor B
**3.10.1 Bulb (hint)** — VERIFIED META-L062-bulb-hint (clip starts mid-camera; B-relative starts are DECISION from the clip + boosters §1),
lossless meta-064 (hint colour **#00DE00**, AA rim #009100 **[P3]** most common pixel (0,222,0)).
| # | start | dur | property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 0 | B | — | booster button press/release (§6.1), badge n → n − 1 (instant) | — | — | ♪ uiClick, ◉ booster | VERIFIED badge; click DECISION (UI button) |
| 1 | B + 0.05 | 0.80 | scroll view zoom + offset | current → **max zoom (28.07 pt/cell)** centred on the hinted unit (clamped by the pan limit) | `ease` `cb(0.25,0.1,0.25,1)` | — | VERIFIED zoom to max + ease-out tail (fast 6 pt/frame, then 1 pt/frame); start DECISION |
| 2 | B + 1.03 | 0.20 | hinted arrow(s) stroke + head colour | black (or red) → #00DE00 | lin | — | VERIFIED 0.98 → 1.18 |
| 3 | B + 1.23 | 0.13 | hold green | — | — | — | VERIFIED |
| 4 | B + 1.36 | 0.17 | colour | green → its own colour | lin | — | VERIFIED |
| 5 | B + 1.53 | 0.38 | off | — | — | — | VERIFIED |
| 6 | B + 1.91 | 0.19 | colour | → #00DE00, then **stays green** until tapped | lin | — | VERIFIED (blink period ≈ 0.88 s) |
| 7 | the hinted unit's `exitLeftBoard` | 0.50 | zoom + offset | → fit, centred | `easeInOut` | — | INFERRED (the next shot is at fit); timing DECISION |
- Using the bulb never starts the timer (VERIFIED). A user pinch/pan during #1 or #7 cancels the camera animation (DECISION: never
  fight the finger). The hinted arrow's exit ramps from green to its painter colour (§3.2.1 #2).

**3.10.2 Hourglass (freeze)** — VERIFIED META-L062-hourglass-freeze (clip starts after the tap; offsets from B are DECISION, shifted
by 0.08 s so the flight fits `boosters.freezeFlight`), shot meta-065 (**[P3]** frost and tray measured). The timer freezes AT B.
| # | start | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 0 | B | — | booster press/release; badge n → n − 1; the level clock freezes (`freezeStarted`) | — | — | ♪ uiClick, ◉ booster | VERIFIED freeze at once |
| 1 | B | 0.12 | icy hourglass (`boosterFreeze` art at 94 × 100 pt, FXOverlay, screen space) at **(192, 612)** · scale · opacity | 0.3 → 1.0 · 0 → 1 | `easeOutBack(1.70)` | — | spawn place VERIFIED (lower centre); pop DECISION |
| 2 | B + 0.10 | 0.83 | hourglass · y (centre) | 612 → 405 pt (90 % of the rise in the first 0.45 s) with a gentle rock ±4°, period 0.6 s | `easeOutCubic` | — | VERIFIED y 607 → 422 (0.45 s) → 405 (0.80 s) |
| 3 | B + 0.98 | 0.40 | hourglass · position along an arc · scale | (194, 400) → the timer pill's stopwatch **(107, 94)**, arc control point (175, 200) · 1.0 → 0.35 | `easeInQuad` | — | VERIFIED accelerating up-left, tracked to (162, 242) at +0.35 s |
| 4 | B + 1.38 | 0.25 | stopwatch icon · icing overlay (`iconStopwatchIced`: snow cap + icicles, UI-ART request) · opacity | 0 → 1 (hourglass hidden on arrival) | `easeOutQuad` | — | VERIFIED sheet ("stopwatch turns icy") |
| 5 | **B + 1.60** | 0.20 | frost vignette (screen space, §3.10.3) · opacity | 0 → 1 | `easeOutCubic` (≈ 80 % on the first frame) | — | VERIFIED edge luminance 255 → 202 (first frame) → 189 (+0.25) |
| 6 | B + 1.60 | 0.20 | countdown tray under the timer pill (frame **93 · 118 · 92 × 25 pt**) · y offset | −25 → 0 pt (slides out from under the pill) | `easeOutBack(1.70)` | — | tray VERIFIED meta-065; slide DECISION |
| 7 | B + 1.60 | **10.0** | tray: digit = ceil(remaining) "10" … "1" (instant swaps, navy #0C2A6B-class GameText 16 pt); blue bar width 100 % → 0 % | lin | — | VERIFIED "10" start, "6" with ≈ 55 % bar |
| 8 | B + 11.60 | 0.30 | frost · icing · opacity | 1 → 0 | lin | — | DECISION (end not recorded, clips-needed #20) |
| 9 | B + 11.60 | 0.15 | tray · y offset | 0 → −25 pt, then hidden; the timer resumes on this frame (`freezeEnded`) | `easeInQuad` | — | DECISION |
- `rules.json boosters.freezeSeconds 10` (present), `boosters.freezeFlight` **1.6** (was 1.5; the countdown and the clock's 10 s
  start at B + 1.60). Silent after the click (VERIFIED). While frozen the timer text does not change.

**3.10.3 Frost vignette look** ([P3] meta-065, lossless): colour at the very edge **#6BD4F8** (107,212,248) → white; depth to white
**≈ 30 pt at the left/right edges, ≈ 88 pt at the bottom and top** (the top reads icy across the whole status/HUD band); a crystalline
texture (fine cracks, a few snowflakes and twinkles). Build: 4 edge gradients (#6BD4F8 α 1 → 0 over those depths) + ONE static frost
overlay PNG `fxFrostEdge` (393 × 852 pt @3x, our own cracks/flakes, alpha only at the edges; UI-ART request §15.4). No animation
while frozen (VERIFIED static in the shot sequence).

---

## 4 HUD motion (S2)

| event | start | dur | property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| intro drop / boosters / big timer / hearts | §3.6 #6–#10 | | | | | — | VERIFIED |
| heart lost | C | 0.40 | §3.4.5 | | | ◉ heartLost | VERIFIED |
| timer tick | every displayed second | 1 frame | text swap m:ss (no leading zero: "0:18" … "0:00"; `displayedSeconds = ceil(remaining)`) | — | — | — | VERIFIED |
| last seconds | — | — | **no colour change, no pulse, no scale, no sound** (`rules.json clock.alerts = []`) | — | — | — | VERIFIED META-L062-timer-last-seconds (18 s) |
| time out | "0:00" shown | **1.61** | hold, input locked, in-flight exits finish | — | — | — | VERIFIED |
| Out of Time popup | "0:00" + 1.61 | 1 frame | popup complete (dim 0.94 + panel) | — | — | ◉ fail | VERIFIED "complete in one frame" |
| hearts out | C of the 3rd heart + **0.60** | 1 frame | "Out of Lives!" popup | — | — | ◉ fail | INFERRED (shots only; after the heart break ends at C + 0.40) |
| Add Time (+30 sec) | popup close | 0.25 | timer text · scale | 1.3 → 1.0 (the new value) | `easeOutBack(1.70)` | — | DECISION |
| Add Lives (+3) | popup close | 0.30 + stagger 0.10 | the 3 hearts re-pop left → right in their slots | `Curves.heartPop` | kf | — | DECISION (mirrors the intro) |
| coin pill (in level) | spend | 1 frame | number swap | — | — | — | DECISION |
| booster badge | use | 1 frame | n → n − 1 | — | — | — | VERIFIED |
| freeze tray | §3.10.2 | | | | | | |
- `ui.json` NEW `hud.outOfTimeHold 1.61`, `hud.heartsOutDelay 0.60` (read by GAME's FailFlowDirector; mirror in `game.json` if GAME
  prefers, same keys).

---

## 5 Win: celebration, logo slam, confetti, fireworks, panel (S2 `WinLogoSequence`, `Confetti`, `Fireworks`, `WinPanel`)

Anchor **W** (the last arrow's tail leaves its last cell). VERIFIED S1-L50-win-seq-1 (60/30 Hz, unskipped, silent) + [P3] sheet
2.4–4.8 s; the same beats in V1 (+0.05 s). The celebration clock starts AT W, concurrently with the clear wave (§3.8). Our logo is
"ARROW OUT!" (`logoArrowOut` split into parts, §15.4): blue sign plate, the letters A-R-R-O-W, the purple arrow sign, "OUT!".
Rest layout (from `uim celebrate.logo` 46 · 294.9 · 307.9 × 232.2): blue sign centre **(199, 351)**, arrow sign centre **(205, 471)**,
group centre (200, 411).

| # | start (W +) | dur | layer · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | 0 | 0.50 | clear wave | §3.8 | | ◉ clear | VERIFIED |
| 2 | 0.41 | 0.23 | blue sign · position (arc) · rotation · scale | (−150, 900) → (199, 351) via control (−40, 420) · −200° → −3° · 0.6 → 1.0 | `easeOutCubic` | — | VERIFIED path (bottom-left, spinning, lands slightly tilted) |
| 3 | 0.59 + 0.035·i (i = 0…4) | 0.12 | letter i · scale | 0 → 1.25 (0.07) → 1.0 | `easeOutQuad` / `easeInOut` | — | VERIFIED "one after another" 0.59 → 0.73 (4 letters); 5-letter stagger DECISION |
| 4 | 0.64 | 0.23 | purple arrow sign · position (arc) · rotation · opacity | (−120, 900) → (205, 471) via (−20, 560) · −40° → +2° · 0.3 → 1.0 | `easeOutCubic` | — | VERIFIED (rises from bottom-left, pale while moving) |
| 5 | 0.94 | 0.13 | "OUT!" · scale · opacity | 0.4 → 2.5 (wider than the screen) · 0.5 → 1.0 | `easeOutCubic` | — | VERIFIED (small/pale at 1.73, > screen width by 1.86) |
| 6 | 1.07 | 0.40 | "OUT!" hold | 2.5 → 2.6 | lin | — | VERIFIED "holds" |
| 7 | **1.47** | 0.17 | "OUT!" · scale (the slam) | 2.6 → 1.0 | `easeInCubic` | — | VERIFIED 2.26 → 2.43 |
| 8 | 1.64 | 0.10 | "OUT!" + arrow sign · scale Y (impact squash) | 1.0 → 0.92 → 1.0 | kf | **◉ win** (on this frame) | squash DECISION; slam frame VERIFIED |
| 9 | 1.64 | 0.26 | whole logo group · scale | 1.0 → 0.94 | `easeOutQuad` | — | VERIFIED "ends a bit smaller" |
| 10 | 1.24 | 0.34 | full-screen dim (over board + HUD, under the logo) · opacity | 0 → **0.90** black | lin | — | VERIFIED luminance 255 → 40, lin 0.33 s; uim `dim.popup` 0.894 |
| 11 | 1.47 | → | confetti burst from the bottom, then rain (§10) | | | — | VERIFIED |
| 12 | 1.60 … | → | 6 firework rockets (§10): launches at W + 1.60, 1.78, 1.95, 2.15, 2.40, 2.75; bursts at W + 2.24, 2.44, 2.64, 2.84, 3.07, 3.47 | | | — | VERIFIED rocket trails from 2.31, bursts ≈ clip 3.03, 3.23, 3.43, 3.63, 3.86, 4.26 [P3] |
| 13 | each burst | 0.15 | full-screen white flash · opacity | 0 → 0.08 → 0 | lin | — | VERIFIED "bursts flash the background"; magnitude DECISION |
| 14 | 3.90 | 1 frame | logo + fireworks removed (confetti keeps falling) | — | — | — | VERIFIED one confetti-only frame |
| 15 | **3.94** | 1 frame | win panel (normal / Hard red / Super Hard purple) appears complete, over the 0.90 dim; coins NOT counted up on the panel | — | — | — | VERIFIED instant |
| 16 | 3.95 | 0.13 | Streak Race strip (`streakRace.*`, bottom band) · y offset | +152 → 0 pt, with the PREVIOUS multiplier chip lit | `easeOutCubic` | — | VERIFIED 4.743 → 4.876 |
| 17 | 4.34 | 0.31 | the lit (green) chip · x | previous → new multiplier chip | `easeInOut` | — | VERIFIED 5.13 → 5.44 |
| 18 | 4.65 | 0.15 | orange ring on the new chip · scale | 0.6 → 1.0 | `easeOutBack(1.70)` | — | VERIFIED ring; pop DECISION |
| 19 | 3.94 | — | confetti emission stops; live pieces finish falling behind the panel (≤ 2.5 s) | | | — | VERIFIED V1 ("keeps falling behind it") |
- **Tap to skip** (VERIFIED V1: 13 of 17 wins skipped; not re-tested on v552): any tap from **W + 0.41** (the sign's first frame) to
  W + 3.94 → ♪ uiClick + ◉ win (if not fired yet) → rows 14–15 happen on that frame (dim jumps to 0.90), the strip rows 16–18 follow
  from there. Taps during W … W + 0.41 are ignored (protects against a double tap on the last arrow; DECISION).
- The **Rocket Race bar** replaces the Streak strip while a race is joined: same slide (row 16); the player's lane counter pops
  1.25 → 1.0 (0.25 s `easeOutBack(1.70)`) at W + 4.34 (DECISION).
- Fail panel ("Level Failed!"): instant; the Streak strip slides up the same way (row 16) with the old multiplier lit, then the lit chip
  slides back to **x1** (row 17 timing). DECISION mirroring the win (fail §1 shows only the end state).
- Whole celebration **silent** (VERIFIED: the unskipped clip is digital zero). No win fanfare (the YT-B fanfare is an older build; the
  recipe in sounds §2.6 stays unused).
- `ui.json`: `win.panelAt 3.94` (anchor W; was 3.36 from the sign), NEW `win.*` beat keys §13.2.

---

## 6 Buttons, popups, overlays, tutorials (S1/S2/S3/SOC2)

### 6.1 Button press (every tappable chrome element: GlossyChrome buttons, nav tabs, popup X, toggles, boosters, event badges, pills)
| # | start | dur | property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | touch-down | 1 frame | scale about the centre | 1.0 → **0.95** | instant | — | VERIFIED (Play 197.5 → 187.5 pt wide; Continue 284.5 → 270) |
| 2 | release inside | 1 frame | scale 0.95 → 1.0; the action | — | instant | ♪ uiClick + ◉ button (same frame) — EXCEPT the win panel's Continue: ◉ button only, no click | VERIFIED click on release; Continue silent VERIFIED; its haptic DECISION |
| 3 | drag out / cancel | 1 frame | scale 0.95 → 1.0, no action | — | instant | — | DECISION |
- `ui.json button.pressScale 0.95` (present). Toggles (Sound/Haptic/Notifications) swap their look in the release frame (no slide).
  The Settings **Music** button: press + click, NO state change (MA2).

### 6.2 Popups and dims
All popups (Pause, Quit Level?, Settings, Out of Time!, Out of Lives!, Continue?, Level Failed, win panel, More Lives, booster buy,
username, edit profile, claims, event offers, Streak Race list, info overlays): **appear complete in one frame, disappear in one
frame**; the dim reaches its alpha in the same frame (`ui.json popup.dimFadeIn 0`). Dims: `dim.popup 0.90`, `dim.unlock 0.90`,
`dim.outOfTime 0.94`, `dim.skyMatch 0.96` (VERIFIED uim). Idle popups are static (Out of Time held 9.5 s with identical frames,
VERIFIED). A popup shown while another is up replaces or stacks per the host (arch §6.6). Silent except the button clicks.

### 6.3 Feature unlock overlay (G2 `UnlockDirector`, S2 `UnlockOverlay`) — anchor S = the Play release (V1 L7: 76.42)
VERIFIED tutorials §6 (V1 25 fps; V2 and phone Pipe card identical layout). Frames from `uim unlock`.
| # | start (S +) | dur | element · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | 0.02 | 1 frame | the level cut in underneath (row 8) + dim 0.90 over it | — | — | ♪ unlockChime (on this frame) | VERIFIED dim; chime "with the dark overlay, ≈ 0.2 s before the icon" |
| 2 | 0.26 | 0.28 | icon · scale | 0 → 1.3 (at +0.16) → 1.0 | kf, `easeOut` segments | — | VERIFIED |
| 3 | 0.50 | 0.16 | title "<Name>!" · scale | 0.2 → 1.15 (+0.12) → 1.0 | kf | — | VERIFIED |
| 4 | 0.62 | 0.08 | "Unlocked!" · scale | 0.2 → 1.0 | `easeOutBack(1.70)` | — | VERIFIED |
| 5 | 0.78 | 0.16 | card · scale | 0.2 → 1.12 (+0.12) → 1.0 | kf | — | VERIFIED |
| 6 | 1.14 → dismiss | loop | twinkles around the icon (§10 `unlockTwinkles`) | — | — | — | VERIFIED "sparkles twinkle until dismissed" |
| 7 | tap anywhere (accepted from S + 0.94, when the card has settled) | 0.16 | whole overlay · opacity | 1 → 0 | lin | ♪ uiClick | VERIFIED fade ≈ 0.16 s; accept-from DECISION (V1 min 1.9 s observed) |
| 8 | 0.02 (= K) | — | the level intro (§3.6 rows 2–11: zoom, draw-in, HUD drop, pops) runs UNDERNEATH the overlay; input opens at max(dismiss, K + 1.015); the timer stays frozen until the first tap | — | — | — | VERIFIED ("the board and the HUD show faintly through it"; after the dismiss the board is ready at 3:00) |
- `ui.json unlock.*`: icon **0.26**, iconSettle **0.54**, title **0.50**, unlocked **0.62**, card **0.78**, sparkles **1.14**,
  dismissFade **0.16**, NEW `unlock.acceptFrom 0.94` (values from tutorials §6 replace the pass-1 0.24/0.40/0.52/0.60/0.76/1.1/0.25).

### 6.4 "Tap to move!" (G2 `TutorialDirector`, S2 `TutorialLayer`) — anchor = the stage-1 board's first frame (V1 0.44)
VERIFIED tutorials §3 (25 fps). Caption **"Tap to move!"** (TR **"Hareket ettirmek için dokun!"**), navy #121B51, ≈ 40 pt
PCDisplay-Black, centre (195.5, 289); hand fingertip at the free middle arrow's upper-middle (38 % down its length).
| # | start | dur | element · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| 1 | +0.36 | 0.20 | caption · scale | `Curves.captionPop` (0.7 → 1.10 → 1.0) | kf | — | VERIFIED |
| 2 | +0.36 | 0.28 | hand · scale about the fingertip | 0.24 → 1.0 | `easeOutCubic` | — | VERIFIED |
| 3 | +0.64 | loop 2.10 | hand · scale about the fingertip (its shadow scales with it) | hold 1.0 (0.28 first, then 1.26) → 0.53 (0.48 s `easeInOut`) → 1.0 (0.36 s `easeOutQuad`) | `Curves.handLoop` | — | VERIFIED one cycle (first press at +0.56 after the hand appears); period INFERRED |
| 4 | the first accepted tap (any arrow) | 0.16 | caption · scale | 1.0 → 0 | `easeInQuad` | (◉ tap of the exit) | VERIFIED |
| 5 | same | 0.12 | hand · opacity (no scale) | 1 → 0 | lin | — | VERIFIED |
- No dim, no spotlight, no input restriction (VERIFIED/INFERRED tutorials §3). Never shown again (`tutorialsDone`).

### 6.5 Weekly Contest tutorial and the info overlays (SOC2) — anchor S
VERIFIED S1-weekly-contest-open: dim to ≈ 10 % brightness in ONE frame (`dim.popup`), then staggered pops:
| element | start (S +) | pop | tag |
|---|---|---|---|
| title "Weekly Contest" | 0.18 | `Curves.pop(0.10, 1.10)` | VERIFIED |
| maze icon card "Beat Levels!" | 0.35 / 0.58 | `pop(0.16, 1.12)` each | VERIFIED |
| pointer arrow | 0.72 | `pop(0.16, 1.12)`, then bobs 8 pt along its direction, period 0.9 s `easeInOutSine` | pop VERIFIED; bob DECISION |
| podium | 0.88 | `pop(0.25, 1.08)` | VERIFIED "grows ≈ 0.25 s" |
| "Tap to Continue" | 1.10 | opacity 0 → 1, 0.15 s, then static | DECISION |
- The same stagger (title +0.18, rows +0.35/+0.58/+0.72/+0.88 in reading order, "Tap to Continue" +1.10) is used for the Claw (i),
  Streak Race (i), Rocket Race tutorial, Sky Jump tutorial and Weekly (i) overlays (DECISION; not captured, clips-needed #23).
- The forced Weekly step (the yellow arrow pointing DOWN at the trophy tab): dim instant, card instant, arrow `pop(0.16, 1.12)` then
  the 8 pt bob. The trophy tab stays live (input restricted). Dismiss/tap: ♪ uiClick.

### 6.6 Claims ("Congratulations! … Tap to Claim"), toasts
- Claim popup: instant; the reward icon `pop(0.30, 1.15)` at S + 0.10; `sunburstRays` behind it rotate 20°/s (continuous); "Tap to
  Claim" static. Tap: ♪ uiClick; the reward is applied at once (∞ lives: the lives pill shows ∞ on return; coins: the home coin
  segment C of §8.3 with the claimed amount). DECISION (never clipped).
- Toast (S1): in 0.08 s fade, hold 2.0 s, out 0.27 s (`ui.json toast.*`, S1 DECISION accepted).

---

## 7 Shell transitions (S1 `Transitions`)
| transition | motion | tag |
|---|---|---|
| launch → Loading | the launch-screen colour, then Loading on the first frame | arch |
| Loading idle | only the dots animate: "Loading" → "Loading." → "Loading.." → "Loading..." cycle, **0.40 s** per step (text swap) | dots VERIFIED; period DECISION (the F00 clip freezes under the iOS alert) |
| Loading → first board (fresh install) | cross-fade **0.13 s** lin, the HUD already in place (§3.6 FTUE) | VERIFIED 0.1–0.16 s |
| Loading → home | cross-fade 0.16 s lin | DECISION (same family) |
| home → level (Play) | hard cut ≤ 0.05 s after release, then §3.6 | VERIFIED cut |
| win panel Continue → next FTUE level | hard cut, then §3.6 (HUD intro included) | VERIFIED V1 28.34 |
| win panel Continue → home | hard cut ≤ 0.05 s after release (original ≈ 0.10 s after touch-down), then §8.3 | VERIFIED |
| Level Failed X → home; Try Again → level | hard cut; Try Again → §3.6 | VERIFIED cut; intro on retry DECISION |
| home tabs (shop · home · leaderboard) | instant page swap; the raised-tab highlight moves instantly | DECISION (not captured; consistent with instant popups; SPEC-ui may override) |
| home → event screen / Profile | instant (full-screen popup family) | DECISION |
- `ui.json transition.loadingToBoard 0.13`, `transition.loadingToHome 0.16`, `transition.homeTabs 0`, `loading.dotsPeriod 0.40`.

---

## 8 Home (S1/S3)

### 8.1 Static things (VERIFIED META-home-idle-12s, 15 s, 911 samples)
The Play button (no pulse), the capsule machine and its arrow pile, the background pipes and the platform are **static** (mean frame
difference < 0.1). The lives pill counts down every second (text swap); badge timers swap text. Tapping the scientist does nothing.
Everything silent (Music OFF on the owner's device; no loop exists, MA2).

### 8.2 Character rigs (S1 `PuppetStage`/`PuppetRig`; rigs `art/out/char_*_rig/rig.json`)
Rules (all DECISION except the periods): every loop is ONE set of repeating `CAKeyframeAnimation`s whose duration = the rig's
**cycle** (so the whole character repeats exactly at the measured period); keyframes start and end at the rest pose (the full render);
group swaps (`eyes`, `body`, `head`, `armR`) are `.discrete` keyframes on the members' `opacity`; a "whole" transform (all layers as
one sublayer tree) carries sway/tilt about the `feet` pivot so eyes, glasses and arms follow the body. Rotations in degrees, positive
= clockwise on screen. Times are fractions of the cycle ×  cycle seconds, given in seconds. Capture mode holds the rest pose (arch).

**Scientist** `char_sci_home_rig` — **cycle 3.16 s** (VERIFIED period; "breathing / blinking / head tilt, small, continuous"):
| part (pivot) | property | keyframes (s → value) | curve |
|---|---|---|---|
| torso (bottom-centre 95.3, 164) | scale Y | 0 → 1.000, 1.58 → 1.012, 3.16 → 1.000 | `easeInOutSine` |
| head group (neck 94.95, 70.81) | translate Y · rotation | follows the breathe: 0 → 0, 1.58 → −0.8 pt, 3.16 → 0 · 0 → 0°, 0.79 → +1.6°, 2.37 → −0.6°, 3.16 → 0° | `easeInOutSine` |
| armL, armR (shoulders 49.22, 86.31 / 141.42, 92.97) | rotation | 0 → 0°, 1.58 → −1.2° / +1.2°, 3.16 → 0° | `easeInOutSine` |
| lids (overlays) | discrete | 0–2.10 none; 2.10 lidsHalf; 2.15 lidsClosed; 2.25 lidsHalf; 2.30 none | discrete |
- `headOpen` / `armR_point` are not used in the idle loop (store poses; free for event screens).

**Right worker** `char_wk_homeR_blue_rig` (glasses, clipboard) — **cycle 10.2 s** (VERIFIED period; "writes, looks up, nods"):
| part (pivot) | property | keyframes (s → value) | curve |
|---|---|---|---|
| whole (feet 73.67, 122.52) | rotation (sway) | ±1.0°, period 2.55 s (4 per cycle), phase 0 | `easeInOutSine` |
| whole | rotation (look-up / nod, added) | 0–4.0 → 0°; 4.0 → 4.4: 0 → −3.0° (looks up); hold to 6.4; 6.4 → 6.7: +2.0°; 6.7 → 7.0: −1.0°; 7.0 → 7.3: +2.0°; 7.3 → 7.6: −1.0° (two nods); 7.6 → 8.0: → 0° | `easeInOut` per segment |
| armR = pencil arm (shoulder 105.62, 68.65) | rotation (writing scribble) | 0–4.0 and 8.0–10.2: ±6° at period 0.40 s; 4.0–8.0: 0° | `easeInOutSine` |
| armL = clipboard arm (shoulder 44.49, 67.56) | rotation | 0–4.0: −2°; 4.0 → 4.4 → +3° (lifts the board as it looks up); 7.6 → 8.0 → −2° | `easeInOut` |
| eyes group | discrete | default `eyes_half` (looking down); 4.2 `eyes_open`; 5.40 `eyes_closed`; 5.55 `eyes_open`; 7.8 `eyes_half` | discrete |
| body group | discrete | default `body_smile`; 4.4 `body_open`; 4.8 `body_smile` (a small "oh") | discrete |

**Left worker** `char_wk_homeL_blue_rig` (walkie-talkie) — **cycle 17.3 s** (VERIFIED "no repeat inside 15 s"; 17.3 DECISION):
| part (pivot) | property | keyframes (s → value) | curve |
|---|---|---|---|
| whole (feet 67.7, 122.52) | rotation (sway) | ±1.5°, period 17.3/7 = 2.471 s | `easeInOutSine` |
| body group (talking = mouth flaps) | discrete | talk windows 0.0–1.6, 4.0–6.0, 9.0–10.5, 15.5–16.5: `body_open`/`body_smile` alternating every 0.14 s; otherwise `body_open` (default) — outside talk windows the mouth stays as rendered | discrete |
| armR = walkie arm (shoulder 97.0, 66.5) | rotation | talk windows: −4° (raised to the mouth), else 0°, 0.20 s transitions | `easeInOut` |
| whole | rotation (think, added) | 2.2 → 2.5: → −2.5°, hold to 3.4, → 0 by 3.7; 11.0 → 11.3 → −2.5°, hold to 12.2, → 0 by 12.5 | `easeInOut` |
| eyes group | discrete | think windows `eyes_half`; 3.70 `eyes_closed` → 3.95 `eyes_open` (the "wink": a slow closed-eyes beat; a one-eye member is a UI-ART request, §15.4); blinks 8.00–8.15 and 14.20–14.35 (`eyes_half` 0.04, `eyes_closed` 0.07, `eyes_half` 0.04) | discrete |
| armL = free arm (shoulder 35.47, 69.76) | rotation (wave) | 6.0 → 6.3: 0 → −25°; 6.3 → 6.6: → −5°; 6.6 → 6.9: → −25°; 6.9 → 7.2: → 0; same at 12.5–13.7 | `easeInOut` |
- `ui.json puppet` becomes per rig (§13.2): `puppet.<rig>.cycle` + the tables above as keyframe arrays; S1's shared
  `workerSway*`/`sciNod*` knobs are superseded (request §15.3). Zero main-thread work at rest (render-server animations).

### 8.3 The home-return queue after a win (G2 `EventsDirector` + S3 `PayoutSequence`/`ClawBar`/`CoinFly`) — anchor H
VERIFIED S1-L50-win-seq-2-continue (v552, 60 Hz sheets + audio; clip cut at 4.709 → the last coin landing and the cue tail are
extrapolated). Segments play in this order, back to back; a segment is skipped when its event is not active (MA11). After the queue:
the event popups/claims queue (social §4.8) and the rating prompt after L34 (arch §6.10).

**Segment A — Claw token** (when the Claw Challenge is active; points gained = the multiplier m before the win). Times from H.
| # | start (H +) | dur | element · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| A1 | 0.03 | 0.13 | home dim (above the scene, under the token and the top bar) · opacity | 0 → 0.50 black | lin | — | VERIFIED ≈ 50 % 0.20–0.35 |
| A2 | 0.03 | 0.10 | purple hex token `iconHexArrow` (56 pt) at the capsule machine (198, 440) + "+1" label · scale | 0.2 → 1.0 | `easeOutBack(1.70)` | ♪ clawToken at H + 0.055 | VERIFIED |
| A3 | 0.23 | 0.12 | white flash on the token (disc r 30 pt) · opacity | 0 → 0.9 → 0 | kf | — | VERIFIED 0.40 |
| A4 | 0.23 | 0.45 | multiplier badge (xm, orange) at the token's right (+42, −12 pt) · appears, bobs ±3 pt (period 0.15 s), then slides into the token (0.53 → 0.68) | scale 0 → 1 (0.08 s) … position → token centre | `easeInQuad` for the slide | — | VERIFIED 0.40 → 0.85 |
| A5 | 0.68 | 0.18 | white burst (sparkle ring r 0 → 45 pt, 10 `sparkleTwinkle`s) | — | `easeOutQuad` | ♪ clawMerge at H + 0.635 | VERIFIED burst 0.85 |
| A6 | 0.88 | 1 frame | label "+1" → "+m" | — | — | — | VERIFIED 1.05 |
| A7 | 1.33 | 0.20 | home dim · opacity | 0.50 → 0 | lin | — | VERIFIED 1.5–1.7 |
| A8 | 1.43 | 0.30 | token · arc to the Claw bar's hex icon (49, 128) · scale | control point (180, 180) · 1.0 → 0.65; label fades out 0.10 s | `easeInQuad` | — | VERIFIED 1.6 → 1.9 |
| A9 | 1.73 | 0.12 | flash on the bar icon | 0 → 1 → 0 | kf | — | VERIFIED (flash visible at clip 1.997 = H + 1.83, 0.1 s sampling; the count-up already runs) |
| A10 | **1.74** | n × 0.057 | Claw bar number + green fill count up (§8.5): n = min(7, m) steps | old → old + m | steps | ♪ clawTick at H + 1.74 + 0.057·k (k = 0…n−1) | VERIFIED 7 ticks 1.910 … 2.250 for m = 25 (57 ms mean) |
| A11 | last tick + 0.02 (H + 2.10 for n = 7) | — | end of the count-up; segment A ends 0.01 s later (B0) | — | — | ♪ clawComplete | VERIFIED 2.270 |
| — | m = x1 | — | A4–A6 are skipped (no badge to merge; "+1" stays); A7 starts at H + 0.60, the rest shifts by −0.73 s | | | | DECISION |

**Segment B — Streak strip** (when the Streak Race is active). Times from B0 = the end of A (H + 2.11 for n = 7), or H + 0.10 without A.
| # | start (B0 +) | dur | element · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| B1 | 0.00 | 0.22 | chip tray x1 x5 x10 x25 x100 (`home.clawMultTray`) slides out rightwards from behind the multiplier badge, previous chip lit | clip width 0 → full | `easeOutCubic` | — | VERIFIED 2.28 → 2.5 |
| B2 | 0.02 | 0.10 | green flag-roll icon (`iconCheckeredFlag` variant) + "+m" at (133, 232) · scale | 0.2 → 1.0 | `easeOutBack(1.70)` | — | VERIFIED 2.3 (P3 sheet) |
| B3 | 0.57 | 0.17 | flag icon · arc to the Streak badge (49, 231), apex 50 pt above · scale | 1.0 → 0.5; the "+m" label fades 0.2 s in place | `easeInQuad` | — | VERIFIED 2.85 → 3.02 (P3) |
| B4 | 0.72 | 0.10 | lit chip (tray) · x | previous → new multiplier | `easeInOut` | ♪ streakPop at B0 + 0.77 | VERIFIED 3.0 → 3.08; pop 3.050 |
| B5 | 0.92 | 0.15 | sparkle on the new chip | — | — | ♪ streakPop at B0 + 0.92 | VERIFIED pop 3.200 |
| B6 | 1.20 | 0.15 | flash on the Claw multiplier badge + its label → the new multiplier (instant swap under the flash) | — | — | ♪ streakPop at B0 + 1.14 | VERIFIED 3.42 (pop) / 3.48 (flash) |
| B7 | 1.99 | 0.18 | chip tray retracts leftwards | full → 0 | `easeInQuad` | — | VERIFIED 4.29 → 4.45 (P3 sheet; motion.md's 3.6–4.0 is corrected) |
- Coin segment C starts at **C0 = B0 + 1.25** after segment B (its coins lift at B0 + 1.80, overlapping B7); at **A-end + 0.40** when
  only A ran; at **H + 0.35** when A and B are both skipped (the plain payout and the FTUE first home; 0.35 so the coin cue, which
  starts 0.35 s before C0, starts on the cut).

**Segment C — coin payout** (every win; the FTUE first home pays the banked 80 + 20 + 20 = 120). Times from C0.
| # | start (C0 +) | dur | element · property | from → to | easing | cue | tag |
|---|---|---|---|---|---|---|---|
| C1 | 0.00 | 0.25 | "+N" label (GameText 30 pt, white face, dark outline #0B2A7A) + a small coin pile (`coinPileSmall`) over the capsule machine at (196, 490) · scale | 0.3 → 1.1 → 1.0 | `easeOutBack(1.70)` | — | VERIFIED V1 (+0.25 after the cut; ours +0.35 when alone) |
| C2 | 0.55 + 0.22 − 1.12 = **−0.35** | 2.9 | coin glitter swell with 5 baked clinks (the cue is scheduled 1.12 s before the first landing, so its clinks fall on the landings) | — | — | ♪ coinCollect at C0 − 0.35 | VERIFIED swell 1.12 s before the first clink |
| C3 | 0.55 + 0.085·k (k = 0…4) | 0.22 each | coin k (`iconCoin` 30 pt) · position on a quadratic Bézier from (196, 490) with control (196, 180) to the home coin icon (112.7, 70) · scale | 1.0 → 0.85 | `easeInQuad` | — | VERIFIED 5 coins, first lift 4.08, arrivals ≈ 0.085–0.10 s apart, flight ≈ 0.21 s |
| C4 | 0.77 + 0.085·k | 1 frame | coin pill number += N/5 (the remainder on the last coin); sparkle burst on the coin icon (§10 `pillSparkle`) | — | — | ◉ coinLand (clinks are inside ♪ coinCollect) | VERIFIED (3854 → 3858 → … → 3874; 1000 → 1024 … 1120) |
| C5 | 1.12 | 0.20 | "+N" label + pile · opacity | 1 → 0 | lin | — | DECISION |
- Order evidence (clip times, B0 = 2.28): C0 = 3.53; the coins lift at C0 + 0.55 = 4.08 ✓, the glitter at C0 − 0.35 = 3.18 ✓, the
  first clink at C0 + 0.77 = 4.30 ✓, counter steps 4.29 … 4.69 ✓. V1 first home (H = 73.64): label +0.25, lift +0.80, landings
  +1.08 … +1.40 — ours +0.35, +0.90, +1.12 … +1.46 (≤ 0.1 s later, so the baked clinks stay in sync).
- `ui.json homeReturn.*` holds every start/duration above (§13.2).

### 8.4 Coin fly anywhere else
Claim popups that grant coins and the Sky Jump/Rocket Race/Weekly prizes use segment C (C0 = the claim popup's close). Shop purchases
(FakeStore): the pill number swaps instantly + one `pillSparkle` (DECISION).

### 8.5 Claw bar count-up (S3 `ClawBar`)
- Steps: n = min(7, Δ); each step (every **0.057 s**) the number shows `old + round(Δ·k/n)` and the green fill (`home.clawBarFill`)
  animates to the matching width in 0.057 s (lin). VERIFIED 7 ticks for +25 (156 → 167 → 173 → 179 → 181 read at 0.1 s); n for other
  Δ DECISION. ♪ clawTick per step, ♪ clawComplete at the last step's end.
- Reaching the step target: the fill flashes white (0.15 s), then (0.20 s later) shows the overflow against the next target (instant);
  the reward claim popup joins the post-home queue. DECISION (never clipped).
- The multiplier badge: instant label swap under a 0.15 s white flash (B6).

---

## 9 Event and social screens (SOC2) — all DECISION unless marked (clips-needed #23 open)
| screen | motion | tag |
|---|---|---|
| Leaderboard tabs Weekly / World / Country | instant content swap; Country opens already scrolled so the player's row is centred (no scroll animation); "Top" pill → animated scroll to rank 1 (`setContentOffset(animated:)`, native ≈ 0.3 s); World "Bottom" pill → load the next page then animated scroll | "opens auto-scrolled" VERIFIED V2; animations DECISION |
| live updates (every 5 s while visible, social §3.4) | a changed value counts up in 0.30 s `easeOutQuad` (integer steps each frame); rows that change order slide to their new slots in 0.35 s `easeInOut`; the player's rank label counts in 0.30 s; never animate backwards | social §3.4 |
| Weekly podium | static; values update like rows | DECISION |
| Claw Challenge screen, first open | the ladder auto-scrolls from step 1 (bottom) to step 20 (top) in 1.8 s `easeInOutSine`, then stays; later opens: scrolled so the current step is centred, no animation | auto-scroll VERIFIED flows; timing DECISION |
| Streak Race list (auto-shown or badge) | instant popup; rows static; live updates as leaderboards | VERIFIED instant family |
| Sky Jump "Finding players on your level." | the counter counts 29 → 100 in 1.5 s `easeOutQuad`; 14 portraits pop into the fan one by one (`pop(0.16, 1.12)`, stagger 0.10 s from S + 0.10); "Tap to Continue" at the end | counter VERIFIED values; timing social §4.6 |
| Sky Jump map progress (after each first-try win) | the player's portrait hops to the next pad: arc 0.50 s (`easeInOut`, apex 60 pt), landing squash scale Y 1 → 0.85 → 1 (0.12 s); "Players" counts down in 0.60 s; rivals that drop fade 0.25 s | "avatar hopping, Players dropping" VERIFIED stills; timing DECISION |
| Sky Jump win | "You win!" coin plate counts up from 0 to the share in 1.0 s `easeOutQuad`; winners' portraits pop (stagger 0.08 s); then the claim (§6.6) | count-up VERIFIED (367 → 714 caught mid-count) |
| Rocket Race lanes | on open and on each update the rockets rise to their progress positions in 0.60 s `easeInOut`; the n/5 bubble pops `pop(0.20, 1.2)` when it changes; the gold winged "1" badge moves to the leader in 0.30 s | DECISION |
| Rocket Race result | winner's lane card with the gold badge + chest `pop(0.30, 1.12)`; text instant | DECISION |
| Weekly result / Streak result (social §10 NEW screens) | instant popup; rank badge `pop(0.30, 1.15)`; coin plate counts up 0.8 s | DECISION |
| trophy tab "!" badge | appears with `pop(0.20, 1.2)`; no pulse | DECISION |
- All silent except ♪ uiClick on buttons/taps (VERIFIED: v552 events show no cues besides the home-return ones; clips-needed #23 may add).

---

## 10 Particle specifications
Screen-space effects use screen pt; board-space effects use content pt (scale with zoom). "g" = gravity (+y down). Every emitter/pool
is seeded from the `fx` stream (deterministic captures, `-pc.freezeAt`). Pools are allocated at warm-up (arch §5.9).
| effect | count | colours | size | lifetime | velocity (initial) | gravity / drag | spin | space · layer · impl | tag |
|---|---|---|---|---|---|---|---|---|---|
| **trail stars** | 2.4 per cell of tail travel | per painter (§3.2.2) | 0.30 p ± 0.08 | 0.40 s, α 1 → 0 lin, scale 1 → 0.4 | 0 | 0 | ±90°/s, start 0–72° | board · fxRoot · `CAEmitterLayer` per exit (`boardTrailStar`) | VERIFIED rate/size/life; spin DECISION |
| **door shards** | 60 (24 purple #8E3BE0/#6A1FB8, 18 orange #F28A1A/#D9650B, 18 blue #3E8EF0/#2A64C8) | sprite atlas `doorShards` (6 shapes) | 0.25–0.6 p (door-relative) | 0.90 s; α 1 until 0.65 then → 0 | from the door's cells: vy −10…−90 pt/s, vx ±(20…90) pt/s (**FIX-V2 2026-09-27**, S1-L33-key-first 1.68/1.75/1.85/2.00: the pieces hold the door's footprint for ≈ 0.17 s and have dropped ≈ 30 pt by + 0.32 s — the earlier −120…−260 "pop" put them 3 pt ABOVE the door at + 0.32); the look = chunky 3-D pieces with grey drop shadows (blue slat shards inside, orange / purple frame bits at the edge) + the door frame's own ~1-cell pieces and the lock in two halves | g **1000 pt/s²** | ±360°/s | screen · fxRoot shard pool (keyframes, not emitters: arch) | VERIFIED count/colours/timing; g INFERRED; velocities re-fitted FIX-V2 |
| **lock flash** | 1 disc | white | r 0.9 p | 0.216 s kf 0 → 1 → 0 | — | — | — | board · fxRoot | VERIFIED |
| **pipe shards** | 40 cyan (#7FE3FF, #3CC6F2, #B8F2FF) + counter box 2 halves (orange #E86A1A) + 2 gold rims (#F2B620); **FIX-V2: ≈ 4.5 chunky glass shards per tube cell (40 … 130) laid along the tube in order (the phone's double column), grey shadows 0.17 p below; the counter box halves start cracked (0.05 w apart, ±7°)** | `pipeShards` atlas + the counter/rim sprites halved | 0.2–0.5 p; halves as drawn | 1.40 s; α fade from 1.0 s | tube shards: vy −(80…220), vx ±(30…140) pt/s from the tube cells; halves: ±60 pt/s outward, −150 pt/s up; rims: −100 pt/s up | g **1000 pt/s²** | shards ±300°/s; halves/rims ±180°/s (tumble) | screen · fxRoot pool | VERIFIED look/timing (22–55 blobs); g INFERRED |
| **box shards** | 140 purple (#9B44E6, #7A2BC9, #B46BF0, bolt #C79BF5) + 4 silver ring chunks (#C8CCD8); **FIX-V2: a mosaic of chunky 3-D purple chunks (#B858F8 face, #C868F8 / #D888F8 lights, #9848D8 side) at ≈ 0.85 p tiles over the slab (≈ 13 × 4 on L50; the count caps it), grey drop shadows 0.19 p below; the ring breaks into 4 quarters of its own art** | small rounded quads + ring quarter sprites | 0.15–0.35 p (FIX-V2: 0.85-1.05 p looks, ink ≈ 0.7-0.9 of a tile) | 0.67 s; α fade from 0.35 s | laid out over the box area; vx = ±(60…180) pt/s away from the box centre line (bbox 53–340 → 0–393 by +0.34 s), vy 0 (fall from rest) | g **1275 pt/s²** | ±240°/s | screen · fxRoot pool | VERIFIED (centroid +2.5/+18/+44/+67 pt at +0.067/0.167/0.267/0.333) |
| **ripple** | 1 disc per tap (pool 6) | black α 0.294 → 0.02 | r 11 → 22.5 pt | 0.233 s | — | — | — | screen · ScreenFXView | VERIFIED |
| **bump ✖ badge** | 1 | #F62631 / #7A0A10 | 1.0 p | 0.43 s | — | — | — | board · fxRoot | VERIFIED |
| **heart halves** | 2 | heart red #FB3A2A (+ specular #FC8258) | half of 28.7 × 24.4 pt | 0.40 s | vy −115 pt/s, vx ±37.5 pt/s | g **960 pt/s²** | to ±40° | screen · HUD | VERIFIED |
| **confetti** | burst **140** at W+1.47 + rain **45/s** until W+3.94; ≈ 150–180 visible at steady state | 7 colours, equal weights (blue ×1.4): **#1F77F3 · #EB4FB0 · #6A11EF · #D30A20 · #FFB807 · #F8F2DA · #65DD2B** | rounded quads 5–11 pt (median 6.5), aspect 1:1–1:1.6, corner r 1.5 pt | until off-screen (≤ 5 s) | burst: from y 862, x uniform 0–393, speed 900–1500 pt/s within ±12° of vertical; rain: from y −10, x uniform, fall 140–220 pt/s | burst: g 900 pt/s² with drag to a terminal 200 pt/s; rain: constant fall + sway ±20 pt (period 1.2–2 s) | flip 2–5 rev/s (scale-Y cosine) + spin ±180°/s | screen · FXOverlay · 2 `CAEmitterLayer`s (burst: birthRate 1400 for 0.1 s; rain: line emitter along the top) | colours/sizes/count **[P3]** 3 lossless shots (049, 057, 077: 152–183 pieces); motion VERIFIED sheet; speeds DECISION |
| **firework rocket** | 6 (§5 row 12) | white head glow + white trail | head ⌀ 6 pt; trail 60–110 pt tapered | 0.62–0.72 s rise | from y 862, x ∈ {150, 240, 120, 270, 200, 170}; to bursts at (x ± 40, y ∈ 190–330) | decelerating `cb(0.25,0.6,0.4,1)` | — | screen · FXOverlay (CAShapeLayer trail + keyframes) | VERIFIED trails [P3]; placement DECISION |
| **firework burst** | 48 sparks + 1 flash per burst | 40 % white, 15 % each #8D5FFF, #4079FF, #FF2FC6, #FFCE01 | spark streaks 10–18 pt × 1.5 pt; flash disc r 0 → 22 pt | sparks 0.70–0.90 s (α → 0 over the last 0.4); flash 0.18 s | radial 260–420 pt/s | drag e^(−6.3t) + g 180 pt/s² (droop) | streaks align with velocity | screen · FXOverlay (`CAEmitterLayer` burst, birthRate 48/0.02 s) | VERIFIED look (white core + multicolour streaks, r ≈ 120 pt) [P3]; numbers DECISION |
| **unlock twinkles** | continuous: 1 new every 0.18 s, ≤ 6 live | #FFFFFF, #FFF6B0 | `sparkleTwinkle` 10–16 pt | 0.70 s: scale 0 → 1 → 0 (kf 0/0.35/0.70), rotate 0 → 45° | positions uniform in an ellipse 150 × 110 pt around the icon | — | 45° over life | screen · PopupHost overlay | VERIFIED presence; numbers DECISION |
| **pill sparkle** (coin landing) | 7 | #FFFFFF, #FFF6B0, #FFE14A | 9 pt `sparkleTwinkle` | 0.70 s, radial 0 → 22 pt, scale 1 → 0 | radial | — | — | screen · FX (`ui.json fx.sparkles`, S1 values) | VERIFIED presence (V1 "sparkle burst on the coin icon"); numbers S1 DECISION accepted |
| **claw merge burst** | 10 | #FFFFFF, #FFE9A8 | `sparkleTwinkle` 12 pt | 0.30 s, radial 0 → 45 pt | radial | — | — | screen · FX | VERIFIED burst; numbers DECISION |
- Budgets (arch §10): board shards ≤ 200 live, confetti ≤ 260 live, fireworks ≤ 6 × 49; every first use pre-run by the warm-up
  (arch §5.9 step 2 gains: trail stars per painter, door/pipe/box shards, confetti, one firework, heart break, frost vignette, hint
  camera, unlock twinkles, coin fly, puppet loops).

---

## 11 Audio

### 11.1 Verdict (VERIFIED sounds §1 + meta explorer)
v552 is **silent in play**: taps, ripples, exits, stars, combo colours, bumps (slide, red, ✖, vignette, heart break), tape bumps, key
flights, door bursts, pipe passes/shatters, box breaks, the level intro, the timer (incl. its last seconds and 0:00), the Out of Time
popup entrance, the bulb and hourglass effects, the whole win celebration, the win panel and its Streak strip, the home idle, the
Weekly tutorial — every clip's audio is digital zero while the same recorder captures the Play click and the home-return cues. Reviews
agree ("pretty weird playing in complete silence", web §11). **Our build keeps that silence** (MA1, MA3).

### 11.2 Cue list (the SoundIDs; `Tuning/audio.json cues.<moment>`)
| SoundID | trigger (moment key) | frame | gain | bus | tag |
|---|---|---|---|---|---|
| `uiClick` | every UI button **release** (Play, tabs, pills, gear, avatar, badges, Claw bar, pause, back, boosters, Resume, Quit, X, toggles incl. the inert Music button, Try Again, Add Time/Add Lives/Play On/Refill, Start/Join, Save, Continue on popups, "Tap to Continue"/"Tap to Claim", unlock dismiss, the celebration skip-tap) — `cues.uiButton`, `cues.celebrationSkip`, `cues.dismissTap`. **Not** on the win panel's Continue. | the release frame (same frame as the action) | 1.0 | sfx | VERIFIED (Play ×2 = V1 click, corr 0.993); win Continue silent VERIFIED; the list beyond Play/X/pause/resume/unlock/skip = DECISION (same UI family) |
| `unlockChime` | the feature-unlock overlay's first frame — `cues.unlockOverlay` | S + 0.02 | 1.0 | sfx | VERIFIED V1/V2 (5 copies); not met on the phone (no unlock clipped) |
| `clawToken` | segment A2 — `cues.clawToken` | H + 0.055 | 1.0 | sfx | VERIFIED v552 (1) |
| `clawMerge` | segment A5 — `cues.clawMerge` | H + 0.635 | 1.0 | sfx | VERIFIED v552 (1) |
| `clawTick` | each Claw bar count-up step — `cues.clawTick` | step frames | 1.0 | sfx | VERIFIED v552 (run of 7) |
| `clawComplete` | the end of the count-up — `cues.clawComplete` | A11 | 1.0 | sfx | VERIFIED v552 (1) |
| `streakPop` | B4, B5, B6 — `cues.streakPop` | B0 + 0.77 / 0.92 / 1.14 | 1.0 | sfx | VERIFIED v552 (run of 3) |
| `coinCollect` | segment C2 (glitter swell with 5 baked clinks) — `cues.homePayout` | C0 − 0.35 | 1.0 | sfx | VERIFIED v552 = V1 cue |
| `tapTick` | arrow release (the owner's optional tap sound) — `cues.arrowTap` = **""** (unmapped) | R | 0.6 | sfx | DECISION MA3 (rendered, never played by default) |
| (none) | in-level events, celebration, win panel Continue, home idle, event screens | — | — | — | VERIFIED silent |
- A sound fires on the frame of its visual event (arch §8.2): `play()` = `scheduleBuffer(at: nil)` inside the same handler, before the
  CA commit. Overlapping cues use separate voices (8-voice round robin; the 7 ticks + 3 pops + coin cue never exceed 3 at once).
- `clawToken`, `clawMerge`, `clawTick`, `clawComplete`, `streakPop` and `coinCollect` are the **home** cues: they play only on the home
  screen (never under a popup that hides the home).

### 11.3 Synthesis recipes (A1: paste into `tools/audio/specs.py SFX` and `tools/audio/sfx.py RECIPES`)
Our own maths only; nothing is read from `research/sound-refs/` (check.py enforces it). Levels are the measured v552 sample peaks,
clamped to ≤ −1.5 dBFS (the phone capture of the clinks clipped at 0 dBFS). Mono 44.1 kHz 16-bit.

```python
# tools/audio/specs.py — SFX: id: (spec cue, length s, peak dBFS, tag)
SFX = {
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
LOOPS, CHAINS, VARIANTS, SIZED = set(), {}, {}, {}
MUSIC = {}          # music = none (MA2); see §11.5 for the MusicID cases
COIN_CLINKS_S = [1.120, 1.205, 1.290, 1.375, 1.460]   # = the §8.3 C4 landings relative to the cue start (C0 - 0.35)
```

```python
# tools/audio/sfx.py — recipes (helpers from sfx.py/dsp.py; every random draw from dsp.rng_for(sid, part, v))
def r_ui_click(sid, v=1):
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "noise", v)
    f = dsp.glide_exp(390.0, 300.0, 0.015, n)                        # soft low "tock": body 300-390 Hz (v552 peak ~345-352)
    body = dsp.osc_sin(f, n) * dsp.env_exp(n, attack=0.001, tau=0.010)   # ~20 ms above -20 dB (v552: 20 ms)
    body += db2a(-12.0) * dsp.osc_sin(2.02 * f, n) * dsp.env_exp(n, attack=0.001, tau=0.004)
    click = nrm(dsp.spectral_band(n, rng, 1800.0, 3000.0), 0.5) * dsp.env_ahr(n, 0.0005, 0.001, 0.0015)
    return finish(sid, body + db2a(-4.0) * click, fout=0.004)        # a bright 3 ms transient over the low "tock" (class of the original)

def r_unlock_chime(sid, v=1):
    n = n_of(specs.SFX[sid][1]); y = np.zeros(n)
    y += dsp.osc_sin(dsp.glide_exp(90.0, 60.0, 0.12, n), n) * dsp.env_exp(n, 0.005, 0.30)          # low C2-ish thump
    for f, at, g in ((1046.5, 0.10, 0.0), (1318.5, 0.50, -2.0), (1568.0, 1.10, -3.0), (1975.5, 1.10, -4.0), (2637.0, 0.60, -14.0)):
        b = dsp.fm_bell(f, n_of(1.9), ratio=3.5, index0=1.2, index1=0.3, index_tau=0.25, attack=0.004, tau=0.55)
        dsp.place(y, b, at, db2a(g - 16.0))                                                          # Cmaj7 shimmer at a -16 dB plateau
    return finish(sid, y, fout=0.25)

def r_claw_token(sid, v=1):
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "shimmer", v)
    sh = nrm(dsp.spectral_band(n, rng, 4000.0, 10000.0), 0.3) * dsp.env_exp(n, 0.030, 0.15)
    bell = (dsp.osc_sin(1047.0, n) + db2a(-14.0) * dsp.osc_sin(2.76 * 1047.0, n)) * dsp.env_exp(n, 0.005, 0.25)
    body = nrm(dsp.spectral_band(n, rng, 330.0, 430.0), 0.3) * dsp.env_ahr(n, 0.15, 0.10, 0.35, delay=0.20)
    return finish(sid, db2a(-12.0) * sh + bell + db2a(-18.0) * body, fout=0.05)

def r_claw_merge(sid, v=1):
    n = n_of(specs.SFX[sid][1]); y = np.zeros(n)
    y += dsp.osc_sin(dsp.glide_exp(290.0, 210.0, 0.07, n), n) * dsp.env_exp(n, 0.002, 0.025)       # thump C#4 -> A3
    for f in (1109.0, 1397.0):                                                                       # C#6 + F6 tinkle
        dsp.place(y, dsp.osc_sin(f, n_of(1.1)) * dsp.env_exp(n_of(1.1), 0.003, 0.15), 0.015, db2a(-6.0))
    dsp.place(y, dsp.osc_sin(4100.0, n_of(0.3)) * dsp.env_exp(n_of(0.3), 0.001, 0.06), 0.015, db2a(-12.0))
    return finish(sid, y, fout=0.2)

def r_claw_tick(sid, v=1):
    n = n_of(specs.SFX[sid][1])
    sq = dsp.lp(dsp.osc_square(700.0, n), 6000.0, order=2)                                           # buzzy F5 tick, odd harmonics
    return finish(sid, sq * dsp.env_exp(n, 0.001, 0.010), fout=0.006)

def r_claw_complete(sid, v=1):
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "click", v)
    tone = dsp.osc_sin(dsp.glide_exp(380.0, 355.0, 0.12, n), n) * dsp.env_exp(n, 0.003, 0.040)       # F#4 thunk, slight fall
    click = nrm(dsp.white(n, rng), 0.3) * dsp.env_ahr(n, 0.0002, 0.0005, 0.0005)
    return finish(sid, tone + db2a(-14.0) * click, fout=0.03)

def r_streak_pop(sid, v=1):
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "sparkle", v)
    bloop = dsp.osc_sin(dsp.glide_exp(600.0, 370.0, 0.06, n), n) * dsp.env_exp(n, 0.002, 0.05)       # D5 -> F#4 "bloop"
    sp = nrm(dsp.spectral_band(n, rng, 6500.0, 10000.0), 0.3) * dsp.env_exp(n, 0.002, 0.08, delay=0.01)
    return finish(sid, bloop + db2a(-10.0) * sp, fout=0.03)          # one file for all three pops (v552: pops 2-3 carry the sparkle)

def r_coin_collect(sid, v=1):
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "glitter", v); y = np.zeros(n)
    g = np.zeros(n)                                                                                  # (a) glitter grains
    ats = np.arange(0.0, 2.5, 1.0 / 30.0)
    for at in ats + rng.uniform(0, 1.0 / 30.0, len(ats)):
        f = rng.uniform(5500.0, 7500.0); k = n_of(0.025)
        dsp.place(g, dsp.osc_sin(f, k) * np.hanning(k), float(at), rng.uniform(0.5, 1.0))
    y += db2a(-28.0 + 18.0) * g * dsp.env_ahr(n, 0.15, 0.85, 1.50)
    for f in (3140.0, 9300.0):                                                                       # (b) soft early bell pair
        dsp.place(y, dsp.osc_sin(f, n_of(0.6)) * dsp.env_exp(n_of(0.6), 0.004, 0.15), 0.15, db2a(-12.0))
    for at in specs.COIN_CLINKS_S:                                                                   # (c) one clink per landing coin
        k = n_of(1.4); f1 = 3150.0
        clink = (dsp.osc_sin(f1, k) * dsp.env_exp(k, 0.002, 0.25)
                 + 0.6 * dsp.osc_sin(2.96 * f1, k) * dsp.env_exp(k, 0.002, 0.08)
                 + 0.25 * dsp.osc_sin(1.65 * f1, k) * dsp.env_exp(k, 0.002, 0.08))
        dsp.place(y, clink, at)
    return finish(sid, y, fout=0.2)

def r_tap_tick(sid, v=1):
    n = n_of(specs.SFX[sid][1]); rng = dsp.rng_for(sid, "n", v)
    body = dsp.osc_sin(dsp.glide_exp(1400.0, 1100.0, 0.008, n), n) * dsp.env_exp(n, 0.0005, 0.004)
    tick = nrm(dsp.spectral_band(n, rng, 3000.0, 6000.0), 0.4) * dsp.env_ahr(n, 0.0002, 0.0008, 0.0008)
    return finish(sid, body + db2a(-8.0) * tick, fout=0.004)

RECIPES.update({"uiClick": r_ui_click, "unlockChime": r_unlock_chime, "clawToken": r_claw_token, "clawMerge": r_claw_merge,
                "clawTick": r_claw_tick, "clawComplete": r_claw_complete, "streakPop": r_streak_pop,
                "coinCollect": r_coin_collect, "tapTick": r_tap_tick})
```
- If the contract request (§15.1) is refused, render only the 4 existing ids (`uiClick`, `coinCollect`, `unlockChime`, `tapTick`);
  the home segments A/B stay silent (their visuals unchanged).

### 11.4 Engine, buses, gains (A2; `Tuning/audio.json`)
- `AVAudioSession .ambient` (mixes with the user's music, obeys the silent switch), `engine.ioBuffer 0.005`, 8 voices, engine started at
  boot and never stopped in play (arch §7.1). Latency logged at boot.
- Buses: `sfx` (every cue) at output volume 1.0 (Sound ON) / 0 (OFF); `music` exists, stays silent (no files, no decks started).
- Gains: every `gain.<id>` = 1.0 except `gain.tapTick` 0.6 (files are mastered at their target peaks; relative loudness = v552's:
  the home cues ≈ 5–6 dB above the click).
- Default settings (fresh install): **Sound ON, Music OFF, Haptic ON, Notifications ON** (the owner's and V2's state; INFERRED defaults).

### 11.5 Music (MA2)
DECISION: **none**. Evidence: the Music button is inert on v552 (4 attempts), both captured devices show Music OFF, no recording of
any build contains a loop. `audio.json music.enabled = false`. The contract's `MusicID` cases (`home`, `level`) stay (a case-less
Swift enum cannot keep its `String` raw type) but nothing is rendered or played: **A1 changes its own tools** so that
`music.py`/`check.py` skip every `MusicID` while `Tuning/audio.json music.enabled` is false (check.py currently fails on a missing
`Music/<id>.wav`). `playMusic`/`stopMusic` are no-ops when disabled.

### 11.6 Checker assertions (A1 `tools/audio/check.py`, replacing sounds §5.4)
uiClick 25–40 ms, peak −7.5 ±1.5 dBFS; coinCollect 2.9 s ±5 %, exactly 5 clink onsets at `COIN_CLINKS_S` ±5 ms (onset = 3.15 kHz band
envelope), glitter onset at 0 ±20 ms; clawTick ≤ 45 ms; streakPop 0.18 s; unlockChime 2.2 ±0.1 s with a 1047 Hz partial present
from 0.10 s; no file under `research/sound-refs` is opened (existing guard); every SoundID in the contract has its file and no extra
file exists. App-side (A3 SoundBoard + a UI test): zero `play()` calls during a scripted level, the intro and the celebration.

---

## 12 Haptics (A2 `Haptics`; `Tuning/audio.json haptics.<case>`)

### 12.1 The map (every row DECISION: vibration cannot be recorded; the owner's phone has Haptic ON)
| Haptic case | event · frame | generator (style) | intensity | why |
|---|---|---|---|---|
| `tap` | an arrow tap accepted (exit or bump) · R, same handler as the ripple and the mover | `UIImpactFeedbackGenerator(.rigid)` | **0.70** | "that click feeling" (owner 03:00): `.rigid` is the shortest, crispest Taptic impulse — a click, not a thud; 0.70 keeps fast streaks (≥ 4 taps/s) distinct and leaves headroom for the mistake/burst signals |
| `heartLost` (NEW) | bump contact that costs a heart · C | `UINotificationFeedbackGenerator.notificationOccurred(.error)` | — | the owner's "heart loss"; its first pulse lands on the contact frame and the pattern (~0.3 s) spans the heart-break animation 0–0.40 s |
| `bumpContact` | bump contact that costs NO heart (re-bump of a red arrow) · C | `UIImpactFeedbackGenerator(.heavy)` | **0.85** | the owner's "heavy bump": a dull thud distinct from the tap tick |
| `fail` | Out of Time! / Out of Lives! popup · S | `UINotificationFeedbackGenerator(.warning)` | — | a warning, not an error: an offer follows |
| `clear` | board cleared (each stage's W, incl. "Levels 1-4" stages) · W | `UIImpactFeedbackGenerator(.medium)` | **0.80** | marks the moment the wave starts, before the celebration |
| `win` | the OUT! slam (W + 1.64) or the skip-tap, whichever first · once per win | `UINotificationFeedbackGenerator(.success)` | — | the owner's "win" |
| `burst` | door burst, pipe shatter, box break (replaces `tap` on the box-break tap frame) | `UIImpactFeedbackGenerator(.medium)` | **0.65** | an obstacle "gives way": firmer than a tap, softer than the clear |
| `button` (NEW) | every UI button release with the click (§6.1) | `UIImpactFeedbackGenerator(.light)` | **0.50** | the click feeling on the chrome too, subtle enough for menus |
| `booster` (NEW) | booster use (bulb camera start / hourglass spawn) · B | `UIImpactFeedbackGenerator(.medium)` | **0.60** | confirms a spent booster |
| `coinLand` (NEW) | each coin landing on the pill (5 × 85 ms) | `UIImpactFeedbackGenerator(.soft)` | **0.45** | a light rattle under the clinks |
- No haptic for: ripples on empty board points, ignored taps, zoom/pan, the intro, stars, the Claw/Streak home beats, event screens
  (DECISION: keep the Taptic for play and rewards).

### 12.2 Rules
- **One haptic per display frame**; if several are requested in one frame the highest priority wins: `heartLost` > `fail` > `win` >
  `burst` > `bumpContact` > `clear` > `booster` > `coinLand` > `tap` > `button`.
- Fire inside the same handler as the visual (before the CA commit, arch D8); generators are created at boot, `prepare()`d at boot, at
  every level start and after each fire (the Taptic Engine idles after ~2 s).
- Gated by `PlayerState.settings.haptic` (Pause + Settings toggles); iOS "System Haptics" off silences them system-wide.
- `audio.json haptics.<case>.style` ∈ light · medium · heavy · rigid · soft · success · warning · error · none (the existing
  `AudioTuning.haptic(_:)` reader); `none` disables a row without code.

---

## 13 The data (Tuning keys). Owners copy these blocks into their files; keys marked NEW are read by code the owner adds (§15).

### 13.1 `Tuning/board.json` (BOARD) — additions/changes only (keep every other present key)
```json
{
  "exit": { "v0": 7.67, "vmax": 73.86, "tau": 0.353, "colourRamp": 0.09, "leftBoardAt": "lastCell" },
  "combo": { "ladder": ["solid", "solid", "violet", "rainbow"] },
  "color": { "exit": "#10A2EF", "marked": "#EE0A13", "dot": "#C5E1FF", "hint": "#00DE00" },
  "violet": { "palette": ["#01ACFD", "#3972FF", "#7B3CFC", "#B908FE", "#7B3CFC", "#3972FF"], "periodCells": 3.75 },
  "rainbow": { "periodCells": 4.2, "driftDegPerS": 0 },
  "stars": { "perCell": 2.4, "sizePitch": 0.30, "sizeRangePitch": 0.08, "jitterPitch": 0.25, "life": 0.40, "endScale": 0.4,
             "spinDegPerS": 90, "solidColors": ["#1E88F5", "#7FD8FF"] },
  "dots": { "mode": "static" },
  "bump": { "outBase": 0.075, "outPerCell": 0.025, "hold": 0, "back": 0.14, "redFrom": 0.017, "redTo": 0.12,
            "blockerRedFrom": 0.02, "blockerRedTo": 0.12, "blockerBlackAt": 0.33, "obstacleTintAlpha": 0.6 },
  "vignette": { "alpha": 0.42, "decayPt": 27, "hold": 0.035, "total": 0.33,
                "stopsPt": [0, 5, 10, 20, 30, 45, 70, 90], "stopsAlpha": [0.42, 0.37, 0.31, 0.22, 0.16, 0.08, 0.02, 0] },
  "intro": { "zoomFrom": 1.49, "zoomDuration": 1.35, "drawBase": 0.32, "drawPerCell": 0.0216, "drawStartFraction": [0.10, 0.30],
             "ackAt": 1.015, "ftueAckAt": 0.36 },
  "stage": { "dotsFadeFrom": 0.12, "dotsFade": 0.56 },
  "stageGap": 0.7,
  "clearWave": { "frontDuration": 0.45, "total": 0.50, "envelope": [0, 0, 0.05, 1, 0.15, 1, 0.40, 0], "trailFraction": 0.15 },
  "key": { "detachAt": 0.23, "sagPitch": 0.48, "sagDur": 0.08, "wobbleDeg": 15, "floatPitch": 2.3, "floatDur": 0.22,
           "diveGPitch": 428, "diveMin": 0.16, "diveMax": 0.40, "insertDur": 0.15, "insertScale": 0.7, "turnGap": 0.08, "turnDur": 0.10,
           "turnDeg": 90, "flashDur": 0.216, "flashPitch": 0.9 },
  "pipe": { "breakAfterLeave": 0.05 },
  "counter": { "popScale": 1.0, "popDur": 0 },
  "elevator": { "doorsAt": 0.02, "doorsDur": 0.30, "tintFrom": 0.55, "frameFadeAt": 0.30, "frameFadeDur": 0.15 },
  "corner": { "popScale": 1.15, "popDur": 0.15 },
  "shards": {
    "door": { "count": 60, "g": 1000, "life": 0.90, "fadeFrom": 0.65, "vyMin": -260, "vyMax": -120, "vxMax": 160, "spin": 360 },
    "pipe": { "count": 40, "g": 1000, "life": 1.40, "fadeFrom": 1.0, "vyMin": -220, "vyMax": -80, "vxMax": 140, "spin": 300 },
    "box":  { "count": 140, "g": 1275, "life": 0.67, "fadeFrom": 0.35, "vxMin": 60, "vxMax": 180, "spin": 240 }
  },
  "hint": { "cameraDelay": 0.05, "cameraDur": 0.80, "cameraCurve": [0.25, 0.1, 0.25, 1.0],
            "blink": [1.03, 0.20, 0.13, 0.17, 0.38, 0.19], "returnDur": 0.50 },
  "pan": { "limit": "centreInGrid", "bounces": true, "deceleration": "normal" },
  "zoom": { "minPitch": 14.036, "maxPitch": 28.07, "bounces": true },
  "input": { "slopPt": 10 }
}
```
(`hint.blink` = [first fade-in start from B, fade-in, hold, fade-out, off, final fade-in].)

### 13.2 `Tuning/ui.json` (SHELL) — additions/changes
```json
{
  "button": { "pressScale": 0.95 },
  "popup": { "dimFadeIn": 0 },
  "loading": { "dotsPeriod": 0.40 },
  "transition": { "loadingToBoard": 0.13, "loadingToHome": 0.16, "homeTabs": 0 },
  "hudIntro": { "startAfterCut": 1.015, "dropPt": 118.4, "dropDur": 0.334, "dropBack": 3.42,
                "boosterDelay": 0.077, "boosterPt": 88.8, "boosterDur": 0.209, "boosterBack": 2.57,
                "bigTimerAt": 1.339, "bigTimerKf": [0, 3.5, 0.067, 1.42, 0.083, 1.31, 0.10, 1.17, 0.133, 0.95, 0.167, 0.88, 0.20, 0.96, 0.25, 1.0],
                "heartsAt": [1.406, 1.505, 1.622],
                "heartKf": [0, 1.58, 0.05, 1.36, 0.10, 0.93, 0.133, 0.89, 0.167, 0.96, 0.20, 1.04, 0.25, 1.02, 0.30, 1.0] },
  "hud": { "outOfTimeHold": 1.61, "heartsOutDelay": 0.60, "addTimePop": [1.3, 0.25],
           "heartBreak": { "v0": -115, "g": 960, "vx": 37.5, "rot1": 25, "rot2": 40, "fadeFrom": 0.30, "fadeTo": 0.40 } },
  "freeze": { "spawn": [192, 612], "spawnDur": 0.12, "riseFrom": 0.10, "riseDur": 0.83, "riseTo": 405, "rockDeg": 4,
              "flyFrom": 0.98, "flyDur": 0.40, "flyControl": [175, 200], "target": [107, 94], "flyEndScale": 0.35,
              "iceFrom": 1.38, "iceDur": 0.25, "frostFrom": 1.60, "frostDur": 0.20, "frostColor": "#6BD4F8",
              "frostDepthSidesPt": 30, "frostDepthTopBottomPt": 88, "tray": [93, 118, 92, 25], "trayIn": 0.20, "trayOut": 0.15,
              "endFade": 0.30 },
  "win": { "panelAt": 3.94, "skipFrom": 0.41, "signAt": 0.41, "signDur": 0.23, "lettersAt": 0.59, "letterStagger": 0.035,
           "letterDur": 0.12, "arrowSignAt": 0.64, "arrowSignDur": 0.23, "outAt": 0.94, "outGrowDur": 0.13, "outBig": 2.5,
           "outHoldTo": 1.47, "slamDur": 0.17, "squash": 0.92, "settleScale": 0.94, "dimAt": 1.24, "dimDur": 0.34, "dim": 0.90,
           "confettiAt": 1.47, "rockets": [1.60, 1.78, 1.95, 2.15, 2.40, 2.75], "bursts": [2.24, 2.44, 2.64, 2.84, 3.07, 3.47],
           "burstFlash": 0.08, "clearAt": 3.90, "stripAt": 3.95, "stripDur": 0.13, "chipAt": 4.34, "chipDur": 0.31 },
  "unlock": { "icon": 0.26, "iconSettle": 0.54, "title": 0.50, "unlocked": 0.62, "card": 0.78, "sparkles": 1.14,
              "dismissFade": 0.16, "acceptFrom": 0.94 },
  "tutorial": { "showAfter": 0.36, "captionKf": [0, 0.7, 0.04, 0.98, 0.08, 1.10, 0.12, 1.05, 0.16, 1.0],
                "handIn": [0.24, 0.28], "handLoop": [1.26, 0.48, 0.36], "handPressScale": 0.53, "handFirstHold": 0.28,
                "captionOut": 0.16, "handOut": 0.12 },
  "overlayStagger": [0.18, 0.35, 0.58, 0.72, 0.88, 1.10],
  "homeReturn": {
    "claw": { "dimIn": [0.03, 0.13], "dim": 0.50, "tokenAt": 0.03, "tokenDur": 0.10, "flashAt": 0.23, "badgeAt": 0.23, "badgeSlide": [0.53, 0.15],
              "burstAt": 0.68, "labelAt": 0.88, "dimOut": [1.33, 0.20], "flyAt": 1.43, "flyDur": 0.30, "iconFlashAt": 1.73,
              "countAt": 1.74, "tickStep": 0.057, "maxTicks": 7, "end": 2.11, "x1Shift": -0.73 },
    "streak": { "trayIn": [0.0, 0.22], "flagAt": 0.02, "flagFly": [0.57, 0.17], "chipAt": 0.72, "chipDur": 0.10,
                "pops": [0.77, 0.92, 1.14], "badgeFlashAt": 1.20, "trayOut": [1.99, 0.18], "coinsAt": 1.25 },
    "coins": { "labelAt": 0.0, "labelDur": 0.25, "cueLead": 1.12, "liftAt": 0.55, "stagger": 0.085, "flight": 0.22, "count": 5,
               "origin": [196, 490], "control": [196, 180], "target": [112.7, 70], "endScale": 0.85, "labelFadeAt": 1.12 },
    "aloneStart": 0.35, "afterClawOnly": 0.40
  },
  "fx": { "sparkles": { "count": 7, "radius": 22, "duration": 0.7, "size": 9, "colors": ["#FFFFFF", "#FFF6B0", "#FFE14A"] },
          "confetti": { "burst": 140, "rainPerS": 45, "colors": ["#1F77F3", "#EB4FB0", "#6A11EF", "#D30A20", "#FFB807", "#F8F2DA", "#65DD2B"],
                        "sizeMin": 5, "sizeMax": 11, "flipMin": 2, "flipMax": 5 },
          "firework": { "sparks": 48, "speedMin": 260, "speedMax": 420, "life": 0.8,
                        "colors": ["#FFFFFF", "#FFFFFF", "#8D5FFF", "#4079FF", "#FF2FC6", "#FFCE01"] },
          "unlockTwinkles": { "every": 0.18, "max": 6, "life": 0.70, "ellipse": [150, 110] } },
  "puppet": { "char_sci_home_rig": { "cycle": 3.16 }, "char_wk_homeR_blue_rig": { "cycle": 10.2 }, "char_wk_homeL_blue_rig": { "cycle": 17.3 } }
}
```
(The per-rig keyframe tables of §8.2 go under `puppet.<rig>.tracks` as `{layer, property, times[], values[], curve}` arrays; S1 decides
the exact shape when it extends `PuppetParams`, §15.3.)

### 13.3 `Tuning/audio.json` (AUDIO) — full replacement of `cues`, `gain`, `haptics`, `music`
```json
{
  "music": { "enabled": false, "crossfade": 0.3 },
  "cues": { "uiButton": "uiClick", "celebrationSkip": "uiClick", "dismissTap": "uiClick", "unlockOverlay": "unlockChime",
            "homePayout": "coinCollect", "clawToken": "clawToken", "clawMerge": "clawMerge", "clawTick": "clawTick",
            "clawComplete": "clawComplete", "streakPop": "streakPop", "arrowTap": "" },
  "gain": { "uiClick": 1.0, "unlockChime": 1.0, "coinCollect": 1.0, "clawToken": 1.0, "clawMerge": 1.0, "clawTick": 1.0,
            "clawComplete": 1.0, "streakPop": 1.0, "tapTick": 0.6 },
  "haptics": {
    "tap": { "style": "rigid", "intensity": 0.70 }, "heartLost": { "style": "error", "intensity": 1.0 },
    "bumpContact": { "style": "heavy", "intensity": 0.85 }, "fail": { "style": "warning", "intensity": 1.0 },
    "clear": { "style": "medium", "intensity": 0.80 }, "win": { "style": "success", "intensity": 1.0 },
    "burst": { "style": "medium", "intensity": 0.65 }, "button": { "style": "light", "intensity": 0.50 },
    "booster": { "style": "medium", "intensity": 0.60 }, "coinLand": { "style": "soft", "intensity": 0.45 }
  },
  "hapticPriority": ["heartLost", "fail", "win", "burst", "bumpContact", "clear", "booster", "coinLand", "tap", "button"]
}
```

### 13.4 `Tuning/rules.json` (CORE C2) — values this spec fixes
`combo.window 1.25`, `combo.bumpBreaks true`, `pipe.countAt "leave"` (the visible beat), `box.countAt "tap"`, `clock.alerts []`,
`boosters.freezeSeconds 10`, `boosters.freezeFlight 1.6`.

---

## 14 PENDING-motion-audio closure (SPEC-architecture §14 + the `_pending` lists of board/ui/audio/rules.json)
| PENDING item | value | where |
|---|---|---|
| bump profile (phone vs YT-B) | phone: constant speed, T_out = 0.075 + 0.025·c, no hold, back 0.14 s easeOutQuad, red on the return | §3.4 |
| the violet colour | a 6-stop field #01ACFD/#3972FF/#7B3CFC/#B908FE, period 3.75 cells | §3.2.2 |
| the rainbow period | 4.2 cells (P3: 3.66–4.74 on phone shots) | §3.2.2 |
| star counts / sizes | 2.4 per cell, 0.30 p, life 0.40 s, jitter 0.25 p | §3.2.3 |
| build-in of obstacles | drawn complete on the first frame, zoom with the board (no fade) | §3.5.7 |
| pipe/box counter-change timing and animation | pipe when the arrow comes out of the far mouth (VERIFIED vlev-D); box at the tap (VERIFIED); instant glyph swap, no pop (INFERRED) | §3.5.3–4 |
| pan limits and snap-back | centre-in-grid limit; native rubber-band + bounce; deceleration .normal | §3.9 |
| slop | 10 pt | §3.9 |
| combo window refinements, bump breaks | 1.25 s; a bump breaks; ignored taps don't count; tape = one tap; caps at rainbow | §3.3 |
| puppet idle loops | 3.16 s / 10.2 s / 17.3 s with the keyframe tables | §8.2 |
| the cue list and music | 9 SoundIDs (5 new), music none | §11 |
| the owner's tap-sound question | `tapTick` rendered, unmapped; the click feeling = release-fire + ripple + `.rigid` 0.70 haptic | MA3, §12 |
| haptic intensities | §12.1 | §12 |
| intro (`intro.*`), ripple, vignette, exit constants | confirmed/extended | §3.1, §3.4.4, §3.6 |
| timer alerts near 0 (shared with gameplay) | none (VERIFIED) + "0:00" hold 1.61 s | §4 |
| loading dots / transitions (shared with ui) | 0.40 s; 0.13 / 0.16 / 0 s | §7 |
| fx.sparkles (ui) | S1's values accepted | §10 |
| music.enabled | false | §11.5 |

---

## 15 Requests to other owners (nobody edits another's file; the orchestrator routes these)

### 15.1 Contract change — `App/Contracts/AudioContract.swift` ◆ (orchestrator)
```swift
enum SoundID: String, CaseIterable, Sendable {
    case uiClick, coinCollect, unlockChime, tapTick
    case clawToken, clawMerge, clawTick, clawComplete, streakPop
    var bus: AudioBus { return .sfx }
}
enum Haptic: String, CaseIterable, Sendable { case tap, bumpContact, fail, clear, win, burst, heartLost, button, booster, coinLand }
```
Additive only (no existing case changes; `specs.py` parses the case lines). `AudioTuning.haptic(_:)` in `Tuning.swift` ◆ needs default
rows for the 4 new cases (heartLost error, button light 0.5, booster medium 0.6, coinLand soft 0.45) — same request.
**Fallback if refused:** `bumpContact` style = `error` (so a heart loss still buzzes error; a no-heart re-bump then also does);
`button` → none; `booster` → play `.burst`; `coinLand` → none; home cues clawToken…streakPop silent.

### 15.2 CORE C1/C2 (PathCore)
- `Motion/ExitKinematics.swift`: constants v0 7.67, vmax 73.86, T 0.353 and the §2 T(d) table as the test (the HeadlessDriver's
  modelled acks then match the board). `Timing.exitColourRamp` 0.09. `Curves` per §2 (bump, vignette, heartBreak, introDraw, hudDrop,
  bigTimer, heartPop, clearWave, keyFlight).
- `rules.json`: §13.4 values.

### 15.3 BOARD (B1/B2), SHELL (S1–S3), GAME (G1/G2)
- B1: static dots layer (§3.2.4); intro ack at `intro.ackAt`; hit test through the presentation transform during the intro zoom;
  `pan.limit centreInGrid`; the new board.json keys.
- B2: violet field painter; star emitters with keyframed birthRate; shard pools in screen pt; key-flight geometry for far locks;
  elevator doors + tinted reveal; hint camera + blink; clear wave colour-by-radius.
- S1: per-rig puppet cycles and tracks (§8.2) replacing the shared `workerSway*` knobs; button press 0.95 + click + `button` haptic on
  release everywhere (win Continue: no click); the Music button inert (MA2).
- S2: HUD intro keyframes, heart break on the contact frame, freeze tray + frost, celebration (W-anchored, skip from W + 0.41),
  panel strip slides, unlock overlay beats, tutorial hand/caption.
- S3: home-return queue segments A/B/C with the cue schedule; Claw bar count-up; coin fly.
- G1/G2: `FailFlowDirector` waits `hud.outOfTimeHold` 1.61 s after 0:00 and `hud.heartsOutDelay` 0.60 s after the last heart's
  contact; `WinDirector` starts the celebration clock at `lastExitLeftBoard` (not at `clearWaveFinished`); haptic priority per frame.

### 15.4 UI-ART (new or split assets)
`logoArrowOut` parts for the slam (blue sign plate, letters A/R/R/O/W, purple arrow sign, "OUT!"); `iconStopwatchIced` (snow cap +
icicles overlay for `hud.stopwatch`); `fxFrostEdge` (393 × 852 pt edge frost: cracks, flakes, twinkles, alpha only near the edges);
optional `eyes_wink` member for `char_wk_homeL_blue_rig`; the green flag-roll icon of the Streak Race "+m" flight (if
`iconCheckeredFlag` is not it); confirm `boardTrailStar`, `doorShards`, `pipeShards`, `sparkleTwinkle`, `heartHUDHalves`,
`coinPileSmall`, `iconCoin`, `iconHexArrow` are in the bundle (all used above).

### 15.5 AUDIO (A1/A2/A3)
Recipes and spec rows §11.3; `music.py`/`check.py` skip MusicIDs while `music.enabled` is false (§11.5); check assertions §11.6;
`Haptics` priority/one-per-frame rule §12.2; SoundBoard lists the 9 sounds and 10 haptics.

---

## 16 Still open (phone gap-filler; each has a DECISION above until captured — clips-needed.md numbers)
#1b bump law at gap 0 and ≥ 6 cells (the META bump clips of the meta explorer start after the bump — [P3] checked, unusable);
#5 tape member sync; #6b skip-tap on v552; #7b the coin cue's tail; #8b intro of a small / Hard board; #10 combo edge cases +
lossless violet; #13 inertia and rubber-band; #14 key to a far door; #15 booster/X press states; #17 pipe counter change at 60 Hz;
#18 the unlock chime on v552; #20 hourglass tap → spawn and the freeze end; #21 bulb tap → camera start; #23 event-screen motion.
Haptics can only be judged by feel on the phone (D1b): the owner's side-by-side verdict may retune §12.1 as data.

## 17 Strings (EN = the original's; TR = ours)
| key | EN | TR |
|---|---|---|
| payout / event gain label | `+%lld` | `+%lld` |
| tutorial caption | `Tap to move!` | `Hareket ettirmek için dokun!` |
| freeze countdown | `%lld` (digits only) | `%lld` |
No other text is introduced by this spec (every other visible string belongs to SPEC-ui / SPEC-gameplay / SPEC-social).
