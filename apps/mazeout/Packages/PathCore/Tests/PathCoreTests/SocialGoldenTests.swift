import XCTest
@testable import PathCore

// SOC1 (SPEC-architecture §4.17 `Social*Tests`, §12.2 SOC1; SPEC-social §8.1). Bit-exact agreement of the Swift port with
// the Python reference (design/social/tools/socialsim) on the social designer's golden vectors (design/social/fixtures,
// the `.reference` model). Exact equality everywhere: doubles are parsed from Python repr() strings, which restore the
// same bits. Never edit a fixture to pass. Runs in Debug (`swift test`) and -O (`swift test -c release`).

enum SocFix {
    static var testsDir: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent() }
    static var appRoot: URL { testsDir.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent() }
    static var designData: URL { appRoot.appendingPathComponent("design/social/data") }
    static func designFixture(_ name: String) throws -> [String: Any] {
        try json(appRoot.appendingPathComponent("design/social/fixtures/\(name)"))
    }
    static func ownFixture(_ name: String) throws -> [String: Any] {
        try json(testsDir.appendingPathComponent("Fixtures/\(name)"))
    }
    static func json(_ url: URL) throws -> [String: Any] {
        let data = try Data(contentsOf: url)
        guard let o = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw NSError(domain: "SocFix", code: 1, userInfo: [NSLocalizedDescriptionKey: "not an object: \(url.path)"])
        }
        return o
    }

    static let bank: NameBank = {
        do { return try NameBank.load(folder: designData) } catch { fatalError("social_names.json: \(error)") }
    }()
    /// PUBLISH B2: the v2 name data (T6, design/social/data_v2/social_names_v2.json) the shipped world draws from.
    static var designDataV2: URL { appRoot.appendingPathComponent("design/social/data_v2") }
    static let bankV2: NameBank = {
        do { return try NameBank.load(data: Data(contentsOf: designDataV2.appendingPathComponent("social_names_v2.json"))) }
        catch { fatalError("social_names_v2.json: \(error)") }
    }()

    /// Worlds shared by the tests (append-only tables; thread-safe). Fixture keys: "reference" (the prototype), "v552" (the
    /// calibrated v1 world; its fixtures keep their SOC1 file names), "v2" (the shipped world, PUBLISH B2).
    static let refWorld = SocialPopulation(model: .reference, names: bank)
    static let calibratedWorld = SocialPopulation(model: .calibrated, names: bank)
    static let v2World = SocialPopulation(model: .shipped, names: bankV2)
    static func world(_ model: String) -> SocialPopulation {
        switch model {
        case "reference": return refWorld
        case "v2": return v2World
        default: return calibratedWorld
        }
    }
    static func model(_ key: String) -> SocialWorldModel {
        switch key {
        case "reference": return .reference
        case "v2": return .shipped
        default: return .calibrated
        }
    }
    static func bank(_ key: String) -> NameBank { key == "v2" ? bankV2 : bank }
    /// The name data a model draws from: the v2 data for the shipped (v2) world, the v1 data for the others.
    static func bank(for model: SocialWorldModel) -> NameBank { model.intl != nil ? bankV2 : bank }

    // ------------------------------------------------------------ value helpers
    static func d(_ x: Any?) -> Double {
        if let s = x as? String, let v = Double(s) { return v }
        if let n = x as? NSNumber { return n.doubleValue }
        return .nan
    }
    static func dOpt(_ x: Any?) -> Double? { (x == nil || x is NSNull) ? nil : d(x) }
    static func i(_ x: Any?) -> Int { (x as? NSNumber)?.intValue ?? (x as? String).flatMap { Int($0) } ?? Int.min }
    static func u64(_ x: Any?) -> UInt64 { (x as? String).flatMap { UInt64($0) } ?? (x as? NSNumber)?.uint64Value ?? 0 }
    static func arr(_ x: Any?) -> [Any] { x as? [Any] ?? [] }
    static func obj(_ x: Any?) -> [String: Any] { x as? [String: Any] ?? [:] }
    static func str(_ x: Any?) -> String? { x as? String }

    /// Bit equality of two doubles (+0/−0 and NaN never occur in the fixtures).
    static func same(_ a: Double?, _ b: Double?) -> Bool {
        switch (a, b) {
        case (nil, nil): return true
        case let (x?, y?): return x.bitPattern == y.bitPattern
        default: return false
        }
    }
}

