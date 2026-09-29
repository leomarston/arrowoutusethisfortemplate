# Arrow Out — tutorials, FTUE and first-time moments (from the owner's videos + the phone)

Owner-facing name: **Arrow Out**. The original is "Maze Out! - Tap Puzzle" (Grand Games). Every caption below is the original's
wording, which we copy 1:1 (mechanics text). The one exception is the brand: the win splash logo "MAZE OUT!" becomes our "ARROW OUT!"
logo, drawn by us in the same style.

Author: tutor lane, 2026-09-25. Companion file: `research/video-flows.md` (per-level timelines, win/intro sequences, social screens).
Frames: `research/video-frames/tutor/` (gitignored): `full/` (full-res PNG), `sheets/` (contact sheets), `ref/` (crops), `idx1/` (V1 at 5 fps), `idx2/` (V2 at 1 fps),
`f25/` (a few 25 fps runs; any other run regenerates in about a second with `tools/vgrab`).
Tools: `video-frames/tutor/tools/` (`vgrab` exact-frame grabber, `ocr` Vision OCR in pt, `sheet.py`, `rsheet.sh`, `timer.sh`, `tickprobe.sh`).

## 0. Sources and conventions

| id | file | build | fps | what it covers |
|---|---|---|---|---|
| V1 | `research/video/owner/V1-levels-01-20.mp4` | about Aug 2026 (the "Curtain" name, MAZE OUT! win splash, 3-tab home = like the phone) | 25 | loading → Levels 1-4 (every tutorial) → L5 … L20 → home L21. Trimmed start (0.44 s of Loading), YouTube end card from 499 s |
| V2 | `research/video/owner/V2-levels-11-38.mp4` | recorded Thu 30 Jul 2026 22:27 (iOS status bar, Vietnamese locale; a studio studying the game) | 59.64 | launch splash, notification prompt, home L11, a tour of Shop / Leaderboard / Adventure / Settings / Profile, L11 … L38, home L39 |
| phone | `research/flows.md`, `research/levels.md`, `research/obstacles.md`, `research/shots/` | v552 (current) | – | L32 onward |

- Times are video seconds (V1: frame n = n × 0.04 s). "≈" = read from 5 fps or 1 fps indexes. Every other value is from 25 fps frames.
- Points: pt = px × 393/592. Checked on the home screen: V1 Play centre (296,1000) px = (196.5,664) pt, phone (196,668) pt; Home tab
  (296,1210) px = (196.5,803) pt, phone (196,800) pt. That is 0.2-0.6 % off, so V1 geometry can be used directly in the 393 × 852 layout.
