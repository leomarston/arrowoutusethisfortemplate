import XCTest

/// VERIFY V1 `FailFlowTests` (SPEC-architecture §9.7; SPEC-gameplay §5, §7, §8; CONSISTENCY X-1…X-13, T-31; SPEC.md §5.21).
/// G1's GameFlowTests already decline the whole time-out chain and the hearts-out chain; this suite covers the other answers:
///  - Add Time pays 900 and the level goes on with +30 s; Add Lives pays 900 and refills the hearts;
///  - short of coins, the offer's button opens the Shop over it and the offer is still there on return (X-23);
///  - with a streak (L ≥ 30, multiplier above x1) the chain has the streak/token step between the offer and "a life" (X-1/X-5);
///  - X on Level Failed BEFORE the first home retries the level instead of going home (ruling 21, T-31);
///  - Quit costs the life: home shows 4 lives and the 30:00 refill clock (X-7/X-8);
///  - Play with 0 lives opens More Lives (X-12).
final class FailFlowTests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private func level(_ json: String, _ extra: [String] = []) -> XCUIApplication {
        AppUnderTest.launch(["-pc.state", AppUnderTest.state(json), "-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"] + extra)
    }

    private func ready(_ app: XCUIApplication) -> [String: Any] {
        guard let p = app.waitReady() else {
            XCTFail("never ready: \(String(describing: app.probe()))\n\(app.debugDescription)")
            return [:]
        }
        return p
    }

    private func firstTap(_ app: XCUIApplication, _ p: [String: Any]) {
        guard let a = app.arrows(p, free: true).first else { return XCTFail("no free arrow") }
        app.tap(screenX: a.x, y: a.y)
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["timerStarted"] as? Bool) == true }, "the first tap starts the timer")
    }

    func testAddTimePays900AndThePlayGoesOn() {
        let app = level(#"{"level":32,"coins":2000,"homeSeen":true}"#, ["-pc.timer", "3"])
        firstTap(app, ready(app))
        let offer = app.element("popup.outOfTime")
        XCTAssertTrue(offer.waitForExistence(timeout: 12), app.debugDescription)
        XCTAssertTrue(app.element("popup.coins").wait(for: "value == %@", "2000"), "the coin group shows the purse")
        keepShot("fail-out-of-time")
        app.element("popup.outOfTime.primary").tap()                               // Add Time [coin] 900
        XCTAssertTrue(offer.waitForNonExistence(timeout: 5), app.debugDescription)
        guard let p = app.waitForProbe(timeout: 5, { ($0["phase"] as? String) == "playing" }) else {
            return XCTFail("back to playing: \(String(describing: app.probe()))")
        }
        let t = p["t"] as? Double ?? 0
        XCTAssertGreaterThan(t, 25, "+30 s (X-3)")
        XCTAssertLessThanOrEqual(t, 30.01)
        XCTAssertTrue(app.element("hud.coins").wait(for: "value == %@", "1100"), "2000 − 900: \(app.element("hud.coins").debugDescription)")
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { (($0["t"] as? Double) ?? t) < t - 0.5 }, "the timer runs again")
    }

    func testAddLivesRefillsTheHearts() {
        let app = level(#"{"level":32,"coins":1000,"homeSeen":true}"#, ["-pc.hearts", "1"])
        let p = ready(app)
        guard let a = app.arrows(p, free: false).first else { return XCTFail("no blocked arrow on L32") }
        app.tap(screenX: a.x, y: a.y)                                               // a bump takes the last heart
        let offer = app.element("popup.outOfTime")
        XCTAssertTrue(offer.waitForExistence(timeout: 10), app.debugDescription)
        XCTAssertTrue(app.element("popup.variant").wait(for: "value == %@", "hearts"), "Out of Lives! (X-1)")
        app.element("popup.outOfTime.primary").tap()                               // Add Lives [coin] 900
        XCTAssertTrue(offer.waitForNonExistence(timeout: 5))
        XCTAssertNotNil(app.waitForProbe(timeout: 5) { ($0["phase"] as? String) == "playing" && ($0["hearts"] as? Int) == 3 },
                        "3 hearts and playing: \(String(describing: app.probe()))")
        XCTAssertTrue(app.element("hud.hearts").wait(for: "value == %@", "3"))
        XCTAssertTrue(app.element("hud.coins").wait(for: "value == %@", "100"))
    }

    func testShortOfCoinsTheOfferOpensTheShopAndStays() {
        let app = level(#"{"level":32,"coins":100,"homeSeen":true}"#, ["-pc.timer", "3"])
        firstTap(app, ready(app))
        let offer = app.element("popup.outOfTime")
        XCTAssertTrue(offer.waitForExistence(timeout: 12), app.debugDescription)
        app.element("popup.outOfTime.primary").tap()
        XCTAssertTrue(app.element("screen.shop").waitForExistence(timeout: 6), "not enough coins → the Shop over the offer (X-23): \(app.debugDescription)")
        XCTAssertTrue(app.element("shop.testStoreNote").exists, "the honest test-store chip")
        app.element("shop.close").tap()
        XCTAssertTrue(app.element("screen.shop").waitForNonExistence(timeout: 5))
        XCTAssertTrue(offer.exists, "the offer is still up")
        XCTAssertEqual(app.probe()?["phase"] as? String, "offer")
        XCTAssertTrue(app.element("hud.coins").wait(for: "value == %@", "100"), "nothing was spent")
    }

    func testStreakChainOrderThenLevelFailedCostsALife() {
        // L32 ≥ the Streak Race unlock (L30) with a multiplier above x1: the streak / token step comes before "a life"
        let app = level(#"{"level":32,"coins":2000,"homeSeen":true,"events":{"streakStep":2}}"#, ["-pc.timer", "3"])
        firstTap(app, ready(app))
        XCTAssertTrue(app.element("popup.outOfTime").waitForExistence(timeout: 12), app.debugDescription)
        app.element("popup.outOfTime.close").tap()
        let cont = app.element("popup.continue")
        let variant = app.element("popup.variant")
        XCTAssertTrue(cont.waitForExistence(timeout: 5), app.debugDescription)
        XCTAssertTrue(variant.wait(for: "value IN %@", ["streak", "token"] as NSArray), "step B: \(variant.debugDescription)")
        keepShot("fail-continue-streak")
        app.element("popup.continue.close").tap()
        XCTAssertTrue(variant.wait(for: "value == %@", "life", timeout: 5), "step C: You will lose a life! \(variant.debugDescription)")
        app.element("popup.continue.close").tap()
        let failed = app.element("popup.levelFailed")
        XCTAssertTrue(failed.waitForExistence(timeout: 5), app.debugDescription)
        app.element("popup.levelFailed.close").tap()
        let lives = app.element("home.lives")
        XCTAssertTrue(lives.waitForExistence(timeout: 10), "X on Level Failed after the first home → home: \(app.debugDescription)")
        XCTAssertTrue(lives.wait(for: "value MATCHES %@", #"4\|(30:00|29:[0-5][0-9])"#), "one life lost, the 30:00 clock: \(lives.debugDescription)")
    }

    func testXOnLevelFailedBeforeTheFirstHomeRetries() {
        let app = level(#"{"level":5,"coins":1080,"homeSeen":false}"#, ["-pc.timer", "3"])
        let p = ready(app)
        XCTAssertEqual(p["lvl"] as? Int, 5)
        firstTap(app, p)
        XCTAssertTrue(app.element("popup.outOfTime").waitForExistence(timeout: 12), app.debugDescription)
        app.element("popup.outOfTime.close").tap()
        let cont = app.element("popup.continue")
        if cont.waitForExistence(timeout: 4) { app.element("popup.continue.close").tap() }   // "a life" (no streak before L30)
        XCTAssertTrue(app.element("popup.levelFailed").waitForExistence(timeout: 6), app.debugDescription)
        app.element("popup.levelFailed.close").tap()
        guard let again = app.waitReady() else { return XCTFail("X before the first home retries the level: \(app.debugDescription)") }
        XCTAssertEqual(again["lvl"] as? Int, 5, "the same level again (T-31)")
        XCTAssertFalse(app.element("screen.home").exists, "no home before the FTUE chain ends")
    }

    func testQuitCostsTheLifeWithTheThirtyMinuteClock() {
        let app = level(#"{"level":40,"coins":1000,"homeSeen":true}"#)
        firstTap(app, ready(app))
        app.element("hud.back").tap()
        XCTAssertTrue(app.element("popup.quitLevel").waitForExistence(timeout: 5), app.debugDescription)
        app.element("popup.quitLevel.primary").tap()                                // Quit
        XCTAssertTrue(app.element("popup.levelFailed").waitForExistence(timeout: 6), "Quit → Level Failed: \(app.debugDescription)")
        app.element("popup.levelFailed.close").tap()
        let lives = app.element("home.lives")
        XCTAssertTrue(lives.waitForExistence(timeout: 10), app.debugDescription)
        XCTAssertTrue(lives.wait(for: "value MATCHES %@", #"4\|(30:00|29:[0-5][0-9])"#), "4 lives, next in 30:00: \(lives.debugDescription)")
        // the loss is saved: a relaunch keeps 4 lives
        let again = AppUnderTest.launch(["-pc.go", "home"])
        XCTAssertTrue(again.element("home.lives").wait(for: "value BEGINSWITH %@", "4|", timeout: 20))
    }

    func testPlayWithNoLivesOpensMoreLives() {
        let st = #"{"level":40,"coins":1000,"homeSeen":true,"lives":{"count":0,"anchor":"2026-09-25T11:50:00.000Z"}}"#
        let app = AppUnderTest.launch(["-pc.state", AppUnderTest.state(st), "-pc.now", "2026-09-25T12:00:00Z", "-pc.go", "home"])
        let lives = app.element("home.lives")
        XCTAssertTrue(lives.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(lives.wait(for: "value MATCHES %@", #"0\|(20:00|19:[0-5][0-9])"#), "0 lives, the next in 20:00: \(lives.debugDescription)")
        app.element("home.play").tap()
        let popup = app.element("popup.noLives")
        XCTAssertTrue(popup.waitForExistence(timeout: 5), "0 lives at Play → More Lives (X-12): \(app.debugDescription)")
        XCTAssertTrue(app.element("popup.noLives.count").wait(for: "label == %@", "0"))
        keepShot("fail-more-lives")
        XCTAssertNil(app.probe(), "no level started")
    }
}
