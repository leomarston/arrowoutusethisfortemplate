# Arrow Out — UI measurements (start of SPEC-ui)

Role: UI MEASUREMENT, 2026-09-25. Machine-readable twin: `design/ui-tokens.json` (same numbers; engineers reference ids like `hud.timerPill`, `pause.resume`, `text.hud.levelTab.label`, `grad.pause.ribbon`, `dim.popup`). Reference crops: `design/ui-crops/<screen>/<component>.png` (references to LOOK at only — never assets). Tools: `design/ui-crops/_tools/` (re-run: `python3 m_hud.py; python3 m_home.py; python3 m_popups.py; python3 m_events.py; python3 m_extra.py; python3 build_tokens.py; python3 gen_md.py`).

**Name.** The owner renamed the game to **"Arrow Out"** (2026-09-25: "just change the name when we use the name ... keep everything and all the designs same"). Every place the original shows its "MAZE OUT!" lettering (loading logo `loading.logo`, win celebration `celebrate.logo`, iOS prompts) is a slot for OUR "ARROW OUT!" logo at the same frame; everything else here is copied 1:1. The owner also asked for different character colours (background workers blue or red, the top scientist pink): that touches character art only — no UI token below changes, except that avatar tiles/portraits that show the workers (`skyMatch.avatars`, `skyWin.winners`, race avatars) will show our recoloured characters.

## How to read the numbers

