import SwiftUI
import QuartzCore
import PathCore

// F3-A (SPEC.md ruling 52(a)): measurement-only code never ships to review. This file is compiled into Debug and the
// Measure configuration (project.yml: Release's settings + PC_MEASURE; `CONFIG=Measure tools/build.sh A`, build/owner-phone.sh),
// never into the Release (store) build. Router.afterFirstScreen logs an error when `-pc.glitchRun` reaches a store build.
#if DEBUG || PC_MEASURE
// A3 GLITCH (PLAN-P §4.3, owner item 5) — MEASUREMENT ONLY: `-pc.glitchRun <plan>` drives the shell flows the owner named,
// through the same entry points their buttons call, while `simctl io recordVideo` records the screen (build/p/A3/rec.sh) and
// tools/blipscan.py looks for one-frame anomalies. Nothing runs without the flag (like `-pc.tabLoop`, `-pc.popupLoop`).
//   pause:N          in a level: the HUD's Pause (LevelFlow.pause), then Resume on the popup — N times
//   quit:N           in a level: Pause → Quit → Quit Level? Quit → Level Failed X → home → Play — N times
//   play:N           on home: Play → the level's intro → the router's cut back home (as Level Failed's X does) — N times
//                    (measures the Play cut and the home arrival; with `-pc.frameWatch 1` every frame > 20 ms is logged)
//   tabs:N           on home (its queue settled): A2's DebugTabLoop — N tab slides (1- and 2-page), each under a FrameProbe
//   popups:N:a,b,…   each `-pc.popup` id (DebugPopupLauncher, variants as id:variant) presented and closed N times
//   pages:N          FIX-2 A: on a settled home, N round trips home → Profile → home and home → this week's live ladder page
//                    (Claw / Up & Away, its bar's own call) → its X → home (the page → home arrivals under the frame watch)
// Every action logs `[PC][glitch] <step> <action> at <uptime>` (the recording's anchor) and runs under a FrameProbe
// (`[PC][perf] glitch <step> <action> frames n max ms over20 k`). Button feedback (click + haptic) is played like the
// buttons do; the press scale of a real finger is not.

