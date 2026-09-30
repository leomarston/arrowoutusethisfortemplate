import XCTest
@testable import GameCore
@testable import ArrowEscape

// PUBLISH B2 (PLAN-P §4.4 "new calibration guards"; social-intl §6.3 item 6; SPEC.md ruling 43). The shipped v2 world must
// feel online in EVERY country, not only the big English-first ones — the per-country realism guards of
// design/social/tools/v2/calib_v2.py, ported one to one (the Swift world is the Python world bit for bit, so these numbers
// are the reference's own; build/p/T6/calib.json has the Python run):
//   for every country with >= 1,000 players at the start of a reference week (launch week Mon 2026-10-05 07:00 UTC = world
//   age 4 weeks; age 22 weeks; age 52 weeks), over the week's 7 local days:
//     * dead daytime hours <= 20 of 112 (local 08:00-24:00 on the country's model offset: an hour is dead when no row of the
//       Country top 100 gained a level during it);
//     * same-cohort adjacent pairs in the Country top 20 <= 8 of 19 (worst of the 7 local 20:00s) — the audit's "ladders";
//     * no run of more than 3 equal non-zero level gaps in the Country top 20 (worst of 7);
//     * ruling 43: no first name more than 5 times in the Country top 200 (local 20:00, day 0) — the literal "<= 4 % of the
//       first-name rows" is reported, not asserted (it fails 92 % of boards drawn from REAL name frequencies);
//   and for every country (analytic, no sampling): the expected share of its most common first name <= 4 %.
// Default run: the launch week (the boards the first players meet). PC_SOC_CALIB_FULL=1: all three weeks (-O recommended).
// PC_EVIDENCE_DIR=<dir> writes b2-calibration-<weeks>.json.

final class SocialIntlCalibrationTests: XCTestCase {
    typealias F = SocFix

    static let weeks: [(label: String, start: Double)] = [
        ("launch", 1_791_183_600),                                       // Mon 2026-10-05 07:00 UTC (world age 4 weeks)
        ("age22", Double(SocialWorldModel.shipped.epoch + 22 * SocialCalendar.week)),
        ("age52", Double(SocialWorldModel.shipped.epoch + 52 * SocialCalendar.week)),
    ]

    /// calib_v2.iso_offset: the offset of the country's heaviest row.
    static func isoOffset(_ iso: String) -> Int {
        var best: SocialCountryRow?
        for r in SocialWorldModel.shipped.countries where r.iso == iso && (best == nil || r.weight > best!.weight) { best = r }
        return best!.offsetMinutes
    }

    /// calib_v2.first_token: the key of the first name a member's nickname is built on (given / name+suffix / underscore
    /// styles), or nil.
    static func firstToken(_ W: SocialPopulation, _ c: SocialCohort, _ j: Int) -> String? {
        let (st, _) = W.styleOf(c, j)
        guard SocialNames.popularStyles.contains(st), let d = W.names.store, let draw = W.model.nameStyle.draw else { return nil }
        let cu = W.cultureOf(c, j)
        guard let t = SocialNames.drawIndex(st, cu, key: SocialHash.h64(W.seed, SocialLabels.nick, W.ident(c, j)), bank: W.names,
                                            draw: draw)?.token else { return nil }
        let lat = st == "mixed" ? d.mixedTokens[cu]![t] : d.cultures[cu]![t].folded
        return SocialNames.key(lat)
    }

    struct CountryWeek {
        var dead = 0, medianMovers = 0, ladderWorst = 0, runWorst = 0, firstNameRows = 0, topNameCount = 0
        var topNameShare = 0.0
        var structureOK: Bool { dead <= 20 && ladderWorst <= 8 && runWorst <= 3 }
        var nameOK: Bool { topNameCount <= 5 }
    }

    /// calib_v2.country_week.
    static func countryWeek(_ W: SocialPopulation, _ iso: String, _ ws: Double) -> CountryWeek {
        let off = Double(isoOffset(iso) * 60)
        var r = CountryWeek()
        var movers: [Int] = []
        let base = ws - 7 * 3600
        for day in 0..<7 {
            for hh in 8..<24 {
                let t = base + Double(day * 86_400 + hh * 3600) - off
                let n = W.top(t, 100, iso: iso).filter { W.level($0.c, $0.j, t) > W.level($0.c, $0.j, t - 3600) }.count
                movers.append(n)
                if n == 0 { r.dead += 1 }
            }
            let t20 = base + Double(day * 86_400 + 20 * 3600) - off
            let tp = W.top(t20, 20, iso: iso)
            let lv = tp.map { W.level($0.c, $0.j, t20) }
            r.ladderWorst = max(r.ladderWorst, zip(tp, tp.dropFirst()).filter { $0.c === $1.c }.count)
            let gaps = zip(lv, lv.dropFirst()).map { $0 - $1 }
            var best = 0, cur = 0
            for k in gaps.indices {
                if gaps[k] > 0 && k > 0 && gaps[k] == gaps[k - 1] { cur += 1 } else { cur = gaps[k] > 0 ? 1 : 0 }
                best = max(best, cur)
            }
            r.runWorst = max(r.runWorst, best)
        }
        r.medianMovers = movers.sorted()[movers.count / 2]
        let t20 = base + Double(20 * 3600) - off
        let toks = W.top(t20, 200, iso: iso).compactMap { firstToken(W, $0.c, $0.j) }
        var cnt: [String: Int] = [:]
        for k in toks { cnt[k, default: 0] += 1 }
        r.firstNameRows = toks.count
        r.topNameCount = cnt.values.max() ?? 0
        r.topNameShare = toks.isEmpty ? 0 : Double(r.topNameCount) / Double(toks.count)
        return r
    }

