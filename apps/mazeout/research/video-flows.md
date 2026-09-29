# Arrow Out — flows seen in the owner's videos (V1 levels 1-20, V2 levels 11-38)

Author: tutor lane, 2026-09-25. Tutorials and first-time moments are in `research/tutorials.md`; this file holds everything else.
- §1-2: per-level timelines.
- §3-8: screen flows, level intro, win sequences, coin payout, mistakes, economy.
- §9: SOCIAL / ONLINE screens, for the social-sim designer.
- §10: differences from the phone.

Conventions:
- Times are video seconds. V1 is 25 fps (592×1280); V2 is 59.64 fps (592×1280). pt = px × 393/592.
- "≈" = from the 1 fps / 5 fps indexes.
- Frames live under `research/video-frames/tutor/`: `full/` has full-res PNGs named `V1_t<sec>.png` / `V2_t<sec>.png`;
  `sheets/` has the contact sheets; `idx1/` is V1 at 5 fps; `idx2/` is V2 at 1 fps; `idx2b/` holds V2 windows at 4 fps.
- Grab any exact frame with `video-frames/tutor/tools/vgrab VIDEO OUTDIR PREFIX 0 t…` (AVAssetImageGenerator, zero tolerance, <1 s).
- OCR text timelines: `video-frames/tutor/ocr_V1_1fps.jsonl`, `ocr_V2_1fps.jsonl` (one line per second, boxes in pt).

**Which build is which.**
- V1 is the newer skin (about Aug 2026): the "MAZE OUT!" win logo, "Curtain", a 3-tab home. It matches the phone's home and win.
- V2 was recorded on Thu 30 Jul 2026 at 22:27 (the iOS status bar and notification centre, Vietnamese locale). It is an older skin:
  "Well Done!", "Box", a 5-tab home. The device has an AssistiveTouch button (the grey disc at the top right), which is not the game.
- **Both are older than the phone's v552. Their L32-38 boards differ from the phone's** (`sheets/V2_vs_phone_L32-38.jpg`).
- **Visuals follow the phone. The videos give L1-31 content (owner), the FTUE sequence and the captions.**

## 1. V1 timeline (fresh install → L21 on home)

| L | board on screen | first tick 2:59 | time left at win | "MAZE OUT!" | panel | reward | next | home coins |
|---|---|---|---|---|---|---|---|---|
| 1-4 | 0.44 / 5.80 / 11.04 / 17.92 (4 stages) | 4.08 / 8.08 / 13.16 / 20.20 | 2:59 / 2:58 / 2:56 / 2:56 | 24.4 | 27.4 "Level 1-4" | 80 | Continue 28.34 → L5 | – |
| 5 | 28.36 | 31.22 | 2:50 | 41.64 | 43.60 | 20 | → L6 at 45.0 | – |
| 6 (heart-shaped board) | 45.0 | 47.24 | 2:38 | ≈70.6 | ≈72.2 | 20 | Continue 73.60 → **home** | 1000 → 1120 (+120) |
| 7 | Linked Arrows popup 76.44-80.04 → 80.04 | 81.36 | 2:50 | ≈92.2 | ≈94 | 20 | home ≈95 | 1140 |
| 8 | ≈97.8 | 99.48 | 2:50 | ≈111 | ≈114 | 20 | ≈115 | 1160 |
| 9 | ≈119 | ≈121 | 2:44 | ≈137 | ≈138 | 20 | ≈140 | 1180 |
| 10 | ≈142.6 | ≈144 | 2:27 | ≈178 | ≈180 | 20 | ≈181 | 1200 |
| 11 | Curtain popup 183.4-185.8 → 185.8 | ≈188 | 2:51 | ≈198 | ≈199 | 20 | ≈200 | 1220 |
| 12 | ≈202.4 | ≈204 | 2:45 | ≈220 | ≈222 | 20 | ≈223 | 1240 |
| 13 | ≈226 | ≈230 | 2:39 | ≈251 | ≈255 | 20 | ≈258 | 1260 |
| 14 | ≈261.6 | ≈264 | 2:51 | ≈273 | ≈275 | 20 | ≈276 | 1280 |
| 15 | ≈279.2 | ≈281 | 2:27 | ≈315 | ≈316 | 20 | ≈317 | 1300 |
| 16 | ≈319.4 | ≈321 | 2:47 | ≈334 | ≈336 | 20 | ≈337 | 1320 |
| 17 | ≈339.8 | ≈341 | 2:08 (the video skips ≈13 s at 360→361: 2:40 → 2:27) | ≈382 | ≈384 | 20 | ≈385 | 1340 |
| 18 | ≈390 | ≈392 | 2:47 | ≈405.4 | ≈407 | 20 | ≈408, red Play "Hard Level" | 1360 |
| 19 **Hard** | 411.84 | 416.28 | 2:13 | 464.2 | 467.6 (red, "☠ Hard Level ☠") | 60 | ≈471 | 1420 |
| 20 | ≈474.4 | ≈476 | 2:45 | ≈492 | ≈495 | 20 | ≈496, LEVEL 21 | 1440 |

