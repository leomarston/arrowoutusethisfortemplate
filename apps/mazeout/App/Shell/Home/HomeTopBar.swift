import SwiftUI
import PathCore

// SHELL S1 (SPEC-architecture §6.4 item 4; design/ui-measure.md `home.*` top bar, VERIFIED 026 / 002 / 035). Back → front:
// the avatar tile (→ Profile), the coin pill "2260" under the coin icon under the green + (→ the Shop tab), the lives pill
// ("Full" / mm:ss / the ∞ time) under the lives heart with its count, the blue gear (→ the Settings popup). All top-anchored.
// The lives countdown ticks once a second ONLY while lives are refilling or unlimited (a periodic TimelineView); a full bar
// has no timer, so home at rest costs the main thread nothing.

struct HomeTopBarView: View {
    let onAvatar: () -> Void
    let onCoins: () -> Void
    let onLives: () -> Void
    let onSettings: () -> Void
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let s = HomeLive.read(app)                                                   // FIX-A1: not the store (parked home)
        let coins = CoinPillDisplay.shared.shown(s)                                  // S3: the part still flying is hidden
        ZStack(alignment: .topLeading) {
            GameButton(id: "home.avatar", label: "Profile", action: onAvatar) {
                AvatarTile(t: t).overlay { HomeAvatarPortrait() }                    // S3: the player's portrait
            }
                .placed(t.rect("home.avatarButton", CGRect(18.7, 36.7, 63.4, 61.4), .top, m))
                .anchor(.avatar)
            // coins: pill < icon < plus
            GameButton(id: "home.coins.plus", label: "Shop", value: "\(coins)", action: onCoins) {
                ZStack(alignment: .topLeading) {
                    let pill = local(t.rect("home.coinPill", CGRect(126.8, 55.7, 73.7, 32), .top, m))
                    TopPill(t: t, n: t.superellipseN("home.coinPill", 5.3)).placed(pill)
                    PlainTopValue(text: "\(coins)", styleID: "home.coins", size: 18.8, tracking: 0, centre: CGPoint(x: 165.5, y: 76.5),
                                  maxWidth: 62, origin: groupOrigin(t))
                    // the rasters carry padding: draw them where their visible pixels land on the phone's (S1 measured 002)
                    ArtImage(art: .iconCoin).placed(local(t.rect("home.coinIconArt", CGRect(93.45, 51.15, 38.5, 38.5), .top, m)))
                    ArtImage(art: .iconPlusGreen).placed(local(t.rect("home.plusBadgeArt", CGRect(116.6, 71.1, 23.5, 23.5), .top, m)))
                }
                .frame(width: coinGroup(t).width, height: coinGroup(t).height, alignment: .topLeading)
            }
            .placed(coinGroup(t))
            .anchor(.coinPill)
            Color.clear
                .accessibilityElement()
                .accessibilityIdentifier("home.coins")
                .accessibilityLabel(Text("Coins"))
                .accessibilityValue(Text(verbatim: "\(coins)"))
                .allowsHitTesting(false)
                .placed(t.rect("home.coinPill", CGRect(126.8, 55.7, 73.7, 32), .top, m))
            LivesGroup(t: t, onTap: onLives)
            GameButton(id: "home.settings", label: "Settings", action: onSettings) {
                BlueSquareButton { ArtImage(art: .glyphGear).frame(width: 26, height: 26) }
            }
            .placed(squareFrame(t.rect("home.gearButton", CGRect(334.3, 49, 40, 39.7), .top, m)))
            .anchor(.settings)
        }
    }

    /// The coin group's box (icon + pill + plus), in screen pt.
    private func coinGroup(_ t: Tokens) -> CGRect {
        let icon = t.rect("home.coinIcon", CGRect(95.7, 53, 34, 34), .top, m)
        let pill = t.rect("home.coinPill", CGRect(126.8, 55.7, 73.7, 32), .top, m)
        let plus = t.rect("home.plusBadge", CGRect(118.8, 73.7, 18.7, 18.7), .top, m)
        return icon.union(pill).union(plus)
    }

    private func groupOrigin(_ t: Tokens) -> CGPoint { coinGroup(t).origin }

    private func local(_ r: CGRect) -> CGRect {
        let o = coinGroup(app.tuning.ui.tokens).origin
        return r.offsetBy(dx: -o.x, dy: -o.y)
    }

    /// BlueSquareButton draws a 40 pt body in a 44 pt frame: centre that frame on the measured 40 pt body.
    private func squareFrame(_ r: CGRect) -> CGRect { CGRect(x: r.midX - 22, y: r.midY - 22, width: 44, height: 44) }
}