- **Skins.** V1 and V2 are older skins: blue arrows on a light-blue ground (#EFF5FF), a 4-booster bar, and a plain "Level N" text
  under the timer pill. The phone (v552) has black arrows on white, 2 boosters, a coin pill, and a "Level N" tab on the pill.
  **Rule: for how things LOOK, the phone wins. The videos supply content, sequence, captions and timing.**
- **Level content.** The V2 boards for L32-38 match none of the phone's L32-38. See `video-frames/tutor/sheets/V2_vs_phone_L32-38.jpg`:
  different boards, and Hard falls on L35 in V2 but on L34 on the phone. So the videos' L1-31 are the older build's levels. The owner
  asked us to use them for L1-31. V1 and V2 show the same boards for L11-20 (seen on L11 and L19; the levels lane checks the rest).

## 1. The first-time user experience at a glance (V1 = fresh install)

| # | video t | what the player sees | input | notes |
|---|---|---|---|---|
| 1 | V2 0.0-2.9 | publisher splash ("grand", white on crimson) | – | ours: our own studio splash, or none |
| 2 | V2 3.0-11.8 / V1 0-0.44 | Loading screen: logo art + characters + "Loading" with animated dots (".", "..", "...") | – | the iOS notification-permission prompt appears OVER the Loading screen on first launch (V2 3.0-6.0; phone F00) |
| 3 | V1 0.44 | the Loading screen cross-fades (≈0.1 s) straight into **"Levels 1-4"**, stage 1. The HUD is already in place; there is no home first | – | first launch goes straight into play |
| 4 | V1 0.80-3.50 | **"Tap to move!"** caption + a pointing hand on the middle arrow | tap | §3 |
| 5 | V1 3.5-24.2 | the rest of the 4 stages; no hints | taps | §2 |
| 6 | V1 24.2-27.4 | board-clear colour wave → "MAZE OUT!" logo slam → dim + fireworks + confetti | – | ours: "ARROW OUT!" |
| 7 | V1 27.4 | win panel: tab **"Level 1-4"**, **"Perfect!"**, **"Rewards:"**, coin pile **80**, green **"Continue"**, red X | Continue | the coins are NOT counted up here |
| 8 | V1 28.34 | **straight into Level 5** (no home) with the level-intro HUD animation | play | |
| 9 | V1 43.6 → 44.9 | L5 win panel (20) → Continue → **straight into Level 6** (heart-shaped board) | play | |
| 10 | V1 72.2 → 73.64 | L6 win panel (20) → Continue → **HOME for the first time** | – | §5 |
| 11 | V1 73.9-75.3 | "+120" and a coin pile over the LEVEL plate; 5 coins fly to the coin pill; 1000 → 1120 | – | all coins won so far (80+20+20) are paid out here |
| 12 | V1 76.42 | Play → **"Linked Arrows! / Unlocked! / LINKED ARROWS move together!"** over the dimmed L7 board | tap anywhere | §6 |
| 13 | from L7 on | every win → panel → Continue → home (+20 coin fly) → Play | – | |
| 14 | V1 183.3 | L11: **"Curtain! / Unlocked! / Clear required amount of arrows to open the CURTAIN!"** (V2: "Box! … break the BOX!") | tap anywhere | |
| 15 | V1 408 | L19: home Play turns RED with a **"Hard Level"** ribbon; no popup | – | §7 |
| 16 | V2 525 | L21: **"Pipe! / Unlocked! / Pass arrows through the PIPE to break it!"** | tap anywhere | phone: same card at L35 |
| 17 | V2 977 | L29: PURPLE Play button with a **"Super Hard"** ribbon; no popup | – | |
| 18 | V2 1181 | L31: **"Elevator! / Unlocked! / Clear all arrows on the ELEVATOR to activate it!"** | tap anywhere | |
| 19 | V2 1372 | after the **L34** win, on home: the iOS "rate this app" sheet | "Not Now" | phone: also after L34 |
| – | V2 29-34 | Leaderboard → Weekly: **"Reach level 50 to compete in Weekly Contest!"** | – | phone: a forced Weekly Contest tutorial at L50 (flows.md) |
| – | V2 50 | tapping the avatar → Profile → **"Enter Username"** popup (not forced) | type + Continue | video-flows.md §9 |

Boosters: all 4 are there with a "3" badge from the very first board (V1 0.44). There is no booster unlock and no booster tutorial in
either video, and no booster is ever used (every badge reads 3 from start to end, V1 and V2).

## 2. "Levels 1-4": one session, four boards

- **One session.** The level label reads **"Levels 1-4"** (plural) for all four boards. The win panel tab reads **"Level 1-4"**
  (singular). There is ONE win celebration and ONE win panel, at the end, and it pays **80** coins (4 × 20).
- **Four boards in a row, no panel between them.** When a stage's last arrow leaves, the board-clear colour wave runs, the dots
  fade, and the next board builds in:
  - stage 1: the last tap is at ≈4.84 and the arrow is gone by ≈5.08;
  - dots recoloured 5.12, fading 5.20-5.76;
  - stage 2 builds in at 5.80 (the new dot grid first, then the arrows grow from tail to head; complete by ≈6.24).
  - The gap from the last arrow leaving (≈5.08) to the new board appearing (5.80) is ≈0.7 s.
- **The timer restarts at 3:00 for every stage.** It stays frozen until that stage's first tap. The hearts stay at 3 (no heart was
  lost, so whether hearts reset per stage is unknown).

