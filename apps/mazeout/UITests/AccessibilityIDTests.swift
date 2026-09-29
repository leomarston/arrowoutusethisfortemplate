import XCTest

/// VERIFY V1 (SPEC-architecture §9.8 + SPEC-ui §6 additions; CONSISTENCY §18 Y-1…Y-5). The identifiers VERIFY and the
/// capture tools rely on exist on their screens with the documented values. Each screen collects every missing id before it
/// fails, so one run lists them all (the report routes each to its owner).
final class AccessibilityIDTests: XCTestCase {
    override func setUp() { continueAfterFailure = true }

    private func require(_ app: XCUIApplication, _ ids: [String], on screen: String, timeout: TimeInterval = 20,
                         file: StaticString = #filePath, line: UInt = #line) {
        guard let first = ids.first else { return }
        _ = app.element(first).waitForExistence(timeout: timeout)
        let missing = ids.filter { !app.element($0).waitForExistence(timeout: 3) }
        if !missing.isEmpty {
            let a = XCTAttachment(string: app.debugDescription)
            a.name = "hierarchy-\(screen)"
            a.lifetime = .keepAlways
            add(a)
        }
        XCTAssertEqual(missing, [], "\(screen): §9.8 ids missing", file: file, line: line)
    }

    private func value(_ app: XCUIApplication, _ id: String) -> String { (app.element(id).value as? String) ?? "<nil>" }

    func testHomeIdentifiers() {
        let st = AppUnderTest.state(#"{"level":62,"coins":4214,"homeSeen":true,"events":{"streakStep":2},"flags":{"seen":["clawIntro"]}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-09-25T12:00:00Z", "-pc.go", "home"])
        require(app, ["home.play", "home.level", "home.coins", "home.coins.plus", "home.lives", "home.settings", "home.avatar",
                      "home.claw", "nav.shop", "nav.home", "nav.leaderboard", "screen.home"], on: "home")
        XCTAssertEqual(value(app, "home.play"), "62")
        XCTAssertEqual(value(app, "home.coins"), "4214")
        XCTAssertEqual(value(app, "home.lives"), "full")
        XCTAssertEqual(value(app, "nav.home"), "selected")
        XCTAssertTrue(app.element("home.claw").wait(for: "value MATCHES %@", #"\d+/\d+ x\d+"#), "home.claw value n/target xM")
        print("[V1] home.claw value: \(value(app, "home.claw"))")
        let events = app.descendants(matching: .any).matching(NSPredicate(format: "identifier BEGINSWITH %@", "home.event."))
        XCTAssertGreaterThan(events.count, 0, "home.event.<id> badges")
    }

    func testLevelHUDAndBoardIdentifiers() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "32", "-pc.go", "level", "-pc.tutorials", "skip", "-pc.unlocks", "skip"])
        XCTAssertNotNil(app.waitReady(), app.debugDescription)
        require(app, ["hud.level", "hud.timer", "hud.hearts", "hud.coins", "hud.back", "hud.pause", "hud.booster.freeze",
                      "hud.booster.hint", "board", "board.probe", "hud.heart.1", "hud.heart.2", "hud.heart.3"], on: "level")
        XCTAssertEqual(value(app, "hud.level"), "Level 32")
        XCTAssertEqual(value(app, "hud.timer"), "180")
        XCTAssertEqual(value(app, "hud.hearts"), "3")
        XCTAssertEqual(value(app, "hud.booster.freeze"), "stock:3")
        XCTAssertEqual(value(app, "hud.booster.hint"), "stock:3")
    }

    func testTutorialIdentifiers() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "1", "-pc.go", "level", "-pc.tutorials", "force"])
        require(app, ["tutorial.caption", "tutorial.hand"], on: "Levels 1-4 stage 1 (tutorials forced)", timeout: 25)
    }

    func testPopupIdentifiers() {
        var app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "32", "-pc.go", "level", "-pc.popup", "pause"])
        require(app, ["popup.pause", "popup.pause.close", "popup.pause.primary", "popup.pause.secondary", "pause.toggle.sound",
                      "pause.toggle.haptic"], on: "pause")
        app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "34", "-pc.go", "level", "-pc.popup", "win:normal"])
        require(app, ["popup.win", "win.continue", "win.close", "win.reward"], on: "win")
        app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "35", "-pc.go", "level", "-pc.popup", "unlock:pipe", "-pc.unlocks", "force"])
        require(app, ["unlock.overlay"], on: "unlock overlay")
        app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "40", "-pc.go", "home", "-pc.popup", "noLives"])
        require(app, ["popup.noLives", "popup.noLives.close"], on: "More Lives (Y-2: popup.noLives)")
    }

    func testShopSettingsAndCaptureIdentifiers() {
        var app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "40", "-pc.go", "shop"])
        require(app, ["screen.shop", "shop.testStoreNote", "shop.product.offer.special"], on: "shop")
        app = AppUnderTest.launch(["-pc.reset", "1", "-pc.go", "settings"])
        require(app, ["settings.toggle.sound", "settings.toggle.music", "settings.toggle.haptic", "settings.toggle.notifications",
                      "settings.support", "settings.terms", "settings.privacy"], on: "settings")
        XCTAssertEqual(value(app, "settings.toggle.music"), "off", "Y-3: Music always off")
        app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "40", "-pc.go", "home", "-pc.capture", "1"])
        require(app, ["capture.ready"], on: "capture mode")
    }

    /// SPEC-ui §6 profile additions (VERIFY relies on them).
    func testProfileIdentifiers() {
        let st = AppUnderTest.state(#"{"level":62,"coins":4214,"homeSeen":true,"flags":{"seen":["clawIntro"]}}"#)
        var app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "profile"])
        require(app, ["screen.profile", "profile.avatar", "profile.name", "profile.level", "profile.edit", "profile.stat.firstTry",
                      "profile.stat.weekly", "profile.stat.streak", "profile.stat.rocket", "profile.stat.sky", "profile.stat.claw"],
                on: "profile (SPEC-ui §6)")
        app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "profile", "-pc.popup", "editProfile"])
        require(app, ["editProfile.name", "editProfile.avatar.0", "editProfile.avatar.8", "editProfile.save"], on: "Edit Profile (SPEC-ui §6)")
        app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "profile", "-pc.askName", "1"])
        require(app, ["username.field", "username.continue"], on: "Username (SPEC-ui §6)")
    }

    func testLeaderboardAndEventIdentifiers() {
        let st = AppUnderTest.state(#"{"level":62,"coins":4214,"homeSeen":true,"flags":{"seen":["clawIntro"]}}"#)
        var app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-09-25T12:00:00Z", "-pc.socialCountry", "TR", "-pc.go", "leaderboard:world"])
        _ = app.element("social.ready").wait(for: "value == %@", "world", timeout: 25)
        require(app, ["leaderboard.tab.weekly", "leaderboard.tab.world", "leaderboard.tab.country", "leaderboard.row.1"], on: "leaderboard")
        XCTAssertEqual(value(app, "leaderboard.tab.world"), "selected", "SPEC-ui §6: the open tab's value is \"selected\"")
        XCTAssertNotEqual(value(app, "leaderboard.tab.weekly"), "selected", "a closed tab is not selected")
        app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-09-25T12:00:00Z", "-pc.go", "event:streakRace"])
        require(app, ["page.streakRace", "event.streakRace.close"], on: "Streak Race page")
    }
}
