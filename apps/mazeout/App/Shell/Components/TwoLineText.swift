import SwiftUI
import PathCore

// A localised sentence on one or two balanced lines with one highlighted word (`SocTwoLines`, `SocHotLine`). Moved as it was
// from StreakRaceViews.swift in the kit decoupling step (docs/ROADMAP.md): the event pages, their (i) overlays and the booster
// popup (BoosterBuyPopup.descriptionLines) all set text with it, so it is shared chrome (ui-chrome), not the Streak Race's.
// The names keep their `Soc` prefix (and the skin tokens their `social.streakRaceViews` ids) so nothing else changes.

/// A localised sentence broken into centred lines at the word boundary that balances them, one word highlighted: `hot` (a
/// localised highlight word, e.g. "fail" / "kaybedersen") where it occurs, else the first word (SPEC-ui §2.16 (i); DECISION:
/// without a captured highlight the first word is lit in every language).
struct SocTwoLines: View {
    let text: LocalizedStringResource
    let centreX: CGFloat
    let baselines: [CGFloat]
    let box: CGFloat
    var size: CGFloat = 16
    var faceHex: UInt32 = Skin.socialStreakRaceViewsSocTwoLinesFaceHex
    var hotHex: UInt32 = Skin.socialStreakRaceViewsSocTwoLinesHotHex
    var outline: UInt32? = Skin.socialStreakRaceViewsSocTwoLinesOutline
    var hot: LocalizedStringResource? = nil
    /// Fill the first line up to `box` (the phone's breaks for most lines), instead of balancing the two lines.
    var greedy = false
    /// The greedy break width when it differs from the fit box (a first line that may run wider than the second fits).
    var breakAt: CGFloat? = nil
    /// Already-resolved text (numbers formatted without grouping, `SocText.plain`), used instead of `text` / `hot`.
    var resolved: String? = nil
    var hotResolved: String? = nil

    var body: some View {
        let full = resolved ?? String(localized: text)
        // B3: the highlight run is resolved first so a CJK break never falls inside it (LineUnits keep)
        let hotWord = hotResolved ?? hot.map { String(localized: $0) }
        let keep = hotWord.map { [$0] } ?? []
        let lines = greedy ? SocTwoLines.greedyOrBalanced(full, size: size, breakAt: breakAt ?? box, box: box, parts: baselines.count,
                                                          keep: keep)
                           : SocTwoLines.split(full, size: size, parts: baselines.count, keep: keep)
        let hotLine = hotWord.flatMap { h in lines.firstIndex { $0.localizedCaseInsensitiveContains(h) } } ?? 0
        ZStack(alignment: .topLeading) {
            ForEach(Array(lines.enumerated()), id: \.offset) { i, line in
                SocHotLine(line: line, hotWord: hotWord.map { line.localizedCaseInsensitiveContains($0) ? $0 : nil }
                               ?? (i == hotLine ? LineUnits.units(line).first?.text : nil),
                           centreX: centreX, baseline: baselines[min(i, baselines.count - 1)], size: size, box: box,
                           face: faceHex, hot: hotHex, outline: outline)
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: full))
    }

    /// The phone's greedy break while its second line still fits `box`; a longer translation (TR "Bir seviyede / kaybedersen
    /// mücadeleyi kaybedersin!") would shrink that second line, so it gets the balanced break instead.
    static func greedyOrBalanced(_ s: String, size: CGFloat, breakAt: CGFloat, box: CGFloat, parts: Int,
                                 keep: [String] = []) -> [String] {
        let g = greedy(s, size: size, box: breakAt, parts: parts, keep: keep)
        guard g.count > 1 else { return g }
        let second = GameTextLayout.make(g[1], postScriptName: GameText.blackPostScript, size: size, tracking: 0).advance
        return second > box ? split(s, size: size, parts: parts, keep: keep) : g
    }

    /// The first line takes as many words as fit in `box`, the rest go on the second.
    /// B3: words = `LineUnits` (the old space split for the space-separated languages; dictionary words in ja / zh-Hans).
    static func greedy(_ s: String, size: CGFloat, box: CGFloat, parts: Int, keep: [String] = []) -> [String] {
        let words = LineUnits.units(s, keep: keep)
        guard parts > 1, words.count > 1 else { return [s] }
        var n = 1
        while n < words.count - 0 {
            let w = GameTextLayout.make(LineUnits.join(words[..<(n + 1)]), postScriptName: GameText.blackPostScript,
                                        size: size, tracking: 0).advance
            if w > box || n + 1 == words.count { break }
            n += 1
        }
        return [LineUnits.join(words[..<n]), LineUnits.join(words[n...])]
    }

