# Maze Out v552 — META (phone, meta explorer, 2026-09-25 04:27–)

Source: the owner's iPhone 15 (393×852 pt). Shots `research/shots/meta-NNN-*.png` (runner `shot`, 1178×2556 lossless), clips
`research/video/META-*.mov`, ledger `research/phone-meta-progress.md`. Game UI is ENGLISH; iOS prompts are Turkish (EN in brackets).
Coordinates are points. ONLINE = the screen shows other players' data that must come from a server (we simulate it offline, OWNER 02:33).

## 1. HOME (meta-001, 056, 073, 096)
Layout top → bottom (tap targets measured):
| element | where (pt) | tap → |
|---|---|---|
| avatar square (grey placeholder silhouette, blue frame) | (48,68) | **Profile** (§2) |
| coin pill "4214" with a green "+" badge | (150,70); + at (128,82) | **Shop** tab (§3) (the whole pill, not only "+") |
| lives pill: red heart with the count ("5"/"4"/"3", or "∞"), text "Full" / "mm:ss" countdown / ∞ "mm:ss"/"1h 20m" | (265,68) | Full or ∞: nothing (meta-038). Not full: **More Lives** popup (§6) |
| settings gear (blue rounded square) | (352,68) | **Settings** (§4) |
| Claw Challenge bar: purple hexagon-arrow token icon + streak badge "x100"/"x1" hanging under it, green progress "122/500", next reward icon (coin stack "300"), stopwatch "3d 5h" under the bar | bar (196,128) | **Claw Challenge** screen (§5.2) |
| left column badges: Streak Race (checkered flags, "5h 7m"), Rocket Race (blue-gold hexagon rocket, "Join"), Sky Jump (pink drum/cloud, "Join") | (47,235), (47,330), (47,425) | the event screen / offer (§5) |
| scene: purple furry scientist at a console with a big green button + red lever; a capsule machine full of coloured 3D arrows that churn; two yellow capsule workers (left: blue cap, wrench, walkie-talkie; right: green cap, glasses, clipboard) | — | tapping the scientist: no visible reaction (clip META-home-tap-scientist) |
| "LEVEL" / "62" plate (green; red for Hard, purple for Super Hard) | (196,540) | — |
| big green "Play" (red "Hard Level" / purple "Super Hard" variants) | (196,668) | starts the level (the LEVEL 50 Play first routed to the Weekly Contest unlock, flows.md) |
| bottom nav: Shop basket (68,805) · Home (196,800, raised, selected) · trophy (325,805) with a red "!" badge when the contest changed | — | tabs (§3, §7) |
- The red "!" on the trophy tab cleared after opening the Leaderboard once (meta-013 → later homes show no badge).
- The home re-reads the lives count live: "4 19:45" (05:28:22), "3 28:42" (05:49:25), "3 25:18" (05:52:49), "3 18:35" (05:59:32).
- Popups that appeared by themselves on the idle home (player notes): the Streak Race ranking (~4 min idle after L61), the Rocket
  Race offer after L54, the Sky Jump offer after L39. None appeared during this session's ~90 min of home visits.

## 2. PROFILE (meta-002..005)
- Full-screen blue page, title "Profile", red X (355,73).
- Card: avatar (grey, pencil badge at its corner (112,228)), name "Hsheh", "Level 62" tile.
- "General Stats" 2×3 tiles (icon + value): First Try Wins **57** (target icon) · Weekly Contest Wins **-** (gold medal "1") ·
  Streak Race Wins **-** (green flag-roll) · Rocket Race Wins **-** (rocket) · Sky Jump Wins **1** (pink drum) · Claw Challenge Wins **-**
  (purple hexagon token). "-" = zero.
- Pencil → "Edit Profile" popup (yellow title tab, red X (360,160)): avatar + name field "Hsheh" with a pencil (name editable);
  3×3 avatar grid (the grey default is selected with a green ✓; the other 8 are the capsule workers in costumes: blue cap, glasses +
  green cap, moustache + bowler, burger-hat, purple monster, pink sunglasses, goggles, yellow worker with pencil); green "Save".
  The grid does not scroll (meta-004). Closed with X, nothing saved.
