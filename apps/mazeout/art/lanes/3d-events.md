# 3d-events lane: event, leaderboard and shop props (3D, route B3)

Lane scope (orchestrator task, 2026-09-25): the ui-art 3D entries for events, the leaderboard and the shop, which are the
home event badges, the Sky Jump stage chests, the Rocket Race rockets, the prize bowl, the Weekly Contest trophy and the
six shop coin packs.

Copying line: every asset here is OUR SDF model rendered by our renderer (mfrender through `ui3d.render_case`). The phone
shots were only LOOKED AT and measured in pt (sizes, proportions, colour targets written as hex in the recipes); nothing
was traced, sampled into a texture or reused. File names are neutral.

## Files (this lane only)

- recipes: `art/ui/recipes/3d-events_coins.py` (coin + bowl + 6 packs), `3d-events_chest.py` (3 chests),
  `3d-events_badges.py` (3 badges + 2 rockets), `3d-events_trophy.py` (trophy)
- lane scratch manifest: `art/lanes/3d-events.entries.json` (full entry objects: source, file, size_pt, ref, status, notes)
- outputs: `art/ui/out/<id>@3x.png` (16 files)
- caches (gitignored): `build/ui-art/usdz/3d-events_*/`, `build/ui-art/events3d/coin_*.npz` (the coin mesh, instanced)
- sheets (gitignored): `art/ui/sheets/m_<id>.png`

Rebuild and check (from apps/mazeout; one render process, MF_WORKERS=2, ~2 min for all 16 once the meshes are cached):
```
PY=~/.venvs/mf3d/bin/python
$PY art/tools/art_batch.py --manifest art/lanes/3d-events.entries.json --3d
$PY art/tools/manifest_sheets.py --manifest art/lanes/3d-events.entries.json <ids>
$PY art/tools/manifest_check.py --quiet --lanes art/lanes/3d-events.entries.json   # 0 of the 16 fail
```

## Entries

