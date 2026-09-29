import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-ui §1.6 chrome catalogue, §2.15-§2.19; SPEC-motion-audio §6.5, §9). The shared pieces of the social
// screens, drawn in code (the MANIFEST's event logos are route-B1 CODE components — `weeklyContestLogo`, `rocketRaceLogo`,
// `skyJumpLogo`, `clawLogo` — so the lettering is live text in PCDisplay-BlackItalic: it localises and it is ours):
//   SocEventLogo      the italic two-colour lettering with the blue outline and extrusion (Weekly Contest, Rocket Race, Sky Jump,
//                     Claw Challenge; Streak Race reuses S2's StreakRaceLettering with its flags)
//   SocRails          the cyan rails with rivets (Weekly band, Rocket band, Claw band in gold)
//   SocAvatar         a portrait in its frame (S3's AvatarFrameTile; green = the player)
//   SocTapTo          "Tap to Continue" / "Tap to Claim" footers
//   SocPop            the staggered pop of the info overlays (title +0.18, items +0.35/+0.58/+0.72/+0.88, footer +1.10)
// Names avoid GlossyChrome's reserved symbols (RankRow, SegmentTabs, AvatarFrame, RaceLane, TimerPill, …).

/// The italic event lettering: the first word yellow, the rest white (or the reverse for Sky Jump, VERIFIED 069/080),
/// a blue outline and a deep blue extrusion (SPEC-ui §2.15.3 profile; STYLE "EventLogo").
struct SocEventLogo: View {
    let title: LocalizedStringResource
    let frame: CGRect
    var size: CGFloat = 40
    /// true: "Weekly" yellow + "Contest" white; false: the first word white, the rest yellow ("Sky" white, "Jump" yellow).
    var yellowFirst = true
    var twoLines = false
    var outline: UInt32 = 0x00605B
    var extrusion: UInt32 = 0x00434A

    var body: some View {
        let yellow = GameTextStyle.s2(size, -size * 0.06, [0xFFF46A, 0xFFD21A, 0xF6A800], outline: outline, size * 0.075,
                                      drop: size * 0.07, dropColor: extrusion, face: .blackItalic)
        let white = GameTextStyle.s2(size, -size * 0.06, [0xFFFFFF, 0xF0F8F6, 0xD2E9E4], outline: outline, size * 0.075,
                                     drop: size * 0.07, dropColor: extrusion, face: .blackItalic)
        let full = String(localized: title)
        // B3: the first WORD (LineUnits: the first space-separated word, or a CJK name's first dictionary word) takes the
        // first colour; a CJK split has no space, so its two parts touch (gap 0)
        let units = LineUnits.units(full)
        let (w1, w2) = Self.words(units, full: full, twoLines: twoLines)
        let spaced = units.first?.space ?? true
        let s1 = yellowFirst ? yellow : white, s2 = yellowFirst ? white : yellow
        ZStack(alignment: .topLeading) {
            if twoLines {
                GameText(verbatim: w1, style: s1, maxWidth: frame.width - 10).at(frame.width / 2, s1.capCentre(baseline: frame.height * 0.45))
                GameText(verbatim: w2, style: s2, maxWidth: frame.width - 10).at(frame.width / 2, s2.capCentre(baseline: frame.height * 0.88))
            } else {
                // B3: a one-word name (de Wolkenhüpfer, ja 雲わたり) takes the whole width, not the first word's 55 %
                let a = GameTextLayout.make(w1, postScriptName: s1.postScriptName, size: s1.size, tracking: s1.tracking,
                                            maxWidth: w2.isEmpty ? frame.width - 8 : frame.width * 0.55, minScale: 0.6)
                let b = GameTextLayout.make(w2, postScriptName: s2.postScriptName, size: s2.size, tracking: s2.tracking,
                                            maxWidth: frame.width * 0.62, minScale: 0.6)
                let gap = spaced ? size * 0.04 : 0
                let total = a.advance + gap + b.advance
                let fit = min(1, (frame.width - 8) / max(total, 1))
                let _ = FitLedger.note("eventLogo", text: full, need: (frame.width - 8) / max(total, 1))
                let x0 = frame.width / 2 - total / 2
                let base = frame.height * 0.74
                ZStack(alignment: .topLeading) {
                    GameText(verbatim: w1, style: s1, maxWidth: w2.isEmpty ? frame.width - 8 : frame.width * 0.55)
                        .at(x0 + a.advance / 2, s1.capCentre(baseline: base))
                    GameText(verbatim: w2, style: s2, maxWidth: frame.width * 0.62)
                        .at(x0 + a.advance + gap + b.advance / 2, s2.capCentre(baseline: base))
                }
                .frame(width: frame.width, height: frame.height)
                .scaleEffect(fit, anchor: .center)
            }
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(title))
    }

