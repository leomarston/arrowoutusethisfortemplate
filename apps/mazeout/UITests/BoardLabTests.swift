import XCTest

/// B1 (SPEC-architecture §12.2 B1 acceptance 5, §11 R1): 50 REAL releases through XCUITest while BoardLab `latency`
/// records LatencyProbe samples (touch → handler → commit → vsync) into Documents/lab-perf.json (read from the host after
/// the run: build/b1/ evidence). The probe is read once per ROUND, never between taps: every probe read makes XCUITest
/// snapshot the whole accessibility tree on the app's main thread (measured: 75 frames > 20 ms and touch → handler p99
/// 22.6 ms when polling between taps), which would measure the harness, not the board.
final class BoardLabTests: XCTestCase {
    override func setUp() {
        continueAfterFailure = false
    }

    func testFiftyRealTapsEachSendTheirArrow() {
        // R1 A/B: TEST_RUNNER_PCR1=fallback (xcodebuild forwards TEST_RUNNER_* to the runner) launches the fallback recogniser
        var extra = ["-pc.reset", "1", "-pc.go", "boardlab", "-pc.lab", "latency", "-pc.labBoard", "synth40", "-pc.logTaps", "1"]
        if let mode = ProcessInfo.processInfo.environment["PCR1"], !mode.isEmpty { extra += ["-pc.r1", mode] }
        let app = AppUnderTest.launch(extra)
        func arrows(_ p: [String: Any]) -> [[String: Any]] { p["arrows"] as? [[String: Any]] ?? [] }
        guard var p = app.waitForProbe(timeout: 30, { arrows($0).count == 304 && $0["settled"] as? Bool == true }) else {
            print(app.debugDescription)
            return XCTFail("no settled 304-arrow board")
        }
        var fired: [Int] = []
        var rounds = 0
        // rounds: ONE probe read, a pause for the main thread to settle, then every free single arrow of the round tapped
        // 0.25 s apart with no accessibility query in between (free arrows stay free while others leave)
        while fired.count < 50, rounds < 8 {
            rounds += 1
            let free = arrows(p).filter { $0["free"] as? Bool == true && ($0["x"] as? Double ?? -1) > 0
                && ($0["unit"] as? [Int] ?? []).count == 1 && !fired.contains($0["id"] as? Int ?? -1) }
            if free.isEmpty { break }
            RunLoop.current.run(until: Date().addingTimeInterval(0.5))
            for a in free.prefix(50 - fired.count) {
                app.tap(screenX: a["x"] as? Double ?? 0, y: a["y"] as? Double ?? 0)
                fired.append(a["id"] as? Int ?? -1)
                RunLoop.current.run(until: Date().addingTimeInterval(0.25))
            }
            RunLoop.current.run(until: Date().addingTimeInterval(1.0))
            guard let next = app.waitForProbe(timeout: 5, { arrows($0).count == 304 - fired.count }) else {
                return XCTFail("round \(rounds): not every tap on a free arrow sent it")
            }
            p = next
        }
        XCTAssertEqual(fired.count, 50, "50 real releases, each on a free arrow (\(rounds) probe rounds)")
        let left = Set(arrows(p).compactMap { $0["id"] as? Int })
        XCTAssertTrue(left.isDisjoint(with: fired))
        XCTAssertEqual(p["hearts"] as? Int, 3, "no tap bumped")
        RunLoop.current.run(until: Date().addingTimeInterval(1.5))       // the lab writes lab-perf.json every second
    }
}
