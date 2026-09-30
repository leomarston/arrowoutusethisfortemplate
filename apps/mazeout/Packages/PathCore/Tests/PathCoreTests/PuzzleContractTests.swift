import XCTest
import Foundation
import PathCore   // not @testable: the contract and the arrow adapter are public API

/// Template phase 2 (docs/architecture/PUZZLE-MODULE.md): the generic puzzle contract's surface, and ArrowEscape's adapter
/// proven to be a pure re-labelling of `LevelSession` — the same core calls, the same events in the same order.
final class PuzzleContractTests: XCTestCase {
    typealias F = C2Fixtures

    // MARK: surface pins (typed references + a real use, like APISurfaceTests)

    func testContractSurface() {
        let _: (Int) -> PuzzleTarget = PuzzleTarget.init(_:)
        let _: KeyPath<PuzzleTarget, Int> = \.raw
        XCTAssertLessThan(PuzzleTarget(1), PuzzleTarget(2))
        XCTAssertEqual(InputKind.allCases, [.tap, .drag, .swap, .select2, .paint, .multiTouch])
        let inputs: [PuzzleInput] = [.tap(nil), .tap(PuzzleTarget(3)), .drag(from: PuzzleTarget(1), to: nil),
                                     .swap(PuzzleTarget(1), PuzzleTarget(2)), .select(PuzzleTarget(4)),
                                     .custom(id: "paint", targets: [PuzzleTarget(5)])]
        XCTAssertEqual(inputs.map(\.kind), [.tap, .tap, .drag, .swap, .select2, .multiTouch])
        XCTAssertEqual(inputs.map(\.target), [nil, PuzzleTarget(3), PuzzleTarget(1), PuzzleTarget(1), PuzzleTarget(4), PuzzleTarget(5)])
        let _: (PuzzleTarget, Bool) -> PuzzleMove = PuzzleMove.init(target:failed:)

        let offer = ContinueOffer(kind: .outOfMoves, step: 0, price: 900, grant: .addMoves(5))
        let win = WinResult(levels: [1], tag: .normal, timeLeft: 0, heartsLeft: 0, firstTry: true, reward: 20, bumps: 0)
        let metas: [MetaEvent] = [
            .stageLoaded(stage: 0, of: 1, level: 1), .timerArmed(stage: 0, seconds: 0), .timerStarted(stage: 0),
            .timerAlert(seconds: 10), .timeAdded(seconds: 30, cause: .booster), .freezeStarted(seconds: 10), .freezeEnded,
            .heartsChanged(left: 2), .movesChanged(left: 9), .mistake, .goalProgress([GoalState(id: "red", current: 3, target: 20)]),
            .boosterUsed(.hint), .stageCleared(stage: 0), .stageAdvanced(to: 1), .offer(offer), .continued(offer), .won(win),
            .lost(.stuck),
        ]
        XCTAssertEqual(metas.count, 18)
        XCTAssertEqual(SessionOutput.meta(.mistake).metaEvent, .mistake)
        XCTAssertNil(SessionOutput.meta(.mistake).puzzleEvent)
        XCTAssertNil(SessionOutput.meta(.mistake).move)

        let rules: [FailRule] = [.timer, .moves, .hearts(3), .none, .custom("stuck")]
        XCTAssertEqual(Set(rules).count, 5)
        XCTAssertEqual(HUDWidget.allCases, [.timer, .moves, .hearts, .goals, .progress, .score])
        let _: [BoosterKind] = [.freezeTimer, .addTime(30), .addMoves(5), .puzzleAction("shuffle")]
        let _: (BoosterID, BoosterKind, String?) -> BoosterSpec = BoosterSpec.init(id:effect:icon:)
        let _: (PuzzleCapabilities) -> (BoosterID) -> BoosterSpec? = PuzzleCapabilities.booster(_:)
        let _: (Int, LevelTag, Int?, Int?, String, any Sendable) -> PuzzleStage = PuzzleStage.init(level:tag:timerSeconds:hearts:summary:content:)
        XCTAssertEqual(PuzzleContract.version, 1)

        let step = TutorialStep(id: "t", level: 1, hand: TutorialStep.Hand(target: PuzzleTarget(2), at: [1, 2]),
                                allowedTargets: [PuzzleTarget(2)])
        XCTAssertEqual(step.trigger, .stageReady)
        XCTAssertEqual(step.dismiss, .anyTap)
        XCTAssertFalse(step.holdTimer)
    }

