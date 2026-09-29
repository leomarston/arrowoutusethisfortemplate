import XCTest

/// SOCIAL SOC2 UI checks on the real app (SPEC-architecture §9.7 rules: base args, anchored predicates, no sleeps for
/// animations; `-pc.now` fixed so two launches see the same world):
/// - Leaderboard: World opens at the top with rank 1, Country opens on the player's green row (value = rank) and pins it; the
///   tab switch keeps each list; Weekly below L50 shows the locked text (S3), at L62 the podium + the group;
/// - the same seed + time twice → the same rows (row 1's name and the player's rank);
/// - the event pages open with their data (Streak Race rows, Rocket Race lanes from a real C3 join, the Sky Jump map, the Claw
///   ladder);
/// - the L50 Weekly tutorial accepts input only on the trophy tab (needs SHELL's popup-host hook: skipped with a clear message
///   while the host does not know the SOC2 panels);
/// - SocialLab's scroll bench: a 200+-row list flung top → bottom → top twice with 0 frames > 20 ms (Release build for the
///   verdict; the suite records whatever configuration it runs in).
final class SocialUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private let now = ["-pc.now", "2026-09-25T12:00:00Z", "-pc.socialCountry", "TR"]
    /// 25 Sep 2026 12:00 UTC + 19 weeks (B2, requirement change: the shipped v2 world starts 19 weeks later than the world
    /// this suite was written on — ruling 39 OD9): the SAME world age, so Turkey's board has the phone's size (#456 at Level
    /// 62) and the Country list the 200+ rows the scroll bench needs (18 days after its epoch it holds 75).
    private let nowSameAge = ["-pc.now", "2027-02-05T12:00:00Z", "-pc.socialCountry", "TR"]
    private func state(_ json: String) -> String { Data(json.utf8).base64EncodedString() }
    private func level(_ n: Int) -> [String] {
        ["-pc.reset", "1", "-pc.state", state(#"{"level":\#(n),"coins":4214,"homeSeen":true}"#)]
    }

    private func waitReady(_ app: XCUIApplication, _ kind: String, timeout: TimeInterval = 25) {
        let ready = app.element("social.ready")
        XCTAssertTrue(ready.wait(for: "value == %@", kind, timeout: timeout), "social list \(kind) never filled: \(app.debugDescription)")
    }

    func testWorldAndCountryLists() {
        let app = AppUnderTest.launch(level(62) + now + ["-pc.go", "leaderboard:world"])
        waitReady(app, "world")
        let first = app.element("leaderboard.row.1")
        XCTAssertTrue(first.waitForExistence(timeout: 5), app.debugDescription)
        XCTAssertTrue(first.isHittable, "World opens at the top (VERIFIED meta-018)")
        let firstName = first.label
        app.element("leaderboard.tab.country").tap()
        waitReady(app, "country")
        let me = app.element("leaderboard.me")
        XCTAssertTrue(me.waitForExistence(timeout: 5), app.debugDescription)
        let rank = Int((me.value as? String) ?? "") ?? 0
        XCTAssertGreaterThan(rank, 10, "a Level-62 player sits deep in Turkey's list")
        XCTAssertLessThanOrEqual(rank, 600)
        XCTAssertTrue(me.isHittable, "Country opens centred on the player's row (V2 33.5 s, meta-026)")
        // back to World: its list kept its place
        app.element("leaderboard.tab.world").tap()
        XCTAssertTrue(app.element("leaderboard.row.1").waitForExistence(timeout: 5))
        XCTAssertEqual(app.element("leaderboard.row.1").label, firstName)

        // determinism: a second launch at the same seed + time shows the same rows
        let again = AppUnderTest.launch(level(62) + now + ["-pc.go", "leaderboard:country"])
        waitReady(again, "country")
        XCTAssertTrue(again.element("leaderboard.me").wait(for: "value == %@", "\(rank)", timeout: 5), again.debugDescription)
        again.element("leaderboard.tab.world").tap()
        waitReady(again, "world")
        XCTAssertTrue(again.element("leaderboard.row.1").wait(for: "label == %@", firstName, timeout: 5))
    }

    func testWeeklyLockedThenPodium() {
        let locked = AppUnderTest.launch(level(40) + now + ["-pc.go", "leaderboard:weekly"])
        XCTAssertTrue(locked.element("lb.weekly.locked").waitForExistence(timeout: 20), locked.debugDescription)
        let app = AppUnderTest.launch(level(62) + now + ["-pc.go", "leaderboard:weekly"])
        waitReady(app, "weekly")
        XCTAssertTrue(app.element("weekly.podium").exists)
        XCTAssertTrue(app.element("leaderboard.row.1").exists || app.element("leaderboard.me").exists, app.debugDescription)
        // the player joined now with 0: last of the group (VERIFIED phone 132: rank 10, score 0)
        XCTAssertTrue(app.element("leaderboard.me").wait(for: "value == %@", "10", timeout: 5), app.debugDescription)
    }

    func testStreakRacePage() {
        let app = AppUnderTest.launch(level(62) + now + ["-pc.go", "event:streakRace"])
        XCTAssertTrue(app.element("page.streakRace").waitForExistence(timeout: 20), app.debugDescription)
        waitReady(app, "streak")
        // the page opens on the player's row (a fresh join: every row at 0, listed by name, SPEC-social §14.2)
        let rows = app.descendants(matching: .any).matching(NSPredicate(format: "identifier BEGINSWITH %@", "event.streakRace.row."))
        XCTAssertGreaterThanOrEqual(rows.count, 5, app.debugDescription)
        let mine = rows.matching(NSPredicate(format: "label BEGINSWITH %@", "player_")).firstMatch
        XCTAssertTrue(mine.exists, "the player's own row is on screen: \(app.debugDescription)")
        app.element("event.streakRace.close").tap()
        XCTAssertTrue(app.element("page.streakRace").wait(for: "exists == false", timeout: 5))
    }

    func testRocketRaceLanesFromARealJoin() {
        let app = AppUnderTest.launch(level(62) + now + ["-pc.socialScenario", "rocketMid", "-pc.go", "event:rocketRace"])
        XCTAssertTrue(app.element("page.rocketRace").waitForExistence(timeout: 20), app.debugDescription)
        let me = app.element("event.rocketRace.lane.0")
        XCTAssertTrue(me.wait(for: "value == %@", "1/5", timeout: 15), "lane 1 = the player with 1 level beaten: \(app.debugDescription)")
        for i in 1...4 { XCTAssertTrue(app.element("event.rocketRace.lane.\(i)").exists, "rival lane \(i)") }
    }

    func testSkyJumpMap() {
        let app = AppUnderTest.launch(level(45) + now + ["-pc.socialScenario", "skyStep2", "-pc.go", "event:skyJump"])
        XCTAssertTrue(app.element("page.skyJump").waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("event.skyJump.me").wait(for: "value == %@", "2/5", timeout: 15), app.debugDescription)
        let players = app.element("event.skyJump.players")
        let left = Int((players.value as? String) ?? "") ?? 100
        XCTAssertLessThan(left, 100, "players drop with the player's first-try wins")
        XCTAssertGreaterThan(left, 10)
    }

    func testClawLadder() {
        let app = AppUnderTest.launch(level(40) + now + ["-pc.go", "event:claw"])
        XCTAssertTrue(app.element("page.claw").waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("claw.progress").exists)
        XCTAssertTrue(app.element("event.claw.step.20").waitForExistence(timeout: 5) || app.element("event.claw.step.1").exists)
    }

    func testWeeklyTutorialLocksInputToTheTrophyTab() throws {
        let app = AppUnderTest.launch(level(50) + now + ["-pc.go", "home", "-pc.popup", "weeklyTutorial"])
        let card = app.element("weekly.tutorial.card")
        // FIX-3 B (V1A-T1): was `throw XCTSkip("the popup host does not route PopupID.weeklyContestTutorial to SOC2's panel
        // yet")` — a guard from before the SHELL hook existed. The route ships (SocialPopups.swift), so a missing card is a regression
        // and FAILS here: a skip would report it as green. Strengthened, nothing else changed.
        guard card.waitForExistence(timeout: 20) else {
            XCTFail("the Weekly Contest tutorial card ('weekly.tutorial.card') did not appear within 20 s of "
                    + "-pc.popup weeklyTutorial on home: the popup host no longer routes PopupID.weeklyContestTutorial to "
                    + "the tutorial panel. \(app.debugDescription)")
            return
        }
        // a tap anywhere else does nothing (the Play button under the dim)
        app.tap(screenX: 196, y: 470)
        XCTAssertTrue(card.exists, "input outside the trophy tab is locked")
        app.element("weekly.tutorial.tab").tap()
        XCTAssertTrue(app.element("weekly.info").waitForExistence(timeout: 10), "the tab opens the Weekly info: \(app.debugDescription)")
    }

    func testTwoHundredRowScrollHasNoSlowFrames() {
        let app = AppUnderTest.launch(level(62) + nowSameAge + ["-pc.go", "sociallab", "-pc.lab", "scroll:country"])
        // The bench (≈ 55 s of programmatic flings) must run UNOBSERVED: every XCUITest query snapshots the app's accessibility
        // tree on its main thread (tens of ms), which would show up as the app's own slow frames (PLAN F4). So the test does not
        // touch the app until the bench has had time to finish, then reads the result once.
        _ = XCTWaiter().wait(for: [XCTestExpectation(description: "the bench runs unobserved")], timeout: 75)
        let result = app.element("sociallab.result")
        XCTAssertTrue(result.wait(for: "value BEGINSWITH %@", "done", timeout: 60), app.debugDescription)
        let v = (result.value as? String) ?? ""
        print("[SOC2] scroll bench: \(v)")
        let parts = Dictionary(uniqueKeysWithValues: v.split(separator: " ").dropFirst().compactMap { kv -> (String, String)? in
            let p = kv.split(separator: "="); return p.count == 2 ? (String(p[0]), String(p[1])) : nil
        })
        XCTAssertGreaterThanOrEqual(Int(parts["rows"] ?? "") ?? 0, 200, v)
        XCTAssertEqual(Int(parts["over20"] ?? "") ?? -1, 0, "frames > 20 ms during the fling: \(v)")
    }
}
