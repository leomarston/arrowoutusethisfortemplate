import XCTest

/// LOGO-IMPL (build/logo/LOGO-SPEC.md §7 A6) re-stated by A2 FEEL-P as a REQUIREMENT CHANGE (ruling 40 = v582, measured on the owner's
/// phone, motion-catalog §11.4; supersedes D9's "skip from W + 0.41", which let the owner skip mid-animation): every tap is ignored
/// until the logo has landed (W + 1.70), then a tap cuts to the win panel at once. The celebration runs slowed ten times
/// (`-pc.slowmo 10`: the game clock and the FX host's layer time both run at 1/10), so each tap lands at a known moment of the
/// sequence without a timing race: a tap right after W (≈ W + 0.05…0.2 game s) and a tap at ≈ W + 1.3 (OUT! at its peak, the
/// tap v582 ignored) are both ignored — the catcher stays "waiting" and no panel comes while the clock runs on to ≈ W + 1.65 —
/// and a tap after the catcher arms (W + 1.70) skips at once to the win panel, well before its own beat W + 4.034.
/// The absence of the panel is asserted over the whole wait (an inverted expectation), never slept through.
final class WinLogoUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    func testTapsAreIgnoredUntilTheLogoLandsThenATapSkips() {
        let state = AppUnderTest.state("{\"level\":32,\"coins\":2240,\"homeSeen\":true,\"events\":{\"streakStep\":1}}")
        let app = AppUnderTest.launch(["-pc.state", state, "-pc.go", "shelllab", "-pc.lab", "celebrate:normal", "-pc.slowmo", "10"])
        let skip = app.element("celebration.skip")
        XCTAssertTrue(skip.waitForExistence(timeout: 30), app.debugDescription)     // W: the catcher is up
        let w = Date()
        func game() -> Double { Date().timeIntervalSince(w) / 10 }                    // ≈ game seconds since W (+ the catcher's latency)
        let panel = app.element("popup.win")
        // 1. a tap right after W: ignored
        app.tap(screenX: 196, y: 600)
        XCTAssertLessThan(game(), 0.35, "the first tap must land right after W (it landed at ≈ W + \(game()))")
        XCTAssertEqual(skip.value as? String, "waiting", "a tap right after W does not arm or skip")
        // 2. no panel while the clock runs on to ≈ W + 1.3 (13 s of real time at 1/10); then a tap at OUT!'s peak: ignored too
        let noPanel = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true"), object: panel)
        noPanel.isInverted = true
        XCTAssertEqual(XCTWaiter().wait(for: [noPanel], timeout: max(1, 13 - Date().timeIntervalSince(w))), .completed,
                       "the early tap was ignored: no panel before the second tap")
        XCTAssertGreaterThan(game(), 1.2, "the second tap lands during OUT!'s peak (≈ W + \(game()))")
        app.tap(screenX: 196, y: 600)
        let second = game()
        XCTAssertLessThan(second, 1.60, "the second tap landed before the logo lands (≈ W + \(second))")
        XCTAssertEqual(skip.value as? String, "waiting", "a tap at ≈ W + 1.3 does not arm or skip (v582 ignores it)")
        let noPanel2 = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true"), object: panel)
        noPanel2.isInverted = true
        XCTAssertEqual(XCTWaiter().wait(for: [noPanel2], timeout: max(1, 16.5 - Date().timeIntervalSince(w))), .completed,
                       "the tap at ≈ W + 1.3 was ignored: no panel before the logo lands")
        // 3. armed once the logo has landed (W + 1.70), and not before W + 1.6
        XCTAssertTrue(skip.wait(for: "value == %@", "armed", timeout: 10), skip.debugDescription)
        XCTAssertGreaterThan(game(), 1.6, "armed only once the logo has landed (≈ W + \(game()))")
        // 4. a tap now cuts to the win panel at once
        app.tap(screenX: 196, y: 600)
        XCTAssertTrue(panel.waitForExistence(timeout: 5), "a tap after W + 1.70 skips to the win panel")
        XCTAssertLessThan(game(), 3.5, "well before the panel's own beat W + 4.034 (≈ W + \(game()))")
    }
}
