// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
import SwiftUI
import PathCore

// SHELL S2 lab pages (SPEC-architecture §9.5 ShellLab: "the win panels, the unlock overlays"; Debug hook only). Each writes
// Documents/lab-ready.json when its state is on screen. `-pc.go shelllab -pc.lab <page>`:
//   hud:<tag>, hud:hearts2, hud:hearts1, hudIntro, hudBreak, hudSoak      (ShellLab+HUD.swift)
//   celebrate:<normal|hard|superHard>   the level HUD over white, W = first frame + 0.6 s: the celebration, then the win panel at
//                                       W + 3.94 (the WinDirector's order); `-pc.freezeAt win@t` holds any beat; a tap skips
//   unlock:<feature>                    the level HUD, then the unlock overlay (its beats are logged)
//   tutorial                            the "Tap to move!" caption + hand over a white board, fingertip at (193, 424) (V1 L1)
//   race                                the win panel with a Rocket Race joined (lanes fixed to shot 171's standings)
//   popups:<tr|en>                      a contact sheet is not built: use `-pc.popup <id>` (the real host) for every panel

@MainActor enum S2Lab {
    static func make(_ page: String?, app: AppModel) -> AnyView? {
        guard let page else { return nil }
        let parts = page.split(separator: ":", maxSplits: 1).map(String.init)
        let arg = parts.count > 1 ? parts[1] : nil
        switch parts[0] {
        case "hud":
            switch arg {
            case "hearts2": return AnyView(HUDLabPage(kind: .still(.normal, hearts: 2)))
            case "hearts1": return AnyView(HUDLabPage(kind: .still(.normal, hearts: 1)))
            default: return AnyView(HUDLabPage(kind: .still(LevelTag(label: arg) ?? .normal, hearts: 3)))
            }
        case "hudIntro": return AnyView(HUDLabPage(kind: .intro))
        case "hudBreak": return AnyView(HUDLabPage(kind: arg == "once" ? .breakOnce : .breaking))
        case "hudSoak": return AnyView(HUDLabPage(kind: .soak))
        case "celebrate": return AnyView(CelebrationLabPage(tag: LevelTag(label: arg) ?? .normal))
        case "unlock": return AnyView(UnlockLabPage(feature: FeatureID(arg ?? "pipe")))
        case "tutorial": return AnyView(TutorialLabPage())
        case "race": return AnyView(RaceLabPage())
        case "freeze": return AnyView(FreezeLabPage())
        default: return nil
        }
    }
}

/// The WinDirector's order on a white board with the HUD: celebration at W, `finished` → the win panel.
private struct CelebrationLabPage: View {
    let tag: LevelTag
    @Environment(AppModel.self) private var app

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.white
            HUDView(model: app.hud)
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shelllab")
        .task {
            S2Hooks.app = app
            HUDSample.fill(app.hud, tag: tag, hearts: 3)
            if !LogoPartsWait.done { await LogoPartsWait.wait() }
            await S2LabReady.visible(app)
            try? await Task.sleep(nanoseconds: 600_000_000)
            let handle = app.fx.play(.celebration(tag))
            Log.mark("win", "lab W (celebration \(tag.rawValue))")
            if let f = app.args.freezeAt, f.sequence == "win", f.t < CelebrationRun.Beats(app.tuning.ui.file).panelAt {
                // held before the panel: the capture is the celebration itself, pinned at W + t
                while app.clock.frozenAt == nil { try? await Task.sleep(nanoseconds: 16_000_000) }
                await FrameWaiter.frames(3)
                CaptureReady.mark(screen: "shelllab:celebrate:\(tag.rawValue)@\(f.t)", app: app, file: "lab-ready.json")
                Log.mark("lab", "shelllab:celebrate frozen at W+\(f.t)")
                return
            }
            await app.fx.finished(handle)
            let level = tag == .normal ? 32 : (tag == .hard ? 34 : 39)
            let reward = tag == .normal ? 20 : (tag == .hard ? 60 : 100)
            Task { @MainActor in
                await FrameWaiter.frames(4)
                CaptureReady.mark(screen: "shelllab:celebrate:\(tag.rawValue):panel", app: app, file: "lab-ready.json")
                Log.mark("lab", "shelllab:celebrate done")
            }
            let r = await app.popups.present(Popup<PopupResult>.winPanel(WinSummary(levels: [level], reward: reward, tag: tag,
                                                                                    outcomes: [.multiplier(from: 5, to: 10)])))
            Log.mark("win", "lab panel → \(r)")
        }
    }
}

@MainActor enum S2LabReady {
    /// Waits until the router has shown the first screen (the lab page mounts under Loading and runs its task there).
    static func visible(_ app: AppModel) async {
        for _ in 0..<600 {
            if let r = app.router as? Router, r.firstScreenShown { break }
            try? await Task.sleep(nanoseconds: 16_000_000)
        }
        await FrameWaiter.frames(2)
    }
}

