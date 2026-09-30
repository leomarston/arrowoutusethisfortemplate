import SwiftUI
import UIKit
import PathCore

// SOCIAL — B1 EVENTS-P: "Up & Away" (EventID "balloonRise"; our name, T1 / ruling 38), the original v582 Balloon Rise's rules and
// screens 1:1 (build/p/PH0/balloon.md, VERIFIED on the owner's phone; motion-catalog §11.4-§11.5), with OUR copy and art:
//   SocBalloonPage    `Screen.event(.balloonRise)`: a 1-frame cut in and out. A tall scrolling tower: a dark track up its left
//                     edge filling green to the count with a yellow counter badge, the milestone clouds 0 · 2 · 5 · … · 120 (passed
//                     = green), a ledge per platform with its "Step N" sign and its chest ((i) → the reward bubble; a check once
//                     paid), the balloon floating at the count. It opens scrolled to the balloon; a speech bubble pops in over
//                     ≈ 0.13 s after the cut (the next chest's reward, or "Already collected!" over the last paid one). After a
//                     win the balloon RISES to the new count on the next open (+0.09 s, ≈ 1.1 s ease-in-out). Header: our
//                     lettering, (i), the week's countdown, X.
//   the fall page     `PopupRequest.custom("balloonFall", from: n)`: the same page inserted by the fail flow after its last band
//                     when a streak ≥ 2 was lost — the balloon FALLS from n to the ground from the page's first frame (≈ 0.95 s
//                     ease-in-out), the green fill drains in ≈ 0.75 s; X → Level Failed (FailFlowDirector).
//   SocBalloonInfo    `.custom("balloonInfo")`: the (i) — three illustrated lines joined by pointers, the red card, "Tap to
//                     Continue" (dim 0.90, staggered pops like the Treasure Climb (i)).
//   BalloonStrip      the win panel's strip while Up & Away runs (in place of the Hot Streak strip; the Level Failed panel keeps
//                     the Hot Streak strip): a horizontal track of milestone clouds and chests, the balloon on it; ≈ 0.18 s after
//                     the panel it slides ONE step right (39 pt, ≈ 0.77 s ease-in-out) and the green fill grows.
// Art: the balloon, the tower and the home token are the art lane's R8 requests (`UpAwayArt`); until they exist a DEBUG build
// draws the hatched DebugPlaceholder and a RELEASE build does not run Up & Away at all (EventRotationPolicy: never ship stand-in
// content). A4 ART-INTEG (R8, art/lanes/events-d1.handoff.json "upaway"): the page is drawn from R8's PIECES on B1's geometry —
// the D1 dawn-to-night sky, two clouds, the masonry shaft tiled every 340 pt, the observatory top, the foot with the launch pad
// and the town, a timber ledge per platform (B1's code-drawn ledge bar, sign and pad are gone). The track, milestone clouds,
// counter and bubble stay code-drawn chrome; chests, check and info icons are existing art.

/// Where things sit on the page's tall content (393 pt wide, y down).
struct BalloonTrackGeometry {
    let platforms: [Int]
    /// Ground → platform 1: 2 wins × 47 pt (VERIFIED ≈ 47 pt per step at the tower's foot); ledge to ledge 340 pt (≈ 1.4
    /// platforms per 500-pt swipe, VERIFIED).
    static let groundGap: CGFloat = 94
    static let pitch: CGFloat = 340
    static let sky: CGFloat = 330          // above the last ledge (the dome)
    static let street: CGFloat = 250       // below the ground line (the landing pad, the city)

    var groundY: CGFloat { height - Self.street }
    var height: CGFloat { Self.sky + Self.groundGap + CGFloat(max(0, platforms.count - 1)) * Self.pitch + Self.street }

    func y(platform i: Int) -> CGFloat { groundY - Self.groundGap - CGFloat(i) * Self.pitch }

    /// The height of a count (piecewise linear between the milestones; past the last it keeps the last gap's slope, capped).
    func y(count c: Double) -> CGFloat {
        var prevAt = 0.0, prevY = groundY
        for (i, at) in platforms.enumerated() {
            let yi = y(platform: i)
            if c <= Double(at) {
                let k = (c - prevAt) / max(1, Double(at) - prevAt)
                return prevY + (yi - prevY) * CGFloat(k)
            }
            prevAt = Double(at); prevY = yi
        }
        return max(Self.sky * 0.5, prevY - CGFloat(min(c - prevAt, 40)) * 2)
    }
}

