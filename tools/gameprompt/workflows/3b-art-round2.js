export const meta = {
  name: 'matchfactory-art-r2',
  description: 'Art round 2: items for levels 14-19 + special items + fixes of the weakest level 1-13 items, then art-director review',
  phases: [ { title: 'Items', detail: '3 modelling lanes' }, { title: 'Review', detail: 'art director' } ],
}
const ROOT = '/Users/yago/Downloads/app-factory/apps/matchfactory'
const COMMON = `
PROJECT: a 1:1 copy of "Match Factory!" (Peak Games) for iOS. Read ${ROOT}/SPEC.md (copying line: our own procedural models in the same
style — never extract/trace the original's files; captures are only looked at). Art pipeline: ${ROOT}/art/PIPELINE.md (lane workflow,
recipe format, variants, materials, tray pose, outline shells, catalogue), ${ROOT}/art/STYLE.md, ${ROOT}/art/REVIEW.md (the art director's
bar and lessons from round 1). The 83 round-1 items in art/pipeline/items/*.py are the quality bar.
MACHINE: a build workflow is compiling in parallel (tight memory/disk): MF_WORKERS=2, no xcodebuild, no simulators, commands < 4 min,
check 'df -h /' — if < 3 GB free, delete your own previews first and report. Touch only ${ROOT}/art/ (and design/levels.json only where told).
Do not git commit. Log per item in art/lanes/<lane>.md.
ITEM IDS: use snake_case of the research/items.md names (e.g. corn-can -> corn_can). Before naming, grep ${ROOT}/App/Resources/Levels/*.json
and design/levels.json for ids that already reference these items and use exactly those ids if present.
`
const OUT = { type: 'object', properties: { items_done: { type: 'array', items: { type: 'string' } }, items_weak: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } }, required: ['items_done', 'items_weak', 'summary'] }
const LANE = (name, items) => agent(`${COMMON}
ROLE: ITEM MODELLER, round-2 lane "${name}". Model (new recipe files only; shared pipeline files are frozen — requests go to art/requests-${name}.md):
${items}
References: research/items.md (session-2 rows at the end), crops in research/items/, shots 200-322 in research/shots/ for context and relative
sizes (motion.md §17 and levels.md L14-L19 notes). For each item: recipe -> build -> 'preview.py <id> --sheet' next to the crops -> LOOK ->
iterate to the round-1 A/B bar. Use VARIANTS for colourways that share geometry.`, { label: `art2:${name}`, phase: 'Items', schema: OUT })

phase('Items')
const lanes = await parallel([
  () => LANE('cans-fruit-fixes', `- L14: tin cans corn/tomato/broccoli (one can, 3 label variants), corn_cob, watermelon_slice, sandwich_sub (tomato exists)
- L18: grapes_green, kiwi, chili_red (colour variant of the existing chili_green recipe — add it as a VARIANT in a NEW file if the recipe
  file isn't yours: e.g. items/chili_red.py importing chili_green's build), apple_green (exists as green_apple? check catalog; alias if equal)
- FIXES from art/REVIEW.md: fries (lower carton ~0.75x, mostly red with narrow pale stripes), red_robot (chunkier round red body, darker grey
  limbs), bowling-ball swirl (larger-scale glossy ribbons). You may edit those three recipe files.`),
  () => LANE('dolls-school', `- L15: fashion_doll_yellow + fashion_doll_blue (variants), gift_pink_hearts (a variant of the existing gift box — new file importing it),
  notebook_pink_dots, roller_skate, swirl_lollipop, ice_lolly_pink, milkshake_pink
- L16: backpack_blue, skateboard, rope_ring_green, stacking_rings, play_dough_tub, ruler_orange`),
  () => LANE('balloons-sports-specials', `- L17: hot_air_balloon in 4 colours (variants; see crops/levels.md for colours), balloon_purple_dots, balloon_smiley,
  balloon_pink_round (check whether these share geometry with the existing cloud_balloon)
- L19: tennis_racket_red, table_tennis_paddle, cricket_bat, baseball_bat + baseball_bat_brown (decoy variant), pool_cue, pool/billiard balls
  (the "sports balls" fillers — identify the exact set from shots ~300-322; numbered balls as variants)
- SPECIAL pile items: firework (L17, the rocket item), sandglass (L18, +10 s hourglass item), key (L15 Key Challenge pickup) — check
  research/boosters.md / levels.md / motion.md §17 for how they look on the board.`),
])

phase('Review')
const review = await agent(`${COMMON}
ROLE: ART DIRECTOR, round 2. Review every new/changed item from the lanes (reports below; logs in art/lanes/*.md) exactly like round 1
(art/REVIEW.md method: contact sheets vs crops, mock boards per level 14-19, grades A/B/C), fix the worst yourself, rebuild, and append a
"Round 2" section to art/REVIEW.md. Then produce art/ID-MAP.md: for levels 14-19 as recorded in research/levels.md, the goal/filler item ids
that now exist in art/out/catalog.json, so the content team can update design/levels.json (do not edit it yourself).
LANE REPORTS: ${JSON.stringify(lanes.filter(Boolean).map(l => l.summary))}`, { label: 'art2:director', phase: 'Review', schema: OUT })
return { lanes, review }
