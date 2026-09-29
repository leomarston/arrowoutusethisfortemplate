import XCTest
import SwiftUI
import PathCore
@testable import ArrowOut

/// A2 FEEL-P (owner items 2, 3, 7, 8; design/publish/motion-catalog.md §3, §5, §6, §11): the data and the logic of the tab
/// push-slide, the popup entrances (punch / band drop), the haptic map's per-beat intensities and the toggle-order fix.
/// The motion itself is judged on recordings (feelstrip / slide_measure against v582); these pin what feeds it.
@MainActor
final class FeelPTests: XCTestCase {
    private let ui = Tuning.load(bundle: .main).ui

    private func context() -> AppContext {
        let a = LaunchArgs(arguments: [])
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("a2-feel-\(UUID().uuidString)")
        let store = PlayerStore(args: a, now: Date(), bundle: .main, directory: dir, debounce: 0.05)
        return AppContext(args: a, tuning: Tuning.load(bundle: .main), clock: MotionClock(args: a), store: store, hud: HUDModel(),
                          anchors: AnchorRegistry(), perf: PerfMonitor(), latency: LatencyProbe(), bundle: .main)
    }

    // MARK: haptics (motion-catalog §5.1 / §5.2, contract amend 4)

    /// `play(_:intensity:)` fires the beat at its own intensity; a plain `play` of the same case afterwards uses the row again.
    func testABeatFiresAtItsOwnIntensity() async throws {
        let h = Haptics(context())
        h.enabled = true
        h.play(.logoLetter, intensity: 0.55)
        h.flushPending()
        XCTAssertEqual(h.lastFired, .logoLetter)
        XCTAssertEqual(h.lastIntensity ?? -1, 0.55, accuracy: 1e-9)
        try await Task.sleep(nanoseconds: 40_000_000)                    // > 1 frame
        h.play(.logoLetter)
        h.flushPending()
        XCTAssertEqual(h.lastIntensity ?? -1, h.map.row(.logoLetter).intensity, accuracy: 1e-9, "the row's own intensity (0.70)")
        XCTAssertEqual(h.map.row(.logoLetter).intensity, 0.70, accuracy: 1e-9)
    }

    /// Several requests in one turn: the arbiter's priority still decides, and the winner keeps its own request's intensity.
    func testTheWinnerKeepsItsIntensity() async throws {
        let h = Haptics(context())
        h.enabled = true
        try await Task.sleep(nanoseconds: 40_000_000)
        h.play(.button)
        h.play(.logoLetter, intensity: 0.62)
        h.play(.firework, intensity: 0.2)
        h.flushPending()
        XCTAssertEqual(h.lastFired, .logoLetter, "logoLetter > firework > button (§5.2)")
        XCTAssertEqual(h.lastIntensity ?? -1, 0.62, accuracy: 1e-9)
        // a disabled gate drops the request and its intensity
        h.enabled = false
        h.play(.logoLetter, intensity: 0.9)
        h.flushPending()
        h.enabled = true
        try await Task.sleep(nanoseconds: 40_000_000)
        h.play(.logoLetter)
        h.flushPending()
        XCTAssertEqual(h.lastIntensity ?? -1, 0.70, accuracy: 1e-9, "no stale override survives a dropped turn")
    }

