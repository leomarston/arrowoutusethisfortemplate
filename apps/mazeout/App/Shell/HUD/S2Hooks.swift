import SwiftUI
import UIKit
import PathCore

// SHELL S2: where the S2 panels, effects and lab pages plug into S1's shell (one-line hooks in PopupHost.swift `PopupContent`,
// Router.swift `DebugPopupLauncher`, FXOverlayView.swift `FXOverlay`, RootView.swift `PopupPrewarm`, ShellLab.swift
// `ShellDebugScreens`). Nothing here changes a ◆ contract.
//   S2Popups   the panels of outOfTime, continue (streak / token / life / hearts-out), levelFailed, win, unlock, claim, and the
//              `-pc.popup` debug launcher for them (fixed, honest parameters: the player's state + the rules' prices)
//   S2FX       `.celebration`, `.confetti`, `.fireworks` on the FX host (CA layers) + the tap-to-skip state
//   S2Hooks    the app reference the CA effects need (haptics, audio), the Shop route of the offers' coin groups, the warm-up

@MainActor enum S2Hooks {
    /// The running app (set by the shell's first render); the CA effects use it for the win haptic and the skip click.
    static weak var app: AppModel?

    /// The offers' coin group → the Shop as a closable page over the offer (SPEC-ui §2.6.6). The Shop is S3's; until it lands
    /// the tap is logged and nothing opens (never a dead-end: the offer stays up and answers normally).
    static var shopOpener: ((AppModel) -> Void)?
    static func openShop(_ app: AppModel) {
        if let shopOpener { shopOpener(app) } else { Log.mark("popup", "coin group → Shop: S3's Shop page is not installed yet") }
    }

    /// Behind Loading: the logo split for the celebration (off the main thread) and the app reference.
    static func warmUp(_ app: AppModel) {
        self.app = app
        LogoParts.prepare()
    }
}

// MARK: - popups

@MainActor enum S2Popups {
    static func hasPanel(_ request: PopupRequest) -> Bool {
        switch request {
        case .outOfTime, .continueOffer, .levelFailed, .winPanel, .unlockOverlay, .claimReward: return true
        default: return false
        }
    }

    /// The container's accessibility value (SPEC-ui §6: `popup.continue` = streak | token | life | hearts | time; win = the tier).
    static func containerValue(_ request: PopupRequest, app: AppModel) -> String {
        switch request {
        case .continueOffer(let offer, _): return ContinuePopup.variant(offer, app: app).rawValue
        case .outOfTime(let offer, _): return offer.kind == .outOfHearts ? "hearts" : "time"
        case .winPanel(let s): return s.tag.rawValue
        case .unlockOverlay(let f): return f.rawValue
        case .levelFailed(_, let reason): return reason.rawValue
        default: return ""
        }
    }

    @ViewBuilder static func make(_ request: PopupRequest, answer: PopupAnswer) -> some View {
        ZStack(alignment: .topLeading) {
            panel(request, answer: answer)
            VariantMarker(request: request)
        }
    }

    /// `popup.variant` (value = `containerValue`): the layout a popup chose, for UI tests (a `.contain` container exposes no value).
    private struct VariantMarker: View {
        let request: PopupRequest
        @Environment(AppModel.self) private var app
        var body: some View {
            Color.clear.frame(width: 1, height: 1)
                .accessibilityElement()
                .accessibilityIdentifier("popup.variant")
                .accessibilityValue(Text(verbatim: S2Popups.containerValue(request, app: app)))
                .allowsHitTesting(false)
        }
    }

    @ViewBuilder private static func panel(_ request: PopupRequest, answer: PopupAnswer) -> some View {
        switch request {
        case .outOfTime(let offer, let pay): OutOfTimePopup(offer: offer, pay: pay, answer: answer)
        case .continueOffer(let offer, let pay): ContinuePopup(offer: offer, pay: pay, answer: answer)
        case .levelFailed(let levels, let reason): LevelFailedPopup(levels: levels, reason: reason, answer: answer)
        case .winPanel(let summary): WinPanel(summary: summary, answer: answer)
        case .unlockOverlay(let feature): UnlockOverlay(feature: feature, answer: answer)
        case .claimReward(let grant): ClaimRewardPopup(grant: grant, answer: answer)
        default: EmptyView()
        }
    }

