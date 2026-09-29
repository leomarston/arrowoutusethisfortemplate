import XCTest

/// VERIFY V1 `BoosterTests` (SPEC-architecture §9.7; SPEC-gameplay §6; CONSISTENCY K-1…K-16, Y-1). G2's GameG2UITests cover
/// the hourglass freeze (running and before the first tap), the bulb's camera and the 0-stock Buy ×3; this suite covers:
///  - the install stock (3 + 3) on the HUD with the §9.8 values, and a stock that survives a relaunch after use;
///  - a booster is inert while its own effect runs (K-7): a second hourglass tap during the freeze takes nothing;
///  - at 0 stock with too few coins the booster popup's Buy opens the Shop (X-23), and nothing is taken;
///  - using a booster never starts the timer (K-16).
final class BoosterTests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private func level(_ json: String) -> XCUIApplication {
        AppUnderTest.launch(["-pc.state", AppUnderTest.state(json), "-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"])
    }

    func testInstallStockAndAUsedBoosterStaysUsedAfterARelaunch() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "32", "-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"])
        guard app.waitReady() != nil else { return XCTFail("never ready: \(app.debugDescription)") }
        let freeze = app.element("hud.booster.freeze"), hint = app.element("hud.booster.hint")
        XCTAssertTrue(freeze.wait(for: "value == %@", "stock:3"), "K-2: 3 at install: \(freeze.debugDescription)")
        XCTAssertTrue(hint.wait(for: "value == %@", "stock:3"), hint.debugDescription)
        hint.tap()
        XCTAssertTrue(hint.wait(for: "value == %@", "stock:2", timeout: 3), "the bulb takes one at once")
        XCTAssertEqual(app.probe()?["timerStarted"] as? Bool, false, "K-16: a booster never starts the timer")
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))                 // the immediate save
        let again = AppUnderTest.launch(["-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"])
        guard again.waitReady() != nil else { return XCTFail("never ready after the relaunch: \(again.debugDescription)") }
        XCTAssertTrue(again.element("hud.booster.hint").wait(for: "value == %@", "stock:2"), "the used bulb stays used")
        XCTAssertTrue(again.element("hud.booster.freeze").wait(for: "value == %@", "stock:3"))
    }

    func testTheHourglassIsInertWhileItsFreezeRuns() {
        let app = level(#"{"level":32,"coins":1000,"homeSeen":true,"boosters":{"freeze":3,"hint":3}}"#)
        guard let p = app.waitReady(), let a = app.arrows(p, free: true).first else { return XCTFail("never ready: \(app.debugDescription)") }
        app.tap(screenX: a.x, y: a.y)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["timerStarted"] as? Bool) == true })
        let freeze = app.element("hud.booster.freeze")
        freeze.tap()
        XCTAssertTrue(freeze.wait(for: "value IN %@", ["stock:2", "active"] as NSArray, timeout: 3), freeze.debugDescription)
        RunLoop.current.run(until: Date().addingTimeInterval(2.0))                 // past the flight: the freeze runs
        freeze.tap()                                                                // K-7: ignored
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))
        XCTAssertFalse(app.element("popup.boosterBuy").exists, "no popup from the inert tap")
        // the stock after the freeze ends is 2, never 1
        XCTAssertTrue(freeze.wait(for: "value == %@", "stock:2", timeout: 14), "one hourglass taken: \(freeze.debugDescription)")
    }

    func testZeroStockShortOfCoinsOpensTheShopAndTakesNothing() {
        let app = level(#"{"level":32,"coins":100,"homeSeen":true,"boosters":{"freeze":0,"hint":0}}"#)
        guard app.waitReady() != nil else { return XCTFail("never ready: \(app.debugDescription)") }
        let hint = app.element("hud.booster.hint")
        XCTAssertTrue(hint.wait(for: "value == %@", "empty"), "Y-1: 0 stock reads empty: \(hint.debugDescription)")
        hint.tap()
        let buy = app.element("popup.boosterBuy.buy")
        XCTAssertTrue(buy.waitForExistence(timeout: 5), app.debugDescription)
        XCTAssertTrue(buy.wait(for: "value == %@", "3x900"), "Buy ×3 for 900 (K-6): \(buy.debugDescription)")
        buy.tap()
        XCTAssertTrue(app.element("screen.shop").waitForExistence(timeout: 5), "100 coins < 900 → the Shop (X-23): \(app.debugDescription)")
        app.element("shop.close").tap()
        XCTAssertTrue(app.element("popup.boosterBuy").wait(for: "exists == true", timeout: 5), "back on the booster popup")
        app.element("popup.boosterBuy.close").tap()
        XCTAssertTrue(app.element("popup.boosterBuy").waitForNonExistence(timeout: 5))
        XCTAssertTrue(hint.wait(for: "value == %@", "empty"), "nothing bought")
        XCTAssertTrue(app.element("hud.coins").wait(for: "value == %@", "100"), "nothing spent")
        XCTAssertEqual(app.probe()?["timerStarted"] as? Bool, false, "the timer never started")
    }
}