/// FIX-2 lane B (R8-o3 / R8-o4): the tower's ledge / chest / balloon layout in one place (the views and SocialScreensTests read it).
enum BalloonLayout {
    static let ledgeSize = CGSize(width: 240, height: 150)
    /// A4: R8's ledge art has its frame's top-left at (60, y − 94).
    static func ledgeOrigin(_ geo: BalloonTrackGeometry, _ i: Int) -> CGPoint { CGPoint(x: 60, y: geo.y(platform: i) - 94) }
    /// The chest box in the ledge's frame. v582's chests sit LEFT of the balloon's column (x ≈ 130-200 on its page); B1's box
    /// at local x 146 (page x 206-284) put platform 1's chest BEHIND the balloon at low counts (R8 / A4 open issue).
    static let chestBox = CGRect(x: 70, y: 22, width: 78, height: 70)
    static func chestFrame(_ geo: BalloonTrackGeometry, _ i: Int) -> CGRect {
        let o = ledgeOrigin(geo, i)
        return chestBox.offsetBy(dx: o.x, dy: o.y)
    }
    /// The balloon: R8's 150 × 220 hero frame centred on x 285, its basket resting on the count's height.
    static let heroCentreX: CGFloat = 285
    static let heroSize = CGSize(width: 150, height: 220)
    static func heroFrame(_ geo: BalloonTrackGeometry, count: Double) -> CGRect {
        CGRect(x: heroCentreX - heroSize.width / 2, y: geo.y(count: count) - heroSize.height, width: heroSize.width, height: heroSize.height)
    }
    /// The reward bubble over a chest (its tail over the chest's left half, as before the move).
    static func bubbleCentre(_ geo: BalloonTrackGeometry, _ i: Int) -> CGPoint {
        CGPoint(x: chestFrame(geo, i).midX - 15, y: geo.y(platform: i) - 130)
    }
    /// v582's idle drift of the balloon: ±2 pt, one breath every ~4 s.
    static let driftAmplitude: CGFloat = 2
    static let driftPeriod: Double = 4
}

/// FIX-2 lane B (R8-o4): the balloon as a UIImageView whose idle drift is ONE Core Animation loop on the render server
/// (0 main-thread work per frame while the page idles); the rise / fall still moves its frame. Off in capture mode.
private struct DriftingHero: UIViewRepresentable {
    let image: UIImage?
    let drift: Bool

    func makeUIView(context: Context) -> UIImageView {
        let v = UIImageView(image: image)
        v.contentMode = .scaleAspectFit
        v.isUserInteractionEnabled = false
        if drift { Self.addDrift(v.layer) }
        return v
    }

    func updateUIView(_ v: UIImageView, context: Context) {
        if v.image !== image { v.image = image }
        if drift, v.layer.animation(forKey: "drift") == nil { Self.addDrift(v.layer) }
        if !drift { v.layer.removeAnimation(forKey: "drift") }
    }

    static func addDrift(_ layer: CALayer) {
        let a = CABasicAnimation(keyPath: "transform.translation.y")
        a.fromValue = -BalloonLayout.driftAmplitude
        a.toValue = BalloonLayout.driftAmplitude
        a.duration = BalloonLayout.driftPeriod / 2
        a.autoreverses = true
        a.repeatCount = .infinity
        a.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        a.isRemovedOnCompletion = false
        layer.add(a, forKey: "drift")
    }
}

/// The last count the page drew for this week (the next open rises from it): `flags.seen` "balloonShown-<week>.<count>" (one
/// key, the kind-prefix pruning of the home queue's keys).
@MainActor enum BalloonShown {
    static func last(_ app: AppModel, week: Int) -> Int? {
        let prefix = "balloonShown-\(week)."
        return app.store.state.flags.seen.first { $0.hasPrefix(prefix) }.flatMap { Int($0.dropFirst(prefix.count)) }
    }

    static func record(_ app: AppModel, week: Int, count: Int) {
        let key = "balloonShown-\(week).\(count)"
        guard !app.store.state.flags.seen.contains(key) else { return }
        app.store.mutateAndSave { st in
            st.flags.seen = st.flags.seen.filter { !$0.hasPrefix("balloonShown-") }
            st.flags.seen.insert(key)
        }
    }
}

/// The chest art of a platform (the phone's colour cycle red, blue, green, pink, teal on our three chest renders).
enum BalloonChest {
    static func art(_ i: Int) -> UIArt { [.rewardChest3, .rewardChest2, .rewardChest1, .rewardChest3, .rewardChest2][i % 5] }
}

/// A requested art id: the file when it exists, else (DEBUG only) the hatched placeholder; Release draws nothing.
struct UpAwayArtImage: View {
    let id: String
    var contentMode: ContentMode = .fit
    var body: some View {
        if let a = UpAwayArt.art(id) {
            ArtImage(art: a, contentMode: contentMode)
        } else {
            #if DEBUG
            DebugPlaceholder(name: id)
            #else
            Color.clear
            #endif
        }
    }
}

// MARK: - the page

struct SocBalloonPage: View {
    /// The fall page: the streak that was lost (the balloon falls from it); nil = the normal page.
    var fall: Int? = nil
    var answer: PopupAnswer? = nil
    @Environment(\.socPrewarm) private var prewarm
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    @State private var shownAt: Double?
    @State private var from: Double?
    @State private var bubble: Int?
    /// The rise / fall runs (≤ 1.4 s after the cut); the timeline is paused otherwise (0 work at rest).
    @State private var animating = false
    /// B1b (v582 PH-0a): opened from the home's "Finished" bar — the ENDED week's Up & Away as it stood (the chip reads
    /// "Finished"); kept after its hold was dropped at the open. Never on the fall page (that is this week's event).
    @State private var held: Events.BalloonStatus?