/// A plain navy value (no outline) placed by its measured ink centre + baseline, relative to `origin`.
private struct PlainTopValue: View {
    let text: String
    let styleID: String
    let size: CGFloat
    let tracking: CGFloat
    let centre: CGPoint
    let maxWidth: CGFloat
    let origin: CGPoint
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let style = t.text(styleID, GameTextStyle(size: size, tracking: tracking, fill: [Color(hex: 0x00474D)])).sized(size * m.s)
        let p = m.point(centre, .top)
        GameText(verbatim: text, style: style, maxWidth: maxWidth * m.s)
            .at(p.x - origin.x, style.capCentre(baseline: p.y) - origin.y)
    }
}

/// The light-blue pill of the top bar (#DEEEFF, superellipse n 5, a thin darker rim).
struct TopPill: View {
    let t: Tokens
    var n: CGFloat = 5
    var body: some View {
        ZStack {
            Superellipse(n: n).fill(t.color("home.topPillEdge", 0x8BC0BB))
            Superellipse(n: n).fill(LinearGradient(colors: [Color(hex: 0xF4F9FF), t.color("home.topPill", 0xE0F0EB), t.color("home.topPill", 0xE0F0EB)],
                                                   startPoint: .top, endPoint: .bottom)).padding(1)
        }
        .accessibilityHidden(true)
    }
}

/// The avatar tile (SPEC-ui §1.6.12, VERIFIED 002 column x 50 / row y 67): a dark-blue outline, a bright blue ring (#0CAFFB →
/// #008BFE, a light top line, a darker bottom lip), a dark inner rim, and the portrait tile — the default silhouette #637F93 on
/// #86A3AE with a soft inner shadow at the bottom (the player's portrait from S3 on).
private struct AvatarTile: View {
    let t: Tokens
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let ring = t.colors("home.avatarRing", [0x41B7A7, 0x38B2A2, 0x009C8F])
            let tile = CGRect(x: 8.6, y: 8.3, width: w - 17.2, height: h - 16.0)
            ZStack(alignment: .topLeading) {
                Superellipse(n: 3.6).fill(Color(hex: 0x164E4E))
                Superellipse(n: 3.6)
                    .fill(LinearGradient(stops: [.init(color: Color(hex: 0xA5DCC8), location: 0), .init(color: ring[0], location: 0.06),
                                                 .init(color: ring[1], location: 0.3), .init(color: ring[min(2, ring.count - 1)], location: 0.93),
                                                 .init(color: Color(hex: 0x007571), location: 0.965), .init(color: Color(hex: 0x005957), location: 1)],
                                         startPoint: .top, endPoint: .bottom))
                    .padding(1.3)
                Superellipse(n: 3.8).fill(Color(hex: 0x005A57))
                    .frame(width: tile.width + 2.6, height: tile.height + 2.6).offset(x: tile.minX - 1.3, y: tile.minY - 1.3)
                ZStack {
                    t.color("home.avatarPlaceholder", 0x8FA39C)
                    // the default silhouette: a head + wide shoulders reaching the tile's bottom
                    Circle().fill(t.color("home.avatarSilhouette", 0x6B807A))
                        .frame(width: tile.width * 0.46, height: tile.width * 0.46).offset(y: -tile.height * 0.1)
                    Ellipse().fill(t.color("home.avatarSilhouette", 0x6B807A))
                        .frame(width: tile.width * 0.98, height: tile.height * 0.62).offset(y: tile.height * 0.44)
                    LinearGradient(colors: [.clear, Color(hex: 0x475C58, 0.7)], startPoint: UnitPoint(x: 0.5, y: 0.9), endPoint: .bottom)
                }
                .frame(width: tile.width, height: tile.height)
                .clipShape(Superellipse(n: 3.8))
                .offset(x: tile.minX, y: tile.minY)
            }
        }
        .accessibilityHidden(true)
    }
}

