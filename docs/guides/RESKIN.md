# Reskin a game

The skin is everything a player sees that belongs to one game: colours, fonts, names, art, the home and Loading scenes,
the logo, sounds and texts. This guide is the ordered "how"; the reference with every file format, tool option and the
reasons is `docs/SKIN.md`. The goal is a complete reskin **without changing Swift**; section 9 lists what still needs code.

Run everything from the game folder (`cd apps/<slug>`; the reference is `apps/mazeout`). Every tool here is Python 3
stdlib and runs on Linux, except where a step says "Mac".

**The copying line (CLAUDE.md):** copy the category's conventions, never an original's assets. No extracted, traced or
resampled art, audio, fonts, screenshots or levels of another game in `skin/`, `art/`, `App/Resources` or git. Colours and
proportions measured from the original are conventions; its files are not.

## 1. Brand and names
| What | Source | Then |
|---|---|---|
| Display name | `game.yml identity.brand_name` (one source; `Brand.name` in code, `PC_BRAND_NAME` in project.yml) | `python3 ../../tools/game.py generate --game <slug>` |
| Store name | `game.yml store.name` (+ `design/publish/store/<locale>.json`) | naming rules: `docs/lessons/app-naming-keyword-first.md` |
| Names that are not copy | `skin/names.json` (`podiumSampleNames`) | `python3 tools/skin/build.py` |
| Event, character, currency, item names; all copy | `App/Resources/Strings/strings.tsv` (13 languages; the English text is the key) | `python3 tools/strings/build.py`, then `--check` |

Never spell the brand in copy or Swift: interpolate `Brand.name` (the CI brand step and `BrandTests` fail on a literal).

