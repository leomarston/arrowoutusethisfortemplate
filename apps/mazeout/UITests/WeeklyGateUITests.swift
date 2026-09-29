import XCTest

/// FIX-A2 (the INTEG review's low: "WeeklyTutorialGate never executed"). The L50 Weekly Contest gate on the real app, through
/// the real home Play button (App/Game/EventsDirector.swift `WeeklyTutorialGate`, SOC2's `SocialFlows.weeklyTutorial`): the
/// FIRST Play at L50 does not start the level — it opens the Weekly tutorial (input locked to the trophy tab), the tab opens
/// the Weekly page and its info, and the Weekly tab on screen joins the week's group (SocialFlows.joinWeeklyIfNeeded — the
/// info's close would too): the player's row in the list; the SECOND Play
/// goes to the level, and after a relaunch the gate stays done (the intro-seen flag is saved).
/// Tutorials are off in UI tests (ruling 33) unless `-pc.tutorials force`, which also allows the home queue's once-a-day pages:
/// the state marks today's (the Sky Jump offer, the Streak Race board, the Claw first-open page) as seen, so only the gate runs.
final class WeeklyGateUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    /// The fixed world clock. Its event day is 151 = ⌊(2026-09-25 12:00 − 2026-04-27 07:00 UTC, EventSchedule's epoch) / 1 day⌋,
    /// which keys the home queue's daily pages ("skyOffer-151", "streakList-151").
    private let now = ["-pc.now", "2026-09-25T12:00:00Z", "-pc.socialCountry", "TR"]

    func testTheFirstPlayAtL50RunsTheWeeklyTutorialAndTheSecondPlayStartsTheLevel() {
        let st = AppUnderTest.state(#"{"level":50,"coins":4214,"homeSeen":true,"flags":{"seen":["clawIntro","skyOffer-151","streakList-151"]}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home", "-pc.tutorials", "force"] + now)
        let play = app.element("home.play")
        XCTAssertTrue(play.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(play.wait(for: "value == %@", "50"), play.debugDescription)
        XCTAssertFalse(app.element("popup.weeklyTutorial").exists, "nothing before the Play")
        play.tap()

        // 1. the tutorial instead of the level: the card, input locked outside the trophy tab
        let card = app.element("weekly.tutorial.card")
        XCTAssertTrue(card.waitForExistence(timeout: 10), "the first Play at L50 opens the Weekly tutorial: \(app.debugDescription)")
        XCTAssertFalse(app.element("hud.pause").exists, "the level did not start")
        XCTAssertTrue(app.element("screen.home").exists)
        app.tap(screenX: 196, y: 470)                                        // the Play button's area under the dim
        XCTAssertTrue(card.exists, "input outside the trophy tab is locked")
        XCTAssertFalse(app.element("hud.pause").exists, "still no level")

        // 2. the tab → the Weekly page + its info
        app.element("weekly.tutorial.tab").tap()
        let info = app.element("popup.weeklyIntro")
        XCTAssertTrue(info.waitForExistence(timeout: 10), "the tab opens the Weekly info: \(app.debugDescription)")
        XCTAssertFalse(card.exists, "the tutorial is gone")
        XCTAssertTrue(app.element("weekly.podium").waitForExistence(timeout: 5), "the Weekly tab is under the info: \(app.debugDescription)")

        // 3. the info closes on a tap anywhere; the week's group is joined: the player's row (a fresh join sits at rank 10)
        info.tap()
        XCTAssertTrue(info.waitForNonExistence(timeout: 5), app.debugDescription)
        XCTAssertTrue(app.element("social.ready").wait(for: "value == %@", "weekly", timeout: 20), app.debugDescription)
        let me = app.element("leaderboard.me")
        XCTAssertTrue(me.waitForExistence(timeout: 10), "joined: the player's row in the group: \(app.debugDescription)")
        let rank = Int((me.value as? String) ?? "") ?? 0
        XCTAssertTrue((4...10).contains(rank), "a fresh join's row in the list (ranks 4-10): \(me.debugDescription)")

        // 4. home → the second Play starts the level
        app.element("nav.home").tap()
        XCTAssertTrue(play.waitForExistence(timeout: 10), app.debugDescription)
        XCTAssertTrue(play.wait(for: "value == %@", "50"))
        play.tap()
        guard let p = app.waitReady() else { return XCTFail("L50 never became ready: \(app.debugDescription)") }
        XCTAssertEqual(p["lvl"] as? Int, 50)
        XCTAssertFalse(app.element("popup.weeklyTutorial").exists, "the gate ran once")

        // 5. a relaunch on the saved state (no -pc.state / -pc.reset): the gate stays done — Play goes straight to the level
        let again = AppUnderTest.launch(["-pc.go", "home", "-pc.tutorials", "force"] + now)
        let play2 = again.element("home.play")
        XCTAssertTrue(play2.waitForExistence(timeout: 20), again.debugDescription)
        XCTAssertTrue(play2.wait(for: "value == %@", "50"), "the save kept L50 (the level was not played): \(play2.debugDescription)")
        play2.tap()
        guard let q = again.waitReady() else { return XCTFail("L50 never became ready after the relaunch: \(again.debugDescription)") }
        XCTAssertEqual(q["lvl"] as? Int, 50)
        XCTAssertFalse(again.element("weekly.tutorial.card").exists, "weeklyIntroSeen was saved")
    }
    /// FIX-2 lane B (L26: the lock leaked ONCE in 8 runs — one tap on the 0.92 dim answered the tutorial). Every touch outside
    /// the trophy tab is swallowed: 30 taps, 10 double taps and 5 short drags at seeded points all over the screen (the home's
    /// Play button, the other nav tabs, the card — never the tab's hole + a 16 pt margin), each followed by the check that
    /// nothing answered (the card stays 0.5 s, no Weekly info, no level). Then the tab itself still answers. Run it under
    /// `-test-iterations 20 -run-tests-until-failure` for the stress proof (build/p/FIX2/B).
    /// FIX-2 B review: each run of this test in one test process draws ITS OWN points — run i seeds with the base + i (below),
    /// so 20 iterations are 20 × 45 different gestures, not the same 45 twenty times; run 0 is always the same 45 (a single run
    /// is reproducible) and every failure names its seed. Negative control, run: the pre-L26 lock (the `.onTapGesture`
    /// catcher inside the per-frame TimelineView) PASSED 12 runs of this test (540 distinct gestures, idle simulator,
    /// build/p/FIX2/B-R/neg) — so this test does not reproduce that 1-in-8 leak (a simulator double delivery, blocked.md
    /// 19:01) and its green runs are no proof against it; the falsifiable part is the swallow view's hit map
    /// (SocialScreensTests.testTheWeeklyTutorialSwallowClaimsEveryPointOutsideTheTab). It stays as the behaviour check.
    private static var swallowRuns: UInt64 = 0

    func testTheTutorialSwallowsEveryTouchOutsideTheTab() {
        let st = AppUnderTest.state(#"{"level":50,"coins":4214,"homeSeen":true,"flags":{"seen":["clawIntro","skyOffer-151","streakList-151"]}}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "home", "-pc.tutorials", "force"] + now)
        let play = app.element("home.play")
        XCTAssertTrue(play.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(play.wait(for: "value == %@", "50"), play.debugDescription)
        play.tap()
        let card = app.element("weekly.tutorial.card")
        XCTAssertTrue(card.waitForExistence(timeout: 10), "the first Play at L50 opens the Weekly tutorial: \(app.debugDescription)")
        let info = app.element("popup.weeklyIntro"), pause = app.element("hud.pause")
        let hole = CGRect(x: 279.2 - 16, y: 772.3 - 16, width: 93.7 + 32, height: 80.4 + 32)
        let run = Self.swallowRuns
        Self.swallowRuns += 1
        let seed0: UInt64 = 0x50_5745_454B &+ run &* 0x9E37_79B9_7F4A_7C15   // "PWEEK" + this run's step (run 0: the base)
        var seed = seed0
        func unit() -> Double {
            seed = seed &* 6364136223846793005 &+ 1442695040888963407
            return Double(seed >> 11) / Double(1 << 53)
        }
        func point(_ ys: ClosedRange<Double>) -> CGPoint {
            while true {
                let p = CGPoint(x: 8 + unit() * 377, y: ys.lowerBound + unit() * (ys.upperBound - ys.lowerBound))
                if !hole.contains(p) { return p }
            }
        }
        func at(_ p: CGPoint) -> XCUICoordinate { app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: p.x, dy: p.y)) }
        let tag = "run \(run), seed 0x" + String(seed0, radix: 16)
        print("WeeklySwallow \(tag)")                                      // the log shows each repetition's own points
        func holds(_ what: String) {
            XCTAssertFalse(card.waitForNonExistence(timeout: 0.5), "\(tag), \(what): the tutorial answered — the lock leaked: \(app.debugDescription)")
            XCTAssertFalse(info.exists, "\(tag), \(what): the Weekly info opened")
            XCTAssertFalse(pause.exists, "\(tag), \(what): a level started")
        }
        for i in 0..<30 {
            let p = point(60...820)
            app.tap(screenX: p.x, y: p.y)
            holds("tap \(i) at (\(Int(p.x)), \(Int(p.y)))")
        }
        for i in 0..<10 {
            let p = point(60...820)
            at(p).doubleTap()
            holds("double tap \(i) at (\(Int(p.x)), \(Int(p.y)))")
        }
        for i in 0..<5 {
            let a = point(140...720)
            let b = CGPoint(x: min(380, max(12, a.x + (unit() - 0.5) * 80)), y: a.y + (unit() - 0.5) * 80)
            at(a).press(forDuration: 0.05, thenDragTo: at(b))
            holds("drag \(i) (\(Int(a.x)), \(Int(a.y))) → (\(Int(b.x)), \(Int(b.y)))")
        }
        app.element("weekly.tutorial.tab").tap()
        XCTAssertTrue(info.waitForExistence(timeout: 10), "the tab still answers: \(app.debugDescription)")
        XCTAssertFalse(card.exists, "the tutorial is gone")
    }
}
