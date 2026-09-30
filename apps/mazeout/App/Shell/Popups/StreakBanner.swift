import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.7.3, §1.6.16; uim `streakRace.*`, `continueStreak.chips`; VERIFIED 014/016/020/037/196/meta-072;
// SPEC-motion-audio §5 rows 16-18). The Streak Race strip under the win and fail panels, and the cream chip row it shares with
// Continue? (streak):
//   band        0 · 700.6 · 393 · 152.1 (bottom): a rail (light bumper + rivet on the left, blue middle) over the field #2A60EF
//   lettering   78.4 · 687.9 · 233.5 · 53.4: "Streak Race" in PCDisplay-BlackItalic, yellow "Streak" + white "Race", blue outline,
//               a chequered flag each side (`iconCheckeredFlag`) — our lettering drawn in code (MANIFEST `streakRaceLogo` is a
//               route-B1 code component)
//   timer chip  313.6 · 707.3 · 76.7 · 28, "9h 16m" 12.2 / −1.38 #622200 (to the event's end), the small stopwatch on its left
//   chips       8 · 762 · 371.6 · 64.4: x1 … x100 27.2 pt #622200 plain, 1 pt dividers; the lit chip green (#6AFC3F → #00B000)
//               in a gold ring #FFC400, its label #FFFBE6 outlined #015100
// Motion (anchor = the panel's first frame P): the strip slides up +152 → 0 at P + 0.01 over 0.13 s (easeOutCubic) with the
// PREVIOUS multiplier lit; at P + 0.40 the lit chip moves to the new one over 0.31 s (easeInOut); at P + 0.71 its ring pops
// 0.6 → 1.0 (0.15 s, easeOutBack). On Level Failed the lit chip moves back to x1. A TimelineView runs only for that second.
// The views are `StreakStrip` / `StreakChipRow` / `StreakRaceLettering` (GlossyChrome reserves `StreakBanner`, `StreakChips`).

/// The cream chip row (x1 … x100) with one lit chip. `lit` is a fractional chip index (a move in progress), `ring` the gold
/// ring's scale (nil = no ring while the lit chip moves).
struct StreakChipRow: View {
    let steps: [Int]
    let lit: Double
    let ring: Double?
    let frame: CGRect
    let t: Tokens
    /// Continue? draws the row on the cream strip (a tan rim, VERIFIED 014); the Streak Race band on blue (a navy rim, 016).
    var onCream = false

    /// The label centres on 016 / 020 (x1 51.5, x5 120.8, x10 195.3, x25 269.6, x100 340.5 at a 371.6 pt row from x 8).
    static let centres: [CGFloat] = [51.5, 120.8, 195.3, 269.6, 340.5]

