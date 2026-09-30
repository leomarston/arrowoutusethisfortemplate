# Make a new game from the template

A game = **the system** (shared: home, HUD, popups, shop, lives, coins, boosters, events, the offline "online-looking"
leaderboards, store tooling) + **a puzzle module** + **a skin** + **one config file** (`apps/<slug>/game.yml`).
The reference game is `apps/mazeout` (*Arrow Out*); its `game.yml` is the documented example of every key.

One tool drives the config side, from the repo root (Python 3 + PyYAML: `pip3 install -r requirements.txt`):

| Command | What it does |
|---|---|
| `python3 tools/game.py new <slug> --from mazeout --name "Brand" --bundle com.manycode.<x>` | scaffolds `apps/<slug>`: copies the generic parts, renames the old identity, writes `game.yml`, runs `generate` |
| `python3 tools/game.py generate --game <slug> --check` | lists what differs between `game.yml` and the files that repeat its values (exit 1 if anything) |
| `python3 tools/game.py generate --game <slug>` | writes those values (targeted: one regex group or one JSON value per place; nothing else moves) |
| `python3 tools/game.py doctor --game <slug> [--quick] [--strict]` | the checklist: PASS / WARN / FAIL per item; exit 0 only without FAIL (`--strict`: without WARN) |

Tests of the tool: `python3 -m unittest discover -s tools/tests` (about 15 s).

## The steps

### 1. Scaffold
```
python3 tools/game.py new <slug> --from mazeout --name "Brand Name" --bundle com.manycode.<x> \
    [--store-name "Brand Name: Keyword Phrase"] [--puzzle <module-id>] [--bans "Original Name,Its Publisher"] \
    [--product BrandName] [--privacy-url https://…/privacy-<brand>.html]
python3 tools/game.py doctor --game <slug>
```
`<slug>` is the folder name (`[a-z][a-z0-9-]*`); keep it neutral (it ends up in build paths the release gates scan).
`--bans` is the ORIGINAL game's names (the one you are cloning); without it the reference's list is kept.

