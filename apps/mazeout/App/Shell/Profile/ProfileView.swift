import SwiftUI
import PathCore

// SHELL S3 (SPEC-architecture §6.9 "Profile"; SPEC-ui §2.14.1; SPEC-gameplay §13; VERIFIED meta-002 / meta-005 / meta-006; text
// frames tok2 `text2.profile.*`). `Screen.profile`, opened by the home avatar: the page header "Profile" + the red X (→ home, a
// hard cut), the flat #062496 ground, the blue card (the avatar in its frame with the orange pencil → Edit Profile, the name,
// the cyan "Level / 62" plate), "General Stats" between two rules, and the six stat tiles (label above, icon over the pill's
// left end, the value centred on the visible pill; "-" for 0). If the player has never chosen a name, the Username popup opens
// over the page (not forced: X leaves the default `player_` name). Every value is read from `PlayerState` (C3 / SOC1 fields).

struct ProfileView: View {
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    @State private var askedName = false

    var body: some View {
        let t = app.tuning.ui.tokens
        ZStack(alignment: .topLeading) {
            t.color("page.bgProfile", Skin.profileProfileViewPageBgProfile).frame(width: m.size.width, height: m.size.height)
            TopCanvas { ProfileContent() }
            ShellPageHeader(t: t)
            PageTitle(title: "Profile", t: t)
            PopupCloseButton(id: "profile.close", t: t, halo: true) { app.router.go(.home(.normal, tab: .home)) }
                .placed(m.rect(CGRect(333.0, 51.2, 45, 45), .top))
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.profile")
        .onAppear {
            ShopProbe.open(app, "profile open")
            ArtStore.preload(ProfileView.art)
            Log.mark("profile", "open: name \(app.store.state.social.username ?? "default") avatar \(app.store.state.social.avatar)")
            guard !askedName, app.store.state.social.username == nil, !app.args.quietUI || app.args.raw["pc.askName"] == "1" else { return }
            askedName = true
            Task { @MainActor in
                let r = await app.popups.present(Popup<UsernameResult>(.username, style: PopupStyle(dim: .overPage), fallback: .close))
                Log.mark("profile", "username → \(r)")
            }
        }
    }

    /// Behind Loading: the page content once (its card / plate / pill images).
    static func prewarm() -> some View { ProfileContent() }

    static let art: [UIArt] = Avatars.arts + [.iconPencil, .profileStatFirstTry, .profileStatWeeklyWins, .socialScoreChip, .eventRocketRaceRacerMine, .eventSkyJumpIcon,
                                              .eventClawChallengeToken]
}

/// The page's content on the 393-wide reference canvas (top-anchored as a block: `TopCanvas`).
private struct ProfileContent: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        let s = app.store.state
        let name = s.social.displayName(installSeed: s.installSeed)
        ZStack(alignment: .topLeading) {
            ProfileCard().placed(CGRect(12.3, 132.4, 367.6, 116.4))
            GameButton(id: "profile.avatar", label: "Edit Profile", value: "avatar:\(s.social.avatar)", action: openEdit) {
                AvatarFrameTile(index: s.social.avatar, n: 3.6, ring: 0.085)
            }
            .placed(CGRect(23.4, 142.8, 103.4, 97.4))
            GameButton(id: "profile.edit", label: "Edit Profile", action: openEdit) {       // SPEC-ui §6 id
                ArtImage(art: .iconPencil)
            }
            .placed(CGRect(91.2, 207.2, 43.2, 42.0))
            // the name (28.2 / −0.13, face #E3F7FF, outline #16388C 1.8, drop 1.2; left x 137.4, box 115, then "…")
            let nameStyle = GameTextStyle.s2(28.2, -0.13, [Skin.profileProfileViewProfileContentNameStyle0], outline: Skin.profileProfileViewProfileContentNameStyleOutline, 1.78, drop: 1.2)
            LeftText(text: name, style: nameStyle, left: 137.4, baseline: 199.6, box: 115)
                .accessibilityIdentifier("profile.name")
                .accessibilityLabel(Text(verbatim: name))
            LevelPlate(level: s.level).placed(CGRect(258.2, 156.5, 110.1, 63.4))
            // "General Stats" between 1 pt rules from the screen edges to 12 pt of the ink
            let head = GameTextStyle.s2(26.1, -0.34, [Skin.profileProfileViewProfileContentHead0], outline: Skin.profileProfileViewProfileContentHeadOutline, 1.0, drop: 1.0)
            let layout = GameTextLayout.make(String(localized: "General Stats"), postScriptName: head.postScriptName, size: head.size,
                                             tracking: head.tracking)
            let half = layout.advance / 2
            Color(hex: Skin.profileProfileViewProfileContent).frame(width: max(0, 196 - half - 12), height: 1.3).position(x: (196 - half - 12) / 2, y: 276.6)
            Color(hex: Skin.profileProfileViewProfileContent).frame(width: max(0, 393 - (196 + half + 12)), height: 1.3)
                .position(x: (196 + half + 12 + 393) / 2, y: 276.6)
            GameText("General Stats", style: head, maxWidth: 300).at(196, head.capCentre(baseline: 285.0))
            ForEach(Array(ProfileStat.shown(app).enumerated()), id: \.offset) { i, stat in
                StatTile(stat: stat, value: stat.value(s), column: i % 2, row: i / 2)
            }
        }
        .frame(width: 393, height: 852, alignment: .topLeading)
    }

    private func openEdit() {
        Task { @MainActor in
            let r = await app.popups.present(Popup<EditProfileResult>(.editProfile, style: PopupStyle(dim: .overPage), fallback: .close))
            Log.mark("profile", "editProfile → \(r)")
        }
    }
}

