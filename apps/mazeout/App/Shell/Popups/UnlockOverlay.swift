import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.8; uim `unlock.*`, VERIFIED 040 Pipe / 134 Box / V1 L7; SPEC-motion-audio §6.3, §10 "unlock twinkles";
// CONSISTENCY T-25: MA's beats win). A feature's first appearance: over the level (its intro runs underneath, the timer frozen)
// the 0.90 dim, then staggered pops from the overlay's first frame S:
//   S + 0.26  the icon pops 0 → 1.3 (+0.16) → 1.0 (+0.28)                    (ui.json unlock.icon / iconSettle)
//   S + 0.50  "<Name>!" pops 0.2 → 1.15 (+0.12) → 1.0 (+0.16)                 (unlock.title)
//   S + 0.62  "Unlocked!" pops 0.2 → 1.0, easeOutBack, 0.08 s                 (unlock.unlocked)
//   S + 0.78  the card pops 0.2 → 1.12 (+0.12) → 1.0 (+0.16)                  (unlock.card)
//   S + 1.14  twinkles around the icon until dismissed: one every 0.18 s, ≤ 6 live, 0.70 s each, in a 150 × 110 ellipse
//   tap anywhere (accepted from S + 0.94, `unlock.acceptFrom`) → ♪ uiClick + ◉ button; A2 FEEL-P (contract amend 4, `unlock.
//   dismissMode` "contentCut", VERIFIED v552 ×2, motion-catalog §3.2 / §6.7): the content goes on that frame and the DIM fades
//   LINEARLY over `unlock.dismissFade` 0.233 s (the popup host's dim), then .close ("fade": everything fades, the old look)
//   ◉ rewardPop (light 0.40) when the icon lands (S + iconSettle) and when the card lands (S + card + 0.16) — motion-catalog §5.1
//   row 22
// ♪ unlockChime on the first frame (audio.json `cues.unlockOverlay`). Look: the title 54.4 / −3.65 (cream face, a layered blue
// outline 3.3 pt + a #0D49D6 drop), "Unlocked!" 24.5 white outlined #022880, the icon at 147.1 · 354.3 · 123.8 · 112.1 (Pipe; each
// feature's art fitted to its measured box), the cream card 42.7 · 517.1 · 307.9 · 100.1 (rr 23.9, a double blue border #005DEE) with
// two centred lines 22.3 / −0.5 navy #231C67, the CAPS words blue #1A5FD8 (box 272). Copy: Levels/unlocks.json → the strings table.

struct UnlockOverlay: View {
    let feature: FeatureID
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?
    @State private var dismissAt: Double?

    var body: some View {
        let beats = UnlockTiming(app.tuning.ui)
        let content = UnlockContent.of(feature)
        TimelineView(.animation(minimumInterval: nil, paused: shownAt == nil)) { ctx in
            let now = app.clock.gameTime(ctx.date)
            let u = shownAt.map { app.clock.sequenceTime("unlock", now - $0) } ?? 0
            // A2: contentCut = the content goes in one frame (the host fades the dim); fade = everything fades together
            let fade = dismissAt.map { beats.b.dismissMode == .contentCut ? 0 : max(0, 1 - (now - $0) / max(0.01, beats.dismissFade)) } ?? 1
            ZStack(alignment: .topLeading) {
                Color.clear
                UnlockParts(content: content, u: u).equatable()
                if u >= beats.sparkles { UnlockTwinkles(u: u - beats.sparkles, centre: content.iconCentre, t: app.tuning.ui.tokens) }
                let _ = UnlockBeatLog.note(feature: feature, u: u, beats: beats, haptics: dismissAt == nil ? app.haptics : nil)
            }
            .opacity(fade)
        }
        .frame(width: 393, height: 852)
        .contentShape(Rectangle())
        .onTapGesture { tap(beats) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("unlock.overlay")
        .onAppear {
            shownAt = app.clock.gameTime()
            Log.mark("unlock", "show \(feature.rawValue)")
            if let cue = app.tuning.audio.cue("unlockOverlay") { app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue))) }
        }
    }

    private func tap(_ beats: UnlockTiming) {
        guard dismissAt == nil, let s = shownAt else { return }
        let now = app.clock.gameTime()
        guard now - s >= beats.acceptFrom else { return }
        if let cue = app.tuning.audio.cue("uiButton") { app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue))) }
        if let h = GameButtonFeedback.haptic(app) { app.haptics.play(h) }
        dismissAt = now
        Log.mark("unlock", "dismiss \(feature.rawValue) at S+\(String(format: "%.3f", now - s)) (\(beats.b.dismissMode.rawValue))")
        let wait = beats.dismissFade / max(app.clock.baseTimeScale, 0.01)
        if beats.b.dismissMode == .contentCut { answer.host.fadeDim(answer.id, over: wait) }       // A2: the dim, linear
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: UInt64(wait * 1_000_000_000))
            answer(PopupResult.close)
        }
    }
}

