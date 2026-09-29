import SwiftUI
import PathCore

// SHELL S2 (SPEC-architecture §6.5; SPEC-ui §2.3.1-§2.3.2, VERIFIED 003 normal / 036 Hard / 061 Super Hard; SPEC-motion-audio §3.6,
// §4). The level HUD, z 1 over the board (GAME's GameScreen places it: `HUDView(model: app.hud, actions: …)`):
//   top row (top-anchored, drops in together): the coin group · the back button (tier colour) · the light-blue panel 78.4 · 60.4 ·
//     236.5 · 59.4 with the "Level N" tab 149.5 · 54 · 94.4 · 23 (tier colour), the stopwatch + timer pill (always blue) and the
//     three hearts · the pause button (tier colour)
//   booster corners (bottom-anchored): freeze left, hint right
// The views read ONLY `HUDModel` (written by GAME's HUDWriter ≤ 10 Hz; nothing on a tap frame) and never touch the session.
// The intro (`introPhase == .playing(start: K)`) is a TimelineView on the MotionClock (slow motion and `-pc.freezeAt hudIntro@t`
// act on it); at rest there is no timeline, so an idle HUD costs the main thread nothing. The row's parts are Equatable views:
// a timer tick re-renders only the pill, a heart change only the hearts. No "Hard Level" tag inside the HUD (SPEC.md §5 item 10).

/// What the HUD's buttons do (GAME supplies them; the default does nothing).
struct HUDActions {
    var back: () -> Void = {}
    var pause: () -> Void = {}
    var booster: (BoosterID) -> Void = { _ in }
    init(back: @escaping () -> Void = {}, pause: @escaping () -> Void = {}, booster: @escaping (BoosterID) -> Void = { _ in }) {
        self.back = back; self.pause = pause; self.booster = booster
    }
}

struct HUDView: View {
    let model: HUDModel
    var actions = HUDActions()
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    /// The intro start whose timeline has finished (the timeline then pauses: no per-frame work at rest).
    @State private var introDoneFor: Double?

    init(model: HUDModel, actions: HUDActions = HUDActions()) {
        self.model = model
        self.actions = actions
    }

    var body: some View {
        let motion = app.tuning.ui.hudMotion
        let phase = model.introPhase
        let start: Double? = { if case .playing(let s) = phase { return s }; return nil }()
        LayerStack {                                               // FIX-2 A (V3-05): no alignment walk (GameScreen.swift)
            FreezeFrost()                                          // under the HUD, over the board (Time Freeze)
            // FIX-2 A (V3-05): the HUD stays BUILT between Plays (the level screen is parked, Router `parkLevel`) and is hidden
            // while not visible (opacity 0, no input, out of the accessibility tree) — `if model.isVisible` rebuilt the whole HUD
            // subtree at every level start, inside the Play cut's commit (build/p/FIX2/A/tp/v5-tp1: the HUD's ZStack sizing).
                // FEEL item 3: ONE structural path for every intro phase. A phase write (.hidden → .playing, .playing → .shown)
                // only changes `introT` and pauses / resumes the timeline: the HUD subtree keeps its identity and is never
                // rebuilt (a `switch` here swapped the whole row's view branch: a measured 37–40 ms frame at K + 1.96 s, G1).
                TimelineView(.animation(minimumInterval: nil, paused: start == nil || introDoneFor == start)) { ctx in
                    let t: Double? = start.map { app.clock.sequenceTime("hudIntro", app.clock.gameTime(ctx.date) - $0) }
                    let done = t.map { $0 >= motion.introEnd } ?? true
                    HUDLayers(model: model, actions: actions, introT: phase == .hidden ? 0 : (done ? nil : t), motion: motion)
                        .background {
                            if let t, let start {
                                HUDIntroLog.Probe(t: t, motion: motion, onRest: done && introDoneFor != start ? {
                                    Task { @MainActor in introDoneFor = start }
                                } : nil)
                            }
                        }
                }
                .opacity(model.isVisible ? 1 : 0)
                .allowsHitTesting(model.isVisible)
                .accessibilityShown(model.isVisible)
            CelebrationSkip()
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .onAppear { if S2Hooks.app == nil { S2Hooks.app = app } }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("hud")
    }
}

/// The HUD at one instant of the intro (`introT` = seconds since K) or at rest (nil).
private struct HUDLayers: View {
    let model: HUDModel
    let actions: HUDActions
    let introT: Double?
    let motion: HUDMotion
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let drop = introT.map { motion.dropOffset($0) } ?? 0
        let slide = introT.map { motion.boosterOffset($0) } ?? 0
        let slots = model.boosters
        LayerStack {                                                // FIX-2 A (V3-05): the same top-leading placement, no walk
            ZStack(alignment: .topLeading) {
                HUDCoinGroup(coins: model.coins, t: t, m: m).equatable()
                HUDTopRow(model: model, actions: actions, introT: introT, motion: motion)
            }
            .offset(y: CGFloat(drop) * m.s)
            if let left = slots.first(where: { $0.id == .freeze }) ?? slots.first {
                BoosterCornerView(slot: left, side: .left, t: t, m: m, action: actions.booster).equatable()
                    .offset(x: -CGFloat(slide) * m.s)
            }
            if let right = slots.first(where: { $0.id == .hint }) ?? (slots.count > 1 ? slots[1] : nil) {
                BoosterCornerView(slot: right, side: .right, t: t, m: m, action: actions.booster).equatable()
                    .offset(x: CGFloat(slide) * m.s)
            }
        }
    }
}