| stage | board appears | first tap | first tick 2:59 | clear | board (approximate; the levels lane extracts exact cells) |
|---|---|---|---|---|---|
| 1 | 0.44 (built by 0.68) | 3.50 (the hinted arrow) | 4.08 | ≈5.08 | 3 vertical arrows in adjacent columns, pitch 28 pt: left ↓, middle ↑, right ↓, each ≈98 pt (≈4 cells) long. **All three are free.** |
| 2 | 5.80 | 8.00 | 8.08-8.12 | ≈10.2 | 6 arrows: nested ⊐/⌐ frames + two short ↑ in the middle |
| 3 | 11.04 | 12.48 | 13.16 | ≈17.0 | 8 arrows drawn like the glyphs "2 5 / 2 5" |
| 4 | 17.92 | ≈19.5-20.1 | 20.20 | ≈24.0 | ≈10-11 arrows: a spiral / "Tetris-T" maze |

Frames: `full/V1_t0000.76.png`, `V1_t0006.40.png`, `V1_t0011.60.png`, `V1_t0018.40.png`; sheet `sheets/V1_stages_1-4.jpg`.
- **Time left at each clear:** 2:59 / 2:58 / 2:56 / 2:56. The celebration keeps the last value (2:56 in the dimmed HUD).
- **Next level.** Continue on the "Level 1-4" panel starts **Level 5** (the home level counter jumps 1-4 → 5). The Profile's
  "First Try Wins" read **10** at L11 (V2 53 s, a player who never failed). So Levels 1-4 count as FOUR levels, plus L5-L10 = 10.

## 3. Stage 1 tutorial "Tap to move!" (beat by beat, V1 25 fps)

| t (s) | beat |
|---|---|
| 0.44-0.52 | cross-fade from Loading. The HUD is fully there (back ◀, pill with ⏱ 3:00 and ♥♥♥, pause ❚❚, "Levels 1-4" under the pill, the booster bar). No HUD intro on this first board |
| 0.44-0.68 | the 3 arrows grow from their tails; the heads appear last |
| 0.80 | the caption **"Tap to move!"** appears at ≈0.7 scale → 0.84 ≈0.98 → **0.88 ≈1.10 (overshoot)** → 0.92 ≈1.05 → 0.96-1.00 1.0 (ease-out-back, 0.20 s). Same start frame as the hand |
| 0.80-1.08 | the **hand** scales in about its fingertip: 0.24 → 0.42 → 0.58 → 0.77 → 0.86 → 0.96 → 0.99 → 1.0 (ease-out, 0.28 s, no overshoot) |
| 1.08-1.36 | the hand holds at full size (0.28 s) |
| 1.36-1.84 | **press:** the hand shrinks about its fingertip 1.0 → 0.53 (0.48 s, ease-in-out). The shadow shrinks with it: the hand "pushes into" the screen |
| 1.84-2.20 | **release:** 0.53 → 1.0 (0.36 s, ease-out) |
| 2.20-3.48 | holds (≥ 1.28 s; the player tapped before a second press began) |
| 3.48-3.50 | **the player taps the middle arrow.** A grey tap ripple appears at the touch point; the arrow starts to leave (up) on the next frame |
| 3.52-3.64 | the caption scales out 1.0 → 0.70 → 0.54 → 0.29 → 0.12 → gone at 3.68 (0.16 s, ease-in). The hand fades out in place (alpha ≈0.7 → 0.45 → 0.2 → 0 over 3.52-3.64; no scaling) |
| 3.50-3.76 | the tapped arrow leaves through the top of the board area (≈0.26 s) |
| 4.08 | first timer tick: 3:00 → 2:59. The tutorial does not hold the timer any longer than a normal level does (§8) |
| 4.2 / 4.8 | the player taps the left ↓ and then the right ↓. There is no hint for them and the caption never comes back |

**Caption "Tap to move!"**
- Text exactly `Tap to move!` (capital T; lower case after; "!" at the end).
- Heavy rounded display font: the same family as the game's UI (Nunito Black class; ours = PCDisplay-Black).
- Colour: solid navy ink ≈ RGB(18,27,81) = #121B51. No outline, no plate, no shadow.
- Ink bbox x 75.0-316.0 pt, y 271.5-306.7 pt (241 × 35 pt incl. the "p" descender); the "T" cap height is 27.9 pt → ≈40 pt font.
- Centre x 195.5 (screen centre), top at 271.5 pt: ≈96 pt above the arrows' top (387 pt).
- Crop: `ref/V1_caption_tap_to_move.png`.