/// The beats (ui.json `unlock.*`; the ◆ UnlockBeats reader + `acceptFrom`).
struct UnlockTiming {
    let b: UnlockBeats
    let acceptFrom: Double
    init(_ ui: UITuning) {
        b = ui.unlockBeats
        acceptFrom = ui.file.double("unlock.acceptFrom", 0.94)
    }
    var dismissFade: Double { b.dismissFade }
    var sparkles: Double { b.sparkles }

    /// Scale of an element at u (nil before its beat): the generic overshoot pop kf[0: from, rise: over, total: 1.0].
    static func pop(_ u: Double, at: Double, from: Double, over: Double, rise: Double, total: Double) -> Double? {
        let x = u - at
        if x < 0 { return nil }
        if x >= total { return 1 }
        if x < rise { return from + (over - from) * Easing.outQuad(x / rise) }
        return over + (1 - over) * Easing.inOutQuad((x - rise) / max(0.001, total - rise))
    }

    func icon(_ u: Double) -> Double? { Self.pop(u, at: b.icon, from: 0, over: 1.3, rise: 0.16, total: max(0.2, b.iconSettle - b.icon)) }
    func title(_ u: Double) -> Double? { Self.pop(u, at: b.title, from: 0.2, over: 1.15, rise: 0.12, total: 0.16) }
    func unlocked(_ u: Double) -> Double? {
        let x = u - b.unlocked
        if x < 0 { return nil }
        return x >= 0.08 ? 1 : 0.2 + 0.8 * Easing.outBack(x / 0.08)
    }
    func card(_ u: Double) -> Double? { Self.pop(u, at: b.card, from: 0.2, over: 1.12, rise: 0.12, total: 0.16) }
}

/// Title, "Unlocked!", icon and card at time u (Equatable: after the card settles only the twinkles re-render).
struct UnlockParts: View, Equatable {
    let content: UnlockContent
    let u: Double
    @Environment(AppModel.self) private var app

    static func == (a: UnlockParts, b: UnlockParts) -> Bool {
        a.content == b.content && (a.u == b.u || (a.u >= 1.0 && b.u >= 1.0))
    }

