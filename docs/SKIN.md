# Skin: reskinning a game made from this template

A game = the shared system + a puzzle module + a **skin** + a config (see `docs/ROADMAP.md`). The skin is everything a
player sees that is specific to one game: colours, art, fonts, sounds and names. The goal is a complete reskin **without
changing Swift**. Colours are the first part that works this way; the rest is listed at the end.

## 1. Colours

### How they are stored

| File | What it is | Edit it? |
|---|---|---|
| `apps/mazeout/skin/colors.json` | `palette`: named colours (`"teal.42": "#00706B"`). `tokens`: every colour the UI code draws, by a stable id (`"popups.popupChrome.chromePalette.blue.face.0": "teal.66h"`) pointing at a palette name (or at a `#RRGGBB` of its own) | **yes**: this is the source |
| `apps/mazeout/App/Shell/Components/SkinColors.generated.swift` | `enum Skin { static let <token>: UInt32 = 0xRRGGBB }`: one compile-time constant per token | no, generated |
| `apps/mazeout/Tests/AppTests/SkinColorsTable.generated.swift` | token id to constant table for `SkinColorsTests` | no, generated |
| `apps/mazeout/tools/skin/literal_allowlist.json` | hex numbers in the UI code that are not colours (an RNG seed) | only when you add one |
| `apps/mazeout/App/Resources/Tuning/ui.json` | runtime overrides for ui.json-keyed colours (see "ui.json" below) | through `recolor.py --ui-json` |

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
Arrow Out has 996 palette colours (every distinct value the UI draws, exact: merging near-equal ones would change
pixels) behind 1,664 tokens; teal (322 colours, the D1 chrome), pink (130, Super Hard / events), orange (104),
yellow (96), neutral (84), maroon (75), red (74), brown (53), cream (40) and a few confetti/firework accents.

### Reskin the colours: three ways, from coarse to fine

1. **Move whole families** (the usual first step):
   ```sh
   cd apps/mazeout
   python3 tools/skin/recolor.py --map teal=#3A6FE0 --map pink=#7B3FE4 --ui-json \
       --preview /tmp/recolor.html --dry-run            # look at the before/after sheet first
   python3 tools/skin/recolor.py --map teal=#3A6FE0 --map pink=#7B3FE4 --ui-json
   ```
   Each colour of a family keeps its CIELAB lightness L* (so every ramp: face, rim, outline, gradient stops, highlights
   keeps its structure), its chroma relative to the family's most saturated colour, and its hue offset from it; the
   family's anchor takes the new colour's hue and chroma. Options: `SELECT=FROM>TO` picks the anchor, `--lightness shift`
   moves the whole ramp by the anchor's L* difference instead, `--hue-spread 0.5` compresses the family's hue spread,
   `hue:160-212` / `name:teal.42,teal.44` select by hue window or by name, `--config rules.json` keeps the rules in a
   file. This is the D1 reskin's method (`tools/palette_map.py`, `art/ui/src/d1_skin.py`) in stdlib Python.
2. **Edit palette entries** in `skin/colors.json` by hand (change `"teal.42": "#00706B"`): every token using that entry
   follows.
3. **Override one token**: point it at another palette name or give it its own `"#RRGGBB"`.

Then, always:
```sh
python3 tools/skin/build.py            # validates colors.json, rewrites the two generated Swift files
python3 tools/skin/build.py --check    # (CI) fails if they are stale
tools/gen.sh && tools/build.sh …       # build the app as usual (README §3); nothing else changes
```

### ui.json

`App/Resources/Tuning/ui.json` (from `design/ui-tokens.json`) holds ~650 colour values that **override** the compiled
defaults of the ui.json-keyed reads (`t.color("popup.ribbon.top", Skin.…)`, `t.text(…)`, `t.stops(…)`). A recolour must
move both, or those elements keep the old colour: `recolor.py --ui-json` rewrites the ui.json values with the same rules
(a value equal to a palette colour takes exactly that colour's new value, so default and override stay identical; alpha
suffixes are kept). Moving these values into the skin (so ui.json holds geometry only) is a follow-up.

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
  `recolor.py --selftest` the recolour maths. `SkinColorsTests` (app unit tests) checks every compiled constant equals
  colors.json, the String tokens parse, and no 0xRRGGBB literal is left in the UI sources.

## 2. What else belongs to a skin (next steps)

Colours are done; these still live in Arrow Out's names and files and are the next parts of ROADMAP phase 3:

| Part | Today | Target |
|---|---|---|
| **Art slots** | `UIArt` cases named after Arrow Out things (`treasureToken`, `rankBadgeGold` …), PNGs in `art/ui/out/` | art by **slot** (`logo.main`, `event.race.badge`, `home.character.boss`) in `skin/art/`; a missing slot fails `doctor` and the Release build |
| **Scenes and logo** | home/loading scenes and the win-logo timing in code (`HomeScene`, `PuppetRig`, `WinLogoSequence`) | scene/logo descriptions as data in the skin |
| **Fonts** | `App/Resources/Fonts/` + the faces named in `GameText` | the skin names its fonts; the text styles read them |
| **Sounds and music** | `App/Resources/Sounds`, `Music`, the sound bank | sound slots in the skin |
| **Names and texts** | event names, character names and copy in `App/Resources/Strings/*.tsv` | per-game strings (`Games/<slug>/strings/`), brand via `Brand.name` (already one source) |
| **ui.json colours** | colour values in `Tuning/ui.json` next to geometry | the skin's colours only (see above) |

The proof of phase 3 is a second skin that builds and runs with zero Swift changes.
