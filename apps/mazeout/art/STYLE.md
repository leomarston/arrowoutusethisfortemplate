# Maze Out — art style guide (measured) and the art route per family

Art spike, 2026-09-25. Every number below was measured on the UNTINTED runner shots from the owner's iPhone 15
(`research/shots/NNN-*.png`, 1178 x 2556 px lossless sRGB, 393 x 852 pt, **pt = px x 393 / 1178**), on the store icon
and on the board/HUD parts of the store screenshots (`research/store/`). The captures were only looked at: nothing is
traced, sampled into an asset or reused. Every asset is ours (code, our SVG, our SDF models rendered by our renderer).

Tools that produced the numbers (re-run them when new shots arrive):

| tool | what it measures |
|---|---|
| `art/tools/measure_board.py` | stroke, lattice pitch, heads, caps, ink/ground, vacated dots (shots 003/004) |
| `art/tools/sample_palette.py` | the palette table in §D (+ `art/ui/sheets/palette.png`, swatch next to each sampled spot) |
| `art/ui/tools/compare_swap.py` | in-place A/B: erase the element from the shot, paste ours, IoU + CIEDE2000 (sheets `ab_*.png`) |
| `art/ui/tools/compare_c.py` | family C side-by-sides (`c_arrow.png`, `c_worker.png`) |

Sheets live in `art/ui/sheets/` (gitignored; regenerate with the commands in PIPELINE.md).

---

## Decision summary

| family | route | why (evidence) |
|---|---|---|
| **A. Board** (arrows, heads, dots, trail, silhouette borders) | **vector in code** (Core Animation paths from §A numbers) | the board is pure `#000000` ink on `#FFFFFF`, exact lattice (residual < 0.4 px); nothing to rasterise |
| **B1. Stretchable glossy chrome** (all buttons, panels, pills, tabs, ribbons, toggles, badges, progress bars) | **SwiftUI code**: `art/ui/code/GlossyChrome.swift` | same fidelity as SVG (in-place ΔE00: pause 3.88 vs 3.87, Resume 3.94 vs 3.91, Quit 5.15 vs 5.12; identical IoU), and it stretches to any popup size, takes live EN/TR text, has a pressed state, ships 0 bytes |
| **B2. Fixed flat-glossy icons** (HUD heart, coin, stopwatch, sound/haptic glyphs, close X, gear, hex lock, key, chevrons) | **SVG -> @3x PNG** (`art/ui/src/gen_*.py` -> `svg.py`) | same fidelity as SwiftUI (heart ΔE00 4.47 vs 4.50), one cheap bitmap drawn many times (lists, HUD at 10 Hz), multi-layer highlight art is simpler to author and review in SVG |
| **B3. UI props that look RENDERED** (booster icons: frozen hourglass, bulb; big "Out of Time" stopwatch; broken heart; coin stacks; nav basket/garage/trophy; Claw prizes; ∞-heart) | **3D** (SDF recipe -> `ui3d.py` -> mfrender, transparent @3x PNG) | soft volumetric shading + hue-shifted bevels; decide per icon on its sheet: flat gradient + one specular = B2, soft form shading = B3 |
| **C1. Characters + home/loading/event illustrations** | **3D** (SDF -> USDZ -> mfrender), characters as cut-out puppet LAYERS | `c_worker.png`: the SVG worker reads as flat 2D, the 3D worker sits in the reference's family (soft form, glossy eyes, specular); the puppet proof recomposes the full render within mean \|Δ\| 0.2/255 |
| **C2. Glossy 3D arrows** (app icon, capsule-machine pile, loading/win art) | **3D with a painted bevel** (`recipes/arrows3d.py`) | `c_arrow.png`: 3D matches face colour, bevel highlight and the orange lower side; the SVG offset-stroke bevel reads flat and bands; the pile needs arbitrary poses anyway |
| **C3. Board obstacles drawn ON the white board** (pink tape; next: doors, keys, pipes) | **SVG / vector** (tape: `gen_props.tape`, parametric in lanes + orientation) | `ab_tapeV4.png`: SVG IoU 0.915 vs 3D 0.785; the reference tape is a crisp vector sprite (flat strap face, one streak, uniform rim), not a lit object |

---

## §A. Board (vector in code; the engine owner draws it)

Measured on L32 at fit zoom (`003`, `004`), cross-checked at 1.57x (`005`) and 0.79x (`006`) zoom.

