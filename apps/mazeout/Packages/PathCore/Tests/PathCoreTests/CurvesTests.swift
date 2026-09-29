import XCTest
import CoreGraphics
import PathCore

/// C1 (SPEC-architecture §4.16, §4.17): every motion curve at its measured sample points (per clip, from
/// Tests/Fixtures/c1_motion_samples.json), plus the shape facts the analyst stated.
final class CurvesTests: XCTestCase {
    private static var report: [String] = []

    override class func tearDown() {
        C1Fixtures.evidence("curves.txt", report.joined(separator: "\n") + "\n")
        super.tearDown()
    }

    private func check(_ key: String, file: StaticString = #filePath, line: UInt = #line, _ f: (Double) -> Double) {
        CurvesTests.report += C1Motion.check(key, file: file, line: line, f)
    }

    func testExitColourRamp() {
        check("exit_colour") { Curves.exitColour($0) }
        XCTAssertEqual(Timing.exitColourRamp, 0.11)
        XCTAssertEqual(Curves.exitColour.duration, Timing.exitColourRamp)
        XCTAssertEqual(Curves.exitColour(0), 0)
        XCTAssertEqual(Curves.exitColour(-0.01), 0)
        XCTAssertEqual(Curves.exitColour(0.11), 1)
        XCTAssertGreaterThan(Curves.exitColour(0.09), 0.96, "97 % by 0.09 s (colourramp P01)")
        XCTAssertEqual(Curves.exitColour(0.5), 1)
        // Ease-out: the first moved frame (≈ 1/60 s) is already ≈ 30 % of the way (a line would be 17 %).
        XCTAssertGreaterThan(Curves.exitColour(1.0 / 60), 0.28)
    }

    func testRipple() {
        check("ripple_radius") { Curves.ripple($0).radius }
        check("ripple_lum") { Curves.ripple($0).luminance }
        XCTAssertTrue(Curves.ripple(0).visible)
        XCTAssertEqual(Curves.ripple(0).radius, 11)
        XCTAssertEqual(Curves.ripple(0).luminance, 180)
        XCTAssertTrue(Curves.ripple(0.2333).visible)
        XCTAssertFalse(Curves.ripple(0.25).visible, "gone after 0.25 s (every clip)")
        XCTAssertFalse(Curves.ripple(-0.01).visible)
    }

    func testBump() {
        let b = Curves.bump
        check("bump_out") { b.outDuration(contactCells: $0) }
        check("bump_mark") { b.markRed($0) }
        check("bump_blocker") { b.blockerRed($0) }
        check("bump_badge_alpha") { b.badge($0).alpha }
        // Constant speed out, ease-out back over 0.14 s, then rest.
        let c = 3.58, tOut = b.outDuration(contactCells: c)
        XCTAssertEqual(b.travel(0, contactCells: c), 0)
        XCTAssertEqual(b.travel(tOut / 2, contactCells: c), c / 2, accuracy: 1e-12)
        XCTAssertEqual(b.travel(tOut, contactCells: c), c, accuracy: 1e-12)
        XCTAssertEqual(b.travel(tOut + 0.07, contactCells: c), c * 0.25, accuracy: 1e-9, "outQuad half-way: 25 % left")
        XCTAssertEqual(b.travel(tOut + 0.14, contactCells: c), 0, accuracy: 1e-12)
        XCTAssertEqual(b.travel(tOut + 1, contactCells: c), 0, accuracy: 1e-12)
        XCTAssertEqual(b.duration(contactCells: c), tOut + 0.14, accuracy: 1e-12)
        // bump-1's measured speed: 21.8 cells/s.
        XCTAssertEqual(c / tOut, 21.8, accuracy: 0.6)
        // The marked red stays; the blocker returns to black by 0.333; the badge is gone by 0.433.
        XCTAssertEqual(b.markRed(5), 1)
        XCTAssertEqual(b.blockerRed(0.34), 0)
        XCTAssertFalse(b.badge(0.44).visible)
        XCTAssertFalse(b.badge(0.01).visible)
        XCTAssertEqual(b.badge(0.017).scale, 1.4, accuracy: 1e-9)
        XCTAssertEqual(b.badge(0.2).scale, 1.0, accuracy: 1e-9)
        XCTAssertEqual(b.badge(0.43).scale, 0.5, accuracy: 1e-9)
        XCTAssertEqual(b.red, "#EE0912")
    }

