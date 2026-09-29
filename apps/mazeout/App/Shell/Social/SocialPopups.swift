import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-architecture §6.6 "social" row: weeklyContestTutorial, weeklyContestIntro, clawInfo, skyJump pages,
// rocketRace pages, streakRaceBoard; §9.1 `-pc.popup`). Where the SOC2 panels plug into S1's popup host — the same hook shape
// as S2Popups / S3Popups. SHELL wires it (one line each, requested in SOC2's report):
//   PopupHost.swift  `PopupContent.hasPanel` / `isPage` / `make`: `SocialPopups.hasPanel(r)`, `.isPage(r)`, `.make(r, answer:)`
//   Router.swift     `DebugPopupLauncher` default branch: `if await SocialPopups.debugPresent(p, app: app) { return }`
//   RootView.swift   `PopupPrewarm`: `ShellPrewarm.items` stages `SocialPopups.prewarm(app)`, one item per frame
// Custom ids (no ◆ PopupID case): `streakInfo` (the Streak Race (i)), `weeklyResult` (rank / prize params); B1: `balloonInfo`
// (Up & Away's (i)), `balloonFall` (the fail flow's fall page, param `from`).

@MainActor enum SocialPopups {
    static let customIDs: Set<String> = ["streakInfo", "weeklyResult", "balloonInfo", "balloonFall"]

    static func hasPanel(_ r: PopupRequest) -> Bool {
        switch r {
        case .weeklyContestTutorial, .weeklyContestIntro, .clawInfo, .skyJump, .rocketRace, .streakRaceBoard: return true
        case .custom(let id, _): return customIDs.contains(id)
        default: return false
        }
    }

    /// Full pages drawn on the live screen (their own ground / dim): the forced Weekly step (its hole follows the nav bar),
    /// the Streak Race board, the Sky Jump progress map, the Rocket Race result.
    static func isPage(_ r: PopupRequest) -> Bool {
        switch r {
        case .weeklyContestTutorial, .streakRaceBoard: return true
        case .skyJump(let p): return p == .progress
        case .rocketRace(let p): return p == .result
        case .custom(let id, _): return id == "balloonFall"                     // B1: the fall page is a full page
        default: return false
        }
    }

    @ViewBuilder static func make(_ r: PopupRequest, answer: PopupAnswer) -> some View {
        switch r {
        case .weeklyContestTutorial: SocWeeklyTutorial(answer: answer)
        case .weeklyContestIntro: SocWeeklyInfo(answer: answer)
        case .clawInfo: SocClawInfo(answer: answer)
        case .streakRaceBoard: SocStreakPage(answer: answer)
        case .skyJump(let p):
            switch p {
            case .join, .offer: SocSkyOffer(answer: answer)
            case .matching: SocSkyMatching(answer: answer)
            case .tutorial: SocSkyTutorial(answer: answer)
            case .progress: SocSkyMap(answer: answer)
            case .win: SocSkyWin(answer: answer)
            }
        case .rocketRace(let p):
            switch p {
            case .offer: SocRocketOffer(answer: answer)
            case .tutorial: SocRocketTutorial(answer: answer)
            case .result: SocRocketPage(answer: answer)
            }
        case .custom(let id, let params):
            if id == "streakInfo" {
                SocStreakInfo(answer: answer)
            } else if id == "weeklyResult" {
                SocWeeklyResult(rank: Int(params["rank"] ?? "") ?? 0, prize: Int(params["prize"] ?? "") ?? 0, answer: answer)
            } else if id == "balloonInfo" {
                SocBalloonInfo(answer: answer)
            } else if id == "balloonFall" {
                SocBalloonPage(fall: Int(params["from"] ?? "") ?? 0, answer: answer)
            } else {
                EmptyView()
            }
        default: EmptyView()
        }
    }

    /// The style each SOC2 popup is presented with (dims SPEC-ui §1.3).
    static func style(_ r: PopupRequest) -> PopupStyle {
        switch r {
        case .weeklyContestTutorial: return PopupStyle(dim: .none, holdsLevelTimer: false, inputLock: true)
        case .weeklyContestIntro, .clawInfo: return PopupStyle(dim: .unlock, closesOnTapAnywhere: true)
        case .streakRaceBoard: return PopupStyle(dim: .none)
        case .skyJump(let p):
            switch p {
            case .matching: return .skyMatch
            case .tutorial: return PopupStyle(dim: .info, closesOnTapAnywhere: true)
            case .progress: return PopupStyle(dim: .none)
            default: return .standard
            }
        case .rocketRace(let p):
            switch p {
            case .tutorial: return PopupStyle(dim: .info, closesOnTapAnywhere: true)
            case .result: return PopupStyle(dim: .none)
            default: return .standard
            }
        case .custom(let id, _):
            switch id {
            case "streakInfo": return PopupStyle(dim: .info, closesOnTapAnywhere: true)
            case "balloonInfo": return PopupStyle(dim: .unlock, closesOnTapAnywhere: true)      // B1: like the Treasure Climb (i)
            case "balloonFall": return PopupStyle(dim: .none)                                    // B1: a full page, 1-frame cut
            default: return .standard
            }
        default: return .standard
        }
    }

