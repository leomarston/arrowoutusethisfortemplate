# video-tools — the owner's gameplay videos → index + level JSON

V1 = `research/video/owner/V1-levels-01-20.mp4` (25 fps, 505 s), V2 = `research/video/owner/V2-levels-11-38.mp4` (59.64 fps, 1684 s),
both 592x1280 px = a 393x852-pt phone (pt = px × 393/592; verified: V2 L21 reads pitch 28.03 pt, the phone's identical L35 28.09 pt).
Python = `~/.venvs/mf3d/bin/python`. Binaries are gitignored: `swiftc -O -o vgrab vgrab.swift` (same for vocr, vscan).
Frames and caches live in `research/video-frames/` (gitignored). The videos are a DIFFERENT SKIN than v552 (blue arrows on light blue,
4-booster bar, "Level N" tag in V1, boxes/curtains instead of doors): they give level CONTENT and flows, never art.

| tool | what |
|---|---|
| `vgrab V1\|V2\|path OUTDIR [--width W] [--crop x y w h] [--jpg] T[:NAME]...` | exact frame at any time (AVAssetImageGenerator, tolerance 0; ~0.1 s per frame, random access) |
| `vocr [--crop x y w h] [--scale S] IMG...` | Vision OCR → JSON lines (`lines`, `words` with px boxes + confidence) |
| `vscan V START END FPS` | streaming per-frame features (no frames on disk): luma, board-background share, dark share, booster-bar green, blue-ink count + bbox, colour count, 3 heart slots, HUD back-button colour (blue/red/purple = normal/Hard/Super Hard), timer-digit signature, and TOUCH DISCS (the iOS screen-recording touch indicator: transient grey round blobs) |
| `vindex.py scan V` / `build V1 V2` / `write` | segment the scan into play/non-play, OCR every screen, assemble levels (stages of "Levels 1-4", elevator phases, popups), taps/bumps/timer → `research/video-index.json` + `.md` |
| `vextract.py level V N [--t T]` | read the board of level N from its start frame → phone-schema JSON + overlay + ink IoU (+ elevator hidden layers) in `video-frames/work/extract/` |
| `vextract.py read FRAME.png [--out J] [--overlay O]` | same for any frame |
| `vextract.py replay V N [--json J]` | REPLAY CHECK of a level JSON against the video's taps |
| `vextract.py compare A.json B.json` | cell-by-cell comparison (best integer shift) |
| `vbatch.py V1:5 V2:33 ... \| all` | level + replay for many levels, one process → `work/extract/batch-summary.json` |
| `vsheet.py V START END STEP [--crop x y w h] [--marks t:x:y,...]` | contact sheet of exact frames (look before you trust) |
| `vmatch.py [--min 0.5]` | which extracted boards are the same level (V1 vs V2, video vs the phone's research/levels) |

## vextract: the reader (bot.py adapted)
- Ink = saturated blue with G < 0.66·B (core (21,116,254); pipes/boxes/exiting arrows are cyan, G/B ≥ 0.69), band y 180-1122 px.
- Grid: comb fit of stroke centre lines (bot.py) → pitch/origin, lstsq refine (resid 0.4-1.4 px on the validation set).
- Cells: 5×5 window ink ≥ 30 % (rounded corners of 4-px strokes leave ~45 %). Edges: a short line PERPENDICULAR to the edge
  (±max(2, 0.15 pitch)) must cross ≥ 2 ink px. Heads: triangle base wider than 1.5 strokes and ink at min(0.27 pitch, 0.9 stroke)
  beyond the head cell (dense boards have small heads). Occluded runs bridged straight (bot.py rule).
- Obstacles (video skin): `tape_pink` (Linked Arrows tie, V1 L7+), `curtain` (V1 purple crate + counter, blocks rays until its counter
  hits 0), `box` (V2 pure-cyan block + bomb counter, same rule), `pipe` (V2 light-blue tube + mouth rings + counter badge merged; ends +
  out directions; counter by OCR of the badge digit), `elevator` (V2 L31+: hatched lavender platform; per-cell lavender share ≥ 20 %),
  `hand` (tutorial pointer; ignored), `text` (V1 "Level N" tag; ignored). Counters are OCR'd (`counter`; Vision is flaky on this
  font, so bbox + centre crops at 4 scales, then a tight crop around the white digit blobs; all 51 counters of the two videos read).
- ELEVATOR hidden layers (`reveal()`): the platform's arrows are read from the start frame; when the last of them leaves the platform
  drops and a second layer appears in its place. The tool finds that moment (lavender share collapses), reads the first stable frame
  after it ON THE START GRID, and appends the new arrows with `"layer": 2, "under_elevator": k`; `elevators[k]` gets `t_active`,
  `hidden_arrow_ids`, `reveal_frame` (full-res PNG kept in `video-frames/V?/`).
- JSON = the phone schema + `source:"video"`, `video`, `t`, `frame`, `counter`s, `blocker_cells`, `elevators`, `fit_px` (px grid for
  re-reading later frames), `verify` (ink IoU raw and with 1-px tolerance, missed/extra px; overlay: red = frame ink we do not draw,
  orange = model ink the frame lacks).

## vextract replay: what it proves
For every board tap in the index (touch-down disc; the game acts on release), frames at t-0.12, +0.25, +0.6 and +1.5 s:
1. SYNC (t-0.12): arrows whose ink already vanished (a tap the disc detector missed) are removed free-first; each must be FREE in the
   model (`gone_free` / `gone_blocked`). Boxes/curtains/pipes the video shows broken are dropped; counter-driven breaks in the model
   are checked against the video (`blocker_counter_zero`, `blocker_still_there` if it persists >= 1 s, `pipe_broken`). An elevator
   the video shows dropped releases its hidden layer. If >= 40 % of live arrows vanish at once the board may have MOVED: the grid is
   re-fitted and adopted only when it explains clearly more of the frame's ink (`board_moved`; V1 L17 across a cut, V2 L35 a pan
   with no touch visible).