    /// Row 18: switching Haptic ON answers with the button haptic AFTER the gate opened (it used to be asked for while the
    /// gate was still closed, and dropped); switching it OFF, or any other toggle, asks for nothing more.
    func testSwitchingHapticOnClicksAfterEnabling() {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("a2-toggle-\(UUID().uuidString)")
        let store = PlayerStore(args: LaunchArgs(), now: Date(), directory: dir, debounce: 0.05)
        let haptics = GateRecorder()
        haptics.enabled = store.state.settings.haptic
        XCTAssertTrue(haptics.enabled)
        XCTAssertFalse(ShellSettings.toggle(store: store, audio: SilentAudio(), haptics: haptics, \.haptic, name: "haptic"))
        XCTAssertEqual(haptics.plays.count, 0, "switching OFF plays nothing more")
        XCTAssertTrue(ShellSettings.toggle(store: store, audio: SilentAudio(), haptics: haptics, \.haptic, name: "haptic"))
        XCTAssertEqual(haptics.plays.count, 1)
        XCTAssertEqual(haptics.plays.first?.0, .button)
        XCTAssertEqual(haptics.plays.first?.1, true, "played with the gate already open")
        XCTAssertFalse(ShellSettings.toggle(store: store, audio: SilentAudio(), haptics: haptics, \.sound, name: "sound"))
        XCTAssertEqual(haptics.plays.count, 1, "the Sound toggle adds nothing (its GameButton plays the button haptic)")
    }

    /// Row 17: Play clicks with `play` (rigid 0.75), every other button with `button` (rigid 0.60).
    func testPlayAndButtonRows() {
        let map = AudioCueMap(lookup: { Tuning.load(bundle: .main).audio.file.value($0) })
        XCTAssertEqual(map.row(.play).style, .rigid)
        XCTAssertEqual(map.row(.play).intensity, 0.75, accuracy: 1e-9)
        XCTAssertEqual(map.row(.button).style, .rigid)
        XCTAssertEqual(map.row(.button).intensity, 0.60, accuracy: 1e-9)
        XCTAssertEqual(ui.file.double("homeReturn.claw.mergeHaptic", 0), 0.5, accuracy: 1e-9)
    }

    // MARK: the tab push-slide (motion-catalog §6.1 / §11.3)

    /// The strip: a cut into home jumps (no motion, only that page drawn); a tab change draws every page on the way (the
    /// 2-page jump draws Home in the middle), moves the model position to the target at once (SwiftUI animates the view).
    func testTheStripShowsEveryPageOnTheWay() async {
        let strip = HomeTabStrip.shared
        strip.jump(to: .shop)
        XCTAssertEqual(strip.position, 0)
        XCTAssertEqual(strip.shown, [.shop])
        strip.slide(to: .leaderboard, ui: ui)
        XCTAssertEqual(strip.position, 2)
        XCTAssertEqual(strip.shown, [.shop, .home, .leaderboard], "the 2-page jump passes through Home")
        XCTAssertTrue(strip.sliding)
        await strip.settled()
        XCTAssertFalse(strip.sliding)
        XCTAssertEqual(strip.shown, [.leaderboard], "at rest only the current page is drawn")
        strip.slide(to: .home, ui: ui)
        XCTAssertEqual(strip.shown, [.home, .leaderboard])
        strip.jump(to: .home)                                              // a cut during a slide wins
        XCTAssertEqual(strip.shown, [.home])
        XCTAssertFalse(strip.sliding)
        XCTAssertEqual(strip.position, 1)
    }

    // MARK: popup entrances (motion-catalog §3.2, §6.2, §11.2, §11.3; ruling 39 OD2)