/// Back · panel (tab, stopwatch + timer, hearts) · pause.
private struct HUDTopRow: View {
    let model: HUDModel
    let actions: HUDActions
    let introT: Double?
    let motion: HUDMotion
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let tag = model.tag
        let palette = TierPalette.of(tag)
        let timerScale: Double? = introT.map { motion.timerScale($0) } ?? 1
        let _ = HUDRenderCounter.count()
        ZStack(alignment: .topLeading) {
            GameButton(id: "hud.back", label: "Back", action: actions.back) { TierSquareButton(palette: palette, glyph: .back) }
                .placed(square(t.rect("hud.backButton", CGRect(19.0, 68.4, 40.0, 40.0), .top, m)))
                .anchor(.back)
            HUDPanel(t: t, m: m).equatable()
                .anchor(.custom("hud.panel"))
            HUDLevelTab(label: model.levelLabel.map { String(localized: $0) } ?? "", resource: model.levelLabel, tag: tag, t: t, m: m)
                .equatable()
                .anchor(.levelTab)
            HUDTimerLeaf(model: model, scale: timerScale, t: t, m: m)             // FIX-2 A (V3-04): reads the time itself
                .anchor(.timerPill)
            HUDHeartsRow(hearts: model.hearts, introT: introT, motion: motion, t: t, m: m)
                .anchor(.hearts)
            GameButton(id: "hud.pause", label: "Pause", action: actions.pause) { TierSquareButton(palette: palette, glyph: .pause) }
                .placed(square(t.rect("hud.pauseButton", CGRect(334.3, 68.1, 40.4, 40.0), .top, m)))
                .anchor(.pause)
        }
    }

    /// The square button draws a 40 pt body in a 44 pt frame: centre that frame on the measured body.
    private func square(_ r: CGRect) -> CGRect { CGRect(x: r.midX - 22, y: r.midY - 22, width: 44, height: 44) }
}

/// FIX-2 A (V3-04): the timer pill as its own leaf — it is the only view that reads the time, so a tick re-renders the pill,
/// not the whole top row (HUDTopRow re-ran every second in play: V3's timer-tick profile).
private struct HUDTimerLeaf: View {
    let model: HUDModel
    let scale: Double?
    let t: Tokens
    let m: ShellMetrics

    var body: some View {
        HUDTimerPill(text: model.timerText, scale: scale, t: t, m: m).equatable()
            .accessibilityElement(children: .ignore)
            .accessibilityIdentifier("hud.timer")
            .accessibilityValue(Text(verbatim: "\(model.timerSeconds)"))
    }
}

