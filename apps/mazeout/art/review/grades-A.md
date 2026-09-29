# Grader A: SVG, SwiftUI and code art, plus the board sprites

2026-09-25. The machine-readable twin is `art/review/grades-A.json`, with one entry per id: grade, note, fix, sheet and the lane's self-grade. Nothing in `art/` was edited apart from this review and the proof script `art/review/tools/gradeA_proofs.py`. These are the grades that count; the lanes' self-grades appear only for comparison.

**Scope (76 graded):**
- Every svg entry with an output (39 ids).
- The board sprites: 6 tapes, 9 doors, the lock, the key, the pipe mouth and counter, and the curtain crate judged as the BOX skin.
- Every SwiftUI or code entry whose output exists somewhere: the spike renders in `build/ui-art/swiftui`, the shell lane's simulator renders in `build/s1`, and the device grab/frames in `build/device`.

48 SwiftUI/code ids have no output yet and are listed under `not_graded` in the JSON.

**Counts:** A 35 · B 30 · C 11.

**Scale:** A = ship. B = OK: the same art, and the differences only show on inspection. C = redo: different at a glance, the wrong size, colour or silhouette, or not in the original at all.

## How it was judged
- **At game size.** The @3x frame is viewed at 3 px/pt next to the phone capture at the same scale, and the proofs are viewed at 1-2 px/pt. 2x crops were used only to name a difference already visible at 1x.
- **Side-by-sides.** `manifest_sheets.py --manifest build/ui-art/lane_svg/MANIFEST.json` covers the svg lane's entries, with its corrected refs. The plain manifest covers the board sprites.
- **Composed proofs** (`art/ui/sheets/gA_*.png`). In each one, the element was erased from the capture and ours pasted at the measured ui-measure frame or lattice anchor, 1:1 unless noted:
  - HUD row: 003 and 110.
  - Home: the scene layers and character rigs at `placement_pt`, the flat mocked chrome, and our icons, next to 026. There is also a top-bar close-up.
  - Loading: `logoArrowOut` at the original logo's box, 206.8 pt at +4 deg, over the kickoff shot.
  - Paused popup, and the Pipe!/Box! unlock cards.
  - Settings and Edit Profile.
  - Profile stats.
  - Streak Race rows, and the logo flag.
  - Sky Jump, with and without the scene lane's island.
  - Claw, the Claw info and the reward-card rays.
  - Boards: L33 (5 doors, 5 locks and the key), L35 pipe, L32 tapes, and L50 BOX.
  - The app's own renders next to the phone: home, Hard/Super Hard, pause, settings and the L32 board.
- **Regenerating.** Run from `apps/mazeout`; the sheets are gitignored. It builds only PIL composites, plus one scratch WebKit render of the 10x3 box into `build/ui-art/draft`.
  ```sh
  PY=~/.venvs/mf3d/bin/python
  $PY art/review/tools/gradeA_proofs.py all
  $PY art/tools/manifest_sheets.py --manifest build/ui-art/lane_svg/MANIFEST.json <svg ids>
  $PY art/tools/manifest_sheets.py <board ids>
  ```

## Redo list (C)

