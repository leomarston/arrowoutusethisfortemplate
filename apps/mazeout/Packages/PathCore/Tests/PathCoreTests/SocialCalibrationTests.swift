import XCTest
@testable import GameCore
@testable import ArrowEscape

// SOC1 (the orchestrator's brief: "calibrate against what the phone showed (research/meta.md …); if SPEC-social disagrees
// with those observations, follow the observations"). The SHIPPED world (v552) against the owner's phone on
// 25 Sep 2026 ~01:31 UTC (research/meta.md §7, phone-meta-progress 04:31 TRT). Tolerances are stated per number;
// the V2 video's older build (30 Jul) is reported, not targeted (the phone wins, owner 02:55).
// SOC1_SAMPLES_DIR=<dir> also writes the owner-facing samples (names + example views at the phone's moment).

final class SocialCalibrationTests: XCTestCase {
    typealias F = SocFix
    static let phoneT = 1_790_299_860.0      // 2026-09-25 01:31 UTC = 04:31 TRT (the leaderboard shots)
    /// PUBLISH B2: every phone guard runs on the calibrated v1 world ("v552") AND on the shipped v2 world ("v2"), the latter
    /// at the SAME WORLD AGE as the phone's shots (design/social/tools/v2/calib_v2.py: the phone saw the original's world
    /// 150.8 days after its epoch; v2's world starts 19 weeks after the calibrated one, so each moment moves +19 weeks).
    static let models = ["v552", "v2"]
    static func shift(_ model: String) -> Double { model == "v2" ? Double(19 * 604_800) : 0 }

    func testShippedWorldMatchesThePhone() throws {
        for model in Self.models {
            let W = F.world(model)
            let t = Self.phoneT + Self.shift(model)
            W.extend(to: t + 2 * 86_400)
            let top = W.top(t, 300).map { W.level($0.c, $0.j, t) }
            let phone: [(rank: Int, level: Int, tol: Double)] = [(1, 14669, 0.10), (2, 13344, 0.15), (3, 13115, 0.15), (4, 12699, 0.15),
                                                                  (5, 12003, 0.15), (6, 11536, 0.15), (7, 11386, 0.15),
                                                                  (24, 8400, 0.15), (89, 5154, 0.15), (132, 4300, 0.15), (278, 3096, 0.15)]
            var evidence: [[String: Any]] = []
            for p in phone {
                let ours = top[p.rank - 1]
                let rel = Double(ours - p.level) / Double(p.level)
                evidence.append(["board": "World", "rank": p.rank, "phone": p.level, "ours": ours, "rel": rel])
                XCTAssertLessThanOrEqual(abs(rel), p.tol, "\(model) World #\(p.rank): ours \(ours) vs phone \(p.level)")
            }
            let trRank = W.rankOfLevel(62, t, iso: "TR")
            evidence.append(["board": "Turkey", "rank_at_L62": trRank, "phone": 455])
            XCTAssertLessThanOrEqual(abs(Double(trRank - 455) / 455), 0.15, "\(model) Turkey rank at L62: \(trRank) vs 455")
            let trTop = W.top(t, 7, iso: "TR").map { W.level($0.c, $0.j, t) }
            let trPhone = [10824, 3323, 3193, 2575, 2401, 1604, 1349]
            for k in 1..<7 {          // #1 (10824) is a lone outlier on the phone: reported, not targeted
                XCTAssertLessThanOrEqual(abs(Double(trTop[k] - trPhone[k]) / Double(trPhone[k])), 0.40, "Turkey #\(k + 1)")
            }
            evidence.append(["board": "Turkey top 7", "phone": trPhone, "ours": trTop])
            let videoT = 1_785_425_220.0 + Self.shift(model)   // 2026-07-30 15:27 UTC, the V2 video (an older build)
            evidence.append(["board": "World top 8 on 30 Jul (V2 video, older build; reported only)",
                             "video": [11635, 10040, 9120, 9051, 8795, 8443, 8135, 8122],
                             "ours": W.top(videoT, 8).map { W.level($0.c, $0.j, videoT) }])
            // world size and the reference's calibration for comparison
            evidence.append(["players_joined": W.joined(t), "TR_joined": W.joined(t, iso: "TR"), "US_joined": W.joined(t, iso: "US")])
            let cfg = SocialConfig.default
            XCTAssertEqual(cfg.weekly.groupSize, 10, "phone: a 10-player Weekly group")
            XCTAssertEqual(cfg.weekly.prizes, [2000, 1000, 500])
            XCTAssertEqual(cfg.streak.groupSize, 50, "phone: 50 Streak Race rows")
            XCTAssertEqual(cfg.streak.prizes, [2000, 1000, 500, 100, 100, 100, 100, 100, 100, 100])
            if let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty {
                let data = try JSONSerialization.data(withJSONObject: evidence, options: [.prettyPrinted, .sortedKeys])
                try data.write(to: URL(fileURLWithPath: dir).appendingPathComponent("soc1-calibration-\(model).json"))
            }
            print("[SOC1][calibration] \(model) World top-8 \(Array(top.prefix(8))) #24 \(top[23]) #89 \(top[88]) #132 \(top[131]) #278 \(top[277]); TR L62 → #\(trRank); TR top \(trTop)")

        }
    }