/// The light-blue HUD panel (always blue, VERIFIED 003/036/061): rr 18.3, #BDDCFF face, a dark #5983CE outline, a bright top rim,
/// a darker lower lip #517CC9 → #80A6E9 and a soft grey shadow (dy 2, σ 1.33, α 0.47).
private struct HUDPanel: View, Equatable {
    let t: Tokens
    let m: ShellMetrics
    static func == (a: HUDPanel, b: HUDPanel) -> Bool { a.m == b.m }

    var body: some View {
        let r = t.rect("hud.panel", CGRect(78.4, 60.4, 236.5, 59.4), .top, m)
        Rasterized("hudPanel", overflow: 4) { _ in panelArt(radius: t.radius("hud.panel", 18.27) * m.s) }
            .placed(r)
            .allowsHitTesting(false)
    }

    private func panelArt(radius: CGFloat) -> some View {
        // VERIFIED 003 columns: the top edge a thin blue line (#8AAFEC) then a bright #EEF6FF line into the face #BDDCFF; the
        // sides a ≈ 4 pt rim darkening outwards; a ≈ 4.3 pt lower lip #80A6E9 → #517CC9; a soft grey shadow below (≈ 3.5 pt)
        let outer = RoundedRectangle(cornerRadius: radius, style: .continuous)
        let face = RoundedRectangle(cornerRadius: max(1, radius - 3.4), style: .continuous)
        return ZStack {
            outer.fill(t.color("hud.panelShadow", 0x7A8C88).opacity(0.47)).offset(y: 2).blur(radius: 1.33)
            outer.fill(LinearGradient(stops: t.stops("hud.panelRimV", [(0, 0x68BCB6), (0.03, 0x9DD3CC), (0.5, 0x80CAC6), (0.9, 0x5CB4AC),
                                                                       (0.95, 0x408F86), (1, 0x398981)]),
                                      startPoint: .top, endPoint: .bottom))
            face.fill(LinearGradient(stops: t.stops("hud.panelBody", [(0, 0xEFF7F5), (0.03, 0xE8F3F0), (0.07, 0xC9E4DD), (0.1, 0xC0E0D8),
                                                                       (1.0, 0xC0E0D8)]),
                                     startPoint: .top, endPoint: .bottom))
                .padding(EdgeInsets(top: 1.8, leading: 3.4, bottom: 4.6, trailing: 3.4))
                .blur(radius: 0.9)
            face.fill(t.color("hud.panel", 0xC0E0D8))
                .padding(EdgeInsets(top: 5.0, leading: 5.2, bottom: 5.8, trailing: 5.2))
                .blur(radius: 1.2)
        }
    }
}

/// The "Level N" tab in the tier colour (SPEC-ui §2.3.1: blue #008EFE / red #FF3C3D / purple #A628E7; outline #002985 /
/// #5B0000 / #3E006E), label 17.9 / −0.5 (box 84) at baseline 70.7.
private struct HUDLevelTab: View, Equatable {
    let label: String
    let resource: LocalizedStringResource?
    let tag: LevelTag
    let t: Tokens
    let m: ShellMetrics
    static func == (a: HUDLevelTab, b: HUDLevelTab) -> Bool { a.label == b.label && a.tag == b.tag && a.m == b.m }

