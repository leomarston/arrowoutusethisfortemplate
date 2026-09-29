import XCTest
import UIKit
import PathCore
@testable import ArrowOut

/// FIX-B (SPEC-architecture §6.1 "Loading stays until the boot finishes, cap ui.loading.capSeconds"; V1 run 4
/// ShellS2UITests:31: Loading stayed up 29 s under load). The boot's cap must cap:
///  - `AppModel.completes(_:within:)` answers at the cap while the task still runs (the former `withTaskGroup` waited for the
///    warm-up child before returning — V3 r2 logged "warmup 8.800 s" against the 4 s cap);
///  - `BoardEngine.hurryWarmUp()` ends a warm-up whose frames never come (its view out of the window: the display link is
///    paused) at once, with its board cleared and its delegate restored, so the first screen never shares the engine with it;
///  - a hurry before the warm-up started still decodes the sprites and builds the door/key art every level needs, and skips
///    the board part.
@MainActor final class BootCapTests: XCTestCase, BoardDelegate {
    var window: UIWindow?

    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval) {}
    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval) {}
    func boardBeat(_ beat: BoardBeat) {}
    func boardZoomChanged(scale: CGFloat) {}

    private func makeEngine() -> BoardEngine {
        let a = LaunchArgs(arguments: [])
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("bootcap-tests-\(UUID().uuidString)")
        let ctx = AppContext(args: a, tuning: Tuning.load(bundle: .main), clock: MotionClock(args: a),
                             store: PlayerStore(args: a, now: Date(), bundle: .main, directory: dir), hud: HUDModel(),
                             anchors: AnchorRegistry(), perf: PerfMonitor(), latency: LatencyProbe(), bundle: .main)
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

    func testCompletesAnswersAtTheCapWhileTheTaskRuns() async {
        let slow = Task { @MainActor in _ = try? await Task.sleep(nanoseconds: 3_000_000_000) }
        let t0 = Date()
        let finished = await AppModel.completes(slow, within: 0.2)
        let waited = Date().timeIntervalSince(t0)
        XCTAssertFalse(finished, "the cap answers first")
        XCTAssertLessThan(waited, 1.5, "answered at the 0.2 s cap, not when the 3 s task ended (waited \(waited) s)")
        slow.cancel()
    }

    func testCompletesAnswersTrueWhenTheTaskEndsFirst() async {
        let quick = Task { @MainActor in _ = try? await Task.sleep(nanoseconds: 50_000_000) }
        let t0 = Date()
        let finished = await AppModel.completes(quick, within: 3)
        XCTAssertTrue(finished)
        XCTAssertLessThan(Date().timeIntervalSince(t0), 1.5, "answered when the task ended, not at the 3 s cap")
    }

    func testHurryEndsAWarmUpWhoseFramesNeverCome() async {
        let e = makeEngine()
        host(e)
        let warm = Task { @MainActor in await e.prepare() }
        let deadline = Date().addingTimeInterval(15)
        while !(e.warmingUp && e.stage != nil), !e.warmedUp, Date() < deadline {
            try? await Task.sleep(nanoseconds: 5_000_000)
        }
        XCTAssertTrue(e.warmingUp && e.stage != nil, "the warm-up board is up (its frame-paced part runs)")
        e.view.removeFromSuperview()                        // no window: the display link pauses, no frame will come
        XCTAssertEqual(e.linkPaused, true)
        let t0 = Date()
        await e.hurryWarmUp()
        let took = Date().timeIntervalSince(t0)
        // unhurried, each frame wait of a paused link lasts its 5 s timeout (≥ 4 of them): ≥ 20 s
        XCTAssertLessThan(took, 2.0, "the hurried warm-up waits for no frame (took \(took) s)")
        XCTAssertTrue(e.warmedUp)
        XCTAssertFalse(e.warmingUp)
        XCTAssertNil(e.stage, "the warm-up board is cleared before the first screen can load its own")
        XCTAssertTrue(e.delegate === self, "the delegate is restored")
        await warm.value
    }

    func testHurryBeforeTheWarmUpStartedStillBuildsTheArtAndSkipsTheBoard() async {
        let e = makeEngine()
        host(e)
        await e.hurryWarmUp()
        XCTAssertTrue(e.warmedUp)
        XCTAssertFalse(e.warmingUp)
        XCTAssertNil(e.stage, "no warm-up board was loaded")
        XCTAssertNotNil(e.boardArt.doorTop, "the door slices every door level needs are built")
        XCTAssertNotNil(e.boardArt.keyOnly, "the key-only image is built")
        XCTAssertTrue(e.delegate === self)
    }
}