    /// The Weekly group at the phone's moment is complete when the player joins, and its rivals then move at the pace the
    /// phone showed (up to ~9-16 levels an hour for the leaders).
    func testWeeklyGroupShapeAtThePhoneMoment() {
        for model in Self.models {
            let W = F.world(model)
            let join = 1_790_294_760.0 + Self.shift(model)   // 25 Sep 00:06 UTC (the player joined, meta shot 132)
            W.extend(to: join + 9 * 86_400)
            let g = SocialGroupContest(W: W, installSeed: 20_260_925, spec: SocialConfig.default.weekly,
                                       key: SocialGroupKey(instance: SocialCalendar.eventWeek(join), t0: join, ref: 60))
            XCTAssertEqual(g.members.count, 9)
            XCTAssertTrue(g.arrive.allSatisfy { $0 <= join && $0 >= join - 900 }, "every member arrived within 15 min before the join")
            let atJoin = g.standings(join, userScore: 0, userReached: join)
            XCTAssertEqual(atJoin.count, 10)
            XCTAssertLessThanOrEqual(atJoin[0].score, 12, "a fresh group: small scores at the join (phone: 4, 4, 3 … 1, 1, 0)")
            let later = g.standings(join + 3.5 * 3600, userScore: 12, userReached: join + 3 * 3600)
            XCTAssertGreaterThan(later[0].score, atJoin[0].score, "the leaders move while the player plays")

        }
    }

    // ---------------------------------------------------------------------------------------------- phone session 2
    // SOC1b: the recalibration to research/social-dynamics.md (25 Sep 12:07 → 14:47 TRT). Tolerances are loose on purpose:
    // one phone sample per statistic; build/soc1b/calibration.md has the full before/after table (tools/calib_s2.py).

    /// 25 Sep 2026 h:m in Turkey time (UTC+3) as UTC seconds (1_790_283_600 = 25 Sep 00:00 TRT = 24 Sep 21:00 UTC).
    static func trt(_ h: Int, _ m: Int) -> Double { 1_790_283_600.0 + Double(h * 3600 + m * 60) }

    /// Turkey: the player's rank fell ~3.6 places per level won at L62-L84 (455 → 375); SOC1's world had 5.3.
    func testTurkeyRankSlope() {
        for model in Self.models {
            let W = F.world(model)
            W.extend(to: Self.trt(23, 0) + Self.shift(model) + 2 * 86_400)
            let obs: [(h: Int, m: Int, level: Int, rank: Int)] = [(4, 31, 62, 455), (12, 11, 64, 448), (12, 37, 68, 438), (13, 11, 72, 412),
                                                                    (13, 35, 77, 396), (14, 1, 80, 386), (14, 17, 84, 375)]
            let ours = obs.map { W.rankOfLevel($0.level, Self.trt($0.h, $0.m) + Self.shift(model), iso: "TR") }
            for (o, r) in zip(obs, ours) {
                XCTAssertLessThanOrEqual(abs(Double(r - o.rank) / Double(o.rank)), 0.15, "Turkey L\(o.level): #\(r) vs #\(o.rank)")
            }
            let slope = Double(ours[0] - ours[ours.count - 1]) / 22
            XCTAssertTrue((2.7...4.6).contains(slope), "slope \(slope) places per level (phone 3.64)")
            print("[SOC1b][calibration] Turkey ranks \(ours) slope \(slope)")

        }
    }

    /// calib_s2.py `classify`: the name classes the phone's ~113 names were counted in (research/social-dynamics.md §H).
    static func nameClass(_ n: String, given: Set<String>) -> String {
        let sc = Array(n.unicodeScalars)
        if n.hasPrefix("player_") && sc.count == 14 { return "default" }
        let letters = sc.filter { $0.properties.isAlphabetic }
        let hasDigit = sc.contains { SocialNames.isDigit($0) }
        let humps = zip(sc, sc.dropFirst()).filter { $0.0.properties.isLowercase && $0.1.properties.isUppercase }.count
        let firstTwoUpper = sc.count >= 2 && sc[0].properties.isUppercase && sc[1].properties.isUppercase
        if humps >= 1 && !firstTwoUpper { return "camelCase" }
        if !letters.isEmpty && letters.allSatisfy({ $0.properties.isUppercase }) && !hasDigit && letters.count >= 3 && !n.contains("_") {
            return "allCaps"
        }
        if hasDigit || n.contains("_") { return "digitsLeet" }
        if !letters.isEmpty && letters.allSatisfy({ $0.properties.isLowercase }) { return "lowercase" }
        if let f = sc.first, f.properties.isUppercase, letters.dropFirst().allSatisfy({ $0.properties.isLowercase }) {
            return given.contains(SocialNames.key(n)) ? "firstName" : "capitalised"
        }
        return "other"
    }

