import XCTest
import CoreGraphics
import PathCore

/// C1 test helpers shared by GridTests, GeometryTests, LevelJSONTests, KinematicsTests, CurvesTests and RandomTests.
/// Paths come from #filePath (no SwiftPM resources, §2.4). Reports go to $PC_EVIDENCE_DIR when it is set.
enum C1Fixtures {
    /// Packages/PathCore/Tests
    static var testsDir: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent() }
    /// apps/mazeout
    static var appRoot: URL {
        testsDir.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }
    static func fixture(_ name: String) -> URL { testsDir.appendingPathComponent("Fixtures/\(name)") }
    /// Tests/Fixtures/research: a tracked, frozen copy of the research corpus these tests were written for (its layout
    /// mirrors apps/mazeout/research/; file list + sha256 in MANIFEST.txt). Never the live research/ folders: phone sessions
    /// keep adding levels to research/levels, and research/video-frames/ is a gitignored, regenerable cache.
    static var researchRoot: URL { fixture("research") }
    static func research(_ path: String) -> URL { researchRoot.appendingPathComponent(path) }

    static func data(_ url: URL, file: StaticString = #filePath, line: UInt = #line) throws -> Data {
        do { return try Data(contentsOf: url) } catch {
            XCTFail("cannot read \(url.path): \(error)", file: file, line: line)
            throw error
        }
    }

    /// The 30 recorded levels: <researchRoot>/levels/L0NN.json with source "recorded" (no -openK states; the video lane
    /// also wrote video-sourced L001… files into that folder).
    static func recordedBaseFiles() throws -> [URL] {
        try researchLevelFiles().filter {
            $0.lastPathComponent.range(of: #"^L0\d\d\.json$"#, options: .regularExpression) != nil
                && ((try? jsonObject($0))?["source"] as? String) == "recorded"
        }
    }

    /// Every JSON directly in <researchRoot>/levels (phone schema, their reveal states, and video-sourced levels).
    static func researchLevelFiles() throws -> [URL] {
        let dir = research("levels")
        return try FileManager.default.contentsOfDirectory(atPath: dir.path).filter { $0.hasSuffix(".json") }
            .sorted().map { dir.appendingPathComponent($0) }
    }

    /// The video extracts: <researchRoot>/video-frames/work/extract/V?-Lnnn.json and <researchRoot>/levels/video/V?-Lnnn.json.
    static func videoExtractFiles() throws -> [URL] {
        var out: [URL] = []
        for sub in ["video-frames/work/extract", "levels/video"] {
            let dir = research(sub)
            guard FileManager.default.fileExists(atPath: dir.path) else { continue }
            out += try FileManager.default.contentsOfDirectory(atPath: dir.path)
                .filter { $0.range(of: #"^V\d-L\d{3}\.json$"#, options: .regularExpression) != nil }
                .sorted().map { dir.appendingPathComponent($0) }
        }
        return out
    }

    static func jsonObject(_ url: URL) throws -> [String: Any] {
        guard let o = try JSONSerialization.jsonObject(with: try data(url)) as? [String: Any] else {
            throw NSError(domain: "c1", code: 1, userInfo: [NSLocalizedDescriptionKey: "\(url.lastPathComponent) is not an object"])
        }
        return o
    }

    /// Writes a text report into $PC_EVIDENCE_DIR (build/c1/ in the C1 runs); a no-op otherwise.
    static func evidence(_ name: String, _ text: String) {
        guard let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty else { return }
        let url = URL(fileURLWithPath: dir).appendingPathComponent(name)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? Data(text.utf8).write(to: url)
    }

    /// Runs a python3 script under apps/mazeout and returns stdout, or nil when python3 is missing.
    static func python(_ relativePath: String) -> String? {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        p.arguments = ["python3", appRoot.appendingPathComponent(relativePath).path]
        let out = Pipe()
        p.standardOutput = out
        p.standardError = Pipe()
        do { try p.run() } catch { return nil }
        let d = out.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return p.terminationStatus == 0 ? String(decoding: d, as: UTF8.self) : nil
    }
}

final class GridTests: XCTestCase {

    func testMaskRowsParseAndRoundTrip() {
        let g = Grid(cols: 4, rows: 3, maskRows: ["#..#", "####", "##"])      // a short row is padded with "outside"
        XCTAssertNotNil(g.mask)
        XCTAssertTrue(g.contains(Cell(0, 0)))
        XCTAssertFalse(g.contains(Cell(1, 0)))
        XCTAssertTrue(g.contains(Cell(3, 0)))
        XCTAssertTrue(g.contains(Cell(3, 1)))
        XCTAssertTrue(g.contains(Cell(1, 2)))
        XCTAssertFalse(g.contains(Cell(2, 2)))
        XCTAssertFalse(g.contains(Cell(-1, 0)))
        XCTAssertFalse(g.contains(Cell(4, 1)))
        XCTAssertFalse(g.contains(Cell(0, 3)))
        XCTAssertEqual(g.playableCount, 2 + 4 + 2)
        XCTAssertEqual(g.maskRows, ["#..#", "####", "##.."])
        XCTAssertEqual(g.cells.count, g.playableCount)
        XCTAssertEqual(g.cells.first, Cell(0, 0))
        XCTAssertEqual(g.cells.last, Cell(1, 2))
        // In bounds ignores the mask.
        XCTAssertTrue(g.inBounds(Cell(1, 0)))
    }

    func testWrongMaskIsIgnored() {
        let wrongRows = Grid(cols: 3, rows: 2, maskRows: ["###"])             // 1 row for a 2-row grid
        XCTAssertNil(wrongRows.mask)
        XCTAssertTrue(wrongRows.contains(Cell(2, 1)))
        let wrongCount = Grid(cols: 3, rows: 2, mask: [true, false])
        XCTAssertNil(wrongCount.mask)
        XCTAssertNil(Grid(cols: 3, rows: 2, maskRows: nil).mask)
        XCTAssertNil(Grid(cols: 3, rows: 2).maskRows)
        XCTAssertEqual(Grid(cols: 3, rows: 2).playableCount, 6)
    }

    func testIndexIsRowMajorAndRoundTrips() {
        let g = Grid(cols: 7, rows: 5)
        var seen = Set<Int>()
        for r in 0..<g.rows {
            for c in 0..<g.cols {
                let i = g.index(Cell(c, r))
                XCTAssertEqual(i, r * 7 + c)
                XCTAssertEqual(g.cell(at: i), Cell(c, r))
                XCTAssertTrue(seen.insert(i).inserted)
            }
        }
        XCTAssertEqual(seen, Set(0..<35))
        XCTAssertEqual(g.count, 35)
    }

    func testStepsToEdge() {
        let g = Grid(cols: 20, rows: 30)
        XCTAssertEqual(g.stepsToEdge(from: Cell(3, 4), .right), 16)
        XCTAssertEqual(g.stepsToEdge(from: Cell(3, 4), .left), 3)
        XCTAssertEqual(g.stepsToEdge(from: Cell(3, 4), .up), 4)
        XCTAssertEqual(g.stepsToEdge(from: Cell(3, 4), .down), 25)
        XCTAssertEqual(g.stepsToEdge(from: Cell(19, 29), .right), 0)
        XCTAssertEqual(g.stepsToEdge(from: Cell(19, 29), .down), 0)
        // Walking that many steps stays in bounds, one more leaves.
        for d in Dir.allCases {
            let n = g.stepsToEdge(from: Cell(3, 4), d)
            XCTAssertTrue(g.inBounds(Cell(3, 4).moved(d, by: n)))
            XCTAssertFalse(g.inBounds(Cell(3, 4).moved(d, by: n + 1)))
        }
    }

    func testLevelSpecGridUsesTheMask() {
        let l = LevelSpec(level: 1, source: .designed, cols: 3, rows: 2, mask: [".#.", "###"], timerSeconds: 180, arrows: [])
        XCTAssertEqual(l.grid, Grid(cols: 3, rows: 2, maskRows: [".#.", "###"]))
        XCTAssertFalse(l.grid.contains(Cell(0, 0)))
        XCTAssertTrue(l.grid.contains(Cell(1, 0)))
    }
}
