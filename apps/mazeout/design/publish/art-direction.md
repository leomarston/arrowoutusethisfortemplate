> **OWNER PRINCIPLE 2026-09-28 06:27 (SPEC.md ruling 46 — governs everything below):** keep the feel, animations, layouts and composition 1:1 (the proven
> concept); make only the MINIMUM changes needed to be safely distinct (new characters, D1 palette, green OUT! sign, simple arrow icon, names). Where this
> doc proposes a new theme/scene/layout (e.g. a "burrow" backdrop), scale it back: same composition and object types, restyled just enough to pass copygate.

> **OWNER OVERRIDE 2026-09-28 06:17 (SPEC.md ruling 44 — read before anything else):** keep the WIN LOGO's current art and animation — do NOT restyle it,
> do NOT change its font; ONLY recolour the OUT! sign background (logoSignPurple + bends) to a D1-fitting GREEN. Boss v2 gets **EARS, not horns**.
> Palette / pause menu / crew are approved. **ICON IC-1 is REJECTED (ruling 45): simple glossy 3-D arrows like the category leaders, no character/scene; the owner picks from new options.**

# Arrow Out — Art Direction v2 + copy-distance audit (PUBLISH items 1, 4, 11, 15)

2026-09-28 · phase P1 (investigate + plan). Nothing was rendered, built or edited in App/**, Packages/**, Tests/**, UITests/**;
no simulator, no phone. The only computation was one low-priority Python pass over existing PNGs (six 98-px thumbnails) to
calibrate the copy-distance numbers in §2.1.

**Evidence tags.** **VERIFIED** = I saw it in a file, shot, render or code during this pass (path given). **INFERRED** = my
reasoning, estimate or proposal. It is unproven until a render or device check confirms it.

Sibling doc: `design/publish/events.md` (events catalog + rotation) owns event **names** (its §7.3) and the new Balloon event.
This doc owns how every event **looks**.

---

## 0. TL;DR

1. **Copy distance today (VERIFIED).** Almost everything a reviewer sees was built to *match* the original. The art lanes graded
   themselves on "a player takes it for the same art". Seven families are **HIGH** risk:
   - the workers (1:1 designs, recoloured);
   - the pink boss (the same design, lab coat, lanyard, badge and pen, recoloured);
   - the 8 avatars;
   - the home scene;
   - the Loading screen;
   - the "ARROW OUT!" logo: the same blue arched sign, yellow letters, pegs and purple arrow sign, with only the word changed;
   - the app icon: three glossy red/yellow/blue arrows on white, its colours k-means-sampled from their store icon.

   Also HIGH: the popup and page chrome (in-place ΔE00 3.9–5.2 vs theirs) and the event headers. Measured on thumbnails: our home
   vs theirs has a chroma-histogram overlap of 0.84, and our Paused popup vs theirs has SSIM 0.93. Unrelated screens score
   0.13–0.51 and 0.12–0.18 (§2.1).
2. **Why the workers read as "dough" (VERIFIED in `char_worker.py` vs `char_scientist.py`).**
   - One glossy clearcoat material covers body, arms, hands and feet.
   - Every limb is smooth-unioned into the body in the body colour.
   - The body is an egg with no head/body hierarchy.
   - The eyes are googly bulbs with floating capsule brows.
   - A 4 200-lux warm rim turns the edges into wet candy.
   - There is zero meso-detail.

   The scientist is "art" because of: strand fur (~1.4 M triangles) with per-strand tone; three contrasting materials; a
   constructed garment (coat shell, facings, collar, pocket, lanyard); socketed eyes with fur lids and brows; and a silhouette
   broken by tufts (§1). Those differences become the **A-bar craft rules** (§1.3).
3. **Three original directions (§3).**
   - **D1 "Burrow Works"**, *recommended*: velvet-furred mint "Digger" critters with hard hats. A timber-and-lantern burrow
     workshop, where the tunnels are mazes. Teal and tangerine UI.
   - **D2 "Wind-up Workshop"**: enamel tin wind-up robots. A toymaker's attic with a big clock, whose hands are our arrows. Mint,
     brass and tomato UI.
   - **D3 "Feather Post"**: cream puffball bird couriers. A rooftop sorting loft at sunrise. Coral UI with light pages.

   Every direction keeps the pink fur boss the owner loves and changes the details that make him the original's scientist:
   horns, a blush muzzle, amber eyes, a snaggle tooth, a new outfit instead of the lab coat, lanyard, badge and pen, and a new
   station.
4. **Owner item 4 (VERIFIED cause).** The element is `homeArrowPileFull/Half/Low`, drawn by `ArrowPileView` in
   `App/Shell/Home/HomeScene.swift`, inside `homeCapsuleMachine`.
   - `scene_home.py:pile_layout` places 24 arrows by random jitter with **no penetration test**. The render shows arrows passing
     through each other.
   - The refill drops nine 2-D sprites, rotated at random so their baked light rotates too, in front of the heap.

   Replace the heap with a **mounted centrepiece** in which every arrow has its own peg, slot or hand, so they can never
   intersect: D1 the Signpost, D2 the Wind-up Clock, D3 the Pigeonholes. A pairwise-overlap gate applies to any 3-D arrangement
   (§4).
5. **Icon (§5).** Three 3-D concepts, none on white and none a three-arrow row:
   - IC-1 *"Out the Door"*, recommended: one chunky arrow bursting out of a maze-block doorway, with a Digger riding it, on a
     teal ground;
   - IC-2 *"Peek"*: a character-forward close-up;
   - IC-3 *"Boss Grin"*: a fur close-up. It is the most mascot-like, but has medium similarity risk.
6. **Logo (§6).** Keep the measured motion by keeping the layer contract:
   - a top plate holding five letter layers (A R R O W);
   - pegs or hangers;
   - an elongated bottom sign that bends and wobbles;
   - four OUT! glyph layers.

   Change shape, material, colour and typeface. There is one option per direction, and LOGO-SPEC's tables are regenerated, not
   re-measured.
7. **Production (§7).** About 250 manifest ids are touched:
   - about 60 redesigned: characters, avatars, scenes, logo parts and the icon;
   - about 70 reskinned: board obstacles, unlock icons, badges and nav icons;
   - the SwiftUI chrome by a palette codemod over 1 572 hex literals in 57 Swift files plus ui.json.

   D1 costs about 75 min of render wall time per full pass (about 3–3.5 h with three iteration rounds). **No renders until the
   perf agent's timing ends.** The first thing to render is the owner's **concept pack**: per direction, a boss-v2 head, a crew
   hero, an icon draft, a popup in the new palette and a logo sketch (about 10 min of drafts).

---

## 1. The owner's words and what they bind (verbatim extracts, PLAN.md "OWNER 2026-09-28")

- 1: "…the colorings, the screens, the characters, the loading screen … the pink monster needs some differences, not major things,
  but we should be able to say they are not copied … those small blue monsters … look like made of dough, while the pink monster is
  actually an art, I want them to be art as well, and also differnt then the original maze out characters"
- 4: "The arrows under the pink moster are going in to each other etc, maybe we should make sth else there, but still sth that will
  actually be looking good and our games style."
- 11: "make a good icon, LIKE ACTUALLY sth like the mazeout, and not a svg ai slop, just like the art we have in our game. Make sure
  the design is not copied from mazeout. Never mention mazeout in our description or keywords ever."
- 15: "the art is not same so we can actually publish, but it should at the same time feel like same quality level game."
- SPEC.md ruling 37(b) makes all of these ORIGINAL at the same quality: every character (art-grade like the pink scientist, not
  dough), the pink boss (clearly different), the home scene, the Loading screen, the palette of the screens, the icon, and the
  event art. It keeps rules, level logic, systems, timings and FEEL 1:1.

### 1.1 Why the pink scientist is "art" (A) and the blue workers are "dough" (B) — concrete

Sources, VERIFIED:
- `art/pipeline/items/char_scientist.py` and `char_worker.py`;
- `char_kit.py` and `char_fur.py`;
- renders `art/out/char_sci_home@3x.png`, `char_wk_homeL_blue@3x.png`, `char_wk_homeR_blue@3x.png`;
- the composed home `build/fixa1/shots/v11-home.png` and loading `build/compare/captures/loading-en.png`.

| trait | scientist (reads as ART) | workers (read as DOUGH) |
|---|---|---|
| **Surface / meso-detail** | Real strand fur: 40 k head strands + 420 crown strands + brow fur + 5–11 k per hand, clumped toward guide strands (`FUR.strands(... clump=0.55, per_clump=16, jitter=0.18)`). Head ≈ 560 k triangles, whole character ≈ 1.4 M. Each strand is toned root→tip through a 3-row LUT with ±0.06 jitter, so the silhouette is fuzzy and the interior streaky, with micro-shadowing. | One continuous marching-cubes surface. No texture, no fibre, no pores, no seams. The only "detail" is the belt kit, and it is smooth too. |
| **Material contrast** | Fur (rough 0.60), matte coat cloth (`coatm` rough 0.66), shirt 0.70, glossy eyes 0.15–0.20, metal pen clip, emissive glints: at least 5 roughness classes, each with its own reason. | `body_mat`: rough 0.36 + **clearcoat 0.25** over body, arms, hands, feet and lids alike (`Part("armL", ..., bm)`, `lids ... bm`). Shorts and belt are separate, but they are offset shells of the same egg (`clothes()` = `b.offset(0.032)`), so they read as painted on. |
| **SDF blending** | Limbs change material at the wrist: a coat sleeve → a separate cuff (`round_cone`) → a fur mitt. The fur hides every join, and the cuff edge breaks the silhouette. | `union(a, h, k=0.04)` arm + hand, `union(skin, *legs, k=0.05)` legs into body, `K.hand(... k=0.25)` fingers melted into the palm. Every limb grows out of the body **in the body colour with a soft fillet**, which is exactly what squeezed dough looks like. `round_cone` tubes of near-constant radius (0.135 → 0.11) read as noodles. |
| **Silhouette / mass hierarchy** | A revolved head profile with jowls and cheek fullness (`_profile`, `cheeks`). Cheek and crown tufts break the outline. A big head sits on a separate bell-shaped coat torso, with small hands: three clear masses. | `bean()` = two ellipsoids smooth-unioned at k 0.42 = an egg. No neck, no head/body split, the face painted on the torso. Arms stick out of an undifferentiated oval. |
| **Subsurface / rim** | The CHAR_LIGHT rig: key 1 730 lx, cool rim 1 080 lx, warm fill 375 lx (fakes the warm SSS). Obscurance-driven fur LUT: creases deeper and more saturated, tips lighter. The rim is secondary to the form. | `WORKER_LIGHT_HOME`: a **4 200-lx warm orange rim** (plus clearcoat) on a saturated azure LUT. The whole outline glows hot orange, and thin parts (hands, feet) go pale cyan, like jelly or gummy candy. The owner's "dough". |
| **Eyes** | Set IN sockets (`skin.subtract(F["sockets"].offset(-0.02))`), fur combed away around them, brows of the body's own dark fur, lids as fur-covered shells (half / closed), violet iris, 2 glints. | Big white ellipsoid bulbs pushed out of the egg, a black lid tube, and **floating black capsule brows** (`capsule(... 0.055)` above the eye). Googly-eye stickers. |
| **Proportions** | Head 1.33 u wide on a torso 1.6–2 u wide, arms that reach the console, mitts about 0.35 of the head width. Adult "boss" proportions. | 1.9 u egg, stub arms, stub legs (`leg_foot` capsule r 0.12 → blob foot), 4-finger mittens: a toddler blob. |
| **Colour ladder** | Pink ladder `#FFA8C8 … #B22470` (6 stops) at the reference's S/V distribution: lit S ≈ 0.6, shadows deeper and more saturated. | Azure ladder `#A6E6FF … #0A3CA8`. Lit S is high over a very large area, on a royal-blue lab: the colour has to shout to separate. |
| **Garment construction** | Coat = shell with an opening + raised facings + collar flaps + neckband + pocket + pen + lanyard V + badge + photo + clip. Real thicknesses and edges. | Shorts/belt = slices of the body offset. No hems, folds or thickness. |

The lanes' own notes agree (VERIFIED, `art/lanes/characters.md` and `art/STYLE.md` §C.4 "Known gaps"). The worker has "no
subsurface scattering or ambient occlusion … hands are lumpy mittens; no fabric weave … face less expressive". The director
graded every worker B, and the carrier "legs are the body colour and blobby".

### 1.2 What the owner means by "art" (INFERRED from 1.1)

"Art" is the scientist's formula:

1. a surface with fibre-scale detail whose shading carries micro-occlusion;
2. regions of different materials that meet at constructed edges;
3. a silhouette with hierarchy and breakups;
4. eyes that sit in the face;
5. a controlled saturation ladder under a restrained rim.

Every new character must hit all five.

### 1.3 The A-bar craft rules (binding for the new characters; INFERRED, to be confirmed by the owner on the concept pack)

- **R1 Meso-detail.** The main mass carries fibre or a crafted surface. Options:
  - strand fur (the proven A route): long (boss), velvet (short, dense) or down (clumped tufts);
  - painted enamel with edge wear and decals (hard-surface route; §3.2).

  Never a bare smooth LUT surface on more than 40 % of the silhouette.
- **R2 Material boundaries at joints.** No body-coloured limb is smooth-unioned into the torso without a fur cover, cuff, glove,
  boot or ball joint. `union(..., k)` is allowed only inside one material.
- **R3 Three or more materials** per character with roughness 0.15–0.75 spread (fur/fabric, gloss eyes, metal/leather/plastic
  accessory). **No clearcoat** on fur, felt or velvet.
- **R4 Eyes in sockets** with lid shells (open/half/closed/wink for the rig), brows made of the character's own fur/material, and
  2 glints. No floating brows.
- **R5 Silhouette.** A distinct head mass or a strong secondary shape (ears, snout, horns, dome, crest). At 1/3 size the
  thumbnail must identify species and pose.
- **R6 Light.** The CHAR_LIGHT rig family: rim ≤ 1.5 × fill-adjusted key (≤ 1 400 lx at the current key), warm fill for fake SSS,
  a per-direction room environment map (§7.4). Separation from the backdrop comes from value and hue planning, **not** from a hot
  rim.
- **R7 Constructed garments.** Shells with openings, edges, facings, straps and buckles — never a body offset slice.
- **R8 Rig contract unchanged** (`App/Resources/Tuning/ui.json puppet`, VERIFIED: boss layers `torso`, `armL`, `armR`,
  `armR_point`, `head` group (`headSmile`/`headOpen`), `lids` overlays; crew groups `body` (mouth smile/open), `eyes`
  (open/half/closed[/wink]), `armL`, `armR`, `whole`, pivots `feet`, `neck`, `shoulder`, `eyes`). The rig proof must pass: mean ≤
  2/255, ≤ 1 % px > 40, idle-extreme holes = rest holes. New animated parts (ears, a wind-up key, a tail) are optional extra
  layers with their own ui.json tracks (motion owner).

---

## 2. Copy-distance audit

### 2.1 Method and calibration (VERIFIED numbers, INFERRED thresholds)

Metric: 98-px-wide thumbnails, Gaussian blur 1 px, then (a) SSIM on luma and (b) the overlap of the a\*b\* chroma histograms
(16×16 bins over ±80). This is a crude "does it look like the same screen at a glance" test.

| pair | SSIM | chroma overlap | reading |
|---|---|---|---|
| our Paused popup vs 007 | **0.928** | **0.879** | a copy |
| our home (v11) vs 002 | **0.527** | **0.838** | a copy (SSIM held down by our Claw bar and the Dynamic Island) |
| our Loading vs store 8 | **0.473** | **0.672** | a copy |
| CONTROL 002 home vs 069 Sky Jump (same game, other screen) | 0.183 | 0.401 | unrelated |
| CONTROL 002 home vs 003 board | 0.121 | 0.132 | unrelated |
| CONTROL our home vs our loading | 0.145 | 0.513 | unrelated |

Also VERIFIED, from `art/STYLE.md` §B.2:
- the chrome was tuned to in-place ΔE00 3.87–5.15 vs theirs;
- the REVIEW grades say "covers the original exactly" for the doors, tapes, pipes, locks and keys;
- the app icon's arrow colours were "k-means share" of `research/store/icon-1024.png` (`3d-hud_arrows.py ICON_SHADES`).

**Copy-distance gate (proposed; recalibrate on the concept renders).**
- **Screens with art** (home, Loading, event headers): SSIM < 0.30 **and** chroma overlap < 0.55 vs the original's matching
  screen.
- **Popups/pages:** chroma overlap < 0.55, and the chrome face/rim ΔE00 > 25 from theirs. Centred-panel structure is a genre
  constant, so SSIM stays informative only.
- **Characters:** silhouette IoU < 0.55 vs the original character's alpha mask at the same placement, and mean body ΔE00 > 30.
- **Logo and icon:** silhouette IoU < 0.60 and a different dominant hue pair.

The tool lives in `art/review/tools/copy_gate.py` (to write in phase P). It uses research shots as **references to LOOK at**
only, as today.

### 2.2 The audit (every element a reviewer could call copied)

Risk = how likely App Review (guidelines 4.1 Copycats / 5.2.1 IP) or a complaint from the original's publisher could point at
it. This is a practical judgement (INFERRED), not legal advice.

| # | element (ids / where) | what is the same today (VERIFIED) | risk | fix (→ §) |
|---|---|---|---|---|
| 1 | **Workers**: `workerWalkie`, `workerClipboard` (home rigs), `workerCarrier`, `workerFlyer`, `workerFist`, `workerRunners`, `workerCrowdLeft` (loading), `workerClawPair`, `workerRacers` (events) | "the ORIGINAL's designs reproduced 1:1 … only their COLOURS changed" (`characters.md`): capsule bean, black lid lines + floating brows, navy cap + walkie, green cap + square glasses + clipboard + pencil, indigo shorts, brown belt, lilac buckle + wrench, the same poses and placements (placed "by the eye whites on 002 / store 8") | **HIGH** | new species per direction (§3) |
| 2 | **Boss**: `scientist` rig, `scientistLoading`, `avatarScientist` | Same design recoloured purple → pink (ΔE00 18 between the body tones): furry dome, eye/brow shapes, crown tuft, white lab coat + blue shirt + lanyard + ID badge + purple pen in the pocket, hands on a console with a joystick and a lever; the loading "run" pose with a fist and arrows | **HIGH** | boss v2 (§3.0): keep the pink fur face; change the silhouette (horns), muzzle, eyes, tooth, outfit, station and pose |
| 3 | **Avatars**: `avatarWalkie/CapGlasses/Detective/Burger/Scientist/Party/Notebook/BoxHead` | Their v552 portrait set recoloured (detective with deerstalker + moustache, burger eater, party hat, box head …) | **HIGH** | 8 new portraits of the new cast (same count: the social engine maps 8 + default) |
| 4 | **Home scene**: `homeBackdrop`, `homeConsole`, `homeCapsuleMachine`, `homeArrowPile*`, `homePlatform` + layout | Measured from 002 and placed at 002's coordinates: tank wall, striped pipes, valve wheel, vents, console (joystick, buttons, lever, green dome), capsule machine with arrow heap, glass dais. Chroma overlap 0.84 | **HIGH** | new world + asymmetric composition (§3) + item-4 centrepiece (§4) |
| 5 | **Loading**: `loadingBackdrop` + `char_loading_layout.json` | Store 8 1:1: logo top-left, a flyer with a red arrow top-right, the boss running with arrows at centre, the box carrier front-left, the glasses worker front-right, a crowd right, a conveyor left, a tiled floor + cable, "Loading.." bottom | **HIGH** | new composition per direction (§3) |
| 6 | **Logo** "ARROW OUT!": 40 `logo*` parts, `logoArrowOut`; win celebration + Loading | Blue arched rounded sign with a white rim, **yellow letters with orange extrusion**, two grey pegs, a **purple arrow-shaped sign pointing right** with **white "OUT!"**, the same 2-tier layout; only the word differs. The same OFL match of their typeface. Name pattern "___ OUT!" | **HIGH** | §6 restyle; optional drop of "!" (owner) |
| 7 | **App icon** `appIcon` | Three long-shaft glossy block arrows (blue/yellow/red) on a white ground, running off the edges; shades sampled from their store icon | **HIGH** | §5 |
| 8 | **Popup chrome**: `panelFrame`, `panelRibbon`, `panelCream`, `panelClose`, `buttonGreen/Red/Purple`, `toggleOnOff`, `unlockCard` (SwiftUI) | Blue riveted frame + yellow arched ribbon + red X disc + cream inset + green/red glossy pills, same superellipse exponents, ΔE00 3.9–5.2 in place | **HIGH** | palette + shape shift (§3 tokens, §7.3 codemod) |
| 9 | **Full-screen pages**: Settings, Profile, Edit Profile, Leaderboard tabs, Shop, Terms | Dark royal-blue pages with the same cards, tabs, round toggles, podium | **HIGH** | same codemod + page background per direction |
| 10 | **Event headers/scenes**: `clawHeaderArt`, `workerRacers` (Streak header), `rocketRaceBackdrop`, `rocketOfferScene`, `skyJumpBackdrop/Island*/Pad/PopupScene`, `leaderboardPodium` | Each rebuilt from a v552 screen (023, meta-045, 167, 163, 069, 065, meta-013): the same compositions | **HIGH** (with characters) / **MED-HIGH** (props only) | redraw in the chosen world; names per events.md §7.3 |
| 11 | **Board obstacle skins**: `tape*` (6), `door*` (9), `lockHex`, `keyOnArrow`, `pipeMouth`, `pipeCounter`, `pipeTube` (code), `boxSlab`, `boxRing`, `corner*` (9), shards | Pink tape with two crossing straps; orange-framed door with a purple inner frame, blue slatted shutter and gold rivets; purple hex lock; gold key with a purple ribbon; cyan pipe with gold collars and an orange counter; violet box + silver sphere ring; red plate on a blue spring. Graded A because they "cover the original exactly" | **MED-HIGH** (they appear in every gameplay screenshot) | reskin per direction, rules and hit geometry unchanged (§3) |
| 12 | **Unlock cards**: `unlockIcon*` (7) + copy "Box! / Unlocked! / Clear required amount of arrows to break the BOX!" etc. | Same icons and the same wording | **MED** | icons follow the obstacle reskin; rewrite the card lines (strings lane) |
| 13 | **HUD**: `hudPanel`, `hudTimerPill`, `hudLevelTab`, `hudBackButton`, `hudPauseButton`, `hudCoinPill`, `boosterButton`/`Badge` | The same skins, colours and positions (timer pill + "Level N" tab, 3 hearts, blue squircle buttons, green booster squircles with a red badge) | **MED** (layout is functional; the skin is trade dress) | palette codemod; keep positions (FEEL) |
| 14 | **Home chrome**: `homeTopBar`, `navBar`, `navShop`/`navHome`/`navTrophy`, `homeLevelPlate`, `homePlayButton`, `homeClawBar`, `badgeJoin`, `badgeMultiplier`, event badges (`eventBadgeStreak`/`SkyJump`/`Rocket`), `iconHexArrow` | Basket / garage-house / trophy nav icons, raised cyan Home tab, green LEVEL plate + glossy green Play with Hard/Super Hard variants, checkered-flag drum badge | **MED** | palette codemod; new nav glyphs (a direction-flavoured shop, home and trophy); new event badges |
| 15 | **Shop art**: `bundleBag/Barrel/Chest/Safe/Cart/Special`, `coinPack*`, `shopSeal` | Each rebuilt from meta-008…010 | **MED-LOW** alone (genre props), MED in the identical layout | recolour or re-prop to the world (e.g. D1 mine cart, sack, crate); keep the coin |
| 16 | **Typography** | Nunito wght 1000 picked as the best match of their face (glyph IoU 0.863, `design/fonts.md`) + the same cream-face / dark-outline / drop style + their per-element colour pairs | **LOW-MED** (OFL; the effect is genre) | keep Nunito for body and digits; a different OFL display face for titles and the logo (§6) |
| 17 | **Event names + tutorial captions** ("Claw Challenge", "Sky Jump", "Rocket Race", "Streak Race", "Weekly Contest", "Tap to compete in Weekly Contest!") | Verbatim | **MED** for the distinctive names | events.md §7.3 proposes names; strings lane rewrites the captions |
| 18 | `pageBgPattern` (2 chunky arrows at 10 %), `tutorialHand`, `pointerArrowYellow/Down`, `infoPathIcon` | Measured copies | **LOW-MED** | redraw in the direction's motif (D1 dig marks, D2 gears, D3 stamps) |
| 19 | Board exit colour `#10A2EF`, vacated dots `#C5E1FF`, rainbow + pink/blue trails | Sampled from the phone | **LOW-MED** | per-direction accent (§3 tokens) |
| 20 | Board: black arrows on white, lattice, round caps, heads | Genre standard (the repo's own `apps/arrows` does the same) | **LOW** | keep |
| 21 | Generic icons: hearts, coin with star, stopwatch, gear, sound/haptic glyphs, close X, skulls, trophies, chests | Measured, but generic genre props | **LOW** | keep; recolour where they carry the blue chrome |
| 22 | Motion, timings, haptics, flows | Allowed 1:1 by ruling 37(b) | **LOW** (alone) | keep. Note: the logo *motion* with the logo *art* is #6 |
| 23 | **Level boards** L32–L83 (the phone's recorded boards) | The original's level designs; silhouettes are recognisable in screenshots | **MED** (content, not art) | level re-order plan; **store screenshots must show only designed/generated boards** (release/ASO plan) |
| 24 | Rewarded-ad art `iconVideoAd`, `heartGlossySmall` (+1 Live) | — | n/a | removed with owner item 9 |

Not a copy risk: Terms/Privacy text, the Brand constant, bundle id, the notification timing.

### 2.3 The logo, in detail (item 6 above; VERIFIED on `art/ui/out/logoArrowOut@3x.png` next to store 8)

| part | theirs (store 8) | ours today | same? |
|---|---|---|---|
| top sign | rounded rectangle, arched top, **royal blue** face, thick **white/grey rim**, slight 3-D bevel | the same shape family, royal blue `logoSignBlue`, white rim | yes |
| top word | "MAZE", **yellow-gold** chunky letters, **orange** extrusion, dark outline | "ARROW", yellow-gold, orange extrusion (Nunito inflated) | style yes, word no |
| joint | two short grey pegs | `logoPegs`, two grey pegs | yes |
| bottom sign | **purple arrow-shaped plate pointing right**, white rim | `logoSignPurple` (+ 4 bend variants), the same | yes |
| bottom word | **white** chunky "OUT!" with lilac extrusion | white "OUT!" with lilac extrusion | yes |
| layout | 2 tiers, the arrow sign offset right | the same | yes |

Every visual variable is theirs, so only the word is ours. §6 keeps the *motion contract* and changes every one of these rows.

---

## 3. Three original art directions

### 3.0 Shared across directions: the boss v2 (owner: "some differences, not major … we should be able to say they are not copied")

What stays (the owner's A): the pink strand-fur head, the eye and brow language, the smile, the fur ladder `#FFA8C8 … #B22470`, and
his size and role (the boss above the crew).

What changes, a minimal set that clears the gate (INFERRED):

| change | how (pipeline) | why it matters |
|---|---|---|
| **Two short rounded horns** (ivory `#FFF3DE → #E3CFA8`, base `#C9AE82`, 3 soft growth rings) replace the centred spiky crown tuft | `round_cone` + subtracted tori; fur density mask 0 inside the horn base + a short fur collar | The head silhouette is the first read, and theirs has a single tuft |
| **Blush muzzle patch** (`#FFD6E4 → #FFC1D6`) over the mouth and lower cheeks | a second fur Part `muzzlefur` rooted by a mask (like `browfur`) with its own LUT | Breaks the uniform one-colour fur of theirs |
| **Amber eyes** (iris `#D9951F`, pupil kept) | `IRIS` constant | Theirs are violet |
| **One snaggle tooth** in the closed smile (upper left) | a small box/round-cone under the lip groove | Personality mark |
| **Outfit swap**: no white lab coat, no lanyard, no ID badge, no pocket pen | per direction (below); `torso_space` gets a new garment set | These four are the original's exact costume |
| **Station swap**: no console with joystick, buttons and lever; not both hands flat | per direction (below); rig groups unchanged | Their pose and prop |

The "full" option (owner decides) also moves him off-centre, and gives him a tail and ears.

### 3.1 D1 — "BURROW WORKS" (recommended)

**Concept.** A cosy underground workshop where a crew of velvet-furred **Diggers** dig the tunnels (the mazes) and send the arrows
out through them. The pink boss is the foreman on the scaffold. The theme gives the whole game its metaphor: every level is a
tunnel system, and you dig the arrows out. The mood is warm and hand-made: a stop-motion miniature set.

**Crew species: "Diggers."**
- **Shape language:** pear/gourd bodies (wide hips, narrower shoulders) with a **forward snout cone ending in a round peach nose**,
  tiny round ears, and **huge spade paws with three ivory claws**. Short thick legs with padded soles. Cones and spheres, soft but
  with clear masses: body, snout, paws, hat.
- **Personality:** proud, diligent, a little clumsy. They salute, shovel and cheer.
- **Surface:** velvet strand fur. Short (L 0.012–0.025 u), dense, little clumping (0.2), segs 2–3. It reads as moleskin, and is a
  new preset of the proven fur route.
- **Kit:**
  - sunflower hard hat with a headlamp (emissive lens);
  - round brass goggles on the brow (glass lenses: eyes visible behind them, a strong "art" material);
  - a tangerine hi-vis vest with a cream reflective stripe;
  - a leather tool belt with a trowel.
- **Home rig casting:** L = a lamp-hat Digger with a shovel over the shoulder (wave member = the free paw), R = a goggles-down
  Digger reading a tunnel map (the "clipboard" role is now a map scroll).
- **Avatars:** 8 variants from the same model: miner, map-reader, chef (the "burger" slot becomes a lunch pail), party (party hat
  on the hard hat), detective (lamp + magnifier), sleepy (nightcap), strongman (pickaxe), and the boss.

**Boss v2 (D1).**
- **Outfit:** a teal canvas foreman coat (`#2E8C8A / #1F6B6B / #144C4E`) with brass buttons (`#E3B04B`), rolled sleeves, and a
  blueprint roll in the breast pocket. Goggles pushed up between the horns.
- **Station:** a timber scaffold rail with a big brass **lever**. One paw on the lever (armR), the other pointing into the tunnel
  (the `armR_point` equivalent).

**Home scene.** All UI rects unchanged (`ui.json frames.home`: level caption/plate 147.5..246 × 518.8..569, Play 82.7..311 ×
620.5..726, nav from 730, Claw bar 19..374 × 107..151). The left badge column (x 12–100, y 190–380) is kept clear.

| z | layer | frame (pt, INFERRED) | notes |
|---|---|---|---|
| 0 | `homeBackdrop` (new) | 0,0 393×852 | A cut-away burrow: a daylight shaft from the top-right (grass lip, roots, cream light `#FFF1CF`), timber props and cross-beams (`#E0A862/#B97A3E/#7E4E27`), teal-grey rock `#4E7F86 → #1B3A40`, lanterns `#FFCF6B`, cyan crystals `#7FE6FF`, moss accents. A round tunnel mouth dead centre. |
| 1 | boss rig (torso+head) | right of centre, x ≈ 205–385, y ≈ 165–400 | on the scaffold, leaning over the rail; asymmetric vs their centred boss |
| 2 | `homeScaffold` (replaces `homeConsole`) | x ≈ 190–393, y ≈ 330–420 | timber rail + brass lever + rope pulley |
| 3 | boss arms | rig | paw on the lever |
| 4 | `homeFloor` (replaces `homePlatform`) | 0,576 393×182 | packed-earth floor with a round plank work-pad and dig marks |
| 5 | **`homeSignpost`** (item 4; replaces `homeCapsuleMachine` + pile) | x ≈ 120–275, y ≈ 250–575 | a carved post planted in the pad. 5 arrow boards on brackets; the LEVEL board hangs at its foot on two ropes, framing the UI plate rect (§4) |
| 6 | crew rig L | feet ≈ (70, 606) | foreground left, shovel, big and close |
| 7 | crew rig R | sitting on the tunnel-mouth ledge, feet ≈ (300, 470), or front-right (318, 606) | the scene lane picks; the asymmetry is the point |
| 8 | ambient (optional, code) | — | lantern flicker, dust motes in the light shaft, a crystal twinkle |

**Loading screen (D1).**
- The camera looks up a **tunnel exit** into daylight.
- The crew **bursts out of the ground**: a mine cart loaded with arrow boards rolls straight at the camera (front-centre). One
  Digger rides on the cart's front, one is thrown up with an arrow board (upper right), and two pop out of dig holes (left).
- The boss stands on a rock at mid-left, waving a lantern; dirt clods fly.
- The logo sits **centred at the top** (theirs: top-left). "Loading.." stays bottom centre.
- 5–6 figures, data-driven through `char_loading_layout.json` (LoadingScreen reads it generically, VERIFIED `App/Shell/LoadingScreen.swift`).

**UI colour shift (tokens; ΔE00 vs theirs computed, VERIFIED arithmetic).**

| token | theirs | D1 | ΔE00 |
|---|---|---|---|
| chrome face / light edge / rim top / rim bottom / outline | `#0192FF` family | `#17B3A3` / `#7FEADB` / `#0B8A83` / `#075E5E` / `#053F43` | 34 |
| CTA (Play, Resume, Continue): face / light edge / rim / outline / label outline | `#00E400` | `#FFB422→#FF9A12` / `#FFE08A` / `#D06A06→#9E4A00` / `#6B2E00` / `#8A3F00` | 42 |
| danger (Quit) | `#FF3838` | `#F2553F→#DC3A26`, rim `#A82314` | 4 (red stays red; generic) |
| title ribbon | yellow `#FFCF00` arched | a **honey-wood plank** `#F0B86A→#D9913E`, rim `#9E5F24`, label cream `#FFFBEF` / `#6A3510` | 14 + shape change |
| panel inset | `#F8E7D2` | `#FFF3DF`, border `#D8A878` | 3 (cream is generic) |
| page background | `#16388C` royal | `#155158 → #0C343A` deep teal | 23 |
| HUD pill / digits | `#BDDCFF` / `#3861AC` | `#D4F4EC` / `#0B5A55` | — |
| board exit colour / vacated dots | `#10A2EF` / `#C5E1FF` | tangerine `#FF8F1F` / `#FFDDB0` | 52 / 30 |
| hearts, coins, board ink/ground | — | unchanged (generic) | — |

**Obstacle reskin (rules and hit geometry unchanged; the `gen_board.py` generators are parametric).**
- tape → a leather strap `#8E5A2F` with a brass buckle `#C98E3E`;
- door → a plank barn door (keeps "one slat per cell row", iron bands `#4B4F55`), hex lock → a round brass padlock;
- key → a brass key with a tangerine tag;
- pipe → copper `#D9824A` / highlight `#FFC39A` with iron collars, counter in a small crate;
- box → a rope-bound wooden crate with a counter disc;
- corner → a mint rubber bumper on a coil.

**Logo (D1, §6 LG-1).** A carved honey-wood plank sign with bolted corners and an irregular carved edge. ARROW in cream letters,
teal extrusion, dark-brown outline. OUT! in sunflower on a mint-painted **signpost arrow plank** hung by two rope loops.

**Palette summary.**
- timber `#E0A862 #B97A3E #7E4E27`
- rock `#4E7F86 #2E5961 #1B3A40`
- light `#FFF1CF`, lantern `#FFCF6B`, crystal `#7FE6FF`, moss `#86C04E`
- crew mint fur `#B6F5E2 #7FE3C3 #4CCBA5 #2FA888 #1C8068 #115C4C`
- nose `#FFB896`, claws `#FFF4DA`, hat `#FFCB2F`, vest `#FF8A2A`
- boss pink ladder + muzzle `#FFD6E4`, coat teal `#2E8C8A`
- UI chrome `#17B3A3`, CTA `#FFB422`

**Moodboard (generic, described).**
- stop-motion puppet miniatures with visible felt and velvet;
- needle-felted wool animal figurines;
- cut-away burrow and ant-farm illustrations in picture books;
- vintage miners' lamps, timber pit props, rope pulleys;
- warm lantern light against cool blue-green rock;
- glowing cave crystals;
- hand-painted wooden trail signposts with carved arrows.

**Fit.**
- A-achievability: **high**. It uses the fur route that produced the owner's A, plus hard-surface props (A grades on doors and
  chests prove that route).
- Cost: the heaviest (fur crowd).
- Copy distance: **high** (species, palette, world and composition all differ).
- Readability at 64 pt: good thanks to the hat and snout.

### 3.2 D2 — "WIND-UP WORKSHOP"

**Concept.** A toymaker's attic where the pink boss builds **tin wind-up robots** (the "Tinkers") who run on clockwork. The game
has a timer, and the theme turns it into a story: every level is a wind-up; the arrows are clock hands and toy parts.

**Crew species: "Tinkers."**
- **Shape language:** rounded tin cans (cylinders with rolled rims and seams), **glass-dome heads** showing tiny brass gears,
  round lamp eyes (glass lens over an emissive amber disc) or painted eyes on a face plate, accordion-spring or ball-jointed arms,
  rubber mitten grips, little wheel or tin-shoe feet, and a **brass wind-up key on the back** (an idle-rotation layer).
- **Personality:** earnest, mechanical, eager (they march, salute, and rattle when happy).
- **Surface:** painted enamel with **edge wear**. The existing obscurance LUT is used inverted at convex edges: u < 0.12 →
  exposed tin `#D6DADF / #9EA5AD`. Printed decals (numbers, stripes) come through planar UV textures. Rivets and seams are
  subtracted and added SDF details.
- **Colourways:**
  - mint `#8EE3C6 / #5CCCA8 / #2E9A7C`;
  - tomato `#FF8A6E / #F2573F / #C23A26`;
  - powder teal `#A8E4EE / #6BC4D6 / #3C93A8`.

  Never yellow (their worker hue).

**Boss v2 (D2).**
- **Outfit:** a leather toymaker apron `#8A5230 / #5E361C` with brass rivets and tool loops, a cream shirt `#FFF6E8` with rolled
  sleeves, a mustard bow tie `#E8A33A`, and a **brass magnifier loupe** on a headband over one eye.
- **Station:** a walnut workbench; he winds a small Tinker with a big key.

**Home scene.**
- A warm attic: walnut beams `#8A5634 → #3C2314`, cream plaster `#F6E9D2`, a pegboard of tools, shelves of toys, a round window
  with warm light `#FFE7B0`, a checker floor `#F2E4CC / #3B8C8A`.
- Centre: the **Wind-up Clock** (item 4, §4).
- The boss sits at the bench on the left-centre (x ≈ 60–230, y ≈ 170–380), clear of the badge column by sitting behind it in
  depth.
- One Tinker stands on the clock's top; one marches front-right.

**Loading.**
- A giant toy box's lid bursts open, bottom-centre.
- A line of Tinkers marches out towards the camera carrying arrow flags. One flies up on a spring.
- The boss turns a huge wind-up key on the box's side; brass gears and confetti fly.
- The logo is centred at the top.

**UI colour shift.**
- Chrome: mint enamel face `#45C49C → #33AE88`, light edge `#A8F0D6`, **brass rim** `#D9A040 → #9C6618`, outline `#4E3208`
  (ΔE00 41).
- CTA: tomato-orange `#FF6A3D → #EE4F24`, rim `#B8330F` (72).
- Danger: berry `#D8315B` (15).
- Ribbon: an engraved brass plate with screws `#F6C860 → #DB9A34`. The colour is close to their yellow (7), so the shape carries
  it.
- Panel: `#FFF5E4`.
- Page: aubergine-walnut `#3D2A3A → #261923` (22).
- Board exit: tomato `#F2573F`; dots `#FFD9CC`.

**Obstacles.**
- tape → a riveted steel strap;
- door → a toy-cupboard door with cream slats and brass hinges, lock → a brass keyhole plate;
- key → a wind-up key;
- pipe → brass tubing with an enamel dial counter;
- box → a tin crate with a gear counter;
- corner → a spring-loaded tin bumper.

**Logo (LG-2).** A tomato enamel plate with a brass rim and four screws. ARROW in cream letters with walnut extrusion. OUT! in
cream with tomato extrusion, on a mint enamel arrow sign hung by two brass rings.

**Moodboard.**
- mid-century tin wind-up toys with chipped enamel and printed lithography;
- cuckoo and wall clocks with painted dials;
- a watchmaker's bench (loupes, tiny screwdrivers, brass shavings);
- a toy shop window at dusk;
- pastel appliance enamel.

**Fit.**
- A-achievability: **medium-high**. The hard-surface route is proven on props; the characters must earn "art" through wear,
  decals and glass.
- Cost: the **cheapest** (no fur on the crew; ~10–25 s per render).
- Copy distance: **highest**.
- Owner-fit risk: robots are not "monsters". The owner asked for the workers to be "art like the pink monster".

### 3.3 D3 — "FEATHER POST"

**Concept.** A rooftop sorting loft at sunrise, where puffball bird couriers ("Posties") route parcels. Arrows are the routing
signs, and every level is a sorting job that sends everything out. The mood is airy, sunny and quick.

**Crew species: "Posties."**
- **Shape language:** round down-feather bodies (a sphere) with a **triangular orange beak**, a feather crest, a tail fan, little
  wing-hands with three finger feathers, and thin orange stick legs with round feet. Spheres plus triangles.
- **Surface:** "down" strand-fur preset (L 0.035–0.06, strong clumping 0.7 into feather tufts at the crest and tail).
- **Colour:** cream down `#FFFFFF #FFF7EA #F4E6CF #E0C9A6 #BFA27A`. Role colour comes from **chest bibs** (coral `#FF7A5C`,
  teal `#2FB3A8`, gold `#FFC34D`), not the body. Beak and feet `#FF9B3D / #E27414`.
- **Kit:** a teal postal cap `#2F8F8A` with a brass badge, and a kraft leather satchel `#B9773F`.
- **Personality:** busy, chattery, speedy.

**Boss v2 (D3).**
- **Outfit:** a postmaster cap (teal, brass badge) between the horns, a teal waistcoat, and a satchel strap.
- **Station:** a sorting desk, where he slams a giant rubber stamp (arm group swap).

**Home scene.**
- A timber loft with a round window onto rooftops and a sunrise gradient. Pneumatic tubes, parcels, bunting.
- Centre: the **Pigeonhole Sorter** (item 4, §4).
- The boss is behind the sorting desk on the right. One Postie flies in on the left over the badge column's depth; one sorts at
  front-left.

**Loading.**
- The loft's round window bursts open; Posties fly out towards the camera, each carrying an arrow sign or parcel.
- The boss stamps a giant "OUT" stamp on a parcel in the foreground; paper envelopes flutter.
- The logo is centred at the top.

**UI colour shift.**
- Chrome: coral face `#FF7F5E → #F2653F`, light edge `#FFC3AE`, rim `#C4442A → #8F2A17` (ΔE00 48).
- CTA: teal-green `#25B89C → #169C82` (25).
- Danger: crimson `#D52F46`.
- Ribbon: a **postage-stamp label** (perforated edge, cream `#FFF3E0`, coral text).
- Panel: `#FFF8EE`.
- **Light pages**: coral-cream `#FFEBDD → #FFD6C4` with ink text `#5A2A1E` (67), where theirs are dark.
- Board exit: coral `#FF6F4F`.

**Obstacles.**
- tape → parcel twine with a wax seal;
- door → a brass mail-slot shutter (slats per row), lock → a wax-seal lock;
- key → a mailbox key with a tag;
- pipe → a glass pneumatic tube with brass collars and a capsule counter;
- box → a stamped parcel with a counter;
- corner → a sorting flap on a spring.

**Logo (LG-3).** The top plate is a **perforated postage stamp** (cream) with coral letters and a dark-red extrusion. OUT! in
sunshine yellow on a teal envelope-arrow tag hung by twine.

**Moodboard.**
- vintage airmail envelopes and postage stamps with perforations;
- rooftop pigeon lofts;
- fluffy fledgling birds;
- old department-store pneumatic tube systems;
- rubber stamps and wax seals;
- sunrise over terracotta rooftops.

**Fit.**
- A-achievability: medium-high (fur route; beaks, wings and legs are new modelling).
- Cost: close to D1.
- Copy distance: high.
- Risk: Sky Jump's cloud world (event art) already lives in the sky. That is fine, but the palette must keep pink/violet for the
  boss only.

### 3.4 Comparison and recommendation

| criterion (weight) | D1 Burrow Works | D2 Wind-up Workshop | D3 Feather Post |
|---|---|---|---|
| owner fit: "art like the pink monster", "small monsters" (×2) | 5 | 3 | 4 |
| A reachable with proven routes (×2) | 5 (fur = the owner's A) | 4 | 4 |
| copy distance (×2) | 4 | 5 | 5 |
| readability at 40–64 pt (avatars, crowd) | 4 (hat + snout) | 5 | 4 |
| theme synergy (maze, arrows, timer) | 5 (tunnels = mazes, dig out) | 5 (clock hands, timer) | 4 (routing) |
| render cost / Mac load | 2 | 5 | 3 |
| market appeal (cute, warm) | 5 | 4 | 5 |
| **weighted total** | **44** | **43** | **42** |

**Recommendation: D1 "Burrow Works".**
- It answers the owner's own question ("why did not you do them like the top pink monster … in terms of design choices") with the
  *same* technique, turned into a different species.
- It gives the game a metaphor: tunnels are mazes, and you dig the arrows out.
- It is the furthest from the original's cool blue/purple lab: warm timber and teal.

The cost is render time (§7.5): schedule the renders after the perf timing.

Fallback if the owner finds velvet critters too close to "monsters": D2 is the cheapest and the most distant. D3 is the warm
middle ground.

Mixing is possible but not advised. Mixed direction elements (for example D1 crew + D2 clock) weaken the world logic.

---

## 4. Owner item 4 — "the arrows under the pink monster are going into each other"

### 4.1 The element (VERIFIED)

- Art ids: `homeArrowPileFull`, `homeArrowPileHalf`, `homeArrowPileLow` (186 × 126 pt, frame (104, 402)). Recipe:
  `art/ui/recipes/scene_home.py` (`pile_layout`, `pile_arrow`, `_pile_build`; BUILDS). They sit inside `homeCapsuleMachine`
  (95, 365, 206 × 215), directly under the boss's console.
- Code: `App/Shell/Home/HomeView.swift` (lines ~70–72 place the machine and `ArrowPileView`) and
  `App/Shell/Home/HomeScene.swift` (`ArrowPileUIView`: three stacked CALayers cross-faded Low → Half → Full over 1.2 s, plus 9
  drop sprites).

### 4.2 Why they go into each other

**Static heap (VERIFIED: code + render).** `pile_layout("full")` places 24 arrows in 4 depth rows 0.8–0.85 u apart, with x
jitter ±0.45, y ±0.3, z ±0.25, a random roll of 0–360°, pitch −34…−14° and yaw ±14°. The arrows are 4.5 u across the head. There
is **no collision or penetration test**, so overlapping volumes are guaranteed.

In `art/out/homeArrowPileFull@3x.png`:
- a lilac arrow passes through an orange one at the lower left;
- a sky arrow's head is buried in a yellow one at the centre;
- a green arrow cuts through the right-hand orange one.

**Refill (VERIFIED code; the look on device INFERRED).** Nine 2-D sprites (`arrowGlossy*`, 26–34 pt) get a random full rotation
(`CATransform3DMakeRotation(±π)`), so their baked top-left light rotates with them. They fall from the dispenser to random spots
**in front of** the whole pile and fade out at 80 % of 0.40 s. They land on, and appear to sink into, the heap.

### 4.3 Replacement: a mounted centrepiece (every arrow has its own mount → no intersection possible)

**Common contract** (the shell and motion owners implement it in phase P; INFERRED):
- **Frame.** The same `home.scene` slot, and the LEVEL plate rect (147.5, 536.8, 98.4 × 32.4) stays UI. The centrepiece art
  provides a backing or recess around it.
- **Layers.** A rig-style export (shared camera, `rig.py`): the base plus one layer per arrow element plus its pivot. The idle
  sway, tick or bob comes from `ui.json` tracks, in the style of `puppet`.
- **Refill.** `HomeScene.requestRefill()` / `takeRefill()` stays as the trigger (VERIFIED API). The refill becomes a keyframed
  sequence of those layers, in 3-D-correct poses, instead of rotated sprites. 1.2 s (`home.pileRefill`) is kept.
- **No-intersection gate** for any 3-D arrangement of arrows (the centrepiece, the loading props, the icon, the event heaps). A new
  `art/tools/overlap_check.py` samples each arrow's surface points and evaluates every other arrow's SDF there. It fails if any
  point is deeper than 0.01 u (≈ 0.6 pt at home scale). The shipped pile would fail it (INFERRED).

| direction | centrepiece | idle | refill (1.2 s) |
|---|---|---|---|
| **D1 Signpost** (recommended) | A carved timber post in the work-pad, with **5 arrow boards** on iron brackets at different heights and headings. Each board is a different palette colour and chunky, with a painted bevel (the `arrows3d.bevel_texture` method). A small lantern hangs on top. The LEVEL board hangs at the foot on two ropes, framing the UI plate. | Each board sways ±2° about its bracket, with a desynchronised period (2.8–3.6 s); the lantern swings. | The boards spin in one after another (flip about the bracket, 0.15 s each, a 6 % overshoot) with a light haptic tick per board. The post knocks once. |
| D2 Wind-up Clock | A wall clock on a brass wind-up base. The **hour and minute hands are two chunky arrows**, with a pendulum below. The LEVEL nameplate is under the dial. | The minute hand ticks every 1 s (3° with a 0.08 s overshoot); the pendulum swings. | The hands spin 360° with a ratchet; the key turns 2 full turns. |
| D3 Pigeonhole Sorter | A 3 × 3 pigeonhole cabinet. Each slot holds one parcel with an arrow tag in a palette colour. A brass nameplate holds the LEVEL. | The tags flutter ±3°; a bird peeks in and out of one slot. | The parcels slide into the slots one by one (0.12 s each, a small bump). |

If the owner insists on keeping a heap: not recommended, because the capsule-machine-with-heap is itself a HIGH copy element (#4).
The fix would be an offline physically settled heap (drop the arrows one by one with SDF collision, or rejection sampling under
the overlap gate), with the refill drops pre-rendered in 3-D from the same camera as frames, never rotated sprites.

---

## 5. Icon concepts (owner item 11)

**Rules** (INFERRED from the owner's words and the audit):
- 3-D rendered like our in-game art (mfrender, fur and painted bevels), never flat SVG;
- **no white ground, no row of three red/yellow/blue arrows, no arrows running off the edges in parallel** (theirs);
- no text;
- one hero idea readable at 60 px;
- full-bleed opaque 1024 px RGB (`exact_px`, `full_bleed`, as the current `appIcon` entry);
- dark and tinted variants for iOS 18+ home screens (INFERRED platform expectation; verify on device, §8).

| id | concept | composition | palette (D1) | why it is not theirs | risks |
|---|---|---|---|---|---|
| **IC-1 "Out the Door"** (recommended) | One chunky glossy tangerine arrow bursts diagonally up-right **out of a small 3-D maze block through a doorway**. A Digger clings to its shaft, grinning, hard hat flying off. Dirt and sparkle trail. | 3/4 view. The arrow's head fills the top-right third, the maze block the bottom-left third, and the character's face sits at the optical centre (≈ 45 %, 55 %). Rim light separates the arrow from the ground. | ground: teal radial `#1C8C86 → #0C4A4C` with a faint embossed maze pattern; arrow `#FF9A12` bevel `#D06A06`; hat `#FFCB2F`; fur mint | a single arrow and a character; coloured ground; a gameplay story (escape); our species | busiest of the three. Test at 60/40 px; drop the dirt if it muddies. |
| IC-2 "Peek" | A Digger's head and paws pop up from a hole in a maze floor, holding a small arrow sign pointing right, eyes wide with glee. | A face close-up filling ~65 %; the sign at the right edge. | warm amber ground `#FFB84A → #E0781E`; mint fur; peach nose | a character-forward mascot icon (the genre's top grossers use faces) | the arrow is small, so the "arrow puzzle" category signal is weaker (ASO) |
| IC-3 "Boss Grin" | A pink boss v2 close-up (horns, muzzle, amber eyes, snaggle tooth), holding one glossy arrow up beside his face like a trophy. | The head fills ~70 %; the arrow crosses the lower right. | teal ground; the pink fur hero render | the most "premium mascot" read | **MED similarity risk**: a furry monster face is the element most associated with the original's store art. Only after boss v2 has passed the gate. |

**The same concepts in D2 and D3:**
- IC-1 → a Tinker riding an arrow out of a toy box (D2), or a Postie flying out of a pigeonhole with an arrow tag (D3);
- IC-2 → a Tinker's glass dome peeking up (D2), or a Postie peeking out of a mail slot (D3).

**Production.**
- A new recipe `art/ui/recipes/icon_v2.py` in scene-build style: models from `char_crew_*.py` + `arrows3d` + a maze-block SDF, one
  camera, ground painted in `post_fit`.
- Fur at icon scale needs ~4–6× the home strand count and thinner strands (≈ 2–3 M triangles). **One render ≈ 3–6 min
  (INFERRED)**, so it runs in the background with a log. Draft at 512 px first.
- Acceptance:
  - a downscale strip at 1024 / 180 / 120 / 60 / 40 px, on light and dark wallpapers;
  - the copy gate vs `research/store/icon-1024.png` (chroma overlap < 0.40, SSIM < 0.25);
  - the owner's pick.

---

## 6. Logo restyle options that keep our measured motion

**Motion contract (VERIFIED, `build/logo/LOGO-SPEC.md` §0 D2–D10, rulings 35–36).**
- The layer tree is `group ⊃ {bottom sign, pegs, top plate ⊃ 5 letters, 4 OUT! glyphs}`. The group scales about (196.0, 425.5).
- Every track is a **displacement from the part's settled pose about its own anchor**. ARROW's 5 letters sample the lag chain by
  their place `u` along the plate.
- The bottom sign has a pivot, sx ≠ sy, an extra arch (the 4 warped `Bend25..100` variants, `y' = y + k(x − xa)²`), a hidden
  slide, and a wobble on its pegs.
- OUT! = 4 glyph layers that spread and tilt. There is an echo container, and Ext/Face pairs + Flats with a single `flatUntil`.

**What can change without touching the motion:**
- every shape, colour, material and typeface;
- the settled positions within reason, since the anchors are regenerated from the art;
- the plate's outline;
- the pegs → any hanger.

**What must stay:**
- 5 top letter layers and 4 bottom glyph layers (Ext/Face/Flat as today);
- a bottom sign elongated along x (so the bend warp reads);
- a hanger layer between the plate and the sign;
- the frame and pixel rules of LOGO-SPEC D10 (≥ 3.10× for glyphs).

| option | top plate | ARROW letters | hanger | bottom sign | OUT! | notes |
|---|---|---|---|---|---|---|
| **LG-1 (D1) "Signpost plank"** | a carved honey-wood plank `#E0A862/#B97A3E` with an irregular carved edge, visible grain, 4 iron bolts, **no white rim** | cream `#FFF4DC → #FFE3A8` face, **teal** extrusion `#17857A → #0E5A55`, outline `#3A1E0E` | two rope loops | a mint-painted plank arrow `#3FC39C / #1E8A6C` with a **notched tail** (a real signpost arm), a painted edge | sunflower `#FFC526` face, burnt-orange extrusion `#C4700E` | the most natural "arrow" sign, and distant from a glossy blue plate |
| LG-2 (D2) "Enamel plate" | a tomato enamel plate `#F2573F` with a brass rim `#E0A63A` and 4 screws, chipped edges | cream, walnut extrusion `#7A4B2E` | two brass rings | a mint enamel arrow with rivets | cream face, tomato extrusion | — |
| LG-3 (D3) "Postage stamp" | a cream **perforated stamp** outline with a thin coral frame | coral `#FF6F59` face, dark-red extrusion `#A83220` | twine | a teal envelope-arrow tag | sunshine `#FFD15C` | the perforated edge is the signature |

**Shared:**
- **Typeface.** Move the logo (and optionally all titles) from the Nunito match to a distinct OFL display face with chunky,
  slightly condensed forms. Candidates: Lilita One, Titan One, Fredoka Bold, Baloo 2 ExtraBold. Verify each licence file before
  bundling (INFERRED licences). Keep Nunito for body text and digits.
- **"!".** The owner named the logo "ARROW OUT!". Keeping it is fine once everything else differs. Dropping it (or replacing it
  with a small arrowhead glyph, which keeps the 4-glyph motion contract) is an owner decision (§9).
- **Regeneration path** (phase P; no hand edits, VERIFIED tooling):
  1. restyle `art/ui/src/svg/gen_icons.py` (`logo_arrow_out`, `LOGO_PART_FRAMES`, `LOGO_BEND`, pairs, flats);
  2. `art_batch.py --svg --ids logo*`;
  3. `art/ui/tools/logo_parts.py measure` (anchors → MANIFEST `anchor_frac`);
  4. `build/logo/spec/tools/logo_out.py` → `compose_md.py` (tables A/L/P/S/E/U regenerate);
  5. re-run the colour composite test `logo_parts.py look` and re-measure the §5.3 recompose bound;
  6. keep the ids (`logoSignBlue`/`logoSignPurple` are now misnomers, but renaming ripples through UIArt, WinLogoSequence and the
     tests: debt, not a blocker).
- Optional quality step: render the Face/Ext pairs in 3-D through `rig.py` (shared camera per letter) for a true bevel. The SVG
  route is graded "B, near A" today. The owner's "svg ai slop" complaint was about the icon, so the logo can stay SVG if the
  material reads.

---

## 7. Production plan

### 7.1 Inventory (manifest groups, VERIFIED counts from `art/MANIFEST.json`, shipped ids only)

| family | ids | route / pipeline | action |
|---|---|---|---|
| characters | 11 (`scientist`, `scientistLoading`, 9 worker ids) | C1 3-D, `art/pipeline/items/char_*.py` → `rig.py` / `char_make.py` | **REDESIGN**: `char_boss.py` (forked from `char_scientist.py`: fur/groom/rig code kept, horns/muzzle/outfit/station added) + `char_crew_<dir>.py` on `char_kit` + `char_fur` presets |
| avatars | 8 3-D + 1 SVG | C1 3-D portraits | **REDESIGN** 8 (same count and order slots) |
| home | 13 3-D + 3 SVG + 7 SwiftUI | C1 scene (`scene_home.py` BUILDS) | **REDESIGN** backdrop, station, centrepiece (+ rig), floor; nav icons ×3 + event badges ×3 redrawn; SwiftUI by the palette codemod |
| loading | `loadingBackdrop` + layout JSON (+ the 7 `arrowGlossy*` props) | C1 | **REDESIGN** backdrop + 5–6 figures; `arrowGlossy*` recoloured to the palette |
| logo | 40 SVG | B2 `gen_icons.py` | **RESTYLE** + LOGO-SPEC regenerate |
| app icon | 1 | C2/C1 3-D, new `icon_v2.py` | **REDESIGN** (3 drafts → 1 + dark/tinted variants) |
| events | claw 3+2, rocket 7+1, sky jump 9, streak 1+5, leaderboard 2 (+ Balloon ids in events.md) | C1 scene (`scene_events.py`), B2 | **REDESIGN** headers/backdrops with the new cast (~12); props recoloured (~15) |
| board | 24 SVG + 9 3-D + 8 code | C3 `gen_board.py` parametric, `corner.py` 3-D, engine colours | **RESKIN** ~33 files + 2 engine colours |
| popups / profile-shop-settings / hud / boosters / fx | ~70 (3-D + SVG) + ~30 SwiftUI | B1/B2/B3 | unlock icons ×7 **RESKIN**; `pageBgPattern`, `tutorialHand`, pointers **REDRAW**; generic props keep (recolour where needed) |
| SwiftUI chrome + code colours | 49 SwiftUI entries; **1 572 hex literals in 57 Swift files** (top: ShopView 151, PopupChrome 95, WinPanel 72, PageChrome 71), ui.json ~436 distinct colours | B1 code | **PALETTE CODEMOD** (§7.3) |

Rough totals: **~60 redesigned renders/parts** (characters, avatars, scenes, icon) + 40 logo parts regenerated + **~70 reskinned**
SVG/3-D files + the codemod.

### 7.2 Lanes and file ownership (phase P; the same lane system, scratch manifests `art/lanes/<lane>.entries.json`)

| lane | owns | notes |
|---|---|---|
| characters | `char_boss.py`, `char_crew_*.py`, `char_fur.py` presets (`velvet`, `down`), avatars, loading figures, event figures | the rig contract R8; placements via `rig.json placement_pt` |
| scene | `scene_home_v2.py` (or new BUILDS in `scene_home.py` with the same ids), `scene_loading.py`, `scene_events.py`, centrepiece rig | a per-direction `char_env` room map (§7.4) |
| ui-art | `gen_icons.py` logo, `gen_board.py` reskin params, unlock icons, `pageBgPattern`, pointers, nav glyphs | SVG batch is cheap |
| 3d-hud | `icon_v2.py`, `arrowGlossy*` recolour, `corner.py` reskin, booster props if recoloured | icon renders in the background |
| director | grades on the new bar, copy gate, merges | writes `art/review/grades-director-v2.json` |
| shell (build) | palette codemod, `HomeCentrepiece` view replacing `ArrowPileView`, UIArt ids, LoadingScreen (JSON-driven, unchanged) | App/** edits happen only in phase P build |
| motion (build) | `ui.json puppet` tracks for new layers (ears, key, boards), centrepiece idle/refill tracks, logo spec regenerate | FEEL owner |

### 7.3 The palette codemod (build phase; INFERRED design)

`tools/palette_map.py` works in four steps:
1. **Scan** every hex literal in `App/**/*.swift` (`0xRRGGBB`, `Color(hex:)`), `App/Resources/Tuning/ui.json` (colors, gradients,
   frames), `art/ui/code/GlossyChrome.swift` and the SVG generators' colour constants.
2. **Classify** each literal into a family by hue/saturation/value windows plus an explicit table of the measured tokens (STYLE.md
   §D): chrome-blue, chrome-rim-navy, CTA-green, danger-red, ribbon-yellow, cream, page-navy, HUD-pill, exit-blue. Excluded
   families: board ink/ground, hearts, coins, country flags, avatar plates, generic whites/blacks.
3. **Map** each family onto the direction's ladder, **keeping each colour's L\* and its chroma relative to the family's anchor**,
   so gradients, rims and light edges keep the structure that made the chrome read premium.
4. **Emit** a review CSV and a swatch sheet, apply after sign-off, re-run `art_batch.py --svg` for the rasters that bake colour,
   then capture every screen and run the copy gate.

The ribbon and title-plate shape change (plank / brass plate / stamp label) is a component change in `GlossyChrome.swift` and
`PopupChrome.swift`, not a colour.

### 7.4 The A-grade bar v2 (replaces "a player takes it for the same art")

- **A (ship):**
  - on the composed screen at game size (3 px/pt), it reads as the same finish as our pink boss: the director views every new
    character next to `char_sci_home@3x.png` at the same scale, as the calibration card;
  - passes R1–R8 (§1.3);
  - passes the copy gate (§2.1);
  - the 1/3-size thumbnail identifies species and pose;
  - the rig and idle proofs pass;
  - no visible penetration (overlap gate for arrow sets).
- **B:** the same finish with visible modelling gaps at 2×. **C:** redo.
- Target: **100 % A on hero assets** (boss, 2 home crew, centrepiece, icon, logo, loading cast) and ≥ 70 % A overall before
  submit. The owner's verdict on the concept pack overrides the grades.
- Per-direction environment: `char_kit.char_env` gets a direction room map (D1 amber timber + teal rock, D2 walnut/cream, D3
  coral/cream sky), so the reflections and ambient match the new scene. Today it is the blue/lavender lab room (VERIFIED).

### 7.5 Render budget (INFERRED from the logged timings)

Logged timings (VERIFIED, lanes): scientist (fur) 65–125 s; worker 8–25 s; crowd 60–110 s; scene renders ~1 s each (backdrop
composites 10–30 s, first mesh ~80 s); arrow 17 s; today's arrows-only `appIcon` ~90 s (`art/lanes/3d-hud.md`). Any recipe edit
re-meshes every model of that file.

| item | D1 | D2 | D3 |
|---|---|---|---|
| concept pack (per direction: boss-v2 head draft, crew hero draft, icon draft) | ~3–4 min | ~2 min | ~3–4 min |
| boss rig (9 layers + full) | ~15 min | ~15 min | ~15 min |
| 2 crew home rigs (~10 layers each) | ~20 min | ~5 min | ~18 min |
| loading figures (5–6) | ~9 min | ~3 min | ~8 min |
| event figures (2–3 groups) | ~5 min | ~2 min | ~5 min |
| avatars (8) | ~5 min | ~2 min | ~5 min |
| scenes (~20 builds, warm caches) | ~15 min | ~15 min | ~15 min |
| icon final (1024, background) | 3–6 min | 2–3 min | 3–6 min |
| logo + board + icons (SVG) | ~3 min | ~3 min | ~3 min |
| **one full pass** | **~75 min** | **~45 min** | **~70 min** |
| with ~3 iteration rounds on the heroes | **~3–3.5 h** | ~1.5–2 h | ~3 h |

Machine rules: PIPELINE.md and SPEC §6.
- Each command < 4 min; anything longer runs in the background with a polled log.
- ≤ 2 workers (spawn).
- `sysctl vm.swapusage` check ≥ 400 MB free before each 3-D batch (`art_batch`/`scene_make` already enforce it).
- Fur renders peak at ~1.4 M triangles (icon ~3 M): one at a time.
- **Nothing renders while the perf agent is timing**; the orchestrator gives the go.

### 7.6 What to render first (when the Mac is free), in order

1. **Concept pack** (drafts, `--draft`), to present to the owner:
   - **boss v2 head** (minimal-change set) next to today's `sci_home` head, same camera — answers "not major, but not copied";
   - **one crew hero per direction** (idle pose, home scale) + a 1/3 thumbnail, next to today's blue worker (B) and the scientist
     (A) as the calibration card;
   - **icon drafts** IC-1 (per direction) + IC-2/IC-3 once, at 512 px + the 60/40 px strip;
   - **palette mock:** re-render the Paused popup + HUD row with `build/ui-art/swiftuirender` in each direction's tokens (seconds);
   - **logo sketch** per direction (SVG, seconds);
   - one sheet per direction + one side-by-side sheet → the owner.
2. After the pick: centrepiece (item 4) + backdrop draft → **composed home proof**, run through the copy gate.
3. Boss v2 rig → crew rigs → home proof at A.
4. Icon final (+ dark/tinted variants).
5. Loading cast + backdrop → loading proof.
6. Logo restyle → LOGO-SPEC regenerate → colour composite test.
7. Board obstacle reskin (SVG, cheap) → in-place proofs on the levels.
8. Events, avatars, shop props.
9. The palette codemod in the build phase, then captures of every screen and the copy gate.

---

## 8. What needs the phone (not available now)

- **Icon on the real home screen:** legibility at 60 pt among real apps, light/dark wallpapers, and iOS 26 dark/tinted modes
  (needs a test build carrying the candidate icon).
- **P3 colour check:** the new palette and the scene renders on the iPhone 15 display vs the Mac preview (mfrender converts P3 →
  sRGB; saturated teal and tangerine may shift).
- **Centrepiece feel:** the item-4 idle and refill on device, with the haptic tick, next to the rest of the home FEEL.
- **Owner review:** the composed home and Loading at real size on the owner's phone (the D1 install after the build).
- Optional: a short clip of the original's icon on the same springboard and wallpaper, for the copy side-by-side (look only).

---

## 9. Decisions for the owner

1. **Direction:** D1 Burrow Works (recommended), D2 Wind-up Workshop or D3 Feather Post.
2. **Boss changes:**
   - *minimal*: horns, blush muzzle, amber eyes, snaggle tooth, new outfit instead of the lab coat, lanyard, badge and pen, new
     station;
   - or *full*: also off-centre placement, tail and ears.

   Or name the ones to skip.
3. **Icon:** IC-1 "Out the Door" (recommended), IC-2 "Peek" or IC-3 "Boss Grin" (medium similarity risk).
4. **Logo:** keep "ARROW OUT!" with the "!" (fine once restyled), or drop the "!" / replace it with an arrowhead glyph. Also
   approve a new OFL display face for the logo and titles.
5. **UI palette:** approve the direction's chrome/CTA/page tokens. In D1 the "go" colour becomes sunflower-orange instead of
   green. Keep green for "go" instead?
6. **Board obstacle reskin:** tape, doors, locks, keys, pipes, boxes and corners get new looks with identical rules and hit
   geometry (they appear in every screenshot).
7. **Event looks** follow the chosen world; the **event names** are events.md §7.3's decision.
8. **Names for the crew and boss** (optional; for store copy and tutorials).

---

## 10. Open issues and risks

- **Rig contract.** The new characters must export the same groups and pivots, or the motion owner must add tracks. The rig names
  `char_sci_home_rig` / `char_wk_home{L,R}_blue_rig` are referenced by `HomeView.swift` and `ui.json`. Keep the file names or
  migrate them in one mapping step; the "blue" and "sci" in the names become misnomers.
- **Test pins.** Tests pin art sizes and ids (UIArt, `ShellS2Tests` logo bounds, the logo recompose test). A restyle changes the
  frames. They must be regenerated as measured data with reasons, never weakened.
- **Copy-gate calibration** rests on 3 copy pairs and 3 controls (VERIFIED numbers, INFERRED thresholds). Recalibrate on the
  concept renders.
- **Fur cost vs the Mac.** D1 roughly doubles the render time of D2. Renders are blocked while perf timing runs, which is a
  schedule dependency for the orchestrator.
- **The palette codemod is broad.** 1 572 literals + ~436 ui.json colours + about 121 SVG entries whose rasters bake colour. A
  missed family leaves a blue island, so a capture sweep of every screen after the codemod is mandatory.
- **Home layout constraints.** The UI rects and the left badge column fix a lot of the composition. The asymmetric layout (boss
  off-centre, crew at different depths) is what separates us at a glance. The copy gate proves it.
- **Level boards in store screenshots** (audit #23): coordinate with the release/ASO and level re-order plans.
- **iOS 26 icon formats** (layered/tinted) are not in the manifest yet.
- **Rewarded-ad art** (`iconVideoAd`, `heartGlossySmall`) goes with owner item 9 (other topic).
- **The icon fur close-up** needs an untested strand density (≈ 2–3 M triangles). Draft at 512 px first.