    var body: some View {
        let t = app.tuning.ui.tokens
        let rules = ShellEconomy.rules(app)
        let status = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
        let ended = fall == nil ? (held ?? status.finished.balloon) : nil
        let b = ended ?? status.balloon
        let now = SocTime.now(app)
        let platforms = b?.platforms ?? rules.events.balloonRise.platforms.map(\.at)
        let geo = BalloonTrackGeometry(platforms: platforms)
        let target = Double(fall != nil ? 0 : (b?.streak ?? 0))
        let paid = b?.paid ?? 0
        let k = m.s
        ZStack(alignment: .topLeading) {
            BalloonSky().frame(width: m.size.width, height: m.size.height)
            ScrollViewReader { proxy in
                ScrollView(.vertical, showsIndicators: false) {
                    TimelineView(.animation(minimumInterval: nil, paused: animationDone)) { ctx in
                        let c = count(at: ctx.date, target: target)
                        BalloonTower(geo: geo, count: c, fill: fillCount(at: ctx.date, target: target), paid: paid,
                                     rewards: rules.events.balloonRise.platforms.map(\.grant), bubble: bubble,
                                     drift: !app.args.capture && !prewarm, onChest: { i in bubble = i })
                    }
                    .frame(width: 393, height: geo.height, alignment: .topLeading)
                    .scaleEffect(k, anchor: .topLeading)
                    .frame(width: m.size.width, height: geo.height * k, alignment: .topLeading)
                }
                .onAppear { scroll(proxy, geo: geo, target: target) }
            }
            ZStack(alignment: .topLeading) {
                LinearGradient(colors: [Color(hex: Skin.socialBalloonViewsSocBalloonPageColors0, 0.85), .clear], startPoint: .top, endPoint: .bottom)
                    .frame(width: 393, height: 170)
                SocEventLogo(title: "Up & Away", frame: CGRect(58, 50, 277, 60), size: 40)
                // FIX-2 B review (L28): the chip ticks on its own; with no Up & Away of this player's to count down (not this
                // week's event: a debug `-pc.go`), no chip — not a stale "00:00"
                if let end = b?.endsAt ?? (status.live.ladder == .balloonRise ? status.week?.end : nil) {
                    PageTimerChip(seconds: SocTime.left(end, now: now), id: "balloon.timer", finished: ended != nil,
                                  live: (ends: end, now: now, clock: .page))
                        .placed(CGRect(153, 116, 86.7, 27))
                }
            }
            .frame(width: 393, height: 170, alignment: .topLeading)
            .scaleEffect(k, anchor: .topLeading)
            .allowsHitTesting(false)
            PageInfoButton(action: openInfo).placed(m.rect(CGRect(5.3, 50.0, 40, 40), .top))
            PopupCloseButton(id: fall == nil ? "event.balloon.close" : "popup.balloonFall.close", t: t, halo: true) { close() }
                .placed(m.rect(CGRect(332.8, 49.6, 45, 45), .top))
            if fall == nil, ended == nil { ComingNextFooter() }
            WeekStartBanner(event: .balloonRise)
            SocReadyWhen(ready: true, name: fall == nil ? "event:balloonRise" : "popup:balloonFall")
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(fall == nil ? "page.balloon" : "page.balloonFall")
        .accessibilityValue(Text(verbatim: b?.accessibilityValue ?? "0"))
        .onAppear { appeared(status: status, shown: b, ended: ended != nil, target: target) }
    }

    // MARK: motion

    private var animationDone: Bool { !animating }

    /// The balloon's count at `date`: a rise from the last shown count (+0.09 s, 1.1 s ease-in-out) or the fall to 0 (0.95 s
    /// ease-in-out from the first frame).
    private func count(at date: Date, target: Double) -> Double {
        guard let s = shownAt, let f = from, f != target else { return target }
        let u = app.clock.gameTime(date) - s
        let (delay, dur) = fall != nil ? (0.0, 0.95) : (0.09, 1.1)
        let x = min(1, max(0, (u - delay) / dur))
        return f + (target - f) * Self.easeInOut(x)
    }

    /// The green fill: with the balloon while rising; drains in 0.75 s on the fall page.
    private func fillCount(at date: Date, target: Double) -> Double {
        guard fall != nil, let s = shownAt, let f = from else { return count(at: date, target: target) }
        let x = min(1, max(0, (app.clock.gameTime(date) - s) / 0.75))
        return f * (1 - Self.easeInOut(x))
    }

    static func easeInOut(_ x: Double) -> Double { x < 0.5 ? 2 * x * x : 1 - pow(-2 * x + 2, 2) / 2 }

    private func scroll(_ proxy: ScrollViewProxy, geo: BalloonTrackGeometry, target: Double) {
        // it opens at the tower's foot (VERIFIED at low counts); a higher balloon is centred
        let start = max(target, from ?? target)
        if start < 5 { proxy.scrollTo("balloon.ground", anchor: .bottom) } else { proxy.scrollTo("balloon.now", anchor: .center) }
    }

    private func appeared(status: Events.Status, shown: Events.BalloonStatus?, ended: Bool, target: Double) {
        guard !prewarm else { return }
        let week = status.week?.week ?? 0
        if let f = fall {
            from = Double(f)
        } else if !ended, let last = BalloonShown.last(app, week: week), Double(last) < target {
            from = Double(last)
        } else {
            from = target
        }
        shownAt = app.clock.gameTime()
        if from != target {
            animating = true
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: 1_450_000_000)
                animating = false
            }
        }
        if fall == nil, !ended { BalloonShown.record(app, week: week, count: Int(target)) }
        // the opening bubble: the goal chest while it is unpaid, else "Already collected!" over the last paid one
        if let b = shown {
            if let g = b.goal, let i = b.platforms.firstIndex(of: g), i >= b.paid { bubble = i } else if b.paid > 0 { bubble = b.paid - 1 }
        }
        if ended {
            held = shown                                                       // B1b: the result is opened: the hold goes
            EventFinish.open(app, .balloonRise)
        } else {
            EventAnnounce.opened(app, .balloonRise)
        }
        Log.mark("event", "balloonRise \(fall == nil ? "page" : "fall page from \(fall!)") visible (\(shown?.accessibilityValue ?? "not live")\(ended ? ", the ended week" : ""))")
        if fall == nil { SocialModel.install(app).probeOpen("balloonRise") }
        if fall == nil, !ended, !app.store.state.flags.seen.contains("balloonIntro") {
            // the first open ever: the (i) explains the rules (the first-open intro, like the Treasure Climb's auto-scroll)
            app.store.mutateAndSave { _ = $0.flags.seen.insert("balloonIntro") }
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: 400_000_000)
                openInfo()
            }
        }
    }

    private func openInfo() {
        Task { @MainActor in
            _ = await app.popups.present(Popup<PopupResult>(.custom(id: "balloonInfo", params: [:]),
                                                            style: PopupStyle(dim: .unlock, closesOnTapAnywhere: true), fallback: .close))
        }
    }

    private func close() {
        if let answer { answer(PopupResult.close) } else { EventPageShell<EmptyView>.close(app) }
    }
}