    func testEveryPopupHasItsMeasuredEntrance() {
        let pay: PayAction = { false }
        let band = ContinueOffer(kind: .outOfTime, step: 1, price: 900, grant: .addTime(30), warning: .life)
        let plain = ContinueOffer(kind: .outOfTime, step: 0, price: 900, grant: .addTime(30), warning: .none)
        // the boxed family punches (v552 Paused at 60 Hz; v582 More Lives / offers / Level Failed)
        for r: PopupRequest in [.pause, .noLives, .boosterBuy("freeze"), .skyJump(.offer), .rocketRace(.offer),
                                .levelFailed(levels: [40], reason: .timeUp)] {
            guard case .punch(let keys, let a) = PopupEntrance.make(r, ui: ui) else { return XCTFail("\(r.id.rawValue) punches") }
            XCTAssertEqual(keys.last, 1.0, "\(r.id.rawValue) rests at 1")
            XCTAssertGreaterThan(keys.first ?? 0, 1.0, "\(r.id.rawValue): the first frame is already the big one")
            XCTAssertEqual(a.x, 196.6, accuracy: 0.2, "\(r.id.rawValue): about the panel's centre")
        }
        // the band family drops from above (v582 R1 / R5)
        for (r, first, over): (PopupRequest, Double, Double) in [(.quitLevel, -576, 28), (.continueOffer(band, pay: pay), -623, 32)] {
            guard case .drop(let keys) = PopupEntrance.make(r, ui: ui) else { return XCTFail("\(r.id.rawValue) drops") }
            XCTAssertEqual(keys.count, 18, "rest at +0.283 s (frame 17)")
            XCTAssertEqual(keys.first, first)
            XCTAssertEqual(keys.max(), over, "the overshoot below rest")
            XCTAssertEqual(keys.last, 0)
            XCTAssertTrue(PopupEntrance.isBand(r, ui: ui))
        }
        // instant (v552-verified) or with their own staged entrance
        for r: PopupRequest in [.settings, .outOfTime(plain, pay: pay), .continueOffer(plain, pay: pay), .editProfile, .username,
                                .unlockOverlay(FeatureID("pipe")), .skyJump(.matching), .streakRaceBoard, .weeklyContestTutorial,
                                .claimReward(Grant(coins: 10))] {
            XCTAssertEqual(PopupEntrance.make(r, ui: ui), .none, "\(r.id.rawValue) keeps its own entrance")
        }
    }

    /// The punch rows are the measured frames: Paused within 0.005 of v552 (S3-L092) and of v582 (S4-R1b), Level Failed its own
    /// v582 row; the keyed value at each 60 Hz frame is that frame's key, the last key afterwards.
    func testThePunchIsTheMeasuredCurve() {
        guard case .punch(let keys, _) = PopupEntrance.make(.pause, ui: ui) else { return XCTFail() }
        let v552 = [1.022, 0.980, 0.969, 0.967, 0.969, 0.976, 0.986, 0.995, 1.000]
        let v582 = [1.022, 0.984, 0.973, 0.967, 0.967, 0.973, 0.984, 0.995, 1.000]
        XCTAssertEqual(keys.count, 9, "0.133 s")
        for i in 0..<9 {
            XCTAssertEqual(keys[i], v552[i], accuracy: 0.005, "frame \(i) vs v552")
            XCTAssertEqual(keys[i], v582[i], accuracy: 0.005, "frame \(i) vs v582")
            XCTAssertEqual(PopupEntrance.value(keys, at: Double(i) / 60), keys[i], accuracy: 1e-9)
        }
        XCTAssertEqual(PopupEntrance.value(keys, at: 1.0), 1.0)
        guard case .punch(let failed, _) = PopupEntrance.make(.levelFailed(levels: [40], reason: .timeUp), ui: ui) else { return XCTFail() }
        XCTAssertEqual(failed, [1.049, 0.989, 0.984, 0.967, 0.965, 0.967, 0.978, 0.986, 0.995, 1.0])
    }

