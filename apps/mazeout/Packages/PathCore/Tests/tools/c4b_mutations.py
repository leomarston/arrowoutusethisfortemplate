#!/usr/bin/env python3
"""c4b_mutations.py — mutation checks for the content recast's core port (C4b: corners, slots, template timers, the
door-before-pipe rule, the validator's recast rules). GAMEPROMPT §8.3 / SPEC-architecture §4.17: every one must be CAUGHT.

Each mutation edits ONE PathCore source line, rebuilds, runs the suites that pin the port (GeneratorTests,
ValidatorTests, SolverTests, LevelLibraryTests, RulesTests, BotReplayTests) and restores the file. CAUGHT = at least one
test fails (or the build fails / the suite hangs); MISSED = all pass.

Run it on a SCRATCH COPY of the package placed two levels under apps/mazeout (the test helpers find apps/mazeout from
#filePath: C2Fixtures.appRoot = Tests/../../..), e.g.
  rsync -a --exclude .build Packages/PathCore/ build/c4b-pkg/ && python3 Packages/PathCore/Tests/tools/c4b_mutations.py build/c4b-pkg
  [--only N]
"""
import os
import subprocess
import sys

PKG = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else
                      os.path.join(os.path.dirname(__file__), '..', '..'))
ONLY = [int(x) for x in sys.argv[sys.argv.index('--only') + 1].split(',')] if '--only' in sys.argv else None
SRC = os.path.join(PKG, 'Sources', 'ArrowEscape')
SUITES = 'GeneratorTests|ValidatorTests|SolverTests|LevelLibraryTests|RulesTests|BotReplayTests'

G, V, C, R = 'Content/Generator.swift', 'Content/Validator.swift', 'Content/ContentRules.swift', 'Rules/RayWalk.swift'
MUTATIONS = [
    # corner_layout
    ('corner_layout: a second side OPPOSITE the first is allowed', G,
     'if let first = sides.first, oppositeSide[side] == first { continue }',
     'if let first = sides.first, oppositeSide[side] == first, false { continue }'),
    ('corner_layout: a side line keeps its two end cells', G,
     'if H - 1 > 1 { for r in 1..<(H - 1) { line.append(Cell(x, r)) } }',
     'if H - 1 > 1 { for r in 0..<H { line.append(Cell(x, r)) } }'),
    ('corner_layout: a line with a used cell is not skipped', G,
     'if line.count < 3 || line.contains(where: { used.contains($0) || margin.contains($0) }) { continue }',
     'if line.count < 3 { continue }'),
    ('corner_layout: a repeated pick is kept', G,
     'if !picks.contains(i) { picks.append(i) }',
     'picks.append(i)'),
    ('corner_layout: corners placed in draw order, not sorted along the line', G,
     'for i in picks.sorted() {',
     'for i in picks {'),
    ('corner_layout: two sides with p 0.6 (inverted)', G,
     'let nSides = rng.chance(0.6) ? 1 : 2',
     'let nSides = rng.chance(0.6) ? 2 : 1'),
    ('corner_layout: every corner takes the first facing (the draw still made)', G,
     'corners.append((line[i], facings[try rng.below(2)]))',
     'corners.append((line[i], facings[0 * (try rng.below(2))]))'),
    # the plan
    ('plan: corners laid out FIRST instead of last', G,
     'let order = ["door", "elevator", "box", "pipe", "tape", "corner"]',
     'let order = ["corner", "door", "elevator", "box", "pipe", "tape"]'),
    ('plan: the corner margin line is not reserved (snakes tiled onto it)', G,
     'plan.used.formUnion(margin)',
     '_ = margin'),
    # the peel's rays
    ('peel ray: a corner never blocks (a non-accepting side goes straight on)', G,
     'guard let nd = ContentRules.cornerTurn(t, d), hops < ContentRules.maxHops else { return (false, passages) }',
     'guard let nd = ContentRules.cornerTurn(t, d) ?? Optional(d), hops < ContentRules.maxHops else { return (false, passages) }'),
    ('peel ray: the corner hop guard is 1 instead of the shared 16', G,
     'guard let nd = ContentRules.cornerTurn(t, d), hops < ContentRules.maxHops else { return (false, passages) }',
     'guard let nd = ContentRules.cornerTurn(t, d), hops < 1 else { return (false, passages) }'),
    ('peel split: the split test\'s ray ignores corners', G,
     'guard let nd = ContentRules.cornerTurn(t, d), hops < ContentRules.maxHops else { return false }',
     'guard let nd = ContentRules.cornerTurn(t, d) ?? Optional(d), hops < ContentRules.maxHops else { return false }'),
    # assembly, info, targets, timers
    ('assemble: corners emitted without their turn', G,
     'obst.append(RawObstacle(id: "x\\(i)", kind: .corner, cells: [x.cell], turn: x.turn))',
     'obst.append(RawObstacle(id: "x\\(i)", kind: .corner, cells: [x.cell], turn: nil))'),
    ('info: notes.corner_sides dropped', G,
     'let sides = plan.cornerSides.flatMap { $0.isEmpty ? nil : $0 }',
     'let sides: [String]? = nil'),
    ('target: the decade slot ignores curve.slots (3)', G,
     'let slot = Silhouettes.floorMod(Silhouettes.floorDiv(n, 10), curve.slots)',
     'let slot = Silhouettes.floorMod(Silhouettes.floorDiv(n, 10), 3)'),
    ('timer: timers.fromTemplate ignored', G,
     'if t.fromTemplate, let tt = templateTimer { return tt }',
     'if false, t.fromTemplate, let tt = templateTimer { return tt }'),
    # the rules: a locked door first, corner hops shared
    ('game rules (C2): the door-before-pipe/corner lookup is gone', R,
     'if obs[k].kind != .door, let more = extraObs[qi], let dk = more.first(where: { obs[Int($0)].kind == .door }) {',
     'if false, obs[k].kind != .door, let more = extraObs[qi], let dk = more.first(where: { obs[Int($0)].kind == .door }) {'),
    ('game rules (C2): corner turns are not counted by the hop guard', R,
     'guard let t = o.turn, let nd = ObstacleRT.cornerTurn(t, d), hops < rules.pipe.maxHops else {',
     'guard let t = o.turn, let nd = ObstacleRT.cornerTurn(t, d) else {'),
    ('content rules (arrowcore mirror): the locked-door check before the pipe is gone', C,
     'if dk0 >= 0 && !doorOpen[dk0] { return (.obstacle(dk0), passages) }',
     'if false && dk0 >= 0 && !doorOpen[dk0] { return (.obstacle(dk0), passages) }'),
    # the validator
    ('validator: an obstacle under a door overlaps it again', V,
     'if let h = hiderCells[c], under[id] != h {',
     'if let h = hiderCells[c] {'),
    ('validator: a door\'s poking hidden arrow is an error again', V,
     'if k != .door { E(.obstacle, "\\(k.rawValue) \\(id.raw): hidden arrow \\(aid.raw) sticks out") }',
     'if true { E(.obstacle, "\\(k.rawValue) \\(id.raw): hidden arrow \\(aid.raw) sticks out") }'),
    ('validator: the stub\'s ray check is gone', V,
     'if !hit.isEmpty {',
     'if false && !hit.isEmpty {'),
    ('validator: the ray-loop check is gone', V,
     'if w.passages.count + w.trace.corners >= ContentRules.maxHops {',
     'if false && w.passages.count + w.trace.corners >= ContentRules.maxHops {'),
    ('validator: the repeat key keeps the board\'s offset', V,
     'guard let x0 = all.map(\\.c).min(), let y0 = all.map(\\.r).min() else { return [] }',
     'guard !all.isEmpty else { return [] }; let x0 = 0, y0 = 0'),
]


