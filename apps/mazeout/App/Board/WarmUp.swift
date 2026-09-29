import UIKit
import PathCore

// B1 + B2 (SPEC-architecture §5.9, R3; SPEC-motion-audio §10 "every first use pre-run by the warm-up"). `prepare()`: the
// warm-up behind the Loading screen, so the player's first exit, bump, ripple, intro, obstacle effect and painter compile
// nothing (shape paths, gradients and masks, emitters, the image contents, the animation machinery):
//  1. decode the board sprites into SpriteCache (tapes, door slices, lock, key, pipe mouth + counter, shard atlases, the
//     trail star), derive the door 9-slices and the key-only image, hand the atlases to the shard pool, build DigitGlyphs
//     "0"…"99";
//  2. put the REAL view tree in the window UNDER the opaque Loading view (inserted behind the root view when no
//     BoardHost holds it yet), load the built-in warm-up board (every obstacle kind), let it render 2 frames;
//  3. at stage.speed = `warmup.speed` (20), driven by the REAL rules (C2's LevelSession, the bundle's rules.json): the
//     intro; a bump with its badge and vignette; the taped bundle (the box breaks on that first exit: box shards + ring
//     chunks); the key arrow (key flight, door burst, door shards, lock flash; the door's ack reveals its arrow); the pipe
//     pass and shatter (pipe shards, counter halves, rims); the elevator (doors, tint, layer-2 reveal); one exit per
//     painter (solid, violet, rainbow) with its trail stars; a ripple; the clear wave; wait until everything is gone;
//  4. clear, restore the speed and the delegate, take the container out again; log `[PC][warmup] board <s> s`.
// Idempotent; the boot sequence awaits it (AppModel.boot).

