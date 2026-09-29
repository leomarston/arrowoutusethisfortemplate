import XCTest
@testable import PathCore

// SOC1 (SPEC-social §9; the orchestrator's acceptance: "the 52-week bench (active / casual / absent user)"). A Swift port
// of design/social/tools/bench.py driving the SHIPPED world (PUBLISH B2: the v2 world; SOC1 ran it on the calibrated v552
// model) with the phone's event shapes (Weekly = 10 players,
// Streak Race = 50 rows): one simulated user per profile for 52 weeks from 5 Oct 2026, with a lives model, first-try
// rates and Hard/Super Hard pacing, every event joined when offered; it records what the screens would show and checks
// the invariants (no backwards jumps, no duplicate rows, country rank <= world rank). The user's behaviour uses its own
// seeded RNG (it is not part of the pinned model). Opt-in (a few seconds under -O, minutes in Debug):
//     SOC1_BENCH_DIR=<dir> swift test -c release -Xswiftc -enable-testing --filter SocialBenchTests
// Writes <dir>/{active,casual,absent}.json + summary.json.

final class SocialBenchTests: XCTestCase {
    typealias F = SocFix

    struct Profile {
        let name: String, iso: String, off: Int, playP: Double?, sessions: (Int, Int), minutes: (Double, Double)
        let first: Double, hardFirst: Double, seedSalt: Int
    }
    static let profiles = [
        Profile(name: "active", iso: "TR", off: 180, playP: 0.97, sessions: (2, 4), minutes: (12, 35), first: 0.88, hardFirst: 0.72, seedSalt: 1),
        Profile(name: "casual", iso: "US", off: -300, playP: 0.62, sessions: (1, 2), minutes: (6, 16), first: 0.80, hardFirst: 0.60, seedSalt: 2),
        Profile(name: "absent", iso: "GB", off: 0, playP: nil, sessions: (1, 2), minutes: (8, 20), first: 0.82, hardFirst: 0.62, seedSalt: 3),
    ]

    static func isHard(_ l: Int) -> Bool { [19, 25, 34, 44, 54].contains(l) || (l > 54 && l % 5 == 4) }
    static func isSuper(_ l: Int) -> Bool { [29, 39, 49].contains(l) || (l > 54 && l % 10 == 9) }
    /// absent: 3 active weeks, 4 away, 1 back (every other day), 6 away, then one day a fortnight.
    static func absentPlays(_ d: Int) -> Bool {
        let w = d / 7
        if w < 3 { return true }
        if w < 7 { return false }
        if w < 8 { return d % 2 == 0 }
        if w < 14 { return false }
        return d % 14 == 0
    }

    struct UserRNG {
        var r: SocRNG
        mutating func random() -> Double { SocialHash.unit(r.next()) }
        mutating func randint(_ a: Int, _ b: Int) -> Int { a + r.below(b - a + 1) }
        mutating func uniform(_ a: Double, _ b: Double) -> Double { a + (b - a) * random() }
        mutating func gauss(_ mu: Double, _ sigma: Double) -> Double {
            let u1 = max(random(), 1e-300), u2 = random()
            return mu + sigma * (-2 * log(u1)).squareRoot() * cos(2 * Double.pi * u2)
        }
    }

