# Phone session 1 — state ledger (one timestamped line per level / incident)

- 00:06 kickoff (orchestrator): game opened for the first time since install/update → iOS notification prompt → declined ("İzin Verme").
- 00:09 home: LEVEL 32, coins 2240, lives 5 "Full", event badge (checkered flags) "9h 50m" top-left, avatar top-left, settings gear top-right.
- 00:17 orchestrator entered L32 (Play at 196,668): timer 3:00, 3 hearts, coins 2240 shown top-left in level. Boosters: left (40,790) crystal/magnet ×3, right (352,790) light bulb ×3.
- 00:18 tapped the long ← arrow at (60,537) (clear ray): it left; faint grey dots mark its old cells. Timer 2:46 when the shot was taken (it runs).
- 00:19 pinch 2.0 → zoomed in (~2×); pinch 0.4 → zoomed OUT below the fit size (board ~0.75× of fit). Pause (352,88) → "Paused" panel: Sound ON/Haptic ON toggles,
        Resume (123,530) green, Quit (269,530) red, close X (361,256). Timer frozen at 2:08.
- 00:20 STATE WHEN HANDED OVER: L32 PAUSED at 2:08, 3 hearts, board zoomed out below fit (restore it: resume, then pinch in slightly or find the reset).
- 00:37 PLAYER S1 part 1 started (00:23). Bot written: research/bot/bot.py (read/dump/play). L32 start (003) read: 53 arrows, 4 pink tapes x4 arrows, pitch 17.87 pt, 0 anomalies → research/levels/L032.json.
- 00:39-00:48 probes on L32 (see input-model notes in levels.md): hold 5 s = no move until RELEASE (009/010); queued 2nd tap accepted (taps gap 0.25 → real spacing 770 ms: the runner's taps take ~0.5-0.8 s EACH).
- 00:50 L32 FAILED — OUT OF TIME (my fault: a pause tap after the P02 probe did not open the panel, ~30 s ran while I analysed; my blind 'Resume' tap then hit the board). No heart lost (3/3).
        Popups (all declined, NO coins spent): "Out of Time!" (+30 sec, "Add Time 900") → X; "Continue?" "You will lose your streak!" x1..x100, "Play On 900" → X;
        "Continue?" "You will lose a life!" broken heart, "Play On 900" → X; "Level 32 / Level Failed! / Try Again" + Streak Race banner "9h 16m" (x1 lit).
        FIX: research/tools/pause.sh + resume.sh (verify the Paused panel by pixels before/after; never blind-tap Resume).
- 00:58 L32 WON (attempt 2, bot, 1:01 left, 3 hearts). Tape rule: one tap sends the whole 4-bundle. +20 coins → 2260. Streak Race x5.
        Claw Challenge intro seen (0/1). HOME: LEVEL 33, coins 2260, lives 5 Full, boosters 3/3 (unused), Streak Race 9h 7m, Claw 3d 9h.
- 01:16 L33 WON (attempt 2; attempt 1 = out of time, cost a life 5→4). Claw step 1 → ∞ lives 30 min (claimed 01:16, until ~01:46).
        HOME: LEVEL 34 "Hard Level" (red Play), coins 2260 (+20 pending?), lives ∞ 29:57, streak x5, Claw 0/200, boosters 3/3.
- 01:27 after L34 (WON 2:03 left, +60 → 2340): home showed Claw 5/200 (+5 capsule), then an iOS rating prompt 'Maze Out! hoşunuza gidiyor mu?' (Do you enjoy Maze Out!?) → 'Şimdi Değil' (Not Now) (shots/039). Lives ∞ 21:05.
- 01:40 L34 WON (hard, 2:03 left, +60), L35 WON (pipe unlock, 2:19 left), L36 WON (2 pipes, 2:24 left). HOME: LEVEL 37, coins 2380, lives ∞ 06:38 (then 5), streak x100, Claw 40/200 (x100 badge), boosters 3/3 unused.
- 01:52 L37 WON (2:06), L38 WON (2:23), L39 WON (Super Hard, 1:53, +100). HOME: LEVEL 40, coins 2520(+100 pending), lives ∞ ~0:39 left, streak x100, Claw 140/300, new 'Join' badge.
- 02:27 L40-L43 WON (2:03, 1:38, 1:47, 2:05 left; 3/3 hearts each). Sky Jump joined after L39 (free 'Start'); now Levels 4/5, Players 47/100. HOME: LEVEL 44 Hard, coins 2700, lives ∞ 22:57, streak x100, Claw 240/400.
- 02:55 L44 WON (hard, 1:28), Sky Jump stage 1 WON after L44 (+714 coins, shared with 6 winners; stage 2 offer 'PRIZE 7000 / 7 levels' closed with X, not joined),
        L45 WON (2:15; Claw step reward 200 coins claimed), L46 WON (1:14).
- 02:56 STOP (150-min budget). PHONE NOW: game on HOME, LEVEL 47 (normal green Play), coins 3694 (+20 animating → 3714 expected), lives 5 Full,
        boosters 3/3 + 3/3 (never used), Streak Race x100 lit (7h 31m left), Claw Challenge 140/300 (x100 badge, next reward ∞ 1h, 3d 7h left),
        Sky Jump badge 'Join' (stage 2 not joined). No currency spent, no purchases/ads/continues accepted, no hearts lost in any won level.
- 02:35 PLAYER S1 part 2 started (wall clock). Phone: HOME LEVEL 47, coins 3714, lives 5 Full, boosters 3/3, streak x100, Claw 140/300.
- 02:38 runner died once (a 'pinch 0.8 0.5' = positive velocity on a zoom-OUT crashes XCUITest; use 'pinch S' without V for S<1); restarted OK
        in ~60 s; the game had gone to springboard → 'activate' brought it back unchanged (L47 not started, no pause popup).
- 02:50 L47: attempt 1 FAILED (out of time, my probes; 1 heart lost to a deliberate bump) → life 5→4, streak x100→x1; attempt 2 WON (2:07, 3/3).
        HOME: LEVEL 48, coins 3734, lives 4 (refill 15:56), boosters 3/3 unused, streak x5, Claw 141/300 (x5), Sky Jump 'Join'. No coins spent.
- 02:55 L48 WON (0:55 left, 2/3 hearts: 1 lost to the bump probe). HOME: LEVEL 49 Super Hard, coins 3754 expected, lives 4 (10:58), streak x10, Claw 146/300.
- 03:04 L49 WON (Super Hard, 2:30 timer, ~0:56 left, 3/3; +100). HOME: LEVEL 50, coins 3854 expected, lives 4 (04:15), streak x25, Claw 156/300.
- 03:15 L50 WON (1:15, 3/3). Weekly Contest tutorial + Box unlock seen. HOME: LEVEL 51, coins 3874, lives 5 Full, streak x100, Claw 181/300, boosters 3/3.
- 03:19 L51 WON (1:49, 3/3). HOME: LEVEL 52, coins 3894, lives 5 Full, streak x100, Claw 281/300.
- 03:29 L52: attempt 1 OUT OF TIME (bot looped on the last arrow; my fault) → life 5→4, streak x100→x1; attempt 2 WON (2:52, 3/3). HOME: LEVEL 53, coins 3914, lives 4 (20:39), streak x5, Claw 282/300, boosters 3/3. No coins spent.
- 03:34 L53 WON (1:32, 3/3). HOME: LEVEL 54 Hard, coins 3938 expected, lives 4 (15:13), streak x10, Claw 287/300.
- 03:47 L54 WON (Hard, ~1:36, 3/3, +60). Rocket Race joined (free; ∞ lives 30m). HOME: LEVEL 55, coins 3994, lives ∞ 26:11, streak x25, Claw 297/300, boosters 3/3.
- 03:52 L55 WON (1:54, 3/3). Claw reward ∞ 1h claimed. HOME: LEVEL 56, coins 3994, lives ∞ 1h 20m, streak x100, Claw 22/500, Rocket Race rank 4 (1/5), boosters 3/3.
- 03:56 L56 WON (1:48, 3/3). HOME: LEVEL 57, coins 4034, lives ∞ 1h 17m, streak x100, Claw 122/500, Rocket Race 2/5.
- 04:01 L57 WON (2:19, 3/3). HOME: LEVEL 58, coins 4054, lives ∞ 1h 12m, streak x100, Claw 222/500, Rocket Race 3/5 (a rival finished 5/5).
- 04:06 L58 WON (1:36, 3/3). HOME: LEVEL 59 Super Hard, coins 4074, lives ∞ 1h 7m, streak x100, Claw 322/500, Rocket Race 'Join' (lost stage 1, not re-joined).
- 04:11 L59 WON (Super Hard, 2:00 timer, 1:00 left, 3/3, +100). HOME: LEVEL 60, coins 4174, lives ∞ 1h 1m, streak x100, Claw 422/500.
- 04:15 L60 WON (2:35, 3/3). Claw reward bulb x1 claimed. HOME: LEVEL 61, coins 4194, lives ∞ 57:44, streak x100, Claw 22/500 (next 300 coins), boosters: magnet 3, bulb 3+1?
- 04:19 L61 WON (2:04, 3/3). STOP (reached L62). PHONE NOW: HOME, LEVEL 62 (normal green Play), coins 4214 (after the +20 animation), lives ∞ ~55 min, boosters magnet 3 / bulb 4 (never used), Streak Race x100 (5h 42m), Claw 122/500 (x100, next 300 coins, 3d 5h), Rocket Race 'Join' (stage 1 lost, not re-joined), Sky Jump 'Join', trophy tab red '!'. No coins spent in part 2; no purchases/ads/continues accepted.
- 04:25 a Streak Race leaderboard opened by itself on the idle home (shots/203; player rank 4, score 2065) → closed with X. FINAL: HOME LEVEL 62, coins 4214, lives ∞ 48:01, Claw 122/500 (next 300 coins), streak x100 (5h 35m), boosters magnet 3 / bulb 4, Rocket Race 'Join', Sky Jump 'Join', trophy tab '!'. Runner alive.
