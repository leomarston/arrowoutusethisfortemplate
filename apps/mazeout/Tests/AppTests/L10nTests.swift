import Foundation
import XCTest
import UIKit
import CoreText
import SwiftUI
@testable import ArrowOut

/// B3 L10N-APP (PLAN-P §4.4, gate G7; SPEC.md ruling 37a: 13 locales, ruling 38: a bold fallback font chain).
///  1. The BUILT app carries all 13 languages: every catalogue row resolves in every .lproj to its table value
///     (strings.tsv for EN/TR, App/Resources/Strings/l10n/strings.<lang>.tsv for the other 11).
///  2. Argument types and ORDER agree with the English key in every language (2+ arguments spell their positions).
///  3. Honesty in every language: no copy claims an online world, multiplayer, bots, friends or simulated players.
///  4. The bold cascade (GameText.swift `FontCascade`): every script of the shipped name bank and of the 13 languages is drawn
///     by PC Display or a heavy cascade face — never the LastResort box — and the outline follows the fallback glyphs.
///  5. LineUnits: the space-separated languages break exactly where the old word split did; Japanese / Chinese break by the
///     kinsoku rules; `**` runs and highlight runs never break.
///  6. Every unlock card, in every language, fits its 272 pt box in ≤ 2 lines at ≥ 0.70 and lights its term.
///  7. FIT (the generalised tr_review rule — ink width, floor 0.70 — with exact LineUnits breaks instead of tr_review's
///     width / lines x 1.12): every measured layout of tools/strings/fit_frames.json in every language, with the app's
///     cascade face for that language, needs a scale ≥ 0.70; the Country tab label (the app's own advance rule) of every region
///     in every language fits its 100 pt box at ≥ 0.70. Evidence: Documents/b3-evidence/fit.json (copied to build/p/B3).
final class L10nTests: XCTestCase {
    static let languages = ["en", "tr", "de", "fr", "es", "it", "pt-BR", "ja", "ko", "zh-Hans", "pl", "sk", "sl"]
    static let tables = ["de", "fr", "es", "it", "pt-BR", "ja", "ko", "zh-Hans", "pl", "sk", "sl"]

    /// key → language → value, from the TSVs (the source the catalogue is built from).
    static func table() throws -> (keys: [String], values: [String: [String: String]]) {
        let (rows, problems) = try V1Strings.merged()
        XCTAssertEqual(problems, [])
        var values: [String: [String: String]] = [:]
        for r in rows { values[r.en] = ["en": V1Strings.english(r.en), "tr": r.tr] }     // FIX-2 B: keys.tsv identifier keys
        for lang in tables {
            let rel = "App/Resources/Strings/l10n/strings.\(lang).tsv"
            let lines = try V1Repo.text(rel).components(separatedBy: "\n")
            XCTAssertEqual(lines.first, "en\t\(lang)\tnote", rel)
            for line in lines.dropFirst() where !line.isEmpty && !line.hasPrefix("#") {
                let c = line.components(separatedBy: "\t")
                guard c.count == 3 else { XCTFail("\(rel): \(c.count) columns: \(line.prefix(60))"); continue }
                values[V1Strings.unescape(c[0]), default: [:]][lang] = V1Strings.unescape(c[1])
            }
        }
        return (rows.map(\.en), values)
    }

