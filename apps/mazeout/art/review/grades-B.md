# Grader B: 3D art (props, scenes, characters, avatars, arrows, app icon) + composed home and loading

2026-09-25. Machine-readable twin: `art/review/grades-B.json`. Scope: every `family: 3d` entry of `art/MANIFEST.json` merged with the lane scratch manifests (characters, 3d-hud, 3d-events, scene), 79 ids, plus the composed home and loading proofs. Nothing in art/ was edited. These are the grades that count; the lanes' self-grades are listed only for comparison.

**Counts:** A 9 · B 39 · C 23 · n/a 8 (the unbuilt Jul avatar set). Composed: home **B**, loading **C**.

Scale: **A** = ship; **B** = ok (the same art, differences show only on inspection); **C** = redo (different at a glance, wrong size, colour or silhouette, or a defect).

## How it was judged
- At GAME SIZE: the @3x frame at 3 px/pt, viewed at about 1-2 px/pt, the way a 393 x 852 pt phone shows it. 2x crops were used only to name a difference already visible at 1x.
- `manifest_sheets` side-by-sides for every entry: reference | ours on the reference's backdrop | ours pasted in place at the ref anchor. Also compact contacts per group, and COMPOSED screens next to the reference shot at the same scale: home (002, 026, 035, 070, 168), loading (V1 t=0, store 8), Sky Jump (069) and Rocket Race (167). Palette spot checks against STYLE.md §D (home.wall.cream matches; the rocket lane area was measured, see below).
- The home mock: backdrop, then the sci rig (torso + head), console, sci arms, platform, machine, pile, LEVEL plate, the worker rigs at rig.json `placement_pt`, then a top bar (avatarDefault, iconCoin, heartLives, glyphGear on PIL stand-in chrome), eventBadgeStreak, Play, and the nav bar with navShop/navHome/navTrophy. The loading mock: loadingBackdrop, then the `char_loading_layout.json` cast, then logoArrowOut scaled to the original logo's box (x 21-218, y 65-217 pt).
- Regenerate (sheets are gitignored and go to `art/ui/sheets/gradeB/`):
  ```sh
  PY=~/.venvs/mf3d/bin/python   # from apps/mazeout
  $PY art/review/tools/gradeB_merge.py build/ui-art/review/merged.json   # MANIFEST + lane manifests, merged copy
  $PY art/review/tools/gradeB_sheets.py build/ui-art/review/merged.json  # m_<id>.png for every 3d entry
  $PY art/review/tools/gradeB_contact.py build/ui-art/review/merged.json '{"events": {"ids": ["eventBadgeStreak"]}}'
  $PY art/review/tools/gradeB_compose.py                                  # p_home*.png, p_loading*.png, p_workers_*.png, p_sci_002.png
  ```

## Redo list (C), most visible first