    func testArrowEscapeModuleCapabilities() {
        XCTAssertEqual(ArrowEscapeModule.id, "arrow-escape")
        XCTAssertEqual(ArrowEscapeModule.contractVersion, PuzzleContract.version)
        let c = ArrowEscapeModule.capabilities
        XCTAssertEqual(c.failRules, [.timer, .hearts(3)])
        XCTAssertEqual(c.inputs, [.tap])
        XCTAssertEqual(c.boosters.map(\.id), [.freeze, .hint], "the HUD corners: hourglass left, bulb right (v552)")
        XCTAssertEqual(c.boosters.map(\.effect), [.freezeTimer, .puzzleAction("hint")])
        XCTAssertEqual(c.hud, [.timer, .hearts])
        XCTAssertTrue(c.zoomable)
        XCTAssertTrue(c.multiStageSessions)
        // the capabilities agree with the rules table's actions (rules.json boosters.actions)
        for b in c.boosters {
            switch b.effect {
            case .freezeTimer: XCTAssertEqual(RulesTuning.default.boosters.action(b.id), .freezeTimer)
            case .puzzleAction: XCTAssertEqual(RulesTuning.default.boosters.action(b.id), .hint)
            default: XCTFail("\(b)")
            }
        }
    }

    // MARK: the adapter is a pure re-labelling