    /// Splits at the word boundary whose longest line is the shortest (at most `parts` lines, 1 or 2).
    static func split(_ s: String, size: CGFloat, parts: Int, keep: [String] = []) -> [String] {
        let words = LineUnits.units(s, keep: keep)
        guard parts > 1, words.count > 1 else { return [s] }
        func w(_ x: ArraySlice<TextUnit>) -> CGFloat {
            GameTextLayout.make(LineUnits.join(x), postScriptName: GameText.blackPostScript, size: size, tracking: 0).advance
        }
        var best: (CGFloat, [String]) = (.greatestFiniteMagnitude, [s])
        for i in 1..<words.count {
            let a = words[..<i], b = words[i...]
            let cost = max(w(a), w(b))
            if cost < best.0 { best = (cost, [LineUnits.join(a), LineUnits.join(b)]) }
        }
        return best.1
    }
}

/// One centred line, `hotWord` (if any, case-insensitive) in the highlight colour.
struct SocHotLine: View {
    let line: String
    let hotWord: String?
    let centreX: CGFloat
    let baseline: CGFloat
    let size: CGFloat
    let box: CGFloat
    let face: UInt32
    let hot: UInt32
    let outline: UInt32?

    var body: some View {
        let ow: CGFloat = outline == nil ? 0 : 1.0
        let dr: CGFloat = outline == nil ? 0 : 0.8
        let plain = GameTextStyle.s2(size, 0, [face], outline: outline, ow, drop: dr)
        let hotSt = GameTextStyle.s2(size, 0, [hot], outline: outline, ow, drop: dr)
        let r = hotWord.flatMap { line.range(of: $0, options: [.caseInsensitive]) }
        let parts: [(String, Bool)] = r.map { [(String(line[..<$0.lowerBound]), false), (String(line[$0]), true),
                                               (String(line[$0.upperBound...]), false)] } ?? [(line, false)]
        // advances that keep the spaces at the segment edges (GameTextLayout drops trailing whitespace)
        let spaceW = GameTextLayout.make("a a", postScriptName: plain.postScriptName, size: size, tracking: 0).advance
            - GameTextLayout.make("aa", postScriptName: plain.postScriptName, size: size, tracking: 0).advance
        let widths: [CGFloat] = parts.map { seg in
            let core = seg.0.trimmingCharacters(in: .whitespaces)
            let lead = seg.0.prefix { $0 == " " }.count, trail = seg.0.reversed().prefix { $0 == " " }.count
            let w = core.isEmpty ? 0 : GameTextLayout.make(core, postScriptName: plain.postScriptName, size: size, tracking: 0).advance
            return w + CGFloat(lead + trail) * spaceW
        }
        let total = widths.reduce(0, +)
        let fit = min(1, box / max(total, 1))
        let _ = FitLedger.note("socline", text: line, need: box / max(total, 1))
        let pa = plain.sized(size * fit), ph = hotSt.sized(size * fit)
        let x0 = centreX - total * fit / 2
        ZStack(alignment: .topLeading) {
            ForEach(Array(parts.enumerated()), id: \.offset) { i, p in
                let core = p.0.trimmingCharacters(in: .whitespaces)
                if !core.isEmpty {
                    let lead = CGFloat(p.0.prefix { $0 == " " }.count) * spaceW
                    let trail = CGFloat(p.0.reversed().prefix { $0 == " " }.count) * spaceW
                    let before = widths[..<i].reduce(0, +) + lead
                    let st = p.1 ? ph : pa
                    GameText(verbatim: core, style: st).at(x0 + (before + (widths[i] - lead - trail) / 2) * fit, st.capCentre(baseline: baseline))
                }
            }
        }
    }
}

extension SocTwoLines {
    /// B3: a description as one line while it fits `width` at ≥ 0.70, else the two-line break whose wider line is narrowest
    /// (the booster popup's body and the generic offer popup's; moved as it was from BoosterBuyPopup.descriptionLines, which
    /// forwards here). A two-line need is logged under FitLedger's "boosterBuy.desc2" key (`-pc.fitLog`), as before.
    static func descriptionLines(_ text: String, style: GameTextStyle, width: CGFloat) -> [String] {
        func adv(_ s: String) -> CGFloat {
            GameTextLayout.make(s, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking).advance
        }
        guard adv(text) * 0.70 > width else { return [text] }
        let two = SocTwoLines.split(text, size: style.size, parts: 2)
        let w = two.map(adv).max() ?? 0
        FitLedger.note("boosterBuy.desc2", text: text, need: width / max(w, 1))
        return two
    }
}