**Hand pointer**
- A yellow-orange cartoon hand with the index finger pointing up-left (an emoji-style 3D "tap" hand), with a soft grey drop shadow
  down-right. Full size ≈70 × 99 pt including the shadow.
- The **fingertip** sits at ≈(193, 424) pt: on the middle arrow's left edge (arrow x 193-199), ≈38 % down its length (arrow
  y 387-490). That is 10 pt above the arrow's midpoint. The palm and the other fingers hang down-right over the right-hand arrow.
- Every scale animation is anchored at the fingertip.
- Crops: `ref/V1_hand_full_t1.20.png`, `ref/V1_hand_pressed_t1.84.png`, sheet `sheets/V1_hand_crops.jpg`.
- Our art: draw our own hand (same pose, colours and shadow). Never trace the frames.

**Dimming, highlighting, input**
- **No dimming and no spotlight.** The other two arrows stay at full colour and the HUD stays live.
- Input restricted to the hinted arrow? **Not observable.** All three arrows are free, and the player tapped the hinted one.
  Our spec (INFERRED): any arrow may be tapped, and the hint leaves on the first tap of any arrow. A wrong tap is impossible on this
  board (nothing is blocked), which is how the original avoids a failure in the tutorial.
- A wrong tap in general is a **bump**: a heart is lost, a red vignette flashes, and the tapped arrow stays marked (§8).
- The hint is shown **only on stage 1** and only until the first tap. Stages 2-4 have no caption and no hand.
- **Press loop (INFERRED).** Only one press cycle is visible (appear → 0.28 s hold → 0.84 s press → ≥1.28 s hold). Build it as a
  loop with a 2.1 s period: hold 1.26 s, then press 0.48 s + release 0.36 s. The first press starts 0.56 s after the hand appears.

## 4. First win and rewards (V1)

1. The last arrow of stage 4 leaves (≈24.2). The board-clear wave runs: a ring of rainbow-coloured dots expands from the board
   centre through the dot grid, then the dots fade (≈0.4 s).
2. **Logo.**
   - 24.4: the blue "MAZE" sign swoops in from the lower left, spinning, and settles slightly tilted at the upper-middle.
   - The purple arrow sign swoops in from the bottom and settles under MAZE.
   - 24.8-25.2: the white "OUT!" letters balloon to wider than the screen, then slam down into the purple arrow.
   - 25.2-25.4: the screen dims to ≈90 % black.
   - 25.4-27.2: two firework rockets rise from the bottom and burst; confetti rains.
   - The same sequence at 25 fps on L5 is in `video-flows.md` §4.
3. **Win panel (27.4-27.6).** It pops in over the dimmed board with the confetti still falling:
   - a blue panel with a yellow tab **"Level 1-4"** and a red round X at the top right;
   - **"Perfect!"** (white fill, dark outline), **"Rewards:"**, a gold coin pile + **"80"**, and a green **"Continue"** button.
   - V1 shows NO Streak Race banner under the panel. The phone shows one under every panel (flows.md).
4. **Continue (28.34) → Level 5 at once.** The level-intro HUD animation plays:
   - 28.32-28.64: the whole HUD row (back, pill, pause) drops in from above the screen, overshoots ≈38 pt below its rest at 28.48 and
     springs back to rest by 28.64. The pill shows an empty bar and 3 empty heart slots;
   - 28.64: a big "3:00" pops (≈2.2×) and snaps to size by 28.72;
   - the hearts pop in one after another at 28.72 / 28.80 / 28.88, each with an overshoot;
   - "Level 5" fades in 28.88-29.08.
   - The board builds in 28.36-28.72: dots first, then the arrows grow tail→head.
5. The L5 win (panel 43.60, reward **20**) → Continue → **Level 6 at once** (45.0).
6. The L6 win (panel 72.2, **20**) → Continue (73.60) → **HOME (73.64).** The coins won in the FTUE are banked in one payout:
   - 73.9: a coin pile and **"+120"** rise over the capsule machine / LEVEL plate;
   - 74.44-75.00: five coins stream in an arc to the coin pill;
   - the pill counts **1000 → 1024 → 1048 → 1072 → 1096 → 1120** (one step per coin, 74.72-75.04), with a sparkle burst on the pill;
   - it all takes ≈1.4 s.
   - **Starting coins = 1000.**