/// Counts every value compared, so the report can state how many values agreed bit for bit.
final class SocTally {
    nonisolated(unsafe) static var values = 0
    static func add(_ n: Int = 1) { values += n }
}

final class SocialGoldenTests: XCTestCase {
    typealias F = SocFix

    // ------------------------------------------------------------ core.json: hashes, permutations, calendar

    func testCoreHashesPermutationsCalendar() throws {
        let core = try F.designFixture("core.json")
        XCTAssertEqual([F.arr(core["h64"]).count, F.arr(core["perm"]).count, F.arr(core["calendar"]).count], [6, 6, 5])
        for e in F.arr(core["h64"]) {
            let o = F.obj(e)
            let xs = F.arr(o["xs"]).map { F.i($0) }
            let h = SocialHash.h64(F.u64(o["seed"]), F.str(o["label"]) ?? "", xs)
            XCTAssertEqual(h, F.u64(o["h64"]), "h64 \(o)")
            XCTAssertTrue(F.same(SocialHash.unit(h), F.d(o["unit"])), "unit \(o)")
            SocTally.add(2)
        }
        for e in F.arr(core["perm"]) {
            let o = F.obj(e)
            let n = F.i(o["n"]), key = F.u64(o["key"])
            for p in F.arr(o["map"]) {
                let xy = F.arr(p).map { F.i($0) }
                XCTAssertEqual(SocialHash.perm(xy[0], n, key), xy[1], "perm(\(xy[0]), \(n), \(key))")
                SocTally.add()
            }
        }
        for e in F.arr(core["calendar"]) {
            let o = F.obj(e)
            let t = F.i(o["t"])
            XCTAssertEqual(SocialCalendar.eventDay(t), F.i(o["eventDay"]))
            XCTAssertEqual(SocialCalendar.eventWeek(t), F.i(o["eventWeek"]))
            XCTAssertEqual(SocialCalendar.eventDay(Double(t)), F.i(o["eventDay"]))
            for l in F.arr(o["local"]) {
                let v = F.arr(l)
                let (day, minute) = SocialCalendar.localDayMinute(Double(t), offsetMinutes: F.i(v[0]))
                XCTAssertEqual(day, F.i(v[1]))
                XCTAssertTrue(F.same(minute, F.d(v[2])), "local minute \(t) \(v)")
                SocTally.add(2)
            }
            SocTally.add(3)
        }
        XCTAssertEqual(F.i(core["epoch"]), SocialCalendar.epoch)
    }

    // ------------------------------------------------------------ names.json: decode, numbers, blocklist

    func testNamesDecodeNumbersBlocklist() throws {
        let names = try F.designFixture("names.json")
        XCTAssertEqual([F.arr(names["decode"]).count, F.arr(names["blocked"]).count, F.arr(names["number"]).count], [324, 11, 6])
        for e in F.arr(names["decode"]) {
            let o = F.obj(e)
            let st = F.str(o["style"])!, cul = F.str(o["culture"])!, slot = F.i(o["slot"])
            let got = SocialNames.decode(st, slot, cul == "*" ? "en" : cul, bank: F.bank)
            XCTAssertEqual(got, F.str(o["name"]), "decode \(o)")
            SocTally.add()
        }
        for e in F.arr(names["blocked"]) {
            let o = F.obj(e)
            XCTAssertEqual(SocialNames.isBlocked(F.str(o["name"])!, bank: F.bank), (o["blocked"] as? Bool) ?? false, "\(o)")
            SocTally.add()
        }
        for e in F.arr(names["number"]) {
            let o = F.obj(e)
            XCTAssertEqual(SocialNames.number(F.i(o["r"]), F.u64(o["key"])), F.str(o["s"]), "\(o)")
            SocTally.add()
        }
    }

