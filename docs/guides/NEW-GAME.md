# Make a new game, from `game.py new` to the App Store

An ordered checklist. Each step says **where** it can run:
- **[Linux]** any machine with Python 3 (a cloud session included);
- **[CI]** GitHub Actions (`.github/workflows/ci.yml`): the only place a cloud session gets Swift compiled;
- **[Mac]** the owner's Mac (Xcode, simulators, signing keychain, `.env` + `keys/`, the phone);
- **[Owner]** the owner in person (Apple sign-in / 2FA, approvals, agreements, Face ID).

The map of the template is `docs/TEMPLATE.md`; the module and skin guides are `docs/guides/WRITE-A-PUZZLE.md` and
`docs/guides/RESKIN.md`; the store steps are README §6. Before every store, signing, payment, simulator or phone step,
read the matching group of `docs/lessons/README.md`. Hard rules: `CLAUDE.md` (no backend, online features simulated,
real never mock, numbers and colours from data, never weaken a test, secrets only in `.env` / `keys/`, never an original's
assets).

**Read "Known gaps" at the end first.** To reuse single screens or systems (pause menu, leaderboard, shop, …) in another
game, see `docs/guides/KIT.md` (`tools/kit.py`).

## 0. Decide [Linux]
- [ ] Same puzzle as an existing module (ArrowEscape `arrow-escape`, SortPuzzle `sort-puzzle`) or a new one
      (WRITE-A-PUZZLE.md). If you are cloning an original game, research it first (`GAMEPROMPT.md` §4-§6 or
      `GAMEPROMPTMAX.md`): the research decides the module's rules, capabilities and the economy.
- [ ] Names: `<slug>` (folder, `[a-z][a-z0-9-]*`, neutral: it lands in build paths the gates scan), brand name, bundle id
      `com.manycode.<x>`, product (CamelCase), en-US store name (`docs/lessons/app-naming-keyword-first.md`), the
      privacy URL.
- [ ] The ORIGINAL's names (title, publisher, their joined / lowercase forms) for `--bans`: the brand gates keep them out
      of copy, file names and the binary.

## 1. Scaffold [Linux]
```sh
pip3 install -r requirements.txt                        # PyYAML for game.py
python3 tools/game.py new <slug> --from mazeout --name "Brand" --bundle com.manycode.<x> \
    [--puzzle sort-puzzle] [--bans "Original Name,Its Publisher"] [--store-name "Brand: Keyword"] \
    [--product BrandName] [--privacy-url https://…/privacy-<brand>.html]
python3 tools/game.py doctor --game <slug>
```
What `new` copies, renames and leaves out: `docs/TEMPLATE.md` §1. On scaffolds made on 2026-09-30 (scratch copies of this
repo), doctor listed exactly:

| Item | Same puzzle | `--puzzle sort-puzzle --bans …` | Fixed in step |
|---|---|---|---|
| `FAIL store texts` | yes | yes | 8 |
| `FAIL shipped art files` (228 of 228), `FAIL app icon` | yes | yes | 4 |
| `FAIL levels` (no `design/levels.json`, empty `App/Resources/Levels`) | — | yes | 7 (and a known gap) |
| `FAIL store-text gate` / `gate 3 file names` / `l10n review` (ban forms) | — | with `--bans` | 2 |
| `WARN levels are this game's own` (identical to the reference) | yes | — | 7 |
| `WARN strings coverage sources` (`tools/strings/sources.json` names the reference's specs) | yes | yes | 6 |
| `WARN rotation_ref.py EPOCH / seed (reference)` (`design/publish/tools/` is not copied) | yes | yes | 2 |
| `WARN machine.env` | on Linux | on Linux | 10 |

## 2. Configure `game.yml` [Linux]
- [ ] Edit `apps/<slug>/game.yml`: `identity`, `store` (name, keyword seed, category, URLs, support e-mail, copyright,
      locales), `features` (ad attribution stays off unless the game opts in: `docs/recipes/ad-attribution.md`), `events`
      (unlock levels, weekly rotation), `social` (world seed / epoch, rotation seed / epoch), `brand_bans` and
      `brand_ban_forms` (a store pattern, a file stem and a review pattern for every new ban name).
- [ ] `python3 tools/game.py generate --game <slug>` then `generate --game <slug> --check` (0 changes) and doctor.
- [ ] A new world seed or epoch: the social world's frozen Python reference (`design/social/tools/socialsim`,
      `design/social/FROZEN`) and `design/publish/tools/rotation_ref.py` must be re-derived with their fixtures and
      goldens (TEMPLATE.md §4 "Generated whole files"). Keeping the reference's seeds avoids that; the rotation_ref WARN
      then stays (the file is not copied) and must be explained.