- **Source**: the lossless runner shots `research/shots/NNN-*.png` (1178 × 2556 px, the owner's iPhone 15) and `research/kickoff/state.png` (Loading). **pt = px × 393 / 1178** (1 px = 0.334 pt). Never video frames. The only other source is store screenshot 6 for the Streak Race panel the phone never opened (section "race", pt = px × 393 / 1320, positions INSIDE the panel only).
- **frame** = `x · y · w · h` in pt from the top-left of the 393 × 852 pt canvas, to the outer visible edge of the component (antialiased edge at 50 %, ±1 px = ±0.35 pt). Soft drop shadows are NOT in the frame (they are in `shadow`). Frames were found by colour predicates seeded inside the component (`measure.py`), then checked on overlay sheets.
- **shape**: fitted on the mask outline (`mlib.fit_corners`) — "rounded r" = circular-corner rounded rect; "superellipse n" = |x/a|^n + |y/b|^n = 1 over the whole component (art/STYLE.md §B.1: the glossy buttons are superellipses, square HUD n 3.5, wide n 4.0); "circle ⌀" = full round. When one end is covered (coin pill under the coin), the fit uses the free corner only.
- **fills**: 7 × 7 px median samples of solid interiors (names say where). **grad** = vertical profile down one clean column, simplified to ≤ 12 stops (Douglas-Peucker, 6/255 RGB tolerance): `[position 0..1 of the frame height, hex]` — full stops in the JSON. **xsec** = cross-section from OUTSIDE the component inwards (positions in pt) = the bevel/border layering.
- **text**: `“label” size/tracking` in pt for PC Display (= Nunito wght 1000, `PCDisplay-Black`, design/fonts.md). `[fonts.md]` = the value is fonts.md §5/§6 (rendered line-IoU fit of the shipped font; authoritative), otherwise this role's glyph-match fit (`mlib.fit_text_glyphs`: per-glyph ink height vs CoreText glyph ink → size; ink span → tracking; calibrated on fonts.md; over 32 labels both measured the mean |Δsize| is 1.3 %, max 5.7 %). fill = face gradient top→bottom; outl = outline colour + width (stroke drawn OUTSIDE the full-weight glyph); drop = the outline shape moved straight down, same colour, blur 0 (fonts.md §6).
- **anchor**: which screen edge the component sits against and its offset from the iPhone 15 safe area (top inset 59 pt, bottom 34 pt). The offsets are VERIFIED; the anchoring RULE is INFERRED (one device class captured). The original hides the iOS status bar in every captured screen and draws into the full 852 pt (the HUD coin pill at y 30 sits beside the Dynamic Island). "centre ±" = offset of the component centre from the screen centre (426 pt) for popup content.
- **VERIFIED** unless marked INFERRED: every frame/colour/size was measured on the shot named in the row.

## Global tokens

### Dim overlays (behind popups)

| token | colour | alpha | measured (fit per popup) | note |
|---|---|---|---|---|
| `dim.popup` | #000000 | **0.90** | pause 0.890, continue 0.894, failed 0.894, win 0.894, celebrate 0.894, claim 0.901, skyJump 0.901 | least-squares fit dimmed = (1-a)*clean + a*black over unchanged board pixels; 0.890-0.901 across 7 popups (STYLE §D scrim #1C1C1C over white = 0.89): use 0.90 |
| `dim.unlock` | #000000 | **0.90** | unlock 0.902, clawInfo 0.902 |  |
| `dim.outOfTime` | #000000 | **0.94** | outOfTime 0.941 | darker than the other popups (0.941, rms 0.23), plus the blue glow behind the stopwatch |
| `dim.skyMatch` | #000000 | **0.96** | skyMatch 0.960, skyTut 0.956 | Sky Jump matching + tutorial overlays (0.960 / 0.956) |

Method: `dimmed = (1 − a)·clean + a·colour` least-squares over pixels that are unchanged under the dim (the same board before/after); rms 0.16–0.28/255 → the dim is a flat black layer, no blur, no vignette (except the Out of Time glow, below).

### Core palette (role colours; every entry is a named sample in the JSON `colors`)

| token | hex | source |
|---|---|---|
| `board.ground` | #FFFFFF | STYLE §D, 003 |
| `board.ink` | #000000 | STYLE §D |
| `board.vacatedDot` | #C5E1FF | STYLE §D, 004 |
| `hud.panel.fill` | #BDDCFF | 003 (760,335) |
| `hud.coinPill.fill` | #BDDCFF | 003 |
| `hud.coinDigits` | #3861AC | fonts.md / 003 |
| `hud.timerPill.fill` | #6C94DC | 003 (540,300) = vgrad plateau |
| `button.blue.face` | #008CFE | 003 |
| `button.blue.glyph` | #E9FFFD | 003 |
| `button.red.face` | #EC0911 | 036 |
| `button.purple.face` | #9100E4 | 061 |
| `button.green.face` | #00D300 | 026 |
| `button.green.outline` | #0A3C00 | STYLE §B.1 / 007 profile |
| `button.red.outline` | #5A0006 | STYLE §B.1 |
| `tab.blue.fill` | #008EFE | 003 |
| `tab.red.fill` | #FF3C3D | 036 |
| `tab.purple.fill` | #A628E7 | 061 |
| `heart.face` | #FB3A2A | 003 |
| `panel.frame.blue` | #005DEC | 007 |
| `panel.field.blue` | #226DF5 | 007 |
| `panel.groove.blue` | #153CC1 | 007 |
| `panel.bumper.blue` | #00B4FF | 007 |
| `panel.rivet.blue` | #4CA9EF | 007 |
| `panel.frame.red` | #9E0014 | 037 |
| `panel.field.red` | #CC0410 | 037 |
| `panel.frame.purple` | #7306BA | 063 |
| `panel.field.purple` | #8F01DE | 063 |
| `panel.frame.skyPurple` | #5F3AD5 | 065 |
| `card.cream.fill` | #F8E7D2 | 007 |
| `card.cream.border` | #D0987D | 007 |
| `text.brown` | #622100 | fonts.md plain labels |
| `text.navy` | #093896 | fonts.md home top bar |
| `ribbon.yellow.top` | #FFCF00 | 007 |
| `ribbon.yellow.bottom` | #FFBD00 | 007 |
| `toggle.green` | #00E500 | 007 |
| `toggle.knob.blue` | #009EFC | 007 |
| `close.red` | #FF2D2E | 007 |
| `close.glyph` | #FFE9E9 | 007 |
| `topPill.fill` | #DEEEFF | STYLE §D, 002 (590,200) |
| `nav.blue` | #0592FE | STYLE §D |
| `nav.homeTab` | #11D5FF | STYLE §D |
| `booster.green.face` | #00E400 | 003 |
| `booster.badge.red` | #FF4344 | 003 |
| `booster.tray.fill` | #BDDCFF | 003 |
| `dim` | #000000 | alpha 0.90 (popups) / 0.94 (Out of Time) / 0.96 (Sky Jump matching) |
| `race.row.gold` | #FFDA00 | store-6 |
| `race.row.silver` | #BAC3EB | store-6 |
| `race.row.bronze` | #F79753 | store-6 |

### Text roles (for labels not measured one by one)

| role | size / tracking pt | face | outline | drop | note |
|---|---|---|---|---|---|
| `role.popupTitle` | 49 / -0.80 | #FFFFFF | #7B1D01 1.9 | 3.1 | yellow ribbon titles (Paused, Continue?, Level N); band #FFD699 1.5 pt |
| `role.buttonLarge` | 38.9 / -0.50 | #F1FFF2 | #066A01 1.9 | 1.9 | Continue / Try Again (212 x 88 pt buttons); red: outline #650000 |
| `role.buttonPlay` | 48.8 / -3.25 | #F1FFF2 | #066A01 2.2 | 2.2 | home Play (228 x 104 pt) |
| `role.buttonSmall` | 30.5 / -0.50 | #FFFCED → #FEF9E8 → #FDF4DD | #066A01 1.4 | 1.2 | Resume/Quit (125 x 89 pt): max 30.5, shrink to fit (Resume 27.2) |
| `role.hudLabel` | 17.9 / -0.50 | #FFF9EF → #FFF4E0 → #FFEDCB | #002985 0.7 | 0.7 |  |
| `role.panelLabel` | 25.5 / +0.00 | #622100 | none | — | plain dark brown on cream (Sound, Level Failed!) |
| `role.caption` | 16 / +0.00 | #FCE7D7 | #172B5A 1 | — | event captions on the dim (white-cream face, navy outline); highlight words #FFD102 face with #580700 outline |
| `role.tapToContinue` | 20.3 / -0.77 | #FFFFFF | #3A007C 1.2 | 1.2 | Tap to Claim / Tap to Continue |
| `role.coinDigits` | 18.8 / +0.00 | #093896 | none | — | top-bar values (HUD coins #3861AC) |
| `role.bigCongrats` | 45.3 / -0.90 | #FFDD13 → #FFC302 → #FFB700 | #B24900 0.9 | 1.8 | "Congratulations!" (yellow face, orange-brown outline + extrusion) |

## Chrome layer recipes (read from the cross-sections; outside → inside)

The wide green/red buttons and the square HUD buttons already have full layer recipes in **art/STYLE.md §B.1** (measured by the art spike on centre-line profiles, implemented in `art/ui/code/GlossyChrome.swift`). The frames here agree: square button body **40.0 × 40.0 pt**, superellipse n 3.5–3.7 (STYLE: 40 × 40, n 3.5); Resume/Quit **125.1 × 89.1 pt** with the outline, n 3.9 (STYLE: 125 × 89, n 4.0). Variants measured here (clean-column gradients, JSON `grad.*`): blue/red/purple square buttons (`grad.hud.pauseButton`, `...Hard`, `...SuperHard`), green big buttons (`grad.home.playButton`, `grad.win.continue`, `grad.failed.tryAgain`, `grad.continueStreak.playOn`, `grad.skyJump.start`), red (`grad.pause.quit`, `grad.home.playButtonHard`), purple (`grad.home.playButtonSuperHard`).

- **HUD panel `hud.panel` (003)** — light-blue plate #BDDCFF, rounded r 18.3 pt (bottom-right corner fit, rms 0.25 px). Top: 1 pt edge #8CB1E6, a 1 pt white highlight #EEF6FF just inside, back to #BDDCFF within 3 pt. Bottom: a thicker 3D lip #517CC9 → #80A6E9 over ~4.3 pt. Drop shadow: offset 2.0 pt down, σ 1.33 pt, ≈ black 0.47 (grey #9DA5B4 band under the lip). The level tab overlaps the top edge (z above).
- **Coin pill `hud.coinPill` (003)** — fill #BDDCFF, rounded r 6.8 pt (free right corners). ~1 pt outline #527DC8 at the top (#8EAFE3 on the right, #89AEE5 at the bottom), inner highlight fading to the fill over ~3 pt. Digits plain #3861AC (fonts.md). The coin icon (23.7 × 24.4 pt) covers the left end.
- **Timer pill `hud.timerPill` (003)** — a RECESSED well inside the panel: fill #6C94DC; top inner shadow #89AFED → #618AD4 over the top 14 % (~3.7 pt); bottom light rim #BED5F5 → #D9EAFE (last 5 %); rounded r 9.3 pt. The stopwatch icon (29 × 33 pt) overlaps its left end.
- **Level tab `hud.levelTab` (003; red 036, purple 061)** — rounded r 4.9 pt, 94.4 × 23.0 pt, centred on the panel top edge. Blue: dark top line #072885, light band #56BCEA–#5BC7F8 (6–9 %), face #0192FF → #008AFE, bottom lip #004EE9 → #002FB2, 1 pt #09289F outline.
- **Blue popup frame `pause.panel` / `failed.panel` / `win.panel`** — whole-panel superellipse n 5.9–6.3 (fit rms 2.1–2.4 px), 370.6–373.3 pt wide. From the outside: 1 pt navy outline #122F8F · frame bar #0268E8/#0066EF ~16 pt · a dark inner-shadow band #113AA8/#0D2792 that lightens to #1C5AE6 over ~10 pt · inner field #226DF5 with a 1 pt light rim #298FF9 where it meets the card · card. Corner BUMPER pieces (lighter #00B4FF, `pause.bumperTL` 50.4 × 83.7 pt) and RIVETS (`pause.rivet`, ⌀13 pt, #4CA9EF) at the bar joints. Red (Hard) and purple (Super Hard) panels have the same layering: outline #6B000F / #3A0672, bar #9D0013 / #7A03C2, groove #5F0006 / #380163, field #CD0C15 / #9302DF (light rim #D4212B / #981BE2).
- **Cream card `pause.card` / `failed.card`** — rounded r 24.4 pt (rms 0.32 px: a true rounded rect). 1 pt navy line #192D94, then a brown→peach bevel #B16E57 → #D49E83 → #E8BBA0 over ~6 pt, a 1 pt bright line #FCF0E2, fill #F8E7D2. Labels plain #622100.
- **Yellow ribbon title `pause.ribbon` (all popups)** — 274.2 × 90.4 pt, same frame on every popup (x 60.1). It is an ARCHED banner: top edge 190.5 pt at the centre, 194.8 at x 100 and 197.8 at x 320; bottom edge 274.6 at the centre, 278.9 / 279.6 near the ends — both edges follow a circle of radius ≈ 1100 pt (sag ≈ 4.5 pt), body ≈ 84 pt thick, end corners r ≈ 27 pt (007 edge trace). Profile at x = 100 pt: 1 pt dark outline #993805, a bright highlight band #F4ED47–#FFF741 (11–14 %), face #FFD808 → #F9A600 (15–88 %), shade #D95700, bottom outline #662200. The ribbon overlaps the panel top; the close button overlaps the panel top-right corner.
- **Close button `pause.close` (all popups)** — circle ⌀45 pt (fit n 2.0, rms 0.6 px): red disc #FF2D2E with a dark-red rim, white-pink X #FFE9E9, inside a thin blue ring; same size on every popup; on the pause panel its centre (361.3, 256.7) is 20.6 pt inside the panel right edge and 27.8 pt below the panel top (fit).
- **Big green button `win.continue` / `failed.tryAgain` / `skyJump.start`** — 212.5 × 88.1 pt with the ~1 pt outline #0C3A05 (body without it 211.2 × 86.7), superellipse n 4.6–5.0. Face #02D00F/#03DF03 with the glare line #70E872 ~21 % from the top (STYLE: #91FC92 1.5 pt). Add Time / Play On are the same button 233.9 × 88.1 pt.
- **Home Play `home.playButton` + frame `home.playFrame`** — blue outer frame 228.2 × 103.8 pt (superellipse n 4.4), button 211.2 × 86.7 (n 4.7). Column x = 110 pt: blue frame #0E58C3 → #00A9FB, outline #0C3B01, face #02D90F → #13E11E, glare #72EF75 at 17.6 %, face #09E809 → #00C500, bottom outline #073733, frame #00A4F7 → #0071F3. Hard: red face, "Hard Level" ribbon 120.1 × 30 pt on its top edge; Super Hard: purple.
- **Bottom nav `home.navBar`** — top edge at y 771.7: 1 pt dark line #485881, 2 pt dark blue #003BCB, 1 pt bright line #00BFFF (+3.6 pt), then a vertical gradient #00A0FF → #137DFB (+30 pt) → #1C68F5 (+53) → #134BEF (bottom). The selected Home tab is raised 18 pt (`home.navHomeTab` 140.1 pt wide, lighter #11D5FF/#14D3FA) and its icon overhangs the tab top.
- **Claw bar `home.clawBar`** — 354.6 × 43.7 pt: light-blue frame (#0055DF edge, #7BE6FF highlight line, #08ADFA → #03A7FC ~5 pt), dark edge #003FCE, navy track #011162 → #082895; green fill (`home.clawBarFill`, rounded r 6.8) grows from the left; the hexagon icon sits on the left end, the reward on the right end, the multiplier badge hangs below-left, the timer chip hangs below-centre.
- **Booster corner `booster.trayLeft` / `booster.buttonLeft`** — tray #BDDCFF 82.7 × 81.1 pt flush with the screen edge and bottom, corner superellipse n 3.0; 1 pt edge #82A7E8, white highlight #EEF6FF; bottom lip #517CC9 → #87ACEC (~4.3 pt) and a grey shadow; a recessed well #648DD7 (~1.7 pt ring) around the green button 57.4 × 56.4 pt (superellipse n 3.3): outline #0A3800 ~1 pt, rim #127912 → #189818, face #04EA04 → #04C20D with glare #95FC95, bottom lip #007000. Red count badge ⌀24.5 pt #FF4344 bottom-right.
- **Sky Jump panel `skyJump.panel` (065)** — purple: 1 pt outline #3D18A7, bar #6540D9 → #613DD6 ~17 pt, 1 pt inner dark line #38189E; the TOP bar is lighter lilac #926FF9 → #835FFF (~22 pt) with a #5B3AD8 inner line; lighter corner bumpers and rivets like the blue panels. Frame: see `skyJump.panel` (top edge hidden by the logo: INFERRED).
- **Streak Race panel band `race.band` (store 6)** — dark line → blue top bar #1C53FF with a light line #74D9FF, bar #00B4FF (~18 pt), #1F5CFF, a dark line #0A248F, field #0C88F8 → #0781FE. Rows: gold #FFD000-family / silver-lavender / bronze-orange rounded plates (r ≈ 0 by the fit = the plates are nearly square-cornered with a thin rim; see crops).

Out of Time glow (`outOfTime.glow`, 013): a blue radial glow behind the big stopwatch — samples leftwards from the body edge at y = 377 pt: r0_edge_x280 #0C1840, x230 #0D1530, x180 #0E1220, x130 #0F1015, x80 #0F0F0F, x30 #0F0F0F, far_x30_y2300 #0B0D0F (far away the dim reads #0F0F0F).

## Screens

Columns: **frame** x · y · w · h (pt) · **shape** · **fills** (samples; grad = clean-column gradient in the JSON) · **text** (size/tracking pt, face, outline, drop) · **anchor** · **shot**.

### Loading screen — `loading`

- shots: research/kickoff/state.png
- z-order (back → front): loading.background (full-bleed art) → loading.logo → loading.label → ios.notificationAlert (system, over everything)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `loading.logo` | 20 · 66.7 · 206.8 · 160.1 | — | — | — | top: safe +7.7 | state |
| `loading.label` | 130.1 · 765.6 · 115.1 · 40 | — | — | “Loading” 26.8/-0.50 fill #CCCCCC · outl #681E1A 0.9 · drop 0.4 [fonts.md] | bottom: safe +12.4 | state |

- `loading.logo`: game logo sign, top-left, tilted slightly

### iOS system prompts (note only — not built) — `ios`

- shots: state, 039
- z-order (back → front): system UI (note only, not built)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `ios.ratingPrompt` | 153.5 · 303.6 · 221.9 · 330.3 | — | — | — | n/a | 039 |
| `ios.notificationAlert` | 36.7 · 331.9 · 320.9 · 215.2 | — | — | — | n/a | state |

- `ios.notificationAlert`: iOS system alert (note only; not built)
- `ios.ratingPrompt`: iOS SKStoreReviewController sheet (note only)

### Home — `home`

- shots: 002, 026, 035, 038, 051, 060, 064, 070
- z-order (back → front): scene art (full-bleed, 3D) → characters + capsule machine → home.levelCaption → home.levelPlate → home.playFrame → home.playButton → home.hardRibbon / superHardRibbon → top bar: home.avatarButton, home.coinPill < home.coinIcon < home.plusBadge, home.livesPill < home.livesHeart, home.gearButton → home.clawBar < home.clawHex / home.clawReward < home.clawMultBadge (hangs below the bar) < home.clawTimerChip / home.clawMultTray → event badges: home.streakBadge, home.skyJumpBadge / home.eventJoinBadge → home.navBar < home.navShop, home.navTrophy < home.navHomeTab (raised) < home.navHomeIcon (overhangs the tab top)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `home.avatarButton` | 18.7 · 36.7 · 63.4 · 61.4 | superellipse n 3.6 (r≈19.7) | frame #0098FD; placeholder #627F92 | — | top: safe -22.3 | 026 |
| `home.avatarButtonL32` | 18.7 · 36.7 · 63.4 · 61.4 | superellipse n 3.6 (r≈19.7) | frame #0098FD; placeholder #627F92 | — | top: safe -22.3 | 002 |
| `home.gearButton` | 334.3 · 49 · 40 · 39.7 | — | face #0292FF | — | top: safe -10.0 | 026 |
| `home.coinIcon` | 95.7 · 53 · 34 · 34 | circle ⌀34 | — | — | top: safe -6.0 | 026 |
| `home.livesHeart` | 212.5 · 53 · 39 · 33 | — | face #F13827 | — | top: safe -6.0 | 026 |
| `home.livesHeartInf` | 212.5 · 53 · 39 · 33 | — | — | — | top: safe -6.0 | 035 |
| `home.coinPill` | 126.8 · 55.7 · 73.7 · 32 | superellipse n 5.3 (r≈11.3) | fill #DEEEFF; digits #093896 | “2260” 18.8/+0.00 fill #093896 [fonts.md] | top: safe -3.3 | 026 |
| `home.coinPillL32` | 126.8 · 56 · 73.7 · 27.4 | superellipse n 5 (r≈11.3) | fill #DEEEFF; digits #093896 | “2240” 18.8/+0.00 fill #093896 [fonts.md] | top: safe -3.0 | 002 |
| `home.livesPill` | 242.2 · 56 · 76.7 · 27.4 | superellipse n 5 (r≈11.5) | — | “Full” 19.1/-0.75 fill #093896 [fonts.md] | top: safe -3.0 | 026 |
| `home.livesPillL32` | 242.2 · 56 · 76.7 · 27.4 | superellipse n 5 (r≈11.5) | — | “Full” 19.1/-0.75 fill #093896 [fonts.md] | top: safe -3.0 | 002 |
| `home.livesCount` | 226.9 · 61.7 · 20 · 21.4 | — | — | “5” 22.8/+0.00 fill #FFFFFF · outl #870400 0.9 · drop 1 [med] | top: safe +2.7 | 026 |
| `home.livesTimer` | 261.9 · 63.4 · 46.7 · 13.7 | — | — | “29:57” 18.9/-0.35 fill #093896 | top: safe +4.4 | 035 |
| `home.plusBadge` | 118.8 · 73.7 · 18.7 · 18.7 | circle ⌀18.7 | fill #FFFDEE | — | top: safe +14.7 | 026 |
| `home.clawBar` | 19.3 · 107.8 · 354.6 · 43.7 | — | track #082894; frame #019CFB | “0/1” 21.7/+0.44 fill #FFFFFF · outl #061E79 1 | top: safe +48.8 | 026 |
| `home.clawBarHard` | 19.3 · 107.8 · 354.6 · 43.7 | — | track #082894; frame #019CFB | “0/200” 21.7/+0.86 fill #FFFFFF · outl #071E79 1 | top: safe +48.8 | 035 |
| `home.clawReward` | 323.6 · 108.4 · 46 · 48.4 | — | — | — | top: safe +49.4 | 026 |
| `home.clawHex` | 30.7 · 110.8 · 36.7 · 34 | — | — | — | top: safe +51.8 | 026 |
| `home.clawBarFill` | 66.7 · 117.1 · 51 · 24.7 | rounded r 6.8 | fill #77EE28 | “40/200” 21.7/+0.91 fill #FFFFFF · outl #071F7A 1 | top: safe +58.1 | 051 |
| `home.streakBadgeL32` | 11.7 · 117.4 · 75.7 · 80.1 | — | — | — | top: safe +58.4 | 002 |
| `home.clawMultBadgeX5` | 53 · 140.8 · 35.7 · 41.7 | — | — | “x5” 16/-0.37 fill #FFF9EE→#FFF4E0→#FFEDCC · outl #800100 1.1 · drop 0.6 [med] | top: safe +81.8 | 035 |
| `home.clawMultTray` | 71.1 · 141.8 · 145.8 · 42 | rounded r 9.5 | — | “x10” (no reliable fit)<br>“x25” 15.2/-0.39 fill #FFF9EE→#FFF4E0→#FFEDCC · outl #022981 1 · drop 0.6<br>“x100” 15/+0.15 fill #FFF9EE→#FFF4DF→#FFEDCC · outl #022981 1.2 · drop 0.4 | top: safe +82.8 | 035 |
| `home.clawMultBadge` | 53 · 143.5 · 35.4 · 39 | circle ⌀35.4 | — | “x1” 16.1/-1.16 fill #FFF9EE→#FFF5E2→#FFEDCC · outl #800100 1.2 · drop 0.5 [med] | top: safe +84.5 | 026 |
| `home.clawTimerChip` | 174.5 · 149.8 · 54.7 · 16.3 | rounded r 4.8 | fill #0095FD | “3d 9h” 16.3/-0.09 fill #FFFFFF · outl #0F2C80 1.1 · drop 0.7 | top: safe +90.8 | 026 |
| `home.streakBadge` | 11.7 · 190.8 · 75.7 · 80.1 | — | — | — | top: safe +131.8 | 026 |
| `home.skyJumpBadge` | 10 · 291.9 · 76.7 · 81.7 | — | — | “0” 15.6/+0.00 fill #FFFFFF · outl #DB2B6E ? [med]<br>“23h 57m” (no reliable fit) | top: safe +232.9 | 070 |
| `home.eventJoinBadge` | 6.7 · 293.9 · 76.4 · 43 | — | — | — | top: safe +234.9 | 064 |
| `home.levelCaption` | 168.5 · 518.8 · 55 · 16.7 | — | — | “LEVEL” 14.1/-1.50 fill #FFFFFF · outl #093198 0.8 · drop 0.8 [fonts.md] | bottom: safe +282.5 | 026 |
| `home.levelPlate` | 147.5 · 536.8 · 98.4 · 32.4 | rounded r 14.8 | face #05D001; grad 12 stops | “33” 30.6/-1.50 fill #FFFFFF · outl #066A01 2.1 · drop 0.5 [fonts.md] | bottom: safe +248.8 | 026 |
| `home.levelPlateSuperHard` | 147.5 · 536.8 · 98.4 · 32.4 | rounded r 14.8 | face #7400B6 | “39” 30.6/-1.50 fill #FFFFFF [fonts.md] | bottom: safe +248.8 | 060 |
| `home.levelPlateHard` | 147.5 · 537.1 · 98.4 · 31.7 | rounded r 14.3 | face #C2090E | “34” 30.6/-1.50 fill #FFFFFF [fonts.md] | bottom: safe +249.2 | 035 |
| `home.hardRibbon` | 136.8 · 620.5 · 120.1 · 30 | — | face #FFFBE6 | “Hard Level” 17/+0.20 fill #FFFBE6 · outl #650000 1.6 · drop 0.3 [med] | bottom: safe +167.5 | 035 |
| `home.playButtonHard` | 91.7 · 620.5 · 210.5 · 94.7 | superellipse n 5.1 (r≈35.3) | face #F00915; grad 12 stops | “Play” 48.8/-3.25 fill #F1FFF2 · outl #650000 2.6 · drop 1.7 [fonts.md] | bottom: safe +102.8 | 035 |
| `home.playButtonSuperHard` | 90.7 · 620.5 · 212.5 · 95.7 | superellipse n 4.6 (r≈38.4) | face #8E00DF; grad 12 stops | “Play” 48.8/-3.25 fill #F1FFF2 · outl #430080 2.9 · drop 1.5 [fonts.md] | bottom: safe +101.8 | 060 |
| `home.playFrameSuperHard` | 82.7 · 620.5 · 228.2 · 105.4 | superellipse n 4.5 (r≈43.9) | frame #00A7FB | — | bottom: safe +92.1 | 060 |
| `home.superHardRibbon` | 136.8 · 620.5 · 120.1 · 30 | — | face #5A0A8C | “Super Hard” 15.8/-0.43 fill #FFFBE6 · outl #430080 0.9 · drop 0.9 | bottom: safe +167.5 | 060 |
| `home.playFrame` | 82.7 · 622.2 · 228.2 · 103.8 | superellipse n 4.4 (r≈43.9) | frame #00A7FB | — | bottom: safe +92.0 | 026 |
| `home.playFrameHard` | 82.7 · 623.2 · 228.2 · 102.8 | superellipse n 4.4 (r≈43.9) | frame #00A7FB | — | bottom: safe +92.0 | 035 |
| `home.playButton` | 91.1 · 628.2 · 211.2 · 86.7 | superellipse n 4.7 (r≈36.6) | face #00D300; grad 12 stops | “Play” 48.8/-3.25 fill #F1FFF2 · outl #066A01 2.2 · drop 2.2 [fonts.md] | bottom: safe +103.1 | 026 |
| `home.navHomeIcon` | 159.5 · 743.6 · 74.4 · 71.4 | — | — | — | bottom: safe +3.0 | 026 |
| `home.navHomeTab` | 126.8 · 753.6 · 140.1 · 99.1 | — | tab #0DCFFF; tabInner #25DAFF | “Home” 15.1/-0.25 fill #FFFFFF · outl #16388C 1 · drop 0.6 [fonts.md] | bottom: safe -34.7 | 026 |
| `home.navBar` | 0 · 771.7 · 393 · 81.1 | — | bar #117FFB; barTop #005CDA | — | bottom: safe -34.8 | 026 |
| `home.navShop` | 40 · 779 · 56.7 · 56.7 | — | — | — | bottom: safe -17.7 | 026 |
| `home.navTrophy` | 293.6 · 779 · 61.7 · 60.1 | — | — | — | bottom: safe -21.1 | 026 |

- `home.clawBarFill`: green progress fill inside the Claw bar track (40/200)
- `home.clawHex`: hexagon arrow icon
- `home.clawMultTray`: multiplier chevron tray that slides out under the Claw bar (seen after a streak-multiplier change)
- `home.clawReward`: reward icon at the right end (inf-heart 30m / coin stack 100)
- `home.coinPill`: left end hidden under the coin icon
- `home.coinPillL32`: left end hidden under the coin icon
- `home.eventJoinBadge`: Sky Jump entry badge with a red "Join" label
- `home.gearButton`: same 40 pt blue square button as the HUD
- `home.livesCount`: lives count on the heart
- `home.livesHeartInf`: infinite-lives heart (white infinity glyph) while a timed infinite-lives reward runs
- `home.livesTimer`: countdown replaces "Full" (mm:ss)
- `home.navHomeIcon`: garage/house icon of the selected Home tab
- `home.navShop`: shop basket icon (3D look)
- `home.navTrophy`: trophy icon (3D look)
- `home.playFrame`: blue outer frame of the Play button
- `home.playFrameHard`: blue outer frame of the Play button
- `home.playFrameSuperHard`: blue outer frame of the Play button
- `home.skyJumpBadge`: Sky Jump entry badge after joining: pink drum with a level counter, timer plate
- `home.streakBadge`: chequered-flags event badge with a timer plate
- `home.streakBadgeL32`: without the Claw bar the badge sits 220 px (73.4 pt) higher; bottom edge measured, top from the 026 badge height

### Level HUD (normal / Hard / Super Hard) — `hud`

- shots: 003, 036, 061
- z-order (back → front): board (white #FFFFFF, vector arrows) → booster.tray* < booster.button* < booster.icon* < booster.badge* → hud.coinGroup (coin icon over the pill) → hud.backButton, hud.pauseButton → hud.panel < hud.levelTab (overlaps the panel top edge) → hud.timerPill < hud.stopwatch (overlaps the pill left end) → hud.heart1..3

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `hud.coinGroup` | 19.3 · 30 · 87.7 · 25 | — | — | — | top: safe -29.0 | 003 |
| `hud.coinIcon` | 19.7 · 30.4 · 23.7 · 24.4 | rounded r 11.8 | rim #F7D000; face #F4C300; star #FBDD00 | — | top: safe -28.6 | 003 |
| `hud.coinPill` | 42.7 · 30.4 · 64.4 · 22 | rounded r 6.8 | fill #BDDCFF; grad 12 stops | “2240” 18.5/+0.25 fill #3861AC [fonts.md] | top: safe -28.6 | 003 |
| `hud.levelTab` | 149.5 · 54 · 94.4 · 23 | rounded r 4.9 | fill #008EFE; grad 12 stops | “Level 32” 17.9/-0.50 fill #FFF9EF→#FFF4E0→#FFEDCB · outl #002985 0.7 · drop 0.7 [fonts.md] | top: safe -5.0 | 003 |
| `hud.levelTabHard` | 149.5 · 54 · 94.4 · 23 | rounded r 5.1 | fill #FF3C3D; grad 12 stops | “Level 34” 17.9/-0.50 fill #FFF9EF→#FFF4E0→#FFEDCC · outl #5B0000 0.8 · drop 0.7 [fonts.md] | top: safe -5.0 | 036 |
| `hud.levelTabSuperHard` | 149.5 · 54 · 94.4 · 23 | rounded r 4.7 | fill #A628E7; grad 12 stops | “Level 39” 17.9/-0.50 fill #FFF9EF→#FFF4E1→#FFEDCC · outl #3E006E 0.6 · drop 0.8 [fonts.md] | top: safe -5.0 | 061 |
| `hud.panel` | 78.4 · 60.4 · 236.5 · 59.4 | rounded r 18.3 | fill #BDDCFF; grad 12 stops; shadow dy 2 σ 1.3 (≈black 0.47) | — | top: safe +1.4 | 003 |
| `hud.panelHard` | 78.4 · 60.4 · 236.5 · 59.4 | — | fill #BDDCFF; grad 12 stops; shadow dy 2 σ 1.3 (≈black 0.47) | — | top: safe +1.4 | 036 |
| `hud.panelSuperHard` | 78.4 · 60.4 · 236.5 · 59.4 | — | fill #BDDCFF; grad 12 stops; shadow dy 2 σ 1.3 (≈black 0.47) | — | top: safe +1.4 | 061 |
| `hud.pauseButton` | 334.3 · 68.1 · 40.4 · 40 | superellipse n 3.6 (r≈12.8) | face #008CFE; glyph #E9FFFD; grad 12 stops; shadow dy 0.7 σ 1 (≈black 0.99) | — | top: safe +9.1 | 003 |
| `hud.pauseButtonSuperHard` | 334.6 · 68.1 · 39.7 · 40 | superellipse n 3.5 (r≈12.9) | face #9100E4; glyph #FDF6FF; grad 12 stops; shadow dy 0.7 σ 1.3 (≈black 0.97) | — | top: safe +9.1 | 061 |
| `hud.backButton` | 19 · 68.4 · 40 · 40 | superellipse n 3.7 (r≈12.4) | face #008CFE; grad 12 stops; shadow dy 0.7 σ 1 (≈black 0.98) | — | top: safe +9.4 | 003 |
| `hud.backButtonHard` | 19.3 · 68.4 · 39.7 · 39.7 | superellipse n 3.5 (r≈12.8) | face #EC0911; grad 12 stops; shadow dy 0.7 σ 1.3 (≈black 0.99) | — | top: safe +9.4 | 036 |
| `hud.backButtonSuperHard` | 19 · 68.4 · 40 · 39.7 | superellipse n 3.6 (r≈12.6) | face #9100E4; grad 12 stops; shadow dy 0.7 σ 1.3 (≈black 0.98) | — | top: safe +9.4 | 061 |
| `hud.pauseButtonHard` | 334.6 · 68.4 · 39.7 · 39.7 | superellipse n 3.6 (r≈12.5) | face #EC0911; glyph #FFF5F5; grad 12 stops; shadow dy 0.7 σ 1.3 (≈black 0.99) | — | top: safe +9.4 | 036 |
| `hud.stopwatch` | 92.7 · 77.7 · 29 · 33 | — | ring #FDAE06; face #F3E9D9 | — | top: safe +18.7 | 003 |
| `hud.timerPill` | 112.4 · 81.7 · 73.4 · 26.4 | rounded r 9.3 | fill #6C94DC; grad 12 stops | “3:00” 23.3/+0.25 fill #F7F7F9→#EDEDF2→#E2E3EA · outl #081E5E 0.7 · drop 1.1 [fonts.md] | top: safe +22.7 | 003 |
| `hud.timerPillHard` | 112.4 · 81.7 · 73.4 · 26.4 | rounded r 9.3 | fill #6C94DC; grad 12 stops | “3:30” 23.3/+0.25 fill #F7F7F9→#EDEDF2→#E2E3EA [fonts.md] | top: safe +22.7 | 036 |
| `hud.timerPillSuperHard` | 112.4 · 81.7 · 73.4 · 26.4 | rounded r 9.3 | fill #6C94DC; grad 12 stops | “3:00” 23.3/+0.25 fill #F7F7F9→#EDEDF2→#E2E3EA [fonts.md] | top: safe +22.7 | 061 |
| `hud.heart1` | 201.5 · 82.1 · 28.7 · 24.4 | — | face #FB3A2A; spec #FC8258 | — | top: safe +23.1 | 003 |
| `hud.heart2` | 237.5 · 82.1 · 28.7 · 24.4 | — | — | — | top: safe +23.1 | 003 |
| `hud.heart3` | 273.6 · 82.1 · 28.4 · 24.4 | — | — | — | top: safe +23.1 | 003 |

- `hud.coinGroup`: coin icon + coin pill, one unit

### Level HUD — booster corners — `booster`


| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `booster.trayLeft` | 0 · 753.3 · 82.7 · 81.1 | superellipse n 3 (r≈30.2) | fill #BDDCFF; well #648DD7; shadow dy 2.7 σ 1.3 (≈black 0.31) | — | bottom: safe -16.4 | 003 |
| `booster.trayRight` | 310.6 · 753.3 · 82.4 · 81.1 | — | — | — | bottom: safe -16.4 | 003 |
| `booster.buttonLeft` | 14.3 · 764 · 57.4 · 56.4 | superellipse n 3.3 (r≈19.1) | face #00E400; rim #1A901A; grad 12 stops | — | bottom: safe -2.4 | 003 |
| `booster.buttonRight` | 321.6 · 764 · 57.4 · 56.4 | superellipse n 3.3 (r≈19.2) | — | — | bottom: safe -2.4 | 003 |
| `booster.iconRight` | 337.3 · 773 · 26 · 39 | — | — | — | bottom: safe +6.0 | 003 |
| `booster.iconLeft` | 25.7 · 773.3 · 34.4 · 38 | — | — | — | bottom: safe +6.7 | 003 |
| `booster.badgeLeft` | 53 · 801.7 · 24.7 · 24.4 | circle ⌀24.2 | fill #FF4344 | “3” 16.9/+0.00 fill #FFFBF3→#FFF6E6→#FFF2D9 · outl #69000C 0.7 · drop 0.6 [med] | bottom: safe -8.1 | 003 |

### Pause panel — `pause`

- shots: 007, 018, 048, 082, 103
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): level (board + HUD) → dim → pause.panel frame (bars, pause.bumperTL corner pieces, pause.rivet) → pause.card (cream inset) → row icons + labels + toggles (pause.toggleKnob over the track) → pause.resume, pause.quit → pause.ribbon (overlaps the panel top) → pause.close (overlaps the panel top-right)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `pause.ribbon` | 60.1 · 190.5 · 274.2 · 90.4 | rounded r 26.8 | top #FFCF00; bottom #FFBD00; grad 12 stops | “Paused” 49.2/-1.00 fill #FFFFFF · outl #7B1D01 1.9 · drop 3.1 [fonts.md] | centre -190.3 | 007 |
| `pause.panel` | 11.3 · 228.9 · 370.6 · 399 | superellipse n 6.3 | frame #005DEC; field #226DF5; groove #153CC1; bumper #00B4FF | — | centre +2.4 | 007 |
| `pause.close` | 338.6 · 234.2 · 45.4 · 45 | circle ⌀45 | red #FF2D2E; glyph #FFE9E9 | — | centre -169.3 | 007 |
| `pause.bumperTL` | 13.7 · 234.9 · 50.4 · 83.7 | — | face #00B4FF | — | centre -149.2 | 007 |
| `pause.card` | 51.4 · 299.6 · 287.9 · 165.8 | rounded r 24.4 | fill #F8E7D2; border #D0987D | — | centre -43.5 | 007 |
| `pause.rivet` | 17 · 302.6 · 13 · 13 | rounded r 6.3 | centre #4CA9EF | — | centre -116.9 | 007 |
| `pause.toggleKnob` | 262.2 · 328.6 · 60.4 · 37.4 | rounded r 9.3 | knob #009EFC | — | centre -78.7 | 007 |
| `pause.toggleSound` | 206.5 · 328.6 · 116.1 · 37.4 | rounded r 8.5 | green #00E500; knob #009EFC | “ON” 21/-0.75 fill #FFFCED→#FEF7E4→#FDF3DC · outl #066A01 1 · drop 1 [fonts.md] | centre -78.7 | 007 |
| `pause.iconSound` | 73.4 · 331.6 · 31.4 · 28.7 | — | — | “Sound” 25.5/+0.00 fill #622100 [fonts.md] | centre -80.0 | 007 |
| `pause.toggleHaptic` | 206.5 · 401.7 · 116.1 · 37.4 | rounded r 8.8 | — | “ON” 21/-0.75 fill #FFFCED→#FEF7E4→#FDF3DC · outl #066A01 1 · drop 1 [fonts.md] | centre -5.6 | 007 |
| `pause.iconHaptic` | 72.4 · 403.3 · 33 · 31.7 | — | — | “Haptic” 25.2/-0.25 fill #622100 [fonts.md] | centre -6.8 | 007 |
| `pause.quit` | 206.5 · 486.1 · 125.1 · 89.1 | superellipse n 3.9 (r≈31.9) | face #E8050D; grad 12 stops | “Quit” 30.5/-0.50 fill #FFFCED→#FEF8E6→#FDF4DC · outl #650000 1.5 · drop 1.4 [fonts.md] | centre +104.6 | 007 |
| `pause.resume` | 60.4 · 486.1 · 125.1 · 89.1 | superellipse n 3.9 (r≈32) | face #00C900; grad 12 stops | “Resume” 27.2/-1.00 fill #FFFCED→#FEF9E8→#FDF4DD · outl #066A01 1.4 · drop 1.1 [fonts.md] | centre +104.6 | 007 |

- `pause.panel`: superellipse n=6.31 (fit rms 2.09 px); top edge hidden behind the ribbon, from the fit
- `pause.quit`: frame includes the ~1 pt dark outline (second pass); frame_body_pt = coloured body only
- `pause.resume`: frame includes the ~1 pt dark outline (second pass); frame_body_pt = coloured body only

### Out of Time! — `outOfTime`

- shots: 013, 030
- dim: `dim.outOfTime` = #000000 at 0.94
- z-order (back → front): level → dim (0.94) → outOfTime.glow (blue radial) → outOfTime.stopwatch (3D) → outOfTime.title → outOfTime.plus30 → outOfTime.addTime → outOfTime.coinGroup (top-left, above the dim) → outOfTime.close (top-right)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `outOfTime.close` | 327.3 · 53 · 45.4 · 45 | circle ⌀45 | red #FF2A2A; glyph #FFE9E9 | — | top: safe -6.0 | 013 |
| `outOfTime.coinGroup` | 12.7 · 62.4 · 108.4 · 44.4 | — | fill #DEEEFF; plus #F9F1E7 | “2240” 21.4/+0.44 fill #093896 | top: safe +3.4 | 013 |
| `outOfTime.title` | 36.4 · 173.1 · 320.6 · 55.7 | — | faceTop #FFFAFA; faceBottom #580008 | “Out of Time!” 52/-1.04 fill #FFFFFF→#FFFAFA→#FFE5E5 · outl #580008 1.5 + #E42831 3 · drop 4.7 [med] | top: safe +114.1 | 013 |
| `outOfTime.glow` | 0 · 253.5 · 393 · 266.9 | — | r0_edge_x280 #0C1840; x230 #0D1530; x180 #0E1220; x130 #0F1015 | — | centre -39.1 | 013 |
| `outOfTime.stopwatch` | 91.7 · 273.6 · 208.2 · 220.9 | — | — | — | centre -41.9 | 013 |
| `outOfTime.plus30` | 87.1 · 509.4 · 224.9 · 59.4 | — | — | “+30 sec” 61/-0.75 fill #FDF0E6 · outl #004DFB 2.1 · drop 2.6 [med] | centre +113.1 | 013 |
| `outOfTime.addTime` | 71.7 · 627.5 · 249.9 · 104.1 | superellipse n 4.9 (r≈42.6) | — | — | centre +253.5 | 013 |
| `outOfTime.addTimeFace` | 79.7 · 632.9 · 233.9 · 88.1 | superellipse n 5.1 (r≈36.5) | face #00DA00; grad 12 stops | “Add Time” 23.1/+0.22 fill #FFFCED→#FEF8E5→#FDF3DC · outl #066A01 1.2 · drop 1<br>“900” 26.2/+0.52 fill #FFFCED→#FEF7E4→#FDF3DC · outl #066A01 1.6 · drop 0.9 [med] | centre +250.9 | 013 |

- `outOfTime.addTime`: green button inside a blue outer frame
- `outOfTime.glow`: blue radial glow behind the big stopwatch (samples leftwards from the body edge at y=1130 px)
- `outOfTime.stopwatch`: 3D prop, includes its glow
- `outOfTime.title`: white->pink face, red outline, dark-red extrusion (second pass: all glyph components)
- `outOfTime.addTimeFace`: frame includes the ~1 pt dark outline (second pass); frame_body_pt = coloured body only

### Continue? — streak variant — `continueStreak`

- shots: 014
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): level → dim → continueStreak.band (full-width blue band + cream middle) → continueStreak.ribbon → continueStreak.close → continueStreak.message → continueStreak.chips < continueStreak.chipLit → continueStreak.playOn → continueStreak.coinGroup

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `continueStreak.coinGroup` | 12.7 · 96.1 · 105.1 · 41.4 | — | — | — | top: safe +37.1 | 014 |
| `continueStreak.ribbon` | 60.1 · 193.5 · 274.2 · 90.4 | rounded r 26.7 | top #FFCD00; bottom #FFBB00; grad 12 stops | “Continue?” 46.6/-0.17 fill #FFFFFF · outl #7B1D01 2.1 · drop 2.7 [med] | centre -187.3 | 014 |
| `continueStreak.band` | 0 · 213.5 · 393 · 424.7 | — | rail #FFC400; field #FFB600; cream #F8E7D2; lower #226DF5 | — | centre -0.1 | 014 |
| `continueStreak.close` | 340 · 214.8 · 45 · 45 | circle ⌀45 | red #FF2E2F; glyph #FFE9E9 | — | centre -188.7 | 014 |
| `continueStreak.message` | 56.7 · 323.6 · 280.2 · 33.4 | — | — | “You will lose your streak!” 22.9/-0.34 fill #622100 | centre -85.7 | 014 |
| `continueStreak.chips` | 8 · 372 · 376.7 · 66.4 | rounded r 16.5 | track #F8E8D3; litFace #015100; litRing #FFC400 | — | centre -20.8 | 014 |
| `continueStreak.chipLit` | 9.7 · 373.7 · 83.4 · 63.1 | rounded r 16.1 | — | “x1” 30.8/-2.90 fill #FFFBE6 · outl #015100 1.8 · drop 1.6 [med] | centre -20.8 | 014 |
| `continueStreak.playOn` | 79.7 · 498.4 · 233.9 · 88.1 | superellipse n 5 (r≈37.2) | face #00E400; grad 12 stops | “Play On” 31/+0.40 fill #FFFBED→#FEF7E3→#FDF3DC · outl #066A01 2.2 · drop 0.7 [med]<br>“900” 31.6/+0.71 fill #FFFCED→#FEF7E4→#FDF3DC · outl #066A01 2.1 · drop 0.9 [med] | centre +116.4 | 014 |

- `continueStreak.band`: full-width band (no side frame), rails top/bottom with rivets
- `continueStreak.playOn`: frame includes the ~1 pt dark outline (second pass); frame_body_pt = coloured body only

### Continue? — life variant — `continueLife`

- shots: 015
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): level → dim → continueLife.band → continueLife.ribbon → continueLife.close → continueLife.message → continueLife.brokenHeart → continueLife.playOn → continueLife.coinGroup

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `continueLife.coinGroup` | 12.7 · 96.1 · 105.1 · 41.4 | — | — | — | top: safe +37.1 | 015 |
| `continueLife.ribbon` | 60.1 · 193.5 · 274.2 · 90.4 | rounded r 26.7 | top #FFCD00; bottom #FFBB00; grad 12 stops | “Continue?” 46.6/-0.17 fill #FFFFFF · outl #7B1D01 2.1 · drop 2.7 [med] | centre -187.3 | 015 |
| `continueLife.band` | 0 · 213.5 · 393 · 424.7 | — | rail #FFC400; field #FFB600; cream #F8E7D2; lower #226DF5 | — | centre -0.1 | 015 |
| `continueLife.close` | 340 · 214.8 · 45 · 45 | circle ⌀45 | red #FF2E2F; glyph #FFE9E9 | — | centre -188.7 | 015 |
| `continueLife.message` | 56.7 · 323.6 · 280.2 · 33.4 | — | — | “You will lose a life!” 26.1/-1.59 fill #622100 | centre -85.7 | 015 |
| `continueLife.brokenHeart` | 134.1 · 360.6 · 123.1 · 97.4 | — | — | — | centre -16.7 | 015 |
| `continueLife.playOn` | 80.7 · 500.4 · 231.9 · 85.1 | superellipse n 5.3 (r≈34.9) | face #00E400; grad 12 stops | “Play On” 31/+0.40 fill #FFFBED→#FEF7E3→#FDF3DC · outl #066A01 2.2 · drop 0.7 [med]<br>“900” 31.6/+0.71 fill #FFFCED→#FEF7E4→#FDF3DC · outl #066A01 2.1 · drop 0.9 [med] | centre +116.9 | 015 |

