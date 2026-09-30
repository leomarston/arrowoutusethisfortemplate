import XCTest
@testable import GameCore
@testable import ArrowEscape

// SOC1 (SPEC-social §8.2): the reference's property tests (design/social/tools/tests.py, 18 checks) ported 1:1 and run on
// BOTH parameter sets, plus the Swift-only checks (rewind, state round trip, ledger rules). Sampling uses a fixed-seed
// generator (the properties, not the samples, are the reference's).

struct SocRNG {
    var s: UInt64
    init(_ seed: UInt64) { s = seed }
    mutating func next() -> UInt64 { s = s &+ 0x9E37_79B9_7F4A_7C15; return SocialHash.mix(s) }
    mutating func below(_ n: Int) -> Int { Int(next() % UInt64(max(1, n))) }
    mutating func uniform(_ a: Double, _ b: Double) -> Double { a + (b - a) * SocialHash.unit(next()) }
}

final class SocialPropertyTests: XCTestCase {
    typealias F = SocFix
    static let tNow = 1_790_298_000.0            // 2026-09-25 01:00 UTC (tests.py T_NOW)
    /// PUBLISH B2: tests.py runs the same properties on the v2 world at its own T_NOW (2026-12-25 01:00 UTC: v2's world
    /// starts 2026-09-07), then the v2-only checks 15-22 (SocialIntlTests).
    static let tNowV2 = 1_798_160_400.0
    static let models = ["reference", "v552", "v2"]
    func tNow(_ model: String) -> Double { model == "v2" ? Self.tNowV2 : Self.tNow }

    func world(_ model: String) -> SocialPopulation {
        let W = F.world(model)
        W.extend(to: tNow(model) + 9 * 86_400)
        return W
    }
    func live(_ W: SocialPopulation, _ model: String) -> [SocialCohort] {
        W.cohorts.filter { $0.n > 1 && $0.join0 - $0.span < tNow(model) }
    }
    /// Every member of country `iso` joined in a cohort that started before `tMax` (tests.py iso_members: a v2 cohort's
    /// members belong to several countries — brute force over the members; v1: the cohort's one country).
    func members(_ W: SocialPopulation, _ iso: String, _ tMax: Double) -> [(SocialCohort, Int)] {
        var out: [(SocialCohort, Int)] = []
        for c in W.cohorts where c.join0 - c.span < tMax {
            if let ci = c.iso { if ci == iso { for j in 0..<c.n { out.append((c, j)) } }; continue }
            for j in 0..<c.n where W.isoOf(c, j) == iso { out.append((c, j)) }
        }
        return out
    }

    // 0. the exact-arithmetic helpers (SPEC-social §7 "Exactness rules"): floor(x + 0.5) never banker's rounding, and
    //    Python's floor division / modulo on negative operands (Swift / and % truncate)
    func testExactArithmeticHelpers() {
        XCTAssertEqual([0.5, 1.5, 2.5, 3.5, -0.5, -1.5, 2.4999999999999996].map(SocialHash.roundHalfUp), [1, 2, 3, 4, 0, -1, 2])
        XCTAssertEqual(SocialHash.floorDiv(-1, 86_400), -1)
        XCTAssertEqual(SocialHash.floorDiv(-86_400, 86_400), -1)
        XCTAssertEqual(SocialHash.floorDiv(-86_401, 86_400), -2)
        XCTAssertEqual(SocialHash.floorDiv(7, -2), -4)
        XCTAssertEqual(SocialHash.posMod(-1, 28), 27)
        XCTAssertEqual(SocialHash.posMod(-29, 28), 27)
        XCTAssertEqual(SocialHash.posMod(5, -3), -1)
        XCTAssertEqual(SocialCalendar.eventDay(SocialCalendar.epoch - 1), -1)
        XCTAssertEqual(SocialHash.floorInt(-0.5), -1)
        XCTAssertEqual(SocialHash.interp(-1, [0, 1], [4, 20]), 4)
        XCTAssertEqual(SocialHash.interp(2, [0, 1], [4, 20]), 20)
        XCTAssertEqual(SocialHash.interp(0.25, [0, 1], [4, 20]), 8)
    }

