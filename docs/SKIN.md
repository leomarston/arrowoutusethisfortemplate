# Skin: reskinning a game made from this template

A game = the shared system + a puzzle module + a **skin** + a config (see `docs/ROADMAP.md`). The skin is everything a
player sees that is specific to one game: colours, art, fonts, sounds and names. The goal is a complete reskin **without
changing Swift**. Colours (the UI code's and ui.json's), fonts, the non-copy names, the art (by slot) and the home / Loading
scenes work this way today; sounds and the brand name already were data elsewhere (section 3); section 5 is the proof (a
second colour skin that `variant.py --check` builds from data alone) and section 6 what is still not skin data.

**The ordered how-to is `docs/guides/RESKIN.md`**; this file is the reference behind it (formats, tools, reasons).

Everything the skin generates is written by one command and checked by CI's Linux job (and `tools/game.py doctor`):
```sh
cd apps/mazeout
python3 tools/skin/build.py            # validate skin/*.json, rewrite every generated file (colours, fonts, names, art, scenes)
python3 tools/skin/build.py --check    # (CI, game.py doctor) stale output, a colour left in ui.json, a dangling reference
python3 tools/skin/art.py --check      # (CI) the art/scene rules on the Swift sources too (section 4)
```

## 1. Colours

### How they are stored

| File | What it is | Edit it? |
|---|---|---|
| `apps/mazeout/skin/colors.json` | `palette`: named colours (`"teal.42": "#00706B"`). `tokens`: every colour the UI code draws, by a stable id (`"popups.popupChrome.chromePalette.blue.face.0": "teal.66h"`) pointing at a palette name (or at a `#RRGGBB` of its own). `ui`: every colour `Tuning/ui.json` names, by its ui.json path (`"colors.panel.fieldRim": "teal.59c"`) | **yes**: this is the source |
| `apps/mazeout/App/Shell/Components/SkinColors.generated.swift` | `enum Skin { static let <token>: UInt32 = 0xRRGGBB }`: one compile-time constant per token | no, generated |
| `apps/mazeout/Tests/AppTests/SkinColorsTable.generated.swift` | token id to constant table for `SkinColorsTests` | no, generated |
| `apps/mazeout/tools/skin/literal_allowlist.json` | hex numbers in the UI code that are not colours (an RNG seed) | only when you add one |
| `apps/mazeout/App/Resources/Tuning/ui-colors.json` | `{"colors": {ui id: "#RRGGBB"}}`: the `ui` section resolved, which `Tuning.load` reads | no, generated |
| `apps/mazeout/App/Resources/Tuning/ui.json` | geometry, timings, text styles; its colour slots are `"@<ui id>"` references (see "ui.json" below) | numbers yes; colours in the skin |

The UI code (`App/Shell`, `App/FX`, `App/Puzzles`, `art/ui/code/GlossyChrome.swift`) uses `Skin.<name>` wherever it used a colour
literal before, e.g. `Color(hex: Skin.popupsPopupChromeCardBevel0)`, `UIColor(rgb: Skin.fxConfettiConfettiSpecColors2)`,
`t.color("card.fill", Skin.popupsSettingsPopupCardFill)`. Each call site converts the constant exactly as it converted
the literal it replaced, so Arrow Out renders pixel for pixel as before (the codemod's `--verify` proved every value; see
below). The constants are plain `static let`s: the compiler checks every use and folds the value; there is no lookup at
run time.

