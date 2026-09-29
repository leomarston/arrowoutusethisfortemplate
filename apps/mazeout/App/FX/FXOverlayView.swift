import SwiftUI
import UIKit

// SHELL S1 (SPEC-architecture §6.5 z 3, §6.7, D13). The FX host: one transparent UIView over the screens whose effects are
// Core Animation layers on the render server (never per-frame SwiftUI Canvas), so the main thread stays idle during a
// celebration. It implements the ◆ `FXPlaying` contract: `play` returns a handle, `finished` awaits the effect's end,
// `skip` jumps to it, `stop`/`stopAll` remove layers. The MotionClock's time scale mirrors onto the host layer (slow motion,
// capture freezes). S1 builds `.sparkles`; `.celebration`, `.confetti`, `.fireworks` are S2's (WinLogoSequence, Confetti,
// Fireworks) and `.coinFly` is S3's (CoinFly): until they land those finish at once with a log line.
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

    var isPlaying: Bool { !running.isEmpty || S2FX.isPlaying }

    @discardableResult
    func play(_ effect: FXEffect) -> FXHandle {
        next += 1
        let handle = FXHandle(id: next)
        switch effect {
        case .sparkles(let at):
            let tokens = ui.tokens, seed = UInt64(next)
            start(handle) { Sparkles.make(at: at, tokens: tokens, seed: seed) }
        default:
            if S2FX.play(effect, handle: handle, fx: self) { break }                 // S2 hook (HUD/S2Hooks.swift)
            Log.mark("fx", "\(Self.name(effect)): not built yet (S2 / S3), finishing at once")
        }
        return handle
    }

    func finished(_ handle: FXHandle) async {
        if S2FX.owns(handle) { await S2FX.finished(handle); return }               // S2 hook
        guard running[handle.id] != nil else { return }
        await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
            if running[handle.id] != nil { running[handle.id]?.waiters.append(cont) } else { cont.resume() }
        }
    }

    func skip(_ handle: FXHandle) { if S2FX.owns(handle) { S2FX.skip(handle) } else { end(handle.id) } }       // S2 hook
    func stop(_ handle: FXHandle) { if S2FX.owns(handle) { S2FX.stop(handle) } else { end(handle.id) } }       // S2 hook
    func stopAll() { S2FX.stopAll(); for id in Array(running.keys) { end(id) } }

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
