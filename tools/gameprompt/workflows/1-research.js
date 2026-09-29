export const meta = {
  name: 'matchfactory-research',
  description: 'Phase 1 of the Match Factory copy: play the real game on the phone, web research, 3D art pipeline spike, RealityKit tech spike',
  phases: [
    { title: 'Research', detail: 'phone player (then meta explorer + video analyst), web research, art spike, tech spike' },
  ],
}

const ROOT = '/Users/yago/Downloads/app-factory/apps/matchfactory'
const PHONE = '/Users/yago/Downloads/app-factory/tools/phonedriver/phone'
const COMMON = `
PROJECT: a 1:1 copy of the mobile game "Match Factory!" by Peak Games, native iOS (Swift). The owner's brief: "a much much bigger game,
with more graphics and details, so you will have to do real artwork and actually play the game and make a perfect 1:1 copycat. very detailed
work — the effects, the animations, the art, the system. You don't have to make the online features. It should be perfect and actually
possible to compete with it. If it asks for a payment, ad watch etc. just reject it." The repo's app-factory rules (paywall, ASO, submission,
app-factory skill) are SUSPENDED for this task. Read ${ROOT}/PLAN.md first.
COPYING LINE: copy the look, feel, systems, timings and layouts 1:1, but every asset is made by us (procedural 3D models in the same style,
our own sounds, open-licence fonts) — never extract, rip or trace the original's files.
MACHINE LIMITS (hard): 16 GB RAM, ~14 GB free disk, shared by several agents. Never run more than one xcodebuild at a time; pass -jobs 4;
boot only the simulator assigned to you and shut it down at the end; keep build products inside ${ROOT}/build/<your-role>/ (gitignored)
and delete them when done. Keep every single shell command under ~4 minutes. Touch only ${ROOT}/ (and your scratchpad); never other apps.
Do not git commit. Write findings to files as you go (so nothing is lost if you are interrupted), then return the structured summary.
`
const PHONE_RULES = `
PHONE (you have EXCLUSIVE use of the owner's iPhone 15 while you run — nobody else touches it):
- Control: ${PHONE} status | shot OUT.png | tap X Y | press X Y SECONDS | swipe X1 Y1 X2 Y2 SECONDS | activate BUNDLE | launch BUNDLE | home
  (coordinates in POINTS, 393x852 portrait). Match Factory bundle id: net.peakgames.match.
- Screenshots: '${PHONE} shot F.png' gives ~1179x2556 px. To LOOK at the screen cheaply, downscale to exactly 393x852 (then pixel = point)
  with python3/PIL and Read that; use full resolution only when cropping items/UI for the catalogue.
- Video with sound (60 fps): '${PHONE} rec OUT.mov SECONDS' blocks for SECONDS — to record while acting run it in the background in the
  same command, e.g.  (${PHONE} rec ${ROOT}/research/video/x.mov 8 &) ; sleep 1.5 ; ${PHONE} tap 100 400 ; sleep 6
  Starting a recording may make iOS ask "Bir kulaklık mı bağlıyorsunuz?" (headphones?) — tap "Diğer Aygıt" (left button, ~(122,494)).
- If a command says the runner is not reachable: start it in the background (/Users/yago/Downloads/app-factory/tools/phonedriver/start-runner
  > /tmp/phonedriver-runner.log 2>&1 &), wait ~40 s, retry. If the phone is locked/asleep you cannot unlock it: write what you have and stop.
- REJECT every payment, purchase, rewarded ad, "watch ad for …", subscription and continue-for-coins offer (the owner's order). Close
  interstitial ads with their X (wait for the countdown); if an ad opens the App Store or a browser, return with '${PHONE} activate
  net.peakgames.match'. Decline notification permission, tracking (ATT: "Uygulamadan izlememesini iste"), Game Center and account/login prompts.
- The phone UI is Turkish: record the Turkish text AND an English translation.
`
const OUT = {
  type: 'object',
  properties: {
    files_written: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string', description: 'dense findings with numbers, <= 700 words' },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['files_written', 'summary', 'open_questions'],
}

const P1 = `${COMMON}${PHONE_RULES}
ROLE: PLAYER (first-time user experience). Match Factory is open on the phone at LEVEL 1 (tutorial: "Toplamak için 3 aynı öğeye dokunun").
Play the real game from level 1 as far as you can (goal: level 12, or ~120 minutes, or out of lives), and document EVERYTHING so engineers
can rebuild it 1:1 without ever seeing the game:
- How to play fast enough: take a shot, downscale, identify 3 identical items that are visible (the goal items first), tap all three in ONE
  command with ~0.35 s gaps, re-shoot. Items move after taps (physics). Timers start at 5:00 on level 1 — don't over-deliberate.
- For EVERY level write to ${ROOT}/research/levels.md: level number, timer at start, goal cards (item + count), every item type on the
  board with an approximate count, how the board looked (how full, pile height), booster/feature unlocks and their tutorial text, result,
  time left, rewards (coins, stars, chests), every popup before/after.
- Screenshots (full res) into ${ROOT}/research/shots/ named NNN-what.png for every DISTINCT screen and state: level intro, the board at
  start, tray states (1..7 items, grouping of identical items), highlighted hint outline, merge moment, goal card completion, near-fail tray,
  win screen(s), reward screens, home screen after each level, any new UI.
- Videos (60 fps) into ${ROOT}/research/video/: level 1 start (the first 8 s), a single tap-to-tray flight, a triple merge (tap 3 identical
  items while recording), a goal-card completion, the full win sequence (from the last merge until home is idle, ~12-15 s), the home screen
  idle animation, every booster/feature unlock tutorial, and at least one full level (record in 20-30 s chunks).
- ITEM CATALOGUE: ${ROOT}/research/items.md + crops in ${ROOT}/research/items/<item-name>.png (crop from full-res shots, generous margins,
  clearest views, 2-3 angles when you can) for every item type you meet — name it in English (rubber-duck, strawberry, toy-hammer, …) and
  describe shape, colours, materials (glossy/matte), size relative to others.
- ${ROOT}/research/flows.md: every screen and transition in order, all visible text (Turkish + English), buttons and what they do.
Update the files after every level (you may be interrupted). Return a dense summary.`

const P2 = (p1) => `${COMMON}${PHONE_RULES}
ROLE: META EXPLORER (the phone is yours now; the first player has finished — their summary is below and their notes are in
${ROOT}/research/levels.md, flows.md, items.md; read them first and do not duplicate their captures).
Document everything outside the level-by-level play, with full-res screenshots (${ROOT}/research/shots/meta-*.png) and short videos:
1. Home screen: every button, tab, badge, currency (coins, lives + refill timer, stars), level button, idle animations (video), background
   art. Open EVERY tab/screen reachable from home (shop — look only, never buy; settings; profile/avatar; events; chests/rewards; daily
   bonus; leaderboards/teams — these are online: just capture them). Pre-level popup (level details, pre-level boosters, Play button).
2. In-level: the pause menu (all options), each in-level booster that is unlocked (use each once if you have it; record video of its effect),
   locked-booster taps (what they say).
3. FAIL STATES (deliberately, on the current level): fill the tray with 7 non-matching items → the "out of space"/fail flow: every screen,
   every offer (reject all), the final fail/"try again" screen, lives decrement. If practical, also let a timer run out on a level (record
   the last 10 s and the out-of-time flow). Note lives count and refill timer before/after.
4. Settings: every toggle and link. Language if visible.
Write ${ROOT}/research/meta.md, ${ROOT}/research/fail.md, ${ROOT}/research/boosters.md (+ update flows.md). Leave the game on its home
screen when done.
FIRST PLAYER'S SUMMARY:
${JSON.stringify(p1)}`

const ANALYST = (p1) => `${COMMON}
ROLE: MOTION + EFFECTS ANALYST (no phone — you work from the recordings). The player captured 60 fps videos in ${ROOT}/research/video/ and
screenshots in ${ROOT}/research/shots/ (their summary below). Frame extractor: ${PHONE} frames IN.mov OUTDIR FPS [START END] (writes PNGs
named by milliseconds; use 60 fps on short windows, 10 fps to scan). Downscale frames before viewing (Read) to save context.
Measure and specify, with numbers, for the engineers:
- Tap → tray flight: duration, path (arc? straight?), easing, scale change (3D size on board vs in tray), rotation to a canonical pose,
  what happens to neighbours on the board (physics reaction), the tray slot insertion rule (grouping identical items; do others shift?
  timing of the shift), sounds (describe; timestamps).
- Triple merge: sequence and timings (slide together, squash/scale, pop, particles/sparkles/stars — colour, count, size, lifetime,
  direction), goal card update (counter decrement animation, check mark), remaining items sliding left, sound.
- Win sequence: every beat with timestamps (text, banners, confetti/particles, coins flying, stars, button appearance).
- Level intro: how items appear (drop in? fade? camera move?), timer/goal-card entrance animations.
- UI micro-animations: button press feedback, popup entrance/exit curves (scale overshoot?), idle animations.
- The camera: estimate the 3D camera angle/field of view from how items look; the board's floor, walls/edges, lighting direction,
  shadow softness, outline/rim light, colour grading.
Write ${ROOT}/research/motion.md (tables of timings + easing curves in a form engineers can type in) and save key frames in
${ROOT}/research/motion-frames/. Also extract the audio of key moments (afconvert/AVFoundation are available; no ffmpeg) and describe each
sound (pitch, length, character) in ${ROOT}/research/sounds.md — so we can synthesise our own equivalents (never copy their audio).
PLAYER'S SUMMARY:
${JSON.stringify(p1)}`

const WEB = `${COMMON}
ROLE: WEB RESEARCH (no phone). Load WebSearch/WebFetch via ToolSearch "select:WebSearch,WebFetch". Research "Match Factory!" by Peak Games
(App Store id? — find it; Google Play net.peakgames.match): release, ratings, size, engine; and the COMPLETE game design with evidence
(VERIFIED/INFERRED/UNKNOWN + sources): core rules (tray of 7? triples, goals, timer, what counts as winning/losing), all in-level boosters and
pre-level boosters (names, icons, exact effects, unlock levels, costs), economy (coins earned per level, prices, lives count, refill time,
unlimited lives offers), stars/chests/progression, level count, difficulty labels ("Hard"/"Super Hard"), special items or mechanics
introduced later (locked items, boxes, ice, conveyors, etc. — list everything with the level it appears), meta features (events, teams,
leaderboards, daily rewards, piggy bank, album/collections…) and which are online-only, the full item catalogue as far as reviews/wikis/
videos show, level design patterns, tutorials. Sources: App Store page + "What's New" history, Play page, Peak's site, fandom/wikis, level
guides, Reddit, reviews (App Store RSS JSON), YouTube titles/descriptions/storyboards, app-intelligence sites. Save useful images to
${ROOT}/research/web/. Write ${ROOT}/research/web-research.md with a Sources list.`

const ART = `${COMMON}
ROLE: 3D ART PIPELINE SPIKE (no phone, no simulator needed except optionally for previews). Python 3D toolkit: ~/.venvs/mf3d/bin/python
(numpy, scipy, scikit-image marching cubes, trimesh, fast-simplification, usd-core pxr). Build our own asset pipeline and prove it on the first
3 items of level 1: RUBBER DUCK, STRAWBERRY, TOY HAMMER (white/cream head with red star, blue caps, red handle end — see references).
References: full-res frames in ${ROOT}/research/video/test-frames/ (level 1 board) and, as the player captures them, ${ROOT}/research/items/
and research/shots/. Style of the original: glossy, saturated, chunky cartoon toys with soft rounded forms, clear silhouettes, subtle
specular highlights, rendered on a dark slate floor under soft top lighting.
Build in ${ROOT}/art/pipeline/:
1. sdf.py — signed-distance modelling: primitives (sphere, ellipsoid, capsule, rounded box, torus, cylinder/rounded cylinder, cone,
   extruded 2D shapes like a star), smooth union/subtraction/intersection, transforms; each item = named PARTS, each part its own SDF + material.
2. mesher — marching cubes per part at adequate resolution, smooth normals, quadric decimation to a budget (~1.5-4k triangles per item
   total), clean manifold output, consistent scale (define 1 unit = board cell; items roughly 0.8-1.2 units long like the original's
   relative sizes), origin at the centre of mass, canonical "upright" orientation for the tray.
3. usd writer — USDZ with one mesh per part and UsdPreviewSurface materials (baseColor, roughness, metallic, clearcoat,
   clearcoatRoughness, emissive if needed), validated to load in RealityKit/SceneKit.
4. preview renderer — a small Swift macOS CLI (SceneKit offscreen SCNRenderer, or RealityKit's RealityRenderer on macOS 15) that renders
   any USDZ with lighting like the game's (dark slate background, soft key light from above-front, fill, subtle rim) at a 3/4 top view
   → PNG; plus a contact sheet that puts our render next to the reference crop.
Model the 3 items, LOOK at the side-by-side comparisons (Read) and iterate until a player would not notice the difference in style at
game size. Write ${ROOT}/art/PIPELINE.md (how to add an item: the recipe format, commands, budgets) and ${ROOT}/art/STYLE.md (proportions,
saturation, gloss, edge softness, colour palette extracted from references). Outputs: ${ROOT}/art/out/<item>.usdz + previews.`

const TECH = `${COMMON}
ROLE: ENGINE TECH SPIKE. Simulator "MF Spike" UDID FFE58FD1-0DC6-4010-895D-AA12D0327736 only. Build a throwaway prototype in ${ROOT}/build/spike/
(xcodegen at /Users/yago/.local/bin/xcodegen; iOS 18 deployment; SwiftUI app) that proves the core of Match Factory in RealityKit:
- A board area between a top HUD band and a bottom tray band (see ${ROOT}/research/video/test-frames/ for the original's layout: dark slate
  floor, items piled in the middle, 7-slot tray near the bottom, booster bar under it). Perspective camera looking down at a steep angle;
  match the original's apparent angle/scale.
- Spawn 60 / 100 / 150 physics items (use ${ROOT}/art/out/*.usdz if the art agent has produced any, otherwise simple rounded primitives),
  drop them into an invisible walled container and let them settle into a pile (dynamic bodies with convex collision shapes; sleep when at rest).
- Tap: hit test the topmost item under the finger (RealityView + SpatialTapGesture targetedToAnyEntity, or ARView(.nonAR) entity(at:) — try
  both, pick the more reliable/performant, justify). The tapped item leaves physics and flies along an arc into the right tray slot,
  shrinking and rotating to an upright pose; neighbours react physically.
- Tray logic: 7 slots; a new item is inserted right after identical items already in the tray (others shift right, animated); 3 identical
  → merge animation (slide together, squash, pop, sparkle particles via ParticleEmitterComponent) → removed, the rest slide left; 7 filled
  without a triple = fail.
- A yellow outline highlight for hinted items (inverted-hull duplicate with front-face culling, or another approach that works in RealityKit
  on iOS) — prove it.
- Measure: frame time/FPS in the simulator at 60/100/150 items (CADisplayLink or RealityKit stats), physics settle time, tap latency. Note
  what needs a real device.
Write ${ROOT}/design/tech-spike.md: the chosen APIs with exact code that worked, measurements, pitfalls, and a recommended architecture for the
real game (scene graph, layers, how HUD/tray/boosters mix SwiftUI and RealityKit). Keep screenshots of the prototype in ${ROOT}/design/spike-shots/.
Shut the simulator down at the end.`

phase('Research')
const [phoneTrack, web, art, tech] = await parallel([
  async () => {
    const p1 = await agent(P1, { label: 'phone:player', phase: 'Research', schema: OUT })
    const p1s = p1 || { summary: 'player agent failed — read research/levels.md, flows.md, items.md for whatever was captured', files_written: [], open_questions: [] }
    const [p2, analyst] = await parallel([
      () => agent(P2(p1s), { label: 'phone:meta', phase: 'Research', schema: OUT }),
      () => agent(ANALYST(p1s), { label: 'analyst:motion', phase: 'Research', schema: OUT }),
    ])
    return { p1, p2, analyst }
  },
  () => agent(WEB, { label: 'web', phase: 'Research', schema: OUT }),
  () => agent(ART, { label: 'art:spike', phase: 'Research', schema: OUT }),
  () => agent(TECH, { label: 'tech:spike', phase: 'Research', schema: OUT }),
])
return { phoneTrack, web, art, tech }