7. From L7 on, every win pays the same way on home: "+20" (Hard "+60", Super Hard "+100"), 5 coins fly, and the pill counts up in
   5 steps (for example 1240 → 1244 → … → 1260).

## 5. The home screen, first time (V1 73.64, frame `full/V1_t0075.60.png`)

- **Top bar:**
  - an avatar tile (grey silhouette on blue);
  - a coin pill with a green "+" and **"1120"**;
  - lives "5" + **"Full"**. V1 draws the lives badge as a blue bolt; V2 and the phone draw a red heart, so ours is the phone's heart;
  - a settings gear.
- **Scene:**
  - the purple scientist monster at a console with a green button (ours: PINK, owner 02:33);
  - the capsule machine full of coloured 3D arrows;
  - a green **"LEVEL"** plate reading **7**;
  - two yellow worker capsules (ours: BLUE or RED);
  - the big green **"Play"** button;
  - bottom nav with 3 tabs: basket (shop) · raised **Home** · trophy. V2 had 5 tabs (Shop, Leaderboard, Home, Adventure, Settings).
    The phone has 3, like V1.
- **Nothing pops up on the first home:** no name prompt, no event, no hand on Play. There are no event badges on home anywhere in
  V1 (to L21) or V2 (to L39).

## 6. Obstacle unlock popups ("<Name>! / Unlocked! / card")

**All builds share one layout.** Checked side by side: V2's Pipe card = the phone's L35 Pipe card; see `sheets/phone_vs_V2_pipe_popup.jpg`.
- **When:** the first Play tap on a level that introduces the obstacle opens the level UNDER a ≈90 % black overlay. The ground
  #EFF5FF becomes (23,23,25) in V1; white becomes (25,25,25) on the phone. The board and the HUD show faintly through it.
- **Build-in** (V1 L7, t0 = Play tap 76.42):
  - +0.02: the dimmed board is there (no bright frame first);
  - +0.26: the icon pops in at the centre (tiny → ≈1.3× at +0.42 → 1.0 at +0.54, ease-out-back);
  - +0.50: the title pops (small → overshoot at +0.62 → settled at +0.66);
  - +0.62: "Unlocked!" pops (≈0.08 s);
  - +0.78: the card pops (tiny → overshoot at +0.90 → settled at +0.94);
  - from +1.14: gold/white sparkles twinkle around the icon until the popup is dismissed.
- **Dismiss:** tap anywhere. The player tapped after 3.4 s (L7), 2.3 s (L11 V1), 3.4 s (Pipe V2), 1.9 s (Elevator V2). The overlay
  fades in ≈0.16 s and the board is playable with the timer at 3:00. The timer starts at the first tap, as always.
  A minimum display time is unknown.
- **After the popup:** there is NO in-board hint, no hand and no spotlight, on any obstacle level (V1 L7, L11; V2 L11, L21, L31;
  phone L35, L50).