| quantity | value | notes |
|---|---|---|
| lattice pitch | **53.59 px = 17.88 pt** (L32, 20 x 20 board at fit) | rows and columns identical; max residual 0.39 px -> an exact square grid |
| board placement (L32) | cell centres x 79.9 ... 1098.1 px, y 807.1 ... 1825.3 px; centre (196.5, 439.1) pt | horizontally centred on the 393 pt screen; the grid is 20 pitches = 357.6 pt wide (17.7 pt side margins) |
| stroke width | **11.5 px = 3.84 pt = 0.215 pitch** | coverage-summed; 0.226 at 1.57x, 0.233 at 0.79x: the stroke scales with the zoom (world units) -> use **0.22 pitch** |
| ink / ground | `#000000` / `#FFFFFF`, both flat | no tint, no anti-alias colour fringe; long edges are pixel-snapped |
| cap | round, centred on the tail cell centre (tail extends 0.5 stroke past it) | tail profile of row 0 |
| join | round (outer corner radius = 0.5 stroke), inner corner sharp | i.e. `lineJoin = .round` |
| head | isosceles triangle, base **33 px = 11.0 pt = 0.616 pitch**, length **32-33 px = 0.61 pitch**, corners rounded r ~2.5 px (0.047 pitch) | 37 heads, p10-p90 32.0-33.3 px |
| head position | tip **19.3 px (0.36 pitch)** past the head cell centre for ← →; ↑ 16.1 px (0.30), ↓ 23.3 px (0.435) | the vertical heads sit 3.6 px (1.2 pt) lower on screen than the horizontal rule predicts; perpendicular centring is exact (±0.1 px). INFERRED: an anchor offset in the original. Copy the per-direction values. |
| vacated dots | `#C5E1FF` flat discs, **10.3 px = 3.43 pt = 0.192 pitch** diameter (area-equivalent incl. AA), one per cell centre of the exited path | `004`, 5 dots, spacing = pitch |
| exiting arrow | turns light blue and slides along its path (`levels.md`); colour to be measured by the motion analyst | |
| rainbow trail (store 1) | hue gradient ALONG the moving stroke: `#FF470E` -> `#FF8C0E` -> `#CECB0B` -> `#0CE10D` (long plateau) -> `#0CBCD2` -> `#0D1DFE` -> `#E03FFF` -> `#F335E7`, period **~3.8 cells**; same stroke width; the head takes the colour at its position | store shots are marketing composites (stroke/pitch 0.25 there) |
| pink/blue trail (store 5) | `#FA05CF` (magenta) -> `#0D77FF` -> `#14B4FF` (sky) -> back, period **~4.3 cells** | which trail ships when (skin? level?) is for the motion/meta analysts |
| trail particles | 5-point rounded stars in the trail colours, ~0.3-0.6 pitch, scattered behind the tail, fading | store 1, 5 |
| silhouette border (store 5) | a thin magenta/blue gradient outline following the board silhouette (crescent) | measure on the first phone level that has one |

Engine recipe (for the engine owner, not an asset): `CAShapeLayer` per arrow, `lineWidth = 0.22 * pitch`,
`lineCap = .round`, `lineJoin = .round`, black; head = a filled rounded-triangle path (base 0.616, length 0.61 pitch,
corner r 0.047 pitch) at the per-direction offset above; dots = one `CAShapeLayer` of circles r 0.096 pitch `#C5E1FF`.

Board obstacles (vector sprites, route C3):

| obstacle | measured (003, L32) | our asset |
|---|---|---|
| pink tape, 4 lanes | **53 x 186 px** = 0.99 x ((N-1)+0.47) pitch; base band `#D72169` (edges `#BF1C5D`); two straps corner to corner (~8 deg), strap face `#FF3B84`, bright near its top end `#FF93B4`, darker at the bottom end `#D42069`, rim `#BC215B`, strap-on-base shadow `#B31E58`, light streak `#FF7DA7` along one long edge; the TL->BR strap lies on top; soft grey drop shadow 3 px down | `art/ui/out/tapeV4@3x.png` (20 x 65 pt), generator `gen_props.tape(lanes, vertical)` |
| door / lock / key (L33), pipe + counter caps (L35+) | seen on `027`-`029`, `040`-`044`; NOT measured yet | same method: vector sprite, parametric in size (doors span w x h cells) |


### §A.2 Board obstacles, measured (pipeline agent, 2026-09-25; appended — supersedes the "NOT measured yet" row above)

Tool: `~/.venvs/mf3d/bin/python art/tools/measure_obstacles.py [door lock key tape pipe]` -> `art/tools/obstacles_measured.json`
(lattice per level from `research/levels/L0NN.json`; every size is px, pt and a FRACTION OF THE PITCH, because the board
scales with the zoom). Shots: L33 `027` (pitch 53.53 px), L34 `036` (43.65), L35 `042` (84.20), L36 `047` (65.45), L37 `052`
(49.10), L38 `056` (53.56). Sprites: `art/ui/src/gen_board.py` (SVG, drawn at the **design pitch 32 pt/cell**, the engine
scales by pitch/32; anchors per case in the manifest). Side-by-side sheets `art/ui/sheets/m_<id>.png`
(`art/tools/manifest_sheets.py`): each sprite pasted over the capture at its lattice anchor covers the original exactly.

**Pink tape (linked arrows)** — 4 lanes L32 (V and H), 2 lanes L38, 3 lanes L44.

