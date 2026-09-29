# 3d-hud lane — log (3D ui-art: HUD boosters, popups, bottom nav, Claw props, glossy arrows, app icon)

Lane files (nothing else was edited; no shared pipeline file, no MANIFEST.json):
- recipes: `art/ui/recipes/3d-hud_props.py` (13 cases), `art/ui/recipes/3d-hud_arrows.py` (7 block arrows + `appIcon`)
- scratch manifest for the tools / the art director's merge: `art/lanes/3d-hud.entries.json` (21 full entries: `source`
  -> the recipes above, `owner` 3d-hud, `status` done, notes; boosterPointer/boosterDome refs corrected, see below)
- outputs: `art/ui/out/<id>@3x.png` (props), `art/out/arrowGlossy<Colour>@3x.png`, `art/out/appIcon1024.png`
- sheets (gitignored): `art/ui/sheets/m_<id>.png` via `manifest_sheets.py --manifest art/lanes/3d-hud.entries.json <ids>`

Rebuild / check (from apps/mazeout, `PY=~/.venvs/mf3d/bin/python`, one render process, MF_WORKERS=2):
```
$PY art/tools/art_batch.py --manifest art/lanes/3d-hud.entries.json --3d --ids boosterFreeze ...   # everything but appIcon
$PY art/tools/manifest_sheets.py --manifest art/lanes/3d-hud.entries.json boosterFreeze navHome ...
$PY art/tools/manifest_check.py --lanes art/lanes/3d-hud.entries.json          # all 21 lane entries: ok
# appIcon (1024 px is not a whole-pt @3x frame, so art_batch's size check does not apply): render the case with
# ui3d.render_case("appIcon", "3d-hud_arrows") (OUT pointed at build/), then save it as RGB -> art/out/appIcon1024.png
```
Timings: props 3-50 s each (coinPileSmall ~90-150 s: ~70 stacks meshed as one field), block arrows ~15-25 s, appIcon
~90 s. Any edit to a recipe file re-meshes every model of that file (ui3d caches by recipe source hash).

## Entries