    /// B3: (first word, the rest). A one-word hyphenated name on the two-line badge breaks after its hyphen
    /// (de "Raketen-" / "Rallye").
    static func words(_ units: [TextUnit], full: String, twoLines: Bool) -> (String, String) {
        let w1 = units.first?.text ?? full, w2 = LineUnits.join(units.dropFirst())
        if twoLines, units.count == 1, let h = w1.firstIndex(of: "-"), h != w1.startIndex, w1.index(after: h) != w1.endIndex {
            return (String(w1[...h]), String(w1[w1.index(after: h)...]))
        }
        return (w1, w2)
    }
}

/// The cyan rails (face #00B4FF, top light #72D6FF) with round rivets near both ends (Weekly band, Rocket band; VERIFIED
/// meta-013 / 167), or the Claw's gold rails (#FED023).
struct SocRails: View {
    var gold = false
    var body: some View {
        Rasterized("socRails|\(gold)") { size in
            let face: UInt32 = gold ? 0xFED023 : 0x40BCAC
            let light: UInt32 = gold ? 0xFFF08A : 0x95D7C5
            let dark: UInt32 = gold ? 0xB77F00 : 0x007471
            let rivet: UInt32 = gold ? 0xE0A400 : 0x39A496
            ZStack(alignment: .topLeading) {
                Color(hex: dark)
                LinearGradient(colors: [Color(hex: light), Color(hex: face), Color(hex: face)], startPoint: .top, endPoint: .bottom)
                    .padding(.top, 1).padding(.bottom, 1.6)
                ForEach([31.0, 362.0], id: \.self) { x in
                    Circle().fill(Color(hex: dark, 0.6)).frame(width: 13, height: 13).position(x: CGFloat(x) * size.width / 393, y: size.height / 2 + 0.8)
                    Circle().fill(Color(hex: rivet)).frame(width: 13, height: 13).position(x: CGFloat(x) * size.width / 393, y: size.height / 2)
                    Circle().fill(Color.white.opacity(0.35)).frame(width: 5, height: 3).position(x: CGFloat(x) * size.width / 393, y: size.height / 2 - 3)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

/// A portrait in its superellipse frame (S3's AvatarFrameTile; the player's is green).
struct SocAvatar: View {
    let index: Int
    var me = false
    var body: some View { AvatarFrameTile(index: index, selected: me, n: 3.5, ring: 0.085) }
}

/// "Tap to Continue" / "Tap to Claim" (SPEC-ui §2.15.6 footer: 20.8, face #FFF5E8 → #FFDFCC, outline #172B5A 1.2).
struct SocTapTo: View {
    let text: LocalizedStringResource
    let baseline: CGFloat
    var body: some View {
        let st = GameTextStyle.s2(20.8, -0.6, [0xFDF6E9, 0xF5E3CB], outline: 0x1A3132, 1.2, drop: 1.0)
        GameText(text, style: st, maxWidth: 330).at(196.5, st.capCentre(baseline: baseline))
    }
}

/// The info overlays' text: 15-16 pt centred, face #FCE7D7, the key word yellow #FFD302, outline #172B5A 1.0
/// (SPEC-ui §2.15.6). `key` is the highlighted word inside the localised line (drawn yellow when found).
struct SocInfoLine: View {
    let text: LocalizedStringResource
    var key: LocalizedStringResource? = nil
    let centreX: CGFloat
    let baseline: CGFloat
    var size: CGFloat = 16
    var maxWidth: CGFloat = 300
    var alignLeft = false

    var body: some View {
        let plain = GameTextStyle.s2(size, 0, [0xF6E9D8], outline: 0x1A3132, 1.0, drop: 0.8)
        let hot = GameTextStyle.s2(size, 0, [0xFFE45A, 0xFFD302], outline: 0x1A3132, 1.0, drop: 0.8)
        let full = String(localized: text)
        let k = key.map { String(localized: $0) }
        if let k, let r = full.range(of: k) {
            let a = String(full[..<r.lowerBound]), b = String(full[r]), c = String(full[r.upperBound...])
            let la = GameTextLayout.make(a, postScriptName: plain.postScriptName, size: plain.size, tracking: 0)
            let lb = GameTextLayout.make(b, postScriptName: hot.postScriptName, size: hot.size, tracking: 0)
            let lc = GameTextLayout.make(c, postScriptName: plain.postScriptName, size: plain.size, tracking: 0)
            let total = la.advance + lb.advance + lc.advance
            let fit = min(1, maxWidth / max(total, 1))
            let pa = fit < 1 ? plain.sized(plain.size * fit) : plain, ph = fit < 1 ? hot.sized(hot.size * fit) : hot
            let x0 = alignLeft ? centreX : centreX - total * fit / 2
            ZStack(alignment: .topLeading) {
                if !a.isEmpty { GameText(verbatim: a, style: pa).at(x0 + la.advance * fit / 2, pa.capCentre(baseline: baseline)) }
                GameText(verbatim: b, style: ph).at(x0 + (la.advance + lb.advance / 2) * fit, ph.capCentre(baseline: baseline))
                if !c.isEmpty {
                    GameText(verbatim: c, style: pa).at(x0 + (la.advance + lb.advance + lc.advance / 2) * fit, pa.capCentre(baseline: baseline))
                }
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(Text(verbatim: full))
        } else if alignLeft {
            let l = GameTextLayout.make(full, postScriptName: plain.postScriptName, size: plain.size, tracking: 0, maxWidth: maxWidth)
            GameText(verbatim: full, style: plain, maxWidth: maxWidth).at(centreX + l.advance / 2, plain.capCentre(baseline: baseline))
        } else {
            GameText(verbatim: full, style: plain, maxWidth: maxWidth).at(centreX, plain.capCentre(baseline: baseline))
        }
    }
}

/// `Curves.pop(duration, overshoot)`: 0 → overshoot at 60 % → 1 (SPEC-motion-audio §6.5), nil before it starts.
enum SocPop {
    static func scale(_ u: Double, at start: Double, duration: Double = 0.16, overshoot: Double = 1.12) -> Double? {
        let t = u - start
        guard t >= 0 else { return nil }
        guard t < duration else { return 1 }
        let x = t / duration
        if x < 0.6 { let k = x / 0.6; return overshoot * (1 - (1 - k) * (1 - k)) }
        let k = (x - 0.6) / 0.4
        return overshoot + (1 - overshoot) * (k * k * (3 - 2 * k))
    }
}

/// A view that appears with a pop at `start` seconds after `shownAt` (hidden before). The content usually fills the 393 × 852
/// canvas (it is `.placed` / `.at` inside it), so the pop scales about `at` — the item's centre on the canvas — not the canvas
/// centre; without `at` it scales about `anchor` of its own bounds.
struct SocPopIn<Content: View>: View {
    let u: Double
    let start: Double
    var duration = 0.16
    var overshoot = 1.12
    var anchor: UnitPoint = .center
    var at: CGPoint? = nil
    @ViewBuilder var content: Content
    var body: some View {
        if let k = SocPop.scale(u, at: start, duration: duration, overshoot: overshoot) {
            content.scaleEffect(CGFloat(k), anchor: at.map { UnitPoint(x: $0.x / 393, y: $0.y / 852) } ?? anchor)
        }
    }
}

/// Localised sentences with a number written the phone's way ("5000 coins", never the locale's "5,000" / "5.000").
enum SocText {
    static func plain(_ make: (Int) -> LocalizedStringResource, _ n: Int) -> String {
        let s = String(localized: make(987_654_321))
        return s.replacingOccurrences(of: "987\\D?654\\D?321", with: String(n), options: .regularExpression)
    }
}

/// The countdown of an event, in the shared formats (SPEC-social §4.1; Countdown is S3's).
enum SocTime {
    static func left(_ end: SocialTime, now: SocialTime) -> Double { Double(max(0, end.seconds - now.seconds)) }

    @MainActor static func now(_ app: AppModel) -> SocialTime {
        EconomyClock.peekSocial(app.store.state, wall: app.clock.wallClock())
    }
}

/// True inside `SocialPopups.prewarm` (the event pages rendered once, invisibly, behind Loading): the pages skip every side
/// effect of a real open (visibility, probes, event refresh, list host, first-open flags) and only pay their first render.
private struct SocPrewarmKey: EnvironmentKey { static let defaultValue = false }
extension EnvironmentValues {
    var socPrewarm: Bool {
        get { self[SocPrewarmKey.self] }
        set { self[SocPrewarmKey.self] = newValue }
    }
}
