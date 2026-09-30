# Arrow Out — game template

This repository is the starting point for every new game. It holds **Arrow Out**, a finished native Swift iOS puzzle game
(a 1:1-quality copy of *Maze Out!* by Grand Games), together with every tool, script and written lesson that took it from
an empty folder to an App Store submission. To make the next game, copy this repository (see
[Start a new game](#4-start-a-new-game-from-this-repo)), then follow `GAMEPROMPT.md`.

Written for two readers: the owner (plain words, what to click, what to run) and a future Claude Code session (exact
paths and commands). Everything named here was checked to exist when the repo was put together (2026-09-30). The few
things that could not be checked are listed in [What was not verified](#what-was-not-verified).

**Contents**
1. [What this is, and what is NOT in it](#1-what-this-is-and-what-is-not-in-it)
2. [Map of the repo](#2-map-of-the-repo)
3. [Build and run](#3-build-and-run)
4. [Start a new game from this repo](#4-start-a-new-game-from-this-repo) (with the rename checklist)
5. [What to keep and what to replace](#5-what-to-keep-and-what-to-replace)
6. [The store pipeline, in order](#6-the-store-pipeline-in-order)

---

## 1. What this is, and what is NOT in it

**In it**
- `apps/mazeout/` — the whole Arrow Out game: Swift source, the pure-Swift game core, 150 designed levels plus an endless
  level generator, all art (and the tools that made it), synthesised sounds and music, 13 languages, unit + UI tests,
  release gates, the store texts and screenshots for 13 App Store languages, and the full planning record (`PLAN.md`,
  `SPEC.md`, `design/`). The folder is called `mazeout` (the working name) while the product is `ArrowOut` / "Arrow Out".
- `scripts/` — the factory's App Store Connect, RevenueCat, signing and screenshot tools. The same scripts submitted about
  30 other apps.
- `tools/phonedriver/` — lets Claude drive the owner's USB iPhone (tap, swipe, screenshot, record) to study the original game.
- `tools/gameprompt/` — the workflow templates and shell snippets that `GAMEPROMPT.md` refers to.
- `GAMEPROMPT.md` and `GAMEPROMPTMAX.md` — the step-by-step manual for "make a 1:1 copy of game X" (see §5).
- `docs/lessons/` — 117 notes of pitfalls already paid for (signing, App Store Connect, RevenueCat, Meta SDK,
  localisation, screenshots, simulator and phone gotchas). Start at `docs/lessons/README.md`.
- `CLAUDE.md` (the template's working rules) and `docs/ROADMAP.md` (the template plan, decisions and status). The
  subscription-app factory's rules, its DESIGN/ASO notes and its `app-factory` skill are kept in `docs/archive/` and do
  not apply to games.

**Deliberately NOT in it**
- **Secrets.** No `.env` (App Store Connect key id and issuer, RevenueCat secret key, Meta client token, Gemini key,
  Apple web session), no `keys/` folder (the App Store Connect `.p8` key, the Distribution certificate and its private
  key, the signing keychain password), no Apple login cookie (`~/.fastlane/spaceship/…`). `.gitignore` blocks all of
  them. You recreate them from `.env.example` (§3).
- **Build outputs** (`apps/mazeout/build/`, about 17 GB on the owner's Mac: DerivedData per simulator slot, archives,
  evidence, captures). The Xcode project `ArrowOut.xcodeproj` is generated, not stored (§3).
- **The reference material of the original game** (about 4.3 GB): phone recordings, screenshots, frame dumps and sound
  references. It stays only on the owner's Mac under `apps/mazeout/research/` and is git-ignored (see
  `apps/mazeout/.gitignore`). What *is* in git from `research/` is the written notes, the analysis tools and the level
  data read from the recordings.
- **The phone build helper** is included as `apps/mazeout/tools/owner-phone.sh` (snapshot the tree, build the Measure or
  Release configuration for the owner's iPhone, install it). Its paths are absolute (`/Users/yago/Downloads/app-factory`);
  change them with the rest of the rename checklist.
- **The rest of the factory:** the other apps, the subscription-app `template/` folder, the real `ideas.yaml` queue,
  `ROUTINEAPPS.MD`, `PROJECT_LOG.md`, `setup.sh`, `factory.sh`. A few scripts and rules still mention them (listed in §2).
  `ideas.yaml` exists here only as an empty list, because `scripts/asc_submit.py` always opens it.
- **The two earlier game copies** `GAMEPROMPT.md` cites as exemplars (`apps/arrows`, `apps/matchfactory`; they are on the
  factory repo's `build/matchfactory` branch). Arrow Out already carries adapted copies of their tools;
  `apps/mazeout/design/REUSE.md` lists what came from where.

**Where Arrow Out stands:** App Store Connect app id 6816880848, bundle `com.manycode.arrowout`, version 1.0.0, 12
consumable in-app purchases. `apps/mazeout/` is meant to be the final committed tree of the version 1.0.0 App Store
submission (it is copied in after that submission). The owner-facing history is in `apps/mazeout/PLAN.md` (status log
at the bottom) and `apps/mazeout/design/publish/release-plan.md`.

---

## 2. Map of the repo

```
README.md               this file
GAMEPROMPT.md           the manual: build a 1:1 copy of a mobile puzzle game end to end (Workflow tool, "ultracode")
GAMEPROMPTMAX.md        the same manual for /effort max, run with parallel background subagents instead of workflows
CLAUDE.md               working rules for every Claude session here (read docs/ROADMAP.md next)
machine.env.example     this Mac's simulator/phone ids + tool paths -> copy to machine.env (git-ignored)
.env.example            every key the tools read, empty, with where to get it -> copy to .env
.gitignore              secrets, build outputs, generated Xcode projects
ideas.yaml              empty list on purpose (scripts/asc_submit.py opens it; see the comment inside)
requirements.txt        Python packages for scripts/ (pip3 install -r requirements.txt)
requirements-tools.txt  numpy/scipy/Pillow for the store-frame, audio, copygate, compare tools
.github/workflows/ci.yml  CI: Linux content/store checks, core swift test, app build + unit tests (macOS)
.claude/
  settings.example.json permission rules, incl. the two phone rules -> copy to .claude/settings.local.json and fix the paths
apps/
  mazeout/              Arrow Out, the whole game (below)
docs/
  ROADMAP.md            the template plan: phases, decisions, status log
  archive/              the subscription-app factory's rules, DESIGN/ASO notes and app-factory skill (not for games)
  lessons/              117 pitfall notes + README.md (grouped index) + MEMORY.md (flat index)
scripts/                store, payment, signing and image tools; run them from the repo root (table below)
tools/
  phonedriver/          phone (the CLI), start-runner, the XCUITest runner app (project.yml, Host/, UITests/), capture/
  machine.sh, machine.py  load machine.env for the shell / Python tools
  gameprompt/           workflows/1-research.js … 4-build.js (Workflow tool templates), snippets/*.sh, rng_ref.py
```

### apps/mazeout (Arrow Out)

```
project.yml             THE project definition (xcodegen). Targets ArrowOut, ArrowOutTests, ArrowOutUITests;
                        configs Debug / Release / Measure; packages PathCore, RevenueCat 5.89.0, FacebookSDK 18.1.1 (FacebookCore only)
PLAN.md                 the run's log: owner's words, names and resources, decisions, TODO ledger, status log
SPEC.md                 the master prompt every agent read first: copying line, precedence, the numbered rulings (§5)
App/
  GameApp.swift, AppModel.swift, Brand.swift (the product name has ONE source: PC_BRAND_NAME in project.yml)
  Board/                the board: arrows, exit movement, hit testing, obstacles (doors, pipes, corners, elevators, keys),
                        painters and layers, intro build-in, BoardLab (a debug playground of boards and scenarios)
  Game/                 GameController + directors: tutorial, FTUE, fail flow, win, boosters, events, unlocks, rating
                        prompt, notification prompt; AutoPlayer (plays levels for tests)
  Shell/                everything around the board: RootView, Router, LoadingScreen, Home, HUD, Popups (pause, settings,
                        level failed, out of time, no lives, booster buy, rewards, win panel …), Shop (StoreService =
                        StoreKit 2, RevenueCatObserver, StoreConfig), Social (event screens + leaderboards), Profile,
                        Components (buttons, text, tokens, raster cache), ShellLab (debug gallery)
  FX/                   confetti, coin fly, fireworks, sparkles, the win logo sequence, FrameWatch (frame-time probe)
  Audio/                AudioEngine, SoundBank, MusicPlayer, AudioCues, Haptics
  Support/              LaunchArgs (-pc.* debug switches), Log, MetaAds (Meta attribution), PlayerStore (save), Tuning,
                        PerfMonitor, LatencyProbe
  Contracts/            the interfaces the parallel build lanes agreed on (Board / Shell / Audio / Presentation)
  Resources/            Assets.xcassets (app icon, colours), Fonts, Levels (150 level JSONs), Localizable.xcstrings +
                        InfoPlist.xcstrings (13 languages), Strings/ (the TSV sources of those), Sounds, Music, Social
                        (name lists), StoreKit/ArrowOut.storekit (local test store), Tuning/ (game.json, rules.json, ui.json,
                        board.json: every number a designer may change)
Packages/PathCore/      the pure-Swift game core (Foundation + CoreGraphics only; tools/core.sh enforces it; tested on
                        macOS with no simulator): Grid, Model, Rules, Solver, Motion, Economy (coins, lives, boosters,
                        ShopCatalog), Events (Streak Race, Claw Challenge, Balloon Rise, Rocket Race, Sky Jump, Weekly
                        Contest …), Content (Generator = endless levels, Validator, LevelProvider), Persistence, Random
                        (PathRandom, deterministic), Session, Social; plus the `pclevels` command-line tool
Tests/                  unit tests hosted in the app (Tests/AppTests: store release, Meta events + SDK linkage, brand,
                        localisation, strings coverage, levels bundle, tuning …)
UITests/                18 XCUITest files: flows, game, fail flow, boosters, shell, social, events rotation, tracking prompt …
tools/                  slot.sh (the two simulators), gen.sh, build.sh, run.sh, test.sh, core.sh, bench.sh;
                        meta_token.py + meta_dashboard_check.py (Meta client token, never printed); sync_art.sh;
                        bench/ (bench.py, release_gates.sh, meta_sdk_check.py, hudocr.swift); capture/ (capture.py +
                        manifest.json: scripted screenshots); store/compose.py (App Store frames); release/ (meta.py:
                        store texts -> fastlane, audit, IAP check; loc.py; aso_research.py); strings/ (TSV -> xcstrings,
                        coverage, reviews); levels/ (lvtool, content_tests.sh); audio/ (synthesis + signal checks);
                        compare/ (side-by-side fidelity vs the original); watchdog.sh, memguard.sh, cleaner.sh,
                        heartbeat.sh (overnight babysitters); copygate.py (never too close to the original's art)
art/                    PIPELINE.md (how to add any graphic), STYLE.md, MANIFEST.json (every graphic: id, route, size,
                        status), ID-MAP.md, pipeline/ (SDF -> mesh -> USDZ + the mfrender offscreen renderer), ui/ (recipes,
                        src SVG generators, tools, out/ = shipped UI rasters, code/GlossyChrome.swift), out/ (shipped 3D
                        renders), lanes/, review/ (comparison sheets the owner judged)
design/                 SPEC-gameplay / -ui / -motion-audio / -architecture / -social .md, CONSISTENCY.md, REUSE.md,
                        LEVELS.md + levels.json + level-order.json, tools/ (gen_levels.py = the level generator,
                        build_levels.py, validate_levels.py, …), ui-tokens.json, fonts/ + fonts.md, captions/ (screenshot
                        captions x13), keywords.json, social/, publish/ (release-plan.md, PLAN-P.md, iap.json = the IAP
                        catalogue, store/<locale>.json = the store texts, l10n/, palette/, verify/ = release evidence)
research/               in git: the written research (levels.md, flows.md, meta.md, sounds.md, economy.md …), level data
                        read from the recordings (levels/*.json), the research tools. NOT in git: the 4.3 GB of media
fastlane/               Appfile, Deliverfile (Games / Puzzle / Casual), Fastfile (lanes below), metadata/ (13 locales +
                        review_information + app_privacy_details.json + app_rating_config.json + copyright.txt),
                        screenshots/ (13 locales x 5 frames)
```

### scripts/ (run from the repo root)

| Script | What it does | Used for Arrow Out? |
|---|---|---|
| `asc_consumables.py` | creates consumable IAPs from a catalogue JSON: 13 localisations, all territories but China, USA price only, review screenshot, then reads everything back (`--dry-run`, `--self-check`) | yes |
| `rc_consumables.py` | RevenueCat app + consumable products + a non-current offering; writes the public `appl_` key into a Swift file | yes |
| `signing_setup.py` | device-free signing: Distribution certificate, App Store profile, dedicated keychain (`--bundle`, `--profile-name`) | yes |
| `asc_keywords.py` | pushes per-locale keywords from `apps/<slug>/design/keywords.json` straight to App Store Connect | yes |
| `asc_screenshots.py` | uploads `apps/<slug>/fastlane/screenshots/<locale>/` through the API (clears each set first) | yes |
| `asc_submit.py` | the submit: content rights, free price, build attach, IAP items, `--uses-idfa`, review submission, read-back (`--dry-run`) | yes |
| `asc_new_version.py` | opens a new version record for an update | for updates |
| `fastlane_apple_fix.rb` | a patch loaded through `RUBYOPT` when `fastlane create_app` breaks on Ruby 4 / Apple's moved sign-in key (see its header) | only if needed |
| `svg2png.swift`, `textpng.swift` (+ `.bin/textpng`), `flatten_icon.swift` | SVG -> PNG (WebKit), text -> PNG (CoreText, any script), flatten an icon | helpers |
| `gen_image.py` | Gemini image generation (needs `GEMINI_API_KEY`) | no |
| `asc_iap.py`, `rc_setup.py`, `asc_review_assets.py` | the same jobs for SUBSCRIPTION apps (asc_iap reads prices from `ideas.yaml`) | no |
| `meta_sdk.py` | wires the Meta SDK into a factory utility app (Arrow Out was wired by hand: project.yml + `App/Support/MetaAds.swift`) | no |
| `capture_shots.py`, `capture_locales.sh`, `make_screenshots.py`, `fill_locale_urls.py`, `bug_check.py` | the utility-app screenshot and QA pipeline | no (Arrow Out has its own in `apps/mazeout/tools/`) |
| `new_app.sh`, `idea.py`, `routine.sh`, `routine_next.py`, `routine_done.py`, `install_routine.sh`, `launchd/*.plist` | the factory's queue and daily routine; they need `template/`, a real `ideas.yaml` and `ROUTINEAPPS.MD`, which are not here | no |
| `package.sh` | zips the WHOLE repo including `.env` and `keys/` (for moving to another Mac). The zip holds live secrets: keep it private | careful |

---

## 3. Build and run

### Prerequisites (one time per Mac)
- **macOS + Xcode 26** (Arrow Out was built with Xcode 26.0.1; the app targets iOS 18.0; the test simulators were
  iPhone 16 on iOS 26.0). Then `xcode-select --install`.
- **Homebrew**, then `brew install xcodegen fastlane`. On the owner's Mac both are small wrapper scripts in `~/.local/bin`
  (xcodegen 2.45.4; fastlane 2.240.1 is the version the Fastfile comments name). `apps/mazeout/tools/gen.sh` looks for
  xcodegen in `$XCODEGEN`, then `PATH`, then `~/.local/bin/xcodegen`.
- **Python 3** (3.14 on the owner's Mac) and the script packages: `pip3 install -r requirements.txt`
  (pyjwt, cryptography, certifi, requests, pyyaml, Pillow, arabic-reshaper, python-bidi), plus
  `pip3 install -r requirements-tools.txt` (numpy, scipy, Pillow) for the store-frame composer, audio synthesis, copygate,
  compare and level-render tools.
- **Only for making new 3D / rendered art:** a separate virtual environment, which `apps/mazeout/art/PIPELINE.md` calls
  `PY=~/.venvs/mf3d/bin/python`, with numpy, scipy, scikit-image, trimesh, fast-simplification, usd-core and Pillow
  (`python3 -m venv ~/.venvs/mf3d && ~/.venvs/mf3d/bin/pip install numpy scipy scikit-image trimesh fast-simplification usd-core pillow`).
  The font tools also use `fontTools` (`pip3 install fonttools`).
- **Only for scripted screenshots** (`tools/capture/capture.py` taps): the `axe` binary bundled with XcodeBuildMCP, or set `AXE`.

### Secrets: `.env` and `keys/`
1. `cp .env.example .env` and fill it in. Every line says what the key is and where to get it. Never commit `.env`.
2. `mkdir -p keys` and put the App Store Connect key there (`keys/AuthKey_<KEYID>.p8`); set `ASC_KEY_PATH=keys/AuthKey_<KEYID>.p8`.
3. `keys/signing/` is created by `scripts/signing_setup.py` (certificate, private key, keychain password). When you move
   to a new Mac, copy the old Mac's `keys/signing/` over instead of creating a new certificate (Apple allows only a few).
4. The Apple web session (needed only by `fastlane create_app` and `fastlane upload_privacy`) comes from
   `fastlane spaceauth -u <your Apple ID>`: the OWNER types the password and the 2FA code. It lasts at most 30 days
   (see `docs/lessons/apple-session-30-days.md`).

All tools find `.env` at the repo root: the Python scripts through their own parser, the Fastfile through
`Dotenv.load("../../../.env")`, and `apps/mazeout/tools/meta_token.py` by walking up to the first folder that holds both
`.env` and `apps/`. So keep this layout: `<repo>/.env`, `<repo>/keys/`, `<repo>/apps/<slug>/`.

### The two simulators
`apps/mazeout/tools/slot.sh` maps two simulator slots, A and B, to this Mac's simulators; build, run, test, bench and
capture all go through it, so two agents never share a simulator. The UDIDs (and the research phone's ids) live in ONE
git-ignored file, `machine.env` at the repo root (`cp machine.env.example machine.env`; an environment variable of the
same name wins). On a new Mac, create two simulators and put their UDIDs in `machine.env`:
```
xcrun simctl create "Game A" "iPhone 16" com.apple.CoreSimulator.SimRuntime.iOS-26-0
xcrun simctl create "Game B" "iPhone 16" com.apple.CoreSimulator.SimRuntime.iOS-26-0
```
(`xcrun simctl list runtimes` shows the exact runtime name on your Mac.)

### Generate the project, build, run
All `apps/mazeout/tools/*.sh` scripts find their own folder, so they run from anywhere.
```
sh apps/mazeout/tools/gen.sh              # project.yml -> ArrowOut.xcodeproj (+ the 13 knownRegions), under a lock
apps/mazeout/tools/build.sh A             # Debug build for slot A into apps/mazeout/build/dd-A
apps/mazeout/tools/run.sh A               # install + launch on slot A; console log: apps/mazeout/build/run-A.log
apps/mazeout/tools/run.sh A -pc.level 32 -pc.go level     # debug launch switches use the -pc. prefix (App/Support/LaunchArgs.swift)
```
Run `gen.sh` again after adding, removing or renaming any file. Opening `apps/mazeout/ArrowOut.xcodeproj` in Xcode also
works once it is generated (the `ArrowOut` scheme runs Debug with the local StoreKit test store).

**Configurations** (from `project.yml`):
- **Debug** — everything, incl. the measurement harness (`App/Shell/GlitchRun.swift`, `App/FX/FrameWatch.swift`) and the
  BoardLab lab fixtures. Runs without any Meta token (Meta stays in a log-only mode).
- **Release** — the store build: the measurement harness (`#if DEBUG || PC_MEASURE`), the development placeholders and
  the lab fixtures (`lab_L*.json`) are left out.
- **Measure** — Release's exact settings plus `PC_MEASURE`, which compiles the frame/glitch measurement harness back in.
  For performance numbers only (`CONFIG=Measure apps/mazeout/tools/build.sh A`); never uploaded.

**The Meta client token (by design, a Release build FAILS without it).** The token is read only from `.env`
(`META_CLIENT_TOKEN`). `tools/meta_token.py check` runs as the target's first build phase and stops a Release or Measure
build when the token is missing or malformed; `tools/meta_token.py inject` writes it into the *built* Info.plist only,
never into a tracked file, and never prints it. `python3 apps/mazeout/tools/meta_token.py status` tells you whether
`.env` has a usable token. For an internal Release build without a token (never for the store),
`PC_META_VERIFICATION_BUILD=1 CONFIG=Release apps/mazeout/tools/build.sh A`; the fastlane lanes refuse to run with that
variable set.

### Tests and checks
```
apps/mazeout/tools/test.sh A                                  # unit + UI tests on slot A (UI suites must pass twice in a row)
apps/mazeout/tools/test.sh A -only-testing:ArrowOutTests      # unit tests only
apps/mazeout/tools/core.sh                                    # PathCore on macOS (swift build + swift test), no simulator
apps/mazeout/tools/levels/content_tests.sh                    # the level bundle, validator, 1000 endless levels
python3 apps/mazeout/tools/strings/build.py --check           # the string catalogue is up to date with the TSVs
python3 apps/mazeout/tools/skin/build.py --check             # skin colours: generated Swift up to date (docs/SKIN.md)
python3 apps/mazeout/tools/skin/build.py --check-literals    # no colour literal in the UI code outside skin/colors.json
python3 apps/mazeout/tools/release/meta.py audit              # store texts, keywords, captions, IAP catalogue
python3 apps/mazeout/tools/release/meta.py iap-check          # iap.json == rules.json:shop == ArrowOut.storekit
sh apps/mazeout/tools/bench/release_gates.sh <Release .app> [<Debug .app>]   # the release-binary gates (brand, provenance, SDKs, token)
```
Machine rules learned the hard way: at most two builds at once on a 16 GB Mac, keep 15 GB free on `/`, check `df -h`
before archiving (`docs/lessons/max-two-parallel-builds.md`, `disk-full-lies.md`, `disk-fills-fast-clean-archives.md`).

### The phone driver (research on the owner's iPhone)
Phone setup: Developer Mode on, Settings > Developer > Enable UI Automation on, Auto-Lock Never. Then
`tools/phonedriver/start-runner` (in the background) and `tools/phonedriver/phone status | shot F | tap X Y | swipe … |
launch BUNDLE | rec OUT.mov SECONDS …` (coordinates in points). The phone's ids are built-in defaults for the owner's
iPhone 15; another phone needs `PHONE_UDID` (start-runner) and `PHONE_DEVICE` (phone). Claude Code's safety check blocks
both commands until the two rules from `.claude/settings.example.json` are in `.claude/settings.local.json` with this
repo's absolute path (GAMEPROMPT.md "OWNER PRE-FLIGHT"). Details: `docs/lessons/phone-driver.md`.

---

## 4. Start a new game from this repo

**Short path: `docs/TEMPLATE.md`.** Inside one repo, `python3 tools/game.py new <slug> --from mazeout --name "Brand"
--bundle com.manycode.<x>` scaffolds `apps/<slug>` and does the rename below for you; the game's identity, store, flags,
events and brand bans then live in ONE file, `apps/<slug>/game.yml` (`game.py generate` writes it into every place in
the checklist, `game.py doctor --game <slug>` checks the whole folder). The steps below are the manual route and the
reference for what those commands touch.

### Step 1: copy the repo on GitHub
This repository is marked as a **template** on GitHub. On its page press **Use this template > Create a new repository**,
pick your account, type the new game's name, choose **Private**, and create it. (You cannot *fork* your own repository
into the same account; "Use this template" is the way to get a fresh copy with no shared history.)

### Step 2: set it up on the Mac
```
git clone <the new repository's URL> ~/Downloads/<new-game>
cd ~/Downloads/<new-game>
cp .env.example .env                                   # fill it (or copy the owner's existing .env)
mkdir -p keys && cp <path>/AuthKey_<KEYID>.p8 keys/    # and keys/signing/ from the old checkout, if you have it
cp machine.env.example machine.env                     # this Mac's simulator + phone ids (see §3)
cp .claude/settings.example.json .claude/settings.local.json   # then replace /Users/yago/Downloads/app-factory with this folder
pip3 install -r requirements.txt -r requirements-tools.txt
```

### Step 3: tell Claude
Open Claude Code in the new folder, switch to auto mode and type, for example:
- *"Read GAMEPROMPT.md and make Royal Match. ultracode ultrathink"* (multi-agent workflows), or
- *"Read GAMEPROMPTMAX.md and make Royal Match. Use parallel subagents for every phase."* (`/effort max`, subagents).

Do the "OWNER PRE-FLIGHT" list at the top of `GAMEPROMPT.md` first (phone, Mac, permissions, the original game installed).

**Notes for the Claude session that reads this:**
- `GAMEPROMPT.md` was written in the factory repo. It names `/Users/yago/Downloads/app-factory` (11 times in each manual)
  and the exemplars `apps/arrows` and `apps/matchfactory`, which are not in this repo. Read those paths as "this repo"
  and use `apps/mazeout` as the exemplar: `apps/mazeout/design/REUSE.md` maps every Match Factory / Arrows tool to its
  adapted Arrow Out copy, and its §1 table is exactly how the last rename (Match Factory -> Arrow Out) was done.
  `GAMEPROMPT.md` §3.5 already says: if an exemplar is missing, use its description and write the tool again.
- The workflow templates in `tools/gameprompt/workflows/*.js` set `ROOT` to the old Match Factory path; adapt them per §11
  of the manual, as the manual says.
- Recommended layout: keep `apps/mazeout/` untouched as the reference and build the new game in `apps/<new-slug>/` by
  copying what you reuse (GAMEPROMPT §3.5 / §8.0). Once the new game ships, `apps/mazeout/` can be deleted from that repo.

### Step 4: the RENAME CHECKLIST
`tools/game.py` covers rows 1-4, 10-12 and 17-20 (`new` renames, `generate` writes, `doctor` verifies; row 19 only partly, see docs/TEMPLATE.md "Manual"); the rest stay manual.
Counts are from a grep of the Arrow Out tree on 2026-09-30 (2,575 git files, about 220 MB), split into
**code+config** (everything except Markdown notes, logs, `research/`, `art/review/`, `design/spike-*`,
`design/publish/verify/`) and **all files**, plus the files of this repo outside `apps/mazeout`. The Markdown history
(PLAN, SPEC, design notes) can keep the old names; code, config, store texts and tests cannot.

| # | What | Arrow Out value | Where it lives (main places) | apps/mazeout code+config / all | rest of repo | What to do |
|---|---|---|---|---|---|---|
| 1 | Bundle id (also the IAP id prefix) | `com.manycode.arrowout` | `project.yml` (target + `.tests` / `.uitests`), `fastlane/Appfile` + `Fastfile` (11), `App/Resources/StoreKit/ArrowOut.storekit` (12 product ids), `design/publish/iap.json`, `Packages/PathCore/…/Economy/ShopCatalog.swift` (`productPrefix`), `App/Support/Log.swift` (log subsystem), 5 `DispatchQueue` labels (AudioEngine, PlayerStore, SocialModel, SocialLab, GameText), `tools/slot.sh`, `tools/bench/bench.py`, `tools/capture/capture.py`, `tools/play-watch.sh`, `tools/release/meta.py`, tests (MetaEvents, StoreRelease, ShellStoreKit, ShellS3, PathCore Economy) | 23 files / 85 · 32 / 120 | 4 files / 6 (script docstring examples) | new `com.manycode.<game>`; pass it to every script as `--bundle` |
| 2 | Xcode project / target / scheme / product | `ArrowOut` (+ `ArrowOutTests`, `ArrowOutUITests`, `ArrowOut.storekit`, `ArrowOut.app`) | `project.yml` (32), `tools/slot.sh`, `fastlane/Fastfile` (scheme, `Payload/ArrowOut.app`), `tools/bench/release_gates.sh`, tests; most hits are art ids like `logoArrowOut` in `art/MANIFEST.json` (166) and `design/publish/palette/palette_map.csv` (116) | 74 / 496 · 114 / 626 | 1 / 1 | rename in project.yml, slot.sh, Fastfile, gates, tests; art ids only if you keep those assets |
| 3 | App folder / slug | `mazeout` | the folder name; `--slug mazeout` for the scripts; `fastlane/Fastfile` (`ipa_provenance_clean!` refuses an IPA whose binary says "mazeout"), `tools/bench/release_gates.sh` (7), `tools/watchdog.sh` (7), `tools/memguard.sh`, `tools/cleaner.sh`, `tools/meta_token.py` (comments), `Tests/AppTests/BrandTests.swift`, `art/MANIFEST.json` (48 paths) | 57 / 140 · 196 / 394 | 8 / 13 | new slug = new folder `apps/<slug>`; update the provenance checks to the new folder name |
| 4 | Display / store name | "Arrow Out" (store: "Arrow Out: Arrow Escape Puzzle") | ONE source in code: `PC_BRAND_NAME` in `project.yml` -> Info.plist `PCBrandName` -> `Brand.name`. Store side: `design/publish/store/<locale>.json` (13), `fastlane/metadata/<locale>/name.txt` + descriptions, `design/captions/`, `design/publish/iap.json` (`appName`), `fastlane/Fastfile` (`create_app` app_name + SKU), `tools/release/meta.py`, `tools/meta_dashboard_check.py`, `tools/strings/` | 98 / 174 · 134 / 301 | 6 / 6 | new name; follow `docs/lessons/app-naming-keyword-first.md` |
| 5 | App Store Connect app id | 6816880848 | `PLAN.md` only; every script finds the app by bundle id | 0 / 0 · 1 / 1 | 0 | nothing: `fastlane create_app` makes a new one |
| 6 | RevenueCat app id | `app5e0e8dfedb` | `PLAN.md`, `SPEC.md` only; `rc_consumables.py` finds or creates the RC app by bundle id | 0 / 0 · 2 / 2 | 0 | nothing: created by `rc_consumables.py` |
| 7 | RevenueCat offering | `arrowout_shop` | docs only; the script's default is `<last bundle segment>_shop` | 0 / 0 · 4 / 5 | 1 / 1 (docstring) | nothing (automatic). Never make it the project's CURRENT offering: the RC project is shared by every app |
| 8 | RevenueCat public SDK key | `appl_gXsK…` (public, ships in the app) | `App/Shell/Shop/StoreConfig.swift` (`rcAPIKey`) | 1 / 1 · 2 / 2 | 0 | set it to `""` at first (StoreKit still sells; RevenueCat only observes), then `rc_consumables.py --config-file` writes the new key |
| 9 | Meta App ID | 2657116281470019 | `project.yml` (`FacebookAppID`), `App/Info.plist` (generated from project.yml), `Tests/AppTests/MetaEventsTests.swift` (6), `MetaSDKLinkageTests.swift`, `tools/bench/meta_sdk_check.py`, `tools/meta_dashboard_check.py` | 6 / 11 · 7 / 12 | 0 | a new Meta app per game (developers.facebook.com) + its Client token in `.env` `META_CLIENT_TOKEN` |
| 10 | In-app purchase ids | `com.manycode.arrowout.` + `offer.special`, `bundle.mini/epic/elite/mega/legendary`, `coins.1000…100000` (12 consumables) | `App/Resources/Tuning/rules.json` (`shop`), `App/Resources/StoreKit/ArrowOut.storekit`, `design/publish/iap.json`, `ShopCatalog.swift`, tests | (in row 1) | 0 | new catalogue; `python3 apps/<slug>/tools/release/meta.py iap-check` proves the three files agree |
| 11 | Privacy page | `https://leomarston.github.io/manycode-legal/privacy-arrow-out.html` | `fastlane/metadata/<locale>/privacy_url.txt` (13) + descriptions (13), `design/publish/store/<locale>.json` (13), `tools/release/loc.py` (`PRIVACY`), `tools/meta_dashboard_check.py` | 41 / 41 · 43 / 44 | 0 | publish `privacy-<game>.html` on the legal site (GitHub Pages repo `leomarston/manycode-legal`, local copy `~/manycode-legal`), then point these at it |
| 12 | Support e-mail | `anycodeapps@gmail.com` | `App/Resources/Tuning/game.json` (`support.email`), `tools/strings/sources.json`, `Tests/AppTests/TuningTests.swift`, `UITests/MetaTests.swift` | 4 / 5 · 10 / 19 | 2 / 4 (lessons) | usually KEEP (factory rule `support-mail-button`) |
| 13 | Review contact | the owner's Apple ID e-mail | `fastlane/metadata/review_information/email_address.txt` | 1 / 1 · 4 / 6 | 6 / 10 (lessons) | keep while it is the same account |
| 14 | Absolute path | `/Users/yago/Downloads/app-factory` | in `apps/mazeout`: `tools/watchdog.sh` (2), `tools/cleaner.sh`, `tools/heartbeat.sh`, `tools/memguard.sh`, `design/publish/tools/ph0/*.py` (11), `design/publish/tools/social_intl/*.py` (8), `design/font-compare/tools/crop_refs.py`; the other ~130 hits are in `research/` (level data, research scripts, bot logs) and notes. Elsewhere: `GAMEPROMPT.md` (11), `GAMEPROMPTMAX.md` (11), `tools/gameprompt/` (5 workflows + `snippets/play-watch.sh`), `scripts/launchd/…routine.plist` (4), `.claude/settings.example.json` (3) | 24 / 25 · 117 / 156 | 10 / 40 | replace with the new checkout's path where a tool must run; also `/Users/yago/.local/bin/xcodegen` in `tools/phonedriver/start-runner` |
| 15 | Simulator UDIDs | slot A "Maze A" `177520B6-4889-46C2-BDD9-155813D2B175`, slot B "Maze B" `B80EDB24-6280-4C52-A63F-E8AADD245017` | `machine.env` (git-ignored; `machine.env.example` holds these values), read by `tools/machine.sh` / `tools/machine.py` | — | — | create two simulators (§3) and put their UDIDs in `machine.env` |
| 16 | Phone ids | UDID `00008120-000964E426440032`, CoreDevice `878DB538-F187-596F-B24B-EAF8853617DE` (owner's iPhone 15) | `machine.env` (`PHONE_UDID`, `PHONE_DEVICE`); `GAMEPROMPT(MAX).md` text | — | — | set them in `machine.env` for your phone |
| 17 | Apple Team ID | `GDU77F3MXL` | `project.yml` (`DEVELOPMENT_TEAM`), `ArrowOut.storekit`, `tools/phonedriver/project.yml` (2) | 2 / 2 · 4 / 5 | 9 / 10 | keep while it is the same developer account |
| 18 | Provisioning profile name | `manycode arrowout appstore` | `fastlane/Fastfile` (2 lanes) | 1 / 2 · 2 / 3 | 0 | rename; `signing_setup.py` makes `manycode <slug> appstore` unless given `--profile-name` |
| 19 | The ORIGINAL game's brand words | "Maze", "MazeOut", "Arrow Jam", "Grand Games", "grandgames", "arrowjam" | `Tests/AppTests/BrandTests.swift` (banned lists), `tools/bench/release_gates.sh` (gates 3 and 7c), `tools/strings/build.py` (`BRANDS`, which also lists our own "Arrow Out" / "ArrowOut": copy must say `Brand.name`, never the literal) | — | — | replace with the NEW original's names (these checks keep the copy legally clean) |
| 20 | Store category | Games / Puzzle / Casual | `fastlane/Deliverfile` | — | — | per game (a GAMES app needs two subcategories) |
| 21 | Internal prefixes (optional) | `PathCore`, launch args `-pc.`, log tag `[PC]`, build settings `PC_*`, font `PCDisplay` | everywhere in Swift and tools | — | — | neutral on purpose; renaming is optional |

After renaming: `sh apps/<slug>/tools/gen.sh`, build, run the tests, and grep again for the old values (`grep -rn
"arrowout\|ArrowOut\|Arrow Out\|mazeout" apps/<slug> --include="*.swift" --include="*.json" --include="*.yml"
--include="*.py" --include="*.sh" --include="*.txt" --include="Fastfile" --include="Appfile"`).

---

## 5. What to keep and what to replace

**Keep (reusable for any puzzle game)**
- **Engine architecture:** a pure-Swift core package (`Packages/PathCore`: rules, deterministic random, motion curves,
  economy, events, persistence, level generator + validator; testable on macOS) under a SwiftUI + Core Animation app,
  with explicit contracts between the parallel build lanes (`App/Contracts/`).
- **Shell:** loading screen, home, HUD, the popups, shop (StoreKit 2 purchases, RevenueCat as an observer), events
  (streak race, claw challenge, balloon rise, rocket race, sky jump, weekly contest), leaderboards/social, profile,
  settings, tutorial and FTUE directors, lives, boosters, rating prompt after a meaningful action.
- **FX, audio, haptics:** confetti, coin fly, fireworks, sparkles, win sequence; the audio engine, sound bank, music
  player, haptics; the synthesis tools in `tools/audio/` (all sounds are made by us, never extracted).
- **Localisation system:** 13 languages (en, de, fr, es, it, pt-BR, tr, ja, ko, zh-Hans, pl, sk, sl; store: sl-SI):
  TSV sources in `App/Resources/Strings/` -> `tools/strings/build.py` -> `Localizable.xcstrings`, with coverage and
  review tools, plus `InfoPlist.xcstrings` and `tools/known_regions.py`.
- **Store tooling:** `scripts/` (§2) and the app-side `tools/release/meta.py`, `tools/store/compose.py`,
  `tools/capture/capture.py`, the fastlane lanes, and the Meta token handling (`tools/meta_token.py`,
  `tools/meta_dashboard_check.py`).
- **Art pipeline:** `art/PIPELINE.md` + `art/pipeline/` (SDF -> mesh -> USDZ, offscreen renderer), `art/ui/tools/`
  (SVG -> exact-size PNG, comparison sheets, checker), `art/MANIFEST.json` as the single list of every graphic,
  `tools/copygate.py` (never too close to the original).
- **Test harness:** unit + UI tests, `AutoPlayer`, BoardLab / ShellLab, `tools/{slot,gen,build,run,test,core}.sh`,
  `tools/bench/` (performance, release gates), `tools/compare/` (side-by-side with the original), the overnight
  watchdogs.
- **Release gates:** `tools/bench/release_gates.sh` (no debug placeholder, honest strings, no brand of the original, no
  research provenance, only the allowed SDKs, the Meta token present) and the Fastfile's IPA checks.
- **Process:** `PLAN.md` (NOW block, decisions, TODO ledger, status log) + `SPEC.md` (master prompt, numbered rulings)
  + the `design/SPEC-*.md` set, exactly as `GAMEPROMPT.md` §6 and §12 describe.

**Replace (specific to Arrow Out)**
- The rules of play: the board code in `App/Board/` and `PathCore`'s Grid / Rules / Solver / Content, levels
  (`App/Resources/Levels/`, `design/levels.json`, `design/tools/gen_levels.py`'s parameters), tutorials.
- The UI colours: `skin/colors.json` (palette + tokens; `tools/skin/recolor.py` moves whole families), see
  `docs/SKIN.md`.
- All art (`art/out/`, `art/ui/out/`, the app icon), fonts if the new original looks different, sounds and music.
- Every text: `App/Resources/Strings/*.tsv`, store texts (`design/publish/store/`), captions, keywords, screenshots,
  the IAP catalogue and prices (`design/publish/iap.json`, `rules.json:shop`, the `.storekit` file).
- `research/` (a new game gets new research), `PLAN.md`, `SPEC.md`, `design/SPEC-*.md` (start new ones; keep these as
  examples).
- The brand checks of row 19 above.

**The manual:** `GAMEPROMPT.md` is the full step-by-step (owner pre-flight, research on the phone, four specs, art lanes,
the build, verification, genre playbooks for 18 puzzle genres in §10, pitfalls in §13, definition of done in §14).
`GAMEPROMPTMAX.md` is the same with subagents instead of the Workflow tool. When a run teaches something new, update both
(`docs/lessons/gameprompt.md`).

---

## 6. The store pipeline, in order

This is the order Arrow Out actually went through (`apps/mazeout/design/publish/release-plan.md` §8, steps R0-R13, and
the status log in `PLAN.md`). **[OWNER]** marks the steps that need the owner in person.
The GAMEPROMPT build itself ends at "installed on the owner's phone"; publishing is a separate job the owner starts.

| # | Step | Command (from the repo root unless it says `cd`) | Needs |
|---|---|---|---|
| 0 | **[OWNER] Apple web session** | `fastlane spaceauth -u <APPLE_ID>` (password + 2FA code on a trusted device). Check it before steps 1 and 9: `fastlane spaceauth --check_session` (the check the Arrow Out run used) | the owner, every ≤ 30 days |
| 1 | Create the app record (reserves the name) | `cd apps/<slug> && fastlane create_app` (edit the lane's `app_name` / SKU first). If it dies on `CGI.parse` or an `olympus … 404`, load the patch: `RUBYOPT="-r<repo>/scripts/fastlane_apple_fix" fastlane create_app` | the Apple session |
| 2 | Signing (no device needed) | `python3 scripts/signing_setup.py --slug <slug> --bundle <bundle> [--profile-name "manycode <x> appstore"]` | ASC API key |
| 3 | In-app purchases | `python3 scripts/asc_consumables.py --bundle <bundle> --catalog apps/<slug>/design/publish/iap.json --screenshot <shop review .png>` (run with `--dry-run` first; they stay MISSING_METADATA until the review screenshot is in) | ASC API key |
| 4 | RevenueCat | `python3 scripts/rc_consumables.py --bundle <bundle> --catalog apps/<slug>/design/publish/iap.json --config-file apps/<slug>/App/Shell/Shop/StoreConfig.swift` | `RC_PROJECT_ID`, `RC_SECRET_KEY` |
| 5 | **[OWNER approves] Privacy page** | add `privacy-<game>.html` to the legal site and push (it is public; the owner said "yes" for Arrow Out's) | owner's yes |
| 6 | Store texts (13 locales) | `python3 apps/<slug>/tools/release/meta.py write` -> `cd apps/<slug> && fastlane upload_meta_only` -> `python3 scripts/asc_keywords.py --slug <slug>` (a first version cannot be submitted without keywords; never upload a `keywords.txt`) | ASC API key |
| 7 | Screenshots (5 per locale) | capture: `python3 apps/<slug>/tools/capture/capture.py --store …`; compose: `python3 apps/<slug>/tools/store/compose.py set --locale <loc> --raws <5 files>`; **look at every frame**; upload: `python3 scripts/asc_screenshots.py --slug <slug> --version 1.0.0` (fastlane `deliver` cannot upload screenshots on this Mac) | ASC API key |
| 8 | Build + upload | `df -h` first, then `cd apps/<slug> && fastlane upload_build` (checks the Meta dashboard settings, unlocks the signing keychain, regenerates the project, archives unsigned + signs at export, proves the IPA carries the token and no dSYM / no folder name). Wait for the build to process; never bump the build number on "already used" | `META_CLIENT_TOKEN`, signing |
| 9 | **[OWNER may be needed] App Privacy label** | `cd apps/<slug> && fastlane upload_privacy` (uses the Apple web session, can ask for 2FA; the API cannot do it) | the Apple session |
| 10 | App-level settings | the Deliverfile points deliver at `fastlane/metadata/app_rating_config.json` (age rating; the answers are in release-plan §7); content rights + free price are set inside `asc_submit.py`. Arrow Out's app availability ("174 territories, China excluded") was set during the run by hand; there is no script for it here (the IAPs' China exclusion is in step 3) | ASC API key |
| 11 | Submit | `python3 scripts/asc_submit.py --slug <slug> --bundle <bundle> --uses-idfa` (`--dry-run` first). `--uses-idfa` is required whenever the Meta SDK is linked, or Apple marks the build INVALID_BINARY with no reason given. Then watch the version for 15+ minutes and read back: submission WAITING_FOR_REVIEW, the right build, every IAP in the submission | ASC API key |
| 12 | Bookkeeping | commit, update `PLAN.md`, add a lesson for anything new | — |

Other owner-only moments: creating the Meta app + a Facebook Page for the ads (developers.facebook.com; the browser is
allowed only for Meta and Appfigures, never App Store Connect: `docs/lessons/account-and-no-browser.md`), agreeing to any
new Apple agreement, Face ID for a TestFlight purchase test on the phone.

Before each step, the matching group in `docs/lessons/README.md` lists what went wrong last time.

---

## What was not verified

- The game was not built or tested from this staging copy (`apps/mazeout/` is filled in afterwards from the final
  committed tree). `tools/gen.sh` WAS run on a clean copy of the git-tracked files and generated the project with its 13
  languages; `swift build`, `xcodebuild` and the test suites were not run for this README.
- The `simctl create` runtime name and the art virtual-environment `pip install` line in §3 are the standard forms, not
  commands that were run here.
- Whether `scripts/fastlane_apple_fix.rb` is still needed with today's fastlane is unknown; Arrow Out's `create_app`
  succeeded on 2026-09-28 and the log does not say whether the patch was loaded.
- How the app-level China exclusion (step 10) was made: the run's log records the result ("174 territories, CHN
  excluded"), not the command.
