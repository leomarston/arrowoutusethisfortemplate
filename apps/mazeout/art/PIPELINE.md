# Arrow Out — art pipeline (how to add a UI piece, a 3D prop, a character part)

Art spike 2026-09-25; production pipeline + manifest added the same night (pipeline agent). The game's name is
**Arrow Out** (owner 02:33; the folder stays `apps/mazeout`). Which ROUTE a graphic takes is decided in `art/STYLE.md`
(decision table); WHICH graphics exist, their ids, sizes, references, owners and status are in `art/MANIFEST.json`
(human view: `art/ID-MAP.md`); this file is the how-to. Every asset is ours: code, our SVG, our SDF models rendered by our renderer. Captures are references to LOOK at
(side-by-side sheets, in-place A/B); never trace, sample into an asset or reuse them. Never bake translatable text into
a bitmap: labels are live text (EN + TR). Asset and font file names stay neutral (never "maze", "MO", "grand").

```
art/
  STYLE.md            measured look + route per family + palette + art list (§A.2: board obstacles measured)
  PIPELINE.md         this file
  MANIFEST.json       EVERY graphic the game needs (197 entries): id, family, route, size, source, file, ref, status, owner
  ID-MAP.md           generated from the manifest: id -> file / symbol -> where used (never edit by hand)
  lanes/requests.md   lanes file pipeline requests here; the pipeline agent answers in the same file
  tools/              manifest.py (load/edit/add/idmap/ref), manifest_check.py, art_batch.py, manifest_sheets.py,
                      vgrab.swift (video frame refs), measure_board.py, measure_obstacles.py (+ obstacles_measured.json),
                      sample_palette.py
  ref/                reference crops cut from the shots (looked at only; for sheets)
  out/                3D-route renders that ship: <case>@3x.png (transparent, exact frame x 3)
  pipeline/           the SDF -> mesh -> USDZ toolbox, copied VERBATIM from Match Factory (see "Reuse")
    render/           mfrender (offscreen RealityKit renderer) source + build.sh
    items/            board-ITEM recipes only (this game has none: its board is vector); _calib/_materials tools
    examples/         toy_hammer.py, rubber_duck.py: MF recipes kept as format examples (not built)
  ui/
    CASES.txt         the UI raster case list check.py enforces (GENERATED from the manifest: manifest_check --write-cases)
    code/             GlossyChrome.swift: the SwiftUI chrome components (route B1), rendered by tools/swiftui_render
    src/              SVG generators: shapes.py (superellipse, heart, contours), gen_chrome.py, gen_props.py (spike),
                      gen_board.py (board sprites: tape, door, lock, key, pipe mouth/counter) -> <case>.svg
    recipes/          3D UI props + characters: obstacles.py (tape, rejected route), arrows3d.py, worker.py;
                      _example_*_mf.py = MF recipes as format examples (underscore = never indexed)
    tools/            svgr.swift + svg.py, ui3d.py + uikit.py, sheets.py, check.py, compare_swap.py, compare_c.py,
                      swiftui_render.swift
    out/              UI rasters that ship: <case>@3x.png
    sheets/           comparison sheets (gitignored; regenerate)
build/                (gitignored) build/art/mfrender, build/ui-art/{svgr, swiftuirender, usdz/, raw/, route3d/,
                      svgroute/, swiftui/, draft/}
```

Python: `PY=~/.venvs/mf3d/bin/python` (numpy, scipy, scikit-image, trimesh, fast-simplification, usd-core, PIL).
Run everything from `apps/mazeout`. Keep each command under ~4 min; multiprocessing only with spawn, <= 2 workers.

## One-time setup

```sh
sh art/pipeline/render/build.sh                  # -> build/art/mfrender (swiftc, ~1 min; not xcodebuild)
# svg.py compiles build/ui-art/svgr itself on first use
xcrun swiftc -O -parse-as-library -target arm64-apple-macos15.0 -o build/ui-art/swiftuirender \
    art/ui/code/GlossyChrome.swift art/ui/tools/swiftui_render.swift     # ~40 s
```

## Naming and sizes

