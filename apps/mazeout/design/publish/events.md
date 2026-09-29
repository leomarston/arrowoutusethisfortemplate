# Arrow Out — events catalog + weekly rotation (PUBLISH item 14)

Author: events/rotation planner, 2026-09-28. This phase only investigates and plans: no App/Packages/Tests/UITests edits, no simulator,
no phone. Tags: **VERIFIED** = seen in a phone shot/clip, a video frame, a file or a live web page (source given). **INFERRED** =
reasoned from several signals. **DECISION** = ours; each one is a tunable or an owner question (§12).
Reference script: `design/publish/tools/rotation_ref.py` (the rotation generator; it prints the calendar and a golden table).

---

## 0. TL;DR

- The original has run **6 events + 1 shared system** so far: Weekly Contest, Streak Race, Rocket Race (v372), Sky Jump (v443),
  Claw Challenge (v552), **Balloon Rise (v582, released 2026-09-25, after our research: we do NOT have it)**, plus the x1→x100
  win-streak multiplier.
- The original does **not** rotate as far as any evidence shows. Events pile up and all run at once (the Sep 10 home had 3 badges; the
  Sep 25 phone had the Claw bar + 3 badges). Rotation is **our** answer to owner item 14, not a copy. It replaces SPEC-social D3
  ("every event every day/week forever").
- **Proposed calendar.** Streak Race (daily) and Weekly Contest (weekly) are **always on**. Two **featured slots** change every Monday
  07:00 UTC:
  - the **ladder slot**: Claw Challenge ⇄ Balloon Rise;
  - the **race slot**: Rocket Race ⇄ Sky Jump. About 1 week in 7 is a **Double Race Week** with both.

  The calendar is a pure function of the week index plus a constant seed. It is the same on every device, like a live-ops server, and
  runs for years with no updates. It is rewind-safe through the existing SocialTime high-water clock.
- **How a new week is announced:**
  - a "NEW" ribbon on the featured badge or bar;
  - the event's own page opens once, with a "New Event!" banner, on the first home visit of the week (at most 2 unrequested pages per
    home visit);
  - a local notification at a daytime local hour;
  - a red countdown on the last day, with a "Coming next: …" teaser.
- **Code plumbing.** A new pure `EventRotation` in C3 gates `Events.status`, `onWin`, `refresh` and the joins. Balloon Rise is a new
  C3 state machine. It needs no rivals, so SOC's world, `RivalProvider` and fixtures stay unchanged. It needs one small, additive
  contract amendment (EventOutcome + EventScreen), or `.custom` popups instead.

---

## 1. The owner's words (binding)

> 14- The challenges we have in our menu like says join or like other different challenges, since this is an offlien game we might want
> to find all the ones mazeout has and push them sometimes in the game. like it should feel like "oh this week this challenge came".

Also relevant:
- **Item 13:** "the international system works very good … %100 feels like online … all countries".
- **Item 15:** "the art is not same … same quality level".
- **Item 8:** "all the things have small animation".
- **Item 7:** haptics on taps.
- **SPEC.md ruling 37:**
  - (b) event art must become ORIGINAL, while rules/systems/timings stay 1:1;
  - (f) "The social world works for every country; events rotate weekly";
  - never name the original in user-facing text or store text.
- **Ruling 24:** Terms/Privacy never mention simulated players and never claim that anything is online.

---

## 2. Evidence — every event the original has or has had

### 2.1 Catalog

| # | event | how it works | reward | cadence | VERIFIED source | we have it? |
|---|---|---|---|---|---|---|
| 1 | **Weekly Contest** (Leaderboard → Weekly) | At L50 the first Play tap is intercepted. The trophy tab opens an intro ("Beat Levels! / Contest with others! / Win Rewards! / … There is a new contest every week!"). The player joins a **10-player** group. Score = levels won this week. Podium + list; the player's row is green. | ranks 1-3: **2000 / 1000 / 500** coins; Profile "Weekly Contest Wins" | weekly, ends **Mon 07:00 UTC**; unlock L28 (June build) → **L50** (July on) | phone `research/meta.md` §7 (shots 130-133, 132); social-dynamics §A; web `yt_frames/gamemobie_L50_*`, V2 29.5 s | **YES**: C3 WeeklyContest + SOC2 WeeklyViews + L50 tutorial (INTEG) |
| 2 | **Streak Race** (home badge 1 + a strip under every win/fail panel) | Daily ranking of **50** players; all start at 0 and ties sort alphabetically at the join. Each win scores the multiplier lit before the win (x1/x5/x10/x25/x100). The list pops up on the first home of the day. | ranks 1-10: **2000 / 1000 / 500 / 100×7**; none from rank 11; Profile "Streak Race Wins" | **daily**, 07:00 UTC; live at L32 on v552 (ours L30, DECISION) | phone meta §5.1 (shots 015/020/203), social-dynamics §D/§I-D; store screenshot 6; web Aug 13 frames `gamemobie_L76_streak-race-popup.jpg` | **YES**: C3 StreakRace + SOC2 StreakRaceViews |
| 3 | **Win-streak multiplier** (shared system, not an event) | x1 → x5 → x10 → x25 → x100 on each won level; a failed level → x1; a paid continue keeps it. Fail-chain step B: "You will lose your streak!" | feeds #2 and #4 | always, from the Streak Race unlock | phone flows/fail.md, levels L47/L52 (140 → 141) | **YES**: C3 Streak.swift |
| 4 | **Claw Challenge** (bar under the top row) | Solo ladder of **20 steps**. Points per win = the multiplier. The bar fills to each step's threshold (overflow carries). A fail keeps the points but resets the multiplier ("You will lose 100 token and your streak!"). The first-open page follows the L32 win. | steps: ∞ lives 30m…6h, 100…2000 coins, bulbs, hourglasses; **step 20 = 10000 coins** | **weekly**, ends Mon 07:00 UTC ("3d 5h") | store note **v552 (2026-09-21)** "New Event: Claw Challenge! Beat levels without losing and increase your multiplier…"; phone meta §5.2 (shots 021-025, 033-035, 100-101, 172-173, 204) | **YES**: C3 ClawChallenge + SOC2 ClawScreen. Thresholds of steps 8-20 are DECISION (SPEC-gameplay §11.2). |
| 5 | **Rocket Race** (home badge 2, "Join") | A daily offer from L55. "Start" grants ∞ 30m. **5 lanes** (you + 4 rivals): "Beat **5 Levels** before others to win." Stages 1-3. A loss shows "You lost the race! Try again…" and can be re-joined at once. A race bar replaces the Streak strip on the win panel. | stage 1: **500 coins + ∞ 45m** (VERIFIED); stages 2-3 DECISION (1000 + ∞ 90m, 2000 + ∞ 3h) | offer **per event day**; a race ends at the first finisher or the day end | store note **v372 (2026-08-21)**; phone shots 163-189, social-dynamics §E; web Sep 10 `dazecheck_L123_rocket-race-popup.jpg`, `dazecheck_L122_win-panel-race-bar.jpg` | **YES**: C3 RocketRace + SOC rivals + SOC2 RocketRaceViews |
| 6 | **Sky Jump** (home badge 3, "Join") | A daily offer from L40. **100 players**: "Pass N Levels in a row on first try." A fail ends the run. "Players" drops after each of your wins; the survivors share the pool. A run lasts **24 h** from Start. | pools **5000 / 7000 / 10000** for 5 / 7 / **10** levels (all VERIFIED); e.g. 5000/7 = 714 | offer **per event day**; 24 h runs | store note **v443 (2026-08-31)**; phone shots 065-096, social-dynamics §F, §I-E | **YES**: C3 SkyJump + SOC sky curve + SOC2 SkyJumpViews |
| 7 | **Balloon Rise** | Only the store note is known: "**New Event: Balloon Rise! Beat levels in a row and win amazing rewards!**" Screens, rules, rewards, cadence and unlock are **UNKNOWN**. The owner's phone was on v552 during every session. The genre event with the **same name** (Royal Match): a time-limited event of **10 steps**, each with a goal collected by beating levels (extra from Hard levels); **3 balloons**, one lost per failed level; with all 3 lost "you fall to the start of the current step"; unlock L39. | UNKNOWN | UNKNOWN (INFERRED weekly or multi-day) | store note **v582 (2026-09-25)**, apps.apple.com version history + iTunes lookup (fetched 2026-09-28); genre model: Dream Games help centre "Balloon Rise" (fetched 2026-09-28) | **NO**. Designed in §5 (INFERRED mechanics). |