- The clean start-state window for each board (the board is built and nobody has tapped yet) is from "board on screen" + 0.6 s to
  "first tick" − 1.0 s. Where that window is empty (L10, L12, L16, L17, L20: the first tap came within ≈1 s), take the frame at
  board + 0.6 s and check that it has no moving arrow.
- No heart is lost in V1. The last frames (499-505) are a YouTube end card.

## 2. V2 timeline (L11 → L39 on home)

Launch and menus first:
- 0-2.9 "grand" splash.
- 3.0-6.0 Loading with the iOS notification prompt ("'Maze Out!' muốn gửi thông báo …" / "Từ chối" / "Cho phép").
- 8-10 the recorder pulls down the notification centre.
- 11.8 **home at LEVEL 11, coins 1200, lives 5 Full**.
- 12-73: a menu tour (Shop 19-28, Leaderboard 29-34, Adventure 35, Settings 36-48, home 49, Profile / username 50-70, home 71,
  Shop 72, home 73). See §9.

| L | board (after any popup) | time left at win | "Well Done!" | panel | reward | home | coins | notes |
|---|---|---|---|---|---|---|---|---|
| 11 | 79.0 (Box popup 76.2-78.9) | 2:50 | ≈103.5 | ≈107 | 20 | ≈108 | 1220 | back → "Quit Level?" 80.75-82.6 → X; pause 83.1-86.6 and 88.2-89.1 (before the first tap) |
| 12 | ≈111 | 2:39 | ≈134 | ≈137 | 20 | ≈138 | 1240 | |
| 13 | ≈142 | 2:24 | ≈186 | ≈189 | 20 | ≈192 | 1260 | |
| 14 | ≈195 | 2:44 | ≈212 | ≈216 | 20 | ≈217 | 1280 | |
| 15 | ≈220 | 2:08 | ≈275 | ≈278 | 20 | ≈279 | 1300 | |
| 16 | ≈284 | 2:44 | ≈302 | ≈306 | 20 | ≈308 | 1320 | |
| 17 | ≈316 | 1:57 | ≈382 | ≈385 | 20 | ≈386 | 1340 | |
| 18 | ≈390 | 2:41 | 410.0 | 413.5 | 20 | ≈414 | 1360 | home: red Play "Hard Level" |
| 19 **Hard** | ≈417 | 1:52 | ≈491 | ≈494 | 60 | ≈495 | 1420 | |
| 20 | ≈500 | 2:42 | ≈519 | 522.25 | 20 | ≈523 | 1440 | |
| 21 | 528.75 (Pipe popup 525.25-528.7) | 2:44 | ≈548 | ≈552 | 20 | ≈553 | 1460 | |
| 22 | ≈555 | 2:28 | ≈589 | ≈593 | 20 | ≈594 | 1480 | |
| 23 | ≈596 | 2:17 | ≈644 | ≈647 | 20 | ≈649 | 1500 | |
| 24 | ≈652 | 2:11 | ≈705 | ≈708 | 20 | ≈709 | 1520 | home: "Hard Level" |
| 25 **Hard** | ≈712 | 1:40 | ≈793 | ≈797 | 60 | ≈798 | 1580 | |
| 26 | ≈801 | 2:30 | ≈833 | ≈836 | 20 | ≈837 | 1600 | |
| 27 | ≈839 | 2:06 | ≈895 | ≈899 | 20 | ≈900 | 1620 | |
| 28 | ≈902 | 1:51 | ≈973 | ≈976 | 20 | ≈977 | 1640 | home: purple Play "Super Hard" |
| 29 **Super Hard** | ≈979 | 0:20 | ≈1145 | ≈1148 | 100 | ≈1149 | 1740 | |
| 30 | ≈1153 | 2:40 | ≈1174 | ≈1177 | 20 | ≈1178 | 1760 | |
| 31 | 1183.25 (Elevator popup 1181.0-1182.9) | 2:36 | ≈1209 | ≈1212 | 20 | ≈1213 | 1780 | |
| 32 | ≈1216 | 2:26 | 1252.0 | 1255.5 | 20 | ≈1256 | 1800 | **2 hearts lost** (1235.20, ≈1250); won with 1 heart, and the panel still says "Perfect!" |
| 33 | ≈1259 | 2:02 | ≈1320 | ≈1323 | 20 | ≈1324 | 1820 | |
| 34 | ≈1327 | 2:27 | ≈1365 | ≈1369 | 20 | ≈1370 | 1840 | home: "Hard Level" + **iOS rating sheet 1372-1373.5 → "Để sau" (Not Now)** |
| 35 **Hard** | ≈1375 | 1:03 | ≈1498 | ≈1501 | 60 | ≈1502 | 1900 | |
| 36 | ≈1505 | 2:28 | ≈1540 | ≈1544 | 20 | ≈1545 | 1920 | |
| 37 | ≈1547 | 1:49 | ≈1621 | ≈1624 | 20 | ≈1625 | 1940 | |
| 38 | ≈1628 | 2:20 | 1672.0 | 1675.25 | 20 | ≈1676 | 1960 | home: LEVEL 39 "Super Hard" |