- `continueLife.band`: full-width band (no side frame), rails top/bottom with rivets

### Level Failed / Try Again — `failed`

- shots: 016, 031
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): level → dim → failed.panel → failed.card → failed.brokenHeart → failed.caption → failed.tryAgain → failed.ribbon → failed.close → streakRace strip (bottom): streakRace.band < streakRace.logo < streakRace.timerChip < streakRace.chips

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `failed.ribbon` | 60.1 · 171.1 · 274.2 · 90.4 | rounded r 26.2 | top #FFCC00; bottom #FFBA00; grad 12 stops | “Level 32” 49/-0.51 fill #FFFFFF · outl #7B1D01 2.1 · drop 2.8 [med] | centre -209.7 | 016 |
| `failed.panel` | 10 · 198.2 · 373.3 · 464.4 | superellipse n 6 | — | — | centre +4.4 | 016 |
| `failed.close` | 338.3 · 206.8 · 46 · 45.7 | circle ⌀45.7 | red #EE2B2B; glyph #FFE9E9 | — | centre -196.3 | 016 |
| `failed.card` | 54.7 · 280.9 · 283.9 · 210.2 | rounded r 24.2 | fill #F8E7D2 | — | centre -40.0 | 016 |
| `failed.brokenHeart` | 121.4 · 302.9 · 150.5 · 119.1 | — | — | — | centre -63.6 | 016 |
| `failed.caption` | 120.1 · 440.4 · 153.5 · 30 | — | — | “Level Failed!” 25/-0.71 fill #622100 [med] | centre +29.4 | 016 |
| `failed.tryAgain` | 90.4 · 517.1 · 212.5 · 88.4 | superellipse n 4.6 (r≈37.7) | face #00D900; grad 12 stops | “Try Again” 37.7/-1.94 fill #FFFCED→#FEF7E4→#FDF3DC · outl #066A01 1.6 · drop 1.8 [med] | centre +135.3 | 016 |

