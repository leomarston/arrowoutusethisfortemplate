import XCTest

/// GAME G2 on the real app (SPEC-architecture §9.7 rules; §12.2 G2):
///  - `testFreshInstallFTUEWithoutLaunchArguments` — the REAL first run: the app launched with NO arguments on a fresh install
///    (the runner uninstalls it first; the test checks it really is fresh: the iOS notification alert over Loading). The
///    alert is answered, "Levels 1-4" is played through its four boards ("Tap to move!" on stage 1), then L5 and L6 (no home
///    between), and the first home flies +120 onto 1000 → 1120. A relaunch (no arguments) shows no alert again. Without the
///    probe (no `-pc.uitest`) the taps come from `FTUETaps` — the arrows' tap points and a solvable order recorded from the
///    probe by `testRecordFTUETapTable` (the boards and the fit are deterministic: the same points on every 393 × 852 phone).
///    Opt-in (`TEST_RUNNER_G2_FRESH=1`): it needs the uninstall, so a suite run without it would fail for the wrong reason.
///  - boosters: the hourglass freezes the probe's `t` for flight + 10 s, then it runs again; the bulb zooms the board to max
///    and back to fit when the hinted arrow leaves; at 0 stock the booster popup buys x3 for 900.
///  - the L7 unlock overlay on the first Play from home (tap anywhere), not on the retry.
final class GameG2UITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private var env: [String: String] { ProcessInfo.processInfo.environment }

    private func level(_ n: Int, _ extra: [String] = []) -> XCUIApplication {
        AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "\(n)", "-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"] + extra)
    }

    private func waitReady(_ app: XCUIApplication, timeout: TimeInterval = 25) -> [String: Any] {
        guard let p = app.waitForProbe(timeout: timeout, { ($0["phase"] as? String) == "ready" }) else {
            XCTFail("the level never became ready; probe \(String(describing: app.probe()))\n\(app.debugDescription)")
            return [:]
        }
        return p
    }

    private func free(_ p: [String: Any], skipping: Set<Int> = []) -> (id: Int, x: Double, y: Double)? {
        for a in (p["arrows"] as? [[String: Any]] ?? []) where (a["free"] as? Bool) == true && (a["red"] as? Bool) != true {
            if let id = a["id"] as? Int, !skipping.contains(id), let x = a["x"] as? Double, let y = a["y"] as? Double, x >= 0, y >= 0 {
                return (id, x, y)
            }
        }
        return nil
    }

    private func shot(_ name: String) {
        let a = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        a.name = name
        a.lifetime = .keepAlways
        add(a)
    }

    // MARK: the real first run (no launch arguments)

    func testFreshInstallFTUEWithoutLaunchArguments() throws {
        try XCTSkipUnless(env["G2_FRESH"] == "1", "opt-in: run after `simctl uninstall` with TEST_RUNNER_G2_FRESH=1")
        let app = XCUIApplication()
        app.launchArguments = []
        app.launchEnvironment = [:]
        app.launch()
        // Loading + the iOS notification alert over it (first launch)
        XCTAssertTrue(app.element("screen.loading").waitForExistence(timeout: 10), app.debugDescription)
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let alert = springboard.alerts.firstMatch
        XCTAssertTrue(alert.waitForExistence(timeout: 12), "the notification prompt over Loading on the first launch")
        shot("01-loading-notification-prompt")
        XCTAssertTrue(app.element("screen.loading").exists, "…while Loading is still up")
        let allow = alert.buttons.element(boundBy: 1)                   // [Don't Allow, Allow]
        allow.tap()
        XCTAssertTrue(alert.waitForNonExistence(timeout: 5))

        // "Levels 1-4": the board cross-fades in with the HUD in place and "Tap to move!" on stage 1
        let hudLevel = app.element("hud.level")
        XCTAssertTrue(hudLevel.waitForExistence(timeout: 15), app.debugDescription)
        XCTAssertTrue(hudLevel.wait(for: "value == %@", "Levels 1-4"))
        XCTAssertTrue(app.element("tutorial.caption").waitForExistence(timeout: 5), "the \"Tap to move!\" hint on stage 1")
        shot("02-levels1-4-tap-to-move")
        for (k, stage) in FTUETaps.levels1to4.enumerated() {
            if k > 0 { RunLoop.current.run(until: Date().addingTimeInterval(2.2)) }   // W + 0.7 s gap + the draw-in
            play(app, stage)
            if k == 0 { XCTAssertTrue(app.element("tutorial.caption").waitForNonExistence(timeout: 3), "the hint left at the first tap") }
        }
        continueWin(app, expectLabel: "Level 1-4")
        // Level 5 and Level 6 straight away (no home before the L6 win)
        for (n, taps) in [(5, FTUETaps.level5), (6, FTUETaps.level6)] {
            XCTAssertTrue(hudLevel.wait(for: "value == %@", "Level \(n)", timeout: 10), "Level \(n) follows directly: \(app.debugDescription)")
            XCTAssertFalse(app.element("screen.home").exists, "no home before the L6 win")
            RunLoop.current.run(until: Date().addingTimeInterval(1.8))     // the intro zoom (1.35 s) + the HUD drop
            play(app, taps)
            continueWin(app, expectLabel: nil)
        }
        // the first home: +120 flies onto the 1000 start
        XCTAssertTrue(app.element("screen.home").waitForExistence(timeout: 10), app.debugDescription)
        let coins = app.element("home.coins")
        XCTAssertTrue(coins.wait(for: "value == %@", "1120", timeout: 8), "1000 → 1120: \(String(describing: coins.value))")
        shot("03-first-home-1120")
        XCTAssertTrue(app.element("home.play").wait(for: "value == %@", "7"))

        // the prompt is asked once per install: a relaunch (no arguments) goes home without it
        app.terminate()
        app.launch()
        XCTAssertTrue(app.element("screen.home").waitForExistence(timeout: 15), app.debugDescription)
        XCTAssertFalse(springboard.alerts.firstMatch.waitForExistence(timeout: 3), "no notification prompt on the second launch")
        XCTAssertTrue(app.element("home.coins").wait(for: "value == %@", "1120"))
    }

    /// Taps a recorded board: each point once, 0.45 s apart like the recorder (every arrow is free when its turn comes).
    private func play(_ app: XCUIApplication, _ taps: [[Double]]) {
        for p in taps {
            app.tap(screenX: p[0], y: p[1])
            RunLoop.current.run(until: Date().addingTimeInterval(0.45))
        }
    }

    private func continueWin(_ app: XCUIApplication, expectLabel: String?) {
        let cont = app.element("win.continue")
        XCTAssertTrue(cont.waitForExistence(timeout: 12), "the win panel: \(app.debugDescription)")
        cont.tap()
    }

    /// Prints the FTUE tap table from the probe (opt-in: TEST_RUNNER_G2_RECORD=1). "Levels 1-4" is recorded through its REAL
    /// stage transitions in one launch (as the first run plays it), L5 and L6 from their own loads (a hard cut from the panel
    /// is the same load).
    func testRecordFTUETapTable() throws {
        try XCTSkipUnless(env["G2_RECORD"] == "1", "opt-in recorder")
        var out: [String] = []
        func record(_ app: XCUIApplication, _ name: String, stage: Int) {
            guard var p = app.waitForProbe(timeout: 25, { ($0["phase"] as? String) == "ready" && ($0["stage"] as? Int) == stage }) else {
                return XCTFail("\(name) never became ready: \(String(describing: app.probe()))")
            }
            var taps: [[Double]] = []
            var tapped: Set<Int> = []
            while let a = free(p, skipping: tapped) {
                taps.append([a.x, a.y])
                tapped.insert(a.id)
                app.tap(screenX: a.x, y: a.y)
                RunLoop.current.run(until: Date().addingTimeInterval(0.45))
                guard let q = app.probe(), ["ready", "playing"].contains(q["phase"] as? String ?? ""), (q["stage"] as? Int) == stage else { break }
                p = q
            }
            XCTAssertNotNil(app.waitForProbe(timeout: 5) { ["stageClear", "won"].contains($0["phase"] as? String ?? "") || (($0["stage"] as? Int) ?? 0) > stage },
                            "\(name) cleared by the recorded order")
            let line = "\(name): " + taps.map { String(format: "[%.1f, %.1f]", $0[0], $0[1]) }.joined(separator: ", ")
            print("[G2TAPS] " + line)
            out.append(line)
        }
        let first = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "1", "-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"])
        for k in 0..<4 { record(first, "L1s\(k)", stage: k) }
        for n in [5, 6] {
            let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "\(n)", "-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"])
            record(app, "L\(n)s0", stage: 0)
        }
        let a = XCTAttachment(string: out.joined(separator: "\n"))
        a.name = "ftue-taps"
        a.lifetime = .keepAlways
        add(a)
    }

    // MARK: boosters

    func testHourglassFreezesTheTimerThenItRunsAgain() {
        let app = level(32, ["-pc.boosters", "freeze=3,hint=3"])
        let p = waitReady(app)
        guard let a = free(p) else { return XCTFail("no free arrow") }
        app.tap(screenX: a.x, y: a.y)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["timerStarted"] as? Bool) == true })
        let booster = app.element("hud.booster.freeze")
        XCTAssertTrue(booster.wait(for: "value == %@", "stock:3"))
        let bTap = Date()                                                    // B is after this (the tap reaches the app later)
        booster.tap()
        XCTAssertTrue(booster.wait(for: "value == %@", "stock:2", timeout: 3), "the badge shows n − 1 at once")
        RunLoop.current.run(until: Date().addingTimeInterval(0.6))           // the probe refreshes at 4 Hz: read it after B
        guard let t0 = app.probe()?["t"] as? Double else { return XCTFail("no probe") }
        shot("freeze-frost-and-tray")
        // frozen through the flight (1.6 s) and the 10 s countdown: every read that COMPLETED before bTap + 11.3 s (< B + 11.6)
        // must show t0 (XCUITest queries take 0.3–1 s each, so the wall clock of the test is the bound, not a read count)
        let end = bTap.addingTimeInterval(11.3)
        var reads = 0
        while Date() < end {
            let t = app.probe()?["t"] as? Double
            if Date() < end, let t { reads += 1; XCTAssertEqual(t, t0, accuracy: 1e-6, "t moved during the freeze") }
            RunLoop.current.run(until: Date().addingTimeInterval(0.2))
        }
        print("[G2] freeze: t = \(t0) constant over \(reads) probe reads until bTap + 11.3 s")
        XCTAssertGreaterThan(reads, 6)
        // …and running again after B + 11.6
        XCTAssertNotNil(app.waitForProbe(timeout: 6) { (($0["t"] as? Double) ?? t0) < t0 - 0.5 }, "the timer resumes after the freeze")
        shot("freeze-after-resume")
    }

    /// SPEC.md ruling 30 (K-4): the hourglass used BEFORE the first tap flies at once; its tray (B + 1.60) holds "10" with the
    /// timer frozen until the first board tap, which starts the 10 s countdown (the timer still frozen through it).
    func testHourglassBeforeTheFirstTapHoldsThenCountsFromTheTap() {
        let app = level(32, ["-pc.boosters", "freeze=3,hint=3"])
        let p = waitReady(app)
        let t0 = p["t"] as? Double ?? 0
        let booster = app.element("hud.booster.freeze")
        XCTAssertTrue(booster.wait(for: "value == %@", "stock:3"))
        booster.tap()
        XCTAssertTrue(booster.wait(for: "value == %@", "stock:2", timeout: 3), "the stock is taken at B")
        RunLoop.current.run(until: Date().addingTimeInterval(4.0))           // past B + 1.60: the tray is out, holding "10"
        shot("freeze-before-first-tap-tray-holds-10")
        XCTAssertEqual(app.probe()?["timerStarted"] as? Bool, false, "no board tap yet: the timer has not started")
        XCTAssertEqual(app.probe()?["t"] as? Double ?? -1, t0, accuracy: 1e-6)
        guard let q = app.probe(), let a = free(q) else { return XCTFail("no free arrow") }
        let tap = Date()
        app.tap(screenX: a.x, y: a.y)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["timerStarted"] as? Bool) == true }, "the first tap starts the timer")
        RunLoop.current.run(until: Date().addingTimeInterval(2.5))
        shot("freeze-after-first-tap-counting")
        // the countdown runs 10 s from the tap: every read completed before tap + 9.3 s shows the limit
        let end = tap.addingTimeInterval(9.3)
        var reads = 0
        while Date() < end {
            let t = app.probe()?["t"] as? Double
            if Date() < end, let t { reads += 1; XCTAssertEqual(t, t0, accuracy: 1e-6, "t moved during the countdown") }
        }
        XCTAssertGreaterThan(reads, 4)
        XCTAssertNotNil(app.waitForProbe(timeout: 6) { (($0["t"] as? Double) ?? t0) < t0 - 0.5 }, "the timer runs after the countdown")
    }

    /// The freeze tray as drawn (`hud.freeze.tray`, `-pc.uitest` only; FIX-A2): nil while no freeze runs.
    private struct Tray {
        let held: Bool, phase: String, digit: Int, bar: Double, left: Double, raw: String
    }

    private func tray(_ app: XCUIApplication) -> Tray? {
        guard let v = app.element("hud.freeze.tray").value as? String, v != "off" else { return nil }
        var kv: [String: String] = [:]
        for part in v.split(separator: " ") {
            let p = part.split(separator: "=")
            if p.count == 2 { kv[String(p[0])] = String(p[1]) }
        }
        guard let held = kv["held"], let phase = kv["phase"], let digit = kv["digit"].flatMap({ Int($0) }),
              let bar = kv["bar"].flatMap({ Double($0) }), let left = kv["left"].flatMap({ Double($0) }) else { return nil }
        return Tray(held: held == "1", phase: phase, digit: digit, bar: bar, left: left, raw: v)
    }

    private func waitTray(_ app: XCUIApplication, timeout: TimeInterval, _ ok: (Tray?) -> Bool) -> Tray?? {
        let deadline = Date().addingTimeInterval(timeout)
        repeat {
            let t = tray(app)
            if ok(t) { return .some(t) }
            RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        } while Date() < deadline
        return nil
    }

    /// FIX-A2 (G2's request "freeze HUD effect pausable"): Pause during the freeze's countdown holds the tray together with
    /// the level timer — the same digit, bar and time left 3 s later — and Resume continues it from where it stood: it ends
    /// what was left AFTER the resume (the paused seconds are not lost), and only then does the timer run.
    func testPauseHoldsTheFreezeTrayAndResumeContinuesIt() {
        let app = level(32, ["-pc.boosters", "freeze=3,hint=3"])
        let p = waitReady(app)
        guard let a = free(p) else { return XCTFail("no free arrow") }
        app.tap(screenX: a.x, y: a.y)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["timerStarted"] as? Bool) == true })
        let trayElement = app.element("hud.freeze.tray")
        XCTAssertTrue(trayElement.waitForExistence(timeout: 5), "the tray probe (-pc.uitest): \(app.debugDescription)")
        XCTAssertTrue(trayElement.wait(for: "value == %@", "off"), "no freeze yet: \(trayElement.debugDescription)")
        let booster = app.element("hud.booster.freeze")
        booster.tap()
        XCTAssertTrue(booster.wait(for: "value == %@", "stock:2", timeout: 3), "the badge shows n − 1 at once")
        // mid-countdown: the tray is out (B + 1.60) and a few of its 10 s have run
        guard let mid = waitTray(app, timeout: 12, { ($0?.phase == "counting") && ($0?.left ?? 99) <= 7.5 }) ?? nil else {
            return XCTFail("the countdown never ran: \(trayElement.debugDescription)")
        }
        XCTAssertFalse(mid.held)
        XCTAssertLessThan(mid.bar, 1, "the bar shrinks while it counts: \(mid.raw)")

        app.element("hud.pause").tap()
        XCTAssertTrue(app.element("popup.pause").waitForExistence(timeout: 5), app.debugDescription)
        guard let held = waitTray(app, timeout: 3, { $0?.held == true }) ?? nil else {
            return XCTFail("the tray never held under Pause: \(trayElement.debugDescription)")
        }
        XCTAssertEqual(held.phase, "counting", held.raw)
        XCTAssertGreaterThan(held.left, 1.5, "paused mid-countdown: \(held.raw)")
        let t1 = app.probe()?["t"] as? Double
        RunLoop.current.run(until: Date().addingTimeInterval(3.0))
        shot("freeze-paused-tray-held")
        let after = tray(app)
        XCTAssertEqual(after?.raw, held.raw, "3 s under Pause: the tray's digit, bar and time left stood still")
        XCTAssertEqual(app.probe()?["t"] as? Double, t1, "the level timer stood still too")

        app.element("popup.pause.primary").tap()                             // Resume
        let resumed = Date()
        XCTAssertTrue(app.element("popup.pause").waitForNonExistence(timeout: 5))
        guard let running = waitTray(app, timeout: 4, { $0?.held == false && ($0?.left ?? 99) < held.left - 0.2 }) ?? nil else {
            return XCTFail("the tray did not continue after Resume: \(trayElement.debugDescription)")
        }
        XCTAssertEqual(running.phase, "counting", running.raw)
        XCTAssertGreaterThan(running.left, held.left - 3.0, "it continued from where it stood, not from B's clock: \(running.raw)")
        XCTAssertEqual(app.probe()?["t"] as? Double, t1, "the timer is still frozen while the tray counts")
        // the tray ends what was left after the resume (± XCUITest's read latency), then the timer runs
        guard waitTray(app, timeout: held.left + 5, { $0 == nil || $0?.phase == "ended" }) != nil else {
            return XCTFail("the tray never ended: \(trayElement.debugDescription)")
        }
        let endedAfter = Date().timeIntervalSince(resumed)
        print(String(format: "[FIX-A2] paused with %.2f s left; the tray ended %.2f s after Resume", held.left, endedAfter))
        XCTAssertGreaterThan(endedAfter, held.left - 0.6, "the held seconds were not lost (ended too early)")
        XCTAssertNotNil(app.waitForProbe(timeout: 4) { (($0["t"] as? Double) ?? (t1 ?? 0)) < (t1 ?? 0) - 0.3 }, "the timer runs after the freeze")
    }

    /// FIX-A2: the background holds the freeze tray at once (there are no display-link frames there to see the session's hold):
    /// back in the level, Pause is up (§8.6) and the tray shows about what it showed when the app left — not minus the seconds
    /// spent outside — and it continues from there after Resume.
    func testTheBackgroundHoldsTheFreezeTray() {
        let app = level(32, ["-pc.boosters", "freeze=3,hint=3"])
        let p = waitReady(app)
        guard let a = free(p) else { return XCTFail("no free arrow") }
        app.tap(screenX: a.x, y: a.y)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["timerStarted"] as? Bool) == true })
        let booster = app.element("hud.booster.freeze")
        booster.tap()
        XCTAssertTrue(booster.wait(for: "value == %@", "stock:2", timeout: 3))
        guard let mid = waitTray(app, timeout: 12, { ($0?.phase == "counting") && ($0?.left ?? 99) <= 8.5 }) ?? nil else {
            return XCTFail("the countdown never ran: \(app.element("hud.freeze.tray").debugDescription)")
        }
        XCUIDevice.shared.press(.home)
        RunLoop.current.run(until: Date().addingTimeInterval(5.0))          // 5 s outside the game
        app.activate()
        XCTAssertTrue(app.element("popup.pause").waitForExistence(timeout: 10), "back from the background: Pause (§8.6)")
        guard let back = waitTray(app, timeout: 3, { $0?.held == true }) ?? nil else {
            return XCTFail("the tray is not held under Pause: \(app.element("hud.freeze.tray").debugDescription)")
        }
        print("[FIX-A2] background: \(mid.raw) → \(back.raw)")
        XCTAssertEqual(back.phase, "counting", back.raw)
        XCTAssertGreaterThan(back.left, mid.left - 1.5, "the 5 s outside did not run the tray: \(mid.raw) → \(back.raw)")
        app.element("popup.pause.primary").tap()                             // Resume
        XCTAssertNotNil(waitTray(app, timeout: 4, { $0?.held == false && ($0?.left ?? 99) < back.left - 0.2 }) ?? nil,
                        "the tray continues after Resume")
    }

    func testBulbZoomsToAFreeArrowAndBackToFit() {
        let app = level(32, ["-pc.boosters", "freeze=3,hint=3"])
        let p = waitReady(app)
        let zoom0 = p["zoom"] as? Double ?? 1
        let bulb = app.element("hud.booster.hint")
        bulb.tap()
        XCTAssertTrue(bulb.wait(for: "value == %@", "stock:2", timeout: 3))
        guard let zp = app.waitForProbe(timeout: 4, { (($0["zoom"] as? Double) ?? 0) > zoom0 * 1.2 }) else {
            return XCTFail("the camera never zoomed in: \(String(describing: app.probe()))")
        }
        XCTAssertEqual(zp["timerStarted"] as? Bool, false, "the bulb never starts the timer")
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))
        shot("hint-B+1.2-green-at-max-zoom")
        // the hinted arrow is the free arrow nearest the view's centre after the camera settled: tap free arrows until the
        // camera returns to fit (the hinted one's exit)
        var tapped: Set<Int> = []
        for _ in 0..<12 {
            guard let q = app.probe(), let a = free(q, skipping: tapped) else { break }
            tapped.insert(a.id)
            app.tap(screenX: a.x, y: a.y)
            if app.waitForProbe(timeout: 1.5, { (($0["zoom"] as? Double) ?? 9) <= zoom0 + 0.01 }) != nil { break }
        }
        XCTAssertNotNil(app.waitForProbe(timeout: 3) { (($0["zoom"] as? Double) ?? 9) <= zoom0 + 0.01 }, "back to fit after the hinted arrow left")
    }

    func testZeroStockOpensTheBoosterPopupAndBuysThree() {
        let app = level(32, ["-pc.boosters", "freeze=0,hint=0", "-pc.coins", "1500"])
        _ = waitReady(app)
        let booster = app.element("hud.booster.freeze")
        XCTAssertTrue(booster.wait(for: "value == %@", "empty"))
        booster.tap()
        let buy = app.element("popup.boosterBuy.buy")
        XCTAssertTrue(buy.waitForExistence(timeout: 5), app.debugDescription)
        shot("booster-buy-popup")
        guard let t0 = app.probe()?["t"] as? Double else { return XCTFail("no probe") }
        buy.tap()
        XCTAssertTrue(buy.waitForNonExistence(timeout: 5))
        XCTAssertTrue(booster.wait(for: "value == %@", "stock:3", timeout: 3), "Buy x3 for 900")
        XCTAssertEqual(app.probe()?["t"] as? Double, t0, "the timer did not start")
    }

    // MARK: the unlock overlay from home

    func testL7UnlockOverlayOnTheFirstPlayOnly() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "7", "-pc.go", "home", "-pc.tutorials", "skip"])
        let play = app.element("home.play")
        XCTAssertTrue(play.waitForExistence(timeout: 15), app.debugDescription)
        play.tap()
        let overlay = app.element("unlock.overlay")
        XCTAssertTrue(overlay.waitForExistence(timeout: 5), "Linked Arrows! on the first Play of L7: \(app.debugDescription)")
        RunLoop.current.run(until: Date().addingTimeInterval(1.3))
        shot("unlock-linked-L7")
        let p = app.probe()
        XCTAssertEqual(p?["timerStarted"] as? Bool, false, "the timer is frozen under the overlay")
        app.tap(screenX: 196, y: 700)
        XCTAssertTrue(overlay.waitForNonExistence(timeout: 3))
        _ = waitReady(app)
        // back, Quit, Level Failed → Try Again: the retry has no overlay
        app.element("hud.back").tap()
        let quit = app.element("popup.quitLevel.primary")
        if quit.waitForExistence(timeout: 3) { quit.tap() }
        let again = app.element("popup.levelFailed.primary")
        XCTAssertTrue(again.waitForExistence(timeout: 5), app.debugDescription)
        again.tap()
        _ = waitReady(app)
        XCTAssertFalse(overlay.waitForExistence(timeout: 2), "no overlay on the retry")
    }
}