| quantity | value |
|---|---|
| band | across **0.99-1.01** pitch; along **(N - 1) + 0.44-0.47** pitch (4 lanes 3.455-3.473, 2 lanes 1.438); centred on the bundle's cell block |
| layering | the whole tape lies OVER the bound arrows: their shafts stop at the band's edges (correction: the art-spike note implied lanes show through; `m_tapeV4` round 1 had lane gaps, removed in round 2) |
| straps | two straps corner to corner, width 0.49 of the band, end radius 0.13 pitch; the TL->BR strap on top in both orientations; ~8 deg (4 lanes) to ~25 deg (2 lanes) off the band axis |
| colours | as the §A table row above (base `#D72169`, strap `#FF3B84`/`#FF93B4`, rim `#BC215B`, streak `#FF7DA7`); drop shadow 0.05 pitch down, blur 0.035 |

**Door (locked shutter)** — L33 staircase 4 x 4/8/12/16/20; L34 5 x 17 (two), 13 x 4, 14 x 4; L37 22 x 10, 11 x 10 (two); also
L41, L43, L46, L47 (sizes from the content owner's levels.json; `manifest.py add-door W H L c0 r0`).

| quantity | value (pitch units) |
|---|---|
| outer frame | x = the cell block exactly (insets -0.02..+0.04); top **0.05-0.08** below the block top; bottom on the block's bottom edge (0.03-0.10 above it in the bbox: the shadow) |
| corners | top r **0.374**, bottom r 0.05 |
| orange header / posts | header **0.747** tall (face `#FFAA10`, lower band `#FFA20A` from 0.575, top line `#FFB324`, a `#FFC92D` glint 0.075 down); posts **0.39** wide: outer dark band 0.11 (`#CD6D07` left / `#CF7512` right), face `#FFA40D`, 1 px light line `#FFD04A`, dark outline `#3A0E06` 0.037; foot `#B05A03` 0.09 |
| purple inner frame | band top 0.28, sides 0.24, `#AE3DD3` with a `#CE60F1` top highlight; top corners a **soft 45-deg chamfer 0.32 rounded r 0.20** (reads rounded at fit zoom, faceted on the 22-wide door); inner rim `#69239B` (top 0.093, sides 0.056) with a `#E08AF5` line outside it; no dark line along the bottom |
| shutter | from the purple band's inner edge down to 0.09 above the frame bottom; top corners chamfer 0.30; face `#5FA6F2`; a shadow gradient `#274161`->transparent 0.16 under the top, side shading 0.075 |
| slats | **ONE PER CELL ROW, seam on every row boundary** (seam rows vs the lattice edge: +-0.5 px on all three levels; periods 53-54 px @ 53.53, 43-44 @ 43.65, 49-50 @ 49.10); per row: seam `#2B57A8` 0.03, highlight `#A8E2FE` 0.04 below it, face, a lower band `#579DEB` 0.72-0.94, a darkening 0.06 into the next seam; foot `#23519C` 0.09 |
| rivets | two gold domes, centre 0.458 in from each side, 0.411 below the frame top, d 0.374; radial `#FFFFF1` -> `#FFD23A` -> `#EF8E0B`, specular upper right |
| drop shadow | offset (0.02, 0.056), blur 0.035, black 0.5 |
| lock placement | on the door's vertical centre line (dx 0.00 +- 0.02), **0.17-0.20 (use 0.18) below the frame bbox centre**, on every door size |

**Hex lock** — **1.962 x 1.81** pitch (vertices left/right, flat top/bottom), in a blue socket 0.093 (`#3374BE`, darker toward the
hex); bevel facets top `#E36CFB`, upper sides `#CB58EF`, lower sides `#9331BC`, bottom `#7A2BA3` (0.15 top/bottom, 0.10 sides); face
`#CE67E6` -> `#BB51DB` -> `#A242C8`; corners rounded 0.13; keyhole circle r 0.225 at y -0.20, tail to y +0.42 widening 0.24 -> 0.40,
`#44205F` dark top -> `#7F36A3`, light lower lip `#DB8EEB`.

**Key (on a key arrow)** — bbox **1.03 x 2.20** pitch (vertical keys, L33) / 2.22-2.44 x 1.03-1.30 (horizontal, L34/L37: the
ribbon loop lies along the arrow). Registration: the arrow's line and the centre of the key's first cell on the tail side;
the key covers 2 cells toward the head. Pointing DOWN: ribbon loop x +-0.37, y -0.76..+0.16 (`#C020FF`..`#D948FF`, width 0.155);
knot band x -0.14..+0.10, y -0.07..+0.19; ring centre (-0.03, 0.29), outer 0.93 x 0.78, hole 0.37 x 0.34 (torus `#B35A00` hole ->
`#FFC93A` crown -> `#D27A06` edge); shaft x -0.25..+0.17, y 0.60..1.45; bit x 0.08..0.57, y 0.91..1.40. Up = rotate 180; right =
transpose; left = INFERRED.

**Pipe** (L35 `042`, pitch 84.2 px; checked on L36, L38) — CODE route for the tube (CAShapeLayer), SVG for the mouths and the counter.

| quantity | value (pitch units) |
|---|---|
| tube | **1.00** wide, centred on the cell line; outer corner radius ~0.43, inner corner ~0.07 |
| tube shading (lit from the upper right) | across a VERTICAL run, left -> right: rim `#2BCCF2` 0.02, dark `#23A6E0`/`#28A0DD` -0.45..-0.26, ramp `#31B1E7` -> `#7DDAFA` (centre) -> highlight **`#9DE2FB` +0.07..+0.15** with a hard right edge, then `#4CC8F6` +0.16..+0.33, `#3DC4F6` to +0.41, bright rim `#32CFF9`/`#37D8F5` +0.42..+0.51. A HORIZONTAL run is the same profile rotated: highlight `#98E1FA` -0.16..-0.06 (hard top edge), dark `#27A0DD` +0.28..+0.44 at the bottom |
| tube shadow | grey, offset down-left: 0.15 below a horizontal run (`#A6A6A6` -> white), 0.05 left of a vertical run |
| mouth collar (both ends) | a gold collar **1.22 across x 0.61 along**, centred 0.10 OUTWARD from the end cell's centre; the outward face shows the opening: an ellipse 0.20 deep along the axis, interior `#722F00` (far side) -> `#E97F01`; collar face `#FEED82`/`#FDF2AB` with a `#FAAF05`..`#EF9A04` rim; drop shadow below |
| counter box | on the run next to a mouth (L35: centred 0.515 past cell 7, i.e. on the boundary of cells 7/8): orange face **1.09 x 1.14** (`#CD4D00`; top band `#BC3200`, mid `#E66B00`, a `#A92403` top edge), between two gold collars 0.40 wide x **1.33** tall (`#FDF2AB` face, `#F0A606` rim); total **1.90 x 1.33**; the number is live text: white fill, `#822521` outline |
| break | the tube shatters into cyan shards when its count reaches 0 (`S1-L35-pipe-break.mov`) |

Not on the phone (v552) and therefore not measured: the CURTAIN counter gate (purple crate / cyan gear box skins in the
owner's videos), the ELEVATOR platform (owner's V2 video L29-31), the CORNER wedge (May/Jul builds). Their manifest entries carry
`confirmed: false` and video/web references.

**Curtain counter block (owner video V1, Aug build, L11 t 186 s; appended 03:40)** — NOT on the phone; measured on the 592 px
video frame (pitch 42.5 px, looked at only): a **3 x 3-cell** block (2.94 pitch, centred on the cells), purple rounded square r
~0.45 (top edge `#FDDFFF` -> `#E899F4`, face `#B453EE`..`#C36AF8`, bottom band `#592F95` -> `#3E2C68`), a silver sphere r **1.07**
(lit top-left `#E5F2FB`, lower right `#48498C`, reflected-light crescent `#CFE1FF` at the bottom) with four stub cylinders on the
diagonals out to r ~1.36 (w 0.58), a purple ring r 0.68 (`#5D46AE` -> `#C698FF` top) around a navy well r 0.53 (`#142C6A`..
`#1F3C80`) holding the live counter. Its unlock popup ("Curtain! Unlocked! Clear required amount of arrows to open the CURTAIN!",
V1 t 185 s) shows the DOOR art. V2 (Jul) skin: a cyan ice block holding a fused bomb (not measured). Sprite:
`gen_board.curtain_crate` (`curtainCrate`).

**Phone BOX (v552, 135 L50 at pitch 28.07; director round 2 -- the skin every counter level ships, SPEC.md 5.11)**: a flat
violet slab covering its cell block exactly: corner r **0.40** pitch, face `#BC5BF6`, a light top line (`#E9A6F6`, 0.07),
side edges darkening over 0.26 to `#5935A2`, a bottom lip 0.28 (`#AB50EB` -> `#582D96` -> `#4F2F83`), four rivet domes
d 0.31 centred **0.50** pitch in from both edges, a soft grey shadow 0.1 below. The counter ring is a FIXED size (it does not
grow with the block): silver sphere r 0.98 pitch with four stubby lugs on the diagonals (0.62 -> 1.37, w 0.62), purple ring
r 0.72, navy well r 0.50 holding the live counter. Sprites `gen_board.box_slab` (`boxSlab`, 9-slice, cap insets 0.5 pitch +
the 4 pt margin) + `gen_board.box_ring` (`boxRing`); the curtain crate above is not shipped.

**Phone CORNER (v552, first on L70; corner lane round 4, `art/lanes/corner.md` has every number)** -- supersedes the "CORNER
wedge (May/Jul builds) not measured" line above: a red rounded PLATE on a blue coil SPRING, one cell, the plate on the cell's
diagonal facing s (plate 1.25 x 0.36 p, n -0.28..+0.07 around the cell centre; three fat lavender-grey coils + a domed foot
reaching 0.98 p behind the centre; a thin grey shadow 0.04 p down). The art OVERFLOWS its cell: sprites are 2 x 2 pitch
(64 pt at 32 pt/cell) centred on the cell. A rendered-look prop, so the 3D route (`art/ui/recipes/corner.py`), not SVG. The
original rotates one sprite (lighting included) for three facings and draws the fourth (s = (-1, 1), upLeft) as its own
render: `cornerWedge` (UpRight, what the code rotates today) + per-turn layers `corner{Turn}{Spring,Plate}`. Hit animation
MEASURED (S2-L070/L071 clips): the plate translates along s (-0.105 p while the arrow slides over it, +0.079 p overshoot),
the spring scales about its fixed foot; no squash, silent (`art/ui/recipes/corner_anim.py`). Card icon `unlockIconCorner`.

## §B. Glossy UI chrome

### B.1 The layer recipes (measured; SVG in `art/ui/src/gen_chrome.py`, SwiftUI in `art/ui/code/GlossyChrome.swift`)

**Shape.** Every glossy button/pill is a **superellipse** `|x/a|^n + |y/b|^n = 1`, not a rounded rectangle: the edges
curve all the way (the pause button reaches full width only 36 px below its top). Fitted exponents: square HUD
buttons **n 3.5**, wide panel buttons **n 4.0** (face n 4.5). SwiftUI's `RoundedRectangle(.continuous)` is a
different curve; use the `Superellipse` shape.

**Square blue HUD button** (back, pause, settings), 40 x 40 pt body in a 44 x 44 pt frame (003 profiles):

| layer | spec |
|---|---|
| drop shadow | body shape, `#1E2940` at 0.8, blur sigma 0.93 pt, offset y +1 pt (dark right under the body `#5D6B83`, ~8 px below, faint on the sides) |
| rim | body shape, vertical gradient `#0047DB` 0 -> `#004CE4` 0.1 -> `#0050EA` 0.86 -> `#0465EF` 0.9 (lip top) -> `#004CE4` 0.94 -> `#0044D6` 0.97 -> `#0036BE` 1; sides darkened by a horizontal `#002E9A` 0.6 -> 0 over the outer 9 % |
| face | superellipse inset (12, 6, 12, 12) px of the 120 px body (= 4, 2, 4, 4 pt), `#0192FF` -> `#008BFE` |
| face light edge | the face outline stroked 7 px (2.33 pt), clipped inside, blur 0.23 pt, gradient `#50C8FF` 0 -> `#3FBCFF` 0.07 -> `#1B8EF8` 0.14 -> `#1488F8` 0.6 -> `#008BFE` 1 (a bright 5 px top edge, 2 px light sides, none at the bottom) |
| glyph (pause) | two bars 18 x 61 px (6 x 20.3 pt), 30 px apart; navy outline `#0B2B86` 3 px, rx 7; face `#EAFFFD`; bottom shade `#A9D5EB` then `#7BB7DC` (last 13 px) |

**Wide panel button** (Resume green / Quit red / Play / Continue / Try Again...), 125 x 89 pt body (007):

| layer | green | red |
|---|---|---|
| outline (body, 1 pt) | `#0A3C00` | `#5A0006` |
| rim (body inset 1 pt), vertical | `#006400` 0 -> `#007600` .55 -> `#008401` .84 -> `#007600` .9 -> `#005A00` .96 -> `#004A00` 1 | `#A0000C` -> `#B0000E` -> `#BC020F` -> `#A8000D` -> `#86000A` -> `#6A0006` |
| rim outer darkening | inner stroke 4 pt, 0.75, blur 1.33 pt | same |
| face (inset 23, 3, 23, 33 px of 375 x 267; n 4.5) — reaches the TOP edge (a pill seen from a little above) | `#02E10F` 0 -> .07, `#00E900` .1, `#00E400` .3, `#00D600` .65, `#00CA00` 1 | `#FF3838`, `#FF2A2A`, `#FB1E1E`, `#F01010`, `#E20808` |
| face light edge | `#66EC66` inner stroke 3.67 pt, alpha 0.9 top -> 0.2 bottom | `#FF6A6A` |
| glare line | `#91FC92` 1.5 pt at 0.85, 16 px under the top edge, following the top contour, fading out by 55 % of the face height | `#FFA6A6` |

**HUD heart** (lives), 29.3 x 25.3 pt in a 31 x 27 frame: outline = two ellipses leaning +-48 deg (rx 0.46 w, ry 0.38 h,
centres (0.5 +- 0.105) w, 0.485 h) + a tip wedge (base 0.89 h, half-width 0.21 w) — silhouette IoU 0.981 vs 003 (a
round-cone heart reached 0.963 with a blunt tip and was rejected on the sheet). Body radial `#FD6A48` -> `#FB3E2C` .25
-> `#F02416` .55 -> `#DC0C05` .8 -> `#B80400` 1 (centre 0.42, 0.40, focus 0.36, 0.33, r 0.62); darker top edge
`#8A0006` 0.8 -> 0 over 14 %; warm specular blob `#FFB189` -> `#FD9160` on the left lobe; a thin `#FF9A7C` streak on the
right lobe's upper-right edge; inner dark edge `#7A0610`; outline `#6E0E16` 0.53 pt; halo `#1D3570` at 0.6, blur 0.67 pt.

**Outlined label text** (live text, never baked): cream fill + a dark outline in the plate's hue + the same outline
dropped ~1.3 pt. Measured pairs (fill / outline): "Paused" ribbon `#FFFEFD` / `#802404`; "Level 32" tab `#FDF1DB` /
`#073993`; timer digits `#ECECF1` / `#152B6A`; Play `#F0FFF1` / `#076D02`; Resume `#FDF7E3` / `#097004`; Quit `#FDF6E3` /
`#6A0303`; booster badge digit `#FDF4E6` / `#7D101A`; toggle "ON" `#FCF6E2` / `#04B601`. Flat (no outline): HUD coin
digits `#3962AC`, home pill digits `#0B3A97`, panel labels ("Sound") `#632201`. Font: the fonts lane's OFL match
(the sheets use Arial Rounded Bold as a stand-in, which is NOT the match; the button bodies were judged, not the text).

### B.2 Evidence (in-place A/B on the untinted shots, element erased and ours pasted at the measured position)

| element | route | silhouette IoU | mean ΔE00 (p90) inside the element | sheet |
|---|---|---|---|---|
| pause button | SVG | 0.927 | 3.87 (12.7) | `ab_pauseButton.png` |
| pause button | SwiftUI | 0.927 | 3.88 (12.4) | |
| HUD heart | SVG | 0.956 | 4.47 (9.2) | `ab_heartHUD.png` |
| HUD heart | SwiftUI | 0.967 | 4.50 (9.4) | |
| Resume (green) | SVG | 0.918 | 3.91 (10.7) | `ab_buttonGreen.png` |
| Resume (green) | SwiftUI | 0.918 | 3.94 (10.7) | |
| Quit (red) | SVG / SwiftUI | 0.930 / 0.930 | 5.12 / 5.15 | `ab_buttonRed.png` |

In context at game size (`ab_context_003-L32-start.png`, `ab_context_007-L32-pause.png`) the swapped HUD and Paused
panel read the same as the capture; the remaining visible difference is the stand-in font. Iterations: pause v1
ΔE00 8.8 (face inset wrong: profiled at a corner column) -> v2 3.9 (centre-line profiles); heart v1 6.1 (round-cone,
blunt tip) -> 4.5 (two ellipses + wedge); green v1 lip mask left a hard band -> smooth rim gradient.

## §C. Illustration, characters, 3D props

### C.1 Render rig (mfrender, `art/ui/tools/ui3d.py` RIG + per-asset `light`)

| | default UI rig | arrows (`ARROW_LIGHT`) | worker (`WORKER_LIGHT`) |
|---|---|---|---|
| key | directional (0.55, -0.62, -0.56) camera space (upper-left front), 3000 lux, (1.0, 0.975, 0.94) | 2100 lux | 2600 lux |
| rim | (-0.75, -0.25, 0.60) from right-back, 1000 lux, cool (0.92, 0.96, 1.0) | 1000 | 1400 |
| fill | (0.2, 0.9, -0.4) from below-front, 260 lux, warm (1.0, 0.93, 0.85) | (0.1, 0.8, -0.6), 900 lux, neutral | 700 lux, orange (1.0, 0.78, 0.5) — fakes the warm bounce/SSS of the reference bodies |
| ambient | `build/ui-art/ui_env.png` dome, exponent -0.95 | -0.85 | -0.7 |
| tone mapping | off (ACES desaturates toy colours) | off | off |
| camera | perspective, fov 18 (props), 12 (arrows), 8 (flat top-down obstacles) | | |

Materials: toy plastic `gloss()` rough 0.30, ior 1.38-1.40 (arrows, eyes 0.22/1.45); body `gloss` rough 0.40 ior 1.28;
fabric/leather `satin` rough 0.5-0.62; metals nearly dielectric (`metal`: rough 0.34, ior 1.45, metallic 0.05).

**Painted bevel** (the key trick for the glossy arrows): the reference's shading shifts HUE toward a deeper saturated
shade (yellow -> orange `#FB8A03` -> rim `#E46011`), which a PBR falloff cannot do (it went olive-brown). The arrow
texture paints the bevel band (0.11 head-heights from the outline) by the outline's facing: down-right edges take the
measured shade and rim, up-left edges the highlight (`arrows3d.bevel_texture`); the rig then only adds form. Shades
per colour in `arrows3d.SHADES` (yellow `#FEBF0E`/`#FB8A03`/`#E46011`/`#FED23B`, red `#FA3633`/`#D4090B`/`#A80508`/
`#FC635F`, blue `#0292FE`/`#005FF1`/`#0647CC`/`#42B7FC`; green/purple/orange/cyan extrapolated for the pile — measure
them on the capsule machine before production).

### C.2 Our worker (character design, 3D route)

Their workers (looked at only: `002`, store 6/8): a tall leaning yellow bean with the face on it, thick black upper
lids, two black antenna sprouts or a cap/big glasses, indigo shorts, a square lilac buckle, a wrench, bare yellow feet.
**Ours** (`art/ui/recipes/worker.py`): same toy family (chunky golden capsule `#FFB612`, big glossy eyes, wide open
grin, stubby limbs, mitten hands, tool belt over work shorts, soft warm light) with a different silhouette and details:
a **gumdrop** body wider at the base; eyes with **free-floating rounded brows** and no lid strokes; one **orange hair
curl**; **teal** shorts `#1F95A6` and **dark-teal boots** `#1B5F70`; a **round brass buckle** `#F4B63A` and a
**red screwdriver** in the belt. Measured reference body tones (k-means): highlight `#FECB39`, lit `#FBB510`, shade
`#EE9B0D`, deep `#D07405` — our render lands in that family.

Evidence: `c_worker.png` (reference workers | ours 3D | ours SVG, same on-screen height, + 1/3-size silhouettes),
`c_worker_puppet.png` (torso layer, arm layer, their composite, the full render: mean |Δ| 0.2/255, 0.4 % of pixels
> 40 at the shoulder seam; shoulder pivot exported as `{"shoulderR": [77.13, 62.24]}` pt).

### C.3 Evidence for the arrows and the tape
`c_arrow.png`: the icon's three arrows re-composed with our renders at the measured head sizes and tip positions
(yellow 405 px head, tip x 584; red 408, tip x 510; blue 422, tip x 584). `ab_tapeV4.png`: the L32 top-left tape
erased (the 4 shafts under it redrawn at the lattice) and each route pasted in place.

### C.4 Known gaps (honest list, for the art lanes)
- **Worker**: no subsurface scattering or ambient occlusion (the reference bodies glow warm in the creases); hands are
  lumpy mittens; no fabric weave/leather grain; the face is less expressive (no lids, one mouth shape). Next: AO via a
  baked cavity texture, an SSS-ish warm fill per character, a mouth/eye shape set for the puppet.
- **Arrows**: the painted lower rim darkens slightly brown where the rig shades it; the reference's lower side is a
  thicker, brighter orange band. Next: widen the band and lift the fill.
- **Heart (SwiftUI)**: a small kink where the tip wedge meets the ellipses (CGPath union); the SVG heart is smooth.
- **Buttons**: the reference glare line is thinner and the side bevel lighter; the label font is a stand-in.
- **3D tape** (rejected): straps flat-lit, silhouette narrower (IoU 0.785) — kept in `build/` only as the losing candidate.

## §D. Palette (sampled on untinted runner shots; `python3 art/tools/sample_palette.py`)

Median of a 7 x 7 px box; "grad" = the spot sits on a gradient (use the layer recipes above for those).

| token | shot (x, y) px | hex |
|---|---|---|
| board.ground | 003 (600, 600) | `#FFFFFF` |
| board.ink | 003 (120, 807) | `#000000` |
| board.vacatedDot | 004 (80, 1611) | `#C5E1FF` |
| hud.coinPill.fill | 003 (305, 140) | `#BDDCFF` |
| hud.coinPill.digits | 003 (230, 130) | `#3861AC` |
| hud.coin.rim / face / star | 003 (66,130) / (112,146) / (97,124) | `#F7D000` grad / `#F4C300` grad / `#FBDD00` |
| hud.squareButton.face | 003 (1080, 300) | `#008CFE` |
| hud.squareButton.rimTop / lip | 003 (1061, 207) / (1061, 318) | `#044DE1` grad / `#0047DA` grad |
| hud.squareButton.glyph | 003 (1045, 260) | `#E9FFFD` |
| hud.panel.fill | 003 (760, 335) | `#BDDCFF` |
| hud.panel.topEdge / bottomEdge | 003 (760, 187) / (760, 356) | `#ECF5FF` grad / `#537EC9` grad |
| hud.timerPill.fill | 003 (540, 300) | `#6C94DC` |
| hud.timer.digits | 003 (480, 285) | `#EDEDF2` |
| hud.stopwatch.ring / face | 003 (283, 285) / (305, 305) | `#FDAE06` grad / `#F3E9D9` grad |
| hud.levelTab.fill / edge | 003 (470, 196) / (590, 226) | `#008EFE` / `#004EE9` grad |
| hud.heart.face / spec | 003 (660, 275) / (630, 270) | `#FB3A2A` / `#FC8258` grad |
| booster.tray.fill / edge | 003 (20, 2380) / (243, 2380) | `#BDDCFF` / `#749CE1` grad |
| booster.well | 003 (42, 2330) | `#648DD7` grad |
| booster.green.face / rim | 003 (64, 2330) / (50, 2400) | `#00E400` / `#1A901A` grad |
| booster.badge.red | 003 (172, 2432) | `#FF4344` |
| panel.frame.blue / inner field | 007 (70, 1300) / (589, 1421) | `#005DEC` / `#226DF5` |
| panel.rivet | 007 (70, 924) | `#4CA9EF` grad |
| panel.ribbon.top / bottom | 007 (589, 640) / (589, 790) | `#FFCF00` / `#FFB800` |
| panel.cream.fill / border | 007 (589, 1152) / (160, 1152) | `#F8E7D2` / `#D0987D` grad |
| panel.toggle.green / knob | 007 (640, 1070) / (890, 1030) | `#00E500` / `#009EFC` |
| panel.close.red | 007 (1040, 770) | `#FF3C3D` |
| panel.scrim (over white) | 007 (589, 2048) | `#1C1C1C` = black at alpha 0.89 |
| home.play.face | 002 (330, 2060) | `#00D300` |
| home.levelPlate.green | 002 (470, 1660) | `#05D001` |
| home.topPill.fill | 002 (590, 200) | `#DEEEFF` |
| home.gearButton.face | 002 (1024, 173) | `#0191FF` |
| home.nav.blue / homeTab | 002 (55, 2364) / (436, 2364) | `#0592FE` / `#11D5FF` |
| home.floor | 002 (1018, 2182) | `#D0D2ED` |
| home.wall.cream | 002 (55, 1182) | `#CAAE9D` |
| home.machine.blue | 002 (345, 1273) | `#2BA8DF` |

Store-icon arrows (k-means share): yellow `#FEBF0E` 69 %, `#FB8A03` 15 %, `#E46011` 7 %, highlights `#FEC920` /
`#FED23B` / `#FDD561`; red `#FA3633` 71 %, `#D4090B` 20 %; blue `#0292FE` 68 %, `#005FF1` 13 %, `#0647CC` 6 %.

## §E. Art list estimate (every graphic seen so far: shots 002-061, store 1-8)

Counts are estimates; "route" per the decision table. Brand items (name, logo, the purple scientist, the capsule
workers) are replaced by OUR designs in the same style.

| area | graphic | route | est. count |
|---|---|---|---|
| board | arrows + heads, vacated dots, tap ripple (grey disc), exiting colour, rainbow + pink/blue trails, star particles, silhouette border | A code | ~8 visuals (0 bitmaps; star particle = 1 SVG sprite) |
| board | pink tape (2-6 lanes? x H/V), tape leave FX | C3 SVG | 1 generator (+ variants) |
| board | door/shutter (orange frame, rivets, purple inner frame, slats; w x h cells), hex lock, shatter fragments | C3 vector + B2 SVG lock | ~4 |
| board | key on purple ring, key flight | B2 SVG (check vs 3D on its sheet) | 1-2 |
| board | pipe tube (light-blue glossy path), gold end caps, orange numbered counter box, pipe break FX | C3 vector (CAShapeLayer strokes) + B2 caps | ~4 |
| HUD | back, pause, settings square buttons; timer panel; timer pill; Level tab (blue) + "Hard Level" tab (red); coin pill | B1 SwiftUI | 6 components |
| HUD icons | heart (full; lost/empty state?), coin, stopwatch, "+" badge | B2 SVG | ~5 |
| boosters | green booster button + well + red count badge | B1 SwiftUI | 2 components |
| boosters | frozen hourglass (time freeze), light bulb (hint) — rendered look | B3 3D | 2 (+ popup-size versions) |
| popups | panel frame w/ rivets + ribbon title + cream inset + close X; toggles; streak chips row (x1..x100) | B1 SwiftUI | ~6 components |
| popups | sound / haptic glyphs, close X glyph, chevrons | B2 SVG | ~5 |
| popups | big stopwatch (Out of Time), broken heart, coin stack (+20), ∞-heart reward, pipe/door intro illustrations | B3 3D | ~6 |
| events | Streak Race logo plate + checkered-flags badge; Claw Challenge header scene (claw machine + workers + prizes), logo, hexagon-arrow icon, reward ladder nodes + lock cards + prize icons (coins 100/600/10000, bulb, ∞-heart 30m/6h), info overlay maze icon | C1 3D (scenes, prizes) + B1/B2 | ~15 |
| home | factory interior backdrop (pipes, valve, vents, console with buttons), capsule machine + arrow pile, round platform, OUR scientist mascot (new design, their style), 2 workers (ours) in ~4 poses, LEVEL plate (green/red), Play (green/red + "Hard Level" ribbon), top bar (avatar frame + default avatar, coin pill +, lives heart + timer/"Full", gear), Claw bar, bottom nav (basket, garage, trophy; selected raised tab) | C1 3D scene + puppet layers, B1 chrome, B3 nav icons | ~25 |
| loading | splash illustration (our logo, characters, flying arrows) | C1 3D | 1-2 |
| leaderboard (store 6) | rank rows gold/silver/bronze, hex rank badges, avatar portraits, coin-stack rewards, green capsule score chips | B1 + B3 + C1 portraits | ~8 (locked/offline per PLAN) |
| shop, settings | not captured yet | — | ? |
| app icon | ours (glossy 3D arrows in OUR composition, not theirs) | C2 3D | 1 |

Rough total: ~15 SwiftUI chrome components, ~20 SVG icons/sprites, ~35 3D renders (props, scenes, puppet layers),
plus the board in code.