    var body: some View {
        let k = frame.width / 371.6
        let cx = t.list("streakRace.chipCentres", Self.centres.map(Double.init)).map { CGFloat($0) }
        let xs = cx.map { ($0 - 8) * k }
        let litX = interpolate(xs, lit)
        let plain = t.text("streakRace.chips.plain", .s2(27.2, -1.7, [Skin.popupsStreakBannerStreakRaceChipsPlain0])).sized(27.2 * k)
        let lightStyle = t.text("streakRace.chips.lit", .s2(30.8, -2.9, [Skin.popupsStreakBannerStreakRaceChipsLit0], outline: Skin.popupsStreakBannerStreakRaceChipsLitOutline, 1.7, drop: 1.6)).sized(30.8 * k)
        let litIndex = Int(lit.rounded())
        let base = frame.height * 41.3 / 64.4
        ZStack(alignment: .topLeading) {
            Rasterized("streakRow|\(onCream)", overflow: 3) { _ in StripTrack(t: t, onCream: onCream) }
                .frame(width: frame.width, height: frame.height)
            ForEach(1..<xs.count, id: \.self) { i in
                if abs(lit - Double(i)) > 0.6 && abs(lit - Double(i - 1)) > 0.6 {
                    t.color("streakRace.divider", Skin.popupsStreakBannerStreakRaceDivider).frame(width: 1.2, height: frame.height - 12)
                        .position(x: (xs[i - 1] + xs[i]) / 2, y: frame.height / 2)
                }
            }
            ForEach(0..<min(steps.count, xs.count), id: \.self) { i in
                if i != litIndex || abs(lit - Double(litIndex)) > 0.01 {
                    GameText(verbatim: "x\(steps[i])", style: plain, maxWidth: 70 * k).at(xs[i], plain.capCentre(baseline: base))
                }
            }
            LitChip(t: t, ring: ring)
                .frame(width: 83.4 * k, height: 63.1 * k)
                .position(x: litX, y: frame.height / 2)
            if litIndex < steps.count {
                GameText(verbatim: "x\(steps[litIndex])", style: lightStyle, maxWidth: 70 * k)
                    .at(litX, lightStyle.capCentre(baseline: base + 0.6 * k))
            }
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("streak.chips")
        .accessibilityValue(Text(verbatim: "x\(steps[max(0, min(steps.count - 1, litIndex))])"))
    }

    private func interpolate(_ xs: [CGFloat], _ f: Double) -> CGFloat {
        guard !xs.isEmpty else { return 0 }
        let i = max(0, min(Double(xs.count - 1), f))
        let a = Int(i.rounded(.down)), b = min(xs.count - 1, a + 1)
        return xs[a] + (xs[b] - xs[a]) * CGFloat(i - Double(a))
    }
}

/// The cream track: a brown rim, the face #F8E7D2, a lower bevel. On the blue band (VERIFIED 020 at x 22 / y 795) the track
/// is a cyan hairline, a navy rim ~3.4 pt, a tan bevel (2 pt at the sides, 5 pt at the bottom) and the cream face; its box is
/// 8.4 … 383.0 · 763.7 … 823.4, i.e. the token frame moved 0.4 / 1.7 in and 3.4 out on the right, 3.0 up at the bottom.
private struct StripTrack: View {
    let t: Tokens
    var onCream = false
    var body: some View {
        GeometryReader { geo in
            let r = min(geo.size.height * 0.26, 16.5)
            if onCream {
                ZStack {
                    RoundedRectangle(cornerRadius: r, style: .continuous).fill(t.color("continueStreak.trackRim", Skin.popupsStreakBannerContinueStreakTrackRim))
                    RoundedRectangle(cornerRadius: r - 1, style: .continuous)
                        .fill(LinearGradient(colors: [Color(hex: Skin.popupsStreakBannerStripTrackColors0), Color(hex: Skin.popupsStreakBannerStripTrackColors1)], startPoint: .top, endPoint: .bottom))
                        .padding(1.4)
                    RoundedRectangle(cornerRadius: r - 3, style: .continuous)
                        .fill(LinearGradient(stops: [.init(color: t.color("streakRace.track", Skin.popupsStreakBannerStreakRaceTrack), location: 0),
                                                     .init(color: t.color("streakRace.track", Skin.popupsStreakBannerStreakRaceTrack), location: 0.86),
                                                     .init(color: Color(hex: Skin.popupsStreakBannerStripTrackStops2), location: 1)], startPoint: .top, endPoint: .bottom))
                        .padding(EdgeInsets(top: 3.2, leading: 3, bottom: 4.2, trailing: 3))
                }
            } else {
                let rr = r - 2
                ZStack {
                    RoundedRectangle(cornerRadius: rr, style: .continuous).fill(t.color("streakRace.trackLine", Skin.popupsStreakBannerStreakRaceTrackLine))
                    RoundedRectangle(cornerRadius: rr - 0.7, style: .continuous)
                        .fill(LinearGradient(colors: t.colors("streakRace.trackRim", [Skin.popupsStreakBannerStreakRaceTrackRim0, Skin.popupsStreakBannerStreakRaceTrackRim1, Skin.popupsStreakBannerStreakRaceTrackRim2, Skin.popupsStreakBannerStreakRaceTrackRim3]),
                                             startPoint: .top, endPoint: .bottom))
                        .padding(0.7)
                    RoundedRectangle(cornerRadius: rr - 4.5, style: .continuous)
                        .fill(LinearGradient(stops: t.stops("streakRace.trackBevel", [(0, Skin.popupsStreakBannerStreakRaceTrackBevel0), (0.5, Skin.popupsStreakBannerStreakRaceTrackBevel1), (0.84, Skin.popupsStreakBannerStreakRaceTrackBevel2),
                                                                                         (0.93, Skin.popupsStreakBannerStreakRaceTrackBevel3), (1, Skin.popupsStreakBannerStreakRaceTrackBevel4)]),
                                             startPoint: .top, endPoint: .bottom))
                        .padding(EdgeInsets(top: 5.0, leading: 4.9, bottom: 3.7, trailing: 4.3))
                    RoundedRectangle(cornerRadius: rr - 7, style: .continuous).fill(t.color("streakRace.track", Skin.popupsStreakBannerStreakRaceTrack))
                        .overlay(RoundedRectangle(cornerRadius: rr - 7, style: .continuous)
                            .strokeBorder(Color(hex: Skin.popupsStreakBannerStripTrackStrokeBorder).opacity(0.85), lineWidth: 0.9))
                        .padding(EdgeInsets(top: 6.3, leading: 7.6, bottom: 8.7, trailing: 7.7))
                }
                .padding(EdgeInsets(top: 1.7, leading: 0.4, bottom: 3.0, trailing: -3.4))
            }
        }
    }
}

private struct LitChip: View {
    let t: Tokens
    let ring: Double?
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            ZStack {
                if let ring {
                    // VERIFIED 014 at x 24: the orange outline, a gold ring 6 pt at the top, an orange 3D base 4 pt at the bottom
                    Rasterized("litRing2") { _ in
                        ZStack {
                            RoundedRectangle(cornerRadius: h * 0.26, style: .continuous).fill(t.color("streakRace.ringLine", Skin.popupsStreakBannerStreakRaceRingLine))
                            RoundedRectangle(cornerRadius: h * 0.24, style: .continuous)
                                .fill(LinearGradient(stops: t.stops("streakRace.ringFill", [(0, Skin.popupsStreakBannerStreakRaceRingFill0), (0.05, Skin.popupsStreakBannerStreakRaceRingFill1), (0.1, Skin.popupsStreakBannerStreakRaceRingFill2),
                                                                                             (0.5, Skin.popupsStreakBannerStreakRaceRingFill3), (0.86, Skin.popupsStreakBannerStreakRaceRingFill4), (0.9, Skin.popupsStreakBannerStreakRaceRingFill5),
                                                                                             (1, Skin.popupsStreakBannerStreakRaceRingFill6)]),
                                                     startPoint: .top, endPoint: .bottom))
                                .padding(1.2)
                        }
                    }
                    .frame(width: w, height: h)
                    .scaleEffect(CGFloat(ring))
                }
                // the face: an orange hairline, dark-green inner shading, a lime band under the top edge (VERIFIED 014)
                Rasterized("litChip2") { size in
                    let r = size.height * 0.2
                    ZStack {
                        RoundedRectangle(cornerRadius: r + 1, style: .continuous).fill(t.color("streakRace.litLine", Skin.popupsStreakBannerStreakRaceLitLine))
                        ZStack {
                            RoundedRectangle(cornerRadius: r, style: .continuous)
                                .fill(LinearGradient(stops: t.stops("streakRace.litFace", [(0, Skin.popupsStreakBannerStreakRaceLitFace0), (0.12, Skin.popupsStreakBannerStreakRaceLitFace1), (0.16, Skin.popupsStreakBannerStreakRaceLitFace2),
                                                                                            (0.3, Skin.popupsStreakBannerStreakRaceLitFace3), (0.5, Skin.popupsStreakBannerStreakRaceLitFace4), (0.6, Skin.popupsStreakBannerStreakRaceLitFace5),
                                                                                            (0.85, Skin.popupsStreakBannerStreakRaceLitFace6), (1, Skin.popupsStreakBannerStreakRaceLitFace7)]),
                                                     startPoint: .top, endPoint: .bottom))
                            RoundedRectangle(cornerRadius: r, style: .continuous)
                                .stroke(t.color("streakRace.litShade", Skin.popupsStreakBannerStreakRaceLitShade), lineWidth: 3.2).blur(radius: 1.1)
                        }
                        .clipShape(RoundedRectangle(cornerRadius: r, style: .continuous))
                        .padding(1)
                    }
                }
                .frame(width: w - 16, height: h - 16)
                .offset(y: -1)
            }
            .frame(width: w, height: h)
        }
    }
}