    var body: some View {
        let t = app.tuning.ui.tokens
        let beats = UnlockTiming(app.tuning.ui)
        ZStack(alignment: .topLeading) {
            if let s = beats.icon(u) {
                ZStack(alignment: .topLeading) {
                    InkImage(art: content.icon, ink: content.iconInk)
                    if let digit = content.digit {
                        // content-driven (unlocks.json digit size / outline), so no ui.json override
                        let st = GameTextStyle.s2(content.digitSize, 0, [0xFFFFFF, 0xFDF2F7], outline: content.digitOutline, 1.9,
                                                  drop: 1.4)
                        let c = ArtInk.canvas(content.icon, ink: content.iconInk)
                        GameText(verbatim: digit, style: st)
                            .position(x: c.minX + content.digitAt.x * c.width, y: c.minY + content.digitAt.y * c.height)
                    }
                }
                .scaleEffect(CGFloat(s), anchor: UnitPoint(x: content.iconCentre.x / 393, y: content.iconCentre.y / 852))
            }
            if let s = beats.title(u) {
                TokenText(id: "unlock.title.title", source: .copy(content.title),
                          style: .s2(54.4, -3.65, [0xFFFBF4, 0xFFF5E2, 0xFDF0D6], outline: 0x003E44, 0.35, drop: 1.3, dropColor: 0x00635E),
                          baseline: 220.9, centreX: 196.5, maxWidth: 345,
                          rings: [(0x00706C, 3.6), (0x008881, 3.3), (0x00A596, 2.4), (0x005B59, 2.0)])
                    .scaleEffect(CGFloat(s), anchor: UnitPoint(x: 0.5, y: 203.0 / 852))
            }
            if let s = beats.unlocked(u) {
                TokenText(id: "unlock.subtitle.sub", source: .copy("Unlocked!"),
                          style: .s2(24.5, 0.26, [0xFFFFFF], outline: 0x00373B, 1.67, drop: 1.16),
                          baseline: 299.0, centreX: 196.7, maxWidth: 300)
                    .scaleEffect(CGFloat(s), anchor: UnitPoint(x: 0.5, y: 290.0 / 852))
            }
            if let s = beats.card(u) {
                UnlockCard(content: content, t: t)
                    .scaleEffect(CGFloat(s), anchor: UnitPoint(x: 0.5, y: 567.0 / 852))
            }
        }
        .frame(width: 393, height: 852, alignment: .topLeading)
    }
}

/// The cream card with the blue double border and the two lines (greedy line fill in the 272 pt box; CAPS words blue).
private struct UnlockCard: View {
    let content: UnlockContent
    let t: Tokens

