# Roadmap: from Arrow Out to a reusable game template

Read this first in a new session. Update the **Status log** and the phase checkboxes when a step lands.

## The goal (owner, 2026-09-30)
Make this repo a template where a new game = **plug in a puzzle** + **reskin** + **configure** → publish.
- **Stays the same for every game ("the system"):** home, HUD, popups, shop, lives, coins, boosters, continue/fail
  chain, win celebration, tutorials/unlock cards, the tournaments and challenges (streak race, ladders, weekly contest,
  sprints, races, weekly rotation), the **offline but online-looking** leaderboards and rivals, store, localisation,
  persistence, and all build/test/release tooling.
- **Changes per game:** characters, colours, fonts, all art, sounds, texts, shop items and prices, event names and
  skins, economy numbers, and **the puzzle itself**.
- **Genre-agnostic:** the puzzle can be anything (match-3, sorting, colouring, escape, word, logic, merge, …). Genres named
  anywhere in this plan are only test cases; nothing outside a puzzle module may assume one.

## Decisions
| # | Decision | By / when |
|---|---|---|
| D1 | Genre-agnostic puzzle interface; example genres are only test cases | owner, 2026-09-30 |
| D2 | Ad/attribution SDK (Meta) is **not part of the template**; off by default, added from zero per game when wanted | owner, 2026-09-30 |
| D3 | Arrow Out stays in the repo as the reference game and regression fixture ("looks and behaves the same" + its tests) | owner, 2026-09-30 |
| D4 | Layout: one repo, `Engine/` (shared) + `Puzzles/<module>` + `Games/<slug>` (config, skin, strings, levels, store) | proposed default; revisit if the owner prefers one repo per game |
| D5 | Original games' captures, levels and assets are never committed; new games use their own/generated content | 2026-09-30 |

## Target shape
```
Engine/    GameCore (pure Swift: random, motion, save, economy, events, social world, session kit, content kit, config)
           GameShell (SwiftUI + Core Animation UI: router, home, HUD, popups, shop, event screens, FX, audio, theme)
           Contracts (PuzzleModule protocol + generic meta events)
Puzzles/   ArrowEscape (today's rules + board, the first module) · _Template (empty module + checklist) · …
Games/     <slug>/ game.yml · skin/ (tokens, fonts, art slots, scenes, sounds) · strings/ · levels/ · store/
tools/, scripts/   every command takes --game <slug>
```
**Puzzle contract (the core idea):** a module provides levels (authored and/or generated), a deterministic session
(input → events; the board acknowledges when animations land), its own board view (any rendering tech), its fail rule
(timer / moves / hearts / none / custom), goals and progress for the HUD, its boosters, tutorials and unlock cards, and
a bot for tests. The shell only sees generic meta events (started, progress, mistake, offer, won, lost) and a win result
(tier, difficulty tag), which is all the economy, events and social world need.

**Skin:** semantic colour tokens instead of the ~1,800 hex literals in Swift; art by **slot** (`logo.main`,
`event.race.badge`, `home.character.boss`) instead of Arrow Out names; home/loading scenes and the win logo as data;
fonts, sounds, event names from the skin/strings. A missing slot fails `doctor` and the Release build.

**Config:** `Games/<slug>/game.yml` → generated project.yml, .storekit, IAP catalogue, tuning, release-gate brand bans.

