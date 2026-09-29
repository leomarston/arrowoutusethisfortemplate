# Phone session 2 — PLAYER ledger (v552 from L62 on; one timestamped line per level / incident / snapshot)
Shots research/shots/4NN-*.png (from 400), clips research/video/S2-*.mov. Social snapshots → research/social-dynamics.md.
Levels → research/levels/Lnnn*.json + research/levels.md. Budget ~150 min from 12:06; stop at 1 life left (game on HOME).

- 12:06 START. Runner ok (front app com.grandgames.arrowjam). shots/400: HOME, LEVEL 64 "Hard Level" (red Play), coins 4554, lives 5 "Full",
        Claw 128/500 (x10 badge, next 300 coins, 2d 21h), Streak Race badge 21h 53m, Rocket Race 'Join', Sky Jump 'Join'.
        (L62/L63 were won by the latency agent: L62 retry 0:43 left, L63 0:27 left; their bot dumps are in build/phone2/l62-bot/.)
- 12:07-12:14 SOCIAL SNAPSHOT 1 (shots 401-408): Leaderboard opened on Weekly (player row 8, score 14), World top 15, Turkey (player #448 Level 64, top 7), Streak Race all 50 rows (player #31, 6 pts, x10). → social-dynamics.md
- 12:14 Rocket Race badge → offer 'Start' with ∞ icon (shots/409) → JOINED (free; 'Congratulations!' ∞ 30m 'Tap to Claim' → claimed, shots/410-411). Stage 1 lanes: Hsheh, Emilia, quints375, Elo, DER — all 0/5; 21h 44m.
- 12:15 Sky Jump badge → offer PRIZE 7000, 'Pass 7 Levels in a row on first try' (shots/412) → JOINED (free): 'Finding players on your level.' counter 56/100 (12:16:00) → 100/100 (12:16:13), 'Tap to Continue' → pads 1-7, Levels 0/7, Players 100/100, 23h 59m (shots/413-415). No coins/lives spent.
- 12:28 NOTE: one shot (12:28:38) caught the iOS LOCK SCREEN / notification view ('25 Eyl Cum 12:28', 'Rahatsız Etme') for a moment — deleted unviewed (privacy); the next shot showed the game home again.
- 12:17-12:18 L64 (Hard, timer 1:40!, 75 arrows, 24x30, pitch 15.12, no obstacles) WON by go.py (4 rounds) with 0:42 left, 3/3 hearts, 'Perfect!' +60.
        Win popup strip = Rocket Race (Emilia 4/5 already). After Continue: Sky Jump 1/7 → home LEVEL 65, coins 4614, ∞ 26:29, Claw 138/500 x25.
- 12:20 Weekly after the win: player 15 (#8); nobody else moved (shots/420).
- 12:21-12:23 L65 (3:00; 2 DOORS + 2 BOXES 22/52 + 1 key; 23 visible arrows, pitch 14.04) — the bot read the boxes' counter badges as 'unknown'
        (a box touching a door merges into the door blob) → ADDED an additive rule to research/bot/bot.py read_board (an unknown blob < 1.5 cells
        inside a door blob's bbox = 'box_part'). WON with 1:49 left, 3/3, +20. Rocket Race R1 LOST (Emilia 5/5 at ~12:23). Sky Jump 2/7, 88/100.
- 12:26-12:27 L66 (2:30; one big door + 1 key on a long row-20 arrow; 13 visible arrows, pitch 17.87) — key split the key arrow → override
        research/bot/overrides/L066.json (verified on the start shot). WON 2:09 left, 3/3, +20, streak x100. Sky Jump 3/7 (75/100).
        Rocket Race re-offered (Start, tooltip '500 coins + ∞ 45m') → JOINED R2 12:28 (lanes Hsheh, Tin, doost, Truth + an empty 5th lane).
- 12:30-12:34 L67 (2:30; 4 BOXES 25/21/14/9 on the diagonal; 37 arrows incl. 3 traced by override L067.json: two spirals + a head touching
        a box) WON 1:39 left, 3/3, +20. R2 LOST (player_nvbfr9z 5/5 in ≤ 6 min). Sky Jump 4/7 (62/100). Home LEVEL 68, coins 4674, Claw 363/500.
- 12:36-12:41 SOCIAL SNAPSHOT 2 (shots 440-443). → social-dynamics.md
- 12:41-12:43 L68 (3:00; 59 arrows, 20x31; 2 PIPES (counters 6, 3) + 3 pink TAPES) WON 2:06 left, 3/3, +20. Sky Jump 5/7 (49/100).
        Rocket Race re-offered → JOINED R3 12:44 (Hsheh, Lol, Incog, Caz, ned).
- 12:45-12:50 L69 (SUPER HARD, purple; timer 2:00; 58 arrows, pitch 14.04; 3 DOORS, 3 KEYS, 1 PIPE counter 2). Bot stopped mid-level (paused at
        1:48) on a key touching the pipe's counter box (3-end pipe + broken key arrow) → override L069.json (verified on a grid crop), resumed with
        play2 --ignore-anomalies → WON with 0:21 left, 3/3, +100. Claw reward 300 coins claimed ('Congratulations!'). Sky Jump 6/7 (36/100).
        Home LEVEL 70, coins 5094, lives 5 Full (∞ expired), Claw 63/300 (next ∞ 2h).
- 12:53 L70 = NEW OBSTACLE: "Corner! / Unlocked! / Arrows turn when they hit the CORNER!" (unlock card over the dimmed board, red plate on a
        blue spring, shots/456; clip S2-L070-corner-unlock-dismiss.mov). Board: a 9-col maze block + two rows of ← arrows aimed at 2 corners
        (plate faces up-right): an arrow moving LEFT turns UP at the corner cell and exits up its column (clip S2-L070-corner-first-use.mov,
        shots/458: no bump, no heart). The session-1 bot does not know corners → played by hand: corner rows + research/tools/playabove.py for the
        maze (bot planner restricted to arrows above the corner rows). Lower row via the 2nd corner after the maze was cleared (clip
        S2-L070-corner-lower-turn-up.mov). WON with 0:25 left (my analysis time ran the clock), 3/3, +20.
- 13:00-13:02 Sky Jump stage 2 WON: 7/7 with 15/100 players left → "You win! 466 — You are sharing the reward with 14 other winners!"
        (7000/15 = 466.7) → claimed 466 coins → coins 5580. Stage 3 offer "PRIZE 10000 / Pass 10 Levels in a row on first try" → JOINED
        (free; matchmaking counter 1 → 100/100 in ~3 s, 13:03:18-21). R3 LOST at ~13:03 (ned 5/5, Incog 4, Caz 3, Hsheh 2, Lol 1).
- 13:04-13:07 L71 (3:00; maze + a bottom row with 2 CORNERS facing up-left/up-right; right-moving arrows turn UP at the left corner, clip
        S2-L071-corner-right-moving-turns-up.mov) — maze by playabove.py (4 rounds), bottom row by hand. WON with 1:16 left, 3/3, +20.
        Sky Jump 3: 1/10 (100/100). Rocket Race R4 offer DECLINED (X). Home LEVEL 72, coins 5600, 5 Full, Claw 263/300.
- 13:10-13:14 SOCIAL SNAPSHOT 3 (shots 476-477). Player Weekly 22 (#7, passed Ttam), Turkey #412 at Level 72, Streak Race #17 (641).
- 13:41-13:45 L77 (3:00; 42 arrows; 4 BOXES 40/37/26/22 staircase + 4 pink tapes x2) GAP CLIPS: bump gap-0 (clip S2-L077-bump-gap0.mov, arrow id 19 ← len 4 blocked head-on; heart 3 lost, arrow RED, timer started; shots/507) → MY MISTAKE: I analysed for 84 s with the clock running → re-tap of the RED arrow (clip S2-L077-red-arrow-retap.mov) → bot → OUT OF TIME with 3 arrows left (~13:45). Declined: 'Out of Time! +30 sec Add Time 900' X → 'Continue? You will lose 100 token and your streak!' Play On 900 X → 'Continue? You will lose a life!' Play On 900 X → Sky Jump 'You failed the challenge. Better luck next time!' (stage 3 lost at 6/10) → 'Level 77 Level Failed! Try Again' (Streak x100 → x1). Nothing spent; ∞ lives active → no life lost.
- 13:16 L72 (3:00, 15 arrows, round, pitch 26.2) WON 2:52 left (+20) → Claw reward ∞ 2h claimed. Sky Jump 3: 2/10 (91/100).
- 13:19 L73 has a CORNER + 2 boxes → wrote research/bot/corners.py (corner facing from the red plate vs the spring; reflection
        d' = d - (d·s)s from the plate side, blocked from the back; checked on the L70/L71 boards against the clips) + go2.py wrapper.
        L73 (2:30, 61 arrows) WON by the corner-aware bot 1:39 left, +20. Sky Jump 3/10 (82/100).
- 13:25 L74 (HARD, 3:00, 113 arrows) WON ~1:44 left, +60. 13:28 L75 (2:30, 48 arrows) WON 1:57 left, +20 → the Streak Race panel opened
        by itself and animated the player 17 → 13 (641 → 1041). 13:32 L76 (3:00, 56 arrows, 6 corners) WON 2:21 left, +20.
- 13:35-13:39 SOCIAL SNAPSHOT 4 (shots 502-504): Weekly player 27 (#4), Turkey #396 at L77, Streak Race #12 (1141).
- 13:41-13:51 L77 — see the incident line above (gap clips, out of time, all offers declined, Sky Jump 3 lost at 6/10, streak reset);
        retry WON 2:22 left, +20 (home: streak x5, ∞ 1h 26m, Sky Jump cooldown 28:24).
- 13:53 L78 (3:00, 37 arrows) COMBO clip S2-L078-combo-6-quick.mov (6 free arrows ~0.58 s apart) then bot: WON 2:25 left, +20.
- 13:57 L79 (SUPER HARD, 3:00, 74 arrows, 5 corners) HIT-TOLERANCE shots 521-L079-hit13/-hit23 then bot: WON 1:59 left, +100.
- 14:01-14:04 SOCIAL SNAPSHOT 5 (shots 524-525): Weekly player 30 (#3 podium), Turkey #386 at L80, Streak Race #11 (1157).
- 14:05 L80 (3:00, 42 arrows, 4 corners) WON 2:33 left. 14:08 L81 (2:30, 39 arrows, 4 tapes) WON 2:01 left → Claw reward 400 coins claimed.
        14:11 L82 (2:30, 60 arrows, 3 pipes, 2 corners) WON 1:40 left. 14:13 L83 (2:30, 38 arrows, door + key + 2 pipes) WON 1:25 left.
        (gapscan found no ≥ 5-cell gap on L78-L83, so the long-gap bump was not recorded.)
- 14:15 the snapshot script's first tap landed in a Streak Race panel that had opened by itself after the L83 win: it scrolled that panel
        (harmless; data kept as snapshot 6, shots/539: player #7 with 1482, inside the 100-coin band) → closed it (X) and re-ran:
- 14:17 SOCIAL SNAPSHOT 6 (shots 542): Weekly player 34 (#3), Turkey #375 at L84.
- 14:18 STOP (budget). PHONE NOW (shots/543): Maze Out! on HOME, LEVEL 84 "Hard Level" (red Play, not started), coins 6360, lives ∞ 59:37
        (5 underneath), Claw 204/400 (x100 badge, next reward ∞ 3h, 2d 19h), Streak Race badge 19h 41m (x100), Rocket Race 'Join', Sky Jump
        badge cooldown ~01:38. Boosters untouched (hourglass 2, bulb 3). Runner up; Arrow Out not launched this session.
        SPENT: 0 coins, 0 money, no ads, no boosters. EARNED (rewards only): coins 4554 → 6360 (+1806: level wins, Claw 300 + 400, Sky Jump
        stage-2 share 466). Lives: none lost (∞ lives from Rocket Race / Claw rewards covered every start incl. the L77 time-out).
        Joined free events: Rocket Race ×3 (all lost), Sky Jump stage 2 (won, 466 coins) + stage 3 (failed at 6/10 on the L77 time-out).