    /// An info overlay by custom id (the Streak Race (i)).
    static func showInfo(_ app: AppModel, _ id: String) {
        let r = PopupRequest.custom(id: id, params: [:])
        Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>(r, style: style(r), fallback: .close)) }
    }

    /// `-pc.popup <id>[:variant]` for the SOC2 ids. False for an id SOC2 does not own.
    static func debugPresent(_ p: LaunchArgs.PopupArg, app: AppModel) async -> Bool {
        SocialModel.install(app)
        let r: PopupRequest
        switch p.id {
        case PopupID.weeklyContestTutorial.rawValue: r = .weeklyContestTutorial
        case PopupID.weeklyContestIntro.rawValue: r = .weeklyContestIntro
        case PopupID.clawInfo.rawValue: r = .clawInfo
        case PopupID.streakRaceBoard.rawValue: r = .streakRaceBoard
        case PopupID.skyJump.rawValue: r = .skyJump(SkyJumpPage(rawValue: p.variant ?? "offer") ?? .offer)
        case PopupID.rocketRace.rawValue: r = .rocketRace(RocketRacePage(rawValue: p.variant ?? "offer") ?? .offer)
        case "streakInfo": r = .custom(id: "streakInfo", params: [:])
        case "balloonInfo": r = .custom(id: "balloonInfo", params: [:])                        // B1
        case "balloonFall": r = .custom(id: "balloonFall", params: ["from": p.variant ?? "3"])  // B1: -pc.popup balloonFall:<from>
        case "weeklyResult":
            let rank = Int(p.variant ?? "") ?? 1
            let prizes = ShellEconomy.rules(app).events.weekly.prizes
            r = .custom(id: "weeklyResult", params: ["rank": "\(rank)", "prize": "\(rank >= 1 && rank <= prizes.count ? prizes[rank - 1] : 0)"])
        default: return false
        }
        if case .weeklyContestTutorial = r {
            // the real forced flow: the tab → the Weekly tab + the info overlay → the join
            await SocialFlows.weeklyTutorial(app)
            Log.mark("popup", "\(p.id) flow done")
            return true
        }
        // the data behind the panel first (the world is built off the main thread during Loading)
        for _ in 0..<60 where app.socialWorld == nil { try? await Task.sleep(nanoseconds: 50_000_000) }
        SocialModel.shared?.requestAll([.sky, .rocket, .streak])
        try? await Task.sleep(nanoseconds: 150_000_000)
        let answer = await app.popups.present(Popup<PopupResult>(r, style: style(r), fallback: .close))
        Log.mark("popup", "\(p.id) → \(answer)")
        return true
    }

    /// Rendered once, invisibly, behind Loading (the first presentation's SwiftUI graph and glyph rasters are paid there).
    /// Three event pages too, with `socPrewarm` set (no side effects, no shared list host). Measured in Release from a settled
    /// home (build/soc2/lab/open-*.lab-open.json, 3 runs each): first-open worst frame Streak Race 55 → 12 ms, Rocket Race
    /// 32 → 0 ms, Sky Jump 66 → 21 ms on average. The Claw page is left out: its first open was already 0-21 ms and a
    /// prewarmed Claw made it slower (28-79 ms) in all three runs.
    /// FIX-A1: one item per frame (RootView `PopupPrewarm` stages every owner's list).
    static func prewarm(_ app: AppModel) -> [ShellPrewarmItem] {
        let host = PopupHost(ui: app.tuning.ui)
        return [
            ShellPrewarmItem("soc.rocketOffer", ReferenceCanvas { SocRocketOffer(answer: PopupAnswer(id: -61, host: host)) }
                .environment(\.socPrewarm, true)),
            ShellPrewarmItem("soc.skyOffer", ReferenceCanvas { SocSkyOffer(answer: PopupAnswer(id: -62, host: host)) }
                .environment(\.socPrewarm, true)),
            ShellPrewarmItem("soc.streakInfo", ReferenceCanvas { SocStreakInfo(answer: PopupAnswer(id: -63, host: host)) }
                .environment(\.socPrewarm, true)),
            ShellPrewarmItem("soc.streakPage", SocStreakPage().environment(\.socPrewarm, true)),
            ShellPrewarmItem("soc.rocketPage", SocRocketPage().environment(\.socPrewarm, true)),
            ShellPrewarmItem("soc.skyMap", SocSkyMap().environment(\.socPrewarm, true)),
            // B1: Up & Away's page, its (i) and the win-panel strip pay their first render behind Loading too
            ShellPrewarmItem("soc.balloonPage", SocBalloonPage().environment(\.socPrewarm, true)),
            ShellPrewarmItem("soc.balloonInfo", ReferenceCanvas { SocBalloonInfo(answer: PopupAnswer(id: -64, host: host)) }
                .environment(\.socPrewarm, true)),
            ShellPrewarmItem("soc.balloonStrip", ReferenceCanvas {
                BalloonStrip(data: BalloonStripData(from: 1, to: 2, platforms: [2, 5, 8, 13, 20, 28, 36, 46, 77, 120], paid: 0,
                                                    timeLeft: "1d 2h"), shownAt: nil)
            }.environment(\.socPrewarm, true)),
        ]
    }
}
