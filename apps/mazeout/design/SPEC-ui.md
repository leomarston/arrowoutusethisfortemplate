# Arrow Out: SPEC-ui (every screen, every component)

SPEC-ui writer, 2026-09-25 (+03). The look of **Arrow Out**, our 1:1 copy of "Maze Out! - Tap Puzzle" (Grand Games, v552 on the
owner's iPhone 15). This document owns **geometry, colours, text styles and on-screen copy** of every screen (SPEC.md §4). Numbers
are data: frames/fills/text land in `App/Resources/Tuning/ui.json` (SHELL) and are machine-readable in `design/ui-tokens.json`
(first pass, 243 components) + **`design/ui-tokens-2.json`** (this pass: 246 new components, 147 text styles, 164 strings, dims, roles, layout rules,
tuning values). Motion values (durations, curves, particles) belong to SPEC-motion-audio; rules/values (prices, timers, event
ladders) to SPEC-gameplay / SPEC-social. Where this document quotes one of those it says so.

The owner, verbatim (PLAN.md): *"Read GAMEPROMPT.md and make Maze Out on my phone. ultracode ultrathink"*; 02:33: *"make sure you keep
everything and all the designs same"*; 02:55: *"apply the phone, if there is ambiguity, choose the phone as it is the newer version"*.

**Copying line (SPEC.md §2).** Layouts, colours, sizes, typography and copy are copied 1:1 from the phone captures. Every pixel we ship
is ours: chrome in SwiftUI (`art/ui/code/GlossyChrome.swift` + `GameText`), icons/props as our SVG/3D renders, the "ARROW OUT!" logo as
our lettering, characters recoloured (scientist PINK, workers BLUE). The crops in `design/ui-crops/` are references to LOOK at, never
assets. The name "Arrow Out" comes only from `Brand` (PC_BRAND_NAME); the original's name appears nowhere.

---

## 0 Read this first

### 0.1 What this document decides, and who builds it
| decides | built by (SPEC-architecture §3) |
|---|---|
| frames, shapes, fills, gradients, bevels, shadows, dims of every screen/popup/component | SHELL (S1-S3) views; SOC2 for `App/Shell/Social/**` |
| text roles (size, tracking, face gradient, outline, drop), copy EN + TR, auto-shrink | SHELL / SOC2 via `GameText`; CONTENT merges the strings (§3) |
| z-order, anchoring and device adaptation | SHELL `ShellLayout` |
| which art id draws each graphic, the route, what is missing | UI-ART + art lanes (§4) |
| values for every `PENDING-ui` knob and every `_pending` key of `Tuning/ui.json` | SHELL copies them (§5) |

### 0.2 Evidence, tags, sources
- **VERIFIED (shot)**: measured on the lossless runner captures of the owner's phone, `research/shots/NNN-*.png` and
  `research/shots/meta-NNN-*.png` (1178 × 2556 px, **pt = px × 393 / 1178**), or `research/kickoff/state.png`. **INFERRED**: reasoned from
  several captures, the reasoning is given. **DECISION**: ours (the original never showed it). Every table row carries its tag; a row
  with no tag inherits the section's.
- First pass: `design/ui-measure.md` + `ui-tokens.json` (HUD, home, pause, fail chain, win, unlock, Claw, Sky Jump, claims). This pass
  adds the meta explorer's screens (Profile, Edit Profile, Settings, Shop, Leaderboard ×3, Weekly info, More Lives, Quit Level?, Out of
  Lives!, Continue? token, Streak Race screen + info, Claw ladder states, booster UI, home states) and the player's part-2 screens
  (Weekly tutorial 130-133, Rocket Race 163-189, race bar 171/176, claims 164/172/197).
- Method (same as the first pass): `design/ui-crops/_tools/measure.py` specs in `m_meta1.py … m_meta6.py` (colour-predicate component
  frames, superellipse/rounded-rect fits, 7×7 px median fills, clean-column gradients simplified to ≤ 12 stops, text size/tracking by
  glyph matching against the shipped font with CoreText). Re-run: `cd design/ui-crops/_tools && for p in 1 2 3 4 5 6; do python3
  m_meta$p.py; done; python3 strings_fit.py; python3 build_tokens2.py`. Crops: `design/ui-crops/<screen>/<component>.png`.
- Precision: frames ±1 px (±0.35 pt); text sizes ±3 % (glyph match; fonts.md values win where both exist); a red close disc measured
  by its red body (⌀45) vs its whole ring (⌀52.4) is noted per row.
