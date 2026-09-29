import XCTest
import SwiftUI
import UIKit
import PathCore
@testable import ArrowOut

/// SHELL S1 (SPEC-architecture §12.2 S1). Hosted checks of the shell foundation:
/// - the puppets' rest layers recompose each rig's full render (mean |Δ| ≤ 1/255, the art lane's proof re-run through
///   PuppetRig + PuppetStage's layer tree);
/// - GameText lays the measured labels out at fonts.md §5 sizes/tracking (ink widths against the tokens) and shrinks to fit
///   with the 0.7 floor;
/// - the settings toggles write PlayerState only (the save file changes; no UserDefaults key appears) and survive a reload;
/// - ShellMetrics maps the reference canvas (identity on 393 x 852, anchored offsets elsewhere, popups scale below 393 only);
/// - the popup host stacks, answers and falls back; the ui.json tokens cover the S1 screens (no compiled default used).
/// Evidence PNGs go to Documents/s1-evidence/ inside the simulator container.
@MainActor final class ShellTests: XCTestCase {

    // MARK: puppets

    func testPuppetRestPoseRecomposesTheFullRender() throws {
        var report: [String] = []
        // A4 ART-INTEG (R2 CAST's one mapping step, owner item 1): the D1 boss + Diggers replace the scientist + workers under
        // their own folder names; the same recompose bound (mean ≤ 1/255) holds for each
        for name in [HomeView.bossRig, HomeView.diggerLeftRig, HomeView.diggerRightRig] {
            let rig = try PuppetRig.load(name)
            XCTAssertFalse(rig.restLayers.isEmpty, name)
            let full = try XCTUnwrap(rig.fullPath.flatMap { ArtStore.image(path: $0)?.cgImage }, "\(name): full render in the bundle")
            let ours = try XCTUnwrap(PuppetView.renderRest(rig, scale: 3), name)
            XCTAssertEqual(ours.width, full.width, "\(name) width")
            XCTAssertEqual(ours.height, full.height, "\(name) height")
            let (mean, over40) = Self.diff(ours, full)
            report.append("\(name): mean |Δ| \(String(format: "%.3f", mean))/255, \(String(format: "%.3f", over40 * 100)) % px > 40")
            XCTAssertLessThanOrEqual(mean, 1.0, "\(name): the rest layers recompose the full render within 1/255")
            Self.save(ours, "puppet-rest-\(name).png")
        }
        print("[S1] puppet recompose: " + report.joined(separator: " · "))
        Self.saveText(report.joined(separator: "\n"), "puppet-recompose.txt")
    }

    func testPuppetRigDefaultsAndPivots() throws {
        let sci = try PuppetRig.load(HomeView.bossRig)                  // A4: the D1 rigs keep the old rigs' layer contract
        XCTAssertEqual(Set(sci.restLayers.map(\.name)), ["torso", "armL", "armR", "headSmile"])
        XCTAssertNotNil(sci.pivot("neck"))
        let left = try PuppetRig.load(HomeView.diggerLeftRig)
        XCTAssertNotNil(left.pivot("feet"))
        XCTAssertEqual(left.groups["eyes"]?.defaultMember, "eyes_open")
        XCTAssertTrue(left.restLayers.contains { $0.name == "eyes_open" })
        XCTAssertFalse(left.restLayers.contains { $0.name == "eyes_closed" })
        let right = try PuppetRig.load(HomeView.diggerRightRig)
        XCTAssertEqual(right.groups["eyes"]?.defaultMember, "eyes_half", "the right worker rests with half-closed eyes (rig.json)")
    }

    // MARK: GameText

    func testGameTextMeasuredLabels() {
        // fonts.md §5 size / tracking; the face ink width against the measured ink boxes (design/ui-tokens.json textStyles
        // ink_pt on shots 007, 026 and the Loading frame) within 3 %.
        let cases: [(String, CGFloat, CGFloat, CGFloat)] = [("Paused", 49.2, -1.0, 165.1), ("Play", 48.8, -3.25, 92.4),
                                                            ("Resume", 27.2, -1.0, 96.4), ("Quit", 30.5, -0.5, 62.4),
                                                            ("Loading", 26.8, -0.5, 100.1), ("Sound", 25.5, 0, 77.1)]
        var lines: [String] = []
        for (text, size, tracking, ink) in cases {
            let l = GameTextLayout.make(text, postScriptName: GameText.blackPostScript, size: size, tracking: tracking)
            XCTAssertEqual(l.runFonts, [GameText.blackPostScript], "\(text) draws in PCDisplay-Black only")
            XCTAssertEqual(l.glyphCount, text.count)
            lines.append("\(text) \(size)/\(tracking): face ink \(String(format: "%.1f", l.inkBounds.width)) pt (token ink \(ink))")
            XCTAssertEqual(l.inkBounds.width, ink, accuracy: ink * 0.03, "\(text) ink width vs the measured label")
        }
        print("[S1] GameText: " + lines.joined(separator: " · "))
        Self.saveText(lines.joined(separator: "\n"), "gametext-widths.txt")
    }

    func testGameTextShrinksToFitWithTheFloor() {
        let full = GameTextLayout.make("Resume", postScriptName: GameText.blackPostScript, size: 30.5, tracking: -1.0)
        let fit = GameTextLayout.make("Resume", postScriptName: GameText.blackPostScript, size: 30.5, tracking: -1.0, maxWidth: 100)
        XCTAssertGreaterThan(full.advance, 100)
        XCTAssertLessThanOrEqual(fit.advance, 100.01)
        XCTAssertEqual(fit.fontSize, 27.2, accuracy: 0.2, "Resume auto-sizes to the measured 27.2 pt (fonts.md §5)")
        let floor = GameTextLayout.make("Bir can kaybedeceksin! Bir can kaybedeceksin!", postScriptName: GameText.blackPostScript,
                                        size: 25, tracking: 0, maxWidth: 100, minScale: 0.7)
        XCTAssertEqual(floor.fontSize, 25 * 0.7, accuracy: 0.01, "never below 0.7")
    }

    func testGameTextRendersOutlineOutsideTheFace() throws {
        let style = GameTextStyle(size: 49.2, tracking: -1.0, fill: [.white], outline: Color(hex: 0x7B1D01), outlineWidth: 1.87,
                                  drop: 3.15, band: Color(hex: 0xFFD699), bandDY: 1.5)
        let r = ImageRenderer(content: GameText(verbatim: "Paused", style: style).background(Color(hex: 0xFFC400)))
        r.scale = 3
        let img = try XCTUnwrap(r.cgImage)
        let (white, dark) = Self.count(img) { p in (p.r > 250 && p.g > 250 && p.b > 250) } _: { p in (p.r > 100 && p.r < 140 && p.g < 45 && p.b < 20) }
        XCTAssertGreaterThan(white, 3000, "white face")
        XCTAssertGreaterThan(dark, 1500, "#7B1D01 outline + drop")
        Self.save(img, "gametext-paused.png")
        let play = ImageRenderer(content: GameText(verbatim: "Play", style: GameTextStyle(size: 48.8, tracking: -3.25,
                                                                                          fill: [Color(hex: 0xF1FFF2)],
                                                                                          outline: Color(hex: 0x066A01),
                                                                                          outlineWidth: 2.2, drop: 2.2))
                                    .background(Color(hex: 0x00D300)))
        play.scale = 3
        Self.save(try XCTUnwrap(play.cgImage), "gametext-play.png")
    }