    static let givenKeys: Set<String> = {
        var s = Set<String>()
        for (_, toks) in F.bank.store?.cultures ?? [:] { for t in toks { s.insert(SocialNames.key(t.native)) } }
        return s
    }()
    /// calib_v2.py GIVEN: the v2 data's first names (native forms' keys).
    static let givenKeysV2: Set<String> = {
        var s = Set<String>()
        for (_, toks) in F.bankV2.store?.cultures ?? [:] { for t in toks { s.insert(SocialNames.key(t.native)) } }
        return s
    }()

    /// Names on the boards: ~14-18 % player_xxxxxxx (Streak Race 9/49 …), not SOC1's ~46 %; CamelCase, ALL CAPS, lowercase
    /// and short/leet handles all present. SOC1c (drawn names): plain first names ~14 % (SOC1b 0.5 %) and names with
    /// digits ~7 % (SOC1b 24 %), like the phone's boards.
    func testBoardNameMix() {
        for model in Self.models {
            let W = F.world(model)
            let sj = Self.trt(11, 3) + Self.shift(model)
            W.extend(to: sj + 9 * 86_400)
            var names: [String] = []
            // 20 groups (980 names): pure ALL CAPS run at ~1.2 % here (23 of 1,960 over 40 groups), so 6 groups (294 names)
            // was too small a sample to assert on (it held 0 by chance)
            for seed in 0..<20 {
                let g = SocialGroupContest(W: W, installSeed: UInt64(9000 + seed), spec: SocialConfig.default.streak,
                                           key: SocialGroupKey(instance: SocialCalendar.eventDay(sj), t0: sj, ref: 30))
                names += g.members.map { W.name($0.0, $0.1).name }
            }
            let n = Double(names.count)
            let share = { (f: (String) -> Bool) in Double(names.filter(f).count) / n }
            let dflt = share { $0.hasPrefix("player_") }
            XCTAssertTrue((0.08...0.26).contains(dflt), "default share \(dflt) (phone 0.14-0.18)")
            XCTAssertGreaterThan(share { $0.contains { $0.isUppercase } && $0.dropFirst().contains { $0.isUppercase } && $0.contains { $0.isLowercase } }, 0.08,
                                 "CamelCase")
            XCTAssertGreaterThan(share { !$0.hasPrefix("player_") && $0.allSatisfy { $0.isLowercase } }, 0.05, "lowercase handles")
            XCTAssertGreaterThan(share { $0.allSatisfy { $0.isUppercase } }, 0.003, "ALL CAPS (letters only, like ASLAN / DER)")
            let given = model == "v2" ? Self.givenKeysV2 : Self.givenKeys
            let cls = { (k: String) in share { Self.nameClass($0, given: given) == k } }
            XCTAssertTrue((0.08...0.22).contains(cls("firstName")), "plain first names \(cls("firstName")) (phone 0.14; SOC1b 0.005)")
            XCTAssertLessThanOrEqual(cls("digitsLeet"), 0.12, "names with digits \(cls("digitsLeet")) (phone 0.07; SOC1b 0.24)")
            XCTAssertGreaterThan(cls("digitsLeet"), 0.02, "a few handles still carry digits (Caco17, L8M, 0xBK)")
            XCTAssertTrue((0.20...0.45).contains(cls("capitalised")), "capitalised handles \(cls("capitalised")) (phone 0.34)")
            print("[SOC1c][calibration] streak-board names: default \(dflt) firstName \(cls("firstName")) capitalised \(cls("capitalised")) "
                  + "lowercase \(cls("lowercase")) camelCase \(cls("camelCase")) allCaps \(cls("allCaps")) digits \(cls("digitsLeet")) "
                  + "sample \(names.prefix(20))")

        }
    }