**Copied** (the system and the tools): `project.yml`, `App/` (all code; tuning, strings, fonts, sounds, social names,
`.storekit`), `Packages/`, `Tests/`, `UITests/`, `tools/`, `skin/`, the art toolchain and slot list (`art/MANIFEST.json`,
`art/tools`, `art/pipeline`, `art/ui/{code,recipes,src,tools}`, `art/*.md`), `design/ui-tokens*.json`, `design/fonts*`,
`design/social/` (the simulated world's data), `design/publish/iap.json`, `fastlane/{Appfile,Deliverfile,Fastfile}` and
the account-level metadata (`app_privacy_details.json`, `app_rating_config.json`, `copyright.txt`,
`review_information/`), `.gitignore`. With the **same** puzzle module also `design/levels.json`, `level-order.json`,
`LEVELS.md`, `design/tools/` and the level bundle.

**Not copied** (the reference's history or its own content): `research/`, `PLAN.md`, `SPEC.md`, design notes and spikes,
release evidence, store texts (`design/publish/store/`), captions, keywords, `fastlane/metadata/<locale>/`,
screenshots, rendered art (`art/out`, `art/ui/out`, `art/review`, `art/lanes`), the app icon images; with a different
puzzle module also the levels and level tools.

**Renamed** in every code/config file: the bundle id (also the IAP prefix, queue labels, log subsystem), the product
(`ArrowOut` -> `BrandName`, incl. `<product>Tests`, `<product>.app`, `import <product>`, the `.storekit` file; art ids
such as `logoArrowOut` are skin slots and stay), `apps/<old-slug>` paths, the brand name, and the bundle's last segment
(SKU, profile name, RevenueCat offering). Then `generate` writes the rest from `game.yml`.

Right after `new`, doctor reports exactly these TODOs (tested in `tools/tests/test_game.py`):
- `FAIL store texts` - `design/publish/store/<locale>.json` missing (step 5)
- `FAIL shipped art files` + `FAIL app icon` - the skin is not rendered yet (step 3)
- `WARN levels are this game's own` - same puzzle: the levels are still the reference's copy (step 5)
- `WARN strings coverage sources` - `tools/strings/sources.json` points at the reference's `design/SPEC-*.md`; write this
  game's spec sections or trim the file (then `tools/strings/coverage.py` and `selftest.py` pass again)
- with another puzzle module: `FAIL levels` (no level bundle yet); with `--bans`: `FAIL store-text gate` until
  `tools/release/loc.py BANNED_ALL` gets patterns for the new names (hand-kept list, see "Manual" below)
- `WARN machine.env` on any machine without it (only the Mac needs it)

### 2. The puzzle module
Same puzzle as the reference: nothing to do. A new puzzle: follow `docs/architecture/PUZZLE-MODULE.md` (the contract:
levels, deterministic session, board, fail rules, boosters, HUD widgets, bot). Set `puzzle.module` in `game.yml` and list
the module's own level checks under `puzzle.checks` (commands run from `apps/<slug>`; doctor runs them). Until phases
1-2 of `docs/ROADMAP.md` land, the reference puzzle's code lives in `App/Board`, `App/Game` and the core package; a new
module replaces those parts.

### 3. Reskin
Colours: `docs/SKIN.md` (`skin/colors.json` -> `tools/skin/build.py`). Art: `art/PIPELINE.md` + `art/STYLE.md`; every slot
of `art/MANIFEST.json` whose status is `done`/`graded` must exist at its size (doctor checks it), plus the three app
icon images in `App/Resources/Assets.xcassets/AppIcon.appiconset/`. Fonts in `App/Resources/Fonts` (+ `UIAppFonts` in
`project.yml`), sounds in `App/Resources/Sounds`, event names in the strings. Copy the category's conventions, never an
original's assets (CLAUDE.md).

### 4. Configure (`apps/<slug>/game.yml`)
Edit, then `python3 tools/game.py generate --game <slug>` and `doctor`:
- `identity` (brand, bundle, team, profile), `store` (name, keyword seed, category, URLs, support e-mail, copyright,
  locales), `features` (ad attribution off by default, notifications, iPad, rating level), `events` (unlocks, weekly
  rotation), `social` (world seed/epoch, rotation seed/epoch), `brand_bans` (the original's names).
- Economy numbers stay in `App/Resources/Tuning/rules.json` (economy, lives, boosters, rewards, streak, fail chain, shop)
  and the IAP catalogue in `design/publish/iap.json`; after changing products run
  `python3 apps/<slug>/tools/release/meta.py iap-check` (iap.json == rules.json shop == `.storekit`).

**Why game.yml references the tuning instead of copying it.** The app decodes `rules.json` at run time and the store
scripts read `iap.json` directly; ~200 economy numbers mirrored in `game.yml` would be a second source that can drift.
`game.yml` owns the values that are repeated across *files of different kinds* (identity, store, flags, event switches,
seeds, bans): those are what a rename used to miss (README §4 counts 23-196 files per value). doctor checks the
referenced files exist, hold the listed sections, and agree with each other and with the bundle id.

**What generate writes** (doctor checks every one): `project.yml` (`PC_BRAND_NAME`, `DEVELOPMENT_TEAM`,
`bundleIdPrefix`, the three `PRODUCT_BUNDLE_IDENTIFIER`s, `TARGETED_DEVICE_FAMILY`, the known-regions locales);
`fastlane/Appfile`, `Deliverfile` (category + 2 subcategories), `Fastfile` (app identifiers, profile mapping,
`create_app` name + SKU, the IPA provenance slug), `fastlane/metadata/copyright.txt` and every locale's
`privacy_url.txt`/`support_url.txt`; `tools/slot.sh`, `play-watch.sh`, `bench/bench.py`, `capture/capture.py`
(bundle), `tools/release/meta.py` (IAP prefix), `tools/release/loc.py` (`BRAND`, `SEED`, `NAME_EN`, `PRIVACY`,
`SUPPORT`, `COPYRIGHT`, `LOCALES`), `tools/strings/build.py` (`BRANDS` = bans + our names),
`tools/bench/release_gates.sh` gate 3, `Tests/AppTests/BrandTests.swift` (`bannedExact`, the product-name assertion);
`.storekit` team, `iap.json` (`productPrefix`, `appName`, `locales`), `rules.json shop.productPrefix` (when present),
`Tuning/game.json` (support e-mail, notifications, rating level), `Tuning/social.json` (unlocks, rotation, rotation
seed/epoch), `art/MANIFEST.json` brand; the Swift constants `SocialWorldModel.worldSeed`, the shipped world epoch,
`SocialCalendar.epoch`, `ShopCatalog.productPrefix` (until phase 1 moves them to config). A changed bundle id or brand
name is also replaced everywhere else in code/config (the old value is read from `project.yml`).

**(new only) keys:** `id` (the folder) and `identity.product` (target, scheme, `.storekit` file, `import`) are structural;
doctor checks them, generate never renames them. To change one later, run `new` again or rename by hand (README §4).

**Manual (doctor tells you when they are missing a ban):** `tools/release/loc.py BANNED_ALL` (the store-text gate also
holds competitors and "online" claims), `tools/bench/release_gates.sh` gate 3 file-name / data-file greps and gate 7c
`WORDS`, `BrandTests.bannedAnyCase`, `tools/strings/l10n_review.py BRAND_RE`.

### 5. Strings, levels, store texts
- Strings: `App/Resources/Strings/strings.tsv` (+ `l10n/`) -> `python3 apps/<slug>/tools/strings/build.py` (doctor runs
  `--check`). Never spell the brand in copy: interpolate `Brand.name`.
- Levels: the module's tools (reference: `design/tools/gen_levels.py`, `build_levels.py`, `apps/<slug>/tools/levels/`).
- Store texts: `design/publish/store/<locale>.json` (name, subtitle, promotional text, description) for every
  `store.locales`, `design/keywords.json`, `design/captions/`; then `python3 apps/<slug>/tools/release/meta.py audit` and
  `meta.py write` (fills `fastlane/metadata/<locale>/`). Name rules: `docs/lessons/app-naming-keyword-first.md`.

### 6. Doctor until green
`python3 tools/game.py doctor --game <slug>` must end with `0 FAIL`; every remaining WARN must be explained
(`machine.env` on a Linux/cloud session is expected). `--quick` skips the puzzle's level checks and the store audit while
iterating.

### 7. Build and test
- **Cloud session (no Xcode):** push a `claude/**` branch and read GitHub Actions (`.github/workflows/ci.yml`; its
  `APP_DIR` names the game folder).
- **Mac:** `cp machine.env.example machine.env` (this Mac's simulators), then `sh apps/<slug>/tools/gen.sh`,
  `apps/<slug>/tools/build.sh A`, `apps/<slug>/tools/run.sh A`, `apps/<slug>/tools/test.sh A`,
  `apps/<slug>/tools/core.sh` (README §3). At most two builds at once (`docs/lessons/max-two-parallel-builds.md`).
- Release binary gates: `sh apps/<slug>/tools/bench/release_gates.sh <Release .app>`.

### 8. Screenshots
`python3 apps/<slug>/tools/capture/capture.py --store …` (scripted captures from `tools/capture/manifest.json`), then
`python3 apps/<slug>/tools/store/compose.py set --locale <loc> --raws <5 files>`. Look at every frame.

### 9. Publish
README §6, in order, every script with `--dry-run` first; check the matching group of `docs/lessons/README.md` before
each store, signing or payment step. The privacy page (`store.privacy_url`) must be live before submitting.
