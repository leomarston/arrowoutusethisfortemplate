# GAMEPROMPT: build a 1:1 copy of a mobile puzzle game, end to end, on your own

> **Who this is for.** A fresh Claude Code session in this repo (`/Users/yago/Downloads/app-factory`). The owner types one
> sentence, e.g. *"Read GAMEPROMPT.md and make Royal Match. ultracode ultrathink"*, and usually goes to sleep right after.
>
> **What you must deliver, on your own.**
> 1. Research: play the original on the owner's USB-connected iPhone, and do web research.
> 2. Measured specs.
> 3. All the art, sounds and music, made by us.
> 4. A native Swift build.
> 5. Side-by-side verification against the original.
> 6. The finished game installed on the phone.
>
> You orchestrate agents with the Workflow tool for many hours.
>
> **Where this comes from.** Two real runs in this repo:
> - **"Arrows – Puzzle Escape"** (`apps/arrows`, a 2D vector puzzle).
> - **"Match Factory!"** (`apps/matchfactory`, a 3D triple-match game: 126 procedural 3D items, 30 levels, boosters, economy,
>   full UI).
>
> Every rule below was paid for. §13 lists what already went wrong once.

---

## OWNER PRE-FLIGHT (for the owner, ~5 min, BEFORE typing the sentence)

