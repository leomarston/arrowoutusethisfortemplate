import XCTest

/// META (OWNER 2026-09-29 19:33, the Meta SDK in 1.0): the App Tracking Transparency prompt's MOMENT, driven through the app.
/// `-pc.att 1` lets a UI test reach the prompt without live mode (nothing is sent to Meta in a DEBUG run). The ATT alert is
/// one-shot per install (memory att-prompt-is-one-shot-too): B ANSWERS it when it shows ("Ask App Not to Track") and never
/// asserts it; A resets iOS's answer first (`resetAuthorizationStatus(for: .userTracking)`, RFIX / VERIFY F7) so its "no alert
/// during the FTUE" cannot pass vacuously, and asserts the alert DOES come at the first home as its control.
/// What is asserted is what must hold whether or not iOS shows it:
///  - A: during the FTUE chain (a level before the first home) no system alert appears, even with -pc.att 1;
///  - B: at the first home after the FTUE the visit completes (the +120 coins land) and PLAY IS NEVER BLOCKED: after the
///       prompt is answered (or when iOS shows none) Play opens L7 with its unlock card.
/// The WHEN logic itself (after the FTUE, once, never with the rating sheet, never outside live / -pc.att) is unit-tested in
/// MetaEventsTests.testTheTrackingPromptComesOnceAfterTheFTUEAndNeverWithTheRatingSheet.
final class TrackingPromptUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private var springboard: XCUIApplication { XCUIApplication(bundleIdentifier: "com.apple.springboard") }

    /// Answers the ATT alert if it is up within `timeout`; true when one was answered.
    @discardableResult
    private func answerTrackingPromptIfShown(timeout: TimeInterval) -> Bool {
        let alert = springboard.alerts.firstMatch
        guard alert.waitForExistence(timeout: timeout) else { return false }
        keepShot("att-prompt")
        let decline = alert.buttons["Ask App Not to Track"]
        if decline.exists { decline.tap() } else { alert.buttons.element(boundBy: 0).tap() }
        XCTAssertTrue(alert.waitForNonExistence(timeout: 5), "the alert goes away when answered")
        return true
    }

    func testANoTrackingPromptDuringTheFTUEChain() {
        // RFIX 2026-09-29 (VERIFY F7): this test passed VACUOUSLY once the simulator had answered ATT (iOS then never shows the
        // alert, so "no alert during the FTUE" proved nothing). Now iOS's answer is reset first, so the prompt IS possible
        // (-pc.att 1, iOS notDetermined) and only the FTUE rule keeps it away; the positive control at the end shows the
        // same install DOES get the alert at the first home after the FTUE (else the absence above would be meaningless).
        XCUIApplication().resetAuthorizationStatus(for: .userTracking)
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "5", "-pc.go", "level", "-pc.att", "1"])
        let hud = app.element("hud.level")
        XCTAssertTrue(hud.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(hud.wait(for: "value == %@", "Level 5"), hud.debugDescription)
        XCTAssertFalse(app.element("screen.home").exists, "the FTUE chain: no home yet")
        // the level's intro and a few seconds of play time: nothing from iOS may cover the tutorial levels
        XCTAssertFalse(springboard.alerts.firstMatch.waitForExistence(timeout: 6),
                       "no system alert during the FTUE chain (the ATT prompt waits for the first home): \(springboard.debugDescription)")
        // positive control: the same reset install at the first home after the FTUE (the L6 win's payout) DOES get the alert
        let st = AppUnderTest.state(#"{"level":7,"coins":1120,"homeSeen":false,"pendingCoinFly":120}"#)
        let home = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home", "-pc.att", "1"])
        XCTAssertTrue(home.element("screen.home").waitForExistence(timeout: 20), home.debugDescription)
        let alert = springboard.alerts.firstMatch
        XCTAssertTrue(alert.waitForExistence(timeout: 15),
                      "control: with iOS reset, the ATT alert appears at the first home after the FTUE: \(home.debugDescription)")
        XCTAssertTrue(alert.buttons["Ask App Not to Track"].exists, "it is the ATT alert: \(alert.debugDescription)")
        alert.buttons["Ask App Not to Track"].tap()
        XCTAssertTrue(alert.waitForNonExistence(timeout: 5), "answered")
    }

    func testBTheFirstHomeAsksAtMostOnceAndNeverBlocksPlay() {
        // the REAL first home after the L6 win (as ShellS3UITests.testFirstHomePaysOut120): 1000 → 1120 flies on
        let st = AppUnderTest.state(#"{"level":7,"coins":1120,"homeSeen":false,"pendingCoinFly":120}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home", "-pc.att", "1"])
        XCTAssertTrue(app.element("screen.home").waitForExistence(timeout: 20), app.debugDescription)
        let coins = app.element("home.coins")
        // the visit's calm part first: the payout lands (the prompt comes only after it)
        XCTAssertTrue(coins.wait(for: "value == %@", "1120", timeout: 12), "the +120 lands first: \(coins.debugDescription)")
        let answered = answerTrackingPromptIfShown(timeout: 8)
        print("[META] ATT prompt at the first home: \(answered ? "shown and answered" : "not shown (already answered in this simulator)")")
        // never blocks play: Play opens L7 (its Linked Arrows card), and no second alert follows
        let play = app.element("home.play")
        XCTAssertTrue(play.wait(for: "value == %@", "7"), play.debugDescription)
        play.tap()
        XCTAssertTrue(app.element("unlock.overlay").waitForExistence(timeout: 10), "Play works after the prompt: \(app.debugDescription)")
        XCTAssertFalse(springboard.alerts.firstMatch.exists, "one system prompt at most")
        // back home (the next visit) never asks again. RFIX 2026-09-29: the guard is iOS's kept answer, not the saved
        // 'attAsked' marker (no longer written or read; the state below still carries one from older builds, and it changes
        // nothing): the assertion is the same, and it holds because the alert above was answered (or iOS had an answer).
        app.terminate()
        let again = AppUnderTest.launch(["-pc.state", AppUnderTest.state(#"{"level":8,"coins":1120,"homeSeen":true,"flags":{"seen":["attAsked","metaFTUE"]}}"#),
                                         "-pc.go", "home", "-pc.att", "1"])
        XCTAssertTrue(again.element("screen.home").waitForExistence(timeout: 20), again.debugDescription)
        XCTAssertFalse(springboard.alerts.firstMatch.waitForExistence(timeout: 6), "asked once per install: a later visit never asks")
    }

    // MARK: VERIFY (2026-09-29): the real first run, end to end

    /// Opt-in (TEST_RUNNER_META_FRESH=1), run ONLY right after `simctl uninstall` + `simctl privacy … reset all` of the app
    /// (build/p/VERIFY/fresh.sh): iOS has never been asked, so here — and only here — the ATT alert's appearance IS the
    /// assertion. The real first run with no state or target argument, only `-pc.att 1` (a DEBUG run never talks to Meta;
    /// the flag lets it reach the prompt, as a live Release run would): the notification prompt over Loading is declined as in
    /// FlowTests' fresh run; through Levels 1-4, 5 and 6 NO other system alert appears (checked at every level start and win
    /// panel); at the first home, after 1000 → 1120 lands, the ATT alert appears and is answered Allow; Play then opens L7's
    /// card and no further alert follows.
    func testCFreshInstallAsksForTrackingOnlyAfterTheFTUE() throws {
        try XCTSkipUnless(ProcessInfo.processInfo.environment["META_FRESH"] == "1",
                          "opt-in: run right after `simctl uninstall` + a privacy reset with TEST_RUNNER_META_FRESH=1 (build/p/VERIFY/fresh.sh)")
        let app = XCUIApplication()
        app.launchArguments = ["-pc.att", "1"]
        app.launchEnvironment = [:]
        app.launch()
        XCTAssertTrue(app.element("screen.loading").waitForExistence(timeout: 10), app.debugDescription)
        let alert = springboard.alerts.firstMatch
        XCTAssertTrue(alert.waitForExistence(timeout: 12), "the notification prompt over Loading on a fresh install (SPEC.md §5.5)")
        XCTAssertFalse(alert.buttons["Ask App Not to Track"].exists, "the first alert is the notification prompt, not ATT: \(alert.debugDescription)")
        alert.buttons.element(boundBy: 0).tap()                                  // [Don't Allow, Allow]: declined, as the owner did
        XCTAssertTrue(alert.waitForNonExistence(timeout: 5))

        func noAlert(_ when: String) {
            XCTAssertEqual(springboard.alerts.count, 0, "no system alert during the FTUE chain (\(when)): \(springboard.debugDescription)")
        }
        func play(_ taps: [[Double]]) {
            for p in taps {
                app.tap(screenX: p[0], y: p[1])
                RunLoop.current.run(until: Date().addingTimeInterval(0.45))
            }
        }
        let hud = app.element("hud.level")
        XCTAssertTrue(hud.waitForExistence(timeout: 15), "straight into Levels 1-4: \(app.debugDescription)")
        XCTAssertTrue(hud.wait(for: "value == %@", "Levels 1-4"), hud.debugDescription)
        noAlert("Levels 1-4 start")
        for (k, stage) in FTUETaps.levels1to4.enumerated() {
            if k > 0 { RunLoop.current.run(until: Date().addingTimeInterval(2.2)) }
            play(stage)
        }
        let reward = app.element("win.reward")
        XCTAssertTrue(reward.waitForExistence(timeout: 15), "the one Levels 1-4 panel: \(app.debugDescription)")
        noAlert("Levels 1-4 win panel")
        app.element("win.continue").tap()
        for (n, taps) in [(5, FTUETaps.level5), (6, FTUETaps.level6)] {
            XCTAssertTrue(hud.wait(for: "value == %@", "Level \(n)", timeout: 12), "Level \(n) follows directly: \(app.debugDescription)")
            XCTAssertFalse(app.element("screen.home").exists, "no home before the L6 win")
            noAlert("Level \(n) start")
            RunLoop.current.run(until: Date().addingTimeInterval(1.8))
            play(taps)
            XCTAssertTrue(reward.waitForExistence(timeout: 15), "L\(n) panel: \(app.debugDescription)")
            noAlert("Level \(n) win panel")
            app.element("win.continue").tap()
        }

        let coins = app.element("home.coins")
        XCTAssertTrue(app.element("screen.home").waitForExistence(timeout: 12), "the first home after the L6 win: \(app.debugDescription)")
        XCTAssertTrue(coins.wait(for: "value == %@", "1120", timeout: 10), "1000 → 1120 lands before the prompt: \(coins.debugDescription)")
        XCTAssertTrue(alert.waitForExistence(timeout: 12), "the ATT alert at the end of the first calm home visit: \(app.debugDescription)")
        let allow = alert.buttons["Allow"]
        XCTAssertTrue(alert.buttons["Ask App Not to Track"].exists && allow.exists, "it is the App Tracking Transparency alert: \(alert.debugDescription)")
        XCTAssertEqual(coins.value as? String, "1120", "over the landed payout")
        keepShot("verify-att-first-home")
        allow.tap()
        XCTAssertTrue(alert.waitForNonExistence(timeout: 5), "answered")

        let play = app.element("home.play")
        XCTAssertTrue(play.wait(for: "value == %@", "7"), play.debugDescription)
        play.tap()
        XCTAssertTrue(app.element("unlock.overlay").waitForExistence(timeout: 10), "Play works after the answer: \(app.debugDescription)")
        keepShot("verify-att-then-L7-card")
        XCTAssertEqual(springboard.alerts.count, 0, "one ATT prompt, no other alert")
    }
}