/// "Streak Race" lettering with a chequered flag each side (our lettering; route B1 code).
struct StreakRaceLettering: View {
    let frame: CGRect
    let t: Tokens

    var body: some View {
        let k = frame.width / 233.5
        let streak = t.text("streakRace.logoStreak", .s2(41, -2.6, [Skin.popupsStreakBannerStreakRaceLogoStreak0, Skin.popupsStreakBannerStreakRaceLogoStreak1, Skin.popupsStreakBannerStreakRaceLogoStreak2], outline: Skin.popupsStreakBannerStreakRaceLogoStreakOutline, 3.0, drop: 2.8,
                                                         face: .blackItalic)).sized(41 * k)
        let race = t.text("streakRace.logoRace", .s2(41, -2.6, [Skin.popupsStreakBannerStreakRaceLogoRace0, Skin.popupsStreakBannerStreakRaceLogoRace1, Skin.popupsStreakBannerStreakRaceLogoRace2], outline: Skin.popupsStreakBannerStreakRaceLogoRaceOutline, 3.0, drop: 2.8,
                                                     face: .blackItalic)).sized(41 * k)
        // our lettering of the event name (strings "Streak Race" / "Seri Yarışı"): the first word yellow, the rest white
        // B3: first word = LineUnits' first unit (a CJK name has no space: its first dictionary word, "連勝" + "フィーバー")
        let units = LineUnits.units(String(localized: "Hot Streak"))
        let w1 = units.first?.text ?? "Streak", w2 = LineUnits.join(units.dropFirst())
        // B3: the two words keep their 55 % / 45 % boxes (EN/TR unchanged) while the pair still fits between the flags; a
        // name whose words overflow those boxes (ja 連勝 + ラッシュ) takes ONE scale for both words over the whole width,
        // and a one-word name (de Siegesserie) the whole width — floor 0.70, FitLedger (-pc.fitLog).
        let avail = frame.width - 60 * k
        let joint = StreakRaceLettering.joint(w1, w2, streak: streak, race: race, avail: avail)
        // the old per-word boxes (EN/TR: exactly the pre-B3 drawing), or the joint scale
        let st1 = joint.map { streak.sized(streak.size * $0) } ?? streak, st2 = joint.map { race.sized(race.size * $0) } ?? race
        let box1: CGFloat? = joint == nil ? avail * 0.55 : nil, box2: CGFloat? = joint == nil ? avail * 0.45 : nil
        let a = GameTextLayout.make(w1, postScriptName: st1.postScriptName, size: st1.size, tracking: st1.tracking,
                                    maxWidth: box1, minScale: 0.7)
        let b = GameTextLayout.make(w2, postScriptName: st2.postScriptName, size: st2.size, tracking: st2.tracking,
                                    maxWidth: box2, minScale: 0.7)
        let gap = 0 * k
        let total = a.advance + gap + b.advance
        let x0 = frame.width / 2 - total / 2
        let base = frame.height * 38 / 53.4
        ZStack(alignment: .topLeading) {
            InkImage(art: .iconFinishFlag, ink: CGRect(0, 4 * k, 28 * k, 32 * k))
            ArtImage(art: .iconFinishFlag).scaleEffect(x: -1, y: 1)
                .placed(ArtInk.canvas(.iconFinishFlag, ink: CGRect(frame.width - 28 * k, 4 * k, 28 * k, 32 * k)))
            GameText(verbatim: w1, style: st1, maxWidth: box1).at(x0 + a.advance / 2, st1.capCentre(baseline: base))
            GameText(verbatim: w2, style: st2, maxWidth: box2)
                .at(x0 + a.advance + gap + b.advance / 2, st2.capCentre(baseline: base))
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("Hot Streak"))
    }

