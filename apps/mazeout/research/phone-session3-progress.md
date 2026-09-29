# Phone session 3 — PLAYER ledger (v552 from L84 on; one timestamped line per level / incident / snapshot)
Shots research/shots/6NN-*.png (from 600), clips research/video/S3-*.mov. Social snapshots → research/social-dynamics.md (section I).
Levels → research/levels/Lnnn*.json + research/levels.md. Budget ~150 min from 14:29; stop at 1 life left (game on HOME).
Logs/scripts of this session: build/phone3/ (go3 logs, social OCR). Rules as session 2: pause (352,88) before analysing; REJECT every
purchase/ad/continue/offer; never touch iOS settings; boosters untouched.

- 14:30 START. Runner ok (front app com.grandgames.arrowjam). shots/600: HOME, LEVEL 84 "Hard Level" (red Play), coins 6360, lives ∞ 47:28,
        Claw 204/400 (x100 badge, next ∞ 3h, 2d 19h), Streak Race badge 19h 29m, Rocket Race 'Join', Sky Jump badge now 'Finished'
        (was a cooldown timer at 14:18).
- 14:39-14:41 L84 (HARD, 2:00, 87 arrows, pitch 14.04, no obstacles) intro clip S3-L084-play-intro.mov; WON ~0:44 left, 3/3, +60.
        The Hard win panel is RED with a skull "Hard Level" ribbon (shots/603). Home (shots/604): LEVEL 85, ∞ 36:37, Claw 304/400,
        Sky Jump badge back to 'Join', Rocket Race 'Join'. Wrote research/bot/go3.py (go2 + intro clip + automatic P0 gap-clip hook).
- 14:42 SOCIAL SNAPSHOT attempt 1 WASTED: a Sky Jump offer popup (stage 3, PRIZE 10000) had opened by itself on HOME a few s after the
        L84 Continue; every snapshot tap landed on the dim (no button hit). 27 popup-only shots (605/606) deleted; 608 keeps the popup.
        Fix: go3.py and tools/socialsnap3.sh now refuse to start unless HOME is clean.
- 14:45 Sky Jump stage 3 RE-JOINED (free, no coins): matchmaking 29/100 at +2 s → 100/100 at +5 s (shots 609-610), pads 0/10, 100/100,
        23h 59m (611). (Joining a free event = same convention as session 2; no purchase/ad/continue involved.)
