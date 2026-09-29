# Maze Out: typeface identification and font choice

**Decision: one family for every UI text role: Nunito (SIL OFL 1.1) at its heaviest master, wght 1000.**
We ship it as a static, renamed instance: `design/fonts/PCDisplay-Black.ttf`.
- family `PC Display`
- PostScript name `PCDisplay-Black`

`PCDisplay-BlackItalic.ttf` is shipped next to it, for slanted event-title lettering (the "Streak Race" style logos).

The Maze Out look comes from the **effects**, not from a second typeface:
- a light face (often a vertical gradient);
- a dark outline with round joins;
- a solid, unblurred drop shadow in the outline colour.

Titles, buttons, HUD digits, labels and body copy all use the same heavy weight. They differ only in size, tracking,
colours and effects (§5, §6).

**Scores.** Nunito wght 1000 ranked first of 38 candidates on glyph shape (glyph IoU 0.863; next best 0.830). At the
fitted size and tracking, its mean line IoU is 0.840 over 33 reference crops. The best iOS system alternative,
SF Pro Rounded Black, reaches 0.770 (§9).

Every number below was measured by rendering, unless it is tagged *(visual)* or *(inference)*. The references are
the phone runner shots (1178×2556 px, owner's iPhone 15, **1 pt = 1178/393 = 2.9975 px**) and the in-game parts of
the App Store screenshots (1320×2868 px = a 440-pt canvas, 1 pt = 3 px). We only looked at the originals. No file,
glyph or image of theirs was extracted or reused; our font is an OFL family.

---

## 1. What the reference typeface is

*(visual)* A heavy, rounded, geometric-humanist sans with fully rounded stroke ends. Its tells:
- `a` is double-storey with a small counter;
- `g` is single-storey;
- `t` has a slanted top cut;
- `e` has a near-horizontal terminal;
- `y` has a straight tail;
- `Q` has a short tail that stays inside or just below the bowl;
- `J` sits on the baseline and has no top bar;
- `1` has a flag and no foot;
- `4` is closed;
- `3` has a **flat top with a sharp top-left corner**;
- `5` has a flat top;
- `6` has a curved stem.

The whole UI uses one weight, and everything is outlined except a few plain labels.

**Identity: not verified.** No OFL face matches every tell. Nunito matches the lowercase, the `1`, the `0`, `6` and
`d`, and the overall colour. It differs in these ways (measured, §4):
- Nunito's `3` has a **round top**;
- Nunito's `J` **descends below the baseline** (glyph IoU 0.47);
- Nunito's `Q` tail is longer;
- Nunito's glyphs are about 4 % wider, per glyph (median bbox width ratio 1.00–1.07 on the phone crops).

*(inference)* The original is most likely a commercial rounded display face (the VAG-Rounded / Mikado kind) rendered
by Unity TextMeshPro. That was not checked: we did not download or inspect any commercial font or the original's
binary. The recommendation does not depend on the name.

## 2. Method (reproducible; scripts in `design/font-compare/tools/`)

Adapted from `apps/arrows/design/font-compare/tools/` (commit 8e77f85). The changes are listed per script in §11.

1. **Crops and ink maps.** `crop_refs.py` makes 33 samples, listed in §3.
   - **plain** samples (one text colour): ink = the projection of each pixel on the *local* background → *local*
     text colour axis. The local colour is the colour of the nearest "pure" pixel of that class, found with a
     distance transform, so gradients do not bias the edges.
   - **outlined** samples (light face inside a dark outline): each pixel is unmixed against the only two
     anti-aliased mixtures that can occur, background↔outline and outline↔face. The result is a *face* map and an
     *outer* map (face + outline + shadow).
   - The HUD timer, "0:45", "16", "1000" and "Hard Level" have a face colour close to the background, so for those
     the face is taken by luminance inside a 2-px band around the face core.
   - Component filters drop pill edges and icons.
   - `contact_crops.png` shows every crop with its maps.
2. **Sizing on a glyph, not on the cap height.**
   - For each crop, one isolated reference glyph is chosen (`H`, `F`, `P`, `4`, `3`, `d`, …) and its height and bottom
     edge are measured with an ink-sum edge estimator (exact for flat edges).
   - The candidate renders that same character alone, is measured with the same estimator, and is then scaled and
     placed on the baseline to match.
   - So round and flat glyphs are compared like with like, and each font's cap/overshoot conventions cancel out.
3. **Rendering.** `ctrender.swift` renders with CoreText, the engine iOS uses: 4× supersampled, box-downsampled.
   Variation axes are set directly; tracking uses `kCTKernAttributeName`, which is the same as SwiftUI `.tracking`.
4. **Scores.** Alignment is searched in ¼-px steps.
   - **line IoU** = Σmin/Σmax over the whole line. It punishes wrong widths and spacing.
   - **width-fit IoU** is the same score after stretching the render to the reference ink width.
   - **glyph IoU** (`glyphscore.py`): every glyph is aligned on its own. This is pure letterform shape. A
     centroid-spacing RMS comes with it.
   - **ink ×ref** (mass ratio) is the weight check; **width ×ref** is the proportion/spacing check.
5. **Candidates (38).**
   - The brief's 27 faces: Lilita One, Titan One, Luckiest Guy, Fredoka (variable), Baloo 2, Baloo Bhai 2, Chewy,
     Carter One, Passion One, Paytone One, Rubik, Nunito, Grandstander, Sniglet, Changa One, Galindo, Coiny,
     Rammetto One, Bubblegum Sans, Gluten, Madimi One, Dela Gothic One, Bowlby One, Bungee, Chango, Knewave and
     Signika.
   - 9 more rounded or heavy OFL faces: M PLUS Rounded 1c, Varela Round, Zen Maru Gothic, Mochiy Pop One, Dosis,
     Poetsen One, Bagel Fat One, Rowdies and Concert One.
   - 2 system faces, as diagnostics only: SF Pro Rounded and Arial Rounded MT Bold.
   - All TTFs were downloaded with curl from `github.com/google/fonts` (contents API → raw files, 2026-09-25).
   - Variable fonts were scored at every 100 wght from 500 up to their maximum (their `wdth` / `slnt` / `GRAD` axes
     pinned to the default).
   - Static faces were scored at every shipped weight ≥ 500; a single-weight face at its only weight.
6. **Stages.**
   - Stage 1 (`compare.py`): all 38 families × weights × 33 crops.
   - Stage 2 (`glyphscore.py`): glyph IoU for the 16 best families.
   - Stage 3 (`fine.py`): Nunito at wght 850/900/950/1000 × tracking −5…+1 pt, in 0.25-pt steps, per crop. The
     same for SF Pro Rounded at 900/1000.
   - Final (`final_check.py`): the **shipped file** at the spec size and tracking.
7. **Sheets (look at them).** In `design/font-compare/`:
   - `tells_all_heaviest.png`: all 38 families next to the reference;
   - `sheet_top_plain.png`: overlays;
   - `glyphs_letters_top4.png`, `glyphs_face.png`, `glyphs_digits.png`: reference glyphs vs candidates;
   - `final_phone.png`, `final_store.png`: reference | PCDisplay-Black | overlay (red = reference only, blue = ours
     only);
   - `effects_rebuild.png`: the §6 effect spec rebuilt next to the reference;
   - `coverage_tr_en.png`: EN and TR text in the shipped files.

## 3. Reference samples (33)

- **Phone runner shots:**
  - 007 pause popup:
    - Sound, Haptic *(plain)*;
    - Paused, ON ×2, Resume, Quit *(outlined)*.
  - 003 level HUD:
    - coins 2240 *(plain)*;
    - Level 32 tab, timer 3:00 *(outlined)*.
  - 002 home:
    - top bar 2240, Full *(plain)*;
    - LEVEL, 32, Play, Home tab *(outlined)*.
  - kickoff/state.png: Loading *(outlined)*.
- **Store screenshots:**
  - iphone-6 (Streak Race panel):
    - Kate, Max, James, x1, x5, x25, x100, 23:55 *(plain)*;
    - "Beat levels without fail to get more rewards!", x10, 16 *(outlined)*.
  - iphone-2: "Hard Level", 0:45 *(outlined)*.
  - iphone-7: 2356, 23:46 *(plain)*; 1000 *(outlined)*.
- The store's marketing captions ("TAP AWAY ARROWS!" etc.) are not game renders and were **not** used.
- The "Streak Race" logo is 3D artwork and was not scored; see §8.
- The boxes, colours and ink bboxes are in `font-compare/crops/measure.json`.

## 4. Ranking

Full data:
- `results/stage1_*.json` (every family × weight × crop);
- `results/ranking_stage1_{iou,wfit}.tsv`;
- `results/gscore_*.json` (per glyph).

In the table:
- "line IoU" is at each family's best weight with the font's own spacing (no tracking), so it is low for every
  family. The reference sets most labels tighter than any font's default (§5).
- The shape columns (width-fit IoU, glyph IoU) are independent of spacing.
- Rows are sorted by glyph IoU, which was computed for the top 16. The other rows are sorted by width-fit IoU.

| # | family | licence | wght (best line IoU) | line IoU | ink ×ref | width ×ref | best width-fit IoU (wght) | glyph IoU | spacing RMS |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Nunito** | OFL | 1000 | 0.678 | 0.97 | 1.056 | 0.819 (1000) | **0.863** | 3.15 px |
| 2 | M PLUS Rounded 1c | OFL | 900 | 0.592 | 0.91 | 1.066 | 0.751 (900) | 0.830 | 4.94 px |
| 3 | Passion One | OFL | 700 | 0.722 | 1.10 | 1.004 | 0.794 (700) | 0.827 | 2.26 px |
| 4 | Lilita One | OFL | 400 | 0.687 | 0.90 | 0.947 | 0.797 (400) | 0.815 | 3.15 px |
| 5 | Fredoka | OFL | 700 | 0.689 | 0.95 | 0.981 | 0.770 (700) | 0.815 | 2.75 px |
| 6 | Paytone One | OFL | 400 | 0.642 | 1.01 | 1.075 | 0.775 (400) | 0.808 | 5.08 px |
| 7 | Coiny | OFL | 400 | 0.524 | 1.05 | 1.119 | 0.779 (400) | 0.796 | 6.91 px |
| 8 | Rowdies | OFL | 700 | 0.573 | 1.08 | 1.115 | 0.789 (700) | 0.794 | 5.87 px |
| 9 | SF Pro Rounded *(iOS system)* | Apple | 900 | 0.619 | 0.91 | 1.051 | 0.775 (1000) | 0.791 | 4.52 px |
| 10 | Bagel Fat One | OFL | 400 | 0.638 | 0.94 | 0.998 | 0.737 (400) | 0.782 | 3.96 px |
| 11 | Signika | OFL | 700 | 0.640 | 0.82 | 0.990 | 0.762 (700) | 0.779 | 3.41 px |
| 12 | Changa One | OFL | 400 | 0.550 | 1.20 | 1.137 | 0.787 (400) | 0.769 | 7.51 px |
| 13 | Grandstander | OFL | 900 | 0.644 | 1.02 | 1.046 | 0.737 (900) | 0.765 | 4.47 px |
| 14 | Poetsen One | OFL | 400 | 0.652 | 0.87 | 0.987 | 0.725 (400) | 0.756 | 2.42 px |
| 15 | Rubik | OFL | 600 | 0.534 | 0.84 | 1.072 | 0.811 (900) | 0.751 | 8.90 px |
| 16 | Carter One | OFL | 400 | 0.621 | 0.84 | 0.989 | 0.692 (400) | 0.708 | 3.24 px |
| 17 | Chango | OFL | 400 | 0.385 | 1.46 | 1.449 | 0.794 (400) | – | – |
| 18 | Rammetto One | OFL | 400 | 0.468 | 1.30 | 1.260 | 0.766 (400) | – | – |
| 19 | Titan One | OFL | 400 | 0.568 | 1.24 | 1.114 | 0.761 (400) | – | – |
| 20 | Bowlby One | OFL | 400 | 0.495 | 1.26 | 1.207 | 0.759 (400) | – | – |
| 21–22 | Baloo 2 / Baloo Bhai 2 (same Latin) | OFL | 800 | 0.569 | 0.97 | 1.079 | 0.754 (800) | – | – |
| 23 | Dela Gothic One | OFL | 400 | 0.429 | 1.28 | 1.333 | 0.742 (400) | – | – |
| 24 | Sniglet | OFL | 800 | 0.579 | 1.17 | 1.129 | 0.727 (800) | – | – |
| 25 | Gluten | OFL | 600 | 0.459 | 0.99 | 1.187 | 0.717 (800) | – | – |
| 26 | Dosis | OFL | 800 | 0.489 | 0.72 | 0.864 | 0.708 (800) | – | – |
| 27 | Concert One | OFL | 400 | 0.550 | 0.74 | 0.906 | 0.687 (400) | – | – |
| 28 | Chewy | Apache-2.0 | 400 | 0.444 | 0.71 | 0.816 | 0.683 (400) | – | – |
| 29 | Madimi One | OFL | 400 | 0.518 | 0.70 | 0.905 | 0.678 (400) | – | – |
| 30 | Luckiest Guy | Apache-2.0 | 400 | 0.589 | 1.11 | 1.026 | 0.666 (400) | – | – |
| 31 | Zen Maru Gothic | OFL | 900 | 0.518 | 0.65 | 0.907 | 0.653 (900) | – | – |
| 32 | Bungee | OFL | 400 | 0.475 | 1.31 | 1.208 | 0.651 (400) | – | – |
| 33 | Galindo | OFL | 400 | 0.504 | 0.85 | 1.085 | 0.640 (400) | – | – |
| 34 | Mochiy Pop One | OFL | 400 | 0.534 | 0.75 | 1.035 | 0.631 (400) | – | – |
| 35 | Arial Rounded MT Bold *(system)* | Apple/Monotype | 700 | 0.568 | 0.68 | 1.003 | 0.617 (700) | – | – |
| 36 | Bubblegum Sans | OFL | 400 | 0.456 | 0.62 | 0.871 | 0.613 (400) | – | – |
| 37 | Knewave | OFL | 400 | 0.444 | 0.73 | 0.831 | 0.595 (400) | – | – |
| 38 | Varela Round | OFL | 400 | 0.418 | 0.54 | 1.037 | 0.485 (400) | – | – |

**Why Nunito and not the families with a higher raw line IoU.**
- **Passion One** (0.722) and **Lilita One** (0.687) are condensed faces. Their default spacing is closer to the
  reference's tight tracking, which inflates their raw line IoU.
- On shape alone, Nunito wins: width-fit 0.819 vs 0.794 and 0.797, glyph IoU 0.863 vs 0.827 and 0.815.
- Once each face gets its own best tracking, Nunito's line IoU rises to 0.840 (§5).
- *(visual)* Passion One is condensed, with squarer bowls and counters than the reference. See `glyphs_digits.png`,
  `glyphs_face.png` and `sheet_top_plain.png`.

**Glyph IoU per character** (mean over the crops where the character occurs as a separate glyph; n = occurrences):

| glyph | n | Nunito | M PLUS Rounded 1c | Passion One | Lilita One | Fredoka | SF Pro Rounded |
|---|---|---|---|---|---|---|---|
| `3` | 6 | 0.81 | **0.87** | 0.83 | 0.82 | 0.72 | 0.67 |
| `1` | 4 | **0.91** | 0.68 | 0.69 | 0.66 | 0.66 | 0.66 |
| `4` | 4 | 0.76 | 0.82 | 0.85 | **0.87** | 0.68 | 0.79 |
| `2` | 10 | **0.85** | 0.82 | 0.82 | 0.81 | 0.78 | 0.81 |
| `5` | 6 | 0.85 | 0.85 | **0.89** | 0.81 | 0.86 | 0.75 |
| `6` | 3 | 0.90 | 0.82 | **0.91** | 0.86 | 0.80 | 0.78 |
| `0` | 10 | **0.93** | 0.81 | 0.90 | 0.90 | 0.91 | 0.80 |
| `a` | 6 | **0.86** | **0.86** | 0.76 | 0.77 | 0.71 | 0.77 |
| `e` | 8 | 0.87 | 0.83 | 0.81 | 0.76 | **0.89** | 0.80 |
| `t` | 3 | **0.88** | 0.82 | 0.80 | 0.75 | 0.86 | 0.85 |
| `g` | 1 | 0.88 | **0.89** | 0.68 | 0.75 | 0.87 | 0.82 |
| `d` | 3 | **0.93** | 0.86 | 0.82 | 0.72 | 0.81 | 0.89 |
| `Q` | 1 | **0.81** | 0.68 | 0.74 | 0.75 | 0.73 | 0.79 |
| `J` | 1 | 0.47 ✗ | 0.71 | 0.44 | 0.74 | 0.74 | **0.77** |
| `P` | 1 | 0.78 | 0.86 | **0.88** | **0.88** | 0.85 | 0.82 |
| `R` | 1 | 0.80 | 0.89 | **0.91** | 0.89 | 0.88 | 0.81 |
| `L` | 4 | 0.90 | **0.92** | 0.84 | 0.87 | 0.86 | 0.91 |
| `x` | 5 | 0.87 | **0.89** | 0.78 | **0.89** | 0.78 | 0.80 |

**Known deviations of Nunito.**
- **`3`**: round top instead of flat. It is still 0.81, but visible in "32", "3:00" and "23:55".
- **`J`**: descends below the baseline. It only matters in "James"-type names.
- **`P`/`R`**: slightly wider bowls.
- Nunito has **no alternate** for `3` or `J`: its `ss01` only swaps `a` and `1`, `ss02` only swaps `l`.
- Nunito's licence declares no Reserved Font Name, so a derivative with a redrawn flat-top `3` would be allowed if
  it ever matters.

## 5. Weight, size and tracking per UI element

**Weight.** Mean best-tracking line IoU and ink ratio by Nunito wght, over all crops:

| wght | 850 | 900 (Nunito's own "Black") | 950 | **1000** |
|---|---|---|---|---|
| plain crops (15) | 0.758 / ink 0.82 | 0.792 / 0.88 | 0.820 / 0.93 | **0.835 / 0.99** |
| outlined faces (18) | 0.742 / 0.81 | 0.787 / 0.86 | 0.808 / 0.92 | **0.838 / 0.98** |

wght 1000 is best on 31 of the 33 crops. The Level tab and Loading prefer 950, by 0.002 and 0.006. Play preferred
950 only while the tracking scan stopped at −2.5 pt; at −3.25 pt, wght 1000 scores 0.831 against 950's 0.791. So
**one weight, wght 1000, is used everywhere**.

The outlined faces are **not** thinner than the plain text. So the outline sits *outside* the glyph: draw the outline
behind the full-weight glyph. Do not erode the face.

**Size and tracking.** Each value is the CoreText point size of PCDisplay-Black at which the crop's sizing glyph
matches, plus the best tracking. All scores are re-measured with the shipped file (`results/final_check.json`,
`final_*.png`; mean line IoU **0.840**).

Positions are the ink positions in the reference, in pt:
- the baseline y from the top of the screen;
- the ink centre x.

### Phone (393 × 852 pt; the owner's device)

| UI element | text | size pt | tracking pt (em) | line IoU | baseline y | centre x | fill |
|---|---|---|---|---|---|---|---|
| pause popup title | Paused | **49.2** | −1.00 (−0.020) | 0.720 | 247.5 | 197.0 | outlined, §6 |
| pause popup row labels | Sound / Haptic | **25.5** / 25.2 | 0 / −0.25 (−0.01) | 0.875 / 0.860 | 354.5 / 427.5 | left edge 114.4 / 113.8 | #622100 plain |
| toggle label | ON | **21.0** | −0.75 (−0.036) | 0.885 | 353.2 / 426.4 | 236.2 | outlined |
| popup button, green | Resume | **27.2** | −1.00 (−0.037) | 0.863 | 539.3 | 123.6 | outlined |
| popup button, red | Quit | **30.5** | −0.50 (−0.016) | 0.843 | 540.7 | 269.1 | outlined |
| HUD level tab | Level 32 | **17.9** | −0.50 (−0.028) | 0.754 | 70.9 | 196.8 | outlined |
| HUD timer | 3:00 | **23.3** | +0.25 (+0.011) | 0.873 | 104.0 | 152.3 | outlined |
| HUD coins | 2240 | **18.5** | +0.25 (+0.014) | 0.828 | 48.3 | 74.7 | #3861AC plain |
| home top bar value | 2240 / Full | **18.8** / 19.1 | 0 / −0.75 (−0.039) | 0.828 / 0.856 | 76.3 / 76.9 | 165.6 / 285.4 | #093896 plain |
| home "LEVEL" caption | LEVEL | **14.1** | −1.50 (−0.106) | 0.844 | 531.9 | 196.0 | outlined |
| home level number | 32 | **30.6** | −1.50 (−0.049) | 0.819 | 563.3 | 196.5 | outlined |
| home Play button | Play | **48.8** | −3.25 (−0.067) | 0.831 | 685.9 | 197.0 | outlined |
| bottom tab label | Home | **15.1** | −0.25 (−0.017) | 0.854 | 832.6 | 196.8 | outlined |
| loading screen | Loading | **26.8** | −0.50 (−0.019) | 0.889 | 792.7 | 187.2 | outlined |

- *(inference)* The two popup buttons differ in size (Resume 27.2 pt, Quit 30.5 pt). This looks like TextMeshPro
  auto-size. Use one button style with max 30.5 pt that shrinks to fit, since "Resume" measured 27.2.
- The HUD coins colour #3861AC is paler than the home bar's #093896. *(inference)* It is probably the same colour
  under partial alpha.

### Store screenshots (440-pt canvas; ×0.893 converts to the 393-pt phone *(inference)*)

The ×0.893 factor assumes the UI scales with screen width. The **timer checks it**: "0:45" is 25.9 × 0.893 = 23.2 pt,
and the phone's "3:00" is 23.3 pt.

| UI element | text | size pt @440 (→ @393) | tracking pt (em) | line IoU | fill |
|---|---|---|---|---|---|
| Streak Race subtitle | Beat levels without fail to get more rewards! | 19.7 (17.6) | −1.25 (−0.063) | 0.776 | outlined |
| Streak Race multipliers | x1 / x5 / x25 / x100 | 33.2–33.6 (29.7–30.0) | −2.0…−4.0 (−0.06…−0.12) | 0.83–0.90 | #622100 plain |
| selected multiplier | x10 | 35.0 (31.3) | −2.75 (−0.079) | 0.849 | outlined |
| leaderboard names | Kate / Max / James | 27.2–27.6 (24.3–24.7) | −1.0…−2.0 (−0.04…−0.07) | 0.847 / 0.842 / 0.725 | #622100 (Max #1A336F) |
| event timer chip | 23:55 | 18.5 (16.5) | −1.50 (−0.081) | 0.826 | #622100 plain |
| leaderboard count | 16 | 25.2 (22.5) | −0.25 (−0.010) | 0.915 | outlined |
| hard-level tab | Hard Level | 16.1 (14.4) | −0.75 (−0.047) | 0.817 | outlined |
| HUD timer | 0:45 | 25.9 (23.2) | −0.50 (−0.019) | 0.835 | outlined |
| home level number | 1000 | 29.9 (26.7) | 0 | 0.918 | outlined |
| home top bar | 2356 / 23:46 | 24.1 / 23.4 (21.6 / 20.9) | −1.25 / −0.25 | 0.849 / 0.802 | #0A3896 plain |

**Tracking rule of thumb.** Short labels: −0.01 to −0.04 em. Big buttons, captions and multiplier chips are tighter:
−0.06 to −0.11 em.

The per-label tracking values above come from fitting. The reference may equally use tighter per-pair kerning, which
is why "x1" fits at −0.12 em. Where a label is not in these tables, use −0.03 em.

**Unresolved.** The store home top bar ("2356", 21.6 pt @393) is bigger than the phone's "2240" (18.8 pt). The
phone is the current build and wins (source precedence).

## 6. Text effects (measured)

**Layer model.** Every outlined label is drawn from four layers, back to front:
1. **Drop shadow**: the outline shape, same colour, moved **straight down** by `drop`. Blur 0: its lower edge
   anti-aliases in about 1 px, per `tools/profile.py`.
2. **Outline**: the glyph dilated by `w`. Euclidean, so joins are round; this is a stroke of width 2·w behind the
   fill.
3. **Band**: only on the "Paused" title. The glyph, in the band colour, moved down 1.5 pt behind the face. It reads
   as a thin peach step under the white face.
4. **Face**: the glyph with a vertical linear gradient from the top of the text line to its bottom.

`effects_rebuild.png` rebuilds 11 labels from these numbers next to the reference crops. They match by eye.

How the widths were measured:
- `w` is the median sub-pixel distance from the face edge to the outer edge, over the top, left and right sides
  (`tools/effects.py`);
- `drop` = the bottom distance − `w`.

Both are given in pt and as a fraction of the font size (em). Use the em value when a label is resized.

| element (crop) | text | size pt | face fill (top → bottom) | outline colour | outline pt (em) | drop pt (em) | note |
|---|---|---|---|---|---|---|---|
| paused | Paused | 49.2 | #FFFFFF (flat) | #7B1D01 | 1.87 (0.038) | 3.15 (0.064) | band #FFD699, 4.5 px = 1.50 pt (0.030 em) down |
| play | Play | 48.8 | #F1FFF2 (flat) | #066A01 | 2.20 (0.045) | 2.20 (0.045) | |
| resume | Resume | 27.2 | #FFFCED → #FEF9E8 → #FDF4DD | #066A01 | 1.42 (0.052) | 1.06 (0.039) | |
| quit | Quit | 30.5 | #FFFCED → #FEF8E6 → #FDF4DC | #650000 | 1.47 (0.048) | 1.40 (0.046) | |
| on_sound | ON | 21.1 | #FFFCED → #FEF7E4 → #FDF3DC | #066A01 | 1.00 (0.047) | 1.01 (0.048) | |
| level_tab | Level 32 | 17.9 | #FFF9EF → #FFF4E0 → #FFEDCB | #002985 | 0.65 (0.036) | 0.73 (0.041) | |
| timer | 3:00 | 23.3 | #F7F7F9 → #EDEDF2 → #E2E3EA | #081E5E | 0.67 (0.029) | 1.13 (0.049) | |
| LEVEL | LEVEL | 14.1 | #FFFFFF | #093198 | 0.82 (0.058) | 0.76 (0.054) | |
| num32 | 32 | 30.6 | #FFFFFF | #066A01 | 2.14 (0.070) | 0.50 (0.016) | low confidence: the outline's top edge merges with the pill's green border |
| home | Home | 15.1 | #FFFFFF | #16388C | 0.98 (0.065) | 0.58 (0.039) | |
| loading | Loading | 26.8 | #CCCCCC (flat grey) | #681E1A | 0.88 (0.033) | 0.39 (0.015) | |
| s_beat | Beat levels … | 19.7 @440 | #FFFDFA → #FFF7E7 → #FFEFD0 | #022880 | 1.03 (0.052) | 1.71 (0.087) | |
| s_hard | Hard Level | 16.1 @440 | #FFF3F3 | #69000C | 1.00 (0.062) | 1.33 (0.083) | |
| s_045 | 0:45 | 25.9 @440 | #E9FFFD | #072884 | 0.99 (0.038) | 1.34 (0.052) | |
| s_16 | 16 | 25.2 @440 | #FDE8D8 → #FCE6D7 | #622100 | 1.20 (0.047) | 0.80 (0.032) | |
| s_1000 | 1000 | 29.9 @440 | #F1FFF1 | #076A00 | 1.78 (0.059) | 0.73 (0.025) | |

**Plain (no outline) texts:**
- dark brown #622100 on cream #F8E7D2: the popup rows and the Streak Race chips;
- navy #093896 on #DEEEFF: the home top bar;
- #3861AC: the HUD coins;
- #1A336F for "Max" on the lavender row.

**Pattern (use for labels not measured).**
- Outline ≈ **0.05 em**. Big titles are thinner (0.038–0.045 em); small captions are thicker (0.058–0.065 em).
- Drop ≈ **0.04–0.05 em**. "Paused" is 0.064; the Streak Race panel 0.083–0.087.
- The outline colour is the dark shade of the surface colour:
  - green buttons → #066A01;
  - red → #650000;
  - blue → #002985–#16388C;
  - yellow/orange → #7B1D01.
- Faces are white, or cream with a warm 3–4 % gradient.

## 7. Deliverables

`design/fonts/`:

| file | what | sha256 |
|---|---|---|
| `PCDisplay-Black.ttf` | Nunito v3.602, static instance at **wght 1000**, renamed. 132 348 bytes, 1103 glyphs, 938 code points. | `df9d6146529b67ea0743b5ebb573c9f34b6a3a525781276cdd238f4a0939686c` |
| `PCDisplay-BlackItalic.ttf` | Nunito Italic v3.602 at wght 1000, renamed (for slanted event-title lettering, §8). 135 196 bytes. | `a3ced32cb4385adef737357b3eabebeb66cde235ce0dc7dbb717ad89a2bbaf33` |
| `OFL.txt` | SIL OFL 1.1, "Copyright 2014 The Nunito Project Authors (https://github.com/googlefonts/nunito)", unchanged | `580df76c95a1ec5ab878ceb25bb3d85c6a076804e9c970c8c6972aea775fdf65` |

The sources are google/fonts `ofl/nunito/Nunito[wght].ttf` and `Nunito-Italic[wght].ttf`, with sha256 `bb55a5ca…5207`
and `b520cc87…29c8`. The build script checks both hashes.

**Build.** `python3 design/font-compare/tools/make_font.py <google-fonts ofl/nunito dir> design/fonts`. It uses system
python3 with fontTools 4.65 and is byte-reproducible (the head timestamp is kept).

Changes made to the source:
- instanced at wght 1000;
- STAT dropped;
- names set to family `PC Display`, styles `Black` / `Black Italic`, PostScript `PCDisplay-Black` /
  `PCDisplay-BlackItalic`;
- copyright (name ID 0) and licence (IDs 13/14) kept; ID 10 records the source;
- the **`fi` ligature removed from `liga`** (`fl` kept). In Turkish a ligated fi would lose the dot of the i, and
  CoreText applies the TRK language system only when the text carries a language tag.

**Licence.** OFL.txt declares **no Reserved Font Name**, so keeping "Nunito" would have been allowed. We renamed anyway:
- the static wght-1000 instance must not pose as the real "Nunito Black" (which is wght 900);
- it keeps asset names neutral.

The OFL allows bundling in an app. Ship `OFL.txt` with the app, for example in the acknowledgements.

**Checks run.**
- **Coverage (fontTools):** every character is present in both files:
  - `abcçdefgğhıijklmnoöpqrsştuüvwxyz ABCÇDEFGĞHIİJKLMNOÖPQRSŞTUÜVWXYZ 0-9`;
  - `! ? . , : ; ' ’ " “ ” % + - − × / ( ) & @ # … • $ € ₺`.
  - Turkish İ ı Ğ ğ Ş ş Ç ç Ö ö Ü ü are present in both.
  - Nunito also has `i.loclTRK` under the TRK language system.
- **Pixel identity:** with CoreText, both shipped files are **pixel-identical** (max difference 0/255) to the source
  variable fonts at wght 1000, over six EN/TR test lines (`coverage_tr_en.png`). The reference lines break "fi" with
  a ZWNJ to account for the removed ligature.
- **Name resolution:** CoreText on macOS 15 (`tools/resolve.swift`), after `CTFontManagerRegisterFontsForURL`:

  | request | resolves to |
  |---|---|
  | `PCDisplay-Black` | itself ✓ |
  | `PCDisplay-BlackItalic` | itself ✓ |
  | family name `PC Display` | the registered file |
  | `PCDisplay`, `PCDisplay-Regular` | **Helvetica fallback** (do not use them) |

  This was **not** re-checked inside the iOS Simulator: this role had no simulator. The build agent should run the
  same check there once.

**SwiftUI usage.** Register both files with `UIAppFonts` in Info.plist.

```swift
enum PCType {
    static func display(_ size: CGFloat) -> Font { .custom("PCDisplay-Black", fixedSize: size) }       // every UI role
    static func displayItalic(_ size: CGFloat) -> Font { .custom("PCDisplay-BlackItalic", fixedSize: size) }
    // tracking from §5, e.g. Text("Play").font(PCType.display(48.8)).tracking(-3.25)
}
```

**Drawing the outline and shadow.**
- A SwiftUI `.shadow` blurs, and stacking offset copies is not a Euclidean outline. Use a glyph path instead
  (`CTFontCreatePathForGlyph` / `CTLineGetGlyphRuns`) in a `CAShapeLayer`, or a `Canvas`.
- Draw, back to front:
  1. the path stroked at `2·w` with `lineJoin = .round`, filled too, in the outline colour, offset (0, `drop`);
  2. the same stroke+fill without the offset;
  3. for "Paused" only, the fill in the band colour, offset by the band;
  4. the fill with the vertical gradient.
- Draw text as a layer, never baked into artwork, so EN/TR strings swap cleanly.

## 8. Event names and the "Streak Race" logo

The "Streak Race" title in the store screenshot is **lettering artwork**:
- 3D bevel;
- yellow "Streak" and white "Race";
- italic;
- a blue outline;
- chequered flags.

It is not live text, so it was not scored. *(visual)* Its letterforms are consistent with the same family slanted
(`streak_race_logo_vs_italic.png`: Nunito Italic wght 1000 vs the logo).

For our own event titles, lettered in the same style (and never copied from theirs), use `PCDisplay-BlackItalic` as
the base under the §6 layer model. "Claw Challenge" appears in no reference shot yet.

## 9. iOS system fallback: SF Pro Rounded Black

SF Pro Rounded Black is `Font.system(size:weight:.black,design:.rounded)`; it needs no bundling. Fitted the same
way (`results/fine_sfrounded.json`), it reaches a mean line IoU of **0.770** at wght 1000 (0.757 at 900) against
Nunito's 0.840. Its weaknesses:
- round-top `3` (glyph IoU 0.67);
- a weaker `1` (0.66);
- wider letters.

Use it only if bundling is impossible. Arial Rounded MT Bold is too light (ink ×0.68).

## 10. Open points / uncertainty

- **Identity.** Unverified (§1). The original is probably a commercial rounded face under TextMeshPro. No commercial
  font or original binary was checked.
- **Store scaling.** The store shots are marketing composites. Their text sizes convert to the phone with ×0.893
  *(inference)*; the timer cross-checks within 0.4 %, but the home top bar does not (§5).
- **Crop quality.** Some faces were extracted by luminance because their face colour is close to the background:
  timer, 0:45, 16, 1000 and Hard Level. The store faces "16", "1000" and "Hard Level" have few anti-aliased edge
  pixels, which suggests the composites were resampled, so their edges are ±0.5 px. `num32` and `s_x10` outer maps
  touch pill borders, so their outline widths carry low confidence.
- **Not covered by a reference yet.** When more shots arrive in `research/shots/`, add them to `crop_refs.py` and
  `compare.py SIZING`, then re-run `fine.py` for Nunito:
  - win and fail popups;
  - the shop, settings and settings rows;
  - the booster count badges ("3" on red);
  - the heart-count "5" on the home bar;
  - event badges ("9h 42m": that crop was too small and noisy and was dropped).
- **Rendering engine.** Scores come from macOS CoreText renders. iOS uses the same engine, but the Simulator was not
  used here.

## 11. Reproduce

The work directory is set by `FONTCOMPARE_WORK`. It defaults to this session's scratchpad `…/scratchpad/fc/` and
holds the compiled `ctrender`, `renders/` and the downloaded TTFs in `gf/ofl|apache/<family>/`.

1. `swiftc -O tools/ctrender.swift -o $FONTCOMPARE_WORK/ctrender`
2. Download the families into `$FONTCOMPARE_WORK/gf/<licence>/<dir>/`: run `python3 tools/dl_fonts.py ofl/nunito …`
   inside `gf/`. `candidates.py` lists every path.
3. `python3 tools/crop_refs.py` → `crops/`.
4. `python3 tools/compare.py results/stage1_a.json --step 100 --minw 500 --part 0/2`, and `--part 1/2` for the
   second half.
   - At most two processes. Each renders into its own `renders/p<pid>/`; a shared directory corrupted the first run.
5. `python3 tools/rank.py iou_wfit OUT.tsv results/stage1_*.json`.
6. `python3 tools/glyphscore.py OUT.json "Nunito:1000:1000,…"`.
7. `python3 tools/fine.py OUT.json Nunito 1000 -2.5:1:0.25`.
8. `python3 tools/final_check.py final_phone.png <crops>`.
9. `python3 tools/effects.py` and `python3 tools/effects_render.py effects_rebuild.png`.
10. `tools/make_font.py` (§7).

What each script is:

| script | what | copied from `apps/arrows/design/font-compare/tools/` (8e77f85) |
|---|---|---|
| `ctrender.swift` | CoreText renderer | yes, plus optional `track` |
| `candidates.py` | registry | rewritten |
| `crop_refs.py` | crops and ink | rewritten for outlined text |
| `compare.py` | stage-1 scoring | rewritten: glyph sizing, per-process render dirs, parts |
| `glyphscore.py` | glyph IoU | adapted |
| `rank.py` | ranking | adapted to 2 groups |
| `sheet.py` | overlay sheets | adapted |
| `glyphs.py` | tells sheets | adapted |
| `final_check.py` | spec check | adapted |
| `fine.py` | weight × tracking fit | new |
| `effects.py` | effect measurement | new |
| `effects_render.py` | effect rebuild | new |
| `profile.py` | colour run profiles | new |
| `tells.py` | quick all-family sheet | new |
| `contact.py` | contact sheet | new |
| `dl_fonts.py` | google/fonts downloader | new |
| `resolve.swift` | CoreText name check | new |
| `make_font.py` | font build | new |

Not copied: the arrows `measure_metrics.py`, `stems.py` and `stage2.py`. Sizing by glyph and the explicit weight scan
replace them.

---

## 12. PUBLISH (R6 LOGO, 2026-09-28): the logo / title display face — Paytone One — NOT USED (ruling 44)

> **NOT USED (SPEC.md ruling 44, owner 2026-09-28 06:17; LOGOGREEN 2026-09-28).** The owner kept the win logo's CURRENT art
> and animation with **no new display font**, which supersedes ruling 38's logo-restyle line. Paytone One ships in nothing:
> the logo is lettered from Nunito (`PCDisplay-Black`, `art/ui/src/svg/pcdisplay_glyphs.json`) as in §1–§4. LOGOGREEN restored
> the approved `glyph_outlines.py` (no `--title` mode) and removed `art/ui/src/svg/title_glyphs.json`; R6's versions are archived
> in `build/p/LOGOGREEN/r6_after/`. `design/fonts/PaytoneOne-Regular.ttf` + `OFL-PaytoneOne.txt` stay here as a design record
> only: they are not bundled (not in App/Resources/Fonts, not in UIAppFonts), and no title uses them. The text below is R6's
> record of the choice, kept for history.

Rulings 37 (b) and 38 require a **different OFL display face for the logo and titles**, so the logo no longer uses the
Nunito match (§1–§4). Nunito (`PCDisplay-Black`) stays for body text and digits.

**Choice: Paytone One** (Vernon Adams / The Paytone Project Authors).

| item | value |
|---|---|
| file | `design/fonts/PaytoneOne-Regular.ttf` (unmodified; SHA-256 `1c07073b0b578199b54c7866d55e2b631d285e8aa4bb4fbc08809d980cd49b14`) |
| source | google/fonts `ofl/paytoneone` (upstream github.com/googlefonts/paytoneFont), version 1.002, fetched 2026-09-28 |
| licence | SIL Open Font License 1.1, `design/fonts/OFL-PaytoneOne.txt` (SHA-256 `12404fcefccc3cb964cb2406510ba679b30f7d7ae689db08df5b455ae24b3feb`) |
| reserved font names | "Paytone" and "Paytone One": the file may be used and bundled as is; a MODIFIED font (subset, rename, instance) may not carry these names |
| metrics | UPM 1000, cap height 688, 593 mapped characters |
| coverage | Latin + Latin Extended + Vietnamese: every letter of our 10 Latin-script locales (en de fr es it pt-BR tr pl sk sl, incl. ğ ı İ ş ą ć ę ł ń ś ź ż č ď ĺ ľ ň ŕ š ť ž) is present. ja / ko / zh-Hans titles need the CJK fallback cascade (PLAN-P B3), as with Nunito |

**Why this face.** It is chunky and slightly condensed, with soft-square terminals, so it reads as sign-painted or carved
lettering. That suits D1's "Burrow Works" signpost. It is also clearly different from the reference game's rounded
bubble face, from our own Nunito, and from Match Factory's display faces (Titan One, Baloo 2 ExtraBold), which keeps
the two apps apart.

Candidates rendered side by side on 2026-09-28 (`ARROW OUT!` + a Latin-Extended title line):

| candidate | result |
|---|---|
| Lilita One | chunkier, but its Google Fonts build lacks ğ ş İ ą ć ę ń ś ź ż č ď ĺ ľ ň ŕ ť (fails tr / pl / sk / sl titles) |
| Titan One, Baloo 2 | Match Factory's faces |
| Sigmar One, Rammetto One | full coverage, but wide and quirky |
| Coiny | too close to Nunito's roundness |
| Galindo | irregular |
| Bowlby One, Carter One, Chango, Passion One, Sniglet | Latin-Extended gaps |

**How it is used.**
- **Logo:** the win logo "ARROW OUT!" (`logoArrowOut` and its 40 animation parts) is lettered from this face's outlines.
  `art/ui/src/svg/glyph_outlines.py --title` writes `art/ui/src/svg/title_glyphs.json`; `gen_icons._logo_layers` inflates,
  outlines and extrudes the outlines, so the lettering is ours. The font file itself is not bundled for the logo, because
  the logo is baked art.
- **Titles (not switched yet):** titles are live text drawn by `GameText` in 13 languages. Switching them means:
  - bundle the TTF unmodified together with its OFL text (App/Resources/Fonts, Info.plist `UIAppFonts`);
  - change the title style;
  - run B3's fit sweep across all 13 languages, with the CJK cascade.

  That is App code, owned by the shell and localisation lanes, so R6 hands it over as a request. It is not done here.