| id | owner | why | fix |
|---|---|---|---|
| curtainCrate (the BOX skin) | pipeline | The phone BOX (135, 154, 174, 179) has 4 corner studs and a flat violet slab with a light top edge. Its counter sphere stays ~2.4 cells on every size. Ours has no studs and a dark side/bottom shading. Its sphere scales with min(w, h)/3, so a 10x9 box gets a huge sphere. The manifest still describes the V1 "curtain". | Rebuild as the phone BOX with a fixed sphere size and studs. Add `boxW<w>H<h>` entries for 3x3, 3x4, 4x3, 3x5, 5x3, 4x4, 10x3, 10x9 and 20x12. |
| tutorialHand | ui-art | 0.66x of V1's hand; the grey drop shadow is missing; the palm is boxy. | Frame 78 x 110, soft shadow, slimmer palm. |
| glyphMusic | ui-art | The phone Settings (meta-029) uses a WHITE glyph on a green button. Ours is cream/brown and ~0.8x, so it reads muddy. | Redo from meta-029. Add white Settings variants of sound and haptic. |
| glyphBell | ui-art | Ours is a 17 pt cream bell with no outline. meta-029's is a 23 pt white/ice-blue bell with a navy outline. | Redo from meta-029 at ~24 x 26. |
| iconPencil | ui-art | The drawing is right but the size is 0.6x: the phone disc is ~30 pt on meta-002 and meta-003. | Re-export at a 30 pt frame. |
| statFirstTryIcon | ui-art | 0.6x of meta-002's target, and flatter. | Frame ~50 x 46, thicker glossy ring. |
| statWeeklyWinsIcon | ui-art | 0.62x of meta-002's medal. | Frame ~40 x 50, wider ribbon bar. |
| iconCheckeredFlag | ui-art | Ours has small navy/white 4x4 checks on a ball-topped pole. 016's logo flags have big cream/slate 3x2 glossy checks. | Redo from 016. |
| rankBadgePlain | ui-art | Not in the original: ranks 4+ are plain outlined digits (203, meta-013). | Do not ship; draw the digits live. |
| scoreChip | ui-art | The capsule is 0.75x. The plate is one brown tint, where the phone tints it per row (blue/orange/green). | Capsule-only sprite at ~1.3x; plate as a per-row tinted SwiftUI shape. |
| settingsRoundToggle | shell | Not built. The app's Settings is a Paused-style popup with pill rows. The phone's is a full-screen page with 3 round glyph buttons, a Notifications row and Support/Terms/Privacy. | Rebuild Settings on meta-029's layout. |

## B entries worth a one-line fix
- **Size or frame changes:**
  - glyphHaptic: frame 34 x 33.
  - iconPlusGreen: 20 pt.
  - iconCoin: a 34 pt home size, plus a darker, thicker rim.
  - iconHexArrow: ink 37 x 34, not 42 x 40.
  - unlockIconCurtain: 1.09x, and follow the BOX redo.
- **unlockIconCurtain id.** `design/levels.json` unlocks call it `unlockIconBox`, while the manifest and `UIArt.swift` say `unlockIconCurtain`. One id must win, or the Box card has no icon.
- **prizeSign conflict.** `skyJumpIsland` and `skyJumpPopupScene` (scene lane) already bake a 3D PRIZE sign with a blank face, so `gA_skyjump_scene.png` shows two signs. Ship exactly one.
- **logoArrowOut.** The ARROW letters are thinner and flatter than the original's puffy letters because of the 0.70 compression and the shallow extrusion. Widen the plate instead, and deepen the extrusion.
- **Pause popup chrome.** panelFrame needs corner bumper pieces and darker side bars. panelRibbon needs a more arched lower edge. panelClose needs a thicker navy ring. toggleOnOff's track border should be lighter.

## What is A
- **The board sprites** are identical in place on L32, L33, L34, L35, L37, L38 and L44: every tape, all 9 doors, the lock, the key, and the pipe mouth and counter.
- **Board code:** boardArrow on the device grab.
- **HUD:** the hearts, the lost heart, the stopwatch and the pause button.
- **Home:** the gear, avatarDefault, the top bar, the LEVEL plate, the Play button (all 3 difficulties) and the nav bar.
- **Popups:** glyphSound in the Paused panel, unlockIconPipe, and panelCream.
- **FX:** boardTrailStar.

## Notes for other owners (not grades)
- **Tape colour on the device (engine).** On the device grab (`build/device/grab-L032-fit.png`, 08:38), the L32 tapes render paler and pinker than both the capture and our PNG composited offline. The median pink G channel is 69 on the device vs 54 on the capture and 59 in the PNG; the p90 is 122 vs 89. The PNG itself matches the capture, so check `SpriteCache` decoding and down-scaling (thumbnail path, premultiplied edges) or a stale bundle copy (`gA_app_tape_colour.png`).
- **Stale renders.** The `build/s1` renders date from 06:36-07:13. Re-grade the SwiftUI entries once the shell re-renders.
- **Not graded.** 48 SwiftUI/code ids have no output in the manifest, the app renders or the device frames. Among them are every in-level HUD chrome component except pause, the booster button, streak chips, event logos, rank rows, unlockCard and pipeTube. The JSON lists them under `not_graded`.
