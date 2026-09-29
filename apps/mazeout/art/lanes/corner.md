# Lane "corner" — the CORNER obstacle (v552, first on L70) + its unlock card icon

Round 3 lane paused at 17:18 with the recipe, eight layer renders, the card icon and the proof script but no lane log, no
lane manifest, no hit-animation data and no `cornerWedge`; finished 2026-09-25 evening (round 4). Kept from the paused lane:
the model and every board measurement in `art/ui/recipes/corner.py` (re-rendered: the eight layers are byte-identical), the
facing analysis, the two-layer design and `corner_proofs.py`. Added: `cornerWedge` (the id the code loads), the card fixes,
the measured hit animation (`corner_anim.py`), the clip / wedge proofs, the lane manifest and the code requests below.

Files: `art/ui/recipes/corner.py` (recipe), `art/ui/recipes/corner_anim.py` (hit animation data + evaluator),
`art/ui/recipes/corner_proofs.py` (sheets), `art/lanes/corner.entries.json` (10 entries), outputs in `art/ui/out/`,
sheets in `art/ui/sheets/corner/` + `art/ui/sheets/m_corner*.png`, `m_unlockIconCorner.png`.

```sh
PY=~/.venvs/mf3d/bin/python                                               # from apps/mazeout
$PY art/tools/art_batch.py --manifest art/lanes/corner.entries.json --3d  # all 10 (about 5 s)
$PY art/ui/recipes/corner_proofs.py board facings card wedge bounce clip stats
$PY art/ui/recipes/corner_anim.py --keys                                   # fit vs clip + the 60 Hz key table
```

## What ships (ids, frames, anchors)

| id | frame pt | anchor | what |
|---|---|---|---|
| `cornerWedge` | 64 x 64 | frame centre = cell centre | THE sprite the code loads today (CornerLayer.swift, ObstacleSet.spriteIDs, BoardArt.names, PathCore Validator.spriteIDs): the **UpRight** corner (plate facing down-right), i.e. the orientation CornerNode draws at angle 0. Pixel-identical to `cornerUpRightSpring` + `cornerUpRightPlate` composited. |
| `corner{DownRight,DownLeft,UpRight,UpLeft}Spring` | 64 x 64 | frame centre = cell centre | the blue coil spring + domed foot, UNDER the plate |
| `corner{DownRight,DownLeft,UpRight,UpLeft}Plate` | 64 x 64 | frame centre = cell centre | the red plate, OVER the spring |
| `unlockIconCorner` | 100 x 100 | frame centre = 456's ink centre (196.55, 413.25) | the card illustration ("Corner! / Unlocked! / Arrows turn when they hit the CORNER!") |

Board frames are drawn at the design pitch 32 pt: 64 pt = 2 x 2 pitch, centred on the corner cell's centre. The art OVERFLOWS
the cell (plate 1.25 x 0.36 p on the cell diagonal, spring + foot reaching 0.98 p behind the centre), exactly as the
original's does (L70: the capture's corner bbox is x -0.80..+0.45, y -0.47..+0.78 p around the cell centre). The engine scales
by pitch / 32 and must size the layer to the SPRITE (2 p), not to one cell (code request 1).

## Measurements (phone v552 lossless shots 457 L70, 470 L71, 498 L76, 521 L79, 526 L80, 533 L82: 21 corners, pitch 14.7-20.6 pt)

In pitch units, corner frame: n along the facing s (+ = out of the spring), u along the plate (+ = screen down-right for
s = (1, -1)); every number is constant across the six levels (0.01-0.02 p scatter), so the sprite scales with the zoom.

| part | capture | ours |
|---|---|---|
| plate u | -0.602 .. +0.617 | -0.611 .. +0.623 |
| plate n (back .. front) | -0.281 .. +0.069 | -0.286 .. +0.075 |
| spring foot n | -0.974 | -0.978 |
| spring u | -0.303 .. +0.263 | -0.314 .. +0.264 |
| lobes | 3 fat coils, period 0.226 along -n, grooves -0.43 / -0.65 / -0.88, a darker domed foot -0.88 .. -1.00 | same (corner.py) |
| drop shadow | black 12-14 %, (0.015, 0.040) p, almost no blur | same |