/// The six General Stats (SPEC-gameplay §13 counting; SPEC-ui §2.14.1 icons).
struct ProfileStat {
    let label: LocalizedStringResource
    let icon: UIArt?
    /// B1: an art id the generated table does not have yet (Up & Away's R8 request): drawn through `UpAwayArtImage`.
    var iconID: String? = nil
    let iconFrame: CGRect           // relative to the tile column's pill origin
    let value: (PlayerState) -> Int
    let id: String

    /// B1 (VERIFIED v582 balloon.md §6: a 7th tile "… Max Streak"): Up & Away's best streak, while the rotation can run it.
    static let upAndAway = ProfileStat(label: "Up & Away Best Streak", icon: nil, iconID: UpAwayArt.badge,
                                       iconFrame: CGRect(-24.0, -4.0, 48, 54), value: { $0.events.balloon.best }, id: "balloon")

    @MainActor static func shown(_ app: AppModel) -> [ProfileStat] {
        let rot = ShellEconomy.rules(app).events.rotation
        return rot.enabled && !rot.unavailable.contains(EventID.balloonRise.rawValue) ? all + [upAndAway] : all
    }

    static let all: [ProfileStat] = [
        ProfileStat(label: "First Try Wins", icon: .profileStatFirstTry, iconFrame: CGRect(-26.0, -1.0, 57.4, 52.4),
                    value: { $0.stats.firstTryWins }, id: "firstTry"),
        ProfileStat(label: "Weekly Cup Wins", icon: .profileStatWeeklyWins, iconFrame: CGRect(-22.1, -1.0, 48, 51),
                    value: { max($0.stats.weeklyContestWins, $0.social.weeklyContestWins) }, id: "weekly"),
        ProfileStat(label: "Hot Streak Wins", icon: .socialScoreChip, iconFrame: CGRect(-24.0, 2.0, 44, 48.4),
                    value: { $0.events.wins[EventID.streakRace.rawValue] ?? 0 }, id: "streak"),        // SPEC-ui §6 id profile.stat.streak
        ProfileStat(label: "Rocket Rally Wins", icon: .eventRocketRaceRacerMine, iconFrame: CGRect(-23.1, -8.5, 44.7, 64.4),
                    value: { $0.events.wins[EventID.rocketRace.rawValue] ?? 0 }, id: "rocket"),        // SPEC-ui §6 id profile.stat.rocket
        ProfileStat(label: "Cloud Hop Wins", icon: .eventSkyJumpIcon, iconFrame: CGRect(-27.3, -0.5, 58.7, 53.5),
                    value: { $0.events.wins[EventID.skyJump.rawValue] ?? 0 }, id: "sky"),           // SPEC-ui §6 id profile.stat.sky
        ProfileStat(label: "Treasure Climb Wins", icon: .eventClawChallengeToken, iconFrame: CGRect(-26.6, -3.5, 51, 51),
                    value: { $0.events.wins[EventID.clawChallenge.rawValue] ?? 0 }, id: "claw"),
    ]
}