    func testEveryCountryFeelsOnline() throws {
        let full = ProcessInfo.processInfo.environment["PC_SOC_CALIB_FULL"] == "1"
        let weeks = full ? Self.weeks : [Self.weeks[0]]
        let W = F.world("v2")
        W.extend(to: weeks.map(\.start).max()! + 8 * 86_400)
        let isos = Array(Set(SocialWorldModel.shipped.countries.map(\.iso))).sorted()
        var evidence: [String: Any] = [:]
        var failures: [String] = []
        for wk in weeks {
            let big = isos.map { ($0, W.joined(wk.start, iso: $0)) }.filter { $0.1 >= 1000 }.sorted { $0.1 > $1.1 }
            XCTAssertGreaterThanOrEqual(big.count, 10, "\(wk.label): countries with >= 1,000 players")
            var rows: [String: Any] = [:]
            for (iso, n) in big {
                let r = Self.countryWeek(W, iso, wk.start)
                rows[iso] = ["players": n, "deadHours": r.dead, "medianMovers": r.medianMovers, "ladderPairsWorst": r.ladderWorst,
                             "equalGapRunWorst": r.runWorst, "firstNameRows": r.firstNameRows, "topFirstNameCount": r.topNameCount,
                             "topFirstNameShare": r.topNameShare] as [String: Any]
                if !r.structureOK { failures.append("\(wk.label) \(iso): dead \(r.dead) ladder \(r.ladderWorst) run \(r.runWorst)") }
                if !r.nameOK { failures.append("\(wk.label) \(iso): a first name \(r.topNameCount)x in the top 200") }
                print(String(format: "[B2][calibration] %@ %@ %d players: dead %d/112, movers/h %d, ladder %d/19, run %d, top first name x%d of %d rows (%.1f %%)",
                             wk.label, iso, n, r.dead, r.medianMovers, r.ladderWorst, r.runWorst, r.topNameCount, r.firstNameRows,
                             100 * r.topNameShare))
            }
            evidence[wk.label] = rows
        }
        XCTAssertEqual(failures, [], "the per-country realism guards (calib_v2.py; ruling 43)")
        if let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty {
            let data = try JSONSerialization.data(withJSONObject: evidence, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: URL(fileURLWithPath: dir).appendingPathComponent("b2-calibration-\(full ? "full" : "launch").json"))
        }
    }

    /// calib_v2.draw_probs: P(first-name index t) of the v2 draw (M7) for a list of n names.
    static func drawProbs(_ n: Int, _ D: SocialNameStyle.Draw) -> [Double] {
        let H = max(1, min(D.headN, n / 6))
        let hp = Double(D.headP * min(n, 300) / 300) / 100.0
        let tu = Double(D.tailUniformP) / 100.0
        var p = [Double](repeating: 0, count: n)
        for i in 0..<H { p[i] += hp / Double(H) }
        for i in 0..<n {
            p[i] += (1.0 - hp) * (tu / Double(n) + (1.0 - tu) * ((Double(i + 1) / Double(n)).squareRoot() - (Double(i) / Double(n)).squareRoot()))
        }
        return p
    }

    /// Ruling 43, second half: per country, the EXPECTED share of its most common first name among its first-name rows
    /// (given / name+suffix / underscore styles, weighted by the style mix and the rows' culture mixes) <= 4 %.
    func testExpectedMostCommonFirstNameShare() throws {
        let m = SocialWorldModel.shipped
        let d = try XCTUnwrap(F.bankV2.store)
        let draw = try XCTUnwrap(m.nameStyle.draw)
        let wStyle = m.nameStyle.weights.filter { SocialNames.popularStyles.contains($0.style) }
        let totW = wStyle.reduce(0) { $0 + $1.weight }
        var cache: [String: [String: Double]] = [:]
        func dist(_ cu: String) -> [String: Double] {
            if let hit = cache[cu] { return hit }
            var out: [String: Double] = [:]
            for sw in wStyle {
                let toks = sw.style == "mixed" ? d.mixedTokens[cu]! : d.cultures[cu]!.map(\.folded)
                for (t, q) in Self.drawProbs(toks.count, draw).enumerated() { out[SocialNames.key(toks[t]), default: 0] += sw.weight / totW * q }
            }
            cache[cu] = out
            return out
        }
        var worst = (iso: "", share: 0.0)
        var over: [String] = []
        for iso in Set(m.countries.map(\.iso)).sorted() {
            let rows = m.countries.filter { $0.iso == iso }
            let wsum = rows.reduce(0) { $0 + $1.weight }
            var agg: [String: Double] = [:]
            for r in rows {
                let mix = r.mix ?? [SocialCultureShare(culture: r.culture, weight: 1)]
                let mt = mix.reduce(0) { $0 + $1.weight }
                for x in mix { for (k, q) in dist(x.culture) { agg[k, default: 0] += r.weight / wsum * x.weight / mt * q } }
            }
            let top = agg.values.max() ?? 0
            if top > worst.share { worst = (iso, top) }
            if top > 0.04 { over.append("\(iso) \(top)") }
        }
        XCTAssertEqual(over, [], "expected most-common first-name share > 4 %")
        print(String(format: "[B2][calibration] expected most-common first-name share: max %.4f (%@)", worst.share, worst.iso))
    }
}
