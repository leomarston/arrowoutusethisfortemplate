# Maze Out v552 — FAIL paths (phone, meta explorer, 2026-09-25, all on LEVEL 62)

Every offer was closed with its X. **0 coins spent** (4214 before and after), nothing bought, no ad watched.
Ledger with exact times: `research/phone-meta-progress.md`. Earlier fails by the players (L32, L33, L47, L52) agree with this file.

## 0. Before the fails (state captured first)
- 04:57 HOME: coins 4214, lives ∞ (≈29 min left), Streak Race **x100** (5h 32m), Claw 122/500 with an **x100** badge, boosters hourglass 3 /
  bulb 4 (after this session: 2 / 3). Rocket Race + Sky Jump not joined.

## 1. The shared popup chain (text exact; each popup = dim board + panel; X is the only way out without paying)
| # | when | title | body | button (never tapped) | X at |
|---|---|---|---|---|---|
| A | timer hits 0:00 | **"Out of Time!"** (white, red outline) | big blue stopwatch, "+30 sec" | green "Add Time [coin] 900" | (350,76), coin pill "4214 (+)" top-left |
| A' | the 3rd heart is lost | **"Out of Lives!"** | big glossy red heart, "+3 Lives" | green "Add Lives [coin] 900" | (350,76), coin pill top-left |
| B | after A/A' when the streak multiplier > x1 | "Continue?" (yellow tab) | purple hexagon token + "You will lose **100** token and your streak!" + chips x1 x5 x10 x25 x100 (current lit orange) | green "Play On [coin] 900" | (362,238) |
| C | next | "Continue?" | "You will lose a life!" + broken red heart | green "Play On [coin] 900" | (362,238) |
| D | next | yellow tab "Level 62" | broken heart, "Level Failed!" | green "Try Again" (196,558) | (362,229); bottom: Streak Race strip "4h 44m", chips with **x1** lit |
- B is **skipped when the multiplier is already x1** (the 2nd timeout, 05:25, went A → C → D).
- B's number: "100 token" at x100 (= the Claw points one more win would have given). Player saw the plain "You will lose your streak!"
  before the Claw Challenge started (L32).
- The older builds (videos, Jul 30) said "Continue? Get 3 lives to keep playing!" + 3 hearts for A'; v552 uses "Out of Lives! / +3 Lives /
  Add Lives 900" (meta-088).
- X on D → HOME (not the level). "Try Again" on D → the level again at once.

## 2. (a) TIMER OUT — L62, twice
- #1 (04:57 start under ∞ lives; timer started by the first tap 05:08:10; hourglass used): 0:00 ≈ 05:11:24 → A (meta-069) → B "100 token"
  (meta-070) → C (meta-071) → D (meta-072) → X → HOME **5 Full** (no life lost: the level was entered while lives were ∞, and ∞ is checked
  at the level START — ∞ had expired ~05:12:50, before the popups were closed). Streak **x100 → x1**; Claw badge x100 → x1; Claw points
  unchanged (122/500).
- #2 (05:18:07 start at 5 lives): 0:00 ≈ 05:25:27 → A → C (no B at x1) → D → X → HOME **4, 19:45** at 05:28:22 → a life was lost.
- #3 (06:54:20 start at 5 Full; clip **META-L062-timer-last-seconds**, 14.2 s of frames, + lossless shots every ~1 s, meta-128..130):
  the in-level timer reads "0:18" … "0:01" "0:00" (m:ss, no leading zero). In the last 18 s there is **no colour change, no pulse, no
  scale** on the digits, the stopwatch icon or the hearts. "0:00" stays on screen **1.61 s** (clip 6.123 → 7.737 s), then popup A
  appears **complete in a single frame** (dim + title + stopwatch + button; no scale-in or fade). A → C → D → X → HOME **5 Full** (see §6).
- The first timeout's last seconds were missed (my shots fired late); #3 covers them.
- The timer is frozen while any popup of the chain is up (it reads 0:00 behind them).

## 3. (b) THREE HEARTS — L62 (05:30:44 start at 4 lives)
- Bump 1 (gap-0 blocked arrow): heart 3 → grey-blue (108,148,220); **the first bump STARTS the timer** (like a first successful tap).
- Re-tapping an arrow that is already RED (bumped) cost **no** heart (05:33, ONE observation from shots only: the runner reported the tap
  on the red stroke, hearts stayed R R grey; the clip of a 2nd try is unusable) → treat as likely, re-verify with a clip.