- 14:46-14:48 SOCIAL SNAPSHOT 7 (S3 #1; shots 612 streak p0-p14, 614 leaderboards) → social-dynamics.md section I (generator
        build/phone3/social3.py). Weekly: only the player moved (34 → 35, #3). Turkey: player #369 at L85; Mrmş 3329 → 3333.
        Streak Race: player #7, 1582; Sarah 0 → 249, Babs 0 → 141, player_2nbw6lp 0 → 41 (three idle rivals woke up).
- 14:50-14:52 L85 (2:30, 49 arrows, pitch 17.88, 2 corners + 4 tapes) with the go3 hook: LONG-GAP BUMP gap 10 (S3-L085-bump-gap10.mov,
        heart 3 lost, arrow red), RED RE-TAP (S3-L085-red-retap.mov: same out-and-back bump, NO heart lost; tap just before frame 1),
        HIT TOLERANCE (S3-L085-hit-tolerance.mov: 5.9 pt from A → A; 5.9 pt from B → B left, ripple on the marks). WON 1:18 left,
        2/3 hearts yet "Perfect!" +20. Claw reward ∞ 3h claimed (bar 4/800). Sky Jump 3: 1/10 (100/100). Home: LEVEL 86, coins 6440,
        ∞ 3h 24m.
- 14:56-15:00 L86 (2:30, 13 arrows, door + key) = **the same board as L66** (pixel-identical start). First go3 run stopped BEFORE the first
        tap on the key-split anomaly (clock not running) → override L086.json (copy of L066's) + go3 --here → WON 2:07 left, 3/3, +20.
        Sky Jump 3: 2/10 (91/100). Home: LEVEL 87, coins 6460, ∞ 3h 18m, Claw 104/800.
- 15:00-15:02 L87 (3:00, 43 arrows, pitch 19.67, 3 boxes 17/34/40) with the go3 hook (lead time 3.0 s): long-gap bump gap 7
        (S3-L087-bump-gap7.mov) + RE-TAP RETAKE (S3-L087-red-retap.mov: 1.6 s before the tap in frame, same bump replayed, NO heart lost).
        WON 1:46 left, 2/3, "Perfect!" +20. Sky Jump 3: 3/10 (83/100). Home LEVEL 88, coins 6480, ∞ 3h 15m, Claw 204/800.
- 15:04-15:07 L88 (2:30, 76 arrows, pitch 15.12, 2 pipes + 4 tapes): long-gap bump gap 18 (S3-L088-bump-gap18.mov). WON 1:00 left, 2/3,
        +20. Sky Jump 3: 4/10 (75/100). Home: LEVEL 89 "Super Hard" (purple Play), coins 6500, ∞ 3h 11m, Claw 304/800.
- 15:08-15:11 L89 (SUPER HARD, 2:30, 65 arrows, pitch 14.05, 2 doors + 2 keys + 3 corners) with a WIN CLIP (S3-L089-win.mov: last
        exits, MAZE OUT! sign, fireworks, purple Super Hard panel). WON 1:03 left, 3/3, +100. Sky Jump 3: 5/10 (66/100).
        Home: LEVEL 90, coins 6600, ∞ 3h 7m, Claw 404/800.
- 15:12-15:14 SOCIAL SNAPSHOT 8 (S3 #2; shots 649 leaderboards incl. World rows 1-23, 650 streak p0-p14) → section I. Weekly: player 40
        (#3), MagicGoose 23 → 24. Turkey: player #358 at L90. World: ah8prp7 +10, Winner +5, Crazzijj 11641 (+46 since 14:01), Wilbert
        9766 (Ptr unchanged, 9075). Streak Race (18h 46m left): player_2nbw6lp 41 → 2641 (26 wins at x100 in ≤ 26 min), player_0k30dg3 1941 → 2941;
        player 2082 (#7).
- 15:16-15:18 L90 (2:30, 33 arrows, pitch 17.87, no obstacles) WON 2:01 left, 3/3, +20. Sky Jump 3: 6/10 (57/100).
        Home LEVEL 91, coins 6620, ∞ 2h 59m, Claw 504/800. Repeat check: only L86 = L66 among L84-L90.
- 15:20-15:22 L91 (2:30, 38 arrows, 3 corners) bump gap 5 (S3-L091-bump-gap5.mov) → the long-gap set is now gaps 5/7/10/18 (+ S2's 0).
        WON 1:47 left, 2/3, +20. Sky Jump 3: 7/10 (48/100). Home LEVEL 92, coins 6640, ∞ 2h 57m, Claw 604/800.
- 15:23 Home Settings open/close clip S3-home-settings-open-close.mov (nothing toggled; settings = the owner's). 
- 15:25-15:29 L92 (2:30, 40 arrows, pitch 19.66, 1 long box 15 + 2 U-pipes) with a pause open/close clip before the first tap
        (S3-L092-pause-open-close.mov; the clock does not start). WON 1:24 left, 3/3, +20. Sky Jump 3: 8/10. Home LEVEL 93, coins 6660.
- 15:30-15:34 L93 (2:30, 36 arrows, 3 staircase doors + key + 2 corners) with a COMBO clip (S3-L093-combo.mov: runner spacing ~1.0 s;
        7th tap after a 2 s pause exits blue; bump at the end, heart lost). WON 1:08 left, 2/3, +20. Claw reward ×2 hourglass claimed
        (booster stock +2; free reward, not bought). Sky Jump 3: 9/10 (32/100). Home: LEVEL 94 Hard, coins 6680, ∞ 2h 45m.
- 15:35-15:40 L94 (HARD, 2:30, 104 arrows, pitch 14.04) WON 1:20 left, 3/3, +60. Then SKY JUMP STAGE 3 WON: 10/10 with 7/100 players
        left → "You win! 1428 — sharing the reward with 6 other winners" → claimed (clips S3-skyjump3-win-claim, -claim-coins,
        -claim-coins-home; shots 683-686). Coins 6740 → 8168. Sky Jump badge gone from HOME. Home: LEVEL 95, ∞ 2h 37m, Claw 104/700.
- 15:41-15:43 SOCIAL SNAPSHOT 9 (S3 #3; shots 687 leaderboards, 688 streak) → section I. Weekly: player 45 (#3), nobody else moved.
        Turkey: player #344 at L95. World: Winner 13364 (+10), Wilbert 9779 (+13). Streak (18h 17m left): oddgull 741 → 2341
        (16 x100 wins in ≤ 29 min), QueenK 0 → 141; the player 2582 = #6.
- 15:45-15:47 L95 (2:30, 41 arrows, pitch 17.87, no obstacles) WON 1:58 left, 3/3, +20. Home LEVEL 96, coins 8188, ∞ 2h 28m.
- 15:48-15:50 L96 (2:30, 32 arrows, 1 long zig-zag pipe along the left edge) WON 2:00 left, 3/3, +20. Home LEVEL 97.
- 15:51-15:53 L97 (2:30, 48 arrows, 1 pillar box 21 + 4 corners) WON 1:54 left, 3/3, +20. Home LEVEL 98.
- 15:54-15:57 L98 (2:30, 42 arrows, 2 doors + key + 4 tapes) WON 1:12 left, 3/3, +20. Home LEVEL 99 "Super Hard".
        (SPEC ruling 26 at 15:55: v552 repeats its own boards — consistent with this session's L86 = L66.)
- 15:58-16:00 L99 (SUPER HARD, 3:00, 85 arrows, pitch 14.04) WON 2:00 left, 3/3, +100. Home LEVEL 100, coins 8348, ∞ 2h 17m.
- 16:02-16:09 L100 = NEW OBSTACLE **ELEVATOR** (unlock card "Elevator! / Unlocked! / Clear all arrows on the ELEVATOR to activate it!",
        caught by the intro clip S3-L100-play-intro.mov; dismiss clip S3-L100-elevator-unlock-dismiss.mov). Board = the older build's L31
        exactly (28 visible + 7 hidden arrows). go3.py got an --elevator guard (lavender platform detection; the round that empties the
        platform stops after that tap and is recorded): clip S3-L100-elevator-open.mov (doors part from the centre ≈ 0.3 s after the last
        platform arrow, hidden layer under a dark tint, plain by ≈ 0.6 s). WON 2:16 left, 3/3, +20. Claw ∞ 4h claimed. Home LEVEL 101.
- 16:12-16:14 SOCIAL SNAPSHOT 10 (S3 #4; shots 720 leaderboards, 721 streak) → section I. Weekly: the player 51 → **#2** (passed
        player_qqpvpjp 47), LoudRat 30. Turkey: player #333 at L101 (Caco17 10888). Streak (17h 46m left): player 3182 = #5;
        player_7gv2330 +640, Babs +282, Elke +241 (idle rivals waking up).
- 16:17-16:20 L101 (3:00, 29 arrows + a 104-cell elevator) = the older build's L32 exactly (visible + hidden). Elevator clip
        S3-L101-elevator-open.mov. WON 2:16 left, 3/3, +20. Home LEVEL 102, ∞ 5h 59m. v552 L100-101 = old L31-32 (elevator run).
- 16:21-16:29 L102 (2:30, 58 arrows, 260-cell elevator over the top half + 2 corners; new board). Bot paused itself at 2:07 on a drifted
        grid fit (no bad tap) → go3 --resume --fit-from <start shot> → elevator clip S3-L102-elevator-open.mov → WON 0:58 left, 3/3, +20.
- 16:32-16:39 L103 (3:00, 36 arrows, 4 boxes + 2 elevators) = the older build's L33 (36/36 visible). Start read stopped before the first
        tap on 4 box-edge arrows → override L103.json from V2-L033 → go3 --here --fixfit: elevator clip S3-L103-elevator-open.mov,
        WON 1:55 left, 3/3, +20. Home LEVEL 104 "Hard Level", coins 8428, ∞ 5h 43m.
- 16:37-16:40 SOCIAL SNAPSHOT 11 (S3 #5; shots 737 leaderboards, 738 streak) → section I. Weekly: player 54 (#2). Turkey: player #321
        at L104; Caco17 10899. World: Crazzijj 11692. Streak (17h 21m left): player 3482 = #5; Henri 0 → 141, Elke 1461.
- 16:42-16:44 L104 (HARD, 3:00, 83 arrows, pitch 14.56, no obstacles; new board) WON 1:56 left, 3/3, +60. Home LEVEL 105, coins 8488.
- 16:45-16:47 L105 (3:00, 34 arrows, 2 C-pipes) WON 2:07 left, 3/3, +20.
- 16:48 STOP (budget). PHONE NOW (shots/748-S3-final-home.png): Maze Out! on HOME, LEVEL 106 (green Play, not started), coins 8508,
        lives ∞ 5h 29m, Claw 504/800 (x100 badge, next reward x2 booster, 2d 17h), Streak Race badge 17h 12m (x100), Rocket Race 'Join',
        no Sky Jump badge (stage 3 finished). Boosters: hourglass 4 (2 + 2 from a Claw reward), bulb 3 — none used. Runner up.
        SPENT: 0 coins, 0 money, no ads, no continues, no boosters. EARNED (rewards only): coins 6360 → 8508 (+2148: level wins +
        Sky Jump stage-3 share 1428); Claw rewards ∞ 3h, ×2 hourglass, ∞ 4h claimed. Lives: none lost. Joined: Sky Jump stage 3 (free) → WON.
        LEVELS RECORDED: L84-L105 (22). Clips: 41 S3-*.mov in research/video (22 intros incl. the elevator card, 4 long-gap bumps, 2 red
        re-taps, 1 hit tolerance, 1 combo, 1 Super Hard win, pause, settings, 4 elevator openings + the unlock dismiss, 3 Sky Jump claim).