    /// A (0,1)(1,1) → blocked by B (vertical at column 4); B is free. Timer 180 s, 3 hearts.
    func crossing(n: Int = 32) -> LevelSpec {
        F.level(6, 3, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(4, 0), (4, 1), (4, 2)], .down)], timer: 180, n: n)
    }

    func pair(_ levels: [LevelSpec], hearts: Int? = nil) -> (LevelSession, ArrowPuzzleSession) {
        var ls = levels
        if let h = hearts { for i in ls.indices { ls[i].hearts = h } }
        let plan = SessionPlan(id: "S", levels: ls.map(\.level))
        let setup = AttemptSetup(levels: plan.levels)
        let plain = LevelSession(plan: plan, stages: ls, setup: setup, rules: .default)
        let wrapped = ArrowEscapeModule.makeSession(plan: plan, stages: ls, setup: setup, rules: .default, streakActive: false)
        return (plain, wrapped)
    }

    /// Every output is its event's generic form, in order (meta events re-labelled, arrow events carried unchanged).
    func assertSame(_ events: [SessionEvent], _ outputs: [SessionOutput], _ what: String, file: StaticString = #filePath,
                    line: UInt = #line) {
        XCTAssertEqual(outputs.count, events.count, what, file: file, line: line)
        for (e, o) in zip(events, outputs) {
            switch o {
            case .meta(let m):
                if case .meta(let expected) = e.output { XCTAssertEqual(m, expected, what, file: file, line: line) } else {
                    XCTFail("\(what): \(e) came out as meta \(m)", file: file, line: line)
                }
            case .puzzle(let p):
                XCTAssertEqual(p as? SessionEvent, e, what, file: file, line: line)
            }
        }
    }

    func testTheWrappedSessionEmitsTheSameEventsInTheSameOrder() {
        let (a, b) = pair([crossing()], hearts: 1)
        assertSame(a.start(), b.start(), "start")
        assertSame(a.ack(.introFinished), b.ack(.introFinished), "intro")
        XCTAssertEqual(a.phase, b.phase)
        assertSame(a.tap(nil, at: 0.5), b.input(.tap(nil), at: 0.5), "empty tap")
        assertSame(a.useBooster(.hint, hintPolicy: .unblocksMost, freezeFlightFromUse: true), b.useBooster(.hint), "bulb")
        // arrow 0 bumps into 1: the timer starts, the bump plan goes to the board as an arrow event (a failed move)
        let bumpA = a.tap(ArrowID(0), at: 1), bumpB = b.input(.tap(PuzzleTarget(0)), at: 1)
        assertSame(bumpA, bumpB, "bump")
        XCTAssertEqual(bumpB.compactMap(\.move), [PuzzleMove(target: PuzzleTarget(0), failed: true)])
        // the contact frame: the last heart → heartsChanged(0) + the hearts-out offer
        let contactA = a.ack(.bumpContact(ArrowID(0))), contactB = b.ack(.contact(SessionAck.bumpContact(ArrowID(0))))
        assertSame(contactA, contactB, "contact")
        XCTAssertEqual(contactB.compactMap(\.metaEvent).first, .heartsChanged(left: 0))
        guard case .offer(let o) = b.phase else { return XCTFail("no offer: \(b.phase)") }
        XCTAssertEqual(o.kind, .outOfHearts)
        assertSame(a.acceptContinue(), b.acceptContinue(), "continue")
        XCTAssertEqual(b.hearts, a.hearts)
        assertSame(a.ack(.bumpFinished(ArrowID(0))), b.ack(.beat(SessionAck.bumpFinished(ArrowID(0)))), "bump finished")
        assertSame(a.tick(2), b.tick(2), "tick")
        XCTAssertEqual(b.clock, a.clock)
        // B exits (the hint's target), then A: the win at the tap
        XCTAssertEqual(b.hint(), a.hint()?.first?.target)
        let exitB = b.input(.tap(PuzzleTarget(1)), at: 3)
        assertSame(a.tap(ArrowID(1), at: 3), exitB, "exit")
        XCTAssertEqual(exitB.compactMap(\.move), [PuzzleMove(target: PuzzleTarget(1), failed: false)])
        XCTAssertEqual(exitB.compactMap(\.puzzleEvent).flatMap { $0.removedTargets }, [PuzzleTarget(1)])
        let winA = a.tap(ArrowID(0), at: 4), winB = b.input(.tap(PuzzleTarget(0)), at: 4)
        assertSame(winA, winB, "win")
        XCTAssertTrue(b.isFinished)
        assertSame(a.ack(.lastExitLeftBoard), b.ack(.boardCleared), "W")
        XCTAssertEqual(b.phase, a.phase)
        XCTAssertEqual(b.input(.swap(PuzzleTarget(0), PuzzleTarget(1)), at: 5).count, 0, "tap-only module")
    }

    func testHintAndBoosterReadinessFollowTheCore() {
        let (a, b) = pair([crossing()])
        _ = a.start(); _ = b.start()
        XCTAssertFalse(b.canUseBooster("nope"), "an unknown booster does nothing")
        XCTAssertTrue(b.canUseBooster(.freeze))
        XCTAssertEqual(b.canUseBooster(.hint), !(a.hint(policy: .unblocksMost) ?? []).isEmpty)
        _ = a.ack(.introFinished); _ = b.ack(.introFinished)
        let outs = b.useBooster(.hint)
        let hinted = outs.compactMap(\.puzzleEvent).compactMap { $0.hintTargets }.first
        XCTAssertEqual(hinted, a.hint(policy: .unblocksMost)?.map(\.target))
        XCTAssertEqual(b.blockedTargets(), [PuzzleTarget(0)], "A is blocked by B")
        XCTAssertEqual(ArrowID(target: PuzzleTarget(7)), ArrowID(7))
        XCTAssertEqual(ArrowID(7).target, PuzzleTarget(7))
    }

    func testStageAndWarmUp() {
        let l = crossing(n: 44)
        let st = ArrowEscapeModule.stage(l)
        XCTAssertEqual(st.level, 44)
        XCTAssertEqual(st.timerSeconds, 180)
        XCTAssertEqual(st.hearts, l.hearts)
        XCTAssertEqual(st.summary, "2 arrows")
        XCTAssertEqual(st.content as? LevelSpec, l)
        XCTAssertNotNil(ArrowEscapeModule.warmUpWin(rules: .default), "the headless 2-arrow board is won")
    }

    func testTutorialScriptStep() {
        let s = TutorialScript(id: "only1", level: 900, caption: "Tap to move!", hand: TutorialHand(arrow: ArrowID(2), at: [1, 2]),
                               dismiss: .targetTap, allowedArrows: [ArrowID(2), ArrowID(3)])
        let step = s.step
        XCTAssertEqual(step.id, "only1")
        XCTAssertEqual(step.level, 900)
        XCTAssertEqual(step.hand, TutorialStep.Hand(target: PuzzleTarget(2), at: [1, 2]))
        XCTAssertEqual(step.dismiss, .targetTap)
        XCTAssertEqual(step.allowedTargets, [PuzzleTarget(2), PuzzleTarget(3)])
        XCTAssertNil(TutorialScript(id: "x", level: 1).step.hand)
    }
}