**Reading the names.** A token id is `<area>.<file>.<scope>.<role>[.<n>]`:
- `area`: `components`, `home`, `hud`, `pages`, `popups`, `profile`, `shop`, `social`, `shell` (App/Shell/*.swift),
  `fx`, `art` (GlossyChrome), and `puzzle` for a puzzle module's board in `App/Puzzles` (named by hand,
  `puzzle.<board>.<role>`: SortPuzzle's 17 `puzzle.sortBoard.*`; the codemod would file such a literal under `art`).
- `file`: the Swift file (`shopView` = ShopView.swift).
- `scope`: the ui.json key when the colour is a Tokens default (`popup.ribbon.top`), else the type and member it sits in
  (`priceButton`, `winTier.frame`), a `case .hard` or a ternary branch (`me` / `notMe`, `hard` / `notHard`).
- `role`: what the colour feeds (`fill`, `stroke`, `outline`, `face`, `rim`, `stops`, `colors` …) and array positions
  (`.0`, `.1` = gradient stops top to bottom). `.v2`, `.v3` separate different colours that would get the same id.
- The Swift name is the id camel-cased: `shop.shopView.priceTag.st.outline` -> `Skin.shopShopViewPriceTagStOutline`.
- Ids ending in `.hex` are `String` tokens (`"#RRGGBB"`), used where the code passes a hex string default to a tuning read.

**Palette names** are `<family>.<L*>` with a letter for colours sharing both (`teal.42`, `teal.42b`). The family is the
colour's hue group in the reference skin (OKLCh hue windows): `neutral`, `cream`, `maroon` (dark reds), `brown` (dark
oranges/yellows: ink outlines, wood), `red`, `orange`, `yellow`, `lime`, `green`, `teal`, `cyan`, `blue`, `indigo`,
`violet`, `magenta`, `pink`; `L*` is its CIELAB lightness (0 black … 100 white). Names are kept when a colour changes,
so after a recolour `teal.42` is "the colour that was Arrow Out's teal at L* 42".
`python3 apps/mazeout/tools/skin/recolor.py --list-families` shows what each family holds today:
Arrow Out has 1,063 palette colours (every distinct value the UI draws, exact: merging near-equal ones would change
pixels) behind 1,681 tokens (1,664 for the shell + 17 for SortPuzzle's board) and 657 ui.json colours; teal (346 colours, the D1 chrome), pink (135, Super Hard / events),
orange (110), yellow (102), neutral (87), red (87), maroon (81), brown (57), cream (40) and a few confetti/firework
accents.

### Reskin the colours: three ways, from coarse to fine

1. **Move whole families** (the usual first step):
   ```sh
   cd apps/mazeout
   python3 tools/skin/recolor.py --map teal=#3A6FE0 --map pink=#7B3FE4 \
       --preview /tmp/recolor.html --dry-run            # look at the before/after sheet first
   python3 tools/skin/recolor.py --map teal=#3A6FE0 --map pink=#7B3FE4
   ```
   Each colour of a family keeps its CIELAB lightness L* (so every ramp: face, rim, outline, gradient stops, highlights
   keeps its structure), its chroma relative to the family's most saturated colour, and its hue offset from it; the
   family's anchor takes the new colour's hue and chroma. Options: `SELECT=FROM>TO` picks the anchor, `--lightness shift`
   moves the whole ramp by the anchor's L* difference instead, `--hue-spread 0.5` compresses the family's hue spread,
   `hue:160-212` / `name:teal.42,teal.44` select by hue window or by name, `--config rules.json` keeps the rules in a
   file. This is the D1 reskin's method (`tools/palette_map.py`, `art/ui/src/d1_skin.py`) in stdlib Python. (`palette_map.py`
predates the skin: it read ui.json's literal colours, which are now references; `recolor.py` is the tool.)
2. **Edit palette entries** in `skin/colors.json` by hand (change `"teal.42": "#00706B"`): every token and ui entry using
   that entry follows.
3. **Override one token or one ui.json slot**: point its `tokens` / `ui` entry at another palette name or give it its own
   `"#RRGGBB"` (recolour moves own literals too, by an equal palette colour or the first matching rule).

Then, always:
```sh
python3 tools/skin/build.py            # validates the skin, rewrites the generated Swift + ui-colors.json
python3 tools/skin/build.py --check    # (CI) fails if they are stale
tools/gen.sh && tools/build.sh …       # build the app as usual (README §3); nothing else changes
```

### ui.json

`App/Resources/Tuning/ui.json` (from `design/ui-tokens.json`) holds the measured geometry, timings and text styles of the
shell, and 657 colour slots: the values that **override** the compiled defaults of the ui.json-keyed reads
(`t.color("popup.ribbon.top", Skin.…)`, `t.text(…)` fill / outline / drop colours, `t.stops(…)` gradients, the toast, the
freeze frost and the FX palettes). ui.json itself names **no colour**: each slot is a reference
```json
"fieldRim": "@colors.panel.fieldRim",                       // colors.panel.fieldRim
"bumperV": [[0, "@gradients.band.bumperV.0"], [0.25, "@gradients.band.bumperV.1"], …],   // a stop is named by the stop
"fill": ["@text.booster.badge.count.fill.0", …]
```
and the colour is the skin's: `skin/colors.json` `"ui": {"colors.panel.fieldRim": "teal.59c", …}` (a palette name, or its
own `"#RRGGBB"` / `"#RRGGBBAA"`). The ui id is the slot's own dotted path, so it is obvious which entry colours which slot.
`build.py` writes the resolved table to `Tuning/ui-colors.json`; `Tuning.load` (App/Support/Tuning.swift,
`TuningFile.resolvingReferences`) replaces every `"@<id>"` of ui.json (and of a `-pc.tune ui.<key>=@<id>` override) with
it once at load, so every reader (`Tokens`, the toast, the FX, the HUD freeze) sees plain `"#RRGGBB"` strings exactly as
before. An unknown id stays unresolved and the read falls back to its compiled default (it never crashes); `build.py --check`
fails on it. Because the ui entries name palette colours (67 colours only ui.json used were added to the palette), a
family recolour moves them with everything else: there is no separate ui.json step.

To **add a colour to ui.json**, write it as a plain `"#RRGGBB"` while you work, then
```sh
python3 tools/skin/build.py --adopt-ui   # moves every raw colour of ui.json into colors.json `ui` (+ palette) and leaves
                                         # "@<ui id>" in its place (formatting kept), then regenerates
```
`build.py --check` fails while any raw `#RRGGBB[AA]` is left in a ui.json string, while a reference names an id the skin
lacks, and while a `ui` entry is referenced by no slot. `design/ui-tokens.json` (the measurement record) keeps its literal
values; the app never reads it.

### Adding UI code

Write the colour as a literal while you work, then run
```sh
python3 tools/skin/codemod.py --dry-run --list   # what it would name the new literal(s)
python3 tools/skin/codemod.py                    # replaces them, adds tokens (+ palette entries), runs build.py
python3 tools/skin/build.py --check-literals     # 0 un-tokened colour literals (CI runs this)
```
The codemod never renames existing tokens or palette entries; a new literal reuses the palette entry of an equal colour.
`--check-literals` fails on: a `0xRRGGBB`, `"#RRGGBB"` or decimal `(UI)Color(red:green:blue:)` in code (comments are
fine) that is not allow-listed, a `Skin.<name>` the JSON lacks, a token no source uses (delete it from the JSON), and a
stale allow-list entry. A hex number that is not a colour goes into `tools/skin/literal_allowlist.json` with its reason.

What the codemod handles: `0xRRGGBB` in any position (`Color(hex:)`, `UIColor(rgb:)`, `[UInt32]` gradients, `(location,
0xRRGGBB)` stops, tuple/struct fields, ternaries, Tokens defaults), `"#RRGGBB"` strings, and decimal
`UIColor(red:green:blue:alpha:)` (rewritten to `UIColor(rgb: Skin.x, alpha:)`: the channels rounded to 8 bit, under
0.5/255 away, the same rendered pixel). Named system colours (`.white`, `.black`, `.clear`, `Color.white.opacity(…)`)
stay: they are neutral, not a design choice a skin changes, and SwiftUI/UIKit resolve them without a lookup.

### Scope and limits

- **Code-drawn colours only.** Raster art (`art/ui/out/*.png`, the UIArt catalogue, the 3-D renders) has its colours
  baked in; recolouring the chrome does not recolour a PNG. Art is reskinned by slot (section 4).
- **Not in the scan:** `App/Board` (ArrowEscape's board: its colours come from `Tuning/board.json`, the module owns them),
  `App/Game`, `App/Audio` and the core package (no UI colours). `App/Puzzles` (the newer modules' boards) IS scanned:
  their colours are `puzzle.*` tokens.
- **Verification:** `codemod.py --verify <git rev>` inlines every token back into the sources and compares them with that
  revision (0 of 61 files differed when the literals were replaced). `build.py --selftest` tests the lexer (comments,
  nested comments, interpolated/raw/multi-line strings), naming, generation, colour maths and a codemod round trip;
  `recolor.py --selftest` the recolour maths; the selftest also covers the ui.json scanner, `--adopt-ui`, the reference
checks and the fonts/names generation. `SkinColorsTests` (app unit tests) checks every compiled constant equals
  colors.json, the String tokens parse, no 0xRRGGBB literal is left in the UI sources, `Tuning.load` leaves no `"@…"`
reference in ui.json and loads the skin's colour, and the fonts / names constants equal skin/fonts.json / names.json.

## 2. Fonts

`skin/fonts.json` names the text faces by the role the text code draws with (`GameTextStyle.Face`):
```json
{"faces": {"black":       {"postScript": "PCDisplay-Black",       "file": "PCDisplay-Black.ttf"},
           "blackItalic": {"postScript": "PCDisplay-BlackItalic", "file": "PCDisplay-BlackItalic.ttf"}}}
```
`black` draws every label (GameText, the social rows, the pages' SwiftUI text through `GameText.pageFont`), `blackItalic`
the event logos. To change the font: put the new `.ttf`/`.otf` files in `App/Resources/Fonts/` (with their licence; delete
the old ones), write their PostScript names and file names here, run `build.py`. It generates `SkinFonts` (in
`App/Shell/Components/SkinData.generated.swift`: `GameText.blackPostScript` / `italicPostScript`, `AppModel.fontNames`
and the boot/diagnostic screens read it) and rewrites the `UIAppFonts` list in `project.yml` and `App/Info.plist`.
`build.py` fails when a role is missing, a file does not exist, or `Fonts/` holds a font file no face declares; the font
tests (`FontCoverageTests`, `ScaffoldTests`) check the bundle against `SkinFonts`. The non-Latin fallback cascade
(`FontCascade`: the system's Black faces for CJK, Arabic …) is not skin data: it follows the text, not the game.
Metrics: the text styles' sizes and tracking are in ui.json (measured for PC Display); a face with other proportions may
need `text.*.size` / `tracking` retuned there (numbers, not Swift).

Not yet from the skin: `App/Board/DigitGlyphs.swift` (the board's counter digits) still spells `"PCDisplay-Black"`; it is
in the puzzle module's folder, which another lane owns, and should read `GameText.blackPostScript` / `SkinFonts.black`.
`art/ui/code/GlossyChrome.swift`'s `OutlinedLabel` (art tooling only) uses a placeholder system font.

## 3. Names, texts and sounds

| What | Where it comes from | Reskin by |
|---|---|---|
| **Brand / display name** | `game.yml identity.brand_name` -> `project.yml PC_BRAND_NAME` -> Info.plist -> `Brand.name` (the one source in code; copy interpolates it) | `tools/game.py generate` (docs/TEMPLATE.md); not duplicated in the skin |
| **Names that are not copy** | `skin/names.json`: `podiumSampleNames` (the Weekly Cup intro podium's three sample players) -> `SkinNames` (the avatar portraits are art: the `avatar.<n>` slots, section 4) | edit the JSON, run `build.py` |
| **Event, character, currency and item names; all copy** | translated copy: the English source text is the key (`"Treasure Climb"`, `"Coins"`, `"Hot Streak"` …) in `App/Resources/Strings/strings.tsv` (13 languages) | `tools/strings/build.py` (per-game strings, ROADMAP); never a literal in the skin, it must be translated |
| **Sounds** | files `App/Resources/Sounds/<SoundID>.wav`; which moment plays which sound and at what gain is already data (`Tuning/audio.json` `cues`, `gain`; `AudioCues.swift` holds only the equal fallbacks) | replace the `.wav` files (same names) and edit `audio.json`; the set of sound ids is the closed `SoundID` enum in `App/Contracts` (adding a sound slot is a contract change) |

## 4. Art, scenes and the logo

### Art slots: `skin/art.json`

Swift never names an art file. It names a **slot**: what the raster is for.
```json
{"slots": {"currency.coin.icon": "iconCoin",        // slot -> the art/MANIFEST.json id of the file that fills it
           "home.backdrop": "homeWorkshop",
           "avatar.3": "avatarSleuth",
           "event.skyJump.badge": "badgeCloudHop", …},
 "rigs":  {"home.character.main": "boss",           // puppet slot -> the manifest's rig entry (art/out/<folder>_rig)
           "home.centrepiece": "homeSignpostLayers", …}}
```
`tools/skin/art.py` (run by `build.py`) resolves each slot through `art/MANIFEST.json` (file, size, group) and generates
`App/Shell/Components/UIArt.swift`: `enum UIArt` has one case per slot, the id camel-cased (`currency.coin.icon` ->
`UIArt.currencyCoinIcon`, raw value `"currency.coin.icon"`), with `asset` (the manifest id), `path` (the bundle file),
`sizePt` and `group`; `enum ArtRig` has one case per rig slot with its `folder`. The code draws `ArtImage(art: .homeBackdrop)`,
`ArtStore.image(.currencyCoinIcon)`, `PuppetCache.rig(ArtRig.homeCharacterMain.folder)`; the compiler checks every slot it
names. The reference skin maps the 200 shipped rasters one to one (the same files the app drew before slots) and 8 rigs.

**Slot names** are `<area>.<thing>[.<role>]`: `currency.*`, `hud.*`, `lives.*`, `booster.<booster id>.icon`, `icon.*`
(settings glyphs, check, info, pointers), `reward.*` (coin piles, the three stage chests), `fx.*`, `tutorial.hand`,
`unlock.<feature id>.icon`, `avatar.<0…8>` (the avatar index table: 0 = the default silhouette), `rank.<1-3>.badge`,
`social.*`, `leaderboard.*`, `profile.stat.*`, `shop.bundle.<tier>` / `shop.coins.<1-6>`, `nav.<tab>.icon`,
`home.backdrop|station|floor|stand|centrepiece`, `loading.backdrop`, `loading.cast.<n>`, `logo.main`,
`event.<event id>.<thing>` (badge, header, backdrop, offer …), and two namespaces owned elsewhere: `logo.part.<id>` (the win
logo's images, named by ui.json `win.logo`) and `puzzle.<sprite id>` (the puzzle module's board sprites; the module draws
them by sprite id from its level data, the slots keep them in the shipped set).

**Optional slots (template phase 5, docs/architecture/PUZZLE-MODULE.md §8c).** Three slot families are looked up by name at
run time and may be absent from art.json; the shell then draws a clean data fallback, never a stand-in raster:
`booster.<booster id>.icon` (a module booster's HUD corner and buy popup; the reference's `booster.freeze.icon` /
`booster.hint.icon` are mapped, a `BoosterSpec.icon` names another slot; fallback: the booster's name on the green face),
`hud.<widget>.icon` (a HUD counter's icon: `hud.moves.icon`, `hud.progress.icon`, `hud.goals.icon`, `hud.score.icon`;
fallback: the pill centred in its slot) and `popup.<offer kind>.icon` (the prop of the generic offer popup:
`popup.stuck.icon`, `popup.outOfMoves.icon`; fallback: the kind's body text). A skin fills one by adding the slot to
art.json like any other; none of them is mapped in the reference skin today (no existing raster fits them).

**Reskin the art:** render the new files into `art/ui/out/` or `art/out/` and register them in `art/MANIFEST.json`
(`art/PIPELINE.md`), point the slots at them in `skin/art.json` (several slots may share one file), run
`python3 tools/skin/build.py`. A NEW slot (a screen that needs a raster no slot names) is a code change: add it to
art.json, then draw `UIArt.<name>`.

`python3 tools/skin/art.py --check` (CI; `build.py --check` runs the JSON part) fails on:
- a slot whose manifest id is unknown, retired or build-only, or whose file is missing from `art/ui/out` / `art/out`; a rig
  slot without its `rig.json`;
- a shipped raster or rig of the manifest that no slot maps (it would ship with no code able to draw it; retire it in the
  manifest or `tools/art_build_only.txt` instead);
- a slot the Swift code names as a STRING that the skin lacks: `UIArt(rawValue: "…")`, `enum UpAwayArt`'s constants, every
  image id of ui.json `win.logo` (as `logo.part.<id>`);
- a Swift source in `App/` or `art/ui/code/` whose string literal names an art file: a manifest file id, a rig folder,
  `@3x`, `.png`, a `UI/…` / `Art/…` path. `tools/skin/art_allowlist.json` lists the three places that must, with the reason
  (the puzzle module's sprite catalogue in `App/Board/`, the rig loader `PuppetRig.swift`, the logo spec's part names in
  `WinLogoSequence.swift`); a stale entry fails too;
- stale `UIArt.swift` / `SkinScenes.generated.swift`.
`tools/uiart_gen.py --check` (the older CI step) checks the same `UIArt.swift`; its `--exclude-list` (what never ships,
`tools/sync_art.sh`) is unchanged. On the Mac, `SkinArtTests` proves the compiled tables equal the JSON entry by entry and
every rig slot loads; `UIArtBundleTests` that every slot's file is in the bundle and decodes.

### Scenes: `skin/scenes.json`

The home and Loading scenes are lists, back to front, on the 393 x 852 reference canvas:
```json
{"rigParts": {"home.character.main": {"arms": ["armL", "armR", "armR_point"]}},
 "home": {"back":  [{"art": "home.backdrop", "fill": true, "at": [0, 0, 393, 852]},
                    {"rig": "home.character.main", "excluding": "arms"},
                    {"art": "home.station", "frame": "home.scene.console", "at": [109, 176, 191, 192]},
                    {"rig": "home.character.main", "only": "arms"}, …,
                    {"centrepiece": "home.centrepiece", "frame": "home.scene.arrowPile", "at": [101.5, 385.96, 190, 128]}],
          "front": [{"rig": "home.character.left"}, {"rig": "home.character.right"}]},
 "loading": {"backdrop": "loading.backdrop", "logo": "logo.main", "cast": [{"art": "loading.cast.1", "at": [-6, 434, 96, 76]}, …]}}
```
- `art`: a slot drawn aspect-fit at `frame` (a ui.json `frames` key, tunable with `-pc.tune` and without a build) whose
  default is `at`; `fill: true` draws it aspect-fill over `at` (the full-bleed backdrop).
- `rig`: a puppet at its rig.json placement; `only` / `excluding` name a `rigParts` set (a character split around another
  layer: the main character's arms in front of his station).
- `centrepiece`: the rig with the idle loop and the refill steps (ui.json `puppet.<folder>.refill`) at `frame`.
- `home.back` is drawn behind the LEVEL plate and Play, `home.front` in front of them (behind the top bar).
- `loading`: the full-bleed backdrop, the logo (placed at ui.json `frames.loading.logo`) and the cast (fixed rects; R4
  LOADING's layout, which `Art/char_loading_layout.json` used to carry).

`art.py` generates `SkinScenes` (`homeBack`, `homeFront`, `loadingBackdrop`, `loadingLogo`, `loadingCast`); `HomeView` and
`LoadingScreen` draw the lists (no scene literal left in them). The **motion** was already data and stays where it is:
ui.json `puppet.<rig folder>` (cycle, phase, keyframe tracks per layer; the centrepiece's `refill` steps and haptic ticks) and
`home.pileRefill`. A rig's placement and layers are the rig's own `rig.json` (the art pipeline's export).

### The logo

- **Boot / Loading logo:** the `logo.main` slot at ui.json `frames.loading.logo` (the Loading scene above).
- **Win logo:** every beat of the celebration is ui.json `win.*` (`panelAt`, `dimAt`, `confettiAt`, the rockets, bursts,
  haptic beats `win.haptics`) and the logo itself is ui.json `win.logo` (parts, layers with their rects, anchors and
  keyframe tracks, the containers and the arrow sign's swap; generated by the logo spec tools). Each image id there is drawn
  from the slot `logo.part.<id>`; the one-piece fallback from `logo.main`. `WinLogoSequence.swift` keeps only equal
  fallbacks for a missing ui.json block. A new game's logo: new part files + `logo.part.<id>` slots + its own `win.logo`
  block. Limit: the part tree's ROLES are still Swift literals of this logo's part ids (`logoSignBlue` carries the letters,
  `logoSignPurple` bends, `logoOut` + the four OUT! glyphs form the echo group, `LogoSpec.arrowOrder` / `outOrder`), so a
  logo with another structure keeps those ids for its parts or needs a code change (section 6).

## 5. A second skin: the data-only proof

`skin/variants/<name>/colors.json` is an alternate palette made by `recolor.py`'s rules, stored as an OVERLAY on
`skin/colors.json` (its whole palette + any own-literal token / ui values the rules move; the rules themselves are kept in
the file). `skin/variants/cobalt/` moves the teal chrome to #3A6FE0 and the pink family to #7B3FE4 (481 of 1,063 palette
colours). It is **not shipped**: nothing reads `skin/variants/` at build or run time.
```sh
python3 tools/skin/variant.py --check      # (CI) each variant: merges, validates (build.py's rules), generates the colour
                                           # outputs with build.py's own generators, and fails unless they differ from the
                                           # active skin's ONLY in colour values (same files, lines, names; > 0 colours)
python3 tools/skin/variant.py --write NAME --map teal=#3A6FE0 --map pink=#7B3FE4   # make one
python3 tools/skin/variant.py --refresh    # re-apply the stored rules to today's colors.json (after the skin grows)
python3 tools/skin/variant.py --apply NAME # try it in the app: writes the merged palette over skin/colors.json
                                           # (then build.py + build; `git checkout apps/<slug>/skin/colors.json` goes back)
```
Tokens the UI gains later follow a variant through their palette names; a palette entry newer than the variant keeps the
reference colour until `--refresh` (reported). Since the Swift sources are identical for every skin and the generated
Swift differs only in constant values, a variant compiles wherever the reference does. The Mac-side proof (the app built and
screenshotted on a variant) is still to do.

## 6. Not skin data yet

| Part | Today | Target |
|---|---|---|
| **Screen layouts** | many frames and sizes of the shell's screens are Swift defaults of ui.json reads, some plain literals | ui.json keys (numbers, not Swift) |
| **Per-game strings** | copy in `App/Resources/Strings/*.tsv` | `Games/<slug>/strings/` |
| **Launch colours** | `App/GameApp.swift` boot diagnostics / Loading stand-in and the `LaunchBackground` asset colour are outside the skin scan | skin tokens |
| **Art ink boxes** | `S2Chrome.swift` `ArtInk`: each HUD / popup raster's measured alpha bbox (fractions of its canvas) as Swift literals, keyed by slot; a new file in such a slot places its visible pixels by the OLD file's box | generated by art.py from the mapped files |
| **Win logo structure** | the part tree's roles (which part carries the letters, which bends, the OUT! group and orders) are Swift literals of Arrow Out's part ids in `WinLogoSequence.swift` | a role map in `win.logo` / the skin |

The proof of phase 3 is a second skin that builds and runs with zero Swift changes: the colour half is proven at the level
of the generated sources by `variant.py --check` (section 5; green on Linux 2026-09-30; it is a CI Linux step, but CI has
not run since the variant was added: docs/ROADMAP.md, Blocked). Still to do: the app built and screenshotted on a variant
(Mac), and an art variant (`skin/art.json` pointing at other files), which needs those files rendered first.