The two videos give the same coin track: 1200 on reaching L11 in both = 1000 + 80 + 6 × 20.

## 3. Screen flows (both videos, phone-confirmed where noted)

- **Level loop (from L7 on):**
  1. home → Play;
  2. [the obstacle unlock popup, the first time only];
  3. the level intro;
  4. play;
  5. the last arrow → the win sequence → the win panel;
  6. Continue → home (the "+N" coin payout; a new Hard/SH ribbon if the next level is one);
  7. Play.
  - There is no level-start dialog, no "Level N" card before a level, and no between-level ad.
- **FTUE exception:** Levels 1-4 → L5 → L6 chain without home (tutorials.md §1).
- **In level:**
  - back ◀ → "Quit Level?" / broken heart / "You will lose a life!" / red "Quit" / X (V2 `full/V2_t0081.50.png`);
  - pause ❚❚ → "Paused" / Sound, Haptic toggles / green "Resume" / red "Quit" / X (V2 `full/V2_t0085.00.png`; the phone is identical);
  - X on either panel returns to the board. While the timer has not started it stays at 3:00.
- **Fail flows:** never shown in the videos (no fails). The phone documented Out of Time → Continue? (streak) → Continue? (life) →
  Level Failed (flows.md).

## 4. Win sequence (V1 L5 at 25 fps, t0 = the last arrow leaves the board 41.20; `sheets/V1_L5_win_25fps.jpg`)

| t0 + s | beat |
|---|---|
| 0.00-0.40 | board-clear wave: a ring of rainbow-coloured dots (pink, yellow, green, cyan, purple) expands from the board centre through the vacated dot grid; then all dots fade |
| 0.44-0.84 | the blue "MAZE" sign (yellow letters, blue plate) swoops in on an arc from the lower left, spinning; it lands slightly tilted, just above the screen centre. At rest the MAZE plate spans ≈50-348 pt in x and ≈295-406 pt in y |
| 0.64-0.88 | the purple arrow-shaped sign (pointing right) swoops in from the bottom and lands under MAZE, spanning ≈418-524 pt in y. The logo group is centred at ≈(196, 410) pt |
| 1.00-1.64 | the white 3D "OUT!" letters appear on the arrow, balloon to wider than the screen (≈2.5×, at +1.16-1.52), then slam back into the sign (settled by +1.64) |
| 1.28-1.64 | the background dims to ≈90 % black (0.36 s) |
| 1.64-2.36 | confetti rain + two firework rockets from the bottom, bursting near the logo (≈+2.2) |
| 2.40 | the win panel pops in (the logo leaves at once); the confetti keeps falling behind it |

- The same beats appear at L1-4 (24.2 → panel 27.4), L6, L18 (405 → 407.2) and L19 Hard (464.0 → 467.6).
- The phone is the same ("MAZE OUT!" + confetti + fireworks, then the popup ≈2 s later; clips S1-L50-win-seq-*.mov). **Ours: the
  "ARROW OUT!" logo**, "ARROW" on the blue sign (it is longer than MAZE: widen the plate) and "OUT!" on the purple arrow.