/// The sky behind the tower (code gradient; the tower pieces go over it). A4: R8's D1 stops — deep teal night at the top, sea
/// teal, a mint band, a warm dawn at the foot (was B1's navy → violet → pink).
private struct BalloonSky: View {
    var body: some View {
        LinearGradient(stops: [.init(color: Color(hex: Skin.socialBalloonViewsBalloonSkyStops0), location: 0), .init(color: Color(hex: Skin.socialBalloonViewsBalloonSkyStops1), location: 0.40),
                               .init(color: Color(hex: Skin.socialBalloonViewsBalloonSkyStops2), location: 0.66), .init(color: Color(hex: Skin.socialBalloonViewsBalloonSkyStops3), location: 0.84),
                               .init(color: Color(hex: Skin.socialBalloonViewsBalloonSkyStops4), location: 1)],
                       startPoint: .top, endPoint: .bottom)
    }
}

/// A4: R8's tower pieces, back → front: the clouds, the shaft tiles (every 340 pt from y 470 while above the foot; drawn under
/// the top and the foot, which overlap the first and last tile — the masonry is one periodic paint, so every join is seamless),
/// the top at y 0, the foot at the bottom (its ground line at local 450 = `groundY`).
private struct BalloonTowerArt: View {
    let height: CGFloat

    static let topHeight: CGFloat = 470
    static let footHeight: CGFloat = 700
    static let tile: CGFloat = 340
    /// R8's suggested cloud spots (page pt; balloonCloudA 150 × 70, balloonCloudB 100 × 56), kept above the foot.
    static let clouds: [(UIArt, CGPoint, CGSize)] = [
        (.eventBalloonRiseCloudA, CGPoint(x: 250, y: 520), CGSize(width: 150, height: 70)),
        (.eventBalloonRiseCloudB, CGPoint(x: 290, y: 880), CGSize(width: 100, height: 56)),
        (.eventBalloonRiseCloudA, CGPoint(x: 240, y: 1250), CGSize(width: 150, height: 70)),
        (.eventBalloonRiseCloudB, CGPoint(x: 284, y: 1600), CGSize(width: 100, height: 56)),
        (.eventBalloonRiseCloudA, CGPoint(x: 262, y: 1930), CGSize(width: 150, height: 70)),
        (.eventBalloonRiseCloudB, CGPoint(x: 296, y: 2280), CGSize(width: 100, height: 56)),
        (.eventBalloonRiseCloudA, CGPoint(x: 236, y: 2620), CGSize(width: 150, height: 70)),
    ]

