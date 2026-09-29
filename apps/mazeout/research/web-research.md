# Maze Out! — web research (W-desk, 2026-09-25)

Scope: public web only. I did not use the phone, a simulator or a logged-in browser. I used curl, WebSearch and WebFetch.
Raw evidence is under `research/web/`:
- `store/`: App Store HTML and JSON, iTunes lookups, Google Play probes.
- `reviews/`: RSS JSON per country and sort, `all_reviews_merged.json` (61 unique reviews), and the App Store web "see all" reviews.
- `storyboards/<videoId>/`: YouTube storyboard sheets, split frames, contact sheets and `ocr.jsonl` (Vision OCR of every frame).
- `thumbs/`: YouTube thumbnails. For Shorts these are the `oar*` files: full-resolution 884–888 × 1920 portrait frames.
- `yt_frames/`: 142 annotated evidence frames and composites.

**Tags.**
- **VERIFIED**: seen in a primary source, meaning a store page, an in-game frame or thumbnail, or a win or unlock panel readable by OCR.
- **INFERRED**: reasoned from several signals, or read from low-resolution frames.
- **UNKNOWN**: no evidence found.

**Precedence.** Phone (current build v552) > help centre (none exists, see §1) > store screenshots > recent videos > older videos > reviews.

> **Main caveat for the build team: the level CONTENT changes between builds, and the game is heavily A/B-tested.**
> - **Boards change across builds. VERIFIED.**
>   - The May 2026 boards for L5, L6, L8, L10 and L12 differ from the August boards (`yt_frames/compare_may-build-L6-8-10-12-5_vs_aug-build.jpg`).
>   - The phone's L32 (Sep 25, v552) matches none of the July 30 boards for L31–34 (`yt_frames/compare_gamemobie-jul30-L31-34_vs_phone-sep25-L32.jpg`).
>   - The July 30 and August 17 boards for L11–20 DO match each other.
> - **The HUD changes across builds too.**
>   - Booster bar: 4 boosters in Jul 30 and Aug 17; none visible in Aug 13 and Sep 10; 2 boosters on the phone.
>   - Timer and hearts: see §2.
>   - Obstacle skins: the curtain was a purple drape, then a cyan box, then a purple crate, then purple side panels.
> - **What this means for levels.** Treat every video level below as the *shape of the curve* (size, density, which obstacle, where Hard
>   levels fall), not as exact level data. Exact boards come only from the phone. L1–31 exact data needs the owner's reinstall.

---

## 1. Identity

| Item | Value | Tag / source |
|---|---|---|
| Store name | "Maze Out! - Tap Puzzle" (home screen "Maze Out!") | VERIFIED: iTunes lookup us+tr, `store/lookup-*.json` |
| Former name | **"Arrow Jam!"** at launch. The splash showed an "ARROW JAM!" logo on a sky background, and the store text read "Welcome to Arrow Jam!". The bundle id is still `com.grandgames.arrowjam`. The rename happened between about 2026-06-06 (a video still shows the Arrow Jam loading screen) and 2026-07-30 (the Maze Out logo). | VERIFIED: videos `6tObwJPw-JA` (description text + loading frame), `23yqNmkXmTU`, `NoX3FIf4hMs`; `yt_frames/iostouchplay_L00_loading-arrow-jam.jpg` |
| App id / bundle | 6762192889 / com.grandgames.arrowjam | VERIFIED |
| Seller | GRAND GAMES OYUN VE YAZILIM ANONIM SIRKETI; developer name "Grand Games A.Ş.", Istanbul; © Grand Games A.Ş. | VERIFIED: store page |
| Release | 2026-04-27 (v59, notes dated 2026-04-26); current v552, 2026-09-21 | VERIFIED |
| Rating | US 4.68★ from 1,435 ratings; TR 4.63★ from 30 | VERIFIED: lookup 2026-09-25 |
| Chart | #200 in Puzzle (US) | VERIFIED: store ribbon |
| Size / min OS | 334.6 MB; iOS/iPadOS 13.0+; universal (iPhone, iPad, iPod touch) | VERIFIED |
| Languages | English, Portuguese, Spanish (no Turkish; the phone shows an English UI) | VERIFIED: store. A launch-week video shows the UI in Portuguese ("Continuar", "Tentar de Novo", "Nível 9"), `yt_frames/carlospereira_L09_*.jpg` |
| Age rating | 4+, "Contains Advertising" annotation, although the store copy says "Ad-free Experience" | VERIFIED: store "information" shelf |
| Accessibility | "The developer has not yet indicated…" | VERIFIED |
| Privacy label | **Data Used to Track You**: Identifiers (User ID, Device ID); Usage Data (Product Interaction, Advertising Data). **Data Linked to You**: Purchases (Purchase History), Location (Coarse), Contact Info (Name, Email), User Content (Customer Support), Diagnostics (Crash, Performance, Other), Identifiers, Usage Data, Other Data. **Purposes**: third-party advertising, developer marketing, analytics, product personalisation, app functionality. | VERIFIED: `store/appstore-us-data.json` privacyHeader shelf |
| Privacy policy | grand.gs/privacy.html (generic Grand policy, effective 2023-12-26). It mentions IDFA, Game Center ID, AWS servers in the US, "local and global leaderboards", profile data seen by other players, and SNS login. It names no SDKs. | VERIFIED: `site/grand-privacy.txt` |
| Help centre / FAQ | **None found.** grand.gs has only About, Games, Careers, Privacy and Terms. *.grand.gs subdomains are wildcards pointing to the homepage. support.grnd.gg is a different company (Grand Mobile, on Intercom). grandgames.zendesk.com returns 403. In-app, Settings has a "Support" button (July build), and the privacy label's "User Content: Customer Support" points to an in-app ticket tool. | VERIFIED absence (curl probes); in-app support UNKNOWN beyond the button |
| Google Play | **Not on Google Play.** Grand Games' Play developer page (id 6430038787206489041) lists only Magic Sort, Car Match and Block Out. `com.grandgames.arrowjam` returns 404. An Android video titled "Maze Out Games" (`EiimDCMzIbk`) is a different game. | VERIFIED 2026-09-25 |
| Sister games | Magic Sort! (water sort, 653K ratings), Block Out! (color block, 261K), Car Match (111K), Pixel Pop! (color shooter, ad-free, offline), Block Star. The founders came from Good Job Games (Zen Match). Per Naavik on Magic Sort: weekly, country and global leaderboards; milestone events (Broom Streak) and race events (Jetpack Race); a new event about every 2 months; pay-to-continue a failed level to keep a streak. | VERIFIED: store "More by developer"; naavik.co |
| Launch framing | Nextbiggames short (2026-04-29), "Grand Games Enters the Arrow Puzzle Race — And It's Premium!": ad-free, "plenty of moves", "casual approach". | VERIFIED: `yt_frames/primegaming+nextbiggames_L27-keys_hq-thumbs.jpg` |