- Tape bundle with every ray blocked (3 arrows): one tap → the WHOLE bundle + tape slides ~1 cell toward the blockers and back (~0.3 s),
  all three turn red, one ✖ at the contact point, blockers flash red, faint red edge tint → **ONE heart for the bundle**
  (clip META-L062-tape-blocked-bump, 6.6 s; 60 fps track of the pink tape: motion starts ≈1.215 s, the bundle is ~0.5 cell (≈6.8 pt at
  pitch 14.05) forward at ≈1.28 s (contact, ~65 ms), the red SCREEN-EDGE tint appears on that frame at full strength (edge pixels
  (254,155,155)) and fades linearly to white in ≈330 ms (gone at ≈1.63 s); the arrows turn red ≈1.37–1.43 s; the bundle is back at rest
  ≈1.46–1.48 s. Here the blockers were 0 cells ahead, so the travel = the gap to the blocker's stroke edge (≈0.5 cell).
- Heart 3 of 3 (05:42, 1:59 left): → A' "Out of Lives!" (meta-088) → C (meta-089; no B at x1) → D (meta-090).
  The HUD timer froze at 1:59 behind the popups.
- Hearts HUD colours (lossless): full (252,58,42) centre / (243,39,26) mean; lost = (108,148,220) grey-blue, the pill's own colour.

## 4. RESTART DIFF (Try Again, 05:46:17)
- D "Try Again" → the SAME level instantly (no home), fresh 3:00 + 3 hearts, boosters keep their stock.
- Start boards compared pixel by pixel (runner shots, board band y 125–745 pt + HUD): meta-058 (1st entry) = meta-074 (2nd, from home) =
  meta-082 (3rd, from home) = meta-091 (Try Again): **max difference 0** → levels are fully deterministic (same arrows, doors, boxes,
  counters, key positions, same fit zoom).
- A retry costs a life like any start (see §6).

## 5. (c) QUIT
- In-level **back button** (38,88), even before the first tap → "Quit Level?" (yellow tab) / "You will lose a life!" / broken heart /
  red **"Quit"** (196,540) / X (362,238) (meta-075). X = back to the level; the timer had not started and stays 3:00.
- Pause panel **"Quit"** (269,530) → the same "Quit Level?" popup (meta-092) → "Quit" → **D "Level 62 / Level Failed! / Try Again"**
  with the Streak Race strip (meta-093) → X → HOME.
- Quitting counts as a fail (streak reset, life lost). No coins offer on the quit path.

## 6. LIVES accounting (what a fail costs, and when)
| time | event | lives shown after |
|---|---|---|
| 04:57 | start L62 while ∞ | ∞ |
| 05:15:42 | fail #1 closed (∞ expired 05:12:50) | **5 Full** |
| 05:18:07 | start #2 | (in level) |
| 05:28:22 | after fail #2 | **4, 19:45** → next life 05:48:07 = start #2 + 30:00 |
| 05:30:44 | start #3 | |
| 05:46:37 | Try Again start #4 | |
| 05:48:07 | regen tick (predicted) | |
| 05:49:25 | after quit | **3, 28:42** → next life 06:18:07 = 05:48:07 + 30:00 |
- Model that fits every number: **a life is taken when a level STARTS (Play or Try Again) and given back on a win**; while below 5 a
  30:00 regen clock runs continuously (its phase was set when the count first dropped below 5, i.e. at start #2). Fails and quits add no
  extra cost. Cross-checks with the players' ledgers: L32 #1 was entered at 00:17 and failed at 00:50 → its life had already regenerated
  at 00:47 → "5 Full" (the session-1 puzzle solved). L47 #1: "4, 15:56" at 02:50 → start 02:35:56 (player part 2 began 02:35). L52 #1:
  "4, 20:39" at 03:29 → start 03:19:39 (L51 was won at 03:19). The players' "~20 min per life" were partial countdowns.
- **Direct confirmation (07:29):** L62 started 06:54:20 from 5 Full → failed on time 07:20:35 → popups closed 07:28:47 → home "5 Full".
  The start took the life, the 30:00 clock gave it back at 07:24:20, and the fail took nothing more.
- Refill confirmation at the tick: see economy.md §2b.

## 7. Streak / event state before → after
- Streak Race multiplier x100 → **x1** at the first fail (strip on D, home badge). The next win gives x5 (player: L47 retry, L52 retry).
- Claw Challenge: points unchanged by a fail (122/500 before and after); the multiplier badge dropped to x1.
- Rocket Race / Sky Jump: not joined, unaffected. (Sky Jump rule: "If you fail a level, you will fail the challenge!".)
- Weekly Contest: score unchanged (only wins count).