    func testFiftyTwoWeekBench() throws {
        guard let dir = ProcessInfo.processInfo.environment["SOC1_BENCH_DIR"], !dir.isEmpty else {
            throw XCTSkip("set SOC1_BENCH_DIR to run the 52-week bench")
        }
        let weeks = Int(ProcessInfo.processInfo.environment["SOC1_BENCH_WEEKS"] ?? "") ?? 52
        // SOC1_BENCH_MODEL=reference runs the prototype's world + event shapes (to compare with design/social/bench)
        let reference = ProcessInfo.processInfo.environment["SOC1_BENCH_MODEL"] == "reference"
        let prefix = reference ? "reference-" : ""
        try FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        var all: [String: Any] = [:]
        var namePairs = 0, rowPairs = 0
        for p in Self.profiles {
            let res = runBench(p, weeks: weeks, reference: reference)
            let data = try JSONSerialization.data(withJSONObject: res, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: URL(fileURLWithPath: dir).appendingPathComponent("\(prefix)\(p.name).json"))
            let summary = res["summary"] as! [String: Any]
            all[p.name] = summary
            let checks = summary["checks"] as! [String: Int]
            XCTAssertEqual(checks["backwards"], 0, "\(p.name): a row went backwards")
            XCTAssertEqual(checks["dup_rows"], 0, "\(p.name): a duplicate row")
            XCTAssertEqual(checks["rank_inconsistent"], 0, "\(p.name): country rank > world rank")
            XCTAssertEqual(checks["api_bad_pages"], 0, "\(p.name): a ◆ page broke its invariants")
            namePairs += checks["name_repeat_pairs"] ?? 0
            rowPairs += checks["row_pairs"] ?? 0
        }
        // SOC1c: two players on one board may share a NAME (drawn names, the original's two "Bobby"), at the phone's rate:
        // the pooled pair rate of every board the three users saw stays inside the 95 % interval of the phone's 1 repeated
        // pair in 1,721 row pairs (1.5e-5 … 3.2e-3; the lower bound only over the full 52 weeks, where the sample is
        // ~400k row pairs). The reference world's unique first-come names never repeat.
        let nameRate = Double(namePairs) / Double(max(1, rowPairs))
        if reference {
            XCTAssertEqual(namePairs, 0, "reference: unique names never repeat on a board")
        } else {
            XCTAssertLessThanOrEqual(nameRate, 3.2e-3, "repeated names on the boards: \(namePairs) pairs in \(rowPairs)")
            if weeks >= 52 {
                XCTAssertGreaterThanOrEqual(nameRate, 1.5e-5, "repeated names on the boards: \(namePairs) pairs in \(rowPairs)")
            }
        }
        all["nameRepeats"] = ["pairs": namePairs, "rowPairs": rowPairs, "rate": nameRate] as [String: Any]
        let data = try JSONSerialization.data(withJSONObject: all, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: URL(fileURLWithPath: dir).appendingPathComponent("\(prefix)summary.json"))
    }

