export const meta = {
  name: 'matchfactory-build',
  description: 'Build the Match Factory copy per SPEC-architecture §12: scaffold, then board/shell slots + core/content/audio/UI-art, game glue, verification',
  phases: [
    { title: 'Scaffold', detail: 'WP0 lead: project, contracts, stubs' },
    { title: 'Foundations', detail: 'B1 board, S1 shell, C1-C3 core, L1 content, A1-A3 audio, UI art' },
    { title: 'Features', detail: 'B2 choreography, S2 HUD/popups/win, C4 meta, L2 levels 14-30' },
    { title: 'Game', detail: 'G1 integration, S3 home/shop/P1, G2 boosters/specials/P1 glue' },
    { title: 'Verify', detail: 'V1 suites, V3 perf+soak, V2 side-by-side fidelity' },
  ],
}

const ROOT = '/Users/yago/Downloads/app-factory/apps/matchfactory'
const A = 'slot A = simulator "MF Spike" FFE58FD1-0DC6-4010-895D-AA12D0327736'
const B = 'slot B = simulator "MF Main" B8F323DC-F338-4918-B370-5F6D9F48FB11'
const COMMON = `
You are an engineer on the Match Factory copy. READ FIRST, in full: ${ROOT}/SPEC.md (the master prompt: the copying line, which spec wins,
the orchestrator's reconciliations, machine rules). Then read design/SPEC-architecture.md §12 (build plan) and every section your work package
lists, plus the content specs/research it names. Your work package's files, inputs and ACCEPTANCE are defined in SPEC-architecture §12.2 —
meet every acceptance item for real and report the evidence (paths under ${ROOT}/build/ or your scratchpad, never design/).
Memory is tight (an art workflow runs in parallel): before any xcodebuild or simulator boot, check 'sysctl vm.swapusage' and 'memory_pressure -Q';
if free swap < 400 MB or pressure is critical, wait in 2-minute steps (max 10 min) before proceeding. One xcodebuild at a time, -jobs 4 -quiet;
swift build -j 2. Shut your simulator down when you finish. Keep every command under ~4 minutes. Do not git commit. Never touch other apps.
Other engineers work in parallel on other files: edit ONLY files your package owns (SPEC-architecture §3); if you need a change in someone
else's file, work around it and put the request in your report.
`
const RESULT = {
  type: 'object',
  properties: {
    wp: { type: 'string' },
    status: { type: 'string', enum: ['done', 'partial', 'blocked'] },
    acceptance: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, met: { type: 'boolean' }, evidence: { type: 'string' } }, required: ['item', 'met', 'evidence'] } },
    files: { type: 'array', items: { type: 'string' } },
    requests_for_others: { type: 'array', items: { type: 'string' } },
    open_issues: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['wp', 'status', 'acceptance', 'files', 'requests_for_others', 'open_issues', 'summary'],
}
const brief = (r) => r ? `[${r.wp} ${r.status}] ${r.summary}\nREQUESTS: ${JSON.stringify(r.requests_for_others)}\nOPEN: ${JSON.stringify(r.open_issues)}` : '(that package failed — check the files on disk)'
const run = (wp, extra, opts) => agent(`${COMMON}\nYOUR WORK PACKAGE: ${wp}.\n${extra}`, { schema: RESULT, ...opts })

phase('Scaffold')
const wp0 = await run('WP0 (LEAD) — scaffold and contracts', `You use ${B}. You are the only one who writes project.yml, tools/*.sh and the ◆ contract files; freeze them when done (later changes only via the orchestrator). Apply the SPEC.md reconciliations in the contracts (fonts, audio buses, spawn.goalBias/bigLast, catalog loader tolerant of the real art/out/catalog.json).`, { label: 'WP0:lead', phase: 'Scaffold' })
const ctx0 = `WP0 REPORT:\n${brief(wp0)}`

// No-simulator lanes
const coreP = (async () => {
  const c1 = await run('C1 (CORE) — geometry, motion, RNG, visibility', `No simulator. ${ctx0}`, { label: 'C1:core', phase: 'Foundations' })
  const c2 = await run('C2 (CORE) — rules and session', `No simulator. ${ctx0}\nC1: ${brief(c1)}`, { label: 'C2:core', phase: 'Foundations' })
  const c3 = await run('C3 (CORE) — economy and persistence', `No simulator. ${ctx0}\nC2: ${brief(c2)}`, { label: 'C3:core', phase: 'Foundations' })
  return { c1, c2, c3 }
})()
const audioP = (async () => {
  const a1 = await run('A1 (AUDIO) — sounds and music', `No simulator. ${ctx0}\nSound design + music: design/SPEC-motion-audio.md §19-§22 (authoritative for audio) and research/sounds.md. Make them sound polished and pleasant — this is a top-grossing casual game's feel, not placeholder bleeps.`, { label: 'A1:audio', phase: 'Foundations' })
  const a2 = await run('A2 (AUDIO) — audio engine and haptics code', `No simulator. ${ctx0}\nA1: ${brief(a1)}`, { label: 'A2:audio', phase: 'Foundations' })
  return { a1, a2 }
})()
const uiArtP = run('UI-ART — our 2D/3D-rendered UI art for SPEC-ui A-01…A-90', `No simulator. ${ctx0}
Produce every raster graphic SPEC-ui's art plan marks as pre-rendered (3D renders from our art pipeline: booster icons vacuum/spring/fan/icegun,
mega firework, mega hourglass, coin, heart, star, crate, hard hat, gift/chest, pointing hand if 3D; SVG illustrations: logo plate, home factory
background, splash/loading art, badges…) as art/ui/out/<UIArt case>@3x.png (names = the UIArt enum in the contracts), matching the references in
design/ui-crops/ in style and size. You may add recipes under art/pipeline/items/ui_*.py and SVGs under art/ui/src/ (rasterise with WebKit or
PIL; see memory svg-art-pipeline: /Users/yago/Downloads/app-factory/scripts/svg2png.swift). Do NOT edit shared pipeline files (another workflow's
lanes use them). Log per asset in art/ui/UI-ART.md with a side-by-side sheet vs the reference crop. Prioritise what the HUD, popups and home show most.`, { label: 'UI-ART', phase: 'Foundations' })
const l1P = coreP.then(core => run('L1 (CONTENT) — levels 1-13, tutorials, strings', `No simulator. ${ctx0}\nC2: ${brief(core.c2)}\ndesign/levels.json is the source of truth (SPEC.md reconciliation 4): generate the per-level files from it.`, { label: 'L1:content', phase: 'Foundations' }))