    var body: some View {
        let r = t.rect("hud.levelTab", CGRect(149.5, 54.0, 94.4, 23.0), .top, m)
        let key = tag == .normal ? "hud.levelTab" : (tag == .hard ? "hud.levelTabHard" : "hud.levelTabSuperHard")
        let outline: UInt32 = tag == .normal ? 0x00393D : (tag == .hard ? 0x560C00 : 0x4F0F2B)
        let style = t.text(key + ".label", .s2(17.9, -0.5, [0xFFF9EF, 0xFFF4E0, 0xFDEDCF], outline: outline, 0.65, drop: 0.73))
            .sized(17.9 * m.s)
        let p = t.textPoint(key + ".label", baseline: 70.7, centreX: 196.8)
        let at = m.point(CGPoint(x: p.x, y: p.baseline), .top)
        ZStack(alignment: .topLeading) {
            Rasterized("hudTab|\(tag.rawValue)", overflow: 1) { _ in tabArt(key: key, radius: t.radius("hud.levelTab", 4.92) * m.s) }
                .placed(r)
            if let resource {
                GameText(resource, style: style, maxWidth: CGFloat(t.textMaxWidth(key + ".label", 84) ?? 84) * m.s)
                    .at(at.x, style.capCentre(baseline: at.y))
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("hud.level")
        .accessibilityLabel(Text(verbatim: label))
        .accessibilityValue(Text(verbatim: label))
    }

    private func tabArt(key: String, radius: CGFloat) -> some View {
        let d: [(Double, UInt32)]
        switch tag {
        case .normal:
            d = [(0, 0x00393D), (0.03, 0x264F4D), (0.059, 0x6EBFB0), (0.074, 0x6CCCBD), (0.088, 0x5EC8B9), (0.118, 0x05A99A),
                 (0.132, 0x00A293), (0.868, 0x009B8E), (0.926, 0x006D6A), (0.956, 0x006A67), (0.971, 0x00484F), (1.0, 0x004046)]
        case .hard:
            d = [(0, 0x990101), (0.06, 0xA82A1C), (0.083, 0xE59B90), (0.097, 0xEEA69B), (0.153, 0xED6653), (0.847, 0xEE3E29),
                 (0.903, 0x960101), (0.944, 0x730A00), (1.0, 0x7D140D)]
        case .superHard:
            d = [(0, 0x890F51), (0.06, 0xAC2A6B), (0.083, 0xF76D9F), (0.097, 0xFF77A8), (0.153, 0xE42180), (0.847, 0xB81B6E),
                 (0.903, 0x771345), (0.944, 0x5B0E32), (1.0, 0x791347)]
        }
        let outline: UInt32 = tag == .normal ? 0x00393D : (tag == .hard ? 0x85120B : 0x5B0E32)
        return ZStack {
            RoundedRectangle(cornerRadius: radius, style: .continuous).fill(t.color(key + "Outline", outline))
            RoundedRectangle(cornerRadius: max(1, radius - 1), style: .continuous)
                .fill(LinearGradient(stops: t.stops(key + "Face", d), startPoint: .top, endPoint: .bottom))
                .padding(EdgeInsets(top: 0.4, leading: 1.2, bottom: 0.4, trailing: 1.2))
        }
    }
}

// MARK: - instrumentation (the §6.5 "≤ 10 Hz" acceptance, the intro log)

/// Counts evaluations of the HUD top row (a re-render happens only when a field it reads was written).
enum HUDRenderCounter {
    nonisolated(unsafe) static var renders = 0
    static func count() { renders += 1 }
}

/// Logs the intro's beats on the first presented frame at or after each one (`[PC][hud] intro <beat> t=… (spec …)`), so the
/// log shows every beat within one frame of SPEC-motion-audio §3.6.
enum HUDIntroLog {
    struct Probe: View {
        let t: Double
        let motion: HUDMotion
        var onRest: (() -> Void)?
        var body: some View {
            let _ = HUDIntroLog.note(t, motion)
            let _ = onRest?()
            Color.clear.frame(width: 0, height: 0)
        }
    }

    nonisolated(unsafe) private static var logged: Set<String> = []
    nonisolated(unsafe) private static var lastT = -1.0

    static func note(_ t: Double, _ m: HUDMotion) {
        if t < lastT - 0.5 { logged.removeAll() }          // a new intro
        lastT = t
        let beats: [(String, Double)] = [("drop", m.startAfterCut), ("boosters", m.startAfterCut + m.boosterDelay),
                                         ("timer", m.bigTimerAt), ("heart1", m.heartsAt[0]), ("heart2", m.heartsAt[1]),
                                         ("heart3", m.heartsAt[2]), ("rest", m.introEnd)]
        for (name, at) in beats where t >= at && !logged.contains(name) {
            logged.insert(name)
            Log.mark("hud", "intro \(name) t=\(String(format: "%.4f", t)) (spec \(String(format: "%.3f", at)))")
        }
    }
}
