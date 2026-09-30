import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// §4.7.
final class ComboTests: XCTestCase {
    func testWindow() {
        var c = ComboTracker()
        XCTAssertEqual(c.window, 1.25)
        XCTAssertEqual(c.register(tapAt: 0, isBump: false), 1)
        XCTAssertEqual(c.register(tapAt: 1.25, isBump: false), 2)     // within the window (inclusive)
        XCTAssertEqual(c.register(tapAt: 2.4, isBump: false), 3)
        XCTAssertEqual(c.peek(at: 3.0), 4)
        XCTAssertEqual(c.register(tapAt: 3.66, isBump: false), 1)     // 1.26 s → a new streak
        XCTAssertEqual(c.count, 1)
    }

    /// v552 (VERIFIED motion §3.4): taps 0.58 / 0.75 s apart → blue, blue, violet = indices 1, 2, 3.
    func testThreeExitsCheck() {
        var c = ComboTracker()
        XCTAssertEqual([0, 0.58, 1.33].map { c.register(tapAt: $0, isBump: false) }, [1, 2, 3])
    }

    func testBumpBreaks() {
        var c = ComboTracker()
        _ = c.register(tapAt: 0, isBump: false)
        _ = c.register(tapAt: 0.5, isBump: false)
        XCTAssertEqual(c.register(tapAt: 0.8, isBump: true), 0)
        XCTAssertEqual(c.register(tapAt: 1.0, isBump: false), 1)
        var keep = ComboTracker(window: 1.25, bumpBreaks: false)
        _ = keep.register(tapAt: 0, isBump: false)
        XCTAssertEqual(keep.register(tapAt: 0.5, isBump: true), 0)
        XCTAssertEqual(keep.register(tapAt: 1.0, isBump: false), 2)
        keep.reset()
        XCTAssertNil(keep.lastTap)
    }
}
