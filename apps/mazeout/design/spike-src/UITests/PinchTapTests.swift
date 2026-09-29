import XCTest

/// Real touches through XCUITest: tap on release, tap after a long hold, pinch clamps, taps after zoom.
final class PinchTapTests: XCTestCase {
    var app: XCUIApplication!

    override func setUp() {
        continueAfterFailure = true
        app = XCUIApplication()
        app.launchArguments = ["-pc.level", "L032rec", "-pc.scenario", "none", "-pc.uitest", "YES"]
        app.launch()
    }

    private var hud: String { app.staticTexts["hud"].label }
    private func alive() -> Int {
        let part = hud.components(separatedBy: "arrows ")[1].components(separatedBy: "/")[0]
        return Int(part) ?? -1
    }
    private func zoom() -> Double {
        let part = hud.components(separatedBy: "zoom ")[1].components(separatedBy: " ")[0]
        return Double(part) ?? -1
    }
    private func freePoint() -> CGVector? {
        guard hud.contains("free ") else { return nil }
        let xy = hud.components(separatedBy: "free ")[1].components(separatedBy: ",")
        return CGVector(dx: Double(xy[0])!, dy: Double(xy[1])!)
    }
    private func at(_ v: CGVector) -> XCUICoordinate {
        app.coordinate(withNormalizedOffset: .zero).withOffset(v)
    }
    private func shot(_ name: String) {
        let a = XCTAttachment(screenshot: app.screenshot())
        a.name = name
        a.lifetime = .keepAlways
        add(a)
        let url = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("uitest-\(name).png")
        try? app.screenshot().pngRepresentation.write(to: url)
    }

    func testTapHoldPinch() throws {
        XCTAssertTrue(app.staticTexts["hud"].waitForExistence(timeout: 10))
        var log: [String] = []
        let n0 = alive()
        XCTAssertEqual(n0, 53)

        // 1. plain tap on a free arrow at fit
        let p1 = try XCTUnwrap(freePoint())
        at(p1).tap()
        sleep(1)
        log.append("tap@fit \(p1) alive \(alive())")
        XCTAssertEqual(alive(), n0 - 1, "tap at fit")

        // 2. long hold (2 s) then release on a free arrow: the original fires on release
        let p2 = try XCTUnwrap(freePoint())
        at(p2).press(forDuration: 2.0)
        sleep(1)
        log.append("hold2s \(p2) alive \(alive())")
        let afterHold = alive()

        XCTAssertEqual(afterHold, n0 - 2, "a 2 s hold then release must fire (the original fires after 5 s)")

        // 3. pinch in hard: must clamp at the max zoom
        app.otherElements["board"].pinch(withScale: 6, velocity: 4)
        sleep(2)
        let zMax = zoom()
        log.append("pinch in -> zoom \(zMax)")
        XCTAssertLessThanOrEqual(zMax, 3.001)
        XCTAssertGreaterThan(zMax, 1.5)
        shot("pinch-in")
        if let p3 = freePoint() {
            at(p3).tap()
            sleep(1)
            log.append("tap@zoom \(zMax) \(p3) alive \(alive())")
            XCTAssertEqual(alive(), afterHold - 1, "tap while zoomed in")
        } else { log.append("no free arrow on screen at max zoom") }

        // 4. pinch out hard: must clamp at 0.75x of fit
        app.otherElements["board"].pinch(withScale: 0.1, velocity: -4)
        sleep(1)
        app.otherElements["board"].pinch(withScale: 0.3, velocity: -3)
        sleep(2)
        let zMin = zoom()
        log.append("pinch out -> zoom \(zMin)")
        XCTAssertGreaterThanOrEqual(zMin, 0.749)
        XCTAssertLessThan(zMin, 0.9)
        shot("pinch-out")
        let before = alive()
        if let p4 = freePoint() {
            at(p4).tap()
            sleep(1)
            log.append("tap@zoom \(zMin) \(p4) alive \(alive())")
            XCTAssertEqual(alive(), before - 1, "tap while zoomed out")
        }
        let url = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("uitest-log.txt")
        try? log.joined(separator: "\n").write(to: url, atomically: true, encoding: .utf8)
        print("UITEST-LOG\n" + log.joined(separator: "\n"))
    }
}