The session can't click, unlock, install or approve anything once you leave. The agent checks these in its first minute and
lists whatever is missing in its first message.
1. **In the new chat:**
   - switch to **auto mode** (Shift+Tab until the footer says auto; it's per session);
   - include **"ultracode"** in the sentence (or set `/effort ultracode`) — that is your opt-in to multi-agent workflows;
   - add "ultrathink" if you want deeper reasoning.
2. **`/permissions` → Allow → Project (local).** Add these two rules once; they persist for every future game:
   `Bash(/Users/yago/Downloads/app-factory/tools/phonedriver/phone:*)`
   `Bash(/Users/yago/Downloads/app-factory/tools/phonedriver/start-runner:*)`
   Without them, the safety classifier blocks starting the phone runner ("Create Unsafe Agents") and talking to it ("Expose
   Local Services"). Approvals given inside one chat do not carry over.
3. **Phone:**
   - unlocked, USB-connected, Developer Mode on, Settings → Developer → **Enable UI Automation** on;
   - Auto-Lock **Never**;
   - Do Not Disturb on;
   - Portrait Orientation Lock on;
   - Settings → General → Software Update → Automatic Updates **off** (an overnight update reboots the phone locked).
4. **The original game:** installed. If you've played it before, **delete and reinstall it**, so level 1 and the first-time
   tutorials can be recorded. Open it once and leave it on its first screen.
5. **Mac:**
   - on the charger, **lid open**;
   - at least **15 GB** free on `/`;
   - close apps you don't need, especially old Claude sessions (they eat memory for the whole night).

Then type the sentence and leave.

---

## PRECEDENCE: this file overrides the repo defaults for this job (the owner's instruction)

The owner's words for these jobs: *"for this specific task dont focus on our rules in our repo. They come back to
consideration at a later point."* So, for a GAMEPROMPT job:

**Suspended.** Repeat this block in every workflow's COMMON preamble, because subagents also receive CLAUDE.md:
- CLAUDE.md's "HER ZAMAN `app-factory` skill'ini kullan" and its paywall / Restore-Purchases quality gates.
- `ideas.yaml`, `scripts/idea.py`, `scripts/new_app.sh`, RevenueCat, ASO, `scripts/asc_*.py`, fastlane, and App Store
  submission.
- Reading `PROJECT_LOG.md` (116 KB of subscription-app history), `docs/DESIGN.md` and `docs/ASO.md`. Append one line about this
  job to `PROJECT_LOG.md` in your final commit.
- These memories:
  - localize-top-13-locales (this job is EN + TR only);
  - distinctive-ui-not-slop (superseded by copycat-the-category: the identity to hit is the original's, measured);
  - support-mail-button;
  - no-clone-apps / the Guideline 4.3 screen (this is a local, unsubmitted copy the owner asked for; note any overlap in one
    line in the final report, never stop for it);
  - standard-price-3-99-17-99 and copyright-and-five-screenshots;
  - the ASO, keyword and ASC memories;
  - ipad-is-a-review-device (iPhone-only here);
  - the "build to submitted" goal in finish-the-whole-pipeline. Keep its "never stop to check in"; "done" is §14.
- "Takılırsan BLOCKED.md yaz ve dur" (if stuck, write BLOCKED.md and stop). A blocked sub-task goes into PLAN.md's BLOCKED
  line with its workaround, and you keep going. Only a machine-wide hard stop ends the run:
  - under 2 GB free after cleaning;
  - the Mac asleep;
  - the phone locked with no other work left;
  - the repo broken.

**Still binding:**
- memories one-app-per-task, commit-when-work-is-done, verify-real-not-mock, never-ship-stand-in-content and
  rejected-apps-hands-off;
- **account-and-no-browser**: web research uses WebSearch, WebFetch and curl, never the logged-in browser;
- the "no server" spirit: the game runs offline on the device;
- honest reports;
- never weakening a failing test;
- never spending real money.

**Workflows.** Your opt-in to multi-agent workflows is the owner's own "ultracode" (in the sentence or as the session
setting). If neither is present, say so in your first message and run the same roles as sequential subagents until the
owner turns it on.

---

## The owner's own words (verbatim — re-read them whenever you're unsure what "good" means)

**1. Arrows (the first game):**
> "We will be making a %100 copycat of the game called Arrow puzzle. I designed these images, and here i give to you (all the
> games use almost the same type so whatever) we will be making a mobile game, for this specific task dont focus on our rules
> in our repo. They come back to consideration at a later point. Right now we are only focusing on making the best game possible"
>
> "We have to analyze the games, read how these games work and %100 copy the system. Its not that hard to complete, but we have
> to make a %100 perfect copycat. We are using IOS, and you can use the simulator, and write the code in swift, We have to make
> the feeling the smoothest possbile. Lets go work really hard ultrathink ultracode. first plan and craeta a better propmt for
> yourself, Only make 5 starter levels so we know how to work (nothin online needed, only offline), lets go"

**2. Match Factory (the second game):**
> "okey remember this was my previous propmt for arrow game, now we will be making match factory from peak games, which is a
> much much bigger game, with more more graphics and details, so you will have to do real artwork and actually play the game and
> make a perfect 1:1 coypcat. very detailed work you should do, the effects the animations the art, the system. The only thing
> is, you dont have to make the online features. Make the perfect 1:1 Match factory game. It hsoudl be perfect and actually
> possible to copmete with it. ultrathink ultracode. also if it asks for a payment, ad watch etc. just reject it. lets go"

**3. About the phone:**
> "I will leave you with the phone … can you still control it after i open the game and leave … before that we have to make
> sure you can have all the controls."

**4. The request that created this file (it defines success for YOUR run):**
> "I need you to write a very detailed prompt to a GAMEPROMPT.md for me to use other chats to make the exact same way you made
> the games, they will have the phone connected and all the systems that you have here. But you must be mkaing such a good
> porpmtt that I should be able to just tell it read the GAMEPROMPT.md and make the app . and it should be making the same
> hardwork and same quality work just like you did and finish a perfect game on its own, ultracode will also be available for
> that chat and ultrathink i will add at the end of the prompt … This will focus on puzzle games just like you did, for eaxmple
> gmaes like royal match, or like arrow puzzles, or like jigsaw puzzles, etc. mostly puzzle games."

**5. What the owner said mid-run. Each one is a correction you must never need:**
> "what is the problem, why did you not do" *(after the Arrows build workflow crashed and nobody told them)*
> "okey no need to localise the arrows game for now, just stop it" *(after a 10-language pass nobody asked for)*
> "also let another agent run it on the simulator so I can actually see the game"
> "If I connect my iphone here … can you go to an app on it analyze it perfectly and make a perfect copycat of it, all its
> assets effects animations and everything"
> "Okey but by looking at the assets directly, cant you create a 1:1 asset on your own"

**What each phrase means in practice:**

| The owner said | What you do |
|---|---|
| "just tell it read the GAMEPROMPT.md and make the app", "finish a perfect game on its own" | The sentence is the whole brief. Decide everything else (exact app, scope, art route, levels) from this file and your research, and tag it DECISION. After your first message nothing may wait on the owner (§0, §4.1). "Finish" means installed on the phone, verified and committed (§14), not a plan, a spec or a promising start. |
| "same hardwork and same quality work just like you did" | Match Factory's depth is the floor: its research volume (§5), four specs plus the master SPEC (§6), graded art (§7), a build DAG with acceptance evidence (§8), side-by-side verification (§9). |
| "all the systems that you have here" | The tools are here. Session-scoped permission approvals are NOT; check the pre-flight rules in minute one (§4 step 4). |
| "%100 copycat", "perfect 1:1", "copy the system" | Copy rules, systems, layouts, timings, effects and sounds exactly, measured from the real game (§1, §5). |
| "analyze the games, read how these games work", "actually play the game" | Research first: hours of play on the phone, web research, frame-by-frame timings (§5). Nothing gets built from a guess that could have been recorded. |
| "I designed these images, and here i give to you" | Owner-provided screenshots go to `apps/<slug>/research/reference/`. They are primary references: measure them first. |
| "the feeling the smoothest possible" | 60 fps sustained, 120 Hz opt-in, animations on the render server or GPU, no main-thread work per frame during motion, input handled on the same frame, feel constants measured from the original's clips (§8, §13). |
| "first plan and create a better prompt for yourself" | `PLAN.md`, then four specs, then the master `SPEC.md`. That is the better prompt; every builder works from it (§6). |
| "Only make N starter levels so we know how to work" | An owner-set limit is the milestone. Finish it at full quality, report, and don't widen the scope. |
| "real artwork", "more graphics and details", "all its assets" | Real art from our pipelines, graded by an art director against reference crops (§7). Placeholders only bridge while art is in progress, and never ship. |
| "you dont have to make the online features" | Online features are not built; their entry points show honest locked or "not available" states (§6.3). |
| "possible to compete with it" | Fidelity plus polish plus performance on the real phone, compared side by side with the original (§9). |
| "if it asks for a payment, ad watch etc. just reject it" | During research, reject every purchase, rewarded ad, continue-for-coins and subscription; close interstitials; never log in. Never spend real money. Report any in-game currency spent by accident (§2.3). |
| "what is the problem, why did you not do" | Silence after a failure is itself a failure. The moment a workflow dies or stalls, or the machine degrades, tell the owner what died, what survived on disk and what you relaunched (§2.4). |
| "no need to localise … just stop it" | Never add scope. EN + the phone's language (TR) only; no extra locales, no store work. |
| "let another agent run it on the simulator so I can actually see the game" | When the owner is awake and a green build exists, offer a "Play" simulator that auto-installs the newest green build (`tools/gameprompt/snippets/play-watch.sh`). It copies the .app to a stage folder, because builders delete their products. It takes one of the two slots. |
| "create a 1:1 asset on your own" | Assets are judged 1:1 by eye at game size and rebuilt by us from measurements (§1.2, §7). Simple geometric UI can be pixel-exact; characters and logos get our own drawing in the same style. |
| "work really hard", "very detailed work", ultrathink, ultracode | Orchestrate many agents, measure everything, run adversarial reviews and fix loops, and never stop early. Match Factory used ~45 agents in 6 workflows over ~24 h. |
| "make sure you can have all the controls" | Kickoff (§4) proves every capability the night needs while the owner may still be there: runner, taps, the genre's core gesture, capture, recording, the headphones prompt. |

---

## 0. The first five minutes (the owner may already be walking away)

Everything that needs a human goes into your FIRST message, within about 3 minutes. **After that message you keep working in
the same turn.** Never end a turn waiting for an answer, and never end a turn with nothing running (§2.4).

1. **Probe** (≤ 2 min, one Bash call, before reading anything else):
   ```
   cd /Users/yago/Downloads/app-factory; git branch --show-current; git status --short | head -20; df -h / | tail -1;
   sysctl vm.swapusage; pgrep -fl xcodebuild | head; xcrun simctl list devices booted; xcrun devicectl list devices 2>&1 | grep -i iphone;
   grep -c phonedriver .claude/settings.local.json 2>/dev/null; ls /tmp/phonedriver.lock 2>/dev/null
   ```
   Then:
   - identify the original precisely (§4 step 0);
   - check `phone apps | grep -i <word>` (it needs no runner);
   - call ListAgents to see other live Claude sessions on this machine.

   Don't run `phone status` before the runner has been started: with nothing listening it can block for ~2 minutes.
2. **Send one message to the owner, then continue in the same turn.** It holds:
   - the game you identified: name, publisher, App Store id, and its bundle id on the phone (or "not installed");
   - the copying line in one sentence (§1.2);
   - "keep the lid open and the phone plugged in and unlocked";
   - ONLY the failed pre-flight items, one imperative line each (e.g. "add the two phone rules in /permissions";
     "delete and reinstall <game> so I can record the first-time experience"; "the phone is held by the <other> job — may I
     take it?"; "close old Claude sessions").
3. **Start** caffeinate, the watchdog (§2.4) and the phone runner as background Bash tasks, then run the rest of §4.
4. **Calibrate on the exemplars without flooding your context.** Your agents read full files; you read outlines:
   `cd apps/matchfactory; for f in PLAN.md SPEC.md research/levels.md research/motion.md design/SPEC-*.md design/tech-spike.md art/PIPELINE.md art/STYLE.md art/REVIEW.md; do echo "== $f ($(wc -l < $f) lines)"; grep -E '^#{1,3} ' "$f" | head -40; done`
   Then read ~60 lines from the middle of SPEC-gameplay.md, SPEC-motion-audio.md and REVIEW.md to see the density expected.
   Read **§10.0 and the §10 entry for this genre in full**: they change the art route, the engine, the spikes and the content
   model.
5. **Open these memories:**

   | Area | Memories |
   |---|---|
   | Machine and phone | max-two-parallel-builds, phone-driver, parallel-agents-and-simulators, disk-full-lies, disk-fills-fast-clean-archives |
   | Verification | verify-real-not-mock, never-ship-stand-in-content, audio-apps-must-assert-on-signal, screenshots-verify-content-not-count |
   | SwiftUI and plists | appstorage-in-observableobject, localizedstringkey-not-string, infoplist-array-keys-need-a-base-plist, reordered-args-need-positional |
   | Simulator and XCUITest | simctl-launch-args-gotcha, simulator-inherits-mac-region, xcuitest-predicates-must-anchor, xcuitest-hittable-lies, swiftui-container-identifier-swallows-children, swiftui-navigation-and-funnel-traps |
   | Art and content | svg-art-pipeline, fixture-photography, copycat-the-category |
   | Hygiene | one-app-per-task, commit-when-work-is-done |
6. **If the owner doesn't answer, decide; don't wait.** Re-check each missing item every ~20 min from your heartbeat, for up to
   60 min. Then take the fallback (§4.1) and keep going.

---

## 1. The mission, the quality bar, and the copying line

### 1.1 Quality bar ("done" means)
A daily player of the original picks up our build and **feels at home**: the same screens in the same places, the same timings
and bounce, the same sounds at the same moments, the same rules and difficulty curve, and art that reads as the same game at
arm's length. Measured against recordings of the original:

| What | Target |
|---|---|
| Layout | every screen and component within ±2 pt of the measured original |
| Colour | exact hex for flat fills; ΔE2000 ≤ 6 for rendered regions (both images converted to sRGB first) |
| Timing | every animation within ±1 frame at 60 fps, from frame-exact measurement; formulas T = f(distance) where the original uses them |
| Rules | Recorded levels: the AUTHORED content reproduced exactly (layout, blockers, goals, moves or timer, colour count, and the deal or fill when the restart diff shows it is fixed), proved with an overlay check. **Deterministic genres:** a solver proves every level. **Stochastic genres** (random refill or deal): our bot's win rate over ≥ 200 seeds sits in the level's band, calibrated by running the same bot on the recorded levels. **Endless modes:** the generator's measured statistics match the original's within sampling error. **Jigsaw:** the cutter validator passes for every image × piece count. |
| Feel | 60 fps sustained on the owner's iPhone 15 (a **60 Hz** panel: iPhone15,4, no ProMotion); no hitch over 50 ms during play; input handled on the next frame. Opt in to 120 Hz for ProMotion devices, but neither this phone nor the Simulator can verify it: report 120 Hz as UNVERIFIED, never as passed. |
| Art | every shipped asset graded by the art director against reference crops: ≥ 50 % A, no C, 0 proxies in shipped levels |

### 1.2 The copying line (non-negotiable; tell the owner in one line at kickoff)
- **Copy 1:1:** look, feel, rules, systems, timings, layouts, flows, difficulty. Game mechanics and layouts are not protected.
- **Every asset is ours:**
  - our procedural 3D models;
  - 2D art we draw (SVG or code);
  - sounds and music we synthesise;
  - OFL or Apache fonts matched by rendering.
- **Never:**
  - extract, rip, decrypt, trace, resample or reuse the original's files, audio or images;
  - use recordings of the original as inputs to our assets. They are references to *look at* only. Nothing in
    `App/Resources` derives from `research/sound-refs`, `research/video` or `research/shots`.
- **Brand:**
  - the name, logo, monogram, mascots and distinctive characters belong to the original;
  - in dev builds the name sits behind one `Brand` constant with a working title;
  - mascots and characters get **our own design** in the same style;
  - asset, font and module file names use a neutral code prefix, never the brand's initials;
  - tell the owner the name and logo must change before any submission.
- **Authored content** (photos, word lists, nonogram pictures, illustrations): only CC0, public domain or permissively licensed
  sources, with a licence record per item (§7.2). Never the original's content.

---

## 2. How you work: autonomy, orchestration, staying alive, honesty

### 2.1 Autonomy
- **Never stop at a phase boundary to check in.** Chain workflow → review → next workflow until §14 is complete.
- **Make decisions** when evidence is missing:
  1. choose the option most faithful to the captures;
  2. tag it `DECISION` with its reason;
  3. carry on;
  4. collect the open questions for the final report.

  Ask the owner only for physical things, batched into the first message.
- **Status.**
  - Send a short message at each phase transition: what finished, what is running, what is next.
  - Every time, update `PLAN.md`: its NOW block (§2.4) and a timestamped line in the status log.
  - While a phone agent is running, never use PushNotification or anything else that notifies the owner's devices. The
    banner can land on this very iPhone, swallow a tap and ruin captures.
- **Plan against this timeline** (Match Factory's real clock; scale it to the game's size). A phase running past 1.5× its slot
  is a signal to look at it (§2.4), not to keep waiting:

  | Clock | Phase |
  |---|---|
  | 0:00–0:30 | §0 probes, first message, kickoff, agent smoke test (§4) |
  | 0:30–5:00 | W-phone (player → analyst ∥ meta explorer) ∥ W-desk (web, fonts, art spike, tech spike) |
  | ~2:00 | art pipeline upgrade and UI tokens, as soon as W-desk ends |
  | 5:00–6:30 | four specs + consistency pass → master SPEC.md; the phone continues with session 2 |
  | 6:30–18:00 | build DAG ∥ art rounds 1–2 ∥ UI art ∥ audio. The build is the long pole: start it the minute the specs are reconciled |
  | 18:00–24:00 | V1/V2/V3, ≤ 3 fix rounds, D1 on the phone, finish |

### 2.2 Orchestration (you are the conductor)
You own the plan, the phase transitions, spec reconciliation, commits, cross-owner fixes and the owner dialogue. Agents own
the work.
- **Separate workflows for work of different lengths.** A workflow notifies you only when *all* of it ends. Never put a 2-hour
  phone session in the same workflow as a 30-minute spec pass you need to act on (§5.1 splits research into W-phone and
  W-desk).
- **Disjoint file ownership.** Each agent gets a list of files it may edit; a shared file has exactly one owner at a time.
  Cross-owner requests go into the agent's report, and you apply or schedule them.
- **Contracts first.** A lead writes the project, stubs and frozen API contracts (WP0) before the parallel builders start.
- **Chain reports.** Each agent's structured result (summary, open issues, requests) goes into the prompt of the agent that
  depends on it.
- **Adversarial review everywhere.** An art director reviews every lane, a verifier compares captures side by side, and
  reviewers fix the worst problems themselves. Run a consistency pass over the specs (§6.2).
- **You look at the evidence yourself.** After each phase, open 2–4 key comparison images (e.g. our board next to the
  original's shot) and judge them. Never announce quality you haven't seen.

### 2.3 Honesty
- Report exactly what happened, including accidents. In Match Factory a batched tap spent the game's 100 in-game coins on a
  "clear shelf" button, and it was reported. **Never spend real money.**
- "Done" means acceptance checks passed, with evidence paths. "Partial" and "blocked" are fine; fake success is not.
- Never claim "no network". Say what actually uses the network (e.g. StoreKit).

### 2.4 Staying alive for ~24 h (Claude Code mechanics)
- **A turn that ends with nothing running ends the night.** You are re-invoked only when a background task or a workflow
  finishes. Before you end ANY turn, make sure a workflow or a background Bash task is running, e.g. the watchdog below or a
  heartbeat `sleep 1800; echo heartbeat` with `run_in_background`. Re-arm it every time it fires.
- **Watchdog** (start it at kickoff with `run_in_background`; it exits on an alarm, which wakes you; restart it after you
  handle the alarm):
  ```sh
  # apps/<slug>/tools/watchdog.sh
  A=/Users/yago/Downloads/app-factory/apps/<slug>; idle=0; touch /tmp/<slug>-wd; mkdir -p $A/build
  while :; do
    free=$(df -g / | awk 'NR==2{print $4}')
    echo "$(date +%H:%M) disk ${free}G $(sysctl vm.swapusage | cut -c1-70)" >> $A/build/health.log
    if [ -n "$(find $A -newer /tmp/<slug>-wd -type f ! -name health.log 2>/dev/null | head -1)" ]; then idle=0; else idle=$((idle+5)); fi
    touch /tmp/<slug>-wd
    [ "$free" -lt 4 ] && { echo "ALARM disk ${free} GB"; exit 1; }
    pgrep -q caffeinate || { echo "ALARM caffeinate ended"; exit 1; }
    [ -f /tmp/phonedriver.lock/owner ] && grep -q "<slug>" /tmp/phonedriver.lock/owner && \
      ! /Users/yago/Downloads/app-factory/tools/phonedriver/phone status >/dev/null 2>&1 && { echo "ALARM phone runner down"; exit 1; }
    [ $idle -ge 45 ] && { echo "ALARM nothing written for 45 min (stall?)"; exit 1; }
    sleep 300
  done
  ```
- **On every wake-up** (heartbeat, alarm, workflow notification):
  - read the running workflow's journal for new `result` lines (§11), and those reports' `requests_for_others` and
    `open_issues`;
  - check disk and swap;
  - restart caffeinate or the runner if either is dead (a runner restart often needs 2 tries);
  - apply one-line cross-owner fixes and log them.
  If a phone agent's progress file hasn't changed for 30 min, or a workflow has written nothing for 45 min, investigate:
  stop it with `TaskStop` and resume it (§11). Match Factory's meta explorer once stalled for 86 min unseen.
- **Usage limits happen.** One paused a Match Factory workflow for ~1.5 h. Workflows resume on their own; your heartbeat makes
  you resume too. Log the gap.
- **Compaction will happen several times.** Keep this block at the top of `PLAN.md` and rewrite it at every transition:
  ```
  ## NOW (updated HH:MM)
  RUNNING: <workflow / task id / run id / started / produces / holds slot A|B|phone>
  NEXT:    <exact next action and its trigger>
  TODO:    <every promised follow-up, e.g. "recast L14-19 from art/ID-MAP.md", "D1 on the phone">
  BLOCKED: <item: workaround; owner action needed>
  DECISIONS: <pointer to the decisions list>
  ```
  After any compaction, restart or long wait, re-read `GAMEPROMPT.md` §0–§2 and PLAN.md's NOW block before acting.
- **When something dies, tell the owner in that same turn**: what died, what survived on disk, what you relaunched.

---

## 3. The machine, the phone and the tools (verified inventory)

### 3.1 Machine
- **Hardware:** MacBook, **16 GB RAM, 8 cores**. Swap routinely sits at 11–14 GB, because the owner runs VS Code, Brave and
  several Claude sessions. **Swap files live on the boot disk.**
- **Xcode:** 26.0.1 (17A400). The only simulator runtime is iOS 26.0 (`com.apple.CoreSimulator.SimRuntime.iOS-26-0`); the
  phone runs iOS 26.6.1.
- **xcodegen:** `/Users/yago/.local/bin/xcodegen` is a wrapper for `/opt/homebrew/bin/xcodegen`. Homebrew exists at
  `/opt/homebrew/bin/brew` but is not on PATH; don't install packages unattended.
- **Not installed:** ffmpeg, ffprobe, sox, Blender. Use `mfx audio` (§3.5), `afconvert`, `afinfo` and AVFoundation instead.
- **Python:**
  - `python3` is python.org 3.14, with numpy, Pillow and **fontTools**;
  - `/usr/bin/python3` is Apple's 3.9;
  - the 3D venv `~/.venvs/mf3d` (numpy, scipy, scikit-image, trimesh, fast-simplification, usd-core/pxr) has no fontTools.
- **Keep the Mac awake:** start `caffeinate -dimsu -t 172800` (48 h) as a background Bash task at kickoff. A 12 h timer ran
  out mid-run once. The owner keeps the lid open.
- **Bash tool timeout:** 120 s by default, max 600 s. Pass `timeout: 300000`–`600000` for xcodebuild, xcodegen and test runs,
  or run them with `run_in_background` and poll the log. An overrunning command moves to the background, and its output must
  then be read from the task file.

### 3.2 The owner's iPhone and `tools/phonedriver`
**Device.** iPhone 15 "Ozcan'in iPhone'u" (iPhone15,4): 393×852 pt @3x, **60 Hz**, iOS 26.6.1.
- CoreDevice id `878DB538-F187-596F-B24B-EAF8853617DE`, UDID `00008120-000964E426440032`.
- Re-check with `xcrun devicectl list devices`. `PHONE_DEVICE` (CoreDevice id) and `PHONE_UDID` override the ids in the
  tools.

**Control CLI.** Always invoke it by its absolute path: `/Users/yago/Downloads/app-factory/tools/phonedriver/phone`. The
allow rule matches the literal command, so not `phone`, `./phone` or `$P`. Put that sentence in every phone agent's prompt.
```
phone status                          runner alive? → {"ok": true, "app": "<bundle it last activated>"}
phone shot [OUT.png]                  screenshot via the runner, 1178x2556 px, lossless sRGB (use for COLOURS)
phone tap X Y | doubletap X Y | press X Y [SECONDS=0.8] | swipe X1 Y1 X2 Y2 [SECONDS=0.25]
phone activate BUNDLE                 bring to front (launches if needed): use this to get back into a game
phone launch BUNDLE                   TERMINATE + fresh launch: mid-level this usually counts as a loss and costs a life
phone terminate BUNDLE | home | stop  (stop ends the runner)
phone source BUNDLE                   accessibility tree (native apps; empty for Unity/Flutter games)
phone apps                            installed apps + bundle ids (no runner needed)
phone grab OUT.png                    full-res frame via USB screen capture, 1180x2556 (no runner needed)
phone rec OUT.mov SECONDS             variable-frame-rate video (≤ 60 fps, 1180x2556) + AAC 48 kHz audio; blocks ~SECONDS+2 s
phone frames IN.mov OUTDIR FPS [START END]   fixed-grid frames named f<ms>.png (use mfx for exact timing, §3.5)
```
- **Coordinates are in points.**
  - pt = px × 393 / width: 1178 px for runner shots, 1180 px for grabs. Never mix the two sources in one measurement.
  - To look cheaply, downscale a shot to exactly 393×852 with PIL (then pixel = point) and Read that.
  - Use full resolution only for crops and measurement.
- **The runner** is an XCUITest HTTP server on :8100 over the CoreDevice USB tunnel.
  - Start it as a background Bash task:
    `/Users/yago/Downloads/app-factory/tools/phonedriver/start-runner > /tmp/phonedriver-runner.log 2>&1`, then wait ~40 s.
  - It dies when the phone disconnects or the test session ends. The first restart after a death often fails with "Timed
    out while enabling automation mode"; wait 30 s and start it again.
  - `phone` refreshes the tunnel IP by itself.
  - Gestures go through SpringBoard coordinates, so an animating game never blocks on "wait for idle".
- **Recording while acting:** act only once recording has really begun. Device discovery takes up to 10 s plus 1 s of settle;
  a fixed `sleep 1.5` missed the start. Poll the log instead:
  ```sh
  P=/Users/yago/Downloads/app-factory/tools/phonedriver/phone; O=/Users/yago/Downloads/app-factory/apps/<slug>/research/video/x.mov
  rm -f $O $O.log; ($P rec $O 10 >/dev/null 2>&1 &); for i in $(seq 1 60); do grep -q RECORDING $O.log 2>/dev/null && break; sleep 0.25; done
  $P tap X Y; sleep 9; tail -1 $O.log
  ```
  - Never run `grab` or a second `rec` while a `rec` is running: `open -W` reuses the running PhoneCapture and drops the new
    arguments ("no log").
  - macOS has no `timeout`. Wrap anything that can hang: `perl -e 'alarm shift; exec @ARGV' 40 <command>`. After a timeout,
    run `pkill -f PhoneCapture`.
- **PhoneCapture** (the helper behind `grab` and `rec`) is `tools/phonedriver/capture/build/PhoneCapture.app`.
  - macOS treats the iPhone screen as a camera, so the app holds a **camera permission** the owner granted.
  - Rebuilding it (`capture/build.sh`) changes its signature and asks again. **Never rebuild it unattended.** `build.sh
    frames-only` rebuilds just the extractor.
  - **Never `git clean -x/-X`.** PhoneCapture.app and the signed runner (`tools/phonedriver/build/DD`) are gitignored.
- **Gesture gaps.** The runner can tap, double-tap, press, and swipe between 2 points (press 0.05 s, straight drag, hold
  0.05 s, lift). That covers taps, swaps, flings and drag-and-drop. It **cannot**:
  - do a continuous multi-point path (word wheels, draw-a-line, bent strokes);
  - pinch or rotate (jigsaw and big-board zoom);
  - hold while you take a screenshot (for aim lines, record video during a slow swipe instead).

  If the genre needs one of these, **extend the runner at kickoff** while the owner may still be there:
  - `/pinch?scale=&v=` and `/rotate?r=&v=` via `XCUIApplication(bundleIdentifier:).pinch(withScale:velocity:)` and
    `.rotate(_:withVelocity:)`. These act at the app's centre.
  - `/drag?x1=&y1=&x2=&y2=&d=&hold=` via `press(forDuration:thenDragTo:withVelocity:thenHoldForDuration:)`.
  - `/path?pts=x1,y1;x2,y2;...&d=` needs the private event-synthesis classes WebDriverAgent uses (`XCPointerEventPath` +
    `XCSynthesizedEventRecord`), declared in an Objective-C bridging header in `tools/phonedriver/UITests/`. Take the
    signatures from WebDriverAgent's PrivateHeaders with WebFetch. This is test-runner code; it never ships.

  Then:
  1. Add the verbs to `phone` and its `--help`.
  2. `rm -rf tools/phonedriver/build/DD/Build/Products`, then restart the runner. This rebuilds only the runner, not
     PhoneCapture, so there is no camera prompt.
  3. Prove the gesture on the original (spell one word, zoom once) and LOOK at the shot.
  4. Commit it as its own `tools/phonedriver:` commit, keeping the existing endpoints unchanged.

  If `/path` still fails after ~45 min, ask the owner for 3–5 minutes of their own screen recording (Control Centre, mic on),
  and note in PLAN.md that the phone could not play the genre.
- **Phone quirks:**
  - **Headphones prompt.** Starting an audio capture makes iOS ask "Bir kulaklık mı bağlıyorsunuz?" (connecting headphones?).
    Tap "Diğer Aygıt" (Other Device): `phone tap 122 494`. Do it once at kickoff.
  - **Variable frame rate.** Recordings write a frame only when the screen changes, so a nominal 40–54 fps is **normal**
    (Match Factory clips report 40.0–54.1). Long clips also drop stretches (one skipped ~3 s), so keep timing clips
    **≤ 12 s**. Audio is complete but lags video by 0.03–0.3 s: fire sounds on their visual event. Never "fix" a low nominal
    fps by rebuilding PhoneCapture.
  - **Turkish UI.** Record the Turkish text AND an English translation. English strings: §5.3.
- **One phone for all sessions.** Before any phone work, take an atomic lock, and pass it between your own agents ("you have
  EXCLUSIVE use"):
  `mkdir /tmp/phonedriver.lock 2>/dev/null && echo "<slug> <role> $(date +%H:%M)" > /tmp/phonedriver.lock/owner`
  - If the lock exists and isn't yours, don't touch the phone. The same goes for a runner you didn't start
    (`pgrep -fl PhoneDriver`). Check ListAgents, ask in your first message, and do desk work meanwhile.
  - A lock older than 3 h with no phone activity is stale: take it and log that you did.
  - Remove the lock after your last phone use, D1 included.

### 3.3 Simulators, signing, build tools
- **Simulators.** Create dedicated ones:
  `xcrun simctl create "<Game> A" com.apple.CoreSimulator.SimDeviceType.iPhone-16 com.apple.CoreSimulator.SimRuntime.iOS-26-0`
  - Make "<Game> A", "<Game> B" and, if needed, "<Game> Spike". The iPhone 16 is 393×852, the same as the phone and all the
    captures.
  - Never share a simulator between agents.
  - Shut simulators down after each package.
  - **Only ever shut down or erase UDIDs you created, orchestrator included.** A `simctl shutdown all` during cleanup once
    killed another session's simulator.
  - Stop each simulator's ~1 GB background asset downloads, on YOUR simulators only:
    `chmod 000 ~/Library/Developer/CoreSimulator/Devices/<UDID>/data/Library/Caches/com.apple.nsurlsessiond` (restore with
    755 before erasing).
- **Project.** xcodegen `project.yml` (models: `apps/matchfactory/project.yml`, `apps/arrows/project.yml`).
  - Array keys (`UIAppFonts`) and `CADisableMinimumFrameDurationOnPhone` need a **base Info.plist**; `INFOPLIST_KEY_*`
    silently drops them.
  - A new `.metal` file needs `xcodegen generate` again, or `CustomMaterial` silently falls back.
  - Two agents running xcodegen at once corrupt the project: use a `mkdir build/.gen.lock` mutex (MF `tools/gen.sh`).
- **Signing** for the phone:
  - team `GDU77F3MXL`; `.env` has `TEAM_ID`, `BUNDLE_PREFIX` (com.manycode), `ASC_KEY_ID`, `ASC_ISSUER_ID` and a **relative**
    `ASC_KEY_PATH`;
  - xcodebuild needs an **absolute** `-authenticationKeyPath`;
  - use `-allowProvisioningUpdates -allowProvisioningDeviceRegistration`;
  - the first device build may fail with "provisioning profile … cannot be found": it's a race, so retry once.
  - `tools/phonedriver/start-runner` is a working example.
- **Launching on a simulator.**
  - `simctl launch --stdout/--stderr` into `~/Downloads/…` is denied by the host sandbox, and every launch then fails ("denied
    by service delegate"). Write logs into the simulator's `data/tmp` and symlink them (MF `tools/run.sh`).
  - Always pass `--terminate-running-process`: arguments are dropped while the app is running.

### 3.4 Machine limits (hard rules; each was learned by crashing)
- **Two slots per MACHINE, not per session.** At most TWO agents compiling an app or running a simulator at once, counting
  other sessions. Five parallel builds plus three simulators once pushed swap to 17 GB; every agent "stalled", the workflow
  died and the disk filled.
  - Before each build phase: `xcrun simctl list devices booted; pgrep -fl xcodebuild | grep -v PhoneDriver; sysctl vm.swapusage`.
  - If other sessions hold slots, run the no-simulator phases first.
  - Non-compiling agents (research, Python art, specs, `swift test` on a small package) can run alongside. The Workflow cap
    is 6 concurrent agents per workflow, and several workflows add up.
- **Per agent:**
  - one xcodebuild at a time with `-jobs 4 -quiet`; `swift build -j 2`;
  - Python multiprocessing with **spawn**, never fork (fork deadlocks numpy on macOS), and ≤ 2 workers per lane;
  - commands under ~4 min, with explicit Bash timeouts (§3.1);
  - before a build, check `sysctl vm.swapusage` and `memory_pressure -Q`. If free swap is < 400 MB or pressure is critical,
    wait in 2-minute steps.
- **Disk.** It was the #1 obstacle in Match Factory: free space fell to 295 MB mid-build.
  - **Budget per game:**
    - research ≈ 4 GB (3 GB of it video);
    - `build/` ≈ 2–3 GB;
    - each simulator 1.5–3 GB;
    - art previews ≈ 0.3 GB;
    - SwiftPM `.build` ≈ 0.2 GB.

    **Start with ≥ 15 GB free.**
  - `~/Library/Developer/Xcode/DerivedData` is usually tiny here (builds go to `apps/<slug>/build/dd-*`). The real space is in:
    - `~/Library/Developer/CoreSimulator/Devices`;
    - other apps' `apps/*/build/` (gitignored and regenerable);
    - Xcode Preview simulators (`xcrun simctl --set previews delete all`; 8 GB once);
    - `~/Library/Developer/Xcode/Archives`;
    - `xcrun simctl delete unavailable`.
  - **Deleting another app's simulators, research or build folders needs the owner's OK.** Ask in the kickoff message, then do
    it yourself; the classifier denied an agent's `simctl erase`.
  - At kickoff, also list the memory hogs (`ps -axo rss,comm | sort -nr | head -12`) and ask the owner to close what they can.
    Never kill another session or app.
  - `df -h /` before every heavy step; below 3 GB, stop heavy work and clean your own files first.
- **Heavy research is gitignored from day one** (§4 step 2). Before every commit, check what would go in:
  `git add -n -- apps/<slug> | sed "s/^add '//;s/'$//" | xargs du -sh 2>/dev/null | sort -h | tail -5`
  Nothing over 5 MB goes in unless it is a shipped asset.

### 3.5 Tools you reuse (copy and adapt; don't rewrite)
These are committed on `build/matchfactory` (commits 319a63e, 2505087 and 05424db), plus `apps/arrows` and
`tools/gameprompt/snippets/`.
- **3D art pipeline**
  - Location: `apps/matchfactory/art/pipeline/`. Read `art/PIPELINE.md`.
  - What it is:
    - `sdf.py`: SDF modelling;
    - `mesher.py`: marching cubes, buried-surface cull, budgeted decimation, closed outline shells, grouped stable poses;
    - `usdwriter.py`: USDZ with UsdPreviewSurface;
    - `palette.py`: calibrated material families;
    - `build.py`, `preview.py`, `closeup.py`, `review.py`, `calib.py`;
    - `render/`: `mfrender`, an offscreen RealityKit renderer.
  - Copy it WITHOUT Match Factory's ~126 item recipes:
    `mkdir -p apps/<slug>/art/pipeline/items && cp apps/matchfactory/art/pipeline/{sdf,mesher,usdwriter,palette,build,preview,closeup,review,calib}.py apps/<slug>/art/pipeline/ && cp -r apps/matchfactory/art/pipeline/render apps/<slug>/art/pipeline/ && cp apps/matchfactory/art/pipeline/items/{__init__,_calib,_materials}.py apps/<slug>/art/pipeline/items/`
    Keep 2–3 MF recipes (e.g. `toy_hammer.py`, `rubber_duck.py`) outside `items/` as format examples.
  - Then:
    - `sh apps/<slug>/art/pipeline/render/build.sh` builds `apps/<slug>/build/art/mfrender`;
    - rewrite `review.py`'s level→shot map and `CAPTURE_CASTS`, `preview.py`'s `RIG_CFG`, and palette.py's MF item
      materials;
    - regenerate `art/rig/` from your captures (`preview.py --rig`) and write a new STYLE.md.
- **UI raster art**
  - Tools: `apps/matchfactory/art/ui/tools/`:
    - `svgr.swift` + `svg.py`: exact w×h @3x, 2× supersampled;
    - `sheets.py`: side-by-side against the reference crop;
    - `check.py`: present, RGBA, whole-pt sizes, no clipping.
  - Don't use `scripts/svg2png.swift`: it renders one square size at the screen's scale.
  - UI 3D props go in `art/ui/recipes/`, never in `art/pipeline/items/` (`build.py --all` would turn them into board items).
- **Motion and sound analysis:** `apps/matchfactory/research/motion-tools/`. Copy it and build `mfx` with
  `swiftc -O -o mfx mfx.swift` (a macOS CLI).
  - `mfx info IN.mov`.
  - `mfx frames IN.mov OUTDIR FPS START END WIDTH [x y w h]`: real presentation timestamps, crop in pt.
  - `mfx raw …`: a numpy dump for `mf.py`.
  - `mfx audio IN.mov OUT.wav [START END]`: the only audio extractor on this Mac.
  - `mf.py`: set `V` and `MFX` to your paths.
  - `taps.py`: tap and flash onsets.
  - `evavg.py` / `spec.py` / `excess.py`: event-locked median spectrograms, which cancel the music.
  - `ov.py`: clip overview sheets.
- **OCR:** `apps/matchfactory/tools/bench/hudocr.swift` (Vision `VNRecognizeTextRequest`), for HUD numbers, word wheels,
  sudoku givens and nonogram clues.
- **Fidelity:** `apps/matchfactory/tools/compare/{compare_all.py,side_by_side.py,regions.json}` (CIEDE2000 per region, plus a
  side-by-side sheet).
- **Performance:** `apps/matchfactory/tools/bench/{bench.py,bench.sh}`.
- **Audio:** `apps/matchfactory/tools/audio/{dsp,instruments,sfx,music}.py` for synthesis, and `check.py` + `check_selftest.py`
  for signal checks that are themselves mutation-tested.
- **Build scripts:** `apps/matchfactory/tools/{slot,gen,build,run,test}.sh` and `tools/strings/` (TSV → strings + coverage).
- **Content:**
  - `apps/matchfactory/design/tools/gen_levels.py`: levels.json generator and validator;
  - `apps/arrows/design/tools/extract_levels.py`: board extraction from shots with an IoU overlay proof;
  - `apps/arrows/design/tools/solve_levels.py`: a greedy solver.
- **Swift patterns** (starting points, not dependencies):
  - `Packages/MFCore/Sources/MFCore/Random/MFRandom.swift`: xoshiro256** with named `fork` streams;
  - `Session/HeadlessDriver.swift`: a bot over the real core;
  - `Economy/`, `Persistence/`, `Motion/Curves.swift`;
  - `App/Shell/{Components,Popups}`, `App/Audio`, `App/Support` (launch args, probe).
  - For line puzzles: `apps/arrows/App` (Core Animation board).
- **Snippets** (`tools/gameprompt/snippets/`):
  - `iso-build-copy.sh`: build a scratch copy while others edit;
  - `wait-build.sh`: wait for file quiet and memory;
  - `capture-shot.sh`: ready-file capture plus sRGB;
  - `rng_ref.py`: an independent RNG reference;
  - `play-watch.sh`: a Play simulator for the owner.
- **Fonts:**
  - Google Fonts OFL, matched by rendering candidates against measured crops with IoU scoring (models:
    `apps/arrows/design/fonts.md`, matchfactory SPEC-ui).
  - Add missing glyphs (Turkish İ/Ğ/Ş) with fontTools in system `python3`, and rename the font as the OFL's reserved-name
    clause requires.
  - Give the font a neutral file name, not the brand's initials.

If an exemplar is missing when you start, don't stop: use its description here and write the tool again. Write
`design/REUSE.md`: what you copied, from which commit (`git log -1 -- <path>`), and what you changed.

---

## 4. Phase 0: kickoff checklist

Collect everything that needs the owner into your first message (§0). Everything else runs without them.

0. **Identify the original precisely (don't ask).**
   - Search: `curl -s 'https://itunes.apple.com/search?term=<words>&entity=software&country=us&limit=10'`, and again with
     `country=tr`. Use curl: Python urllib fails on Apple endpoints with CERTIFICATE_VERIFY_FAILED.
   - Pick the app whose name and publisher match. If the owner named only a genre ("a jigsaw game"), pick the category leader
     by `userRatingCount` for the head term, and tag it DECISION.
   - Look it up: `curl -s 'https://itunes.apple.com/lookup?id=<trackId>&country=us'` gives the bundleId, version, releaseNotes
     and **screenshotUrls**.
   - Save the screenshots at full size to `research/store/`: swap `…/392x696bb.png` → `…/900x1600bb.png` (icon: `512x512bb` →
     `1024x1024bb`). They are the spikes' first references while the phone player is still playing.
   - Cross-check with `phone apps | grep -i <word>`: the bundle id must match. Record the original's version, bundle id, the
     date and the phone's language in PLAN.md; every VERIFIED fact is verified for that version only.
   - **Names** (decide once, write them in PLAN.md):
     - `<slug>`: lowercase letters and digits only (`royalmatch`);
     - bundle id `com.manycode.<slug>`;
     - scheme and target in UpperCamelCase;
     - a core package with a neutral prefix (not the brand's initials);
     - a launch-argument prefix `-<xx>.` (MF used `-mf.`);
     - simulators "<Game> A" and "<Game> B";
     - branch `build/<slug>`;
     - a `Brand` working title (the original's name, for dev builds only).
1. **Branch, safely.** This working tree is shared with other Claude sessions.
   - Everything this file cites exists only on `build/matchfactory` (and `build/arrows`), **not on `main`** (main has only the
     4 initial factory commits). Branch from the CURRENT HEAD when it is `build/matchfactory` or a later GAMEPROMPT branch.
   - Never run `git checkout main`, `git stash -u`, `git clean` or `git reset --hard`: they delete untracked or ignored tools.
   - **Another session is live in this tree** (ListAgents, booted simulators of another app, recent writes under `apps/`):
     don't switch branches, because that moves HEAD under it. Commit onto your branch without touching HEAD or the shared
     index:
     ```sh
     B=build/<slug>; IDX=/tmp/idx-<slug>; rm -f $IDX; git show-ref -q refs/heads/$B || git branch $B HEAD
     GIT_INDEX_FILE=$IDX git read-tree $B; GIT_INDEX_FILE=$IDX git add -A apps/<slug>; T=$(GIT_INDEX_FILE=$IDX git write-tree)
     C=$(git commit-tree $T -p $B -F /tmp/msg-<slug>.txt); git update-ref refs/heads/$B $C; rm -f $IDX
     ```
   - **No other session:** `git switch -c build/<slug>`.
   - Either way, stage only `apps/<slug>/`. Tool changes (`tools/phonedriver`, `tools/gameprompt`) go in separate, labelled
     commits.
2. **Folders.**
   - Create `apps/<slug>/{research/{shots,video,items,store,kickoff,reference},design,art}`.
   - Create `apps/<slug>/.gitignore` with:
     `research/video/`, `research/shots/`, `research/motion-frames/`, `research/sound-refs/`, `research/items/`,
     `research/web/`, `research/kickoff/*.mov`, `research/motion-tools/w/`, `research/motion-tools/mfx`, `art/previews/`,
     `art/ref/`, `art/ui/sheets/`, `art/rig/*.png.tmp`, `art/pipeline/**/__pycache__/`, `build/`, `*.xcodeproj`,
     `Packages/*/.build/`, `.swiftpm/`, `__pycache__/`.
   - Captures of the original stay out of git.
3. **Genre routing.**
   - Classify the game with §10.0.
   - Paste its §10 entry verbatim into PLAN.md under "Genre playbook", with your adaptations. Every workflow's COMMON includes
     that block.
   - Put the genre's owner needs in the first message: e.g. word games need the in-game language set to English; full lives
     or energy if possible.
4. **Stay awake; permissions; rehearsal.**
   - Start caffeinate and the watchdog (§2.4, §3.1).
   - Check that `.claude/settings.local.json` holds the two phone rules from the pre-flight. If they're missing, the first
     message asks the owner to add them. Only on an explicit "yes, add them" may you add exactly those two rules yourself,
     with the `update-config` skill. Never ask for broader rules.
   - Take the phone lock (§3.2), start the runner, then `phone status`.
   - **Agent smoke test.** You running a command proves nothing about your agents. Launch a one-agent workflow whose agent
     runs each of these and reports each as ok or denied:
     - `phone status`, `phone shot <ROOT>/research/kickoff/smoke.png`, `phone grab <ROOT>/research/kickoff/smoke-grab.png`,
       `phone rec <ROOT>/research/kickoff/smoke.mov 3`;
     - a WebFetch of the App Store page;
     - `curl -sLo` of one Google Fonts TTF;
     - `~/.venvs/mf3d/bin/python -c 'import skimage, trimesh; from pxr import Usd'`;
     - `xcrun simctl list devices`.
     This also proves the Workflow tool is available. Paste the report into PLAN.md. A denied phone command → the owner action
     in your first message, and the fallback (§4.1) until it's fixed.
   - **Prove the genre's core gesture on the original** (swap, group tap, drag with lift, path, pinch: from its §10 entry).
     A gesture found missing at 2 a.m. has no fix (§3.2).
   - If the classifier denies a long `;`-chained phone one-liner, move the sequence into a small script under
     `apps/<slug>/research/tools/` and run that.
5. **The first-time experience (FTUE) is one-shot.** A never-opened game plays its splash, intro, consent/ATT prompts and
   first tutorial exactly once, and only the owner can reinstall it.
   - Open the game ONLY with a recording running, and touch nothing inside it: start
     `rec research/video/F00-first-launch.mov 12` with the log-poll recipe (§3.2), then `phone activate <bundle>`.
   - Dismiss only iOS system prompts (headphones → "Other Device"). Then `phone shot research/kickoff/state.png`.
   - If it's a first launch, leave it there: the player's first action continues the FTUE with back-to-back ≤ 12 s clips and
     a shot every ~3 s until the first playable board.
   - If the game is past level 1, ask in the first message for a delete + reinstall, and continue either way (§4.1).
   - Then capture a level board: `phone grab research/kickoff/board.png` (the log must say `SAVED 1180 x 2556`; if macOS asks
     for camera access for "Phone Capture", that needs the owner). Record `research/video/test.mov` for 6 s, then
     `phone frames … research/video/test-frames 2` (the templates' spikes read that folder).
   - `afinfo` must show AAC 48 kHz.
6. **Resources.**
   - `df -h /` ≥ 15 GB, or list the candidates with sizes and ask (§3.4).
   - Create your simulators and chmod their nsurlsessiond caches.
   - Check the venv: `~/.venvs/mf3d/bin/python -c "import skimage, trimesh, fast_simplification; from pxr import Usd"`.
     If it's broken: `python3 -m venv ~/.venvs/mf3d && ~/.venvs/mf3d/bin/pip install numpy pillow scipy scikit-image trimesh fast-simplification usd-core`.
7. **PLAN.md.**
   - The NOW block (§2.4).
   - The owner's sentence, verbatim.
   - The copying line.
   - The names and resources: phone ids, bundle id, the original's version, simulator UDIDs, the venv.
   - The machine limits.
   - The genre playbook.
   - The timeline.
   - The status log.

### 4.1 If the owner is already gone (the normal case)
Never block on an answer. Start everything that doesn't need one, re-check the blocked item from your heartbeat, and at the
next phase boundary take the fallback and log it:

| Blocked | Fallback (keep going) |
|---|---|
| Phone commands blocked or runner denied | Research from the web only: store screenshots, walkthrough videos (§5.5), help centre, reviews. Timings from video frames, tagged INFERRED. Build the whole game anyway, write "NO PHONE RESEARCH: fidelity unverified" in PLAN.md, and put the phone sessions first in the next steps. |
| PhoneCapture camera permission missing (`grab`/`rec` fail) | Bursts of `phone shot` for layout and colour; timings from walkthrough frames (INFERRED, with the source video's fps). |
| Original not installed | Web-only research, as above. The morning message lists exactly which captures are missing. |
| Game already past the tutorial | Never reinstall or reset it yourself. Take the FTUE and early levels from walkthrough videos. |
| Phone locked or disconnected overnight | Stop phone work and finish everything else. Never retry the runner more than 3 times in a row. |
| Workflow tool unavailable | Run the same roles as sequential subagents, one phase at a time, and say so. |

---

## 5. Phase 1: research (the most important phase)

You can't copy what you haven't measured. Match Factory's research (two phone sessions, ~7 h of phone time) produced:
- 19 levels logged in `levels.md`;
- ~420 full-resolution screenshots, ~100 clips with audio, ~250 item crops from 2–3 angles;
- frame-exact timings in `motion.md` (measured with `mfx`) and sound analysis in `sounds.md`;
- a 97-article help-centre scrape and 840 App Store reviews.

That is the floor.

### 5.1 Workflow shape: TWO research workflows
- **W-phone** (long and serial; the only thing that touches the phone):
  1. the player (the FTUE, then level 1 up to the genre minimum in the §14 table, using the §10.0 perception bot; ~2–4 h,
     split into sessions around lives and energy);
  2. motion analyst ∥ meta explorer;
  3. player session 2 (later levels);
  4. a gap filler (the clips listed in `research/clips-needed.md`).

  Launch the next phone workflow the moment one ends. The phone must never sit idle while the owner sleeps.
- **W-desk** (parallel, no phone): web research (§5.5), font match (against the store screenshots and kickoff crops), art spike,
  tech spike. When it ends (usually 1–2 h), immediately start the art pipeline upgrade and the UI-token work, without waiting
  for W-phone.
- Template: `tools/gameprompt/workflows/1-research.js`. It is Match Factory's script, so adapt it (§11) and split it into
  the two workflows.

### 5.2 The PLAYER (phone). Its prompt must require all of this
- **The original belongs to the owner.** Never uninstall, offload, reset, clear the data of, or log out of it, and never touch
  its account, its purchases or iOS settings (date, time, language). If it's past the tutorial, record where it is.
- **You may be a retry.** First: read the phone-state ledger, `phone shot`, and continue from the real phone state. A retried
  MF agent found the level paused mid-play.
- **Phone-state ledger:** `research/phone-session<N>-progress.md`. One timestamped line per level and per incident: level, lives
  + refill timer, coins, booster stock, keys, streaks, what is on screen when you stop.
- **Numbering blocks per session:**
  - session 1: shots `001–199`, clips `S1-*`;
  - session 2: `200–399`, `S2-*`;
  - the meta explorer: `meta-NNN-*`.
- **Play fast, play safe.**
  - For any grid, hex, tube, tile or letter game, **build the §10.0 perception bot within the first 20 minutes** and play
    with it. It must:
    - pass the popup guard before every move: HUD anchors match their crops and the board isn't dimmed;
    - stop **one move before any possible fail state** (last move, tray or waiting area at capacity − 1, last shot), where the
      agent decides by eye;
    - wait for the board to settle (two shots 0.3–0.4 s apart differing by < 1 %);
    - play ≤ 200 s per call, with the agent looping it;
    - log every move to `research/bot/log.jsonl` and dump each level's start state as draft level JSON;
    - render its recognised board as an overlay PNG before trusting it;
    - keep a look-alike list. In MF, thin bats lying across rackets made the taps pick the wrong item, and L19 was lost 3
      times.
  - Word and logic games read the board with Vision OCR (`hudocr.swift`).
  - Without a bot (tap games): take a shot, batch the obvious moves in one command with 0.3–0.4 s gaps, re-shoot.
    **Never batch near a fail state.** A queued tap once hit a purchase button.
  - **Timed levels: pause between batches** (resume → batch → shot → pause), so thinking never costs clock time.
- **Lives are the research budget.** A loss costs a life (30 min each in MF), so the player plays to win.
  - Deliberate fails happen only in the meta explorer, with full lives, after any streak feature has been captured.
  - At 1 life, stop and hand over to the meta explorer or desk work.
  - Never buy lives, energy or continues.
  - Using an already-owned booster or a free hint once, to record its effect, is research. Spending progression currency the
    normal way (stars on renovation tasks) is required, because that meta is what you're copying. Log every spend.
- **Per level, append to `research/levels.md`:**
  - the level number;
  - the timer or moves;
  - goals and counts;
  - the full board as a machine-readable block (an ASCII grid with a legend per layer; offset rows for hex);
  - item or piece types and counts;
  - tutorials (TR + EN);
  - unlocks, result, stars and rewards, and every popup before and after.
- **Screenshots** of every distinct screen and state.
- **Clips** (≤ 12 s each, log-poll recipe): the level intro, a single move, a combo or special, a goal completion, the full win
  sequence until home is idle (in chunks), home idle, every feature-unlock tutorial, and at least one full level in chunks.
- **Catalogue:**
  - `research/items.md` (or `pieces.md`): name, shape, colours, material, relative size, first level, and a `seen_in: [shots]`
    column;
  - crops in `research/items/<name>.png` from 2–3 angles;
  - sample colours from **untinted** states: hint glows and dim overlays tinted MF's crops and misled the art;
  - confirm each item on ≥ 2 shots (the "gold trumpet" was a harp seen side-on).
- **`research/flows.md`:** every screen and transition, every visible string (TR + EN), what every button does.
- Write files **after every level**: the agent may be interrupted.

### 5.3 META EXPLORER (after the player; full lives)
- **Home:** every button, tab, badge, currency, timer and idle animation.
- **Every menu:** the shop (look only), settings (every toggle and its toast), profile, events, daily rewards, chests,
  collections. Online screens: capture them.
- **In-level:** the pause menu; each booster's effect (record it).
- **Every FAIL path, deliberately:** out of moves or time, out of space, quit. Capture every offer screen and reject it, the
  "you will lose" and "level failed" screens, the lives decrement, and the out-of-lives popup.
- **The lives refill period,** measured exactly with timestamps across several refills. MF's first "~25 min" guess was wrong: it
  was exactly 30:00, counted from the level START.
- **Is the original deterministic?** Start the same level twice (after a real fail → Try Again) and diff the two start states.
  In MF "Try Again" deals a NEW pile, which decided the per-attempt seed design. For match-3, also check whether refills repeat.
  Check first whether a restart costs a life.
- **Some clips with the music off,** so the sound effects are clean.
- **English strings.** If the game has an in-game language setting, or iOS shows a Language row under Settings › Apps ›
  <game>, end with one EN pass (screens only, no play) and restore Turkish. Those strings are VERIFIED; otherwise they come from
  the store, the help centre and videos, tagged INFERRED.
- Write `research/meta.md`, `fail.md` and `boosters.md`, and update `flows.md`.

### 5.4 MOTION + EFFECTS ANALYST (videos only)
- **Use `mfx`, not `phone frames`, for timing.** The recordings are variable-frame-rate, so a timestamp gap means "nothing
  moved". Use real presentation times, never frame index × 1/60, and measure only inside continuous stretches.
- **Establish the input model first:** what happens on touch-down, while held, on drag and on release. Record `phone press X Y
  1.0` next to a quick tap. MF picks on RELEASE, so its flight formula had to be re-based from touch-down (0.295 s) to release
  (0.26 s).
- **Fit formulas, don't quote examples.** Collect ≥ 15 (distance, duration) pairs, fit by least squares and report the RMS.
  MF: T = 0.26 + 0.000635·d s, RMS 0.018 s over 21 pairs.
- **Colours come from runner shots only** (lossless, sRGB). Video frames and grabs are compressed and carry a video colour
  profile: use them for motion only.
- **What to measure:**
  - input feedback; durations and easing; scale and rotation keyframes; stagger;
  - the match, merge or clear sequence beat by beat;
  - particles (count, colour, size, lifetime, direction);
  - goal-counter animations; the level intro; win and lose sequences with timestamps;
  - popup springs; button press scale;
  - the camera or projection (3D FOV and tilt; 2D grid pitch); lighting and shadow direction.
- **Sound.** Extract with `mfx audio`, average repeated events with `evavg.py`, and describe each cue: pitch, length, character,
  a synthesis recipe, and its bus (music-off clips show which cues sit on the music bus). Find the BPM and key of each loop.
- **Publish `research/clips-needed.md` early:** every moment you couldn't measure, with its duration and whether music must be
  off. Every later phone session uses it as its shot list.
- Write `research/motion.md` (tables an engineer can type in) and `research/sounds.md`.

### 5.5 WEB research (W-desk)
- Load WebSearch and WebFetch via ToolSearch.
- **Store data:** the store page, ratings, "What's New" history, IAP list.
- **The publisher's help centre:** scrape ALL of it.
- **App Store reviews:** `https://itunes.apple.com/us/rss/customerreviews/page=N/id=<id>/sortby=mostrecent/json`, pages 1–10,
  both sort orders.
- **Wikis, level guides and Reddit.**
- **Walkthrough videos are level data.** "Levels 1–100" channels give goals, timers or moves, layouts and unlocks for levels
  the phone won't reach tonight. Video download is blocked, but storyboard sprite sheets and thumbnails work. Save annotated
  frames as `research/web/yt_frames/<source>_<level>_<what>.jpg`, tagged with the build and date.
- **Source precedence when sources disagree:** the phone (current build) > the help centre > current store screenshots > recent
  videos > older videos > reviews and wikis. YouTube *descriptions* can be AI boilerplate; only frames are evidence.
- Tag every claim VERIFIED, INFERRED or UNKNOWN, with sources, in `research/web-research.md`.

### 5.6 ART SPIKE and TECH SPIKE (W-desk)
- **Art spike.** Build this genre's art route (§7.2) on its first 3 items or pieces.
  - Put our render **side by side with the reference crop** at the same scale, and iterate until a player wouldn't notice the
    style difference.
  - For glossy 2D pieces, try BOTH routes (vector gradients, and a 3D model pre-rendered with `mfrender`) and pick the closer.
  - Deliver `art/PIPELINE.md` and `art/STYLE.md`: palette, materials, lighting measured from captures.
- **Tech spike.** Prove the §10 entry's engine on its own simulator, with the entry's spike checklist: the core mechanic,
  input, the hardest animation, fps at the densest board.
  - Deliver `design/tech-spike.md`: code that worked, measurements, pitfalls and the recommended architecture.

---

## 6. Phase 2: specs and the master SPEC

### 6.1 Four spec writers in parallel
Template: `tools/gameprompt/workflows/2-spec.js`. Adapt it, and give the writers your §6.3 scope.

| File | Owner | Content |
|---|---|---|
| `design/SPEC-gameplay.md` + `design/levels.json` | gameplay | Every rule and state machine: input, the core mechanic, goals, timers or moves, stars, hints, boosters and their edge cases, specials and obstacles, continues and fail paths with prices, lives, coins, unlock schedule, offline meta, EN/TR game strings. `levels.json` holds a schema, the recorded levels exactly, and designed levels in the original's curve. Each level carries `"source": "recorded" \| "video" \| "designed"` plus its capture. The generator/validator lives in `design/tools/`. |
| `design/SPEC-ui.md` + `design/ui-tokens.json` + `design/ui-crops/` + `design/fonts/` | ui | Pixel-measured geometry of every screen and component (pt = px × 393 / width), colours and gradients, bevels, shadows, text styles, the font match (licences included), every string (EN + TR), and the **UI art plan**: every graphic and how we make it. |
| `design/SPEC-motion-audio.md` | motion | A table row per animated event (start, duration, property, from → to, easing, sound cue), particle presets, a synthesis recipe per sound cue, the music loop specs, buses and mixing. |
| `design/SPEC-architecture.md` | architecture | See the section contract below. |

**Section contract.** The build template depends on it; put it in the architecture writer's prompt, and check it with
`grep -n '^## \|^### 12' design/SPEC-architecture.md` before the build. Model: `apps/matchfactory/design/SPEC-architecture.md`.
- §2 project (xcodegen, identity, `tools/*.sh`)
- **§3 folder layout and FILE OWNERSHIP**
- §4 core package
- §5 engine / board
- §6 shell
- §7 audio
- §8 game glue
- **§9 test hooks** (launch args `-<xx>.*`, capture mode, probe, accessibility ids)
- **§10 performance budgets**
- §11 risks and first-day checks
- **§12 build plan**: **§12.1** the slots/stages table; **§12.2** one block per work package, with ids WP0, C1–C4, L1–L2,
  A1–A3, UI-ART, B1–B2, S1–S3, G1–G2, V1–V3, D1, each with Files / Inputs / Acceptance.

Every fact in every spec is tagged `VERIFIED` (seen in captures), `INFERRED` or `DECISION`, with a citation.

### 6.2 Consistency pass, then the master `SPEC.md`
- **Don't reconcile from summaries alone.** Summaries caught 7 conflicts in MF, but others reached the build: the merge beat
  (0.30 s spec vs 0.33 s measured), a vacuum formula that ignored tray copies, and levels cast with stand-ins before later levels
  were recorded.
- Run one **consistency agent** after the four specs land. It extracts every named constant that appears in two or more files
  (durations, curves, colours, font names, bus names, ids, level fields, prices, unlock levels, formulas) into
  `design/CONSISTENCY.md`, with the value per file, the tag and the citation, and flags every disagreement. You rule on each
  flag.
- **`SPEC.md`** (you write it; keep it short):
  - the owner's sentence;
  - the copying line;
  - the PRECEDENCE block;
  - a **precedence table** of which spec wins for what;
  - your **reconciliations** (a measurement beats an estimate; a newer capture beats an older one);
  - the machine rules and the slot assignment.
- Commit the specs.

### 6.3 V1 scope (defaults; an owner-set limit always wins; tag deviations DECISION)
**Every genre:**
- iPhone only, portrait, iOS 18+ (`TARGETED_DEVICE_FAMILY: "1"`). EN (base) + TR.
- An app icon in the original's style, with our own mascot or monogram, behind `Brand` (1024 px, from our pipeline).
- No ads, no ad SDK, no ATT, no analytics, no network calls beyond StoreKit.
- **Ad-gated and paid entry points:**
  - Keep every button where the original has it, looking the same, video badge included.
  - Rewarded ads go through an `AdSlot` protocol. V1 ships `OfflineAdSlot`: it shows the original's "video not available"
    toast (or our honest equivalent) and never grants the reward in Release.
  - A coin price for the same thing (a hint or revive for coins) works through the local economy.
  - A DEBUG-only `-<xx>.ads simulate` flag drives the reward flow in tests.
  - **Never grant ad rewards for free in Release.** It silently changes the economy and the difficulty curve you measured.
- **StoreKit.**
  - Monetisation screens (shop, bundles, VIP) are copied 1:1, backed only by a local `.storekit` file.
  - That file applies only to the scheme's Run action: under `simctl`, `xcodebuild test` or a `devicectl` install,
    `Product.products` is empty (MF: "products: 0/12").
  - So tests and captures use a `FakeStore` with the same interface and the spec's prices, and the dev build on the phone
    falls back to FakeStore, labelled "Test store: nothing is charged". The shop is never an empty screen, and no real
    purchase path is reachable.
- **Online features:** entry points only, honest locked or "not available in this version" states.
- **Levels:**
  - reproduce every recorded level;
  - design the rest in the original's curve, using only items that exist or are being made;
  - when a later phone session records a level, the recorded version replaces the designed one and the validator and bot
    rerun (a TODO-ledger item).
- **Games without levels** (endless, merge, daily logic): P0 is every mode, meta screen and system a player meets in their
  first ~2 hours. The §10 entry's V1 line says what that means.

**Per genre:** use the V1 line of the §10 entry. Examples:
- **Swap match-3:**
  - P0: levels 1–40+ (every recorded level exact); every special, combo, obstacle and booster met by then, with unlock
    tutorials; moves, goals, stars, rewards, the end-of-level bonus; lives, coins; every win/lose flow; home, shop, settings,
    pause.
  - Renovation area 1 complete (every task, its before/after art and its build animation); area 2 as the original's locked
    teaser.
  - Our own mascot, with every animation seen.
- **Jigsaw:** the library home with the original's tabs and categories; ≥ 60 CC0/PD images across its top ≥ 6 categories; every
  piece-count option; the full play screen; "my puzzles"; a local-date daily puzzle; settings.

---

## 7. Phase 3: art, UI art, fonts, audio (in parallel with specs and build)

### 7.1 Art production (templates `3-art-round1.js`, `3b-art-round2.js`; adapt them)
0. **Catalogue identity pass, before any lane starts.** One agent checks every `items.md` entry against ≥ 2 captures and merges
   duplicates. In MF, `blue_case` and `boombox` were `blue_radio` seen from the back and top, "blue toy blocks" were keys, and
   `gold_trumpet`/`gold_tuba` (a harp seen side-on) were modelled, graded and thrown away. An item seen in only one shot is
   flagged; an item seen in none is not built.
1. **Pipeline upgrade agent.** It is the ONLY editor of the shared pipeline files. It adds what the engine needs:
   - for 3D: tray and card poses, closed outline shells, colour variants, the catalogue, material presets;
   - for 2D: atlases, @3x exports, naming.
2. **Lanes split by what the art IS**, not by habit:
   - **Many distinct objects** (tile match, merge items), by theme: 5 lanes, each adding **only new recipe files** (pipeline
     requests go into a file), iterating recipe → build → contact sheet next to the crops → Read → fix, and logging every item
     in `art/lanes/<lane>.md`. Finish everything at "good" before polishing any one item.
   - **Match-3 / tap-blast:**
     1. pieces and specials (with glow and idle frames);
     2. obstacles (every layer and damage state);
     3. board tiles, frame and background;
     4. UI-ART;
     5. renovation area 1 (the base scene, plus each task's object before and after);
     6. mascot and characters (animation parts).
   - **Jigsaw:**
     1. photo sourcing, licences and grading;
     2. the piece look (bevel, edge light, shadow, tray style);
     3. UI-ART;
     4. category thumbnails and icons.
   - **Vector/line puzzles:** only the UI-ART lane; the rest is measured geometry in code.
3. **Later phone sessions** capture new items in parallel. Round 2 builds them, and the content owner recasts `levels.json`
   from `art/ID-MAP.md`.
4. **Art director** (the grades that count):
   - **Commit each round's lane output before the director edits it.** In MF the pre-review recipes survived only as
     scratchpad copies.
   - Lane self-grades don't count. The director changed many (rope ring A → B+; pink gift A- → C → B+).
   - The director judges at game size against the capture of each level, never in close-up:
     - recognisable at a glance;
     - the right size next to its neighbours;
     - the same style family (saturation, gloss, edge softness, outline);
     - **look-alike decoys exactly as distinguishable as in the original, no more and no less.**
   - A mock board per level next to its capture, built from the **captured cast** (`review.py --cast capture`), never from
     what `levels.json` currently says.
   - Grade A/B/C, fix the worst, write `art/REVIEW.md`, and flag content errors.

### 7.2 Choosing the art route
- **3D objects** (tile-match 3D, 3D sort, physics piles): SDF recipes → USDZ → RealityKit (§3.5).
  - Budget 1.5–4k triangles per item.
  - Conventions: 1 unit = 1 cell, +Y up, +Z front, origin at the centre of mass.
  - The sidecar JSON holds stable poses (grouped for round items), collision hulls, tray/card pose and scale, and icons.
  - **Author at base size.** A per-level scale applied to lengths already measured at that level made L1 items 15 % too big.
- **Glossy 2D pieces** (gems, candies, cubes, tiles, bubbles): the spike picks vector gradients vs a 3D pre-render with `mfrender`
  (transparent background, checked for alpha) by side-by-side comparison, and logs the choice in STYLE.md.
- **Flat and vector games** (arrows, lines, nonograms, sudoku-like, word): no bitmaps on the BOARD; draw with Core Animation,
  SwiftUI or Core Graphics from measured geometry. Backgrounds may be photos or our SVG illustrations. Nonogram and
  colour-by-number pictures are assets: our own pixel art.
- **Illustrations** (home scenes, renovation areas, backgrounds): SVG with gradients and shading, rasterised @3x with `svgr`,
  or 3D scenes rendered with `mfrender`. Never bake translatable text into raster art: draw text as a separate layer (MF's
  crate ships a blank panel plus quad corners).
- **Characters and mascots:** our own design in the original's style, as separate SVG parts (head, eyes, mouth shapes, torso,
  arms, hat), animated as a cut-out puppet (SpriteKit nodes or CALayers) with keyframes measured from the clips.
- **Voice lines** ("Sweet!", grunts): macOS `say` output must not ship. DECISION: a musical sting at the same moment, plus the
  on-screen word.
- **Photos** (jigsaw, word backgrounds): CC0 or public domain only.
  - **Sources:**
    - the Openverse API (`license=cc0,pdm`);
    - Wikimedia Commons public-domain paintings (PD-Art);
    - NASA and other US-government works.
    Not Unsplash or Pexels: their licences are not CC0 and restrict compiling their photos.
  - **Resolution:** native ≥ 2048 px on the long edge; **never upscale.** The 4032 px rule in fixture-photography was for
    storage-app fixtures, where upscaling was the point.
  - **Excluded:** identifiable people, logos, brands, visible text, watermarks (Vision text detection), and artworks still
    under copyright.
  - **Curation:** sharpness (Laplacian variance), colourfulness; match the original's category mix and brightness.
  - **Shipping:** JPEG/HEIC at about 2× the board size (never 4032 px: 48 MB in RGBA), plus thumbnails; budget ≤ 150 MB.
  - **Records:** `design/images.json` (id, category, source URL, author, licence, size, SHA-256). The validator fails any image
    without an entry.
  - **Review:** labelled contact sheets indexed by filename, not by `ls` order.
- **UI art:** one UI-ART agent follows SPEC-ui's plan and produces `art/ui/out/<name>@3x.png` at exact frame×3, each with a
  side-by-side sheet. Simple shapes (rounded rectangles, gradients, bevels, outlined text) stay SwiftUI code.
- **Audio.** Make it polished (a top-grossing casual game's feel, not bleeps); synthesise every cue from its recipe, and compose
  our own loops in the analysed BPM and key. **Nothing may derive from `research/sound-refs`.**
  - **The checker is part of the deliverable** (model: MF `tools/audio/check.py` + `check_selftest.py`). Per cue, it checks:
    - length, peak and true peak ±1.5 dB;
    - mono 44.1 kHz 16-bit;
    - no click at the start or end;
    - the loop seam, with RMS across it within ±1 dB;
    - no stray files.
    Its self-test injects mutations and must catch all of them.
  - **Measure what the app outputs** per cue (bus level vs the file, onset latency). MF found a 6 dB mono-through-stereo loss
    this way.
  - **Compare by picture:** our spectrogram next to the original's event-locked median (`evavg.py`). Band levels within ~3 dB,
    attack and decay within ~20 ms. This is comparison, not derivation.
  - Compress the music loops (AAC) if the WAVs are large.

---

## 8. Phase 4: build

### 8.0 Reuse before you write
Before WP0, one agent (no simulator) copies what transfers (§3.5), renames the MF prefixes, and writes `design/REUSE.md`. The
board or engine is always new.

### 8.1 Engine choice (the §10 entry decides; confirm it in the tech spike)
- **Vector or line puzzles:** UIKit + **Core Animation** `CAShapeLayer`, with animations on the render server.
  - Arrows proved `strokeStart`/`strokeEnd` + the head position in one `CATransaction` (attachment ≤ 0.03 pt).
  - Shape layers stay crisp under `UIScrollView` zoom with no fix.
  - Disable implicit actions on every model write.
- **Sprite puzzles** (match-3, tap-blast, tile 2D, mahjong, block, sort, jigsaw, bubble, merge): **SpriteKit**. Neither
  exemplar used it, so the tech spike must prove each point:
  - **Hosting:** an `SKView` in a `UIViewRepresentable` owning ONE persistent scene.
    - The kitz memory found that a `SpriteView` scene had zero size when first presented, and that re-creating it via `.id()`
      double-presents it.
    - Size the scene from the view's bounds, and spawn on the first `update` with a non-zero size.
  - **120 Hz:** `preferredFramesPerSecond = 120`, plus `CADisableMinimumFrameDurationOnPhone` in the base plist.
  - **Textures:** one atlas per family (`SKTextureAtlas(dictionary:)` from our @3x PNGs), preloaded with `SKTexture.preload`
    behind the loading screen; `ignoresSiblingOrder = true` with explicit zPositions.
  - **Never in play:** `SKShapeNode`, `SKEffectNode`/CIFilters, `SKCropNode` per piece, `SKLabelNode` for changing numbers.
    Use bitmap digits and pre-rendered glows with `.add` blending instead.
  - **Curves:** `SKAction.timingFunction` fed by the core's unit-tested curves, so the motion.md numbers drive the actions.
  - **Particles:** `SKEmitterNode` configured in code, or pooled sprites.
  - **Input:** touches go to the core on the same frame; hit-test with the core's grid maths.
  - The core resolves a move into a step list; the scene plays it back.
- **3D physics puzzles** (tile-match 3D, 3D sort, bus jam in true perspective, hexa-sort flips): **RealityKit**
  `ARView(cameraMode: .nonAR)` in `UIViewRepresentable` (SceneKit is deprecated):
  - `cancelsTouchesInView = false` on ARView's hidden tap recognizer, and our own touch handling;
  - an inverse-LUT post-process for ARView's forced tone mapping;
  - a `CustomMaterial` outline shell;
  - a tween engine in the per-frame update;
  - warm materials up behind the loading screen;
  - settle on a velocity threshold, not on sleep; angular damping ≈ 2.5 for round items.
- **Shell:** SwiftUI + Observation.
  - The HUD syncs at ≤ 10 Hz.
  - A popup host with stackable async popups.
  - Outlined "casual game" text in our font.
  - `Brand`.
  - Strings from a TSV (EN + TR) as `LocalizedStringKey`; custom components taking `String` ship untranslated.
- **Core:** a pure-Swift package (`swift test` on macOS, no simulator) holding:
  - rules, the level model, a session state machine with one event stream, economy, lives (wall-clock chains), persistence
    (atomic JSON; never `@AppStorage` for game state) and a seeded RNG with named streams;
  - geometry and motion curves, unit-tested against motion.md;
  - a level validator and a bot or solver (`HeadlessDriver` pattern).

### 8.2 The build workflow (template `4-build.js`; adapt it: §11)
A dependency DAG over two simulator slots (A and B), plus no-simulator lanes:
```
WP0 lead (slot B): project.yml, tools/{gen,build,run,test,slot}.sh, frozen ◆ contracts (+ sha256), core stubs, tuning JSON, storekit, assets
├─ no-sim: C1→C2→C3→C4 core (swift test)  ·  L1→L2 content (levels from levels.json + tutorials + strings)  ·  A1→A2 audio  ·  UI-ART
├─ slot A: B1 board/engine foundation + risk checks → B2 choreography/effects → G1 game glue → G2 boosters/tutorials/specials/meta → V3 perf+soak
└─ slot B: S1 shell foundation → A3 audio integration → S2 HUD/popups/win → S3 home/shop/meta → V1 test suites → V2 side-by-side fidelity
then: your own 5-finish workflow — fix loops, level recast from new recordings, D1 device check, install (§9)
```
- Every work package ends with the slot's build green, the simulator shut down, and a structured report: status, acceptance
  items with evidence paths, files, requests for others, open issues.
- **One app target, many editors, means broken builds for everyone** (MF's S1 broke on BOARD's half-written shader; G1 on S3's
  mid-edit view). So:
  1. Never leave your files non-compiling past one edit-build cycle. Develop big rewrites in a new file and wire them in when
     they compile.
  2. Use one local Swift package per owner where the engine allows it.
  3. To build while others edit, build a scratch copy (`tools/gameprompt/snippets/iso-build-copy.sh`) after
     `wait-build.sh`.
  4. An agent blocked by someone else's file appends `file:line error — owner` to `build/blocked.md` and works around it.
     You apply the minimal fix yourself, as orchestrator (as with MF G1's boot hang: `prepare()` awaited the layout of a view
     that wasn't in any window).
- **Frozen contracts are enforced:** `shasum -a 256 -c build/wp0/frozen-contracts.sha256` at the end of every package, and an
  `APISurfaceTests` file that imports the core WITHOUT `@testable`.
- Commit after the build workflow and after every fix loop.

### 8.3 Acceptance techniques (proven in MF `build/*/evidence.txt`)
- **Mutation checks prove the tests.** Core, content/strings and audio owners inject plausible bugs one at a time, run the
  suite, restore the source, and report CAUGHT or MISSED. A MISSED mutation means a weak test. MF's first core draft missed 2
  of 5.
- **Independent reference implementations** for numerics: RNG, projection maths, the lives chain, flight formulas. Swift and
  Python must agree exactly (`snippets/rng_ref.py`).
- **A lab screen per engine owner** (BoardLab, ShellLab, SoundBoard), reachable by a launch argument, drives the real engine with
  scripted scenarios and writes `Documents/lab-ready.json` plus perf JSON. Owners prove their acceptance before the glue exists.
- **Read back what was rendered, not what was set.** MF checked flights against their landing frames: 47/47 within ±1 frame.
- **Timing from log marks:** `mark <name> t=<uptime>`, and a checker that prints OK/FAIL against the spec rows.
- **Golden tests from real play:** turn a recorded phone attempt into a test.
- **Captures wait for a ready file, never a fixed sleep** (`snippets/capture-shot.sh`):
  1. the app writes `capture-ready.json`;
  2. `xcrun simctl io <udid> screenshot --type=png --mask=ignored`;
  3. `sips -m "/System/Library/ColorSync/Profiles/sRGB Profile.icc"`;
  4. reject frames that are > 88 % one flat tone.
- **Performance on a loaded Mac needs an idle baseline** (MF saw 65 ms stalls idle at load 11). Measure speeds over ≥ 45 ms
  windows. The verdict is taken on the phone (D1).
- **Holds:** whatever the loop consumes must not change while the player can't act:
  - timers during popups, pause, tutorials and freezes;
  - moves on invalid swaps, booster use and cascades;
  - lives on a quit from home;
  - elapsed time in menus.
  Probe the value; it must stay constant for 3 s.
- **Autoplay:** from a fresh install, the launch argument `-<xx>.autoplay 1` completes levels 1→N in order, and the tutorial log
  matches the expected list. Stochastic genres use each level's **golden seed**: the first seed the bot wins, stored in
  `levels.json`.
- **Difficulty bands** (stochastic genres): a Monte-Carlo bot at human-like speed plays ≥ 200 seeds per level and records win
  rate, moves or time left (p10/p50/p90) and booster use in `build/<role>/difficulty.csv`.
  - Calibrate by running it on the RECORDED levels of the same difficulty tag.
  - The band check is a content test: when it fails, fix the level, never the band.
  - A bot winning with 78 % of the time left proves a level is solvable, not how hard it feels.
- **Overlay-verify every recorded level:** render our level JSON over the capture and diff (IoU ≥ 0.99).
- **Content:** every level passes the validator and the solver or bot. Every item or piece id resolves in the bundle. Strings are
  covered in EN and TR, including the argument ORDER.
- **Brand:** grep the build for the working title and the brand's initials. They may appear only in `Brand`, the build settings
  and string interpolation, and never in file names.

---

## 9. Phase 5: verify, polish, finish

1. **V2 side-by-side fidelity.**
   - Capture ≥ 30 screens and states in EN and TR, plus freezes of the key sequences.
   - Compare each region against research shots (`compare_all.py`): layout ±2 pt, ΔE ≤ 6.
   - Write `build/compare/FINDINGS.md` with an owner per finding.
2. **Fix loops are bounded:** at most 3 rounds of V2 capture → fixes → re-capture.
   - You schedule owners one at a time per slot.
   - After round 3, every open finding goes to the report with its measured delta and owner.
   - **P0 findings are never deferred:** a wrong rule, a broken flow, a crash, a missing screen.
3. **Level pass.**
   - Autoplay all levels.
   - Play 3–5 levels "by hand" through XCUITest taps, and look at the frames yourself.
   - Recast any level that has since been recorded.
4. **D1 on the phone** (once the phone is free; you hold the lock):
   ```sh
   cd /Users/yago/Downloads/app-factory; set -a; source .env; set +a; KP="$ASC_KEY_PATH"; case "$KP" in /*) ;; *) KP="$PWD/$KP";; esac
   xcodebuild -project apps/<slug>/<Name>.xcodeproj -scheme <Name> -configuration Release \
     -destination id=00008120-000964E426440032 -derivedDataPath apps/<slug>/build/device -jobs 4 -quiet \
     -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
     -authenticationKeyPath "$KP" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID" build
   D=878DB538-F187-596F-B24B-EAF8853617DE
   xcrun devicectl device uninstall app --device $D com.manycode.<slug>    # fresh save; ignore "not installed"
   xcrun devicectl device install app --device $D apps/<slug>/build/device/Build/Products/Release-iphoneos/<Name>.app
   xcrun devicectl device process launch --device $D com.manycode.<slug>
   ```
   - Give the build a Bash timeout ≥ 300000 ms. A "provisioning profile … cannot be found" error is a race: retry once.
   - Run the bench on the densest level.
   - Check feel: touch latency, 60 fps, and the first-launch stall (shader compile). 120 Hz can't be checked on this phone.
   - Record our game with `phone rec` next to the original's clip of the same moment, and compare them side by side.
   - If a budget misses on the device, do one optimisation round, then report the numbers.
   - The Release build must boot, **without launch arguments**, to the real first-run state. The shop works through the
     FakeStore fallback. `phone shot` and LOOK.
5. **After §14, if the owner hasn't returned:** implement P1 items in scope order, committing after each. Stop when P1 is done,
   or when the next item needs the phone and the phone is unavailable.
6. **End state:**
   - our game installed and in the foreground on the phone: home, level 1, fresh save;
   - `phone stop`;
   - `/tmp/phonedriver.lock` removed;
   - the watchdog, heartbeat and caffeinate stopped;
   - your simulators shut down, and erased if disk is tight;
   - scratch cleaned;
   - the final commit.
7. **The final message to the owner:**
   - what they can play right now, and how;
   - 2–3 comparison images (with SendUserFile if it's available);
   - what is done;
   - DECISIONs;
   - known gaps and open findings;
   - accidents;
   - next steps.

---

## 10. Genre playbooks (puzzle games)

Starting points, not answers. A number not marked as measured is a hint to verify on the phone; the recordings of the original
always win over this section.

### 10.0 How to use this section
**Pick the playbook: classify by core verb, not theme.** Hybrids get both entries, led by the core loop.

| Core verb | Entry |
|---|---|
| swap two pieces | 10.1 |
| tap a group | 10.2 |
| tap an item into a tray, 3D | 10.3 |
| tap a tile into a tray, 2D | 10.4 |
| pick free pairs | 10.5 |
| drag pieces into a picture | 10.6 |
| drag shapes onto a grid | 10.7 |
| move top runs between containers | 10.8 |
| tap or slide a piece out | 10.9 |
| tap a unit that walks to a queue | 10.10 |
| pull pins / unscrew under physics | 10.11 |
| drag-merge with generators | 10.12 |
| swipe through letters | 10.13 |
| fill cells by logic | 10.14 |
| aim and shoot | 10.15 |
| drop stacks that transfer by colour | 10.16 |
| yarn / knit | 10.17 |

- **A genre without a game** → copy the category leader (§4 step 0).
- **Templates:** each entry's **Spikes** line replaces the templates' ART and TECH spike prompts; **Rules** and **Measure** go into
  the PLAYER, META and ANALYST prompts; **Content** goes into the gameplay-spec brief. Paste the whole entry into every COMMON.
- **Scope:** the entry's **V1** line applies unless the owner set a limit.

**Research tricks for every genre** (the PLAYER and META prompts require the ones that apply):
- **Perception bot** in `research/bot/` (Python + PIL). One loop:
  1. shot;
  2. **guard**: 2–3 HUD anchors match their crops within ΔE 8, and the board isn't dimmed by more than 15 %; otherwise STOP
     and hand back;
  3. **read**: sample cell centres and cluster crops with k-means into classes named once in `bot/classes.json` (an unknown
     cluster means stop and label);
  4. **solve** with our solver;
  5. **act** with `phone tap` or `phone swipe`;
  6. **settle**: the board region unchanged between two shots;
  7. **log** `{level, state, move, result}` to `bot/log.jsonl`.

  Each call plays ≤ 200 s. The bot writes each level's start state as draft level JSON, and never moves within one move of a
  fail state.
- **OCR** for letters, digits, clues and HUD numbers: `hudocr.swift` (Vision).
- **Restart diff:** start the same level twice and diff the start boards. What matches is authored (layout, blockers, goals,
  deals); what differs is RNG. The diff decides the level model. Check first whether a restart costs a life.
- **Distributions, not impressions.**
  - Count ≥ 500 spawned pieces or dealt shapes and test them against uniform (chi-square) and against the board state (does the
    game deal what fits?).
  - Fit score, coin and star formulas by least squares.
  - Time every flight at ≥ 3 distances.
- **Input probes:**
  - the swipe-commit threshold (4, 8, 12, 16, 24 pt);
  - tap vs drag;
  - input during an animation: a second input at +100, +250 and +500 ms into a cascade, and whether it is queued, dropped or run
    concurrently. Often this IS the feel;
  - the drag lift offset;
  - hit tolerance (taps 5, 10 and 15 pt off target).
- **Finger-down states** (aim lines, ghost previews, snap highlights) exist only while a finger is down: record them during a
  slow swipe.
- **Haptics** can't be recorded. Note whether settings has a vibration toggle, map each event class to a
  `UIImpactFeedbackGenerator` style, and tag the mapping DECISION.

**Content rules.**
- **Deterministic puzzles** (escape, sort, unblock, mahjong deals, logic, jigsaw cuts): reproduce recorded levels exactly and prove
  each with the solver; generate the rest, with the solver as the gate.
- **Stochastic puzzles** (match-3, tap-blast, bubble, block, hexa, merge): reproduce the authored part exactly; the fill is
  seeded; difficulty bands and golden seeds as in §8.3.
- **Artwork content is an asset,** so it must be ours: nonogram pictures, jigsaw photos, mahjong faces, word backgrounds, merge
  chains. Pure mechanics data (grids, layouts, colour orders) may be reproduced.
- **RNG:** named streams per consumer (`fork("refill")`, `fork("deal")`), as in `MFRandom.swift`. The bot runs the real core.

**Engine rule of thumb** (the entry's choice wins; details in §8.1):
- flat vector with few moving parts → Core Animation or SwiftUI Canvas;
- many sprites, particles or 2D physics → SpriteKit;
- true 3D (the camera moves, objects pile or tumble) → RealityKit;
- a fixed 3D-looking camera → pre-rendered sprites, unless objects visibly rotate in depth.

**Meta:**
- **Offline (build it):**
  - lives and refill timers, coins, in-level and pre-level boosters;
  - stars, star chests, win streaks;
  - daily bonus and daily puzzles;
  - local events with bundled content;
  - renovation and decoration;
  - collections without trading.
- **Online (show locked):** teams, leaderboards, races or tournaments against other players, trading, gifting, cloud save.
- Rewarded ads and IAP follow §6.3.

### 10.1 Swap match-3 (Royal Match, Candy Crush)
- **Rules to pin:**
  - the board mask and the layers per cell (under: grass or jelly; the piece; over: chains, ice, cage), and which layer a
    match or blast damages;
  - match shapes, and which one wins when a move makes several;
  - the special each shape makes, where it is born (the swapped cell or the match centre) and its orientation;
  - every activation area, and every special + special combo;
  - gravity, including diagonal slides past blockers; spawners and non-spawning cells;
  - the no-moves shuffle; the moves-left bonus.
  - Hints to verify:
    - Royal Match: rocket = 4 in a line, propeller = 2×2, TNT = L/T, light ball = 5;
    - Candy Crush: striped, wrapped, colour bomb, fish.
- **Measure:**
  - swap T and curve; the invalid swap's out-and-back; the swipe-commit threshold; whether tap-then-tap swaps work;
  - the clear pop (scale, T, stagger);
  - falls: y(t) from 3 heights (constant acceleration? a speed cap?), landing squash, column stagger, the delay between
    cascade steps;
  - special birth (convergence); rocket speed (pt/s); TNT radius and timing; the propeller's path and how it picks a target;
    the light-ball beam stagger;
  - obstacle hit flash and debris;
  - goal fly-to-HUD (T vs d); hint idle delay and wiggle; the shuffle;
  - the cascade pitch ladder (semitones per step) and combo banners.
- **Engine:** SpriteKit.
  - The core resolves a move into a step list: swap → match → specials → damage → gravity → refill → repeat.
  - If the original takes input during cascades (use the input probe), resolve regions concurrently with per-column locks. This
    is the genre's hardest problem.
- **Art:**
  - pieces and specials: SDF-modelled and pre-rendered to transparent @3x under a rig matched to the captures (or vector,
    whichever the spike picks);
  - obstacles with 2–4 damage states plus debris;
  - a procedural FX kit (soft dot, sparkle, streak, shockwave ring, smoke) with additive blending;
  - the board frame as a 9-slice;
  - renovation areas as illustrations, with a before and after per task: the biggest art cost, so scope it.
- **Content:**
  - `levels.json`: mask, layers with hp, colour count, spawn weights, goals, moves, pre-placed specials, spawners;
  - validator: no match at the start, ≥ 1 legal move, every goal reachable, every obstacle damageable;
  - bot: greedy with 1-ply lookahead over the real resolver, with bands.
- **Meta:**
  - offline: lives, coins, boosters (verify Royal Match's: hammer, arrow, cannon, jester hat, plus pre-level boosters), win
    streak, chests, renovation tasks paid with stars;
  - locked: teams, races, the pass.
- **Research:**
  - the perception bot is mandatory (a level by hand takes 5–10 min; with the bot, ~1 min);
  - specials and obstacles are their own classes;
  - swap with a `phone swipe` of ~40 pt at 0.12 s;
  - record some clips with the music off for the pitch ladder;
  - check the wiki level pages.
- **Spikes and V1:**
  - art spike: 3 pieces + 1 special;
  - tech spike: the full resolver with cascades, one special of each kind, the input-during-cascade policy, and 81 pieces plus
    particles at 60 fps (120 opt-in);
  - V1: every recorded level (≥ 40) plus designed levels up to 60; all specials, combos and obstacles up to 60; renovation area 1.

### 10.2 Tap-blast / collapse (Toon Blast, Toy Blast)
- **Rules to pin:**
  - a group of ≥ 2 orthogonally connected same-colour cubes pops; a lone cube shakes (does it cost a move?);
  - group-size thresholds make specials at the tapped cell (Toon Blast hint: 5–6 rocket, 7–8 bomb, 9+ disco ball; verify);
  - specials fire on tap, and combo when next to each other;
  - gravity and refill; a shuffle when no group exists;
  - obstacles: boxes, balloons, toys that must reach the bottom;
  - goals and moves.
- **Measure:**
  - tap-to-pop latency; pop scale and particles;
  - the special-preview icons on a qualifying group;
  - special birth; rocket speed and split; bomb radius; disco lightning stagger;
  - fall and bounce; refill stagger; goal fly-to-HUD; the end bonus;
  - whether taps are accepted during falls.
- **Engine:** SpriteKit; a flood-fill resolver; per-column settle flags, so taps during falls work.
- **Art:** glossy relief cubes pre-rendered from 3D; obstacles with damage states; our own cartoon cast in SVG; the episode map
  as tiled SVG.
- **Content:** the match-3 JSON without swaps; a goal-directed greedy bot biased toward making specials, with bands; validator:
  ≥ 1 group at the start.
- **Meta:**
  - offline: lives, coins, boosters, pre-level rocket/bomb/disco, the map, star chest;
  - locked: teams.
- **Research:** the bot only classifies cells, so it's very fast; the icons on the cubes reveal the thresholds without spending
  moves.
- **Spikes and V1:**
  - art: 3 cubes + a rocket;
  - tech: taps during falls with 100 cubes;
  - V1: the first ~40 levels.

### 10.3 Triple match 3D (Match Factory, Triple Match 3D)
- **Rules to pin:**
  - the pick is the topmost visible item: highlight on touch-down, the target follows the drag, commit on release;
  - tray insertion (MF: 7 slots; a new item goes after its identical items); a triple merges; a full tray fails;
  - goals; the timer and what pauses it;
  - stars (MF: time-left ratio ≥ 0.40 → 3★, ≥ 0.20 → 2★, an INFERRED fit on 9 levels; collect wins near each boundary);
  - boosters and continue prices.
- **Measure:**
  - the flight (MF: T = 0.26 + 0.000635·d s from release);
  - merge beats and tray hops;
  - hint cadence (MF: first at 5 s, then every 4 s) and the timer colour stops;
  - how neighbours react physically;
  - camera FOV and tilt; the lighting rig.
- **Engine:** RealityKit `ARView(.nonAR)`, with every §13 engine pitfall in mind.
- **Art:** SDF → USDZ; goal-card icons rendered from the same models.
- **Content:** counts in multiples of 3; decoys (the same model in another colour, or look-alikes); big occluders; layered piles;
  `HeadlessDriver`.
- **Meta:**
  - offline: lives, coins, boosters, streak chest, daily bonus, key challenge;
  - locked: teams.
- **Spikes and V1:** as in `apps/matchfactory`; 30 levels.

### 10.4 Tile match 2D (Tile Busters, Tile Master, Zen Match)
- **Rules to pin:**
  - tiles in layers on half-tile offsets; a tile is pickable only if no higher tile overlaps it (by any amount? measure);
    covered tiles are dimmed;
  - the tray; a triple clears; a full tray fails;
  - boosters (undo, shuffle, auto-triple, extra slot, return-3; verify per game);
  - timer and stars.
- **Measure:** tap feedback; the flight T(d); tray hops; the triple clear; the undim fade; the per-layer deal-in stagger; the
  shuffle; the full-tray shake.
- **Engine:** SpriteKit (≤ ~200 tiles).
- **Art:**
  - the tile body (bevel, thickness, shadow): pre-rendered once, or drawn with Core Graphics;
  - faces: our own icon set in their style.
- **Content:**
  - layouts as `(x, y, layer)` in half-tile units, extracted by edge detection plus the dim level;
  - the restart diff decides whether faces are fixed;
  - the generator assigns faces in triples along a simulated removal order that respects the tray capacity (solvable by
    construction);
  - a DFS solver with memo validates each deal and rates difficulty.
- **Meta:**
  - offline: lives, coins, boosters, stars, chests, daily;
  - locked: leagues.
- **Spikes and V1:**
  - art: the tile body + 6 faces;
  - tech: 150 tiles, the pick rule and the tray;
  - V1: 30–50 levels.

### 10.5 Mahjong solitaire
- **Rules to pin:**
  - identical pairs clear; flowers and seasons match within their group;
  - a tile is free when nothing lies on it and its left or right side is open;
  - layouts;
  - hint, shuffle, undo; the no-moves prompt; timer and stars.
  - Tray hybrids go to 10.4.
- **Measure:** the select highlight; the pair slide-together and burst; the invalid shake; hint and shuffle; the per-layer offset,
  tile thickness and shadow; zoom and pan; the win sequence.
- **Engine:** SpriteKit + `SKCameraNode`.
- **Art:** the tile body pre-rendered; faces as our own SVG set (CJK glyphs from Noto Serif CJK, OFL); never their faces.
- **Content:**
  - layouts as `(x, y, z)`;
  - the deal is built in reverse (pairs placed on positions that would be free), so it's solvable by construction;
  - a DFS solver counts dead ends for difficulty.
- **Meta:**
  - offline: a daily calendar, trophies, skins, stats;
  - locked: leaderboards.
- **Spikes and V1:**
  - tech: 144 tiles with zoom;
  - V1: the recorded layouts + 50 designed + dailies.

### 10.6 Jigsaw (Jigsaw Puzzles by Easybrain, Magic Jigsaw)
- **Rules to pin:**
  - piece counts per difficulty;
  - the cut (classic tabs: neck width, head radius, jitter; or a grid); rotation mode;
  - where loose pieces live: a bottom tray strip, or scattered;
  - **whether pieces join each other as groups anywhere, or only lock into their board cell.** Measure this first: it shapes the
    core, the snap code and the tests;
  - the edge-only filter, the ghost image, background colours;
  - completion (seams fade, a shine sweeps); autosave per puzzle; unlocks.
- **Measure:**
  - pickup from the tray (scale, T);
  - the drag lift (scale, shadow offset and blur) and drag-follow latency;
  - the **snap threshold**: after one piece snaps, drop its neighbours at 4, 8, 12, 16, 20 and 30 pt off target, each drop
    recorded at 60 fps; log snap or no snap;
  - the snap animation, sound and haptic;
  - what a wrong drop does; tray scroll physics; the zoom range; completion.
- **Engine:** SpriteKit.
  - Cut the pieces with Core Graphics Bézier paths at load and **bake each piece** (mask, bevel and edge light, shadow) into ONE
    atlas per puzzle, at about 2× the board's size in pt.
  - Never use `SKCropNode` or `SKEffectNode` per piece: each costs a stencil or offscreen pass, and 100–400 of them kill the
    frame rate.
  - `SKCameraNode` for zoom.
- **Art:** photos per §7.2; illustrated packs as our own SVG.
- **Content:**
  - a puzzle = image + cut seed + piece count, and the cut is deterministic;
  - validator: no self-intersecting tabs, the thinnest neck ≥ 6 pt at the largest count, one slot per piece;
  - autoplace completes every puzzle.
- **Meta:**
  - offline: coins for unlocks, a local-date daily puzzle, albums, local events;
  - locked: downloaded images.
- **Research:**
  - finish ≥ 3 puzzles (the smallest, a middle one, one of ≥ 100 pieces);
  - open every piece count, tab and category;
  - solve with the preview: capture the full image, then match each tray piece to its cell by normalised cross-correlation on
    1/3-scale crops;
  - drag with `phone swipe d ≥ 0.4`, or `/drag` with a hold; zoom needs `/pinch` (§3.2).
- **Spikes and V1:**
  - tech: cut 225 pieces from a 3000 px photo in < 1.5 s and < 150 MB; drag at 60 fps; snap;
  - V1: §6.3.

### 10.7 Block puzzles (Block Blast, Woodoku, 1010!)
- **Rules to pin:**
  - board size (8×8; 9×9 with 3×3 boxes; 10×10);
  - 3 pieces per deal; whether a new deal comes only after all three are placed; no rotation;
  - rows, columns (and boxes) clear simultaneously;
  - game over when no piece fits;
  - scoring: per cell, per line, the multi-line multiplier, combo streaks, the board-clear bonus;
  - modes; revive.
- **Measure:** piece scale in the tray vs on the board; the lift offset; the ghost and "will clear" highlight; drop snap T; the
  invalid-drop return; the line-clear sweep (stagger, direction); the score count-up and "+N"; combo words; the game-over
  grey-out; the deal slide-in.
- **Engine:** SpriteKit or Core Animation. The dragged piece follows the touch on the same frame.
- **Art:** glossy cells (a pre-rendered rounded cube, or a Core Graphics bevel); Woodoku style: procedural wood grain with engraved
  cells.
- **Content:**
  - classic mode has no levels: **the generator is the content.** Log ≥ 300 deals with their boards, measure shape frequencies
    and any bias toward pieces that fit, and implement the same statistics;
  - adventure levels are recorded exactly;
  - bot: exhaustive search over orders and positions, scored by lines, holes and open space.
- **Meta:**
  - offline: best score, revive, themes, daily;
  - locked: leaderboards.
- **Spikes and V1:**
  - tech: drag latency and the line clear;
  - V1: classic, plus adventure levels 1–20.

### 10.8 Sort puzzles (water, ball, nut & bolt)
- **Rules to pin:**
  - capacity (usually 4);
  - a move takes the top contiguous run into a container whose top matches or is empty, as much as fits;
  - the win: every container empty or full of one colour;
  - hidden "?" units, locked or extra containers, the undo count, restart.
  - Screw-the-planks → 10.11; screw-into-boxes → 10.10.
- **Measure:**
  - water: the select lift, the path, the tilt angle and pivot, pour T per unit, stream width, surface wobble, the return;
  - balls: pop-out height, arc, bounce;
  - nuts: the unscrew spin, the hop, the screw-down;
  - the cap and confetti when a container is done; the invalid shake.
- **Engine:** SpriteKit.
  - Water needs an `SKShader` that fills the tube in WORLD space, so the surface stays level while the tube tilts, plus a wobble
    term. This is the tech spike's main risk.
  - Nuts: 8–12 pre-rendered spin frames (RealityKit only if the camera is truly 3D).
- **Art:** vector glass with gradient highlights; exact liquid hexes; balls and nuts pre-rendered from 3D.
- **Content:**
  - containers bottom → top + capacity;
  - record the first 20 exactly;
  - BFS/A* over a canonical state proves solvability and gives the minimum moves;
  - the generator shuffles, then the solver filters, fitted to the recorded min-moves curve; never start with a finished
    container.
- **Meta:** offline: coins, undo and extra-container boosters, skins, daily.
- **Spikes and V1:**
  - tech: the pour shader;
  - V1: the recorded 20 + generated levels up to 200.

### 10.9 Escape / unblock / parking (Arrows, Tap Away, Unblock Me, Parking Jam)
- **Rules to pin:**
  - escape: a tapped piece leaves along its path if its ray is clear, otherwise it bumps and costs a heart;
  - sliding: drag along the piece's axis; stars for minimum moves;
  - parking: a swipe moves a car forward or back, and a free car drives the loop to the exit;
  - the exact blocking rule; penalties; zoom.
- **Measure:**
  - the grid pitch, from line positions;
  - path geometry: stroke, corner radius, the head;
  - exit T(d) and acceleration; trail dots;
  - the bump-and-return: distance, T, colour;
  - hit tolerance; zoom and pan limits; hearts;
  - parking: the loop path, speed, the exit queue.
- **Engine:** Core Animation for flat puzzles (Arrows); SpriteKit for sprite cars; RealityKit, or 8–16 pre-rendered headings, for
  a 3D lot.
- **Art:** vector paths with no bitmaps; cars and blocks from the SDF pipeline.
- **Content:**
  - extract recorded levels exactly with overlay verification (`extract_levels.py`, IoU ≥ 0.99);
  - solve escape greedily (`solve_levels.py`), sliding and parking by BFS;
  - generate by adding pieces in reverse;
  - difficulty = dependency depth.
- **Meta:**
  - offline: hearts, coins, hints, skins;
  - locked: leaderboards.
- **Research:** extract → solve → play the solution; one deliberate mistake per level to measure the bump.
- **Spikes and V1:**
  - tech: 200 pieces under zoom;
  - V1: the recorded levels + generated levels to 100+.

### 10.10 Bus / car jam and queue games (Bus Jam, Car Jam, Screw Jam, many yarn games)
- **Rules to pin:**
  - coloured units sit on a grid;
  - a tapped unit with a free path (BFS through empty cells) walks to the active vehicle if the colours match, otherwise to the
    waiting area (N slots);
  - vehicles arrive in a fixed colour sequence, with a capacity;
  - a full waiting area fails;
  - tunnels and spawners, hidden units, locked cells.
- **Measure:** walk speed in cells/s and how units turn; boarding and seat fill; vehicle leave and arrive; waiting-slot hops; the
  blocked-tap feedback; the fail sequence; the camera.
- **Engine:** RealityKit for true perspective with many figures (limb entities animated per figure); otherwise SpriteKit with 4–8
  pre-rendered directions × walk frames.
- **Art:** our own low-poly SDF figures and vehicles.
- **Content:**
  - grid + colours + vehicle sequence + capacity;
  - a DFS/BFS solver over tap orders;
  - reverse construction from the vehicle sequence;
  - record the first ~20 exactly.
- **Meta:** offline: coins, boosters (undo, extra slot, shuffle, VIP), lives, stars.
- **Spikes and V1:**
  - tech: 60 walking units;
  - V1: the recorded 20 + generated to 60.

### 10.11 Pin pull and screw-the-planks (2D physics)
- **Rules to pin:**
  - pins slide out on a swipe (or tap); balls, liquid, gems or hazards fall;
  - grey balls turn coloured on contact; the win: N % in the goal; hazards (lava + water → stone);
  - planks hang on screws; a tapped screw goes to a colour box; a free plank swings and falls; the level is won when all planks
    are down.
- **Measure:** gravity (pt/s²), ball radius and count, restitution and friction; the pin slide-out; plank swing and angular
  damping; the unscrew spin.
- **Engine:** SpriteKit physics (≈ 200 circles). It isn't deterministic across devices, so validate statistically.
- **Art:** SVG bodies, pins and screws; liquids as metaball blobs (a threshold shader over soft dots).
- **Content:**
  - hand-authored bodies, joints, pins and goals;
  - validator: a headless scene runs the intended order 20× with jitter and must win ≥ 95 %; one wrong order must fail.
- **Meta:** offline: coins, skins, the level map.
- **Research:** take 60 fps clips and track balls by colour to fit gravity and restitution.
- **Spikes and V1:**
  - tech: 200 balls + the liquid look;
  - V1: the recorded ~20 + 40 designed.

### 10.12 Merge (Merge Mansion style)
- **Rules to pin:**
  - board size and locked cells;
  - the merge count and chain lengths;
  - generators: energy cost per tap, charges, cooldowns, drop tables;
  - orders that pay coins, XP or stars;
  - story tasks that spend stars on renovation;
  - energy regen and cap (timestamped);
  - the inventory, selling, and what happens when the board is full.
- **Measure:** the drag lift; the merge (fly-together, burst, pop); which free cell a generated item flies to; the order-complete
  animation; the energy bar; the info panel.
- **Engine:** SpriteKit for the board, inside a SwiftUI shell.
- **Art:** volume is the risk (dozens of chains × 8–15 items, plus renovation scenes). Count the chains area 1 needs and scope to
  them.
- **Content:**
  - chains;
  - generators with weighted drop tables (sample ≥ 100 taps per generator);
  - the scripted early orders, recorded exactly;
  - areas and tasks;
  - an economy-simulator bot proves there is no dead end and that the pacing matches the recording.
- **Meta:**
  - offline: everything local;
  - locked: events, leaderboards, co-op.
- **Research:** the chain info panel shows whole chains without progressing, so capture every one. Energy caps the session: never
  buy it.
- **Spikes and V1:**
  - art: one full chain;
  - tech: drag-merge and spawns;
  - V1: area 1's chains, orders and renovation.

### 10.13 Word (Wordscapes, Word Cookies)
- **Rules to pin:**
  - the wheel letters; answer slots in a crossword; the minimum length;
  - bonus words that fill a meter;
  - hints (verify their names); shuffle; the already-found feedback;
  - packs and their backgrounds.
- **Measure:** the letter-select pop; the line to the finger; the preview bubble; the bubble → grid letter flight (stagger, T);
  the wrong-word shake; the bonus flight; level complete; the pitch ladder per letter.
- **Engine:** a SwiftUI shell + Core Animation. The wheel line is a `CAShapeLayer` updated on the touch frame; `CAEmitterLayer`
  for confetti.
- **Art:** backgrounds as CC0 scenic photos (Wordscapes style) or our own SVG (Cookies style); the font match is critical.
- **Content:**
  - validity: a clearly licensed list (e.g. ENABLE);
  - answers: common words from a permissively licensed frequency list, with a licence file and a profanity filter;
  - the generator:
    1. take a seed word of 6–7 letters;
    2. find its sub-anagrams of ≥ 3 letters;
    3. pick answers by how common they are;
    4. lay out the crossword by backtracking;
  - validator: every answer can be formed, the grid is connected, no accidental adjacent words.
- **Language:**
  - the phone is Turkish, so the original may serve TURKISH puzzles;
  - at kickoff, set the game's own language to English, or ask the owner;
  - V1 content is English;
  - record the language every recording shows.
- **Research:** OCR the wheel; find answers with our dictionary; enter them with `/path` (§3.2). Without `/path` this genre
  cannot be played.
- **Spikes and V1:**
  - tech: the drag through letters and the fly-to-grid;
  - content: 50 generated levels that pass the validator;
  - V1: packs 1–2 as recorded + 200 generated levels.

### 10.14 Logic (Sudoku.com, Nonogram.com, Killer Sudoku)
- **Rules to pin:**
  - sudoku: givens, notes, erase, undo, hints, the mistake limit, auto-removed notes, highlights, tiers;
  - nonogram: clues, fill and X modes, drag-fill, mistake hearts, auto-X on finished lines, the picture reveal.
- **Measure:** highlight colours and T; the digit pop; conflict red; the completion wave (direction, stagger); the
  puzzle-complete sequence; the timer format; the input order.
- **Engine:** SwiftUI with Canvas or Core Animation. Crisp text matters more than sprites.
- **Art:** flat vector; the digit and clue font match is critical; nonogram pictures are our own pixel art (5×5 to 20×20).
- **Content:**
  - sudoku: a random full grid, with givens removed while the solution stays unique (backtracking with a count limit of 2), and
    a technique grader calibrated by OCR-ing ≥ 10 of their puzzles per tier;
  - nonogram: a line solver plus probing for uniqueness; reject non-unique pictures.
- **Meta:**
  - offline: a daily calendar with trophies, seasonal events with bundled content, stats;
  - locked: leaderboards.
- **Research:** OCR → solve → enter by taps. Only ever enter solved values, because mistakes cost hearts.
- **V1:** every tier with a generator, the dailies, 60 of our own nonogram pictures.

### 10.15 Bubble shooter
- **Rules to pin:**
  - the hex grid (offset rows);
  - current and next bubble, swapped by a tap;
  - straight shots that bounce off the side walls and snap to the nearest free hex next to the bubble they hit;
  - ≥ 3 connected pop; anything cut off from the top falls;
  - the queue colours (only colours still on the board? verify);
  - the shot limit, goals, specials, boosters; the descending ceiling (if any).
- **Measure:** shot speed (pt/s); the aim line (dot spacing, length, how many bounces it previews); the snap; the pop stagger (BFS
  distance × Δt); the fall of cut-off bubbles; the reload and swap; the minimum aim angle.
- **Engine:** SpriteKit, with collisions done analytically in the core (a ray against circles, no physics engine) so it stays
  deterministic.
- **Art:** glossy bubbles pre-rendered from 3D; our own characters.
- **Content:** the hex layout + shots + colour set; bot: an angle search in 0.5° steps through the real core, with bands.
- **Research:** capture the aim line during a 3–4 s swipe; learn whether releasing the finger fires.
- **V1:** the first ~40 levels.

### 10.16 Hexa sort
- **Rules to pin:**
  - the hex board, with locked cells that unlock;
  - three offered stacks: dealt after all three are placed, or one at a time?
  - **the transfer rule**: after a placement, which neighbour gives to which, in what order among several neighbours, and
    whether it chains. Pin it with deliberate test placements filmed at 60 fps before any spec;
  - the clear threshold (verify);
  - goals; a full board fails; boosters (hammer, swap, shuffle).
- **Measure:** the per-tile flip transfer (arc, flip, T, stagger); the clear (shrink, pop, count-up); the delay between chain
  steps; the drag lift and snap; the deal slide-in.
- **Engine:** tiles flip in depth, so lean toward RealityKit (hex prisms, the proven stack). Use SpriteKit flip frames only if the
  spike shows they read the same.
- **Art:** SDF hex prisms in sampled colours.
- **Content:** mask + goal + stack-generator parameters fitted to ≥ 200 logged stacks; a Monte-Carlo bot with bands.
- **V1:** the first ~40 levels.

### 10.17 Knit / yarn games
- **Identify the sub-mechanic on levels 1–5:**
  - a queue → 10.10;
  - a sort → 10.8;
  - an unravel (pull a yarn free when nothing crosses it) → 10.9, with a 2.5D crossing order.
- **What is specific:**
  - rope rendering: a spline mesh strip with a twisted-strand texture, never `SKShapeNode`;
  - spool winding as a helix (measure the turns and T);
  - knitted-picture fill as V-stitch sprites;
  - procedural wool and knit textures (numpy fibre noise plus a stitch pattern).

### 10.18 A game that fits none of these
Before Phase 2, write a mini-entry in PLAN.md with the same headings, borrowing from the closest entries. Promote it into this
file once it has worked.

---

## 11. Workflow-script rules (the Workflow tool)

- Load the `workflow-authoring` skill once, then write scripts inline, or edit a copy and pass its `scriptPath`.
- **The templates in `tools/gameprompt/workflows/` are Match Factory's scripts exactly as they ran:** worked examples, not
  parameterised code.

  | Template | Phase |
  |---|---|
  | `1-research.js` | research |
  | `2-spec.js` | specs |
  | `3-art-round1.js`, `3b-art-round2.js` | art |
  | `4-build.js` | build DAG |

  Keep their SHAPE: phases, the COMMON preamble, schemas, `brief()`, `.filter(Boolean)`, resource assignment, the slot DAG.
  Better still, read the constants from `args` (`const { ROOT, SLUG, GAME, BUNDLE, SIM_A, SIM_B, BRIEF, SCOPE } = args`). Then
  **rewrite every role prompt** from your research and your §10 entry. Specifically:
  - **All five:**
    - `meta.name` (`matchfactory-*` → `<slug>-*`), ROOT, the brief (the owner's current sentence, verbatim), stale disk
      numbers;
    - simulator names and UDIDs (`MF Spike FFE58FD1-…`, `MF Main B8F323DC-…` → yours);
    - add the PRECEDENCE block to every COMMON;
    - add "call the phone by its absolute path" to every phone prompt.
  - **`1-research.js`:**
    - the bundle id `net.peakgames.match`, the Turkish L1 tutorial text, "timers start at 5:00", the tap-3-identical loop and the
      tray/merge capture list → your genre loop;
    - the stop rule "level 12 or ~120 minutes" → the §14 minimum;
    - "20–30 s chunks" → **≤ 12 s**;
    - the `sleep 1.5` recording recipe → the log-poll recipe;
    - the ART spike builds a pipeline from scratch → copy it (§3.5);
    - the RealityKit TECH spike → your §8.1 engine;
    - the ANALYST → §5.4, using `mfx`;
    - split it into W-phone and W-desk (§5.1).
  - **`2-spec.js`:** the whole V1 SCOPE block, the MF component and event lists, `com.manycode.matchfactory`, "3 finished
    items", "a second phone session is playing levels 14+" → yours. Add the §6.1 section contract to the architecture prompt,
    and add the consistency agent (§6.2).
  - **`3-art-round1.js` / `3b-art-round2.js`:**
    - all the lane item lists, PLAYER2's MF specifics, "tray box ~48x58 pt, 1 unit = ~67 pt", "83 round-1 items", the shot
      numbers and the MF fixes → yours;
    - add the identity pass (§7.1 step 0) and a commit point before the director;
    - for 2D and vector games, replace the lanes (§7.1).
  - **`4-build.js`:**
    - the MF names ("MFCore C1", "R1/R5", "CameraRig/Lanes/Visibility", "SPEC-motion-audio §19-§22", "SPEC-ui A-01…A-90",
      "UIArt enum", the booster icons) → your spec's;
    - its UI-ART line "recipes under art/pipeline/items/ui_*.py" is wrong: they go in `art/ui/recipes/`;
    - it ends at V2/V3: write your own `5-finish` workflow (fix loops, recast, D1, install).
  - **After editing:**
    `grep -nE 'matchfactory|Match Factory|peakgames|MF (Main|Spike)|FFE58FD1|B8F323DC|MFCore|rubber|7 slots' <script>` must
    print nothing except deliberate exemplar paths.
- **Always** `.filter(Boolean)` parallel results, and guard `r ? … : fallback`. A null from a dead agent once crashed a whole
  workflow.
- **Every agent's COMMON preamble contains:**
  - the owner's sentence;
  - "read SPEC.md / PLAN.md first";
  - the copying line;
  - PRECEDENCE;
  - the machine limits;
  - "touch only your files";
  - "do not git commit";
  - "write progress to files as you go";
  - the genre playbook.
- **Structured results.** Use a schema: files, summary, open issues, requests. Build work packages add acceptance items with
  evidence.
- **Resources explicit:** the simulator UDID, whether the agent has the phone, its DerivedData path.
- **Resume, don't restart.** Every result gives a `runId` and the persisted script path; relaunch with
  `Workflow({scriptPath, resumeFromRunId})` to reuse cached agent results.
  - Journals live at `~/.claude/projects/-Users-yago-Downloads-app-factory/<session-id>/subagents/workflows/wf_<id>/journal.jsonl`,
    with `started` and `result` lines per label, next to each agent's transcript.
  - Agents write to disk as they go, so a retried agent resumes rather than restarts. Its prompt says: "files from an
    interrupted run may exist: read them, keep what is good, finish what is missing".
- **Stop at a stage boundary:** watch the transcript folder for the next agent's role with a background Bash loop, then
  `TaskStop`.

---

## 12. File layout per game
```
apps/<slug>/
  PLAN.md            NOW block, owner's sentence, names/resources, genre playbook, timeline, status log, decisions, TODO ledger
  SPEC.md            master prompt: copying line, PRECEDENCE, precedence table, reconciliations, machine rules
  research/          levels.md flows.md items.md meta.md fail.md boosters.md motion.md sounds.md web-research.md clips-needed.md
                     phone-session<N>-progress.md  store/ kickoff/ reference/ bot/ motion-tools/   (heavy dirs gitignored)
  design/            SPEC-{gameplay,ui,motion-audio,architecture}.md CONSISTENCY.md REUSE.md levels.json ui-tokens.json images.json
                     ui-crops/ fonts/ tools/ tech-spike.md
  art/               pipeline/ out/ ui/{recipes,src,tools,out} lanes/ PIPELINE.md STYLE.md REVIEW.md ID-MAP.md
  App/ Packages/<Core>/ Tests/ UITests/ tools/ project.yml
  build/             (ignored) per-slot DerivedData, evidence, compare/, bench/, health.log, blocked.md
```

---

## 13. Pitfalls we already paid for

**Autonomy and infrastructure**
- **Too many builds at once.** Five build agents plus three simulators on this Mac meant 17 GB of swap; every agent stalled
  and the workflow died. → Two slots per machine (counting other sessions), memory checks, and `.filter(Boolean)`.
- **Disk.** Swap, simulators and captures ate it silently, down to 295 MB free at one point. A full disk shows up as codesign or
  linker errors. → A 15 GB start, `df -h /` before heavy steps, the cleanup list, the watchdog.
- **Nobody told the owner.** A crash went unreported until the owner asked "what is the problem, why did you not do". → The
  watchdog, and telling the owner in the same turn.
- **A timer ran out.** A 12 h caffeinate expired mid-run → 48 h, plus the watchdog.
- **Permission approvals don't carry over between chats.** → The pre-flight rules, and an agent smoke test at kickoff.
- **The camera prompt returns after every PhoneCapture rebuild.** → Never rebuild it unattended.
- **Queued taps hit an offer button in a fail state.** → The bot guard; never batch near a fail state.
- **`xcrun simctl shutdown all`, run by the orchestrator during cleanup,** killed another session's simulator. → Only your own
  UDIDs.
- **Nobody asked for 10-language localisation, and the owner cancelled it.** → Never add scope.
- **A long phone session sat in the same workflow as short work,** so nobody reacted for hours. → Separate workflows.

**Research**
- Hint glows, dim overlays and a dimmed iOS alert tinted crops by 20–40 %. → Take colours from untinted runner shots only.
- A single angle misidentified items (a harp became a "trumpet"; blue_case was blue_radio from the back). → The ≥ 2-shot
  identity pass.
- Long USB clips drop frames and have a variable frame rate. → ≤ 12 s clips and `mfx` timestamps.
- Music masks sound effects. → Music-off clips and event averaging.
- The life refill was guessed at "~25 min"; it was exactly 30:00 from the level start. → Timestamps across several refills.
- A pick-on-release formula was first fitted from touch-down. → Establish the input model first.
- Web sources disagreed (help centre vs the game). → Source precedence (§5.5).

**Art**
- A double-applied scale made L1 items 15 % too big. → Author at base size.
- Only the top 4 hull facets were kept, so cans and drums spawned standing. → Grouped stable poses.
- Abutting parts made slivers and seams. → One part plus a texture for colour zones.
- Fork multiprocessing deadlocked numpy. → Spawn.
- RealityKit and USD:
  - RealityKit renders in Display P3; read as sRGB, the colours look washed out;
  - UsdPreviewSurface `ior` drives specular;
  - clearcoat adds a whitish veil;
  - an orthographic camera plus automatic shadows barely works → use a narrow perspective camera.
- Outline shells need closed, manifold meshes.
- Lane self-grades were too kind, and pre-review recipes were only in scratch. → Director grades only; commit before review.

**Engine**
- ARView's hidden tap recognizer cancels quick taps. → `cancelsTouchesInView = false`.
- ARView always tone-maps. → An inverse-LUT post-process (worst about 7/255).
- The first material draw stalls 0.5–3.5 s, and the first launch after install is slower still. → Warm up behind the loading
  screen, and do a throwaway launch before UI suites.
- Physics sleep isn't "settled". → A velocity threshold. Round items roll → angular damping.
- Boot hang: `prepare()` awaited the layout of a view that wasn't in a window. → Never await layout off-window.
- Core Animation:
  - disable implicit actions;
  - `beginTime = 0` means "now";
  - `.linear` isn't exact, so use `timingFunction = nil`;
  - to freeze for captures, `layer.speed = 0` with `timeOffset`;
  - the exit ray must be long enough.
- SpriteKit: a zero-size scene on first present; a scene re-created via `.id()` double-presents; hitches from `SKShapeNode`,
  `SKEffectNode` or `SKLabelNode` in play, or from textures not preloaded.
- A new `.metal` file without re-running xcodegen → `CustomMaterial` silently falls back.
- SwiftUI "unable to type-check this expression" under memory pressure → small view bodies, explicit types.
- Shared-tree builds broke on others' half-edits. → Keep files compiling; iso-copy builds.

**Swift, iOS, simulator**
- `@AppStorage` doesn't publish through Observation → keep game state in the core's JSON store.
- `String`-typed helpers and custom components skip the strings table → `LocalizedStringKey`, plus coverage tests over your
  own components.
- Turkish reorders format arguments → positional `%1$@`; the validator compares argument ORDER.
- Array plist keys need a base plist.
- `simctl launch` drops arguments while the app runs → `--terminate-running-process`. Logs under `~/Downloads` are denied by the
  sandbox → the simulator's own tmp. xcodegen needs a mutex.
- The simulator inherits the Mac's region (comma decimals).
- The owner's iPhone 15 and the Simulator are both 60 Hz → 120 Hz is unverified until a ProMotion device.
- The brand leaked through a shipped file name (`MFDisplay-Regular.ttf`) → neutral code prefixes.
- The local `.storekit` doesn't apply outside the scheme's Run action → FakeStore.
- Never `git clean -x/-X` (gitignored, owner-approved binaries), never `git stash -u`/`checkout main` (untracked tools).

---

## 14. Definition of done (check every line before the final message)
- [ ] **Research** complete (heavy captures gitignored), at the genre minimum:

  | Genre (§10) | Minimum captured on the phone |
  |---|---|
  | Match-3, tap-blast, bubble | ≥ 40 levels (bot), every obstacle met by then, wiki levels cross-checked |
  | Tile match 2D/3D, mahjong, hexa, bus jam | ≥ 20 levels (≥ 12 if timed), every booster used once |
  | Sort, escape, unblock, parking, pin pull | ≥ 30 levels |
  | Block puzzle | ≥ 300 logged deals, ≥ 3 full games, adventure ≥ 10 levels if present |
  | Jigsaw | every piece count opened, ≥ 3 puzzles completed, snap threshold and lift measured |
  | Word | ≥ 30 levels (letters, answers, layout, language noted) |
  | Logic | ≥ 10 puzzles per tier OCR'd and graded, every input mode recorded |
  | Merge | the whole first area: orders, every chain via the info panel, energy regen timed |

  Also: every home, meta and menu screen captured; the FTUE recorded (or its fallback noted).
- [ ] **Specs:** four specs + CONSISTENCY.md + SPEC.md, committed.
- [ ] **Art:** every asset in shipped levels graded A/B by the director (0 C) in REVIEW.md; UI art complete with side-by-side
  sheets; **0 proxies or placeholders** (the boot log prints "N kinds, N with art, 0 proxies").
- [ ] **Audio:** sounds and music synthesised by us; the checker and its self-test pass; in-app levels measured.
- [ ] **Content:**
  - every level has a `source`;
  - recorded levels are overlay-verified;
  - deterministic levels are solver-proved;
  - stochastic levels are within their bands, with golden seeds;
  - designed levels are calibrated.
- [ ] **Build and tests:**
  - build green; core tests green; mutation checks all CAUGHT; UI suites green twice in a row;
  - autoplay completes every level from a fresh install;
  - no dev placeholder string in the Release binary (`strings <App>.app/<App> | grep -c "not installed yet"` = 0, with a control
    string > 0);
  - Release data only.
- [ ] **Fidelity:** side-by-side findings closed or explained (≤ 3 rounds; no open P0). Performance budgets met in the
  simulator and **on the phone** at 60 Hz.
- [ ] **On the phone:** installed from a clean uninstall; boots to first run without arguments; the shop works via FakeStore;
  LOOKED at via `phone shot`.
- [ ] **Ledger:** the PLAN.md TODO ledger is empty, or every open item is in the final report.
- [ ] **Committed:** everything on `build/<slug>` (never on main unless asked); one line appended to `PROJECT_LOG.md`.
- [ ] **End state (§9.6):** runner stopped, phone lock released, watchdog, heartbeat and caffeinate stopped, simulators shut
  down, scratch cleaned.
- [ ] **Final message:** what the owner can play now, comparison images, decisions, gaps, accidents, next steps.
