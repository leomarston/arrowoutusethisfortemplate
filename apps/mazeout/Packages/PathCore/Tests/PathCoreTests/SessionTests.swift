import XCTest
import Foundation
@testable import PathCore

/// §4.5 path by path (the diagram in LevelSession.swift).
final class SessionTests: XCTestCase {
    typealias F = C2Fixtures
    let a0 = ArrowID(0), a1 = ArrowID(1), a2 = ArrowID(2)

    /// A (0,1)(1,1) → blocked by B (vertical at column 4); B is free. Timer 180 s, 3 hearts.
    func crossing(n: Int = 32, timer: Int = 180, tag: LevelTag = .normal) -> LevelSpec {
        F.level(6, 3, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(4, 0), (4, 1), (4, 2)], .down)], timer: timer,
                n: n, tag: tag)
    }

    func session(_ levels: [LevelSpec], id: String = "S", reward: Int? = nil, hearts: HeartsCarry = .carry,
                 attempt: Int = 1, rules: RulesTuning = .default) -> LevelSession {
        LevelSession(plan: SessionPlan(id: id, levels: levels.map(\.level), reward: reward, hearts: hearts),
                     stages: levels, setup: AttemptSetup(levels: levels.map(\.level), attemptIndex: attempt), rules: rules)
    }

    /// start → intro → ready (timer armed, frozen) → the first tap starts it.
    func begin(_ s: LevelSession) {
        XCTAssertEqual(s.start(), [.stageLoaded(stage: 0, of: s.stages.count, level: s.stages[0].level)])
        XCTAssertEqual(s.phase, .intro(stage: 0))
        XCTAssertEqual(s.ack(.introFinished), [.timerArmed(stage: 0, seconds: s.stages[0].timerSeconds)])
        XCTAssertEqual(s.phase, .ready(stage: 0))
    }

    func exitPlan(_ ev: [SessionEvent]) -> ExitPlan? {
        for e in ev { if case .exited(let p) = e { return p } }
        return nil
    }

    // MARK: the timer starts at the first tap (VERIFIED levels.md L33/L35, tutorials §8)

    func testTimerStartsAtTheFirstTapNeverBefore() throws {
        let s = session([crossing()])
        XCTAssertEqual(s.tap(a1, at: 0), [.tapIgnored(a1, .notPlaying)])           // before start()
        XCTAssertEqual(s.start().count, 1)
        XCTAssertEqual(s.start(), [])                                                // idempotent
        XCTAssertEqual(s.tick(5), [])
        XCTAssertEqual(s.tap(a1, at: 1), [.tapIgnored(a1, .notPlaying)])           // taps during the build-in
        XCTAssertEqual(s.ack(.introFinished), [.timerArmed(stage: 0, seconds: 180)])
        XCTAssertEqual(s.ack(.introFinished), [])
        _ = s.tick(30)                                                               // .ready: frozen at the limit
        XCTAssertEqual(s.clock.remaining, 180)
        XCTAssertFalse(s.clock.started)
        XCTAssertEqual(s.tap(nil, at: 2), [.tapIgnored(nil, .noArrow)])            // an empty point starts nothing
        XCTAssertFalse(s.clock.started)
        XCTAssertEqual(s.useBooster(.hint).first, .boosterUsed(.hint))              // boosters never start it
        XCTAssertFalse(s.clock.started)
        let ev = s.tap(a1, at: 3)
        XCTAssertEqual(ev.first, .timerStarted(stage: 0))
        XCTAssertNotNil(exitPlan(ev))
        XCTAssertEqual(s.phase, .playing(stage: 0))
        _ = s.tick(2.5)
        XCTAssertEqual(s.clock.remaining, 177.5, accuracy: 1e-9)
        XCTAssertEqual(s.clock.displayedSeconds, 178)
    }

    /// The first BUMP starts the timer too (VERIFIED fail.md §3); the heart goes at CONTACT, not at the tap.
    func testBumpStartsTimerAndTheHeartGoesAtContact() {
        let s = session([crossing()])
        begin(s)
        let ev = s.tap(a0, at: 0)
        XCTAssertEqual(ev.first, .timerStarted(stage: 0))
        guard case .bumped(let plan)? = ev.last else { return XCTFail("no bump") }
        XCTAssertEqual(plan.arrow, a0)
        XCTAssertEqual(s.hearts, 3)
        _ = s.tick(0.1)                                                              // the timer runs through a bump
        XCTAssertEqual(s.ack(.bumpContact(a0)), [.heartLost(remaining: 2), .arrowMarked(a0)])
        XCTAssertEqual(s.hearts, 2)
        XCTAssertEqual(s.ack(.bumpContact(a0)), [])                                  // one contact per bump
        XCTAssertEqual(s.tap(a0, at: 0.2), [.tapIgnored(a0, .bumping)])
        XCTAssertEqual(s.ack(.bumpFinished(a0)), [])
        XCTAssertEqual(s.bumps, 1)
        XCTAssertEqual(s.clock.remaining, 179.9, accuracy: 1e-9)
    }

    /// Re-tapping a red arrow that is still blocked costs no heart (VERIFIED 1 clean observation, fail.md §3).
    func testRepeatBumpOnARedArrowCostsNoHeart() {
        let s = session([crossing()])
        begin(s)
        _ = s.tap(a0, at: 0); _ = s.ack(.bumpContact(a0)); _ = s.ack(.bumpFinished(a0))
        XCTAssertEqual(s.hearts, 2)
        _ = s.tap(a0, at: 1)
        XCTAssertEqual(s.ack(.bumpContact(a0)), [])
        XCTAssertEqual(s.hearts, 2)
        var rules = RulesTuning(); rules.bump.repeatOnMarkedCostsHeart = true
        let t = session([crossing()], rules: rules)
        begin(t)
        _ = t.tap(a0, at: 0); _ = t.ack(.bumpContact(a0)); _ = t.ack(.bumpFinished(a0))
        _ = t.tap(a0, at: 1)
        XCTAssertEqual(t.ack(.bumpContact(a0)), [.heartLost(remaining: 1)])
    }

    // MARK: holds keep remaining constant

    func testHoldsFreezeTheClockAndLockInput() {
        let s = session([crossing()])
        begin(s)
        _ = s.tap(a1, at: 0)
        for h in [HoldReason.pause, .popup, .tutorial, .unlockOverlay, .background] {
            s.hold(h)
            _ = s.tick(3)
            XCTAssertEqual(s.clock.remaining, 180, "\(h) must hold the clock")
            if h == .tutorial {                                                      // "Tap to move!" keeps input
                XCTAssertEqual(s.tap(ArrowID(99), at: 1), [.tapIgnored(ArrowID(99), .noArrow)])
            } else {
                XCTAssertEqual(s.tap(a0, at: 1), [.tapIgnored(a0, .inputLocked)])
            }
            s.release(h)
        }
        _ = s.tick(1)
        XCTAssertEqual(s.clock.remaining, 179)
    }

    // MARK: win at the tap; a win beats a fail

    func testWinAtTheLastTapAndWinBeatsFail() throws {
        let s = session([crossing(timer: 60)])
        begin(s)
        _ = s.tap(a1, at: 0)
        _ = s.tick(59.5)
        let ev = s.tap(a0, at: 60)
        let win = WinResult(levels: [32], tag: .normal, timeLeft: 1, heartsLeft: 3, firstTry: true, reward: 20, bumps: 0)
        XCTAssertEqual(ev.last, .won(win))
        XCTAssertEqual(s.phase, .won(win))
        XCTAssertTrue(s.isFinished)
        // the exits are still on screen: time runs out meanwhile → nothing (the timer stopped on the last arrow)
        XCTAssertEqual(s.tick(10), [])
        XCTAssertEqual(s.clock.remaining, 0.5, accuracy: 1e-9)
        XCTAssertEqual(s.ack(.lastExitLeftBoard), [])
        XCTAssertEqual(s.tap(a0, at: 61), [.tapIgnored(a0, .inputLocked)])
        XCTAssertEqual(s.quit(), [])
        XCTAssertEqual(s.phase, .won(win))
    }

    /// A pending bump's contact after the win only marks the arrow: no heart, no offer.
    func testContactAfterTheWinOnlyMarks() {
        // A blocked by B; C free elsewhere. Bump A, then tap B and A... A is bumping (ignored) → tap order B, then contact
        let lv = F.level(6, 4, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(4, 0), (4, 1), (4, 2)], .down)])
        let s = session([lv])
        begin(s)
        _ = s.tap(a0, at: 0)                         // bump (A still on the board)
        _ = s.ack(.bumpContact(a0)); _ = s.ack(.bumpFinished(a0))
        _ = s.tap(a1, at: 1)
        _ = s.tap(a0, at: 2)                         // won
        guard case .won = s.phase else { return XCTFail("not won") }
        XCTAssertEqual(s.ack(.bumpContact(a0)), [])   // stale contact: nothing
        XCTAssertEqual(s.hearts, 2)
        let w = WinResult(levels: [1], tag: .normal, timeLeft: 180, heartsLeft: 2, firstTry: true, reward: 20, bumps: 1)
        XCTAssertEqual(s.phase, .won(w))
    }

    func testRewardsByTagAndAttempt() {
        for (tag, coins) in [(LevelTag.normal, 20), (.hard, 60), (.superHard, 100)] {
            let s = session([crossing(tag: tag)], attempt: 2)
            begin(s)
            _ = s.tap(a1, at: 0)
            guard case .won(let r)? = s.tap(a0, at: 1).last else { return XCTFail("not won") }
            XCTAssertEqual(r.reward, coins)
            XCTAssertEqual(r.tag, tag)
            XCTAssertFalse(r.firstTry)
        }
    }

    // MARK: "Levels 1-4": one session, four boards, one win (VERIFIED tutorials §2)

    func testMultiStageSession() throws {
        let stages = (1...4).map { crossing(n: $0) }
        let s = session(stages, id: "L1-4", reward: 80)
        begin(s)
        for k in 0..<4 {
            XCTAssertEqual(s.stage, k)
            XCTAssertFalse(s.clock.started)                                           // each stage re-arms, frozen
            XCTAssertEqual(s.clock.remaining, 180)
            _ = s.tap(a1, at: Double(k * 10))
            _ = s.tick(4)
            let ev = s.tap(a0, at: Double(k * 10 + 1))
            if k < 3 {
                XCTAssertEqual(ev.last, .stageCleared(stage: k))
                XCTAssertEqual(s.phase, .stageClear(stage: k))
                XCTAssertEqual(s.tick(10), [])                                        // held through the transition
                XCTAssertEqual(s.tap(a0, at: 0), [.tapIgnored(a0, .inputLocked)])
                XCTAssertEqual(s.ack(.lastExitLeftBoard), [])
                XCTAssertEqual(s.ack(.stageTransitionDone),
                               [.stageAdvanced(to: k + 1), .stageLoaded(stage: k + 1, of: 4, level: k + 2),
                                .timerArmed(stage: k + 1, seconds: 180)])
                XCTAssertEqual(s.phase, .ready(stage: k + 1))
            } else {
                let win = WinResult(levels: [1, 2, 3, 4], tag: .normal, timeLeft: 176, heartsLeft: 3, firstTry: true,
                                    reward: 80, bumps: 0)
                XCTAssertEqual(ev.last, .won(win))
            }
        }
        XCTAssertEqual(s.ack(.stageTransitionDone), [])
    }

    func testHeartsCarryOrResetBetweenStages() {
        for mode in [HeartsCarry.carry, .reset] {
            let s = session([crossing(n: 1), crossing(n: 2)], hearts: mode)
            begin(s)
            _ = s.tap(a0, at: 0); _ = s.ack(.bumpContact(a0)); _ = s.ack(.bumpFinished(a0))
            _ = s.tap(a1, at: 1); _ = s.tap(a0, at: 2)
            _ = s.ack(.stageTransitionDone)
            XCTAssertEqual(s.hearts, mode == .carry ? 2 : 3)
        }
    }

    func testFirstStageFromSetup() {
        let stages = (1...4).map { crossing(n: $0) }
        let s = LevelSession(plan: SessionPlan(id: "L1-4", levels: [1, 2, 3, 4]), stages: stages,
                             setup: AttemptSetup(levels: [1, 2, 3, 4], firstStage: 2))
        XCTAssertEqual(s.start(), [.stageLoaded(stage: 2, of: 4, level: 3)])
        XCTAssertEqual(s.ack(.introFinished), [.timerArmed(stage: 2, seconds: 180)])
    }

    // MARK: the fail chains (VERIFIED texts fail.md §1)

    func testOutOfTimeChainDeclined() {
        let s = session([crossing(timer: 10)])
        begin(s)
        _ = s.tap(a1, at: 0)
        var ev = s.tick(9.9)
        XCTAssertEqual(ev, [])
        ev = s.tick(0.2)
        let a = ContinueOffer(kind: .outOfTime, step: 0, price: 900, grant: .addTime(30), warning: .none, isLast: false)
        XCTAssertEqual(ev, [.offer(a)])
        XCTAssertEqual(s.phase, .offer(a))
        XCTAssertEqual(s.clock.remaining, 0)
        XCTAssertEqual(s.tick(5), [])                                                   // frozen behind the popups
        XCTAssertEqual(s.tap(a0, at: 20), [.tapIgnored(a0, .inputLocked)])
        let c = ContinueOffer(kind: .outOfTime, step: 1, price: 900, grant: .addTime(30), warning: .life, isLast: true)
        XCTAssertEqual(s.declineContinue(), [.offer(c)])                               // no streak: B is skipped
        XCTAssertEqual(s.declineContinue(), [.lost(.timeUp)])
        XCTAssertEqual(s.phase, .lost(.timeUp))
        XCTAssertEqual(s.declineContinue(), [])
    }

    func testOutOfTimeChainWithStreakAndAccept() {
        let s = session([crossing(timer: 10)])
        s.streakActive = true
        begin(s)
        _ = s.tap(a1, at: 0)
        guard case .offer(let a)? = s.tick(11).last else { return XCTFail("no offer") }
        XCTAssertEqual(a.step, 0)
        guard case .offer(let b)? = s.declineContinue().last else { return XCTFail("no B") }
        XCTAssertEqual(b.warning, .token)
        XCTAssertFalse(b.isLast)
        XCTAssertEqual(s.acceptContinue(), [.continued(b), .timeAdded(seconds: 30, cause: .continueOffer)])
        XCTAssertEqual(s.phase, .playing(stage: 0))
        XCTAssertEqual(s.clock.remaining, 30)
        _ = s.tick(1)
        XCTAssertEqual(s.clock.remaining, 29)
        XCTAssertEqual(s.acceptContinue(), [])
        // time runs out again → the chain restarts at step 0
        guard case .offer(let again)? = s.tick(30).last else { return XCTFail("no second offer") }
        XCTAssertEqual(again.step, 0)
    }

    func testOutOfHeartsChain() {
        var rules = RulesTuning(); rules.bump.repeatOnMarkedCostsHeart = true      // three bumps of the same arrow
        let s = session([crossing()], rules: rules)
        begin(s)
        for k in 0..<3 {
            _ = s.tap(a0, at: Double(k))
            let ev = s.ack(.bumpContact(a0))
            _ = s.ack(.bumpFinished(a0))
            if k < 2 { XCTAssertEqual(ev.first, .heartLost(remaining: 2 - k)) }
            else {
                let o = ContinueOffer(kind: .outOfHearts, step: 0, price: 900, grant: .refillHearts(3), warning: .none,
                                      isLast: false)
                XCTAssertEqual(ev, [.heartLost(remaining: 0), .offer(o)])      // the red mark came with the first bump
                XCTAssertEqual(s.tick(20), [])
                XCTAssertEqual(s.acceptContinue(), [.continued(o)])
                XCTAssertEqual(s.hearts, 3)
                XCTAssertEqual(s.phase, .playing(stage: 0))
            }
        }
        // three more (repeat bumps on the red arrow cost nothing) → use B instead: mark-free arrow needed; quit instead
        XCTAssertEqual(s.quit(), [.lost(.quit)])
        XCTAssertEqual(s.phase, .lost(.quit))
        XCTAssertEqual(s.quit(), [])
    }

    func testOutOfHeartsDeclinedLoses() {
        var rules = RulesTuning(); rules.bump.repeatOnMarkedCostsHeart = true
        let s = session([crossing()], rules: rules)
        begin(s)
        var last: [SessionEvent] = []
        for k in 0..<3 { _ = s.tap(a0, at: Double(k)); last = s.ack(.bumpContact(a0)); _ = s.ack(.bumpFinished(a0)) }
        guard case .offer? = last.last else { return XCTFail("no offer") }
        guard case .offer(let c)? = s.declineContinue().last else { return XCTFail("no C") }
        XCTAssertEqual(c.warning, .life)
        XCTAssertEqual(s.declineContinue(), [.lost(.hearts)])
    }

    // MARK: boosters (the stock is the caller's)

    func testFreezeBooster() {
        let s = session([crossing()])
        begin(s)
        XCTAssertEqual(s.useBooster(.freeze), [.boosterUsed(.freeze), .freezeStarted(seconds: 11.6)])   // 1.6 s flight (K-3) + 10
        _ = s.tick(20)                                   // not started: the freeze waits (DECISION, never wasted)
        XCTAssertEqual(s.clock.remaining, 180)
        _ = s.tap(a1, at: 0)
        XCTAssertEqual(s.tick(11), [])
        XCTAssertEqual(s.clock.remaining, 180)
        XCTAssertEqual(s.tick(1), [.freezeEnded])        // 0.6 s of freeze left, then 0.4 s runs
        XCTAssertEqual(s.clock.remaining, 179.6, accuracy: 1e-9)
        XCTAssertEqual(s.useBooster(BoosterID("dome")), [])        // unknown → nothing
    }

    func testHintBooster() {
        let s = session([crossing()])
        begin(s)
        XCTAssertEqual(s.useBooster(.hint), [.boosterUsed(.hint), .hintShown([a1])])
        XCTAssertEqual(s.hint(), [a1])
        _ = s.tap(a1, at: 0)
        XCTAssertEqual(s.hint(), [a0])
    }

    // MARK: combo in the plans

    func testComboIndicesInThePlans() {
        let lv = F.level(8, 1, (0..<4).map { F.arrow($0, [(2 * $0, 0), (2 * $0 + 1, 0)], .right) }.reversed())
        let s = session([lv])
        begin(s)
        let t: [Double] = [0, 1.0, 2.2, 5]
        var combos: [Int] = []
        for (k, id) in [3, 2, 1, 0].enumerated() { combos.append(exitPlan(s.tap(ArrowID(id), at: t[k]))?.combo ?? -1) }
        XCTAssertEqual(combos, [1, 2, 3, 1])            // 1.0 and 1.2 s apart continue; 2.8 s breaks
    }

    // MARK: snapshot

    func testSnapshot() {
        let s = session([crossing()])
        begin(s)
        _ = s.tap(a1, at: 0)
        _ = s.tick(2)
        let snap = s.snapshot()
        XCTAssertEqual(snap, SessionSnapshot(levels: [32], stage: 0, phase: "playing", remaining: 178, timerStarted: true,
                                             hearts: 3, live: [a0], free: [[a0]], counters: [:], combo: 1))
    }
}