## Phases
- [ ] **0. Baseline & hygiene**
  - [x] CI: Linux content/store checks, PathCore `swift test`, app build + unit tests on an iOS simulator (macos-26)
  - [x] Remove committed captures of the original game (art/review images, motion-evidence strips)
  - [x] Fix verified release/babysitter script bugs (package.sh, signing_setup, asc_submit dry-run, asc_new_version,
        Fastfile secrets, start-runner, stallcheck, memguard)
  - [x] Machine specifics (simulators, phone, paths) → git-ignored `machine.env`
  - [x] Game-aware `CLAUDE.md`; subscription-factory rules and `app-factory` skill archived in `docs/archive/`
  - [x] Purchase durability: never `finish` a StoreKit transaction whose grant failed to save
  - [x] Remove the Meta SDK from the engine (D2): code, strings, privacy manifest/label, gates; recipe in
        `docs/recipes/ad-attribution.md`; generic `PurchaseReporting` hook kept; SDK gate 8 = allow-list (`sdk_gate.py`)
  - [x] Debug harness (BoardLab/ShellLab/SoundBoard/SocialLab/AutoPlayer/`-pc.win`) out of Release builds: shipping types
        moved out of the lab files (`ShellLab+Meta.swift` → `Popups/S3Hooks.swift`; `HUDLab.fill/text` → `HUD/HUDSample.swift`;
        `LabBoards.warmEffectsBoard` → `Board/WarmBoard.swift` `WarmBoards.effectsBoard()`, the lab forwards), then the 12
        harness files wrapped whole in `#if DEBUG || PC_MEASURE` (Measure = the bench's config keeps them; store captures
        use none) and every call site gated (entry `makeDebugScreen`s fall back to the contract default, `AppModel.autoplayer`,
        `SocOpenBench`, `-pc.win`/`-pc.lose` jumps); Release logs an error and ignores `-pc.go <lab>`, `-pc.autoplay`,
        `-pc.win/lose`, `-pc.lab open`. `tools/harness_gate.py` (+ `--selftest`) in CI's Linux job; `measure_strip_check.sh`
        gained lab markers. Awaiting: CI Debug build, and a Release/Measure build + `measure_strip_check.sh` on the Mac
        (CI builds no Release).
  - [ ] Recover `build/` specs the code still cites (logo timing, Balloon Rise rules, contract hashes) from the owner's Mac
  - [ ] PathCore/GameCore buildable + testable on Linux (cloud sessions)
- [ ] **1. Restructure without behaviour change** — `Engine/`, `Puzzles/ArrowEscape/`, `Games/arrowout/`; split
      PathCore into GameCore + ArrowEscape; cut the seams (RulesTuning meta/arrow split, decode helper, streak steps,
      world seed, booster ids from config)
  - [ ] PathCore split (awaiting CI): `Packages/PathCore` now has targets `GameCore` (Random, Persistence, Economy,
        Events, Social, Tuning/MetaRules, Motion/Ease+Tunable, Session/SessionTypes+LevelClock, Model/IDs) and
        `ArrowEscape` (Grid, Model incl. ArrowIDs, Rules, Solver, Content, Session incl. SessionAck, board Motion),
        ArrowEscape → GameCore only (core.sh checks the imports); `PathCore` is an umbrella (`@_exported`), so the app
        and lvtool are unchanged. Seams cut: `MetaRules` (failChain/rewards/boosters, same rules.json keys; RulesTuning
        keeps typealiases) read by `EconomyRules.boosterRules`; decode helper + dotted overrides in `TuningJSON`.
        Still open: streak steps, world seed, booster ids from config (not needed for the dependency direction).
- [ ] **2. Puzzle contract** (`docs/architecture/PUZZLE-MODULE.md`, now v1-candidate = what is built) — `PuzzleModule`, generic meta events, GameController/directors/HUD/fail flow generic,
      `PuzzleBoard` replaces the arrow-typed board contract, generic bot/probe, ArrowEscape implements it
  - [x] GameCore contract (`Session/PuzzleContract.swift`): `PuzzleTarget`, `PuzzleInput`, `PuzzleMove`, `PuzzleEvent` /
        `PuzzleBeat` (opaque), `PuzzleAck`, `MetaEvent`, `SessionOutput` (`.meta` / `.puzzle(any PuzzleEvent)`),
        `PuzzleCapabilities` (`FailRule`, `InputKind`, `BoosterSpec`/`BoosterKind`, `HUDWidget`), `PuzzleStage`,
        `PuzzleSession`, `PuzzleModule`, `TutorialStep` (+ `TutorialTrigger`/`TutorialDismiss` moved to GameCore);
        additive: `ContinueOffer.Kind` outOfMoves/stuck (+ `lossReason`), `Grant` addMoves/puzzleAction, `LossReason`
        outOfMoves/stuck, `WinResult` stars/stats (old JSON decodes; APISurfaceTests: the two allCases lists extended, new
        pins added); `PuzzleContractTests`
  - [x] ArrowEscape adapter (`Session/ArrowPuzzleSession.swift`): `ArrowPuzzleSession` wraps `LevelSession` unchanged,
        `SessionEvent` → `SessionOutput` 1:1 in order, `SessionAck: PuzzleBeat`, `ArrowEscapeModule` (capabilities
        timer + hearts(3), tap, freeze/hint, HUD timer + hearts, zoomable, multi-stage)
  - [x] App: `PuzzleBoard` / `PuzzleBoardDelegate` / `PuzzlePlugin` / `ActivePuzzle` (`App/Contracts/PuzzleBoardContract.swift`);
        `ArrowPuzzleBoard` + `ArrowEscapePlugin` (`App/Board/ArrowEscapePlugin.swift`) around the unchanged BoardEngine;
        GameController + LevelFlow, FailFlow, Win, Booster (slots from `BoosterSpec`s), HUDWriter, Tutorial, Unlock, Events
        directors and the AutoPlayer consume `SessionOutput`/`MetaEvent` and the capabilities — no arrow type left in
        `App/Game`; the module is registered in ONE place (`ActivePuzzle.entry`); GameControllerTests / GameG2Tests drive
        the controller through ArrowPuzzleBoard's real translation (assertions unchanged)
  - [ ] CI green on the phase-2 change (written without a Swift toolchain), then UI tests + bench + captures on the Mac
        ("no behaviour change" proof), then the §7.2 paper designs (sorting, match-3, colouring) before freezing v1
  - [ ] Gaps for other genres (found while building, not needed by Arrow Out): HUD moves/goals widgets, `outOfMoves`/`stuck`
        popup texts (13 languages) and Shell variants, `MetaRules.StepGrant.addMoves`, `SessionPlan` into GameCore,
        audio cue key `cues.arrowTap` → a generic move cue
