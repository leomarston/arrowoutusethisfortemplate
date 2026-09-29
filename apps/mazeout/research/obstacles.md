# Maze Out — obstacles (phone session 1)

## Pink TAPE (first L32)
- Look: a pink band 1 cell wide laid across 4 parallel straight arrows, with a pink X (two crossed straps) on it; covers one cell of each.
- Rule (4/4 observations on L32): ONE tap on any taped arrow sends all four arrows out together (the tape leaves with them), provided
  every bundled arrow's ray is clear. Untested: tapping when only some rays are clear (expected: bump).
- Bot: tape_pink class; a bundle is one unit; tapped at a member's tail cell.

## DOOR + KEY (first L33)
- Door: blue slatted shutter, orange outer frame with rivets, purple inner frame, purple hexagon lock with a keyhole; doors are
  rectangles standing on the board's bottom edge; they hide arrows. Door cells block rays.
- Key: gold key hanging on a purple ring threaded on an arrow's body.
- Rule: when a key arrow leaves, its key flies to the next locked door (L33: lowest/leftmost first), unlocks it (~1.0 s) and the door
  shatters (~1.2-1.6 s after the tap), revealing its arrows. Clip: video/S1-L33-key-first.mov (decode with tools/frames2).

## PIPE (first L35) — added by player part 2 from part-1 notes
- A light-blue tube (straight / L / U / frame shapes) with gold rims at both mouths and an orange counter box with a white number.
- Rule: a ray entering a mouth continues out of the other mouth in that mouth's outward direction; each passage -1; at 0 it shatters.
  Tube cells (not mouths) block. Seen L35, L36, L38, L41, L42, L44, L48 (three U pipes capping three columns, counters 4/4/4), L49 (5 U pipes).

## BOX (first L50, unlock card 'Box! Unlocked!' / 'Clear required amount of arrows to break the BOX!')
- Look: a wide purple slab (rounded corners, 4 lighter-purple bolts), a silver 4-lobed ring in the centre holding the counter number.
  L50: 10 x 3 cells under the maze, counter 10.
- Rule (L50, 10/10 decrements observed): each arrow cleared ANYWHERE on the board decrements the counter by 1; at 0 the box breaks
  (clip video/S1-L50-box-break.mov) and its cells become ordinary empty (dotted) cells. Nothing was under it on L50.
- Bot: class 'box' (cells block like a door until it breaks); its counter ring/digits/bolts are 'box_part'.

## BUMP (measured on L47, L48)
- Tapping an arrow whose ray is blocked costs 1 heart (rightmost red heart → grey-blue), the arrow slides toward the blocker and back,
  and turns RED (238,10,19) — it STAYS red for the rest of the level but otherwise behaves normally (clips video/S1-L47-bump-1.mov,
  video/S1-L48-bump-2.mov). The win popup still says 'Perfect!' with a heart lost.
- BUMP TIMELINE (clip video/S1-L47-bump-1.mov decoded with tools/frames2 at ~53 fps → motion-frames/S1-L47-bump-1/; 3-cell arrow,
  head 3 empty cells from the blocker, pitch 18.08 pt; times are clip ms, the tap lift is just before 283 ms):
  * ~290 ms the arrow starts to slide ALONG ITS OWN PATH (snake motion: the tail follows the body) toward the blocker at a constant
    ~400 pt/s (~22 cells/s): head tip 306.9 → 243.7 pt in ~160 ms, stopping when the tip touches the blocker's stroke edge (travel 63 pt = 3.5 cells).
  * ~450-580 ms it slides back to its rest position (~130 ms, faster than the way out); it turns RED during the return (~516 ms) and stays red.
  * at contact (~516-830 ms) the BLOCKER arrow flashes RED and a red '✖' badge (dark outline) sits at the contact point; both fade by ~850 ms.
  * a faint red tint over the screen during ~500-800 ms; the grey touch ripple is visible at the tap point. 1 heart lost.