- Shorthands: `uim` = design/ui-measure.md, `tok` = ui-tokens.json, `tok2` = ui-tokens-2.json, `arch` = SPEC-architecture.md,
  `social` = SPEC-social.md, `meta` `fail` `boosters` `economy` `flows` `motion` `sounds` `tutorials` `vflows` = research/*.md,
  `STYLE` = art/STYLE.md, `MANIFEST` = art/MANIFEST.json.

### 0.3 Units, canvas, notation
- Canvas **393 × 852 pt** (iPhone 15). Safe area top **59**, bottom **34** (the original hides the status bar and draws full screen).
- **frame** = `x · y · w · h` pt from the canvas top-left, to the outer visible edge (antialiased 50 %), soft shadows excluded.
- **anchor**: `top +a` = frame top is `a` pt below the top safe inset (59); `bottom b` = frame bottom is `b` pt above the bottom safe
  inset (818 = 852 − 34; negative = below it); `centre c` = frame centre is `c` pt below the screen centre (426).
- Shapes: `se n` = superellipse |x/a|^n + |y/b|^n = 1 over the whole frame (`Superellipse` in GlossyChrome); `rr r` = rounded rect,
  circular corners of radius r; `○⌀` = circle.
- Text: `size/tracking` pt of `PCDisplay-Black` (Nunito wght 1000), `face` top→bottom gradient, `outl colour width`, `drop` = the
  outline shape moved straight down, unblurred, same colour (fonts.md §6). Every label is `GameText` taking `LocalizedStringResource`.

### 0.4 CORRECTIONS to what the build already has (read before coding)
S1 wrote `Tuning/ui.json` before this pass with guesses for screens v552 had not shown yet. The phone shows otherwise:

| # | where | the build's guess | v552 truth (this spec) | tag |
|---|---|---|---|---|
| C1 | `frames.settings.*`, `layout.settingsRows`, `layout.settings*` | Settings = a blue popup panel (ribbon, cream card, rows Sound/Music/Haptic/Notifications, links row) | Settings = a **full-screen page** like Profile: page header "Settings" + red X; a Notifications card with a pill toggle; a Sound/Music/Haptic card with three 66 pt green **square** toggle buttons (OFF = a red slash over the icon); a big green "Support" button; blue "Terms" / "Privacy" pills (§2.13) | VERIFIED meta-029..037, 132-136 |
| C2 | `frames.quit.*` | Quit Level? = the Level Failed panel | Quit Level? = the **full-width band** popup (the Continue? family): ribbon "Quit Level?", cream strip "You will lose a life!" + broken heart, a red "Quit" button in a blue frame, X (§2.5) | VERIFIED meta-075, meta-092 |
| C3 | `text.loading.label.fill #CCCCCC`, outline `#681E1A` | measured under the iOS alert | the iOS 26 alert dims the app by exactly 0.80 (255 × 0.8 = 204 = #CC): true face **#FFFFFF**, outline **#82251F** (= #681E1A ÷ 0.8) | INFERRED state.png (dim ratio exact) |
| C4 | `frames.home.scene.arrowPile` + "pile states Full/Half/Low by progress" (MANIFEST note) | the pile level follows the level number | the pile is full on every idle home; the low piles in 070/168/184/204 are frames of a **refill animation** (arrows dropping from the top chute) that plays when home re-appears after an event page (§2.2.8) | INFERRED 44 home captures |
| C5 | `text.pause.toggleOff`, `colors.toggle.off*` | not seen | OFF = blue knob on the LEFT, the right part a dark-navy track #1031A9 carrying "OFF" (face #FEF6E2, outline #093896 1.0) (§1.6.13) | VERIFIED meta-032 |
| C6 | `boardSilhouetteBorder` (MANIFEST, route A) | a magenta/blue outline around silhouette boards (store 5) | **absent on v552**: silhouette boards (L40, L52, L60, L61) are just the arrows on white. Do not build it | VERIFIED 071, 145, 194, 199 |
| C7 | social ranking list sizes (SPEC-social D12/D13: Weekly 50, Streak Race 20) | — | the phone lists **50** Streak Race rows (ranks 1-50; prizes 2000/1000/500/100 × 7) and a **10**-row Weekly group; the UI renders any length, the sizes are SPEC-social's call → flagged to the orchestrator | VERIFIED meta-045..052, meta-013..015 |
| C8 | `home.navHomeTab` only | Home selected | the raised tab moves with the selection: Shop tab raised at x 0-141.5 on the Shop page, trophy tab raised at x 253.5-393 on the Leaderboard page, each labelled ("Shop", "Leaderboard") (§2.2.6) | VERIFIED meta-012, meta-013 |

### 0.5 PENDING-ui answers (SPEC-architecture §14) at a glance
| PENDING-ui item | answer | § |
|---|---|---|
| Loading minimum time | 1.5 s from Loading's first frame, AND boot done, AND the first-launch notification alert answered; cap 4 s (alert excluded) | 2.1 |
| home tab + Loading → home transitions | Loading → home cross-fade 0.16 s; tab swap = hard cut (0 s); page open/close (Profile, Settings, event pages) = hard cut | 1.8 |
| arrow-pile states | not progress states: full pile at rest + a home-entry refill animation (Low → Half → Full + falling arrows) | 2.2.8 |
| no-lives layout | the v552 **More Lives** popup, opened by Play at 0 lives (count "0") or the lives pill when < 5 | 2.9 |
| booster-buy layout | DECISION: a booster info popup (name, icon, what it does, "Get more in the Shop!", green "Shop" → Shop tab at Bundles); v552 sells boosters only in bundles | 2.10 |
| settings layout | full page (C1) | 2.13 |
| Support/Terms/Privacy offline states | Support = offline Help page (Brand.supportEmail → Mail composer only when configured); Terms / Privacy = bundled full pages with real text | 2.13.1 |
| silhouette border | absent on v552 (C6) | 0.4 |
| box sprites/slices | the phone's Box = a code-drawn purple slab (9-slice numbers) + a counter-ring sprite (missing from MANIFEST: `boxRing`) | 4.3 |
| shop layout | full v552 layout, 3 sections, 12 products | 2.12 |

---

## 1 The system

### 1.1 Canvas and device adaptation (`ShellLayout`, arch §6.12; SPEC.md reconciliation 14)
- Design canvas 393 × 852 pt. **Width scale** `s = min(1, W / 393)` (iPhone SE/mini 375 pt → 0.954); **no upscale** above 393 (Pro Max
  430/440 pt: s = 1, content centred, full-width bands/rows/backgrounds stretch edge to edge; `layout.popupUpscale = false`).
- **Top-anchored** items (HUD, home top bar, Claw bar, event column, page headers, page content start, info-overlay titles):
  `y' = safeTop' + (y − 59) · s`. **Bottom-anchored** (bottom nav, booster corners, streak strip / race bar, "Tap to …" footers,
  pinned rows): `y'bottom = H' − safeBottom' − ((818) − ybottom) · s`. **Centre-anchored** (popups, overlays, unlock, claims):
  `ycentre' = H'/2 + (ycentre − 426) · s`. Full-bleed art (home/loading/sky backdrops) is aspect-filled on the whole screen
  (anchored at its vertical centre, cropping the width first).
- **x**: `x' = W'/2 + (x − 196.5) · s` for everything except edge-flush items (booster trays, full-width bands, rails, list rows
  keep their side insets in pt · s from their own edge).
- **Scroll areas** (Shop, Leaderboard lists, Claw ladder, Streak Race list) stretch between the header/fixed band bottom and the nav
  top (or the screen bottom when there is no nav); their row geometry is fixed.
- The board play rect (HUD bottom … booster top) is published by `ShellLayout` from the adapted HUD/booster frames (arch §6.12).
- Dynamic Island devices: nothing is drawn under the island except backgrounds; the HUD coin pill (y 30.4) sits beside it (VERIFIED 003).

### 1.2 Layer stack (arch §6.5 + §6.6)
| screen type | back → front |
|---|---|
| level | board (white) → HUD + booster corners → tutorial caption/hand → FX overlay (celebration) → popup host (dim + panels + unlock) → toasts / debug / probe |
| home | backdrop → scientist (torso, head) → console → scientist arms → platform → capsule machine → arrow pile → LEVEL caption/plate + Play frame/button (+ ribbon) → workers → top bar → Claw bar (+ tray) → event column → bottom nav → payout FX → popup host → toasts (§2.2.1) |
| page (Profile, Settings, Shop, Leaderboard, event pages) | page background → scroll content → fixed bands → page header (with X/(i)) → bottom nav (Shop/Leaderboard only) → popup host → toasts |
| popup | the screen beneath → dim → panel/band → content → buttons → ribbon (over the panel top) → close X (over the panel corner) → top-left coin group (fail offers) |

### 1.3 Dims (flat black layers, no blur; appear in 0-0.1 s, arch §6.6)
| token | alpha | used by | tag |
|---|---|---|---|
| `dim.popup` | **0.90** | Paused, Quit Level?, Continue? ×3, Level Failed, Win panel, celebration, claims, More Lives, Rocket/Sky offers, booster info | VERIFIED uim + quitLevel 0.894, moreLives 0.894, rocketOffer 0.902, claim 0.902 |
| `dim.unlock` | 0.90 | feature unlock, Claw (i), Weekly Contest (i) | VERIFIED uim; weekly (i) 0.894 |
| `dim.outOfTime` | **0.94** | Out of Time!, **Out of Lives!** (+ their coloured glow) | VERIFIED 013, meta-088 (0.941) |
| `dim.skyMatch` | 0.96 | Sky Jump matching | VERIFIED uim |
| `dim.info` (NEW) | **0.95** | Streak Race (i), Rocket Race tutorial, Sky Jump tutorial | VERIFIED meta-053 0.949, 068 0.949-0.956, 166 ≈ 0.96 |
| `dim.weeklyTutorial` (NEW) | **0.92** | L50 forced Weekly tutorial (hole over the trophy tab, §2.15.7) | VERIFIED 130 (0.921) |
| `dim.overPage` (NEW) | **0.63** | a popup opened on top of a full page (Edit Profile over Profile; Username over Profile) | VERIFIED meta-003 (0.627, IQR 0.372-0.374) |

### 1.4 Typography
One family, `PCDisplay-Black` (Nunito wght 1000, fonts.md), `PCDisplay-BlackItalic` only for event-logo lettering. `GameText` draws
four layers (drop → outline → band → face, fonts.md §6). **Auto-shrink** (SPEC.md 14): every label has a box width; the font size is
`min(maxSize, maxSize · boxW / inkWidth(maxSize))`, floor **0.70 · maxSize**; below the floor the string must be rewritten or allowed
a second line (the §3 table proves every EN and TR string fits, `strings_fit.py`). One line unless the row says 2-3.

**Ribbon titles** (every yellow arched TitlePlate): max 49 pt, tracking −0.5, box **228 pt** (VERIFIED: "Level 32" 49.0 → 193.5 pt ink;
"Continue?" shrinks to 46.6 → 226.5; "Quit Level?" 43.3 → 231.8; "Edit Profile" 42.8 → 233; "More Lives" 43.9 → 222), face #FFFFFF,
outline #7B1D01 1.9, drop 2.7-3.1 (#7B1D01), band #FFD699 1.5 pt down (fonts.md "Paused"). Baseline = ribbon top + 57.0 at 49 pt; a
shrunk title keeps its ink centred on the plate's mid-line (ribbon top + 41).

Roles (first-pass roles `role.*` stay; NEW roles of this pass):
| role | size / track | face | outline | drop | used by | tag |
|---|---|---|---|---|---|---|
| `role.pageTitle` | 37.0 / −1.0 (box 260) | #E3F7FF flat | #022880 1.0 | **4.8 #022880** (a thick 3-D extrusion) | Profile 35.6, Settings 37.0, Shop 36.8, Leaderboard 38.1 (one style; the spread is fit noise) · baseline y 84-87 | VERIFIED meta-002/029/012/013 |
| `role.infoTitle` | **FIX-V2 (2026-09-27, re-measured; the 42 pt row was not what its evidence shows)** event look 36.5 / −1.0 (box 300): face #E3F7FF with a 1.8 pt #7EBFFF band under it, #001B8B 1.3 outline extruded 3.5, a #25BDFF rim 4.4 pt out (1.1 low), a #001B8B edge 5.0 pt out (1.3 low, dropped 4.8) — "Streak Race" / "Rocket Race" / "Sky Jump" / "Claw Challenge", ink 201 / 210 / 166 / 268 pt, baselines 83.3 / 83.2 / 82.9 / 82.9; Weekly look 35.4 / −1.0: cream #FFFCF6 → #FFF3DD, #022880 1.1 extruded 3.5, #007FFF rim 4.1 pt over a #00A2F5 top light and a #003DFF foot, ink 68.4 → 330.3 (centre 199.3), baseline 83.4 | (see the look column) | | | (i) / tutorial overlay titles | VERIFIED meta-017, meta-053, 166, 068, 025 (profiles + ink boxes, FIX-V2) |
| `role.cardLabel` | 22.9 / +0.1 | #FFFFFF | #093896 1.15 | 1.15 | Settings card labels | VERIFIED meta-029 |
| `role.profileName` | 28.2 / −0.1 | #E3F7FF | #16388C 1.8 | 1.2 | Profile name | VERIFIED meta-002 |
| `role.sectionHeading` | 26.1 / −0.3 | #E3F7FF | #022880 1.0 | 1.0 | "General Stats" | VERIFIED meta-002 |
| `role.statLabel` | 14.0 / −0.2 | #FEF8F3 → #FDEEE4 | #0F2C80 0.9 | 0.8 | Profile stat labels | VERIFIED (outline width = role pattern 0.06 em) |
| `role.statValue` | 25.0 / −1.0 | #FFFFFF | #16388C 1.4 | 0.8 | Profile stat values ("57", "-") | VERIFIED meta-002 |
| `role.rowName` | 23.6 / −0.3 plain | Weekly & Streak rows **#622100**; World/Country rows **#0D1E5C** | — | — | leaderboard / race names (box 180, shrink 0.7 → then truncate "…") | VERIFIED meta-013, meta-018, meta-045 |
| `role.rowRank` | 24.8 / 0 | #FDE3C4 (weekly) / #FFFBE6 | #762217 (weekly) / #09066D (world/country) 2.0 | 0.7 | plain ranks 4+ (box 50: "455" 22.0) | VERIFIED |
| `role.rowCaption` | 15.3 / −0.25 plain | #AD7343 | — | — | "Score", "Level" above the value | VERIFIED |
| `role.rowValue` | 26 / −0.7 (box 70) | #FDE7D8 | #762217 1.8 | 0.8 | row values (Score 12, Level 14669 → shrinks, 101 fills) | VERIFIED |
| `role.shopName` | 27.8 / 0 | #FFFFFF | #16388C 1.8 | 1.8 | bundle names on blue | VERIFIED meta-012 |
| `role.shopAmount` | 30.7 / −0.3 | #FEFAF7 → #FDEEE5 | #660100 2.2 | 1.0 | "1 000", "60 000" | VERIFIED |
| `role.shopPrice` | 24.4 / −0.2 (box 110) | #FFFFFF | #066A01 1.1 | 1.2 | "49,99 TL" on the green price button | VERIFIED |
| `role.sectionPlate` | 27.6 / −0.2 | #F6FCFF (purple/blue) / #FFF9EE→#FFEDCC (yellow) | purple #560099 / blue #022880 / yellow #6D302B, 1.9 | 1.0 | Shop section plates | VERIFIED |
| `role.bigNumberPlus` | 60.4 / −1.1 | #FDF0E6 flat | Out of Time #004DFB 2.1 / Out of Lives #580008 2.1 | 2.6 | "+30 sec", "+3 Lives" | VERIFIED 013, meta-088 |
| `role.eventSubtitle` | 17.2 / −0.5 | #FDF0E6 → #FFF1D7 | #012880 0.9 | 1.5 | "Beat levels without fail to get more rewards!" (Streak Race, Claw) | VERIFIED meta-045 |
| `role.chipLabelBlue` | 22.4 / −0.8 | #FFFFFF | #022981 1.5 | 0.8 | blue chevron chips x1…x25 | VERIFIED meta-070, 021 |
| `role.chipLabelLit` | 22.6 / −0.1 | #FFFFFF | #800100 1.6 | 0.7 | the lit orange chevron chip | VERIFIED meta-070 |
| `role.toast` (NEW) | 18 / 0 | #FFFFFF | #022880 1.0 | 1.0 | toasts (§2.20) | DECISION |

Colour rule for any label this table does not list: fonts.md §6 pattern (outline ≈ 0.05 em in the dark shade of its surface, drop ≈
0.045 em, cream/white face).

### 1.5 Palette additions (tok2 `colors`)
| token | hex | where | tag |
|---|---|---|---|
| `page.header.top/mid/low` | #2B5EEE / #1C75F8 / #0283FF | page header vertical gradient (0 / 0.556 / 0.95 of 0…104.4 pt) | VERIFIED meta-002/029 |
| `page.header.hiLine` | #0C91FE | 1.3 pt line at the header's bottom (103.1-104.4) | VERIFIED |
| `page.header.lip` | #153EC4 → #0B2590 | 104.7-110.4 pt | VERIFIED |
| `page.header.shadow` | #031D6B → page | 110.4-115 pt | VERIFIED |
| `page.bg.profile` | #062496 | Profile page ground (flat) | VERIFIED |
| `page.bg.navy` | #0B2176 → #091B68 (bottom) + faint darker arrow pattern | Settings, Leaderboard list, Claw ladder, Shop bundles ground | VERIFIED meta-029 (pattern INFERRED: rotated arrow glyphs 4-6 % darker) |
| `shop.bg.offers` | #370660 | behind "Special Offers" | VERIFIED |
| `shop.bg.coins` | #460A24 | behind "Coins" | VERIFIED |
| `row.cream` | #F8E7D2 face, #FFF7EF top highlight, #AA5F45 lower lip | list rows | VERIFIED |
| `row.me` | #20F620 top → #15E815 face → #02D102, lip #008900 → #004A00 | the player's row | VERIFIED |
| `row.gold/silver/bronze` | #FEDD00 / #BCC6ED / #F89D59 | Streak Race rows 1-3 | VERIFIED meta-045 |
| `heart.lost` | #6C94DC well + top inner shadow | an empty HUD heart slot | VERIFIED meta-077 |
| `hint.green` | #00DE00 (AA rim #009100) | the hint arrow | VERIFIED boosters §1 |
| `frost.edge` | #6BD4F8 (sides) / #60EFFB (top/bottom) → white | freeze vignette | VERIFIED meta-065 |
| `toast.plate` | #0B2176 at 0.92 | toast plate | DECISION |

### 1.6 Chrome catalogue (GlossyChrome names are reserved, arch §6.11; SHELL never redefines them)
Every component below is built once and reused. Frames are the reference instance.

**1.6.1 BlueSquareButton** (back, pause, gear, (i) is separate): body 40 × 40 pt, se n 3.5-3.7, STYLE §B.1 recipe; face #008CFE (Hard
#EC0911, Super Hard #9100E4); glyph #E9FFFD. Home gear 40 × 39.7 at (334.3, 49.0). VERIFIED uim.

**1.6.2 PanelButton** (wide green/red/purple). Two sizes:
- *small* 125.1 × 89.1 (Resume/Quit), se n 3.9, label `role.buttonSmall` (max 30.5, box 96).
- *big* 211-212.5 × 86.4-88.4 (Continue, Try Again, Save, Start, Support-less), se n 4.4-5.0, label max 38.9 (box 172) — and *wide*
  231.9-233.9 × 86.4-88.1 (Add Time, Play On, Refill, +1 Live, Add Lives) with a label + coin + price.
- *framed*: every big/wide popup button sits in a **blue well** 11-12 pt larger each side (e.g. Refill face 80.7 · 451.7 · 231.9 ·
  86.4 inside frame 69.4 · 443.0 · 254.5 · 104.1; Quit face 91.1 · 499.4 · 211.2 · 86.4 inside 79.7 · 490.7 · 233.9 · 106.4): the well is
  the Play-frame recipe (#0E58C3 → #00A9FB top, #00A4F7 → #0071F3 bottom, 1 pt #0C3B01 outline) (VERIFIED meta-075/095/088, uim
  `home.playFrame`).
- Colours: green face #02E10F → #00CA00 (STYLE §B.1), red #FF3838 → #E20808 (Quit: #FF5357 top → #F83538, lip #A10000 → #4F0000,
  VERIFIED meta-075 column), purple face #8E00DF (`grad.home.playButtonSuperHard`, VERIFIED 060).
- Press: scale 0.95 on touch-down, instant; action on release (VERIFIED motion §6.3). Hit area = the frame (≥ 44 pt).

**1.6.3 CloseButton** (red X): red disc **⌀45** (face #FF3B3C, a 1.3 pt dark-red rim #AC0000 → #620000; glyph X #FFE9E9 with a 1 pt
#890E0E outline), inside a **blue ring** 3.7 pt (#1487D1 → #0C62B6 → #094FAA, outer line #053A6C; outer ⌀ **52.4**), plus a soft dark halo
to ⌀57-59 on page headers (VERIFIED meta-075 profile through the X). Positions (disc centre): pause
(361.3, 256.7), Continue/Quit band (362.3, 241.0), Out of Time/Lives (349.6-350, 76), More Lives (362.4, 198.2), Edit Profile (358.8,
160.1), Profile/page headers (355.5, 73.7; Settings 347.7, 71.5), Streak/Claw/Rocket pages (355.3, 72.1). VERIFIED (red-predicate
frames 45.0-45.4; ring frames 52.4-52.7).

**1.6.4 PanelFrame** (blue popup body): se n 5.6-6.3, 1 pt navy outline #122F8F, bar #0268E8/#0066EF ~16 pt, inner shadow band
#113AA8 → #1C5AE6 ~10 pt, field #226DF5 with a 1 pt #298FF9 rim; lighter corner BUMPERS (#00B4FF, 50.4 × 83.7) and RIVETS ⌀13 #4CA9EF at
the bar joints (uim). Widths: 370.6 (Paused, More Lives 372.6), 373.3 (Failed, Win), **382.0 (Edit Profile)**. Variants: red (Hard win),
purple (Super Hard win), sky-purple (Sky Jump), **space** (Rocket Race offer: the blue frame around a starfield panel, §2.17.1).
| instance | frame (panel fit) | n | tag |
|---|---|---|---|
| Paused | 11.3 · 224.9 · 370.6 · 402.7 (first pass 228.9 · 399.0 by a different fit; use the first pass) | 5.6-6.3 | VERIFIED |
| More Lives | 10.3 · 164.5 · 372.6 · 541.8 | 5.8 | VERIFIED meta-095 |
| Edit Profile | 5.7 · 132.1 · 382.0 · 638.9 | 6.5 | VERIFIED meta-003 |
| Level Failed / Win | 10.0 · 198.2 · 373.3 · 464.4 / 10.0 · 176.8 · 373.3 · 465.1 | 5.9-6.0 | VERIFIED uim |
| Rocket Race offer | 9.7 · 180.2 · 379.0 · 527.1 | — | VERIFIED 163 |

**1.6.5 TitlePlate** (yellow arched ribbon): 274.2 × 90.4, x 60.1; both edges follow a circle r ≈ 1100 pt (sag 4.5); end corners
r 27; face #FFD808 → #F9A600, highlight band #F4ED47-#FFF741 (11-14 %), shade #D95700, outlines #993805 / #662200 (uim). Placed so its
top is **38.4 pt above the panel top** (Paused 190.5 vs 228.9), or **39.7 pt above the band top** (bands 193.5 vs 233.2). Instances: Paused 190.5, Continue?/
Quit 193.5, Failed 171.1, Win 149.8, **More Lives 136.8, Edit Profile 93.7** (VERIFIED; yellow-core frames +2 pt, −4 pt calibration).

**1.6.6 CreamCard**: rr 24.4, 1 pt navy #192D94, bevel #B16E57 → #D49E83 → #E8BBA0 (6 pt), 1 pt #FCF0E2, fill #F8E7D2 (uim). Edit
Profile cards rr 17-18 (275.2 wide), More Lives card rr ~24 with a **sunburst** (#FFFFFA rays on #F8E7D2, 16 rays, centred on the icon)
(VERIFIED meta-003/095).

**1.6.7 BandPopup** (Continue?, Quit Level?): full-width band **0 · 233.2 · 393 · 404.8** (Quit +1 pt) — correction: uim's
`continueStreak.band` top 213.5 included the ring of the X. Top → bottom (VERIFIED column x 33 pt on 014, meta-070, meta-075, meta-089):
top rail 234.7-256 (#1D52FF line, #50ADFF highlight, **#00B4FF** face 16 pt, #1C53FF lower line; round rivets ⌀13 #4697ED at x 55 and
338), dark lip #0C2997 → #1844D2 (256-265), blue field **#226DF5** (265-303), a 2.7 pt #0038C6 line + #00076D, cream edge #CE9378 → #E9BCA1
(308-313), **cream strip #F8E7D2 313.3-470** (lower edge #E9BCA1/#BF8065 → #0038C6), blue field #226DF5 (478-608, holds the framed
button), lip #1741CA → #0B2694 (610-616), bottom rail **#005DEC → #0070FA** (620-636), outline #12329F (638).

**1.6.8 PageHeader** (NEW; Profile, Settings, Shop, Leaderboard): full width, 0 → 104.4 pt light gradient (`page.header.*`), a 1.3 pt
highlight line, a 5.7 pt lip, a 4.6 pt shadow (§1.5); title `role.pageTitle` centred, baseline 84-87; X at the right (Profile/Settings)
or a coin pill at the left (Shop). The header ignores the safe area (it paints from y 0); its content is top-anchored.

**1.6.9 PageBackground** (NEW): Profile flat #062496; Settings/Leaderboard/Claw/Shop-bundles `page.bg.navy` with the faint arrow pattern
(our pattern: a 64 pt tile of 3 rotated arrow glyphs at 5 % darker, INFERRED).

**1.6.10 SegmentTabs** (Leaderboard): 3 tabs 117.4-125.4 × 52.4 at y 122.4, x 10.0 / 137.4 / 260.9 (the selected one is 8 pt wider);
selected = green (#00E700 top → #00D800 → #076E00 lip, rr 24), unselected = deep blue (#0077EF → #0162E5 → #0055E3, lip #01176B, se
n 4.2), 1 pt dark-navy outline #0D2C9E; labels 23 pt `#FFFAF0 → #FFF1D6` with the tab's dark outline (#066A00 / #0F2C80) 1.5. The strip
behind: #167AFA band y 110-170 with a darker lip to y 186 (VERIFIED meta-013).

**1.6.11 RankRow** (Leaderboards, Streak Race): 378 × 60.4 face + a 4 pt lower lip (row pitch **72.07 pt**, gap ~7), rr 10, x 7.7;
`row.cream` or `row.me` or `row.gold/silver/bronze`; content: rank badge (hex ⌀39 × 38 for 1-3, plain `role.rowRank` for 4+, centred at
x 32), AvatarFrame 53 × 53.4 at x 54.7, name `role.rowName` from x 110, right block (Score/Level caption + `role.rowValue`, right edge
x 378). Streak rows add a prize bowl (coinBowl 55 × 43 at x 243) + a score chip (flag roll 36 × 41 + pill 53 × 33 at x 301-379).
(VERIFIED meta-013/018/045.)

**1.6.12 AvatarFrame**: se n 3.4-3.6, blue frame #0070E7 → #009BFD (5 pt ring) around a coloured portrait tile; player tile green
frame #15E615; default silhouette #627F92 on #7B98AC. Sizes: rows 53, podium 63-65, profile 103 × 97, top bar 63.4 × 61.4, Edit Profile
grid 79.7 × 80.1, race tiles 44 (VERIFIED).

**1.6.13 PillToggle** (Pause rows, Settings Notifications): 116.1-122.8 × 37.4-41.7, rr 8.5-12.6, in a 2 pt darker blue well. ON:
green left part #00E500 with "ON" (21/−0.75, face #FFFCED → #FDF3DC, outl #066A01 1.0, drop 1.0), blue knob #009BFD-#009EFC on the
right (≈ half the width, rr 9.3, a light top edge). **OFF: the knob on the LEFT, the right part a dark-navy track #1031A9 carrying
"OFF"** (21/−0.75, face #FEF6E2, outline #093896 1.0) (VERIFIED meta-032 crop `settings/notifToggleOff.png`). Tap anywhere toggles,
instant (no slide seen at 1 fps; DECISION: the knob slides 0.12 s ease-out).

**1.6.14 SquareToggle** (Settings Sound/Music/Haptic, NEW): 66.1 × 65.7 green square button (se n 3.6, face #01D501, the BoosterButton
recipe) in a blue well 74.4 × 73.1; white glyph (speaker / note / phone-vibrate, 36 pt); **OFF = a red diagonal slash** (#FF2626 core,
#CD0000 edge, 6 pt wide, top-right → bottom-left across the glyph, rounded caps) over the glyph; the button stays green (VERIFIED meta-029/
030).

**1.6.15 TimerChip** (event countdowns): cream chip #FAE7D2 rr 12, height 23-29, with the small stopwatch `iconStopwatchSmall` (24 ×
25.7) overlapping its left end; text `#622200` plain 14.5-16.3 pt ("3d 5h", "5h 13m") (VERIFIED lb, streak, rocket). The HUD-style
variant on the Claw bar/home is blue (#0095FD, white text outlined #0F2C80, uim `home.clawTimerChip`).

**1.6.16 StreakChips** (cream strip x1…x100): 372.6 × 64.7 (Streak page) / 376.7 × 66.4 (Continue?), cream #F8E7D2 with #622200 plain
labels 27.4 pt and 1 pt dividers; lit chip = green rr 9.8 (#6AFC3F top → #00B000) with a gold ring #FFC400 (82.4 × 62.1) and a label
`#FFFBE6` outlined #015100 1.9 (VERIFIED meta-045, 014).

**1.6.17 ChevronChips** (Claw, Continue? token, Streak (i)): blue arrow chips (#00A2FC → #008CFD, dark track #031A6F, 339-347 × 46-55),
lit chip = orange/gold arrow (#FED902 → #FFB700, rim #FF7A00) with `role.chipLabelLit` (VERIFIED meta-070, 021).

**1.6.18 EventProgressBar** (Claw bar/home, Claw page): uim `home.clawBar` (354.6 × 43.7) — frame #019CFB, navy track #082894, green fill
#77EE28 rr 6.8, value `n/target` 21.7 pt white outlined #061E79 1.0, hex icon at the left, reward icon at the right.

**1.6.19 CountBadge** red ⌀24.5 #FF4344 (booster stock) · **PlusBadge** green ⌀18.7 (1 pt #212C05 outline, #008602 → #11DB0E ring,
cream + #FFFCE6) on the coin icon (118.8, 73.7) and on the lives heart when lives < 5 (237.5, 73.7) · **NewsBadge** a red disc
⌀15.7 with a white "!" (dark-red outline #760F16) at (332.6, 778.7) on the trophy tab (VERIFIED meta-094, meta-001).

**1.6.20 InfoButton** "(i)": ⌀24.4 (lb) / 30.4 (Claw, Streak pages) blue #00A1FC disc, white "i" outlined navy (uim `claw.infoButton`).

**1.6.21 JumpPill** ("Bottom" / "Top", NEW): 82.4 × 28, translucent navy (#0A2A8A at 0.55 over the rows → reads #7E85A7 on cream), 1.5 pt
light-blue rim #8FB4F4, label 19.2 pt white #E0E0E0 face, #09066D outline 1.5 (VERIFIED meta-019).

**1.6.22 Toast** (NEW, §2.20).

### 1.7 Interaction states
- Buttons: pressed = scale 0.95 about the centre, instant; released = 1.0 (VERIFIED motion §6.3). Disabled (not seen): 50 % saturation
  + 0.6 alpha (DECISION; only the Continue offer when coins < price shows it, §2.6.6).
- Tabs: the selected tab is raised and labelled; unselected icons only (§2.2.6).
- Every hit area ≥ 44 × 44 pt (the X discs extend their hit area to 56 pt).
- Sounds: the UI click on release for every button (sounds.md cue 1) except the win panel's Continue (SPEC-motion-audio).

### 1.8 Transitions (arch §6.1; values into `ui.json transition.*`)
| from → to | how | value | tag |
|---|---|---|---|
| launch screen → Loading | the launch storyboard colour **#ABA0D8** (the mean colour of our `loadingBackdrop` render, so the first frame does not flash) then Loading on the first frame | — | DECISION (no publisher splash, arch D22) |
| Loading → first board | cross-fade | **0.16 s** (`transition.loadingToBoard` 0.13 → keep 0.13-0.16) | VERIFIED tutorials §1 |
| Loading → home | cross-fade | **0.16 s** (`transition.loadingToHome` 0.3 → **0.16**) | INFERRED (same mechanism as Loading → board) |
| home tabs (Shop / Home / Leaderboard) | hard cut, the raised tab moves at once | **0** (`transition.homeTabs`) | INFERRED (1 fps meta shots; no transitional frame in meta-006/007/012) |
| home → page (Profile, Settings, event pages) and back | hard cut | 0 | INFERRED |
| home → level / win Continue → home | hard cut | 0 (+0.06-0.10 s after the click) | VERIFIED motion §6.1/6.3 |
| popups / claims / offers | instant; dim 0-0.1 s | 0 | VERIFIED motion §6.3 |
| unlock overlay, info overlays, Weekly tutorial | staggered pops | SPEC-motion-audio (`unlock.*`) | VERIFIED motion §6.3 |

---

## 2 Screens

Each screen: evidence → layout table (frame, shape, fills, text, anchor, art id) → states → copy (EN / TR; the full fit table is §3)
→ accessibility ids (arch §9.8 + §6 here). First-pass components are cited by their `tok` id (all numbers in ui-tokens.json /
ui-measure.md); new ones are in `tok2`.

### 2.1 Loading (`Screen.loading`, S1 `LoadingScreen`)
Evidence: research/kickoff/state.png (v552, first launch, under the iOS alert), F00-first-launch.mov (splash 0-1.8 s, Loading from
≈1.85 s, the alert on the same frames), V1 0-0.44 s. VERIFIED unless marked.

| id | frame | content | anchor | tag / art |
|---|---|---|---|---|
| `loading.background` | 0 · 0 · 393 · 852 | our full-bleed illustration: factory floor, flying glossy arrows, the pink scientist running (`char_ld_sci` at 41.62, 231.84, 318 × 306), blue workers `char_ld_flyer` (190.08, 80.19, 150 × 204), `char_ld_runner` (176.41, 428.82, 208 × 212), `char_ld_carrier` (1.16, 369.44, 236 × 400) (z in that order, `art/out/char_loading_layout.json`) | full bleed | `loadingBackdrop` (C1) + characters lane renders; VERIFIED layout vs state.png |
| `loading.logo` | 20.0 · 66.7 · 206.8 · 160.1 (tilted ≈ −4°) | **our "ARROW OUT!" logo** (blue sign "ARROW" in yellow letters, purple arrow sign "OUT!") — the original's frame; our plate is wider for the longer word, keep the frame's centre (123.4, 146.8) and height, width may grow to 235 | top +7.7 | `logoArrowOut` (B2, 306 × 236 master scaled 0.678) |
| `loading.label` | 130.1 · 765.6 · 115.1 · 40 | "Loading" + dots cycling "." → ".." → "..." every 0.4 s (`loading.dotsPeriod`); the dots are extra glyphs to the right, the word does not move (left edge fixed at the ink x of "L") | bottom +12.4 | GameText 26.8 / −0.5, face **#FFFFFF**, outline **#82251F** 0.88, drop 0.39 (correction C3); a cable plug under it is part of the backdrop art |
| iOS notification alert | system | "“Arrow Out” Would Like to Send You Notifications" (iOS supplies it, localised) | — | first launch only (arch §6.10) |

Rules: Loading holds until (a) boot finished, (b) **≥ 1.5 s** since its first frame (`loading.minSeconds`), (c) on the first launch the
notification alert has been answered (the alert time does not count toward the 4 s cap `loading.capSeconds`). Then: fresh install →
cross-fade 0.16 s into "Levels 1-4" (HUD already in place, no HUD intro); returning player → cross-fade 0.16 s into home. DECISION on
1.5 s: the original's Loading was on screen ≥ 1.5 s in every capture (V2 3.0-11.8 s with the alert; F00 ≥ 10 s with the alert).
Strings: `Loading` / `Yükleniyor`. a11y: `loading`, `loading.label`.

### 2.2 Home (`Screen.home(_, tab: .home)`)
Evidence: 002, 026, 035, 060, 070, 101, 168, 173, 204, meta-001, 006, 056, 073, 081, 094, 097-100, 112-114, 131, 137, 138; clips
META-home-idle-12s, S1-L50-win-seq-2-continue. First-pass frames: uim "Home" (all `home.*` ids).

#### 2.2.1 Scene and characters (back → front; art/lanes/scene.md "Home composition", VERIFIED proof `scene_home_proof.png`)
| z | layer | frame | art id / file | notes |
|---|---|---|---|---|
| 0 | backdrop | 0 · 0 · 393 · 852 | `homeBackdrop` | full bleed; includes the machine's wall shadow |
| 1 | scientist torso + head (+ lids, headOpen) | `placement_pt` (104.08, 172.33), 190 × 164 | `scientist` → `art/out/char_sci_home_rig/rig.json` | PINK (owner 02:33); idle ≈ 3.16 s loop (meta §8; SPEC-motion-audio) |
| 2 | console | 95 · 266 · 214 · 109 | `homeConsole` | covers the scientist's lower torso |
| 3 | scientist arms (armL, armR / armR_point) | as rig.json | rig layers | hands rest on the console |
| 4 | platform | 0 · 576 · 393 · 182 | `homePlatform` | full width; contact shadows baked |
| 5 | capsule machine | 95 · 365 · 206 · 215 | `homeCapsuleMachine` | LEVEL recess 144-250 × 533-572 |
| 6 | arrow pile | 104 · 402 · 186 · 126 | `homeArrowPileFull` (+ Half, Low for the refill, §2.2.8) | registered to the machine window |
| 7 | UI: `home.levelCaption`, `home.levelPlate`, Play frame/button/ribbon | §2.2.5 | chrome | |
| 8 | workers (walkie left, clipboard right) | (11.37, 490.67) and (242.26, 490.33), 150 × 132 each | `workerWalkie` → `char_wk_homeL_blue_rig`, `workerClipboard` → `char_wk_homeR_blue_rig` | BLUE (owner 02:55); right worker ≈ 10.2 s loop, left > 15 s (meta §8) |
| 9 | top bar, Claw bar, event column, nav, payout FX | §2.2.2-2.2.7 | | |
Characters do not react to taps (VERIFIED META-home-tap-scientist). Play is static (no pulse, VERIFIED F01 7.3 s).

#### 2.2.2 Top bar (uim `home.*`, VERIFIED 026/meta-001/094)
| id | frame | content / states |
|---|---|---|
| `home.avatarButton` | 18.7 · 36.7 · 63.4 · 61.4, se n 3.6 | AvatarFrame (#0098FD) + the player's avatar (default silhouette #627F92); tap → Profile |
| `home.coinIcon` + `home.coinPill` + `home.plusBadge` | 95.7 · 53 · 34 · 34 / 126.8 · 55.7 · 73.7 · 32 (se n 5.3, #DEEEFF) / 118.8 · 73.7 ⌀18.7 | coins 18.8 / 0 #093896 plain, box 60 (7 digits shrink); tap anywhere on the group → Shop tab (VERIFIED meta-007) |
| `home.livesHeart` + `home.livesPill` | 212.5 · 53 · 39 · 33 / 242.2 · 56 · 76.7 · 27.4 (se n 5) | states: **full** "5" on the heart + "Full"; **counting** "4" + "mm:ss" (29:59 … 00:01, always two-digit minutes) + the green PlusBadge (237.5, 73.7) on the heart; **tick** the word "Finished" for ≈ 1 s then the next count; **unlimited** the heart shows a white "∞" glyph instead of the count and the pill "mm:ss" (< 1 h) or "1h 20m" (≥ 1 h) (VERIFIED meta-001, 035, 094, 099, economy §2b) |
| `home.livesCount` | 226.9 · 61.7 · 20 · 21.4 | count 22.8 / 0, face #FFFFFF, outl #870400 0.95, drop 1.04 |
| `home.livesTimer` / "Full" | text in the pill, centre x 285.2, baseline 77 | 18.9 / −0.35 #093896 (Full 19.1 / −0.75); box 52 |
| `home.gearButton` | 334.3 · 49 · 40 · 39.7 | BlueSquareButton + gear glyph (`glyphGear`); tap → Settings page |
Lives pill tap: full or ∞ → nothing; < 5 → More Lives popup (§2.9) (VERIFIED meta-038, meta-095, meta-114).

#### 2.2.3 Claw bar (uim `home.clawBar*`, VERIFIED 026/035/051/meta-001/168/173)
Frame 19.3 · 107.8 · 354.6 · 43.7 (top +48.8). Hex token icon `iconHexArrow` 30.7 · 110.8 · 36.7 · 34 on the left end; green fill
(#77EE28, rr 6.8) grows from x 66.7; value `n/target` centred on the track (21.7 / +0.4-0.9, white, outl #061E79 1.0); the next reward
at the right end 323.6 · 108.4 · 46 · 48.4: coin bowl + amount (12.2 pt white outl #800100, e.g. "300"), or ∞-heart + duration
("1h"), or a booster + "x1" (VERIFIED 101/168/173/204). **Multiplier badge** under the hex (53 · 143.5, ⌀35.4 + tail): x1 red-orange
badge, x5/x10/x25 orange, **x100 a gold flame badge** 53.7 · 143.5 · 34.7 · 40.4 (label 11.9 pt, outl #800100) (VERIFIED meta-001).
Timer chip under the bar: blue #0095FD 174.5 · 149.8 · 54.7 · 16.3 (text "3d 5h" 16.3, white outl #0F2C80 1.0). The chevron tray
(`home.clawMultTray` 71.1 · 141.8 · 145.8 · 42) slides out to the right of the badge during the home-return sequence (§2.2.7). Tap the
bar → Claw Challenge page. Shown from the Claw unlock (SPEC-social: L33).

#### 2.2.4 Event badges column (left, VERIFIED meta-001, 070, 168, 173, 204)
Badges stack from the top in this order, packing up when one is absent: **Streak Race**, **Rocket Race**, **Sky Jump**. Slot tops
**190.8 / 293.6 / 390.3** pt (pitch ≈ 98.5; with no Claw bar the column starts 73.4 pt higher, VERIFIED 002); x 6.7-11.7; each 76.7
× 80-83. Each badge = a gold hexagon frame (#FFC20E face, #E37F00 lower lip, 1 pt dark outline) holding the event art, standing on a
round pedestal whose front plate carries the live text: Streak = a **blue** pedestal (#2A67F0 → #1B49C8) with the countdown ("5h 32m",
≈ 16 pt white, outline #16388C 1.0, box 62); Rocket / Sky Jump = a **purple** pedestal (#4521BE → #3E12B5, gold rim #FFCD11) with
**"Join"** (≈ 13 pt white, outline #380E66 1.0; measured 10.6 pt on the ink, box 50) or, once joined, the countdown (VERIFIED crops
`homeInf/*Badge.png`). The hexagon + art is one render (`eventBadge*`, 80 × 84 pt); the pedestal plate text is live.
| badge | art id | states |
|---|---|---|
| Streak Race | `eventBadgeStreak` (chequered flags on a drum) | countdown to the event day end |
| Rocket Race | `eventBadgeRocket` (blue-gold hexagon with a rocket) | not joined: "Join"; racing: the player's rank "1"-"5" on the hex (white 20 pt, outl #0F2C80) + countdown (VERIFIED 173 "4" / "6h 8m") |
| Sky Jump | `eventBadgeSkyJump` (pink drum) | not joined: "Join"; running: levels won this run on the drum (15.6 pt, outl #DB2B6E) + the run's countdown (VERIFIED 070 "0" / "23h 57m") |
Tap → the event page / offer (§2.16-2.18). Visibility per the event schedule (SPEC-social §4.1).

#### 2.2.5 LEVEL plate and Play (uim, VERIFIED 026/035/060)
| tier | LEVEL plate (147.5 · 536.8 · 98.4 · 32.4, rr 14.8) | Play frame + button | ribbon on the button's top edge |
|---|---|---|---|
| normal | green face #05D001 (`grad.home.levelPlate`), number 30.6 / −1.5 white outl #066A01 2.14 | frame 82.7 · 622.2 · 228.2 · 103.8 (se n 4.4, blue) + green button 91.1 · 628.2 · 211.2 · 86.7 (se n 4.7); "Play" 48.8 / −3.25 #F1FFF2 outl #066A01 2.2 drop 2.2 | none |
| Hard | red face #C2090E, outline #650000 | red button 91.7 · 620.5 · 210.5 · 94.7 (se n 5.1, #F00915), label outl #650000 2.65 / drop 1.73 | **"Hard Level"** 136.8 · 620.5 · 120.1 · 30 (#FFFBE6 face, outl #650000 1.6, 17 / +0.2) on a red tab #D5221B |
| Super Hard | purple face #7400B6, outline #430080 | purple button 90.7 · 620.5 · 212.5 · 95.7 (se n 4.6, #8E00DF), label outl #430080 2.9 / drop 1.48 | **"Super Hard"** (15.8 / −0.43, outl #430080 0.9) on a purple tab #8D0DD2 (darker #5A0A8C edge) |
Caption "LEVEL" 168.5 · 518.8 (14.1 / −1.5 white outl #093198 0.82) above the plate. Level numbers up to 5 digits: plate box 84 pt
(shrink). Play: press 0.95, click on release, hard cut to the level +0.06 s (motion §6.1). At 0 lives Play opens More Lives (§2.9).

#### 2.2.6 Bottom nav (uim `home.navBar`, VERIFIED 026, meta-012, meta-013)
Bar 0 · 771.7 · 393 · 81.1 (bottom −34.8, i.e. it runs under the home indicator). Three equal columns (131 pt). The **selected** tab is a
raised lighter tile (#11D5FF / #0DCFFF with #25DAFF inner, 140.1 wide, top 753.6) whose icon overhangs its top and which shows its label
(15.1 / −0.25 white outl #16388C 1.0, baseline 832.7); unselected tabs show the icon only (shop basket 40 · 779 · 56.7 · 56.7, trophy
293.6 · 779 · 61.7 · 60.1, home garage 159.5 · 743.6 · 74.4 · 71.4 when selected / ≈ 62 when not).
**FIX-V2 (2026-09-27, INK boxes measured on 026 / meta-001 / meta-012 / meta-013 / meta-018 — the boxes above were art frames and
came out 17-20 % small):** unselected ink shop 42.4 · 782.4 · 51.4 · 52.4, home 172.4 · 780.0 · 49.0 · 55.7, trophy 297.4 · 782.4 ·
55.4 · 52.7 (ink bottoms ≈ 835.2); a selected icon is the same icon × 1.445 with its ink bottom at 814.4 (home 161.4 · 734.0 · 71.1 ·
80.4; basket ≈ 31 · 738.5 · 74.3 · 75.7; trophy 284 · 738.2 · 80 · 76.2); column grooves at x 131.8 / 259.4 (1 pt #0B9CED → #18A7FA
+ 1 pt #0042CB) between unselected tabs. ui.json `home.nav*` hold the resulting ART frames.
| selected | raised tile | label | tag |
|---|---|---|---|
| Home | 126.8 · 753.6 · 140.1 · 99.1 | "Home" / "Ana Sayfa" | VERIFIED 026 |
| Shop | 0 · 744.0 · 141.5 · 108.8 (flush left) | "Shop" / "Mağaza" (15.2 / 0) | VERIFIED meta-012 |
| Leaderboard | 253.5 · 734.0 · 139.5 · 118.8 (flush right) | "Leaderboard" / "Sıralama" (15.4 / −0.13) | VERIFIED meta-013 |
Trophy **NewsBadge** "!" at (332.6, 778.7) ⌀15.7 when the leaderboard has news (SPEC-social §3.4; cleared on opening the tab, VERIFIED
meta-013 → later homes). Icons: `navShop`, `navHome`, `navTrophy`.

#### 2.2.7 Home-return sequence and payout (geometry; timings = SPEC-motion-audio from motion §6.5, VERIFIED S1-L50-win-seq-2-continue)
After Continue on a win panel, in order (each step only if it applies):
1. Home dims to ≈ 50 % (`dim` flat black 0.50, DECISION on the exact alpha: measured ≈ 50 % luminance drop).
2. **Claw token "+1"** (`iconHexArrow` at 64 pt, centred on the capsule machine glass ≈ (198, 450)) pops; the orange **multiplier badge**
   (x25 …) appears at its right and merges into it; then **"+N"** (the points: multiplier value) shows above (white face, outline #505878
   2 pt, 25 pt, INFERRED 173 "+25", 101 "+100" at ≈ (111-160, 245-270) on its way) and the token flies to the Claw bar's hex icon
   (30.7, 110.8); the bar counts up in steps.
3. The Streak chip tray (`home.clawMultTray`) slides out under the Claw bar with the previous chip lit, the lit chip moves to the new
   multiplier, a green "+N" flag flies to the Streak badge, the tray retracts.
4. **Coin payout**: "+N" coins label (≈ 36 pt, white face, brown outline #6B3A1E 2 pt; centre ≈ (229, 484), INFERRED 129/139/144) over
   the machine with a coin pile (`coinPileSmall` ≈ 46 pt); 5 coins (`iconCoin` at 34 pt) fly in an arc to the top-bar coin icon (112.7,
   70); each arrival adds N/5 to the pill and bursts sparkles (`sparkleTwinkle`) on the icon (VERIFIED vflows §6: +120 = 5 × 24).
5. Queued popups (claims, offers, results, the daily Streak Race list) one at a time (SPEC-social §4.8).
First home ever (after L6): only step 4 with "+120" (1000 → 1120) (VERIFIED tutorials §4).

#### 2.2.8 Arrow-pile refill (correction C4)
At rest the pile is `homeArrowPileFull`. When home appears **from an event page or a popup flow that replaced the home** (Sky Jump join
070, Rocket Race page 168, Rocket lost 184, Streak Race page 204), the machine refills: `homeArrowPileLow` → `homeArrowPileHalf` →
`homeArrowPileFull` with 6-12 glossy arrows (`arrowGlossy*` at 26-34 pt) dropping from the top dispenser (x ≈ 196, y ≈ 402) into the
pile. INFERRED from 4 captures (never seen on a plain idle home, meta §8: the pile is static for 15 s); timing DECISION: 1.2 s total
(SPEC-motion-audio may refine; clips-needed candidate). After a level win the pile is full (VERIFIED 26 captures).

Home a11y (arch §9.8) plus: `home.event.streakRace|rocketRace|skyJump` (value `"join"` or `"timer:5h 32m"` / `"rank:4"`),
`home.claw.reward` (value e.g. `"coins:300"`), `nav.*.selected`.

### 2.3 Level screen: HUD, boosters, in-level feedback (S2 `HUDView`, GAME `GameScreen`)
Evidence: 003 (normal), 036 (Hard), 061 (Super Hard), meta-058..091 (L62 states), 107/110 (bump), 116; clips META-L062-*. All HUD
frames are uim `hud.*` / `booster.*` (VERIFIED); they are summarised here with the states the first pass did not have.

#### 2.3.1 Top HUD (top-anchored; uim)
| id | frame | notes |
|---|---|---|
| `hud.coinGroup` | coin 19.7 · 30.4 · 23.7 · 24.4 + pill 42.7 · 30.4 · 64.4 · 22 (rr 6.8, #BDDCFF) | digits 18.5 / +0.25 #3861AC plain, box 52; beside the Dynamic Island; not tappable in a level (DECISION: v552 never showed a reaction) |
| `hud.backButton` | 19 · 68.4 · 40 · 40 | BlueSquareButton ◀; tag colour (blue / red #EC0911 / purple #9100E4) → Quit Level? (§2.5) |
| `hud.panel` | 78.4 · 60.4 · 236.5 · 59.4, rr 18.3, #BDDCFF, shadow dy 2 σ 1.3 α 0.47 | always light blue |
| `hud.levelTab` | 149.5 · 54 · 94.4 · 23, rr 4.9 | "Level 32" / "Levels 1-4" 17.9 / −0.5 (box 84); blue #008EFE, Hard #FF3C3D, Super Hard #A628E7; outline #002985 / #5B0000 / #3E006E |
| `hud.stopwatch` + `hud.timerPill` | 92.7 · 77.7 · 29 · 33 + 112.4 · 81.7 · 73.4 · 26.4 (rr 9.3, well #6C94DC) | "m:ss" 23.3 / +0.25, face #F7F7F9 → #E2E3EA, outl #081E5E 0.67, drop 1.13; always blue; **no colour/pulse near 0** (VERIFIED fail §2 #3); "0:00" holds 1.61 s before Out of Time! |
| `hud.heart1..3` | 201.5 / 237.5 / 273.6 · 82.1 · 28.7 · 24.4 (pitch 36.1) | full = `heartHUD` (#FB3A2A); **lost = `heartHUDLost`**: the same heart outline filled with the pill well #6C94DC with the well's top inner shadow (#89AFED → #618AD4 over the top 14 %) — a recessed empty slot (VERIFIED meta-077/078); hearts are lost right → left |
| `hud.pauseButton` | 334.3 · 68.1 · 40.4 · 40 | BlueSquareButton ❚❚ (tag colour) → Paused |
No "Hard Level" tag inside the HUD on v552 (SPEC.md 10; uim flag 1).

#### 2.3.2 Booster corners (bottom-anchored; uim `booster.*`)
Trays 0 · 753.3 · 82.7 · 81.1 (left, flush to the left and bottom edges, corner se n 3.0) and 310.6 · 753.3 · 82.4 · 81.1 (right); green
buttons 57.4 × 56.4 at (14.3, 764) / (321.6, 764); icons: left **freeze** = the icy hourglass `boosterFreeze` (34.4 × 38 drawn), right
**hint** = the bulb `boosterHint` (26 × 39); red CountBadge ⌀24.5 at (53, 801.7) / (360.2, 801.7), count 16.9 pt (#FFFBF3 → #FFF2D9,
outl #69000C 0.7). States:
| state | look | tag |
|---|---|---|
| stock n ≥ 1 | red badge "n" (n ≤ 99; "99+" beyond) | VERIFIED |
| stock 0 | the red badge becomes a green PlusBadge ⌀24.5 with a white "+"; tap → booster info popup (§2.10) | DECISION (never reached on the phone) |
| active (freeze running) | the left button stays; the badge already shows n − 1; tapping again during a freeze is ignored (button press still animates) | INFERRED meta-065 |
| before the first tap | both usable (a booster does not start the timer) | VERIFIED boosters §1-2 |

#### 2.3.3 Freeze booster UI (VERIFIED meta-065, META-L062-hourglass-freeze; timings SPEC-motion-audio)
| id | frame | look |
|---|---|---|
| `hudFreeze.tray` | 92.7 · 118.4 · 92.7 · 25.0 (hangs under the HUD panel's left half, merged into its bottom edge; its lower corners rr ≈ 8) | the HUD panel material (#BDDCFF, lower lip #517CC9 → #83A9EB, grey shadow) |
| `hudFreeze.digit` | centre (107.6, 129.8) | seconds left "10" … "1" (≈ 14 pt, white face, navy outline ≈ #0D2C9E 1.0; INFERRED from the 1:1 crop, the fit failed) |
| `hudFreeze.barTrack` | 119.4 · 125.4 · 59.7 · 10.0, rr 4.7 | well #6C94DC |
| `hudFreeze.barFill` | 120.4 · 126.4 · (30.7 at 6 s of 10) · 7.0 | #2AA1FC → #0D48D3 lower half; width = 57.7 × remaining/10, anchored left |
| iced stopwatch | over `hud.stopwatch` (92.1 · 82.1 · 30.7 · 33) | `iconStopwatchFrozen` (MISSING art): the stopwatch with a snow cap on the top, frosted face, icicles on the right |
| frost vignette | full screen | edges #6BD4F8 (sides) / #60EFFB (top, bottom) fading to white; depth ≈ 27 pt at the sides, ≈ 53 pt at the top, ≈ 83 pt at the bottom; faint white ice-crack lines within 40 pt of the corners; over the board and HUD, under popups (`fxFrostVignette`, MISSING art: code gradient + an SVG crack overlay) |
Removed at the freeze end (fade, SPEC-motion-audio). The flying hourglass is `boosterFreeze` at ≈ 90 × 100 pt (VERIFIED position ≈ (190,
617) at the start).

#### 2.3.4 Hint booster (VERIFIED meta-064, META-L062-bulb-hint)
The board pans (at the current zoom) to centre one free arrow, which blinks green twice and stays **#00DE00** (AA rim #009100) until it
leaves (board engine, `hint.green`). No UI overlay; the right badge decrements.

#### 2.3.5 Bump feedback (board FX, B1; numbers from motion §4 / obstacles "BUMP", listed for completeness)
Red screen-edge vignette (≈ 50 pt deep, #FE9B9B at the edge), a red ✖ badge ≈ 1 pitch (18 pt at fit 17.9) at the contact point (#F62631
face, dark-red outline, lighter bevel), the arrow and blocker flash red, the bumped arrow stays #EE0A13; the rightmost full heart turns
`heartHUDLost` (cross-fade 0.07-0.10 s).

#### 2.3.6 Tutorial "Tap to move!" (stage 1 of "Levels 1-4" only; tutorials §3, VERIFIED V1 geometry, phone skin)
| id | frame / anchor | look |
|---|---|---|
| `tutorial.caption` | centre (196.5, 289.1); ink 75-316 × 271.5-306.7 (with "p") | "Tap to move!" / "Dokun ve çıkar!" ≈ 40 pt, tracking 0, solid navy **#121B51**, no outline, no plate, box 353 |
| `tutorial.hand` | 70 × 99 incl. the shadow; the **fingertip** is the anchor: on the hinted arrow's left stroke edge, 38 % of its length from its tail end nearest the caption (V1: (193, 424) on an arrow spanning y 387-490) | `tutorialHand` (our hand: yellow-orange cartoon hand pointing up-left, soft grey shadow down-right); all scaling about the fingertip |
No dim, no spotlight, input not restricted (tutorials §3). Removed on the first tap of any arrow.

#### 2.3.7 Level intro (geometry only; motion §6.1)
Hard cut from home; board zooms from 1.49× to fit; HUD row drops from 118 pt above its rest; boosters slide in from the sides; big timer
pops over the pill; hearts pop. The very first board (from Loading) skips the HUD intro.

### 2.4 Paused (`PopupID.pause`; uim `pause.*`, VERIFIED 007/meta-059/079/083/086)
Dim 0.90 over the level. Panel 11.3 · 228.9 · 370.6 · 399 (se n 6.3) + ribbon "Paused" (190.5) + X (361.3, 256.7) + cream card 51.4 ·
299.6 · 287.9 · 165.8 (rr 24.4) with two rows: speaker glyph 73.4 · 331.6 (`glyphSound`) "Sound" 25.5 / 0 #622100 plain + PillToggle
206.5 · 328.6 · 116.1 · 37.4; vibrate glyph 72.4 · 403.3 (`glyphHaptic`) "Haptic" + PillToggle 206.5 · 401.7. Buttons: "Resume" green
60.4 · 486.1 · 125.1 · 89.1 and "Quit" red 206.5 · 486.1 (small PanelButtons, label max 30.5, box 96). No Music row (VERIFIED meta).
Resume/X → back to the level (timer resumes); Quit → Quit Level? (§2.5). The toggles write `PlayerState.settings` like Settings.
Copy: Paused/Duraklatıldı · Sound/Ses · Haptic/Titreşim · ON/AÇIK · OFF/KAPALI · Resume/Devam · Quit/Çık.

### 2.5 Quit Level? (`PopupID.quitLevel`; correction C2; VERIFIED meta-075, meta-092)
Opened by the HUD back button (also before the first tap) or Pause → Quit. Dim 0.90. BandPopup (§1.6.7):
| id | frame | content |
|---|---|---|
| `quitLevel.ribbon` | 60.1 · 193.5 · 274.2 · 90.4 | "Quit Level?" / "Çıkılsın mı?" (43.3 measured = 49 shrunk to the 228 box) |
| `quitLevel.close` | disc centre (362.3, 241.2) ⌀45, ring ⌀52.4 | X → back to the level (timer unchanged) |
| `quitLevel.message` | centre x 196.2, baseline 344.0 | "You will lose a life!" / "Bir can kaybedeceksin!" 25.4 / −1.3 #622100 plain (box 340) |
| `quitLevel.heart` | 133.8 · 359.3 · 122.8 · 97.4 | `heartBroken` |
| `quitLevel.quit` | face 91.1 · 499.4 · 211.2 · 86.4 (se n 4.5) in the blue frame 79.7 · 490.7 · 233.9 · 106.4 | red PanelButton "Quit" / "Çık" 43.2 pt (max 43.2, box 170), face #FFFCEE → #FDF3DC, outl #650000 2.3, drop 2.25 |
Quit → the Level Failed popup (§2.6.5) (a loss: streak reset, the life stays spent; VERIFIED fail §5).

### 2.6 The fail chain (SPEC-gameplay owns the order/prices; VERIFIED fail §1)
Each popup appears complete in one frame (VERIFIED META-L062-timer-last-seconds). The top-left **coin group** (a larger coin pill with
a green +: 12.7 · 62.4 · 108.4 · 44.4 on Out of Time/Lives; 12.7 · 96.1 · 105.1 · 41.4 on Continue?; digits 21.4 / +0.44 #093896) stays
above the dim; tapping it opens the Shop (§2.12, DECISION: as a closable page; the timer stays held).

#### 2.6.1 Out of Time! (`outOfTime`; uim, VERIFIED 013/030/meta-069/128)
Dim **0.94** + a blue radial glow (#0C1840 at the stopwatch edge → #0F0F0F by 190 pt out). Title "Out of Time!" 36.4 · 173.1 (52 / −1.04,
face #FFFFFF → #FFE5E5, double outline #580008 1.5 + #E42831 3, drop 4.7; box 345), big stopwatch 91.7 · 273.6 · 208.2 · 220.9
(`stopwatchBig`), "+30 sec" (`role.bigNumberPlus`, outline #004DFB) baseline 554.7, green wide button in a blue frame 71.7 · 627.5 ·
249.9 · 104.1: "Add Time" 23.1 + coin + "900" 26.2. X (350, 76) top-right (top +16.9).

#### 2.6.2 Out of Lives! (`outOfLives`, NEW; VERIFIED meta-088)
Same layout as Out of Time: dim 0.94 + a **red** radial glow behind the heart (#FF2F20 at the heart edge, #480F0D at 100 pt, black by
150 pt); title "Out of Lives!" 40.7 · 177.5 · 311.6 ink (52.5 / −1.2, same style as Out of Time, box 345) baseline 215.5; big glossy
heart 103.8 · 320.6 · 184.8 · 155.1 (`heartBig` — MISSING art: a whole glossy red heart, not `heartBroken`); "+3 Lives" 60.4 / −1.1
face #FDF0E6 outline **#580008** baseline 554.7; green button face 80.7 · 633.5 · 231.9 · 86.7 in the frame 71.4 · 627.5 · 250.9 · 105.4:
"Add Lives" 23.1 + coin + "900" 26.2; X disc centre (349.6, 76.9).
Copy: Out of Lives! / Canların Bitti! · +3 Lives / +3 Can · Add Lives / Can Ekle.

#### 2.6.3 Continue? — streak (`continue:streak`; uim `continueStreak.*`, VERIFIED 014) and **token** (`continue:token`, NEW, VERIFIED meta-070, 113)
BandPopup; ribbon "Continue?" (46.6); X (362.5, 237.4).
- *streak* (the Claw Challenge is not running): message "You will lose your streak!" 22.9 / −0.34 #622100 (baseline ≈ 350) + StreakChips
  8 · 372 · 376.7 · 66.4 with the current chip lit green.
- *token* (the Claw is running and the multiplier > x1): the hex token `iconHexArrow` 50-105 × 322-375 (≈ 55 × 53) left of a 2-line
  message "You will lose **100** token" / "and your streak!" (21.0 / −0.6 #622100, baseline 343.4 / 369.1, box 235; the number in red
  **#DE0002**; TR "**100** jetonu ve" / "serini kaybedeceksin!", positional `%1$lld`); below, ChevronChips 30.0 · 390.3 · 343.6 · 53.4
  (x1 x5 x10 x25 blue, the current multiplier lit orange-gold #FED902 → #FFB700; on 113 an orange x1 chip slides over the current one =
  the reset preview, SPEC-motion-audio).
- *skipped* when the multiplier is already x1 (VERIFIED fail §1: the chain goes Out of Time → Continue? life).
Both: green wide button "Play On" + coin + "900" (79.7 · 498.4 · 233.9 · 88.1) in its blue frame.

#### 2.6.4 Continue? — life (`continue:life`; uim `continueLife.*`, VERIFIED 015/meta-071/089)
Message "You will lose a life!" 26.1 / −1.6 #622100 + `heartBroken` 134.1 · 360.6 · 123.1 · 97.4 + "Play On 900".
The old "Get 3 lives to keep playing!" variant is gone in v552 (Out of Lives! replaced it, fail §1).

#### 2.6.5 Level Failed (`levelFailed`; uim `failed.*`, VERIFIED 016/031/meta-072/080/090/093)
Panel 10 · 198.2 · 373.3 · 464.4; ribbon "Level 62" (the level label; "Level 1-4" for the FTUE session); cream card 54.7 · 280.9 · 283.9 ·
210.2 with `heartBroken` 121.4 · 302.9 · 150.5 · 119.1 and "Level Failed!" 25 / −0.7 #622100; green "Try Again" 90.4 · 517.1 · 212.5 ·
88.4 (37.7 / −1.9); X (361.3, 229.7) → home. Under it the **Streak Race strip** (§2.7.3) with x1 lit (the reset). TR: "Seviye
Başarısız!", "Tekrar Dene".

#### 2.6.6 Not enough coins (DECISION; never tried on the phone)
Play On / Add Time / Add Lives / Refill stay enabled; with coins < price a tap opens the Shop as a page over the popup (Shop + a red X in
its header right, §2.12.5) scrolled to "Coins"; closing it returns to the same offer (the level timer held throughout).

### 2.7 Win (S2; uim `celebrate`, `win*`, `streakRace.*`)
#### 2.7.1 Celebration (VERIFIED 049/053/…; timings motion §6.6)
Dim 0.90 (reached +1.58 s after the wave); **our "ARROW OUT!" logo** in the original's frame 46 · 294.9 · 307.9 · 232.2 (centre (200, 411);
`logoArrowOut`, the blue "ARROW" sign above the purple arrow sign "OUT!"; the OUT! letters balloon to > 393 pt wide during the slam);
confetti + two firework rockets (FX code). A tap anywhere skips to the panel.

#### 2.7.2 Win panel (VERIFIED 020, 037, 063, 171, 196)
| tier | panel | above the ribbon | ribbon | content |
|---|---|---|---|---|
| normal | blue 10 · 176.8 · 373.3 · 465.1 (n 5.9) | — | "Level 32" 60.1 · 149.8 | "Perfect!" 110.8 · 254.5 (45.2 / −1.6, face #FFFAF0 → #FFEDCB, outl #022880 2.4, drop 4.2); "Rewards:" 25.9 white; coin stack `coinStackReward` 141.1 · 366.6 · 120.1 · 99.1 + amount "20" 56.5 / −3.7 white outl #022880 (lower right of the stack); green "Continue" 90.4 · 497.4 · 212.5 · 88.1 (38.9 / +0.05); X (361.3, 207.7) |
| Hard | red 9.7 · 177.2 · 374 · 464.7 (field #CC0410, frame #9E0014) | **"Hard Level"** tag ribbon 76.7 · 100.1 · 240.2 · 56.7 (white face, outl #69000C 1.6, 23.4 / −1) with a skull icon each side (`iconSkull`, MISSING art) | same | amount 60 |
| Super Hard | purple 9.7 · 177.2 · 374.3 · 465.4 (field #8F01DE, frame #7306BA) | "Super Hard" tag ribbon (outl #3A007C) | same | amount 100 |
The title is always "Perfect!" (VERIFIED with hearts lost). The panel appears in one frame; coins are not counted up on it. X = Continue
(DECISION; never tapped on the phone). Copy: Perfect!/Mükemmel! · Rewards:/Ödüller: · Continue/Devam · Hard Level/Zor Seviye ·
Super Hard/Süper Zor.

#### 2.7.3 Streak Race strip (under Win and Level Failed; uim `streakRace.*`, VERIFIED 016/020/196/meta-072)
Band 0 · 700.6 · 393 · 152.1 (rail #F6F2ED, field #2A60EF; bottom-anchored), logo lettering 78.4 · 687.9 · 233.5 · 53.4 ("Streak Race" in
`PCDisplay-BlackItalic`, yellow "Streak" + white "Race", blue outline, chequered flags each side — `streakRaceLogo`), timer chip
313.6 · 707.3 · 76.7 · 28 ("9h 16m", 12.2 pt #622200), StreakChips 8 · 762 · 371.6 · 64.4 (x1 … x100, 27.2 pt #622200; lit chip green with
the gold ring). It slides up 0.13 s after the panel (motion §6.3). Shown when the Streak Race is unlocked (SPEC-social L30).

#### 2.7.4 Rocket Race bar (replaces the strip while a race runs; NEW, VERIFIED 171, 176)
| id | frame | look |
|---|---|---|
| `raceBar.band` | 0 · 687.2 · 393 · 165.5 (bottom-anchored) | top rail #01B4FF with rivets, field #2B5DEF; a **chequered finish strip** at the right edge (x 377-393, #212C50 / white squares ≈ 6 pt) |
| `raceBar.plate` | 135.1 · 689.9 · 123.1 · 25.4 (yellow plate, rr 6) | "Rocket Race" 17.8 pt white outl #800100 |
| `raceBar.timer` | 313.6 · 685.9 · 73.4 · 29.4 | TimerChip "6h 9m" |
| 5 tiles | 59.7 × 96.4 cream tiles (se n 5.3), top 736.6, x **8.7 / 80.0 / 154.7 / 228.7 / 302.3** (pitch ≈ 74; the player's tile is green, 65.7 × 107.1, top 730.6) ordered by rank **descending left → right** (rank 5 left, the leader next to the finish strip) | each: rank bubble ⌀25 on the top edge (cream, digit 16.8 pt white outl #800100; the leader's is the gold winged badge `rankWings1`), AvatarFrame 44, name 15.3 pt #622100 (box 54), progress pill "n/5" (#622200 pill, cream digits 17.5 pt) |
Order and values come from `RivalProvider.rocketRace` (SOC1).

### 2.8 Feature unlock overlay (`unlockOverlay`; uim `unlock.*`, VERIFIED 040 Pipe, 134 Box; V1 L7 geometry; beats motion §6.3)
Dim 0.90 over the level (timer not started). Centre column, x 196.5:
| id | frame | look |
|---|---|---|
| `unlock.title` | ink 128.4 · 168.5 · 136.8 · 70.1 ("Pipe!"), centre y ≈ 200 | 54.4 / −3.65 (box 345), face #FFFDF9 → #FFF3DC; a **3.0 pt layered outline** (face outward: 0.3 pt #010ABB, 1.7 pt #0140D1, a 0.4 pt light line #1C96FD, 0.9 pt #0072FF, edge #065CD7) and a 1.3 pt drop #0D49D6 (VERIFIED 040 profiles) |
| `unlock.subtitle` | 131.8 · 275.2 · 130.1 · 30 | "Unlocked!" 24.5 / +0.26 white, outl #022880 1.7, drop 1.2 |
| `unlock.icon` | 147.1 · 354.3 · 123.8 · 112.1 (centre ≈ (209, 410)) | per feature: `unlockIconLinked`, `unlockIconBox` (MISSING: the phone's purple slab + ring "5", 134), `unlockIconPipe`, `unlockIconElevator`, `unlockIconDoor`; sparkles `sparkleTwinkle` around it |
| `unlock.card` | 42.7 · 517.1 · 307.9 · 100.1, rr 23.9 | cream #F8E7D2 with a double blue border #005DEE (3-4 pt); 2 centred lines 22.3 / −0.5 navy **#231C67**, the feature word in CAPS **#1A5FD8** (box 272) |
Tap anywhere dismisses (fade 0.25 s). Card lines (FIX-V2): greedy fill in the 272 pt box (the phone's breaks, 040 / 134); when a
line would overflow, the two-line break whose wider line is narrowest, both lines shrunk by one factor ≥ 0.70 (§1.4; the TR Elevator
line ran past both card edges). Cards (SPEC.md 19 order):
| level | title EN / TR | card EN / TR (CAPS word blue) |
|---|---|---|
| 7 | Linked Arrows! / Bağlı Oklar! | LINKED ARROWS move together! / BAĞLI OKLAR birlikte hareket eder! |
| 11 | Box! / Kutu! | Clear required amount of arrows to break the BOX! / KUTUYU kırmak için gereken sayıda oku temizle! |
| 21 | Pipe! / Boru! | Pass arrows through the PIPE to break it! / Kırmak için okları BORUDAN geçir! |
| 31 | Elevator! / Asansör! | Clear all arrows on the ELEVATOR to activate it! / Çalıştırmak için ASANSÖRDEKİ tüm okları temizle! |
| 33 | Door! / Kapı! | Collect the KEY to open the DOOR! / KAPIYI açmak için ANAHTARI topla! (SPEC.md 19, DECISION) |
| (content) | Corner! / Köşe! | The CORNER turns arrows around! / KÖŞE okların yönünü çevirir! (DECISION, only if a level uses corners) |
All end with "Unlocked!" / "Açıldı!".

### 2.9 More Lives (`PopupID.noLives`, NEW; VERIFIED meta-095) — also the "no lives" popup
Opens from the lives pill when lives < 5 and from **Play (or Try Again) at 0 lives** (DECISION: v552 never reached 0; the same popup with
"0" is the honest v552-style answer). Dim 0.90 over home. Components (centre-anchored):
| id | frame | content |
|---|---|---|
| `moreLives.panel` | 10.3 · 164.5 · 372.6 · 541.8 (se n 5.8) | blue PanelFrame |
| `moreLives.ribbon` | 60.4 · 136.8 · 274.2 · 90.4 | "More Lives" / "Ekstra Can" (43.9 measured = 49 shrunk to 228) |
| `moreLives.close` | disc centre (362.4, 198.2) | X → close |
| `moreLives.card` | 59.4 · 242.5 · 275.2 · 182.8, rr ≈ 24 | cream card with a white sunburst (16 rays, #FFFFFA on #F8E7D2) centred on the heart |
| `moreLives.heart` | 150.1 · 254.2 · 95.1 · 84.1 | glossy red heart (`heartLivesBig` — MISSING, the `heartLives` art at 95 pt) with the count "3" (50.3 pt, face #FFFBE6, outl #870400 1.7) and a white "+" (bottom-right, 28 pt, outl #870400) |
| caption | centre x 196.5, baseline ≈ 369 | "Time to next live:" / "Sonraki cana kalan:" 25.4 / −0.7 #622100 plain (box 270); at 0 lives the same |
| `moreLives.timerChip` | 138.1 · 377.0 · 120.1 · 44.4 | a recessed peach capsule (rr 22): face #E7A17C, top inner shadow #B56340 → #D5A189, a light lower rim #FAEDE7 (VERIFIED column); `iconStopwatch` (34 pt) over its left end; "27:04" 25.4 / −0.7 white outl #622100 0.94 |
| `moreLives.refill` | face 80.7 · 451.7 · 231.9 · 86.4 in frame 69.4 · 443.0 · 254.5 · 104.1 | green: "Refill" 35.5 + `iconCoin` 34 + "900" 35.7 (outl #066A01 1.5, drop 1.8) → coins −900, lives = 5 (SPEC-gameplay) |
| `moreLives.adLive` (SUPERSEDED, ruling 37(d): not built; the panel ends at 589.5 like BoosterBuy's) | face 80.7 · 567.5 · 231.9 · 86.4 | green: video-clapper icon 98.8 · 591.5 · 35.7 · 37 (`iconVideoAd` — MISSING) + a red heart with "+1" (141.8 · 593.8 · 42.7 · 36.4) + "Live" 38.6 → **AdSlot** "video not available" toast; no reward in Release (SPEC.md 18) |
| `moreLives.coinGroup` | 13.0 · 64.7 · 105.1 · 41.4 (top +5.7) | the big coin pill with + (digits 21.0 #093896) → Shop |
When lives reach 5 while it is open the popup closes itself (DECISION).

### 2.10 Booster info (`PopupID.boosterBuy`, DECISION — PENDING-ui "booster-buy layout")
v552 never sells a booster alone (economy §3: only bundles) and stock never reached 0 on the phone. Tapping a booster with stock 0 opens:
the More Lives panel geometry (panel 10.3 · 164.5 · 372.6 · 541.8, ribbon, X) with ribbon = the booster name ("Time Freeze" / "Dondurucu",
"Hint" / "İpucu"), the cream sunburst card (59.4 · 242.5 · 275.2 · 182.8) holding the booster icon at 110 pt (`boosterFreeze` /
`boosterHint`) and a 2-line description (21 / −0.6 #622100, box 270): "Stops the timer for 10 seconds!" / "Süreyi 10 saniye
durdurur!" · "Shows you an arrow that can move!" / "Çıkabilecek bir oku gösterir!"; below the card "Get more in the Shop!" / "Mağazadan
daha fazlasını al!" (21 pt white outl #0F2C80, centre y 470); one framed green button "Shop" / "Mağaza" (big, 91.4 · 580 · 211.2 · 86.4)
→ Shop page (closable) scrolled to "Bundles". The level timer is held while it is open.

### 2.11 Reward claims ("Congratulations!"; uim `claim`, `claimCoins`; VERIFIED 033/034/095/100/164/172/173/197/198)
Dim 0.90, no panel. Title "Congratulations!" 10 · 151.8 · 373.7 · 53.4 (45.2 / −0.8, face #FFDD13 → #FFC302 → #FFB700, outl #B24900 0.9, extrusion
1.8; box 360; top +92.8); the reward centred at (197, ≈ 411): ∞-heart `heartInfinite` 74 × 65 + duration "30m" / "1h" (27.6 / −1.0 white
outl #B30400 1.6) · coins `coinPileSmall` 77 × 60 + amount (27.2-27.6, white outl #09066D 2.6) · booster (`boosterHint` 44 × 63) + "x1"
(15.2 pt white outl #09066D) (VERIFIED 197); "Tap to Claim" 96.7 · 673.9 (31.5 / −0.5 white outl #3A007C 1.2; bottom +110.7). Tap anywhere →
the reward flies to its counter (coins → the coin pill, ∞ → the lives heart, booster → nowhere on home) and the next queued item shows.
Used by: Claw steps, Sky Jump share (after "You win!"), Rocket Race join (∞ 30m) / win, Weekly / Streak Race results (§2.15.8, §2.16 "Result").

### 2.12 Shop (`Screen.home(_, tab: .shop)`; S3 `ShopView`; VERIFIED meta-007..012)
Full page: PageHeader + a vertical scroll + the bottom nav with the Shop tab raised (§2.2.6). No X when opened as a tab.
#### 2.12.1 Header
Coin pill 5.0 · 57.7 · 110.4 · 38.0 (#DEEEFF, se) with `iconCoin` 6.7 · 59.7 · 33.7 · 33.4 at its left, digits 18.7 #093896 (centre x 76.4,
baseline 82.6), **no plus badge** (VERIFIED); title "Shop" / "Mağaza" (`role.pageTitle`, centre 197, baseline 86.2).
#### 2.12.2 Sections (scroll content, y from 115; pitch values VERIFIED meta-008/011/012)
| block | geometry | look |
|---|---|---|
| section plate "Special Offers" | plate 60.1 · 120.8 · 273.6 · 57.0 rr 19.8 on a full-width rail (133.4-160: #6600C3 line, #C278FA highlight, #A023EF rail, rivets ⌀13 #AB42EA centred at x ≈ 31 and 362) | plate face #8E22D8 (top edge #7833B9, 1 pt navy outline); label 27.6 / −0.2 #F6FCFF outl #560099 1.9; section ground **#370660** |
| Special Offer card | 4.0 · 190.2 · 381.7 · 199.8 (the seal's box; **FIX-V2: the card itself is 8.5 · 195.4 · 376.3 · 193.4**) | gold-orange top (#FEC006 → #FDA504 with a sunburst #FDA804-#FFD522) to 304.5, a 4 pt ledge #CF6902 → #A03401, the purple strip **308.8-373** (#6C0AB1 line, #C67DFD highlight, #B55FF5 → #8300CD) + a dark foot to 377.6 (FIX-V2, meta-012 column profile; was "#A746EF, 336-384"), a gold bevel rim light inside → dark outside (sides 7 pt, top 5, bottom 10.5), the price button in a recessed #5A009C well with a #B050F4 lip; "90% OFF" seal 7.7 · 190.2 · 53.4 · 52.4 (red scalloped #DE0007 with a darker rim, "90%" 18.5 / "OFF" 15.2 white outl #69000C; TR "%90" / "İNDİRİM"); coin art (`coinPackMedium`) left 20-120 × 205-290; amount "1 000" (`role.shopAmount`, centre x 117, baseline 299.2); items tile 196.2 · 211.8 · 105.8 · 91.1 (rr 12.8, #FCA800, bottom strip #FC8800 with "x1") showing `boosterHint` + `boosterFreeze` at 30 pt; ∞ tile 307.9 · 211.8 · 59.4 · 91.1 (`heartInfiniteSmall` + "1h"); name "Special Offer" (28 / −0.25 white outl #560099, left x 22.7, baseline 350.9); price button 232.9 · 317.9 · 130.1 · 48.4 (green se n 4.9, `role.shopPrice`) |
| section plate "Bundles" | 60.1 · 403.7 · 273.6 · 58.4 (face #007EFF, rr 15.4) on a blue rail (#00B4FF, rivets) | label 28.1 / −0.7 #FFFCE6 outl #022880 1.1; ground **#0B2176** |
| bundle card ×5 | 7.7 · 472.7 · 378.3 · 194.5, rr 29.6; **pitch 203.5** | frame #0241B3 (outer #008EE3 highlight); cream top 489.7-582.6 (#F8E9DD → #F8E1CE with a faint sunburst behind the art); a 1 pt #AA5D44 seam; blue strip 588.5-648 (#00B1FF, top highlight #7AD1FF); art left (48-175 × 490-583); amount right-aligned at x 177, baseline card top + 105; items tile 196.2 · (card top + 16) · 105.8 · 91.1 (rr 11.2, #F5DECC, strip #E8C2AA with "x1", 18.5 #FEFAF7 outl #622100); ∞ tile 307.9 · … · 59.4 · 91.1; name (`role.shopName`, left 22.7, baseline card top + 155); price button 232.9 · (card top + 122) · 130.1 · 48.7 |
| corner sash | 5.0 · (card top − 1) · 87.4 · 85.7 | purple diagonal sash #B02BF6 (dark edge #5F1896) across the card's top-left corner, label 15 pt white outl #5F1896, rotated −45°: "Popular" / "Popüler" (Elite), "Best Value" / "En Avantajlı" (Legendary) |
| section plate "Coins" | 69.4 · (y) · 254.5 · 43.0 (rr 8.8) on a yellow rail (#FFDE03, rivets) | plate face #FFDE03 → #FFB500 (1 pt #A05102 outline, #D07007 top line); label 27.6 / +0.2 face #FFF9EE → #FFEDCC outl #6D302B 1.9; ground **#460A24** |
| coin tile ×6 (3 × 2) | 117.4 × 163.5; x **9.7 / 137.8 / 266.0** (pitch 128.1); row pitch **171.8** | cream top 93 pt (#FAEEE0 with a white sunburst), coin art (`coinPackTiny` … `coinPackGiant`), amount (27.6 white outl #660100 2.4 drop) at tile top + 92.8; yellow bottom #FDC306 (rim #FCF201, lip #0B3700 line) with a green price button 90.4 × 44.0 (se n 4.3) at (tile x + 14, tile top + 108): price 19.9 (box 80; "1.499,99 TL" shrinks to 14.4) |
Scroll order and contents: Special Offer (1 000 coins + 1 of each booster + ∞ 1h) · Mini (2 000 + x1 + ∞ 3h) · Epic (4 000 + x3 + 6h) ·
Elite "Popular" (8 000 + x8 + 12h) · Mega (20 000 + x18 + 36h) · Legendary "Best Value" (60 000 + x36 + 72h) · Coins 1 000 / 5 000 / 10 000 /
25 000 / 50 000 / 100 000 (VERIFIED meta §3; catalogue ids/prices = SPEC-gameplay). Thousands separator = a thin space ("1 000") in
both languages (VERIFIED EN on a TR phone).
#### 2.12.3 Prices and the test-store note (FakeStore, arch §6.8)
With StoreKit products: `displayPrice` as given. With **FakeStore** (every build the owner gets): the US prices ($0.99, $4.99, $9.99,
$19.99, $49.99, $99.99; coins $1.99 … $99.99; web-research §7) formatted by the device locale's currency style with "$" (DECISION).
The note **"Test store: nothing is charged"** / "Test mağazası: ücret alınmaz" (15 pt white outl #022880 1.0 on a #0B2176 α 0.92 chip rr
12, 330 × 26) is the first row of the scroll content, centred, above "Special Offers" (y 119-145; the sections move down 30 pt)
(`shop.testStoreNote`). DECISION: honesty rule (arch D18) outranks 1:1 here.
#### 2.12.4 Purchase flow
Tap a price → button pressed 0.95 → FakeStore: 0.3 s → the claim overlay ("Congratulations!" with the pack's coins; bundles show the coins,
then the boosters "x3", then ∞ "6h" one after another) → coins fly to the header pill. `.pending` → toast "Purchase pending." /
"Satın alma beklemede."; cancel → nothing. No Restore row (VERIFIED: v552 has none).
#### 2.12.5 Shop as a closable page (from the fail chain, booster info, coin pills)
Same page without the bottom nav, a CloseButton at the header right (disc centre (355.5, 73.7)); X returns to the caller.

### 2.13 Settings (`Screen` page; correction C1; VERIFIED meta-029..037, 132-137)
Full page, no nav: PageHeader "Settings" / "Ayarlar" + CloseButton (disc centre (347.7, 71.5)); ground `page.bg.navy`.
| id | frame | content |
|---|---|---|
| `settings.notifCard` | 19.0 · 134.1 · 355.3 · 95.7, rr 23.7 | card: 1 pt #051B56 outline, 1 pt #1440C6, face #0C91FD → #1B75F8 (top 39 %), a darker lower half #226AF1 → #2C71EF, bottom lip #00163D; ground shadow |
| bell | 44.0 · 164.5 · 30.7 · 38.4 | `glyphBell` (white bell, navy outline) |
| label | left x 83.4, baseline 189.6 | "Notifications" / "Bildirimler" `role.cardLabel` (box 150) |
| `settings.notifToggle` | 234.9 · 161.1 · 122.8 · 41.7 | PillToggle ON/OFF (§1.6.13) |
| `settings.audioCard` | 19.0 · 248.5 · 355.3 · 152.5, rr 23.6 | same card material |
| labels | centres x 90.6 / 195.7 / 300.4, baseline 290.4 | "Sound" / "Music" / "Haptic" — "Ses" / "Müzik" / "Titreşim" (`role.cardLabel`, box 90) |
| square toggles | 58.0 / 162.1 / 266.9 · 312.3 · 66.1 · 65.7 (wells 74.4 × 73.1) | SquareToggle (§1.6.14) with `glyphSound`, `glyphMusic`, `glyphHaptic` at ≈ 36 pt; OFF = red slash |
| `settings.support` | face 102.8 · 438.4 · 188.8 · 77.4 in frame 93.7 · 433.0 · 206.2 · 94.4 | green framed button "Support" / "Destek" 30.6 / −0.6 (box 150) |
| `settings.terms` / `settings.privacy` | 53.0 / 218.5 · 552.1 · 121.8 · 49.0 (se n 4.5), in 3 pt navy wells | blue pills (#0070ED face, darker lip) "Terms" / "Şartlar", "Privacy" / "Gizlilik" 22.3 white outl #093896 1.1 |
Behaviour: Notifications toggles `settings.notifications` (no iOS prompt, no toast, VERIFIED meta-032); off → cancel scheduled local
notifications; turning it ON while the iOS permission is denied keeps it ON in-app and shows the toast "Allow notifications in iOS
Settings." / "Bildirimlere iOS Ayarlar'dan izin ver." (DECISION; no deep link). Sound / Haptic toggle the buses. **Music**: the original's
button is inert with Music OFF (VERIFIED meta-133..136; sounds §3); ours toggles `settings.music` (the default OFF; no music ships unless
SPEC-motion-audio adds some — then it works). Support / Terms / Privacy open the offline pages (§2.13.1).

#### 2.13.1 Support, Terms, Privacy pages (PENDING-ui "offline states"; DECISION, honest)
Each is a full page: PageHeader with the title + CloseButton, ground `page.bg.navy`, a cream scroll card 19 · 126 · 355 · (to 34 pt above
the bottom safe inset), rr 23.7 (the Settings card shape, cream #F8E7D2 face), body text 17 / 0 #622100 plain, headings 21 pt #622100,
left-aligned, 20 pt insets, line height 1.3. No network, no web views. Text (final wording; CONTENT copies it; the numbers must follow
SPEC-gameplay's final rules):
- **Support / Destek** (title "Support" / "Destek"): *How to play* — "Tap an arrow to send it out along its path. If something is in the
  way it bumps back and you lose a heart. Clear every arrow before the time runs out!" / "Bir oka dokun, kendi yolu boyunca dışarı çıksın.
  Önünde bir şey varsa geri sekiyor ve bir kalp kaybediyorsun. Süre bitmeden bütün okları temizle!" · *Lives* — "Starting a level uses a
  life; winning gives it back. A new life arrives every 30 minutes." / "Bir seviyeye başlamak bir can harcar; kazanınca geri gelir. Her 30
  dakikada bir yeni can gelir." · *Boosters* — "The hourglass freezes the timer for 10 seconds. The bulb shows an arrow that can move." /
  "Kum saati süreyi 10 saniye dondurur. Ampul çıkabilecek bir oku gösterir." · *Your progress* — "Your progress is saved on this device." /
  "İlerlemen bu cihazda kaydedilir." · Footer: "Version %1$@ · Level %2$lld" / "Sürüm %1$@ · Seviye %2$lld". If `Brand.supportEmail` is
  set (nil by default) a green "Contact Us" / "Bize Yaz" button opens the Mail composer (subject "%@ Support" with `Brand.name`, body with
  the version and level) — the original's behaviour (VERIFIED meta-035) with our address; never the original's address.
- **Terms of Use / Kullanım Şartları**: "%@ is a game for your personal entertainment." · "Coins, lives and boosters are part of the game.
  They have no cash value and cannot be exchanged or transferred." · "Purchases are handled by Apple through the App Store." · "We may
  update the game and these terms." — TR: "%@ kişisel eğlencen için bir oyundur." · "Altınlar, canlar ve güçlendiriciler oyunun
  parçasıdır; nakit değerleri yoktur, takas edilemez ve aktarılamaz." · "Satın almalar App Store üzerinden Apple tarafından yapılır." ·
  "Oyunu ve bu şartları güncelleyebiliriz."
- **Privacy Policy / Gizlilik Politikası**: "%@ does not collect personal data." · "Your progress, settings and nickname are stored only on
  this device." · "There are no ads, no analytics and no tracking." · "Notifications are reminders scheduled on your device." ·
  "Purchases are processed by Apple." — TR: "%@ kişisel veri toplamaz." · "İlerlemen, ayarların ve takma adın yalnızca bu cihazda
  saklanır." · "Reklam, analiz ya da izleme yoktur." · "Bildirimler cihazında planlanan hatırlatmalardır." · "Satın almalar Apple
  tarafından işlenir."
(`%@` = `Brand.name`.)

### 2.14 Profile, Edit Profile, Username (S3; VERIFIED meta-002..006, V2 50-70 for the username flow)
#### 2.14.1 Profile page (tap the home avatar)
PageHeader "Profile" / "Profil" + CloseButton (355.5, 73.7); ground **#062496**.
| id | frame | content |
|---|---|---|
| `profile.card` | 12.3 · 132.4 · 367.6 · 116.4 (rr ≈ 25) | blue card: 1 pt #041F77, 1 pt #0844A7, a light top line #3797F6-#399AFA, face #1960D6 → #0549C0, lower lip #012A83 → #01184D |
| `profile.avatar` | 23.4 · 142.8 · 103.4 · 97.4 (se n 3.6) | AvatarFrame (#009BFD frame) with the player's avatar |
| `profile.pencil` | 92.1 · 208.2 · 41.4 · 40.0 | orange disc #FFBE01 (dark rim) with a white pencil (`iconPencil`) → Edit Profile |
| name | left x 137.4, baseline 199.6 | `role.profileName` (box 115; 16-char names shrink, floor 0.7, then "…") |
| `profile.levelPlate` | 258.2 · 156.5 · 110.1 · 63.4, rr 12.0 | cyan plate #00B3FB (4 rivets #1C56D7 in the corners, darker rim); "Level" / "Seviye" 19.6 / −0.35 face #FFC100 → #FF9D00 outl #16388C 1.2 (baseline 180.5) + the level 29.8 / −0.8 white outl #16388C 2.3 (baseline 207.8, box 90) |
| heading | centre 196, baseline 285.0 | "General Stats" / "Genel İstatistikler" `role.sectionHeading`, with 1 pt #00125F rules from the screen edges to 12 pt of the text (y 276) |
| 6 stat tiles (2 × 3) | pill 121.1 × 52 (capsule, face #051F86, a 2 pt lighter rim) at x **56.7 / 243.0**, y **341.6 / 440.0 / 540.8**; label above (`role.statLabel`, centred on the column 115.9 / 301.6, baselines 332.8 / 429.9 / 526.0, box 165); icon 57 × 52 overlapping the pill's left end (x 30.7 / 219.9); value `role.statValue` centred at x **118.4 / 304.6** (the pill's visible part) | 1 First Try Wins (`statFirstTryIcon` target) · 2 Weekly Contest Wins (`statWeeklyWinsIcon` medal) · 3 Streak Race Wins (`iconFlagRoll` — MISSING) · 4 Rocket Race Wins (`rocketMine` at 40 pt) · 5 Sky Jump Wins (`iconSkyDrum` — MISSING) · 6 Claw Challenge Wins (`iconHexArrow`); value "-" when 0 (VERIFIED) |
If the player has no username when Profile opens, the Username popup appears over it (not forced, VERIFIED V2 50.2).
#### 2.14.2 Edit Profile (pencil)
Dim **0.63** over the Profile page (`dim.overPage`). Panel 5.7 · 132.1 · 382.0 · 638.9; ribbon 60.4 · 93.7 "Edit Profile" / "Düzenle";
X disc centre (358.8, 160.1).
| id | frame | content |
|---|---|---|
| `editProfile.card1` | 59.1 · 204.2 · 275.2 · 97.7, rr 17.9 | CreamCard: avatar 69.4 · 211.5 · 79.4 · 80.1 (se n 3.5) + name field 157.1 · 229.2 · 171.8 · 43.0 (rr 12.9, #F6D8C0 well, inner shadow) with the name 25.4 / +0.1 **#70200D** plain (left x 168, box 115) and a pencil badge 288.9 · 236.2 · 31.7 · 32 (tap the field → keyboard) |
| `editProfile.card2` | 57.7 · 329.9 · 277.9 · 270.6, rr 16.9 | CreamCard with the 3 × 3 avatar grid: tiles 79.7 × 80.1 (se n 3.4) at x **67.4 / 156.5 / 247.5**, y **338.6 / 427.4 / 514.4** (pitch 91 × 88) |
| selected tile | 67.4 · 339.6 · 86.1 · 84.1 | green frame #16E816 (instead of blue) + a green check badge 113.4 · 390.3 · 40 · 33.4 (#36C801, white outline) at its lower right |
| `editProfile.save` | face 91.4 · 630.2 · 210.5 · 86.7 in the well 80.1 · 621.9 · 233.2 · 108.4 (#0066E8) | green "Save" / "Kaydet" 49.1 / −1.7, face #FDEFEF → #FDE7D7, outl #005914 3.0, drop 1.9 |
Grid order (v552: default + 8 portraits, no scroll, VERIFIED meta-003/004): default silhouette · blue cap + wrench · green cap + glasses ·
detective (bowler + moustache) · burger · pink scientist · party (hat + sunglasses) · box on the head · notebook — our renders (art lane,
2026-09-25 08:43-08:49, 192 × 192 px = 64 pt @3x, tile background included) `art/out/char_avatar{Walkie,CapGlasses,Detective,Burger,
Scientist,Party,BoxHead,Notebook}@3x.png`. **Avatar index table** (`SimPlayer.avatar`, the player's choice): 0 default (`avatarDefault`),
1 Walkie, 2 CapGlasses, 3 Detective, 4 Burger, 5 Scientist, 6 Party, 7 BoxHead, 8 Notebook (DECISION on the numbering; the order is the
phone's). The portrait fills the tile inside the 5-6 pt AvatarFrame ring (≈ 68 pt at the grid size). Save writes name + avatar;
X discards (VERIFIED meta-005: X saves nothing).
#### 2.14.3 Username (DECISION on the v552 skin; flow VERIFIED V2)
Dim 0.63 over Profile; the Edit Profile panel shortened to 10.3 · 250 · 372.6 · 330: ribbon "Username" / "Kullanıcı Adı"; caption
"Create your username:" / "Kullanıcı adını oluştur:" (22 / −0.5 #622100, centre y 330); the Edit Profile name field widened to 280 × 48
(centre (196.5, 380)) with the keyboard up; green "Continue" / "Devam" (big, centre (196.5, 470)); X. Rules: 3-16 characters, letters,
digits and "_"; the social blocklists apply (SPEC-social §2.8); an invalid name → the field shakes and the toast "This name is not
available." / "Bu isim kullanılamıyor.". Default name `player_` + 7 characters until the player sets one.

### 2.15 Leaderboard (`Screen.home(_, tab: .leaderboard)`; SOC2 `LeaderboardView`; VERIFIED meta-013..028, 107-111, 130-133)
Full page: PageHeader "Leaderboard" / "Sıralama" (no X) + the tab strip + the tab body + the bottom nav with the trophy tab raised.
#### 2.15.1 Tab strip (fixed)
Band 0 · 110.1 · 393 · 76.7 (#167AFA; lower lip #143BB7 → #00163E at 186-190); SegmentTabs (§1.6.10): **Weekly** 10.0 · 122.4 · 125.4 · 52.4
(selected green), **World** 137.4 · 122.4 · 117.4 · 52.0, **country** 260.9 · 122.4 · 117.4 · 52.0 (unselected blue). Labels 23 pt, box
100: "Weekly" / "Haftalık", "World" / "Dünya", the country's name from `Locale.current.localizedString(forRegionCode:)` of the player's
frozen home country (SPEC-social D5): "Turkey" / "Türkiye". If the name needs < 0.7 scale: a curated short name ("United States" → "USA" /
"ABD", "United Kingdom" → "UK" / "İngiltere", "United Arab Emirates" → "UAE" / "BAE", …; table in `Tuning/ui.json lb.countryShort`), else the
ISO alpha-3 code. The Weekly countdown chip 26.7 · 166.8 · 86.7 · 27.0 (TimerChip, "3d 5h" 15.4 #622200) hangs under the Weekly tab on
**every** tab (VERIFIED meta-018/026); hidden while Weekly is locked (DECISION). Tab switch = hard cut; each tab keeps its scroll.
#### 2.15.2 Weekly — locked (before the Weekly unlock, L50)
Body: the navy page (#0A2176) with 3 centred white lines "Reach level 50 / to compete in / Weekly Contest!" (26 / −0.5, white outl #022880
1.4, centre y 430, box 330) — TR "Haftalık Yarışmaya / katılmak için / 50. seviyeye ulaş!" (VERIFIED V2 29.5 s; v552 look INFERRED).
#### 2.15.3 Weekly — joined (VERIFIED meta-013)
| id | frame | look |
|---|---|---|
| rails + logo | rails 0 · 200.2 · 393 · 33.4 (#00B4FF face, #72D6FF top light, rivets ⌀13 #4697ED centred at x ≈ 31 / 362); logo 60.1 · 193.5 · 276.9 · 50 | "Weekly Contest" EventLogo (italic; "Weekly" face #FFED40 → #FAB910 with an orange lower shade #FC8E04 → #BB5500 and a thin #631F00 inner line, "Contest" white; a 2.5 pt blue outer outline #034AC8 with a light rim #14C4F9 and a 3 pt blue extrusion) (VERIFIED meta-013 profile) — `weeklyContestLogo` (MISSING in MANIFEST, route B1 EventLogo) |
| `lb.info` | 13.3 · 242.9 · 24.4 · 22.4 | InfoButton → Weekly info overlay (§2.15.6) |
| field | 0 · 233.6 · 393 · 270 | blue #0B8DF5 → #007FF2 |
| podium | art `leaderboardPodium` 389 × 206 at (2, 294) | blocks: 2nd lilac 4.0 · 326.9 · 127.4 · 165.8, 1st gold 123.4 · 296.9 · 146.8 · 200.2, 3rd orange 263.6 · 340.3 · 125.8 · 152.5 |
| podium avatars | 1st 166.8 · 252.2 · 63.4 · 61.4; 2nd 34.7 · 281.9 · 65.4 · 61.7; 3rd ≈ 297 · 296 · 65 · 62 (INFERRED symmetric) | AvatarFrame |
| rank hexes | centres (195.8, 319.3) gold, (66, 349) silver, (326, 361) bronze (scene lane anchors) | digits 1/2/3 live (≈ 20 pt white, outline the hex's dark shade; INFERRED) |
| names | 2nd baseline 396.1, 1st baseline 365.9, 3rd baseline 410.3; box 110 | 21 pt: 2nd face #E3F7FF outl #1E275E; 1st / 3rd face #FDE7D8 outl #800100; long default names shrink (1st "player_qqpvpjp" 10.9 pt) — floor 0.7 then "…" |
| prize bowls | `coinBowl` ≈ 62 × 52 centred on each block (1st 165.1 · 384.3) | amounts 2000 / 1000 / 500 (14.5-16.9 pt, face #FDE7D8, outl #800100) |
| score plates | on each block's foot, baseline 479.2 | "Score : 27" / "Puan : 27" (15.9-16.5, face #FDE7D8 / #FCE6D7, outl #800100 (1st, 3rd) / #1E275E (2nd)) on a dark plate |
| list | viewport 500 → 744 (the nav tile top); rows from rank 4 at 577.8 (pitch 72.07) | RankRow cream; the player's row green (`lb.rowMe` 5.0 · 503.8 · 383.3 · 66.4) |
| row content | rank centre x 32 (`role.rowRank`, #FDE3C4 outl #762217); avatar 54.7 · +4 · 53 · 53.4; name `role.rowName` **#622100** from x 110; "Score" / "Puan" caption (15.3 #AD7343) centred x 355, baseline row top + 19.2; value (`role.rowValue`) baseline row top + 45 |
The podium is fixed; the list scrolls under it. **Pinned player row**: when the player's row leaves the list viewport, a copy is pinned at the
viewport top (row above) or bottom (row below) edge (VERIFIED meta-014 top, meta-111 bottom). Ties: SPEC-social §3.1.
#### 2.15.4 World (VERIFIED meta-018..025)
List viewport 200.4 → 744 (under the chip); first row 207.2, pitch 72.07. Ranks 1-3: hex badges 39 × 38 at x 12.7 (`rankBadgeGold`,
`rankBadgeSilver`, `rankBadgeBronze`, digits live 20 pt), 4+: `role.rowRank` (#FFFBE6 face, outl #09066D; "455" 22.0, box 50). Names
**#0D1E5C**; right block "Level" / "Seviye" caption + value (5-6 digits shrink in box 70; "14669" ≈ 18 pt, "101" 26 pt). Opens at the top.
List composition (SPEC-social §3.3): ranks 1-100, a separator row "• • •" (3 cream dots ⌀6, centred, row height 36), then R−10 … R+10 with
the player's green row. **JumpPill** "Bottom" / "Aşağı" (155.1 · 706.6 · 82.4 · 28; bottom +83.4) floats while the
player's row is below the viewport → scrolls to it (VERIFIED meta-019..024 "Bottom").
#### 2.15.5 Country (VERIFIED meta-026..028, 108; V2 33.5 s)
Same rows as World. Opens scrolled so the player's row is centred; the player's row pins at the viewport bottom/top edge when scrolled
away (VERIFIED meta-027 pinned at 5.0 · 692.6 · 383.3 · 66.4); JumpPill "Top" / "Yukarı" at the same place while rank 1 is not visible
→ scrolls to rank 1 (V2 "Top"; DECISION to keep it on v552's skin).
#### 2.15.6 Weekly Contest info overlay ((i); VERIFIED meta-016/017)
Dim 0.90. `role.infoTitle` "Weekly Contest" / "Haftalık Yarışma" (centre 196.5, baseline 81.7). Items (static art + text, centred text
15-16 pt face #FCE7D7 with the key word yellow #FFD302, outline #172B5A 1.0):
| item | frame | text |
|---|---|---|
| maze icon | 37.4 · 153.5 · 115.1 · 115.1 (rr 7.3; `infoPathIcon`) | "**Beat** Levels!" / "Seviyeleri **Geç!**" centred under it, baseline 289.2 |
| arrow 1 | 192.8 · 203.2 · 37.7 · 36.7 (`pointerArrowYellow`, pointing down-right) | — |
| mini podium | 148.1 · 309.3 · 220.9 · 136.1 (podium art at 0.57 + 3 avatars; names "Max" 1000, "Neo" 2000, "James" 500 — static, not localised) | "Contest with others!" / "Diğerleriyle yarış!" baseline 464.9 |
| arrow 2 | 229.2 · 498.8 · 36.7 · 37.7 (pointing down-left) | — |
| coins | 32.7 · 525.1 · 191.5 · 83.7 (`coinPileSmall` ×3 heap) | "Win **Rewards!**" / "Ödülleri **Kazan!**" baseline 642.4 |
| trophy | 28.7 · 686.2 · 57.0 · 53.4 (`trophyCup`) | 2 lines left-aligned at x 96: "Compete against your friends!" / "There is a new contest every week!" — "Arkadaşlarınla yarış!" / "Her hafta yeni bir yarışma var!" (16 pt, baselines 712.4 / 731.1) |
| footer | centre 196.5, baseline 793.8 | "Tap to Continue" / "Devam etmek için dokun" (20.8, face #FFF5E8 → #FFDFCC, outl #172B5A 1.2) |
#### 2.15.7 L50 Weekly tutorial (forced; VERIFIED 130-133, S1-weekly-contest-open)
The first Play tap on the Weekly-unlock level: dim **0.92** over home with a **hole** over the trophy tab (279.2 · 772.3 · 93.7 · 80.4,
the tab drawn undimmed and highlighted #117FFB); card 55.7 · 514.8 · 281.9 · 82.1 (rr 14.5, cream #F8E7D2, 2.5 pt blue border #0070EA)
with 2 lines "Tap to compete in" / "Weekly Contest!" (26 / −1.0 #0D1E5C plain, baselines 548.1 / 578.8; TR "Haftalık Yarışmaya" /
"katılmak için dokun!"); a big yellow arrow 287.9 · 639.2 · 72.1 · 97.1 (`pointerArrowYellow` at 2×, pointing down) above the tab. Only the
tab accepts input (`PopupStyle.inputLock`). Tab → the info overlay → the Weekly board (the group joins now).
#### 2.15.8 Weekly result (NEW, DECISION; the original's was not captured)
At the first home after the week ends: the claim overlay (§2.11) with title "Weekly Contest" (infoTitle style, gold face like
"Congratulations!" when rank ≤ 3), the rank hex (gold/silver/bronze, 64 pt) or the plain rank, "You finished #%lld!" / "%lld. oldun!" (26 pt
white outl #022880, centre y 470), the prize (`coinPileSmall` + amount) for ranks 1-3, and "Tap to Claim" (ranks 1-3) / "Tap to Continue".

### 2.16 Streak Race (event page; SOC2 `StreakRaceView`; VERIFIED meta-045..053, 102-106, 203)
Full page, no nav, opened from the home badge or auto-shown (SPEC-social §4.4).
| id | frame | look |
|---|---|---|
| header art | 0 · 0 · 393 · 316.9 | `workerRacers` (blue workers riding a pink slide, chequered flag on the left) |
| `streak.info` / close | 5.3 · 50 · 40 · 40 / disc centre (355.3, 72.1) | InfoButton (30.4 disc) / CloseButton |
| logo | 40.0 · 298.9 · 313.6 · 54.7 (overlaps the art bottom) | "Streak Race" EventLogo (italic, yellow "Streak" + white "Race", blue outline, chequered flags each end; `streakRaceLogo`) |
| band | 0 · 313.6 · 393 · 170 | rails #00B4FF (+ rivets) at the top, field blue #2A5DEC |
| subtitle | centre 196.3, baseline 373.8 | `role.eventSubtitle` "Beat levels without fail to get more rewards!" / "Daha fazla ödül için seviyeleri hatasız geç!" (box 355) |
| chips | 11.7 · 383.7 · 372.6 · 64.7; lit 307.6 · 391.3 · 68.1 · 47.7 + gold ring 300.6 · 384.3 · 82.4 · 62.1 | StreakChips (x1 x5 x10 x25 x100) |
| timer | 154.8 · 452.7 · 84.1 · 29.0 | TimerChip "5h 13m" |
| list | viewport 485 → 852; rows 7.0 · 485.7 · 379.3 · 64.4, pitch 72.07 | RankRow: 1 gold #FEDD00, 2 silver #BCC6ED, 3 bronze #F89D59, the player green, others cream; hex badges for 1-3 |
| row content | hex 12.7 · +11 (39 × 38); avatar 54.7; name from x 110 (`role.rowName` #622100, box 130); prize bowl 243.2 · +10.7 · 55.4 · 43 (`coinBowl`, amount 14.3 white outl #660100; ranks 1-10 only: 2000/1000/500/100 ×7, SPEC-social); flag roll 301.3 · +13.4 · 35.7 · 41.4 (`scoreChip` flag-roll); score pill 325.6 · +16 · 53.4 · 33.4 (a darker shade of the row: #DFC0AD on gold VERIFIED; silver #4F63B8 and bronze #AC3C04 from store 6; green and cream rows INFERRED the same 25 % darker shade) with the score 16.4 white-cream outl #622200 (box 44) |
The band and header are fixed; the list scrolls; opens scrolled to the player's row; the player's row pins like Weekly.
**(i) overlay** (meta-053): dim 0.95; title "Streak Race"; maze icon 52.7 · 133.1 · 115.1 · 115.4 + "**Beat** levels / without losing!"
(baselines 271.7 / 291.4); arrow; the chip group x5 [x10 lit green] x25 (≈ 128-360 × 330-395) + "**Increase** your score / multiplier!"
(423.9 / 443.5); arrow; 3 mini rows (gold/silver/bronze, 31.4 · 479.4 · 162.8 · 110, a yellow up arrow at the left) + "**Earn** more flags /
than others!" (623.0 / 642.4); a warning card 59.4 · 690.6 · 274.6 · 55.4 (cream #FDF2E9, rr 8.7) with `heartBroken` (44 pt) and "If you
**fail** a level / the multiplier will reset!" (16.4 #8B5739, "fail" red #DE0002); footer "Tap to Continue" (baseline 793.4).
TR: "Seviyeleri **kaybetmeden** geç!" · "Puan **çarpanını** artır!" · "Diğerlerinden **fazla** bayrak topla!" · "Bir seviyede **kaybedersen**
çarpan sıfırlanır!".
**Result** (NEW, DECISION): after the event day ends, the next home shows this page in its final order with the countdown chip reading
"Ended" / "Bitti" and a framed green "Continue" / "Devam" (91.4 · 741.3 · 210.5 · 86.4 over a blue bottom band 0 · 717.3 · 393 · 135.4, as
Rocket Race lost); Continue → the claim overlay when the rank has a prize.

### 2.17 Rocket Race (SOC2 `RocketRaceView`; VERIFIED 163-168, 171, 176, 178, 183, 184, 189, meta-054)
#### 2.17.1 Offer popup (163 first offer, 189 re-offer)
Dim 0.90 over home. Blue PanelFrame 9.7 · 180.2 · 379.0 · 527.1 whose field is a starry night scene (a moon with a treasure chest of coins +
hearts, planets; `rocketOfferScene` — MISSING, build from the `rocketRaceBackdrop` models) ; logo "Rocket Race" 63.4 · 114.1 · 266.9 · 126.1
(two lines "Rocket" / "Race" + a rocket icon, tilted −4°, overlapping the panel top; `rocketRaceLogo`); TimerChip 153.5 · 233.5 · 86.7 · 29
("6h 20m"); first offer only: a prize bubble 214.8 · 333.6 · 158.8 · 83.4 (cream rr 10.7, rim #D39C81, tail down-left) with `coinBowl`
"500" + "+" + ∞-heart "45m"; stage strip 40.7 · 453.7 · 312.9 · 107.4 (rr 21.7): three planet tiles "Stage 1" (lit #008CFF) / "Stage 2" /
"Stage 3" (15.2 pt white outl #0A2176) + a navy text strip (#0A2C81): "Beat **5 Levels** before others to win and / advance to next stages
for greater prizes!" (14.6 white outl #0A2176, "5 Levels" #FFC400; baselines 531.9 / 547.3); framed green "Start" / "Başla" 91.4 · 575.2 ·
210.8 · 86.7 (44.3 / −3.4) with an ∞-heart icon right of the word on the first offer; X disc (360.8, 199.0).
#### 2.17.2 Join claim (164): the claim overlay with ∞ "30m". **Tutorial** (166; first join only): dim 0.95, title "Rocket Race", then
(INFERRED positions from the 166 grid): maze icon ≈ 45 · 119 · 113 · 113 + "**Beat** levels!" (centre (100, 244)); arrow; rocket (`rocketMine`
at 1.1×) ≈ 257 · 205 · 76 · 110 + "**Finish** race before / others!" (centre (295, 334)); arrow; chest heap ≈ 8 · 355 · 193 · 115 + "Win amazing
**rewards!**" (centre (107, 489)); arrow; three planets ≈ 186 · 530 · 190 · 100 + "Advance to next stages / for greater **prizes!**" (centre
(270, 657)); "Tap to Continue" (centre (197, 786)).
#### 2.17.3 Race page (167, 178)
| id | frame | look |
|---|---|---|
| header art | 0 · 0 · 393 · 227 | `rocketRaceBackdrop` top: the moon + treasure; (i) (25.4, 70.1), X (355.3, 72.1) |
| stage tag | 0 · 196.2 · 61.4 · 23.4 (flush left) | yellow tab "Stage 1" / "Aşama 1" (15.2 pt #622200 plain) |
| timer tag | 318.9 · 190.2 · 74.1 · 36.7 (flush right) | TimerChip "6h 14m" |
| logo | 93.4 · 166.8 · 203.5 · 106.8 | "Rocket Race" EventLogo |
| band | 0 · 226.9 · 393 · 110.1 | rail #00B4FF (rivets), field #1779FA → #2D72F1, text "Beat **5 levels** before others to finish / the race" (19.7 / −0.4 white outl #0F2C80 1.3, "5 levels" #FFC400; baselines 292.3 / 314.4; box 345) |
| lanes | 0 · 336.9 · 393 · 515.1; 5 lanes 78.6 wide, dividers 2 pt #0050D2 at x 78.6 / 157.2 / 235.8 / 314.4 | ground #230F6F → #5F1CB2 with stars |
| rockets | 73 × 103.4 centred in each lane; top = **630.5 − 44.5 · n** (n = levels won 0…4; VERIFIED n 0/2/3/4 on 167/178) | `rocketMine` (red-yellow, the player) / `rocketOther` (blue) |
| counter bubbles | 34 × 31.7 above each rocket (top = rocket top − 26.6) | cream speech bubble, digit 18 pt #0F2C80 |
| leader badge | 15.0 · 341.0 · 49 · 33.4 at the top of the leading lane | gold winged "1" (`rankWings1`, MISSING) |
| name tiles | centred on the lanes (39.3 / 117.9 / 196.5 / 275.1 / 353.7), 59.4 × 82.4 cream (the player 65.7 × 88.4 green), top 751.6 | AvatarFrame 44 + name 9-15 pt #622200 (box 52) |
The rival order is lane 1 = the player, then SOC1's rivals. **Lost** (183): text "You lost the race! Try again to win / amazing rewards!"; the
winner's lane is topped by a card 160.1 · 333.6 · 73.4 · 93.4 (cream) with the winged "1" and a chest (`stageChestBlue`); rockets and tiles
move up (tiles top ≈ 617); a blue bottom band 0 · 717.3 · 393 · 135.4 with a framed green "Continue" 91.4 · 741.3 · 210.5 · 86.4 → home;
the badge says "Join" again. **Won** (NEW, DECISION): the same with "You won the race! Claim your amazing rewards!" / "Yarışı kazandın!
Harika ödüllerini al!", the player's lane topped by the card, Continue → the claim overlay (stage prize) → the next stage's offer.
#### 2.17.4 Win-panel race bar: §2.7.4. Home badge: §2.2.4.

### 2.18 Sky Jump (SOC2 `SkyJumpViews`; first pass uim `skyJump`, `skyOffer`, `skyMatch`, `skyTut`, `skyMap`, `skyWin`, `claimCoins`; VERIFIED 065-070, 074-096, meta-055)
- **Offer** (065 stage 1, 096/meta-055 stage 2+): dim 0.90; sky-purple segmented panel 10.3 · 172.8 · 372.6 · 536.5 (uim note: r_top ≈ 57,
  r_bottom ≈ 80); logo "Sky Jump" 66.7 · 133.4 · 266.9 · 70.1 (`skyJumpLogo`); TimerChip (#865FF8) 158.8 · 209.5 · 75.4 · 23.4; scene
  `skyJumpPopupScene` (arrow sign "PRIZE 5000" — live text on the sign face; chest of coins); stages tray 40.7 · 455.4 · 309.9 · 105.8 (#8F6EFE
  rr 18.6): `stageChestGreen` / `Blue` / `Pink` with "Stage 1/2/3" (18 / −0.46 white outl #0F2C80 1.8; a green check `iconCheck` on won
  stages, 74.1 · 462.1 · 39.4 · 31.7) + rules strip "Pass **5 Levels** in a row on first try and advance to next stages!" (14.6 white, "5 Levels"
  yellow; the count from SPEC-social: 5/7/9); green "Start" 89.7 · 574.8 · 212.5 · 87.7; X (360.8, 199).
- **Matching** (066/067): dim 0.96; logo top +17.7; the prize island; bubble 63.1 · 470.7 · 267.2 · 96.4 (white head "Finding players on your
  level." 17.8 white outl #380E66 + cream body "29/100" → "100/100" 33 pt #622200); a fan of 14 avatar tiles 24 · 588.2 · 341 · 139.1 with the
  player's tile green-framed; "Tap to Continue" bottom +17.3.
- **Tutorial** (068): dim 0.95; uim `skyTut.*` (title, avatar fan, "Start with 100 players!", maze icon + "Beat 5 levels!", island + "Win your
  share of / 5000 coins!", stages tray + "Advance to next stages for greater prizes!", a red warning card 47.4 · 697.9 · 298.9 · 61.1 "If you
  fail a level, you will fail the challenge!", "Tap to Continue").
- **Map** (069/074/080/084/088): `skyJumpBackdrop` full bleed; header plate 0 · 103.4 · 393 · 103.4 (se n 4.2, frame #5F3AD5, inner #E5A380)
  with stat plates "Stages" (3 dots), "Levels" "n/5", "Players" "n/100" (labels 17-18 pt white outl #622200; values 19.8-20.7); TimerChip;
  pads `skyJumpPad` numbered 1-4 (live digits 28.5 pt #FFF5F9 outl #830031) up to `skyJumpIsland` (PRIZE sign live) and two
  `skyJumpIslandFar`; the player's avatar tile (71.1 × 69.1, green frame) on its pad, up to 2 rival portraits beside it; "Tap to Continue"
  bottom +18.3; (i) (24.9, 72.2) → the tutorial; X (355.5, 71.6).
- **Stage won** (094) → claim (095): uim `skyWin.*` ("Congratulations!", island, "You win!", coin plate counting up to the share, the player's
  avatar, "You are sharing the reward with / 6 other winners!", winner fan) then `claimCoins` "714" + "Tap to Claim".
- **Failed** (NEW, DECISION; SPEC-social §10): the map with the player's pad cracked (the pad art darkened 40 % + a crack overlay), a red
  card (the tutorial's warning card geometry, centre y 470) "You failed the challenge!" / "Mücadeleyi kaybettin!" (26 pt #DE0002 on cream) and
  a framed green "Continue" at 91.4 · 741.3; badge → "Join" when a new run is allowed.

### 2.19 Claw Challenge (SOC2 `ClawScreen`; first pass uim `claw.*`, `clawInfo.*`, `claim*`; VERIFIED 021-025, meta-039..044, 103)
Page: header art `clawHeaderArt` 0 · 0 · 393 · 243.5 (claw machine, the two blue workers `workerClawPair`, prizes); (i) 9.7 · 57 · 30.4 ·
30.4; X (355.5, 71.6); logo "Claw Challenge" 43.4 · 208.5 · 306.9 · 58.4 (`clawLogo`, yellow "Claw" + white "Challenge"); band 0 · 233.5 ·
393 · 200.2 (#2569F3, rails #FED023); TimerChip "3d 5h" 162.8 · 262.9 · 67.7 · 23; subtitle (`role.eventSubtitle`, 17.2); ChevronChips
18.3 · 315.3 · 347 · 55 (the current multiplier lit **orange-gold**, VERIFIED meta-039 x100); progress bar 23.4 · 380.3 · 347 · 41.7 (hex icon
left, reward right, "122/500"). Ladder (scrolls; `page.bg.navy` #0A2176): rail 20 pt (#00A6FC, edges #0035AE) at x 63.4-83.4; nodes ⌀54.7
on the rail, cards 190-208 × 74-96 (rr 16-25, cream #F8E7D2 with a 3 pt blue rim #0099F8 and a white sunburst behind the reward) at x 138.5-
347, **node pitch 121.8** (VERIFIED meta-039: cards at 477.7 / 600 / 723.3); a 2 pt connector #004CBF from each node to its card.
| step state | node | card | tag |
|---|---|---|---|
| locked | face #A7B4E6 (lilac), ring #009AFD, number white outl #172B5A 2.3 | reward icon + amount; gold padlock `padlockGold` 36.4 × 44.7 at the card's lower right (311.9 · 540.1 relative placement: card right − 35, card bottom − 34) | VERIFIED |
| next (the one the bar fills toward) | locked look + a white sunburst glow behind the node (⌀80) | as locked | VERIFIED meta-039 node 7 |
| done | face gold #FFC400 → #FF9A00, number white outl #800100 1.8 | reward replaced by a big green check (`iconCheck` 53.7 × 46.4) centred; no padlock | VERIFIED meta-039 node 6 |
Rewards (ladder data = SPEC-gameplay/social): ∞-heart + duration ("30m", "2h", "6h": 16 pt white outl #B30400 on the heart), coin bowl +
amount (12-14 pt white outl #800100), booster + "x1"/"x2". First open auto-scrolls from step 1 up to 20 (flows). (i) overlay: uim `clawInfo.*`.
Step claims: §2.11.

### 2.20 Toasts, AdSlot, FakeStore (NEW, DECISION — v552 shows no toast anywhere)

**SUPERSEDED in part (A1 STORE-APP 2026-09-28): the AdSlot and its toast are removed (SPEC.md ruling 37(d), owner item 9); the
FakeStore and its test-store chip exist only in DEBUG builds — a Release build sells through StoreKit 2 (+ RevenueCat observer)
and shows StoreKit's `displayPrice` or a disabled "…" well (release-plan §2.5 S-1…S-3). The rows below are kept as evidence.**
- **Toast**: a plate `toast.plate` (#0B2176 at α 0.92, rr 16, 1.5 pt #00B4FF border) around one or two lines of `role.toast` (18 pt white
  outl #022880 1.0, box 330, 2 lines max), padding 16 × 10; centred x; y centre **390** on home/pages, **110** pt below the top safe inset
  inside a level (`toast.homeY` / `toast.panelY` already in ui.json); above popups (z 5); hold 2.0 s, fade in 0.08 s, out 0.27 s; a new toast
  replaces the current one. a11y `toast` (label).
- Toast copy: AdSlot "Video not available right now." / "Video şu an kullanılamıyor." · "Purchase pending." / "Satın alma beklemede." ·
  "This name is not available." / "Bu isim kullanılamıyor." · "Allow notifications in iOS Settings." / "Bildirimlere iOS Ayarlar'dan izin
  ver." · "Not enough coins!" / "Yeterli altın yok!" (only if the shop cannot open).
- **AdSlot** (SPEC.md 18): every rewarded-ad button (More Lives "+1 Live") is drawn as in v552 and calls `AdSlot.show()`, which offline always
  answers "not available" → the toast above; no reward.
- **FakeStore note**: §2.12.3.

### 2.21 System prompts (not built; arch §6.10)
iOS notification alert over Loading on the first launch; iOS rating sheet on home right after the L34 win (VERIFIED 039). Both are Apple's UI;
our only job is the moment. The app name inside them is `Brand.name` (display name).

---

## 3 Copy: EN (the original's) and TR (ours)
Rules: EN is copied exactly from the captures (case and punctuation included; the original's UI is English on a Turkish phone). TR is
natural casual-game Turkish (informal "sen", short imperatives, "altın" for coins, "jeton" for tokens, "can" for lives). Numbers keep
their format in both languages (thin-space thousands "1 000", "m:ss"). Arguments are positional (`%1$lld`, `%2$@`) wherever TR reorders
them. The whole table was rendered with the shipped font at each style's size and box (`design/ui-crops/_tools/strings_fit.py` →
`out/strings_fit.json`): **every EN and TR string fits at scale ≥ 0.70**; the lowest TR scales are "KAPALI" 0.72, "Devam Et" 0.74,
"Kullanım Şartları" 0.74, "Gökyüzü Atlayışı" 0.70 (logo box). CONTENT merges these rows into `strings.tsv` (SHELL/SOC2 append them to
their `requests/*.tsv`); SPEC-gameplay's strings win where both define a key (consistency pass).

Scale columns = the auto-shrink factor needed (1.00 = fits at the full size). "lines" = lines allowed in the box.
SPEC-social §10's TR proposals are adopted where they exist ("İlk Denemede Kazanılan" 1.00, "Haftalık Yarışma Birincilikleri" 0.84 in the
165 pt stat box; the other four stats follow the same pattern). Differences for the consistency pass: "Gökyüzü Atlayışı" (not
"Zıplayışı": more natural for a jump event); "Yukarı" for Top (pairs with "Aşağı" for the v552 "Bottom"; social had "Başa");
"Düzenle" for Edit Profile (social's "Profili Düzenle" needs 0.66 in the 228 pt ribbon); the Rocket Race offer sentence reworded to fit
its 2-line strip ("5 seviyeyi herkesten önce geç, kazan ve daha büyük ödüller için ilerle!").

| key | EN | TR | size / track pt | box w pt | lines | EN scale | TR scale |
|---|---|---|---|---|---|---|---|
| `loading.label` | Loading | Yükleniyor | 26.8 / -0.50 | 200 | 1 | 1.00 | 1.00 |
| `home.play` | Play | Oyna | 48.8 / -3.25 | 170 | 1 | 1.00 | 1.00 |
| `home.levelCaption` | LEVEL | SEVİYE | 14.1 / -1.50 | 80 | 1 | 1.00 | 1.00 |
| `home.livesFull` | Full | Dolu | 19.1 / -0.75 | 52 | 1 | 1.00 | 1.00 |
| `home.livesFinished` | Finished | Doldu | 19.1 / -0.75 | 52 | 1 | 0.72 | 0.99 |
| `home.hardRibbon` | Hard Level | Zor Seviye | 17.0 / +0.20 | 100 | 1 | 1.00 | 1.00 |
| `home.superHardRibbon` | Super Hard | Süper Zor | 15.8 / -0.43 | 100 | 1 | 1.00 | 1.00 |
| `home.join` | Join | Katıl | 10.6 / +0.70 | 40 | 1 | 1.00 | 1.00 |
| `nav.home` | Home | Ana Sayfa | 15.1 / -0.25 | 118 | 1 | 1.00 | 1.00 |
| `nav.shop` | Shop | Mağaza | 15.2 / -0.05 | 118 | 1 | 1.00 | 1.00 |
| `nav.leaderboard` | Leaderboard | Sıralama | 15.4 / -0.13 | 118 | 1 | 1.00 | 1.00 |
| `hud.level` | Level %lld | Seviye %lld | 17.9 / -0.50 | 84 | 1 | 1.00 | 0.95 |
| `hud.levels14` | Levels 1-4 | Seviye 1-4 | 17.9 / -0.50 | 84 | 1 | 0.99 | 0.97 |
| `tutorial.tapToMove` | Tap to move! | Dokun ve çıkar! | 40.0 / +0.00 | 353 | 1 | 1.00 | 1.00 |
| `pause.title` | Paused | Duraklatıldı | 49.0 / -0.50 | 228 | 1 | 1.00 | 0.80 |
| `pause.sound` | Sound | Ses | 25.5 / +0.00 | 95 | 1 | 1.00 | 1.00 |
| `pause.haptic` | Haptic | Titreşim | 25.2 / -0.25 | 95 | 1 | 1.00 | 0.93 |
| `toggle.on` | ON | AÇIK | 21.0 / -0.75 | 53 | 1 | 1.00 | 1.00 |
| `toggle.off` | OFF | KAPALI | 21.0 / -0.75 | 53 | 1 | 1.00 | 0.72 |
| `pause.resume` | Resume | Devam | 30.5 / -0.50 | 96 | 1 | 0.85 | 0.98 |
| `pause.quit` | Quit | Çık | 30.5 / -0.50 | 96 | 1 | 1.00 | 1.00 |
| `quit.title` | Quit Level? | Çıkılsın mı? | 49.0 / -0.50 | 228 | 1 | 0.86 | 0.85 |
| `quit.message` | You will lose a life! | Bir can kaybedeceksin! | 25.4 / -1.28 | 340 | 1 | 1.00 | 1.00 |
| `quit.button` | Quit | Çık | 43.2 / -0.50 | 170 | 1 | 1.00 | 1.00 |
| `oot.title` | Out of Time! | Süre Bitti! | 52.0 / -1.04 | 345 | 1 | 1.00 | 1.00 |
| `oot.plus30` | +30 sec | +30 sn | 61.0 / -0.75 | 300 | 1 | 1.00 | 1.00 |
| `oot.addTime` | Add Time | Süre Ekle | 23.1 / +0.22 | 110 | 1 | 0.98 | 1.00 |
| `ool.title` | Out of Lives! | Canların Bitti! | 52.5 / -1.21 | 345 | 1 | 1.00 | 1.00 |
| `ool.plus3` | +3 Lives | +3 Can | 61.0 / -0.75 | 300 | 1 | 1.00 | 1.00 |
| `ool.addLives` | Add Lives | Can Ekle | 23.1 / +0.09 | 110 | 1 | 0.99 | 1.00 |
| `continue.title` | Continue? | Devam mı? | 49.0 / -0.50 | 228 | 1 | 0.97 | 0.89 |
| `continue.streak` | You will lose your streak! | Serini kaybedeceksin! | 22.9 / -0.34 | 280 | 1 | 1.00 | 1.00 |
| `continue.token` | You will lose %lld token and your streak! | %lld jetonu ve serini kaybedeceksin! | 21.0 / -0.64 | 235 | 2 | 1.00 | 1.00 |
| `continue.life` | You will lose a life! | Bir can kaybedeceksin! | 26.1 / -1.59 | 280 | 1 | 1.00 | 1.00 |
| `continue.playOn` | Play On | Devam Et | 31.0 / +0.40 | 110 | 1 | 0.91 | 0.74 |
| `failed.caption` | Level Failed! | Seviye Başarısız! | 25.0 / -0.71 | 250 | 1 | 1.00 | 1.00 |
| `failed.tryAgain` | Try Again | Tekrar Dene | 37.7 / -1.94 | 172 | 1 | 1.00 | 0.82 |
| `win.perfect` | Perfect! | Mükemmel! | 45.2 / -1.62 | 300 | 1 | 1.00 | 1.00 |
| `win.rewards` | Rewards: | Ödüller: | 25.9 / -1.52 | 200 | 1 | 1.00 | 1.00 |
| `win.continue` | Continue | Devam | 38.9 / +0.05 | 172 | 1 | 1.00 | 1.00 |
| `win.hardTag` | Hard Level | Zor Seviye | 23.4 / -0.96 | 150 | 1 | 1.00 | 1.00 |
| `win.superHardTag` | Super Hard | Süper Zor | 23.2 / -0.65 | 150 | 1 | 1.00 | 1.00 |
| `unlock.unlocked` | Unlocked! | Açıldı! | 24.5 / +0.26 | 300 | 1 | 1.00 | 1.00 |
| `unlock.linked.title` | Linked Arrows! | Bağlı Oklar! | 54.4 / -3.65 | 345 | 1 | 0.96 | 1.00 |
| `unlock.linked.card` | LINKED ARROWS move together! | BAĞLI OKLAR birlikte hareket eder! | 22.3 / -0.52 | 272 | 2 | 1.00 | 1.00 |
| `unlock.box.title` | Box! | Kutu! | 54.4 / -3.65 | 345 | 1 | 1.00 | 1.00 |
| `unlock.box.card` | Clear required amount of arrows to break the BOX! | KUTUYU kırmak için gereken sayıda oku temizle! | 22.3 / -0.52 | 272 | 2 | 0.89 | 0.95 |
| `unlock.pipe.title` | Pipe! | Boru! | 54.4 / -3.65 | 345 | 1 | 1.00 | 1.00 |
| `unlock.pipe.card` | Pass arrows through the PIPE to break it! | Kırmak için okları BORUDAN geçir! | 22.3 / -0.52 | 272 | 2 | 1.00 | 1.00 |
| `unlock.elevator.title` | Elevator! | Asansör! | 54.4 / -3.65 | 345 | 1 | 1.00 | 1.00 |
| `unlock.elevator.card` | Clear all arrows on the ELEVATOR to activate it! | Çalıştırmak için ASANSÖRDEKİ tüm okları temizle! | 22.3 / -0.52 | 272 | 2 | 0.95 | 0.90 |
| `unlock.door.title` | Door! | Kapı! | 54.4 / -3.65 | 345 | 1 | 1.00 | 1.00 |
| `unlock.door.card` | Collect the KEY to open the DOOR! | KAPIYI açmak için ANAHTARI topla! | 22.3 / -0.52 | 272 | 2 | 1.00 | 1.00 |
| `unlock.corner.title` | Corner! | Köşe! | 54.4 / -3.65 | 345 | 1 | 1.00 | 1.00 |
| `unlock.corner.card` | The CORNER turns arrows around! | KÖŞE okların yönünü çevirir! | 22.3 / -0.52 | 272 | 2 | 1.00 | 1.00 |
| `moreLives.title` | More Lives | Ekstra Can | 49.0 / -0.50 | 228 | 1 | 0.90 | 0.90 |
| `moreLives.next` | Time to next live: | Sonraki cana kalan: | 25.4 / -0.73 | 270 | 1 | 1.00 | 1.00 |
| `moreLives.refill` | Refill | Doldur | 35.5 / -0.92 | 120 | 1 | 1.00 | 1.00 |
| `moreLives.live` | Live | Can | 38.6 / +0.43 | 110 | 1 | 1.00 | 1.00 |
| `claim.congrats` | Congratulations! | Tebrikler! | 45.2 / -0.83 | 360 | 1 | 0.99 | 1.00 |
| `claim.tap` | Tap to Claim | Almak için dokun | 31.5 / -0.48 | 330 | 1 | 1.00 | 1.00 |
| `common.tapToContinue` | Tap to Continue | Devam etmek için dokun | 20.3 / -0.77 | 330 | 1 | 1.00 | 1.00 |
| `booster.freezeTitle` | Time Freeze | Dondurucu | 49.0 / -0.50 | 228 | 1 | 0.80 | 0.88 |
| `booster.hintTitle` | Hint | İpucu | 49.0 / -0.50 | 228 | 1 | 1.00 | 1.00 |
| `booster.freezeDesc` | Stops the timer for 10 seconds! | Süreyi 10 saniye durdurur! | 21.0 / -0.64 | 270 | 2 | 1.00 | 1.00 |
| `booster.hintDesc` | Shows you an arrow that can move! | Çıkabilecek bir oku gösterir! | 21.0 / -0.64 | 270 | 2 | 1.00 | 1.00 |
| `booster.getMore` | Get more in the Shop! | Mağazadan daha fazlasını al! | 21.0 / -0.64 | 270 | 2 | 1.00 | 1.00 |
| `booster.goShop` | Shop | Mağaza | 38.9 / +0.05 | 172 | 1 | 1.00 | 1.00 |
| `shop.title` | Shop | Mağaza | 36.8 / +0.00 | 180 | 1 | 1.00 | 1.00 |
| `shop.specialOffers` | Special Offers | Özel Teklifler | 27.6 / -0.24 | 230 | 1 | 1.00 | 1.00 |
| `shop.bundles` | Bundles | Paketler | 28.1 / -0.72 | 230 | 1 | 1.00 | 1.00 |
| `shop.coins` | Coins | Altınlar | 27.6 / +0.18 | 230 | 1 | 1.00 | 1.00 |
| `shop.specialOffer` | Special Offer | Özel Teklif | 28.0 / -0.25 | 200 | 1 | 1.00 | 1.00 |
| `shop.mini` | Mini Bundle | Mini Paket | 27.8 / +0.00 | 200 | 1 | 1.00 | 1.00 |
| `shop.epic` | Epic Bundle | Epik Paket | 27.8 / +0.00 | 200 | 1 | 1.00 | 1.00 |
| `shop.elite` | Elite Bundle | Elit Paket | 27.8 / +0.00 | 200 | 1 | 1.00 | 1.00 |
| `shop.mega` | Mega Bundle | Mega Paket | 27.8 / +0.00 | 200 | 1 | 1.00 | 1.00 |
| `shop.legendary` | Legendary Bundle | Efsanevi Paket | 27.8 / +0.00 | 200 | 1 | 0.81 | 0.99 |
| `shop.popular` | Popular | Popüler | 15.0 / +0.00 | 70 | 1 | 1.00 | 1.00 |
| `shop.bestValue` | Best Value | En Avantajlı | 15.0 / +0.00 | 70 | 1 | 0.88 | 0.78 |
| `shop.offPct` | 90% | %90 | 18.5 / +0.00 | 46 | 1 | 1.00 | 1.00 |
| `shop.offWord` | OFF | İNDİRİM | 15.2 / -1.82 | 46 | 1 | 1.00 | 0.91 |
| `shop.testNote` | Test store: nothing is charged | Test mağazası: ücret alınmaz | 15.0 / +0.00 | 330 | 1 | 1.00 | 1.00 |
| `settings.title` | Settings | Ayarlar | 37.0 / -1.19 | 220 | 1 | 1.00 | 1.00 |
| `settings.notifications` | Notifications | Bildirimler | 22.8 / +0.14 | 150 | 1 | 1.00 | 1.00 |
| `settings.sound` | Sound | Ses | 23.0 / +0.10 | 90 | 1 | 1.00 | 1.00 |
| `settings.music` | Music | Müzik | 22.9 / +0.44 | 90 | 1 | 1.00 | 1.00 |
| `settings.haptic` | Haptic | Titreşim | 22.9 / +0.10 | 90 | 1 | 1.00 | 0.94 |
| `settings.support` | Support | Destek | 30.6 / -0.61 | 150 | 1 | 1.00 | 1.00 |
| `settings.terms` | Terms | Şartlar | 22.3 / +0.00 | 95 | 1 | 1.00 | 1.00 |
| `settings.privacy` | Privacy | Gizlilik | 22.3 / +0.00 | 95 | 1 | 1.00 | 1.00 |
| `page.support` | Support | Destek | 37.0 / -1.19 | 220 | 1 | 1.00 | 1.00 |
| `page.terms` | Terms of Use | Kullanım Şartları | 37.0 / -1.19 | 220 | 1 | 0.98 | 0.74 |
| `page.privacy` | Privacy Policy | Gizlilik Politikası | 37.0 / -1.19 | 220 | 1 | 0.93 | 0.76 |
| `profile.title` | Profile | Profil | 35.6 / -0.84 | 220 | 1 | 1.00 | 1.00 |
| `profile.level` | Level | Seviye | 19.6 / -0.35 | 90 | 1 | 1.00 | 1.00 |
| `profile.generalStats` | General Stats | Genel İstatistikler | 26.1 / -0.34 | 240 | 1 | 1.00 | 1.00 |
| `profile.firstTryWins` | First Try Wins | İlk Denemede Kazanılan | 13.9 / -0.27 | 165 | 1 | 1.00 | 1.00 |
| `profile.weeklyWins` | Weekly Contest Wins | Haftalık Yarışma Birincilikleri | 14.2 / -0.34 | 165 | 1 | 1.00 | 0.84 |
| `profile.streakWins` | Streak Race Wins | Seri Yarışı Birincilikleri | 14.0 / -0.20 | 165 | 1 | 1.00 | 1.00 |
| `profile.rocketWins` | Rocket Race Wins | Roket Yarışı Birincilikleri | 14.0 / -0.20 | 165 | 1 | 1.00 | 0.99 |
| `profile.skyWins` | Sky Jump Wins | Gökyüzü Atlayışı Zaferleri | 14.0 / -0.20 | 165 | 1 | 1.00 | 0.94 |
| `profile.clawWins` | Claw Challenge Wins | Pençe Mücadelesi Zaferleri | 14.0 / -0.20 | 165 | 1 | 1.00 | 0.92 |
| `editProfile.title` | Edit Profile | Düzenle | 49.0 / -0.50 | 228 | 1 | 0.85 | 1.00 |
| `editProfile.save` | Save | Kaydet | 49.1 / -1.71 | 172 | 1 | 1.00 | 1.00 |
| `username.title` | Username | Kullanıcı Adı | 49.0 / -0.50 | 228 | 1 | 0.97 | 0.76 |
| `username.prompt` | Create your username: | Kullanıcı adını oluştur: | 22.0 / -0.50 | 270 | 1 | 1.00 | 1.00 |
| `username.continue` | Continue | Devam | 38.9 / +0.05 | 172 | 1 | 1.00 | 1.00 |
| `lb.title` | Leaderboard | Sıralama | 38.1 / -1.18 | 260 | 1 | 1.00 | 1.00 |
| `lb.weekly` | Weekly | Haftalık | 23.5 / -1.17 | 100 | 1 | 1.00 | 1.00 |
| `lb.world` | World | Dünya | 22.8 / -0.81 | 100 | 1 | 1.00 | 1.00 |
| `lb.country` | Turkey | Türkiye | 23.0 / -0.32 | 100 | 1 | 1.00 | 1.00 |
| `lb.countryLong` | Germany | Almanya | 23.0 / -0.32 | 100 | 1 | 1.00 | 1.00 |
| `lb.countryShort` | USA | ABD | 23.0 / -0.32 | 100 | 1 | 1.00 | 1.00 |
| `lb.score` | Score | Puan | 15.3 / -0.25 | 60 | 1 | 1.00 | 1.00 |
| `lb.level` | Level | Seviye | 14.5 / +0.17 | 60 | 1 | 1.00 | 1.00 |
| `lb.podiumScore` | Score : %lld | Puan : %lld | 15.9 / -0.15 | 100 | 1 | 1.00 | 1.00 |
| `lb.bottom` | Bottom | Aşağı | 19.2 / -0.50 | 70 | 1 | 1.00 | 1.00 |
| `lb.top` | Top | Yukarı | 19.2 / -0.50 | 70 | 1 | 1.00 | 1.00 |
| `lb.locked` | Reach level 50 to compete in Weekly Contest! | Haftalık Yarışmaya katılmak için 50. seviyeye ulaş! | 26.0 / -0.50 | 330 | 3 | 1.00 | 1.00 |
| `weekly.title` | Weekly Contest | Haftalık Yarışma | 32.8 / +0.00 | 330 | 1 | 1.00 | 1.00 |
| `weekly.tut` | Tap to compete in Weekly Contest! | Haftalık Yarışmaya katılmak için dokun! | 26.0 / -1.00 | 250 | 2 | 1.00 | 0.94 |
| `weekly.beat` | Beat Levels! | Seviyeleri Geç! | 15.4 / +0.00 | 170 | 1 | 1.00 | 1.00 |
| `weekly.contest` | Contest with others! | Diğerleriyle yarış! | 15.3 / +0.00 | 250 | 1 | 1.00 | 1.00 |
| `weekly.win` | Win Rewards! | Ödülleri Kazan! | 14.6 / +0.00 | 180 | 1 | 1.00 | 1.00 |
| `weekly.compete1` | Compete against your friends! | Arkadaşlarınla yarış! | 16.0 / +0.00 | 280 | 1 | 1.00 | 1.00 |
| `weekly.compete2` | There is a new contest every week! | Her hafta yeni bir yarışma var! | 16.0 / +0.00 | 280 | 1 | 1.00 | 1.00 |
| `weekly.result` | You finished #%lld! | %lld. oldun! | 26.0 / -0.50 | 300 | 1 | 1.00 | 1.00 |
| `streak.title` | Streak Race | Seri Yarışı | 45.0 / -1.00 | 290 | 1 | 1.00 | 1.00 |
| `streak.sub` | Beat levels without fail to get more rewards! | Daha fazla ödül için seviyeleri hatasız geç! | 17.2 / -0.51 | 355 | 1 | 0.98 | 1.00 |
| `streak.info1` | Beat levels without losing! | Seviyeleri kaybetmeden geç! | 15.9 / +0.00 | 190 | 2 | 1.00 | 1.00 |
| `streak.info2` | Increase your score multiplier! | Puan çarpanını artır! | 16.0 / +0.00 | 240 | 2 | 1.00 | 1.00 |
| `streak.info3` | Earn more flags than others! | Diğerlerinden fazla bayrak topla! | 15.9 / +0.00 | 200 | 2 | 1.00 | 1.00 |
| `streak.info4` | If you fail a level the multiplier will reset! | Bir seviyede kaybedersen çarpan sıfırlanır! | 16.4 / +0.00 | 190 | 2 | 1.00 | 0.99 |
| `claw.title` | Claw Challenge | Pençe Mücadelesi | 45.0 / -1.00 | 300 | 1 | 0.90 | 0.81 |
| `claw.sub` | Beat levels without fail to get more rewards! | Daha fazla ödül için seviyeleri hatasız geç! | 17.2 / -0.27 | 360 | 1 | 0.97 | 1.00 |
| `rocket.title` | Rocket Race | Roket Yarışı | 45.0 / -1.00 | 260 | 1 | 1.00 | 1.00 |
| `rocket.offer` | Beat 5 Levels before others to win and advance to next stages for greater prizes! | 5 seviyeyi herkesten önce geç, kazan ve daha büyük ödüller için ilerle! | 14.6 / -0.16 | 290 | 2 | 0.91 | 1.00 |
| `rocket.race` | Beat 5 levels before others to finish the race | Yarışı bitirmek için 5 seviyeyi herkesten önce geç | 19.7 / -0.38 | 345 | 2 | 1.00 | 1.00 |
| `rocket.lost` | You lost the race! Try again to win amazing rewards! | Yarışı kaybettin! Harika ödüller için tekrar dene! | 19.7 / -0.38 | 345 | 2 | 1.00 | 1.00 |
| `rocket.won` | You won the race! Claim your amazing rewards! | Yarışı kazandın! Harika ödüllerini al! | 19.7 / -0.38 | 345 | 2 | 1.00 | 1.00 |
| `rocket.stage` | Stage %lld | Aşama %lld | 15.2 / -0.85 | 80 | 1 | 1.00 | 1.00 |
| `rocket.start` | Start | Başla | 44.3 / -3.44 | 130 | 1 | 1.00 | 1.00 |
| `rocket.tut1` | Beat levels! | Seviyeleri geç! | 15.9 / +0.00 | 170 | 1 | 1.00 | 1.00 |
| `rocket.tut2` | Finish race before others! | Yarışı herkesten önce bitir! | 15.9 / +0.00 | 170 | 2 | 1.00 | 1.00 |
| `rocket.tut3` | Win amazing rewards! | Harika ödüller kazan! | 15.9 / +0.00 | 280 | 1 | 1.00 | 1.00 |
| `rocket.tut4` | Advance to next stages for greater prizes! | Daha büyük ödüller için sonraki aşamalara geç! | 15.9 / +0.00 | 230 | 2 | 1.00 | 1.00 |
| `sky.title` | Sky Jump | Gökyüzü Atlayışı | 45.0 / -1.00 | 250 | 1 | 1.00 | 0.70 |
| `sky.offer` | Pass %lld Levels in a row on first try and advance to next stages! | %lld seviyeyi art arda ilk denemede geç ve sonraki aşamalara ilerle! | 14.6 / -0.16 | 280 | 2 | 1.00 | 1.00 |
| `sky.finding` | Finding players on your level. | Seviyene uygun oyuncular aranıyor. | 17.8 / -0.05 | 250 | 2 | 1.00 | 1.00 |
| `sky.tut1` | Start with 100 players! | 100 oyuncuyla başla! | 17.8 / +0.05 | 200 | 1 | 0.98 | 1.00 |
| `sky.tut2` | Beat %lld levels! | %lld seviye geç! | 17.2 / +0.00 | 115 | 1 | 0.86 | 0.92 |
| `sky.tut3` | Win your share of %lld coins! | %lld altından payını kazan! | 19.7 / +0.00 | 180 | 2 | 1.00 | 1.00 |
| `sky.tut4` | Advance to next stages for greater prizes! | Daha büyük ödüller için sonraki aşamalara geç! | 16.5 / +0.09 | 340 | 1 | 0.98 | 0.87 |
| `sky.tutWarn` | If you fail a level, you will fail the challenge! | Bir seviyede kaybedersen mücadeleyi kaybedersin! | 16.4 / +0.00 | 230 | 2 | 1.00 | 1.00 |
| `sky.stages` | Stages | Aşamalar | 18.4 / -0.61 | 85 | 1 | 1.00 | 1.00 |
| `sky.levels` | Levels | Seviyeler | 17.9 / -0.04 | 85 | 1 | 1.00 | 1.00 |
| `sky.players` | Players | Oyuncular | 17.2 / -0.45 | 90 | 1 | 1.00 | 1.00 |
| `sky.prize` | PRIZE | ÖDÜL | 14.0 / +0.00 | 50 | 1 | 1.00 | 1.00 |
| `sky.youWin` | You win! | Kazandın! | 29.5 / -0.03 | 250 | 1 | 1.00 | 1.00 |
| `sky.share` | You are sharing the reward with %lld other winners! | Ödülü %lld kazananla daha paylaşıyorsun! | 21.0 / -0.22 | 320 | 2 | 1.00 | 1.00 |
| `sky.fail` | You failed the challenge! | Mücadeleyi kaybettin! | 26.0 / -0.50 | 320 | 1 | 1.00 | 1.00 |
| `stage.label` | Stage %lld | Aşama %lld | 18.0 / -0.46 | 72 | 1 | 0.85 | 0.77 |
| `adslot.unavailable` | Video not available right now. | Video şu an kullanılamıyor. | 18.0 / +0.00 | 300 | 1 | 1.00 | 1.00 |

Additional copy (no fit risk; boxes ≥ 300 pt or numbers): "Tap to Claim"/"Almak için dokun", "Tap to Continue"/"Devam etmek için dokun",
"Ended"/"Bitti", "Contact Us"/"Bize Yaz", "Purchase pending."/"Satın alma beklemede.", "This name is not available."/"Bu isim kullanılamıyor.",
"Allow notifications in iOS Settings."/"Bildirimlere iOS Ayarlar'dan izin ver.", "Not enough coins!"/"Yeterli altın yok!", the Support/
Terms/Privacy texts (§2.13.1), "Version %1$@ · Level %2$lld"/"Sürüm %1$@ · Seviye %2$lld", countdowns "%lldd %lldh" / "%lldh %lldm" /
"%lld:%02lld" (the letters d/h/m stay in TR too: the original shows "3d 5h" on the Turkish phone; DECISION keep, "g/sa/dk" would not fit the
chips). Names of simulated players and the "Max / Neo / James" podium in the Weekly info are never translated.

---

## 4 UI ART PLAN
Routes (STYLE decision summary): **A** code (board, FX), **B1** SwiftUI chrome (`GlossyChrome.swift` + `GameText`), **B2** SVG → @3x PNG,
**B3** 3D prop → @3x PNG, **C1** 3D scene/character (puppets from rigs), **C2** glossy 3D arrows, **C3** board sprites (drawn at 32 pt/cell).

### 4.1 Every MANIFEST id → where this spec uses it (199 entries; "file on disk" checked 2026-09-25)
| group | id | family / route | file on disk | MANIFEST status | used in (this spec) |
|---|---|---|---|---|---|
| board | `boardArrow` | code / A | — | todo | board (B1) |
| board | `boardExitColour` | code / A | — | todo | board |
| board | `boardVacatedDot` | code / A | — | todo | board |
| board | `boardDotLattice` | code / A | — | todo | — (video skin only) |
| board | `boardTapRipple` | code / A | — | todo | board |
| board | `boardTrailRainbow` | code / A | — | todo | board combo painter |
| board | `boardTrailStar` | svg / B2 | yes | todo | board |
| board | `boardSilhouetteBorder` | code / A | — | todo | — NOT SHIPPED (C6) |
| board | `tapeV4` | svg / C3 | yes | done | board |
| board | `tapeH4` | svg / C3 | yes | done | board |
| board | `tapeH2` | svg / C3 | yes | done | board |
| board | `tapeV3` | svg / C3 | yes | done | board |
| board | `tapeH3` | svg / C3 | yes | done | board |
| board | `tapeV2` | svg / C3 | yes | done | board |
| board | `doorW4H4` | svg / C3 | yes | done | board |
| board | `doorW4H8` | svg / C3 | yes | done | board |
| board | `doorW4H12` | svg / C3 | yes | done | board |
| board | `doorW4H16` | svg / C3 | yes | done | board |
| board | `doorW4H20` | svg / C3 | yes | done | board |
| board | `doorW5H17` | svg / C3 | yes | done | board |
| board | `doorW13H4` | svg / C3 | yes | done | board |
| board | `doorW11H10` | svg / C3 | yes | done | board |
| board | `doorW22H10` | svg / C3 | yes | done | board |
| board | `lockHex` | svg / C3 | yes | done | board |
| board | `keyOnArrow` | svg / C3 | yes | done | board |
| board | `doorShards` | svg / B2 | yes | todo | board |
| board | `pipeTube` | code / A | — | todo | board |
| board | `pipeMouth` | svg / C3 | yes | done | board |
| board | `pipeCounter` | svg / C3 | yes | done | board |
| board | `pipeShards` | svg / B2 | yes | todo | board |
| board | `curtainCrate` | svg / C3 | yes | done | — NOT SHIPPED (phone Box skin wins, SPEC.md 11) |
| board | `curtainCyan` | svg / C3 | no | todo | — NOT SHIPPED (V2 skin) |
| board | `curtainBurst` | code / A | — | todo | Box break FX (reuse for boxSlab) |
| board | `elevatorPlatform` | code / A | — | todo | board (L31+ video mechanics, phone palette) |
| board | `cornerWedge` | svg / C3 | no | todo | board (only if content uses corners) |
| hud | `hudCoinPill` | swiftui / B1 | — | todo | §2.3.1 |
| hud | `iconCoin` | svg / B2 | yes | todo | §2.2.2, 2.3.1, 2.6, 2.9, 2.12 |
| hud | `iconPlusGreen` | svg / B2 | yes | todo | §1.6.19 PlusBadge |
| hud | `hudBackButton` | swiftui / B1 | — | todo | §2.3.1 |
| hud | `hudPauseButton` | swiftui / B1 | — | done | §2.3.1 |
| hud | `hudPanel` | swiftui / B1 | — | todo | §2.3.1 |
| hud | `hudLevelTab` | swiftui / B1 | — | todo | §2.3.1 |
| hud | `hudHardRibbon` | swiftui / B1 | — | todo | — NOT SHIPPED (no Hard tag in the v552 HUD) |
| hud | `hudTimerPill` | swiftui / B1 | — | todo | §2.3.1 |
| hud | `iconStopwatch` | svg / B2 | yes | todo | §2.3.1, 2.9 |
| hud | `iconStopwatchSmall` | svg / B2 | yes | todo | §1.6.15 TimerChip |
| hud | `heartHUD` | svg / B2 | yes | done | §2.3.1 |
| hud | `heartHUDLost` | svg / B2 | yes | todo | §2.3.1 (the empty well) |
| fx | `heartHUDHalves` | svg / B2 | yes | todo | §2.3.5 heart break FX |
| boosters | `boosterButton` | swiftui / B1 | — | todo | §2.3.2 |
| boosters | `boosterBadge` | swiftui / B1 | — | todo | §2.3.2 |
| boosters | `boosterBar` | swiftui / B1 | — | todo | — NOT SHIPPED (4-slot video bar) |
| boosters | `boosterFreeze` | 3d / B3 | yes | todo | §2.3.2-2.3.3, 2.10, 2.12 |
| boosters | `boosterHint` | 3d / B3 | yes | todo | §2.3.2, 2.10, 2.11, 2.12 |
| boosters | `boosterPointer` | 3d / B3 | yes | todo | — NOT SHIPPED (video only) |
| boosters | `boosterDome` | 3d / B3 | yes | todo | — NOT SHIPPED (video only) |
| popups | `panelFrame` | swiftui / B1 | — | todo | §1.6.4 |
| popups | `panelRibbon` | swiftui / B1 | — | todo | §1.6.5 |
| popups | `panelCream` | swiftui / B1 | — | todo | §1.6.6 |
| popups | `panelClose` | swiftui / B1 | — | todo | §1.6.3 |
| popups | `buttonGreen` | swiftui / B1 | — | done | §1.6.2 |
| popups | `buttonRed` | swiftui / B1 | — | done | §1.6.2 |
| popups | `buttonPurple` | swiftui / B1 | — | todo | §2.2.5 |
| popups | `toggleOnOff` | swiftui / B1 | — | todo | §1.6.13 |
| popups | `glyphSound` | svg / B2 | yes | todo | §2.4, 2.13 |
| popups | `glyphHaptic` | svg / B2 | yes | todo | §2.4, 2.13 |
| profile-shop-settings | `glyphMusic` | svg / B2 | yes | todo | §2.13 |
| popups | `streakChips` | swiftui / B1 | — | todo | §1.6.16 |
| popups | `stopwatchBig` | 3d / B3 | yes | todo | §2.6.1 |
| popups | `heartBroken` | 3d / B3 | yes | todo | §2.5, 2.6, 2.16 info |
| popups | `coinStackReward` | 3d / B3 | yes | todo | §2.7.2 |
| fx | `sparkleTwinkle` | svg / B2 | yes | todo | §2.2.7, 2.8 |
| popups | `heartInfinite` | 3d / B3 | yes | todo | §2.11 |
| popups | `heartInfiniteSmall` | svg / B2 | yes | todo | §2.2.2 (∞ lives), 2.12, 2.17 |
| popups | `unlockCard` | swiftui / B1 | — | todo | §2.8 |
| popups | `unlockIconPipe` | svg / B2 | yes | todo | §2.8 |
| popups | `unlockIconLinked` | svg / B2 | yes | todo | §2.8 |
| popups | `unlockIconCurtain` | svg / B2 | yes | todo | — replaced by unlockIconBox (MISSING) |
| popups | `unlockIconElevator` | svg / B2 | yes | todo | §2.8 |
| popups | `unlockIconDoor` | svg / B2 | yes | todo | §2.8 |
| popups | `tutorialHand` | svg / B2 | yes | todo | §2.3.6 |
| popups | `pointerArrowYellow` | svg / B2 | yes | todo | §2.15.6-7, 2.16, 2.17 (also at 72 × 97) |
| popups | `infoPathIcon` | svg / B2 | yes | todo | §2.15.6, 2.16, 2.17, 2.18 |
| loading-win | `wellDoneWord` | swiftui / B1 | — | todo | — NOT SHIPPED (V2 skin) |
| fx | `fxConfetti` | code / A | — | todo | §2.7.1 |
| fx | `fxFireworkStreak` | code / A | — | todo | §2.7.1 |
| fx | `fxCoinFly` | code / A | — | todo | §2.2.7 |
| fx | `fxKeyFlight` | code / A | — | todo | board |
| home | `homeBackdrop` | 3d / C1 | yes | todo | §2.2.1 |
| home | `homeConsole` | 3d / C1 | yes | todo | §2.2.1 |
| home | `homeCapsuleMachine` | 3d / C1 | yes | todo | §2.2.1 |
| home | `homeArrowPileFull` | 3d / C2 | yes | todo | §2.2.1, 2.2.8 |
| home | `homeArrowPileHalf` | 3d / C2 | yes | todo | §2.2.8 |
| home | `homeArrowPileLow` | 3d / C2 | yes | todo | §2.2.8 |
| home | `homePlatform` | 3d / C1 | yes | todo | §2.2.1 |
| home | `homeLevelPlate` | swiftui / B1 | — | todo | §2.2.5 |
| home | `homePlayButton` | swiftui / B1 | — | todo | §2.2.5 |
| home | `homeTopBar` | swiftui / B1 | — | todo | §2.2.2 |
| home | `glyphGear` | svg / B2 | yes | todo | §2.2.2 |
| home | `heartLives` | svg / B2 | yes | todo | §2.2.2 |
| home | `homeClawBar` | swiftui / B1 | — | todo | §2.2.3 |
| home | `iconHexArrow` | svg / B2 | yes | todo | §2.2.3, 2.6.3, 2.14, 2.19 |
| home | `badgeMultiplier` | swiftui / B1 | — | todo | §2.2.3 |
| home | `eventBadgeStreak` | 3d / B3 | yes | todo | §2.2.4 |
| home | `eventBadgeSkyJump` | 3d / B3 | yes | todo | §2.2.4 |
| home | `eventBadgeRocket` | 3d / B3 | yes | todo | §2.2.4 |
| home | `badgeJoin` | swiftui / B1 | — | todo | §2.2.4 (pedestal text) |
| home | `navBar` | swiftui / B1 | — | todo | §2.2.6 |
| home | `navShop` | 3d / B3 | yes | todo | §2.2.6 |
| home | `navHome` | 3d / B3 | yes | todo | §2.2.6 |
| home | `navTrophy` | 3d / B3 | yes | todo | §2.2.6 |
| characters | `scientist` | 3d / C1 | yes | wip | §2.2.1 |
| characters | `scientistLoading` | 3d / C1 | yes | todo | §2.1 (char_ld_sci) |
| characters | `workerWalkie` | 3d / C1 | no | todo | §2.2.1 |
| characters | `workerClipboard` | 3d / C1 | no | todo | §2.2.1 |
| characters | `workerCarrier` | 3d / C1 | yes | todo | §2.1 (char_ld_carrier) |
| characters | `workerRunners` | 3d / C1 | yes | todo | §2.1 (char_ld_runner / flyer) |
| characters | `workerClawPair` | 3d / C1 | yes | todo | §2.19 header |
| characters | `workerRacers` | 3d / C1 | no | todo | §2.16 header |
| avatars | `avatarDefault` | svg / B2 | yes | todo | §1.6.12, 2.14 |
| avatars | `avatarGreen` | 3d / C1 | no | todo | — NOT SHIPPED (V2 arrow-mascot set) |
| avatars | `avatarRed` | 3d / C1 | no | todo | — NOT SHIPPED (V2 set) |
| avatars | `avatarCap` | 3d / C1 | no | todo | — NOT SHIPPED (V2 set) |
| avatars | `avatarBlue` | 3d / C1 | no | todo | — NOT SHIPPED (V2 set) |
| avatars | `avatarPoint` | 3d / C1 | no | todo | — NOT SHIPPED (V2 set) |
| avatars | `avatarSpecs` | 3d / C1 | no | todo | — NOT SHIPPED (V2 set) |
| avatars | `avatarShades` | 3d / C1 | no | todo | — NOT SHIPPED (V2 set) |
| avatars | `avatarPink` | 3d / C1 | no | todo | — NOT SHIPPED (V2 set) |
| events-streak | `streakRaceLogo` | swiftui / B1 | — | todo | §2.7.3, 2.16 |
| events-streak | `iconCheckeredFlag` | svg / B2 | yes | todo | §2.7.3, 2.16 logo |
| events-streak | `streakBanner` | swiftui / B1 | — | todo | §2.7.3 |
| events-streak | `rankRow` | swiftui / B1 | — | todo | §1.6.11 |
| events-streak | `rankBadgeGold` | svg / B2 | yes | todo | §2.15.4, 2.16 |
| events-streak | `rankBadgeSilver` | svg / B2 | yes | todo | §2.15.4, 2.16 |
| events-streak | `rankBadgeBronze` | svg / B2 | yes | todo | §2.15.4, 2.16 |
| events-streak | `rankBadgePlain` | svg / B2 | yes | todo | — not used (ranks 4+ are plain text) |
| events-streak | `avatarFrame` | swiftui / B1 | — | todo | §1.6.12 |
| events-streak | `coinBowl` | 3d / B3 | yes | todo | §2.15.3, 2.16, 2.17 |
| events-streak | `scoreChip` | svg / B2 | yes | todo | §2.16 |
| events-claw | `clawHeaderArt` | 3d / C1 | yes | todo | §2.19 |
| events-claw | `clawLogo` | swiftui / B1 | — | todo | §2.19 |
| events-claw | `clawChevronChips` | swiftui / B1 | — | todo | §1.6.17 |
| events-claw | `clawLadderNode` | swiftui / B1 | — | todo | §2.19 |
| events-claw | `clawRewardCard` | swiftui / B1 | — | todo | §2.19 |
| events-claw | `sunburstRays` | svg / B2 | yes | todo | §1.6.6, 2.19 |
| events-claw | `padlockGold` | 3d / B3 | yes | todo | §2.19 |
| events-claw | `coinPileSmall` | 3d / B3 | yes | todo | §2.2.7, 2.11, 2.15 |
| events-skyjump | `skyJumpLogo` | swiftui / B1 | — | todo | §2.18 |
| events-skyjump | `skyJumpBackdrop` | 3d / C1 | yes | todo | §2.18 |
| events-skyjump | `skyJumpPad` | 3d / C1 | yes | todo | §2.18 |
| events-skyjump | `skyJumpIsland` | 3d / C1 | yes | todo | §2.18 |
| events-skyjump | `skyJumpIslandFar` | 3d / C1 | yes | todo | §2.18 |
| events-skyjump | `prizeSign` | svg / B2 | yes | todo | §2.18 (live text on the face) |
| events-skyjump | `stageChestGreen` | 3d / B3 | yes | todo | §2.18 |
| events-skyjump | `stageChestBlue` | 3d / B3 | yes | todo | §2.18, 2.17.3 |
| events-skyjump | `stageChestPink` | 3d / B3 | yes | todo | §2.18 |
| events-skyjump | `skyJumpPopupScene` | 3d / C1 | yes | todo | §2.18 |
| events-rocket | `rocketRaceLogo` | swiftui / B1 | — | todo | §2.17 |
| events-rocket | `rocketRaceBackdrop` | 3d / C1 | yes | todo | §2.17.3 |
| events-rocket | `rocketMine` | 3d / B3 | yes | todo | §2.17, 2.14 stat |
| events-rocket | `rocketOther` | 3d / B3 | yes | todo | §2.17 |
| events-rocket | `raceLane` | swiftui / B1 | — | todo | §2.17.3 |
| events-rocket | `raceBar` | swiftui / B1 | — | todo | §2.7.4 |
| leaderboard | `leaderboardTabs` | swiftui / B1 | — | todo | §1.6.10 |
| leaderboard | `leaderboardPodium` | 3d / C1 | yes | todo | §2.15.3, 2.15.6 |
| leaderboard | `trophyCup` | 3d / B3 | yes | todo | §2.15.6 |
| leaderboard | `countryFlag` | code / B1 | — | todo | — not shown on v552 (text country name only) |
| leaderboard | `weeklyContestPopup` | swiftui / B1 | — | todo | §2.15.6 (overlay, not a panel) |
| profile-shop-settings | `profileEdit` | swiftui / B1 | — | todo | §2.14.2 |
| profile-shop-settings | `profileCard` | swiftui / B1 | — | todo | §2.14.1 |
| profile-shop-settings | `iconPencil` | svg / B2 | yes | todo | §2.14 |
| profile-shop-settings | `shopOfferCard` | swiftui / B1 | — | todo | §2.12.2 |
| profile-shop-settings | `coinPackTiny` | 3d / B3 | yes | todo | §2.12 coin tile 1 |
| profile-shop-settings | `coinPackSmall` | 3d / B3 | yes | todo | §2.12 tile 2 |
| profile-shop-settings | `coinPackMedium` | 3d / B3 | yes | todo | §2.12 tile 3 + Special Offer |
| profile-shop-settings | `coinPackBig` | 3d / B3 | yes | todo | §2.12 tile 4 |
| profile-shop-settings | `coinPackSuper` | 3d / B3 | yes | todo | §2.12 tile 5 |
| profile-shop-settings | `coinPackGiant` | 3d / B3 | yes | todo | §2.12 tile 6 |
| profile-shop-settings | `badgeDiscount` | swiftui / B1 | — | todo | §2.12 seal (see shopSeal) |
| profile-shop-settings | `settingsRoundToggle` | swiftui / B1 | — | todo | §1.6.14 (square, not round, on v552) |
| profile-shop-settings | `glyphBell` | svg / B2 | yes | todo | §2.13 |
| loading-win | `logoArrowOut` | svg / B2 | yes | todo | §2.1, 2.7.1 |
| loading-win | `loadingBackdrop` | 3d / C1 | yes | todo | §2.1 |
| loading-win | `arrowGlossyYellow` | 3d / C2 | yes | todo | §2.2.8 falling arrows |
| loading-win | `arrowGlossyRed` | 3d / C2 | yes | todo | §2.2.8 |
| loading-win | `arrowGlossyBlue` | 3d / C2 | yes | todo | §2.2.8 |
| loading-win | `arrowGlossyGreen` | 3d / C2 | yes | todo | §2.2.8 |
| loading-win | `arrowGlossyPurple` | 3d / C2 | yes | todo | §2.2.8 |
| loading-win | `arrowGlossyOrange` | 3d / C2 | yes | todo | §2.2.8 |
| loading-win | `arrowGlossyCyan` | 3d / C2 | yes | todo | §2.2.8 |
| app-icon | `appIcon` | 3d / C2 | yes | todo | app icon |
| profile-shop-settings | `statFirstTryIcon` | svg / B2 | yes | todo | §2.14.1 |
| profile-shop-settings | `statWeeklyWinsIcon` | svg / B2 | yes | todo | §2.14.1 |
| avatars | `avatarParty` | 3d / C1 | yes | todo | §2.14.2 index 6 |
| avatars | `avatarBoxHead` | 3d / C1 | yes | todo | §2.14.2 index 7 |
| avatars | `avatarDetective` | 3d / C1 | yes | todo | §2.14.2 index 3 |
| avatars | `avatarCapGlasses` | 3d / C1 | yes | todo | §2.14.2 index 2 |
| avatars | `avatarScientist` | 3d / C1 | yes | todo | §2.14.2 index 5 |
| avatars | `avatarWalkie` | 3d / C1 | yes | todo | §2.14.2 index 1 |

MANIFEST statuses lag the disk (art round 1 finished after ID-MAP.md was generated): the art director merges them. **Avatars**: the v552
set is on disk as `art/out/char_avatar{Walkie,CapGlasses,Detective,Burger,Scientist,Party,BoxHead,Notebook}@3x.png` (192 × 192 px, the art
lane renamed them at 08:43-08:49); the MANIFEST lacks `avatarBurger` and `avatarNotebook` (add them) and its V2-set entries are not shipped
(§4.4). Index order: §2.14.2.

### 4.2 Graphics this spec needs that the MANIFEST lacks (for the art lanes)
| proposed id | route | size pt | what / where | ref (look only) |
|---|---|---|---|---|
| `unlockIconBox` | B2 | 124 × 112 | the phone's Box unlock icon: purple slab + silver counter ring "5" (§2.8) | 134 |
| `boxSlab` | C3 (or code: a 9-slice) | per box W × H cells | the phone's Box obstacle (§4.3) | 135, meta-062 |
| `boxRing` | C3 | 2.2 × 2.2 pitch | the silver counter ring with 4 diagonal stubs, purple inner ring, navy well (digits live) | 135 |
| `iconStopwatchFrozen` | B2 | 31 × 33 | iced HUD stopwatch (snow cap, frosted face, icicles) (§2.3.3) | meta-065 |
| `fxFrostVignette` + `frostCracks` | A + B2 | full screen / 120 × 120 corner tile | freeze vignette gradient + white ice-crack lines (§2.3.3) | meta-065 |
| `heartBig` | B3 | 185 × 155 | whole glossy red heart for Out of Lives! (+ its red glow) (§2.6.2) | meta-088 |
| `heartLivesBig` | B2 | 96 × 86 | the lives heart at popup size, count live (§2.9) | meta-095 |
| `iconVideoAd` | B2 | 36 × 37 | video clapper for rewarded-ad buttons (§2.9) | meta-095 |
| `iconCheck` | B2 | 54 × 46 | big green check (Claw done cards, Sky Jump won stage, Edit Profile selection badge at 40 × 33) | meta-039, 096, meta-003 |
| `iconSkull` | B2 | 24 × 24 | skull each side of the "Hard Level" / "Super Hard" win tag ribbon (§2.7.2) | 037, 063 |
| `rankWings1` | B2 | 49 × 33 | gold winged rank badge "1" (race leader; digit live) (§2.7.4, 2.17) | 167, 171 |
| `rocketOfferScene` | C1 | 360 × 250 | the starry offer-panel scene (moon, chest, planets) (§2.17.1) | 163 |
| `weeklyContestLogo` | B1 (EventLogo) | 277 × 50 | "Weekly Contest" lettering (§2.15.3) | meta-013 |
| `iconFlagRoll` | B3 | 36 × 41 | the green flag roll (Streak score chip left part, Profile "Streak Race Wins") | meta-045, meta-002 |
| `iconSkyDrum` | B3 | 57 × 52 | the pink drum (Profile "Sky Jump Wins"; the Sky Jump badge art alone) | meta-002 |
| `bundleBag`, `bundleChestRed`, `bundleChestPurple`, `bundleSafe`, `bundleCart` | B3 | 128 × 94 each | Shop bundle art (Mini, Epic, Elite, Mega, Legendary) (§2.12.2) | meta-008..011 |
| `shopSeal` | B2 | 53 × 52 | red scalloped "90% OFF" seal (text live) | meta-012 |
| `pageBgPattern` | B2 | 64 × 64 tile | faint rotated-arrow pattern of the navy page ground | meta-029 |
| `pointerArrowYellow` @ 72 × 97 | B2 | 72 × 97 | the Weekly tutorial's big arrow (render the SVG at this size, not upscaled) | 130 |
Not art (SwiftUI/code, SHELL): PageHeader, SegmentTabs, JumpPill, SquareToggle + red slash, the shop sash, the race-bar chequered strip, toast.

### 4.3 The phone's Box obstacle (PENDING-ui "box sprites/slices", with UI-ART; VERIFIED 135 at pitch 28.07, meta-062 at 14.05)
Covers its cell block exactly (L50: 10 × 3 cells = 280.6 × 83.7 pt). Slab (drawn at 32 pt/cell, scaled by pitch/32): corner radius **0.40
pitch**; face **#BC5BF6**; top bevel 0.04 pitch #E89FF4 → #ECB2F3 (a light line) → face; left/right edges darken over 0.26 pitch from
#5935A2 at the edge to the face; bottom lip 0.28 pitch #AB50EB → #582D96 → #4F2F83; a soft grey shadow 0.1 pitch below; four rivets (domes
⌀0.30 pitch, lighter lilac highlight / darker purple shade, INFERRED colours) inset 0.35 pitch from each corner. Counter ring `boxRing` ⌀2.2 pitch centred on the block
(for blocks < 2.5 cells on a side: scale to 0.85 × the short side): silver sphere (#E5F2FB lit top-left → #48498C lower right) with four
stub cylinders on the diagonals, a purple ring (#5D46AE → #C698FF) around a navy well (#142C6A → #1F3C80) holding the live counter (white
face, purple outline #4B1F86, 0.8 pitch) — ring colours from STYLE §A.2's crate ring, which the phone's Box ring matches by eye (INFERRED). Break: shards (motion §5.4). 9-slice for a bitmap route: insets 0.5 pitch on every side
(corners + rivets), stretch the middle.

### 4.4 Not shipped (MANIFEST entries the v552 look does not use)
`boardSilhouetteBorder`, `boardDotLattice`, `curtainCrate`, `curtainCyan`, `unlockIconCurtain`, `hudHardRibbon`, `boosterBar`,
`boosterPointer`, `boosterDome`, `wellDoneWord`, `avatarGreen … avatarPink` (V2 set), `rankBadgePlain`, `countryFlag`. They stay in the
MANIFEST with `confirmed: false`; no build agent references them.

---

## 5 Tuning: `Tuning/ui.json` values for every `_pending` key (SHELL copies them; SPEC-motion-audio may retune times)
| key | value | § |
|---|---|---|
| `loading.minSeconds` | 1.5 (unchanged) | 2.1 |
| `loading.capSeconds` | 4.0, the first-launch alert excluded | 2.1 |
| `loading.dotsPeriod` | 0.4 (unchanged; ".", "..", "..." cycle, the word fixed) | 2.1 |
| `transition.loadingToBoard` | 0.13 (0.10-0.16 VERIFIED) | 1.8 |
| `transition.loadingToHome` | **0.16** (was 0.3) | 1.8 |
| `transition.homeTabs` | 0 | 1.8 |
| `toast` | `{hold 2.0, in 0.08, out 0.27, homeY 390, panelY 110, plate "#0B2176", plateAlpha 0.92, radius 16, border "#00B4FF", borderWidth 1.5, text 18, maxWidth 330}` | 2.20 |
| `frames.settings.*` | **replace** with the page layout: `header`, `close [325.9,44.4,59.1,58.7]` (disc centre 347.7,71.5), `notifCard [19.0,134.1,355.3,95.7]`, `bell [44.0,164.5,30.7,38.4]`, `notifToggle [234.9,161.1,122.8,41.7]`, `audioCard [19.0,248.5,355.3,152.5]`, `sound [58.0,312.3,66.1,65.7]`, `music [162.1,311.9,65.7,65.7]`, `haptic [266.9,311.6,66.1,65.7]`, `support [102.8,438.4,188.8,77.4]`, `supportFrame [93.7,433.0,206.2,94.4]`, `terms [53.0,552.1,121.8,49.0]`, `privacy [218.5,552.1,121.8,49.0]`; drop `layout.settingsRows`, `layout.rowPitch`, `layout.firstRowOffset`, `layout.settingsIcon`, `layout.settingsToggle`, `layout.settingsLabelLeft`, `layout.linkGap` | 2.13 |
| `frames.quit.*` | **replace** with the band: `band [0,234.2,393,405.0]`, `ribbon [60.1,193.5,274.2,90.4]`, `close` disc centre (362.3,241.2) ⌀45, `message` baseline 344.0, `heart [133.8,359.3,122.8,97.4]`, `quit [91.1,499.4,211.2,86.4]`, `quitFrame [79.7,490.7,233.9,106.4]` | 2.5 |
| `text.pause.toggleOff` | size 21, tracking −0.75, fill ["#FEF6E2"], outline "#093896", outlineWidth 1.0, drop 1.0 | 1.6.13 |
| `colors.toggle.offTrack` / `offKnob` | "#1031A9" / "#009BFD" | 1.6.13 |
| `text.settings.link` | Terms/Privacy: 22.3 / 0, fill ["#FFFFFF"], outline "#093896", 1.1, drop 1.2 | 2.13 |
| `text.home.levelNumberHard` / `…SuperHard` | as already in ui.json (outline #650000 / #430080) — confirmed | 2.2.5 |
| `colors.home.plateHard` / `plateSuperHard` | "#C2090E" / "#7400B6" | 2.2.5 |
| `colors.home.ribbonHard` / `ribbonSuperHard` | tab faces "#D5221B" / "#8D0DD2" (median of the tab body, VERIFIED 035 / 060); text face "#FFFBE6" | 2.2.5 |
| `colors.home.base` | "#7D8BC3" (mean colour of our `homeBackdrop` render; shown only if the art is late) | 2.2.1 |
| `colors.loading.base` | "#ABA0D8" (mean colour of our `loadingBackdrop` render; also the launch-screen colour, §1.8) | 2.1 |
| `text.loading.label` | fill ["#FFFFFF"], outline "#82251F" (correction C3) | 2.1 |
| `puppet` | placements from rig.json (§2.2.1); loops = SPEC-motion-audio | 2.2.1 |
| `settings.links` | true (Support, Terms, Privacy open the offline pages) | 2.13.1 |
| `frames.home.scene.*` | `platform [0,576,393,182]`, `console [95,266,214,109]`, `capsuleMachine [95,365,206,215]`, `arrowPile [104,402,186,126]` (scene lane) | 2.2.1 |
| `fx.sparkles` | unchanged (count 7, radius 22, 0.7 s, size 9, colours #FFFFFF #FFF6B0 #FFE14A) — geometry only; SPEC-motion-audio owns the motion | 2.2.7 |
| NEW `dim.info` / `dim.weeklyTutorial` / `dim.overPage` | 0.95 / 0.92 / 0.63 | 1.3 |
| NEW `ribbon.maxSize` / `ribbon.box` | 49 / 228 | 1.4 |
| NEW `text.minScale` | 0.70 | 1.4 |
| NEW `lb.countryShort` | `{"US":["USA","ABD"],"GB":["UK","İngiltere"],"AE":["UAE","BAE"],"CD":["DR Congo","KDC"],"CF":["C. African Rep.","OAC"],"BA":["Bosnia","Bosna"],"TT":["Trinidad","Trinidad"],"KN":["St Kitts","St. Kitts"],"VC":["St Vincent","St. Vincent"],"DO":["Dominican Rep.","Dominik C."]}` (extend as SPEC-social's country table needs) | 2.15.1 |
| NEW `shop.fakePrices` | USD `{offer 0.99, mini 4.99, epic 9.99, elite 19.99, mega 49.99, legendary 99.99, coins [1.99,7.99,14.99,29.99,54.99,99.99]}` (SPEC-gameplay may override) | 2.12.3 |
All frames/texts of the new screens are in `design/ui-tokens-2.json` `components` / `textStyles` (ids = the `id` column of each table).

---

## 6 Accessibility identifiers (additions to arch §9.8; VERIFY relies on them)
- Pages: `page.profile`, `page.settings`, `page.shop`, `page.leaderboard`, `page.streakRace`, `page.claw`, `page.rocketRace`,
  `page.skyJump`, `page.support`, `page.terms`, `page.privacy`, each with `.close` where it has an X.
- Settings: `settings.toggle.sound|music|haptic|notifications` (value on/off), `settings.support`, `settings.terms`, `settings.privacy`.
- Profile: `profile.avatar`, `profile.name` (label), `profile.level` (value), `profile.edit`, `profile.stat.firstTry|weekly|streak|rocket|sky|claw`
  (value), `editProfile.name`, `editProfile.avatar.<0-8>` (value `"selected"`), `editProfile.save`, `username.field`, `username.continue`.
- Shop: `shop.product.<id>` (value = price text), `shop.testStoreNote`, `shop.section.offers|bundles|coins`.
- Leaderboard: `leaderboard.tab.weekly|world|country` (value selected), `leaderboard.row.<rank>`, `leaderboard.me` (value rank),
  `leaderboard.jump` (label Top/Bottom), `leaderboard.locked`, `weekly.info`, `weekly.tutorial.card`.
- Level: `hud.booster.freeze|hint` (value `"stock:n|empty|active"`), `hud.freeze.remaining` (value seconds), `hud.heart.<1-3>` (value full/lost).
- Popups: `popup.moreLives` (+ `.refill`, `.ad`), `popup.boosterBuy.<id>` (+ `.shop`), `popup.outOfLives` (+ `.primary`), `popup.continue`
  (value streak|token|life), `claim.tap`, `toast`.
- Events: `event.streakRace.row.<rank>`, `event.rocketRace.lane.<0-4>` (value n/5), `event.skyJump.players` (value), `event.claw.step.<n>`
  (value locked|next|done).

---

## 7 Open items, owner questions, clips that would settle DECISIONs
| # | item | current DECISION | settles it |
|---|---|---|---|
| 1 | Loading → home transition and Loading's minimum on a returning launch | 0.16 s cross-fade, ≥ 1.5 s | a cold-launch clip on the phone (Loading → home), no alert |
| 2 | home tab transition | hard cut | a 60 Hz clip tapping Shop → Home → Leaderboard |
| 3 | arrow-pile refill trigger and timing | on home re-entry from an event page, 1.2 s | a clip of X on the Streak Race page → home |
| 4 | booster at 0 stock | green "+" badge → booster info popup → Shop | spend the phone's last hourglass (costs a booster; owner's call) |
| 5 | not enough coins on Play On | Shop page over the offer | a phone state with < 900 coins (not available: 4214) |
| 6 | Weekly / Streak Race / Rocket win / Sky Jump fail result screens | §2.15.8, 2.16, 2.17.3, 2.18 | the phone at the Monday / 10:00 TRT boundaries (SPEC-social §11) |
| 7 | Support without an e-mail address | offline Help page; `Brand.supportEmail` nil | owner: give an address if a contact button is wanted |
| 8 | FakeStore prices in USD on a TR device | "$0.99" style | owner: prefer TL look-alike prices? (they would look real — we chose honest) |
| 9 | Music toggle (inert on v552) | ours toggles a setting; no music ships unless SPEC-motion-audio adds some | owner |
| 11 | ranking list sizes (C7) | UI renders any length | SPEC-social (phone: Streak 50, Weekly 10 visible) |

---

## 8 Files of this pass
- `design/SPEC-ui.md` (this file), `design/ui-tokens-2.json` (new ids only; `ui-tokens.json` untouched).
- `design/ui-crops/<screen>/*.png`: new folders `profile`, `editProfile`, `settings`, `moreLives`, `quitLevel`, `outOfLives`,
  `continueToken`, `shop`, `lb`, `wkInfo`, `wkTut`, `streak`, `streakInfo`, `clawLadder`, `rocketOffer`, `rocket`, `rocketLost`, `raceBar`,
  `hudFreeze`, `hudHearts`, `homeInf`, `homeLives`, `homePayout`, `claimBulb` (references to look at only).
- `design/ui-crops/_tools/`: `m_meta1.py … m_meta6.py` (measurement specs), `mfit.py` (panel fit helper), `dump.py`, `strings_fit.py`,
  `build_tokens2.py`, `tokens2_curated.json`, `out/meta1..6.json`, `out/strings_fit.{json,md}`.