    /// SOC1c: names repeat like the original's (two different "Bobby" in its World top 15; its boards held 1 repeated pair
    /// in 1,721 row pairs — a 95 % interval of 1.5e-5 … 3.2e-3 for the chance that two rows of a board share a name). The
    /// shipped world must land inside it, show repeats on some boards, and keep every row a distinct player (gid).
    func testNameRepeatsAtThePhonesRate() {
        for model in Self.models {
            let W = F.world(model)
            let sj = Self.trt(11, 3) + Self.shift(model)
            W.extend(to: sj + 9 * 86_400)
            var pairs = 0, rowPairs = 0, boardsWithRepeat = 0
            var examples: [String] = []
            for seed in 0..<100 {
                let g = SocialGroupContest(W: W, installSeed: UInt64(19_000 + seed), spec: SocialConfig.default.streak,
                                           key: SocialGroupKey(instance: SocialCalendar.eventDay(sj), t0: sj, ref: 30))
                XCTAssertEqual(Set(g.members.map { W.gid($0.0, $0.1) }).count, g.members.count, "every row is a distinct player")
                var cnt: [String: Int] = [:]
                for m in g.members { cnt[SocialNames.key(W.name(m.0, m.1).name), default: 0] += 1 }
                let p = cnt.values.reduce(0) { $0 + $1 * ($1 - 1) / 2 }
                if p > 0 {
                    boardsWithRepeat += 1
                    if examples.count < 6 { examples += g.members.map { W.name($0.0, $0.1).name }.filter { cnt[SocialNames.key($0)]! > 1 } }
                }
                pairs += p
                rowPairs += g.members.count * (g.members.count - 1) / 2
            }
            let rate = Double(pairs) / Double(rowPairs)
            XCTAssertGreaterThan(boardsWithRepeat, 0, "some boards show a repeated name (the phone's two Bobby)")
            XCTAssertTrue((1.5e-5...3.2e-3).contains(rate), "pair rate \(rate) (phone 1 / 1721 = 5.8e-4, 95 % CI 1.5e-5 … 3.2e-3)")
            print("[SOC1c][calibration] streak boards: \(boardsWithRepeat) of 100 show a repeated name, \(pairs) pairs in \(rowPairs) "
                  + "row pairs (rate \(rate)); e.g. \(examples)")

        }
    }

    /// Weekly: the rivals move in bursts; ~40 % stay idle from +3.5 h to +11.2 h after the join (phone 4 of 9).
    func testWeeklyBurstiness() {
        for model in Self.models {
            let W = F.world(model)
            let join = Self.trt(3, 6) + Self.shift(model)
            W.extend(to: join + 9 * 86_400)
            var idle = 0, total = 0, movers = 0
            for seed in 0..<12 {
                let g = SocialGroupContest(W: W, installSeed: UInt64(7000 + seed), spec: SocialConfig.default.weekly,
                                           key: SocialGroupKey(instance: SocialCalendar.eventWeek(join), t0: join, ref: 175))
                for i in g.members.indices {
                    let a = g.memberScore(i, join + 3.5 * 3600) ?? 0, b = g.memberScore(i, join + 9 * 3600) ?? 0
                    let c = g.memberScore(i, join + 11.2 * 3600) ?? 0
                    total += 1
                    if c == a { idle += 1 }
                    if b > a { movers += 1 }
                }
            }
            let share = Double(idle) / Double(total)
            XCTAssertTrue((0.30...0.72).contains(share), "idle share \(share) (phone 0.44)")
            XCTAssertGreaterThan(Double(movers) / 12, 2.0, "movers per group from +3.5 h to +9 h (phone 5)")
            print("[SOC1b][calibration] weekly idle share \(share), movers/group \(Double(movers) / 12)")

        }
    }

    /// Streak Race: all rivals at 0 when the player joins, listed alphabetically; most score within the first hour.
    func testStreakRaceStartsAtZeroAlphabetical() {
        for model in Self.models {
            let W = F.world(model)
            let sj = Self.trt(11, 3) + Self.shift(model)
            W.extend(to: sj + 9 * 86_400)
            var zeros69: [Int] = []
            for seed in 0..<6 {
                let g = SocialGroupContest(W: W, installSeed: UInt64(9000 + seed), spec: SocialConfig.default.streak,
                                           key: SocialGroupKey(instance: SocialCalendar.eventDay(sj), t0: sj, ref: 30))
                let st = g.standings(sj, userScore: 0, userReached: sj, userName: "Hsheh")
                XCTAssertEqual(st.count, 50)
                XCTAssertTrue(st.allSatisfy { $0.score == 0 }, "everyone at 0 at the join")
                let keys = st.map { SocialGroupContest.sortKey($0.member.map { W.name(g.members[$0].0, g.members[$0].1).name } ?? "Hsheh") }
                XCTAssertTrue(zip(keys, keys.dropFirst()).allSatisfy { !$1.lexicographicallyPrecedes($0) }, "alphabetical at 0")
                zeros69.append(g.members.indices.filter { (g.memberScore($0, sj + 69 * 60) ?? 0) == 0 }.count)
            }
            let med = zeros69.sorted()[zeros69.count / 2]
            XCTAssertTrue((8...32).contains(med), "rows still at 0 after 69 min: \(zeros69) (phone 17)")

        }
    }