**Not in the original.** No source shows any of these: daily login gift, piggy bank, chests, teams, collection/album events, a battle
pass or seasons (web-research.md §7 "Not seen in any source"; no phone screen). The July build had a 5-tab bar with a compass(?) tab
(`gamemobie_meta_*`, UNKNOWN purpose), but v552 has 3 tabs.

### 2.2 Timeline (store version history, VERIFIED 2026-09-28)

| version | date (UTC) | note |
|---|---|---|
| 59 | 2026-04-26 | launch |
| 109 … 342 | 05-02 … 08-14 | bug fixes only (14 releases) |
| 372 | 08-21 | "Meet our newest event: Rocket Race!" |
| 443 | 08-31 | "Meet our newest event: Sky Jump!" |
| 463, 507 | 09-03, 09-14 | bug fixes |
| 552 | 09-21 | "New Event: Claw Challenge!" |
| **582** | **09-25** | **"New Event: Balloon Rise!"** |

The Weekly Contest (June: "Reach level 28", July: "Reach level 50") and the Streak Race (Aug 13 video, store screenshot 6) arrived
without store notes. Since August a new event has arrived every 4-10 days. By contrast, Magic Sort adds "a new event about every two
months" (Naavik).

### 2.3 Does the original rotate? — No evidence that it does

- Aug 13 home (`gamemobie_L76_home.jpg`): one event badge (Streak Race).
- Sep 10 home (`dazecheck_L123_home-hq.jpg`, looked at): Streak "14h 26m", Rocket rank "1" "14h 26m", and Sky Jump "Join", **all at
  once**.
- Sep 25 phone (meta §1): the Claw bar + Streak + Rocket + Sky, all at once.
- **INFERRED:** events accumulate and stay on, and a server can switch them. Whether v582 turned something off to make room for Balloon
  Rise is UNKNOWN (→ §11).
- So the rotation below is a **DECISION** that serves item 14. It overrides SPEC-social D3.

### 2.4 The publisher's other games (patterns only; none of these was seen in the original)

| game | events in store notes / articles | VERIFIED source |
|---|---|---|
| Magic Sort | Broom Streak (solo milestone), Magic Streak (leaderboard), Jetpack Race (race), Sky Jump; "a new event introduced approximately every two months" | naavik.co digest; Gamigion deconstruction (search snippet) |
| Block Out | "A new Streak Race experience … Hop on your Dino" (v588, 2026-06-08); refreshed "Daily Gift" (v588); "Journey" level maps (Balloon Ride v801); "New Event: **Lily Leap**! Beat levels without failing, hop across the lily pads, and earn the grand prize!" (v828, 2026-08-10) | App Store version history (fetched) |
| Car Match | "New event" (v4.71, v5.08, Feb 2026); "Collection event", "Teams" (v5.37, 2026-02-26); "Multiple New Events and Offers" in every release since March | App Store version history (fetched) |

**INFERRED:** the publisher keeps one event framework and re-skins it across titles (Streak Race in two games, Sky Jump in two games,
Jetpack Race vs Rocket Race). **DECISION:** we build only the original's own events, adding Balloon Rise. Teams and collections would
need a team simulation or board items. A daily gift is not a "challenge" and is absent from the original. None of these is proposed.

---

## 3. What we have today (code, read 2026-09-28)

- **Events.** `Packages/PathCore/Sources/PathCore/Events/` (C3). `EventSchedule` (event day = 07:00 UTC, week = Monday 07:00 UTC from
  EPOCH 2026-04-27) and `EventRules` (unlocks 30/33/40/50/55 from social.json). `Events.onWin/onLoss/refresh/status/claim` are pure state
  machines over `PlayerState.events`, driven by the rewind-safe `EconomyClock.social` (= SocialTime high-water).
- **Always-on today.** `Events.status` gates only by unlock level. Every unlocked event is live every day/week (SPEC-social D3).
- **Home.** `App/Shell/Home/EventBadges.swift` + `ClawBar.swift`: the Claw bar on top plus a badge column (Streak, Rocket, Sky) that
  packs up when one is absent; they re-read `Events.status` every 20 s.
- **Home queue.** `App/Game/EventsDirector.swift` `HomeQueue`, in this order: claims → Rocket lost result → daily offers (Rocket, Sky;
  once per event day) → the day's Streak list → the Claw first-open page → rating. Unrequested pages are off under `-pc.uitest` /
  `-pc.capture` (ruling 33).
- **Notifications.** `App/Game/NotificationPrompt.swift`: `livesFull` + `weeklyEnding` (2 h before), scheduled at background.
- **Frozen contracts that matter here:** `Events/EventTypes.swift` (EventOutcome, RivalProvider), `Model/IDs.swift` (EventID),
  `Economy/PlayerState.swift`, `App/Contracts/ShellContract.swift` (EventScreen = claw/streakRace/rocketRace/skyJump; PopupRequest,
  which already has `.custom(id:params:)`), `App/Support/LaunchArgs.swift`.
