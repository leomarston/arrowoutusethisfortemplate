import XCTest

/// GAME G1 on the real app (SPEC-architecture §9.7 rules: base args, anchored predicates, probe values, no sleeps for
/// animations except the 3 s hold windows the acceptance names). Covers the §12.2 G1 items that need the real board and
/// shell: the probe's `t` stays constant for 3 s before the first tap, during Pause, the Quit Level? popup, an offer and the
/// unlock overlay; the time-out chain (`-pc.timer 3`) and the hearts-out chain (`-pc.hearts 1`) through the S2 popups; a
/// win banked before the celebration (the app killed during it is still won at the relaunch); 50 real taps with the
/// same-frame log on (`-pc.sameFrame 1`: the app appends each tap's timings to Documents/sameframe.txt).
final class GameFlowTests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    /// A level screen on L32 (Normal, 3:00) for a player who has seen home, with no tutorial or unlock in the way.
    private func level(_ n: Int = 32, _ extra: [String] = []) -> XCUIApplication {
        AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "\(n)", "-pc.go", "level", "-pc.tutorials", "skip",
                             "-pc.unlocks", "skip"] + extra)
    }

    private func t(_ p: [String: Any]?) -> Double? { p?["t"] as? Double }
    private func phase(_ p: [String: Any]?) -> String? { p?["phase"] as? String }

    /// The probe once the stage is playable (`ready`, the intro acked).
    private func waitReady(_ app: XCUIApplication, timeout: TimeInterval = 25) -> [String: Any] {
        guard let p = app.waitForProbe(timeout: timeout, { ($0["phase"] as? String) == "ready" }) else {
            XCTFail("the level never became ready; probe \(String(describing: app.probe()))\n\(app.debugDescription)")
            return [:]
        }
        return p
    }

    /// A free (or blocked) visible arrow's tap point from the probe.
    private func arrow(_ p: [String: Any], free: Bool) -> (id: Int, x: Double, y: Double)? {
        let arrows = p["arrows"] as? [[String: Any]] ?? []
        for a in arrows where (a["free"] as? Bool) == free && (a["red"] as? Bool) != true {
            if let id = a["id"] as? Int, let x = a["x"] as? Double, let y = a["y"] as? Double, x >= 0, y >= 0 { return (id, x, y) }
        }
        return nil
    }

    /// Reads `t` back to back for `seconds` (the probe refreshes at 4 Hz; one XCUITest query takes ≈ 0.3–0.4 s, so 3 s
    /// give ≈ 7–9 reads) and asserts it never changed; the read count is printed.
    private func assertTConstant(_ app: XCUIApplication, seconds: Double = 3, _ what: String) {
        guard let t0 = t(app.probe()) else { return XCTFail("\(what): no probe") }
        let start = Date()
        let end = start.addingTimeInterval(seconds)
        var reads = 0
        while Date() < end {
            if let v = t(app.probe()) { reads += 1; XCTAssertEqual(v, t0, accuracy: 1e-9, "\(what): t moved \(t0) → \(v)") }
            RunLoop.current.run(until: Date().addingTimeInterval(0.05))
        }
        print("[G1] \(what): t = \(t0) constant over \(reads) probe reads in \(String(format: "%.2f", Date().timeIntervalSince(start))) s")
        XCTAssertGreaterThanOrEqual(reads, 6, "\(what): too few probe reads over \(seconds) s")
    }

    /// Taps the first free arrow and waits for the timer to start.
    private func firstTap(_ app: XCUIApplication, _ p: [String: Any]) {
        guard let a = arrow(p, free: true) else { return XCTFail("no free arrow in \(p)") }
        app.tap(screenX: a.x, y: a.y)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["timerStarted"] as? Bool) == true }, "the first tap starts the timer")
    }

    // MARK: holds

    func testTimerIsFrozenBeforeTheFirstTapAndDuringPause() {
        let app = level()
        let p = waitReady(app)
        XCTAssertEqual(t(p), 180)
        assertTConstant(app, "before the first tap")
        firstTap(app, p)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { (self.t($0) ?? 180) < 179.5 }, "the timer runs after the first tap")
        app.element("hud.pause").tap()
        XCTAssertTrue(app.element("popup.pause").waitForExistence(timeout: 5), app.debugDescription)
        assertTConstant(app, "Pause")
        let held = t(app.probe()) ?? 0
        app.element("popup.pause.primary").tap()                                            // Resume
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { (self.t($0) ?? held) < held - 0.5 }, "Resume releases the timer")
    }

    func testQuitLevelPopupHoldsTheTimerAndXReturns() {
        let app = level()
        let p = waitReady(app)
        firstTap(app, p)
        app.element("hud.back").tap()
        XCTAssertTrue(app.element("popup.quitLevel").waitForExistence(timeout: 5), app.debugDescription)
        assertTConstant(app, "Quit Level?")
        app.element("popup.quitLevel.close").tap()
        XCTAssertTrue(app.element("popup.quitLevel").wait(for: "exists == false", timeout: 5))
        XCTAssertEqual(phase(app.probe()), "playing")
    }

    func testUnlockOverlayHoldsTheTimer() {
        // the overlay arrives 6 s after the level screen (S1's -pc.popupDelay), over a running timer
        let app = level(32, ["-pc.popup", "unlock:pipe", "-pc.popupDelay", "6"])
        let p = waitReady(app)
        firstTap(app, p)
        XCTAssertTrue(app.element("unlock.overlay").waitForExistence(timeout: 12), app.debugDescription)
        assertTConstant(app, "the unlock overlay")
    }

    // MARK: the fail chains

    func testTimeOutChainDeclinedCostsALife() {
        let app = level(32, ["-pc.timer", "3"])
        let p = waitReady(app)
        XCTAssertEqual(t(p), 3)
        firstTap(app, p)
        let offer = app.element("popup.outOfTime")
        XCTAssertTrue(offer.waitForExistence(timeout: 10), "Out of Time! after 0:00 + 1.61 s\n\(app.debugDescription)")
        XCTAssertEqual(phase(app.probe()), "offer")
        assertTConstant(app, "the Out of Time! offer")
        XCTAssertEqual(t(app.probe()), 0)
        app.element("popup.outOfTime.close").tap()
        let cont = app.element("popup.continue")
        XCTAssertTrue(cont.waitForExistence(timeout: 5), app.debugDescription)
        XCTAssertTrue(app.element("popup.variant").wait(for: "value == %@", "life"), "no streak: straight to 'You will lose a life!'")
        app.element("popup.continue.close").tap()
        let failed = app.element("popup.levelFailed")
        XCTAssertTrue(failed.waitForExistence(timeout: 5), app.debugDescription)
        app.element("popup.levelFailed.close").tap()
        let lives = app.element("home.lives")
        XCTAssertTrue(lives.waitForExistence(timeout: 10), "X on Level Failed → home\n\(app.debugDescription)")
        XCTAssertTrue(lives.wait(for: "value BEGINSWITH %@", "4|"), "one life lost, counting down: \(lives.debugDescription)")
    }

    func testHeartsOutChainAndTryAgainIsTheSameBoard() {
        let app = level(32, ["-pc.hearts", "1"])
        let p = waitReady(app)
        let lvl = p["lvl"] as? Int
        guard let a = arrow(p, free: false) else { return XCTFail("no blocked arrow on L32") }
        app.tap(screenX: a.x, y: a.y)                                                        // a bump: the last heart
        let offer = app.element("popup.outOfTime")
        XCTAssertTrue(offer.waitForExistence(timeout: 8), "Out of Lives! 0.60 s after the contact\n\(app.debugDescription)")
        XCTAssertTrue(app.element("popup.variant").wait(for: "value == %@", "hearts"))
        XCTAssertEqual(app.probe()?["hearts"] as? Int, 0)
        assertTConstant(app, "the Out of Lives! offer")
        app.element("popup.outOfTime.close").tap()
        XCTAssertTrue(app.element("popup.continue").waitForExistence(timeout: 5))
        app.element("popup.continue.close").tap()
        XCTAssertTrue(app.element("popup.levelFailed").waitForExistence(timeout: 5))
        app.element("popup.levelFailed.primary").tap()                                       // Try Again
        let again = waitReady(app)
        XCTAssertEqual(again["lvl"] as? Int, lvl, "Try Again = the same board")
        XCTAssertEqual(again["hearts"] as? Int, 1)
        XCTAssertEqual(again["timerStarted"] as? Bool, false, "a fresh timer, frozen until the first tap")
    }

    // MARK: the win is banked at the tap

    func testKilledDuringTheCelebrationIsStillAWin() {
        // L7 (Linked Arrows' level; its unlock is marked seen) played by the autoplayer through the real board
        let app = level(7, ["-pc.autoplay", "1", "-pc.autoplayRate", "0.25"])
        let skip = app.element("celebration.skip")
        XCTAssertTrue(skip.waitForExistence(timeout: 90), "the celebration runs\n\(app.debugDescription)")
        app.terminate()                                                                     // killed during the celebration
        let again = AppUnderTest.launch(["-pc.go", "home"])
        let plate = again.element("home.level")
        XCTAssertTrue(plate.waitForExistence(timeout: 20), again.debugDescription)
        XCTAssertTrue(plate.wait(for: "value BEGINSWITH %@", "8|"), "L7 was banked as won: \(plate.debugDescription)")
        XCTAssertTrue(again.element("home.coins").wait(for: "value == %@", "1020"), "1000 + 20, banked at the tap")
        XCTAssertTrue(again.element("home.lives").wait(for: "value BEGINSWITH %@", "full"), "the life came back with the win")
    }

    // MARK: 50 real taps with the same-frame log

    func testFiftyRealTapsLogTheSameFramePipeline() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.sameFrame", "1", "-pc.tutorials", "skip"])
        var taps = 0
        let deadline = Date().addingTimeInterval(240)
        while taps < 50 && Date() < deadline {
            let cont = app.element("win.continue")
            if app.element("popup.win").exists, cont.exists, cont.isHittable {
                cont.tap()
                _ = app.element("popup.win").wait(for: "exists == false", timeout: 5)
                continue
            }
            guard let p = app.probe(), ["ready", "playing"].contains(phase(p) ?? ""), let a = arrow(p, free: true) else {
                RunLoop.current.run(until: Date().addingTimeInterval(0.2))
                continue
            }
            app.tap(screenX: a.x, y: a.y)
            taps += 1
            _ = app.waitForProbe(timeout: 2) { q in
                !((q["arrows"] as? [[String: Any]] ?? []).contains { ($0["id"] as? Int) == a.id && ($0["free"] as? Bool) == true })
                    || (q["lvl"] as? Int) != (p["lvl"] as? Int) || (q["stage"] as? Int) != (p["stage"] as? Int)
            }
        }
        XCTAssertGreaterThanOrEqual(taps, 50, "50 real taps through the FTUE levels")
    }
}
