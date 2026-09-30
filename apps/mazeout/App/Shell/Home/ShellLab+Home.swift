// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
import SwiftUI
import PathCore

// SHELL S3 lab pages (SPEC-architecture §9.5; Debug hook reachable only with `-pc.go shelllab -pc.lab <page>`, D21). They drive
// the REAL home through the router with the entry a win would give it:
//   homeReturn   banks the coins (`PlayerState.pendingCoinFly`, as C3's finishAttempt does) and goes home with
//                `.afterWin(WinSummary(outcomes:))`: `-pc.payoutCoins N` (20), `-pc.payoutClaw m` (Claw points added, 0 = none),
//                `-pc.payoutMult a:b` (the multiplier step, none by default), `-pc.payoutFirst 1` (the FTUE first home, +120)
//   pileRefill   goes home as if back from an event page (the capsule machine's pile refills)
//   tabTour      home → Shop → home → Leaderboard → home → Profile → home through the router, 2 s apart, each switch's frames
//                logged ("[PC][perf] tab <name> frames n max x ms over20 k")
// The home then plays PayoutSequence exactly as after a real win; its beats are logged ([PC][payout] …).

@MainActor enum S3Lab {
    static func make(_ page: String?, app: AppModel) -> AnyView? {
        switch page {
        case "homeReturn": return AnyView(S3LabRedirect(kind: .homeReturn))
        case "pileRefill": return AnyView(S3LabRedirect(kind: .pileRefill))
        case "tabTour": return AnyView(S3TabTour())
        default: return nil
        }
    }
}

/// The real `HomeView` hosted by the lab screen (the router's first screen stays the lab, so a capture's `-pc.freezeAt coinFly@t`
/// wait does not hold the router's queue), entered with the entry a win gives it.
private struct S3LabRedirect: View {
    enum Kind { case homeReturn, pileRefill }
    let kind: Kind
    @Environment(AppModel.self) private var app
    @State private var entry: HomeEntry?

    var body: some View {
        ZStack {
            Color(hex: Skin.homeShellLabHomeS3LabRedirect)
            if let entry { HomeView(tab: .home, refill: kind == .pileRefill ? 1 : 0, labEntry: entry) }
        }
        .accessibilityIdentifier("screen.shelllab")
        .task {
            switch kind {
            case .pileRefill:
                entry = .normal                                             // refills on creation (refill token 1)
            case .homeReturn:
                let raw = app.args.raw
                let coins = Int(raw["pc.payoutCoins"] ?? "") ?? (raw["pc.payoutFirst"] == "1" ? 120 : 20)
                var outcomes: [EventOutcome] = []
                if let m = raw["pc.payoutMult"]?.split(separator: ":").compactMap({ Int($0) }), m.count == 2 {
                    outcomes.append(.multiplier(from: m[0], to: m[1]))
                    outcomes.append(.streakRaceScore(m[0]))
                }
                if let claw = Int(raw["pc.payoutClaw"] ?? ""), claw > 0 {
                    let rules = ShellEconomy.rules(app)
                    let st = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
                    let target = st.claw?.target ?? 300
                    let total = min(target, (st.claw?.points ?? 0) + claw)
                    outcomes.append(.clawPoints(added: claw, total: total, target: target))
                    app.store.mutate { $0.events.claw.points = total }
                }
                app.store.mutateAndSave { $0.pendingCoinFly = coins }
                let level = app.store.state.level
                let summary = WinSummary(levels: [max(1, level - 1)], reward: coins, tag: .normal, outcomes: outcomes)
                Log.mark("lab", "homeReturn: coins \(coins) outcomes \(outcomes.count)")
                entry = raw["pc.payoutFirst"] == "1" ? .firstHome(summary) : .afterWin(summary)
            }
        }
    }
}

/// Drives the router like taps on the nav / avatar / X would, with a frame probe around each switch.
private struct S3TabTour: View {
    @Environment(AppModel.self) private var app
    var body: some View {
        Color(hex: Skin.homeShellLabHomeS3TabTour)
            .onAppear { Task { @MainActor in await S3TabTour.run(app) } }   // not `.task`: the tour outlives this lab view
    }

    private static func run(_ app: AppModel) async {
                let steps: [(String, Screen)] = [("home", .home(.normal, tab: .home)), ("shop", .home(.normal, tab: .shop)),
                                                 ("home", .home(.normal, tab: .home)), ("leaderboard", .home(.normal, tab: .leaderboard)),
                                                 ("home", .home(.normal, tab: .home)), ("profile", .profile),
                                                 ("home", .home(.normal, tab: .home)), ("shop", .home(.normal, tab: .shop)),
                                                 ("home", .home(.normal, tab: .home))]
                try? await Task.sleep(nanoseconds: 1_500_000_000)
                for (name, screen) in steps {
                    let probe = FrameProbe("tab \(name)")
                    probe.start()
                    app.router.go(screen)
                    try? await Task.sleep(nanoseconds: 1_000_000_000)
                    probe.stop()
                    try? await Task.sleep(nanoseconds: 800_000_000)
                }
                Log.mark("lab", "tabTour done")
    }
}
#endif