    // swiftlint:disable:next function_body_length cyclomatic_complexity
    func runBench(_ prof: Profile, weeks: Int, reference: Bool = false) -> [String: Any] {
        typealias C = SocialCalendar
        var cfg = reference ? SocialConfig.reference : SocialConfig.default
        // tuning aid: SOC1_BENCH_STREAK_BANDS='[[count, lo, hi, sameHours], …]' tries other Streak Race bands
        if let raw = ProcessInfo.processInfo.environment["SOC1_BENCH_STREAK_BANDS"],
           let arr = try? JSONSerialization.jsonObject(with: Data(raw.utf8)) as? [[Double]] {
            cfg.streak.bands = arr.map { SocialBand(Int($0[0]), $0[1], $0[2], $0[3] != 0) }
        }
        if let v = Double(ProcessInfo.processInfo.environment["SOC1_BENCH_STREAK_MINTARGET"] ?? "") { cfg.streak.minTarget = v }
        if let v = ProcessInfo.processInfo.environment["SOC1_BENCH_STREAK_PERPLAYDAY"] { cfg.streak.expectedPerPlayDay = v == "1" }
        var rng = UserRNG(r: SocRNG(UInt64(7 * 1000 + prof.seedSalt)))
        let tInstall = 1_791_223_200.0                          // 2026-10-05 18:00 UTC
        let installSeed = SocialHash.h64(7, "install", [7])
        let W = SocialPopulation(model: cfg.model, names: F.bank(for: cfg.model))
        W.extend(to: tInstall)
        let api = SocialWorld(installSeed: installSeed, config: cfg, names: F.bank(for: cfg.model))
        let iso = prof.iso, off = prof.off

        var level = 1, lives = 5
        var lifeClock: Double? = nil
        let infUntil = 0.0
        var streak = SocialWinStreak()
        var wins: [(t: Double, level: Int, firstTry: Bool)] = []
        var fails = 0
        var firstTryLevel = true
        var weekly: SocialGroupContest? = nil, weeklyW = 0, weeklyUser = 0
        var weeklyLastWin: Double? = nil
        var weeklyResults: [[String: Any]] = []
        var weeklyPace: [[String: Any]] = []
        var streakRace: SocialGroupContest? = nil, streakDay: Int? = nil, streakUser = 0
        var streakLast: Double? = nil
        var streakResults: [[String: Any]] = []
        var streakShapes: [[String: Any]] = []
        var rocket: SocialRocketRace? = nil, rocketTimes: [Double] = [], rocketStage = 1, rocketId = 0, rocketCool = 0.0
        var rocketResults: [[String: Any]] = []
        var rocketDayJoined: Int? = nil, rocketStarts = 0, skyRuns = 0
        var sky: SocialSkyJump? = nil, skyStep = 0, skyStage = 1, skyId = 0, skyCool = 0.0, skyT0 = 0.0
        var skyResults: [[String: Any]] = []
        var ranks: [[Any]] = []
        var dynamics: [[String: Any]] = []
        var checks: [String: Int] = ["backwards": 0, "dup_rows": 0, "rank_inconsistent": 0, "views": 0, "api_bad_pages": 0, "api_pages": 0,
                                     "name_repeat_views": 0, "name_repeat_pairs": 0, "row_pairs": 0]
        var seenLevels: [Int: Int] = [:]
        var idle: [[String: Any]] = []
        var lastView: (t: Double, level: Int, below: [(SocialCohort, Int)], window: [(SocialCohort, Int)])? = nil
        var topPrev: [Int]? = nil
        var topChurn: [[String: Any]] = []
        var weeklyDyn: [[String: Any]] = []
        var playWindows: [[Double]] = []
        var ledger: [LedgerEntry] = []

        func refill(_ t: Double) {
            while lives < 5, let lc = lifeClock, t >= lc {
                lives += 1
                lifeClock = lives < 5 ? lc + 1200 : nil
            }
        }
        func showRows(_ rows: [(gid: Int, name: String, level: Int)]) {
            // a duplicate ROW = the same player twice (identity = the gid). SOC1c: two players may share a NAME (drawn names,
            // like the original's two "Bobby"): counted as a statistic, not an invariant
            if Set(rows.map(\.gid)).count != rows.count { checks["dup_rows"]! += 1 }
            var cnt: [String: Int] = [:]
            for r in rows { cnt[SocialNames.key(r.name), default: 0] += 1 }
            let p = cnt.values.reduce(0) { $0 + $1 * ($1 - 1) / 2 }
            if p > 0 { checks["name_repeat_views"]! += 1 }
            checks["name_repeat_pairs"]! += p
            checks["row_pairs"]! += rows.count * (rows.count - 1) / 2
            for r in rows {
                if let prev = seenLevels[r.gid], r.level < prev { checks["backwards"]! += 1 }
                seenLevels[r.gid] = r.level
            }
            checks["views"]! += 1
        }
        func rowsOf(_ refs: [SocialPopulation.Ref], _ t: Double) -> [(gid: Int, name: String, level: Int)] {
            refs.map { (W.gid($0.c, $0.j), W.name($0.c, $0.j).name, W.level($0.c, $0.j, t)) }
        }
        func settleWeekly(_ now: Double) {
            guard let g = weekly, now >= g.we else { return }
            let st = g.standings(g.we, userScore: weeklyUser, userReached: weeklyLastWin ?? g.t0)
            let rank = (st.firstIndex { $0.member == nil } ?? 0) + 1
            weeklyResults.append(["week": weeklyW, "rank": rank, "size": st.count, "user": weeklyUser, "top": st[0].score,
                                  "third": st.count > 2 ? st[2].score : 0,
                                  "prize": rank <= cfg.weekly.prizes.count ? cfg.weekly.prizes[rank - 1] : 0])
            weekly = nil
        }
        func settleStreak(_ now: Double) {
            guard let g = streakRace, now >= g.we else { return }
            let st = g.standings(g.we, userScore: streakUser, userReached: streakLast ?? g.t0, userName: "BenchUser")
            let rank = (st.firstIndex { $0.member == nil } ?? 0) + 1
            streakResults.append(["day": streakDay ?? 0, "rank": rank, "size": st.count, "user": streakUser, "top": st[0].score,
                                  "prize": rank <= cfg.streak.prizes.count ? cfg.streak.prizes[rank - 1] : 0])
            streakRace = nil
        }
        func rocketCheck(_ now: Double) {
            guard let r = rocket else { return }
            let (res, tf) = r.outcome(userTimes: rocketTimes)
            if res == .win || ((res == .lose || res == .none) && tf <= now) {
                rocketResults.append(["stage": rocketStage, "result": res.rawValue, "wins": rocketTimes.count,
                                      "minutes": ((tf - r.t0) / 6).rounded() / 10])
                if res == .win && rocketStage < 3 { rocketStage += 1 }
                else if res == .win { rocketStage = 1; rocketCool = Double(C.eventDayStart(C.eventDay(tf) + 1)) }
                else { rocketStage = 1; rocketCool = tf }
                rocket = nil
            }
        }

        let nDays = weeks * 7
        let tStartWall = Date()
        for di in 0..<nDays {
            let dayStartLocal = tInstall - Double(SocialHash.posMod(Int(tInstall) + off * 60, 86_400)) + Double(di * 86_400)
            W.extend(to: dayStartLocal + 2 * 86_400)
            var plays = prof.playP == nil ? Self.absentPlays(di) : rng.random() < prof.playP!
            if di == 0 { plays = true }
            var sessions: [Double] = []
            if plays {
                let k = rng.randint(prof.sessions.0, prof.sessions.1)
                for _ in 0..<k {
                    let x = rng.random()
                    let cdf = SocialWorldModel.diurnalCDF[0]
                    var h = 0
                    while h < 23 && cdf[h + 1] <= x { h += 1 }
                    sessions.append(dayStartLocal + Double(Int((Double(h) + rng.random()) * 3600)))
                }
                if di == 0 { sessions = [tInstall] }
                sessions.sort()
            }
            let sampledDyn = di % 3 == 0
            for (si, s0) in sessions.enumerated() {
                var t = s0
                settleWeekly(t); settleStreak(t); rocketCheck(t)
                refill(t)
                let dur = rng.uniform(prof.minutes.0, prof.minutes.1) * 60
                let sEnd = s0 + dur
                let ed = C.eventDay(t)
                if level >= cfg.unlocks.streakRace && streakDay != ed {
                    settleStreak(t)
                    let pace = SocialPace.of(wins: wins, at: t)
                    streakRace = SocialGroupContest(W: W, installSeed: installSeed, spec: cfg.streak,
                                                    key: SocialGroupKey(instance: ed, t0: t, ref: pace.daily, windows: playWindows))
                    streakDay = ed; streakUser = 0; streakLast = nil
                }
                if rocketDayJoined != ed { rocketDayJoined = ed; rocketStarts = 0; skyRuns = 0 }
                if level >= cfg.unlocks.rocketRace && rocket == nil && t >= rocketCool && (rocketStage > 1 || rocketStarts < 99) {
                    if rocketStage == 1 { rocketStarts += 1 }
                    let pace = SocialPace.of(wins: wins, at: t)
                    rocketId += 1
                    rocket = SocialRocketRace(W: W, installSeed: installSeed, raceId: rocketId, stage: rocketStage, t0: t,
                                              secondsPerWin: pace.secondsPerWin, spec: cfg.rocket)
                    rocketTimes = []
                }
                if level >= cfg.unlocks.skyJump && sky == nil && t >= skyCool && (skyStage > 1 || skyRuns < 2) {
                    if skyStage == 1 { skyRuns += 1 }
                    skyId += 1
                    sky = SocialSkyJump(installSeed: installSeed, attemptId: skyId, stage: skyStage, spec: cfg.sky)
                    skyStep = 0; skyT0 = t
                }
                if let lv = lastView, si == 0 {
                    let passed = lv.below.filter { W.level($0.0, $0.1, t) > level }.count
                    let moved = lv.window.filter { W.level($0.0, $0.1, t) > W.level($0.0, $0.1, lv.t) }.count
                    idle.append(["hours": ((t - lv.t) / 360).rounded() / 10, "passed_user": passed, "window_moved": moved])
                }
                var dyn: (below: [(SocialCohort, Int)], above: [(SocialCohort, Int)], startLevel: Int, rank0: Int)? = nil
                if sampledDyn && si == 0 {
                    let (ab, be) = W.neighbours(level, t, above: 6, below: 6, iso: iso)
                    showRows(rowsOf(ab + be, t))
                    dyn = (be.map { ($0.c, $0.j) }, ab.map { ($0.c, $0.j) }, level, W.rankOfLevel(level, t, iso: iso))
                    // the same view through the ◆ API: the player's row sits at myRank, levels never rise going down
                    let me = PlayerStanding(name: "BenchUser", avatar: 0, country: iso, level: level, ledger: ledger)
                    let page = api.page(.country(iso), me: me, at: SocialTime(seconds: Int64(t)), around: dyn!.rank0, radius: 10)
                    let lv = page.rows.map(\.value)
                    let meRow = page.rows.first { $0.isMe }
                    if page.myRank != dyn!.rank0 || meRow?.rank != page.myRank || zip(lv, lv.dropFirst()).contains(where: { $0 < $1 })
                        || Set(page.rows.map(\.rank)).count != page.rows.count {
                        checks["api_bad_pages"]! += 1
                    }
                    checks["api_pages"]! += 1
                }
                var wkSnap: (t: Double, scores: [Int?], st: [SocialStandingRow])? = nil
                if let g = weekly, sampledDyn, si == 0 {
                    wkSnap = (t, g.members.indices.map { g.memberScore($0, t) }, g.standings(t, userScore: weeklyUser, userReached: weeklyLastWin ?? g.t0))
                }
                // play
                while t < sEnd {
                    refill(t)
                    if lives <= 0 && t >= infUntil { break }
                    let hard = Self.isHard(level), sup = Self.isSuper(level)
                    let med = !(hard || sup) ? 95.0 : (hard ? 150.0 : 185.0)
                    var d = med * exp(rng.gauss(0, 0.35))
                    if level == 1 { d = 30 }
                    t += d
                    var p = !(hard || sup) ? prof.first : prof.hardFirst
                    if !firstTryLevel { p = min(0.97, p + 0.1) }
                    if rng.random() < p {
                        let lw = level
                        wins.append((t, lw, firstTryLevel))
                        let pts = streak.win()
                        ledger.append(LedgerEntry(at: SocialTime(seconds: Int64(t)), level: lw, score: pts, kind: .win, firstTry: firstTryLevel))
                        if ledger.count > 400 { ledger.removeFirst(ledger.count - 400) }
                        level = level == 1 ? 5 : level + 1
                        if let g = streakRace, t < g.we { streakUser += pts; streakLast = t }
                        if lw >= cfg.unlocks.weeklyContest {
                            let w = C.eventWeek(t)
                            if weekly != nil && w != weeklyW { settleWeekly(t) }
                            if weekly == nil {
                                let pace = SocialPace.of(wins: wins, at: t)
                                let g = SocialGroupContest(W: W, installSeed: installSeed, spec: cfg.weekly,
                                                           key: SocialGroupKey(instance: w, t0: t, ref: pace.weekly, windows: playWindows))
                                weekly = g; weeklyW = w; weeklyUser = 0
                                // the phone saw the top rival gain +23 in 85 min and +43 in 3.5 h after the join
                                func gain(_ h: Double) -> [Int] {
                                    g.members.indices.map { (g.memberScore($0, t + h * 3600) ?? 0) - (g.memberScore($0, t) ?? 0) }.sorted(by: >)
                                }
                                weeklyPace.append(["week": w, "size": g.members.count + 1,
                                                   "atJoin": g.members.indices.map { g.memberScore($0, t) ?? -1 }.sorted(by: >),
                                                   "gain85min": gain(85.0 / 60), "gain3h30": gain(3.5)])
                            }
                            weeklyUser += 1; weeklyLastWin = t
                        }
                        if rocket != nil { rocketTimes.append(t); rocketCheck(t) }
                        if let sj = sky, firstTryLevel {
                            skyStep += 1
                            if skyStep >= sj.N {
                                skyResults.append(["stage": skyStage, "result": "win", "winners": sj.alive[sj.N], "share": sj.share])
                                if skyStage < 3 { skyStage += 1 } else { skyStage = 1; skyCool = Double(C.eventDayStart(C.eventDay(t) + 1)) }
                                sky = nil
                            }
                        }
                        firstTryLevel = true
                    } else {
                        fails += 1
                        firstTryLevel = false
                        streak.fail()
                        ledger.append(LedgerEntry(at: SocialTime(seconds: Int64(t)), level: level, score: 0, kind: .fail))
                        if t >= infUntil {
                            lives -= 1
                            if lifeClock == nil { lifeClock = t + 1200 }
                        }
                        if let sj = sky {
                            skyResults.append(["stage": skyStage, "result": "lose", "step": skyStep, "alive": sj.alive[skyStep]])
                            sky = nil; skyStage = 1; skyCool = t + 1800      // SKY_RETRY_COOLDOWN
                        }
                    }
                    if sky != nil && t - skyT0 > 86_400 {
                        skyResults.append(["stage": skyStage, "result": "expired", "step": skyStep])
                        sky = nil; skyStage = 1
                    }
                }
                // session end
                if let dy = dyn {
                    let (ab2, be2) = W.neighbours(level, t, above: 6, below: 6, iso: iso)
                    showRows(rowsOf(ab2 + be2, t))
                    let overtook = dy.below.filter { W.level($0.0, $0.1, t) > level }.count
                    let moved = (dy.below + dy.above).filter { W.level($0.0, $0.1, t) > W.level($0.0, $0.1, s0) }.count
                    let r1 = W.rankOfLevel(level, t, iso: iso)
                    dynamics.append(["minutes": ((t - s0) / 6).rounded() / 10, "levels": level - dy.startLevel,
                                     "rank_gain": dy.rank0 - r1, "overtaken_by": overtook, "neighbours_moved": moved])
                }
                if let snap = wkSnap, let g = weekly, t < g.we {
                    let scB = g.members.indices.map { g.memberScore($0, t) }
                    let stB = g.standings(t, userScore: weeklyUser, userReached: weeklyLastWin ?? g.t0)
                    var posA: [Int: Int] = [:], posB: [Int: Int] = [:]
                    for (k, r) in snap.st.enumerated() { posA[r.member ?? -1] = k }
                    for (k, r) in stB.enumerated() { posB[r.member ?? -1] = k }
                    let changed = g.members.indices.filter { snap.scores[$0] != nil && scB[$0] != nil && scB[$0]! > snap.scores[$0]! }.count
                    let passed = posA.keys.filter { $0 >= 0 && posB[$0] != nil && posA[$0]! > posA[-1]! && posB[$0]! < posB[-1]! }.count
                    weeklyDyn.append(["minutes": ((t - snap.t) / 6).rounded() / 10, "members_scored": changed, "passed_user": passed,
                                      "user_rank_before": posA[-1]! + 1, "user_rank_after": posB[-1]! + 1])
                }
                if let g = streakRace, t >= g.ws + 18.5 * 3600, t <= g.ws + 19.5 * 3600, streakShapes.count < 60 {
                    let st = g.standings(t, userScore: streakUser, userReached: streakLast ?? g.t0, userName: "BenchUser")
                    streakShapes.append(["day": g.key.instance, "hoursIntoDay": ((t - g.ws) / 360).rounded() / 10,
                                         "scores": st.map(\.score), "userRank": (st.firstIndex { $0.member == nil } ?? 0) + 1])
                }
                if t > s0 { playWindows.append([s0, t]); if playWindows.count > 10 { playWindows.removeFirst() } }
                if si == sessions.count - 1 {
                    let (ab3, be3) = W.neighbours(level, t, above: 10, below: 10, iso: iso)
                    lastView = (t, level, be3.map { ($0.c, $0.j) }, (ab3 + be3).map { ($0.c, $0.j) })
                }
            }
            // end of day
            let tDayEnd = dayStartLocal + 86_399
            settleWeekly(tDayEnd); settleStreak(tDayEnd); rocketCheck(tDayEnd)
            let wr = W.rankOfLevel(level, tDayEnd), cr = W.rankOfLevel(level, tDayEnd, iso: iso)
            if cr > wr { checks["rank_inconsistent"]! += 1 }
            ranks.append([tDayEnd, level, wr, cr])
            if di % 28 == 0 {
                let tp = W.top(tDayEnd, 100)
                let ids = tp.map(\.gid)
                if let prev = topPrev {
                    topChurn.append(["days": 28, "new_entries": Set(ids).subtracting(prev).count,
                                     "same_rank": zip(ids, prev).filter { $0 == $1 }.count,
                                     "top1": W.name(tp[0].c, tp[0].j).name, "top1_level": W.level(tp[0].c, tp[0].j, tDayEnd),
                                     "l100": W.level(tp[tp.count - 1].c, tp[tp.count - 1].j, tDayEnd)])
                }
                topPrev = ids
                showRows(rowsOf(tp, tDayEnd))
                showRows(rowsOf(W.top(tDayEnd, 100, iso: iso), tDayEnd))
            }
            if di % 91 == 90 {
                print(String(format: "[SOC1][bench] %@ day %d level %d world %d country %d (%.1fs)", prof.name, di + 1, level, wr, cr,
                             Date().timeIntervalSince(tStartWall)))
            }
        }

        func rate(_ xs: [[String: Any]], _ k: String, _ v: Int) -> Double {
            xs.isEmpty ? 0 : Double(xs.filter { ($0[k] as? Int) == v }.count) / Double(xs.count)
        }
        func frac(_ xs: [[String: Any]], _ f: ([String: Any]) -> Bool) -> Double {
            xs.isEmpty ? 0 : Double(xs.filter(f).count) / Double(xs.count)
        }
        func median(_ xs: [Int]) -> Int { xs.isEmpty ? 0 : xs.sorted()[xs.count / 2] }
        func mean(_ xs: [[String: Any]], _ k: String) -> Double {
            xs.isEmpty ? 0 : xs.reduce(0.0) { $0 + Double(($1[k] as? Int) ?? 0) } / Double(xs.count)
        }
        var byStage: [String: Any] = [:]
        for s in 1...3 {
            let rs = rocketResults.filter { ($0["stage"] as? Int) == s }
            byStage["\(s)"] = ["n": rs.count, "win": frac(rs) { ($0["result"] as? String) == "win" }]
        }
        let skyWins = skyResults.filter { ($0["result"] as? String) == "win" }
        let last = ranks.last!
        let summary: [String: Any] = [
            "profile": prof.name, "weeks": weeks, "install": "2026-10-05T18:00:00Z", "model": cfg.worldModel,
            "final_level": level, "wins": wins.count, "fails": fails,
            "world_rank_final": last[2], "country_rank_final": last[3], "population_final": W.gidLimit(last[0] as! Double),
            "weekly": ["n": weeklyResults.count, "group": cfg.weekly.groupSize, "win": rate(weeklyResults, "rank", 1),
                       "podium": frac(weeklyResults) { ($0["rank"] as! Int) <= 3 },
                       "median_rank": median(weeklyResults.map { $0["rank"] as! Int }),
                       "coins": weeklyResults.reduce(0) { $0 + ($1["prize"] as! Int) }],
            "streak_race": ["n": streakResults.count, "group": cfg.streak.groupSize, "first": rate(streakResults, "rank", 1),
                            "top3": frac(streakResults) { ($0["rank"] as! Int) <= 3 },
                            "median_rank": median(streakResults.map { $0["rank"] as! Int }),
                            "coins_per_day": streakResults.isEmpty ? 0 : Double(streakResults.reduce(0) { $0 + ($1["prize"] as! Int) }) / Double(streakResults.count)],
            "rocket": ["n": rocketResults.count, "by_stage": byStage],
            "sky": ["n": skyResults.count, "wins": skyWins.count,
                    "mean_share": skyWins.isEmpty ? 0 : Double(skyWins.reduce(0) { $0 + ($1["share"] as! Int) }) / Double(skyWins.count)],
            "dynamics": ["n": dynamics.count, "sessions_overtaken_by_someone": frac(dynamics) { ($0["overtaken_by"] as! Int) > 0 },
                         "mean_neighbours_moved": mean(dynamics, "neighbours_moved"), "mean_rank_gain": mean(dynamics, "rank_gain")],
            "idle": ["n": idle.count, "returns_with_someone_passing": frac(idle) { ($0["passed_user"] as! Int) > 0 },
                     "mean_passed": mean(idle, "passed_user"), "mean_window_moved": mean(idle, "window_moved")],
            "weekly_session": ["n": weeklyDyn.count, "with_members_scoring": frac(weeklyDyn) { ($0["members_scored"] as! Int) > 0 },
                               "someone_passed_user": frac(weeklyDyn) { ($0["passed_user"] as! Int) > 0 }],
            "weekly_rival_pace": ["weeks": weeklyPace.count,
                                  "median_top_gain_85min": median(weeklyPace.compactMap { ($0["gain85min"] as? [Int])?.first }),
                                  "median_top_gain_3h30": median(weeklyPace.compactMap { ($0["gain3h30"] as? [Int])?.first }),
                                  "median_max_score_at_join": median(weeklyPace.compactMap { ($0["atJoin"] as? [Int])?.first }),
                                  "phone": "join: podium 4,4,3 … 1,1,0; top +23 in 85 min, +43 in 3.5 h (meta §7)"],
            "top100_churn_per_4w": Array(topChurn.suffix(6)),
            "checks": checks,
        ]
        return ["summary": summary, "ranks": stride(from: 0, to: ranks.count, by: 7).map { ranks[$0] },
                "weekly": weeklyResults, "weekly_pace": weeklyPace, "streak": Array(streakResults.suffix(60)),
                "streak_shapes_18h": streakShapes, "rocket": rocketResults, "sky": skyResults, "dynamics": dynamics,
                "idle": Array(idle.suffix(80)), "weekly_dyn": weeklyDyn]
    }
}