    /// An out-of-range input never hangs the cycle walk (it used to spin forever on some keys).
    func testPermOutOfRangeTerminates() {
        for n in [3, 7, 100, 4097] {
            for x in [n, n + 1, 5 * n + 3, -1, -n - 2] {
                let y = SocialHash.perm(x, n, SocialHash.h64(9, "p", [n, x]))
                XCTAssertTrue((0..<n).contains(y))
            }
        }
    }

    // 1. perm is a bijection and permInv inverts it
    func testPermBijection() {
        for n in [1, 2, 3, 7, 64, 100, 1000, 4097] {
            let key = SocialHash.h64(1, "p", [n])
            let img = (0..<n).map { SocialHash.perm($0, n, key) }
            XCTAssertEqual(img.sorted(), Array(0..<n), "n \(n)")
            for x in stride(from: 0, to: n, by: max(1, n / 50)) {
                XCTAssertEqual(SocialHash.permInv(SocialHash.perm(x, n, key), n, key), x)
            }
        }
    }

    // 2. members are sorted by level inside every cohort (monotone in u) at random times
    func testMonotoneInU() {
        for model in Self.models {
            let W = world(model), lv = live(W, model)
            var rng = SocRNG(42), bad = 0, n = 0
            for _ in 0..<400 {
                let c = lv[rng.below(lv.count)]
                let t = rng.uniform(c.join0 - c.span, tNow(model))
                var prev = -1.0
                for j in stride(from: 0, to: c.n, by: max(1, c.n / 30)) {
                    let P = W.progress(c, j, t) ?? -1.0
                    n += 1
                    if P < prev - 1e-9 { bad += 1 }
                    prev = P
                }
            }
            XCTAssertEqual(bad, 0, "\(model): \(bad) of \(n)")
        }
    }

    // 3. a member's progress never decreases with time
    func testMonotoneInTime() {
        for model in Self.models {
            let W = world(model), lv = live(W, model)
            var rng = SocRNG(43), bad = 0
            for _ in 0..<300 {
                let c = lv[rng.below(lv.count)], j = rng.below(c.n)
                let times = (0..<40).map { _ in rng.uniform(c.join0 - c.span, tNow(model)) }.sorted()
                var prev = -1.0
                for t in times {
                    let P = W.progress(c, j, t) ?? -1.0
                    if P < prev - 1e-9 { bad += 1 }
                    prev = P
                }
            }
            XCTAssertEqual(bad, 0, model)
        }
    }

    // 4. continuity across local midnight
    func testMidnightContinuity() {
        for model in Self.models {
            let W = world(model), lv = live(W, model)
            var rng = SocRNG(44), worst = 0.0
            for _ in 0..<300 {
                let c = lv[rng.below(lv.count)], j = rng.below(c.n)
                let mb = W.member(c, j)
                let t = rng.uniform(mb.J, tNow(model))
                let (dl, _) = SocialCalendar.localDayMinute(t, offsetMinutes: c.off)
                let mid = Double((dl + 1) * 86_400 - c.off * 60)
                if let a = W.progress(c, j, mid - 0.001), let b = W.progress(c, j, mid) { worst = max(worst, b - a) }
            }
            XCTAssertLessThan(worst, 0.01, model)
        }
    }

    // 5. session windows are ordered, non-overlapping, inside the day; fractions sum to 1
    func testSessionWindows() {
        for model in Self.models {
            let W = world(model), lv = live(W, model)
            var rng = SocRNG(45), bad = 0
            for _ in 0..<500 {
                let c = lv[rng.below(lv.count)], dl = rng.below(200)
                guard let s = W.computeSessions(c, dl) else { continue }
                let L = s.f.map { $0 * c.lamMax * s.m / s.pace }
                for k in s.starts.indices {
                    if s.starts[k] < 0 || s.starts[k] + L[k] > 1439.0 + 1e-6 { bad += 1 }
                    if k > 0 && s.starts[k] < s.starts[k - 1] + L[k - 1] + SocialWorldModel.sessionGap - 1e-6 { bad += 1 }
                }
                if abs(s.f.reduce(0, +) - 1.0) > 1e-12 { bad += 1 }
            }
            XCTAssertEqual(bad, 0, model)
        }
    }