2. MAP the touch to the nearest live arrow <= 0.75 cell (head tip counts). The disc centroid is pulled off the stroke it covers: with
   several arrows within 0.85 cell, the one gone at +0.25 s (then +0.6, then +1.5 s) is taken (a second tap 0.3 s later can take a
   neighbour). No arrow -> `late` (an arrow near the point just left) or `miss`.
3. VIDEO outcome: `bump` = a confirmed heart loss (index), `exit` = the arrow/bundle lost its blue ink by +0.6 or +1.5 s, else `stay`
   (`stay_weak` for one-frame / debris / tutorial-hand-shadow discs). MODEL verdict free/blocked (arrows incl. live hidden layers,
   unbroken boxes/curtains, pipes: a ray entering a mouth against its outward direction leaves by the other mouth, bot.py rule).
   consistent = exit on FREE or bump on BLOCKED (+ every gone_free); inconsistent = the model contradicts the video.
Rules enforced (all measured here): a box/curtain breaks on the exit that makes arrows-removed == counter (every Linked bundle member
counts); a pipe breaks after `counter` passes; an elevator's layer 2 is live the moment its last platform arrow leaves (drawn
~0.4-0.9 s later); a bumped arrow is redrawn BLACK in V2 and still counts as present.
Limits: it only tests what the player did — an extra arrow the player never needed, or a missing blocker that never mattered, is
invisible to it (the IoU check covers missing/extra ink). Negative control (V1 L19): reversing 3 arrows -> 2 inconsistencies flagged;
deleting arrows or dropping curtains -> 0 (the one-sided limit above; the IoU drops instead).

## Gotchas
- `mfx frames` decodes from 0 unless `MFX_SEEK=1` (the owner's mp4s are constant-frame-rate: seeking is safe); `vgrab` is random access.
- V2 has an AssistiveTouch-like grey circle fixed at the top right (outside the touch band) and iOS notification banners (Vietnamese)
  that cover the HUD for ~1 s (hearts "vanish": not a loss).
- The tutorial hand's grey drop shadow looks like a touch disc: taps next to the hand are flagged `near_hand` (tutorial levels only).
- Exiting arrows: V1 turns rainbow/cyan at once, V2 turns light cyan; vacated cells show faint grid dots (not ink).
- Frames for replay/reveal are JPEG q0.9 in a temp dir, deleted after each run (hundreds per level).