// Slot B: shell (+ audio integration window)
const slotB = (async () => {
  const s1 = await run('S1 (SHELL) — shell foundation', `You use ${B}. ${ctx0}`, { label: 'S1:shell', phase: 'Foundations' })
  const audio = await audioP
  const a3 = await run('A3 (AUDIO) — audio integration (a short slot-B window)', `You use ${B}. ${ctx0}\nA1: ${brief(audio.a1)}\nA2: ${brief(audio.a2)}\nS1: ${brief(s1)}`, { label: 'A3:audio', phase: 'Foundations' })
  const s2 = await run('S2 (SHELL) — HUD, game popups, win', `You use ${B}. ${ctx0}\nS1: ${brief(s1)}\nA3: ${brief(a3)}`, { label: 'S2:shell', phase: 'Features' })
  return { s1, a3, s2 }
})()

// Slot A: board
const slotA1 = (async () => {
  const b1 = await run('B1 (BOARD) — board foundation and risk checks', `You use ${A}. ${ctx0}\nC1 is being written in parallel by CORE; start with the host + R1/R5 and switch to CameraRig/Lanes/Visibility when MFCore C1 is green (swift test).`, { label: 'B1:board', phase: 'Foundations' })
  const b2 = await run('B2 (BOARD) — choreography and effects', `You use ${A}. ${ctx0}\nB1: ${brief(b1)}`, { label: 'B2:board', phase: 'Features' })
  return { b1, b2 }
})()

const core = await coreP
const [c4, l2] = await parallel([
  () => run('C4 (CORE) — P1 meta rules', `No simulator. ${ctx0}\nC3: ${brief(core.c3)}`, { label: 'C4:core', phase: 'Features' }),
  () => l1P.then(l1 => run('L2 (CONTENT) — levels 14-30', `No simulator. ${ctx0}\nL1: ${brief(l1)}\nAlso re-read research/levels.md: phone session 2 has been recording real levels 14+ — prefer the real data where it exists.`, { label: 'L2:content', phase: 'Features' })),
])
const l1 = await l1P
const [boardR, shellR] = await Promise.all([slotA1, slotB])
const uiArt = await uiArtP

phase('Game')
const featureCtx = `${ctx0}\nC1-C3: ${brief(core.c3)}\nC4: ${brief(c4)}\nL1: ${brief(l1)}\nL2: ${brief(l2)}\nB1: ${brief(boardR.b1)}\nB2: ${brief(boardR.b2)}\nS1: ${brief(shellR.s1)}\nS2: ${brief(shellR.s2)}\nA3: ${brief(shellR.a3)}\nUI-ART: ${brief(uiArt)}`
const [g1, s3] = await parallel([
  () => run('G1 (GAME) — game integration', `You use ${A}. ${featureCtx}`, { label: 'G1:game', phase: 'Game' }),
  () => run('S3 (SHELL) — home sequences, shop, P1 screens', `You use ${B}. ${featureCtx}`, { label: 'S3:shell', phase: 'Game' }),
])
const [g2, v1] = await parallel([
  () => run('G2 (GAME) — boosters, tutorials, specials, P1 glue', `You use ${A}. ${featureCtx}\nG1: ${brief(g1)}\nS3: ${brief(s3)}`, { label: 'G2:game', phase: 'Game' }),
  () => run('V1 (VERIFY) — test suites', `You use ${B}. ${featureCtx}\nG1: ${brief(g1)}\nS3: ${brief(s3)}\nG2 runs in parallel on slot A; write/run the suites for what exists, re-run at the end.`, { label: 'V1:verify', phase: 'Verify' }),
])

phase('Verify')
const vctx = `${featureCtx}\nG1: ${brief(g1)}\nG2: ${brief(g2)}\nS3: ${brief(s3)}\nV1: ${brief(v1)}`
const [v3, v2] = await parallel([
  () => run('V3 (VERIFY) — performance and soak', `You use ${A}. ${vctx}`, { label: 'V3:perf', phase: 'Verify' }),
  () => run('V2 (VERIFY) — side-by-side fidelity', `You use ${B}. ${vctx}\nProduce the capture list and the per-region comparison; write every finding with its owner into ${ROOT}/build/compare/FINDINGS.md (the orchestrator runs the fix loops next).`, { label: 'V2:fidelity', phase: 'Verify' }),
])
return { wp0, core, c4, l1, l2, audio: await audioP, uiArt, board: boardR, shell: shellR, g1, s3, g2, v1, v3, v2 }
