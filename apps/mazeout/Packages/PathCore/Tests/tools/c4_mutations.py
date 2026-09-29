#!/usr/bin/env python3
"""c4_mutations.py — C4's mutation checks (GAMEPROMPT §8.3, SPEC-architecture §4.17: C4 needs 3, all CAUGHT).

Each mutation edits ONE PathCore source line, rebuilds, runs the C4 suites (GeneratorTests, ValidatorTests,
SolverTests, LevelLibraryTests) and restores the file. CAUGHT = at least one test fails; MISSED = all pass.
  python3 Tests/tools/c4_mutations.py [package dir] [--only N]   (run it on a scratch copy of the package)
"""
import os
import subprocess
import sys

PKG = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else
                      os.path.join(os.path.dirname(__file__), '..', '..'))
ONLY = int(sys.argv[sys.argv.index('--only') + 1]) if '--only' in sys.argv else None
SRC = os.path.join(PKG, 'Sources', 'PathCore')

MUTATIONS = [
    ('generator: the tiler tries the turns before going straight when it should go straight',
     'Content/Generator.swift',
     'let opts = rng.chance(straight) ? [d] + turn : turn + [d]',
     'let opts = rng.chance(straight) ? turn + [d] : [d] + turn'),
    ('generator: the incremental DAG skips the cycle test (a head flip that closes a cycle is accepted)',
     'Content/Generator.swift',
     'if reaches(newR, i) { return false }',
     'if false && reaches(newR, i) { return false }'),
    ('rules mirror: a pipe mouth accepts a ray moving WITH its out direction',
     'Content/ContentRules.swift',
     'if S.pipeEndPipe[k] == Int32(p), let out = S.pipeEndOut[k], out == d.opposite {',
     'if S.pipeEndPipe[k] == Int32(p), let out = S.pipeEndOut[k], out == d {'),
    ('validator: the tape tie-cell check is gone',
     'Content/Validator.swift',
     'if cs.count != mem.count || ties != Set(cs) {',
     'if false && (cs.count != mem.count || ties != Set(cs)) {'),
    ('search: every board counts as monotone (a greedy failure is final)',
     'Solver/Search.swift',
     'if board.isMonotone { return .unsolvable }',
     'if true { return .unsolvable }'),
    ('provider: a generated level is served even when the validator refuses it',
     'Content/LevelProvider.swift',
     'return rep.isValid ? nil : rep.errors.first.map(\\.message) ?? "invalid"',
     'return nil'),
]


def run(cmd, timeout=None):
    """Runs in its own process group so a hung xctest is killed with it (a mutant that makes the suite hang is
    CAUGHT: the default suite finishes in about a minute)."""
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
        if ONLY and k != ONLY:
            continue
        path = os.path.join(SRC, rel)
        text = open(path).read()
        if text.count(old) != 1:
            print('SKIP %d %s: anchor found %d times' % (k, name, text.count(old)), flush=True)
            continue
        try:
            open(path, 'w').write(text.replace(old, new))
            b = run(['swift', 'build', '-j', '2', '--build-tests'])
            if b.returncode != 0:
                verdict, detail = 'CAUGHT (does not compile)', b.stdout[-400:]
            else:
                t = run(['swift', 'test', '-j', '2', '--skip-build', '--filter',
                         'GeneratorTests|ValidatorTests|SolverTests|LevelLibraryTests'], timeout=600)
                failed = [l for l in t.stdout.splitlines() if ' failed (' in l and "Test Case '-[" in l]
                verdict = ('CAUGHT (the suite hangs: killed after 600 s)' if t.returncode == 124
                           else 'CAUGHT' if t.returncode != 0 else 'MISSED')
                detail = '; '.join(sorted({l.split('[')[1].split(']')[0] for l in failed}))[:500]
        finally:
            open(path, 'w').write(text)
        rows.append((k, verdict, name, detail))
        print('%d %s  %s  [%s]' % (k, verdict, name, detail), flush=True)
    run(['swift', 'build', '-j', '2', '--build-tests'])
    caught = sum(1 for r in rows if r[1].startswith('CAUGHT'))
    print('%d/%d caught' % (caught, len(rows)))


if __name__ == '__main__':
    main()
