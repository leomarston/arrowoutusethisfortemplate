import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-architecture §6.9 Leaderboards; SPEC-ui §2.15.3 Weekly joined, §2.15.4 World, §2.15.5 Country, §1.6.21 JumpPill;
// SPEC-social §3, §4.3; VERIFIED meta-013..028, 107-111). The tab BODY inside S3's LeaderboardPageShell (which draws the header,
// the tab strip, the Weekly countdown chip and the locked text), laid out from the shell's body top (reference y 190):
//   Weekly   the rails + "Weekly Contest" lettering + (i) → the info overlay, the blue field, the podium (ranks 1-3: avatars,
//            rank digits, names, prize bowls 2000 / 1000 / 500, "Score : n"), then the group's list from rank 4 (the player's
//            row green, pinned to the viewport edge when scrolled away). Opening the tab joins the week's group (C3).
//   World    ranks 1-100, "• • •", the player's R ± 10 (green); opens at the top; "Bottom" pill while the player is below.
//   Country  the player's frozen home country (device region): continuous to R + 10 while R ≤ 600, opens centred on the
//            player's row, which pins at the viewport edges; "Top" pill while rank 1 is off screen.
// All rows come from the SocialModel's background snapshots (0 ms of world work on the main thread) and refresh every 5 s.

struct SocLeaderboardBody: View {
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let tab = LeaderboardShellState.shared.tab
        GeometryReader { geo in
            ZStack(alignment: .topLeading) {
                switch tab {
                case .weekly: SocWeeklyTab(size: geo.size)
                case .world: SocLevelTab(kind: .world, size: geo.size)
                case .country: SocLevelTab(kind: .country, size: geo.size)
                }
            }
            .frame(width: geo.size.width, height: geo.size.height, alignment: .topLeading)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("page.leaderboard.body")
    }
}

// MARK: - World / Country

struct SocLevelTab: View {
    let kind: SocListKind
    let size: CGSize
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let model = SocialModel.install(app)
        let host = model.listHost(kind)
        let k = m.s
        ZStack(alignment: .topLeading) {
            SocListRepresentable(host: host, k: k).frame(width: size.width, height: size.height)
            if let j = model.jumps[kind], j != .none {
                let y: CGFloat = (kind == .country && model.pinnedBottom[kind] == true) ? 466.6 : 516.6
                SocJumpPill(jump: j) { host.list.jump() }
                    .frame(width: 82.4 * k, height: 28 * k)
                    .position(x: (155.1 + 41.2) * k, y: (y + 14) * k)
            }
            SocReadyMarker(kind: kind)
        }
        .onAppear {
            model.appear(kind == .world ? .world : .country)
            model.probeOpen(kind.rawValue, kind == .world ? .world : .country)
            Log.mark("leaderboard", "\(kind.rawValue) visible")
        }
        .onDisappear { model.disappear(kind == .world ? .world : .country) }
        // FIX-V2 F-04: Country opens on the player's row every time it is really shown (World opens at the top: no-op)
        .task(id: model.isOnScreen(kind == .world ? .world : .country)) {
            if model.isOnScreen(kind == .world ? .world : .country) { host.list.pageOpened() }
        }
    }
}

/// "Top" / "Bottom" (SPEC-ui §1.6.21: 82.4 × 28, translucent navy #0A2A8A at 0.55, a 1.5 pt light-blue rim #8FB4F4, the label
/// 19.2 pt #E0E0E0 outlined #09066D 1.5; VERIFIED meta-019).
struct SocJumpPill: View {
    let jump: SocJump
    let action: () -> Void