- Reference for every key and what `generate` writes: `docs/TEMPLATE.md` §4.

## 3. The puzzle module [Linux → CI/Mac]
- [ ] Same puzzle: nothing to write. A new one: `docs/guides/WRITE-A-PUZZLE.md` end to end (core target, session, board,
      plugin, entry, Python reference + goldens, tests).
- [ ] Select it: the `ActivePuzzle` branch + `SWIFT_ACTIVE_COMPILATION_CONDITIONS: "$(inherited) PC_PUZZLE_<X>"` on the app
      and test targets of `apps/<slug>/project.yml` (`new --puzzle` does not set it), `game.yml puzzle.module` and
      `puzzle.checks` (e.g. `tools/sortpuzzle/ref.py --check`).
- [ ] [Linux] the module's reference `--check`. [CI/Mac] `tools/core.sh` and the app tests.

## 4. Reskin [Linux + Mac for rendering]
- [ ] `docs/guides/RESKIN.md` in order: names, colours, fonts, art by slot (+ MANIFEST), scenes and logo, app icon,
      sounds, then its checks. doctor's `shipped art files` and `app icon` turn PASS when every shipped manifest file
      exists at its size.

## 5. Economy and in-app purchases [Linux]
- [ ] `App/Resources/Tuning/rules.json`: `economy` (start coins, `startBoosters`, booster pack price) with an entry for
      **each of the module's booster ids**, `lives`, `rewards`, `streak`, `failChain` (a module's default chain for its own
      fail kind lives in its tuning file; rules.json wins for a kind it lists), `shop`. rules.json also carries the
      reference module's arrow keys (`tape`, `bump`, `pipe`, …) that ArrowEscape decodes; leave them unless you remove
      ArrowEscape from the build.
- [ ] `design/publish/iap.json` (the catalogue: ids, prices, grants, localised names), `rules.json shop`, and
      `App/Resources/StoreKit/<Product>.storekit` must agree:
      `python3 apps/<slug>/tools/release/meta.py iap-check` → `IAP OK`.

## 6. Strings, tutorials, unlock cards [Linux]
- [ ] Copy in `App/Resources/Strings/strings.tsv` (+ `l10n/`), 13 languages; the module's popup, booster and tutorial
      texts included. `python3 apps/<slug>/tools/strings/build.py` then `--check`; `selftest.py`, `coverage.py
      --strict-code`.
- [ ] `tools/strings/sources.json`: point it at this game's spec sections or trim it (doctor's WARN).
- [ ] Tutorials (`TutorialStep`s) and unlock cards from the plugin, captions as string keys.

## 7. Levels [Linux]
- [ ] Authored levels: the module's tools + validator (reference: `design/tools/gen_levels.py`, `build_levels.py`,
      `validate_levels.py`, `tools/levels/bundle_check.py --publish`), shipped in `App/Resources/Levels/`.
- [ ] Generated levels (SortPuzzle): the generator's tuning (`levels.salt`, `curve`) and the goldens
      (`tools/<module>/ref.py --write`, review the diff). doctor still FAILs `levels` for such a module (known gap).
