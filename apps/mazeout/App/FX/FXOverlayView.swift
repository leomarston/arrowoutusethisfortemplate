import SwiftUI
import UIKit

// SHELL S1 (SPEC-architecture §6.5 z 3, §6.7, D13). The FX host: one transparent UIView over the screens whose effects are
// Core Animation layers on the render server (never per-frame SwiftUI Canvas), so the main thread stays idle during a
// celebration. It implements the ◆ `FXPlaying` contract: `play` returns a handle, `finished` awaits the effect's end,
// `skip` jumps to it, `stop`/`stopAll` remove layers. The MotionClock's time scale mirrors onto the host layer (slow motion,
// capture freezes). Kit decoupling step: the host names no effect — each effect's component registers it (`FXEffects`):
// a layer builder the host runs in one transaction (the sparkles), or a handler that runs its own effects (the win
// celebration, the Time Freeze, confetti, fireworks). An effect nobody registered finishes at once with a log line
// (`.coinFly` is drawn by CoinFly's own layers, not through the host).
// Coordinates: screen pt of the root view (the AnchorRegistry's global frames).

@MainActor final class FXOverlay: FXPlaying {
    let hostView = FXHostView()
    let ui: UITuning
    private var next = 0
    private struct Running {
        var layers: [CALayer]
        var waiters: [CheckedContinuation<Void, Never>] = []
    }
    private var running: [Int: Running] = [:]

    init(_ ctx: AppContext) {
        ui = ctx.tuning.ui
        ctx.clock.observeTimeScale { [weak self] k in self?.setTimeScale(k) }
        if ctx.args.raw["pc.frameWatch"] != nil {
            #if DEBUG || PC_MEASURE
            // FEEL: the shell-wide frame monitor (App/FX/FrameWatch.swift), measurement runs only
            FrameWatch.start {
                guard let app = S2Hooks.app else { return "boot" }
                let top = app.popups.topID.map { "+\($0.rawValue)" } ?? ""
                return app.router.screen.logName + top
            }
            #else
            // F3-A (ruling 52(a)): no frame watch in the store build — say so instead of logging "no hitches"
            Log.error("frame", "-pc.frameWatch: no frame watch in this build (Release); measurement runs use the Measure configuration")
            #endif
        }
    }

    init(ui: UITuning) { self.ui = ui }

    var isPlaying: Bool { !running.isEmpty || FXEffects.isPlaying }

    @discardableResult
    func play(_ effect: FXEffect) -> FXHandle {
        next += 1
        let handle = FXHandle(id: next)
        if let build = FXEffects.layers(for: effect, fx: self, seed: UInt64(next)) {
            start(handle, build: build)                                             // a layer builder (the sparkles)
        } else if !FXEffects.play(effect, handle: handle, fx: self) {              // a handler (celebration, freeze, …)
            Log.mark("fx", "\(Self.name(effect)): not built yet (S2 / S3), finishing at once")
        }
        return handle
    }

    func finished(_ handle: FXHandle) async {
        if let h = FXEffects.owner(of: handle) { await h.finished(handle); return }
        guard running[handle.id] != nil else { return }
        await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
            if running[handle.id] != nil { running[handle.id]?.waiters.append(cont) } else { cont.resume() }
        }
    }

    func skip(_ handle: FXHandle) { if let h = FXEffects.owner(of: handle) { h.skip(handle) } else { end(handle.id) } }
    func stop(_ handle: FXHandle) { if let h = FXEffects.owner(of: handle) { h.stop(handle) } else { end(handle.id) } }
    func stopAll() { FXEffects.stopAll(); for id in Array(running.keys) { end(id) } }

    /// Builds the effect's layers INSIDE one transaction whose completion (every animation done, in layer time) ends it.
    private func start(_ handle: FXHandle, build: () -> [CALayer]) {
        CATransaction.begin()
        CATransaction.setCompletionBlock { [weak self] in
            MainActor.assumeIsolated { self?.end(handle.id) }
        }
        let layers = build()
        running[handle.id] = Running(layers: layers)
        for l in layers { hostView.layer.addSublayer(l) }
        CATransaction.commit()
    }

    private func end(_ id: Int) {
        guard let r = running.removeValue(forKey: id) else { return }
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for l in r.layers { l.removeAllAnimations(); l.removeFromSuperlayer() }
        CATransaction.commit()
        for w in r.waiters { w.resume() }
    }

    private func setTimeScale(_ k: Double) {
        let layer = hostView.layer
        let local = layer.convertTime(CACurrentMediaTime(), from: nil)
        layer.beginTime = CACurrentMediaTime()
        layer.timeOffset = local
        layer.speed = Float(k)
    }

    static func name(_ e: FXEffect) -> String {
        switch e {
        case .celebration: return "celebration"
        case .confetti: return "confetti"
        case .fireworks: return "fireworks"
        case .coinFly: return "coinFly"
        case .sparkles: return "sparkles"
        case .custom(let id, _): return "custom(\(id))"
        }
    }
}