    static func evidence(_ text: String, _ name: String) {
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
        let dir = docs.appendingPathComponent("b3-evidence", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try? text.write(to: dir.appendingPathComponent(name), atomically: true, encoding: .utf8)
    }

    // MARK: 1. the built catalogue in 13 languages

    func testEveryRowIsInTheBuiltCatalogueInAll13Languages() throws {
        let (keys, values) = try Self.table()
        XCTAssertGreaterThan(keys.count, 200)
        let sentinel = "\u{1}MISSING\u{1}"
        var missing: [String] = [], wrong: [String] = []
        for lang in Self.languages {
            guard let b = V1Bundle.lproj(lang) else { XCTFail("\(lang).lproj is not in the app"); continue }
            for k in keys {
                guard let want = values[k]?[lang] else { missing.append("\(lang) \(k.debugDescription) (no table row)"); continue }
                let got = b.localizedString(forKey: k, value: sentinel, table: nil)
                if got == sentinel { missing.append("\(lang) \(k.debugDescription)"); continue }
                if V1Format.canonical(got) != V1Format.canonical(want) {
                    wrong.append("\(lang) \(k.debugDescription): bundle \(got.debugDescription) ≠ table \(want.debugDescription)")
                }
            }
        }
        v1Attach("catalogue-13", "missing \(missing.count)\n\(missing.joined(separator: "\n"))\nwrong \(wrong.count)\n\(wrong.joined(separator: "\n"))")
        XCTAssertEqual(missing, [], "rows absent from a built .lproj (Localizable.xcstrings not rebuilt by tools/strings/build.py?)")
        XCTAssertEqual(wrong, [], "a built value differs from its table")
        let locs = Set(Bundle.main.localizations)
        XCTAssertTrue(Set(Self.languages).isSubset(of: locs), "Bundle.main.localizations \(locs.sorted())")
    }

    // MARK: 2. argument order

    func testArgumentTypesAndOrderAgreeInEveryLanguage() throws {
        let (keys, _) = try Self.table()
        var bad: [String] = []
        var checked = 0
        for lang in Self.languages {
            guard let b = V1Bundle.lproj(lang) else { XCTFail("\(lang).lproj"); continue }
            for k in keys {
                let v = b.localizedString(forKey: k, value: nil, table: nil)
                let want = V1Format.resolvedTypes(k), got = V1Format.resolvedTypes(v)
                if want?.isEmpty == false { checked += 1 }
                if want != got { bad.append("\(lang) \(k.debugDescription) → \(v.debugDescription): \(String(describing: got)) vs \(String(describing: want))") }
                let a = V1Format.args(v)
                // the EN value IS the key (same order by definition); every translation with 2+ arguments spells positions
                if v != k && a.count >= 2 && a.contains(where: { $0.position == nil }) {
                    bad.append("\(lang) \(v.debugDescription): 2+ arguments without positions (%1$@)")
                }
            }
        }
        XCTAssertGreaterThan(checked, 13 * 20)
        XCTAssertEqual(bad, [])
    }

    // MARK: 3. honesty

    static let honesty: [String: [String]] = {
        let all = ["simul", "symul", "online", "on-line", "multiplayer", "multi-player", "bot ", "bots", "friend"]
        let per: [String: [String]] = [
            "tr": ["simüle", "çevrimiçi", "arkadaş", "çok oyunculu"], "de": ["freund", "mehrspieler"],
            "fr": ["en ligne", "multijoueur"], "es": ["en línea", "amigo", "multijugador"], "it": ["in linea", "multigiocatore"],
            "pt-BR": ["amigo", "multijogador"], "ja": ["オンライン", "シミュレ", "マルチ", "ボット", "友達", "友だち", "フレンド", "対戦"],
            "ko": ["온라인", "시뮬", "멀티", "봇", "친구"], "zh-Hans": ["在线", "联网", "模拟", "多人", "机器人", "好友", "朋友"],
            "pl": ["znajom", "przyjaci", "wieloosob"], "sk": ["priatel", "kamarát"], "sl": ["prijatelj", "večigral"],
        ]
        var out: [String: [String]] = [:]
        for l in L10nTests.languages { out[l] = all + (per[l] ?? []) }
        return out
    }()

    func testNoLanguageClaimsAnOnlineWorld() throws {
        let (keys, _) = try Self.table()
        var hits: [String] = []
        for lang in Self.languages {
            guard let b = V1Bundle.lproj(lang) else { continue }
            for k in keys {
                let v = b.localizedString(forKey: k, value: nil, table: nil).lowercased()
                for w in Self.honesty[lang] ?? [] where v.contains(w.lowercased()) { hits.append("\(lang) \(w.debugDescription) in \(v.debugDescription)") }
                if lang == "fr", v.range(of: #"\bami(e|s|es)?\b"#, options: .regularExpression) != nil { hits.append("fr 'ami' in \(v)") }
                if lang == "it", v.range(of: #"\bamic[oaie]\b"#, options: .regularExpression) != nil { hits.append("it 'amico' in \(v)") }
            }
        }
        XCTAssertEqual(hits, [], "OWNER 10:35 / ruling 38: the social world is on the device; no copy may claim otherwise")
    }

    // MARK: 4. the bold cascade

    /// (sample, a substring of the PostScript name of the face that must draw its non-Latin glyphs; "" = any heavy face)
    static let scriptSamples: [(String, String)] = [
        ("連勝ラッシュ", "Hira"), ("さくら", "Hira"), ("王伟", "PingFang"), ("하늘 높이", "SDGothic"), ("Γιώργος", ""), ("محمد", ""),
        ("علی‌رضا", ""), ("דוד", ""), ("สมชาย", "Thonburi"), ("Արամ", ""), ("გიორგი", ""),
        ("Иван", "PCDisplay-Black"), ("Nguyễn", "PCDisplay-Black"),
    ]

    /// The faces CoreText draws `text` with (the app's cascade for `lang`) and their weight traits (Bold ≈ 0.4, Heavy ≈
    /// 0.56, Black ≈ 0.62), read from the run fonts themselves (the system's heavy cuts have private names).
    static func runFaces(_ text: String, lang: String = "en") -> [(name: String, weight: CGFloat)] {
        let face = FontCascade.face(for: text, language: lang)
        let font = FontCascade.font(GameText.blackPostScript, 20, face: face)
        var attrs: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font]
        if let l = FontCascade.language(for: text, face: face) { attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = l }
        let line = CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: attrs))
        var out: [(String, CGFloat)] = []
        for run in CTLineGetGlyphRuns(line) as! [CTRun] {
            let f = (CTRunGetAttributes(run) as NSDictionary)[kCTFontAttributeName as String] as! CTFont
            let name = CTFontCopyPostScriptName(f) as String
            let w = ((CTFontCopyTraits(f) as NSDictionary)[kCTFontWeightTrait as String] as? NSNumber).map { CGFloat($0.doubleValue) } ?? 0
            if !out.contains(where: { $0.0 == name }) { out.append((name, w)) }
        }
        return out
    }