- `failed.panel`: superellipse n=6.04 (rms 2.41 px)
- `failed.tryAgain`: frame includes the ~1 pt dark outline (second pass); frame_body_pt = coloured body only

### Streak Race strip (under the Failed and Win panels) — `streakRace`


| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `streakRace.logo` | 78.4 · 687.9 · 233.5 · 53.4 | — | — | — | bottom: safe +76.7 | 016 |
| `streakRace.band` | 0 · 700.6 · 393 · 152.1 | — | rail #F6F2ED; field #2A60EF | — | bottom: safe -34.7 | 016 |
| `streakRace.timerChip` | 313.6 · 707.3 · 76.7 · 28 | rounded r 11.8 | — | “9h 16m” 12.2/-1.38 fill #622200 [med] | bottom: safe +82.7 | 016 |
| `streakRace.chips` | 8 · 762 · 371.6 · 64.4 | rounded r 11.3 | — | “x5” 27.2/-2.37 fill #622200 [med]<br>“x10” 27.2/-1.64 fill #622200<br>“x25” 27.1/-1.78 fill #622200<br>“x100” 27/-1.42 fill #622200<br>“x1” 30.8/-2.90 fill #FFFBE6 · outl #015100 1.6 · drop 1.7 [med] | bottom: safe -8.4 | 016 |