/// Lives: the pill ("Full" / mm:ss / the unlimited time) under the heart with its count.
private struct LivesGroup: View {
    let t: Tokens
    let onTap: () -> Void
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let s = HomeLive.read(app)                                                   // FIX-A1: not the store (parked home)
        let heart = t.rect("home.livesHeart", CGRect(212.5, 53, 39, 33), .top, m)
        let pill = t.rect("home.livesPill", CGRect(242.2, 56, 76.7, 27.4), .top, m)
        let box = heart.union(pill)
        let wall = HomeLive.shared.livesClock(app)                                   // FIX-A1: frozen while parked
        let ticking = s.lives.count < 5 || (s.unlimitedLivesUntil.map { $0 > wall } ?? false)
        GameButton(id: "home.lives", label: "Lives", value: LivesText.value(s, now: wall, refill: refill), action: onTap) {
            ZStack(alignment: .topLeading) {
                TopPill(t: t, n: t.superellipseN("home.livesPill", 5)).placed(pill.offsetBy(dx: -box.minX, dy: -box.minY))
                if ticking && HomeLive.shared.active {                               // FIX-A1: no ticks while parked
                    TimelineView(.periodic(from: .now, by: 1)) { _ in content(s, box: box) }
                } else {
                    content(s, box: box)
                }
                ArtImage(art: .heartLives)
                    .placed(t.rect("home.livesHeartArt", CGRect(210.5, 50.9, 42.3, 39.8), .top, m).offsetBy(dx: -box.minX, dy: -box.minY))
                countText(s, box: box)
            }
            .frame(width: box.width, height: box.height, alignment: .topLeading)
        }
        .placed(box)
        .anchor(.livesPill)
    }

    private var refill: Double { ShellEconomy.rules(app).lives.refillSeconds }       // S3: C3's EconomyRules (1800 s, GP §8.1)

    @ViewBuilder private func content(_ s: PlayerState, box: CGRect) -> some View {
        let now = HomeLive.shared.livesClock(app)                                    // FIX-A1: frozen while parked
        let pill = LivesText.state(s, now: now, refill: refill)
        let text: String? = { if case .time(let t) = pill { return t }; return nil }()
        let full = text == nil
        let style = full ? t.text("home.lives", GameTextStyle(size: 19.1, tracking: -0.75, fill: [Color(hex: 0x00474D)]))
                         : t.text("home.livesTimer", GameTextStyle(size: 18.9, tracking: -0.35, fill: [Color(hex: 0x00474D)]))
        let st = style.sized(style.size * m.s)
        let p = m.point(CGPoint(x: full ? 285.4 : 285.1, y: 76.9), .top)
        Group {
            if let text { GameText(verbatim: text, style: st, maxWidth: 52 * m.s) }
            else if pill == .finished { GameText("Finished", style: st, maxWidth: 52 * m.s) }
            else { GameText("Full", style: st, maxWidth: 52 * m.s) }
        }
        .at(p.x - box.minX, st.capCentre(baseline: p.y) - box.minY)
    }

    @ViewBuilder private func countText(_ s: PlayerState, box: CGRect) -> some View {
        let unlimited = s.unlimitedLivesUntil.map { $0 > HomeLive.shared.livesClock(app) } ?? false
        let base = t.text("home.livesCount", GameTextStyle(size: 21.8, fill: [.white], outline: Color(hex: 0x870400), outlineWidth: 0.95,
                                                           drop: 1.04))
        let style = base.sized(base.size * m.s)
        let at = t.textPoint("home.livesCount", baseline: 77.0, centreX: 232.2)
        let p = m.point(CGPoint(x: at.x, y: at.baseline), .top)
        if unlimited {
            InfinityGlyph(outline: Color(hex: 0x870400)).frame(width: 22 * m.s, height: 12 * m.s)
                .at(p.x - box.minX, style.capCentre(baseline: p.y) - box.minY)
        } else {
            GameText(verbatim: "\(s.lives.count)", style: style)
                .at(p.x - box.minX, style.capCentre(baseline: p.y) - box.minY)
        }
    }
}