    /// `-pc.popup <id>[:variant]` for the S2 ids (SPEC-architecture §9.1). Returns false for an id S2 does not own.
    static func debugPresent(_ p: LaunchArgs.PopupArg, app: AppModel) async -> Bool {
        let popups = app.popups
        let s = app.store.state
        let price = Int(app.tuning.rules.double("failChain.outOfTime.0.price", 900))
        let pay: PayAction = { @MainActor in
            // the debug launcher never spends: it reports what the real PayAction would get
            Log.mark("popup", "debug pay: coins \(app.store.state.coins) ≥ \(price) → \(app.store.state.coins >= price)")
            return false
        }
        switch p.id {
        case PopupID.outOfTime.rawValue:
            let offer = ContinueOffer(kind: .outOfTime, step: 0, price: price, grant: .addTime(30))
            let r = await popups.present(Popup<PopupResult>.outOfTime(offer, pay: pay))
            Log.mark("popup", "outOfTime → \(r)")
        case PopupID.continueOffer.rawValue:
            let v = ContinuePopup.Variant(rawValue: p.variant ?? "streak") ?? .streak
            ContinuePopup.forced = v
            let offer: ContinueOffer
            switch v {
            case .hearts, .time:
                offer = ContinueOffer(kind: v == .hearts ? .outOfHearts : .outOfTime, step: 0, price: price,
                                      grant: v == .hearts ? .refillHearts(3) : .addTime(30))
            case .life: offer = ContinueOffer(kind: .outOfTime, step: 2, price: price, grant: .addTime(30), warning: .life, isLast: true)
            case .token: offer = ContinueOffer(kind: .outOfTime, step: 1, price: price, grant: .addTime(30), warning: .token)
            case .streak: offer = ContinueOffer(kind: .outOfTime, step: 1, price: price, grant: .addTime(30), warning: .streak)
            }
            let r = await popups.present(Popup<PopupResult>.continueOffer(offer, pay: pay))
            ContinuePopup.forced = nil
            Log.mark("popup", "continue:\(v.rawValue) → \(r)")
        case PopupID.levelFailed.rawValue:
            let r = await popups.present(Popup<PopupResult>.levelFailed(levels: levels(app), reason: .timeUp))
            Log.mark("popup", "levelFailed → \(r)")
        case PopupID.winPanel.rawValue:
            let tag = LevelTag(label: p.variant) ?? .normal
            let reward = Int(app.tuning.rules.double("rewards.\(tag.rawValue)", tag == .normal ? 20 : (tag == .hard ? 60 : 100)))
            let lv = levels(app)
            let summary = WinSummary(levels: lv, reward: lv.count > 1 ? 80 : reward, tag: tag)
            let r = await popups.present(Popup<PopupResult>.winPanel(summary))
            Log.mark("popup", "win → \(r)")
        case PopupID.unlockOverlay.rawValue:
            let f = FeatureID(p.variant ?? "pipe")
            let r = await popups.present(Popup<PopupResult>.unlockOverlay(f))
            Log.mark("popup", "unlock → \(r)")
        case PopupID.claimReward.rawValue:
            let g: Grant
            switch p.variant ?? "lives" {
            case "coins": g = .coins(200)
            case "hint": g = .booster(.hint, 1)
            case "freeze": g = .booster(.freeze, 1)
            default: g = .unlimited(1800)
            }
            let r = await popups.present(Popup<PopupResult>.claimReward(g))
            Log.mark("popup", "claim → \(r)")
        default:
            _ = s
            return false
        }
        return true
    }

    /// The level the debug panels name: the player's next level (`-pc.level`), or the FTUE session.
    private static func levels(_ app: AppModel) -> [Int] {
        let launch = app.levelLaunch(for: app.store.state.level)
        return launch.levels
    }