    func testVignette() {
        let v = Curves.vignette
        check("vignette_edge") { v.alpha($0, depth: 0) }
        check("vignette_depth") { v.alpha(0, depth: $0) }
        XCTAssertEqual(v.alpha(0.34, depth: 0), 0)
        XCTAssertEqual(v.alpha(-0.01, depth: 0), 0)
        XCTAssertEqual(v.duration, 0.333, accuracy: 1e-9)
        // Past the measured 45 pt the analyst's e^(−d/27) tail: small and decreasing, 0 by 130 pt.
        XCTAssertLessThan(v.alpha(0, depth: 60), v.alpha(0, depth: 45))
        XCTAssertEqual(v.alpha(0, depth: 200), 0, accuracy: 1e-9)
    }

    func testHeartBreak() {
        let h = Curves.heartBreak
        check("heart_break_dy") { h.dy($0) }
        XCTAssertEqual(-h.v0 / h.gravity, -0.1198, accuracy: 0.001, "the rise peaks at τ ≈ 0.12")
        XCTAssertEqual(h.dy(0.12), -6.9, accuracy: 0.2, "≈ 7 pt up")
        XCTAssertEqual(h.alpha(0.3), 1)
        XCTAssertEqual(h.alpha(0.35), 0.5, accuracy: 1e-9)
        XCTAssertEqual(h.alpha(0.4), 0)
        XCTAssertEqual(h.tilt(0.12), 25)
        XCTAssertEqual(h.spreadX(0.4), 15)
    }

    func testHUDIntro() {
        check("hud_drop") { Curves.hudDrop.value($0) }
        check("booster_slide") { Curves.boosterSlide.value($0) }
        // The quoted fit quality: RMS 2.20 / 1.18 pt.
        func rms(_ key: String, _ f: (Double) -> Double) -> Double {
            let g = C1Motion.samples[key] ?? []
            return (g.map { pow(f($0.t) - $0.v, 2) }.reduce(0, +) / Double(max(1, g.count))).squareRoot()
        }
        XCTAssertLessThanOrEqual(rms("hud_drop") { Curves.hudDrop.value($0) }, 2.3)
        XCTAssertLessThanOrEqual(rms("booster_slide") { Curves.boosterSlide.value($0) }, 1.25)
        // easeOutBack: overshoots, then lands exactly (no undershoot).
        XCTAssertEqual(Curves.hudDrop.value(Curves.hudDrop.end), 68.5, accuracy: 1e-9)
        XCTAssertGreaterThan(Curves.hudDrop.value(Curves.hudDrop.delay + 0.16), 100)
        XCTAssertEqual(Curves.hudDrop.value(0.5), -48.921)
        check("heart_pop") { Curves.heartPop($0) }
        check("heart_stagger") { Curves.heartPop.stagger[Int($0)] }
        check("big_timer") { Curves.bigTimer($0) }
        XCTAssertNil(Curves.heartPop.scaleAfterCut(1.40, element: 0))
        XCTAssertEqual(Curves.heartPop.scaleAfterCut(1.406, element: 0)!, 1.6163, accuracy: 1e-9)
        XCTAssertNil(Curves.heartPop.scaleAfterCut(1.406, element: 1))
        XCTAssertEqual(Curves.heartPop.scaleAfterCut(1.406 + 0.216 + 0.4, element: 2)!, 1.0, accuracy: 1e-9)
        XCTAssertEqual(Curves.heartPop(0.1333), 0.8868, accuracy: 1e-9, "the 0.89× undershoot")
    }

