# Maze Out — flows (phone session 1). Game UI is ENGLISH; iOS prompts Turkish.

## In-level HUD (shots/003)
- Top-left coin pill "2240" (coin icon). Row below: back button (blue square, white ◀) at (38,88) pt; centre pill: tab "Level 32" above,
  stopwatch icon + "3:00" timer + 3 red hearts; pause button (blue square, ❚❚) at (352,88).
- Bottom: left booster (green rounded square, crystal/magnet icon, red badge "3") at (40,790); right booster (light bulb, badge "3") at (352,790).
- Board: white background, black snake arrows.

## Pause (shots/007)
- Tap ❚❚ → dim + panel "Paused": rows "Sound [ON]" and "Haptic [ON]" toggles, green "Resume" (123,530), red "Quit" (269,530), red close X (361,256).
  The timer is frozen while paused.

## Fail by time (L32 attempt 1, shots/013-016)
1. "Out of Time!" — big blue stopwatch, "+30 sec", green button "Add Time [coin] 900"; top-right: coin pill "2240" with green +, red X (350,76).
2. X → "Continue?" panel: "You will lose your streak!" + streak chips x1 (lit, green) x5 x10 x25 x100; green "Play On [coin] 900"; X (362,238).
3. X → "Continue?" panel: "You will lose a life!" + broken red heart; green "Play On [coin] 900"; X (362,238).
4. X → "Level 32" panel: broken heart, "Level Failed!", green "Try Again"; X (362,229). Below: "Streak Race" banner (checkered flags),
   stopwatch "9h 16m", chips x1 (lit) x5 x10 x25 x100.

## Win (L32, shots/020)
- Popup over dimmed board: yellow tab "Level 32", title "Perfect!" (white, blue outline), "Rewards:", coin stack + "20", green "Continue"
  (196,538), red X (361,207). Bottom: Streak Race banner (checkered flags) "9h 9m", chips x1 x5 x10 x25 x100 — x5 lit after this win.

## Claw Challenge (first shown after L32 Continue; shots/021-025)
- Full screen: header art = claw machine with two yellow capsule workers and prizes; (i) (27,70); red X (357,72).
- "Claw Challenge" logo, stopwatch "3d 9h", "Beat levels without fail to get more rewards!", chevron chips x1 (lit) x5 x10 x25 x100,
  progress bar: purple hexagon-arrow icon, "0/1", reward icon ∞-heart "30m".
- Vertical reward ladder, numbered nodes 1..20 with locked cards: 1 ∞heart 30m, 2 100 coins, 3 ∞heart 30m, ... 17 bulb x1, 18 600 coins,
  19 ∞heart 6h, 20 10000 coins. On first open it auto-scrolls from 1 up to 20.
- (i) → overlay: "Claw Challenge", maze icon + "Beat levels without losing!", "x5 [x10] x25" + "Increase your score multiplier!", coin pile.
  Tap anywhere closes it.

## Home (after L32, shots/026)
- Top bar: avatar (grey placeholder) · coin pill "2260" with green + · lives heart "5" + "Full" · settings gear.
- Claw bar under it: hexagon icon + "x1" badge, "0/1", ∞-heart 30m, stopwatch "3d 9h".
- Left: Streak Race badge (checkered flags) "9h 7m".
- Scene: purple monster in lab coat at a console with a green button; capsule machine full of coloured 3D arrows; two yellow capsule
  workers (walkie-talkie; glasses + clipboard); "LEVEL 33" plate; big green "Play" (196,668).
- Bottom nav: shop basket (68,805) · Home (196,800, raised, selected) · trophy (325,805).

## Hard / Super Hard (L34, L39)
- Home: the Play button turns RED with a "Hard Level" ribbon (L34) or PURPLE with a "Super Hard" ribbon (L39); the LEVEL plate turns the same colour.
- In level: the Level tab + back + pause buttons take that colour (red / purple); the timer pill stays blue.
- Win popup: panel in that colour, a ribbon "☠ Hard Level ☠" / "☠ Super Hard ☠" above the yellow "Level N" tab; rewards 60 (Hard L34) / 100 (Super Hard L39) vs 20 normal.