- [ ] Same puzzle: replace the reference's levels (doctor's `levels are this game's own`).

## 8. Store texts [Linux]
- [ ] `design/publish/store/<locale>.json` (name, subtitle, promotional text, description) for every `store.locales`,
      `design/keywords.json`, `design/captions/<locale>.json`.
- [ ] `python3 apps/<slug>/tools/release/meta.py audit` → `AUDIT OK`, then `meta.py write` (fills `fastlane/metadata/`).
      Lessons: "Screenshots & ASO", "Localisation" groups.

## 9. Doctor green + every Linux check [Linux]
```sh
python3 tools/game.py doctor --game <slug>            # must end "0 FAIL"; explain every WARN (machine.env on Linux is expected)
python3 tools/game.py generate --game <slug> --check  # 0 files to change
python3 -m unittest discover -s tools/tests           # game.py's own tests
A=apps/<slug>
python3 $A/tools/strings/build.py --check && python3 $A/tools/strings/selftest.py && python3 $A/tools/strings/coverage.py --strict-code
python3 $A/tools/release/meta.py audit && python3 $A/tools/release/meta.py iap-check && python3 $A/tools/release/meta.py selftest
python3 $A/tools/skin/build.py --check && python3 $A/tools/skin/build.py --check-literals
python3 $A/tools/skin/art.py --check && python3 $A/tools/skin/variant.py --check && python3 $A/tools/uiart_gen.py --check
python3 $A/tools/harness_gate.py
# the module's own: e.g. python3 $A/tools/sortpuzzle/ref.py --check; ArrowEscape: tools/levels/bundle_check.py --publish,
# design/tools/validate_levels.py
```
All of these passed for `apps/mazeout` on Linux on 2026-09-30 (doctor: 105 PASS, 1 WARN = machine.env, 0 FAIL).

## 10. Build and test
- [ ] **[CI]** Push a `claude/**` branch. `ci.yml` is written for ONE game: `APP_DIR: apps/mazeout`, `doctor --game
      mazeout`, `ArrowOut.xcodeproj` / scheme `ArrowOut` / `ArrowOutTests`, and the arrow level steps. A second game needs
      those adapted (a CI change; a matrix over games is the likely shape). The repository is public, so hosted runners
      (macOS included) are free; if it goes private again, the account's Actions budget can stop CI (docs/ROADMAP.md).
- [ ] **[Mac]** `cp machine.env.example machine.env` (two simulators, README §3), then
      `sh apps/<slug>/tools/gen.sh`, `apps/<slug>/tools/build.sh A`, `apps/<slug>/tools/run.sh A`,
      `apps/<slug>/tools/core.sh`, `apps/<slug>/tools/test.sh A` (UI suites must pass twice in a row).
      At most two builds at once, 15 GB free (`docs/lessons/max-two-parallel-builds.md`, `disk-full-lies.md`).
- [ ] **[Mac]** Release: `CONFIG=Release apps/<slug>/tools/build.sh A`, then
      `sh apps/<slug>/tools/bench/release_gates.sh <Release .app> [<Debug .app>]` (placeholder, honesty, brand,
      provenance, SDK gates). Measure: `CONFIG=Measure apps/<slug>/tools/build.sh A`, then
      `sh apps/<slug>/tools/bench/measure_strip_check.sh <Release .app> <Measure .app> [<Debug .app>]` (the debug harness
      is in Measure, not in Release).
- [ ] **[Mac]** Play it: autoplay from a fresh install, look at every screen, the bench on the densest level
      (`apps/<slug>/tools/bench.sh`).
- [ ] **[Mac + Owner's phone]** `apps/<slug>/tools/owner-phone.sh` (Measure by default; `PHONE_CONFIG=Release` for the store
      build), boot without launch arguments to the real first run.

