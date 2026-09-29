import Foundation
import XCTest
import PathCore
@testable import ArrowOut

/// VERIFY V1 (SPEC-architecture §12.2 V1 `TuningTests`; SPEC.md §5.21-22, §5.29-32; design/CONSISTENCY.md §20). The six
/// Tuning files the BUILT app ships parse, load through the app's own readers (Tuning.load, RulesTuning.load,
/// EconomyRules.load — the calls AppModel makes at boot) without problems, and carry the RULED values; the frozen compiled
/// fallbacks agree where a ruling moved them (UnlockBeats, lives 1800). ScaffoldTests (WP0 → V1) keeps the per-key
/// bundled-vs-compiled comparison; this suite pins the rulings themselves.
final class TuningTests: XCTestCase {

    private var tuning: Tuning { Tuning.load(bundle: .main) }

    private func json(_ name: String) throws -> [String: Any] {
        let url = try XCTUnwrap(Bundle.main.url(forResource: name, withExtension: "json", subdirectory: "Tuning"), name)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any], "\(name).json is an object")
    }

    func testTheSixFilesShipParseAndLoad() throws {
        for name in Tuning.fileNames { _ = try json(name) }
        XCTAssertEqual(Set(tuning.loadedFiles), Set(Tuning.fileNames))
        let (_, ruleProblems) = RulesTuning.load(json: tuning.rules.data, overrides: [:])
        XCTAssertEqual(ruleProblems, [], "rules.json decodes into RulesTuning")
        let (_, econProblems) = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data)
        XCTAssertEqual(econProblems, [], "rules.json + social.json decode into EconomyRules")
        XCTAssertNotNil(tuning.social.file.decode(SocialConfig.self), "social.json decodes into SocialConfig (no silent .default)")
    }

    /// CONSISTENCY G-5, SPEC.md §5.29/§5.32: the app always passes board.json's 22 pt; the frozen 15 pt fallbacks stay.
    func testHitRadiusIsTheRuled22ptAndTheAppReadsIt() throws {
        XCTAssertEqual(((try json("board"))["input"] as? [String: Any])?["hitRadiusPt"] as? Double, 22)
        XCTAssertEqual(tuning.board.hitRadiusPt, 22, "BoardTuning reads the bundled value")
        XCTAssertEqual(BoardConfig(tuning.board).hitRadius, 22, "the board's config (HitTester's radiusPt) is the bundled value")
        XCTAssertEqual(Tuning.defaults.board.hitRadiusPt, 15, "ruling 32: the frozen fallback stays 15 pt")
        let (rules, _) = RulesTuning.load(json: tuning.rules.data, overrides: [:])
        XCTAssertEqual(rules.hit.radiusPt, 22, "rules.json hit.radiusPt carries the same value")
    }

    /// CONSISTENCY X-7 + SPEC.md §5.29: one life per 30:00 (1800 s) — in the file, in the loader the app uses, and in the
    /// compiled fallback.
    func testLivesRefillEvery1800Seconds() throws {
        XCTAssertEqual(((try json("rules"))["lives"] as? [String: Any])?["refillSeconds"] as? Double, 1800)
        let (econ, _) = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data)
        XCTAssertEqual(econ.lives.refillSeconds, 1800)
        XCTAssertEqual(econ.lives.max, 5)
        XCTAssertEqual(econ.lives.refillPrice, 900)
        XCTAssertEqual(EconomyRules().lives.refillSeconds, 1800, "the compiled fallback (lives fallback 1800)")
        // the home pill counts 30:00 per life (HomeTopBar LivesText with the loaded interval)
        var s = PlayerState()
        s.lives = LivesState(count: 4, anchor: LaunchArgs.captureDate)
        XCTAssertEqual(LivesText.value(s, now: LaunchArgs.captureDate, refill: econ.lives.refillSeconds), "4|30:00")
        XCTAssertEqual(LivesText.value(s, now: LaunchArgs.captureDate.addingTimeInterval(600), refill: econ.lives.refillSeconds), "4|20:00")
        XCTAssertEqual(LivesText.value(s, now: LaunchArgs.captureDate.addingTimeInterval(1799), refill: econ.lives.refillSeconds), "4|00:01")
    }

    func testRulesCarryTheRuledValues() throws {
        let (rules, _) = RulesTuning.load(json: tuning.rules.data, overrides: [:])
        XCTAssertEqual(rules.pipe.countAt, .leave, "CONSISTENCY O-15")
        XCTAssertEqual(rules.boosters.freezeFlight, 1.6, accuracy: 1e-9, "K-3")
        XCTAssertEqual(rules.boosters.freezeSeconds, 10, accuracy: 1e-9)
        let (econ, _) = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data)
        XCTAssertEqual(econ.economy.startCoins, 1000, "X-14")
        XCTAssertEqual(econ.economy.startBoosters, ["freeze": 3, "hint": 3], "K-2")
        XCTAssertEqual(econ.economy.boosterPack, EconomyRules.BoosterPack(count: 3, price: 900), "K-6")
        let r = try json("rules")
        let rewards = try XCTUnwrap(r["rewards"] as? [String: Int])
        XCTAssertEqual(rewards["normal"], 20); XCTAssertEqual(rewards["hard"], 60); XCTAssertEqual(rewards["superHard"], 100)
        XCTAssertNil(rewards["session"], "X-15: the L1-4 reward lives in sessions.json only")
        let chain = try XCTUnwrap(r["failChain"] as? [String: [[String: Any]]])
        for (k, steps) in chain {
            XCTAssertEqual(steps.count, 3, k)
            for s in steps { XCTAssertEqual(s["price"] as? Int, 900, "X-2: 900 on every step (\(k))") }
        }
        XCTAssertEqual(chain["outOfTime"]?.first?["amount"] as? Int, 30, "Add Time +30 s")
        XCTAssertEqual(chain["outOfHearts"]?.first?["amount"] as? Int, 3, "Add Lives → 3 hearts")
    }

    func testBoardUIAndGameCarryTheRuledValues() throws {
        XCTAssertEqual(tuning.board.rainbowPeriodCells, 4.2, accuracy: 1e-9, "E-12")
        XCTAssertEqual(tuning.board.zoomMin, 0.786, accuracy: 1e-9)
        XCTAssertEqual(tuning.board.zoomMaxPitch, 28.07, accuracy: 1e-9)
        // SPEC.md ruling 35 (the same approved W-2 pin as ShellS2Tests, same strength): re-anchored on the wave start, v552's
        // panel at W + 4.034 (build/logo/LOGO-SPEC.md §1)
        XCTAssertEqual(tuning.ui.winPanelAt, 4.034, accuracy: 1e-9, "W-2 re-anchored on the wave start: the panel at W + 4.034")
        let beats = tuning.ui.unlockBeats
        // SPEC.md §5 item 42 (contract amend 4; motion-catalog §6.7, v552): the dismiss is a one-frame content cut + a 0.233 s
        // linear dim fade (was dismissFade 0.16) — the whole struct still compared exactly, the new dismissMode included
        XCTAssertEqual(beats, UnlockBeats(icon: 0.26, iconSettle: 0.54, title: 0.50, unlocked: 0.62, card: 0.78, sparkles: 1.14,
                                          dismissFade: 0.233, dismissMode: .contentCut),
                       "SPEC-motion-audio §6.3 (T-25) + motion-catalog §6.7")
        XCTAssertEqual(Tuning.defaults.ui.unlockBeats, beats, "SPEC.md §5.29/§5.42: the frozen defaults were amended to the same beats")
        XCTAssertEqual(tuning.game.ftueChainUntilLevel, 7)
        XCTAssertEqual(tuning.game.ratingAfterLevel, 34, "D24: the rating sheet after the L34 win")
        XCTAssertTrue(tuning.game.notificationsAskOnFirstLaunch, "SPEC.md §5.5")
        XCTAssertEqual(tuning.game.file.string("support.email", ""), "anycodeapps@gmail.com", "SPEC.md §5.21/§5.24")
        XCTAssertNil(tuning.audio.cue("arrowTap"), "SPEC.md §5.4: no tap sound")
    }

    /// CONSISTENCY §20: the shipped social avatar range is the 8 portraits + the default silhouette, and each has art.
    func testSocialAvatarsAreTheShippedPortraits() throws {
        let folder = try XCTUnwrap(Bundle.main.resourceURL).appendingPathComponent("Social")
        let world = SocialWorld(installSeed: 7, config: tuning.social.config, names: try NameBank.load(folder: folder))
        let me = PlayerStanding(name: "player_7", avatar: 0, country: "TR", level: 40, ledger: [])
        let page = world.page(.world, me: me, at: SocialTime(seconds: Int64(LaunchArgs.captureDate.timeIntervalSince1970)), ranks: 1...400)
        let avatars = Set(page.rows.map(\.player.avatar))
        XCTAssertFalse(avatars.isEmpty)
        XCTAssertTrue(avatars.isSubset(of: Set(0...8)), "avatars \(avatars.sorted()) ⊆ 0…8")
    }

    /// F3-A (Wave 3 bundle hygiene; F3-B's release_gates gate 7b WATCH): the JSON the app ships from App/Resources carries no
    /// developer documentation — no "_" comment keys (_about / _sources / _owner / _corrections / _pending) and no prose keys
    /// (note / notes / opacityRule / opacityFrom / baked / proof / replaces), at any depth. No reader reads them (TuningFile
    /// reads named paths; RulesTuning / EconomyRules / SocialConfig decode named keys; LogoSpec reads its numeric fields).
    /// The one exception is B0's ruling (design/tools/strip_provenance.py RULES curve:_comment): Levels/curve.json keeps its
    /// neutral "_about", because the runtime compares the bundled curve with the compiled CurveSpec.default byte for byte —
    /// that key is pinned equal to the compiled one here, and nothing else may join it.
    func testShippedResourceJSONCarriesNoDeveloperNotes() throws {
        let root = try XCTUnwrap(Bundle.main.resourceURL)
        let doc: Set<String> = ["note", "notes", "opacityRule", "opacityFrom", "baked", "proof", "replaces"]
        func notes(_ o: Any, _ path: String, _ out: inout [String]) {
            if let d = o as? [String: Any] {
                for (k, v) in d {
                    if k.hasPrefix("_") || doc.contains(k) { out.append(path + "." + k) }
                    notes(v, path + "." + k, &out)
                }
            } else if let a = o as? [Any] {
                for v in a { notes(v, path + "[]", &out) }
            }
        }
        var files: [String] = Tuning.fileNames.map { "Tuning/\($0).json" }
        let social = try FileManager.default.contentsOfDirectory(atPath: root.appendingPathComponent("Social").path)
        files += social.filter { $0.hasSuffix(".json") }.map { "Social/" + $0 }
        files += ["Levels/sessions.json", "Levels/unlocks.json", "Levels/tutorials.json", "Levels/curve.json"]
        XCTAssertGreaterThanOrEqual(files.count, 11, "the six tuning files, the name bank, the four level-side files")
        var found: [String] = []
        for f in files {
            let data = try Data(contentsOf: root.appendingPathComponent(f))
            let obj = try JSONSerialization.jsonObject(with: data)
            var out: [String] = []
            notes(obj, "", &out)
            found += out.map { f + $0 }
        }
        XCTAssertEqual(found.sorted(), ["Levels/curve.json._about"], "developer notes in the shipped JSON")
        // the curve's comment is the compiled curve's own (B0): the same text, so the ruled exception cannot drift
        let curve = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("Levels/curve.json"))) as? [String: Any])
        XCTAssertEqual(curve["_about"] as? String, CurveSpec.default.json["_about"]?.stringValue, "curve.json _about = CurveSpec.default's")
        // the scanner sees what it looks for (a planted note at depth, a "_" key in an array element)
        var planted: [String] = []
        notes(["a": ["b": [["note": "x", "_c": 1]]], "_d": 2], "", &planted)
        XCTAssertEqual(planted.sorted(), ["._d", ".a.b[]._c", ".a.b[].note"], "control: the scanner finds planted notes")
    }
}