- A raster case is `<case>@3x.png`, exactly **frame_pt x 3** px, RGBA, whole-pt frame (`check.py` enforces it).
  `<case>` is lowerCamelCase and names the thing, not the brand: `heartHUD`, `tapeV4`, `boosterFreeze`, `workerWave`.
- Frames come from the capture: measure the element's bbox in px, divide by 3 (pt = px x 393 / 1178 = px / 2.997),
  add the shadow margin. Write the measured size into the generator's comment and into STYLE.md.
- UI rasters -> `art/ui/out/`; 3D-route renders (characters, scenes, 3D arrows) -> `art/out/`; losing-route
  candidates stay in `build/ui-art/{svgroute,route3d}/` (compare only).

## 0. The manifest (start here)

`art/MANIFEST.json` is the one list of graphics. Each entry: `id` (neutral lowerCamelCase; never maze/mo/grand/arrowjam),
`family` (swiftui | svg | 3d | code), `route` (STYLE.md A, B1, B2, B3, C1, C2, C3), `group`, `purpose`, `screen`, `size_pt`
(+ `size_px` = x3), `source` (`<generator.py>:<case>`, `<recipe.py>:<case>`, `<File.swift>:<Symbol>`, or `engine`), `file`
(the shipped raster), `ref` (what to LOOK at), `status` (todo -> wip -> done -> graded), `owner` (lane), `notes`.
Optional: `pitch_pt` + `anchor_pt` (board sprites), `rig` (a cut-out rig directory), `text_live`, `full_bleed`, `confirmed:
false` (seen only in older builds / the owner's videos), `exact_px` (the 1024 px icon), `preview` (a PNG of a swiftui/code
entry for its sheet). `superseded` (top level) lists old files a lane still has to delete (the axolotl "Doc", the spike worker).

```sh
PY=~/.venvs/mf3d/bin/python
python3 art/tools/manifest.py list --owner ui-art --status todo       # what a lane has left
python3 art/tools/manifest.py show heartHUD
python3 art/tools/manifest.py set boosterHint status=wip               # lanes update their own entries
python3 art/tools/manifest.py add '{"id": "...", "family": "svg", ...}'  # a new graphic (schema-checked)
python3 art/tools/manifest.py add-door 24 7 46 0 3                     # a door size for level 46 at cells (0, 3)
python3 art/tools/manifest.py ref keyOnArrow                           # the reference crop -> build/ui-art/refcrops/
python3 art/tools/manifest.py idmap                                    # regenerate art/ID-MAP.md
$PY art/tools/manifest_check.py [--quiet] [--strict] [--write-cases]    # exit 1 on any failure
```

**While several lanes run at once, lanes never edit `MANIFEST.json`.** A lane keeps its entries (same schema, full entry
objects with its `source` / `file` / `size_pt` / `status`) in a scratch manifest `art/lanes/<lane>.entries.json` and points
every tool at it: `art_batch.py --manifest ...`, `manifest_sheets.py --manifest ...`, `manifest_check.py --manifest ...`.
The art director merges it:
```sh
python3 art/tools/manifest.py merge art/lanes/<lane>.entries.json                   # field diffs vs MANIFEST.json (dry run)
python3 art/tools/manifest.py merge art/lanes/<lane>.entries.json --out /tmp/m.json # merged copy -> check it:
$PY art/tools/manifest_check.py --manifest /tmp/m.json --quiet
python3 art/tools/manifest.py merge art/lanes/<lane>.entries.json --apply [--ids a b]   # write MANIFEST.json, then idmap
```
Only the fields the lane entry carries are compared/written (a lane file never deletes a field); new ids are added with
the `add` schema check. `manifest_check.py --lanes` checks the manifest with EVERY `art/lanes/*.entries.json` merged in memory
(nothing written; `--lanes a.json b.json` for specific files): while lanes run, the plain check fails wherever a lane has
already shipped an output whose size/status only its scratch manifest knows -- judge a lane's work with `--lanes`.