## 11. Screenshots [Mac]
- [ ] `python3 apps/<slug>/tools/capture/capture.py --store` (a Release build; entries from `tools/capture/manifest.json`),
      then `python3 apps/<slug>/tools/store/compose.py set --locale <loc> --raws <5 files> --home-plate <this game's file>`
      per locale. Look at every frame (`docs/lessons/screenshots-verify-content-not-count.md`).

## 12. Publish [Mac + Owner] — README §6, in order, every script `--dry-run` first
| README §6 step | Where |
|---|---|
| 0 Apple web session (`fastlane spaceauth`) | **Owner** (password + 2FA), every ≤ 30 days |
| 1 `fastlane create_app` (edit app name / SKU first) | Mac, needs the session |
| 2 `scripts/signing_setup.py --slug <slug> --bundle <bundle>` | Mac (keychain) |
| 3 `scripts/asc_consumables.py` (IAPs, review screenshot) | wherever `.env` + `keys/` are (the Mac) |
| 4 `scripts/rc_consumables.py` | same |
| 5 privacy page `privacy-<game>.html` on the legal site | **Owner approves** (it is public) |
| 6 store texts: `meta.py write` → `fastlane upload_meta_only` → `scripts/asc_keywords.py` | Mac |
| 7 screenshots: `scripts/asc_screenshots.py --slug <slug> --version 1.0.0` | Mac |
| 8 `fastlane upload_build` (→ TestFlight; wait for processing, never bump on "already used") | Mac |
| 9 `fastlane upload_privacy` (App Privacy label) | Mac, **Owner** may be asked for 2FA |
| 10 age rating (Deliverfile), availability | Mac |
| 11 `scripts/asc_submit.py --slug <slug> --bundle <bundle>` (`--uses-idfa` only if the game added an attribution SDK) | Mac; watch it 15+ min |
| 12 bookkeeping: commit, `docs/ROADMAP.md` status log, a lesson for anything new | any |

A TestFlight purchase test on the phone needs the owner's Face ID.

## Known gaps (open work before a game on a new module ships)
Found by SortPuzzle (phase 5). Closed since and green on CI (run 20): HUD widgets from `capabilities.hud`, the stuck /
out-of-moves offer popup (13 languages), module boosters in the shop and HUD, only the active module built, generic
frame metering; `SessionPlan` / `FeatureUnlock` moved to GameCore. Still open:

| Gap | Effect today | Needs |
|---|---|---|
| **SortPuzzle has no tutorials or unlock cards** | `tutorials` / `unlocks` are empty | content: `TutorialStep`s + strings |
| **Icons for module boosters and new popups** | `booster.undo.icon`, `booster.extraTube.icon`, `popup.stuck.icon` … are optional slots with a text fallback | art from the owner, mapped in `skin/art.json` |
| **Text fit of the new strings** | the 14 offer / booster strings are not measured | ctfit on the Mac |
| doctor's `levels` check assumes level files | a generated-level module FAILs `levels`, and its `puzzle.checks` never run (they run only after the files check passes) | `tools/game.py` change (e.g. a generated-levels flag) |
| `ci.yml` is single-game | a second game is not built or tested by CI | a CI change (APP_DIR / slug / product per game) |
| Arrow-specific tests are copied into every game | `Tests/` holds BoardEngine / LevelsBundle / arrow level tests; with `--puzzle` the level bundle is emptied, so some are expected to fail (not verified: nothing was built) | adapt or remove the reference module's tests in the new game |
| `new --puzzle` does not set the compile condition | the scaffold still runs ArrowEscape | add `PC_PUZZLE_<X>` by hand (step 3) |
| Other contract gaps (phase 2) | the move cue key is `cues.arrowTap` | when a module needs it |

Also unverified end to end: `new` for a second game built with Xcode (docs/ROADMAP.md phase 4), and a variant skin built
and screenshotted. SortPuzzle's Swift is compiled and tested on CI (core + app tests, run 19 onward).