Region colours, capture vs ours in place, averaged over all 21 corners (CIEDE2000 of the region means): plate front band
#E05244 / #E94B3F 1.6; plate middle #E4392D / #EA3025 1.4; back band #CD322A / #DA2D24 2.5; ends #CE352F / #DB2922 3.2;
centre #E54D3C / #ED4637 1.4; spring lobes #788BB0 / #788CB1 0.7; foot #5D6C98 / #5B6999 1.2.

### Facings: rotation is NOT enough for one of the four (checked before relying on rotation)

SPEC-gameplay 3.9 / research JSON: facing s (y down) (1,-1) = downRight, (-1,-1) = downLeft, (1,1) = upRight, (-1,1) = upLeft.
Each capture compared with the canonical (1,-1) capture under all 8 dihedral transforms (L76, L79, L80, same level = same
pitch): (-1,-1) = the canonical rotated 90 deg ccw (mean |d| 2.7-7.7 vs >= 34 for the others; identity baseline 1.6),
(1,1) = rotated 90 deg cw (4.5-5.2), but (-1,1) matches NEITHER the 180 deg rotation nor a mirror well (8.4-12.7): its plate's
lit end stays up-left (lum 120 vs 79 at the other end, as on the canonical) and its shadow stays below -- the original draws
that facing as its own render, lit from the screen top. So the original's lighting is rotated for three facings and not for
the fourth. Ours: the canonical render + two exact quarter-turns + one separate UpLeft render (corner.py FACINGS).
Consequence for today's code (one `cornerWedge`, rotated per turn): upRight / downRight / downLeft come out exactly as the
original; upLeft gets the plate's lit end and the shadow on the wrong side (sheet `wedge_L076.png`, rows UpLeft). The
per-turn layers fix it (code request 2).

## Hit animation (MEASURED; corner_anim.py)

Clips `S2-L070-corner-first-use`, `S2-L070-corner-lower-turn-up` (L70, facing (1,-1), pitch 20.63) and
`S2-L071-corner-right-moving-turns-up` (L71, facing (-1,-1), pitch 19.66), 60 Hz, full-res crops of the corner cell; the
plate's red centroid projected on s, the spring's pixels along s. The three clips give the SAME curve in pitch units, frame
by frame within 0.003 p: it scales with the zoom.

- **Plate: translates along s only.** No squash (length 74.3 px and thickness 19.8 px identical on every frame), no rotation,
  no colour change. (A 0.02 p drift along the plate during the whole press + bounce is not modelled: < 0.4 pt.)
- **Spring: stretches/compresses along s between a FIXED foot and the plate** (the foot's far end stays at n -0.914 on every
  frame; the coils near the plate move most) = a scale along s about the foot.
- The exiting arrow is drawn OVER the corner the whole time (clip frames 1.281-1.381); silent.