    /// Rocket Race: one rival finishes 5 levels 6-19 min after the join (phone); a player at 2 min a level wins some.
    func testRocketSprinter() {
        for model in Self.models {
            let W = F.world(model)
            let t0 = Self.trt(12, 15) + Self.shift(model)
            W.extend(to: t0 + 3 * 86_400)
            var firsts: [Double] = [], wins2 = 0
            for k in 0..<16 {
                let t = t0 + Double(k) * 1800
                let rr = SocialRocketRace(W: W, installSeed: UInt64(5000 + k), raceId: k + 1, stage: 1, t0: t, secondsPerWin: 110, spec: .shipped)
                if let f = rr.rivals.indices.compactMap({ rr.finishTime($0, userNminus1: nil) }).min() { firsts.append((f - t) / 60) }
                if rr.outcome(userTimes: (1...5).map { t + 120 * Double($0) }).result == .win { wins2 += 1 }
            }
            let med = firsts.sorted()[firsts.count / 2]
            XCTAssertTrue((6...19).contains(med), "first finish median \(med) min (phone 6, 8, 19)")
            XCTAssertTrue((2...14).contains(wins2), "2 min a level wins \(wins2) of 16")
            print("[SOC1b][calibration] rocket first finish \(firsts.sorted()) wins@2min \(wins2)/16")

        }
    }

    /// Sky Jump stage 2 (phone): 100 100 88 75 62 49 36 → 15 winners sharing 7000 (466 each).
    func testSkyJumpStageTwo() {
        var winners: [Int] = []
        for a in 0..<40 {
            let sj = SocialSkyJump(installSeed: 4242, attemptId: a, stage: 2, spec: SocialConfig.default.sky)
            XCTAssertEqual(sj.alive[1], 100, "nobody drops at the first win of stage 2")
            let drops = (2..<sj.N).map { sj.alive[$0 - 1] - sj.alive[$0] }
            XCTAssertTrue(drops.allSatisfy { (10...15).contains($0) }, "\(sj.alive)")
            winners.append(sj.alive[sj.N])
        }
        XCTAssertTrue(winners.allSatisfy { (12...18).contains($0) })
        XCTAssertEqual(7000 / 15, 466)
    }

    /// Sky Jump stage 3 (phone sessions 2 and 3): 10 levels, PRIZE 10000; 100 100 91 83 75 66 57 48 40 32 → 7 winners
    /// ("You win! 1428 — You are sharing the reward with 6 other winners!", 10000/7).
    func testSkyJumpStageThree() {
        XCTAssertEqual(SocialConfig.default.sky.levels, [5, 7, 10])
        XCTAssertEqual(SocialConfig.default.sky.pools, [5000, 7000, 10000])
        var winners: [Int] = []
        for a in 0..<40 {
            let sj = SocialSkyJump(installSeed: 4242, attemptId: a, stage: 3, spec: SocialConfig.default.sky)
            XCTAssertEqual(sj.N, 10)
            XCTAssertEqual(sj.pool, 10000)
            XCTAssertEqual(sj.alive.count, 11)
            XCTAssertEqual(sj.alive[1], 100, "nobody drops at the first win of stage 3")
            let drops = (2..<sj.N).map { sj.alive[$0 - 1] - sj.alive[$0] }
            XCTAssertTrue(drops.allSatisfy { (6...11).contains($0) }, "\(sj.alive) (phone 8-9 a level)")
            XCTAssertTrue((22...44).contains(sj.alive[9]), "\(sj.alive) (phone 32 before the last level)")
            XCTAssertEqual(sj.share, 10000 / sj.alive[10])
            winners.append(sj.alive[10])
        }
        XCTAssertTrue(winners.allSatisfy { (5...9).contains($0) })
        XCTAssertEqual(winners.sorted()[winners.count / 2], 7, "median winners = the phone's 7 (share 1428)")
    }