def run(cmd, timeout=None):
    """Own process group, so a hung xctest dies with it (a hanging mutant is CAUGHT)."""
    p = subprocess.Popen(cmd, cwd=PKG, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, 9)
        # B0 2026-09-28: `swift test` runs xctest OUTSIDE this process group, so a hung mutant's xctest survived the killpg
        # as an orphan (ppid 1) and grew to 10 GB until the orchestrator killed it (build/blocked.md 05:26). Kill whatever
        # still runs from this package copy's build folder (run the script on a SCRATCH copy, never on the shared package).
        subprocess.run(['pkill', '-9', '-f', os.path.join(PKG, '.build') + '/'])
        out, _ = p.communicate()
        return subprocess.CompletedProcess(cmd, 124, out + '\nTIMEOUT', '')
    return subprocess.CompletedProcess(cmd, p.returncode, out, '')


def main():
    rows = []
    for k, (name, rel, old, new) in enumerate(MUTATIONS, 1):
        if ONLY and k not in ONLY:
            continue
        path = os.path.join(SRC, rel)
        text = open(path).read()
        if text.count(old) != 1:
            print('SKIP %d %s: anchor found %d times' % (k, name, text.count(old)), flush=True)
            rows.append((k, 'SKIP', name, ''))
            continue
        try:
            open(path, 'w').write(text.replace(old, new))
            b = run(['swift', 'build', '-j', '2', '--build-tests'])
            if b.returncode != 0:
                verdict, detail = 'CAUGHT (does not compile)', b.stdout[-300:].replace('\n', ' ')
            else:
                t = run(['swift', 'test', '-j', '2', '--skip-build', '--filter', SUITES], timeout=600)
                failed = [l for l in t.stdout.splitlines() if ' failed (' in l and "Test Case '-[" in l]
                verdict = ('CAUGHT (the suite hangs: killed after 600 s)' if t.returncode == 124
                           else 'CAUGHT' if t.returncode != 0 else 'MISSED')
                detail = '; '.join(sorted({l.split('[')[1].split(']')[0] for l in failed}))[:600]
        finally:
            open(path, 'w').write(text)
        rows.append((k, verdict, name, detail))
        print('%d %s  %s  [%s]' % (k, verdict, name, detail), flush=True)
    run(['swift', 'build', '-j', '2', '--build-tests'])
    caught = sum(1 for r in rows if r[1].startswith('CAUGHT'))
    print('%d/%d caught' % (caught, len(rows)), flush=True)


if __name__ == '__main__':
    main()
