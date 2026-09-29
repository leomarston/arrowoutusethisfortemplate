# pipeline lane (pipeline keeper) -- log

Sole editor of the shared pipeline files (art/pipeline/*.py, art/pipeline/render/**, art/ui/tools/**, art/tools/**,
art/PIPELINE.md). Requests and answers: `art/lanes/requests.md`.

## Entries (pipeline-owned, still todo)

| id | status | output path | reference used | self-grade | remaining differences |
|---|---|---|---|---|---|
| curtainCyan | todo (not built, by decision) | art/ui/out/curtainCyan@3x.png (none) | V2-levels-11-38.mp4 t=96 (not grabbed) | - | SPEC reconciliation 11: the videos' Curtain/Box levels use the phone's BOX skin (curtainCrate family, `curtainW<w>H<h>`), so the V2 cyan ice/bomb skin is not shipped. Build only if the SPEC changes. |
| cornerWedge | todo (not built, by decision) | art/ui/out/cornerWedge@3x.png (none) | yt_frames primegaming_L10_corners.jpg (not used) | - | No level 32-61 (research/levels) and none of the owner's L1-38 videos has a corner obstacle; levels beyond 61 follow the recorded curve. Build (phone-palette skin, SPEC 11) only when a level needs it. |

## Pipeline changes (2026-09-25)

| time | change | files | verification |
|---|---|---|---|
| 05:35 | request 4: premeshed parts natively in `ui3d.mesh_parts` (`ui3d.premeshed(p)`; recipe order kept; SDF-less part without premesh -> ValueError) | art/ui/tools/ui3d.py | premesh_example draft + rig; workerExample rig proof unchanged (0.249/255, 0.177 %) |
| 05:36 | request 5: rig colour bake (`bake=True` in RIGS spec, `rig.py --bake/--no-bake`, `rig.bake`), proof on the baked composite, `baked` note in rig.json; draft supported | art/ui/tools/rig.py | reproduces the lane's shipped sci_home / wk_homeL_blue / wk_homeR_blue rigs pixel for pixel (max |d| 0 on every layer) |
| 05:38 | self-tests: `premesh_example.py` (premeshed strand tuft + bake), `selftest_manifest.json` (art_batch --rigs over both example rigs) | art/pipeline/examples/ | `art_batch.py --manifest art/pipeline/examples/selftest_manifest.json --rigs`: both OK; `manifest_check.py --quiet`: 199 entries, 0 failing |
| 05:40 | PIPELINE.md §3.1 (bake, premeshed parts, self-tests) + Reuse row | art/PIPELINE.md | - |
| 06:17 | `manifest.py merge <lane>.entries.json [--out copy] or [--apply] [--ids ...]` (dry-run diffs by default) for the art director; PIPELINE.md §0 documents lane scratch manifests | art/tools/manifest.py, art/PIPELINE.md | 3d-events file: 16 diffs; applied to a copy -> re-diff 0; checker on the copy works; MANIFEST.json md5 unchanged |
| 07:09 | `manifest_check.py --lanes [files]`: lane scratch manifests merged in memory before the check; `merge_apply(validate=False)` | art/tools/manifest_check.py, art/tools/manifest.py, art/PIPELINE.md | plain check 6+ failing (lane outputs vs unmerged sizes) -> `--lanes` 5 failing (scene lane has no entries file yet); MANIFEST.json md5 unchanged |
| 07:31 | `art_batch.py --3d` builds `exact_px` entries (app icon): resize to exact_px, opaque full_bleed -> RGB; `verify` + `manifest_check` check exact size + RGB for full_bleed exact_px | art/tools/art_batch.py, art/tools/manifest_check.py, art/PIPELINE.md, examples `iconExample` + 2 selftest entries | self-test `--3d --rigs`: 4/4 OK (icons RGB 100 + 120 px); shipped appIcon1024.png passes; main check `--lanes`: 5 failing, all lane-side (scene sizes, trophyCup source) |
| 08:00 | close-out: requests 1-5 answered, none open; polled art/lanes every ~4 min 05:40-08:00 | - | self-tests `--3d --rigs` 4/4 OK; `manifest_check --quiet --lanes`: 9 failing, all scene-lane renders without a scene entries file; MANIFEST.json untouched (md5 5f3d895d...) |

## Known limitations (not changed)
- ui3d's USDZ cache key is the recipe's source hash (+ local imports, uikit.py, `_*.py` in the recipe dir): any edit to
  a recipe re-meshes each of its models on its next render (3d-hud, scene lanes noted it; the scene lane's kit caches per
  model). A per-model key would re-mesh every cached model once and risks stale meshes on a missed dependency.
- Rig bake: overlays and non-default swap-group members are never baked (they are only seen when the puppet moves).