| # | id | owner | priority | why | fix |
|---|---|---|---|---|---|
| 1 | homeArrowPileFull | scene | high | The heap is peaked and chaotic, with arrows on edge, and ~25 % narrower than 002's wide, flat mound. It also spills ~20 pt below the window's inner edge onto the bezel; 002's heap stays inside the glass. It is the focal point of the home screen, and at game size it reads as a different pile. | Wide, low mound clipped to the glass; most arrows lie face-up to the camera; balance the colour mix (more cyan/purple, less lime). |
| 2 | homeArrowPileHalf | scene | high | Same overflow: a blue arrow crosses the lower-left bezel. 168 shows a vertical orange+cyan stream under the dispenser and a half heap inside the glass. | Clip to the window; make the stream 2 arrows. |
| 3 | homeConsole | scene | high | Too small and too pale next to the scientist. The rim spans x 112-283 pt vs 002's 100-293 (~0.9x). Ours is a flat cool-cream bowl with a thin blue lip; 002 has a bulging warm cream-to-yellow belly and a thick glossy blue rim. The scientist's hands sit ON it instead of gripping behind the rim. | Widen to ~193 pt at the rim, taller bulging belly with the warm gradient, thicker blue rim; then re-check the scientist's hands. |
| 4 | navHome | 3d-hud | high | Too small next to its neighbours: 026's raised Home icon is ~75 pt wide, ours ~53 pt (~0.7x), and the orange roof arch is thin. In the composed home it reads as a smaller, paler house under the tab. | Re-render ~1.4x (grow the frame to ~80 x 84 pt, or scale it in the tab) with a thicker orange arch and eaves. |
| 5 | avatarWalkie, avatarCapGlasses, avatarDetective, avatarBurger, avatarScientist, avatarParty, avatarNotebook, avatarBoxHead (8) | characters | high | Framing: ~0.7x of the phone's close-up, frontal, one shared grin (see the table below) | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| 6 | loadingBackdrop | scene | high | The press on the left is flat painted panels (V1: a detailed blue/pink machine with a lilac girder and a conveyor). The floor grid is regular. A speckled noise band runs along the floor horizon (y ~570-590 pt) and shows at game size. There is no crowd, no conveyor and no depth of field, and the characters get no contact shadows on it. | Remove the speckle band; model the press + girder + conveyor; soft warm light/haze; bake contact shadows under the cast. |
| 7 | scientistLoading | characters | high | Pose, expression and costume differ at game size. The fist is raised beside the head instead of punching toward the camera. The head is wide and flat with an open buck-tooth mouth (V1: a big open smile). Long puffy white sleeves cover the whole arm (V1: rolled short sleeves, bare fur arms). The torso is stiff and hidden behind the box and arrows. | Rebuild the run pose: fist forward, short rolled sleeves + fur forearms, white shirt, rounder head + smile, arrows held against the belly. |
| 8 | workerCarrier | characters | high | Too small, with the wrong proportions. V1's carrier is a tall bean whose legs reach the screen bottom (~y 830 pt); ours is a squat egg ending at ~y 700 pt, floating with dangling feet and no contact shadow. The box is a flat front slab whose two black hand-holes read as eyes (V1: 3/4 view from below, with arrows spilling out on top). | Taller body with running legs to the bottom edge; box in 3/4 view with arrows in it; a contact shadow. |
| 9 | clawHeaderArt | scene | high | Ships WITHOUT its two workers: the file was built at 07:59, before char_workerClawPair landed at 08:50. At game size the header is an empty claw box, where 023 is two big workers behind the prizes. The box interior is also a little darker/purpler than 023's neon blue. | Re-run `scene_make.py build clawHeaderArt` (it composites char_workerClawPair at (200,115)), then regrade. |
| 10 | rocketRaceBackdrop | scene | high | Below the header, ours is a flat lavender #6A48BA; 167 is deep indigo (#16105C at the top of the lanes to #420FAC). The chest is seen straight-on as an upright blue drum (167: 3/4 top view, gold bands, diamond clasp), sitting on a thin flat coin band instead of a pyramid hoard on a rock. The moon surface is flat. | Dark indigo lane gradient + stars; chest in 3/4 view on a rock with a pyramid hoard. |
| 11 | skyJumpIsland | scene | high | (1) The baked haze reaches the frame edge (alpha up to 83/255 on 39 % of the border), which draws a visible rectangle on the backdrop. (2) The island is ~0.8x of 069's (~172 vs ~215 pt wide at the ref box). (3) The chest is pale lilac-white with the lid thrown back and no shield, and the coins are sparse; 069 has a lavender chest with a quilted green lid and the green shield, surrounded by dense coin stacks. | Fade the haze to 0 inside the frame; island ~1.25x; chest as 069 (lavender body, shield on the lid front); dense coin stacks. |
| 12 | skyJumpIslandFar | scene | medium | The same frame-edge haze rectangle (alpha up to 65/255). The island is ~0.8x of 069's far island, with a sparse coin heap. | As skyJumpIsland. |
| 13 | skyJumpPopupScene | scene | medium | The coins are a pale beige-yellow and the hill is thinner, where 065's hill is saturated orange-gold with a glow and fills the corners. The chest is pale with the lid thrown back and no shield (065: lavender chest, with the shield hanging over the front). | Warm saturated coin ramp + glow; denser hill to the corners; chest as on 065. |
| 14 | workerRacers | characters | medium | The slide scene reads differently. The chute is a flat painted ribbon looping as a '9'; the riders stand upright on floating plates instead of sitting in sleds inside the chute; the room is flat and emptier; the checkered banner is missing. | Riders seated in sleds inside the chute, a modelled chute with depth, busier room, the checkered banner. |
| 15 | workerRunners | characters | low (P1) | The background crowd reads as crisp, saturated stickers floating above the floor horizon. V1's crowd stands on the floor, hazed and defocused, and warmer. The left conveyor pair is missing. P1 per SPEC 5.16. | Ground them (feet on the floor near the horizon), stronger haze/defocus, add the conveyor pair. |
| 16 | boosterDome | 3d-hud | low | Ring-stack shape right, but rings and ball are deep royal blue where V1's are light sky/cyan; sits ~3 pt high. Unconfirmed: the phone skin has only 2 boosters (SPEC 5.10). | Light sky/cyan rings + ball; lower 3 pt. Only if the 4-booster bar ever ships. |

