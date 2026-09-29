import XCTest

/// VERIFY V1 `MetaTests` (SPEC-architecture §9.7; SPEC.md §5.21, §5.24; SPEC-gameplay §8, §9.4, §12; CONSISTENCY X-7, X-11,
/// X-17…X-22). S1/S3/SOC2 cover the Settings toggles' persistence, the Special Offer, the username/avatar round trip, More
/// Lives, the leaderboard lists and the event pages opened by launch argument. This suite covers what the player reaches:
///  - Terms / Privacy / Support in EN and TR: real copy, the support address, the brand interpolated, and NOTHING about a
///    simulation, bots or being online (SPEC.md §5.24, owner 10:35);
///  - a coin pack through FakeStore: the honest test-store chip, the claim, the purse +1000, saved across a relaunch;
///  - lives refill one per 30:00 on the wall clock (`-pc.now` across relaunches), the pill's "mm:ss" and "full";
///  - Profile shows the player's level and stats;
///  - the leaderboard tab and an event page reached by TAPS from home, and back.
final class MetaTests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private static let banned = ["simulat", "simüle", "bot ", "online", "çevrimiçi", "yapay oyuncu"]

    private func assertHonestPages(_ app: XCUIApplication, lang: String) {
        XCTAssertTrue(app.element("page.settings").waitForExistence(timeout: 20), app.debugDescription)
        var all: [String: [String]] = [:]
        for page in ["terms", "privacy", "support"] {
            app.element("settings.\(page)").tap()
            let container = app.element("page.\(page)")
            XCTAssertTrue(container.waitForExistence(timeout: 5), "\(lang) \(page): \(app.debugDescription)")
            let texts = app.texts(in: "page.\(page)")
            all[page] = texts
            XCTAssertGreaterThanOrEqual(texts.count, 3, "\(lang) \(page) has real copy: \(texts)")
            for t in texts {
                for b in Self.banned { XCTAssertFalse(t.lowercased().contains(b), "\(lang) \(page): \"\(t)\" mentions \(b)") }
                XCTAssertFalse(t.contains("%@") || t.contains("%lld"), "\(lang) \(page): an unfilled placeholder in \"\(t)\"")
            }
            keepShot("\(lang)-page-\(page)")
            app.element("page.\(page).close").tap()
            XCTAssertTrue(container.waitForNonExistence(timeout: 5))
        }
        let terms = all["terms"] ?? [], privacy = all["privacy"] ?? [], support = all["support"] ?? []
        XCTAssertTrue(terms.contains { $0.hasPrefix("Arrow Out ") }, "\(lang): the Terms name the game through Brand.name: \(terms)")
        XCTAssertTrue(privacy.contains { $0.hasPrefix("Arrow Out ") }, "\(lang): \(privacy)")
        XCTAssertTrue((terms + support).contains { $0.contains("anycodeapps@gmail.com") }, "\(lang): the support address (SPEC.md §5.24)")
        let v = app.element("page.support.version")
        XCTAssertTrue(v.exists || support.contains { $0.hasPrefix(lang == "tr" ? "Sürüm" : "Version") }, "\(lang): the version line")
    }

    func testTermsPrivacySupportAreHonestInEnglish() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "40", "-pc.go", "settings",
                                       "-AppleLanguages", "(en)", "-AppleLocale", "en_US"])
        assertHonestPages(app, lang: "en")
    }

    func testTermsPrivacySupportAreHonestInTurkish() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "40", "-pc.go", "settings",
                                       "-AppleLanguages", "(tr)", "-AppleLocale", "tr_TR"])
        assertHonestPages(app, lang: "tr")
    }

    func testCoinPackPurchaseThroughFakeStore() {
        let app = AppUnderTest.launch(["-pc.state", AppUnderTest.state(#"{"level":40,"coins":500,"homeSeen":true}"#), "-pc.go", "home"])
        XCTAssertTrue(app.element("home.coins").wait(for: "value == %@", "500", timeout: 20), app.debugDescription)
        app.element("nav.shop").tap()
        XCTAssertTrue(app.element("screen.shop").waitForExistence(timeout: 8), app.debugDescription)
        XCTAssertTrue(app.element("shop.testStoreNote").exists, "\"Test store: nothing is charged\" (D18, X-22)")
        let pack = app.element("shop.product.coins.1000")
        let scroll = app.element("shop.scroll")
        var swipes = 0
        while !(pack.exists && pack.isHittable) && swipes < 6 { scroll.swipeUp(); swipes += 1 }
        XCTAssertTrue(pack.exists, "the 1 000-coin pack is listed: \(app.debugDescription)")
        let price = (pack.value as? String) ?? ""
        XCTAssertFalse(price.isEmpty, "the price text is the product's value")
        keepShot("shop-coins")
        pack.tap()
        let claim = app.element("claim.tap")
        XCTAssertTrue(claim.waitForExistence(timeout: 10), "the claim overlay after the FakeStore purchase: \(app.debugDescription)")
        claim.tap()
        XCTAssertTrue(app.element("shop.coins").wait(for: "value == %@", "1500", timeout: 10), app.element("shop.coins").debugDescription)
        let again = AppUnderTest.launch(["-pc.go", "home"])
        XCTAssertTrue(again.element("home.coins").wait(for: "value == %@", "1500", timeout: 20), "the purchase was saved")
    }

    func testLivesRefillOnePerThirtyMinutes() {
        // 3 lives, the refill clock anchored at 12:00:00Z
        let st = AppUnderTest.state(#"{"level":40,"coins":1000,"homeSeen":true,"lives":{"count":3,"anchor":"2026-09-25T12:00:00.000Z"}}"#)
        var app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-09-25T12:00:00Z", "-pc.go", "home"])
        var lives = app.element("home.lives")
        XCTAssertTrue(lives.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(lives.wait(for: "value MATCHES %@", #"3\|(30:00|29:[0-5][0-9])"#), "3 lives, next in 30:00: \(lives.debugDescription)")
        // +10 min: the same life 20:00 away
        app = AppUnderTest.launch(["-pc.now", "2026-09-25T12:10:00Z", "-pc.go", "home"])
        lives = app.element("home.lives")
        XCTAssertTrue(lives.wait(for: "value MATCHES %@", #"3\|(20:00|19:[0-5][0-9])"#, timeout: 20), lives.debugDescription)
        // +31 min: one life arrived, the next 29:00 away (one continuous clock)
        app = AppUnderTest.launch(["-pc.now", "2026-09-25T12:31:00Z", "-pc.go", "home"])
        lives = app.element("home.lives")
        XCTAssertTrue(lives.wait(for: "value MATCHES %@", #"4\|(29:00|28:[0-5][0-9])"#, timeout: 20), "one per 30:00: \(lives.debugDescription)")
        // +61 min: full
        app = AppUnderTest.launch(["-pc.now", "2026-09-25T13:01:00Z", "-pc.go", "home"])
        lives = app.element("home.lives")
        XCTAssertTrue(lives.wait(for: "value == %@", "full", timeout: 20), lives.debugDescription)
    }

    func testProfileShowsLevelAndStats() {
        let st = AppUnderTest.state(#"{"level":62,"coins":4214,"homeSeen":true,"stats":{"wins":61,"losses":3,"firstTryWins":58,"weeklyContestWins":0,"playSeconds":3600},"flags":{"seen":["clawIntro"]}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home"])
        let avatar = app.element("home.avatar")
        XCTAssertTrue(avatar.waitForExistence(timeout: 20), app.debugDescription)
        avatar.tap()
        XCTAssertTrue(app.element("screen.profile").waitForExistence(timeout: 6), app.debugDescription)
        XCTAssertTrue(app.element("profile.level").wait(for: "value == %@", "62"), app.element("profile.level").debugDescription)
        XCTAssertTrue(app.element("profile.stat.firstTry").wait(for: "value == %@", "58"), app.element("profile.stat.firstTry").debugDescription)
        XCTAssertFalse(app.element("profile.name").label.isEmpty, "a name is shown")
        keepShot("profile")
        app.element("profile.close").tap()
        XCTAssertTrue(app.element("screen.home").waitForExistence(timeout: 6))
    }

    func testLeaderboardAndAnEventPageByTapsFromHome() {
        let st = AppUnderTest.state(#"{"level":62,"coins":4214,"homeSeen":true,"flags":{"seen":["clawIntro"]}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-09-25T12:00:00Z", "-pc.socialCountry", "TR", "-pc.go", "home"])
        XCTAssertTrue(app.element("home.play").waitForExistence(timeout: 20), app.debugDescription)
        app.element("nav.leaderboard").tap()
        XCTAssertTrue(app.element("screen.leaderboard").waitForExistence(timeout: 6), app.debugDescription)
        XCTAssertTrue(app.element("social.ready").wait(for: "value IN %@", ["world", "country", "weekly"] as NSArray, timeout: 20),
                      "a list filled: \(app.debugDescription)")
        XCTAssertTrue(app.element("leaderboard.row.1").waitForExistence(timeout: 6) || app.element("leaderboard.me").exists, app.debugDescription)
        keepShot("leaderboard-from-home")
        app.element("nav.home").tap()
        XCTAssertTrue(app.element("home.play").waitForExistence(timeout: 6))
        let badge = app.element("home.event.streakRace")
        XCTAssertTrue(badge.waitForExistence(timeout: 6), "the Streak Race badge at L62: \(app.debugDescription)")
        badge.tap()
        XCTAssertTrue(app.element("page.streakRace").waitForExistence(timeout: 8), "the badge opens the Streak Race page: \(app.debugDescription)")
        keepShot("streak-race-from-home")
        app.element("event.streakRace.close").tap()
        XCTAssertTrue(app.element("home.play").waitForExistence(timeout: 8), "X returns home")
    }
}