    // 6. countAtLeast (per-cohort binary search) == brute force (TR, random times and levels)
    func testCountEqualsBruteForce() {
        for model in Self.models {
            let W = world(model)
            let tr = members(W, "TR", tNow(model))
            var rng = SocRNG(46)
            for _ in 0..<12 {
                let t = rng.uniform(tNow(model) - 60 * 86_400, tNow(model))
                let x = [2, 5, 11, 30, 56, 120, 400, 1500][rng.below(8)]
                var brute = 0
                for (c, j) in tr where W.level(c, j, t) >= x { brute += 1 }
                XCTAssertEqual(W.countAtLeast(x, t, iso: "TR"), brute, "\(model) x \(x)")
            }
        }
    }

    // 7. top-k == brute force (TR) and 8. neighbours consistent with rank
    func testTopAndNeighboursEqualBruteForce() {
        for model in Self.models {
            let W = world(model)
            let t = tNow(model) - 3 * 86_400
            let tr = members(W, "TR", tNow(model))
            var all: [(P: Double, gid: Int)] = []
            for (c, j) in tr { if let P = W.progress(c, j, t) { all.append((P, W.gid(c, j))) } }
            all.sort { $0.P != $1.P ? $0.P > $1.P : $0.gid < $1.gid }
            XCTAssertEqual(W.top(t, 50, iso: "TR").map(\.gid), all.prefix(50).map(\.gid), model)
            for x in [3, 12, 40, 90, 300] {
                let (ab, be) = W.neighbours(x, t, above: 10, below: 10, iso: "TR")
                let la = ab.map { W.level($0.c, $0.j, t) }, lb = be.map { W.level($0.c, $0.j, t) }
                XCTAssertFalse(la.contains { $0 <= x } || lb.contains { $0 > x }, "\(model) x \(x)")
                XCTAssertEqual(la, la.sorted()); XCTAssertEqual(lb, lb.sorted(by: >))
                let want = all.filter { 1 + SocialHash.floorInt($0.P) >= x + 1 }
                if let first = ab.first, let last = want.last { XCTAssertEqual(first.gid, last.gid, "\(model) x \(x): the row above the player") }
                XCTAssertEqual(W.rankOfLevel(x, t, iso: "TR"), 1 + want.count)
            }
        }
    }

    // 8b. PUBLISH B2: the World neighbours' pruned path (the frozen cohorts' K best, the window bounds, the fixed-bracket
    //     straddlers known by exact bounds) = the plain full scan (k > neighbourK takes it) at random moments — daytime and
    //     night, inside local midnight spans and across them — for low and high levels
    func testWorldNeighboursPrunedEqualFullScan() {
        let big = SocialPopulation.neighbourK + 6
        for model in ["v552", "v2"] {
            let W = world(model)
            var rng = SocRNG(48)
            var bad: [String] = [], checked = 0
            for _ in 0..<60 {
                let t = (rng.uniform(tNow(model) - 40 * 86_400, tNow(model))).rounded(.down)
                let x = [3, 12, 40, 62, 150, 400, 1200][rng.below(7)]
                let (a1, b1) = W.neighbours(x, t, above: 26, below: 26)
                let (a2, b2) = W.neighbours(x, t, above: big, below: big)
                if a1.map(\.gid) != Array(a2.prefix(26)).map(\.gid) || b1.map(\.gid) != Array(b2.prefix(26)).map(\.gid) {
                    bad.append("x \(x) t \(t)")
                }
                XCTAssertEqual(a1.map(\.P.bitPattern), Array(a2.prefix(26)).map(\.P.bitPattern))
                checked += 1
            }
            XCTAssertEqual(bad, [], "\(model): pruned vs full World neighbours (\(checked) queries)")
        }
    }

