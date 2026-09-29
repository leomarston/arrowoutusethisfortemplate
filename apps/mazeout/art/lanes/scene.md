# Scene lane (3D scene illustrations) — Arrow Out

Lane: **scene** (16 manifest entries). Every entry is done at the "good" bar: our 3D models (hand-written SDF / analytic
meshes, rendered by mfrender with one light rig per scene) over structure painted in code. The captures
(research/shots, research/web, the owner's video frame) were LOOKED AT and measured in pt on gridded crops only.
Nothing was sampled into an asset, traced or reused; every colour is a hex chosen here against measured tones.
The art director merges the table below into `art/MANIFEST.json`. I did not edit the manifest or any shared pipeline
file.

## Status table

Self-grade: A = a player takes it for the same art at game size, B = the same thing in the same style (visible
modelling differences at 2x), C = recognisable, with clear shape or detail misses.

| id | status | output | reference used | self-grade | remaining differences |
|---|---|---|---|---|---|
| homeBackdrop | done | art/out/homeBackdrop@3x.png (393x852, full bleed) | 002 (+026) | B | Painted walls are cleaner than theirs: no metal texture on the tank, and softer panel seams. The copper bell pipe on the right is duller. The glass tank's blue glow is a painted gradient, not a lit cylinder. The capsule machine's wall shadow is baked here, because the machine is static. |
| homeConsole | done | art/out/homeConsole@3x.png (214x109) | 002 | B | Their tub bulges more at the belly and has a warm-yellow gradient; ours is a cooler cream. The joystick ball is smaller, and the lever handle is flatter. |
| homeCapsuleMachine | done | art/out/homeCapsuleMachine@3x.png (206x215) | 002 | B | The bezel is a flat glass-blue ring; theirs is a slanted light cyan inner wall. The glass sheen is two painted blobs. The dispenser ring is a little flatter. The LEVEL recess is a blank well: the plate and "LEVEL" are UI. |
| homeArrowPileFull | done | art/out/homeArrowPileFull@3x.png (186x126) | 002 | B | Their heap is a wider, flatter mass that reaches the bezel on both sides, and nearly every arrow faces the camera. Ours peaks in the middle, and a few arrows show their edges. |
| homeArrowPileHalf | done | art/out/homeArrowPileHalf@3x.png (186x126) | 168 / 204 | B- | Their stream is one vertical orange arrow plus one lilac arrow under the dispenser. Ours has three arrows in the stream plus an emerging arrow. |
| homeArrowPileLow | done | art/out/homeArrowPileLow@3x.png (186x126) | 070 | B | Their emerging arrow is green and shows its shaft; ours is cropped by the ring holdout to a triangle. |
| homePlatform | done | art/out/homePlatform@3x.png (393x182) | 002 | B | Their dais is glassier: it has a mirror-like reflection of the blue wall in its back half. Ours shows this as a painted gradient. The workers' contact shadows are baked in at the rigs' feet anchors. |
| loadingBackdrop | done | art/out/loadingBackdrop@3x.png (393x852, full bleed) | V1 t=0 (refcrops/loadingBackdrop.png), store 8 | C+ | Our machine at the left is painted flat panels; theirs is a detailed blue/pink press with a lilac girder. The background crowd of workers (top hat, burger) and the conveyor are missing. Our floor tiles are more regular. The arrows' motion blur and depth of field are missing. |
| clawHeaderArt | done (workers pending) | art/out/clawHeaderArt@3x.png (393x240, full bleed) | 023 | B- (without workers) | The characters lane's `workerClawPair` does not exist yet. When `art/out/char_workerClawPair@3x.png` lands, re-run the build: it is composited behind the prizes, centred at (200, 115) pt. Our glass box edges are thinner. Their prize heap has more arrows and bigger hearts. The claw's prongs are rounder than theirs. |
| skyJumpBackdrop | done | art/out/skyJumpBackdrop@3x.png (393x852, full bleed) | 069 | B | Our cloud banks are procedural puffs, less sculpted than theirs; the far banks lack their violet underside. |
| skyJumpPad | done | art/out/skyJumpPad@3x.png (112x104) | 069 pad "4" | B | Our cream rings are a little whiter and taller. The number plate face is blank: the digit is live text. |
| skyJumpIsland | done | art/out/skyJumpIsland@3x.png (238x180) | 069 main island | B- | Their PRIZE sign overlaps the chest's left corner and sits lower; ours stands left of the chest. Their coin stacks are taller around the chest. The sign face is blank for live text. |
| skyJumpIslandFar | done | art/out/skyJumpIslandFar@3x.png (148x110) | 069 upper-left island | B | This is the blue-chest variant. The purple-chest variant (upper right on 069) exists as the models `island_farR` + `chest_purple`, but has no manifest id. Their far islands are heaped higher with coins. |
| skyJumpPopupScene | done | art/out/skyJumpPopupScene@3x.png (330x190) | 065 | B- | Their coin hill is denser and oranger and reaches the frame corners. Their chest lid shows the quilt from a lower angle, with the shield hanging over the front. The sign face is blank for live text. |
| rocketRaceBackdrop | done | art/out/rocketRaceBackdrop@3x.png (393x852, full bleed) | **167 (phone v552)**, replacing the manifest's web frame | B- | Their hoard is taller and more pyramidal. Their chest is shorter and wider, with a bigger diamond clasp. The moon craters are painted rims. The lane area below the header is a plain gradient with stars, because the lane art is UI. |
| leaderboardPodium | done | art/out/leaderboardPodium@3x.png (389x206) | meta-013 (phone v552) | B | The rank badges are blank hexagons (digits are live). Their caps have a brighter top face; ours are flatter-lit. The name, coin stack and score chip on the front panels belong to other lanes or are live. |

**Unconfirmed**: `rocketRaceBackdrop` is marked `confirmed: false` in the manifest, but the phone has the screen (shots
163-189, 167 is the Rocket Race screen). I built it from 167. Please set `confirmed: true` and point its ref at 167.

## Proposed manifest changes (the art director merges these)

| id | field | from | to | why |
|---|---|---|---|---|
| all 16 | source | `art/ui/recipes/scenes.py:<id>` | `art/ui/recipes/scene_home.py:<id>` (home*), `scene_events.py:<id>` (sky*, claw, podium, rocket), `scene_loading.py:<id>` | The recipes are split per screen. They define `BUILDS` (not `ASSETS`); the driver is `scene_make.py`. See requests.md. |
| all 16 | status | todo | done | |
| homeConsole | size_pt, ref.box_pt | 214x100, [95,272,309,372] | **214x109**, [95,266,309,375] | The 100 pt frame clipped the joystick ball and the base. |
| homeCapsuleMachine | size_pt, ref | 206x180, 026 [95,365,301,545] | **206x215**, 002 [95,365,301,580] | The housing goes down to the floor (y 577); the old box cut it at the LEVEL plate. |
| homeArrowPile{Full,Half,Low} | size_pt, ref.box_pt | 170x110, [112,410,282,520] | **186x126**, [104,402,290,528] | The pile overlaps the bezel. Half: ref 168 (not 026). |
| homePlatform | size_pt, ref.box_pt, full_bleed | 360x150, [16,580,376,730] | **393x182**, [0,576,393,758], `full_bleed: true` | The dais is wider than the screen on 002. |
| homeBackdrop | ref | 026 | 002 | This lane's brief names 002. |
| clawHeaderArt | notes | "" | "workers = char_workerClawPair composited at build time (centre 200,115 pt); rebuild after it lands" | |
| skyJumpPad | size_pt, ref.box_pt | 106x80, [55,505,161,585] | **112x104**, [51,503,163,607] | Includes the cyan hover glow under the drum. |
| skyJumpIsland | size_pt, ref.box_pt | 230x170, [78,345,308,515] | **238x180**, [74,342,312,522] | |
| skyJumpIslandFar | size_pt, ref.box_pt | 140x100, [18,250,158,350] | **148x110**, [14,246,162,356] | |
| rocketRaceBackdrop | ref, confirmed | yt_frames/dazecheck..., false | `research/shots/167-rocket-race-screen.png` [0,0,393,852], **true** | The phone has it. |
| leaderboardPodium | size_pt, ref | 340x190, yt_frames/gamemobie | **389x206**, `research/shots/meta-013-leaderboard-weekly.png` [2,294,391,500] | The phone has it. |

A ready-made manifest subset with these values: `build/ui-art/scene/scene_manifest.json` (16 entries). `manifest_check.py
--manifest build/ui-art/scene/scene_manifest.json` gives 16 ok, 0 failing (RGBA, exact size x3, not empty, and no
edge contact except the full-bleed entries). Side-by-sides: `manifest_sheets.py --manifest
build/ui-art/scene/scene_manifest.json --all` writes `art/ui/sheets/m_<id>.png`.

## Home composition (for the shell / engine)

Every home layer is a frame at a fixed screen position (pt, top-left on the 393x852 home screen). Back to front:

| z | layer | frame x, y (pt) | size (pt) | notes |
|---|---|---|---|---|
| 0 | homeBackdrop | 0, 0 | 393x852 | Includes the machine's wall shadow. |
| 1 | char_sci_home_rig: torso + head (+ lids / headOpen swaps) | rig.json `placement_pt` (104.08, 172.33) | 190x164 | characters lane |
| 2 | homeConsole | 95, 266 | 214x109 | Covers the scientist's lower torso. |
| 3 | char_sci_home_rig: armL, armR / armR_point | as rig.json | | Hands rest on the console top. |
| 4 | homePlatform | 0, 576 | 393x182 | Includes the workers' contact shadows. |
| 5 | homeCapsuleMachine | 95, 365 | 206x215 | |
| 6 | homeArrowPile{Full,Half,Low} | 104, 402 | 186x126 | Registered to the machine's window; same camera as the machine. |
| 7 | UI: LEVEL caption + plate (the plate 147.5..246 x 536.8..569 pt sits in the machine's recess, about 144..250 x 533..572 pt), Play frame / button, top bar, Claw bar, nav | ui-measure.md | | |
| 8 | char_wk_homeL_blue_rig, char_wk_homeR_blue_rig | rig.json `placement_pt` (11.37, 490.67), (242.26, 490.33) | 150x132 each | They stand in front of the machine's lower corners. |

Proof (our layers only, next to 002 at the same scale): `art/ui/sheets/scene_home_proof.png` (+ `_half.png`). Loading:
`art/ui/sheets/scene_loading_proof.png`. Rebuild both with `scene_make.py proof home loading`.

**Pile rule (observations, not a rule).** L32-L39 (shots 002, 026, 035, 051, 060) show the same full pile. L40 (070)
shows ~6 arrows plus one emerging. L55 (168) and L62 (204) show a half heap plus a stream from the dispenser. The pile
is not monotonic in the level, so it may cycle or be driven by something else (for example a win animation state). The
content / meta analysts should decide which variant shows when; all three variants ship.

## Live-text anchors (text is never baked)

| id | element | box inside the frame (pt) |
|---|---|---|
| skyJumpPad | number plate face (pink) | 46..67 x 53..72 (centre 56.5, 62.5) |
| skyJumpIsland | PRIZE sign face (green) | 44..104 x 9..40; the coin disc sits at its left end, and the text goes right of it |
| skyJumpPopupScene | PRIZE sign face | 35..131 x 16..62; coin disc at the left end |
| leaderboardPodium | rank hexagons (approx. ±3 pt) | silver centre (64, 55), gold (193, 25), bronze (324, 67) |
| homeCapsuleMachine | LEVEL plate recess | about 49..155 x 168..207 in the frame = screen 144..250 x 533..572 (the UI's 147.5..246 x 536.8..569 plate fits inside) |

## Files (this lane only)

- `art/ui/recipes/scene_kit.py`: the lane's toolbox, not a recipe. It has a per-model mesh cache keyed by a hash of
  the model function plus everything it references, premeshed lathe / grid surfaces, instanced meshes (hundreds of
  coins meshed once), batched sprite renders through `ui3d.scene_job` / `run_job`, a float canvas with paint helpers,
  clouds, colour grading and the memory-rule check.
- `art/ui/recipes/scene_home.py`: home models + BUILDS (7 ids).
- `art/ui/recipes/scene_events.py`: coins, chest, sign, islands, pad, claw + prizes, podium, rock + BUILDS (8 ids).
- `art/ui/recipes/scene_loading.py`: loading models + painted structure (1 id).
- `art/ui/recipes/scene_make.py`: the driver. It checks the memory rule before each render batch and refuses to start
  (rather than sleeping) when swap is low.
- `art/ui/recipes/scene_proofs.py`: composed home / loading proofs.
- Caches, raws, drafts and the scratch manifest go to `build/ui-art/scene/` (gitignored).

```
PY=~/.venvs/mf3d/bin/python
$PY art/ui/recipes/scene_make.py list
$PY art/ui/recipes/scene_make.py build homeConsole [...] [--draft]     # -> art/out/<id>@3x.png
$PY art/ui/recipes/scene_make.py proof home loading
```
A full rebuild of all 16 ids takes about 3 minutes with warm mesh caches (renders take about 1 s each; the backdrop
composites take about 10-30 s). The first mesh of the home backdrop objects takes about 80 s.

## Method and iteration notes

- **Home.** Walls were painted from measured column / row tones (tank glow, ledge lip, lower wall, deck rim, cream
  wall, blue band, floor). The pipes, valve, flanges, vents, railings and lamps are 3D in screen-registered world
  coordinates (x = sx/10, y = -sy/10): one render with a near-orthographic camera (fov 3) over the screen rectangle,
  so every object lands on its measured spot. Iterations:
  - v1 cavity too dark and shallow, arrows too small (20 pt), console too flat, platform too light. Fixed: cavity walls
    split light / dark, the camera tilted 11 deg so the floor hatch shows, arrows 33 pt with chunkier heads, console
    height 5.0, platform graded.
  - The key light's hard shadow put a black wedge in the cavity and on the console; the key shadow is now off for
    those two renders, and 2D soft shadows are used instead.
- **Arrow pile.** Our own copy of the painted-bevel method (arrows3d) with five colours, whose ladders were measured
  from 002's window pixels (dark / mid / light per hue). The pile renders with the machine's camera and bounds, so it
  registers to the window exactly. The half and low variants hold out the dispenser ring so the emerging arrow comes
  out of it.
- **Sky Jump.** Pad v1 was too flat. v2-v4 re-proportioned the bands (cream / gold / cream / purple) and the camera
  pitch against the "4" pad. Chest v1 had its lid thrown back showing the lining; v2 opened it 52 deg with the quilt
  outward and the shield on the raised edge. The island is a clover-shaped extrusion stack (cream / gold / purple), with
  the purple base faded into the clouds.
- **Claw.** Prizes were 2x too small in v1 (bulb r 12 vs 20 pt). v2 scaled prizes and blocks to the measured sizes and
  thickened the prongs.
- **Podium.** v1 was over-lit (washed-out gold, pale lilac). v2 lowered the key and fill, saturated 1.2, made the
  hexagons bigger, and put the gold block in front of its neighbours.

## Known gaps (honest list)

- `clawHeaderArt` ships without its workers until the characters lane renders `workerClawPair`.
- `loadingBackdrop` is the weakest entry (C+): the left machine is flat painted panels, and the background crowd and
  conveyor are missing. The characters lane's note offers its top-hat / burger avatar models; rendering a small crowd
  from them is the next step.
- No glass pane is rendered on the capsule machine (painted sheen only), and no reflections are rendered on the
  platform.
- The second far island (purple chest, upper right on 069) has models but no manifest id. Add `skyJumpIslandFar2` if
  the screen needs it: `_island_build("farR", ...)` builds it.