**Version history (all "What's New" notes).**
- 552 (Sep 21): "New Event: Claw Challenge! Beat levels without losing and increase your multiplier to win amazing rewards!"
- 507 (Sep 14) and 463 (Sep 3): "Bug Fixes & Improvements. Enjoy!"
- 443 (Aug 31): "Meet our newest event: **Sky Jump**! Complete stages by beating levels in a row on your first try and advance to next stages for greater prizes!"
- 372 (Aug 21): "Meet our newest event: **Rocket Race**! Beat levels before others to finish the race and advance to next stages for greater prizes!"
- 342, 311, 272, 260, 245, 222, 193, 179 and 165 (Aug 14 back to Jun 12): "Bug fixes and performance improvements".
- 148 (Jun 7), 131 (May 29), 118 (May 18) and 109 (May 2): bug fixes.
- 59 (Apr 26): launch.

Build numbers jump 45–100 per release, so internal builds are frequent. The timer arrived with v131 (review of May 29, §11).

---

## 2. Core rules

- **Board. VERIFIED.**
  - Orthogonal snake arrows on a hidden square grid; white background; black arrows on the phone and store screenshots.
  - Some builds use coloured arrows: blue in the Jul–Sep videos; multi-colour in the May–June Arrow Jam videos.
  - Arrow colour is an A/B or theme variable. The phone (black) is authoritative.
- **Tap. VERIFIED.**
  - A tapped arrow leaves along its own path.
  - It leaves a **rainbow trail** (store screenshot 1; `yt_frames/dazecheck_L122_rainbow-trail-hq.jpg`).
  - Its vacated cells become faint dots.
  - If its head's ray is blocked, it bumps and a heart is lost (heart loss visible in `yt_frames/gamemobie_L32_hearts-lost.jpg`).
  - The exact bump rule is for the phone team to measure.
- **Store description. VERIFIED.** "Tap the arrows in the right order and extract each arrow from a crowded board before time runs out. You have
  plenty of moves – but limited time." Quick guide: "Find arrows with a clear path and tap to release them / Free one arrow to unlock the path for the others / Plan your moves to clear the board — before time runs out."
- **Timer + hearts history. INFERRED; A/B across cohorts.**
  - **Launch week (v59–v109).**
    - Some players had a timer: Apr 29 and May 3–12 videos show 2:00 (1:30 in launch marketing footage) and no hearts in the HUD; an "Out of Time!" screen exists.
    - Other players had "3 hearts" and no timer (reviews of May 29 and Jun 30: "When the game used to be 3 hearts…").
  - **v131 (May 29).** The timer arrived for more players, and hearts were gone for them: "no penalty for failed moves" (Jun 22); "Now that it's a timer I can just randomly click" (Jun 30).
  - **Jun 6 video.** Timer 3:00, no hearts.
  - **Jul 30, Aug 13, Aug 17 and Sep 10 videos.** Timer **and** 3 hearts. VERIFIED from frames.
  - **Phone, v552.** Timer + 3 hearts.
- **Timer values. VERIFIED per frame.** The timer is a per-level parameter:
  - May: normal 2:00; Hard L25 2:00.
  - June: 3:00.
  - Jul 30: normal, Hard (L19, L25, L35) and Super Hard (L29) all 3:00.
  - Aug 13: one Super Hard at **2:00** (5 s frames count down cleanly from 2:00, `yt_frames/zoom_superhard-timer-2-00_gamemobie-aug13.jpg`).
  - Aug 17: L1–20 all 3:00.
  - Phone: normal 3:00, Hard L34 3:30.
  - Store screenshots show 2:00, 1:45, 1:30 and 0:45 (Hard) as marketing values.
- **Level intro. VERIFIED (Jul/Aug).**
  - The board builds in while the HUD pill is greyed and the hearts are pale.
  - Then the pill shows an **enlarged "3:00"** (`yt_frames/gamemobie_L26_intro-big-timer-3-00.jpg`) and shrinks back.
  - The phone found that the timer starts at the first tap (levels.md).
