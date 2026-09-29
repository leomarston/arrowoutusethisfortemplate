import XCTest
import PathCore
@testable import ArrowOut

/// FIX-A2 (PLAN FIX LOOP 1: "add FEEL's new data keys to board.json/ui.json"). FEEL gave five knobs compiled defaults only;
/// the bundled files now carry them with exactly those values, so the data is the source again (a `-pc.tune` or a file edit
/// moves them) while the app behaves as before:
///   board.json exit.tapMotionLead 1/60 · ripple.coreFirstRadiusPt 9.5 · load.prepBudgetMs 1.0; ui.json win.prebuildFrom 0.10 ·
///   win.burstPerFrame 10; and board.json no longer carries ripple.edgeSoftPt (no reader draws with it).
/// Each value is checked in the raw file AND through the reader the app uses, against the same reader on an empty file (the
/// compiled default). ScaffoldTests keeps the WP0 per-key comparison.
@MainActor final class FeelTuningKeysTests: XCTestCase {

    private func json(_ name: String) throws -> [String: Any] {
        let url = try XCTUnwrap(Bundle.main.url(forResource: name, withExtension: "json", subdirectory: "Tuning"), name)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any], name)
    }

    private func number(_ d: [String: Any], _ section: String, _ key: String) -> Double? {
        ((d[section] as? [String: Any])?[key] as? NSNumber)?.doubleValue
    }

    func testTheFeelKeysAreInTheBundledFilesWithTheCompiledDefaults() throws {
        let board = try json("board"), ui = try json("ui")
        XCTAssertEqual(try XCTUnwrap(number(board, "exit", "tapMotionLead")), 1.0 / 60, accuracy: 1e-12)
        XCTAssertEqual(number(board, "ripple", "coreFirstRadiusPt"), 9.5)
        XCTAssertEqual(number(board, "load", "prepBudgetMs"), 1.0)
        XCTAssertEqual(number(ui, "win", "prebuildFrom"), 0.10)
        XCTAssertEqual(number(ui, "win", "burstPerFrame"), 10)
        XCTAssertNil((board["ripple"] as? [String: Any])?["edgeSoftPt"], "ripple.edgeSoftPt is gone from the data")

        let bundled = Tuning.load(bundle: .main), compiled = Tuning.defaults
        let bc = BoardConfig(bundled.board), cc = BoardConfig(compiled.board)
        XCTAssertEqual(bc.tapMotionLead, cc.tapMotionLead, accuracy: 1e-12, "exit.tapMotionLead = the compiled 1/60")
        XCTAssertEqual(bc.tapMotionLead, 1.0 / 60, accuracy: 1e-12)
        XCTAssertEqual(bc.rippleCoreFirstRadius, cc.rippleCoreFirstRadius)
        XCTAssertEqual(bc.rippleCoreFirstRadius, 9.5)
        let be = EffectsConfig(bundled.board), ce = EffectsConfig(compiled.board)
        XCTAssertEqual(be.prepBudgetMs, ce.prepBudgetMs)
        XCTAssertEqual(be.prepBudgetMs, 1.0)
        let bw = CelebrationRun.Beats(bundled.ui.file), cw = CelebrationRun.Beats(compiled.ui.file)
        XCTAssertEqual(bw.prebuildFrom, cw.prebuildFrom)
        XCTAssertEqual(bw.prebuildFrom, 0.10)
        XCTAssertEqual(bw.burstPerFrame, cw.burstPerFrame)
        XCTAssertEqual(bw.burstPerFrame, 10)

        // the file is really read (not only equal by chance): a tune override moves each through the same readers
        let tuned = Tuning.load(bundle: .main, tune: ["board.exit.tapMotionLead": "0.03", "board.ripple.coreFirstRadiusPt": "7",
                                                      "board.load.prepBudgetMs": "2.5", "ui.win.prebuildFrom": "0.2",
                                                      "ui.win.burstPerFrame": "4"])
        XCTAssertEqual(BoardConfig(tuned.board).tapMotionLead, 0.03, accuracy: 1e-12)
        XCTAssertEqual(BoardConfig(tuned.board).rippleCoreFirstRadius, 7)
        XCTAssertEqual(EffectsConfig(tuned.board).prepBudgetMs, 2.5)
        XCTAssertEqual(CelebrationRun.Beats(tuned.ui.file).prebuildFrom, 0.2, accuracy: 1e-12)
        XCTAssertEqual(CelebrationRun.Beats(tuned.ui.file).burstPerFrame, 4)
    }
}
