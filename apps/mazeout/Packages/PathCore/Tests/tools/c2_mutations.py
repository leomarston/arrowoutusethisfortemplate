#!/usr/bin/env python3
"""c2_mutations.py — C2's mutation checks (SPEC-architecture §4.17, GP §8.3): each mutation breaks one rule on a COPY of
the package (build/c2/mut/, research + App symlinked so #filePath fixtures resolve) and must make the C2 suites fail.
Writes build/c2/mutations.txt (CAUGHT/MISSED per mutation + the first failing assertion) and a log per run."""
import os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..', '..'))
APP = os.path.abspath(os.path.join(PKG, '..', '..'))
OUTDIR = os.path.join(APP, 'build', 'c2')
MUT = os.path.join(OUTDIR, 'mut')
COPY = os.path.join(MUT, 'Packages', 'PathCore')
SUITES = 'RulesTests|SessionTests|ClockTests|ComboTests|GoldenRoundsTests|HeadlessTests|APISurfaceTests'
R = 'Sources/ArrowEscape/'

MUTATIONS = [
    ('m1-ray-stops-one-cell-early', R + 'Rules/RayWalk.swift',
     'if !grid.inBounds(q) {', 'if !grid.inBounds(q) || !grid.inBounds(q + d) {'),
    ('m2-tape-all-clear-to-any-clear', R + 'Rules/TapResolver.swift',
     'if blocked.isEmpty { return .exit(', 'if blocked.count < unit.count { return .exit('),
    ('m3-door-opens-at-the-tap', R + 'Rules/BoardState.swift',
     'if obs[d].door == .locked { obs[d].door = .targeted }', 'if obs[d].door == .locked { obs[d].door = .open; breakObstacle(d) }'),
    ('m4-pipe-consumes-on-a-bump', R + 'Rules/BoardState.swift',
     '        guard let a = index[plan.arrow] else { return [] }\n        var members = [a]',
     '        for s in plan.path.segments { if case .tube(let p, _) = s, let k = obsIndex[p], let c = obs[k].counter { obs[k].counter = max(0, c - 1) } }\n'
     '        guard let a = index[plan.arrow] else { return [] }\n        var members = [a]'),
    ('m5-timer-starts-at-intro', R + 'Session/LevelSession.swift',
     '        started = true\n        clock.hold(.intro)', '        started = true\n        clock.startOnFirstTap()'),
    # the win is defended twice (the clock holds at the win AND expiry only fires while playing): m6 removes both (the
    # real bug), m6b only lets the clock run on after the last tap (the timer must stop on the last arrow)
    ('m6-win-does-not-beat-fail', R + 'Session/LevelSession.swift',
     '                if case .playing = phase { ev += openOffer(.outOfTime, step: 0) }', '                ev += openOffer(.outOfTime, step: 0)',
     '        clock.hold(.winSequence)\n        let result', '        let result'),
    ('m6b-clock-runs-after-the-win', R + 'Session/LevelSession.swift',
     '        clock.hold(.winSequence)\n        let result', '        let result'),
    ('m7-key-to-the-highest-order-door', R + 'Rules/TapResolver.swift',
     'if let b = best, (obs[b].order, b) <= (obs[d].order, d) { continue }', 'if let b = best, (obs[b].order, b) >= (obs[d].order, d) { continue }'),
    ('m8-box-counts-a-bundle-once', R + 'Rules/BoardState.swift',
     'let left = max(0, c - unit.count)', 'let left = max(0, c - 1)'),
    ('m9-heart-at-the-tap-not-contact', R + 'Session/LevelSession.swift',
     '            ev.append(.bumped(plan))\n            board.commit(.bump(plan))',
     '            ev.append(.bumped(plan))\n            board.commit(.bump(plan))\n            hearts -= 1'),
    ('m10-combo-window-ignored', R + 'Session/Combo.swift',
     'if let last = lastTap, t - last <= window, t >= last { count += 1 } else { count = 1 }', 'count += 1'),
]


def run(cmd, cwd, log):
    with open(log, 'w') as f:
        p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    return p.returncode, open(log).read()


def main():
    only = sys.argv[1:]
    os.makedirs(MUT, exist_ok=True)
    if os.path.exists(COPY):
        for sub in ('Sources', 'Tests'):
            shutil.rmtree(os.path.join(COPY, sub), ignore_errors=True)
    os.makedirs(COPY, exist_ok=True)
    for sub in ('Sources', 'Tests'):
        shutil.copytree(os.path.join(PKG, sub), os.path.join(COPY, sub))
    shutil.copy(os.path.join(PKG, 'Package.swift'), COPY)
    for link, target in (('research', os.path.join(APP, 'research')), ('App', os.path.join(APP, 'App'))):
        lp = os.path.join(MUT, link)
        if not os.path.islink(lp):
            os.symlink(target, lp)
    test = ['swift', 'test', '-j', '2', '--filter', SUITES]
    code, out = run(test, COPY, os.path.join(MUT, 'baseline.log'))
    base = re.findall(r'Executed (\d+) tests?, with (\d+) failures', out)
    print('baseline:', 'ok' if code == 0 else 'FAILED', base[-1] if base else '')
    if code != 0:
        sys.exit('baseline must be green')
    lines = []
    for name, rel, *edits in MUTATIONS:
        if only and name.split('-')[0] not in only:
            continue
        path = os.path.join(COPY, rel)
        src = open(path).read()
        mutated = src
        for old, new in zip(edits[0::2], edits[1::2]):
            assert mutated.count(old) == 1, '%s: pattern found %d times' % (name, mutated.count(old))
            mutated = mutated.replace(old, new)
        open(path, 'w').write(mutated)
        try:
            code, out = run(test, COPY, os.path.join(MUT, name + '.log'))
        finally:
            open(path, 'w').write(src)
        fails = [l for l in out.splitlines() if ': error: ' in l]
        if 'error: compile' in out or ('error:' in out and not fails and code != 0):
            verdict = 'BUILD-FAILED (fix the mutation)'
        else:
            verdict = 'CAUGHT (%d failing assertions)' % len(fails) if fails else 'MISSED'
        first = fails[0].split(': error: ', 1)[1][:260] if fails else ''
        line = '%s: %s%s' % (name, verdict, (' — first: ' + first) if first else '')
        print(line, flush=True)
        lines.append(line)
    if not only:
        open(os.path.join(OUTDIR, 'mutations.txt'), 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