- **Level label. VERIFIED.** The "Level N" tab sits above the timer pill. May/June builds printed "Levels 1-4" or "Level N" under the HUD instead.
- **Fail flows.**
  - **Hearts out. VERIFIED, Jul 30.** "Continue? Get 3 lives to keep playing!", three hearts, "Play On [coin] 900", X (`yt_frames/gamemobie_L4x-L50_continue-weeklycontest_sequence.jpg`).
  - **Time out. VERIFIED, Apr 29.** "Out of Time!", stopwatch, "+30 sec", "Continue [coin] 900". X leads to "Level 9 / [broken heart] You failed the level / Try Again".
  - The phone's v552 chain adds "You will lose your streak!" and "You will lose a life!" steps (flows.md).
  - Review (Aug 31, L84): "Spend money and only get 30 more seconds". Review (Sep 19): "the timer is too short for the hard levels and there is no way to move on unless you pay for coins".
- **Pause. VERIFIED.** "Paused" panel with Sound and Haptic toggles, green Resume, red Quit, X (Apr 29 and phone).
- **Win sequence.**
  - **Jul/Aug/Sep builds. VERIFIED.**
    1. The last arrow leaves.
    2. The **MAZE OUT! logo pops** on the board. On white first (`usman_L15_win-logo-on-white.jpg`), then the screen goes dark with confetti and firework streaks (`usman_L16_win-confetti.jpg`, `dazecheck_L122_win-splash-hq.jpg`).
    3. The panel shows: yellow tab "Level N", "Perfect!", "Rewards:", coin stack, "Continue", red X, and a Streak Race banner along the bottom.
  - **May–June and Jul 30 builds.** A "Well Done!" word with confetti instead of the logo.
  - **Panel colour by difficulty.** Blue for normal, **red** with a "Hard Level" ribbon for Hard, **purple** for Super Hard (`yt_frames/gamemobie_L78-81_win-panels_superhard-100_streak-multiplier.jpg`).
- **Hint of "hidden blocks". INFERRED.** A review (Jul 17) says the trick to super hard levels is "scan into the puzzle so that you can see hidden blocks". This most likely refers to arrows under doors, curtains and elevators, and possibly to zoom.
- **Zoom / fit. VERIFIED (reviews).**
  - "board doesn't fit on the screen and you have to scroll to see arrows at the edges or being hidden by the on screen icons" (Sep 19; also May 6, Jul 18).
  - "2 bars are blocking the game" (Aug 2) refers to the HUD bar and the booster bar.

---

## 3. Obstacles: names, rules, first level per build

The game's own names come from the unlock popups: a dark full screen with "<Name>!", "Unlocked!", an icon, and a caption card. The captions below were read at 8× zoom (`yt_frames/zoom_unlock-captions_corner-linked-curtain-elevator.jpg`).

| Obstacle | Unlock caption (EN) | Look | Rule | First level seen, per build |
|---|---|---|---|---|
| **Linked Arrows** (pink tape) | "Linked Arrows! Unlocked! — **LINKED ARROWS move together!**" (VERIFIED) | 2, 3 or 4 parallel straight arrows bound by a pink band with a pink X. In May the bands were red/pink across coloured arrows. | One tap moves the whole bundle (the phone confirmed this on L32). | May: popup after L5, first on **L6** (pairs), then L8 triples, L10 quads (VERIFIED `primegaming_L06_linked-unlock`). June: popup at about L10. Aug 17: **L7** (4 pairs, dimmed tutorial board), L8, L10, L13, L17. Jul 30: L17, L23, L24, L28, L34. Phone: L32 (4 quads). |
| **Corner** (bumper) | "Corner! Unlocked! — **Arrows turn when they hit the CORNER!**" (INFERRED reading of a 83-px caption; the word CORNER is certain) | Teal/cyan 45° wedge in a cell (red-pink in the Jul L41 frames). | The flight turns 90° off the wedge. Review (Sep 11): "bouncing the arrows off corner bumpers, once twice, even three times to change direction!" | May: popup after L9 (Hard), first on **L10**; L12 and L25 full of corners (VERIFIED). Jul 30: at L41+ (`gamemobie_L41_corners`). Aug 13: L7x–8x. Store: "Discover linked arrows, corners, pipes and much more". **Not seen in Jul/Aug L1–38.** |
| **Curtain** (counter gate) | "Curtain! Unlocked! — **Clear required amount of arrows to open the CURTAIN!**" (VERIFIED) | Skins changed by build. June: two purple stage-curtain drapes with a rope and a numbered tag (20, 6) covering a region (`iostouchplay_L1x_curtain-drapes-hq`). Launch footage: drape with a padlock tag "3". Jul 30: **cyan** box with a gear-like counter. Aug 17: **purple crate** (orange frame) with a counter badge; the popup icon is a purple crate with a purple hexagon lock. Aug 13 and Sep 10: tall **purple side panels** with counters (5/23, then 6/24 one arrow earlier) framing a shaded region. | The counter drops by 1 per arrow cleared anywhere (Sep 10 frames: 6→5 and 24→23 after one exit). At 0 it opens and reveals or frees the arrows it covered or blocked. The box blocks rays. | June: popup after about L11. Aug 17: popup after the L10 win, first on **L11** (counters 5 and 18), then L12, L13, L15, L19H (VERIFIED `usman_L11_*`). Jul 30: L11, L13, L19H, L25H, L27, L28, L33, L37. |
| **Door + Key** (v552 name TBD) | UNKNOWN (the phone saw no popup; doors were first met on L33) | Blue slatted shutter, orange frame, purple hexagon lock. Store screenshot 3 shows 4 corner crates with hex locks and 4 **key arrows** (gold key on a purple ring). Aug 13 video: a large blue **rolling shutter** covering the bottom half (`gamemobie_L76-85_no-booster-bar_shutter_curtaingates.jpg`). Launch footage (Apr 29): arrows with small **keys** next to curtains with "3" padlock tags. | Phone (L33): a key arrow exits, the key flies to the next door, and the door shatters. The launch footage suggests keys were the original curtain opener. INFERRED lineage: key-locked curtain (Apr), then counter curtain (Jun–Sep), then key door (v552). | Phone: L33, L34 (Hard). Videos: Apr 29 (keys), Aug 13 (shutter). |
| **Elevator** | "Elevator! Unlocked! — **Clear all arrows on the ELEVATOR to activate it!**" (VERIFIED) | Translucent blue-grey rectangle (a raised platform) holding a layer of arrows. Other arrows lie beneath it. | Clear every arrow on the platform and it activates. Then it lowers or disappears, and the arrows underneath become playable (May L26: blue platform arrows, then green arrows appear where the platform was, `primegaming_L26_elevator-hq` and `_elevator-lowered-hq`). The shaded rectangles in the Jul/Aug/Sep boards are elevators. | May: popup at **L26** (VERIFIED short `2dwCfk7OJKw`). June: L26–27. Jul 30: L31, L32, L33, L35H, L39SH. Sep 10: L122. |
| **Pipe** | UNKNOWN in videos (no popup captured at 10 s sampling). Phone: "pipe unlocked" popup at **L35** in v552 (shots/040). | Cyan/blue tube laid along cells, L- or U-shaped, with end caps. Store screenshot 4: pipes around the border with numbered caps "2". | INFERRED: an arrow entering a pipe end travels through it and comes out the other end. The cap number is the number of uses left; the pipe **shatters** when used up (Jul 30 L23 frame shows cyan shards, `gamemobie_L23_pipe-shatter`). The phone team must verify. | Jul 30: **L21** (single L pipe), L22, L23 (two pipes), L25H, L29SH, L38. Phone: L35. |
| "Hard Level" / "Super Hard" tags | n/a | Hard: red back/pause buttons, red "Hard Level" ribbon over the timer, red Play button on home with a "Hard Level" ribbon, red win panel. Super Hard: the same in **purple**. | Rewards: 60 coins (Hard) and **100** (Super Hard). | See §5. |

