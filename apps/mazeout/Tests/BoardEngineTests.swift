import XCTest
import UIKit
import PathCore
@testable import ArrowOut

/// B1 (SPEC-architecture §5.1, §5.5, §5.10, §5.11, §9.4): the engine against the ◆ BoardControlling contract, in a
/// private context (its own PlayerStore directory, MotionClock and perf probes; the running app is not touched).
@MainActor final class BoardEngineTests: XCTestCase, BoardDelegate {
    var beats: [BoardBeat] = []
    var releases: [ArrowID?] = []
    var window: UIWindow?

    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval) {}
    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval) { releases.append(arrow) }
    func boardBeat(_ beat: BoardBeat) { beats.append(beat) }
    func boardZoomChanged(scale: CGFloat) {}

    private func makeEngine(_ args: [String] = []) -> BoardEngine {
        let a = LaunchArgs(arguments: args)
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("board-tests-\(UUID().uuidString)")
        let clock = MotionClock(args: a)
        let store = PlayerStore(args: a, now: Date(), bundle: .main, directory: dir)
        let tuning = Tuning.load(bundle: .main)
        let ctx = AppContext(args: a, tuning: tuning, clock: clock, store: store, hud: HUDModel(), anchors: AnchorRegistry(),
                             perf: PerfMonitor(), latency: LatencyProbe(), bundle: .main)
        let e = BoardEngine(ctx)
        e.delegate = self
        return e
    }

    private func host(_ e: BoardEngine) {
        let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
        let w = scene.map { UIWindow(windowScene: $0) } ?? UIWindow(frame: CGRect(x: 0, y: 0, width: 393, height: 852))
        w.frame = CGRect(x: 0, y: 0, width: 393, height: 852)
        w.addSubview(e.view)
        e.view.frame = w.bounds
        w.isHidden = false
        e.view.layoutIfNeeded()
        window = w
    }

    override func tearDown() {
        window?.isHidden = true
        window = nil
        super.tearDown()
    }

    private func wait(_ s: Double) { RunLoop.main.run(until: Date().addingTimeInterval(s)) }

    func testCommandsBeforeTheFirstLayoutAreQueued() {
        let e = makeEngine()
        let level = LabBoards.hitBoard()
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        XCTAssertNil(e.stage, "no layout yet: queued, never awaited")
        host(e)
        XCTAssertNotNil(e.stage, "replayed after the first layout")
        XCTAssertEqual(e.nodes.count, level.arrows.count)
        wait(0.1)
        XCTAssertTrue(beats.contains(.introFinished))
        XCTAssertTrue(e.isSettled)
    }

    func testRestArrowIsExactlyTwoLayersAndFramesHugTheirPaths() {
        let e = makeEngine()
        host(e)
        let level = LabBoards.level("L032", bundle: .main)!
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        XCTAssertEqual(e.roots.rest.sublayers?.count, 2 * level.arrows.count)
        for n in e.nodes.values {
            XCTAssertLessThan(n.body.frame.width * n.body.frame.height, e.contentBounds.width * e.contentBounds.height / 4,
                              "P4: the body frame hugs its path")
            XCTAssertNil(n.body.animationKeys())
        }
        XCTAssertEqual(e.dots.dotCount, 399, "a dot under every arrow cell from the start (motion §2.3)")
    }

    func testReleaseRipplesAndReportsTheHitArrowInTheSameTurn() {
        let e = makeEngine()
        host(e)
        let level = LabBoards.hitBoard()
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        e.inputEnabled = false
        let p = e.tapPoint(of: ArrowID(2))!
        e.handleRelease(screenPoint: p, touchTimestamp: CACurrentMediaTime())
        XCTAssertTrue(releases.isEmpty, "input disabled: nothing reported")
        e.inputEnabled = true
        e.handleRelease(screenPoint: p, touchTimestamp: CACurrentMediaTime())
        XCTAssertEqual(releases, [ArrowID(2)])
        e.allowedArrows = [ArrowID(0)]
        e.handleRelease(screenPoint: p, touchTimestamp: CACurrentMediaTime())
        XCTAssertEqual(releases.last, .some(nil), "a tutorial restriction turns other arrows into misses")
    }

    func testExitMoverIsBuiltInOneTransactionWithFullInkAndReportsItsBeats() {
        let e = makeEngine()
        host(e)
        let level = LabBoards.hitBoard()
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        let rules = LabRules(level: level)
        let events = rules.tap(ArrowID(2), at: 0)
        e.present(events)
        let m = e.movers[ArrowID(2)]
        XCTAssertNotNil(m)
        XCTAssertEqual(m?.kind, .exit)
        XCTAssertTrue(e.nodes[ArrowID(2)]!.body.isHidden, "the rest layers hide in the same transaction")
        // P1: nothing in the mover carries an implicit fade (no action-created opacity animation)
        for l in [m!.root] + (m!.root.sublayers ?? []) {
            XCTAssertFalse((l.animationKeys() ?? []).contains("opacity"), "implicit fade on \(l)")
            XCTAssertEqual(l.opacity, 1)
        }
        XCTAssertFalse(e.isSettled)
        wait(1.2)
        XCTAssertTrue(beats.contains(.exitLeftBoard(ArrowID(2))))
        XCTAssertTrue(beats.contains(.exitFinished(ArrowID(2))))
        XCTAssertNil(e.movers[ArrowID(2)])
        XCTAssertFalse(e.nodes[ArrowID(2)]!.attached)
    }

    func testBumpReportsContactThenFinishedAndStaysRed() {
        let e = makeEngine()
        host(e)
        let level = LabBoards.warmBoard()
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        let rules = LabRules(level: level)
        let t0 = CACurrentMediaTime()
        e.present(rules.tap(ArrowID(8), at: 0))
        XCTAssertEqual(e.movers[ArrowID(8)]?.kind, .bump)
        var contactAt: CFTimeInterval?
        let end = Date().addingTimeInterval(1.5)
        while Date() < end {
            RunLoop.main.run(until: Date().addingTimeInterval(0.005))
            if contactAt == nil, beats.contains(.bumpContact(ArrowID(8))) {
                contactAt = CACurrentMediaTime() - t0
                e.present(rules.contact(ArrowID(8)))
            }
            if beats.contains(.bumpFinished(ArrowID(8))) { break }
        }
        let planned = e.config.bumpOutBase + e.config.bumpOutPerCell * (3 - Metrics.headApexPast(.right) - Metrics.stroke / 2)
        XCTAssertNotNil(contactAt)
        XCTAssertEqual(contactAt ?? 0, planned, accuracy: 0.05, "the contact beat comes from the contact keyframe")
        XCTAssertTrue(beats.contains(.bumpFinished(ArrowID(8))))
        let n = e.nodes[ArrowID(8)]!
        XCTAssertTrue(n.marked)
        XCTAssertFalse(n.body.isHidden)
        XCTAssertEqual(n.body.strokeColor, e.config.markedColor)
        XCTAssertEqual(beats.filter { $0 == .bumpContact(ArrowID(8)) }.count, 1)
    }

    func testLastExitLeftBoardFiresOnceAfterTheLastArrow() {
        let e = makeEngine()
        host(e)
        let level = LabBoards.hitBoard()
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        let rules = LabRules(level: level)
        for id in rules.greedyOrder() { e.present(rules.tap(id, at: 0)) }
        wait(1.5)
        XCTAssertEqual(beats.filter { $0 == .lastExitLeftBoard }.count, 1)
        XCTAssertTrue(e.movers.isEmpty)
    }

    func testProbeCarriesTapPointsInsideThePlayRect() throws {
        let e = makeEngine(["-pc.uitest", "1"])
        host(e)
        let level = LabBoards.level("L032", bundle: .main)!
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        let p = e.probe()
        XCTAssertEqual(p.arrows.count, 53)
        XCTAssertEqual(p.pitch, 17.864, accuracy: 0.01)
        let play = e.config.playRect(in: CGSize(width: 393, height: 852))
        for a in p.arrows {
            XCTAssertTrue(play.contains(CGPoint(x: a.x, y: a.y)), "a\(a.id) tap point \(a.x),\(a.y)")
            let cp = e.screenToContent(CGPoint(x: a.x, y: a.y))
            XCTAssertEqual(e.stage!.hit.owner(e.stage!.layout.cell(at: cp)), ArrowID(a.id))
        }
        let json = p.json()
        for key in ["\"lvl\"", "\"zoom\"", "\"pitch\"", "\"settled\"", "\"moving\"", "\"arrows\"", "\"obstacles\""] {
            XCTAssertTrue(json.contains(key), key)
        }
    }

    func testFreezeHoldsTheStageAtAnExactSequenceTime() {
        let e = makeEngine()
        host(e)
        let level = LabBoards.hitBoard()
        e.load(StageSetup(level: level, screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
        let f0 = e.container.screenFX.localNow
        e.present(LabRules(level: level).tap(ArrowID(2), at: 0))
        e.freezeSequence(stageStart: s0, fxStart: f0, at: 0.2)
        wait(0.4)
        XCTAssertEqual(e.roots.stage.speed, 0)
        XCTAssertEqual(e.roots.stage.convertTime(CACurrentMediaTime(), from: nil), s0 + 0.2, accuracy: 1e-6)
        XCTAssertNotNil(e.movers[ArrowID(2)], "frozen mid-exit: the mover is still there")
        e.setFrozen(false)
        wait(1.2)
        XCTAssertNil(e.movers[ArrowID(2)], "resumed: the exit finished")
    }
}