    func testTheBoldCascadeDrawsEveryScriptWithAHeavyFace() {
        var bad: [String] = [], report: [String] = []
        for (s, want) in Self.scriptSamples {
            let l = GameTextLayout.make(s, postScriptName: GameText.blackPostScript, size: 20, tracking: 0)
            let faces = Self.runFaces(s)
            let fallback = faces.map(\.name).filter { $0 != GameText.blackPostScript }
            report.append("\(s)\t" + faces.map { "\($0.name) \($0.weight)" }.joined(separator: ","))
            if l.runFonts.contains(where: { $0.lowercased().contains("lastresort") }) { bad.append("\(s): LastResort") }
            if l.glyphCount < s.unicodeScalars.filter({ !$0.properties.isWhitespace }).count / 2 { bad.append("\(s): \(l.glyphCount) glyphs") }
            if want == GameText.blackPostScript {
                if !fallback.isEmpty { bad.append("\(s): PC Display draws it, not \(fallback)") }
                continue
            }
            if fallback.isEmpty { bad.append("\(s): no fallback face") }
            if fallback.count > 1 { bad.append("\(s): one name, two faces \(fallback)") }
            if !want.isEmpty && !fallback.contains(where: { $0.contains(want) }) { bad.append("\(s): drawn with \(fallback), want *\(want)*") }
            // Bold or heavier (Thonburi / Apple SD Gothic Neo stop at Bold on iOS; the rest come in Heavy / Black / W8)
            for f in faces where f.name != GameText.blackPostScript && f.weight < 0.39 { bad.append("\(s): \(f.name) is light (weight \(f.weight))") }
        }
        Self.evidence(report.joined(separator: "\n"), "script-faces.tsv")
        XCTAssertEqual(bad, [])
        // the per-string CJK order: kana → Japanese, Hangul → Korean, Han only → Chinese outside a Japanese UI
        XCTAssertEqual(FontCascade.face(for: "さくら", language: "en"), .ja)
        XCTAssertEqual(FontCascade.face(for: "민준", language: "ja"), .ko)
        XCTAssertEqual(FontCascade.face(for: "王伟", language: "en"), .zh)
        XCTAssertEqual(FontCascade.face(for: "設定", language: "ja"), .ja, "a Japanese UI word in kanji only is Japanese")
        XCTAssertEqual(FontCascade.face(for: "张伟", language: "ja"), .zh, "Hiragino lacks 张: the name stays in one face")
        // the named public faces stay in the chain behind the system's Black cascade (Greek first among them)
        XCTAssertEqual(Array(FontCascade.names(.ja).prefix(4)), ["HelveticaNeue-Bold", "HiraginoSans-W8", "PingFangSC-Semibold", "AppleSDGothicNeo-Bold"])
        XCTAssertEqual(Array(FontCascade.names(.zh).prefix(3)), ["HelveticaNeue-Bold", "PingFangSC-Semibold", "HiraginoSans-W8"])
        XCTAssertGreaterThan(FontCascade.cascade(.zh).count, FontCascade.names(.zh).count, "the system's Black cascade leads the chain")
    }