    var body: some View {
        let footY = height - Self.footHeight
        let tiles = Array(stride(from: Self.topHeight, to: footY, by: Self.tile))
        ZStack(alignment: .topLeading) {
            ForEach(Array(Self.clouds.enumerated()), id: \.offset) { _, c in
                if c.1.y + c.2.height < footY { ArtImage(art: c.0).placed(CGRect(origin: c.1, size: c.2)) }
            }
            ForEach(tiles, id: \.self) { y in
                UpAwayArtImage(id: UpAwayArt.towerShaft).placed(CGRect(0, y, 112, Self.tile))
            }
            UpAwayArtImage(id: UpAwayArt.towerTop).placed(CGRect(0, 0, 393, Self.topHeight))
            UpAwayArtImage(id: UpAwayArt.towerFoot).placed(CGRect(0, footY, 393, Self.footHeight))
        }
        .frame(width: 393, height: height, alignment: .topLeading)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

/// The tall content: backdrop, track, milestones, ledges + chests, the balloon.
private struct BalloonTower: View {
    let geo: BalloonTrackGeometry
    let count: Double
    let fill: Double
    let paid: Int
    let rewards: [Grant]
    let bubble: Int?
    /// FIX-2 B (R8-o4): the balloon's idle drift (off in capture mode and in the prewarm copy).
    var drift = true
    let onChest: (Int) -> Void

    var body: some View {
        let trackX: CGFloat = 34, trackW: CGFloat = 16
        let topY = geo.y(platform: geo.platforms.count - 1) - 40
        let fillTop = geo.y(count: fill)
        let balloonY = geo.y(count: count)
        ZStack(alignment: .topLeading) {
            BalloonSky().frame(width: 393, height: geo.height)
            // A4: R8's tower pieces (the foot carries the landing pad and the walkway: B1's two pad capsules are gone)
            BalloonTowerArt(height: geo.height)
            Color.clear.frame(width: 1, height: 1).position(x: 196, y: geo.groundY + 200).id("balloon.ground")
            // the track: dark rail, green fill to the count
            RoundedRectangle(cornerRadius: trackW / 2).fill(Color(hex: Skin.socialBalloonViewsBalloonTowerFill))
                .frame(width: trackW + 6, height: geo.groundY - topY + 6).position(x: trackX, y: (geo.groundY + topY) / 2)
            RoundedRectangle(cornerRadius: trackW / 2)
                .fill(LinearGradient(colors: [Color(hex: Skin.socialBalloonViewsBalloonTowerColors0), Color(hex: Skin.socialBalloonViewsBalloonTowerColors1)], startPoint: .leading, endPoint: .trailing))
                .frame(width: trackW, height: max(0, geo.groundY - fillTop)).position(x: trackX, y: (geo.groundY + fillTop) / 2)
            // the ledges (platform i), their signs and chests
            ForEach(Array(geo.platforms.enumerated()), id: \.offset) { i, at in
                // A4: R8's ledge art is 240 × 150 with its frame's top-left at (60, y − 94), as B1's 240 × 120 box was
                let o = BalloonLayout.ledgeOrigin(geo, i)
                BalloonLedge(step: i + 1, paid: i < paid, chest: BalloonChest.art(i), onChest: { onChest(i) })
                    .frame(width: 240, height: 150, alignment: .topLeading)
                    .position(x: o.x + 120, y: o.y + 75)
                BalloonMilestone(count: at, passed: fill >= Double(at) - 0.001)
                    .position(x: trackX, y: geo.y(platform: i))
            }
            BalloonMilestone(count: 0, passed: true).position(x: trackX, y: geo.groundY)
            BalloonCounterBadge(count: Int(count.rounded())).position(x: trackX + 30, y: fillTop)
            // the balloon (its basket rests on the count's height; A4: R8's hero frame is 150 × 220, was 150 × 190); FIX-2 B:
            // v582's idle drift on the render server
            let hero = BalloonLayout.heroFrame(geo, count: count)
            DriftingHero(image: UpAwayArt.art(UpAwayArt.hero).flatMap { ArtStore.image($0) }, drift: drift)
                .frame(width: hero.width, height: hero.height).position(x: hero.midX, y: hero.midY)
                .accessibilityElement()
                .accessibilityIdentifier("balloon.hero")
                .accessibilityValue(Text(verbatim: "\(Int(count.rounded()))"))
            Color.clear.frame(width: 1, height: 1).position(x: 285, y: balloonY - 110).id("balloon.now")
            if let i = bubble, i < geo.platforms.count {
                BalloonBubble(reward: i < paid ? nil : rewards[safe: i])
                    .position(BalloonLayout.bubbleCentre(geo, i))
                    .transition(.scale(scale: 0.6, anchor: .bottom))
            }
        }
        .frame(width: 393, height: geo.height, alignment: .topLeading)
    }
}

private struct BalloonLedge: View {
    let step: Int
    let paid: Bool
    let chest: UIArt
    let onChest: () -> Void

    var body: some View {
        let sign = GameTextStyle.s2(15, -0.3, [Skin.socialBalloonViewsBalloonLedgeSign0], outline: Skin.socialBalloonViewsBalloonLedgeSignOutline, 1.1, drop: 0.8)
        ZStack(alignment: .topLeading) {
            // A4: R8's timber ledge with its hanging teal board (was B1's code-drawn purple bar, blue sign and posts); the live
            // "Step N" sits on the board (local 34…118 × 112…140), the chest box is B1's
            UpAwayArtImage(id: UpAwayArt.ledge).frame(width: 240, height: 150)
            GameText("Step \(step)", style: sign, maxWidth: 76).position(x: 76, y: sign.capCentre(baseline: 131))
            // the chest with its (i) (tap → the reward bubble), a check once paid
            GameButton(id: "balloon.chest.\(step)", label: "Info", value: paid ? "paid" : "unpaid", action: onChest) {
                ZStack {
                    ArtImage(art: chest)
                    if paid { ArtImage(art: .iconCheck).frame(width: 34, height: 30).offset(x: 20, y: 18) }
                }
            }
            .frame(width: BalloonLayout.chestBox.width, height: BalloonLayout.chestBox.height)
            .offset(x: BalloonLayout.chestBox.minX, y: BalloonLayout.chestBox.minY)   // FIX-2 B (R8-o3): left of the balloon
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("balloon.platform.\(step)")
        .accessibilityValue(Text(verbatim: paid ? "paid" : "unpaid"))
    }
}

/// A milestone cloud on the track (lavender; green once passed) with its count.
private struct BalloonMilestone: View {
    let count: Int
    let passed: Bool
    var body: some View {
        let st = GameTextStyle.s2(count >= 100 ? 14 : 17, -0.5, [Skin.socialBalloonViewsBalloonMilestoneSt0], outline: passed ? Skin.socialBalloonViewsBalloonMilestoneStOutlinePassed : Skin.socialBalloonViewsBalloonMilestoneStOutlineNotPassed, 1.2, drop: 0.8)
        ZStack {
            BalloonCloudShape().fill(Color(hex: passed ? Skin.socialBalloonViewsBalloonMilestoneFillPassed : Skin.socialBalloonViewsBalloonMilestoneFillNotPassed)).frame(width: 52, height: 38).offset(y: 1.5)
            BalloonCloudShape().fill(LinearGradient(colors: passed ? [Color(hex: Skin.socialBalloonViewsBalloonMilestoneColorsPassed0), Color(hex: Skin.socialBalloonViewsBalloonMilestoneColorsPassed1)]
                                                                   : [Color(hex: Skin.socialBalloonViewsBalloonMilestoneColorsNotPassed0), Color(hex: Skin.socialBalloonViewsBalloonMilestoneColorsNotPassed1)],
                                                    startPoint: .top, endPoint: .bottom))
                .frame(width: 50, height: 36)
            GameText(verbatim: "\(count)", style: st, maxWidth: 44).position(x: 26, y: st.capCentre(baseline: 25))
        }
        .frame(width: 52, height: 38)
    }
}

/// Three bumps over a flat base.
struct BalloonCloudShape: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        let h = r.height, w = r.width
        p.addEllipse(in: CGRect(x: r.minX, y: r.minY + h * 0.30, width: w * 0.46, height: h * 0.66))
        p.addEllipse(in: CGRect(x: r.minX + w * 0.22, y: r.minY, width: w * 0.56, height: h * 0.80))
        p.addEllipse(in: CGRect(x: r.minX + w * 0.54, y: r.minY + h * 0.26, width: w * 0.46, height: h * 0.70))
        p.addRoundedRect(in: CGRect(x: r.minX + w * 0.12, y: r.minY + h * 0.52, width: w * 0.76, height: h * 0.46),
                         cornerSize: CGSize(width: h * 0.2, height: h * 0.2))
        return p
    }
}

/// The yellow counter badge riding the fill (the count, an up arrow).
private struct BalloonCounterBadge: View {
    let count: Int
    var body: some View {
        let st = GameTextStyle.s2(17, -0.5, [Skin.socialBalloonViewsBalloonCounterBadgeSt0], outline: Skin.socialBalloonViewsBalloonCounterBadgeStOutline, 1.3, drop: 0.8)
        ZStack {
            RoundedRectangle(cornerRadius: 9).fill(Color(hex: Skin.socialBalloonViewsBalloonCounterBadgeFill)).frame(width: 42, height: 30).offset(y: 1.5)
            RoundedRectangle(cornerRadius: 8).fill(LinearGradient(colors: [Color(hex: Skin.socialBalloonViewsBalloonCounterBadgeColors0), Color(hex: Skin.socialBalloonViewsBalloonCounterBadgeColors1)],
                                                                   startPoint: .top, endPoint: .bottom)).frame(width: 40, height: 28)
            GameText(verbatim: "\(count)", style: st, maxWidth: 34).position(x: 21, y: st.capCentre(baseline: 20))
        }
        .frame(width: 42, height: 30)
        .accessibilityElement()
        .accessibilityIdentifier("balloon.streak")
        .accessibilityValue(Text(verbatim: "\(count)"))
    }
}

/// The speech bubble over a chest: its reward, or "Already collected!".
private struct BalloonBubble: View {
    let reward: Grant?
    var body: some View {
        let st = GameTextStyle.s2(15, -0.3, [Skin.socialBalloonViewsBalloonBubbleSt0])
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 14).fill(Color(hex: Skin.socialBalloonViewsBalloonBubbleFill)).frame(width: 150, height: 66).offset(y: 2)
            RoundedRectangle(cornerRadius: 14).fill(Color(hex: Skin.socialBalloonViewsBalloonBubbleFillV2)).frame(width: 150, height: 66)
            Path { p in p.move(to: CGPoint(x: 64, y: 64)); p.addLine(to: CGPoint(x: 86, y: 64)); p.addLine(to: CGPoint(x: 75, y: 80)) }
                .fill(Color(hex: Skin.socialBalloonViewsBalloonBubbleFillV2))
            if let reward {
                BalloonRewardRow(grant: reward).frame(width: 140, height: 56).offset(x: 5, y: 5)
            } else {
                GameText("Already collected!", style: st, maxWidth: 136).position(x: 75, y: st.capCentre(baseline: 39))
            }
        }
        .frame(width: 150, height: 82, alignment: .topLeading)
        .accessibilityElement()
        .accessibilityIdentifier("balloon.bubble")
        .accessibilityValue(Text(verbatim: reward.map { "\($0)" } ?? "claimed"))
    }
}