- `streakRace.logo`: lettering artwork (italic, yellow Streak / white Race, blue outline, chequered flags)

### Win popup (normal) — `win`

- shots: 020, 032, 045, 050, 054, 058, 073, 078, 083, 087, 099, 104
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): level → dim → win.panel → win.perfect → win.rewardsLabel → win.coins < win.amount → win.continue → win.ribbon → win.close → streakRace strip (bottom)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `win.ribbon` | 60.1 · 149.8 · 274.2 · 90.4 | rounded r 26.5 | top #FFCF00; bottom #FFBD00; grad 12 stops | “Level 32” 49/-0.51 fill #FFFFFF · outl #7B1D01 2.1 · drop 2.8 [med] | centre -231.0 | 020 |
| `win.panel` | 10 · 176.8 · 373.3 · 465.1 | superellipse n 5.9 | field #2370F5; fieldTop #FFFBF2; fieldGlow #FFCA00; frame #005EED | — | centre -16.6 | 020 |
| `win.close` | 338.6 · 185.2 · 45.4 · 45 | circle ⌀45 | red #FF5053; glyph #FFE9E9 | — | centre -218.3 | 020 |
| `win.perfect` | 110.8 · 254.5 · 172.5 · 45.4 | — | — | “Perfect!” 45.2/-1.62 fill #FFFAF0→#FFF5E1→#FFEDCB · outl #022880 2.4 · drop 4.2 [med] | centre -148.8 | 020 |
| `win.rewardsLabel` | 140.1 · 306.9 · 113.4 · 30 | — | — | “Rewards:” 25.9/-1.52 fill #FFFFFF | centre -104.1 | 020 |
| `win.coins` | 141.1 · 366.6 · 120.1 · 99.1 | — | — | — | centre -9.8 | 020 |
| `win.amountDigits` | 215.2 · 413.7 · 74.1 · 62.1 | — | — | “20” 56.5/-3.73 fill #FFFFFF [med] | centre +18.8 | 020 |
| `win.amount` | 243.5 · 415.4 · 61.7 · 60.1 | — | — | — | centre +19.4 | 020 |
| `win.continue` | 90.4 · 497.4 · 212.5 · 88.1 | superellipse n 5 (r≈35.5) | face #01D801; grad 12 stops | “Continue” 38.9/+0.05 fill #FFFCED→#FEF9E8→#FDF4DC · outl #066A01 1.7 · drop 1.8 [med] | centre +115.4 | 020 |

- `win.amount`: SUPERSEDED by win.amountDigits: this first-pass box covers only the right half of the "20"
- `win.amountDigits`: reward amount "20" (white face, navy #022880 outline) overlapping the coin stack; replaces the first-pass win.amount box
- `win.coins`: 3D coin stack + amount
- `win.panel`: superellipse n=5.92 (rms 2.41 px)
- `win.continue`: frame includes the ~1 pt dark outline (second pass); frame_body_pt = coloured body only

### Win popup — Hard — `winHard`

- shots: 037, 092
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): as win; red panel; winHard.tagRibbon above win.ribbon

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `winHard.tagRibbon` | 76.7 · 100.1 · 240.2 · 56.7 | — | face #FFFFFF | “Hard Level” 23.4/-0.96 fill #FFFFFF · outl #69000C 1.6 · drop 1 | centre -297.6 | 037 |
| `winHard.ribbon` | 60.1 · 150.1 · 274.2 · 90.1 | rounded r 26.9 | top #FFCF00; bottom #FFBD00; grad 12 stops | “Level 34” 49/-0.54 fill #FFFFFF · outl #7B1D01 1.9 · drop 3.1 | centre -230.9 | 037 |
| `winHard.panel` | 9.7 · 177.2 · 374 · 464.7 | superellipse n 5.9 | field #CC0410; frame #9E0014; groove #89010B | — | centre -16.5 | 037 |

- `winHard.panel`: n=6.12 rms 2.46

### Win popup — Super Hard — `winSuperHard`

- shots: 063
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): as win; purple panel; winSuperHard.tagRibbon above the ribbon

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `winSuperHard.tagRibbon` | 76.7 · 100.1 · 240.2 · 56.7 | — | face #FFFFFF | “Super Hard” 23.2/-0.65 fill #FFFFFF · outl #3A007C 1.9 · drop 0.7 | centre -297.6 | 063 |
| `winSuperHard.ribbon` | 60.1 · 150.5 · 274.2 · 89.7 | rounded r 26.6 | top #FFCF00; bottom #FFBD00; grad 12 stops | “Level 39” 49/-0.32 fill #FFFFFF · outl #7B1D01 2.1 · drop 2.9 [med] | centre -230.7 | 063 |
| `winSuperHard.panel` | 9.7 · 177.2 · 374.3 · 465.4 | superellipse n 5.9 | field #8F01DE; frame #7306BA; groove #580694 | — | centre -16.1 | 063 |

- `winSuperHard.panel`: INFERRED = the Hard panel geometry (the purple glow defeats the outline fit); bottom edge checked on the centre column (y 1926 px)

### Win celebration (logo + confetti) — `celebrate`

- shots: 049, 053, 057, 062, 072, 077, 086, 091, 098
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): level → dim → confetti + 2 firework rockets → celebrate.logo

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `celebrate.logo` | 46 · 294.9 · 307.9 · 232.2 | — | — | — | centre -15.0 | 049 |

- `celebrate.logo`: game logo sign (our own logo in the build); confetti + 2 rocket trails around it

### Feature unlock (Pipe!) — `unlock`

- shots: 040
- dim: `dim.unlock` = #000000 at 0.90
- z-order (back → front): level (timer not started) → dim → unlock.title → unlock.subtitle → unlock.icon → unlock.card

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `unlock.title` | 128.4 · 168.5 · 136.8 · 70.1 | — | — | “Pipe!” 54.4/-3.65 fill #FFFBF4→#FFF5E2→#FFF0D3 [med] | centre -222.4 | 040 |
| `unlock.subtitle` | 131.8 · 275.2 · 130.1 · 30 | — | — | “Unlocked!” 24.5/+0.26 fill #FFFFFF · outl #022880 1.7 · drop 1.2 | centre -135.8 | 040 |
| `unlock.icon` | 147.1 · 354.3 · 123.8 · 112.1 | — | — | — | centre -15.6 | 040 |
| `unlock.card` | 42.7 · 517.1 · 307.9 · 100.1 | rounded r 23.9 | fill #F8E7D2; border #005DEE | “Pass arrows through the” 22.3/-0.52 fill #231C67<br>“to break it!” 21.6/-0.05 fill #231C67 | centre +141.1 | 040 |

- `unlock.icon`: pipe icon with the "3" counter cap

### Claw Challenge screen — `claw`

- shots: 021, 022, 023, 024
- z-order (back → front): claw.band background (blue) → claw.ladderRail < claw.ladderNode → claw.ladderCard < claw.padlock (scrolls) → claw.header (3D art) → claw.logo → claw.timerChip → claw.subtitle → claw.chevrons → claw.progressBar < claw.progressHex / claw.progressReward → claw.infoButton, claw.close (fixed)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `claw.header` | 0 · 0 · 393 · 243.5 | — | — | — | top: safe -59.0 | 021 |
| `claw.close` | 332.9 · 49 · 45 · 45 | circle ⌀45 | red #FF2526 | — | top: safe -10.0 | 021 |
| `claw.infoButton` | 9.7 · 57 · 30.4 · 30.4 | — | face #009CFD; glyph #F1FEFF | — | top: safe -2.0 | 021 |
| `claw.logo` | 43.4 · 208.5 · 306.9 · 58.4 | — | — | — | top: safe +149.5 | 021 |
| `claw.band` | 0 · 233.5 · 393 · 200.2 | — | fill #2569F3; rail #FED023 | — | centre -92.4 | 021 |
| `claw.timerChip` | 162.8 · 262.9 · 67.7 · 23 | rounded r 4.4 | fill #F9E5D2 | “3d 9h” 14.9/-0.29 fill #622200 | top: safe +203.9 | 021 |
| `claw.subtitle` | 13.3 · 288.6 · 367 · 25 | — | — | “Beat levels without fail to get more rewards!” 17.2/-0.27 fill #FDEEED→#FDE8DB→#FDE2C8 · outl #0F2C80 1.1 · drop 0.7 | top: safe +229.6 | 021 |
| `claw.chevrons` | 18.3 · 315.3 · 347 · 55 | — | track #0186FD; chip #C2CCE1; lit #800100 | “x1” 25.7/-2.33 fill #FFFFFF · outl #800100 1.8 · drop 0.9 [med]<br>“x5” 22.5/-1.31 fill #FFFFFF · outl #022981 1.5 · drop 0.8 [med]<br>“x10” 22.4/-0.68 fill #FFFFFF · outl #022981 1.6 · drop 0.7<br>“x25” 22.5/-0.78 fill #FFFFFF · outl #022981 1.5 · drop 0.9<br>“x100” 20.8/-0.11 fill #FFFFFF · outl #022981 1.5 · drop 0.7 | top: safe +256.3 | 021 |
| `claw.progressReward` | 326.9 · 380 · 40.4 · 35.7 | — | — | — | top: safe +321.0 | 021 |
| `claw.progressBar` | 23.4 · 380.3 · 347 · 41.7 | — | track #082894 | “0/1” 21.2/+0.63 fill #FFFFFF · outl #061E79 1 | top: safe +321.3 | 021 |
| `claw.progressHex` | 27.7 · 383.7 · 37.7 · 35.4 | — | — | — | top: safe +324.7 | 021 |
| `claw.ladderRail` | 63.4 · 433.7 · 20 · 419 | — | rail #00A6FC | — | centre +217.2 | 021 |
| `claw.ladderCard` | 149.1 · 742 · 185.8 · 78.7 | rounded r 20 | fill #F8E7D2; rim #0039A3 | — | centre +355.4 | 021 |
| `claw.ladderNode` | 46 · 759.3 · 54.7 · 55.4 | — | inner #A7B4E6; ring #059BFD | “1” 26.1/+0.00 fill #FFFFFF · outl #172B5A 2.3 · drop 0.4 [med] | centre +361.0 | 021 |
| `claw.padlock` | 311.6 · 797.7 · 37.4 · 36.4 | — | — | — | centre +389.9 | 021 |

- `claw.band`: blue header band under the art (rails with rivets on top)
- `claw.header`: 3D illustration header (claw machine, two workers, prizes); full width, top of the screen
- `claw.infoButton`: round blue (i) button, white glyph with navy outline
- `claw.ladderCard`: locked reward card (cream, blue rim) + padlock
- `claw.ladderNode`: numbered node on the vertical rail
- `claw.logo`: "Claw Challenge" lettering artwork: italic, yellow "Claw" + white "Challenge", navy outline, 3D bevel
- `claw.padlock`: padlock icon on a locked card
- `claw.progressHex`: hexagon-arrow icon
- `claw.progressReward`: inf-heart 30m reward icon