| id | status | output path | reference used | self-grade | remaining differences |
|---|---|---|---|---|---|
| boosterFreeze | done | art/ui/out/boosterFreeze@3x.png | 003-L32-start box 14,760-76,822 (+ V1 t 30 s 4-bar frame) | B- | reads as the frozen hourglass at game size; our icicles are a little comb-like (two straight drips) where the capture has one fat curled icicle; our glass is a lighter cyan (the capture's teal middle is the green button seen through the glass -- ours is 0.82 opaque so it tints the same way in place) |
| boosterHint | done | art/ui/out/boosterHint@3x.png | 003-L32-start box 318,760-378,822 | B+ | glass a touch paler/whiter than the capture's pale blue; the capture's darker blue glass rim is softer in ours |
| stopwatchBig | done | art/ui/out/stopwatchBig@3x.png | 013-L32-popup box 85,268-310,493 | B+ | our tick marks are slightly longer/ovaler; the capture's dial has a faint inner shadow under the bezel lip; glow (ours, post) sits a bit more to the right |
| heartBroken | done | art/ui/out/heartBroken@3x.png | 016-L32-after-decline-life box 117,296-277,428 | B+ | the capture's heart is a little taller in the lobes; our specular is a streak along the left lobe where the capture has a broad soft blob; red now close (deep crimson rim via sticker outline) |
| coinStackReward | done | art/ui/out/coinStackReward@3x.png | 020-L32-win-1 box 133,360-243,460 | B | same cluster read (standing star coins in front, flat stacks behind); the capture's coins are a bit bigger and overflow its box; our twinkles are smaller than the capture's left twinkle |
| heartInfinite | done | art/ui/out/heartInfinite@3x.png | 033-after-L33 box 152,368-244,452 | B+ | our tip is sharper; the capture's infinity loops are slightly fatter; the gold sparkles around it on 033 are FX (not baked) |
| navShop | done | art/ui/out/navShop@3x.png | 026-home-after-L32 box 38,772-100,834 | B+ | the capture's basket is a touch wider at the rim with a thicker rim band; its coin shows a bigger star |
| navHome | done | art/ui/out/navHome@3x.png | 026-home-after-L32 box 163,735-229,801 | B- | shapes/colours match (thick orange arch with flared eaves, round window, orange garage frame, cream slat door, wide cream chimney + orange cap); SIZE: the capture's raised Home icon is ~1.2x ours -- it runs below the 66 pt box under the "Home" label, while ours is the whole house fitted in 66 x 66. Draw it at ~1.2x (or grow the frame to ~66 x 80 pt and re-render) |
| navTrophy | done | art/ui/out/navTrophy@3x.png | 026-home-after-L32 box 288,772-356,834 | B | the capture's handles are squarer and its foot a single tall slab; ours shows a little of the foot's top |
| padlockGold | done | art/ui/out/padlockGold@3x.png | 023-claw-challenge-c box 308,508-352,562 | B+ | the capture's body edge turns more orange at the sides; its keyhole has a lighter inner lip |
| coinPileSmall | done | art/ui/out/coinPileSmall@3x.png | 025-claw-info box 84,522-152,578 | B | same mound of stacks + glow; the capture has deeper orange crevices between stacks and a dark reflection under the pile |
| arrowGlossyYellow | done | art/out/arrowGlossyYellow@3x.png | 026 capsule-machine pile box 112,410-282,520; store iphone-8 (loading arrows) | B | see "Block arrows" below; canonical pose pointing right, seen from above-front |
| arrowGlossyRed | done | art/out/arrowGlossyRed@3x.png | same + store icon red set | B | the loading screen's red arrow is more orange-red than the icon red we use |
| arrowGlossyBlue | done | art/out/arrowGlossyBlue@3x.png | same + store icon blue set | B | - |
| arrowGlossyGreen | done | art/out/arrowGlossyGreen@3x.png | 026 pile (green family measured) | B | - |
| arrowGlossyPurple | done | art/out/arrowGlossyPurple@3x.png | 026 pile (purple family measured) | B | - |
| arrowGlossyOrange | done | art/out/arrowGlossyOrange@3x.png | 026 pile (orange family measured) | B | - |
| arrowGlossyCyan | done | art/out/arrowGlossyCyan@3x.png | 026 pile (cyan family measured) | B | the manifest ref (store iphone-8 300,100-440,250) frames the red-orange loading arrow, not a cyan one; the cyan was measured on 026 |
| appIcon | done | art/out/appIcon1024.png (1024 x 1024, RGB, no alpha) | research/store/icon-1024.png (style only) | B | OUR composition (below); same style as the store icon; the yellow up-arrow shows a slightly lighter bevel rim than the store icon's yellow |
| boosterPointer | done (unconfirmed) | art/ui/out/boosterPointer@3x.png | V1-levels-01-20.mp4 t 30 s, box CORRECTED to 62,760-112,810 | C+ | it is a yellow SET-SQUARE (not an arrow cursor): rounded right-triangle plate with a triangular window and tick grooves; ours is a little more yellow/less orange |
| boosterDome | done (unconfirmed) | art/ui/out/boosterDome@3x.png | V1 t 30 s, box CORRECTED to 282,760-332,810 | C+ | it is a RING-STACK toy (not a dome/bell): yellow base, two blue rings, blue ball; the capture's blues are lighter/cyan-er |

## Decisions and measurements

- **Toon paint instead of plain PBR** (every prop part except glass/snow/dial): the references darken toward a deeper
  SATURATED hue (gold -> orange, red -> crimson, blue -> ultramarine); PBR alone went olive/brown (first trophy/padlock
  drafts). `tpart()` paints each part from its own SDF: u = 1 - n_view.z (how far the surface turns away from the
  viewer, in the POSED view), v = screen height; a 2D LUT (top/mid/bottom face colours, edge colours) per scheme
  (`SCHEMES`: gold, goldDeep, orange, yellow, red, blue, cream, slate, bulb, ice, arrowRed). Lighting = `PROP_LIGHT`: a
  flatter, brighter rig than ui3d.RIG (key 2100, fill 900 from below, rim 1100, + a 700 lux frontal fill).
- **Coins** (`coin_part`): built at a canonical R 0.5 then scaled (recess/emblem depths stay proportional); face gold
  `#FFC21C`, recessed field `#FFAC10`, raised chubby star `#FFD440`, edge band `#EC8C04`, painted per vertex from the
  coin's LOCAL coordinates; `min_tris=10**9` (no decimation) -- the decimated coins showed polygonal rims and blotchy
  paint. The pile uses one grooved-cylinder field per stack (`stack_sdf`).
- **Registration** (`fill`/`align`): each frame is centred on its ref box by `manifest_sheets`, so the art is sized to
  the capture at scale 1: boosters fill ~37 x 40 pt of 56 (the icon inside the 62 pt green button), stopwatch 0.975,
  hearts 0.93-0.955, nav icons 0.88-0.95.
- **Block arrows** (arrowGlossy*): the manifest ref is the capsule-machine pile, whose arrows are chunky BLOCK arrows
  (measured on 026 at 3x: head width 1, head length 0.58, shaft width 0.54, shaft length 0.54, thickness 0.30, tip r
  0.16, head back corners r 0.14), not the store icon's long-shaft arrows. So arrowGlossy* are block arrows (the spike's
  long-shaft renders at the same paths were replaced); the icon's long-shaft model lives in the same recipe
  (`icon_*` models) and is used by appIcon. Colours (face / wall shade / deep wall / bevel highlight): yellow
  `#FEC307/#FB9A08/#E8700C/#FFDB52`, orange `#FD8A0C/#F06A06/#CC4E08/#FFB456`, green `#86E532/#4DBA12/#349A06/#BAF472`,
  cyan `#3EC6F9/#1C9ADA/#0A74BC/#94E0FD`, purple `#D06EEA/#AE42D4/#8A2EB0/#EAB0F8` (value quantiles of each hue family
  over 026's pile), red/blue = the store icon's k-means sets (STYLE.md §D). Painted per vertex: u = which way the 2D
  outline faces (screen up-left -> down-right), v = zone (top face -> bevel -> wall -> back); `min_tris=10**9`.
  Canonical pose: pointing right, pitch -28 (the bottom wall shows, as in the pile), fov 12, fills the 100 pt height.
- **App icon** (ours): blue arrow entering from the RIGHT edge pointing left (top band), yellow from the BOTTOM edge
  pointing up (right), red from the LEFT edge pointing right (bottom band) -- every colour has a different direction
  and place than the store icon (yellow ->, red <-, blue -> in three horizontal lanes). Same style: long-shaft glossy
  arrows (head 0.40 of the icon), painted bevel in SCREEN space (`roll` passed to the paint so the lower-right shade
  follows each arrow's rotation), scene-level pitch -14 so every arrow shows its screen-bottom wall, white ground with a
  4.5 % cool vignette and a soft contact shadow (ours, post). Opaque RGB 1024 px. Checked at 180 px with a rounded mask
  and at 60 px: three bold arrows read.
- **Glows / twinkles** are drawn by us in 2D post (`_glow`, `_twinkles`), never sampled: stopwatch blue glow, coin-pile
  warm glow, two small twinkles on coinStackReward.

## For the art director

1. `boosterPointer` / `boosterDome` refs: the manifest's box_pt y 795..840 frames the LOWER half of the V1 4-bar
   buttons (the icons sit at y ~760..810 on the 592 px = 393 pt frame). The lane file carries corrected boxes
   [62,760,112,810] and [282,760,332,810]. Their purposes should read "yellow set-square" and "ring-stack toy"
   (research/tutorials.md: "yellow set-square, frozen hourglass, bulb, blue ring-stack").
2. `navHome`: frame 66 x 66 pt holds the whole house; on the phone the raised icon is ~1.2x (clipped by the label).
   Either scale it in the nav bar or grow the entry to ~66 x 80 pt (a re-render is one line in ASSETS).
3. `arrowGlossyCyan` ref points at store iphone-8's red-orange loading arrow; the pile on 026 is the cyan reference.
4. 3d-events' `trophyCup` (Weekly Contest / profile) could reuse `3d-hud_props.trophy` (drop the arrow emblem).
5. The freeze booster's flight in the freeze animation (~90 x 100 pt, research/motion.md §7.2) can scale
   boosterFreeze@3x (the art is ~40 pt tall in it: ~2.5x upscale looks soft) -- if it must be crisp, add a case
   `boosterFreezeBig` (same model, frame ~100 x 100) to 3d-hud_props.py.

## Iteration log (sheets looked at every round)

- R1 drafts: pipeline + sheets working; trophy/padlock too dark/olive (PBR) -> toon paint + PROP_LIGHT.
- R2: trophy seen from above, handles thin; house too small/thin roof; hourglass thin with tiny caps; hearts too flat
  (heart_curve y 0.84) and orange; coin reward coins small; pile flat -> reshaped all.
- R3: icon arrows' paint followed MODEL space (rolled arrows lit wrong) -> screen-space paint; icon arrows enlarged,
  composition re-laid (distinct from the store icon); hourglass view steeper (too much snow) -> funnel-profile glass
  (the classic hourglass), thinner snow, view pitch 30.
- Finals R1: coins faceted + blotchy paint, arrows' band noisy -> no decimation for coins/arrows; bigger star emblem;
  deeper hearts red; bulb opacity 0.94; stopwatch yaw -16 / crown upright / hand toward 4:30.
- Unconfirmed boosters built last from the V1 frame (after every confirmed entry was at "good").
