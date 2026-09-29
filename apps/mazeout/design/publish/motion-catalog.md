# Arrow Out — MOTION + HAPTICS CATALOG (publish phase P1, owner items 2, 3, 7, 8)

Written 2026-09-28 by the P1 motion/haptics agent. Desk only: no phone, no simulator, no xcodebuild, no heavy rendering (a
performance agent was timing on this Mac). Every number was measured for this document on existing recordings with
`research/motion-tools` (`mf.raw` = real presentation timestamps; small widths, short windows) unless the row cites an earlier
measurement. Nothing in App/**, Packages/**, Tests/** or UITests/** was edited.

Re-check any number: `~/.venvs/mf3d/bin/python design/publish/tools/motion_catalog_measure.py [pause|slide|v2slide|shopcards|badges|claim|unlock]`.
Evidence sheets (frames with their clip times): `design/publish/motion-evidence/*.jpg` (listed in §10).

## 0. Headline

1. **Item 2 is right, and the old research was wrong.** Tab changes in Maze Out SLIDE. The v552 clip `S1-weekly-contest-open` (50 Hz)
   begins in the middle of a Home → Leaderboard tab change. The page is 90 pt from rest and eases in over 0.23 s, under a bottom
   nav that does not move. The owner's older-build video V2 shows the whole move (the same curve to ±2 pt on the part both clips
   show). Both pages move together as one strip ("push"), **0.50 s**, `p(u) = 1 − (1 − u)^2.56` ≈ cubic-bezier
   **(0.372, 0.952, 0.716, 1.0)**. The raised tab jumps to the new tab in the first frame. SPEC-ui §1.8 and SPEC-motion-audio §7
   called tabs a "hard cut". That was INFERRED from 1-fps screenshots, so it is replaced here. Ours: an opacity flip
   (`HomeView.swift` + `ui.json transition.homeTabs 0`).
2. **Item 8 is right for the pause menu.** Re-measured at 60 Hz, the v552 **Paused** panel is not "instant". The dim is complete in
   one frame. The panel "punches": first frame 1.022×, down to 0.967× at +0.05 s, back to 1.000× at +0.133 s, scaling about its
   centre. The V2 **Quit Level?** and V2 **Paused** panels follow the same curve within 0.005. Closing is one frame. Our PopupHost
   shows every popup in one frame, which matched the earlier (wrong, 10-fps) reading.
3. **"The close menu comes from top"** has no recording on v552. On v552, Quit Level? and Continue? are full-width BAND popups
   (stills meta-092, 014, 113), not boxed panels. How the band enters is unknown: the only clip of Quit Level? is V2, where it
   punches like Pause. **Phone recording R1 (P0).** Another reading of the owner's words: the in-level top bar holding the ◀ close
   button drops in from above at every level start (easeOutBack, VERIFIED v552). Ours already does that drop.
4. **Item 8 is right for "rockets moving".** The previous idle-home analysis measured the characters, the capsule machine and Play,
   but never looked at the left **event badges**. They animate on the idle v552 home:
   - the Streak Race flags wave (continuously for 8.1 s of the 15 s clip);
   - the **Rocket Race rocket lifts off** 9 pt with smoke and a flame (8.47 → 10.33 s);
   - the Sky Jump drum hops about 5 pt (four times in 15 s).

   Ours: static badge renders (`EventBadges.swift`).
5. **Item 3.** None of the v552 win clips we hold has a tap during the celebration:
   - S1-L50-win-seq-1 and S3-L089-win both run unskipped, and the panel lands at W + 4.034 in both;
   - the bot never taps between the last arrow and the panel.

   So "not skippable on v552" is **OWNER-DIRECTED** (item 3, ruling 37c), not VERIFIED by us. The older V1 build did skip on a tap
   (13 of 17 panels came about 2 s early, INFERRED from timing). Ours skips from W + 0.41 (`CelebrationSkip`, S2Hooks.swift:430).
   Remove it. Recording **R3 (P0)** can confirm it on v552.
6. **Other gaps found while cataloguing.** All are measured on v552 at 60 Hz:
   - Unlock-card dismiss: the card's content vanishes in 1 frame, then the dim fades linearly over **0.233 s**. Ours fades the whole
     overlay in 0.16 s.
   - Claim screens are STAGED. Examples from the Sky Jump claim: the "Congratulations!" letters pop in left to right over 0.43 s;
     the coin counter counts **linearly** for 1.0 s starting at +1.38 s. Ours shows everything at once, with a 1.0 s easeOutQuad
     count starting at 0.
7. **Item 7 (haptics).** Vibration cannot be recorded, so every haptic row is OWNER-DIRECTED or a DECISION. Two things change:
   - the win logo gets beats: 5 letter clicks, the OUT! slam, the bounce and the firework pops;
   - buttons go from `.light 0.50`, which the owner does not feel, to `.rigid 0.60`, the same family as the arrow-tap click.

   The map is in §5. The owner can check the original by feel with the checklist in §5.4.

## 1. Sources and tags

| id | what | rate | build |
|---|---|---|---|
| v552 | phone recordings `research/video/S*.mov`, `META-*.mov`, `F00/F01` (iPhone 15, 393 × 852 pt) + lossless shots `research/shots/*` | 37–60 Hz, real timestamps | **the build we copy** |
| V2 | owner video `research/video/owner/V2-levels-11-38.mp4` | 59.64 fps | older build (5-tab home, "Well Done!" win); used for mechanics v552 does not show, never for looks |
| V1 | owner video `V1-levels-01-20.mp4` | 25 fps | older cousin of v552 (same win logo) |

Tags: **VERIFIED v552** (seen in a v552 clip or shot, numbers measured) · **VERIFIED V2** (seen in V2 only) · **INFERRED** (reasoned
from fewer or older observations) · **DECISION** (ours, no evidence either way) · **OWNER** (the owner's words; binding).
Times: `F` = the first frame the new state is on screen; `W` = the win wave start (LOGO-SPEC D1); `K` = the level cut; `S` = the popup's
first frame.

## 2. The owner's items → answers

| item | owner (verbatim, shortened) | what the evidence says | what we do |
|---|---|---|---|
| 2 | "The sub page changes are not smooth and they are instant … in mazeout, those have like sliding" | VERIFIED v552 (tail) + V2 (whole): tabs push-slide 0.50 s. Profile and the Settings page open and close in 1 frame (Settings VERIFIED v552 60 Hz; Profile VERIFIED V2). Event screens: no recording | Tab slide (§3.1, §6.1). Keep Settings and Profile cuts unless R4 shows otherwise |
| 3 | "the arrow out animation logo is not skippable by clicking in mazeout but in our game it is" | No v552 clip has a tap during the celebration (§4). Both v552 wins ran unskipped to W + 4.034 | OWNER: remove the tap-skip (§6.5). R3 confirms |
| 7 | "the logo animation screen should have that small vibrations we had while clicking on arrows … same when clicks play, pause etc." | Not recordable | Haptic map §5 |
| 8 | "the pause menu … gets a bigger … feels alive … rockets … are moving and animated, the close menu in the game comes from top" | Pause (and V2 Quit) punch VERIFIED. Rocket badge lift-off VERIFIED v552. "From top": no v552 recording (R1). The HUD drop from the top is VERIFIED and already built | §3.2, §3.5, §6.2, §6.3 |

## 3. The catalog — every animated UI moment

Columns: **v552 / evidence** (trigger · duration · property curves · easing · tag) · **ours** (file · behaviour today) · **gap → action**.

### 3.1 Pages, sub-pages, tabs

| moment | v552 / evidence | ours | gap → action |
|---|---|---|---|
| **Bottom tabs (Shop · Home · Leaderboard)** | Tab tap → both pages move as ONE strip, adjacent (V2 separation 394 pt ≈ 393). New page from the right when the target tab is to the right, from the left otherwise. Page offset `x = D · (1 − u)^2.56`, u = t / **0.50 s** (V2 fit RMS 1.26 pt; v552 tail 90 → 0 pt in 0.216 s matches it at RMS 1.1 pt). ≈ cubic-bezier (0.372, 0.952, 0.716, 1.0). The **bottom nav stays still**. The raised tab and its label jump to the new tab on the slide's first frame (V2 28.453). **Same duration for a 2-page jump**: start speed 2.0 pt/ms for 1 page, 3.6–4.0 pt/ms for 2 pages (V2 leaderboard → adventure, settings → home), so the page between the two passes through. VERIFIED v552 (tail) + VERIFIED V2 (whole curve, 4 slides); 2-page = INFERRED from V2 speeds | `HomeView.swift` shows the three pre-mounted pages by opacity (`transition.homeTabs 0`): a hard cut | **Build the push slide** (§6.1). Record R2 for the v552 start and a Shop ↔ Leaderboard jump |
| A popup queued behind a tab tap | v552: the forced Weekly Contest dim came on the frame after the slide settled (+0.017 s) | the tutorial presents at once | Present queued popups on the slide's completion (1 case, INFERRED) |
| Home → level (Play) | Hard cut 0.06–0.08 s after the release click; then the level intro | Router hard cut | none |
| Win-panel Continue → home; Level Failed X → home; Try Again | Hard cut | Router hard cut | none |
| Launch → Loading | Publisher splash → Loading cross-fade ≈ 0.10 s (F00 1.83 → 1.94) VERIFIED v552 | launch-screen colour, then Loading | new Loading art (item 1). Keep a 0.10–0.16 s cross-fade |
| Loading → home / first board | 0.13–0.16 s cross-fade (earlier research) | `transition.loadingToHome 0.16`, `loadingToBoard 0.13` | none |
| **Settings page (gear)** | Open and close: 1 frame each, no dim ramp. VERIFIED v552 60 Hz (S3-home-settings-open-close 1.747 / 4.260) | full page in the popup host, 1 frame | none (1:1). The owner may still want a slide here: a decision (§9 D2) |
| Profile (avatar) + X | 1-frame cut both ways. VERIFIED V2 (49.663, 54.525) | Router cut | none. Check on v552 in R4 |
| Edit Profile popup | 1 frame, **no punch**. VERIFIED V2 (56.352, close 68.743) | 1 frame | none |
| Username popup | 1 frame; then the iOS keyboard slides up (≈ 0.4 s, system) VERIFIED V2 | 1 frame | none |
| Leaderboard Weekly / World / Country | content swaps in 1 frame. VERIFIED V2 (30.582, 31.907) | instant swap | none |
| Event screens (Claw Challenge, Streak Race, Rocket Race, Sky Jump map) from the home bar or badges | **no recording** on any build (V2 has no events) | cut / full-screen popup, entrance pops per DECISION | R4. Keep until then |
| Closable Shop (a coin route, not the tab) | V2 71.174: the header and X appear in 1 frame on black. Each CARD ROW slides in from the right: spring response ≈ 0.40 s, damping ≈ 0.66 (from +393 pt; overshoot to **−23 pt** at +0.27 s; settled by +0.6 s). Rows stagger ≈ **0.045 s**. Close: 1 frame (72.163). VERIFIED V2; v552 unknown (its coin pill opens the Shop TAB) | S3's closable Shop: shown whole | Add the card stagger to the closable Shop (DECISION leaning to V2, since the owner wants life). The Shop TAB keeps its cards still (VERIFIED V2 18.5: cards move with the page) |

### 3.2 Popups and overlays (open / close)

| moment | v552 / evidence | ours | gap → action |
|---|---|---|---|
| **Paused** (❚❚) | Dim to full alpha (0.89) in 1 frame. The panel scales about its centre (≈ 200, 429.5 pt). Measured scale per 60 Hz frame from F: **1.022, 0.980, 0.969, 0.967, 0.969, 0.976, 0.986, 0.995, 1.000** (+0.133 s). Close (Resume / X): panel + dim gone in 1 frame. VERIFIED v552 (S3-L092 1.514–1.647, 4.193); VERIFIED V2 ×2 (83.414, 88.242) | `PopupHost` appends with animations off: 1 frame, no punch | **Add the punch** (§6.2): keyframes (0, 1.022) → (0.033, 0.969) easeOut → (0.067, 0.967) → (0.133, 1.000) easeInOut; dim unchanged; close unchanged |
| **Quit Level?** (◀ back, or Pause → Quit) | V2: the SAME punch (1.020, 0.983, 0.969, 0.966, 0.966, 0.972, 0.983, 0.994, 1.000); close 1 frame. On v552 it is a full-width band (still meta-092); its **entrance is unrecorded** ("comes from top", owner) | 1 frame | Give the band the punch now (INFERRED). R1 decides between punch and a drop from the top |
| Continue? ×2 (the fail-chain bands) | band popups (stills 014, 015, 113, 114); entrance unrecorded | 1 frame | Same as Quit Level? (one band family). R5 |
| Level Failed (boxed panel) | stills only (016, 115, meta-093) | 1 frame | Punch (INFERRED from Pause; same boxed panel family). R5 |
| **Out of Time!** | Appears COMPLETE in 1 frame, static afterwards (dim + stopwatch + button). VERIFIED v552 60 Hz (META-L062-timer-last-seconds 7.737; 9.5 s static in S1-L52) | 1 frame | none (keep instant: v552-verified) |
| Out of Lives! | stills only | 1 frame | Same as Out of Time (same layout family, INFERRED) |
| **Win panel** | Complete in 1 frame at W + 4.034. The Streak strip then slides up 0.13 s; the chip moves 0.31 s; the ring pops. VERIFIED v552 | `WinPanel` + `StreakBanner` per spec | none |
| Unlock card ("Elevator!", "Corner!") entrance | Dim in 1 frame at the cut K, then staggered pops (frame-difference bursts): icon K + 0.18 → 0.33 (peak change +0.25), title +0.38 → 0.55, "Unlocked!" +0.57 → 0.67, card +0.68 → 0.90, twinkles from ≈ +0.93. VERIFIED v552 60 Hz S3-L100-play-intro. That is ≈ 0.05–0.12 s EARLIER than the V1-based spec (icon 0.26, title 0.50, unlocked 0.62, card 0.78) | `UnlockOverlay` per `ui.json unlock.*` (V1 values) | Optional: move the beats to the v552 values (small; §6.7) |
| **Unlock card dismiss** (tap) | **The content (title, icon, "Unlocked!", card, sparkles) vanishes in ONE frame. Then the dim fades LINEARLY to 0 over 0.233 s** (S3-L100 1.148 → 1.381; S2-L070 1.398 → 1.631). VERIFIED v552 ×2 | the whole overlay fades 0.16 s (`unlock.dismissFade` 0.16, frozen `UnlockBeats` default) | **Change** (§6.7): content 1 frame + dim 0.233 s linear. Needs a contract amend (ShellContract `UnlockBeats`) + ShellS2Tests:87, TuningTests:87 expectations |
| Weekly Contest tutorial / info overlays | Dim in 1 frame (luminance 133 → 14), then staggered pops: title at +0.18 (grows ≈ 0.1 s), maze icon +0.35 (grows to +0.48), "Beat Levels!" +0.52, pointer ≈ +0.68–0.72, podium +0.88. VERIFIED v552 50 Hz (sheet `v552-tab-slide-home-to-leaderboard.jpg` frames 0.25–1.0) | `WeeklyViews`, `StreakRaceViews`, `ClawScreen` (i): `SocPopIn` staggers (0.18 / 0.35 / 0.58 / 0.72) | none (matches within a frame or two) |
| **Claim ("Congratulations! … Tap to Claim")**, measured on the Sky Jump stage win | From the tap (S = the first dim frame, 1 frame after the event screen):<br>• title letters pop in **left → right**, each growing (26 → 49 pt tall), right edge 43 → 376 pt by **S + 0.43** (≈ 27 ms per letter, 16 characters);<br>• the prize island scales in from S + 0.28, peaks 1.05× at +0.60, settles 1.00 at +0.68;<br>• "You win!" grows +0.88 → peak 1.04× at +1.18 → settles +1.28;<br>• coin plate pops ≈ +0.95; the player's portrait +1.20 → +1.36;<br>• **the counter counts LINEARLY 0 → 1428 from +1.38 to +2.38 s** (≈ 1430/s), then a gold glow burst on the plate at +2.44;<br>• "You are sharing the reward with 6 other winners!" +1.53 → +1.70;<br>• 5 winner portraits pop one by one from +1.61, ≈ 0.12–0.15 s apart, all in by +2.2;<br>• "Tap to Claim" ≈ +2.36.<br>VERIFIED v552 60 Hz (S3-skyjump3-win-claim) | `SocSkyWin`: everything shown at once; count-up 1.0 s easeOutQuad from 0. `ClaimRewardPopup`: static title, reward pop 0.30 s at S + 0.10 | **Stage both** (§6.6). Generic claims (∞ lives, coins, boosters): the letter-by-letter title is INFERRED to be shared (R8) |
| Event offer popups (Rocket Race, Sky Jump "Start", Streak Race list when it pops by itself) | stills only (065, 163, 203) | 1 frame | Punch (INFERRED). R4 |
| More Lives, booster info | stills only | 1 frame | Punch (INFERRED). R4 |
| Toasts | none seen on v552 | fade in 0.08 s / hold 2.0 s / out 0.27 s (DECISION) | none |

### 3.3 Buttons (press feedback)

| moment | v552 / evidence | ours | gap → action |
|---|---|---|---|
| Any button touch-down | Scale **0.95** in ONE frame, held while pressed. VERIFIED v552: Play (197.5 → 187.5 pt), Continue (284.5 → 270), **Resume (114 → 109 pt at S3-L092 4.143)**, the HUD ❚❚ (39 → 37 pt at 1.464) | `PressStyle` 0.95, instant, held | none |
| Release | Action on release; the next screen or popup appears 1–3 frames later (❚❚: popup at +0.05 s after the touch-down frame). UI click on release (sounds.md) | same (GameButton) | none |
| Toggle (Sound / Haptic / Notifications) | look swaps; knob motion unknown | swap on release; SPEC-ui DECISION knob 0.12 s ease-out | R6 |
| Popup X | not measured | 0.95 like every GameButton | R6 |
| Booster buttons | not measured | 0.95 | R6 (low priority) |

### 3.4 In-level (for completeness: all already built and specified; not re-measured here)

| moment | v552 | ours |
|---|---|---|
| Level intro | board zoom 1.49 → 1.0 easeOutCubic 1.35 s; arrows draw tail → head (0.32 s + 21.6 ms/cell); **HUD top row drops from 118 pt above, easeOutBack(3.42) 0.334 s at K + 1.015** (the ◀ close and ❚❚ buttons "come from top"); boosters slide in from the sides at K + 1.092; big timer pop at K + 1.339; hearts pop at K + 1.406 / 1.505 / 1.622 (SPEC-motion-audio §3.6, VERIFIED) | `HUDIntro.swift` + board intro (built; FEEL/V2 verified earlier) |
| Tap ripple, exit, colour ladder, stars, bump, heart break, red vignette, obstacles, boosters, timer | SPEC-motion-audio §3–§4 (VERIFIED) | built |
| Win celebration (wave, logo, dim, confetti, fireworks) | LOGO-SPEC (measured frame by frame on both v552 clips) | `WinLogoSequence.swift` (LOGO-IMPL done 22:05) — see §4 for the skip |

### 3.5 Home idle (the home scene will get new art, items 1 and 15: keep the timings, re-target the motion)

| moment | v552 / evidence | ours | gap → action |
|---|---|---|---|
| Scientist | continuous small breathe / blink / head tilt, **3.16 s** loop. VERIFIED v552 (META-home-idle-12s) | `PuppetStage` rig, cycle 3.16 s | re-rig for the new character (same cycle) |
| Right worker | writes / looks up / nods, **10.2 s** loop. VERIFIED | rig 10.2 s | re-rig |
| Left worker | walkie-talkie talk / think / wink / wave; no repeat inside 15 s. VERIFIED (period ≥ 15 s) | rig 17.3 s (DECISION) | re-rig |
| **Streak Race badge (flags)** | the chequered flags **wave continuously** (cloth ripple, period ≈ 1.25 s by autocorrelation) for 0.0–8.1 s of the clip, then still to 15.1 s. VERIFIED v552 (region motion 58 % of frames, max deviation 16/255) | static render | **Add** a flag wave to the new badge art (§6.4) |
| **Rocket Race badge ("rockets are moving")** | the rocket **lifts off**: smoke puffs and a flame under it, the nose rises **9 pt** (top y 301 → 292 at 8.84 s), holds, settles; one lift in the 15 s clip (8.47 → 10.33 s, smoke from ≈ 8.3 s). VERIFIED v552 (sheet `v552-home-badges-rocket-liftoff.jpg`) | static | **Add** a lift-off loop (§6.4). Period unknown (≥ 15 s): R7 |
| **Sky Jump badge** | the drum **hops ≈ 5 pt** with cloud puffs: 3.78–4.94, 6.71–7.47, 9.20–9.87, 14.54–15.14 s (every ≈ 2.5–5 s). VERIFIED v552 | static | **Add** a hop loop (§6.4) |
| Claw bar, coin pill, gear, avatar, level plate, Play, capsule machine, background pipes | **static** (mean frame difference < 0.2/255). The Play button does NOT pulse. VERIFIED v552 | static (the capsule pile refills on some arrivals: `HomeScene`, a DECISION, SPEC-ui §2.2.8) | none |
| Lives pill | text swap every second while refilling | `HomeTopBar` 1 Hz TimelineView | none |
| Badge timers | text swap | 20 s TimelineView | none |
| Tapping the scientist | no reaction. VERIFIED | none | none |

### 3.6 Counters and rewards

| moment | v552 / evidence | ours | gap → action |
|---|---|---|---|
| Home coin pill after a win | 5 coins fly from the machine to the pill ≈ 0.085 s apart, each landing adds N/5 (3854 → 3858 → … → 3874). VERIFIED v552 | `PayoutSequence` segment C | none |
| Claw bar count-up | 7 steps, 0.057 s each (+25: 156 → 181). VERIFIED | `ClawBar` | none |
| Claw token, multiplier merge, Streak chip tray, flag flight | SPEC-motion-audio §8.3 (VERIFIED) | `PayoutSequence` | none |
| Sky Jump coin plate | **linear** 1.0 s, starting at S + 1.38 (§3.2) | easeOutQuad 1.0 s from S | change the curve and start (§6.6) |
| "Finding players" counter 29 → 100 | stills only | 1.5 s easeOutQuad (DECISION) | none |
| Win panel "Rewards: 20" | static (coins fly on home) | static | none |
| In-level coin pill, booster badges, timer | 1-frame text swaps | same | none |

### 3.7 Lists

| moment | v552 / evidence | ours | gap → action |
|---|---|---|---|
| Leaderboard rows | move with the page during the tab slide; no row stagger. VERIFIED v552 (weekly-contest clip) | static rows | none |
| Claw Challenge ladder, first open | auto-scrolls from step 1 to step 20 (flows.md; timing not measured) | 1.8 s sineInOut (DECISION) | none |
| Closable Shop cards | stagger slide-in from the right with overshoot (V2, §3.1) | none | add (§6.1b) |
| Streak Race ranking, Rocket Race lanes, Sky Jump map hop | no recording | DECISION timings (SPEC-motion-audio §9) | R4, R9 |

## 4. Item 3 — is the v552 win logo skippable? (audit of every v552 win recording)

| recording | taps during W … panel? | panel at | verdict |
|---|---|---|---|
| `S1-L50-win-seq-1.mov` (L50; marks: ONE tap = the last arrow at action_start) | none after the last arrow | W + 4.034 (LOGO-REF §2, within one frame) | unskipped run; says nothing about a tap |
| `S3-L089-win.mov` (L89 Super Hard; `go3.py --win-clip`: `taps` of the last ≤ 5 arrows, 0.3 s apart) | none: the last tap is the last arrow | W + 4.034 | same |
| `S1-L50-win-seq-2-continue.mov` | starts on the panel | — | not about the logo |
| `S1-L52-short-exit-win.mov` | holds the Out of Time popup, not a win | — | — |
| ≈ 60 bot wins (research/bot `go.py` / `go3.py`) | the bot takes a shot, waits 2.3 s, shoots again and taps Continue only after `is_win` sees the panel | — | no tap in the window |

**Result:** we hold **no v552 evidence either way** about a skip tap. "Not skippable" is **OWNER-DIRECTED** (item 3, SPEC ruling
37c), and it is binding. For context, the older V1 build skipped: 13 of 17 panels came ≈ 2 s early (INFERRED from timing, motion.md §6.6).

**Ours today:** `CelebrationSkip` (App/Shell/HUD/S2Hooks.swift:430, placed by HUDView.swift:61) accepts a tap from W + 0.41
(`ui.json win.skipFrom`). The tap clears the logo and fireworks, jumps the dim, shows the panel, plays a click and fires the win
haptic. That is what the owner saw. The fix is in §6.5.

**Phone confirmation (R3, P0, optional given the owner's word):** on a win, tap the board area 4 times at ≈ +1.0 / +1.8 / +2.6 /
+3.4 s after the last arrow's tap, with a 60 Hz recording running. Unskippable = the panel still appears at W + 4.03 ± 1 frame. The
same clip shows whether a tap during the celebration draws a ripple or plays a click on v552.

## 5. HAPTIC MAP (item 7) — proposal

Vibration cannot be recorded. **Every row is OWNER-DIRECTED** (from item 7's words) **or a DECISION**. The owner's own reference is
the arrow tap ("that small vibrations we had while clicking on arrows"): `UIImpactFeedbackGenerator(.rigid)` at 0.70 on the release
frame, which the owner likes. The whole proposal is built from that click family.

### 5.1 The map

Legend: **keep** = today's `audio.json haptics` row. **change** = a data change only. **NEW** = a new beat; it needs a call site, and
a new `Haptic` case if it must be tuned on its own. Timing = the frame the haptic fires on: the first display-link tick with
t ≥ the beat, through the existing `HapticArbiter` (one per frame, flushed before the Core Animation commit).

| # | event | when (anchor) | generator · style | intensity | status | why |
|---|---|---|---|---|---|---|
| 1 | arrow tap accepted (exit) | the release frame, with the ripple and the first motion | `UIImpactFeedbackGenerator(.rigid)` | 0.70 | keep `tap` | the owner's reference click |
| 2 | bump that costs a heart | contact C | `UINotificationFeedbackGenerator(.error)` | — | keep `heartLost` | the pattern spans the heart break (0–0.40 s) |
| 3 | re-bump of a red arrow (no heart) | C | `.heavy` | 0.85 | keep `bumpContact` | |
| 4 | door burst / pipe shatter / box break | burst frame (the box: the tap frame) | `.medium` | 0.65 | keep `burst` | |
| 5 | key turns in the lock | tap + 1.531 (key-turn beat, motion.md §5.2) | `.rigid` | 0.45 | NEW (optional) `keyTurn` | a small "clack" before the burst at + 1.664 |
| 6 | booster used | bulb camera start / hourglass spawn (B) | `.medium` | 0.60 | keep `booster` | |
| 7 | hourglass lands on the stopwatch | B + 1.33 (icing) | `.rigid` | 0.50 | NEW (optional) | the freeze "locks" |
| 8 | stage / board clear | W | `.medium` | 0.80 | keep `clear` | also opens the logo sequence |
| 9 | Out of Time! / Out of Lives! | S | `.warning` | — | keep `fail` | |
| **10** | **logo letters** A · R · R · O · W land (the lagging chain, right → left like v552's MAZE) | **W + 0.815, 0.848, 0.881, 0.914, 0.947** (the letters' peak swings are W 0.815 · O 0.840 · R2 0.890 · R1 0.907 · A 0.915 per LOGO-SPEC §3, spread to ≥ 2 frames = 33 ms so none are merged by the one-per-frame rule) | `.rigid` | 0.55 → 0.70 (rising, last = strongest) | **NEW** `logoLetter` (phase 1: `tap` ×5) | "small vibrations like clicking on arrows" on the letters |
| **11** | OUT! turns solid (ghost → opaque, 2.2×) | W + 1.139 | `.light` | 0.45 | NEW (optional) `logoSwell` | announces the grow |
| **12** | **OUT! slam / impact** (OUT! back on its sign) | **W + 1.688** (`win.impactAt`, today's ◉ win beat) | `.heavy` | **1.00** | **change** `win`: `.success` → `.heavy` 1.0 | the owner's "impact". A heavy thud reads as a slam; the success triple-pulse reads as a notification |
| 13 | logo bounce (group rebound high) | W + 1.828 | `.rigid` | 0.40 | NEW `logoBounce` (phase 1: `tap`) | the "boing" after the slam |
| 14 | firework bursts | `win.bursts` = W + 2.365, 2.565, 2.765, 2.965, 3.195, 3.595 | `.soft` | 0.35 | NEW `firework` (phase 1: `coinLand` soft 0.45) | light pops under the flashes; soft keeps them below the slam |
| 15 | win panel appears | W + 4.034 | none | — | — | the next vibration is the Continue press |
| **16** | **every UI button release** (Play, ◀, ❚❚, Resume, Quit, X, tabs, gear, avatar, pills, badges, Claw bar, boosters, toggles, Start / Join, Try Again, Add Time / Play On / Refill, Save, Continue, "Tap to Continue" / "Tap to Claim", unlock dismiss) | release frame, with the click | **`.rigid`** | **0.60** | **change** `button`: `.light` 0.50 → `.rigid` 0.60 | the owner does not feel today's `.light` 0.50 ("same when clicks play, pause"). Rigid 0.60 is the arrow click, a notch softer |
| 17 | Play (the primary button) | release | `.rigid` | 0.75 | NEW (optional) `play` | the owner names Play: a slightly stronger click. Needs a per-button override in GameButton |
| 18 | Haptic toggle switched ON | release | the button haptic **after** enabling | 0.60 | code-order fix | today the tap plays while haptics may still be off |
| 19 | coin lands on the pill | each landing (5 × ≈ 0.085 s) | `.soft` | 0.45 | keep `coinLand` | |
| 20 | Claw token pops / multiplier merge burst / Streak flag lands | H + 0.03 / H + 0.68 / B0 + 0.74 | `.light` 0.40 / `.rigid` 0.50 / `.light` 0.40 | | NEW (optional) `rewardPop` | the home reward beats (no haptic today) |
| 21 | claim screen: island lands / counter done (glow) / winner portraits | S + 0.60 / S + 2.44 / each pop | `.rigid` 0.50 / `.medium` 0.60 / `.light` 0.30 | | NEW (optional) `rewardPop` | the claim "feels alive" |
| 22 | unlock card: icon lands / card lands | the icon's settle (`unlock.iconSettle`) / the card's settle (≈ K + 0.90 on v552) | `.light` | 0.40 | NEW (optional) | |
| — | tab slide, popup punch, HUD drop, level intro, tap ripple on empty board, zoom / pan, idle home | — | none | — | — | the button that caused it already vibrated; idle motion never vibrates |

### 5.2 Rules (additions to SPEC-motion-audio §12.2)
- Priority when two beats share a frame (extends today's list):
  `heartLost > fail > win(slam) > burst > bumpContact > clear > logoLetter > booster > rewardPop > coinLand > firework >
  logoBounce > tap > button`.
- Logo beats come from DATA: `ui.json win.haptics = [[0.815,"logoLetter",0.55],[0.848,"logoLetter",0.58],[0.881,"logoLetter",0.62],
  [0.914,"logoLetter",0.66],[0.947,"logoLetter",0.70],[1.139,"logoSwell"],[1.688,"win"],[1.828,"logoBounce"],[2.365,"firework"],
  [2.565,"firework"],[2.765,"firework"],[2.965,"firework"],[3.195,"firework"],[3.595,"firework"]]`. `WinLogoSequence.tick` fires each
  beat once, on the first tick at or after its time. This is the same mechanism as today's `impactAt` → `fireWinHaptic()`.
  A per-beat intensity needs `HapticPlaying.play(_:intensity:)` or distinct cases. Otherwise use one intensity per case.
- Beats stay at least 2 frames (33 ms) apart. The Taptic Engine blurs impacts closer than about 25–30 ms into one buzz (INFERRED;
  tune by feel).
- Everything stays gated by the Haptic toggle (Pause + Settings) and by the iOS System Haptics switch.
- **Contract:** `enum Haptic` lives in the frozen ◆ `App/Contracts/AudioContract.swift`. Adding cases goes through the orchestrator
  (additive; precedent: ruling 21). **Phase 1 needs no contract change:**
  - `button` → rigid 0.60 (data only);
  - `win` → heavy 1.0 (data only);
  - letters and bounce call the existing `.tap`;
  - fireworks call `.coinLand`.

  Phase 2 adds `logoLetter`, `logoBounce`, `firework`, `rewardPop` (and optionally `logoSwell`, `keyTurn`, `play`) so each can be
  tuned on its own.

### 5.3 Where the calls go (for the build phase; no code written here)
| beat | file |
|---|---|
| 10–14 | `App/FX/WinLogoSequence.swift` (next to `fireWinHaptic`, ≈ l. 888–912) + `ui.json win.haptics` |
| 12, 16 | `App/Resources/Tuning/audio.json haptics.win / haptics.button` |
| 17 | `App/Shell/Home/PlayButton.swift` → a `GameButton(haptic:)` override |
| 18 | `App/Shell/Popups/PausePopup.swift` `toggle(...)` + `SettingsPopup.swift` |
| 20 | `App/Shell/Home/PayoutSequence.swift` (A2, A5, B3) |
| 21 | `App/Shell/Social/SkyJumpViews.swift` `SocSkyWin`, `App/Shell/Popups/ClaimRewardPopup.swift` |
| 5, 7, 22 | `App/Game/GameController.swift` (key turn), `App/Game/BoosterDirector.swift` / `HUDFreeze.swift`, `App/Shell/Popups/UnlockOverlay.swift` |

### 5.4 Owner checklist — the ORIGINAL's haptics by feel (the only way to know them)
With Maze Out on the phone, Haptic ON: for each moment, does it vibrate, and is it light, medium or strong? Arrow tap · wrong tap
(bump) · heart lost · Play · ❚❚ · Resume · X · Sound/Haptic toggle · a bottom tab · a booster · the win: letters? the OUT! slam?
fireworks? the panel? · Continue · coins landing on home · "Tap to Claim" · the unlock card tap. The answers replace the DECISION
rows above, where they differ.

## 6. Implementation notes (for the phase-P build; values go to ui.json, never hard-coded)

### 6.1 Tab push-slide (item 2)
- Put the three tab pages side by side in one strip container, `x = −index × width`. On a tab tap, animate the container's x from
  the current to the target position:
  - **0.50 s**, `CAMediaTimingFunction(controlPoints: 0.372, 0.952, 0.716, 1.0)`;
  - SwiftUI equivalent: `.timingCurve(0.372, 0.952, 0.716, 1.0, duration: 0.50)` applied to one `offset`.
- The duration is the same for 1- and 2-page jumps; for 2 pages the Home page passes through the middle (INFERRED).
- The bottom nav stays still. Everything above it moves with its page, each page's own header included: on v552 the "Leaderboard"
  title and tabs slid with the list, and the Shop page carries its own coin pill and title.
- Selection state (raised tile + label) switches on the first frame, together with the button's click and haptic.
- **Feel budget (owner 03:00, V3):** 0 frames over 20 ms during the slide. The pages are already pre-mounted
  (`HomeLive.tabsMounted`), so the slide must be a render-server animation:
  - one `CABasicAnimation` on the strip layer's position, or one SwiftUI offset change;
  - no per-frame SwiftUI body evaluation of the home scene or the list.

  Measure with `FrameProbe` on the phone. Keep the puppets running. Hidden-page opacity stays 0 outside the two (or three) pages
  that are in view.
- A tap on a tab during a slide retargets from the current position (DECISION). A popup queued by the tab action shows when the
  slide completes (v552 Weekly case).
- Keys: `ui.json transition.tabSlide.duration 0.50`, `transition.tabSlide.curve [0.372, 0.952, 0.716, 1.0]`; `transition.homeTabs`
  is retired. Test pin to change: `Tests/ShellTests.swift:226 XCTAssertEqual(ui.homeTabsFade, 0)`.
- Item 5 (glitches): no other page may flash during the slide. Only the pages the strip exposes are visible, and the parked
  level / home layers stay at opacity 0.

### 6.1b Closable Shop card stagger (V2)
Each row `offset(x:)` starts at +393 and settles with `.spring(response: 0.40, dampingFraction: 0.66)` (overshoot ≈ −25 pt at +0.27 s,
settled by +0.6 s). Rows start 0.045 s apart; the header and X are instant. Not on the Shop TAB.

### 6.2 Popup punch (item 8)
- Apply to the PANEL only (never the dim): `transform.scale` keyframes, t from the popup's first frame:
  - (0.000, **1.022**) → (0.033, 0.969) easeOut → (0.067, 0.967) linear → (0.133, **1.000**) easeInOut;
  - anchor = the panel's centre.
- The dim reaches its alpha in the first frame (`popup.dimFadeIn 0` stays). Close stays 1 frame for panel and dim together.
- Families:
  - VERIFIED: Pause (v552) and Quit Level? (V2).
  - INFERRED, until R1/R4/R5: Continue?, Level Failed, More Lives, booster info, event offers, the Streak Race list popup.
  - **NOT** (VERIFIED instant on v552): Out of Time!, Out of Lives! (same family, INFERRED), the win panel, the Settings page,
    Profile, Edit Profile (V2).
- Keys: `ui.json popup.punch.keys [[0,1.022],[0.033,0.969],[0.067,0.967],[0.133,1.0]]`, `popup.punch.curves ["easeOut","linear","easeInOut"]`,
  and a per-`PopupID` flag `popup.punch.ids [...]`.
- Implement it as a Core Animation keyframe on the panel's hosting layer, or a SwiftUI `keyframeAnimator` on the panel. The 0 ms
  first-frame rule still holds: the first frame shows the panel at 1.022, with no wait.

### 6.3 "Close menu comes from top" (item 8) — pending R1
- If R1 shows the v552 Quit Level? / Continue? band **dropping from the top**, measure it and give the band family that motion.
  The HUD-drop family is a fair prior: easeOutBack, 0.33 s from −(band height).
- If R1 shows a punch, §6.2 already covers it.
- Until then, give the band the punch (the V2 evidence).

### 6.4 Home event badges (item 8 "rockets moving")
Draw each badge as a few layers (new original art, item 14/15): body, moving part, smoke or clouds. Loop with repeating
`CAKeyframeAnimation`s (render server, 0 main-thread work, like the puppets):
- **Flags / race badge:** a cloth wave of about ±6° skew or a 3-frame flutter, 1.25 s period. Active 8 s, then rest 7 s.
- **Rocket badge:** smoke puffs grow and fade at the base; a flame flickers (0.1 s); the rocket rises 9 pt over ≈ 0.35 s, easeOut,
  holds ≈ 1.0 s, settles 0.3 s. Once every ≈ 15–20 s (period DECISION until R7).
- **Drum / sky badge:** a hop of 5 pt, up 0.25 s easeOut, down 0.25 s easeIn, then 0.4 s of cloud drift. About every 3 s during
  active stretches.
- Stagger the three badges so that only one or two move at a time (v552: flags 0–8 s, drum 3.8–9.9 s, rocket 8.5–10.3 s).
- The Claw bar, Play and the pills stay still (VERIFIED).

### 6.5 Remove the celebration skip (item 3, OWNER)
- Delete the skip catcher `CelebrationSkip` (S2Hooks.swift:430, HUDView.swift:61) and the `skip(fromTap:)` path in
  `WinLogoSequence`. Keep a non-interactive accessibility marker such as `celebration.running`, because GameFlowTests.swift:151
  waits for `celebration.skip` as "the celebration runs".
- Taps during W … panel are swallowed: no click, no haptic, no ripple, no board input. The panel comes at W + 4.034 on every win.
- Tests encode the old behaviour; they change as a stated requirement change, not a weakening:
  - `UITests/ShellS2UITests.swift:69 testCelebrationTapSkipsToThePanel` becomes "a tap at W + 1.30 does NOT skip; panel at W + 4.034";
  - `UITests/WinLogoUITests.swift:11 testEarlyTapIsIgnoredAndATapAtTheOUTPeakSkips` becomes "taps at W + 0.2 and W + 1.30 are
    ignored";
  - `Tests/WinLogoTests.swift:303` (`skipFrom 0.41`) goes;
  - `ui.json win.skipFrom` goes;
  - LOGO-SPEC D9 / A6 are superseded by item 3.
- The autoplayer and the UI suites lose ≈ 3.6 s per win. Check suite time budgets.

### 6.6 Claims staged (item 8 "all the things have small animation")
- `SocSkyWin`, and the other claim screens if R8 confirms, follow §3.2:
  - title letters pop left → right, 27 ms apart, each `pop(0.12, 1.15)`;
  - island 0.28 → 0.68 (easeOutBack, peak 1.05);
  - "You win!" 0.88 → 1.28 (peak 1.04);
  - portrait 1.20; count-up **linear** 1.38 → 2.38; glow 2.44;
  - "sharing" line 1.53;
  - winners 1.61 + 0.13·k;
  - "Tap to Claim" 2.36.
- Taps before "Tap to Claim" do nothing. Ours accepts them from 0.6 s; DECISION to accept from 2.36, like v552's order.

### 6.7 Unlock card dismiss + entrance
- Dismiss: the content goes in 1 frame, the dim fades linearly over 0.233 s (`unlock.dismissFade 0.233`, plus a `dismissMode
  "contentCut"`). `UnlockBeats` is a frozen ShellContract type (ruling 29), so its default needs an orchestrator amend and its two
  test pins (ShellS2Tests:87, TuningTests:87).
- Entrance beats (optional): icon 0.18 / title 0.38 / "Unlocked!" 0.57 / card 0.68 on v552, against 0.26 / 0.50 / 0.62 / 0.78 today.

## 7. Phone recordings needed (the phone is unavailable now; for the orchestrator's next phone session)

General rules:
- `phone rec OUT.mov SECONDS` at 60 Hz; start ≥ 0.5 s before the action and keep ≥ 1 s after.
- Run `research/motion-tools/segs` on each file (edit-list holes).
- No coins spent; restore the owner's settings (Sound ON, Music OFF, Haptic ON, Notifications ON).
- Name files `S4-<id>-….mov`.

| id | pri | what to open, exactly | seconds | answers |
|---|---|---|---|---|
| **R1** | P0 | In a level BEFORE the first board tap (the timer stays frozen, no life at risk): tap ◀ (38, 88) → wait 2 s → X on "Quit Level?" → wait 1 s → ❚❚ (352, 88) → wait 1.5 s → Quit (269, 530) → wait 2 s → X → Resume. Plus 1 lossless shot 1 s after the first open | 12 (two 6-s recs) | item 8 "close menu comes from top": the band's entrance and exit; Pause → Quit hand-over |
| **R2** | P0 | Home: Shop tab (68, 805) → 2 s → Home (196, 800) → 2 s → trophy (325, 805) → 2 s → Shop (68, 805) (the 2-page jump) → 2 s → Home; then the coin pill (150, 70) → 2 s → Home | 14 (chain) | item 2: the slide from its first frame on v552; the 2-page jump (does Home pass through?); the coin-pill route |
| **R3** | P0 | A win: leave 1 arrow (`go3.py --win-clip`), rec, tap it, then tap the empty board at (196, 600) at ≈ +1.0 / +1.8 / +2.6 / +3.4 s | 10 | item 3 on v552: the panel stays at W + 4.03 → not skippable; ripple or click during the celebration |
| R4 | P1 | Home, 3 s each: avatar (48, 68) → Profile → X; Claw bar (196, 128) → Claw Challenge → (i) → tap → X; Streak badge (47, 235) → X; Rocket / Sky badge ("Join") → offer → X; lives pill when < 5 lives → More Lives → X | 6 × 3 | sub-page entrances (cut or slide), popup punch on offers / More Lives |
| R5 | P1 | Fail chain (costs one life; allowed): let a level time out, or 3 bumps → Out of Time / Out of Lives → X → Continue? (streak) → X → Continue? (life) → X → Level Failed → Try Again | 12 (chain) | the band family's entrance (with R1); Level Failed punch; Try Again cut |
| R6 | P1 | Pause → Sound toggle off → on (restore) → X; Settings → Sound off → on → X (press and hold each ≈ 0.3 s) | 8 | toggle knob / press states; the X press |
| R7 | P1 | Home idle, no touches, 30 s (two 15-s recs), with all three badges showing | 30 | the badges' loop periods and schedule (the rocket lift-off period); the characters' periods for the new rigs |
| R8 | P2 | Any claim ("Congratulations! … Tap to Claim": a Claw step reward or a Rocket Race join) | 6 | is the letter-by-letter title shared by every claim? |
| R9 | P2 | Rocket Race screen open + the race update after a win; Sky Jump map hop after a first-try win | 6 + 6 | "rockets are moving" on the race screen; the hop curve |
| R10 | P2 | Leaderboard: Weekly → World → Country → Weekly | 6 | V2 says instant: confirm on v552 |
| H | **P0** | **Owner by feel**, not a recording: the checklist §5.4 | — | the original's haptic map (item 7) |

## 8. Corrections to earlier documents (so later agents stop reading the old values)

| document · place | said | now |
|---|---|---|
| research/motion.md §1 "popups" + §6.3 "Paused / Quit Level? full size on the first frame"; clips-needed #12 "one-frame cuts at 10 fps" | popups instant | Pause (v552 60 Hz) and Quit (V2) **punch** 1.022 → 0.967 → 1.0 over 0.133 s; the dim is instant; close instant |
| SPEC-ui §1.8 / SPEC-motion-audio §7 "home tabs: instant page swap (DECISION / INFERRED from 1-fps shots)" | hard cut | **push slide 0.50 s**, 1 − (1 − u)^2.56, VERIFIED v552 + V2 |
| SPEC-motion-audio §8.1 / meta.md §8 "home idle" | the badges were not measured | the badges animate (flags, rocket lift-off, drum hop), VERIFIED v552 |
| SPEC-motion-audio §6.3 row 7 / `unlock.dismissFade 0.16` (V1 25 fps) | whole overlay fades 0.16 s | content cut + dim linear 0.233 s (v552 ×2) |
| SPEC-motion-audio §9 Sky Jump win "count-up 1.0 s easeOutQuad" (DECISION) | from S, easeOutQuad | LINEAR 1.0 s from S + 1.38 s; full staged sequence §3.2 |
| SPEC-motion-audio §5 / LOGO-SPEC D9 / CONSISTENCY W-8 "tap to skip" | skippable from W + 0.41 | not skippable (OWNER item 3, ruling 37c) |
| SPEC-motion-audio §12.1 `win` | `.success` at the slam | `.heavy` 1.0 at the slam + letter / bounce / firework beats (§5) |

## 9. Decisions for the owner (defaults apply if no answer)
- **D1 Popup punch reach.** v552 shows it on Pause (and V2 on Quit), while Out of Time and the win panel are instant.
  **Default:** punch on every boxed or band panel popup, and keep the v552-verified instant ones instant. Alternative: punch
  everywhere, "feels alive".
- **D2 Settings / Profile / event pages.** They cut on v552 and V2. **Default:** keep the cut (1:1). Alternative: give them the same
  push-slide from the right.
- **D3 Letter haptics.** **Default:** 5 rising rigid clicks. Alternative: a single click when the word lands.
- **D4 Button haptic strength.** **Default:** rigid 0.60, and Play 0.75.
- **D5 Badge idle loops on the new event art.** **Default:** yes, with the timing in §6.4.

## 10. Evidence files (design/publish/motion-evidence/)
| file | what |
|---|---|
| v552-pause-open-punch.jpg | S3-L092 1.498–1.697, every frame: the Paused panel's punch |
| v552-tab-slide-home-to-leaderboard.jpg | S1-weekly-contest-open 0.00–1.00 every 2nd frame: the page slide tail, then the Weekly tutorial pops |
| v552-tab-slide-nav-static.jpg | the same clip, the bottom nav band: static during the slide |
| v2-nav-order.jpg, v2-tab-slide-home-to-shop.jpg | V2's 5-tab nav order and a 2-page slide (with a start hitch) |
| v2-quit-level-punch.jpg | V2 80.563–80.748: Quit Level? punch |
| v2-closable-shop-cards-slide-in.jpg, v2-closable-shop-close-instant.jpg | V2 71.1–72.25: the card stagger and the 1-frame close |
| v552-popup-stills.jpg, v552-fail-chain-stills.jpg | the band vs boxed popup families (meta-092, 007, 113, 115, 163, 065, 013–016, 114, meta-093) |
| v552-home-badges-rocket-liftoff.jpg, -skyjump-hop.jpg, -flags-wave.jpg | META-home-idle-12s, the badge column at 0.1 s steps |
| v552-skyjump-claim-sequence.jpg | S3-skyjump3-win-claim 1.20–4.28: the staged claim |
| v552-launch-to-loading.jpg | F00: publisher splash → Loading |

## Appendix A — raw series

**A1 Pause punch (v552 S3-L092; width of the blue panel / yellow title in pt, 1 px = 1 pt).**
F = 1.514: 382/269 · 1.531: 366/258 · 1.547: 362/255 · 1.564: 361/255 · 1.581: 362/255 · 1.597: 365/257 · 1.614: 369/259 ·
1.631: 372/262 · 1.647+: 374/263 (rest). Panel centre x 200 (constant), y 430 → 428 → 427.5 → 429.5. Dim: board white 255 → 28 in
one frame (alpha 0.89). Close at 4.193: one frame. The Resume press at 4.143 (114 → 109 pt) is 3 frames before the close.

**A2 Tab slide, v552 tail (S1-weekly-contest-open, page offset in pt, every 16.7 ms from clip 0.000).**
90, 77, 65, 54, 45, 36, 28.5, 22, 16, 11, 7, 4, 2, 0 (0.216).

**A3 Tab slide, V2 Shop → Leaderboard (new page's offset, pt; start 28.436).**
393, 359, 327, 297, 265, 244, 220, 196, 174, 154, 136, 120, 104, 90, 76, 64, 54, 44, 36, 28, 22, 16, 12, 8, 4, 2, 0 (28.872).
Fits:
- `393·(1 − u)^2.56`, T 0.497 s, RMS 1.26 pt;
- easeOutCubic T 0.551, RMS 2.3;
- easeOutQuad T 0.428, RMS 4.1;
- exponential RMS 12.4.

The 2-page jumps start at 3.6–4.0 pt/ms, against 2.0 pt/ms for 1 page.

**A4 Closable Shop cards (V2; row offset in pt from 71.174, 16.7 ms steps).**
- First rows: 174, 113, 75, 49, 25, 6, −8, −15, −19, −22, −23, −23, −23, −21, −19, −16, −13, −10, −7, −4, −2, −1, 0 (71.543).
- The 3rd row runs ≈ 0.05 s later and the 4th ≈ 0.10 s later.
- Spring fit (D 393): ω 15.8 rad/s, ζ 0.66 → SwiftUI `.spring(response: 0.40, dampingFraction: 0.66)`, RMS 3.5 pt.

**A5 Badges (META-home-idle-12s, 15.1 s).**
- Rocket nose top y 301 at rest, 292 at 8.84 s; up > 2 pt during 8.47–10.33.
- Sky drum top y 398 at rest, 393 minimum; up > 2 pt during 3.78–4.94, 6.71–7.47, 9.20–9.87, 14.54–15.14.
- Flags moving 0.03–8.14.

**A6 Unlock dismiss (v552 mean luminance, 60 Hz).**
- S3-L100: 51 (card) → 35 (1.148, content gone) → 48, 61, 74, 88, 101, 114, 128, 141, 154, 167, 181, 194, 207, 219 → 220 (1.397).
  That is a linear dim of 0.233 s.
- S2-L070: identical steps (1.398 → 1.631).

## 11. v582 phone recordings (PH-0c, 2026-09-28 01:26–02:48 TRT)

**Source.** The owner's iPhone 15 ran the ORIGINAL at **v582** (it auto-updated from v552 on 2026-09-25). I recorded it at 60 Hz with
`research/tools/recact.sh` / `recseq.sh`.
- Clips: `research/video/S4-*.mov`.
- Re-check any number: `nice -n 19 ~/.venvs/mf3d/bin/python design/publish/tools/ph0/run_all.py [name]`. The names are listed in
  that file.
- Evidence sheets: `design/publish/motion-evidence/v582-*.jpg`.
- Balloon Rise (PH-0b): `build/p/PH0/balloon.md`.

**Tags.** **VERIFIED v582** = measured on these clips. v582 is not v552. When a v582 value differs from a v552 row above, the
difference may be a v582 change; it is not proof about v552. Where both exist, they are compared. `F` = the first frame the new
state is on screen. `W` = the wave start, estimated as the dim onset − 1.355 s (LOGO-SPEC D8), ±1 frame.

### 11.1 Headline

1. **R1: "the close menu comes from top" is literal.** VERIFIED v582.
   - The **Quit Level?** band and the **Continue?** bands **drop in from above the screen**, overshoot ≈ 28–32 pt downward, dip
     6 pt back, and settle **0.283 s** after F. They do not punch. The dim is at full alpha on F.
   - **Cancel (X)** sends the band back **up**: easeOutQuad 0.302 s, with the dim fading linearly over 0.300 s.
   - **Going on** in the fail chain (Quit, or X on a Continue? step) sends it **down**, off the bottom, after a 2-frame
     anticipation up. The dim stays.
   - Pause → Quit is a 1-frame hand-over (the panel vanishes on the band's F).
   - This **replaces** §3.2's "give the band the punch (INFERRED)" and settles §6.3: the band family gets the drop (§11.2).
2. **R2: tabs.** VERIFIED from the first frame.
   - The tab slide is `remaining = D·(1 − u)^2.51`, `u = t / 0.488 s`, RMS 0.62 pt. The four other 1-page slides repeat the
     series within ±1 pt. The first moving frame is already 34 pt in.
   - §6.1's curve (0.50 s, 2.56) fits within RMS 1.17 pt (max 2.2 pt), so it stays valid.
   - **The 2-page jump** (Leaderboard → Shop) has the **same duration** and twice the distance. Home passes through the middle,
     centred at +0.116 s. Normalised, the 2-page series equals the 1-page series within 0.0025.
   - **The coin pill opens the Shop tab with the same slide.**
   - The raised tab jumps on the first slide frame.
3. **R3: the v582 win celebration CAN be skipped by a tap, but only after ≈ W + 1.3…1.8 s.**
   - Taps at W + 0.21 / 0.71 / 1.21 were **ignored**: no ripple, no click, and the beats were unchanged. So was a tap at
     ≈ W + 1.1–1.3 in a second clip.
   - A tap whose touch-up came at **W + 1.79** in one clip, and at ≈ W + 2.6 in the other, **cut to the win panel in one frame**
     and played **one UI click** (20 ms).
   - The unskipped control put the panel at ≈ W + 4.07 (v552: 4.034).
   - This conflicts with the owner's item 3 ("not skippable in mazeout"). The owner's ruling 37c stays binding, so A2 still
     removes our skip. **Decision for the orchestrator/owner (§11.4 D6).**
   - Our current skip accepts taps from W + 0.41, which is earlier than v582 in any case. The owner most likely tapped during
     the logo, where v582 ignores taps.
4. **Popup punch.** VERIFIED v582 on:
   - **Paused**, which equals v552 within 0.004;
   - the **Rocket Race** and **Sky Jump** offers;
   - **More Lives**;
   - **Level Failed**.

   Close is 1 frame. OD2's default is right.
5. **Sub-pages.** Profile, Claw Challenge, Streak Race and the new Balloon Rise page open and close in **1 frame** (OD3's
   default is right). The Leaderboard's Weekly / World / Country switch the list in **1 frame** on release (R10 answered: V2
   is confirmed).
6. **The toggle knob slides.** It moves 56.5 pt in **0.249 s** (easeInOutQuad, RMS 0.09 pt). The track colour and the label flip
   in 1 frame when the knob centre passes x ≈ 250 pt. The toggle has **no press scale**. The popup X presses to 0.95 while held
   and closes on release.
7. **Home idle, v582:**
   - the rocket lifts off 8 pt (up 0.5 s, hold 1.0 s, down 0.7 s) about every **12.0 s**;
   - the flags wave for 10.6 s of every 16 s;
   - the Sky drum hops;
   - the **new Balloon Rise badge** (right column) bobs ±1 pt on a **4.0 s** loop.

### 11.2 The band family (R1, R5): entrance, exits, hand-overs

**Entrance.** The table gives the band bottom's offset from rest in pt, per 60 Hz frame from F; negative = above rest.

| frame | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Quit Level?** (Super Hard purple; `S4-R1a` 2.330 and `S4-R1b` 4.693 give identical rows; rest bottom 638) | −576 | −497 | −415 | −333 | −254 | −179 | −112 | −56 | −14 | +14 | +26 | **+28** | +23 | +14 | +4 | −4 | **−6** | 0 |
| **Continue?** (after Out of Time; `S4-R5-L109-outoftime-x` 2.363; rest bottom 636) | −623 | −535 | −451 | −361 | −275 | −194 | −122 | −61 | −14 | +16 | +30 | **+32** | +26 | +16 | +5 | −4 | **−6** | 0 |

- **Fit (Quit Level?).**
  - Segment A goes from −638 (the band's bottom at the screen top, fully hidden) to +28 in **0.1875 s** along cubic-bezier
    **(0.428, 0.551, 0.651, 1.0)**. RMS 0.31 pt, max 0.7 pt. F falls 0.013 s into segment A.
  - Segment B goes +28 → −6 over 0.083 s (frames 11 → 16), then snaps to 0 at frame 17 (+0.283 s).
  - A damped spring does not fit (best RMS 11 pt), and neither does easeOutBack (19 pt).
- **Build suggestion (DECISION for A2).** Key the band's y to this 18-frame table, as ui.json keyframes at 1/60 s, with the dim at
  full alpha 0.89 on F. The Continue? row is the same shape: it starts one frame's travel higher and overshoots 4 pt more.
  Recording both rows is enough; one table within ±5 pt serves both.

**Exits and hand-overs.**

| trigger | the band | the dim | then | evidence |
|---|---|---|---|---|
| **X = cancel** (Quit Level? from ◀ or from Pause) | **up**, no anticipation: −73, −137, −199, −258, −312, −362, −408, −451, −489, −523, −553, −580, −602, −620, −635, gone. easeOutQuad **T 0.302 s, D 654 pt**, RMS 0.60 pt | **linear** fade over **0.300 s** (18 frames; board luminance 25 → 237) | the board (the level resumes untouched; Pause → Quit → X returns to the board, not to Paused) | `v582-band-cancel-exit-up.jpg`, `S4-R1a` 4.976, `S4-R1b` 7.189 |
| **Quit** / **X on a Continue? step** = go on with the fail | a 2-frame anticipation **up** (−27, −39), then **down** and off the bottom: −11, +29, +79, +137, +201, +269, +339, +410, +479, +545, +606 (≈ 70 pt/frame at the end; gone ≈ 0.23 s after the first moving frame). No standard ease fits; key it to the table | stays full | the next screen 0.08–0.13 s after the band is gone (Level Failed panel, or the Balloon Rise "fall" page, see balloon.md §5) | `v582-band-proceed-exit-down.jpg`, `S4-PH0b-L112-quit-step2` 2.297, `S4-R5-L109-continue-x` 2.063 |
| step → step inside the chain (Quit "25 token and your streak" → "a life"; Continue? token → life) | the band **stays**; only its content swaps, in 1 frame | stays | — | `S4-PH0b-L112-quit-step1` 2.180 |
| Out of Time! → Continue? | Out of Time vanishes on the band's F (1-frame hand-over) | stays | — | `S4-R5-L109-outoftime-x` 2.363 |
| Paused → Quit → Quit Level? | the Paused panel vanishes on the band's F | stays | — | `S4-R1b` 4.693 |
| Try Again | 1-frame cut to the level, then the level intro (§3.4) | — | — | `S4-R5-L109-try-again` 2.080 |

On Super Hard levels the band, the Paused panel and the Level Failed panel are **purple**, with a "Super Hard" skull ribbon; on
normal levels they are blue. Only the colour differs; the motion is the same.

### 11.3 Punch, pages, tabs, toggles (R2, R4, R6, R10)

**Popup punch.** Width ratio per 60 Hz frame from F, measured on a straight row of the panel frame.

| popup | clip | F, +1 … +8 (+0.133 s) | rest width |
|---|---|---|---|
| **Paused** (Super Hard) | `S4-R1b` 2.196, `S4-R6` 1.980 (identical) | 1.022, 0.984, 0.973, 0.967, 0.967, 0.973, 0.984, 0.995, 1.000 | 365 pt |
| v552 Paused (§3.2, reference) | S3-L092 | 1.022, 0.980, 0.969, 0.967, 0.969, 0.976, 0.986, 0.995, 1.000 | — |
| **More Lives** | `S4-R4-lives-open` 2.047 | 1.019, 0.984, 0.967, 0.965, 0.967, 0.973, 0.984, 0.992, 1.000 | 369 pt |
| **Rocket Race offer** | `S4-R4-rocket-open` 2.014 | 1.019, 0.981, 0.967, 0.965, 0.965, 0.973, 0.981, 0.992, 1.000 | 368 pt |
| **Sky Jump offer** | `S4-R4-sky-open` 1.964 | 1.016, 0.978, 0.967, 0.962, 0.962, 0.970, 0.978, 0.989, 0.997, 1.000 | 369 pt |
| **Level Failed** (Super Hard; after the band falls) | `S4-R5-L109-continue-x` 2.379 | 1.049, 0.989, 0.984, 0.967, 0.965, 0.967, 0.978, 0.986, 0.995, 1.000 | 369 pt |

On every row the dim is complete on F, and closing (X) takes 1 frame. Level Failed differs in two ways: its first frame is larger
(1.049), and it lasts one frame longer (rest at +0.150 s). Its keys after F stay within 0.02 of the family.

**Pages and sub-pages.**

| moment | v582 | vs this catalog |
|---|---|---|
| Profile (avatar) open / X | 1-frame cut both ways, no motion after | = V2 (§3.1); OD3 ✓ |
| Claw Challenge (bar) open / X | 1-frame cut | OD3 ✓ |
| Claw (i) | dim and content in 1 frame, then small staggered pops for ≈ 0.5 s | like the Weekly info (§3.2) |
| Streak Race (badge) open / X | 1-frame cut | OD3 ✓ |
| **Balloon Rise** (new badge) open / X | 1-frame cut. A speech-bubble tooltip pops in over ≈ 0.13 s after the cut. After a win, the balloon rises about 47 pt per step over ≈ 1.1 s (ease-in-out, starting +0.09 s). After a fail, the "fall" page drops it 285 pt in ≈ 0.95 s | new (balloon.md §2, §5) |
| Rocket / Sky offers, More Lives | punch (above) | OD2 ✓ |
| Leaderboard Weekly / World / Country (R10) | touch-down: the tab presses (1 frame, 2–3 frames before release); release: the list and the tab state swap in **1 frame**; nothing moves afterwards (4 of 4) | = V2 (§3.1) ✓ |
| Win panel, v582 | **the Streak Race strip is replaced by a Balloon Rise strip** while Balloon runs. ≈ 0.18 s after the panel, the strip's balloon slides one step right (39 pt, ≈ 0.77 s, ease-in-out) | new (balloon.md §5) |
| A Rocket Race offer that opens by itself on HOME after a win's Continue | seen after L109 (its entrance was not recorded) | §3.2 "event offer popups" |

**Tabs (R2).** Remaining page offset in pt per 60 Hz frame. Frame 0 = the last still frame.

| transition | series (26 frames) |
|---|---|
| Home → Shop (the page comes from the left), `S4-R2-tabs-chain` 1.980 | 393, 359, 329, 299, 271, 245, 220, 197, 175, 155, 137, 120, 104, 90, 77, 65, 54, 45, 36, 29, 22, 16, 12, 8, 4, 2, 0 |
| Shop → Home, Home → Leaderboard, Shop → Home again, coin pill → Shop | the same series within ±1 pt (5.091, 8.036, 13.411; `S4-R2-coinpill` 1.947) |
| **Leaderboard → Shop (2 pages)**, 10.716 | 786, 717, 657, 597, 541, 488, 439, **393** (Home centred), 350, 311, 274, 240, 208, 180, 154, 130, 108, 89, 72, 57, 44, 33, 23, 15, 9, 4, 0 |

- **Fit.** `D·(1 − u)^p`, `u = t / T` from the last still frame:
  - 1 page: T 0.488 s, p 2.51, RMS 0.62 pt;
  - 2 pages: T 0.488 s, p 2.50, RMS 1.12 pt;
  - V2 (Appendix A3), refitted the same way: T 0.490 s, p 2.52.
- **§6.1's (0.50, 2.56):** RMS 1.17 / max 2.2 pt for 1 page; RMS 2.16 / max 4.2 pt for 2 pages. **Recommendation:** use
  **(0.488 s, p 2.51)**, which holds the G3 "±2 pt" gate on the 2-page jump too. Equivalently, keep the bezier and set 0.488 s.
- **Nav.** The raised tab and its label jump to the target on the slide's first frame. The new tab's icon briefly grows and
  settles (≈ 0.05 s; seen on the sheet, not measured). The page under the nav slides; the nav bar does not.

**Toggles and presses (R6).**

| moment | v582 |
|---|---|
| **Toggle** (Paused → Sound; tapped OFF, then ON again; restored and checked in shot 032) | The knob slides **56.5 pt** (291.5 ↔ 235.0) in **0.249 s**, **easeInOutQuad** (RMS 0.09 pt). The ON-green track and the "ON"/"OFF" label flip in 1 frame when the knob centre passes x ≈ 250 pt: 68–78 % of the way when turning OFF, 22–32 % when turning ON. The toggle has **no press scale** (the knob stays 55–56 pt wide). Both directions are identical (`S4-R6` 4.027 and 5.857). |
| **Popup X press** (held 0.3 s) | 0.95 (42 → 40 pt) on the touch-down frame, held while pressed; the popup and its dim close in 1 frame on release (`S4-R6` 7.754 → 8.054). This VERIFIES §3.3's "0.95 like every GameButton" for the X |
| the Settings-page toggles | not recorded (R6's second half) |

### 11.4 R3 in detail: the celebration skip on v582

Tap times: the phone runner's per-tap start times (host `ms`), mapped to clip time through the arrow taps' ripple frames. The
arrows in the same `taps` call land 0.449 / 0.450 s apart against 0.465 / 0.443 s requested, so the error is ≈ ±0.02 s. A
touch-up follows its start by ≈ 0.09 s (click 5.115 against a tap started at 5.023).

| clip | taps after the last arrow (clip time → W+) | W | panel F | panel − W | what skipped | audio |
|---|---|---|---|---|---|---|
| `S4-L111-win` (**control**, no taps) | — | 4.253 | 8.320 (partial), 8.337 | 4.07–4.08 (v552: 4.034; a 50 ms capture hole at 8.27–8.32) | — | digital silence |
| `S4-R3-L109-win-taps` (4 taps, ≈ 1.33 s apart) | ≈ 8.92–9.10 (W+1.09…1.27) · ≈ 10.25–10.43 (W+2.42…2.60) · 2 more after the panel | 7.830 | **10.434** | **2.60** | the 2nd tap | **one** 20 ms click at 10.425 (−13 dBFS) |
| `S4-R3-L112-win-taps-n6-g0.0` (6 taps, gap 0) | 3.534 (W+0.21) · 4.028 (W+0.71) · 4.529 (W+1.21) · **5.023 (W+1.70; touch-up ≈ W+1.79)** · 5.549, 6.073 (on the panel, below Continue) | 3.314 | **5.109** | **1.80** | the 4th tap | **one** 20 ms click at 5.115 (−14.8 dBFS) |

**What an ignored tap does.** Nothing:
- no ripple (`v582-r3-tap-skips-celebration.jpg`);
- no click;
- the beats are unchanged: the dim ramp starts at W + 1.355 and lasts 0.35 s in all 3 clips, and the confetti starts at
  ≈ W + 1.69.

**What the skip does.** On one frame, about one frame after the touch-up:
- the logo and the dim ramp give way to the **complete win panel** at the full dim;
- a few confetti and rocket streaks keep moving around the panel for a handful of frames;
- the UI click plays (the same 20 ms click as buttons; the level and the unskipped celebration are silent);
- the panel then behaves as unskipped: the Balloon strip slides after ≈ 0.18 s.

**The window.** It opens between a touch-up at **W + 1.30** (ignored) and one at **W + 1.79** (skips). That brackets the OUT!
slam / confetti / win haptic (W + 1.655–1.688) and the dim's end (W + 1.704). INFERRED: the skip is enabled once the logo has
landed. A third run at ≈ W + 1.45 was planned, but the level (L113) was lost, so the edge stays within ±0.25 s.

**D6 (decision for the owner / orchestrator; default = ruling 37c).**
- **(a) Default:** no skip at all, as the owner asked. A2 removes `CelebrationSkip` and re-states the 4 tests as planned.
- **(b) Match v582:** ignore every tap until W + 1.70, then a tap cuts to the panel in 1 frame with the UI click. The owner's
  "in our game it is skippable" would also be fixed, since today's skip starts at W + 0.41, inside the window v582 ignores.

Do not choose (b) without the owner: item 3 is their word.

### 11.5 Home idle, v582 (R7, `S4-R7-home-idle-a/b`, 2 × 16 s, no touches)

| element | v582 | v552 (§3.5 / A5) |
|---|---|---|
| Rocket Race badge (lift-off) | nose top 301 → 293 pt (8 pt): up 0.55 s (1.90 → 2.45), hold ≈ 1.0 s, down ≈ 0.75 s (3.45 → 4.20); the next lift-off 13.9 s → **period ≈ 12.0 s** | 9 pt, up 8.47 → 10.33 |
| Streak Race flags | wave for 10.6 s of the 16 s clip (1.02 → 11.63) | 8.1 s of 15 s |
| Sky Jump drum | hops in bursts (1.2–2.8, 2.9–4.1, 4.5–5.5, 5.7–6.6, 7.0–9.3, 12.0–14.8 s) | 4 hops in 15 s |
| **Balloon Rise badge (new)** | the balloon bobs 196 ↔ 198 pt (±1 pt), **period ≈ 4.0 s** (lows at 0.0, 3.6–4.1, 7.6–8.1, 11.6–12.0, 15.6–16.0 s), with small sparkle bursts ≈ 1.1 s apart | — |
| scientist, workers | continuous idle loops (active 12.9 s / 11.4 s / 10.2 s of 16 s) | §3.5 |
| Claw token, Play | still | — |

### 11.6 Still open after this session

- **R8**: a claim screen. It needs 5 Balloon wins in a row; the best run was 3.
- **R9**: the Rocket Race screen and race update, and the Sky Jump hop. It needs joining an event; skipped.
- **R6** on the Settings page.
- **The Balloon first open.** The player had already seen it.
- **R3's exact edge** (±0.25 s).
- **The haptic checklist H.** Only the owner can feel it.

**Incident (honesty).** On L113 the bot misread the board (a large elevator plus pink tapes) and lost all 3 hearts mid-round. A
later tap of the same 18-tap round hit "Add Lives 900" on the Out of Lives popup, which **spent 900 coins** (8778 → 7878). No real
money and no ad were involved. I declined everything after that with X (Add Lives 1900, 2 × Play On 1900) and played no more levels.
Details: `build/p/PH0/balloon.md` §7.

### 11.7 Evidence (v582)

| file | what |
|---|---|
| `v582-band-drop-from-top.jpg` | `S4-R1a` 2.313–2.630, every frame: the Quit Level? band drops from the top |
| `v582-band-cancel-exit-up.jpg` | `S4-R1a` 4.94–5.28: X → the band goes up, the dim fades |
| `v582-band-proceed-exit-down.jpg` | `S4-PH0b-L112-quit-step2` 2.26–2.66: Quit → anticipation, then the band falls out |
| `v582-r3-tap-skips-celebration.jpg` | `S4-R3-L112-win-taps-n6-g0.0` 3.3–5.2, every 3rd frame: ignored taps, then the skip to the panel at 5.109 |
| `v582-tab-slide-2page-jump.jpg` | `S4-R2-tabs-chain` 10.70–11.17: Leaderboard → Shop, Home passing through |
| `v582-balloon-fall-after-quit.jpg` | `S4-PH0b-L112-quit-step2` 2.6–4.4: the Balloon Rise page inserted into the fail flow, the balloon falls 3 → 0 |