    /// Rendered once, invisibly, behind Loading (the first presentation's SwiftUI + raster cost is paid there), one item per
    /// frame (RootView `PopupPrewarm` stages every owner's list; FIX-A1). Every win tier, not only Normal (FEEL item 1: the
    /// Hard / Super Hard rasters — tierPanel, coinGlow, the red / purple offer wells, the tag ribbon, the skulls — and their
    /// first draw were paid on the first Hard win, 1.95 s at L19, G1). `-pc.feelPrewarm normalOnly` keeps B1's Normal-only
    /// list (the before/after measurement).
    static func prewarm(_ app: AppModel) -> [ShellPrewarmItem] {
        let host = PopupHost(ui: app.tuning.ui)
        let offer = ContinueOffer(kind: .outOfTime, step: 1, price: 900, grant: .addTime(30), warning: .streak)
        let pay: PayAction = { false }
        let tiers: [LevelTag] = app.args.raw["pc.feelPrewarm"] == "normalOnly" ? [.normal] : LevelTag.allCases
        var items: [ShellPrewarmItem] = [
            ShellPrewarmItem("outOfTime", ReferenceCanvas {
                OutOfTimePopup(offer: ContinueOffer(kind: .outOfTime, step: 0, price: 900, grant: .addTime(30)), pay: pay,
                               answer: PopupAnswer(id: -11, host: host))
            }),
            ShellPrewarmItem("outOfHearts", ReferenceCanvas {
                OutOfTimePopup(offer: ContinueOffer(kind: .outOfHearts, step: 0, price: 900, grant: .refillHearts(3)), pay: pay,
                               answer: PopupAnswer(id: -12, host: host))
            }),
            ShellPrewarmItem("continue", ReferenceCanvas { ContinuePopup(offer: offer, pay: pay, answer: PopupAnswer(id: -13, host: host)) }),
            ShellPrewarmItem("levelFailed", ReferenceCanvas {
                LevelFailedPopup(levels: [32], reason: .timeUp, answer: PopupAnswer(id: -14, host: host))
            }),
        ]
        for (i, tag) in tiers.enumerated() {
            items.append(ShellPrewarmItem("win.\(tag.rawValue)", ReferenceCanvas {
                WinPanel(summary: WinSummary(levels: [32], reward: tag == .normal ? 20 : (tag == .hard ? 60 : 100), tag: tag),
                         answer: PopupAnswer(id: -15 - i, host: host), prewarm: true)
            }))
        }
        items.append(ShellPrewarmItem("unlockParts", ReferenceCanvas { UnlockParts_Prewarm() }))
        // G2's request (the first claim popup took 31.7 ms present → visible in Debug): the claim screen's graph and rasters
        items.append(ShellPrewarmItem("claim.coins", ReferenceCanvas {
            ClaimRewardPopup(grant: .coins(200), answer: PopupAnswer(id: -18, host: host))
        }))
        items.append(ShellPrewarmItem("claim.unlimited", ReferenceCanvas {
            ClaimRewardPopup(grant: .unlimited(1800), answer: PopupAnswer(id: -19, host: host))
        }))
        // A2: the staged claim titles draw one GameText per letter: every letter's raster (the claim's style and the Sky Jump
        // win's) is made here, all letters at rest, not in the claim's first frames
        let claimTitle = ClaimTitle.style(app.tuning.ui.tokens, id: "claim.title.title",
                                          .s2(45.2, -0.83, [Skin.hudS2HooksS2PopupsPrewarmClaimTitleStyle0, Skin.hudS2HooksS2PopupsPrewarmClaimTitleStyle1, Skin.hudS2HooksS2PopupsPrewarmClaimTitleStyle2], outline: Skin.hudS2HooksS2PopupsPrewarmClaimTitleOutline, 0.94, drop: 1.81))
        let skyTitle = GameTextStyle.s2(45.5, -1.0, [Skin.hudS2HooksS2PopupsPrewarmSkyTitle0, Skin.hudS2HooksS2PopupsPrewarmSkyTitle1, Skin.hudS2HooksS2PopupsPrewarmSkyTitle2], outline: Skin.hudS2HooksS2PopupsPrewarmSkyTitleOutline, 0.9, drop: 1.8)
        // A2: the Pause toggle's OFF track (the track and the knob are separate rasters now; ON is made with the Pause popup)
        let tk = app.tuning.ui.tokens
        items.append(ShellPrewarmItem("toggle.off", ReferenceCanvas {
            PopupToggle(id: "prewarm.toggle", isOn: false, t: tk) {}.placed(tk.frame("pause.toggleSound", CGRect(206.5, 328.6, 116.1, 37.4)))
        }))
        items.append(ShellPrewarmItem("claim.letters", ReferenceCanvas {
            LetterPopTitle(text: String(localized: "Congratulations!"), style: claimTitle, baseline: 187.4, centreX: 196.8,
                           maxWidth: 360, u: 5)
            LetterPopTitle(text: String(localized: "Congratulations!"), style: skyTitle, baseline: 122.8, centreX: 196.8,
                           maxWidth: 360, u: 5)
        }))
        // the level HUD in every tier and booster state: its chrome rasters are made here, not on the first level's cut
        for (i, model) in prewarmHUDs.enumerated() { items.append(ShellPrewarmItem("hud.\(i)", HUDView(model: model))) }
        return items
    }