    /// B3: nil = the old per-word boxes (55 % / 45 % of `avail`, each word shrinking to its box, floor 0.70) — kept while
    /// the pair then fits `avail`; else the ONE scale for both words over `avail` (a one-word name: over `avail`), floor
    /// 0.70 (FitLedger notes a need below it).
    static func joint(_ w1: String, _ w2: String, streak: GameTextStyle, race: GameTextStyle, avail: CGFloat) -> CGFloat? {
        let a0 = GameTextLayout.make(w1, postScriptName: streak.postScriptName, size: streak.size, tracking: streak.tracking).advance
        let b0 = w2.isEmpty ? 0 : GameTextLayout.make(w2, postScriptName: race.postScriptName, size: race.size, tracking: race.tracking).advance
        func boxed(_ w: CGFloat, _ box: CGFloat) -> CGFloat { w <= box ? 1 : max(0.7, (box / w * 1000).rounded(.down) / 1000) }
        if !w2.isEmpty && a0 * boxed(a0, avail * 0.55) + b0 * boxed(b0, avail * 0.45) <= avail { return nil }
        let need = avail / max(a0 + b0, 1)
        FitLedger.note("streakLettering", text: w1 + (w2.isEmpty ? "" : " " + w2), need: need)
        return min(1, max(0.7, (need * 1000).rounded(.down) / 1000))
    }
}