- V2 instead shows a yellow **"Well Done!"** word with a blue outline. It writes in from the left in ≈0.5 s, over the undimmed board
  with confetti, then the panel follows ≈3.3-3.5 s after it starts (`sheets/V2_missing_panels.jpg`).
  That is the older skin; do not use it.

**Win panel** (V1 `full/V1_t0027.60.png`, `V1_t0043.60.png`):
- normal: a blue panel, the yellow tab "Level N", a red round X at the top right, "Perfect!", "Rewards:", a gold coin pile with the
  amount at its lower right, and a green "Continue";
- Hard: a red panel + the "☠ Hard Level ☠" ribbon; Super Hard: a purple panel + "☠ Super Hard ☠".
- The phone adds the Streak Race banner under the panel.

## 5. Level intro (V1 L5, Continue at 28.34; `sheets/V1_L5_hud_intro_25fps.jpg`, `V1_L5_board_buildin.jpg`)

- **28.32-28.64:** the whole HUD row drops in from above the screen. The pause button's top goes 45 → 77 → 96 → 105.6 pt
  (overshooting ≈38 pt below its rest) → 101 → 83 → 69 → rests at 67.7 pt by 28.64.
- **28.36-28.60:** the pill shows an empty timer bar and 3 empty (pale) heart slots.
- **28.64:** "3:00" appears ≈2.2× large and snaps to size by 28.72.
- **28.72 / 28.80 / 28.88:** hearts 1, 2 and 3 pop in with an overshoot (≈1.4× → 1).
- **28.88-29.08:** "Level 5" fades in under the pill.
- **Board:**
  - 28.36 the dot grid appears;
  - 28.36-28.72 every arrow grows from its tail to its head at the same time, and the heads pop on at the end;
  - built by ≈28.72 (≈0.36 s).
- The very first board (Levels 1-4 stage 1) skips the HUD intro: the HUD is already in place when the Loading screen cross-fades.
- Hard levels are the same, with the red "Hard Level" tab riding on the pill (V1 411.8-412.4).

## 6. Home payout after a win (V1 first home, 73.64; `sheets/V1_first_home_coins_25fps.jpg`)

- +0.25 s: a small coin pile and "+120" appear over the capsule machine / LEVEL plate. The text is white with a dark outline, and
  it sits above the pile.
- +0.80 → +1.36: 5 gold coins lift off one after another and fly in an arc (up and to the left) to the coin icon in the top bar.
- Each arrival adds reward/5 to the pill (1000 → 1024 → 1048 → 1072 → 1096 → 1120) and bursts a sparkle on the coin icon.
- All done by ≈+1.6 s.
- The LEVEL plate already shows the next level.
- Normal wins: "+20" in 5 steps of 4. Hard: "+60". Super Hard: "+100".
- The phone is the same (flows.md: "+20 animating").

## 7. Mistakes (bump) — V2 L32, 1235.20 (`sheets/V2_bump_L32.jpg`, `V2_bump_detail.jpg`)

- The player taps an arrow whose ray is blocked (here by an arrow that the elevator had just brought up). What follows:
  - a red vignette glows round all screen edges (≈0.3 s, fading);
  - the rightmost heart dims red → pale grey-blue in ≈0.2 s;
  - the tapped arrow and the blocking arrow draw dark navy for ≈0.4 s;
  - the tapped arrow STAYS dark for the rest of the level.
- There is no time penalty.
- The phone's rule and marker are in obstacles.md (BUMP: the arrow slides toward the blocker and back, and stays RED). **Use the phone's.**

## 8. Economy seen in the videos