/// Levels 1-4 (four boards, reached through the real stage transitions), L5 and L6: the arrows' tap points (screen pt at fit,
/// 393 × 852) in a solvable order, recorded from the probe by `testRecordFTUETapTable` (build/g2/ftue-taps.txt; stages 2-4
/// RE-RECORDED by FEEL after the stage-transition centring fix, build/feel/ftue-taps.txt: every stage now sits where a direct
/// load puts it, centred in the play rect).
enum FTUETaps {
    static let levels1to4: [[[Double]]] = [
        [[168.4, 452.6], [196.5, 424.5], [224.6, 452.6]],
        [[126.4, 368.4], [266.8, 508.8], [154.5, 396.5], [182.6, 424.6], [210.6, 452.6], [238.7, 452.6]],
        [[126.2, 438.4], [154.3, 382.2], [154.3, 410.3], [266.6, 438.4], [238.5, 522.6], [98.2, 494.5], [294.7, 382.2], [238.5, 494.5]],
        [[168.3, 621.0], [168.3, 368.4], [140.2, 396.5], [196.4, 564.9], [196.4, 592.9], [308.7, 480.7], [112.2, 256.1], [280.6, 480.7]],
    ]
    static let level5: [[Double]] = [[70.2, 284.2], [70.2, 564.9], [98.2, 340.3], [210.5, 340.3], [126.3, 396.5], [182.5, 284.2], [266.7, 312.2], [238.6, 284.2], [322.8, 340.3], [294.7, 508.7], [322.8, 424.5], [322.8, 621.0], [238.6, 536.8], [182.5, 564.9], [42.1, 592.9], [70.2, 368.4], [154.4, 536.8]]
    static let level6: [[Double]] = [[20.3, 391.2], [74.5, 458.9], [210.1, 323.4], [128.7, 309.9], [210.1, 337.0], [142.3, 526.7], [169.4, 553.8], [128.7, 472.5], [196.5, 580.9], [250.7, 499.6], [318.5, 445.4], [291.4, 486.1], [318.5, 337.0], [345.6, 404.7], [47.4, 364.1], [304.9, 418.3], [359.1, 391.2], [264.3, 431.8], [182.9, 431.8], [291.4, 458.9], [101.6, 486.1], [74.5, 377.6], [304.9, 404.7], [223.6, 350.5], [264.3, 513.2], [277.8, 337.0], [372.7, 404.7], [169.4, 391.2], [182.9, 526.7]]
}
