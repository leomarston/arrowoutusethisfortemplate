# Maze Out — items / pieces / obstacles (phone session 1; colours = median sRGB from untinted 'shot' PNGs, 1178x2556)

| item | shape | colours (sRGB) | size (pt, at fit zoom) | first level | seen_in |
|---|---|---|---|---|---|
| Arrow (idle) | snake polyline through cell centres, round caps, small corner radius; filled triangular head | black (0,0,0) | stroke 3.7 pt at pitch 17.9 pt (≈0.2 pitch); head base ≈0.55 pitch wide, tip ≈0.37 pitch past the head cell centre, base ≈0.2 pitch behind it; tail cap ends at the tail cell centre | L32 | shots/003 |
| Arrow (exiting) | same, sliding along its own path | light blue (not sampled yet; see video/S1-P01-press2s.mov frames) | — | L32 | shots/010, video/S1-P01 |
| Vacated-cell dots | small dot at every cell centre an arrow left | (197,225,255) | ~1.5 pt | L32 | shots/043 |
| Tap ripple | grey translucent disc at the touch point (drawn at release) | grey (not sampled) | not measured | L32 | video/S1-P01 |
| Pink TAPE | 1-cell-wide pink band across 2-4 parallel straight arrows with a crossed-straps X | (254,57,131) | 1 cell x (n arrows) | L32 (x4 bundles), L38 (x2), L44 (x3) | shots/003, 056, 090 |
| DOOR | rectangle of blue horizontal slats, orange riveted frame, purple inner frame, purple hexagon lock with a keyhole in the centre | fill (95,166,241), frame (255,170,16), lock (187,82,218) | any rectangle (L33: staircase of 5; L34: 4 around the edges; L37/43/46: wide bands) | L33 | shots/027, 036, 052, 085, 102 |
| KEY | gold key hanging on a purple ring threaded on an arrow's straight segment | gold (244,180,20), ring (178,27,251) | ≈2 cells long | L33 | shots/027 |
| PIPE | 1-cell light-blue tube (straight, L, U or long frame shapes), gold rims at both mouths, dark-orange counter box with a white number | tube (78,200,246), rim (253,190,7), counter (211,79,0) | 1 cell wide | L35 | shots/042, 047, 056, 076, 081, 090 |
| Background | plain white board, no grid lines | (255,255,255) | — | — | — |
| HUD pause/back | rounded square buttons: blue normal (4,143,253), red Hard (250,65,68), purple Super Hard (154,0,241) | | ~36 pt | L32/L34/L39 | shots/003, 036, 061 |
| HUD timer pill | stopwatch icon + m:ss + 3 hearts (243,39,26) on a blue pill (108,148,220) | | | L32 | shots/003 |
| Boosters | green rounded squares with red count badges: left = crystal/magnet "3", right = light bulb "3" (never used this session) | | ~56 pt | L32 | shots/003 |

## Player part 2 additions
- BOX (first L50): purple slab (sampled ~ (173,92,230) mean incl. highlights), lighter-purple corner bolts (221,147,245), silver 4-lobed
  counter ring with a dark-purple number disc; L50 10x3 cells; L51 three 4x3-ish boxes; L53 two 3x3 boxes; L56 two large squares; L57 a
  4-step staircase. seen_in: shots/134 (unlock icon), 135, 140, 154, 174, 179.
- RED (bumped) ARROW: stroke (238,10,19), anti-aliased rim ~ (249,179,183); stays red. seen_in: shots/110, 122 (L47/L48).
- BUMP '✖' marker: red X badge with dark outline at the contact point + the blocker flashes red for ~0.3 s (motion-frames/S1-L47-bump-1).
- Rocket Race badge (home, left column): blue hexagon with a rocket + number / 'Join'; Weekly Contest = trophy tab (red '!' badge when updated).
