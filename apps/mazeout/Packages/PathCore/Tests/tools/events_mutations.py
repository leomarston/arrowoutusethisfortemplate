#!/usr/bin/env python3
"""events_mutations.py — B1 EVENTS-P's mutation checks (design/publish/events.md §8.4 A11; PLAN-P §4.4 B1): each mutation
breaks one rule of the weekly rotation, Up & Away or the event notifications on a COPY of the package (build/p/B1/mut/,
research + App + design + tools symlinked so the #filePath fixtures resolve) and must make the events suites fail.
Writes build/p/B1/mutations.txt (CAUGHT/MISSED per mutation + the first failing assertion) and a log per run.

A11's five (events.md): the maxRun rule dropped; the week from the wall clock instead of SocialTime; the Double gap 3 -> 1;
the Balloon fall resetting ALL steps (v582 terms: a fall also resets the paid platforms, so they pay again); a notification
outside 10-21 local. The others are extra B1 rules. f1-f8 = B1b's "Finished" state (events.md PH-0a, EventFinished.swift);
`python3 events_mutations.py f1 f2 …` runs only those (mutations.txt is not rewritten; B1b keeps its lines in build/p/B1b/).
Hygiene (B0 2026-09-28, GAMEPROMPT §13 pitfall): every run has a 600 s timeout; `swift test` runs xctest OUTSIDE its process
group, so after every run everything still running from the copy's .build/ is killed (no orphaned xctest).
Usage: nice -n 10 python3 events_mutations.py [e1 e3 …]   (no argument = all, and mutations.txt is rewritten)"""
import os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..', '..'))
APP = os.path.abspath(os.path.join(PKG, '..', '..'))
OUTDIR = os.path.join(APP, 'build', 'p', 'B1')
MUT = os.path.join(OUTDIR, 'mut')
COPY = os.path.join(MUT, 'Packages', 'PathCore')
SUITES = 'EventRotationTests|BalloonRiseTests|EventsRotationHookTests|EventsBenchTests|EventsTests|EventsFinishedTests'
E = 'Sources/PathCore/Events/'

MUTATIONS = [
    # events.md §8.4 A11
    ('e1-maxRun-rule-dropped', E + 'EventRotation.swift',
     '            if g.ladderRun >= maxRun { lad = 1 - last } else {',
     '            if false && g.ladderRun >= maxRun { lad = 1 - last } else {'),
    ('e2-week-from-the-wall-clock', E + 'Events.swift',
     '        let rw = EventRotation.week(t, ev)',
     '        let rw = EventRotation.week(SocialTime(seconds: Int64(now.timeIntervalSince1970.rounded(.down))), ev)'),
    ('e3-double-gap-3-to-1', E + 'EventRotation.swift',
     'let maxRun = max(1, rot.maxRun), gap = max(1, rot.doubleMinGap)',
     'let maxRun = max(1, rot.maxRun), gap = 1'),
    ('e4-fall-resets-the-paid-platforms', E + 'BalloonRise.swift',
     '        s.events.balloon.streak = 0\n',
     '        s.events.balloon.streak = 0\n        s.events.balloon.paid = 0\n'),
    ('e5-notification-outside-the-local-window', E + 'EventNotifications.swift',
     'cands.append(Item(kind: .eventStart, at: firstInWindow(atOrAfter: start, zone: zone, window: window), events: fresh,',
     'cands.append(Item(kind: .eventStart, at: start, events: fresh,'),
    # extra B1 rules
    ('e6-fail-keeps-the-last-checkpoint', E + 'BalloonRise.swift',
     '        s.events.balloon.streak = 0\n',
     '        s.events.balloon.streak = r.events.balloonRise.platforms.last(where: { $0.at <= from })?.at ?? 0\n'),
    ('e7-a-win-adds-two', E + 'BalloonRise.swift',
     '        b.streak += 1\n',
     '        b.streak += 2\n'),
    ('e8-claw-scores-in-every-week', E + 'Events.swift',
     'if EventSchedule.counts(.clawChallenge, wonLevel: level, rules: ev), live.contains(.clawChallenge) {',
     'if EventSchedule.counts(.clawChallenge, wonLevel: level, rules: ev) {'),
    ('e9-a-sky-run-dies-at-the-roll', E + 'Events.swift',
     'if EventSchedule.isUnlocked(.skyJump, level: c.level, rules: ev), live.contains(.skyJump) || c.events.sky.active != nil {',
     'if EventSchedule.isUnlocked(.skyJump, level: c.level, rules: ev), live.contains(.skyJump) {'),
    ('e10-kill-switch-runs-up-and-away', E + 'EventRotation.swift',
     'ladder: usable(rot.ladder[0]) ? EventID(rot.ladder[0]) : nil,',
     'ladder: usable(rot.ladder[1]) ? EventID(rot.ladder[1]) : nil,'),
    ('e11-notification-cap-one-hour', E + 'EventNotifications.swift',
     'public static let gap: Int64 = 86_400',
     'public static let gap: Int64 = 3_600'),
    ('e12-joins-ignore-the-calendar', E + 'SkyJump.swift',
     'guard EventRotation.isLive(.skyJump, at: t, level: s.level, rules: rules.events) else {',
     'guard true || EventRotation.isLive(.skyJump, at: t, level: s.level, rules: rules.events) else {'),
    # B1b — the Finished state (v582 PH-0a)
    ('f1-nothing-held-at-the-roll', E + 'EventFinished.swift',
     '        if f != s.events.finished { s.events.finished = f }',
     '        if false && f != s.events.finished { s.events.finished = f }'),
    ('f2-held-under-the-kill-switch', E + 'EventFinished.swift',
     '        guard r.events.rotation.enabled else { return [] }',
     '        guard true || r.events.rotation.enabled else { return [] }'),
    ('f3-a-win-keeps-the-holds', E + 'Events.swift',
     '        dropFinished(&s, movedOn)\n',
     '        _ = movedOn\n'),
    ('f4-the-prize-claim-keeps-the-hold', E + 'Events.swift',
     '        case .streakRacePrize: s.events.finished.removeAll { $0.event == .streakRace && $0.index == c.index }',
     '        case .streakRacePrize: break'),
    ('f5-held-forever', E + 'EventFinished.swift',
     '            return f.index < now - 1 || f.index >= now',
     '            return f.index >= now'),
    ('f6-an-open-drops-every-hold', E + 'EventFinished.swift',
     '        s.events.finished.removeAll { $0.event == e }',
     '        s.events.finished.removeAll()'),
    ('f7-a-loss-moves-on', E + 'Events.swift',
     '        out += balloonFail(&s, at: t, rules)\n',
     '        out += balloonFail(&s, at: t, rules)\n        dropFinished(&s, Set(finishable))\n'),
    ('f8-the-rebase-keeps-future-holds', E + 'Events.swift',
     '        s.events.finished.removeAll { f in\n            f.event == .streakRace ? EventSchedule.dayStart(f.index + 1) > t : EventSchedule.weekStart(f.index + 1) > t\n        }',
     '        s.events.finished.removeAll { _ in false }'),
]


def run(cmd, cwd, log, timeout=600):
    with open(log, 'w') as f:
        p = subprocess.Popen(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, 9)
            code = -9
            f.write('\nTIMEOUT after %d s\n' % timeout)
        finally:
            # xctest lives outside the process group: kill whatever still runs from the copy's .build/
            subprocess.run(['pkill', '-9', '-f', os.path.join(COPY, '.build') + '/'])
    return code, open(log).read()


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
        if not os.path.islink(lp) and not os.path.exists(lp):
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
