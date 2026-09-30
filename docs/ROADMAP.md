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
  - [ ] Debug harness (BoardLab/ShellLab/SoundBoard/SocialLab/AutoPlayer/`-pc.win`) out of Release builds — **moved to
        phase 1**: shipping types live inside the lab files (`S3Hooks`/`S3Popups` in `ShellLab+Meta.swift`, `HUDLab.fill`
        used by `S2Hooks`, `SocOpenBench` by `SocialModel`, `LabBoards.warmEffectsBoard` by `WarmUp`); split them out
        while the files move, then gate the labs with `#if DEBUG || PC_MEASURE` (bench runs Measure; store captures use
        no lab). Unreachable in Release today (launch arguments only).
  - [ ] Recover `build/` specs the code still cites (logo timing, Balloon Rise rules, contract hashes) from the owner's Mac
  - [ ] PathCore/GameCore buildable + testable on Linux (cloud sessions)
- [ ] **1. Restructure without behaviour change** — `Engine/`, `Puzzles/ArrowEscape/`, `Games/arrowout/`; split
      PathCore into GameCore + ArrowEscape; cut the seams (RulesTuning meta/arrow split, decode helper, streak steps,
      world seed, booster ids from config)
- [ ] **2. Puzzle contract** (draft for review: `docs/architecture/PUZZLE-MODULE.md`) — `PuzzleModule`, generic meta events, GameController/directors/HUD/fail flow generic,
      `PuzzleBoard` replaces the arrow-typed board contract, generic bot/probe, ArrowEscape implements it
- [ ] **3. Skin system** — colour tokens (pixel-checked against the baseline), art slots, scene/logo data, fonts,
      sounds, names; prove it with a second skin and zero Swift changes
- [ ] **4. Config + generators** — `game.yml`, `tools/game.py new|generate|doctor`, every script/lane/gate per game
- [ ] **5. Prove a second puzzle** — a module with a different input and fail rule, shipped to TestFlight with its own skin
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
