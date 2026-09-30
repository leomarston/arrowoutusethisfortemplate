#!/usr/bin/env python3
"""soc_mutations.py — SOC1's mutation checks (SPEC-architecture §4.17: "SOC1: 4 (banker's rounding, truncating division, a
hash label typo, rewind allowed)", GP §8.3), plus three more, plus SOC1b's six on the session-2 mechanisms (honeymoon
session sizing and rate, name-ordered ties, the leet style, the Sky Jump first step, the Rocket sprint window), plus
SOC1c's seven on the drawn nicknames, the style counts and Sky Jump stage 3 (the popularity head dropped, uniform instead
of by rank, case variants keyed by the round, the draw switched off = unique slots again, a shifted 2-digit number, stage 3
back to 9 levels, the per-cohort style counts back to the last-style-takes-the-remainder rounding). Each mutation breaks one rule on a COPY of the package (build/soc1c/mut/: Sources + the Social test files + soc_
fixtures; design, research and App symlinked so #filePath paths resolve) and must make the Social suites fail. Writes
build/soc1c/mutations.txt.
    python3 Packages/PathCore/Tests/tools/soc_mutations.py [name ...]
"""
import os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, '..', '..'))
APP = os.path.abspath(os.path.join(PKG, '..', '..'))
OUTDIR = os.path.join(APP, 'build', 'soc1c')
MUT = os.path.join(OUTDIR, 'mut')
COPY = os.path.join(MUT, 'Packages', 'PathCore')
S = 'Sources/GameCore/Social/'
FILTER = 'SocialGoldenTests|SocialModelGoldenTests|SocialPropertyTests'
# PUBLISH B2: the suites that pin the v2 world (goldens, intl fixture + tests_v2 properties, the shipped name bank)
V2F = 'SocialModelGoldenTests/testV2|SocialIntlTests|SocialNamesTests|SocialPropertyTests'