## Win celebration (L36, shots/049)
- After the last arrow: dim + big "MAZE OUT!" logo (yellow MAZE on a blue sign, white OUT! on a purple arrow sign), confetti, two firework
  rockets; then the win popup (~2 s later).

## Feature unlock (L35, shots/040)
- Dim overlay over the level: "Pipe!" (white, blue outline), "Unlocked!", the pipe icon with a "3" counter, cream card with blue border
  "Pass arrows through the PIPE to break it!" (PIPE in blue). Tap anywhere → the level (timer not yet started).

## Claw Challenge rewards
- Step 1 (after the 1st win with the event): "Congratulation(s)!" + ∞-heart "30m" + "Tap to Claim" → lives show ∞ with a countdown (shots/033-035).
- Home bar then counts points toward the next step: 0/200 → +5 (x5) → +10 (x10) → +25 (x25) → +100 (x100): points per win = the current
  streak multiplier. Bar 5/200 → 15 → 40 → 140 → (+100) → reset "37/300"/"40/300" with a 30m ∞-heart reward next; +100 coins arrived on home.

## iOS rating prompt (after L34, shots/039)
- System sheet: app icon, "Maze Out! hoşunuza gidiyor mu?" (Do you enjoy Maze Out!?), "App Store'da puanlamak için yıldızlara dokunun."
  (Tap the stars to rate on the App Store.), 5 stars, "Şimdi Değil" (Not Now) → declined.

## Sky Jump (appeared on home after L39 via a new red 'Join' badge; shots/065-070)
- Popup "Sky Jump" (white/yellow logo), stopwatch "8h 14m", art: arrow sign "PRIZE 5000" + open chest of coins; three chests "Stage 1"
  (green) "Stage 2" (blue) "Stage 3" (pink); "Pass 5 Levels in a row on first try and advance to next stages!"; green "Start"; X.
- Start → "Finding players on your level." counter 29/100 → 100/100 with a fan of avatar tiles (yellow capsule characters) + the player's
  grey avatar in a green frame; "Tap to Continue".
- Tutorial overlay: "Start with 100 players!", "Beat 5 levels!", "Win your share of 5000 coins!", "Advance to next stages for greater
  prizes!", red card "If you fail a level, you will fail the challenge!", "Tap to Continue".
- Event screen: sky + clouds, numbered jump pads 1-4 leading to the prize island (PRIZE 5000 chest), two more islands above (later
  stages); header "Stages" (3 dots), "Levels 0/5", "Players 100/100", stopwatch "23h 58m"; (i), X. Player avatar bottom-left.
- Sky Jump progress after each win (before home): the event screen with "Levels n/5" and "Players" dropping (100 → 82 → 64 → 47 → ...),
  the player's avatar hopping to the next pad, "Tap to Continue" (shots/080, 084, 088).
- Stage won after 5 first-try wins (L40-L44): "Congratulations!" + prize island + "You win!" coin plate counting up (367 → 714), the
  player's avatar and "You are sharing the reward with 6 other winners!" + winner avatars (shots/094); then "Congratulations!" coin stack
  "714" + "Tap to Claim" (shots/095) → home; the Sky Jump badge shows "Join" again (next stage).  5000 / 7 winners = 714.
- Stage 2 offer right after the claim: 'PRIZE 7000', Stage 1 ✓, 'Pass 7 Levels in a row on first try and advance to next stages!', Start, X — closed with X (not joined) to save time (shots/096). Coins 2760 → 3474 (+714).

## Player part 2 additions (02:35–)

