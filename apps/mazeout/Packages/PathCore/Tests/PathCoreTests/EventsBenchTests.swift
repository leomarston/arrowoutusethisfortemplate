import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// B1 EVENTS-P — events.md §8.4 A9, re-stated for the v582 rules (build/p/PH0/balloon.md; SPEC.md ruling 42c). The §5 bench
/// targets tuned the puffs/balloons model's GOALS; v582's rules are the original's (ruling 37b: rules 1:1, platforms 2 … 120
/// VERIFIED), so nothing is tuned here: the bench checks that Up & Away, played through the REAL C3 hooks with the shipped
/// rotation for 52 weeks by SocialBenchTests' three players, is reachable for everyone and never out-pays Treasure Climb
/// (PLAN-P risk 10: "coin inflow swings between Claw and Balloon weeks").
///   players (SocialBenchTests' profiles): active (plays 97 % of days, 2-4 sessions, first-try 0.88 / Hard 0.72), casual (62 %,
///   1-2 sessions, 0.80 / 0.60), absent (3 active weeks, 4 away, 1 back every other day, 6 away, then a day a fortnight;
///   0.82 / 0.62). A session = 4-9 levels; a level is retried until won; every failed attempt is a loss (Events.onLoss).
/// Measured (B1, 2026-09-28; 25 Up & Away + 27 Treasure Climb weeks of the calendar from week 23):
///   active  Up & Away: mean 5.0 platforms, ≥1/≥2/≥3 in 100 % of its weeks, 198 coins + ∞ 0.5 h + 1.7 boosters a week;
///           Treasure Climb 2,130 coins + ∞ 10.7 h + 4.6 boosters a week
///   casual  Up & Away: mean 3.0, ≥1 100 %, ≥2 96 %, ≥3 72 %, 74 coins; Treasure Climb 315 coins
///   absent  Up & Away (7 played weeks): mean 3.1, ≥1 100 %, 64 coins; Treasure Climb (16 played) 131 coins
/// The guards below sit well inside those numbers (regression guards, not tuning). Writes the table to
/// $PC_EVIDENCE_DIR/events-bench.txt (C3.evidence) when set.
final class EventsBenchTests: XCTestCase {
    struct Profile {
        let name: String, playP: Double?, sessions: (Int, Int), first: Double, hardFirst: Double, seed: UInt64
    }
    static let profiles = [
        Profile(name: "active", playP: 0.97, sessions: (2, 4), first: 0.88, hardFirst: 0.72, seed: 1),
        Profile(name: "casual", playP: 0.62, sessions: (1, 2), first: 0.80, hardFirst: 0.60, seed: 2),
        Profile(name: "absent", playP: nil, sessions: (1, 2), first: 0.82, hardFirst: 0.62, seed: 3),
    ]

    struct RNG {
        var s: UInt64
        mutating func next() -> UInt64 { s = s &+ 0x9E37_79B9_7F4A_7C15; return SocialHash.mix(s) }
        mutating func unit() -> Double { SocialHash.unit(next()) }
        mutating func int(_ a: Int, _ b: Int) -> Int { a + Int(next() % UInt64(b - a + 1)) }
    }

    static func isHard(_ l: Int) -> Bool { l % 5 == 4 }

    struct WeekResult {
        var ladder: EventID?
        var platforms = 0          // Up & Away: platforms paid this week
        var clawSteps = 0
        var bestStreak = 0
        var ladderCoins = 0
        var ladderLives: Double = 0
        var ladderBoosters = 0
        var played = false
    }