    /// Owner-facing samples (SOC1b): the shipped world along the phone's session-2 timeline (25 Sep 2026, TRT) for a
    /// player like the phone's (Hsheh, Turkey, ~35 wins a day): World and Turkey boards, the Weekly group from the join,
    /// the Streak Race from the join, three Rocket Races at the phone's slow pace, Sky Jump curves, 200 nicknames.
    /// SOC1_SAMPLES_DIR=<dir> writes <dir>/owner-sample.txt + names-sample.json.
    func testWriteOwnerSamples() throws {
        guard let dir = ProcessInfo.processInfo.environment["SOC1_SAMPLES_DIR"], !dir.isEmpty else {
            throw XCTSkip("set SOC1_SAMPLES_DIR to write the owner samples")
        }
        let seed: UInt64 = 20_260_925
        // PUBLISH B2: the shipped v2 world at the phone's world age (+19 weeks); clock() prints the phone's wall times
        let world = SocialWorld(installSeed: seed, config: .default, names: F.bankV2)
        let sh = Self.shift("v2")
        func T(_ h: Int, _ m: Int) -> SocialTime { SocialTime(seconds: Int64(Self.trt(h, m) + sh)) }
        func clock(_ t: SocialTime) -> String {
            let x = Int(t.seconds) + 3 * 3600
            return String(format: "%02d:%02d", (x / 3600) % 24, (x / 60) % 60)
        }
        var st = SocialState()
        st.setHomeIfNeeded(region: "TR", offsetMinutes: 180)
        st.username = "Hsheh"
        // history: ~35 wins on each of the 3 days before (SocialPace: 35 a day; first Weekly week -> ref 5 x 35 = 175)
        for d in 1...3 {
            let base = Int64(Self.trt(20, 0) + sh) - Int64(d) * 86_400
            for k in 0..<35 { st.recordWin(level: 10 + d * 35 + k, firstTry: true, points: 1, at: SocialTime(seconds: base + Int64(k) * 150)) }
        }
        let joinW = T(3, 6)
        let week = SocialCalendar.eventWeek(Int(joinW.seconds))
        _ = st.joinWeekly(week: week, level: 50, at: joinW)
        var level = 50
        func win(_ t: SocialTime, _ pts: Int) { st.recordWin(level: level, firstTry: true, points: pts, at: t); level += 1 }
        for k in 0..<12 { win(SocialTime(seconds: joinW.seconds + 300 + Int64(k) * 400), 1) }            // L50-L61 by 04:28
        let joinS = T(11, 3)
        let day = SocialCalendar.eventDay(Int(joinS.seconds))
        let skey = st.joinStreak(day: day, level: 62, at: joinS)
        // L62-L84 from 11:23: the ladder x1 x5 x10 x25 x100 …, one time-out (the phone's L77) resets it
        var step = 0
        for k in 0..<22 {
            let t = SocialTime(seconds: T(11, 23).seconds + Int64(k) * 480)
            if k == 15 { st.recordFail(level: level, at: SocialTime(seconds: t.seconds - 120)); step = 0 }
            win(t, SocialWinStreak.steps[step]); step = min(step + 1, 4)
        }
        func me(_ lv: Int) -> PlayerStanding { st.standing(installSeed: seed, level: lv) }
        func row(_ r: LeaderboardRow) -> String {
            "\(r.rank)\t\(r.player.name)\(r.isMe ? "  <- you" : "")\t\(r.value)\t\(r.player.country)\tavatar \(r.player.avatar)"
        }
        var out = "The player world as the owner will meet it (the shipped v2 world: the calibrated world + country blocks, 200 countries, native-script names; Sky Jump stage 3 = 10 levels)\n"
        out += "Timeline: Friday 25 Sep 2026, Turkey time (the phone's session 2). Player: Hsheh, Turkey, ~35 wins a day.\n"
        out += "Everything below is computed by PathCore (the shipped Swift code), not hand-written.\n\n"
        // World at 12:09 and 14:01
        let w1 = world.page(.world, me: me(64), at: T(12, 9), ranks: 1...15).rows
        let w2 = world.page(.world, me: me(80), at: T(14, 1), ranks: 1...25).rows
        let later = Dictionary(w2.map { ($0.player.id, $0.value) }, uniquingKeysWith: { a, _ in a })
        out += "WORLD top 15 at 12:09 (rank, name, level, country, avatar) and the same player's level at 14:01:\n"
        out += w1.map { row($0) + "\t-> \(later[$0.player.id].map(String.init) ?? "?")" }.joined(separator: "\n") + "\n"
        out += "(phone: 14730 13349 13154 12699 12003 … #15 10069; 9 of 15 static over these 1.9 h, one climber +66)\n\n"
        // Turkey
        out += "TURKEY top 7 at 12:11:\n" + world.page(.country("TR"), me: me(64), at: T(12, 11), ranks: 1...7).rows.map(row).joined(separator: "\n") + "\n"
        for (h, m, lv) in [(4, 31, 62), (12, 11, 64), (13, 11, 72), (14, 17, 84)] {
            let p = world.page(.country("TR"), me: me(lv), at: T(h, m), ranks: 1...1)
            out += "TURKEY: the player at Level \(lv) at \(String(format: "%02d:%02d", h, m)) is #\(p.myRank)\n"
        }
        out += "(phone: #455 at L62 04:31, #448 at L64, #412 at L72, #375 at L84 14:17)\n"
        let myTR = world.page(.country("TR"), me: me(64), at: T(12, 11), ranks: 1...1).myRank
        out += "TURKEY around the player at 12:11 (rank \(myTR)):\n"
            + world.page(.country("TR"), me: me(64), at: T(12, 11), around: myTR, radius: 5).rows.map(row).joined(separator: "\n") + "\n\n"
        // Weekly from the join
        let wkTimes = [joinW, T(4, 31), T(6, 39), T(12, 8), T(14, 17)]
        var wkCols: [UInt64: [Int]] = [:]
        var wkNames: [UInt64: String] = [:]
        var lastBoard: SocialGroupBoard? = nil
        for t in wkTimes {
            guard let b = world.weeklyBoard(week: week, me: me(level), at: t) else { continue }
            for r in b.rows { wkCols[r.player.id, default: []].append(r.value); wkNames[r.player.id] = r.player.name + (r.isMe ? " (you)" : "") }
            lastBoard = b
        }
        out += "WEEKLY CONTEST (10 players; joined 03:06) — score at " + wkTimes.map(clock).joined(separator: " / ") + ", rank at the end:\n"
        for r in lastBoard?.rows ?? [] {
            out += "\(r.rank)\t\(wkNames[r.player.id] ?? "")\t" + (wkCols[r.player.id] ?? []).map(String.init).joined(separator: " / ") + "\n"
        }
        out += "(phone: Guy 19/34/79/79, player_qqpvpjp 27/45/47/47, LoudRat 9/17/29/29 … Boo 6, Mema 4 — ~40 % idle all day)\n\n"
        // Streak Race from the join
        let stTimes = [joinS, T(12, 12), T(12, 40), T(14, 3)]
        var stCols: [UInt64: [Int]] = [:]
        var stLast: SocialGroupBoard? = nil
        var stFirst: SocialGroupBoard? = nil
        for t in stTimes {
            let b = world.streakBoard(key: skey, me: me(level), at: t)
            for r in b.rows { stCols[r.player.id, default: []].append(r.value) }
            if stFirst == nil { stFirst = b }
            stLast = b
        }
        out += "STREAK RACE at the join (11:03): 50 rows, everyone at 0, listed alphabetically — first 12: "
            + (stFirst?.rows.prefix(12).map { $0.player.name + ($0.isMe ? " (you)" : "") }.joined(separator: ", ") ?? "") + "\n"
        out += "STREAK RACE — points at " + stTimes.map(clock).joined(separator: " / ") + " (rank at 14:03, prize):\n"
        for r in stLast?.rows ?? [] {
            let prize = r.rank <= (stLast?.prizes.count ?? 0) ? String(stLast!.prizes[r.rank - 1]) : "-"
            out += "\(r.rank)\t\(r.player.name)\(r.isMe ? " (you)" : "")\t" + (stCols[r.player.id] ?? []).map(String.init).joined(separator: " / ") + "\t\(prize)\n"
        }
        out += "(phone 12:12: 1941 1498 1101 1101 1001 … 17 rows still at 0; 12:12 -> 14:03 ~47 % of rows static)\n\n"
        // Rocket Races at the phone's joins, the player at ~6 min a level (the phone's pace; it lost all three)
        for (i, (h, m)) in [(12, 15), (12, 28), (12, 44)].enumerated() {
            let j = T(h, m)
            let wins = (1...5).map { SocialTime(seconds: j.seconds + Int64($0) * 360) }
            out += "ROCKET RACE joined \(String(format: "%02d:%02d", h, m)) (the player at ~6 min a level):\n"
            for mm in [3, 6, 8, 12, 19] {
                let b = world.rocketBoard(raceId: 100 + i, stage: 1, joinedAt: j, secondsPerWin: 360, userWins: wins, me: me(level),
                                          at: SocialTime(seconds: j.seconds + Int64(mm) * 60))
                out += "  +\(mm) min: " + b.lanes.map { "\($0.player.name)\($0.isMe ? " (you)" : "") \($0.score)/\(b.levels)" }.joined(separator: ", ")
                    + (b.result == "none" ? "" : "  -> \(b.result)") + "\n"
            }
        }
        out += "(phone: R1 Emilia 5/5 by +8 min; R2 player_nvbfr9z 5/5 by +6 min; R3 ned 5/5 at +19 min; the player lost all three)\n\n"
        // Sky Jump
        for stage in 1...3 {
            out += "SKY JUMP stage \(stage) (players after each first-try win; last = winners, share):\n"
            for a in 0..<3 {
                let c: SocialSkyJump = world.skyJumpCurve(attemptId: 40 + stage * 10 + a, stage: stage)
                let alive: [String] = c.alive.map { String($0) }
                out += "  " + alive.joined(separator: " ") + "  share \(c.share)\n"
            }
        }
        out += "(phone: stage 1 100 82 64 ? 47 -> 7 (714); stage 2 100 100 88 75 62 49 36 -> 15 (466); stage 3 = 10 levels, PRIZE 10000: "
            + "100 100 91 83 75 66 57 48 40 32 -> 7 (1428))\n\n"
        // 200 names as met on the boards: every k-th player of the Streak Race groups of many installs — 200 DIFFERENT
        // players (the installs' groups at one moment share the online players, so the same gid is listed once: a name
        // shown twice below is two players, as on the phone)
        let W = F.world("v2")
        W.extend(to: Double(joinS.seconds) + 9 * 86_400)
        var met: [String] = []
        var metG = Set<Int>()
        var k = 0
        while met.count < 200 {
            let g = SocialGroupContest(W: W, installSeed: UInt64(31_000 + k), spec: SocialConfig.default.streak,
                                       key: SocialGroupKey(instance: day, t0: Double(joinS.seconds), ref: 30))
            for (o, m) in g.members.enumerated() where o % 5 == k % 5 && metG.insert(W.gid(m.0, m.1)).inserted {
                met.append(W.name(m.0, m.1).name)
            }
            k += 1
        }
        let sample = Array(met.prefix(200))
        let dflt = Double(sample.filter { $0.hasPrefix("player_") }.count) / Double(sample.count)
        func pct(_ k: String) -> Int { Int((100 * Double(sample.filter { Self.nameClass($0, given: Self.givenKeys) == k }.count) / Double(sample.count)).rounded()) }
        out += "200 NICKNAMES as met on Streak Race boards (\(Int((dflt * 100).rounded()))% player_xxxxxxx, \(pct("firstName"))% plain first "
            + "names, \(pct("digitsLeet"))% with digits; phone 14 / 14 / 7 %):\n"
        out += stride(from: 0, to: sample.count, by: 10).map { sample[$0..<min($0 + 10, sample.count)].joined(separator: ", ") }.joined(separator: "\n") + "\n\n"
        // repeated names (SOC1c): the World top 100 at 12:09 and 60 Streak Race boards at the phone's join
        let top100 = world.page(.world, me: me(64), at: T(12, 9), ranks: 1...100).rows.filter { !$0.isMe }
        var cw: [String: [Int]] = [:]
        for r in top100 { cw[SocialNames.key(r.player.name), default: []].append(r.rank) }
        let rep = cw.filter { $0.value.count > 1 }.sorted { $0.value[0] < $1.value[0] }
        out += "REPEATED NAMES (names repeat like the original's two \"Bobby\"; every row is still a different player):\n"
        var repTexts: [String] = []
        for kv in rep {
            let shown: String = top100.first { SocialNames.key($0.player.name) == kv.key }?.player.name ?? kv.key
            let ranks: [String] = kv.value.map { String($0) }
            repTexts.append(shown + " at #" + ranks.joined(separator: " and #"))
        }
        let repLine: String = repTexts.isEmpty ? "none this time" : repTexts.joined(separator: "; ")
        out += "  World top 100 at 12:09: " + repLine + "\n"
        var repBoards: [String] = []
        var nRep = 0
        for s in 0..<60 {
            let g = SocialGroupContest(W: W, installSeed: UInt64(19_000 + s), spec: SocialConfig.default.streak,
                                       key: SocialGroupKey(instance: day, t0: Double(joinS.seconds), ref: 30))
            var cnt: [String: [String]] = [:]
            for m in g.members { let nm = W.name(m.0, m.1).name; cnt[SocialNames.key(nm), default: []].append(nm) }
            let r = cnt.values.filter { $0.count > 1 }
            if !r.isEmpty { nRep += 1; if repBoards.count < 6 { repBoards.append(r.map { $0.joined(separator: " + ") }.joined(separator: ", ")) } }
        }
        out += "  Streak Race boards: \(nRep) of 60 show a repeated name — e.g. " + repBoards.joined(separator: "; ") + "\n"
        out += "(phone: 1 repeated pair on its 5 boards — Bobby #9 and Bobby #15 in the World top 15)\n"
        try FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        try out.write(to: URL(fileURLWithPath: dir).appendingPathComponent("owner-sample.txt"), atomically: true, encoding: .utf8)
        let data = try JSONSerialization.data(withJSONObject: ["names200": sample, "defaultShare": dflt], options: [.prettyPrinted, .sortedKeys])
        try data.write(to: URL(fileURLWithPath: dir).appendingPathComponent("names-sample.json"))
        print(out)
    }
}