MUTATIONS = [
    ('m1-bankers-rounding', S + 'SocialHash.swift',
     'static func roundHalfUp(_ x: Double) -> Int { Int((x + 0.5).rounded(.down)) }',
     'static func roundHalfUp(_ x: Double) -> Int { Int(x.rounded(.toNearestOrEven)) }'),
    ('m2-truncating-division', S + 'SocialHash.swift',
     'return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q', 'return q'),
    ('m3-hash-label-typo', S + 'SocialHash.swift',
     'static let cn = Label("cn")', 'static let cn = Label("cN")'),
    ('m4-rewind-allowed', S + 'SocialClock.swift',
     'if device > highWater { highWater = device }\n        return (SocialTime(seconds: highWater), false)',
     'highWater = device\n        return (SocialTime(seconds: device), false)'),
    # extra: the player sits LAST (not first) among its level group; the cycle walk dropped; a stale frozen memo
    ('m5-player-last-among-equals', S + 'Population.swift',
     'func rankOfLevel(_ x: Int, _ t: Double, iso: String? = nil) -> Int { 1 + countAtLeast(x + 1, t, iso: iso) }',
     'func rankOfLevel(_ x: Int, _ t: Double, iso: String? = nil) -> Int { 1 + countAtLeast(x, t, iso: iso) }'),
    ('m6-no-cycle-walk', S + 'SocialHash.swift',
     'while y >= nn { y = permPow2(y, half, key) }', 'if y >= nn { y = y % nn }'),
    ('m7-frozen-too-early', S + 'Population.swift',
     'if t > c.frozenAfter {\n            if let P = c.frozenP[j] { return P }',
     'if t > c.frozenAfter - 86_400 {\n            if let P = c.frozenP[j] { return P }'),
    # SOC1b: the session-2 mechanisms
    ('m8-honeymoon-windows-unsized', S + 'Population.swift',
     'if c.hE != nil && dl <= c.hDL { Q = c.lamMax * (1.0 + c.hb) * m }',
     'if c.hE != nil && dl <= c.hDL && false { Q = c.lamMax * (1.0 + c.hb) * m }'),
    ('m13-honeymoon-rate-dropped', S + 'Population.swift',
     'let lh = mb.lam * (1.0 + c.hb)', 'let lh = mb.lam'),
    ('m9-streak-ties-by-reach', S + 'RaceBots.swift',
     'if spec.tieByName, let un = userName {', 'if spec.tieByName && false, let un = userName {'),
    ('m10-leet-digits-shifted', S + 'Names.swift',
     'if i < leetB { return L[i / 900] + String(100 + i % 900) }', 'if i < leetB { return L[i / 900] + String(100 + (i + 1) % 900) }'),
    ('m11-sky-drops-from-step-1', S + 'RaceBots.swift',
     'let drop = k < dr.first ? 0 :', 'let drop = k < 1 ? 0 :'),
    ('m12-rocket-sprint-window', S + 'RaceBots.swift',
     'let sprint = spec.sprintMinutes * 60.0 * Double(N) / 5.0', 'let sprint = spec.sprintMinutes * 60.0'),
    # SOC1c: drawn nicknames (duplicates allowed) and Sky Jump stage 3 = 10 levels
    ('m14-draw-head-dropped', S + 'Names.swift',
     'if H.below(key, L.headQ, 100) < D.headP {', 'if H.below(key, L.headQ, 100) < 0 {'),
    ('m15-draw-uniform-not-by-rank', S + 'Names.swift',
     't = H.floorInt(Double(ntok) * u * u)', 't = H.floorInt(Double(ntok) * u)'),
    ('m16-draw-variants-by-round', S + 'Names.swift',
     'vr: Int(H.h64(key, L.variant) & 0x7FFF_FFFF),', 'vr: r,'),
    ('m17-draw-off-unique-slots', S + 'Population.swift',
     '} else if let draw = model.nameStyle.draw {', '} else if let draw = model.nameStyle.draw, false {'),
    ('m18-draw-two-digit-shifted', S + 'Names.swift',
     '10 + H.below(key, L.num, 90)', '11 + H.below(key, L.num, 89)'),
    ('m19-sky-stage3-nine-levels', S + 'RaceBots.swift',
     'public static let shipped = SocialSkySpec(levels: [5, 7, 10]', 'public static let shipped = SocialSkySpec(levels: [5, 7, 9]'),
    # SOC1c: per-cohort style counts by systematic apportionment (the reference's remainder rounding over-weights 'leet')
    ('m20-style-counts-remainder-last', S + 'Population.swift',
     'if model.nameStyle.systematic {', 'if model.nameStyle.systematic && false {'),
    # PUBLISH B2: the v2 world's mechanisms (social-intl §6.3 item 8: block order label, apportion offset, jitter label,
    # culture-mix label, an alias entry, the LOCAL salt; + the shards, tilt, native shares, scaled head, epoch, the unit
    # counts, the hashed blocklist and the CJK username rule). The 5th element narrows the run to the suites that pin them.
    ('v1-block-order-label', S + 'SocialHash.swift', 'cord = Label("cord")', 'cord = Label("c0rd")', V2F),
    ('v2-apportion-offset', S + 'Population.swift',
     'min(m, H.floorInt(Double(m) * (cw / tot) + u))', 'min(m, H.floorInt(Double(m) * (cw / tot) + 0.5))', V2F),
    ('v3-jitter-label', S + 'SocialHash.swift', 'uj = Label("uj")', 'uj = Label("uJ")', V2F),
    ('v4-culture-mix-label', S + 'SocialHash.swift', 'mcul = Label("mcul")', 'mcul = Label("mcu1")', V2F),
    ('v5-alias-entry', S + 'SocialIntlTables.swift', 'IC\\talias\\tES', 'IC\\talias\\tPT', V2F),
    ('v6-local-salt', S + 'Population.swift', 'ck ^= h << 32', 'ck ^= h << 31', V2F),
    ('v7-row-tilt-dropped', S + 'Population.swift',
     'model.archetypes.map { a in rs.map { r in intl.rowTilt[r.iso].map { r.weight * ($0[a.key] ?? 1.0) } ?? r.weight } }',
     'model.archetypes.map { _ in rs.map { r in r.weight } }', V2F),
    ('v8-min-shards-dropped', S + 'Population.swift',
     'if let mins = intl?.minShards { ns = max(ns, mins[key] ?? 1) }', 'if let mins = intl?.minShards, false { ns = max(ns, mins[key] ?? 1) }', V2F),
    ('v9-native-share-ignored', S + 'Names.swift',
     'let useNative = v < UInt64(nativeT?[culture] ?? 180)', 'let useNative = v < 180', V2F),
    ('v10-kana-dropped', S + 'Names.swift', 'if kanaP > 0 && useNative && culture == "jp"', 'if kanaP > 100 && useNative && culture == "jp"', V2F),
    ('v11-head-unscaled', S + 'Names.swift', 'let headN = max(1, min(D.headN, ntok / 6))', 'let headN = max(1, min(D.headN, ntok))', V2F),
    ('v12-world-epoch-a-week-early', S + 'SocialModel.swift', 'm.epoch = 1_788_764_400', 'm.epoch = 1_788_764_400 - 604_800', V2F),
    ('v13-unit-count-ignores-start', S + 'Population.swift',
     'for u in g.units where u.e > b { tot += u.e - max(b, u.s) }', 'for u in g.units where u.e > b { tot += u.e - b }', V2F),
    ('v14-hashed-blocklist-ignored', S + 'Names.swift', 'let hashed = !d.blockHashed.isEmpty', 'let hashed = false', V2F),
    # PUBLISH B2 perf/memory mechanisms (must stay exact: the goldens pin every value they touch)
    ('p1-moving-bracket-trusted', S + 'Population.swift',
     'if br.lo == br.hi && c.ckMono { return br.lo }', 'if c.ckMono { return br.lo }'),
    ('p2-neighbour-prune-by-upper-bound', S + 'Population.swift', 'for d in deferA where d.lo <= ta {', 'for d in deferA where d.hi <= ta {'),
    ('p3-session-cache-key-without-day', S + 'Population.swift',
     'let key = UInt64(truncatingIfNeeded: c.idx) << 32 | UInt64(UInt32(truncatingIfNeeded: dl))',
     'let key = UInt64(truncatingIfNeeded: c.idx) << 32'),
    ('p4-prefix-sum-reversed', S + 'Population.swift',
     'for i in from..<(from + k) { s = s + p[i] }', 'for i in (from..<(from + k)).reversed() { s = s + p[i] }'),
    ('v15-username-cjk-three', S + 'Names.swift',
     'public static func usernameLengths(_ s: String) -> ClosedRange<Int> { (hasCJK(s) ? 2 : 3)...16 }',
     'public static func usernameLengths(_ s: String) -> ClosedRange<Int> { 3...16 }', V2F),
]