    // ------------------------------------------------------------ world.json: cohorts, sessions, progress, names

    func testWorldCohortTableAtT() throws {
        let w = try F.designFixture("world.json")
        let T = Double(F.i(w["t"]))
        let W = SocialPopulation(model: .reference, names: F.bank)      // built exactly to T, like the fixture
        W.extend(to: T)
        XCTAssertEqual(W.cohorts.count, F.i(w["cohortCount"]))
        XCTAssertEqual(W.sharedPlayerCount, F.i(w["members"]))
        XCTAssertEqual(W.gidLimit(T), F.i(w["gidLimit"]))
        let cs = W.cohorts
        XCTAssertEqual(F.arr(w["cohorts"]).count, 60)
        for e in F.arr(w["cohorts"]) {
            let o = F.obj(e)
            guard F.i(o["idx"]) < cs.count else { XCTFail("cohort \(F.i(o["idx"])) missing"); continue }
            let c = cs[F.i(o["idx"])]
            XCTAssertEqual([c.ck, c.p, c.b, c.a, c.day, c.n, c.gid0, c.off],
                           ["ck", "p", "b", "a", "day", "n", "gid0", "off"].map { F.i(o[$0]) }, "cohort \(c.idx)")
            XCTAssertEqual(c.iso, F.str(o["iso"])); XCTAssertEqual(c.culture, F.str(o["culture"]))
            XCTAssertTrue(F.same(c.v, F.d(o["v"])) && F.same(c.pace, F.d(o["pace"])) && F.same(c.join0, F.d(o["join0"]))
                          && F.same(c.R, F.dOpt(o["R"])), "cohort \(c.idx) doubles")
            let m = F.arr(o["m"]).map { F.d($0) }, ml = F.arr(o["ml"]).map { F.d($0) }
            XCTAssertEqual(c.m.map(\.bitPattern), m.map(\.bitPattern), "cohort \(c.idx) m")
            XCTAssertEqual(c.ml.map(\.bitPattern), ml.map(\.bitPattern), "cohort \(c.idx) ml")
            let styles = F.arr(o["styles"]).map { F.arr($0) }
            let cum = W.styleCum(c), base = W.styleBase(c)
            XCTAssertEqual(cum.count, styles.count)
            for (k, s) in styles.enumerated() where k < cum.count {
                XCTAssertEqual(cum[k].style, F.str(s[0]))
                XCTAssertEqual([cum[k].lo, cum[k].hi, base[k]], [F.i(s[1]), F.i(s[2]), F.i(s[3])])
            }
            SocTally.add(14 + m.count + ml.count + styles.count * 4)
        }
    }