| id | status | output path | reference used | self-grade | remaining differences |
|---|---|---|---|---|---|
| coinPackTiny | done | art/ui/out/coinPackTiny@3x.png | research/shots/meta-011 (1,000 card), pile bbox 82 x 38 pt | B | Our coins are slightly flatter in tone. The reference's highlight is whiter and sits on the upper-left rims. Our face star relief reads a little soft at 1x. |
| coinPackSmall | done | art/ui/out/coinPackSmall@3x.png | meta-011 (5,000), 81 x 46 pt | B | Our arrangement is our own. The reference's centre column is one coin taller. |
| coinPackMedium | done | art/ui/out/coinPackMedium@3x.png | meta-011 (10,000), 81 x 56 pt | B | The pile is 4 pt narrower than the reference (77 vs 81 pt). The reference's big coin on edge sits more to the left. |
| coinPackBig | done | art/ui/out/coinPackBig@3x.png | meta-011 (25,000), 98 x 56 pt | B | The reference's coin on edge stands higher, on top of a stack. |
| coinPackSuper | done | art/ui/out/coinPackSuper@3x.png | meta-011 (50,000), 95 x 58 pt | B | Our two coins on edge sit in the front row. The reference has one high on the left and one mid-right. |
| coinPackGiant | done | art/ui/out/coinPackGiant@3x.png | meta-011 (100,000), 96 x 62 pt | B | The reference is a touch denser at the flanks. |
| coinBowl | done | art/ui/out/coinBowl@3x.png | research/shots/023 (Claw ladder "10000" card); meta-045 (Streak Race rows) looked at | B | The reference heap has a tall coin standing on edge at the upper left and one big coin tilted toward the viewer in front. Ours are smaller and the heap is 2-3 pt lower. The band has a very slight dark ring at its base. |
| stageChestGreen | done | art/ui/out/stageChestGreen@3x.png | research/shots/065 (Sky Jump popup, Stage 1 tile) | B | The reference's end straps show a D-shaped inset of the chest colour on the left end, which ours barely shows (the view is nearly frontal). The reference lock plate is a bit larger. |
| stageChestBlue | done | art/ui/out/stageChestBlue@3x.png | 065 (Stage 2 tile) | B | As green. Our lid is a little more cyan. |
| stageChestPink | done | art/ui/out/stageChestPink@3x.png | 065 (Stage 3 tile) | B | As green. |
| eventBadgeStreak | done | art/ui/out/eventBadgeStreak@3x.png | research/shots/026 (home, "9h 7m" badge) | B- | The reference flags are bigger cloth with stronger folds (they cover most of the plaque), a 3 x 2 check pattern and fatter poles. Our flags are smaller and flatter. The live timer is not baked. |
| eventBadgeSkyJump | done | art/ui/out/eventBadgeSkyJump@3x.png | research/shots/070 (home, Sky Jump joined, "0" / "23h 57m") | B- | The reference pad is wider and flatter (its layers overhang the clouds), the clouds are softer and pinker, and more of the drum is covered. The count plate is live text. |
| eventBadgeRocket | done | art/ui/out/eventBadgeRocket@3x.png | research/shots/168 (home, Rocket Race "4" / "6h 13m") | B | The reference rocket is narrower and taller, and its fins reach down onto the drum. The navy starry panel is close. The count on the glass is live. |
| rocketMine | done | art/ui/out/rocketMine@3x.png | research/shots/178 (race lanes, the player's red/yellow rocket); 167 looked at | B- | The reference nose is rounder and blunter and the body is wider at the band. The reference flame is a larger, brighter fireball. Ours is our own painted puff, drawn at 68 x 98 pt with the flame included. |
| rocketOther | done | art/ui/out/rocketOther@3x.png | 178 (opponent rockets, white/blue) | B- | As rocketMine. The reference body is a bluish white with a blue nose. |
| trophyCup | done | art/ui/out/trophyCup@3x.png | research/shots/meta-017 (Weekly Contest info, "Compete against your friends!"); meta-016, 130, 131, 026 nav looked at | B- | The reference ear handles are fuller, with a small hole and a flat top. The reference stand is a taller trapezoid. The reference gold is slightly more lemon. The dark halo in the popup is not part of the asset. |

## Decisions and changes the art director has to merge

The lane never edited `art/MANIFEST.json`. Everything below is in `art/lanes/3d-events.entries.json` (the merge tool
`manifest.py merge art/lanes/3d-events.entries.json` shows 16 diffs).

1. **Owner** of all 16 entries: `3d-events` (they were `ui-art`). **Source** of each:
   `art/ui/recipes/3d-events_{coins,chest,badges,trophy}.py:<id>` (they named a planned `props.py`).
2. **Frame sizes changed** to what the phone shows (the old sizes were estimates, several from web frames):

   | id | old size_pt | new size_pt | why |
   |---|---|---|---|
   | coinPack* (6) | 90 x 70 | **102 x 66** | the six piles measure 81-98 x 38-62 pt on meta-011. One shared frame, each pile fitted to its measured bbox, bottom-aligned (anchor_pt 51, 64 = the pile's base centre) |
   | coinBowl | 84 x 72 | **74 x 62** | 69 x 56 pt on 023 |
   | stageChest* (3) | 68 x 46 | **56 x 42** | 52 x ~38.5 pt on 065 |
   | eventBadge* (3) | 70x86 / 76x76 / 70x80 | **80 x 84** (all three) | one shared base (hex plaque 67 wide, ring 59 wide). Bottom-aligned, anchor_pt 40, 82 = the ring's bottom centre |
   | rocketMine / rocketOther | 44 x 70 | **68 x 98** | 64 pt across the fins x 74 pt nose to nozzle, plus the flame, on 178 |
   | trophyCup | 120 x 130 | **62 x 58** | 57 x 53 pt in the Weekly Contest info (meta-017). The render scales up cleanly. |
3. **Refs moved to phone shots** (v552 beats web frames): eventBadgeRocket -> 168, rocketMine/rocketOther -> 178,
   trophyCup -> meta-017, coinPack* -> meta-011 per card, each with `anchor_pt` for an in-place sheet. **eventBadgeRocket,
   rocketMine and rocketOther lose `confirmed: false`**: they are on the phone (163-189, 168, 178).
4. **Live text, never baked.** These are the suggested text centres in our frames (pt from the frame's top-left), taken from the
   reference layout. Tune them in the SwiftUI preview.
   - Badges: timer on the drum front at about (40, 68).
   - Sky Jump count: on the pink plate at about (40, 41).
   - Rocket badge count: on the porthole glass at (39.3, 32.2).
   - rocketMine / rocketOther: glass centre (33.4, 30.2) if a lane label is wanted.
   - coinBowl amount: on the band front at about (37, 53).
   - Chest "Stage N": the popup's own label overlaps the chest's lower edge, as on 065.
5. **navTrophy (not this lane's)** is the same cup design as trophyCup (026: gold cup, orange up-arrow). The trophy recipe
   can render it with one more ASSETS case if the owning lane wants it.

## Method notes (for whoever iterates next)

- **Coin = one mesh, instanced.** `coin_mesh()` meshes the SDF once (cached by its parameters) and `coins_part()` places
  it at every pose as a premeshed Part (`ui3d.premeshed`), so a 90-coin pile renders in under a second after the first mesh.
- **Painted gold.** The coin's colour comes through its uv: u = the normal's axis component (underside 0, edge 0.5, face 1).
  A ramp paints deep orange underneath, orange on the edge and yellow on the faces (STYLE C.1 "painted bevel").
  Gotcha: keep the uv off the texture border (0.03..0.97). The sampler wraps, so u = 1.0 on a flat face bled the
  underside paint into every top face as streaks.
- **Coins on edge** are slid forward automatically until they clear every stack (`_hits`), so no coin is cut by another.
- **No cast shadows on the trophy** (`shadow=False`): the bowl's shadow drew a hard diagonal band across the knob that the
  reference does not have.
- **Flag checker uv** is planar along the pole frame. The texture must be defined on [0, 1]^2 (a -1..0 v range got
  clipped to one row, which gave stripes on the first try).
