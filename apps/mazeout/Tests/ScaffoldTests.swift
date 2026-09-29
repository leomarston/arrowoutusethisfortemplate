import XCTest
import UIKit
import PathCore
@testable import ArrowOut

/// WP0 → V1 (SPEC-architecture §12.2 WP0). Hosted scaffold checks that only the simulator can make: the brand comes from
/// Info.plist, the fonts resolve by PostScript name through UIAppFonts, the bundle carries the six tuning files, the
/// launch arguments parse (§9.1), and the tuning files agree with their compiled defaults. VERIFY owns this file from
/// V1 on (its FontCoverage / Tuning / Brand suites supersede these checks).
final class ScaffoldTests: XCTestCase {

    func testBrandComesFromInfoPlist() {
        let key = Bundle.main.object(forInfoDictionaryKey: "PCBrandName") as? String
        XCTAssertNotNil(key)
        XCTAssertFalse(Brand.name.isEmpty)
        XCTAssertEqual(key, Brand.name)
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String, Brand.name)
    }

    func testFontsResolveByPostScriptName() {
        for name in AppModel.fontNames {
            let font = UIFont(name: name, size: 20)
            XCTAssertNotNil(font, "\(name) is not registered")
            XCTAssertEqual(font?.fontName, name)
        }
    }

    func testBundleCarriesTheSixTuningFiles() {
        for name in Tuning.fileNames {
            XCTAssertNotNil(Bundle.main.url(forResource: name, withExtension: "json", subdirectory: "Tuning"), name)
        }
        XCTAssertEqual(Set(Tuning.load(bundle: .main).loadedFiles), Set(Tuning.fileNames))
    }

    func testLaunchArgumentsParse() {
        let a = LaunchArgs(arguments: ["ArrowOut", "-pc.reset", "-pc.clockOffset", "-3600", "-pc.go", "leaderboard:weekly",
                                       "-pc.boosters", "freeze=3,hint=0", "-pc.popup", "continue:life", "-pc.win", "superHard",
                                       "-pc.freezeAt", "win@1.2", "-AppleLanguages", "(tr)"])
        XCTAssertTrue(a.reset)
        XCTAssertEqual(a.clockOffset, -3600)
        XCTAssertEqual(a.go, .leaderboard("weekly"))
        XCTAssertEqual(a.boosters, ["freeze": 3, "hint": 0])
        XCTAssertEqual(a.popup, LaunchArgs.PopupArg(id: "continue", variant: "life"))
        XCTAssertEqual(a.win, .superHard)
        XCTAssertEqual(a.freezeAt, LaunchArgs.FreezeAt(sequence: "win", t: 1.2))
        XCTAssertNil(a.raw["AppleLanguages"])
        let capture = LaunchArgs(arguments: ["-pc.capture", "1"])
        XCTAssertEqual(capture.effectiveSeed, 1)
        XCTAssertEqual(capture.clockStart, LaunchArgs.captureDate)
        XCTAssertEqual(capture.effectiveClockRate, 0)
        XCTAssertTrue(capture.holdsTimerForCapture)
    }

    func testTuningFilesAgreeWithTheCompiledDefaults() {
        let bundled = Tuning.load(bundle: .main)
        let compiled = Tuning.defaults
        XCTAssertEqual(bundled.board.zoomMin, compiled.board.zoomMin)
        XCTAssertEqual(bundled.board.zoomMaxPitch, compiled.board.zoomMaxPitch)
        XCTAssertEqual(bundled.board.comboLadder, compiled.board.comboLadder)
        XCTAssertEqual(bundled.board.rainbowPalette, compiled.board.rainbowPalette)
        XCTAssertEqual(bundled.game.ftueChainUntilLevel, compiled.game.ftueChainUntilLevel)
        for token in DimToken.allCases { XCTAssertEqual(bundled.ui.dim(token), compiled.ui.dim(token), "\(token)") }
        XCTAssertEqual(bundled.ui.unlockBeats, compiled.ui.unlockBeats)
        for moment in ["uiButton", "celebrationSkip", "homePayout", "unlockOverlay", "arrowTap"] {
            XCTAssertEqual(bundled.audio.cue(moment), compiled.audio.cue(moment), moment)
        }
        XCTAssertNil(bundled.audio.cue("arrowTap"), "v552 is silent on taps (SPEC.md §5 item 4)")
        for h in Haptic.allCases {
            XCTAssertEqual(bundled.audio.haptic(h).style, compiled.audio.haptic(h).style)
            XCTAssertEqual(bundled.audio.haptic(h).intensity, compiled.audio.haptic(h).intensity)
        }
        XCTAssertEqual(Tuning.load(bundle: .main, tune: ["board.zoom.min": "0.8"]).board.zoomMin, 0.8)
    }
}