    var body: some View {
        let st = GameTextStyle.s2(19.2, -0.5, [Skin.socialLeaderboardViewsSocJumpPillSt0], outline: Skin.socialLeaderboardViewsSocJumpPillStOutline, 1.5, drop: 0.8)
        let title: LocalizedStringResource = jump == .top ? "Top" : "Bottom"
        GameButton(id: "leaderboard.jump", label: title, action: action) {
            ZStack {
                RoundedRectangle(cornerRadius: 9).fill(Color(hex: Skin.socialLeaderboardViewsSocJumpPillFill, 0.55))
                RoundedRectangle(cornerRadius: 9).stroke(Color(hex: Skin.socialLeaderboardViewsSocJumpPillStroke), lineWidth: 1.5)
                GameText(title, style: st, maxWidth: 70)
            }
        }
    }
}

// MARK: - Weekly

struct SocWeeklyTab: View {
    let size: CGSize
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let model = SocialModel.install(app)
        let k = m.s
        let listTop = (500 - 190) * k
        ZStack(alignment: .topLeading) {
            SocWeeklyHeader(snap: model.weekly)
                .frame(width: 393, height: 320, alignment: .topLeading)
                .scaleEffect(k, anchor: .topLeading)
                .frame(width: size.width, height: 320 * k, alignment: .topLeading)
            SocListRepresentable(host: model.listHost(.weekly), k: k)
                .frame(width: size.width, height: max(0, size.height - listTop))
                .offset(y: listTop)
            SocReadyMarker(kind: .weekly)
        }
        .onAppear {
            model.appear(.weekly)
            model.probeOpen("weekly", .weekly)
            Log.mark("leaderboard", "weekly visible")
        }
        // opening the Weekly tab (really on screen, not the page pre-rendered behind Loading or mounted behind home) joins
        // the week's group (C3 `Events.joinWeekly`, SPEC-social §4.3)
        .task(id: model.isOnScreen(.weekly)) {
            guard model.isOnScreen(.weekly) else { return }
            model.listHost(.weekly).list.pageOpened()          // FIX-V2 F-04: open on the player's row, every open
            if SocialFlows.joinWeeklyIfNeeded(app) { model.request(.weekly) }
        }
        .onDisappear {
            model.disappear(.weekly)
            if let r = model.weekly?.myRank, r > 0 { model.lastSeenWeeklyRank = r }
        }
        .onChange(of: model.weekly?.myRank) { _, r in
            if let r, r > 0, LeaderboardShellState.shared.tab == .weekly { model.lastSeenWeeklyRank = r }
        }
    }
}

/// The fixed Weekly header: rails + lettering + (i), the blue field, the podium (SPEC-ui §2.15.3; y from the body top 190).
struct SocWeeklyHeader: View {
    let snap: SocWeeklySnap?
    @Environment(AppModel.self) private var app

    private func y(_ v: CGFloat) -> CGFloat { v - 190 }

    var body: some View {
        ZStack(alignment: .topLeading) {
            LinearGradient(colors: [Color(hex: Skin.socialLeaderboardViewsSocWeeklyHeaderColors0), Color(hex: Skin.socialLeaderboardViewsSocWeeklyHeaderColors1)], startPoint: .top, endPoint: .bottom)
                .placed(CGRect(0, y(233.6), 393, 270))
            SocRails().placed(CGRect(0, y(200.2), 393, 33.4))
            SocEventLogo(title: "Weekly Cup", frame: CGRect(55, y(191), 287, 54), size: 44)
            GameButton(id: "weekly.info", label: "Info", action: openInfo) {
                SocInfoDisc()
            }
            .placed(CGRect(13.3 - 8, y(242.9) - 8, 24.4 + 16, 22.4 + 16))
            ArtImage(art: .cupPodium).placed(CGRect(2, y(294), 389, 206))
            if let s = snap {
                ForEach(Array(s.podium.enumerated()), id: \.offset) { _, row in
                    SocPodiumSlot(row: row, prize: row.rank <= s.prizes.count ? s.prizes[row.rank - 1] : 0, y0: 190)
                }
            }
        }
        .frame(width: 393, height: 320, alignment: .topLeading)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("weekly.podium")
    }

    private func openInfo() {
        Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>.weeklyContestIntro) }
    }
}

