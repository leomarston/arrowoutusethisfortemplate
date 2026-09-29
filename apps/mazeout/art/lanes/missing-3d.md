# missing-3d lane: the unbuilt 3D-route ids of SPEC-ui §4.2 (round 3, 2026-09-25)

Scope (orchestrator task): every 3D-route id on SPEC-ui §4.2's unbuilt list -- the shop's Special Offer + five bundle
arts, `rocketOfferScene`, `weeklyContestLogo`, the frost sprite of the hourglass (freeze) booster, the 069 upper-right
island -- plus any other 3D id there (`iconSkyDrum`; `heartBig` and `iconFlagRoll` turned out to be covered, see below).

Copying line: every asset is OUR model rendered by our renderer (mfrender through scene_kit) or painted in code. The
captures (research/shots meta-002/007-013/065/088, 069, 163, 166) were LOOKED AT and measured in pt on gridded crops;
nothing was traced, sampled into an asset or reused. Neutral file names. `art/MANIFEST.json` and `App/` were not
edited; nothing was committed.

## Status table (self-grades at game size, judged side by side with the capture and in place over it)

| id | status | output | reference | self-grade | remaining differences |
|---|---|---|---|---|---|
| bundleSpecial | done | art/ui/out/bundleSpecial@3x.png (176 x 102) | meta-012 (Special card) | B | Same stacks and two big coins on edge as the phone. The left coin on edge faces further right than the phone's, and the phone's glints are warmer and bigger. |
| bundleBag | done | art/ui/out/bundleBag@3x.png | meta-012 (Mini) | B | Crimson sack, twisted rope with a knot and two ends, a lavender base and stacks either side. The rope ends hang straighter and the rolled rim is thinner than the phone's. The coins in the mouth sit a little lower. |
| bundleBarrel | done | art/ui/out/bundleBarrel@3x.png | meta-008 (Epic) | B | Crimson staves, a lavender hoop, a jagged hole with coins pouring out, a broken stave, and stacks. The phone's barrel is squatter with fatter staves, and its spill is fewer, bigger coins. |
| bundleChest | done | art/ui/out/bundleChest@3x.png | meta-008 (Elite) | B- | Red chest, lavender frame, pink gem and coin heap. The phone's chest is turned to show its left end and fills more of the card. Its lid is a barrel thrown back with the gem on the front edge; ours reads flatter and more frontal. |
| bundleSafe | done | art/ui/out/bundleSafe@3x.png | meta-008 (Mega) | B | Lavender safe, open door with its wheel, and coins pouring out. The phone shows the door's wheel face-on at the far left; ours shows the door edge-on with its bolts. |
| bundleCart | done | art/ui/out/bundleCart@3x.png | meta-010 / meta-009 (Legendary) | B- | Crimson plank cart, lavender posts and wheels, a huge heap spilling to the ground. The phone's heap is a taller pyramid of fewer, BIGGER coins facing the viewer; ours is a wider mound of smaller coins. |
| rocketOfferScene | done | art/out/rocketOfferScene@3x.png (330 x 504, full bleed) | 163 | B | Stars, the banded planet, the lilac moon with craters, the gold/teal chest in a coin mound with a heart, and a pink cloud bank. The phone's hoard sits on a visible bluish rock slab, its coins are brighter, and its clouds are softer. |
| skyJumpIslandFar2 | done | art/out/skyJumpIslandFar2@3x.png (144 x 132) | 069 (upper right) | B | The purple-chest island is paler, seen from higher, with the chest set back. The phone's island has more coin stacks round its chest. |
| iconSkyDrum | done | art/ui/out/iconSkyDrum@3x.png (57 x 52) | meta-002 (Profile stats) | B+ | The pink cushion, cream rings, gold belt with its plate, purple foot and cyan glow all match. The phone's drum shows a touch more of the top. |
| planetStage1 / 2 / 3 | done | art/ui/out/planetStage{1,2,3}@3x.png (60 x 60, 60 x 60, 104 x 60) | 163 (stage strip) | B- | Not on SPEC-ui §4.2's list, but §2.17.1 / 2.17.2 draw them (see below). The sizes and placement match. The phone's bands are broader and more contrasted, and its ring is thicker and glassier. |
| weeklyContestLogo (+ TR) | done | art/ui/out/weeklyContestLogo@3x.png, weeklyContestLogoTR@3x.png (277 x 54) | meta-013 | B | Yellow "Weekly" + white "Contest" with bevels, a blue outline, a cyan rim and an extrusion. The phone's face is rounder with a taller x-height; ours uses the game's OFL font (PC Display Black). |
| fxFrostVignette | done | art/ui/out/fxFrostVignette@3x.png (393 x 852, full bleed) | meta-065 (vs pre-freeze meta-064) | B | Streaky cyan edge ice, a translucent white haze, fine cracks and sparkles, with a clear middle. The phone's side ice is a little more saturated and its corner cracks are denser. |

