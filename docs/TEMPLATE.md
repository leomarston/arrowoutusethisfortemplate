# Make a new game from the template (map)

A game = **the system** (shared: home, HUD, popups, shop, lives, coins, boosters, events, the offline "online-looking"
leaderboards, store tooling) + **a puzzle module** + **a skin** + **one config file** (`apps/<slug>/game.yml`).
The reference game is `apps/mazeout` (*Arrow Out*, module `arrow-escape`); its `game.yml` is the documented example of every
key. A second module, SortPuzzle (`sort-puzzle`), is compiled into the same app and selected at compile time.

**Where to read what**

| You want to | Read |
|---|---|
| make a game, start to App Store, in order (with what needs the owner's Mac, and the known gaps) | [`docs/guides/NEW-GAME.md`](guides/NEW-GAME.md) |
| write a new puzzle module (worked example: SortPuzzle) | [`docs/guides/WRITE-A-PUZZLE.md`](guides/WRITE-A-PUZZLE.md) |
| reskin: colours, fonts, names, art slots, scenes, sounds | [`docs/guides/RESKIN.md`](guides/RESKIN.md) |
| the puzzle contract itself (types, rules, v1.1) | [`docs/architecture/PUZZLE-MODULE.md`](architecture/PUZZLE-MODULE.md) |
| the skin's file formats and tools in depth | [`docs/SKIN.md`](SKIN.md) |
| take one piece (pause menu, shop, leaderboard, sounds, an event ...) into a game or project: the component kit | [`docs/guides/KIT.md`](guides/KIT.md), `kit/catalog.html` |
| the config tool and `game.yml` (this file, §1 and §4) | below |
| build / run / test commands, the rename checklist, the store pipeline | `README.md` §3, §4, §6 |
| research and clone an original game (the full autonomous run) | `GAMEPROMPT.md` / `GAMEPROMPTMAX.md` |
| where the template work stands | `docs/ROADMAP.md` |

One tool drives the config side, from the repo root (Python 3 + PyYAML: `pip3 install -r requirements.txt`):

| Command | What it does |
|---|---|
| `python3 tools/game.py new <slug> --from mazeout --name "Brand" --bundle com.manycode.<x>` | scaffolds `apps/<slug>`: copies the generic parts, renames the old identity, writes `game.yml`, runs `generate` |
| `python3 tools/game.py generate --game <slug> --check` | lists what differs between `game.yml` and the files that repeat its values (exit 1 if anything) |
| `python3 tools/game.py generate --game <slug>` | writes those values (targeted: one regex group or one JSON value per place; nothing else moves) |
| `python3 tools/game.py doctor --game <slug> [--quick] [--strict]` | the checklist: PASS / WARN / FAIL per item; exit 0 only without FAIL (`--strict`: without WARN; `--quick` skips the puzzle's level checks and the store audit) |

Tests of the tool: `python3 -m unittest discover -s tools/tests` (28 tests, about 15 s).

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

Right after `new`, doctor reports these TODOs (tested in `tools/tests/test_game.py`; the list was re-checked on scratch
scaffolds, same puzzle and `--puzzle sort-puzzle --bans …`, on 2026-09-30; what fixes each: `docs/guides/NEW-GAME.md` §1):
- `FAIL store texts` - `design/publish/store/<locale>.json` missing (step 5)
- `FAIL shipped art files` + `FAIL app icon` - the skin is not rendered yet (step 3)
- `WARN levels are this game's own` - same puzzle: the levels are still the reference's copy (step 5)
- `WARN strings coverage sources` - `tools/strings/sources.json` points at the reference's `design/SPEC-*.md`; write this
  game's spec sections or trim the file (then `tools/strings/coverage.py` and `selftest.py` pass again)
- with another puzzle module: `FAIL levels` (no level bundle yet); with `--bans`: `FAIL store-text gate`, `FAIL gate 3
  file names` and `FAIL l10n review` until `game.yml brand_ban_forms` gets patterns / stems for the new names (it keeps
  the reference's; see "Ban lists" below), then `generate`
- `WARN rotation_ref.py EPOCH` / `seed (reference)` - `design/publish/tools/rotation_ref.py` (the frozen rotation reference) is
  not copied; explain the WARN, or copy and re-derive it when the game changes the rotation seed / epoch (§4)
- `WARN machine.env` on any machine without it (only the Mac needs it)

### 2. The puzzle module
Same puzzle as the reference: nothing to do. A new puzzle: **`docs/guides/WRITE-A-PUZZLE.md`** (core target, session, board,
plugin, entry, tests, the Python reference and goldens, the `ActivePuzzle` switch), with SortPuzzle as the worked example;
the contract is `docs/architecture/PUZZLE-MODULE.md`. In `game.yml`: `puzzle.module` (the module's id) and `puzzle.checks`
(the module's own level checks, run from `apps/<slug>` by doctor; a `.py` path first, not `python3`, e.g.
`tools/sortpuzzle/ref.py --check`). `new --puzzle <id>` records the module but does not switch the app to it: the
`PC_PUZZLE_<X>` compilation condition is a hand edit of `project.yml` (WRITE-A-PUZZLE.md §7). `App/Game` is genre-agnostic
and stays as it is; until phase 1's folder move, the reference puzzle's board lives in `App/Board`, a new module's in
`App/Puzzles/<Module>/`.

### 3. Reskin
**`docs/guides/RESKIN.md`** (the ordered steps and what is still not data), `docs/SKIN.md` (formats and tools). In short:
colours in `skin/colors.json` (`tools/skin/recolor.py`, `build.py`), fonts `skin/fonts.json`, non-copy names
`skin/names.json`, art by SLOT in `skin/art.json` -> the ids of `art/MANIFEST.json` -> files; the home / Loading scenes
`skin/scenes.json`; sounds `App/Resources/Sounds` + `Tuning/audio.json`; copy in the strings. doctor checks that every file
the manifest ships exists at its size, plus the three app icon images in
`App/Resources/Assets.xcassets/AppIcon.appiconset/`. Copy the category's conventions, never an original's assets (CLAUDE.md).

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
`tools/bench/release_gates.sh` gate 3, `Tests/AppTests/BrandTests.swift` (`bannedExact`, the product-name assertion),
the ban lists below;
`.storekit` team, `iap.json` (`productPrefix`, `appName`, `locales`), `rules.json shop.productPrefix` (when present),
`Tuning/game.json` (support e-mail, notifications, rating level), `Tuning/social.json` (unlocks, rotation, rotation
seed/epoch), `art/MANIFEST.json` brand. A changed bundle id or brand name is also replaced everywhere else in
code/config (the old value is read from `project.yml`).

**Generated whole files:** `Packages/PathCore/Sources/GameCore/Config/GameConfig.generated.swift` (`enum GameConfig`: world
seed, world epoch, calendar epoch, rotation seed, IAP product prefix). The core reads these only from there
(`SocialWorldModel.worldSeed`, `SocialWorldModel.shipped.epoch`, `SocialCalendar.epoch`, the `EventRules` calendar and
rotation defaults, `ShopCatalog.productPrefix`), so its sources hold no game's value and the package still builds and
tests on its own. doctor fails while the file is stale or missing, and when one of these values is spelled as a literal
in `App/` or `Packages/*/Sources` outside it (tests may pin them). The social world's Python reference
(`design/social/tools/socialsim`, frozen by `design/social/FROZEN`) and `design/publish/tools/rotation_ref.py` are only
READ: a new seed or epoch means re-deriving that reference, its fixtures and the goldens, then re-freezing.

**Ban lists** (`game.yml brand_ban_forms`; generate writes, doctor checks each still catches every `brand_bans` name):
`store_patterns` -> `tools/release/loc.py BANNED_BRAND` (the store-text gate; `BANNED_ALL` = it + the category words,
competitors and "online" claims, which stay in loc.py); `file_stems` -> `release_gates.sh` gate 3 file-name grep;
`binary_words` -> gate 7c `WORDS` / `NEVER_SDK`; `review_patterns` -> `tools/strings/l10n_review.py BRAND_RE`. Derived
from `brand_bans`: the multi-word names in any case, joined and spaced (`BrandTests.bannedAnyCase`, gate 3's data-file
`grep -qi`), and the rest case-sensitive (gate 3's `grep -q`).

**(new only) keys:** `id` (the folder) and `identity.product` (target, scheme, `.storekit` file, `import`) are structural;
doctor checks them, generate never renames them. To change one later, run `new` again or rename by hand (README §4).

**Still hand-kept:** the category words, competitors and "online" claims of `loc.py BANNED_ALL`; gate 7c's provenance
words (`recorded`, `video`, `research/`, version tags); `BrandTests`' nickname check (`bannedAnyCase + ["maze"]`) and
`Packages/PathCore/Tests/tools/soc_ship_names.py BRAND` (the shipped name bank's filter, frozen output).

### 5-9. Strings, levels, store texts, doctor, build, screenshots, publish
In order, with the commands and which steps need the owner's Mac: **`docs/guides/NEW-GAME.md`** §5-§12 (strings and
tutorials, levels, store texts and `meta.py audit`, doctor until `0 FAIL`, CI / Mac build and tests, release gates,
screenshots, then README §6 for the store). Before each store, signing or payment step read the matching group of
`docs/lessons/README.md`.