### Fail flow text change once the Claw Challenge is running (L47, shots/113)
- 2nd popup now reads "Continue?" / "You will lose 100 token and your streak!" (purple hexagon token icon left of the text; '100' in red)
  + streak chips x1 x5 x10 x25 x100 where an orange x1 chip slides over the current one; "Play On [coin] 900"; X (362,238).
  The Claw bar was NOT reduced by the fail (140 before, 141 after the next x1 win): the '100 token' is the multiplier bonus you forfeit.
- Life refill: a lost life (02:47) showed '4 / 15:56' at 02:50 and was back to '5 Full' by 03:07 → ~20 min per life.

### Weekly Contest unlock (first Play tap on the LEVEL 50 home, shots/130-133, clip video/S1-weekly-contest-open.mov)
1. Tapping Play did NOT start the level: dim overlay, cream card with blue border "Tap to compete in Weekly Contest!", a big yellow
   arrow pointing DOWN at the trophy tab (325,805), which is highlighted (bright blue square) — the only live target (shots/130).
2. Trophy tab → full-screen intro over the Leaderboard: title "Weekly Contest"; maze-icon card + "Beat Levels!"; yellow arrow →
   podium of three capsule avatars (Max 1000 / Neo 2000 / James 500, 'Neo' centre on the tallest gold block) + "Contest with others!";
   arrow → coin pile + "Win Rewards!"; trophy + "Compete against your friends! There is a new contest every week!"; "Tap to Continue" (shots/131).
3. Leaderboard screen (shots/132): title "Leaderboard"; tabs "Weekly" (green, selected) | "World" | "Turkey"; stopwatch "3d 6h" under
   Weekly; blue banner "Weekly Contest" + (i); podium 1st (centre, gold block, 2000 coins, "Score : 4"), 2nd (left, lilac block,
   1000 coins, "Score : 4"), 3rd (right, orange block, 500 coins, "Score : 3"), each with a grey avatar and a rank hexagon; below a
   scrolling list of cream rows "rank · avatar · name · Score n" (rows 7–10 visible), the player's own row GREEN (rank 10, score 0).
   Bottom nav: shop · home · "Leaderboard" (selected, raised).
4. Home tab → home (LEVEL 50, Play works again).

### Rocket Race (appeared on home after L54 won; free join; shots/163-168)
1. Popup (auto, on home): logo "Rocket Race" (rocket), stopwatch "6h 20m", art: treasure chest of coins + a heart on a moon, a tooltip
   bubble "[coins] 500 + [∞-heart] 45m" (the stage-1 prize), three planets "Stage 1" (lit) "Stage 2" "Stage 3", text
   "Beat 5 Levels before others to win and advance to next stages for greater prizes!" (5 Levels in yellow), green "Start [∞-heart]", X (361,197).
2. Start → "Congratulations!" ∞-heart "30m" "Tap to Claim" (joining gives 30 min of infinite lives) (shots/164).
3. Tutorial (animated, shots/165-166): "Rocket Race" — maze card "Beat levels!" → rocket "Finish race before others!" → chest
   "Win amazing rewards!" → three planets "Advance to next stages for greater prizes!"; "Tap to Continue".