Not found anywhere: bombs, ice, chains, colour-matching exits, moving pieces. The store's "and much more" is marketing. Several reviews say the store's example puzzles "don't exist" (Jul 17, Jul 21, Aug 31).

---

## 4. Levels 1–31, from videos (INFERRED unless marked; NOT the current v552 boards)

**Sources.**
- **L1–20** come from "Usman's Gaming", uploaded 2026-08-17 (`e45Uv_THi6A`; storyboard 83×180 px every 5 s; App Store version then about v342).
- **L21–31** come from "Game Mobie", uploaded 2026-07-30 (`Ax_FrOhKnlE`; 83×180 every 10 s; about v260). Its L11–20 match the Aug 17 boards.

**How to read the numbers.**
- Grid = rough bounding box in cells (cols × rows, ±2).
- Arrows = rough count (±25 %), read from 83-px frames.
- A 1,178-px-wide phone shot is needed for exact values.
- Composite start frames: `yt_frames/composite_L01-16_*`, `composite_L17-29_*`, `composite_L30-31_*`.
- Per-level frames: `yt_frames/usman_Lnn_*.jpg` and `gamemobie_Lnn_*.jpg`.

| L | Timer | Tag | Shape | Grid | Arrows | Obstacles | Tutorial / unlock / notes |
|---|---|---|---|---|---|---|---|
| 1–4 | 3:00 (Aug; the timer seems to reset per stage); 2:00 shared (May) | – | 4 mini-boards in ONE session labelled **"Levels 1-4"** (VERIFIED May/June; label length matches in Aug) | tiny, then about 6×8 | stage 1: 1–3; stage 3: about 4; stage 4: about 10–12 (nested ⊐ shapes) | – | May stage 1: "**Tap to move!**" text plus a hand on the free arrow among 3 parallel vertical arrows (VERIFIED `gamerfox_L01-04_tap-to-move-hand`). June win panel "Level 1-4 / Perfect! / Rewards 80" (VERIFIED). Aug: MAZE OUT! win splash. |
| 5 | 3:00 | – | rectangle | 10×12 | about 24 | – | "Level 5" label. VERIFIED: 3:00, 3 hearts. |
| 6 | 3:00 | – | **heart** silhouette | 14×12 | about 40 | – | Board-build intro frame `usman_L06_board-build-intro` |
| 7 | 3:00 | – | rectangle | 9×12 | about 15 + 4 linked pairs | Linked ×4 (pairs) | **Linked Arrows tutorial** (board dimmed) |
| 8 | 3:00 | – | rectangle | 12×15 | about 35 | Linked ×2 (a pair and a triple) | – |
| 9 | 3:00 | – | square-ish maze | 13×15 | about 42 | – | – |
| 10 | 3:00 | – | irregular | 14×14 | about 45 | Linked ×2 | Win "Level 10 Perfect! 20" (VERIFIED). Then "**Curtain! Unlocked!**" (VERIFIED) |
| 11 | 3:00 | – | small L-shape | 9×12 | about 12 | Curtain ×2 (counters 5, 18) | Curtain tutorial level |
| 12 | 3:00 | – | irregular | 11×14 | about 30 | Curtain ×3 (≈4/12/16) | – |
| 13 | 3:00 | – | rectangle | 12×15 | about 35 | Curtain ×2 (2, 26) + Linked ×2 | Win "Level 13 Perfect!" (VERIFIED) |
| 14 | 3:00 | – | irregular blob | 12×12 | about 25 | – | Win "Level 14 Perfect! 20" (VERIFIED); home coins 1240 (hq thumb) |
| 15 | 3:00 | – | rectangle | 12×15 | about 40 | Curtain ×2 (small) | – |
| 16 | 3:00 | – | spiral rectangle | 11×14 | about 25 | – | – |
| 17 | 3:00 | – | rectangle | 12×16 | about 45 | Linked ×3 | – |
| 18 | 3:00 | – | rectangle | 12×12 | about 20 | – | – |
| 19 | 3:00 (VERIFIED zoom) | **Hard** | tall rectangle | 16×24 | about 80 | Curtain ×3 (corners) | First Hard. Red Play on home; red HUD; win "Hard Level / Level 19 / Perfect! / 60" (VERIFIED) |
| 20 | 3:00 | – | rectangle | 13×16 | about 40 | – | Win "Level 20 Perfect! 20" (VERIFIED) |
| 21 | 3:00 | – | rectangle | 12×15 | about 30 | **Pipe ×1** (L-shape) | First pipe (unlock popup not captured; the phone says v552 unlocks pipes at L35) |
| 22 | 3:00 | – | two-part board | 13×16 | about 35 | Pipe ×1 | – |
| 23 | 3:00 | – | rectangle | 13×16 | about 40 | Pipe ×2 + Linked ×2 | Pipe shatter frame |
| 24 | 3:00 | – | irregular | 13×16 | about 40 | Linked ×3 | – |
| 25 | 3:00 (VERIFIED zoom) | **Hard** | tall rectangle | 15×24 | about 75 | Curtain ×3 + Pipe ×2 | – |
| 26 | 3:00 (big-timer intro frame) | – | small cross | 10×12 | about 20 | – | – |
| 27 | 3:00 | – | rectangle | 13×17 | about 45 | Curtain ×3 | – |
| 28 | 3:00 | – | rectangle | 13×17 | about 40 | Curtain ×2 + Linked ×3 | – |
| 29 | 3:00 (VERIFIED: 2:52 → 0:21 in 10 s steps) | **Super Hard** | tall rectangle | 16×24 | about 90 | Pipe ×3 | Purple HUD; cleared with about 0:20 left |
| 30 | 3:00 | – | small | 10×12 | about 20 | – | – |
| 31 | 3:00 | – | small wide | 10×8 | about 15 | **Elevator ×2** (shaded) | – |