### Claw Challenge info overlay — `clawInfo`

- shots: 025
- dim: `dim.unlock` = #000000 at 0.90
- z-order (back → front): claw screen → dim → clawInfo.title → clawInfo.mazeIcon → captions → clawInfo.chips → clawInfo.coins

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `clawInfo.title` | 56.7 · 50 · 280.2 · 50 | — | — | — | top: safe -9.0 | 025 |
| `clawInfo.mazeIcon` | 57.4 · 138.8 · 105.8 · 105.4 | rounded r 6.1 | — | — | centre -234.5 | 025 |
| `clawInfo.caption1` | 50 · 255.2 · 123.4 · 41.7 | — | line1Face #611100 | “Beat levels” 15.7/+0.02 fill #FFD302→#FCE7D7→#FCDFD2<br>“without losing!” 15.5/+0.27 fill #FCE7D7 | centre -149.9 | 025 |
| `clawInfo.chips` | 166.8 · 338.6 · 197.2 · 62.4 | — | — | — | centre -56.2 | 025 |
| `clawInfo.caption2` | 181.8 · 407 · 161.8 · 41.7 | — | line1Face #580700 | “Increase your score” 16.5/+0.17 fill #FFD102→#FCE7D7→#FCE7D7<br>“multiplier!” 16/+0.26 fill #FCE7D7 | centre +1.9 | 025 |
| `clawInfo.coins` | 89.7 · 523.4 · 75.4 · 47.4 | — | — | — | centre +121.1 | 025 |

- `clawInfo.caption1`: line 1 yellow face, line 2 white face; lines found: [(201, 776, 457, 820), (155, 834, 511, 887)]
- `clawInfo.caption2`: line 1 yellow face, line 2 white face; lines found: [(555, 1230, 1023, 1283), (662, 1290, 914, 1342)]
- `clawInfo.title`: event title lettering (white face, blue outline + extrusion)

### Reward claim — infinite lives — `claim`

- shots: 033, 034
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): home → dim → claim.title → claim.heart → claim.amount → claim.tap

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `claim.title` | 10 · 151.8 · 373.7 · 53.4 | — | — | “Congratulations!” 45.2/-0.83 fill #FFDC13→#FFC402→#FFB700 · outl #B24900 0.9 · drop 1.8 [med] | top: safe +92.8 | 034 |
| `claim.heart` | 159.8 · 379 · 74.1 · 64.7 | — | — | — | centre -14.6 | 034 |
| `claim.amount` | 165.1 · 433.7 · 61.7 · 31.7 | — | — | “30m” 27.6/-1.03 fill #FFFFFF · outl #B30400 1.6 · drop 1.2 | centre +23.6 | 034 |
| `claim.tap` | 96.7 · 673.9 · 200.2 · 33.4 | — | — | “Tap to Claim” 31.5/-0.48 fill #FFFFFF · outl #3A007C 1.2 · drop 1.2 [med] | bottom: safe +110.7 | 034 |

### Reward claim — coins — `claimCoins`

- shots: 095, 100-after-L045-home1
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): home → dim → claimCoins.title → claimCoins.coins → claimCoins.amount → claimCoins.tap

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `claimCoins.title` | 15.3 · 151.1 · 363 · 47.7 | — | — | “Congratulations!” 45.2/-0.83 fill #FFDD13→#FFC503→#FFB700 · outl #B24900 0.9 · drop 1.8 [med] | top: safe +92.1 | 095 |
| `claimCoins.coins` | 158.5 · 382.7 · 76.7 · 60.1 | — | — | — | centre -13.2 | 095 |
| `claimCoins.amount` | 168.5 · 433.7 · 56.7 · 33.4 | — | — | “714” 27.2/-1.69 fill #FFFFFF · outl #09066D 2.6 · drop 0.2 | centre +24.4 | 095 |
| `claimCoins.amount200` | 163.5 · 433.7 · 66.7 · 30 | — | — | “200” 27.6/-0.31 fill #FFFFFF · outl #09066D 2.7 · drop 0.2 [med] | centre +22.7 | 100 |
| `claimCoins.tap` | 99.1 · 677.9 · 193.8 · 32.4 | — | — | “Tap to Claim” 31.7/-0.59 fill #FFFFFF · outl #3A007C 1.2 · drop 1.2 [med] | bottom: safe +107.7 | 095 |

- `claimCoins.amount200`: Claw step reward 200 coins

### Sky Jump popup (join) — `skyJump`

- shots: 065
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): home → dim → skyJump.panel → sky/prize art → skyJump.timerChip → skyJump.stages < skyJump.stageLabel → skyJump.rules → skyJump.start → skyJump.logo (overlaps the panel top) → skyJump.close

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `skyJump.logo` | 66.7 · 133.4 · 266.9 · 70.1 | — | — | — | centre -257.6 | 065 |
| `skyJump.panel` | 10.3 · 172.8 · 372.6 · 536.5 | custom (see note) | frame #5F3AD5; rivet #8D6DE9; rivetBottom #5A35CA; sky #2387F2 | — | centre +15.1 | 065 |
| `skyJump.close` | 338.3 · 176.5 · 45 · 45 | circle ⌀45 | — | — | centre -227.0 | 065 |
| `skyJump.timerChip` | 158.8 · 209.5 · 75.4 · 23.4 | — | fill #865FF8 | “8h 14m” 13.2/-0.32 fill #FFFFFF | centre -204.8 | 065 |
| `skyJump.stages` | 40.7 · 455.4 · 309.9 · 105.8 | rounded r 18.6 | fill #8F6EFE; tile #9473FE; rulesStrip #502DC3 | — | centre +82.3 | 065 |
| `skyJump.stageLabel` | 58.4 · 490.4 · 71.7 · 21.7 | — | — | “Stage 1” 18/-0.46 fill #FFFFFF · outl #0F2C80 1.8 · drop 0 | centre +75.2 | 065 |
| `skyJump.rules` | 66.7 · 518.8 · 260.2 · 33.4 | — | — | — | centre +109.5 | 065 |
| `skyJump.start` | 89.7 · 574.8 · 212.5 · 87.7 | superellipse n 4.9 (r≈36) | grad 12 stops | “Start” 44.3/-3.44 fill #F1FFF2 · outl #066A01 2 · drop 2 [med] | centre +192.6 | 065 |

- `skyJump.logo`: "Sky Jump" lettering artwork
- `skyJump.panel`: segmented purple frame (straight bars + lighter corner bumpers + rivets at the joints). Left 31 / right 1148 / bottom 2126 px VERIFIED (065, 096 identical); top edge hidden by the logo: 518 px INFERRED from the top-left arc (x 40 -> 700 px, 100 -> 570, 195 -> 522). Corner profile (x px -> edge y px): top 40:700 60:623 100:570 140:541 195:522; bottom 40:1927 60:2003 100:2057 160:2096 (centre 2126). A single superellipse does not fit (rms 17 px); approximate with a rounded rect r_top ~57 pt, r_bottom ~80 pt or draw the profile.
- `skyJump.timerChip`: stopwatch icon 476-556 px overlapping a purple chip; white text, #380E66 outline
- `skyJump.start`: frame includes the ~1 pt dark outline (second pass); frame_body_pt = coloured body only

### Sky Jump stage-2 offer — `skyOffer`

- shots: 096
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): as skyJump (stage-2 offer)

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `skyOffer.panel` | 10.3 · 172.8 · 372.6 · 536.5 | custom (see note) | — | — | centre +15.1 | 096 |
| `skyOffer.close` | 338.3 · 176.5 · 45 · 45 | circle ⌀45 | — | — | centre -227.0 | 096 |
| `skyOffer.check` | 74.1 · 462.1 · 39.4 · 31.7 | — | face #76E438 | — | centre +52.0 | 096 |

- `skyOffer.panel`: identical frame to skyJump.panel (065 vs 096: same edges); Stage 1 chip shows a green check

### Sky Jump matching — `skyMatch`

- shots: 066, 067
- dim: `dim.skyMatch` = #000000 at 0.96
- z-order (back → front): home → dim (0.96) → skyMatch.logo → prize island → skyMatch.bubble → skyMatch.avatars → skyMatch.tap

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `skyMatch.logo` | 63.4 · 76.7 · 270.2 · 73.4 | — | — | — | top: safe +17.7 | 067 |
| `skyMatch.bubble` | 63.1 · 470.7 · 267.2 · 96.4 | — | head #FFFFFF; body #F8E7D2 | “Finding players on your level.” 17.8/-0.05 fill #FFFFFF · outl #380E66 1.1 · drop 0.7<br>“100/100” 33/+0.56 fill #622200 [med] | centre +92.9 | 067 |
| `skyMatch.avatars` | 24 · 588.2 · 341 · 139.1 | — | — | — | centre +231.8 | 067 |
| `skyMatch.tap` | 113.4 · 774 · 163.5 · 26.7 | — | — | “Tap to Continue” 20.3/-0.77 fill #FCE7D7 [med] | bottom: safe +17.3 | 067 |

### Sky Jump tutorial overlay — `skyTut`

- shots: 068
- dim: `dim.skyMatch` = #000000 at 0.96
- z-order (back → front): skyMap → dim (0.956) → skyTut.* captions + icons → skyTut.tap

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `skyTut.title` | 108.8 · 53.4 · 176.1 · 40 | — | — | “Sky Jump” (no reliable fit) | top: safe -5.6 | 068 |
| `skyTut.avatarFan` | 35.7 · 174.8 · 176.1 · 84.1 | — | — | — | centre -209.1 | 068 |
| `skyTut.c1` | 24.4 · 271.2 · 196.8 · 17.3 | — | — | “Start with 100 players!” 17.8/+0.05 fill #FFD202→#FFCD01→#FFC100 | centre -146.2 | 068 |
| `skyTut.mazeIcon` | 269.6 · 271.9 · 96.1 · 96.1 | rounded r 6.2 | — | — | centre -106.1 | 068 |
| `skyTut.island` | 47.7 · 370 · 154.1 · 130.4 | — | — | — | centre +9.2 | 068 |
| `skyTut.c2` | 260.9 · 380 · 109.1 · 13 | — | — | “Beat 5 levels!” 17.2/-0.02 fill #FFD302→#FFCE01→#FFC401 | centre -39.5 | 068 |
| `skyTut.c3a` | 43 · 509.4 · 170.5 · 19 | — | — | “Win your share of” 19.7/-0.05 fill #FCE7D7 | centre +92.9 | 068 |
| `skyTut.c3b` | 73.7 · 533.5 · 108.8 · 15.3 | — | — | “5000 coins!” 19.9/+0.33 fill #FFD102→#FFCB01→#FFC101 | centre +115.1 | 068 |
| `skyTut.stagesTray` | 42.4 · 582.2 · 309.6 · 60.7 | rounded r 18 | — | — | centre +186.6 | 068 |
| `skyTut.c4` | 28.4 · 658.2 · 335.6 · 16.7 | — | — | “Advance to next stages for greater prizes!” 16.5/+0.09 fill #FCE7D7→#FCE7D7→#FFC301 | centre +240.6 | 068 |
| `skyTut.warning` | 47.4 · 697.9 · 298.9 · 61.1 | rounded r 11.2 | fill #F8E7D2 | — | centre +302.4 | 068 |
| `skyTut.tap` | 156.8 · 782.7 · 79.7 · 10 | — | — | “Tap to Continue” 10.2/+0.24 fill #FCE7D7 | bottom: safe +25.3 | 068 |

### Sky Jump event map — `skyMap`

