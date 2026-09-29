# Maze Out — recorded levels (phone session 1, player part 1)

Conventions: shots = research/shots/NNN-*.png (1178x2556 px, pt = px*393/1178). Level JSON = research/levels/Lnnn.json (cells [col,row]
tail→head, dir = head direction; cols/rows = bounding box of arrow cells). Board read by research/bot/bot.py (overlay in research/bot/overlay/).

## Input model / global facts (measured)
- TAP FIRES ON RELEASE (touch-up): a 5.0 s press on a free arrow (L32 arrow 31) left it in place for the whole hold (USB grab during the
  hold: shots/009); it was already leaving 0.23 s after lift-off (shots/010). A tap ripple (grey disc) is drawn at the touch point.
- An exiting arrow turns LIGHT BLUE and slides along its own path; its vacated cells show a grid of faint light-blue dots (not black ink).
- Two taps 770 ms apart (A = L32 #35 free, B = #17 whose ray was blocked only by A): both accepted, no heart lost (clip S1-P02-queued-tap-250ms.mov).
  NOTE: the phone runner's 'taps X;Y GAP' spaces taps ~0.5-0.8 s apart whatever GAP is (XCUITest per-tap overhead) — shorter offsets untested.
- PAUSE freezes the timer (L32 sat paused 00:20→00:37 and lost ~0-8 s including resume overhead). Double-tap on empty board does NOT reset zoom.
- Zoom: pinch in/out works during play; board can be zoomed below its fit size (L32: 0.786x fit, pitch 14.04 pt vs 17.87 pt at fit).
- Recording caveat: the phone 'rec' movies contain only ~2-3 s of frames (the capture's edit list is short and frames stop early);
  research/tools/frames2 decodes every sample (use it instead of 'phone frames').

## L32
- Tag: none. Timer 3:00. Hearts 3. Board 20x20 cells (square, no silhouette), 53 arrows, pitch 17.87 pt at fit (stroke 3.7 pt).
- Obstacles: 4 pink TAPES, each binding 4 parallel straight arrows (top-left 4x → right; top-right 4x ↓; bottom-left 4x ↑; bottom-right 4x →).
- JSON: research/levels/L032.json (from shots/003-L32-start.png). Overlay: research/bot/overlay/L032-start.png.
- Attempt 1: FAILED, out of time (probing), 3 hearts left. Popups: see flows.md. Attempt 2: below.
- Attempt 2 (Try Again → same board, fit zoom, timer 3:00, hearts 3): WON by the bot in 18 rounds, 1:01 left, 3/3 hearts (bot/log.jsonl).
  The timer still read 3:00 in the bot's first shot a few seconds after the board appeared (bot/tmp/L032-r01.png) → timer seems to start
  at the first tap (to verify on L33).
  TAPE (pink, 4 parallel arrows): ONE tap on any bundled arrow (tapped the tail of the 2nd) sent ALL FOUR out together and the tape went
  with them (shots/019, 3 hearts kept). Seen 4 times (all 4 tapes of L32), each time with all four rays clear. Not yet tested: tapping a
  bundle when only some of its arrows are clear.
  Win: popup "Level 32" / "Perfect!" / "Rewards:" coin stack "20" / green "Continue" / X; Streak Race banner below with x5 lit (was x1)
  (shots/020). Continue → Claw Challenge event screen (first time, auto-scrolling reward ladder 1→20; shots/021-025) → X → home LEVEL 33,
  coins 2260 (+20), lives 5 "Full" (the failed attempt's "You will lose a life!" did not leave a missing life), Claw bar 0/1 (shots/026).

## L33
- Tag: none. Timer 3:00 (did NOT start at load: still 3:00 at +1.3 s and +5.3 s, shots/027 + bot/tmp/L033-t5.png → the timer starts
  at the FIRST TAP). Hearts 3. Board 20x20 cells, 20 visible arrows at start + arrows hidden under DOORS.
- Obstacles: 5 LOCKED DOORS (blue slatted shutters, orange frame, purple inner frame, purple hexagon lock with keyhole) in a staircase
  along the bottom (door heights grow left→right, the rightmost reaches the top row); 2 KEYS (gold key hanging on a purple ring) on two
  arrows (top-left ↓ arrow; a ↑ arrow at mid-left).
- KEY RULE (clip S1-L33-key-first.mov, frames 0-3 s): tap the key arrow → it turns blue and leaves; the key drops off, flies (spinning)
  to the LEFTMOST/LOWEST locked door, enters its keyhole (~1.0 s after the tap), turns, and the door SHATTERS into purple/blue/orange
  fragments (~1.2-1.6 s after the tap), revealing the arrows that were under it (bottom-left: a ← arrow + a small ↓ hook). Door cells
  block rays like arrows (bot rule, conservative; the top-left ↓ key arrow stayed blocked by the first door until it broke).
  Attempt-2 round shots (bot/tmp/L033-011032-r01..r16): doors opened strictly left→right (door1 r03, door2 by r05, door3 by r07,
  door4 r11, door5 by r13); every door hid the key arrow for the next door
  (bot round shots bot/tmp/L033-*-rNN.png).
- JSON: research/levels/L033.json (start state; arrows under doors not yet included — see bot/tmp round shots for the revealed ones).
- Attempt 1: FAILED out of time (old slow bot: ~7 s per round). Popups identical to L32; streak reset x5 → x1; this fail cost a life (5 → 4, refill 11:20).
- Attempt 2: WON by the fast bot (play2: whole greedy schedule in one taps call) with 2:08 left, 3/3 hearts. "Perfect!" +20 coins, streak x5.
  After Continue: "Congratulation(s)!" ∞-heart "30m" + "Tap to Claim" (Claw Challenge step 1) → home: lives ∞ 29:57, Claw bar 0/200 →
  100 coins, LEVEL 34 plate RED with a "Hard Level" ribbon over a RED Play button (shots/033-035).

## L34
- Tag: Hard Level. Timer 3:30. Hearts 3. Board 25x35 cells (bounding box of arrow+obstacle cells), pitch 14.562 pt at fit zoom (stroke 3.0 pt).
- Arrows at start (visible): 76 (dirs {'left': 17, 'up': 14, 'down': 26, 'right': 19}; length min/median/max 2/6/30 cells).
- Obstacles: {'door': 4, 'key': 2}; door cells 278
- JSON: research/levels/L034.json (shot research/shots/036-L034-start.png). Bot: 116 tap entries over 9 rounds (bot/log.jsonl).
- Start shot shots/036-L034-start.png. HARD LEVEL: HUD turns RED (Level tab, back + pause buttons), timer 3:30.
- Obstacles: 4 doors (top horizontal, bottom horizontal, left vertical, right vertical, each with a purple hexagon lock) + 2 key arrows (both → with the key on a horizontal segment).
- Result: WON by bot play2 with 2:03 left, 3/3 hearts, no heart lost. Win popup: red panel with a 'Hard Level' ribbon flanked by skulls over the yellow 'Level 34' tab, 'Perfect!', 'Rewards:' coins '60', Continue; Streak Race x10 lit (shots/037).

## L35
- Tag: none. Timer 3:00. Hearts 3. Board 12x18 cells (bounding box of arrow+obstacle cells), pitch 28.092 pt at fit zoom (stroke 6.01 pt).
- Arrows at start (visible): 20 (dirs {'right': 11, 'down': 4, 'up': 5}; length min/median/max 2/6/41 cells).
- Obstacles: {'pipe': 1}
- JSON: research/levels/L035.json (shot research/shots/042-L035-start.png). Bot: 18 tap entries over 1 rounds (bot/log.jsonl).
- FEATURE UNLOCK (one-shot) before the board: dim overlay 'Pipe!' / 'Unlocked!' / U-pipe icon with an orange '3' cap / card 'Pass arrows through the PIPE to break it!' (shots/040); tap anywhere → board (shots/041 = start state, copied to 042).
- PIPE: light-blue tube 1 cell wide, orange rims at both mouths, orange counter box with a white number ('2' here) on the tube. Here: mouth at the right end of the top row facing LEFT, tube runs right then down the right side, exit mouth facing DOWN below the board's right column. Two → arrows on the top row aim at the mouth.
- PIPE RULE (2 observations): an arrow whose ray enters the mouth travels THROUGH the tube and leaves from the other mouth (no heart lost); each passage decrements the counter (2→1: shots/043; clip video/S1-L35-pipe-first.mov); at 0 the pipe breaks and disappears entirely (shots/044; clip video/S1-L35-pipe-break.mov); its cells then show vacated-cell dots.
- Timer check: the first tap started the clock (3:00 → 2:53 after one tap + ~7 s of recording overhead).
- Result: WON (pipe arrows by hand, then 18 arrows in ONE bot batch) with 2:19 left, 3/3 hearts. 'Perfect!' +20 coins; Streak Race x25 lit (shots/045).

## L36
- Tag: none. Timer 3:00. Hearts 3. Board 16x23 cells (bounding box of arrow+obstacle cells), pitch 21.836 pt at fit zoom (stroke 4.67 pt).
- Arrows at start (visible): 31 (dirs {'up': 7, 'right': 12, 'left': 5, 'down': 7}; length min/median/max 3/6/42 cells).
- Obstacles: {'pipe': 2}
- JSON: research/levels/L036.json (shot research/shots/047-L036-start.png). Bot: 31 tap entries over 5 rounds (bot/log.jsonl).
- Obstacles: 2 PIPES on the left edge, both counters '1': upper mouth faces RIGHT at the end of a long ← arrow's row, tube runs left then UP to an exit facing up; lower mouth faces RIGHT at the next row's long ← arrow, tube runs left then DOWN to an exit facing down (start shot shots/047).
- Pipe rule confirmed again (2 more observations): a ← arrow entered each mouth, came out of the other end, counter 1→0 and the pipe shattered into blue fragments (the break animation lasts ~1-2 s; bot retries its read meanwhile).
- Result: WON with 2:24 left, 3/3 hearts (bot + pipe-aware planner). End: full-screen 'MAZE OUT!' logo + confetti + fireworks (shots/049), then popup 'Level 36 / Perfect! / 20 / Continue', Streak Race x100 lit (shots/050).

## L37
- Tag: none. Timer 3:00. Hearts 3. Board 22x30 cells (bounding box of arrow+obstacle cells), pitch 16.381 pt at fit zoom (stroke 3.34 pt).
- Arrows at start (visible): 14 (dirs {'right': 6, 'up': 2, 'down': 5, 'left': 1}; length min/median/max 5/13/36 cells).
- Obstacles: {'door': 1, 'key': 1}; door cells 440
- JSON: research/levels/L037.json (shot research/shots/052-L037-start.png). Bot: 49 tap entries over 11 rounds (bot/log.jsonl).
- Start shots/052 (timer 3:00, normal HUD). Obstacles: 3 DOORS (one wide door across the top half, two doors side by side below it) + 1 key arrow (bottom-left) + arrows in the lower part; the doors hide the rest.
- Result: WON by go.py/play2 with 2:06 left, 3/3 hearts; 'Perfect!' +20; Streak x100 (shots/054). Home after: Claw 140/200 ('+100' capsule, x100), coins 2380, LEVEL 38 (shots/055).

## L38
- Tag: none. Timer 3:00. Hearts 3. Board 20x22 cells (bounding box of arrow+obstacle cells), pitch 17.868 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 42 (dirs {'up': 15, 'left': 9, 'down': 14, 'right': 4}; length min/median/max 3/6/59 cells).
- Obstacles: {'pipe': 1, 'tape_pink': 3}
- JSON: research/levels/L038.json (shot research/shots/056-L038-start.png). Bot: 39 tap entries over 9 rounds (bot/log.jsonl).
- Start shots/056 (timer 3:00). Obstacles: 1 PIPE along the top edge with counter '4' (mouth at the left end on the left edge, tube runs right along the top then down on the right) + small PINK TAPES binding 2 adjacent parallel vertical arrows (3 such 2-bundles, mid-board).
- Result: WON by go.py/play2 with 2:23 left, 3/3 hearts; 'Perfect!' +20; Streak x100 (shots/058). Home after: Claw bar reset to '37/300' with an ∞-heart 30m reward icon (the 200 step passed), coins 2400, LEVEL 39 with a 'Super Hard' ribbon over a PURPLE Play button (shots/059).

## L39
- Tag: Super Hard. Timer 3:00. Hearts 3. Board 24x34 cells (bounding box of arrow+obstacle cells), pitch 15.126 pt at fit zoom (stroke 3.34 pt).
- Arrows at start (visible): 102 (dirs {'right': 14, 'left': 34, 'up': 33, 'down': 21}; length min/median/max 2/6/40 cells).
- Obstacles: none
- JSON: research/levels/L039.json (shot research/shots/061-L039-start.png). Bot: 102 tap entries over 3 rounds (bot/log.jsonl).
- SUPER HARD: Play button on home is PURPLE with a 'Super Hard' ribbon; in-level HUD is PURPLE (Level tab, back/pause buttons). Timer 3:00 (start shots/061). Dense maze, no obstacles.
- Result: WON by go.py/play2 (3 rounds: 40 + 22 taps in the last two) with 1:53 left, 3/3 hearts; popup: purple panel, 'Super Hard' ribbon with skulls, 'Perfect!', '100' coins (shots/063). Home after: coins 2500→2520 (Claw 200-step reward +100 arrived before L39), Claw 140/300 (+100), a new red 'Join' badge under the Streak Race badge (left side), LEVEL 40 (shots/064).

## L40
- Tag: none. Timer 2:30. Hearts 3. Board 20x27 cells (bounding box of arrow+obstacle cells), pitch 17.871 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 42 (dirs {'left': 18, 'right': 11, 'down': 10, 'up': 3}; length min/median/max 3/6/31 cells).
- Obstacles: none
- JSON: research/levels/L040.json (shot research/shots/071-L040-start.png). Bot: 42 tap entries over 2 rounds (bot/log.jsonl).
- Start shots/071: timer 2:30 (!), normal HUD. The board is a SILHOUETTE (figure-like shape: ring/loops on top, a band of zig-zag rows in the middle, wide rows at the bottom), no obstacles.
- Result: WON by go.py/play2 with 2:03 left, 3/3 hearts; 'Perfect!' +20; x100 (shots/073). After Continue: Sky Jump screen 'Levels 0/5' + 'Tap to Continue' (shots/074) → tap → home: Sky Jump badge '1', Claw 240/300, coins 2640, LEVEL 41 (shots/075).

## L41
- Tag: none. Timer 2:30. Hearts 3. Board 20x26 cells (bounding box of arrow+obstacle cells), pitch 17.868 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 27 (dirs {'right': 10, 'up': 10, 'down': 7}; length min/median/max 3/6/43 cells).
- Obstacles: {'pipe': 2, 'key': 1, 'door': 1}; door cells 200
- JSON: research/levels/L041.json (shot research/shots/076-L041-start.png). Bot: 48 tap entries over 11 rounds (bot/log.jsonl).
- Start shots/076: timer 2:30. Obstacles: 2 PIPES (counters 3 and 3): top pipe mouth on the top row's right end, tube left along the top then down the left edge; bottom pipe mouth at the top of the right edge, tube down then left along the bottom to a mouth facing left; a wide DOOR across the middle; a KEY on a top-left U-shaped arrow (its ring touches the top pipe; the reader splits touching blobs since this level).
- Result: WON by go.py/play2 with 1:38 left, 3/3 hearts; +20 (shots/078). Sky Jump progress screen auto-dismissed; home: Claw 37/400 (next reward 200 coins), Sky Jump badge 2, lives 5 Full, LEVEL 42 (shots/079).

## L42
- Tag: none. Timer 3:00. Hearts 3. Board 22x30 cells (bounding box of arrow+obstacle cells), pitch 16.383 pt at fit zoom (stroke 3.34 pt).
- Arrows at start (visible): 45 (dirs {'up': 20, 'left': 11, 'down': 11, 'right': 3}; length min/median/max 2/6/43 cells).
- Obstacles: {'pipe': 4}
- JSON: research/levels/L042.json (shot research/shots/081-L042-start.png). Bot: 45 tap entries over 17 rounds (bot/log.jsonl).
- Start shots/081: timer 3:00. Board = a shield/face-like silhouette. Obstacles: 4 U-shaped PIPES with both mouths facing the board: two at the top (mouths facing DOWN, counters 4 and 4) and two at the bottom (mouths facing UP, counters 3 and 3). Arrows enter one leg and come out of the other leg (U-turn).
- Result: WON with 1:47 left, 3/3 hearts (one bot stop: a read taken while an arrow was still flying out of a pipe → 'stuck'; the bot now re-reads 3x before calling a stop). +20 (shots/083). Sky Jump screen: Levels 2/5, Players 64/100 (shots/084).

## L43
- Tag: none. Timer 3:00. Hearts 3. Board 20x32 cells (bounding box of arrow+obstacle cells), pitch 17.868 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 27 (dirs {'down': 5, 'right': 9, 'left': 6, 'up': 7}; length min/median/max 3/6/45 cells).
- Obstacles: {'key': 1, 'door': 2}; door cells 320
- JSON: research/levels/L043.json (shot research/shots/085-L043-start.png). Bot: 59 tap entries over 6 rounds (bot/log.jsonl).
- Start shots/085: timer 3:00. Obstacles: 2 wide DOORS stacked across the whole bottom half + 1 KEY arrow (→, lower right of the maze).
- Result: WON with 2:05 left, 3/3 hearts; +20 (shots/087). Sky Jump screen 'Levels 4/5', 'Players 47/100' (shots/088). Home: lives ∞ 22:57, Claw 240/400, coins 2700, Sky Jump badge 4, LEVEL 44 'Hard Level' red Play (shots/089).

## L44
- Tag: Hard Level. Timer 3:00. Hearts 3. Board 25x36 cells (bounding box of arrow+obstacle cells), pitch 14.566 pt at fit zoom (stroke 3.0 pt).
- Arrows at start (visible): 91 (dirs {'left': 37, 'up': 24, 'right': 21, 'down': 9}; length min/median/max 3/4/44 cells).
- Obstacles: {'pipe': 2, 'tape_pink': 4}
- JSON: research/levels/L044.json (shot research/shots/090-L044-start.png). Bot: 83 tap entries over 15 rounds (bot/log.jsonl).
- HARD (red HUD), timer 3:00 (start shots/090). Two tall halves: LEFT half framed by a PIPE (counter 8): mouth at the top-left facing down, tube along the top and down the half's right side to a mouth at the bottom facing down; RIGHT half framed by a PIPE (counter 3): mouth at the bottom-left facing left (with the counter box), tube along the bottom and up the right edge to a mouth at the top-right facing up. 4 PINK TAPES each binding 3 parallel arrows (corners of the right half).
- Reader note: the bottom-left tape touches the right pipe's counter box; since L44 touching colour blobs are split by hue (tape/key/rim/counter) before classification.
- Result: WON with 1:28 left, 3/3 hearts; Hard popup +60 (shots/092). Home: Sky Jump badge 5, Claw 340/400, lives ∞ 15:02, LEVEL 45 (shots/093).

## L45
- Tag: none. Timer 2:30. Hearts 3. Board 15x19 cells (bounding box of arrow+obstacle cells), pitch 23.115 pt at fit zoom (stroke 5.0 pt).
- Arrows at start (visible): 26 (dirs {'up': 11, 'left': 6, 'down': 7, 'right': 2}; length min/median/max 4/7/47 cells).
- Obstacles: none
- JSON: research/levels/L045.json (shot research/shots/097-L045-start.png). Bot: 26 tap entries over 1 rounds (bot/log.jsonl).
- Start shots/097: timer 2:30, square-ish maze, no obstacles.
- Result: WON with 2:15 left, 3/3 hearts; +20 (shots/099). Then Claw Challenge step reward 'Congratulations!' 200 coins 'Tap to Claim' (shots/100; the claim needs a tap on the text/centre — taps at y=785 did nothing). Claw bar reset 40/300.

## L46
- Tag: none. Timer 3:00. Hearts 3. Board 24x32 cells (bounding box of arrow+obstacle cells), pitch 15.118 pt at fit zoom (stroke 3.34 pt).
- Arrows at start (visible): 56 (dirs {'left': 19, 'right': 13, 'down': 20, 'up': 4}; length min/median/max 2/3/34 cells).
- Obstacles: {'door': 2, 'key': 4}; door cells 410
- JSON: research/levels/L046.json (shot research/shots/102-L046-start.png). Bot: 102 tap entries over 9 rounds (bot/log.jsonl).
- Start shots/102: timer 3:00. Obstacles: 4 DOORS (a wide door across the top, two small doors left/right in the middle band, a wide door across the middle) + 4 KEY arrows (one vertical ↓ key near the top, two horizontal keys mid-board, one key at the bottom-left touching the wide door above it).
- Reader: the bottom-left key touching a door broke the blob split until the distance-limited core assignment (bot.label_blobs) — now all 11 recorded starts read with 0 anomalies. One mid-level stop was a read taken during an exit animation (a 2-cell remnant); finished with --ignore-anomalies.
- Result: WON with 1:14 left, 3/3 hearts; +20 (shots/104). Home after: LEVEL 47, coins 3694 (+20 animating), lives 5 Full, Claw 140/300 (next ∞ 1h), Sky Jump 'Join', Streak Race 7h 31m (shots/105).

## Session summary (player part 1, 00:23-02:56)
- Recorded 15 levels L32-L46 (JSON for each start state, 0 reader anomalies on all 15 with the final bot.py). All 15 WON, 0 hearts lost
  in any win. Failed attempts: L32 #1 and L33 #1, both OUT OF TIME (probing / the first slow bot); every continue offer declined.
- Timers seen: 3:00 (most), 3:30 (L34 Hard), 2:30 (L40, L41, L45). Tags: Hard Level L34, L44; Super Hard L39.
- Obstacles met: pink tape (L32, L38, L44), door+key (L33, L34, L37, L41, L43, L46), pipe (unlock at L35; L35, L36, L38, L41, L42, L44).
- NOT measured this session (need a later probe session): the bump (no deliberate wrong tap was made), hit tolerance, head-vs-tail-vs-middle
  (only: a tap on a tail cell works, L32 tape), swipe, exit speed T(d) (clips exist: video/S1-P01, S1-P02, S1-L33-key-first,
  S1-L35-pipe-first, S1-L35-pipe-break — decode with research/tools/frames2), rainbow trail (none seen: exiting arrows are light blue),
  boosters (never used), zoom limits.

## L47
- Tag: none. Timer 3:00. Hearts 3. Board 20x30 cells (bounding box of arrow+obstacle cells), pitch 17.87 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 29 (dirs {'down': 7, 'up': 8, 'left': 4, 'right': 10}; length min/median/max 2/7/44 cells).
- Obstacles: {'door': 2, 'key': 1}; door cells 300
- JSON: research/levels/L047.json (shot research/shots/106-L047-start.png). Bot: 93 tap entries over 10 rounds (bot/log.jsonl).
- Start shots/106 (timer 3:00, not running until the first tap): 2 DOORS (checkerboard: top-left and bottom-right quadrants) + 1 KEY arrow (upper-right quadrant, key hanging on a vertical up-arrow).
- PROBES (attempt 1, part-2 player): (a) ZOOM before the first tap: a pinch does NOT start the timer (still 3:00 4 s after). Zoom range measured by repeated pinches: MAX pitch 28.07 pt (stroke 6.0 pt) = 1.568x the fit pitch 17.90 pt; MIN pitch 14.01 pt (stroke 3.0 pt) = 0.783x fit (ink bbox 275.9 vs 351.2 pt wide = 0.786x). Max/min = 2.0. At min zoom the board is centred. (b) HEAD tap: a tap on the head triangle (tip area) of the long 44-cell frame arrow sends it out (clip video/S1-L47-headtap-long-exit.mov; timer started at this tap). (c) HIT TOLERANCE: a tap 10 pt left of a vertical stroke centre (no other ink within 1 cell) sends the arrow (shots/108); a tap 15 pt above a horizontal stroke centre (empty board margin above) also sends it (shots/109). So the hit radius is >= 15 pt (~0.84 pitch) when no other arrow is nearer. (d) BUMP (deliberate, clip video/S1-L47-bump-1.mov): tapping a blocked 3-cell arrow (head 3 empty cells from its blocker) cost 1 HEART (3rd heart turns grey-blue), and the arrow turns RED (238,10,19) and STAYS red for the rest of the level (still red 28 s later; it is still a normal arrow: tapped later when free, it leaves). Bot patched: red strokes are ink. (e) SWIPE on an arrow body does NOT trigger it: a 52 pt horizontal swipe starting on a free arrow PANNED the whole board ~30 pt to the right (the pan persisted; board partly off-screen) — a swipe back of the same length restored it.
- Attempt 1 FAILED — OUT OF TIME with 2 hearts (probing cost ~2 min, then the bot stopped on an arrow cut by the screen edge after the pan). Declined everything, NO coins spent: 'Out of Time!' (+30 sec, Add Time 900) X → 'Continue?' NEW TEXT 'You will lose 100 token and your streak!' (purple hexagon token icon, streak chips x1 x5 x10 x25 x100 with an animated x1 chip, shots/113) 'Play On 900' X → 'Continue?' 'You will lose a life!' (shots/114) X → 'Level 47 / Level Failed! / Try Again' + Streak Race banner 7h 12m, x1 lit (shots/115). Life 5 -> 4.
- Attempt 2 (Try Again, shots/116 = same start): WON by go.py --retry in 10 rounds with 2:07 left, 3/3 hearts; 'Perfect!' +20; Streak Race x5 (shots/119). Home: coins 3734, lives 4 (refill 15:56), Claw 141/300 (x5 badge) — the failed level did NOT remove 100 tokens from the bar (140 -> 141 = +1 for the x1 win), LEVEL 48 (shots/120).
- INCIDENT: shots/117 (1-2 s after the last bot taps) shows the iOS CONTROL CENTER open over the 'MAZE OUT!' win animation (header 'Maze Out! Oyun Katmani' = Game Overlay), closing by itself in shots/118; nothing was toggled (purple modules are the logo shining through the glass). Cause unknown (no swipe was sent; all taps were at y 448-680 pt).

## L48
- Tag: none. Timer 2:30. Hearts 3. Board 20x24 cells (bounding box of arrow+obstacle cells), pitch 17.87 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 47 (dirs {'up': 15, 'left': 5, 'right': 10, 'down': 17}; length min/median/max 2/6/42 cells).
- Obstacles: {'pipe': 3}
- JSON: research/levels/L048.json (shot research/shots/121-L048-start.png). Bot: 47 tap entries over 15 rounds (bot/log.jsonl).
- Start shots/121: timer 2:30. Three vertical maze columns, each capped by a U-shaped PIPE (counter 4 each; both mouths face DOWN into the column below: left and middle pipes have the counter box on the LEFT leg, the right pipe on the RIGHT leg). Clip video/S1-L48-play-intro.mov = Play tap → level intro.
- PROBE: deliberate BUMP #2 (clip video/S1-L48-bump-2.mov): a right-pointing 8-cell arrow with 1 empty cell before its blocker → -1 heart, arrow turns red and stays red. Bot fix: the red arrow's anti-aliased rim (249,179,183) is now ink too (it was read as a thin 'unknown' blob → one bot stop, game paused, no time lost).
- Result: WON with 0:55 left, 2/3 hearts (the one lost = the probe). Popup still says 'Perfect!' with a heart lost (+20). Streak Race x10 (shots/124). Home: LEVEL 49 'Super Hard' (purple Play), coins 3734 (+20 animating), lives 4 (10:58), Claw 146/300 (+5 = x5 streak at the win) with a NEW strip under the bar 'x10 | x1 x5 x10 x25 x100' (shots/125).

## L49
- Tag: Super Hard. Timer 2:30. Hearts 3. Board 24x36 cells (bounding box of arrow+obstacle cells), pitch 15.127 pt at fit zoom (stroke 3.34 pt).
- Arrows at start (visible): 59 (dirs {'right': 29, 'left': 11, 'up': 6, 'down': 13}; length min/median/max 2/8/48 cells).
- Obstacles: {'door': 1, 'pipe': 5, 'key': 2}; door cells 168
- JSON: research/levels/L049.json (shot research/shots/126-L049-start.png). Bot: 69 tap entries over 14 rounds (bot/log.jsonl).
- SUPER HARD (purple HUD). Timer 2:30 (!). Start shots/126 (intro clip video/S1-L49-play-intro-superhard.mov). Obstacles: one wide DOOR across the top; 5 PIPES: top-right U (counter 4, mouths facing LEFT), left U (counter 4, mouths RIGHT), right-middle U (counter 3, mouths LEFT), left-middle U (counter 3, mouths RIGHT), bottom U (counter 3, mouths UP); 1 KEY arrow at the top-left whose key body touches the left pipe's counter box.
- READER: the touching key+pipe broke the key arrow into pieces; fixed with a per-level override research/bot/overrides/L049.json (key arrow tail (1,21)->(1,22)->(2,22)->(3,22)->head (4,22) RIGHT, verified on a grid-labelled crop) + a small purple blob = key ring rule. The start JSON includes it (59 arrows).
- Revealed state after the door opened: research/levels/L049-open1.json (25 arrows left on the board at that read; the arrows that were under the door are the ones inside its rectangle).
- Result: WON by go.py in 23 rounds with ~0:56 left, 3/3 hearts. Popup: purple 'Super Hard' ribbon with skulls, 'Perfect!', 100 coins; Streak Race x25 (shots/128). Home: LEVEL 50 normal, coins 3754 (+100 animating), lives 4 (04:15), Claw 156/300 (+10 = x10), streak strip x25 (shots/129).

## L50
- Tag: none. Timer 3:00. Hearts 3. Board 10x18 cells (bounding box of arrow+obstacle cells), pitch 28.07 pt at fit zoom (stroke 6.01 pt).
- Arrows at start (visible): 16 (dirs {'left': 4, 'up': 4, 'down': 3, 'right': 5}; length min/median/max 4/6/23 cells).
- Obstacles: {'box': 1, 'box_part': 6}
- JSON: research/levels/L050.json (shot research/shots/135-L050-start.png). Bot: 14 tap entries over 2 rounds (bot/log.jsonl).
- FEATURE UNLOCKS on the way in: (1) first Play tap on LEVEL 50 home → 'Weekly Contest' tutorial (see flows.md; shots/130-133); (2) level open → 'Box! / Unlocked!' card: purple rounded-square icon with a silver ring counter '5', cream card 'Clear required amount of arrows to break the BOX!' (BOX in blue) (shots/134); tap anywhere → level, timer not started.
- Start shots/135: timer 3:00; small maze (16 arrows) at pitch 28.07 pt = the same absolute pitch as the MAX zoom measured on L47 → a small board opens at the zoom CAP, so max zoom is an absolute cell size (~28.07 pt), not a multiple of fit. Below the maze a wide purple BOX (10 cols x 3 rows, bolts in the corners, silver ring counter '10' in the centre).
- BOX RULE (2 observations): every arrow that is cleared anywhere on the board decrements the counter by 1 (after 9 clears it read '1', shots/136); the 10th clear broke it (clip video/S1-L50-box-break.mov; shots/137): the slab vanished and its cells show the light-blue vacated dots, NOTHING was hidden under it. Before breaking, the box cells block rays (bot assumption; no arrow was tapped into it).
- Result: WON with 1:15 left, 3/3 hearts; +20; Streak Race x100 (shots/138). Win sequence clips: video/S1-L50-win-seq-1.mov (last tap → MAZE OUT! → popup) and video/S1-L50-win-seq-2-continue.mov (Continue → home). Home: LEVEL 51, coins 3874, lives 5 Full, Claw 181/300 (+25 = x25) (shots/139).

## L51
- Tag: none. Timer 3:00. Hearts 3. Board 15x21 cells (bounding box of arrow+obstacle cells), pitch 23.123 pt at fit zoom (stroke 5.0 pt).
- Arrows at start (visible): 24 (dirs {'down': 4, 'left': 1, 'right': 13, 'up': 6}; length min/median/max 2/9/29 cells).
- Obstacles: {'box': 3, 'box_part': 7}
- JSON: research/levels/L051.json (shot research/shots/140-L051-start.png). Bot: 24 tap entries over 4 rounds (bot/log.jsonl).
- Start shots/140: timer 3:00, pitch 23.12 pt. Three BOXES in a staircase along the bottom-right (counters 8 / 16 / 23; 24 arrows on the board).
- BOX RULE confirmed: ALL boxes count down together — after 8 clears the '8' box broke (nothing under it) and the others read 8 and 15 (shots/141).
- Result: WON with 1:49 left, 3/3 hearts; +20; x100 (shots/143). Home: LEVEL 52, coins 3874 (+20 animating), lives 5 Full, Claw 281/300 (+100) (shots/144).

## L52
- Tag: none. Timer 3:00. Hearts 3. Board 13x16 cells (bounding box of arrow+obstacle cells), pitch 26.199 pt at fit zoom (stroke 5.67 pt).
- Arrows at start (visible): 15 (dirs {'down': 4, 'up': 3, 'left': 6, 'right': 2}; length min/median/max 2/7/42 cells).
- Obstacles: none
- JSON: research/levels/L052.json (shot research/shots/145-L052-start.png). Bot: 25 tap entries over 2 rounds (bot/log.jsonl).
- Start shots/145: timer 3:00, pitch 26.2 pt, OVAL silhouette board, 15 arrows, no obstacles.
- PROBES: (a) a tap at the exact midpoint (±1 pt) between two FREE parallel vertical strokes 1 cell (26.2 pt) apart sent the RIGHT-hand one (12-cell arrow, head (10,24)); the left one stayed (shots/146). (b) clip video/S1-L52-three-exits.mov: 3 free arrows tapped in one 'taps' call (starts 0/578/1166 ms) — three simultaneous exits.
- Attempt 1 FAILED — OUT OF TIME with 3/3 hearts (my fault): the bot's --leave 1 left the last 2-cell arrow and then looped on 'too few strokes to fit a grid' without pausing (~2 min), and my clip of the last tap started too late. Declined all offers (same 3 popups, 'You will lose 100 token and your streak!'), NO coins spent; life 5 -> 4; streak x100 -> x1 (shots/148 Out of Time, 149 Level Failed). Bot fixed: reuse the last grid fit when 1-3 arrows are left, pause after 4 read failures, and pause the game on --leave/--tapcap stops.
- Attempt 2 (Try Again, shots/150): WON by go.py --retry with 2:52 left (8 s of play), 3/3 hearts; +20; x5 (shots/152). Home: LEVEL 53, coins 3914, lives 4 (20:39 → a life refills in 20:00-20:40), Claw 282/300 (shots/153).

## L53
- Tag: none. Timer 2:30. Hearts 3. Board 20x30 cells (bounding box of arrow+obstacle cells), pitch 17.87 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 30 (dirs {'right': 16, 'up': 8, 'left': 3, 'down': 3}; length min/median/max 2/6/30 cells).
- Obstacles: {'box': 2, 'door': 2, 'box_part': 2, 'key': 1}; door cells 300
- JSON: research/levels/L053.json (shot research/shots/154-L053-start.png). Bot: 61 tap entries over 5 rounds (bot/log.jsonl).
- Start shots/154: timer 2:30. Obstacles: 2 DOORS stacked on the whole left half, 2 BOXES in the right half (top counter 39, bottom counter 21), 1 KEY arrow (horizontal key, left-pointing... key hangs on a right-pointing arrow mid-left, next to the lower door). Counters 39/21 exceed the 30 visible arrows: arrows hidden under the doors count too.
- Reveals: research/levels/L053-open1.json (after the 1st door), L053-open2.json (after both doors; 34 arrows on the board at that read).
- Result: WON with 1:32 left, 3/3 hearts (one bot stop on a 3-cell hook arrow read with 2 heads; finished with --ignore-anomalies); +20; x10 (shots/157). Home: LEVEL 54 'Hard Level' (red Play, red LEVEL plate), coins 3918 (+20 animating), lives 4 (15:13), Claw 287/300 (x10) (shots/158).

## L54
- Tag: Hard Level. Timer 3:00. Hearts 3. Board 26x34 cells (bounding box of arrow+obstacle cells), pitch 14.044 pt at fit zoom (stroke 3.0 pt).
- Arrows at start (visible): 72 (dirs {'down': 23, 'left': 21, 'up': 15, 'right': 13}; length min/median/max 2/4/42 cells).
- Obstacles: {'door': 1, 'key': 1}; door cells 312
- JSON: research/levels/L054.json (shot research/shots/159-L054-start.png). Bot: 102 tap entries over 10 rounds (bot/log.jsonl).
- HARD (red HUD). Start shots/159: timer 3:00, pitch 14.04 pt, 72 visible arrows. One wide DOOR across the top third; 1 KEY on the top row (key hanging on a left-pointing arrow just under the door's right half). Reveal: research/levels/L054-open1.json (61 arrows on the board at that read).
- Result: WON by go.py in 14 rounds with ~1:36 left, 3/3 hearts; red 'Hard Level' popup (skull ribbon) +60; x25 (shots/161). Then the ROCKET RACE event offer popped up on home (joined for free: +∞ lives 30m; see flows.md, shots/163-168). Home: LEVEL 55, coins 3994, lives ∞ 26:11, Claw 297/300 (x25), Rocket Race badge (shots/168).

## L55
- Tag: none. Timer 2:30. Hearts 3. Board 20x27 cells (bounding box of arrow+obstacle cells), pitch 17.874 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 48 (dirs {'down': 15, 'left': 17, 'up': 6, 'right': 10}; length min/median/max 3/6/42 cells).
- Obstacles: none
- JSON: research/levels/L055.json (shot research/shots/169-L055-start.png). Bot: 48 tap entries over 3 rounds (bot/log.jsonl).
- Start shots/169: timer 2:30, pitch 17.87 pt. SILHOUETTE: one wide block on top + two square blocks below separated by an empty column/row gap; 48 arrows, no obstacles.
- Result: WON with 1:54 left, 3/3 hearts; +20 (shots/171). NEW: with Rocket Race joined, the win popup's bottom strip is 'Rocket Race' (stopwatch 6h 9m) with 5 player tiles, rank badges 5 4 3 2 1 and progress n/5 each (player green, rank 4, 1/5; rivals 0/5, 3/5, 3/5, 4/5) instead of the Streak Race strip. Then Claw Challenge step reward 'Congratulations!' ∞-heart '1h' 'Tap to Claim' (tap on the text at (196,460); taps at y=785 do nothing) (shots/172). Home: LEVEL 56, coins 3994, lives ∞ 1h 20m (the 1 h stacked on the Rocket Race 30 m), Claw 22/500 (next reward: bulb x1), streak x100 (shots/173).

## L56
- Tag: none. Timer 3:00. Hearts 3. Board 24x32 cells (bounding box of arrow+obstacle cells), pitch 15.12 pt at fit zoom (stroke 3.34 pt).
- Arrows at start (visible): 60 (dirs {'left': 15, 'right': 21, 'down': 19, 'up': 5}; length min/median/max 3/5/46 cells).
- Obstacles: {'box': 2, 'box_part': 2, 'pipe': 4}
- JSON: research/levels/L056.json (shot research/shots/174-L056-start.png). Bot: 60 tap entries over 10 rounds (bot/log.jsonl).
- Start shots/174: timer 3:00, pitch 15.12 pt, 60 arrows. Obstacles: 2 BOXES (top-left 47, bottom-right 18), 4 U-PIPES (counters 5, 5, 4, 3). Box-break states: research/levels/L056-open1.json, -open2.json (whether anything sat under the boxes: compare the box rectangles).
- Result: WON with 1:48 left, 3/3 hearts; +20; Rocket Race strip: player 2/5, rank 4 (shots/176). Home: LEVEL 57, coins 4014 (+20 animating), lives ∞ 1h 17m, Claw 122/500 (+100) (shots/177).

## L57
- Tag: none. Timer 3:00. Hearts 3. Board 20x24 cells (bounding box of arrow+obstacle cells), pitch 17.845 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 42 (dirs {'up': 16, 'left': 11, 'right': 8, 'down': 7}; length min/median/max 3/5/37 cells).
- Obstacles: {'tape_pink': 4, 'box': 1, 'box_part': 7}
- JSON: research/levels/L057.json (shot research/shots/179-L057-start.png). Bot: 38 tap entries over 8 rounds (bot/log.jsonl).
- Start shots/179 (the first Play tap on this home opened the Rocket Race screen instead: shots/178 shows rivals at 4/4/3/0 vs the player's 2; closed with X). Timer 3:00, pitch 17.84 pt, 42 arrows. Obstacles: 4 PINK TAPES on the top row, each binding 2 adjacent up-arrows; 4 BOXES in a rising staircase along the bottom (counters 40, 37, 26, 22 from left to right; the touching boxes are read as one 'box' blob whose covered cells are exactly the staircase).
- Result: WON with 2:19 left, 3/3 hearts; +20; Rocket Race strip: DSMShark 5/5 (rank 1), player 3/5 (rank 4) (shots/181). Home: LEVEL 58, coins 4034 (+20 animating), lives ∞ 1h 12m, Claw 222/500 (shots/182).

## L58
- Tag: none. Timer 2:30. Hearts 3. Board 22x24 cells (bounding box of arrow+obstacle cells), pitch 16.375 pt at fit zoom (stroke 3.34 pt).
- Arrows at start (visible): 27 (dirs {'down': 3, 'right': 9, 'left': 4, 'up': 11}; length min/median/max 3/6/38 cells).
- Obstacles: {'key': 1, 'door': 1}; door cells 286
- JSON: research/levels/L058.json (shot research/shots/185-L058-start.png). Bot: 61 tap entries over 6 rounds (bot/log.jsonl).
- Start shots/185: timer 2:30, pitch 16.38 pt, 27 visible arrows in the top half; one wide DOOR over the whole bottom half; 1 KEY (horizontal key on a left-pointing arrow, left side). Reveal: research/levels/L058-open1.json.
- Result: WON with 1:36 left, 3/3 hearts; +20; Streak Race x100 strip (Rocket Race not re-joined) (shots/187). Home: LEVEL 59 'Super Hard' (purple Play), coins 4054 (+20 animating), lives ∞ 1h 7m, Claw 322/500 (shots/188).

## L59
- Tag: Super Hard. Timer 2:00. Hearts 3. Board 26x34 cells (bounding box of arrow+obstacle cells), pitch 14.042 pt at fit zoom (stroke 3.0 pt).
- Arrows at start (visible): 85 (dirs {'down': 19, 'left': 27, 'right': 17, 'up': 22}; length min/median/max 2/6/44 cells).
- Obstacles: none
- JSON: research/levels/L059.json (shot research/shots/190-L059-start.png). Bot: 85 tap entries over 4 rounds (bot/log.jsonl).
- SUPER HARD (purple HUD). Timer 2:00 (!) — the shortest so far. Start shots/190 (the first Play tap on this home re-offered Rocket Race: 'Start' without the ∞ icon and without the prize tooltip; closed with X, shots/189). Dense rectangular maze, pitch 14.04 pt, 85 arrows, no obstacles.
- Result: WON with 1:00 left, 3/3 hearts; purple 'Super Hard' popup +100; x100 (shots/192). Home: LEVEL 60, coins 4074 (+100 animating), lives ∞ 1h 1m, Claw 422/500 (shots/193).

## L60
- Tag: none. Timer 3:00. Hearts 3. Board 20x20 cells (bounding box of arrow+obstacle cells), pitch 17.865 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 34 (dirs {'down': 10, 'left': 10, 'right': 8, 'up': 6}; length min/median/max 3/7/39 cells).
- Obstacles: none
- JSON: research/levels/L060.json (shot research/shots/194-L060-start.png). Bot: 34 tap entries over 2 rounds (bot/log.jsonl).
- Start shots/194: timer 3:00, pitch 17.87 pt, 34 arrows, no obstacles; SILHOUETTE: a square with a big notch cut out of the right-middle (a 'C'/'G' shape).
- Result: WON with 2:35 left, 3/3 hearts; +20; x100 (shots/196). Claw Challenge step reward 'Congratulations!' light-bulb 'x1' 'Tap to Claim' (shots/197) → a hint booster. Home: LEVEL 61, coins 4186 (+20 animating), lives ∞ 57:44, Claw 22/500 with the next reward '300' coins (shots/198).

## L61
- Tag: none. Timer 2:30. Hearts 3. Board 20x20 cells (bounding box of arrow+obstacle cells), pitch 17.856 pt at fit zoom (stroke 3.67 pt).
- Arrows at start (visible): 39 (dirs {'left': 4, 'up': 7, 'right': 14, 'down': 14}; length min/median/max 3/4/44 cells).
- Obstacles: {'tape_pink': 4}
- JSON: research/levels/L061.json (shot research/shots/199-L061-start.png). Bot: 35 tap entries over 3 rounds (bot/log.jsonl).
- Start shots/199: timer 2:30, pitch 17.86 pt, 39 arrows. SILHOUETTE: an octagon / rounded diamond with stepped diagonal edges. 4 PINK TAPES, each binding 2 parallel arrows, at the four compass points (top: 2 down-arrows; bottom: 2 down-arrows; left: 2 right-arrows; right: 2 right-arrows). The right booster (bulb) shows 4 after the Claw reward.
- Result: WON with 2:04 left, 3/3 hearts; +20; x100 (shots/201). Home: LEVEL 62, coins 4194 (+20 animating), lives ∞ 55:22, Claw 122/500 (next 300 coins), a red '!' badge on the trophy (Leaderboard) tab (shots/202).

## Session summary (player part 2, 02:35-04:28 wall clock)
- Recorded 15 levels L47-L61 (JSON for every start state; door/box states after opening in Lnnn-openK.json for L47, L49, L53, L54, L56,
  L57, L58). All 15 WON; 2 first attempts FAILED on time (L47 = my probes; L52 = bot looped on the last arrow) → 2 lives lost, no coins spent.
- Timers: 3:00 (L47, L50, L51, L52, L54, L56, L57, L60), 2:30 (L48, L49, L53, L55, L58, L61), 2:00 (L59 Super Hard).
  Tags: Hard L54 (+60); Super Hard L49, L59 (+100).
- New: BOX obstacle (unlock L50; L50, L51, L53, L56, L57), Weekly Contest unlock (home before L50), Rocket Race event (after L54).
- Measured: zoom range (max = absolute ~28.07 pt cell, min ≈ 0.78x fit), pinch does not start the timer, head tap works, hit radius
  >= 15 pt, midpoint tie → the right-hand arrow won once, swipe pans the board (no trigger), bump (-1 heart, red arrow, blocker flash +
  ✖ marker, ~400 pt/s slide, timeline in obstacles.md), 'Perfect!' even with a heart lost, all boxes count down together, life refill ~20 min.

## Phone session 2 (v552 L62 onward; player S2 12:06-; ledger research/phone-session2-progress.md)
Same conventions. New in S2: CORNER obstacle (unlock L70) → bot add-on research/bot/corners.py (+ go2.py); per-level overrides
research/bot/overrides/L066/L067/L069.json (key-/box-occluded arrows verified by eye); an additive read rule in bot.py (a box's counter
badge inside a merged door+box blob = 'box_part'). Corner JSON obstacles carry kind "corner" + "facing" [sx, sy] (the plate's diagonal).

## L62
- Tag: none. Timer 3:00. Hearts 3. Board 26x34+ (pitch 14.04 pt = fit = the absolute minimum), 44 visible arrows at start.
- Obstacles: 2 DOORS, 3 BOXES (counters 23 / 66 / 34), 3 pink TAPES, 2 KEYS. Two U-shaped arrows at (13-14,34) and (15-16,34) run under the
  bottom door's top frame (heads hidden) → listed as anomalies in the start JSON; they are in the open-state JSONs.
- JSON: research/levels/L062.json (start, from shots/meta-058 = pixel-identical to every later L62 start); L062-open1/open2.json from the
  latency agent's bot run (build/phone2/l62-bot, bot/tmp/L062-111422-rNN; cells in that run's start frame — the run began after 5 latency
  taps, so its "start" lacks those arrows; use the open files for the revealed arrows only).
- History: meta explorer (S1) ran it out on purpose 3x + 1 hearts-out; latency agent attempt 1 out of time (67 s left foregrounded), retry
  WON by the bot with 0:43 left, 3/3, +20 (11:20).

## L63
- Tag: none. Timer 2:30. 38 visible arrows at start, 1 big DOOR, 2 PIPES, 1 KEY (pitch 14.04).
- JSON: research/levels/L063.json + L063-open1.json (from the latency agent's bot run: bot/tmp/L063-112956-rNN, --leave 6).
- WON by the latency agent's last measured tap: 'Perfect!' 0:27 left, 3/3, +20, Streak Race x10.

## L64
- Tag: HARD (red). Timer **1:40** (the shortest Hard timer so far). Board 24x30, pitch 15.12 pt, 75 arrows (dirs L23 U21 R16 D15; length 2/7/45).
- Obstacles: none. Dense rectangular maze.
- JSON: research/levels/L064.json (shots/416). WON by go.py (4 rounds) with 0:42 left, 3/3, 'Perfect!' +60 (shots/418).

## L65
- Tag: none. Timer 3:00. Pitch 14.04, 23 visible arrows (bottom-right quarter only) + everything else under obstacles.
- Obstacles: 2 DOORS (tall left door; middle-right door), 2 BOXES stacked on the right (counters 22 top, 52 bottom), 1 KEY (on a bottom
  arrow). The boxes touch the doors, so the reader sees ONE merged 'door' blob (767 cells) + 2 'box_part' badges — the JSON's single
  'door' obstacle = 2 doors + 2 boxes (split them by the shot: left door cols 0-9 rows 0-33; right column: box 22 (top), door, box 52).
- JSON: research/levels/L065.json (shots/421) + L065-open1.json (bot state after the first opening). Revealed rounds: bot/tmp/L065-122221-rNN.
- WON 1:49 left, 3/3, +20.

## L66
- Tag: none. Timer 2:30. Board 20x20, pitch 17.87, 13 visible arrows around one big central DOOR (rows 21-26), 1 KEY on the long row-20
  arrow (override L066.json). JSON L066.json (shots/427) + L066-open1.json (arrows under the door). WON 2:09 left, 3/3, +20.

## L67
- Tag: none. Timer 2:30. Board 20x20, pitch 17.87, 37 arrows (3 by override L067.json: two left-edge spirals, one head touching a box).
- Obstacles: 4 BOXES on the anti-diagonal, counters 25 (top-right), 21, 14, 9 (bottom-left). JSON L067.json (shots/434) (+ L067-open1.json =
  a box-state snapshot; boxes hide nothing). WON 1:39 left, 3/3, +20.

## L68
- Tag: none. Timer 3:00. Board 20x31, pitch 17.87, 59 arrows. Obstacles: 2 PIPES (right edge; counters 6 top, 3 bottom) + 3 pink TAPES
  (left edge, 4 arrows each). JSON L068.json (shots/444). WON 2:06 left, 3/3, +20.

## L69
- Tag: SUPER HARD (purple). Timer 2:00. Pitch 14.04, 58 visible arrows at start. Obstacles: 3 DOORS (top; bottom middle; bottom right),
  3 KEYS, 1 PIPE (bottom-left, counter 2) whose counter box touches a key (override L069.json for the key arrow).
- JSON L069.json (shots/450) + L069-open1.json. Bot stopped mid-level on the key/pipe anomaly (paused at 1:48), resumed after the override.
  WON with **0:21** left, 3/3, +100.

## L70 — CORNER unlock
- Tag: none. Timer 3:00. Pitch 20.6 pt (small board). Unlock card first: "Corner! / Unlocked! / Arrows turn when they hit the CORNER!"
  (shots/456; card dismissed by a tap, clip S2-L070-corner-unlock-dismiss.mov).
- Board: a 9-col arrow block (cols 0-8, rows 12-24; mostly ↑) + row 26: two ← arrows aimed at a CORNER at (9,26) + row 29: four ← arrows aimed
  at a CORNER at (1,29). Both corners face up-right (red plate up-right of the blue spring).
- RULE (clips S2-L070-corner-first-use.mov, S2-L070-corner-lower-turn-up.mov): a ← arrow reaching the corner cell turns ↑ and leaves up that
  column; no heart lost; the corner stays. Row-29 arrows need col 1 clear (the block) first.
- JSON L070.json (from shots/457, the board after the card). WON 0:25 left (hand play + playabove.py), 3/3, +20.

## L71
- Tag: none. Timer 3:00. Pitch 19.66, 27 arrows. A maze + a bottom row (row 30): L-arrow + → arrow | CORNER (8,30) facing up-left | CORNER
  (11,30) facing up-right | ← arrow + L-arrow. A → arrow turns ↑ at the left corner (clip S2-L071-corner-right-moving-turns-up.mov); a ← arrow
  turns ↑ at the right one. JSON L071.json (shots/470). WON 1:16 left, 3/3, +20.

## L72
- Tag: none. Timer 3:00. Pitch 26.20 (max-zoom-sized board), 15 arrows, round silhouette, no obstacles. JSON L072.json (shots/478).
  WON 2:52 left, 3/3, +20 (Claw reward ∞ 2h).

## L73
- Tag: none. Timer 2:30. Board 20x26, pitch 17.87, 61 arrows. Obstacles: CORNER at (1,12) top-left facing down-right (an ↑ arrow in col 1
  turns → along the top row), 2 BOXES (46 top-right, 58 bottom-right). First level played by the corner-aware bot (corners.py).
  JSON L073.json (bot round 1) + L073-open1.json. WON 1:39 left, 3/3, +20.

## L74
- Tag: HARD (red). Timer 3:00. Pitch 14.05, 113 arrows (the densest so far), no obstacles. JSON L074.json (shots/488).
  WON (4 rounds) with ~1:40 left, 3/3, +60.

## L75
- Tag: none. Timer 2:30. Pitch 17.87, 48 arrows; silhouette = a wide top block + two lower blocks with a gap. No obstacles.
  JSON L075.json (shots/492). WON 1:57 left, 3/3, +20. The Streak Race panel then opened by itself and animated the player's row 17 → 13
  (641 → 1041, +4 wins at x100 applied at once; shots/496).

## L76
- Tag: none. Timer 3:00. Board 24x26, pitch 15.12, 56 arrows + 6 CORNERS on the right edge (two stacked pairs + singles; facings in the
  JSON). First multi-corner board; corner-aware bot cleared it in 4 rounds. JSON L076.json (shots/498). WON 2:21 left, 3/3, +20.

## L77
- Tag: none. Timer 3:00. Board 20x24, pitch 17.84, 42 arrows. Obstacles: 4 pink TAPES (pairs, top row) + 4 BOXES in a staircase
  (40 / 37 / 26 / 22 left→right; read as 1 box + 7 box parts). JSON L077.json (shots/505) + L077-open1.json.
- Attempt 1 = gap clips: bump gap-0 (clip S2-L077-bump-gap0.mov; ← arrow blocked head-on, heart lost, arrow red; shots/507) and a re-tap
  of the red arrow (clip S2-L077-red-arrow-retap.mov); I analysed with the clock running → OUT OF TIME with 3 arrows left (popups declined,
  shots/508-512). Retry WON 2:22 left, 3/3, +20.

## L78
- Tag: none. Timer 3:00. Board 18x28, pitch 19.66, 37 arrows, no obstacles. Combo clip: 6 free arrows in one taps call (~0.58 s apart;
  clip S2-L078-combo-6-quick.mov). JSON L078.json (shots/517). WON 2:25 left, 3/3, +20. Win celebration shots/518 = the full-screen
  "MAZE OUT!" sign + confetti over the dimmed board.

## L79
- Tag: SUPER HARD (purple). Timer **3:00** (not 2:00 like L49/L59/L69). Board 24x30, pitch 15.12, 74 arrows + 5 CORNERS on both side edges.
  Hit-tolerance probe (shots/521-L079-hit13/-hit23): two parallel free ← arrows 15.1 pt apart; a tap 5 pt from the upper one → the upper
  one left; a 2nd tap ~2 s later 5 pt from the lower one (10 pt from the vacated upper line) → nothing moved (the lower arrow stayed).
  JSON L079.json (shots/521). WON 1:59 left, 3/3, +100.

## L80
- Tag: none. Timer 3:00. Board 22x24, pitch 16.39, 42 arrows + 4 CORNERS at the board's corners/edges. JSON L080.json (shots/526).
  WON 2:33 left, 3/3, +20.

## L81
- Tag: none. Timer 2:30. Board 20x20, pitch 17.86, 39 arrows + 4 pink TAPES. JSON L081.json (shots/529). WON 2:01 left, 3/3, +20
  (Claw reward 400 coins).

## L82
- Tag: none. Timer 2:30. Board 21x29, pitch 17.09, 60 arrows + 3 PIPES + 2 CORNERS (right edge). JSON L082.json (shots/533).
  WON 1:40 left, 3/3, +20.

## L83
- Tag: none. Timer 2:30. Board 22x28, pitch 16.38, 38 visible arrows + 1 DOOR + 1 KEY + 2 PIPES. JSON L083.json (shots/536) +
  L083-open1.json. WON 1:25 left, 3/3, +20. Next: L84 = HARD (red Play) — not started.

## Session summary (player S2, 12:06-14:18)
- Recorded L64-L83 (20 boards, every start JSON + door/box open states where the bot saw them) and filed L62/L63 from the latency
  agent's run; L62 start re-dumped from S1's meta-058.
- All won; one deliberate-clip attempt failed on time (L77 a) — no life lost (∞ lives), nothing bought.
- Timers: 3:00 (L65, 68, 70, 71, 72, 74, 76, 77, 78, 79, 80), 2:30 (L66, 67, 73, 75, 81, 82, 83), 2:00 (L69 Super Hard), 1:40 (L64 Hard).
  Tags: Hard L64 (+60), L74 (+60), L84 (next); Super Hard L69, L79 (+100).
- New obstacle: CORNER (unlock card at L70); corners appear again on L71, 73, 76, 79, 80, 82.

## L84 (phone session 3)
- Tag: HARD (red). Timer **2:00**. Board 26x33, pitch 14.04, 87 arrows (dense maze), no obstacles. JSON L084.json (shots/601).
  Intro clip S3-L084-play-intro.mov (Play tap → Hard intro). No gap clip (timer < 2:30 → skipped by rule). WON (13 bot rounds) with ~0:44 left,
  3/3, "Perfect!" +60. **Hard win panel is RED** (red frame, red ribbon "Hard Level" with skull icons, "Level 84" plate, Perfect!, 60 coins,
  green Continue; shots/603) — answers clips-needed #22 for the panel colour (celebration not clipped).

## L85
- Tag: none. Timer 2:30. Board 20x26, pitch 17.88, 49 arrows + 2 CORNERS (left edge facing up-right, right edge facing up-left, mid-board)
  + 4 pink TAPES. JSON L085.json (shots/615). Intro clip S3-L085-play-intro.mov.
- P0 CLIPS (automatic hook in go3.py, no pause): **long-gap bump** gap 10 (clip S3-L085-bump-gap10.mov; an ↑ 5-cell hook arrow, blocker
  = a J-shaped arrow 10 empty cells above; ~31 arrows left, clock ≈2:06): the arrow slides the full 10 cells, touches, blocker + arrow flash
  red with the red screen-edge tint, heart 3 breaks (shards) → grey, the arrow is back at rest RED ≈0.5 s after the tap (shots/616).
  **Re-tap of the red arrow** 9 s later (clip S3-L085-red-retap.mov, shots/617): the red arrow does the SAME out-and-back bump to its
  blocker (blocker flashes), but **no heart is lost** (hearts R R grey before and after) and no red edge tint was seen. The clip's first
  frame already shows the motion (the tap landed ~0.1 s before the first frame) → a lead-time retake is still wanted.
  **Hit tolerance** (clip S3-L085-hit-tolerance.mov, shots/618): two free ↑ arrows 17.88 pt apart (x 259.2 / 277.0 at y 251.5); tap 1 at
  x 265.1 (5.9 pt from A) → A left; tap 2 ~2.5 s later at x 271.1 (5.9 pt from B, 11.9 pt from A's vacated line) → **B left**. The ripple
  sits exactly on each tap mark (no runner offset). This does NOT replicate S2's L79 miss (B stayed) — see clips-needed #16.
- WON (7 bot rounds) with 1:18 left, 2/3 hearts, the popup still says **"Perfect!"** (+20) with a heart lost. Then Claw reward
  "Congratulations! ∞ 3h — Tap to Claim" (claimed; Claw bar → 4/800, next reward icon x2), Sky Jump stage 3: 1/10 (100/100).

## L86
- Tag: none. Timer 2:30. **The SAME board as L66** (start shot's board band is pixel-identical to shots/427, diff 0.0; same 13 arrows,
  cells and origin in the JSON): 20x20, pitch 17.86, one full-width DOOR + 1 KEY on the long row-20 arrow. v552 repeats boards.
  The key splits the key arrow again → override research/bot/overrides/L086.json (= L066's). JSON L086.json (shots/626) + L086-open1.json
  (after the door opened; a different moment of play than L066-open1, so the arrow counts differ). Intro clip S3-L086-play-intro.mov.
  No long-gap/parallel candidate appeared (few arrows per round). WON 2:07 left, 3/3, +20. Sky Jump 3: 2/10 (91/100).

## L87
- Tag: none. Timer 3:00. Board 16x31 (bot frame), pitch 19.67, 43 arrows + 3 BOXES stacked in the right column (counters 17 / 34 / 40
  top→bottom, 3x3 cells each). JSON L087.json (shots/631) + L087-open1.json (bot dump after the last box broke). Intro clip
  S3-L087-play-intro.mov.
- P0 clips: long-gap bump gap 7 (clip S3-L087-bump-gap7.mov; a → hook arrow, 5 cells, top-left; shots/632) and the **re-tap retake WITH
  lead time** (clip S3-L087-red-retap.mov, shots/633): 1.6 s of the static red arrow, the tap ripple at movie t ≈ 2.6 s on the tap mark,
  the red arrow slides 7 cells right to its blocker (≈ 0.2 s), the blocker flashes red, back at rest red by ≈ 3.0 s; hearts R R grey in
  every frame → a re-tap of a red arrow replays the bump but costs NO heart (3rd observation: S1, S3-L085, S3-L087).
- WON (14 bot rounds) 1:46 left, 2/3 hearts, "Perfect!" +20. Sky Jump 3: 3/10 (83/100). Home LEVEL 88, coins 6480, Claw 204/800.

## L88
- Tag: none. Timer 2:30. Board 24x30, pitch 15.12, 76 arrows in two blocks; 2 PIPES (each runs along the top of a block from the left
  edge to the right edge, counter badge "3" at the right end) + 4 pink TAPES (pairs under the pipe mouths). JSON L088.json (shots/638).
  Intro clip S3-L088-play-intro.mov.
- P0 clip: long-gap bump **gap 18** (clip S3-L088-bump-gap18.mov; a ↓ 7-cell arrow, 17 arrows left, clock ≈1:21; shots/639).
- WON (17 bot rounds) 1:00 left, 2/3, "Perfect!" +20. Sky Jump 3: 4/10 (75/100). Next: L89 = SUPER HARD (purple Play).

## L89
- Tag: SUPER HARD (purple). Timer **2:30**. Board 26x36, pitch 14.05, 65 visible arrows + 2 DOORS side by side over the top third + 2 KEYS
  (mid-board) + 3 CORNERS (top-left, bottom-left, bottom-right edges). JSON L089.json (shots/644) + L089-open1.json (after the first door
  opened). Intro clip S3-L089-play-intro.mov (Super Hard intro).
- WIN CLIP S3-L089-win.mov (11.9 s, one 33 ms gap at 1.9 s): the last exits → board clear → a dotted orange ring burst at the centre →
  the "MAZE OUT!" sign (same as normal levels) over a darkening board → fireworks + confetti on the dark → the **purple Super Hard win
  panel** ("Super Hard" skull ribbon, "Level 89", Perfect!, 100 coins, green Continue) with the Streak Race strip. → clips-needed #22:
  celebration unchanged, only the panel/ribbon colour follows the tag (red Hard L84, purple Super Hard L89).
- WON 1:03 left, 3/3, +100. Sky Jump 3: 5/10 (66/100). Home LEVEL 90, coins 6600, Claw 404/800.

## L90
- Tag: none. Timer 2:30. Board pitch 17.87, 33 arrows in three stacked horizontal blocks, no obstacles (no new obstacle at L90).
  JSON L090.json (shots/652). Intro clip S3-L090-play-intro.mov. No parallel pair at pitch ≤ 16 (hit re-check skipped).
  WON (6 bot rounds) 2:01 left, 3/3, +20. Sky Jump 3: 6/10 (57/100). Home LEVEL 91, coins 6620, Claw 504/800.
- Repeat check (build/phone3/dupes.py, normalised cell sets vs every recorded + video board): L84-L90 match nothing except
  **L86 = L66** (Jaccard 1.0).

## L91
- Tag: none. Timer 2:30. Board 20x20, pitch 17.87, 38 arrows + 3 CORNERS (top-right, bottom-left, bottom-right). JSON L091.json
  (shots/657). Intro clip S3-L091-play-intro.mov. Bump clip at the short end of the long-gap range: **gap 5** (S3-L091-bump-gap5.mov,
  shots/658). WON 1:47 left, 2/3, "Perfect!" +20. Sky Jump 3: 7/10 (48/100). Home LEVEL 92, coins 6640, Claw 604/800.

## L92
- Tag: none. Timer 2:30. Board 18x22, pitch 19.66, 40 arrows + 1 BOX (counter 15; one row high across the whole top of the board) + 2 PIPES
  (U-shaped, bottom-left and bottom-right corners, counter 3 at each mouth). JSON L092.json (shots/664) + L092-open1.json (after the box
  broke). Intro clip S3-L092-play-intro.mov. Pause clip S3-L092-pause-open-close.mov before the first tap (timer still 2:30 after it,
  shots/665). WON (17 bot rounds) 1:24 left, 3/3, +20. Sky Jump 3: 8/10. Home LEVEL 93, coins 6660, Claw 704/800.

## L93
- Tag: none. Timer 2:30. Board 21x26, pitch 17.08, 36 visible arrows + 3 DOORS in a rising staircase along the bottom
  (left low, right high) + 1 KEY + 2 CORNERS (top-left, top-right). JSON L093.json (shots/670) + L093-open1.json. Intro clip
  S3-L093-play-intro.mov. COMBO clip S3-L093-combo.mov (clips-needed #10; 7 free arrows + a bump; heart 3 lost).
- WON 1:08 left, 2/3, "Perfect!" +20. Claw reward "Congratulations! ×2 (hourglass booster) — Tap to Claim" → claimed (Claw bar 4/700,
  next ∞ 4h). Sky Jump 3: 9/10 (32/100). Home LEVEL 94 = HARD (red Play), coins 6680.

## L94
- Tag: HARD (red). Timer **2:30** (L84 Hard had 2:00, L64 1:40, L74 3:00). Board 26x36, pitch 14.04, 104 arrows (dense), no obstacles.
  JSON L094.json (shots/679). Intro clip S3-L094-play-intro.mov. WON (4 bot rounds) 1:20 left, 3/3, red panel +60.
- After Continue: home, then **Sky Jump stage 3 WON** screen by itself: "Levels 10/10, Players 7/100, Tap to Claim" (shots/683) →
  "Congratulations! You win! 1428 — You are sharing the reward with 6 other winners!" (10000/7; clip S3-skyjump3-win-claim.mov,
  shots/684) → home overlay "Congratulations! 1428 Tap to Claim" (clip S3-skyjump3-claim-coins.mov, shots/685) → coins fly to the counter
  6740 → 8168 (clip S3-skyjump3-claim-coins-home.mov, shots/686). The Sky Jump badge is gone from HOME afterwards (all 3 stages done).

## L95
- Tag: none. Timer 2:30. Board 20x26, pitch 17.87, 41 arrows, no obstacles. JSON L095.json (shots/690). Intro clip S3-L095-play-intro.mov.
  WON (4 bot rounds) 1:58 left, 3/3, +20. Home LEVEL 96, coins 8188, Claw 204/700 (no event popup; Sky Jump badge absent).

## L96
- Tag: none. Timer 2:30. Board 20x22, pitch 17.87, 32 arrows + 1 very long PIPE (58 cells: from a mouth on the top edge it runs left,
  then snakes down the whole left edge in a zig-zag to a mouth on the bottom edge with counter "3"). JSON L096.json (shots/695).
  Intro clip S3-L096-play-intro.mov. WON (5 bot rounds) 2:00 left, 3/3, +20. Home LEVEL 97, coins 8208, Claw 304/700.

## L97
- Tag: none. Timer 2:30. Board 22x26, pitch 16.38, 48 arrows + 1 tall BOX (counter 21; a 3-column-wide pillar down the middle of
  the board, 104 cells) + 4 CORNERS (two at the top of the right block, one at the bottom-left, one at the bottom of the left block).
  JSON L097.json (shots/699) + L097-open1.json (after the box broke). Intro clip S3-L097-play-intro.mov.
  WON (4 bot rounds) 1:54 left, 3/3, +20. Home LEVEL 98, coins 8228, Claw 404/700.

## L98
- Tag: none. Timer 2:30. Board 24x30, pitch 15.12, 42 visible arrows + 2 big DOORS side by side over the middle band (384 cells) +
  1 KEY (bottom right) + 4 pink TAPES (two above, two below the doors). JSON L098.json (shots/703) + L098-open1.json (arrows revealed:
  48 read after the doors opened). Intro clip S3-L098-play-intro.mov. WON (10 bot rounds) 1:12 left, 3/3, +20.
  Next: L99 = SUPER HARD (purple Play).
- Repeat check L84-L98 (build/phone3/dupes.py; the same tool finds all five known repeats L72/75/77/81/83 with Jaccard 1.0): only
  **L86 = L66**; every other board L84-L98 is new (best Jaccard ≤ 0.06).

## L99
- Tag: SUPER HARD (purple). Timer **3:00**. Board 26x32, pitch 14.04, 85 arrows, no obstacles. JSON L099.json (shots/707). Intro clip
  S3-L099-play-intro.mov. WON (5 bot rounds) 2:00 left, 3/3, purple panel +100. Home LEVEL 100, coins 8348, Claw 604/700.

## L100 — NEW OBSTACLE: ELEVATOR (v552 unlock)
- Tag: none. Timer 3:00. **Unlock card on opening** (over the dimmed board; clip S3-L100-play-intro.mov catches its entrance, shots/712):
  title **"Elevator!"**, **"Unlocked!"**, icon = a pale grey-lavender rounded square with TWO door panels (each with two dots), cream
  caption box with a blue border **"Clear all arrows on the ELEVATOR to activate it!"** (ELEVATOR in blue caps). Dismissed by a tap
  below the board (clip S3-L100-elevator-unlock-dismiss.mov); the clock was still 3:00 after it (shots/713).
- Board 16x17, pitch 21.82, 28 visible arrows. The ELEVATOR = a lavender rounded platform, 12x7 = 84 cells, split by a vertical
  divider into two doors (rim (207,213,238), inner panels (190,197,224), divider (137,146,182)); 9 arrows stand on it.
  **This board is IDENTICAL to the older build's L31** (research/levels/video/V2-L031.json): all 28 visible arrows and all 7 hidden arrows
  match cell for cell (build/phone3/dupes.py + a per-layer check). v552 moved the elevator's debut from L31 to L100.
- Play (research/bot/go3.py --elevator: the lavender platform is detected per round; the round that empties it stops right after the
  last platform arrow and is recorded): clip **S3-L100-elevator-open.mov** — the last platform arrow (a ⊓, 3 cells) is tapped at movie
  t ≈ 1.0 s and slides out down; ≈ 0.3 s later the doors part from the centre divider outward, the hidden layer shows under a dark tint
  (≈ 1.4 s), the tint fades and the platform frame is gone by ≈ 1.6 s → 7 ordinary arrows (the video's hidden layer). Same mechanics as
  video-levels-D.md "Elevator". JSON L100.json (shots/713; the elevator's 84 cells added as obstacle kind "elevator") + L100-open1.json
  (the 7 revealed arrows). Empty platform cells did not block any ray; no bump.
- WON 2:16 left, 3/3, +20. Claw reward ∞ 4h claimed (bar → 4/800). Home LEVEL 101, coins 8368.

## L101
- Tag: none. Timer 3:00. Board 17x21, pitch 20.68, 29 visible arrows + 1 ELEVATOR (104 cells, a tall platform on the left; 8 arrows on
  it). **Identical to the older build's L32** (V2-L032: 29/29 visible, 11/11 hidden arrows). JSON L101.json (shots/723; elevator cells
  added) + L101-open1.json (after the doors opened). Intro clip S3-L101-play-intro.mov; the bot's first round emptied the platform →
  clip S3-L101-elevator-open.mov (16 taps up to the last platform arrow, then the doors). WON 2:16 left, 3/3, +20.
- Pattern: v552 L100 = old L31, L101 = old L32 → the older build's elevator run (L31-L38, research/levels/video/V2-L031..038) seems
  to be re-used from L100 on. NB SPEC rule 19 uses V2-L032..V2-L038 as substitutes/spares in L35-L77 of Arrow Out.

## L102
- Tag: none. Timer 2:30. Board 20x27, pitch 17.87, 58 visible arrows + 1 wide ELEVATOR covering the top half (260 cells, 14 arrows on
  it) + 2 CORNERS (middle band, left and right edges) + a maze below. New board (no match in the older build or L1-L101). JSON
  L102.json (shots/727; elevator cells added) + L102-open1.json (22 arrows after the doors opened). Intro clip S3-L102-play-intro.mov.
- Incident: after round 1 the bot's free grid fit drifted (origin off by ~2 px with fewer strokes on the lavender platform) → 11 bogus
  anomalies → the bot PAUSED the game at 2:07 (no wrong tap). Added go3 --fit-from (every read uses the start shot's grid; the zoom never
  changes in a level) + --resume; resumed 2:03 → the elevator round was recorded (clip S3-L102-elevator-open.mov, 30 taps up to the last
  platform arrow, ~26 s) → WON 0:58 left, 3/3, +20.

## L103
- Tag: none. Timer 3:00. Board 17x23, pitch 20.68, 36 visible arrows + 4 BOXES (41 / 28 top, 13 / 18 bottom) + 2 ELEVATORS (78 cells
  each, left and right columns between the boxes). **Identical to the older build's L33** (V2-L033: 36/36 visible arrows at offset
  (+1,+10); the reader broke 4 arrows at box edges → override research/bot/overrides/L103.json taken from V2-L033). JSON L103.json
  (shots/733; elevator cells added) + L103-open1.json (NB: dumped while the 2nd elevator's doors were still animating: only 8 of the
  video's 17 hidden arrows are in it — use V2-L033's hidden layer). Intro clip S3-L103-play-intro.mov; elevator clip
  S3-L103-elevator-open.mov (the first platform to empty). WON (11 bot rounds, fixed start grid) 1:55 left, 3/3, +20.
  Next: L104 = HARD (red Play) — the older build's Hard elevator level was L35 (V2-L035, pipe + 320-cell elevator).

## L104
- Tag: HARD (red). Timer **3:00**. Board 25x36, pitch 14.56, 83 arrows (a dense spiral-like maze), no obstacles — a new board (NOT the
  older build's Hard elevator L35). JSON L104.json (shots/740). Intro clip S3-L104-play-intro.mov. WON (10 bot rounds, fixed start
  grid) 1:56 left, 3/3, red panel +60. Home LEVEL 105, coins 8488, Claw 404/800.

## L105
- Tag: none. Timer 3:00. Board 16x20, pitch 21.82, 34 arrows + 2 C-shaped PIPES on the left edge (16 cells each, counter "3" at the
  right-hand mouth). New board. JSON L105.json (shots/744-L105-start). Intro clip S3-L105-play-intro.mov. WON (14 bot rounds) 2:07 left,
  3/3, +20. Home LEVEL 106 (not started).

## Session summary (player S3, 14:29-16:49)
- Recorded **L84-L105 (22 boards)**, every start JSON + open states for doors/boxes/elevators; all won on the first try (no fail, no
  life lost, ∞ lives all session). Timers: 3:00 (L87, 99 SH, 100, 101, 103, 104 H, 105), 2:30 (L85, 86, 88, 89 SH, 90-98, 102),
  2:00 (L84 H). Tags: Hard L84 (+60, red panel), L94 (+60), L104 (+60); Super Hard L89 (+100, purple panel), L99 (+100).
- NEW OBSTACLE: **ELEVATOR** at L100 (unlock card + clips); L100-L103 use it. L100/L101/L103 are the older build's L31/L32/L33 boards
  exactly; L86 is L66 again. Everything else L84-L105 is new.
- P0 clips: long-gap bumps gap 5/7/10/18, red re-tap (x2, retake covers the tap), hit-tolerance re-check (pitch 17.9; no pitch ≤ 16
  parallel pair appeared afterwards), elevator card + opening; extra: Super Hard win, combo ladder, pause and settings open/close,
  Sky Jump stage-3 win + claim.