Beyond the table, from the same builds: L32 elevator (about 35 arrows; lost 2 hearts); L33 4 curtains + elevators; L34 4 linked quads; L35
Hard (elevator strip); L36; L37 2 curtains; L38 U-pipes; L39 Super Hard (elevators + linked); L41+ corners; the "Weekly
Contest" popup on reaching L50. The Aug 13 video covers L76–85 (Super Hard L79, 2:00, 100 coins; purple curtain side-gates; rolling shutter). The Sep 10 video covers L122–123
(curtain gates + elevator; octagon board with linked pairs).

**Phone v552 check.** The phone's L32 (20×20, 53 arrows, 4 tape quads, 3:00), L33 (doors + keys) and L34 (Hard 3:30, 25×35) match none of these. The unlock order also moved: tapes appeared by L32, doors and keys at L33, pipes at L35. So **L1–31 of v552 are UNKNOWN** until a reinstall.

---

## 5. Difficulty curve

- **Hard positions.**
  - Aug/Jul builds: **19 H, 25 H, 29 SH, 35 H, 39 SH**, then roughly every 4–6 levels.
  - May build: 9 H, 25 H (both 60 coins).
  - Phone v552: 34 H.
- **Hard levels are big and slow.** Hard and Super Hard levels are the biggest boards (about 16×24 and 75–90 arrows in Jul/Aug; phone L34: 25×35, 76 visible arrows). They use 3:00–3:30 (one Super Hard used 2:00). Normal levels vary from about 15 to 45 arrows, so difficulty goes up and down rather than rising steadily.
- **Levels repeat. VERIFIED, reviews.** This is the most common complaint.
  - How soon and how many: "Levels repeat after 30 levels" (Jun 22). "repeats the same 30 levels over and over" (Aug 29). "Great for the first 100 levels" (Jul 4). "Fun for the first 150 or so" (Jul 21). "I've done the same map since level 100" (Jul 26, L309). "same 4-5 levels over and over since 150" (Aug 24, L370). "same hard and super hard puzzles on repeat… literally the same 5-6 puzzles" (Sep 1).
  - One report of a stop: "it seems to stop at level 100" (Jul 17).
  - **INFERRED:** a hand-made block of about 100–150 levels, then a cycle drawn from a small pool (by difficulty tier). Our V1 goal of "recorded + generated to 100+" matches what players actually get.
- **Perceived difficulty.** "too easy… all within 30 seconds" (Jul 15). "after the most recent update, the hard levels are pretty much impossible" (Aug 6, v272). "On level 84. No way to win" (Aug 31). "Timer Too Short … hard levels" (Sep 19).

---

## 6. Boosters

- **Phone v552. VERIFIED on the phone.** Two boosters, each with count 3, in the bottom corners: left is an hourglass/crystal (freeze time?), right is a light bulb (hint). Effects are for the phone team.
- **Jul 30 and Aug 17 builds. VERIFIED.** A bar of **4** boosters, each with a red badge "3" (`yt_frames/zoom_booster-bar-jul-aug-4-boosters.jpg`). Left to right:
  1. a yellow arrow/cursor;
  2. an hourglass (ice-blue);
  3. a light bulb;
  4. a blue dome/bell.

  Names and effects are UNKNOWN.