    func testWorldSessionsProgressNames() throws {
        let w = try F.designFixture("world.json")
        let W = F.refWorld
        W.extend(to: Double(F.i(w["t"])) + 9 * 86_400)
        let cs = W.cohorts
        XCTAssertEqual([F.arr(w["sessions"]).count, F.arr(w["progress"]).count, F.arr(w["names"]).count], [15, 800, 120])
        for e in F.arr(w["sessions"]) {
            let o = F.obj(e)
            guard F.i(o["idx"]) < cs.count else { XCTFail("cohort missing \(o)"); continue }
            let s = W.computeSessions(cs[F.i(o["idx"])], F.i(o["dl"]))
            if let want = o["sessions"] as? [String: Any] {
                guard let s = s else { XCTFail("sessions nil \(o)"); continue }
                XCTAssertEqual(s.starts.map(\.bitPattern), F.arr(want["starts"]).map { F.d($0).bitPattern }, "starts \(o["idx"]!)")
                XCTAssertEqual(s.f.map(\.bitPattern), F.arr(want["f"]).map { F.d($0).bitPattern })
                XCTAssertTrue(F.same(s.pace, F.d(want["pace"])) && F.same(s.m, F.d(want["m"])))
                SocTally.add(s.starts.count * 2 + 2)
            } else {
                XCTAssertNil(s, "rest day \(o)")
                SocTally.add()
            }
        }
        var bad = 0
        for e in F.arr(w["progress"]) {
            let o = F.obj(e)
            guard F.i(o["idx"]) < cs.count, F.i(o["j"]) < cs[F.i(o["idx"])].n else { bad += 1; continue }
            let c = cs[F.i(o["idx"])], j = F.i(o["j"]), t = F.d(o["t"])
            let P = W.progress(c, j, t)
            if !F.same(P, F.dOpt(o["P"])) || W.level(c, j, t) != F.i(o["level"]) {
                bad += 1
                if bad < 5 { XCTFail("progress idx \(c.idx) j \(j) t \(t): \(String(describing: P)) vs \(String(describing: o["P"]))") }
            }
            SocTally.add(2)
        }
        XCTAssertEqual(bad, 0, "progress/level mismatches")
        for e in F.arr(w["names"]) {
            let o = F.obj(e)
            guard F.i(o["idx"]) < cs.count, F.i(o["j"]) < cs[F.i(o["idx"])].n else { XCTFail("member missing \(o)"); continue }
            let c = cs[F.i(o["idx"])], j = F.i(o["j"])
            let (nm, st) = W.name(c, j)
            XCTAssertEqual(W.gid(c, j), F.i(o["gid"]))
            XCTAssertEqual(nm, F.str(o["name"]), "name idx \(c.idx) j \(j)")
            XCTAssertEqual(st, F.str(o["style"]))
            XCTAssertEqual(W.avatar(c, j, style: st), F.i(o["avatar"]))
            SocTally.add(4)
        }
    }

    // ------------------------------------------------------------ queries.json: counts, ranks, neighbours, top-25

    func testQueries() throws {
        let q = try F.designFixture("queries.json")
        let W = F.refWorld
        W.extend(to: Double(1_790_298_000 + 9 * 86_400))
        XCTAssertEqual([F.arr(q["rank"]).count, F.arr(q["top"]).count], [5, 3])
        for e in F.arr(q["rank"]) {
            let o = F.obj(e)
            let t = Double(F.i(o["t"])), x = F.i(o["level"]), iso = F.str(o["iso"])
            XCTAssertEqual(W.countAtLeast(x + 1, t, iso: iso), F.i(o["countGE"]), "countGE \(o)")
            XCTAssertEqual(W.rankOfLevel(x, t, iso: iso), F.i(o["rank"]))
            let (ab, be) = W.neighbours(x, t, above: 5, below: 5, iso: iso)
            XCTAssertEqual(ab.map(\.gid), F.arr(o["above"]).map { F.i($0) }, "above \(o)")
            XCTAssertEqual(be.map(\.gid), F.arr(o["below"]).map { F.i($0) }, "below \(o)")
            SocTally.add(12)
        }
        for e in F.arr(q["top"]) {
            let o = F.obj(e)
            let t = Double(F.i(o["t"])), iso = F.str(o["iso"])
            let top = W.top(t, 25, iso: iso)
            let want = F.arr(o["top"]).map { F.arr($0).map { F.i($0) } }
            XCTAssertEqual(top.map { [$0.gid, 1 + SocialHash.floorInt($0.P)] }, want, "top \(o["t"]!) \(iso ?? "world")")
            SocTally.add(want.count * 2)
        }
    }

    // ------------------------------------------------------------ events.json: groups, races, Sky Jump

