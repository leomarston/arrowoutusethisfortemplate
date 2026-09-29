# Maze Out v552 — BOOSTERS (phone, meta explorer, L62, 2026-09-25)

Two boosters, bottom corners of the level screen: green rounded squares (~56 pt) with a red count badge.
Each was used ONCE from owned stock (research). Nothing bought. Stock before → after: **hourglass 3 → 2, bulb 4 → 3**.
No locked booster slot exists on v552 (the older videos had 4 boosters: + yellow arrow, blue dome — PLAN DECISION 02:50).

## 1. BULB = HINT (right, (352,790)) — clip `video/META-L062-bulb-hint.mov`, shots meta-063 (before) / meta-064 (after)
- Usable BEFORE the first tap; using it does **not** start the timer (still 3:00 afterwards).
- Effect (clip, 60 fps, t = clip ms): the view animates from fit (pitch 14.05 pt) to **max zoom** (pitch ≈ 28–29 pt; 28.96 fitted on
  meta-064 while the camera had not fully settled) centred on **one free arrow** (≈0.20 → 0.85 s, ease-in-out, 0.65 s). Then that arrow
  BLINKS GREEN twice: stroke green fades in (0.96 → 1.17 s), holds (1.17 → 1.30), fades out (1.30 → 1.51), off 1.51 → 1.85, second
  blink 1.85 → 2.30, then **stays solid green** (lossless (0,222,0); darker AA rim (0,145,0)) until tapped. Blink period ≈ 0.88 s.
- The hinted arrow had a clear ray (it left when tapped). The view stays zoomed until that arrow leaves; after it left the board was
  back at fit (meta-065) — auto zoom-out on the hinted arrow's exit (INFERRED from the next shot; not in a clip).
- The badge counts down 4 → 3 on use.

## 2. HOURGLASS = TIME FREEZE (left, (40,790)) — clip `video/META-L062-hourglass-freeze.mov`, shot meta-065
- The icon is an ICY HOURGLASS (frosted glass, blue sand) — the players called it "crystal/magnet"; it is an hourglass.
- Used at 05:09:00 with the timer running at 2:11: the timer **froze at once**. An icy hourglass flies from the booster to the HUD
  stopwatch (clip 0.80 → 1.45 s), then: a frost VIGNETTE on all four screen edges (light icy blue, fuzzy), the stopwatch face iced over,
  and a small bar under the timer pill: a counter "10" + a blue progress bar that empties (meta-065 shows "6" with ~60 % bar).
- Timer readings (OCR every ~1.7 s): 2:11 at 05:09:08.2, 09.9, 11.6 → 2:10 at 05:09:13.3 → running again. **Freeze = 10 s** of real time
  after the flight (≈1.5 s); the clock does not tick during the flight either.
- Badge 3 → 2.

## 3. Buying boosters
- Boosters are never sold alone in the shop: only inside bundles ("xN" = N of each booster; x1 … x36, meta.md §3).
- Free sources: Claw Challenge steps (bulb x1 at step 6/17, hourglass x2 at 11, bulb x2 at 13) — meta.md §5.2.
- What tapping a booster at 0 stock does: UNKNOWN (stock never reached 0; we did not spend stock to find out).

## 4. Pinch zoom (L62, before the first tap) — shots meta-058/060–063
- Fit pitch on L62 = **14.05 pt** (26×… cells board, width-bound).
- pinch ×4.0 → pitch **28.04 pt**; a second ×4.0 → still 28.04 → **max = 28.0 pt per cell** (absolute, not relative: player measured
  28.07 on L50 where the board already opened at max).
- pinch ×0.2 → back to 14.05 (= fit), a second ×0.2 → 14.05 → on L62 the **min is the fit size** because it equals the absolute minimum
  (~14.0 pt; player: L47 min 14.0 pt = 0.78× its 17.9 pt fit). So zoom range = clamp(pitch, 14.0, 28.0 pt), fit = min(28, fit-to-board).
- PAN (L62 at max zoom, meta-116..123): one-finger drags pan the board; the pan is clamped so that the **viewport centre stays inside the
  board rectangle** — a board edge can be dragged to the centre of the board viewport (x≈196, y≈435; measured edges 182/205–211 pt
  horizontally, 418/443 pt vertically, ±½ cell) and no further. No rubber-band beyond it was seen in shots (not clip-verified).
- Pinch-out from a panned state returns to the fit SCALE but KEEPS the pan offset (meta-124/125: at fit scale the board corner stayed at the
  viewport centre); pinch-out from a centred view looks centred. Zoom + pan reset to fit/centre on every new level and Try Again.
- Drags and pinches never start the timer; only a tap on an arrow does (a bump also starts it).
- Pinching does not start the timer.