/// The lives pill's text and its accessibility value (`home.lives`: "n|mm:ss|full|inf:mm:ss", §9.8). SPEC-ui §2.2.2: counting
/// "mm:ss" (always two-digit minutes); the word "Finished" for ≈ 1 s when a life has just arrived; unlimited "mm:ss" below an
/// hour, "1h 20m" from an hour.
enum LivesText {
    enum Pill: Equatable { case full, finished, time(String) }

    static func state(_ s: PlayerState, now: Date, refill: Double) -> Pill {
        if let until = s.unlimitedLivesUntil, until > now {
            let left = until.timeIntervalSince(now)
            return .time(left >= 3600 ? hoursMinutes(left) : clock(left))
        }
        guard s.lives.count < 5 else { return .full }
        guard let anchor = s.lives.anchor else { return .time(clock(refill)) }
        let elapsed = now.timeIntervalSince(anchor)
        let period = max(refill, 1)
        if elapsed >= period, elapsed.truncatingRemainder(dividingBy: period) < 1 { return .finished }
        return .time(clock(max(0, period - elapsed.truncatingRemainder(dividingBy: period))))
    }

    /// nil = "Full" / "Finished"; else the time text.
    static func pill(_ s: PlayerState, now: Date, refill: Double) -> String? {
        if case .time(let t) = state(s, now: now, refill: refill) { return t }
        return nil
    }

    static func value(_ s: PlayerState, now: Date, refill: Double) -> String {
        if let until = s.unlimitedLivesUntil, until > now, case .time(let shown) = state(s, now: now, refill: refill) {
            return "inf:" + shown                                   // CONSISTENCY Y-4: "inf:<the displayed text>"
        }
        switch state(s, now: now, refill: refill) {
        case .full: return "full"
        case .finished: return "\(s.lives.count)|finished"
        case .time(let t): return "\(s.lives.count)|\(t)"
        }
    }

    /// mm:ss (h:mm:ss above an hour: the accessibility value).
    static func clock(_ seconds: Double) -> String {
        let t = Int(seconds.rounded(.up))
        let h = t / 3600, mnt = (t % 3600) / 60, sec = t % 60
        return h > 0 ? String(format: "%d:%02d:%02d", h, mnt, sec) : String(format: "%02d:%02d", mnt, sec)
    }

    /// "1h 20m" (units are the original's letters in both languages).
    static func hoursMinutes(_ seconds: Double) -> String {
        let t = Int(seconds.rounded(.up))
        return "\(t / 3600)h \(((t % 3600) / 60))m"
    }
}

/// The ∞ drawn in code (PCDisplay has no ∞ glyph, fonts.md §7 coverage): a white lemniscate with a dark outline.
struct InfinityGlyph: View {
    var outline: Color
    /// The phone's ∞ face is cream, not white (VERIFIED 035 median).
    var face: Color = Color(hex: 0xF2E6D5)
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let path = Path { p in
                let n = 64
                for i in 0...n {
                    let a = Double(i) / Double(n) * 2 * .pi
                    let d = 1 + sin(a) * sin(a)
                    let x = w / 2 + (w * 0.42) * CGFloat(cos(a) / d), y = h / 2 + (h * 0.9) * CGFloat(sin(a) * cos(a) / d)
                    if i == 0 { p.move(to: CGPoint(x: x, y: y)) } else { p.addLine(to: CGPoint(x: x, y: y)) }
                }
            }
            ZStack {
                path.stroke(outline, style: StrokeStyle(lineWidth: h * 0.46, lineCap: .round, lineJoin: .round))
                path.stroke(face, style: StrokeStyle(lineWidth: h * 0.28, lineCap: .round, lineJoin: .round))
            }
        }
        .accessibilityHidden(true)
    }
}