    func testIntroZoomAndBuildIn() {
        check("intro_zoom") { Curves.introZoom($0) }
        XCTAssertEqual(Curves.introZoom(0), 1.4931, accuracy: 1e-9)
        XCTAssertEqual(Curves.introZoom(1.3501), 1, accuracy: 1e-12)
        XCTAssertEqual(Curves.introZoom(5), 1)
        let b = Curves.buildIn
        check("build_in_t50") { b.t50(cells: Int($0)) }
        check("build_in_t98") { b.t98(cells: Int($0)) }
        for n in [2, 3, 6, 10, 17, 42] {
            XCTAssertEqual(b.fraction(b.t50(cells: n), cells: n), 0.5, accuracy: 1e-12)
            XCTAssertEqual(b.fraction(b.t98(cells: n), cells: n), 0.98, accuracy: 1e-12)
            XCTAssertEqual(b.fraction(b.duration(cells: n), cells: n), 1, accuracy: 1e-12)
            XCTAssertEqual(b.fraction(-0.01, cells: n), 0)
            XCTAssertLessThan(b.fraction(0, cells: n), 0.2, "a small first-frame jump, as introdraw2_L48")
        }
        // 3-cell ≈ 0.39 s, 10-cell ≈ 0.54 s (motion.md §6.1 "98 % drawn").
        XCTAssertEqual(b.t98(cells: 3), 0.39, accuracy: 0.01)
        XCTAssertEqual(b.t98(cells: 10), 0.54, accuracy: 0.01)
    }

    func testTutorialHandAndCaption() {
        let h = Curves.tutorial
        check("hand") { h.handScale($0) }
        check("caption_in") { h.captionScale($0) }
        XCTAssertEqual(h.handScale(0.4), 1)
        XCTAssertEqual(h.handScale(0.56 + 0.48), 0.5306, accuracy: 1e-9, "fully pressed")
        XCTAssertEqual(h.handScale(0.56 + 2.1), 1, accuracy: 1e-9, "the loop restarts")
        XCTAssertEqual(h.handScale(0.56 + 2.1 + 0.48), 0.5306, accuracy: 1e-9)
        XCTAssertEqual(h.captionOut(0.20), 0)
        XCTAssertEqual(h.handOutAlpha(0.16), 0)
        XCTAssertEqual(h.captionScale(0.08), 1.10, accuracy: 1e-9, "the overshoot")
        // The §4.16 names.
        for t in stride(from: 0.0, through: 3.0, by: 0.05) {
            XCTAssertEqual(Curves.captionPop(t), h.captionScale(t))
            XCTAssertEqual(Curves.handLoop(t), h.handScale(t))
        }
        XCTAssertEqual(Curves.handIn(0), 0.2449, accuracy: 1e-9)
        XCTAssertEqual(Curves.handIn(0.24), 1, accuracy: 1e-9)
    }

    func testUnlockOverlay() {
        let u = Curves.unlockOverlay
        check("unlock_icon") { u.icon.scale($0) ?? 0 }
        XCTAssertNil(u.icon.scale(0.25))
        XCTAssertNil(u.card.scale(0.77))
        XCTAssertEqual(u.title.scale(0.62)!, 1.1, accuracy: 1e-9)
        XCTAssertEqual(u.title.scale(0.66)!, 1)
        XCTAssertEqual(u.card.scale(0.94)!, 1)
        XCTAssertEqual(u.unlocked.scale(0.70)!, 1)
        XCTAssertEqual(u.sparklesFrom, 1.14)
        XCTAssertEqual(u.dismissFade, 0.25)
        // Staggered in the VERIFIED order: icon, title, "Unlocked!", card.
        XCTAssertLessThan(u.icon.start, u.title.start)
        XCTAssertLessThan(u.title.start, u.unlocked.start)
        XCTAssertLessThan(u.unlocked.start, u.card.start)
    }