extension BoardEngine {
    func runWarmUp() async {
        let t0 = ProcessInfo.processInfo.systemUptime
        warmingUp = true
        defer { warmingUp = false }
        DigitGlyphs.shared.warm()
        sprites.preload(["tapeV2", "tapeV3", "tapeV4", "tapeH2", "tapeH3", "tapeH4"] + BoardArt.names)
        await sprites.drain()
        boardArt.build()
        for n in ["doorShards", "pipeShards", "pipeCounter", "pipeMouth"] { shards.setImage(n, sprites.image(n)) }
        _ = StarTrail.image(sprites)
        let tDecode = ProcessInfo.processInfo.systemUptime

        guard stage == nil, !warmHurry else {
            Log.mark("warmup", warmHurry ? String(format: "board part skipped at the boot cap (sprites+glyphs %.3f s)", tDecode - t0)
                                         : "board skipped (a stage is already loaded)")
            warmedUp = true
            return
        }
        var attached = false
        if container.window == nil, let w = Self.keyWindow() {
            w.insertSubview(container, at: 0)             // behind the root view: the opaque Loading covers it
            container.frame = w.bounds
            container.layoutIfNeeded()
            attached = true
        }
        guard container.window != nil, let level = LabBoards.level("warmfx", bundle: bundle) else {
            Log.mark("warmup", String(format: "board %.3f s (no window: sprites + glyphs only)",
                                      ProcessInfo.processInfo.systemUptime - t0))
            warmedUp = true
            return
        }
        let savedDelegate = delegate
        let savedInput = inputEnabled
        let savedAllowed = allowedArrows
        delegate = nil
        allowedArrows = nil
        let session = LevelSession(plan: SessionPlan(id: "warm", levels: [level.level]), stages: [level],
                                   setup: AttemptSetup(levels: [level.level]), rules: Self.bundleRules(bundle))
        _ = session.start()
        let tr = args.raw["pc.warmTrace"] != nil
        if tr { Log.mark("warmup", "trace: load (link paused \(String(describing: linkPaused)))") }
        doLoad(StageSetup(level: level, screen: container.bounds.size, config: config))
        while !pendingAttach.isEmpty { attachStep() }
        CATransaction.begin(); CATransaction.setDisableActions(true)
        Self.setLayerTiming(roots.stage, speed: Float(config.warmupSpeed), freezeAt: nil)
        container.screenFX.applyTiming(speed: Float(config.warmupSpeed), freezeAt: nil)
        CATransaction.commit()
        runIntro(.growFromTails)
        _ = session.ack(.introFinished)
        if tr { Log.mark("warmup", "trace: intro (link paused \(String(describing: linkPaused)))") }
        await frames(2)
        if tr { Log.mark("warmup", "trace: 2 frames") }

        func tap(_ id: Int, painter: String) {
            forcedPainter = painter
            doPresent(session.tap(ArrowID(id), at: 0))
        }
        // a bump (the badge, the vignette, the red return), then its contact ack (the heart, the mark)
        let bump = session.tap(ArrowID(3), at: 0)
        doPresent(bump)
        doPresent(session.ack(.bumpContact(ArrowID(3))))
        // the taped bundle: solid + stars; the box breaks on this first exit (shards, ring chunks, reveal)
        tap(0, painter: "solid")
        // the key: flight, burst, shards, flash; the door's ack reveals its arrow
        tap(5, painter: "violet")
        doPresent(session.ack(.doorBurst(ObstacleID("d0"))))
        // the pipe: pass, counter, shatter (tube shards, counter halves, rims)
        tap(7, painter: "rainbow")
        // the elevator: the last platform arrow leaves → doors part, tint, layer-2 reveal
        tap(8, painter: "solid")
        await frames(2)
        tap(4, painter: "violet")
        tap(11, painter: "rainbow")
        forcedPainter = nil
        CATransaction.begin(); CATransaction.setDisableActions(true)
        container.screenFX.ripple(at: CGPoint(x: container.bounds.midX, y: container.bounds.midY))
        CATransaction.commit()
        runClearWave(report: false)
        if tr { Log.mark("warmup", "trace: effects started (movers \(movers.count), bursts \(activeBursts))") }
        for _ in 0..<120 where !movers.isEmpty || activeBursts > 0 { await frames(1) }
        if tr { Log.mark("warmup", "trace: effects done (movers \(movers.count), bursts \(activeBursts))") }
        await frames(3)

        doClear()
        while !teardown.isEmpty { teardownStep(10_000) }
        CATransaction.begin(); CATransaction.setDisableActions(true)
        Self.setLayerTiming(roots.stage, speed: Float(max(clock.timeScale, 0.0001)), freezeAt: nil)
        container.screenFX.applyTiming(speed: Float(max(clock.timeScale, 0.0001)), freezeAt: nil)
        CATransaction.commit()
        if clock.timeScale == 0 { frozen = false; applyClockScale(0) }
        delegate = savedDelegate
        inputEnabled = savedInput
        allowedArrows = savedAllowed
        if attached, container.superview is UIWindow { container.removeFromSuperview() }
        warmedUp = true
        let t1 = ProcessInfo.processInfo.systemUptime
        Log.mark("warmup", String(format: "board %.3f s (sprites+glyphs %.3f s, effects %.3f s%@, painters %@, obstacles door key pipe box elevator, clear wave)",
                                  t1 - t0, tDecode - t0, t1 - tDecode, warmHurry ? " cut short at the boot cap" : "",
                                  painters.keys.sorted().joined(separator: ",")))
    }

    /// The bundle's Tuning/rules.json as C2's RulesTuning (defaults when missing; problems logged).
    static func bundleRules(_ bundle: Bundle) -> RulesTuning {
        let url = bundle.url(forResource: "rules", withExtension: "json", subdirectory: "Tuning")
        let data = url.flatMap { try? Data(contentsOf: $0) }
        let r = RulesTuning.load(json: data)
        for p in r.problems { Log.error("board", "rules.json: \(p)") }
        return r.rules
    }

    static func keyWindow() -> UIWindow? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let windows = scenes.flatMap(\.windows)
        return windows.first(where: \.isKeyWindow) ?? windows.first
    }
}
