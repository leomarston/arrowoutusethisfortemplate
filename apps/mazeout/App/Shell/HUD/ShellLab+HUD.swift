import SwiftUI
import PathCore

// SHELL S2 lab pages for the HUD (SPEC-architecture §9.5 ShellLab: "the HUD states (normal / Hard / Super Hard, hearts 3/2/1,
// frozen)"). Fixed data, Debug hook only (`-pc.go shelllab -pc.lab <page>`); GAME's HUDWriter is not involved: the lab writes
// the same HUDModel the level screen reads.
//   hud:normal|hard|superHard   Level 32 · 3:00 / Level 34 · 3:30 / Level 39 · 3:00, coins 2240, boosters 3 / 3 (shots 003 / 036 / 061)
//   hud:hearts2 | hud:hearts1   the same with one / two hearts lost (the recessed slots)
//   hudIntro                    the intro from K = the page's first frame + 0.5 s (`-pc.freezeAt hudIntro@t` holds it); logs beats
//   hudBreak                    a heart breaks every 1.5 s (the halves at `-pc.freezeAt`-free speed; the log names each)
//   hudSoak                     60 s of simulated play written the HUDWriter way (the timer text only when the displayed second
//                               changes, hearts / boosters / coins on events): counts the model's writes and the HUD row's
//                               renders per second and logs `[PC][hud] soak …` (acceptance "HUD writes ≤ 10 Hz")

struct HUDLabPage: View {
    enum Kind: Equatable { case still(LevelTag, hearts: Int), intro, breaking, breakOnce, soak }
    let kind: Kind
    @Environment(AppModel.self) private var app

    var body: some View {
        ZStack(alignment: .topLeading) {
            Color.white
            HUDView(model: app.hud, actions: HUDActions(back: { Log.mark("lab", "hud back") }, pause: { Log.mark("lab", "hud pause") },
                                                        booster: { Log.mark("lab", "hud booster \($0.rawValue)") }))
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shelllab")
        .task { await run() }
    }

    private func run() async {
        let hud = app.hud
        S2Hooks.app = app
        switch kind {
        case .still(let tag, let hearts):
            HUDLab.fill(hud, tag: tag, hearts: hearts)
            await S2LabReady.visible(app)
            CaptureReady.mark(screen: "shelllab:hud:\(tag.rawValue):\(hearts)", app: app, file: "lab-ready.json")
            Log.mark("lab", "shelllab:hud done")
        case .intro:
            HUDLab.fill(hud, tag: .normal, hearts: 3)
            hud.introPhase = .hidden
            await S2LabReady.visible(app)
            try? await Task.sleep(nanoseconds: 500_000_000)
            let k = app.clock.gameTime()
            hud.introPhase = .playing(start: k)
            Log.mark("hud", "intro K at game time \(String(format: "%.4f", k))")
            if app.args.freezeAt?.sequence == "hudIntro" {
                while app.clock.frozenAt == nil { try? await Task.sleep(nanoseconds: 16_000_000) }
            } else {
                try? await Task.sleep(nanoseconds: 2_200_000_000)
            }
            if app.args.raw["pc.feelShown"] != nil {
                // FEEL item 3: the rest phase written after the intro (.playing → .shown) must not rebuild the HUD (the frame
                // monitor, `-pc.frameWatch 1`, logs any frame > 20 ms around this write)
                Log.mark("hud", "lab write introPhase .shown (K + \(String(format: "%.3f", app.clock.gameTime() - k)) s)")
                hud.introPhase = .shown
                try? await Task.sleep(nanoseconds: 600_000_000)
                hud.introPhase = .playing(start: app.clock.gameTime() - 5)       // and back (an intro that is already over)
                Log.mark("hud", "lab write introPhase .playing (at rest)")
                try? await Task.sleep(nanoseconds: 600_000_000)
            }
            await FrameWaiter.frames(2)
            CaptureReady.mark(screen: "shelllab:hudIntro", app: app, file: "lab-ready.json")
            Log.mark("lab", "shelllab:hudIntro done")
        case .breaking:
            HUDLab.fill(hud, tag: .normal, hearts: 3)
            await S2LabReady.visible(app)
            for lost in 1...3 {
                try? await Task.sleep(nanoseconds: 1_500_000_000)
                hud.hearts = (0..<3).map { $0 < 3 - lost ? .full : .lost }
                Log.mark("hud", "lab write hearts \(3 - lost)")
            }
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            hud.hearts = [.full, .full, .full]
            Log.mark("hud", "lab write hearts refill")
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            CaptureReady.mark(screen: "shelllab:hudBreak", app: app, file: "lab-ready.json")
            Log.mark("lab", "shelllab:hudBreak done")
        case .breakOnce:
            // one bump contact: heart 3 breaks (`-pc.freezeAt heartBreak@τ` holds the halves at τ)
            HUDLab.fill(hud, tag: .normal, hearts: 3)
            await S2LabReady.visible(app)
            try? await Task.sleep(nanoseconds: 400_000_000)
            hud.hearts = [.full, .full, .lost]
            Log.mark("hud", "lab write hearts 2 (contact)")
            if app.args.freezeAt?.sequence == "heartBreak" {
                while app.clock.frozenAt == nil { try? await Task.sleep(nanoseconds: 16_000_000) }
            } else {
                try? await Task.sleep(nanoseconds: 800_000_000)
            }
            await FrameWaiter.frames(2)
            CaptureReady.mark(screen: "shelllab:hudBreak:once", app: app, file: "lab-ready.json")
            Log.mark("lab", "shelllab:hudBreak:once done")
        case .soak:
            await HUDLab.soak(app)
        }
    }
}

@MainActor enum HUDLab {
    static func fill(_ hud: HUDModel, tag: LevelTag, hearts: Int) {
        let level = tag == .normal ? 32 : (tag == .hard ? 34 : 39)
        let secs = tag == .hard ? 210 : 180
        hud.levelLabel = "Level \(level)"
        hud.tag = tag
        hud.timerSeconds = secs
        hud.timerText = HUDLab.text(secs)
        hud.timerFrozen = true
        hud.hearts = (0..<3).map { $0 < hearts ? .full : .lost }
        hud.coins = 2240
        hud.boosters = [BoosterSlotVM(id: .freeze, state: .stock(3)), BoosterSlotVM(id: .hint, state: .stock(3))]
        hud.introPhase = .shown
        hud.isVisible = true
    }