    // 9. the reference: no two players share a nickname (60k, case/accent-insensitive). The shipped world (SOC1c) draws
    //    names with replacement like the original (two "Bobby" in its World top 15): they repeat at the phone's rate
    //    (board-like pair rate inside 1.5e-5 … 3.2e-3, the 95 % interval of its 1 pair in 1,721), no name is longer than
    //    the username rule, identity stays the gid. Neither shows a blocked name. (tests.py #9)
    func testNicknamesUniqueAndClean() {
        for model in Self.models {
            let W = world(model)
            let drawn = W.model.nameStyle.draw != nil
            XCTAssertEqual(drawn, model != "reference")
            var seen = Set<String>(), gids = Set<Int>(), dup = 0, blocked = 0, n = 0, long = 0
            var board: [String: Int] = [:]
            outer: for c in W.cohorts.prefix(1500) {
                for j in 0..<c.n {
                    let (nm, st) = W.name(c, j)
                    let key = SocialNames.key(nm)
                    if !seen.insert(key).inserted { dup += 1 }
                    if c.arch.key != "tourist" { board[key, default: 0] += 1 }
                    gids.insert(W.gid(c, j))
                    if st != "fallback" && SocialNames.isBlocked(nm, bank: F.bank(model)) { blocked += 1 }
                    if drawn && nm.unicodeScalars.count > 16 { long += 1 }
                    n += 1
                    if n > 60_000 { break outer }
                }
            }
            if drawn {
                let nb = Double(board.values.reduce(0, +))
                let q = Double(board.values.reduce(0) { $0 + $1 * ($1 - 1) }) / (nb * (nb - 1))
                XCTAssertTrue((1.5e-5...3.2e-3).contains(q), "\(model): board-like pair rate \(q) over \(Int(nb)) rows")
                XCTAssertGreaterThan(dup, 0, "\(model): drawn names repeat")
                XCTAssertEqual(long, 0, model)
            } else {
                XCTAssertEqual(dup, 0, "\(model): \(n) names")
            }
            XCTAssertEqual(gids.count, n, "\(model): identity = the gid")
            XCTAssertEqual(blocked, 0, model)
            XCTAssertGreaterThan(n, 60_000)
        }
    }

    // 9b. every 'player_' name comes from one bijection with disjoint slot ranges (shared, LOCAL, user, fallbacks)
    func testDefaultNamesOneBijection() {
        var seen = Set<String>()
        var ok = true
        for (base, step) in [(0, 1), (SocialNames.localDefaultBase, 1), (SocialNames.userDefaultBase, 7919), (SocialNames.d36_7 - 80_000, 1)] {
            for i in 0..<20_000 {
                let nm = SocialNames.defaultName(base + i * step)
                ok = ok && seen.insert(nm).inserted && nm.count == 14 && nm.hasPrefix("player_")
            }
        }
        XCTAssertTrue(ok)
    }

    // 10. the shared world does not depend on the install: a LOCAL partition leaves the shared names/levels untouched
    func testLocalPartitionLeavesSharedWorldIdentical() {
        for key in Self.models {
            let model = F.model(key)
            let W = F.world(key)
            W.extend(to: tNow(key))
            // tests.py #10: v2's LOCAL partition exists only for an unknown code (M4): ('ZZ', 0, 'en')
            let lp = key == "v2" ? SocialLocalPartition(iso: "ZZ", offsetMinutes: 0, culture: "en")
                : SocialLocalPartition(iso: "IS", offsetMinutes: 0, culture: "nordic")
            let W2 = SocialPopulation(model: model, local: lp, names: F.bank(key))
            W2.extend(to: tNow(key))
            let shared2 = W2.cohorts.filter { !$0.local }
            for (c, c2) in zip(W.cohorts.prefix(800), shared2.prefix(800)) {
                XCTAssertEqual([c.ck, c.n, c.gid0], [c2.ck, c2.n, c2.gid0])
                if c.n > 0 {
                    let j = c.n / 2
                    XCTAssertEqual(W.name(c, j).name, W2.name(c2, j).name)
                    XCTAssertEqual(W.level(c, j, tNow(key)), W2.level(c2, j, tNow(key)))
                }
            }
            XCTAssertGreaterThan(W2.cohorts.filter(\.local).count, 0)
        }
    }