/// A reward's parts side by side (coins, ∞, boosters) — the Treasure Climb's icon for each.
private struct BalloonRewardRow: View {
    let grant: Grant
    var body: some View {
        let parts = BalloonRewardRow.parts(grant)
        HStack(spacing: 2) {
            ForEach(Array(parts.enumerated()), id: \.offset) { _, g in SocRewardIcon(grant: g).frame(width: 46, height: 46) }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    static func parts(_ g: Grant) -> [Grant] {
        var out: [Grant] = []
        if g.coins > 0 { out.append(.coins(g.coins)) }
        if g.unlimitedLives > 0 { out.append(Grant(unlimitedLives: g.unlimitedLives)) }
        for (k, v) in g.boosters.sorted(by: { $0.key < $1.key }) where v > 0 { out.append(Grant(boosters: [k: v])) }
        return out
    }
}

fileprivate extension Array {
    subscript(safe i: Int) -> Element? { indices.contains(i) ? self[i] : nil }
}

// MARK: - the (i)

/// Up & Away's (i) (dim 0.90): the path icon + "Beat levels in a row to rise higher!", the balloon + "Every stop has a
/// reward!", the coins + "Reach the top for the big prize!", the red card "If you fail a level, you fall back to the ground!",
/// "Tap to Continue". Our copy (the rules are the original's; its words are not).
struct SocBalloonInfo: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 1.4 } ?? true)) { ctx in
            let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            ZStack(alignment: .topLeading) {
                Color.clear
                SocPopIn(u: u, start: 0.18, duration: 0.10, overshoot: 1.10, at: CGPoint(x: 196.8, y: 82.9 - 13)) {
                    SocInfoTitle(title: "Up & Away", baseline: 82.9)
                }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 110, y: 190)) { ArtImage(art: .iconInfo).placed(CGRect(57.4, 138.8, 105.8, 105.4)) }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 111.7, y: 264)) {
                    SocTwoLines(text: "Beat levels in a row to rise higher!", centreX: 111.7, baselines: [270.5, 290.5], box: 170, greedy: true)
                }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 254, y: 258)) { ArtImage(art: .iconPointer).placed(CGRect(234, 236, 40, 45)) }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 280, y: 350)) {
                    UpAwayArtImage(id: UpAwayArt.hero).placed(CGRect(236, 300, 90, 110))
                }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 262.7, y: 438)) {
                    SocTwoLines(text: "Every stop has a reward!", centreX: 262.7, baselines: [438.5, 458.5], box: 170, greedy: true)
                }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 254, y: 510)) {
                    ArtImage(art: .iconPointer).scaleEffect(x: -1, y: 1).placed(CGRect(234, 488, 40, 45))
                }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 127, y: 554)) { ArtImage(art: .rewardCoinsSmall).placed(CGRect(89.7, 523.4, 75.4, 62)) }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 127, y: 608)) {
                    SocTwoLines(text: "Reach the top for the big prize!", centreX: 127, baselines: [608, 628], box: 200, hot: "big prize",
                                greedy: true)
                }
                SocPopIn(u: u, start: 1.0, at: CGPoint(x: 196, y: 688)) {
                    SocWarningCard(text: "If you fail a level, you fall back to the ground!", frame: CGRect(36, 654, 321, 68))
                }
                if u >= 1.10 { SocTapTo(text: "Tap to Continue", baseline: 793.4).opacity(min(1, (u - 1.10) / 0.15)) }
            }
            .frame(width: 393, height: 852)
        }
        .contentShape(Rectangle())
        .onTapGesture { answer(PopupResult.close) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("balloon.info.overlay")
        .onAppear { shownAt = app.clock.gameTime() }
    }
}