    func run(_ p: Profile, weeks: Int = 52) -> [WeekResult] {
        var r = EconomyRules.default
        r.events.rotation.enabled = true                                      // the shipped calendar (social.json)
        var s = C3.fresh(r)
        s.level = 33
        var rng = RNG(s: p.seed &* 7919)
        let start = 1_791_223_200.0                                           // Mon 2026-10-05 12:00 UTC (week 23)
        var out: [WeekResult] = []
        var level = 33
        var seenClaims = 0
        for day in 0..<(weeks * 7) {
            let t0 = start + Double(day) * 86_400
            let w = EventRotation.week(SocialTime(seconds: Int64(t0)), r.events)
            if out.count <= day / 7 { out.append(WeekResult(ladder: EventRotation.live(week: w, level: level, rules: r.events).ladder)) }
            let plays: Bool
            if let pp = p.playP { plays = rng.unit() < pp } else {
                let wk = day / 7
                plays = wk < 3 || (wk == 7 && day % 2 == 0) || (wk >= 14 && day % 14 == 0)
            }
            guard plays else { continue }
            out[day / 7].played = true
            Economy.grant(&s, .unlimited(86_400), now: Date(timeIntervalSince1970: t0))   // lives are not this bench's subject
            var t = t0
            for _ in 0..<rng.int(p.sessions.0, p.sessions.1) {
                for _ in 0..<rng.int(4, 9) {
                    var attempt = 0
                    while true {
                        t += 90
                        let pWin = attempt == 0 ? (Self.isHard(level) ? p.hardFirst : p.first) : 0.85
                        let now = Date(timeIntervalSince1970: t)
                        if rng.unit() < pWin {
                            s.level = level + 1
                            _ = Events.onWin(&s, WinContext(levels: [level], tag: Self.isHard(level) ? .hard : .normal, firstTry: attempt == 0,
                                                            now: now), rivals: StubRivals(), rules: r)
                            level += 1
                            break
                        }
                        _ = Events.onLoss(&s, LossContext(levels: [level], reason: .timeUp, now: now), rules: r)
                        attempt += 1
                    }
                }
                t += 3 * 3600
            }
            // this day's ladder claims (collected at once, like the home queue does)
            let wk = day / 7
            for c in s.events.claims.dropFirst(seenClaims) where c.kind == .balloonStep || c.kind == .clawStep {
                out[wk].ladderCoins += c.grant.coins
                out[wk].ladderLives += c.grant.unlimitedLives
                out[wk].ladderBoosters += c.grant.boosters.values.reduce(0, +)
            }
            seenClaims = s.events.claims.count
            out[wk].platforms = max(out[wk].platforms, s.events.balloon.paid)
            out[wk].clawSteps = max(out[wk].clawSteps, s.events.claw.step)
            out[wk].bestStreak = max(out[wk].bestStreak, s.events.balloon.best)
        }
        return out
    }

    func testFiftyTwoWeeksOfTheRotationThroughTheRealHooks() {
        var report = ["profile  week-kind  weeks  played  mean-platforms  >=1  >=2  >=3  mean-coins  mean-inf-h  mean-boosters"]
        for p in Self.profiles {
            let weeks = run(p)
            XCTAssertEqual(weeks.count, 52)
            let up = weeks.filter { $0.ladder == .balloonRise && $0.played }
            let claw = weeks.filter { $0.ladder == .clawChallenge && $0.played }
            XCTAssertGreaterThan(up.count, 0, p.name)
            XCTAssertGreaterThan(claw.count, 0, p.name)
            func mean(_ a: [Double]) -> Double { a.isEmpty ? 0 : a.reduce(0, +) / Double(a.count) }
            func share(_ a: [WeekResult], _ k: Int) -> Double { Double(a.filter { $0.platforms >= k }.count) / Double(max(1, a.count)) }
            let upCoins = mean(up.map { Double($0.ladderCoins) }), clawCoins = mean(claw.map { Double($0.ladderCoins) })
            for (kind, set) in [("upAway", up), ("claw", claw)] {
                report.append(String(format: "%-8@ %-10@ %5d  %6d  %14.2f  %.2f %.2f %.2f  %10.0f  %10.2f  %13.2f", p.name as NSString,
                                     kind as NSString, weeks.filter { $0.ladder == (kind == "upAway" ? .balloonRise : .clawChallenge) }.count,
                                     set.count, mean(set.map { Double($0.platforms) }), share(set, 1), share(set, 2), share(set, 3),
                                     mean(set.map { Double($0.ladderCoins) }), mean(set.map { $0.ladderLives / 3600 }),
                                     mean(set.map { Double($0.ladderBoosters) })))
            }
            // (1) Up & Away never out-pays Treasure Climb (the reachable week, not an inflation source)
            XCTAssertLessThanOrEqual(upCoins, max(clawCoins, 1), "\(p.name): Up & Away \(upCoins) > Treasure Climb \(clawCoins) coins a week")
            // (2) reachable: every player opens a chest in most of the Up & Away weeks it plays; the active player gets further
            switch p.name {
            case "active":
                XCTAssertGreaterThanOrEqual(share(up, 2), 0.90, "active: platform 2 (5 in a row)")
                XCTAssertGreaterThanOrEqual(share(up, 3), 0.60, "active: platform 3 (8 in a row)")
            case "casual":
                XCTAssertGreaterThanOrEqual(share(up, 1), 0.80, "casual: platform 1 (2 in a row)")
                XCTAssertGreaterThanOrEqual(share(up, 2), 0.40, "casual: platform 2 (5 in a row)")
            default:
                XCTAssertGreaterThanOrEqual(share(up, 1), 0.60, "absent: platform 1 in the weeks it plays")
            }
            // (3) the last chest (120 in a row) stays the rare prize it is in the original: no profile completes a week
            XCTAssertFalse(up.contains { $0.platforms == 10 }, "\(p.name) completed Up & Away")
        }
        C3.evidence("events-bench.txt", report.joined(separator: "\n") + "\n")
        print(report.joined(separator: "\n"))
    }
}