    // 11. Sky Jump: players never increase, winners in [3, 12] (reference) / the stage's range (shipped), share = pool /
    //     winners; shipped: no drop before the stage's first step, then 8-16 per level (phone session 2: 8-13 of 100;
    //     stage 3 = 10 levels, 8-9 a level, SOC1c)
    func testSkyJumpCurve() {
        for a in 0..<300 {
            let sj = SocialSkyJump(installSeed: 99, attemptId: a, stage: 1 + a % 3)
            XCTAssertTrue(zip(sj.alive, sj.alive.dropFirst()).allSatisfy { $0 >= $1 })
            XCTAssertTrue((3...12).contains(sj.alive.last!), "\(sj.alive)")
            XCTAssertEqual(sj.share, sj.pool / sj.alive.last!)
            XCTAssertEqual(sj.alive.count, sj.N + 1)
            let stage = 1 + a % 3
            let v = SocialSkyJump(installSeed: 99, attemptId: a, stage: stage, spec: .shipped)
            let dr = SocialSkySpec.shipped.drops![stage - 1]
            XCTAssertTrue(zip(v.alive, v.alive.dropFirst()).allSatisfy { $0 >= $1 })
            XCTAssertTrue((dr.wlo...dr.whi).contains(v.alive.last!), "\(v.alive)")
            XCTAssertEqual(v.share, v.pool / v.alive.last!)
            XCTAssertEqual(v.alive.count, v.N + 1)
            let drops = (1..<v.N).map { v.alive[$0 - 1] - v.alive[$0] }
            XCTAssertTrue(drops.prefix(dr.first - 1).allSatisfy { $0 == 0 }, "\(v.alive)")
            XCTAssertTrue(drops.dropFirst(dr.first - 1).allSatisfy { $0 >= Int(dr.lo) - 1 && $0 <= Int(dr.hi) + 2 }, "\(v.alive)")
        }
        // the phone's run: 100 → … and 5000 / 7 = 714 is a reachable outcome of the curve's arithmetic
        XCTAssertEqual(5000 / 7, 714)
    }

    // 12. Rocket Race: rival progress monotone in time; a finish time never moves into the past
    func testRocketMonotoneAndPastStable() {
        for model in Self.models {
            let W = world(model)
            var rng = SocRNG(47)
            for a in 0..<20 {
                let t0 = tNow(model) - rng.uniform(0, 20) * 86_400
                let rr = SocialRocketRace(W: W, installSeed: 5, raceId: a, stage: 1, t0: t0, secondsPerWin: 110,
                                          spec: model == "reference" ? .reference : .shipped)
                for i in rr.rivals.indices {
                    var prev = -1
                    for m in stride(from: 0, to: 240, by: 3) {
                        let p = rr.rivalProgress(i, t0 + Double(m) * 60, userNminus1: nil)
                        XCTAssertGreaterThanOrEqual(p, prev); prev = p
                    }
                }
                let un = t0 + 1800
                for i in rr.rivals.indices {
                    if let fb = rr.finishTime(i, userNminus1: nil), fb <= un {
                        XCTAssertEqual(rr.finishTime(i, userNminus1: un), fb, "\(model) race \(a) rival \(i)")
                    }
                }
            }
        }
    }

    // 12b. group contests: member scores monotone, standings sorted with the user exactly once, groups only grow
    func testGroupContests() {
        for (model, cfg) in [("reference", SocialConfig.reference), ("v552", SocialConfig.default), ("v2", SocialConfig.default)] {
            let W = world(model)
            for spec in [cfg.weekly, cfg.streak] {
                for inst in 0..<3 {
                    let t0 = tNow(model) - Double(inst) * 2 * 86_400 - 3600 * 5
                    let instance = spec.kind == .weekly ? SocialCalendar.eventWeek(t0) : SocialCalendar.eventDay(t0)
                    let g = SocialGroupContest(W: W, installSeed: UInt64(11 + inst), spec: spec,
                                               key: SocialGroupKey(instance: instance, t0: t0, ref: spec.kind == .weekly ? 90 : 15))
                    XCTAssertEqual(g.members.count, spec.groupSize - 1, "\(model) \(spec.kind)")
                    var prevRows = 0
                    var prevScores = [Int?](repeating: nil, count: g.members.count)
                    var h = 0
                    while t0 + Double(h) * 3600 <= g.we {
                        let t = t0 + Double(h) * 3600
                        let st = g.standings(t, userScore: 0, userReached: t0)
                        XCTAssertEqual(st.filter { $0.member == nil }.count, 1)
                        let keys = st.map { (-$0.score, $0.reached) }
                        XCTAssertTrue(zip(keys, keys.dropFirst()).allSatisfy { $0.0 < $1.0 || ($0.0 == $1.0 && $0.1 <= $1.1) })
                        if spec.tieByName {
                            // shipped Streak Race: equal scores listed alphabetically (case/accent-insensitive), the user too
                            let sn = g.standings(t, userScore: 0, userReached: t0, userName: "Hsheh")
                            XCTAssertEqual(sn.filter { $0.member == nil }.count, 1)
                            let nk = sn.map { r -> (Int, [UInt32]) in
                                (-r.score, SocialGroupContest.sortKey(r.member.map { W.name(g.members[$0].0, g.members[$0].1).name } ?? "Hsheh"))
                            }
                            XCTAssertTrue(zip(nk, nk.dropFirst()).allSatisfy { $0.0 < $1.0 || ($0.0 == $1.0 && !$1.1.lexicographicallyPrecedes($0.1)) },
                                          "\(model) name order at +\(h) h")
                        }
                        XCTAssertGreaterThanOrEqual(st.count, prevRows); prevRows = st.count
                        for i in g.members.indices {
                            let sc = g.memberScore(i, t)
                            if let p = prevScores[i] { XCTAssertNotNil(sc); XCTAssertGreaterThanOrEqual(sc ?? -1, p) }
                            prevScores[i] = sc
                        }
                        h += 3
                    }
                }
            }
        }
    }