## 2. Colours
1. **Move whole colour families** (keeps every ramp's lightness structure):
   ```sh
   python3 tools/skin/recolor.py --list-families                       # what each family holds
   python3 tools/skin/recolor.py --map teal=#3A6FE0 --map pink=#7B3FE4 --preview /tmp/recolor.html --dry-run
   python3 tools/skin/recolor.py --map teal=#3A6FE0 --map pink=#7B3FE4
   ```
2. **Fine-tune palette entries** by hand in `skin/colors.json` `palette` (every token and ui entry using it follows).
3. **Override one token** (`tokens`, the UI code's colours) or **one ui.json colour** (`ui`, the colours `Tuning/ui.json`
   references as `"@<ui id>"`) by pointing it at another palette name or its own `"#RRGGBB"`.
4. The puzzle board's colours are `puzzle.<board>.*` tokens in the same file (SortPuzzle: `puzzle.sortBoard.*`); the
   reference module ArrowEscape still takes its board colours from `Tuning/board.json` (the module owns them).
5. Regenerate and check:
   ```sh
   python3 tools/skin/build.py            # rewrites SkinColors.generated.swift, Tuning/ui-colors.json, the test table
   python3 tools/skin/build.py --check    # stale output, a raw colour in ui.json, a dangling reference
   python3 tools/skin/build.py --check-literals   # no colour literal in App/Shell, App/FX, App/Puzzles, GlossyChrome
   ```
Raster art keeps its baked colours: recolouring the chrome does not recolour a PNG (section 4).

## 3. Fonts
Put the new `.ttf` / `.otf` files (OFL or Apache, with their licence) in `App/Resources/Fonts/`, delete the old ones,
write each role's PostScript and file name in `skin/fonts.json` (`faces.black` draws every label, `faces.blackItalic` the
event logos), run `python3 tools/skin/build.py`: it regenerates `SkinFonts` and rewrites `UIAppFonts` in `project.yml` and
`App/Info.plist`. Give font files a neutral name (never the brand's initials). A face with other proportions may need
`text.*.size` / `tracking` retuned in `Tuning/ui.json` (numbers). Font matching by rendering: GAMEPROMPT.md §3.5 "Fonts".

## 4. Art, by slot
Swift names **slots** (`UIArt.currencyCoinIcon`, `ArtRig.homeCharacterMain`), never files. The skin maps each slot to an
`art/MANIFEST.json` id, and the manifest maps the id to a file, size and group.
1. Make the new rasters with the art pipeline (`art/PIPELINE.md`, style guide `art/STYLE.md`): UI rasters into
   `art/ui/out/`, rendered 3D / puppet rigs into `art/out/`. **Mac:** the renderers are macOS tools (`art/ui/tools/svgr.swift`,
   the RealityKit renderer in `art/pipeline/render/`); the Python recipes and checks run anywhere.
2. Register each file in `art/MANIFEST.json` (id, route, size, status); retire what no longer ships.
3. Point the slots at them in `skin/art.json` (`slots`: raster slots, `rigs`: puppet slots; several slots may share a file).
   Slot names: `currency.*`, `hud.*`, `lives.*`, `booster.<id>.icon`, `reward.*`, `avatar.<n>`, `shop.*`, `nav.<tab>.icon`,
   `home.*`, `loading.*`, `logo.main`, `logo.part.<id>`, `event.<id>.<thing>`, `puzzle.<sprite>` (full list: SKIN.md §4).
4. `python3 tools/skin/build.py` (regenerates `UIArt.swift`, `ArtRig`, `SkinScenes`), then `python3 tools/skin/art.py --check`.
   It fails on an unknown / retired manifest id, a missing file, a shipped file no slot maps, a slot named as a string that
   the skin lacks, and any Swift string that names an art file.
5. The app icon: `App/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png`, `icon-1024-dark.png`,
   `icon-1024-tinted.png` (doctor checks all three).

A new game scaffolded by `tools/game.py new` has the reference's slot list and manifest but **no rendered files**: doctor
reports `FAIL shipped art files` (228 of 228 missing on a scaffold made 2026-09-30) and `FAIL app icon` until they exist.

## 5. Scenes and the logo
- **Home and Loading** are lists in `skin/scenes.json`: `home.back` (behind the level plate and Play), `home.front`,
  `loading` (backdrop, logo, cast), each layer an art slot at a ui.json `frames` key (with an `at` default), a rig, or the
  centrepiece; `rigParts` splits a character around another layer. Motion stays in ui.json `puppet.<rig folder>`.
- **Boot / Loading logo:** the `logo.main` slot at ui.json `frames.loading.logo`.
- **Win logo:** ui.json `win.logo` (parts, layers, anchors, keyframes) drawing `logo.part.<id>` slots; the celebration
  timing is ui.json `win.*`. Limit: the part ROLES are still Arrow Out's part ids in Swift (section 9).
- `python3 tools/skin/build.py` + `art.py --check` after every change.

## 6. Sounds and music
Replace `App/Resources/Sounds/<SoundID>.wav` (same file names; the id set is the closed `SoundID` enum in
`App/Contracts/AudioContract.swift`, adding one is a code change) and tune `Tuning/audio.json` (`cues`: which moment plays
which sound, `gain`, `music`, `haptics`). Make them with the synthesis tools (`tools/audio/sfx.py`, `music.py`,
`instruments.py`) and check them with `tools/audio/check.py` (+ `check_selftest.py`). Never use audio extracted from the
original, not even as a synthesis input.

## 7. The variant check (a skin is data only)
`skin/variants/<name>/colors.json` is an alternate palette stored as an overlay (`skin/variants/cobalt`: teal → #3A6FE0,
pink → #7B3FE4). It is not shipped. The check proves a skin change is data only:
```sh
python3 tools/skin/variant.py --check        # each variant builds with build.py's own generators and differs from the
                                             # active skin ONLY in colour values (same files, lines, names)
python3 tools/skin/variant.py --write NAME --map teal=#3A6FE0   # make one
python3 tools/skin/variant.py --apply NAME   # try it in the app (then build.py + a build on the Mac;
                                             # `git checkout skin/colors.json` goes back)
```
Verified on Linux 2026-09-30: `variant cobalt: builds; only colour values change`. Not yet done: the app built and
screenshotted on a variant (Mac), and an ART variant (`skin/art.json` pointing at other files).

## 8. Checks after a reskin
```sh
python3 tools/skin/build.py --check && python3 tools/skin/build.py --check-literals
python3 tools/skin/art.py --check && python3 tools/skin/variant.py --check
python3 tools/uiart_gen.py --check
python3 tools/strings/build.py --check
python3 ../../tools/game.py doctor --game <slug>          # from the repo root: python3 tools/game.py doctor --game <slug>
```
Then on the Mac (or CI): `tools/gen.sh`, build, `tools/test.sh A -only-testing:<Product>Tests` (`SkinColorsTests`,
`SkinArtTests`, `UIArtBundleTests`, the font tests compare the compiled tables with the JSON), and **look** at every
screen: capture them (`tools/capture/capture.py`) and open the images. A skin nobody looked at is not done.

## 9. What is still not skin data (needs Swift or a tool change)
From docs/SKIN.md §6 and the phase-3/5 notes:

| Part | Today | Workaround until it is data |
|---|---|---|
| Screen layouts | many shell frames and sizes are Swift defaults of ui.json reads, some plain literals | keep the reference layout, or move the value into ui.json (a code change) |
| Per-game strings folder | copy lives in `App/Resources/Strings/*.tsv` inside the game folder | edit them there (each game folder has its own copy) |
| Launch colours | `App/GameApp.swift` boot diagnostics / Loading stand-in and the `LaunchBackground` colour asset are outside the skin scan | edit `Assets.xcassets/LaunchBackground.colorset` by hand |
| Art ink boxes | `S2Chrome.swift` `ArtInk`: measured alpha boxes of the OLD HUD / popup rasters, Swift literals keyed by slot | a new file in such a slot is placed by the old file's box: draw it on the same canvas and margins, or change ArtInk |
| Win logo structure | the part tree's roles (letters, bend, the OUT! echo group, orders) are Arrow Out's part ids in `WinLogoSequence.swift` | keep those part ids for your parts, or change the code |
| Screenshot home plate | `tools/store/compose.py set --home-plate` defaults to the reference's `art/out/homeWorkshop@3x.png` | pass `--home-plate` with the new game's file |
| Puzzle colours of ArrowEscape | `Tuning/board.json`, not skin tokens | edit board.json (module data) |