    var body: some View {
        let frame = t.frame("unlock.card", CGRect(42.7, 517.1, 307.9, 100.1))
        let style0 = t.text("unlock.card.line1", .s2(22.3, -0.66, [0x002E32]))
        // FIX-V2 F-02: greedy breaks (the phone's), else the balanced break + one shrink for both lines (TR "ASANSÖRÜ …" overflowed)
        // B3: units, not words: a CJK card breaks between its words (LineUnits) and lights its `**` run (no letter case)
        let base = CGFloat(t.textMaxWidth("unlock.card.line1", 272) ?? 272)
        let fit = UnlockCardLines.fitUnits(String(localized: content.card), style: style0,
                                           width: UnlockCardLines.width(feature: content.feature, base: base))
        let lines = fit.lines
        let style = fit.scale < 1 ? style0.sized(style0.size * fit.scale) : style0
        let b1 = CGFloat(t.number("text.unlock.card.line1.baseline", 561.1)), b2 = CGFloat(t.number("text.unlock.card.line2.baseline", 588.0))
        ZStack(alignment: .topLeading) {
            Rasterized("unlockCard2", overflow: 2) { _ in
                // VERIFIED 040 at y 575 / x 196: an 11.3 pt border — navy hairline, the blue band, a cyan line, a deep-blue line, a
                // dark line, a tan bevel ~3 pt, a light hairline — then the cream (54.4 / 528.4 on a 42.7 / 517.1 frame)
                ZStack {
                    RoundedRectangle(cornerRadius: 23.9, style: .continuous).fill(Color(hex: 0x001E21))
                    RoundedRectangle(cornerRadius: 23.2, style: .continuous).fill(t.color("unlock.cardBorder", 0x007572)).padding(0.8)
                    RoundedRectangle(cornerRadius: 19.8, style: .continuous).fill(Color(hex: 0x1AA495)).padding(4.2)
                    RoundedRectangle(cornerRadius: 19.2, style: .continuous).fill(Color(hex: 0x00494F)).padding(4.9)
                    RoundedRectangle(cornerRadius: 17.8, style: .continuous).fill(Color(hex: 0x002326)).padding(6.3)
                    RoundedRectangle(cornerRadius: 17.2, style: .continuous)
                        .fill(Color(hex: 0xDCBB95))
                        .overlay(RoundedRectangle(cornerRadius: 17.2, style: .continuous).strokeBorder(Color(hex: 0xC18F5D), lineWidth: 1.1)
                            .blur(radius: 0.5))
                        .clipShape(RoundedRectangle(cornerRadius: 17.2, style: .continuous))
                        .padding(7.0)
                    RoundedRectangle(cornerRadius: 14.2, style: .continuous).fill(Color(hex: 0xFAF4EB)).padding(10.2)
                    RoundedRectangle(cornerRadius: 13.6, style: .continuous).fill(t.color("unlock.card", 0xF4E8D4)).padding(10.9)
                }
            }
            .placed(frame)
            ForEach(Array(lines.enumerated()), id: \.offset) { i, line in
                MultiRunText(units: line, style: style, highlight: t.color("unlock.caps", 0x00736E))
                    .at(196.5, style.capCentre(baseline: lines.count == 1 ? (b1 + b2) / 2 : (i == 0 ? b1 : b2)))
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("unlock.card")
        .accessibilityLabel(Text(verbatim: LineUnits.plain(String(localized: content.card))))
    }
}

/// Greedy line fill of the unlock card (VERIFIED 040 / 134 breaks).
/// B3: the card breaks between `LineUnits` — its words in EN/TR and the other space-separated languages (identical to the
/// old word split), its dictionary words in Japanese and Chinese — and a `**` run (the caseless languages' highlight) is
/// measured without its markers. `lines` / `fit` keep their word API ([[String]]); the card draws `fitUnits`.
enum UnlockCardLines {
    /// FIX-2 lane B (F-16, V2: the phone's Corner card breaks "Arrows turn when they hit / the CORNER!", one word later than
    /// ours at 272 pt — its line 1 ink is 274.3 pt on build/compare/refs/S2-L070-corner-unlock-card.png, ours needs ≈ 281 pt of
    /// advance in PC Display): the Corner card's line box is 285 pt (the cream is 286 pt wide). Every other card keeps the
    /// measured 272 pt — widening them all would move none of the VERIFIED breaks (040 pipe, 134 box, 712 elevator) but would
    /// change the other languages' fits for no evidence.
    static func width(feature: String, base: CGFloat) -> CGFloat { feature == "corner" ? max(base, 285) : base }

    /// Greedy fill: words go on line 1 while it fits `width`, the rest on line 2 (VERIFIED 040 / 134 breaks).
    static func lines(_ text: String, style: GameTextStyle, width: CGFloat) -> [[String]] {
        unitLines(text, style: style, width: width).map { $0.map(\.text) }
    }

    static func unitLines(_ text: String, style: GameTextStyle, width: CGFloat) -> [[TextUnit]] {
        let words = LineUnits.units(text)
        var first: [TextUnit] = []
        for (i, w) in words.enumerated() {
            let trial = LineUnits.plain(LineUnits.join(first + [w]))
            let adv = GameTextLayout.make(trial, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking).advance
            if adv > width && !first.isEmpty {
                return [first, Array(words[i...])]
            }
            first.append(w)
        }
        return [first]
    }

    /// FIX-V2 F-02 (SPEC-ui §1.4 auto-shrink, floor 0.70): the greedy lines when every line fits `width` (scale 1); else the
    /// two-line break whose wider line is narrowest, and the one scale that fits it into `width` (never below 0.70).
    static func fit(_ text: String, style: GameTextStyle, width: CGFloat) -> (lines: [[String]], scale: CGFloat) {
        let f = fitUnits(text, style: style, width: width)
        return (f.lines.map { $0.map(\.text) }, f.scale)
    }

    static func fitUnits(_ text: String, style: GameTextStyle, width: CGFloat) -> (lines: [[TextUnit]], scale: CGFloat) {
        func adv(_ ws: [TextUnit]) -> CGFloat {
            GameTextLayout.make(LineUnits.plain(LineUnits.join(ws)), postScriptName: style.postScriptName, size: style.size,
                                tracking: style.tracking).advance
        }
        let greedy = unitLines(text, style: style, width: width)
        let widest = greedy.map(adv).max() ?? 0
        if widest <= width { return (greedy, 1) }
        let words = LineUnits.units(text)
        var best = greedy, bestW = widest
        if words.count > 1 {
            for i in 1..<words.count {
                let a = Array(words[..<i]), b = Array(words[i...])
                let w = max(adv(a), adv(b))
                if w < bestW { best = [a, b]; bestW = w }
            }
        }
        let scale = max(0.70, min(1, width / max(bestW, 1)))
        FitLedger.note("unlock.card", text: text, need: width / max(bestW, 1))
        return (best, scale)
    }
}

/// One line of words, the fully upper-case words (≥ 2 letters) in the highlight colour, centred on the view's centre.
/// B3: `units` (LineUnits) instead of words — a unit with no space after it is glued to the next (CJK), and a `**…**` run
/// is lit in the highlight colour (the unlock term of the caseless languages: ja, ko, zh-Hans), its markers never drawn.
struct MultiRunText: View {
    let units: [TextUnit]
    let style: GameTextStyle
    let highlight: Color

    init(units: [TextUnit], style: GameTextStyle, highlight: Color) {
        self.units = units; self.style = style; self.highlight = highlight
    }

    init(words: [String], style: GameTextStyle, highlight: Color) {
        self.init(units: words.enumerated().map { TextUnit(text: $0.element, space: $0.offset < words.count - 1) },
                  style: style, highlight: highlight)
    }

    static func isCaps(_ w: String) -> Bool {
        let letters = w.filter { $0.isLetter }
        return letters.count >= 2 && letters == letters.uppercased() && letters != letters.lowercased()
    }

    /// (text, highlighted, glued to the previous run: no space) — consecutive pieces with the same highlight merge.
    static func runs(_ units: [TextUnit]) -> [(String, Bool, Bool)] {
        var pieces: [(String, Bool, Bool)] = []           // (text, highlighted, gap before)
        var marked = false
        for (i, u) in units.enumerated() {
            let gap = i > 0 && units[i - 1].space
            if !marked && !u.text.contains("**") {
                // a CAPS word's trailing punctuation stays plain ("BOX" blue, "!" navy)
                let c = isCaps(u.text)
                var core = u.text, tail = ""
                if c { while let last = core.last, !last.isLetter { tail = String(last) + tail; core.removeLast() } }
                pieces.append((core, c, gap))
                if !tail.isEmpty { pieces.append((tail, false, false)) }
                continue
            }
            let parts = u.text.components(separatedBy: "**")
            for (j, part) in parts.enumerated() {
                if j > 0 { marked.toggle() }
                if part.isEmpty { continue }
                pieces.append((part, marked, j == 0 ? gap : false))
            }
        }
        var runs: [(String, Bool, Bool)] = []
        for p in pieces where !p.0.isEmpty {
            if let last = runs.last, last.1 == p.1 {
                runs[runs.count - 1].0 += (p.2 ? " " : "") + p.0
            } else {
                runs.append((p.0, p.1, runs.isEmpty ? false : !p.2))
            }
        }
        return runs
    }

    var body: some View {
        let text = LineUnits.plain(LineUnits.join(units))
        return RunsLine(runs: Self.runs(units), style: style, highlight: highlight).accessibilityLabel(Text(verbatim: text))
    }
}

/// Runs laid out left → right with a space between them, centred.
private struct RunsLine: View {
    let runs: [(String, Bool, Bool)]
    let style: GameTextStyle
    let highlight: Color

    var body: some View {
        let layouts = runs.map { GameTextLayout.make($0.0, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking) }
        let space = GameTextLayout.make("x x", postScriptName: style.postScriptName, size: style.size, tracking: style.tracking).advance
            - GameTextLayout.make("xx", postScriptName: style.postScriptName, size: style.size, tracking: style.tracking).advance
        let widths = layouts.map { $0.advance + style.tracking }
        // the gap before run i: a space unless the run is glued punctuation
        let gaps = runs.enumerated().map { i, r -> CGFloat in i == 0 || r.2 ? 0 : space }
        let starts = (0..<runs.count).map { i in widths.prefix(i).reduce(0, +) + gaps.prefix(i + 1).reduce(0, +) }
        let total = (starts.last ?? 0) + (layouts.last?.advance ?? 0)
        ZStack(alignment: .topLeading) {
            ForEach(Array(runs.enumerated()), id: \.offset) { i, run in
                GameText(verbatim: run.0, style: colored(run.1))
                    .position(x: starts[i] + layouts[i].advance / 2, y: 1)
            }
        }
        .frame(width: max(1, total), height: 2, alignment: .topLeading)
    }

    private func colored(_ h: Bool) -> GameTextStyle {
        var s = style
        if h { s.fill = [highlight] }
        return s
    }
}

/// The feature's copy and art (Levels/unlocks.json → the strings table; icons fitted to the phone's measured boxes).
struct UnlockContent: Equatable {
    let feature: String
    let title: LocalizedStringResource
    let card: LocalizedStringResource
    let icon: UIArt
    let iconInk: CGRect
    let digit: String?
    let digitSize: CGFloat
    let digitOutline: UInt32
    /// The digit's centre as a fraction of the icon's canvas.
    let digitAt: CGPoint

    var iconCentre: CGPoint { CGPoint(x: iconInk.midX, y: iconInk.midY) }

    static func == (a: UnlockContent, b: UnlockContent) -> Bool { a.feature == b.feature }

    private struct Row: Decodable { let feature: String; let title: String; let card: String; let icon: String? }
    private struct File: Decodable { let unlocks: [Row] }
    @MainActor private static var rows: [String: Row]?

    @MainActor static func of(_ feature: FeatureID) -> UnlockContent {
        if rows == nil {
            var map: [String: Row] = [:]
            if let url = Bundle.main.url(forResource: "unlocks", withExtension: "json", subdirectory: "Levels"),
               let data = try? Data(contentsOf: url), let f = try? JSONDecoder().decode(File.self, from: data) {
                for r in f.unlocks { map[r.feature] = r }
            }
            rows = map
        }
        let row = rows?[feature.rawValue]
        let title = row?.title ?? (feature == .corner ? "Corner!" : feature.rawValue.capitalized + "!")
        let card = row?.card ?? (feature == .corner ? "The CORNER turns arrows around!" : "")
        let icon = row?.icon.flatMap(UIArt.init(rawValue:)) ?? Self.defaultIcon(feature)
        // measured ink boxes: Pipe 040, Box 134; the others centred where the phone centres the icon (196.5, 410)
        let ink: CGRect
        var digit: String?, size: CGFloat = 30, outline: UInt32 = 0x123538, at = CGPoint.zero
        switch icon {
        case .unlockIconPipe:
            // the counter cap's centre in the canvas (art/ui/out/unlockIconPipe@3x.png), the phone's "3" (040)
            ink = CGRect(125.0, 353.0, 142.0, 117.0)       // the whole pipe incl. its gold mouths (040: x 125-267, y 353-470)
            digit = "3"; size = 26; outline = 0x713201
            at = CGPoint(x: 0.437, y: 0.225)
        case .unlockIconBox:
            // the ring's centre (unlockIconBox@3x.png), the phone's "5" (134)
            ink = CGRect(136.5, 351.0, 121.5, 127.5)
            digit = "5"; size = 34; outline = 0x19383A
            at = CGPoint(x: 0.475, y: 0.47)
        case .unlockIconCorner:
            ink = CGRect(146.55, 363.25, 100, 100)          // FIX-2 A (L02): the whole 100 pt canvas centred on 456's ink centre
        default:
            ink = CGRect(136.5, 355.0, 120.0, 110.0)
        }
        return UnlockContent(feature: feature.rawValue, title: LocalizedStringResource(String.LocalizationValue(title)),
                             card: LocalizedStringResource(String.LocalizationValue(card)), icon: icon, iconInk: ink, digit: digit,
                             digitSize: size, digitOutline: outline, digitAt: at)
    }

    private static func defaultIcon(_ f: FeatureID) -> UIArt {
        switch f {
        case .linked: return .unlockIconLinked
        case .box: return .unlockIconBox
        case .pipe: return .unlockIconPipe
        case .elevator: return .unlockIconElevator
        case .door: return .unlockIconDoor
        case .curtain: return .unlockIconBox        // FIX-2 B (A4-r2): a curtain wears the BOX skin (ruling 11); unlockIconCurtain is retired
        default: return .unlockIconLinked
        }
    }
}

/// Twinkles around the icon (SPEC-motion-audio §10: one every 0.18 s, ≤ 6 live, 0.70 s: scale 0 → 1 → 0 + a 45° turn, uniform in a
/// 150 × 110 ellipse; `sparkleTwinkle` 10-16 pt). Deterministic per spawn index (captures repeat).
private struct UnlockTwinkles: View {
    let u: Double
    let centre: CGPoint
    let t: Tokens

    var body: some View {
        let every = t.number("fx.unlockTwinkles.every", 0.18), life = t.number("fx.unlockTwinkles.life", 0.70)
        let ell = t.list("fx.unlockTwinkles.ellipse", [150, 110])
        let newest = Int(u / every)
        let oldest = max(0, newest - Int(ceil(life / every)) + 1)
        ZStack(alignment: .topLeading) {
            ForEach(oldest...max(oldest, newest), id: \.self) { i in
                let age = u - Double(i) * every
                if age >= 0 && age < life {
                    let r = Self.rand(i)
                    let a = r.0 * 2 * .pi, rr = sqrt(r.1)
                    let x = centre.x + CGFloat(cos(a) * rr * ell[0] / 2), y = centre.y + CGFloat(sin(a) * rr * ell[1] / 2)
                    let size = CGFloat(t.number("fx.unlockTwinkles.sizeMin", 12) + (t.number("fx.unlockTwinkles.sizeMax", 20) - t.number("fx.unlockTwinkles.sizeMin", 12)) * r.2)
                    let k = age / life
                    let s = k < 0.5 ? k / 0.5 : (1 - k) / 0.5
                    ArtImage(art: .sparkleTwinkle)
                        .colorMultiply(r.2 < 0.5 ? Color(hex: 0xFFE680) : .white)
                        .frame(width: size, height: size)
                        .scaleEffect(CGFloat(s))
                        .rotationEffect(.degrees(45 * k))
                        .position(x: x, y: y)
                }
            }
        }
        .allowsHitTesting(false)
    }

    /// Three uniform numbers in 0..1 from the spawn index (SplitMix64 steps).
    static func rand(_ i: Int) -> (Double, Double, Double) {
        var z = UInt64(bitPattern: Int64(i)) &+ 0x9E3779B97F4A7C15
        func next() -> Double {
            z = z &+ 0x9E3779B97F4A7C15
            var x = z
            x = (x ^ (x >> 30)) &* 0xBF58476D1CE4E5B9
            x = (x ^ (x >> 27)) &* 0x94D049BB133111EB
            x ^= x >> 31
            return Double(x >> 11) / Double(1 << 53)
        }
        return (next(), next(), next())
    }
}

/// `[PC][unlock] beat <name> S+t (spec …)` on the first frame at or after each beat.
@MainActor enum UnlockBeatLog {
    private static var logged: Set<String> = []
    private static var lastU = -1.0

    static func note(feature: FeatureID, u: Double, beats: UnlockTiming, haptics: (any HapticPlaying)? = nil) {
        if u < lastU - 0.3 { logged.removeAll() }
        lastU = u
        let list: [(String, Double)] = [("icon", beats.b.icon), ("title", beats.b.title), ("unlocked", beats.b.unlocked),
                                        ("card", beats.b.card), ("sparkles", beats.b.sparkles), ("accept", beats.acceptFrom),
                                        ("iconLand", beats.b.iconSettle), ("cardLand", beats.b.card + 0.16)]
        for (name, at) in list where u >= at && !logged.contains(name) {
            logged.insert(name)
            // A2 (motion-catalog §5.1 row 22): the icon and the card landing vibrate lightly, on their frame (not if late)
            if name.hasSuffix("Land"), u - at < 0.05 { haptics?.play(.rewardPop) }
            Log.mark("unlock", "beat \(feature.rawValue) \(name) S+\(String(format: "%.4f", u)) (spec \(String(format: "%.2f", at)))")
        }
    }
}

/// The unlock overlay's static parts rendered once behind Loading (the titles' ring rasters, the card, the icons).
struct UnlockParts_Prewarm: View {
    var body: some View {
        ZStack {
            ForEach(["linked", "box", "pipe", "elevator", "door"], id: \.self) { f in
                UnlockParts(content: UnlockContent.of(FeatureID(f)), u: 5)
            }
        }
    }
}
