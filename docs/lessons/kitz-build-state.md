---
name: kitz-build-state
description: Kitz (Game For Cats) — SpriteKit prey-hunt game; aggressive monetization; competitor-matched real art
metadata: 
  node_type: memory
  type: project
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

Kitz = "Game For Cats - Kitz", com.manycode.kitz, ASC app 6796774630, accent #FFD23F (cat-visible yellow). ENTERTAINMENT category. SpriteKit game, on-device, no server/ads/tracking.

**Concept (grounded in competitor research — Meow 4.2★/1.1K, Games for Cats):** prey-hunt game FOR the cat. 4 hunts, only Mouse free; Laser/Firefly/Fish are Pro. Prey has FLEE-AI (bolts from a paw, freezes, creeps back). Cat Mode = full-screen, no cat-tappable chrome, exit via press-hold. **Aggressive monetization per user:** free Mouse interrupts with a dismissable paywall every 2 min (GameView 1Hz timer, elapsed%120); the 3 other hunts + ALL tuning (speed/color/count) are Pro; every paywall dismissable (2s-delay X — the one hard Apple rule).

**Art (user demanded REAL art, not SF Symbols/code — twice angry):** studied 5+ competitor App Store screenshots (via `itunes.apple.com/lookup?id=` → screenshotUrls, downloaded + viewed). Key finding: top apps use BRIGHT THEMATIC backgrounds (blue water for fish, warm floor for mice) + realistic-COLORED prey (grey mice, orange goldfish), NOT neon-on-black. Pivoted to that. Prey art = SVG illustrations generated via multi-agent Workflow, rasterized with `scripts/svg2png.swift` (WebKit, no deps), → PNG imagesets prey_{mouse,laser,firefly,fish}. Themed bg per hunt bg_{mouse=floor,fish=water,firefly=night,laser=carpet} via tools/make_backgrounds.py (PIL). See [[svg-art-pipeline]]. Home = dark branded menu with real prey-art hero + tokens + cat mascot; games = themed bright fields. Icon: tools/make_icon.py (glowing paw batting cyan prey, no Gemini).

**Files:** Prey.swift (Hunt lib), HuntScene.swift (SpriteKit: flee-AI, catch, themed bg sprite), PreyNode.swift (sprite + brain; glow halo only for firefly/laser), GameView.swift (Cat Mode paw-lock + 2-min paywall + press-hold exit — game.exit needs .accessibilityAddTraits(.isButton)), HomeView.swift (game menu), GameStore.swift (catches/streak + Pro tuning), TuningSheet, sounds via tools/make_sounds.py (pure-python WAV).

**SUBMITTED build 2, 2026-08-01** (reviewSubmission 283cdc68): version 1.0.0 + weekly + yearly all WAITING_FOR_REVIEW.

**MEOW-STYLE REARCHITECTURE (build 2, after user "look at the other apps and make it 100% like that" + chose Meow):** killed the menu hub entirely. App now opens STRAIGHT into the full-screen hunt; the ONLY chrome is a small home button top-right (plain tap) that opens a simple hunt grid (ModePicker) with themed tile previews + Pro locks. No HUD, no score pill in-game. Settings (incl. Pro tuning) lives behind the grid. Prey SIZE is now a 4th Pro knob (0.6–1.8×, scales sprite + halo + catch radius); speed/size/count/color apply live via applyTuning().

**BUGS BURNED (build 2):** (1) SpriteView root scene had zero size at present → prey never spawned; fix = create HuntScene with `s.size = UIScreen.main.bounds.size` up front AND spawn on the first `update()` frame where `size.width > 40` (didMove/didChangeSize were unreliable). Recreating the scene via `.id()` double-presents and drops prey — reconfigure ONE persistent scene instead (`reload()`). (2) Locked-tile paywall never opened: the tile Button's frame was **180×388** vs the 150pt tile because of a greedy `scaledToFill` bg + `maxHeight:.infinity` child → taps landed outside; fix = `Color.clear` bounded box + overlays. See [[swiftui-greedy-scaledtofill-gotcha]] (now documents the tap-target variant + the NSLog frame-dump diagnosis). (3) Settings sheet raced the grid-overlay dismissal → delay 0.35s before presenting + retry in the test. (4) `errSecInternalComponent` on export → re-run `scripts/signing_setup.py --slug kitz` (partition-list), then release succeeds.

Faz 0-11 done: RC✓ create_app✓ asc_iap✓(175 regions) signing✓ screenshots✓ metadata✓(keywords removed per [[keywords-are-user-owned]], set via PATCH; description had to be PATCHed too — an empty description.txt blocks review with ENTITY_ERROR.ATTRIBUTE.REQUIRED) bug_check✓(5/5 both modes) submit✓. See [[simctl-launch-args-gotcha]] (kitz captures very flaky with multi-arg -ShowScreen; uninstall+install per shot, still ~50% drop rate).
