import XCTest

/// SHELL S1 (SPEC-architecture §12.2 S1, §9.7 rules: base arguments, anchored predicates, no sleeps for animations).
/// - Pause / Quit Level? / Settings open through `-pc.popup` with their controls and answer;
/// - the Settings toggles survive a relaunch (PlayerState; the store is proven file-only by ShellTests);
/// - home shows the next level on Play and the plate, the nav tabs switch, the gear opens Settings.
final class ShellUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }

    func testPausePopupOpensWithItsControlsAndCloses() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "32", "-pc.go", "level", "-pc.popup", "pause"])
        let popup = app.element("popup.pause")
        XCTAssertTrue(popup.waitForExistence(timeout: 12), app.debugDescription)
        XCTAssertTrue(app.element("popup.pause.primary").exists)
        XCTAssertTrue(app.element("popup.pause.secondary").exists)
        XCTAssertEqual(app.element("pause.toggle.sound").value as? String, "on")
        XCTAssertEqual(app.element("pause.toggle.haptic").value as? String, "on")
        app.element("popup.pause.close").tap()
        XCTAssertTrue(popup.waitForNonExistence(timeout: 3), app.debugDescription)
    }

    func testQuitLevelPopupAnswersQuit() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "32", "-pc.go", "level", "-pc.popup", "quitLevel"])
        let popup = app.element("popup.quitLevel")
        XCTAssertTrue(popup.waitForExistence(timeout: 12), app.debugDescription)
        XCTAssertTrue(app.element("popup.quitLevel.close").exists)
        XCTAssertTrue(app.element("popup.quitLevel.message").exists)
        app.element("popup.quitLevel.primary").tap()
        XCTAssertTrue(popup.waitForNonExistence(timeout: 3), app.debugDescription)
    }

    func testSettingsTogglesPersistAcrossARelaunch() {
        var app = AppUnderTest.launch(["-pc.reset", "1", "-pc.go", "settings"])
        XCTAssertTrue(app.element("popup.settings").waitForExistence(timeout: 12), app.debugDescription)
        for id in ["settings.toggle.sound", "settings.toggle.haptic", "settings.toggle.notifications"] {
            XCTAssertEqual(app.element(id).value as? String, "on", id)
        }
        // SPEC-motion-audio MA2: the Music button is inert and shows OFF; a tap changes nothing
        XCTAssertEqual(app.element("settings.toggle.music").value as? String, "off")
        app.element("settings.toggle.music").tap()
        app.element("settings.toggle.sound").tap()
        app.element("settings.toggle.haptic").tap()
        app.element("settings.toggle.notifications").tap()
        XCTAssertTrue(app.element("settings.toggle.sound").wait(for: "value == %@", "off"), app.debugDescription)
        XCTAssertTrue(app.element("settings.toggle.haptic").wait(for: "value == %@", "off"))
        XCTAssertTrue(app.element("settings.toggle.notifications").wait(for: "value == %@", "off"))
        XCTAssertEqual(app.element("settings.toggle.music").value as? String, "off")

        app = AppUnderTest.launch(["-pc.go", "settings"])                 // no reset: the saved PlayerState loads
        XCTAssertTrue(app.element("popup.settings").waitForExistence(timeout: 12), app.debugDescription)
        XCTAssertEqual(app.element("settings.toggle.sound").value as? String, "off")
        XCTAssertEqual(app.element("settings.toggle.haptic").value as? String, "off")
        XCTAssertEqual(app.element("settings.toggle.notifications").value as? String, "off")
        XCTAssertEqual(app.element("settings.toggle.music").value as? String, "off")
        app.element("settings.toggle.notifications").tap()
        XCTAssertTrue(app.element("settings.toggle.notifications").wait(for: "value == %@", "on"))

        app = AppUnderTest.launch(["-pc.level", "32", "-pc.go", "level", "-pc.popup", "pause"])   // Pause reads the same settings
        XCTAssertTrue(app.element("popup.pause").waitForExistence(timeout: 12), app.debugDescription)
        XCTAssertEqual(app.element("pause.toggle.sound").value as? String, "off")
        XCTAssertEqual(app.element("pause.toggle.haptic").value as? String, "off")
        app.element("pause.toggle.sound").tap()
        XCTAssertTrue(app.element("pause.toggle.sound").wait(for: "value == %@", "on"))
    }

    func testSettingsOfflinePagesOpenAndClose() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.go", "settings"])
        XCTAssertTrue(app.element("popup.settings").waitForExistence(timeout: 12), app.debugDescription)
        for page in ["terms", "privacy", "support"] {
            app.element("settings.\(page)").tap()
            let container = app.element("popup.page.\(page)")
            XCTAssertTrue(container.waitForExistence(timeout: 3), app.debugDescription)
            app.element("page.\(page).close").tap()
            XCTAssertTrue(container.waitForNonExistence(timeout: 3), app.debugDescription)
        }
        app.element("popup.settings.close").tap()
        XCTAssertTrue(app.element("popup.settings").waitForNonExistence(timeout: 3), app.debugDescription)
    }

    func testHomeShowsTheNextLevelAndSwitchesTabs() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "34", "-pc.go", "home"])
        let play = app.element("home.play")
        XCTAssertTrue(play.waitForExistence(timeout: 12), app.debugDescription)
        XCTAssertEqual(play.value as? String, "34")
        XCTAssertTrue(app.element("home.level").exists)
        XCTAssertEqual(app.element("home.coins").value as? String, "1000")
        XCTAssertEqual(app.element("home.lives").value as? String, "full")
        XCTAssertEqual(app.element("nav.home").value as? String, "selected")
        app.element("home.settings").tap()
        XCTAssertTrue(app.element("popup.settings").waitForExistence(timeout: 3), app.debugDescription)
        app.element("popup.settings.close").tap()
        XCTAssertTrue(app.element("popup.settings").waitForNonExistence(timeout: 3))
        app.element("nav.leaderboard").tap()
        XCTAssertTrue(app.element("nav.leaderboard").wait(for: "value == %@", "selected"), app.debugDescription)
        app.element("nav.home").tap()
        XCTAssertTrue(app.element("home.play").waitForExistence(timeout: 3))
    }

    /// FIX-2 A (V3-06): the keyboard warm-up behind Loading (RootView `KeyboardWarm`: an off-screen field becomes first
    /// responder and resigns in one run-loop turn) never puts a keyboard on screen — not while Loading is up, not on home.
    /// (ShellS3UITests' username round trip types into the real field afterwards: the warm-up leaves input working.)
    /// FIX-2 A-R (review-A: "no positive control"): the checks are only meaningful when (1) the warm-up really made its field
    /// first responder in this process (`warmup.keyboard` = "warmed"), and (2) a keyboard that DOES come up is visible to
    /// `app.keyboards` in this simulator setup (a connected hardware keyboard hides the on-screen one): the same test then
    /// focuses the real Username field and requires the keyboard to appear. If either fails, the "none" checks proved nothing.
    func testTheKeyboardWarmUpShowsNoKeyboard() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "34", "-pc.go", "home"])
        if app.element("screen.loading").waitForExistence(timeout: 10) {
            XCTAssertEqual(app.keyboards.count, 0, "no keyboard over Loading")
        }
        XCTAssertTrue(app.element("home.play").waitForExistence(timeout: 12), app.debugDescription)
        let warm = app.element("warmup.keyboard")
        XCTAssertTrue(warm.waitForExistence(timeout: 5), "the warm-up ran in this process: \(app.debugDescription)")
        XCTAssertEqual(warm.value as? String, "warmed", "its field became first responder")
        XCTAssertEqual(app.keyboards.count, 0, "no keyboard on home after the warm-up")
        XCTAssertFalse(app.keyboards.firstMatch.waitForExistence(timeout: 1.5), "none appears later either")
        // positive control: a real focus in this setup shows a keyboard that `app.keyboards` sees
        let named = AppUnderTest.launch(["-pc.state", AppUnderTest.state(#"{"level":62,"coins":4214,"homeSeen":true}"#),
                                         "-pc.go", "profile", "-pc.askName", "1"])
        let field = named.element("username.field")
        XCTAssertTrue(field.waitForExistence(timeout: 20), named.debugDescription)
        XCTAssertEqual(named.keyboards.count, 0, "no keyboard before the field is focused")
        field.tap()
        XCTAssertTrue(named.keyboards.firstMatch.waitForExistence(timeout: 5),
                      "POSITIVE CONTROL: a focused field shows a keyboard app.keyboards can see (else the checks above prove nothing)")
    }

    /// FIX-2 A-R (review-A BLOCKER): the win panel's hidden warm copy (RootView `PopupWarm`, drawn at W+2.6) ran the panel's
    /// appearance code, which hands the celebration's dim over — the board went full-bright from W+2.6 until the real panel at
    /// W+4.03 on every real win. A REAL win (autoplay; a `-pc.win` win draws no warm copy): from the moment the dim is up
    /// (≥ 0.85, W+1.7) until `popup.win` exists, every sample of `shell.warmProbe` (computed when queried) must show the dim
    /// still up — and the probe must show that a warm copy WAS drawn during that stretch (else the test proved nothing).
    func testTheWinPanelsWarmCopyLeavesTheCelebrationDimUp() {
        let st = AppUnderTest.state(#"{"level":20,"coins":5000,"homeSeen":true,"flags":{"ratingPromptShown":true,"notificationPromptShown":true,"weeklyIntroSeen":true,"seen":["clawIntro"]}}"#)
        // the bot answers popups after `autoplay.popupDelay` (0.6 s): held 30 s here, so the real panel stays up to be seen
        let app = AppUnderTest.launch(["-pc.state", st, "-pc.go", "level", "-pc.level", "20", "-pc.tutorials", "skip",
                                       "-pc.hearts", "9", "-pc.autoplay", "1", "-pc.tune", "game.autoplay.popupDelay=30"])
        let probe = app.element("shell.warmProbe")
        XCTAssertTrue(probe.waitForExistence(timeout: 20), app.debugDescription)
        func read() -> (dim: Double?, warms: Int, mounted: Bool) {
            let v = (probe.value as? String) ?? ""
            var d: Double?, w = 0, m = false
            for part in v.split(separator: " ") {
                let kv = part.split(separator: "=", maxSplits: 1).map(String.init)
                guard kv.count == 2 else { continue }
                switch kv[0] {
                case "dim": d = Double(kv[1])
                case "warms": w = Int(kv[1]) ?? 0
                case "mounted": m = kv[1] == "1"
                default: break
                }
            }
            return (d, w, m)
        }
        // the real win's dim comes up (autoplay clears L20 in ≈ 15-25 s)
        let upBy = Date().addingTimeInterval(90)
        var s = read()
        while !((s.dim ?? 0) >= 0.85), Date() < upBy { RunLoop.current.run(until: Date().addingTimeInterval(0.1)); s = read() }
        XCTAssertGreaterThanOrEqual(s.dim ?? 0, 0.85, "the celebration's dim came up: \(probe.value ?? "-")")
        let warmsBefore = s.warms
        let panel = app.element("popup.win")
        // every sample from the dim's arrival to the panel; the ones AFTER the warm copy was drawn (W+2.6 … W+4.03) decide
        var afterWarm = 0, minDim = 1.0, log: [String] = []
        let end = Date().addingTimeInterval(8)
        while !panel.exists, Date() < end {
            let r = read()
            // the real panel hands the dim over on its first frame: a low sample taken as it arrives is not the copy's doing
            if let d = r.dim, d < 0.85, panel.waitForExistence(timeout: 0.3) { break }
            log.append("\(r.dim.map { String(format: "%.2f", $0) } ?? "-")/\(r.warms)")
            if r.warms > warmsBefore || r.mounted {
                afterWarm += 1
                if let d = r.dim { minDim = min(minDim, d) }
            }
        }
        XCTAssertTrue(panel.waitForExistence(timeout: 5), "the real panel came: \(app.debugDescription)")
        XCTAssertGreaterThan(afterWarm, 0,
                             "POSITIVE CONTROL: samples taken after the panel's warm copy was drawn (dim/warms: \(log))")
        XCTAssertGreaterThanOrEqual(minDim, 0.85, "the dim stayed up until the real panel (dim/warms samples: \(log))")
    }

    /// FIX-2 A-R (review-A): the win panel's hidden warm copy (RootView `PopupWarm`, drawn at W+2.6 until the real panel at W+4.03)
    /// is out of the accessibility tree — with `accessibilityHidden(true)` on its root, `win.continue`, `win.close`, `win.reward`
    /// and `popup.variant` (own identifiers) stayed queryable, by XCUITest and VoiceOver. `-pc.popupWarm win` holds a copy over
    /// home; `popupWarm.mounted` proves it is there while none of its elements can be found; then the REAL panel
    /// (`-pc.popup win` after 8 s) shows the same queries do find them.
    func testTheHiddenWinPanelCopyIsOutOfTheAccessibilityTree() {
        let app = AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "34", "-pc.go", "home", "-pc.popupWarm", "win",
                                       "-pc.popup", "win", "-pc.popupDelay", "8"])
        XCTAssertTrue(app.element("home.play").waitForExistence(timeout: 12), app.debugDescription)
        let mounted = app.element("popupWarm.mounted")
        XCTAssertTrue(mounted.waitForExistence(timeout: 5), "the warm copy is mounted: \(app.debugDescription)")
        XCTAssertEqual(mounted.value as? String, "win")
        for id in ["win.continue", "win.close", "win.reward", "popup.variant"] {
            XCTAssertFalse(app.element(id).exists, "\(id) of the hidden copy is not in the accessibility tree: \(app.debugDescription)")
        }
        XCTAssertFalse(app.element("popup.win").exists, "the real panel is not up yet (the checks above saw the copy alone)")
        // positive control: the real panel's elements ARE found by the same queries
        XCTAssertTrue(app.element("popup.win").waitForExistence(timeout: 15), app.debugDescription)
        XCTAssertTrue(app.element("win.continue").waitForExistence(timeout: 5), app.debugDescription)
        XCTAssertTrue(app.element("win.reward").exists)
    }
}