def run(cmd, cwd, log, timeout=900):
    """Runs the suites; a run over `timeout` seconds is killed and reported as a HANG (never silently CAUGHT)."""
    with open(log, 'w') as f:
        try:
            p = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            subprocess.run(['pkill', '-f', os.path.join(OUTDIR, '.build-mut')])
            code = 'HANG'
    return code, open(log, errors='replace').read()


def fresh_copy():
    os.makedirs(os.path.join(COPY, 'Tests', 'PathCoreTests'), exist_ok=True)
    os.makedirs(os.path.join(COPY, 'Tests', 'Fixtures'), exist_ok=True)
    for d in ('design', 'research', 'App'):
        link = os.path.join(MUT, d)
        if not os.path.lexists(link):
            os.symlink(os.path.join(APP, d), link)
    shutil.rmtree(os.path.join(COPY, 'Sources'), ignore_errors=True)
    shutil.copytree(os.path.join(PKG, 'Sources'), os.path.join(COPY, 'Sources'))
    shutil.copy(os.path.join(PKG, 'Package.swift'), os.path.join(COPY, 'Package.swift'))
    for sub, pat in (('PathCoreTests', re.compile(r'^Social.*Tests\.swift$')), ('Fixtures', re.compile(r'^soc_'))):
        dst = os.path.join(COPY, 'Tests', sub)
        for f in os.listdir(dst):
            os.remove(os.path.join(dst, f))
        for f in os.listdir(os.path.join(PKG, 'Tests', sub)):
            if pat.match(f):
                shutil.copy(os.path.join(PKG, 'Tests', sub, f), os.path.join(dst, f))


def main():
    only = sys.argv[1:]
    os.makedirs(MUT, exist_ok=True)
    scratch = os.path.join(OUTDIR, '.build-mut')
    cmd = ['swift', 'test', '-j', '2', '--scratch-path', scratch, '--filter', FILTER]
    fresh_copy()
    # the baseline runs every suite a selected mutation uses
    base_filter = '|'.join(sorted({FILTER} | {m[4] for m in MUTATIONS if len(m) > 4 and (not only or m[0] in only)}))
    code, out = run(cmd[:-1] + [base_filter], COPY, os.path.join(MUT, 'baseline.log'))
    lines = ['baseline (no mutation): %s' % ('PASS' if code == 0 else 'FAIL — fix before judging mutations')]
    print(lines[0], flush=True)
    for name, rel, old, new, *more in MUTATIONS:
        if only and name not in only:
            continue
        fresh_copy()
        path = os.path.join(COPY, rel)
        src = open(path).read()
        if old not in src:
            lines.append('%s: NOT APPLIED (pattern missing in %s)' % (name, rel)); print(lines[-1]); continue
        open(path, 'w').write(src.replace(old, new, 1))
        mcmd = cmd[:-1] + [more[0]] if more else cmd
        code, out = run(mcmd, COPY, os.path.join(MUT, name + '.log'))
        fails = re.findall(r'error: -\[PathCoreTests\.(\w+) (\w+)\] : (.*)', out)
        if code == 'HANG':
            lines.append('%s: HANG (no result within the timeout; a hang is a defect to fix, not a catch)' % name)
        elif code != 0 and fails:
            first = ('%s.%s: %s' % fails[0])[:220]
            lines.append('%s: CAUGHT (%d failing assertions) — first: %s' % (name, len(fails), first))
        elif code != 0:
            # SOC1c: a mutation that does not compile (or crashes the runner) proves nothing about the tests
            last = out.strip().splitlines()[-1][:220] if out.strip() else ''
            lines.append('%s: NOT JUDGED (the run failed without a failing assertion: a compile error or a crash) — %s'
                         % (name, last))
        else:
            lines.append('%s: MISSED' % name)
        print(lines[-1], flush=True)
    fresh_copy()
    with open(os.path.join(OUTDIR, 'mutations.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