    /// Three HUD models (normal / Hard / Super Hard; stock, empty and a lost heart) for the warm-up render.
    private static let prewarmHUDs: [HUDModel] = LevelTag.allCases.map { tag in
        let m = HUDModel()
        HUDLab.fill(m, tag: tag, hearts: tag == .normal ? 3 : 2)
        if tag == .superHard { m.boosters = [BoosterSlotVM(id: .freeze, state: .empty), BoosterSlotVM(id: .hint, state: .stock(12))] }
        return m
    }
}

// MARK: - effects

@MainActor enum S2FX {
    private static var runs: [Int: CelebrationRun] = [:]
    private static var loose: [Int: (CALayer, Double)] = [:]     // handle → (root, removal in game time)
    private static var freezes: [Int: FreezeRun] = [:]           // handle → the running Time Freeze
    private static var looseDone: [Int: Double] = [:]            // handle → `finished` in game time (the freeze's end)

    /// A running Time Freeze (FIX-A2: pausable). `end` = the countdown's end in game time (∞ while the tray holds "10" for
    /// the first tap, ruling 30); `countdownAt` = its start in the parts' own time; `heldSince` = game time the session's
    /// hold began (the layers stand still, `finished` and the removal wait; the resume moves `end` by the held span).
    private struct FreezeRun {
        let parts: HUDFreezeFX.Parts
        let b: Double
        var end: Double
        var countdownAt: CFTimeInterval?
        var heldSince: Double?
    }

    /// Publishes a freeze's end (the removal after the fade), or waits while it is held or holding for the first tap.
    private static func setFreezeEnd(_ h: Int, _ run: FreezeRun) {
        guard let root = loose[h]?.0 else { return }
        let done = run.heldSince == nil ? run.end : .infinity
        looseDone[h] = done
        loose[h] = (root, done + run.parts.spec.endFade + 0.05)
    }

    static func owns(_ h: FXHandle) -> Bool { runs[h.id] != nil || loose[h.id] != nil }

    /// FIX-A2, UI tests (`hud.freeze.tray`, computed when queried): the newest freeze's tray as drawn —
    /// "held=<0|1> phase=<flight|holding|counting|ended> digit=<n> bar=<width fraction> left=<s>" in the parts' own time, or
    /// "off" when no freeze runs. `bar` is read from the presentation layer (what is on screen).
    static func freezeTrayProbe() -> String {
        guard let run = freezes.max(by: { $0.key < $1.key })?.value else { return "off" }
        let p = run.parts
        let local = HUDFreezeFX.localTime(p)
        let n = max(1, Int(p.seconds.rounded(.up)))
        var phase = "holding", digit = n, left = p.seconds
        if local < p.t0 + p.spec.frostFrom {
            phase = "flight"
        } else if let c = run.countdownAt {
            left = max(0, p.seconds - max(0, local - c))
            phase = left > 0 ? "counting" : "ended"
            digit = left > 0 ? min(n, Int((left - 1e-9).rounded(.up))) : 0
        }
        let full = max(0.001, p.fill.bounds.width)
        let shown = (p.fill.presentation() ?? p.fill).bounds.width
        return String(format: "held=%d phase=%@ digit=%d bar=%.3f left=%.2f", run.heldSince == nil ? 0 : 1, phase, digit,
                      Double(shown / full), left)
    }
    static var isPlaying: Bool { !runs.isEmpty || !loose.isEmpty }

