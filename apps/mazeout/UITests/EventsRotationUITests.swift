import XCTest

/// B1 EVENTS-P — events.md §8.4 A7 (the home queue and the ribbons under the weekly rotation) and Up & Away's screens, on the
/// real app. Every test runs the CALENDAR — with `-pc.socialScenario rotation` for the home tests, or with the explicit
/// `-pc.tune rules.events.rotation.enabled=true` where a level runs (a scenario rewrites the saved state asynchronously after
/// the world is built, which would race the level) — while plain -pc.uitest keeps the v552 plan (every existing suite is
/// unchanged), at a fixed `-pc.now` in week 22 = Up & Away + Double Event Week (EventRotationTests pins the calendar):
///  - the week-start pages: the ladder event's page by itself with the "New Event!" ribbon (Let's Go! clears it), then the race
///    offers with the "Double Event Week!" ribbon, at most 2 unrequested pages per home visit (the Hot Streak list waits), and
///    never twice in a week (a relaunch shows only the waiting list);
///  - the NEW ribbon on the bar and the race badges until the event is opened this week, the ×2 gems, the Up & Away bar in
///    place of the Treasure Climb bar;
///  - the Up & Away page (the count, the paid platform, the (i) on the first open), the fail flow's fall page (VERIFIED v582:
///    after the chain, before Level Failed), the win panel's Up & Away strip.
/// B1b (v582 PH-0a, VERIFIED across the Monday 07:00 UTC roll): the ended events' badges stay and read "Finished" and the trophy
/// tab gets a red "!" until the player opens the result; then the new week's featured events show — on an idle home crossing
/// the roll from week 23 (Treasure Climb + Cloud Hop) into week 24 (Up & Away + Cloud Hop), and on the next home visit after it
/// (the claim, then the new day; this week's ladder page waits behind the Finished bar and follows its open).
final class EventsRotationUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    private let week22 = ["-pc.now", "2026-09-30T12:00:00Z", "-pc.clockRate", "0", "-pc.socialCountry", "TR"]
    private let calendar = ["-pc.tune", "rules.events.rotation.enabled=true"]
    private func state(_ json: String) -> String { Data(json.utf8).base64EncodedString() }
    private func count(_ app: XCUIApplication, _ id: String) -> Int {
        app.descendants(matching: .any).matching(identifier: id).count
    }

    func testWeekStartPagesOncePerWeekAndAtMostTwoPerVisit() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.state", state(#"{"level":60,"coins":4214,"homeSeen":true}"#)] + week22
                                      + ["-pc.socialScenario", "rotation", "-pc.tutorials", "force", "-pc.go", "home"])
        // (1) the ladder event's week-start page opens by itself, with its ribbon
        let page = app.element("page.balloon")
        XCTAssertTrue(page.waitForExistence(timeout: 30), "Up & Away's week-start page: \(app.debugDescription)")
        let ribbon = app.element("event.weekStart")
        XCTAssertTrue(ribbon.wait(for: "value == %@", "new", timeout: 5), app.debugDescription)
        if app.element("balloon.info.overlay").waitForExistence(timeout: 3) { app.element("balloon.info.overlay").tap() }  // the first open's (i)
        app.element("event.letsGo").tap()
        XCTAssertTrue(ribbon.waitForNonExistence(timeout: 5), "Let's Go! clears the ribbon")
        app.element("event.balloon.close").tap()
        // (2) back home: the race week-start offers, the Double Event Week ribbon on each
        let rocket = app.element("popup.rocketRace")
        XCTAssertTrue(rocket.waitForExistence(timeout: 20), "Rocket Rally's week-start offer: \(app.debugDescription)")
        XCTAssertTrue(app.element("event.weekStart").wait(for: "value == %@", "double", timeout: 5), app.debugDescription)
        app.element("popup.rocketRace.close").tap()
        let sky = app.element("popup.skyJump")
        XCTAssertTrue(sky.waitForExistence(timeout: 10), "Cloud Hop's week-start offer: \(app.debugDescription)")
        XCTAssertTrue(app.element("event.weekStart").wait(for: "value == %@", "double", timeout: 5))
        app.element("popup.skyJump.close").tap()
        // (3) the cap: 2 unrequested pages this visit — the day's Hot Streak list waits
        XCTAssertFalse(app.element("page.streakRace").waitForExistence(timeout: 6), "a third unrequested page this visit")
        XCTAssertTrue(app.element("home.balloon").exists, "the Up & Away bar in the ladder slot")
        XCTAssertFalse(app.element("home.claw").exists, "no Treasure Climb in an Up & Away week")
        // (4) the next visit (a relaunch, same week): no week-start page again; the waiting list comes first
        let again = AppUnderTest.launch(week22 + ["-pc.socialScenario", "rotation", "-pc.tutorials", "force", "-pc.go", "home"])
        XCTAssertTrue(again.element("page.streakRace").waitForExistence(timeout: 30), "the list the cap held back: \(again.debugDescription)")
        XCTAssertFalse(again.element("page.balloon").exists)
        XCTAssertFalse(again.element("event.weekStart").exists, "a week-start page shows once per event per week")
    }

    func testNewRibbonsAndDoubleGemsUntilTheEventIsOpened() {
        // no -pc.tutorials force: no page opens by itself, so every featured event is still NEW
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.state", state(#"{"level":60,"coins":4214,"homeSeen":true}"#)] + week22
                                      + ["-pc.socialScenario", "rotation", "-pc.go", "home"])
        let bar = app.element("home.balloon")
        XCTAssertTrue(bar.waitForExistence(timeout: 30), app.debugDescription)
        XCTAssertTrue(bar.wait(for: "value BEGINSWITH %@", "0/2 x", timeout: 5), "streak 0 toward platform 1: \(bar.debugDescription)")
        XCTAssertFalse(app.element("home.claw").exists)
        XCTAssertEqual(count(app, "home.event.new"), 3, "the bar + Rocket Rally + Cloud Hop: \(app.debugDescription)")
        XCTAssertEqual(count(app, "home.event.double"), 2, "×2 on both race badges")
        bar.tap()
        XCTAssertTrue(app.element("page.balloon").waitForExistence(timeout: 10), app.debugDescription)
        if app.element("balloon.info.overlay").waitForExistence(timeout: 3) { app.element("balloon.info.overlay").tap() }
        app.element("event.balloon.close").tap()
        XCTAssertTrue(app.element("home.balloon").waitForExistence(timeout: 10))
        let two = NSPredicate { _, _ in self.count(app, "home.event.new") == 2 }
        XCTAssertEqual(XCTWaiter().wait(for: [XCTNSPredicateExpectation(predicate: two, object: nil)], timeout: 25), .completed,
                       "the bar's ribbon goes once Up & Away was opened this week: \(app.debugDescription)")
    }

    func testUpAndAwayPageShowsTheCountAndThePaidPlatform() {
        let json = #"{"level":45,"coins":4214,"homeSeen":true,"events":{"balloon":{"week":22,"streak":3,"paid":1,"best":3}}}"#
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.state", state(json)] + week22 + calendar + ["-pc.go", "event:balloonRise"])
        let page = app.element("page.balloon")
        XCTAssertTrue(page.waitForExistence(timeout: 30), app.debugDescription)
        XCTAssertTrue(page.wait(for: "value == %@", "3/5", timeout: 5), "3 wins in a row, the next platform at 5: \(page.debugDescription)")
        // the first open ever explains the rules
        let info = app.element("balloon.info.overlay")
        XCTAssertTrue(info.waitForExistence(timeout: 5), "the first open shows the (i): \(app.debugDescription)")
        info.tap()
        XCTAssertTrue(info.waitForNonExistence(timeout: 5))
        XCTAssertTrue(app.element("balloon.platform.1").wait(for: "value == %@", "paid", timeout: 5))
        XCTAssertTrue(app.element("balloon.platform.2").wait(for: "value == %@", "unpaid", timeout: 5))
        XCTAssertTrue(app.element("balloon.hero").wait(for: "value == %@", "3", timeout: 5), "the balloon at 3")
        XCTAssertTrue(app.element("balloon.timer").exists)
        app.element("event.info").tap()
        XCTAssertTrue(app.element("balloon.info.overlay").waitForExistence(timeout: 5), "(i) on demand")
    }

    func testTheFallPageFollowsALostStreakThenLevelFailed() {
        let json = #"{"level":45,"coins":4214,"homeSeen":true,"flags":{"seen":["balloonIntro"]},"events":{"streakStep":2,"balloon":{"week":22,"streak":3,"paid":1,"best":3}}}"#
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.state", state(json)] + week22 + calendar
                                      + ["-pc.tutorials", "skip", "-pc.unlocks", "skip", "-pc.go", "level", "-pc.lose", "quit"])
        let fall = app.element("page.balloonFall")
        XCTAssertTrue(fall.waitForExistence(timeout: 30), "the fall page after the chain (VERIFIED v582): \(app.debugDescription)")
        XCTAssertFalse(app.element("popup.levelFailed").exists, "Level Failed waits behind the fall page")
        app.element("popup.balloonFall.close").tap()
        XCTAssertTrue(app.element("popup.levelFailed").waitForExistence(timeout: 10), "its X leads to Level Failed: \(app.debugDescription)")
    }

    func testTheWinPanelShowsTheUpAndAwayStrip() {
        let json = #"{"level":45,"coins":4214,"homeSeen":true,"events":{"balloon":{"week":22,"streak":3,"paid":1,"best":3}}}"#
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.state", state(json)] + week22 + calendar
                                      + ["-pc.tutorials", "skip", "-pc.unlocks", "skip", "-pc.go", "level", "-pc.win", "normal"])
        // B1b: the strip INSIDE the presented win panel — under load the Loading warm-up's hidden strip (the same id, value
        // "1>2") can still be in the tree when the level starts, and matched first, then left before the panel came (ui-rot-2,
        // ui-pass2: "No matches found"); the assertions are unchanged
        let panel = app.element("popup.win")
        XCTAssertTrue(panel.waitForExistence(timeout: 30), "the win panel: \(app.debugDescription)")
        let strip = panel.descendants(matching: .any).matching(identifier: "win.balloonStrip").firstMatch
        XCTAssertTrue(strip.waitForExistence(timeout: 10), "the Up & Away strip replaces the Hot Streak strip: \(app.debugDescription)")
        XCTAssertTrue(strip.wait(for: "value == %@", "3>4", timeout: 5), strip.debugDescription)
        XCTAssertFalse(panel.descendants(matching: .any).matching(identifier: "streak.chips").firstMatch.exists,
                       "no Hot Streak strip on this win panel")
    }

    // MARK: B1b — the Finished state at the week's end (v582 PH-0a)

    /// Sunday evening of week 23 as the owner's v582 home had it: the ladder bar at 537 of step 12's 800, yesterday-to-today's
    /// Hot Streak joined (day 167 = Sun 10-11 07:00 → Mon 10-12 07:00 UTC), the week-23 Weekly Cup joined. `claims`: extra JSON.
    /// The Treasure Climb page was opened before (`social.clawLadder`): its first-ever open runs a 2.2 s auto-scroll whose end
    /// rebuilds the page's accessibility tree — an X tapped in that instant lost its hit point (ui-rot-3); not what these test.
    private func endOfWeek23(weekly: Bool = true, claims: String = "") -> String {
        let week = weekly ? #","weekly":{"index":23,"joinedAt":{"seconds":1791187200},"score":0}"# : ""
        return #"{"level":60,"coins":4214,"homeSeen":true,"flags":{"seen":["social.clawLadder"]},"#
            + #""events":{"claw":{"week":23,"points":537,"step":11},"#
            + #""streakRace":{"index":167,"joinedAt":{"seconds":1791702600},"score":12,"lastScoreAt":{"seconds":1791740000}}"#
            + week + claims + "}}"
    }

    /// Taps every claim overlay that comes within `timeout` (an honest podium of the world's final ranks may add one). It taps
    /// inside the PRESENTED popup ("popup.claim", PopupHost's container): under load the Loading warm-up's hidden claim view
    /// (also "claim.tap") can still be in the tree when home arrives, and a tap on it claims nothing (ui-pass2).
    @discardableResult
    private func claimAll(_ app: XCUIApplication, timeout: TimeInterval) -> Int {
        let popup = app.element("popup.claim")
        var n = 0
        while n < 4, popup.waitForExistence(timeout: n == 0 ? timeout : 4) {
            popup.descendants(matching: .any).matching(identifier: "claim.tap").firstMatch.tap()
            n += 1
            _ = popup.wait(for: "exists == false", timeout: 8)       // a following claim takes the same id: the loop taps it
        }
        XCTAssertFalse(popup.exists, "every claim was answered: \(app.debugDescription)")
        return n
    }

    func testTheIdleHomeReadsFinishedAtTheMondayRollUntilEachResultIsOpened() {
        // the home sits idle across Mon 2026-10-12 07:00 UTC (the clock runs ×2 from 06:59:00; no touch, like PH-0a)
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.state", state(endOfWeek23())]
                                      + ["-pc.now", "2026-10-12T06:59:00Z", "-pc.clockRate", "2", "-pc.socialCountry", "TR"]
                                      + calendar + ["-pc.go", "home"])
        let bar = app.element("home.claw")
        let chip = app.element("home.claw.timer")
        let streak = app.element("home.event.streakRace")
        let news = app.element("nav.leaderboard.news")
        XCTAssertTrue(bar.waitForExistence(timeout: 30), app.debugDescription)
        // before the roll: the countdowns run, no "!"
        XCTAssertTrue(bar.wait(for: "value BEGINSWITH %@", "537/800 x", timeout: 5), bar.debugDescription)
        XCTAssertTrue(streak.wait(for: "value BEGINSWITH %@", "timer:", timeout: 5), streak.debugDescription)
        XCTAssertFalse(chip.wait(for: "value == %@", "finished", timeout: 1), "before the roll: \(chip.debugDescription)")
        XCTAssertFalse(news.exists, "no '!' before the roll: \(app.debugDescription)")
        // at the roll (≤ one 20 s re-read later): the same badges read Finished, the bar keeps 537/800, the trophy gets its "!",
        // and nothing new takes the ladder slot yet
        XCTAssertTrue(chip.wait(for: "value == %@", "finished", timeout: 75), "the bar's chip at the roll: \(chip.debugDescription)")
        XCTAssertTrue(streak.wait(for: "value == %@", "finished", timeout: 25), streak.debugDescription)
        XCTAssertTrue(news.waitForExistence(timeout: 25), "the trophy tab's red '!': \(app.debugDescription)")
        XCTAssertTrue(bar.wait(for: "value BEGINSWITH %@", "537/800 x", timeout: 2), bar.debugDescription)
        XCTAssertFalse(app.element("home.balloon").exists, "this week's Up & Away waits behind the Finished bar")
        // the Weekly Cup's result = the Leaderboard tab: its "!" goes (a podium claim, if the world's ranks gave one, is claimed)
        app.element("nav.leaderboard").tap()
        XCTAssertTrue(app.element("nav.leaderboard").wait(for: "value == %@", "selected", timeout: 10))
        app.element("nav.home").tap()
        XCTAssertTrue(bar.waitForExistence(timeout: 10))
        claimAll(app, timeout: 6)
        XCTAssertTrue(news.waitForNonExistence(timeout: 25), "the '!' went with the opened result: \(app.debugDescription)")
        XCTAssertTrue(chip.wait(for: "value == %@", "finished", timeout: 2), "each result is opened on its own")
        // the Hot Streak's result = its page; back home: the new day's countdown
        streak.tap()
        XCTAssertTrue(app.element("page.streakRace").waitForExistence(timeout: 10), app.debugDescription)
        app.element("event.streakRace.close").tap()
        XCTAssertTrue(streak.wait(for: "value BEGINSWITH %@", "timer:", timeout: 25), "the new day's Hot Streak: \(streak.debugDescription)")
        // the ladder's result = the ended week's page ("Finished"), then this week's Up & Away takes the slot, NEW on its token
        bar.tap()
        let page = app.element("page.claw")
        XCTAssertTrue(page.waitForExistence(timeout: 10), app.debugDescription)
        XCTAssertTrue(page.wait(for: "value == %@", "finished", timeout: 5), "the ended week's ladder: \(page.debugDescription)")
        app.element("event.claw.close").tap()
        let balloon = app.element("home.balloon")
        XCTAssertTrue(balloon.waitForExistence(timeout: 15), "then the new week's ladder event: \(app.debugDescription)")
        XCTAssertTrue(balloon.wait(for: "value BEGINSWITH %@", "0/2 x", timeout: 5), balloon.debugDescription)
        XCTAssertTrue(app.element("home.balloon.timer").wait(for: "value != %@", "finished", timeout: 5))
        XCTAssertFalse(bar.exists, "the Finished bar is gone")
        XCTAssertGreaterThanOrEqual(count(app, "home.event.new"), 1, "the new week's event is NEW: \(app.debugDescription)")
    }

    func testAfterTheRollTheClaimThenTheNewDayAndTheLadderPageFollowsTheFinishedOne() {
        // the first home visit after the roll (the ended Hot Streak's prize waits as a claim; the unrequested pages run)
        let prize = #","claims":[{"id":1,"event":"streakRace","kind":"streakRacePrize","grant":{"coins":2000},"value":1,"index":167,"at":{"seconds":1791788400}}],"nextClaimID":2"#
        let args = ["-pc.now", "2026-10-12T07:05:00Z", "-pc.clockRate", "0", "-pc.socialCountry", "TR"] + calendar
                   + ["-pc.tutorials", "force", "-pc.go", "home"]
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.state", state(endOfWeek23(weekly: false, claims: prize))] + args)
        XCTAssertTrue(app.element("popup.claim").waitForExistence(timeout: 30), "the claim first: \(app.debugDescription)")
        XCTAssertGreaterThanOrEqual(claimAll(app, timeout: 1), 1)
        let streak = app.element("home.event.streakRace")
        XCTAssertTrue(streak.wait(for: "value BEGINSWITH %@", "timer:", timeout: 10), "the claim, then the new day: \(streak.debugDescription)")
        // the visit's unrequested pages: Cloud Hop's week-start offer and the day's list — NOT this week's Up & Away page, the
        // ladder slot still holds last week's Treasure Climb
        let sky = app.element("popup.skyJump")
        XCTAssertTrue(sky.waitForExistence(timeout: 20), "Cloud Hop's week-start offer: \(app.debugDescription)")
        app.element("popup.skyJump.close").tap()
        let list = app.element("popup.streakRace")                          // the presented list (not the warm-up's copy)
        XCTAssertTrue(list.waitForExistence(timeout: 15), "the day's Hot Streak list: \(app.debugDescription)")
        list.descendants(matching: .any).matching(identifier: "event.streakRace.close").firstMatch.tap()
        XCTAssertFalse(app.element("page.balloon").waitForExistence(timeout: 6), "this week's ladder page waits behind the Finished bar")
        XCTAssertTrue(app.element("home.claw.timer").wait(for: "value == %@", "finished", timeout: 5), app.debugDescription)
        XCTAssertFalse(app.element("home.balloon").exists)
        // the hold is saved: a relaunch in the same minute still shows the Finished bar and opens nothing by itself
        let again = AppUnderTest.launch(args)
        XCTAssertTrue(again.element("home.claw.timer").wait(for: "value == %@", "finished", timeout: 30), again.debugDescription)
        XCTAssertFalse(again.element("page.balloon").waitForExistence(timeout: 6))
        // opening the Finished bar: the ended week's page; its X brings home back and THIS week's page opens by itself
        again.element("home.claw").tap()
        XCTAssertTrue(again.element("page.claw").wait(for: "value == %@", "finished", timeout: 10), again.debugDescription)
        again.element("event.claw.close").tap()
        let page = again.element("page.balloon")
        XCTAssertTrue(page.waitForExistence(timeout: 20), "then the new week's page: \(again.debugDescription)")
        XCTAssertTrue(again.element("event.weekStart").wait(for: "value == %@", "new", timeout: 5), again.debugDescription)
        if again.element("balloon.info.overlay").waitForExistence(timeout: 3) { again.element("balloon.info.overlay").tap() }
        again.element("event.letsGo").tap()
        again.element("event.balloon.close").tap()
        XCTAssertTrue(again.element("home.balloon").waitForExistence(timeout: 10), again.debugDescription)
        XCTAssertFalse(again.element("home.claw").exists, "the ended week's bar is gone")
    }
    /// FIX-2 lane B (L28 — the phone wins, v582 PH-0a build/p/PH0a/before-reset.png): in an event's LAST HOUR the Treasure Climb
    /// chip and the Hot Streak badge read mm:ss ("09:34" at 9 min 34 s before the Monday 07:00 UTC roll, which is also the Hot
    /// Streak day's end) on the BLUE chip — no red last-day face, no "last:" value — and an hour earlier the chip reads
    /// "1h 9m" (minutes kept). The v552 plan (no rotation tune): the Claw runs every week.
    func testLastHourCountdownReadsMinutesAndSecondsOnTheBlueChip() {
        let st = state(#"{"level":62,"coins":4194,"homeSeen":true}"#)
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-10-05T06:50:26Z", "-pc.clockRate", "0",
                                       "-pc.socialCountry", "TR", "-pc.go", "home"])
        let chip = app.element("home.claw.timer")
        XCTAssertTrue(chip.waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(chip.wait(for: "value == %@", "09:34"), "mm:ss in the last hour, no 'last:' red chip: \(chip.debugDescription)")
        XCTAssertTrue(app.element("home.event.streakRace").wait(for: "value == %@", "timer:09:34"),
                      app.element("home.event.streakRace").debugDescription)
        let before = AppUnderTest.launch(["-pc.state", st, "-pc.now", "2026-10-05T05:50:26Z", "-pc.clockRate", "0",
                                          "-pc.socialCountry", "TR", "-pc.go", "home"])
        let chip2 = before.element("home.claw.timer")
        XCTAssertTrue(chip2.waitForExistence(timeout: 20), before.debugDescription)
        XCTAssertTrue(chip2.wait(for: "value == %@", "1h 9m"), chip2.debugDescription)
    }

    /// FIX-2 lane B, review of L28: the event PAGES' countdowns tick on their own in the last hour, like home's — each chip
    /// reads the running clock at every second, not the time its page last rendered. 9 min 34 s before the Monday 07:00 UTC
    /// roll (week 22's end and the Hot Streak day's end) with the clock at real speed, for ~6 s: the Hot Streak page's chip and
    /// the Up & Away page's chip each step down WITH the clock — at least 4 different values, never up, never more than one
    /// second ahead of the time between two reads, and the whole drop = the time that passed (± 1.5 s). The pages before
    /// this fix fail it (the review's evidence, build/p/FIX2/review-B/ticks: Up & Away stood at "09:32" for 6 s; Hot Streak
    /// jumped in 5 s steps with the social refresh); negative control run on that build: build/p/FIX2/B-R/neg.
    /// FIX-2 lane B, review nit of L28: a ladder page opened for an event this player has no running instance of (the Treasure
    /// Climb page in week 22, Up & Away's week — only a debug `-pc.go` reaches it) draws no countdown chip at all, instead of
    /// a stale "00:00" beside "Coming next: Treasure Climb · Starts in 09:33"; this week's own page (Up & Away) keeps its chip.
    func testALadderPageWithNoRunningEventDrawsNoCountdown() {
        let st = state(#"{"level":62,"coins":4194,"homeSeen":true,"flags":{"seen":["clawIntro","balloonIntro","weekStart-22.balloonRise","social.clawLadder"]},"events":{"balloon":{"week":22,"streak":1,"paid":0,"best":1}}}"#)
        let now = ["-pc.now", "2026-10-05T06:50:26Z", "-pc.clockRate", "0", "-pc.socialCountry", "TR"]
        let app = AppUnderTest.launch(["-pc.state", st] + now + calendar + ["-pc.go", "event:claw"])
        XCTAssertTrue(app.element("page.claw").waitForExistence(timeout: 20), app.debugDescription)
        XCTAssertTrue(app.element("event.comingNext").wait(for: "value == %@", "clawChallenge", timeout: 5), "the teaser names it: \(app.debugDescription)")
        XCTAssertFalse(app.element("event.timer").exists, "no chip for a ladder that is not running: \(app.debugDescription)")
        let again = AppUnderTest.launch(["-pc.state", st] + now + calendar + ["-pc.go", "event:balloonRise"])
        XCTAssertTrue(again.element("balloon.timer").wait(for: "value == %@", "09:34", timeout: 20), again.debugDescription)
    }

    func testEventPageCountdownsTickEverySecondInTheLastHour() {
        let seen = #""flags":{"seen":["clawIntro","balloonIntro","weekStart-22.balloonRise","skyOffer-160","streakList-160","rocketOffer-160"]}"#
        let st = state(#"{"level":62,"coins":4194,"homeSeen":true,"# + seen + #","events":{"balloon":{"week":22,"streak":1,"paid":0,"best":1}}}"#)
        let now = ["-pc.now", "2026-10-05T06:50:26Z", "-pc.clockRate", "1", "-pc.socialCountry", "TR"]
        func seconds(_ v: Any?) -> Int? {
            guard let s = v as? String else { return nil }
            let p = s.split(separator: ":")
            guard p.count == 2, p[0].count == 2, p[1].count == 2, let m = Int(p[0]), let x = Int(p[1]) else { return nil }
            return m * 60 + x
        }
        for (go, id) in [("event:streakRace", "event.timer"), ("event:balloonRise", "balloon.timer")] {
            let app = AppUnderTest.launch(["-pc.state", st] + now + calendar + ["-pc.go", go])
            let chip = app.element(id)
            XCTAssertTrue(chip.waitForExistence(timeout: 20), "\(go): \(app.debugDescription)")
            XCTAssertTrue(chip.wait(for: "value MATCHES %@", "0[89]:[0-5][0-9]", timeout: 5), "\(go): mm:ss in the last hour: \(chip.debugDescription)")
            var samples: [(t: Date, s: Int)] = []
            let t0 = Date()
            while Date().timeIntervalSince(t0) < 6 {
                if let s = seconds(chip.value) { samples.append((Date(), s)) }
                RunLoop.current.run(until: Date().addingTimeInterval(0.25))
            }
            let trail = samples.map { "\($0.s)@" + String(format: "%.2f", $0.t.timeIntervalSince(t0)) }.joined(separator: " ")
            XCTAssertGreaterThanOrEqual(samples.count, 6, "\(go): enough reads: \(trail)")
            guard let first = samples.first, let last = samples.last else { continue }
            XCTAssertGreaterThanOrEqual(Set(samples.map(\.s)).count, 4, "\(go): a new value every second: \(trail)")
            for (a, b) in zip(samples, samples.dropFirst()) {
                XCTAssertLessThanOrEqual(b.s, a.s, "\(go): never goes up: \(trail)")
                XCTAssertLessThanOrEqual(Double(a.s - b.s), b.t.timeIntervalSince(a.t) + 1.2, "\(go): no jump ahead of the clock: \(trail)")
            }
            XCTAssertEqual(Double(first.s - last.s), last.t.timeIntervalSince(first.t), accuracy: 1.5, "\(go): follows the clock: \(trail)")
        }
    }
}