Also fix the blocking defects in B entries: the **coinPack*** shadows are cut by the frame's bottom edge (a faint hard line). And note that **clawHeaderArt** may only need a rebuild, now that `char_workerClawPair` exists.

## Composed proofs

**homeProof: B.** At game size the composed home (scene layers + the three rigs at rig.json placement_pt + a mocked top bar / streak badge / LEVEL plate / Play / nav) reads as 002/026: same layout, lighting and characters (pink scientist, blue workers). Three things block an A: the arrow pile (peaked, spills out of the window), the console (small and pale), and the nav Home icon (~0.7x). After those: the capsule window bevel, the workers' thin arms and walkie pose, and the streak badge's small flags.  
Evidence: `p_home.png`, `p_home_noui.png`, `p_home_mid.png`, `p_home_low.png`, `p_home_top.png`, `p_workers_035.png`, `p_workers_026.png`, `p_sci_002.png`, `p_home_homeArrowPileHalf.png`, `p_home_homeArrowPileLow.png`, `home_composed.png`

**loadingProof: C.** The layout matches V1 t=0 / store 8, and logoArrowOut sits at the original logo's spot and size (x 21-218, y 65-217 pt; ours scaled to 197 pt wide). It reads in the original's style: blue plate + yellow bubble word + purple OUT! arrow plate. Its letters are narrower than 'MAZE' (svg family, not graded here). The cast and backdrop miss: the scientist's pose/costume, the carrier's size and box, a floating crowd, a flat backdrop with a noise band, and no contact shadows on anyone.  
Evidence: `p_loading.png`, `p_loading_s8.png`, `p_loading_mid.png`, `p_loading_low.png`, `p_loading_backdrop_only.png`, `loading_composed.png`

## Every entry

### Home scene

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| homeBackdrop | **B** | B | Every structure is on its measured spot and the composed home reads as 002. The tank area is greyer and less luminous (no vertical glass streaks) and the copper pipe is dull. | Lift the tank glow; add 2-3 soft vertical highlight bands. |
| homeConsole | **C** | B | Too small and too pale next to the scientist. The rim spans x 112-283 pt vs 002's 100-293 (~0.9x). Ours is a flat cool-cream bowl with a thin blue lip; 002 has a bulging warm cream-to-yellow belly and a thick glossy blue rim. The scientist's hands sit ON it instead of gripping behind the rim. | Widen to ~193 pt at the rim, taller bulging belly with the warm gradient, thicker blue rim; then re-check the scientist's hands. |
| homeCapsuleMachine | **B** | B | Shape, size and placement right. The window reads darker because the inner bevel is a thin light ring; 002 shows a thick (~12-15 pt) slanted light-cyan inner wall and the floor hatch. | Widen the slanted inner wall and show the window floor. |
| homeArrowPileFull | **C** | B | The heap is peaked and chaotic, with arrows on edge, and ~25 % narrower than 002's wide, flat mound. It also spills ~20 pt below the window's inner edge onto the bezel; 002's heap stays inside the glass. It is the focal point of the home screen, and at game size it reads as a different pile. | Wide, low mound clipped to the glass; most arrows lie face-up to the camera; balance the colour mix (more cyan/purple, less lime). |
| homeArrowPileHalf | **C** | B- | Same overflow: a blue arrow crosses the lower-left bezel. 168 shows a vertical orange+cyan stream under the dispenser and a half heap inside the glass. | Clip to the window; make the stream 2 arrows. |
| homeArrowPileLow | **B** | B | Reads as 'a few arrows plus one emerging'. Our arrows float mid-window (no floor), and the emerging arrow is cropped to a cone. 070's arrows lie on the window floor and the emerging green one shows its shaft. | Drop the arrows onto the window floor; show the emerging arrow's shaft. |
| homePlatform | **B** | B | Right size and placement. Our dais rim is a crisp bright ring; 002's is glassier, with a soft reflection of the wall. |  |