// MARK: - the win-panel strip

/// What the win panel's Up & Away strip shows (nil = the event is not live / the win did not count for it).
struct BalloonStripData: Equatable {
    var from: Int
    var to: Int
    var platforms: [Int]
    var paid: Int
    var timeLeft: String
    /// FIX-2 B (review of L28): the week's end — the strip's time ticks (the win panel can stay up for minutes).
    var ends: SocialTime? = nil
}

@MainActor enum BalloonStripSource {
    /// From the win's outcomes (`.balloonStreak`): the strip replaces the Hot Streak strip while Up & Away runs.
    static func data(_ app: AppModel, outcomes: [EventOutcome]) -> BalloonStripData? {
        guard let total = outcomes.compactMap({ o -> Int? in if case .balloonStreak(_, let t, _) = o { return t }; return nil }).last
        else { return nil }
        let rules = ShellEconomy.rules(app)
        let st = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
        let now = SocTime.now(app)
        return BalloonStripData(from: max(0, total - 1), to: total, platforms: rules.events.balloonRise.platforms.map(\.at),
                                paid: st.balloon?.paid ?? 0,
                                timeLeft: Countdown.text(SocTime.left(st.balloon?.endsAt ?? now, now: now)), ends: st.balloon?.endsAt)
    }
}

/// The strip under the win panel (the Hot Streak strip's band place 0 · 700.6 · 393 · 152.1 on the panel's canvas, our
/// lettering, the week's countdown, the track). It rises with the Hot Streak strip's beats (ui.json win.stripAt / stripDur).
struct BalloonStrip: View {
    let data: BalloonStripData
    let shownAt: Double?
    @Environment(AppModel.self) private var app

    static let step: CGFloat = 39
    static let slideStart = 0.18
    static let slideDuration = 0.77

