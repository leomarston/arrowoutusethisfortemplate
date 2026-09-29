import XCTest

/// SHELL S3 UI checks on the real app (SPEC-architecture §9.7 rules: base args incl. `-pc.fakeStore 1`, anchored predicates, no
/// sleeps for animations): the Shop's FakeStore purchase (the honest note, the claim overlays, the header pill counting up, the
/// once-only Special Offer), the username + avatar round trip persisting across a relaunch, More Lives (Refill, no ad offer), the
/// booster pack, the home's Claw bar / badges / payout, and the nav tabs.
final class ShellS3UITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private func state(_ json: String) -> String { Data(json.utf8).base64EncodedString() }

    func testShopPurchaseThroughFakeStore() {
        let app = AppUnderTest.launch(["-pc.state", state(#"{"level":40,"coins":2000,"homeSeen":true}"#), "-pc.go", "shop"])
        XCTAssertTrue(app.element("screen.shop").waitForExistence(timeout: 20), app.debugDescription)
        // FIX-B: waited for, not read at the instant screen.shop appeared — the note is drawn on the Shop's first frame, but
        // under load its accessibility element can land a snapshot after the screen's container (r-shop/i-shop 13:06: 5 of
        // 6 reads missed it while the recording shows it on screen); the assertion (the note is on the Shop) is unchanged
        XCTAssertTrue(app.element("shop.testStoreNote").waitForExistence(timeout: 5), "Test store: nothing is charged")
        let coins = app.element("shop.coins")
        XCTAssertTrue(coins.wait(for: "value == %@", "2000"), coins.debugDescription)
        let offer = app.element("shop.product.offer.special")
        XCTAssertTrue(offer.exists)
        offer.tap()
        // the claim overlays: coins, then the boosters, then ∞ 1h (SPEC-ui §2.12.4)
        for i in 0..<3 {
            let claim = app.element("claim.tap")
            XCTAssertTrue(claim.waitForExistence(timeout: 10), "claim \(i): \(app.debugDescription)")
            claim.tap()
            XCTAssertTrue(app.element("popup.claim").wait(for: "exists == false", timeout: 5) || i < 2)
        }
        XCTAssertTrue(coins.wait(for: "value == %@", "3000", timeout: 10), "the pill counts up to 3000: \(coins.debugDescription)")
        XCTAssertTrue(offer.wait(for: "exists == false", timeout: 5), "the once-only Special Offer disappears")
        // the purchase survived a relaunch (saved at once)
        let again = AppUnderTest.launch(["-pc.go", "shop"])
        XCTAssertTrue(again.element("shop.coins").wait(for: "value == %@", "3000", timeout: 20))
        XCTAssertFalse(again.element("shop.product.offer.special").exists)
    }

    func testUsernameAndAvatarRoundTripPersists() {
        let app = AppUnderTest.launch(["-pc.state", state(#"{"level":62,"coins":4214,"homeSeen":true}"#), "-pc.go", "profile",
                                       "-pc.askName", "1"])
        let field = app.element("username.field")
        XCTAssertTrue(field.waitForExistence(timeout: 20), app.debugDescription)
        field.tap()
        field.typeText("ab")
        app.element("username.continue").tap()
        XCTAssertTrue(app.element("toast").waitForExistence(timeout: 5), "a 2-character name is refused with a toast")
        field.typeText("Hsheh")
        app.element("username.continue").tap()
        XCTAssertTrue(app.element("popup.username").wait(for: "exists == false", timeout: 5))
        XCTAssertTrue(app.element("profile.name").wait(for: "label == %@", "abHsheh"), app.element("profile.name").debugDescription)
        app.element("profile.edit").tap()
        XCTAssertTrue(app.element("popup.editProfile").waitForExistence(timeout: 5))
        app.element("editProfile.avatar.5").tap()
        XCTAssertTrue(app.element("editProfile.avatar.5").wait(for: "value == %@", "selected"))
        app.element("editProfile.save").tap()
        XCTAssertTrue(app.element("popup.editProfile").wait(for: "exists == false", timeout: 5))
        XCTAssertTrue(app.element("profile.avatar").wait(for: "value == %@", "avatar:5"))
        // X on Edit Profile saves nothing
        app.element("profile.edit").tap()
        app.element("editProfile.avatar.2").tap()
        app.element("popup.editProfile.close").tap()
        XCTAssertTrue(app.element("profile.avatar").wait(for: "value == %@", "avatar:5"))
        // relaunch: the save file keeps both
        let again = AppUnderTest.launch(["-pc.go", "profile"])
        XCTAssertTrue(again.element("profile.name").wait(for: "label == %@", "abHsheh", timeout: 20))
        XCTAssertTrue(again.element("profile.avatar").wait(for: "value == %@", "avatar:5"))
        XCTAssertFalse(again.element("popup.username").exists, "a named player is not asked again")
    }

    /// A1 (owner item 9, ruling 37(d), release-plan §4.2 step 5 — a REQUIREMENT change, not a weakening): was
    /// `testMoreLivesRefillAndOfflineAd`, which tapped the rewarded-video "+1 Live" button and expected the offline slot's toast.
    /// The button is removed, so the test now asserts it does NOT exist (and no ad element is anywhere on screen); every refill
    /// assertion is kept (lives 3 → full, coins 1000 → 100).
    func testMoreLivesRefill() {
        let st = state(#"{"level":40,"coins":1000,"homeSeen":true,"lives":{"count":3,"anchor":"2026-09-25T11:57:04.000Z"}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-09-25T12:00:00Z", "-pc.go", "home", "-pc.popup", "noLives"])
        let popup = app.element("popup.noLives")
        XCTAssertTrue(popup.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("popup.noLives.count").wait(for: "label == %@", "3"))
        XCTAssertTrue(app.element("popup.noLives.refill").exists, "Refill is the offer")
        XCTAssertFalse(app.element("popup.noLives.ad").exists, "no rewarded-ad offer (owner item 9): \(app.debugDescription)")
        let adLike = app.descendants(matching: .any).matching(NSPredicate(format: "identifier ENDSWITH '.ad' OR identifier CONTAINS '.ad.' OR label ==[c] 'Live' OR label ==[c] '+1 Live'"))
        XCTAssertEqual(adLike.count, 0, "no ad button or '+1 Live' label on More Lives: \(app.debugDescription)")
        app.element("popup.noLives.refill").tap()
        XCTAssertTrue(popup.wait(for: "exists == false", timeout: 5))
        XCTAssertTrue(app.element("home.lives").wait(for: "value == %@", "full"), app.element("home.lives").debugDescription)
        XCTAssertTrue(app.element("home.coins").wait(for: "value == %@", "100"))
    }

    func testBoosterPackBuy() {
        let st = state(#"{"level":40,"coins":1000,"homeSeen":true,"boosters":{"freeze":0,"hint":0}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home", "-pc.popup", "boosterBuy:hint"])
        let popup = app.element("popup.boosterBuy")
        XCTAssertTrue(popup.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("popup.boosterBuy.buy").wait(for: "value == %@", "3x900"))
        app.element("popup.boosterBuy.buy").tap()
        XCTAssertTrue(popup.wait(for: "exists == false", timeout: 5), app.debugDescription)
        XCTAssertTrue(app.element("home.coins").wait(for: "value == %@", "100"))
        // short of coins now: the Shop opens over the popup, and the popup stays
        let second = AppUnderTest.launch(["-pc.go", "home", "-pc.popup", "boosterBuy:freeze"])
        XCTAssertTrue(second.element("popup.boosterBuy").waitForExistence(timeout: 20))
        second.element("popup.boosterBuy.buy").tap()
        XCTAssertTrue(second.element("screen.shop").waitForExistence(timeout: 5), "not enough coins → the Shop")
        second.element("shop.close").tap()
        XCTAssertTrue(second.element("popup.boosterBuy").wait(for: "exists == true", timeout: 5), "back on the popup")
    }

    func testHomeEventLayerAndNav() {
        let st = state(#"{"level":62,"coins":4194,"homeSeen":true,"events":{"streakStep":4,"claw":{"week":21,"points":122,"step":6}}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-09-25T01:17:40Z", "-pc.go", "home"])
        let claw = app.element("home.claw")
        XCTAssertTrue(claw.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(claw.wait(for: "value == %@", "122/500 x100"), claw.debugDescription)
        XCTAssertTrue(app.element("home.claw.reward").wait(for: "value == %@", "coins:300"))
        XCTAssertTrue(app.element("home.claw.timer").wait(for: "value == %@", "3d 5h"))
        XCTAssertTrue(app.element("home.event.streakRace").wait(for: "value == %@", "timer:5h 42m"),
                      app.element("home.event.streakRace").debugDescription)
        XCTAssertTrue(app.element("home.event.rocketRace").wait(for: "value == %@", "join"))
        XCTAssertTrue(app.element("home.event.skyJump").wait(for: "value == %@", "join"))
        app.element("nav.shop").tap()
        XCTAssertTrue(app.element("screen.shop").waitForExistence(timeout: 5))
        app.element("nav.leaderboard").tap()
        XCTAssertTrue(app.element("screen.leaderboard").waitForExistence(timeout: 5))
        app.element("nav.home").tap()
        XCTAssertTrue(app.element("home.claw").waitForExistence(timeout: 5))
        app.element("home.avatar").tap()
        XCTAssertTrue(app.element("screen.profile").waitForExistence(timeout: 5))
        app.element("profile.close").tap()
        XCTAssertTrue(app.element("home.claw").waitForExistence(timeout: 5))
    }

    func testFirstHomePaysOut120() {
        let st = state(#"{"level":7,"coins":1120,"homeSeen":false,"pendingCoinFly":120}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home"])
        let coins = app.element("home.coins")
        XCTAssertTrue(coins.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertEqual(coins.value as? String, "1000", "the banked 120 is hidden until it flies")
        XCTAssertTrue(coins.wait(for: "value == %@", "1120", timeout: 10), "1000 → 1120 after the five coins land: \(coins.debugDescription)")
        // relaunch: the fly was taken out of the save (it pays once)
        let again = AppUnderTest.launch(["-pc.go", "home"])
        XCTAssertTrue(again.element("home.coins").wait(for: "value == %@", "1120", timeout: 20))
    }
}