Timing, relative to the `.corner` beat (the head reaching the corner cell centre; clip 1: tap R 1.1644 from the tail track,
beat R + T(2) = 1.2795, tail at the corner centre R + T(4) = 1.3456, with SPEC-motion-audio's exit kinematics):

| phase | when (s after the beat) | plate offset x along s (pitch) | curve |
|---|---|---|---|
| rest | < -0.012 | 0 | |
| press | -0.012 -> +0.004 | 0 -> -0.093 | ease-out (one 60 Hz frame; measured -0.083 on the first frame after the beat with the head still covering part of the plate, -0.002 one frame before) |
| hold | +0.004 -> release | -0.093 -> -0.105 | linear (the body slides over the plate) |
| release | tail at the corner centre + 0.010 | -0.105 | |
| overshoot | release + 0.063 | +0.079 | ease-in-out |
| back | release + 0.124 | -0.030 | ease-in-out |
| rest | release + 0.229 | 0 | ease-in-out |

Fit vs the 21 measured frames of clip 1: rms 0.0035 p, max 0.0093 p. Spring: scale k = 1 + x / 0.694 along s about the
pivot cell centre + (-0.98 p) s (0.694 = foot pivot to the plate's back face): k 0.849 fully pressed, 1.114 at the overshoot.
INFERRED: "release when the tail passes" -- every recorded hit is a 3-cell arrow, so a fixed 0.066 s hold fits the clips
equally; physically the plate stays in while the body slides over it. Replaces SPEC-motion-audio 3.5.6's pop (1.0 -> 1.15 ->
1.0, a DECISION from older builds) and board.json `corner.popScale/popDur`.

60 Hz key table (hold 0.066 s, the clips' case; `corner_anim.py --keys` prints it for any hold):
`-0.012 0 | +0.005 -0.093 | +0.021 -0.096 | +0.038 -0.099 | +0.055 -0.101 | +0.071 -0.104 | +0.088 -0.089 | +0.105 -0.026 |
+0.121 +0.046 | +0.138 +0.079 | +0.155 +0.062 | +0.171 +0.019 | +0.188 -0.020 | +0.205 -0.030 | +0.221 -0.027 | +0.238 -0.021 |
+0.255 -0.014 | +0.271 -0.007 | +0.288 -0.002 | +0.305 0`

## Card (unlockIconCorner, shot 456)

Same model at 73.4 pt per pitch (the card's plate is 92.5 pt long vs 26.0 pt on L70's board). The paused lane's card was
too bright/orange with even ends and a uniform front rim, and its spring sky-blue: plate all dE00 4.8, ends 9.3, front 7.4,
foot 9.1. Round 4 (card only; the board layers are untouched): the plate's ends and back band painted deep red from 456's
profile (G 27 / 15 / 5 at u -0.4 / +0.4 / +0.58), the front rim line faded along the plate (brightest mid-plate as on 456),
the spring rougher (0.40), graded onto 456's measured six-band tone ramp (lavender grey, not sky blue), the foot lighter and
0.03 p longer. Now: plate all 0.4, middle 0.3, back 1.5, ends 2.1, front 3.3, centre 2.0; spring all 1.1; foot 5.0 (dE00 of
the region means); silhouette IoU 0.928. Ink 149.6..244.6 x 365.9..461.9 pt (456: 150.3..242 x 367..458 + AA).
The sparkles around the icon on 456 are the live UnlockTwinkles; no text is baked.

## Proofs (LOOKED at)

- `board_L070.png`, `board_L071.png` (1:1 capture px = game size): ours pasted in place at the lattice anchor over each
  captured corner reads as the same object; `*_2x.png` for L070/L071/L076/L079/L080/L082.
- In-place numbers over all 21 corners at the anchor: silhouette IoU 0.878 mean (0.820 min), mean dE00 11.4 (p90 30.4);
  registration bias 0.000 / -0.001 p. The capture-vs-capture floor (the SAME v552 sprite at two cells of one level) is
  IoU 0.95-0.99, dE00 0.7-3.7: our own model differs per pixel (sharper coil glints, the plate's sheen band) while every
  region colour sits within dE00 0.7-3.2 and every extent within 0.011 p.
- `wedge_L070/L071/L076.png`: capture | `cornerWedge` rotated as CornerNode rotates it | the per-turn layers.
- `clip.png`: S2-L070 first-use frames | our two layers posed by corner_anim at the same time after the beat.
- `bounce.png`: the animation spec at 60 Hz; `facings.png`: capture | ours | in place | diff x4 per facing.
- `card_456.png`, `card_456_context.png`, `m_unlockIconCorner.png`: the card icon in place over 456.

Self-grades: board layers + `cornerWedge` **A** (identical at game size; side by side at 4x the coil glints are sharper and
the plate sheen is a band where the capture has a streak). `unlockIconCorner` **A-** (the capture's lowest lobe reaches
0.04 p further up-left; our plate sits 0.016 p up-left of the capture's).

## CODE REQUESTS (board B2 + shell; the art never edits App/)

1. **Size (needed even with one sprite).** `App/Board/CornerLayer.swift` `CornerNode.init`: the layer is `p x p` with
   `contentsGravity = .resize`, which squeezes the 2 x 2 pitch sprite into one cell (half size). Make it the sprite's frame
   at the level's pitch, centred on the cell centre:
   `let side = 64.0 * p / 32.0  // sprite size_pt x pitch / design pitch` ; `layer.bounds = CGRect(x: 0, y: 0, width: side, height: side)` ;
   `layer.position = c` (unchanged) ; `inner.frame = layer.bounds`. Rotation stays about the centre (the anchor is the centre).
2. **1:1 (per-turn layers + the measured hit animation).** Replace the rotated `cornerWedge` + pop with two sublayers,
   spring under plate, both `side x side` centred on the cell, NO rotation:
   `let suffix = [.upRight: "UpRight", .upLeft: "UpLeft", .downLeft: "DownLeft", .downRight: "DownRight"][turn]`;
   `spring.contents = art.image("corner\(suffix)Spring")`, `plate.contents = art.image("corner\(suffix)Plate")`; if either is
   missing, fall back to today's `cornerWedge` rotated per turn. Facing unit vector s (screen, y down):
   upRight (0.7071, 0.7071), upLeft (-0.7071, 0.7071), downLeft (-0.7071, -0.7071), downRight (0.7071, -0.7071).
   Spring `anchorPoint` = the foot pivot (cell centre - 0.98 p s) in unit coords of the 2p frame:
   upRight (0.1535, 0.1535), upLeft (0.8465, 0.1535), downLeft (0.8465, 0.8465), downRight (0.1535, 0.8465)
   (then set `spring.position` so the frame stays centred on the cell). Hit: in `BoardEngine.playBeats`
   `case let .corner(cid, aid, s)`: `hold = t(s + Double(cells(aid) - 1)) - t(s)` (the tail reaching the corner centre;
   tape members: that member's cells), then from `begin: t0 + t(s)` run two `CAKeyframeAnimation`s sampled at 60 Hz from
   `corner_anim.offset(t, hold)` (table above; `calculationMode .linear`, like the exits): plate `position` += x p s;
   spring `transform` = scale along s: `CGAffineTransform(a: (1+k)/2, b: (k-1)/2*sg, c: (k-1)/2*sg, d: (1+k)/2, tx: 0, ty: 0)`
   with k = 1 + x / 0.694 and sg = +1 for upRight/downLeft, -1 for upLeft/downRight. A second hit while one runs restarts
   from the current value. board.json `corner` -> `{"pressLead": 0.012, "pressDur": 0.016, "push": -0.093,
   "holdEnd": -0.105, "releaseAfterTail": 0.010, "peak": [0.063, 0.079], "trough": [0.124, -0.030], "restAt": 0.229,
   "pivot": -0.98, "springLen": 0.694}` (replaces popScale/popDur). Z: the corner stays in `roots.obstacle`, below `mover`
   (the clip shows the exiting arrow over the plate).
3. **Preload lists.** `ObstacleSet.spriteIDs` (`.corner`) and `BoardArt.names`: add the 8 `corner{Turn}{Spring,Plate}` ids
   (keep `cornerWedge`: the fallback and the id PathCore's `Validator.spriteIDs` checks; it may add the layer ids too).
4. **Unlock card.** After the manifest merge: `python3 tools/uiart_gen.py` (adds `.unlockIconCorner`, `.cornerWedge` sizes
   64 x 64 and the 8 layer cases) and `tools/sync_art.sh`. `App/Shell/Popups/UnlockOverlay.swift` `UnlockContent.of`: add
   `case .unlockIconCorner: ink = CGRect(146.55, 363.25, 100, 100)` (the whole canvas; centre = 456's ink centre, which is
   also the pop anchor and the twinkles' centre). Without it the default 120 x 110 box draws the icon 10 % too big, 3 pt high.
5. **Level tools.** `tools/levels/lvtool/Sources/lvtool/Endless.swift` still refuses corners ("no cornerWedge art"): the art
   is shipped now (content owner's call; not an art change).

## Remaining gaps (honest)
- Per-pixel the board sprite is ours, not a copy: sharper glints on the coils and a sheen BAND on the plate where v552 has a
  thin streak; visible only side by side at 4x.
- Card: the lowest lobe's up-left reach (0.04 p short) and a 0.016 p plate offset; the lobes read a touch thinner than 456's.
- The hold rule (tail-tied) is INFERRED from 3-cell arrows only; the spring's own wobble after the plate settles was not
  measurable (no residual motion above 1 capture px after release + 0.23 s).