/// What the strip shows: the multiplier steps, the chip lit before (from) and after (to), the time left.
struct StreakStripData: Equatable {
    var steps: [Int]
    var from: Int          // step index lit when the strip appears
    var to: Int            // step index after the win / loss
    var timeLeft: String   // "9h 16m" (already formatted)
    /// FIX-2 B (review of L28): the Hot Streak day's end — the strip's chip then ticks (the win panel can stay up for minutes).
    var ends: SocialTime? = nil
}

/// The Streak Race strip under the win / fail panel, with its entrance (SPEC-motion-audio §5 rows 16-18).
struct StreakStrip: View {
    let data: StreakStripData
    /// MotionClock game time of the panel's first frame (P); nil = at rest (captures of the settled state).
    let shownAt: Double?
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let f = app.tuning.ui.file
        let slideAt = f.double("win.stripAt", 3.95) - f.double("win.panelAt", 3.94)
        let slideDur = f.double("win.stripDur", 0.13)
        let chipAt = f.double("win.chipAt", 4.34) - f.double("win.panelAt", 3.94)
        let chipDur = f.double("win.chipDur", 0.31)
        let ringAt = f.double("win.ringAt", 4.65) - f.double("win.panelAt", 3.94)
        let ringDur = f.double("win.ringDur", 0.15)
        let end = ringAt + ringDur
        TimelineView(.animation(minimumInterval: nil, paused: shownAt == nil)) { ctx in
            let u = shownAt.map { app.clock.sequenceTime("strip", app.clock.gameTime(ctx.date) - $0) } ?? end + 1
            let slide = Easing.outCubic((u - slideAt) / slideDur)
            let move = u < chipAt ? 0 : (u >= chipAt + chipDur ? 1 : Easing.inOutQuad((u - chipAt) / chipDur))
            let lit = Double(data.from) + Double(data.to - data.from) * move
            let ring: Double? = data.from == data.to ? 1 : (u < chipAt ? 1 : (u < ringAt ? nil : 0.6 + 0.4 * Easing.outBack((u - ringAt) / ringDur)))
            StripBody(data: data, lit: lit, ring: ring, t: t)
                .offset(y: CGFloat((1 - slide) * f.double("win.stripRise", 152)))
        }
    }
}

