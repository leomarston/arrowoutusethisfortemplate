import XCTest

// WP0 → V1 (SPEC-architecture §9.4, §9.7). Shared launch + probe helpers for every UI suite; VERIFY owns this file
// from V1 on. Owners add their own helpers as extensions in their own test files.
// Rules (§9.7): every test launches with `-pc.uitest 1 -pc.seed 1 -pc.fakeStore 1` + a state (`-pc.reset 1` or
// `-pc.state …`) + a target (`-pc.go …`, `-pc.popup …`), terminating the app first; tests never sleep for animations,
// they wait on ANCHORED predicates (`label == …`, BEGINSWITH; never a loose CONTAINS) or on probe values; on a failure
// print `app.debugDescription` before guessing. Permission prompts are one-shot: uninstall before a test that expects one.

enum AppUnderTest {
    /// The §9.7 base arguments.
    static let baseArguments = ["-pc.uitest", "1", "-pc.seed", "1", "-pc.fakeStore", "1"]

    /// Terminates the app, then launches it with the base arguments + `extra` (state and target), e.g.
    /// `AppUnderTest.launch(["-pc.reset", "1", "-pc.level", "32", "-pc.go", "level"])`.
    @discardableResult
    static func launch(_ extra: [String], base: [String] = baseArguments) -> XCUIApplication {
        let app = XCUIApplication()
        app.terminate()
        app.launchArguments = base + extra
        app.launch()
        return app
    }
}

extension XCUIApplication {
    /// The §9.4 probe: the `board.probe` element's accessibilityValue parsed as JSON (nil while it is not there).
    func probe() -> [String: Any]? {
        let e = descendants(matching: .any).matching(identifier: "board.probe").firstMatch
        guard e.exists, let text = e.value as? String, let data = text.data(using: .utf8) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    /// Polls the probe (it refreshes at ≤ 4 Hz, P8) until `predicate` holds or `timeout` passes.
    func waitForProbe(timeout: TimeInterval = 10, _ predicate: ([String: Any]) -> Bool) -> [String: Any]? {
        let deadline = Date().addingTimeInterval(timeout)
        repeat {
            if let p = probe(), predicate(p) { return p }
            RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        } while Date() < deadline
        return nil
    }

    /// A real tap at a screen point in pt (the probe's x, y): the spike's proven method (§9.4).
    func tap(screenX x: Double, y: Double) {
        coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x, dy: y)).tap()
    }

    /// The element with this accessibility identifier, of any type.
    func element(_ identifier: String) -> XCUIElement {
        descendants(matching: .any).matching(identifier: identifier).firstMatch
    }
}

extension XCUIElement {
    /// Waits until an anchored NSPredicate on this element holds, e.g. `wait(for: "value == %@", "3")`.
    func wait(for format: String, _ args: CVarArg..., timeout: TimeInterval = 10) -> Bool {
        let predicate = NSPredicate(format: format, argumentArray: args)
        let exp = XCTNSPredicateExpectation(predicate: predicate, object: self)
        return XCTWaiter().wait(for: [exp], timeout: timeout) == .completed
    }
}

// MARK: - V1 helpers (VERIFY owns this file from V1 on; SPEC-architecture §9.7)

extension AppUnderTest {
    /// A partial PlayerState JSON for `-pc.state` (base64; the app fills every missing field with its default).
    static func state(_ json: String) -> String { Data(json.utf8).base64EncodedString() }
}

/// One probe arrow (§9.4): its id, the screen point to tap, and its tape unit.
struct ProbeArrow: Equatable {
    var id: Int
    var x: Double
    var y: Double
    var unit: [Int]
}

extension XCUIApplication {
    /// The probe once the stage is playable (`ready`: built, the intro acked, the timer frozen until the first tap).
    func waitReady(timeout: TimeInterval = 25, stage: Int? = nil) -> [String: Any]? {
        waitForProbe(timeout: timeout) { p in
            (p["phase"] as? String) == "ready" && (stage == nil || (p["stage"] as? Int) == stage)
        }
    }

    /// Visible, not-red arrows of the probe that are free (or blocked) in the session's rules.
    func arrows(_ p: [String: Any], free: Bool, skipping: Set<Int> = []) -> [ProbeArrow] {
        (p["arrows"] as? [[String: Any]] ?? []).compactMap { a in
            guard (a["free"] as? Bool) == free, (a["red"] as? Bool) != true, let id = a["id"] as? Int, !skipping.contains(id),
                  let x = a["x"] as? Double, let y = a["y"] as? Double, x >= 0, y >= 0 else { return nil }
            return ProbeArrow(id: id, x: x, y: y, unit: a["unit"] as? [Int] ?? [id])
        }
    }

    /// Plays the current board through the REAL input path: taps a free arrow, waits until the probe shows it gone (or the
    /// phase moved on), repeats until the session leaves `ready`/`playing` (won, stage clear, an offer…). Returns the taps.
    @discardableResult
    func playFreeArrows(timeout: TimeInterval = 120) -> Int {
        var taps = 0
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            guard let p = probe() else { RunLoop.current.run(until: Date().addingTimeInterval(0.2)); continue }
            let phase = p["phase"] as? String ?? ""
            guard ["ready", "playing"].contains(phase) else { return taps }
            guard let a = arrows(p, free: true).first else { RunLoop.current.run(until: Date().addingTimeInterval(0.25)); continue }
            tap(screenX: a.x, y: a.y)
            taps += 1
            _ = waitForProbe(timeout: 3) { q in
                let gone = !(q["arrows"] as? [[String: Any]] ?? []).contains { ($0["id"] as? Int) == a.id && ($0["free"] as? Bool) == true }
                return gone || !["ready", "playing"].contains(q["phase"] as? String ?? "") || (q["stage"] as? Int) != (p["stage"] as? Int)
            }
        }
        return taps
    }

    /// Visible static texts inside a container (labels), for copy checks.
    func texts(in identifier: String) -> [String] {
        element(identifier).descendants(matching: .staticText).allElementsBoundByIndex.map(\.label)
    }
}

extension XCTestCase {
    /// A screenshot kept in the result bundle (evidence; build/v1 exports them).
    func keepShot(_ name: String) {
        let a = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        a.name = name
        a.lifetime = .keepAlways
        add(a)
    }
}
