export const meta = {
  name: 'matchfactory-spec',
  description: 'Write the Match Factory build specs from the research: gameplay+levels, UI tokens, motion+audio, architecture',
  phases: [ { title: 'Spec', detail: '4 spec writers in parallel' } ],
}

const ROOT = '/Users/yago/Downloads/app-factory/apps/matchfactory'
const COMMON = `
PROJECT: a 1:1 copy of "Match Factory!" (Peak Games), native iOS/Swift. The owner: "perfect 1:1 copycat … the effects, the animations, the art,
the system … you don't have to make the online features … it should be perfect and actually possible to compete with it." The repo's
app-factory rules are suspended. COPYING LINE: copy look/feel/systems/timings/layouts 1:1; every asset is ours (procedural 3D, our sounds,
open-licence fonts); name + logo behind a Brand constant (working title "Match Factory", replaced before any submission).
EVIDENCE (read what your part needs; cite it): ${ROOT}/PLAN.md; research/: levels.md, flows.md, items.md, meta.md, fail.md, boosters.md,
motion.md, sounds.md, web-research.md (+ research/shots/*.png full-res captures of the real game at 1179x2556 = 393x852 pt @3x,
research/items/ crops, research/video/ 60 fps clips, research/motion-frames/); art/PIPELINE.md, art/STYLE.md, art/out/ (3 finished items);
design/tech-spike.md (proven RealityKit engine choices + measurements). A second phone session is playing levels 14+ right now and will append
to research/*.md — use what is there when you read it.
V1 SCOPE (decided — write the spec for exactly this):
- iPhone portrait, iOS 18+, English (base) + Turkish (the captures are Turkish; use their exact Turkish wording).
- P0: levels 1-30 (1-13 reproduce the recorded levels exactly: timers, goal cards, item themes and counts; 14-30 designed in the same style from
  the item catalogue, with Hard levels as in the original); the whole in-level loop (pile, pick, tray, merge, goals, timer, hint, stars);
  4 in-level boosters (Vacuum L3, Spring L5, Fan L7, Freezer L9) and 2 pre-level boosters (Mega Firework L11, Mega Hourglass L13) with their
  unlock popups/tutorials, stock and coin prices; special pile items Firework (L17) and Sandglass (L18); lives (5, 30 min, taken at start,
  returned on win) and coins (start 100, 0 per win); every lose/continue flow (Time Is Up, Out Of Space, free first sweeper, You Will Lose,
  Level Failed, Try Again, out-of-lives); the win sequence and the home crate sequence; home with top bar, crate/Play, 5-tab pager; the shop
  (coin packs + bundles via StoreKit with a local .storekit config — no real purchases in testing); settings + pause; locked-feature toasts;
  splash/loading.
- P1: Chief's Tool streak (L19), Key Challenge (L15), Daily Bonus (L21) — offline versions.
- NOT BUILT: online features (Teams, team events, leaderboards, Factory Pass, Collection, Star Race, Mine Dash, Life Bank, chat, sign-in) — their
  tabs/buttons exist and show the original's locked/unavailable state honestly.
Write for engineers who will NEVER see the original: exact numbers (pt, hex, seconds, curves), exact strings (EN + TR), every state and
transition, and mark each fact VERIFIED (seen in captures) / INFERRED / DECISION (ours). Touch only ${ROOT}/design/ (and your scratchpad).
Do not git commit. No xcodebuild/simulators. Keep shell commands under ~4 min.
`
const OUT = {
  type: 'object',
  properties: {
    files_written: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string', description: 'what the spec covers + the key decisions, <= 500 words' },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['files_written', 'summary', 'open_questions'],
}

const SPECS = [
  { key: 'gameplay', prompt: `${COMMON}
WRITE design/SPEC-gameplay.md + design/levels.json. Cover: board/pile rules (item counts, multiples of 3, spawn, pick = top-most under the finger on
release, drag moves the highlight); tray (7 slots, insertion rule, merge, fail at 7, pink 6/7 warning); goals (cards 1-6, counts, decrement on tap,
increment when an item leaves the tray, win when all 0, fillers left over); timer (per level, pauses: tutorials/popups/pause/freezer; colour
thresholds, red flashes); stars rule (best evidence; state the rule you choose); hint (5 s idle, 4 s repeat, which triple it picks, settings toggle);
every booster (exact effect incl. edge cases: vacuum with full tray / no goals left, spring with empty tray, fan, freezer stacking; unlock level,
free first use + tutorial, stock 3, coin price to buy 3); pre-level boosters (selection UI rules, effects, stock, prices); special items firework
(destroys 3 non-goal items) and sandglass (+10 s) — how they are collected; continues (Time Is Up +60 s for 100 coins, the +120 s case, Out Of
Space clear bar 100 coins, the free first sweeper, second-offer prices), lose flow and life cost; lives (5, 30 min exactly, taken at start, back on
win, out-of-lives popup + refill 100); coins (start 100, 0 per win, all sinks and sources in scope); P1 systems (Chief's Tool, Key Challenge, Daily
Bonus) as offline designs. LEVELS: design/levels.json — a schema + levels 1-30: id, timer seconds, hard flag, goals [{item,count}], fillers
[{item,count}] (total items per level as recorded; for 1-13 copy research/levels.md exactly), unlocks/tutorials triggered, special items. Levels
14-30: design them in the original's style (themes, look-alike decoys, occluders, difficulty curve and Hard levels per web-research.md) using ONLY
item ids that exist or are being modelled (see research/items.md; art lanes are building everything from levels 1-13). Explain the curve.` },

  { key: 'ui', prompt: `${COMMON}
WRITE design/SPEC-ui.md + design/ui-tokens.json + crops in design/ui-crops/. Measure the real screens pixel-by-pixel (Python+PIL on
research/shots/*.png; pt = px/3; sample solid interiors for colours) and specify EVERY screen and component: splash + loading; home (background art
description, top bar: level/lives/coins/settings; crate + Play button; locked-feature entries; 5-tab bottom pager with icons/labels/selection);
level-start popup (hard variant purple); in-level HUD (level label, timer pill + progress bar + hourglass, pause button, goal cards incl. check/gold
M states, the board band, the 7-slot tray tiles incl. flash/pink warning, booster bar with counts/locks "Svy.N"/green "+"); every popup (booster
unlocked, tutorials with the pointing hand + dim + spotlight, pause, settings, quit confirm, Time Is Up, Out Of Space, You Will Lose, Level
Failed, out of lives, booster buy, shop, locked-feature toast); the win sequence screens (logo plate, stars plank, title, time left, Continue).
For each: geometry in pt (x, y, w, h, radius), colours/gradients (hex + stops), borders, bevels, shadows, text (font, size, weight, colour,
stroke/outline, drop shadow — the original uses a chunky rounded display font with dark outline), icons. FONT: identify the closest OFL/Google font
to the original's display and body fonts by rendering candidates (Lilita One, Luckiest Guy, Titan One, Fredoka, Baloo 2, Rubik, Nunito, etc.)
against crops; download the chosen TTFs into ${ROOT}/design/fonts/ with licences. UI ART PLAN: list every non-trivial graphic (riveted blue
plates, wooden crate, hard hat, logo, booster icons, coin, heart, star, hourglass, pointing hand, gift/chest, factory home background…) and decide
how we make each (SwiftUI vector drawing / pre-rendered from our 3D pipeline / SVG illustration rasterised) with a reference crop.` },

  { key: 'motion', prompt: `${COMMON}
WRITE design/SPEC-motion-audio.md. Consolidate research/motion.md, boosters.md, fail.md, meta.md and sounds.md into an implementation-ready
spec: for EVERY animated event (touch-down highlight, pick lift, flight, landing flash + dip, tray insertion hops, merge sequence, gap close, pink
warning pulse, goal-card tap pop / completion spin / gold M / shrink-away / slide-left, level intro (M cards flip, items rain into the box), hint
outline pulse, timer flashes + hourglass flip, every booster effect (vacuum, spring, fan tornado, freezer beam + frost frame + countdown pill), pre-
level boosters (mega firework rockets, mega hourglass +30 s count-up), special items, continue effects (sweeper robot), win sequence beat by beat,
home crate rain/squash/sink/new crate, popup in/out, button press, tab pager, particles (sparkles, fireworks, confetti, dust ring, snow/frost)):
a table row with start time, duration, property, from → to, easing (cubic-bezier or spring params), and the sound cue. Give particle specs
(count, colour, size, lifetime, velocity, gravity). AUDIO: for every sound cue an own-synthesis recipe (oscillators/noise, envelopes, pitches,
duration, loudness target) from sounds.md, plus the two music loops (home ~118 BPM A minor/C major; level ~94 BPM D/E): instrumentation,
chords, structure, length, loop points — cheerful, polished casual-game feel; and the mixing rules (music vs SFX volume, ducking, settings toggles).` },

  { key: 'architecture', prompt: `${COMMON}
WRITE design/SPEC-architecture.md. From design/tech-spike.md (proven: ARView(cameraMode: .nonAR) in UIViewRepresentable with our own touch
handling + the hidden-tap-recognizer fix; CustomMaterial outline; projection math; tween engine in the per-frame update; warm-up of materials;
velocity-threshold settle; angular damping), art/PIPELINE.md + STYLE.md (asset conventions, sidecar JSON, lighting rig, Display-P3/tone-mapping
notes) and the scope above, define: the Xcode project (xcodegen, iOS 18, SwiftUI app, bundle id com.manycode.matchfactory, team GDU77F3MXL),
module/folder layout with FILE OWNERSHIP per build agent; the pure-Swift game core (level model, tray, goals, timer, boosters, economy, lives,
persistence, deterministic RNG + tests) and its API; the RealityKit scene (camera numbers, lighting rig, floor vignette, walls, spawn, physics
params, pick/highlight, flight/tray/merge rendering, outline, particles, asset loading + caching + warm-up behind the loading screen, memory
budget); the SwiftUI shell (navigation, popups system, HUD overlay sync at ≤10 Hz, fonts), audio engine (AVAudioEngine, music + SFX buses),
haptics; test hooks (launch args to jump to any level/state, a deterministic seed, capture mode) and XCUITest strategy; performance budgets
(60/120 fps, frame-time targets, triangle and texture budgets); and a BUILD PLAN for the engineers: ordered work packages, each with owner, files,
inputs, acceptance checks — respecting that at most TWO agents compile/run simulators at once on this 16 GB Mac (simulators "MF Main"
B8F323DC-F338-4918-B370-5F6D9F48FB11 and "MF Spike" FFE58FD1-0DC6-4010-895D-AA12D0327736), and that art is still being produced (the build must
load whatever items exist in art/out/catalog.json).` },
]

phase('Spec')
const results = await parallel(SPECS.map(s => () =>
  agent(s.prompt, { label: `spec:${s.key}`, phase: 'Spec', schema: OUT }).then(r => r ? { key: s.key, ...r } : null)))
return results.filter(Boolean)