    /// Every character of the shipped name bank (the native-script first names of B2's v2 world) is drawn by PC Display or a
    /// cascade / system face — none by the LastResort box. Only counts and faces are reported (never the names).
    func testEveryNameBankCharacterHasAGlyph() throws {
        let data = try Data(contentsOf: V1Repo.url("App/Resources/Social/social_names.json"))
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        var chars = Set<Character>()
        func walk(_ x: Any) {
            if let s = x as? String { for c in s where c.unicodeScalars.first!.value >= 0x250 { chars.insert(c) } }
            else if let a = x as? [Any] { a.forEach(walk) }
            else if let d = x as? [String: Any] { d.values.forEach(walk) }
        }
        for (k, v) in json where !k.hasPrefix("block") { walk(v) }
        XCTAssertGreaterThan(chars.count, 500, "the v2 bank carries native scripts")
        var faces: [String: Int] = [:]
        var lastResort = 0
        var weights: [String: CGFloat] = [:]
        for c in chars {
            let l = GameTextLayout.make(String(c), postScriptName: GameText.blackPostScript, size: 20, tracking: 0)
            for f in l.runFonts { faces[f, default: 0] += 1 }
            for f in Self.runFaces(String(c)) { weights[f.name] = f.weight }
            if l.runFonts.contains(where: { $0.lowercased().contains("lastresort") }) { lastResort += 1 }
        }
        Self.evidence(faces.sorted { $0.key < $1.key }.map { "\($0.key)\t\($0.value)\tweight \(weights[$0.key] ?? -1)" }.joined(separator: "\n"), "namebank-faces.tsv")
        XCTAssertEqual(lastResort, 0, "characters with no glyph in any face: \(lastResort)")
        let light = faces.keys.filter { $0 != GameText.blackPostScript && (weights[$0] ?? 0) < 0.39 }
        XCTAssertEqual(light, [], "a native-script name drawn in a light face next to PC Display Black")
    }

    func testTheOutlineFollowsTheFallbackGlyphs() {
        let plain = GameTextStyle(size: 30, fill: [.white])
        let outlined = GameTextStyle(size: 30, fill: [.white], outline: Color(red: 0, green: 0, blue: 0.5), outlineWidth: 2.5, drop: 2)
        for s in ["連勝", "하늘", "直上", "Γιώργος", "محمد"] {
            let l = GameTextLayout.make(s, postScriptName: GameText.blackPostScript, size: 30, tracking: 0)
            XCTAssertGreaterThan(l.inkBounds.width, 20, "\(s): the fallback glyphs are paths")
            let size = CGSize(width: l.advance + 20, height: 60)
            let a = GameTextRaster.render(l, style: plain, size: size, origin: CGPoint(x: 10, y: 42), scale: 2)
            let b = GameTextRaster.render(l, style: outlined, size: size, origin: CGPoint(x: 10, y: 42), scale: 2)
            let na = Self.opaque(a), nb = Self.opaque(b)
            XCTAssertGreaterThan(na, 200, s)
            XCTAssertGreaterThan(Double(nb), Double(na) * 1.25, "\(s): the outline + drop are drawn around the fallback glyphs (\(na) → \(nb) px)")
        }
    }

    static func opaque(_ img: CGImage?) -> Int {
        guard let img, let data = img.dataProvider?.data, let p = CFDataGetBytePtr(data) else { return 0 }
        let bpp = img.bitsPerPixel / 8, row = img.bytesPerRow
        var n = 0
        for y in 0..<img.height { for x in 0..<img.width where p[y * row + x * bpp + 3] > 128 { n += 1 } }
        return n
    }

    // MARK: 5. line units

    func testLineUnitsKeepTheOldWordSplitAndBreakCJKByKinsoku() throws {
        // the space-separated languages: exactly the old split(separator: " ")
        for s in ["Pass arrows through the PIPE to break it!", "Bir seviyede kaybedersen yere geri düşersin!", "연결 화살표는 함께 움직여요!"] {
            XCTAssertEqual(LineUnits.units(s).map(\.text), s.split(separator: " ").map(String.init), s)
            XCTAssertEqual(LineUnits.join(LineUnits.units(s)), s)
        }
        let ja = "レベルに失敗すると倍率がx1に戻ります！"
        let u = LineUnits.units(ja, language: "ja")
        XCTAssertGreaterThan(u.count, 2, "\(u.map(\.text))")
        XCTAssertEqual(LineUnits.join(u), ja)
        XCTAssertTrue(u.allSatisfy { !$0.space })
        for x in u.dropFirst() {
            XCTAssertFalse(LineUnits.noStart.contains(x.text.first!), "a unit starts with a closing mark: \(u.map(\.text))")
            XCTAssertFalse(x.text.allSatisfy { ("\u{3041}"..."\u{309F}").contains($0) }, "a particle stands alone: \(u.map(\.text))")
        }
        XCTAssertTrue(u.map(\.text).contains { $0.contains("x1") }, "digits and Latin stay together")
        // ** runs and highlight runs never break
        let card = LineUnits.units("必要な数の矢印を消して**ボックス**を壊そう！", language: "ja")
        XCTAssertTrue(card.contains { $0.text.contains("**ボックス**") }, "\(card.map(\.text))")
        let zh = LineUnits.units("一旦闯关失败，就会跌回地面！", keep: ["失败"], language: "zh-Hans")
        XCTAssertTrue(zh.contains { $0.text.contains("失败") }, "\(zh.map(\.text))")
        XCTAssertFalse(zh.contains { $0.text.hasPrefix("，") || $0.text.hasPrefix("！") })
        // every value of every language round-trips (no double spaces)
        let (keys, values) = try Self.table()
        for k in keys { for (lang, v) in values[k] ?? [:] {
            XCTAssertEqual(LineUnits.join(LineUnits.units(v, language: lang)), v, "\(lang) \(v)")
        } }
    }