- First Try Wins 57 at LEVEL 62 (61 levels passed; first-attempt fails known on the phone: L32, L33, L47, L52) → counts levels won on the
  first attempt (INFERRED; 61 − 4 = 57 ✓).

## 3. SHOP (bottom tab "Shop"; meta-007..012) — look only, no price tapped
Header: coin pill "4214" (no +), title "Shop". Sections (prices are the Turkish App Store's, TL; the US list is in web-research.md):
| section | item | content | price |
|---|---|---|---|
| Special Offers | "Special Offer", red "90% OFF" badge | 1 000 coins + bulb & hourglass **x1** + ∞ **1h** | 49,99 TL |
| Bundles | Mini Bundle | 2 000 coins + x1 + ∞ 3h | 249,99 TL |
| | Epic Bundle | 4 000 + x3 + ∞ 6h | 499,99 TL |
| | Elite Bundle, "Popular" ribbon | 8 000 + x8 + ∞ 12h | 999,99 TL |
| | Mega Bundle | 20 000 + x18 + ∞ 36h | 2.499,99 TL |
| | Legendary Bundle, "Best Value" ribbon | 60 000 + x36 + ∞ 72h | 4.999,99 TL |
| Coins (3×2 grid) | 1 000 / 5 000 / 10 000 / 25 000 / 50 000 / 100 000 | coin piles growing | 99,99 / 399,99 / 799,99 / 1.499,99 / 2.999,99 / 4.999,99 TL |
- "xN" in a bundle = N of EACH booster (bulb icon + hourglass icon shown together).
- NO "Remove Ads", NO "Restore Purchases" row, no free/ad item, no booster sold alone. The shop is a plain scroll (ends at the coin grid).

## 4. SETTINGS (gear; meta-029..037)
Title "Settings", red X (348,70). Rows:
1. "Notifications" with a bell, ON/OFF slider (ON = green "ON" + blue knob right). Tap toggles instantly, no iOS prompt, no toast (meta-032/033).
2. "Sound" / "Music" / "Haptic": three green square buttons (speaker, note, phone-vibrate icons). OFF = a red diagonal slash across the
   icon (the button stays green) — meta-030. No toast.
3. Green "Support" (196,476) → leaves the game into the iOS **Mail** composer: To `help-mazeout@grand.gs`, Subject "Grand Games Maze Out!
   Support Ticket", body "Please describe your issue above. We will get back to you as soon as possible." + "DeviceID : <uuid>" "Version : 552"
   "LevelId : -1 - 62" (meta-035; address/ID redacted in our shots). Nothing was sent; draft deleted.
4. Blue "Terms" / "Privacy" (open the web; NOT tapped — out of the app).
- **Owner's state (restored exactly):** Notifications ON, Sound ON, **Music OFF**, Haptic ON. We toggled Sound off→on and Notifications
  off→on once each (verified by pixels).
- **The Music button is INERT**: 4 attempts (taps at (196,343) ×2, (200,352), a 0.3 s press; 07:33–07:38) left it OFF while Sound toggled
  normally → music cannot be switched on in v552 (consistent with no music anywhere). Settings restored pixel-identical (meta-136 = meta-029).
- No language option (the game shows ENGLISH on a Turkish iOS → English-only build, INFERRED).
- In-level pause panel has only Sound + Haptic (no Music) — see fail.md.

## 5. EVENTS
### 5.1 Streak Race (left badge 1; meta-045..053) — ONLINE-looking
- Header art (capsule workers on a pink slide), (i) (25,72), X (355,72); "Streak Race" logo; "Beat levels without fail to get more rewards!";
  chips x1 x5 x10 x25 **x100** (current = green, framed gold); stopwatch "5h 13m" (the race ends; a new one starts).
- Ranking of **50** players: rank hexagon (gold 1 / silver 2 / bronze 3; plain numbers after), avatar, name, coin prize plate
  (**2000 / 1000 / 500 / 100×7** for ranks 1–10; none from 11), green flag-roll + score (flags).
  Scores at 04:46: 3530, 3423, 2950, **2065 (player, rank 4, GREEN row)**, 1882, 1846, 1827, 1800, 1628, 1364, 1311, 1306, 1038, 909, 906,
  873, 798, 782, 721, 706 … 28:282, 29:226, 30:183, 31:143, 32:142, 33-35:141, 36:6, 37:5, 38-41:1, 42-50:0.
  141 = 1+5+10+25+100 = exactly one full climb from x1 to x100 → **score per win = the current multiplier** (x1, x5, x10, x25, x100, then
  x100 per further win). Many bottom rows are idle (0).
- (i) → overlay "Streak Race": maze icon "Beat levels without losing!" → "x5 [x10] x25" "Increase your score multiplier!" → 3 mini rows
  "Earn more flags than others!" → red card "If you fail a level the multiplier will reset!" → "Tap to Continue" (meta-053).
- The fail flow shows the multiplier reset x100 → x1 (fail.md). Player's names: SteelLion34, Mas, karl, Gatorgirl, Ceb, RetroWizardBoss,
  KG__BigTicket, Nosir, player_xzmx6lp, DigitalBear, SaltyWizardPro, JOKER9, Radio, Smid, SneakyGoblin90, Gdoc, player_ot50r1w, Mario,
  FastDog … mahdi, player_xx50fh7, Coco, Ginger, IronGiantX, Meo, Peps, Smitty, StevieB, TaLele ("player_xxxxxxx" = default names).

### 5.2 Claw Challenge (bar under the top row; meta-039..044)
- Header art: claw machine with the two capsule workers and prizes (bulbs, hourglasses, hearts, arrows); (i), X; "Claw Challenge" logo;
  stopwatch "3d 5h"; "Beat levels without fail to get more rewards!"; chevron chips x1 x5 x10 x25 x100 (current = orange/gold);
  bar "122/500" with the next reward (300 coins).
- Vertical ladder 1 (bottom) → 20 (top), locked cards with a padlock, done cards with a green ✓. Full ladder (steps 1–5 from session 1):
  1 ∞ 30m · 2 100 coins · 3 ∞ 30m(?) · 4 200 coins · 5 ∞ 1h · 6 ✓(bulb x1) · **7 300 coins (next)** · 8 ∞ 2h · 9 400 coins · 10 ∞ 3h ·
  11 hourglass x2 · 12 ∞ 4h · 13 bulb x2 · 14 2000 coins · 15 ∞ 5h · 16 500 coins · 17 bulb x1 · 18 600 coins · 19 ∞ 6h · 20 10000 coins.
  (Steps 1–6 as claimed by the players: ∞ 30m, 100 coins, ∞ 30m, 200 coins, ∞ 1h, bulb x1 — order from the ledgers, ladder art for 1–5
  not re-shot this session.)
- Step targets seen on the bar: 0/1, 0/200, 37/300, 37/400, 40/300 (?), 22/500, 22/500 (ledgers) → targets 1, 200, 300, 400, (300), 500, 500 points; points per win = the current streak multiplier (flows.md); a fail does NOT
  subtract points but resets the multiplier (the "You will lose 100 token" line = the bonus you would forfeit).

### 5.3 Rocket Race (left badge 2; meta-054) — ONLINE-looking race vs 4 rivals
- Offer popup: "Rocket Race" logo with a rocket, stopwatch "5h 8m", chest of coins + hearts on a moon, planets "Stage 1 / Stage 2 / Stage 3",
  "Beat **5 Levels** before others to win and advance to next stages for greater prizes!", green "Start", X (361,197). Not joined.
  (The first-ever offer showed "Start [∞]" and a prize bubble "500 + ∞ 45m"; this re-offer shows plain "Start" and no bubble.)

### 5.4 Sky Jump (left badge 3; meta-055) — ONLINE-looking elimination (100 players)
- Stage-2 offer: "Sky Jump" logo, stopwatch "5h 7m", arrow sign "PRIZE 7000", silver chest of coins, chests "Stage 1 ✓ / Stage 2 / Stage 3",
  "Pass **7 Levels** in a row on first try and advance to next stages!", "Start", X. Not joined. (Stage 1 = 5 levels, prize 5000 shared.)

### 5.5 Weekly Contest (trophy tab; §7)

## 6. LIVES UI
- Max 5. Home pill: "5 Full"; "4 19:45"; "∞ 29:11" (∞ symbol inside the heart, timer = time left of unlimited lives).
- **More Lives** popup (lives < 5, meta-095): yellow tab "More Lives", heart with "3" and a "+" , "Time to next live:" + stopwatch "27:04",
  green **"Refill [coin] 900"**, green **"[video-clapper][heart] +1 Live"** = a REWARDED AD for one life (the store says "ad-free" — this is
  an opt-in ad; not tapped), X (361,197). Refill/regen rules → economy.md.

## 7. LEADERBOARD (trophy tab, "Leaderboard"; meta-013..028) — ONLINE
- Tabs **Weekly** (green = selected) | **World** | **Turkey** (the player's country); stopwatch "3d 5h" under Weekly (contest end).
- Weekly: blue banner "Weekly Contest" + (i) (25,255); podium 2 (lilac, left) / 1 (gold, centre, tallest) / 3 (orange, right) with avatar,
  rank hexagon, name, prize coins **1000 / 2000 / 500**, "Score : 19 / 27 / 14"; list rows 4…10 "rank · avatar · name · Score n":
  4 **Hsheh 12 (GREEN, the player)**, 5 LoudRat 9, 6 SneakyFalconer51 9, 7 ChillKnight71, 8 MagicGoose 8, 9 Boo 6, 10 Mema 4 → a
  **10-player group**; Score = levels won this week since the contest unlocked (the player won L50–L61 = 12 ✓).
  (i) → the "Weekly Contest" intro overlay ("Beat Levels!" / podium Max 1000, Neo 2000, James 500 "Contest with others!" / coins "Win Rewards!" /
  trophy "Compete against your friends! There is a new contest every week!" / "Tap to Continue").
- World: rows "rank · avatar · name · Level NNNNN" (gold/silver/bronze hexagons for 1–3): player_ah8prp7 14669, Winner 13344, ezbee 13115,
  Tetety 12699, Sunshine 12003, Limminator 11536, Crazzijj 11386, Han … ~#89 5154, ~#278 3096; loads in pages as you scroll, a green
  "Bottom" pill at the end of a page jumps/loads further. The player's row is not pinned on World.
- Turkey: opens scrolled to the player: 452 rng 63, 453 turko 63, 454 Gulyabani 62, **455 Hsheh 62 (green)**, 456 player_8jgl4qr 62 …;
  top: Caco17 10824, Mrmş 3323, Namnam 3193, Dug 2575, Hakki 2401, player_g5r28yh 1604, Seyhan 1349. The player's row stays pinned at the
  bottom edge while scrolled away.
- Level counts > 552 show that levels continue far beyond the store's content (14669 = generated/looping content, INFERRED).

## 8. Home idle / animations
- Clip **META-home-idle-12s** (15.1 s of frames, 911 samples, no touches, clean) — measured by frame differencing at 10 fps
  (best repeat lag = loop period):
  | region | motion | loop |
  |---|---|---|
  | scientist (breathing / blinking / head tilt) | small, continuous | **≈3.16 s** (repeats at 3.2, 6.3, 9.5 s) |
  | right worker (glasses, clipboard: writes, looks up, nods) | large pose changes | **≈10.2 s** |
  | left worker (walkie-talkie: talks, thinks, winks, waves) | large pose changes | no repeat inside 15 s (> 15 s or randomised) |
  | capsule machine arrows, Play button, background pipes | static (mean frame diff < 0.1) | — (no idle pulse on Play) |
- The lives pill counts down live every second on the idle home.
- Clip META-home-tap-scientist: tapping the scientist gives no reaction (only the idle loop).
- Every META clip's audio track is digital zero. The recorder DOES capture app audio (sounds.md pass 2: Play click, home-return cues),
  so these are verified SILENT moments of v552: home idle with Music OFF, tapping the scientist, a tape-bundle bump, the timer's last
  seconds and the "Out of Time!" entrance, the hourglass flight/frost, the bulb pan/blink.