- **Art.** Event art in `art/MANIFEST.json` (46 ids) is the original's look, rebuilt by us: `eventBadgeStreak/Rocket/SkyJump`,
  `clawHeaderArt`, `workerClawPair`, `workerRacers`, `skyJump*`, `rocket*`, `planetStage1-3`, `stageChest*`, `leaderboardPodium`,
  `*Logo` lettering. Under ruling 37(b) it **all needs original redraws** (the art lane's job; listed in §7).

---

## 4. The rotation calendar (DECISION)

### 4.1 Principles
1. **Offline and deterministic.** The featured events of week `w` are a pure function of `w`, a constant `ROT_SEED` and the tunables.
   There is no server, no network, and no stored calendar.
2. **One calendar for everyone.** This follows SPEC-social rule 1 ("one shared world"): two friends see the same "event of the week",
   as with a real live-ops server. The brief suggested seeding from the install seed; a per-install calendar would make friends
   disagree, which reads as fake. The install seed keeps driving what it drives today (groups, rivals, matchmaking inside each event).
   Differences between players come only from **level segmentation** (§4.4), which real servers also do.
3. **Rewind-safe.** `w = EventSchedule.week(SocialTime)`, and SocialTime = max(device clock, high-water). Setting the clock back
   freezes the calendar until real time catches up, so a past week's event never comes back. A clock moved forward starts next week
   early; that is accepted, exactly as SPEC-social §5 accepts it for every event. The one-time 30-day rebase (§5) re-derives the week
   and keeps `Events.rebase` as today.
4. **Forever.** The generator iterates forward from week 0 (the world epoch). 20 years = 1,043 weeks ≈ 3k hash calls, about 10-30 µs,
   so there is no table to ship and no content update to need.
5. **Kill switch.** With `rotation.enabled = false` every unlocked event is live every week: today's behaviour, v552's look. It is
   also the fallback if social.json is missing or broken (more events, never fewer).

### 4.2 Slots

| slot | members | period | unlock (reached level) | home position (unchanged geometry) |
|---|---|---|---|---|
| **Always · daily** | Streak Race (+ the multiplier) | event day | L30 | left column slot 1 + the win/fail strip |
| **Always · weekly** | Weekly Contest | event week | L50 | trophy tab |
| **Featured · ladder** | Claw Challenge ⇄ Balloon Rise | the event week | L33 (both) | the bar under the top row (Claw bar or Balloon bar) |
| **Featured · race** | Rocket Race ⇄ Sky Jump; both in a Double Race Week | the event week (daily offers inside it) | Sky L40, Rocket L55 | left column slots 2 (-3) |

The home never holds more than the v552 home did (one bar + three badges). Usually it holds one bar + two badges.

### 4.3 The generator (`rotation_ref.py` = the reference; Swift port in C3)

For each week `w = 0, 1, 2, …` in order:
- **Ladder.** At w = 0, pick with `u01(ROT_SEED, "ladder", 0) < 0.5`. If the last `maxRun = 2` weeks were the same event, switch.
  Otherwise switch with `pSwitch = 0.65`, else keep.
- **Race.** It is a Double week when `u01(ROT_SEED, "raceDouble", w) < pDouble = 0.22` and no Double week fell in the previous 2 weeks
  (`doubleMinGap = 3`). Otherwise take the last single pick (Double weeks are skipped): if its run length is ≥ 2, switch; else switch
  with `pSwitch`.
- **Pins.** `pins[w]` overrides a week (optional; e.g. the release week). The default is none.
- Hash primitives are `socialsim/core.py` `h64/u01` = the Swift `SocialHash` (already bit-exact, SOC1). `ROT_SEED = 0x524F544154494F4E`.

**Measured on 600 weeks (the script's report):**
- The ladder is Claw 49 %, and neither event runs more than 2 weeks in a row or is absent more than 2 weeks.
- The race is Rocket 43 %, Sky 42 %, Double 14 % (≈ 1 week in 7). Each race event is absent at most 2 weeks, and Double weeks are ≥ 3
  weeks apart.
- Only **5.3 %** of weeks are identical to the week before, so almost every Monday something changes.

**The calendar it produces (live today, weeks start Monday 07:00 UTC = 10:00 TRT, 03:00 New York, 16:00 Tokyo):**

| week | starts | ladder | race |
|---|---|---|---|
| 22 | 2026-09-28 | Balloon Rise | Double (Rocket + Sky) |
| 23 | 10-05 | Claw | Sky |
| 24 | 10-12 | Balloon | Sky |
| 25 | 10-19 | Balloon | Double |
| 26 | 10-26 | Claw | Rocket |
| 27 | 11-02 | Balloon | Sky |
| 28 | 11-09 | Claw | Double |
| 29 | 11-16 | Balloon | Rocket |
| 30 | 11-23 | Claw | Sky |
| 31 | 11-30 | Balloon | Double |
| 32 | 12-07 | Claw | Sky |
| 33 | 12-14 | Balloon | Rocket |
| 34 | 12-21 | Claw | Rocket |
| 35 | 12-28 | Balloon | Sky |

### 4.4 Level segmentation (per player, deterministic)
- **Ladder.** Both members unlock at L33, so no fallback is needed. Balloon Rise takes the Claw's unlock (DECISION).
- **Race.** When the week's pick is Rocket and the player is below L55, the slot shows **Sky Jump** if the player is at L40+.
  - L40-54 players see Sky every week. L55+ players follow the calendar.
  - On a Double week an L40-54 player gets Sky only.
  - Below L40 the slot is empty (as in the original).
- **First-open pages.** The v552 beat "Claw first-open page right after the L32 win" becomes "**the live ladder event's** first-open
  page after the L32 win". A player who meets Balloon first gets the Claw's intro in its first Claw week, as that week's
  announcement (§6).

### 4.5 What happens at the Monday 07:00 UTC roll

| event | when it goes off / changes |
|---|---|
| Claw / Balloon | The week's state ends: points and step reset, as `clawRoll` does today. Unclaimed step rewards stay as claims, and claims are always presented. If the same event runs again, it restarts at step 1. |
| Rocket Race | A race already ends at the event-day end, which is the same instant (07:00 UTC), so no race crosses the roll. No offer or "Join" after the roll unless it is live. |
| Sky Jump | A run joined before the roll **keeps its own 24 h**. Players hate losing a run to a calendar. Its win is paid. The next-stage offer is not shown once Sky is off (per-day stage progress already resets at 07:00 today). |
| Streak Race, Weekly | unchanged (always on) |
| Multiplier | unchanged |

A "Join" tap that races the roll, e.g. from a stale badge or a notification, gets `JoinError.notLive(next:)`. The offer panel then shows
"This event has ended." plus "Coming next: …" instead of starting.

### 4.6 Tests and captures (determinism)
- Under `-pc.uitest` / `-pc.capture`, the rotation uses the **v552 plan (everything live)** unless `-pc.socialScenario rotation*` is
  given. This follows ruling 33: existing UI tests keep their meaning and never go red every other week. It scopes the calendar out;
  it does not weaken any assertion.
- Rotation UI tests use `-pc.now <date in a known week>` + a `rotation*` scenario. No new launch argument is needed
  (`LaunchArgs.swift` is frozen; scenario names are free strings).
- The compiled default `EventRules.Rotation.enabled = false` keeps every existing C3 unit test pinned to today's semantics. The
  shipped social.json sets `true`, and a test asserts it does.

---

## 5. Balloon Rise — our build of the new v582 event (INFERRED mechanics, DECISION numbers)

The store note says "Beat levels in a row and win amazing rewards!". The only concrete model is the genre event of the same name
(§2.1 #7). The mechanics below follow it and are **not verified in the original** (→ §11 #1).

| rule | value |
|---|---|
| slot / period / unlock | ladder slot, one event week, L33 (its first-open page after the L32 win when it is live) |
| steps | **10**; each has a goal of **puffs** (hot air): 2, 3, 4, 5, 6, 6, 7, 8, 9, 10 (= 60) |
| puffs per won level | Normal 1 · Hard 2 · Super Hard 3 (the genre's "extra from Hard levels") |
| "in a row" pressure | **3 balloons** carry the basket. A failed level (Level Failed, Quit, a killed app — the same losses that reset the multiplier) pops **one**. At 0 the basket **falls to the start of the current step**: that step's puffs are lost, finished steps are kept, and the balloons refill to 3. Finishing a step also refills them to 3. |
| paid continue | keeps the balloons (like the streak) |
| rewards (claimed on home: "Congratulations! … Tap to Claim") | 1: 100 coins · 2: ∞ 30m · 3: bulb ×1 · 4: 200 coins · 5: ∞ 1h · 6: hourglass ×1 · 7: 400 coins · 8: bulb ×1 + hourglass ×1 · 9: ∞ 2h · **10: 5000 coins + bulb ×2 + hourglass ×2** |
| after step 10 | the bar stays full, "Completed!", until the week ends; `events.wins["balloonRise"] += 1` (Profile keeps its 6 v552 tiles) |
| multiplier chip | in Balloon weeks the x1…x100 chip, which hangs under the Claw token today, moves to the Streak Race badge (same art). Balloon puffs do not use the multiplier. |

**Fail-chain wording (step B).**
- In Balloon weeks, step B shows when the streak is active **or** the current step has puffs.
- "You will lose a balloon and your streak!" / "You will lose a balloon!" / today's "You will lose your streak!". This parallels the
  Claw's "You will lose %lld token and your streak!". The two are exclusive, because the slot is.

**Bench acceptance (tuned before shipping).** The SocialBenchTests profiles are reused over 52 weeks with rotation on. The goals are
tuned, not the rewards:
- casual reaches step ≥ 5 in ≥ 70 % of Balloon weeks and completes 20-40 %;
- active completes ≥ 90 %;
- absent reaches step ≥ 2 in ≥ 50 % of the weeks it plays.

Balloon is the "reachable" week and Claw the "grind" week: 14,101 points ≈ 141 wins at x100 for Claw, against 60 puffs for Balloon.

---

## 6. How a week is announced (feels live)

### 6.1 Home
- **"NEW" ribbon** (code-drawn capsule, the new palette's accent, bold 11 pt) on the top-right of a featured badge and on the ladder
  bar's token.
  - It shows until the player opens that event's page this week. The flag key is `new-<event>-<week>`, with kind-prefix pruning like
    `soc2(once:)`, so the save does not grow.
  - Idle motion (item 8): a 6° wiggle every 6 s.
- **Arrival animation.** When a featured badge appears while home is visible, it scales in with a spring 0 → 1.08 → 1 (0.35 s) plus a
  sparkle burst (FX system). An outgoing badge fades out 0.2 s, never under a finger. MA to fold these into SPEC-motion-audio.
- **Countdowns** (the existing "Xd Yh" / "Xh Ym"): in the event's last 24 h the text turns red with a soft 1.0 → 1.06 pulse every 4 s.
- **Double Race Week:** a small "×2" gem on both race badges for the week.

### 6.2 Home queue (G2 `HomeQueue`; new items in bold)
1. claims, in the order earned (unchanged, never capped);
2. the Rocket Race lost result (unchanged);
3. **week-start pages**: once per featured event per week, the event's own page or offer. It carries a "New Event!" banner (or "Double
   Race Week!") across its header and a "Let's Go!" button with a light haptic (item 7). Order: ladder, then race.
4. daily offers (Rocket / Sky; unchanged, only when live);
5. the day's Streak Race list (unchanged);
6. rating (unchanged).

**Cap:** at most **2 unrequested pages** (3 + 4 + 5) per home visit. The rest wait for the next visit. A Double week's first day would
otherwise stack 4 pages.

### 6.3 Teaser
In the last 24 h of a week, each featured event page's footer shows "Coming next: {event} · Starts in {countdown}", with next week's
pick for this player's level (§4.4). The home gets no extra element, to avoid clutter.

### 6.4 Local notifications (offline; only with Settings ON + iOS permission; scheduled at background like `livesFull`)
- `eventStart`: the next week's featured event(s) the player has unlocked, at the first local time ≥ the start inside **10:00-21:00
  local** (else 10:00 the next morning). "{event} has started! Beat levels to win amazing rewards!" A Double week reads "Double Race
  Week! Rocket Race and Sky Jump are both on!"
- `eventEnding`: the ladder event, if the player has progress and has not finished it, 3 h before the end: "{event} ends in 3 hours!"
- At most **one event notification per 24 h**; priority ending > start. `weeklyEnding` (existing) counts in the cap. Permission is
  asked once as today; this is more *use* of it (ruling 5: never ask without using).

### 6.5 Untouched
The Leaderboard tabs, the Weekly group, the win panel's strip (Rocket bar while racing, else the Streak banner), and the claim popup.

---

## 7. Screens, art and copy each event needs

### 7.1 Screens (the ✓ ones exist in SOC2/S3; every art id must be REDRAWN original under ruling 37b)

| event | screens | art ids today (→ redraw) | new art |
|---|---|---|---|
| Weekly Contest | L50 tutorial ✓, intro ✓, board + podium ✓, result claim ✓ | `leaderboardPodium`, `trophyCup`, `weeklyContestLogo(+TR)`, `weeklyContestPopup`, `statWeeklyWinsIcon`, `navTrophy` | — |
| Streak Race | badge ✓, list ✓, win/fail strip ✓, (i) ✓?, result ✓ | `eventBadgeStreak`, `streakRaceLogo`, `streakBanner`, `streakChips`, `iconCheckeredFlag`, `workerRacers` | "NEW"/"×2" chips are code, not art |
| Claw Challenge | bar ✓, page + ladder ✓, (i) ✓, first-open ✓, claims ✓ | `homeClawBar`, `clawHeaderArt`, `workerClawPair`, `clawLogo`, `clawChevronChips`, `clawLadderNode`, `clawRewardCard` | week-start banner (code) |
| Rocket Race | badge ✓, offer ✓, join claim ✓, tutorial ✓, race ✓, lost ✓, won ✓, win-panel bar ✓ | `eventBadgeRocket`, `rocketRaceLogo`, `rocketRaceBackdrop`, `rocketOfferScene`, `rocketMine/Other`, `raceLane`, `raceBar`, `planetStage1-3` | "event has ended" state (code) |
| Sky Jump | badge ✓, offer ✓, matching ✓, tutorial ✓, map ✓, progress ✓, win ✓, fail ✓ | `eventBadgeSkyJump`, `skyJumpLogo`, `skyJumpBackdrop`, `skyJumpPad`, `skyJumpIsland(Far/Far2)`, `skyJumpPopupScene`, `stageChest*`, `iconSkyDrum` | same |
| **Balloon Rise** | **all new:** home bar; full page (a sky with a 10-node altitude track, reward cards beside the nodes, the basket + 3 balloons at the current node bobbing on a 2.4 s idle loop, a puffs bar, countdown, (i), X); (i) overlay of 5 cards + "Tap to Continue"; first-open page; step claims (existing claim popup); pop FX (code particles + a light haptic); the fall animation (basket drops to the step start, balloons re-inflate, 0.8 s) played on the bar at the next home visit; a puff flight from the win to the home bar (a PayoutSequence segment like the Claw token's) | — | `balloonBarIcon`, `balloonLogo`, `balloonBackdrop`, `balloonBasket`, `balloonSingle` ×3 colours, `balloonAltitudeNode`, reward cards reuse the ladder card chrome. Route: characters/props 3D or SVG→@3x per art/STYLE.md at the new art's quality (item 15). |
| rotation (all) | NEW ribbon, ×2 gem, week-start banner, "Coming next" footer, red last-day countdown, "event has ended" offer state | — | all code-drawn SwiftUI (GlossyChrome), no bitmaps |

### 7.2 New copy — EN now; the other 12 locales (de fr es it pt-BR tr ja ko zh-Hans pl sk sl) later
Every format with 2+ arguments uses positional specifiers (`%1$@`, memory: reordered args). Max lengths are for the measured frames;
TR/DE auto-shrink to 0.7 (ruling 14).

| key | EN | max | note |
|---|---|---|---|
| event.new | NEW | 7 | ribbon |
| event.started | New Event! | 18 | week-start banner |
| event.double | Double Race Week! | 22 | banner, both race events |
| event.letsGo | Let's Go! | 12 | week-start button |
| event.endsIn | Ends in %@ | 18 | %@ = countdown |
| event.lastDay | Last day! | 14 | red chip, last 24 h |
| event.comingNext | Coming next: %1$@ · Starts in %2$@ | 40 | footer teaser |
| event.over | This event has ended. | 26 | a stale Join tap |
| notif.eventStart | %@ has started! Beat levels to win amazing rewards! | 90 | local notification |
| notif.eventDouble | Double Race Week! Rocket Race and Sky Jump are both on! | 90 | names follow §12 #3 |
| notif.eventEnding | %@ ends in 3 hours! | 60 | ladder event with progress |
| balloon.title | Balloon Rise | 16 | name per §12 #3 |
| balloon.sub | Beat levels in a row to rise higher! | 44 | page subtitle |
| balloon.info.1 | Beat levels to fill your balloons with hot air! | 48 | (i) card 1 |
| balloon.info.2 | Hard levels give more hot air! | 40 | card 2 |
| balloon.info.3 | Fail a level and a balloon pops! | 40 | card 3 |
| balloon.info.4 | Lose all 3 balloons and you fall to the start of the step! | 64 | red card 4 |
| balloon.info.5 | Reach the top for the grand prize! | 40 | card 5 |
| balloon.step | Step %lld | 10 | node label |
| balloon.complete | Completed! | 14 | bar after step 10 |
| balloon.fell | You fell to the start of step %lld! | 44 | bar toast after the 3rd pop |
| fail.balloon | You will lose a balloon! | 40 | fail step B |
| fail.balloonStreak | You will lose a balloon and your streak! | 48 | fail step B |

The strings go into `App/Resources/Strings/strings.tsv` + `Localizable.xcstrings` (the strings lane), with the release-gate check:
no "simulat" / "bot " (ruling 24).

### 7.3 Event names (owner decision §12 #3)
The rules stay 1:1. The display names are what a reviewer reads first. "Sky Jump" is shared by two of the publisher's games, and
"Balloon Rise" by the original and Royal Match. The internal `EventID` raw values never change (they live in saves).

| id | original's name | proposed ours |
|---|---|---|
| weeklyContest | Weekly Contest | Weekly Cup |
| streakRace | Streak Race | Hot Streak |
| clawChallenge | Claw Challenge | Prize Tower (the ladder is a vertical 1→20 tower; the art moves off the claw machine) |
| rocketRace | Rocket Race | Rocket Rally |
| skyJump | Sky Jump | Cloud Hop |
| balloonRise | Balloon Rise | Balloon Climb |

---

## 8. How it plugs in (owners, files, contracts, tests)

### 8.1 C3 (PathCore Events; not frozen unless marked ◆)
1. **`Events/EventRotation.swift` (new, pure).**
   - `WeekPlan { week, ladder: EventID, race: [EventID], start, end }`.
   - `plan(week:rules:)` and `plan(at: SocialTime, rules:)`.
   - `isLive(_:at:level:rules:)`, which applies §4.4, and `next(after:level:rules:)` for the teaser.
   - No shared cache: an O(w) recompute of about 20 µs at week 520 keeps it thread-agnostic. The perf test asserts p95 ≤ 0.2 ms on the
     phone.
2. **`EventRules.Rotation`** (social.json `events.rotation`, C3's layout):
   ```json
   "rotation": { "enabled": true, "seed": "0x524F544154494F4E",
                 "always": ["streakRace", "weeklyContest"],
                 "ladder": ["clawChallenge", "balloonRise"], "race": ["rocketRace", "skyJump"],
                 "pSwitch": 0.65, "pDouble": 0.22, "doubleMinGap": 3, "maxRun": 2,
                 "pins": {}, "announceCap": 2, "teaserHours": 24, "notifyWindow": [10, 21] }
   ```
   The compiled default has `enabled: false` (§4.6). Add `"balloonRise": 33` to `unlocks`, plus an `events.balloonRise` block (goals,
   puffs per tag, balloons, rewards).
3. **`Events.status`** returns nil for non-live featured events and adds `week: WeekPlan`, `next: WeekPlan?`, `balloon:
   BalloonStatus?`. `Status` is C3's type, so this is additive.
4. **Hooks.**
   - `onWin`: the Claw scores only when live; the Balloon when live.
   - `refresh(home:)`: joins the Claw/Balloon only when live.
   - `continueWarning` gains the balloon variants.
   - `joinRocketRace` / `joinSkyJump` refuse outside live weeks with the new `JoinError.notLive(next: SocialTime?)`. `JoinError` is in
     C3's RocketRace.swift; exhaustive `switch`es in App will flag every site.
   - Sky runs cross the roll (§4.5).
5. **`Events/BalloonRise.swift`** (new) + `BalloonState { week, step, puffs, balloons }` in `EventsState`. This is additive-only
   (decodeIfPresent), so old saves decode unchanged. `balloonRoll` works like `clawRoll`. `rebase` works as for the Claw.
   `extension EventID { static let balloonRise = EventID("balloonRise") }` goes in C3's own file; ◆ IDs.swift is untouched.
6. **◆ Contract amend 4 (orchestrator):**
   - `EventTypes.swift` `EventOutcome` += `.balloonPuffs(added:total:goal:)`, `.balloonPopped(left:)`, `.balloonFell(step:)`,
     `.balloonStep(step:reward:)` (additive, then re-hash);
   - `ShellContract.swift` `EventScreen` += `.balloonRise`.

   Fallback without an amendment: present the page as `PopupRequest.custom(id: "balloonRise", …)` full-screen, and read the Balloon
   state from `Events.status` instead of outcomes. It is uglier but needs no contract change.

### 8.2 SOC (Social world + SOC2 screens)
- **World model: no change.** World/Country/Weekly boards, the Streak group, the Rocket rivals and the Sky curve do not depend on the
  calendar. `RivalProvider` and every `soc_*` fixture stay bit for bit. Balloon Rise has no opponents.
- `SocialConfig` must round-trip the new `events.rotation` / `events.balloonRise` blocks. SocialNamesTests keeps social.json equal to
  what SocialConfig encodes. Alternatively the test ignores C3-only keys.
- SOC2 pages:
  - the week-start banner, "Coming next" footer and "event has ended" state on the Claw / Rocket / Sky pages;
  - the Balloon page + (i) (SOC2 or S3, whoever owns ClawScreen).
- SocialLab (debug): a week picker that shows `plan(week:)` and jumps `-pc.now`, for the art/UI lanes and the phone check (D1b)
  without launch arguments.

### 8.3 SHELL (S3) and GAME (G2)
- **S3.**
  - `HomeEventLayer`: the ladder bar becomes `ClawBar` or `BalloonBar`.
  - `EventBadgeKind.visible` reads the live set.
  - NEW ribbon / ×2 gem / red last-day pulse / arrival spring.
  - The multiplier chip moves to the Streak badge in Balloon weeks.
- **G2.**
  - `HomeQueue` adds week-start pages + the cap.
  - The ladder first-open page is generic (`clawIntro` / `balloonIntro`).
  - `FailFlowDirector` step B wording.
  - `NotificationPrompt.plan`: `eventStart` / `eventEnding` + the 1-per-24 h cap (the plan can see several weeks ahead because the
    calendar is pure).
  - PayoutSequence: a Balloon puff segment in place of the Claw token's in Balloon weeks.

### 8.4 Tests and acceptance
| # | check | where |
|---|---|---|
| A1 | the calendar == `rotation_ref.py --json 1044`, bit for bit (a pinned fixture of 20 years) | PathCore `EventRotationTests` |
| A2 | properties over 1,043 weeks: max run ≤ 2, Double gap ≥ 3, each ladder event 40-60 %, each race event absent ≤ 2 weeks, ≤ 8 % of weeks unchanged | same |
| A3 | the plan is constant inside a week; the roll happens at Monday 07:00:00 UTC exactly; rewind (device clock back across a Monday) never shows last week's events (SocialTime); the 30-day rebase case | same + existing SocialClock tests |
| A4 | segmentation: L45 in a Rocket week → Sky; L45 in a Double week → Sky only; L35 → ladder only; L60 → the calendar | same |
| A5 | a Join outside a live week → `.notLive`; a Sky run crossing the roll finishes and pays; Claw/Balloon claims survive the roll | C3 Events tests |
| A6 | Balloon: puffs per tag, pop on each loss kind, the fall at 0, refill on a step, a paid continue keeps balloons, step claims, completed state, save round-trip + old-save decode | `BalloonRiseTests` |
| A7 | home queue: ≤ 2 unrequested pages per visit; week-start page once per event per week; NEW ribbon clears on open | G2 unit + UI (`-pc.now` + `rotation*` scenario) |
| A8 | every existing suite unchanged and green (rotation = v552 plan under uitest/capture; compiled default off) | V1 |
| A9 | Balloon bench targets (§5) over 52 weeks with rotation on | SocialBenchTests |
| A10 | FEEL: the week-start page + arrival spring on the home visit = 0 frames > 20 ms on the iPhone 15; status p95 ≤ 0.2 ms | V3 / D1b |
| A11 | mutations: drop the maxRun rule; compute the week from the wall clock (not SocialTime); Double gap 3 → 1; Balloon fall → reset all steps; notification outside 10-21 local — each caught | mutations script |

---

## 9. Economy note (for the economy / IAP lane)
- A Claw week is worth up to 14,100 coins + ∞ 21.5 h + 6 boosters, but a full ladder takes ≈ 141 wins at x100. A Balloon week pays
  5,700 coins + ∞ 3.5 h + 8 boosters and is reachable for casual players.
- A race week keeps today's per-day values. A Double week gives both.
- Alternating weeks therefore change the weekly coin inflow by more than 2× for grinders and little for casuals. The economy owner
  should look at this with the coin packs (RevenueCat consumables, ruling 37a) before shipping. All numbers are tunables in social.json.

---

## 10. Risks and honesty
1. **Rotation is not the original's behaviour** (§2.3). It is the owner's item 14. The kill switch restores v552's "all on".
2. **Balloon Rise mechanics are inferred** from one store sentence + the genre's same-name event. The phone capture (§11 #1) can
   confirm or replace them. Until then we ship our own consistent version, not a guess dressed up as a copy.
3. **Honest copy.** The event texts copy the original's phrases ("Compete against your friends!", "Finding players on your level.").
   The store listing and Terms must not claim online multiplayer (ruling 24). This is for the ASO lane.
4. **Name clash (outside this topic, flagged):** other listings already use "Arrow Out". App Store "Arrow Out Puzzle Tap Away" (id
   6757767754); Google Play "Arrow Out: Tap Away Puzzle Pro" (FunSimulation) and "Arrow Out Game - Puzzle Escape" (Gamingrat) (web
   search, 2026-09-28). The ASO lane should check that the store name is unique.
5. **Time zones (item 13).** The 07:00 UTC anchor is global, as the original's is (VERIFIED from 12 countdowns). Countdowns are
   duration-based, so they are correct in every time zone and across DST. Notifications respect the local daytime window.

---

## 11. Needs the phone (not available now)
1. **Balloon Rise in the original (v582).** First check whether the owner's copy auto-updated to v582+; updating the owner's app needs
   the owner's OK. Then record it without spending:
   - the home entry;
   - the first-open / tutorial and the (i) text verbatim;
   - the page, the step goals and rewards, and the fail behaviour;
   - the countdown / duration, the unlock level, and whether rivals exist.
2. **Rotation evidence.** Screenshots of the original's home before and after a Monday 10:00 TRT roll: does any event disappear or
   appear? Does Balloon Rise take the Claw's bar or a badge slot? Do all of Claw, Rocket, Sky and Balloon run at once in v582?
3. **Still-uncaptured result screens** (SPEC-social §11): Sky Jump fail, Rocket won, the Streak/Weekly result popups, and the (i) pages
   of Weekly/Streak/Rocket/Sky.
4. **Our build (D1b).**
   - A week-start notification arrives at a daytime local hour.
   - The NEW ribbon, arrival spring and red last-day pulse at 60 Hz with 0 frames > 20 ms.
   - The Balloon pop/fall animations, with haptics on the same frame.
   - A week jump through the SocialLab picker.

---

## 12. Decisions for the owner
1. **Rotation shape.**
   - Default (proposed): Streak Race + Weekly always on; weekly featured Claw⇄Balloon + Rocket⇄Sky, with ~1 Double Race Week in 7.
   - Alternatives: (a) keep everything always on like the original, adding only "NEW" announcements; (b) a stronger rotation with one
     featured event per week.
2. **Build Balloon Rise now** from the inferred rules (default), wait for the phone capture, or skip it.
3. **Event display names.** Keep the original's names, or use our own (§7.3). The default proposal is our own; the internal IDs are
   unchanged.
4. **Event notifications** (week start + 3 h before a ladder event ends, max 1/day): on by default?
5. **Optional pins:** feature a chosen pair in the App Store release week, e.g. Claw + Double Race, for launch screenshots.
6. **Optional seasonal weeks (P2):** date-based offline re-skins of the featured events (Halloween, Christmas, New Year). This needs
   extra art.

---

## 13. Sources
- App Store page + version history (fetched 2026-09-28): https://apps.apple.com/us/app/maze-out-tap-puzzle/id6762192889 ; iTunes lookup
  `https://itunes.apple.com/lookup?id=6762192889&country=us` (v582, 2026-09-25 02:36 UTC, "New Event: Balloon Rise!").
- Publisher's apps: `https://itunes.apple.com/lookup?id=1742757639&entity=software`; version histories of Block Out (id6752672568),
  Magic Sort (id6499209744), Car Match (id6504421808), Pixel Pop (id6759798927), Block Star (id6747201329).
- Naavik, "Grand Games and Leveling Up Mobile Casual Puzzle": https://naavik.co/digest/why-peak-games-investors-backed-grand-games/
- Gamigion, "Game Deconstruction: Magic Sort by Grand Games": https://www.gamigion.com/game-deconstruction-magic-sort-by-grand-games/
  (search snippet only; the page failed TLS from this Mac).
- Dream Games help centre, "Balloon Rise" (Royal Match): https://dreamgames.helpshift.com/hc/en/3-royal-match/faq/119-balloon-rise/
- Our research: `research/meta.md` §1, §5, §7; `research/social-dynamics.md` §A-§I; `research/web-research.md` §1, §8; `design/SPEC-social.md`
  §1, §4, §12-§15; `design/SPEC-gameplay.md` §11; web frames `research/web/yt_frames/gamemobie_L76_home.jpg`,
  `dazecheck_L123_home-hq.jpg` (both looked at).
- YouTube search (2026-09-28, event names + the game's name): no video shows Balloon Rise or the Claw; titles found are the known level
  videos (e45Uv_THi6A, A_h9Vv6EaM4) and unrelated arrow games.

---

## 14. T7 EV-REF: the final reference (2026-09-28, Wave 0)

Tags as above. Files: `tools/rotation_ref.py` (final), `tools/balloon_ref.py` (new), `tools/fixtures/rotation_1044.json`
(sha256 `f48c5f4f…c89e14`), `tools/fixtures/balloon_trace.json` (sha256 `98517f36…c0619d`). Evidence: `build/p/T7/`.

**Final constants (DECISION, each a social.json tunable).**
- `seed` = `0x524F544154494F4E`, unchanged. `pins` = `{}` (OD12 default).
- `epoch` = **1777273200** (Mon 2026-04-27 07:00 UTC) = week 0 = the **event** calendar anchor (`EventRules.Calendar.epoch`,
  socialsim `core.EPOCH`). It is pinned in the rotation block on its own, and it is **not** the world epoch: OD9 / ruling 38
  move only the social world (social-intl M8). A slipped release therefore never changes a week, and the rotation's `w` equals
  the number the Claw state keys its week with. B1 test: `rotation.epoch ≡ calendar.epoch (mod 604800)`.
- The §8.1 block gains `"epoch": 1777273200`. Everything else in it is unchanged.
- A pin replaces one week verbatim and enters the history, so the weeks after it are re-derived. Weeks before a pin never change.
  Add pins only before a release, then regenerate the fixture.

**The generator did not change.** VERIFIED: the final state machine reproduces the P1 script's calendar for all 1,044 weeks, and
the §4.3 table (weeks 22-35) is asserted by `--selftest`. One latent bug was fixed: with `doubleMinGap = 1`, the P1 code's
`rac[-0:]` scanned the whole history. It is now an explicit window. The default output is unaffected.

**Porting rules for B1.** They are in the `rotation_ref.py` docstring: the O(1) state, the three stateless draws
`u01(seed, "ladder" | "race" | "raceDouble", w)`, strict `<`, w < 0 clamped to week 0, and the kill switch = the v552 plan
(Balloon never). The fixture carries hash KATs, clock KATs, the clamp, the kill-switch table, 84 segmentation rows (A4) and
1,044 week rows with their start seconds (A1). Swift tests can read it in place, the way `SocialGoldenTests.designFixture`
reads `design/social/fixtures/`.

**A2 over the fixture (VERIFIED, weeks 0..1042 and 0..1043).** All pass:
- runs: ladder max run 2; race max run 2 (singles 2, with Double weeks skipped);
- Double weeks: min gap 3; share 14.7 %;
- ladder share: Claw 49.2 %, Balloon 50.8 %;
- race absence: Rocket and Sky each absent at most 2 weeks;
- unchanged weeks: 4.9 %.

Robustness (VERIFIED):
- The smallest |u − threshold| over 2,166 decisions is 1.5e-4, so a 1-ulp JSON parse of `pSwitch`/`pDouble` cannot flip a week.
- The structural properties held for 200 of 200 random seeds.
- 8 of 8 negative controls were CAUGHT: maxRun dropped, gap 3 → 1, pSwitch 0.05, the world epoch used, a label typo, draws keyed
  w+1, seed + 1, pDouble 0.20.
- Two runs in separate processes (different PYTHONHASHSEED) were byte-identical.

**Observation (not in A2; INFERRED product risk).** Double Race weeks average 1 in 6.8, but the gaps between them are uneven.
The longest are 39 weeks (weeks 371-410, 2033-34) and 26 weeks (weeks 69-95, Aug 2027 - Feb 2028). A 52-week window holds 4 to
12 Double weeks. A cap rule (`doubleMaxGap`: force a Double once the last one is ≥ N weeks old) was measured:

| N | first changed week | Double share | 52-week window |
|---|---|---|---|
| 12 | 81 | 16.0 % | 5-12 |
| 14 | 83 | 15.6 % | 5-12 |

A2 still passes with either value. The first changed week is ≥ 79 (Oct 2027), so the cap can ship in **any** update before then
without rewriting a week anyone has seen. It is not adopted here: it would add a rule to ruling 38's shape. This is an
orchestrator call.

**Balloon Rise rules.** PH-0b (`build/p/PH0/balloon.md`) did not exist when T7 was written or when it was checked, so the source is §5
(INFERRED mechanics, DECISION numbers). The rules block is `balloon_ref.RULES`: social.json `events.balloonRise`, a `ladder` of
`{goal, grant}` like the Claw's, plus `puffs`, `balloons`, `carryOverflow` and `popAtZeroPuffs`. The §5 goals total 60 and the
§9 week value is 5,700 coins + ∞ 3.5 h + 8 boosters; both are asserted. `balloon_ref.py` prints a warning while PH-0b exists and
the rules do not name it.

Two T7 refinements (DECISION, each one key):
1. `carryOverflow: true`. Overflow carries to the next step, like the Claw's (VERIFIED for the Claw); §5 is silent on it.
2. `popAtZeroPuffs: false`. A loss pops a balloon only while the step has puffs. This matches §5's own step-B rule ("You will lose
   a balloon!" only with puffs), and it avoids a "You fell to the start of step N!" toast for a player already there. The
   literal §5 reading (`true`) is kept and traced as the `literalSection5` variant.

The trace fixture (A6 golden) holds 3 traces:
- `main`, 47 rows: weeks 22 Balloon → 23 Claw → 24, 25 Balloon twice. It covers the fall, a zero-puff loss, a paid continue, a
  step refill after a pop, completion + wins, the roll, and the restart at step 1.
- `gate`, 5 rows: L32 → L33.
- `literalSection5`, 6 rows.

Each row gives the outcomes in EventOutcome's Codable shape, the state, the home bar, the claims, the wins, and the step-B key
with the streak off and on. Negative controls: 6 of 6 CAUGHT.

**B1 note (2026-09-28, EVENTS-P).** PH-0b landed before B1's Balloon step (OD11): `tools/balloon_ref.py` and
`tools/fixtures/balloon_trace.json` were RE-DERIVED from `build/p/PH0/balloon.md` (the v582 rules: one win-streak counter,
any failed level → 0, platforms at 2/5/8/13/20/28/36/46/77/120 paying once per event, the Profile's best streak, the fall page
from a lost streak ≥ 2; SPEC.md ruling 42c's outcome shapes). New fixture sha256 `bde984da…e87b913`; `--selftest` 6/6
negative controls CAUGHT. T7's §5-model script and trace are kept in `build/p/B1/t7/`. So §5, §7.2's puff/balloon strings,
§8.1's `.balloonPuffs/.balloonPopped` and §5's bench targets describe the superseded model; the calendar (§4, rotation_ref.py)
is unchanged and ported bit for bit (PathCore `EventRotation`, 1,044 weeks).

## PH-0a (2026-09-28, phone, v582) — the Monday 10:00 TRT reset, VERIFIED
build/p/PH0a/before-reset.png (09:50) vs after-reset.png (10:10), same home, no touches in between:
- BEFORE: the event badges (Streak flags, Balloon, Claw bar) show countdowns "09:34"; trophy tab plain.
- AFTER: the SAME badges stay on home and read **"Finished"** (Streak flags, Balloon and the Claw bar's timer chip); the trophy tab gets a red
  **"!"** badge (weekly results to see). No new event replaces them on the spot — the ended events wait in a "Finished" state until the player
  opens them (results / claims), INFERRED from the badge state; the next events appear after that.
- Implication for ours (B1 shows "This event has ended." on a stale Join and removes non-featured events): at the week boundary, keep the ended
  events' badges on home as "Finished" + a red "!" on the trophy tab until the player opens the result, then show the new week's featured events.

### B1b (2026-09-28, EVENTS FINISHED STATE) — how ours matches PH-0a
Code: `Packages/PathCore/Sources/PathCore/Events/EventFinished.swift` (C3) + the home (EventBadges / ClawBar / BalloonBar), the
pages (ClawScreen, BalloonViews, StreakRaceViews: `EventFinish.open`), the home queue (EventsDirector). Tests: PathCore
`EventsFinishedTests` (11), app `EventsB1Tests.testTheEndedEventsAreHeldUnderTheShippedRotationOnly`, UI
`EventsRotationUITests.testTheIdleHomeReadsFinishedAtTheMondayRollUntilEachResultIsOpened` + `…TheClaimThenTheNewDay…`;
mutations f1-f8 in `Packages/PathCore/Tests/tools/events_mutations.py`.
- **Held** (VERIFIED look): an instance the player took part in (joined) that ends at a roll becomes a `FinishedEvent` snapshot:
  the Hot Streak badge's pedestal reads "Finished" (daily roll too), the ladder bar (Treasure Climb or Up & Away) keeps its final
  numbers with its timer chip reading "Finished" (in place of this week's ladder event), and the trophy tab gets the red "!" for
  the ended Weekly Cup — on an idle home too (both re-read every 20 s).
- **Opened** (INFERRED "until the player opens the result"): the Finished bar's page shows the ended week as it stood (chip
  "Finished"); the Hot Streak page (badge tap, or the day's auto-shown list) and the Leaderboard tab open theirs; the ended
  contest's rank-prize claim is its result too ("the claim, then the new week"). Then the new instance shows in the slot (NEW
  ribbon); the home queue's ladder week-start page waits while the slot is held and follows the open.
- **DECISIONS** where PH-0a is silent: a counted win moves the player into the new instance of what it scores (Hot Streak, the
  live ladder event) and drops those holds (never a Finished bar over points just earned); a loss drops nothing; a hold is one
  instance deep (the next roll drops it: a player who never opens it loses one period's badge, never an event; a returning
  player sees no stale Finished); the race badges (Rocket Rally / Cloud Hop offers) follow the calendar as before (PH-0a showed
  them unchanged, "Join"; a stale Join still says "This event has ended."). Rules untouched: the new instances join and score as
  before. Only while the rotation runs: the kill switch / -pc.uitest v552 plan is byte-for-byte today's.
- **FEEL** (sim FrameProbe, `-pc.finishedProbe`): the flip itself must not hitch an idle home — the ladder bar keeps its view
  identity across live → Finished → this week's bar, and the "Finished" rasters + the trophy dot are made while home is first
  built (Debug: 39 + 27 ms at the flip → 0 frames > 20 ms over 50 s). Release sim, 11 runs of the final flip code: 0 frames > 20 ms
  in 6; one 33-38 ms frame at the flip in 5 (taken while other agents built: host load 10-30 where logged; Time Profiler: ~13 ms of main-thread
  SwiftUI update spread over the changed badge views — no single hotspot; ~3 ms of it is `Tokens.text` lookups, ObjC
  dictionary bridging + hex parsing per call). The Finished page's open: 0 frames > 20 ms (4 final runs). Its X back home: the
  65-75 ms return first measured was the session's FIRST return home after parking, whatever the page (a Profile round trip:
  57 ms on its own return); after one, 0 frames > 20 ms in 2 of 4 runs, one 25-27 ms frame at the cut in 2 (6-7 ms main-thread
  CPU, host load 11-30; the live page's return: 0). A hidden re-render of home under the page cleared that return but cost a
  34 ms frame of its own while the page was up — removed. The phone verdict belongs to D1b/PH-3.
- **Also fixed** (B1's week-start ribbon, surfaced by A3's popup hand-over): `WeekStartBanner.onDisappear` clears only its own
  event's announcement — on a Double Event Week the first offer's banner left the view tree after the second offer's ribbon was
  set and cleared it.