### Home characters

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| scientist | **A** | B | Composed on 002 at game size, it reads as the same character recoloured pink: same pose, size, eye line, coat, badge and pen. Minor: the crown tuft is a thin side wisp (002: a centred spiky tuft). The hands are big fur mitts on top of the console, while 002's grip behind the rim; this follows the console fix. |  |
| workerWalkie | **B** | B- | Same design recoloured blue, at the right size and spot on the composed home (rest frames 026/035). Differences that show at game size: noodle-thin arms and small hands (phone: thick arms, big 4-finger hands); the walkie is held up by the face (rest: held forward toward the machine); the default mouth is the open buck-tooth grin (035 rest: closed smile, which the rig's body_smile has); the egg body is a little squat. Separation from the royal-blue band is adequate but lower-contrast than the yellow originals. | Thicker arms + bigger hands, walkie forward at chest height, consider body_smile as the default. |
| workerClipboard | **B** | B- | Glasses, cap and belt read. The clipboard shows its white paper face (002/035: the brown board back with spiral rings), the arms are thin, and the green cap reads dark. | Board-back clipboard, thicker arms. |

### Home HUD props (badges, nav)

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| eventBadgeStreak | **B** | B- | Reads as the streak badge on 002/026. The flags are ~25 % smaller and flatter, so our navy hex plaque shows; the capture's cloth flags cover it. | Flags ~1.3x with bigger checks and folds. |
| eventBadgeSkyJump | **B** | B- | Reads as the Sky Jump badge. The pad spans ~70 % of the plaque; 070's pad spans it and its clouds overhang, so our purple hex interior shows above the pad. | Pad ~1.25x; wider, lower clouds. |
| eventBadgeRocket | **B** | B | Rocket is wider and shorter than 168's, and its fins end above the drum. | Narrower, taller body; fins down onto the drum. |
| navShop | **B** | B+ | Same size and colours as 026. The slots are arched outlines where 026 has dark vertical cut-outs; the coin rides higher. | Dark rounded-rect slot cut-outs. |
| navHome | **C** | B- | Too small next to its neighbours: 026's raised Home icon is ~75 pt wide, ours ~53 pt (~0.7x), and the orange roof arch is thin. In the composed home it reads as a smaller, paler house under the tab. | Re-render ~1.4x (grow the frame to ~80 x 84 pt, or scale it in the tab) with a thicker orange arch and eaves. |
| navTrophy | **B** | B | Same size as 026. The handles are thin loops (026: thick squarish ears) and the stem is multi-tier (026: one tall foot slab). | Fuller handles, single foot slab. |

### Boosters

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| boosterFreeze | **B** | B- | Reads as the frozen hourglass inside the green button at 56 pt and covers the original in place. Snow caps are thinner than the capture's thick white caps; the drips read comb-like. | Fatter snow caps (optional). |
| boosterHint | **B** | B+ | Reads as the bulb. Our glass is milk-white with no filament; the capture's is pale blue with a visible filament loop. | Pale-blue glass tint + a filament inside. |
| boosterPointer | **B** | C+ | Yellow set-square reads (unconfirmed, V1 only). Ours is more lemon and rotated steeper than V1's orange set-square, so the original peeks out in place. The phone skin has only the 2-booster bar (SPEC 5.10). | Only if the 4-booster bar ships. |
| boosterDome | **C** | C+ | Ring-stack shape right, but rings and ball are deep royal blue where V1's are light sky/cyan; sits ~3 pt high. Unconfirmed: the phone skin has only 2 boosters (SPEC 5.10). | Light sky/cyan rings + ball; lower 3 pt. Only if the 4-booster bar ever ships. |

### Popups

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| stopwatchBig | **A** | B+ | Same prop at 225 pt. The ticks are rounder pills than the capture's flat bars; that shows only at 2x. |  |
| heartBroken | **B** | B+ | Reads as the same broken heart. The lobes are flatter and wider than on 016, so the original peeks out under the left lobe in place. | Taller, rounder lobes (~+6 %). |
| coinStackReward | **B** | B | Same cluster (standing star coins in front, stacks behind), ~10 % small: 020's coins overflow ours in place. | Coins ~1.1x. |
| heartInfinite | **A** | B+ | Same at game size; the tip is marginally sharper. |  |

### Loading

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| loadingBackdrop | **C** | C+ | The press on the left is flat painted panels (V1: a detailed blue/pink machine with a lilac girder and a conveyor). The floor grid is regular. A speckled noise band runs along the floor horizon (y ~570-590 pt) and shows at game size. There is no crowd, no conveyor and no depth of field, and the characters get no contact shadows on it. | Remove the speckle band; model the press + girder + conveyor; soft warm light/haze; bake contact shadows under the cast. |
| scientistLoading | **C** | C+ | Pose, expression and costume differ at game size. The fist is raised beside the head instead of punching toward the camera. The head is wide and flat with an open buck-tooth mouth (V1: a big open smile). Long puffy white sleeves cover the whole arm (V1: rolled short sleeves, bare fur arms). The torso is stiff and hidden behind the box and arrows. | Rebuild the run pose: fist forward, short rolled sleeves + fur forearms, white shirt, rounder head + smile, arrows held against the belly. |
| workerCarrier | **C** | B- | Too small, with the wrong proportions. V1's carrier is a tall bean whose legs reach the screen bottom (~y 830 pt); ours is a squat egg ending at ~y 700 pt, floating with dangling feet and no contact shadow. The box is a flat front slab whose two black hand-holes read as eyes (V1: 3/4 view from below, with arrows spilling out on top). | Taller body with running legs to the bottom edge; box in 3/4 view with arrows in it; a contact shadow. |
| workerFlyer | **B** | B- | Right place and pose (hanging under a red arrow, a small blue arrow in the other hand). The red arrow is long-shafted; V1's is a chunky block arrow. | Block-arrow red (the arrowGlossy family). |
| workerFist | **B** | B- | Right place and size. Thin arms, a buck-tooth grin (V1: a wide smile), and it floats slightly with no contact shadow. |  |
| workerRunners | **C** | C+ | The background crowd reads as crisp, saturated stickers floating above the floor horizon. V1's crowd stands on the floor, hazed and defocused, and warmer. The left conveyor pair is missing. P1 per SPEC 5.16. | Ground them (feet on the floor near the horizon), stronger haze/defocus, add the conveyor pair. |

### Claw Challenge

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| clawHeaderArt | **C** | B- (without workers) | Ships WITHOUT its two workers: the file was built at 07:59, before char_workerClawPair landed at 08:50. At game size the header is an empty claw box, where 023 is two big workers behind the prizes. The box interior is also a little darker/purpler than 023's neon blue. | Re-run `scene_make.py build clawHeaderArt` (it composites char_workerClawPair at (200,115)), then regrade. |
| workerClawPair | **B** | B- | Both workers read on 023 at the right size and placement. The arms are thin and both wear the same buck-tooth grin (023: a laughing left worker with a big fist). Not yet composited into clawHeaderArt. |  |
| padlockGold | **B** | B+ | Reads the same at 44 pt. Ours is more lemon than 023's orange-edged gold; the keyhole is reddish. |  |
| coinPileSmall | **B** | B | The same glowing mound of stacks. Ours is flatter with paler coins and less orange in the crevices. |  |
| coinBowl | **B** | B | The bowl is pinker than 023's crimson; the coin heap is 2-3 pt lower and lacks the tall coin on edge at the upper left. |  |

### Streak Race

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| workerRacers | **C** | C+ | The slide scene reads differently. The chute is a flat painted ribbon looping as a '9'; the riders stand upright on floating plates instead of sitting in sleds inside the chute; the room is flat and emptier; the checkered banner is missing. | Riders seated in sleds inside the chute, a modelled chute with depth, busier room, the checkered banner. |

### Sky Jump

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| skyJumpBackdrop | **A** | B | Composed with our islands and pad, it reads as 069 (sky over a pink cloud sea). Cloud sculpting is softer, which is fine at game size. |  |
| skyJumpPad | **A** | B | Matches 069's '4' pad in size, bands and glow. |  |
| skyJumpIsland | **C** | B- | (1) The baked haze reaches the frame edge (alpha up to 83/255 on 39 % of the border), which draws a visible rectangle on the backdrop. (2) The island is ~0.8x of 069's (~172 vs ~215 pt wide at the ref box). (3) The chest is pale lilac-white with the lid thrown back and no shield, and the coins are sparse; 069 has a lavender chest with a quilted green lid and the green shield, surrounded by dense coin stacks. | Fade the haze to 0 inside the frame; island ~1.25x; chest as 069 (lavender body, shield on the lid front); dense coin stacks. |
| skyJumpIslandFar | **C** | B | The same frame-edge haze rectangle (alpha up to 65/255). The island is ~0.8x of 069's far island, with a sparse coin heap. | As skyJumpIsland. |
| skyJumpPopupScene | **C** | B- | The coins are a pale beige-yellow and the hill is thinner, where 065's hill is saturated orange-gold with a glow and fills the corners. The chest is pale with the lid thrown back and no shield (065: lavender chest, with the shield hanging over the front). | Warm saturated coin ramp + glow; denser hill to the corners; chest as on 065. |
| stageChestGreen | **A** | B | Matches 065's stage tile at 56 x 42 pt (colour, lid, lock plate). |  |
| stageChestBlue | **A** | B | Matches 065's stage tile at 56 x 42 pt (colour, lid, lock plate). |  |
| stageChestPink | **A** | B | Matches 065's stage tile at 56 x 42 pt (colour, lid, lock plate). |  |

### Rocket Race

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| rocketRaceBackdrop | **C** | B- | Below the header, ours is a flat lavender #6A48BA; 167 is deep indigo (#16105C at the top of the lanes to #420FAC). The chest is seen straight-on as an upright blue drum (167: 3/4 top view, gold bands, diamond clasp), sitting on a thin flat coin band instead of a pyramid hoard on a rock. The moon surface is flat. | Dark indigo lane gradient + stars; chest in 3/4 view on a rock with a pyramid hoard. |
| rocketMine | **B** | B- | Reads as the player's rocket. The nose is pointier, the body narrower at the band, and the flame smaller than 178's. |  |
| rocketOther | **B** | B- | The lower half is painted mid blue; 178's opponent rocket is white/pale down to the fins, with a blue nose and fins. | White body to the fins. |

### Leaderboard, profile, shop

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| leaderboardPodium | **A** | B | Blocks, colours, caps and hex sockets match meta-013 at game size. |  |
| trophyCup | **B** | B- | The handles are thinner loops than meta-017's full ears, and the stand is shorter. |  |
| coinPackTiny | **B** | B | Reads like meta-011's pile at 102 pt. The stacks are shorter and the coins slightly smaller and more lemon than the capture's orange-gold. The soft base shadow is cut by the frame's bottom edge (bottom-row alpha up to ~75/255), which leaves a faint hard line where the card shows it. | Fade the shadow to 0 before the frame edge (or grow the frame 3 pt down); taller stacks, warmer gold. |
| coinPackSmall | **B** | B | Reads like meta-011's pile at 102 pt. The stacks are shorter and the coins slightly smaller and more lemon than the capture's orange-gold. The soft base shadow is cut by the frame's bottom edge (bottom-row alpha up to ~75/255), which leaves a faint hard line where the card shows it. The capture's centre column rises above ours. | Fade the shadow to 0 before the frame edge (or grow the frame 3 pt down); taller stacks, warmer gold. |
| coinPackMedium | **B** | B | Reads like meta-011's pile at 102 pt. The stacks are shorter and the coins slightly smaller and more lemon than the capture's orange-gold. The soft base shadow is cut by the frame's bottom edge (bottom-row alpha up to ~75/255), which leaves a faint hard line where the card shows it. 4 pt narrower than the capture. | Fade the shadow to 0 before the frame edge (or grow the frame 3 pt down); taller stacks, warmer gold. |
| coinPackBig | **B** | B | Reads like meta-011's pile at 102 pt. The stacks are shorter and the coins slightly smaller and more lemon than the capture's orange-gold. The soft base shadow is cut by the frame's bottom edge (bottom-row alpha up to ~75/255), which leaves a faint hard line where the card shows it. | Fade the shadow to 0 before the frame edge (or grow the frame 3 pt down); taller stacks, warmer gold. |
| coinPackSuper | **B** | B | Reads like meta-011's pile at 102 pt. The stacks are shorter and the coins slightly smaller and more lemon than the capture's orange-gold. The soft base shadow is cut by the frame's bottom edge (bottom-row alpha up to ~75/255), which leaves a faint hard line where the card shows it. | Fade the shadow to 0 before the frame edge (or grow the frame 3 pt down); taller stacks, warmer gold. |
| coinPackGiant | **B** | B | Reads like meta-011's pile at 102 pt. The stacks are shorter and the coins slightly smaller and more lemon than the capture's orange-gold. The soft base shadow is cut by the frame's bottom edge (bottom-row alpha up to ~75/255), which leaves a faint hard line where the card shows it. | Fade the shadow to 0 before the frame edge (or grow the frame 3 pt down); taller stacks, warmer gold. |

### Avatars (Edit Profile set, meta-003)

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| avatarWalkie | **C** | B- | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 2: their navy kepi + wave. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarCapGlasses | **C** | B- | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 3: their worker leans into the frame. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarDetective | **C** | B- | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 4: deerstalker + trench collar; ours wears a flat newsboy cap. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarBurger | **C** | C+ | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 5: their burger is big and in the open mouth (a bite); ours is small, held in front. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarScientist | **C** | B- | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 6: plate VIOLET by the lane's decision (pink character); the orange clipboard is missing. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarParty | **C** | B | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 7. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarNotebook | **C** | B- | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 8: plate SUNNY yellow by the lane's decision (a blue worker vanished on sky blue); OK. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarBoxHead | **C** | B- | Framing: the character is ~0.7x of the phone's close-up. On meta-003 the head fills the tile width and is cropped by the frame; ours shows a small head plus the belt in the middle of the tile. Every portrait is frontal with the same open buck-tooth grin, where the phone set has 3/4 leaning poses and distinct expressions. Cell 9: their box is cropped by the frame top. | One change for the whole set: camera ~1.4x closer, eyes at ~40 % height, crop at the belt, lean/turn per cell, one expression per cell as on meta-003. |
| avatarGreen | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |
| avatarRed | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |
| avatarCap | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |
| avatarBlue | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |
| avatarPoint | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |
| avatarSpecs | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |
| avatarShades | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |
| avatarPink | **n/a** |  | Not built and not shipped: the unconfirmed Jul-build arrow-character set is replaced by the phone's portrait set (SPEC 5.12). The manifest still lists it as todo, so the director should mark it superseded. |  |

### Glossy arrows + app icon

| id | grade | lane self | note | fix |
|---|---|---|---|---|
| arrowGlossyYellow | **B** | B | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. |  |
| arrowGlossyRed | **B** | B | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The loading screen's red arrow is more orange-red. |  |
| arrowGlossyBlue | **B** | B | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. |  |
| arrowGlossyGreen | **B** | B | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The green leans lime. |  |
| arrowGlossyPurple | **B** | B | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The purple leans magenta against 026's lilac. |  |
| arrowGlossyOrange | **B** | B | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. |  |
| arrowGlossyCyan | **B** | B | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The manifest ref points at store 8's red-orange loading arrow; judged against 026's cyan. |  |
| appIcon | **B** | B | Our own composition, by design, in the same glossy family. At 60 px the arrows read thinner and the white ground emptier than the store icon (their heads are ~1.3x bigger with a plumper pillow bevel). Our flat face with an inset rim line reads more like a sticker. | Heads and shafts ~1.25x, rounder pillow bevel, keep the composition. |

## Notes for the art director (merge / manifest)
- `avatarGreen` .. `avatarPink` are still `todo` in MANIFEST.json. They are not built and not shipped (SPEC 5.12), so mark them superseded or drop them.
- The scene lane has no `art/lanes/scene.entries.json`. Its sizes and refs live in `build/ui-art/scene/scene_manifest.json` (gitignored), which this review merged. Commit an entries file, or the sizes are lost on a clean checkout.
- `arrowGlossyCyan`'s ref points at store 8's red arrow; the lane measured cyan on 026.
- `clawHeaderArt` predates `char_workerClawPair` (07:59 vs 08:50). Rebuild it before the next grading round.
- Workers on the home screen: the rig defaults are `body_open` (L) and `eyes_half` (R). The phone's rest frames (026/035) show the L worker with a closed smile, so consider `body_smile` as L's default.