    func testEvents() throws {
        let ev = try F.designFixture("events.json")
        let W = F.refWorld
        let T = Double(F.i(ev["t"])), seed = F.u64(ev["installSeed"])
        W.extend(to: T + 9 * 86_400)
        // Weekly Contest (the reference: 50 players)
        let wk = F.obj(ev["weekly"])
        XCTAssertEqual([F.arr(wk["members"]).count, F.arr(F.obj(ev["streak"])["members"]).count, F.arr(ev["sky"]).count], [49, 19, 4])
        let g = SocialGroupContest(W: W, installSeed: seed, spec: .referenceWeekly,
                                   key: SocialGroupKey(instance: F.i(wk["week"]), t0: T, ref: F.d(wk["ref"]),
                                                       windows: [[T - 7200, T - 5400], [T - 3600, T - 1800]]))
        XCTAssertEqual(g.members.map { W.gid($0.0, $0.1) }, F.arr(wk["members"]).map { F.i($0) }, "weekly members")
        XCTAssertEqual(g.arrive.map(\.bitPattern), F.arr(wk["arrive"]).map { F.d($0).bitPattern }, "weekly arrivals")
        XCTAssertEqual(g.base, F.arr(wk["base"]).map { F.i($0) })
        let st = g.standings(T + 48 * 3600, userScore: 30, userReached: T + 40 * 3600)
        XCTAssertEqual(st.map { [$0.member ?? -1, $0.score] }, F.arr(wk["standings48h"]).map { F.arr($0).map { F.i($0) } })
        SocTally.add(g.members.count * 3 + st.count * 2)
        // Streak Race (the reference: 20 players)
        let sr = F.obj(ev["streak"])
        let s = SocialGroupContest(W: W, installSeed: seed, spec: .referenceStreak,
                                   key: SocialGroupKey(instance: F.i(sr["day"]), t0: T, ref: F.d(sr["ref"])))
        XCTAssertEqual(s.members.map { W.gid($0.0, $0.1) }, F.arr(sr["members"]).map { F.i($0) }, "streak members")
        XCTAssertEqual(s.arrive.map(\.bitPattern), F.arr(sr["arrive"]).map { F.d($0).bitPattern })
        XCTAssertEqual(s.s0, F.arr(sr["s0"]).map { F.i($0) })
        XCTAssertEqual(s.q.map(\.bitPattern), F.arr(sr["q"]).map { F.d($0).bitPattern })
        XCTAssertEqual(s.members.indices.map { s.memberScore($0, T + 6 * 3600) ?? 0 }, F.arr(sr["scores6h"]).map { F.i($0) })
        let st2 = s.standings(T + 6 * 3600, userScore: 400, userReached: T + 5 * 3600)
        XCTAssertEqual(st2.map { [$0.member ?? -1, $0.score] }, F.arr(sr["standings6h"]).map { F.arr($0).map { F.i($0) } })
        SocTally.add(s.members.count * 5 + st2.count * 2)
        // Rocket Race
        let rk = F.obj(ev["rocket"])
        let rr = SocialRocketRace(W: W, installSeed: seed, raceId: F.i(rk["raceId"]), stage: F.i(rk["stage"]), t0: T,
                                  secondsPerWin: F.d(rk["spw"]))
        XCTAssertEqual(rr.rivals.map { W.gid($0.0, $0.1) }, F.arr(rk["rivals"]).map { F.i($0) }, "rocket rivals")
        XCTAssertEqual(rr.hold.map(\.bitPattern), F.arr(rk["hold"]).map { F.d($0).bitPattern })
        XCTAssertEqual(rr.delta.map(\.bitPattern), F.arr(rk["delta"]).map { F.d($0).bitPattern })
        XCTAssertEqual(rr.natural.map { $0?.bitPattern }, F.arr(rk["natural"]).map { F.dOpt($0)?.bitPattern })
        for p in F.arr(rk["progress"]) {
            let v = F.arr(p)
            let m = Double(F.i(v[0]))
            XCTAssertEqual((0..<4).map { rr.rivalProgress($0, T + m * 60, userNminus1: nil) }, F.arr(v[1]).map { F.i($0) }, "min \(m)")
            SocTally.add(4)
        }
        SocTally.add(16)
        // Sky Jump
        for e in F.arr(ev["sky"]) {
            let o = F.obj(e)
            let sj = SocialSkyJump(installSeed: seed, attemptId: F.i(o["attempt"]), stage: F.i(o["stage"]))
            XCTAssertEqual(sj.alive, F.arr(o["alive"]).map { F.i($0) })
            XCTAssertEqual(sj.share, F.i(o["share"]))
            SocTally.add(sj.alive.count + 1)
        }
    }
}