- **Geometry (V1 L7, pt):**
  - title "Linked Arrows!": cream-white fill #FEF6E7 with a thick blue outline and a dark rim; fill bbox 59-334 × 186.5-215.8
    (≈40 pt font), centre y ≈200;
  - "Unlocked!": white with a navy outline, 138-254 × 281-297 (≈22 pt font), centre y ≈290;
  - icon: centre (196, 412), ≈140 × 97 pt;
  - card: a blue border (3-4 pt, double line), cream fill #F9E5CE, rounded ≈16 pt; outer 44.5-347.9 × 516.5-612.1 (303 × 96 pt,
    centre y 564);
  - card text: two centred lines, navy, the obstacle name in CAPS and BLUE (#1a5fd8-ish), ≈19 pt.
  - Frame `ref/V1_unlock_linked_arrows.png`.

| build | level | title | card text (exact; the caps word is blue) | icon |
|---|---|---|---|---|
| V1 | **7** | `Linked Arrows!` | `LINKED ARROWS move together!` | two blue → arrows bound by a pink X tape |
| V1 | **11** | `Curtain!` | `Clear required amount of arrows to open the CURTAIN!` | orange frame, blue slatted shutter, purple hexagon lock (the phone's DOOR look) |
| V2 | **11** | `Box!` | `Clear required amount of arrows to break the BOX!` | cyan box with a round lock + counter "5" |
| V2 | **21** | `Pipe!` | `Pass arrows through the PIPE to break it!` | a U pipe with counter "3" |
| V2 | **31** | `Elevator!` | `Clear all arrows on the ELEVATOR to activate it!` | grey double sliding doors |
| phone | 35 | `Pipe!` | `Pass arrows through the PIPE to break it!` | U pipe, orange cap "3" (shots/040) |
| phone | 50 | `Box!` | `Clear required amount of arrows to break the BOX!` | purple slab icon with a silver ring "5" (shots/134) |

- The phone's pink TAPE (obstacles.md) is the videos' **Linked Arrows**: pink X tape, one tap moves the bundle.
- The phone's DOOR has the V1 Curtain look but opens with KEYS (L33).
- **No unlock popup appeared at L32 (tape) or at L33 (doors + keys) on the phone.** shots/003 and 027 are the start frames. So v552
  introduced both before L32, and their card texts are unknown. The videos' "Linked Arrows!" card is the one to use for tapes.
- **Counter rule seen in V1 L11:** every arrow cleared lowers every curtain counter by 1 (8 → 7 → 6 …; 13 → 12 …). See
  `sheets/V1_L10win_curtain_L11.jpg`.

## 7. Hard and Super Hard, first time

- **No popup** (V1 L19, V2 L19/L25/L29/L35).
- **Home:**
  - the Play button turns **red** with a small **"Hard Level"** ribbon tab on its top edge (Super Hard: **purple**, ribbon **"Super Hard"**);
  - the LEVEL plate turns the same colour.
  - These appear on the home that follows the previous level's win (V1 408; V2 414, 709, 977, 1370, 1676).
- **In level (V1 skin):** a small red tab **"Hard Level"** sits on top of the timer pill; the back and pause buttons turn red
  (purple for Super Hard). Phone: the tab shows "Level N" in red/purple.
- **Win panel:** a red panel (Super Hard: purple) with a ribbon **"☠ Hard Level ☠"** above the yellow "Level 19" tab. Rewards
  **60** (Hard), **100** (Super Hard), 20 normal. Frames: `full/V1_t0468.60.png`, `full/V2_t1148.50.png`.
- **Timers in the videos:** 3:00 for every level L1-L38, Hard and Super Hard included. The phone's v552 Hard L34 has 3:30 and
  Super Hard L49 has 2:30 (levels.md). Timers are per-level data.
- **Positions:** V1/V2 have Hard at 19, 25, 35 and Super Hard at 29, 39; the phone has Hard at 34 and Super Hard at 39, 49.

## 8. Timer, hearts and mistakes in the early levels

- **Every early level, the FTUE included, has the timer (3:00) and 3 hearts.** No early level hides the HUD.
- **The timer is frozen at 3:00 until the first tap**, during the "Tap to move!" hint and while unlock popups show. It then counts
  down one step per second.
- **Delay from the first tap to the first 2:59.** Measured on 8 boards: 0.58 (tutorial), ≈0.1, 0.68, 0.96, 0.32, 0.24, 0.36, 0.60 s
  (stage 1, stage 2, stage 3, L5, L6, L7, L8, L19). It is never 0 and never more than 1 s, and the phase is not tied to the board appearing. Build it as: start a 1 Hz tick at
  the first tap, first tick after a random or fixed 0.1-1.0 s. The phone team measured "timer starts at the first tap". A 1.0 s
  ceil-display is an acceptable approximation.
- **The timer stops on the last arrow.** The HUD keeps the final value through the celebration.
- **No heart was lost** in V1 (L1-20) or in V2 L11-31. The only mistakes in the videos are V2 **L32**: 2 hearts, at 1235.20 and ≈1250.
  - Bump sequence (`sheets/V2_bump_L32.jpg`): tap on a blocked arrow → a **red vignette** flashes round the screen edges (1235.20-1235.47)
    → the rightmost red heart dims to grey-blue in ≈0.2 s → the tapped arrow and its blocker draw dark navy for ≈0.4 s
    → the tapped arrow **stays dark for the rest of the level**.
  - There is no time penalty (2:42 → 2:41 on schedule).
  - Phone: the same rule, with the marker colour RED (238,10,19) on black arrows (obstacles.md). **Phone wins: red.**
- A heart loss does not change the win title: it is "Perfect!" on phone L48 (1 heart lost) and on V2 L32 (2 hearts lost, 1255.5).

## 9. Other first-time moments

| moment | when | exact text / look | source |
|---|---|---|---|
| iOS notification permission | first launch, over Loading | system alert (the game name + "would like to send you notifications"). Phone: declined | V2 3.0-6.0, phone F00 |
| back button in level | any time | panel **"Quit Level?"**, broken-heart icon, **"You will lose a life!"**, red **"Quit"**, red X. Shown even before the first tap | V2 80.75-82.6, `full/V2_t0081.50.png` |
| pause | any time | panel **"Paused"**, round toggles **"Sound"** and **"Haptic"**, green **"Resume"**, red **"Quit"**, red X. The timer is frozen | V2 83.1, 88.2; phone shots/007 |
| rating prompt | home, right after the **L34** win (before L35) | the iOS SKStoreReview sheet ("Do you enjoy Maze Out!? / Tap a star to rate it on the App Store / Not Now") | V2 1372-1373.5, phone 01:27 |
| username | only when the player taps the avatar → Profile opens → **"Enter Username"** popup over it: **"Create your username:"** + field + **"Continue"** + X. Not forced | V2 50.2 | video-flows.md §9 |
| Weekly Contest | V2 leaderboard Weekly tab before L50: **"Reach level 50 / to compete in / Weekly Contest!"** (3 centred lines). Phone: the first Play tap on LEVEL 50 → forced tutorial (a yellow arrow points at the trophy tab, "Tap to compete in Weekly Contest!", the intro card, the board) | V2 29-30; phone flows.md "Weekly Contest unlock" | |
| events (Streak Race, Claw, Sky Jump, Rocket Race) | **absent from both videos** (no badge, no banner, no popup through V1 L21 / V2 L39) | – | phone: Streak Race banner + Claw bar already by L32 (Claw intro after the L32 win); Sky Jump "Join" after L39 (flows.md) |
| booster unlock / tutorial | none; 4 boosters ×3 from Levels 1-4 (V1/V2); the phone has 2 boosters ×3 | – | |

## 10. The phone-only tutorials (v552) — for completeness

- **Weekly Contest (L50):**
  - Play is intercepted: dim overlay, cream card "Tap to compete in Weekly Contest!", and a big yellow arrow pointing DOWN at the
    highlighted trophy tab. That tab is the only live target (input restricted).
  - Next an intro page ("Weekly Contest" / "Beat Levels!" / "Contest with others!" / "Win Rewards!" / "Compete against your
    friends! There is a new contest every week!" / "Tap to Continue").
  - Then the Weekly board. Details: flows.md.
- **Claw Challenge intro** (first shown after the L32 win) and its (i) overlay; **Sky Jump** intro overlay ("Start with 100 players!" …):
  flows.md.
- These are the only restricted-input tutorials seen anywhere; they use an ARROW pointer, not the hand.

## 11. What differs from the phone build, and which is current

| topic | V1 (Aug) | V2 (Jul 30) | phone v552 (current) | use |
|---|---|---|---|---|
| arrows / ground | blue #1678FF on #EFF5FF | same | black on white | phone |
| exit look | rainbow/gradient trail + dots | same | solid light blue #10A2EF | phone (PLAN decision) |
| bump marker | – | arrow stays dark navy | arrow stays red | phone |
| in-level label | "Levels 1-4" / "Level N" as plain outlined text under the pill; "Hard Level" red tab on the pill | same, "Super Hard" purple tab | "Level N" blue tab on the pill (red/purple on Hard/SH) + a coin pill top-left | phone (the tab text reads "Levels 1-4" on the FTUE board) |
| boosters | 4: yellow set-square, frozen hourglass, bulb, blue ring-stack (×3 each) | same | 2: frozen hourglass (left), bulb (right) (×3) | phone |
| win celebration | "MAZE OUT!" logo + dim + fireworks + confetti | "Well Done!" text + confetti, no dim | "MAZE OUT!" logo + dim + fireworks (= V1) | phone/V1 → our "ARROW OUT!" |
| win panel | yellow tab, blue panel, coin pile | blue tab, coins on blue cubes | yellow tab, blue panel + Streak Race banner below | phone |
| home nav | 3 tabs (shop, Home, trophy) | 5 tabs (+Adventure "Coming Soon", Settings) | 3 tabs | phone |
| lives badge | blue bolt "5" | red heart "5" | red heart "5" | phone |
| events on home | none | none | Claw bar, Streak Race, Sky Jump, (Rocket Race per web) | phone (simulated offline, owner 02:33) |
| obstacle names | Linked Arrows L7, Curtain L11 | Box L11, Pipe L21, Elevator L31 | Tape/Linked by L32, Door+Key L33, Pipe L35, Box L50 | levels 1-31 content from the videos (owner); captions exactly as in the table in §6 |
| Hard/SH timers | 3:00 | 3:00 | Hard 3:30 (L34), SH 2:30 (L49) | per-level data |
| rating prompt | – | after L34 | after L34 | both agree |

## 12. The FTUE spec for Arrow Out (what to build)

1. **First launch:** our splash → Loading (logo art + characters + "Loading" with cycling dots) → the notification prompt over
   Loading → a ≈0.1 s cross-fade into **"Levels 1-4"** (no home).
2. **"Levels 1-4"** = 4 boards played back to back, labelled "Levels 1-4". Each board has 3:00 (frozen until its first tap) and
   3 hearts. Between boards: the board-clear colour wave (≈0.4 s) + fade, then the next board builds in (≈0.7 s from the last arrow leaving to the new board).
   Nothing else between boards.
3. **Stage 1 hint:**
   - "Tap to move!" (navy, ≈40 pt display font, centred at y≈289 pt) pops in with an overshoot, and a hand scales in on the middle
     arrow (fingertip at the arrow's upper-middle), both 0.36 s after the board appears;
   - the hand loops its press;
   - on the first tap of any arrow: caption scale-out 0.16 s + hand fade-out 0.12 s; never shown again;
   - no dimming, no input restriction (all 3 arrows are free).
4. **End of stage 4:** the "ARROW OUT!" celebration → win panel "Level 1-4 / Perfect! / Rewards: / 80 / Continue / X".
   Continue → **Level 5** → win → **Level 6** → win → **home**, which pays out the FTUE coins (+120) onto the 1000 starting coins.
5. **From L7:** home after every level.
   - Unlock popups on the first Play of: **L7 Linked Arrows**, **L11 Curtain/Box**, **L21 Pipe**, **L31 Elevator**. Plus whatever
     the levels lane assigns for Door+Key and later phone-only obstacles; the texts are in §6.
   - Hard at 19 and 25, Super Hard at 29, following the video levels. The later curve comes from the phone.
   - The rating prompt after the L34 win. The Weekly Contest tutorial at L50 (phone).
   - The events are simulated offline (owner 02:33). The videos give no unlock levels for them; the phone shows them already live
     at L32. The unlock levels for our build are a design decision for the social-sim/meta lane.
6. **Booster presence:** follow the phone (2 boosters ×3 from the first level). No booster tutorial is seen anywhere.

## 13. Unknowns (not answerable from the videos)

- A wrong tap or a fail during "Levels 1-4": what happens (does the session restart at stage 1, or at the failed stage?). No
  failure occurs in V1.
- Whether input is restricted during the "Tap to move!" hint. No other arrow was tapped, and all were free anyway.
- The press-loop period of the hand (only one cycle was seen before the tap).
- A minimum display time for unlock popups before a tap is accepted.
- Whether X on a win panel differs from Continue (never tapped).
- The v552 unlock levels below L32 for Tape/Linked, Streak Race, Claw Challenge, and the door/key popup text.