- **Aug 13 (L76–85) and Sep 10 (L122) builds. VERIFIED.** No booster bar visible, which points to an A/B test.
- **Sources of boosters.** The shop bundles contain 2 booster icons (hourglass + bulb, VERIFIED Jul 30). The v552 Claw ladder gives "bulb ×1" at step 17 (phone).
- **Hints are wanted.** Review (Sep 17): "No option to have hints… Only an option to purchase extra seconds". Either that player had no bulb booster, or had used it up. INFERRED.

---

## 7. Economy

- **Coins per win. VERIFIED on win panels, all builds.**
  - Normal **20**, Hard **60**, Super Hard **100**.
  - "Levels 1-4" session: **80** (June).
  - The panel title is always "Perfect!" in every capture, including after heart losses? (UNKNOWN whether a non-perfect title exists).
- **Coin track (Aug 17). INFERRED.**
  - Home coins read 1120 (L8), 1140, 1160, 1200 (L12), 1240 (L14, hq), 1320 (L18): +20 per normal win.
  - That implies about **1,000 starting coins**, assuming 80 for L1–4 plus 20 each for L5 and L6.
  - The phone has 2240 at L32.
- **Continue prices. VERIFIED.**
  - "Play On 900" coins (hearts out) and "Add Time/Continue 900" for **+30 sec** (time out).
  - The v552 chain adds a streak-loss warning (phone). Magic Sort also uses 900-coin continues (Magic Sort reviews).
- **Lives.** 5, shown as "5 Full" on home (VERIFIED in all builds).
  - Refill period: the store screenshot home shows "4 [heart] 23:46", so it is at least 23:46 and probably 30:00 (INFERRED).
  - The phone showed "refill 11:20" after a loss. The phone team should measure it.
  - Losing a level costs a life in v552 (phone). **Unlimited lives** show as "∞ 27:40" (Sep 10 home) and "∞ 30m" (Claw reward).
- **IAPs. VERIFIED, US store "In-App Purchases" list (popularity order).**
  - Tiny Coin Package $1.99
  - Small Coin Package $7.99
  - Medium Coin Package $14.99
  - Mini Bundle $4.99
  - Special Offer $0.99
  - Epic Bundle $9.99
  - Big Coin Package $29.99
  - Elite Bundle $19.99
  - Super Coin Package $54.99
  - Giant Coin Package $99.99
- **Shop screen (Jul 30). VERIFIED** (`yt_frames/gamemobie_meta_shop.jpg`).
  - Header coin pill + "Shop".
  - "Special Offers" section: a card with a "90% OFF"(?) badge: 1,000 coins + 2 boosters + ∞-heart. Titled "Special Offer", **$0.99**.
  - "Bundles" section: "Mini Bundle" with 2,000 coins + 2 boosters + ∞-heart, **$4.99**. More bundles follow below.
  - Coin quantities of the other packs are UNKNOWN. Coin-package amounts need the phone (look only, never buy).
- **Piggy bank / daily rewards / chests.** Not seen in any source (UNKNOWN; likely absent).

---

## 8. Meta and events

- **Home (v552 look, VERIFIED on store screenshot 7 and Sep 10 hq thumb `dazecheck_hq-thumbs_sep10-build.jpg`).**
  - Top bar: avatar, coins with a green +, lives heart, settings gear.
  - Left column: event badges with timers. Sep 10 had a checkered flag "14h 26m" (Streak Race), a rocket with "1" and "14h 26m" (Rocket Race), and a pedestal with a red gem box, "Join" (probably Sky Jump; INFERRED).
  - Centre: the lab scene with the purple monster at a console, a capsule machine full of 3D arrows, and a "LEVEL N" plate.
  - Big green Play. It turns red with a "Hard Level" ribbon on Hard levels.
  - Bottom nav, 3 tabs: shop basket, Home, trophy.
- **Older navigation.** The July build had 5 tabs: shop, trophy, home, compass(?) and settings (`gamemobie_meta_*.jpg`). The June build had a vertical **level road** home with hexagon nodes (`iostouchplay_L09_home-level-road.jpg`).
- **Streak Race. VERIFIED** (store screenshot 6; Aug 13 video).
  - Popup: slide art with capsule workers, "Streak Race" logo, "Beat levels without fail to get more rewards!", chips **x1 x5 x10 x25 x100**, a timer, and a ranked list of 5 players. Each row: avatar, name, a coin prize (store: 3000 / 2000 / 1000) and a score.
  - Each first-try win moves the lit chip one step (x1 → x5 → x10 → x25 → x100); a fail resets it to x1 (phone).
  - It appears on every win panel and on the fail panel. Names seen: Kate, Max, James (store). In the Aug 13 frames the names are mostly illegible at 83 px; one reads "GOLDEN".
  - **INFERRED:** the score is levels × multiplier, and opponents are bots or asynchronous players.
- **Claw Challenge (v552). VERIFIED.**
  - Notes: "Beat levels without losing and increase your multiplier to win amazing rewards!"
  - The phone documented the screen and its 1–20 reward ladder (flows.md).
- **Rocket Race (v372+). VERIFIED** (Sep 10 frames `dazecheck_L123_rocket-race-popup.jpg`).
  - Notes: "Beat levels before others to finish the race and advance to next stages for greater prizes!"
  - Popup: "Rocket Race — Beat 5(?) levels before others to finish the race", 5 rocket lanes with a numbered badge each, and 5 avatars at the bottom (you + 4).
  - The win panel shows a 5-avatar race bar with a finish flag (`dazecheck_L122_win-panel-race-bar.jpg`).