    /// A band that replaces a band inside the fail chain swaps its content (no second drop, v582 §11.2); a band after a
    /// boxed popup (Pause → Quit, Out of Time → Continue?) drops.
    func testABandAfterABandSwapsItsContent() async {
        let host = PopupHost(ui: ui)
        let pay: PayAction = { false }
        let token = ContinueOffer(kind: .outOfTime, step: 1, price: 900, grant: .addTime(30), warning: .token)
        let life = ContinueOffer(kind: .outOfTime, step: 2, price: 900, grant: .addTime(30), warning: .life)
        func presentAndRead(_ p: Popup<PopupResult>) async -> PopupEntrance? {
            let task = Task { await host.present(p) }
            for _ in 0..<50 where host.stack.isEmpty { await Task.yield() }
            let e = host.stack.last?.entrance
            if let id = host.stack.last?.id { host.answer(id, PopupResult.close) }
            _ = await task.value
            return e
        }
        let pause = await presentAndRead(.pause)
        guard case .punch = pause else { return XCTFail("Pause punches: \(String(describing: pause))") }
        let quit = await presentAndRead(.quitLevel)
        guard case .drop = quit else { return XCTFail("Pause → Quit: the band drops") }
        let second = await presentAndRead(.continueOffer(token, pay: pay))
        XCTAssertEqual(second, PopupEntrance.none, "band → band at once: the content swaps")
        try? await Task.sleep(nanoseconds: 300_000_000)
        let later = await presentAndRead(.continueOffer(life, pay: pay))
        guard case .drop = later else { return XCTFail("a band well after the last one drops again") }
    }

    /// The band exits (motion-catalog §11.2, v582): X = rise off the top with a 0.30 s linear dim fade; Quit / X on the last
    /// Continue? = fall off the bottom (a 2-frame lift first); X on a Continue? another step follows = content swap (no exit).
    func testTheBandsLeaveAsMeasured() {
        let pay: PayAction = { false }
        let middle = ContinueOffer(kind: .outOfTime, step: 1, price: 900, grant: .addTime(30), warning: .token, isLast: false)
        let last = ContinueOffer(kind: .outOfTime, step: 2, price: 900, grant: .addTime(30), warning: .life, isLast: true)
        guard case .rise(let up, let dim) = PopupExit.make(.quitLevel, answer: PopupResult.close, ui: ui) else { return XCTFail() }
        XCTAssertEqual(up.first, -73)
        XCTAssertEqual(up.count, 16, "gone after ≈ 0.27 s (easeOutQuad 0.302 s, 654 pt)")
        XCTAssertEqual(dim, 0.30, accuracy: 1e-9)
        XCTAssertEqual(zip(up, up.dropFirst()).filter { $1 >= $0 }.count, 0, "it only rises")
        guard case .fall(let down) = PopupExit.make(.quitLevel, answer: PopupResult.primary, ui: ui) else { return XCTFail() }
        XCTAssertEqual(Array(down.prefix(2)), [-27, -39], "the 2-frame lift")
        XCTAssertGreaterThan((down.last ?? 0) + 234, 852, "the band's top is below the screen at the end")
        XCTAssertEqual(PopupExit.make(.continueOffer(last, pay: pay), answer: PopupResult.close, ui: ui).map { $0.keys.first }, -27)
        XCTAssertNil(PopupExit.make(.continueOffer(middle, pay: pay), answer: PopupResult.close, ui: ui), "a next step swaps")
        guard case .rise = PopupExit.make(.continueOffer(last, pay: pay), answer: PopupResult.primary, ui: ui) else { return XCTFail() }
        XCTAssertNil(PopupExit.make(.pause, answer: PopupResult.close, ui: ui), "boxed popups close in one frame")
        XCTAssertEqual(PopupExit.rise(up, dimFade: 0.3).dim(at: 0.15), 0.5, accuracy: 1e-9, "the dim fades linearly")
        XCTAssertEqual(PopupExit.fall(down).offset(at: 0), -27)
        XCTAssertEqual(PopupExit.fall(down).offset(at: 1.0 / 60 + 0.001), -39)
    }