4. Race screen (shots/167): header art, "Stage 1" tag (left), stopwatch "6h 14m" (right), (i) (25,72), X (355,72); banner
   "Rocket Race"; "Beat 5 levels before others to finish the race"; 5 vertical lanes, each a rocket (player's = red/yellow, others blue)
   with a counter bubble "0" above and a name tile below (player's tile green); a gold winged rank badge "1" at the top of lane 1.
5. X → home: a new Rocket Race badge on the left column (hexagon with a number + timer).
6. Race lost (auto-shown on home after L57, when a rival reached 5/5 first; shots/178 mid-race, 183 lost): same screen, text
   "You lost the race! Try again to win amazing rewards!", the winner's lane topped by a card with the gold rank badge "1" over a chest,
   green "Continue" (196,780) → home; the Rocket Race badge reads "Join" again (not re-joined).
   Note: the rivals advance on their own clock (3/5 and 4/5 after the player's 1st win), so 5 wins in a row at ~5 min each lost the race.

### Streak Race leaderboard (appeared on its own over the idle LEVEL 62 home ~4 min after L61; shots/203)
- Full screen: header art (capsule workers riding a pink slide), (i) (25,72), X (355,72); "Streak Race" logo; "Beat levels without fail to
  get more rewards!"; chips x1 x5 x10 x25 x100 (x100 lit green); stopwatch "5h 36m"; ranking rows: rank hexagon (2 silver, 3 bronze,
  4+ plain number) · avatar · name · coin prize plate (1000 / 500 / 100 / 100 / 100) · green token score (3423, 2950, player 2065, 1882, 1846);
  the player's row is GREEN (rank 4). X → home (shots/204).

## Meta explorer additions (2026-09-25 04:27–, shots meta-NNN; full detail in meta.md, fail.md, boosters.md, economy.md)

### Home taps (meta.md §1)
- avatar (48,68) → "Profile" (General Stats; pencil → "Edit Profile": name + 9 avatars + "Save"); coin pill → Shop tab; lives pill → nothing
  when Full/∞, "More Lives" popup when < 5 ("Time to next live:", "Refill [coin] 900", "[video][heart] +1 Live" rewarded ad); gear → "Settings";
  Claw bar → Claw Challenge; left badges → Streak Race ranking / Rocket Race offer / Sky Jump offer; trophy → "Leaderboard".

### Settings (meta-029)
- "Notifications" [ON] slider · "Sound" "Music" "Haptic" square toggles (OFF = red slash over the icon) · "Support" (→ iOS Mail composer to
  help-mazeout@grand.gs, subject "Grand Games Maze Out! Support Ticket", body with DeviceID / Version : 552 / LevelId) · "Terms" · "Privacy".
  Owner's settings: Sound ON, Music OFF, Haptic ON, Notifications ON (restored). No language option.
- iOS strings met: Mail account alert → "Vazgeç" (Cancel); composer close → "Taslağı Sil" (Delete Draft).

### Leaderboard tabs (meta-013..028)
- "Weekly" (10-player group, podium 2000/1000/500 coins, "Score : n", player row green) · "World" (rank by "Level", paged with a "Bottom" pill) ·
  "Turkey" (opens on the player's row, #455 Level 62). Bottom nav label "Leaderboard" under the raised trophy.

### In-level
- Back button (38,88) → "Quit Level?" / "You will lose a life!" / broken heart / red "Quit" / X — also before the first tap.
- Pause (352,88) → "Paused": "Sound" [ON] and "Haptic" [ON] sliders (no Music), "Resume", "Quit" (→ the same "Quit Level?"), X.
- Bulb booster → camera zooms to max on a free arrow, which blinks green twice and stays green; timer not started.
- Hourglass booster → timer frozen 10 s: icy hourglass flies to the stopwatch, frost vignette, "10" countdown bar under the timer pill.

### Fail chain v552 (fail.md §1)
- Timer 0 → "Out of Time!" (+30 sec, "Add Time 900") · 3rd heart → "Out of Lives!" ("+3 Lives", "Add Lives 900") → [streak > x1 only]
  "Continue?" "You will lose 100 token and your streak!" ("Play On 900") → "Continue?" "You will lose a life!" ("Play On 900") →
  "Level N" / "Level Failed!" / "Try Again" + Streak Race strip (x1 lit). X → home; Try Again → identical board.

### Timer end + lives (meta)
- In-level timer "m:ss" ("0:18" … "0:01" "0:00"), no colour/pulse in the last seconds; "0:00" holds 1.61 s, then "Out of Time!" appears in one frame.
- Home lives pill: "5 Full" (no badge) / "4 29:59" with a green "+" on the heart; under a minute "00:12"; at zero "Finished" for ~1 s; 30:00 per life, counted
  from the LEVEL START that took the life; a win refunds it (economy.md §2).
- Settings "Music" button does nothing on v552 (stays OFF).