- **Sky Jump (v443+). VERIFIED text only.** "Complete stages by beating levels in a row on your first try and advance to next stages for greater prizes!"
- **Weekly Contest / Leaderboard. VERIFIED.**
  - Trophy tab: "Leaderboard" with tabs Weekly / World / Country. Before the unlock level it shows "Reach level **28** (June) / **50** (July) to compete in Weekly Contest!".
  - On reaching L50 (July: after the L49 win, before L50 is played) a popup appears: "Weekly Contest — Beat Levels / Compete with others / Win Rewards! / There is a new contest every week! / Tap to Continue". The Weekly board then shows a podium of 3 plus a list.
  - Usernames look like real accounts: "player_9otloqs", "player_wbribfy" (June), "SneakySnakeGal", "Grib".
  - **INFERRED: online (server leaderboards; the privacy policy mentions global leaderboards and AWS).**
- **Profile. VERIFIED, Jul 30.**
  - "Enter Username — Create your username: [field] — Continue".
  - "Edit Profile": name field plus a 3×3 grid of avatar portraits (default blue silhouette, green monster, red, orange-cat, blue, orange, yellow, sunglasses, pink); Save.
  - "Profile" page: avatar, name, "Level 11" ribbon, and "General Stats" with "First Try Wins" and "Weekly Contest Wins".
- **Settings. VERIFIED, Jul 30.** Notifications ON/OFF; Sound, Music and Haptic round toggles; green "Support"; "Terms"; "Privacy".
- **Rating prompt. VERIFIED on the phone.** An iOS rating prompt appeared after L34 (phone).

---

## 9. Online vs offline

- **The store says "Offline Play … no wi-fi required".** Levels, lives and coins are local. INFERRED: the game works offline.
- **Online-dependent features. INFERRED.**
  - Weekly, World and Country leaderboards (real usernames; AWS per the policy).
  - Username and profile sync.
  - Streak Race, Rocket Race and Claw opponents: bots or asynchronous; UNKNOWN.
  - IAP.
  - Analytics and ad-attribution SDKs per the privacy label (tracking identifiers, coarse location). Ads: none seen in any video.
- **For our offline build.** Leaderboards become honest locked or offline states. Streak Race, Rocket Race and Sky Jump can run against local simulated rivals only if they are clearly labelled; that is a product decision for the SPEC.

---

## 10. FTUE / tutorials

1. **First launch. VERIFIED.** Splash "grand" (white wordmark on crimson). Then the loading screen: Maze Out! logo art plus "Loading" (Arrow Jam sky art in older builds). Then the iOS notification prompt (phone). Then straight into the "Levels 1-4" session, with no home screen first. INFERRED: in the Aug video the first frame after loading is stage 1, but the upload may be trimmed.
2. **"Levels 1-4".** Stage 1: "Tap to move!" and a pointing hand on the one free arrow (May, VERIFIED). Later stages have no text. The session ends in one win panel ("Level 1-4 … 80", June).
3. **Popups.** Each obstacle gets a full-screen unlock popup before its first level (captions in §3). The first level of an obstacle can show a dimmed board (Aug L7 linked tutorial frame), probably a spotlight on the obstacle with a hand (INFERRED).
4. **Level labels.** Hard and Super Hard need no popup; the home Play button and HUD change colour.
5. **Profile.** The username prompt appears when opening Profile or Leaderboard (Jul 30 frames 5–6), not forced.
6. **Unlock levels per build.**
   - May: Linked L6, Corner L10, Elevator L26, leaderboard L28.
   - June: Linked about L10, Curtain about L12, Elevator L26, leaderboard L28.
   - Aug: Linked L7, Curtain L11, Hard L19, Pipe L21 (Jul), Elevator L31 (Jul), Corner about L41 (Jul), Weekly Contest on reaching L50 (Jul).
   - v552 (phone): Tape by L32, Door+Key L33, Pipe L35.

---

## 11. Reviews digest

**Sample.** 61 unique reviews; raw data in `research/web/reviews/`.
- Countries: US 15 (RSS) + 10 web, GB 6, CA 16, AU 15, TR 5, DE 3, BR 1.
- Stars: 1★ 18, 2★ 14, 3★ 11, 4★ 5, 5★ 13.
- Versions: 109 to 507.
- **Limit hit:** Apple's RSS returns at most about 15 reviews per country and page 2 is always empty (retried 6× per page). The App Store web "see all" page returns 10. No token was available for the amp-api.

**Themes, most frequent first:**
1. **Repeating levels.** About 22 reviews. "30-level cycle", "same 4-5 levels since 150", "same map since level 100".
2. **Timer and hearts design.**
   - Some reviewers hated the timer (May 29 "Why the Timer?"; DE Sep 15 "Ohne Timer … perfekt").
   - Some said the time is too long or that there is no penalty (Jun 22, Jun 30).
   - Some said the timer is too short on hard levels (Sep 19).
   - Launch-week TR complaints: you can pass by spamming taps, "add a move limit" (May 11, Jun 7).
3. **Too easy, then too hard after v272** (Aug 6, Aug 31 at L84).
4. **Board doesn't fit the screen / HUD bars cover arrows** (May 6, Jul 18, Aug 2, Sep 19).
5. **No sound.**
   - "pretty weird playing in complete silence" (Sep 11); "Yes I have sound enabled… but nothing!" (Aug 16).
   - **INFERRED:** in-level sound is minimal or absent for some cohorts. The phone and motion analyst should verify; the Settings screen does have Sound and Music toggles.