- Starting coins **1000**.
- Rewards per level: **80** for "Level 1-4", **20** normal, **60** Hard, **100** Super Hard.
- The FTUE coins (L1-4, L5, L6) are paid out together on the first home (+120).
- Lives stay "5 Full" throughout (never lost).
- Boosters stay 3 of each, never used.
- **The V2 Shop** (Jul skin; the phone's shop wins; `sheets/V2_shop_full.jpg`). Header: coin pill + "Shop".
  - **Special Offers:** "90% OFF" badge; 1,000 coins + 1 of each booster + ∞ lives 1h; "Special Offer" **$0.99**.
  - **Bundles.** Each gives coins + N of each of the 4 boosters + ∞ lives for a period:
    - Mini: 2,000 + ×1 + 3h, $4.99;
    - Epic: 4,000 + ×3 + 6h, $9.99;
    - Elite ("Popular" ribbon): 8,000 + ×8 + 12h, $19.99;
    - Mega: 20,000 + ×18 + 36h, $49.99;
    - Legendary ("Best Value" ribbon): 60,000 + ×36 + 72h, $99.99.
  - **Coins:** 1,000 $1.99; 5,000 $7.99; 10,000 $14.99; 25,000 $29.99; 50,000 $54.99; 100,000 $99.99.
- **The V2 Settings page:**
  - "Notifications" ON/OFF pill toggle;
  - three round toggles "Sound", "Music" and "Haptic" (Music shown OFF with a red slash);
  - a green "Support" button;
  - blue "Terms" and "Privacy" buttons.
  - Frame `full/V2_t0036.50.png`.
- **"Adventure" tab (V2 only):** "Coming Soon".

## 9. SOCIAL / ONLINE screens (for the social-sim designer)

The only social screens in either video are in **V2 29-70** (Jul skin; nav tab "Leaderboard" = the trophy). Neither video shows
Streak Race, Claw Challenge, Sky Jump or Rocket Race anywhere: no badge, banner, popup or opponent list through V1 L21 / V2 L39.
The phone is the only source for those (flows.md: Streak Race banner and chips, Claw ladder, Sky Jump "Finding players …
100/100", "sharing the reward with 6 other winners", Weekly Contest podium; web-research.md §8: Rocket Race 5 lanes, the
Streak Race list of 5 with Kate/Max/James).

### 9.1 Leaderboard (V2 28.7-34.5; `sheets/V2_leaderboard_tabs.jpg`, `full/V2_t0029.50.png`, `V2_t0031.50.png`, `V2_t0033.50.png`)

- **Header:** "Leaderboard" (white, orange outline) on a blue bar. Tabs in a dark-blue segmented control: **"Weekly" | "World" |
  "Country"**. The selected tab is lighter blue. Phone v552: "Weekly" (green when selected) | "World" | the country's NAME ("Turkey").
- **The tab opens on Weekly.**
  - Before L50 it shows only the centred white text **"Reach level 50 / to compete in / Weekly Contest!"** on the navy page.
  - After L50 (phone) it shows the contest: a stopwatch countdown ("3d 6h"), a blue "Weekly Contest" banner with (i), a podium for
    the top 3 with coin prizes 2000 / 1000 / 500 and "Score : n", and the list with "Score n".
- **World (all-time, ranked by level reached; the player sees it from the top).** Rows are cream cards (≈382 × 60 pt of fill + a darker bottom
  lip, pitch 72 pt, x 5-388 pt): rank · avatar tile · name · "Level" caption + number on the right (dark-red outlined digits).
  - Ranks 1-3 get star badges: gold 1, blue-silver 2, bronze-orange 3. Rank 4+ is plain navy digits.
  - Data on 30 Jul 2026 (the game released 27 Apr 2026):

    | rank | name | level | avatar |
    |---|---|---|---|
    | 1 | Tetety | 11635 | avatar #4 (orange arrow-character in a black cap, winking) |
    | 2 | Bobby | 10040 | default blue silhouette |
    | 3 | Alex56k | 9120 | default |
    | 4 | Stacx251 | 9051 | default |
    | 5 | Ptr | 8795 | default |
    | 6 | Longy | 8443 | default |
    | 7 | Limminator | 8135 | avatar #8 (yellow arrow-character, party hat, star sunglasses) |
    | 8 | player_ah8prp7 | 8122 | avatar #4 |

  - The player's own World row was not scrolled to.
- **Country (the player's country; it opens AUTO-SCROLLED to the player's own row).** A translucent **"Top"** pill button floats
  over the first visible row (it jumps to rank 1).
  - The player's row is **bright green** with dark text.
  - Rows seen (a Vietnamese account at level 11):

    | rank | name | level |
    |---|---|---|
    | 127 | player_…a9hp (hidden behind "Top") | 14 |
    | 128 | player_lcx59yk | 14 |
    | 129 | player_b5s19jr | 13 |
    | 130 | player_d637jt8 | 12 |
    | 131 | player_prhx1ne | 12 |
    | **132** | **player_fiv0pqv (you)** | **11** |
    | 133 | player_v6t61ie | 11 |
    | 134 | player_3km8b0d | 11 |
    | 135 | player_ayeummj | 11 |

  - All of these have the default silhouette avatar.
  - Ties at the same level get consecutive ranks; the player sits FIRST among the level-11 group.
- **Default username format:** **`player_` + 7 random lowercase letters/digits** (for example player_fiv0pqv, player_3km8b0d). Most
  low-level players keep it. Players who set a name use short handles: "Tetety", "Bobby", "Alex56k", "Stacx251", "Ptr", "Longy",
  "Limminator"; the phone's podium/intro shows "Max", "Neo", "James", "Kate".
- **Implications for the simulation** (numbers only; the design is the social lane's):
  - The World board is level-based: dedicated players are at 8-12k levels about 3 months after launch (≈100+ levels a day). So the
    game must have effectively unlimited levels, or the board counts repeated levels.
  - The Country board is dense near a new player: rank 132 at L11 in Vietnam, so ≈131 Vietnamese players were at level ≥ 11, and
    ranks 127-135 span only levels 14 → 11. The player's rank is shown by scrolling to it.
  - The Weekly board is score-based (phone: "Score : 4" for the leaders, 3 days into the week), with a coin prize podium.

### 9.2 Profile (V2 50-70; `full/V2_t0050.20.png`, `V2_t0052.50.png`, `V2_t0053.50.png`, `V2_t0057.50.png`, `V2_t0069.50.png`)

- **Entry:** tap the avatar tile on home. The "Profile" page opens (a blue header, a red round X).
- If the player has no username yet, the **"Enter Username"** popup appears over it at once. The popup is a blue panel with a
  scroll-shaped title plate: **"Create your username:"** (dark red text) + a cream text field + a green **"Continue"** + a red X.
  The keyboard opens.
  - The player typed "Hihi" → Continue.
  - Not forced: it appears on opening Profile. Opening the Leaderboard first (29-34) did NOT prompt, although web-research.md
    suggests the Leaderboard can prompt too.
- **Profile page:**
  - an avatar tile with an orange pencil badge (edit), the name under it;
  - a purple pennant at the right reading **"Level" / "11"**;
  - a purple **"General Stats"** plate over a cream card with two stats: a red-target icon **"First Try Wins" 10** and a gold-medal
    icon **"Weekly Contest Wins" -** (a dash when zero or not unlocked).
- **Edit Profile** (the pencil):
  - a blue panel with title "Edit Profile", red X;
  - a cream row with the current avatar + the name field with a pencil;
  - a **3 × 3 avatar grid** (cream card; `ref/V2_edit_profile_avatar_grid.png`). Every avatar is an up-ARROW-shaped mascot with a face,
    on a coloured tile:
    1. the default blue silhouette (selected: green frame + green check);
    2. a green arrow with a big smile;
    3. a red arrow, winking, sunglasses pushed up;
    4. an orange arrow in a black cap, winking, peace sign;
    5. a blue arrow looking surprised, on pink;
    6. an orange arrow in a thinking pose;
    7. a yellow arrow in round glasses;
    8. a yellow arrow in a party hat and star sunglasses, tongue out;
    9. a pink arrow, winking.
  - a green **"Save"**.
  - The player picked #4; the Profile then shows it.
- **Ours:** the same screens and fields, with 9 avatars of our own: arrow-mascots with our own faces and accessories, the default
  silhouette first. The simulated players use the same 9 (+ the default). The "Weekly Contest Wins" stat is fed by the simulation.

### 9.3 What the videos do NOT show (so the phone and web data rule)

- Any event popup, race, opponent list, "finding players" matchmaking, point values or player counts.
- The Weekly Contest in progress (only its lock text).
- Any friends list, chat, sharing or login. There are no Facebook/Game Center buttons in Settings or Profile (V2).

## 10. Differences from the phone build (v552 = current)

See the full table in tutorials.md §11. Short version:
- visuals, HUD, boosters (2 vs 4), home nav (3 tabs = V1), win panel + Streak Race banner, events, bump colour and Hard/SH timers
  → follow the **phone**;
- captions, the FTUE order, L1-31 content and the unlock order for L7-L31 → from the **videos** (owner's order; V1 over V2 where they
  differ in skin: "Curtain" (V1, Aug) vs "Box" (V2, Jul) for the L11 obstacle);
- the phone uses "Box" for its L50 counter slab and "Door" for the key shutter.

**Naming decision needed (for the content/obstacle lane).** Choose between:
- keep V1's "Curtain!" card for the counter-shutter at L11 and the phone's "Box!" card for the counter-slab (L50); or
- use "Box!" for both.

The V1 curtain icon = the phone's door look, so the phone has re-skinned it. Recommended: the phone names + looks (Box for
counter-covers, Door+Key for key-covers). The L11 card then reads "Box! / Unlocked! / Clear required amount of arrows to break
the BOX!" (V2 = phone wording, exact).
