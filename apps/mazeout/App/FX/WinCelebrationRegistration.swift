import SwiftUI
import UIKit
import PathCore

// Kit component `win-celebration` (kit/fx/win-celebration): `.celebration(tag)` on the FX host (`CelebrationFX`, was S2FX in
// HUD/S2Hooks.swift) and its boot warm-up (the logo split, off the main thread, behind Loading: was S2Hooks.warmUp).
// GameComponents.swift lists it. The skip catcher (`CelebrationSkip`) and its state stay core's (FXOverlayView.swift): they
// ask `FXEffects` whether a skippable effect runs.

@MainActor enum WinCelebrationRegistration {
    static func register() {
        FXEffects.register(CelebrationFX.shared)
        ShellWarmUps.register(order: 10) { _ in LogoParts.prepare() }
    }
}

/// The Core Animation win celebration as an FX host effect: one `CelebrationRun` per handle, skippable, its dim handed over to
/// the win panel's. Moved as it was from S2FX.
@MainActor final class CelebrationFX: FXEffectHandler {
    static let shared = CelebrationFX()
    private var runs: [Int: CelebrationRun] = [:]

    func play(_ effect: FXEffect, handle: FXHandle, fx: FXOverlay) -> Bool {
        guard let clock = S2Hooks.app?.clock, case .celebration(let tag) = effect else { return false }
        let run = CelebrationRun(handle: handle, tag: tag, host: fx.hostView.layer, clock: clock, ui: fx.ui, app: S2Hooks.app,
                                 seed: UInt64(0xC0FFEE) &+ UInt64(handle.id))
        run.onEnd = { [weak self] in self?.runs[handle.id] = nil; CelebrationState.shared.update() }
        runs[handle.id] = run
        CelebrationState.shared.update()
        return true
    }

    func owns(_ h: FXHandle) -> Bool { runs[h.id] != nil }

    func finished(_ h: FXHandle) async {
        if let run = runs[h.id] { await run.finished() }
    }

    func skip(_ h: FXHandle) {
        if let run = runs[h.id] { run.skip(fromTap: false) } else { stop(h) }
    }

    func stop(_ h: FXHandle) {
        if let run = runs[h.id] { run.end() }
        CelebrationState.shared.update()
    }

    func stopAll() { for id in Array(runs.keys) { stop(FXHandle(id: id)) } }

    var isPlaying: Bool { !runs.isEmpty }
    var skippable: Bool { runs.values.contains { $0.isSkippable } }
    var armed: Bool { runs.values.contains { $0.isArmed } }

    /// The skip tap (CelebrationSkip): the newest running celebration.
    func skipTap() -> Bool? {
        guard let run = runs.values.max(by: { $0.handle.id < $1.handle.id }) else { return nil }
        let ok = run.skip(fromTap: true)
        CelebrationState.shared.update()
        return ok
    }

    /// The celebration the panel takes over (its first frame).
    func handOverDim() { for r in runs.values { r.handOverDim() } }

    /// FIX-2 A-R (UI tests only, `shell.warmProbe`): the newest running celebration's dim as drawn; nil without one.
    func dimProbe() -> String? {
        guard let run = runs.values.max(by: { $0.handle.id < $1.handle.id }) else { return nil }
        return String(format: "%.2f", run.dimOpacity)
    }
}