- shots: 069, 074, 075, 080, 084, 088
- z-order (back → front): sky background (full-bleed art) → islands + numbered pads → skyMap.header < stat plates → skyMap.timerChip → avatars (skyMap.playerAvatar) → skyMap.tap → skyMap.info, skyMap.close

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `skyMap.close` | 332.9 · 49 · 45 · 45 | circle ⌀45 | — | — | top: safe -10.0 | 069 |
| `skyMap.info` | 9.7 · 57 · 30.4 · 30.4 | — | — | — | top: safe -2.0 | 069 |
| `skyMap.header` | 0 · 103.4 · 393 · 103.4 | superellipse n 4.2 (r≈51.7) | frame #5F3AD5; inner #E5A380 | — | top: safe +44.4 | 069 |
| `skyMap.statLevels` | 143.5 · 126.8 · 103.4 · 60.1 | — | — | “Levels” 17.9/-0.04 fill #FFFFFF · outl #622200 1.7 · drop 0.6<br>“0/5” 20.7/+0.67 fill #FFFFFF · outl #622200 1.9 · drop 0.9 [med] | top: safe +67.8 | 069 |
| `skyMap.statPlayers` | 250.2 · 126.8 · 106.8 · 60.1 | — | — | “Players” 17.2/-0.45 fill #FFFFFF · outl #622200 1.7 · drop 0.6<br>“100/100” 19.9/+0.71 fill #FFFFFF · outl #622200 1.8 · drop 0.9 | top: safe +67.8 | 069 |
| `skyMap.statStages` | 40 · 131.4 · 96.1 · 48.7 | rounded r 11.5 | — | “Stages” 18.4/-0.61 fill #FFFFFF · outl #622200 1.9 · drop 0.5 | top: safe +72.4 | 069 |
| `skyMap.levelsValue` | 169.1 · 146.8 · 55.7 · 32.7 | — | — | “1/5” (no reliable fit) | top: safe +87.8 | 080 |
| `skyMap.playersValue` | 270.6 · 146.8 · 70.4 · 28.7 | — | — | “82/100” 19.8/+0.63 fill #FFFFFF · outl #622200 1.9 · drop 0.9 | top: safe +87.8 | 080 |
| `skyMap.playerAvatar` | 262.9 · 579.5 · 71.1 · 69.1 | superellipse n 3.5 (r≈22.9) | — | — | centre +188.0 | 080 |
| `skyMap.padBadge` | 196.8 · 727.6 · 50 · 43 | rounded r 16.1 | — | “1” 28.5/+0.00 fill #FFF5F9 · outl #830031 2.4 [med] | centre +323.1 | 080 |
| `skyMap.tap` | 115.8 · 770.7 · 161.8 · 29 | — | — | “Tap to Continue” (no reliable fit) | bottom: safe +18.3 | 080 |

- `skyMap.info`: same (i) button as Claw Challenge

### Sky Jump stage won — `skyWin`

- shots: 094
- dim: `dim.popup` = #000000 at 0.90
- z-order (back → front): home → dim → skyWin.title → skyWin.island → skyWin.youWin → skyWin.coinPlate < skyWin.amount → skyWin.avatar → skyWin.message → skyWin.winners

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `skyWin.title` | 15.3 · 86.7 · 363 · 46.7 | — | — | “Congratulations!” 45.5/-1.00 fill #FFDD13→#FFC302→#FFB700 · outl #B24900 0.9 · drop 1.8 [med] | top: safe +27.7 | 094 |
| `skyWin.island` | 90.1 · 149.8 · 210.2 · 167.1 | — | — | — | centre -192.6 | 094 |
| `skyWin.youWin` | 132.8 · 349 · 130.1 · 26 | — | — | “You win!” 29.5/-0.03 fill #FFD102→#FFCC01→#FFC201 [med] | centre -64.0 | 094 |
| `skyWin.coinPlate` | 139.1 · 386.3 · 115.8 · 97.4 | — | plate #D41549 | — | centre +9.0 | 094 |
| `skyWin.amount` | 165.1 · 443.7 · 63.4 · 35 | — | — | “367” 29.9/-0.73 fill #FDE7D8 · outl #660100 2.2 · drop 1.1 | centre +35.2 | 094 |
| `skyWin.avatar` | 157.8 · 500.1 · 77.1 · 74.7 | superellipse n 3.5 (r≈24.7) | frame #15E615; placeholder #627F92 | — | centre +111.5 | 094 |
| `skyWin.message` | 35.7 · 593.8 · 321.3 · 41 | — | — | “You are sharing the reward with” 21/-0.22 fill #FDE7D8<br>“6 other winners!” 20.4/+0.17 fill #FDE7D8 | centre +188.3 | 094 |
| `skyWin.winners` | 113.4 · 667.2 · 208.5 · 91.7 | — | — | — | centre +287.1 | 094 |

- `skyWin.island`: prize island + PRIZE sign + chest (3D illustration)
- `skyWin.winners`: fan of winner avatar tiles (blue frames), centre tile largest

### Streak Race leaderboard panel (STORE screenshot 6 — provisional) — `race`

- shots: research/store/iphone-6.png (store, marketing composite)
- z-order (back → front): header art → race.band (blue panel) → race.logo → race.subtitle → race.chips < race.chipLit → race.timerChip → race.row1..3 < rank hex / avatar / name / reward plate / capsule + score pill

| id | frame | shape | fills | text | anchor | shot |
|---|---|---|---|---|---|---|
| `race.logo` | 44.7 · 297.7 · 303.7 · 53.6 | — | — | — | n/a | iphone-6 |
| `race.band` | 0 · 312.6 · 393 · 187.6 | — | fill #1779FA; rivet #3C8AEA; bottomBand #0B2176 | — | n/a | iphone-6 |
| `race.subtitle` | 20.8 · 364.7 · 351.3 · 22.3 | — | — | “Beat levels without fail to get more rewards!” 17.6/-1.12 fill #FFFEFB→#FFF8E9→#FFF1D7 · outl #022880 0.9 [fonts.md] | n/a | iphone-6 |
| `race.chips` | 16.4 · 393.9 · 361.1 · 61.6 | — | cream #622100; divider #F8E7D2 | — | n/a | iphone-6 |
| `race.chipLit` | 162.3 · 401 · 69.4 · 47.9 | rounded r 10 | — | “x10” 31.3/-2.46 fill #FFFDFA→#FFF6E6→#FFEFD0 · outl #005100 1.4 [fonts.md] | n/a | iphone-6 |
| `race.timerChip` | 179.5 · 468.9 · 51.5 · 19.1 | — | — | “23:55” 16.5/-1.34 fill #622100 [fonts.md] | n/a | iphone-6 |
| `race.row1` | 3 · 499.6 · 387 · 73.2 | rounded r 0.1 | fill #FFDA00; fillLow #FFD800; rim #FFF25B | — | n/a | iphone-6 |
| `race.reward1` | 241.2 · 509.1 · 61 · 54.2 | — | — | “3000” 16.3/-1.46 fill #FDE8D8→#FCE7D7→#FCE6D7 · outl #8D0E28 ? [med] | n/a | iphone-6 |
| `race.avatar1` | 55.4 · 509.7 · 51.2 · 50.9 | superellipse n 3.6 (r≈16.1) | — | — | n/a | iphone-6 |
| `race.score1` | 300.7 · 512.1 · 81.9 · 48.2 | — | pill #C15B00 | “16” 22.5/-0.22 fill #FDE8D8→#FCE7D7→#FCE6D7 · outl #622100 1.1 · drop 0.7 [fonts.md] | n/a | iphone-6 |
| `race.rank1` | 10.4 · 515.1 · 44.7 · 42.3 | — | — | “1” 29.1/+0.00 fill #FFF38A→#FDE8D8→#FCE6D7 · outl #8B1E24 2.6 [med] | n/a | iphone-6 |
| `race.name1` | 110.2 · 518 · 80.4 · 36.3 | — | — | “Kate” 24.3/-1.34 fill #622100 [fonts.md] | n/a | iphone-6 |
| `race.row2` | 3 · 571 · 387 · 73.2 | rounded r 0.1 | fill #BAC3EB; fillLow #AFBAE3; rim #EAEDFD | — | n/a | iphone-6 |
| `race.reward2` | 241.2 · 580.6 · 61 · 54.2 | — | — | “2000” 14.9/-0.01 fill #FDE8D8→#FCE7D7→#FCE6D7 · outl #78001D 1.9 · drop 1 | n/a | iphone-6 |
| `race.avatar2` | 55.4 · 581.8 · 51.2 · 51.2 | superellipse n 3.6 (r≈16.1) | — | — | n/a | iphone-6 |
| `race.score2` | 300.7 · 583.5 · 81.9 · 48.2 | — | pill #4F63B8 | “15” 22.4/-1.38 fill #FDE8D8→#FDE7D8→#FCE6D7 · outl #1A336F 1.1 · drop 0.7 [med] | n/a | iphone-6 |
| `race.rank2` | 10.4 · 586.5 · 44.7 · 42.3 | — | — | “2” 28.7/+0.00 fill #CDD6FA→#F4E0D8→#FCE6D7 [med] | n/a | iphone-6 |
| `race.name2` | 110.2 · 589.5 · 80.4 · 36.3 | — | — | “Max” 24.5/-1.34 fill #1A336F [fonts.md] | n/a | iphone-6 |
| `race.row3` | 3 · 642.5 · 387 · 73.2 | rounded r 0.1 | fill #F79753; fillLow #F49548; rim #F6CFB2 | — | n/a | iphone-6 |
| `race.reward3` | 241.2 · 652 · 61 · 54.2 | — | — | “1000” 14.7/-0.07 fill #FDE8D8→#FCE7D7→#FCE6D7 [med] | n/a | iphone-6 |
| `race.avatar3` | 55.4 · 652.6 · 51.2 · 51.2 | superellipse n 3.5 (r≈16.6) | — | — | n/a | iphone-6 |
| `race.score3` | 300.7 · 655 · 81.9 · 48.2 | — | pill #AC3C04 | “12” 22.4/-0.99 fill #FDE8D8→#FCE7D7→#FCE6D7 · outl #622100 1.1 · drop 0.8 [med] | n/a | iphone-6 |
| `race.rank3` | 10.4 · 658 · 44.7 · 42.3 | — | — | “3” 28.6/+0.00 fill #FEDCBC→#FDE8D8→#FCE6D7 · outl #8D121D ? [med] | n/a | iphone-6 |
| `race.name3` | 110.2 · 661 · 80.4 · 36.3 | — | — | “James” 24.6/-1.34 [fonts.md] | n/a | iphone-6 |

- `race.chips`: the 5-chip cream strip x1..x100 incl. the lit chip
- `race.logo`: "Streak Race" lettering + chequered flags (artwork)
- `race.reward1`: coin stack on a red plate
- `race.reward2`: coin stack on a red plate
- `race.reward3`: coin stack on a red plate
- `race.score1`: green capsule icon + score pill
- `race.score2`: green capsule icon + score pill
- `race.score3`: green capsule icon + score pill

## Cross-checks

### fonts.md (sizes) vs this role's glyph-match fit

| component | text | fonts.md size / tracking | glyph-match size / tracking | Δ size |
|---|---|---|---|---|
| `hud.coinPill` | 2240 | 18.5 / +0.25 | 18.4 / +0.40 | -0.5 % |
| `hud.levelTab` | Level 32 | 17.9 / -0.50 | 17.3 / +0.14 | -3.4 % |
| `hud.timerPill` | 3:00 | 23.3 / +0.25 | 23.5 / +0.05 | +0.9 % |
| `hud.levelTabHard` | Level 34 | 17.9 / -0.50 | 17.3 / +0.18 | -3.4 % |
| `hud.timerPillHard` | 3:30 | 23.3 / +0.25 | 23.2 / -0.24 | -0.4 % |
| `hud.levelTabSuperHard` | Level 39 | 17.9 / -0.50 | 17.3 / +0.15 | -3.4 % |
| `hud.timerPillSuperHard` | 3:00 | 23.3 / +0.25 | 23.5 / +0.05 | +0.9 % |
| `home.coinPill` | 2260 | 18.8 / +0.00 | 18.9 / -0.02 | +0.5 % |
| `home.livesPill` | Full | 19.1 / -0.75 | 18.7 / -0.81 | -2.1 % |
| `home.levelCaption` | LEVEL | 14.1 / -1.50 | 14 / -1.22 | -0.7 % |
| `home.levelPlate` | 33 | 30.6 / -1.50 | 30.3 / -2.27 | -1.0 % |
| `home.playButton` | Play | 48.8 / -3.25 | 48.9 / -3.60 | +0.2 % |
| `home.navHomeTab` | Home | 15.1 / -0.25 | 15.6 / -0.57 | +3.3 % |
| `home.levelPlateHard` | 34 | 30.6 / -1.50 | 30.1 / -1.26 | -1.6 % |
| `home.playButtonHard` | Play | 48.8 / -3.25 | 48.9 / -3.60 | +0.2 % |
| `home.levelPlateSuperHard` | 39 | 30.6 / -1.50 | 30.3 / -1.15 | -1.0 % |
| `home.playButtonSuperHard` | Play | 48.8 / -3.25 | 48.9 / -3.60 | +0.2 % |
| `home.coinPillL32` | 2240 | 18.8 / +0.00 | 18.8 / +0.15 | +0.0 % |
| `home.livesPillL32` | Full | 19.1 / -0.75 | 18.7 / -0.81 | -2.1 % |
| `pause.ribbon` | Paused | 49.2 / -1.00 | 48.9 / -0.95 | -0.6 % |
| `pause.toggleSound` | ON | 21 / -0.75 | 20.8 / -0.19 | -1.0 % |
| `pause.toggleHaptic` | ON | 21 / -0.75 | 21.1 / -0.87 | +0.5 % |
| `pause.iconSound` | Sound | 25.5 / +0.00 | 25.4 / +0.03 | -0.4 % |
| `pause.iconHaptic` | Haptic | 25.2 / -0.25 | 25.3 / +0.14 | +0.4 % |
| `pause.resume` | Resume | 27.2 / -1.00 | 27.7 / -1.57 | +1.8 % |
| `pause.quit` | Quit | 30.5 / -0.50 | 30.1 / -0.46 | -1.3 % |
| `loading.label` | Loading | 26.8 / -0.50 | 26.2 / +0.01 | -2.2 % |
| `race.subtitle` | Beat levels without fail to get more rewards! | 17.6 / -1.12 | 16.6 / -0.26 | -5.7 % |
| `race.chipLit` | x10 | 31.3 / -2.46 | 31.4 / -2.71 | +0.3 % |
| `race.name1` | Kate | 24.3 / -1.34 | 24.8 / -2.07 | +2.1 % |
| `race.score1` | 16 | 22.5 / -0.22 | 22.4 / -0.21 | -0.4 % |
| `race.name2` | Max | 24.5 / -1.34 | 24.6 / -1.57 | +0.4 % |