/// The blue (i) disc (SPEC-ui §1.6.20: #00A1FC, a white "i" outlined navy).
struct SocInfoDisc: View {
    var body: some View {
        Rasterized("socInfoDisc", overflow: 1) { size in
            ZStack {
                Circle().fill(Color(hex: Skin.socialLeaderboardViewsSocInfoDiscFill))
                Circle().fill(LinearGradient(colors: [Color(hex: Skin.socialLeaderboardViewsSocInfoDiscColors0), Color(hex: Skin.socialLeaderboardViewsSocInfoDiscColors1), Color(hex: Skin.socialLeaderboardViewsSocInfoDiscColors2)],
                                             startPoint: .top, endPoint: .bottom)).padding(1.5)
                Capsule().fill(Color.white).frame(width: size.width * 0.14, height: size.height * 0.36).offset(y: size.height * 0.1)
                Circle().fill(Color.white).frame(width: size.width * 0.16, height: size.width * 0.16).offset(y: -size.height * 0.2)
            }
        }
        .padding(8)
    }
}

/// One podium block's live parts: the avatar, the rank digit on the hexagon, the name, the prize bowl + amount, "Score : n".
struct SocPodiumSlot: View {
    let row: LeaderboardRow
    let prize: Int
    let y0: CGFloat

    private func y(_ v: CGFloat) -> CGFloat { v - y0 }

    var body: some View {
        let r = row.rank
        // measured frames per place (SPEC-ui §2.15.3; the 3rd avatar INFERRED symmetric)
        let avatar: CGRect = r == 1 ? CGRect(166.8, 252.2, 63.4, 61.4) : r == 2 ? CGRect(34.7, 281.9, 65.4, 61.7) : CGRect(294.0, 296.0, 65.0, 62.0)
        let hex: CGPoint = r == 1 ? CGPoint(x: 195.8, y: 319.3) : r == 2 ? CGPoint(x: 66, y: 349) : CGPoint(x: 326, y: 361)
        let cx: CGFloat = r == 1 ? 196.8 : r == 2 ? 67.7 : 326.5
        let nameBase: CGFloat = r == 1 ? 365.9 : r == 2 ? 396.1 : 410.3
        let bowl: CGRect = r == 1 ? CGRect(165.1, 384.3, 62, 52) : r == 2 ? CGRect(36.7, 405.0, 62, 52) : CGRect(295.5, 416.0, 62, 52)
        let lilac = r == 2
        // VERIFIED meta-013: "player_qqpvpjp" shrinks to 10.9 pt of 21 (minScale 0.5)
        let nameStyle: GameTextStyle = {
            var st = GameTextStyle.s2(21, -0.3, [lilac ? Skin.socialLeaderboardViewsSocPodiumSlotNameStyleStLilac0 : Skin.socialLeaderboardViewsSocPodiumSlotNameStyleStNotLilac0], outline: lilac ? Skin.socialLeaderboardViewsSocPodiumSlotNameStyleStOutlineLilac : Skin.socialLeaderboardViewsSocPodiumSlotNameStyleStOutlineNotLilac, 1.6, drop: 1.0)
            st.minScale = 0.5
            return st
        }()
        let digit = GameTextStyle.s2(20, 0, [Skin.socialLeaderboardViewsSocPodiumSlotDigit0], outline: r == 1 ? Skin.socialLeaderboardViewsSocPodiumSlotDigitOutlineR1 : r == 2 ? Skin.socialLeaderboardViewsSocPodiumSlotDigitOutlineR2 : Skin.socialLeaderboardViewsSocPodiumSlotDigitOutlineNotR2, 1.6, drop: 0.8)
        let amount = GameTextStyle.s2(15.6, -0.3, [Skin.socialLeaderboardViewsSocPodiumSlotAmount0], outline: Skin.socialLeaderboardViewsSocPodiumSlotAmountOutline, 1.5, drop: 0.8)
        let scoreSt = GameTextStyle.s2(16.2, -0.3, [Skin.socialLeaderboardViewsSocPodiumSlotScoreSt0], outline: lilac ? Skin.socialLeaderboardViewsSocPodiumSlotScoreStOutlineLilac : Skin.socialLeaderboardViewsSocPodiumSlotScoreStOutlineNotLilac, 1.3, drop: 0.7)
        ZStack(alignment: .topLeading) {
            SocAvatar(index: row.player.avatar, me: row.isMe).placed(CGRect(avatar.minX, y(avatar.minY), avatar.width, avatar.height))
            GameText(verbatim: "\(r)", style: digit).at(hex.x, digit.capCentre(baseline: y(hex.y) + 7.1))
            GameText(verbatim: row.player.name, style: nameStyle, maxWidth: 110).at(cx, nameStyle.capCentre(baseline: y(nameBase)))
            if prize > 0 {
                ArtImage(art: .coinBowl).placed(CGRect(bowl.minX, y(bowl.minY), bowl.width, bowl.height))
                GameText(verbatim: "\(prize)", style: amount, maxWidth: 50).at(bowl.midX, amount.capCentre(baseline: y(bowl.minY) + 45.5))
            }
            RoundedRectangle(cornerRadius: 7).fill(Color.black.opacity(0.28))
                .placed(CGRect(cx - 50, y(479.2) - 17.5, 100, 24))
            GameText("Score : \(row.value)", style: scoreSt, maxWidth: 96)
                .at(cx, scoreSt.capCentre(baseline: y(479.2)))
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier(row.isMe ? "leaderboard.me" : "leaderboard.row.\(r)")
        .accessibilityLabel(Text(verbatim: row.player.name))
        .accessibilityValue(Text(verbatim: row.isMe ? "\(r)" : "\(row.value)"))
    }
}

// MARK: - capture readiness

/// Writes Documents/social-ready.json once the list shows a snapshot (captures wait for it; `-pc.capture 1` only), and
/// exposes `social.ready` (value = the list kind) for UI tests.
struct SocReadyMarker: View {
    let kind: SocListKind
    @Environment(AppModel.self) private var app

