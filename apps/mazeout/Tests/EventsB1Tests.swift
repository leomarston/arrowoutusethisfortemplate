import XCTest
import PathCore
@testable import ArrowOut

/// B1 EVENTS-P (events.md §4.6, §6, §8.4 A7/A8): the app side of the weekly rotation and Up & Away.
///  - the policy: the shipped rotation runs; -pc.uitest / -pc.capture keep the v552 plan unless a `rotation…` scenario or an
///    explicit tune asks (existing UI tests keep their meaning); the Release art gate hands Up & Away's weeks to Treasure Climb
///    until its art exists (never ship stand-in content);
///  - the win panel's Up & Away strip reads the win's outcome; the notification plan carries the event notifications inside
///    10:00-21:00 local, one per 24 h; the week-start / NEW keys stay one per event and kind.
///  - B1b: the ended events are held ("Finished", v582 PH-0a) under the shipped rotation only.
@MainActor
final class EventsB1Tests: XCTestCase {
    func economy(_ pairs: [String: String]) -> EconomyRules {
        let args = LaunchArgs(pairs: pairs)
        let tuning = Tuning.load(bundle: .main, tune: EventRotationPolicy.tune(args))
        var r = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data, overrides: tuning.rules.overrides).rules
        EventRotationPolicy.apply(&r)
        return r
    }

    func testTheRotationPolicy() {
        XCTAssertTrue(economy([:]).events.rotation.enabled, "the shipped social.json runs the calendar")
        XCTAssertFalse(economy(["pc.uitest": "1"]).events.rotation.enabled, "UI tests keep the v552 plan")
        XCTAssertFalse(economy(["pc.capture": "1"]).events.rotation.enabled, "captures keep the v552 plan")
        XCTAssertTrue(economy(["pc.uitest": "1", "pc.socialScenario": "rotationBalloon"]).events.rotation.enabled,
                      "a rotation scenario runs the calendar")
        XCTAssertFalse(economy(["pc.uitest": "1", "pc.socialScenario": "rocketMid"]).events.rotation.enabled)
        XCTAssertTrue(economy(["pc.uitest": "1", "pc.tune": "rules.events.rotation.enabled=true"]).events.rotation.enabled,
                      "an explicit tune wins")
        XCTAssertFalse(economy(["pc.tune": "rules.events.rotation.enabled=false"]).events.rotation.enabled, "the kill switch by tune")
        // the uitest plan: every unlocked event, whatever the calendar (week 22 is an Up & Away + Double week)
        let r = economy(["pc.uitest": "1"])
        XCTAssertEqual(EventRotation.live(week: 22, level: 60, rules: r.events),
                       LiveEvents(always: [.streakRace, .weeklyContest], ladder: .clawChallenge, race: [.rocketRace, .skyJump]))
    }

    func testTheReleaseArtGate() {
        // pure: Release without the art → unavailable; DEBUG never (the hatched placeholder shows there)
        XCTAssertTrue(EventRotationPolicy.gate(debug: false, ready: false))
        XCTAssertFalse(EventRotationPolicy.gate(debug: false, ready: true))
        XCTAssertFalse(EventRotationPolicy.gate(debug: true, ready: false))
        // A4 ART-INTEG: R8 delivered the page as pieces (the tall backdrop would decode to 53 MB; the pieces ≈ 21 MB), so the
        // gate's list is R8's delivered ids — same exact equality — and every one of them is now in the generated table
        // (skin phase 3: the ids are the art SLOTS those pieces fill, skin/art.json; the files are still R8's)
        XCTAssertEqual(UpAwayArt.ids, ["event.balloonRise.badge", "event.balloonRise.hero", "event.balloonRise.towerTop",
                                       "event.balloonRise.towerShaft", "event.balloonRise.towerFoot", "event.balloonRise.ledge"],
                       "R8's delivered Up & Away pieces, by slot")
        XCTAssertEqual(UpAwayArt.ids.compactMap { UIArt(rawValue: $0)?.asset },
                       ["eventBadgeBalloon", "balloonHero", "balloonTowerTop", "balloonTowerShaft", "balloonTowerFoot", "balloonLedge"],
                       "the reference skin fills them with R8's files")
        XCTAssertTrue(UpAwayArt.ready, "every Up & Away id is a generated UIArt case: the Release gate is open")
        #if DEBUG
        XCTAssertTrue(economy([:]).events.rotation.unavailable.isEmpty, "a DEBUG build runs Up & Away with placeholders")
        #endif
        // what the gate does to the calendar: Up & Away's weeks run Treasure Climb, the race slot is untouched
        var r = economy([:])
        r.events.rotation.unavailable = ["balloonRise"]
        XCTAssertEqual(EventRotation.live(week: 22, level: 60, rules: r.events).ladder, .clawChallenge)
        XCTAssertEqual(EventRotation.live(week: 22, level: 60, rules: r.events).race, [.rocketRace, .skyJump])
    }

    func testTheStripAndPageMotionConstants() {
        // the strip slides one step (39 pt, 0.77 s ease-in-out from +0.18 s, VERIFIED v582)
        XCTAssertEqual(BalloonStrip.step, 39)
        XCTAssertEqual(BalloonStrip.slideStart, 0.18)
        XCTAssertEqual(BalloonStrip.slideDuration, 0.77)
        XCTAssertEqual(SocBalloonPage.easeInOut(0), 0)
        XCTAssertEqual(SocBalloonPage.easeInOut(0.5), 0.5, accuracy: 1e-12)
        XCTAssertEqual(SocBalloonPage.easeInOut(1), 1)
    }

    func testThePageGeometryPlacesTheMilestonesInOrder() {
        let geo = BalloonTrackGeometry(platforms: EventRules.BalloonRise().platforms.map(\.at))
        XCTAssertEqual(geo.y(count: 0), geo.groundY)
        XCTAssertEqual(geo.groundY - geo.y(count: 1), 47, accuracy: 0.001, "≈ 47 pt per step at the tower's foot (VERIFIED)")
        XCTAssertEqual(geo.y(count: 2), geo.y(platform: 0))
        XCTAssertEqual(geo.y(count: 120), geo.y(platform: 9))
        var last = CGFloat.greatestFiniteMagnitude
        for c in stride(from: 0.0, through: 130, by: 0.5) {
            let y = geo.y(count: c)
            XCTAssertLessThanOrEqual(y, last, "the balloon never sinks as the count grows (\(c))")
            XCTAssertGreaterThan(y, 0)
            last = y
        }
    }

    func testTheNotificationPlanCarriesTheEventNotifications() throws {
        let tuning = Tuning.load(bundle: .main, tune: [:])
        let rules = economy([:])
        var s = PlayerState()
        s.level = 46
        s.settings.notifications = true
        let now = Date(timeIntervalSince1970: 1_790_578_800 + 3 * 86_400)             // Thursday of week 22 (Up & Away + Double)
        s.level = 47
        _ = Events.onWin(&s, WinContext(levels: [46], tag: .normal, firstTry: true, now: now),
                         rivals: SocialWorld(installSeed: 7, config: .default, names: NameBank()), rules: rules)
        let trt = try XCTUnwrap(TimeZone(identifier: "Europe/Istanbul"))
        let p = LocalNotifications.plan(s, now: now, rules: rules, tuning: tuning.game, zone: trt)
        XCTAssertNil(p.weeklyEndingIn, "L47: no Weekly Cup")
        XCTAssertEqual(p.events.map(\.kind), [.eventEnding, .eventStart])
        for it in p.events {
            XCTAssertTrue(EventNotifications.inWindow(it.at, zone: trt, window: [10, 21]), "\(it)")
            XCTAssertFalse(LocalNotifications.body(it).isEmpty)
        }
        XCTAssertEqual(LocalNotifications.body(p.events[0]), String(localized: "\(String(localized: "Up & Away")) ends soon!"))
        XCTAssertTrue(LocalNotifications.body(p.events[1]).hasPrefix(String(localized: "Treasure Climb")), LocalNotifications.body(p.events[1]))
        XCTAssertGreaterThanOrEqual(p.events[1].at - p.events[0].at, 86_400, "one per 24 h")
        s.settings.notifications = false
        XCTAssertEqual(LocalNotifications.plan(s, now: now, rules: rules, tuning: tuning.game, zone: trt), .init())
        // the rotation off (v552 plan): no event notifications
        let off = economy(["pc.uitest": "1"])
        s.settings.notifications = true
        XCTAssertEqual(LocalNotifications.plan(s, now: now, rules: off, tuning: tuning.game, zone: trt).events, [],
                       "the v552 plan announces nothing: next week = this week")
    }

    func testTheEndedEventsAreHeldUnderTheShippedRotationOnly() {
        // B1b (v582 PH-0a): the shipped social.json runs the rotation, so at the roll an ended event the player took part in is
        // held ("Finished", its final numbers) until its result is opened; the UI tests' v552 plan holds nothing (every
        // existing suite keeps its meaning)
        let shippedRules = economy([:])
        var s = Economy.freshState(installSeed: 7, installDate: Date(timeIntervalSince1970: 1_790_000_000), rules: shippedRules)
        s.level = 60
        s.events.claw = ClawState(week: 23, points: 537, step: 11)
        s.events.streakRace = ContestState(index: 167, joinedAt: SocialTime(seconds: 1_791_702_600), score: 12)
        let roll = Date(timeIntervalSince1970: 1_791_788_400)                    // Mon 2026-10-12 07:00 UTC: week 23 → 24
        XCTAssertTrue(Events.status(s, now: roll - 1, rules: shippedRules).finished.isEmpty, "not before the roll")
        let shipped = Events.status(s, now: roll, rules: shippedRules)
        XCTAssertEqual(shipped.finished.claw?.points, 537)
        XCTAssertEqual(shipped.finished.claw?.target, 800, "the bar keeps \"537/800\" (step 12)")
        XCTAssertEqual(shipped.finished.ladder, .clawChallenge)
        XCTAssertEqual(shipped.finished.streakRace?.score, 12)
        XCTAssertEqual(EventBadgeKind.visible(shipped).first, .streakRace, "the Hot Streak badge stays (reading Finished)")
        XCTAssertNotNil(shipped.balloon, "this week's Up & Away is computed; the home shows it once the Finished bar is opened")
        XCTAssertTrue(Events.status(s, now: roll, rules: economy(["pc.uitest": "1"])).finished.isEmpty, "the v552 plan: no hold")
    }

    func testTheAnnounceKeysAreOnePerEventAndKind() {
        XCTAssertEqual(EventAnnounce.weekStartKey(.balloonRise, week: 22), "weekStart-balloonRise-22")
        XCTAssertEqual(EventAnnounce.openedKey(.rocketRace, week: 23), "opened-rocketRace-23")
        XCTAssertEqual(EventNames.name(.balloonRise).key, "Up & Away")
        XCTAssertEqual(EventNames.name(.clawChallenge).key, "Treasure Climb")
        XCTAssertEqual(EventNames.name(.skyJump).key, "Cloud Hop")
    }
}