**References.** `ref.box_pt` is in the shot's own pt (phone shots 393 pt wide = 1178 px; store shots 440 pt = 1320 px, @3x);
annotated web frames (`research/web/yt_frames`, 600 x 760 composites) use `box_px` + `px_per_pt`; the owner's videos use
`{video, t, box_pt}` and the frame is grabbed on demand by `art/tools/vgrab.swift` (AVAssetImageGenerator, seek-based, compiled
once to `build/ui-art/vgrab`; 592 px = 393 pt assumed) into `build/ui-art/refframes/`. Board refs also carry `pitch_pt` (the
level's fit pitch) and `anchor_pt` (the lattice point the sprite registers to), computed from `research/levels/L0NN.json`.

**The checker** (`manifest_check.py`): schema (ids unique/neutral, families, routes, statuses, owner), whole-pt raster sizes,
`file` = `<dir>/<id>@3x.png` (characters lane: `<dir>/char_<id>@3x.png`, rigs `art/out/char_<id>_rig/`), refs inside their
images, sources resolve (a `todo` entry may name a PLANNED generator/symbol: reported as a note), outputs of done/graded
entries present, RGBA, exact size x3, not empty, some transparency, nothing touching the frame edge (unless `full_bleed`),
rig dirs have rig.json; stray files in art/ui/out + art/out; superseded files still on disk.

## 0.1 Batch builds

```sh
$PY art/tools/art_batch.py --svg                      # every svg entry -> its file at exactly frame x 3 (one WebKit run)
$PY art/tools/art_batch.py --svg --ids tapeV4 --sync  # + write the generator's frame size / anchor back to the manifest
$PY art/tools/art_batch.py --3d                       # every 3d entry via ui3d.render_case (calibrated rig) -> its file
$PY art/tools/art_batch.py --rigs                     # every rig entry -> art/ui/tools/rig.py export (layers + rig.json)
$PY art/tools/art_batch.py --3d --draft               # low-res drafts to build/ui-art/draft/ (nothing ships)
$PY art/tools/art_batch.py --status todo,wip --svg --dry
$PY art/tools/art_batch.py --manifest scratch.json --3d   # another manifest (self-tests, scratch batches)
$PY art/tools/art_batch.py --3d --ids appIcon          # exact_px entry: exact size, RGB (no alpha) when full_bleed + opaque
```
`exact_px` entries (only the 1024 px app icon): the recipe case's frame is `exact_px / 3` pt (e.g. `frame=(1024 / 3, 1024 /
3)`, `no_fit`, an opaque `background` or a full-bleed `post_fit`); `art_batch --3d` resizes to exactly `exact_px` if needed,
saves a fully opaque full-bleed render as RGB and verifies size + RGB (the checker applies the same rule).
SVG sources are `art/ui/src/<gen>.py:<case>`: the module's `CASES[case]()` returns the SVG text or `(svg, {"anchor": (x, y)
pt})`; `gen_board.door_case(w, h)` registers any door size on demand. 3D sources are `<recipe dir>/<recipe>.py:<ASSETS case>`
(art/ui/recipes or art/pipeline/items); rig sources name a `RIGS` entry. Every output is verified (the checker's rules);
3D and rig batches check `sysctl vm.swapusage` first and wait in 2-minute steps while < 400 MB is free. Self-test (both
paths, 2026-09-25): arrows3d `arrowIconBlue_3d` through `--3d`, `rig_worker_example` through `--rigs` (proof 0.25/255,
0.18 % px > 40).

## 0.2 Side-by-side sheets (per entry, at GAME size)

```sh
$PY art/tools/manifest_sheets.py tapeV4 doorW4H8 lockHex     # -> art/ui/sheets/m_<id>.png
$PY art/tools/manifest_sheets.py --group board               # + a contact sheet art/ui/sheets/m_board.jpg
$PY art/tools/manifest_sheets.py --all
$PY art/tools/manifest_sheets.py --draft tapeV4              # the draft render instead of the shipped file
```
Row 1 at the capture's scale (3 px per pt): the reference crop | ours on the reference's backdrop colour | ours IN PLACE over
the capture at `ref.anchor_pt` (any size or registration error shows as the original peeking out) | alpha. Row 2 = the
first three at 2x. Board sprites are scaled by `ref.pitch_pt / pitch_pt` (fit pitch / design pitch 32). Rig entries show the
rig's full render (rig.json `full`); swiftui/code entries use `preview`. LOOK at every sheet before marking an entry done.

## 0.3 Board sprites (route C3) — design pitch

Board obstacle sprites are drawn at the **design pitch 32 pt per cell** (`MANIFEST.board_design_pitch_pt`), crisp up to 32
pt/cell on screen (fit pitch 14-28 pt); the engine scales each by `pitch_on_screen / 32` and places the sprite's `anchor_pt` on
the lattice point named in the entry's notes (tape: the bundle's block centre; door: the block's top-left corner; lock: door
bbox centre + (0, 0.18 pitch); key: the arrow line x first key cell centre; pipe mouth: the end cell centre; counter: its
centre; curtain block: the block's top-left corner). Numbers in pitch units: STYLE §A.2. Generator:
`art/ui/src/gen_board.py`; sizes on demand: `doorW<w>H<h>` (`manifest.py add-door`) and `curtainW<w>H<h>` (add an entry
with `source` `art/ui/src/gen_board.py:curtainW2H2`; `curtainCrate` is the 3 x 3 case).

## 1. A UI piece

First decide the class (STYLE.md B1/B2/B3). Then:

### B1 — stretchable chrome = SwiftUI code
1. Profile the element on an untinted shot along its CENTRE column and row (not near a corner: the pause button's
   first profile at a corner column put the face inset 2x too deep). Note each layer: outline, rim/lip gradient stops,
   face inset (l, t, r, b), light edges, glare, shadow. Fit the superellipse exponent from row extents near the top.
2. Add the component to `art/ui/code/GlossyChrome.swift` (shapes `Superellipse`, `GlossyHeartShape`; colours as
   `Color(hex:)`; all numbers in pt = the SVG px / 3). Label = live `Text`, placeholder font until the fonts lane lands.
3. Add a case to `art/ui/tools/swiftui_render.swift`, rebuild the renderer, render:
   `build/ui-art/swiftuirender build/ui-art/swiftui`
4. A/B in place: add the case to `CASES` in `art/ui/tools/compare_swap.py` (shot, element bbox, mask fn, where the
   frame's origin goes, how to erase the original), then
   `$PY art/ui/tools/compare_swap.py <case>` -> `art/ui/sheets/ab_<case>.png` + `ab_context_<shot>.png`, with silhouette
   IoU and mean/p90 CIEDE2000 inside the element. READ the sheet. Iterate until the context sheet reads the same at game
   size (spike results: ΔE00 3.9-5.2, IoU 0.92-0.97).
   Optional: write the same recipe as SVG (`gen_chrome.py`, `svg.py --route <case>`) to cross-check the SwiftUI
   semantics (blur radius, gradient radii) — the two routes agreed within 0.05 ΔE00 on every spike element.

### B2 — fixed icon = SVG -> @3x PNG
1. Write the generator function in `art/ui/src/gen_chrome.py` (chrome icons) or `gen_props.py` (board sprites):
   units = @3x px (1 = 1/3 pt), y down, `svg_doc(W_pt, H_pt, body, defs)`. Shapes from `shapes.py` primitives
   (superellipse, `heart2_path`, contours of a small SDF) — parameters measured, never a traced outline.
2. `$PY art/ui/src/gen_chrome.py <case>` (writes `art/ui/src/<case>.svg`), then `$PY art/ui/tools/svg.py <case>`
   (WebKit, 2x supersampled, resized to exactly frame x 3 -> `art/ui/out/<case>@3x.png`).
3. Add (or update) the manifest entry (`manifest.py add` / `set`), then `art_batch.py --ids <id>` and
   `manifest_check.py --write-cases` (regenerates `art/ui/CASES.txt`); `python3 art/ui/tools/check.py` still works on it.
4. Sheets: `$PY art/ui/tools/compare_swap.py <case>` (in place) and/or `$PY art/ui/tools/sheets.py <case>` (reference
   crop | ours on the backdrop colour at display size | alpha), after adding the case to `sheets.REFS`.

### B3 — rendered-looking UI prop = 3D (same as §2)

## 2. A 3D prop (UI prop, board-scene prop, glossy arrow)

UI/scene props live in `art/ui/recipes/<name>.py`, never in `art/pipeline/items/` (`build.py --all` would turn them
into board items). A recipe module defines:

```python
from uikit import Part, gloss, satin, metal, extrude, rect2, box, capsule, ellipsoid, union, ...   # read-only toolbox
VOXEL = 0.006                                  # marching-cubes cell (authoring units)
def model():                                   # -> (list[Part], voxel); +Y up, +Z toward the viewer
    return [Part("body", sdf, gloss("x_body", "#FEBF0E", rough=0.30, ior=1.40), voxel=0.004)], VOXEL
