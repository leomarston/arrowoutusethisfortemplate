import XCTest

/// VERIFY V1 `FlowTests` (SPEC-architecture §9.7, §12.2 V1; SPEC.md §5.2, §5.5, §5.19; SPEC-gameplay FTUE):
///  - `testFreshInstallFTUEThroughTheL7UnlockCard` — the REAL first run: a fresh install (the runner uninstalls the app first)
///    launched with NO arguments: Loading + the notification prompt (answered "Don't Allow", as the owner did), "Levels 1-4"
///    with "Tap to move!" on stage 1 played through its four boards → the panel pays 80 → L5 → L6 (no home between) → the
///    first home flies 1000 → 1120 → Play shows L7's "Linked Arrows!" card → the level. Without the probe the taps come from
///    G2's recorded `FTUETaps` (deterministic boards and fit). Opt-in (`TEST_RUNNER_V1_FRESH=1`): a run on an installed app
///    would fail for the wrong reason (not fresh).
///  - `testLevelLoopWinPaysAndAdvances` — home → Play → the board played through real taps → the panel's +20 → Continue →
///    home shows the next level, the coins flown on and a full lives pill (the life came back with the win).
///  - `testEveryUnlockCardShowsOnItsFirstPlay` — Box L11, Pipe L21, Elevator L31, Door L33, Corner L70 (L7 above): the card's
///    text is the ruled copy, the timer is frozen under it, a tap dismisses it and the level is playable.
final class FlowTests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    // MARK: the real first run

    func testFreshInstallFTUEThroughTheL7UnlockCard() throws {
        try XCTSkipUnless(ProcessInfo.processInfo.environment["V1_FRESH"] == "1",
                          "opt-in: run right after `simctl uninstall` with TEST_RUNNER_V1_FRESH=1 (build/v1/run-fresh.sh)")
        let app = XCUIApplication()
        app.launchArguments = []
        app.launchEnvironment = [:]
        app.launch()
        XCTAssertTrue(app.element("screen.loading").waitForExistence(timeout: 10), app.debugDescription)
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let alert = springboard.alerts.firstMatch
        XCTAssertTrue(alert.waitForExistence(timeout: 12), "the notification prompt over Loading on a fresh install (SPEC.md §5.5)")
        XCTAssertTrue(app.element("screen.loading").exists, "…asked while Loading is up")
        keepShot("fresh-01-loading-notification-prompt")
        alert.buttons.element(boundBy: 0).tap()                              // [Don't Allow, Allow]: the owner declined
        XCTAssertTrue(alert.waitForNonExistence(timeout: 5))

        let hud = app.element("hud.level")
        XCTAssertTrue(hud.waitForExistence(timeout: 15), "straight into Levels 1-4: \(app.debugDescription)")
        XCTAssertTrue(hud.wait(for: "value == %@", "Levels 1-4"), hud.debugDescription)
        XCTAssertFalse(app.element("screen.home").exists, "no home before the FTUE chain ends")
        let caption = app.element("tutorial.caption")
        XCTAssertTrue(caption.waitForExistence(timeout: 6), "\"Tap to move!\" on stage 1: \(app.debugDescription)")
        XCTAssertEqual(caption.label, "Tap to move!", caption.debugDescription)
        XCTAssertTrue(app.element("tutorial.hand").exists, "the hand points at the hinted arrow")
        keepShot("fresh-02-levels1-4-tap-to-move")
        XCTAssertTrue(app.element("hud.booster.freeze").wait(for: "value == %@", "stock:3"), "3 hourglasses at install (K-2)")
        XCTAssertTrue(app.element("hud.booster.hint").wait(for: "value == %@", "stock:3"), "3 bulbs at install")

        for (k, stage) in FTUETaps.levels1to4.enumerated() {
            if k > 0 { RunLoop.current.run(until: Date().addingTimeInterval(2.2)) }   // W + the 0.7 s gap + the draw-in
            play(app, stage)
            if k == 0 { XCTAssertTrue(caption.waitForNonExistence(timeout: 3), "the hint leaves at the first tap") }
        }
        let reward = app.element("win.reward")
        XCTAssertTrue(reward.waitForExistence(timeout: 15), "the one Levels 1-4 panel: \(app.debugDescription)")
        XCTAssertTrue(reward.wait(for: "value == %@", "80"), "the session pays 80 (X-14): \(reward.debugDescription)")
        keepShot("fresh-03-levels1-4-panel-80")
        app.element("win.continue").tap()

        for (n, taps) in [(5, FTUETaps.level5), (6, FTUETaps.level6)] {
            XCTAssertTrue(hud.wait(for: "value == %@", "Level \(n)", timeout: 12), "Level \(n) follows directly: \(app.debugDescription)")
            XCTAssertFalse(app.element("screen.home").exists, "no home before the L6 win")
            RunLoop.current.run(until: Date().addingTimeInterval(1.8))                 // the intro zoom + the HUD drop
            play(app, taps)
            XCTAssertTrue(reward.waitForExistence(timeout: 15), "L\(n) panel: \(app.debugDescription)")
            XCTAssertTrue(reward.wait(for: "value == %@", "20"), "a Normal win pays 20")
            app.element("win.continue").tap()
        }

        let coins = app.element("home.coins")
        XCTAssertTrue(app.element("screen.home").waitForExistence(timeout: 12), "the first home after the L6 win: \(app.debugDescription)")
        XCTAssertTrue(coins.wait(for: "value == %@", "1120", timeout: 10), "1000 → 1120 (80 + 20 + 20 flown on the first home): \(coins.debugDescription)")
        XCTAssertTrue(app.element("home.play").wait(for: "value == %@", "7"))
        XCTAssertTrue(app.element("home.lives").wait(for: "value == %@", "full"), "wins refund their lives")
        keepShot("fresh-04-first-home-1120")

        app.element("home.play").tap()
        let overlay = app.element("unlock.overlay")
        XCTAssertTrue(overlay.waitForExistence(timeout: 8), "L7's Linked Arrows card on its first Play: \(app.debugDescription)")
        let card = app.element("unlock.card")
        XCTAssertTrue(card.waitForExistence(timeout: 4))
        XCTAssertEqual(card.label, "LINKED ARROWS move together!")
        keepShot("fresh-05-unlock-linked-L7")
        app.tap(screenX: 196, y: 700)
        XCTAssertTrue(overlay.waitForNonExistence(timeout: 4), "a tap anywhere dismisses the card")
        XCTAssertTrue(hud.wait(for: "value == %@", "Level 7", timeout: 8), hud.debugDescription)
        XCTAssertFalse(springboard.alerts.firstMatch.exists, "no second system prompt (rating comes after L34 only)")
    }

    /// Taps a recorded board: each point once, 0.45 s apart (every arrow is free when its turn comes).
    private func play(_ app: XCUIApplication, _ taps: [[Double]]) {
        for p in taps {
            app.tap(screenX: p[0], y: p[1])
            RunLoop.current.run(until: Date().addingTimeInterval(0.45))
        }
    }

    // MARK: the level loop

    func testLevelLoopWinPaysAndAdvances() {
        let st = AppUnderTest.state(#"{"level":8,"coins":1000,"homeSeen":true,"flags":{"seen":["clawIntro"]}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home", "-pc.tutorials", "skip"])
        let play = app.element("home.play")
        XCTAssertTrue(play.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(play.wait(for: "value == %@", "8"))
        XCTAssertTrue(app.element("home.level").wait(for: "value == %@", "8|normal"), app.element("home.level").debugDescription)
        play.tap()
        guard let p = app.waitReady() else { return XCTFail("L8 never became ready: \(app.debugDescription)") }
        XCTAssertEqual(p["lvl"] as? Int, 8)
        XCTAssertEqual(p["timerStarted"] as? Bool, false)
        XCTAssertTrue(app.element("home.lives").exists == false, "the level screen replaced home")
        let taps = app.playFreeArrows()
        XCTAssertGreaterThan(taps, 5)
        let reward = app.element("win.reward")
        XCTAssertTrue(reward.waitForExistence(timeout: 15), "the win panel after the celebration: \(app.debugDescription)")
        XCTAssertTrue(reward.wait(for: "value == %@", "20"))
        app.element("win.continue").tap()
        XCTAssertTrue(app.element("screen.home").waitForExistence(timeout: 10), app.debugDescription)
        XCTAssertTrue(play.wait(for: "value == %@", "9"), "home offers the next level: \(play.debugDescription)")
        XCTAssertTrue(app.element("home.coins").wait(for: "value == %@", "1020", timeout: 10), "1000 + 20 flown on home")
        XCTAssertTrue(app.element("home.lives").wait(for: "value == %@", "full"), "the win refunded the life")
        // the progress is saved: a relaunch shows the same home
        let again = AppUnderTest.launch(["-pc.go", "home"])
        XCTAssertTrue(again.element("home.play").wait(for: "value == %@", "9", timeout: 20))
        XCTAssertTrue(again.element("home.coins").wait(for: "value == %@", "1020"))
    }

    // MARK: unlock cards

    func testEveryUnlockCardShowsOnItsFirstPlay() {
        let cards: [(Int, String)] = [
            (11, "Clear required amount of arrows to break the BOX!"),
            (21, "Pass arrows through the PIPE to break it!"),
            (31, "Clear all arrows on the ELEVATOR to activate it!"),
            (33, "Collect the KEY to open the DOOR!"),
            (70, "Arrows turn when they hit the CORNER!"),
        ]
        for (n, text) in cards {
            // a returning player (the Claw Challenge's first-open page already seen: G2's home queue would open it first)
            let st = AppUnderTest.state(#"{"level":\#(n),"coins":1000,"homeSeen":true,"flags":{"seen":["clawIntro"]}}"#)
            let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home", "-pc.tutorials", "skip"])
            let play = app.element("home.play")
            XCTAssertTrue(play.waitForExistence(timeout: 20), "L\(n): \(app.debugDescription)")
            play.tap()
            let overlay = app.element("unlock.overlay")
            XCTAssertTrue(overlay.waitForExistence(timeout: 8), "L\(n): the card on the first Play: \(app.debugDescription)")
            let card = app.element("unlock.card")
            XCTAssertTrue(card.waitForExistence(timeout: 4), "L\(n)")
            XCTAssertEqual(card.label, text, "L\(n) card copy")
            XCTAssertEqual(app.probe()?["timerStarted"] as? Bool, false, "L\(n): the timer is frozen under the card")
            keepShot("unlock-L\(n)")
            app.tap(screenX: 196, y: 700)
            XCTAssertTrue(overlay.waitForNonExistence(timeout: 4), "L\(n): a tap dismisses the card")
            guard let p = app.waitReady() else { return XCTFail("L\(n) never became ready after the card") }
            XCTAssertEqual(p["lvl"] as? Int, n)
        }
    }
}