- [ ] **3. Skin system** — colour tokens (pixel-checked against the baseline), art slots, scene/logo data, fonts,
      sounds, names; prove it with a second skin and zero Swift changes
  - [x] Colour tokens (code): every colour literal of App/Shell, App/FX and GlossyChrome (1,703 sites) is a `Skin.<token>`
        constant generated from `apps/mazeout/skin/colors.json` (996 palette colours, 1,664 tokens); `tools/skin/`
        build.py (--check, --check-literals, --selftest), codemod.py (--verify: values identical to the pre-codemod
        sources), recolor.py (L*-preserving family recolour, --preview); `SkinColorsTests`; CI Linux job;
        `docs/SKIN.md`. Pixel check on a device/simulator against the baseline: not done yet (the values are proven equal
        in source, not by screenshots)
  - [x] ui.json colours into the skin: the 657 colour slots of `Tuning/ui.json` are `"@<ui id>"` references to
        `skin/colors.json` `ui` (palette names; 67 ui-only colours added to the palette, 1,063 now); build.py generates
        `Tuning/ui-colors.json`, `Tuning.load` resolves the references at load (`TuningFile.resolvingReferences`);
        `build.py --adopt-ui` moves a raw colour written into ui.json into the skin, `--check` fails on one; the family
        recolour covers them through the palette (`--ui-json` retired). Verified on Linux: resolving the new ui.json gives
        the old one value for value; the Swift side (`SkinColorsTests.testUIJSONColourReferencesResolveAtLoad`) is CI's
  - [x] Fonts and names as skin data: `skin/fonts.json` (faces by GameTextStyle.Face role) and `skin/names.json` ->
        `SkinData.generated.swift` (`SkinFonts`, `SkinNames`) + the UIAppFonts lists in project.yml / Info.plist.
        Sounds were already data (`audio.json` cues/gain, files by SoundID); brand name stays game.yml's; copy names stay
        in strings.tsv (docs/SKIN.md §3). Left: `App/Board/DigitGlyphs.swift` spells "PCDisplay-Black" (another lane's folder)
  - [x] Art slots, scenes/logo data (docs/SKIN.md §4); a second skin (colours, §5). `skin/art.json`: 200 raster slots
        (`home.backdrop`, `currency.coin.icon`, `avatar.<n>`, `event.<id>.*`, `logo.part.<id>`, `puzzle.<sprite>` …) -> the
        manifest ids, 8 rig slots; `skin/scenes.json`: the home layer lists, rig part sets, the Loading scene.
        `tools/skin/art.py` generates `UIArt` (a case per slot: asset/path/sizePt/group) + `ArtRig` and `SkinScenes`;
        `--check` (CI) fails on an unmapped shipped file, a missing file, a string slot the skin lacks, a Swift string naming
        an art file (allow-list: App/Board sprite ids, PuppetRig, the win-logo part ids). 419 call sites renamed to slots;
        HomeView / LoadingScreen draw the scene lists. Fixed on the way: the race lanes' portraits pointed at 8 retired
        files (`Art/char_avatar<Walkie…>@3x.png`, placeholder in Debug, nothing in Release) — now the `avatar.<n>` slots.
        `skin/variants/cobalt` + `tools/skin/variant.py --check` (CI): the variant's generated files differ from the
        reference's only in colour values. Swift not compiled in that session (CI); an art variant and a screenshot of a
        variant on the Mac are still to do
- [ ] **4. Config + generators** — `game.yml`, `tools/game.py new|generate|doctor`, every script/lane/gate per game
  - [x] `apps/mazeout/game.yml`: identity, puzzle module + its level checks, store, events (mirrored into social.json),
        social seeds, brand bans, feature flags; economy + IAP catalogue REFERENCED (rules.json / iap.json stay the source)
  - [x] `tools/game.py doctor --game <slug>`: schema; ~60 identity anchors (project.yml, fastlane, tools, .storekit,
        iap.json, tuning, metadata URLs, Swift seeds); `com.<org>.*` literal sweep; ad attribution off; ban coverage in
        BRANDS / gate 3 / BrandTests / loc.py; IAP triple (meta.py iap-check); strings --check; skin --check; the
        puzzle's `checks`; store texts + meta.py audit; art MANIFEST files at size + app icon; machine.env (warn); no
        identity of another game. apps/mazeout: 0 FAIL (WARN only machine.env on Linux)
  - [x] `tools/game.py generate --game <slug> [--check]`: targeted writes (regex group / JSON value span) + old bundle
        id / brand sweep; mazeout `--check` = 0 changes; write mode tested on scratch copies and in unit tests
  - [x] `tools/game.py new <slug> --from mazeout …`: copy plan (docs/TEMPLATE.md), identity rename, game.yml, generate;
        doctor on the result = only the TODOs (store texts, rendered art, app icon; warns: levels copy, strings sources)
  - [x] `tools/tests/test_game.py` (28 tests, `python3 -m unittest discover -s tools/tests`); `docs/TEMPLATE.md`; README §4
  - [x] Tools read identity from one place: `meta.py` brand checks use `loc.py BRAND`; strings `BRANDS` = game.yml bans
        + our names (now also blocks "Maze", "grandgames", "arrowjam" in copy, like gate 3 / BrandTests)
  - [ ] CI: run `python3 tools/game.py doctor --game $APP_DIR_SLUG --quick` + the game.py unit tests in the Linux job
  - [ ] `new` for a second game end-to-end on the Mac (gen/build/test of the scaffold) — needs a real second game (phase 5)
  - [x] Generate the remaining hand-kept lists: `game.yml brand_ban_forms` (store_patterns -> loc.py `BANNED_BRAND`,
        file_stems -> gate 3 file-name grep, binary_words -> gate 7c `WORDS`/`NEVER_SDK`, review_patterns -> l10n_review
        `BRAND_RE`) + derived from `brand_bans` (`BrandTests.bannedAnyCase`, gate 3 data-file greps); doctor: fresh +
        each list catches every ban. Still hand-kept: loc.py's category/competitor/"online" words, 7c provenance words
  - [x] Swift constants game.yml mirrored -> `GameCore/Config/GameConfig.generated.swift` (world seed, world epoch,
        calendar epoch, rotation seed, IAP prefix; values unchanged); SocialWorldModel / SocialCalendar / EventRules /
        ShopCatalog read `GameConfig`. doctor: file fresh + no such literal in App/ or Packages/*/Sources; the frozen
        Python reference is read-only-checked. Generate no longer edits hand-written Swift (only BrandTests' lists)
- [ ] **5. Prove a second puzzle** — a module with a different input and fail rule, shipped to TestFlight with its own skin
  - [x] SortPuzzle through the contract (awaiting CI): core target `Packages/PathCore/Sources/SortPuzzle` (GameCore only,
        own product, not in the umbrella; core.sh import check): level model, seeded generator (solvable by construction),
        bounded DFS solver, `SortPuzzleSession` (select-then-target, no timer/hearts, fail `stuck` → an extra-tube continue,
        undo / extra-tube boosters, multi-stage), `SortPuzzleModule`, `SortBot`; Python reference `tools/sortpuzzle/ref.py`
        + goldens (CI Linux `--check`); `SortPuzzleTests`; app half `App/Puzzles/SortPuzzle/` (plugin, UIKit/CA board from
        sort.json + `puzzle.sortBoard.*` skin tokens, entry) compiled in, selected by `PC_PUZZLE_SORT`; `SortPuzzleAppTests`
        (plugin + board headless; the unchanged GameController to the win panel; a stuck offer paid through the shell)
  - [x] Contract v1.1 (PUZZLE-MODULE.md §8b): `MetaRules.FailStep.action` (additive; ArrowEscape unchanged), module
        default fail chains, modules as separate products + compile-time selection, explicit board/untimed semantics
  - [ ] Shell work before a sort game ships (PUZZLE-MODULE.md §6b): HUD honours `capabilities.hud` (no timer pill; a
        progress widget), `stuck` popup texts (13 languages) + variants, `undo`/`extraTube` economy entries + buy-popup
        texts + corner art, boot without the arrow engine/library, tutorials; then a game folder (`new --puzzle
        sort-puzzle`), its skin, TestFlight
- [ ] **6. Docs & prompts** — TEMPLATE.md, PUZZLE-MODULE.md, SKIN.md; the game manual split into "write a puzzle
      module" and "reskin & publish"

## Blocked / needs the owner
- CI excludes two machine-dependent checks from gating (run non-gating): `ShellStoreKitTests` (SKTestSession answers
  `notEntitled` on hosted runners) and `BoardEngineTests.testBumpReportsContactThenFinishedAndStaysRed` (animation timing
  0.23 s vs 0.138±0.05 on a shared VM). Confirm both on the Mac: `apps/mazeout/tools/test.sh A -only-testing:ArrowOutTests`.
- Swift changes are verified on GitHub Actions (no Xcode in cloud sessions); UI tests and phone checks need the Mac.
- Phase 0 item "recover build/ specs" needs files that exist only on the owner's Mac.

## Status log
- 2026-09-30: analysis of the repo (report + plan delivered in chat); CI added; original captures removed; script bugs
  fixed; machine.env; CLAUDE.md rewritten, factory rules archived. First CI baseline (untouched game code): app builds
  on Xcode 26.6; 280 unit tests ran, failures only in the Meta linkage test (owner-machine paths) and the two
  machine-dependent checks above; core 403 tests with 1 failure: SocialIntlTests read the OS's region list, which on
  macOS 26.6 also holds groupings (003, 202, 419, EU, EZ, UN) -> the test now requires every COUNTRY to have a board
  and every grouping to land on a real or local one. After the Meta removal + purchase fix: app build + gating unit
  tests GREEN on CI (run 5). Run 6: ALL jobs green (Linux checks, core 403 tests, app build + gating unit tests).
- 2026-09-30: skin colours (phase 3, first part): 1,703 colour literals in the UI code -> `Skin` constants from
  `skin/colors.json`; `codemod.py --verify` shows 0 of 61 files differ from the literals they replaced; CI Linux job
  runs `tools/skin/build.py --check / --check-literals / --selftest` and `recolor.py --selftest`. App build + the new
  `SkinColorsTests` still to be confirmed on CI (no Swift toolchain in the session that wrote it).
- 2026-09-30: config + generators (phase 4, first part): `apps/mazeout/game.yml`, `tools/game.py doctor|generate|new`,
  `tools/tests/test_game.py` (19 tests green), `docs/TEMPLATE.md`. doctor on apps/mazeout: 0 FAIL, 1 WARN (no
  `machine.env` in a cloud session). generate --check on apps/mazeout: 0 changes. `new testgame` on a scratch copy of
  the repo: doctor lists only store texts / rendered art / app icon (FAIL, TODO) + levels copy / strings SPEC sources
  (WARN). Verified on Linux only; the scaffold was not built with Xcode.
- 2026-09-30: skin, second part (phase 3): ui.json's 657 colours -> skin/colors.json `ui` (ui.json keeps "@<ui id>"
  references, resolved by Tuning.load from the generated Tuning/ui-colors.json); skin/fonts.json + skin/names.json ->
  SkinData.generated.swift (+ UIAppFonts lists); build.py --check / --adopt-ui / selftest extended, recolor.py covers the
  ui colours through the palette. Linux: resolved ui.json == the old file value for value, all Linux checks green. Swift
  (Tuning.swift resolver, font/name call sites, new SkinColorsTests cases) not compiled in that session: CI to confirm.
- 2026-09-30: puzzle contract (phase 2, first part): GameCore `PuzzleContract.swift` (the generic contract), ArrowEscape
  `ArrowPuzzleSession` + `ArrowEscapeModule`, app `PuzzleBoard`/`PuzzlePlugin`/`ActivePuzzle` + `ArrowPuzzleBoard`/
  `ArrowEscapePlugin`; the Game layer (`App/Game/*`) is genre-agnostic (no arrow type). Additive changes to the frozen
  session types (Kind/Grant/LossReason/WinResult). `docs/architecture/PUZZLE-MODULE.md` rewritten as v1-candidate.
  Written in a cloud session without a Swift toolchain: nothing compiled yet — CI is the first build.
- 2026-09-30: debug harness out of Release (phase 0): 3 shipping types split out of lab files (S3Hooks/S3Popups,
  HUDSample, WarmBoards), 12 harness files + their call sites (7 files) gated `#if DEBUG || PC_MEASURE`; `tools/harness_gate.py`
  (Linux CI, selftest 13 planted failures) finds 29 problems on the old tree, 0 now. Written without a Swift toolchain:
  the Debug build is CI's; CI now also compiles Release (run 14 green); Measure still needs a Mac build.
- 2026-09-30: config + generators, second part (phase 4): game.yml is the single source of the core's per-game constants
  (`GameConfig.generated.swift`, written by `tools/game.py generate`; same literals as before, byte for byte) and of every
  brand-ban list the gates use (`brand_ban_forms` + lists derived from `brand_bans`; loc.py `BANNED_ALL` value-identical).
  doctor on apps/mazeout --quick: 0 FAIL; generate --check: 0 changes; 28 game.py tests green; CI Linux steps green
  locally. Swift (GameConfig + 5 call sites) not compiled in this session: CI's core + app jobs are the first build.
- 2026-09-30: second puzzle module (phase 5): SortPuzzle (colour sorting: pick a tube then a target, no timer, fail =
  stuck) written only against the contract; one additive contract change (v1.1: `FailStep.action`, a fail-chain step that
  grants a module action) plus documented semantics (async board acks, untimed sessions, pick-state in the session). Its
  app half is compiled into the app while ArrowEscape stays active (`PC_PUZZLE_SORT` switches). Linux: ref.py goldens
  (40 levels + a 12-level stress set) self-checked and fresh, skin --check / --check-literals green, harness gate, doctor,
  brand check, strings, meta audit green; `uiart_gen --check` was red from another lane's in-progress UIArt.swift edit.
  Swift (SortPuzzle target, its tests, FailStep.action + ContractV11Tests, the app files and SortPuzzleAppTests) not
  compiled in this session: CI's core + app jobs are the first build.
- 2026-09-30: skin, third part (phase 3): art by slot (skin/art.json -> UIArt/ArtRig, 200 + 8 slots, the reference
  mapping = the same 200 files and 8 rigs), scenes as data (skin/scenes.json -> SkinScenes: home back/front layer lists,
  the main character's arm split, the Loading cast; HomeView / LoadingScreen draw the lists), win/boot logo timing stays
  ui.json's (`win.*`, `frames.loading.logo`), its images are `logo.part.<id>` / `logo.main` slots; a second colour skin
  (`skin/variants/cobalt`, recolor rules, not shipped) with `variant.py --check` proving a colour-only diff. Race-lane
  portraits fixed (they named 8 retired files). Linux: art.py / variant.py / build.py checks + self-tests, uiart_gen --check,
  every CI Linux step green locally. Swift (419 renamed call sites, HomeView scene loop, LoadingScreen, RaceBar, WinLogo
  decode, SkinArtTests + test updates) not compiled in that session: CI's app job is the first build.
- 2026-09-30: CI results: phase 2 contract green (run 13, after a brand-in-comment fix), debug-harness gating green incl.
  the new Release compile (run 14), phase 4 GameConfig green (run 15: core goldens unchanged, app Debug + Release).
  Run 16 (`d465610`) never started (see Blocked).
- 2026-09-30: the Actions stop was the account's Actions budget ($0 + stop usage) after the included minutes ran out;
  the owner made the repository public (standard runners, macOS included, are free for public repos). CI resumed.
