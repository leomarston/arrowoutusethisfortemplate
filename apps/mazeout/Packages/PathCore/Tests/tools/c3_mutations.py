#!/usr/bin/env python3
"""c3_mutations.py — C3's mutation checks (SPEC-architecture §4.17, GP §8.3): each mutation breaks one economy / events /
persistence rule on a COPY of the package (build/c3/mut/, research + App + design symlinked so the #filePath fixtures
resolve) and must make the C3 suites fail. Writes build/c3/mutations.txt (CAUGHT/MISSED per mutation + the first failing
assertion) and a log per run. §4.17 asks for 5 (refill interval, anchor on a win, stacking, a Claw point on a loss, backup
skipped); m6–m11 are extra C3 rules.
Usage: python3 c3_mutations.py [m1 m3 …]   (no argument = all, and mutations.txt is rewritten)"""
import os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..', '..'))
APP = os.path.abspath(os.path.join(PKG, '..', '..'))
OUTDIR = os.path.join(APP, 'build', 'c3')
MUT = os.path.join(OUTDIR, 'mut')
COPY = os.path.join(MUT, 'Packages', 'PathCore')
SUITES = 'EconomyTests|LivesTests|BoostersTests|EventsTests|PersistenceTests'
R = 'Sources/GameCore/'

MUTATIONS = [
    # §4.17 C3: 5
    ('m1-refill-interval-20-min', R + 'Economy/Lives.swift',
     'return Int(((elapsed + r.refillEpsilon) / r.refillSeconds).rounded(.down))',
     'return Int(((elapsed + r.refillEpsilon) / (r.refillSeconds * 2 / 3)).rounded(.down))'),
    ('m2-anchor-restarts-on-a-win', R + 'Economy/Lives.swift',
     '        s.lives.count = min(r.max, s.lives.count + 1)\n        if s.lives.count >= r.max { s.lives.anchor = nil }',
     '        s.lives.count = min(r.max, s.lives.count + 1)\n        s.lives.anchor = t\n        if s.lives.count >= r.max { s.lives.anchor = nil }'),
    ('m3-unlimited-does-not-stack', R + 'Economy/Lives.swift',
     'let base = max(s.unlimitedLivesUntil ?? t, t)', 'let base = t'),
    ('m4-a-claw-point-on-a-loss', R + 'Events/Events.swift',
     '        if let f = streakFail(&s.events, rules) { out.append(.multiplier(from: f.from, to: f.to)) }',
     '        if let f = streakFail(&s.events, rules) { out.append(.multiplier(from: f.from, to: f.to)) }\n'
     '        out += clawAdd(&s, points: 1, at: t, rules)'),
    ('m5-backup-skipped', R + 'Persistence/StateStore.swift',
     '        if fm.fileExists(atPath: url.path), primaryLooksGood() { rotateBackup() }\n', ''),
    # extra C3 rules
    ('m6-life-refunded-on-a-loss', R + 'Economy/Economy.swift',
     '            if !free && rules.lives.cost == .atLoss { takeLife(&s, at: t, rules.lives) }',
     '            if !free && rules.lives.cost == .atLoss { takeLife(&s, at: t, rules.lives) }\n'
     '            if !free { giveLifeBack(&s, at: t, rules.lives) }'),
    ('m7-unlimited-ignored-at-the-start', R + 'Economy/Economy.swift',
     '        let free = unlimited(s, at: t)\n', '        let free = false\n'),
    ('m8-streak-scores-after-the-step', R + 'Events/Streak.swift',
     '        return (from, from, stepValue(e.streakStep, r))',
     '        return (stepValue(e.streakStep, r), from, stepValue(e.streakStep, r))'),
    ('m9-clock-rewind-allowed', R + 'Economy/Lives.swift',
     '        let t = SocialClock.now(wall: wall, highWater: &s.social.highWater)',
     '        let t = SocialTime(seconds: Int64(wall.timeIntervalSince1970.rounded(.down)))\n'
     '        s.social.highWater = max(s.social.highWater, t.seconds)'),
    ('m10-a-kill-is-not-a-loss', R + 'Economy/Economy.swift',
     '            if rules.lives.killIsLoss {', '            if !rules.lives.killIsLoss {'),
    ('m11-corrupt-file-rotated-into-the-backup', R + 'Persistence/StateStore.swift',
     '                primaryIsGood = false\n', '                primaryIsGood = true\n'),
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
    for link in ('research', 'App', 'design', 'tools'):
        lp = os.path.join(MUT, link)
        if not os.path.islink(lp):
            os.symlink(os.path.join(APP, link), lp)
    test = ['swift', 'test', '-j', '2', '--filter', SUITES]
    code, out = run(test, COPY, os.path.join(MUT, 'baseline.log'))
    base = re.findall(r'Executed (\d+) tests?, with (\d+) failures', out)
    print('baseline:', 'ok' if code == 0 else 'FAILED', base[-1] if base else '', flush=True)
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
        fails = [l for l in out.splitlines() if ': error: -[' in l]
        if not fails and code != 0:
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
