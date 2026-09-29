import XCTest

/// B1 (SPEC-architecture §9.7 BoardInputTests, §12.2 B1 acceptance 2 + 4, §11 R6): real touches through XCUITest on the
/// real engine in BoardLab (`-pc.lab input`, the lab rules stand in for the session). Everything is read from the
/// `board.probe` element (§9.4): exited arrows leave `arrows`, `timerStarted` flips at the first arrow tap only.
final class BoardInputTests: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    private func launch(board: String, lab: String = "input") -> XCUIApplication {
        AppUnderTest.launch(["-pc.reset", "1", "-pc.go", "boardlab", "-pc.lab", lab, "-pc.labBoard", board])
    }

    private func arrows(_ p: [String: Any]) -> [[String: Any]] { p["arrows"] as? [[String: Any]] ?? [] }
    private func arrow(_ p: [String: Any], _ id: Int) -> [String: Any]? { arrows(p).first { $0["id"] as? Int == id } }
    private func point(_ a: [String: Any]) -> (Double, Double) { (a["x"] as? Double ?? -1, a["y"] as? Double ?? -1) }

    private func ready(_ app: XCUIApplication, count: Int) -> [String: Any] {
        guard let p = app.waitForProbe(timeout: 25, { self.arrows($0).count == count && $0["settled"] as? Bool == true }) else {
            print(app.debugDescription)
            XCTFail("the probe never showed \(count) settled arrows")
            return [:]
        }
        return p
    }

    private func gone(_ app: XCUIApplication, _ id: Int, timeout: TimeInterval = 5) -> [String: Any]? {
        app.waitForProbe(timeout: timeout) { self.arrow($0, id) == nil }
    }

    func testTwoSecondHoldFiresOnRelease() {
        let app = launch(board: "hit")
        let p0 = ready(app, count: 5)
        XCTAssertEqual(p0["timerStarted"] as? Bool, false)
        let (x, y) = point(arrow(p0, 2)!)
        app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x, dy: y)).press(forDuration: 2.0)
        let p1 = gone(app, 2)
        XCTAssertNotNil(p1, "a 2 s hold must fire on release (the original fires even after 5 s)")
        XCTAssertEqual(p1?["timerStarted"] as? Bool, true)
        XCTAssertEqual(arrows(p1 ?? [:]).count, 4)
    }

    func testSwipePansWithoutFiring() {
        let app = launch(board: "hit")
        let p0 = ready(app, count: 5)
        let (x, y) = point(arrow(p0, 4)!)
        let start = app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x, dy: y))
        let end = app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x - 52, dy: y))
        start.press(forDuration: 0.05, thenDragTo: end)
        guard let p1 = app.waitForProbe(timeout: 5, { p in
            guard let a = self.arrow(p, 4) else { return false }
            return abs(self.point(a).0 - x) > 10 && p["settled"] as? Bool == true
        }) else {
            print(app.debugDescription)
            return XCTFail("the swipe did not pan the board")
        }
        XCTAssertEqual(arrows(p1).count, 5, "a swipe never fires an arrow")
        XCTAssertEqual(p1["timerStarted"] as? Bool, false, "a pan never starts the timer")
        let (x1, y1) = point(arrow(p1, 4)!)
        XCTAssertLessThan(x1, x - 10, "panned left with the finger")
        XCTAssertEqual(y1, y, accuracy: 3)
        // the pan persists (VERIFIED L47e): still there a moment later
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))
        let p2 = app.probe() ?? [:]
        XCTAssertEqual(point(arrow(p2, 4)!).0, x1, accuracy: 2)
    }

    func testHeadTapSendsTheArrow() {
        let app = launch(board: "hit")
        let p0 = ready(app, count: 5)
        let pitch = p0["pitch"] as? Double ?? 0
        let (x, y) = point(arrow(p0, 3)!)                    // arrow 3 is two cells: its tap point is the head cell
        app.tap(screenX: x, y: y - 0.3 * pitch)               // the head triangle's tip area (it points up)
        XCTAssertNotNil(gone(app, 3), "a tap on the head triangle sends the arrow (VERIFIED L47b)")
    }

    func testTapFifteenPointsOffTheStrokeSendsIt() {
        let app = launch(board: "hit")
        let p0 = ready(app, count: 5)
        let (x, y) = point(arrow(p0, 2)!)                    // the isolated horizontal arrow's middle cell
        app.tap(screenX: x, y: y - 15)
        XCTAssertNotNil(gone(app, 2), "a tap 15 pt above an isolated stroke still sends it (VERIFIED L47c)")
        XCTAssertNotNil(arrow(app.probe() ?? [:], 0))
        XCTAssertNotNil(arrow(app.probe() ?? [:], 1))
    }

    func testMidpointTieGoesRight() {
        let app = launch(board: "hit")
        let p0 = ready(app, count: 5)
        let (xl, yl) = point(arrow(p0, 0)!)
        let (xr, yr) = point(arrow(p0, 1)!)
        XCTAssertEqual(yl, yr, accuracy: 0.01)
        app.tap(screenX: (xl + xr) / 2, y: yl)
        let p1 = gone(app, 1)
        XCTAssertNotNil(p1, "the midpoint between two parallel free arrows sends the right-hand one (VERIFIED L52a)")
        XCTAssertNotNil(arrow(p1 ?? [:], 0), "the left one stays")
    }

    func testPinchClampsAtBothLimitsAndNeverStartsTheTimer() {
        let app = launch(board: "L032")
        let p0 = ready(app, count: 53)
        XCTAssertEqual(p0["pitch"] as? Double ?? 0, 17.864, accuracy: 0.01)
        let board = app.element("board")
        board.pinch(withScale: 6, velocity: 4)
        guard let pIn = app.waitForProbe(timeout: 6, { ($0["zoom"] as? Double ?? 0) > 1.3 && $0["settled"] as? Bool == true }) else {
            return XCTFail("pinch-in did not zoom")
        }
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))     // the zoom bounce settles
        let pInSettled = app.probe() ?? pIn
        XCTAssertEqual(pInSettled["pitch"] as? Double ?? 0, 28.07, accuracy: 0.05, "clamps at 28.07 pt per cell")
        XCTAssertEqual(pInSettled["zoom"] as? Double ?? 0, 1.5713, accuracy: 0.003)
        board.pinch(withScale: 0.1, velocity: -4)
        board.pinch(withScale: 0.3, velocity: -3)
        RunLoop.current.run(until: Date().addingTimeInterval(1.5))
        guard let pOut = app.waitForProbe(timeout: 6, { ($0["zoom"] as? Double ?? 9) < 0.9 }) else {
            return XCTFail("pinch-out did not zoom out")
        }
        XCTAssertEqual(pOut["zoom"] as? Double ?? 0, 0.786, accuracy: 0.003, "clamps at 0.786 x fit")
        XCTAssertEqual(pOut["pitch"] as? Double ?? 0, 14.04, accuracy: 0.05)
        XCTAssertEqual(pOut["timerStarted"] as? Bool, false, "a pinch never starts the timer (VERIFIED L47a)")
        XCTAssertEqual(arrows(pOut).count, 53, "a pinch never fires an arrow")
        // taps still work after zooming out
        if let f = arrows(pOut).first(where: { $0["free"] as? Bool == true && ($0["x"] as? Double ?? -1) > 0 }) {
            let id = f["id"] as? Int ?? -1
            let (x, y) = point(f)
            app.tap(screenX: x, y: y)
            let unit = (f["unit"] as? [Int] ?? [id]).count
            XCTAssertNotNil(app.waitForProbe(timeout: 5) { self.arrows($0).count == 53 - unit }, "tap at 0.786x")
        }
    }

    func testSmallBoardOpensAtTheCapAndCannotZoomIn() {
        // PUBLISH B0 (level re-order): the lab loads a board by the level it SHIPS at (Levels/level_NNNN.json first); v552
        // L50's 10x18 board (16 arrows) ships at L57 now, so the test follows its board
        let app = launch(board: "L057")
        let p0 = ready(app, count: 16)
        XCTAssertEqual(p0["pitch"] as? Double ?? 0, 28.07, accuracy: 0.01, "v552 L50's board opens at the cap (VERIFIED)")
        app.element("board").pinch(withScale: 4, velocity: 4)
        RunLoop.current.run(until: Date().addingTimeInterval(1.5))
        let p1 = app.probe() ?? [:]
        XCTAssertEqual(p1["zoom"] as? Double ?? 0, 1.0, accuracy: 0.003)
        XCTAssertEqual(p1["pitch"] as? Double ?? 0, 28.07, accuracy: 0.01)
    }
}