Tracking differs more than size (±0.6 pt typical): the glyph-match tracking comes from the ink span between the first and last glyph, fonts.md's from the best line IoU. fonts.md values are used in the tokens wherever it measured the label.

### art/STYLE.md §D palette — re-sampled at the same spots

| STYLE token | shot (x, y) px | STYLE | re-sampled | ΔRGB |
|---|---|---|---|---|
| hud.coinPill.fill | 003 (305, 140) | #BDDCFF | #BDDCFF | 0.0 |
| hud.squareButton.face | 003 (1080, 300) | #008CFE | #008CFE | 0.0 |
| hud.panel.fill | 003 (760, 335) | #BDDCFF | #BDDCFF | 0.0 |
| hud.timerPill.fill | 003 (540, 300) | #6C94DC | #6C94DC | 0.0 |
| hud.levelTab.fill | 003 (470, 196) | #008EFE | #008EFE | 0.0 |
| hud.heart.face | 003 (660, 275) | #FB3A2A | #FB3A2A | 0.0 |
| booster.tray.fill | 003 (20, 2380) | #BDDCFF | #BDDCFF | 0.0 |
| booster.green.face | 003 (64, 2330) | #00E400 | #00E400 | 0.0 |
| booster.badge.red | 003 (172, 2432) | #FF4344 | #FF4344 | 0.0 |
| panel.frame.blue | 007 (70, 1300) | #005DEC | #005DEC | 0.0 |
| panel.inner field | 007 (589, 1421) | #226DF5 | #226DF5 | 0.0 |
| panel.ribbon.top | 007 (589, 640) | #FFCF00 | #FFCF00 | 0.0 |
| panel.ribbon.bottom | 007 (589, 790) | #FFB800 | #FFB800 | 0.0 |
| panel.cream.fill | 007 (589, 1152) | #F8E7D2 | #F8E7D2 | 0.0 |
| panel.toggle.green | 007 (640, 1070) | #00E500 | #00E500 | 0.0 |
| panel.toggle.knob | 007 (890, 1030) | #009EFC | #009EFC | 0.0 |
| panel.close.red | 007 (1040, 770) | #FF3C3D | #FF3C3D | 0.0 |
| panel.scrim | 007 (589, 2048) | #1C1C1C | #1C1C1C | 0.0 |
| home.play.face | 002 (330, 2060) | #00D300 | #00D300 | 0.0 |
| home.levelPlate.green | 002 (470, 1660) | #05D001 | #05D001 | 0.0 |
| home.topPill.fill | 002 (590, 200) | #DEEEFF | #DEEEFF | 0.0 |
| home.gearButton.face | 002 (1024, 173) | #0191FF | #0191FF | 0.0 |
| home.nav.blue | 002 (55, 2364) | #0592FE | #0592FE | 0.0 |
| home.nav.homeTab | 002 (436, 2364) | #11D5FF | #11D5FF | 0.0 |

All 24 STYLE §D spots reproduce within ΔRGB ≤ 3 (same method). Frames vs STYLE §B.1: square HUD button 40 × 40 pt ✓, wide popup button 125 × 89 pt ✓ (after including the 1 pt outline), HUD heart: 28.7 × 24.4 pt here = the red body only; STYLE's 29.3 × 25.3 includes the 0.53 pt outline and halo ✓.

### research/flows.md tap points vs measured centres

| flows.md | component | measured centre | Δ (pt) |
|---|---|---|---|
| back button (38,88) | `hud.backButton` | (39, 88.4) | 1.0, 0.4 |
| pause (352,88) | `hud.pauseButton` | (354.5, 88.1) | 2.5, 0.1 |
| left booster (40,790) | `booster.buttonLeft` | (43, 792.2) | 3.0, 2.2 |
| right booster (352,790) | `booster.buttonRight` | (350.3, 792.2) | -1.7, 2.2 |
| Resume (123,530) | `pause.resume` | (122.9, 530.6) | -0.1, 0.6 |
| Quit (269,530) | `pause.quit` | (269.1, 530.6) | 0.1, 0.6 |
| pause X (361,256) | `pause.close` | (361.3, 256.7) | 0.3, 0.7 |
| Out of Time X (350,76) | `outOfTime.close` | (350, 75.6) | 0.0, -0.4 |
| Continue X (362,238) | `continueStreak.close` | (362.5, 237.4) | 0.5, -0.6 |
| Failed X (362,229) | `failed.close` | (361.3, 229.7) | -0.7, 0.7 |
| win Continue (196,538) | `win.continue` | (196.7, 541.5) | 0.7, 3.5 |
| win X (361,207) | `win.close` | (361.3, 207.7) | 0.3, 0.7 |
| Claw (i) (27,70) | `claw.infoButton` | (24.9, 72.2) | -2.1, 2.2 |
| Claw X (357,72) | `claw.close` | (355.5, 71.6) | -1.5, -0.4 |
| Play (196,668) | `home.playButton` | (196.7, 671.6) | 0.7, 3.6 |
| shop tab (68,805) | `home.navShop` | (68.4, 807.4) | 0.4, 2.4 |
| trophy tab (325,805) | `home.navTrophy` | (324.4, 809) | -0.6, 4.0 |

All within 4.0 pt — the flows.md points were tap targets (eyeballed), the table gives the measured component centres.

### Disagreements and flags (for the SPEC-ui writer)

1. **"Hard Level" tag in the HUD — not on the phone.** The task brief, PLAN.md and art/STYLE.md §E list a red "Hard Level" tab in
   the level HUD; that tag is only in store screenshot 2 (an older build; fonts.md measured it there). On the phone (v552, 036 L34 Hard,
   061 L39 Super Hard) the HUD shows the normal **"Level 34" tab recoloured red** (`hud.levelTabHard`, fill #FF3C3D) or purple
   (`hud.levelTabSuperHard`, #A628E7), the back/pause buttons recoloured, and the **timer pill stays blue** (#6C94DC in all three). The
   "Hard Level" / "Super Hard" ribbons exist on the home Play button (`home.hardRibbon`) and above the win popup (`winHard.tagRibbon`).
   Phone wins (source precedence).
2. **fonts.md vs glyph-match sizes**: HUD level tab 17.9 vs 17.3 (−3.4 %), store subtitle 17.6 vs 16.6 (−5.7 %), Home tab 15.1 vs
   15.6 (+3.3 %); all others within ±2.2 %. Tokens use fonts.md.
3. **Ribbon titles auto-size**: "Paused" 49.2, "Level 32" 49.0, "Continue?" 46.6 pt on the same 274 pt ribbon — like the
   Resume/Quit pair (fonts.md: TextMeshPro auto-size, INFERRED). Use one style with max ≈ 49 pt that shrinks to fit (EN and TR).
4. **Two different dim strengths**: most popups 0.89–0.90 black (STYLE §D scrim agrees: #1C1C1C over white = 0.89), but Out of Time is
   **0.94** and the Sky Jump matching/tutorial overlays **0.96**. Not one global scrim.
5. **Hearts are not in the timer pill** (PLAN.md wording): they sit in the HUD panel right of the pill (`hud.heart1..3`, 28.7 × 24.4 pt,
   36.1 pt pitch).
6. **Hidden edges**: the tops of the popup panels (under the ribbon) come from the superellipse fit (INFERRED); the Sky Jump panel top
   (under its logo) from the corner arc (INFERRED); every other edge is measured.
7. **Text fits rejected** (implausible size/tracking; ink boxes kept, use the role style): `skyMap.levelsValue` on 080 (the plate rim
   pollutes the outline; use 069's "0/5" = 20.7 pt — `skyMap.playersValue` 19.8 pt on 080 agrees with 069's 19.9), `skyMap.tap` (light face
   on light clouds; same style as `skyMatch.tap` 20.3 pt), `race.timerChip` (fonts.md 16.5 pt used), `home.clawMultTray` "x10",
   `home.skyJumpBadge` timer, `skyTut.title` (event-logo lettering, not live text).
8. **Captions on the dim** (`clawInfo.*`, `skyTut.*`, `skyWin.message`) were fitted on the face by luminance: sizes are good, but the
   outline widths were not measurable (dark outline on a near-black dim). Use `role.caption` (outline ≈ 1 pt navy #172B5A, yellow words
   #FFD102 with #580700).

### Screens NOT captured yet (for the meta explorer / SPEC-ui writer)

Priority first. "web" = only the web-research video frames (July/Aug builds, research/web) exist — look, but capture v552 on the phone.

1. **Leaderboard (trophy tab)** — Weekly / World / Country tabs, rank rows, own-row highlight (web, July). The owner wants a simulated
   online leaderboard with country + global boards: this is the most important missing screen.
2. **Streak Race full panel on the phone** (tap the home chequered-flag badge): only store screenshot 6 is measured here (section
   `race`, provisional). Also its results/claim popup and the "race ended" state.
3. **Settings** (home gear): Notifications, Sound, Music, Haptic toggles, Support, Terms, Privacy (web, July).
4. **Shop** (basket tab) + the coin "+" entry: special offer + bundles (web, July). Ours has no real purchases (owner's rule), but the
   screen layout is needed.
5. **Profile / avatar picker / name entry** (avatar button, web July: 3 × 3 portraits, name field, Save; Profile stats).
6. **Lives**: tap on the lives pill; out-of-lives popup (refill / wait timer); the lives countdown with a number (store 7 shows "4" +
   "23:46" — the phone only showed "Full" and the ∞ timer).
7. **In-level states**: a lost heart (empty heart look), the wrong-tap bump, low-time warning (does the timer turn red?), booster use
   (freeze overlay on the timer, hint highlight on an arrow), booster count 0 → buy popup, booster unlock intro.
8. **Pause → Quit** confirmation popup and what it costs.
9. **Continue accepted** (coins spent, +30 sec resumes) and not-enough-coins → shop.
10. **Other feature-unlock popups** (only "Pipe!" is captured): tape/linked arrows, corners, doors + keys (the phone saw no popup at
    L33), elevators…; the L1–31 tutorial overlays (hand pointer + captions) — video only (INFERRED).
11. **Hard / Super Hard level-start splash** (if any — the phone shots go from home straight to the board; confirm on a recording).
12. **Claw Challenge**: claimed/unlocked ladder nodes, a mid-ladder reward popup other than ∞ lives / coins, event end.
13. **Sky Jump**: failure popup ("you failed the challenge"), (i) info content, stage 2/3 maps, the home badge in each state.
14. **Loading between home and level** (none seen), app launch screen, and the TR version of every label (the original's game UI stayed
    English on the Turkish phone, so TR string lengths are untested: every TR label must fit the frames above — auto-shrink like the
    original).
15. iOS prompts (notification, rating) are system UI: noted in `ios.*`, not built.

### Limits of this measurement (honest list)

- One device class (iPhone 15, 393 × 852 pt). Anchoring rules are INFERRED; if the build targets other sizes, anchor top-bar/HUD items
  to the safe-area top, the nav bar/booster corners to the screen bottom, popups to the centre, and keep the pt sizes (the store
  screenshots on a 440 pt canvas scale the UI with the screen WIDTH: ×440/393 — fonts.md timer check — so a width-proportional scale is
  the alternative; decide in SPEC-ui).
- Gradients are single clean columns (+ cross-sections); horizontal shading of wide plates is only in the xsecs and crops.
- 3D artworks (logos, Claw header, Sky Jump islands, broken hearts, coin stacks, nav icons) are measured as bounding boxes only; their
  art is the art lanes' job (our own designs; the "ARROW OUT!" logo replaces the original's lettering at the same frames).
- The `race` section comes from a marketing composite scaled by width (pt = px × 393/1320); only sizes and positions INSIDE the panel
  are meaningful, and it may be an older build.

### Files

- `design/ui-tokens.json` — everything above, machine-readable (`components`, `textStyles`, `gradients` incl. `xsec.*`, `radii`,
  `shadows`, `dims`, `palette`, `colors`, `screens` with z-order, `crosschecks`).
- `design/ui-crops/<screen>/<component>.png` — reference crops (look only).
- `design/ui-crops/_tools/` — `mlib.py` (helpers), `measure.py` (declarative component measurement), `m_hud.py`, `m_home.py`,
  `m_popups.py`, `m_events.py` (first pass), `m_extra.py` (second pass: fixes, new screens, store-6), `build_tokens.py`, `gen_md.py`,
  `textcheck.py` (text-fit overlay sheet), `grid.py` / `prof.py` (coordinate grids, colour profiles), `ctmeasure.swift` (CoreText ink
  bounds; build: `swiftc -O ctmeasure.swift -o <scratch>/ctmeasure`, path in `mlib.CTMEASURE`), `out/*.json` (raw per-pass results).