    // 12c. clock set back: displayed levels never decrease; a > 30-day repair rebases exactly once
    func testClockNeverRewindsAndRebasesOnce() {
        for model in Self.models {
            let W = world(model)
            let lv = live(W, model)
            let players = stride(from: 0, to: lv.count, by: 97).map { lv[$0] }.filter { $0.n > 0 }.prefix(40).map { ($0, $0.n / 2) }
            var high: Int64 = 0
            var prev: [Int: Int] = [:]
            var rebased = 0
            let T = tNow(model)
            let hours: [Double] = [-5, -4, -7, -6, -3, -72, 0]
            for dev in hours.map({ T + $0 * 3600 }) {
                let r = SocialClockRules.advance(wall: Date(timeIntervalSince1970: dev), highWater: &high)
                if r.rebased { rebased += 1 }
                for (c, j) in players {
                    let L = W.level(c, j, Double(r.time.seconds))
                    XCTAssertGreaterThanOrEqual(L, prev[W.gid(c, j)] ?? 0, model)
                    prev[W.gid(c, j)] = L
                }
            }
            XCTAssertEqual(rebased, 0)
            XCTAssertGreaterThan(players.count, 20, "\(model): players sampled")
            var high2 = Int64(T) + 400 * 86_400
            let r2 = SocialClockRules.advance(wall: Date(timeIntervalSince1970: T), highWater: &high2)
            XCTAssertTrue(r2.rebased)
            XCTAssertEqual(r2.time.seconds, Int64(T))
            XCTAssertFalse(SocialClockRules.advance(wall: Date(timeIntervalSince1970: T + 1), highWater: &high2).rebased)
        }
    }

    // 13. the streak ladder: 1, 5, 10, 25, 100, 100, 100, then a fail resets to 1
    func testStreakLadder() {
        var s = SocialWinStreak()
        var pts = (0..<7).map { _ in s.win() }
        s.fail()
        pts.append(s.win())
        XCTAssertEqual(pts, [1, 5, 10, 25, 100, 100, 100, 1])
    }

    // 14. event calendar: days start 07:00 UTC, weeks Monday 07:00 UTC
    func testEventCalendarBoundaries() {
        let d = SocialCalendar.eventDay(1_790_319_599), d2 = SocialCalendar.eventDay(1_790_319_600)   // 25 Sep 06:59:59 / 07:00
        let w1 = SocialCalendar.eventWeek(1_790_578_740), w2 = SocialCalendar.eventWeek(1_790_578_800) // 28 Sep 06:59 / 07:00
        XCTAssertEqual(d2, d + 1)
        XCTAssertEqual(w2, w1 + 1)
        let start = Date(timeIntervalSince1970: TimeInterval(SocialCalendar.eventWeekStart(w2)))
        var cal = Calendar(identifier: .gregorian); cal.timeZone = TimeZone(identifier: "UTC")!
        XCTAssertEqual(cal.component(.weekday, from: start), 2)   // Monday
        XCTAssertEqual(cal.component(.hour, from: start), 7)
        XCTAssertEqual(SocialCalendar.countdown(seconds: 3 * 86_400 + 6 * 3600 + 59).big, 3)
        XCTAssertTrue(SocialCalendar.countdown(seconds: 9 * 3600 + 50 * 60 + 30) == (9, 50, false))
    }

    // ------------------------------------------------------------ Swift-only: rewind at the API, state, ledger