@MainActor enum GlitchRun {
    static func start(_ plan: String, app: AppModel, router: Router) {
        let parts = plan.split(separator: ":", maxSplits: 2).map(String.init)
        let n = parts.count > 1 ? max(1, Int(parts[1]) ?? 1) : 1
        let gap = app.args.raw["pc.glitchGap"].flatMap(Double.init) ?? 1.0
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: UInt64((app.args.raw["pc.glitchDelay"].flatMap(Double.init) ?? 2.0) * 1e9))
            Log.mark("glitch", "run \(plan) (gap \(gap) s)")
            switch parts[0] {
            case "pause": await pauseLoop(n, gap: gap, app: app, router: router)
            case "quit": await quitLoop(n, gap: gap, app: app, router: router)
            case "play": await playLoop(n, gap: gap, app: app, router: router)
            case "tabs":
                // A2's DebugTabLoop (the nav's own router calls) on a settled home (the week-start event page closed first)
                await settleHome(app, step: 0)
                DebugTabLoop.run(n, app: app, router: router)
            case "popups": await popupLoop(n, ids: parts.count > 2 ? parts[2].split(separator: ",").map(String.init) : [],
                                           gap: gap, app: app)
            case "pages": await pagesLoop(n, gap: gap, app: app, router: router)
            default: Log.error("glitch", "unknown plan \(plan)")
            }
            Log.mark("glitch", "done \(plan)")
        }
    }

    // MARK: steps

    private static func mark(_ step: Int, _ what: String) -> FrameProbe {
        Log.mark("glitch", String(format: "%d %@ at %.4f", step, what, CACurrentMediaTime()))
        let p = FrameProbe("glitch \(step) \(what)")
        p.start()
        return p
    }

    private static func sleep(_ s: Double) async { try? await Task.sleep(nanoseconds: UInt64(max(0, s) * 1e9)) }

    private static func press(_ app: AppModel, haptic: Haptic? = nil) {
        if let cue = app.tuning.audio.cue("uiButton") { app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue))) }
        if let h = haptic ?? GameButtonFeedback.haptic(app) { app.haptics.play(h) }
    }

    /// Waits (≤ `limit` s) until `ok`, polling each frame.
    private static func wait(_ limit: Double, _ ok: () -> Bool) async -> Bool {
        let end = ProcessInfo.processInfo.systemUptime + limit
        while !ok() {
            if ProcessInfo.processInfo.systemUptime > end { return false }
            await FrameWaiter.frames(1)
        }
        return true
    }

    private static func host(_ app: AppModel) -> PopupHost? { app.popups as? PopupHost }

    /// Home, or the week-start event page home's queue put over it (settleHome closes it).
    private static func atHome(_ app: AppModel) -> Bool {
        if case .event = app.router.screen { return true }
        return app.router.screen.isHome
    }

    /// The level is up, its intro done, nothing presented.
    private static func levelReady(_ app: AppModel) -> Bool {
        guard app.router.screen.isLevel, let g = app.game, !g.isTornDown, g.introDone else { return false }
        return !app.popups.isPresenting
    }

    /// Answers the top popup `id` the way its button does, once it has landed.
    private static func answerTop(_ app: AppModel, _ id: PopupID, _ value: Any?, step: Int, after: Double) async -> Bool {
        guard await wait(6, { host(app)?.stack.last?.request.id == id }) else {
            Log.error("glitch", "\(step): \(id.rawValue) never came up (top \(host(app)?.topID?.rawValue ?? "none"))")
            return false
        }
        await sleep(after)
        guard let h = host(app), let top = h.stack.last, top.request.id == id else { return false }
        let p = mark(step, "answer \(id.rawValue)")
        press(app)
        h.answer(top.id, value)
        await sleep(0.6)
        p.stop()
        return true
    }

    private static func pauseLoop(_ n: Int, gap: Double, app: AppModel, router: Router) async {
        for k in 0..<n {
            guard await wait(15, { levelReady(app) }) else { Log.error("glitch", "pause \(k): no level"); return }
            await sleep(gap)
            let p = mark(k, "pause")
            press(app)
            app.game?.flow.pause()
            await sleep(0.6)
            p.stop()
            guard await answerTop(app, .pause, PopupResult.primary, step: k, after: gap - 0.6) else { return }
        }
    }

    private static func quitLoop(_ n: Int, gap: Double, app: AppModel, router: Router) async {
        for k in 0..<n {
            guard await wait(20, { levelReady(app) }) else { Log.error("glitch", "quit \(k): no level"); return }
            await sleep(gap)
            let p = mark(k, "pause")
            press(app)
            app.game?.flow.pause()
            await sleep(0.6)
            p.stop()
            guard await answerTop(app, .pause, PopupResult.secondary, step: k, after: gap - 0.6),
                  await answerTop(app, .quitLevel, PopupResult.primary, step: k, after: gap),
                  await answerTop(app, .levelFailed, PopupResult.close, step: k, after: gap) else { return }
            // home: its queue (payouts, offers) is answered like a player would, then Play
            guard await wait(8, { atHome(app) }) else { Log.error("glitch", "quit \(k): not home"); return }
            let h = mark(k, "home arrival")
            await sleep(1.0)
            h.stop()
            await settleHome(app, step: k)
            let level = app.store.state.level
            let play = mark(k, "play L\(level)")
            press(app, haptic: .play)
            router.go(.level(app.levelLaunch(for: level)))
            await sleep(1.5)
            play.stop()
        }
    }

    /// Home's queue, answered like a player would: a week-start event page takes the screen (its X goes home), offers and
    /// payouts are popups (closed). Returns once home has been quiet for 1.2 s.
    private static func settleHome(_ app: AppModel, step k: Int) async {
        var quiet = 0.0
        while quiet < 1.2 {
            if case .event = app.router.screen {
                await sleep(0.8)
                let c = mark(k, "event page close")
                press(app)
                EventPageShell<EmptyView>.close(app)
                _ = await wait(3, { app.router.screen.isHome })
                await sleep(0.6)
                c.stop()
                quiet = 0
            } else if let top = host(app)?.stack.last {
                await sleep(0.8)
                press(app)
                host(app)?.answer(top.id, nil)
                quiet = 0
            } else { quiet += 0.2 }
            await sleep(0.2)
        }
    }

    private static func playLoop(_ n: Int, gap: Double, app: AppModel, router: Router) async {
        for k in 0..<n {
            await settleHome(app, step: k)
            guard await wait(10, { app.router.screen.isHome && !app.popups.isPresenting }) else {
                Log.error("glitch", "play \(k): home is not up (\(app.router.screen.logName))"); return
            }
            await sleep(gap + 0.8)
            let level = app.store.state.level
            let p = mark(k, "play L\(level)")
            press(app, haptic: .play)
            router.go(.level(app.levelLaunch(for: level)))
            await sleep(1.0)
            p.stop()
            guard await wait(10, { levelReady(app) }) else { Log.error("glitch", "play \(k): no level"); return }
            await sleep(gap)
            let h = mark(k, "home cut")
            press(app)
            router.go(.home(.normal, tab: .home))
            await sleep(1.0)
            h.stop()
        }
    }

    /// FIX-2 A: page → home arrivals (Profile, the live ladder event page), each open and each return under its own probe.
    private static func pagesLoop(_ n: Int, gap: Double, app: AppModel, router: Router) async {
        // the ladder page to open, looked up ONCE (Events.status is ~20 ms of main thread: inside the loop it showed up as a
        // "home" frame of the measured round trips)
        await settleHome(app, step: 0)
        let st = Events.status(app.store.state, now: app.clock.wallClock(), rules: ShellEconomy.rules(app))
        let ladder = st.live.ladder ?? st.finished.ladder
        for k in 0..<n {
            await settleHome(app, step: k)
            guard await wait(10, { app.router.screen.isHome && !app.popups.isPresenting }) else {
                Log.error("glitch", "pages \(k): home is not up (\(app.router.screen.logName))"); return
            }
            await sleep(gap)
            let o = mark(k, "open profile")
            press(app)
            PayoutSequence.cancel()
            router.go(.profile)
            await sleep(1.2)
            o.stop()
            let b = mark(k, "profile → home")
            press(app)
            router.go(.home(.normal, tab: .home))
            await sleep(1.5)
            b.stop()
            await settleHome(app, step: k)
            guard let lad = ladder else { Log.mark("glitch", "\(k): no ladder page"); continue }
            await sleep(gap)
            let e = mark(k, "open page \(lad.rawValue)")
            press(app)
            router.go(.event(lad == .clawChallenge ? .claw : .balloonRise))
            await sleep(1.5)
            e.stop()
            let c = mark(k, "page → home")
            press(app)
            EventPageShell<EmptyView>.close(app)
            await sleep(1.5)
            c.stop()
        }
    }

    private static func popupLoop(_ n: Int, ids: [String], gap: Double, app: AppModel) async {
        if atHome(app) { await settleHome(app, step: 0) }        // over home itself, not the week-start event page
        for k in 0..<n {
            for raw in ids {
                let parts = raw.split(separator: "~", maxSplits: 1).map(String.init)   // id~variant (':' splits the plan)
                let arg = LaunchArgs.PopupArg(id: parts[0], variant: parts.count > 1 ? parts[1] : nil)
                guard await wait(10, { !app.popups.isPresenting }) else { Log.error("glitch", "popups: \(raw) stuck"); return }
                await sleep(gap)
                let p = mark(k, "open \(raw)")
                press(app)
                DebugPopupLauncher.present(arg, app: app)
                guard await wait(3, { app.popups.isPresenting }) else {
                    p.stop(); Log.error("glitch", "popups: \(raw) did not present"); continue
                }
                await sleep(0.8)
                p.stop()
                await sleep(max(0, gap - 0.8))
                // close: the page's / popup's X (answered with nothing = its fallback, as a dismissal)
                var closes = 0
                while let h = host(app), let top = h.stack.last, closes < 5 {
                    closes += 1
                    let c = mark(k, "close \(top.request.id.rawValue)")
                    press(app)
                    h.answer(top.id, nil)
                    await sleep(0.6)
                    c.stop()
                }
            }
        }
    }
}
#endif