    /// Builds an S2 effect; false = not an S2 effect.
    static func play(_ effect: FXEffect, handle: FXHandle, fx: FXOverlay) -> Bool {
        guard let clock = S2Hooks.app?.clock ?? fallbackClock else { return false }
        switch effect {
        case .celebration(let tag):
            let run = CelebrationRun(handle: handle, tag: tag, host: fx.hostView.layer, clock: clock, ui: fx.ui, app: S2Hooks.app,
                                     seed: UInt64(0xC0FFEE) &+ UInt64(handle.id))
            run.onEnd = { runs[handle.id] = nil; CelebrationState.shared.update() }
            runs[handle.id] = run
            CelebrationState.shared.update()
            return true
        case .custom(let id, let params) where id == "freeze":
            // the Time Freeze HUD bits (HUD/HUDFreeze.swift): `finished` at the freeze's end, the layers gone after the fade.
            // params["hold"] = 1 (SPEC.md ruling 30, the hourglass before the first tap): the flight, icing and tray as usual,
            // the tray holding "10" until `.custom("freezeGo", ["handle": id])` starts the countdown (the first board tap)
            let host = fx.hostView.layer
            let t0 = host.convertTime(CACurrentMediaTime(), from: nil)
            let seconds = params["seconds"] ?? fx.ui.file.double("freeze.seconds", 10)
            let hold = (params["hold"] ?? 0) > 0
            let safeTop = fx.hostView.window?.safeAreaInsets.top ?? fx.hostView.safeAreaInsets.top
            CATransaction.begin(); CATransaction.setDisableActions(true)
            let parts = HUDFreezeFX.build(host: host, t0: t0, seconds: seconds, ui: fx.ui, safeTop: safeTop > 0 ? safeTop : 59, hold: hold)
            host.addSublayer(parts.root)
            CATransaction.commit()
            let spec = parts.spec
            let now = clock.gameTime()
            let run = FreezeRun(parts: parts, b: now, end: hold ? .infinity : now + spec.frostFrom + seconds,
                                countdownAt: hold ? nil : parts.t0 + spec.frostFrom, heldSince: nil)
            freezes[handle.id] = run
            loose[handle.id] = (parts.root, 0)
            setFreezeEnd(handle.id, run)
            Log.mark("fx", "freeze \(seconds) s at B (tray at B+\(spec.frostFrom))" + (hold ? ", holding \"\(Int(seconds))\" until the first tap" : ""))
            Task { @MainActor in
                while let e = loose[handle.id], clock.gameTime() < e.1 { try? await Task.sleep(nanoseconds: 50_000_000) }
                stop(handle)
            }
            return true
        case .custom(let id, let params) where id == "freezeGo":
            // ruling 30: the first board tap starts a held freeze's countdown (never before its tray is out, B + 1.60)
            guard let h = params["handle"].map({ Int($0) }), var run = freezes[h], loose[h] != nil else { return true }
            let parts = run.parts
            let spec = parts.spec
            let local = HUDFreezeFX.localTime(parts)                  // the parts' own time (it stops while held)
            let start = max(local, parts.t0 + spec.frostFrom)
            HUDFreezeFX.startCountdown(parts, at: start)
            let now = clock.gameTime()
            run.countdownAt = start
            run.end = (run.heldSince ?? now) + (start - local) + parts.seconds
            freezes[h] = run
            setFreezeEnd(h, run)
            Log.mark("fx", String(format: "freeze countdown from B+%.2f of its own time (%.0f s)", start - parts.t0, parts.seconds))
            return true
        case .custom(let id, let params) where id == "freezeHold":
            // FIX-A2: the session's clock is held (Pause, a popup, an offer, a tutorial, the background) or runs again: the
            // flight, icing, tray and frost stand still with it and end with C2's freeze
            guard let h = params["handle"].map({ Int($0) }), var run = freezes[h], loose[h] != nil else { return true }
            let on = (params["on"] ?? 0) > 0
            let now = clock.gameTime()
            if on, run.heldSince == nil {
                run.heldSince = now
                HUDFreezeFX.hold(run.parts, true)
                FreezeHUDState.shared.hold(true)
            } else if !on, let since = run.heldSince {
                run.heldSince = nil
                if run.end.isFinite { run.end += now - since }
                HUDFreezeFX.hold(run.parts, false)
                FreezeHUDState.shared.hold(false)
                Log.mark("fx", String(format: "freeze resumed after %.2f s held", now - since))
            } else {
                return true
            }
            freezes[h] = run
            setFreezeEnd(h, run)
            if on { Log.mark("fx", String(format: "freeze held at B+%.2f of its own time", HUDFreezeFX.localTime(run.parts) - run.parts.t0)) }
            return true
        case .confetti(let rect), .fireworks(let rect):
            let root = CALayer()
            let host = fx.hostView.layer
            root.frame = host.bounds
            let t0 = host.convertTime(CACurrentMediaTime(), from: nil)
            var rng = PathRandom(seed: 0xF1 &+ UInt64(handle.id))
            let area = rect.isEmpty ? host.bounds : rect
            CATransaction.begin(); CATransaction.setDisableActions(true)
            if case .confetti = effect {
                let spec = ConfettiSpec(fx.ui.tokens)
                for _ in 0..<spec.burst { root.addSublayer(Confetti.burstPiece(&rng, spec: spec, bounds: area, begin: t0)) }
            } else {
                let spec = FireworkSpec(fx.ui.tokens)
                for i in 0..<2 {
                    let from = CGPoint(x: area.minX + area.width * (0.35 + 0.3 * CGFloat(i)), y: area.maxY)
                    let to = CGPoint(x: from.x + CGFloat((rng.unit() - 0.5) * 60), y: area.minY + area.height * 0.3)
                    for l in Fireworks.rocket(from: from, to: to, launch: t0 + 0.2 * Double(i), burst: t0 + 0.2 * Double(i) + 0.65, trail: 200) {
                        root.addSublayer(l)
                    }
                    for l in Fireworks.burst(at: to, begin: t0 + 0.2 * Double(i) + 0.65, spec: spec, rng: &rng) { root.addSublayer(l) }
                }
            }
            host.addSublayer(root)
            CATransaction.commit()
            loose[handle.id] = (root, clock.gameTime() + 5)
            Task { @MainActor in
                while let e = loose[handle.id], clock.gameTime() < e.1 { try? await Task.sleep(nanoseconds: 200_000_000) }
                stop(handle)
            }
            return true
        default:
            return false
        }
    }