    func testKeyFlight() {
        let k = Curves.keyFlight
        let to = CGPoint(x: 62.4 - 74.2, y: 592.4 - 448.6)            // the L33 keyhole, relative to the resting key
        check("key_flight_y") { Double(k.position($0, from: .zero, to: to).y) }
        check("key_burst") { _ in k.burst }
        XCTAssertEqual(Timing.doorBurstAfterTap, 1.14)
        XCTAssertEqual(k.position(0.1, from: .zero, to: to), .zero, "hangs where it was until the sag")
        XCTAssertEqual(Curves.keyFlight(0.7, from: .zero, to: to), k.position(0.7, from: .zero, to: to))
        XCTAssertEqual(k.position(2, from: .zero, to: to), to, "ends in the keyhole")
        XCTAssertEqual(k.diveEnd(from: .zero, to: to), 0.554 + ((2 * (143.8 + 32.5)) / 7650).squareRoot(), accuracy: 1e-9)
        XCTAssertLessThan(k.diveEnd(from: .zero, to: to), k.turnFrom)
        XCTAssertLessThan(k.turnTo, k.burst)
        XCTAssertEqual(k.scale(0.5, from: .zero, to: to), 1)
        XCTAssertEqual(k.scale(3, from: .zero, to: to), k.insertScale, accuracy: 1e-9)
        XCTAssertEqual(k.turn(k.turnTo), k.turnDegrees, accuracy: 1e-9)
        // A lock ABOVE the apex (a far door, clips-needed #14): a finite, ending dive.
        let up = CGPoint(x: 100, y: -200)
        XCTAssertEqual(k.position(k.diveStart + k.diveFallback + 0.01, from: .zero, to: up), up)
    }

    func testDebris() {
        check("box_shards_dy") { Curves.boxShards.dy($0) }
        let d = Curves.debris
        let apexT = d.popSpeed / d.gravity
        XCTAssertEqual(d.dy(apexT), -14, accuracy: 1e-9, "the door debris pops ≈ 14 pt up")
        XCTAssertEqual(d.alpha(0.5), 1)
        XCTAssertEqual(d.alpha(0.9), 0)
        XCTAssertEqual(Curves.boxShards.alpha(0.67), 0)
        XCTAssertEqual(Curves.pipeShards.life, 1.42)
    }

    func testWinBeatsAndClearWave() {
        let w = Curves.win
        check("win_dim") { w.dim($0) }
        check("win_panel") { _ in w.panel }
        XCTAssertEqual(Timing.winPanelAfterTrigger, w.panel)
        XCTAssertEqual(w.dim(1.0), 0)
        XCTAssertEqual(w.dim(3), 0.85)
        XCTAssertEqual(w.panel - (w.dimFrom + w.dimFor), 2.367, accuracy: 0.01, "dim complete → panel 2.36 s (motion.md §6.6)")
        let c = Curves.clearWave
        XCTAssertEqual(c.duration, 0.51, accuracy: 1e-9, "wave 0 → +0.51 s")
        XCTAssertEqual(c.light(0.06, rho: 0.14), 1, "centre dots lit at +0.06")
        XCTAssertEqual(c.light(0.41, rho: 0.98), 1, "the outer ring lit at +0.41")
        XCTAssertEqual(c.light(0.02, rho: 0.9), 0)
        for rho in stride(from: 0.0, through: 1.0, by: 0.1) { XCTAssertEqual(c.light(0.511, rho: rho), 0, accuracy: 1e-9) }
        XCTAssertLessThan(c.hue(rho: 0), c.hue(rho: 1))
    }