/// The transparent host; never takes touches (the celebration's tap-to-skip is the level screen's, S2).
final class FXHostView: UIView {
    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        isAccessibilityElement = false
    }
    required init?(coder: NSCoder) { fatalError("FXHostView is built in code") }
}

struct FXOverlayView: UIViewRepresentable {
    let fx: FXOverlay
    func makeUIView(context: Context) -> FXHostView { fx.hostView }
    func updateUIView(_ uiView: FXHostView, context: Context) {}
}

extension ShellEntry {
    static func makeFX(_ ctx: AppContext) -> any FXPlaying { FXOverlay(ctx) }
}

// MARK: - the effects other components register

/// A component's Core Animation effects on the FX host (the win celebration, the Time Freeze, confetti, fireworks): it builds
/// the effects it knows and keeps their handles; the host routes `finished` / `skip` / `stop` to the handler that owns one.
@MainActor protocol FXEffectHandler: AnyObject {
    /// Builds `effect` for `handle`; false = not this handler's effect (the host asks the next one).
    func play(_ effect: FXEffect, handle: FXHandle, fx: FXOverlay) -> Bool
    func owns(_ h: FXHandle) -> Bool
    func finished(_ h: FXHandle) async
    func skip(_ h: FXHandle)
    func stop(_ h: FXHandle)
    func stopAll()
    var isPlaying: Bool { get }
    /// A running effect a tap can skip (CelebrationSkip over the board), and whether the tap skips now.
    var skippable: Bool { get }
    var armed: Bool { get }
    /// The skip tap: nil = nothing of this handler's to skip.
    func skipTap() -> Bool?
    /// The win panel's first frame takes over the effect's dim.
    func handOverDim()
    /// FIX-2 A-R (UI tests only): the newest skippable effect's dim as drawn; nil = none running here.
    func dimProbe() -> String?
}

extension FXEffectHandler {
    var skippable: Bool { false }
    var armed: Bool { false }
    func skipTap() -> Bool? { nil }
    func handOverDim() {}
    func dimProbe() -> String? { nil }
}

@MainActor enum FXEffects {
    /// A component's layer effect: the layers for `effect` (built inside the host's transaction, which ends the effect when
    /// every animation is done), or nil when `effect` is not this builder's.
    typealias LayerBuilder = @MainActor (_ effect: FXEffect, _ fx: FXOverlay, _ seed: UInt64) -> (() -> [CALayer])?

    private static var handlers: [any FXEffectHandler] = []
    private static var builders: [LayerBuilder] = []

    static func register(_ handler: any FXEffectHandler) { handlers.append(handler) }
    static func registerLayers(_ builder: @escaping LayerBuilder) { builders.append(builder) }

    private static var all: [any FXEffectHandler] {
        ComponentRegistry.installOnce()
        return handlers
    }

    static func layers(for effect: FXEffect, fx: FXOverlay, seed: UInt64) -> (() -> [CALayer])? {
        ComponentRegistry.installOnce()
        for b in builders {
            if let build = b(effect, fx, seed) { return build }
        }
        return nil
    }