    // MARK: 6. unlock cards

    static let unlockCards = ["LINKED ARROWS move together!", "Clear required amount of arrows to break the BOX!",
                              "Pass arrows through the PIPE to break it!", "Clear all arrows on the ELEVATOR to activate it!",
                              "Collect the KEY to open the DOOR!", "Arrows turn when they hit the CORNER!"]

    /// FIX-2 B review (F-16): each card is fitted in the line box the app gives ITS feature (`UnlockCardLines.width`, the
    /// same call UnlockCard makes: the Corner card 285 pt, the others 272 pt) — the feature read from the shipped
    /// Levels/unlocks.json, so every language's Corner card is measured at the width it ships with, and no line may exceed it.
    func testEveryUnlockCardFitsAndLightsItsTermInEveryLanguage() throws {
        let style = GameTextStyle.s2(22.3, -0.66, [0x231C67])
        struct Row: Decodable { let feature: String; let card: String }
        struct File: Decodable { let unlocks: [Row] }
        let url = try XCTUnwrap(Bundle.main.url(forResource: "unlocks", withExtension: "json", subdirectory: "Levels"))
        let feature = Dictionary(uniqueKeysWithValues: try JSONDecoder().decode(File.self, from: Data(contentsOf: url)).unlocks.map { ($0.card, $0.feature) })
        XCTAssertEqual(Set(feature.keys), Set(Self.unlockCards), "the six cards are the shipped unlocks")
        XCTAssertEqual(UnlockCardLines.width(feature: feature[Self.unlockCards[5]] ?? "", base: 272), 285, "the Corner card's box")
        var bad: [String] = []
        for lang in Self.languages {
            guard let b = V1Bundle.lproj(lang) else { continue }
            for card in Self.unlockCards {
                let text = b.localizedString(forKey: card, value: nil, table: nil)
                let box = UnlockCardLines.width(feature: try XCTUnwrap(feature[card], card), base: 272)
                let fit = UnlockCardLines.fitUnits(text, style: style, width: box)
                if fit.lines.count > 2 || fit.scale < 0.70 { bad.append("\(lang) \(text): \(fit.lines.count) lines at \(fit.scale)") }
                XCTAssertEqual(fit.lines.flatMap { $0 }.map(\.text).joined(), LineUnits.units(text).map(\.text).joined(), "no unit lost")
                let st = style.sized(style.size * fit.scale)
                for line in fit.lines {
                    let w = GameTextLayout.make(LineUnits.plain(LineUnits.join(line)), postScriptName: st.postScriptName,
                                                size: st.size, tracking: st.tracking).advance
                    if w > box + 0.5 { bad.append("\(lang) '\(LineUnits.join(line))' is \(w) pt (box \(box))") }
                }
                let lit = fit.lines.flatMap { MultiRunText.runs($0) }.filter { $0.1 }.map { $0.0 }
                if lit.isEmpty { bad.append("\(lang) \(text): no term lit") }
                if lit.contains(where: { $0.contains("*") }) { bad.append("\(lang) \(text): a marker is drawn \(lit)") }
            }
        }
        XCTAssertEqual(bad, [])
    }

    // MARK: 6b. the fallback layouts B3 added for the long languages