MODELS = {"model_name": model}
ASSETS = {"caseName": dict(model="model_name", yaw=0, pitch=0, roll=0, frame=(W_pt, H_pt), fill=0.96,
                           align=(0.5, 0.5), fov=18, light=dict(key_lux=...), post_fit=fn, dest=None)}
```

`dest="route3d"` sends a candidate to `build/ui-art/route3d/<case minus _3d>.png` (compare only); no `dest` writes
`art/ui/out/<case>@3x.png`. Other spec keys: `scene=[(model, pose), ...]`, `bounds`, `no_fit`, `anchors` (3D points ->
pt in a sidecar JSON), `margin`, `post`/`post_fit` (PIL fns, e.g. the tape's drop shadow).

```sh
$PY art/ui/tools/ui3d.py --list
$PY art/ui/tools/ui3d.py caseName --draft          # quick low-res -> build/ui-art/draft/
$PY art/ui/tools/ui3d.py caseName                  # mesh (cached by recipe hash) + render
```

Timings on this Mac: tape 3 s, one arrow 17 s (1024 px painted texture), the worker 8-10 s.

Recipe patterns that worked:
- **Painted bevels** (`arrows3d.bevel_texture`): when the reference's shading shifts hue (yellow -> orange), paint it:
  planar UV over the 2D outline, colour by distance-to-outline and outline facing; let the rig only add form.
- **Arching a flat strap** (`obstacles.tape.arch`): wrap an SDF with `z += k y^2` (Lipschitz x 0.9).
- **Open mouths**: subtract a flat-topped half ellipsoid from the body, put a slightly smaller dark-red one inside,
  tongue on its floor, teeth under the lip (a surface patch reads as a sticker, not a mouth).
- Lighting overrides per family (`ARROW_LIGHT`, `WORKER_LIGHT`) — see STYLE.md §C.1.

Budgets: UI/scene renders are offline, so triangles only cost render time (the worker is 319k tris); keep any single
render < 60 s and the USDZ in `build/` (not committed: 1-5 MB each). The shipped artifact is the PNG. If a prop ever
has to be LIVE 3D in the app, build it through `art/pipeline/build.py` instead (1.5-4k tris, outline shells, JSON
sidecar; see `pipeline/examples/`).

## 3. A character part (cut-out puppet)

Characters are one recipe with a pose table (`worker.py` `POSES`) and are split into LAYERS rendered with ONE shared
camera, then animated in-app as a cut-out puppet (CALayers / SpriteKit nodes) with keyframes from the motion analyst.

1. Make the part separable in the recipe (`worker(split_arm="R")` makes the arm + mitten its own Part) and add one
   model per layer that filters parts (`_only({"armR"}, keep=True/False)`).
2. Give every layer the same view: `scene=[(model, dict(yaw, pitch, center=False))]` (no per-part recentring),
   explicit `bounds` (framing), `no_fit=True` (registration kept; frame aspect = bounds aspect), same `light`.
3. Export pivots with `anchors={"shoulderR": [[x, y, z]]}` -> `<sidecar>.json` points in pt (origin top-left).
4. Prove the split: composite the layers and diff against the full render (spike: mean |Δ| 0.2/255, 0.4 % of pixels
   > 40, all at the shoulder seam) — `art/ui/sheets/c_worker_puppet.png`.
5. Eyes (blink), mouth shapes, brows: separate thin layers the same way; a pose change of the whole body = a new
   POSES entry rendered as a new layer set.

Side-by-side for characters: `$PY art/ui/tools/compare_c.py worker` (reference workers | ours at the same on-screen
height | 1/3-size silhouettes).

### 3.1 The rig export (pipeline feature, `art/ui/tools/rig.py`)

A recipe declares `RIGS = {name: spec}` (explicit layer cases, or `auto=dict(factory, pose, frame, layers=[...])`); `rig.py`
(or `ui3d.py --rig`, or `art_batch.py --rigs` from the manifest) renders every layer with ONE shared camera, trims each to
its alpha bbox and writes `art/out/char_<name>_rig/<layer>@3x.png` + `rig.json` {character, frame_pt, full, placement_pt,
layers: [{name, file, z, rect_pt, pivots_pt, group?, default?, overlay?, parent?}], groups {eyes: open/half/closed, mouth:
shapes}, proof {mean_abs, pct_gt40}}, plus `art/ui/sheets/char_<name>_puppet.png` (full | painter's composite | diff x4)
and `rig_<name>_layers.png`. HOLDOUT mattes keep buried parts (eyes, mouths) to their visible pixels. The batch fails a rig
whose proof exceeds mean 2/255 or 1 % of pixels > 40. Format + self-test: `art/pipeline/examples/rig_worker_example.py`.
Characters live in `art/pipeline/items/char_*.py` (the characters lane's files; `build.py --all` skips `char_*`).

- **Colour bake** (`bake=True` in the RIGS spec, or `rig.py --bake` / `--no-bake` to override): each layer renders alone and
  misses its neighbours' cast shadows; the bake copies the full render's colour into every DEFAULT layer where it is the
  top-most, (nearly) opaque layer (alpha untouched; overlays and non-default group members untouched), then the proof is
  taken on the baked composite and rig.json gains `baked`. sci_home: 1.39/255, 1.6 % px > 40 -> 0.12/255, 0.004 %. Same
  maths as the lane's `char_make.bake` (rig.py reproduces the shipped sci_home / wk_homeL_blue / wk_homeR_blue rigs pixel
  for pixel from the same part renders); never bake twice.
- **Premeshed parts**: a Part with `sdf=None` and a `premesh` instance attribute (callable -> `(v, f, n, uv)`, uv may be
  None) is meshed natively by `ui3d.mesh_parts` (taken as-is: no marching cubes, decimation or reprojection), so fur
  (`char_fur.fur_part`) renders through ui3d.py / rig.py / art_batch.py without a driver patch.
- **Self-tests** (scratch outputs under build/ui-art/rigs, never art/out):
  `$PY art/tools/art_batch.py --manifest art/pipeline/examples/selftest_manifest.json --rigs` -> `workerExample` (auto mode +
  holdout, unbaked 0.25/255, 0.18 %) and `premeshExample` (`premesh_example.py`: premeshed strand tuft + bake, 0.10/255,
  0.0 %; 0.25/255, 0.12 % unbaked); with `--3d` also two exact_px icon entries (100 px as rendered, 120 px resized; both
  RGB). Run it, plus `manifest_check.py --quiet --lanes`, after any change to ui3d.py / rig.py / art_batch.py.

## 4. The board (route A, code)

No bitmaps. `python3 art/tools/measure_board.py` prints the stroke, lattice, heads, caps and dots on shots 003/004;
STYLE.md §A turns them into the engine recipe (fractions of the pitch). Re-run on new levels (zoom, silhouettes).
Board obstacle sprites are SVG generators in `gen_board.py` (tape 2/3/4 lanes x H/V, doors of any w x h, hex lock, key,
pipe mouth + counter), parametric in size, at the design pitch (§0.3); `measure_obstacles.py` re-measures them on new shots.
The art-spike `gen_props.tape` (fit-pitch 20 x 65 pt) is superseded by `gen_board.tape`.

## Reuse (what was copied, from where)

| copied | from | source commit | changed here |
|---|---|---|---|
| `art/pipeline/{sdf,mesher,usdwriter,palette,build,preview,closeup,review,calib}.py`, `render/{main.swift,build.sh}`, `items/{__init__,_calib,_materials}.py` | `apps/matchfactory/art/pipeline/` | sdf/main.swift 319a63e, mesher 2505087 (all byte-identical to HEAD) | nothing (verbatim). `preview.py RIG_CFG`, `review.py` level->shot maps and `palette.py` MF materials are still Match Factory's: they only serve board-ITEM piles, which this game does not have |
| `art/pipeline/examples/{toy_hammer,rubber_duck}.py` | MF `art/pipeline/items/` | 2505087 | format examples only |
| `art/ui/tools/{svgr.swift,svg.py,sheets.py,check.py,ui3d.py,uikit.py}` | `apps/matchfactory/art/ui/tools/` | 05424db | svg.py `--route`; sheets.py REFS/GROUPS + ref dirs (art/ref, research/store); check.py reads `art/ui/CASES.txt` (no SPEC-ui yet); ui3d.py `dest="route3d"` + sidecars next to it; uikit.py neutral font paths + a placeholder |
| `art/ui/recipes/_example_{characters,economy}_mf.py` | MF `art/ui/recipes/` | 05424db | format examples (underscore: never indexed) |
| new | — | — | `art/tools/*`, `art/ui/src/*`, `art/ui/code/GlossyChrome.swift`, `art/ui/tools/{compare_swap,compare_c}.py`, `swiftui_render.swift`, recipes `obstacles.py`, `arrows3d.py`, `worker.py` |
| new (production, pipeline agent) | — | — | `art/MANIFEST.json`, `art/ID-MAP.md`, `art/tools/{manifest,manifest_check,art_batch,manifest_sheets,measure_obstacles}.py`, `art/tools/vgrab.swift`, `art/ui/src/gen_board.py`, `art/ui/tools/rig.py`; `build.py recipes()` skips `char_*`; `ui3d.py --recipes/--out/--rig`, holdout mattes; `mesher.compute_uv` "fn" kind; premeshed parts in `ui3d.mesh_parts` + rig colour bake (`rig.py` `bake`), examples `premesh_example.py` + `selftest_manifest.json` |

## Gotchas found in the spike (and in production)

- **The tape covers its arrows.** The shafts stop at the band's edges; a sprite with lane gaps showed black stripes the
  capture does not have (m_tapeV4 round 1).
- **Store shots are 440 pt wide** (1320 px, @3x), not 393: the manifest's `shot_scale` knows; a hand-made crop must too.
- **Sheet backdrop = the median of the crop's border**: a crop that is all door shows ours on lilac; that is cosmetic.
- **Spike A/B tools predate the design pitch**: `compare_swap.py tapeV4` / `sheets.py tapeV4` expect the spike's 20 x 65 pt
  tape; the shipped `tapeV4` (gen_board, 39 x 118 pt at 32 pt/cell) is judged with `manifest_sheets.py` (it scales by pitch).
  The spike tape and SVG worker are compare-only now (`gen_props` `tapeV4Spike`, `workerHome` -> build/ui-art/svgsrc).
- **Web frames (`yt_frames`) are annotated composites**: the screen sits at the left of a 600 x 760 canvas; refs use
  `box_px` + `px_per_pt`, never `box_pt`.

- **Profile on centre lines.** Squircle edges curve, so a profile 13 px from the side reads a much thicker rim.
- **SwiftUI `EllipticalGradient` fractions**: 0.5 = the frame edge (SVG `r` in bbox units maps 1:1 to the fraction).
  A 2x error made the SwiftUI heart orange (ΔE00 7.6 -> 4.5 after the fix).
- **`CGPath.union`** (iOS 16 / macOS 13) builds the heart; the wedge join leaves a small kink — smooth it if it shows.
- **IoU fits of a primitive family** pick blunt shapes when the model cannot express the feature (the round-cone heart
  bought IoU with a blunt tip); add the missing feature (a tip wedge) and check the row widths near the tip.
- **mfrender outputs Display P3 converted to sRGB** (see MF PIPELINE); tone mapping stays off.
- **PBR darkens toward olive/brown**; toy art darkens toward a deeper SATURATED hue -> paint it (painted bevel).
- **`ui3d` fit crops to the alpha bbox**: use `margin` to keep feet/hands off the frame edge, or `bounds` + `no_fit`
  when layers must register.
- **svg.py writes art/ui/out by default**; SVG candidates of classes that ship another route go through `--route`.
- **Never bake text**: the button PNG/SwiftUI bodies are blank; the comparison tools draw a stand-in label for context.
