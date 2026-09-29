> **OWNER DECISION 02:55 — WORKERS ARE BLUE.** Do not pick red. Use a blue that clearly separates from the blue lab background (brighter/more saturated body + warm rim light); tune it on the home and loading compositions. The scientist stays PINK.

# Characters lane (3D) — Arrow Out

Owner update 02:33 (overrides PLAN.md's DECISION 02:05 axolotl "Doc" + gumdrop worker): the characters are the
ORIGINAL's designs reproduced 1:1 as OUR OWN 3D models (modelled from scratch in SDF, rendered by mfrender), with only
their COLOURS changed. Brief (owner, verbatim): "the little monsters on the background can be a different color, like
blue or red, and the top monster can be like pink or sth so that we dont face copyright issues. Other than that you can
do 1:1 same."

Copying line: the captures (research/shots, research/store, research/web) were LOOKED AT only. Nothing in art/out or
the rigs derives from their pixels: every shape is an SDF written by hand from measurements (pt), every colour is a hex
chosen here (the reference's HSV statistics are used as targets, never sampled into a texture).

Files (this lane only)
- recipes: `art/pipeline/items/char_scientist.py`, `char_worker.py`, `char_avatars.py`, `char_loading.py`,
  `char_events.py` (Claw + Streak Race headers) (+ helpers `char_kit.py`, `char_fur.py`, `char_props.py`, driver
  `char_make.py`); SVG: `art/ui/src/characters/gen_avatars.py` (avatarDefault)
- renders + rigs: `art/out/char_*` (+ `art/ui/out/avatarDefault@3x.png`) · sheets (gitignored): `art/ui/sheets/char_*`,
  `art/ui/sheets/m_<id>.png`
- scratch manifest for the art director: **`art/lanes/characters.entries.json`** (27 entries: full objects with the real
  `file` / `source` / `size_pt` / `status` / `ref` / notes, 4 NEW ids). `manifest_check.py --quiet --lanes
  art/lanes/characters.entries.json` -> every characters entry passes (the remaining failures are other lanes').
- the superseded axolotl: `art/scratch/doc_axolotl/` (never shipped)

Commands (from apps/mazeout; `PY=~/.venvs/mf3d/bin/python`)
```
$PY art/pipeline/items/char_make.py list
$PY art/pipeline/items/char_make.py render <case> [--draft] [--force]
$PY art/pipeline/items/char_make.py rig <name> [--skip-render]   # layers -> art/out/char_<name>_rig/ + rig.json + proof (+ bake)
$PY art/pipeline/items/char_make.py sheet <name>        # home_detail | sci_home | wk_home | avatars | loading (rewrites char_loading_layout.json)
$PY art/tools/art_batch.py --manifest art/lanes/characters.entries.json --svg --ids avatarDefault
$PY art/tools/manifest_sheets.py --manifest art/lanes/characters.entries.json <id> ...
```

## Status table (2026-09-25 ~09:20; the art director merges `characters.entries.json`)
Self-grade: A = a player takes it for the same art at game size (colour aside), B = the same thing in the same style,
visible modelling differences at 2x, C = recognisable, clear shape/detail misses.

| id | status | output path | reference used | self-grade | remaining differences |
|---|---|---|---|---|---|
| scientist | done | `art/out/char_sci_home_rig/` (+ full `char_sci_home@3x.png`, 190 x 164 pt, placement (109.23, 176.52)) | 002 (in place) | B | Coat has no fold lines; mitten hands; their brows are a touch thinner; the pointing layer's fist hides the curled fingers (reads as a finger up at 1/3, ambiguous at 2x). Scale + placement now match 002 (see v6 below). |
| workerWalkie | done | `art/out/char_wk_homeL_blue_rig/` (placement (18.04, 483.66)) | 035 / 026 / meta-056 rest frames (002 is mid-animation) | B- | Walkie held up by the face (their rest frame holds it forward at the machine); arms slimmer; no toes. |
| workerClipboard | done | `art/out/char_wk_homeR_blue_rig/` (placement (244.93, 483.33)) | 035 / 026 / meta-056 | B- | Clipboard shows the paper side; cap sits flatter. |
| scientistLoading | done | `art/out/char_scientistLoading@3x.png` (318 x 306) | V1 t=0 + store 8 | C+ | P1 outfit gap: their coat has rolled short sleeves over a white shirt; their fist punches toward the camera (ours raised beside the head). |
| workerCarrier | done | `art/out/char_workerCarrier@3x.png` (236 x 400) | V1 t=0 + store 8 | B- | Their box shows its side face and sits lower. |
| workerFlyer (NEW id) | done | `art/out/char_workerFlyer@3x.png` (170 x 220; v1 clipped the feet) | V1 t=0 + store 8 | B- | Their arrow is a little wider. |
| workerFist (NEW id) | done | `art/out/char_workerFist@3x.png` (208 x 212) | V1 t=0 + store 8 | B- | Notebook is our clipboard (no spiral rings). |
| workerRunners | done (P1) | `art/out/char_workerRunners@3x.png` (112 x 164, layout z -1 at (290, 350)) | V1 t=0 | C+ | Ours ~15 % smaller than their crowd; the left-background conveyor pair is not built. |
| workerClawPair | done | `art/out/char_workerClawPair@3x.png` (360 x 170, full bleed at the bottom by design) | 023 | B- | Their left worker is turned further to the right with a bigger laugh; their caps sit further back. The scene lane must re-run clawHeaderArt (see "for other lanes"). |
| workerRacers | done (good bar, 25-min rule) | `art/out/char_workerRacers@3x.png` (393 x 290, full bleed) | meta-045 / meta-050 (phone) | C+ | The room is painted flat and simpler (their pipes / machines are modelled and busier); the small riders float on the chute rim instead of sitting in it; the checkered banner is hidden under the chute's exit; no motion streaks. Layout / track / riders read as theirs at game size. |
| avatarDefault | done | `art/ui/out/avatarDefault@3x.png` (64 x 64, full bleed) | meta-003 cell 1 | A- | Their tile has the frame's inner shadow (UI). |
| avatarWalkie | done | `art/out/char_avatarWalkie@3x.png` (64 x 64) | meta-003 cell 2 | B- | Their cap is a small kepi; id kept although cell 2 shows no walkie. |
| avatarCapGlasses | done | `art/out/char_avatarCapGlasses@3x.png` | meta-003 cell 3 | B- | Their pose leans further in; one hand holds a pencil. |
| avatarDetective | done | `art/out/char_avatarDetective@3x.png` | meta-003 cell 4 | B- | Trench collar simplified. |
| avatarBurger (NEW id) | done | `art/out/char_avatarBurger@3x.png` | meta-003 cell 5 | C+ | Their burger is bigger and in the open mouth (a bite); their eyes huger. |
| avatarScientist | done | `art/out/char_avatarScientist@3x.png` | meta-003 cell 6 | B- | Plate VIOLET (theirs pink: ours is a pink character, deliberate); their free hand holds an orange clipboard. |
| avatarParty | done | `art/out/char_avatarParty@3x.png` | meta-003 cell 7 | B | |
| avatarNotebook (NEW id) | done | `art/out/char_avatarNotebook@3x.png` | meta-003 cell 8 | B- | Plate SUNNY yellow (theirs sky blue: our blue worker vanished on it, deliberate); spiral notebook = our clipboard. |
| avatarBoxHead | done | `art/out/char_avatarBoxHead@3x.png` | meta-003 cell 9 | B- | Their box is cropped by the frame top (ours shows its front). |
| avatarGreen .. avatarPink (8, unconfirmed Jul set) | not built | -- | V2 t=60 | -- | Not shipped per SPEC §5.12 (the phone set replaces them); entries carry that note. |

Superseded outputs removed from `art/out` (moved to the session scratch): the 44 pt `char_av<Name>[Cutout]@3x.png` set
(9 + 9), `char_ld_{sci,carrier,flyer,runner}` (+ sidecars; renamed to the manifest ids), `workerHome@3x.png` (the spike
gumdrop worker, manifest `superseded`). Stray-but-needed: `char_loading_layout.json` (the app reads it) and the
`char_<id>.json` anchor sidecars (the layout is derived from them).

**Edit Profile order** (meta-003 row-major, `char_avatars.PROFILE_ORDER`): avatarDefault, avatarWalkie,
avatarCapGlasses, avatarDetective, avatarBurger, avatarScientist, avatarParty, avatarNotebook, avatarBoxHead.

## For other lanes (the characters lane does not edit their files)
- **scene (clawHeaderArt):** `char_workerClawPair@3x.png` now exists (360 x 170 pt; your build centres it at (200, 115)
  -> x 20..380, y 30..200 pt); re-run `scene_make.py build clawHeaderArt`.
- **scene (homePlatform contact shadows):** the worker rigs moved (phone rest frames 026 / 035 / meta-056): feet anchors
  now (85.74, 606.18) L and (318.60, 605.85) R pt; the rendered feet BOTTOMS sit at ~612-613 pt, i.e. on your pools'
  y (613.2 / 612.9) -- only the LEFT pool's x should move 79.1 -> ~85.7 (right 315.9 -> ~318.6).
- **scene (homeConsole):** on the composed home our scientist now matches 002; the console reads smaller than theirs
  (their tub spans ~x 345..1200 px at the rim with a thicker blue lip; the scientist's hands rest on its top).
- **SPEC-ui §2.14 / loading table (spec owner):** the grid order there lists "carrier" at cell 8 and "top hat" at cell 9;
  the phone shows cell 8 = green cap + glasses + fist + notebook, cell 9 = the box carrier, and no top hat. The file names
  `char_av*` / `char_ld_*` are replaced by `char_<manifest id>` (list above); the loading layout JSON already carries the
  new names (LoadingScreen reads it, no code change). The SimPlayer avatar index table should map to the 9 ids above
  (TopHat / Wave portraits no longer exist).
- **shell (UIArt, after the art director's merge):** new ids `avatarBurger`, `avatarNotebook` (Edit Profile cells 5 / 8)
  and `workerFlyer`, `workerFist` (loading; LoadingScreen already gets them through the layout JSON). The 8 Jul-set
  avatar cases in UIArt (avatarGreen .. avatarPink) have no files and are not shipped (SPEC §5.12).

Placement of every home render: `rig.json` -> `placement_pt` (frame top-left on the 393 x 852 pt home screen; the
scientist by his eye whites on 002 (v6: (109.23, 176.52)), the workers by their feet on the phone rest frames 026 / 035 /
meta-056 (v6: (18.04, 483.66) L, (244.93, 483.33) R; v5 used store 7 and sat 21 px low)). Z order on the home screen
(the scene lane): wall < scientist torso + head < console body < scientist arms (hands on the console top, behind its
joystick / lever) ; capsule machine < workers (in front of the machine's lower corners).

## Decisions
- DECISION (fur) — **geometric strand cards** (`char_fur.py`): tens of thousands of thin tapered, camera-facing,
  double-sided ribbons rooted on the SDF skin (area-weighted samples of its marching-cubes mesh), groomed (lift + comb
  in the tangent plane + gravity), CLUMPED toward guide strands (tufts), shaded with the skin normal bent slightly
  toward the strand, coloured through a 3-row LUT texture (u = the character's volumetric obscurance at the root; v =
  underside-shade / root / tip). Rejected: A = smooth skin + noise ripples + soft SDF tuft cones: reads as rubber
  (hammered plastic), no fuzzy silhouette. mfrender has no hair shader, no alpha-tested shells and our USD writer no
  normal maps, but it renders ~1 M triangles in seconds; the head is 560 k strand triangles, the whole scientist ~1.4 M.
- DECISION (pink) — scientist fur ladder at hue 328-338: tips `#FFA8C8`, lit `#FF8AB9`, mid `#FA6BA9`, shade
  `#EB5098`, deep `#D13684`, underside `#B22470`; brows `#801953`/`#61103F`. The reference purple fur measures median
  H 284 S 0.63 V 0.82 (p10 V 0.66, p90 S 0.77); ours H 331 S ~0.6 V ~0.8 -- the same saturation/value ladder, shadows
  deeper and more saturated, only the hue moved (a ~50 deg turn reads as a different character colour at a glance).
  Iris kept dark violet (an eye colour, not the body).
- DECISION (workers) — **BLUE** (owner 02:55; red not rendered): body LUT `#A6E6FF` / `#62CAFF` / `#36B0FF` /
  `#1F8EF2` / `#1264D6` / crease `#0A3CA8` (a light azure: the reference yellow ladder `#FECB39`/`#FBB510`/`#EE9B0D`/
  `#D07405` slides hue + gains saturation into the shade; ours slides from azure toward cobalt). Separation from the
  blue lab: lighter value than the wall band (`#2F7FF0`), + a WARM rim light (1.0, 0.80, 0.55; 2600 lux from the
  right-back) + clearcoat 0.25. Compared on the home plate: blue v1 (`#25A2FB` mid, cool rim) blended into the wall;
  cyan-blue (`#27B8F5`) separated slightly better but drifts toward teal; the final lighter azure keeps "blue" and
  separates by value + rim (sheet `char_wk_colour.png`).
  Clothes/props keep the original's colours (indigo shorts, brown belt, lilac-grey buckle + wrench, navy / green caps,
  black-grey glasses, navy walkie with red button, red-brown clipboard): none clashes with the azure body (the navy
  cap and indigo shorts are 40-50 % darker in value), so nothing was adjusted.
- DECISION (rigs) — every rig is rendered by the pipeline's `rig.py` (explicit layers from `char_kit.explicit_rig`,
  one shared camera, holdout mattes for the layers behind) and then BAKED by `char_make.py`: where a default layer is
  top-most, its colour becomes the full render's, so the default pose recomposes the full render exactly, cast shadows
  included (the scientist's proof: mean |d| 1.39/255 -> 0.12/255, 1.6 % -> 0.004 % px > 40).

## Measurements (pt = px x 393 / 1178 on the phone shots; store shots 1320 px wide map to the phone by x 0.8924)
Scientist (002, phone px): head incl. fur x 488..755 (267 px widest, y 669), top 530 (crown tuft), jowl bottom 784;
eye whites L 571..608 x 600..646, R 624..665 x 607..656 (midpoint 617, 627 px = 205.9, 209.2 pt); pupils low + inner;
brows L 574..611 x 576..589, R 635..672 x 581..608; closed smile 540..702 px; head rolled ~9 deg clockwise; coat rows
(half-widths about x 627): y 720 502..744, 780 443..804, 850 408..846; console top y ~890; badge 560..617 x 815..857.
Scale: 1 u = 200 phone px = 66.8 pt. Our head (render, same scale): widest 244 px (tufts), eyes 39 x 46 / 40 x 41 px.
Workers (s7 at phone scale; 002 is an animation frame; v6 target = the phone rest frames: feet bottoms 1835-1840 px, feet
x L 191..343 / R 872..1025, green cap top 1472-1488 px): LEFT feet centre (237, 1838) px, RIGHT (947, 1837) px; standing
height feet -> cap top ~347-360 px; body ~1.3 u wide at the eyes. Scale: 1 u = 171 phone px = 57 pt. Ours: 353 / 358 px
tall incl. cap and props.

## Iteration log
Self-grades are the lane's own (A = indistinguishable at game size except the colour, B = same character, visible
modelling differences at 2x, C = recognisable, clear shape/detail misses, D = off-model). The art director grades later.

### Scientist
- v0 fur spike (head only, 104 x 92 pt at game scale): A smooth+ripples reads rubber (C-); B strands reads fur
  (C+: silhouette IoU 0.893 vs the reference head mask; brows mottled, smile too heavy, too magenta).
- v1: taller dome, bigger eyes, brows as their own dark-fur part, thinner smile, 3-row fur LUT with an underside row,
  lighter candy palette -> IoU 0.914; colour stats ours H331 S0.55 V0.80 vs ref H284 S0.63 V0.82 (under-saturated).
- v2: saturation ladder +0.1 (S 0.61 median), crown tuft = its own strongly clumped strand set, brows lower/thicker,
  bigger iris -> IoU 0.913; brows now read as a frown (too low, on the eyes).
- v3 (full body): bell torso (ellipsoid stack after the revolved spline made meshing 3x slower), coat shell with front
  opening + facings, collar flaps, crew neckband, lanyard V + badge, pocket + purple pen, sleeves + cuffs, furry mitts
  (5 k hand strands each), head rolled -10; aligned on the eye midpoint. Eyes 10 % too small, jowls sat above the
  collar (bottom 768 vs 784 px), hands under the console rim.
- v4: torso -0.06, head +0.04 forward, wider cheek tufts, arms on the console top and wider apart, lighter candy
  palette (tips `#FFA8C8`), friendly brows with a gap; rig + bake; sheet `char_sci_home.png`. Open mouth: teeth hidden
  by the solid back wall, then a mouthguard bar, then fixed (back wall behind the teeth, lip fur combed away).
  Self-grade **B**: same character, same pose/proportions and face at game size, fur reads as fur; misses: the coat
  is cleaner/puffier than theirs (no fold lines), the pointing hand is a mitten, the open-mouth teeth band is smaller.

### Workers
- v1: egg body, huge dark lid crescents ("sunglasses"), pancake cap, tiny walkie, noodle arms (D).
- v2-v4: lid line = a tube on the eye's top contour; the black stubs identified as floating BROWS (not antennae);
  bigger D mouth with two front teeth; cap rebuilt (crown + band + short brim, tilted); walkie x1.75; wrench at the
  belt with the handle down; glasses frames 0.51 u each with thick rims; bean widened to 1.31 u at the eyes (= theirs);
  arms pushed out. Self-grade **B-**: silhouettes/proportions/outfits match at game size; misses: arms slimmer and
  less expressive, cap sits flatter, the glasses worker's clipboard shows the paper side (002 shows the board back).
- v5: the walkie worker rounder (`girth` 1.14: store 7 w/h ~0.8 vs the glasses worker ~0.68), bigger D mouth
  (0.40 x 0.29 u), bigger eyes; his rig frame recentred +0.16 u so the walkie is not clipped. Rigs re-exported: L 7
  layers (proof baked 0.071/255), R 8 layers (0.177/255). Swap groups: body = mouth open / smile, eyes = open / half /
  closed (blink), + glasses (R), arms with their props (walkie / clipboard / pencil) and shoulder pivots.

## Known gaps (v5 list; the v6 status table above supersedes the file names)
- Scientist: coat has no fold lines; the pointing / fist hands are mittens with a stub finger; the open mouth's
  tooth band is two teeth (theirs: one wide band) -- chosen to read at 1/3 size; the loading pose keeps the home
  coat (long sleeves, blue shirt) where theirs rolls the sleeves and shows a white shirt.
- Workers: 002's frame of the walkie worker is a mid-animation pose (eyes closed, kicked foot, leaning back); we
  copied store 7's standing pose (the rest pose) -- the animation lane can reach 002's frame with the rig (eyes_closed
  + a body rotation). No bare-feet toes; hands are 4-finger mittens (theirs are 4-finger too, slightly longer).
- Loading: the background workers / conveyor / logo are not this lane's; the "top hat" and "burger" designs exist as
  avatar models (`char_avatars.py`) if the scene lane wants them rendered in the loading scene.
- `char_wk_colour.png`: the v1 / cyan candidate panels were placed with the blue case's anchors; after the v5
  re-framing of the L worker, the L candidates in those two panels sit ~9 pt off (the decision is unaffected).

### Loading screen (store 8; blue workers, pink scientist)
- v1 carrier at the home scale: half the reference's size (their loading art is a wide-angle close-up); v2 fov 34,
  104 pt/u, taller eyes; v3 box yawed/smaller and moved right of the head (their box sits right of the eyes), arms
  asymmetric; v4 matched on BODY size (84 pt/u) with bigger eyes (their loading workers have larger eyes relative to
  the body than the home ones). Flyer: a fat red arrow (2.75 x 2.15 u) held overhead, blue arrow in the other glove,
  legs dangling, rolled 22 deg; runner: fist up, glasses + green cap, clipboard. Scientist: a new "run" pose (torso
  turned 26 deg, 0.84 torso scale, fist punched forward, two arrows held against the belly, belt + trousers).
  All placed by the eye midpoint (`char_loading_layout.json`). Self-grade **C+**: layout, sizes and poses read like
  theirs at game size; misses: their carrier box shows its side face and sits lower, their scientist's coat has
  rolled short sleeves and a white shirt (ours: long sleeves, the home shirt), the background workers (top hat,
  burger, conveyor) are not rendered here (the avatar models cover the top hat + burger designs if the scene lane
  wants them), the flyer's arrow is a little narrower than theirs.

### Avatars
- 9 portraits (their v552 set, phone 067 / 094 + store 6): scientist, glasses + green cap ("Max"), party hat + pink
  glasses ("James"), detective (deerstalker, moustache, hand on chin, trench collar), burger, box carrier, navy cap +
  walkie, waving, top hat. Plates: their gradient families (pink / purple / green-yellow / orange); the scientist's
  plate turned VIOLET (theirs is pink behind a purple character; ours is pink -> the only deliberate change).
  44 x 44 pt @3x. Self-grade **B-**: same characters and props, read at 30 pt; misses: the hat tops are cropped a
  little more than theirs, the detective's trench collar is simplified.


## Iteration log (2026-09-25, second run: "finish the lane")

### Scientist v6 -- scale / placement against 002 (the ask: "rendered larger than the capture at the same frame")
- Diagnosis on the COMPOSED home (scene layers + our rigs, `art/ui/sheets/char_home_detail.png`): the head was the
  right size, but the coat was 24 % too wide (row y 810 px: 357..858 vs their 425..828) and centred ~20 px left, the
  badge 57 px left, the head silhouette ~13 px left of the eyes, the left cheek tuft 25 px out. `m_scientist.png`'s
  "larger" read also came from its reference: 026 is another animation frame (head 49 px lower) and the sheet pasted
  the frame centre on 026's box centre. The v5 draft sidecar was stale (a first mis-measure; recomputed).
- Fix (home pose only, other poses unchanged): torso x 0.80 + body shifted +0.07 / +0.07 u under the head, torso yaw
  -14 -> -8, head roll -10 -> -8 + yaw -6, arms tucked (elbows 0.85 / 0.84, wrists 0.86 / 0.96), badge + pocket/pen
  moved to 002's spots, shorter higher brows, smile counter-tilted (level like theirs), lower/shorter cheek tufts; the
  placement target carries a measured 10 px eye bias (the eyeMid anchor projects below the visible whites).
- Result (002 px): eye whites L 569..604 x 602..646 / R 627..664 x 609..649 vs theirs 572..607 x 601..644 / 625..664 x
  608..653; coat rows 780 452..784 / 810 417..824 / 840 405..852 vs 443..804 / 425..828 / 409..842; pen 694..705 x
  805..845 vs 694..706 x 812..848. Rig re-exported + baked (proof 0.115/255, 0.003 % px > 40); placement (109.23, 176.52).

### Workers -- placement on the composed home
- Against the phone REST frames (026 / 035 / meta-056): same size (356 px cap-to-sole) but ours sat 21 px low (the feet
  anchor is the sole centre; the toes project below it) and the left worker ~20 px left. Feet targets corrected in
  `char_worker.FEET_FIX_PX`; rigs re-exported with `--skip-render` (layers identical, proofs unchanged 0.071 / 0.177).
- Blue vs the lab: checked on the composed home at game size -- the light azure bodies + warm rim separate from the
  saturated royal-blue wall band by value (lighter) and hue; the navy shorts / caps read as clothing. No change.

### Avatars v2 -- the phone set at the manifest size
- The phone's Edit Profile (meta-003/004) is the v552 set: default + 8 portraits (not v1's 9; no top hat, no plain
  waver; cell 8 = green cap + glasses + fist + notebook). Rebuilt at 64 x 64 pt (v1: 44 pt) as `char_<manifest id>`,
  plates sampled per cell. Framing measured: the frame covers ~4.5 pt per edge, their bean ~70 % of the 55 pt interior
  with the eyes at ~40 % -> 30 pt/u, view 0.19 u below the eyes (v1 read ~25 % too big inside the frame).
- Deliberate plate changes: scientist VIOLET (pink character), notebook SUNNY yellow (a blue worker on their sky blue
  disappeared -- seen on the sheet).
- avatarDefault: SVG, measured silhouette (head d 0.667 of the interior at 0.394, shoulders 0.91 wide).

### Loading v2
- Cases renamed to manifest ids (+ 2 proposed ids); layout JSON rewritten (same placement rule). Flyer frame grown to
  170 x 220 (v1 clipped the feet and the small arrow). New P1 background crowd `workerRunners` (top hat waving, waver,
  burger eater; blurred + hazed toward the room like V1's depth of field).

### Event headers
- workerClawPair: two close-up workers at 86 pt/u (their bean ~110 pt), placed by the eyes on 023; v2 moved the fist to
  mouth level beside the body and the second worker's hands to his head / low right (v1 flung the arms out of frame).
- workerRacers: v1 a physical helix -> the composition could not match (their illustration fakes a strong perspective);
  a camera fit (scipy) did not converge. v2 traces the chute's centreline on meta-045 in screen pt and widens it toward
  the viewer (near-ortho camera, fov 10), riders placed on their screen spots; v3 widened the chute 1.2-1.7x and
  brightened the purple/pink. The room is painted in code (post_fit) and defocused. Shipped at the good bar (C+).


## Round 3 (2026-09-25 afternoon): loading cast B -> A candidates, home idle poses

Brief: take the loading characters from B to A (director sheet `director/p_loading_s8.png` vs store 8), keep PINK and
BLUE, then make sure every home-rig pose used by SPEC-motion-audio §8.2's idle loops exists and recomposes cleanly.
References (store 8, V1 t=0 refcrop) were looked at only; every change is a recipe edit. Not committed.

### Tools (new, lane files)
- `art/pipeline/items/char_proofs.py` (helper, no ASSETS): `loading <name> x0 y0 x1 y1 [k]` = ours (the LIVE layout from
  the render sidecars) | store 8 | V1 at a pt box; `eyes x0 y0 x1 y1` = eye-white blobs in pt (how every placement below was
  matched); `layout` = rewrite `art/out/char_loading_layout.json`; `idle [rig ...]` = the home rigs at the idle-loop
  extremes composed the way `PuppetStage` does (rect_pt, rig.json pivots, head group about `neck`, whole about `feet`,
  torso scaleY about its track pivot) with interior holes painted red. Sheets: `art/ui/sheets/characters/`.
- Proofs to LOOK at: `p_loading_r2_r3_s8_1x.png` (round 2 | round 3 | store 8, game size), `p_loading_r2_r3_s8.png` /
  `p_loading_r2_r3_v1.png` (2x), crops `carrier8.png`, `scihead4.png`, `final_sci.png`, `fist7.png`, `crowd4.png`,
  `crowdL1.png`, idle sheets `idle_sci_home.png`, `idle_wk_homeR_blue.png`, `idle_wk_homeL_blue.png`.

### Status (self-grades at game size; the director re-grades)
| id | r2 | r3 self | what changed | still differs |
|---|---|---|---|---|
| `scientistLoading` | B | **A-** | new `"load"` pose + style (char_scientist `POSES["load"]`, `style="load"`): squat WIDE torso (scale x 1.05 / y 0.90) whose shoulders rise to the cheeks, centred right of the face and turned 14 deg left; the fist a clenched BALL (`fist_ball`) beside the mouth on a fur forearm out of a rolled cuff; the other mitt grips an orange (up-left) + red (left) arrow at the right side; the far leg kicked back (fur); plain shirt front (no badge/pen). Head: turned 16 deg left, taller fuller dome (`_profile("load")`: rows now within ~5 pt of store 8's), wispy flare up-right + wisp low-left, crown tuft leaning left, raised thinner lighter brows, a CRESCENT smile (`mouth="crescent"`) with a two-tooth band (16 x 5 pt vs theirs 19 x 5) + red tongue, fur-free rim at the corners. Fur ladder lifted for the loading light (`FUR_STOPS_LOAD`: median S 0.67 V 0.81 vs theirs 0.67 / 0.82; hue stays PINK 331). Camera pitch -4 -> +5 (store 8 looks from a little above: the belt smiles; from below the mouth roof showed and read as a shout). Placed by the eye whites (target biased 3.5 pt left / 3 pt down). | the mouth still opens a bit rounder/deeper than theirs at 2x; no notched lapel on the coat; our crown tuft is thinner strands |
| `workerCarrier` | B | **A-** | full bean (girth 0.97, `tall` 1.13, belt lowered to 0.48 via the new `belt_y`), turned 16 deg to screen LEFT (face on the left of the capsule, pouch + wrench side showing), arms near-vertical to the box's lower corners with the gloves on its front edge, SHORT CHUNKY legs with big round shoe feet (new `char_worker.leg_chunky`: hip -> knee -> ankle, r 0.21, flattened sole; near foot toe-on under the belly, far foot kicked back-left), tall laughing D with a short tooth band (`face_kw` mouth_h 0.47, teeth_w 0.32), box 1.42 wide seen from a little above (pose pitch +8). Eye whites match store 8 within ~2 pt (L 80..103 x 558..594 vs 80..101 x 558..593). | no box hand-holes (theirs has two small dark slots at the front-bottom); the mouth is a little narrower |
| `workerFist` | B | **B+** | ~20 % bigger (79 pt/u; frame 208 x 212 -> 236 x 236), rounder bean, bigger square glasses (`glasses_kw`), eyes closer (matched on store 8), the fist below-left of the glasses on a thick arm (`arm_r`, `hand_r`), a SPIRAL NOTEBOOK (`"notebook"` prop: brown cover, cream pages, lilac rings), a wide toothless grin, chunky legs + shoe feet | their fist is a bigger flexed bicep pose; the cap's two dark tabs are not modelled |
| `workerRunners` | B | **B+** | the right crowd at store 8's sizes/spots (38 pt/u, frame 156 x 200 at (262, 335)): top-hat worker (fist out + wave) x 0.80 at eyes (333, 388), the waver (arms up) x 0.74 at (369, 401) in front, the burger eater x 1.25 at (357, 438) without the floating brows; chunky running legs; haze 2.2 px / 36 % -> 1.1 px / 12 % (r2 read as pale ghosts) | the burger eater's gaping mouth around the burger |
| `workerCrowdLeft` (NEW, P1) | -- | **B** | the review's missing left group: a navy-cap worker holding a clipboard at the screen edge + two small workers seen from behind (one pointing) where store 8's conveyor is; defocused 1.8 px + 16 %; layout z -2 at (-30, 436) | stands where the (scene lane's, unbuilt) conveyor platform should be |
| `workerWalkie` (rig) | B | B | NEW swap members `eyes_wink` (SPEC-motion-audio §15.4 UI-ART request) and `armL_wave` (group `armL`, default `armL`); every existing layer re-exported PIXEL-IDENTICAL (max abs diff 0; full render identical; proof 0.076/255, 0.001 %) | (arms still thinner than theirs: r2 note) |

Workers stay BLUE (`COLOURWAYS["blue"]`), the scientist PINK. `workerFlyer` untouched (B).

### Home idle poses (SPEC-motion-audio §8.2 / `ui.json puppet`) -- checked, `char_proofs.py idle`
- Every member the loops use exists: scientist `headSmile` (+ `headOpen`), `lidsHalf` / `lidsClosed` overlays, `armL`,
  `armR` (+ `armR_point`), `torso`; right worker `eyes_half|open|closed`, `body_smile|open`, `armL` (clipboard), `armR`
  (pencil), `glasses`; left worker `eyes_open|half|closed` (+ new `wink`), `body_smile|open`, `armL` (+ new `armL_wave`),
  `armR` (walkie). Pivots used by the app come from rig.json (`shoulder`, `neck`, `feet`) and exist on every layer that
  rotates.
- Recomposition at the extremes (torso 1.012 + head -0.8 pt / +1.6 / -0.6 deg + arms +-1.2; worker sway + look-up -4 /
  nod +3; pencil +-6, board -2..+3; walkie -4; think -4; wave): no new holes or seams -- the hole counts stay at the
  rest pose's (the rest "holes" are real background gaps: crown-tuft strands, the glasses' left lens overhanging the
  head, the gap between a raised arm and the head). Sheets `idle_*.png`.
- FINDING (for the spec / shell owner, not changed here): §8.2's left-worker wave rotates the hip-fist `armL` by -25 deg;
  with "positive = clockwise" that swings the fist INWARD onto the belt (see `idle_wk_homeL_blue.png`, "wave armL -25").
  Suggested `ui.json puppet.char_wk_homeL_blue_rig` tracks instead: `{"layer": "armL", "prop": "member", "t": [0, 6.0,
  7.2, 12.5, 13.7], "v": ["armL", "armL_wave", "armL", "armL_wave", "armL"], "curve": "discrete"}` + `{"layer":
  "armL_wave", "prop": "rotation", "t": [0, 6.0, 6.3, 6.6, 6.9, 7.2, 12.5, 12.8, 13.1, 13.4, 13.7, 17.3], "v": [0, 0, 10,
  -8, 10, 0, 0, 10, -8, 10, 0, 0], "curve": "easeInOut"}` (the wave member swings cleanly +-10 deg about its shoulder) and
  drop the -25 rotation; the 3.70 s "wink" beat can use `eyes_wink` instead of `eyes_closed`. PuppetStage already handles
  a new group generically (member track -> opacity swap; the `armL` rotation track still targets the `armL` layer).
- The §8.2 table's scientist arm pivots (49.22, 86.31) / (141.42, 92.97) are stale; the app reads rig.json (61.23, 83.63) /
  (136.65, 86.61), which is correct.

### For other lanes
- **scene (loadingBackdrop):** the baked contact shadows were placed from the OLD layout + alphas; the cast moved (carrier
  frame (21.12, 363.5), feet now ~y 745 pt under x ~60..150; runner (161.14, 423.94) 236 x 236; crowd (262, 335) 156 x 200;
  new left crowd (-30, 436) 124 x 106 whose two back-view workers stand where store 8's conveyor top is, y ~495) -- re-run
  the backdrop's shadow bake from `art/out/char_loading_layout.json`; the conveyor + press (review round-3 list) would
  give the left pair their platform.
- **shell:** `char_loading_layout.json` has a new entry `char_workerCrowdLeft` (file `char_workerCrowdLeft@3x.png`, z -2)
  and new frames for `char_workerFist` (236 x 236) and `char_workerRunners` (156 x 200); `LoadingScreen` reads the JSON
  generically, the new PNG must be in the bundle's Art/. The left-worker rig gained 2 layers (bundle them with the rig).
- **director:** `characters.entries.json` carries the new sizes / notes (6 entries changed, 1 new: `workerCrowdLeft`);
  `manifest_check.py --quiet --lanes art/lanes/characters.entries.json` -> 209 entries, 0 failing.

### Recipe notes (r3)
- `char_worker.worker()` never passed a spec's top-level `eye_c` / `eye_r` / `mouth_h` / `brows` to `face_parts`
  (r1/r2 values there were silently ignored). They stay unpassed so every shipped render is unchanged; new specs opt in
  with `face_kw` (+ `teeth_w`, `mouth_z`, `lid_w`). Also new, all opt-in: `legs` / `leg_r` / `shoe` (chunky legs), `belt_y`,
  `arm_r`, `hand_r`, `glasses_kw`, `eyes="wink"`, prop `"notebook"`, `rig_for(eye_members=, arm_l_alts=)`.
- `char_scientist`: everything new is behind `POSES["load"]` / `style="load"` / `mouth="crescent"` / `arm_pts` / `leg`;
  the home rig and the avatar portrait paths are code-identical (not re-rendered).
- A worker brow capsule placed above the dome (eye_c raised) missed the surface and got a z bound of -321, which made
  the obscurance field 24 818 voxels deep (3-minute renders): the runner spec now has `no_brows` (they sit under the cap).
- Render times on this Mac: carrier / runner 25 s, crowd 75 s, crowd-left 60-110 s, scientist (fur) 65-125 s.