    /// The booster popup's "Buy" + "x3" group, its description, the Hot Streak lettering and the two-line Rocket badge hold
    /// the 0.70 floor in every language (the in-app sweep found them: FitLedger), and EN/TR keep their old drawing.
    func testTheLongLanguageFallbacksHoldTheFloorInEveryLanguage() {
        let buy = GameTextStyle.s2(35.5, -0.92, [0xFFFCED], outline: 0x066A01, 1.52, drop: 1.84)
        let count = GameTextStyle.s2(24.0, -0.6, [0xFFFCED], outline: 0x066A01, 1.3, drop: 1.2)
        let line = GameTextStyle.s2(21, -0.6, [0x622100])
        let streak = GameTextStyle.s2(41, -2.6, [0xFFD21A], outline: 0x0A2F9E, 3.0, drop: 2.8, face: .blackItalic)
        let race = GameTextStyle.s2(41, -2.6, [0xFFFFFF], outline: 0x0A2F9E, 3.0, drop: 2.8, face: .blackItalic)
        var bad: [String] = []
        for lang in Self.languages {
            guard let b = V1Bundle.lproj(lang) else { continue }
            func loc(_ k: String) -> String { b.localizedString(forKey: k, value: nil, table: nil) }
            // Buy x3: one scale for both, ≥ 0.70 (EN/TR/most: 1)
            let fa = GameTextLayout.make(loc("Buy"), postScriptName: buy.postScriptName, size: buy.size, tracking: buy.tracking)
            let fb = GameTextLayout.make("x3", postScriptName: count.postScriptName, size: count.size, tracking: count.tracking)
            func half(_ l: GameTextLayout) -> CGFloat { max(l.advance / 2, l.advance / 2 - l.inkBounds.minX, l.inkBounds.maxX - l.advance / 2) }
            let need = (118 - 10) / max(2 * (half(fa) + buy.outlineWidth) + 2 * (half(fb) + count.outlineWidth), 1)
            if need < 0.70 { bad.append("\(lang) Buy x3 '\(loc("Buy"))' needs \(need)") }
            XCTAssertGreaterThanOrEqual(BoosterBuyPopup.groupScale(loc("Buy"), "x3", buy: buy, count: count, width: 118), 0.70)
            if lang == "en" || lang == "tr" { XCTAssertEqual(BoosterBuyPopup.groupScale(loc("Buy"), "x3", buy: buy, count: count, width: 118), 1) }
            // the booster descriptions: one line or two, every line ≥ 0.70 of 262 pt
            for k in ["Freeze the timer for 10 seconds!", "Find an arrow that can move!"] {
                let lines = BoosterBuyPopup.descriptionLines(loc(k), style: line, width: 262)
                XCTAssertLessThanOrEqual(lines.count, 2)
                if lang == "en" || lang == "tr" { XCTAssertEqual(lines, [loc(k)], "EN/TR keep one line") }
                for l in lines {
                    let w = GameTextLayout.make(l, postScriptName: line.postScriptName, size: line.size, tracking: line.tracking).advance
                    if 262 / w < 0.70 { bad.append("\(lang) '\(l)' needs \(262 / w)") }
                }
            }
            // the Hot Streak lettering on the strip (233.5 pt frame, the flags leave 173.5 pt)
            let units = LineUnits.units(loc("Hot Streak"))
            let w1 = units.first?.text ?? "", w2 = LineUnits.join(units.dropFirst())
            if let k = StreakRaceLettering.joint(w1, w2, streak: streak, race: race, avail: 173.5) {
                let a0 = GameTextLayout.make(w1, postScriptName: streak.postScriptName, size: 41, tracking: -2.6).advance
                let b0 = w2.isEmpty ? 0 : GameTextLayout.make(w2, postScriptName: race.postScriptName, size: 41, tracking: -2.6).advance
                if 173.5 / (a0 + b0) < 0.70 { bad.append("\(lang) Hot Streak lettering needs \(173.5 / (a0 + b0)) (k \(k))") }
            }
            if lang == "en" || lang == "tr" {
                XCTAssertNil(StreakRaceLettering.joint(w1, w2, streak: streak, race: race, avail: 173.5), "EN/TR keep the per-word boxes")
            }
        }
        XCTAssertEqual(bad, [])
        // the two-line Rocket badge: a one-word hyphenated name breaks after its hyphen; EN keeps its two words
        XCTAssertTrue(SocEventLogo.words(LineUnits.units("Raketen-Rallye"), full: "Raketen-Rallye", twoLines: true) == ("Raketen-", "Rallye"))
        XCTAssertTrue(SocEventLogo.words(LineUnits.units("Rocket Rally"), full: "Rocket Rally", twoLines: true) == ("Rocket", "Rally"))
        XCTAssertTrue(SocEventLogo.words(LineUnits.units("Raketen-Rallye"), full: "Raketen-Rallye", twoLines: false) == ("Raketen-Rallye", ""))
    }

    // MARK: 7. fit in every language (exact breaks)