private struct StripBody: View {
    let data: StreakStripData
    let lit: Double
    let ring: Double?
    let t: Tokens
    @Environment(AppModel.self) private var app

    var body: some View {
        let band = t.frame("streakRace.band", CGRect(0, 700.6, 393, 152.1))
        let chip = t.frame("streakRace.timerChip", CGRect(313.6, 707.3, 76.7, 28.0))
        ZStack(alignment: .topLeading) {
            Rasterized("streakBand") { _ in StripBand(t: t) }.placed(band.insetBy(dx: -40, dy: 0).offsetBy(dx: 0, dy: 0))
            StreakRaceLettering(frame: t.frame("streakRace.logo", CGRect(78.4, 687.9, 233.5, 53.4)), t: t)
            EventTimerChip(text: data.timeLeft, frame: chip, textID: "streakRace.timerChip.timer", t: t,
                           live: data.ends.map { (ends: $0, now: SocTime.now(app)) })
            StreakChipRow(steps: data.steps, lit: lit, ring: ring, frame: t.frame("streakRace.chips", CGRect(8.0, 762.0, 371.6, 64.4)), t: t)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("streak.strip")
    }
}

/// The band: a rail with a light bumper + rivet at the left end, then the blue field to the bottom of the screen.
private struct StripBand: View {
    let t: Tokens
    var body: some View {
        // VERIFIED 016 / 020 / 037 / 063 at x 4 / 30 / 70: the band's visible top is 716.9, 16.3 pt under the token frame's top
        // (the frame's 700.6 is the lettering's reach): a soft shadow, a 13.4 pt rail (a cyan bumper with a rivet on the left, a
        // blue rail after it), a 6.3 pt navy groove, then the field #0894FF → #1D71F6 (y 795) → #2A60EF at the bottom.
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let side: CGFloat = 40                        // the band is drawn 40 pt wider on each side (full-bleed phones)
            let top = CGFloat(t.number("streakRace.bandTop", 16.3)), rail: CGFloat = 13.4, groove: CGFloat = 6.3
            ZStack(alignment: .topLeading) {
                LinearGradient(colors: [.black.opacity(0), .black.opacity(0.35)], startPoint: .top, endPoint: .bottom)
                    .frame(width: w, height: 1.6).offset(y: top - 1.6)
                LinearGradient(stops: t.stops("streakRace.rail", [(0, Skin.popupsStreakBannerStreakRaceRail0), (0.12, Skin.popupsStreakBannerStreakRaceRail1), (0.6, Skin.popupsStreakBannerStreakRaceRail2), (1, Skin.popupsStreakBannerStreakRaceRail3)]),
                               startPoint: .top, endPoint: .bottom)
                    .frame(width: w, height: rail).offset(y: top)
                LinearGradient(stops: t.stops("band.bumperV", [(0, Skin.popupsStreakBannerBandBumperV0), (0.1, Skin.popupsStreakBannerBandBumperV1), (0.22, Skin.popupsStreakBannerBandBumperV2), (0.88, Skin.popupsStreakBannerBandBumperV3),
                                                                (1, Skin.popupsStreakBannerBandBumperV4)]),
                               startPoint: .top, endPoint: .bottom)
                    .frame(width: side + 51.4, height: rail).offset(y: top)
                Color(hex: Skin.popupsStreakBannerStripBand).frame(width: 1.2, height: rail).offset(x: side + 50.2, y: top)
                Circle().fill(RadialGradient(colors: [Color(hex: Skin.popupsStreakBannerStripBandColors0), Color(hex: Skin.popupsStreakBannerStripBandColors1)], center: UnitPoint(x: 0.42, y: 0.38),
                                             startRadius: 0, endRadius: 4.6))
                    .overlay(Circle().stroke(Color(hex: Skin.popupsStreakBannerStripBandStroke), lineWidth: 1.0))
                    .frame(width: 8.6, height: 8.6).position(x: side + 45.7, y: top + rail / 2)
                LinearGradient(colors: t.colors("streakRace.groove", [Skin.popupsStreakBannerStreakRaceGroove0, Skin.popupsStreakBannerStreakRaceGroove1, Skin.popupsStreakBannerStreakRaceGroove2, Skin.popupsStreakBannerStreakRaceGroove3]), startPoint: .top,
                               endPoint: .bottom)
                    .frame(width: w, height: groove).offset(y: top + rail)
                LinearGradient(stops: t.stops("streakRace.field", [(0, Skin.popupsStreakBannerStreakRaceField0), (0.2, Skin.popupsStreakBannerStreakRaceField1), (0.51, Skin.popupsStreakBannerStreakRaceField2), (0.83, Skin.popupsStreakBannerStreakRaceField3),
                                                                    (1, Skin.popupsStreakBannerStreakRaceField4)]),
                               startPoint: .top, endPoint: .bottom)
                    .frame(width: w, height: h - top - rail - groove).offset(y: top + rail + groove)
            }
            .frame(width: w, height: h, alignment: .topLeading)
        }
    }
}