    // MARK: settings persist in PlayerState, never UserDefaults

    func testSettingsTogglesWritePlayerStateOnly() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("s1-settings-\(UUID().uuidString)")
        let before = Set(UserDefaults.standard.dictionaryRepresentation().keys)
        let store = PlayerStore(args: LaunchArgs(), now: Date(), directory: dir, debounce: 0.05)
        XCTAssertTrue(store.state.settings.sound)
        let audio = RecordingAudio(), haptics = RecordingHaptics()
        XCTAssertFalse(ShellSettings.toggle(store: store, audio: audio, haptics: haptics, \.sound, name: "sound"))
        XCTAssertFalse(ShellSettings.toggle(store: store, audio: audio, haptics: haptics, \.haptic, name: "haptic"))
        XCTAssertFalse(ShellSettings.toggle(store: store, audio: audio, haptics: haptics, \.music, name: "music"))
        XCTAssertFalse(ShellSettings.toggle(store: store, audio: audio, haptics: haptics, \.notifications, name: "notifications"))
        store.flush()
        XCTAssertEqual(audio.applied.last?.sound, false, "the SFX bus follows at once")
        XCTAssertEqual(haptics.enabled, false, "the haptics gate follows at once")
        let saved = try PlayerStore.decode(Data(contentsOf: store.fileURL))
        XCTAssertEqual(saved.settings, PlayerState.Settings(sound: false, music: false, haptic: false, notifications: false))
        // a "relaunch": a new store on the same directory loads the toggles from player.json
        let again = PlayerStore(args: LaunchArgs(), now: Date(), directory: dir)
        XCTAssertEqual(again.loadSource, .primary)
        XCTAssertFalse(again.state.settings.sound)
        XCTAssertFalse(again.state.settings.haptic)
        let added = Set(UserDefaults.standard.dictionaryRepresentation().keys).subtracting(before)
        XCTAssertTrue(added.filter { $0.lowercased().contains("sound") || $0.lowercased().contains("haptic")
                                      || $0.lowercased().contains("music") || $0.lowercased().contains("setting") }.isEmpty,
                      "no settings key in UserDefaults: \(added)")
        try? FileManager.default.removeItem(at: dir)
    }

    func testShellSourcesNeverUseUserDefaultsOrAppStorage() throws {
        // The shell's Swift sources travel in the test bundle? No: read them from the repo through #filePath.
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("App")
        var offenders: [String] = []
        for sub in ["Shell", "FX"] {
            let dir = root.appendingPathComponent(sub)
            guard let e = FileManager.default.enumerator(at: dir, includingPropertiesForKeys: nil) else { continue }
            for case let url as URL in e where url.pathExtension == "swift" {
                let text = (try? String(contentsOf: url, encoding: .utf8)) ?? ""
                let code = text.split(separator: "\n").map { line -> Substring in
                    guard let r = line.range(of: "//") else { return line }
                    return line[line.startIndex..<r.lowerBound]
                }.joined(separator: "\n")
                if code.range(of: #"UserDefaults\s*[.(]"#, options: .regularExpression) != nil || code.contains("@AppStorage") {
                    offenders.append(url.lastPathComponent)
                }
            }
        }
        XCTAssertEqual(offenders, [], "D11: no UserDefaults / @AppStorage in App/Shell or App/FX")
    }

    // MARK: layout

    func testShellMetricsMapping() {
        let ref = ShellMetrics()
        let r = CGRect(91.1, 628.2, 211.2, 86.7)
        XCTAssertEqual(ref.rect(r, .top), r)
        XCTAssertEqual(ref.rect(r, .bottom), r)
        XCTAssertEqual(ref.rect(r, .centre), r)
        // a 375 x 812 phone (safe 44 / 34): x scales by W/393, top keeps the offset from the safe top, bottom from the safe bottom
        let small = ShellMetrics(size: CGSize(width: 375, height: 812), safeTop: 44, safeBottom: 34)
        let s = 375.0 / 393
        XCTAssertEqual(small.rect(CGRect(18.7, 36.7, 63.4, 61.4), .top).minY, 44 + (36.7 - 59) * s, accuracy: 0.001)
        XCTAssertEqual(small.rect(r, .bottom).maxY, 812 - 34 - (852 - 34 - (628.2 + 86.7)) * s, accuracy: 0.001)
        XCTAssertEqual(small.popupScale, min(375.0 / 393, 812.0 / 852), accuracy: 1e-9, "popups scale below 393 pt")
        let big = ShellMetrics(size: CGSize(width: 440, height: 956), safeTop: 62, safeBottom: 34)
        XCTAssertEqual(big.popupScale, 1, "no upscale above 393 pt (SPEC.md §5 item 14)")
        XCTAssertEqual(big.playRect(top: 122, bottom: 755).minY, 62 + (122 - 59) * 440 / 393, accuracy: 0.001)
    }

    // MARK: popups

    func testPopupHostStacksAnswersAndFallsBack() async {
        let host = PopupHost(ui: Tuning.defaults.ui)
        XCTAssertFalse(host.isPresenting)
        async let pause: PopupResult = host.present(Popup<PopupResult>.pause)
        for _ in 0..<200 where host.topID != .pause { await Task.yield() }
        XCTAssertEqual(host.topID, .pause)
        async let settings: PopupResult = host.present(Popup<PopupResult>.settings)
        for _ in 0..<200 where host.stack.count < 2 { await Task.yield() }
        XCTAssertEqual(host.stack.count, 2)
        XCTAssertEqual(host.topID, .settings)
        host.answer(host.stack[1].id, PopupResult.close)
        let s = await settings
        XCTAssertEqual(s, .close)
        XCTAssertEqual(host.topID, .pause)
        host.dismissAll()
        let p = await pause
        XCTAssertEqual(p, .primary, "dismissAll answers the fallback (pause → Resume)")
        XCTAssertFalse(host.isPresenting)
        XCTAssertEqual(host.dimAlpha(.standard), 0.90, accuracy: 1e-9)
        XCTAssertEqual(host.dimAlpha(.outOfTime), 0.94, accuracy: 1e-9)
    }

    /// A3 GLITCH (owner item 5, "for milliseconds other pages appear"): a hand-over is ATOMIC. An answered popup leaves the
    /// logical stack at once (its panel goes) but its dim stays drawn (no input) until its successor is committed — the next
    /// popup in the same transaction, the router's cut (`endBridge`), or `bridgeFrames` frames later when nothing follows. Before, the pop and
    /// the successor were committed on different run-loop turns and the level showed undimmed in between (blipscan).
    func testAnAnsweredPopupStaysDrawnUntilItsSuccessorIsCommitted() async {
        let host = PopupHost(ui: Tuning.load(bundle: .main).ui)             // the shipped ui.json: Quit Level? is a band
        // (1) Pause → Quit → Quit Level?: the successor replaces the answered popup in its own transaction
        let pause = Task { await host.present(Popup<PopupResult>.pause) }
        for _ in 0..<200 where host.topID != .pause { await Task.yield() }
        guard let p1 = host.stack.last?.id else { return XCTFail("pause presented") }
        host.answer(p1, PopupResult.secondary)
        XCTAssertFalse(host.isPresenting, "the logical stack is closed at once: callers see the answer")
        XCTAssertEqual(host.closing.map(\.id), [p1], "but the answered popup is still drawn")
        XCTAssertEqual(host.closing.first?.closingDrawn, true, "drawn without input or accessibility")
        let quit = Task { await host.present(Popup<PopupResult>.quitLevel) }
        for _ in 0..<200 where host.topID != .quitLevel { await Task.yield() }
        XCTAssertTrue(host.closing.isEmpty, "replaced in the successor's transaction: no frame without either")
        XCTAssertEqual(host.stack.last?.bridged, true, "the successor's dim starts at its alpha")
        let r1 = await pause.value
        XCTAssertEqual(r1, .secondary)
        if let q = host.stack.last?.id { host.answer(q, PopupResult.close) }        // a band rising away: its own ghost
        _ = await quit.value
        XCTAssertTrue(host.closing.isEmpty, "a rising band is drawn by `leaving`, never twice")
        // (2) an answer nothing follows (Resume, X) closes in ONE frame, panel and dim together, as v552 does
        let resume = Task { await host.present(Popup<PopupResult>.pause) }
        for _ in 0..<200 where host.topID != .pause { await Task.yield() }
        guard let p2 = host.stack.last?.id else { return XCTFail("pause presented again") }
        host.answer(p2, PopupResult.primary)
        XCTAssertTrue(host.closing.isEmpty, "Resume: nothing is held")
        _ = await resume.value
        XCTAssertFalse(PopupHost.expectsSuccessor(.pause, answer: PopupResult.close), "X on Pause: nothing follows")
        XCTAssertTrue(PopupHost.expectsSuccessor(.levelFailed(levels: [1], reason: .quit), answer: nil), "Level Failed → a screen")
        // (2a) a chain whose successor does not come: its dim goes `bridgeFrames` frames later (the panel went at once)
        let quitNoFollow = Task { await host.present(Popup<PopupResult>.pause) }
        for _ in 0..<200 where host.topID != .pause { await Task.yield() }
        guard let p2a = host.stack.last?.id else { return XCTFail("pause presented for 2a") }
        host.answer(p2a, PopupResult.secondary)
        XCTAssertEqual(host.closing.map(\.id), [p2a])
        var waits = 0
        while !host.closing.isEmpty, waits < 50 { try? await Task.sleep(nanoseconds: 10_000_000); waits += 1 }
        XCTAssertTrue(host.closing.isEmpty, "gone after \(waits * 10) ms (bridgeFrames \(PopupHost.bridgeFrames))")
        XCTAssertLessThan(waits, 30, "within a few frames")
        _ = await quitNoFollow.value
        // (2b) a router transition queued meanwhile (the Weekly tutorial's tab change before its intro): held until it is done
        let tab = Task { await host.present(Popup<PopupResult>.pause) }
        for _ in 0..<200 where host.topID != .pause { await Task.yield() }
        guard let p2b = host.stack.last?.id else { return XCTFail("pause presented for 2b") }
        host.answer(p2b, PopupResult.secondary)
        host.handOverFollowsTransition()
        try? await Task.sleep(nanoseconds: 150_000_000)                    // ~9 frames: far past bridgeFrames
        XCTAssertEqual(host.closing.map(\.id), [p2b], "held while the router's transition runs")
        host.transitionDone()
        waits = 0
        while !host.closing.isEmpty, waits < 50 { try? await Task.sleep(nanoseconds: 10_000_000); waits += 1 }
        XCTAssertTrue(host.closing.isEmpty, "released a few frames after the transition (\(waits * 10) ms)")
        _ = await tab.value
        // (3) the router's cut takes it away in the cut's own transaction
        let failed = Task { await host.present(Popup<PopupResult>.pause) }
        for _ in 0..<200 where host.topID != .pause { await Task.yield() }
        guard let p3 = host.stack.last?.id else { return XCTFail("pause presented a third time") }
        host.answer(p3, PopupResult.secondary)
        XCTAssertFalse(host.closing.isEmpty)
        host.endBridge()
        XCTAssertTrue(host.closing.isEmpty, "endBridge (the router's cut) removes it at once")
        _ = await failed.value
        // (4) the player's own pages close in one frame as before (nothing follows Settings); an event page (the Weekly tutorial,
        // its own darkening → its intro) is held whole
        let page = Task { await host.present(Popup<PopupResult>.settings) }
        for _ in 0..<200 where host.topID != .settings { await Task.yield() }
        if let s = host.stack.last?.id { host.answer(s, PopupResult.close) }
        XCTAssertTrue(host.closing.isEmpty, "Settings closes in one frame")
        _ = await page.value
        let tutorial = Task { await host.present(Popup<PopupResult>(.weeklyContestTutorial, style: PopupStyle(dim: .none), fallback: .close)) }
        for _ in 0..<200 where host.topID != .weeklyContestTutorial { await Task.yield() }
        guard let w = host.stack.last?.id else { return XCTFail("the weekly tutorial presented") }
        host.answer(w, PopupResult.primary)
        XCTAssertEqual(host.closing.map(\.id), [w], "an event page is held until its successor")
        XCTAssertEqual(host.closing.first?.closingDrawn, true)
        let intro = Task { await host.present(Popup<PopupResult>(.weeklyContestIntro, style: PopupStyle(dim: .unlock), fallback: .close)) }
        for _ in 0..<200 where host.topID != .weeklyContestIntro { await Task.yield() }
        XCTAssertTrue(host.closing.isEmpty, "and handed over in the successor's transaction")
        _ = await tutorial.value
        host.dismissAll()
        _ = await intro.value
    }

    func testTokensCoverTheS1Keys() {
        let t = Tuning.load(bundle: .main).ui.tokens
        for id in ["pause.panel", "pause.card", "pause.ribbon", "pause.close", "pause.resume", "pause.quit", "pause.toggleSound",
                   "pause.toggleHaptic", "pause.iconSound", "pause.iconHaptic",
                   "quit.band", "quit.ribbon", "quit.closeDisc", "quit.heart", "quit.quit", "quit.quitFrame",
                   "settings.header", "settings.closeDisc", "settings.notifCard", "settings.bell", "settings.notifToggle",
                   "settings.audioCard", "settings.sound", "settings.music", "settings.haptic", "settings.support",
                   "settings.supportFrame", "settings.terms", "settings.privacy", "page.card",
                   "home.avatarButton", "home.gearButton", "home.coinIcon", "home.coinPill", "home.plusBadge", "home.livesHeart",
                   "home.livesPill", "home.levelPlate", "home.playFrame", "home.playButton", "home.hardRibbon", "home.navBar",
                   "home.navHomeTab", "home.navHomeIcon", "home.navShop", "home.navTrophy", "home.navShopTab", "home.navLeaderboardTab",
                   "home.scene.platform", "home.scene.console", "home.scene.capsuleMachine", "home.scene.arrowPile", "loading.logo",
                   "loading.label"] {
            XCTAssertNotEqual(t.frame(id, .zero), .zero, "frames.\(id)")
        }
        for id in ["popup.title", "pause.rowLabel", "pause.toggleOn", "pause.toggleOff", "pause.resume", "pause.quit", "quit.message",
                   "quit.quit", "settings.label", "settings.support", "settings.link", "page.title", "home.coins", "home.lives",
                   "home.livesTimer", "home.livesCount", "home.levelCaption", "home.levelNumber", "home.levelNumberHard",
                   "home.levelNumberSuperHard", "home.play", "home.playHard", "home.playSuperHard", "home.hardRibbon",
                   "home.superHardRibbon", "home.navLabel", "home.navLabelShop", "home.navLabelLeaderboard", "loading.label", "toast"] {
            XCTAssertNotEqual(t.text(id, GameTextStyle(size: -1)).size, -1, "text.\(id)")
        }
        // SPEC-ui §0.4 corrections are in the data: the Settings page and the Quit band (C1, C2), the Loading label (C3),
        // the OFF toggle (C5); SPEC-motion-audio §13.2 timings.
        XCTAssertEqual(t.frame("settings.notifCard", .zero), CGRect(19.0, 134.1, 355.3, 95.7))
        XCTAssertEqual(t.frame("quit.band", .zero), CGRect(0, 234.2, 393, 405))
        // A5 CODEMOD (PLAN-P §4.3, owner items 1/15, ruling 46): the three colour pins follow R9's D1 palette map
        // (design/publish/palette/palette_map.csv; was 0x82251F / 0x093896 / 0x1031A9 — danger-red keeps its hue, the
        // blue chrome becomes the D1 teal at the same L*). Same exact-equality strength on the same keys.
        XCTAssertEqual(t.text("loading.label", GameTextStyle(size: 1)).outline, Color(hex: 0x7E2A1C))
        XCTAssertEqual(t.text("pause.toggleOff", GameTextStyle(size: 1)).outline, Color(hex: 0x00474D))
        XCTAssertEqual(t.color("toggle.offTrack", 0), Color(hex: 0x00484E))
        let ui = Tuning.load(bundle: .main).ui
        XCTAssertEqual(ui.loadingToHomeFade, 0.16, accuracy: 1e-9)
        XCTAssertEqual(ui.loadingToBoardFade, 0.13, accuracy: 1e-9)
        // A2 FEEL-P (owner item 2, requirement change): the tabs push-slide instead of the hard cut (`transition.homeTabs` 0
        // retired); motion-catalog §11.3 R2, VERIFIED v582 60 Hz: remaining = D·(1 − u)^2.51, u = t / 0.488 s. The same exact
        // strength as the old pin: the bundled values, and the compiled defaults equal them.
        XCTAssertNil(ui.file.value("transition.homeTabs"), "the hard-cut key is retired")
        // the bundled curve is v582's own series (27 frames: 1 → 0 in 26 frames = 0.433 s, strictly falling); the fitted model
        // (the compiled default, no table) stays within ±2 pt of it at every frame (the G3 tolerance)
        let table = ui.tabSlideTable
        XCTAssertEqual(table.count, 27)
        XCTAssertEqual(table.first, 1.0)
        XCTAssertEqual(table.last, 0.0)
        XCTAssertEqual(zip(table, table.dropFirst()).filter { $1 >= $0 }.count, 0, "the remaining distance falls every frame")
        XCTAssertEqual(ui.tabSlideDuration, 26.0 / 60, accuracy: 1e-9)
        XCTAssertEqual(ui.tabSlidePower, 2.51, accuracy: 1e-9)
        let compiled = UITuning(file: TuningFile(name: "ui", json: [:]))
        XCTAssertEqual(compiled.tabSlideDuration, 0.488, accuracy: 1e-9)
        XCTAssertEqual(compiled.tabSlidePower, ui.tabSlidePower, accuracy: 1e-9)
        let measured = TabSlideCurve(duration: ui.tabSlideDuration, power: 2.51, lead: 0, table: table)
        let model = TabSlideCurve(duration: 0.488, power: 2.51, lead: 0)
        for k in 1..<26 {
            let t = Double(k) / 60
            XCTAssertEqual(measured.progress(t) ?? -1, 1 - table[k], accuracy: 1e-9, "frame \(k) is the table's")
            XCTAssertEqual(((model.progress(t) ?? 1) - (measured.progress(t) ?? 1)) * 393, 0, accuracy: 2.0, "model vs v582 at frame \(k)")
        }
        XCTAssertNil(measured.progress(26.0 / 60), "the slide ends on frame 26")
        XCTAssertEqual(ui.dim(.popup), 0.90, accuracy: 1e-9)
        XCTAssertEqual(t.frame("pause.ribbon", .zero), CGRect(60.1, 190.5, 274.2, 90.4), "copied from design/ui-tokens.json")
        XCTAssertEqual(t.text("popup.title", GameTextStyle(size: 1)).size, 49.2)
    }

    // MARK: puppet loops (SPEC-motion-audio §8.2) and the inert Music button (MA2)

    func testPuppetLoopsAreDataAndTargetRealLayers() throws {
        let file = Tuning.load(bundle: .main).ui.file
        // A4: the same measured cycles under the D1 rigs' names (R2's mapping step: the track bodies are unchanged)
        let expected = [HomeView.bossRig: 3.16, HomeView.diggerRightRig: 10.2, HomeView.diggerLeftRig: 17.3]
        for (name, cycle) in expected {
            let rig = try PuppetRig.load(name)
            let motion = PuppetMotion(file, rig: name)
            XCTAssertEqual(motion.cycle, cycle, accuracy: 1e-9, "\(name) cycle (MA12)")
            XCTAssertGreaterThanOrEqual(motion.tracks.count, 5, name)
            let names = Set(rig.layers.map(\.name)).union(rig.groups.keys).union(["whole", "head", "lids"])
            for t in motion.tracks {
                XCTAssertTrue(names.contains(t.layer), "\(name): track target \(t.layer) exists")
                XCTAssertEqual(t.times.first, 0, "\(name) \(t.layer) starts at 0")
                XCTAssertLessThanOrEqual(t.times.last ?? 99, cycle + 1e-9)
                XCTAssertEqual(t.times, t.times.sorted(), "\(name) \(t.layer) key times rise")
                XCTAssertEqual(t.curves.count, t.values.count - 1)
                if t.prop == "member" {
                    let members = Set(rig.groups[t.layer]?.members ?? [])
                    XCTAssertTrue(t.values.allSatisfy { members.contains(($0 as? String) ?? "") }, "\(name) \(t.layer) members")
                }
            }
            // installed in a window, the stage adds its animations (render server; no timers, no display link)
            let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 393, height: 852))
            let view = PuppetView(rig: rig, motion: motion, animate: true)
            window.addSubview(view)
            XCTAssertGreaterThan(view.installedCount, 0, "\(name) loops installed")
            view.removeFromSuperview()
        }
    }

    /// F3-A (LOOK-2 carry-over 1): LOOK-2 redrew home Digger L's rest arm as a hand on the hip; the old idle wave rotated THAT
    /// arm -25° about the shoulder, which swings the hand across the belly. The wave now swaps in the rig's raised-paw member
    /// (`armL_wave`, rig group armL) and waves it: the hip arm never rotates, the raised arm reverses ≥ 3 times per window
    /// with ≥ 8° swings, and stays inside [-25°, +8°] (the paw on screen, clear of the face). A negative control runs the
    /// same check on the pre-fix track.
    static func diggerWaveProblems(_ motion: PuppetMotion, rig: PuppetRig) -> [String] {
        var out: [String] = []
        let members = Set(rig.groups["armL"]?.members ?? [])
        if !members.contains("armL") || !members.contains("armL_wave") { out.append("rig group armL lacks armL / armL_wave") }
        for t in motion.tracks where t.layer == "armL" && t.prop != "member" {
            let v = t.values.compactMap { ($0 as? NSNumber)?.doubleValue }
            if v.contains(where: { abs($0) > 3 }) { out.append("the hip arm (armL) \(t.prop) moves up to \(v.map(abs).max() ?? 0)") }
        }
        guard let swap = motion.tracks.first(where: { $0.layer == "armL" && $0.prop == "member" }) else {
            return out + ["no armL member swap: the raised paw never shows"]
        }
        let names = swap.values.map { ($0 as? String) ?? "" }
        var windows: [(Double, Double)] = []
        for (i, n) in names.enumerated() where n == "armL_wave" {
            windows.append((swap.times[i], i + 1 < swap.times.count ? swap.times[i + 1] : motion.cycle))
        }
        if windows.isEmpty { out.append("the member swap never shows armL_wave") }
        guard let wave = motion.tracks.first(where: { $0.layer == "armL_wave" && $0.prop == "rotation" }) else {
            return out + ["armL_wave has no rotation track: the raised paw does not wave"]
        }
        let v = wave.values.compactMap { ($0 as? NSNumber)?.doubleValue }
        if let lo = v.min(), let hi = v.max(), lo < -25 || hi > 8 { out.append("armL_wave rotation \(lo)…\(hi) outside -25…8") }
        for (a, b) in windows {
            let keys = zip(wave.times, v).filter { $0.0 >= a - 1e-9 && $0.0 <= b + 1e-9 }.map(\.1)
            var reversals = 0, lastDir = 0.0
            for (x, y) in zip(keys, keys.dropFirst()) where abs(y - x) >= 8 {
                let dir = y > x ? 1.0 : -1.0
                if lastDir != 0, dir != lastDir { reversals += 1 }
                lastDir = dir
            }
            if reversals < 3 { out.append(String(format: "window %.2f-%.2f: %d reversals of ≥ 8°", a, b, reversals)) }
        }
        return out
    }

    func testDiggerLWavesTheRaisedPawNeverTheHipArm() throws {
        let file = Tuning.load(bundle: .main).ui.file
        let rig = try PuppetRig.load(HomeView.diggerLeftRig)
        let motion = PuppetMotion(file, rig: HomeView.diggerLeftRig)
        XCTAssertEqual(Self.diggerWaveProblems(motion, rig: rig), [])
        // negative control: the pre-fix loop (the hip arm rotated 0 → -25 → -5 → -25 → 0 twice, no member swap) fails
        var old = try XCTUnwrap(file.value("puppet." + HomeView.diggerLeftRig) as? [String: Any])
        var tracks = try XCTUnwrap(old["tracks"] as? [[String: Any]]).filter {
            ($0["layer"] as? String) != "armL" && ($0["layer"] as? String) != "armL_wave"
        }
        tracks.append(["layer": "armL", "prop": "rotation", "t": [0, 6.0, 6.3, 6.6, 6.9, 7.2, 12.5, 12.8, 13.1, 13.4, 13.7, 17.3],
                       "v": [0, 0, -25, -5, -25, 0, 0, -25, -5, -25, 0, 0], "curve": "easeInOut"])
        old["tracks"] = tracks
        let pre = PuppetMotion(TuningFile(name: "ui", json: ["puppet": [HomeView.diggerLeftRig: old]]), rig: HomeView.diggerLeftRig)
        XCTAssertEqual(pre.cycle, 17.3, accuracy: 1e-9)
        let problems = Self.diggerWaveProblems(pre, rig: rig)
        XCTAssertTrue(problems.contains { $0.hasPrefix("the hip arm (armL) rotation") }, "control: \(problems)")
        XCTAssertTrue(problems.contains { $0.hasPrefix("no armL member swap") }, "control: \(problems)")
    }

    /// A4 ART-INTEG (owner items 4 + 8; R3 HOME / R8 EVENT-ART): the signpost centrepiece and the badge rigs recompose their full
    /// renders at rest (the art lanes' proofs through PuppetRig + PuppetStage), loop on real layers (ui.json puppet.<rig>), and the
    /// signpost refill is data (five board flips about their hinges, each with its landing tick, then the post's knock).
    func testTheD1CentrepieceAndBadgeRigsAreData() throws {
        let file = Tuning.load(bundle: .main).ui.file
        let rigs = [HomeView.signpostRig: 36.0, "badge_hotstreak_rig": 16.0, "badge_rocketrally_rig": 12.0,
                    "badge_cloudhop_rig": 12.0, "badge_upaway_rig": 4.0]
        var report: [String] = []
        for (name, cycle) in rigs {
            let rig = try PuppetRig.load(name)
            let full = try XCTUnwrap(rig.fullPath.flatMap { ArtStore.image(path: $0)?.cgImage }, "\(name): full render in the bundle")
            let ours = try XCTUnwrap(PuppetView.renderRest(rig, scale: 3), name)
            XCTAssertEqual(ours.width, full.width, "\(name) width")
            XCTAssertEqual(ours.height, full.height, "\(name) height")
            let (mean, _) = Self.diff(ours, full)
            report.append("\(name): mean |Δ| \(String(format: "%.3f", mean))/255")
            XCTAssertLessThanOrEqual(mean, 1.0, "\(name): the rest layers recompose the full render within 1/255")
            let motion = PuppetMotion(file, rig: name)
            XCTAssertEqual(motion.cycle, cycle, accuracy: 1e-9, "\(name) cycle")
            XCTAssertFalse(motion.tracks.isEmpty, name)
            let names = Set(rig.layers.map(\.name)).union(["whole", "exhaust"])
            for t in motion.tracks {
                XCTAssertTrue(names.contains(t.layer), "\(name): track target \(t.layer) exists")
                XCTAssertEqual(t.times.first, 0, "\(name) \(t.layer) starts at 0")
                XCTAssertLessThanOrEqual(t.times.last ?? 99, cycle + 1e-9, "\(name) \(t.layer) inside the cycle")
                XCTAssertEqual(t.times, t.times.sorted(), "\(name) \(t.layer) key times rise")
                XCTAssertEqual(t.curves.count, t.values.count - 1)
            }
            let window = UIWindow(frame: CGRect(x: 0, y: 0, width: 393, height: 852))
            let view = PuppetView(rig: rig, motion: motion, animate: true)
            window.addSubview(view)
            XCTAssertGreaterThan(view.installedCount, 0, "\(name) loops installed")
            view.removeFromSuperview()
        }
        print("[A4] D1 rigs recompose: " + report.sorted().joined(separator: " · "))
        // the refill: boards 1-5 top → bottom, 0.18 s apart, each hidden until its flip and ticking on its landing; the knock last
        let refill = SignpostRefill(file, rig: HomeView.signpostRig)
        let flips = refill.steps.filter { $0.prop == "scaleX" }
        XCTAssertEqual(flips.map(\.layer), ["board1", "board2", "board3", "board4", "board5"])
        XCTAssertEqual(Set(refill.hiddenAtStart), Set(flips.map(\.layer)))
        XCTAssertEqual(flips.compactMap { $0.haptic?.at }.count, 5, "one tick per board")
        for (a, b) in zip(flips, flips.dropFirst()) { XCTAssertEqual(b.begin - a.begin, 0.18, accuracy: 1e-9) }
        for f in flips {
            XCTAssertEqual(f.values.first, 0, "\(f.layer) starts folded")
            XCTAssertEqual(f.values.last, 1, "\(f.layer) lands at rest")
            XCTAssertEqual(f.haptic?.at ?? 0, f.begin + f.duration * 0.7, accuracy: 0.002, "\(f.layer) ticks on its landing key")
        }
        XCTAssertEqual(refill.steps.last?.layer, "base", "the post's knock ends the refill")
        let end = refill.steps.map { $0.begin + $0.duration }.max() ?? 0
        XCTAssertLessThanOrEqual(end, Tuning.load(bundle: .main).ui.tokens.number("home.pileRefill", 1.2) + 1e-9, "inside home.pileRefill")
    }

    func testMusicButtonIsInertAndShowsOff() {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("s1-music-\(UUID().uuidString)")
        let store = PlayerStore(args: LaunchArgs(), now: Date(), directory: dir, debounce: 0.05)
        let ui = Tuning.load(bundle: .main).ui
        XCTAssertFalse(SettingsPopup.musicShown(ui: ui, settings: store.state.settings), "MA2: Music shows OFF")
        let before = store.state.settings
        SettingsPopup.tapMusic(ui: ui, store: store, audio: RecordingAudio(), haptics: RecordingHaptics())
        XCTAssertEqual(store.state.settings, before, "MA2: no state change")
        try? FileManager.default.removeItem(at: dir)
    }

    func testToastWrapsIntoTwoLinesWithinTheBox() {
        let style = GameTextStyle(size: 18, fill: [.white], outline: Color(hex: 0x022880), outlineWidth: 1, drop: 1)
        XCTAssertEqual(ToastCenter.wrap("Purchase pending.", style: style, maxWidth: 330), ["Purchase pending."])
        let lines = ToastCenter.wrap("Bildirimlere iOS Ayarlar'dan izin ver. Bildirimlere iOS Ayarlar'dan izin ver.", style: style, maxWidth: 330)
        XCTAssertEqual(lines.count, 2)
        let w = GameTextLayout.make(lines[0], postScriptName: GameText.blackPostScript, size: 18, tracking: 0).advance
        XCTAssertLessThanOrEqual(w, 330)
    }

    func testLivesText() {
        var s = PlayerState()
        let now = Date(timeIntervalSince1970: 1_000_000)
        XCTAssertNil(LivesText.pill(s, now: now, refill: 1200))
        XCTAssertEqual(LivesText.value(s, now: now, refill: 1200), "full")
        s.lives = LivesState(count: 4, anchor: now.addingTimeInterval(-3))
        XCTAssertEqual(LivesText.pill(s, now: now, refill: 1200), "19:57")
        XCTAssertEqual(LivesText.value(s, now: now, refill: 1200), "4|19:57")
        s.unlimitedLivesUntil = now.addingTimeInterval(1800)
        XCTAssertEqual(LivesText.value(s, now: now, refill: 1200), "inf:30:00")
        s.unlimitedLivesUntil = now.addingTimeInterval(4800)
        XCTAssertEqual(LivesText.pill(s, now: now, refill: 1200), "1h 20m", "SPEC-ui §2.2.2: an hour or more reads 1h 20m")
        XCTAssertEqual(LivesText.value(s, now: now, refill: 1200), "inf:1h 20m", "CONSISTENCY Y-4")
        s.unlimitedLivesUntil = nil
        s.lives = LivesState(count: 3, anchor: now.addingTimeInterval(-1200.4))
        XCTAssertEqual(LivesText.state(s, now: now, refill: 1200), .finished, "a life just arrived: Finished for ≈ 1 s")
        XCTAssertEqual(LivesText.value(s, now: now, refill: 1200), "3|finished")
    }

    func testUIArtIsGeneratedFromTheManifest() {
        XCTAssertEqual(UIArt.iconCoin.path, "UI/iconCoin@3x.png")
        // A4 ART-INTEG (R2 / R3, owner items 1 + 15): the same two facts on the D1 ids that replaced avatarParty / homeBackdrop
        // (their predecessors are NOT SHIPPED now, like avatarGreen before them)
        XCTAssertEqual(UIArt.avatarConfetti.path, "Art/char_avatarConfetti@3x.png")   // a shipped 3d avatar
        XCTAssertEqual(UIArt.homeWorkshop.sizePt, CGSize(width: 393, height: 852))
        XCTAssertGreaterThan(UIArt.allCases.count, 100)
        let missing = ArtStore.missing()
        print("[S1] UIArt: \(UIArt.allCases.count) ids, \(missing.count) not in the bundle yet (the art lanes' todo): "
              + missing.map(\.rawValue).joined(separator: ","))
    }

    // MARK: helpers

    struct Px { let r: Int; let g: Int; let b: Int; let a: Int }

    static func pixels(_ cg: CGImage) -> [UInt8] {
        let w = cg.width, h = cg.height
        var px = [UInt8](repeating: 0, count: w * h * 4)
        let ctx = CGContext(data: &px, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                            space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
        return px
    }

    /// Mean |Δ| over RGBA (premultiplied, 0…255) and the share of channels differing by more than 40.
    static func diff(_ a: CGImage, _ b: CGImage) -> (Double, Double) {
        let pa = pixels(a), pb = pixels(b)
        guard pa.count == pb.count, !pa.isEmpty else { return (255, 1) }
        var sum = 0, over = 0
        for i in 0..<pa.count {
            let d = abs(Int(pa[i]) - Int(pb[i]))
            sum += d
            if d > 40 { over += 1 }
        }
        return (Double(sum) / Double(pa.count), Double(over) / Double(pa.count))
    }

    static func count(_ cg: CGImage, _ a: (Px) -> Bool, _ b: (Px) -> Bool) -> (Int, Int) {
        let px = pixels(cg)
        var na = 0, nb = 0
        for i in stride(from: 0, to: px.count, by: 4) where px[i + 3] > 240 {
            let p = Px(r: Int(px[i]), g: Int(px[i + 1]), b: Int(px[i + 2]), a: Int(px[i + 3]))
            if a(p) { na += 1 }
            if b(p) { nb += 1 }
        }
        return (na, nb)
    }

    // MARK: FIX-2 lane B (L28 / F-10 / B1b-r3): the event countdown and the ended-event word

    /// v582 PH-0a (the phone wins): ONE formatter for every event countdown — ≥ 1 day "1d 1h", ≥ 1 hour "Xh Ym" keeping " 0m"
    /// (F-10: the win strip's "19h 0m"), under an hour "mm:ss" with two-digit minutes ("09:34"). The last hour (and one 20 s
    /// layer tick before it) runs home's per-second timeline.
    func testCountdownFormats() {
        let cases: [(Double, String)] = [(574, "09:34"), (3599, "59:59"), (3600, "1h 0m"), (68_400, "19h 0m"), (90_000, "1d 1h"),
                                         (59.9, "00:59"), (0, "00:00"), (-5, "00:00"), (86_399, "23h 59m"), (86_400, "1d 0h")]
        for (s, want) in cases { XCTAssertEqual(Countdown.text(s), want, "\(s) s") }
        XCTAssertTrue(LiveCountdown<EmptyView>.ticks(3599))
        XCTAssertTrue(LiveCountdown<EmptyView>.ticks(3610), "one layer tick early: '1h 0m' → '59:59' lands on its second")
        XCTAssertTrue(LiveCountdown<EmptyView>.ticks(0))
        XCTAssertFalse(LiveCountdown<EmptyView>.ticks(3700), "at an hour or more the layer's 20 s tick is enough")
        XCTAssertFalse(LiveCountdown<EmptyView>.ticks(-30), "an ended event does not tick")
    }

    /// B1b-r3: the ended event's word is its own key, so a language can say "ended" there and "ready" on the lives pill.
    func testTheEndedEventWordIsItsOwnKey() throws {
        func lproj(_ l: String) throws -> Bundle { try XCTUnwrap(Bundle.main.path(forResource: l, ofType: "lproj").flatMap(Bundle.init(path:)), l) }
        XCTAssertEqual(try lproj("en").localizedString(forKey: "event.finished", value: "∅", table: nil), "Finished", "v582's English word")
        XCTAssertEqual(try lproj("en").localizedString(forKey: "Finished", value: "∅", table: nil), "Finished")
        for (lang, ended) in [("ja", "終了"), ("ko", "종료"), ("zh-Hans", "已结束"), ("es", "Terminó"), ("pt-BR", "Acabou"), ("tr", "Bitti")] {
            XCTAssertEqual(try lproj(lang).localizedString(forKey: "event.finished", value: "∅", table: nil), ended, lang)
        }
        XCTAssertNotEqual(try lproj("ja").localizedString(forKey: "Finished", value: "∅", table: nil), "終了",
                          "the lives pill keeps its own word")
        XCTAssertEqual(EventWord.finished, Bundle.main.localizedString(forKey: "event.finished", value: "∅", table: nil),
                       "every event site reads event.finished")
    }

    /// V3's "cached digit rasters": the last hour's mm:ss is one raster per character and pass, placed at CoreText's own
    /// advances (the run's width = the whole label's layout width: no pair kerning under an explicit kern), and it looks like
    /// the whole label — in particular no neighbour's outline over a face (PC Display's "14" inks overlap the 1 pt outline).
    func testGlyphRunTextComposesTheWholeLabel() throws {
        let st = CountdownChip.textStyle(Tuning.load(bundle: .main).ui.tokens)
        XCTAssertTrue(GlyphRunText.composable("09:34"))
        XCTAssertFalse(GlyphRunText.composable("1h 0m"))
        XCTAssertFalse(GlyphRunText.composable(""))
        for text in ["09:34", "14:41", "00:00", "59:59"] {
            let (rs, glyphs) = GlyphRunText.run(text, style: st, maxWidth: 54)
            let whole = GameTextLayout.make(text, postScriptName: st.postScriptName, size: st.size, tracking: st.tracking, maxWidth: 54)
            XCTAssertEqual(rs.size, whole.fontSize, accuracy: 0.001, "\(text): the same fit")
            let first = try XCTUnwrap(glyphs.first), last = try XCTUnwrap(glyphs.last)
            let span = (last.dx + last.layout.advance / 2) - (first.dx - first.layout.advance / 2)
            XCTAssertEqual(span, whole.advance, accuracy: 0.01, "\(text): per-glyph advances + tracking = the whole line")
        }
        // pixels: the run vs the whole label, both centred at the same point, @3x
        func render<V: View>(_ v: V) throws -> CGImage {
            let r = ImageRenderer(content: ZStack { v.at(40, 15) }.frame(width: 80, height: 30, alignment: .topLeading)
                .environment(\.displayScale, 3))
            r.scale = 3
            return try XCTUnwrap(r.cgImage)
        }
        func rgba(_ cg: CGImage) -> [UInt8] {
            var px = [UInt8](repeating: 0, count: cg.width * cg.height * 4)
            let ctx = CGContext(data: &px, width: cg.width, height: cg.height, bitsPerComponent: 8, bytesPerRow: cg.width * 4,
                                space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: cg.width, height: cg.height))
            return px
        }
        for text in ["09:34", "14:41"] {
            let a = rgba(try render(GameText(verbatim: text, style: st, maxWidth: 54)))
            let b = rgba(try render(GlyphRunText(text: text, style: st, maxWidth: 54)))
            XCTAssertEqual(a.count, b.count)
            var faceLost = 0, faces = 0, sum = 0
            for i in stride(from: 0, to: a.count, by: 4) {
                let whiteA = a[i] > 235 && a[i + 1] > 235 && a[i + 2] > 235 && a[i + 3] > 250
                if whiteA {
                    faces += 1
                    if Int(b[i]) + Int(b[i + 1]) + Int(b[i + 2]) < 3 * 128 { faceLost += 1 }      // face pixel painted dark
                }
                sum += abs(Int(a[i + 3]) - Int(b[i + 3]))
            }
            XCTAssertGreaterThan(faces, 300, "\(text): the label has a white face")
            XCTAssertLessThanOrEqual(faceLost, faces / 100, "\(text): an outline covers a face in the run (\(faceLost) of \(faces) px)")
            XCTAssertLessThan(Double(sum) / Double(a.count / 4), 6, "\(text): mean alpha difference vs the whole label")
        }
    }

    /// FIX-2 B review (L28): a live countdown re-reads the clock exactly where its text can change — the wall clock's whole
    /// seconds — at `-pc.clockRate` speed; a stopped clock or a paused countdown draws once. (Was 4 polls a second, up to
    /// 250 ms late.)
    func testCountdownScheduleTicksOnTheWallClocksWholeSeconds() throws {
        let real = Date(timeIntervalSinceReferenceDate: 800_000_000)
        func wall(_ d: Date, _ w0: Double, _ rate: Double) -> Double { w0 + d.timeIntervalSince(real) * rate }
        for (w0, rate) in [(1_791_183_026.4, 1.0), (1_791_183_026.999, 1.0), (1_791_183_026.0, 2.0), (1_791_183_026.7, 0.5)] {
            let sch = CountdownSchedule(real: real, wall: w0, rate: rate, paused: false)
            for start in [real, real.addingTimeInterval(10.2), real.addingTimeInterval(-3)] {
                let it = sch.entries(from: start, mode: .normal)
                XCTAssertEqual(it.next(), start, "the first entry is the start (the view's first draw)")
                // entries sit 3 ms (of real time) past each whole wall second: the first one is the first such point after
                // the start (a start exactly on a whole second gets that second's own entry 3 ms later)
                var last = (wall(start, w0, rate) - 0.003 * rate).rounded(.down)
                var prev = start
                for _ in 0..<6 {
                    let d = try XCTUnwrap(it.next())
                    XCTAssertGreaterThan(d, prev)
                    let w = wall(d, w0, rate)
                    XCTAssertEqual(w.rounded(.down), last + 1, "one entry per wall second (w0 \(w0), rate \(rate))")
                    XCTAssertEqual(w - w.rounded(.down), 0.003 * rate, accuracy: 1e-4, "just past the second, never before it")
                    last += 1
                    prev = d
                }
            }
        }
        for sch in [CountdownSchedule(real: real, wall: 1_791_183_026.4, rate: 0, paused: false),
                    CountdownSchedule(real: real, wall: 1_791_183_026.4, rate: 1, paused: true)] {
            let it = sch.entries(from: real, mode: .normal)
            XCTAssertEqual(it.next(), real)
            XCTAssertNil(it.next(), "a stopped clock / a paused countdown draws once")
        }
    }

    /// FIX-2 B review (L28): the page chips now draw their time as a glyph run too (they tick) — for each page chip's style the
    /// run looks like the whole label it replaced (the same mean alpha test as the home chip's).
    func testGlyphRunTextMatchesTheLabelInEveryPageChipStyle() throws {
        let t = Tuning.load(bundle: .main).ui.tokens
        let event = t.text("claw.timer", .s2(15.0, -0.6, [0x5A2801]))
        let styles: [(String, GameTextStyle, CGFloat)] = [
            ("EventTimerChip", event.sized(event.size * 23 / 28), 67.7 - 26 * 23 / 28),
            ("PageTimerChip", .s2(15.4, -0.3, [0x5A2801]), 56),
            ("SocSkyChip", .s2(13.2, -0.3, [0xFFFFFF], outline: 0x49142B, 1.0, drop: 0.6), 49.4),
            ("BalloonStrip", .s2(12.2, -1.38, [0x5A2801]), 62)]
        func render<V: View>(_ v: V) throws -> [UInt8] {
            let r = ImageRenderer(content: ZStack { v.at(40, 15) }.frame(width: 80, height: 30, alignment: .topLeading)
                .environment(\.displayScale, 3))
            r.scale = 3
            let cg = try XCTUnwrap(r.cgImage)
            var px = [UInt8](repeating: 0, count: cg.width * cg.height * 4)
            let ctx = try XCTUnwrap(CGContext(data: &px, width: cg.width, height: cg.height, bitsPerComponent: 8, bytesPerRow: cg.width * 4,
                                              space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue))
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: cg.width, height: cg.height))
            return px
        }
        for (name, st, maxW) in styles {
            for text in ["09:34", "14:41", "00:07"] {
                let a = try render(GameText(verbatim: text, style: st, maxWidth: maxW))
                let b = try render(GlyphRunText(text: text, style: st, maxWidth: maxW))
                XCTAssertEqual(a.count, b.count)
                var ink = 0, sum = 0
                for i in stride(from: 3, to: a.count, by: 4) {
                    if a[i] > 128 { ink += 1 }
                    sum += abs(Int(a[i]) - Int(b[i]))
                }
                XCTAssertGreaterThan(ink, 200, "\(name) \(text): the label draws")
                XCTAssertLessThan(Double(sum) / Double(a.count / 4), 6, "\(name) \(text): mean alpha difference vs the whole label")
            }
        }
    }

    /// B3-o4: the zh-Hans event name carries an explicit split (U+200B) so the lettering draws 火热 and 连胜 in its two colours,
    /// like "Hot" + "Streak"; the space-separated languages split exactly as before, and the round trip keeps the marker.
    func testTheLetteringSplitHonoursAnExplicitZeroWidthBreak() throws {
        let zhLproj = try XCTUnwrap(Bundle.main.path(forResource: "zh-Hans", ofType: "lproj").flatMap(Bundle.init(path:)))
        let zh = zhLproj.localizedString(forKey: "Hot Streak", value: "∅", table: nil)
        XCTAssertEqual(zh, "火热\u{200B}连胜", "the zh-Hans table marks the split")
        let u = LineUnits.units(zh, language: "zh-Hans")
        let (w1, w2) = SocEventLogo.words(u, full: zh, twoLines: false)
        XCTAssertEqual(w1, "火热")
        XCTAssertEqual(w2, "连胜")
        XCTAssertEqual(LineUnits.join(u), zh, "the round trip keeps the marker")
        XCTAssertFalse(u.contains { $0.text.contains("\u{200B}") }, "the marker is never drawn")
        for (s, a, b) in [("Hot Streak", "Hot", "Streak"), ("Rocket Rally", "Rocket", "Rally"), ("Weekly Cup", "Weekly", "Cup")] {
            let (x, y) = SocEventLogo.words(LineUnits.units(s, language: "en"), full: s, twoLines: false)
            XCTAssertEqual([x, y], [a, b], s)
        }
        let ja = LineUnits.units("連勝ラッシュ", language: "ja")
        XCTAssertEqual(SocEventLogo.words(ja, full: "連勝ラッシュ", twoLines: false).0, "連勝", "ja keeps its dictionary split")
    }

    /// F-19 (V2: the phone's popup field has a 1 pt light rim at its edge, #298FF9 → D1 `colors.panel.fieldRim`): a pixel probe
    /// half a point inside the field's top edge reads the rim colour, and 3 pt further in the darker field / inner shadow.
    func testPopupPanelFieldHasItsLightRim() throws {
        let t = Tuning.load(bundle: .main).ui.tokens
        let r = ImageRenderer(content: PopupPanelFrame(t: t).frame(width: 370.6, height: 399).environment(\.displayScale, 3))
        r.scale = 3
        let img = try XCTUnwrap(r.cgImage)
        var px = [UInt8](repeating: 0, count: img.width * img.height * 4)
        let ctx = try XCTUnwrap(CGContext(data: &px, width: img.width, height: img.height, bitsPerComponent: 8, bytesPerRow: img.width * 4,
                                          space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue))
        ctx.draw(img, in: CGRect(x: 0, y: 0, width: img.width, height: img.height))
        func rgb(_ xPt: CGFloat, _ yPt: CGFloat) -> (Int, Int, Int) {
            let x = Int(xPt * 3), y = Int(yPt * 3), i = (y * img.width + x) * 4
            return (Int(px[i]), Int(px[i + 1]), Int(px[i + 2]))
        }
        let edge = 18.6 + 1.3                                          // the field's top edge (bar + groove gap)
        let rim = rgb(185.3, edge + 0.5), inside = rgb(185.3, edge + 3.5)
        let want = (0x00, 0x9F, 0x91)                                  // ui.json colors.panel.fieldRim
        XCTAssertLessThanOrEqual(abs(rim.0 - want.0) + abs(rim.1 - want.1) + abs(rim.2 - want.2), 24, "the rim: \(rim)")
        XCTAssertGreaterThan(rim.1, inside.1 + 12, "lighter than the field just inside it: \(rim) vs \(inside)")
        Self.save(img, "panel-field-rim.png")
    }

    static var evidenceDir: URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("s1-evidence")
        try? FileManager.default.createDirectory(at: docs, withIntermediateDirectories: true)
        return docs
    }

    static func save(_ cg: CGImage, _ name: String) {
        if let data = UIImage(cgImage: cg).pngData() { try? data.write(to: evidenceDir.appendingPathComponent(name)) }
    }

    static func saveText(_ text: String, _ name: String) {
        try? text.write(to: evidenceDir.appendingPathComponent(name), atomically: true, encoding: .utf8)
    }
}

@MainActor private final class RecordingAudio: AudioPlaying {
    var applied: [PlayerState.Settings] = []
    func warmUp() async {}
    func play(_ s: SoundID, gain: Float) {}
    func playMusic(_ m: MusicID, fade: Double) {}
    func stopMusic(fade: Double) {}
    func apply(settings: PlayerState.Settings) { applied.append(settings) }
    var outputLatency: TimeInterval { 0 }
}

@MainActor private final class RecordingHaptics: HapticPlaying {
    var enabled = true
    func prepare() {}
    func play(_ h: Haptic) {}
}