    static func finished(_ h: FXHandle) async {
        if let run = runs[h.id] { await run.finished(); return }
        guard let clock = S2Hooks.app?.clock else { return }
        while loose[h.id] != nil {
            if let done = looseDone[h.id], clock.gameTime() >= done { return }
            try? await Task.sleep(nanoseconds: 16_000_000)
        }
    }

    static func skip(_ h: FXHandle) {
        if let run = runs[h.id] { run.skip(fromTap: false) } else { stop(h) }
    }

    static func stop(_ h: FXHandle) {
        if let run = runs[h.id] { run.end() }
        if looseDone.removeValue(forKey: h.id) != nil { FreezeHUDState.shared.cancel() }   // a freeze: the frost goes with it
        freezes[h.id] = nil
        if let l = loose.removeValue(forKey: h.id) {
            CATransaction.begin(); CATransaction.setDisableActions(true); l.0.removeFromSuperlayer(); CATransaction.commit()
        }
        CelebrationState.shared.update()
    }

    static func stopAll() {
        FreezeHUDState.shared.cancel()
        for id in Array(runs.keys) { stop(FXHandle(id: id)) }
        for id in Array(loose.keys) { stop(FXHandle(id: id)) }
    }

    /// The celebration the panel takes over (its first frame).
    static func handOverDim() { for r in runs.values { r.handOverDim() } }

    /// FIX-2 A-R (UI tests only, `shell.warmProbe`): the newest running celebration's dim as drawn ("none" without one).
    static func celebrationDimProbe() -> String {
        guard let run = runs.values.max(by: { $0.handle.id < $1.handle.id }) else { return "none" }
        return String(format: "%.2f", run.dimOpacity)
    }

    /// The skip tap (CelebrationSkip): the newest running celebration.
    @discardableResult
    static func skipTap() -> Bool {
        guard let run = runs.values.max(by: { $0.handle.id < $1.handle.id }) else { return false }
        let ok = run.skip(fromTap: true)
        CelebrationState.shared.update()
        return ok
    }

    static var skippable: Bool { runs.values.contains { $0.isSkippable } }
    static var armed: Bool { runs.values.contains { $0.isArmed } }

    private static var fallbackClock: MotionClock?
}

/// Observed by the skip catcher (HUDView): true while a celebration can be skipped.
@MainActor @Observable final class CelebrationState {
    static let shared = CelebrationState()
    /// A celebration runs (the catcher swallows taps from W).
    private(set) var active = false
    /// … and a tap now skips (from W + 1.70 = the logo has landed, `win.skipFrom`; ruling 40).
    private(set) var armed = false
    func update() {
        let v = S2FX.skippable
        if v != active { active = v }
        let a = S2FX.armed
        if a != armed { armed = a }
    }
}

/// A full-screen transparent catcher over the board while a celebration runs (the FX host takes no touches): every tap before
/// W + 1.70 is swallowed with no effect (no ripple, no click, no board or HUD input); a tap from W + 1.70 skips to the panel
/// (ruling 40 = v582, motion-catalog §11.4; was W + 0.41).
struct CelebrationSkip: View {
    var body: some View {
        if CelebrationState.shared.active {
            Color.clear
                .contentShape(Rectangle())
                .onTapGesture { S2FX.skipTap() }
                .accessibilityIdentifier("celebration.skip")
                .accessibilityValue(Text(verbatim: CelebrationState.shared.armed ? "armed" : "waiting"))
        }
    }
}

extension FXOverlay {
    /// The win panel's first frame: the celebration's dim hands over to the popup's.
    func handOverCelebrationDim() { S2FX.handOverDim() }
}