// MARK: - data from the player's state

@MainActor enum StreakStripSource {
    /// The multiplier steps (`rules.json streak.steps`; ShellEconomy's reader, shared with the fail flow's Continue?).
    static func steps(_ app: AppModel) -> [Int] { ShellEconomy.streakSteps(app) }

    /// The strip for a panel: shown only from the Streak Race unlock (social.json `unlocks.streakRace`, L30).
    static func data(_ app: AppModel, level: Int, outcomes: [EventOutcome], lost: Bool) -> StreakStripData? {
        data(steps: steps(app), step: app.store.state.events.streakStep, level: level,
             unlock: app.tuning.social.file.int("unlocks.streakRace", 30), outcomes: outcomes, lost: lost, timeLeft: timeLeft(app))
            .map { var d = $0; d.ends = dayEnd(app); return d }
    }

    /// Pure: the strip from the multiplier steps, the player's step, the panel's level and the win's outcomes.
    nonisolated static func data(steps: [Int], step: Int, level: Int, unlock: Int, outcomes: [EventOutcome], lost: Bool,
                                 timeLeft: String) -> StreakStripData? {
        guard level >= unlock, !steps.isEmpty else { return nil }
        var from = max(0, min(steps.count - 1, step))
        var to = from
        for case let .multiplier(a, b) in outcomes {
            from = steps.firstIndex(of: a) ?? from
            to = steps.firstIndex(of: b) ?? to
        }
        if lost { to = 0 }
        return StreakStripData(steps: steps, from: from, to: to, timeLeft: timeLeft)
    }

    /// Time to the daily Streak Race boundary (SPEC-social: the event day ends 07:00 UTC), as "9h 16m" / "16:05" (`Countdown`).
    static func timeLeft(_ app: AppModel) -> String {
        let now = app.clock.wallClock()
        return Countdown.text(dayEndDate(app, now: now).timeIntervalSince(now))   // FIX-2 B (L28): the ONE event formatter
    }

    /// FIX-2 B (review of L28): that boundary on the social clock (the strip's chip ticks to it).
    static func dayEnd(_ app: AppModel) -> SocialTime {
        SocialTime(seconds: Int64(dayEndDate(app, now: app.clock.wallClock()).timeIntervalSince1970.rounded(.down)))
    }

    private static func dayEndDate(_ app: AppModel, now: Date) -> Date {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "UTC") ?? .gmt
        let hour = app.tuning.social.file.int("streakRace.endHourUTC", 7)
        var end = cal.date(bySettingHour: hour, minute: 0, second: 0, of: now) ?? now
        if end <= now { end = end.addingTimeInterval(86_400) }
        return end
    }
}