    static func play(_ effect: FXEffect, handle: FXHandle, fx: FXOverlay) -> Bool {
        for h in all where h.play(effect, handle: handle, fx: fx) { return true }
        return false
    }

    static func owner(of handle: FXHandle) -> (any FXEffectHandler)? { all.first { $0.owns(handle) } }
    static var isPlaying: Bool { all.contains { $0.isPlaying } }
    static func stopAll() { for h in all { h.stopAll() } }
    static var skippable: Bool { all.contains { $0.skippable } }
    static var armed: Bool { all.contains { $0.armed } }

    /// The skip tap (CelebrationSkip): the newest running skippable effect.
    @discardableResult
    static func skipTap() -> Bool {
        for h in all {
            if let r = h.skipTap() { return r }
        }
        return false
    }

    /// The win panel's first frame: every running effect's dim hands over to the popup's.
    static func handOverDim() { for h in all { h.handOverDim() } }

    /// FIX-2 A-R (UI tests only, `shell.warmProbe`): the running celebration's dim as drawn ("none" without one).
    static func dimProbe() -> String {
        for h in all {
            if let p = h.dimProbe() { return p }
        }
        return "none"
    }
}

/// Observed by the skip catcher (HUDView): true while a celebration can be skipped.
@MainActor @Observable final class CelebrationState {
    static let shared = CelebrationState()
    /// A celebration runs (the catcher swallows taps from W).
    private(set) var active = false
    /// … and a tap now skips (from W + 1.70 = the logo has landed, `win.skipFrom`; ruling 40).
    private(set) var armed = false
    func update() {
        let v = FXEffects.skippable
        if v != active { active = v }
        let a = FXEffects.armed
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
                .onTapGesture { FXEffects.skipTap() }
                .accessibilityIdentifier("celebration.skip")
                .accessibilityValue(Text(verbatim: CelebrationState.shared.armed ? "armed" : "waiting"))
        }
    }
}

extension FXOverlay {
    /// The win panel's first frame: the celebration's dim hands over to the popup's.
    func handOverCelebrationDim() { FXEffects.handOverDim() }
}

/// Short-lived layers on the FX host that remove themselves at a game time (confetti, fireworks): a component registers one
/// with its builder (the layers for its own effect, added to the host inside one transaction; nil = not its effect).
@MainActor final class LooseLayerFX: FXEffectHandler {
    typealias Build = @MainActor (_ effect: FXEffect, _ handle: FXHandle, _ fx: FXOverlay) -> CALayer?
    private let build: Build
    private let lifetime: Double
    private var loose: [Int: (CALayer, Double)] = [:]          // handle → (root, removal in game time)

    /// `lifetime` = game seconds the layers stay (the confetti / fireworks bursts: 5).
    init(lifetime: Double, _ build: @escaping Build) {
        self.lifetime = lifetime
        self.build = build
    }

    func play(_ effect: FXEffect, handle: FXHandle, fx: FXOverlay) -> Bool {
        guard let clock = S2Hooks.app?.clock, let root = build(effect, handle, fx) else { return false }
        loose[handle.id] = (root, clock.gameTime() + lifetime)
        Task { @MainActor in
            while let e = self.loose[handle.id], clock.gameTime() < e.1 { try? await Task.sleep(nanoseconds: 200_000_000) }
            self.stop(handle)
        }
        return true
    }

    func owns(_ h: FXHandle) -> Bool { loose[h.id] != nil }

    func finished(_ h: FXHandle) async {
        guard S2Hooks.app?.clock != nil else { return }
        while loose[h.id] != nil { try? await Task.sleep(nanoseconds: 16_000_000) }
    }

    func skip(_ h: FXHandle) { stop(h) }

    func stop(_ h: FXHandle) {
        if let l = loose.removeValue(forKey: h.id) {
            CATransaction.begin(); CATransaction.setDisableActions(true); l.0.removeFromSuperlayer(); CATransaction.commit()
        }
        CelebrationState.shared.update()
    }

    func stopAll() { for id in Array(loose.keys) { stop(FXHandle(id: id)) } }

    var isPlaying: Bool { !loose.isEmpty }
}
