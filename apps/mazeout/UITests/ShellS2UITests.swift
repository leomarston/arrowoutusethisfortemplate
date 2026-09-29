import XCTest

/// SHELL S2 UI checks on the real app (SPEC-architecture §9.7 rules: base args, anchored predicates, no sleeps for animations):
/// the fail-chain panels and their answers, the win panel's Continue, the unlock overlay's tap-anywhere (only after its cards
/// settle), the celebration's tap-to-skip, and the HUD's identifiers / values.
final class ShellS2UITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private func state(level: Int, coins: Int = 2240, step: Int = 0) -> String {
        let json = "{\"level\":\(level),\"coins\":\(coins),\"homeSeen\":true,\"events\":{\"streakStep\":\(step)}}"
        return Data(json.utf8).base64EncodedString()
    }

    func testOutOfTimeOfferAndClose() {
        let app = AppUnderTest.launch(["-pc.state", state(level: 32), "-pc.go", "level", "-pc.popup", "outOfTime"])
        let popup = app.element("popup.outOfTime")
        XCTAssertTrue(popup.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("popup.outOfTime.primary").exists, "Add Time")
        XCTAssertTrue(app.element("popup.coins").exists, "the coin group above the dim")
        let coins = app.element("popup.coins")
        XCTAssertTrue(coins.wait(for: "value == %@", "2240"), "popup.coins: \(coins.debugDescription)")
        app.element("popup.outOfTime.close").tap()
        XCTAssertTrue(popup.wait(for: "exists == false", timeout: 5))
    }

    func testContinueVariantsExposeTheirLayout() {
        for variant in ["streak", "life", "hearts"] {
            let app = AppUnderTest.launch(["-pc.state", state(level: 62, coins: 4214, step: 2), "-pc.go", "level",
                                           "-pc.popup", "continue:\(variant)"])
            let popup = app.element("popup.continue")
            XCTAssertTrue(popup.waitForExistence(timeout: 20), app.debugDescription)
            let v = app.element("popup.variant")
            XCTAssertTrue(v.wait(for: "value == %@", variant), "\(variant): \(v.debugDescription)")
            XCTAssertTrue(app.element("popup.continue.primary").exists)
            if variant == "streak" { XCTAssertTrue(app.element("streak.chips").wait(for: "value == %@", "x10")) }
            app.element("popup.continue.close").tap()
            XCTAssertTrue(popup.wait(for: "exists == false", timeout: 5))
        }
    }

    func testLevelFailedTryAgainAnswers() {
        let app = AppUnderTest.launch(["-pc.state", state(level: 32), "-pc.go", "level", "-pc.popup", "levelFailed"])
        let popup = app.element("popup.levelFailed")
        XCTAssertTrue(popup.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("streak.strip").exists, "the Streak Race strip under the panel (L32 ≥ L30)")
        app.element("popup.levelFailed.primary").tap()
        XCTAssertTrue(popup.wait(for: "exists == false", timeout: 5))
    }

    func testWinPanelContinueAndReward() {
        let app = AppUnderTest.launch(["-pc.state", state(level: 34, step: 2), "-pc.go", "level", "-pc.popup", "win:hard"])
        let popup = app.element("popup.win")
        XCTAssertTrue(popup.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("win.reward").wait(for: "value == %@", "60"), "Hard pays 60 (rules.json rewards.hard)")
        XCTAssertTrue(app.element("win.tagRibbon").exists, "the Hard Level tag ribbon")
        app.element("win.continue").tap()
        XCTAssertTrue(popup.wait(for: "exists == false", timeout: 5))
    }

    func testUnlockOverlayDismissesOnATapAfterItSettles() {
        let app = AppUnderTest.launch(["-pc.state", state(level: 35), "-pc.go", "shelllab", "-pc.lab", "unlock:pipe"])
        let overlay = app.element("unlock.overlay")
        XCTAssertTrue(overlay.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("unlock.card").waitForExistence(timeout: 5), "the card pops at S + 0.78")
        app.tap(screenX: 196, y: 700)
        XCTAssertTrue(overlay.wait(for: "exists == false", timeout: 5), "tap anywhere dismisses (content cut + dim 0.233 s)")
    }

    func testCelebrationTapSkipsToThePanel() {
        let app = AppUnderTest.launch(["-pc.state", state(level: 32, step: 1), "-pc.go", "shelllab", "-pc.lab", "celebrate:normal"])
        let skip = app.element("celebration.skip")
        XCTAssertTrue(skip.waitForExistence(timeout: 20), app.debugDescription)
        // ruling 40 (v582, motion-catalog §11.4; requirement change, A2): taps during W … W + 1.70 are ignored (was W + 0.41), so
        // the catcher arms 1.29 s later than before and the wait for it grows by that much (3 → 4.5 s); the assertion is the same
        // (it arms, and a tap then skips at once). WinLogoUITests asserts the ignored taps.
        XCTAssertTrue(skip.wait(for: "value == %@", "armed", timeout: 4.5), skip.debugDescription)
        let start = Date()
        app.tap(screenX: 196, y: 600)
        let panel = app.element("popup.win")
        XCTAssertTrue(panel.waitForExistence(timeout: 3), "the tap skips to the win panel")
        XCTAssertLessThan(Date().timeIntervalSince(start), 3.0, "well before W + 3.94 + the launch margin")
    }

    func testHUDIdentifiersAndValues() {
        let app = AppUnderTest.launch(["-pc.state", state(level: 32), "-pc.go", "shelllab", "-pc.lab", "hud:hard"])
        XCTAssertTrue(app.element("hud.timer").waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("hud.timer").wait(for: "value == %@", "210"))
        XCTAssertTrue(app.element("hud.level").wait(for: "value == %@", "Level 34"))
        XCTAssertTrue(app.element("hud.hearts").wait(for: "value == %@", "3"))
        XCTAssertTrue(app.element("hud.coins").wait(for: "value == %@", "2240"))
        XCTAssertTrue(app.element("hud.booster.freeze").wait(for: "value == %@", "stock:3"))
        XCTAssertTrue(app.element("hud.booster.hint").wait(for: "value == %@", "stock:3"))
        XCTAssertTrue(app.element("hud.back").exists)
        XCTAssertTrue(app.element("hud.pause").exists)
    }
}
