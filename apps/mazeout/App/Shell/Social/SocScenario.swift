import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-social §7 "Launch args": `-pc.socialScenario <name>` preset states for UI tests and captures; SPEC-architecture
// §9.1 private flags through `args.raw`). Each preset drives the REAL state machines (C3's Events joins / wins on a copy of the
// state at a fixed `-pc.now`), so what a capture shows is what the game would show at that moment — no invented rows.
//   weeklyFresh    L62, the week's group joined now (rank 10 at 0, VERIFIED phone 132)
//   weeklyPodium   L62, joined 2 days ago and 40 wins since (the podium in reach)
//   streakList     L62, today's race joined 6 h ago and 12 wins at a climbing multiplier
//   rocketMid      L62, a race joined 7 min ago, 1 level beaten
//   rocketLost     L62, a race joined 40 min ago, 2 levels beaten; the rivals have finished, so the refresh right after
//                  ends it lost (C3 keeps the ended race in `lastRun` / `lastEndedAt`: the result page draws its final lanes)
//   skyStep1…4     L45, a stage-1 run joined 1 h ago with k first-try wins
//   skyWin         L45, a stage-1 run won just now (the share claim waits)
//   skyFail        L45, a stage-1 run that failed a level just now
//   clawStep       L40, the Claw bar a few points from its step
//   l50            L50, the Weekly Contest not joined (the forced tutorial's state)
// B1 (the weekly rotation; any name starting with "rotation" runs the CALENDAR under -pc.uitest / -pc.capture, which
// otherwise keep the v552 plan — EventRotationPolicy):
//   rotation         L60, nothing else: the week of `-pc.now` decides the featured events
//   rotationBalloon  L45, in an Up & Away week: 3 wins in a row (platform 1's chest waits as a claim)
//   rotationStreak6  L45, in an Up & Away week: 6 wins in a row (the fall page on the next loss; platforms 1-2 paid)

@MainActor enum SocScenario {
    static func applyIfRequested(_ app: AppModel) {
        guard let name = app.args.raw["pc.socialScenario"], !name.isEmpty else { return }
        Task { @MainActor in
            for _ in 0..<200 where app.socialWorld == nil { try? await Task.sleep(nanoseconds: 25_000_000) }
            guard let world = app.socialWorld else { Log.error("social", "scenario \(name): no world"); return }
            let before = app.store.state
            let wall = app.clock.wallClock()
            let rules = ShellEconomy.rules(app)
            let s = await Task.detached(priority: .userInitiated) { build(name, from: before, wall: wall, world: world, rules: rules) }.value
            guard let s else { Log.error("social", "scenario \(name): unknown"); return }
            app.store.mutateAndSave { $0 = s }
            Log.mark("social", "scenario \(name) applied (level \(s.level))")
            SocialModel.shared?.requestAll()
            if name == "rocketLost" {
                // the running race first (for a moment), then the world ends it at an events refresh: lost, kept by C3 in
                // `lastRun` / `lastEndedAt` (SocCompute.rocket draws the result from those; there is no in-memory memo any more)
                try? await Task.sleep(nanoseconds: 400_000_000)
                SocialFlows.refreshEvents(app) { SocialModel.shared?.request(.rocket) }
            }
            ScenarioReady.done = true
        }
    }

    nonisolated static func build(_ name: String, from s0: PlayerState, wall: Date, world: SocialWorld,
                                  rules: EconomyRules) -> PlayerState? {
        var s = s0
        func at(_ minutesAgo: Double) -> Date { wall.addingTimeInterval(-minutesAgo * 60) }
        // the preset replays the past in order: the rewind-safe clock (SocialClock high-water mark) must start before it,
        // then every step raises it again up to `wall`
        s.social.highWater = min(s.social.highWater, Int64(at(3 * 24 * 60).timeIntervalSince1970.rounded(.down)))
        func level(_ n: Int) { if s.level < n { s.level = n }; s.homeSeen = true }
        func win(_ minutesAgo: Double, firstTry: Bool = true) {
            let lv = s.level
            _ = Events.onWin(&s, WinContext(levels: [lv], tag: .normal, firstTry: firstTry, now: at(minutesAgo)), rivals: world, rules: rules)
            s.level = lv + 1
        }
        switch name {
        case "l50":
            level(50)
        case "weeklyFresh":
            level(62)
            _ = Events.joinWeekly(&s, now: at(0), rules: rules)
        case "weeklyPodium":
            level(62)
            _ = Events.joinWeekly(&s, now: at(2 * 24 * 60), rules: rules)
            for k in 0..<40 { win(Double(2 * 24 * 60 - 60 - k * 60)) }
        case "streakList":
            level(62)
            for k in 0..<12 { win(Double(360 - k * 25)) }
        case "rocketMid", "rocketLost":
            level(62)
            let ago: Double = name == "rocketMid" ? 7 : 40
            guard case .success = Events.joinRocketRace(&s, now: at(ago), rules: rules) else { return nil }
            let beaten = name == "rocketMid" ? 1 : 2
            for k in 0..<beaten { win(ago - 2 - Double(k) * 2) }
        case "skyStep1", "skyStep2", "skyStep3", "skyStep4", "skyWin":
            level(45)
            guard case .success = Events.joinSkyJump(&s, now: at(60), rules: rules) else { return nil }
            let k = name == "skyWin" ? rules.events.skyJump.levels(stage: 1) : Int(String(name.last!)) ?? 1
            for i in 0..<k { win(Double(55 - i * 4)) }
        case "skyFail":
            level(45)
            guard case .success = Events.joinSkyJump(&s, now: at(60), rules: rules) else { return nil }
            win(50); win(46)
            _ = Events.onLoss(&s, LossContext(levels: [s.level], reason: .timeUp, now: at(1)), rules: rules)
        case "clawStep":
            level(40)
            for k in 0..<6 { win(Double(120 - k * 10)) }
        case "rotation":
            level(60)
        case "rotationBalloon", "rotationStreak6":
            level(45)
            let n = name == "rotationBalloon" ? 3 : 6
            for k in 0..<n { win(Double(30 - k * 4)) }
        default:
            return nil
        }
        return s
    }
}

/// Set when a requested scenario finished (the social ready file waits for it).
@MainActor enum ScenarioReady { static var done = false }
