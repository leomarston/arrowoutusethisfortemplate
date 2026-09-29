import XCTest
@testable import PathCore

// SOC1 (§12.2 acceptance "a 50-row page <= 1 ms on macOS -O"; SPEC-architecture §4.11 invariant 7; SPEC-social §3.2 query
// budgets at a 3-year world). Budgets are asserted only in optimised builds (`swift test -c release`); Debug prints.
// Each metric is the best of 3 trials of n queries (p50/p95 of the best trial; the machine is shared).
// Timings go to $PC_EVIDENCE_DIR/soc1-perf.json when the variable is set.
// PUBLISH B2: the SHIPPED world is v2 (country blocks: a Country query now walks every cohort of the country's band, and
// M9's shards double the cohorts per week). Every moment is taken at the SAME WORLD AGE as SOC1's (v2's world starts 19
// weeks later), the 3-year budgets are asserted on the v2 world, and the cohort table's memory is measured (and gated).
// T6's warning (59.5k cohorts by 2031 vs 33k) is measured at 2031-09-25 too.

final class SocialPerfTests: XCTestCase {
    typealias F = SocFix

    static func time(_ n: Int, _ body: () -> Void) -> (p50: Double, p95: Double, max: Double) {
        var ms: [Double] = []
        for _ in 0..<n {
            let a = DispatchTime.now().uptimeNanoseconds
            body()
            ms.append(Double(DispatchTime.now().uptimeNanoseconds - a) / 1e6)
        }
        ms.sort()
        return (ms[ms.count / 2], ms[min(ms.count - 1, (ms.count * 95) / 100)], ms[ms.count - 1])
    }