    var body: some View {
        let f = app.tuning.ui.file
        let riseAt = f.double("win.stripAt", 3.95) - f.double("win.panelAt", 3.94)
        let riseDur = f.double("win.stripDur", 0.13)
        TimelineView(.animation(minimumInterval: nil, paused: shownAt == nil)) { ctx in
            let u = shownAt.map { app.clock.sequenceTime("strip", app.clock.gameTime(ctx.date) - $0) } ?? 99
            let rise = Easing.outCubic((u - riseAt) / riseDur)
            let x = min(1, max(0, (u - Self.slideStart) / Self.slideDuration))
            let pos = Double(data.from) + Double(data.to - data.from) * SocBalloonPage.easeInOut(x)
            BalloonStripBody(data: data, position: pos)
                .frame(width: 393, height: 152.1, alignment: .topLeading)
                .placed(CGRect(0, 700.6, 393, 152.1))
                .offset(y: CGFloat((1 - rise) * f.double("win.stripRise", 152)))
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("win.balloonStrip")
        .accessibilityValue(Text(verbatim: "\(data.from)>\(data.to)"))
    }
}

private struct BalloonStripBody: View {
    let data: BalloonStripData
    /// The balloon's count (fractional while it slides).
    let position: Double
    @Environment(AppModel.self) private var app

    var body: some View {
        let step = BalloonStrip.step
        let track = CGRect(0, 72, 393, 60)
        // the window keeps the balloon at 1/3 of the width; milestones outside it are clipped
        let origin = 130 - CGFloat(position) * step
        let chip = GameTextStyle.s2(12.2, -1.38, [Skin.socialBalloonViewsBalloonStripBodyChip0])
        ZStack(alignment: .topLeading) {
            LinearGradient(colors: [Color(hex: Skin.socialBalloonViewsBalloonStripBodyColors0), Color(hex: Skin.socialBalloonViewsBalloonStripBodyColors1)], startPoint: .top, endPoint: .bottom)
                .frame(width: 393, height: 152.1).offset(y: 12)
            SocRails().frame(width: 393, height: 14).offset(y: 6)
            SocEventLogo(title: "Up & Away", frame: CGRect(78.4, -12.7, 233.5, 53.4), size: 34)
            RoundedRectangle(cornerRadius: 12).fill(Color(hex: Skin.socialBalloonViewsBalloonStripBodyFill)).frame(width: 76.7, height: 28).offset(x: 313.6, y: 6.7)
            Group {                                                          // FIX-2 B review (L28): ticks on its own
                if let end = data.ends {
                    LiveCountdown(ends: end, now: SocTime.now(app), clock: .page) { s in
                        GlyphRunText(text: Countdown.text(s), style: chip, maxWidth: 62)
                    }
                } else {
                    GlyphRunText(text: data.timeLeft, style: chip, maxWidth: 62)
                }
            }
            .position(x: 356, y: chip.capCentre(baseline: 25))
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 9).fill(Color(hex: Skin.socialBalloonViewsBalloonStripBodyFillV2)).frame(width: 2000, height: 18).offset(x: origin - 20, y: 30)
                RoundedRectangle(cornerRadius: 8)
                    .fill(LinearGradient(colors: [Color(hex: Skin.socialBalloonViewsBalloonStripBodyColors0V2), Color(hex: Skin.socialBalloonViewsBalloonStripBodyColors1V2)], startPoint: .top, endPoint: .bottom))
                    .frame(width: max(0, CGFloat(position) * step + 10), height: 14).offset(x: origin - 5, y: 32)
                BalloonMilestoneSmall(count: 0, passed: true).position(x: origin, y: 39)
                ForEach(Array(data.platforms.enumerated()), id: \.offset) { i, at in
                    let x = origin + CGFloat(at) * step
                    if x > -40 && x < 440 {
                        ArtImage(art: BalloonChest.art(i)).frame(width: 34, height: 30).position(x: x, y: 6)
                        if i < data.paid { ArtImage(art: .iconCheck).frame(width: 18, height: 16).position(x: x + 12, y: 12) }
                        BalloonMilestoneSmall(count: at, passed: position >= Double(at) - 0.001).position(x: x, y: 39)
                    }
                }
                UpAwayArtImage(id: UpAwayArt.hero).frame(width: 44, height: 56).position(x: 130, y: 6)
            }
            .frame(width: track.width, height: track.height, alignment: .topLeading)
            .clipped()
            .offset(y: track.minY)
        }
        .frame(width: 393, height: 152.1, alignment: .topLeading)
    }
}

private struct BalloonMilestoneSmall: View {
    let count: Int
    let passed: Bool
    var body: some View {
        let st = GameTextStyle.s2(12, -0.4, [Skin.socialBalloonViewsBalloonMilestoneSmallSt0], outline: passed ? Skin.socialBalloonViewsBalloonMilestoneSmallStOutlinePassed : Skin.socialBalloonViewsBalloonMilestoneSmallStOutlineNotPassed, 1.0, drop: 0.6)
        ZStack {
            BalloonCloudShape().fill(LinearGradient(colors: passed ? [Color(hex: Skin.socialBalloonViewsBalloonMilestoneSmallColorsPassed0), Color(hex: Skin.socialBalloonViewsBalloonMilestoneSmallColorsPassed1)]
                                                                   : [Color(hex: Skin.socialBalloonViewsBalloonMilestoneSmallColorsNotPassed0), Color(hex: Skin.socialBalloonViewsBalloonMilestoneSmallColorsNotPassed1)],
                                                    startPoint: .top, endPoint: .bottom))
                .frame(width: 36, height: 26)
            GameText(verbatim: "\(count)", style: st, maxWidth: 30).position(x: 18, y: st.capCentre(baseline: 18))
        }
        .frame(width: 36, height: 26)
    }
}