    /// §12.2 "the rewind test": with the device clock behind the high-water mark the world shown is frozen at the mark
    /// (identical pages), and it moves again once wall time passes it.
    func testRewindFreezesTheWorld() {
        let world = SocialWorld(installSeed: 7, config: .default, names: F.bank)
        let me = PlayerStanding(name: "Hsheh", avatar: 3, country: "TR", level: 62, ledger: [])
        var high: Int64 = 0
        let t1 = Date(timeIntervalSince1970: 1_790_300_000)
        let a = SocialClock.now(wall: t1, highWater: &high)
        let pageA = world.page(.country("TR"), me: me, at: a, around: 400, radius: 12)
        let backs: [Double] = [60, 3600, 86_400, 1_728_000]
        for back in backs {
            let b = SocialClock.now(wall: t1.addingTimeInterval(-back), highWater: &high)
            XCTAssertEqual(b, a, "set back \(back) s: the world time stays at the high-water mark")
            let pageB = world.page(.country("TR"), me: me, at: b, around: 400, radius: 12)
            XCTAssertEqual(pageB.rows, pageA.rows)
            XCTAssertEqual(pageB.myRank, pageA.myRank)
        }
        let later = SocialClock.now(wall: t1.addingTimeInterval(6 * 3600), highWater: &high)
        XCTAssertGreaterThan(later, a)
        let pageC = world.page(.world, me: me, at: later, ranks: 1...30)
        let pageA2 = world.page(.world, me: me, at: a, ranks: 1...30)
        let before = Dictionary(uniqueKeysWithValues: pageA2.rows.map { ($0.player.id, $0.value) })
        for r in pageC.rows { if let v = before[r.player.id] { XCTAssertGreaterThanOrEqual(r.value, v, "nothing moves backwards") } }
    }

    func testSocialStateRoundTripAndOldSaves() throws {
        // the WP0 v1 shape still decodes
        let old = #"{"username":null,"avatar":2,"country":"TR","highWater":1790300000,"ledger":[{"at":{"seconds":1790299000},"level":61,"score":100}]}"#
        let s = try JSONDecoder().decode(SocialState.self, from: Data(old.utf8))
        XCTAssertEqual(s.avatar, 2); XCTAssertEqual(s.ledger.first?.kind, .win); XCTAssertTrue(s.ledger.first?.firstTry ?? false)
        XCTAssertEqual(try JSONDecoder().decode(SocialState.self, from: Data("{}".utf8)), SocialState())
        var st = SocialState()
        st.setHomeIfNeeded(region: "tr", offsetMinutes: 180)
        st.setHomeIfNeeded(region: "US", offsetMinutes: -300)            // frozen at first launch
        XCTAssertEqual(st.country, "TR"); XCTAssertEqual(st.offsetMinutes, 180)
        let t0: Int64 = 1_790_280_000
        for k in 0..<30 { st.recordWin(level: 40 + k, firstTry: k % 4 != 0, points: [1, 5, 10, 25, 100][min(k, 4)], at: SocialTime(seconds: t0 + Int64(k) * 150)) }
        st.recordFail(level: 70, at: SocialTime(seconds: t0 + 5000))
        let key = st.joinWeekly(week: 21, level: 70, at: SocialTime(seconds: t0 + 6000))
        XCTAssertEqual(st.joinWeekly(week: 21, level: 71, at: SocialTime(seconds: t0 + 9000)), key, "idempotent")
        XCTAssertEqual(st.weeklyKey(week: 21), key)
        let data = try JSONEncoder().encode(st)
        XCTAssertEqual(try JSONDecoder().decode(SocialState.self, from: data), st)
    }

    func testLedgerCapKeepsCurrentJoinMarkers() {
        var st = SocialState()
        let t0: Int64 = 1_790_280_000
        let week = SocialCalendar.eventWeek(Int(t0)), day = SocialCalendar.eventDay(Int(t0))
        st.joinWeekly(week: week, level: 60, at: SocialTime(seconds: t0))
        st.joinStreak(day: day, level: 60, at: SocialTime(seconds: t0))
        for k in 0..<1000 { st.recordWin(level: 60 + k, firstTry: true, points: 100, at: SocialTime(seconds: t0 + 10 + Int64(k) * 60)) }
        XCTAssertLessThanOrEqual(st.ledger.count, SocialState.ledgerCap)
        XCTAssertNotNil(st.weeklyKey(week: week), "the current week's marker survives the cap")
        XCTAssertNotNil(st.streakKey(day: day))
        XCTAssertEqual(st.winsByWeek[week], 1000, "the aggregates keep counting what the ledger dropped")
    }
}