    /// "m:ss" with no leading zero on the minutes (SPEC-motion-audio §4).
    static func text(_ s: Int) -> String { "\(s / 60):" + String(format: "%02d", s % 60) }

    /// 60 s of play written the HUDWriter way; counts writes (Observation) and top-row renders; logs the rates.
    static func soak(_ app: AppModel) async {
        let hud = app.hud
        fill(hud, tag: .normal, hearts: 3)
        await S2LabReady.visible(app)
        let meter = HUDWriteMeter(hud)
        meter.start()
        let renders0 = HUDRenderCounter.renders
        let probe = FrameProbe("hud soak")
        probe.start()
        let duration = Double(app.args.raw["pc.soakSeconds"].flatMap(Double.init) ?? 60)
        let t0 = ProcessInfo.processInfo.systemUptime
        var remaining = 180.0
        var shown = 180
        var nextEvent = 7.0
        var hearts = 3
        var tick = 0
        while ProcessInfo.processInfo.systemUptime - t0 < duration {
            try? await Task.sleep(nanoseconds: 16_666_667)            // a display-link-like 60 Hz loop, as the session ticks
            tick += 1
            let now = ProcessInfo.processInfo.systemUptime - t0
            remaining = max(0, 180 - now)
            let disp = Int(ceil(remaining))
            if disp != shown {                                         // the ≤ 10 Hz rule: write only when the second changes
                shown = disp
                hud.timerSeconds = disp
                hud.timerText = text(disp)
            }
            if now >= nextEvent {                                      // an event now and then: a bump, a booster, coins
                nextEvent += 7
                switch Int(now / 7) % 3 {
                case 0:
                    hearts = hearts > 1 ? hearts - 1 : 3
                    hud.hearts = (0..<3).map { $0 < hearts ? .full : .lost }
                case 1:
                    hud.boosters = [BoosterSlotVM(id: .freeze, state: .stock(Int(now) % 3 + 1)), BoosterSlotVM(id: .hint, state: .stock(3))]
                default:
                    hud.coins += 20
                }
            }
        }
        probe.stop()
        meter.stop()
        let secs = ProcessInfo.processInfo.systemUptime - t0
        let renders = HUDRenderCounter.renders - renders0
        let writes = meter.writes
        Log.mark("hud", "soak \(String(format: "%.1f", secs)) s: model writes \(writes) (\(String(format: "%.2f", Double(writes) / secs)) Hz, max \(meter.maxPerSecond)/s) · top-row renders \(renders) (\(String(format: "%.2f", Double(renders) / secs)) Hz) · loop ticks \(tick)")
        let payload: [String: Any] = ["seconds": secs, "writes": writes, "writesHz": Double(writes) / secs, "maxWritesPerSecond": meter.maxPerSecond,
                                      "renders": renders, "rendersHz": Double(renders) / secs, "ticks": tick, "fields": meter.byField]
        if let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first,
           let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys, .prettyPrinted]) {
            try? data.write(to: docs.appendingPathComponent("hud-soak.json"), options: .atomic)
        }
        CaptureReady.mark(screen: "shelllab:hudSoak", app: app, file: "lab-ready.json")
        Log.mark("lab", "shelllab:hudSoak done")
    }
}

/// Counts HUDModel writes through Observation (every write to a tracked field fires `onChange` once; tracking re-arms at once).
/// Usable on the real level screen too (V3: attach it under `-pc.hud debug`).
@MainActor final class HUDWriteMeter {
    private let hud: HUDModel
    private var running = false
    private(set) var writes = 0
    private(set) var byField: [String: Int] = [:]
    private var perSecond: [Int: Int] = [:]
    private let t0 = ProcessInfo.processInfo.systemUptime

    init(_ hud: HUDModel) { self.hud = hud }

    var maxPerSecond: Int { perSecond.values.max() ?? 0 }

    func start() { running = true; arm() }
    func stop() { running = false }

    private func arm() {
        guard running else { return }
        let fields: [(String, () -> Void)] = [
            ("levelLabel", { _ = self.hud.levelLabel }), ("tag", { _ = self.hud.tag }), ("timerText", { _ = self.hud.timerText }),
            ("timerSeconds", { _ = self.hud.timerSeconds }), ("timerFrozen", { _ = self.hud.timerFrozen }),
            ("hearts", { _ = self.hud.hearts }), ("coins", { _ = self.hud.coins }), ("boosters", { _ = self.hud.boosters }),
            ("introPhase", { _ = self.hud.introPhase }), ("isVisible", { _ = self.hud.isVisible }),
        ]
        for (name, read) in fields { track(name, read) }
    }

    private func track(_ name: String, _ read: @escaping () -> Void) {
        withObservationTracking { read() } onChange: { [weak self] in
            Task { @MainActor in
                guard let self, self.running else { return }
                self.writes += 1
                self.byField[name, default: 0] += 1
                self.perSecond[Int(ProcessInfo.processInfo.systemUptime - self.t0), default: 0] += 1
                self.track(name, read)
            }
        }
    }
}