    /// The host: a cancelled band is answered at once and rises as a ghost (not presented: no input, not `isPresenting`); a
    /// band that goes on stays presented (input blocked) while it falls and is answered once it is gone.
    func testTheHostAnswersARiseAtOnceAndAFallWhenItIsGone() async {
        let host = PopupHost(ui: ui)
        let rise = Task { await host.present(Popup<PopupResult>.quitLevel) }
        for _ in 0..<50 where host.stack.isEmpty { await Task.yield() }
        guard let id = host.stack.last?.id else { return XCTFail("presented") }
        host.answer(id, PopupResult.close)
        let r = await rise.value
        XCTAssertEqual(r, .close)
        XCTAssertFalse(host.isPresenting, "answered at once: the level resumes under the rising band")
        XCTAssertEqual(host.leaving.count, 1)
        XCTAssertEqual(host.leaving.first?.ghost, true)
        try? await Task.sleep(nanoseconds: 450_000_000)
        XCTAssertTrue(host.leaving.isEmpty, "the ghost is gone after its rise")
        let fall = Task { await host.present(Popup<PopupResult>.quitLevel) }
        for _ in 0..<50 where host.stack.isEmpty { await Task.yield() }
        guard let id2 = host.stack.last?.id else { return XCTFail("presented") }
        let t0 = ProcessInfo.processInfo.systemUptime
        host.answer(id2, PopupResult.primary)
        XCTAssertTrue(host.isPresenting, "still presented while it falls: input stays blocked")
        host.answer(id2, PopupResult.close)                                   // a second answer during the exit is ignored
        let f = await fall.value
        XCTAssertEqual(f, .primary)
        XCTAssertGreaterThanOrEqual(ProcessInfo.processInfo.systemUptime - t0, 14.0 / 60, "answered once the band is gone")
        XCTAssertFalse(host.isPresenting)
    }

    /// The Pause toggle (motion-catalog §11.3 R6, v582): the knob slides 0.249 s easeInOutQuad; the track flips at 26.5 % of the
    /// travel from the OFF end (v582: 22-32 % turning ON, 68-78 % turning OFF); a reversal mid-way starts from where it is.
    func testTheToggleKnobSlidesAsMeasured() {
        XCTAssertEqual(ui.file.double("toggle.slide", 0), 0.249, accuracy: 1e-9)
        XCTAssertEqual(ui.file.double("toggle.flipAt", 0), 0.265, accuracy: 1e-9)
        let t0 = Date()
        let on = ToggleSlide(from: 0, to: 1, start: t0, duration: 0.249)
        XCTAssertEqual(on.position(t0), 0)
        XCTAssertEqual(Double(on.position(t0.addingTimeInterval(0.1245))), 0.5, accuracy: 1e-6, "easeInOutQuad: half way at half time")
        XCTAssertEqual(Double(on.position(t0.addingTimeInterval(0.249 * 0.25))), 0.125, accuracy: 1e-6)
        XCTAssertEqual(on.position(t0.addingTimeInterval(1)), 1)
        // the flip: 26.5 % of the travel is crossed at u ≈ 0.364 turning ON and ≈ 0.636 turning OFF (the 22-32 % / 68-78 %
        // of the WAY in v582's terms — the knob's distance, not time; both directions are the same position)
        let off = ToggleSlide(from: 1, to: 0, start: t0, duration: 0.249)
        XCTAssertGreaterThan(off.position(t0.addingTimeInterval(0.249 * 0.5)), 0.265)
        XCTAssertLessThan(off.position(t0.addingTimeInterval(0.249 * 0.8)), 0.265)
    }

    // MARK: the unlock dismiss (contract amend 4, motion-catalog §6.7)

    func testTheUnlockDismissCutsTheContentAndFadesTheDim() {
        let b = ui.unlockBeats
        XCTAssertEqual(b.dismissMode, .contentCut)
        XCTAssertEqual(b.dismissFade, 0.233, accuracy: 1e-9)
        let host = PopupHost(ui: ui)
        host.fadeDim(7, over: 0.233)
        XCTAssertEqual(host.dimFading[7] ?? 0, 0.233, accuracy: 1e-9)
    }
}

/// Records each haptic request with the gate's state at that moment.
@MainActor private final class GateRecorder: HapticPlaying {
    var enabled = true
    var plays: [(Haptic, Bool)] = []
    func prepare() {}
    func play(_ h: Haptic) { plays.append((h, enabled)) }
}