Evidence (gitignored, regenerate below): `art/ui/sheets/m_<id>.png` (manifest_sheets: ref | ours | in place | alpha)
and `art/ui/sheets/m3d_<id>.png` (the lane's proofs: ref | ours on the card ground | ours in place, at 1x and 2x).

## The ids vs SPEC-ui §4.2 (decisions the art director merges)

1. **Bundle ids name what is drawn.** §4.2 proposed `bundleBag, bundleChestRed, bundleChestPurple, bundleSafe, bundleCart`
   for Mini, Epic, Elite, Mega and Legendary. The phone disagrees on two of them:
   - Epic (meta-008) is a BARREL. It ships as `bundleBarrel`.
   - Elite is a RED chest with lavender trim. It ships as `bundleChest`.

   The Special Offer card also has its own art: the 1 000 pile at 1.23x plus glints. It ships as `bundleSpecial`,
   because SPEC-ui 2.12.2's `coinPackMedium` is the wrong pile and the wrong size there.

   **Shell:** these are the ids to reference. `bundleChestRed` and `bundleChestPurple` do not exist.
2. **One frame for every bundle card:** 176 x 102 pt.
   - Its top-left sits at (16, card top + 7.7), which is (16, cream top − 1).
   - The Special card uses (16, 200).
   - Each art is fitted inside that frame to its measured bbox and bottom-aligned, so the shell places all six at the same
     offset.
   - The amounts ("2 000" …) are live text over the art's lower right, exactly as on the phone.
3. **`weeklyContestLogo` is one raster per language (EN + `weeklyContestLogoTR`)**, not SPEC-ui's B1 live-text EventLogo.
   - Why: the lettering IS the art (bevels, outline, cyan rim, extrusion), as with `logoArrowOut`, and the owner ships
     only EN + TR.
   - How the shell uses it: it picks the file by the app language.
   - The alternative: `m3d_events.build_weekly_logo` is the full layer recipe, and it ports 1:1 to a SwiftUI EventLogo
     if the owner prefers live text. That is the director's call.
   - The frame is 277 x **54** pt. SPEC-ui says 50, but the 'y' descender plus the outline and extrusion reach y 245.
4. **`fxFrostVignette` is one full-screen raster, not SPEC-ui's code vignette (A) + a 120 pt crack tile.**
   - The missing-svg lane already ships the crack tile, `frostCracks`.
   - This overlay CONTAINS cracks along every edge. Use it ALONE, or use the code vignette + `frostCracks`, **never
     both**.
   - Layer it between the board and the HUD: on 065 the HUD and boosters stay crisp above the frost.
5. **`heartBig` belongs to the missing-svg lane** (an SVG, shipped at art/ui/out/heartBig@3x.png; §4.2 had said B3).
   - I built a 3D heart before I saw their entry, and my first final render overwrote their file at 14:19. Their lane
     re-rendered it at 14:20 (it is 582 x 492 again, theirs).
   - My heart is now a ROUTE CANDIDATE only, at `build/ui-art/route3d/heartBig.png`, for comparison. It is a harmonic
     inflation of meta-088's outline, with painted highlights. It is never written to art/ui/out.
6. **`iconFlagRoll` is not built.** Round 2 ruled that the capsule-only `scoreChip` IS that sprite (REVIEW.md "Still
   missing").
7. **Extras not in §4.2:** `planetStage1..3`. SPEC-ui 2.17.1 (offer stage strip) and 2.17.2 (tutorial) draw three stage
   planets, and no manifest id covered them. Their frames on 163 are (62, 427), (165, 427) and (247, 427).
8. **`skyJumpIslandFar2`:** frame 144 x 132 at (213, 214). Draw it after skyJumpBackdrop and before the pads, like
   `skyJumpIslandFar`.

## Files (this lane only)

- `art/ui/recipes/m3d_kit.py`: the lane toolbox. It holds coin heaps on domes (`heap_poses`), solid heap cores so the
  gaps read gold, stacks, the painted toy material (`painted`, with the uv fix below), the shop light, glints, contact
  shadows and edge fades. It reuses 3d-events_coins.py (the shop coin) and 3d-hud_props.py (toon schemes) READ-ONLY.
- `art/ui/recipes/m3d_shop.py`: the six shop arts (BUILDS).
- `art/ui/recipes/m3d_events.py`: rocketOfferScene, skyJumpIslandFar2, iconSkyDrum, the planets and the Weekly lettering.
  It uses scene_events.py's models READ-ONLY.
- `art/ui/recipes/m3d_fx.py`: fxFrostVignette and the heartBig3d candidate.
- `art/ui/recipes/m3d_make.py`: the driver, which checks the memory rule. `art/ui/recipes/m3d_proofs.py`: the lane's
  proof sheets.
- The scratch manifest is `art/lanes/missing-3d.entries.json` (15 entries).

```
PY=~/.venvs/mf3d/bin/python                              # from apps/mazeout; one render process, MF_WORKERS=2
$PY art/ui/recipes/m3d_make.py list
$PY art/ui/recipes/m3d_make.py build bundleBag [...] [--draft]     # all 16 builds: ~1 min with warm mesh caches
$PY art/ui/recipes/m3d_proofs.py bundleBag [...]                   # -> art/ui/sheets/m3d_<id>.png
$PY art/tools/manifest_sheets.py --manifest art/lanes/missing-3d.entries.json <ids>
$PY art/tools/manifest_check.py --quiet --lanes art/lanes/missing-3d.entries.json   # the lane's 15: 0 failing
```

**For the pipeline keeper.** `art_batch.py --3d` cannot rebuild these entries, because the modules have BUILDS, not
ASSETS. It hits the same gap as the scene lane's request 1 in requests.md. Until it grows a BUILDS path, rebuild them
with `m3d_make.py`.

## Method notes and gotchas (for whoever iterates next)

- **The painted toy material's uv wraps.** 3d-hud_props.tpart sets u = 1 − n·z, which is 0 on a surface facing the
  camera. The sampler repeats, so u = 0 fetched the far EDGE colour: a dark spot on the apex of any dome (heartBig3d,
  round 3).
  - `m3d_kit.painted` squeezes u and v into 0.02..0.98 and un-squeezes them in the texture.
  - The same bug may sit in the 3d-hud lane's props wherever a face points straight at the camera. I did not edit their
    file.
- **The mesh cache does not see the kit.** scene_kit.model_hash walks functions and constants, but not modules
  (`MK.`, `EC.`). After editing m3d_kit.py, delete `build/ui-art/scene/usdz/m3d_*/*.hash`, or the old meshes are
  reused.
- **Heaps.**
  - A heap is ONE coin layer on a dome (`heap_poses`), with coins tilted toward the viewer by `face`.
  - A heap without a solid core shows the card through its gaps, which reads as grey holes. `heap_core` fills them with
    a satin gold mound of the same profile.
  - `depth` jitters coins into the core so the surface is not a regular hex tiling.
- **Inflating a 2D outline.** Solve laplace(h) = −1 DIRECTLY (a sparse solve on ~20k pixels takes 0.3 s). Jacobi sweeps
  never converge on a 300 px grid; they left a flat plateau with a rim, which showed as a ring on the heart.
- **Scene reuse.** The Elite chest is scene_events.chest stretched (scale_xyz on every part's SDF). The rocket hoard is
  scene_events' rock / chest_gold / rr_hoard / heart plus our coin mound (`roStacks`), seen at pitch 15 rather than the
  race page's 40.
- **Frost.** It has two bands, measured on 065:
  - a streaky cyan ice band: sides ~14 pt, top ~34, bottom ~26, deeper in the corners;
  - a translucent white haze: sides ~46 pt, top ~120, bottom ~112, alpha ≤ 0.8. The board shows through it.
  - Round 1 was opaque white 60+ pt deep and hid the doors.

## Next pass (A candidates, one each)

- `bundleCart`: fewer, bigger coins (≈20 pt) stacked into a taller pyramid that faces the viewer.
- `bundleChest`: yaw the chest about −25° so its left end shows, fill the card, and model the thrown-back barrel lid.
- The planets: broader, more contrasted marbling.
- `rocketOfferScene`: brighter coins and the rock slab's front face.
- `weeklyContestLogo`: a rounder face (or the SwiftUI port).