@MainActor enum LogoPartsWait {
    static var done: Bool { LogoParts.ready != nil }
    static func wait() async {
        LogoParts.prepare()
        for _ in 0..<200 where LogoParts.ready == nil { try? await Task.sleep(nanoseconds: 20_000_000) }
    }
}

private struct UnlockLabPage: View {
    let feature: FeatureID
    @Environment(AppModel.self) private var app

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.white
            HUDView(model: app.hud)
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shelllab")
        .task {
            S2Hooks.app = app
            HUDSample.fill(app.hud, tag: .normal, hearts: 3)
            app.hud.levelLabel = "Level 35"
            await S2LabReady.visible(app)
            Task { @MainActor in
                if app.args.freezeAt?.sequence == "unlock" {
                    while app.clock.frozenAt == nil { try? await Task.sleep(nanoseconds: 16_000_000) }
                } else {
                    try? await Task.sleep(nanoseconds: 1_600_000_000)
                }
                await FrameWaiter.frames(2)
                CaptureReady.mark(screen: "shelllab:unlock:\(feature.rawValue)", app: app, file: "lab-ready.json")
                Log.mark("lab", "shelllab:unlock done")
            }
            let r = await app.popups.present(Popup<PopupResult>.unlockOverlay(feature))
            Log.mark("unlock", "lab overlay → \(r)")
        }
    }
}

private struct TutorialLabPage: View {
    @Environment(AppModel.self) private var app
    @State private var hint = TutorialHint()

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.white
            // a stand-in board is NOT drawn: the hint alone over the white ground (the board is BOARD's)
            TutorialLayer(hint: hint)
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shelllab")
        .task {
            await S2LabReady.visible(app)
            hint.show(caption: "Tap to move!", fingertip: CGPoint(x: 193, y: 424), clock: app.clock)
            if app.args.freezeAt?.sequence == "caption" {
                while app.clock.frozenAt == nil { try? await Task.sleep(nanoseconds: 16_000_000) }
            } else {
                try? await Task.sleep(nanoseconds: 1_200_000_000)
            }
            await FrameWaiter.frames(2)
            CaptureReady.mark(screen: "shelllab:tutorial", app: app, file: "lab-ready.json")
            Log.mark("lab", "shelllab:tutorial done")
        }
    }
}

/// The win panel with a Rocket Race joined (the lab's fixed standings = shot 171).
private struct RaceLabPage: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.white
            HUDView(model: app.hud)
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shelllab")
        .task {
            HUDSample.fill(app.hud, tag: .normal, hearts: 3)
            app.hud.levelLabel = "Level 55"
            await S2LabReady.visible(app)
            RocketRaceStripSource.provider = { _ in
                RocketRaceStripData(lanes: [RaceLaneVM(rank: 5, name: "Nope", avatar: 0, progress: 0, isMe: false),
                                            RaceLaneVM(rank: 4, name: "Hsheh", avatar: 0, progress: 1, isMe: true),
                                            RaceLaneVM(rank: 3, name: "lady", avatar: 1, progress: 3, isMe: false),
                                            RaceLaneVM(rank: 2, name: "DSMShark", avatar: 1, progress: 3, isMe: false),
                                            RaceLaneVM(rank: 1, name: "muffinman", avatar: 0, progress: 4, isMe: false)],
                                    goal: 5, timeLeft: "6h 9m")
            }
            await FrameWaiter.frames(3)
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: 1_200_000_000)
                await FrameWaiter.frames(2)
                CaptureReady.mark(screen: "shelllab:race", app: app, file: "lab-ready.json")
                Log.mark("lab", "shelllab:race done")
            }
            _ = await app.popups.present(Popup<PopupResult>.winPanel(WinSummary(levels: [55], reward: 20, tag: .normal)))
            RocketRaceStripSource.provider = nil
        }
    }
}

/// The Time Freeze HUD bits at B = first frame + 0.5 s (`-pc.freezeAt freeze@t` is not wired: capture with `-pc.slowmo`).
private struct FreezeLabPage: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.white
            HUDView(model: app.hud)
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shelllab")
        .task {
            S2Hooks.app = app
            HUDSample.fill(app.hud, tag: .normal, hearts: 3)
            app.hud.levelLabel = "Level 62"
            await S2LabReady.visible(app)
            try? await Task.sleep(nanoseconds: 500_000_000)
            app.hud.boosters = [BoosterSlotVM(id: .freeze, state: .active), BoosterSlotVM(id: .hint, state: .stock(3))]
            let h = app.fx.play(.custom(id: "freeze", params: ["seconds": 10]))
            Log.mark("lab", "freeze B")
            let wait = Double(app.args.raw["pc.freezeWait"].flatMap(Double.init) ?? 7.6)
            try? await Task.sleep(nanoseconds: UInt64(wait * 1_000_000_000))
            await FrameWaiter.frames(2)
            CaptureReady.mark(screen: "shelllab:freeze@\(wait)", app: app, file: "lab-ready.json")
            await app.fx.finished(h)
            Log.mark("lab", "shelllab:freeze done")
        }
    }
}
#endif