    func testCoinFlyAndTimings() {
        let f = Curves.coinFly
        XCTAssertEqual(f.increments(total: 120), [24, 24, 24, 24, 24])
        XCTAssertEqual(f.increments(total: 20), [4, 4, 4, 4, 4], "+20 in 5 steps of 4 (video-flows §6, motion.md §6.5)")
        XCTAssertEqual(f.increments(total: 23), [4, 4, 4, 4, 7])
        XCTAssertEqual((0..<5).map { f.pill(f.arrival($0), start: 1000, total: 120) }, [1024, 1048, 1072, 1096, 1120])
        XCTAssertEqual(f.pill(0, start: 3854, total: 20), 3854)
        XCTAssertEqual(f.arrival(1) - f.arrival(0), 0.10, accuracy: 1e-12, "≈ 0.1 s apart (v552)")
        XCTAssertEqual(f.arrival(0), 0.21, accuracy: 1e-12, "4.08 lift → 4.29 first arrival")
        XCTAssertEqual(f.duration, 0.61, accuracy: 1e-12, "4.08 → 4.69")
        XCTAssertEqual(Timing.stageGap, 0.7)
        XCTAssertEqual(Timing.pipeBreakAfterHeadLeaves, 0.05)
        XCTAssertEqual(Timing.playCutAfterClick, 0.06)
        XCTAssertEqual(Timing.buttonPressScale, 0.95)
    }

    func testCurvesAreDataAndRoundTrip() throws {
        // Every curve encodes and decodes to itself, and a partial override changes only what it names.
        func roundTrip<T: Codable & Equatable>(_ v: T) throws { XCTAssertEqual(try JSONDecoder().decode(T.self, from: JSONEncoder().encode(v)), v) }
        try roundTrip(Curves.exitColour); try roundTrip(Curves.ripple); try roundTrip(Curves.bump); try roundTrip(Curves.vignette)
        try roundTrip(Curves.buildIn); try roundTrip(Curves.introZoom); try roundTrip(Curves.clearWave); try roundTrip(Curves.keyFlight)
        try roundTrip(Curves.debris); try roundTrip(Curves.hudDrop); try roundTrip(Curves.bigTimer); try roundTrip(Curves.heartBreak)
        try roundTrip(Curves.unlockOverlay); try roundTrip(Curves.tutorial); try roundTrip(Curves.win); try roundTrip(Curves.coinFly)
        try roundTrip(TimingTable.measured); try roundTrip(ArrowMetrics.style); try roundTrip(ExitKinematics.measured)
        let slower = try Curves.exitColour.overridden(by: Data("{\"duration\": 0.2}".utf8))
        XCTAssertEqual(slower.duration, 0.2)
        XCTAssertEqual(slower.power, 2)
        let bump = try Curves.bump.overridden(by: Data("{\"back\": 0.2, \"badgeScale\": {\"t\": [0, 1], \"v\": [2, 1]}}".utf8))
        XCTAssertEqual(bump.back, 0.2)
        XCTAssertEqual(bump.badgeScale(0), 2)
        XCTAssertEqual(bump.outBase, 0.075)
        let unlock = try Curves.unlockOverlay.overridden(by: Data("{\"card\": {\"peakScale\": 1.2}}".utf8))
        XCTAssertEqual(unlock.card.peakScale, 1.2)
        XCTAssertEqual(unlock.card.start, 0.78, "nested objects merge")
        XCTAssertEqual(Curves.bump.unknownKeys(in: Data("{\"back\": 1, \"shake\": 2, \"_note\": 3}".utf8)), ["shake"])
        let style = try ArrowMetrics.style.overridden(by: Data("{\"apexUp\": 0.39}".utf8))
        XCTAssertEqual(style.apexPast(.up), 0.39)
        XCTAssertEqual(style.apexPast(.down), 0.435)
        XCTAssertThrowsError(try JSONDecoder().decode(KeyTrack.self, from: Data("{\"t\": [1, 0], \"v\": [0, 1]}".utf8)))
        XCTAssertThrowsError(try JSONDecoder().decode(KeyTrack.self, from: Data("{\"t\": [0, 1], \"v\": [0]}".utf8)))
    }
}