    var body: some View {
        let model = SocialModel.install(app)
        let v = model.listVersion[kind] ?? 0
        Color.clear.frame(width: 1, height: 1)
            .accessibilityElement()
            .accessibilityIdentifier("social.ready")
            .accessibilityValue(Text(verbatim: v > 0 ? kind.rawValue : "pending"))
            .onChange(of: v) { _, nv in if nv == 1 { SocReady.mark("leaderboard:\(kind.rawValue)", app: app) } }
            .onAppear { if v > 0 { SocReady.mark("leaderboard:\(kind.rawValue)", app: app) } }
    }
}

/// Marks the social ready file once `ready` holds (the event pages: their snapshot arrived).
struct SocReadyWhen: View {
    let ready: Bool
    let name: String
    @Environment(AppModel.self) private var app
    @State private var done = false
    var body: some View {
        Color.clear.frame(width: 1, height: 1)
            .accessibilityElement()
            .accessibilityIdentifier("social.ready")
            .accessibilityValue(Text(verbatim: ready ? name : "pending"))
            .onAppear { if ready && !done { done = true; SocReady.mark(name, app: app) } }
            .onChange(of: ready) { _, r in if r && !done { done = true; SocReady.mark(name, app: app) } }
    }
}

@MainActor enum SocReady {
    /// After two presented frames: the social ready file (capture mode) + a log mark.
    static func mark(_ screen: String, app: AppModel) {
        Task { @MainActor in
            if app.args.raw["pc.socialScenario"] != nil { for _ in 0..<80 where !ScenarioReady.done { try? await Task.sleep(nanoseconds: 25_000_000) } }
            await FrameWaiter.frames(2)
            CaptureReady.mark(screen: screen, app: app, file: "social-ready.json")
        }
    }
}