    func testPageAndQueryBudgets() throws {
        #if DEBUG
        let optimised = false
        #else
        let optimised = true
        #endif
        var report: [String: Any] = ["optimised": optimised]
        let world = SocialWorld(installSeed: 12345, config: .default, names: F.bankV2)
        let age = Int64(19 * 604_800)                           // v2's world starts 19 weeks after the calibrated one
        let now = SocialTime(seconds: 1_790_307_060 + age)      // 2026-09-25 03:31 UTC (the phone session) at v2's world age
        var st = SocialState()
        st.setHomeIfNeeded(region: "TR", offsetMinutes: 180)
        for k in 0..<40 { st.recordWin(level: 22 + k, firstTry: true, points: 25, at: SocialTime(seconds: now.seconds - 20_000 + Int64(k) * 300)) }
        st.joinWeekly(week: SocialCalendar.eventWeek(Int(now.seconds)), level: 62, at: SocialTime(seconds: now.seconds - 3000))
        let me = st.standing(installSeed: 12345, level: 62)
        world.warmUp(to: now)
        _ = world.page(.world, me: me, at: now, ranks: 1...50)            // warm the caches of this moment's data
        /// `budget` applies to the p95 unless `onMedian` (steady state; the first query of a 6-hour window computes the
        /// exact pruning bounds for every active cohort and is reported as the max).
        func t(_ key: String, _ n: Int, budget: Double?, onMedian: Bool = false, _ body: () -> Void) {
            // best of 3 trials (the machine is shared with other build lanes; the first trial also carries the first
            // query of the 6-hour window, reported in `firstTrialMax_ms`)
            var trials: [(p50: Double, p95: Double, max: Double)] = []
            for _ in 0..<3 { trials.append(Self.time(n, body)) }
            let r = trials.min { onMedian ? $0.p50 < $1.p50 : $0.p95 < $1.p95 }!
            report[key + ".firstTrialMax_ms"] = trials[0].max
            report[key] = ["p50_ms": r.p50, "p95_ms": r.p95, "max_ms": r.max, "budget_ms": budget as Any,
                           "budget_on": onMedian ? "p50" : "p95"]
            print(String(format: "[SOC1][perf] %@ p50 %.3f p95 %.3f max %.3f ms%@", key, r.p50, r.p95, r.max,
                         budget.map { String(format: " (budget %.1f on %@)", $0, onMedian ? "p50" : "p95") } ?? ""))
            if optimised, let b = budget { XCTAssertLessThanOrEqual(onMedian ? r.p50 : r.p95, b, "\(key) over budget") }
        }
        var s = 0
        // 50-row pages at the phone session's world age (≈330k players)
        t("page50.world.top", 40, budget: 1.0) { s += world.page(.world, me: me, at: SocialTime(seconds: now.seconds + Int64(s % 7)), ranks: 1...50).rows.count }
        t("page50.country.aroundMe", 40, budget: 1.0) { s += world.page(.country("TR"), me: me, at: now, around: 400, radius: 25).rows.count }
        // World around the player (SPEC-social §3.3's "R−10 … R+10" window; the phone's World shows no player row, so the
        // app may never ask): the page call carries its own rank count, measured apart
        let myWorldRank = world.rank(level: 62, country: nil, me: me, at: now)
        t("rank.world", 40, budget: nil) { s += world.rank(level: 62, country: nil, me: me, at: now) }
        t("page50.world.aroundMe", 40, budget: 1.0) { s += world.page(.world, me: me, at: now, around: myWorldRank, radius: 25).rows.count }
        t("page21.world.aroundMe", 40, budget: nil) { s += world.page(.world, me: me, at: now, around: myWorldRank, radius: 10).rows.count }
        t("page.weekly10", 40, budget: 1.0) { s += world.page(.weekly(week: SocialCalendar.eventWeek(Int(now.seconds))), me: me, at: now, ranks: 1...10).rows.count }
        let sk = SocialGroupKey(instance: SocialCalendar.eventDay(Int(now.seconds)), t0: Double(now.seconds - 60_000), ref: 30)
        t("page.streak50", 40, budget: 1.0) { s += world.streakBoard(key: sk, me: me, at: now).rows.count }
        // 3-year world (2029-09-25, ≈3 M players): SPEC-social §3.2 budgets (iPhone 15: rank 8, top-100 10, country 2,
        // neighbours 3 ms) — macOS is faster, so these are asserted at the device figures
        let W = F.world("v2")
        let t3 = 1_884_931_200.0 + Double(age)                   // 2029-09-25 00:00 UTC at v2's world age (2030-02-05)
        W.extend(to: t3 + 2 * 86_400)
        _ = W.rankOfLevel(3000, t3)
        t("y3.worldRank", 20, budget: 8.0) { s += W.rankOfLevel(3000, t3 + Double(s % 5)) }
        t("y3.top100", 10, budget: 10.0) { s += W.top(t3 + Double(s % 5), 100).count }
        t("y3.countryRank", 20, budget: 2.0) { s += W.rankOfLevel(3000, t3 + Double(s % 5), iso: "TR") }
        t("y3.neighbours", 20, budget: 3.0) { s += W.neighbours(3000, t3 + Double(s % 5), above: 10, below: 10, iso: "TR").above.count }
        let refs = W.top(t3, 50)
        t("y3.materialise50rows", 20, budget: 1.0) {
            s += refs.map { W.name($0.c, $0.j).name.count + W.avatar($0.c, $0.j, style: "default") }.reduce(0, +)
        }
        // World neighbours (the World list's R±10 window) are not in SOC's gate list (its neighbours budget is the Country
        // query, gated above): reported only (≈1.8-2.3 ms p50 on a quiet Mac, off the main thread per V-29)
        t("y3.worldNeighbours", 20, budget: nil) { s += W.neighbours(3000, t3 + Double(s % 5), above: 10, below: 10).above.count }
        // the phone's screens on a 3-year world: World pages from the top, Country opened at the player's row
        let world3 = SocialWorld(installSeed: 99, config: .default, names: F.bankV2)
        let at3 = SocialTime(seconds: Int64(t3))
        let me3 = PlayerStanding(name: "Hsheh", avatar: 3, country: "TR", level: 3000, ledger: [])
        world3.warmUp(to: at3)
        let r3 = world3.page(.country("TR"), me: me3, at: at3, ranks: 1...1).myRank
        _ = world3.page(.world, me: me3, at: at3, ranks: 1...50)
        // CONSISTENCY V-29 (ruled 09:55): "≤ 1 ms on macOS for a World page is unlikely at a 3-year world" → the binding
        // gates are 0 ms on the main thread + SOC's per-query numbers (above); the 3-year pages keep ARCH's DEVICE figure
        // (a 50-row page ≤ 2 ms) as a regression guard
        t("y3.page50.world.top", 20, budget: 2.0) { s += world3.page(.world, me: me3, at: at3, ranks: 51...100).rows.count }
        t("y3.page50.country.aroundMe", 20, budget: 2.0) { s += world3.page(.country("TR"), me: me3, at: at3, around: r3, radius: 25).rows.count }
        report["cohorts_y3"] = W.cohorts.count
        report["players_y3"] = W.sharedPlayerCount
        report["blocks_y3"] = W.blk.count
        // T6's warning: the v2 world in 2031 (59.5k cohorts, 4.5 M players) — the device budgets hold there too
        let W5 = SocialPopulation(model: .shipped, names: F.bankV2)
        let t5 = 1_948_003_200.0                                 // 2031-09-25 00:00 UTC
        W5.extend(to: t5 + 2 * 86_400)
        _ = W5.rankOfLevel(3000, t5); _ = W5.rankOfLevel(3000, t5, iso: "TR"); _ = W5.top(t5, 100)
        t("y2031.worldRank", 20, budget: 8.0) { s += W5.rankOfLevel(3000, t5 + Double(s % 5)) }
        t("y2031.top100", 10, budget: 10.0) { s += W5.top(t5 + Double(s % 5), 100).count }
        t("y2031.countryRank", 20, budget: 2.0) { s += W5.rankOfLevel(3000, t5 + Double(s % 5), iso: "TR") }
        t("y2031.neighbours", 20, budget: 3.0) { s += W5.neighbours(3000, t5 + Double(s % 5), above: 10, below: 10, iso: "TR").above.count }
        t("y2031.countryTop100.US", 10, budget: 10.0) { s += W5.top(t5 + Double(s % 5), 100, iso: "US").count }
        report["cohorts_y2031"] = W5.cohorts.count
        report["players_y2031"] = W5.sharedPlayerCount
        XCTAssertGreaterThan(s, 0)
        XCTAssertGreaterThan(W5.cohorts.count, 55_000, "the 2031 world T6 warned about")
        if let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty {
            let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: URL(fileURLWithPath: dir).appendingPathComponent(optimised ? "soc1-perf-release.json" : "soc1-perf-debug.json"))
        }
    }

    /// Bytes held by live heap allocations (malloc's size in use): a world's delta is exactly what it allocated and still
    /// holds (the process footprint moves in pages and reuses freed ones, so it cannot attribute a table).
    static func heapInUse() -> Int {
        var st = malloc_statistics_t()
        malloc_zone_statistics(nil, &st)
        return Int(st.size_in_use)
    }

    /// PUBLISH B2 (PLAN-P B2 "+ memory"): the cohort table's memory, before (the calibrated v1 world) and after (the shipped
    /// v2 world), at the launch week, 1 year and 3 years of world age, plus the v2 world in 2031. A world is built, queried
    /// once (World top 100, a TR rank, TR neighbours: the memo layers fill) and measured as the heap it holds.
    func testCohortTableMemory() throws {
        #if DEBUG
        let optimised = false
        #else
        let optimised = true
        #endif
        var report: [String: Any] = ["optimised": optimised]
        func measure(_ model: SocialWorldModel, _ t: Double) -> (mb: Double, cohorts: Int, players: Int) {
            let before = Self.heapInUse()
            var W: SocialPopulation? = SocialPopulation(model: model, names: F.bank(for: model))
            W!.extend(to: t + 2 * 86_400)
            _ = W!.top(t, 100); _ = W!.rankOfLevel(62, t); _ = W!.rankOfLevel(62, t, iso: "TR")
            _ = W!.neighbours(62, t, above: 10, below: 10); _ = W!.neighbours(62, t, above: 10, below: 10, iso: "TR")
            let after = Self.heapInUse()
            let r = (Double(after - before) / 1_048_576, W!.cohorts.count, W!.sharedPlayerCount)
            W = nil
            return r
        }
        let week = 604_800.0
        var rows: [[String: Any]] = []
        for (label, ageWeeks) in [("launch", 4.0), ("1y", 52.0), ("3y", 156.0)] {
            let cal = measure(.calibrated, Double(SocialWorldModel.calibrated.epoch) + ageWeeks * week)
            let v2 = measure(.shipped, Double(SocialWorldModel.shipped.epoch) + ageWeeks * week)
            rows.append(["age": label, "calibratedMB": cal.mb, "calibratedCohorts": cal.cohorts, "v2MB": v2.mb, "v2Cohorts": v2.cohorts,
                         "v2Players": v2.players])
            print(String(format: "[B2][memory] %@: calibrated %.1f MB (%d cohorts) -> v2 %.1f MB (%d cohorts, %d players)",
                         label, cal.mb, cal.cohorts, v2.mb, v2.cohorts, v2.players))
            // Budget: never more than the calibrated v1 world held at the same world age BEFORE B2 (B2 measured 28.5 MB at 1
            // year and 86.7 MB at 3 years with the per-cohort session caches and the four pattern arrays; build/p/B2), though
            // v2 has twice its cohorts (M9's shards): the shared session cache, one pattern array, the shared archetypes
            // and the compact style table pay for them
            if label == "1y" { XCTAssertLessThanOrEqual(v2.mb, 28, "v2 world at 1 year: \(v2.mb) MB") }
            if label == "3y" { XCTAssertLessThanOrEqual(v2.mb, 86, "v2 world at 3 years: \(v2.mb) MB") }
        }
        let y31 = measure(.shipped, 1_948_003_200)
        rows.append(["age": "2031-09-25", "v2MB": y31.mb, "v2Cohorts": y31.cohorts, "v2Players": y31.players])
        print(String(format: "[B2][memory] 2031-09-25: v2 %.1f MB (%d cohorts)", y31.mb, y31.cohorts))
        report["rows"] = rows
        if let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty {
            let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: URL(fileURLWithPath: dir).appendingPathComponent(optimised ? "b2-memory-release.json" : "b2-memory-debug.json"))
        }
    }
}
