import XCTest
import Foundation
@testable import PathCore

/// CORE-2, SPEC.md ruling 30 (K-4): the hourglass used BEFORE the first tap. Its flight (B → B + `boosters.freezeFlight`
/// 1.6 s) counts from the use, its 10 s countdown from the first tap (`LevelClock.freeze(_:lead:)`, `freezeLead`,
/// `freezeWaitsForFirstTap`; `LevelSession.useBooster(_:hintPolicy:freezeFlightFromUse:)`). The numbers are GameG2Tests'
/// (the app's BoosterDirector tests): a first tap after the flight leaves 10 s of freeze, one 0.5 s into the flight
/// 1.1 + 10 s, and the level timer never moves while frozen. `useBooster(_:)` (the plain freeze) keeps its semantics, and a
/// lead changes nothing once the timer runs. Frames = the display link's dt at 60 Hz, as the app feeds `tick`.
final class FreezeLeadTests: XCTestCase {
    typealias F = C2Fixtures
    let a0 = ArrowID(0), a1 = ArrowID(1)
    let frame = 1.0 / 60

    /// SessionTests' crossing board: a0 → blocked by a1; a1 free. 180 s, 3 hearts.
    func crossing() -> LevelSpec {
        F.level(6, 3, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(4, 0), (4, 1), (4, 2)], .down)], timer: 180, n: 32)
    }

    /// start → intro → `.ready`: the timer armed at 180, frozen until the first tap.
    func ready(_ rules: RulesTuning = .default) -> LevelSession {
        let lv = crossing()
        let s = LevelSession(plan: SessionPlan(id: "S", levels: [lv.level]), stages: [lv], setup: AttemptSetup(levels: [lv.level]),
                             rules: rules)
        _ = s.start()
        XCTAssertEqual(s.ack(.introFinished), [.timerArmed(stage: 0, seconds: 180)])
        XCTAssertEqual(s.phase, .ready(stage: 0))
        return s
    }

    @discardableResult
    func frames(_ s: LevelSession, _ n: Int) -> [SessionEvent] { (0..<n).flatMap { _ in s.tick(frame) } }

    /// The app's call (BoosterDirector after FIX-A2).
    func ruled(_ s: LevelSession, _ b: BoosterID = .freeze) -> [SessionEvent] {
        s.useBooster(b, hintPolicy: .unblocksMost, freezeFlightFromUse: true)
    }

    // MARK: the clock

    func testTheLeadCountsBeforeTheFirstTapAndTheRestWaitsForIt() {
        var c = LevelClock(limit: 180)
        c.freeze(11.6, lead: 1.6)
        XCTAssertEqual(c.freezeRemaining, 11.6)
        XCTAssertEqual(c.freezeLead, 1.6)
        XCTAssertTrue(c.isFrozen)
        XCTAssertFalse(c.freezeWaitsForFirstTap, "the flight is still flying")
        XCTAssertEqual(c.tick(1), [])
        XCTAssertEqual(c.freezeRemaining, 10.6, accuracy: 1e-9)
        XCTAssertEqual(c.freezeLead, 0.6, accuracy: 1e-9)
        XCTAssertEqual(c.tick(5), [], "the rest of the flight (0.6 s), then the countdown waits")
        XCTAssertEqual(c.freezeRemaining, 10, accuracy: 1e-9)
        XCTAssertEqual(c.freezeLead, 0)
        XCTAssertTrue(c.freezeWaitsForFirstTap, "the tray holds \"10\"")
        XCTAssertEqual(c.tick(300), [])
        XCTAssertEqual(c.freezeRemaining, 10, accuracy: 1e-9, "never wasted before the first tap")
        XCTAssertEqual(c.remaining, 180)
        XCTAssertFalse(c.started)
        c.startOnFirstTap()
        XCTAssertFalse(c.freezeWaitsForFirstTap)
        XCTAssertEqual(c.tick(9.5), [])
        XCTAssertEqual(c.remaining, 180, "frozen through the countdown")
        XCTAssertEqual(c.tick(1), [.freezeEnded], "0.5 s of countdown left, then 0.5 s runs")
        XCTAssertEqual(c.remaining, 179.5, accuracy: 1e-9)
        XCTAssertFalse(c.isFrozen)
        XCTAssertEqual(c.freezeLead, 0)
    }

    func testHoldsStopTheLeadLikeEveryOtherClockTime() {
        var c = LevelClock(limit: 180)
        c.freeze(11.6, lead: 1.6)
        _ = c.tick(0.5)
        c.hold(.pause)
        XCTAssertEqual(c.tick(20), [])
        XCTAssertEqual(c.freezeLead, 1.1, accuracy: 1e-9, "paused: the flight waits")
        XCTAssertEqual(c.freezeRemaining, 11.1, accuracy: 1e-9)
        c.release(.pause)
        _ = c.tick(1.1)
        XCTAssertEqual(c.freezeLead, 0)
        XCTAssertEqual(c.freezeRemaining, 10, accuracy: 1e-9)
        XCTAssertTrue(c.freezeWaitsForFirstTap)
    }

    /// Once the timer runs, `freeze(s, lead:)` is `freeze(s)`: the same events and values tick by tick.
    func testALeadChangesNothingOnceTheTimerRuns() {
        var plain = LevelClock(limit: 60), led = LevelClock(limit: 60)
        plain.startOnFirstTap(); led.startOnFirstTap()
        _ = plain.tick(3); _ = led.tick(3)
        plain.freeze(11.6); led.freeze(11.6, lead: 1.6)
        for dt in [0.4, 1.0, 0.25, 5, 4.9, 0.1, 0.3, 2] {
            XCTAssertEqual(plain.tick(dt), led.tick(dt), "dt \(dt)")
            XCTAssertEqual(plain.remaining, led.remaining, accuracy: 1e-9)
            XCTAssertEqual(plain.freezeRemaining, led.freezeRemaining, accuracy: 1e-9)
            XCTAssertFalse(led.freezeWaitsForFirstTap)
        }
        XCTAssertEqual(led.remaining, 60 - 3 - 2.35, accuracy: 1e-9)
        XCTAssertEqual(led.freezeLead, 0)
        // freezeRunsBeforeStart: the whole freeze counts before the start anyway, lead or not
        var early = LevelClock(limit: 60, freezeRunsBeforeStart: true)
        early.freeze(11.6, lead: 1.6)
        XCTAssertEqual(early.tick(5), [])
        XCTAssertEqual(early.freezeRemaining, 6.6, accuracy: 1e-9)
        XCTAssertFalse(early.freezeWaitsForFirstTap)
        XCTAssertEqual(early.tick(7), [.freezeEnded])
        XCTAssertEqual(early.remaining, 60)
    }

    func testTheLeadIsClampedAndStacks() {
        var c = LevelClock(limit: 90)
        c.freeze(2, lead: 5)
        XCTAssertEqual(c.freezeLead, 2, "a lead never exceeds its freeze")
        XCTAssertEqual(c.tick(3), [.freezeEnded], "a freeze that is all lead ends before the first tap")
        XCTAssertEqual(c.remaining, 90)
        c.freeze(-1, lead: 1)
        c.freeze(0, lead: 1)
        XCTAssertEqual(c.freezeRemaining, 0)
        XCTAssertEqual(c.freezeLead, 0)
        c.freeze(3, lead: -1)
        XCTAssertEqual(c.freezeLead, 0, "a negative lead is none")
        XCTAssertEqual(c.tick(10), [])
        XCTAssertEqual(c.freezeRemaining, 3)
        c.freeze(11.6, lead: 1.6)                                        // a second hourglass on a waiting freeze
        XCTAssertEqual(c.freezeRemaining, 14.6, accuracy: 1e-9)
        XCTAssertEqual(c.freezeLead, 1.6, accuracy: 1e-9)
        XCTAssertEqual(c.tick(10), [])
        XCTAssertEqual(c.freezeRemaining, 13, accuracy: 1e-9, "its flight flew, both countdowns wait")
        c.freeze(1)                                                      // a plain freeze adds no lead
        XCTAssertEqual(c.freezeLead, 0)
        XCTAssertEqual(c.freezeRemaining, 14, accuracy: 1e-9)
        c.freeze(1, lead: 5)                                             // on a waiting freeze: the lead is its own 1 s, not 5
        XCTAssertEqual(c.freezeLead, 1, accuracy: 1e-9)
        XCTAssertEqual(c.freezeRemaining, 15, accuracy: 1e-9)
        XCTAssertEqual(c.tick(3), [])
        XCTAssertEqual(c.freezeRemaining, 14, accuracy: 1e-9)
    }

    // MARK: the session (GameG2Tests' numbers)

    /// GameG2Tests.testHourglassBeforeTheFirstTapFliesAtOnceAndCountsFromTheFirstTap: B, 600 frames, the first tap → 10 s of
    /// countdown left; the level timer frozen through it, running 6 frames after.
    func testRuledFreezeBeforeTheFirstTapTappedAfterTheFlight() {
        let s = ready()
        XCTAssertEqual(ruled(s), [.boosterUsed(.freeze), .freezeStarted(seconds: 11.6)])   // flight 1.6 (K-3) + 10
        XCTAssertFalse(s.clock.started, "a booster never starts the timer")
        XCTAssertEqual(s.clock.freezeLead, 1.6, accuracy: 1e-9)
        XCTAssertEqual(frames(s, 96), [], "the flight flies at once (B → B + 1.60)")
        XCTAssertTrue(s.clock.freezeWaitsForFirstTap)
        XCTAssertEqual(frames(s, 504), [])
        XCTAssertEqual(s.clock.freezeRemaining, 10, accuracy: 1e-9, "the flight was flown at B: the countdown waits")
        XCTAssertEqual(s.clock.remaining, 180)
        let ev = s.tap(a1, at: 10)
        XCTAssertEqual(ev.first, .timerStarted(stage: 0))
        XCTAssertEqual(s.phase, .playing(stage: 0))
        XCTAssertEqual(s.clock.freezeRemaining, 10, accuracy: 1e-9, "10 s of countdown left at the first tap")
        XCTAssertFalse(s.clock.freezeWaitsForFirstTap)
        XCTAssertEqual(frames(s, 600 - 6), [])
        XCTAssertEqual(s.clock.remaining, 180, "frozen through the 10 s countdown")
        XCTAssertEqual(frames(s, 12), [.freezeEnded])
        XCTAssertEqual(s.clock.remaining, 180 - 6 * frame, accuracy: 1e-6, "the timer runs when the countdown ends")
    }

    /// GameG2Tests.testHourglassBeforeTheFirstTapTappedDuringTheFlight: 30 frames into the flight → 1.1 s + 10 s; the
    /// countdown ends at B + 1.60 + 10.
    func testRuledFreezeBeforeTheFirstTapTappedDuringTheFlight() {
        let s = ready()
        _ = ruled(s)
        XCTAssertEqual(frames(s, 30), [])
        _ = s.tap(a1, at: 0.5)
        XCTAssertEqual(s.clock.freezeRemaining, 11.1, accuracy: 1e-9, "1.1 s of flight left + 10 s")
        XCTAssertEqual(s.clock.freezeLead, 1.1, accuracy: 1e-9)
        XCTAssertEqual(frames(s, 666 - 6), [])                        // B + 11.5
        XCTAssertEqual(s.clock.remaining, 180)
        XCTAssertEqual(frames(s, 12), [.freezeEnded])                  // B + 11.6 = B + 1.60 + 10
        XCTAssertEqual(s.clock.remaining, 180 - 6 * frame, accuracy: 1e-6)
    }

    /// Mid-level (the timer running) the ruled freeze IS the plain one: flight + 10 s of running time from B.
    func testRuledFreezeMidLevelIsThePlainFreeze() {
        let plain = ready(), led = ready()
        _ = plain.tap(a1, at: 0); _ = led.tap(a1, at: 0)
        _ = plain.tick(2); _ = led.tick(2)
        XCTAssertEqual(plain.useBooster(.freeze), ruled(led))
        for n in [60, 36, 300, 293, 6, 5, 60] {
            XCTAssertEqual(frames(plain, n), frames(led, n), "\(n) frames")
            XCTAssertEqual(plain.clock.remaining, led.clock.remaining, accuracy: 1e-9)
            XCTAssertEqual(plain.clock.freezeRemaining, led.clock.freezeRemaining, accuracy: 1e-9)
        }
        XCTAssertFalse(led.clock.isFrozen)
        // 760 frames since the use: 696 frozen (11.6 s), then 64 ran
        XCTAssertEqual(led.clock.remaining, 178 - 64 * frame, accuracy: 1e-6)
    }

    /// `useBooster(_:)` and `freezeFlightFromUse: false` keep the plain freeze: before the first tap nothing counts (the
    /// whole 11.6 s waits; the app's pre-FIX-A2 workaround consumes the flown flight itself).
    func testThePlainFreezeKeepsItsPreStartSemantics() {
        for use in [{ (s: LevelSession) in s.useBooster(.freeze) },
                    { (s: LevelSession) in s.useBooster(.freeze, hintPolicy: .unblocksMost, freezeFlightFromUse: false) }] {
            let s = ready()
            XCTAssertEqual(use(s), [.boosterUsed(.freeze), .freezeStarted(seconds: 11.6)])
            XCTAssertEqual(s.clock.freezeLead, 0)
            _ = frames(s, 600)
            XCTAssertEqual(s.clock.freezeRemaining, 11.6, accuracy: 1e-9, "never wasted before the start")
            XCTAssertTrue(s.clock.freezeWaitsForFirstTap, "no lead: the whole plain freeze waits for the first tap")
            _ = s.tap(a1, at: 10)
            XCTAssertEqual(s.clock.freezeRemaining, 11.6, accuracy: 1e-9)
        }
    }

    /// The flight honours the session's holds (pause, popups): paused 5 s into nothing.
    func testRuledFreezeFlightPausesWithTheSession() {
        let s = ready()
        _ = ruled(s)
        _ = frames(s, 30)
        s.hold(.pause)
        XCTAssertEqual(frames(s, 300), [])
        XCTAssertEqual(s.clock.freezeLead, 1.1, accuracy: 1e-9)
        s.release(.pause)
        _ = frames(s, 70)
        XCTAssertTrue(s.clock.freezeWaitsForFirstTap)
        XCTAssertEqual(s.clock.freezeRemaining, 10, accuracy: 1e-9)
    }

    /// The same guards as `useBooster(_:)`: nothing outside `.ready` / `.playing`, nothing for an unknown booster, the
    /// freeze length from the rules (freezeFlight 2 → lead 2, total 12).
    func testRuledEntryGuardsAndRules() {
        let lv = crossing()
        let intro = LevelSession(plan: SessionPlan(id: "S", levels: [32]), stages: [lv], setup: AttemptSetup(levels: [32]))
        _ = intro.start()
        XCTAssertEqual(ruled(intro), [], "the intro: no booster")
        XCTAssertEqual(intro.clock.freezeRemaining, 0)
        let s = ready()
        XCTAssertEqual(ruled(s, BoosterID("dome")), [])
        XCTAssertEqual(s.clock.freezeRemaining, 0)
        var rules = RulesTuning()
        rules.boosters.freezeFlight = 2
        let r = ready(rules)
        XCTAssertEqual(ruled(r), [.boosterUsed(.freeze), .freezeStarted(seconds: 12)])
        XCTAssertEqual(r.clock.freezeLead, 2, accuracy: 1e-9)
        _ = r.tick(5)
        XCTAssertEqual(r.clock.freezeRemaining, 10, accuracy: 1e-9)
        _ = r.quit()
        XCTAssertEqual(ruled(r), [], "lost: no booster")
    }
}
