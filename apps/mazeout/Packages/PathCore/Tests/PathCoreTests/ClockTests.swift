import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// §4.6.
final class ClockTests: XCTestCase {
    func testFrozenUntilTheFirstTap() {
        var c = LevelClock(limit: 150)
        XCTAssertEqual(c.tick(10), [])
        XCTAssertEqual(c.remaining, 150)
        XCTAssertFalse(c.isRunning)
        XCTAssertEqual(c.displayedSeconds, 150)
        c.startOnFirstTap()
        XCTAssertTrue(c.isRunning)
        _ = c.tick(0.25)
        XCTAssertEqual(c.displayedSeconds, 150)          // ceil: 149.75 still shows 2:30
        _ = c.tick(0.75)
        XCTAssertEqual(c.displayedSeconds, 149)
    }

    func testHoldsStack() {
        var c = LevelClock(limit: 60)
        c.startOnFirstTap()
        c.hold(.pause); c.hold(.popup)
        _ = c.tick(5)
        c.release(.pause)
        _ = c.tick(5)
        XCTAssertEqual(c.remaining, 60)
        c.release(.popup)
        _ = c.tick(5)
        XCTAssertEqual(c.remaining, 55)
        XCTAssertEqual(c.holds, [])
    }

    func testExpiryOnceAndAddTime() {
        var c = LevelClock(limit: 3)
        c.startOnFirstTap()
        XCTAssertEqual(c.tick(2), [])
        XCTAssertEqual(c.tick(2), [.expired])
        XCTAssertEqual(c.remaining, 0)
        XCTAssertEqual(c.tick(2), [])
        XCTAssertFalse(c.isRunning)
        c.add(30)
        XCTAssertEqual(c.remaining, 30)
        XCTAssertEqual(c.limit, 3)
        XCTAssertEqual(c.tick(31), [.expired])
    }

    func testFreezeSplitsATick() {
        var c = LevelClock(limit: 100)
        c.startOnFirstTap()
        c.freeze(2)
        c.freeze(1)                                      // stacks
        XCTAssertTrue(c.isFrozen)
        XCTAssertEqual(c.tick(2), [])
        XCTAssertEqual(c.tick(2), [.freezeEnded])
        XCTAssertEqual(c.remaining, 99)
        var early = LevelClock(limit: 100, freezeRunsBeforeStart: true)
        early.freeze(5)
        XCTAssertEqual(early.tick(6), [.freezeEnded])
        XCTAssertEqual(early.remaining, 100)
    }

    func testAlerts() {
        var c = LevelClock(limit: 30, alerts: [5, 10])
        c.startOnFirstTap()
        XCTAssertEqual(c.tick(19), [])
        XCTAssertEqual(c.tick(1), [.alert(10)])
        XCTAssertEqual(c.tick(6), [.alert(5)])
        XCTAssertEqual(c.tick(10), [.expired])
        c.add(20)
        XCTAssertEqual(c.tick(15), [.alert(10), .alert(5)])   // re-armed above the new value
    }
}