    /// The advance of `text` as GameTextLayout lays it out in an app running in `lang` (the same cascade face choice).
    static func advance(_ text: String, size: CGFloat, tracking: CGFloat, lang: String) -> (CGFloat, [String]) {
        let face = FontCascade.face(for: text, language: lang)
        let font = FontCascade.font(GameText.blackPostScript, size, face: face)
        var attrs: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font,
                                                    NSAttributedString.Key(kCTKernAttributeName as String): tracking]
        if FontCascade.scripts(text).cjk { attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = face == .ja ? "ja" : face == .ko ? "ko" : "zh-Hans" }
        else if lang == "tr" { attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = "tr" }
        let line = CTLineCreateWithAttributedString(NSAttributedString(string: text.isEmpty ? " " : text, attributes: attrs))
        let typo = CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil))
        var fonts = Set<String>()
        for run in CTLineGetGlyphRuns(line) as! [CTRun] {
            let a = CTRunGetAttributes(run) as NSDictionary
            if let f = a[kCTFontAttributeName as String] { fonts.insert(CTFontCopyPostScriptName(f as! CTFont) as String) }
        }
        return (max(0, typo - CGFloat(CTLineGetTrailingWhitespaceWidth(line)) - (text.isEmpty ? 0 : tracking)), fonts.sorted())
    }

    /// The INK width of `text` (tr_review's rule: CoreText glyph-path bounds, not the advance), same face choice as `advance`.
    static func inkWidth(_ text: String, size: CGFloat, tracking: CGFloat, lang: String) -> (CGFloat, [String]) {
        let face = FontCascade.face(for: text, language: lang)
        let font = FontCascade.font(GameText.blackPostScript, size, face: face)
        var attrs: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font,
                                                    NSAttributedString.Key(kCTKernAttributeName as String): tracking]
        if FontCascade.scripts(text).cjk { attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = face == .ja ? "ja" : face == .ko ? "ko" : "zh-Hans" }
        else if lang == "tr" { attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = "tr" }
        let line = CTLineCreateWithAttributedString(NSAttributedString(string: text.isEmpty ? " " : text, attributes: attrs))
        var x0 = CGFloat.infinity, x1 = -CGFloat.infinity
        var fonts = Set<String>()
        for run in CTLineGetGlyphRuns(line) as! [CTRun] {
            let rf = (CTRunGetAttributes(run) as NSDictionary)[kCTFontAttributeName as String] as! CTFont
            fonts.insert(CTFontCopyPostScriptName(rf) as String)
            let n = CTRunGetGlyphCount(run)
            var g = [CGGlyph](repeating: 0, count: n), pos = [CGPoint](repeating: .zero, count: n)
            CTRunGetGlyphs(run, CFRange(location: 0, length: n), &g)
            CTRunGetPositions(run, CFRange(location: 0, length: n), &pos)
            for i in 0..<n {
                guard let p = CTFontCreatePathForGlyph(rf, g[i], nil) else { continue }
                let b = p.boundingBoxOfPath
                if b.isNull || b.width == 0 { continue }
                x0 = min(x0, pos[i].x + b.minX); x1 = max(x1, pos[i].x + b.maxX)
            }
        }
        return (x1 > x0 ? x1 - x0 : 0, fonts.sorted())
    }

    static func ink(_ s: String) -> String {
        var t = s.replacingOccurrences(of: #"%(\d+\$)?lld"#, with: "100", options: .regularExpression)
        t = t.replacingOccurrences(of: #"%(\d+\$)?@"#, with: "Turkey", options: .regularExpression)
        return LineUnits.plain(t)
    }

    /// The narrowest widest line over every break of `units` into `n` lines (n = 1, 2 or 3).
    static func widest(_ units: [TextUnit], lines n: Int, _ w: (String) -> CGFloat) -> (CGFloat, [String]) {
        let full = LineUnits.join(units)
        if n <= 1 || units.count < 2 { return (w(full), [full]) }
        var best: (CGFloat, [String]) = (w(full), [full])
        for i in 1..<units.count {
            if n == 2 {
                let a = LineUnits.join(units[..<i]), b = LineUnits.join(units[i...])
                let c = max(w(a), w(b))
                if c < best.0 { best = (c, [a, b]) }
            } else {
                for j in (i + 1)..<max(i + 2, units.count) where j < units.count {
                    let p = [LineUnits.join(units[..<i]), LineUnits.join(units[i..<j]), LineUnits.join(units[j...])]
                    let c = p.map(w).max() ?? 0
                    if c < best.0 { best = (c, p) }
                }
            }
        }
        return best
    }

    func testEveryMeasuredLayoutFitsInEveryLanguage() throws {
        let data = try Data(contentsOf: V1Repo.url("tools/strings/fit_frames.json"))
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let frames = try XCTUnwrap(json["frames"] as? [[String: Any]])
        XCTAssertGreaterThan(frames.count, 150)
        var rows: [[String: Any]] = [], fails: [String] = []
        for lang in Self.languages {
            guard let b = V1Bundle.lproj(lang) else { XCTFail(lang); continue }
            for f in frames {
                let key = f["key"] as! String, id = f["id"] as! String
                let size = CGFloat(f["size"] as! Double), track = CGFloat(f["track"] as! Double), box = CGFloat(f["box"] as! Double)
                let n = f["lines"] as! Int
                let text = Self.ink(b.localizedString(forKey: key, value: nil, table: nil))
                var fonts = Set<String>()
                let measure: (String) -> CGFloat = { s in let (a, fs) = Self.inkWidth(s, size: size, tracking: track, lang: lang); fonts.formUnion(fs); return a }
                let (w, lines) = Self.widest(LineUnits.units(text, language: lang), lines: n, measure)
                let scale = min(1, box / max(w, 0.01))
                rows.append(["lang": lang, "frame": id, "key": key, "text": text, "box": box, "lines": lines, "scale": (scale * 1000).rounded() / 1000,
                             "fonts": fonts.sorted()])
                if scale < 0.70 { fails.append("\(lang) \(id) '\(text)' \(String(format: "%.3f", scale)) (\(lines))") }
            }
        }
        // the Country tab (B2 CountryName.label: the region's name in the app's language, a curated short name when it would
        // shrink below 0.7, else the ISO code) for every region iOS reports, in every language
        let short = (try? JSONSerialization.jsonObject(with: Data(contentsOf: V1Repo.url("App/Resources/Tuning/ui.json"))) as? [String: Any])
            .flatMap { ($0["lb"] as? [String: Any])?["countryShort"] as? [String: Any] }
        XCTAssertNotNil(short, "ui.json lb.countryShort")
        // the BOARDS a player can have (B2's v2 table: the tab names the board's country; a region code plays on the board
        // of design/social/data_v2/regions_v2.tsv — IC → ES), every one in every language
        func tsv(_ rel: String) throws -> [[String]] {
            try V1Repo.text(rel).components(separatedBy: "\n").filter { !$0.isEmpty && !$0.hasPrefix("#") }.map { $0.components(separatedBy: "\t") }
        }
        let boards = Set(try tsv("design/social/data_v2/countries_v2.tsv").map { $0[0] }).sorted()
        var boardOf: [String: String] = [:]
        for r in try tsv("design/social/data_v2/regions_v2.tsv") where r.count >= 3 { boardOf[r[0]] = r[2] }
        XCTAssertGreaterThan(boards.count, 150)
        var country: [[String: Any]] = [], isoFallback: [String] = []
        let focus = ["SK", "SI", "CN", "JP", "KR", "TR", "XK", "IC"]
        for lang in Self.languages {
            for code in boards {
                let label = Self.countryLabel(code, lang: lang, short: short)
                let (w, _) = Self.advance(label, size: 23, tracking: -0.4, lang: lang)
                let scale = min(1, 100 / max(w, 0.01))
                if scale < 0.70 { fails.append("\(lang) country \(code) '\(label)' \(String(format: "%.3f", scale))") }
                // the ISO code where lb.countryShort gives none (B2's last resort), not a curated short that IS the code ("NZ")
                if label == code && CountryName.short(code, language: lang, table: short) == nil {
                    let name = CountryName.name(code, language: lang)
                    let need = 100 / max(Self.advance(name, size: 23, tracking: -0.4, lang: lang).0, 0.01)
                    isoFallback.append("\(lang) \(code) \(name) needs \(String(format: "%.2f", need))")
                }
            }
            for region in focus {
                let board = boardOf[region] ?? region
                let label = Self.countryLabel(board, lang: lang, short: short)
                let (w, fonts) = Self.advance(label, size: 23, tracking: -0.4, lang: lang)
                country.append(["lang": lang, "region": region, "board": board, "label": label,
                                "scale": (min(1, 100 / max(w, 0.01)) * 1000).rounded() / 1000, "fonts": fonts])
            }
        }
        let out: [String: Any] = ["about": "B3 fit sweep (Tests/AppTests/L10nTests.swift): every layout of tools/strings/fit_frames.json x 13 languages, the app's cascade face, exact LineUnits breaks; the Country tab label of every region x 13 languages",
                                  "floor": 0.70, "failures": fails, "frames": rows, "country": country, "countryIsoFallback": isoFallback]
        if let d = try? JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .sortedKeys]) {
            Self.evidence(String(decoding: d, as: UTF8.self), "fit.json")
        }
        v1Attach("fit-failures", fails.joined(separator: "\n"))
        XCTAssertEqual(fails, [], "layouts below the 0.70 floor (SPEC.md §5.14)")
    }

    /// CountryName.label for a language other than the test host's (the same rule, measured with that language's face).
    static func countryLabel(_ code: String, lang: String, short: [String: Any]?) -> String {
        let name = CountryName.name(code, language: lang)
        let (w, _) = advance(name, size: 23, tracking: -0.4, lang: lang)
        guard w * 0.7 > 100 else { return name }
        return CountryName.short(code, language: lang, table: short) ?? code
    }
}