6. **Misleading store puzzles** (colour and shape puzzles "don't exist").
7. **Monetisation.** "only get 30 more seconds", "no hints … only extra seconds", "purposely built to make you fail".
8. **Positives.** Ad-free ("no ads, fun"; "Keine Werbung"), addictive, "Clever assignments… Nice colours and effects" (Jul 26), corner bumpers are fun.
9. **Visual A/B clue.** "I'm at level 350 and I've seen nothing but white backgrounds and black arrows. Where is the colour" (May 28). So the black-arrow skin existed in May, while videos from the same month show coloured arrows.

---

## 12. Open questions (UNKNOWN; for the phone or later)

- v552 levels 1–31 (reinstall) and the v552 unlock levels of Linked/Tape, Corner, Curtain and Elevator.
- Pipe rule details: the entry side, the cap count, and what happens when an arrow's head enters a pipe versus a body segment.
- Whether Corner and Curtain still exist in v552.
- The 2 v552 boosters' names, effects and prices, and the names and effects of the 4 Jul/Aug boosters.
- Coin-pack sizes in the shop.
- Lives refill period (probably 30:00).
- Starting coins (≈1000).
- Whether "Perfect!" changes after a heart loss.
- Leaderboard: real or bot.
- Sky Jump screen.
- The in-level sound set.

---

## 13. Sources

**Store and company**
- iTunes lookup us/tr: `https://itunes.apple.com/lookup?id=6762192889&country=us`, saved as `research/store/lookup-*.json`.
- App Store page: https://apps.apple.com/us/app/maze-out-tap-puzzle/id6762192889, saved as `web/store/appstore-us.html` and `appstore-us-data.json`, and the reviews page as `appstore-us-reviews.html`.
- Reviews RSS: `https://itunes.apple.com/{cc}/rss/customerreviews/page=N/id=6762192889/sortby={mostrecent|mosthelpful}/json`, 37 countries, saved as `web/reviews/*.json`.
- Grand Games: https://grand.gs/, https://grand.gs/games/, and https://grand.gs/privacy.html (saved as `web/site/`).
- Google Play developer page: https://play.google.com/store/apps/dev?id=6430038787206489041.
- Naavik on Grand Games: https://naavik.co/digest/why-peak-games-investors-backed-grand-games/.

**YouTube (storyboards + thumbnails; video download not used)**

| Video | Uploader, date | Coverage |
|---|---|---|
| https://www.youtube.com/watch?v=e45Uv_THi6A | Usman's Gaming, 2026-08-17 | "Levels 1-20" |
| https://www.youtube.com/watch?v=Ax_FrOhKnlE | Game Mobie, 2026-07-30 | "Level 11-38", plus shop, leaderboard, settings and profile |
| https://www.youtube.com/watch?v=_IJ_3oAgVBY | Game Mobie, 2026-07-30 | "Level 39-50", continue offer, Weekly Contest |
| https://www.youtube.com/watch?v=JHJRxIHTuo4 | Game Mobie, 2026-08-13 | "76-85", Streak Race, Super Hard 100 |
| https://www.youtube.com/watch?v=A_h9Vv6EaM4 | dazecheck games, 2026-09-10 | Short, L122–123, Rocket Race; hq oar thumbs |
| https://www.youtube.com/watch?v=6tObwJPw-JA | IOSTouchplayHD, 2026-06-02 | Arrow Jam era; FTUE; Linked, Curtain and Elevator unlocks |
| https://www.youtube.com/watch?v=NoX3FIf4hMs | Drawing Tutorial With Nei, 2026-06-06 | Arrow Jam; "Level 1-4 … 80"; curtain |
| https://www.youtube.com/watch?v=23yqNmkXmTU | PrimeGaming, 2026-05-03 | Arrow Jam L1–20; Linked L6; Corner L10 |
| https://www.youtube.com/watch?v=x05VvsPkMAA | Carlos Pereira, 2026-04-29 | Launch week; Out of Time; Paused; failed |
| https://www.youtube.com/watch?v=1abRDenGSJg | Nextbiggames, 2026-04-29 | Launch coverage; keys + curtains + corners |

Level shorts from May 2026, with hq oar thumbs:
- Gamer Fox: `gQNHcqMsrlY` (L1–4), `7ckoAj3E3T8` (L5), `7onQ1lsM9tA` (L6), `hxZhMz5xOks` (L8), `dyoO_NJa-1I` (L10), `YEhosmnsU5w` (L12).
- PrimeGaming: `CS8FHs3c7NQ` (L21), `EDrfadCG_b4` (L22), `vLFDrZQeszU` (L23), `NURsYOPJupE` (L24), `6zmECXOtHH0` (L25 Hard), `2dwCfk7OJKw` (L26 Elevator), `qG-3vGV2e_4` (L27).

**Method.**
- Frames: the storyboard spec from `ytInitialPlayerResponse` gives the L3 sprite sheets (83×180 px per frame; 1–10 s apart).
- `i.ytimg.com/vi/<id>/{maxres1-3,oar1-3,oardefault}.jpg`: the oar* files of Shorts are full-resolution portrait frames.
- OCR: a Vision CLI (scratch `ocr.swift`) run over 5×-upscaled frames.
- Every level number, reward, caption and timer marked VERIFIED was read from a readable panel or zoomed frame. It is saved in `research/web/yt_frames/`, where each file name carries the uploader and the level.