private struct StatTile: View {
    let stat: ProfileStat
    let value: Int
    let column: Int
    let row: Int

    var body: some View {
        // B1: a 4th row for the 7th tile (the row pitch continued)
        let x: [CGFloat] = [56.7, 243.0], y: [CGFloat] = [341.6, 440.0, 540.8, 640.8]
        let labelBase: [CGFloat] = [332.8, 429.9, 526.0, 626.2], labelX: [CGFloat] = [110.1, 293.4], valueX: [CGFloat] = [118.4, 304.6]
        let pill = CGRect(x: x[column], y: y[row], width: column == 0 ? 121.1 : 121.1, height: 52)
        let label = GameTextStyle.s2(13.9, -0.25, [Skin.profileProfileViewStatTileLabel0, Skin.profileProfileViewStatTileLabel1, Skin.profileProfileViewStatTileLabel2], outline: Skin.profileProfileViewStatTileLabelOutline, 0.9, drop: 0.8)
        let v = GameTextStyle.s2(25.1, -1.0, [Skin.profileProfileViewStatTileV0], outline: Skin.profileProfileViewStatTileVOutline, 1.4, drop: 0.8)
        ZStack(alignment: .topLeading) {
            GameText(stat.label, style: label, maxWidth: 165).at(labelX[column], label.capCentre(baseline: labelBase[row]))
            StatPill().placed(pill)
            if let icon = stat.icon {
                ArtImage(art: icon).placed(stat.iconFrame.offsetBy(dx: pill.minX, dy: pill.minY))
            } else if let id = stat.iconID {
                UpAwayArtImage(id: id).placed(stat.iconFrame.offsetBy(dx: pill.minX, dy: pill.minY))
            }
            GameText(verbatim: value > 0 ? "\(value)" : "-", style: v, maxWidth: 80)
                .at(valueX[column], v.capCentre(baseline: pill.minY + 33.3))
                .accessibilityElement()
                .accessibilityIdentifier("profile.stat.\(stat.id)")
                .accessibilityValue(Text(verbatim: "\(value)"))
        }
    }
}

/// The dark stat capsule (face #051F86, a 2 pt lighter rim, a dark inner top shadow; VERIFIED meta-002).
private struct StatPill: View {
    var body: some View {
        Rasterized("statPill") { size in
            let r = size.height / 2
            ZStack {
                RoundedRectangle(cornerRadius: r).fill(Color(hex: Skin.profileProfileViewStatPillFill))
                RoundedRectangle(cornerRadius: r - 2).fill(Color(hex: Skin.profileProfileViewStatPillFillV2)).padding(2)
                RoundedRectangle(cornerRadius: r - 2)
                    .fill(LinearGradient(colors: [Color(hex: Skin.profileProfileViewStatPillColors0, 0.8), .clear], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.35)))
                    .padding(2)
            }
        }
    }
}

