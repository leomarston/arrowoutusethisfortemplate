# Maze Out v552 — ECONOMY (phone sessions 1 + meta, 2026-09-25)

## 1. Coins
- Balance history (phone): 2240 at kickoff (L32) → 4214 at L62. No coins were ever spent by us.
- **Per win** (win panel "Rewards:"): **20** normal · **60** "Hard Level" (L34, L44, L54) · **100** "Super Hard" (L39, L49, L59).
  A heart lost does not reduce it (panel still "Perfect!", +20). Coins fly to the pill on Continue.
- Event coin income seen: Claw Challenge steps 100, 200 (next 300, 400, 500, 600, 2000, 10000 on the ladder); Sky Jump stage 1 = 714
  (5000 shared by 7 winners); Streak Race rank prizes 2000/1000/500/100 (ranks 1/2/3/4–10, paid at the race end — not observed);
  Weekly Contest podium 2000/1000/500.
- L32 → L62 = 30 wins: 24×20 + 3×60 + 3×100 = 960 + Claw 100 + 200 + Sky Jump 714 = 1974 = 4214 − 2240 ✓.
- **Sinks** (all 900 coins, never used): "Add Time" (+30 sec, on Out of Time), "Add Lives" (+3 hearts, on Out of Lives), "Play On"
  (both "Continue?" popups), "Refill" (lives to full, More Lives popup). Nothing else costs coins on v552 (boosters are not sold for coins).

## 2. Lives
- Max **5**. A life is **taken when a level starts** (Play, Try Again) and **given back on a win**; a fail/quit therefore "loses" it.
  "∞" (unlimited lives) is checked at the level start: a level started under ∞ costs nothing even if it fails after ∞ ran out.
- **Regen: 1 life per 30:00**, one continuous clock while lives < 5, phase set when the count first drops below 5:
  | reading (home pill, OCR on lossless shots) | at | → next tick |
  |---|---|---|
  | 4, 19:45 | 05:28:22 | 05:48:07 |
  | 3, 28:42 | 05:49:25 | 06:18:07 |
  | 3, 27:04 (More Lives popup) | 05:51:03 | 06:18:07 |
  | 3, 25:18 | 05:52:49 | 06:18:07 |
  | 3, 18:35 | 05:59:32 | 06:18:07 |
  05:48:07 − 30:00 = 05:18:07 = the moment L62 attempt #2 was started from a 5-Full home → the clock starts at the level START.
  Direct test 06:54:20 → 07:29: a level started from 5 Full and failed 26 min later left the home at **5 Full** (its life came back at
  07:24:20, before the fail was closed) → the life is spent at the start; a fail costs nothing extra; a win refunds it.
  Tick observation at 06:18:07: see §2b.
- Unlimited lives ("∞ mm:ss" on the pill): Claw rewards ∞ 30m/1h/2h…6h, joining Rocket Race (∞ 30m), bundles (∞ 1h…72h). Durations stack
  (∞ 1h + running 30m showed "1h 20m").
- More Lives popup (lives < 5): "Refill [coin] 900" and "+1 Live" for a rewarded video ad.
- Out of lives at home: not reached (we kept ≥ 3).

## 2b. Refill tick (observed 06:17:56–06:18:17, OCR every ~1.03 s; shots meta-098/099/100)
- "3 00:12" 06:17:56.2 · … · "3 00:01" 06:18:06.5 · **"3 Finished" 06:18:07.5** · "4 29:59" 06:18:08.6 · "4 29:51" 06:18:16.6.
- The tick landed on the predicted 06:18:07 (±0.5 s) → **period exactly 30:00**; the next countdown starts at once (29:59 one second later),
  i.e. the clock is continuous, not restarted by the tick.
- Pill text rules: "mm:ss" (28:42); under a minute still "00:ss" (00:01); at zero the word **"Finished"** for ~1 s; heart shows the count
  with a small green "+" badge while lives < 5 (tap → More Lives).

## 3. Boosters (stock at kickoff: hourglass 3, bulb 3)
- Claw rewards: bulb x1 (step 6, claimed after L60 → bulb 4), hourglass x2 (step 11), bulb x2 (13), bulb x1 (17).
- Shop bundles only (x1/x3/x8/x18/x36 of each). Now: hourglass 2, bulb 3 (one of each used by the meta explorer).

## 4. Real-money prices (Turkish store, TL, shop screen; US $ list in web-research.md §IAPs)
| product | content | TL |
|---|---|---|
| Special Offer (90% OFF) | 1 000 coins + 1 of each booster + ∞ 1h | 49,99 |
| Mini Bundle | 2 000 + x1 + ∞ 3h | 249,99 |
| Epic Bundle | 4 000 + x3 + ∞ 6h | 499,99 |
| Elite Bundle ("Popular") | 8 000 + x8 + ∞ 12h | 999,99 |
| Mega Bundle | 20 000 + x18 + ∞ 36h | 2.499,99 |
| Legendary Bundle ("Best Value") | 60 000 + x36 + ∞ 72h | 4.999,99 |
| Coins | 1 000 / 5 000 / 10 000 / 25 000 / 50 000 / 100 000 | 99,99 / 399,99 / 799,99 / 1.499,99 / 2.999,99 / 4.999,99 |
- One continue (900 coins) ≈ 0.9 × the 99,99 TL coin pack ≈ 90 TL, or 45 normal wins' worth of coins.

## 5. Streak / event multipliers (points, not coins)
- Streak multiplier ladder x1 → x5 → x10 → x25 → x100 (one step per consecutive first-try win; any fail → x1).
- Claw Challenge points per win = the multiplier; Streak Race flags per win = the multiplier (141 = one full climb).
- Weekly Contest score = +1 per win.
