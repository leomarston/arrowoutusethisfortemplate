# Skin: reskinning a game made from this template

A game = the shared system + a puzzle module + a **skin** + a config (see `docs/ROADMAP.md`). The skin is everything a
player sees that is specific to one game: colours, art, fonts, sounds and names. The goal is a complete reskin **without
changing Swift**. Colours (the UI code's and ui.json's), fonts and the non-copy names work this way today; sounds and the
brand name already were data elsewhere (section 3); art and scenes are listed at the end.

Everything the skin generates is written by one command and checked by CI:
```sh
cd apps/mazeout
python3 tools/skin/build.py            # validate skin/*.json, rewrite every generated file
python3 tools/skin/build.py --check    # (CI, game.py doctor) stale output, a colour left in ui.json, a dangling reference
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

The UI code (`App/Shell`, `App/FX`, `art/ui/code/GlossyChrome.swift`) uses `Skin.<name>` wherever it used a colour
literal before, e.g. `Color(hex: Skin.popupsPopupChromeCardBevel0)`, `UIColor(rgb: Skin.fxConfettiConfettiSpecColors2)`,
`t.color("card.fill", Skin.popupsSettingsPopupCardFill)`. Each call site converts the constant exactly as it converted
the literal it replaced, so Arrow Out renders pixel for pixel as before (the codemod's `--verify` proved every value; see
below). The constants are plain `static let`s: the compiler checks every use and folds the value; there is no lookup at
run time.

**Reading the names.** A token id is `<area>.<file>.<scope>.<role>[.<n>]`:
- `area`: `components`, `home`, `hud`, `pages`, `popups`, `profile`, `shop`, `social`, `shell` (App/Shell/*.swift),
  `fx`, `art` (GlossyChrome).
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
pixels) behind 1,664 tokens and 657 ui.json colours; teal (346 colours, the D1 chrome), pink (135, Super Hard / events),
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
  baked in; recolouring the chrome does not recolour a PNG. Art is the next skin step (slots, below).
- **Not in the scan:** `App/Board` (the puzzle's colours come from `Tuning/board.json`: the puzzle module owns them),
  `App/Game`, `App/Audio` and the core package (no UI colours).
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
| **Names that are not copy** | `skin/names.json`: `podiumSampleNames` (the Weekly Cup intro podium's three sample players), `avatarPortraits` (portrait index 1…8 -> `Art/char_avatar<Name>@3x.png`) -> `SkinNames` | edit the JSON, run `build.py` |
| **Event, character, currency and item names; all copy** | translated copy: the English source text is the key (`"Treasure Climb"`, `"Coins"`, `"Hot Streak"` …) in `App/Resources/Strings/strings.tsv` (13 languages) | `tools/strings/build.py` (per-game strings, ROADMAP); never a literal in the skin, it must be translated |
| **Sounds** | files `App/Resources/Sounds/<SoundID>.wav`; which moment plays which sound and at what gain is already data (`Tuning/audio.json` `cues`, `gain`; `AudioCues.swift` holds only the equal fallbacks) | replace the `.wav` files (same names) and edit `audio.json`; the set of sound ids is the closed `SoundID` enum in `App/Contracts` (adding a sound slot is a contract change) |

## 4. What else belongs to a skin (next steps)

| Part | Today | Target |
|---|---|---|
| **Art slots** | `UIArt` cases named after Arrow Out things (`treasureToken`, `rankBadgeGold` …), PNGs in `art/ui/out/`; `Brand.logoArtID` | art by **slot** (`logo.main`, `event.race.badge`, `home.character.boss`) in `skin/art/`; a missing slot fails `doctor` and the Release build |
| **Scenes and logo** | home/loading scenes and the win-logo timing in code (`HomeScene`, `PuppetRig`, `WinLogoSequence`) | scene/logo descriptions as data in the skin |
| **Per-game strings** | copy in `App/Resources/Strings/*.tsv` | `Games/<slug>/strings/` |
| **Launch colours** | `App/GameApp.swift` boot diagnostics / Loading stand-in and the `LaunchBackground` asset colour are outside the skin scan | skin tokens |

The proof of phase 3 is a second skin that builds and runs with zero Swift changes.