/// The blue profile card: the avatar's raised square joined to the long row (1 pt #041F77, 1 pt #0844A7, a light top line
/// #3797F6, face #1960D6 → #0549C0, lower lip #012A83 → #01184D; VERIFIED meta-002).
private struct ProfileCard: View {
    var body: some View {
        Rasterized("profileCard", overflow: 3) { size in
            ZStack(alignment: .topLeading) {
                shape(size).fill(Color(hex: Skin.profileProfileViewProfileCardFill)).offset(y: 3)
                shape(size).fill(Color(hex: Skin.profileProfileViewProfileCardFillV2))
                shape(size).fill(Color(hex: Skin.profileProfileViewProfileCardFillV3)).padding(1)
                shape(size).fill(LinearGradient(colors: [Color(hex: Skin.profileProfileViewProfileCardColors0), Color(hex: Skin.profileProfileViewProfileCardColors1)], startPoint: .top,
                                                 endPoint: UnitPoint(x: 0.5, y: 0.08))).padding(2)
                shape(size).fill(LinearGradient(colors: [Color(hex: Skin.profileProfileViewProfileCardColors0V2), Color(hex: Skin.profileProfileViewProfileCardColors1V2)], startPoint: .top, endPoint: .bottom))
                    .padding(EdgeInsets(top: 3.5, leading: 2.5, bottom: 4.5, trailing: 2.5))
            }
        }
    }

    private func shape(_ size: CGSize) -> ProfileCardShape { ProfileCardShape(avatarWidth: 125.6, rowTop: 16.7) }
}

private struct ProfileCardShape: Shape {
    let avatarWidth: CGFloat
    let rowTop: CGFloat
    func path(in r: CGRect) -> Path {
        var p = Path(roundedRect: CGRect(x: r.minX, y: r.minY, width: avatarWidth, height: r.height), cornerRadius: 25)
        p.addPath(Path(roundedRect: CGRect(x: r.minX, y: r.minY + rowTop, width: r.width, height: r.height - rowTop), cornerRadius: 25))
        return p.normalized()
    }
}

/// The cyan "Level / n" plate (rr 12, 4 navy rivets; "Level" 19.6 gold → orange outlined #16388C, the number 29.8 white).
private struct LevelPlate: View {
    let level: Int
    var body: some View {
        let cap = GameTextStyle.s2(19.6, -0.35, [Skin.profileProfileViewLevelPlateCap0, Skin.profileProfileViewLevelPlateCap1, Skin.profileProfileViewLevelPlateCap2], outline: Skin.profileProfileViewLevelPlateCapOutline, 1.19, drop: 0.81)
        let num = GameTextStyle.s2(29.8, -0.78, [Skin.profileProfileViewLevelPlateNum0], outline: Skin.profileProfileViewLevelPlateNumOutline, 2.3, drop: 0.78)
        ZStack(alignment: .topLeading) {
            Rasterized("profileLevelPlate", overflow: 2) { size in
                ZStack(alignment: .topLeading) {
                    RoundedRectangle(cornerRadius: 12).fill(Color(hex: Skin.profileProfileViewLevelPlateFill)).offset(y: 1.5)
                    RoundedRectangle(cornerRadius: 12).fill(Color(hex: Skin.profileProfileViewLevelPlateFillV2))
                    RoundedRectangle(cornerRadius: 10.5)
                        .fill(LinearGradient(colors: [Color(hex: Skin.profileProfileViewLevelPlateColors0), Color(hex: Skin.profileProfileViewLevelPlateColors1), Color(hex: Skin.profileProfileViewLevelPlateColors2)], startPoint: .top,
                                             endPoint: .bottom))
                        .padding(2.2)
                    ForEach(0..<4, id: \.self) { i in
                        Circle().fill(Color(hex: Skin.profileProfileViewLevelPlateFillV3)).frame(width: 5.5, height: 5.5)
                            .position(x: i % 2 == 0 ? 8.5 : size.width - 8.5, y: i < 2 ? 8.5 : size.height - 8.5)
                    }
                }
            }
            GameText("Level", style: cap, maxWidth: 92).at(57.1, cap.capCentre(baseline: 180.5 - 156.5))
            GameText(verbatim: "\(level)", style: num, maxWidth: 90).at(57.4, num.capCentre(baseline: 207.8 - 156.5))
        }
        .frame(width: 110.1, height: 63.4, alignment: .topLeading)
        .accessibilityElement()
        .accessibilityIdentifier("profile.level")
        .accessibilityValue(Text(verbatim: "\(level)"))
    }
}
