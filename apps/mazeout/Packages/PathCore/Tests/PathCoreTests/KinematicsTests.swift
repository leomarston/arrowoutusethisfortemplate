import XCTest
import PathCore

/// One measured sample of Tests/Fixtures/c1_motion_samples.json (written by Tests/tools/c1_motion_samples.py from
/// research/motion-tools/out and the motion.md / tutorials.md tables).
struct C1Sample: Decodable {
    let t: Double
    let v: Double
    let tol: Double
    let src: String
}

enum C1Motion {
    static let samples: [String: [C1Sample]] = {
        let url = C1Fixtures.fixture("c1_motion_samples.json")
        guard let d = try? Data(contentsOf: url), let s = try? JSONDecoder().decode([String: [C1Sample]].self, from: d) else {
            return [:]
        }
        return s
    }()

    /// Checks `f(t)` against every sample of `key`; returns the report lines. Fails on a missing group.
    @discardableResult
    static func check(_ key: String, file: StaticString = #filePath, line: UInt = #line, _ f: (Double) -> Double) -> [String] {
        guard let group = samples[key], !group.isEmpty else {
            XCTFail("fixture group \(key) missing (run Tests/tools/c1_motion_samples.py)", file: file, line: line)
            return []
        }
        var out: [String] = []
        var worst = 0.0
        for s in group {
            let got = f(s.t)
            let err = abs(got - s.v)
            worst = max(worst, err / s.tol)
            XCTAssertLessThanOrEqual(err, s.tol + 1e-9, "\(key) at \(s.t): \(got) vs \(s.v) ± \(s.tol) (\(s.src))", file: file, line: line)
            out.append(String(format: "  %@ t=%.4f measured %.4f curve %.4f err %.4f tol %.4f  %@", key, s.t, s.v, got, err, s.tol, s.src))
        }
        out.insert(String(format: "%@: %d samples, worst |err|/tol = %.2f", key, group.count, worst), at: 0)
        return out
    }
}

/// C1 (SPEC-architecture §4.16, D5): the exit law against motion.md's T(d) table (pass 2, the default) and the
/// architecture's pass-1 table, ±0.003 s.
final class KinematicsTests: XCTestCase {

    func testPass2TableWithin3ms() {
        let k = ExitKinematics.measured
        var lines = C1Motion.check("exit_T_pass2") { k.time(toTravel: $0) }
        lines += C1Motion.check("exit_v_pass2") { k.v($0) }
        C1Fixtures.evidence("kinematics.txt", lines.joined(separator: "\n") + "\n")
        XCTAssertEqual(k.v0, 7.67); XCTAssertEqual(k.vmax, 73.86); XCTAssertEqual(k.tau, 0.353)
        XCTAssertEqual((k.vmax - k.v0) * k.tau, 23.37, accuracy: 0.01, "motion.md: s = 73.86τ − 23.37(1 − e^(−τ/0.353))")
    }

    func testPass1TableWithin3ms() {
        let k = ExitKinematics.pass1
        C1Motion.check("exit_T_pass1") { k.time(toTravel: $0) }
        XCTAssertEqual((k.vmax - k.v0) * k.tau, 21.29, accuracy: 1e-9, "SPEC-architecture D5: s = 71.4τ − 21.29(1 − e^(−τ/0.323))")
        // motion.md: "T(d) differs ≤ 7 ms" between the two fits; measured here: ≤ 7 ms to 33 cells, 8.4 ms at 40 cells.
        var worst = 0.0
        for d in stride(from: 0.5, through: 40, by: 0.5) {
            let diff = abs(ExitKinematics.pass1.time(toTravel: d) - ExitKinematics.measured.time(toTravel: d))
            worst = max(worst, diff)
            XCTAssertLessThanOrEqual(diff, d <= 33 ? 0.007 : 0.009, "d \(d)")
        }
        C1Fixtures.evidence("kinematics-pass1-vs-pass2.txt", String(format: "max |T_pass1 − T_pass2| over 0.5…40 cells = %.4f s\n", worst))
    }

    func testInverseAndMonotonicity() {
        for k in [ExitKinematics.measured, .pass1, ExitKinematics(v0: 0, vmax: 50, tau: 0.2)] {
            var last = -1.0
            for i in 1...2000 {
                let d = Double(i) * 0.1
                let t = k.time(toTravel: d)
                XCTAssertEqual(k.s(t), d, accuracy: 1e-8, "d \(d)")
                XCTAssertGreaterThan(t, last)
                last = t
            }
            XCTAssertEqual(k.time(toTravel: 0), 0)
            XCTAssertEqual(k.time(toTravel: -3), 0)
            XCTAssertEqual(k.s(0), 0)
            XCTAssertEqual(k.s(-1), 0)
            XCTAssertEqual(k.v(-1), k.v0)
            // v is the derivative of s.
            for t in [0.01, 0.1, 0.4, 1.2] {
                XCTAssertEqual((k.s(t + 1e-6) - k.s(t - 1e-6)) / 2e-6, k.v(t), accuracy: 1e-4)
            }
        }
        // Statics = the measured law.
        XCTAssertEqual(ExitKinematics.s(0.3), ExitKinematics.measured.s(0.3))
        XCTAssertEqual(ExitKinematics.v(0.3), ExitKinematics.measured.v(0.3))
        XCTAssertEqual(ExitKinematics.time(toTravel: 12), ExitKinematics.measured.time(toTravel: 12))
    }

    func testSamplesForKeyframes() {
        let k = ExitKinematics.measured
        let s = k.samples(toTravel: 20)
        XCTAssertEqual(s.first?.t, 0)
        XCTAssertEqual(s.first?.s, 0)
        XCTAssertEqual(s.last!.t, k.time(toTravel: 20), accuracy: 1e-12)
        XCTAssertEqual(s.last!.s, 20)
        for (a, b) in zip(s, s.dropFirst()) {
            XCTAssertLessThanOrEqual(b.t - a.t, 1.0 / 60 + 1e-9)
            XCTAssertGreaterThan(b.s, a.s)
        }
        XCTAssertEqual(s.count, Int((k.time(toTravel: 20) * 60).rounded(.up)) + 1)
        XCTAssertEqual(k.samples(toTravel: 0).count, 1)
    }

    func testTheLawIsData() throws {
        let k = try ExitKinematics.measured.overridden(by: Data("{\"vmax\": 80, \"_why\": \"SPEC-motion-audio\"}".utf8))
        XCTAssertEqual(k.vmax, 80)
        XCTAssertEqual(k.v0, 7.67, "missing keys keep the measured value")
        XCTAssertEqual(ExitKinematics.measured.unknownKeys(in: Data("{\"vmax\": 1, \"speed\": 2}".utf8)), ["speed"])
        XCTAssertThrowsError(try ExitKinematics.measured.overridden(by: Data("{\"vmax\": \"fast\"}".utf8)))
        XCTAssertThrowsError(try ExitKinematics.measured.overridden(by: Data("[1]".utf8)))
    }
}
